# pastrocore/gui/p_tab_vis_az_el.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidgetItem, QApplication
from PySide6.QtCore import Slot, Qt
from .ui_tab_vis_default import Ui_VisDefaultTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from msb_arch.utils.logging_setup import logger
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from typing import List, Optional
import matplotlib.pyplot as plt
import gc

class AzElVisualizationTab(QWidget):
    """Widget for Az/El or HA/Dec visualization with source, scan, and telescope selection."""

    def __init__(self, manipulator: ScheduleManipulator, observation: Observation, parent=None):
        """Initialize the Az/El or HA/Dec visualization tab.

        Args:
            manipulator: ScheduleManipulator instance for processing visualization requests.
            observation: Observation object containing Az/El or HA/Dec data.
            parent: Parent widget, typically a QDialog.
        """
        super().__init__(parent)
        self.ui = Ui_VisDefaultTab()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self.observation = observation
        self.canvas = None
        self.toolbar = None
        self.figure = None
        self.is_processing = False
        self.coord_type = "AzEl"
        logger.debug("AzElVisualizationTab initialized for observation id=%s", id(observation))

        self.layout = QVBoxLayout(self.ui.widget)
        self._populate_filters()
        logger.debug("AzElVisualizationTab UI populated and ready for visualization")

        self.ui.cmbSource.currentIndexChanged.connect(self.filter_changed)
        self.ui.listScans.itemChanged.connect(self.filter_changed)
        self.ui.listTelescopes.itemChanged.connect(self.filter_changed)

        if self.ui.cmbSource.count() > 0:
            self.update_scans_for_source(self.ui.cmbSource.currentText())
            self.update_visualization()

    def _populate_filters(self):
        """Populate source and telescope filters from Az/El DataFrame."""
        try:
            # One request instead of reading the frame, checking it against the schema and
            # calling unique() twice.
            response = self.manipulator.export(
                obj=self.observation, method="distinct",
                key="az_el", columns=["source_name", "telescope_code"])
            values = (response["result"] if isinstance(response, dict) and "status" in response
                      else response) or {}
            sources = values.get("source_name", [])
            telescopes = values.get("telescope_code", [])
            if not sources:
                logger.error("No valid Az/El data available for populating filters")
                self.ui.cmbSource.addItem("No Az/El data available")
                return

            self.ui.cmbSource.addItems(sources)
            for telescope in telescopes:
                item = QListWidgetItem(telescope)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(Qt.Checked)
                self.ui.listTelescopes.addItem(item)
            logger.debug("Populated %s sources and %s telescopes", len(sources), len(telescopes))
        except Exception as e:
            logger.error("Failed to populate filters: %s", str(e))
            self.ui.cmbSource.addItem("Failed to retrieve filters")

    def _lock_ui(self):
        """Lock UI elements during visualization processing."""
        self.ui.cmbSource.setEnabled(False)
        self.ui.listScans.setEnabled(False)
        self.ui.listTelescopes.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        logger.debug("UI locked for visualization processing")

    def _unlock_ui(self):
        """Unlock UI elements after visualization processing."""
        self.ui.cmbSource.setEnabled(True)
        self.ui.listScans.setEnabled(True)
        self.ui.listTelescopes.setEnabled(True)
        QApplication.restoreOverrideCursor()
        QApplication.processEvents()
        logger.debug("UI unlocked after visualization processing")

    def _clear_canvas(self):
        """Clear the current figure, canvas, and toolbar."""
        if self.canvas:
            self.layout.removeWidget(self.canvas)
            self.canvas.deleteLater()
            self.canvas = None
        if self.toolbar:
            self.layout.removeWidget(self.toolbar)
            self.toolbar.deleteLater()
            self.toolbar = None
        if self.figure:
            plt.close(self.figure)
            self.figure = None
        gc.collect()
        logger.debug("Canvas, toolbar, and figure cleared")

    def embed_figure(self, figure: Figure):
        """Embed a Matplotlib figure into the widget layout.

        Args:
            figure: Matplotlib figure to embed.
        """
        self._clear_canvas()
        try:
            self.figure = figure
            self.canvas = FigureCanvas(self.figure)
            self.toolbar = NavigationToolbar(self.canvas, self)
            self.layout.addWidget(self.toolbar)
            self.layout.addWidget(self.canvas)
            self.canvas.draw()
            logger.debug("Figure embedded successfully")
        except Exception as e:
            logger.error("Failed to embed figure: %s", str(e))
            self._clear_canvas()

    def get_selected_source(self) -> Optional[str]:
        """Get the currently selected source name.

        Returns:
            Selected source name or None if no source is selected.
        """
        source_name = self.ui.cmbSource.currentText()
        if not source_name or source_name in ["No Az/El data available", "No schema defined", "Invalid Az/El data structure", "Failed to retrieve filters"]:
            logger.debug("No valid source selected")
            return None
        logger.debug("Selected source: %s", source_name)
        return source_name

    def get_selected_scans(self) -> List[str]:
        """Get the list of selected scan names.

        Returns:
            List of selected scan names.
        """
        selected_scans = []
        for i in range(self.ui.listScans.count()):
            item = self.ui.listScans.item(i)
            if item.checkState() == Qt.Checked:
                scan_name = item.data(Qt.UserRole)
                if scan_name:
                    selected_scans.append(scan_name)
        logger.debug("Selected scans: %s", selected_scans)
        return selected_scans

    def get_selected_telescopes(self) -> List[str]:
        """Get the list of selected telescope codes.

        Returns:
            List of selected telescope codes.
        """
        selected_telescopes = []
        for i in range(self.ui.listTelescopes.count()):
            item = self.ui.listTelescopes.item(i)
            if item.checkState() == Qt.Checked:
                selected_telescopes.append(item.text())
        logger.debug("Selected telescopes: %s", selected_telescopes)
        return selected_telescopes

    @Slot()
    def filter_changed(self):
        """Handle changes in filter selections by updating visualization."""
        if self.is_processing:
            logger.debug("Filter change ignored, visualization is processing")
            return
        self.is_processing = True
        self._lock_ui()
        try:
            self.update_scans_for_source(self.ui.cmbSource.currentText())
            self.update_visualization()
        finally:
            self.is_processing = False
            self._unlock_ui()

    def update_scans_for_source(self, source_name: str):
        """Update the scans list based on the selected source.

        Args:
            source_name: Name of the selected source.
        """
        self.ui.listScans.clear()
        current_checks = {item.data(Qt.UserRole): item.checkState() for item in [self.ui.listScans.item(i) for i in range(self.ui.listScans.count())]}

        try:
            # One request instead of a read, a schema check, a filter, a group-by and a time
            # conversion.
            response = self.manipulator.export(
                obj=self.observation, method="scan_times",
                key="az_el", source_name=source_name)
            scan_times = (response["result"] if isinstance(response, dict) and "status" in response
                          else response) or []
            if not scan_times:
                logger.debug("No scans for source '%s' in Az/El", source_name)
                self.ui.listScans.addItem(QListWidgetItem("No scans available"))
                return

            scans = [entry["scan_name"] for entry in scan_times]

            for entry in scan_times:
                scan_name = entry["scan_name"]
                display_text = entry["start"]
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, scan_name)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(current_checks.get(scan_name, Qt.Checked))
                self.ui.listScans.addItem(item)
            logger.debug("Populated %s scans for source '%s'", len(scans), source_name)
        except Exception as e:
            logger.error("Failed to update scans for source '%s': %s", source_name, str(e))
            self.ui.listScans.addItem(QListWidgetItem("Failed to retrieve scans"))

    def update_visualization(self):
        """Update the Az/El or HA/Dec visualization based on current filter selections."""
        source_name = self.get_selected_source()
        scans = self.get_selected_scans()
        telescopes = self.get_selected_telescopes()
        logger.debug("Updating visualization: source='%s', scans=%s, telescopes=%s", source_name, scans, telescopes)

        if not source_name or not scans or not telescopes:
            logger.debug("Missing required filters (source, scans, or telescopes), clearing canvas")
            self._clear_canvas()
            return

        vis_attributes = {
            "plot_type": "az_el",
            "show": False,
            "return_figure": True,
            "source_name": source_name,
            "scans": scans,
            "telescopes": telescopes,
            "coord_type": self.coord_type,
            "line_styles": {"primary": "-", "secondary": "--"}
        }

        try:
            result = self.manipulator.visualize(obj=self.observation, **vis_attributes)
            logger.debug("Visualization result: %s", result)
            if not result or (result.get("telescopes", 0) == 0):
                logger.debug("Empty visualization result, clearing canvas")
                self._clear_canvas()
                return
            figure = result.get("figure")
            if figure:
                self.embed_figure(figure)
                logger.debug("Az/El visualization updated for source '%s'", source_name)
            else:
                logger.error("No figure returned from visualizer, clearing canvas")
                self._clear_canvas()
        except Exception as e:
            logger.error("Exception during Az/El visualization update: %s", str(e))
            self._clear_canvas()

    def closeEvent(self, event):
        """Ensure resources are cleaned up when the widget is closed."""
        self._clear_canvas()
        super().closeEvent(event)
        logger.debug("AzElVisualizationTab closed, resources cleaned up")