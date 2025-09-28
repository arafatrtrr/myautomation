# scripts/timezone_handler.py
"""
This module handles discovering the timezone and location of a proxy.
"""
import requests
import logging

logger = logging.getLogger(__name__)

IP_ECHO_SERVICE_URL = "https://api.ipify.org?format=json"
TIMEZONE_API_URL = "https://ip-score.com/json"

def get_proxy_location_details(proxy: dict, instance_id: str) -> dict | None:
    """
    Finds the location details (timezone and country code) for a given proxy.

    Returns:
        A dictionary {'timezone': '...', 'country_code': '...'} or None on failure.
    """
    proxy_url = f"http://{proxy['user']}:{proxy['pass']}@{proxy['host']}:{proxy['port']}"
    proxies_for_request = {"http": proxy_url, "https": proxy_url}
    
    public_ip = None
    try:
        logger.info(f"[{instance_id}] Discovering public IP for proxy {proxy['host']}...")
        response = requests.get(IP_ECHO_SERVICE_URL, proxies=proxies_for_request, timeout=20)
        response.raise_for_status()
        public_ip = response.json().get('ip')
        if not public_ip:
            logger.error(f"[{instance_id}] IP echo service did not return an IP address.")
            return None
        logger.info(f"[{instance_id}] Proxy public IP discovered: {public_ip}")

    except requests.exceptions.RequestException as e:
        logger.error(f"[{instance_id}] Failed to connect through proxy to get public IP. Error: {e}")
        return None

    try:
        logger.info(f"[{instance_id}] Querying ip-score.com for location of {public_ip}...")
        response = requests.post(TIMEZONE_API_URL, files={'ip': (None, public_ip)}, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        geoip = data.get("geoip1", {})
        timezone = geoip.get("timezone")
        country_code = geoip.get("countrycode")
        
        if not timezone or not country_code:
            logger.error(f"[{instance_id}] API response missing timezone or countrycode.")
            return None
            
        logger.info(f"[{instance_id}] Location found: Timezone='{timezone}', Country='{country_code}'")
        return {'timezone': timezone, 'country_code': country_code}

    except requests.exceptions.RequestException as e:
        logger.error(f"[{instance_id}] Failed to get location from ip-score API. Error: {e}")
        return None
    except Exception:
        logger.error(f"[{instance_id}] Error parsing location response.", exc_info=True)
        return None