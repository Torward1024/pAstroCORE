"""What a report sent from a testing machine may and may not carry.

Somebody trying this out has a log, a settings file and a version, and sending them one at a
time takes three emails. One file holds all of it.

What it must not hold is who they are. A log line names the directory a project was opened
from, which is under somebody's home directory, under their name -- so the one thing checked
hardest here is that neither reaches the file.
"""
import json
import pathlib
import sys
import zipfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_a_report_says_what_is_running():
    """A report nobody can place is a report nobody can act on."""
    from pastrocore.diagnostics import report

    said = report()
    for subject in ("pAstroCORE", "msb_arch", "Python", "platform"):
        assert subject in said, f"the report says nothing about {subject}:\n{said}"


def test_nothing_sent_names_the_person_or_their_directories(tmp_path):
    """The log names every directory a project was opened from, and each is under a home
    directory named after somebody."""
    from pastrocore.diagnostics import without_identity

    home = pathlib.Path.home()
    person = home.name
    text = (f"Opened project from {home / 'work' / 'survey.pastro'}\n"
            f"Settings saved to {home}/AppData/Local/pAstroCORE/settings.pastro\n"
            f"user={person} ran it\n")

    clean = without_identity(text)
    assert str(home) not in clean, f"the home directory survived:\n{clean}"
    assert person not in clean, f"the person's name survived:\n{clean}"
    assert "survey.pastro" in clean, "scrubbing took the useful part with it"


@pytest.mark.skipif(sys.platform != "win32", reason="8.3 names are Windows'")
def test_the_short_form_of_a_home_directory_goes_as_well():
    """Windows writes the same directory two ways, and half the paths in a log are the 8.3
    form -- `C:\\Users\\SOMEBO~1`. Scrubbing the long one alone left the short one in."""
    import ctypes

    from pastrocore.diagnostics import without_identity

    held = ctypes.create_unicode_buffer(1024)
    assert ctypes.windll.kernel32.GetShortPathNameW(str(pathlib.Path.home()), held, 1024)
    short = held.value

    clean = without_identity(f"Opened project from {short}\\work\\survey.pastro")
    assert short not in clean, f"the short form survived:\n{clean}"
    assert pathlib.Path(short).name not in clean, f"the short name survived:\n{clean}"


def test_the_file_holds_the_report_the_settings_and_the_log(tmp_path, monkeypatch):
    """Three things are asked for in every exchange about a problem."""
    from pastrocore import diagnostics

    home = tmp_path / "data"
    home.mkdir()
    (home / "settings.pastro").write_text(json.dumps({"theme": "dark"}), encoding="utf-8")
    (home / "output.log").write_text("INFO - started\n" * 50, encoding="utf-8")
    monkeypatch.setattr(diagnostics, "data_home", lambda: home)

    written = diagnostics.collect(tmp_path / "report.zip")

    assert written.is_file()
    with zipfile.ZipFile(written) as held:
        inside = set(held.namelist())
        assert {"report.txt", "settings.pastro", "output.log"} <= inside, inside
        assert "started" in held.read("output.log").decode("utf-8")


def test_a_missing_log_is_said_rather_than_raised(tmp_path, monkeypatch):
    """Somebody reporting a problem on a first run has no log yet, and the report still has
    to reach us."""
    from pastrocore import diagnostics

    home = tmp_path / "empty"
    home.mkdir()
    monkeypatch.setattr(diagnostics, "data_home", lambda: home)

    written = diagnostics.collect(tmp_path / "report.zip")

    with zipfile.ZipFile(written) as held:
        assert "report.txt" in held.namelist()
        assert "no output.log" in held.read("report.txt").decode("utf-8")


def test_the_log_is_cut_to_its_tail(tmp_path, monkeypatch):
    """A log from a long session is megabytes, and what went wrong is at the end of it."""
    from pastrocore import diagnostics

    home = tmp_path / "long"
    home.mkdir()
    (home / "output.log").write_text("".join(f"line {number}\n" for number in range(50_000)),
                                     encoding="utf-8")
    monkeypatch.setattr(diagnostics, "data_home", lambda: home)

    written = diagnostics.collect(tmp_path / "report.zip")

    with zipfile.ZipFile(written) as held:
        kept = held.read("output.log").decode("utf-8").splitlines()
        assert len(kept) <= diagnostics.TAIL + 1
        assert kept[-1] == "line 49999", "the end of the log is what was wanted"
