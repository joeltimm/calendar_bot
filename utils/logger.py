import logging
import os
from logging.handlers import RotatingFileHandler

# Set up log directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Shared log file path
LOG_PATH = os.path.join(LOG_DIR, 'calendar_bot.log')

# Create logger
logger = logging.getLogger("calendar_bot")
logger.setLevel(logging.INFO)

# Prevent duplicate handlers if module is imported multiple times
if not logger.hasHandlers():
    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5_000_000, backupCount=3)
    stream_handler = logging.StreamHandler()

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
