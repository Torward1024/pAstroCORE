from common.super.super import Super
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.frequencies import IF, Frequencies
from pastrocore.base.sources import Source, Sources
from pastrocore.base.telescopes import Telescope, SpaceTelescope, Telescopes
from pastrocore.base.scans import Scan, Scans
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
from common.utils.validation import check_type
from typing import Dict, Any, Union


class ScheduleInspector(Super):
    """Implementation of Inspector for inspecting scheduling entities using the Super framework.

    Provides methods to inspect astronomical scheduling entities (IF, Frequencies, Source, Sources,
    Telescope, SpaceTelescope, Telescopes, Scan, Scans, Observation, ScheduleProject) by invoking
    their getter methods. Returns the result of a final method (e.g., get, get_code) in the response dictionary.

    Args:
        manipulator: The Manipulator instance for method lookup and validation.

    Returns:
        Dict[str, Any]: Dictionary containing the result of the final method, wrapped by Super.execute
        in a response dictionary with keys status, object, method, result, and error (if status=False).

    Examples:
        >>> from pastrocore.super.manipulator import ScheduleManipulator
        >>> manipulator = ScheduleManipulator()
        >>> inspector = ScheduleInspector(manipulator)
        >>> source = Source(name="3C 286")
        >>> result = inspector.execute(source, {"get": "name"})
        {'status': True, 'object': <Source>, 'method': '_inspect_source', 'result': {'name': '3C 286'}}
        >>> project = ScheduleProject()
        >>> project.create_item(item_code="OBS001")
        >>> result = inspector.execute(project, {"name": "OBS001", "get": "code"})
        {'status': True, 'object': <Observation>, 'method': '_inspect_observation', 'result': 'OBS001'}
    """
    def __init__(self, manipulator: 'Manipulator'):
        """Initialize the ScheduleInspector.

        Args:
            manipulator: The Manipulator instance providing method validation and execution capabilities.
        """
        super().__init__(manipulator=manipulator)
        self._operation = "inspect"
        logger.info("Initialized ScheduleInspector")

    def _inspect_if(self, if_obj: IF, attributes: Dict[str, Any]) -> Any:
        """Inspect an IF object and return its get() result with requested attributes.

        Args:
            if_obj (IF): The IF object to inspect.
            attributes (Dict[str, Any]): Dictionary of getter method names and arguments.

        Returns:
            Any: Result of if_obj.get(getter_args) or if_obj.get().

        Raises:
            ValueError: If no valid getters are applied.
        """
        check_type(if_obj, IF, "IF object")
        valid_getters = self._get_methods(IF)
        applied = False
        
        for getter_name, getter_args in attributes.items():
            if getter_name == "get":
                continue
            value = self._validate_and_apply_method(if_obj, getter_name, getter_args, valid_getters)
            if value["status"]:
                applied = True
            else:
                logger.warning(f"Invalid getter '{getter_name}' for IF inspection: {value['error']}")
                raise ValueError(value["error"])
        
        getter_args = attributes.get("get")
        if not applied and not getter_args:
            logger.warning("No valid getters applied for IF inspection")
            raise ValueError("No valid getters applied")
        
        result = self._validate_and_apply_method(if_obj, "get", getter_args, valid_getters)
        if not result["status"]:
            raise ValueError(result["error"])
        
        final_result = result["result"]
        logger.info(f"Inspected IF: frequency={if_obj.get('frequency')} MHz, result={final_result}")
        return final_result

    def _inspect_frequencies(self, freq_obj: Frequencies, attributes: Dict[str, Any]) -> Any:
        """Inspect a Frequencies object, supporting nested IF inspection.

        Args:
            freq_obj (Frequencies): The Frequencies object to inspect.
            attributes (Dict[str, Any]): Dictionary with optional "name" for nested inspection.

        Returns:
            Any: Length of freq_obj or result of nested IF inspection.

        Raises:
            ValueError: If no valid getters are applied or nested inspection fails.
        """
        check_type(freq_obj, Frequencies, "Frequencies object")
        if "name" in attributes:
            name = attributes["name"]
            if_obj = freq_obj.get(name)
            if if_obj is None:
                logger.error(f"IF '{name}' not found in Frequencies")
                raise ValueError(f"Name '{name}' not found in Frequencies")
            result = self._do_nested(
                freq_obj, attributes, "name", lambda k: freq_obj.get(k), self._inspect_if
            )
            if result["status"]:
                logger.info(f"Inspected nested IF in Frequencies: name={name}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to inspect nested IF in Frequencies: name={name}")
            raise ValueError(result.get("error", "Operation not executed"))
        valid_getters = self._get_methods(Frequencies)
        applied = False
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(freq_obj, getter_name, getter_args, valid_getters)
            if value["status"]:
                applied = True
        if not applied:
            logger.warning("No valid getters applied for Frequencies inspection")
            raise ValueError("No valid getters applied")
        final_result = len(freq_obj)
        logger.info(f"Inspected Frequencies: count={final_result}, result={final_result}")
        return final_result

    def _inspect_source(self, source_obj: Source, attributes: Dict[str, Any]) -> Any:
        """Inspect a Source object and return its get() result with requested attributes."""
        check_type(source_obj, Source, "Source object")
        valid_getters = self._get_methods(Source)
        applied = False
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(source_obj, getter_name, getter_args, valid_getters)
            if value["status"]:
                applied = True
            else:
                logger.warning(f"Invalid getter '{getter_name}' for Source inspection: {value['error']}")
                raise ValueError(value["error"])
        if not applied:
            logger.warning("No valid getters applied for Source inspection")
            raise ValueError("No valid getters applied")
        getter_args = attributes.get("get")
        final_result = source_obj.get(getter_args) if getter_args else source_obj.get()
        logger.info(f"Inspected Source: name='{source_obj.get('name')}', result={final_result}")
        return final_result

    def _inspect_sources(self, sources_obj: Sources, attributes: Dict[str, Any]) -> Any:
        """Inspect a Sources object, supporting nested Source inspection.

        Args:
            sources_obj (Sources): The Sources object to inspect.
            attributes (Dict[str, Any]): Dictionary with optional "name" for nested inspection.

        Returns:
            Any: Length of sources_obj or result of nested Source inspection.

        Raises:
            ValueError: If no valid getters are applied or nested inspection fails.
        """
        check_type(sources_obj, Sources, "Sources object")
        if "name" in attributes:
            name = attributes["name"]
            source_obj = sources_obj.get(name)
            if source_obj is None:
                logger.error(f"Source '{name}' not found in Sources")
                raise ValueError(f"Name '{name}' not found in Sources")
            result = self._do_nested(
                sources_obj, attributes, "name", lambda k: sources_obj.get(k), self._inspect_source
            )
            if result["status"]:
                logger.info(f"Inspected nested Source in Sources: name={name}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to inspect nested Source in Sources: name={name}")
            raise ValueError(result.get("error", "Operation not executed"))
        valid_getters = self._get_methods(Sources)
        applied = False
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(sources_obj, getter_name, getter_args, valid_getters)
            if value["status"]:
                applied = True
        if not applied:
            logger.warning("No valid getters applied for Sources inspection")
            raise ValueError("No valid getters applied")
        final_result = len(sources_obj)
        logger.info(f"Inspected Sources: count={final_result}, result={final_result}")
        return final_result

    def _inspect_telescope(self, telescope_obj: Union[Telescope, SpaceTelescope], attributes: Dict[str, Any]) -> str:
        """Inspect a Telescope or SpaceTelescope object and return its get_code() result."""
        check_type(telescope_obj, (Telescope, SpaceTelescope), "Telescope object")
        obj_type = type(telescope_obj)
        valid_getters = self._get_methods(obj_type)
        applied = False
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(telescope_obj, getter_name, getter_args, valid_getters)
            if value["status"]:
                applied = True
            else:
                logger.warning(f"Invalid getter '{getter_name}' for {obj_type.__name__} inspection: {value['error']}")
                raise ValueError(value["error"])
        if not applied:
            logger.warning(f"No valid getters applied for {obj_type.__name__} inspection")
            raise ValueError("No valid getters applied")
        final_result = telescope_obj.get_code()
        logger.info(f"Inspected {obj_type.__name__}: code='{final_result}', result={final_result}")
        return final_result

    def _inspect_telescopes(self, telescopes_obj: Telescopes, attributes: Dict[str, Any]) -> Any:
        """Inspect a Telescopes object, supporting nested Telescope inspection.

        Args:
            telescopes_obj (Telescopes): The Telescopes object to inspect.
            attributes (Dict[str, Any]): Dictionary with optional "name" for nested inspection.

        Returns:
            Any: Length of telescopes_obj or result of nested Telescope inspection.

        Raises:
            ValueError: If no valid getters are applied or nested inspection fails.
        """
        check_type(telescopes_obj, Telescopes, "Telescopes object")
        if "name" in attributes:
            name = attributes["name"]
            telescope_obj = telescopes_obj.get(name)
            if telescope_obj is None:
                logger.error(f"Telescope '{name}' not found in Telescopes")
                raise ValueError(f"Name '{name}' not found in Telescopes")
            result = self._do_nested(
                telescopes_obj, attributes, "name", lambda k: telescopes_obj.get(k), self._inspect_telescope
            )
            if result["status"]:
                logger.info(f"Inspected nested Telescope in Telescopes: name={name}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to inspect nested Telescope in Telescopes: name={name}")
            raise ValueError(result.get("error", "Operation not executed"))
        valid_getters = self._get_methods(Telescopes)
        applied = False
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(telescopes_obj, getter_name, getter_args, valid_getters)
            if value["status"]:
                applied = True
        if not applied:
            logger.warning("No valid getters applied for Telescopes inspection")
            raise ValueError("No valid getters applied")
        final_result = len(telescopes_obj)
        logger.info(f"Inspected Telescopes: count={final_result}, result={final_result}")
        return final_result

    def _inspect_scan(self, scan_obj: Scan, attributes: Dict[str, Any]) -> Any:
        """Inspect a Scan object, supporting observation-dependent getters."""
        check_type(scan_obj, Scan, "Scan object")
        valid_getters = self._get_methods(Scan)
        applied = False

        for getter_name, getter_args in attributes.items():
            if getter_name in {"get_source", "get_telescopes", "get_frequencies", "check_telescope_availability"}:
                observation = None
                if isinstance(getter_args, dict):
                    observation = getter_args.get("observation")
                print(f"Observation for {getter_name}: {observation}")
                if not observation or not isinstance(observation, Observation):
                    logger.error(f"Getter {getter_name} requires a valid Observation object, got {type(observation)}")
                    raise ValueError(f"Getter {getter_name} requires a valid Observation object")
                extra_args = {"observation": observation}
            else:
                extra_args = None

            value = self._validate_and_apply_method(
                scan_obj,
                getter_name,
                getter_args,
                valid_getters,
                extra_args
            )
            if value["status"]:
                applied = True
                result = value["result"]
                return result
            else:
                logger.warning(f"Invalid getter '{getter_name}' for Scan inspection: {value['error']}")
                raise ValueError(value["error"])

        if not applied:
            logger.warning("No valid getters applied for Scan inspection")
            raise ValueError("No valid getters applied")
        
        getter_args = attributes.get("get")
        final_result = scan_obj.get(getter_args) if getter_args else scan_obj.get()
        logger.info(f"Inspected Scan: start={scan_obj.get('start').isot}, result={final_result}")
        return final_result

    def _inspect_scans(self, scans_obj: Scans, attributes: Dict[str, Any]) -> Any:
        """Inspect a Scans object, supporting nested Scan inspection.

        Args:
            scans_obj (Scans): The Scans object to inspect.
            attributes (Dict[str, Any]): Dictionary with optional "name" for nested inspection.

        Returns:
            Any: Length of scans_obj or result of nested Scan inspection.

        Raises:
            ValueError: If no valid getters are applied or nested inspection fails.
        """
        check_type(scans_obj, Scans, "Scans object")
        if "name" in attributes:
            name = attributes["name"]
            scan_obj = scans_obj.get(name)
            if scan_obj is None:
                logger.error(f"Scan '{name}' not found in Scans")
                raise ValueError(f"Name '{name}' not found in Scans")
            if not isinstance(scan_obj, Scan):
                logger.error(f"Object with name '{name}' is not a Scan, got {type(scan_obj).__name__}")
                raise ValueError(f"Object with name '{name}' is not a Scan")
            result = self._do_nested(
                scans_obj, attributes, "name", lambda k: scans_obj.get(k), self._inspect_scan
            )
            if result["status"]:
                logger.info(f"Inspected nested Scan in Scans: name={name}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to inspect nested Scan in Scans: name={name}")
            raise ValueError(result.get("error", "Operation not executed"))
        valid_getters = self._get_methods(Scans)
        applied = False
        for getter_name, getter_args in attributes.items():
            if getter_name == "get_active_scans" and getter_args and "observation" in getter_args:
                if not isinstance(getter_args["observation"], Observation):
                    logger.error(f"Argument 'observation' for {getter_name} must be an Observation object")
                    raise ValueError(f"Argument 'observation' for {getter_name} must be an Observation object")
            value = self._validate_and_apply_method(scans_obj, getter_name, getter_args, valid_getters)
            if value["status"]:
                applied = True
        if not applied:
            logger.warning("No valid getters applied for Scans inspection")
            raise ValueError("No valid getters applied")
        final_result = len(scans_obj)
        logger.info(f"Inspected Scans: count={final_result}, result={final_result}")
        return final_result

    def _inspect_observation(self, obs_obj: Observation, attributes: Dict[str, Any]) -> str:
        """Inspect an Observation object and return its get_observation_code() result."""
        check_type(obs_obj, Observation, "Observation object")
        valid_getters = self._get_methods(Observation)
        applied = False
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(obs_obj, getter_name, getter_args, valid_getters)
            if value["status"]:
                applied = True
            else:
                logger.warning(f"Invalid getter '{getter_name}' for Observation inspection: {value['error']}")
                raise ValueError(value["error"])
        if not applied:
            logger.warning("No valid getters applied for Observation inspection")
            raise ValueError("No valid getters applied")
        final_result = obs_obj.get_observation_code()
        logger.info(f"Inspected Observation: code='{final_result}', result={final_result}")
        return final_result

    def _inspect_scheduleproject(self, project_obj: ScheduleProject, attributes: Dict[str, Any]) -> Any:
        """Inspect a ScheduleProject object, supporting nested Observation inspection.

        Args:
            project_obj (ScheduleProject): The ScheduleProject object to inspect.
            attributes (Dict[str, Any]): Dictionary with optional "name" for nested inspection.

        Returns:
            Any: Result of project_obj.get_name() or result of nested Observation inspection.

        Raises:
            ValueError: If no valid getters are applied or nested inspection fails.
        """
        check_type(project_obj, ScheduleProject, "ScheduleProject object")
        if "name" in attributes:
            name = attributes["name"]
            obs_obj = project_obj.get_observation(name)
            if obs_obj is None:
                logger.error(f"Observation '{name}' not found in ScheduleProject")
                raise ValueError(f"Name '{name}' not found in ScheduleProject")
            result = self._do_nested(
                project_obj, attributes, "name", lambda k: project_obj.get_observation(k), self._inspect_observation
            )
            if result["status"]:
                logger.info(f"Inspected nested Observation in ScheduleProject: name={name}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to inspect nested Observation in ScheduleProject: name={name}")
            raise ValueError(result.get("error", "Operation not executed"))
        valid_getters = self._get_methods(ScheduleProject)
        applied = False
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(project_obj, getter_name, getter_args, valid_getters)
            if value["status"]:
                applied = True
        if not applied:
            logger.warning("No valid getters applied for ScheduleProject inspection")
            raise ValueError("No valid getters applied")
        final_result = project_obj.get_name()
        logger.info(f"Inspected ScheduleProject: name='{final_result}', result={final_result}")
        return final_result