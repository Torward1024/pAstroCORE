# super/manipulator.py
from abc import ABC
from typing import Dict, Any, Optional, Union, Callable, List, Type
from base.project import Project
from super.configurator import Configurator, DefaultConfigurator
from super.inspector import Inspector, DefaultInspector
from super.calculator import Calculator, DefaultCalculator
from utils.logging_setup import logger
from functools import lru_cache
import inspect

class Manipulator(ABC):
    """Super-class for managing objects and orchestrating interactions with other super-classes."""
    """Super-class for managing objects and orchestrating interactions with dynamically registered super-classes."""
    def __init__(self, managing_object: Optional[Any] = None,
                 base_classes: Optional[List[Type]] = None,
                 operations: Optional[Dict[str, Callable]] = None):
        """
        Initialize the Manipulator with an optional managing object and base classes.
        
        Args:
            managing_object: The object to manage (e.g., Project).
            base_classes: List of base classes to register methods for.
            operations: Optional initial dictionary of operation names mapped to super-class instances.
        """
        self._managing_object = managing_object
        self._base_classes = base_classes if base_classes is not None else []
        self._operations = operations or {}  # Пустой словарь по умолчанию
        self._registry = self._get_method_registry()
        logger.info(f"Initialized Manipulator with {len(self._operations)} initial operations")

    def set_managing_object(self, obj: Any) -> None:
        """Set the object to be managed."""
        self._managing_object = obj
        logger.info(f"Set managing object of type '{type(obj).__name__}' in Manipulator")

    def get_managing_object(self) -> Optional[Any]:
        """Get the managed object."""
        return self._managing_object

    def _validate_object(self, obj: Any, obj_type: str) -> None:
        """Validate the object type and presence."""
        if obj is None and self._managing_object is None:
            logger.error(f"No {obj_type} or managing object provided for operation")
            raise ValueError(f"No {obj_type} or managing object provided")
        if obj is not None and type(obj) not in self._registry:
            logger.error(f"Unsupported object type for {obj_type}: {type(obj)}")
            raise ValueError(f"Unsupported object type: {type(obj)}")

    def get_methods_for_type(self, obj_type: Type) -> Dict[str, Callable]:
        """Get methods registered for a specific type."""
        if obj_type not in self._registry:
            logger.error(f"No methods registered for type {obj_type.__name__}")
            raise ValueError(f"No methods registered for type {obj_type.__name__}")
        return self._registry[obj_type]

    def update_registry(self, additional_classes: Optional[List[Type]] = None) -> None:
        """Update the method registry in runtime."""
        if additional_classes:
            self._base_classes.extend([cls for cls in additional_classes if cls not in self._base_classes])
        self._registry = self._get_method_registry.cache_clear() or self._get_method_registry()
        logger.info(f"Registry updated with {len(self._registry)} types")

    def register_operation(self, operation: str, super_instance: Callable) -> None:
        """Register a new operation with its super-class instance or callable."""
        if not isinstance(operation, str) or not operation:
            logger.error("Operation name must be a non-empty string")
            raise ValueError("Operation name must be a non-empty string")
        if not (hasattr(super_instance, "execute") or callable(super_instance)):
            logger.error(f"Super-instance for '{operation}' must have 'execute' method or be callable")
            raise ValueError(f"Super-instance for '{operation}' must be executable")
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
        """Build a registry of methods for supported types."""
        registry = {}
        # Регистрируем методы супер-классов из _operations
        for operation, instance in self._operations.items():
            super_type = type(instance)
            methods = {
                name: method for name, method in inspect.getmembers(instance, predicate=inspect.ismethod)
                if not name.startswith('__') and callable(method)
            }
            registry[super_type] = methods
            logger.debug(f"Registered {len(methods)} methods for {super_type.__name__} via operation '{operation}'")

        for cls in self._base_classes:
            methods = {
                name: getattr(cls, name) for name, _ in inspect.getmembers(cls)
                if (inspect.isfunction(getattr(cls, name, None)) or inspect.ismethod(getattr(cls, name, None)))
                and not name.startswith('_') and callable(getattr(cls, name))
            }
            registry[cls] = methods
            logger.debug(f"Registered {len(methods)} methods for {cls.__name__}")

        logger.info(f"Method registry initialized with {len(registry)} types")
        return registry

    def process_request(self, request: Dict[str, Any]) -> Any:
        """Process a request by delegating to the appropriate super-class."""
        operation = request.get("operation")
        if not operation or operation not in self._operations:
            logger.error(f"Unsupported operation: {operation}. Available: {list(self._operations.keys())}")
            raise ValueError(f"Unsupported operation: {operation}")
        
        super_instance = self._operations[operation]
        target_obj = request.get("obj", self._managing_object)
        target = request.get("target")

        execute_args = {
            "obj": target_obj,
            "attributes": request.get("attributes", {})
        }
        
        if target and target_obj:
            self._validate_object(target_obj, target)

        try:
            if hasattr(super_instance, "execute"):
                result = super_instance.execute(**execute_args)
            elif callable(super_instance):
                result = super_instance(**execute_args)
            else:
                logger.error(f"Operation '{operation}' has no executable implementation")
                raise ValueError(f"No executable implementation for '{operation}'")
            logger.debug(f"Processed request '{operation}' with args: {execute_args}")
            return result
        except Exception as e:
            logger.error(f"Failed to process request '{operation}': {str(e)}")
            raise

    def get_supported_operations(self) -> List[str]:
        """Return a list of supported operation names."""
        return list(self._operations.keys())

    def __repr__(self) -> str:
        obj_type = type(self._managing_object).__name__ if self._managing_object else "None"
        return f"Manipulator(managing_object='{obj_type}', operations={list(self._operations.keys())})"

class DefaultManipulator(Manipulator):
    """Default implementation of Manipulator tailored for Project-based radio astronomy planning."""
    def __init__(self, project: Optional['Project'] = None):
        from base.project import Project
        from base.observation import Observation
        from base.frequencies import IF, Frequencies
        from base.sources import Source, Sources
        from base.telescopes import Telescope, SpaceTelescope, Telescopes
        from base.scans import Scan, Scans
        from super.configurator import DefaultConfigurator
        from super.inspector import DefaultInspector
        from super.calculator import DefaultCalculator

        base_classes = [
            Project, Observation, IF, Frequencies, Source, Sources,
            Telescope, SpaceTelescope, Telescopes, Scan, Scans
        ]
        
        super().__init__(managing_object=project, base_classes=base_classes)
        
        self.register_operation("configure", DefaultConfigurator(self))
        self.register_operation("inspect", DefaultInspector(self))
        self.register_operation("calculate", DefaultCalculator(self))
        
        logger.info("Initialized DefaultManipulator with default operations")