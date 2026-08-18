"""A command line over the same requests the window sends.

This is the claim the whole backend was built for, tested rather than asserted: **the interface
is one caller among several.** If it is true, a command line is thin -- it parses arguments,
sends requests and prints what comes back -- and it needs nothing from `pastrocore.gui`.

The ratchet at the bottom is the proof. Everything above it is what the thing actually does.
"""
import json
import pathlib
import subprocess
import sys

import pytest

import conftest
from pastrocore import cli
from pastrocore.super.schedule_project import ScheduleProject

ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture
def saved(tmp_path):
    """The fixture project, on disk, where a command line would find it."""
    project = ScheduleProject.from_dict(json.loads(conftest.FIXTURE.read_text(encoding="utf-8")))
    destination = tmp_path / "survey.pastro"
    project.save(str(destination))
    return destination


def run(*arguments, capsys=None):
    """Run one command and return `(exit code, what it printed)`."""
    code = cli.main([str(argument) for argument in arguments])
    return code, capsys.readouterr().out if capsys else ""


# --- what it does --------------------------------------------------------------------------

def test_it_says_what_a_project_holds(saved, capsys):
    code, printed = run("info", saved, capsys=capsys)

    assert code == 0
    assert "OBS_DEFAULT" in printed
    assert "telescope" in printed.lower()
    assert "uv_coverage" in printed, "the results it holds are the point of asking"


def test_it_lists_what_can_be_calculated(capsys):
    code, printed = run("calculations", capsys=capsys)

    assert code == 0
    assert "uv_coverage" in printed and "UV Coverage" in printed

    # A step belongs under its own heading rather than among the choices. Checked on the key
    # column, since the choices legitimately *mention* their steps under "needs".
    offered, steps = printed.split("Steps")
    keys = {line.split()[0] for line in offered.splitlines() if line.startswith("  ")}
    assert "time_arrays" not in keys
    assert "time_arrays" in steps


def test_it_runs_a_calculation_and_reports_each_step(saved, capsys):
    code, printed = run("run", saved, "--only", "uv_coverage", "--force", capsys=capsys)

    assert code == 0
    assert "uv_coverage" in printed
    assert "source_visibility" in printed, "the prerequisites it ran are part of what it did"
    assert " s" in printed, "each step reports its own time"


def test_a_run_writes_its_results_into_the_project(saved, capsys):
    run("run", saved, "--only", "uv_coverage", "--force", capsys=capsys)

    reopened = ScheduleProject.open(str(saved))
    observation = reopened.observations()[0]
    assert observation.get_calculated_data_by_key("uv_coverage")["data"].height > 0


def test_it_exports_what_was_calculated(saved, tmp_path, capsys):
    code, printed = run("export", saved, tmp_path / "out", "--only", "uv_coverage",
                        capsys=capsys)

    assert code == 0
    written = list((tmp_path / "out").glob("*.txt"))
    assert written, printed


def test_it_shows_a_session_and_can_replay_one(saved, tmp_path, capsys):
    session = tmp_path / "session.json"
    run("run", saved, "--only", "uv_coverage", "--force", "--session", session, capsys=capsys)
    assert session.is_file()

    code, printed = run("replay", saved, session, capsys=capsys)
    assert code == 0
    assert "replayed" in printed.lower()


# --- what it refuses -----------------------------------------------------------------------

def test_a_project_that_is_not_there_is_refused(tmp_path, capsys):
    code, printed = run("info", tmp_path / "nothing.pastro", capsys=capsys)

    assert code != 0
    assert "not" in printed.lower()


def test_a_calculation_nobody_offers_is_refused(saved, capsys):
    code, printed = run("run", saved, "--only", "not_a_calculation", capsys=capsys)

    assert code != 0
    assert "not_a_calculation" in printed


# --- the proof -----------------------------------------------------------------------------

def test_the_command_line_needs_nothing_from_the_window():
    """The whole point. A command line that has to import a dialog is not a second caller of a
    backend -- it is the window with the pixels removed."""
    source = (ROOT / "pastrocore" / "cli.py").read_text(encoding="utf-8")

    assert "pastrocore.gui" not in source, "the command line reaches into the interface"
    assert "PySide6" not in source, "the command line imports Qt"


def test_it_starts_without_qt(saved):
    """Measured rather than asserted: run it in a process where importing Qt would be visible."""
    result = subprocess.run(
        [sys.executable, "-c",
         "import sys; from pastrocore import cli; "
         "code = cli.main(['calculations']); "
         "print('QT' if any(m.startswith('PySide6') for m in sys.modules) else 'NO_QT')"],
        capture_output=True, text=True, cwd=ROOT)

    assert result.returncode == 0, result.stderr
    assert "NO_QT" in result.stdout, "the command line pulled Qt in"


def test_the_window_is_still_what_the_bare_command_does():
    """R4 promised `pastrocore` starts the application. A command line must not take that over."""
    import tomllib

    manifest = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = manifest["project"]["scripts"]

    assert scripts["pastrocore"] == "pastrocore.app:main"
    assert scripts["pastrocore-cli"] == "pastrocore.cli:main"


# --- a session is a document somebody edits ------------------------------------------------

def test_it_checks_a_session_without_running_it(saved, tmp_path, capsys):
    session = tmp_path / "session.json"
    run("run", saved, "--only", "uv_coverage", "--force", "--session", session, capsys=capsys)

    code, printed = run("check", saved, session, capsys=capsys)
    assert code == 0
    assert "ok" in printed.lower() or "no problem" in printed.lower(), printed


def test_a_hand_edited_session_is_refused_with_the_reason(saved, tmp_path, capsys):
    """The question L2 asks. A file people edit will be wrong sometimes, and it must say how
    rather than run half of it."""
    session = tmp_path / "edited.json"
    session.write_text(json.dumps({"steps": [
        {"operation": "calculate", "object": "OBS_DEFAULT", "method": "no_such_thing",
         "attributes": {}}]}), encoding="utf-8")

    code, printed = run("check", saved, session, capsys=capsys)
    assert code != 0
    assert "no_such_thing" in printed

    code, printed = run("replay", saved, session, capsys=capsys)
    assert code != 0
    assert "no_such_thing" in printed


def test_an_attribute_nothing_reads_is_reported_as_a_warning(saved, tmp_path, capsys):
    session = tmp_path / "warned.json"
    session.write_text(json.dumps({"steps": [
        {"operation": "compute", "method": "catalogue", "attributes": {"noo": 1}}]}),
        encoding="utf-8")

    code, printed = run("check", saved, session, capsys=capsys)
    assert code == 0, "a warning is not a refusal"
    assert "noo" in printed
