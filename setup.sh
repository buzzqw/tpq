#!/bin/bash
set -e

echo "========================================"
echo "  TPQ Terminal - Setup"
echo "========================================"
echo ""

# --- Detect OS ---
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    OS=$(uname -s)
fi

# --- Install uv if missing ---
if ! command -v uv &>/dev/null; then
    echo "[1/4] Installing uv (Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    if ! command -v uv &>/dev/null; then
        echo "ERROR: Failed to install uv. Please install it manually:"
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    echo "       uv installed: $(uv --version)"
else
    echo "[1/4] uv already installed: $(uv --version)"
fi

# --- System dependencies (Linux only) ---
if [ "$OS" = "debian" ] || [ "$OS" = "ubuntu" ] || [ "$OS" = "linuxmint" ]; then
    echo "[2/4] Checking system dependencies..."
    MISSING=""
    dpkg -s python3-pyqt6 &>/dev/null || MISSING="$MISSING python3-pyqt6"
    dpkg -s python3-pyqt6.qtwebengine &>/dev/null || true
    dpkg -s libqt6gui6 &>/dev/null || MISSING="$MISSING libqt6gui6"

    if [ -n "$MISSING" ]; then
        echo "       Installing:$MISSING"
        sudo apt-get update -qq
        sudo apt-get install -y $MISSING
    else
        echo "       All system deps present."
    fi
elif [ "$OS" = "fedora" ]; then
    echo "[2/4] Checking system dependencies..."
    rpm -q python3-qt6 &>/dev/null || sudo dnf install -y python3-qt6
elif [ "$OS" = "arch" ]; then
    echo "[2/4] Checking system dependencies..."
    pacman -Qi python-pyqt6 &>/dev/null || sudo pacman -S --noconfirm python-pyqt6
else
    echo "[2/4] Skipping system deps (unknown OS: $OS)."
    echo "       Ensure PyQt6 is installed via your package manager."
fi

# --- Create virtual environment ---
echo "[3/4] Creating virtual environment..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ -d "$VENV_DIR" ]; then
    echo "       Removing existing .venv..."
    rm -rf "$VENV_DIR"
fi

uv venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# --- Install Python packages ---
echo "[4/4] Installing Python packages..."
uv pip install --python "$VENV_DIR/bin/python" pyte requests PyQt6 Pillow

echo ""
echo "========================================"
echo "  Setup complete!"
echo "========================================"
echo ""
echo "  Run TPQ:  $SCRIPT_DIR/tpq.sh"
echo "  Activate: source $VENV_DIR/bin/activate"
echo "  Then:     python -m tpq"
echo ""
