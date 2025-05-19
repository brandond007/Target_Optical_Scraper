import os
import sys
import json
import time
import select
import base64
import calendar
import subprocess
from datetime import datetime, time as dtime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from io import BytesIO
import qrcode

# ================== CONFIGURABLE SETTINGS ================== #
LOGO_FILENAMES = ["logo.jpeg", "logo.png"]
LOG_FILE = "debug_log.txt"
UPDATE_CHECK_INTERVAL = 10
GITHUB_REPO = "brandond007/target_optical_scraper"
BRANCH = "main"
SCRIPT_FILENAME = "target_optical_scraper.py"
HTML_FILENAME = "eye_appointments.html"
BANNER_FILE = ".update_required"
SKIP_LOGO_ON_UPDATE = True
CONFIG_FILE = "scraper_config.json"
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
    return "", ""

def check_update_available():
    try:
        result = subprocess.run(
            ["git", "ls-remote", f"https://github.com/{GITHUB_REPO}.git", BRANCH],
            capture_output=True, text=True
        )
        remote_hash = result.stdout.strip().split("\t")[0]
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
            logos = [f for f in LOGO_FILENAMES if os.path.exists(f)]
            for logo in logos:
                os.rename(logo, f"{logo}.bak")
        res = subprocess.run(["git", "pull"], capture_output=True, text=True)
        write_log(f"git pull result: {res.stdout} {res.stderr}")
        if SKIP_LOGO_ON_UPDATE:
            for logo in [f"{name}.bak" for name in LOGO_FILENAMES]:
                base = logo[:-4]
                if os.path.exists(logo):
                    os.replace(logo, base)
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

def display_update_banner_on_html(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    if "UPDATE REQUIRED" in html:
        return
    banner = """
    <div style="position:fixed;top:0;left:0;width:100vw;padding:60px 0;background:#fffbe6;z-index:9999;
    text-align:center;border-bottom:6px solid #ff0000;font-size:5vw;font-weight:bold;color:#cc0000;">
    🚨 UPDATE REQUIRED – UPDATING AUTOMATICALLY 🚨</div>
    """
    html = html.replace("<body>", f"<body>{banner}")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

def load_config():
    default_config = {
        "start_hour": None,
        "end_hour": None,
        "store_number": 2064
    }
    just_created = False
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=2)
        just_created = True
        return default_config, just_created
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        for key in default_config:
            if key not in data:
                data[key] = default_config[key]
        return data, just_created
    except Exception as e:
        write_log(f"Error loading config: {e}")
        return default_config, just_created

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

def get_schedule_exam_url(store_number):
    return (
        f"https://www.examappts.com/ScheduleExamView"
        f"?catalogId=12751&storeId=12001&langId=-1"
        f"&storeNumber={store_number}&clearExams=1&cid=yext_{store_number}"
    )

def run_scraper():
    try:
        config, _ = load_config()
        store_number = config.get("store_number", 2064)
        url = get_schedule_exam_url(store_number)
        print(f"[DEBUG] Using store_number: {store_number}")
        print(f"[DEBUG] Full URL: {url}")
        write_log(f"[DEBUG] Using store_number: {store_number}")
        write_log(f"[DEBUG] Full URL: {url}")

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        import platform
        if platform.machine().startswith("arm") or platform.machine().startswith("aarch"):
            chromedriver_path = "/usr/bin/chromedriver"
        else:
            from webdriver_manager.chrome import ChromeDriverManager
            chromedriver_path = ChromeDriverManager().install()

        service = ChromeService(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        })

        wait = WebDriverWait(driver, 30)
        driver.get(url)
        time.sleep(2)

        try:
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
        except Exception as e:
            write_log(f"Error finding/clicking Eye exam or No button: {e}")

        scrape_calendar(driver, wait, store_number, url)

    except Exception as e:
        write_log(f"Error in run_scraper: {e}")
        try:
            driver.quit()
        except:
            pass
        time.sleep(10)

def scrape_calendar(driver, wait, store_number, url):
    today = datetime.today()
    current_month = today.month
    current_year = today.year

    appointments_by_day = []
    max_days = 3
    total_days_scraped = 0

for month_shift in range(2):
    # If we're shifting to next month, click to next month in the calendar
    if month_shift == 1:
        try:
            next_month_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//div[contains(@class, 'cal-arrow') and contains(@class, 'right')]")
                )
            )
            driver.execute_script("arguments[0].click();", next_month_btn)
            for _ in range(20):
                try:
                    cal_header = driver.find_element(By.CSS_SELECTOR, ".cal-header-title").text.strip()
                    expected_header = datetime(current_year, current_month % 12 + 1, 1).strftime('%B %Y')
                    if expected_header in cal_header:
                        break
                except Exception:
                    pass
                time.sleep(0.3)
            if current_month == 12:
                current_month = 1
                current_year += 1
            else:
                current_month += 1
        except Exception as e:
            print("No next month or error: ", e)
            break

    # Always try to find available days for the current month,
    # regardless of whether it's the first or second iteration.
    try:
        available_elements = wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.cal-cell-day-layout.available"))
        )
    except Exception:
        print(f"❌ No available appointment days found in {calendar.month_name[current_month]} {current_year}.")
        available_elements = []  # No days found, but DON'T break—just continue

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

    qr = qrcode.make(url)
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
    <h1>Target Optical – Store #{store_number}</h1>
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

if __name__ == "__main__":
    config, just_created = load_config()
    if just_created:
        print(f"\nConfig file '{CONFIG_FILE}' has been created in this directory.")
        print("You can edit this file to set 'start_hour', 'end_hour' (0-23), and 'store_number' for the Target Optical store.")
        print("If both times are null, the script will always run. Press Enter to exit and edit the config as needed.")
        input()
        sys.exit(0)

    start_hour = config.get("start_hour", None)
    end_hour = config.get("end_hour", None)
    refresh_count = 0

    if check_update_available():
        print("🚨 UPDATE REQUIRED! Script is out of date.")
        set_update_banner(True)
        write_log("Update required at startup.")
        print("Automatically updating from GitHub...")
        if run_update():
            print("✅ Update complete! Restarting script...")
            write_log("Update applied, restarting script.")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            print("❌ Update failed. Check debug_log.txt.")
            write_log("Update failed.")
            time.sleep(10)
            sys.exit(1)
    else:
        set_update_banner(False)

    while True:
        if not is_within_schedule(start_hour, end_hour):
            print("\n[!] Outside scheduled run window. Script sleeping 60s.")
            time.sleep(60)
            continue

        if is_update_banner_set():
            display_update_banner_on_html(HTML_FILENAME)
            print("\n🚨 Update required. Automatically updating...")
            if run_update():
                print("✅ Update complete! Restarting script...")
                write_log("Update applied, restarting script.")
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                print("❌ Update failed. Check debug_log.txt.")
                write_log("Update failed.")
                time.sleep(10)
                continue

        run_scraper()
        refresh_count += 1

        if refresh_count % UPDATE_CHECK_INTERVAL == 0:
            if check_update_available():
                print("🚨 UPDATE REQUIRED! Script is out of date.")
                set_update_banner(True)
                write_log("Update required.")
                print("Automatically updating from GitHub...")
                if run_update():
                    print("✅ Update complete! Restarting script...")
                    write_log("Update applied, restarting script.")
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                else:
                    print("❌ Update failed. Check debug_log.txt.")
                    write_log("Update failed.")
                    time.sleep(10)
                    continue

        manual = countdown_timer(300)
        if manual:
            write_log("Manual refresh triggered by user.")

