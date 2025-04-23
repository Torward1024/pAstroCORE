from pastrocore.super.schedule_project import ScheduleProject
from common.utils.logging_setup import logger
from common.super.manipulator import Manipulator
from typing import Optional

class ScheduleManipulator(Manipulator):
    """Scheduler implementation of Manipulator for managing astronomical scheduling operations.

    Extends the base Manipulator class to provide a centralized interface for configuring, inspecting,
    calculating, and visualizing ScheduleProject and its components. Registers default operations
    (configure, inspect, calculate, visualize) with corresponding handler classes.

    Args:
        project (Optional[ScheduleProject]): The ScheduleProject instance to manage. Defaults to None.

    Attributes:
        managing_object: The object being managed (typically a ScheduleProject).
        base_classes (List[type]): List of supported base classes for method validation.
        operations (Dict[str, Any]): Registered operations (e.g., "configure", "inspect").

    Examples:
        >>> from unit_scheduling.super.schedule_project import ScheduleProject
        >>> manipulator = ScheduleManipulator(project=ScheduleProject(name="TestProject"))
        >>> manipulator.operations["configure"]
        <ScheduleConfigurator object at ...>
        >>> manipulator.get_methods_for_type(Source)
        {'get_name': <function ...>, 'set_name': <function ...>, ...}
    """
    def __init__(self, project: Optional['ScheduleProject'] = None):
        """Initialize the ScheduleManipulator with default operations and supported classes.

        Args:
            project (Optional[ScheduleProject]): The ScheduleProject instance to manage. If None, no project is set initially.

        Notes:
            - Registers base classes: ScheduleProject, Observation, IF, Frequencies, Source, Sources,
            Telescope, SpaceTelescope, Telescopes, Scan, Scans.
            - Registers operations: configure (ScheduleConfigurator), inspect (ScheduleInspector),
            calculate (ScheduleCalculator), visualize (ScheduleVisualizer).
            - Logs initialization upon completion.
        """
        from pastrocore.super.schedule_project import ScheduleProject
        from pastrocore.base.observation import Observation
        from pastrocore.base.frequencies import IF, Frequencies
        from pastrocore.base.sources import Source, Sources
        from pastrocore.base.telescopes import Telescope, SpaceTelescope, Telescopes
        from pastrocore.base.scans import Scan, Scans
        from pastrocore.super.schedule_configurator import ScheduleConfigurator
        from pastrocore.super.schedule_inspector import ScheduleInspector
        from pastrocore.super.schedule_calculator import ScheduleCalculator
        from pastrocore.super.schedule_visualizer import ScheduleVisualizer

        base_classes = [
            ScheduleProject, Observation, IF, Frequencies, Source, Sources,
            Telescope, SpaceTelescope, Telescopes, Scan, Scans
        ]
        
        super().__init__(managing_object=project, base_classes=base_classes)
        
        self.register_operation("configure", ScheduleConfigurator(self))
        self.register_operation("inspect", ScheduleInspector(self))
        self.register_operation("calculate", ScheduleCalculator(self))
        self.register_operation("visualize", ScheduleVisualizer(self))
        
        logger.info("Initialized ScheduleManipulator!")