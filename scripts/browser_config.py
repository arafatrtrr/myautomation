# scripts/browser_config.py
from selenium.webdriver.chrome.options import Options as ChromeOptions

def get_chrome_options(binary_path: str, profile_path: str, user_agent: str, 
                         width: int, height: int, pixel_ratio: float, 
                         proxy_extension_path: str = None, 
                         timezone: str = None) -> ChromeOptions:
    """
    Configures and returns a ChromeOptions object, using a custom profile path.
    """
    options = ChromeOptions()
    
    if proxy_extension_path:
        options.add_extension(proxy_extension_path)
        
    options.binary_location = binary_path
    
    # Use the provided custom user data directory
    options.add_argument(f"--user-data-dir={profile_path}")
    
    if timezone:
        options.add_argument(f"--force-timezone={timezone}")
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    mobile_emulation = {
        "deviceMetrics": {"width": width, "height": height, "pixelRatio": pixel_ratio},
        "userAgent": user_agent
    }
    options.add_experimental_option("mobileEmulation", mobile_emulation)
        
    return options