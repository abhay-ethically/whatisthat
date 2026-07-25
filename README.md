# LinuxBot — Offline Linux Command Helper

A fully offline CLI chatbot that helps you remember Linux, networking/recon, and pentest commands. It stores all tool documentation in a local JSON file and uses fuzzy keyword matching to answer questions like:

- "hi i want nmap command to check ports"
- "command to check connected devices in network"
- "describe nmap"
- "how does this tool work"  (uses conversation context)
- "options for it"  (refers back to the last tool)
- "show examples for nmap"
- "all commands for nmap"
- "how to install nmap"
- "explain -sS -p-"
- "list tools"

No internet, no API keys, no model downloads — just Python 3 and a local knowledge base.

## Features

- ✅ Works 100% offline
- ✅ Zero external dependencies (Python standard library only)
- ✅ Conversation context memory — ask about "this tool" or "it"
- ✅ Covers Core Linux, Networking/Recon, and Pentest tools
- ✅ 795+ tool entries, including the full Kali Linux tools list (`data/kali_tools.json`)
- ✅ Suggests commands with descriptions and safety warnings
- ✅ Explains flags and options
- ✅ Shows examples, all commands, install steps, and step-by-step guides
- ✅ Searches the knowledge base
- ✅ Understands normal English: contractions, filler words, and synonyms
- ✅ Category browsing (e.g. `list networking tools`)
- ✅ Suggests "did you mean..." for likely typos
- ✅ Smart fallback when a query isn't a direct match
- ✅ Handles small talk ("hi", "how are you", "who are you") and general tech questions
- ✅ Can suggest a random command on request
- ✅ Saves favorite commands locally
- ✅ Can run suggested commands after explicit confirmation
- ✅ Safety blocklist for dangerous command patterns

## Quick Start

```bash
# From the WebCamm folder
chmod +x run.sh
./run.sh

# Or directly
python3 linuxbot.py
```

## Example Usage

```text
You: hi
LinuxBot: Hello! I'm your offline Linux command helper. Ask me for commands, tool descriptions, flags, or type 'help'.

You: nmap command to check ports
LinuxBot: Tool: nmap (networking)
LinuxBot: Task: scan common ports on a target
LinuxBot: nmap <target>
LinuxBot: Description: Default SYN scan of the top 1000 ports.
⚠️  Only scan networks and hosts you own or have explicit written permission to test.

You: command to check connected devices in network
LinuxBot: Tool: netdiscover (networking)
LinuxBot: Task: discover live hosts on local network
LinuxBot: sudo netdiscover -i eth0 -r 192.168.1.0/24
LinuxBot: Description: Active ARP scan on the given interface and range.

You: save last
LinuxBot: Saved command: nmap <target>

You: run it
LinuxBot: About to execute:
   $ nmap <target>
⚠️  Do you want to run this command? Type 'yes' to confirm, anything else to cancel.
Confirm: no
LinuxBot: Execution cancelled.
```

## What You Can Ask

| Intent | Example |
|--------|---------|
| Greeting | `hi`, `hello` |
| Command for a task | `nmap command to check ports`, `command to transfer file` |
| Describe tool | `describe nmap`, `what is sqlmap`, `how does it work` |
| List options | `options for nmap`, `flags for it` |
| Explain flags | `explain -sS -p-`, `what does -l mean` |
| Show examples | `show examples for nmap` |
| All commands | `all commands for nmap` |
| Install steps | `how to install nmap` |
| Step-by-step guide | `guide me through nmap`, `how to use nmap` |
| List tools | `list tools`, `list networking tools`, `show pentest tools` |
| Search | `search sql injection`, `find command for wifi` |
| Save command | `save last`, `favorite` |
| Run last command | `run it`, `execute` |
| Chat / small talk | `hi`, `how are you`, `what is your name`, `tell me a joke` |
| General knowledge | `what is Linux`, `what is Kali Linux`, `what is a firewall` |
| Random command | `give me a random command` |
| Help | `help`, `usage` |
| Exit | `bye`, `exit`, `quit` |

## Tools Included (v1)

### Core Linux
- `find`, `grep`, `sed`, `awk`, `chmod`, `chown`, `ps`, `kill`, `top`, `tar`, `curl`, `ssh`, `scp`, `rsync`, `ip`, `ss`, `lsof`, `apt`, `systemctl`

### Networking / Recon
- `nmap`, `netdiscover`, `netcat`, `tcpdump`, `tshark`, `arp-scan`, `masscan`, `traceroute`, `ping`, `dig`, `wget`, `dnsrecon`

### Pentest / Security
- `hydra`, `nikto`, `gobuster`, `dirb`, `ffuf`, `sqlmap`, `enum4linux`, `aircrack-ng`, `searchsploit`, `metasploit`, `john`, `hashcat`, `wpscan`

## Extending the Knowledge Base

All tool data lives in `data/knowledge_base.json`. The bot also merges entries from `data/kali_tools.json` (the full Kali Linux package list) and applies curated enrichments from `data/enrichments.json` for popular tools. To add a new tool, copy the JSON schema of an existing tool and change the values:

```json
{
  "name": "your-tool",
  "category": "core",
  "description": "...",
  "install": "sudo apt install your-tool",
  "commands": [
    {"task": "short task name", "command": "your-tool <target>", "description": "..."}
  ],
  "flags": [
    {"flag": "-f", "description": "...", "example": "your-tool -f file"}
  ],
  "examples": ["your-tool example"],
  "safety_notes": "..."
}
```

Run `python3 -m json.tool data/knowledge_base.json` to validate JSON after editing.

## Safety Notes

- LinuxBot **never** runs commands automatically.
- Destructive patterns (e.g., `rm -rf /`, `mkfs`, fork bombs) are blocked.
- If you choose to run a command, you must type `yes` to confirm.
- Many tools in this knowledge base are security tools. **Only use them on systems you own or have explicit written authorization to test.**

## Files

```
WebCamm/
├── linuxbot.py              # Main chatbot
├── run.sh                   # Launcher script
├── README.md                # This file
├── data/
│   ├── knowledge_base.json  # Core tool documentation
│   ├── kali_tools.json      # Full Kali Linux package list
│   ├── enrichments.json     # Curated commands/flags for popular Kali tools
│   └── favorites.json       # Saved commands (created at runtime)
└── utils/
    ├── matcher.py           # Intent detection and fuzzy matching
    ├── executor.py          # Safe command execution
    └── formatter.py         # Terminal colors
```

## License

This is a local helper tool. Use responsibly and ethically.
