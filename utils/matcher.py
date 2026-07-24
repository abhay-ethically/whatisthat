"""Intent detection, fuzzy tool matching, and context-aware responses for LinuxBot."""
import json
import re
from difflib import SequenceMatcher, get_close_matches
from pathlib import Path


INTENT_KEYWORDS = {
    "greet": ["hi", "hello", "hey", "hola", "greetings", "sup", "yo"],
    "describe": [
        "describe", "what is", "what's", "how does", "full description",
        "explain tool", "about", "how it works", "tell me about", "overview",
        "what does this tool do", "what is this tool", "details",
    ],
    "command": [
        "command", "commands", "how to", "i want", "give me", "show me",
        "need", "check", "scan", "find", "get", "use", "run", "do", "perform",
        "connected devices", "live hosts", "open ports", "port scan",
        "discover", "enumerate", "brute", "download", "transfer", "list files",
        "search file", "change permissions", "kill process", "monitor",
    ],
    "options": [
        "options", "flags", "arguments", "args", "settings", "parameters",
        "switches", "what flag", "list flags", "all flags", "what are the flags",
    ],
    "examples": [
        "examples", "show examples", "example", "give example", "sample",
        "how to use it", "usage examples", "some examples",
    ],
    "install": [
        "install", "how to install", "download tool", "setup", "get this tool",
        "apt install", "package name",
    ],
    "all_commands": [
        "all commands", "every command", "all tasks", "what can it do",
        "show all commands", "list commands", "commands for",
    ],
    "explain": [
        "explain", "what does", "meaning", "mean", "break down",
        "what is flag", "what is option", "what is -", "what does -",
    ],
    "list": [
        "list tools", "show tools", "what tools", "available tools",
        "all tools", "tools list", "which tools", "tool list",
    ],
    "save": [
        "save", "favorite", "bookmark", "keep", "store", "remember",
    ],
    "search": [
        "search", "find command for", "lookup", "look up", "find tool",
    ],
    "execute": [
        "run it", "execute", "run command", "launch", "start", "fire",
    ],
    "help": [
        "help", "usage", "how do i use", "commands", "what can you do",
        "what can i ask", "assist", "support",
    ],
    "exit": [
        "bye", "exit", "quit", "goodbye", "see you", "close", "later",
    ],
}

TOOL_ALIASES = {
    "nc": "netcat",
    "ifconfig": "ip",
    "netstat": "ss",
    "msf": "metasploit",
    "msfconsole": "metasploit",
    "john the ripper": "john",
    "jtr": "john",
}

# Pronouns / context words that should reuse the last discussed tool
CONTEXT_PRONOUNS = [
    "this tool", "that tool", "this one", "that one", "the tool", "same tool",
    "it", "its", "this", "that", "the same", "above tool", "previous tool",
]


class LinuxBot:
    def __init__(self, kb_path=None, data_dir=None):
        if kb_path is None:
            base = Path(__file__).resolve().parent.parent
            kb_path = base / "data" / "knowledge_base.json"
        self.kb_path = Path(kb_path)
        self.data_dir = data_dir or self.kb_path.parent
        self.data_dir = Path(self.data_dir)
        self.kb = self._load_kb()
        self.tools = self.kb.get("tools", [])
        self.tool_names = [t["name"].lower() for t in self.tools]
        self.categories = self.kb.get("categories", [])
        # Conversation context
        self.last_tool_name = None
        self.last_command = None
        self.last_response = None
        self.last_intent = None
        # Session data
        self.favorites = []
        self._load_session()

    def _load_kb(self):
        with open(self.kb_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_session(self):
        self.favorites_path = self.data_dir / "favorites.json"
        if self.favorites_path.exists():
            try:
                with open(self.favorites_path, "r", encoding="utf-8") as f:
                    self.favorites = json.load(f)
            except Exception:
                self.favorites = []
        else:
            self.favorites = []

    def _save_session(self):
        self.favorites_path = self.data_dir / "favorites.json"
        with open(self.favorites_path, "w", encoding="utf-8") as f:
            json.dump(self.favorites, f, indent=2)

    def _normalize(self, text):
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9\s\-/]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def _detect_intent(self, text):
        norm = self._normalize(text)
        scores = {}
        for intent, keywords in INTENT_KEYWORDS.items():
            score = 0
            for kw in keywords:
                if re.search(r"(?:^|\s)" + re.escape(kw) + r"(?:\s|$)", norm):
                    score += len(kw)  # longer keywords are stronger signals
            if score:
                scores[intent] = score
        if not scores:
            return None
        return max(scores, key=scores.get)

    def _uses_pronoun(self, text):
        norm = self._normalize(text)
        for pronoun in CONTEXT_PRONOUNS:
            if re.search(r"(?:^|\s)" + re.escape(pronoun) + r"(?:\s|$)", norm):
                return True
        return False

    def _extract_tool(self, text):
        norm = self._normalize(text)

        # If query uses only a pronoun and we have context, reuse last tool
        if self._uses_pronoun(text) and self.last_tool_name:
            return self.last_tool_name

        # Direct alias handling
        for alias, real in TOOL_ALIASES.items():
            if re.search(r"(?:^|\s)" + re.escape(alias) + r"(?:\s|$)", norm):
                return real

        # Direct tool name match
        for name in self.tool_names:
            if re.search(r"(?:^|\s)" + re.escape(name) + r"(?:\s|$)", norm):
                return name

        # Fuzzy match against full normalized text
        matches = get_close_matches(norm, self.tool_names, n=1, cutoff=0.6)
        if matches:
            return matches[0]

        # Fuzzy match per token
        for token in norm.split():
            if len(token) < 3:
                continue
            matches = get_close_matches(token, self.tool_names, n=1, cutoff=0.75)
            if matches:
                return matches[0]

        return None

    def _find_tool(self, name):
        name = name.lower()
        for tool in self.tools:
            if tool["name"].lower() == name:
                return tool
        return None

    def _find_command_by_task(self, query, top_n=3):
        """Search command task/descriptions across all tools using fuzzy ratio."""
        from difflib import SequenceMatcher
        query_norm = self._normalize(query)
        stop_words = {
            "a", "an", "the", "to", "for", "in", "on", "of", "and", "or",
            "is", "are", "was", "were", "with", "i", "want", "need", "me",
            "give", "show", "command", "commands", "how", "do", "does", "can",
            "you", "use", "using", "run", "my", "this", "that", "it", "its",
            "tool", "please", "tell", "about", "what", "which", "where",
            "when", "why", "who", "there", "here", "some", "any", "all",
        }
        query_words = [w for w in query_norm.split() if w not in stop_words]
        matches = []
        for tool in self.tools:
            for cmd in tool.get("commands", []):
                task = self._normalize(cmd.get("task", ""))
                desc = self._normalize(cmd.get("description", ""))
                ratio = SequenceMatcher(None, query_norm, task).ratio()
                score = ratio * 80
                task_words = set([w for w in task.split() if w not in stop_words])
                desc_words = set([w for w in desc.split() if w not in stop_words])
                query_set = set(query_words)
                score += len(query_set & task_words) * 15
                score += len(query_set & desc_words) * 5
                direct_phrases = {
                    "connected device": ["live host", "discover", "arp"],
                    "live host": ["discover", "network"],
                    "open port": ["port", "scan"],
                    "port scan": ["scan", "port"],
                    "transfer file": ["transfer", "send", "receive", "copy"],
                    "devices": ["host", "discover", "network"],
                    "connected": ["discover", "network", "arp"],
                    "find file": ["search", "find", "locate"],
                    "change owner": ["chown", "owner"],
                    "permission": ["chmod", "permission", "access"],
                    "process": ["ps", "kill", "top", "monitor"],
                    "monitor traffic": ["tcpdump", "tshark", "capture"],
                    "brute force": ["brute", "hydra", "john", "hashcat"],
                    "wifi": ["aircrack", "wireless", "wpa"],
                    "web scan": ["nikto", "gobuster", "dirb", "ffuf"],
                    "sql injection": ["sqlmap", "sql"],
                    "enumerate": ["enum4linux", "enumerate", "discovery"],
                    "reverse shell": ["nc", "netcat", "shell"],
                }
                for phrase, hints in direct_phrases.items():
                    if phrase in query_norm:
                        for hint in hints:
                            if hint in task or hint in desc:
                                score += 25
                if score > 10:
                    matches.append((score, tool, cmd))
        matches.sort(key=lambda x: x[0], reverse=True)
        return matches[:top_n]

    def _best_command_match(self, tool, query):
        query_norm = self._normalize(query)
        stop_words = {
            "a", "an", "the", "to", "for", "in", "on", "of", "and", "or",
            "is", "are", "with", "i", "want", "need", "me", "give", "show",
            "command", "commands", "how", "do", "does", "can", "you", "use",
            "using", "run", "my", "this", "that", "it", "its", "tool",
        }
        best = None
        best_score = 0
        for cmd in tool.get("commands", []):
            task = self._normalize(cmd.get("task", ""))
            desc = self._normalize(cmd.get("description", ""))
            score = 0
            query_set = set([w for w in query_norm.split() if w not in stop_words])
            task_words = set([w for w in task.split() if w not in stop_words])
            desc_words = set([w for w in desc.split() if w not in stop_words])
            score += len(query_set & task_words) * 4
            score += len(query_set & desc_words) * 1
            ratio = SequenceMatcher(None, query_norm, task).ratio()
            score += ratio * 30

            # Phrase boosts for common task-specific requests
            phrase_boosts = {
                "scan ports": ["open ports", "all ports", "comprehensive scan"],
                "scan all ports": ["all ports", "comprehensive scan", "-p-"],
                "check ports": ["open ports", "all ports"],
                "all ports": ["all ports", "comprehensive scan", "-p-"],
                "scan network": ["network range", "live hosts", "discover"],
                "connected devices": ["live hosts", "network range", "discover"],
                "transfer file": ["transfer", "send file", "receive file"],
                "brute force": ["brute", "dictionary", "password"],
                "full scan": ["comprehensive scan", "all ports"],
            }
            for phrase, hints in phrase_boosts.items():
                if phrase in query_norm:
                    for hint in hints:
                        if hint in task or hint in desc or hint in cmd.get("command", ""):
                            score += 25

            if score > best_score:
                best_score = score
                best = cmd
        return best

    def _explain_flags(self, text):
        # Extract flags like -sS, --script, -p-, --open, etc.
        flags = re.findall(r"(?:^|\s)(-[-a-zA-Z0-9]+)", text)
        flags = [f.strip() for f in flags if f.strip()]
        if not flags:
            return None

        results = []
        for flag in flags:
            found = False
            for tool in self.tools:
                for f in tool.get("flags", []):
                    if f["flag"] == flag:
                        results.append({
                            "tool": tool["name"],
                            "flag": f["flag"],
                            "description": f["description"],
                            "example": f.get("example", ""),
                        })
                        found = True
                        break
                if found:
                    break
            if not found:
                results.append({"flag": flag, "description": "Unknown flag in local knowledge base."})
        return results

    def _search_kb(self, query):
        query_norm = self._normalize(query)
        words = set(query_norm.split())
        results = []
        for tool in self.tools:
            score = 0
            text = " ".join([
                tool.get("name", ""),
                tool.get("category", ""),
                tool.get("description", ""),
            ])
            for cmd in tool.get("commands", []):
                text += " " + cmd.get("task", "") + " " + cmd.get("description", "")
            for flag in tool.get("flags", []):
                text += " " + flag.get("flag", "") + " " + flag.get("description", "")
            text = self._normalize(text)
            for word in words:
                if word in text:
                    score += 1
            if score > 0:
                results.append((score, tool))
        results.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in results[:5]]

    def _update_context(self, tool_name=None, command=None, response=None, intent=None):
        if tool_name:
            self.last_tool_name = tool_name
        if command:
            self.last_command = command
        if response:
            self.last_response = response
        if intent:
            self.last_intent = intent

    def handle(self, user_input):
        text = user_input.strip()
        if not text:
            return {"type": "empty", "text": "I didn't catch that. Type 'help' for what I can do."}

        intent = self._detect_intent(text)
        tool_name = self._extract_tool(text)

        # Inherit the last discussed tool for follow-up questions like "show examples"
        context_intents = {"describe", "options", "examples", "install", "all_commands"}
        if not tool_name and self.last_tool_name and intent in context_intents:
            tool_name = self.last_tool_name

        # Handle ambiguous "this tool" / "it" requests that carry no explicit intent
        if self._uses_pronoun(text) and self.last_tool_name and not intent:
            intent = "describe"

        # Greetings
        if intent == "greet":
            self._update_context(intent="greet")
            return {
                "type": "greet",
                "text": (
                    "Hello! I'm LinuxBot, your offline command helper. "
                    "Ask me about any tool, command, or option. Type 'help' to see examples."
                ),
            }

        if intent == "exit":
            return {"type": "exit", "text": "Goodbye! Stay safe out there."}

        if intent == "help" or (intent is None and not tool_name):
            return {
                "type": "help",
                "text": (
                    "Here are some things you can ask me:\n"
                    "  'nmap command to check ports'\n"
                    "  'command to check connected devices in network'\n"
                    "  'describe nmap' or 'what is nmap'\n"
                    "  'how does nmap work'\n"
                    "  'options for nmap' or 'flags for nmap'\n"
                    "  'explain -sS -p-'\n"
                    "  'show examples for nmap'\n"
                    "  'all commands for nmap'\n"
                    "  'how to install nmap'\n"
                    "  'list tools'\n"
                    "  'search sql injection'\n"
                    "  'save last' (save the last command shown)\n"
                    "  'run it' (execute the last command with confirmation)"
                ),
            }

        if intent == "list":
            return {"type": "list", "tools": self.tools}

        if intent == "search":
            query = text
            for kw in ["search", "find command for", "lookup", "look up", "find tool"]:
                query = re.sub(r"(?:^|\s)" + re.escape(kw) + r"(?:\s|$)", " ", query)
            return {
                "type": "search",
                "query": query.strip(),
                "tools": self._search_kb(query.strip()),
            }

        if intent == "save":
            if self.last_command:
                entry = {
                    "command": self.last_command,
                    "context": self.last_response or "",
                }
                self.favorites.append(entry)
                self._save_session()
                return {"type": "save", "text": f"Saved command: {self.last_command}"}
            return {"type": "save", "text": "There's no command to save yet. Ask me for a command first."}

        if intent == "execute":
            if self.last_command:
                return {"type": "execute", "command": self.last_command}
            return {"type": "execute", "text": "No command to run. Ask me for a command first."}

        if intent == "explain":
            flags = self._explain_flags(text)
            if flags:
                self._update_context(intent="explain")
                return {"type": "explain", "flags": flags}
            # Maybe the user wants a tool description instead
            if tool_name:
                tool = self._find_tool(tool_name)
                if tool:
                    self._update_context(tool_name=tool["name"], intent="describe")
                    return {"type": "describe", "tool": tool}
            return {
                "type": "explain",
                "text": "I couldn't find flags to explain. Try: 'explain -sS -p-' or 'describe nmap'.",
            }

        if intent == "options":
            if not tool_name:
                return {"type": "options", "text": "Which tool's options do you want? Try: 'options for nmap'."}
            tool = self._find_tool(tool_name)
            if tool:
                self._update_context(tool_name=tool["name"], intent="options")
                return {"type": "options", "tool": tool}
            return {"type": "options", "text": f"I don't know a tool named '{tool_name}'."}

        if intent == "examples":
            if not tool_name:
                return {"type": "examples", "text": "Which tool's examples do you want? Try: 'show examples for nmap'."}
            tool = self._find_tool(tool_name)
            if tool:
                self._update_context(tool_name=tool["name"], intent="examples")
                return {"type": "examples", "tool": tool}
            return {"type": "examples", "text": f"I don't know a tool named '{tool_name}'."}

        if intent == "install":
            if not tool_name:
                return {"type": "install", "text": "Which tool's install command do you want? Try: 'how to install nmap'."}
            tool = self._find_tool(tool_name)
            if tool:
                self._update_context(tool_name=tool["name"], intent="install")
                return {"type": "install", "tool": tool}
            return {"type": "install", "text": f"I don't know a tool named '{tool_name}'."}

        if intent == "all_commands":
            if not tool_name:
                return {"type": "all_commands", "text": "Which tool's commands do you want? Try: 'all commands for nmap'."}
            tool = self._find_tool(tool_name)
            if tool:
                self._update_context(tool_name=tool["name"], intent="all_commands")
                return {"type": "all_commands", "tool": tool}
            return {"type": "all_commands", "text": f"I don't know a tool named '{tool_name}'."}

        if intent == "describe":
            if not tool_name:
                return {"type": "describe", "text": "Which tool do you want me to describe? Try: 'describe nmap' or 'what is nmap'."}
            tool = self._find_tool(tool_name)
            if tool:
                self._update_context(tool_name=tool["name"], intent="describe")
                return {"type": "describe", "tool": tool}
            return {"type": "describe", "text": f"I don't know a tool named '{tool_name}'."}

        # Default intent is command/task lookup
        if tool_name:
            tool = self._find_tool(tool_name)
            if tool:
                cmd = self._best_command_match(tool, text)
                if cmd:
                    self._update_context(
                        tool_name=tool["name"],
                        command=cmd["command"],
                        response=f"{tool['name']}: {cmd['task']}",
                        intent="command",
                    )
                    return {
                        "type": "command",
                        "tool": tool,
                        "command": cmd,
                    }
                # If no good command match but tool mentioned, show all commands
                self._update_context(tool_name=tool["name"], intent="all_commands")
                return {"type": "all_commands", "tool": tool}

        # Try to find a command by task description even when tool name isn't mentioned
        cmd_matches = self._find_command_by_task(text, top_n=3)
        if cmd_matches:
            score, tool, cmd = cmd_matches[0]
            self._update_context(
                tool_name=tool["name"],
                command=cmd["command"],
                response=f"{tool['name']}: {cmd['task']}",
                intent="command",
            )
            return {
                "type": "command",
                "tool": tool,
                "command": cmd,
            }

        # Fallback: search across all tools
        results = self._search_kb(text)
        if results:
            return {"type": "search", "query": text, "tools": results}

        return {
            "type": "unknown",
            "text": (
                "I'm not sure I understood. Try asking for a command, description, "
                "or flags. Type 'help' for examples."
            ),
        }

    def get_favorites(self):
        return self.favorites
