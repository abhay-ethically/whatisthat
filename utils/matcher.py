"""Intent detection, fuzzy tool matching, and context-aware responses for LinuxBot."""
import json
import random
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
    "guide": [
        "guide", "walk me through", "step by step", "how do i use",
        "how to use", "steps to use", "tutorial", "teach me",
        "how should i start", "how can i use", "usage guide",
    ],
    "explain": [
        "explain", "what does", "meaning", "mean", "break down",
        "what is flag", "what is option", "what is -", "what does -",
        "explain command", "what does this command do", "explain this command",
        "break down this command", "what is this command", "what does this do",
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
    "bundle": [
        "everything", "full guide", "complete info", "all info", "full details",
        "tell me everything", "all about", "give me everything", "full tutorial",
        "show me everything", "complete guide",
    ],
    "execute": [
        "run it", "execute", "run command", "launch", "start", "fire",
    ],
    "abuse": [
        "gtfobins", "suid", "privilege escalation", "escalate privileges",
        "binary abuse", "sudo abuse", "abuse", "bypass", "post exploitation",
        "post-exploitation",
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
    "msfvenom": "metasploit",
    "john the ripper": "john",
    "jtr": "john",
    "aircrack": "aircrack-ng",
    "airodump": "aircrack-ng",
    "airmon": "aircrack-ng",
}

CHITCHAT_RESPONSES = {
    r"\b(hi|hello|hey|hola|greetings|yo|sup)\b": [
        "Hello! I'm LinuxBot. Ask me about Linux commands, networking tools, or pentest tools.",
        "Hey there! Ready to help with Linux commands and security tools.",
    ],
    r"\bhow are you\b": "I'm running smoothly. What Linux command can I help you with today?",
    r"\bwhat('s| is) your name\b": "I'm LinuxBot, your offline Linux command helper.",
    r"\bwho are you\b": "I'm LinuxBot. I know about Linux, networking, and pentest tools — fully offline.",
    r"\bwhat can you do\b": "I can suggest commands, explain flags, show examples, and guide you through tools. Type 'help' for ideas.",
    r"\b(thank you|thanks|ty)\b": "You're welcome! Let me know if you need another command.",
    r"\b(tell me a joke|joke|funny)\b": "Why do programmers prefer dark mode? Because light attracts bugs.",
    r"\bhelp me\b": "Sure! Tell me what you want to do — e.g., scan ports, find files, crack a wifi handshake — and I'll suggest the right command.",
}

GENERAL_RESPONSES = {
    r"\bwhat is linux\b": "Linux is a free, open-source operating system kernel. Distributions like Ubuntu, Debian, Fedora, and Kali Linux build on top of it.",
    r"\bwhat is (kali linux|kali)\b": "Kali Linux is a Debian-based distribution designed for penetration testing and security auditing. It comes preloaded with hundreds of security tools.",
    r"\bwhat is (pentest|penetration testing)\b": "Penetration testing is the practice of testing computer systems, networks, or web applications for security weaknesses with authorization.",
    r"\bwhat is (hacking|ethical hacking)\b": "Hacking means exploring or modifying systems. Ethical hacking is done with permission to find and fix security issues.",
    r"\bwhat is a firewall\b": "A firewall is a network security device or software that monitors and controls incoming and outgoing network traffic based on rules.",
    r"\bwhat is an? (ids|intrusion detection system)\b": "An IDS (Intrusion Detection System) monitors network or system traffic for suspicious activity and alerts administrators.",
    r"\bwhat is a vpn\b": "A VPN (Virtual Private Network) encrypts your internet connection and hides your IP address for privacy and security.",
    r"\bwhat is an? (ips|intrusion prevention system)\b": "An IPS (Intrusion Prevention System) monitors traffic and can actively block detected threats, unlike an IDS which only alerts.",
    r"\bwhat is (a |an )?(bash|shell)\b": "Bash is a Unix shell and command language. A shell reads your commands and translates them into instructions for the computer.",
    r"\bwhat is (a |an )?(terminal|command line|cli)\b": "The command line interface (CLI) is a text-based way to interact with the operating system by typing commands instead of clicking icons.",
    r"\bwhat is (root|sudo|superuser)\b": "Root is the superuser account on Linux with full system privileges. sudo lets an authorized user run commands as root temporarily.",
    r"\bwhat is an? (ip address|ip)\b": "An IP address is a unique identifier assigned to a device on a network, used to route traffic. IPv4 looks like 192.168.1.1; IPv6 is longer and hexadecimal.",
    r"\bwhat is (dns|domain name system)\b": "DNS translates human-readable domain names like example.com into IP addresses that computers use to communicate.",
    r"\bwhat is a (mac address|mac)\b": "A MAC address is a hardware identifier burned into a network interface card. It is used for local network communication.",
    r"\bwhat is (dhcp|dynamic host configuration protocol)\b": "DHCP automatically assigns IP addresses and network settings to devices when they join a network.",
    r"\bwhat is (https|ssl|tls|http)\b": "HTTP transfers web pages. HTTPS adds encryption via SSL/TLS to protect data between your browser and the server.",
    r"\bwhat is (ssh|secure shell)\b": "SSH is a protocol for securely connecting to and managing remote systems over an encrypted channel.",
    r"\bwhat is a (port|network port)\b": "A port is a virtual point where network connections start or end. Different services listen on standard ports, e.g. 80 for HTTP and 22 for SSH.",
    r"\bwhat is a (protocol|network protocol)\b": "A network protocol is a set of rules that define how devices exchange data over a network, such as TCP, UDP, IP, and HTTP.",
    r"\bwhat is (tcp|udp)\b": "TCP is a reliable, connection-oriented protocol. UDP is faster but connectionless and does not guarantee delivery.",
    r"\bwhat is (wireless|wi-fi|wifi)\b": "Wi-Fi uses radio waves to provide wireless network access, commonly using the 2.4 GHz and 5 GHz frequency bands.",
    r"\bwhat is a (router|switch|access point)\b": "A router forwards traffic between networks. A switch connects devices within the same network. An access point provides wireless connectivity.",
    r"\bwhat is (encryption|cryptography)\b": "Encryption scrambles data so only authorized parties can read it. Cryptography is the broader science of securing information.",
    r"\bwhat is a (hash|hashing)\b": "A hash is a fixed-size value generated from data. Good hashes are one-way, making them useful for storing passwords and verifying file integrity.",
    r"\bwhat is (malware|virus|trojan|worm|ransomware)\b": "Malware is malicious software. Viruses infect files, Trojans disguise themselves, worms spread independently, and ransomware encrypts data for ransom.",
    r"\bwhat is (phishing|social engineering)\b": "Phishing tricks users into revealing credentials or sensitive data. Social engineering manipulates people into breaking security procedures.",
    r"\bwhat is a (vulnerability|exploit|cve|zero day)\b": "A vulnerability is a weakness. An exploit takes advantage of it. CVEs are publicly tracked vulnerability IDs; a zero-day is an unpatched flaw.",
    r"\bwhat is (reconnaissance|recon|footprinting)\b": "Reconnaissance is gathering information about a target before attacking, such as identifying hosts, ports, services, and employees.",
    r"\bwhat is (enumeration|scanning)\b": "Enumeration extracts detailed information from a target, such as users, shares, and software versions. Scanning maps live hosts and open ports.",
    r"\bwhat is (privilege escalation|privesc)\b": "Privilege escalation is gaining higher-level permissions on a system, e.g. from a regular user to root or administrator.",
    r"\bwhat is (lateral movement|pivoting)\b": "Lateral movement or pivoting is moving from a compromised host to other systems inside the same network.",
    r"\bwhat is (persistence|backdoor)\b": "Persistence maintains access to a compromised system after reboots. A backdoor provides hidden access.",
    r"\bwhat is (credential stuffing|password spraying)\b": "Credential stuffing tries leaked username/password pairs. Password spraying tries a few common passwords against many accounts to avoid lockouts.",
    r"\bwhat is (osi|osi model)\b": "The OSI model is a 7-layer conceptual framework for networking: Physical, Data Link, Network, Transport, Session, Presentation, Application.",
    r"\bwhat is (kerberos|ldap|active directory|ad)\b": "Active Directory is Microsoft's directory service for managing users, computers, and policies. Kerberos is its main authentication protocol. LDAP queries directory data.",
    r"\bwhat is (a |an )?(reverse shell|bind shell)\b": "A reverse shell has the target connect back to the attacker. A bind shell listens on the target for an incoming attacker connection.",
    r"\bwhat is (a |an )?(dos|ddos)\b": "Denial of Service (DoS) floods a target to make it unavailable. Distributed DoS uses many machines, often a botnet.",
    r"\bwhat is (a |an )?(mitm|man in the middle)\b": "A Man-in-the-Middle attack intercepts communication between two parties to eavesdrop or alter messages.",
    r"\bwhat is (arp|arp spoofing)\b": "ARP maps IP addresses to MAC addresses. ARP spoofing poisons this mapping to redirect traffic through the attacker.",
    r"\bwhat is (a |an )?(wordlist|dictionary attack)\b": "A wordlist is a file of candidate passwords or usernames. A dictionary attack tries each entry against a target.",
    r"\bwhat is (a |an )?(botnet|c2|command and control)\b": "A botnet is a network of compromised devices controlled by an attacker. C2 (command and control) is the infrastructure used to manage them.",
    r"\bwhat is (a |an )?(rootkit|keylogger)\b": "A rootkit hides malicious presence deep in the OS. A keylogger records keystrokes to steal passwords and other sensitive input.",
}

EXTRACTION_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "being", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "want",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "my", "your", "his", "its", "our", "their", "this", "that", "these",
    "those", "what", "which", "who", "whom", "whose", "where", "when",
    "why", "how", "all", "any", "both", "each", "few", "more", "most",
    "other", "some", "such", "no", "nor", "not", "only", "own", "same",
    "so", "than", "too", "very", "just", "but", "and", "or", "yet", "for",
    "on", "in", "at", "by", "with", "about", "against", "between", "into",
    "through", "during", "before", "after", "above", "below", "from",
    "up", "down", "of", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "if", "else", "because", "until", "while", "as",
    "to",
    "tell", "give", "show", "describe", "explain", "install", "list",
    "search", "find", "look", "run", "use", "using", "command", "commands",
    "tool", "tools", "flag", "flags", "option", "options", "task", "tasks",
}

# Filler prefixes we can strip from a task query without losing meaning
FILLER_PREFIXES = [
    "how do i", "how can i", "how would i", "how should i",
    "i want to", "i need to", "i would like to", "i'd like to",
    "can you", "could you", "would you", "will you",
    "please", "show me how to", "tell me how to", "give me the",
    "what is the", "what's the", "how to", "command to", "way to",
    "method to", "steps to",
]

# Spoken-language synonyms mapped to canonical command/task words
TASK_SYNONYMS = {
    "display": "show",
    "lookup": "search",
    "look up": "search",
    "look for": "find",
    "seek": "find",
    "retrieve": "get",
    "fetch": "get",
    "erase": "delete",
    "remove": "delete",
    "kill": "stop",
    "terminate": "stop",
    "halt": "stop",
    "linked": "connected",
    "joined": "connected",
    "active hosts": "live hosts",
    "running hosts": "live hosts",
    "ports open": "open ports",
    "open port": "open ports",
    "port scanning": "port scan",
    "portscanner": "port scan",
    "send file": "transfer file",
    "move file": "transfer file",
    "copy file": "transfer file",
    "file copy": "transfer file",
    "wi fi": "wifi",
    "wi-fi": "wifi",
    "wireless network": "wifi",
    "cracker": "crack",
    "cracking": "crack",
    "bruteforce": "brute force",
    "brute-force": "brute force",
    "web scanner": "web scan",
    "web scanning": "web scan",
    "sql injection": "sqlmap",
    "sqlmap scan": "sqlmap",
    "enumerate shares": "enum4linux",
    "list users": "enumerate users",
    "list files": "find file",
    "search file": "find file",
    "locate file": "find file",
    "sniff": "capture",
    "sniffing": "capture",
    "packet sniffing": "capture packet",
    "change permission": "change permissions",
    "file permission": "change permissions",
    "file permissions": "change permissions",
    "banner grab": "banner grabbing",
    "grab banner": "banner grabbing",
    "sub domain": "subdomain",
    "sub-domain": "subdomain",
    "disk usage": "du",
    "disk free": "df",
    "free space": "df",
    "free disk": "df",
    "memory usage": "free",
    "ram usage": "free",
    "process list": "ps",
    "list processes": "ps",
    "running processes": "ps",
    "gimme": "give me",
    "lemme": "let me",
    "wanna": "want to",
    "gonna": "going to",
    "plz": "please",
    "how to run": "how to use",
    "learn": "teach me",
    "crack wifi": "crack wifi",
    "hack wifi": "crack wifi",
    "wifi crack": "crack wifi",
    "capture wifi": "capture wifi",
    "dump wifi": "capture wifi",
    "get shell": "reverse shell",
    "spawn shell": "reverse shell",
    "get a shell": "reverse shell",
    "list hidden files": "list hidden files",
    "hidden files": "list hidden files",
    "show hidden files": "list hidden files",
    "check service": "check service",
    "start service": "start service",
    "stop service": "stop service",
    "restart service": "restart service",
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
        self._merge_kali_tools()
        self._merge_enrichments()
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

        # Optional tldr-pages and GTFOBins datasets (loaded lazily on first use)
        self._tldr_kb = None
        self._tldr_by_name = {}
        self._gtfo_kb = None
        self._gtfo_by_name = {}

    def _load_kb(self):
        with open(self.kb_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _merge_kali_tools(self):
        kali_path = self.data_dir / "kali_tools.json"
        if not kali_path.exists():
            return
        with open(kali_path, "r", encoding="utf-8") as f:
            kali_kb = json.load(f)
        existing = {t["name"].lower() for t in self.tools}
        for tool in kali_kb.get("tools", []):
            if tool["name"].lower() not in existing:
                self.tools.append(tool)

    def _merge_enrichments(self):
        enrich_path = self.data_dir / "enrichments.json"
        if not enrich_path.exists():
            return
        with open(enrich_path, "r", encoding="utf-8") as f:
            enrich_kb = json.load(f)
        existing = {t["name"].lower(): t for t in self.tools}
        for tool in enrich_kb.get("tools", []):
            name = tool["name"].lower()
            if name in existing:
                existing[name].update(tool)
            else:
                self.tools.append(tool)

    def _load_tldr_kb(self):
        """Lazy-load the optional tldr-pages dataset."""
        if self._tldr_kb is not None:
            return self._tldr_kb
        tldr_path = self.data_dir / "tldr_kb.json"
        if not tldr_path.exists():
            self._tldr_kb = []
            return self._tldr_kb
        with open(tldr_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._tldr_kb = data.get("tools", [])
        self._tldr_by_name = {t["name"].lower(): t for t in self._tldr_kb}
        return self._tldr_kb

    def _find_tldr_tool(self, name):
        self._load_tldr_kb()
        return self._tldr_by_name.get(name.lower())

    def _search_tldr(self, query):
        """Search tldr descriptions and examples for a query."""
        self._load_tldr_kb()
        query_norm = self._normalize_task_query(query)
        # Keep short words that are actual tldr tool names (e.g. du, ps, df)
        words = set()
        for w in query_norm.split():
            if w in self._tldr_by_name:
                words.add(w)
            elif w not in EXTRACTION_STOPWORDS and len(w) >= 2:
                words.add(w)
        results = []
        for tool in self._tldr_kb:
            text = tool.get("description", "") + " " + " ".join(tool.get("examples", []))
            text_norm = self._normalize(text)
            name = tool["name"].lower()
            score = 0
            for word in words:
                if word == name:
                    score += 35
                elif word in name:
                    score += 20
                if word in text_norm:
                    score += 5
            if score > 0:
                results.append((score, tool))
        results.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in results[:5]]

    def _load_gtfobins_kb(self):
        """Lazy-load the optional GTFOBins dataset."""
        if self._gtfo_kb is not None:
            return self._gtfo_kb
        gtfo_path = self.data_dir / "gtfobins_kb.json"
        if not gtfo_path.exists():
            self._gtfo_kb = []
            return self._gtfo_kb
        with open(gtfo_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._gtfo_kb = data.get("tools", [])
        self._gtfo_by_name = {t["name"].lower(): t for t in self._gtfo_kb}
        return self._gtfo_kb

    def _search_gtfobins(self, query):
        """Search GTFOBins function names and command text."""
        self._load_gtfobins_kb()
        query_norm = self._normalize_task_query(query)
        words = set(
            w for w in query_norm.split()
            if w not in EXTRACTION_STOPWORDS and len(w) >= 3
        )
        results = []
        for tool in self._gtfo_kb:
            text = self._normalize(tool.get("description", ""))
            for cmd in tool.get("commands", []):
                text += " " + self._normalize(cmd.get("task", ""))
                text += " " + self._normalize(cmd.get("command", ""))
            score = 0
            name = tool["name"].lower()
            for word in words:
                if word == name:
                    score += 30
                elif word in name:
                    score += 15
                if word in text:
                    score += 5
            if score > 0:
                results.append((score, tool))
        results.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in results[:5]]

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

    def _normalize_intent_query(self, text):
        """Normalize a user query for intent detection. Preserves question words."""
        norm = self._normalize(text)
        contractions = {
            "whats": "what is",
            "whatre": "what are",
            "hows": "how is",
            "wheres": "where is",
            "whos": "who is",
            "im": "i am",
            "youre": "you are",
            "theyre": "they are",
            "isnt": "is not",
            "arent": "are not",
            "dont": "do not",
            "doesnt": "does not",
            "cant": "cannot",
            "wont": "will not",
            "shouldnt": "should not",
            "wouldnt": "would not",
        }
        for bad, good in contractions.items():
            norm = re.sub(r"\b" + bad + r"\b", good, norm)
        return re.sub(r"\s+", " ", norm).strip()

    def _normalize_task_query(self, text):
        """Normalize a user query for task/command matching."""
        norm = self._normalize_intent_query(text)

        # Strip common filler prefixes so matching focuses on the actual task
        for prefix in FILLER_PREFIXES:
            norm = re.sub(r"^\s*" + re.escape(prefix) + r"\b\s*", "", norm)

        # Map synonyms to canonical words
        for phrase, canon in TASK_SYNONYMS.items():
            norm = re.sub(r"\b" + re.escape(phrase) + r"\b", canon, norm)

        return re.sub(r"\s+", " ", norm).strip()

    def _detect_intent(self, text):
        norm = self._normalize_intent_query(text)

        # Catch "list/show <category> tools" even when other words sit between them
        if re.search(r"\b(list|show)\b.*\btools?\b", norm) or \
           re.search(r"\btools?\b.*\b(list|show)\b", norm):
            return "list"

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

    def _detect_chitchat(self, text):
        lower = text.lower()
        for pattern, response in CHITCHAT_RESPONSES.items():
            if re.search(pattern, lower):
                if isinstance(response, list):
                    return random.choice(response)
                return response
        return None

    def _detect_general(self, text):
        lower = text.lower()
        for pattern, response in GENERAL_RESPONSES.items():
            if re.search(pattern, lower):
                return response
        return None

    def _extract_tool(self, text):
        norm = self._normalize(text)

        # If query uses only a pronoun and we have context, reuse last tool
        if self._uses_pronoun(text) and self.last_tool_name:
            return self.last_tool_name

        # Direct alias handling (exact word match)
        for alias, real in TOOL_ALIASES.items():
            if re.search(r"(?:^|\s)" + re.escape(alias) + r"(?:\s|$)", norm):
                return real

        # Direct tool name match (word boundaries)
        for name in self.tool_names:
            if re.search(r"(?:^|\s)" + re.escape(name) + r"(?:\s|$)", norm):
                return name

        # Fuzzy matching is intentionally disabled here: too many conversational
        # words (e.g. "scan", "change", "life") are substrings of tool names and
        # produced false positives. Task/search fallbacks handle tool-free queries.
        return None

    def _extract_category(self, text):
        """Return a category name if the user is asking for tools in a category."""
        norm = self._normalize_task_query(text)
        available = sorted({t.get("category", "") for t in self.tools if t.get("category")})
        category_aliases = {
            "core": ["core", "linux", "basic", "system", "general"],
            "networking": ["networking", "network", "net", "recon", "reconnaissance"],
            "pentest": ["pentest", "penetration", "security", "hacking", "exploit"],
            "kali": ["kali", "kalitools"],
        }
        # Exact match first
        for cat in available:
            if re.search(r"\b" + re.escape(cat) + r"\b", norm):
                return cat
        # Alias match
        for cat, aliases in category_aliases.items():
            for alias in aliases:
                if re.search(r"\b" + re.escape(alias) + r"\b", norm):
                    return cat
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
        query_norm = self._normalize_task_query(query)
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
                    "change permission": ["chmod"],
                    "change permissions": ["chmod"],
                    "file permission": ["chmod"],
                    "file permissions": ["chmod"],
                    "chmod": ["chmod"],
                    "process": ["ps", "kill", "top", "monitor"],
                    "monitor traffic": ["tcpdump", "tshark", "capture"],
                    "brute force": ["brute", "hydra", "john", "hashcat"],
                    "wifi": ["aircrack", "wireless", "wpa"],
                    "web scan": ["nikto", "gobuster", "dirb", "ffuf"],
                    "sql injection": ["sqlmap", "sql"],
                    "enumerate": ["enum4linux", "enumerate", "discovery"],
                    "reverse shell": ["nc", "netcat", "shell"],
                    "capture packet": ["tcpdump", "tshark", "capture"],
                    "password crack": ["john", "hashcat", "crack"],
                    "directory brute": ["gobuster", "dirb", "ffuf", "directory"],
                    "subdomain": ["dnsrecon", "gobuster", "subdomain"],
                    "banner grab": ["netcat", "nc", "banner"],
                }
                has_direct_match = False
                for phrase, hints in direct_phrases.items():
                    if phrase in query_norm:
                        for hint in hints:
                            if hint in task or hint in desc or hint in cmd.get("command", ""):
                                score += 25
                                has_direct_match = True
                # Require either a direct phrase, a shared word, or a very strong
                # fuzzy ratio. This stops random ratio-only matches like
                # "show me disk usage" -> curl "show headers".
                has_word_match = bool(query_set & task_words) or bool(query_set & desc_words)
                if score > 10 and (has_direct_match or has_word_match or ratio >= 0.7):
                    matches.append((score, tool, cmd))
        matches.sort(key=lambda x: x[0], reverse=True)
        matches = [m for m in matches if m[0] >= 25]
        return matches[:top_n]

    def _best_command_match(self, tool, query):
        query_norm = self._normalize_task_query(query)
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
                "full enumeration": ["enum4linux", "enumerate", "all simple enumeration"],
                "crack password": ["john", "hashcat", "crack"],
                "capture packet": ["tcpdump", "tshark", "capture"],
                "put interface in monitor mode": ["airmon-ng", "monitor mode"],
            }
            for phrase, hints in phrase_boosts.items():
                if phrase in query_norm:
                    for hint in hints:
                        if hint in task or hint in desc or hint in cmd.get("command", ""):
                            score += 25

            if score > best_score:
                best_score = score
                best = cmd

        # Only return a match if it is reasonably confident
        if best_score < 20:
            return None
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

    def _strip_explain_prefix(self, text):
        """Remove leading phrases like 'explain' or 'what does ... do' so we can
        see the actual command the user wants explained."""
        prefixes = [
            "explain command", "explain this command:", "explain this command",
            "break down this command:", "break down this command",
            "what does this command do", "what does this do", "what is this command:",
            "what is this command", "explain:", "explain", "what does", "what is",
            "break down",
        ]
        lower = text.lower()
        for prefix in prefixes:
            if lower.startswith(prefix + " "):
                return text[len(prefix) + 1 :].strip()
            if lower.startswith(prefix):
                remainder = text[len(prefix) :].strip()
                # Drop a trailing " do" / " mean" left over from "what does X do"
                if remainder.lower().endswith(" do"):
                    remainder = remainder[:-3].strip()
                if remainder.lower().endswith(" mean"):
                    remainder = remainder[:-5].strip()
                return remainder
        return text

    def _is_command_input(self, text):
        """Detect if the user pasted an actual command line to be explained."""
        command_part = self._strip_explain_prefix(text)
        if not command_part:
            return False
        norm = self._normalize(command_part)
        parts = norm.split()
        if not parts:
            return False
        first = parts[0]
        # Allow commands prefixed with sudo/doas/su
        if first in ("sudo", "doas", "su") and len(parts) > 1:
            first = parts[1]
        if first not in self.tool_names:
            self._load_tldr_kb()
            if first not in self._tldr_by_name:
                return False
        # A single tool name like "cat" or "nmap" should be handled by describe/guide
        if len(parts) == 1:
            return False
        # Strong command-line signals
        if re.search(
            r"[-<>=|&;]|\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(/\d{1,2})?\b|/\w+|\.(txt|json|csv|sh|py|cap|pcap|tar|gz|tgz|log|conf|md)\b",
            norm,
        ):
            return True
        # If the user explicitly asked to explain/break down a command, trust it.
        explain_prefixes = ["explain", "what does", "what is", "break down"]
        lower = text.lower()
        if any(lower.startswith(p) or (" " + p + " ") in lower for p in explain_prefixes):
            return True
        return False

    def _explain_command(self, text):
        """Break a full command line into plain-English pieces."""
        command_part = self._strip_explain_prefix(text)
        norm = self._normalize(command_part)
        parts = norm.split()
        has_sudo = False
        if parts and parts[0] == "sudo":
            has_sudo = True
            parts = parts[1:]
        if not parts:
            return None
        tool_name = parts[0]
        tool = self._find_tool(tool_name) or self._find_tldr_tool(tool_name)
        if not tool:
            return None

        # Build a flag lookup from the tool's documented flags
        flag_map = {}
        for f in tool.get("flags", []):
            flag_map[f["flag"]] = f
            # Also index without leading dash(s)
            bare = f["flag"].lstrip("-")
            flag_map[bare] = f

        explanations = []
        if has_sudo:
            explanations.append({
                "type": "operator",
                "value": "sudo",
                "description": "Run the following command with superuser privileges.",
            })
        for token in parts[1:]:
            # Redirections / pipes / operators
            if token in ("|", "||", "&&", ";", ">>", ">", "<", "&"):
                explanations.append({
                    "type": "operator",
                    "value": token,
                    "description": "Shell operator.",
                })
            elif token == "sudo":
                explanations.append({
                    "type": "operator",
                    "value": token,
                    "description": "Run the following command with superuser privileges.",
                })
            elif token.startswith("-"):
                f = flag_map.get(token)
                if f:
                    explanations.append({
                        "type": "flag",
                        "value": token,
                        "description": f.get("description", "No description available."),
                    })
                else:
                    explanations.append({
                        "type": "flag",
                        "value": token,
                        "description": "Flag not documented in the local knowledge base.",
                    })
            elif re.match(r"^<.+>$", token):
                explanations.append({
                    "type": "arg",
                    "value": token,
                    "description": "Placeholder — replace with a real value.",
                })
            elif re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(/\d{1,2})?$", token):
                explanations.append({
                    "type": "arg",
                    "value": token,
                    "description": "An IP address or CIDR range (likely the target).",
                })
            elif re.match(r"^[\w.-]+\.[a-z]{2,}$", token):
                explanations.append({
                    "type": "arg",
                    "value": token,
                    "description": "A domain name.",
                })
            elif "/" in token or token.endswith((".txt", ".json", ".csv", ".sh", ".py", ".cap", ".pcap", ".tar", ".gz")):
                explanations.append({
                    "type": "arg",
                    "value": token,
                    "description": "A file path or filename.",
                })
            else:
                explanations.append({
                    "type": "arg",
                    "value": token,
                    "description": "Command argument or value.",
                })

        return {
            "tool": tool,
            "command": text.strip(),
            "explanations": explanations,
        }

    def _extract_entities(self, text):
        """Pull common command entities out of a natural-language request."""
        entities = {}
        # IP address / CIDR
        ips = re.findall(
            r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?\b", text
        )
        if ips:
            entities["target"] = ips[0]
            entities["ip"] = ips[0]
        # Domain (skip things that look like IPs or file paths)
        if "target" not in entities:
            domains = re.findall(
                r"\b[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?)+\.[a-z]{2,}\b",
                text,
                re.IGNORECASE,
            )
            domains = [d for d in domains if "." in d and not re.match(r"\d+\.\d+\.\d+\.\d+", d)]
            if domains:
                entities["target"] = domains[0]
                entities["domain"] = domains[0]
        # Port or range
        port_match = re.search(
            r"\b(?:port[s]?\s+)?(\d{1,5}(?:\s*-\s*\d{1,5})?)\b", text, re.IGNORECASE
        )
        if port_match:
            entities["port"] = port_match.group(1).replace(" ", "")
        # Network interface
        iface_match = re.search(
            r"\b(eth0|eth1|wlan0|wlan1|lo|tun0|tap0|ens\d+|enp\d+s\d+)\b", text, re.IGNORECASE
        )
        if iface_match:
            entities["interface"] = iface_match.group(1)
        # Wordlist file
        wordlists = re.findall(r"\b\S+\.txt\b", text)
        if wordlists:
            entities["wordlist"] = wordlists[0]
        # Output / capture file
        outputs = re.findall(r"\b\S+\.(pcap|cap|log|txt|json|csv|tar|gz)\b", text)
        if outputs:
            entities["output"] = outputs[0]
        # Protocol
        if re.search(r"\bssh\b", text, re.IGNORECASE):
            entities["protocol"] = "ssh"
        elif re.search(r"\bftp\b", text, re.IGNORECASE):
            entities["protocol"] = "ftp"
        elif re.search(r"\bhttp(?:s)?\b", text, re.IGNORECASE):
            entities["protocol"] = "http"
        return entities

    def _substitute_placeholders(self, command, entities):
        """Replace placeholders in a command template with entities from the query."""
        if not command:
            return command
        out = command
        if "target" in entities:
            out = re.sub(r"<target>|\{\{target\}\}|<ip>|\{\{ip\}\}", entities["target"], out, flags=re.IGNORECASE)
        if "port" in entities:
            out = re.sub(r"<port>|\{\{port\}\}", entities["port"], out, flags=re.IGNORECASE)
        if "interface" in entities:
            out = re.sub(r"<interface>|\{\{interface\}\}|<iface>|\{\{iface\}\}", entities["interface"], out, flags=re.IGNORECASE)
        if "wordlist" in entities:
            out = re.sub(r"<wordlist>|\{\{wordlist\}\}", entities["wordlist"], out, flags=re.IGNORECASE)
        elif re.search(r"<wordlist>|\{\{wordlist\}\}", out, re.IGNORECASE):
            out = re.sub(r"<wordlist>|\{\{wordlist\}\}", "/usr/share/wordlists/rockyou.txt", out, flags=re.IGNORECASE)
        if "output" in entities:
            out = re.sub(r"<output>|\{\{output\}\}|<file>|\{\{file\}\}", entities["output"], out, flags=re.IGNORECASE)
        return out

    def _build_tool_bundle(self, tool, query=None):
        """Create a complete answer bundle for a tool."""
        best = None
        if query:
            best = self._best_command_match(tool, query)
        if not best and tool.get("commands"):
            best = tool["commands"][0]

        ready_command = None
        explanation = None
        if best:
            entities = self._extract_entities(query or "")
            ready_command = self._substitute_placeholders(best["command"], entities)
            if ready_command != best["command"]:
                explanation = "I substituted values from your request into the template."

        bundle = {
            "type": "bundle",
            "tool": tool,
            "command": best,
            "ready_command": ready_command or (best["command"] if best else ""),
            "explanation": explanation,
            "examples": tool.get("examples", [])[:4],
            "commands": tool.get("commands", [])[:5],
            "flags": tool.get("flags", [])[:5],
            "install": tool.get("install", ""),
            "related": self._get_related_tools(tool, n=3),
        }
        return bundle

    def _get_related_tools(self, tool, n=3):
        """Suggest related tools based on category and command-task overlap."""
        if not tool:
            return []
        category = tool.get("category", "")
        name = tool["name"].lower()
        candidates = []
        # Same category, excluding the tool itself
        for t in self.tools:
            if t["name"].lower() == name:
                continue
            if t.get("category") == category:
                candidates.append(t)
        # Prefer tools with at least one command, so suggestions are useful
        candidates = [t for t in candidates if t.get("commands")] + candidates
        seen = set()
        related = []
        for t in candidates:
            if t["name"].lower() in seen:
                continue
            seen.add(t["name"].lower())
            related.append({"name": t["name"], "category": t.get("category", "")})
            if len(related) >= n:
                break
        return related

    def _search_kb(self, query):
        query_norm = self._normalize_task_query(query)
        words = set([w for w in query_norm.split() if w not in EXTRACTION_STOPWORDS])
        results = []
        for tool in self.tools:
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

            name = tool.get("name", "").lower()
            score = 0
            for word in words:
                if word == name:
                    score += 10
                elif name.startswith(word) or name.endswith(word):
                    score += 5
                elif word in name.split("-"):
                    score += 3
                elif word in text:
                    score += 1
            if score > 0:
                results.append((score, tool))
        results.sort(key=lambda x: (x[0], x[1]["name"]), reverse=True)
        return [t for _, t in results[:5]]

    def _suggest_tool_names(self, text, max_suggestions=3):
        """Return close tool-name matches for typo'd or unknown tool words."""
        norm = self._normalize_task_query(text)
        candidates = []
        for token in norm.split():
            if len(token) < 3 or token in EXTRACTION_STOPWORDS:
                continue
            for m in get_close_matches(token, self.tool_names, n=3, cutoff=0.75):
                ratio = SequenceMatcher(None, token, m).ratio()
                if ratio >= 0.75:
                    candidates.append((ratio, m))
        candidates.sort(key=lambda x: x[0], reverse=True)
        seen = set()
        out = []
        for _, name in candidates:
            if name not in seen:
                seen.add(name)
                out.append(name)
                if len(out) >= max_suggestions:
                    break
        return out

    def _smart_fallback(self, text):
        results = self._search_kb(text)
        if results:
            return {"type": "search", "query": text, "tools": results}
        suggestions = self._suggest_tool_names(text)
        if suggestions:
            did_you_mean = ", ".join(suggestions)
            return {
                "type": "unknown",
                "text": (
                    "I'm not sure I have a command for that. Did you mean one of these tools? "
                    f"{did_you_mean}. Try asking for a tool by name or a task like 'scan ports'."
                ),
            }
        return {
            "type": "unknown",
            "text": (
                "I'm not sure I have a command for that. Try asking for a tool by name, "
                "a task like 'scan ports', or type 'help' for examples. I can also explain "
                "flags, show examples, and guide you through tools."
            ),
        }

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

        # Small talk / general questions first so casual words don't look like tools
        chitchat = self._detect_chitchat(text)
        if chitchat:
            return {"type": "chitchat", "text": chitchat}

        general = self._detect_general(text)
        if general:
            return {"type": "general", "text": general}

        if re.search(r"\brandom command\b", text.lower()):
            tool = random.choice(self.tools)
            commands = tool.get("commands", [])
            if commands:
                cmd = random.choice(commands)
                self._update_context(
                    tool_name=tool["name"],
                    command=cmd["command"],
                    response=f"{tool['name']}: {cmd['task']}",
                    intent="command",
                )
                return {"type": "command", "tool": tool, "command": cmd}
            self._update_context(tool_name=tool["name"], intent="describe")
            return {"type": "describe", "tool": tool}

        intent = self._detect_intent(text)
        tool_name = self._extract_tool(text)

        # Inherit the last discussed tool for follow-up questions like "show examples"
        # Note: describe is handled by the pronoun-only fallback so a random
        # "what is ..." question doesn't inherit the previous tool.
        context_intents = {"options", "examples", "install", "all_commands", "guide"}
        if not tool_name and self.last_tool_name and intent in context_intents:
            tool_name = self.last_tool_name

        # Handle ambiguous "this tool" / "it" requests that carry no explicit intent
        if self._uses_pronoun(text) and self.last_tool_name and not intent:
            intent = "describe"

        # If the user pasted a command line, explain it instead of running it.
        # We skip this when they explicitly asked to execute ("run it", "execute ...").
        if intent != "execute" and self._is_command_input(text):
            explanation = self._explain_command(text)
            if explanation:
                self._update_context(tool_name=explanation["tool"]["name"], intent="command_explain")
                return {"type": "command_explain", **explanation}

        if intent == "exit":
            return {"type": "exit", "text": "Goodbye! Stay safe out there."}

        if intent == "greet":
            self._update_context(intent="greet")
            return {
                "type": "greet",
                "text": (
                    "Hello! I'm LinuxBot, your offline command helper. "
                    "Ask me about any tool, command, or option. Type 'help' to see examples."
                ),
            }

        if intent == "help":
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
                    "  'explain nmap -sS -p- <target>' (break down a command)\n"
                    "  'what does this command do: sudo apt update'\n"
                    "  'show examples for nmap'\n"
                    "  'all commands for nmap'\n"
                    "  'how to install nmap'\n"
                    "  'guide me through nmap' or 'how to use nmap'\n"
                    "  'list tools' or 'list networking tools'\n"
                    "  'search sql injection'\n"
                    "  'save last' (save the last command shown)\n"
                    "  'run it' (execute the last command with confirmation)\n"
                    "  'give me a random command'\n\n"
                    "You can ask in normal English, e.g. 'how do I check open ports?' or 'what is Linux?'.\n"
                    "Press TAB while typing to autocomplete tool names."
                ),
            }

        if intent == "list":
            category = self._extract_category(text)
            if category:
                tools = [t for t in self.tools if t.get("category", "").lower() == category]
                return {"type": "list", "tools": tools, "category": category}
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

        if intent == "abuse":
            # Strip only the generic request word; keep words like "suid" or
            # "privilege escalation" because they help score GTFOBins entries.
            query = re.sub(
                r"(?:^|\s)gtfobins(?:\s|$)", " ", text, flags=re.IGNORECASE
            ).strip()
            results = self._search_gtfobins(query)
            if not results:
                return {
                    "type": "unknown",
                    "text": "I couldn't find a GTFOBins technique for that. Try 'gtfobins tar shell' or 'suid binary abuse'.",
                }
            return {"type": "search", "query": query or "GTFOBins", "tools": results}

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
            # If the user asked to explain a full command line, break it down.
            if self._is_command_input(text):
                explanation = self._explain_command(text)
                if explanation:
                    self._update_context(tool_name=explanation["tool"]["name"], intent="command_explain")
                    return {"type": "command_explain", **explanation}
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

        if intent == "guide":
            if not tool_name:
                return {"type": "guide", "text": "Which tool do you want a guide for? Try: 'guide me through nmap' or 'how to use nmap'."}
            tool = self._find_tool(tool_name)
            if tool:
                self._update_context(tool_name=tool["name"], intent="guide")
                return {"type": "guide", "tool": tool}
            return {"type": "guide", "text": f"I don't know a tool named '{tool_name}'."}

        if intent == "describe":
            if not tool_name:
                # Maybe the user is asking about flags like "what is -l"
                flags = self._explain_flags(text)
                if flags:
                    self._update_context(intent="explain")
                    return {"type": "explain", "flags": flags}
                # Try the tldr dataset for common commands (e.g. "what is cat")
                tldr_tool = self._extract_tldr_tool(text)
                if tldr_tool:
                    self._update_context(tool_name=tldr_tool["name"], intent="tldr")
                    return {"type": "tldr", "tool": tldr_tool}
                return self._smart_fallback(text)
            tool = self._find_tool(tool_name)
            if tool:
                self._update_context(tool_name=tool["name"], intent="describe")
                return {"type": "describe", "tool": tool}
            return {"type": "describe", "text": f"I don't know a tool named '{tool_name}'."}

        if intent == "bundle":
            if not tool_name:
                return {
                    "type": "bundle",
                    "text": "Which tool do you want a complete guide for? Try: 'tell me everything about nmap'.",
                }
            tool = self._find_tool(tool_name)
            if tool:
                self._update_context(tool_name=tool["name"], intent="bundle")
                return self._build_tool_bundle(tool, query=text)
            # Try tldr for common commands
            tldr_tool = self._find_tldr_tool(tool_name)
            if tldr_tool:
                self._update_context(tool_name=tldr_tool["name"], intent="bundle")
                return {"type": "tldr", "tool": tldr_tool}
            return {"type": "bundle", "text": f"I don't know a tool named '{tool_name}'."}

        # Default intent is command/task lookup
        if tool_name:
            tool = self._find_tool(tool_name)
            if tool:
                cmd = self._best_command_match(tool, text)
                if cmd:
                    entities = self._extract_entities(text)
                    ready_command = self._substitute_placeholders(cmd["command"], entities)
                    self._update_context(
                        tool_name=tool["name"],
                        command=ready_command if ready_command else cmd["command"],
                        response=f"{tool['name']}: {cmd['task']}",
                        intent="command",
                    )
                    return {
                        "type": "command",
                        "tool": tool,
                        "command": cmd,
                        "ready_command": ready_command,
                        "related": self._get_related_tools(tool, n=3),
                    }
                # If the user started with the tool name, show all its commands
                # rather than guessing a different tool from the rest of the query.
                normalized_words = self._normalize(text).split()
                if normalized_words and (normalized_words[0] == tool_name or normalized_words[0] in TOOL_ALIASES):
                    self._update_context(tool_name=tool["name"], intent="all_commands")
                    return {"type": "all_commands", "tool": tool}

                # If a longer query mentions a tool elsewhere, the user may be
                # describing a task using that tool name (e.g. "brute force ssh").
                if len(text) >= 14:
                    cmd_matches = self._find_command_by_task(text, top_n=3)
                    if cmd_matches and cmd_matches[0][0] >= 30:
                        score, t, c = cmd_matches[0]
                        entities = self._extract_entities(text)
                        ready_command = self._substitute_placeholders(c["command"], entities)
                        self._update_context(
                            tool_name=t["name"],
                            command=ready_command if ready_command else c["command"],
                            response=f"{t['name']}: {c['task']}",
                            intent="command",
                        )
                        return {
                            "type": "command",
                            "tool": t,
                            "command": c,
                            "ready_command": ready_command,
                            "related": self._get_related_tools(t, n=3),
                        }

                # If no good command match but tool mentioned, show all commands
                self._update_context(tool_name=tool["name"], intent="all_commands")
                return {"type": "all_commands", "tool": tool}

        # Try an exact tldr-pages match before fuzzy task search. This gives
        # clean answers for common commands like "tar", "sort", "cat", etc.
        tldr_tool = self._extract_tldr_tool(text)
        if tldr_tool:
            self._update_context(tool_name=tldr_tool["name"], intent="tldr")
            return {"type": "tldr", "tool": tldr_tool}

        # Try to find a command by task description even when tool name isn't mentioned
        cmd_matches = self._find_command_by_task(text, top_n=3)
        if cmd_matches:
            score, tool, cmd = cmd_matches[0]
            entities = self._extract_entities(text)
            ready_command = self._substitute_placeholders(cmd["command"], entities)
            self._update_context(
                tool_name=tool["name"],
                command=ready_command if ready_command else cmd["command"],
                response=f"{tool['name']}: {cmd['task']}",
                intent="command",
            )
            return {
                "type": "command",
                "tool": tool,
                "command": cmd,
                "ready_command": ready_command,
                "related": self._get_related_tools(tool, n=3),
            }

        # Fallback to the offline tldr-pages dataset for keyword searches
        # e.g. "find large files", "copy preserving permissions"
        tldr_results = self._search_tldr(text)
        if tldr_results:
            return {"type": "search", "query": text, "tools": tldr_results}

        # Fallback to the offline GTFOBins dataset for privilege-escalation
        # and binary abuse context, e.g. "gtfobins tar shell".
        gtfo_results = self._search_gtfobins(text)
        if gtfo_results:
            return {"type": "search", "query": text, "tools": gtfo_results}

        # Smart fallback: search main KB, then suggest help
        return self._smart_fallback(text)

    def _extract_tldr_tool(self, text):
        """Return a tldr entry if the query looks like a simple common-command request.

        Only the first meaningful word is considered, so a query like
        'transfer a file' does not accidentally match the `file` tool.
        """
        norm = self._normalize_intent_query(text)
        words = [w for w in norm.split() if w not in EXTRACTION_STOPWORDS and len(w) > 1]
        if not words:
            return None
        word = words[0]
        entry = self._find_tldr_tool(word)
        if entry and not self._find_tool(word):
            return entry
        return None

    def get_favorites(self):
        return self.favorites
