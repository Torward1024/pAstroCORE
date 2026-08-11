# pastrocore/gui/p_tab_vis_uv_coverage.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidgetItem, QApplication
from PySide6.QtCore import Slot, Qt
from .ui_tab_vis_uv_coverage import Ui_UVCoverageVisTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
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
            # One request instead of reading the frame, checking it against the schema and
            # calling unique() twice. The same question fills a combo box in every tab.
            response = self.manipulator.export(
                obj=self.observation, method="distinct",
                key="uv_coverage", columns=["source_name", "baseline"])
            values = (response["result"] if isinstance(response, dict) and "status" in response
                      else response) or {}
            sources = values.get("source_name", [])
            baselines = values.get("baseline", [])
            if not sources:
                logger.error("No valid UV coverage data available for populating filters")
                self.ui.comboBox.addItem("No UV coverage data available")
                return

            self.ui.comboBox.addItems(sources)
            for baseline in baselines:
                item = QListWidgetItem(baseline)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(Qt.Checked)
                self.ui.listBaselines.addItem(item)

            for freq in sorted(self.frequencies):
                item = QListWidgetItem(f"{freq:.2f} MHz")
                item.setData(Qt.UserRole, freq)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(Qt.Checked)
                self.ui.listFrequencies.addItem(item)

            self.ui.comboBox_2.addItems(["Wavelengths", "Earth Diameters"])
            logger.debug("Populated %s sources, %s baselines, and %s frequencies", len(sources), len(baselines), len(self.frequencies))
        except Exception as e:
            logger.error("Failed to populate filters: %s", str(e))
            self.ui.comboBox.addItem("Failed to retrieve data")

    def _get_frequencies(self) -> List[float]:
        """Retrieve the list of frequencies (in MHz) from the observation."""
        try:
            frequencies = self.manipulator.inspect(obj=self.observation, get_frequencies=None)
            freq_list = [float(f.get("frequency")) for f in frequencies.get_items()]
            logger.debug("Retrieved frequencies: %s", freq_list)
            return freq_list
        except Exception as e:
            logger.error("Failed to retrieve frequencies: %s", str(e))
            return []

    def _lock_ui(self):
        """Lock UI elements to prevent further changes during visualization."""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.ui.comboBox.setEnabled(False)
        self.ui.listScans.setEnabled(False)
        self.ui.listBaselines.setEnabled(False)
        self.ui.listFrequencies.setEnabled(False)
        self.ui.comboBox_2.setEnabled(False)
        logger.debug("UI locked in UVVisualizationTab")

    def _unlock_ui(self):
        """Unlock UI elements after visualization is complete."""
        QApplication.restoreOverrideCursor()
        self.ui.comboBox.setEnabled(True)
        self.ui.listScans.setEnabled(True)
        self.ui.listBaselines.setEnabled(True)
        self.ui.listFrequencies.setEnabled(True)
        self.ui.comboBox_2.setEnabled(True)
        logger.debug("UI unlocked in UVVisualizationTab")

    def _clear_canvas(self):
        """Safely clear the canvas, toolbar, and figure to release resources."""
        logger.debug("Clearing canvas, toolbar, and figure")
        if self.canvas:
            try:
                self.layout.removeWidget(self.canvas)
                self.canvas.setParent(None)
                self.canvas.deleteLater()
                logger.debug("Canvas removed and scheduled for deletion")
            except Exception as e:
                logger.warning("Failed to remove canvas: %s", str(e))
            finally:
                self.canvas = None

        if self.toolbar:
            try:
                self.layout.removeWidget(self.toolbar)
                self.toolbar.setParent(None)
                self.toolbar.deleteLater()
                logger.debug("Toolbar removed and scheduled for deletion")
            except Exception as e:
                logger.warning("Failed to remove toolbar: %s", str(e))
            finally:
                self.toolbar = None

        if self.figure:
            try:
                for ax in self.figure.axes:
                    ax.clear()
                    ax.remove()
                self.figure.clf()
                plt.close(self.figure)
                logger.debug("Figure %s closed and cleared", id(self.figure))
            except Exception as e:
                logger.warning("Failed to close figure %s: %s", id(self.figure), str(e))
            finally:
                self.figure = None

        gc.collect(2)
        logger.debug("Number of open figures after cleanup: %s", len(plt.get_fignums()))

    def embed_figure(self, figure: Figure):
        """Embed a Matplotlib figure into the widget.

        Args:
            figure: Matplotlib Figure object to embed.
        """
        self._clear_canvas()
        self.figure = figure
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        self.canvas.draw()
        logger.debug("Embedded Matplotlib figure %s in UVVisualizationTab", id(figure))

    def get_selected_source(self) -> Optional[str]:
        """Get the currently selected source name.

        Returns:
            Selected source name or None if no source is selected.
        """
        source = self.ui.comboBox.currentText() if self.ui.comboBox.currentText() else None
        logger.debug("Selected source: %s", source)
        return source

    def get_selected_scans(self) -> List[str]:
        """Get the list of selected scan names.

        Returns:
            List of selected scan names.
        """
        selected_scans = []
        for i in range(self.ui.listScans.count()):
            item = self.ui.listScans.item(i)
            if item.checkState() == Qt.Checked:
                selected_scans.append(item.data(Qt.UserRole))
        logger.debug("Selected scans: %s", selected_scans)
        return selected_scans

    def get_selected_baselines(self) -> List[str]:
        """Get the list of selected baseline pairs.

        Returns:
            List of selected baseline pairs.
        """
        selected_baselines = []
        for i in range(self.ui.listBaselines.count()):
            item = self.ui.listBaselines.item(i)
            if item.checkState() == Qt.Checked:
                selected_baselines.append(item.text())
        logger.debug("Selected baselines: %s", selected_baselines)
        return selected_baselines

    def get_selected_frequencies(self) -> List[float]:
        """Get the list of selected frequency values.

        Returns:
            List of selected frequency values in MHz.
        """
        selected_frequencies = []
        for i in range(self.ui.listFrequencies.count()):
            item = self.ui.listFrequencies.item(i)
            if item.checkState() == Qt.Checked:
                selected_frequencies.append(float(item.data(Qt.UserRole)))
        logger.debug("Selected frequencies: %s", selected_frequencies)
        return selected_frequencies

    def get_selected_units(self) -> str:
        """Get the selected units for visualization.

        Returns:
            Selected units ("Wavelengths" or "Earth Diameters") or None if not selected.
        """
        units = self.ui.comboBox_2.currentText().lower() if self.ui.comboBox_2.currentText() else None
        logger.debug("Selected units: %s", units)
        return units

    @Slot()
    def filter_changed(self):
        """Handle changes in filter selections by updating scans and visualization."""
        if self.is_processing:
            logger.debug("Filter change ignored, visualization is processing")
            return
        self.is_processing = True
        self._lock_ui()
        try:
            source_name = self.get_selected_source()
            logger.debug("Filter changed, updating scans for source '%s'", source_name)
            self.update_scans_for_source(source_name)
            self.update_visualization()
        finally:
            self.is_processing = False
            self._unlock_ui()

    def update_scans_for_source(self, source_name: Optional[str] = None):
        """Update the scans list based on the selected source, preserving check states.

        Args:
            source_name: Name of the selected source, or None to clear the scans list.
        """
        current_checks = {self.ui.listScans.item(i).data(Qt.UserRole): self.ui.listScans.item(i).checkState()
                          for i in range(self.ui.listScans.count())}
        logger.debug("Stored check states: %s", current_checks)

        self.ui.listScans.clear()
        if not source_name:
            logger.debug("No source selected, clearing scans list")
            return

        try:
            # One request instead of a read, a schema check, a filter, a group-by and a time
            # conversion. The same question is asked by every visualization tab, so it lives
            # in ScheduleData where a script can ask it too.
            response = self.manipulator.export(
                obj=self.observation, method="scan_times",
                key="uv_coverage", source_name=source_name)
            scan_times = (response["result"] if isinstance(response, dict) and "status" in response
                          else response) or []
            if not scan_times:
                logger.debug("No scans for source '%s' in UV coverage", source_name)
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