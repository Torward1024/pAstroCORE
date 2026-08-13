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
    return response["result"] if isinstance(response, dict) and "status" in response else response


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
