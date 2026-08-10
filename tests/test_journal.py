"""Every request is recorded, which is the shortest route from a bug report to a reproduction.

A user says a schedule came out wrong. Without a record, the only evidence is the result. With
one, the exact sequence of requests that produced it is there to read, and to run again.

It costs one interceptor because the framework was built for it: a request is data rather than
a call, and a response already reports every method that ran.
"""
import pytest

from msb_arch import RequestJournal


def test_the_orchestrator_records_by_default(manipulator, observation):
    journal = manipulator.get_journal()
    assert isinstance(journal, RequestJournal)

    manipulator.inspect(observation, get_observation_code=None)
    assert len(journal) >= 1
    assert journal[-1]["operation"] == "inspect"


def test_recording_can_be_declined(project):
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    quiet = ScheduleManipulator(project, journal_limit=None)
    assert quiet.get_journal() is None
    quiet.inspect(project, get_name=None)


def test_the_journal_is_bounded(project):
    """A session that runs for a day must not accumulate without end."""
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    bounded = ScheduleManipulator(project, journal_limit=5)
    for _ in range(20):
        bounded.inspect(project, get_name=None)

    assert len(bounded.get_journal()) == 5


def test_an_objects_history_can_be_read_back(manipulator, observation):
    """Provenance, read backwards: everything that ever touched this observation."""
    journal = manipulator.get_journal()
    journal.clear()

    manipulator.inspect(observation, get_observation_code=None)
    manipulator.inspect(observation, get_observation_type=None)

    history = journal.touching(observation.name)
    assert len(history) == 2
    assert [entry["operation"] for entry in history] == ["inspect", "inspect"]


def test_a_failed_request_is_recorded_too(manipulator, observation):
    """The requests worth reading after a bug report are usually the ones that failed."""
    journal = manipulator.get_journal()
    journal.clear()

    manipulator.inspect(observation, no_such_method=None, raise_on_error=False)
    assert len(journal) == 1


def test_a_session_can_be_replayed(manipulator, observation):
    """Read forwards instead, and the reported problem becomes a reproduction."""
    journal = manipulator.get_journal()
    journal.clear()

    manipulator.configure(observation, deactivate=None)
    assert observation.isactive is False

    manipulator.remove_interceptor(journal)     # or the replay records itself
    observation.activate()
    assert observation.isactive is True

    journal.replay(manipulator)
    assert observation.isactive is False, "the session ended where it ended"


def test_recording_does_not_change_what_a_request_returns(manipulator, observation):
    """An interceptor that altered the answer would be worse than no interceptor."""
    with_journal = manipulator.inspect(observation, get_observation_code=None)

    manipulator.remove_interceptor(manipulator.get_journal())
    without_journal = manipulator.inspect(observation, get_observation_code=None)

    assert with_journal == without_journal


# --- the built-in operations, adopted (M3) ------------------------------------------------

def test_reading_and_writing_still_work_through_the_builtins(manipulator, observation):
    """Twenty handlers were deleted in favour of msb_arch's. Nothing a caller does changed."""
    assert manipulator.inspect(observation, get_observation_code=None)
    assert len(manipulator.inspect(observation.get_telescopes(), get_all=None)) == 2


def test_a_request_reaches_one_member_of_a_container(manipulator, observation):
    """The ten container handlers existed only for this. msb_arch 1.1.0 does it."""
    telescopes = observation.get_telescopes()
    name = next(iter(manipulator.inspect(telescopes, get_all=None)))

    assert manipulator.inspect(telescopes, name=name, get_code=None)

    manipulator.configure(telescopes, name=name, deactivate=None)
    assert telescopes.get(name).isactive is False
    manipulator.configure(telescopes, name=name, activate=None)
    assert telescopes.get(name).isactive is True


def test_a_request_reaches_one_observation_of_the_project(manipulator, project, project_data):
    """The case that made the descent a hook: a project answers `get_observation`, not `get`."""
    code = next(iter(project_data["items"]))
    assert manipulator.inspect(project, name=code, get_observation_code=None)


def test_generating_observations_still_has_its_own_handler(manipulator):
    """The one handler of twenty-one that carries domain logic, and the reason it stayed."""
    from pastrocore.super.schedule_configurator import ScheduleConfigurator

    assert hasattr(ScheduleConfigurator, "_configure_scheduleproject")
    assert not hasattr(ScheduleConfigurator, "_configure_observation")
