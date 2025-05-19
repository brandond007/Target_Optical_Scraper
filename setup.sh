#!/bin/bash

REPO_URL="https://github.com/brandond007/target_optical_scraper.git"
FOLDER="target_optical_scraper"

# 1. Clone if needed
if [ ! -d "$FOLDER" ]; then
  echo "== Cloning repo from GitHub =="
  git clone "$REPO_URL"
  if [ $? -ne 0 ]; then
    echo "Clone failed. Exiting."
    exit 1
  fi
fi

cd "$FOLDER" || { echo "Failed to cd into $FOLDER"; exit 1; }

# 2. Ensure config.json and eye_appointments.html are in .gitignore (to preserve local config & HTML!)
if ! grep -q "^config.json" .gitignore 2>/dev/null; then
  echo "config.json" >> .gitignore
fi
if ! grep -q "^eye_appointments.html" .gitignore 2>/dev/null; then
  echo "eye_appointments.html" >> .gitignore
fi

echo "================================================================================"
echo " Target Optical Scraper — Automated Setup Script"
echo "================================================================================"

# 3. System package install (Debian/Ubuntu/Mint/RPi)
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv chromium chromium-chromedriver git

# 4. Python venv setup
if [ -d "selenium-env" ]; then
  echo "Removing old selenium-env virtual environment..."
  rm -rf selenium-env
fi

echo "Creating new Python 3 virtual environment (selenium-env)..."
python3 -m venv selenium-env

echo "Activating virtual environment..."
# shellcheck disable=SC1091
source selenium-env/bin/activate

echo "Upgrading pip, setuptools, wheel in venv..."
python -m pip install --upgrade pip setuptools wheel

echo "================================================================================"
echo "Installing Python dependencies (selenium, webdriver-manager, qrcode[pil])..."
pip install --upgrade selenium webdriver-manager qrcode[pil]

if [ $? -ne 0 ]; then
  echo "[ERROR] Python dependency installation failed."
  read -p "Press Enter to exit..."
  deactivate
  exit 1
fi

echo "[OK] All Python dependencies installed."

# 5. chromedriver fix for Ubuntu/Mint (if not in PATH)
if ! command -v chromedriver &>/dev/null && [ -f /usr/lib/chromium-browser/chromedriver ]; then
  echo "Linking chromedriver to /usr/local/bin..."
  sudo ln -sf /usr/lib/chromium-browser/chromedriver /usr/local/bin/chromedriver
fi

echo "================================================================================"
echo "Testing Selenium installation... "
python -c "import selenium, webdriver_manager, qrcode; print('OK')" || {
  echo '[FAIL: Could not import one or more dependencies]';
  read -p "Press Enter to exit..."
  deactivate
  exit 1
}
echo "[OK] Selenium, webdriver-manager, and qrcode can be imported."

echo "================================================================================"
echo "Setup complete! Your virtual environment is now active."
echo ""
echo "Next steps:"
echo " - You will be prompted to enter your store number, store name, and theme colors"
echo "   the first time you run 'python3 target_optical_scraper.py'."
echo " - This info will be saved in 'config.json' and never overwritten by updates."
echo ""
echo "To activate the venv in the future, run:"
echo "    source selenium-env/bin/activate"
echo "To run the scraper:"
echo "    python3 target_optical_scraper.py"
echo "To exit the environment, type: deactivate"
echo ""

# 6. Optional cron job
read -p "Do you want the scraper to auto-start at boot? (y/n): " AUTOSTART
if [[ "$AUTOSTART" =~ ^[Yy]$ ]]; then
  CRONLINE="@reboot cd $(pwd) && source selenium-env/bin/activate && python3 target_optical_scraper.py >> scraper_cron.log 2>&1"
  (crontab -l 2>/dev/null | grep -v "target_optical_scraper.py"; echo "$CRONLINE") | crontab -
  echo "Auto-start cron job added!"
else
  echo "Skipping auto-start setup."
fi

echo "================================================================================"
echo "All done! Happy scraping. If you see errors, check scraper_cron.log or debug_log.txt"
echo "================================================================================"

# Pause for user review if interactive
if [ -t 0 ]; then
  read -rp "Press Enter to finish setup..."
fi

if [ "$PS1" ] && [ -z "$VIRTUAL_ENV" ]; then
  echo
  echo "Dropping you into an activated virtual environment shell. To exit, type: deactivate"
  exec $SHELL --rcfile <(echo "source $(pwd)/selenium-env/bin/activate; PS1=\"(selenium-env) \$PS1\";")
fi

exit 0


