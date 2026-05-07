@echo off
setlocal enabledelayedexpansion

:: Switch to English to avoid encoding issues on different systems
:: This prevents "garbage characters" and crashes due to codepage mismatch

echo =================================================================
echo       Electricity Bill Intelligent Analysis System - Start Script
echo =================================================================

:: 1. Check Environment
echo.
echo [1/4] Checking environment dependencies...

:: Check Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] Node.js not found. Please install: https://nodejs.org/
    goto :error
)

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] Python not found. Please install Python 3.10+
    goto :error
)

:: 2. Prepare Backend
echo.
echo [2/4] Preparing backend environment...
if not exist "backend" (
    echo [Error] 'backend' directory not found!
    goto :error
)
cd backend

:: Prefer venv
if exist "venv\Scripts\python.exe" (
    set "PYTHON_CMD=venv\Scripts\python.exe"
    echo [Info] Using virtual environment: backend\venv
) else (
    set "PYTHON_CMD=python"
    echo [Info] Using system Python
)

:: Install backend deps
echo [Info] Checking/Installing backend dependencies...
"%PYTHON_CMD%" -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [Error] Failed to install backend dependencies.
    echo [Tip] Try running backend\setup_env.bat manually.
    goto :error
)
cd ..

:: 3. Prepare Frontend
echo.
echo [3/4] Preparing frontend environment...
if not exist "frontend" (
    echo [Error] 'frontend' directory not found!
    goto :error
)
cd frontend

if not exist "node_modules" (
    echo [Info] First run detected. Installing frontend dependencies, this may take a few minutes...
    call npm install
    if !errorlevel! neq 0 (
        echo [Error] Failed to install frontend dependencies. Check network/Node.js.
        goto :error
    )
) else (
    echo [Info] Frontend dependencies ready.
)
cd ..

:: 4. Start Services
echo.
echo [4/4] Starting services...

:: Start Backend (New Window)
echo [Start] Backend Service (Port 8003)...
start "Electricity Bill Backend" cmd /k "cd backend && !PYTHON_CMD! run_server.py"

:: Start Frontend (New Window)
echo [Start] Frontend Service (Port 5173)...
start "Electricity Bill Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo =================================================================
echo       Services Started!
echo       Backend API Docs: http://localhost:8003/docs
echo       Frontend URL:     http://localhost:5173
echo =================================================================
echo.
echo [Action Required]
echo Press ANY KEY to close this launcher window.
echo (The backend and frontend windows will remain open)
pause
exit /b 0

:error
echo.
echo =================================================================
echo       [FAILED] An error occurred during startup.
echo =================================================================
echo Please check the error messages above.
echo.
echo Press ANY KEY to exit...
pause
exit /b 1
