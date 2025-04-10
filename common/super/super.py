from abc import ABC
from typing import Dict, Any, Callable, Type, Optional, Union
from common.utils.logging_setup import logger
from common.super.manipulator import Manipulator
import inspect

class Super(ABC):
    """Abstract super-class providing common functionality for operation handlers.

    Designed to work with a Manipulator, this class defines a framework for executing operations on objects
    based on attributes. Subclasses implement specific operations (e.g., configuration, inspection, calculation, etc.)
    by defining methods with naming conventions like `_<operation>_<type>` or `_<operation>`.

    Attributes:
        _manipulator (Manipulator): The associated Manipulator instance for method lookup.
        _methods (Dict[Type, Dict[str, Callable]]): Custom method registry for specific object types.
        _operation (str): The operation name, set by Manipulator during registration.

    Notes:
        - Method resolution order: explicit method, prefixed method (`_<operation>_<method>`), type-specific method (`_<operation>_<type>`), default method (`_<operation>`).
        - Logging is integrated via `common.utils.logging_setup.logger`.

    Examples:
        >>> class Configurator(Super):
        ...     def _configure_list(self, obj, attrs):
        ...         obj.append(attrs.get("value"))
        ...         return True
        >>> manip = Manipulator()
        >>> config = Configurator(manip)
        >>> manip.register_operation("configure", config)
        >>> manip.process_request({"operation": "configure", "obj": [], "attributes": {"value": 1}})
        True
    """
    def __init__(self, manipulator: 'Manipulator' = None, methods: Optional[Dict[Type, Dict[str, Callable]]] = None):
        """Initialize a Super instance with an optional Manipulator and method registry.

        Args:
            manipulator (Manipulator, optional): The Manipulator instance to associate with. Defaults to None.
            methods (Optional[Dict[Type, Dict[str, Callable]]]): Custom method registry. Defaults to None (empty dict).
        """
        self._manipulator = manipulator
        self._methods = methods or {}
        self._method_cache = {}

    def _get_methods(self, obj_type: Type) -> Dict[str, Callable]:
        """Retrieve methods available for a given object type.

        Args:
            obj_type (Type): The type of object to query methods for.

        Returns:
            Dict[str, Callable]: Dictionary of method names mapped to their callable implementations.

        Raises:
            ValueError: If no methods are available for the type in either _methods or the Manipulator.
        """
        if obj_type in self._methods:
            return self._methods[obj_type]
        if self._manipulator:
            return self._manipulator.get_methods_for_type(obj_type)
        raise ValueError(f"No methods available for {obj_type.__name__}")

    def _do_nested(self, obj: Any, attributes: Dict[str, Any], index_key: str, getter_method: Callable,
                   nested_handler: Callable) -> Any:
        """Handle nested operations on an object using an index and a handler.

        Args:
            obj (Any): The object containing nested elements.
            attributes (Dict[str, Any]): Attributes dictionary with an optional index_key.
            index_key (str): The key in attributes specifying the index.
            getter_method (Callable): Method to retrieve the nested object by index.
            nested_handler (Callable): Method to process the nested object.

        Returns:
            Any: The result of the nested operation, or a default result if index is invalid or missing.
        """
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
        """Validate and apply a method to an object with given arguments.

        Args:
            obj (Any): The object to apply the method to.
            method_name (str): The name of the method to apply.
            method_args (Any): Arguments for the method, expected as a dict or None.
            valid_methods (Dict[str, Callable]): Dictionary of valid methods for the object type.
            extra_args (Dict[str, Any], optional): Additional arguments to merge with method_args. Defaults to None.

        Returns:
            Optional[Any]: The result of the method application (True on success), or None if validation or execution fails.
        """
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

        if method_args and not provided_params.issubset(expected_params):
            logger.error(f"Invalid arguments for {method_name}: expected {expected_params}, got {provided_params}")
            return None

        try:
            if extra_args:
                method_args = {**(method_args or {}), **extra_args}
            result = method(obj, **method_args) if method_args else method(obj)
            logger.info(f"Applied {method_name} to {type(obj).__name__}, result={result}")
            return True
        except Exception as e:
            logger.error(f"Failed to apply {method_name} to {type(obj).__name__}: {str(e)}")
            return None

    def register_method(self, obj_type: Type, method_name: str, method: Callable) -> None:
        """Register a custom method for a specific object type.

        Args:
            obj_type (Type): The type of object the method applies to.
            method_name (str): The name of the method.
            method (Callable): The callable method to register.
        """
        if obj_type not in self._methods:
            self._methods[obj_type] = {}
        self._methods[obj_type][method_name] = method
        self._method_cache.clear()

    def execute(self, obj: Any, attributes: Dict[str, Any] = None, method: str = None) -> Union[Dict[str, Any], bool]:
        """Execute an operation on an object based on attributes and an optional method.

        Args:
            obj (Any): The object to process.
            attributes (Dict[str, Any], optional): Dictionary of operation attributes. Defaults to None.
            method (str, optional): Explicit method to call, if provided in the request.

        Returns:
            Union[Dict[str, Any], bool]: The result of the operation.

        Raises:
            ValueError: If no suitable method is found.
        """
        if attributes is None:
            attributes = {}
        cache_key = (self._operation, type(obj), method, tuple(sorted(attributes.items())) if attributes else None)
        if cache_key in self._method_cache:
            return self._method_cache[cache_key]
        try:

            if method:
                method_func = getattr(self, method, None)
                if callable(method_func):
                    result = method_func(obj, attributes)
                    self._method_cache[cache_key] = result
                    return result
            
            method_name = attributes.get("method")
            if not method_name and "attributes" in attributes and isinstance(attributes["attributes"], dict):
                nested_attrs = attributes["attributes"]
                method_name = nested_attrs.get("method")
                object_attributes = nested_attrs.get("attributes", {})
            else:
                object_attributes = {k: v for k, v in attributes.items() if k != 'method'}
            
            if method_name:
                method = getattr(self, method_name, None)
                if callable(method):
                    result = method(obj, object_attributes)
                    self._method_cache[cache_key] = result
                    return result
                
                prefixed_method_name = f"_{self._operation}_{method_name}"
                method = getattr(self, prefixed_method_name, None)
                if callable(method):
                    result = method(obj, object_attributes)
                    self._method_cache[cache_key] = result
                    return result

            obj_type = type(obj).__name__.lower()
            auto_method_name = f"_{self._operation}_{obj_type}"
            method = getattr(self, auto_method_name, None)
            if callable(method):
                result = method(obj, object_attributes)
                self._method_cache[cache_key] = result
                return result

            default_method_name = f"_{self._operation}"
            method = getattr(self, default_method_name, None)
            if callable(method):
                result = method(obj, object_attributes)
                self._method_cache[cache_key] = result
                return result

            raise ValueError(f"No suitable method found for operation '{self._operation}' and object '{obj_type}' in {self.__class__.__name__}")
        except ValueError as e:
            logger.error(f"Execution failed for operation '{self._operation}': {str(e)}")
            return self._default_result()
        except Exception as e:
            logger.error(f"Unexpected error in execute for '{self._operation}': {str(e)}")
            return self._default_result()

    def _default_result(self) -> Union[Dict[str, Any], bool]:
        """Provide a default result when an operation cannot be executed.

        Returns:
            Union[Dict[str, Any], bool]: An empty dictionary as the default result.
        """
        return {}

    def _default_nested_result(self) -> Union[Dict[str, Any], bool]:
        """Provide a default result for nested operations.

        Returns:
            Union[Dict[str, Any], bool]: An empty dictionary as the default result.
        """
        return {}

    def __repr__(self) -> str:
        """Return a string representation of the Super instance.

        Returns:
            str: A formatted string with the class name.
        """
        return f"{self.__class__.__name__}()"