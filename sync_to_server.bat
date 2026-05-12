@echo off
chcp 65001 >nul
title 同步到云服务器

set PYTHON=C:\Users\18420\AppData\Local\Python\pythoncore-3.14-64\python.exe
set SCRIPT=%~dp0sync_to_server.py

echo ============================================
echo   同步文件到 47.99.126.187
echo   目标: /pepm/Electricity-bills-Recognize-main
echo ============================================
echo.

rem 检查 paramiko 是否已安装
%PYTHON% -c "import paramiko" 2>nul
if %errorlevel% neq 0 (
    echo [提示] 正在安装 paramiko...
    %PYTHON% -m pip install paramiko -q
    if %errorlevel% neq 0 (
        echo [错误] paramiko 安装失败，请检查网络连接
        pause
        exit /b 1
    )
    echo [完成] paramiko 安装成功
    echo.
)

echo [开始] 正在连接服务器并上传文件...
echo.

%PYTHON% "%SCRIPT%"

echo.
echo ============================================
echo   同步完成
echo ============================================
pause
