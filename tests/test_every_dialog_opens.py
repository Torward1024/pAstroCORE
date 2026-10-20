"""Every door in the interface opens.

The scan editor could not be opened at all in four released versions, and 1 573 tests passed
throughout. They all built the dialogs directly -- `ScanEditorDialog(observation, ...)` -- and
what was broken was the step before: the tab handing the editor a copy of the scan, made with
a `clone` a scan cannot answer.

So these go the way a person goes. The methods are found rather than listed, which is what
makes this hold for a tab or an editor added later.
"""
import inspect
import json

import pytest

import conftest
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject

#: Which tab opens the editors of which part, and what the part is called in the model.
TABS = {
    "p_tab_telescopes": "get_telescopes",
    "p_tab_sources": "get_sources",
    "p_tab_frequencies": "get_frequencies",
    "p_tab_scans": "get_scans",
}


@pytest.fixture
def opened(project, qt_application, monkeypatch):
    """Answer every dialog and every question without showing one."""
    from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

    seen = []
    monkeypatch.setattr(QDialog, "exec",
                        lambda self: seen.append(type(self).__name__) or QDialog.Rejected)
    for asked in ("information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, asked, staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", "")))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: ("", "")))
    return seen


def doors_of(holder):
    """Return the methods that open an editor, found by what they are called."""
    return sorted(name for name in dir(type(holder))
                  if (name.startswith(("add_", "edit_")) and not name.startswith("_")
                      and callable(getattr(type(holder), name, None))))


def knock(holder, door, named):
    """Call one opener, filling whatever it asks for by the name it asks under.

    Args:
        holder: The tab.
        door (str): The method that opens an editor.
        named (dict): What each parameter name is worth here.
    """
    asked = inspect.signature(getattr(holder, door)).parameters
    missing = [key for key in asked if key not in named]
    if missing:
        raise TypeError(f"{door} asks for {missing}, which this test cannot answer")
    getattr(holder, door)(**{key: named[key] for key in asked})


def tabs_for(project):
    """Build each tab from its own signature, the tabs not agreeing on an order.

    Notes:
        - Built by parameter name rather than by position, so a tab that gains an argument
          is still built here instead of quietly dropping out of the test.
    """
    import importlib

    observation = project.get_observations()[0]
    from pastrocore.paths import shipped_catalog
    from pastrocore.utils.catalogmanager import CatalogManager

    catalogues = CatalogManager()
    for kind in ("telescopes", "sources"):
        catalogues.load(kind, str(shipped_catalog(f"{kind}.json")))
    available = {"observation": observation, "manipulator": ScheduleManipulator(project),
                 "project": project, "parent": None, "catalog_manager": catalogues}
    made = []
    for module, accessor in TABS.items():
        imported = importlib.import_module(f"pastrocore.gui.{module}")
        for name, candidate in vars(imported).items():
            if not (inspect.isclass(candidate) and candidate.__module__ == imported.__name__
                    and name.endswith("Tab")):
                continue
            asked = inspect.signature(candidate.__init__).parameters
            given = {key: available[key] for key in list(asked)[1:] if key in available}
            made.append((name, candidate(**given), accessor))
    return made


def test_every_editor_a_tab_offers_opens(project, opened):
    """One of these would have failed for four releases: the scan editor raised before the
    dialog was built, and nothing opened it the way the table's menu does."""
    failed = []
    for label, tab, accessor in tabs_for(project):
        held = getattr(tab.observation, accessor)().get_items()
        assert held, f"{label} has nothing to edit in this fixture"
        named = {"telescope_name": held[0].name, "source_name": held[0].name,
                 "freq_name": held[0].name, "scan_name": held[0].name}
        for door in doors_of(tab):
            before = len(opened)
            try:
                knock(tab, door, named)
            except Exception as why:                # noqa: BLE001 - collected, then reported
                failed.append(f"{label}.{door}: {type(why).__name__}: {why}")
                continue
            # Counted, not merely survived: a tab catches what its editor raises, logs it and
            # shows a message box, so a door that opens nothing raises nothing either.
            if len(opened) == before:
                failed.append(f"{label}.{door}: opened no dialog")
        tab.deleteLater()

    assert not failed, "these doors do not open:\n  " + "\n  ".join(failed)


def test_the_window_opens_what_the_project_tab_hands_it(project, opened, qt_application):
    """The project tab passes these to the window, so the window is where they are knocked
    on. One opens a dialog and one opens a tab, which is why each is checked for its own
    answer rather than both for a dialog."""
    from pastrocore.app import PAstroCoreMainWindow

    window = PAstroCoreMainWindow()
    window.project = project
    window.manipulator = ScheduleManipulator(project)
    observation = project.get_observations()[0]
    try:
        window.add_observation()
        assert opened, "Add Observation opened no dialog"

        tabs = window.ui.tabContainer.count()
        window.edit_observation(observation.name, observation.get_observation_code())
        assert window.ui.tabContainer.count() > tabs, "editing opened no observation tab"
    finally:
        window.close()
        window.deleteLater()


def test_an_editor_is_actually_shown(project, opened):
    """The guard for this file: if `exec` stopped being how a dialog is shown, every test
    above would pass by opening nothing at all."""
    from pastrocore.gui.p_tab_scans import ScansTab

    observation = project.get_observations()[0]
    tab = ScansTab(observation, ScheduleManipulator(project))
    tab.edit_scan(observation.get_scans().get_items()[0].name)
    tab.deleteLater()

    assert "ScanEditorDialog" in opened, f"nothing was shown; {opened}"
