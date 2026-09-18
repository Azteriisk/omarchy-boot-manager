@echo off
schtasks /run /tn RebootToOmarchy >nul 2>&1
if %errorlevel% neq 0 (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0omarchy-boot.ps1" reboot omarchy
)
