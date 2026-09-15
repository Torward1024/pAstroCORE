"""Nothing on a form lies on anything else, and no text is cut off (G8).

The pixel harness says whether a form still looks as it did; it cannot say whether it looked right.
Twelve dialogs had a window whose minimum and maximum size were the same, and five of them were
smaller than their layout needed on any font, so Qt squeezed everything inside: fields 20 px high where the stylesheet's padding
needs 26, a Cancel button on its progress bar, the About text cut through the middle. The generator
gave its list buttons a minimum of 20 px, which replaces the height their text needs, and got
"Up" and "Down" with the tops of the letters missing.

Every generated form is laid out as it is authored and at the smallest its window allows, each page
of each tab in turn, with the application's stylesheet -- which is what decides how much room text
needs -- and the widgets the form names are measured:

- no two siblings intersect, and none extends past its parent;
- a label, button or checkbox is at least as large as its text asks for, and wrapped text
  has the height its lines need;
- a field is at least as tall as it asks for.

It is metrics rather than pixels, so it holds on any platform: a form whose window is sized by its
layout fits whatever font it gets, and one sized by hand is exactly what fails here.
"""
import importlib
import pathlib

import pytest

pytest.importorskip("PySide6")

GUI = pathlib.Path(__file__).parent.parent / "pastrocore" / "gui"

#: How far a measurement may be off before it counts: a pixel of rounding.
SLACK = 1

#: Qt's QWIDGETSIZE_MAX, which PySide6 does not export: a size with no maximum.
UNLIMITED = (1 << 24) - 1


def form_classes():
    """Every generated form, as (module stem, class name)."""
    found = []
    for path in sorted(GUI.glob("ui_*.py")):
        module = importlib.import_module(f"pastrocore.gui.{path.stem}")
        found.extend((path.stem, name) for name in sorted(dir(module)) if name.startswith("Ui_"))
    return found


def build(stem, class_name):
    """The form on whichever host widget it was written for."""
    from PySide6.QtWidgets import QDialog, QMainWindow, QWidget

    form = getattr(importlib.import_module(f"pastrocore.gui.{stem}"), class_name)
    for host_type in (QDialog, QWidget, QMainWindow):
        host, ui = host_type(), form()
        try:
            ui.setupUi(host)
        except Exception:
            host.deleteLater()
            continue
        return host, ui
    raise AssertionError(f"{stem}.{class_name} could not be built on any host widget")


def problems(host, ui):
    """Everything wrong with the form as it is laid out right now, in words."""
    from PySide6.QtWidgets import (QAbstractButton, QAbstractSpinBox, QComboBox, QLabel,
                                   QLineEdit, QWidget)

    named = {id(value): name for name, value in vars(ui).items() if isinstance(value, QWidget)}
    shown = [widget for name, widget in vars(ui).items()
             if isinstance(widget, QWidget) and widget is not host and widget.isVisibleTo(host)]
    found = []

    by_parent = {}
    for widget in shown:
        by_parent.setdefault(id(widget.parentWidget()), []).append(widget)
    for siblings in by_parent.values():
        for index, one in enumerate(siblings):
            for other in siblings[index + 1:]:
                common = one.geometry().intersected(other.geometry())
                if common.width() > SLACK and common.height() > SLACK:
                    found.append(f"{named[id(one)]} and {named[id(other)]} overlap by "
                                 f"{common.width()}x{common.height()}")

    for widget in shown:
        name = named[id(widget)]
        parent = widget.parentWidget()
        inside = parent.rect().adjusted(-SLACK, -SLACK, SLACK, SLACK)
        if not inside.contains(widget.geometry()):
            found.append(f"{name} extends past its parent")
        if isinstance(widget, QLabel) and widget.wordWrap() and widget.text():
            # A window does not grow taller for text that wraps, so the last lines are cut off.
            wants = widget.heightForWidth(widget.width())
            if widget.height() + SLACK < wants:
                found.append(f"{name} ('{widget.text()[:24]}') is {widget.height()} px high, "
                             f"its wrapped text needs {wants}")
        elif isinstance(widget, (QLabel, QAbstractButton)) and widget.text():
            wants = widget.sizeHint()
            if widget.width() + SLACK < wants.width() or widget.height() + SLACK < wants.height():
                found.append(f"{name} ('{widget.text()[:24]}') is {widget.width()}x{widget.height()}, "
                             f"its text needs {wants.width()}x{wants.height()}")
        elif isinstance(widget, (QLineEdit, QComboBox, QAbstractSpinBox)):
            wants = widget.minimumSizeHint()
            if widget.height() + SLACK < wants.height():
                found.append(f"{name} is {widget.height()} px high and needs {wants.height()}")
    return found


def layouts(application, host):
    """Lay the form out at its authored size and at its minimum, each tab page in turn."""
    from PySide6.QtWidgets import QStackedWidget, QTabWidget, QWidget

    authored = host.size()
    sizes = [("as authored", authored)]
    smallest = host.minimumSizeHint()
    if smallest.isValid():
        sizes.append(("at its smallest", smallest.expandedTo(host.minimumSize())))
    pages = [widget for widget in host.findChildren(QWidget)
             if isinstance(widget, (QTabWidget, QStackedWidget))]
    for label, size in sizes:
        host.resize(size)
        application.processEvents()
        yield f"{label} ({host.width()}x{host.height()})"
        for container in pages:
            for index in range(container.count()):
                container.setCurrentIndex(index)
                application.processEvents()
                yield f"{label} ({host.width()}x{host.height()}), {container.objectName()} page {index}"


@pytest.mark.parametrize("stem,class_name", form_classes())
def test_a_window_is_as_large_as_its_layout_says(qt_application, stem, class_name):
    """A window pinned to a size by hand fits the font it was drawn with and no other. Seven more
    fitted Arial on Windows and cut their labels in half with a wider font -- the one a Linux
    desktop has, or anyone's larger system font -- and the catalogue browser, pinned at 740x550,
    could not be made larger for a catalogue of hundreds. A window that must not be resized
    says so through its layout's size constraint, which follows the font."""
    host, _ = build(stem, class_name)
    try:
        maximum = host.maximumSize()
        assert (maximum.width(), maximum.height()) == (UNLIMITED, UNLIMITED) or (
            host.layout() is not None and host.layout().sizeConstraint().name == "SetFixedSize"), (
            f"{stem} pins its window to {maximum.width()}x{maximum.height()}")
    finally:
        host.deleteLater()


@pytest.mark.parametrize("stem,class_name", form_classes())
def test_nothing_on_a_form_overlaps_or_is_cut_off(qt_application, stem, class_name):
    from pastrocore.gui.styling import load_stylesheet

    if not qt_application.styleSheet():
        qt_application.setStyleSheet(load_stylesheet())
    host, ui = build(stem, class_name)
    host.show()
    qt_application.processEvents()
    try:
        found = {}
        for where in layouts(qt_application, host):
            for problem in problems(host, ui):
                found.setdefault(problem, where)
        assert not found, f"{stem}:\n" + "\n".join(f"  {problem} -- {where}"
                                                   for problem, where in found.items())
    finally:
        host.close()
        host.deleteLater()


def test_the_check_would_notice_a_squeezed_form(qt_application):
    """A check that cannot fail proves nothing: a dialog pinned smaller than its layout needs is
    exactly what it exists to catch."""
    from PySide6.QtWidgets import QDialog, QLineEdit, QPushButton, QVBoxLayout

    from pastrocore.gui.styling import load_stylesheet

    if not qt_application.styleSheet():
        qt_application.setStyleSheet(load_stylesheet())

    class Form:
        def setupUi(self, host):
            layout = QVBoxLayout(host)
            self.field = QLineEdit(host)
            self.button = QPushButton("A button with a long label", host)
            layout.addWidget(self.field)
            layout.addWidget(self.button)

    host, ui = QDialog(), Form()
    ui.setupUi(host)
    host.setFixedSize(60, 30)
    host.show()
    qt_application.processEvents()
    try:
        assert problems(host, ui), "a form pinned to 60x30 passed"
    finally:
        host.close()
        host.deleteLater()


def test_a_long_progress_message_neither_widens_the_window_nor_is_cut_off(qt_application):
    """The progress window grew as wide as the longest step's name; wrapped instead, the message lost
    its second line, since a window does not grow taller for wrapped text. Shortened in the middle,
    it keeps what the step is and how far along, and the window stays put."""
    from PySide6.QtWidgets import QApplication

    from pastrocore.gui.p_dialog_progress import ProgressDialog
    from pastrocore.gui.styling import load_stylesheet

    if not qt_application.styleSheet():
        qt_application.setStyleSheet(load_stylesheet())
    dialog = ProgressDialog(None, "Calculating", "Starting")
    dialog.show()
    QApplication.processEvents()
    width = dialog.width()
    message = "Calculating uv_coverage for observation " + "A_VERY_LONG_OBSERVATION_NAME_" * 4 + " (step 7 of 12)"
    try:
        dialog.update_progress(63, message)
        QApplication.processEvents()
        label = dialog.ui.label
        assert dialog.width() == width, "the window grew for a long message"
        assert problems(dialog, dialog.ui) == []
        assert label.fontMetrics().horizontalAdvance(label.text()) <= label.contentsRect().width()
        assert label.text().startswith("Calculating") and label.text().endswith("(step 7 of 12)")
        assert label.toolTip() == message, "the whole message is not anywhere to read"
    finally:
        dialog.finish()
        dialog.deleteLater()
