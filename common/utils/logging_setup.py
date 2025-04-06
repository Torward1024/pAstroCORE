# utils/logging_setup.py
import logging
import os

def setup_logging(log_file: str = "output.log"):
    """Set up and configure logging for the system.

    Creates a logger with both file and console handlers, using a consistent format for log messages.

    Args:
        log_file (str): Path to the log file. Defaults to "output.log".

    Returns:
        logging.Logger: The configured logger instance.

    Notes:
        - Logger level is set to INFO.
        - Log format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s".
        - Handlers are added only if the logger has no existing handlers to avoid duplication.

    Examples:
        >>> logger = setup_logging("my_log.log")
        >>> logger.info("Test message")
        # Output to both my_log.log and console: <timestamp> - INFO - Test message
    """
    logger = logging.getLogger("")
    logger.setLevel(logging.INFO)

    # avoid duplicate handlers if already setup
    if not logger.handlers:
        # file handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.INFO)

        # console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        # add handlers
        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger

# singleton logger instance
logger = setup_logging()