from abc import ABC
from typing import Dict, Any, Optional, Callable, List, Type
from common.utils.logging_setup import logger
from functools import lru_cache
import inspect

class Manipulator(ABC):
    """Abstract ``mega`` class for managing and processing operations on objects.

    Provides a framework for registering operations and their associated methods, managing a central object,
    and processing requests. Maintains a registry of supported object types and their methods, with caching
    for performance. Super-classes can extend this to implement specific manipulation logic.

    Attributes:
        _managing_object (Optional[Any]): The central object being managed by the manipulator.
        _base_classes (List[Type]): List of base classes whose methods are registered.
        _operations (Dict[str, Callable]): Dictionary mapping operation names to their super-instance handlers.
        _registry (Dict[Type, Dict[str, Callable]]): Registry of object types and their available methods.

    Notes:
        - Uses `functools.lru_cache` to optimize method registry generation.
        - Logging is integrated via `common.utils.logging_setup.logger`.
        - Operations are executed via super-instances (e.g., super-classes `Super`) that must have an `execute` method.

    Examples:
        >>> manip = Manipulator(base_classes=[list])
        >>> manip.register_operation("append", Super())  # Assuming super-class with execute method
        >>> manip.process_request({"operation": "append", "obj": [], "attributes": {"value": 1}})
        True  # Assuming Super.execute modifies the list and returns True
    """
    def __init__(self, managing_object: Optional[Any] = None,
                 base_classes: Optional[List[Type]] = None,
                 operations: Optional[Dict[str, Callable]] = None):
        """Initialize a Manipulator with an optional managing object, base classes, and operations.

        Args:
            managing_object (Optional[Any]): The central object to manage. Defaults to None.
            base_classes (Optional[List[Type]]): List of classes whose methods are registered. Defaults to None (empty list).
            operations (Optional[Dict[str, Callable]]): Initial operations mapped to super-instances. Defaults to None (empty dict).
        """
        self._managing_object = managing_object
        self._base_classes = base_classes if base_classes is not None else []
        self._operations = operations or {}
        self._registry = self._get_method_registry()
        logger.info(f"Initialized Manipulator with {len(self._operations)} initial operations")

    def set_managing_object(self, obj: Any) -> None:
        """Set the central managing object.

        Args:
            obj (Any): The object to set as the managing object.
        """
        self._managing_object = obj
        logger.info(f"Set managing object of type '{type(obj).__name__}' in Manipulator")

    def get_managing_object(self) -> Optional[Any]:
        """Retrieve the central managing object.

        Returns:
            Optional[Any]: The managing object, or None if not set.
        """
        return self._managing_object

    def _validate_object(self, obj: Any, obj_type: str) -> None:
        """Validate that an object is provided and supported.

        Args:
            obj (Any): The object to validate.
            obj_type (str): Descriptive name of the object type for error messages.

        Raises:
            ValueError: If neither obj nor _managing_object is provided, or if obj type is not in the registry.
        """
        if obj is None and self._managing_object is None:
            logger.error(f"No {obj_type} or managing object provided for operation")
            raise ValueError(f"No {obj_type} or managing object provided")
        if obj is not None and type(obj) not in self._registry:
            logger.error(f"Unsupported object type for {obj_type}: {type(obj)}")
            raise ValueError(f"Unsupported object type: {type(obj)}")

    def get_methods_for_type(self, obj_type: Type) -> Dict[str, Callable]:
        """Retrieve the registered methods for a given object type.

        Args:
            obj_type (Type): The type of object to query methods for.

        Returns:
            Dict[str, Callable]: Dictionary of method names mapped to their callable implementations.

        Raises:
            ValueError: If no methods are registered for the specified type.
        """
        if obj_type not in self._registry:
            logger.error(f"No methods registered for type {obj_type.__name__}")
            raise ValueError(f"No methods registered for type {obj_type.__name__}")
        return self._registry[obj_type]

    def update_registry(self, additional_classes: Optional[List[Type]] = None, clear_operations: bool = False) -> None:
        """Update the method registry with additional base classes.

        Clears the cache and rebuilds the registry if additional classes are provided.

        Args:
            additional_classes (Optional[List[Type]]): Additional classes to register. Defaults to None.
        """
        if additional_classes:
            self._base_classes.extend([cls for cls in additional_classes if cls not in self._base_classes])
        if clear_operations:
            self._operations.clear()
        self._registry = self._get_method_registry.cache_clear() or self._get_method_registry()
        logger.info(f"Registry updated with {len(self._registry)} types")

    def register_operation(self, operation: str, super_instance: Callable) -> None:
        """Register an operation with its super-instance handler.

        Args:
            operation (str): The name of the operation. Must be a non-empty string.
            super_instance (Callable): The super-instance (e.g., super-class `Super`) with an `execute` method.

        Raises:
            ValueError: If operation is not a non-empty string or super_instance lacks an `execute` method.
        """
        if not isinstance(operation, str) or not operation:
            logger.error("Operation name must be a non-empty string")
            raise ValueError("Operation name must be a non-empty string")
        if not hasattr(super_instance, "execute"):
            logger.error(f"Super-instance for '{operation}' must have 'execute' method")
            raise ValueError(f"Super-instance for '{operation}' must have 'execute' method")
        super_instance._operation = operation
        self._operations[operation] = super_instance

        super_type = type(super_instance)
        if super_type not in self._registry:
            methods = {
                name: method for name, method in inspect.getmembers(super_instance, predicate=inspect.ismethod)
                if not name.startswith('__') and callable(method)
            }
            self._registry[super_type] = methods
            logger.debug(f"Registered {len(methods)} methods for {super_type.__name__}")
        logger.info(f"Registered operation '{operation}' with {type(super_instance).__name__}")

    @lru_cache(maxsize=2048)
    def _get_method_registry(self) -> Dict[Type, Dict[str, Callable]]:
        """Generate and cache the method registry for registered operations and base classes.

        Returns:
            Dict[Type, Dict[str, Callable]]: A registry mapping object types to their methods.

        Notes:
            - Cached with a max size of 2048 entries to improve performance.
        """
        registry = {}
        for operation, instance in self._operations.items():
            super_type = type(instance)
            methods = {
                name: method for name, method in inspect.getmembers(instance, predicate=inspect.ismethod)
                if not name.startswith('__') and callable(method)
            }
            registry[super_type] = methods
            logger.info(f"Registered {len(methods)} methods for {super_type.__name__}: {list(methods.keys())}")

        for cls in self._base_classes:
            methods = {
                name: getattr(cls, name) for name, _ in inspect.getmembers(cls)
                if (inspect.isfunction(getattr(cls, name, None)) or inspect.ismethod(getattr(cls, name, None)))
                and not name.startswith('_') and callable(getattr(cls, name))
            }
            for name, method in methods.items():
                if not callable(method):
                    logger.error(f"Method {name} for {cls.__name__} is not callable: {method} (type: {type(method).__name__})")
            registry[cls] = methods
        return registry

    def process_request(self, request: Dict[str, Any]) -> Any:
        """Process a request or sequence of requests.

        Handles both single requests and nested dictionaries of requests, delegating to `_process_single_request`.

        Args:
            request (Dict[str, Any]): A dictionary specifying the operation, object, and attributes, or a sequence of such dictionaries.

        Returns:
            Any: The result of the request(s). For a single request, the result of `_process_single_request`; for a sequence, a dict of results.

        Examples:
            >>> manip.process_request({"operation": "append", "obj": [], "attributes": {"value": 1}})
            True
            >>> manip.process_request({"req1": {"operation": "append", "obj": [], "attributes": {"value": 1}}})
            {'req1': True}
        """
        if all(isinstance(k, str) and isinstance(v, dict) for k, v in request.items()) and "operation" not in request:
            results = {}
            logger.info(f"Processing sequence of {len(request)} requests")
            for req_id, sub_request in request.items():
                if not isinstance(sub_request, dict):
                    logger.error(f"Sub-request '{req_id}' must be a dict, got {type(sub_request)}")
                    raise TypeError(f"Sub-request '{req_id}' must be a dict")
                result = self._process_single_request(sub_request)
                results[req_id] = result
            return results
        if not isinstance(request, dict):
            logger.error(f"Request must be a dict, got {type(request)}")
            raise TypeError("Request must be a dict")
        return self._process_single_request(request)

    def _process_single_request(self, request: Dict[str, Any]) -> Any:
        """Process a single request by executing the specified operation."""
        operation = request.get("operation")
        obj = request.get("obj")
        method = request.get("method")
        attributes = request.get("attributes", {})
        
        if not operation:
            logger.error("No operation specified in request")
            return False
        
        super_instance = self._operations.get(operation)
        if super_instance is None:
            logger.error(f"No super instance registered for operation '{operation}'")
            return False
        
        if not isinstance(attributes, dict):
            logger.error(f"Attributes must be a dictionary, got {type(attributes)}")
            return False
            
        execute_args = {"obj": obj}
        if attributes or method:
            execute_args["attributes"] = attributes.copy()
            if method:
                execute_args["method"] = method
        try:
            result = super_instance.execute(**execute_args)
            return result
        except Exception as e:
            logger.error(f"Failed to process request '{operation}' via execute: {str(e)}")
            return False

    def get_supported_operations(self) -> List[str]:
        """Retrieve the list of supported operation names.

        Returns:
            List[str]: A list of registered operation names.
        """
        return list(self._operations.keys())

    def __repr__(self) -> str:
        """Return a string representation of the Manipulator.

        Returns:
            str: A formatted string with the managing object type and registered operations.
        """
        obj_type = type(self._managing_object).__name__ if self._managing_object else "None"
        return f"Manipulator(managing_object='{obj_type}', operations={list(self._operations.keys())})"