#!/usr/bin/env bash
# Complete All-In-One Installer for Omarchy Boot & Secure Boot Manager (azterisk.boot)
# Author: Azteriisk

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ID="azterisk.boot"
PLUGINS_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins"
TARGET_DIR="$PLUGINS_DIR/$PLUGIN_ID"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
MENU_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/extensions/omarchy-menu.jsonc"

echo "⚡ Installing Omarchy Boot & Secure Boot Manager..."

# 1. Ensure target directories exist
mkdir -p "$PLUGINS_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$APPS_DIR"
mkdir -p "$(dirname "$MENU_CONFIG")"

# 2. Copy files to plugins directory if running outside
if [ "$SCRIPT_DIR" != "$TARGET_DIR" ]; then
  mkdir -p "$TARGET_DIR"
  cp -a "$SCRIPT_DIR/manifest.json" \
        "$SCRIPT_DIR/Service.qml" \
        "$SCRIPT_DIR/omarchy-boot.desktop" \
        "$SCRIPT_DIR/scripts" \
        "$SCRIPT_DIR/install.sh" \
        "$SCRIPT_DIR/uninstall.sh" \
        "$SCRIPT_DIR/README.md" "$TARGET_DIR/"
  if [ -d "$SCRIPT_DIR/windows" ]; then
    cp -a "$SCRIPT_DIR/windows" "$TARGET_DIR/"
  fi
fi

# 3. Ensure scripts are executable & symlink CLI binaries
chmod +x "$TARGET_DIR/scripts/omarchy-boot"
chmod +x "$TARGET_DIR/scripts/omarchy-boot-gui"
ln -sf "$TARGET_DIR/scripts/omarchy-boot" "$BIN_DIR/omarchy-boot"
ln -sf "$TARGET_DIR/scripts/omarchy-boot-gui" "$BIN_DIR/omarchy-boot-gui"
echo "  ✓ Symlinked omarchy-boot to $BIN_DIR/omarchy-boot"
echo "  ✓ Symlinked omarchy-boot-gui to $BIN_DIR/omarchy-boot-gui"

# 4. Install desktop application entry
cp "$TARGET_DIR/omarchy-boot.desktop" "$APPS_DIR/omarchy-boot.desktop"
update-desktop-database "$APPS_DIR" 2>/dev/null || true
echo "  ✓ Installed application entry in $APPS_DIR/omarchy-boot.desktop"

# 5. Install polkit policy if root/writable
if [ -w /usr/share/polkit-1/actions ]; then
  cp "$TARGET_DIR/scripts/org.omarchy.bootmanager.policy" /usr/share/polkit-1/actions/ 2>/dev/null || true
  echo "  ✓ Installed polkit policy in /usr/share/polkit-1/actions/"
fi

# 6. Integrate into Omarchy Menu (omarchy-menu.jsonc)
echo "  ⚙ Configuring Omarchy Menu extensions for Boot Manager..."
python3 - << 'PYEOF'
import re
from pathlib import Path

menu_file = Path.home() / ".config" / "omarchy" / "extensions" / "omarchy-menu.jsonc"

entries_to_add = {
    "setup.boot": {
        "icon": "󰌿",
        "label": "Boot & Secure Boot",
        "description": "Windows dual-boot & Secure Boot configuration",
        "aliases": ["boot", "secure-boot", "windows-boot", "bios-setup"],
        "action": "omarchy-boot gui"
    },
    "system.reboot-windows": {
        "icon": "",
        "label": "Reboot into Windows",
        "description": "One-shot boot directly into Windows for next boot",
        "aliases": ["reboot-windows", "windows"],
        "action": "omarchy-boot reboot windows"
    },
    "system.reboot-bios": {
        "icon": "󰒔",
        "label": "Reboot into BIOS Setup",
        "description": "Reboot straight to motherboard UEFI firmware",
        "aliases": ["reboot-bios", "bios", "uefi"],
        "action": "omarchy-boot reboot bios"
    }
}

if menu_file.exists():
    content = menu_file.read_text(encoding="utf-8")
else:
    content = "{\n}\n"

# Remove existing boot manager block if already present to avoid duplicates
block_marker_start = "// --- BEGIN OMARCHY BOOT MANAGER ---"
block_marker_end = "// --- END OMARCHY BOOT MANAGER ---"

if block_marker_start in content and block_marker_end in content:
    pattern = re.compile(rf"{re.escape(block_marker_start)}.*?{re.escape(block_marker_end)}\n?", re.DOTALL)
    content = pattern.sub("", content)

# Format the JSONC entries block
lines = [
    f"  {block_marker_start}",
    '  "setup.boot": {"icon": "󰌿", "label": "Boot & Secure Boot", "description": "Windows dual-boot & Secure Boot configuration", "aliases": ["boot", "secure-boot", "windows-boot", "bios-setup"], "action": "omarchy-boot gui"},',
    '  "system.reboot-windows": {"icon": "", "label": "Reboot into Windows", "description": "One-shot boot directly into Windows for next boot", "aliases": ["reboot-windows", "windows"], "action": "omarchy-boot reboot windows"},',
    '  "system.reboot-bios": {"icon": "󰒔", "label": "Reboot into BIOS Setup", "description": "Reboot straight to motherboard UEFI firmware", "aliases": ["reboot-bios", "bios", "uefi"], "action": "omarchy-boot reboot bios"}',
    f"  {block_marker_end}"
]
insertion = "\n".join(lines) + "\n"

# Insert before the last closing bracket
r_bracket = content.rfind("}")
if r_bracket != -1:
    new_content = content[:r_bracket].rstrip()
    if new_content and not new_content.endswith("{") and not new_content.endswith(","):
        new_content += ",\n"
    else:
        new_content += "\n"
    new_content += insertion + "}\n"
else:
    new_content = "{\n" + insertion + "}\n"

menu_file.write_text(new_content, encoding="utf-8")
print("     [OK] Injected Boot & Secure Boot entries into omarchy-menu.jsonc")
PYEOF

# 6. Reload Omarchy shell / menu if running
if command -v omarchy >/dev/null 2>&1; then
  omarchy restart shell 2>/dev/null || true
fi

echo ""
echo "======================================================================"
echo "  ⚡ Omarchy Boot & Secure Boot Manager installed successfully!"
echo "======================================================================"
echo "  How to access:"
echo "    • Omarchy Menu -> Setup -> 'Boot & Secure Boot'"
echo "    • Omarchy Menu -> System -> 'Reboot into Windows' & 'Reboot into BIOS'"
echo "    • App Launcher: search 'boot', 'windows', 'secure boot', 'anticheat'"
echo "    • Terminal CLI: run 'omarchy-boot status' or 'omarchy-boot setup'"
echo "    • Graphical App: run 'omarchy-boot gui'"
echo "======================================================================"
