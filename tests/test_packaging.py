"""An installed pAstroCORE finds its own files.

The application read `catalogs/sources.dat` and wrote `settings.pastro` as paths relative to
wherever it was started. In a checkout that is the repository and everything works; installed
with `pip install .` and started from anywhere else, the catalogs are empty and the settings go
into whichever directory the user happened to be in.

That is what R4 means by "gives a working command", so it is what these check -- from a
different working directory, which is the only way to tell the two apart.
"""
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def elsewhere(tmp_path, monkeypatch):
    """Run from a directory that is not the checkout."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_the_catalogs_are_found_from_any_directory(elsewhere):
    from pastrocore.paths import shipped_catalog

    for name in ("sources.dat", "telescopes.dat"):
        assert shipped_catalog(name).is_file(), f"{name} is not where an install would find it"


def test_the_catalogs_are_inside_the_package():
    """A file beside the package is not in the wheel. This is what makes them shippable."""
    from pastrocore.paths import shipped_catalog

    import pastrocore
    package = Path(pastrocore.__file__).resolve().parent
    assert package in shipped_catalog("sources.dat").resolve().parents


def test_the_defaults_point_at_files_that_exist(elsewhere):
    """The defaults were relative, so from anywhere else they named nothing and the application
    started with empty catalogs and said so only in the log."""
    from pastrocore.app import PAstroCoreMainWindow

    settings = PAstroCoreMainWindow.load_settings()
    assert Path(settings["sources_catalog_path"]).is_file()
    assert Path(settings["telescopes_catalog_path"]).is_file()


def test_the_settings_live_in_one_place_per_user(elsewhere, monkeypatch):
    from pastrocore.base.scratch import data_home
    from pastrocore.paths import settings_file

    assert settings_file() == data_home() / "settings.pastro", (
        "settings written where the application was started are settings a user loses")


def test_settings_left_in_a_working_directory_are_adopted_once(tmp_path, monkeypatch):
    """Anyone upgrading has a `settings.pastro` beside the checkout. Reading it and then
    writing somewhere else would look like the settings had been forgotten."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "user"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user"))
    (tmp_path / "settings.pastro").write_text(json.dumps({"time_step": 1234}), encoding="utf-8")

    from pastrocore.app import PAstroCoreMainWindow
    from pastrocore.paths import settings_file

    settings = PAstroCoreMainWindow.load_settings()
    assert settings["time_step"] == 1234, "what the user had was not read"
    assert settings_file().is_file(), "and was not kept where it will be read next time"
    assert json.loads(settings_file().read_text(encoding="utf-8"))["time_step"] == 1234


def test_a_stored_path_that_no_longer_exists_falls_back(tmp_path, monkeypatch):
    """A settings file records absolute paths, and an install that moves invalidates them.
    Starting with empty catalogs and a line in the log is how that used to present."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "user"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user"))
    (tmp_path / "settings.pastro").write_text(json.dumps({
        "sources_catalog_path": str(tmp_path / "gone" / "sources.dat")}), encoding="utf-8")

    from pastrocore.app import PAstroCoreMainWindow

    settings = PAstroCoreMainWindow.load_settings()
    assert Path(settings["sources_catalog_path"]).is_file(), (
        "a path that no longer exists must fall back to what was shipped")


# --- the package itself ---------------------------------------------------------------------

def test_the_project_declares_how_to_build_itself():
    manifest = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert manifest["project"]["name"] == "pastrocore"
    assert manifest["project"]["scripts"]["pastrocore"] == "pastrocore.app:main"
    assert "version" in manifest["project"]["dynamic"], (
        "the version lives in pastrocore/__init__.py and must not be repeated here")


def test_the_version_is_stated_once():
    """MSB tagged 1.1.2 with one of its two version numbers bumped, built 1.1.1 again and PyPI
    refused it. Two sources of one number is one too many."""
    import pastrocore

    manifest = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "version" not in manifest["project"], "declared in two places"
    assert manifest["tool"]["hatch"]["version"]["path"] == "pastrocore/__init__.py"
    assert pastrocore.__version__


def test_every_dependency_the_code_imports_is_declared():
    """The dependency list and requirements.txt are two lists of one thing, and the one that
    goes stale is the one nothing installs from."""
    manifest = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = {name.split("[")[0].split(">")[0].split("=")[0].strip().lower()
                for name in manifest["project"]["dependencies"]}

    for needed in ("msb_arch", "polars", "astropy", "numpy", "scipy", "matplotlib",
                   "pyside6", "pyarrow", "psutil"):
        assert needed in declared, f"{needed} is imported and not declared"


def test_the_data_files_are_included_in_the_wheel():
    manifest = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    wheel = manifest["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert "pastrocore" in wheel["packages"]


@pytest.mark.slow
def test_the_wheel_builds_and_carries_the_catalogs(tmp_path):
    """The only check that says the packaging works rather than that it is declared."""
    build = subprocess.run([sys.executable, "-m", "build", "--wheel", "--outdir", str(tmp_path)],
                           cwd=ROOT, capture_output=True, text=True)
    if build.returncode != 0 and "No module named build" in (build.stdout + build.stderr):
        pytest.skip("the build module is not installed here")
    assert build.returncode == 0, build.stdout + build.stderr

    import zipfile

    wheel = next(tmp_path.glob("*.whl"))
    names = zipfile.ZipFile(wheel).namelist()
    assert "pastrocore/catalogs/sources.dat" in names
    assert "pastrocore/gui/ui_main_window.py" in names
    assert any(name.endswith("entry_points.txt") for name in names)


def test_a_catalogue_the_user_chose_survives_a_restart(tmp_path, monkeypatch):
    """The point of the fallback is a path that is *gone*, not one the user picked.

    Preferences writes `sources_catalog_path`, so choosing a catalogue has to mean the next
    start reads that one and not the shipped one.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "user"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user"))

    from pastrocore.app import PAstroCoreMainWindow

    mine = tmp_path / "mine" / "sources.dat"
    mine.parent.mkdir()
    mine.write_text("# my own catalogue\n", encoding="utf-8")

    settings = PAstroCoreMainWindow.load_settings()
    settings["sources_catalog_path"] = str(mine)
    PAstroCoreMainWindow._write_settings(settings)

    read_back = PAstroCoreMainWindow.load_settings()
    assert Path(read_back["sources_catalog_path"]) == mine, (
        "the catalogue the user chose was replaced by the shipped one")
    assert Path(read_back["telescopes_catalog_path"]).is_file(), "and the other still resolves"


def test_a_catalogue_that_was_deleted_does_not_silently_empty_the_application(tmp_path, monkeypatch):
    """The other half: the chosen file is honoured until it is not there."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "user"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user"))

    from pastrocore.app import PAstroCoreMainWindow
    from pastrocore.paths import shipped_catalog

    mine = tmp_path / "mine" / "sources.dat"
    mine.parent.mkdir()
    mine.write_text("# my own catalogue\n", encoding="utf-8")
    PAstroCoreMainWindow._write_settings({"sources_catalog_path": str(mine)})
    assert Path(PAstroCoreMainWindow.load_settings()["sources_catalog_path"]) == mine

    mine.unlink()
    fallen_back = PAstroCoreMainWindow.load_settings()["sources_catalog_path"]
    assert Path(fallen_back) == shipped_catalog("sources.dat")


def test_the_about_dialog_shows_the_version_the_package_states(qt_application):
    """It was a literal in the `.ui`, so a release had to remember two places -- and 0.8.0
    shipped with the form still saying 0.7.0."""
    import pastrocore
    from pastrocore.gui.p_dialog_about import AboutDialog

    dialog = AboutDialog()
    assert dialog.ui.labelVersion.text() == f"Version {pastrocore.__version__}"
    dialog.close()


def test_the_readme_states_the_version_the_package_does():
    """Including the badge, which is the copy nobody looks at when cutting a release."""
    import re

    import pastrocore

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    stated = re.search(r"^Version (\d+\.\d+\.\d+)", readme, re.M)
    assert stated and stated.group(1) == pastrocore.__version__, (
        f"the README says {stated and stated.group(1)}, the package says "
        f"{pastrocore.__version__}")

    badge = re.search(r"badge/version-(\d+\.\d+\.\d+)-", readme)
    assert badge and badge.group(1) == pastrocore.__version__, (
        f"the version badge says {badge and badge.group(1)}")


def test_the_readme_asks_for_the_msb_it_actually_needs():
    """`accepts` arrived in 1.5.0 and the exporter does not work without it. A README naming an
    older one is an installation that fails at the first export."""
    import re
    import tomllib

    import msb_arch

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    asked = re.search(r"`msb_arch` (\d+\.\d+\.\d+) or later", readme)
    assert asked, "the README does not say which msb_arch it needs"

    manifest = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = next(name for name in manifest["project"]["dependencies"]
                    if name.startswith("msb_arch"))
    assert asked.group(1) == declared.split(">=")[1], (
        f"the README says {asked.group(1)}, pyproject says {declared}")

    badge = re.search(r"MSB%20(\d+\.\d+\.\d+)", readme)
    assert badge and badge.group(1) == asked.group(1), "and the badge says something else again"
    assert msb_arch.__version__ >= asked.group(1), "the installed msb_arch is older than that"


def test_a_legacy_relative_path_is_repaired_rather_than_warned_about_forever(tmp_path, monkeypatch):
    """A settings file written before the catalogues moved names them relatively, which can
    never resolve from a per-user directory. Falling back every start and warning every start
    is a warning nobody can act on:

        WARNING - Catalogue 'catalogs\sources.dat' is not there; using the one shipped at ...

    So a *relative* path -- which is always a leftover -- is corrected in the settings once. An
    absolute path that is missing keeps warning: that one is a real problem, and it may be a
    network drive that will come back.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "user"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user"))

    from pastrocore.app import PAstroCoreMainWindow
    from pastrocore.paths import settings_file, shipped_catalog

    PAstroCoreMainWindow._write_settings({
        "sources_catalog_path": "catalogs/sources.dat",
        "telescopes_catalog_path": "catalogs/telescopes.dat"})

    first = PAstroCoreMainWindow.load_settings()
    assert Path(first["sources_catalog_path"]) == shipped_catalog("sources.dat")

    stored = json.loads(settings_file().read_text(encoding="utf-8"))
    assert Path(stored["sources_catalog_path"]) == shipped_catalog("sources.dat"), (
        "the leftover is still in the file, so the next start warns about it again")


def test_a_missing_absolute_path_is_kept_and_still_reported(tmp_path, monkeypatch):
    """The other half. A path the user chose that is not there right now is a problem worth
    saying, and overwriting it would lose what they chose."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "user"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user"))

    from pastrocore.app import PAstroCoreMainWindow
    from pastrocore.paths import settings_file

    chosen = str(tmp_path / "network" / "sources.dat")
    PAstroCoreMainWindow._write_settings({"sources_catalog_path": chosen})
    PAstroCoreMainWindow.load_settings()

    stored = json.loads(settings_file().read_text(encoding="utf-8"))
    assert stored["sources_catalog_path"] == chosen, "the user's choice was overwritten"
