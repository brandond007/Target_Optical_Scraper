
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
(OPTIONAL): USERNAME SETUP FOR SCRIPT
=================================================================================

- This script expects your username to be **user1** and project files to be in `/home/user1/Desktop/`.
- If you set up your Raspberry Pi with a different username (for example, the default "pi" or anything else):

    1. Open a terminal (press Ctrl + Alt + F1).
    2. Type this command to see your current username:
       
           whoami

    3. Open the script file (`target_optical_scraper.py`) in a text editor.

    4. Search for every place in the script where it says:
       
           /home/user1/

       and replace **user1** with your current username (the result from `whoami`).

    5. Save the script and continue with the setup instructions.

- **This will ensure the script works with your setup, even if your username is not user1.**
=================================================================================
=================================================================================
IMPORTANT: USERNAME AND FILE PLACEMENT
=================================================================================

- During Raspberry Pi setup, name the main user **`user1`** when prompted (or set the username to `user1` using Raspberry Pi Imager or the OS setup wizard).
- **All project files in this folder must be placed in the `/home/user1/Desktop/` folder** (your Desktop folder for the `user1` account).

    Required files to place in `/home/user1/Desktop/`:
    - target_optical_scraper.py
    - target_logo.jpeg
    - (Optional: chromedriver, requirements.txt, README_instructions.txt, etc.)

- Your script expects these exact locations and filenames for everything to work correctly!

=================================================================================
=================================================================================
    SETTING UP THE APPOINTMENT DASHBOARD ON RASPBERRY PI WITH SCREENLY OSE
=================================================================================

1.  Plug your Pi into a monitor/TV and keyboard.
    Boot up and wait for the Screenly display.

2.  Open the terminal:
    - Press Ctrl + Alt + F1 (or Ctrl + Alt + F2).
    - Login: username: pi   password: raspberry

3.  [Optional] Stop Screenly while you work (so it doesn't interfere):

        sudo systemctl stop screenly-viewer.service

4.  [First time only] Expand the Pi's filesystem (if you just flashed SD):

        sudo raspi-config

    - Go to "Advanced Options" → "Expand Filesystem" → Finish and Reboot.

5.  Update Pi and install everything needed:

        sudo apt update
        sudo apt install -y python3 python3-pip python3-venv chromium-driver chromium-browser libnss3 libgconf-2-4 libxi6 libgdk-pixbuf2.0-0 libxss1 libasound2

6.  Make a project folder and move into it:

        cd ~/Desktop
        mkdir appointment-dashboard
        cd appointment-dashboard

7.  Set up Python virtual environment:

        python3 -m venv selenium-env
        source selenium-env/bin/activate

8.  Install Python tools:

        pip install selenium webdriver-manager qrcode[pil]

9.  Copy the following files into this folder:
    - Your Python script: target_optical_scraper.py
    - Your image: target_logo.jpeg

10.  Run the script (to check it works):

        python3 target_optical_scraper.py

    (It will scrape and make eye_appointments.html. You can press Ctrl+C to stop.)

11.  Open another terminal window (Ctrl + Alt + F2), log in, go to the same folder:

        cd ~/Desktop/appointment-dashboard

12.  Start a local web server to serve the HTML file:

        python3 -m http.server 8080

    (Your file is now at http://localhost:8080/eye_appointments.html)

13.  In the Screenly web dashboard (use your phone or laptop browser), add a new "Asset":
    - Use this address: http://localhost:8080/eye_appointments.html
    - This makes your dashboard show on the TV!

14.  Make everything run automatically when the Pi boots up:
    - Type:

        crontab -e

    - At the bottom, add these lines:

        @reboot cd /home/user1/Desktop/appointment-dashboard && source selenium-env/bin/activate && python3 target_optical_scraper.py &
        @reboot cd /home/user1/Desktop/appointment-dashboard && python3 -m http.server 8080 &


***"If your username is not 'user1', change all folder paths in crontab to match your username, for example /home/pi/ or /home/whatever/."****



    - Save and exit (Ctrl+O, Enter, then Ctrl+X).

15.  [Optional] Start Screenly viewer again (if you stopped it):

        sudo systemctl start screenly-viewer.service

16.  That's it! The dashboard will keep updating automatically every 5 minutes and show on your TV.

=================================================================================
         IF ANYTHING DOESN'T WORK, REBOOT THE PI OR ASK FOR HELP!
=================================================================================




(Troubleshooting Note:
If you see errors about "chromedriver" not found, not executable, or wrong version:

- Try to install using:
    

        sudo apt install -y chromium-driver chromium-browser


- If that doesn’t work:
    • Download or copy a compatible 'chromedriver' binary into your project folder (where your script is).
    • Make it executable by running:
        chmod +x chromedriver
    • Edit your Python script. Find the line:
        

        service = ChromeService(ChromeDriverManager().install())
     

 and change it to:
        

        service = ChromeService(executable_path="./chromedriver")
    

• Save your script and rerun it.

- Tip: You can find ARM (Raspberry Pi) compatible chromedriver builds online, or copy from another working Pi.
- Keeping a backup copy of chromedriver in your project folder is recommended for reliability on kiosks.
)



=================================================================================
HOW TO CHANGE THE NUMBER OF DAYS DISPLAYED
=================================================================================

- By default, the script will show the **next 3 available appointment days**.
- **To change this:**  
    1. Open `target_optical_scraper.py` in a text editor.
    2. Find the line near the top of the `run_scraper()` function:
       
           max_days = 3  # <--- Change this if you want more or less days displayed

    3. Change the number `3` to however many days you want the script to show (e.g., 1, 5, 7, etc.).
    4. Save the file.

- **Example:**  
    - To show 7 days, use:
        
          max_days = 7

- No other changes are needed—the script will always fetch up to that many available appointment days across this month and the next.

=================================================================================

FOR REFERENCE:

=================================================================================
TROUBLESHOOTING: CHROMEDRIVER FOR RASPBERRY PI
=================================================================================

- If the script fails to start due to Chromedriver issues, or you want to install a specific version manually, you can download an appropriate ARM version here:

    https://chromedriver.chromium.org/downloads

- Make sure to pick a version that matches your installed Chromium browser version.
- After downloading:
    1. Copy the "chromedriver" binary to your project folder (e.g., `/home/user1/Desktop/`).
    2. Make it executable:
           chmod +x chromedriver
    3. Edit your Python script, and change the driver line to:
           service = ChromeService(executable_path="./chromedriver")

=================================================================================

