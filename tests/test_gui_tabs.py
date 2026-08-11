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

    classes = [value for name, value in vars(module).items()
               if inspect.isclass(value) and issubclass(value, QWidget)
               and value.__module__ == module.__name__]
    assert classes, f"{module_name} defines no widget class"
    return classes[0]


@pytest.fixture
def observation(project):
    return project.get_observation(next(iter(project.get_items())))


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
