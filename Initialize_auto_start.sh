#!/bin/bash

# ===============================================
#   Initialize_Auto_Start.sh
#   Universal autostart initializer for
#   Target Optical Scraper
# ===============================================

LOG_FILE="auto_start_setup.log"

echo ""
echo "========== Target Optical Scraper Auto-Start Initialization =========="
echo ""

# --- Detect script and working directory ---
SCRIPT_DIR="$(cd "$(dirname "$0")"; pwd)"
cd "$SCRIPT_DIR"

VENV_PATH="$SCRIPT_DIR/selenium-env/bin/activate"
PYTHON_SCRIPT="$SCRIPT_DIR/target_optical_scraper.py"
AUTOSTART_DIR="$HOME/.config/autostart"
AUTOSTART_DESKTOP="$AUTOSTART_DIR/target_optical_scraper.desktop"

# --- Setup: Check prerequisites ---
if [ ! -f "$VENV_PATH" ] || [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "ERROR: setup.sh has not been completed in this directory!"
    echo "Please run:  ./setup.sh"
    echo ""
    echo "[ERROR] setup.sh not found or setup incomplete. Exiting." >> "$LOG_FILE"
    exit 1
fi

# --- Detect available terminal emulator ---
TERMINAL_EMU=""
for term in lxterminal x-terminal-emulator gnome-terminal xfce4-terminal konsole mate-terminal; do
    if command -v "$term" >/dev/null 2>&1; then
        TERMINAL_EMU="$term"
        break
    fi
done

if [ -z "$TERMINAL_EMU" ]; then
    echo "ERROR: No supported terminal emulator found!"
    echo "Please install one (e.g., lxterminal) and try again."
    echo "[ERROR] No terminal emulator found. Exiting." >> "$LOG_FILE"
    exit 1
fi

# --- Create autostart directory if missing ---
if [ ! -d "$AUTOSTART_DIR" ]; then
    mkdir -p "$AUTOSTART_DIR"
    echo "[INFO] Created autostart directory: $AUTOSTART_DIR" >> "$LOG_FILE"
fi

# --- Compose the launch command ---
LAUNCH_CMD="cd \"$SCRIPT_DIR\" && source \"$VENV_PATH\" && python3 \"$PYTHON_SCRIPT\"; exec bash"

# --- .desktop file contents ---
read -r -d '' DESKTOP_CONTENT << EOM
[Desktop Entry]
Type=Application
Name=Target Optical Scraper
Comment=Runs Target Optical Scraper in terminal at login
Exec=$TERMINAL_EMU -e bash -c '$LAUNCH_CMD'
Terminal=false
EOM

# --- Write or update the autostart entry ---
if [ -f "$AUTOSTART_DESKTOP" ]; then
    # Compare existing contents; update only if changed
    if ! grep -q "$PYTHON_SCRIPT" "$AUTOSTART_DESKTOP"; then
        echo "$DESKTOP_CONTENT" > "$AUTOSTART_DESKTOP"
        echo "[INFO] Updated autostart entry at $AUTOSTART_DESKTOP" >> "$LOG_FILE"
        echo "Updated existing autostart entry."
    else
        echo "Autostart already configured. No changes made."
        echo "[INFO] Autostart entry already exists." >> "$LOG_FILE"
    fi
else
    echo "$DESKTOP_CONTENT" > "$AUTOSTART_DESKTOP"
    echo "[INFO] Wrote new autostart entry at $AUTOSTART_DESKTOP" >> "$LOG_FILE"
    echo "Autostart entry created successfully!"
fi

echo ""
echo "✅ Done! On next boot/login, your scraper will run automatically in a terminal window."
echo "To remove autostart in the future, delete:"
echo "   $AUTOSTART_DESKTOP"
echo ""
echo "[SUCCESS] Initialization complete at $(date)" >> "$LOG_FILE"

exit 0

