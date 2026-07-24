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
- ✅ Suggests commands with descriptions and safety warnings
- ✅ Explains flags and options
- ✅ Shows examples, all commands, and install steps
- ✅ Searches the knowledge base
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
| List tools | `list tools`, `show tools` |
| Search | `search sql injection`, `find command for wifi` |
| Save command | `save last`, `favorite` |
| Run last command | `run it`, `execute` |
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

All tool data lives in `data/knowledge_base.json`. To add a new tool, copy the JSON schema of an existing tool and change the values:

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
│   ├── knowledge_base.json  # Tool documentation
│   └── favorites.json       # Saved commands (created at runtime)
└── utils/
    ├── matcher.py           # Intent detection and fuzzy matching
    ├── executor.py          # Safe command execution
    └── formatter.py         # Terminal colors
```

## License

This is a local helper tool. Use responsibly and ethically.
