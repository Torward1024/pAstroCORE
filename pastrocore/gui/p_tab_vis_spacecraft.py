# pastrocore/gui/p_tab_vis_spacecraft.py
"""Tabs for the two results about tracking a spacecraft.

Both are filtered the same way -- which spacecraft, which scans, which stations -- so they share
one widget and differ only in the result they draw. What they do *not* have is a source: a
spacecraft is tracked, not observed, so the first filter is the target rather than the source.
"""
import gc
from typing import List, Optional

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from msb_arch.utils.logging_setup import logger
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QApplication, QListWidgetItem, QVBoxLayout, QWidget

from pastrocore.base.observation import Observation
from pastrocore.super.schedule_manipulator import ScheduleManipulator

from .ui_tab_vis_default import Ui_VisDefaultTab


class SpacecraftVisualizationTab(QWidget):
    """Draws one spacecraft result, filtered by target, scans and stations.

    Args:
        manipulator (ScheduleManipulator): The orchestrator every request goes through.
        observation (Observation): The observation holding the result.
        parent: The dialog owning the tab.

    Notes:
        - `STORE_KEY` says which result a subclass draws. Everything else is shared.
    """

    STORE_KEY = "telescope_az_el"

    def __init__(self, manipulator: ScheduleManipulator, observation: Observation, parent=None):
        super().__init__(parent)
        self.ui = Ui_VisDefaultTab()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self.observation = observation
        self.canvas = None
        self.toolbar = None
        self.figure = None
        self.is_processing = False

        self.layout = QVBoxLayout(self.ui.widget)
        self._populate_filters()

        self.ui.cmbSource.currentIndexChanged.connect(self.filter_changed)
        self.ui.listScans.itemChanged.connect(self.filter_changed)
        self.ui.listTelescopes.itemChanged.connect(self.filter_changed)

        if self.ui.cmbSource.count() > 0:
            self.update_scans_for_target(self.ui.cmbSource.currentText())
            self.update_visualization()

    def _populate_filters(self):
        """Fill the target and station lists from the result itself."""
        try:
            response = self.manipulator.export(
                obj=self.observation, method="distinct",
                key=self.STORE_KEY, columns=["target_code", "telescope_code"])
            values = (response["result"] if isinstance(response, dict) and "status" in response
                      else response) or {}
            targets = values.get("target_code", [])
            stations = values.get("telescope_code", [])

            if not targets:
                logger.debug("No '%s' data to populate filters from", self.STORE_KEY)
                self.ui.cmbSource.addItem("No data available")
                return

            self.ui.cmbSource.addItems(targets)
            for station in stations:
                item = QListWidgetItem(station)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(Qt.Checked)
                self.ui.listTelescopes.addItem(item)
            logger.debug("Populated %s target(s) and %s station(s) for '%s'",
                         len(targets), len(stations), self.STORE_KEY)
        except Exception as error:                       # noqa: BLE001 - shown to the user
            logger.error("Could not populate filters for '%s': %s", self.STORE_KEY, str(error))
            self.ui.cmbSource.addItem("Failed to retrieve data")

    def _lock_ui(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.ui.cmbSource.setEnabled(False)
        self.ui.listScans.setEnabled(False)
        self.ui.listTelescopes.setEnabled(False)

    def _unlock_ui(self):
        QApplication.restoreOverrideCursor()
        self.ui.cmbSource.setEnabled(True)
        self.ui.listScans.setEnabled(True)
        self.ui.listTelescopes.setEnabled(True)

    def _clear_canvas(self):
        """Release the canvas, toolbar and figure."""
        if self.canvas:
            try:
                self.layout.removeWidget(self.canvas)
                self.canvas.setParent(None)
                self.canvas.deleteLater()
            except Exception as error:                   # noqa: BLE001 - logged
                logger.warning("Could not remove the canvas: %s", str(error))
            finally:
                self.canvas = None

        if self.toolbar:
            try:
                self.layout.removeWidget(self.toolbar)
                self.toolbar.setParent(None)
                self.toolbar.deleteLater()
            except Exception as error:                   # noqa: BLE001 - logged
                logger.warning("Could not remove the toolbar: %s", str(error))
            finally:
                self.toolbar = None

        if self.figure:
            try:
                for axis in self.figure.axes:
                    axis.clear()
                    axis.remove()
                self.figure.clf()
                plt.close(self.figure)
            except Exception as error:                   # noqa: BLE001 - logged
                logger.warning("Could not close the figure: %s", str(error))
            finally:
                self.figure = None

        gc.collect(2)

    def embed_figure(self, figure: Figure):
        """Put a figure into the tab, replacing whatever was there."""
        self._clear_canvas()
        self.figure = figure
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        self.canvas.draw()

    def get_selected_target(self) -> Optional[str]:
        """The spacecraft currently chosen, or None."""
        return self.ui.cmbSource.currentText() or None

    def get_selected_scans(self) -> List[str]:
        """The scans currently ticked."""
        return [self.ui.listScans.item(index).data(Qt.UserRole)
                for index in range(self.ui.listScans.count())
                if self.ui.listScans.item(index).checkState() == Qt.Checked]

    def get_selected_telescopes(self) -> List[str]:
        """The stations currently ticked."""
        return [self.ui.listTelescopes.item(index).text()
                for index in range(self.ui.listTelescopes.count())
                if self.ui.listTelescopes.item(index).checkState() == Qt.Checked]

    @Slot()
    def filter_changed(self):
        """Redraw when a filter changes."""
        if self.is_processing:
            return
        self.is_processing = True
        self._lock_ui()
        try:
            self.update_scans_for_target(self.get_selected_target())
            self.update_visualization()
        finally:
            self.is_processing = False
            self._unlock_ui()

    def update_scans_for_target(self, target_code: Optional[str] = None):
        """Fill the scan list for one spacecraft, keeping what was ticked."""
        ticked = {self.ui.listScans.item(index).data(Qt.UserRole):
                  self.ui.listScans.item(index).checkState()
                  for index in range(self.ui.listScans.count())}
        self.ui.listScans.clear()
        if not target_code:
            return

        try:
            response = self.manipulator.export(
                obj=self.observation, method="scan_times",
                key=self.STORE_KEY, target_code=target_code)
            scan_times = (response["result"] if isinstance(response, dict) and "status" in response
                          else response) or []
            if not scan_times:
                self.ui.listScans.addItem(QListWidgetItem("No scans available"))
                return

            for entry in scan_times:
                item = QListWidgetItem(entry["start"])
                item.setData(Qt.UserRole, entry["scan_name"])
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(ticked.get(entry["scan_name"], Qt.Checked))
                self.ui.listScans.addItem(item)
        except Exception as error:                       # noqa: BLE001 - shown to the user
            logger.error("Could not list scans for '%s': %s", target_code, str(error))
            self.ui.listScans.addItem(QListWidgetItem("Failed to retrieve scans"))

    def update_visualization(self):
        """Draw the result with the current filters."""
        target_code = self.get_selected_target()
        scans = self.get_selected_scans()
        stations = self.get_selected_telescopes()

        if not target_code or not scans or not stations:
            self._clear_canvas()
            return

        try:
            result = self.manipulator.visualize(
                obj=self.observation, plot_type=self.STORE_KEY, show=False, return_figure=True,
                target_code=target_code, scans=scans, telescopes=stations)
            if not result or not result.get("telescopes"):
                self._clear_canvas()
                return
            figure = result.get("figure")
            if figure:
                self.embed_figure(figure)
            else:
                self._clear_canvas()
        except Exception as error:                       # noqa: BLE001 - shown to the user
            logger.error("Could not draw '%s': %s", self.STORE_KEY, str(error))
            self._clear_canvas()

    def closeEvent(self, event):
        self._clear_canvas()
        super().closeEvent(event)


class SpacecraftPointingVisualizationTab(SpacecraftVisualizationTab):
    """Where each station points to follow a spacecraft, and how far away it is."""

    STORE_KEY = "telescope_az_el"


class SpacecraftVisibilityVisualizationTab(SpacecraftVisualizationTab):
    """When each station can see the spacecraft."""

    STORE_KEY = "telescope_visibility"
