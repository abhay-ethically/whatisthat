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


def parse_gtfo_page(path):
    """Parse a GTFOBins markdown page into a tool entry."""
    text = path.read_text(encoding="utf-8")
    # GTFOBins pages have front matter and headings per function
    # We extract the binary name and command blocks under each function.
    name = path.stem.lower()
    commands = []
    current_function = None
    current_desc = None

    for line in text.splitlines():
        if line.startswith("##"):
            heading = line.lstrip("#").strip()
            # Skip the title heading (usually the binary name)
            if heading.lower() != name.lower():
                current_function = heading
                current_desc = heading
        elif line.startswith("```"):
            # skip the marker line
            continue
        elif line.strip().startswith(">") or line.strip().startswith("^"):
            # explanation / continuation of previous block
            continue
        elif line.strip() and line.strip()[0].isalnum() and current_function:
            # this is likely a command line example
            commands.append(
                {
                    "task": current_function,
                    "command": line.strip(),
                    "description": current_desc or "GTFOBins technique",
                }
            )

    if not commands:
        return None

    return {
        "name": name,
        "category": "gtfobins",
        "description": f"Unix binary abuse techniques for {name} (privilege escalation, file reads, shells, etc.).",
        "install": f"usually pre-installed; see GTFOBins for details",
        "commands": commands[:8],
        "flags": [],
        "examples": [c["command"] for c in commands[:8]],
        "safety_notes": "GTFOBins techniques are used for privilege escalation and post-exploitation. Only use on systems you own or are authorized to test.",
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
            if path.suffix != ".md":
                continue
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
