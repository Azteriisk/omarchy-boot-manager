<#
.SYNOPSIS
    Omarchy Boot & Reboot Manager for Windows
    Windows companion to omarchy-boot-manager.
.DESCRIPTION
    Provides zero-friction swapping between Windows and Omarchy Linux.
    Sets the UEFI one-shot boot sequence to Omarchy / Limine and reboots immediately.
#>

param(
    [Parameter(Position = 0)]
    [string]$Command = "status",

    [Parameter(Position = 1)]
    [string]$Target = "",

    [Parameter()]
    [string]$Guid = ""
)

$ErrorActionPreference = "Continue"
if (Get-Variable -Name "PSNativeCommandUseErrorActionPreference" -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigFile = Join-Path $ScriptDir "config.json"
$TaskName = "RebootToOmarchy"

function Test-ScheduledTaskExists {
    cmd.exe /c "schtasks /query /tn `"$TaskName`" >nul 2>&1"
    return ($LASTEXITCODE -eq 0)
}

function Remove-ScheduledTaskIfExists {
    cmd.exe /c "schtasks /query /tn `"$TaskName`" >nul 2>&1 && schtasks /delete /tn `"$TaskName`" /f >nul 2>&1"
}

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Assert-Admin {
    param([string[]]$Arguments)
    if (-not (Test-IsAdmin)) {
        Write-Host "Elevating privileges for this operation..." -ForegroundColor Yellow
        $argList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"") + $Arguments
        Start-Process powershell.exe -Verb RunAs -ArgumentList $argList -Wait
        exit $LASTEXITCODE
    }
}

function Get-SecureBootStatus {
    try {
        $sb = Get-ItemPropertyValue -Path "HKLM:\System\CurrentControlSet\Control\SecureBoot\State" -Name "UEFISecureBootEnabled" -ErrorAction SilentlyContinue
        return ($sb -eq 1)
    } catch {
        return $false
    }
}

function Get-EfiPartitions {
    try {
        $parts = Get-Partition | Where-Object { $_.GptType -eq "{c12a7328-f81f-11d2-ba4b-00a0c93ec93b}" }
        return $parts
    } catch {
        return @()
    }
}

function Parse-BcdFirmwareEntries {
    if (-not (Test-IsAdmin)) {
        return @()
    }

    $raw = bcdedit /enum firmware 2>&1
    $entries = @()
    $current = $null

    foreach ($line in ($raw -split "`r?`n")) {
        $trimmed = $line.Trim()
        if ($trimmed -match '^(?:Firmware Application|Windows Boot Manager|Firmware Boot Manager)\s*(\(.*\))?') {
            if ($current -and $current.Identifier) {
                $entries += [PSCustomObject]$current
            }
            $current = [ordered]@{
                Type        = $matches[0]
                Identifier  = ""
                Description = ""
                Path        = ""
                Device      = ""
            }
        } elseif ($line -match '^identifier\s+(.+)$') {
            if (-not $current) {
                $current = [ordered]@{ Type = "Unknown"; Identifier = ""; Description = ""; Path = ""; Device = "" }
            }
            $current.Identifier = $matches[1].Trim()
        } elseif ($line -match '^description\s+(.+)$') {
            if ($current) { $current.Description = $matches[1].Trim() }
        } elseif ($line -match '^path\s+(.+)$') {
            if ($current) { $current.Path = $matches[1].Trim() }
        } elseif ($line -match '^device\s+(.+)$') {
            if ($current) { $current.Device = $matches[1].Trim() }
        }
    }
    if ($current -and $current.Identifier) {
        $entries += [PSCustomObject]$current
    }
    return $entries
}

function Get-SavedConfig {
    if (Test-Path $ConfigFile) {
        try {
            return Get-Content $ConfigFile -Raw | ConvertFrom-Json
        } catch {}
    }
    return $null
}

function Save-Config ($cfg) {
    $json = $cfg | ConvertTo-Json -Depth 4
    Set-Content -Path $ConfigFile -Value $json -Encoding utf8
}

function Find-OmarchyEntry {
    $config = Get-SavedConfig
    if ($config -and $config.omarchy_guid) {
        return @{
            Identifier  = $config.omarchy_guid
            Description = $config.omarchy_description
            Source      = "config.json"
        }
    }

    if (-not (Test-IsAdmin)) {
        return $null
    }

    $entries = Parse-BcdFirmwareEntries
    # Exclude Windows Boot Manager and Firmware Boot Manager
    $candidates = $entries | Where-Object {
        $_.Identifier -ne "{fwbootmgr}" -and
        $_.Identifier -ne "{bootmgr}" -and
        $_.Description -notlike "*Windows Boot Manager*"
    }

    # 1. Search by keyword
    $match = $candidates | Where-Object {
        $_.Description -match "(?i)(omarchy|limine|linux|arch)" -or
        $_.Path -match "(?i)(limine|omarchy|linux)"
    } | Select-Object -First 1

    if ($match) {
        return @{
            Identifier  = $match.Identifier
            Description = $match.Description
            Source      = "bcdedit-detected"
        }
    }

    # 2. If single non-Windows candidate
    if ($candidates.Count -eq 1) {
        return @{
            Identifier  = $candidates[0].Identifier
            Description = $candidates[0].Description
            Source      = "bcdedit-candidate"
        }
    }

    return $null
}

function Show-Status {
    $sb = Get-SecureBootStatus
    $sbColor = if ($sb) { "Green" } else { "Red" }
    $sbText = if ($sb) { "Active (Enrolled & Validated)" } else { "Disabled" }

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "     Omarchy Boot & Secure Boot Manager (Windows)" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  UEFI Secure Boot:  " -NoNewline
    Write-Host $sbText -ForegroundColor $sbColor

    # Partitions
    $efiParts = Get-EfiPartitions
    Write-Host "`n  EFI System Partitions:" -ForegroundColor White
    foreach ($p in $efiParts) {
        $disk = $p.DiskNumber
        $sizeGb = [math]::Round($p.Size / 1GB, 2)
        $guid = $p.Guid
        $label = if ($p.Size -gt 500MB) { "Omarchy / Linux ESP" } else { "Windows ESP" }
        Write-Host "   - Disk $disk, Partition $($p.PartitionNumber) ($sizeGb GB) - $label" -ForegroundColor Gray
        Write-Host "     GUID: $guid" -ForegroundColor DarkGray
    }

    # Omarchy firmware target
    $omarchy = Find-OmarchyEntry
    Write-Host "`n  Omarchy Boot Target:" -ForegroundColor White
    if ($omarchy) {
        Write-Host "   - Title: " -NoNewline
        Write-Host "$($omarchy.Description)" -ForegroundColor Green
        Write-Host "   - GUID:  " -NoNewline
        Write-Host "$($omarchy.Identifier)" -ForegroundColor Cyan
        Write-Host "   - Origin: $($omarchy.Source)" -ForegroundColor DarkGray
    } else {
        if (-not (Test-IsAdmin)) {
            Write-Host "   - (Run with Administrator or run 'omarchy-boot setup' to detect)" -ForegroundColor Yellow
        } else {
            Write-Host "   - Not detected automatically. Run 'omarchy-boot setup' to configure." -ForegroundColor Yellow
        }
    }

    # Scheduled Task Status
    Write-Host "`n  One-Click Fast Switch Task:" -ForegroundColor White
    if (Test-ScheduledTaskExists) {
        Write-Host "   - Status: Installed ($TaskName)" -ForegroundColor Green
        Write-Host "   - Perms:  Elevated (zero UAC prompts on swap)" -ForegroundColor DarkGreen
    } else {
        Write-Host "   - Status: Not installed (Run 'omarchy-boot setup' to install)" -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "  Quick Actions:" -ForegroundColor White
    Write-Host "   - Swap to Omarchy:   omarchy-boot reboot omarchy" -ForegroundColor Cyan
    Write-Host "   - Reboot into BIOS:  omarchy-boot reboot bios" -ForegroundColor Cyan
    Write-Host "   - Full Setup Wizard: omarchy-boot setup" -ForegroundColor Cyan
    Write-Host "============================================================`n" -ForegroundColor Cyan
}

function Invoke-DirectRebootOmarchy {
    # This function is designed to be executed directly by the elevated scheduled task
    $entry = Find-OmarchyEntry
    if (-not $entry -or -not $entry.Identifier) {
        # Fallback: check config file directly
        $cfg = Get-SavedConfig
        if ($cfg -and $cfg.omarchy_guid) {
            $guid = $cfg.omarchy_guid
        } else {
            Write-Host "Error: Omarchy boot GUID not configured." -ForegroundColor Red
            exit 1
        }
    } else {
        $guid = $entry.Identifier
    }

    Write-Host "Setting one-shot boot sequence to Omarchy ($guid)..." -ForegroundColor Cyan
    $res = bcdedit /set "{fwbootmgr}" bootsequence $guid 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to set bootsequence: $res" -ForegroundColor Red
        exit 1
    }

    Write-Host "Restarting system into Omarchy Linux..." -ForegroundColor Green
    Start-Sleep -Milliseconds 500
    shutdown /r /t 0
}

function Invoke-Reboot {
    param([string]$TargetName)
    $TargetName = $TargetName.ToLower()

    if ($TargetName -in @("bios", "uefi", "firmware")) {
        Write-Host "Rebooting into UEFI / BIOS Setup..." -ForegroundColor Cyan
        shutdown /r /fw /t 0
        return
    }

    if ($TargetName -in @("omarchy", "linux", "limine", "")) {
        # Check if scheduled task exists
        if (Test-ScheduledTaskExists) {
            Write-Host "Triggering fast swap to Omarchy via elevated task..." -ForegroundColor Cyan
            cmd.exe /c "schtasks /run /tn `"$TaskName`" >nul 2>&1"
            Write-Host "Reboot initiated." -ForegroundColor Green
            return
        }

        # Otherwise elevate
        Assert-Admin @("reboot-direct")
        Invoke-DirectRebootOmarchy
        return
    }

    Write-Host "Unknown target: $TargetName. Use 'omarchy' or 'bios'." -ForegroundColor Red
}

function Run-Setup {
    Assert-Admin @("setup")

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "      Omarchy Boot Manager Windows Setup Wizard" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""

    # Check existing config
    $existingCfg = Get-SavedConfig
    $selected = $null

    if ($Guid) {
        $cleanGuid = if ($Guid.StartsWith("{")) { $Guid } else { "{$Guid}" }
        $selected = [PSCustomObject]@{
            Identifier  = $cleanGuid
            Description = "Specified Omarchy Target"
        }
    } elseif ($existingCfg -and $existingCfg.omarchy_guid) {
        Write-Host "Found previously configured Omarchy entry: $($existingCfg.omarchy_description) ($($existingCfg.omarchy_guid))`n" -ForegroundColor Green
        $keep = Read-Host "Keep this entry? [Y/n]"
        if ($keep.Trim().ToLower() -ne "n") {
            $selected = [PSCustomObject]@{
                Identifier  = $existingCfg.omarchy_guid
                Description = $existingCfg.omarchy_description
            }
        }
    }

    if (-not $selected) {
        Write-Host "Scanning UEFI firmware entries..." -ForegroundColor Cyan
        $entries = Parse-BcdFirmwareEntries

        $candidates = $entries | Where-Object {
            $_.Identifier -ne "{fwbootmgr}" -and
            $_.Identifier -ne "{bootmgr}" -and
            $_.Description -notlike "*Windows Boot Manager*"
        }

        if (-not $candidates -or $candidates.Count -eq 0) {
            $candidates = $entries | Where-Object { $_.Identifier -ne "{fwbootmgr}" }
        }

        Write-Host "`nDiscovered UEFI Boot Entries:" -ForegroundColor White
        $index = 1
        foreach ($c in $candidates) {
            Write-Host "  [$index] $($c.Description) ($($c.Identifier))" -ForegroundColor Gray
            if ($c.Path) { Write-Host "      Path: $($c.Path)" -ForegroundColor DarkGray }
            $index++
        }

        # Auto detect
        $selected = $candidates | Where-Object {
            $_.Description -match "(?i)(omarchy|limine|linux|arch)" -or
            $_.Path -match "(?i)(limine|omarchy|linux)"
        } | Select-Object -First 1

        if (-not $selected -and $candidates.Count -eq 1) {
            $selected = $candidates[0]
        }

        if ($selected) {
            Write-Host "`nAuto-detected Omarchy/Limine entry:" -ForegroundColor Green
            Write-Host "  $($selected.Description) ($($selected.Identifier))" -ForegroundColor Cyan
            $confirm = Read-Host "`nUse this entry for swapping to Omarchy? [Y/n]"
            if ($confirm.Trim().ToLower() -eq "n") {
                $selected = $null
            }
        }

        if (-not $selected) {
            $pick = Read-Host "`nEnter the number of the Omarchy / Limine entry [1-$($candidates.Count)] or paste the GUID"
            if ($pick -match '^\d+$' -and [int]$pick -ge 1 -and [int]$pick -le $candidates.Count) {
                $selected = $candidates[[int]$pick - 1]
            } elseif ($pick -match '^\{?[0-9a-fA-F\-]{36}\}?$') {
                $cleanGuid = if ($pick.StartsWith("{")) { $pick } else { "{$pick}" }
                $selected = [PSCustomObject]@{
                    Identifier  = $cleanGuid
                    Description = "Custom Omarchy Entry"
                }
            } else {
                Write-Host "Invalid selection. Setup cancelled." -ForegroundColor Red
                return
            }
        }
    }

    # Save to config.json
    $cfg = @{
        omarchy_guid        = $selected.Identifier
        omarchy_description = $selected.Description
        installed_at        = (Get-Date -Format "o")
    }
    Save-Config $cfg
    Write-Host "`nSaved Omarchy target to config.json." -ForegroundColor Green

    # Create runner script for Scheduled Task
    $runnerPath = Join-Path $ScriptDir "reboot-runner.cmd"
    $runnerContent = "@echo off`r`npowershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSCommandPath`" reboot-direct`r`n"
    Set-Content -Path $runnerPath -Value $runnerContent -Encoding ascii

    # Remove existing task if present
    Remove-ScheduledTaskIfExists

    # Create Scheduled Task for zero-UAC execution
    Write-Host "`nRegistering elevated scheduled task '$TaskName' (allows 1-click reboot with no UAC)..." -ForegroundColor Cyan
    $createOutput = cmd.exe /c "schtasks /create /tn `"$TaskName`" /tr `"\`"$runnerPath\`"`" /sc ONCE /st 00:00 /ru `"SYSTEM`" /rl HIGHEST /f 2>&1"

    if ($LASTEXITCODE -ne 0) {
        $user = "$env:USERDOMAIN\$env:USERNAME"
        $createOutput = cmd.exe /c "schtasks /create /tn `"$TaskName`" /tr `"\`"$runnerPath\`"`" /sc ONCE /st 00:00 /ru `"$user`" /rl HIGHEST /f 2>&1"
    }

    if ($LASTEXITCODE -eq 0) {
        Write-Host "Scheduled task created successfully." -ForegroundColor Green
    } else {
        Write-Host "Warning: Could not create scheduled task: $createOutput" -ForegroundColor Yellow
    }

    # Create Desktop Shortcut
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktopPath "Reboot into Omarchy.lnk"
    $cmdLauncherPath = Join-Path $ScriptDir "reboot-to-omarchy.cmd"

    # Create cmd launcher
    $cmdLauncherContent = "@echo off`r`nschtasks /run /tn $TaskName >nul 2>&1`r`nif %errorlevel% neq 0 (`r`n    powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"%~dp0omarchy-boot.ps1`" reboot omarchy`r`n)`r`n"
    Set-Content -Path $cmdLauncherPath -Value $cmdLauncherContent -Encoding ascii

    $wshShell = New-Object -ComObject WScript.Shell
    $shortcut = $wshShell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $cmdLauncherPath
    $shortcut.WorkingDirectory = $ScriptDir
    $shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll, 220" # Restart icon
    $shortcut.Description = "Instantly swap into Omarchy Linux"
    $shortcut.Save()

    Write-Host "Created Desktop Shortcut: 'Reboot into Omarchy'" -ForegroundColor Green

    # Create BIOS Shortcut
    $biosShortcutPath = Join-Path $desktopPath "Reboot into BIOS.lnk"
    $biosCmdPath = Join-Path $ScriptDir "reboot-to-bios.cmd"
    Set-Content -Path $biosCmdPath -Value "@echo off`r`nshutdown /r /fw /t 0`r`n" -Encoding ascii

    $biosShortcut = $wshShell.CreateShortcut($biosShortcutPath)
    $biosShortcut.TargetPath = $biosCmdPath
    $biosShortcut.WorkingDirectory = $ScriptDir
    $biosShortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll, 44" # Hardware / BIOS icon
    $biosShortcut.Description = "Reboot directly into UEFI / BIOS Setup"
    $biosShortcut.Save()
    Write-Host "Created Desktop Shortcut: 'Reboot into BIOS'" -ForegroundColor Green

    # PowerShell profile helper
    $profileDir = Split-Path -Parent $PROFILE
    if (-not (Test-Path $profileDir)) {
        New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    }
    $helperFunc = @"

# Omarchy Boot Manager Helper
function reboot-omarchy { & '$PSCommandPath' reboot omarchy }
function reboot-bios { & '$PSCommandPath' reboot bios }
"@
    if (-not (Test-Path $PROFILE) -or (Get-Content $PROFILE -Raw) -notmatch "reboot-omarchy") {
        Add-Content -Path $PROFILE -Value $helperFunc
        Write-Host "Added 'reboot-omarchy' and 'reboot-bios' functions to your PowerShell `$PROFILE." -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "  Setup complete! You can now swap to Omarchy anytime by:" -ForegroundColor Green
    Write-Host "  1. Double-clicking 'Reboot into Omarchy' on your Desktop" -ForegroundColor White
    Write-Host "  2. Typing 'reboot-omarchy' in PowerShell or Windows Terminal" -ForegroundColor White
    Write-Host "============================================================`n" -ForegroundColor Green
}

# Command Router
switch ($Command.ToLower()) {
    "status" {
        Show-Status
    }
    "reboot" {
        Invoke-Reboot $Target
    }
    "reboot-direct" {
        Invoke-DirectRebootOmarchy
    }
    "setup" {
        Run-Setup
    }
    "install" {
        Run-Setup
    }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host "Usage: omarchy-boot [status|reboot|setup]" -ForegroundColor Yellow
    }
}
