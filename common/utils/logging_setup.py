# utils/logging_setup.py
import logging

def setup_logging(log_file: str = "output.log", log_level: int = logging.INFO, clear_log: bool = False) -> logging.Logger:
    """Set up and configure logging for the system.

    Creates a logger with both file and console handlers, using a consistent format for log messages.
    Allows specifying the logging level and whether to clear the log file on start.

    Args:
        log_file (str): Path to the log file. Defaults to "output.log".
        log_level (int): Logging level (e.g., logging.DEBUG, logging.INFO). Defaults to logging.INFO.
        clear_log (bool): If True, clears the log file before adding new logs. Defaults to False.

    Returns:
        logging.Logger: The configured logger instance.

    Notes:
        - Log format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s".
        - Handlers are added only if the logger has no existing handlers to avoid duplication.
        - If clear_log is True, the log file is truncated before adding new logs.
    """
    logger = logging.getLogger("")
    logger.setLevel(log_level)

    if not logger.handlers:
        mode = 'w' if clear_log else 'a'
        fh = logging.FileHandler(log_file, mode=mode)
        fh.setLevel(log_level)

        ch = logging.StreamHandler()
        ch.setLevel(log_level)

        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

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

def update_logging_clear(log_file: str, clear_log: bool) -> None:
    """Update the logging configuration to clear the log file if specified.

    Args:
        log_file (str): Path to the log file.
        clear_log (bool): If True, reconfigures the file handler to clear the log file.
    """
    global logger
    if logger is None:
        logger = setup_logging(log_file=log_file, clear_log=clear_log)
        return

    if clear_log:
        for handler in logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                logger.removeHandler(handler)
                handler.close()
    
        fh = logging.FileHandler(log_file, mode='w')
        fh.setLevel(logger.level)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        logger.debug("Log file cleared due to clear_log=True")

logger = setup_logging()