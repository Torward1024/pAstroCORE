# utils/validation.py
from common.utils.logging_setup import logger

def check_type(value, expected_type, name: str) -> None:
    """Check if a value matches the expected type or is None for optional parameters.

    Args:
        value: The value to check.
        expected_type: The expected type or tuple of types (e.g., str, (int, float)).
        name (str): Name of the parameter for use in error messages.

    Raises:
        TypeError: If value is neither None nor of the expected type.

    Notes:
        - Allows None as a valid value for optional parameters.
        - Logs an error message via `logger` before raising an exception.

    Examples:
        >>> check_type("test", str, "my_string")
        >>> check_type(None, str, "optional_string")  # No exception
        >>> check_type(123, str, "my_string")
        Traceback (most recent call last):
        ...
        TypeError: my_string must be of type <class 'str'>, got <class 'int'>
    """
    if value is None:
        return
    if not isinstance(value, expected_type):
        logger.error(f"{name} must be of type {expected_type}, got {type(value)}")
        raise TypeError(f"{name} must be of type {expected_type}, got {type(value)}")

def check_range(value: float, min_val: float, max_val: float, name: str) -> None:
    """Check if a numeric value is within a specified range.

    Args:
        value (float): The value to check.
        min_val (float): Minimum allowed value (inclusive).
        max_val (float): Maximum allowed value (inclusive).
        name (str): Name of the parameter for error messages.

    Raises:
        TypeError: If value is not a number (int or float).
        ValueError: If value is outside the range [min_val, max_val].

    Notes:
        - Logs an error message via `logger` before raising an exception.

    Examples:
        >>> check_range(5.0, 0.0, 10.0, "my_value")
        >>> check_range(-1, 0.0, 10.0, "my_value")
        Traceback (most recent call last):
        ...
        ValueError: my_value must be between 0.0 and 10.0, got -1
    """
    if not isinstance(value, (int, float)):
        logger.error(f"{name} must be a number, got {type(value)}")
        raise TypeError(f"{name} must be a number, got {type(value)}")
    if not min_val <= value <= max_val:
        logger.error(f"{name} must be between {min_val} and {max_val}, got {value}")
        raise ValueError(f"{name} must be between {min_val} and {max_val}, got {value}")

def check_positive(value: float, name: str) -> None:
    """Check if a numeric value is positive.

    Args:
        value (float): The value to check.
        name (str): Name of the parameter for error messages.

    Raises:
        TypeError: If value is not a number (int or float).
        ValueError: If value is not positive (less than or equal to 0).

    Notes:
        - Logs an error message via `logger` before raising an exception.

    Examples:
        >>> check_positive(1.5, "my_value")
        >>> check_positive(0, "my_value")
        Traceback (most recent call last):
        ...
        ValueError: my_value must be positive, got 0
    """
    if not isinstance(value, (int, float)):
        logger.error(f"{name} must be a number, got {type(value)}")
        raise TypeError(f"{name} must be a number, got {type(value)}")
    if value <= 0:
        logger.error(f"{name} must be positive, got {value}")
        raise ValueError(f"{name} must be positive, got {value}")

def check_list_type(lst: list, expected_type, name: str) -> None:
    """Check if all elements in a list or tuple match the expected type.

    Args:
        lst (list): The list or tuple to check.
        expected_type: The expected type for all elements (e.g., str, int).
        name (str): Name of the parameter for error messages.

    Raises:
        TypeError: If lst is not a list/tuple or any element does not match expected_type.

    Notes:
        - Logs an error message via `logger` before raising an exception.

    Examples:
        >>> check_list_type(["a", "b"], str, "my_list")
        >>> check_list_type([1, "b"], str, "my_list")
        Traceback (most recent call last):
        ...
        TypeError: All items in my_list must be of type <class 'str'>, got <class 'int'>
    """
    if not isinstance(lst, (list, tuple)):
        logger.error(f"{name} must be a list or tuple, got {type(lst)}")
        raise TypeError(f"{name} must be a list or tuple, got {type(lst)}")
    for item in lst:
        if not isinstance(item, expected_type):
            logger.error(f"All items in {name} must be of type {expected_type}, got {type(item)}")
            raise TypeError(f"All items in {name} must be of type {expected_type}, got {type(item)}")

def check_non_negative(value: float, name: str) -> None:
    """Check if a numeric value is non-negative.

    Args:
        value (float): The value to check.
        name (str): Name of the parameter for error messages.

    Raises:
        TypeError: If value is not a number (int or float).
        ValueError: If value is negative (less than 0).

    Notes:
        - Logs an error message via `logger` before raising an exception.

    Examples:
        >>> check_non_negative(0.0, "my_value")
        >>> check_non_negative(-1.0, "my_value")
        Traceback (most recent call last):
        ...
        ValueError: my_value must be non-negative, got -1.0
    """
    if not isinstance(value, (int, float)):
        logger.error(f"{name} must be a number, got {type(value)}")
        raise TypeError(f"{name} must be a number, got {type(value)}")
    if value < 0:
        logger.error(f"{name} must be non-negative, got {value}")
        raise ValueError(f"{name} must be non-negative, got {value}")

def check_non_empty_string(value: str, name: str) -> None:
    """Check if a value is a non-empty string.

    Args:
        value (str): The value to check.
        name (str): Name of the parameter for error messages.

    Raises:
        TypeError: If value is not a string.
        ValueError: If value is empty or contains only whitespace.

    Notes:
        - Logs an error message via `logger` before raising an exception.

    Examples:
        >>> check_non_empty_string("test", "my_string")
        >>> check_non_empty_string("", "my_string")
        Traceback (most recent call last):
        ...
        ValueError: my_string must not be empty
    """
    if not isinstance(value, str):
        logger.error(f"{name} must be a string, got {type(value)}")
        raise TypeError(f"{name} must be a string, got {type(value)}")
    if not value.strip():
        logger.error(f"{name} must not be empty")
        raise ValueError(f"{name} must not be empty")

def check_non_zero(value: float, name: str) -> None:
    """Check if a numeric value is non-zero.

    Args:
        value (float): The value to check.
        name (str): Name of the parameter for error messages.

    Raises:
        TypeError: If value is not a number (int or float).
        ValueError: If value is zero.

    Notes:
        - Logs an error message via `logger` before raising an exception.

    Examples:
        >>> check_non_zero(1.0, "my_value")
        >>> check_non_zero(0.0, "my_value")
        Traceback (most recent call last):
        ...
        ValueError: my_value must be non-zero, got 0.0
    """
    if not isinstance(value, (int, float)):
        logger.error(f"{name} must be a number, got {type(value)}")
        raise TypeError(f"{name} must be a number, got {type(value)}")
    if value == 0:
        logger.error(f"{name} must be non-zero, got {value}")
        raise ValueError(f"{name} must be non-zero, got {value}")