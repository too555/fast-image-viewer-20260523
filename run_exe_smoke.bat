@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\exe_smoke_check.ps1"
exit /b %errorlevel%
