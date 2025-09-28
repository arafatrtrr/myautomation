# scripts/proxy_handler.py
"""
This module handles loading proxies from a file and creating a
temporary Chrome extension for authenticated proxy connections.
"""
import os
import zipfile
import json
import logging

logger = logging.getLogger(__name__)

def load_proxies(proxy_file_path: str) -> list:
    """
    Loads proxies from a text file (format: host:port:user:pass).

    Returns:
        A list of dictionaries, each representing a proxy.
    """
    proxies = []
    try:
        with open(proxy_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        host, port, user, password = line.split(':')
                        proxies.append({
                            'host': host,
                            'port': int(port),
                            'user': user,
                            'pass': password
                        })
                    except ValueError:
                        logger.warning(f"Skipping malformed proxy line: {line}")
        if not proxies:
            logger.critical("Proxy file is empty or contains no valid proxies.")
        return proxies
    except FileNotFoundError:
        logger.critical(f"Proxy file not found at '{proxy_file_path}'.")
        return []

def create_proxy_extension(proxy: dict, instance_id: str) -> str:
    """
    Creates a temporary Chrome extension as a .zip file to handle
    proxy authentication.

    Returns:
        The file path to the created .zip extension.
    """
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
                host: "{proxy['host']}",
                port: {proxy['port']}
              }},
              bypassList: ["localhost"]
            }}
          }};

    chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

    function callbackFn(details) {{
        return {{
            authCredentials: {{
                username: "{proxy['user']}",
                password: "{proxy['pass']}"
            }}
        }};
    }}

    chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {{urls: ["<all_urls>"]}},
                ['blocking']
    );
    """
    
    # Create a unique path for the extension for this instance
    extension_dir = f"temp_proxy_ext_{instance_id}"
    os.makedirs(extension_dir, exist_ok=True)
    
    path_to_manifest = os.path.join(extension_dir, "manifest.json")
    path_to_background = os.path.join(extension_dir, "background.js")
    path_to_zip = f"{extension_dir}.zip"

    with open(path_to_manifest, "w") as f:
        f.write(manifest_json)
    with open(path_to_background, "w") as f:
        f.write(background_js)
    
    with zipfile.ZipFile(path_to_zip, 'w') as zp:
        zp.write(path_to_manifest, "manifest.json")
        zp.write(path_to_background, "background.js")
    
    # Clean up the temporary directory and its contents
    os.remove(path_to_manifest)
    os.remove(path_to_background)
    os.rmdir(extension_dir)
    
    logger.info(f"Created temporary proxy extension at: {path_to_zip}")
    return path_to_zip