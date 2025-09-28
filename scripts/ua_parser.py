# scripts/ua_parser.py
"""
This module provides utilities for parsing user-agent strings
to extract details needed for comprehensive browser spoofing.
"""

def get_spoof_details(user_agent: str) -> dict:
    """
    Parses a user-agent string and returns a dictionary with details
    for JavaScript navigator object spoofing.

    Args:
        user_agent: The user-agent string.

    Returns:
        A dictionary containing spoofed values for 'platform', 'appVersion', and 'vendor'.
    """
    details = {}

    # --- Determine Platform and Vendor ---
    # This is a simplified logic; more complex UAs might need more rules.
    if 'iPhone' in user_agent or 'iPad' in user_agent:
        # For iOS devices, the platform is typically 'iPhone' or 'iPad'. 'iPhone' is a safe bet.
        details['platform'] = 'iPhone'
        details['vendor'] = 'Apple Computer, Inc.'
    elif 'Android' in user_agent:
        # For Android, the platform is 'Linux armv8l' or similar. This is a common value.
        details['platform'] = 'Linux armv8l'
        details['vendor'] = 'Google Inc.'
    else:
        # Fallback for unknown or desktop user agents
        details['platform'] = ''
        details['vendor'] = 'Google Inc.'

    # --- Determine appVersion ---
    # navigator.appVersion is often the part of the UA string after "Mozilla/5.0 ".
    try:
        details['appVersion'] = user_agent.split('Mozilla/5.0 ')[1]
    except IndexError:
        # If the format is unexpected, use the full UA as a safe fallback
        details['appVersion'] = user_agent

    return details