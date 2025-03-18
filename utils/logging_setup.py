# utils/logging_setup.py
import logging
import os

def setup_logging(log_file: str = "pvcore.log"):
    """Setup logging configuration for pvCORE."""
    logger = logging.getLogger("pvCORE")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if already setup
    if not logger.handlers:
        # File handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.INFO)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        # Add handlers
        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger

# Singleton logger instance
logger = setup_logging()