#!/usr/bin/env python3
"""
Hardware, EFI variables, partition, and bootloader detection engine.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

EFIVARS_DIR = Path("/sys/firmware/efi/efivars")
DMI_DIR = Path("/sys/class/dmi/id")

MOTHERBOARD_GUIDES = {
    "asus": {
        "vendor": "ASUS",
        "key": "F2 or DEL",
        "menu_path": "Advanced Mode (F7) -> Boot tab -> Secure Boot",
        "setup_mode_steps": [
            "Press F7 to enter Advanced Mode.",
            "Navigate to the 'Boot' tab and select 'Secure Boot'.",
            "Set 'OS Type' to 'Other OS' (or 'Custom').",
            "Select 'Key Management' -> 'Clear Secure Boot Keys' (enters Setup Mode).",
            "Save changes (F10) and reboot into Omarchy."
        ],
        "enable_steps": [
            "Press F7 to enter Advanced Mode.",
            "Navigate to 'Boot' -> 'Secure Boot'.",
            "Set 'OS Type' back to 'Windows UEFI mode' (or 'Enabled').",
            "Save changes (F10) and reboot."
        ]
    },
    "msi": {
        "vendor": "MSI",
        "key": "DEL",
        "menu_path": "Advanced (F7) -> Settings -> Security -> Secure Boot",
        "setup_mode_steps": [
            "Press F7 for Advanced Mode.",
            "Go to 'Settings' -> 'Security' -> 'Secure Boot'.",
            "Change 'Secure Boot Mode' from 'Standard' to 'Custom'.",
            "Select 'Delete PK' or 'Enroll all Factory Default Keys' -> 'Delete'.",
            "Save and reboot into Omarchy."
        ],
        "enable_steps": [
            "Return to 'Settings' -> 'Security' -> 'Secure Boot'.",
            "Set 'Secure Boot' to 'Enabled'.",
            "Save and reboot."
        ]
    },
    "gigabyte": {
        "vendor": "Gigabyte / AORUS",
        "key": "DEL",
        "menu_path": "Settings / BIOS -> Secure Boot",
        "setup_mode_steps": [
            "Enter BIOS (DEL key).",
            "Navigate to 'Settings' (or 'BIOS') -> 'Secure Boot'.",
            "Set 'Secure Boot Mode' to 'Custom'.",
            "Select 'Delete PK' or 'Restore Factory Keys' to enter Setup Mode.",
            "Save and reboot into Omarchy."
        ],
        "enable_steps": [
            "Navigate to 'Settings' -> 'Secure Boot'.",
            "Set 'Secure Boot' to 'Enabled'.",
            "Save and reboot."
        ]
    },
    "asrock": {
        "vendor": "ASRock",
        "key": "F2 or DEL",
        "menu_path": "Security tab -> Secure Boot",
        "setup_mode_steps": [
            "Navigate to the 'Security' tab.",
            "Select 'Secure Boot'.",
            "Change mode to 'Custom' and select 'Clear Keys'.",
            "Save and reboot into Omarchy."
        ],
        "enable_steps": [
            "Navigate to 'Security' -> 'Secure Boot'.",
            "Set 'Secure Boot' to 'Enabled'.",
            "Save and reboot."
        ]
    },
    "generic": {
        "vendor": "Generic UEFI Firmware",
        "key": "DEL, F2, F10, or F12",
        "menu_path": "Security / Boot -> Secure Boot",
        "setup_mode_steps": [
            "Enter BIOS Setup.",
            "Find 'Secure Boot' under Security or Boot settings.",
            "Switch to 'Custom Mode' and clear existing Platform Keys (PK).",
            "Save and reboot into Omarchy."
        ],
        "enable_steps": [
            "Enter BIOS Setup.",
            "Enable 'Secure Boot'.",
            "Save and reboot."
        ]
    }
}


def read_sys_file(path: Path) -> str:
    """Reads a sysfs file safely and returns stripped text."""
    try:
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        pass
    return ""


def get_hardware_info() -> Dict[str, Any]:
    """Queries DMI information for motherboard and vendor matching."""
    sys_vendor = read_sys_file(DMI_DIR / "sys_vendor")
    board_vendor = read_sys_file(DMI_DIR / "board_vendor")
    product_name = read_sys_file(DMI_DIR / "product_name")
    board_name = read_sys_file(DMI_DIR / "board_name")
    bios_version = read_sys_file(DMI_DIR / "bios_version")

    effective_vendor = board_vendor or sys_vendor or "Unknown"
    effective_model = board_name or product_name or "System"

    vendor_lower = effective_vendor.lower()
    matched_key = "generic"
    if "asus" in vendor_lower:
        matched_key = "asus"
    elif "msi" in vendor_lower or "micro-star" in vendor_lower:
        matched_key = "msi"
    elif "gigabyte" in vendor_lower or "aorus" in vendor_lower:
        matched_key = "gigabyte"
    elif "asrock" in vendor_lower:
        matched_key = "asrock"

    guide = MOTHERBOARD_GUIDES.get(matched_key, MOTHERBOARD_GUIDES["generic"])

    return {
        "vendor": effective_vendor,
        "model": effective_model,
        "bios_version": bios_version,
        "guide": guide,
        "matched_key": matched_key
    }


def read_efivar_byte(prefix: str) -> Optional[int]:
    """Reads the data byte (5th byte) of a boolean EFI variable."""
    try:
        matches = list(EFIVARS_DIR.glob(f"{prefix}-*"))
        if matches and matches[0].exists():
            data = matches[0].read_bytes()
            if len(data) >= 5:
                return int(data[4])
    except Exception:
        pass
    return None


def get_secure_boot_status() -> Dict[str, Any]:
    """Checks the live state of UEFI Secure Boot."""
    sb_byte = read_efivar_byte("SecureBoot")
    sm_byte = read_efivar_byte("SetupMode")
    vk_byte = read_efivar_byte("VendorKeys")

    enabled = (sb_byte == 1)
    setup_mode = (sm_byte == 1)
    custom_keys = (vk_byte == 1)

    status_code = "disabled"
    if enabled:
        status_code = "enabled"
    elif setup_mode:
        status_code = "setup_mode"

    return {
        "enabled": enabled,
        "setup_mode": setup_mode,
        "custom_keys": custom_keys,
        "raw_secure_boot": sb_byte,
        "raw_setup_mode": sm_byte,
        "status_code": status_code,
        "label": (
            "Enabled & Active" if enabled else
            ("Setup Mode (Ready to Enroll)" if setup_mode else "Disabled (User Mode)")
        )
    }


def get_efi_boot_entries() -> Dict[str, Any]:
    """Parses efibootmgr entries to locate Windows and Omarchy/Limine loaders."""
    entries = []
    boot_current = ""
    boot_order = []
    windows_boot_id = None
    limine_boot_id = None

    try:
        res = subprocess.run(
            ["efibootmgr"],
            capture_output=True,
            text=True,
            check=False
        )
        for line in res.stdout.splitlines():
            line = line.strip()
            if line.startswith("BootCurrent:"):
                boot_current = line.split(":", 1)[1].strip()
            elif line.startswith("BootOrder:"):
                raw_order = line.split(":", 1)[1].strip()
                boot_order = [x.strip() for x in raw_order.split(",") if x.strip()]
            elif line.startswith("Boot"):
                m = re.match(r"^Boot([0-9A-Fa-f]{4})\*?\s+(.*?)(?:\t(.*))?$", line)
                if m:
                    b_id = m.group(1)
                    title = m.group(2).strip()
                    path = (m.group(3) or "").strip()
                    is_windows = "windows" in title.lower() or "bootmgfw.efi" in path.lower()
                    is_limine = "limine" in title.lower() or "limine" in path.lower()

                    entry_info = {
                        "id": b_id,
                        "title": title,
                        "path": path,
                        "is_windows": is_windows,
                        "is_limine": is_limine
                    }
                    entries.append(entry_info)

                    if is_windows and not windows_boot_id:
                        windows_boot_id = b_id
                    if is_limine and not limine_boot_id:
                        limine_boot_id = b_id
    except Exception:
        pass

    return {
        "current": boot_current,
        "order": boot_order,
        "entries": entries,
        "windows_id": windows_boot_id,
        "limine_id": limine_boot_id
    }


def get_windows_partitions() -> List[Dict[str, Any]]:
    """
    Finds Windows installations and EFI partitions by scanning
    efibootmgr and disk partuuids.
    """
    found = []

    # 1. First extract partition GUID directly from efibootmgr Windows Boot Manager line
    efi_data = get_efi_boot_entries()
    for entry in efi_data.get("entries", []):
        if entry["is_windows"]:
            path = entry["path"]
            # Look for HD(...,GPT,<guid>,...)
            m = re.search(r"GPT,([0-9a-fA-F\-]{36})", path)
            if m:
                guid = m.group(1).lower()
                found.append({
                    "partuuid": guid,
                    "boot_id": entry["id"],
                    "title": entry["title"],
                    "source": "efibootmgr",
                    "efi_path": "/EFI/Microsoft/Boot/bootmgfw.efi"
                })

    # 2. Also check lsblk partition tables for vfat/efi partitions
    try:
        res = subprocess.run(
            ["lsblk", "-r", "-n", "-o", "NAME,PARTUUID,FSTYPE,LABEL,MOUNTPOINTS"],
            capture_output=True,
            text=True,
            check=False
        )
        for line in res.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                partuuid = parts[1].lower()
                if len(partuuid) == 36 and not any(f["partuuid"] == partuuid for f in found):
                    # Check if mounted or mountable, or if by-partuuid exists
                    pu_path = Path(f"/dev/disk/by-partuuid/{partuuid}")
                    if pu_path.exists():
                        # We don't necessarily have root to mount and inspect raw fat,
                        # but efibootmgr already gave us the exact Windows ESP partition.
                        pass
    except Exception:
        pass

    return found


def get_firmware_info() -> Dict[str, Any]:
    """Returns general UEFI system capabilities."""
    is_uefi = EFIVARS_DIR.exists()
    has_fw_setup = False

    try:
        res = subprocess.run(
            ["bootctl", "status"],
            capture_output=True,
            text=True,
            check=False
        )
        for line in res.stdout.splitlines():
            if "Boot into FW:" in line and "supported" in line.lower():
                has_fw_setup = True
                break
    except Exception:
        has_fw_setup = is_uefi

    return {
        "is_uefi": is_uefi,
        "supports_firmware_setup": has_fw_setup,
        "hardware": get_hardware_info(),
        "secure_boot": get_secure_boot_status(),
        "boot_entries": get_efi_boot_entries(),
        "windows_partitions": get_windows_partitions()
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_firmware_info(), indent=2))
