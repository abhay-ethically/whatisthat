#!/usr/bin/env python3
"""LinuxBot - offline Linux command helper chatbot."""
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


def print_command_response(response):
    tool = response["tool"]
    cmd = response["command"]
    say(f"Tool: {tool['name']} ({tool['category']})")
    say(f"Task: {cmd['task']}")
    print(f"{bot_name()}: {command(cmd['command'])}")
    say(f"Description: {cmd['description']}")
    if tool.get("safety_notes"):
        say(warning(tool["safety_notes"]))
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


def print_tldr_response(response):
    tool = response["tool"]
    say(f"{tool['name']} ({tool['category']})")
    say(tool.get("description", "No description available."))
    print()
    if tool.get("examples"):
        say("Common examples:")
        for ex in tool["examples"]:
            print(f"  {command(ex)}")
    if tool.get("commands"):
        say("Useful commands:")
        for cmd in tool["commands"][:5]:
            print(f"  {command(cmd['command'])}")
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


def print_examples_response(response):
    tool = response["tool"]
    say(f"Example commands for {tool['name']}:")
    for ex in tool.get("examples", []):
        print(f"  {command(ex)}")
    if not tool.get("examples"):
        say("No examples available in the knowledge base.")
    if tool.get("safety_notes"):
        print()
        print(say_msg(warning(tool["safety_notes"])))


def print_install_response(response):
    tool = response["tool"]
    say(f"How to install {tool['name']}:")
    if tool.get("install"):
        print(f"  {command(tool['install'])}")
    else:
        say("No install information available. It may be pre-installed.")


def print_all_commands_response(response):
    tool = response["tool"]
    say(f"All available commands/tasks for {tool['name']}:")
    for idx, cmd in enumerate(tool.get("commands", []), 1):
        print(f"\n  {idx}. {cmd['task']}")
        print(f"     {command(cmd['command'])}")
        print(f"     {cmd.get('description', '')}")
    if not tool.get("commands"):
        say("No commands documented for this tool yet.")


def print_guide_response(response):
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
