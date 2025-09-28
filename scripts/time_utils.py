# scripts/time_utils.py
"""
Handles custom, localized time formatting for Bangladesh.
"""
from datetime import datetime
import pytz

# Define the timezone for Bangladesh
BD_TIMEZONE = pytz.timezone('Asia/Dhaka')

def get_current_bd_datetime():
    """Returns the current datetime object aware of the BD timezone."""
    return datetime.now(BD_TIMEZONE)

def format_bd_time(dt: datetime) -> str:
    """
    Formats a datetime object into the custom Bangladeshi 12-hour format.
    Example: Shokal 08:11:30
    """
    hour = dt.hour
    
    if 4 <= hour <= 11:
        period = "Shokal"
    elif 12 <= hour <= 15:
        period = "Dupur"
    elif 16 <= hour <= 17:
        period = "Bikal"
    elif 18 <= hour <= 19:
        period = "Shondha"
    else: # Covers 20:00-23:59 and 00:00-03:59
        period = "Raat"
        
    # Format to 12-hour clock
    formatted_time = dt.strftime('%I:%M:%S')
    
    return f"{period} {formatted_time}"

def format_bd_date(dt: datetime) -> str:
    """Formats a datetime object into YYYY-MM-DD."""
    return dt.strftime('%Y-%m-%d')

def calculate_runtime(start_dt: datetime, end_dt: datetime) -> str:
    """Calculates the duration and returns a human-readable string."""
    duration = end_dt - start_dt
    total_seconds = int(duration.total_seconds())
    
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    
    if minutes > 0:
        return f"{minutes} minute(s) {seconds} second(s)"
    else:
        return f"{seconds} second(s)"