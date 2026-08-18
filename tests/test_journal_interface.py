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


def test_a_step_naming_something_this_project_lacks_is_refused_before_anything_runs(session,
                                                                                    tmp_path):
    """Not skipped in silence, and not skipped mid-run either: the session is checked whole
    first, so a step naming nothing here stops the replay rather than leaving a hole in it."""
    manipulator, project, _ = session
    path = tmp_path / "session.json"
    manipulator.export(obj=project, method="journal", path=str(path))

    session_data = json.loads(path.read_text(encoding="utf-8"))
    session_data["steps"][0]["object"] = "obs_that_does_not_exist"
    session_data["steps"][0].pop("path", None)
    path.write_text(json.dumps(session_data), encoding="utf-8")

    empty = ScheduleProject(name="Empty")
    outcome = ask(ScheduleManipulator(empty), "replay", path=str(path))

    assert outcome["problems"], "a step naming nothing here has to be said out loud"
    assert any("obs_that_does_not_exist" in problem for problem in outcome["problems"])
    assert outcome["ran"] == [], "nothing may run from a session that does not check out"


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


def test_the_session_says_which_object_not_just_its_name():
    """Two observations may hold a source of the same name, and the panel showed the bare name
    -- so two rows about two different sources were indistinguishable.

    Every entry carries its path, so the row can say where the object is. Read here rather than
    formatted in the window: a command line printing a session wants the same column.
    """
    project = ScheduleProject(name="Two")
    project.create_item(item_code="OBS_A")
    project.create_item(item_code="OBS_B")
    for observation in project.observations():
        observation.get_sources().create_source(
            name="1228+126", ra_h=12.0, ra_m=30.0, ra_s=49.4,
            de_d=12.0, de_m=23.0, de_s=28.0)

    manipulator = ScheduleManipulator(project)
    first, second = project.observations()
    manipulator.configure(second.get_sources().get_items()[0],
                          set={"params": {"spectral_index": -0.7}})

    rows = ask(manipulator, "history")
    edit = [row for row in rows if row["operation"] == "configure"][-1]

    assert edit["object"] == "1228+126"
    assert edit["where"].endswith("1228+126"), edit["where"]
    assert second.name in edit["where"], (
        f"the row cannot say which of the two sources it was: {edit['where']}")
    assert first.name not in edit["where"]


def test_the_panel_shows_where_as_a_column(qt_application, session):
    """What the row gained has to reach the reader, or it is a field nobody sees."""
    from pastrocore.gui.p_dialog_session import SessionDialog

    manipulator, _, _ = session
    dialog = SessionDialog(manipulator)
    try:
        headers = [dialog.ui.tableRequests.horizontalHeaderItem(column).text()
                   for column in range(dialog.ui.tableRequests.columnCount())]
        assert "Where" in headers

        column = headers.index("Where")
        shown = [dialog.ui.tableRequests.item(row, column).text()
                 for row in range(dialog.ui.tableRequests.rowCount())]
        assert any(text for text in shown), "the column is there and empty"
    finally:
        dialog.close()


def test_a_replayed_step_drops_what_cannot_be_replayed(session, tmp_path):
    """A run carries callables -- one to report progress, one to ask whether to stop -- and a
    journal cannot record a callable, so it records what it was: `<function>`.

    Replaying handed that string back as `progress`, and the handler called it:
    `'str' object is not callable`. Found by writing the command line, which replays a session
    that contains a run rather than only calculations.
    """
    manipulator, project, _ = session
    path = tmp_path / "with_a_callback.json"

    manipulator.compute(obj=None, method="run", targets=project.observations(),
                        calculations=["time_arrays"], time_step=600.0, force=True,
                        progress=lambda percent, message: None,
                        cancelled=lambda: False)
    manipulator.export(obj=project, method="journal", path=str(path))

    outcome = ask(ScheduleManipulator(project), "replay", path=str(path))
    assert outcome["failed"] == [], outcome


# --- a session is a document somebody will edit -------------------------------------------------

def _session_file(tmp_path, steps):
    """Write a session by hand, as somebody editing one would."""
    path = tmp_path / "edited.json"
    path.write_text(json.dumps({"steps": steps}, indent=2), encoding="utf-8")
    return path


def test_a_session_that_checks_out_says_so(session, tmp_path):
    manipulator, project, _ = session
    path = tmp_path / "recorded.json"
    manipulator.export(obj=project, method="journal", path=str(path))

    report = ask(manipulator, "check", path=str(path))
    assert report["problems"] == [], report
    assert report["steps"] > 0


def test_an_operation_nobody_has_is_named_rather_than_attempted(session, tmp_path):
    """The first thing a hand-edited file gets wrong. Which operations exist is asked of the
    orchestrator, so a new one needs nothing added here."""
    manipulator, project, observation = session
    path = _session_file(tmp_path, [{"operation": "calculat", "object": observation.name,
                                     "method": "time_arrays", "attributes": {}}])

    report = ask(manipulator, "check", path=str(path))
    assert any("calculat" in problem for problem in report["problems"]), report


def test_a_method_that_operation_does_not_have_is_named(session, tmp_path):
    manipulator, project, observation = session
    path = _session_file(tmp_path, [{"operation": "calculate", "object": observation.name,
                                     "method": "time_arrys", "attributes": {}}])

    report = ask(manipulator, "check", path=str(path))
    assert any("time_arrys" in problem for problem in report["problems"]), report


def test_an_object_that_is_not_here_is_named_with_where_it_looked(session, tmp_path):
    manipulator, project, _ = session
    path = _session_file(tmp_path, [{"operation": "calculate", "object": "obs_not_here",
                                     "path": ["nowhere", "obs_not_here"],
                                     "method": "time_arrays", "attributes": {}}])

    report = ask(manipulator, "check", path=str(path))
    assert any("obs_not_here" in problem for problem in report["problems"]), report


def test_an_attribute_the_handler_never_reads_is_a_warning_not_a_refusal(session, tmp_path):
    """`accepts` is what a handler reads, derived -- and MSB documents it as a **lower** bound:
    a key read under a name computed at run time is invisible to it. So a typo like `time_stp`
    is worth saying and not worth refusing over."""
    manipulator, project, observation = session
    path = _session_file(tmp_path, [{"operation": "calculate", "object": observation.name,
                                     "method": "time_arrays",
                                     "attributes": {"time_stp": 600.0}}])

    report = ask(manipulator, "check", path=str(path))
    assert any("time_stp" in note for note in report["warnings"]), report
    assert report["problems"] == [], "an unread attribute is not a reason to refuse"


def test_a_session_that_does_not_check_out_is_refused_rather_than_half_run(session, tmp_path):
    """The whole question L2 asks. A file with one bad step and one good one must run neither."""
    manipulator, project, observation = session
    observation.clear_calculated_data()
    path = _session_file(tmp_path, [
        {"operation": "calculate", "object": observation.name, "method": "time_arrays",
         "attributes": {"time_step": 600.0, "store_key": "times"}},
        {"operation": "calculate", "object": observation.name, "method": "not_a_calculation",
         "attributes": {}}])

    outcome = ask(manipulator, "replay", path=str(path))

    assert outcome["ran"] == [], outcome
    assert outcome["problems"], "it ran nothing and did not say why"
    assert "times" not in observation.calculated_data, (
        "the good step ran, which is exactly what a refusal is meant to prevent")


def test_the_panel_refuses_a_session_that_does_not_check_out(qt_application, session, tmp_path,
                                                             monkeypatch):
    """The window says the same thing the command line says, because both ask the same
    operation: nothing ran, and here is why."""
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    from pastrocore.gui.p_dialog_session import SessionDialog

    manipulator, project, observation = session
    path = tmp_path / "edited.json"
    path.write_text(json.dumps({"steps": [
        {"operation": "calculate", "object": observation.name, "method": "no_such_thing",
         "attributes": {}}]}), encoding="utf-8")

    monkeypatch.setattr(QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (str(path), "")))
    said = {}
    for name in ("information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, name,
                            staticmethod(lambda parent, title, text, *rest, _n=name:
                                         said.setdefault(_n, text)))

    dialog = SessionDialog(manipulator)
    try:
        dialog.replay_session()
        assert "no_such_thing" in (said.get("critical") or ""), said
        assert "information" not in said, "a refused session was reported as a success"
    finally:
        dialog.close()
