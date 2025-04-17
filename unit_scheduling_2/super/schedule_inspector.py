# /super/schedule_inspector.py
from common.super.super import Super
from unit_scheduling_2.super.schedule_project import ScheduleProject
from unit_scheduling_2.base.frequencies import IF, Frequencies
from unit_scheduling_2.base.sources import Source, Sources
from unit_scheduling_2.base.telescopes import Telescope, SpaceTelescope, Telescopes
from unit_scheduling_2.base.scans import Scan, Scans
from unit_scheduling_2.base.observation import Observation
from common.utils.logging_setup import logger
from typing import Dict, Any, Union

class ScheduleInspector(Super):
    """Implementation of Inspector for inspecting scheduling entities using the Super framework.

    Provides methods to inspect astronomical scheduling entities (IF, Frequencies, Source, Sources,
    Telescope, SpaceTelescope, Telescopes, Scan, Scans, Observation, ScheduleProject) by invoking
    their getter methods and returning results in a dictionary. Supports nested inspection via name-based
    access and validates method applicability through a Manipulator.

    Args:
        manipulator: The Manipulator instance for method lookup and validation.

    Returns:
        Dict[str, Any]: Dictionary containing getter method results.

    Examples:
        >>> from unit_scheduling_2.super.manipulator import ScheduleManipulator
        >>> manipulator = ScheduleManipulator()
        >>> inspector = ScheduleInspector(manipulator)
        >>> source = Source(name="3C 286")
        >>> result = inspector.execute(source, {"get_name": None})
        {'get_name': '3C 286'}
        >>> project = ScheduleProject()
        >>> project.create_item(item_code="OBS001")
        >>> result = inspector.execute(project, {"name": "OBS001", "get_observation_code": None})
        {'get_observation_code': 'OBS001'}
    """
    def __init__(self, manipulator: 'Manipulator'):
        """Initialize the ScheduleInspector.

        Args:
            manipulator: The Manipulator instance providing method validation and execution capabilities.
        """
        super().__init__(manipulator=manipulator)
        self._operation = "inspect"  # Set operation name for Super framework
        logger.info("Initialized ScheduleInspector")

    def _default_result(self) -> Dict[str, Any]:
        """Return default result for failed inspections."""
        return {}

    def _inspect_if(self, if_obj: IF, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect an IF object by calling specified getter methods.

        Args:
            if_obj (IF): The IF object to inspect.
            attributes (Dict[str, Any]): Dictionary of getter method names and arguments.

        Returns:
            Dict[str, Any]: Dictionary mapping getter names to their results.
        """
        valid_getters = self._get_methods(IF)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(if_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters applied for IF inspection")
            return {}
        logger.info(f"Inspected IF: frequency={if_obj.get_frequency()} MHz")
        return result

    def _inspect_frequencies(self, freq_obj: Frequencies, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Frequencies object, supporting nested IF inspection.

        Args:
            freq_obj (Frequencies): The Frequencies object to inspect.
            attributes (Dict[str, Any]): Dictionary with optional "name" for nested inspection.

        Returns:
            Dict[str, Any]: Dictionary with getter results.
        """
        if "name" in attributes:
            name = attributes["name"]
            try:
                if_obj = freq_obj.get(name)
            except KeyError:
                logger.error(f"IF '{name}' not found in Frequencies")
                return {}
            if if_obj:
                nested_attrs = {k: v for k, v in attributes.items() if k != "name"}
                result = self._inspect_if(if_obj, nested_attrs)
                if result:
                    return result
                logger.warning(f"Failed to inspect IF '{name}'")
                return {}
            logger.warning(f"IF '{name}' not found in Frequencies")
            return {}
        valid_getters = self._get_methods(Frequencies)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(freq_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters applied for Frequencies inspection")
            return {}
        logger.info(f"Inspected Frequencies: count={len(freq_obj)}")
        return result

    def _inspect_source(self, source_obj: Source, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Source object by calling specified getter methods.

        Args:
            source_obj (Source): The Source object to inspect.
            attributes (Dict[str, Any]): Dictionary of getter names and arguments.

        Returns:
            Dict[str, Any]: Dictionary with getter results.
        """
        valid_getters = self._get_methods(Source)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(source_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters applied for Source inspection")
            return {}
        logger.info(f"Inspected Source: name='{source_obj.get_name()}'")
        return result

    def _inspect_sources(self, sources_obj: Sources, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Sources object, supporting nested Source inspection.

        Args:
            sources_obj (Sources): The Sources object to inspect.
            attributes (Dict[str, Any]): Dictionary with optional "name" for nested inspection.

        Returns:
            Dict[str, Any]: Dictionary with getter results.
        """
        if "name" in attributes:
            source_name = attributes["name"]
            source_obj = sources_obj.get(source_name)
            if source_obj is None:
                logger.error(f"Source '{source_name}' not found in Sources")
                return {}
            if not isinstance(source_obj, Source):
                logger.error(f"Object with name '{source_name}' is not a Source, got {type(source_obj).__name__}")
                return {}
            nested_attrs = {k: v for k, v in attributes.items() if k != "name"}
            result = self._inspect_source(source_obj, nested_attrs)
            if result:
                return result
            logger.warning(f"Failed to inspect Source '{source_name}'")
            return {}
        valid_getters = self._get_methods(Sources)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(sources_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters applied for Sources inspection")
            return {}
        logger.info(f"Inspected Sources: count={len(sources_obj)}")
        return result

    def _inspect_telescope(self, telescope_obj: Union[Telescope, SpaceTelescope], attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Telescope or SpaceTelescope object.

        Args:
            telescope_obj (Telescope | SpaceTelescope): The telescope object to inspect.
            attributes (Dict[str, Any]): Dictionary of getter names and arguments.

        Returns:
            Dict[str, Any]: Dictionary with getter results.
        """
        obj_type = type(telescope_obj)
        valid_getters = self._get_methods(obj_type)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(telescope_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning(f"No valid getters applied for {obj_type.__name__} inspection")
            return {}
        logger.info(f"Inspected {obj_type.__name__}: code='{telescope_obj.get_code()}'")
        return result

    def _inspect_telescopes(self, telescopes_obj: Telescopes, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Telescopes object, supporting nested Telescope inspection.

        Args:
            telescopes_obj (Telescopes): The Telescopes object to inspect.
            attributes (Dict[str, Any]): Dictionary with optional "name" for nested inspection.

        Returns:
            Dict[str, Any]: Dictionary with getter results.
        """
        if "name" in attributes:
            name = attributes["name"]
            telescope_obj = telescopes_obj.get(name)
            if telescope_obj is None:
                logger.error(f"Telescope '{name}' not found in Telescopes")
                return {}
            if not isinstance(telescope_obj, (Telescope, SpaceTelescope)):
                logger.error(f"Object with code '{name}' is not a Telescope or SpaceTelescope, got {type(telescope_obj).__name__}")
                return {}
            nested_attrs = {k: v for k, v in attributes.items() if k != "name"}
            result = self._inspect_telescope(telescope_obj, nested_attrs)
            if result:
                return result
            logger.warning(f"Failed to inspect Telescope '{name}'")
            return {}
        valid_getters = self._get_methods(Telescopes)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(telescopes_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters applied for Telescopes inspection")
            return {}
        logger.info(f"Inspected Telescopes: count={len(telescopes_obj)}")
        return result

    def _inspect_scan(self, scan_obj: Scan, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Scan object, supporting observation-dependent getters.

        Args:
            scan_obj (Scan): The Scan object to inspect.
            attributes (Dict[str, Any]): Dictionary of getter names and arguments, optionally including "observation".

        Returns:
            Dict[str, Any]: Dictionary with getter results.
        """
        valid_getters = self._get_methods(Scan)
        result = {}
        observation = attributes.get("observation")
        for getter_name, getter_args in attributes.items():
            if getter_name == "observation":
                continue
            if getter_name in {"get_source", "get_telescopes", "get_frequencies", "check_telescope_availability"}:
                if not observation or not isinstance(observation, Observation):
                    logger.error(f"Getter {getter_name} requires a valid Observation object")
                    continue
            value = self._validate_and_apply_method(
                scan_obj,
                getter_name,
                getter_args,
                valid_getters,
                {"observation": observation} if observation else None
            )
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters applied for Scan inspection")
            return {}
        logger.info(f"Inspected Scan: start={scan_obj.get_start().isot}")
        return result

    def _inspect_scans(self, scans_obj: Scans, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Scans object, supporting nested Scan inspection.

        Args:
            scans_obj (Scans): The Scans object to inspect.
            attributes (Dict[str, Any]): Dictionary with optional "name" for nested inspection.

        Returns:
            Dict[str, Any]: Dictionary with getter results.
        """
        if "name" in attributes:
            name = attributes["name"]
            scan_obj = scans_obj.get(name)
            if scan_obj is None:
                logger.error(f"Scan '{name}' not found in Scans")
                return {}
            if not isinstance(scan_obj, Scan):
                logger.error(f"Object with name '{name}' is not a Scan, got {type(scan_obj).__name__}")
                return {}
            nested_attrs = {k: v for k, v in attributes.items() if k != "name"}
            result = self._inspect_scan(scan_obj, nested_attrs)
            if result:
                return result
            logger.warning(f"Failed to inspect Scan '{name}'")
            return {}
        valid_getters = self._get_methods(Scans)
        result = {}
        for getter_name, getter_args in attributes.items():
            if getter_name == "get_active_scans" and getter_args and "observation" in getter_args:
                if not isinstance(getter_args["observation"], Observation):
                    logger.error(f"Argument 'observation' for {getter_name} must be an Observation object")
                    continue
            value = self._validate_and_apply_method(scans_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters applied for Scans inspection")
            return {}
        logger.info(f"Inspected Scans: count={len(scans_obj)}")
        return result

    def _inspect_observation(self, obs_obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect an Observation object by calling specified getter methods.

        Args:
            obs_obj (Observation): The Observation object to inspect.
            attributes (Dict[str, Any]): Dictionary of getter names and arguments.

        Returns:
            Dict[str, Any]: Dictionary with getter results.
        """
        valid_getters = self._get_methods(Observation)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(obs_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters applied for Observation inspection")
            return {}
        logger.info(f"Inspected Observation: code='{obs_obj.get_observation_code()}'")
        return result

    def _inspect_project(self, project_obj: ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a ScheduleProject object, supporting nested Observation inspection.

        Args:
            project_obj (ScheduleProject): The ScheduleProject object to inspect.
            attributes (Dict[str, Any]): Dictionary with optional "name" for nested inspection.

        Returns:
            Dict[str, Any]: Dictionary with getter results.
        """
        if "name" in attributes:
            name = attributes["name"]
            try:
                observation_obj = project_obj.get_observation(name)
            except KeyError:
                logger.error(f"Observation '{name}' not found in Project")
                return {}
            if observation_obj:
                nested_attrs = {k: v for k, v in attributes.items() if k != "name"}
                result = self._inspect_observation(observation_obj, nested_attrs)
                if result:
                    return result
                logger.warning(f"Failed to inspect Observation '{name}'")
                return {}
            logger.warning(f"Observation '{name}' not found in ScheduleProject")
            return {}
        valid_getters = self._get_methods(ScheduleProject)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(project_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters applied for ScheduleProject inspection")
            return {}
        logger.info(f"Inspected ScheduleProject: name='{project_obj.get_name()}'")
        return result