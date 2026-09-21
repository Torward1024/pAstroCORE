"""The window's own furniture: its toolbar, its keys and its status bar (G11, G12, G13).

The menus were the only way to reach anything: no toolbar, not one keyboard shortcut, and a status
bar that was an empty strip. None of that is about the model, which is why it is tested here rather
than through it -- what is asserted is what a user can reach and what the window tells them.
"""
import logging
import re

import pytest

pytest.importorskip("PySide6")


@pytest.fixture
def listening():
    """The suite quietens the loggers; a test about what the log shows has to turn one back up."""
    from msb_arch.utils.logging_setup import logger

    attached = logging.getLogger(logger.name)
    was = attached.level
    attached.setLevel(logging.INFO)
    yield
    attached.setLevel(was)


@pytest.fixture
def window(qt_application, project):
    """The main window holding the fixture project, built as the application builds it."""
    from pastrocore.app import PAstroCoreMainWindow
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    built = PAstroCoreMainWindow()
    built.project = project
    built.manipulator = ScheduleManipulator(project)
    try:
        yield built
    finally:
        built.status.close()
        built.close()
        built.deleteLater()
        qt_application.processEvents()


def menu_actions(window):
    """Every action the menu bar offers, by name."""
    from PySide6.QtWidgets import QMenu

    found = {}
    for action in window.menuBar().actions():
        menus = [action.menu()] if action.menu() else []
        while menus:
            menu = menus.pop()
            for entry in menu.actions():
                if entry.menu():
                    menus.append(entry.menu())
                elif not entry.isSeparator():
                    found[entry.objectName()] = entry
    return found


# --- G11: a toolbar ---------------------------------------------------------------------------------

def test_the_window_has_a_toolbar_of_the_actions_a_user_reaches_for(window):
    from PySide6.QtWidgets import QToolBar

    toolbar = window.findChild(QToolBar, "mainToolBar")
    assert toolbar is not None, "the window has no toolbar"
    on_it = [action for action in toolbar.actions() if not action.isSeparator()]
    assert len(on_it) >= 10, f"a toolbar of {len(on_it)} is not worth the row it takes"
    for action in on_it:
        assert not action.icon().isNull(), f"{action.objectName()} is on the toolbar without an icon"


def test_every_toolbar_button_says_what_it_does(window):
    """U1: a row of thirteen unlabelled icons is a row of thirteen guesses. The toolbar shows
    the text under the icon, and it is the short one -- a menu says "Export Calculated Data...",
    a button under an icon has room for "Results"."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QToolBar

    toolbar = window.findChild(QToolBar, "mainToolBar")

    assert toolbar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonTextUnderIcon
    unlabelled = [action.objectName() for action in toolbar.actions()
                  if not action.isSeparator() and not action.iconText().strip()]
    assert not unlabelled, f"these toolbar buttons have no label: {unlabelled}"
    long_ones = [action.iconText() for action in toolbar.actions()
                 if not action.isSeparator() and len(action.iconText()) > 12]
    assert not long_ones, f"these labels do not fit under an icon: {long_ones}"


def test_the_explorer_filter_hides_what_does_not_match(window, qt_application):
    """U1: a project of fifty observations is a tree nobody scrolls. What is typed narrows it,
    and a rebuilt tree keeps the filter -- a refresh that shows everything again undoes what the
    user asked for."""
    from PySide6.QtWidgets import QTreeView

    window.update_project_explorer()
    tree = window.findChild(QTreeView, "projectExplorer")
    code = window.project.get_observations()[0].get_observation_code()

    assert window.filter_project_explorer(code[:3]) == 1, "the observation it names is shown"
    assert window.filter_project_explorer("nothing_is_called_this") == 0

    window.ui.explorerFilter.setText("nothing_is_called_this")
    window.update_project_explorer()
    observations = tree.model().index(0, 0, tree.model().index(0, 0))
    assert tree.isRowHidden(0, observations), "a rebuilt tree forgot the filter"


def test_a_toolbar_button_is_the_menu_action_itself(window):
    """Not a copy: an action the window disables has to be unreachable both ways, and a copy on the
    toolbar would go on offering work the menu has already refused."""
    from PySide6.QtWidgets import QToolBar

    toolbar = window.findChild(QToolBar, "mainToolBar")
    from_menu = menu_actions(window)
    for action in toolbar.actions():
        if action.isSeparator():
            continue
        name = action.objectName()
        assert name in from_menu, f"{name} is on the toolbar and in no menu"
        assert action is from_menu[name], f"{name} on the toolbar is a copy of the menu's action"

    calculate = from_menu["actionCalculate"]
    calculate.setEnabled(False)
    try:
        assert not toolbar.widgetForAction(calculate).isEnabled(), "the toolbar offers a disabled action"
    finally:
        calculate.setEnabled(True)


# --- G12: shortcuts ---------------------------------------------------------------------------------

def test_no_two_actions_answer_to_the_same_keys(window):
    taken = {}
    for name, action in menu_actions(window).items():
        for sequence in action.shortcuts():
            keys = sequence.toString()
            assert keys not in taken, f"{keys} is both {taken[keys]} and {name}"
            taken[keys] = name
    assert len(taken) >= 10, f"only {len(taken)} shortcut(s) in the whole window"


def test_the_usual_things_answer_to_the_usual_keys(window):
    """A user's fingers know these before they know the application."""
    from PySide6.QtGui import QKeySequence

    actions = menu_actions(window)
    for name, standard in (("actionNewProject", QKeySequence.StandardKey.New),
                           ("actionOpenProject", QKeySequence.StandardKey.Open),
                           ("actionSaveProject", QKeySequence.StandardKey.Save),
                           ("actionSave_Project_As", QKeySequence.StandardKey.SaveAs),
                           ("actionExit", QKeySequence.StandardKey.Quit)):
        expected = QKeySequence(standard)
        if expected.isEmpty():
            continue                                    # the platform has no key for it
        assert actions[name].shortcut() == expected, (
            f"{name} answers to '{actions[name].shortcut().toString()}', "
            f"not the platform's '{expected.toString()}'")

    assert actions["actionCalculate"].shortcut().toString() == "Ctrl+R"
    assert actions["actionAbout"].shortcut().toString() == "F1"


def test_every_shortcut_is_a_key_sequence_qt_understands(window):
    for name, action in menu_actions(window).items():
        for sequence in action.shortcuts():
            assert not sequence.isEmpty(), f"{name} carries a shortcut Qt could not read"


# --- G13: the status bar -----------------------------------------------------------------------------

def test_the_status_bar_says_what_the_log_says(window, qt_application, listening):
    """Fed by the log rather than by call sites: everything the application already reports arrives
    without anything being wired up for it."""
    from msb_arch.utils.logging_setup import logger

    logger.info("Opened project from somewhere")
    qt_application.processEvents()
    assert window.status.message.text() == "Opened project from somewhere"

    logger.warning("Sources are not among the metadata")
    qt_application.processEvents()
    assert window.status.message.text() == "Sources are not among the metadata"
    assert window.status.message.property("level") == "warning", "a warning is not marked as one"

    logger.error("Failed to save project")
    qt_application.processEvents()
    assert window.status.message.property("level") == "error", "an error is not marked as one"

    logger.debug("counting rows")
    qt_application.processEvents()
    assert window.status.message.text() == "Failed to save project", "debug noise reached the bar"


def test_a_message_from_a_working_thread_reaches_the_bar(window, qt_application, listening):
    """Calculations and saves run off the window's thread, and a widget may only be touched from
    its own. The handler hands the record to a signal, which is what crosses the threads."""
    import threading

    from msb_arch.utils.logging_setup import logger

    threading.Thread(target=lambda: logger.info("Writing OBS_1: uv_coverage")).start()
    for _ in range(50):
        qt_application.processEvents()
        if window.status.message.text() == "Writing OBS_1: uv_coverage":
            break
    assert window.status.message.text() == "Writing OBS_1: uv_coverage"


def test_the_status_bar_shows_what_the_process_holds(window):
    window.status.refresh_memory()
    assert re.fullmatch(r"Memory: \d+(\.\d)? (KB|MB|GB)", window.status.memory.text()), \
        window.status.memory.text()


def test_closing_the_window_stops_it_listening(window, qt_application):
    """A handler left on the logger writes to a label that has been destroyed, which is an access
    violation rather than an exception."""
    from msb_arch.utils.logging_setup import logger

    attached = logging.getLogger(logger.name)
    before = len(attached.handlers)
    window.status.close()
    assert len(attached.handlers) == before - 1
    logger.info("after the window has gone")            # must reach nothing and raise nothing
