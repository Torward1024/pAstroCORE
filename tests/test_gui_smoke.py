"""Every GUI module imports, and the main window can be built.

This is the cheapest test in the suite and catches the most embarrassing failure: a rename in
the model that leaves a dialog referring to a method that no longer exists, found by a user
rather than by a build.

It proves nothing about behaviour. It proves the application still starts, which is exactly
what a refactoring of the layers underneath it threatens.

Qt runs on the offscreen platform, so this works on a build machine with no display.
"""
import importlib
import os
import pathlib
import pkgutil

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

GUI = pathlib.Path(__file__).parent.parent / "pastrocore" / "gui"


def gui_modules():
    """Every module in the GUI package, generated and hand-written alike."""
    return sorted(name for _, name, _ in pkgutil.iter_modules([str(GUI)]))


@pytest.fixture(scope="session")
def qt_application():
    """One QApplication for the session; Qt permits no more."""
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication([])
    yield application


@pytest.mark.parametrize("module", gui_modules())
def test_a_gui_module_imports(qt_application, module):
    """A module that cannot be imported is a window that cannot be opened."""
    importlib.import_module(f"pastrocore.gui.{module}")


def test_every_gui_module_is_covered():
    """The parametrization is generated, so this guards against it silently finding nothing."""
    assert len(gui_modules()) > 40, f"only {len(gui_modules())} GUI modules found"


def test_the_main_window_can_be_built(qt_application):
    """The application's entry point, constructed without being shown.

    This was the one part of the interface no test could reach: the window lived in
    `pastrocore.py` beside the `pastrocore` package, so `import pastrocore` found the package
    and the script was unreachable. It now lives in `pastrocore.app`.
    """
    from pastrocore.app import PAstroCoreMainWindow

    window = PAstroCoreMainWindow()
    try:
        assert window.windowTitle()
    finally:
        window.close()
        window.deleteLater()


def test_the_launcher_imports():
    """`run.py` is the entry point users type; it must at least resolve."""
    import pathlib as _pathlib

    launcher = _pathlib.Path(__file__).parent.parent / "run.py"
    assert launcher.exists(), "run.py is missing"
    assert "from pastrocore.app import main" in launcher.read_text(encoding="utf-8")


def test_the_shipped_settings_use_portable_paths():
    r"""The settings file the repository ships was written on Windows.

    On Linux `catalogs\sources.dat` is not a directory and a file, it is one filename with a
    backslash in it, so the catalogs failed to load and the application then opened a modal
    dialog from inside its constructor -- which on a build machine hung for ten minutes and to
    a user would look like a program that will not start.
    """
    import json
    import pathlib as _pathlib

    settings = _pathlib.Path(__file__).parent.parent / "settings.pastro"
    data = json.loads(settings.read_text(encoding="utf-8"))
    for key in ("sources_catalog_path", "telescopes_catalog_path"):
        assert "\\" not in data[key], f"{key} is a Windows-only path: {data[key]!r}"


def test_a_settings_path_written_on_another_platform_still_resolves():
    from pastrocore.app import _portable

    assert _portable(r"catalogs\sources.dat").endswith("sources.dat")
    assert _portable("catalogs/sources.dat").endswith("sources.dat")


def test_the_constructor_opens_no_modal_dialog():
    """A window that needs a click to finish constructing cannot be tested, and cannot start."""
    import ast
    import pathlib as _pathlib

    source = (_pathlib.Path(__file__).parent.parent / "pastrocore" / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    constructors = [node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef)
                    and node.name in ("__init__", "initialize_catalog_manager")]

    for node in constructors:
        for call in ast.walk(node):
            if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                    and isinstance(call.func.value, ast.Name)
                    and call.func.value.id == "QMessageBox"):
                raise AssertionError(
                    f"{node.name} opens a modal QMessageBox at line {call.lineno}")


@pytest.fixture
def window(qt_application, project):
    """The main window holding the fixture project, constructed but never shown."""
    from pastrocore.app import PAstroCoreMainWindow
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    built = PAstroCoreMainWindow()
    built.project = project
    built.manipulator = ScheduleManipulator(project)
    try:
        yield built
    finally:
        built.close()
        built.deleteLater()


def test_opening_asks_for_a_directory(tmp_path, monkeypatch, window):
    """A project is a directory, so the dialog that opens one asks for a directory.

    It used to call `getOpenFileName`, which cannot select a directory at all -- a user had to
    navigate inside the project and pick `project.json`, and that worked only because
    `ScheduleProject.open` was written to tolerate being handed it.
    """
    from PySide6.QtWidgets import QFileDialog

    root = tmp_path / "saved.pastro"
    window.project.save(str(root))

    asked = []
    monkeypatch.setattr(QFileDialog, "getExistingDirectory",
                        staticmethod(lambda *a, **k: asked.append(a) or str(root)))
    monkeypatch.setattr(QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: pytest.fail("open must not ask for a file")))
    window.open_project()

    assert asked, "the directory chooser was never shown"
    assert pathlib.Path(window.current_project_path) == root


def test_opening_something_that_is_not_a_project_says_so(tmp_path, monkeypatch, window):
    """A directory chooser will happily return any directory, so the answer has to be checked."""
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    plain = tmp_path / "just_a_folder"
    plain.mkdir()
    before = window.project

    warned = []
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(plain)))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: warned.append(a)))
    window.open_project()

    assert warned, "the user must be told, rather than shown a traceback"
    assert window.project is before, "the open project must be left alone"


def test_saving_from_the_window_writes_a_directory(tmp_path, monkeypatch, window):
    """The whole point: the interface has to produce the new format, not the old one."""
    from PySide6.QtWidgets import QFileDialog

    target = tmp_path / "fresh.pastro"
    target.mkdir()
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(target)))
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: pytest.fail("save must not ask for a file")))
    window.save_project_as()

    assert (target / "project.json").is_file()
    assert (target / "results").is_dir()


def test_saving_into_a_folder_holding_something_else_asks_first(tmp_path, monkeypatch, window):
    """A directory chooser cannot warn about this, so the application has to.

    Choosing a folder that already holds a user's files would drop `project.json` and a
    `results/` directory in among them with nothing said.
    """
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    occupied = tmp_path / "my_documents"
    occupied.mkdir()
    (occupied / "notes.txt").write_text("something of mine", encoding="utf-8")

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(occupied)))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))
    window.save_project_as()

    assert not (occupied / "project.json").exists(), "declining must write nothing"
    assert (occupied / "notes.txt").is_file()

    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    window.save_project_as()
    assert (occupied / "project.json").is_file(), "agreeing must go ahead"


def test_saving_into_an_empty_folder_asks_nothing(tmp_path, monkeypatch, window):
    """An empty folder is what the dialog's New Folder button produces."""
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    fresh = tmp_path / "brand_new.pastro"
    fresh.mkdir()
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(fresh)))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: pytest.fail("an empty folder needs no question")))
    window.save_project_as()

    assert (fresh / "project.json").is_file()


def test_the_window_keeps_its_results_where_a_crash_cannot_reach_them(window, tmp_path, monkeypatch):
    """A calculation must be on disk before anyone presses save."""
    from pastrocore.base.scratch import ScratchSpace
    import polars as pl

    space = ScratchSpace(root=tmp_path / "scratch", session="test-session")
    window.project.attach_results_store(space.store)

    observation = window.project.get_observation(next(iter(window.project.get_items())))
    observation.set_calculated_data_by_key("fresh", pl.DataFrame({"x": [1.0]}), {})

    assert list((space.path / "results").rglob("*.parquet")), "not waiting for a save"


def test_a_clean_close_takes_the_scratch_with_it(window, tmp_path):
    """Only on this path: a session that ended normally has nothing worth recovering."""
    from pastrocore.base.scratch import ScratchSpace
    import polars as pl

    space = ScratchSpace(root=tmp_path / "scratch", session="closing")
    window.project._scratch = space
    space.store.write("obs", "a", pl.DataFrame({"x": [1.0]}), {})
    assert space.path.exists()

    window.close()

    assert not (tmp_path / "scratch" / "closing").exists()


def test_the_recovery_offer_is_not_raised_from_the_constructor():
    """A modal dialog with no window to own it blocks forever. That hung the build for ten
    minutes once, and this is the second thing that could have done it."""
    import inspect

    from pastrocore.app import PAstroCoreMainWindow

    source = inspect.getsource(PAstroCoreMainWindow.__init__)
    assert "_offer_abandoned_sessions" not in source, (
        "the recovery offer must be raised after the window is shown, not while building it")


def test_declining_a_recovered_session_removes_it(window, tmp_path, monkeypatch):
    """The user is asked. The one thing that must never happen is deleting without asking."""
    from PySide6.QtWidgets import QMessageBox
    from pastrocore.base import scratch as scratch_module
    from pastrocore.base.scratch import ScratchSpace
    import polars as pl

    root = tmp_path / "scratch"
    ScratchSpace(root=root, session="1-dead").store.write(
        "obs", "uv_coverage", pl.DataFrame({"x": [1.0]}), {})

    monkeypatch.setattr(scratch_module, "_process_is_alive", lambda pid: False)
    asked = []
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: asked.append(a) or QMessageBox.StandardButton.No))
    window._offer_abandoned_sessions(root=root)

    assert asked, "the user must be asked before anything is removed"
    assert not (root / "1-dead").exists()


def test_keeping_a_recovered_session_leaves_it_alone(window, tmp_path, monkeypatch):
    """The default answer, and the one that matters: the results are still there afterwards."""
    from PySide6.QtWidgets import QMessageBox
    from pastrocore.base import scratch as scratch_module
    from pastrocore.base.scratch import ScratchSpace
    import polars as pl

    root = tmp_path / "scratch"
    ScratchSpace(root=root, session="2-dead").store.write(
        "obs", "uv_coverage", pl.DataFrame({"x": [1.0]}), {})

    monkeypatch.setattr(scratch_module, "_process_is_alive", lambda pid: False)
    asked = []
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: asked.append(a) or QMessageBox.StandardButton.Yes))
    window._offer_abandoned_sessions(root=root)

    assert asked, "an assertion that nothing was deleted is worthless if nothing was offered"
    assert (root / "2-dead" / "results" / "obs" / "uv_coverage.parquet").is_file()
