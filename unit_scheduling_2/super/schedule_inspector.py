# /super/inspector.py
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
    """Scheduler implementation of Inspector for inspecting ScheduleProject and its components.

    Provides a universal interface to inspect scheduling objects by invoking their getter methods and
    returning results in a dictionary. Supports nested inspection for collections (e.g., Sources, Telescopes)
    via index-based access and validates method applicability through a Manipulator.

    Args:
        manipulator: The Manipulator instance used to validate and apply getter methods.

    Returns:
        Dict[str, Any]: Dictionary containing getter method results.

    Attributes:
        manipulator: The Manipulator instance used for method validation and execution.

    Examples:
        >>> from unit_scheduling.super.manipulator import ScheduleManipulator
        >>> manipulator = ScheduleManipulator()
        >>> inspector = ScheduleInspector(manipulator)
        >>> source = Source(name="3C 286")
        >>> result = inspector.inspect(source, {"get_name": None})
        {'get_name': '3C 286'}
        >>> project = ScheduleProject()
        >>> result = inspector.inspect(project, {"observation_index": 0, "get_observation_code": None})
        {'get_observation_code': 'OBS_DEFAULT'}
    """
    def __init__(self, manipulator: 'Manipulator'):
        """Initialize the ScheduleInspector.

        Args:
            manipulator: The Manipulator instance providing method validation and execution capabilities.

        Notes:
            - Initializes the parent Super class and sets up logging.
        """
        super().__init__(manipulator)
        logger.info("Initialized Scheduling Inspector")

    def _default_result(self) -> Dict[str, Any]:
        """Return the default result when inspection is not applied.

        Returns:
            Dict[str, Any]: An empty dictionary indicating no inspection was performed.
        """
        return {}
    
    def _inspect_if(self, if_obj: IF, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect an IF object by calling specified getter methods.

        Args:
            if_obj (IF): The IF object to inspect.
            attributes (Dict[str, Any]): Dictionary of getter method names and their arguments (e.g., {"get_frequency": None}).

        Returns:
            Dict[str, Any]: Dictionary mapping getter names to their results.

        Notes:
            - Only valid getter methods are executed, as determined by the Manipulator.
            - Logs frequency upon successful inspection.
        """
        valid_getters = self._manipulator.get_methods_for_type(IF)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(if_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters provided for IF inspection")
            return {}
        logger.info(f"Successfully inspected IF: freq={if_obj.get_frequency()} MHz")
        return result

    def _inspect_frequencies(self, freq_obj: Frequencies, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Frequencies object, supporting nested IF inspection.

        Args:
            freq_obj (Frequencies): The Frequencies object to inspect.
            attributes (Dict[str, Any]): Dictionary of getter names and arguments, optionally including "if_index".

        Returns:
            Dict[str, Any]: Dictionary with getter results.

        Notes:
            - Supports nested inspection of IF objects via "if_index".
            - Logs the total number of IFs upon success.
        """
        result = self._inspect_nested(freq_obj, attributes, "if_index", freq_obj.get_by_index, self._inspect_if)
        if result:
            return result
        valid_getters = self._manipulator.get_methods_for_type(Frequencies)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(freq_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters provided for Frequencies inspection")
            return {}
        logger.info(f"Successfully inspected Frequencies: count={len(freq_obj)}")
        return result

    def _inspect_source(self, source_obj: Source, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Source object by calling specified getter methods.

        Args:
            source_obj (Source): The Source object to inspect.
            attributes (Dict[str, Any]): Dictionary of getter names and arguments (e.g., {"get_name": None}).

        Returns:
            Dict[str, Any]: Dictionary with getter results.

        Notes:
            - Logs the source name upon successful inspection.
        """
        valid_getters = self._manipulator.get_methods_for_type(Source)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(source_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters provided for Source inspection")
            return {}
        logger.info(f"Successfully inspected Source: name='{source_obj.get_name()}'")
        return result

    def _inspect_sources(self, sources_obj: Sources, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Sources object, supporting nested Source inspection.

        Args:
            sources_obj (Sources): The Sources object to inspect.
            attributes (Dict[str, Any]): Dictionary of getter names and arguments, optionally including "source_index".

        Returns:
            Dict[str, Any]: Dictionary with getter results.

        Notes:
            - Supports nested Source inspection via "source_index".
            - Logs the total number of sources.
        """
        result = self._inspect_nested(sources_obj, attributes, "source_index", sources_obj.get_by_index, self._inspect_source)
        if result:
            return result
        valid_getters = self._manipulator.get_methods_for_type(Sources)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(sources_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters provided for Sources inspection")
            return {}
        logger.info(f"Successfully inspected Sources: count={len(sources_obj)}")
        return result

    def _inspect_telescope(self, telescope_obj: Union[Telescope, SpaceTelescope], attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Telescope or SpaceTelescope object.

        Args:
            telescope_obj (Telescope | SpaceTelescope): The telescope object to inspect.
            attributes (Dict[str, Any]): Dictionary of getter names and arguments (e.g., {"get_code": None}).

        Returns:
            Dict[str, Any]: Dictionary with getter results.

        Notes:
            - Dynamically handles both Telescope and SpaceTelescope types.
            - Logs the telescope code upon success.
        """
        obj_type = type(telescope_obj)
        valid_getters = self._manipulator.get_methods_for_type(obj_type)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(telescope_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning(f"No valid getters provided for {obj_type.__name__} inspection")
            return {}
        logger.info(f"Successfully inspected {obj_type.__name__}: code='{telescope_obj.get_code()}'")
        return result

    def _inspect_telescopes(self, telescopes_obj: Telescopes, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Telescopes object, supporting nested Telescope inspection.

        Args:
            telescopes_obj (Telescopes): The Telescopes object to inspect.
            attributes (Dict[str, Any]): Dictionary of getter names and arguments, optionally including "telescope_index".

        Returns:
            Dict[str, Any]: Dictionary with getter results.

        Notes:
            - Supports nested Telescope inspection via "telescope_index".
            - Logs the total number of telescopes.
        """
        result = self._inspect_nested(telescopes_obj, attributes, "telescope_index", telescopes_obj.get_by_index, self._inspect_telescope)
        if result:
            return result
        valid_getters = self._manipulator.get_methods_for_type(Telescopes)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(telescopes_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters provided for Telescopes inspection")
            return {}
        logger.info(f"Successfully inspected Telescopes: count={len(telescopes_obj)}")
        return result

    def _inspect_scan(self, scan_obj: Scan, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Scan object, supporting observation-dependent getters.

        Args:
            scan_obj (Scan): The Scan object to inspect.
            attributes (Dict[str, Any]): Dictionary of getter names and arguments, optionally including "observation".

        Returns:
            Dict[str, Any]: Dictionary with getter results.

        Notes:
            - Getters like "get_source" require an "observation" argument of type Observation.
            - Logs the scan start time upon success.
        """
        valid_getters = self._manipulator.get_methods_for_type(Scan)
        result = {}
        for getter_name, getter_args in attributes.items():
            if getter_name in {"get_source", "get_telescopes", "get_frequencies", "check_telescope_availability"}:
                if not getter_args or "observation" not in getter_args:
                    logger.error(f"Getter {getter_name} requires an 'observation' argument for Scan")
                    continue
                if not isinstance(getter_args["observation"], Observation):
                    logger.error(f"Argument 'observation' for {getter_name} must be an Observation object")
                    continue
            value = self._validate_and_apply_method(scan_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters provided for Scan inspection")
            return {}
        logger.info(f"Successfully inspected Scan: start={scan_obj.get_start()}")
        return result

    def _inspect_scans(self, scans_obj: Scans, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Scans object, supporting nested Scan inspection.

        Args:
            scans_obj (Scans): The Scans object to inspect.
            attributes (Dict[str, Any]): Dictionary of getter names and arguments, optionally including "scan_index".

        Returns:
            Dict[str, Any]: Dictionary with getter results.

        Notes:
            - Supports nested Scan inspection via "scan_index".
            - Validates "observation" argument for "get_active_scans".
            - Logs the total number of scans.
        """
        result = self._inspect_nested(scans_obj, attributes, "scan_index", scans_obj.get_by_index, self._inspect_scan)
        if result:
            return result
        valid_getters = self._manipulator.get_methods_for_type(Scans)
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
            logger.warning("No valid getters provided for Scans inspection")
            return {}
        logger.info(f"Successfully inspected Scans: count={len(scans_obj)}")
        return result

    def _inspect_observation(self, obs_obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a ScheduleProject object, supporting nested Observation inspection.

        Args:
            project_obj (ScheduleProject): The ScheduleProject object to inspect.
            attributes (Dict[str, Any]): Dictionary of getter names and arguments, optionally including "observation_index".

        Returns:
            Dict[str, Any]: Dictionary with getter results.

        Notes:
            - Supports nested Observation inspection via "observation_index".
            - Logs the project name upon success.
        """
        valid_getters = self._manipulator.get_methods_for_type(Observation)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(obs_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters provided for Observation inspection")
            return {}
        logger.info(f"Successfully inspected Observation: code='{obs_obj.get_observation_code()}'")
        return result

    def _inspect_project(self, project_obj: ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a ScheduleProject object, supporting nested Observation inspection.

        Args:
            project_obj (ScheduleProject): The ScheduleProject object to inspect.
            attributes (Dict[str, Any]): Dictionary of getter names and arguments, optionally including "observation_index".

        Returns:
            Dict[str, Any]: Dictionary with getter results.
        """
        result = self._inspect_nested(project_obj, attributes, "observation_index", project_obj.get_by_index, self._inspect_observation)
        if result:
            return result
        valid_getters = self._manipulator.get_methods_for_type(ScheduleProject)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(project_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters provided for Project inspection")
            return {}
        logger.info(f"Successfully inspected Project: name='{project_obj.get_name()}'")
        return result