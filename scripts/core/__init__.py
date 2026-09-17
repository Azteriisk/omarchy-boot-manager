"""
Omarchy Boot & Secure Boot Manager core module.
"""

from .boot_detector import (
    get_firmware_info,
    get_secure_boot_status,
    get_windows_partitions,
    get_efi_boot_entries,
    get_hardware_info
)
from .limine_manager import (
    read_limine_config,
    has_windows_chainload,
    generate_windows_entry,
    add_windows_to_limine
)
from .secureboot_manager import (
    check_sbctl_installed,
    get_sbctl_status,
    get_signable_files,
    generate_setup_commands
)

__all__ = [
    "get_firmware_info",
    "get_secure_boot_status",
    "get_windows_partitions",
    "get_efi_boot_entries",
    "get_hardware_info",
    "read_limine_config",
    "has_windows_chainload",
    "generate_windows_entry",
    "add_windows_to_limine",
    "check_sbctl_installed",
    "get_sbctl_status",
    "get_signable_files",
    "generate_setup_commands",
]
