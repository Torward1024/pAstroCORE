"""Exporting and drawing the results about a spacecraft.

Three things were wrong at once, and each hid the next: nothing drew these two results, the
exporter held its own list of what could be drawn, and the call into the visualizer named an
attribute that does not exist -- so picture export raised for *every* calculation and was
reported as nothing written.
"""
import json
import os

import pytest
from PySide6.QtCore import Qt

from pastrocore.base.telescopes import SpaceTelescope
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject

import conftest


@pytest.fixture
def tracked():
    """The fixture observation with a spacecraft, and both spacecraft results computed."""
    project = ScheduleProject.from_dict(json.loads(conftest.FIXTURE.read_text(encoding="utf-8")))
    observation = project.observations()[0]
    scan = observation.get_scans().get_active_items()[0]
    observation.get_telescopes().add(SpaceTelescope(
        code="RADIO", name="RadioAstron", use_kep=True,
        kepler_elements={"a": 2.5e7, "e": 0.01, "i": 63.4, "raan": 30.0, "argp": 270.0,
                         "nu": 0.0, "epoch": scan.get_start(), "mu": 3.986004418e14}))

    manipulator = ScheduleManipulator(project)
    for method in ("telescope_az_el", "telescope_visibility"):
        manipulator.calculate(observation, method=method, target_telescope="RADIO",
                              time_step=300.0, recalculate=True, raise_on_error=False)
    return manipulator, observation


def test_both_results_can_be_drawn(tracked):
    """The catalogue is what the dialogs read, so this is what decides whether they appear."""
    manipulator, observation = tracked
    catalogue = {entry["key"]: entry for entry in
                 manipulator.compute(obj=observation, method="catalogue")}

    assert catalogue["telescope_az_el"]["can_plot"] is True
    assert catalogue["telescope_visibility"]["can_plot"] is True


def test_drawing_one_produces_a_file(tracked, tmp_path):
    manipulator, observation = tracked

    for key in ("telescope_az_el", "telescope_visibility"):
        target = tmp_path / f"{key}.png"
        result = manipulator.visualize(obj=observation, plot_type=key, output_file=str(target),
                                       dpi=76, raise_on_error=False)
        assert result["status"] is True, key
        assert target.exists(), key
        assert result["result"]["telescopes"] > 0, key


def test_exporting_them_writes_text_and_pictures(tracked, tmp_path):
    manipulator, observation = tracked
    manipulator.export(observation, export_path=str(tmp_path),
                       calc_types=["telescope_az_el", "telescope_visibility"],
                       export_data=True, export_vis=True)

    written = sorted(path.name for path in tmp_path.iterdir())
    assert written == ["OBS_DEFAULT_telescope_az_el.png",
                       "OBS_DEFAULT_telescope_az_el.txt",
                       "OBS_DEFAULT_telescope_visibility.png",
                       "OBS_DEFAULT_telescope_visibility.txt"]


def test_a_spacecraft_result_is_drawn_once_rather_than_once_per_source(tracked, tmp_path):
    """Whether a result is per source is read from its columns: these name a target, not a
    source, so one picture covers the observation."""
    manipulator, observation = tracked
    manipulator.export(observation, export_path=str(tmp_path), calc_types=["telescope_az_el"],
                       export_data=False, export_vis=True)

    assert [path.name for path in tmp_path.iterdir()] == ["OBS_DEFAULT_telescope_az_el.png"]


def test_exporting_an_ordinary_plot_still_works(tracked, tmp_path):
    """The attribute error in the exporter broke picture export for everything, not only for
    the spacecraft results."""
    manipulator, observation = tracked
    manipulator.export(observation, export_path=str(tmp_path), calc_types=["az_el"],
                       export_data=False, export_vis=True)

    written = [path.name for path in tmp_path.iterdir()]
    assert written and all(name.endswith(".png") for name in written)


def test_what_can_be_drawn_is_not_a_list_anyone_maintains():
    """A plot that exists is offered. Three tables agreeing about it is what went wrong."""
    import pathlib

    source = pathlib.Path(__file__).resolve().parent.parent
    exporter = (source / "pastrocore" / "super" / "schedule_data.py").read_text(encoding="utf-8")
    visualizer = (source / "pastrocore" / "super" / "schedule_visualizer.py").read_text(
        encoding="utf-8")

    assert "VISUALIZABLE = (" not in exporter, "the exporter is listing plots again"
    assert '"uv_coverage": self._visualize_uv_coverage' not in visualizer, (
        "the visualizer is listing its own handlers again")


def test_both_tabs_open_and_draw(tracked, qt_application):
    """The dialog maps a result to a widget by hand, so a plot that exists without a tab is a
    user picking something and getting an error box."""
    from pastrocore.gui.p_tab_vis_spacecraft import (SpacecraftPointingVisualizationTab,
                                                     SpacecraftVisibilityVisualizationTab)

    manipulator, observation = tracked
    for tab_class in (SpacecraftPointingVisualizationTab, SpacecraftVisibilityVisualizationTab):
        tab = tab_class(manipulator, observation)
        assert tab.get_selected_target() == "RADIO", tab_class.__name__
        assert tab.get_selected_scans(), tab_class.__name__
        assert tab.get_selected_telescopes() == ["ALMA", "APEX"], tab_class.__name__
        assert tab.canvas is not None, f"{tab_class.__name__} drew nothing"
        tab.close()


def test_scan_times_narrows_by_whatever_the_result_holds(tracked):
    """A result about a spacecraft has no source_name, so the filter is read from the frame
    rather than assumed."""
    manipulator, observation = tracked

    by_target = manipulator.export(observation, method="scan_times",
                                   key="telescope_az_el", target_code="RADIO")
    assert by_target and all("scan_name" in entry for entry in by_target)

    nothing = manipulator.export(observation, method="scan_times",
                                 key="telescope_az_el", target_code="NOSUCH")
    assert nothing == []


# --- asking what to point at ---------------------------------------------------------------

def test_the_dialog_learns_which_calculations_need_a_target(tracked, qt_application):
    """Read from the catalogue, which reads it from the result's columns. A list here is what
    goes stale when a calculation is added."""
    from pastrocore.gui.p_dialog_calculations import CalculationDialog

    manipulator, _ = tracked
    dialog = CalculationDialog(manipulator, time_step=600)

    assert dialog._needs_target == {"telescope_az_el", "telescope_visibility"}
    dialog.close()


def test_one_spacecraft_is_chosen_without_asking(tracked, qt_application):
    from pastrocore.gui.p_dialog_calculations import CalculationDialog

    manipulator, observation = tracked
    dialog = CalculationDialog(manipulator, time_step=600)

    assert dialog._ask_for_target([observation], ["telescope_az_el"]) == "RADIO"
    dialog.close()


def test_several_spacecraft_are_offered(tracked, qt_application, monkeypatch):
    from PySide6.QtWidgets import QInputDialog

    from pastrocore.base.telescopes import SpaceTelescope
    from pastrocore.gui.p_dialog_calculations import CalculationDialog

    manipulator, observation = tracked
    scan = observation.get_scans().get_active_items()[0]
    observation.get_telescopes().add(SpaceTelescope(
        code="SECOND", name="Another", use_kep=True,
        kepler_elements={"a": 3.0e7, "e": 0.01, "i": 51.0, "raan": 10.0, "argp": 90.0,
                         "nu": 0.0, "epoch": scan.get_start(), "mu": 3.986004418e14}))

    offered = {}

    def choose(parent, title, label, items, current, editable):
        offered["items"] = list(items)
        return "SECOND", True

    monkeypatch.setattr(QInputDialog, "getItem", staticmethod(choose))
    dialog = CalculationDialog(manipulator, time_step=600)

    assert dialog._ask_for_target([observation], ["telescope_az_el"]) == "SECOND"
    assert offered["items"] == ["RADIO", "SECOND"]
    dialog.close()


def test_no_spacecraft_refuses_rather_than_computing_nothing(qt_application, monkeypatch):
    """What the reported log showed: the calculation ran, said it had nothing to point at, and
    finished in a millisecond having produced nothing."""
    from PySide6.QtWidgets import QMessageBox

    from pastrocore.gui.p_dialog_calculations import CalculationDialog

    project = ScheduleProject.from_dict(json.loads(conftest.FIXTURE.read_text(encoding="utf-8")))
    observation = project.observations()[0]
    manipulator = ScheduleManipulator(project)

    warned = {}
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda parent, title, text, *rest: warned.update(text=text)))

    dialog = CalculationDialog(manipulator, time_step=600)
    assert dialog._ask_for_target([observation], ["telescope_az_el"]) is None
    assert "no space telescope" in warned["text"].lower()
    dialog.close()


def test_running_from_the_dialog_passes_the_target(tracked, qt_application, monkeypatch):
    """The test the first fix lacked, and the reason it did not work.

    The list shows labels, the catalogue speaks keys, and the fix compared one against the
    other -- so nothing was found to need a target and the calculation ran with none, exactly
    as the reported log showed.
    """
    from pastrocore.gui import p_dialog_calculations
    from pastrocore.gui.p_dialog_calculations import CalculationDialog

    manipulator, observation = tracked
    started = {}

    class CapturedThread:
        def __init__(self, manipulator, targets, calc_types, params):
            started["calc_types"] = list(calc_types)
            started["params"] = params
            self.progress = self.finished = self.error = _Signal()

        def start(self):
            started["started"] = True

    class _Signal:
        def connect(self, *args, **kwargs):
            return None

    monkeypatch.setattr(p_dialog_calculations, "CalculationThread", CapturedThread)
    monkeypatch.setattr(p_dialog_calculations, "ProgressDialog",
                        lambda parent=None: _FakeProgress())

    dialog = CalculationDialog(manipulator, time_step=600)
    for index in range(dialog.ui.targetList.count()):
        item = dialog.ui.targetList.item(index)
        item.setCheckState(Qt.Checked if item.data(Qt.UserRole) is observation else Qt.Unchecked)
    for index in range(dialog.ui.calcList.count()):
        item = dialog.ui.calcList.item(index)
        wanted = item.data(Qt.UserRole + 1) in ("telescope_az_el", "telescope_visibility")
        item.setCheckState(Qt.Checked if wanted else Qt.Unchecked)

    dialog.run_calculation()

    assert started.get("started") is True
    for label, given in started["params"].items():
        assert given.get("target_telescope") == "RADIO", f"{label} was run with no target"
    dialog.close()


class _FakeProgress:
    """Stands in for the modal progress dialog, which would block the suite."""

    class _Button:
        clicked = property(lambda self: _FakeProgress._Signal())

    class _Signal:
        def connect(self, *args, **kwargs):
            return None

    def __init__(self):
        self.ui = type("ui", (), {"pushButtonCancel": type("b", (), {"clicked": _FakeProgress._Signal()})()})()

    def update_progress(self, *args, **kwargs):
        return None

    def show(self):
        return None
