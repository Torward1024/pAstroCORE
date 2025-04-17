from common.super.super import Super
from unit_scheduling_2.super.schedule_project import ScheduleProject
from unit_scheduling_2.base.frequencies import IF, Frequencies
from unit_scheduling_2.base.sources import Source, Sources
from unit_scheduling_2.base.telescopes import Telescope, SpaceTelescope, Telescopes
from unit_scheduling_2.base.scans import Scan, Scans
from unit_scheduling_2.base.observation import Observation
from common.utils.logging_setup import logger
from common.utils.validation import check_type
from typing import Dict, Any, Union


class ScheduleInspector(Super):
    """Implementation of Inspector for inspecting scheduling entities using the Super framework.

    Provides methods to inspect astronomical scheduling entities (IF, Frequencies, Source, Sources,
    Telescope, SpaceTelescope, Telescopes, Scan, Scans, Observation, ScheduleProject) by invoking
    their getter methods and returning results in a dictionary. Supports nested inspection via name-based
    access using _do_nested and validates method applicability through a Manipulator.

    Args:
        manipulator: The Manipulator instance for method lookup and validation.

    Returns:
        Dict[str, Any]: Dictionary containing getter method results, wrapped by execute in a response dictionary
        with keys status, object, method, result, and error (if status=False).

    Examples:
        >>> from unit_scheduling_2.super.manipulator import ScheduleManipulator
        >>> manipulator = ScheduleManipulator()
        >>> inspector = ScheduleInspector(manipulator)
        >>> source = Source(name="3C 286")
        >>> result = inspector.execute(source, {"get": "name"})
        {'status': True, 'object': <Source>, 'method': '_inspect_source', 'result': {'get': '3C 286'}}
        >>> project = ScheduleProject()
        >>> project.create_item(item_code="OBS001")
        >>> result = inspector.execute(project, {"name": "OBS001", "get": "code"})
        {'status': True, 'object': <Observation>, 'method': '_inspect_observation', 'result': {'get': 'OBS001'}}
    """
    def __init__(self, manipulator: 'Manipulator'):
        """Initialize the ScheduleInspector.

        Args:
            manipulator: The Manipulator instance providing method validation and execution capabilities.
        """
        super().__init__(manipulator=manipulator)
        self._operation = "inspect"
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
        check_type(if_obj, IF, "IF object")
        valid_getters = self._get_methods(IF)
        result = {}
        applied = False
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(if_obj, getter_name, getter_args, valid_getters)
            if value["status"]:
                result[getter_name] = value["result"]
                applied = True
        if not applied:
            logger.warning("No valid getters applied for IF inspection")
            return {}
        logger.info(f"Inspected IF: frequency={if_obj.get('frequency')} MHz")
        return result

    def _inspect_frequencies(self, freq_obj: Frequencies, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Frequencies object, supporting nested IF inspection.

        Args:
            freq_obj (Frequencies): The Frequencies object to inspect.
            attributes (Dict[str, Any]): Dictionary with optional "name" for nested inspection.

        Returns:
            Dict[str, Any]: Dictionary with getter results or result of nested IF inspection.
        """
        check_type(freq_obj, Frequencies, "Frequencies object")
        if "name" in attributes:
            result = self._do_nested(
                freq_obj, attributes, "name", lambda k: freq_obj.get(k), self._inspect_if
            )
            if result["status"]:
                logger.info(f"Inspected nested IF in Frequencies: name={attributes['name']}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to inspect nested IF in Frequencies: name={attributes.get('name')}")
            return {}
        valid_getters = self._get_methods(Frequencies)
        result = {}
        applied = False
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(freq_obj, getter_name, getter_args, valid_getters)
            if value["status"]:
                result[getter_name] = value["result"]
                applied = True
        if not applied:
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
        check_type(source_obj, Source, "Source object")
        valid_getters = self._get_methods(Source)
        result = {}
        applied = False
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(source_obj, getter_name, getter_args, valid_getters)
            if value["status"]:
                result[getter_name] = value["result"]
                applied = True
        if not applied:
            logger.warning("No valid getters applied for Source inspection")
            return {}
        logger.info(f"Inspected Source: name='{source_obj.get('name')}'")
        return result

    def _inspect_sources(self, sources_obj: Sources, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Sources object, supporting nested Source inspection.

        Args:
            sources_obj (Sources): The Sources object to inspect.
            attributes (Dict[str, Any]): Dictionary with optional "name" for nested inspection.

        Returns:
            Dict[str, Any]: Dictionary with getter results or result of nested Source inspection.
        """
        check_type(sources_obj, Sources, "Sources object")
        if "name" in attributes:
            result = self._do_nested(
                sources_obj, attributes, "name", lambda k: sources_obj.get(k), self._inspect_source
            )
            if result["status"]:
                logger.info(f"Inspected nested Source in Sources: name={attributes['name']}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to inspect nested Source in Sources: name={attributes.get('name')}")
            return {}
        valid_getters = self._get_methods(Sources)
        result = {}
        applied = False
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(sources_obj, getter_name, getter_args, valid_getters)
            if value["status"]:
                result[getter_name] = value["result"]
                applied = True
        if not applied:
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
        check_type(telescope_obj, (Telescope, SpaceTelescope), "Telescope object")
        obj_type = type(telescope_obj)
        valid_getters = self._get_methods(obj_type)
        result = {}
        applied = False
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(telescope_obj, getter_name, getter_args, valid_getters)
            if value["status"]:
                result[getter_name] = value["result"]
                applied = True
        if not applied:
            logger.warning(f"No valid getters applied for {obj_type.__name__} inspection")
            return {}
        logger.info(f"Inspected {obj_type.__name__}: code='{telescope_obj.get('code')}'")
        return result

    def _inspect_telescopes(self, telescopes_obj: Telescopes, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Telescopes object, supporting nested Telescope inspection.

        Args:
            telescopes_obj (Telescopes): The Telescopes object to inspect.
            attributes (Dict[str, Any]): Dictionary with optional "name" for nested inspection.

        Returns:
            Dict[str, Any]: Dictionary with getter results or result of nested Telescope inspection.
        """
        check_type(telescopes_obj, Telescopes, "Telescopes object")
        if "name" in attributes:
            result = self._do_nested(
                telescopes_obj, attributes, "name", lambda k: telescopes_obj.get(k), self._inspect_telescope
            )
            if result["status"]:
                logger.info(f"Inspected nested Telescope in Telescopes: name={attributes['name']}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to inspect nested Telescope in Telescopes: name={attributes.get('name')}")
            return {}
        valid_getters = self._get_methods(Telescopes)
        result = {}
        applied = False
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(telescopes_obj, getter_name, getter_args, valid_getters)
            if value["status"]:
                result[getter_name] = value["result"]
                applied = True
        if not applied:
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
        check_type(scan_obj, Scan, "Scan object")
        valid_getters = self._get_methods(Scan)
        result = {}
        applied = False
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
            if value["status"]:
                result[getter_name] = value["result"]
                applied = True
        if not applied:
            logger.warning("No valid getters applied for Scan inspection")
            return {}
        logger.info(f"Inspected Scan: start={scan_obj.get('start').isot}")
        return result

    def _inspect_scans(self, scans_obj: Scans, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Scans object, supporting nested Scan inspection.

        Args:
            scans_obj (Scans): The Scans object to inspect.
            attributes (Dict[str, Any]): Dictionary with optional "name" for nested inspection.

        Returns:
            Dict[str, Any]: Dictionary with getter results or result of nested Scan inspection.
        """
        check_type(scans_obj, Scans, "Scans object")
        if "name" in attributes:
            name = attributes["name"]
            scan_obj = scans_obj.get(name)
            if scan_obj is None:
                logger.error(f"Scan '{name}' not found in Scans")
                return {}
            if not isinstance(scan_obj, Scan):
                logger.error(f"Object with name '{name}' is not a Scan, got {type(scan_obj).__name__}")
                return {}
            result = self._do_nested(
                scans_obj, attributes, "name", lambda k: scans_obj.get(k), self._inspect_scan
            )
            if result["status"]:
                logger.info(f"Inspected nested Scan in Scans: name={name}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to inspect nested Scan in Scans: name={name}")
            return {}
        valid_getters = self._get_methods(Scans)
        result = {}
        applied = False
        for getter_name, getter_args in attributes.items():
            if getter_name == "get_active_scans" and getter_args and "observation" in getter_args:
                if not isinstance(getter_args["observation"], Observation):
                    logger.error(f"Argument 'observation' for {getter_name} must be an Observation object")
                    continue
            value = self._validate_and_apply_method(scans_obj, getter_name, getter_args, valid_getters)
            if value["status"]:
                result[getter_name] = value["result"]
                applied = True
        if not applied:
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
        check_type(obs_obj, Observation, "Observation object")
        valid_getters = self._get_methods(Observation)
        result = {}
        applied = False
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(obs_obj, getter_name, getter_args, valid_getters)
            if value["status"]:
                result[getter_name] = value["result"]
                applied = True
        if not applied:
            logger.warning("No valid getters applied for Observation inspection")
            return {}
        logger.info(f"Inspected Observation: code='{obs_obj.get('code')}'")
        return result

    def _inspect_scheduleproject(self, project_obj: ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a ScheduleProject object, supporting nested Observation inspection.

        Args:
            project_obj (ScheduleProject): The ScheduleProject object to inspect.
            attributes (Dict[str, Any]): Dictionary with optional "name" for nested inspection.

        Returns:
            Dict[str, Any]: Dictionary with getter results or result of nested Observation inspection.
        """
        check_type(project_obj, ScheduleProject, "ScheduleProject object")
        if "name" in attributes:
            result = self._do_nested(
                project_obj, attributes, "name", lambda k: project_obj.get_observation(k), self._inspect_observation
            )
            if result["status"]:
                logger.info(f"Inspected nested Observation in ScheduleProject: name={attributes['name']}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to inspect nested Observation in ScheduleProject: name={attributes.get('name')}")
            return {}
        valid_getters = self._get_methods(ScheduleProject)
        result = {}
        applied = False
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(project_obj, getter_name, getter_args, valid_getters)
            if value["status"]:
                result[getter_name] = value["result"]
                applied = True
        if not applied:
            logger.warning("No valid getters applied for ScheduleProject inspection")
            return {}
        logger.info(f"Inspected ScheduleProject: name='{project_obj.get('name')}'")
        return result