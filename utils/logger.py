# utils/logger.py
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

def setup_logger():
    """
    Configure a global logger for the supermarket system.

    Features:
    - Daily rotating log files (one file per day)
    - Console + file output
    - Unified log format with timestamp and level
    - Creates directories automatically
    """

    # Create log directory if not exists
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Log file base name
    log_file = log_dir / "supermarket.log"

    # Create logger (singleton pattern)
    logger = logging.getLogger("supermarket")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if setup_logger() is called multiple times
    if logger.handlers:
        return logger

    # Formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    # Console handler 
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("Logger initialized (daily rotation enabled)")
    return logger