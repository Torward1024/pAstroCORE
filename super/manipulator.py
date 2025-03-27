# super/manipulator.py
from abc import ABC
from typing import Dict, Any, Optional, Union, Callable
from base.project import Project
from base.observation import Observation
from super.configurator import Configurator, DefaultConfigurator
from super.inspector import Inspector, DefaultInspector
from super.calculator import Calculator, DefaultCalculator
from utils.logging_setup import logger
from functools import lru_cache

class Manipulator(ABC):
    """Super-class for managing Project and orchestrating interactions with other super-classes.

    Attributes:
        _project (Project): The project being managed.
        _configurator (Configurator): Instance for configuring objects.
        _inspector (Inspector): Instance for inspecting objects.
        _calculator (Calculator): Instance for performing calculations.

    Methods:
        set_project: Set or update the current project.
        get_project: Retrieve the current project.
        process_request: Universal method to handle configuration, inspection, or calculation requests.
        _validate_object: Validate the target object for operations.
        _get_super_class_instance: Retrieve the appropriate super-class instance.
    """
    def __init__(self, project: Optional[Project] = None,
                 configurator: Optional[Configurator] = None,
                 inspector: Optional[Inspector] = None,
                 calculator: Optional[Calculator] = None):
        """Initialize the Manipulator"""
        self._project = project
        self._configurator = configurator if configurator else DefaultConfigurator()
        self._inspector = inspector if inspector else DefaultInspector()
        self._calculator = calculator if calculator else DefaultCalculator()
        logger.info("Initialized Manipulator")

    def set_project(self, project: Project) -> None:
        """Set or update the current project"""
        if not isinstance(project, Project):
            logger.error(f"Expected Project instance, got {type(project)}")
            raise ValueError(f"Expected Project instance, got {type(project)}")
        self._project = project
        logger.info(f"Set project '{project.get_name()}' in Manipulator")

    def get_project(self) -> Optional[Project]:
        """Retrieve the current project"""
        return self._project

    def _validate_object(self, obj: Any, obj_type: str) -> None:
        """Validate the target object for operations"""
        if obj is None and self._project is None:
            logger.error(f"No {obj_type} or project provided for operation")
            raise ValueError(f"No {obj_type} or project provided")
        if obj is not None and not isinstance(obj, (Project, Observation)):
            logger.error(f"Unsupported object type for {obj_type}: {type(obj)}")
            raise ValueError(f"Unsupported object type: {type(obj)}")

    def _get_super_class_instance(self, operation: str) -> Union[Configurator, Inspector, Calculator]:
        """Retrieve the appropriate super-class instance based on operation"""
        operation_map = {
            "configure": self._configurator,
            "inspect": self._inspector,
            "calculate": self._calculator
        }
        if operation not in operation_map:
            logger.error(f"Unsupported operation: {operation}")
            raise ValueError(f"Unsupported operation: {operation}")
        return operation_map[operation]

    def process_request(self, operation: str, target: str, attributes: Dict[str, Any],
                       obj: Optional[Union[Project, Observation]] = None) -> Dict[str, Any]:
        """Universal method to handle configuration, inspection, or calculation requests.

        Args:
            operation (str): Type of operation ("configure", "inspect", "calculate").
            target (str): Target entity (e.g., "project", "observation", "telescope", "source").
            attributes (Dict[str, Any]): Dictionary with operation-specific parameters.
            obj (Optional[Union[Project, Observation]]): Specific object to operate on (default uses current project).

        Returns:
            Dict[str, Any]: Result of the operation.

        Raises:
            ValueError: If operation or target is unsupported, or validation fails.
        """
        # Validate input
        if not isinstance(attributes, dict):
            logger.error(f"Attributes must be a dictionary, got {type(attributes)}")
            raise ValueError(f"Attributes must be a dictionary, got {type(attributes)}")

        # Determine the target object
        target_obj = obj if obj is not None else self._project
        self._validate_object(target_obj, target)

        # Resolve nested targets (e.g., observation within project)
        if target == "observation" and isinstance(target_obj, Project):
            obs_index = attributes.get("observation_index")
            if obs_index is None or not isinstance(obs_index, int) or not (0 <= obs_index < len(target_obj.get_observations())):
                logger.error(f"Invalid or missing observation_index for project '{target_obj.get_name()}'")
                raise ValueError(f"Invalid observation_index: {obs_index}")
            target_obj = target_obj.get_observation(obs_index)
            attributes = {k: v for k, v in attributes.items() if k != "observation_index"}

        # Map targets to base class types or direct operations
        target_map = {
            "project": Project,
            "observation": Observation,
            "telescope": "telescopes",
            "telescopes": "telescopes",
            "source": "sources",
            "sources": "sources",
            "frequency": "frequencies",
            "frequencies": "frequencies",
            "scan": "scans",
            "scans": "scans"
        }
        
        if target not in target_map:
            logger.error(f"Unsupported target: {target}")
            raise ValueError(f"Unsupported target: {target}")

        super_instance = self._get_super_class_instance(operation)

        # Handle nested configurations/inspections/calculations
        nested_target_map = {
            "telescope": "get_telescopes",
            "source": "get_sources",
            "frequency": "get_frequencies",
            "scan": "get_scans"
        }

        if target in nested_target_map and isinstance(target_obj, Observation):
            index_key = f"{target}_index"
            if index_key in attributes:
                target_obj = getattr(target_obj, nested_target_map[target])()

        # Execute the operation
        operation_map = {
            "configure": {
                "method": lambda: super_instance.configure(target_obj, attributes),
                "log_message": lambda: f"Configured {target} in '{target_obj.get_observation_code() if isinstance(target_obj, Observation) else target_obj.get_name()}'",
                "result": lambda res: {"success": res}
            },
            "inspect": {
                "method": lambda: super_instance.inspect(target_obj, attributes),
                "log_message": lambda: f"Inspected {target} in '{target_obj.get_observation_code() if isinstance(target_obj, Observation) else target_obj.get_name()}'",
                "result": lambda res: res
            },
            "calculate": {
                "method": lambda: super_instance.calculate(target_obj, attributes),
                "log_message": lambda: f"Calculated {attributes.get('type', 'unknown')} for '{target_obj.get_observation_code() if isinstance(target_obj, Observation) else target_obj.get_name()}'",
                "result": lambda res: res,
                "validate": lambda: isinstance(target_obj, (Project, Observation)) or raise_value_error(
                    f"Calculation only supported for Project or Observation, got {type(target_obj)}"
                )
            }
        }

        def raise_value_error(message):
            logger.error(message)
            raise ValueError(message)

        operation_data = operation_map.get(operation)
        if operation_data:
            if "validate" in operation_data:
                operation_data["validate"]()
            result = operation_data["method"]()
            logger.info(operation_data["log_message"]())
            return operation_data["result"](result)

        return {}

    def __repr__(self) -> str:
        """String representation of Manipulator"""
        project_name = self._project.get_name() if self._project else "None"
        return f"Manipulator(project='{project_name}')"


class DefaultManipulator(Manipulator):
    """Default implementation of Manipulator for managing Project and its components"""
    def __init__(self, project: Optional[Project] = None):
        super().__init__(project=project)
        logger.info("Initialized DefaultManipulator")