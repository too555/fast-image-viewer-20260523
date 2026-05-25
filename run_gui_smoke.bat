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

"%PY_EXE%" scripts\gui_smoke_check.py
