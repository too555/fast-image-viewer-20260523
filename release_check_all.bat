@echo off
setlocal
cd /d "%~dp0"

chcp 65001 >nul

call :run_step "Build exe" "build_exe.bat"
if errorlevel 1 exit /b %errorlevel%

call :run_step "Exe smoke" "run_exe_smoke.bat"
if errorlevel 1 exit /b %errorlevel%

echo.
echo ==== Minimal E2E ====
python "tools\release_e2e_check.py"
if errorlevel 1 (
    echo RELEASE_CHECK_ALL_FAILED: Minimal E2E
    exit /b %errorlevel%
)

call :run_step "Create release zip" "create_release_zip.bat"
if errorlevel 1 exit /b %errorlevel%

call :run_step "Release zip smoke" "run_release_zip_smoke.bat"
if errorlevel 1 exit /b %errorlevel%

call :run_step "Create SHA256" "create_release_sha256.bat"
if errorlevel 1 exit /b %errorlevel%

echo RELEASE_CHECK_ALL_OK
exit /b 0

:run_step
echo.
echo ==== %~1 ====
call "%~2"
if errorlevel 1 (
    echo RELEASE_CHECK_ALL_FAILED: %~1
    exit /b %errorlevel%
)
exit /b 0
