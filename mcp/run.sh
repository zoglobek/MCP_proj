#!/bin/bash
# Startup script for MCP on Linux/Mac

set -e

echo "========================================="
echo "Master Control Program (MCP) - Startup"
echo "========================================="

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "[✓] Python version: $python_version"

# Check dependencies
if [ ! -d "venv" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv venv
fi

echo "[*] Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "[*] Checking dependencies..."
pip install -q --upgrade pip setuptools wheel
pip install -q -r requirements.txt

# Create directories
mkdir -p data logs backups
echo "[✓] Created necessary directories"

# Initialize database if needed
if [ ! -f "data/mcp.db" ]; then
    echo "[*] Initializing database..."
    python -c "from db.models import init_db; init_db('data/mcp.db')"
    echo "[✓] Database initialized"
fi

# Validate configuration
if [ ! -f "config.json" ]; then
    echo "[!] config.json not found. Copying from config.json.example..."
    [ -f "config.json.example" ] && cp config.json.example config.json || echo "[!] config.json.example not found"
fi

echo "[*] Validating configuration..."
python -c "from config import init_config; init_config(); print('[✓] Configuration valid')" || exit 1

echo ""
echo "========================================="
echo "Starting MCP API Server..."
echo "========================================="
echo "API: http://localhost:5000"
echo "Dashboard: http://localhost (after Docker startup)"
echo "Config: config.json"
echo "Logs: logs/"
echo ""
echo "Press Ctrl+C to stop"
echo "========================================="
echo ""

# Start the application
python main.py
