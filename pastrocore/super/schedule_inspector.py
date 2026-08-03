from msb_arch.super.super import Super
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.frequencies import IF, Frequencies
from pastrocore.base.sources import Source, Sources
from pastrocore.base.telescopes import Telescope, SpaceTelescope, Telescopes
from pastrocore.base.scans import Scan, Scans
from pastrocore.base.observation import Observation
from msb_arch.utils.logging_setup import logger
from msb_arch.utils.validation import check_type
from typing import Dict, Any


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
    OPERATION = "inspect"

    def __init__(self, manipulator: 'Manipulator'):
        """Initialize the ScheduleInspector.

        Args:
            manipulator: The Manipulator instance providing method validation and execution capabilities.
        """
        super().__init__(manipulator=manipulator)
        logger.debug("Initialized ScheduleInspector")

    def _inspect_if(self, if_obj: IF, attributes: Dict[str, Any]) -> Any:
        """Inspect an IF object and report every requested getter."""
        check_type(if_obj, IF, "IF object")
        return self._apply_methods(if_obj, attributes)


    def _inspect_frequencies(self, freq_obj: Frequencies, attributes: Dict[str, Any]) -> Any:
        """Inspect a Frequencies object, supporting nested IF inspection."""
        check_type(freq_obj, Frequencies, "Frequencies object")
        if "name" in attributes:
            result = self._do_nested(
                freq_obj, attributes, "name", freq_obj.get, self._inspect_if
            )
            if result["status"]:
                logger.debug(f"Inspected nested IF in Frequencies: name={attributes['name']}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to inspect nested IF in Frequencies: name={attributes.get('name')}")
            raise ValueError(result.get("error", "Operation not executed"))
        return self._apply_methods(freq_obj, attributes)


    def _inspect_source(self, source_obj: Source, attributes: Dict[str, Any]) -> Any:
        """Inspect a Source object and report every requested getter."""
        check_type(source_obj, Source, "Source object")
        return self._apply_methods(source_obj, attributes)


    def _inspect_sources(self, sources_obj: Sources, attributes: Dict[str, Any]) -> Any:
        """Inspect a Sources object, supporting nested Source inspection."""
        check_type(sources_obj, Sources, "Sources object")
        if "name" in attributes:
            result = self._do_nested(
                sources_obj, attributes, "name", sources_obj.get, self._inspect_source
            )
            if result["status"]:
                logger.debug(f"Inspected nested Source in Sources: name={attributes['name']}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to inspect nested Source in Sources: name={attributes.get('name')}")
            raise ValueError(result.get("error", "Operation not executed"))
        return self._apply_methods(sources_obj, attributes)


    def _inspect_telescope(self, telescope_obj: Telescope, attributes: Dict[str, Any]) -> Any:
        """Inspect a Telescope object and report every requested getter."""
        check_type(telescope_obj, Telescope, "Telescope object")
        return self._apply_methods(telescope_obj, attributes)

    
    def _inspect_spacetelescope(self, telescope_obj: SpaceTelescope, attributes: Dict[str, Any]) -> Any:
        """Inspect a SpaceTelescope object and report every requested getter."""
        check_type(telescope_obj, SpaceTelescope, "SpaceTelescope object")
        return self._apply_methods(telescope_obj, attributes)


    def _inspect_telescopes(self, telescopes_obj: Telescopes, attributes: Dict[str, Any]) -> Any:
        """Inspect a Telescopes object, supporting nested Telescope inspection."""
        check_type(telescopes_obj, Telescopes, "Telescopes object")
        if "name" in attributes:
            result = self._do_nested(
                telescopes_obj, attributes, "name", telescopes_obj.get, self._inspect_telescope
            )
            if result["status"]:
                logger.debug(f"Inspected nested Telescope in Telescopes: name={attributes['name']}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to inspect nested Telescope in Telescopes: name={attributes.get('name')}")
            raise ValueError(result.get("error", "Operation not executed"))
        return self._apply_methods(telescopes_obj, attributes)


    def _inspect_scan(self, scan_obj: Scan, attributes: Dict[str, Any]) -> Any:
        """Inspect a Scan object and report every requested getter."""
        check_type(scan_obj, Scan, "Scan object")
        return self._apply_methods(scan_obj, attributes)


    def _inspect_scans(self, scans_obj: Scans, attributes: Dict[str, Any]) -> Any:
        """Inspect a Scans object, supporting nested Scan inspection."""
        check_type(scans_obj, Scans, "Scans object")
        if "name" in attributes:
            result = self._do_nested(
                scans_obj, attributes, "name", scans_obj.get, self._inspect_scan
            )
            if result["status"]:
                logger.debug(f"Inspected nested Scan in Scans: name={attributes['name']}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to inspect nested Scan in Scans: name={attributes.get('name')}")
            raise ValueError(result.get("error", "Operation not executed"))
        return self._apply_methods(scans_obj, attributes)


    def _inspect_observation(self, obs_obj: Observation, attributes: Dict[str, Any]) -> Any:
        """Inspect an Observation object and report every requested getter."""
        check_type(obs_obj, Observation, "Observation object")
        return self._apply_methods(obs_obj, attributes)


    def _inspect_scheduleproject(self, project_obj: ScheduleProject, attributes: Dict[str, Any]) -> Any:
        """Inspect a ScheduleProject object, supporting nested Observation inspection."""
        check_type(project_obj, ScheduleProject, "ScheduleProject object")
        if "name" in attributes:
            result = self._do_nested(
                project_obj, attributes, "name", project_obj.get_observation, self._inspect_observation
            )
            if result["status"]:
                logger.debug(f"Inspected nested Observation in ScheduleProject: name={attributes['name']}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to inspect nested Observation in ScheduleProject: name={attributes.get('name')}")
            raise ValueError(result.get("error", "Operation not executed"))
        return self._apply_methods(project_obj, attributes)

