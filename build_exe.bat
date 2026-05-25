@echo off
setlocal
cd /d "%~dp0"

set "PY_EXE="

if defined PYTHON (
    "%PYTHON%" -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PY_EXE=%PYTHON%"
)

if exist ".venv\Scripts\python.exe" (
    if not defined PY_EXE (
        ".venv\Scripts\python.exe" -c "import sys" >nul 2>nul
        if not errorlevel 1 set "PY_EXE=.venv\Scripts\python.exe"
    )
)

if not defined PY_EXE (
    where py >nul 2>nul
    if not errorlevel 1 set "PY_EXE=py"
)

if not defined PY_EXE (
    where python >nul 2>nul
    if not errorlevel 1 set "PY_EXE=python"
)

if not defined PY_EXE (
    echo Python was not found. Create .venv or set PYTHON to python.exe.
    exit /b 1
)

"%PY_EXE%" -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo PyInstaller was not found. Run: "%PY_EXE%" -m pip install -r requirements-dev.txt
    exit /b 1
)

"%PY_EXE%" -m PyInstaller --clean --noconfirm fast_image_viewer.spec
if errorlevel 1 exit /b 1

if not exist "dist\*.exe" (
    echo No exe was created in dist.
    exit /b 1
)

echo Created exe in dist.
