from common.super.super import Super
from unit_scheduling_2.super.schedule_project import ScheduleProject
from unit_scheduling_2.base.frequencies import IF, Frequencies
from unit_scheduling_2.base.sources import Source, Sources
from unit_scheduling_2.base.telescopes import Telescope, SpaceTelescope, Telescopes
from unit_scheduling_2.base.scans import Scan, Scans
from unit_scheduling_2.base.observation import Observation
from common.utils.logging_setup import logger
from typing import Dict, Any, Union

class ScheduleConfigurator(Super):
    """Implementation of Configurator for configuring scheduling entities using the Super framework.

    Provides methods to configure astronomical scheduling entities (IF, Frequencies, Source, Sources,
    Telescope, SpaceTelescope, Telescopes, Scan, Scans, Observation, ScheduleProject) with validation
    and nested configuration support. Integrates with Manipulator for method validation.

    Args:
        manipulator: The Manipulator instance for method lookup and validation.

    Returns:
        bool: True if configuration succeeds, False otherwise.

    Examples:
        >>> from unit_scheduling_2.super.manipulator import ScheduleManipulator
        >>> manipulator = ScheduleManipulator()
        >>> configurator = ScheduleConfigurator(manipulator)
        >>> source = Source()
        >>> configurator.execute(source, {"set": {"name": "3C 286", "ra_h": 13, "ra_m": 31, "ra_s": 8.287}})
        True
    """
    def __init__(self, manipulator: 'Manipulator'):
        super().__init__(manipulator=manipulator)
        self._operation = "configure"  # Set operation name for Super framework
        logger.info("Initialized ScheduleConfigurator")

    def _default_result(self) -> bool:
        """Return default result for failed configurations."""
        return False

    def _configure_if(self, if_obj: IF, attributes: Dict[str, Any]) -> bool:
        """Configure an IF object.

        Args:
            if_obj (IF): The IF object to configure.
            attributes (Dict[str, Any]): Dictionary of method names and arguments (e.g., {"set": {"frequency": 1420.0}}).

        Returns:
            bool: True if configuration is successful, False otherwise.
        """
        valid_methods = self._get_methods(IF)
        applied = False
        for method_name, method_args in attributes.items():
            if self._validate_and_apply_method(if_obj, method_name, method_args, valid_methods):
                applied = True
        if not applied:
            logger.warning("No valid methods applied for IF configuration")
            return False
        logger.info(f"Configured IF: frequency={if_obj.frequency}, bandwidth={if_obj.bandwidth}")
        return True

    def _configure_frequencies(self, freq_obj: Frequencies, attributes: Dict[str, Any]) -> bool:
        """Configure a Frequencies object, supporting nested IF configuration.

        Args:
            freq_obj (Frequencies): The Frequencies object to configure.
            attributes (Dict[str, Any]): Dictionary with optional "if_name" for nested configuration.

        Returns:
            bool: True if configuration is successful, False otherwise.
        """
        if "if_name" in attributes:
            if_name = attributes["if_name"]
            if_obj = freq_obj.get(if_name)
            if if_obj:
                result = self._configure_if(if_obj, attributes)
                if result:
                    return True
                logger.warning(f"Failed to configure IF '{if_name}'")
                return False
            logger.warning(f"IF '{if_name}' not found in Frequencies")
            return False
        valid_methods = self._get_methods(Frequencies)
        applied = False
        for method_name, method_args in attributes.items():
            if self._validate_and_apply_method(freq_obj, method_name, method_args, valid_methods):
                applied = True
        if not applied:
            logger.warning("No valid methods applied for Frequencies configuration")
            return False
        logger.info(f"Configured Frequencies: count={len(freq_obj)}")
        return True

    def _configure_source(self, source_obj: Source, attributes: Dict[str, Any]) -> bool:
        """Configure a Source object.

        Args:
            source_obj (Source): The Source object to configure.
            attributes (Dict[str, Any]): Dictionary of method names and arguments (e.g., {"set": {...}}).

        Returns:
            bool: True if configuration is successful, False otherwise.
        """
        valid_methods = self._get_methods(Source)
        applied = False
        for method_name, method_args in attributes.items():
            if method_name == "set_source":
                # Handle set_source specifically to map to individual setters
                params = {}
                if "name" in method_args:
                    params["name"] = method_args["name"]
                for key in ["ra_h", "ra_m", "ra_s", "de_d", "de_m", "de_s"]:
                    if key in method_args:
                        params[key] = method_args[key]
                if "name_J2000" in method_args:
                    params["name_J2000"] = method_args["name_J2000"]
                if "alt_name" in method_args:
                    params["alt_name"] = method_args["alt_name"]
                source_obj.set(params)
                applied = True
            elif self._validate_and_apply_method(source_obj, method_name, method_args, valid_methods):
                applied = True
        if not applied:
            logger.warning("No valid methods applied for Source configuration")
            return False
        logger.info(f"Configured Source: name='{source_obj.name}'")
        return True

    def _configure_sources(self, sources_obj: Sources, attributes: Dict[str, Any]) -> bool:
        """Configure a Sources object, supporting nested Source configuration.

        Args:
            sources_obj (Sources): The Sources object to configure.
            attributes (Dict[str, Any]): Dictionary with optional "source_name" for nested configuration.

        Returns:
            bool: True if configuration is successful, False otherwise.
        """
        if "source_name" in attributes:
            source_name = attributes["source_name"]
            source_obj = sources_obj.get(source_name)
            if source_obj:
                result = self._configure_source(source_obj, attributes)
                if result:
                    return True
                logger.warning(f"Failed to configure Source '{source_name}'")
                return False
            logger.warning(f"Source '{source_name}' not found in Sources")
            return False
        valid_methods = self._get_methods(Sources)
        applied = False
        for method_name, method_args in attributes.items():
            if self._validate_and_apply_method(sources_obj, method_name, method_args, valid_methods):
                applied = True
        if not applied:
            logger.warning("No valid methods applied for Sources configuration")
            return False
        logger.info(f"Configured Sources: count={len(sources_obj)}")
        return True

    def _configure_telescope(self, tel_obj: Union[Telescope, SpaceTelescope], attributes: Dict[str, Any]) -> bool:
        """Configure a Telescope or SpaceTelescope object.

        Args:
            tel_obj (Telescope | SpaceTelescope): The telescope object to configure.
            attributes (Dict[str, Any]): Dictionary of method names and arguments.

        Returns:
            bool: True if configuration is successful, False otherwise.
        """
        obj_type = type(tel_obj)
        valid_methods = self._get_methods(obj_type)
        applied = False
        for method_name, method_args in attributes.items():
            if self._validate_and_apply_method(tel_obj, method_name, method_args, valid_methods):
                applied = True
        if not applied:
            logger.warning(f"No valid methods applied for {obj_type.__name__} configuration")
            return False
        logger.info(f"Configured {obj_type.__name__}: code='{tel_obj.get_code()}'")
        return True

    def _configure_telescopes(self, tel_obj: Telescopes, attributes: Dict[str, Any]) -> bool:
        """Configure a Telescopes object, supporting nested Telescope configuration.

        Args:
            tel_obj (Telescopes): The Telescopes object to configure.
            attributes (Dict[str, Any]): Dictionary with optional "telescope_code" for nested configuration.

        Returns:
            bool: True if configuration is successful, False otherwise.
        """
        if "telescope_code" in attributes:
            telescope_code = attributes["telescope_code"]
            telescope_obj = tel_obj.get(telescope_code)
            if telescope_obj:
                result = self._configure_telescope(telescope_obj, attributes)
                if result:
                    return True
                logger.warning(f"Failed to configure Telescope '{telescope_code}'")
                return False
            logger.warning(f"Telescope '{telescope_code}' not found in Telescopes")
            return False
        valid_methods = self._get_methods(Telescopes)
        applied = False
        for method_name, method_args in attributes.items():
            if self._validate_and_apply_method(tel_obj, method_name, method_args, valid_methods):
                applied = True
        if not applied:
            logger.warning("No valid methods applied for Telescopes configuration")
            return False
        logger.info(f"Configured Telescopes: count={len(tel_obj)}")
        return True

    def _configure_scan(self, scan_obj: Scan, attributes: Dict[str, Any]) -> bool:
        """Configure a Scan object, optionally validating with an observation.

        Args:
            scan_obj (Scan): The Scan object to configure.
            attributes (Dict[str, Any]): Dictionary of method names and arguments, optionally including "observation".

        Returns:
            bool: True if configuration is successful, False otherwise.
        """
        valid_methods = self._get_methods(Scan)
        applied = False
        observation = attributes.get("observation")
        for method_name, method_args in attributes.items():
            if method_name == "observation":
                continue
            if self._validate_and_apply_method(
                scan_obj,
                method_name,
                method_args,
                valid_methods,
                {"observation": observation} if observation else None
            ):
                applied = True
                if observation and not scan_obj.validate_with_observation(observation):
                    logger.error(f"Scan invalid after {method_name}: observation='{observation.get_observation_code()}'")
                    return False
        if not applied:
            logger.warning("No valid methods applied for Scan configuration")
            return False
        source_str = "OFF SOURCE" if scan_obj.is_off_source else f"source_name={scan_obj.get_source_name()}"
        logger.info(f"Configured Scan: start={scan_obj.get_start().isot}, {source_str}")
        return True

    def _configure_scans(self, scans_obj: Scans, attributes: Dict[str, Any]) -> bool:
        """Configure a Scans object, checking for overlaps in nested Scan changes.

        Args:
            scans_obj (Scans): The Scans object to configure.
            attributes (Dict[str, Any]): Dictionary with optional "scan_name" for nested configuration.

        Returns:
            bool: True if configuration is successful, False otherwise.
        """
        if "scan_name" in attributes:
            scan_name = attributes["scan_name"]
            scan_obj = scans_obj.get(scan_name)
            if scan_obj:
                result = self._configure_scan(scan_obj, attributes)
                if result:
                    overlap, reason = scans_obj._check_overlap(scan_obj, exclude_name=scan_name)
                    if overlap:
                        logger.error(f"Modified scan '{scan_name}' {reason}")
                        return False
                    return True
                logger.warning(f"Failed to configure Scan '{scan_name}'")
                return False
            logger.warning(f"Scan '{scan_name}' not found in Scans")
            return False
        valid_methods = self._get_methods(Scans)
        applied = False
        for method_name, method_args in attributes.items():
            if self._validate_and_apply_method(scans_obj, method_name, method_args, valid_methods):
                applied = True
        if not applied:
            logger.warning("No valid methods applied for Scans configuration")
            return False
        logger.info(f"Configured Scans: count={len(scans_obj)}")
        return True

    def _configure_observation(self, obs_obj: Observation, attributes: Dict[str, Any]) -> bool:
        """Configure an Observation object, validating its state.

        Args:
            obs_obj (Observation): The Observation object to configure.
            attributes (Dict[str, Any]): Dictionary of method names and arguments.

        Returns:
            bool: True if configuration is successful and valid, False otherwise.
        """
        valid_methods = self._get_methods(Observation)
        applied = False
        for method_name, method_args in attributes.items():
            if self._validate_and_apply_method(obs_obj, method_name, method_args, valid_methods):
                applied = True
        if not applied:
            logger.warning("No valid methods applied for Observation configuration")
            return False
        if not obs_obj.validate():
            logger.error(f"Observation '{obs_obj.get_observation_code()}' invalid after configuration")
            return False
        logger.info(f"Configured Observation: code='{obs_obj.get_observation_code()}'")
        return True

    def _configure_project(self, project_obj: ScheduleProject, attributes: Dict[str, Any]) -> bool:
        """Configure a ScheduleProject object, supporting nested Observation configuration.

        Args:
            project_obj (ScheduleProject): The ScheduleProject object to configure.
            attributes (Dict[str, Any]): Dictionary with optional "observation_code" for nested configuration.

        Returns:
            bool: True if configuration is successful, False otherwise.
        """
        if "observation_code" in attributes:
            observation_code = attributes["observation_code"]
            observation_obj = project_obj.get_observation(observation_code)
            if observation_obj:
                result = self._configure_observation(observation_obj, attributes)
                if result:
                    return True
                logger.warning(f"Failed to configure Observation '{observation_code}'")
                return False
            logger.warning(f"Observation '{observation_code}' not found in ScheduleProject")
            return False
        valid_methods = self._get_methods(ScheduleProject)
        applied = False
        for method_name, method_args in attributes.items():
            if self._validate_and_apply_method(project_obj, method_name, method_args, valid_methods):
                applied = True
        if not applied:
            logger.warning("No valid methods applied for ScheduleProject configuration")
            return False
        logger.info(f"Configured ScheduleProject: name='{project_obj.get_name()}', observations={len(project_obj.get_items())}")
        return True