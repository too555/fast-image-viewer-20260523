@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\create_release_zip.ps1"
exit /b %errorlevel%
