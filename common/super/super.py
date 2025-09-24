from abc import ABC
from typing import Dict, Any, Callable, Type, Optional, Union
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
        - Results are returned as dictionaries with keys: status (bool), object (str), method (str | None),
          result (Any), error (str | None, included only if status=False).
    """

    OPERATION: Optional[str] = None # Default operation name for auto-registration

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
            Dict[str, Any]: Standardized response dictionary with object name in 'object' key.
        """
        obj_name = getattr(obj, 'name', None)
        if obj_name is None:
            obj_name = obj
        
        response = {
            "status": status,
            "object": obj_name,
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
        try:
            nested_obj = getter_method(key)
            if nested_obj is None:
                logger.error(f"Item '{key}' not found in {type(obj).__name__}")
                return None
            return nested_obj
        except Exception as e:
            logger.error(f"Invalid key {key} for {type(obj).__name__}: {str(e)}")
            return None

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
                return self._build_response(obj, False, None, None, f"Name '{index}' not found in {type(obj).__name__}")

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
        """Validate and apply a method to an object with given arguments."""
        if method_name not in valid_methods:
            logger.error(f"Invalid method '{method_name}' for '{type(obj).__name__}'")
            return self._build_response(obj, False, method_name, None, f"Method '{method_name}' not found")

        method = valid_methods[method_name]
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        expected_params = [p for p in params if p != 'self']

        try:
            final_args = {}
            if 'obj' in expected_params:
                final_args['obj'] = obj
            else:
                pass
            required_params = [
                p for p in expected_params
                if sig.parameters[p].default == inspect.Parameter.empty
                and sig.parameters[p].kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            ]

            if not expected_params:
                logger.debug(f"Applying {method_name} to {type(obj).__name__} with no args")
                result = method(obj)
            else:
                if method_args is not None:
                    if isinstance(method_args, dict):
                        final_args.update(method_args)
                    else:
                        if required_params:
                            final_args[required_params[0]] = method_args
                        else:
                            final_args[expected_params[0]] = method_args

                if extra_args:
                    final_args.update(extra_args)

                for param in required_params:
                    if param not in final_args:
                        logger.error(f"Missing required argument '{param}' for {method_name}")
                        return self._build_response(obj, False, method_name, None, f"Missing required argument '{param}'")

                valid_args = {k: v for k, v in final_args.items() if k in expected_params}
                result = method(obj, **valid_args) if 'obj' not in expected_params else method(**valid_args)

            logger.debug(f"Applied {method_name} to {type(obj).__name__}, result={result}")
            return self._build_response(obj, True, method_name, result)
        except TypeError as e:
            logger.error(f"TypeError applying {method_name} to {type(obj).__name__}: {str(e)}")
            return self._build_response(obj, False, method_name, None, f"TypeError: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to apply {method_name} to {type(obj).__name__}: {str(e)}")
            return self._build_response(obj, False, method_name, None, f"Failed to apply {method_name}: {str(e)}")
    
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
            Dict[str, Any]: Dictionary with status, object (name), method, result, and error (if status=False).
        """
        if attributes is None:
            attributes = {}
        logger.debug(f"Executing operation '{self._operation}' on {type(obj).__name__} with attributes={attributes}, method={method}")

        try:
            if method:
                method_func = getattr(self, method, None)
                if callable(method_func):
                    result = method_func(obj, attributes)
                    return self._build_response(obj, True, method, result)

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
                    return self._build_response(obj, True, method_name, result)

                prefixed_method_name = f"_{self._operation}_{method_name}"
                method = getattr(self, prefixed_method_name, None)
                if callable(method):
                    result = method(obj, object_attributes)
                    return self._build_response(obj, True, prefixed_method_name, result)

            obj_type_name = type(obj).__name__.lower()
            auto_method_name = f"_{self._operation}_{obj_type_name}"
            method = getattr(self, auto_method_name, None)
            if callable(method):
                result = method(obj, object_attributes)
                return self._build_response(obj, True, auto_method_name, result)

            if isinstance(obj, BaseContainer):
                base_method_name = f"_{self._operation}_basecontainer"
                method = getattr(self, base_method_name, None)
                if callable(method):
                    result = method(obj, object_attributes)
                    return self._build_response(obj, True, base_method_name, result)

            default_method_name = f"_{self._operation}"
            method = getattr(self, default_method_name, None)
            if callable(method):
                result = method(obj, object_attributes)
                return self._build_response(obj, True, default_method_name, result)

            raise ValueError(f"No suitable method found for operation '{self._operation}' and object '{obj_type_name}' in {self.__class__.__name__}")
        except ValueError as e:
            logger.error(f"Execution failed for operation '{self._operation}': {str(e)}")
            return self._build_response(obj, False, None, None, str(e))
        except Exception as e:
            logger.error(f"Unexpected error in execute for '{self._operation}': {str(e)}")
            return self._build_response(obj, False, None, None, str(e))
        
    def clear_cache(self) -> None:
        """Clear the method cache to free memory."""
        self._method_cache.clear()
        logger.debug(f"Cleared method cache for {self.__class__.__name__}")

    def clear(self) -> None:
        """Clear all references to prevent memory leaks.

        This method clears the manipulator reference, method registry, and cache
        to break potential reference cycles and aid garbage collection.
        """
        self._manipulator = None
        self._methods.clear()
        self.clear_cache()
        logger.debug(f"Cleared references for {self.__class__.__name__}")

    def _default_result(self, obj: Any) -> Dict[str, Any]:
        """Provide a default result when an operation cannot be executed.

        Args:
            obj (Any): The object associated with the operation.

        Returns:
            Dict[str, Any]: Dictionary with status, object (name), method, result, and error.
        """
        return self._build_response(obj, False, None, None, "Operation not executed")

    def _default_nested_result(self, obj: Any) -> Dict[str, Any]:
        """Provide a default result for nested operations.

        Args:
            obj (Any): The object associated with the operation.

        Returns:
            Dict[str, Any]: Dictionary with status, object (name), method, result, and error.
        """
        return self._build_response(obj, False, None, None, "Operation not executed")

    def __repr__(self) -> str:
        """Return a string representation of the Super instance.

        Returns:
            str: A formatted string with the class name.
        """
        return f"{self.__class__.__name__}()"

    def __del__(self) -> None:
        """Ensure cleanup of references to prevent memory leaks."""
        try:
            self.clear()
        except Exception as e:
            logger.error(f"Error during cleanup of {self.__class__.__name__}: {str(e)}")