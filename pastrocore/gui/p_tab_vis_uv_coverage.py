# pastrocore/gui/p_tab_vis_uv_coverage.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidgetItem, QApplication
from PySide6.QtCore import Slot, Qt
from .ui_tab_vis_uv_coverage import Ui_UVCoverageVisTab
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

class UVVisualizationTab(QWidget):
    """Widget for UV coverage visualization with source, scan, baseline, and frequency selection."""

    def __init__(self, manipulator: ScheduleManipulator, observation: Observation, parent=None):
        """Initialize the UV visualization tab.

        Args:
            manipulator: ScheduleManipulator instance for processing visualization requests.
            observation: Observation object containing UV coverage data.
            parent: Parent widget, typically a QDialog.
        """
        super().__init__(parent)
        self.ui = Ui_UVCoverageVisTab()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self.observation = observation
        self.canvas = None
        self.toolbar = None
        self.figure = None
        self.is_processing = False
        self.frequencies = self._get_frequencies()
        logger.debug("UVVisualizationTab initialized for observation id=%s", id(observation))

        self.layout = QVBoxLayout(self.ui.widget)
        self._populate_filters()
        logger.debug("UVVisualizationTab UI populated and ready for visualization")

        self.ui.comboBox.currentIndexChanged.connect(self.filter_changed)
        self.ui.listScans.itemChanged.connect(self.filter_changed)
        self.ui.listBaselines.itemChanged.connect(self.filter_changed)
        self.ui.listFrequencies.itemChanged.connect(self.filter_changed)
        self.ui.comboBox_2.currentIndexChanged.connect(self.filter_changed)

        if self.ui.comboBox.count() > 0:
            self.update_scans_for_source(self.ui.comboBox.currentText())
            self.update_visualization()

    def _populate_filters(self):
        """Populate source, baseline, and frequency filters from UV coverage DataFrame and observation."""
        try:
            # One request instead of a filter, a group-by and a time conversion repeated
            # in every visualization tab. The query lives in ScheduleData, where a script
            # can ask it too.
            response = self.manipulator.export(
                obj=self.observation, method="scan_times",
                key="uv_coverage", source_name=source_name)
            scans_found = (response["result"] if isinstance(response, dict) and "status" in response
                           else response) or []
            if not scans_found:
                logger.debug("No scans for source '%s' in uv_coverage", source_name)
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
        """Update the UV coverage visualization based on current filter selections."""
        source_name = self.get_selected_source()
        frequencies = self.get_selected_frequencies()
        units = self.get_selected_units()
        scans = self.get_selected_scans()
        baselines = self.get_selected_baselines()
        logger.debug("Updating visualization: source='%s', frequencies=%s, units=%s, scans=%s, baselines=%s", source_name, frequencies, units, scans, baselines)

        if not source_name or not scans or not baselines or not frequencies:
            logger.debug("Missing required filters (source, scans, baselines, or frequencies), clearing canvas")
            self._clear_canvas()
            return

        vis_attributes = {
            "plot_type": "uv_coverage",
            "show": False,
            "return_figure": True,
            "source_name": source_name,
            "scans": scans,
            "baselines": baselines,
            "frequencies": frequencies,
            "units": units
        }

        try:
            result = self.manipulator.visualize(obj=self.observation, **vis_attributes)
            logger.debug("Visualization result: %s", result)
            if not result or (result.get("baselines", 0) == 0 and result.get("frequencies", 0) == 0):
                logger.debug("Empty visualization result, clearing canvas")
                self._clear_canvas()
                return
            figure = result.get("figure")
            if figure:
                self.embed_figure(figure)
                logger.debug("UV coverage visualization updated for source '%s', frequencies %s", source_name, frequencies)
            else:
                logger.error("No figure returned from visualizer, clearing canvas")
                self._clear_canvas()
        except Exception as e:
            logger.error("Exception during UV coverage visualization update: %s", str(e))
            self._clear_canvas()

    def closeEvent(self, event):
        """Ensure resources are cleaned up when the widget is closed."""
        self._clear_canvas()
        super().closeEvent(event)
        logger.debug("UVVisualizationTab closed, resources cleaned up")