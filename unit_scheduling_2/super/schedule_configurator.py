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

    Provides methods to configure astronomical scheduling entities with validation and nested configuration support.
    Integrates with Manipulator for method validation.

    Args:
        manipulator: The Manipulator instance for method lookup and validation.

    Returns:
        Dict[str, Any]: A dictionary with results of the configuration operation, managed by Super.execute.

    Examples:
        >>> from unit_scheduling_2.super.manipulator import ScheduleManipulator
        >>> manipulator = ScheduleManipulator()
        >>> configurator = ScheduleConfigurator(manipulator)
        >>> source = Source()
        >>> configurator.execute(source, {"set": {"params": {"name": "3C 286", "ra_h": 13, "ra_m": 31, "ra_s": 8.287}}})
        {"status": True, "object": <Source>, "method": "_configure_source", "result": True}
    """
    def __init__(self, manipulator: 'Manipulator'):
        super().__init__(manipulator=manipulator)
        self._operation = "configure"
        logger.info("Initialized ScheduleConfigurator")

    def _configure_if(self, if_obj: IF, attributes: Dict[str, Any]) -> bool:
        """Configure an IF object."""
        valid_methods = self._get_methods(IF)
        applied = False
        for method_name, method_args in attributes.items():
            result = self._validate_and_apply_method(if_obj, method_name, method_args, valid_methods)
            if result["status"]:
                applied = True
        if not applied:
            logger.warning("No valid methods applied for IF configuration")
            return False
        logger.info(f"Configured IF: frequency={if_obj.frequency}, bandwidth={if_obj.bandwidth}")
        return True

    def _configure_frequencies(self, freq_obj: Frequencies, attributes: Dict[str, Any]) -> bool:
        """Configure a Frequencies object, supporting nested IF configuration."""
        if "name" in attributes:
            result = self._do_nested(
                freq_obj, attributes, "name", lambda k: freq_obj.get(k), self._configure_if
            )
            if result["status"]:
                logger.info(f"Configured nested IF in Frequencies: name={attributes['name']}")
                return result["result"]
            logger.warning(f"Failed to configure nested IF in Frequencies: name={attributes.get('name')}")
            return False
        valid_methods = self._get_methods(Frequencies)
        applied = False
        for method_name, method_args in attributes.items():
            result = self._validate_and_apply_method(freq_obj, method_name, method_args, valid_methods)
            if result["status"]:
                applied = True
        if not applied:
            logger.warning("No valid methods applied for Frequencies configuration")
            return False
        logger.info(f"Configured Frequencies: count={len(freq_obj)}")
        return True

    def _configure_source(self, source_obj: Source, attributes: Dict[str, Any]) -> bool:
        """Configure a Source object."""
        valid_methods = self._get_methods(Source)
        applied = False
        for method_name, method_args in attributes.items():
            result = self._validate_and_apply_method(source_obj, method_name, method_args, valid_methods)
            if result["status"]:
                applied = True
        if not applied:
            logger.warning("No valid methods applied for Source configuration")
            return False
        logger.info(f"Configured Source: name='{source_obj.name}'")
        return True

    def _configure_sources(self, sources_obj: Sources, attributes: Dict[str, Any]) -> bool:
        """Configure a Sources object, supporting nested Source configuration."""
        if "name" in attributes:
            result = self._do_nested(
                sources_obj, attributes, "name", lambda k: sources_obj.get(k), self._configure_source
            )
            if result["status"]:
                logger.info(f"Configured nested Source in Sources: name={attributes['name']}")
                return result["result"]
            logger.warning(f"Failed to configure nested Source in Sources: name={attributes.get('name')}")
            return False
        valid_methods = self._get_methods(Sources)
        applied = False
        for method_name, method_args in attributes.items():
            result = self._validate_and_apply_method(sources_obj, method_name, method_args, valid_methods)
            if result["status"]:
                applied = True
        if not applied:
            logger.warning("No valid methods applied for Sources configuration")
            return False
        logger.info(f"Configured Sources: count={len(sources_obj)}")
        return True

    def _configure_telescope(self, tel_obj: Union[Telescope, SpaceTelescope], attributes: Dict[str, Any]) -> bool:
        """Configure a Telescope or SpaceTelescope object."""
        obj_type = type(tel_obj)
        valid_methods = self._get_methods(obj_type)
        applied = False
        for method_name, method_args in attributes.items():
            result = self._validate_and_apply_method(tel_obj, method_name, method_args, valid_methods)
            if result["status"]:
                applied = True
        if not applied:
            logger.warning(f"No valid methods applied for {obj_type.__name__} configuration")
            return False
        logger.info(f"Configured {obj_type.__name__}: code='{tel_obj.get_code()}'")
        return True

    def _configure_telescopes(self, tel_obj: Telescopes, attributes: Dict[str, Any]) -> bool:
        """Configure a Telescopes object, supporting nested Telescope configuration."""
        if "name" in attributes:
            result = self._do_nested(
                tel_obj, attributes, "name", lambda k: tel_obj.get(k), self._configure_telescope
            )
            if result["status"]:
                logger.info(f"Configured nested Telescope in Telescopes: name={attributes['name']}")
                return result["result"]
            logger.warning(f"Failed to configure nested Telescope in Telescopes: name={attributes.get('name')}")
            return False
        valid_methods = self._get_methods(Telescopes)
        applied = False
        for method_name, method_args in attributes.items():
            result = self._validate_and_apply_method(tel_obj, method_name, method_args, valid_methods)
            if result["status"]:
                applied = True
        if not applied:
            logger.warning("No valid methods applied for Telescopes configuration")
            return False
        logger.info(f"Configured Telescopes: count={len(tel_obj)}")
        return True

    def _configure_scan(self, scan_obj: Scan, attributes: Dict[str, Any]) -> bool:
        """Configure a Scan object, optionally validating with an observation."""
        valid_methods = self._get_methods(Scan)
        applied = False
        observation = attributes.get("observation")
        for method_name, method_args in attributes.items():
            if method_name == "observation":
                continue
            extra_args = {"observation": observation} if observation else None
            result = self._validate_and_apply_method(scan_obj, method_name, method_args, valid_methods, extra_args)
            if result["status"]:
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
        """Configure a Scans object, checking for overlaps in nested Scan changes."""
        if "name" in attributes:
            name = attributes["name"]
            scan_obj = scans_obj.get(name)
            if scan_obj is None:
                logger.error(f"Scan '{name}' not found in Scans")
                return False
            if not isinstance(scan_obj, Scan):
                logger.error(f"Object with name '{name}' is not a Scan, got {type(scan_obj).__name__}")
                return False
            nested_attrs = {k: v for k, v in attributes.items() if k != "name"}
            result = self._configure_scan(scan_obj, nested_attrs)
            if result:
                overlap, reason = scans_obj._check_overlap(scan_obj, exclude_name=name)
                if overlap:
                    logger.error(f"Modified scan '{name}' {reason}")
                    return False
            return result
        valid_methods = self._get_methods(Scans)
        applied = False
        for method_name, method_args in attributes.items():
            result = self._validate_and_apply_method(scans_obj, method_name, method_args, valid_methods)
            if result["status"]:
                applied = True
        if not applied:
            logger.warning("No valid methods applied for Scans configuration")
            return False
        logger.info(f"Configured Scans: count={len(scans_obj)}")
        return True

    def _configure_observation(self, obs_obj: Observation, attributes: Dict[str, Any]) -> bool:
        """Configure an Observation object, validating its state."""
        valid_methods = self._get_methods(Observation)
        applied = False
        for method_name, method_args in attributes.items():
            result = self._validate_and_apply_method(obs_obj, method_name, method_args, valid_methods)
            if result["status"]:
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
        """Configure a ScheduleProject object, supporting nested Observation configuration."""
        if "name" in attributes:
            result = self._do_nested(
                project_obj, attributes, "name", lambda k: project_obj.get_observation(k), self._configure_observation
            )
            if result["status"]:
                logger.info(f"Configured nested Observation in ScheduleProject: name={attributes['name']}")
                return result["result"]
            logger.warning(f"Failed to configure nested Observation in ScheduleProject: name={attributes.get('name')}")
            return False
        valid_methods = self._get_methods(ScheduleProject)
        applied = False
        for method_name, method_args in attributes.items():
            result = self._validate_and_apply_method(project_obj, method_name, method_args, valid_methods)
            if result["status"]:
                applied = True
        if not applied:
            logger.warning("No valid methods applied for ScheduleProject configuration")
            return False
        logger.info(f"Configured ScheduleProject: name='{project_obj.get_name()}', observations={len(project_obj.get_items())}")
        return True