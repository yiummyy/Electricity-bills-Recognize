#!/bin/bash
set -e

echo "========================================"
echo "  Electricity Bill - Deploy Script"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# ---------- 配置区（按你的服务器实际情况修改）----------
PROJECT_DIR="/opt/electricity-bill"
PYTHON_CMD="python3"
SERVICE_NAME="electricity-bill"
NGINX_SERVE_DIR="/var/www/electricity-bill"
# ----------------------------------------------------

cd "$PROJECT_DIR"

echo "[1/4] Pulling latest code..."
git checkout main
git pull origin main

echo "[2/4] Installing backend dependencies..."
cd "$PROJECT_DIR/backend"
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    $PYTHON_CMD -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt -q
deactivate

echo "[3/4] Building frontend..."
cd "$PROJECT_DIR/frontend"
npm ci --silent
npm run build

echo "[4/4] Restarting services..."
sudo systemctl restart $SERVICE_NAME

if [ -d "$NGINX_SERVE_DIR" ]; then
    cp -r dist/* "$NGINX_SERVE_DIR/"
    sudo systemctl reload nginx 2>/dev/null || true
    echo "Frontend files copied to $NGINX_SERVE_DIR"
fi

echo ""
echo "========================================"
echo "  Deploy Complete!"
echo "========================================"
