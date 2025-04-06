from abc import ABC
from typing import Dict, Any, Callable, Type, Optional, Union
from common.utils.logging_setup import logger
from common.super.manipulator import Manipulator
import inspect

class Super(ABC):
    """Abstract base super-class providing common functionality for configurators, inspectors, calculators, etc."""
    def __init__(self, manipulator: 'Manipulator' = None, methods: Optional[Dict[Type, Dict[str, Callable]]] = None):
        self._manipulator = manipulator
        self._methods = methods or {}

    def _get_methods(self, obj_type: Type) -> Dict[str, Callable]:
        if obj_type in self._methods:
            return self._methods[obj_type]
        if self._manipulator:
            return self._manipulator.get_methods_for_type(obj_type)
        raise ValueError(f"No methods available for {obj_type.__name__}")

    def _do_nested(self, obj: Any, attributes: Dict[str, Any], index_key: str, getter_method: Callable,
                   nested_handler: Callable) -> Any:
        index = attributes.get(index_key)
        if index is not None:
            if not isinstance(index, int) or not 0 <= index < len(obj):
                logger.error(f"Invalid {index_key} {index} for {type(obj).__name__}")
                return self._default_nested_result()
            nested_obj = getter_method(index)
            nested_attrs = {k: v for k, v in attributes.items() if k != index_key}
            return nested_handler(nested_obj, nested_attrs)
        return self._default_nested_result()

    def _validate_and_apply_method(self, obj: Any, method_name: str, method_args: Any,
                               valid_methods: Dict[str, Callable], extra_args: Dict[str, Any] = None) -> Optional[Any]:
        if method_name not in valid_methods:
            logger.error(f"Invalid method {method_name} for {type(obj).__name__} object")
            return None
        if method_args is not None and not isinstance(method_args, dict):
            logger.error(f"Arguments for {method_name} must be a dictionary or None, got {type(method_args)}")
            return None
        
        method = valid_methods[method_name]
        sig = inspect.signature(method)
        expected_params = set(sig.parameters.keys()) - {"self"}
        provided_params = set(method_args.keys()) if method_args else set()

        logger.debug(f"Validating {method_name}: expected {expected_params}, provided {provided_params}")
        if method_args and not provided_params.issubset(expected_params):
            logger.error(f"Invalid arguments for {method_name}: expected {expected_params}, got {provided_params}")
            return None

        try:
            if extra_args:
                method_args = {**(method_args or {}), **extra_args}
            logger.debug(f"Applying {method_name} with args: {method_args}")
            result = method(obj, **method_args) if method_args else method(obj)
            logger.info(f"Applied {method_name} to {type(obj).__name__}, result={result}")
            return True  # Успех, даже если результат None
        except Exception as e:
            logger.error(f"Failed to apply {method_name} to {type(obj).__name__}: {str(e)}")
            return None

    def register_method(self, obj_type: Type, method_name: str, method: Callable) -> None:
        if obj_type not in self._methods:
            self._methods[obj_type] = {}
        self._methods[obj_type][method_name] = method
        logger.debug(f"Registered method '{method_name}' for {obj_type.__name__}")

    def execute(self, obj: Any, attributes: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute an operation on the object using attributes.

        Args:
            obj: The object to process.
            attributes: Dictionary with operation attributes (user-defined).

        Returns:
            Union[Dict[str, Any], bool]: Result of the operation, depending on the subclass.

        Raises:
            ValueError: If object is None or no method is found.
        """
        if attributes is None:
            attributes = {}
        
        logger.debug(f"Executing for operation '{self._operation}', obj_type='{type(obj).__name__}'")
        method_name = attributes.get("method")
        
        if method_name:
            method = getattr(self, method_name, None)
            logger.debug(f"Checking explicit method '{method_name}': {method}")
            if callable(method):
                return method(obj, attributes)
        
        if method_name:
            prefixed_method_name = f"_{self._operation}_{method_name}"
            method = getattr(self, prefixed_method_name, None)
            logger.debug(f"Checking prefixed method '{prefixed_method_name}': {method}")
            if callable(method):
                return method(obj, attributes)

        obj_type = type(obj).__name__.lower()
        auto_method_name = f"_{self._operation}_{obj_type}"
        method = getattr(self, auto_method_name, None)
        logger.debug(f"Checking auto method '{auto_method_name}': {method}")
        if callable(method):
            return method(obj, attributes)

        default_method_name = f"_{self._operation}"
        method = getattr(self, default_method_name, None)
        logger.debug(f"Checking default method '{default_method_name}': {method}")
        if callable(method):
            return method(obj, attributes)

        raise ValueError(f"No suitable method found for operation '{self._operation}' and object '{obj_type}' in {self.__class__.__name__}")

    def _default_result(self) -> Union[Dict[str, Any], bool]:
        """Return a default result when execution fails."""
        return {}

    def _default_nested_result(self) -> Union[Dict[str, Any], bool]:
        """Return a default result for nested operations."""
        return {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"