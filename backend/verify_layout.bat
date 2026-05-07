@echo off
echo Starting Backend Server (Background)...
start /B venv\Scripts\python run_server.py > server.log 2>&1

echo Waiting for server to start (15s)...
timeout /t 15

echo Running Layout API Test...
venv\Scripts\python tests\test_layout.py

echo.
echo Check server.log for server output if test fails.
pause
