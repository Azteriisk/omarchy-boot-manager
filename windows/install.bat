@echo off
:: Self-elevate to Administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Elevating to Administrator...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0omarchy-boot.ps1" setup
pause
