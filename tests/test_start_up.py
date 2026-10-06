"""Starting the application, from a command line and from a build.

A download that does not start is the one failure a test suite never sees: everything here
passes in a checkout, and the thing a user double-clicks is a different artefact. `--selftest`
is how a build says it started -- it opens a project, draws, and closes, with one line saying
what it opened and an exit code saying whether it worked.

These run it as a subprocess, because that is the only way to tell "the function returns" from
"the program starts".
"""
import json
import os
import pathlib
import subprocess
import sys

import pytest

import conftest

ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def saved_project(tmp_path_factory):
    """The fixture project written out as a directory, which is what a user opens."""
    sys.path.insert(0, str(ROOT))
    from pastrocore.super.schedule_project import ScheduleProject

    directory = tmp_path_factory.mktemp("opened") / "survey.pastro"
    ScheduleProject.from_dict(
        json.loads(conftest.FIXTURE.read_text(encoding="utf-8"))).to_directory(str(directory))
    return directory


def started(*arguments, home, where=None):
    """Run the application as its own process, with a per-user directory of its own."""
    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONPATH=str(ROOT))
    for name in ("LOCALAPPDATA", "XDG_DATA_HOME", "HOME"):
        environment[name] = str(home)
    return subprocess.run([sys.executable, "-m", "pastrocore.app", *arguments],
                          capture_output=True, text=True, cwd=str(where or ROOT),
                          env=environment, timeout=300)


def test_the_self_test_starts_and_stops_on_its_own(tmp_path):
    """What CI runs against a build: no project, no display, no click, and an exit code."""
    done = started("--selftest", home=tmp_path)

    assert done.returncode == 0, done.stderr[-2000:]
    assert "Untitled" in done.stdout or "no project" in done.stdout, done.stdout


def test_a_project_named_on_the_command_line_is_the_one_that_opens(saved_project, tmp_path):
    """A `.pastro` directory passed as an argument, which is also what a file association
    hands over when one is double-clicked."""
    done = started("--selftest", str(saved_project), home=tmp_path)

    assert done.returncode == 0, done.stderr[-2000:]
    assert "1 observation" in done.stdout, done.stdout


def test_a_path_that_is_not_a_project_is_refused(tmp_path):
    """Said on the way in rather than drawn as an empty window somebody has to diagnose."""
    done = started("--selftest", str(tmp_path / "nothing.pastro"), home=tmp_path)

    assert done.returncode != 0
    assert "nothing.pastro" in (done.stderr + done.stdout)


def test_the_log_is_beside_the_settings_and_not_where_it_was_started(tmp_path):
    """A log in whatever directory the application happened to start from is a log nobody can
    be asked to send, and in an installed one that directory may not be writable at all."""
    working = tmp_path / "elsewhere"
    working.mkdir()
    done = started("--selftest", home=tmp_path / "user", where=working)

    assert done.returncode == 0, done.stderr[-2000:]
    assert not (working / "output.log").exists(), "the log was left where it was started"
    written = list((tmp_path / "user").rglob("output.log"))
    assert written, "no log was written in the per-user directory"


def test_help_says_what_it_takes(tmp_path):
    """A build a user cannot ask what it takes is a build they have to guess at."""
    done = started("--help", home=tmp_path)

    assert done.returncode == 0, done.stderr[-2000:]
    assert "--selftest" in done.stdout and "project" in done.stdout
