#!/usr/bin/env python3
"""Extract EXAMPLES sections from local man pages.

This is an OPTIONAL build-time helper. It requires `man` to be installed and
will only run when invoked directly; LinuxBot does not need it at runtime.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUT_FILE = DATA_DIR / "man_kb.json"


def run(cmd, input=None):
    try:
        return subprocess.run(
            cmd,
            input=input,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except Exception as e:
        return subprocess.CompletedProcess(cmd, -1, "", str(e))


def extract_examples(page_text):
    """Return the EXAMPLES section of a man page as a list of example commands."""
    examples = []
    in_examples = False
    buffer = []
    for line in page_text.splitlines():
        if re.match(r"^\s*EXAMPLES?\s*$", line):
            in_examples = True
            buffer = []
            continue
        if in_examples and re.match(r"^[A-Z][A-Z\s]+$", line.strip()):
            break
        if in_examples:
            buffer.append(line)

    if not buffer:
        return examples

    # Join and look for indented command lines
    block = "\n".join(buffer)
    for line in block.splitlines():
        stripped = line.strip()
        # Lines that look like shell examples: indented, start with $ or command
        if stripped.startswith(("$ ", "# ")):
            examples.append(stripped[2:].strip())
        elif re.match(r"^\s{4,}\S+", line) and not stripped.startswith(("-", "•")):
            examples.append(stripped)
    return examples


def fetch_man_page(tool):
    if shutil.which("man") is None:
        return None
    res = run(["man", tool])
    if res.returncode != 0 or not res.stdout:
        return None
    # Strip formatting using `col -b` if available
    if shutil.which("col"):
        res = run(["col", "-b"], input=res.stdout)
    return res.stdout


def build_man_kb(tools=None):
    if tools is None:
        # Default: try to extract examples for tools already in the main KB
        kb_path = DATA_DIR / "knowledge_base.json"
        if kb_path.exists():
            data = json.loads(kb_path.read_text(encoding="utf-8"))
            tools = [t["name"] for t in data.get("tools", [])]
        else:
            tools = []

    entries = []
    for name in tools:
        text = fetch_man_page(name)
        if not text:
            continue
        examples = extract_examples(text)
        if not examples:
            continue
        entries.append(
            {
                "name": name,
                "category": "man",
                "description": f"Examples extracted from the man page for {name}.",
                "install": f"usually pre-installed; see man {name}",
                "commands": [
                    {"task": "man example", "command": ex, "description": "man page example"}
                    for ex in examples[:10]
                ],
                "flags": [],
                "examples": examples[:10],
                "safety_notes": "Only run commands you understand and are authorized to execute.",
            }
        )

    entries.sort(key=lambda x: x["name"])
    DATA_DIR.mkdir(exist_ok=True)
    OUT_FILE.write_text(json.dumps({"tools": entries}, indent=2), encoding="utf-8")
    print(f"Wrote {len(entries)} man-page entries to {OUT_FILE}")


if __name__ == "__main__":
    tools = sys.argv[1:] or None
    build_man_kb(tools)
