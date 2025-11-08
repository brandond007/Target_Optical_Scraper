#!/usr/bin/env python3
import os
import sys
import json
import time
import select
import base64
import calendar as calmod
import subprocess
from datetime import datetime, time as dtime
from io import BytesIO
import platform
import shutil
import re
from typing import List, Tuple, Dict, Any, Optional

import qrcode
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ================== CONFIG ================== #
HEADLESS = True  # set False once to watch it run
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
MAX_DAYS_PER_RUN = 6          # scrape up to N days each run
MONTHS_TO_SCAN = 2            # current month + N-1 next months
# ============================================ #

# -------------- Utils / Logging -------------- #
def write_log(msg: str):
    try:
        with open(LOG_FILE, "a") as f:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

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
        remote_hash = (result.stdout.strip().split("\t")[0] or "").strip()
        local_hash = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        write_log(f"Checked updates: local {local_hash}, remote {remote_hash}")
        return bool(remote_hash and local_hash and (remote_hash != local_hash))
    except Exception as e:
        write_log(f"check_update_available error: {e}")
        return False

def run_update():
    try:
        write_log("Running git pull...")
        backups = []
        if SKIP_LOGO_ON_UPDATE:
            for logo in LOGO_FILENAMES:
                if os.path.exists(logo):
                    bak = f"{logo}.bak"
                    os.replace(logo, bak)
                    backups.append((bak, logo))
        res = subprocess.run(["git", "pull"], capture_output=True, text=True)
        write_log(f"git pull => {res.stdout} {res.stderr}")
        for bak, orig in backups:
            if os.path.exists(bak):
                os.replace(bak, orig)
        if os.path.exists(BANNER_FILE):
            os.remove(BANNER_FILE)
        return True
    except Exception as e:
        write_log(f"run_update error: {e}")
        return False

def set_update_banner(flag=True):
    try:
        if flag:
            with open(BANNER_FILE, "w") as f:
                f.write("Update required\n")
        else:
            if os.path.exists(BANNER_FILE):
                os.remove(BANNER_FILE)
    except Exception:
        pass

def is_update_banner_set():
    return os.path.exists(BANNER_FILE)

def display_update_banner_on_html(html_path):
    try:
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
    except Exception as e:
        write_log(f"display_update_banner_on_html error: {e}")

def load_config():
    default_config = {"start_hour": None, "end_hour": None, "store_number": 2064}
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=2)
        return default_config, True
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        for k, v in default_config.items():
            data.setdefault(k, v)
        return data, False
    except Exception as e:
        write_log(f"load_config error: {e}")
        return default_config, False

def is_within_schedule(start_hour, end_hour):
    if start_hour is None or end_hour is None:
        return True
    now = datetime.now().time()
    sh, eh = dtime(hour=start_hour), dtime(hour=end_hour)
    return sh <= now <= eh

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

# -------------- Selenium helpers -------------- #
def build_driver():
    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,1600")
    options.add_argument("user-agent=Mozilla/5.0 (X11; Linux) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    chromium_bin = shutil.which("chromium") or shutil.which("chromium-browser") or "/usr/bin/chromium"
    if os.path.exists(chromium_bin):
        options.binary_location = chromium_bin

    driver_path = shutil.which("chromedriver") or "/usr/lib/chromium/chromedriver"
    if not os.path.exists(driver_path):
        from webdriver_manager.chrome import ChromeDriverManager
        driver_path = ChromeDriverManager().install()

    service = ChromeService(executable_path=driver_path)
    drv = webdriver.Chrome(service=service, options=options)
    try:
        drv.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"})
    except Exception:
        pass
    drv.set_page_load_timeout(60)
    drv.set_script_timeout(60)
    return drv

def safe_text(el) -> str:
    try:
        t = el.get_attribute("innerText")
        if t is None:
            t = el.text
        return (t or "").strip()
    except Exception:
        return ""

def stable_click(driver, el) -> bool:
    try:
        el.click()
        return True
    except Exception:
        pass
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        driver.execute_script("arguments[0].click();", el)
        return True
    except Exception:
        pass
    try:
        ActionChains(driver).move_to_element(el).pause(0.05).click().perform()
        return True
    except Exception:
        pass
    try:
        box = el.rect
        x = box.get("x", 0) + box.get("width", 0) / 2
        y = box.get("y", 0) + box.get("height", 0) / 2
        driver.execute_script("const [x,y]=arguments; const n=document.elementFromPoint(x,y); if(n) n.click();", x, y)
        return True
    except Exception:
        return False

def click_any_by_text(driver, labels, tags=("button","div","span","a"), timeout=6):
    end = time.time() + timeout
    while time.time() < end:
        try:
            nodes=[]
            for t in tags:
                nodes.extend(driver.find_elements(By.TAG_NAME, t))
            for n in nodes:
                if not n.is_displayed():
                    continue
                txt = safe_text(n).lower()
                al = (n.get_attribute("aria-label") or "").lower()
                for label in labels:
                    l = label.lower()
                    if l in txt or l in al:
                        if stable_click(driver, n):
                            return True
        except Exception:
            pass
        time.sleep(0.15)
    return False

def advance_continue(driver):
    click_any_by_text(driver, ["continue","next","proceed","start","get started","schedule","confirm"], timeout=3)

# --------- Calendar / iframe detection tuned for MUI --------- #
def switch_into_calendar_iframe(driver) -> bool:
    """
    Enter any iframe that clearly contains the MUI calendar:
    - a 'Go to next month' button, or
    - at least one enabled numeric day button (1-31) without .Mui-disabled
    """
    try:
        driver.switch_to.default_content()
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        for idx, fr in enumerate(frames):
            driver.switch_to.default_content()
            driver.switch_to.frame(fr)
            if driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Go to next month']"):
                write_log(f"Calendar iframe found by next-month in frame #{idx}")
                return True
            if _has_enabled_numeric_day(driver):
                write_log(f"Calendar iframe found by enabled day in frame #{idx}")
                return True
        driver.switch_to.default_content()
        return False
    except Exception as e:
        write_log(f"switch_into_calendar_iframe error: {e}")
        driver.switch_to.default_content()
        return False

def _has_enabled_numeric_day(driver) -> bool:
    day_btns = driver.find_elements(By.CSS_SELECTOR, "button.MuiButtonBase-root:not(.Mui-disabled)")
    for b in day_btns:
        t = safe_text(b)
        if t.isdigit() and 1 <= int(t) <= 31:
            return True
    return False

def wait_for_calendar_loaded(driver, timeout=25):
    wait = WebDriverWait(driver, timeout)
    # any MUI calendar pieces
    return wait.until(EC.any_of(
        EC.presence_of_element_located((By.CSS_SELECTOR, "button[aria-label='Go to next month']")),
        EC.presence_of_element_located((By.CSS_SELECTOR, "button.MuiButtonBase-root:not(.Mui-disabled)")),
    ))

def click_next_month(driver, timeout=10) -> bool:
    wait = WebDriverWait(driver, timeout)
    # Primary: exact aria-label used on your saved page
    try:
        nxt = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Go to next month']")))
        driver.execute_script("arguments[0].click();", nxt)
        return True
    except Exception:
        pass
    # Fallbacks (icon buttons)
    for xp in [
        "//button[.//*[contains(@class,'ChevronRight') or contains(@data-testid,'ChevronRight')]]",
        "(//button)[last()]"
    ]:
        try:
            nxt = wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
            driver.execute_script("arguments[0].click();", nxt)
            return True
        except Exception:
            continue
    return False

def find_enabled_day_elements(driver, target_year, target_month) -> List[Tuple[Any,int]]:
    """
    On your page, day grid is MUI <button> with numeric text; disabled days have .Mui-disabled.
    No reliable aria-label for dates; we filter spillover using the visible month header when possible.
    """
    out = []
    day_btns = driver.find_elements(By.CSS_SELECTOR, "button.MuiButtonBase-root:not(.Mui-disabled)")
    for b in day_btns:
        t = safe_text(b)
        if t.isdigit():
            d = int(t)
            if 1 <= d <= 31:
                out.append((b, d))
    return out

def month_header_text(driver) -> str:
    # try common MUI header labels
    locs = [
        (By.CSS_SELECTOR, "[class*='CalendarHeader'] [class*='Typography']"),
        (By.CSS_SELECTOR, "div.MuiPickersCalendarHeader-label"),
        (By.XPATH, "//h6[contains(@class,'MuiTypography')]"),
    ]
    for by, sel in locs:
        try:
            el = driver.find_element(by, sel)
            txt = el.text.strip()
            if txt:
                return txt
        except Exception:
            continue
    return ""

def parse_month_year_from_header(text_: str) -> Optional[Tuple[int, int]]:
    m = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", text_)
    if not m:
        return None
    return list(calmod.month_name).index(m.group(1)), int(m.group(2))

def slots_panel_visible(driver) -> bool:
    tests = [
        (By.CLASS_NAME, "aptm-box"),
        (By.XPATH, "//div[contains(@class,'aptm-box')]"),
        # generic AM/PM time tokens anywhere near a button/span
        (By.XPATH, "//*[self::button or self::div or self::span][text()[contains(.,':') and (contains(.,'AM') or contains(.,'PM'))]]"),
    ]
    for by, sel in tests:
        if driver.find_elements(by, sel):
            return True
    return False

def wait_for_slots_change(driver, prev_len=None, tries=22):
    for _ in range(tries):
        if slots_panel_visible(driver):
            return True
        cur_len = len(driver.page_source)
        if prev_len is not None and abs(cur_len - prev_len) > 250:
            return True
        time.sleep(0.35)
        prev_len = cur_len
    return False

def collect_slots_any_ui(driver) -> Tuple[Dict[str, List[str]], List[str]]:
    slots_by = {"morning": [], "afternoon": [], "evening": []}
    doctors = set()

    # Tabbed UI first
    tabs = [
        ("morning",   "//div[contains(@class,'aptm-tab-layout')][contains(.,'MORNING')]"),
        ("afternoon", "//div[contains(@class,'aptm-tab-layout')][contains(.,'AFTERNOON')]"),
        ("evening",   "//div[contains(@class,'aptm-tab-layout')][contains(.,'EVENING')]"),
    ]
    any_tab = False
    for label, xp in tabs:
        try:
            tab = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, xp)))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", tab)
            driver.execute_script("arguments[0].click();", tab)
            time.sleep(0.35)
            any_tab = True
            boxes = driver.find_elements(By.CLASS_NAME, "aptm-box")
            for box in boxes:
                try:
                    t_text = ""
                    d_text = ""
                    try:
                        t_text = box.find_element(By.CLASS_NAME, "aptm-cell-text-time").get_attribute("innerText").strip()
                    except Exception:
                        mt = re.search(r"\b\d{1,2}:\d{2}\s?(AM|PM)\b", safe_text(box))
                        t_text = mt.group(0) if mt else ""
                    try:
                        d_text = box.find_element(By.CLASS_NAME, "aptm-cell-text-provider").get_attribute("innerText").strip()
                    except Exception:
                        mt = re.search(r"Dr\.?\s+[A-Za-z][\w\- ]+", safe_text(box))
                        d_text = mt.group(0) if mt else ""
                    if t_text:
                        slots_by[label].append(t_text)
                    if d_text:
                        doctors.add(d_text.replace("Dr. ", "").replace("Dr ", "").strip())
                except Exception:
                    continue
        except Exception:
            continue

    if not any_tab:
        # flat time chips anywhere
        flat = set()
        nodes = driver.find_elements(By.XPATH, "//*[self::button or self::div or self::span]")
        for n in nodes:
            m = re.search(r"\b\d{1,2}:\d{2}\s?(AM|PM)\b", safe_text(n))
            if m:
                flat.add(m.group(0))
        if flat:
            # bucket approx
            def bucket(t):
                try:
                    hr = int(re.search(r"(\d{1,2}):", t).group(1))
                    am = "AM" in t
                    if am and hr < 11:
                        return "morning"
                    if (am and hr == 11) or (not am and hr < 5):
                        return "afternoon"
                    return "evening"
                except Exception:
                    return "afternoon"
            for t in sorted(flat):
                slots_by[bucket(t)].append(t)

        # doctor names heuristic
        for n in nodes:
            mt = re.search(r"Dr\.?\s+[A-Za-z][\w\- ]+", safe_text(n))
            if mt:
                doctors.add(mt.group(0).replace("Dr. ", "").replace("Dr ", "").strip())

    return {k: sorted(v) for k, v in slots_by.items()}, sorted(doctors)

# --------- Wizard (accept cookies + exam + seen-before) --------- #
def click_seen_before_no(driver, timeout=8) -> bool:
    end = time.time() + timeout
    qs = [
        "//*/text()[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'been seen')]/ancestor::*[1]//button[normalize-space()='No']",
        "//*/text()[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'returning patient')]/ancestor::*[1]//button[normalize-space()='No']",
        "(//button[normalize-space()='No' or normalize-space()='NO'])[1]",
        "(//button[contains(.,'No')])[1]"
    ]
    while time.time() < end:
        for xp in qs:
            try:
                el = driver.find_element(By.XPATH, xp)
                if el.is_displayed() and stable_click(driver, el):
                    print("✅ Answered 'No' to seen-before prompt")
                    return True
            except Exception:
                continue
        click_any_by_text(driver, ["i am a new patient","new patient"], timeout=1)
        time.sleep(0.25)
    return False

def navigate_intro_flow(driver):
    # Accept cookies always
    click_any_by_text(driver, ["accept all cookies","accept all","accept","i agree","got it","allow all"], timeout=3)

    # Early exit if calendar already present (either in main DOM or iframe)
    driver.switch_to.default_content()
    if driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Go to next month']") or _has_enabled_numeric_day(driver):
        print("➡️ Calendar detected immediately (skipping wizard).")
        return
    if switch_into_calendar_iframe(driver):
        if driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Go to next month']") or _has_enabled_numeric_day(driver):
            print("➡️ Calendar detected in iframe (skipping wizard).")
            return
        driver.switch_to.default_content()

    print("➡️ Clicking exam/start…")
    click_any_by_text(driver, ["eye exam","comprehensive eye exam","comprehensive exam","schedule exam","book now"], timeout=6)
    advance_continue(driver)

    print("➡️ Answering seen-before = No…")
    clicked = click_seen_before_no(driver, timeout=10)
    if not clicked:
        click_any_by_text(driver, ["no"], timeout=3)
    advance_continue(driver)

    print("➡️ Skipping optional prompts…")
    for _ in range(4):
        hit = (
            click_any_by_text(driver, ["no"], timeout=1) or
            click_any_by_text(driver, ["skip"], timeout=1) or
            click_any_by_text(driver, ["not now"], timeout=1) or
            click_any_by_text(driver, ["i don’t know","i don't know"], timeout=1)
        )
        if hit:
            advance_continue(driver)
            time.sleep(0.25)
        else:
            break

    driver.switch_to.default_content()
    if not (driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Go to next month']") or _has_enabled_numeric_day(driver)):
        switch_into_calendar_iframe(driver)

# -------------------- Scraper core -------------------- #
def run_scraper():
    driver = None
    try:
        config, _ = load_config()
        store_number = config.get("store_number", 2064)
        url = get_schedule_exam_url(store_number)
        print(f"[DEBUG] Using store_number: {store_number}")
        print(f"[DEBUG] Full URL: {url}")
        write_log(f"[DEBUG] URL: {url}")

        driver = build_driver()
        driver.get(url)
        time.sleep(1.2)

        navigate_intro_flow(driver)

        # Make sure we're in the calendar context
        driver.switch_to.default_content()
        if not (driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Go to next month']") or _has_enabled_numeric_day(driver)):
            switch_into_calendar_iframe(driver)

        scrape_calendar(driver, store_number, url)

    except Exception as e:
        write_log(f"run_scraper error: {e}")
        try:
            if driver:
                with open("last_error_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                driver.save_screenshot("last_error_page.png")
        except Exception as ee:
            write_log(f"debug save failed: {ee}")
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass

def scrape_calendar(driver, store_number, url):
    today = datetime.today()
    appts = []
    total_days = 0

    # Ensure calendar loaded
    try:
        wait_for_calendar_loaded(driver, timeout=25)
    except Exception:
        pass

    # Determine current header for better month tracking (best-effort)
    header = month_header_text(driver)
    parsed = parse_month_year_from_header(header) if header else None
    cur_month, cur_year = (parsed if parsed else (today.month, today.year))

    for month_idx in range(MONTHS_TO_SCAN):
        # Gather enabled days for (cur_year, cur_month)
        pairs = find_enabled_day_elements(driver, cur_year, cur_month)

        # filter out past days if current month
        filtered = []
        for el, dn in pairs:
            if cur_year == today.year and cur_month == today.month and dn < today.day:
                continue
            filtered.append((el, dn))

        unique_days = sorted({dn for _, dn in filtered})
        if not unique_days:
            print(f"❌ No available appointment days found in {calmod.month_name[cur_month]} {cur_year}.")
        else:
            print(f"\n📅 [{cur_year}-{cur_month:02d}] Enabled days: {unique_days}")

        for dn in unique_days:
            if total_days >= MAX_DAYS_PER_RUN:
                break

            # re-find the element fresh
            target = None
            fresh = find_enabled_day_elements(driver, cur_year, cur_month)
            for el, num in fresh:
                if num == dn:
                    target = el
                    break
            if not target:
                print(f"⚠️ Day {dn} not clickable now; skipping.")
                continue

            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
            ok = stable_click(driver, target)
            print(f"👉 Click date {dn} ({calmod.month_name[cur_month]}) {'✓' if ok else '✗'}")
            if not ok:
                continue

            prev_len = len(driver.page_source)
            wait_for_slots_change(driver, prev_len, tries=24)

            slots_by, doctors = collect_slots_any_ui(driver)
            full_date = datetime(cur_year, cur_month, dn)
            appts.append({
                "date": full_date.strftime("%A, %B %d"),
                "date_obj": full_date,
                "morning": slots_by.get("morning", []),
                "afternoon": slots_by.get("afternoon", []),
                "evening": slots_by.get("evening", []),
                "doctors": set(doctors),
            })
            total_days += 1

            # Save per-day debug if nothing
            if not any([slots_by.get("morning"), slots_by.get("afternoon"), slots_by.get("evening")]):
                try:
                    with open(f"debug_no_slots_{cur_year}-{cur_month:02d}-{dn:02d}.html","w",encoding="utf-8") as f:
                        f.write(driver.page_source)
                    driver.save_screenshot(f"debug_no_slots_{cur_year}-{cur_month:02d}-{dn:02d}.png")
                except Exception as e:
                    write_log(f"debug save failed: {e}")

        if total_days >= MAX_DAYS_PER_RUN:
            break

        # Move to next month
        if month_idx < MONTHS_TO_SCAN - 1:
            moved = click_next_month(driver)
            if not moved:
                print("No next month or unable to click next month.")
                break
            # wait a moment for calendar to swap
            time.sleep(0.5)
            header = month_header_text(driver)
            parsed = parse_month_year_from_header(header) if header else None
            if parsed:
                cur_month, cur_year = parsed
            else:
                # fallback increment
                if cur_month == 12:
                    cur_month, cur_year = 1, cur_year + 1
                else:
                    cur_month += 1

    # ---------- Build HTML ----------
    rel_days = []
    today2 = datetime.today().date()
    for d in appts:
        delta = (d["date_obj"].date() - today2).days
        if delta == 0:
            rel_days.append("Today")
        elif delta == 1:
            rel_days.append("Tomorrow")
        else:
            rel_days.append(d["date_obj"].strftime("%A"))
    avail_message = ", ".join(rel_days) if rel_days else "No appointments found"

    qr = qrcode.make(url)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    qr_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    logo_base64, logo_ext = load_logo_base64()
    logo_mime = "image/png" if logo_ext == "png" else "image/jpeg"

    first_slot = False
    day_cards = ""
    for d in appts:
        times_html = ""
        for label, icon in [("morning","🌅 Morning"),("afternoon","☀️ Afternoon"),("evening","🌙 Evening")]:
            block = f'<div class="time-block"><h4>{icon}</h4>'
            if d[label]:
                for t in d[label]:
                    css = "slot"
                    if not first_slot:
                        css += " first-slot-blink"
                        first_slot = True
                    block += f'<div class="{css}">{t}</div>'
            else:
                block += '<div class="slot none">No appointments</div>'
            block += '</div>'
            times_html += block
        docs = [f"Dr. {x}" if not x.startswith("Dr.") else x for x in sorted(d["doctors"])]
        doc_line = " & ".join(docs) if docs else "Doctor Unavailable"
        day_cards += f"""
        <div class="day-card">
          <div class="day-header"><span class="big-date">{d['date']}</span></div>
          <div class="doctor-line">{doc_line}</div>
          <div class="day-body">{times_html}</div>
        </div>"""

    html_output = f"""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Eye Appointment Schedule</title>
<style>
body {{ font-family: 'Segoe UI', sans-serif; background:#fff; color:#222; padding: 350px 20px 40px; display:flex; flex-wrap:wrap; gap:20px; justify-content:center; }}
.top-bar {{ position:fixed; top:0; left:0; right:0; background:#fff; text-align:center; padding-top:20px; z-index:50; }}
.top-bar h1 {{ font-size:min(12vw,80px); color:#cc0000; margin:0; }}
.top-bar .subtitle {{ font-size:min(6vw,40px); margin:5px 0; color:#333; }}
.top-bar .updated {{ font-size:min(5vw,28px); margin-bottom:10px; color:#222; }}
.availability {{ font-size:min(8vw,56px); color:#007700; margin-top:20px; }}
.logo {{ position:absolute; top:20px; right:20px; height:200px; }}
.qr-top-left {{ position:absolute; top:20px; left:20px; height:200px; z-index:100; }}
.first-slot-blink {{ animation: blink-text 1.2s linear infinite; font-weight:bold; }}
@keyframes blink-text {{ 0%,100% {{ color:#222; background:#e6f4ea; }} 45%,55% {{ color:#b20000; background:#ffeaea; }} }}
.day-card {{ width:420px; background:#f9f9f9; border-radius:10px; box-shadow:0 0 10px rgba(0,0,0,0.1); padding:20px; border:2px solid #ccc; }}
.day-header {{ font-size:min(6vw,32px); font-weight:bold; color:#cc0000; }}
.big-date {{ font-size:min(10vw,64px); }}
.doctor-line {{ font-size:min(5.5vw,36px); color:#1a237e; font-weight:bold; text-align:center; margin-bottom:15px; }}
.time-block {{ margin-top:15px; }}
.time-block h4 {{ font-size:min(6vw,36px); margin-bottom:5px; }}
.slot {{ font-size:min(8vw,56px); padding:16px; margin:10px 0; background:#e6f4ea; border-left:6px solid #4CAF50; border-radius:6px; text-align:center; }}
.none {{ background:#ffe5e5; border-left-color:#f44336; }}
.footer {{ width:100%; text-align:center; margin-top:40px; }}
.footer p {{ font-size:min(5vw,42px); }}
</style></head><body>
<header class="top-bar">
<img class="qr-top-left" src="data:image/png;base64,{qr_base64}" alt="QR Code">
<img class="logo" src="data:{logo_mime};base64,{logo_base64}" alt="Logo">
<h1>Target Optical – Store #{store_number}</h1>
<h2 class="subtitle">Appointment Availability</h2>
<p class="availability">Appointments available as soon as {avail_message}</p>
<p class="updated">Last updated: {datetime.now().strftime('%A, %B %d, %Y %I:%M %p')}</p>
</header>
{day_cards}
<div class="footer"><p>For appointments further out, please visit our website or scan the QR code above.</p></div>
</body></html>
"""
    with open(HTML_FILENAME, "w", encoding="utf-8") as f:
        f.write(html_output)
    print(f"✅ HTML saved at ~/{HTML_FILENAME}")

# -------------------- Main loop -------------------- #
if __name__ == "__main__":
    config, just_created = load_config()
    if just_created:
        print(f"\nConfig file '{CONFIG_FILE}' has been created.")
        print("Edit start_hour/end_hour/store_number as needed, then run again. Press Enter to exit.")
        input()
        sys.exit(0)

    start_hour = config.get("start_hour")
    end_hour = config.get("end_hour")
    refresh_count = 0

    if check_update_available():
        print("🚨 UPDATE REQUIRED! Pulling latest…")
        set_update_banner(True)
        if run_update():
            print("✅ Update complete! Restarting…")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            print("❌ Update failed. See debug_log.txt.")
            sys.exit(1)
    else:
        set_update_banner(False)

    while True:
        if not is_within_schedule(start_hour, end_hour):
            print("\n[!] Outside scheduled run window. Sleeping 60s.")
            time.sleep(60)
            continue

        if is_update_banner_set():
            display_update_banner_on_html(HTML_FILENAME)
            print("\n🚨 Update required. Pulling latest…")
            if run_update():
                print("✅ Update complete! Restarting…")
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                print("❌ Update failed. See debug_log.txt.")
                time.sleep(8)
                continue

        run_scraper()
        refresh_count += 1

        if refresh_count % UPDATE_CHECK_INTERVAL == 0 and check_update_available():
            print("🚨 UPDATE REQUIRED! Pulling latest…")
            set_update_banner(True)
            if run_update():
                print("✅ Update complete! Restarting…")
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                print("❌ Update failed. See debug_log.txt.")
                time.sleep(8)
                continue

        manual = countdown_timer(300)
        if manual:
            write_log("Manual refresh requested.")
