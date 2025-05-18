from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, time as dtime
import time
import base64
import qrcode
from io import BytesIO
import sys
import select
import calendar
import os
import subprocess
import threading

# ================== CONFIGURABLE SETTINGS ================== #
LOGO_FILENAMES = ["logo.jpeg", "logo.png"]
LOG_FILE = "debug_log.txt"
UPDATE_CHECK_INTERVAL = 10   # Check for update every N refreshes
GITHUB_REPO = "brandond007/target_optical_scraper"
BRANCH = "main"
SCRIPT_FILENAME = "target_optical_scraper.py"
HTML_FILENAME = "eye_appointments.html"
BANNER_FILE = ".update_required"
SKIP_LOGO_ON_UPDATE = True   # Prevent logo file from being overwritten
# =========================================================== #

def write_log(msg):
    with open(LOG_FILE, "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {msg}\n")

def load_logo_base64():
    for fname in LOGO_FILENAMES:
        if os.path.exists(fname):
            with open(fname, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode("utf-8"), fname.split(".")[-1]
    return "", ""  # Fallback if not found

def check_update_available():
    try:
        # Fetch remote HEAD commit hash
        result = subprocess.run(
            ["git", "ls-remote", f"https://github.com/{GITHUB_REPO}.git", BRANCH],
            capture_output=True, text=True
        )
        remote_hash = result.stdout.strip().split("\t")[0]
        # Get current HEAD commit hash
        local_hash = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        write_log(f"Checked for updates: local {local_hash}, remote {remote_hash}")
        return remote_hash != local_hash
    except Exception as e:
        write_log(f"Error checking for updates: {e}")
        return False

def run_update():
    try:
        write_log("Running update from GitHub...")
        if SKIP_LOGO_ON_UPDATE:
            # Backup logo files before pull
            logos = [f for f in LOGO_FILENAMES if os.path.exists(f)]
            for logo in logos:
                os.rename(logo, f"{logo}.bak")
        res = subprocess.run(["git", "pull"], capture_output=True, text=True)
        write_log(f"git pull result: {res.stdout} {res.stderr}")
        if SKIP_LOGO_ON_UPDATE:
            # Restore logo files (overwrite if update changed them)
            for logo in [f"{name}.bak" for name in LOGO_FILENAMES]:
                base = logo[:-4]
                if os.path.exists(logo):
                    os.replace(logo, base)
        # Remove update banner after update
        if os.path.exists(BANNER_FILE):
            os.remove(BANNER_FILE)
        write_log("Update completed successfully.")
        return True
    except Exception as e:
        write_log(f"Update failed: {e}")
        return False

def set_update_banner(flag=True):
    if flag:
        with open(BANNER_FILE, "w") as f:
            f.write("Update required\n")
    else:
        if os.path.exists(BANNER_FILE):
            os.remove(BANNER_FILE)

def is_update_banner_set():
    return os.path.exists(BANNER_FILE)

def prompt_schedule():
    print("== Scheduled Activation ==")
    try:
        inp = input("Enter active start hour (0-23, blank for always on): ").strip()
        if not inp:
            return None, None
        start_hour = int(inp)
        inp = input("Enter active end hour (0-23, blank for always on): ").strip()
        if not inp:
            return None, None
        end_hour = int(inp)
        print(f"Script will run from {start_hour:02d}:00 to {end_hour:02d}:00 daily.")
        return start_hour, end_hour
    except Exception:
        print("Invalid input, running script always.")
        return None, None

def is_within_schedule(start_hour, end_hour):
    if start_hour is None or end_hour is None:
        return True
    now = datetime.now().time()
    sh, eh = dtime(hour=start_hour), dtime(hour=end_hour)
    if sh <= now <= eh:
        return True
    return False

def countdown_timer(seconds):
    try:
        for remaining in range(seconds, 0, -1):
            mins, secs = divmod(remaining, 60)
            print(f"\r⏳ Next update in {mins:02}:{secs:02} — press Enter to refresh now. ", end='', flush=True)
            i, _, _ = select.select([sys.stdin], [], [], 1)
            if i:
                input()
                print("\n🔄 Manual refresh triggered!            ")
                return True
        print("\r🔁 Auto refresh triggered.               ")
        return False
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
        return False

def display_update_banner_on_html(html_path):
    # Inject update banner into the HTML file
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    if "UPDATE REQUIRED" in html:
        return  # Already set
    banner = """
    <div style="position:fixed;top:0;left:0;width:100vw;padding:60px 0;background:#fffbe6;z-index:9999;
    text-align:center;border-bottom:6px solid #ff0000;font-size:5vw;font-weight:bold;color:#cc0000;">
    🚨 UPDATE REQUIRED – PRESS ENTER IN TERMINAL TO UPDATE 🚨</div>
    """
    # Insert after <body>
    html = html.replace("<body>", f"<body>{banner}")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

def run_scraper():
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        })

        wait = WebDriverWait(driver, 30)
        driver.get("https://www.examappts.com/webapp/wcs/stores/servlet/EyeExamFlow?catalogId=12751&storeId=12001&langId=-1&storeNumber=2064&clearExams=1&cid=yext_2064")

        eye_exam_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[text()='Eye exam']")))
        driver.execute_script("arguments[0].click();", eye_exam_btn)
        print("✅ Clicked 'Eye exam'")

        all_divs = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "view-button-small")))
        for div in all_divs:
            if div.text.strip().lower() == "no":
                driver.execute_script("arguments[0].scrollIntoView(true);", div)
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", div)
                print("✅ Clicked 'No'")
                break

        today = datetime.today()
        current_month = today.month
        current_year = today.year

        appointments_by_day = []
        max_days = 3  # <--- Change this if you want more or less days displayed
        total_days_scraped = 0

        for month_shift in range(2):  # 0 = current month, 1 = next month only
            if month_shift == 1:
                # Click "Next Month"
                next_month_btn = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//div[contains(@class, 'cal-arrow') and contains(@class, 'right')]")
                ))
                driver.execute_script("arguments[0].click();", next_month_btn)

                # Wait for the calendar header to update to the next month
                for _ in range(20):
                    try:
                        cal_header = driver.find_element(By.CSS_SELECTOR, ".cal-header-title").text.strip()
                        expected_header = datetime(current_year, current_month % 12 + 1, 1).strftime('%B %Y')
                        if expected_header in cal_header:
                            break
                    except Exception:
                        pass
                    time.sleep(0.3)
                # Update month/year
                if current_month == 12:
                    current_month = 1
                    current_year += 1
                else:
                    current_month += 1

            available_elements = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.cal-cell-day-layout.available"))
            )
            month_days = []
            for el in available_elements:
                day_txt = el.text.strip()
                if not day_txt.isdigit():
                    continue
                day_num = int(day_txt)
                if month_shift == 0 and current_year == today.year and current_month == today.month and day_num < today.day:
                    continue
                month_days.append(day_num)

            month_days = sorted(list(set(month_days)))

            print(f"\n📅 [{current_year}-{current_month:02d}] Found days: {month_days}")

            for day_num in month_days:
                if total_days_scraped >= max_days:
                    break

                print(f"\n👉 Clicking date: {day_num} ({calendar.month_name[current_month]})")
                day_found = False
                for _ in range(3):
                    available_days = driver.find_elements(By.CSS_SELECTOR, "div.cal-cell-day-layout.available")
                    for day_element in available_days:
                        if day_element.text.strip() == str(day_num):
                            driver.execute_script("arguments[0].scrollIntoView(true);", day_element)
                            time.sleep(0.3)
                            driver.execute_script("arguments[0].click();", day_element)
                            day_found = True
                            break
                    if day_found:
                        break
                    time.sleep(1)
                if not day_found:
                    print(f"⚠️ Could not find day {day_num} on calendar. Skipping.")
                    continue

                time.sleep(1.5)
                try:
                    selected = driver.find_element(By.CSS_SELECTOR, "div.cal-cell-day-layout.selected")
                    date_label = selected.text.strip()
                except:
                    date_label = str(day_num)

                full_date = datetime(current_year, current_month, day_num)
                full_label = full_date.strftime('%A, %B %d')

                tabs = {
                    "morning": "//div[contains(@class, 'aptm-tab-layout') and contains(., 'MORNING')]",
                    "afternoon": "//div[contains(@class, 'aptm-tab-layout') and contains(., 'AFTERNOON')]",
                    "evening": "//div[contains(@class, 'aptm-tab-layout') and contains(., 'EVENING')]"
                }

                day_data = {"date": full_label, "morning": [], "afternoon": [], "evening": [], "doctors": set(), "date_obj": full_date}

                for label, xpath in tabs.items():
                    try:
                        tab = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                        driver.execute_script("arguments[0].scrollIntoView(true);", tab)
                        time.sleep(0.3)
                        driver.execute_script("arguments[0].click();", tab)
                        print(f"  ✅ Switched to {label}")
                        wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "aptm-box")))
                        time.sleep(1)
                        boxes = driver.find_elements(By.CLASS_NAME, "aptm-box")
                        for box in boxes:
                            try:
                                time_text = box.find_element(By.CLASS_NAME, "aptm-cell-text-time").text.strip()
                                doc_text = box.find_element(By.CLASS_NAME, "aptm-cell-text-provider").text.strip()
                                if time_text and doc_text:
                                    day_data[label].append(time_text)
                                    clean = doc_text.replace("Dr. ", "").strip()
                                    day_data["doctors"].add(clean)
                            except:
                                continue
                    except:
                        continue
                appointments_by_day.append(day_data)
                total_days_scraped += 1

            if total_days_scraped >= max_days:
                break

        rel_days = []
        today = datetime.today()
        for day in appointments_by_day:
            delta = (day['date_obj'].date() - today.date()).days
            if delta == 0:
                rel_days.append("Today")
            elif delta == 1:
                rel_days.append("Tomorrow")
            else:
                rel_days.append(day['date_obj'].strftime('%A'))
        avail_message = ", ".join(rel_days) if rel_days else "No appointments found"

        qr = qrcode.make("https://www.examappts.com/webapp/wcs/stores/servlet/EyeExamFlow?catalogId=12751&storeId=12001&langId=-1&storeNumber=2064&clearExams=1&cid=yext_2064")
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        logo_base64, logo_ext = load_logo_base64()
        logo_mime = "image/png" if logo_ext == "png" else "image/jpeg"

        day_cards = ""
        for day in appointments_by_day:
            times_html = ""
            for label, icon in [("morning", "🌅 Morning"), ("afternoon", "☀️ Afternoon"), ("evening", "🌙 Evening")]:
                block = f'<div class="time-block"><h4>{icon}</h4>'
                if day[label]:
                    for t in day[label]:
                        block += f'<div class="slot">{t}</div>'
                else:
                    block += '<div class="slot none">No appointments</div>'
                block += '</div>'
                times_html += block

            doctors = [f"Dr. {d}" if not d.startswith("Dr.") else d for d in sorted(day.get("doctors", []))]
            doctor_line = " & ".join(doctors) if doctors else "Doctor Unavailable"

            day_cards += f'''
            <div class="day-card">
              <div class="day-header"> <span class="big-date">{day['date']}</span></div>
              <div class="doctor-line">{doctor_line}</div>
              <div class="day-body">{times_html}</div>
            </div>'''

        html_output = f"""
        <!DOCTYPE html>
        <html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Eye Appointment Schedule</title>
        <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #fff; color: #222; padding: 350px 20px 40px; display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; }}
        .top-bar {{ position: fixed; top: 0; left: 0; right: 0; background: #fff; text-align: center; padding-top: 20px; z-index: 50; }}
        .top-bar h1 {{ font-size: min(12vw, 80px); color: #cc0000; margin: 0; }}
        .top-bar .subtitle {{ font-size: min(6vw, 40px); margin: 5px 0; color: #333; }}
        .top-bar .updated {{ font-size: min(5vw, 28px); margin-bottom: 10px; color: #222; }}
        .availability {{ font-size: min(8vw, 56px); color: #007700; margin-top: 20px; }}
        .logo {{ position: absolute; top: 20px; right: 20px; height: 200px; }}
        .day-card {{ width: 420px; background: #f9f9f9; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); padding: 20px; border: 2px solid #ccc; }}
        .day-header {{ font-size: min(6vw, 32px); font-weight: bold; color: #cc0000; }}
        .big-date {{ font-size: min(10vw, 64px); }}
        .doctor-line {{ font-size: min(5.5vw, 36px); color: #1a237e; font-weight: bold; text-align: center; margin-bottom: 15px; }}
        .time-block {{ margin-top: 15px; }}
        .time-block h4 {{ font-size: min(6vw, 36px); margin-bottom: 5px; }}
        .slot {{ font-size: min(8vw, 56px); padding: 16px; margin: 10px 0; background: #e6f4ea; border-left: 6px solid #4CAF50; border-radius: 6px; text-align: center; }}
        .none {{ background: #ffe5e5; border-left-color: #f44336; }}
        .footer {{ width: 100%; text-align: center; margin-top: 40px; }}
        .footer p {{ font-size: min(5vw, 42px); }}
        .footer img {{ height: 360px; margin-top: 10px; }}
        </style></head><body>
        <header class="top-bar">
        <img class="logo" src="data:{logo_mime};base64,{logo_base64}" alt="Logo">
        <h1>Target Optical – Lino Lakes</h1>
        <h2 class="subtitle">Appointment Availability</h2>
        <p class="availability">Appointments available as soon as {avail_message}</p>
        <p class="updated">Last updated: {datetime.now().strftime('%A, %B %d, %Y %I:%M %p')}</p>
        </header>{day_cards}<div class="footer">
        <p>For appointments further out, please visit our website or scan the QR code:</p>
        <img src="data:image/png;base64,{qr_base64}" alt="QR Code"></div></body></html>
        """

        with open(HTML_FILENAME, "w", encoding="utf-8") as f:
            f.write(html_output)

        if is_update_banner_set():
            display_update_banner_on_html(HTML_FILENAME)

        print(f"✅ HTML saved at ~/{HTML_FILENAME}")
        driver.quit()
    except Exception as e:
        write_log(f"Error in run_scraper: {e}")
        try:
            driver.quit()
        except:
            pass
        time.sleep(10)

# ============= MAIN SCRIPT ============= #

if __name__ == "__main__":
    # Get schedule config at start
    start_hour, end_hour = prompt_schedule()
    refresh_count = 0

    # Check for update at script start
    if check_update_available():
        print("🚨 UPDATE REQUIRED! Script is out of date.")
        set_update_banner(True)
        write_log("Update required at startup.")
    else:
        set_update_banner(False)

    while True:
        # Check time window for scheduled running
        if not is_within_schedule(start_hour, end_hour):
            print("\n[!] Outside scheduled run window. Script sleeping 60s.")
            time.sleep(60)
            continue

        if is_update_banner_set():
            # Pause and show update banner in HTML
            display_update_banner_on_html(HTML_FILENAME)
            print("\n🚨 Update required. Press ENTER to run updater and resume.")
            while is_update_banner_set():
                i, _, _ = select.select([sys.stdin], [], [], 1)
                if i:
                    input()
                    print("🔄 Running updater...")
                    if run_update():
                        print("✅ Update complete! Script resuming.")
                        write_log("Update applied, resuming script.")
                    else:
                        print("❌ Update failed. Check debug_log.txt.")
                        write_log("Update failed.")
                else:
                    time.sleep(1)
            continue  # After update, rerun scraper

        run_scraper()
        refresh_count += 1

        # Check for updates every UPDATE_CHECK_INTERVAL refreshes
        if refresh_count % UPDATE_CHECK_INTERVAL == 0:
            if check_update_available():
                print("🚨 UPDATE REQUIRED! Script is out of date.")
                set_update_banner(True)
                write_log("Update required.")
                continue

        manual = countdown_timer(300)
        if manual:
            write_log("Manual refresh triggered by user.")

