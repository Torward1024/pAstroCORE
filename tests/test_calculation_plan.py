"""Running several calculations is a plan the backend builds, not a loop in a dialog.

What this pins: the prerequisites and their order come from the handlers themselves, a caller
naming one calculation gets everything it needs, and progress and cancellation ride on the one
hook MSB provides rather than on a loop that only the interface has.
"""
import json

import pytest

from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject

import conftest


@pytest.fixture
def bench():
    project = ScheduleProject.from_dict(json.loads(conftest.FIXTURE.read_text(encoding="utf-8")))
    observation = project.get_observation(next(iter(project.get_items())))
    observation.clear_calculated_data()
    return ScheduleManipulator(project), observation


def test_asking_for_one_plans_everything_it_needs(bench):
    manipulator, observation = bench
    plan = manipulator.export(obj=None, method="plan", targets=[observation],
                              calculations=["uv_coverage"], time_step=300.0)

    assert [name.split("/")[-1] for name in plan] == [
        "time_arrays", "interpolated_orbits", "telescope_positions", "source_visibility",
        "uv_coverage"]


def test_the_order_comes_from_the_handlers(bench):
    """Nothing here lists it: MSB derives which handler calls which, and the plan uses that."""
    manipulator, observation = bench
    plan = manipulator.export(obj=None, method="plan", targets=[observation],
                              calculations=["uv_coverage"], time_step=300.0)

    positions = {name.split("/")[-1]: index for index, name in enumerate(plan)}
    for step, needed in (("uv_coverage", "source_visibility"),
                         ("source_visibility", "telescope_positions"),
                         ("telescope_positions", "time_arrays")):
        assert positions[step] > positions[needed], f"{step} must follow {needed}"


def test_every_step_waits_for_what_it_needs(bench):
    manipulator, observation = bench
    plan = manipulator.export(obj=None, method="plan", targets=[observation],
                              calculations=["uv_coverage"], time_step=300.0)

    uv = plan[f"{observation.code}/uv_coverage"]
    assert f"{observation.code}/source_visibility" in uv["after"]


def test_two_observations_do_not_wait_for_each_other(bench):
    """Their steps are independent, which is what lets a stage run them together."""
    manipulator, observation = bench
    plan = manipulator.export(obj=None, method="plan", targets=[observation, observation],
                              calculations=["time_arrays"], time_step=300.0)

    assert len(plan) == 1, "the same observation twice is one set of steps"


def test_running_it_computes_everything(bench):
    manipulator, observation = bench
    outcome = manipulator.export(obj=None, method="run", targets=[observation],
                                 calculations=["uv_coverage"], time_step=300.0,
                                 recalculate=True)

    assert outcome["failed"] == []
    assert outcome["cancelled"] is False
    assert "uv_coverage" in observation.calculated_data
    assert "source_visibility" in observation.calculated_data


def test_progress_is_reported_step_by_step(bench):
    manipulator, observation = bench
    seen = []
    manipulator.export(obj=None, method="run", targets=[observation],
                       calculations=["uv_coverage"], time_step=300.0, recalculate=True,
                       progress=lambda percent, message: seen.append((percent, message)))

    assert [percent for percent, _ in seen] == [20, 40, 60, 80, 100]
    assert seen[-1][1].endswith("uv_coverage")


def test_cancelling_stops_and_says_so(bench):
    """A cancellation is a refused request, so the branch below it is skipped exactly as a
    failure would be."""
    manipulator, observation = bench
    asked = {"times": 0}

    def cancelled():
        asked["times"] += 1
        return asked["times"] > 2

    outcome = manipulator.export(obj=None, method="run", targets=[observation],
                                 calculations=["uv_coverage"], time_step=300.0,
                                 recalculate=True, cancelled=cancelled)

    assert outcome["cancelled"] is True
    assert outcome["failed"], "the steps after the cancellation did not run"
    assert len(outcome["ran"]) < 5


def test_asking_for_nothing_is_refused(bench):
    manipulator, observation = bench
    with pytest.raises(Exception):
        manipulator.export(obj=None, method="plan", targets=[observation], calculations=[])


def test_the_interface_thread_only_sends_a_request():
    """A ratchet. The loop, the ordering and the prerequisites belong to the backend, or a CLI
    and a server would each need their own copy."""
    import pathlib

    source = (pathlib.Path(__file__).resolve().parent.parent / "pastrocore" / "gui"
              / "p_dialog_calculations.py").read_text(encoding="utf-8")
    thread = source[source.index("class CalculationThread"):source.index("class ProgressDialog")]

    assert "for calc_type in" not in thread, "the thread is looping over calculations again"
    assert 'method="run"' in thread, "the thread should send one request"
