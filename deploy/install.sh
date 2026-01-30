#!/bin/bash
#
# TQQQ Trading Bot - Installation Script for Linux VMs
#
# Usage: sudo ./install.sh
#
set -e

INSTALL_DIR="/opt/tqqq"
LOG_DIR="/var/log/tqqq"
SERVICE_USER="tqqq"

echo "=========================================="
echo "TQQQ Trading Bot - Installation"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: Please run as root (sudo ./install.sh)"
    exit 1
fi

# Create service user
echo "[1/7] Creating service user..."
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /bin/false "$SERVICE_USER"
    echo "  Created user: $SERVICE_USER"
else
    echo "  User already exists: $SERVICE_USER"
fi

# Create directories
echo "[2/7] Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$INSTALL_DIR/data"
mkdir -p "$INSTALL_DIR/logs"

# Copy application files
echo "[3/7] Copying application files..."
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cp -r "$SCRIPT_DIR/tqqq" "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/scripts" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/.env.example" "$INSTALL_DIR/"

# Create .env if not exists
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    echo "  Created .env file - please configure it"
fi

# Create Python virtual environment
echo "[4/7] Setting up Python environment..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# Set permissions
echo "[5/7] Setting permissions..."
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chown -R "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR"
chmod 600 "$INSTALL_DIR/.env"

# Install systemd service
echo "[6/7] Installing systemd service..."
cp "$SCRIPT_DIR/deploy/tqqq-api.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable tqqq-api
systemctl start tqqq-api
echo "  API server started on port 8080"

# Install cron job
echo "[7/7] Installing cron job..."
cp "$SCRIPT_DIR/deploy/tqqq-cron" /etc/cron.d/tqqq
chmod 644 /etc/cron.d/tqqq
echo "  Cron job installed (runs at 6 PM ET daily)"

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Configure .env file:"
echo "     sudo nano $INSTALL_DIR/.env"
echo ""
echo "  2. Register webhook endpoints:"
echo "     curl -X POST http://localhost:8080/webhooks \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"url\": \"https://your-webhook-url\", \"name\": \"My Webhook\"}'"
echo ""
echo "  3. Fetch initial data:"
echo "     sudo -u $SERVICE_USER $INSTALL_DIR/venv/bin/python $INSTALL_DIR/scripts/fetch_data.py --full"
echo ""
echo "  4. Check status:"
echo "     curl http://localhost:8080/status"
echo "     curl http://localhost:8080/webhooks"
echo ""
echo "  5. View logs:"
echo "     tail -f $LOG_DIR/cron.log"
echo "     tail -f $LOG_DIR/api.log"
echo ""
echo "Service commands:"
echo "  systemctl status tqqq-api"
echo "  systemctl restart tqqq-api"
echo "  journalctl -u tqqq-api -f"
echo ""
