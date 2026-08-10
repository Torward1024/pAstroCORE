from msb_arch import Inspector
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


class ScheduleInspector(Inspector):
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

    def _nested_getter(self, obj):
        """How to reach one member of `obj` by name.

        Notes:
            - A `ScheduleProject` holds observations and answers `get_observation(name)`,
              where a container answers `get(name)`. That difference is the whole reason
              msb_arch made the descent a hook rather than a convention.
        """
        if isinstance(obj, ScheduleProject):
            return obj.get_observation
        return super()._nested_getter(obj)
    OPERATION = "inspect"

    def __init__(self, manipulator: 'Manipulator'):
        """Initialize the ScheduleInspector.

        Args:
            manipulator: The Manipulator instance providing method validation and execution capabilities.
        """
        super().__init__(manipulator=manipulator)
        logger.debug("Initialized ScheduleInspector")










    











