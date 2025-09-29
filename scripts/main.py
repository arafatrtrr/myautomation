import time
import os
import sys
import logging
import random
import threading
import secrets  # <-- NEW IMPORT for random hex names
import shutil   # <-- NEW IMPORT for deleting directories
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService

from . import (logger_setup, cdp_handler, js_spoofer, browser_config, 
               ua_parser, webgl_spoofer, hardware_spoofer, workflow, 
               network_utils, proxy_handler, timezone_handler, shared_state)

logger = logging.getLogger(__name__)

# (load_config and load_user_agents are unchanged)
def load_config(project_root):
    #... (no changes)
    config_path = os.path.join(project_root, 'config', 'paths.txt')
    config = {}
    try:
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
                    except ValueError:
                        logger.warning(f"Skipping invalid line in config file: {line}")
    except FileNotFoundError:
        logger.critical(f"Configuration file not found at '{config_path}'")
        sys.exit(1)
    return config

def load_user_agents(project_root):
    #... (no changes)
    ua_path = os.path.join(project_root, 'config', 'user_agent.txt')
    try:
        with open(ua_path, 'r') as f:
            user_agents = [line.strip() for line in f if line.strip()]
        if not user_agents:
            logger.critical("User agent file is empty.")
            sys.exit(1)
        return user_agents
    except FileNotFoundError:
        logger.critical(f"User agent file not found at '{ua_path}'")
        sys.exit(1)



# In scripts/main.py, replace the entire run_single_browser_instance function with this

def run_single_browser_instance(instance_id: str, project_root: str, config: dict, user_agents: list, proxy_data: dict):
    proxy = proxy_data['proxy']
    timezone = proxy_data['timezone']
    
    extension_path = None
    try:
        selected_user_agent = random.choice(user_agents)
        webgl_profile = webgl_spoofer.get_webgl_profile_for_ua(selected_user_agent)
        hardware_profile = hardware_spoofer.get_hardware_profile_for_ua(selected_user_agent)
        spoof_details = ua_parser.get_spoof_details(selected_user_agent)
        
        unique_hex = secrets.token_hex(8)
        profile_name = f"profile_{instance_id}_{unique_hex}"
        profile_path = os.path.join(project_root, 'profiles', profile_name)
        os.makedirs(profile_path, exist_ok=True)
        logger.info(f"[{instance_id}] Created custom profile directory at: {profile_path}")
        
        extension_path = proxy_handler.create_proxy_extension(proxy, instance_id)

        options = browser_config.get_chrome_options(
            binary_path=config['CHROMIUM_BINARY_PATH'],
            profile_path=profile_path,  # <-- FIX #1: Pass the created profile_path
            user_agent=selected_user_agent,
            width=config['MOBILE_WIDTH'], height=config['MOBILE_HEIGHT'],
            pixel_ratio=config['MOBILE_PIXEL_RATIO'], proxy_extension_path=extension_path,
            timezone=timezone
        )
        service = ChromeService(executable_path=config['CHROMEDRIVER_PATH'])
        
        driver = None
        try:
            logger.info(f"[{instance_id}] Launching browser...")
            driver = webdriver.Chrome(service=service, options=options)
            
            spoof_script = js_spoofer.generate_full_spoof_script(
                user_agent=selected_user_agent, platform=spoof_details['platform'],
                app_version=spoof_details['appVersion'], vendor=spoof_details['vendor'],
                width=config['MOBILE_WIDTH'], height=config['MOBILE_HEIGHT'],
                pixel_ratio=config['MOBILE_PIXEL_RATIO'], color_depth=config['MOBILE_COLOR_DEPTH'],
                webgl_vendor=webgl_profile['vendor'], webgl_renderer=webgl_profile['renderer'],
                device_memory=hardware_profile['memory'], hardware_concurrency=hardware_profile['cores'],
                timezone=timezone
            )
            cdp_handler.apply_spoofing_script(driver=driver, script_source=spoof_script)
            
            workflow.run_browser_workflow(
                driver=driver, instance_id=instance_id, cdp_handler=cdp_handler, 
                spoof_script=spoof_script, shared_state=shared_state,
                iframe_page_url=config['IFRAME_PAGE_URL'],
                target_link_text=config['TARGET_LINK_TEXT']
            )
        finally:
            if driver:
                driver.quit()
    except Exception:
        logger.error(f"[{instance_id}] A critical error occurred in the main worker.", exc_info=True)
        # <-- FIX #2: Use the correct function name and pattern
        shared_state.update_instance_gate(instance_id, 99, "critical_failure")
    finally:
        if extension_path and os.path.exists(extension_path):
            os.remove(extension_path)
        logger.info(f"[{instance_id}] Thread finished.")

# --- NEW PROXY CHECKING WORKER ---
def check_proxy_worker(proxy, valid_proxies_list, lock, max_retries=3, retry_delay=10):
    """
    Worker function to check a single proxy with retry logic for API failures.
    """
    if not network_utils.is_internet_available():
        logger.error(f"Host internet connection lost during proxy check for {proxy['host']}.")
        return

    check_id = f"ProxyCheck-{proxy['host']}"
    
    for attempt in range(max_retries):
        location_details = timezone_handler.get_proxy_location_details(proxy, check_id)

        if location_details:
            # API call was successful, we can now check the country
            if location_details['country_code'] == 'US':
                with lock:
                    valid_proxies_list.append({
                        'proxy': proxy,
                        'timezone': location_details['timezone']
                    })
                logger.info(f"SUCCESS: Found valid US proxy: {proxy['host']}.")
            else:
                logger.warning(f"REJECTED: Proxy {proxy['host']} is in {location_details['country_code']}, not US.")
            
            return # Exit the function, as we have a definitive answer (US or not US)

        # If location_details is None, it means the API failed. We should retry.
        logger.warning(f"API FAIL: Could not verify location for {proxy['host']} on attempt {attempt + 1}/{max_retries}. Retrying in {retry_delay}s...")
        time.sleep(retry_delay)
    
    # If the loop finishes without returning, all retries have failed.
    logger.error(f"REJECTED: Failed to verify location for proxy {proxy['host']} after {max_retries} attempts.")


# In scripts/main.py, add this new function near the top

def get_user_choice(prompt_text: str, options: list) -> str:
    """Displays options to the user and returns the chosen URL."""
    print("\n" + "="*50)
    print(prompt_text)
    print("="*50)
    for i, option in enumerate(options):
        print(f"  {i+1}. {option['desc']}  ({option['url']})")
    
    while True:
        try:
            choice = int(input("Enter your choice (number): "))
            if 1 <= choice <= len(options):
                selected_url = options[choice-1]['url']
                print(f"You selected: {selected_url}\n")
                return selected_url
            else:
                print(f"Invalid number. Please enter a number between 1 and {len(options)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def main():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    logger_setup.setup_logging(project_root)
    
    selected_iframe_url = get_user_choice("Select an initial page for the workflow:", workflow.IFRAME_PAGE_OPTIONS)
    selected_target_link = get_user_choice("Select a target link to click in the first iframe:", workflow.TARGET_LINK_OPTIONS)
    
    logger.info("--- Automation Framework Started ---")
    run_mode = input("Enter 'loop' to run continuously, or press Enter to run once: ").lower().strip()
    
    config = { 
        'NUMBER_OF_BROWSERS': 10, 'LAUNCH_DELAY_SECONDS': 10, 
        'MOBILE_WIDTH': 750, 'MOBILE_HEIGHT': 1334,
        'MOBILE_PIXEL_RATIO': 2.0, 'MOBILE_COLOR_DEPTH': 24,
        'IFRAME_PAGE_URL': selected_iframe_url,
        'TARGET_LINK_TEXT': selected_target_link
    }
    
    config.update(load_config(project_root))
    user_agents = load_user_agents(project_root)
    proxy_file_path = os.path.join(project_root, 'config', 'proxies.txt')

    batch_number = 1
    while True:
        logger.info(f"--- Starting Batch #{batch_number} ---")
        
        all_proxies = proxy_handler.load_proxies(proxy_file_path)
        if not all_proxies:
            logger.info("Proxy file is empty. No more proxies to process. Exiting.")
            break
        batch_size = min(len(all_proxies), config['NUMBER_OF_BROWSERS'])
        proxies_for_this_run_raw = all_proxies[:batch_size]
        remaining_proxies = all_proxies[batch_size:]
        
        logger.info(f"Loaded {len(all_proxies)} proxies. Taking {len(proxies_for_this_run_raw)} for this batch.")
        try:
            with open(proxy_file_path, 'w') as f:
                for p in remaining_proxies:
                    f.write(f"{p['host']}:{p['port']}:{p['user']}:{p['pass']}\n")
            logger.info(f"Rewrote proxies.txt with {len(remaining_proxies)} remaining proxies.")
        except Exception as e:
            logger.error(f"Could not rewrite proxy file! Aborting. Error: {e}")
            break

        logger.info(f"Concurrently checking batch of {len(proxies_for_this_run_raw)} proxies for US location...")
        valid_proxies_for_run = []
        lock = threading.Lock()
        proxy_check_threads = []

        for proxy in proxies_for_this_run_raw:
            thread = threading.Thread(target=check_proxy_worker, args=(proxy, valid_proxies_for_run, lock))
            proxy_check_threads.append(thread)
            thread.start()
        
        for thread in proxy_check_threads:
            thread.join()
        
        if not valid_proxies_for_run:
            logger.error("No valid US proxies found in this batch. Skipping to next batch.")
            if run_mode != 'loop': break
            else: batch_number += 1; continue
        
        instance_ids = [f"Browser-{i+1}" for i in range(len(valid_proxies_for_run))]
        shared_state.initialize_state(instance_ids)
        
        threads = []
        for i, proxy_data in enumerate(valid_proxies_for_run):
            instance_id = instance_ids[i]
            
            # --- THIS IS THE CORRECTED THREAD CREATION LINE ---
            thread = threading.Thread(target=run_single_browser_instance,
                args=(instance_id, project_root, config, user_agents, proxy_data))
                
            threads.append(thread)
            thread.start()
            logger.info(f"Launched thread for {instance_id}.")
            if i < len(valid_proxies_for_run) - 1:
                logger.info(f"Waiting {config['LAUNCH_DELAY_SECONDS']} seconds before next launch...")
                time.sleep(config['LAUNCH_DELAY_SECONDS'])

        for thread in threads:
            thread.join()
        
        logger.info(f"--- Batch #{batch_number} Completed ---")

        profiles_dir = os.path.join(project_root, 'profiles')
        if os.path.exists(profiles_dir):
            try:
                shutil.rmtree(profiles_dir)
                logger.info("Successfully deleted all profile directories.")
            except Exception as e:
                logger.error(f"Error while deleting profile directories: {e}")

        if run_mode != 'loop':
            logger.info("Run mode is 'once'. Exiting loop.")
            break
        else:
            logger.info("Run mode is 'loop'. Preparing for next batch in 10 seconds...")
            time.sleep(10)
            batch_number += 1
    
    logger.info("--- All batches completed or script was stopped. Automation Finished. ---")


    
if __name__ == "__main__":
    main()