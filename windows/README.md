# Omarchy Boot Manager — Windows Companion

A Windows companion script and zero-UAC shortcut system for [omarchy-boot-manager](https://github.com/Azteriisk/omarchy-boot-manager).

It mirrors Omarchy's `omarchy-boot reboot windows` command, giving you a seamless, one-click way to jump back to Omarchy Linux from Windows without pressing BIOS hotkeys (F11/F12) or making manual bootloader selections.

---

## How It Works

Under UEFI, Windows manages the one-shot boot target via the BCD store:
```cmd
bcdedit /set {fwbootmgr} bootsequence <OMARCHY_ENTRY_GUID>
shutdown /r /t 0
```
This sets the UEFI NVRAM `BootNext` variable directly, telling your motherboard firmware to jump straight into Limine / Omarchy on the very next boot. On subsequent boots, the standard boot order is preserved.

### Zero-UAC Execution

Modifying BCD requires Administrator privileges. To avoid an annoying Windows UAC prompt every time you want to switch operating systems:
- The installer registers a Windows Scheduled Task (`RebootToOmarchy`) with highest privileges.
- Desktop shortcuts and terminal commands simply trigger the task (`schtasks /run /tn "RebootToOmarchy"`).
- **Result:** Instant reboot into Omarchy with zero prompt.

---

## Setup

1. Right-click **`install.bat`** and choose **"Run as administrator"** (or run `.\omarchy-boot.ps1 setup` from an elevated PowerShell window).
2. The wizard automatically parses your UEFI firmware entries, identifies your Limine / Omarchy entry, and prompts you to confirm.
3. The installer creates:
   - **`Reboot into Omarchy`** shortcut on your Desktop.
   - **`Reboot into BIOS`** shortcut on your Desktop.
   - Adds `reboot-omarchy` and `reboot-bios` command aliases to your PowerShell `$PROFILE`.

---

## Usage

### Option 1: Desktop Shortcut
Double-click the **`Reboot into Omarchy`** icon on your desktop.

### Option 2: Windows Terminal / PowerShell
```powershell
# Instant reboot into Omarchy
reboot-omarchy

# Instant reboot into BIOS / UEFI setup
reboot-bios

# View system Secure Boot state & EFI partitions
.\omarchy-boot.ps1 status
```
