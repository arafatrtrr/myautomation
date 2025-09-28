# FINAL SCRIPT — Fully Customized
# Save as selenium_proxy_repl.py and run: python selenium_proxy_repl.py
# Requirements: pip install selenium
# Make sure the paths below match your system.

import os
import zipfile
import tempfile
import time
import sys
import shlex
import time
import random

from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, WebDriverException, JavascriptException


# ------------------- USER VALUES (from your message) -------------------
proxy_str = "pr-na.pyproxy.com:16666:new3409k-zone-resi-region-us-session-e7596f405232-sessTime-120:Usae345uh"
user_agent = "Mozilla/5.0 (Linux; Android 14; SM-S928K) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/25.4 Chrome/139.0.7114.21 Mobile Safari/537.36"
start_url = "https://tinyurl.com/momin005-001"
# ------------------- LOCAL BINARY / CHROMEDRIVER PATHS -------------------
CHROMIUM_BINARY_PATH = r"C:\Users\trr\.gologin\browser\orbita-browser-134\chrome.exe"
CHROMEDRIVER_PATH = r"C:\chromedriver.exe"
# ----------------------------------------------------------------------

def parse_proxy(proxy_string):
    parts = proxy_string.split(":")
    if len(parts) < 4:
        raise ValueError("Proxy string must be host:port:username:password")
    host = parts[0]
    port = int(parts[1])
    username = parts[2]
    password = ":".join(parts[3:])
    return host, port, username, password

def make_proxy_extension(host, port, username, password, tmpdir):
    manifest_json = """
{
  "version": "1.0.0",
  "manifest_version": 2,
  "name": "Chrome Proxy",
  "permissions": [
    "proxy",
    "tabs",
    "unlimitedStorage",
    "storage",
    "<all_urls>",
    "webRequest",
    "webRequestBlocking"
  ],
  "background": {
    "scripts": ["background.js"]
  }
}
"""
    background_js = f"""
var config = {{
    mode: "fixed_servers",
    rules: {{
      singleProxy: {{
        scheme: "http",
        host: "{host}",
        port: {port}
      }},
      bypassList: ["localhost"]
    }}
}};

chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

function callbackFn(details) {{
    return {{
        authCredentials: {{
            username: "{username}",
            password: "{password}"
        }}
    }};
}}

chrome.webRequest.onAuthRequired.addListener(
    callbackFn,
    {{urls: ["<all_urls>"]}},
    ["blocking"]
);
"""
    ext_dir = os.path.join(tmpdir, "proxy_ext")
    os.makedirs(ext_dir, exist_ok=True)
    manifest_path = os.path.join(ext_dir, "manifest.json")
    background_path = os.path.join(ext_dir, "background.js")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest_json.strip())
    with open(background_path, "w", encoding="utf-8") as f:
        f.write(background_js.strip())

    zip_path = os.path.join(tmpdir, "proxy_auth_extension.zip")
    with zipfile.ZipFile(zip_path, 'w') as z:
        z.write(manifest_path, "manifest.json")
        z.write(background_path, "background.js")
    return zip_path

def build_driver(proxy_string, user_agent_str):
    host, port, username, password = parse_proxy(proxy_string)
    tmpdir = tempfile.mkdtemp(prefix="selenium_proxy_")
    extension_path = make_proxy_extension(host, port, username, password, tmpdir)

    options = webdriver.ChromeOptions()
    options.add_extension(extension_path)
    options.add_argument(f"--user-agent={user_agent_str}")

    # Point to your Chromium binary
    options.binary_location = CHROMIUM_BINARY_PATH

    # Try to reduce automation fingerprint
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--start-maximized")

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
"""
        })
    except Exception:
        pass

    return driver

def repl_loop(driver):
    help_text = """
Interactive REPL commands:
  help
  open <url>
  click <css_selector>
  click_xpath <xpath>
  send_keys <css> <text>
  exec_js <javascript>
  get_url
  get_html
  screenshot <path.png>
  find <css_selector>
  quit
"""
    print(help_text)
    while True:
        try:
            raw = input("selenium> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting REPL and closing browser.")
            break
        if not raw:
            continue
        parts = shlex.split(raw)
        cmd = parts[0].lower()
        args = parts[1:]
        try:
            if cmd == "help":
                print(help_text)
            elif cmd == "open":
                if not args:
                    print("Usage: open <url>")
                    continue
                url = args[0]
                if not (url.startswith("http://") or url.startswith("https://")):
                    url = "http://" + url
                driver.get(url)
                print("Opened", driver.current_url)
            elif cmd == "click":
                if not args:
                    print("Usage: click <css_selector>")
                    continue
                sel = args[0]
                try:
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                    el.click()
                    print("Clicked element:", sel)
                except NoSuchElementException:
                    print("Element not found:", sel)
            elif cmd == "click_xpath":
                if not args:
                    print("Usage: click_xpath <xpath>")
                    continue
                xp = args[0]
                try:
                    el = driver.find_element(By.XPATH, xp)
                    el.click()
                    print("Clicked xpath:", xp)
                except NoSuchElementException:
                    print("XPath not found:", xp)
            elif cmd == "send_keys":
                if len(args) < 2:
                    print("Usage: send_keys <css> <text>")
                    continue
                sel = args[0]
                text = " ".join(args[1:])
                try:
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                    el.clear()
                    el.send_keys(text)
                    print("Sent keys to", sel)
                except NoSuchElementException:
                    print("Element not found:", sel)
            elif cmd == "exec_js":
                if not args:
                    print("Usage: exec_js <javascript>")
                    continue
                js = " ".join(args)
                try:
                    res = driver.execute_script(js)
                    print("Result:", res)
                except JavascriptException as e:
                    print("JS error:", e)
            elif cmd == "get_url":
                print(driver.current_url)
            elif cmd == "get_html":
                html = driver.page_source
                print(html[:5000])
                if len(html) > 5000:
                    print("... (truncated)")
            elif cmd == "screenshot":
                if not args:
                    print("Usage: screenshot <path.png>")
                    continue
                path = args[0]
                driver.save_screenshot(path)
                print("Saved screenshot to", path)
            elif cmd == "find":
                if not args:
                    print("Usage: find <css_selector>")
                    continue
                sel = args[0]
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                print(f"Found {len(els)} element(s) for selector: {sel}")
                if els:
                    try:
                        print("First element text:", els[0].text[:400])
                    except Exception:
                        print("Couldn't read text of first element.")
            elif cmd == "iframes":
                # Find all iframe elements
                frames = driver.find_elements(By.TAG_NAME, "iframe")
                print(f"Found {len(frames)} iframe(s).")
                for i, frame in enumerate(frames, 1):
                    try:
                        src = frame.get_attribute("src")
                        print(f"  [{i}] iframe src: {src}")
                    except Exception:
                        print(f"  [{i}] iframe (could not read src)")

            elif cmd == "switch_iframe":
                if not args:
                    print("Usage: switch_iframe <index>")
                    continue
                try:
                    idx = int(args[0]) - 1  # user sees 1-based index
                    frames = driver.find_elements(By.TAG_NAME, "iframe")
                    if idx < 0 or idx >= len(frames):
                        print("Invalid iframe index")
                        continue
                    driver.switch_to.frame(frames[idx])
                    print(f"Switched to iframe [{idx+1}]")
                except Exception as e:
                    print("Error switching iframe:", e)
                    
            elif cmd == "switch_iframe_id":
                        if not args:
                            print("Usage: switch_iframe_id <id>")
                            continue
                        iframe_id = args[0]
                        try:
                            driver.switch_to.frame(iframe_id)
                            print(f"Switched to iframe with ID: {iframe_id}")
                        except Exception as e:
                            print(f"Error switching to iframe with ID {iframe_id}:", e)     
                    
            elif cmd == "switch_default":
                driver.switch_to.default_content()
                print("Switched to main page (default content)")

            elif cmd == "find_xpath":
                if not args:
                    print("Usage: find_xpath <xpath>")
                    continue
                xpath = " ".join(args)
                try:
                    elements = driver.find_elements(By.XPATH, xpath)
                    print(f"Found {len(elements)} element(s) for XPath: {xpath}")
                    for i, el in enumerate(elements, 1):
                        text = el.text
                        href = el.get_attribute("href")
                        print(f"  [{i}] text: {text}")
                        if href:
                            print(f"      href: {href}")
                except Exception as e:
                    print("Error finding XPath:", e)


            elif cmd == "quit":
                print("Closing browser and exiting.")
                driver.quit()
                return
            else:
                print("Unknown command. Type 'help' to see commands.")
        except WebDriverException as e:
            print("WebDriver error:", e)
        except Exception as e:
            print("Error:", e)

def main():
    print("Starting Chromium with proxy and custom User-Agent...")
    try:
        driver = build_driver(proxy_str, user_agent)
    except Exception as e:
        print("Failed building driver. Check CHROMIUM_BINARY_PATH, CHROMEDRIVER_PATH, and selenium/chromedriver versions.")
        print("Error:", e)
        sys.exit(1)

    try:
        print("Navigating to start URL:", start_url)
        driver.get(start_url)
    except Exception as e:
        print("Failed to open start URL:", e)

    # AUTOMATION START
    print("Waiting 10 seconds for the page to load...")
    time.sleep(10)

    try:
        # Switch to first iframe
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        if len(frames) == 0:
            print("No iframe found on the page.")
        else:
            driver.switch_to.frame(frames[0])
            print("Switched to first iframe.")

            # Find <a> by its visible text
            link_text = "https://tinyurl.com/ujc3dxp8"
            try:
                # Try to find the <a> element by exact match first, then fallback to partial match
                try:
                    a_elem = driver.find_element(By.XPATH, f"//a[normalize-space(text())='{link_text}']")
                except NoSuchElementException:
                    try:
                        a_elem = driver.find_element(By.XPATH, f"//a[contains(text(), '{link_text}')]")
                    except NoSuchElementException:
                        print(f"No <a> tag found with text or containing: {link_text}")
                        a_elem = None

                if a_elem:
                    outer_html = a_elem.get_attribute("outerHTML")
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", a_elem)
                    except Exception:
                        pass
                    a_elem.click()
                    print("Found and clicked <a> tag:")
                    print(outer_html)

                    # Switch to the new tab
                    driver.switch_to.window(driver.window_handles[-1])
                    print("Switched to new tab.")

                    # Wait for the new tab to load
                    time.sleep(5)

                    # Find and print iframes with their IDs
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    print(f"Found {len(iframes)} iframe(s) in the new tab.")
                    for i, iframe in enumerate(iframes):
                        iframe_id = iframe.get_attribute("id")
                        print(f"  [{i+1}] iframe ID: {iframe_id if iframe_id else 'No ID'}")
                        # Check if there's an iframe with the name "master-1" and switch to it
                        try:
                            driver.switch_to.frame("master-1")
                            print("Switched to iframe 'master-1'.")

                            # Find all <a> tags with href inside the iframe
                            a_tags = driver.find_elements(By.XPATH, "//a[@href]")
                            print(f"Found {len(a_tags)} <a> tags with href inside the iframe.")

                            # Iterate through the <a> tags and print href and text from the <span> tag
                            for a_tag in a_tags:
                                href = a_tag.get_attribute("href")
                                span_text = a_tag.find_element(By.XPATH, ".//span").text if a_tag.find_elements(By.XPATH, ".//span") else "No span text"
                                print(f"  Href: {href}, Text: {span_text}")
                                # Click a random <a> tag found
                                if a_tags:
                                    random_a_tag = random.choice(a_tags)
                                    href = random_a_tag.get_attribute("href")
                                    print(f"Clicking a random <a> tag with href: {href}")
                                    random_a_tag.click()

                                    # Switch to the new tab
                                    driver.switch_to.window(driver.window_handles[-1])
                                    print("Switched to the new tab.")

                                    # Optionally, wait for the new tab to load
                                    time.sleep(2)
                                    break
                            # Switch back to the main content
                            driver.switch_to.default_content()
                            driver.switch_to.window(driver.window_handles[-1])
                            print("Switched back to the main content.")

                        except NoSuchElementException:
                            print("Iframe 'master-1' not found.")
                        except Exception as e:
                            print(f"An error occurred: {e}")

                else:
                    print(f"Could not find <a> tag with text: {link_text}")

            finally:
                # Stay inside iframe, REPL will continue here
                pass
    except Exception as e:
        print("Error during automated browsing:", e)

    print("Automation done. You can now use REPL commands.")

    try:
        repl_loop(driver)
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass

if __name__ == "__main__":
    main()
