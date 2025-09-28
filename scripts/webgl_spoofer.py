# scripts/webgl_spoofer.py
"""
This module provides categorized lists of mobile WebGL profiles and
selects a realistic one based on the provided user-agent string.
"""
import random
import logging

logger = logging.getLogger(__name__)

# --- Categorized GPU Profiles ---

# Apple GPUs are consistent across iPhones/iPads
APPLE_GPUS = [
    {'vendor': 'Apple Inc.', 'renderer': 'Apple A16 GPU'},
    {'vendor': 'Apple Inc.', 'renderer': 'Apple A15 GPU'},
    {'vendor': 'Apple Inc.', 'renderer': 'Apple A14 GPU'},
    {'vendor': 'Apple Inc.', 'renderer': 'Apple A13 GPU'},
]

# ARM Mali GPUs are common in Samsung (Exynos) and other non-Qualcomm Androids
ARM_GPUS = [
    {'vendor': 'ARM', 'renderer': 'Mali-G710 MP10'},
    {'vendor': 'ARM', 'renderer': 'Mali-G78 MP14'},
    {'vendor': 'ARM', 'renderer': 'Mali-G77 MC9'},
    {'vendor': 'ARM', 'renderer': 'Mali-G76 MC4'},
    {'vendor': 'ARM', 'renderer': 'Mali-G57 MC2'},
    {'vendor': 'ARM', 'renderer': 'Mali-G52 MC2'},
]

# Qualcomm Adreno GPUs are the most common in the general Android ecosystem
QUALCOMM_GPUS = [
    {'vendor': 'Qualcomm', 'renderer': 'Adreno (TM) 740'},
    {'vendor': 'Qualcomm', 'renderer': 'Adreno (TM) 730'},
    {'vendor': 'Qualcomm', 'renderer': 'Adreno (TM) 660'},
    {'vendor': 'Qualcomm', 'renderer': 'Adreno (TM) 650'},
    {'vendor': 'Qualcomm', 'renderer': 'Adreno (TM) 640'},
    {'vendor': 'Qualcomm', 'renderer': 'Adreno (TM) 630'},
    {'vendor': 'Qualcomm', 'renderer': 'Adreno (TM) 618'},
]

# NVIDIA Tegra is specific to devices like the Nintendo Switch
NVIDIA_GPUS = [
    {'vendor': 'NVIDIA Corporation', 'renderer': 'NVIDIA Tegra X1'},
]

def get_webgl_profile_for_ua(user_agent: str):
    """
    Selects a realistic WebGL vendor/renderer based on the user-agent string.

    Args:
        user_agent: The user-agent string of the browser.

    Returns:
        A dictionary with 'vendor' and 'renderer' keys.
    """
    ua_lower = user_agent.lower()

    if 'iphone' in ua_lower or 'ipad' in ua_lower:
        logger.debug("UA detected as Apple. Choosing an Apple GPU.")
        return random.choice(APPLE_GPUS)
    
    # Samsung model numbers (SM-...) are a reliable indicator.
    if 'samsung' in ua_lower or 'sm-' in ua_lower:
        logger.debug("UA detected as Samsung. Choosing an ARM Mali GPU.")
        return random.choice(ARM_GPUS)

    if 'nintendo' in ua_lower:
        logger.debug("UA detected as Nintendo. Choosing an NVIDIA GPU.")
        return random.choice(NVIDIA_GPUS)
    
    if 'android' in ua_lower:
        # This is a fallback for non-Samsung Android devices.
        logger.debug("UA detected as generic Android. Choosing a Qualcomm Adreno GPU.")
        return random.choice(QUALCOMM_GPUS)
        
    # If no specific mobile platform is detected, default to the most common one.
    logger.warning(f"Could not determine specific mobile vendor from UA. Defaulting to Qualcomm.")
    return random.choice(QUALCOMM_GPUS)