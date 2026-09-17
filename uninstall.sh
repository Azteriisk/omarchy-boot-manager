#!/usr/bin/env bash
# Uninstaller for Omarchy Boot & Secure Boot Manager (azterisk.boot)
# Author: Azteriisk

set -euo pipefail

PLUGIN_ID="azterisk.boot"
TARGET_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins/$PLUGIN_ID"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
MENU_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/extensions/omarchy-menu.jsonc"

echo "Removing $PLUGIN_ID..."

# 1. Remove symlinks and desktop entry
rm -f "$BIN_DIR/omarchy-boot"
rm -f "$BIN_DIR/omarchy-boot-gui"
rm -f "$APPS_DIR/omarchy-boot.desktop"
update-desktop-database "$APPS_DIR" 2>/dev/null || true

# 2. Clean menu entries from omarchy-menu.jsonc
if [[ -f "$MENU_CONFIG" ]]; then
  echo "  ⚙ Reverting entries in omarchy-menu.jsonc..."
  python3 - << 'PYEOF'
import re
from pathlib import Path

menu_file = Path.home() / ".config" / "omarchy" / "extensions" / "omarchy-menu.jsonc"
if menu_file.exists():
    content = menu_file.read_text(encoding="utf-8")
    block_marker_start = "// --- BEGIN OMARCHY BOOT MANAGER ---"
    block_marker_end = "// --- END OMARCHY BOOT MANAGER ---"

    if block_marker_start in content and block_marker_end in content:
        pattern = re.compile(rf"{re.escape(block_marker_start)}.*?{re.escape(block_marker_end)}\n?", re.DOTALL)
        content = pattern.sub("", content)
        menu_file.write_text(content, encoding="utf-8")
        print("     [OK] Removed Boot Manager entries from omarchy-menu.jsonc")
PYEOF
fi

# 3. Remove plugin directory
if [[ -d "$TARGET_DIR" ]]; then
  rm -rf "$TARGET_DIR"
fi

if command -v omarchy >/dev/null 2>&1; then
  omarchy restart shell 2>/dev/null || true
fi

echo "Omarchy Boot & Secure Boot Manager uninstalled successfully."
