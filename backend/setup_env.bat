@echo off
setlocal enabledelayedexpansion

:: Switch to English to avoid encoding issues on different systems
:: This prevents "garbage characters" and crashes due to codepage mismatch

echo =================================================================
echo       Electricity Bill Intelligent Analysis System - Setup Script
echo =================================================================

:: 1. Check Python
echo.
echo [1/5] Checking Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] Python not found. Please install Python 3.10+
    echo Visit: https://www.python.org/downloads/
    goto :error
)

python --version
if %errorlevel% neq 0 (
    echo [Error] Failed to check Python version.
    goto :error
)

:: 2. Check/Create Venv
echo.
echo [2/5] Checking virtual environment...
set "VENV_DIR=venv"

if not exist "%VENV_DIR%" (
    echo [Info] Creating virtual environment: %VENV_DIR% ...
    python -m venv %VENV_DIR%
    if !errorlevel! neq 0 (
        echo [Error] Failed to create virtual environment. Check permissions.
        goto :error
    )
    echo [Success] Virtual environment created.
) else (
    echo [Info] Virtual environment exists.
)

:: 3. Activate Venv
echo.
echo [3/5] Activating virtual environment...
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [Error] Activation script missing: %VENV_DIR%\Scripts\activate.bat
    echo [Tip] Try deleting the '%VENV_DIR%' folder and running this again.
    goto :error
)

call "%VENV_DIR%\Scripts\activate.bat"
if %errorlevel% neq 0 (
    echo [Error] Failed to activate virtual environment.
    goto :error
)
echo [Success] Virtual environment activated.

:: 4. Upgrade pip
echo.
echo [4/5] Upgrading pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [Warning] Failed to upgrade pip. Continuing...
)

:: 5. Install Dependencies
echo.
echo [5/5] Installing dependencies (this may take a while)...
if exist "requirements.txt" (
    pip install -r requirements.txt
    if !errorlevel! neq 0 (
        echo [Error] Failed to install dependencies.
        echo [Tip] Check your network or try a mirror source.
        echo [Tip] Try: pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
        goto :error
    )
    echo [Success] Dependencies installed!
) else (
    echo [Warning] requirements.txt not found, skipping installation.
)

echo.
echo =================================================================
echo       Setup Complete!
echo =================================================================
echo.
echo Next steps:
echo    1. Activate env: backend\%VENV_DIR%\Scripts\activate
echo    2. Run server:   python run_server.py
echo.
echo Press any key to exit...
pause >nul
exit /b 0

:error
echo.
echo =================================================================
echo       [FAILED] Setup failed.
echo =================================================================
echo Please check the error messages above.
echo.
echo Press any key to exit...
pause >nul
exit /b 1
