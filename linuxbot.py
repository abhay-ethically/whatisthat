#!/usr/bin/env python3
"""LinuxBot - offline Linux command helper chatbot."""
import atexit
import readline
import re
import sys
from pathlib import Path

from utils.formatter import (
    bot_name,
    command,
    danger,
    header,
    info,
    say,
    say_msg,
    success,
    warning,
)
from utils.matcher import LinuxBot


def _safety_badge(cmd_text, tool_name=""):
    """Return a short safety label for a command string."""
    text = (cmd_text or "").lower()
    name = (tool_name or "").lower()
    destructive = [
        "rm -rf", "mkfs", "dd if", ":(){:", "fork bomb", "> /dev/sd",
        "format ", "del /", "del \\", "wipefs", " shred", "mkfs.",
        "iptables -f", "shutdown", "reboot", "poweroff", "halt",
    ]
    for pat in destructive:
        if pat in text:
            return danger("DANGEROUS")
    risky = [
        "sudo", "nmap", "masscan", "hydra", "aircrack", "sqlmap", "nikto",
        "gobuster", "dirb", "ffuf", "enum4linux", "john", "hashcat",
        "tcpdump", "wireshark", "tshark", "iptables", "responder",
        "bettercap", "ettercap", "metasploit", "msfvenom", "mimikatz",
        "impersonate", "psexec", "secretsdump", "pass-the-hash",
    ]
    if any(r in text for r in risky) or any(r in name for r in risky):
        return warning("CAUTION")
    return success("SAFE")


def print_command_response(response):
    tool = response["tool"]
    cmd = response["command"]
    ready = response.get("ready_command", cmd["command"])
    say(f"Tool: {tool['name']} ({tool['category']})")
    say(f"Task: {cmd['task']}")
    if ready and ready != cmd["command"]:
        print(f"{bot_name()}: {command(ready)}  {_safety_badge(ready, tool['name'])}")
        print(f"  Template: {command(cmd['command'])}")
    else:
        print(f"{bot_name()}: {command(cmd['command'])}  {_safety_badge(cmd['command'], tool['name'])}")
    say(f"Description: {cmd['description']}")
    if tool.get("safety_notes"):
        say(warning(tool["safety_notes"]))
    related = response.get("related", [])
    if related:
        print(f"\n  {info('Related tools:')} " + ", ".join(r["name"] for r in related))
    print()


def print_options_response(response):
    tool = response["tool"]
    say(f"Options/flags for {tool['name']}:")
    for flag in tool.get("flags", []):
        print(f"  {command(flag['flag'])}")
        print(f"    {flag['description']}")
        if flag.get("example"):
            print(f"    Example: {command(flag['example'])}")
        print()


def print_describe_response(response):
    tool = response["tool"]
    say(f"About {tool['name']}:")
    say(tool.get("description", "No description available."))
    print()
    if tool.get("install"):
        print(say_msg(f"Install: {command(tool['install'])}"))
    print(say_msg(f"Category: {tool['category']}"))
    if tool.get("examples"):
        say("Examples:")
        for ex in tool["examples"]:
            print(f"  {command(ex)}")
    if tool.get("safety_notes"):
        print()
        print(say_msg(warning(tool["safety_notes"])))


def print_list_response(response):
    tools = response["tools"]
    category = response.get("category")
    if category:
        say(f"Tools in '{category}' category:")
    else:
        say("Available tools:")
    categories = {}
    for tool in tools:
        categories.setdefault(tool["category"], []).append(tool["name"])
    for cat in sorted(categories):
        print(f"\n  [{cat}]")
        for name in sorted(categories[cat]):
            print(f"    - {name}")


def print_search_response(response):
    query = response["query"]
    tools = response["tools"]
    if not tools:
        say(f"No tools found matching '{query}'.")
        return
    say(f"Top matches for '{query}':")
    for tool in tools:
        print(f"\n  {command(tool['name'])} ({tool['category']})")
        print(f"    {tool.get('description', '')[:120]}...")


def _clean_tldr_example(text):
    """Convert tldr {{placeholders}} into simpler <placeholders>."""
    return re.sub(r"\{\{(.+?)\}\}", r"<\1>", text)


def print_tldr_response(response):
    if "text" in response:
        say(response["text"])
        return
    tool = response["tool"]
    say(f"{tool['name']} ({tool['category']})")
    desc = _clean_tldr_example(tool.get("description", "No description available."))
    say(desc)
    print()
    if tool.get("examples"):
        say("Common examples:")
        for ex in tool["examples"][:8]:
            print(f"  {command(_clean_tldr_example(ex))}  {_safety_badge(ex, tool['name'])}")
    if tool.get("commands"):
        say("Useful commands:")
        for cmd in tool["commands"][:5]:
            print(f"  {command(_clean_tldr_example(cmd['command']))}  {_safety_badge(cmd['command'], tool['name'])}")
            print(f"    # {cmd.get('description', '')}")
    if tool.get("safety_notes"):
        print()
        print(say_msg(warning(tool["safety_notes"])))


def print_explain_response(response):
    if "text" in response:
        say(response["text"])
        return
    say("Flag explanations:")
    for item in response["flags"]:
        flag = item["flag"]
        desc = item["description"]
        print(f"  {command(flag)}")
        print(f"    {desc}")
        if item.get("example"):
            print(f"    Example: {command(item['example'])}")
        if item.get("tool"):
            print(f"    Source: {item['tool']}")
        print()


def print_command_explain_response(response):
    if "text" in response:
        say(response["text"])
        return
    tool = response["tool"]
    cmd = response["command"]
    say(f"Let me break down this command for you:")
    print(f"  {command(cmd)}")
    print(f"  Tool: {tool['name']} ({tool.get('category', 'common')})")
    print(f"  {tool.get('description', '')[:160]}")
    print()
    say("Piece-by-piece:")
    for ex in response["explanations"]:
        label = ex["type"].capitalize()
        print(f"  {label:9} {command(ex['value'])}  →  {ex['description']}")
    if tool.get("safety_notes"):
        print()
        print(say_msg(warning(tool["safety_notes"])))


def print_bundle_response(response):
    if "text" in response:
        say(response["text"])
        return
    tool = response["tool"]
    say(f"Complete guide for {tool['name']} ({tool.get('category', 'common')})")
    desc = tool.get("description", "No description available.")
    if desc:
        print(f"  {desc[:300]}")
        print()

    best = response.get("command")
    ready = response.get("ready_command")
    if best:
        say("Best command for your request:")
        if ready and ready != best["command"]:
            print(f"  {command(ready)}  {_safety_badge(ready, tool['name'])}")
            print(f"    Template: {command(best['command'])}")
        else:
            print(f"  {command(best['command'])}  {_safety_badge(best['command'], tool['name'])}")
        print(f"    Task: {best.get('task', '')}")
        print(f"    {best.get('description', '')}")
        if response.get("explanation"):
            print(f"    Note: {response['explanation']}")
        print()

    if response.get("examples"):
        say("More examples:")
        for ex in response["examples"]:
            print(f"  {command(ex)}  {_safety_badge(ex, tool['name'])}")
        print()

    if response.get("flags"):
        say("Common flags:")
        for flag in response["flags"]:
            print(f"  {command(flag['flag'])}")
            print(f"    {flag.get('description', '')}")
        print()

    if response.get("install"):
        say("Install:")
        print(f"  {command(response['install'])}")
        print()

    related = response.get("related", [])
    if related:
        print(f"  {info('Related tools:')} " + ", ".join(r["name"] for r in related))

    if tool.get("safety_notes"):
        print()
        print(say_msg(warning(tool["safety_notes"])))


def print_examples_response(response):
    if "text" in response:
        say(response["text"])
        return
    tool = response["tool"]
    say(f"Example commands for {tool['name']}:")
    for ex in tool.get("examples", []):
        print(f"  {command(ex)}  {_safety_badge(ex, tool['name'])}")
    if not tool.get("examples"):
        say("No examples available in the knowledge base.")
    if tool.get("safety_notes"):
        print()
        print(say_msg(warning(tool["safety_notes"])))


def print_install_response(response):
    if "text" in response:
        say(response["text"])
        return
    tool = response["tool"]
    say(f"How to install {tool['name']}:")
    if tool.get("install"):
        print(f"  {command(tool['install'])}")
    else:
        say("No install information available. It may be pre-installed.")


def print_all_commands_response(response):
    if "text" in response:
        say(response["text"])
        return
    tool = response["tool"]
    say(f"All available commands/tasks for {tool['name']}:")
    for idx, cmd in enumerate(tool.get("commands", []), 1):
        print(f"\n  {idx}. {cmd['task']}")
        print(f"     {command(cmd['command'])}  {_safety_badge(cmd['command'], tool['name'])}")
        print(f"     {cmd.get('description', '')}")
    if not tool.get("commands"):
        say("No commands documented for this tool yet.")


def print_guide_response(response):
    if "text" in response:
        say(response["text"])
        return
    tool = response["tool"]
    is_skeleton = tool.get("category") == "kali" and len(tool.get("commands", [])) <= 1
    say(f"Quick guide for {tool['name']}:")
    print()
    say(f"What it is: {tool['description']}")
    print()
    say("Steps to get started:")
    print(f"  1. Install it: {command(tool.get('install', 'usually pre-installed'))}")
    print("  2. Check built-in help to learn flags:")
    print(f"     {command(tool['name'] + ' --help')}")
    commands = tool.get("commands", [])
    if commands and not is_skeleton:
        print("  3. Try these common commands:")
        for cmd in commands[:5]:
            print(f"     {command(cmd['command'])}  # {cmd['task']}")
    else:
        print("  3. Read the manual page:")
        print(f"     {command('man ' + tool['name'])}")
    if tool.get("examples") and not is_skeleton:
        print("  4. Example to copy:")
        for ex in tool["examples"][:3]:
            print(f"     {command(ex)}")
    if is_skeleton:
        print()
        say("Tip: This entry is from the Kali tools list. Add detailed commands to data/knowledge_base.json if you want richer answers.")
    if tool.get("safety_notes"):
        print()
        print(say_msg(warning(tool["safety_notes"])))


def run_bot():
    base_dir = Path(__file__).resolve().parent
    kb_path = base_dir / "data" / "knowledge_base.json"
    data_dir = base_dir / "data"

    if not kb_path.exists():
        print(danger(f"Knowledge base not found at {kb_path}"))
        sys.exit(1)

    bot = LinuxBot(kb_path=kb_path, data_dir=data_dir)

    # Tab completion and command history
    bot._load_tldr_kb()
    completer_names = sorted(set(bot.tool_names) | set(bot._tldr_by_name.keys()))

    def make_completer(names):
        def completer(text, state):
            matches = [n for n in names if n.startswith(text)]
            try:
                return matches[state]
            except IndexError:
                return None
        return completer

    readline.set_completer(make_completer(completer_names))
    readline.parse_and_bind("tab: complete")
    history_file = base_dir / ".linuxbot_history"
    try:
        readline.read_history_file(str(history_file))
    except (FileNotFoundError, OSError):
        pass
    atexit.register(readline.write_history_file, str(history_file))

    tool_count = len(bot.tools)
    print(header("LinuxBot - Offline Linux Command Helper"))
    say(f"Loaded {tool_count} tools locally. No internet needed.")
    say("Type 'help' for examples, 'bye' to exit.")
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            say("Goodbye!")
            break

        if not user_input:
            continue

        response = bot.handle(user_input)
        rtype = response.get("type")

        if rtype == "exit":
            say(response["text"])
            break
        elif rtype == "empty":
            say(response["text"])
        elif rtype == "greet":
            say(response["text"])
        elif rtype == "chitchat":
            say(response["text"])
        elif rtype == "general":
            say(response["text"])
        elif rtype == "help":
            say(response["text"])
        elif rtype == "command":
            print_command_response(response)
        elif rtype == "options":
            print_options_response(response)
        elif rtype == "describe":
            print_describe_response(response)
        elif rtype == "examples":
            print_examples_response(response)
        elif rtype == "install":
            print_install_response(response)
        elif rtype == "all_commands":
            print_all_commands_response(response)
        elif rtype == "guide":
            print_guide_response(response)
        elif rtype == "list":
            print_list_response(response)
        elif rtype == "search":
            print_search_response(response)
        elif rtype == "tldr":
            print_tldr_response(response)
        elif rtype == "explain":
            print_explain_response(response)
        elif rtype == "command_explain":
            print_command_explain_response(response)
        elif rtype == "bundle":
            print_bundle_response(response)
        elif rtype == "save":
            say(response["text"])
        elif rtype == "execute":
            if "command" in response:
                from utils.executor import ask_and_run
                ask_and_run(response["command"])
            else:
                say(response["text"])
        else:
            say(response.get("text", "I'm not sure how to help with that."))


if __name__ == "__main__":
    run_bot()
