# pastrocore/gui/p_tab_vis_sun_angles.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidgetItem, QApplication
from PySide6.QtCore import Slot, Qt
from .ui_tab_vis_default import Ui_VisDefaultTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from pastrocore.base.data_structure import CalculatedDataStructure
from msb_arch.utils.logging_setup import logger
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from typing import List, Optional
import matplotlib.pyplot as plt
import gc

class SunAnglesVisualizationTab(QWidget):
    """Widget for Sun angles visualization with source, scan, and telescope selection."""

    def __init__(self, manipulator: ScheduleManipulator, observation: Observation, parent=None):
        """Initialize the Sun angles visualization tab.

        Args:
            manipulator: ScheduleManipulator instance for processing visualization requests.
            observation: Observation object containing Sun angles data.
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
        logger.debug("SunAnglesVisualizationTab initialized for observation id=%s", id(observation))

        self.layout = QVBoxLayout(self.ui.widget)
        self._populate_filters()
        logger.debug("SunAnglesVisualizationTab UI populated and ready for visualization")

        self.ui.cmbSource.currentIndexChanged.connect(self.filter_changed)
        self.ui.listScans.itemChanged.connect(self.filter_changed)
        self.ui.listTelescopes.itemChanged.connect(self.filter_changed)

        if self.ui.cmbSource.count() > 0:
            self.update_scans_for_source(self.ui.cmbSource.currentText())
            self.update_visualization()

    def _populate_filters(self):
        """Populate source and telescope filters from Sun angles DataFrame."""
        try:
            # One request instead of a filter, a group-by and a time conversion repeated
            # in every visualization tab. The query lives in ScheduleData, where a script
            # can ask it too.
            response = self.manipulator.export(
                obj=self.observation, method="scan_times",
                key="sun_angles", source_name=source_name)
            scans_found = (response["result"] if isinstance(response, dict) and "status" in response
                           else response) or []
            if not scans_found:
                logger.debug("No scans for source '%s' in sun_angles", source_name)
                self.ui.listScans.addItem(QListWidgetItem("No scans available"))
                return

            scans = [entry["scan_name"] for entry in scans_found]
            for entry in scans_found:
                scan_name = entry["scan_name"]
                start_time = entry["start"]
                display_text = f"{start_time}"
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
        """Update the Sun angles visualization based on current filter selections."""
        source_name = self.get_selected_source()
        scans = self.get_selected_scans()
        telescopes = self.get_selected_telescopes()
        logger.debug("Updating visualization: source='%s', scans=%s, telescopes=%s", source_name, scans, telescopes)

        if not source_name or not scans or not telescopes:
            logger.debug("Missing required filters (source, scans, or telescopes), clearing canvas")
            self._clear_canvas()
            return

        vis_attributes = {
            "plot_type": "sun_angles",
            "show": False,
            "return_figure": True,
            "source_name": source_name,
            "scans": scans,
            "telescopes": telescopes
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
                logger.debug("Sun angles visualization updated for source '%s'", source_name)
            else:
                logger.error("No figure returned from visualizer, clearing canvas")
                self._clear_canvas()
        except Exception as e:
            logger.error("Exception during Sun angles visualization update: %s", str(e))
            self._clear_canvas()

    def closeEvent(self, event):
        """Ensure resources are cleaned up when the widget is closed."""
        self._clear_canvas()
        super().closeEvent(event)
        logger.debug("SunAnglesVisualizationTab closed, resources cleaned up")