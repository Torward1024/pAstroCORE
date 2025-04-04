from unit_scheduling.super.schedule_project import ScheduleProject
from common.utils.logging_setup import logger
from common.super.manipulator import Manipulator
from typing import Optional

class ScheduleManipulator(Manipulator):
    def __init__(self, project: Optional['ScheduleProject'] = None):
        from unit_scheduling.super.schedule_project import ScheduleProject
        from unit_scheduling.base.observation import Observation
        from unit_scheduling.base.frequencies import IF, Frequencies
        from unit_scheduling.base.sources import Source, Sources
        from unit_scheduling.base.telescopes import Telescope, SpaceTelescope, Telescopes
        from unit_scheduling.base.scans import Scan, Scans
        from unit_scheduling.super.configurator import ScheduleConfigurator
        from unit_scheduling.super.inspector import ScheduleInspector
        from unit_scheduling.super.calculator import ScheduleCalculator
        from unit_scheduling.super.visualizer import ScheduleVisualizer

        base_classes = [
            ScheduleProject, Observation, IF, Frequencies, Source, Sources,
            Telescope, SpaceTelescope, Telescopes, Scan, Scans
        ]
        
        super().__init__(managing_object=project, base_classes=base_classes)
        
        self.register_operation("configure", ScheduleConfigurator(self))
        self.register_operation("inspect", ScheduleInspector(self))
        self.register_operation("calculate", ScheduleCalculator(self))
        self.register_operation("visualize", ScheduleVisualizer(self))
        
        logger.info("Initialized DefaultManipulator with default operations")