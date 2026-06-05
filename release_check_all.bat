@echo off
setlocal
cd /d "%~dp0"

chcp 65001 >nul

call :run_step "Build exe" "build_exe.bat"
if errorlevel 1 exit /b %errorlevel%

call :run_classified_step "Exe smoke" "run_exe_smoke.bat"
if errorlevel 1 exit /b %errorlevel%

call :run_classified_python "Minimal E2E" "tools\release_e2e_check.py"
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

:run_classified_step
echo.
echo ==== %~1 ====
set "release_step_log=%TEMP%\fast_image_viewer_release_check_%RANDOM%_%RANDOM%.log"
call "%~2" > "%release_step_log%" 2>&1
set "step_error=%errorlevel%"
type "%release_step_log%"
python "tools\release_e2e_check.py" --classify-log "%release_step_log%" --exit-code %step_error%
del "%release_step_log%" >nul 2>nul
if not "%step_error%"=="0" (
    echo RELEASE_CHECK_ALL_FAILED: %~1
    exit /b %step_error%
)
exit /b 0

:run_classified_python
echo.
echo ==== %~1 ====
set "release_step_log=%TEMP%\fast_image_viewer_release_check_%RANDOM%_%RANDOM%.log"
python "%~2" > "%release_step_log%" 2>&1
set "step_error=%errorlevel%"
type "%release_step_log%"
python "tools\release_e2e_check.py" --classify-log "%release_step_log%" --exit-code %step_error%
del "%release_step_log%" >nul 2>nul
if not "%step_error%"=="0" (
    echo RELEASE_CHECK_ALL_FAILED: %~1
    exit /b %step_error%
)
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
