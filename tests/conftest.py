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


@pytest.fixture(autouse=True)
def scratch_of_its_own(tmp_path, monkeypatch):
    """Give each test its own per-user data directory, and so its own scratch.

    Notes:
        - A scratch is named for the *process*, so every window built in one test run shared
          one directory. Results written by one test then looked unsaved to another test's
          window, which asked about them on close -- a modal dialog with nobody to answer it,
          and the suite stopped dead.
        - It also means a test run never reads or deletes anything of the user's, which was
          always the intention: `_offer_abandoned_sessions` takes a root for exactly this
          reason, and everything else reached the real one.
    """
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "user"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user"))
    monkeypatch.setenv("HOME", str(tmp_path / "user"))
    yield


@pytest.fixture(scope="session")
def qt_application():
    """One QApplication for the session; Qt permits no more."""
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication([])
    yield application


def pytest_addoption(parser):
    """Options a run may be given.

    Notes:
        - `--regenerate-form-pixels` rewrites the reference the form harness compares against.
          Deliberate and separate, because a reference that regenerates itself on a mismatch
          records whatever happened rather than what was meant.
    """
    parser.addoption("--regenerate-form-pixels", action="store_true", default=False,
                     help="rewrite tests/fixtures/form_pixels.json from what the forms render now")


def pytest_sessionfinish(session, exitstatus):
    """Write the form reference, when asked for it."""
    if not session.config.getoption("--regenerate-form-pixels", default=False):
        return

    import json

    from PySide6.QtWidgets import QApplication

    from test_form_pixels import REFERENCE, form_classes, platform_key, render

    QApplication.instance() or QApplication([])
    # Kept per platform: pixels are not portable, and rewriting the file would throw away the
    # reference recorded on whatever machine is not this one.
    everything = {}
    if REFERENCE.is_file():
        everything = json.loads(REFERENCE.read_text(encoding="utf-8"))
    everything[platform_key()] = {f"{stem}.{name}": render(stem, name)
                                  for stem, name in form_classes()}
    REFERENCE.parent.mkdir(parents=True, exist_ok=True)
    REFERENCE.write_text(json.dumps(everything, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    print(f"\nwrote {REFERENCE} for {platform_key()}: "
          f"{len(everything[platform_key()])} form(s)")
