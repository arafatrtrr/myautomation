# scripts/cdp_handler.py
import logging
from selenium.webdriver.chrome.webdriver import WebDriver

# Get a logger for this module
logger = logging.getLogger(__name__)

def apply_spoofing_script(driver: WebDriver, script_source: str):
    """
    Uses the Chrome DevTools Protocol (CDP) to add a script that will be 
    evaluated on new document creation. This is crucial for applying spoofing 
    before the target website's own scripts can run.

    Args:
        driver: The Selenium WebDriver instance.
        script_source: A string containing the JavaScript code to inject.
    """
    try:
        logger.info("Applying CDP script to evaluate on new document.")
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': script_source
        })
    except Exception:
        # Use exc_info=True to log the full traceback for debugging
        logger.error("Failed to apply CDP spoofing script.", exc_info=True)
        # Depending on the use case, you might want to re-raise the exception
        # raise