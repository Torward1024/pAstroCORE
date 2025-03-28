# super/manipulator.py
from abc import ABC
from typing import Dict, Any, Optional, Union, Callable
from base.project import Project
from base.observation import Observation
from base.frequencies import IF, Frequencies
from base.sources import Source, Sources
from base.scans import Scan, Scans
from base.telescopes import Telescope, SpaceTelescope, Telescopes
from super.configurator import Configurator, DefaultConfigurator
from super.inspector import Inspector, DefaultInspector
from super.calculator import Calculator, DefaultCalculator
from utils.logging_setup import logger
from functools import lru_cache
import inspect

class Manipulator(ABC):
    """Super-class for managing Project and orchestrating interactions with other super-classes."""
    def __init__(self, project: Optional[Project] = None,
             configurator: Optional[Configurator] = None,
             inspector: Optional[Inspector] = None,
             calculator: Optional[Calculator] = None):
        self._project = project
        self._configurator = configurator if configurator else DefaultConfigurator(self)
        self._inspector = inspector if inspector else DefaultInspector(self)
        self._calculator = calculator if calculator else DefaultCalculator(self)
        self._registry = self._get_method_registry()
        logger.info("Initialized Manipulator")

    def set_project(self, project: Project) -> None:
        if not isinstance(project, Project):
            logger.error(f"Expected Project instance, got {type(project)}")
            raise ValueError(f"Expected Project instance, got {type(project)}")
        self._project = project
        logger.info(f"Set project '{project.get_name()}' in Manipulator")

    def get_project(self) -> Optional[Project]:
        return self._project

    def _validate_object(self, obj: Any, obj_type: str) -> None:
        if obj is None and self._project is None:
            logger.error(f"No {obj_type} or project provided for operation")
            raise ValueError(f"No {obj_type} or project provided")
        if obj is not None and not isinstance(obj, (Project, Observation)):
            logger.error(f"Unsupported object type for {obj_type}: {type(obj)}")
            raise ValueError(f"Unsupported object type: {type(obj)}")

    def _get_super_class_instance(self, operation: str) -> Union[Configurator, Inspector, Calculator]:
        operation_map = {
            "configure": self._configurator,
            "inspect": self._inspector,
            "calculate": self._calculator
        }
        if operation not in operation_map:
            logger.error(f"Unsupported operation: {operation}")
            raise ValueError(f"Unsupported operation: {operation}")
        return operation_map[operation]
    
    def get_methods_for_type(self, obj_type: type) -> Dict[str, Callable]:
        """Get a specific section of the method registry (e.g., 'configure', 'inspect', 'calculate')"""
        if obj_type not in self._registry:
            logger.error(f"No methods registered for type {obj_type.__name__}")
            raise ValueError(f"No methods registered for type {obj_type.__name__}")
        return self._registry[obj_type]

    @lru_cache(maxsize=1)
    def _get_method_registry(self) -> Dict[type, Dict[str, Callable]]:
        from base.frequencies import IF, Frequencies
        from base.sources import Source, Sources
        from base.telescopes import Telescope, SpaceTelescope, Telescopes
        from base.scans import Scan, Scans
        from base.observation import Observation
        from base.project import Project

        base_classes = [
            Project, Observation, IF, Frequencies, Source, Sources,
            Telescope, SpaceTelescope, Telescopes, Scan, Scans,
            Configurator, Inspector, Calculator
        ]

        registry = {}

        for super_class, instance in [
            (Configurator, self._configurator),
            (Inspector, self._inspector),
            (Calculator, self._calculator)
        ]:
            methods = {
                name: method for name, method in inspect.getmembers(instance, predicate=inspect.ismethod)
                if not name.startswith('__')
            }
            registry[super_class] = methods
            logger.debug(f"Registered {len(methods)} methods for {super_class.__name__}")

        for cls in base_classes:
            if cls in {Configurator, Inspector, Calculator}:
                continue
            methods = {
                name: method for name, method in inspect.getmembers(cls, predicate=inspect.ismethod)
                if not name.startswith('_')  # Только публичные методы
            }
            registry[cls] = methods
            logger.debug(f"Registered {len(methods)} methods for {cls.__name__}")

        logger.info(f"Method registry initialized with {len(registry)} types")
        return registry

    def process_request(self, operation: str, target: str, attributes: Dict[str, Any],
                        obj: Optional[Union[Project, Observation]] = None) -> Any:
        if not isinstance(attributes, dict):
            logger.error(f"Attributes must be a dictionary, got {type(attributes)}")
            raise ValueError(f"Attributes must be a dictionary, got {type(attributes)}")

        target_obj = obj if obj is not None else self._project
        self._validate_object(target_obj, target)

        operation_map = {
            "configure": Configurator,
            "inspect": Inspector,
            "calculate": Calculator
        }

        if operation not in operation_map:
            logger.error(f"Unsupported operation: {operation}")
            raise ValueError(f"Unsupported operation: {operation}")

        super_type = operation_map[operation]
        super_instance = {
            Configurator: self._configurator,
            Inspector: self._inspector,
            Calculator: self._calculator
        }[super_type]

        obj_type = type(target_obj)
        if obj_type not in self._registry:
            logger.error(f"Object type {obj_type} not supported")
            raise ValueError(f"Object type {obj_type} not supported")

        if "execute" not in self._registry[super_type]:
            logger.error(f"No execute method found for {super_type.__name__}")
            raise ValueError(f"No execute method for {operation}")

        return super_instance.execute(target_obj, attributes)

    def __repr__(self) -> str:
        project_name = self._project.get_name() if self._project else "None"
        return f"Manipulator(project='{project_name}')"

class DefaultManipulator(Manipulator):
    def __init__(self, project: Optional[Project] = None):
        super().__init__(project=project)
        logger.info("Initialized DefaultManipulator")