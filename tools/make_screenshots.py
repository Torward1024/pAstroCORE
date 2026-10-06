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
import os
import pathlib
import re
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMAGES = ROOT / "docs" / "images"

#: What the window is grabbed at. Wide enough that a table shows its columns, and the same
#: every run, so a regenerated screenshot differs only where the application does.
WINDOW = (1280, 820)

#: The example array, by the codes the shipped catalogue gives it, and what one of its
#: antennas delivers over the 6 cm band, as the VLBA's status summary quotes it.
ARRAY = ("BR", "FD", "HN", "KP", "LA", "MK", "NL", "OV", "PT", "SC")
SEFD = [(3900.0, 7900.0, 210.0)]

#: A spacecraft beside them, so the two plots about one have something to draw: Spektr-R's
#: ten metres, its SEFD over the same band, and its orbit rounded to three figures.
SPACECRAFT = "RA"
SPACECRAFT_SEFD = [(3900.0, 7900.0, 4500.0)]
ORBIT = {"a": 1.86e8, "e": 0.91, "i": 51.3, "raan": 180.0, "argp": 285.0, "nu": 0.0}

#: Three standard flux calibrators, under the names the catalogue files them by, with the
#: flux scale's values at the two frequencies this band sits between.
CALIBRATORS = {"1328+307": {1400.0: 14.9, 5000.0: 7.3},
               "0538+498": {1400.0: 22.4, 5000.0: 8.0},
               "1409+524": {1400.0: 22.2, 5000.0: 6.6}}

#: The band, the night, and the spacing between sampled moments.
BAND = {"frequency": 4990.0, "bandwidth": 128.0}
NIGHT = {"start": "2026-08-10T18:00:00", "end": "2026-08-11T08:00:00"}
STEP = 60.0


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


def catalogues():
    """Return the shipped catalogues, read the way the application reads them."""
    from pastrocore.paths import shipped_catalog
    from pastrocore.utils.catalogmanager import CatalogManager

    manager = CatalogManager()
    for kind in ("telescopes", "sources"):
        manager.load(kind, str(shipped_catalog(f"{kind}.json")))
    return manager


def array(manager):
    """Return the example array: the catalogue's stations, and a spacecraft beside them.

    Notes:
        - The catalogue carries geometry and no measurements, so the SEFD is given here. It
          is one published number for ten identical antennas, not a value per station.
    """
    from astropy.time import Time

    from pastrocore.base.spacetelescope import SpaceTelescope
    from pastrocore.base.telescopes import Telescopes

    telescopes = Telescopes()
    for code in ARRAY:
        dish = manager.get_telescope(code)
        dish.set({"sefd_table": SEFD})
        telescopes.add(dish)

    orbiting = SpaceTelescope(code=SPACECRAFT, name="Spektr-R", diameter=10.0,
                              sefd_table=SPACECRAFT_SEFD)
    orbiting.set_keplerian(epoch=Time(NIGHT["start"]), **ORBIT)
    telescopes.add(orbiting)
    return telescopes


def demo_project(into):
    """Build the schedule the manual is drawn from, write it into `into`, and return where.

    Notes:
        - Generated rather than carried as a file, so the example cannot drift from what the
          application makes of the same pattern, and the generator is exercised on every run.
        - A real array on real calibrators: nothing on a screenshot is a station or a source
          that does not exist, and the one number not in the catalogue is a published one.
    """
    sys.path.insert(0, str(ROOT))
    from pastrocore.base.frequencies import IF, Frequencies
    from pastrocore.base.sources import Sources
    from pastrocore.super.schedule_manipulator import ScheduleManipulator
    from pastrocore.super.schedule_project import ScheduleProject

    manager = catalogues()
    sources = Sources()
    for name, flux in CALIBRATORS.items():
        source = manager.get_source(name)
        source.set({"flux_table": flux})
        sources.add(source)

    frequencies = Frequencies()
    frequencies.add(IF(name="C", polarizations=["RCP", "LCP"], sidebands=["USB"], **BAND))

    project = ScheduleProject(name="Survey")
    ScheduleManipulator(project).configure(obj=project, generate_observations={
        "sources": sources, "telescopes": array(manager), "frequencies": frequencies,
        "observation_type": "VLBI", "time_range": NIGHT, "parallel": True,
        "scan_duration": 600.0, "num_scans": 8,
        "pattern": {"interval_sec": 2400, "naming_mask": "SV{i}"}})

    directory = into / "survey.pastro"
    project.to_directory(str(directory))
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


def hide_paths(widget, real):
    """Replace the directory this ran from, wherever a screen shows it.

    Notes:
        - A path reaches a screen three ways -- the status bar, a report, a field filled with
          where the project is -- and each was found by looking at a picture rather than by
          reasoning. This covers the class: whatever a widget says, it does not say the
          temporary directory this ran in, under the name of whoever ran it.
    """
    from PySide6.QtWidgets import QLabel, QLineEdit

    shown = "D:\\schedules" if os.name == "nt" else "/home/you/schedules"
    for kind in (QLineEdit, QLabel):
        for found in widget.findChildren(kind):
            said = found.text()
            if said and real in said:
                found.setText(said.replace(real, shown))


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
        - One observation, not every one: three observations of the same shape would be
          three sets of the same five screenshots.
    """
    from pastrocore.gui.p_tab_analysis import AnalysisTab

    observation = next(iter(window.manipulator.inspect(window.project, get_items=None)))
    window.open_observation_tab(observation.name, observation.get_observation_code())
    window.open_analysis_tab()
    # Asked as well as opened: the tab's own answer is what it is for, and an unasked one
    # is a form with an empty table under it.
    for tab in window.findChildren(AnalysisTab):
        tab.ask()


def dialog_classes():
    """Return every dialog the package defines, found rather than listed."""
    import importlib
    import inspect

    from PySide6.QtWidgets import QDialog

    found = {}
    for path in sorted((ROOT / "pastrocore" / "gui").glob("p_dialog_*.py")):
        module = importlib.import_module(f"pastrocore.gui.{path.stem}")
        for name, candidate in vars(module).items():
            if (inspect.isclass(candidate) and issubclass(candidate, QDialog)
                    and candidate.__module__ == module.__name__):
                found[name] = candidate
    # A base two others are built on is not a screen: the catalogue dialog cannot say which
    # catalogue it is, and a reader only ever meets one of its two subclasses.
    return {name: cls for name, cls in found.items()
            if not any(other is not cls and issubclass(other, cls) for other in found.values())}


def pool(window):
    """Return what a dialog's constructor may ask for, by the name it asks under.

    Notes:
        - A dialog is built from its own signature rather than from a table of calls, so one
          added to the package is a screenshot the next run makes. What it may ask for is
          named here; a parameter this does not hold is left to the dialog's own default.
    """
    observation = next(iter(window.manipulator.inspect(window.project, get_items=None)))
    scans = observation.get_scans().get_items()
    sources = observation.get_sources().get_items()
    frequencies = observation.get_frequencies().get_items()
    telescopes = observation.get_telescopes().get_items()

    return {
        "parent": window,
        "manipulator": window.manipulator,
        "project": window.project,
        "catalog_manager": window.catalog_manager,
        "settings": window.settings,
        "observation": observation,
        "scan": scans[0] if scans else None,
        "source_obj": sources[0] if sources else None,
        "if_obj": frequencies[0] if frequencies else None,
        "telescope": telescopes[0] if telescopes else None,
        "title": "Calculating",
        "message": "Source visibility, 3 of 11",
    }


def reports(window):
    """Return the two answers a dialog cannot be built without, from real requests.

    Notes:
        - A run report and a format report are what two of these dialogs are *for*. Writing
          plausible ones by hand would put numbers in the manual that nothing produced.
    """
    import tempfile

    held = {}
    manipulator = window.manipulator
    # What to run is asked of the catalogue, exactly as the command line asks it.
    catalogue = manipulator.inspect(window.project, method="catalogue")
    offered = sorted(entry["key"] for entry in catalogue if entry["offer"])
    ran = manipulator.compute(obj=None, method="run", calculations=offered,
                              targets=window.project.get_observations(),
                              time_step=STEP, target_telescope=SPACECRAFT,
                              raise_on_error=False)
    if getattr(ran, "ok", False):
        held["outcome"] = ran.value

    with tempfile.TemporaryDirectory() as into:
        written = manipulator.vex(window.project, method="export", path=into,
                                  raise_on_error=False)
    if getattr(written, "ok", False):
        held["report"] = as_an_example(written.value, into)
        held["label"] = "VEX"
    return held


def as_an_example(report, real):
    """Return the report with the directory it wrote to replaced by an example one.

    Notes:
        - A report carries where it wrote, and this wrote into a temporary directory named
          after whoever ran it. Which directory is not what the screenshot is about, and a
          manual is no place to publish one off the machine that built it.
    """
    shown = "D:\\schedules" if os.name == "nt" else "/home/you/schedules"
    swapped = dict(report)
    swapped["path"] = shown
    swapped["files"] = [{**entry,
                         "path": str(entry["path"]).replace(str(real), shown)}
                        for entry in report.get("files", []) if isinstance(entry, dict)]
    return swapped


def dialogs(window, held):
    """Yield `(name, dialog)` for every dialog in the package.

    Notes:
        - None is `exec`-ed: a modal dialog waits for a click nobody is here to give, which is
          how a build once hung for ten minutes.
        - One that cannot be built from the pool is reported rather than skipped in silence,
          so the manual does not quietly lose a screen.
    """
    import inspect

    available = pool(window)
    available.update(held)

    for name, dialog in sorted(dialog_classes().items()):
        asked = inspect.signature(dialog.__init__).parameters
        given = {key: available[key] for key in list(asked)[1:]
                 if key in available and available[key] is not None}
        # The two telescope editors ask under one name for two different kinds of station.
        if "Space" in name and "telescope" in given:
            from pastrocore.base.spacetelescope import SpaceTelescope
            given["telescope"] = SpaceTelescope()
        # Runs of capitals stay together, or `IFEditorDialog` reads as `i-f-editor`.
        cut = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "-", name)
        label = "dialog-" + cut.lower().replace("-dialog", "")
        try:
            yield label, dialog(**given)
        except Exception as why:  # noqa: BLE001 -- said out loud, never swallowed
            print(f"{label}: cannot be built -- {why}", file=sys.stderr)


def nothing_modal():
    """Turn the message boxes into printed lines, for a run with nobody to click them.

    Notes:
        - A dialog reports a failure by asking for an OK nobody is here to give. Printed
          instead, so a plot that cannot be drawn is said out loud rather than hanging.
    """
    from PySide6.QtWidgets import QMessageBox

    for level in ("critical", "warning", "information"):
        setattr(QMessageBox, level, staticmethod(
            lambda parent, title, text, *rest, said=level:
            print(f"{said}: {title} -- {text}", file=sys.stderr)))


def named(label):
    """Return a file name for a plot's label: `Space Telescope Pointing` is one word a part."""
    return "plot-" + re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


def plots(window):
    """Yield `(name, tab)` for every plot the dialog offers, opened as a reader opens one.

    Notes:
        - Driven through the dialog: which widget draws which result is its own answer, and
          what it offers is what the observation has results for.
        - The tabs stay open behind each other, which is what they do for a reader too.
    """
    from pastrocore.gui.p_dialog_visualize import VisualizationDialog

    dialog = VisualizationDialog(window.manipulator, parent=window)
    dialog.resize(*WINDOW)
    offered = dialog.ui.comboBoxVisualizationType
    for index in range(offered.count()):
        offered.setCurrentIndex(index)
        dialog.perform_visualization()
        drawn = dialog.ui.tabWidget.currentWidget()
        if drawn is None:
            print(f"{offered.itemText(index)}: no tab was opened", file=sys.stderr)
            continue
        yield named(offered.itemText(index)), drawn


def shots(window, application):
    """Yield `(name, widget)` for every screen the manual shows.

    Notes:
        - The window first, while the project tab is the one showing, which is what a reader
          meets on opening a project. Walking the tabs afterwards leaves the last one current.
        - Calculated before the tabs are opened, in the order a reader works in: the analysis
          tab reads what there is when it is built, and an empty one shows nothing.
    """
    yield "window", window
    held = reports(window)
    open_everything(window)
    application.processEvents()
    yield from dialogs(window, held)
    yield from plots(window)

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
        directory = demo_project(workspace)

        from PySide6.QtWidgets import QApplication

        from pastrocore.app import PAstroCoreMainWindow

        nothing_modal()
        application = QApplication.instance() or QApplication([])
        window = PAstroCoreMainWindow()
        try:
            window.resize(*WINDOW)
            window._open_project_at(str(directory))
            application.processEvents()
            for name, widget in shots(window, application):
                hide_the_path(window)
                hide_paths(widget, str(workspace))
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
