# scripts/workflow.py
import time
import logging
import random
from urllib.parse import urlparse
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- Workflow Configuration Options ---
IFRAME_PAGE_OPTIONS = [
    {'desc': 'this is from momin', 'url': 'https://tinyurl.com/momin10k-003'},
    {'desc': 'this is from arefin', 'url': 'https://tinyurl.com/cbjdek-003'},
    {'desc': 'this is from thisha', 'url': 'https://cmdkduen.com'},
]

TARGET_LINK_OPTIONS = [
    {'desc': 'this is jakafiya', 'url': 'https://tinyurl.com/5n6s6hxt'},
    {'desc': 'this is from jfiej', 'url': 'https://ndjirnr.com'},
    {'desc': 'this is from nvhe', 'url': 'https://tinndjfr.com'},
]

MASTER_IFRAME_ID = "master-1"
VISIT_WEBSITE_TEXT = "Visit Website"
STATIC_SLEEP = 10
WINNERS_COUNT = 5

logger = logging.getLogger(__name__)

# --- Helper Function for getting title with retry ---
def _get_title_with_retry(driver: WebDriver, instance_id: str, wait: WebDriverWait) -> str | None:
    try:
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        title = driver.title
        if "could not be reached" in title.lower() or "problem loading page" in title.lower():
            logger.warning(f"[{instance_id}] Page load error detected ('{title}'). Reloading once...")
            driver.refresh()
            time.sleep(STATIC_SLEEP)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            title = driver.title
        return title
    except TimeoutException:
        logger.error(f"[{instance_id}] Timed out waiting for page body to get title.")
        return None
    except Exception:
        logger.error(f"[{instance_id}] Unexpected error getting page title.", exc_info=True)
        return None


def run_browser_workflow(driver: WebDriver, instance_id: str, cdp_handler, spoof_script: str, shared_state, 
                         iframe_page_url: str, target_link_text: str):
    logger.info(f"[{instance_id}] Starting coordinated workflow with page '{iframe_page_url}' and link '{target_link_text}'.")
    
    # Create Wait objects with configured timeouts
    wait_20s = WebDriverWait(driver, 20)
    wait_25s = WebDriverWait(driver, 25)
    
    try:
        # === PHASE 1: Initial Navigation & First Tab Hop ===
        driver.get(iframe_page_url) # Use the chosen URL
        time.sleep(STATIC_SLEEP)
        
        title = _get_title_with_retry(driver, instance_id, wait_20s)
        shared_state.update_instance_gate(instance_id, 1, "title_ok" if title else "failed")
        if not shared_state.wait_at_gate(instance_id, 1, []): return

        wait_25s.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//iframe[contains(@src, 'facebook.com')]")))
        time.sleep(2)
        original_window = driver.current_window_handle
        wait_25s.until(EC.element_to_be_clickable((By.LINK_TEXT, target_link_text))).click() # Use the chosen link text
        
        wait_20s.until(EC.number_of_windows_to_be(2))
        new_window = [w for w in driver.window_handles if w != original_window][0]
        driver.switch_to.window(new_window)
        cdp_handler.apply_spoofing_script(driver=driver, script_source=spoof_script)
        driver.refresh()

        # === PHASE 2: Second Page Navigation ===
        time.sleep(STATIC_SLEEP)
        title = _get_title_with_retry(driver, instance_id, wait_20s)
        shared_state.update_instance_gate(instance_id, 2, "title_ok" if title else "failed")
        if not shared_state.wait_at_gate(instance_id, 2, []): return

        wait_25s.until(EC.frame_to_be_available_and_switch_to_it((By.ID, MASTER_IFRAME_ID)))
        time.sleep(2)
        
        all_links = driver.find_elements(By.XPATH, ".//a[@href]")
        eligible_links = [link for link in all_links if len(link.text.split()) >= 2]
        if not eligible_links: raise Exception("No eligible random links found.")
        random.choice(eligible_links).click()

        # === PHASE 3: Third Page and "Visit Website" Race ===
        time.sleep(STATIC_SLEEP)
        title = _get_title_with_retry(driver, instance_id, wait_20s)
        shared_state.update_instance_gate(instance_id, 3, "title_ok" if title else "failed")
        if not shared_state.wait_at_gate(instance_id, 3, []): return

        time.sleep(5)
        driver.switch_to.default_content()
        wait_25s.until(EC.frame_to_be_available_and_switch_to_it((By.ID, MASTER_IFRAME_ID)))
        time.sleep(2)

        try:
            visit_locator = (By.XPATH, f".//a[text()='{VISIT_WEBSITE_TEXT}'] | .//span[text()='{VISIT_WEBSITE_TEXT}']")
            wait_25s.until(EC.element_to_be_clickable(visit_locator))
            
            is_winner = shared_state.attempt_to_win_race(instance_id, WINNERS_COUNT)
            if is_winner:
                driver.find_element(*visit_locator).click()
            else:
                logger.warning(f"[{instance_id}] Lost race or limit reached. Terminating.")
                return
        except TimeoutException:
            logger.error(f"[{instance_id}] Could not find '{VISIT_WEBSITE_TEXT}'. Terminating.")
            shared_state.update_instance_gate(instance_id, 99, "failed")
            return
            
        # === PHASE 4: Winners' Final Actions ===
        logger.info(f"[{instance_id}] Proceeding as a WINNER.")
        time.sleep(STATIC_SLEEP)
        title = _get_title_with_retry(driver, instance_id, wait_20s)
        shared_state.update_instance_gate(instance_id, 4, "title_ok" if title else "failed")
        if not shared_state.wait_at_gate(instance_id, 4, []): return

        time.sleep(10)
        try:
            cookie_xpath = "//*[contains(translate(., 'ACDEILOPT', 'acdeilopt'), 'allow') or contains(translate(., 'ACDEILOPT', 'acdeilopt'), 'accept')]"
            cookie_button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, cookie_xpath)))
            cookie_button.click()
            logger.info(f"[{instance_id}] Clicked a cookie button.")
        except TimeoutException:
            logger.info(f"[{instance_id}] No cookie button found within 3s, continuing.")
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        current_domain = urlparse(driver.current_url).netloc
        all_page_links = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.XPATH, "//a[@href]")))
        
        external_link_clicked = False
        num_windows_before = len(driver.window_handles)
        for link in all_page_links:
            try:
                href = link.get_attribute('href')
                if href and urlparse(href).netloc not in ['', current_domain]:
                    logger.info(f"[{instance_id}] Found external link to '{href}'. Clicking.")
                    link.click()
                    external_link_clicked = True
                    break
            except Exception:
                continue

        if external_link_clicked:
            time.sleep(3)
            if len(driver.window_handles) > num_windows_before:
                final_window = [w for w in driver.window_handles if w != driver.current_window_handle][0]
                driver.switch_to.window(final_window)
                cdp_handler.apply_spoofing_script(driver=driver, script_source=spoof_script)
                logger.info(f"[{instance_id}] Switched to final window and injected JS.")
                time.sleep(3)
            else:
                logger.info(f"[{instance_id}] External link opened in same tab.")
                time.sleep(7)
        else:
            logger.warning(f"[{instance_id}] No external link was clicked. Finishing.")
            time.sleep(2)
        
        logger.info(f"[{instance_id}] Workflow completed successfully.")

    except Exception as e:
        logger.error(f"[{instance_id}] A critical error terminated the workflow.", exc_info=True)
        shared_state.update_instance_gate(instance_id, 99, "failed")
    finally:
        shared_state.update_instance_gate(instance_id, 100, "finished")