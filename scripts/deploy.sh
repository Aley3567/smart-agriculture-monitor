#!/bin/bash
set -e

SERVER="ubuntu@119.91.114.175"
REMOTE_DIR="/home/ubuntu/smart-agri"
FRONTEND_DIR="/var/www/smart-agri"
SERVICE_NAME="smart-agri"
BACKEND_PORT=8001

echo "=== Smart Agriculture Monitor Deploy ==="

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "[1/5] Building frontend..."
cd "$PROJECT_ROOT/frontend"
npx vite build

echo "[2/5] Syncing backend to server..."
cd "$PROJECT_ROOT"
rsync -avz --exclude '__pycache__' --exclude '*.pyc' --exclude 'agriculture.db' \
  backend/ "$SERVER:$REMOTE_DIR/backend/"

echo "[3/5] Syncing serial_bridge..."
rsync -avz --exclude '__pycache__' --exclude '*.pyc' \
  serial_bridge/ "$SERVER:$REMOTE_DIR/serial_bridge/"

echo "[4/5] Syncing frontend dist..."
rsync -avz frontend/dist/ "$SERVER:$FRONTEND_DIR/"

echo "[5/5] Installing deps & configuring server..."
ssh "$SERVER" bash <<'REMOTE_SCRIPT'
set -e

cd /home/ubuntu/smart-agri
if [ ! -x /home/ubuntu/smart-agri/venv/bin/python3 ]; then
  python3 -m venv /home/ubuntu/smart-agri/venv
fi
/home/ubuntu/smart-agri/venv/bin/python3 -m pip install -q -r /home/ubuntu/smart-agri/backend/requirements.txt
/home/ubuntu/smart-agri/venv/bin/python3 -m pip install -q -r /home/ubuntu/smart-agri/serial_bridge/requirements.txt

sudo tee /etc/systemd/system/smart-agri.service > /dev/null <<EOF
[Unit]
Description=Smart Agriculture FastAPI
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/smart-agri/backend
ExecStart=/home/ubuntu/smart-agri/venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable smart-agri
sudo systemctl restart smart-agri
sleep 2
systemctl is-active smart-agri && echo "Backend: OK" || echo "Backend: FAILED"

NGINX_CONF="/etc/nginx/sites-available/smart-agri"
if [ ! -f "$NGINX_CONF" ]; then
  sudo tee "$NGINX_CONF" > /dev/null <<'NGINXEOF'
server {
    listen 18082;
    server_name _;

    root /var/www/smart-agri;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
NGINXEOF
  sudo ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/smart-agri
fi

sudo nginx -t && sudo systemctl reload nginx
echo "Nginx: OK"
echo "Deploy complete: http://119.91.114.175:18082"
REMOTE_SCRIPT
