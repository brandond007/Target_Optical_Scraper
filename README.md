        █████████
     ███         ███
   ██     ████     ██
  ██    ██    ██    ██
 ██    ██      ██    ██
 ██   ██      ██    ██
 ██    ██    ██    ██
  ██     ████     ██
   ███         ███
      █████████
 _____  _____   _____   _____   _____   _____

   T  A  R  G  E  T   O P T I C A L   S C R A P E R

=================================================================================
SETUP INSTRUCTIONS — AUTOMATED
=================================================================================

**Best for: Raspberry Pi, Ubuntu, and Debian-based systems**
            ------------  ------      ------
**1. Clone the repository:**
  
   git clone https://github.com/brandond007/target_optical_scraper.git
   cd target_optical_scraper
-----------------------------------------------------------------------
2. Run the automated setup script:-->     source setup.sh

This script will:--

Install all system dependencies (Python, pip, Chromium, Chromedriver, etc.)

Create and activate a Python virtual environment (selenium-env)

Install all required Python packages

(Optionally) Add a cron job so your scraper runs automatically at boot

You’ll end up inside the virtual environment.
---------------------------------------------
3. Place your logo:

Put your custom logo as logo.jpeg or logo.png in this folder.

The script will auto-detect which logo file to use.
-------------------------------------------------------
4. To run the scraper manually at any time:-->   python3 target_optical_scraper.py

To exit the virtual environment, type deactivate.
--------------------------------------------------------
5. To enable auto-start at boot:

If you selected "yes" during setup, this is already done!

Otherwise, re-run setup.sh and choose "yes" when prompted.
---------------------------------------------------------
6. To check logs/output from the cron job:

Check the file scraper_cron.log in this folder.

=================================================================================
NOTES ON USERNAME AND FILE LOCATIONS
This setup script and the scraper are designed to work from any folder and any username.

No more hard-coded paths or manual editing for /home/user1/ required!

Just make sure to always run everything from inside the cloned repo folder.

=================================================================================
RUNNING WITH SCREENLY OSE (KIOSK MODE)
Boot your Pi and open a terminal.

(Optional) Stop Screenly while working:


sudo systemctl stop screenly-viewer.service
Setup as described above.

Start the local web server inside the repo folder:


python3 -m http.server 8080
(Or add to crontab for auto-start; see below.)

Add the asset in the Screenly dashboard as:


http://localhost:8080/eye_appointments.html
(Optional) To make the web server auto-start at boot, you can add this to crontab:


@reboot cd /path/to/target_optical_scraper && python3 -m http.server 8080 &
=================================================================================
CHANGING THE NUMBER OF DAYS DISPLAYED
Open target_optical_scraper.py in a text editor.

Find the line near the top of the run_scraper() function:
---
max_days = 3  # <--- Change this if you want more or less days displayed
Change 3 to any number you want (e.g., 7 for a week).
---
Save the file.

=================================================================================
TROUBLESHOOTING & TIPS
If you see errors about chromedriver:

Try: sudo apt install -y chromium-driver chromium-browser

Or download a matching chromedriver for your Chromium browser version and put it in this folder.

Make it executable:

chmod +x chromedriver
If needed, update the driver line in your Python script:

service = ChromeService(executable_path="./chromedriver")
If you use a different username or folder, you do NOT need to change any code or paths.

To remove the auto-start cron job:

Edit your crontab with crontab -e and remove the relevant line(s).

To fully update everything, just pull the latest repo changes and rerun source setup.sh.

=================================================================================
SUPPORT & UPDATES
For help, open an issue on GitHub or contact the maintainer.

The script supports self-updating from GitHub—if a new version is detected, you’ll be prompted to update.

=================================================================================






