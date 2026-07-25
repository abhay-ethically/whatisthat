#!/usr/bin/env bash
set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/share/linuxbot}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
WRAPPER="$BIN_DIR/linuxbot"

echo "Installing LinuxBot from $REPO_DIR to $INSTALL_DIR..."

mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# Sync source files, preserving data/
rsync -av --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
    "$REPO_DIR/" "$INSTALL_DIR/" >/dev/null 2>&1 || {
    # fallback if rsync unavailable
    cp -r "$REPO_DIR/linuxbot.py" "$REPO_DIR/data" "$REPO_DIR/utils" "$REPO_DIR/run.sh" "$INSTALL_DIR/" 2>/dev/null || true
    cp -r "$REPO_DIR/scripts" "$INSTALL_DIR/" 2>/dev/null || true
}

cat > "$WRAPPER" <<EOF
#!/usr/bin/env bash
python3 "$INSTALL_DIR/linuxbot.py" "\$@"
EOF
chmod +x "$WRAPPER"

echo "Installed to $WRAPPER"
echo "Make sure $BIN_DIR is in your PATH."
echo "Run: linuxbot"
