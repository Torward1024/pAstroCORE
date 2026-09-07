# gui/p_tab_vis_base.py
"""What every visualization tab does, written once (G6).

Nine tabs, about 2500 lines, each with the same nine methods: populate the filters, lock the
interface while drawing, clear the canvas, embed a figure, read the selection, redraw when it
changes, clean up on close. **No two of those methods were byte-identical**, which is why this
was a rewrite rather than a lift -- they were nine parallel variations, and the differences
that mattered were buried among the differences that did not.

What actually varies is four things, and each is now a declaration:

| | |
| --- | --- |
| `FORM` | which generated form the tab is laid out with |
| `STORE_KEY` | the result it reads, which is also the plot it asks for unless `PLOT_TYPE` says otherwise |
| `FILTERS` | which columns its filters are built from -- asked of the result, not listed |
| `DRAWN` | the field in the visualizer's answer that counts what was drawn |

A tab that needs more than that overrides `_extra_attributes`, which is where units,
frequencies and a pointing target go. Everything else is inherited, including the bugs being
fixed once rather than nine times.
"""
import gc
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QApplication, QListWidgetItem, QVBoxLayout, QWidget
from msb_arch.utils.logging_setup import logger

from pastrocore.base.observation import Observation
from pastrocore.super.schedule_manipulator import ScheduleManipulator


class VisualizationTab(QWidget):
    """A tab that draws one calculation and lets it be filtered.

    Args:
        manipulator (ScheduleManipulator): The orchestrator every request goes through.
        observation (Observation): What is being drawn.
        parent (QWidget): Usually the visualization dialog.
    """

    #: The generated form this tab is laid out with. Subclasses set it.
    FORM = None

    #: The result it reads. Also the plot it asks the visualizer for, unless `PLOT_TYPE` differs.
    STORE_KEY = ""
    PLOT_TYPE = ""

    #: The columns the filters are built from. `source_name` fills the combo; anything else
    #: fills a list of checkboxes. Which *values* each takes is asked of the result.
    FILTERS = ("source_name", "telescope_code")

    #: The field in the visualizer's answer that says how much was drawn. An answer of zero is
    #: an empty plot, and an empty plot is cleared rather than shown.
    DRAWN = "telescopes"

    def __init__(self, manipulator: ScheduleManipulator, observation: Observation, parent=None):
        super().__init__(parent)
        self.ui = self.FORM()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self.observation = observation
        self.canvas = None
        self.toolbar = None
        self.figure = None
        self.is_processing = False

        self.layout = QVBoxLayout(self.ui.widget)
        self._populate_filters()

        for widget, signal in self._filter_signals():
            signal.connect(self.filter_changed)

        logger.debug("%s ready for observation '%s'", type(self).__name__, observation.name)
        self._first_draw()

    # --- what a subclass may adjust ---------------------------------------------------------

    def plot_type(self) -> str:
        """The plot to ask for. The result's own key unless a subclass says otherwise."""
        return self.PLOT_TYPE or self.STORE_KEY

    def _extra_attributes(self) -> Dict[str, Any]:
        """Anything this plot needs beyond source, scans and telescopes.

        Notes:
            - Units, frequencies, baselines and a pointing target live here. Returning nothing
              is the common case, which is why it is the default.
        """
        return {}

    def _first_draw(self):
        """Draw once the filters are populated, if there is anything to draw."""
        if self._has(self.ui, "cmbSource") and self.ui.cmbSource.count() > 0:
            self.update_scans_for_source(self.ui.cmbSource.currentText())
        self.update_visualization()

    # --- filters ---------------------------------------------------------------------------

    @staticmethod
    def _has(ui, name: str) -> bool:
        """Whether the form carries a widget. The forms differ, and this is how they may."""
        return hasattr(ui, name)

    def _filter_signals(self):
        """Yield the signals that mean "redraw", for whichever widgets this form has."""
        if self._has(self.ui, "cmbSource"):
            yield self.ui.cmbSource, self.ui.cmbSource.currentIndexChanged
        for name in ("listScans", "listTelescopes", "listBaselines", "listFrequencies"):
            if self._has(self.ui, name):
                widget = getattr(self.ui, name)
                yield widget, widget.itemChanged
        if self._has(self.ui, "cmbUnits"):
            yield self.ui.cmbUnits, self.ui.cmbUnits.currentIndexChanged

    def _distinct(self, columns: List[str]) -> Dict[str, List[str]]:
        """Ask what values a result's columns take.

        Notes:
            - One request rather than reading the frame, checking it against the schema and
              calling `unique()` per column.
        """
        try:
            answer = self.manipulator.export(
                obj=self.observation, method="distinct",
                key=self.STORE_KEY, columns=list(columns))
            return answer or {}
        except Exception as e:                          # noqa: BLE001 - an empty tab, not a crash
            logger.error("Could not read the filters of '%s': %s", self.STORE_KEY, str(e),
                         exc_info=True)
            return {}

    def _populate_filters(self):
        """Fill every filter this form has from what the result actually contains."""
        values = self._distinct(self.FILTERS)

        if self._has(self.ui, "cmbSource"):
            sources = values.get("source_name") or values.get("target_code") or []
            if sources:
                self.ui.cmbSource.addItems(sources)
            else:
                self.ui.cmbSource.addItem(f"No {self.STORE_KEY} data available")

        for column, widget_name in (("telescope_code", "listTelescopes"),
                                    ("baseline", "listBaselines")):
            if not self._has(self.ui, widget_name):
                continue
            widget = getattr(self.ui, widget_name)
            for value in values.get(column, []):
                item = QListWidgetItem(value)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(Qt.Checked)
                widget.addItem(item)

        self._populate_extra_filters()

    def _populate_extra_filters(self):
        """Anything this form has that the common ones do not. Nothing, usually."""

    # --- reading the selection --------------------------------------------------------------

    def get_selected_source(self) -> Optional[str]:
        """The chosen source, or None when the form has no source at all."""
        if not self._has(self.ui, "cmbSource"):
            return None
        return self.ui.cmbSource.currentText() or None

    @staticmethod
    def _checked(widget, role=None) -> List[str]:
        """Every checked item of a list, by its data or its text."""
        chosen = []
        for index in range(widget.count()):
            item = widget.item(index)
            if item.checkState() == Qt.Checked:
                chosen.append(item.data(role) if role is not None else item.text())
        return chosen

    def get_selected_scans(self) -> List[str]:
        if not self._has(self.ui, "listScans"):
            return []
        return self._checked(self.ui.listScans, Qt.UserRole)

    def get_selected_telescopes(self) -> List[str]:
        if not self._has(self.ui, "listTelescopes"):
            return []
        return self._checked(self.ui.listTelescopes)

    def get_selected_baselines(self) -> List[str]:
        if not self._has(self.ui, "listBaselines"):
            return []
        return self._checked(self.ui.listBaselines)

    # --- redrawing --------------------------------------------------------------------------

    @Slot()
    def filter_changed(self):
        """A filter moved: update the scans it implies, and redraw.

        Notes:
            - Guarded, because populating the scans list emits `itemChanged` per item and each
              of those would otherwise redraw the whole plot.
        """
        if self.is_processing:
            return
        self.is_processing = True
        self._lock_ui()
        try:
            self.update_scans_for_source(self.get_selected_source())
            self.update_visualization()
        finally:
            self.is_processing = False
            self._unlock_ui()

    def update_scans_for_source(self, source_name: Optional[str] = None):
        """Refill the scans list for a source, keeping whatever was already ticked.

        Args:
            source_name (Optional[str]): The source, or None to empty the list.

        Notes:
            - A scan is shown by its start time and carries its name underneath, because two
              scans of one source are told apart by when they are, not by a UUID.
        """
        if not self._has(self.ui, "listScans"):
            return

        was_checked = {self.ui.listScans.item(index).data(Qt.UserRole):
                       self.ui.listScans.item(index).checkState()
                       for index in range(self.ui.listScans.count())}
        self.ui.listScans.clear()

        if not source_name and self._has(self.ui, "cmbSource"):
            return

        try:
            asked = {"obj": self.observation, "method": "scan_times", "key": self.STORE_KEY}
            if source_name:
                asked["source_name"] = source_name
            scan_times = self.manipulator.export(**asked) or []
        except Exception as e:                          # noqa: BLE001 - an empty list, not a crash
            logger.error("Could not read the scans of '%s': %s", self.STORE_KEY, str(e),
                         exc_info=True)
            self.ui.listScans.addItem(QListWidgetItem("Failed to retrieve scans"))
            return

        if not scan_times:
            self.ui.listScans.addItem(QListWidgetItem("No scans available"))
            return

        for entry in scan_times:
            item = QListWidgetItem(entry["start"])
            item.setData(Qt.UserRole, entry["scan_name"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(was_checked.get(entry["scan_name"], Qt.Checked))
            self.ui.listScans.addItem(item)

    def _attributes(self) -> Optional[Dict[str, Any]]:
        """What to ask the visualizer for, or None when the selection draws nothing."""
        source = self.get_selected_source()
        scans = self.get_selected_scans()
        telescopes = self.get_selected_telescopes()

        if self._has(self.ui, "cmbSource") and not source:
            return None
        if self._has(self.ui, "listScans") and not scans:
            return None
        if self._has(self.ui, "listTelescopes") and not telescopes:
            return None

        attributes: Dict[str, Any] = {"plot_type": self.plot_type(),
                                      "show": False, "return_figure": True}
        if source:
            attributes["source_name"] = source
        if scans:
            attributes["scans"] = scans
        if telescopes:
            attributes["telescopes"] = telescopes

        extra = self._extra_attributes()
        if extra is None:
            return None
        attributes.update(extra)
        return attributes

    def update_visualization(self):
        """Ask for the plot and put it on screen, or clear the canvas."""
        attributes = self._attributes()
        if attributes is None:
            self._clear_canvas()
            return

        try:
            result = self.manipulator.visualize(obj=self.observation, **attributes)
        except Exception as e:                          # noqa: BLE001 - a blank tab, not a crash
            logger.error("Could not draw '%s': %s", self.plot_type(), str(e), exc_info=True)
            self._clear_canvas()
            return

        if not result or (self.DRAWN and result.get(self.DRAWN, 0) == 0):
            logger.debug("Nothing to draw for '%s'", self.plot_type())
            self._clear_canvas()
            return

        figure = result.get("figure")
        if figure is None:
            logger.error("The visualizer returned no figure for '%s'", self.plot_type())
            self._clear_canvas()
            return
        self.embed_figure(figure)

    # --- the canvas ---------------------------------------------------------------------------

    def embed_figure(self, figure: Figure):
        """Put a figure on screen, replacing whatever was there."""
        self._clear_canvas()
        self.figure = figure
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        self.canvas.draw()

    def _clear_canvas(self):
        """Take the canvas, toolbar and figure down, releasing what they hold.

        Notes:
            - The figure is built by the visualizer with `Figure(...)` rather than
              `plt.figure(...)`, so pyplot never registered it and there is nothing to close --
              it goes when the last reference does. Clearing its axes first is what actually
              frees the arrays a plot of a day's sampling holds.
        """
        for name in ("canvas", "toolbar"):
            widget = getattr(self, name, None)
            if widget is None:
                continue
            try:
                self.layout.removeWidget(widget)
                widget.setParent(None)
                widget.deleteLater()
            except Exception as e:                      # noqa: BLE001 - teardown never raises
                logger.warning("Could not remove the %s: %s", name, str(e))
            finally:
                setattr(self, name, None)

        if self.figure is not None:
            try:
                for axes in list(self.figure.axes):
                    axes.clear()
                    axes.remove()
                self.figure.clf()
            except Exception as e:                      # noqa: BLE001 - teardown never raises
                logger.warning("Could not clear the figure: %s", str(e))
            finally:
                self.figure = None
        gc.collect(2)

    def _lock_ui(self):
        """Stop the filters being moved while a plot is being drawn."""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        for widget, _ in self._filter_signals():
            widget.setEnabled(False)

    def _unlock_ui(self):
        """Give the filters back."""
        QApplication.restoreOverrideCursor()
        for widget, _ in self._filter_signals():
            widget.setEnabled(True)

    def closeEvent(self, event):
        """Release the figure when the tab goes."""
        self._clear_canvas()
        super().closeEvent(event)
