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
    plan = manipulator.compute(obj=None, method="plan", targets=[observation],
                              calculations=["uv_coverage"], time_step=300.0)

    assert [name.split("/")[-1] for name in plan] == [
        "time_arrays", "interpolated_orbits", "telescope_positions", "source_visibility",
        "uv_coverage"]


def test_the_order_comes_from_the_handlers(bench):
    """Nothing here lists it: MSB derives which handler calls which, and the plan uses that."""
    manipulator, observation = bench
    plan = manipulator.compute(obj=None, method="plan", targets=[observation],
                              calculations=["uv_coverage"], time_step=300.0)

    positions = {name.split("/")[-1]: index for index, name in enumerate(plan)}
    for step, needed in (("uv_coverage", "source_visibility"),
                         ("source_visibility", "telescope_positions"),
                         ("telescope_positions", "time_arrays")):
        assert positions[step] > positions[needed], f"{step} must follow {needed}"


def test_every_step_waits_for_what_it_needs(bench):
    manipulator, observation = bench
    plan = manipulator.compute(obj=None, method="plan", targets=[observation],
                              calculations=["uv_coverage"], time_step=300.0)

    uv = plan[f"{observation.code}/uv_coverage"]
    assert f"{observation.code}/source_visibility" in uv["after"]


def test_two_observations_do_not_wait_for_each_other(bench):
    """Their steps are independent, which is what lets a stage run them together."""
    manipulator, observation = bench
    plan = manipulator.compute(obj=None, method="plan", targets=[observation, observation],
                              calculations=["time_arrays"], time_step=300.0)

    assert len(plan) == 1, "the same observation twice is one set of steps"


def test_running_it_computes_everything(bench):
    manipulator, observation = bench
    outcome = manipulator.compute(obj=None, method="run", targets=[observation],
                                 calculations=["uv_coverage"], time_step=300.0,
                                 recalculate=True)

    assert outcome["failed"] == []
    assert outcome["cancelled"] is False
    assert "uv_coverage" in observation.calculated_data
    assert "source_visibility" in observation.calculated_data


def test_progress_is_reported_step_by_step(bench):
    manipulator, observation = bench
    seen = []
    manipulator.compute(obj=None, method="run", targets=[observation],
                       calculations=["uv_coverage"], time_step=300.0, recalculate=True,
                       progress=lambda percent, message: seen.append((percent, message)))

    assert [percent for percent, _ in seen] == [20, 40, 60, 80, 100]
    assert "uv_coverage" in seen[-1][1]
    assert seen[-1][1].endswith(" s"), "each step reports how long it took"


def test_cancelling_stops_and_says_so(bench):
    """A cancellation is a refused request, so the branch below it is skipped exactly as a
    failure would be."""
    manipulator, observation = bench
    asked = {"times": 0}

    def cancelled():
        asked["times"] += 1
        return asked["times"] > 2

    outcome = manipulator.compute(obj=None, method="run", targets=[observation],
                                 calculations=["uv_coverage"], time_step=300.0,
                                 recalculate=True, cancelled=cancelled)

    assert outcome["cancelled"] is True
    assert outcome["failed"], "the steps after the cancellation did not run"
    assert len(outcome["ran"]) < 5


def test_asking_for_nothing_is_refused(bench):
    manipulator, observation = bench
    with pytest.raises(Exception):
        manipulator.compute(obj=None, method="plan", targets=[observation], calculations=[])


class _FakeProgress:
    """Stands in for the modal progress dialog, which would block the suite."""

    def update_progress(self, *args, **kwargs):
        return None

    def close(self):
        return None


def test_a_run_with_a_failed_step_is_not_called_a_success(bench, qt_application, monkeypatch):
    """What the interface said when a step failed: "All calculations completed successfully".

    `CalculationDialog` defined `calculation_finished` twice, and the later definition took one
    argument where the signal carries two. PySide drops the arguments a slot does not accept
    rather than complaining, so the list of failures fell into the gap between the two
    definitions and the run was reported as clean.

    Driven through the signal rather than by calling the slot, because the silent drop is the
    whole defect and a direct call would not reproduce it.
    """
    from PySide6.QtWidgets import QMessageBox

    from pastrocore.gui.p_dialog_calculations import CalculationDialog, CalculationThread

    manipulator, observation = bench
    said = {}
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda parent, title, text, *rest: said.setdefault(
                            "information", text)))
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda parent, title, text, *rest: said.setdefault(
                            "warning", text)))

    dialog = CalculationDialog(manipulator, time_step=600)
    dialog.progress_dialog = _FakeProgress()

    thread = CalculationThread(manipulator, [observation], ["uv_coverage"], {})
    thread.finished.connect(dialog.calculation_finished)
    thread.finished.emit({f"{observation.code}/time_arrays": True},
                         [f"{observation.code}/uv_coverage failed"],
                         {f"{observation.code}/time_arrays": 0.1})

    assert "information" not in said, (
        f"a run with a failed step was reported as a success: {said['information']!r}")
    assert "uv_coverage" in said.get("warning", ""), (
        f"the user was not told which step failed: {said!r}")
    dialog.close()


def test_the_interface_thread_only_sends_a_request():
    """A ratchet. The loop, the ordering and the prerequisites belong to the backend, or a CLI
    and a server would each need their own copy."""
    import pathlib

    source = (pathlib.Path(__file__).resolve().parent.parent / "pastrocore" / "gui"
              / "p_dialog_calculations.py").read_text(encoding="utf-8")
    thread = source[source.index("class CalculationThread"):source.index("class ProgressDialog")]

    assert "for calc_type in" not in thread, "the thread is looping over calculations again"
    assert 'method="run"' in thread, "the thread should send one request"


# --- independent branches run at once ---------------------------------------------------------

def test_independent_steps_run_together(bench):
    """Measured at 1.30x on the fixture project: three steps must be sequential and nine wait
    only on those, so the ceiling is what that fan costs.

    What this pins is not the speed -- a build machine's noise is larger than the difference --
    but that asking for it produces the same results as not asking.
    """
    manipulator, observation = bench
    outcome = manipulator.compute(obj=None, method="run", targets=[observation],
                                 calculations=["uv_coverage", "sun_angles"], time_step=600.0,
                                 recalculate=True, concurrent=True)

    assert outcome["failed"] == []
    assert "uv_coverage" in observation.calculated_data
    assert "sun_angles" in observation.calculated_data


def test_cancelling_a_concurrent_run_still_stops_it(bench):
    """Cancellation is a refused request, and a stage running two steps at once must not turn
    that into a partly-cancelled run that reports success."""
    manipulator, observation = bench
    asked = {"times": 0}

    def cancelled():
        asked["times"] += 1
        return asked["times"] > 2

    outcome = manipulator.compute(obj=None, method="run", targets=[observation],
                                 calculations=["uv_coverage"], time_step=600.0,
                                 recalculate=True, concurrent=True, cancelled=cancelled)

    assert outcome["cancelled"] is True
    assert outcome["failed"], "the steps after the cancellation did not run"


def test_every_step_reports_its_own_time(bench):
    """Measured where every request passes, rather than estimated by whoever called.

    The caller cannot time a step from outside: with a stage running several at once, the wall
    clock between two progress callbacks is not any one calculation's duration.
    """
    manipulator, observation = bench
    outcome = manipulator.compute(obj=None, method="run", targets=[observation],
                                 calculations=["uv_coverage"], time_step=600.0,
                                 recalculate=True)

    timings = outcome["timings"]
    assert [name for name in timings] == outcome["ran"], "one entry per step, in plan order"
    assert all(seconds >= 0.0 for seconds in timings.values())
    assert sum(timings.values()) > 0.0, "a whole run of five calculations took no time at all"


def test_the_progress_percentage_counts_finished_work(bench):
    """A bar that advances when a step *starts* sits at 80% through the longest step of the
    run and then jumps -- which is the shape of a bar that looks stuck."""
    manipulator, observation = bench
    seen = []

    manipulator.compute(obj=None, method="run", targets=[observation],
                       calculations=["uv_coverage"], time_step=600.0, recalculate=True,
                       progress=lambda percent, message: seen.append((percent, message)))

    assert seen[0][0] > 0, "the first report is a step already finished"
    assert seen[-1][0] == 100
    assert [percent for percent, _ in seen] == sorted(percent for percent, _ in seen)
