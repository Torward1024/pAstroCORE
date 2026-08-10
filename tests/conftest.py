"""A real project to calculate against.

The calculations are the product, and until this suite existed nothing said whether a
refactoring changed them. Everything here serves one purpose: make "the numbers did not move"
a statement a build can check.

The fixture is a project the author produced and trusts -- ALMA and APEX observing 1228+126
over a day -- rather than a synthetic one. That matters more than it sounds: a hand-built
observation can easily describe a source that is never above the horizon, and every
calculation then returns an empty frame, so the suite passes while defending nothing.

It also means the reference needs no separate file. **The saved results are the reference**:
recomputing has to reproduce what the project already contains.
"""
import copy
import json
import logging
import pathlib

import pytest

from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "test_project.pastro"


@pytest.fixture(autouse=True)
def quiet_logging():
    """The application logs heavily at debug level; a test run should not."""
    saved = {name: logging.getLogger(name).level for name in ("msb_arch", "pastrocore", "")}
    for name in saved:
        logging.getLogger(name).setLevel(logging.CRITICAL)
    yield
    for name, level in saved.items():
        logging.getLogger(name).setLevel(level)


@pytest.fixture(scope="session")
def project_data():
    """The raw saved project, read once and never mutated."""
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def project(project_data):
    """A fresh project each test, so one cannot leave state for the next."""
    return ScheduleProject.from_dict(copy.deepcopy(project_data))


@pytest.fixture
def observation(project, project_data):
    """The single observation the fixture project holds."""
    return project.get_observation(next(iter(project_data["items"])))


@pytest.fixture
def manipulator(project):
    """The single entry point, configured exactly as the application configures it."""
    orchestrator = ScheduleManipulator(project)
    yield orchestrator
    close = getattr(orchestrator, "close", None)
    if close:
        close()


@pytest.fixture
def saved_results(observation):
    """What the project was saved holding: the reference every calculation is checked against.

    Returns:
        dict: Calculation key mapped to `{"data": DataFrame, "metadata": dict}`.
    """
    return {key: dict(value) for key, value in observation.calculated_data.items()}
