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


def test_the_shipped_settings_pin_no_catalogue_path():
    r"""The settings file the repository ships was written on Windows and named the catalogues
    by a relative path.

    On Linux `catalogs\sources.dat` is not a directory and a file, it is one filename with a
    backslash in it, so the catalogues failed to load and the application then opened a modal
    dialog from inside its constructor -- which on a build machine hung for ten minutes and to
    a user would look like a program that will not start. Relative to what, besides, was
    whichever directory it was started from.

    Neither key belongs in a shipped file: the catalogues come with the install and are found
    beside the package. A user pointing at their own still gets one recorded.
    """
    import json
    import pathlib as _pathlib

    settings = _pathlib.Path(__file__).parent.parent / "settings.pastro"
    data = json.loads(settings.read_text(encoding="utf-8"))
    for key in ("sources_catalog_path", "telescopes_catalog_path"):
        assert key not in data, f"{key} is pinned to one machine: {data.get(key)!r}"


def test_a_settings_path_written_on_another_platform_still_resolves():
    from pastrocore.paths import portable

    assert portable(r"catalogs\sources.dat").endswith("sources.dat")
    assert portable("catalogs/sources.dat").endswith("sources.dat")


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

    observation = window.project.observations()[0]
    observation.set_calculated_data_by_key("fresh", pl.DataFrame({"x": [1.0]}), {})

    assert list((space.path / "results").rglob("*.parquet")), "not waiting for a save"


def test_a_clean_close_takes_the_scratch_with_it(window, tmp_path, monkeypatch):
    """Only on this path: a session that ended normally has nothing worth recovering.

    It asks first when the scratch holds results, since those are exactly what a clean close
    would destroy -- the thing writing them through to disk exists to prevent. Discarding is
    then the user's decision rather than the window's.
    """
    from PySide6.QtWidgets import QMessageBox

    from pastrocore.base.scratch import ScratchSpace
    import polars as pl

    space = ScratchSpace(root=tmp_path / "scratch", session="closing")
    window.project._scratch = space
    space.store.write("obs", "a", pl.DataFrame({"x": [1.0]}), {})
    assert space.path.exists()

    asked = {}
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *args, **kwargs: (
                            asked.update(seen=True), QMessageBox.StandardButton.Discard)[1]))

    window.close()

    assert asked, "the results were discarded without a word"
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

    monkeypatch.setattr(scratch_module, "live_pids", lambda: set())
    asked = []
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: asked.append(a) or QMessageBox.StandardButton.No))
    window._offer_abandoned_sessions(root=root)

    assert asked, "the user must be asked before anything is removed"
    assert not (root / "1-dead").exists()


def test_keeping_a_recovered_session_leaves_it_alone(window, tmp_path, monkeypatch):
    """The default answer, and the one that matters: the results are still there afterwards."""
    from PySide6.QtWidgets import QMessageBox
    import os

    from pastrocore.base import scratch as scratch_module
    from pastrocore.base.scratch import ScratchSpace
    import polars as pl

    root = tmp_path / "scratch"
    ScratchSpace(root=root, session="2-dead").store.write(
        "obs", "uv_coverage", pl.DataFrame({"x": [1.0]}), {})

    monkeypatch.setattr(scratch_module, "live_pids", lambda: set())
    asked = []
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: asked.append(a) or QMessageBox.StandardButton.Yes))
    window._offer_abandoned_sessions(root=root)

    assert asked, "an assertion that nothing was deleted is worthless if nothing was offered"
    assert (root / "2-dead" / "results" / "obs" / "uv_coverage.parquet").is_file()


# --- what the interface does with it ---------------------------------------------------------

def test_the_explorer_labels_a_stale_observation(project, qt_application):
    """T2 in the interface: a label the user can see, not a dialog that interrupts them."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QTreeView

    from pastrocore.app import PAstroCoreMainWindow
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    observation = project.observations()[0]
    observation.calculated_data.clear()
    ScheduleManipulator(project).calculate(observation, method="uv_coverage",
                                          time_step=300.0, raise_on_error=False)

    window = PAstroCoreMainWindow()
    try:
        window.project = project
        window.manipulator = ScheduleManipulator(project)
        window.update_project_explorer()

        explorer = window.ui.dockWidget.findChild(QTreeView, "projectExplorer")

        def labels():
            # Re-fetched every time: update_project_explorer installs a *new* model, so a
            # reference taken once goes on describing the tree as it used to be.
            model = explorer.model()
            found = []

            def walk(item):
                for row in range(item.rowCount()):
                    child = item.child(row, 0)
                    if child is None:
                        continue
                    if child.data(Qt.UserRole) == "observation":
                        found.append(child.text())
                    walk(child)

            for row in range(model.rowCount()):
                top = model.item(row, 0)
                if top.data(Qt.UserRole) == "observation":
                    found.append(top.text())
                walk(top)
            return found

        assert all("stale" not in text for text in labels()), "nothing is stale yet"

        telescope = observation.get_telescopes().get_active_items()[0]
        telescope.set({"x": telescope.get_coordinates()[0] + 1_000_000.0})
        window.update_project_explorer()

        assert any("stale" in text for text in labels()), (
            "a stale observation must be visible in the explorer")
    finally:
        window.close()
        window.deleteLater()


def test_editing_a_telescope_makes_the_label_appear_by_itself(project, qt_application):
    """The question "where is it shown" is only half an answer without "and when".

    A label that appears only when something else happens to refresh the tree is worse than no
    label, because it would be right sometimes. This goes through the signal an editor emits
    rather than calling the refresh directly.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QTreeView

    from pastrocore.app import PAstroCoreMainWindow
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    observation = project.observations()[0]
    observation.calculated_data.clear()
    ScheduleManipulator(project).calculate(observation, method="uv_coverage",
                                           time_step=300.0, raise_on_error=False)

    window = PAstroCoreMainWindow()
    try:
        window.project = project
        window.manipulator = ScheduleManipulator(project)
        window.clear_connections(is_initial_setup=True)
        window.setup_connections()
        window.update_project_explorer()

        explorer = window.ui.dockWidget.findChild(QTreeView, "projectExplorer")

        def observation_labels():
            model = explorer.model()
            found = []

            def walk(item):
                for row in range(item.rowCount()):
                    child = item.child(row, 0)
                    if child is None:
                        continue
                    if child.data(Qt.UserRole) == "observation":
                        found.append(child.text())
                    walk(child)

            for row in range(model.rowCount()):
                walk(model.item(row, 0))
            return found

        assert all("stale" not in text for text in observation_labels())

        telescope = observation.get_telescopes().get_active_items()[0]
        telescope.set({"x": telescope.get_coordinates()[0] + 1_000_000.0})

        # What an editor tab emits when it changes something, rather than a direct refresh.
        window.handle_observationTab_observation_updated()

        assert any("stale" in text for text in observation_labels()), (
            "an edit must make the label appear without anything else being clicked")
    finally:
        window.close()
        window.deleteLater()


# --- closing must not throw away what was calculated -------------------------------------------

def _project_with_unsaved_results(tmp_path):
    """A project whose results live in this session's scratch, which is where they live until
    it is saved.

    Notes:
        - The scratch is rooted in `tmp_path`, not where the application puts it. A scratch is
          named for the process, so every window built in one test run would otherwise share
          one directory -- and results written by one test would make another test's window ask
          about them on close, with a modal dialog and no one to answer it.
    """
    import json

    import conftest
    from pastrocore.base.scratch import ScratchSpace
    from pastrocore.super.schedule_manipulator import ScheduleManipulator
    from pastrocore.super.schedule_project import ScheduleProject

    project = ScheduleProject.from_dict(json.loads(conftest.FIXTURE.read_text(encoding="utf-8")))
    observation = project.observations()[0]
    observation.clear_calculated_data()
    project._scratch = ScratchSpace(root=tmp_path / "scratch")
    project.hold_results_in_scratch()
    ScheduleManipulator(project).compute(
        obj=None, method="run", targets=[observation], calculations=["time_arrays"],
        time_step=600.0)
    return project


def test_closing_with_unsaved_results_asks_before_discarding_them(qt_application, monkeypatch,
                                                                  tmp_path):
    """Results are written to a scratch directory the moment they are calculated, and live
    there until the project is saved. `closeEvent` discarded that directory on every normal
    close -- so calculating and then closing the window destroyed the results, and the project's
    own `results/` was empty because it had been saved before the calculation.

    The mechanism that exists to survive a crash was deleting a day of calculation on a tidy
    exit, without a word.
    """
    from PySide6.QtGui import QCloseEvent
    from PySide6.QtWidgets import QMessageBox

    from pastrocore.app import PAstroCoreMainWindow

    window = PAstroCoreMainWindow()
    window.project = _project_with_unsaved_results(tmp_path)
    scratch = window.project.scratch.path
    assert scratch is not None and scratch.exists()

    asked = {}
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *args, **kwargs: (
                            asked.update(text=args[2]), QMessageBox.StandardButton.Cancel)[1]))

    event = QCloseEvent()
    window.closeEvent(event)

    assert asked, "the window closed without asking about results nobody has saved"
    assert not event.isAccepted(), "cancelling the question still closed the window"
    assert scratch.exists(), "the results were discarded anyway"


def test_closing_a_project_with_nothing_unsaved_asks_nothing(qt_application, monkeypatch):
    """Nothing calculated, nothing to lose, no question."""
    from PySide6.QtGui import QCloseEvent
    from PySide6.QtWidgets import QMessageBox

    from pastrocore.app import PAstroCoreMainWindow

    window = PAstroCoreMainWindow()
    asked = {}
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *args, **kwargs: (
                            asked.update(text=args[2]), QMessageBox.StandardButton.Yes)[1]))

    window.closeEvent(QCloseEvent())
    assert not asked, "a window with nothing calculated asked about saving anyway"


def test_starting_a_new_project_does_not_leave_a_scratch_behind(qt_application, monkeypatch):
    """Reported: two recovery offers on one start, from two different scratch directories.

    A new project is a new `ScheduleProject`, and a project makes its own scratch on first use.
    Nothing discarded the outgoing one, so every File -> New Project in a session left a
    directory that the next start offered to recover -- from a session that had ended perfectly
    normally and had nothing in it.
    """
    from pastrocore.app import PAstroCoreMainWindow

    window = PAstroCoreMainWindow()
    try:
        window.project.hold_results_in_scratch()
        first = window.project.scratch.path
        assert first is not None and first.exists()

        window.new_project()

        assert window.project.scratch.path != first, "a new project reuses the old scratch"
        assert not first.exists(), (
            "the scratch of the project that was replaced is still there, and the next start "
            "will offer to recover it")
    finally:
        window.close()


def test_a_scratch_holding_results_is_kept_when_the_project_is_replaced(qt_application, monkeypatch,
                                                                        tmp_path):
    """The other half. Litter is worth clearing; a day of calculation is not."""
    from pastrocore.app import PAstroCoreMainWindow

    window = PAstroCoreMainWindow()
    try:
        window.project = _project_with_unsaved_results(tmp_path)
        held = window.project.scratch.path
        assert held is not None and held.exists()

        window._cleanup_project()

        assert held.exists(), "results nobody has saved were discarded by replacing the project"
    finally:
        window.project = None           # or closing asks about them, and blocks the suite
        window.close()
