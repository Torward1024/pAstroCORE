# super/manipulator.py
from abc import ABC
from typing import Dict, Any, Optional, Union
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
        logger.info("Initialized Manipulator")
        self._project = project
        self._configurator = configurator if configurator else DefaultConfigurator(self)
        self._inspector = inspector if inspector else DefaultInspector(self)
        self._calculator = calculator if calculator else DefaultCalculator(self)
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
    
    def get_registry_section(self, section: str) -> Dict[type, Dict[str, Any]]:
        """Get a specific section of the method registry (e.g., 'configure', 'inspect', 'calculate')"""
        registry = self._get_method_registry()
        if section not in registry:
            logger.error(f"Invalid registry section requested: {section}")
            raise ValueError(f"Invalid section: {section}")
        return registry[section]

    @lru_cache(maxsize=1)
    def _get_method_registry(self) -> Dict[str, Dict[type, Dict[str, Any]]]:
        from base.frequencies import IF, Frequencies
        from base.sources import Source, Sources
        from base.telescopes import Telescope, SpaceTelescope, Telescopes
        from base.scans import Scan, Scans
        from base.observation import Observation
        from base.project import Project

        base_classes = [
            Project, Observation, IF, Frequencies, Source, Sources,
            Telescope, SpaceTelescope, Telescopes, Scan, Scans
        ]
        type_map = {cls.__name__.lower(): cls for cls in base_classes}

        access_map = {
            IF: ("frequencies", "get_frequencies", "get_IF"),
            Frequencies: ("frequencies", "get_frequencies", None),
            Source: ("sources", "get_sources", "get_source"),
            Sources: ("sources", "get_sources", None),
            Telescope: ("telescopes", "get_telescopes", "get_telescope"), 
            SpaceTelescope: ("telescopes", "get_telescopes", "get_telescope"),
            Telescopes: ("telescopes", "get_telescopes", None),
            Scan: ("scans", "get_scans", "get_scan"),
            Scans: ("scans", "get_scans", None),
            Observation: ("observation", None, None),
            Project: ("project", None, "get_observation")
        }

        registry = {"configure": {}, "inspect": {}, "calculate": {}}

        # Configure methods
        for name, method in inspect.getmembers(self._configurator, predicate=inspect.isfunction):
            if name.startswith("_configure_"):
                target_name = name[len("_configure_"):]
                target_type = type_map.get(target_name)
                if target_type:
                    target_str, access_method, item_method = access_map.get(target_type, (target_name, None, None))
                    registry["configure"][target_type] = {
                        "config_func": method,
                        "target_name": target_str,
                        "access_method": access_method,
                        "item_method": item_method
                    }
                elif target_name == "telescope":
                    for t in [Telescope, SpaceTelescope]:
                        target_str, access_method, item_method = access_map[t]
                        registry["configure"][t] = {
                            "config_func": method,
                            "target_name": target_str,
                            "access_method": access_method,
                            "item_method": item_method
                        }

        # Inspect methods (аналогично)
        for name, method in inspect.getmembers(self._inspector, predicate=inspect.isfunction):
            if name.startswith("_inspect_"):
                target_name = name[len("_inspect_"):]
                target_type = type_map.get(target_name)
                if target_type:
                    target_str, access_method, item_method = access_map.get(target_type, (target_name, None, None))
                    registry["inspect"][target_type] = {
                        "inspect_func": method,
                        "target_name": target_str,
                        "access_method": access_method,
                        "item_method": item_method
                    }
                elif target_name == "telescope":
                    for t in [Telescope, SpaceTelescope]:
                        target_str, access_method, item_method = access_map[t]
                        registry["inspect"][t] = {
                            "inspect_func": method,
                            "target_name": target_str,
                            "access_method": access_method,
                            "item_method": item_method
                        }

        # Calculate methods
        calc_methods = {}
        for name, method in inspect.getmembers(Calculator, predicate=inspect.isfunction):
            if name.startswith("_calculate_"):
                calc_name = name[len("_calculate_"):]
                calc_methods[calc_name] = method
        if calc_methods:
            for t in [Observation, Project]:
                target_str, access_method, item_method = access_map[t]
                registry["calculate"][t] = {
                    "methods": calc_methods,
                    "target_name": target_str,
                    "access_method": access_method,
                    "item_method": item_method
                }

        logger.debug(f"Method registry initialized with {len(registry['configure'])} configure, "
                    f"{len(registry['inspect'])} inspect, and {len(registry['calculate'])} calculate entries")
        return registry

    def process_request(self, operation: str, target: str, attributes: Dict[str, Any],
                    obj: Optional[Union[Project, Observation]] = None) -> Dict[str, Any]:
        if not isinstance(attributes, dict):
            logger.error(f"Attributes must be a dictionary, got {type(attributes)}")
            raise ValueError(f"Attributes must be a dictionary, got {type(attributes)}")

        target_obj = obj if obj is not None else self._project
        self._validate_object(target_obj, target)

        registry = self._get_method_registry()
        super_instance = self._get_super_class_instance(operation)
        section = registry[operation]

        
        target_types = {t: info for t, info in section.items() if info["target_name"] == target}
        if not target_types:
            logger.error(f"Unsupported target: {target}")
            raise ValueError(f"Unsupported target: {target}")

        
        obj_type = type(target_obj)
        if obj_type not in section:
            logger.error(f"Object type {obj_type} not supported for operation {operation}")
            raise ValueError(f"Object type {obj_type} not supported")

        
        if obj_type in {Project, Observation} and target != section[obj_type]["target_name"]:
            
            for t, info in target_types.items():
                if info["access_method"] and hasattr(target_obj, info["access_method"]):
                    index_key = f"{target}_index"
                    if index_key in attributes:
                        index = attributes[index_key]
                        if not isinstance(index, int):
                            logger.error(f"Invalid {index_key} {index} for {target}")
                            raise ValueError(f"Invalid {index_key}: {index}")
                        
                        container = getattr(target_obj, info["access_method"])()
                        
                        if info["item_method"] and hasattr(container, info["item_method"]):
                            try:
                                target_obj = getattr(container, info["item_method"])(index)
                            except IndexError:
                                logger.error(f"Index {index} out of range for {target}")
                                raise ValueError(f"Index {index} out of range for {target}")
                        else:
                            # Если item_method нет (например, для Telescopes), используем список
                            all_items = container.get_all_telescopes()  # Предполагаем для Telescopes
                            if not (0 <= index < len(all_items)):
                                logger.error(f"Invalid {index_key} {index} for {target}")
                                raise ValueError(f"Invalid {index_key}: {index}")
                            target_obj = all_items[index]
                        attributes = {k: v for k, v in attributes.items() if k != index_key}
                        break
                    else:
                        target_obj = getattr(target_obj, info["access_method"])()
                        break
            else:
                logger.error(f"No valid access method for {target} in {obj_type}")
                raise ValueError(f"Cannot access {target} from {obj_type}")

        if target == "observation" and isinstance(target_obj, Project):
            obs_index = attributes.get("observation_index")
            if obs_index is None or not isinstance(obs_index, int) or not (0 <= obs_index < len(target_obj.get_observations())):
                logger.error(f"Invalid or missing observation_index for project '{target_obj.get_name()}'")
                raise ValueError(f"Invalid observation_index: {obs_index}")
            target_obj = target_obj.get_observation(obs_index)
            attributes = {k: v for k, v in attributes.items() if k != "observation_index"}

        return super_instance.execute(operation, target_obj, attributes, section)

    def __repr__(self) -> str:
        project_name = self._project.get_name() if self._project else "None"
        return f"Manipulator(project='{project_name}')"

class DefaultManipulator(Manipulator):
    def __init__(self, project: Optional[Project] = None):
        super().__init__(project=project)
        logger.info("Initialized DefaultManipulator")