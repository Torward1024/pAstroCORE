"""A session can be looked at, written down, and run again somewhere else.

MSB records every request that reaches the orchestrator; that has been true here since the
journal was registered. What was missing is everything a person can do with it -- and one thing
that stood in the way: **an entry holds the live object the request named**, so a journal can
neither be written to a file nor replayed against a different project.

What this pins is the portable form: a request with its object *named* rather than held, and
resolved against whatever project it is replayed on.
"""
import json

import pytest

import conftest
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject


@pytest.fixture
def session():
    """A manipulator that has done some work, so there is something to look at."""
    project = ScheduleProject.from_dict(json.loads(conftest.FIXTURE.read_text(encoding="utf-8")))
    observation = project.get_observation(next(iter(project.get_items())))
    observation.clear_calculated_data()
    manipulator = ScheduleManipulator(project)
    manipulator.compute(obj=None, method="run", targets=[observation],
                        calculations=["time_arrays"], time_step=600.0, recalculate=True)
    return manipulator, project, observation


def ask(manipulator, method, **attributes):
    response = manipulator.compute(obj=manipulator.get_managing_object(), method=method,
                                   raise_on_error=False, **attributes)
    return response.value


def test_the_session_can_be_read_as_rows(session):
    manipulator, _, observation = session
    rows = ask(manipulator, "history")

    assert rows, "the session did work and recorded none of it"
    calculated = [row for row in rows if row["operation"] == "calculate"]
    assert calculated, "the calculations are what a person wants to see"
    assert calculated[0]["object"] == observation.name
    assert calculated[0]["method"] == "time_arrays"
    assert calculated[0]["seconds"] >= 0.0
    assert calculated[0]["status"] is True


def test_a_row_holds_no_live_object(session):
    """The whole obstacle. An entry naming an object cannot leave the process."""
    manipulator, _, _ = session
    rows = ask(manipulator, "history")

    json.dumps(rows)        # raises if anything in there is not plain data


def test_the_session_can_be_written_and_read_back(session, tmp_path):
    manipulator, project, _ = session
    path = tmp_path / "session.json"

    written = manipulator.export(obj=project, method="journal", path=str(path))
    assert path.is_file()
    assert written["steps"] > 0

    read = json.loads(path.read_text(encoding="utf-8"))
    assert read["steps"], "a session written with no steps is a file that says nothing"


def test_it_replays_against_another_project(session, tmp_path):
    """The criterion. A session recorded against one project runs against another, which is
    what makes it a reproduction rather than a souvenir."""
    manipulator, project, _ = session
    path = tmp_path / "session.json"
    manipulator.export(obj=project, method="journal", path=str(path))

    fresh = ScheduleProject.from_dict(json.loads(conftest.FIXTURE.read_text(encoding="utf-8")))
    elsewhere = fresh.get_observation(next(iter(fresh.get_items())))
    elsewhere.clear_calculated_data()
    assert "times" not in elsewhere.calculated_data

    other = ScheduleManipulator(fresh)
    outcome = ask(other, "replay", path=str(path))

    assert outcome["failed"] == [], outcome
    assert "times" in elsewhere.calculated_data, (
        "the replay ran against the recorded objects rather than against this project")


def test_a_step_naming_something_this_project_lacks_is_reported(session, tmp_path):
    """Not skipped in silence: a session that half ran is worse than one that refused."""
    manipulator, project, _ = session
    path = tmp_path / "session.json"
    manipulator.export(obj=project, method="journal", path=str(path))

    session_data = json.loads(path.read_text(encoding="utf-8"))
    session_data["steps"][0]["object"] = "obs_that_does_not_exist"
    path.write_text(json.dumps(session_data), encoding="utf-8")

    empty = ScheduleProject(name="Empty")
    outcome = ask(ScheduleManipulator(empty), "replay", path=str(path))

    assert outcome["unresolved"], "a step naming nothing here has to be said out loud"


# --- recording is a setting -------------------------------------------------------------------

def test_recording_can_be_turned_off(qt_application, monkeypatch, tmp_path):
    """Measured at 10.4 us per request and 75.6 KB per 500 entries, so it is on by default --
    but a user who wants none of it should be able to say so."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "user"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user"))

    from pastrocore.app import PAstroCoreMainWindow

    settings = PAstroCoreMainWindow.load_settings()
    assert settings["record_session"] is True, "a session is recorded unless somebody says not to"

    window = PAstroCoreMainWindow({**settings, "record_session": False})
    try:
        assert window.manipulator.journal() is None
    finally:
        window.close()

    window = PAstroCoreMainWindow({**settings, "record_session": True, "session_limit": 7})
    try:
        assert window.manipulator.journal() is not None
    finally:
        window.close()


# --- the panel ---------------------------------------------------------------------------------

def test_the_session_panel_lists_what_was_asked(qt_application, session):
    """Everything it shows is one request, and the dialog holds the table and the file chooser
    -- which is the whole of what an interface is for."""
    from pastrocore.gui.p_dialog_session import SessionDialog

    manipulator, _, observation = session
    dialog = SessionDialog(manipulator)
    try:
        table = dialog.ui.tableRequests
        assert table.rowCount() > 0, "the session did work and the panel shows none of it"

        operations = {table.item(row, 0).text() for row in range(table.rowCount())}
        assert "calculate" in operations
        assert "request(s)" in dialog.ui.labelSummary.text()
    finally:
        dialog.close()


def test_the_panel_says_so_when_nothing_is_recorded(qt_application):
    """Recording is a setting. An empty table with no explanation reads as a broken panel."""
    from pastrocore.gui.p_dialog_session import SessionDialog
    from pastrocore.super.schedule_manipulator import ScheduleManipulator
    from pastrocore.super.schedule_project import ScheduleProject

    manipulator = ScheduleManipulator(ScheduleProject(name="Quiet"), journal_limit=None)
    dialog = SessionDialog(manipulator)
    try:
        assert dialog.ui.tableRequests.rowCount() == 0
        assert "Nothing has been recorded" in dialog.ui.labelSummary.text()
    finally:
        dialog.close()


def test_the_panel_replays_a_saved_session(qt_application, session, tmp_path, monkeypatch):
    """The button, end to end: choose a file, run it against the project that is open now."""
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    from pastrocore.gui.p_dialog_session import SessionDialog
    from pastrocore.super.schedule_manipulator import ScheduleManipulator
    from pastrocore.super.schedule_project import ScheduleProject

    manipulator, project, _ = session
    path = tmp_path / "session.json"
    manipulator.export(obj=project, method="journal", path=str(path))

    fresh = ScheduleProject.from_dict(json.loads(conftest.FIXTURE.read_text(encoding="utf-8")))
    elsewhere = fresh.get_observation(next(iter(fresh.get_items())))
    elsewhere.clear_calculated_data()
    other = ScheduleManipulator(fresh)

    monkeypatch.setattr(QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (str(path), "")))
    said = {}
    for name in ("information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, name,
                            staticmethod(lambda parent, title, text, *rest, _n=name:
                                         said.setdefault(_n, text)))

    dialog = SessionDialog(other)
    try:
        dialog.replay_session()
        assert "times" in elsewhere.calculated_data, f"nothing was replayed: {said}"
        assert "replayed" in (said.get("information") or said.get("warning") or "")
    finally:
        dialog.close()


def test_a_recorded_edit_replays_after_the_project_is_reopened(tmp_path):
    """A session that *edited* something could not be replayed at all.

    Replay resolved each step by name, and `find` never descends into an observation -- so a
    source, a telescope or a scan came back as unresolved every time. Every journal entry has
    carried its **path** since MSB 1.9.0, and 1.9.2 made that path resolvable; this uses it.

    Onto the *same* project, reopened -- which is the case that exists. The parts of this model
    are named with UUIDs, and those are written into the project file, so a path resolves after
    a restart. It cannot resolve onto a project built separately, because nothing there shares a
    name: applying a session to *other* objects would mean mapping by what a person reads -- an
    observation code, a source name -- and that is a decision nobody has taken yet.
    """
    project = ScheduleProject(name="Rec")
    project.create_item(item_code="OBS_A")
    observation = project.observations()[0]
    observation.get_sources().create_source(
        name="1228+126", ra_h=12.0, ra_m=30.0, ra_s=49.4, de_d=12.0, de_m=23.0, de_s=28.0)

    manipulator = ScheduleManipulator(project)
    manipulator.configure(observation.get_sources().get_items()[0],
                          set={"params": {"spectral_index": -0.7}})

    session = tmp_path / "edit.json"
    manipulator.export(obj=project, method="journal", path=str(session))
    manipulator.save(obj=project, path=str(tmp_path / "rec.pastro"))

    reopened = ScheduleProject.open(str(tmp_path / "rec.pastro"))
    its_source = reopened.observations()[0].get_sources().get_items()[0]
    its_source.set({"spectral_index": None})
    assert its_source.spectral_index is None

    outcome = ask(ScheduleManipulator(reopened), "replay", path=str(session))

    assert outcome["unresolved"] == [], outcome
    assert outcome["failed"] == [], outcome
    assert its_source.spectral_index == -0.7, (
        "the edit was replayed somewhere else, or nowhere")
