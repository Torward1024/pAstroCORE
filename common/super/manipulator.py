from abc import ABC
from typing import Dict, Any, Optional, Callable, List, Type
from common.utils.logging_setup import logger
from functools import lru_cache
import inspect

class Manipulator(ABC):
    def __init__(self, managing_object: Optional[Any] = None,
                 base_classes: Optional[List[Type]] = None,
                 operations: Optional[Dict[str, Callable]] = None):
        self._managing_object = managing_object
        self._base_classes = base_classes if base_classes is not None else []
        self._operations = operations or {}
        self._registry = self._get_method_registry()
        logger.info(f"Initialized Manipulator with {len(self._operations)} initial operations")

    def set_managing_object(self, obj: Any) -> None:
        self._managing_object = obj
        logger.info(f"Set managing object of type '{type(obj).__name__}' in Manipulator")

    def get_managing_object(self) -> Optional[Any]:
        return self._managing_object

    def _validate_object(self, obj: Any, obj_type: str) -> None:
        if obj is None and self._managing_object is None:
            logger.error(f"No {obj_type} or managing object provided for operation")
            raise ValueError(f"No {obj_type} or managing object provided")
        if obj is not None and type(obj) not in self._registry:
            logger.error(f"Unsupported object type for {obj_type}: {type(obj)}")
            raise ValueError(f"Unsupported object type: {type(obj)}")

    def get_methods_for_type(self, obj_type: Type) -> Dict[str, Callable]:
        if obj_type not in self._registry:
            logger.error(f"No methods registered for type {obj_type.__name__}")
            raise ValueError(f"No methods registered for type {obj_type.__name__}")
        return self._registry[obj_type]

    def update_registry(self, additional_classes: Optional[List[Type]] = None) -> None:
        if additional_classes:
            self._base_classes.extend([cls for cls in additional_classes if cls not in self._base_classes])
        self._registry = self._get_method_registry.cache_clear() or self._get_method_registry()
        logger.info(f"Registry updated with {len(self._registry)} types")

    def register_operation(self, operation: str, super_instance: Callable) -> None:
        if not isinstance(operation, str) or not operation:
            logger.error("Operation name must be a non-empty string")
            raise ValueError("Operation name must be a non-empty string")
        if not hasattr(super_instance, "execute"):
            logger.error(f"Super-instance for '{operation}' must have 'execute' method")
            raise ValueError(f"Super-instance for '{operation}' must have 'execute' method")
        # Задаем _operation для super_instance
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

    @lru_cache(maxsize=128)
    def _get_method_registry(self) -> Dict[Type, Dict[str, Callable]]:
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
        if all(isinstance(k, str) and isinstance(v, dict) for k, v in request.items()) and "operation" not in request:
            results = {}
            logger.info(f"Processing sequence of {len(request)} requests")
            for req_id, sub_request in request.items():
                result = self._process_single_request(sub_request)
                results[req_id] = result
            return results
        return self._process_single_request(request)

    def _process_single_request(self, request: Dict[str, Any]) -> Any:
        operation = request.get("operation")
        obj = request.get("obj")
        attributes = request.get("attributes", {})

        if not operation:
            logger.error("No operation specified in request")
            return False

        super_instance = self._operations.get(operation)
        if super_instance is None:
            logger.error(f"No super instance registered for operation '{operation}'")
            return False

        execute_args = {"obj": obj}
        if attributes:
            execute_args["attributes"] = attributes
        try:
            result = super_instance.execute(**execute_args)
            return result
        except Exception as e:
            logger.error(f"Failed to process request '{operation}' via execute: {str(e)}")
            return False

    def get_supported_operations(self) -> List[str]:
        return list(self._operations.keys())

    def __repr__(self) -> str:
        obj_type = type(self._managing_object).__name__ if self._managing_object else "None"
        return f"Manipulator(managing_object='{obj_type}', operations={list(self._operations.keys())})"