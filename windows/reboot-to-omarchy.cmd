@echo off
schtasks /run /tn RebootToOmarchy
if %errorlevel% neq 0 (
    echo [!] Fast swap task not found or not configured yet.
    echo Running setup...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0omarchy-boot.ps1" reboot omarchy
)
