@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\check_release_zip_extract.ps1" %*
exit /b %errorlevel%
