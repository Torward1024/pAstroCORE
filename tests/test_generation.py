"""Generating observations, and what the dialog is told about it.

The generator answers with `{"status", "result", "error"}`. The thread that runs it wrapped that
answer as `{"status": True, "result": answer}`, so the dialog saw a success every time: a time
range too short for a single observation closed the dialog as if it had worked, and nobody was
told why nothing appeared. A cancel answered `"result": []` while the project already held
every observation made before it.
"""
import pytest

from pastrocore.base.frequencies import Frequencies
from pastrocore.base.sources import Source, Sources
from pastrocore.base.telescopes import Telescopes
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject


def request(names, hours):
    """What the dialog hands the generator: these sources, two stations, one band."""
    sources = Sources()
    for index, name in enumerate(names):
        sources.add(Source(name=name, ra_h=float(index + 1), de_d=10.0))
    telescopes = Telescopes()
    telescopes.create_telescope(code="Sv", name="Svetloe", x=2730173.0, y=1562442.7, z=5529969.1)
    telescopes.create_telescope(code="Zc", name="Zelenchuk", x=3451207.5, y=3060375.4, z=4391915.0)
    frequencies = Frequencies()
    frequencies.create_if(name="f1", frequency=8400.0, bandwidth=16.0)
    return {"sources": sources, "telescopes": telescopes, "frequencies": frequencies,
            "time_range": {"start": "2026-01-01 00:00:00",
                           "end": f"2026-01-01 {hours:02d}:00:00"},
            "scan_duration": 300.0, "num_scans": 2, "parallel": True,
            "pattern": {"naming_mask": "OBS_{s}", "interval_sec": 300}}


def run_thread(attributes):
    """Run the dialog's thread in place and return what it emitted."""
    from pastrocore.gui.p_dialog_generate_observations import GenerationThread

    project = ScheduleProject(name="generated")
    thread = GenerationThread(ScheduleManipulator(project), project, attributes)
    emitted = []
    thread.finished.connect(emitted.append)
    thread.run()
    assert len(emitted) == 1, "the thread must answer exactly once"
    return project, emitted[0]


def test_a_generation_that_made_nothing_is_not_reported_as_a_success(qt_application):
    """Ten scans of five minutes with five-minute gaps do not fit in an hour."""
    attributes = request(["A"], hours=1)
    attributes["num_scans"] = 10

    project, answer = run_thread(attributes)

    assert project.observations() == []
    assert answer["status"] is False, "nothing was generated and the dialog was told it worked"
    assert "No observations generated" in answer["error"]


def test_a_generation_that_worked_names_what_it_made(qt_application):
    project, answer = run_thread(request(["A", "B"], hours=12))

    assert answer["status"] is True
    assert sorted(answer["result"]) == ["OBS_A", "OBS_B"]
    assert len(project.observations()) == 2


def test_a_cancel_names_what_was_already_added(qt_application):
    """Cancelled after the first observation: that one is in the project, so it is the answer."""
    attributes = request(["A", "B", "C"], hours=12)

    def cancel_once_one_is_made(value, message):
        attributes["cancelled"] = True

    from pastrocore.gui.p_dialog_generate_observations import GenerationThread

    project = ScheduleProject(name="generated")
    thread = GenerationThread(ScheduleManipulator(project), project, attributes)
    # The thread installs its own callback; replaced after, as a progress dialog's Cancel
    # would arrive while it runs.
    attributes["progress_callback"] = cancel_once_one_is_made
    emitted = []
    thread.finished.connect(emitted.append)
    thread.run()

    answer = emitted[0]
    assert answer.get("cancelled") is True
    assert answer["result"] == ["OBS_A"], (
        f"the project holds {[o.get_observation_code() for o in project.observations()]} "
        f"and the answer said {answer['result']}")
