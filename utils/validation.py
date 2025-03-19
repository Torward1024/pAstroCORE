# utils/validation.py
from utils.logging_setup import logger

def check_type(value, expected_type, name: str) -> None:
    """Check if value matches the expected type or is None (for optional parameters).

    Args:
        value: Value to check.
        expected_type: Expected type or tuple of types.
        name (str): Name of the parameter for error message.
    """
    if value is None:  # Разрешаем None для необязательных параметров
        return
    if not isinstance(value, expected_type):
        logger.error(f"{name} must be of type {expected_type}, got {type(value)}")
        raise TypeError(f"{name} must be of type {expected_type}, got {type(value)}")

def check_range(value: float, min_val: float, max_val: float, name: str) -> None:
    """Check if value is within the specified range."""
    if not isinstance(value, (int, float)):
        logger.error(f"{name} must be a number, got {type(value)}")
        raise TypeError(f"{name} must be a number, got {type(value)}")
    if not min_val <= value <= max_val:
        logger.error(f"{name} must be between {min_val} and {max_val}, got {value}")
        raise ValueError(f"{name} must be between {min_val} and {max_val}, got {value}")

def check_positive(value: float, name: str) -> None:
    """Check if value is positive."""
    if not isinstance(value, (int, float)):
        logger.error(f"{name} must be a number, got {type(value)}")
        raise TypeError(f"{name} must be a number, got {type(value)}")
    if value <= 0:
        logger.error(f"{name} must be positive, got {value}")
        raise ValueError(f"{name} must be positive, got {value}")

def check_list_type(lst: list, expected_type, name: str) -> None:
    """Check if all elements in the list match the expected type."""
    if not isinstance(lst, (list, tuple)):
        logger.error(f"{name} must be a list or tuple, got {type(lst)}")
        raise TypeError(f"{name} must be a list or tuple, got {type(lst)}")
    for item in lst:
        if not isinstance(item, expected_type):
            logger.error(f"All items in {name} must be of type {expected_type}, got {type(item)}")
            raise TypeError(f"All items in {name} must be of type {expected_type}, got {type(item)}")

def check_non_negative(value: float, name: str) -> None:
    """Check if value is non-negative."""
    if not isinstance(value, (int, float)):
        logger.error(f"{name} must be a number, got {type(value)}")
        raise TypeError(f"{name} must be a number, got {type(value)}")
    if value < 0:
        logger.error(f"{name} must be non-negative, got {value}")
        raise ValueError(f"{name} must be non-negative, got {value}")

def check_non_empty_string(value: str, name: str) -> None:
    """Check if value is a non-empty string."""
    if not isinstance(value, str):
        logger.error(f"{name} must be a string, got {type(value)}")
        raise TypeError(f"{name} must be a string, got {type(value)}")
    if not value.strip():
        logger.error(f"{name} must not be empty")
        raise ValueError(f"{name} must not be empty")

def check_non_zero(value: float, name: str) -> None:
    """Check if value is non-zero."""
    if not isinstance(value, (int, float)):
        logger.error(f"{name} must be a number, got {type(value)}")
        raise TypeError(f"{name} must be a number, got {type(value)}")
    if value == 0:
        logger.error(f"{name} must be non-zero, got {value}")
        raise ValueError(f"{name} must be non-zero, got {value}")