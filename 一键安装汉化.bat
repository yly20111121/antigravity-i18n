@echo off
setlocal
title Antigravity Localizer Installer
cd /d "%~dp0"

set "PY_CMD="
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
)
if "%PY_CMD%"=="" (
    if exist "C:\Users\yly\AppData\Local\Programs\Python\Python313\python.exe" (
        set "PY_CMD=C:\Users\yly\AppData\Local\Programs\Python\Python313\python.exe"
    )
)
if "%PY_CMD%"=="" (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        set "PY_CMD=python"
    )
)

if "%PY_CMD%"=="" (
    echo [ERROR] Python not found.
    echo Please make sure Python is installed.
    echo.
    pause
    exit /b 1
)

"%PY_CMD%" "%~dp0patch_antigravity.py" install
echo.
pause
