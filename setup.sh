#!/bin/bash
set -e

echo "========================================"
echo "  TPQ Terminal - Setup"
echo "========================================"
echo ""

# --- Detect distro ---
OS_ID=""
OS_ID_LIKE=""
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_ID="${ID:-}"
    OS_ID_LIKE="${ID_LIKE:-}"
else
    OS_ID="$(uname -s)"
fi
DISTRO_MATCH="$OS_ID $OS_ID_LIKE"

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

# --- System dependencies (best-effort; uv/pip install below is the real fallback) ---
echo "[2/4] Checking system dependencies (PyQt6)..."

install_with_apt() {
    dpkg -s python3-pyqt6 &>/dev/null && return 0
    echo "       Installing PyQt6 via apt (Debian/Ubuntu family)..."
    sudo apt-get update -qq
    sudo apt-get install -y python3-pyqt6 libqt6gui6
}

install_with_dnf() {
    rpm -q python3-qt6 &>/dev/null && return 0
    echo "       Installing PyQt6 via dnf (Fedora/RHEL family)..."
    sudo dnf install -y python3-qt6
}

install_with_yum() {
    rpm -q python3-qt6 &>/dev/null && return 0
    echo "       Installing PyQt6 via yum (RHEL/CentOS family)..."
    sudo yum install -y python3-qt6
}

install_with_pacman() {
    pacman -Qi python-pyqt6 &>/dev/null && return 0
    echo "       Installing PyQt6 via pacman (Arch family)..."
    sudo pacman -Sy --noconfirm python-pyqt6
}

install_with_zypper() {
    rpm -q python3-qt6 &>/dev/null && return 0
    echo "       Installing PyQt6 via zypper (openSUSE)..."
    sudo zypper --non-interactive install python3-qt6
}

install_with_apk() {
    apk info -e py3-pyqt6 &>/dev/null && return 0
    echo "       Installing PyQt6 via apk (Alpine)..."
    sudo apk add py3-pyqt6
}

install_with_xbps() {
    xbps-query -l 2>/dev/null | grep -q python3-PyQt6 && return 0
    echo "       Installing PyQt6 via xbps (Void)..."
    sudo xbps-install -Sy python3-PyQt6
}

# Match on both ID and ID_LIKE so derivatives (Mint, Pop!_OS, Manjaro,
# EndeavourOS, Rocky, Alma, openSUSE Tumbleweed, ...) are covered without
# needing to be listed by name individually.
case "$DISTRO_MATCH" in
    *debian*|*ubuntu*)
        install_with_apt \
            || echo "       WARNING: automatic PyQt6 install failed, continuing anyway." ;;
    *rhel*|*centos*|*fedora*)
        if command -v dnf &>/dev/null; then
            install_with_dnf || echo "       WARNING: automatic PyQt6 install failed, continuing anyway."
        elif command -v yum &>/dev/null; then
            install_with_yum || echo "       WARNING: automatic PyQt6 install failed, continuing anyway."
        fi ;;
    *arch*)
        install_with_pacman \
            || echo "       WARNING: automatic PyQt6 install failed, continuing anyway." ;;
    *suse*)
        install_with_zypper \
            || echo "       WARNING: automatic PyQt6 install failed, continuing anyway." ;;
    *alpine*)
        install_with_apk \
            || echo "       WARNING: automatic PyQt6 install failed, continuing anyway." ;;
    *void*)
        install_with_xbps \
            || echo "       WARNING: automatic PyQt6 install failed, continuing anyway." ;;
    *)
        echo "       Unrecognized distro (ID=$OS_ID). Skipping system package step;"
        echo "       PyQt6 will be installed from PyPI in step 4/4 instead." ;;
esac

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
# PyQt6 wheels from PyPI bundle their own Qt6 libraries, so this works even
# when the system-package step above was skipped or failed.
echo "[4/4] Installing Python packages..."
uv pip install --python "$VENV_DIR/bin/python" pyte requests PyQt6

echo ""
echo "========================================"
echo "  Setup complete!"
echo "========================================"
echo ""
echo "  Run TPQ:  $SCRIPT_DIR/tpq.sh"
echo "  Activate: source $VENV_DIR/bin/activate"
echo "  Then:     python -m tpq"
echo ""
