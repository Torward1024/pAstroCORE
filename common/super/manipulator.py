from abc import ABC
from typing import Dict, Any, Optional, Callable, List, Type
from common.utils.logging_setup import logger
from functools import lru_cache
import inspect

class Manipulator(ABC):
    """Abstract class for managing and processing operations on objects.

    Provides a framework for registering operations and their associated methods, managing a central object,
    and processing requests. Maintains a registry of supported object types and their methods, with caching
    for performance. Subclasses can extend this to implement specific manipulation logic.

    Attributes:
        _managing_object (Optional[Any]): The central object being managed.
        _base_classes (List[Type]): List of base classes whose methods are registered.
        _operations (Dict[str, Callable]): Dictionary mapping operation names to super-instance handlers.
        _registry (Dict[Type, Dict[str, Callable]]): Registry of object types and their available methods.

    Notes:
        - Uses `functools.lru_cache` to optimize method registry generation.
        - Logging is integrated via `common.utils.logging_setup.logger`.
        - Operations are executed via super-instances that must have an `execute` method.
        - Results are returned as dictionaries with keys: status (bool), object (Any), method (str | None),
          result (Any), error (str | None, included only if status=False).

    Examples:
        >>> manip = Manipulator(base_classes=[list])
        >>> manip.register_operation("append", Super())  # Assuming super-class with execute method
        >>> manip.process_request({"operation": "append", "obj": [], "attributes": {"value": 1}})
        {"status": True, "object": [1], "method": "append", "result": True}
    """
    def __init__(self, managing_object: Optional[Any] = None,
                 base_classes: Optional[List[Type]] = None,
                 operations: Optional[Dict[str, Callable]] = None,
                 strict_type_check: bool = False):
        """Initialize a Manipulator with an optional managing object, base classes, and operations.

        Args:
            managing_object (Optional[Any]): The central object to manage. Defaults to None.
            base_classes (Optional[List[Type]]): List of base classes for method registration. Defaults to None.
            operations (Optional[Dict[str, Callable]]): Initial operations to register. Defaults to None.
            strict_type_check (bool): If True, enforce strict type checking for objects. Defaults to False.
        """
        self._managing_object = managing_object
        self._strict_type_check = strict_type_check
        self._base_classes = base_classes if base_classes is not None else []
        if managing_object is not None and type(managing_object) not in self._base_classes:
            self._base_classes.append(type(managing_object))
        self._operations = operations or {}
        self._registry = self._get_method_registry()
        logger.info(f"Initialized Manipulator with {len(self._operations)} initial operations")

    def set_managing_object(self, obj: Any) -> None:
        """Set the central managing object.

        Args:
            obj (Any): The object to set as the managing object.
        """
        self._managing_object = obj
        if obj is not None and type(obj) not in self._base_classes:
            self._base_classes.append(type(obj))
            self.update_registry()
        logger.info(f"Set managing object of type '{type(obj).__name__}' in Manipulator")

    def get_managing_object(self) -> Optional[Any]:
        """Retrieve the central managing object.

        Returns:
            Optional[Any]: The managing object, or None if not set.
        """
        return self._managing_object

    def _validate_object(self, obj: Any, obj_type: str) -> Any:
        """Validate that an object is provided and supported.

        Args:
            obj (Any): The object to validate.
            obj_type (str): Descriptive name of the object type for error messages.

        Returns:
            Any: The validated object.

        Raises:
            ValueError: If no object is provided or the type is unsupported.
        """
        effective_obj = obj if obj is not None else self._managing_object
        if effective_obj is None:
            logger.error(f"No {obj_type} or managing object provided for operation")
            raise ValueError(f"No {obj_type} or managing object provided")
        if self._strict_type_check and type(effective_obj) not in self._registry:
            logger.error(f"Unsupported object type for {obj_type}: {type(effective_obj)}")
            raise ValueError(f"Unsupported object type: {type(effective_obj)}")
        return effective_obj

    def get_methods_for_type(self, obj_type: Type) -> Dict[str, Callable]:
        """Retrieve the registered methods for a given object type.

        Args:
            obj_type (Type): The type of object to query methods for.

        Returns:
            Dict[str, Callable]: Dictionary of method names and their callable implementations.

        Raises:
            ValueError: If no methods are registered for the type.
        """
        if obj_type not in self._registry:
            logger.error(f"No methods registered for type {obj_type.__name__}")
            raise ValueError(f"No methods registered for type {obj_type.__name__}")
        return self._registry[obj_type]

    def update_registry(self, additional_classes: Optional[List[Type]] = None, clear_operations: bool = False) -> None:
        """Update the method registry with additional base classes or clear operations.

        Args:
            additional_classes (Optional[List[Type]]): Additional classes to register. Defaults to None.
            clear_operations (bool): If True, clear all operations. Defaults to False.
        """
        if clear_operations:
            self._operations.clear()
            logger.info("Cleared all operations in registry")
        if additional_classes:
            self._base_classes.extend([cls for cls in additional_classes if cls not in self._base_classes])
        self._get_method_registry.cache_clear()
        self._registry = self._get_method_registry()
        logger.info(f"Registry updated with {len(self._registry)} types")

    def register_operation(self, operation: str, super_instance: Callable) -> None:
        """Register an operation with its super-instance handler.

        Args:
            operation (str): The name of the operation.
            super_instance (Callable): The super-instance with an 'execute' method.

        Raises:
            ValueError: If the operation name is invalid or the super-instance lacks an 'execute' method.
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
    def _get_method_registry(self, validate_annotations: bool = False) -> Dict[Type, Dict[str, Callable]]:
        """Generate and cache the method registry for registered operations and base classes.

        Args:
            validate_annotations (bool): If True, validate method return annotations. Defaults to False.

        Returns:
            Dict[Type, Dict[str, Callable]]: Registry of types and their methods.
        """
        registry = {}
        for operation, instance in self._operations.items():
            super_type = type(instance)
            methods = {
                name: method for name, method in inspect.getmembers(instance, predicate=inspect.ismethod)
                if not name.startswith('__') and callable(method)
            }
            if validate_annotations:
                for name, method in methods.items():
                    sig = inspect.signature(method)
                    if not sig.return_annotation or sig.return_annotation is inspect.Signature.empty:
                        logger.warning(f"Method {name} in {super_type.__name__} lacks return annotation")
            registry[super_type] = methods
            logger.debug(f"Registered {len(methods)} methods for {super_type.__name__}: {list(methods.keys())}")

        for cls in self._base_classes:
            methods = {}
            if cls in (list, dict, set):
                for name in dir(cls):
                    if name.startswith('_'):
                        continue
                    method = getattr(cls, name, None)
                    if callable(method) and not isinstance(method, (type, property)):
                        methods[name] = method
            else:
                for name, method in inspect.getmembers(cls, predicate=lambda x: inspect.isfunction(x) or inspect.ismethod(x)):
                    if name.startswith('_') or not callable(method) or name in ('__getattribute__', '__setattr__'):
                        continue
                    if validate_annotations:
                        sig = inspect.signature(method)
                        if not sig.return_annotation or sig.return_annotation is inspect.Signature.empty:
                            logger.warning(f"Method {name} in {cls.__name__} lacks return annotation")
                    methods[name] = method
            if methods:
                registry[cls] = methods
                logger.debug(f"Registered {len(methods)} methods for {cls.__name__}: {list(methods.keys())}")
            else:
                logger.warning(f"No valid methods found for {cls.__name__}")
        return registry

    def process_request(self, request: Dict[str, Any]) -> Any:
        """Process a request or sequence of requests.

        Args:
            request (Dict[str, Any]): The request dictionary specifying the operation, object, and attributes.
                For a single request, expected keys include "operation", and optionally "obj", "method" (str),
                "attributes" (dict). For a sequence of requests, expected format is {request_id: {sub_request}}
                where each sub_request has the same structure as a single request.

        Returns:
            Any: For a single request, a dictionary with status, object, method, result, and error (if status=False).
                For a sequence of requests, a dictionary mapping request IDs to results.

        Raises:
            TypeError: If the request is not a dictionary or contains invalid types.
            ValueError: If the request structure is invalid.
        """
        if not isinstance(request, dict):
            logger.error(f"Invalid request type: expected dict, got {type(request).__name__}")
            raise TypeError(f"Request must be a dictionary, got {type(request).__name__}")

        # Debug: Log request keys and types
        logger.debug(f"Request keys and types: {[(k, type(v).__name__) for k, v in request.items()]}")

        # Check if the request is a potential sequence (no 'operation' key and multiple keys)
        is_potential_sequence = len(request) > 0 and "operation" not in request

        if is_potential_sequence:
            # Validate that all sub-requests are dictionaries
            invalid_sub_requests = [
                (k, type(v).__name__) for k, v in request.items() if not isinstance(v, dict)
            ]
            if invalid_sub_requests:
                error_msg = f"Invalid sub-request type in sequence: {invalid_sub_requests}"
                logger.error(error_msg)
                return {
                    "status": False,
                    "object": None,
                    "method": None,
                    "result": None,
                    "error": error_msg
                }

            # If all sub-requests are dictionaries, process as sequence
            logger.info(f"Processing sequence of {len(request)} requests")
            results = {}
            for req_id, sub_request in request.items():
                if "operation" not in sub_request:
                    logger.error(f"Missing 'operation' in sub-request for ID '{req_id}'")
                    results[req_id] = {
                        "status": False,
                        "object": sub_request.get("obj"),
                        "method": None,
                        "result": None,
                        "error": "Missing 'operation' in sub-request"
                    }
                    continue
                if "method" in sub_request and not isinstance(sub_request["method"], (str, type(None))):
                    logger.error(f"Invalid 'method' type in sub-request for ID '{req_id}': expected str or None, got {type(sub_request['method']).__name__}")
                    results[req_id] = {
                        "status": False,
                        "object": sub_request.get("obj"),
                        "method": None,
                        "result": None,
                        "error": f"Invalid 'method' type: expected str or None, got {type(sub_request['method']).__name__}"
                    }
                    continue
                if "attributes" in sub_request and not isinstance(sub_request["attributes"], (dict, type(None))):
                    logger.error(f"Invalid 'attributes' type in sub-request for ID '{req_id}': expected dict or None, got {type(sub_request['attributes']).__name__}")
                    results[req_id] = {
                        "status": False,
                        "object": sub_request.get("obj"),
                        "method": None,
                        "result": None,
                        "error": f"Invalid 'attributes' type: expected dict or None, got {type(sub_request['attributes']).__name__}"
                    }
                    continue
                result = self._process_single_request(sub_request)
                results[req_id] = result
            logger.debug(f"Sequence processing results: {results}")
            return results

        if "operation" not in request:
            error_msg = "No operation specified in request"
            logger.error(error_msg)
            return {"status": False, "object": request.get("obj"), "method": None, "result": None, "error": error_msg}

        if "method" in request and not isinstance(request["method"], (str, type(None))):
            error_msg = f"Invalid 'method' type: expected str or None, got {type(request['method']).__name__}"
            logger.error(error_msg)
            return {"status": False, "object": request.get("obj"), "method": None, "result": None, "error": error_msg}

        if "attributes" in request and not isinstance(request["attributes"], (dict, type(None))):
            error_msg = f"Invalid 'attributes' type: expected dict or None, got {type(request['attributes']).__name__}"
            logger.error(error_msg)
            return {"status": False, "object": request.get("obj"), "method": None, "result": None, "error": error_msg}

        return self._process_single_request(request)

    def _process_single_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single request by executing the specified operation.

        Args:
            request (Dict[str, Any]): The request dictionary with operation, object, and attributes.

        Returns:
            Dict[str, Any]: Dictionary with status, object, method, result, and error (if status=False).
        """
        operation = request.get("operation")
        obj = request.get("obj")
        method = request.get("method")
        attributes = request.get("attributes", {})

        if not operation:
            error_msg = "No operation specified in request"
            logger.error(error_msg)
            return {"status": False, "object": obj, "method": None, "result": None, "error": error_msg}

        super_instance = self._operations.get(operation)
        if super_instance is None:
            error_msg = f"Operation '{operation}' not registered"
            logger.error(error_msg)
            return {"status": False, "object": obj, "method": None, "result": None, "error": error_msg}

        try:
            effective_obj = self._validate_object(obj, "request object")
        except ValueError as e:
            logger.error(f"Object validation failed: {str(e)}")
            return {"status": False, "object": obj, "method": None, "result": None, "error": str(e)}

        execute_args = {"obj": effective_obj}
        if attributes or method:
            if not isinstance(attributes, dict):
                logger.error(f"Attributes must be a dictionary, got {type(attributes).__name__}")
                return {"status": False, "object": effective_obj, "method": None, "result": None, "error": "Invalid attributes type"}
            execute_args["attributes"] = attributes.copy()
            if method:
                execute_args["method"] = method

        try:
            super_result = super_instance.execute(**execute_args)
            logger.debug(f"Processed operation '{operation}' on {type(effective_obj).__name__}")
            result_dict = {
                "status": super_result["status"],
                "object": super_result["object"],
                "method": super_result["method"],
                "result": super_result["result"]
            }
            if not super_result["status"]:
                result_dict["error"] = super_result["error"]
            return result_dict
        except Exception as e:
            logger.error(f"Failed to process request '{operation}' via execute: {str(e)}")
            return {"status": False, "object": effective_obj, "method": None, "result": None, "error": str(e)}

    def get_supported_operations(self) -> List[str]:
        """Retrieve the list of supported operation names.

        Returns:
            List[str]: List of registered operation names.
        """
        return list(self._operations.keys())

    def __repr__(self) -> str:
        """Return a string representation of the Manipulator.

        Returns:
            str: A formatted string with the managing object type and operations.
        """
        obj_type = type(self._managing_object).__name__ if self._managing_object else "None"
        return f"Manipulator(managing_object='{obj_type}', operations={list(self._operations.keys())})"