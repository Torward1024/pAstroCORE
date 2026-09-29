"""The project's own tab: the table of observations, its search, and its context menu.

425 lines with nothing holding them. What is asserted is what the table shows, what the search
finds, and that the menu opens on a row the model cannot answer for -- which is where an
`except` that logged and then carried on had left a name unbound.
"""
import pytest

pytest.importorskip("PySide6")

from pastrocore.super.schedule_manipulator import ScheduleManipulator


@pytest.fixture
def tab(project, qt_application):
    """The project tab, filled, built the way the window builds it."""
    from pastrocore.gui.p_tab_project import ProjectInfoTab

    widget = ProjectInfoTab(ScheduleManipulator(project))
    widget.update_tab()
    yield widget
    widget.close()
    widget.deleteLater()


def test_the_table_shows_the_observations_the_project_holds(tab, project):
    assert tab.model.rowCount() == len(project.get_observations())


def test_the_search_takes_a_code_rather_than_a_pattern(tab, project):
    """An observation code is whatever its author typed. Handed to the table as a regular
    expression, a `+` in it was one-or-more and an unclosed bracket emptied the table."""
    tab.manipulator.configure(project.get_observations()[0], set={"params": {"code": "EVN+N26"}})
    tab.update_tab()
    code = tab.model.item(0, 3).text()
    assert code == "EVN+N26", "the code the rest of this test is about is not on the row"

    tab.handle_search_text_changed(code)
    assert tab.proxy_model.rowCount() == 1, "searching for a code found no row carrying it"

    tab.handle_search_text_changed("(")
    assert tab.proxy_model.rowCount() == 0, "an unclosed bracket is not a code either"

    tab.handle_search_text_changed("")
    assert tab.proxy_model.rowCount() == tab.model.rowCount(), "an empty box hides nothing"


def test_the_menu_opens_on_a_row_the_model_cannot_answer_for(tab, monkeypatch):
    """The read of the row was wrapped, logged and then carried straight on to use the name it
    had failed to bind. Add Observation and Import New Observation need nothing from the row,
    and the NameError took them down with the rest."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    opened = []

    def read_and_close():
        """`exec` on a menu runs an event loop; nothing here is going to click anything."""
        popup = QApplication.activePopupWidget()
        if popup is not None:
            opened.append([entry.text() for entry in popup.actions()])
            popup.close()

    real = tab.manipulator.inspect

    def refuse(obj, **request):
        if "get_item" in request:
            raise RuntimeError("no")
        return real(obj, **request)

    monkeypatch.setattr(tab.manipulator, "inspect", refuse)
    table = tab.ui.projectInfoTable
    table.resize(800, 400)
    over_a_row = table.visualRect(tab.proxy_model.index(0, 0)).center()

    QTimer.singleShot(0, read_and_close)
    tab.show_context_menu(over_a_row)

    assert opened, "the menu never opened"
    assert "Add Observation" in opened[0], f"the menu offered only {opened[0]}"
