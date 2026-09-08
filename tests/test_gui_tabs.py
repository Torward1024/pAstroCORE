"""The visualization tabs, actually driven rather than merely imported.

Written after an edit deleted 851 lines across four of these files -- whole methods with them --
and the whole suite passed. The GUI tests import every module and build the main window, so a
tab whose methods have been destroyed still imports cleanly and still constructs. Nothing called
them, so nothing noticed. It was found by running the application.

These tests construct each tab against the fixture observation and call the methods a user's
first click reaches. They are not about appearance; they are about the code still being there
and still running.
"""
import importlib
import inspect
import pathlib

import pytest

TABS = {
    "p_tab_vis_uv_coverage": "UVVisualizationTab",
    "p_tab_vis_az_el": None,
    "p_tab_vis_sun_angles": None,
    "p_tab_vis_baseline_projections": None,
    "p_tab_vis_beam_pattern": None,
    "p_tab_vis_mollweide": None,
    "p_tab_vis_parallactic": None,
    "p_tab_vis_time_on_source": None,
}


def tab_class(module_name):
    """Return the widget class a tab module defines.

    Notes:
        - Found rather than listed, so a renamed class fails here instead of quietly dropping
          the tab out of these tests.
    """
    module = importlib.import_module(f"pastrocore.gui.{module_name}")
    from PySide6.QtWidgets import QWidget

    # Named in TABS where a module defines more than one -- `p_tab_vis_uv_coverage` holds the
    # base the two baseline plots share as well as the tab itself, and taking the first class
    # found would test the base.
    named = TABS.get(module_name)
    if named:
        widget_class = getattr(module, named, None)
        assert widget_class is not None, f"{module_name} defines no {named}"
        return widget_class

    classes = [value for name, value in vars(module).items()
               if inspect.isclass(value) and issubclass(value, QWidget)
               and value.__module__ == module.__name__]
    assert classes, f"{module_name} defines no widget class"
    return classes[0]


@pytest.fixture
def observation(project):
    return project.observations()[0]


@pytest.mark.parametrize("module_name", sorted(TABS))
def test_a_tab_can_be_built(module_name, project, observation, qt_application):
    """The floor: it constructs against a real observation."""
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    widget = tab_class(module_name)(ScheduleManipulator(project), observation)
    try:
        assert widget is not None
    finally:
        widget.deleteLater()


@pytest.mark.parametrize("module_name", sorted(TABS))
def test_the_methods_a_first_click_reaches_still_run(module_name, project, observation,
                                                     qt_application):
    """What the import-only tests could not see.

    A tab whose methods have been deleted imports cleanly, constructs cleanly, and fails the
    moment anybody uses it. These call the ones a user reaches by selecting a source, which is
    the first thing anyone does in these tabs.
    """
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    widget = tab_class(module_name)(ScheduleManipulator(project), observation)
    try:
        # Named per tab rather than assumed: the beam pattern tab has no sources or scans to
        # choose, so a list that fits the others would either skip it or invent a method for it.
        candidates = ("update_sources", "update_scans", "update_telescopes", "update_baselines",
                      "update_frequencies", "get_selected_source", "_populate_filters",
                      "get_selected_frequencies", "get_selected_telescopes")
        called = []
        for name in candidates:
            method = getattr(widget, name, None)
            if method is None or not callable(method):
                continue
            called.append(name)
            method()                       # must not raise, and must still exist to be called
        assert called, f"{module_name} exposes none of the methods a first click reaches"
    finally:
        widget.deleteLater()


@pytest.mark.parametrize("module_name", sorted(TABS))
def test_a_tab_keeps_the_methods_its_own_signals_are_wired_to(module_name):
    """A deleted method is often still connected to a signal, which raises only when clicked.

    Reading the source for `self.method` in a `connect(...)` and checking the class has it
    catches that without a click.
    """
    import re

    source = (pathlib.Path(__file__).resolve().parent.parent / "pastrocore" / "gui"
              / f"{module_name}.py").read_text(encoding="utf-8")
    widget = tab_class(module_name)

    wired = set(re.findall(r"\.connect\(\s*self\.(\w+)\s*\)", source))
    missing = sorted(name for name in wired if not hasattr(widget, name))
    assert not missing, f"{module_name} connects signals to methods it does not have: {missing}"


@pytest.mark.parametrize("module_name", sorted(TABS))
def test_a_tab_uses_no_name_it_never_defines(module_name):
    """The failure that was reported: `source_name` and `current_checks` undefined, because the
    lines defining them had been deleted along with everything else between two anchors."""
    import ast

    source = (pathlib.Path(__file__).resolve().parent.parent / "pastrocore" / "gui"
              / f"{module_name}.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    problems = []
    for function in [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]:
        assigned, used = set(), []
        for node in ast.walk(function):
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    assigned.add(node.id)
                else:
                    used.append(node.id)
            elif isinstance(node, (ast.For, ast.comprehension)):
                target = getattr(node, "target", None)
                if isinstance(target, ast.Name):
                    assigned.add(target.id)
            elif isinstance(node, ast.arg):
                assigned.add(node.arg)
            elif isinstance(node, ast.ExceptHandler) and node.name:
                assigned.add(node.name)
        for name in ("source_name", "current_checks", "scans", "df", "scan_times"):
            if name in used and name not in assigned:
                problems.append(f"{function.name} uses '{name}' without defining it")

    assert not problems, f"{module_name}: " + "; ".join(problems)


# --- the dialog that creates the tabs -------------------------------------------------------

def test_the_visualize_dialog_can_actually_open_a_tab(project, qt_application):
    """The path none of the tests above covered, and it broke the moment it was changed.

    They build a tab directly; the dialog picks one by the label a user chose, which needs the
    label turned back into a result key. A name that was in scope in one method and not in the
    other raised `vis_key is not defined` for every visualization, and every test passed.
    """
    from PySide6.QtWidgets import QMessageBox

    from pastrocore.gui.p_dialog_visualize import VisualizationDialog
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    dialog = VisualizationDialog(ScheduleManipulator(project))
    try:
        assert dialog.ui.comboBoxVisualizationType.count() > 0, (
            "the fixture holds results, so something must be offered")

        complaints = []
        original = QMessageBox.critical
        QMessageBox.critical = staticmethod(lambda *a, **k: complaints.append(a))
        try:
            for index in range(dialog.ui.comboBoxVisualizationType.count()):
                dialog.ui.comboBoxVisualizationType.setCurrentIndex(index)
                dialog.perform_visualization()
        finally:
            QMessageBox.critical = original

        assert not complaints, f"opening a tab failed: {complaints}"
        assert dialog.ui.tabWidget.count() > 0, "no tab was opened"
    finally:
        dialog.close()
        dialog.deleteLater()


def test_every_offered_visualization_has_a_widget(project, qt_application):
    """The dialog offers what the visualizer can draw and maps each to a widget by hand. If the
    two ever disagree, a user picks something and gets an error box."""
    from pastrocore.gui.p_dialog_visualize import VisualizationDialog
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    manipulator = ScheduleManipulator(project)
    observation = project.observations()[0]

    response = manipulator.compute(obj=observation, method="catalogue", raise_on_error=False)
    catalogue = (response["result"] if isinstance(response, dict) else response) or []
    drawable = {entry["key"] for entry in catalogue if entry["can_plot"]}

    source = pathlib.Path(VisualizationDialog.__module__.replace(".", "/") + ".py")
    text = (pathlib.Path(__file__).resolve().parent.parent / source).read_text(encoding="utf-8")
    mapped = {key for key in drawable if f'"{key}":' in text}

    assert drawable == mapped, (
        f"the visualizer can draw {sorted(drawable - mapped)} but no widget is mapped to them")


# --- the run says what it did (M4) -------------------------------------------------------------

def _outcome():
    """What `compute(method="run")` hands back, in the shape the window renders."""
    return {
        "ran": ["OBS1/time_arrays"],
        "failed": ["OBS1/uv_coverage"],
        "cancelled": False,
        "timings": {"OBS1/time_arrays": 0.25},
        "report": [
            {"step": "OBS1/time_arrays", "observation": "OBS1", "label": "Time Arrays",
             "seconds": 0.25, "outcome": "ok"},
            {"step": "OBS1/uv_coverage", "observation": "OBS1", "label": "UV Coverage",
             "seconds": 0.0, "outcome": "failed"},
        ],
        "summary": {"steps": 1, "failed": 1, "seconds": 0.25, "slowest": "time_arrays",
                    "slowest_seconds": 0.25},
    }


def test_the_report_shows_every_step_and_names_the_failed_one(qt_application):
    """A run used to end in one message box saying everything worked, with the detail in
    `output.log`. A failure has to be visible in the window."""
    from pastrocore.gui.p_dialog_run_report import RunReportDialog

    dialog = RunReportDialog(_outcome())
    table = dialog.ui.tableSteps

    assert table.rowCount() == 2
    shown = {table.item(row, 1).text(): table.item(row, 3).text() for row in range(2)}
    assert shown == {"Time Arrays": "ok", "UV Coverage": "failed"}
    assert "1 failed" in dialog.ui.labelSummary.text()
    assert "0.25" in dialog.ui.labelSummary.text()
    dialog.close()


def test_the_report_can_be_copied_as_text(qt_application):
    """For a bug report, which is the other reason anybody wants this."""
    from pastrocore.gui.p_dialog_run_report import RunReportDialog

    dialog = RunReportDialog(_outcome())
    text = dialog.as_text()

    assert "UV Coverage" in text and "failed" in text
    assert "Time Arrays" in text
    dialog.close()


def test_the_report_outlives_the_dialog_that_showed_it(qt_application, monkeypatch, tmp_path):
    """"Reachable after the run rather than only during it" is the criterion. A run that ended
    twenty minutes ago is exactly when somebody asks which step failed."""
    from pastrocore.app import PAstroCoreMainWindow

    window = PAstroCoreMainWindow()
    try:
        assert window.ui.actionLast_Run_Report.isEnabled() is False, (
            "nothing has run yet, so there is nothing to show"
        )
        window.last_run = _outcome()
        window.ui.actionLast_Run_Report.setEnabled(True)

        shown = {}
        monkeypatch.setattr("pastrocore.gui.p_dialog_run_report.RunReportDialog.exec",
                            lambda self: shown.setdefault("rows", self.ui.tableSteps.rowCount()))
        window.open_last_run_report()
        assert shown.get("rows") == 2
    finally:
        window.close()


# --- the explorer opens what was clicked ------------------------------------------------------

def test_an_observation_with_stale_results_still_opens(qt_application, monkeypatch, tmp_path):
    """Reported from a live session:

        ERROR - Observation with code 'OBS_DEFAULT  • 12 stale' not found

    The explorer labels an observation with how many of its results have gone stale, and the
    click handler looked the observation up by the label. So the moment staleness had anything
    to say, the observation could no longer be opened -- and the label is exactly what tells a
    user to go and look at it.
    """
    import json

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QStandardItem, QStandardItemModel

    import conftest
    from pastrocore.app import PAstroCoreMainWindow
    from pastrocore.super.schedule_project import ScheduleProject

    window = PAstroCoreMainWindow()
    try:
        window.project = ScheduleProject.from_dict(
            json.loads(conftest.FIXTURE.read_text(encoding="utf-8")))
        from pastrocore.super.schedule_manipulator import ScheduleManipulator
        window.manipulator = ScheduleManipulator(window.project)
        observation = window.project.observations()[0]

        model = QStandardItemModel()
        item = QStandardItem(f"{observation.code}  • 12 stale")
        item.setData("observation", Qt.UserRole)
        item.setData(observation.name, Qt.UserRole + 1)
        model.appendRow(item)
        window.ui.projectExplorer.setModel(model)

        opened = {}
        monkeypatch.setattr(window, "open_observation_tab",
                            lambda name, code: opened.update(name=name, code=code))
        window.handle_project_explorer_click(model.indexFromItem(item))

        assert opened.get("code") == observation.code, (
            f"the label was used as the code: {opened!r}")
        assert opened.get("name") == observation.name
    finally:
        window.close()


def test_the_explorer_is_refreshed_after_a_run(qt_application, monkeypatch):
    """"12 stale" stayed on an observation whose results had just been recomputed.

    The explorer is rebuilt when the project changes, and finishing a run is exactly that --
    but the calculation dialog was the one path that never said so. A label telling a user to
    recompute, which survives the recomputation, is worse than no label.
    """
    from pastrocore import app as application
    from pastrocore.app import PAstroCoreMainWindow

    window = PAstroCoreMainWindow()
    try:
        class FinishedDialog:
            outcome = {"ran": ["OBS/times"], "failed": [], "cancelled": False,
                       "timings": {}, "report": [], "summary": {"steps": 1, "failed": 0,
                                                                "seconds": 0.1}}

            def __init__(self, *args, **kwargs):
                self.time_step_updated = _Signal()

            def exec(self):
                return 1

        class _Signal:
            def connect(self, *args, **kwargs):
                return None

        monkeypatch.setattr("pastrocore.gui.p_dialog_calculations.CalculationDialog",
                            FinishedDialog)
        monkeypatch.setattr(window, "open_last_run_report", lambda: None)

        refreshed = []
        monkeypatch.setattr(window, "update_project_explorer",
                            lambda: refreshed.append(True))
        window.project_updated.connect(window.update_project_explorer)

        window.open_calculation_dialog()
        assert refreshed, "the explorer still shows what the run has just changed"
    finally:
        window.close()


def test_importing_a_frequency_from_a_file_works(qt_application, project, tmp_path):
    """`load` returns the object it read; this path still asked it for `["object"]`, a shape
    that stopped existing when the contract became MSB's own.

    No test covered the frequency tab's import, so it raised `NotFoundError: Attribute 'object'
    not found in IF` in the one place a user would meet it. Found by the ratchet that forbids
    unwrapping a response by hand.
    """
    from pastrocore.base.frequencies import IF
    from pastrocore.gui.p_tab_frequencies import FrequenciesTab
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    manipulator = ScheduleManipulator(project)
    observation = project.observations()[0]
    path = tmp_path / "if.pastrod"
    # A band that does not overlap what the observation already has: importing a copy of an
    # existing one is refused, and rightly -- two IFs covering the same range is a mistake.
    manipulator.save(obj=IF(name="IF_IMPORTED", frequency=43000.0, bandwidth=64.0),
                     path=str(path))

    before = len(observation.get_frequencies().get_items())
    tab = FrequenciesTab(observation, manipulator)
    try:
        from PySide6.QtWidgets import QFileDialog

        original = QFileDialog.getOpenFileName
        QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(path), ""))
        try:
            tab.import_new_if()
        finally:
            QFileDialog.getOpenFileName = original

        after = observation.get_frequencies().get_items()
        assert len(after) == before + 1, "the imported frequency did not arrive"
        assert all(isinstance(item, IF) for item in after)
    finally:
        tab.close()


@pytest.mark.parametrize("module_name", sorted(TABS))
def test_a_tab_actually_draws(module_name, project, observation, qt_application):
    """Building is the floor; this is the point of the tab.

    Every one of them shared nine methods and no two were byte-identical, so folding them onto
    one base was a rewrite rather than a lift. Constructing proves nothing about that: a tab
    that silently draws a blank canvas builds perfectly well.
    """
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    manipulator = ScheduleManipulator(project)
    manipulator.compute(obj=observation, method="run", time_step=600.0, recalculate=True,
                        raise_on_error=False,
                        calculations=["uv_coverage", "az_el", "sun_angles", "time_on_source",
                                      "parallactic_angle", "beam_pattern",
                                      "baseline_projections", "mollweide_tracks"])

    widget = tab_class(module_name)(manipulator, observation)
    try:
        assert widget.canvas is not None, f"{module_name} built but drew nothing"
        assert widget.figure is not None
    finally:
        widget.close()
        widget.deleteLater()


@pytest.mark.parametrize("module_name", sorted(TABS))
def test_a_tab_declares_what_it_draws_rather_than_implementing_it(module_name):
    """What varies between the tabs is a declaration now: which form, which result, which
    filters. A tab that reimplements the shared machinery has drifted back."""
    from pastrocore.gui.p_tab_vis_base import VisualizationTab

    widget_class = tab_class(module_name)

    assert issubclass(widget_class, VisualizationTab), f"{module_name} is not on the base"
    assert widget_class.FORM is not None, f"{module_name} declares no form"
    assert widget_class.STORE_KEY, f"{module_name} declares no result to read"


def test_redrawing_reuses_the_canvas_instead_of_rebuilding_it(project, observation,
                                                              qt_application):
    """A tab redraws whenever a filter moves, so anything it leaves behind is left behind
    hundreds of times in a session.

    Rebuilding the canvas per redraw built a `NavigationToolbar` per redraw, which is ten
    `QAction`s each -- 400 of them over 40 redraws, because a widget's `deleteLater` is
    scheduled rather than done. Measured: 60 redraws went from 14.60 s and +89.7 MB to 5.80 s
    and +10.2 MB.

    Checked on identity rather than on a count of objects, because a count is a fact about the
    whole process and the suite has other windows in it.
    """
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    manipulator = ScheduleManipulator(project)
    manipulator.compute(obj=observation, method="run", time_step=600.0, recalculate=True,
                        raise_on_error=False, calculations=["uv_coverage"])

    widget = tab_class("p_tab_vis_uv_coverage")(manipulator, observation)
    try:
        widget.update_visualization()
        canvas, toolbar = widget.canvas, widget.toolbar
        assert canvas is not None, "nothing was drawn, so there is nothing to check"

        for _ in range(5):
            widget.update_visualization()
            qt_application.processEvents()

        assert widget.canvas is canvas, "the canvas was rebuilt"
        assert widget.toolbar is toolbar, "the toolbar was rebuilt, and it is ten QActions"
    finally:
        widget.close()
        widget.deleteLater()


def test_no_figure_is_replaced_at_all(project, observation, qt_application):
    """The tab owns one figure and asks the visualizer to draw *into* it, so a redraw creates
    nothing to let go of.

    Swapping a new `Figure` into an existing canvas was the first attempt. It stopped the
    figures accumulating -- a figure holds its canvas and the canvas holds it back, and each
    has a C++ half whose deletion is only scheduled, so the ring outlived the collector at
    about 1.5 MB a redraw -- but `canvas.figure = ...` is not something matplotlib supports,
    and the navigation toolbar went on referring to axes that had been cleared.

    This was written, measured *wrongly*, reverted, and put back. The measurement that
    condemned it ran while three copies of this suite were on the same machine: 60 redraws
    "took 280 s". Measured alone, back to back in one process, the two designs are 5.04 s and
    5.31 s for 60 redraws and both grow by 0.1 MB. **A number taken on a busy machine is not a
    number.**
    """
    import gc

    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    manipulator = ScheduleManipulator(project)
    manipulator.compute(obj=observation, method="run", time_step=600.0, recalculate=True,
                        raise_on_error=False, calculations=["uv_coverage"])

    widget = tab_class("p_tab_vis_uv_coverage")(manipulator, observation)
    try:
        widget.update_visualization()
        figure = widget.figure
        gc.collect(2)
        before = sum(1 for o in gc.get_objects() if type(o).__name__ == "Figure")

        for _ in range(5):
            widget.update_visualization()
            qt_application.processEvents()

        assert widget.figure is figure, "the tab's figure was replaced"
        assert widget.canvas.figure is figure, "the canvas is showing something else"
        gc.collect(2)
        after = sum(1 for o in gc.get_objects() if type(o).__name__ == "Figure")
        assert after <= before, f"redrawing left figures behind: {before} -> {after}"
    finally:
        widget.close()
        widget.deleteLater()


def test_the_editor_shows_what_the_band_would_cover(qt_application):
    """`frequency` is an edge, not a middle. 4828 upper and 4844 lower are the same 16 MHz, and
    a project holding both is refused with a message about a rule rather than about the two
    numbers on screen -- so the span is shown while the band is being edited, before Save."""
    from pastrocore.base.frequencies import IF
    from pastrocore.gui.p_dialog_edit_if import IFEditorDialog

    band = IF(name="C", frequency=4828.0, bandwidth=16.0, sidebands=["U"])
    dialog = IFEditorDialog(band)
    try:
        assert dialog.ui.coverageDisplay.text() == "4828.000 - 4844.000"

        # Tick the lower sideband as well: one setting, either side of its sky frequency.
        for index in range(dialog.ui.sidebandsList.count()):
            dialog.ui.sidebandsList.item(index).setSelected(True)

        assert dialog.ui.coverageDisplay.text() == "4812.000 - 4844.000"
    finally:
        dialog.close()
        dialog.deleteLater()


def test_the_editor_writes_the_sidebands_back(qt_application):
    """Showing them and not saving them would be worse than not showing them."""
    from pastrocore.base.frequencies import IF
    from pastrocore.gui.p_dialog_edit_if import IFEditorDialog

    band = IF(name="C", frequency=4828.0, bandwidth=16.0, polarizations=["RCP"],
              sidebands=["U"])
    dialog = IFEditorDialog(band)
    try:
        for index in range(dialog.ui.sidebandsList.count()):
            dialog.ui.sidebandsList.item(index).setSelected(True)
        saved = dialog.get_if_object()

        assert set(saved.get_sidebands()) == {"U", "L"}
        assert saved.get_band() == (4812.0, 4844.0)
        assert saved.get_channel_count() == 2      # one polarization, two sidebands
    finally:
        dialog.close()
        dialog.deleteLater()


def test_a_band_with_no_sideband_cannot_be_saved(qt_application, monkeypatch):
    """The one thing the dialog refuses itself, because there is no sensible default to fall
    back to: a band that says nothing about which way it runs is not a band."""
    from PySide6.QtWidgets import QMessageBox

    from pastrocore.base.frequencies import IF
    from pastrocore.gui.p_dialog_edit_if import IFEditorDialog

    complaints = []
    monkeypatch.setattr(QMessageBox, "critical",
                        lambda *args, **kwargs: complaints.append(args[2]))

    dialog = IFEditorDialog(IF(name="C", frequency=4828.0, bandwidth=16.0))
    try:
        dialog.clear_selections()
        dialog.accept()

        assert complaints, "it was saved without a sideband"
        assert dialog.result() != dialog.DialogCode.Accepted
    finally:
        dialog.close()
        dialog.deleteLater()


# --- the catalog browsers -------------------------------------------------------------------

@pytest.mark.parametrize("module_name,class_name,rows", [
    ("p_dialog_sources_catalog", "SourcesCatalogDialog", "source_catalog"),
    ("p_dialog_telescopes_catalog", "TelescopesCatalogDialog", "telescope_catalog"),
])
@pytest.mark.parametrize("allow_selection", [False, True])
def test_a_catalog_browser_opens_and_fills(module_name, class_name, rows, allow_selection,
                                           project, qt_application):
    """Reported from a live session, both of them:

        AttributeError: 'SourcesCatalogDialog' object has no attribute 'manipulator'

    The lookup was moved onto the orchestrator and the dialog was never given one, so **every
    way of opening either catalog raised** -- from the Options menu, from the sources tab, from
    the telescopes tab, and from Generate Observations. Nothing constructed these dialogs, so
    nothing noticed.

    Both selection modes, because `allow_selection` builds a different set of buttons and is
    the mode three of the four callers use.
    """
    import importlib

    from pastrocore.paths import existing_or_shipped
    from pastrocore.utils.catalogmanager import CatalogManager

    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    catalogs = CatalogManager(existing_or_shipped("", "sources.dat"),
                              existing_or_shipped("", "telescopes.dat"))
    dialog_class = getattr(importlib.import_module(f"pastrocore.gui.{module_name}"), class_name)

    dialog = dialog_class(catalogs, ScheduleManipulator(project),
                          allow_selection=allow_selection)
    try:
        assert dialog.model.rowCount() > 0, "the shipped catalogue is not empty"
        assert dialog.model.rowCount() == len(getattr(catalogs, rows).get_items())
    finally:
        dialog.close()
        dialog.deleteLater()


def test_a_catalog_browser_is_given_the_orchestrator_rather_than_making_one(project):
    """One entry point is the whole point of the framework, so a dialog that cannot reach the
    orchestrator is given it -- it does not build a second one. Checked on the signature
    because building one would work, and quietly."""
    import inspect as inspection

    from pastrocore.gui.p_dialog_sources_catalog import SourcesCatalogDialog
    from pastrocore.gui.p_dialog_telescopes_catalog import TelescopesCatalogDialog

    for dialog_class in (SourcesCatalogDialog, TelescopesCatalogDialog):
        parameters = inspection.signature(dialog_class.__init__).parameters
        assert "manipulator" in parameters, f"{dialog_class.__name__} takes no orchestrator"

        source = inspection.getsource(dialog_class)
        assert "ScheduleManipulator(" not in source, (
            f"{dialog_class.__name__} builds an orchestrator of its own")


# --- the recently-opened list (G4) -----------------------------------------------------------

def test_a_project_opened_is_remembered_and_survives_a_restart(qt_application, monkeypatch,
                                                               tmp_path, project):
    """G4's exit criterion, both halves. The list is a *setting*, so surviving a restart is
    surviving being written and read back rather than something the window holds."""
    from pastrocore.app import PAstroCoreMainWindow
    from pastrocore.super.schedule_project import ScheduleProject

    settings = tmp_path / "settings.json"
    monkeypatch.setattr("pastrocore.app.settings_file", lambda: settings)

    where = tmp_path / "a_project"
    project.save(str(where))
    assert ScheduleProject.is_directory_project(str(where))

    window = PAstroCoreMainWindow()
    try:
        # Reachable, not merely built: the submenu was declared and never added to File, so it
        # was filled correctly and never appeared. Driving  on its own is
        # what let that through.
        assert "Recent Projects" in [a.text() for a in window.ui.menuFile.actions()]

        window.open_recent(str(where))
        assert window.settings["recent_projects"][0] == str(where)
        assert [a.text() for a in window.ui.menuRecent_Projects.actions()] == [str(where)]
    finally:
        window.close()

    # The restart: a second window reads the settings the first one wrote.
    again = PAstroCoreMainWindow()
    try:
        assert str(where) in again.settings.get("recent_projects", [])
        assert [a.text() for a in again.ui.menuRecent_Projects.actions()] == [str(where)]
    finally:
        again.close()


def test_a_project_that_has_gone_is_removed_when_it_is_clicked(qt_application, monkeypatch,
                                                               tmp_path):
    """The other half of the criterion. Checked when clicked rather than when the menu opens:
    ten paths on a network share is a pause with no cause a user can see."""
    from PySide6.QtWidgets import QMessageBox

    from pastrocore.app import PAstroCoreMainWindow

    settings = tmp_path / "settings.json"
    monkeypatch.setattr("pastrocore.app.settings_file", lambda: settings)
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

    window = PAstroCoreMainWindow()
    try:
        gone = str(tmp_path / "was_a_project")
        window.settings["recent_projects"] = [gone]
        window.rebuild_recent_menu()
        assert [a.text() for a in window.ui.menuRecent_Projects.actions()] == [gone]

        window.open_recent(gone)

        assert gone not in window.settings["recent_projects"]
        assert [a.text() for a in window.ui.menuRecent_Projects.actions()] == \
            ["Nothing opened yet"]
    finally:
        window.close()
