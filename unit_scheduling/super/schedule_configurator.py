# /super/configurator.py
from common.super.super import Super
from unit_scheduling.super.schedule_project import ScheduleProject  
from unit_scheduling.base.frequencies import IF, Frequencies
from unit_scheduling.base.sources import Source, Sources
from unit_scheduling.base.telescopes import Telescope, SpaceTelescope, Telescopes
from unit_scheduling.base.scans import Scan, Scans
from unit_scheduling.base.observation import Observation
from common.utils.logging_setup import logger
from typing import Dict, Any
import inspect

class ScheduleConfigurator(Super):
    """Default implementation of Configurator for configuring Project and its components.

    Inherits configuration methods from Super and provides a universal interface for managing
    astronomical scheduling entities such as observations, telescopes, sources, frequencies, and scans.
    Supports nested configuration via index-based access and validates method applicability through a Manipulator.

    Args:
        obj: The object to configure (e.g., IF, Frequencies, Source, Sources, Telescope, SpaceTelescope, Scan, Observation, ScheduleProject).
        attributes (Dict[str, Any]): Dictionary mapping method names to their arguments.
            Examples:
                - IF: {"set_frequency": {"freq": 1420.0}}
                - Frequencies: {"if_index": 0, "set_frequency": {"freq": 1420.0}}
                - Source: {"set_source": {"name": "3C 286", "ra_h": 13, "ra_m": 31, "ra_s": 8.287, "dec_d": 30, "dec_m": 30, "dec_s": 33.16}}
                - Sources: {"source_index": 0, "set_name": {"name": "New Name"}}
                - Telescope: {"set_coordinates": {"coordinates": (1000.0, 2000.0, 3000.0)}}
                - Telescopes: {"telescope_index": 0, "set_name": {"name": "New Name"}}
                - Scan: {"set_scan": {"start": "2023-01-01T00:00:00", "duration": 300.0}}
                - Scans: {"scan_index": 0, "set_duration": {"duration": 600.0}}
                - Observation: {"set_observation_code": {"code": "OBS001"}}
                - Project: {"observation_index": 0, "set_observation_code": {"code": "OBS001"}}

    Returns:
        bool: True if configuration succeeds, False otherwise.

    Raises:
        ValueError: If the object type is not supported by the configurator.

    Attributes:
        manipulator: The Manipulator instance used to validate and execute methods.

    Examples:
        >>> from unit_scheduling.super.manipulator import ScheduleManipulator
        >>> manipulator = ScheduleManipulator()
        >>> configurator = ScheduleConfigurator(manipulator)
        >>> source = Source()
        >>> configurator.configure(source, {"set_source": {"name": "3C 286", "ra_h": 13, "ra_m": 31, "ra_s": 8.287, "dec_d": 30, "dec_m": 30, "dec_s": 33.16}})
        True
    """
    def __init__(self, manipulator: 'Manipulator'):
        """Initialize the ScheduleConfigurator.

        Args:
            manipulator: The Manipulator instance providing method validation and execution capabilities.

        Notes:
            - Initializes the parent Super class and sets up logging.
        """
        super().__init__(manipulator)
        logger.info("Initialized Scheduling Configurator")
    
    def _default_result(self) -> bool:
        """Return the default result when configuration is not applied.

        Returns:
            bool: False, indicating no configuration was performed.
        """
        return False

    def _configure_if(self, if_obj: IF, attributes: Dict[str, Any]) -> bool:
        """Configure an IF object with specified attributes.

        Args:
            if_obj (IF): The IF object to configure.
            attributes (Dict[str, Any]): Dictionary of method names and their arguments (e.g., {"set_frequency": {"freq": 1420.0}}).

        Returns:
            bool: True if at least one valid method was applied, False otherwise.

        Notes:
            - Uses Manipulator to validate applicable methods.
            - Logs success with frequency and bandwidth details.
        """
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
        """Configure a Frequencies object, including nested IF configuration.

        Args:
            freq_obj (Frequencies): The Frequencies object to configure.
            attributes (Dict[str, Any]): Dictionary of method names and arguments, optionally including "if_index" for nested configuration.

        Returns:
            bool: True if configuration succeeds, False otherwise.

        Notes:
            - Supports nested IF configuration via "if_index".
            - Logs the number of IFs configured.
        """
        result = self._do_nested(freq_obj, attributes, "if_index", freq_obj.get_by_index, self._configure_if)
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
        """Configure a Source object with specified attributes.

        Args:
            source_obj (Source): The Source object to configure.
            attributes (Dict[str, Any]): Dictionary of method names and arguments (e.g., {"set_source": {"name": "3C 286", ...}}).

        Returns:
            bool: True if at least one valid method was applied, False otherwise.

        Notes:
            - Logs the source name upon successful configuration.
        """
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
        """Configure a Sources object, including nested Source configuration.

        Args:
            sources_obj (Sources): The Sources object to configure.
            attributes (Dict[str, Any]): Dictionary of method names and arguments, optionally including "source_index".

        Returns:
            bool: True if configuration succeeds, False otherwise.

        Notes:
            - Supports nested Source configuration via "source_index".
            - Logs the total number of sources.
        """
        result = self._do_nested(sources_obj, attributes, "source_index", sources_obj.get_by_index, self._configure_source)
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
        """Configure a Telescope or SpaceTelescope object.

        Args:
            tel_obj (Telescope | SpaceTelescope): The telescope object to configure.
            attributes (Dict[str, Any]): Dictionary of method names and arguments (e.g., {"set_coordinates": {"coordinates": (1000.0, 2000.0, 3000.0)}}).

        Returns:
            bool: True if at least one valid method was applied, False otherwise.

        Notes:
            - Handles both Telescope and SpaceTelescope types dynamically.
            - Logs the telescope code upon success.
        """
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
        """Configure a SpaceTelescope object.

        Args:
            tel_obj (SpaceTelescope): The SpaceTelescope object to configure.
            attributes (Dict[str, Any]): Dictionary of method names and arguments.

        Returns:
            bool: True if at least one valid method was applied, False otherwise.

        Notes:
            - Specific to SpaceTelescope; logs the telescope code upon success.
        """
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
        """Configure a Telescopes object, including nested Telescope configuration.

        Args:
            tel_obj (Telescopes): The Telescopes object to configure.
            attributes (Dict[str, Any]): Dictionary of method names and arguments, optionally including "telescope_index".

        Returns:
            bool: True if configuration succeeds, False otherwise.

        Notes:
            - Supports nested Telescope configuration via "telescope_index".
            - Logs the total number of telescopes.
        """
        result = self._do_nested(tel_obj, attributes, "telescope_index", tel_obj.get_by_index, self._configure_telescope)
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
        """Configure a Scan object, optionally validating with an observation.

        Args:
            scan_obj (Scan): The Scan object to configure.
            attributes (Dict[str, Any]): Dictionary of method names and arguments, optionally including "observation".

        Returns:
            bool: True if configuration succeeds and scan is valid, False otherwise.

        Notes:
            - Validates scan against observation if provided.
            - Logs start time and source details.
        """
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
        """Configure a Scans object, checking for overlaps in nested Scan changes.

        Args:
            scans_obj (Scans): The Scans object to configure.
            attributes (Dict[str, Any]): Dictionary of method names and arguments, optionally including "scan_index".

        Returns:
            bool: True if configuration succeeds without overlaps, False otherwise.

        Notes:
            - Checks for scan overlaps when modifying nested scans.
            - Logs the total number of scans.
        """
        nested_result = self._do_nested(scans_obj, attributes, "scan_index", scans_obj.get_by_index, self._configure_scan)
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
        """Configure an Observation object, validating its state afterward.

        Args:
            obs_obj (Observation): The Observation object to configure.
            attributes (Dict[str, Any]): Dictionary of method names and arguments.

        Returns:
            bool: True if configuration succeeds and observation is valid, False otherwise.

        Notes:
            - Performs validation post-configuration.
            - Logs the observation code upon success.
        """
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

    def _configure_project(self, project_obj: ScheduleProject, attributes: Dict[str, Any]) -> bool:
        """Configure a Project object, including nested Observation configuration.

        Args:
            project_obj (ScheduleProject): The Project object to configure.
            attributes (Dict[str, Any]): Dictionary of method names and arguments, optionally including "observation_index".

        Returns:
            bool: True if configuration succeeds, False otherwise.

        Notes:
            - Supports nested Observation configuration via "observation_index".
            - Logs project name and observation count.
        """
        result = self._do_nested(project_obj, attributes, "observation_index", project_obj.get_by_index, self._configure_observation)
        if result:
            return result
        
        valid_methods = self._manipulator.get_methods_for_type(ScheduleProject)
        logger.debug(f"Valid methods for ScheduleProject: {list(valid_methods.keys())}")
        
        applied = False
        method_name = attributes.get("method")
        method_args = attributes.get("attributes", {})
        
        if method_name:
            if method_name in valid_methods:
                if self._validate_and_apply_method(project_obj, method_name, method_args, valid_methods):
                    applied = True
            else:
                logger.warning(f"Method {method_name} not found in valid methods for ScheduleProject")
        
        if not applied:
            logger.warning("No valid methods provided for Project configuration")
            return False
        logger.info(f"Successfully configured Project: name='{project_obj.get_name()}', observations_count={len(project_obj.get_items())}")
        return True