#!/usr/bin/env python3
"""
Secure Boot & sbctl management engine.
Handles checking sbctl status, generating enrollment commands, and verifying EFI signatures.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

BOOT_DIR = Path("/boot")
EFI_DIR = Path("/boot/EFI")


def check_sbctl_installed() -> bool:
    """Checks whether sbctl binary is installed on system."""
    return shutil.which("sbctl") is not None


def get_sbctl_status() -> Dict[str, Any]:
    """
    Runs sbctl status to get cryptographic status.
    Returns parsed dictionary or fallback based on /sys/firmware/efi.
    """
    if not check_sbctl_installed():
        return {
            "installed": False,
            "setup_mode": False,
            "secure_boot": False,
            "enrolled": False,
            "keys_created": False,
            "raw": "sbctl is not installed."
        }

    try:
        res = subprocess.run(["sbctl", "status", "--json"], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            data["installed"] = True
            return data
    except Exception:
        pass

    # Fallback to plain sbctl status text parsing
    try:
        res = subprocess.run(["sbctl", "status"], capture_output=True, text=True, check=False)
        stdout = res.stdout.lower()
        return {
            "installed": True,
            "setup_mode": "setup mode: enabled" in stdout,
            "secure_boot": "secure boot: enabled" in stdout,
            "enrolled": "vendor keys: custom" in stdout or "keys enrolled: yes" in stdout,
            "raw": res.stdout.strip()
        }
    except Exception as e:
        return {
            "installed": True,
            "error": str(e)
        }


def get_signable_files() -> List[str]:
    """
    Scans for EFI binaries that require signing for Omarchy + Limine to boot under Secure Boot.
    """
    files = [
        "/boot/EFI/BOOT/BOOTX64.EFI",
        "/boot/EFI/LIMINE/LIMINE_X64.EFI"
    ]

    linux_efi_dir = EFI_DIR / "Linux"
    if linux_efi_dir.exists():
        for f in linux_efi_dir.glob("*.efi"):
            files.append(str(f))

    # Add any fallback wildcards for scripts
    return sorted(list(set(files)))


def generate_setup_commands() -> List[str]:
    """
    Returns the exact sequence of shell commands to set up sbctl,
    enroll keys with Microsoft CA support (-m), and sign boot files.
    """
    return [
        "sudo pacman -S --needed --noconfirm sbctl",
        "sudo sbctl create-keys",
        "sudo sbctl enroll-keys -m",
        "sudo sbctl sign -s /boot/EFI/BOOT/BOOTX64.EFI",
        "sudo sbctl sign -s /boot/EFI/LIMINE/LIMINE_X64.EFI",
        "sudo sbctl sign -s /boot/EFI/Linux/*.efi",
        "sudo sbctl verify"
    ]


def verify_signatures() -> Tuple[bool, str]:
    """Runs sbctl verify to confirm that all required EFI binaries are signed."""
    if not check_sbctl_installed():
        return False, "sbctl is not installed"

    try:
        res = subprocess.run(["sbctl", "verify"], capture_output=True, text=True, check=False)
        is_ok = (res.returncode == 0)
        return is_ok, res.stdout.strip() or res.stderr.strip()
    except Exception as e:
        return False, str(e)


if __name__ == "__main__":
    print(f"sbctl installed: {check_sbctl_installed()}")
    print(f"Status: {json.dumps(get_sbctl_status(), indent=2)}")
    print("Signable files:")
    for f in get_signable_files():
        print(f"  - {f}")
