"""Take the manual's screenshots from the running application.

Usage:
    python tools/make_screenshots.py            write every screenshot
    python tools/make_screenshots.py --list     name them without writing any

Notes:
    - A screenshot in a manual goes stale the moment a form is edited, and nothing says so.
      These are made from the application against the fixture project, so regenerating them
      is one command and `test_documentation` fails on a page naming one that is not made.
    - Offscreen, with its own per-user directory, so a run reads and writes nothing of the
      reader's -- the same isolation the suite gives every test.
"""
import argparse
import copy
import json
import os
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMAGES = ROOT / "docs" / "images"
FIXTURE = ROOT / "tests" / "fixtures" / "test_project.pastro"

#: What the window is grabbed at. Wide enough that a table shows its columns, and the same
#: every run, so a regenerated screenshot differs only where the application does.
WINDOW = (1280, 820)


def isolate(home, headless):
    """Put the application's files under `home`, and Qt offscreen if asked.

    Notes:
        - **The platform decides whether there is a font**, and a screenshot of tofu boxes is
          worse than none. The offscreen plugin registers no system font here, so the default
          is the desktop's own platform -- `grab()` needs no window shown either way.
        - `--headless` is for a machine with no display, where the boxes are the price.
    """
    if headless:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    for name in ("LOCALAPPDATA", "XDG_DATA_HOME", "HOME"):
        os.environ[name] = str(home)


def opened_project(into):
    """Write the fixture project into `into` as a directory, and return its path.

    Notes:
        - Named at construction rather than renamed: a name is given once and the model
          refuses to change it, and "Untitled Project" across every screenshot reads as a
          manual written against nothing.
    """
    sys.path.insert(0, str(ROOT))
    from pastrocore.super.schedule_project import ScheduleProject

    saved = copy.deepcopy(json.loads(FIXTURE.read_text(encoding="utf-8")))
    saved["name"] = "Survey"
    directory = into / "survey.pastro"
    ScheduleProject.from_dict(saved).to_directory(str(directory))
    return directory


def hide_the_path(window):
    """Empty the status bar, which otherwise carries where this run put its project.

    Notes:
        - The bar says the last thing the log said, and opening a project logs the directory
          it came from -- a temporary one here, under the name of whoever ran this. A manual
          showing it would be publishing a path off the machine that built it.
    """
    bar = getattr(window, "status", None)
    message = getattr(bar, "message", None)
    if message is not None:
        message.setText("")


def grab(widget, name):
    """Write one widget to `docs/images/<name>.png`."""
    IMAGES.mkdir(parents=True, exist_ok=True)
    image = widget.grab().toImage()
    path = IMAGES / f"{name}.png"
    assert image.save(str(path)), f"could not write {path}"
    return path


def outermost(widget):
    """Return the tab widget nothing else holds, or None.

    Notes:
        - Found rather than named: an attribute renamed in the window or in a generated form
          would otherwise leave this quietly taking no screenshots at all, which is how the
          first version of it found one screen of a dozen.
    """
    from PySide6.QtWidgets import QTabWidget

    found = widget.findChildren(QTabWidget)
    outer = [t for t in found if not any(o is not t and o.isAncestorOf(t) for o in found)]
    return outer[0] if outer else None


def pages(tabs):
    """Yield `(label, page)` for each tab, showing it first so what it draws is drawn."""
    for index in range(tabs.count()):
        tabs.setCurrentIndex(index)
        label = tabs.tabText(index).split(":")[-1].strip().lower().replace(" ", "-")
        yield label, tabs.widget(index)


def open_everything(window):
    """Open the tabs a reader opens, so the manual shows them with a project in them.

    Notes:
        - An observation tab is opened by double-clicking the explorer and the analysis tab
          from the Tools menu; neither is there when a project is merely opened.
    """
    for observation in window.manipulator.inspect(window.project, get_items=None):
        window.open_observation_tab(observation.name, observation.get_observation_code())
    window.open_analysis_tab()


def shots(window, application):
    """Yield `(name, widget)` for every screen the manual shows.

    Notes:
        - The window first, while the project tab is the one showing, which is what a reader
          meets on opening a project. Walking the tabs afterwards leaves the last one current.
    """
    yield "window", window
    open_everything(window)
    application.processEvents()

    container = outermost(window)
    if container is None:
        return
    for label, page in pages(container):
        application.processEvents()
        yield f"tab-{label}", page
        inner = outermost(page)
        if inner is None:
            continue
        for name, sub in pages(inner):
            application.processEvents()
            yield f"tab-{label}-{name}", sub


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="name them without writing any")
    parser.add_argument("--headless", action="store_true",
                        help="render offscreen, on a machine with no display")
    asked = parser.parse_args()

    workspace = pathlib.Path(tempfile.mkdtemp(prefix="pastrocore-shots-"))
    try:
        isolate(workspace / "user", asked.headless)
        directory = opened_project(workspace)

        from PySide6.QtWidgets import QApplication

        from pastrocore.app import PAstroCoreMainWindow

        application = QApplication.instance() or QApplication([])
        window = PAstroCoreMainWindow()
        try:
            window.resize(*WINDOW)
            window._open_project_at(str(directory))
            application.processEvents()
            for name, widget in shots(window, application):
                hide_the_path(window)
                if asked.list:
                    print(name)
                    continue
                application.processEvents()
                print(grab(widget, name).relative_to(ROOT).as_posix())
        finally:
            window.close()
            window.deleteLater()
            application.processEvents()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    main()
