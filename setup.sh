#!/bin/bash

# Robust FULL SETUP SCRIPT FOR TARGET OPTICAL SCRAPER — Raspberry Pi 3B+ / Screenly

VENV_NAME="selenium-env"
PYTHON_SCRIPT="target_optical_scraper.py"
LOGO_NOTE="Keep your logo as 'logo.jpeg' or 'logo.png' in this folder."
LOG_PATH="scraper_cron.log"
CONFIG_FILE="scraper_config.json"
REPO_DIR="$(cd "$(dirname "$0")"; pwd)"
VENV_PATH="$REPO_DIR/$VENV_NAME/bin/activate"
PY_SCRIPT="$REPO_DIR/$PYTHON_SCRIPT"

echo ""
echo "========== Target Optical Scraper Full Auto-Setup =========="
echo ""

# 1. Install system dependencies (for Debian/Raspberry Pi OS/Screenly)
echo "[*] Installing system dependencies (python3, pip, dev libraries, Chromium, Chromedriver, etc.)..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git wget \
    libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev \
    libopenjp2-7-dev libtiff5-dev tk-dev \
    chromium-driver chromium-browser \
    libnss3 libgconf-2-4 libxi6 libgdk-pixbuf2.0-0 libxss1 libasound2

# 2. Try to upgrade python3 and pip to latest in the repo
echo "[*] Attempting to upgrade python3 and pip..."
sudo apt install -y python3.9 python3.9-venv python3.9-distutils || echo "python3.9 not found, using system python3"
python3 -m pip install --upgrade pip setuptools wheel

# 3. Create or update virtual environment
if command -v python3.9 &>/dev/null; then
    PY=python3.9
else
    PY=python3
fi

if [ ! -d "$VENV_NAME" ]; then
    echo "[*] Creating Python virtual environment ($VENV_NAME) with $PY..."
    $PY -m venv $VENV_NAME
else
    echo "[*] Virtual environment ($VENV_NAME) already exists."
fi

echo "[*] Activating virtual environment..."
# shellcheck source=/dev/null
source $VENV_NAME/bin/activate

echo "[*] Upgrading pip, setuptools, wheel in venv..."
pip install --upgrade pip setuptools wheel

# 4. Install required Python packages with robust error checking
echo "[*] Installing Python dependencies (selenium, webdriver-manager, qrcode[pil])..."
pip install selenium webdriver-manager qrcode[pil]
if [ $? -ne 0 ]; then
    echo "[!] Python dependency installation failed. Trying to fix by updating pip and retrying..."
    pip install --upgrade pip
    pip install selenium webdriver-manager qrcode[pil]
    if [ $? -ne 0 ]; then
        echo "[!] Dependency install failed again. Please check your Python version and system libraries!"
        exit 1
    fi
fi

# Pillow retry block (now includes missing libraries)
echo "[*] Verifying Pillow install..."
if ! python3 -c "from PIL import Image" 2>/dev/null; then
    echo "[!] Pillow install failed — retrying with additional system libraries..."
    sudo apt install -y libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev \
        libopenjp2-7-dev libtiff5-dev libwebp-dev tcl8.6-dev tk8.6-dev python3-dev
    pip install --force-reinstall pillow
fi

# 5. Create default config file if not present, with universal store_number support
if [ ! -f "$CONFIG_FILE" ]; then
    cat > "$CONFIG_FILE" <<EOL
{
  "start_hour": null,
  "end_hour": null,
  "store_number": 2064
}
EOL
    echo ""
    echo "Created $CONFIG_FILE with default store_number 2064."
    echo ""
    echo "============================================================"
    echo "You may now edit your store number and time settings as needed."
    echo "Opening $CONFIG_FILE in nano (close nano when done)..."
    echo ""
    nano "$CONFIG_FILE"
    echo ""
    echo "Press Enter to run the scraper, or Ctrl+C to abort."
    read
else
    echo ""
    echo "$CONFIG_FILE already exists."
    echo "If you wish to change the store, open it and edit the 'store_number' field."
    echo ""
fi

echo "============================================================"
echo "Setup complete! ✅"
echo ""
echo "You are now inside the '$VENV_NAME' virtual environment."
echo "To run the scraper, type:"
echo "    python3 $PYTHON_SCRIPT"
echo ""
echo "To exit the environment later, type: deactivate"
echo ""
echo "[$LOGO_NOTE]"
echo ""
echo "============================================================"

# 6. Set up cron job for auto-start at boot
echo ""
read -p "Do you want to install a cron job to run the scraper at every boot? (y/n): " installcron
if [[ "$installcron" == "y" || "$installcron" == "Y" ]]; then
    CRONLINE="@reboot cd $REPO_DIR && source $VENV_PATH && python3 $PY_SCRIPT > $LOG_PATH 2>&1 &"
    crontab -l > old_crontab.bak 2>/dev/null
    crontab -l 2>/dev/null | grep -v "$PY_SCRIPT" > new_crontab.tmp
    echo "$CRONLINE" >> new_crontab.tmp
    crontab new_crontab.tmp
    rm new_crontab.tmp
    echo ""
    echo "✅ Cron job installed!"
    echo ""
    echo "The scraper will run at every boot for user: $USER"
    echo "To remove, edit your crontab with: crontab -e"
    echo "Script output will be logged to: $REPO_DIR/$LOG_PATH"
else
    echo "Skipping cron job installation."
fi

echo ""
echo "Setup complete! Launching the Target Optical Scraper automatically..."
echo ""
$REPO_DIR/$VENV_NAME/bin/python3 $PY_SCRIPT

