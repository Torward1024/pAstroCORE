# utils/logging_setup.py
import logging

def setup_logging(log_file: str = "output.log", log_level: int = logging.INFO) -> logging.Logger:
    """Set up and configure logging for the system.

    Creates a logger with both file and console handlers, using a consistent format for log messages.
    Allows specifying the logging level for flexible logging configuration.

    Args:
        log_file (str): Path to the log file. Defaults to "output.log".
        log_level (int): Logging level (e.g., logging.DEBUG, logging.INFO). Defaults to logging.INFO.

    Returns:
        logging.Logger: The configured logger instance.

    Notes:
        - Log format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s".
        - Handlers are added only if the logger has no existing handlers to avoid duplication.
        - Valid log levels are defined in the logging module (e.g., logging.DEBUG, logging.INFO, logging.WARNING).

    Examples:
        >>> logger = setup_logging("my_log.log", logging.DEBUG)
        >>> logger.debug("Debug message")
        # Output to both my_log.log and console: <timestamp> - root - DEBUG - Debug message
    """
    logger = logging.getLogger("")
    logger.setLevel(log_level)

    # Avoid duplicate handlers if already set up
    if not logger.handlers:
        # File handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(log_level)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(log_level)

        # Formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        # Add handlers
        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger

def update_logging_level(log_level: int) -> None:
    """Update the logging level for the singleton logger and its handlers.

    Args:
        log_level (int): New logging level (e.g., logging.DEBUG, logging.INFO).

    Notes:
        - Updates the level of the singleton logger and all its handlers.
        - If the logger is not initialized, it will be created with default settings and the specified level.
    """
    global logger
    if logger is None:
        logger = setup_logging(log_level=log_level)
    else:
        logger.setLevel(log_level)
        for handler in logger.handlers:
            handler.setLevel(log_level)

# Singleton logger instance with default INFO level
logger = setup_logging()