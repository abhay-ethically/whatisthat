#!/usr/bin/env bash
# Quick launcher for LinuxBot
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "${SCRIPT_DIR}/linuxbot.py"
