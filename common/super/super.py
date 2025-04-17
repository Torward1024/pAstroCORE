from abc import ABC
from typing import Dict, Any, Callable, Type, Optional
from common.utils.logging_setup import logger
from common.super.manipulator import Manipulator
from common.base.baseentity import BaseEntity
from common.base.basecontainer import BaseContainer
from collections import OrderedDict
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
        - Results are returned as dictionaries with keys: status (bool), object (Any), method (str | None),
          result (Any), error (str | None, included only if status=False).
    """
    def __init__(self, manipulator: 'Manipulator' = None, methods: Optional[Dict[Type, Dict[str, Callable]]] = None,
                 cache_size: int = 2048):
        """Initialize a Super instance with an optional Manipulator and method registry.

        Args:
            manipulator (Manipulator, optional): The Manipulator instance to associate with. Defaults to None.
            methods (Optional[Dict[Type, Dict[str, Callable]]]): Custom method registry. Defaults to None (empty dict).
            cache_size (int): Maximum size of the method cache. Defaults to 2048.
        """
        self._manipulator = manipulator
        self._methods = methods or {}
        self._method_cache = OrderedDict()
        self._cache_size = cache_size

    def _build_response(self, obj: Any, status: bool, method: str = None, result: Any = None,
                         error: str = None) -> Dict[str, Any]:
        """Format a standardized response dictionary.

        Args:
            obj (Any): The object associated with the operation.
            status (bool): Whether the operation was successful.
            method (str, optional): Name of the method executed. Defaults to None.
            result (Any, optional): Result of the operation. Defaults to None.
            error (str, optional): Error message if status is False. Defaults to None.

        Returns:
            Dict[str, Any]: Standardized response dictionary.
        """
        response = {
            "status": status,
            "object": obj,
            "method": method,
            "result": result
        }
        if not status and error:
            response["error"] = error
        return response

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

    def _get_nested_object(self, obj: Any, key: Any, getter_method: Callable) -> Any:
        """Retrieve a nested object from a container.

        Args:
            obj (Any): The object to query.
            key (Any): The key or index to access the nested object.
            getter_method (Callable): Method to retrieve the nested object by key.

        Returns:
            Any: The nested object, or None if the key is invalid.
        """
        if isinstance(obj, BaseContainer):
            if not isinstance(key, str):
                logger.error(f"Invalid key {key} for BaseContainer; expected string")
                return None
            nested_obj = obj.get(key)
            if nested_obj is None:
                logger.error(f"Item '{key}' not found in BaseContainer")
            return nested_obj
        if not isinstance(key, int) or not 0 <= key < len(obj):
            logger.error(f"Invalid key {key} for {type(obj).__name__}")
            return None
        return getter_method(key)

    def _do_nested(self, obj: Any, attributes: Dict[str, Any], key: str, getter_method: Callable,
                   nested_handler: Callable) -> Dict[str, Any]:
        """Handle nested operations on an object using an index and a handler.

        Args:
            obj (Any): The object containing nested elements.
            attributes (Dict[str, Any]): Attributes dictionary with an optional key.
            key (str): The key in attributes specifying the index or name.
            getter_method (Callable): Method to retrieve the nested object by key.
            nested_handler (Callable): Method to process the nested object.

        Returns:
            Dict[str, Any]: Dictionary with status, object, method, result, and error (if status=False).
        """
        index = attributes.get(key)
        if index is None:
            logger.debug(f"No {key} provided for nested operation")
            return self._build_response(obj, False, None, None, "Operation not executed")

        try:
            nested_obj = self._get_nested_object(obj, index, getter_method)
            if nested_obj is None:
                return self._build_response(obj, False, None, None, "Operation not executed")

            nested_attrs = {k: v for k, v in attributes.items() if k != key}
            result = nested_handler(nested_obj, nested_attrs)
            method_name = nested_handler.__name__ if hasattr(nested_handler, '__name__') else None
            logger.info(f"Processed nested operation on {type(obj).__name__} with {key}={index}")
            return self._build_response(nested_obj, True, method_name, result)
        except Exception as e:
            logger.error(f"Nested operation failed: {str(e)}")
            return self._build_response(obj, False, None, None, str(e))

    def _validate_and_apply_method(self, obj: Any, method_name: str, method_args: Any,
                                   valid_methods: Dict[str, Callable], extra_args: Dict[str, Any] = None) -> Dict[str, Any]:
        """Validate and apply a method to an object with given arguments.

        Args:
            obj (Any): The object to apply the method to.
            method_name (str): The name of the method to apply.
            method_args (Any): Arguments for the method, expected as a dict, str, list, or None.
            valid_methods (Dict[str, Callable]): Dictionary of valid methods for the object type.
            extra_args (Dict[str, Any], optional): Additional arguments to merge with method_args. Defaults to None.

        Returns:
            Dict[str, Any]: Dictionary with status, object, method, result, and error (if status=False).
        """
        if method_name not in valid_methods:
            logger.error(f"Invalid attribute/method '{method_name}' for '{type(obj).__name__} object'")
            return self._build_response(obj, False, None, None, f"Method '{method_name}' not found")

        method = valid_methods[method_name]
        sig = inspect.signature(method)
        expected_params = set(sig.parameters.keys()) - {"self", "obj"}

        if method_args is not None and not isinstance(method_args, (dict, str, list, type(None))):
            logger.error(f"Arguments for {method_name} must be a dictionary, string, list, or None, got {type(method_args)}")
            return self._build_response(obj, False, method_name, None, f"Invalid argument type: {type(method_args)}")

        if method_args is not None and not isinstance(method_args, (dict, type(None))):
            valid_arg = False
            for param_name, param in sig.parameters.items():
                if param_name in ("self", "obj"):
                    continue
                annotation = param.annotation
                if annotation is inspect.Parameter.empty:
                    if isinstance(method_args, (str, list)):
                        logger.error(f"Invalid argument type for {method_name}: got {type(method_args)}")
                        return self._build_response(obj, False, method_name, None, f"Invalid argument type: {type(method_args)}")
                    valid_arg = True
                    break
                if isinstance(method_args, annotation):
                    valid_arg = True
                    break
            if not valid_arg:
                logger.error(f"Invalid argument type for {method_name}: got {type(method_args)}")
                return self._build_response(obj, False, method_name, None, f"Invalid argument type: {type(method_args)}")

        if isinstance(method_args, dict):
            provided_params = set(method_args.keys())
            if not provided_params.issubset(expected_params):
                logger.error(f"Invalid arguments for {method_name}: expected {expected_params}, got {provided_params}")
                return self._build_response(obj, False, method_name, None, f"Invalid arguments: expected {expected_params}, got {provided_params}")

        try:
            if extra_args:
                method_args = {**(method_args or {}), **extra_args} if isinstance(method_args, dict) else method_args
            if isinstance(method_args, dict):
                result = method(obj, **method_args)
            elif method_args is None:
                result = method(obj)
            else:
                result = method(obj, method_args)

            logger.info(f"Applied {method_name} to {type(obj).__name__}, result={result}")
            return self._build_response(obj, True, method_name, result)
        except Exception as e:
            logger.error(f"Failed to apply {method_name} to {type(obj).__name__}: {str(e)}")
            return self._build_response(obj, False, method_name, None, str(e))

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
        logger.info(f"Registered method '{method_name}' for {obj_type.__name__}")

    def _make_hashable(self, obj: Any) -> Any:
        """Convert an object into a hashable form for caching.

        Args:
            obj (Any): The object to convert.

        Returns:
            Any: A hashable representation of the object.
        """
        if isinstance(obj, dict):
            return tuple(sorted((k, self._make_hashable(v)) for k, v in obj.items()))
        elif isinstance(obj, (list, tuple)):
            return tuple(self._make_hashable(item) for item in obj)
        elif isinstance(obj, BaseEntity | BaseContainer):
            name = getattr(obj, 'name', None)
            if name is None:
                logger.debug(f"Object {obj} has no 'name' attribute, using str(obj) for hashing")
                return str(obj)
            return name
        return obj

    def _update_cache(self, key: tuple, value: Dict[str, Any]) -> None:
        """Update the cache with a new key-value pair, respecting the size limit.

        Args:
            key (tuple): The cache key.
            value (Dict[str, Any]): The result to cache.
        """
        if len(self._method_cache) >= self._cache_size:
            self._method_cache.popitem(last=False)
        self._method_cache[key] = value
        logger.debug(f"Cache updated with key {key}")

    def execute(self, obj: Any, attributes: Dict[str, Any] = None, method: str = None) -> Dict[str, Any]:
        """Execute an operation on an object based on attributes and an optional method.

        Args:
            obj (Any): The object to process.
            attributes (Dict[str, Any], optional): Dictionary of operation attributes. Defaults to None.
            method (str, optional): Explicit method to call, if provided in the request.

        Returns:
            Dict[str, Any]: Dictionary with status, object, method, result, and error (if status=False).
        """
        if attributes is None:
            attributes = {}
        cache_key = (self._operation, type(obj).__name__, method, self._make_hashable(attributes))

        if cache_key in self._method_cache:
            logger.debug(f"Cache hit for {cache_key}")
            return self._method_cache[cache_key]

        try:
            if method:
                method_func = getattr(self, method, None)
                if callable(method_func):
                    result = method_func(obj, attributes)
                    response = self._build_response(obj, True, method, result)
                    self._update_cache(cache_key, response)
                    return response

            method_name = attributes.get("method")
            if not method_name and "attributes" in attributes and isinstance(attributes["attributes"], dict):
                nested_attrs = attributes["attributes"]
                method_name = nested_attrs.get("method")
                object_attributes = nested_attrs
            else:
                object_attributes = {k: v for k, v in attributes.items() if k != 'method'}

            if method_name:
                method = getattr(self, method_name, None)
                if callable(method):
                    result = method(obj, object_attributes)
                    response = self._build_response(obj, True, method_name, result)
                    self._update_cache(cache_key, response)
                    return response

                prefixed_method_name = f"_{self._operation}_{method_name}"
                method = getattr(self, prefixed_method_name, None)
                if callable(method):
                    result = method(obj, object_attributes)
                    response = self._build_response(obj, True, prefixed_method_name, result)
                    self._update_cache(cache_key, response)
                    return response

            obj_type_name = type(obj).__name__.lower()
            auto_method_name = f"_{self._operation}_{obj_type_name}"
            method = getattr(self, auto_method_name, None)
            if callable(method):
                result = method(obj, object_attributes)
                response = self._build_response(obj, True, auto_method_name, result)
                self._update_cache(cache_key, response)
                return response

            if isinstance(obj, BaseContainer):
                base_method_name = f"_{self._operation}_basecontainer"
                method = getattr(self, base_method_name, None)
                if callable(method):
                    result = method(obj, object_attributes)
                    response = self._build_response(obj, True, base_method_name, result)
                    self._update_cache(cache_key, response)
                    return response

            default_method_name = f"_{self._operation}"
            method = getattr(self, default_method_name, None)
            if callable(method):
                result = method(obj, object_attributes)
                response = self._build_response(obj, True, default_method_name, result)
                self._update_cache(cache_key, response)
                return response

            raise ValueError(f"No suitable method found for operation '{self._operation}' and object '{obj_type_name}' in {self.__class__.__name__}")
        except ValueError as e:
            logger.error(f"Execution failed for operation '{self._operation}': {str(e)}")
            response = self._build_response(obj, False, None, None, str(e))
            self._update_cache(cache_key, response)
            return response
        except Exception as e:
            logger.error(f"Unexpected error in execute for '{self._operation}': {str(e)}")
            response = self._build_response(obj, False, None, None, str(e))
            self._update_cache(cache_key, response)
            return response

    def _default_result(self, obj: Any) -> Dict[str, Any]:
        """Provide a default result when an operation cannot be executed.

        Args:
            obj (Any): The object associated with the operation.

        Returns:
            Dict[str, Any]: Dictionary with status, object, method, result, and error.
        """
        return self._build_response(obj, False, None, None, "Operation not executed")

    def _default_nested_result(self, obj: Any) -> Dict[str, Any]:
        """Provide a default result for nested operations.

        Args:
            obj (Any): The object associated with the operation.

        Returns:
            Dict[str, Any]: Dictionary with status, object, method, result, and error.
        """
        return self._build_response(obj, False, None, None, "Operation not executed")

    def __repr__(self) -> str:
        """Return a string representation of the Super instance.

        Returns:
            str: A formatted string with the class name.
        """
        return f"{self.__class__.__name__}()"