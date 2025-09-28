import logging
import os
import pytz
from datetime import datetime

# Define the timezone for Bangladesh
BD_TIMEZONE = pytz.timezone('Asia/Dhaka')

class TimezoneFormatter(logging.Formatter):
    """Custom formatter to add timezone-aware timestamps."""
    
    def converter(self, timestamp):
        dt = datetime.fromtimestamp(timestamp)
        return BD_TIMEZONE.localize(dt)

    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created)
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            s = dt.strftime("%Y-%m-%d %H:%M:%S %Z")
        return s

def setup_logging(project_root):
    """
    Configures the logging system to output to console and separate files.
    """
    # Define the log directory path
    log_dir = os.path.join(project_root, 'logs')
    os.makedirs(log_dir, exist_ok=True) # Ensure the logs directory exists

    # Define paths for log files
    main_log_file = os.path.join(log_dir, 'main.log')
    error_log_file = os.path.join(log_dir, 'error.log')

    # Create our custom formatter
    log_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    formatter = TimezoneFormatter(log_format)

    # --- Configure the root logger ---
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO) # Set the lowest level to capture

    # --- Main log handler (main.log) ---
    # Captures everything from INFO level and up
    main_handler = logging.FileHandler(main_log_file, mode='a', encoding='utf-8')
    main_handler.setLevel(logging.INFO)
    main_handler.setFormatter(formatter)
    
    # --- Error log handler (error.log) ---
    # Captures only ERROR and CRITICAL levels
    error_handler = logging.FileHandler(error_log_file, mode='a', encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # --- Console handler ---
    # Shows INFO and above on the screen
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Add handlers to the root logger
    # Avoid adding handlers if they already exist (prevents duplicate logs)
    if not root_logger.handlers:
        root_logger.addHandler(main_handler)
        root_logger.addHandler(error_handler)
        root_logger.addHandler(console_handler)