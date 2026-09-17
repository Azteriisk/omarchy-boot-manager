#!/usr/bin/env python3
"""
Limine bootloader configuration manager.
Handles parsing, Windows chainload injection, and default OS selection.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

LIMINE_PATHS = [
    Path("/boot/limine.conf"),
    Path("/boot/limine/limine.conf"),
    Path("/boot/EFI/LIMINE/limine.conf")
]


def find_limine_config() -> Optional[Path]:
    """Finds the active limine.conf on the system."""
    for p in LIMINE_PATHS:
        if p.exists():
            return p
    return Path("/boot/limine.conf")


def read_limine_config(path: Optional[Path] = None) -> Optional[str]:
    """Reads limine.conf safely."""
    cfg_path = path or find_limine_config()
    if not cfg_path:
        return None

    try:
        if cfg_path.exists() and os.access(cfg_path, os.R_OK):
            return cfg_path.read_text(encoding="utf-8")
    except Exception:
        pass

    # Attempt via cat
    try:
        res = subprocess.run(["cat", str(cfg_path)], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            return res.stdout
    except Exception:
        pass

    return None


def has_windows_chainload(content: str) -> bool:
    """Checks if limine.conf already has a Windows efi_chainload entry."""
    if not content:
        return False
    lower = content.lower()
    return "efi_chainload" in lower and "bootmgfw.efi" in lower


def generate_windows_entry(partuuid: str, label: str = "Windows 11") -> str:
    """Formats the standardized Limine efi_chainload block."""
    guid_clean = str(partuuid).strip().lower()
    return f"\n/{label}\n    comment: Boot Windows Boot Manager\n    protocol: efi_chainload\n    image_path: guid({guid_clean}):/EFI/Microsoft/Boot/bootmgfw.efi\n"


def inject_windows_entry(content: str, partuuid: str, label: str = "Windows 11") -> str:
    """Appends or updates the Windows chainload entry in limine.conf content."""
    if has_windows_chainload(content):
        guid_clean = str(partuuid).strip().lower()
        pattern = r"(image_path:\s*guid\()[0-9a-fA-F\-]{36}(\):/EFI/Microsoft/Boot/bootmgfw\.efi)"
        if re.search(pattern, content, re.IGNORECASE):
            return re.sub(pattern, rf"\g<1>{guid_clean}\g<2>", content, flags=re.IGNORECASE)
        return content

    entry = generate_windows_entry(partuuid, label)
    stripped = content.rstrip()
    return f"{stripped}\n{entry}\n"


def add_windows_to_limine(partuuid: str, label: str = "Windows 11") -> Tuple[bool, str]:
    """Safely adds Windows chainload entry to /boot/limine.conf."""
    cfg_path = find_limine_config() or Path("/boot/limine.conf")
    guid_clean = str(partuuid).strip().lower()
    entry_text = generate_windows_entry(guid_clean, label)

    script = f"""set -e
CFG="{cfg_path}"
if [ ! -f "$CFG" ]; then
    echo "limine.conf not found at $CFG"
    exit 1
fi

cp "$CFG" "$CFG.bak-$(date +%s)"

if grep -qi "bootmgfw.efi" "$CFG"; then
    echo "Windows entry already exists in $CFG"
    exit 0
fi

cat << 'LIMEOF' >> "$CFG"
{entry_text}
LIMEOF
echo "Windows entry added successfully to $CFG"
"""

    runner = ["bash", "-c", script]
    if os.geteuid() != 0:
        runner = ["pkexec", "bash", "-c", script]

    try:
        res = subprocess.run(runner, capture_output=True, text=True, check=True)
        return True, res.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, f"Elevation error: {e.stderr.strip() or str(e)}"
    except FileNotFoundError:
        return False, "pkexec is not installed on this system"


if __name__ == "__main__":
    guid = "8a80c1ba-ee7f-4114-929e-cef5b92cf75e"
    print("Sample Windows Limine Entry:")
    print(generate_windows_entry(guid))
