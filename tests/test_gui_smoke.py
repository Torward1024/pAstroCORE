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


def test_the_window_remembers_the_project_not_the_file_inside_it(tmp_path, monkeypatch, window):
    """A user can navigate into a project and pick project.json. What gets remembered has to
    be the project directory, or the next save would write a directory over the model file."""
    from pastrocore.super.schedule_project import ScheduleProject
    from PySide6.QtWidgets import QFileDialog

    root = tmp_path / "saved.pastro"
    window.project.save(str(root))

    monkeypatch.setattr(QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (str(root / "project.json"), "")))
    window.open_project()

    assert pathlib.Path(window.current_project_path) == root

    window.save_project()
    assert (root / "project.json").is_file(), "the model file must still be a file"
    assert root.is_dir()


def test_saving_from_the_window_writes_a_directory(tmp_path, monkeypatch, window):
    """The whole point: the interface has to produce the new format, not the old one."""
    from PySide6.QtWidgets import QFileDialog

    target = tmp_path / "fresh.pastro"
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(target), "")))
    window.save_project_as()

    assert target.is_dir(), "Save As must write a directory"
    assert (target / "project.json").is_file()
    assert (target / "results").is_dir()
