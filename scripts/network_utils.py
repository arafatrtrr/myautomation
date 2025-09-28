# scripts/network_utils.py
import socket
import logging
import requests
import json

logger = logging.getLogger(__name__)

def is_internet_available(host="8.8.8.8", port=53, timeout=3):
    """
    Checks for an active internet connection by attempting to resolve Google's DNS.
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        logger.error(f"Internet connection check failed: {ex}")
        return False
