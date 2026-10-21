"""Finding out that a newer version exists, and fetching it.

Everything that decides anything is here rather than in the dialog: which release is newer,
which file belongs to this machine, and whether a URL may be downloaded at all. The dialog
asks these and shows the answer.

Nothing here reaches the network. What the API would say is handed in, because what is being
checked is the deciding, not GitHub.
"""
import json
import pathlib

import pytest

from pastrocore import updates


def release(tag="v2.0.0", names=("pAstroCORE-2.0.0-windows-x64.exe",
                                "pAstroCORE-2.0.0-macos-arm64.dmg",
                                "pAstroCORE-2.0.0-linux-x86_64.AppImage")):
    """What the API returns for a release, cut down to what is read."""
    return {"tag_name": tag, "html_url": f"{updates.SITE}/releases/tag/{tag}",
            "body": "what changed",
            "assets": [{"name": name, "size": 100,
                        "browser_download_url": f"https://github.com/Torward1024/pAstroCORE/"
                                                f"releases/download/{tag}/{name}"}
                       for name in names]}


@pytest.mark.parametrize("running, found, newer", [
    ("1.20.0", "v1.20.0", False),
    ("1.20.0", "v1.20.1", True),
    ("1.20.0", "v1.21.0", True),
    ("1.20.0", "v2.0.0", True),
    ("1.20.0", "v1.19.9", False),
    ("1.9.0", "v1.10.0", True),            # as numbers, not as text: 10 comes after 9
    ("1.20.0", "1.21.0", True),            # with or without the v
])
def test_which_release_is_newer(running, found, newer):
    assert updates.is_newer(found, running) is newer


def test_a_version_that_makes_no_sense_is_not_newer():
    """A tag nobody can read is not an invitation to download something."""
    assert updates.is_newer("latest", "1.20.0") is False
    assert updates.is_newer("", "1.20.0") is False


@pytest.mark.parametrize("platform, expected", [
    ("win32", "pAstroCORE-2.0.0-windows-x64.exe"),
    ("darwin", "pAstroCORE-2.0.0-macos-arm64.dmg"),
    ("linux", "pAstroCORE-2.0.0-linux-x86_64.AppImage"),
])
def test_the_file_for_this_machine_is_the_one_offered(platform, expected):
    found = updates.asset_for(release(), platform)

    assert found is not None and found["name"] == expected


def test_a_release_with_nothing_for_this_machine_offers_nothing():
    """A release whose build failed for one platform has two files, not three."""
    only_linux = release(names=("pAstroCORE-2.0.0-linux-x86_64.AppImage",))

    assert updates.asset_for(only_linux, "win32") is None


def test_only_this_project_s_own_releases_may_be_downloaded():
    """The URL comes from an answer off the network, and what is downloaded is run. It is
    taken only when it is this repository's own release asset."""
    assert updates.may_fetch(f"{updates.SITE}/releases/download/v2.0.0/pAstroCORE.exe")

    for refused in (
            "http://github.com/Torward1024/pAstroCORE/releases/download/v2/x.exe",  # not https
            "https://github.com/someone/else/releases/download/v2/x.exe",
            "https://example.com/pAstroCORE.exe",
            "https://github.com.evil.test/Torward1024/pAstroCORE/releases/download/v2/x.exe",
            "https://raw.githubusercontent.com/Torward1024/pAstroCORE/main/setup.exe"):
        assert not updates.may_fetch(refused), f"{refused} should not be fetched"


def test_what_is_downloaded_is_what_was_offered(tmp_path, monkeypatch):
    """A file of another length is not the file that was described, so it is not kept."""
    said = {"name": "pAstroCORE-2.0.0-windows-x64.exe", "size": 5,
            "browser_download_url": f"{updates.SITE}/releases/download/v2.0.0/x.exe"}

    monkeypatch.setattr(updates, "_read", lambda url, report: b"too long for five")
    with pytest.raises(ValueError, match="length"):
        updates.fetch(said, tmp_path)

    assert not list(tmp_path.iterdir()), "a file that did not match was kept"


def test_a_download_lands_under_the_name_it_was_offered_under(tmp_path, monkeypatch):
    said = {"name": "pAstroCORE-2.0.0-windows-x64.exe", "size": 4,
            "browser_download_url": f"{updates.SITE}/releases/download/v2.0.0/x.exe"}
    monkeypatch.setattr(updates, "_read", lambda url, report: b"abcd")

    written = updates.fetch(said, tmp_path)

    assert written == tmp_path / said["name"]
    assert written.read_bytes() == b"abcd"


def test_the_check_reports_what_it_found(monkeypatch):
    """One answer the dialog shows: whether there is something newer, and what it is."""
    monkeypatch.setattr(updates, "_ask_github", lambda: release("v2.0.0"))

    found = updates.check("1.20.0", "win32")

    assert found.newer is True
    assert found.version == "2.0.0"
    assert found.asset["name"].endswith(".exe")
    assert found.page.endswith("/releases/tag/v2.0.0")


def test_the_check_says_so_when_there_is_nothing_newer(monkeypatch):
    monkeypatch.setattr(updates, "_ask_github", lambda: release("v1.20.0"))

    found = updates.check("1.20.0", "win32")

    assert found.newer is False and found.version == "1.20.0"


def test_a_network_that_does_not_answer_is_reported_rather_than_raised(monkeypatch):
    """Somebody on a laboratory network with no way out should be told that, once."""
    def refuse():
        raise OSError("no route to host")

    monkeypatch.setattr(updates, "_ask_github", refuse)
    found = updates.check("1.20.0", "win32")

    assert found.newer is False
    assert found.error and "no route" in found.error


def test_too_many_checks_is_said_in_words(monkeypatch):
    """GitHub allows sixty questions an hour from one address, and a department behind one
    address reaches that. `HTTP Error 403: rate limit exceeded` is not something to show."""
    import urllib.error

    def refuse():
        raise urllib.error.HTTPError(updates.API, 403, "rate limit exceeded", {}, None)

    monkeypatch.setattr(updates, "_ask_github", refuse)
    found = updates.check("1.20.0", "win32")

    assert found.newer is False
    assert "too many" in found.error.lower(), found.error
    assert updates.SITE in found.error, "it should say where to look instead"


def test_the_menu_item_asks_and_says_what_it_found(project, qt_application, monkeypatch):
    """Help -> Check for Updates, end to end but for the network: it asks, and whatever
    comes back it says something rather than nothing."""
    from PySide6.QtWidgets import QMessageBox

    from pastrocore.app import PAstroCoreMainWindow
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    said = []
    for level in ("information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, level,
                            staticmethod(lambda parent, title, text, *rest, held=said:
                                         held.append(text)))
    monkeypatch.setattr(updates, "_ask_github", lambda: release("v9.9.9"))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))

    window = PAstroCoreMainWindow()
    window.project = project
    window.manipulator = ScheduleManipulator(project)
    try:
        assert window.ui.actionCheckForUpdates.isEnabled(), "the menu item is not there"
        window.check_for_updates()
    finally:
        window.close()
        window.deleteLater()

    # Nothing was said because the question was answered No -- which is itself the point:
    # it got as far as offering, rather than stopping at the check.
    assert not said, f"it reported instead of offering the download: {said}"


def test_nothing_newer_is_said_plainly(project, qt_application, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from pastrocore.app import PAstroCoreMainWindow
    from pastrocore.super.schedule_manipulator import ScheduleManipulator
    from pastrocore import __version__

    said = []
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda parent, title, text, *rest: said.append(text)))
    monkeypatch.setattr(updates, "_ask_github", lambda: release(f"v{__version__}"))

    window = PAstroCoreMainWindow()
    window.project = project
    window.manipulator = ScheduleManipulator(project)
    try:
        window.check_for_updates()
    finally:
        window.close()
        window.deleteLater()

    assert said and __version__ in said[0] and "latest" in said[0], said
