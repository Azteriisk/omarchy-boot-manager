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

    # Attempt via cat (works if user has read access)
    try:
        res = subprocess.run(["cat", str(cfg_path)], capture_output=True, text=True, check=False)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout
    except Exception:
        pass

    # Attempt via sudo -n cat (handles fmask=0077 ESP mounts where /boot is root-only)
    try:
        res = subprocess.run(["sudo", "-n", "cat", str(cfg_path)], capture_output=True, text=True, check=False)
        if res.returncode == 0 and res.stdout.strip():
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


GUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
LABEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}$")


def validate_guid(guid: str) -> str:
    """Validates and returns a canonical lowercase GUID."""
    guid_clean = str(guid).strip().lower()
    if not GUID_PATTERN.match(guid_clean):
        raise ValueError(f"Invalid canonical partition GUID: '{guid}'. Expected standard 8-4-4-4-12 hex format.")
    return guid_clean


def validate_label(label: str) -> str:
    """Validates that a label is single-line, within 64 chars, and contains only safe characters."""
    label_clean = str(label).strip()
    if not LABEL_PATTERN.match(label_clean):
        raise ValueError(
            f"Invalid label: '{label}'. Must be 1-64 characters starting with alphanumeric and containing only letters, numbers, spaces, hyphens, underscores, or dots."
        )
    return label_clean


def generate_windows_entry(partuuid: str, label: str = "Windows 11") -> str:
    """Formats the standardized Limine efi_chainload block."""
    guid_clean = validate_guid(partuuid)
    label_clean = validate_label(label)
    return f"\n/{label_clean}\n    comment: Boot Windows Boot Manager\n    protocol: efi_chainload\n    image_path: guid({guid_clean}):/EFI/Microsoft/Boot/bootmgfw.efi\n"


def inject_windows_entry(content: str, partuuid: str, label: str = "Windows 11") -> str:
    """Appends or updates the Windows chainload entry in limine.conf content."""
    guid_clean = validate_guid(partuuid)
    label_clean = validate_label(label)
    if has_windows_chainload(content):
        pattern = r"(image_path:\s*guid\()[0-9a-fA-F\-]{36}(\):/EFI/Microsoft/Boot/bootmgfw\.efi)"
        if re.search(pattern, content, re.IGNORECASE):
            return re.sub(pattern, rf"\g<1>{guid_clean}\g<2>", content, flags=re.IGNORECASE)
        return content

    entry = generate_windows_entry(guid_clean, label_clean)
    stripped = content.rstrip()
    return f"{stripped}\n{entry}\n"


LIMINE_APPEND_HELPER = """
import sys, re, shutil, time
from pathlib import Path

GUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
LABEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}$")

if len(sys.argv) < 4:
    sys.exit("Usage: helper <cfg_path> <guid> <label>")

cfg = Path(sys.argv[1]).resolve()
guid = sys.argv[2].strip().lower()
label = sys.argv[3].strip()

# Reject unexpected file targets (must be named limine.conf in /boot or /efi)
is_test_mode = Path(cfg).name == "limine.conf" and bool(importlib := __import__("os").environ.get("_OMARCHY_BOOT_TEST_PATH"))
if cfg.name != "limine.conf" or (not is_test_mode and not any(str(cfg).startswith(prefix) for prefix in ("/boot", "/efi"))):
    sys.exit(f"Target is not a valid limine.conf: {cfg}")

if not GUID_PATTERN.match(guid):
    sys.exit(f"Invalid canonical GUID: {guid}")
if not LABEL_PATTERN.match(label):
    sys.exit(f"Invalid label: {label}")
if not cfg.is_file():
    sys.exit(f"Config file does not exist: {cfg}")

content = cfg.read_text(encoding="utf-8")
lower = content.lower()
if "efi_chainload" in lower and "bootmgfw.efi" in lower:
    print("Windows entry already exists in config")
    sys.exit(0)

# Create timestamped backup
shutil.copy2(cfg, f"{cfg}.bak-{int(time.time())}")

entry = f"\\n/{label}\\n    comment: Boot Windows Boot Manager\\n    protocol: efi_chainload\\n    image_path: guid({guid}):/EFI/Microsoft/Boot/bootmgfw.efi\\n"
with open(cfg, "a", encoding="utf-8") as f:
    f.write(entry)

print(f"Windows entry added successfully to {cfg}")
"""


def add_windows_to_limine(partuuid: str, label: str = "Windows 11") -> Tuple[bool, str]:
    """Safely adds Windows chainload entry to /boot/limine.conf."""
    try:
        guid_clean = validate_guid(partuuid)
        label_clean = validate_label(label)
    except ValueError as e:
        return False, str(e)

    cfg_path = find_limine_config() or Path("/boot/limine.conf")
    if not cfg_path.exists():
        return False, f"limine.conf not found at {cfg_path}"

    import sys
    if os.geteuid() == 0:
        runner = [sys.executable, "-c", LIMINE_APPEND_HELPER, str(cfg_path), guid_clean, label_clean]
    elif subprocess.run(["sudo", "-n", "true"], capture_output=True).returncode == 0:
        runner = ["sudo", sys.executable, "-c", LIMINE_APPEND_HELPER, str(cfg_path), guid_clean, label_clean]
    else:
        runner = ["pkexec", sys.executable, "-c", LIMINE_APPEND_HELPER, str(cfg_path), guid_clean, label_clean]

    try:
        res = subprocess.run(runner, capture_output=True, text=True, check=True)
        return True, res.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, f"Elevation error: {e.stderr.strip() or str(e)}"
    except FileNotFoundError:
        return False, "pkexec is not installed on this system"


SET_ONESHOT_HELPER = """
import sys, re, subprocess
from pathlib import Path

LABEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}$")

if len(sys.argv) < 2:
    sys.exit("Usage: helper <label>")

label = sys.argv[1].strip()
if not LABEL_PATTERN.match(label):
    sys.exit(f"Invalid label: {label}")

guid = "4a67b082-0a4c-41cf-b6c7-440b29bb8c4f"
attrs = b"\\x07\\x00\\x00\\x00"

def write_var(name, val_str):
    p = Path(f"/sys/firmware/efi/efivars/{name}-{guid}")
    if p.exists():
        subprocess.run(["chattr", "-i", str(p)], check=False)
        try:
            p.unlink()
        except Exception:
            pass
    payload = attrs + val_str.encode("utf-16le") + b"\\x00\\x00"
    with open(p, "wb") as f:
        f.write(payload)

write_var("LoaderEntryOneShot", label)
write_var("LoaderConfigTimeoutOneShot", "0")
print("One-shot boot set for Limine")
"""


def set_limine_oneshot(entry_label: str = "Windows 11") -> Tuple[bool, str]:
    """Sets the UEFI Boot Loader Interface variable LoaderEntryOneShot so Limine boots Windows on the next reboot."""
    try:
        label_clean = validate_label(entry_label)
    except ValueError as e:
        return False, str(e)

    import sys
    if os.geteuid() == 0:
        runner = [sys.executable, "-c", SET_ONESHOT_HELPER, label_clean]
    elif subprocess.run(["sudo", "-n", "true"], capture_output=True).returncode == 0:
        runner = ["sudo", sys.executable, "-c", SET_ONESHOT_HELPER, label_clean]
    else:
        runner = ["pkexec", sys.executable, "-c", SET_ONESHOT_HELPER, label_clean]

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
