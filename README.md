# Target Optical Scraper

## Overview

This project automatically scrapes and displays Target Optical eye appointment availability, updating every 5 minutes.  
The results are shown in a visually clear HTML dashboard, ideal for digital signage, kiosks, or in-office displays.

- **Self-updating:** Pulls updates from GitHub automatically.
- **Configurable hours:** Set run times with `scraper_config.json`.
- **Kiosk-ready:** Use on digital signage, with auto-start support.

---

## How It Works

- The Python script (`target_optical_scraper.py`) scrapes appointment availability and generates `eye_appointments.html`.
- Run hours are configurable via `scraper_config.json` (see below).
- Script auto-updates from GitHub.
- Optional: Auto-start at boot using `Initialize_auto_start.sh` (sets up a cron job).
- Runs quietly in the background (headless mode). No terminal window appears unless run manually.

---

## First-Time Setup

### Install All Dependencies

```bash
sudo apt update
sudo apt install python3 python3-pip git
pip3 install selenium webdriver-manager qrcode
```

> You may also need to install `chromium-chromedriver` or similar for your OS.

### Clone the Repository

```bash
git clone https://github.com/brandond007/target_optical_scraper.git
cd target_optical_scraper
```

#### (Optional) Add Your Logo

Save your logo as `logo.png` or `logo.jpeg` in the project directory.

---

## Configuring Run Hours (Optional)

After first run, a file named `scraper_config.json` will appear:

```json
{
  "start_hour": null,
  "end_hour": null
}
```

- Set `start_hour` and `end_hour` to desired 24-hour times (e.g., `8` for 8 AM, `18` for 6 PM).
- `null` means always-on.

---

## Test the Script

```bash
python3 target_optical_scraper.py
```

- On first run, the script creates the config file and may prompt you to edit it.

---

## Auto-Start on Boot (Kiosk Mode)

Use `Initialize_auto_start.sh` to set up auto-start in the background at boot (via cron).

### Setup

```bash
chmod +x Initialize_auto_start.sh
./Initialize_auto_start.sh
```

**What this does:**
- Adds a cronjob for your user:
  ```
  @reboot cd /path/to/target_optical_scraper && python3 target_optical_scraper.py >> scraper_cron.log 2>&1
  ```
- Script runs in the background after every reboot.
- Output and errors go to `scraper_cron.log` in the project folder.

---

## Viewing or Controlling the Background Script

- **Check if running:**
  ```bash
  ps aux | grep target_optical_scraper.py
  # or
  pgrep -af target_optical_scraper.py
  ```

- **See live output:**
  ```bash
  tail -f scraper_cron.log
  ```

- **Manually stop the script:**
  ```bash
  pkill -f target_optical_scraper.py
  ```

- **Manually run in foreground:**
  ```bash
  python3 target_optical_scraper.py
  ```

---

## Logs & Troubleshooting

- `debug_log.txt`: Detailed logs for debugging (updates, errors, scraping events).
- `scraper_cron.log`: All terminal output from cronjob.

**If the script is not updating:**
- Check both logs for errors.
- Make sure dependencies are installed and `chromedriver` is available.

---

## Configuration (`scraper_config.json`)

Control when the scraper runs (24-hour format):

```json
{
  "start_hour": 8,
  "end_hour": 18
}
```
- Example above: Runs from 8:00 to 18:59 every day.
- Use `null` for always-on.

---

## Updating the Script

- **Auto-update:**  
  Script checks for GitHub updates every 10 refreshes (about every 50 minutes by default). If an update is found, it pulls changes and restarts itself.
- **Manual update:**  
  In the project directory:
  ```bash
  git pull
  ```

---

## FAQ

**Where is the output?**  
The HTML dashboard is saved as `eye_appointments.html` in the project folder.

**How do I display it?**  
Open the file in any web browser, or point your digital signage solution to it.

**Can I see live terminal output?**  
Only if you run the script manually, or by checking `scraper_cron.log`.

**How do I disable auto-start?**  
Edit your crontab:
```bash
crontab -e
```
Remove the line referring to `target_optical_scraper.py`.

---

## Files

- `target_optical_scraper.py` – Main script
- `scraper_config.json` – Schedule configuration
- `eye_appointments.html` – Output dashboard
- `debug_log.txt` – Debugging log file
- `scraper_cron.log` – Output from cron background run
- `Initialize_auto_start.sh` – Auto-start setup script

---

## Advanced

You can run the script as another user, or as a `systemd` service for advanced setups.

For persistent digital signage, use a browser in kiosk mode pointed to `eye_appointments.html`.

---
