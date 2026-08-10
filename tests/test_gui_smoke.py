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
    """The application's entry point, constructed without being shown."""
    import pastrocore

    window_class = next(
        (getattr(pastrocore, name) for name in dir(pastrocore)
         if name.endswith("Window") or name.endswith("MainWindow")),
        None,
    )
    if window_class is None:
        pytest.skip("no main window class exported from pastrocore")

    window = window_class()
    try:
        assert window is not None
    finally:
        window.close()
        window.deleteLater()
