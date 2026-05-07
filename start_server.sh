#!/bin/bash

# =================================================================
#       Electricity Bill Intelligent Analysis System - macOS/Linux Start
# =================================================================

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Electricity Bill Analysis System...${NC}"

# 1. Check Environment
echo ""
echo "[1/4] Checking environment dependencies..."

if ! command -v node &> /dev/null; then
    echo -e "${RED}[Error] Node.js not found. Please install: https://nodejs.org/${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[Error] Python 3 not found. Please install Python 3.10+${NC}"
    exit 1
fi

# 2. Backend Setup
echo ""
echo "[2/4] Preparing backend environment..."
cd backend || exit

PYTHON_CMD="python3"
if [ -d "venv" ]; then
    echo "[Info] Using virtual environment: backend/venv"
    if [ -f "venv/bin/python" ]; then
        PYTHON_CMD="./venv/bin/python"
    else
        echo "[Warning] venv exists but bin/python missing. Trying python3."
    fi
else
    echo "[Info] Using system Python"
fi

echo "[Info] Checking/Installing backend dependencies..."
$PYTHON_CMD -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}[Error] Failed to install backend dependencies.${NC}"
    exit 1
fi
cd ..

# 3. Frontend Setup
echo ""
echo "[3/4] Preparing frontend environment..."
cd frontend || exit
if [ ! -d "node_modules" ]; then
    echo "[Info] First run detected. Installing frontend dependencies..."
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}[Error] Failed to install frontend dependencies.${NC}"
        exit 1
    fi
else
    echo "[Info] Frontend dependencies ready."
fi
cd ..

# 4. Start Services
echo ""
echo "[4/4] Starting services..."

OS="$(uname)"

start_macos() {
    echo "Detected macOS. Opening new Terminal tabs..."
    
    # Get absolute paths
    BACKEND_DIR="$(pwd)/backend"
    FRONTEND_DIR="$(pwd)/frontend"
    
    # Open Backend
    osascript -e "tell application \"Terminal\" to do script \"cd \\\"$BACKEND_DIR\\\" && $PYTHON_CMD run_server.py\""
    
    # Open Frontend
    osascript -e "tell application \"Terminal\" to do script \"cd \\\"$FRONTEND_DIR\\\" && npm run dev\""
}

start_linux() {
    echo "Detected Linux. Attempting to start services..."
    
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal -- bash -c "cd backend && $PYTHON_CMD run_server.py; exec bash"
        gnome-terminal -- bash -c "cd frontend && npm run dev; exec bash"
    elif command -v xterm &> /dev/null; then
        xterm -e "cd backend && $PYTHON_CMD run_server.py" &
        xterm -e "cd frontend && npm run dev" &
    else
        echo -e "${RED}[Warning] No supported terminal emulator (gnome-terminal/xterm) found.${NC}"
        echo "Starting in background mode..."
        
        cd backend && $PYTHON_CMD run_server.py &
        BACKEND_PID=$!
        
        cd ../frontend && npm run dev &
        FRONTEND_PID=$!
        
        echo "Services running in background (PID: Backend=$BACKEND_PID, Frontend=$FRONTEND_PID)"
        echo "Press Ctrl+C to stop all services."
        
        trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
        wait
    fi
}

if [ "$OS" == "Darwin" ]; then
    start_macos
    echo ""
    echo -e "${GREEN}=================================================================${NC}"
    echo -e "${GREEN}       Services Started!${NC}"
    echo -e "${GREEN}       Backend API: http://localhost:8003/docs${NC}"
    echo -e "${GREEN}       Frontend:    http://localhost:5173${NC}"
    echo -e "${GREEN}=================================================================${NC}"
elif [ "$OS" == "Linux" ]; then
    start_linux
else
    echo -e "${RED}[Error] Unsupported OS: $OS${NC}"
    echo "Please start manually:"
    echo "1. cd backend && python run_server.py"
    echo "2. cd frontend && npm run dev"
fi
