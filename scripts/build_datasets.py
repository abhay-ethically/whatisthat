#!/usr/bin/env python3
"""Fetch and parse offline datasets (tldr-pages, GTFOBins) into local JSON KBs.

Run this script when you want to refresh the bundled knowledge bases.
It requires an internet connection during the build step; the resulting
JSON files let the bot work fully offline afterwards.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TLDR_OUT = DATA_DIR / "tldr_kb.json"
GTFO_OUT = DATA_DIR / "gtfobins_kb.json"


def run(cmd, cwd=None):
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def parse_tldr_page(path):
    """Parse a tldr markdown page into a tool entry."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines:
        return None

    # First non-empty line is the title: '# command-name'
    title = lines[0].lstrip("#").strip()
    name = title.split()[0].lower() if title else path.stem

    # Collect description and examples
    description = []
    examples = []
    current_desc = None

    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            current_desc = stripped[2:].strip()
            description.append(current_desc)
        elif stripped.startswith("`") and stripped.endswith("`"):
            cmd_text = stripped.strip("`").strip()
            examples.append(cmd_text)
        # Ignore other lines

    if not examples:
        return None

    return {
        "name": name,
        "category": "common",
        "description": " ".join(description) or f"Common usage examples for {name}.",
        "install": f"sudo apt install {name}",
        "commands": [
            {
                "task": f"example: {ex.split()[0] if ex else 'run'}",
                "command": ex,
                "description": "tldr example",
            }
            for ex in examples[:8]
        ],
        "flags": [],
        "examples": examples[:12],
        "safety_notes": "Only run commands you understand and are authorized to execute.",
    }


def build_tldr():
    pages_dirs = ["common", "linux"]
    entries = []
    with tempfile.TemporaryDirectory(prefix="linuxbot_tldr_") as tmp:
        clone_dir = Path(tmp) / "tldr"
        run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "https://github.com/tldr-pages/tldr.git",
                str(clone_dir),
            ]
        )
        for platform in pages_dirs:
            platform_dir = clone_dir / "pages" / platform
            if not platform_dir.exists():
                continue
            for path in platform_dir.iterdir():
                if path.suffix != ".md":
                    continue
                entry = parse_tldr_page(path)
                if entry:
                    entry["category"] = platform
                    entries.append(entry)
    entries.sort(key=lambda x: x["name"])
    TLDR_OUT.write_text(json.dumps({"tools": entries}, indent=2), encoding="utf-8")
    print(f"Wrote {len(entries)} tldr entries to {TLDR_OUT}")


def _read_yaml_literal_block(lines, start_idx):
    """Read a YAML literal block (| or |-) starting at lines[start_idx].

    Returns (block_text, next_index).
    """
    if start_idx >= len(lines):
        return "", start_idx
    first_content = lines[start_idx]
    if not first_content.strip():
        return "", start_idx + 1
    base_indent = len(first_content) - len(first_content.lstrip(" "))
    content_lines = []
    i = start_idx
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            content_lines.append("")
            i += 1
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent < base_indent:
            break
        content_lines.append(line[base_indent:])
        i += 1
    return "\n".join(content_lines).rstrip(), i


def parse_gtfo_page(path):
    """Parse a GTFOBins Jekyll page into a tool entry."""
    text = path.read_text(encoding="utf-8")
    name = path.stem.lower()

    # GTFOBins files begin with an empty frontmatter (just `---`), so the body
    # is everything after the first separator.
    if text.startswith("---"):
        body = text.split("---", 1)[1]
    else:
        body = text

    commands = []
    current_function = None
    current_entry = None

    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Function names are top-level keys under functions: at 2-space indent
        if (
            stripped.endswith(":")
            and not stripped.startswith("-")
            and not stripped.startswith("functions")
            and line.startswith("  ")
            and not line.startswith("   ")
        ):
            if current_entry and current_function:
                commands.append(current_entry)
                current_entry = None
            current_function = stripped[:-1].strip()
            i += 1
            continue

        # New list item under a function
        if stripped.startswith("- code:"):
            if current_entry and current_function:
                commands.append(current_entry)
            current_entry = {"task": current_function, "description": "", "tags": []}
            i += 1
            current_entry["command"], i = _read_yaml_literal_block(lines, i)
            continue

        if stripped.startswith("comment:"):
            i += 1
            comment, i = _read_yaml_literal_block(lines, i)
            if current_entry:
                current_entry["description"] = comment
            continue

        # Skip contexts, version, sender, receiver, etc.
        i += 1

    if current_entry and current_function:
        commands.append(current_entry)

    if not commands:
        return None

    # Deduplicate identical commands
    seen = set()
    unique = []
    for c in commands:
        key = (c["task"], c["command"])
        if key not in seen:
            seen.add(key)
            unique.append(c)

    return {
        "name": name,
        "category": "gtfobins",
        "description": (
            f"GTFOBins abuse techniques for {name}: privilege escalation, "
            "file reads/writes, shells, uploads/downloads, and more."
        ),
        "install": f"usually pre-installed; see https://gtfobins.github.io/gtfobins/{name}/",
        "commands": unique[:12],
        "flags": [],
        "examples": [c["command"] for c in unique[:8]],
        "safety_notes": "GTFOBins techniques are used for privilege escalation and post-exploitation. Only use on systems you own or are explicitly authorized to test.",
    }


def build_gtfobins():
    entries = []
    with tempfile.TemporaryDirectory(prefix="linuxbot_gtfo_") as tmp:
        clone_dir = Path(tmp) / "GTFOBins.github.io"
        run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "https://github.com/GTFOBins/GTFOBins.github.io.git",
                str(clone_dir),
            ]
        )
        gtfobins_dir = clone_dir / "_gtfobins"
        if not gtfobins_dir.exists():
            print(f"GTFOBins directory not found: {gtfobins_dir}")
            return
        for path in gtfobins_dir.iterdir():
            # GTFOBins binary pages have no extension
            if path.is_file() and not path.suffix and not path.name.startswith("."):
                entry = parse_gtfo_page(path)
                if entry:
                    entries.append(entry)
    entries.sort(key=lambda x: x["name"])
    GTFO_OUT.write_text(json.dumps({"tools": entries}, indent=2), encoding="utf-8")
    print(f"Wrote {len(entries)} GTFOBins entries to {GTFO_OUT}")


def main():
    DATA_DIR.mkdir(exist_ok=True)
    print("Building tldr-pages knowledge base...")
    try:
        build_tldr()
    except subprocess.CalledProcessError as e:
        print(f"tldr build failed: {e}")
    print("\nBuilding GTFOBins knowledge base...")
    try:
        build_gtfobins()
    except subprocess.CalledProcessError as e:
        print(f"GTFOBins build failed: {e}")
    print("\nDone. You can commit the generated JSON files to keep the bot offline.")


if __name__ == "__main__":
    main()
