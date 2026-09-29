"""The dialogs an operation is asked for in: calculate, export, generate.

They hold no logic of their own -- what a calculation takes, what a plan costs, what units a
baseline is measured in are all the backend's answers. What is asserted here is that they ask
before they destroy, tell the window when they have, offer only what is asked for, and offer
what the model names rather than a list of their own.
"""
import pytest

pytest.importorskip("PySide6")

from pastrocore.super.schedule_manipulator import ScheduleManipulator


@pytest.fixture
def calculations(project, qt_application):
    """The calculation dialog on the fixture project."""
    from pastrocore.gui.p_dialog_calculations import CalculationDialog

    dialog = CalculationDialog(ScheduleManipulator(project))
    yield dialog
    dialog.deleteLater()


def answer(monkeypatch, with_what):
    """Make the next question answer itself, and record that it was asked."""
    from PySide6.QtWidgets import QMessageBox

    asked = []
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *arguments, **keywords: (asked.append(arguments[2]),
                                                                     with_what)[1]))
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *arguments, **keywords: None))
    return asked


def test_clearing_the_results_asks_first(calculations, project, monkeypatch):
    """Every other way of throwing something away in this application asks -- an observation,
    a catalogue entry, the results a project is closed on. This button took a day of
    calculation on one click and said "Success" afterwards."""
    from PySide6.QtWidgets import QMessageBox

    asked = answer(monkeypatch, QMessageBox.No)
    held = len(project.get_observations()[0].calculated_data)
    assert held, "the fixture observation has no results, so this proves nothing"

    calculations.clear_selected_data()

    assert asked, "the results were thrown away without a word"
    assert len(project.get_observations()[0].calculated_data) == held, "and thrown away anyway"


def test_clearing_the_results_tells_the_window(calculations, project, monkeypatch):
    """The explorer's labels are read from the project, and the window refreshes them after a
    run for exactly this reason -- "the label that sent the user here to recompute survived the
    recomputation". After a clear it heard nothing, and went on listing results that were gone.
    """
    from PySide6.QtWidgets import QMessageBox

    answer(monkeypatch, QMessageBox.Yes)
    told = []
    calculations.project_changed.connect(lambda: told.append(True))

    calculations.clear_selected_data()

    assert not project.get_observations()[0].calculated_data, "nothing was cleared"
    assert told, "the window was not told the project had changed"


def test_unticking_a_calculation_stops_offering_what_it_takes(calculations):
    """The dialog offers exactly the parameters the selected calculations take -- in one
    direction. `handle_calc_selection` returned before refreshing for anything unticked, and
    for anything with no prerequisites, so Clear All left every box enabled and a detection
    threshold offered to nothing at all."""
    assert calculations.ui.thresholdSpin.isEnabled(), "nothing takes a threshold here"

    calculations.clear_all_calcs()

    assert not calculations.ui.thresholdSpin.isEnabled(), (
        "a threshold is offered with no calculation selected")


def test_a_third_kind_of_observation_would_be_offered_without_a_form_being_touched(
        project, qt_application, monkeypatch):
    """The forms carry the two so they are not empty in Designer, and one that offers a choice
    replaces them at run time from the model's own list -- because "a list in a form is a
    second place for the answer to live, and the two disagree the first time one changes".
    The generation dialog never replaced them, so its list was the form's."""
    from pastrocore.gui import p_dialog_add_observation, p_dialog_generate_observations
    from pastrocore.gui import p_tab_observation
    from pastrocore.paths import existing_or_shipped
    from pastrocore.utils.catalogmanager import CatalogManager

    invented = ("VLBI", "SINGLE_DISH", "PULSAR_TIMING")
    for module in (p_dialog_add_observation, p_dialog_generate_observations, p_tab_observation):
        monkeypatch.setattr(module, "OBSERVATION_TYPES", invented)

    catalogs = CatalogManager(existing_or_shipped("", "sources.json"),
                              existing_or_shipped("", "telescopes.json"))
    core = ScheduleManipulator(project)
    combos = []
    built = [p_dialog_generate_observations.GenerateObservationsDialog(project, core, catalogs),
             p_dialog_add_observation.AddObservationDialog(core)]
    combos = [built[0].ui.observationTypeCombo, built[1].ui.combo_obs_type]
    try:
        for combo in combos:
            offered = [combo.itemText(index) for index in range(combo.count())]
            assert offered == list(invented), f"a form offers {offered} of its own"
    finally:
        for dialog in built:
            dialog.deleteLater()


@pytest.mark.parametrize("tab,container,editor", [
    ("p_tab_telescopes:TelescopesTab", "get_telescopes", "TelescopeEditorDialog"),
    ("p_tab_sources:SourcesTab", "get_sources", "SourceEditorDialog"),
], ids=["telescopes", "sources"])
def test_an_editor_is_given_a_copy_of_what_the_observation_holds(tab, container, editor,
                                                                 project, qt_application,
                                                                 monkeypatch):
    """The catalogue dialog hands its editor `held.clone()` and says why: an editor "writes
    what it shows into the object it was given before its own checks run, so an edit it
    refused, then cancelled, stayed in the catalogue". The four observation tabs handed over
    the object the observation holds."""
    import importlib

    from PySide6.QtWidgets import QDialog

    module_name, class_name = tab.split(":")
    module = importlib.import_module(f"pastrocore.gui.{module_name}")
    widget_class = getattr(module, class_name)

    class Editor:
        """Writes into whatever it was handed, as every one of these does, and is cancelled."""

        def __init__(self, *arguments, **keywords):
            self.subject = keywords.get("telescope") or keywords.get("source_obj")
            self.subject.set({"name": self.subject.name})   # touched, then abandoned
            self.subject.isactive = not self.subject.isactive

        def exec(self):
            return QDialog.Rejected

    monkeypatch.setattr(module, editor, Editor)
    observation = project.get_observations()[0]
    core = ScheduleManipulator(project)
    held = getattr(observation, container)().get_items()[0]
    was = held.isactive
    needs_catalog = module_name in ("p_tab_sources", "p_tab_telescopes")
    if needs_catalog:
        from pastrocore.paths import existing_or_shipped
        from pastrocore.utils.catalogmanager import CatalogManager
        widget = widget_class(observation, core,
                              CatalogManager(existing_or_shipped("", "sources.json"),
                                             existing_or_shipped("", "telescopes.json")))
    else:
        widget = widget_class(observation, core)
    try:
        getattr(widget, f"edit_{container.replace('get_', '')[:-1]}")(held.name)

        assert held.isactive == was, "a cancelled edit changed what the observation holds"
    finally:
        widget.close()
        widget.deleteLater()


def test_the_units_a_baseline_is_measured_in_are_named_once(project, qt_application):
    """Two places offered them and spelled the same one two ways -- `earth diameters` from the
    tab, `earth_diameters` from the export dialog -- and the baseline plot labels its axis with
    whichever string it was handed, so one plot came out with two different labels depending on
    which door it was drawn from."""
    from pastrocore.gui.p_dialog_export_calculated_data import ExportCalculatedDataDialog
    from pastrocore.gui.p_tab_vis_uv_coverage import UVVisualizationTab
    from pastrocore.super.schedule_visualizer import UV_UNITS

    core = ScheduleManipulator(project)
    observation = project.get_observations()[0]
    export = ExportCalculatedDataDialog(core)
    tab = UVVisualizationTab(core, observation)
    try:
        from_export = [export.ui.cmbUnits.itemData(index)
                       for index in range(export.ui.cmbUnits.count())]
        from_tab = [tab.ui.comboBox_2.itemData(index)
                    for index in range(tab.ui.comboBox_2.count())]

        assert from_export == list(UV_UNITS), f"the export offers {from_export}"
        assert from_tab == list(UV_UNITS), f"the tab offers {from_tab}"
        assert tab.get_selected_units() in UV_UNITS
    finally:
        tab.deleteLater()
        export.deleteLater()


def test_a_baseline_plot_is_labelled_the_same_whichever_door_it_came_through(project):
    """It put the request's `units` string straight on its axis."""
    from pastrocore.super.schedule_visualizer import UV_UNITS, uv_units

    for spelling in ("earth_diameters", "Earth Diameters", "earth diameters"):
        assert uv_units(spelling) == "earth_diameters", f"{spelling!r} is not read as one unit"
    assert uv_units("wavelengths") == "wavelengths"
    assert uv_units("furlongs") == "wavelengths", "an unknown unit is not silently another one"
    assert UV_UNITS["earth_diameters"]["axis"] == "xED"
