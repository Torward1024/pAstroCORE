from pastrocore import theme
from pastrocore.super.schedule_project import ScheduleProject
from msb_arch.utils.logging_setup import logger
from msb_arch import RequestJournal
from msb_arch.mega.manipulator import Manipulator
from typing import Optional

class ScheduleManipulator(Manipulator):
    """Scheduler implementation of Manipulator for managing astronomical scheduling operations.

    Which operations only read is said by their names (S1):

    | Reads | Changes the project | Files, read or written |
    | --- | --- | --- |
    | `inspect`, `visualize`, `analyze`, `catalogue` | `configure`, `calculate`, `compute` | `save`, `load`, `export`, `vex`, `cfx` |

    `inspect` is held to it by msb_arch, which since 3.0.0 calls nothing through it that is not
    named as a read; the questions this application asks of itself -- what can be calculated,
    what is stale, what a session held -- are `inspect` handlers for the same reason.

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
        >>> from pastrocore.super.schedule_project import ScheduleProject
        >>> manipulator = ScheduleManipulator(project=ScheduleProject(name="TestProject"))
        >>> manipulator.operations["configure"]
        <ScheduleConfigurator object at ...>
        >>> manipulator.get_methods_for_type(Source)
        {'get_name': <function ...>, 'set_name': <function ...>, ...}
    """
    #: The operations that only read: a session leaves them out and a replay does not run
    #: them. `catalogue` here is msb_arch's own, not `inspect(method="catalogue")`.
    READING = frozenset({"inspect", "visualize", "analyze", "catalogue"})

    #: The operations whose attributes name the model's own methods when no handler is
    #: named: `configure(project, create_item={...})` calls `create_item`.
    CALLING = frozenset({"inspect", "configure"})

    #: The operations that change the project in hand, which a command line saves after. A file
    #: read or written -- `load`, `save`, `export` -- changes nothing in it.
    CHANGING = frozenset({"configure", "calculate", "compute"})

    @classmethod
    def reads(cls, operation: Optional[str]) -> bool:
        """Report whether an operation only reads, by its name."""
        return operation in cls.READING

    @classmethod
    def changes(cls, operation: Optional[str]) -> bool:
        """Report whether an operation changes the project in hand, by its name."""
        return operation in cls.CHANGING

    def __init__(self, project: Optional['ScheduleProject'] = None,
                 journal_limit: Optional[int] = 500):
        """Initialize the ScheduleManipulator with default operations and supported classes.

        Args:
            project (Optional[ScheduleProject]): The ScheduleProject instance to manage. If None, no project is set initially.
            journal_limit (Optional[int]): How many requests to remember, most recent first.
                Defaults to 500. Pass None to record nothing.

        Notes:
            - Registers every model class, and the operations `configure`, `inspect`,
              `calculate`, `visualize`, `export`, `save`, `load` and `compute`.
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
        # Deferred: between them these two import matplotlib, astropy.coordinates and
        # scipy, which is 2.3 s of start-up. Registered here and built when first asked.
        self.register_deferred("calculate", self._make_calculator)
        self.register_deferred("visualize", self._make_visualizer)
        # One Super, three operations. MSB binds an instance to one operation name, so
        # one is registered per name; data in and data out is one concern.
        self.register_operation(ScheduleData(self), operation="export")
        self.register_operation(ScheduleData(self), operation="save")
        self.register_operation(ScheduleData(self), operation="load")

        # `calculate` does one, `compute` orchestrates many, `export` writes them out.
        # Not on the calculator: `_calculate_run` would be a calculation called "Run".
        self.register_operation(ScheduleRunner(self), operation="compute")

        # `analyze` reads results rather than producing them, so `_calculate_windows`
        # would be a calculation called "Windows". Deferred, like the calculator.
        self.register_deferred("analyze", self._make_analyzer)

        # One operation per format, named after the format: writing a VEX file, reading
        # one and checking one are three things done to one contract.
        self.register_deferred("vex", self._make_vex)
        self.register_deferred("cfx", self._make_cfx)

        # The palette the plots are drawn in, until the interface says which one the window is
        # wearing. Light, because that is what a plot saved to a file for a paper wants.
        self._plot_theme = "light"

        # Every request is recorded, which answers what was actually asked for. Bounded,
        # so a session running for a day does not accumulate without end.
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

        visualizer = ScheduleVisualizer(self)
        visualizer.set_style_config(theme.plot_style(self._plot_theme), partial=True)
        return visualizer

    def set_plot_theme(self, name: str) -> str:
        """Draw the plots in the palette the window is drawn in (U1).

        Args:
            name (str): `light` or `dark`; anything else is taken as the light one, since a
                settings file is a file a person may edit.

        Returns:
            str: The theme now in force.

        Notes:
            - Asked of the orchestrator, because the visualizer is deferred and does not
              exist at start-up; the choice is applied when it is built.
            - A plot on screen keeps the palette it was drawn in until it is redrawn.
        """
        self._plot_theme = theme.resolve(name)
        visualizer = self._operations.get("visualize")
        if visualizer is not None:
            visualizer.set_style_config(theme.plot_style(self._plot_theme), partial=True)
        return self._plot_theme

    def _make_analyzer(self):
        """Build the analyzer. Called once, by MSB, when `analyze` is first needed."""
        from pastrocore.super.schedule_analyzer import ScheduleAnalyzer

        return ScheduleAnalyzer(self)

    def _make_vex(self):
        """Build the VEX writer. Called once, by MSB, when `vex` is first needed."""
        from pastrocore.super.schedule_vex import ScheduleVEX

        return ScheduleVEX(self)

    def _make_cfx(self):
        """Build the CFX writer. Called once, by MSB, when `cfx` is first needed."""
        from pastrocore.super.schedule_cfx import ScheduleCFX

        return ScheduleCFX(self)

    def get_journal(self) -> Optional[RequestJournal]:
        """Return the record of every request this orchestrator has processed.

        Returns:
            Optional[RequestJournal]: The journal, or None if the orchestrator was built
                without one.

        Notes:
            - Backwards it answers what produced a result: `journal.touching(name)`.
            - Forwards it replays: `manipulator.replay(journal)` runs the session again.
            - `journal.entries` is plain data, so a session writes to a file and comes back
              -- which is what `export(method="journal")` and `compute(method="replay")` do.
        """
        return self._journal