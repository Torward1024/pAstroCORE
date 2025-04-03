# /super/configurator.py
from abc import ABC
from base.frequencies import IF, Frequencies
from base.sources import Source, Sources
from base.telescopes import Telescope, SpaceTelescope, Telescopes
from base.scans import Scan, Scans
from base.observation import Observation
from base.project import Project 
from utils.logging_setup import logger
from typing import Dict, Any, Callable, Type, Optional
import inspect

class Configurator(ABC):
    """Super-class for configuring Project and its components.

    Attributes:
        _config_methods (dict): Cached dictionary mapping object types to configuration functions and methods.

    Methods:
        configure: Universal method to configure objects using method calls in attributes dictionary.
        _get_config_methods: Cached method to retrieve configuration method mappings.
    """
    def __init__(self, manipulator: 'Manipulator'= None, methods: Optional[Dict[Type, Dict[str, Callable]]] = None):
        """Initialize the Configurator"""
        self._manipulator = manipulator
        self._methods = methods

    def _get_methods(self, obj_type: Type) -> Dict[str, Callable]:
        if self._methods and obj_type in self._methods:
            return self._methods[obj_type]
        if self._manipulator:
            return self._manipulator.get_methods_for_type(obj_type)
        raise ValueError(f"No methods provided for {obj_type.__name__}")

    def _validate_and_apply_method(self, obj: Any, method_name: str, method_args: Any, valid_methods: Dict[str, Callable], 
                                  extra_args: Dict[str, Any] = None) -> bool:
        """Validate and apply a method to an object

        Args:
            obj: The object to apply the method to
            method_name: Name of the method to call
            method_args: Arguments for the method
            valid_methods: Dictionary of valid methods for the object's type
            extra_args: Optional additional arguments to pass to the method (e.g., observation for Scan)

        Returns:
            bool: True if the method was applied successfully, False otherwise
        """
        if method_name not in valid_methods:
            logger.error(f"Invalid method {method_name} for {type(obj).__name__} object")
            return False
        if not isinstance(method_args, dict):
            logger.error(f"Arguments for {method_name} must be a dictionary, got {type(method_args)}")
            return False

        method = valid_methods[method_name]
        sig = inspect.signature(method)
        expected_params = set(sig.parameters.keys()) - {"self"}
        provided_params = set(method_args.keys())

        if not provided_params.issubset(expected_params):
            logger.error(f"Invalid arguments for {method_name}: expected {expected_params}, got {provided_params}")
            return False

        try:
            if extra_args:
                method_args = {**method_args, **extra_args}
            method(obj, **method_args)
            return True
        except Exception as e:
            logger.error(f"Failed to apply {method_name} to {type(obj).__name__}: {str(e)}")
            return False
    
    def _configure_nested(self, obj: Any, attributes: Dict[str, Any], index_key: str, getter_method: Callable,
                         nested_configurator: Callable) -> bool:
        index = attributes.get(index_key)
        if index is not None:
            if not isinstance(index, int) or not 0 <= index < len(obj):
                logger.error(f"Invalid {index_key} {index} for {type(obj).__name__}")
                return False
            nested_obj = getter_method(index)
            nested_attrs = {k: v for k, v in attributes.items() if k != index_key}
            return nested_configurator(nested_obj, nested_attrs)
        return False
    
    def register_method(self, obj_type: Type, method_name: str, method: Callable) -> None:
        if self._methods is None:
            self._methods = {}
        if obj_type not in self._methods:
            self._methods[obj_type] = {}
        self._methods[obj_type][method_name] = method

    def execute(self, obj: Any, attributes: Dict[str, Any]) -> bool:    
        if obj is None:
            logger.error("Configuration object cannot be None")
            raise ValueError("Configuration object cannot be None")

        obj_type = type(obj)
        config_methods = self._manipulator.get_methods_for_type(type(self))
        config_method_name = f"_configure_{obj_type.__name__.lower()}"

        if config_method_name not in config_methods:
            logger.error(f"No configuration method found for {obj_type.__name__}")
            raise ValueError(f"No configuration method for {obj_type.__name__}")

        try:
            return config_methods[config_method_name](obj, attributes)
        except Exception as e:
            logger.error(f"Failed to configure {obj_type}: {str(e)}")
            return False

    def __repr__(self) -> str:
        """String representation of Configurator"""
        return "Configurator()"

class DefaultConfigurator(Configurator):
    """Default implementation of Configurator for configuring Project and its components

    Inherits all configuration methods from Configurator and provides a ready-to-use instance
    for managing observations, telescopes, sources, frequencies, and scans

    Universal method to configure an object using method calls in a single attributes dictionary

        Args:
            obj: The object to configure (e.g., IF, Frequencies, Source, Sources, Telescope, SpaceTelescope, Scan, Observation, etc.)
            attributes: Dictionary where keys are method names and values are their arguments
                    Example: {"set_frequency": {"freq": 1420.0}}
                    For nested config: {"if_index": 0, "set_frequency": {"freq": 1420.0}}
                    For Source: {"set_source": {"name": "3C 286", "ra_h": 13, "ra_m": 31, ...}}
                    For Sources: {"source_index": 0, "set_name": {"name": "New Name"}}
                    For Telescope: {"set_coordinates": {"coordinates": (1000.0, 2000.0, 3000.0)}}
                    For Telescopes: {"telescope_index": 0, "set_name": {"name": "New Name"}}
                    For Scan: {"set_scan": {"start": Time object or ISO string (e.g., "2023-01-01T00:00:00") or Unix timestamp, "duration": 300.0}}
                    For Scans: {"scan_index": 0, "set_duration": {"duration": 600.0}}

        Returns:
            bool: True if configuration succeeds, False otherwise

        Raises:
            ValueError: If the object type is not supported
    """
    def __init__(self, manipulator: 'Manipulator'):
        super().__init__(manipulator)
        logger.info("Initialized DefaultConfigurator")

    def _configure_if(self, if_obj: IF, attributes: Dict[str, Any]) -> bool:
        """Configure an IF object"""
        valid_methods = self._manipulator.get_methods_for_type(IF)
        applied = False
        for method_name, method_args in attributes.items():
            if self._validate_and_apply_method(if_obj, method_name, method_args, valid_methods):
                applied = True
        if not applied:
            logger.warning("No valid methods provided for IF configuration")
            return False
        logger.info(f"Successfully configured IF: freq={if_obj.get_frequency()}, bw={if_obj.get_bandwidth()}")
        return True

    def _configure_frequencies(self, freq_obj: Frequencies, attributes: Dict[str, Any]) -> bool:
        """Configure a Frequencies object"""
        result = self._configure_nested(freq_obj, attributes, "if_index", freq_obj.get_by_index, self._configure_if)
        if result:
            return result
        valid_methods = self._manipulator.get_methods_for_type(Frequencies)
        applied = False
        for method_name, method_args in attributes.items():
            if self._validate_and_apply_method(freq_obj, method_name, method_args, valid_methods):
                applied = True
        if not applied:
            logger.warning("No valid methods provided for Frequencies configuration")
            return False
        logger.info(f"Successfully configured Frequencies: count={len(freq_obj)}")
        return True

    def _configure_source(self, source_obj: Source, attributes: Dict[str, Any]) -> bool:
        """Configure a Source object"""
        valid_methods = self._manipulator.get_methods_for_type(Source)
        applied = False
        for method_name, method_args in attributes.items():
            if self._validate_and_apply_method(source_obj, method_name, method_args, valid_methods):
                applied = True
        if not applied:
            logger.warning("No valid methods provided for Source configuration")
            return False
        logger.info(f"Successfully configured Source: name='{source_obj.get_name()}'")
        return True

    def _configure_sources(self, sources_obj: Sources, attributes: Dict[str, Any]) -> bool:
        """Configure a Sources object."""
        result = self._configure_nested(sources_obj, attributes, "source_index", sources_obj.get_by_index, self._configure_source)
        if result:
            return result
        valid_methods = self._manipulator.get_methods_for_type(Sources)
        applied = False
        for method_name, method_args in attributes.items():
            if self._validate_and_apply_method(sources_obj, method_name, method_args, valid_methods):
                applied = True
        if not applied:
            logger.warning("No valid methods provided for Sources configuration")
            return False
        logger.info(f"Successfully configured Sources: count={len(sources_obj)}")
        return True

    def _configure_telescope(self, tel_obj: Telescope | SpaceTelescope, attributes: Dict[str, Any]) -> bool:
        """Configure a Telescope or SpaceTelescope object"""
        obj_type = type(tel_obj)
        valid_methods = self._manipulator.get_methods_for_type(obj_type)
        applied = False
        for method_name, method_args in attributes.items():
            if self._validate_and_apply_method(tel_obj, method_name, method_args, valid_methods):
                applied = True
        if not applied:
            logger.warning(f"No valid methods provided for {obj_type.__name__} configuration")
            return False
        logger.info(f"Successfully configured {obj_type.__name__}: code='{tel_obj.get_code()}'")
        return True
    
    def _configure_spacetelescope(self, tel_obj: SpaceTelescope, attributes: Dict[str, Any]) -> bool:
        """Configure a SpaceTelescope object"""
        valid_methods = self._manipulator.get_methods_for_type(SpaceTelescope)
        applied = False
        for method_name, method_args in attributes.items():
            if self._validate_and_apply_method(tel_obj, method_name, method_args, valid_methods):
                applied = True
        if not applied:
            logger.warning("No valid methods provided for SpaceTelescope configuration")
            return False
        logger.info(f"Successfully configured SpaceTelescope: code='{tel_obj.get_code()}'")
        return True

    def _configure_telescopes(self, tel_obj: Telescopes, attributes: Dict[str, Any]) -> bool:
        """Configure a Telescopes object"""
        result = self._configure_nested(tel_obj, attributes, "telescope_index", tel_obj.get_by_index, self._configure_telescope)
        if result:
            return result
        valid_methods = self._manipulator.get_methods_for_type(Telescopes)
        applied = False
        for method_name, method_args in attributes.items():
            if self._validate_and_apply_method(tel_obj, method_name, method_args, valid_methods):
                applied = True
        if not applied:
            logger.warning("No valid methods provided for Telescopes configuration")
            return False
        logger.info(f"Successfully configured Telescopes: count={len(tel_obj)}")
        return True

    def _configure_scan(self, scan_obj: Scan, attributes: Dict[str, Any]) -> bool:
        """Configure a Scan object, validating with observation if provided"""
        valid_methods = self._manipulator.get_methods_for_type(Scan)
        applied = False
        observation = attributes.get("observation")
        for method_name, method_args in attributes.items():
            if method_name == "observation":
                continue
            extra_args = {"observation": observation} if observation and "observation" in inspect.signature(valid_methods[method_name]).parameters else {}
            if self._validate_and_apply_method(scan_obj, method_name, method_args, valid_methods, extra_args):
                applied = True
                if observation and not scan_obj.validate_with_observation(observation):
                    logger.error(f"Scan became invalid after {method_name} with observation '{observation.get_observation_code()}'")
                    return False
        if not applied:
            logger.warning("No valid methods provided for Scan configuration")
            return False
        source_str = "OFF SOURCE" if scan_obj.is_off_source else f"source_index={scan_obj.get_source_index()}"
        logger.info(f"Successfully configured Scan: start={scan_obj.get_start()}, {source_str}")
        return True

    def _configure_scans(self, scans_obj: Scans, attributes: Dict[str, Any]) -> bool:
        """Configure a Scans object, checking overlaps for nested Scan changes"""
        nested_result = self._configure_nested(scans_obj, attributes, "scan_index", scans_obj.get_by_index, self._configure_scan)
        if nested_result:
            overlap, reason = scans_obj._check_overlap(scans_obj.get_by_index(attributes["scan_index"]), exclude_index=attributes["scan_index"])
            if overlap:
                logger.error(f"Modified scan at index {attributes['scan_index']} {reason}")
                return False
            return True
        valid_methods = self._manipulator.get_methods_for_type(Scans)
        applied = False
        for method_name, method_args in attributes.items():
            if self._validate_and_apply_method(scans_obj, method_name, method_args, valid_methods):
                applied = True
        if not applied:
            logger.warning("No valid methods provided for Scans configuration")
            return False
        logger.info(f"Successfully configured Scans: count={len(scans_obj)}")
        return True

    def _configure_observation(self, obs_obj: Observation, attributes: Dict[str, Any]) -> bool:
        """Configure an Observation object, validating its state afterward"""
        valid_methods = self._manipulator.get_methods_for_type(Observation)
        applied = False
        for method_name, method_args in attributes.items():
            if self._validate_and_apply_method(obs_obj, method_name, method_args, valid_methods):
                applied = True
        if not applied:
            logger.warning("No valid methods provided for Observation configuration")
            return False
        if not obs_obj.validate():
            logger.error(f"Observation '{obs_obj.get_observation_code()}' is invalid after configuration")
            return False
        logger.info(f"Successfully configured Observation: code='{obs_obj.get_observation_code()}'")
        return True

    def _configure_project(self, project_obj: Project, attributes: Dict[str, Any]) -> bool:
        """Configure a Project object, including nested Observation configuration by index"""
        result = self._configure_nested(project_obj, attributes, "observation_index", project_obj.get_by_index, self._configure_observation)
        if result:
            return result
        valid_methods = self._manipulator.get_methods_for_type(Project)
        applied = False
        for method_name, method_args in attributes.items():
            if self._validate_and_apply_method(project_obj, method_name, method_args, valid_methods):
                applied = True
        if not applied:
            logger.warning("No valid methods provided for Project configuration")
            return False
        logger.info(f"Successfully configured Project: name='{project_obj.get_name()}', observations_count={len(project_obj.get_observations())}")
        return True