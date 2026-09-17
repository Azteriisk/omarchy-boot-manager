# Omarchy Boot & Secure Boot Manager (`azterisk.boot`)

A unified desktop application, CLI helper, and Omarchy Menu extension that bridges the gap between **Windows** and **Omarchy Linux**. 

Built for users dual-booting with Windows or preparing for a seamless transition, it solves the two biggest pain points in Linux gaming and dual-booting:
1. **Zero-BIOS Anti-Cheat Compatibility**: Enrolls custom Secure Boot keys alongside Microsoft OEM keys (`sbctl enroll-keys -m`) so games like **Valorant (Vanguard)**, **EasyAntiCheat**, and **FACEIT** run in Windows while Omarchy boots smoothly with Secure Boot permanently enabled 24/7.
2. **Instant Limine Dual-Boot Integration**: Automatically detects Windows EFI System Partitions and injects chainload entries into Limine with one click.
3. **One-Click Quick Boots**: Reboot straight into Windows (for the next boot only via `efibootmgr -n`) or directly into your motherboard's UEFI BIOS setup (`systemctl reboot --firmware-setup`) without hammering keyboard hotkeys during POST.

---

## ✨ Key Features

- 🔒 **Permanent Secure Boot Setup**:
  - Automatically identifies your motherboard model (ASUS, MSI, Gigabyte, ASRock, etc.) and provides vendor-specific instructions to enter Setup Mode.
  - Automates key generation, Microsoft OEM preservation (`-m`), and EFI signing for both Limine and all UKI kernels (`omarchy_linux.efi`, `linux-omarchy.efi`).
  - Once configured, Secure Boot stays enabled 24/7—no entering BIOS to switch OSes!
- 🪟 **Automatic Windows Chainloading**:
  - Scans GPT partition tables and EFI variables to find the exact Windows ESP partition GUID.
  - Generates and writes valid Limine `efi_chainload` entries into `/boot/limine.conf`.
- ⚡ **Omarchy Menu Integration**:
  - **Setup Menu**: Adds `Boot & Secure Boot` (`omarchy-boot gui`).
  - **System Menu**: Adds one-click `Reboot into Windows` and `Reboot into BIOS Setup`.
  - **Searchable**: Search "windows", "anticheat", "bios", or "secure boot" in the Omarchy launcher.
- 🎨 **Modern Libadwaita / GTK4 GUI (`omarchy-boot-gui`)**:
  - Overview dashboard with live security badges, motherboard information, and partition details.
  - Step-by-step interactive wizard with confirmation dialogs.
- 💻 **Robust Command Line Interface (`omarchy-boot`)**:
  - `status`, `json`, `reboot windows`, `reboot bios`, `add-windows`, `setup`.

---

## 📦 Installation

```bash
git clone https://github.com/Azteriisk/omarchy-boot-manager.git
cd omarchy-boot-manager
chmod +x install.sh
./install.sh
```

The installer will:
1. Symlink CLI binaries to `~/.local/bin/omarchy-boot` and `~/.local/bin/omarchy-boot-gui`.
2. Install the desktop launcher to `~/.local/share/applications/omarchy-boot.desktop`.
3. Integrate `setup.boot`, `system.reboot-windows`, and `system.reboot-bios` into `~/.config/omarchy/extensions/omarchy-menu.jsonc`.

---

## 🚀 Usage

### 1. Graphical Interface (GUI)
Launch **"Omarchy Boot & Secure Boot Manager"** from the Omarchy Application Menu, or run:

```bash
omarchy-boot gui
```

- **Overview Tab**: Check live status of Secure Boot, motherboard model, and Windows detection.
- **Secure Boot Wizard Tab**: Follow the 3-step walkthrough to configure permanent Secure Boot.
- **Limine Tab**: Preview and inject Windows chainload entry into `/boot/limine.conf`.

### 2. Command Line Interface (CLI)

```bash
# View complete system status summary
omarchy-boot status

# Output status as JSON (for scripts or widgets)
omarchy-boot json

# Reboot directly into Windows (one-shot next boot only)
omarchy-boot reboot windows

# Reboot directly into motherboard UEFI BIOS setup
omarchy-boot reboot bios

# Add detected Windows partition to Limine bootloader
omarchy-boot add-windows

# Launch interactive terminal setup wizard
omarchy-boot setup
```

---

## 🛡️ Anti-Cheat & Secure Boot Runbook

Why does this exist?
Under UEFI specifications, the `SecureBoot` variable is read-only at runtime. No software or bootloader can toggle BIOS Secure Boot on/off.

Instead of toggling BIOS settings manually:
1. **Put your motherboard in Setup Mode**:
   - Clear existing Platform Keys (PK) in BIOS (e.g. `Key Management` -> `Clear Secure Boot Keys`).
2. **Run the Wizard**:
   - Click "Run Wizard" in `omarchy-boot gui` or run `omarchy-boot setup`.
   - Generates custom keys and enrolls them with `-m` (`sbctl enroll-keys -m`).
   - Signs Limine (`BOOTX64.EFI`, `LIMINE_X64.EFI`) and Omarchy UKIs (`/boot/EFI/Linux/*.efi`).
3. **Turn Secure Boot ON in BIOS**:
   - Set Secure Boot to **Enabled**.

**Result:**
- **Windows Anti-Cheat** (Vanguard, EAC, FACEIT) sees Secure Boot is **ENABLED** with official Microsoft CA certificates enrolled.
- **Omarchy** boots cleanly because Limine and your kernel images are signed with your custom enrolled keys.

---

## 🗑️ Uninstallation

To restore default settings and remove menu extensions:

```bash
cd omarchy-boot-manager
./uninstall.sh
```

---

## 📄 License

MIT © [Azteriisk](https://github.com/Azteriisk)
