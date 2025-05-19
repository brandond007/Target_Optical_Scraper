Target Optical Scraper – README


(Overview)
This project automatically scrapes and displays Target Optical eye appointment availability, updating every 5 minutes.
The results are shown in a visually clear HTML dashboard, ideal for digital signage, kiosks, or in-office displays.
It supports self-updating from GitHub and can be set to run only during certain hours.

(How It Works)
Python script (target_optical_scraper.py) scrapes availability and generates the eye_appointments.html file.

Configurable: Set run hours with scraper_config.json (see below).

Auto-updates: Checks GitHub for updates and applies them automatically.

Auto-starts: With Initialize_auto_start.sh, the script will run automatically in the background at boot via cron.

Runs quietly: The script runs in the background (headless), so you won’t see a terminal window unless you run it manually.

(First-Time Setup)


(Install all dependencies:)

sudo apt update
sudo apt install python3 python3-pip git
pip3 install selenium webdriver-manager qrcode
(You may need to install chromium-chromedriver or similar for your OS.)

(Clone the repository:)

git clone https://github.com/brandond007/target_optical_scraper.git
cd target_optical_scraper
(Optional) Add your logo:
Save your logo as logo.png or logo.jpeg in the same directory.

(Configure run hours) (optional):
After first run, a file named scraper_config.json will appear:

{
  "start_hour": null,
  "end_hour": null
}
(Set these to the desired start/end hour in 24-hour format (e.g., 8 for 8 AM, 18 for 6 PM).

null means always-on.

(Test the script:)

python3 target_optical_scraper.py
(On first run, it will create the config file and may prompt you to edit it.)

(Auto-Start on Boot) (Kiosk Mode)
To run the scraper automatically at startup in the background, use the provided Initialize_auto_start.sh script.
This will create a cronjob that runs the scraper after every boot. The process is “invisible” (no terminal will pop up).

(To set up auto-start:)

chmod +x Initialize_auto_start.sh
./Initialize_auto_start.sh
(What this does:)

Adds a cronjob for your user:
@reboot cd /path/to/target_optical_scraper && python3 target_optical_scraper.py >> scraper_cron.log 2>&1

The script runs in the background after every reboot.

Output and errors go to scraper_cron.log in the project folder.

(How to View or Control the Background Script)
Since the cronjob runs the script in the background:

1. To check if it’s running

ps aux | grep target_optical_scraper.py
or

pgrep -af target_optical_scraper.py
2. To see the live output

(Check the log file produced by cron:)

tail -f scraper_cron.log

(3. To manually stop the script)

Find the process and kill it:
pkill -f target_optical_scraper.py

(4. To manually run the script in the foreground) (with terminal output)

python3 target_optical_scraper.py
Logs & Troubleshooting
debug_log.txt contains detailed logs for debugging (updates, errors, scraping events).

(scraper_cron.log shows all terminal output from the cronjob.)

(If the script is not updating:)

Check both logs for errors.

Make sure dependencies are installed and chromedriver is available.

(Configuration: scraper_config.json)
Edit this file to control when the scraper runs (24-hour format):

{
  "start_hour": 8,
  "end_hour": 18
}
(Example above runs from 8:00 to 18:59 every day.)
(Use null for always-on.)

(Updating the Script)
Auto-update:
The script checks for updates on GitHub every 10 refreshes (about every 50 minutes by default).
If an update is found, it will pull changes and restart itself automatically.

(Manual update:)
From the project directory:

git pull


(FAQ)
Where is the output?
The HTML dashboard is saved as eye_appointments.html in the project folder.

(How do I display it?)
Open the file in any web browser or point your digital signage solution to it.

(Can I see live terminal output?)
Only if you run the script manually, or by checking scraper_cron.log.

(How do I disable auto-start?)
Edit your crontab:

crontab -e
Then remove the line referring to target_optical_scraper.py.

------------Files-----------------
target_optical_scraper.py – main script

scraper_config.json – schedule configuration

eye_appointments.html – output dashboard

debug_log.txt – log file for debugging

scraper_cron.log – output from cron background run

Initialize_auto_start.sh – auto-start setup script

(Advanced)
You can run the script as another user, or as a systemd service, for more advanced setups.

For persistent digital signage, use a browser in kiosk mode pointed to eye_appointments.html.
