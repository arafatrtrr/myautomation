import time
import tkinter as tk
from tkinter import messagebox
import concurrent.futures
import threading
import base64
import zipfile
import io
import socket
import requests
import random
import os

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException, WebDriverException

# ==============================================================================
# --- 1. CONFIGURATION & GLOBAL SETUP ---
# ==============================================================================
CHROMIUM_BINARY_PATH = r"C:\Users\trr\.gologin\browser\orbita-browser-134\chrome.exe"
CHROMEDRIVER_PATH = r"C:\chromedriver.exe"
PROXY_FILE = "proxy.txt"
REUSE_PROXY_FILE = "re_proxy.txt"
WORKFLOW_TIMEOUT = 530
SLEEP_BEFORE_CLOSING = 3

# --- Custom Exception for Network Failures ---
class LocalNetworkError(Exception):
    """Custom exception to signal a local internet connection failure."""
    pass

# --- FINGERPRINT SPOOFING CONFIGURATION ---
SPOOFED_USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/138.0.7204.53 Mobile/15E148 Safari/604.1"
SPOOFED_PLATFORM = "iPhone"
SPOOFED_VIDEO_VENDOR = "Apple Inc."
SPOOFED_VIDEO_RENDERER = "Apple GPU"
CPU_CORE_OPTIONS = [2, 4, 6, 8, 10, 12, 14, 16]
RAM_OPTIONS = [4, 6, 8, 12, 16]
STORAGE_GB_OPTIONS = [32, 64, 128, 256, 512, 1024]
IPHONE_RESOLUTIONS = [
    (430, 932), (393, 852), (390, 844), (428, 926),
    (414, 896), (375, 812), (375, 667),
]

proxy_lock = threading.Lock()

# ==============================================================================
# --- 2. HELPER FUNCTIONS (Single Responsibility) ---
# ==============================================================================
def extract_timezone_id(text):
    try:
        return text.rsplit(',', 1)[1].strip()
    except (IndexError, AttributeError):
        print(f"[WARNING] Could not extract timezone from text: '{text}'")
        return None

def find_print_click(driver, by, value, profile_number, max_tries=5, delay=3, description="element"):
    for try_num in range(max_tries):
        print(f"[Profile {profile_number}] Finding '{description}' (Attempt {try_num + 1}/{max_tries})...")
        try:
            element = driver.find_element(by, value)
            print(f"[Profile {profile_number}] Found '{description}'. Clicking...")
            driver.execute_script("arguments[0].click();", element)
            print(f"[Profile {profile_number}] Successfully clicked '{description}'.")
            return True
        except (NoSuchElementException, ElementClickInterceptedException):
            print(f"[Profile {profile_number}] Did not find or could not click '{description}'. Retrying in {delay}s...")
            time.sleep(delay)
    print(f"[FATAL] [Profile {profile_number}] Could not click '{description}' after {max_tries} attempts. Stopping profile.")
    print(f"--- Sleeping for {SLEEP_BEFORE_CLOSING}s before closing. ---")
    time.sleep(SLEEP_BEFORE_CLOSING)
    return False

def save_proxy_for_reuse(proxy_str, reason="task failed"):
    if not proxy_str: return
    try:
        with proxy_lock:
            with open(REUSE_PROXY_FILE, "a") as f:
                f.write(f"{proxy_str} || {reason}\n")
        print(f"[INFO] Saved proxy '{proxy_str.split(':')[0]}' to {REUSE_PROXY_FILE} for reuse.")
    except Exception as e:
        print(f"[ERROR] Could not save proxy to reuse file. Reason: {e}")

def get_proxies_for_batch(num_needed):
    with proxy_lock:
        try:
            try:
                with open(PROXY_FILE, 'r') as f:
                    main_proxies = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                print(f"[ERROR] Main proxy file '{PROXY_FILE}' not found!")
                return []
            if not main_proxies: return []
            take_from_main = min(num_needed, len(main_proxies))
            proxies_for_batch = main_proxies[:take_from_main]
            remaining_main_proxies = main_proxies[take_from_main:]
            with open(PROXY_FILE, 'w') as f:
                for proxy in remaining_main_proxies:
                    f.write(proxy + "\n")
            print(f"[INFO] Sourced {len(proxies_for_batch)} fresh proxies from {PROXY_FILE}.")
            return proxies_for_batch
        except Exception as e:
            print(f"[FATAL PROXY ERROR] A critical error occurred while getting proxies: {e}")
            return []

def check_internet_connection(timeout=5):
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except OSError:
        return False

def get_timezone_via_proxy(proxy_str, max_retries=2, retry_delay=3):
    try:
        host, port, user, password = proxy_str.split(':')
    except (ValueError, IndexError):
        print(f"[FAILURE] Could not parse the proxy string.")
        return None
    proxy_url = f"http://{user}:{password}@{host}:{port}"
    proxies = {"http": proxy_url, "https": proxy_url}
    api_url = "https://ip-score.com/json"
    for attempt in range(max_retries):
        try:
            response = requests.post(api_url, proxies=proxies, timeout=15)
            response.raise_for_status()
            data = response.json()
            if data.get('status'):
                timezone = data.get('geoip1', {}).get('timezone')
                if timezone: return timezone
            print(f"[WARNING] Proxy '{host}' connected, but ip-score.com did not provide a timezone.")
            return None
        except requests.exceptions.RequestException:
            print(f"[INFO] Attempt {attempt + 1}/{max_retries} to connect via proxy '{host}' failed.")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                print(f"[FAILURE] All retry attempts for proxy '{host}' have failed. Diagnosing root cause...")
                if not check_internet_connection():
                    print("[DIAGNOSIS] >> Your local internet connection has failed.")
                    raise LocalNetworkError("Local internet connection failed.")
                else:
                    print(f"[DIAGNOSIS] >> Your internet is OK. The proxy '{host}' is likely dead.")
                    return None
    return None

def create_proxy_extension(proxy_str):
    try:
        host, port, user, password = proxy_str.split(':')
        manifest_json = """{"version":"1.0.0","manifest_version":2,"name":"Chrome Proxy","permissions":["proxy","tabs","unlimitedStorage","storage","<all_urls>","webRequest","webRequestBlocking"],"background":{"scripts":["background.js"]}}"""
        background_js = f"""var config={{mode:"fixed_servers",rules:{{singleProxy:{{scheme:"http",host:"{host}",port:parseInt({port})}},bypassList:["localhost"]}}}};chrome.proxy.settings.set({{value:config,scope:"regular"}},function(){{}});function callbackFn(details){{return{{authCredentials:{{username:"{user}",password:"{password}"}}}}}}chrome.webRequest.onAuthRequired.addListener(callbackFn,{{urls:["<all_urls>"]}},['blocking']);"""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", manifest_json); zf.writestr("background.js", background_js)
        return base64.b64encode(zip_buffer.getvalue()).decode()
    except (ValueError, IndexError): return None

def generate_spoofing_script():
    cpu = random.choice(CPU_CORE_OPTIONS); ram = random.choice(RAM_OPTIONS)
    storage_gb = random.choice(STORAGE_GB_OPTIONS); storage_bytes = storage_gb * 1024**3
    resolution = random.choice(IPHONE_RESOLUTIONS); width, height = resolution
    touch_points = random.randint(4, 6)
    script = f"""
    (function() {{
        Object.defineProperty(navigator, 'userAgent', {{ get: () => '{SPOOFED_USER_AGENT}', configurable: true }});
        Object.defineProperty(navigator, 'appVersion', {{ get: () => '{SPOOFED_USER_AGENT}'.replace('Mozilla/', ''), configurable: true }});
        Object.defineProperty(navigator, 'userAgentData', {{ get: () => undefined, configurable: true }});
        Object.defineProperty(screen, 'width', {{ get: () => {width}, configurable: true }});
        Object.defineProperty(screen, 'height', {{ get: () => {height}, configurable: true }});
        Object.defineProperty(screen, 'availWidth', {{ get: () => {width}, configurable: true }});
        Object.defineProperty(screen, 'availHeight', {{ get: () => {height}, configurable: true }});
        Object.defineProperty(window, 'innerWidth', {{ get: () => {width}, configurable: true }});
        Object.defineProperty(window, 'innerHeight', {{ get: () => {height}, configurable: true }});
        Object.defineProperty(window, 'outerWidth', {{ get: () => {width}, configurable: true }});
        Object.defineProperty(window, 'outerHeight', {{ get: () => {height}, configurable: true }});
        Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {cpu}, configurable: true }});
        Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {ram}, configurable: true }});
        Object.defineProperty(navigator, 'platform', {{ get: () => '{SPOOFED_PLATFORM}', configurable: true }});
        Object.defineProperty(navigator, 'maxTouchPoints', {{ get: () => {touch_points}, configurable: true }});
        Object.defineProperty(navigator, 'msMaxTouchPoints', {{ get: () => {touch_points}, configurable: true }});
        window.ontouchstart = () => {{}};
        Object.defineProperty(navigator, 'plugins', {{ get: () => ({{length: 0, item: () => undefined, namedItem: () => undefined, [Symbol.iterator]: function* () {{}}}}), configurable: true }});
        Object.defineProperty(navigator, 'mimeTypes', {{ get: () => ({{length: 0, item: () => undefined, namedItem: () => undefined, [Symbol.iterator]: function* () {{}}}}), configurable: true }});
        if (navigator.storage && navigator.storage.estimate) {{ const o=navigator.storage.estimate.bind(navigator.storage); navigator.storage.estimate=()=>o().then(e=>({{...e,quota:{storage_bytes}}})) }}
        try {{ const p=WebGLRenderingContext.prototype.getParameter; WebGLRenderingContext.prototype.getParameter=function(k){{ if(k===37445)return'{SPOOFED_VIDEO_VENDOR}'; if(k===37446)return'{SPOOFED_VIDEO_RENDERER}'; return p.apply(this,arguments) }} }} catch(e){{}}
    }})();
    """
    print(f"Generated spoofing profile: Res={width}x{height}, CPU={cpu}, RAM={ram}GB, TouchPoints={touch_points}, Plugins=0")
    return script, resolution, touch_points

def configure_browser_options(user_agent, proxy_extension, is_headless=False, resolution=None):
    options = Options()
    options.binary_location = CHROMIUM_BINARY_PATH
    options.add_argument(f'user-agent={user_agent}')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--disable-blink-features=AutomationControlled")
    if proxy_extension:
        options.add_encoded_extension(proxy_extension)
    if is_headless:
        print("[INFO] Headless mode enabled with anti-detection.")
        options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')
        if resolution:
            width, height = resolution
            options.add_argument(f'--window-size={width},{height}')
        else:
            options.add_argument('--window-size=390,844')
    return options

def launch_and_prepare_browser(options, spoofing_script, touch_points):
    try:
        service = Service(executable_path=CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_cdp_cmd("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": touch_points})
        if spoofing_script:
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": spoofing_script})
        return driver
    except WebDriverException:
        print(f"[FATAL LAUNCH ERROR] The browser process failed to start or crashed.")
        print(f"   > Most likely cause: ChromeDriver version does not match the Orbita Browser version.")
        return None
    except Exception as e:
        print(f"Failed to launch browser with an unexpected error: {e}");
        return None

def perform_browser_task(driver, timezone, profile_number):
    task_succeeded = False # Assume failure until the final step
    if timezone:
        try:
            driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": timezone})
        except Exception: pass
        print(f"[Profile {profile_number}] Navigating to ip-score.com for timezone verification...")
        
        
    else:
        print(f"[INFO] [Profile {profile_number}] Running without proxy, skipping timezone verification.")
    
    print(f"\n[Profile {profile_number}] Starting the safelink navigation workflow...")
    driver.get("https://www.revenuecpmgate.com/c06qh2nb?key=ffc7ea2b15f5cc21855e72c95de3a90a")
    time.sleep(20)
    time.sleep(SLEEP_BEFORE_CLOSING)
    task_succeeded = True
    return task_succeeded, "completed"

def run_one_profile(profile_number, is_headless, proxy=None):
    if proxy:
        print(f"--- [Profile {profile_number}]: Starting new session with proxy '{proxy.split(':')[0]}' ---")
    else:
        print(f"--- [Profile {profile_number}]: Starting new session (no proxy) ---")
    driver = None
    try:
        timezone = None
        proxy_extension = None
        if proxy:
            timezone = get_timezone_via_proxy(proxy)
            if timezone is None:
                print(f"[FAILURE] [Profile {profile_number}]: Proxy '{proxy.split(':')[0]}' is likely dead. Discarding.")
                return
            proxy_extension = create_proxy_extension(proxy)
        spoofing_script, resolution, touch_points = generate_spoofing_script()
        options = configure_browser_options(SPOOFED_USER_AGENT, proxy_extension, is_headless, resolution)
        driver = launch_and_prepare_browser(options, spoofing_script, touch_points)
        if not driver:
            if proxy: save_proxy_for_reuse(proxy, "browser launch failed")
            return
        
        task_succeeded = False
        reason = "unknown"
        result_container = []
        task_thread = threading.Thread(target=lambda: result_container.append(perform_browser_task(driver, timezone, profile_number)))
        task_thread.start()
        task_thread.join(timeout=WORKFLOW_TIMEOUT)
        
        if task_thread.is_alive():
            print(f"[TIMEOUT] [Profile {profile_number}]: Workflow timed out after {WORKFLOW_TIMEOUT}s. Terminating.")
            reason = f"workflow timed out"
        else:
            if result_container and isinstance(result_container[0], tuple):
                task_succeeded, reason = result_container[0]
                if task_succeeded:
                    print(f"[SUCCESS] [Profile {profile_number}]: Task completed successfully.")
                else:
                    print(f"[FAILURE] [Profile {profile_number}]: Task failed: {reason}")
            else:
                reason = "Task ended unexpectedly"
                print(f"[FAILURE] [Profile {profile_number}]: {reason}")
    except LocalNetworkError:
        print("\n" + "="*60)
        print(">>> CATASTROPHIC NETWORK FAILURE DETECTED <<<")
        print(">>> Your local internet connection appears to be offline. <<<")
        if proxy:
            print(f">>> Saving the currently used proxy '{proxy.split(':')[0]}' to fallback file...")
            save_proxy_for_reuse(proxy, "local network failure")
        print(">>> The script will now terminate immediately. <<<")
        print("="*60 + "\n")
        os._exit(1)
    except Exception as e:
        print(f"[ERROR] [Profile {profile_number}]: A critical error occurred: {e}")
        reason = "critical error"
    finally:
        if proxy and not task_succeeded:
            if reason == "non-american proxy":
                save_proxy_for_reuse(proxy, reason)
            elif reason != "mismatched american proxy":
                 save_proxy_for_reuse(proxy, reason)
        if driver:
            driver.quit()
        print(f"--- [Profile {profile_number}]: Finished ---")

def get_terminal_input_and_run():
    print("--- Browser Automation Launcher ---")
    while True:
        try:
            num_profiles_str = input("How many profiles to run in parallel per batch? ")
            num_profiles = int(num_profiles_str)
            if num_profiles > 0: break
            else: print("Please enter a positive number.")
        except ValueError: print("Invalid input. Please enter a number.")
    while True:
        proxy_choice = input("Continue with proxy? (1=Yes, 2=No): ").strip()
        if proxy_choice in ['1', '2']: break
        else: print("Invalid choice. Please enter '1' or '2'.")
    while True:
        mode_choice = input("Run once or loop continuously? (1=once, 2=loop): ").strip()
        if mode_choice in ['1', '2']: break
        else: print("Invalid choice. Please enter '1' or '2'.")
    while True:
        headless_choice = input("Run in headless (invisible) mode? (y/n): ").strip().lower()
        if headless_choice.startswith(('y', 'n')): break
        else: print("Invalid choice. Please enter 'y' or 'n'.")
    while True:
        concurrency_choice = input("Use Multithreading or Multiprocessing? (1=threads, 2=processes): ").strip()
        if concurrency_choice in ['1', '2']: break
        else: print("Invalid choice. Please enter '1' or '2'.")
    
    use_proxies = True if proxy_choice == '1' else False
    selected_mode = 'loop' if mode_choice == '2' else 'one_time'
    is_headless = True if headless_choice.startswith('y') else False
    Executor = concurrent.futures.ProcessPoolExecutor if concurrency_choice == '2' else concurrent.futures.ThreadPoolExecutor
    concurrency_method_name = "Multiprocessing" if concurrency_choice == '2' else "Multithreading"
    print(f"\n--- Using {concurrency_method_name} ---")
    if not use_proxies: print("--- Running WITHOUT proxies ---")
    
    if selected_mode == "loop":
        batch_number = 0
        while True:
            batch_number += 1
            print(f"\n{'='*20} Starting Batch {batch_number} {'='*20}")
            proxies_for_this_batch = []
            if use_proxies:
                proxies_for_this_batch = get_proxies_for_batch(num_profiles)
                if not proxies_for_this_batch:
                    print("[STOP] No more proxies available. Stopping continuous loop.")
                    break
            else:
                proxies_for_this_batch = [None] * num_profiles
            actual_batch_size = len(proxies_for_this_batch)
            print(f"--- Launching {actual_batch_size} profiles for this batch ---")
            profile_numbers = range(1, actual_batch_size + 1)
            headless_flags = [is_headless] * actual_batch_size
            with Executor(max_workers=actual_batch_size) as executor:
                executor.map(run_one_profile, profile_numbers, headless_flags, proxies_for_this_batch)
            print(f"\n--- Batch {batch_number} finished. ---")
            print("--- Restarting in 5 seconds... (Press Ctrl+C to stop) ---")
            time.sleep(5)
    else:
        print(f"\n--- Starting one-time run... ---")
        proxies_for_this_batch = []
        if use_proxies:
            proxies_for_this_batch = get_proxies_for_batch(num_profiles)
            if not proxies_for_this_batch:
                print("[FAILURE] No proxies available to run the batch.")
                return
        else:
            proxies_for_this_batch = [None] * num_profiles
        actual_batch_size = len(proxies_for_this_batch)
        print(f"--- Launching {actual_batch_size} profiles ---")
        profile_numbers = range(1, actual_batch_size + 1)
        headless_flags = [is_headless] * actual_batch_size
        with Executor(max_workers=actual_batch_size) as executor:
            executor.map(run_one_profile, profile_numbers, headless_flags, proxies_for_this_batch)
        print("\n--- All automation tasks have been completed. ---")

if __name__ == "__main__":
    get_terminal_input_and_run()