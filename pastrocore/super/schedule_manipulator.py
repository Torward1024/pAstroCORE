from pastrocore.super.schedule_project import ScheduleProject
from msb_arch.utils.logging_setup import logger
from msb_arch import RequestJournal
from msb_arch.mega.manipulator import Manipulator
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
    def __init__(self, project: Optional['ScheduleProject'] = None,
                 journal_limit: Optional[int] = 500):
        """Initialize the ScheduleManipulator with default operations and supported classes.

        Args:
            project (Optional[ScheduleProject]): The ScheduleProject instance to manage. If None, no project is set initially.
            journal_limit (Optional[int]): How many requests to remember, most recent first.
                Defaults to 500. Pass None to record nothing.

        Notes:
            - Registers base classes: ScheduleProject, Observation, IF, Frequencies, Source, Sources,
            Telescope, SpaceTelescope, Telescopes, Scan, Scans.
            - Registers operations: configure (ScheduleConfigurator), inspect (ScheduleInspector),
            calculate (ScheduleCalculator), visualize (ScheduleVisualizer),
            export/save/load (ScheduleData), compute (ScheduleRunner).
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
        from pastrocore.super.schedule_data import ScheduleData
        from pastrocore.super.schedule_runner import ScheduleRunner

        base_classes = [
            ScheduleProject, Observation, IF, Frequencies, Source, Sources,
            Telescope, SpaceTelescope, Telescopes, Scan, Scans
        ]
        
        super().__init__(managing_object=project, base_classes=base_classes)
        
        self.register_operation(ScheduleConfigurator(self))
        self.register_operation(ScheduleInspector(self))
        # Deferred: between them these two import matplotlib, astropy.coordinates and scipy,
        # which is 2.3 s of a start-up that happens whether or not anyone calculates or plots.
        # They are registered from here -- the catalogue lists them, a facade exists, a plan may
        # name them -- and built when something first asks. `app.main` warms them in the
        # background once the window is up.
        self.register_deferred("calculate", self._make_calculator)
        self.register_deferred("visualize", self._make_visualizer)
        # One Super, three operations. MSB binds an instance to one operation name, so an
        # instance is registered per name and each resolves its own `_export`, `_save` or
        # `_load`. Keeping them in one class is deliberate: they are the same concern -- data
        # in and data out -- and a caller mapping commands to requests needs no special case
        # for the one that happens to be a save.
        self.register_operation(ScheduleData(self), operation="export")
        self.register_operation(ScheduleData(self), operation="save")
        self.register_operation(ScheduleData(self), operation="load")

        # `calculate` does one, `compute` orchestrates many, `export` writes the results
        # somewhere. Running a set of calculations lived on `export` because that is where the
        # plumbing already was, and it is not exporting anything. It cannot go on the calculator
        # either: a Super's handlers *are* its operation's methods, so a `_calculate_run` would
        # appear in the catalogue as a calculation called "Run".
        self.register_operation(ScheduleRunner(self), operation="compute")

        # Every request that reaches this orchestrator is recorded. It costs one interceptor
        # and answers the question a bug report never can: what was actually asked for.
        # Bounded, because a session that runs for a day should not accumulate without end.
        self._journal = RequestJournal(limit=journal_limit) if journal_limit else None
        if self._journal is not None:
            self.add_interceptor(self._journal)

        logger.info("Initialized ScheduleManipulator!")

    def _make_calculator(self):
        """Build the calculator. Called once, by MSB, when `calculate` is first needed."""
        from pastrocore.super.schedule_calculator import ScheduleCalculator

        return ScheduleCalculator(self)

    def _make_visualizer(self):
        """Build the visualizer. Called once, by MSB, when `visualize` is first needed."""
        from pastrocore.super.schedule_visualizer import ScheduleVisualizer

        return ScheduleVisualizer(self)

    def get_journal(self) -> Optional[RequestJournal]:
        """Return the record of every request this orchestrator has processed.

        Returns:
            Optional[RequestJournal]: The journal, or None if the orchestrator was built
                without one.

        Notes:
            - Read backwards it answers what produced a result: `journal.touching(name)` gives
              everything that ever touched an object, in order.
            - Read forwards it replays: `manipulator.replay(journal)` runs the same session
              again, which is how a reported problem becomes a reproduction.
            - **A session is portable.** `journal.entries` is plain data -- each step names its
              object by the path it sat at -- so it writes to a file and comes back:
              `RequestJournal.from_entries(...)`, or `replay` given the entries themselves.
              That is what `export(method="journal")` and `compute(method="replay")` are.
        """
        return self._journal