@echo off
setlocal enabledelayedexpansion

chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
set PYTHON=C:\Users\18420\AppData\Local\Python\pythoncore-3.14-64\python.exe
set SCRIPT=%~dp0sync_to_server.py

echo ============================================
echo   Electricity Bill - Deploy to Cloud Server
echo   Server: 47.99.126.187
echo   User:   opxny
echo ============================================
echo.
echo   Steps:
echo     1. SCP upload all project files
echo     2. Restart backend  in tmux (Electricity)
echo     3. Restart frontend in tmux (elect-frontend)
echo ============================================
echo.

%PYTHON% -c "import paramiko" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Installing paramiko...
    %PYTHON% -m pip install paramiko -q
    if %errorlevel% neq 0 (
        echo [ERROR] paramiko install failed, check network
        pause
        exit /b 1
    )
    echo [OK] paramiko installed
    echo.
)

echo [START] Running deploy script...
echo.

%PYTHON% "%SCRIPT%"

if %errorlevel% neq 0 (
    echo.
    echo ============================================
    echo   Deploy FAILED, check errors above
    echo ============================================
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Deploy DONE!
echo   Check manually:
echo     ssh opxny@47.99.126.187
echo     tmux a -t Electricity       (backend)
echo     tmux a -t elect-frontend    (frontend)
echo ============================================
pause