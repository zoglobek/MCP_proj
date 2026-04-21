#!/bin/bash
# Quick setup script for MCP development environment with virtual environment

set -e

echo "========================================="
echo "Master Control Program (MCP) - Setup"
echo "========================================="

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "[✓] Python version: $python_version"

# Check if we need to create venv
if [ ! -d "venv" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv venv
    echo "[✓] Virtual environment created"
fi

# Activate venv
echo "[*] Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "[*] Upgrading pip, setuptools, and wheel..."
pip install -q --upgrade pip setuptools wheel

# Install dependencies
echo "[*] Installing dependencies..."
pip install -q --no-cache-dir -r requirements.txt

echo "[✓] Dependencies installed"

# Create directories if needed
echo "[*] Creating necessary directories..."
cd mcp
mkdir -p data logs backups
echo "[✓] Created data, logs, and backups directories"

# Initialize database if needed
if [ ! -f "data/mcp.db" ]; then
    echo "[*] Initializing database..."
    python -c "from db.models import init_db; init_db('data/mcp.db')"
    echo "[✓] Database initialized"
else
    echo "[✓] Database already exists"
fi

# Validate configuration
echo "[*] Validating configuration..."
python -c "from config import init_config; init_config(); print('[✓] Configuration valid')" || exit 1

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "To activate the virtual environment:"
echo "  source venv/bin/activate"
echo ""
echo "To run tests:"
echo "  cd mcp && make test"
echo ""
echo "To start the API server:"
echo "  cd mcp && make run"
echo ""
echo "For more information, see VENV_SETUP.md"
echo ""
