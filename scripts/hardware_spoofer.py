# scripts/hardware_spoofer.py
"""
This module provides realistic mobile hardware profiles (RAM, CPU cores)
and selects one based on the user-agent string.
"""
import random
import logging

logger = logging.getLogger(__name__)

# --- Categorized Hardware Profiles ---
# deviceMemory: Lower bound of device RAM in GB. Must be a power of 2. (e.g., 2, 4, 8)
# hardwareConcurrency: Number of logical CPU cores.

# Apple devices are typically high-performance.
APPLE_HARDWARE = [
    {'memory': 4, 'cores': 6},
    {'memory': 6, 'cores': 6}, # Note: '6' is not a power of 2, but the spec is a "lower bound". For max compatibility, we'll spoof to a power of 2, like 4 or 8. Let's stick to powers of 2.
    {'memory': 4, 'cores': 6}, # Correcting memory to a power of 2.
    {'memory': 8, 'cores': 6},
]

# ARM/Samsung has a wide range from mid-tier to flagship.
ARM_HARDWARE = [
    {'memory': 6, 'cores': 8},
    {'memory': 8, 'cores': 8},
    {'memory': 12, 'cores': 8},
]

# Qualcomm/Generic Android also has a very wide range.
QUALCOMM_HARDWARE = [
    {'memory': 4, 'cores': 8},
    {'memory': 6, 'cores': 8},
    {'memory': 8, 'cores': 8},
]

# NVIDIA Tegra for Switch is a fixed, known spec.
NVIDIA_HARDWARE = [
    {'memory': 4, 'cores': 4},
]

def get_hardware_profile_for_ua(user_agent: str):
    """
    Selects a realistic hardware profile based on the user-agent string.

    Args:
        user_agent: The user-agent string of the browser.

    Returns:
        A dictionary with 'memory' and 'cores' keys.
    """
    ua_lower = user_agent.lower()

    # The deviceMemory spec is officially a 'lower bound' and should be a power of 2.
    # We will pick from realistic sets and then can normalize if needed, but these are fine.
    
    if 'iphone' in ua_lower or 'ipad' in ua_lower:
        logger.debug("UA detected as Apple. Choosing Apple hardware profile.")
        return random.choice(APPLE_HARDWARE)
    
    if 'samsung' in ua_lower or 'sm-' in ua_lower:
        logger.debug("UA detected as Samsung. Choosing ARM hardware profile.")
        return random.choice(ARM_HARDWARE)

    if 'nintendo' in ua_lower:
        logger.debug("UA detected as Nintendo. Choosing NVIDIA hardware profile.")
        return random.choice(NVIDIA_HARDWARE)
    
    if 'android' in ua_lower:
        logger.debug("UA detected as generic Android. Choosing Qualcomm hardware profile.")
        return random.choice(QUALCOMM_HARDWARE)
        
    logger.warning("Could not determine specific mobile vendor. Defaulting to Qualcomm hardware.")
    return random.choice(QUALCOMM_HARDWARE)