# pastrocore/gui/p_tab_vis_uv_coverage.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidgetItem
from PySide6.QtCore import Slot, Qt
from .ui_tab_vis_uv_coverage import Ui_UVCoverageVisTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from typing import List, Optional
from astropy.time import Time
import astropy.units as u
import matplotlib.pyplot as plt
import gc

class UVVisualizationTab(QWidget):
    """Widget for UV coverage visualization with source, scan, baseline, and frequency selection."""

    def __init__(self, manipulator: ScheduleManipulator, observation: Observation,
                 sources: List[str], scans: List[str], baselines: List[str], parent=None):
        """Initialize the UV visualization tab.

        Args:
            manipulator: ScheduleManipulator instance for processing visualization requests.
            observation: Observation object containing UV coverage data.
            sources: List of available source names.
            scans: List of available scan names.
            baselines: List of available baseline pairs.
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
        self.cached_data = None
        self.frequencies = self._get_frequencies()
        logger.debug(f"UVVisualizationTab initialized for observation id={id(observation)}")

        # Populate UI elements
        self.ui.comboBox.addItems(sources)
        for baseline in baselines:
            item = QListWidgetItem(baseline)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            self.ui.listBaselines.addItem(item)

        # Populate frequencies
        for freq in self.frequencies:
            item = QListWidgetItem(f"{freq:.2f} MHz")
            item.setData(Qt.UserRole, freq)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            self.ui.listFrequencies.addItem(item)

        # Populate units combo box
        self.ui.comboBox_2.addItems(["Wavelengths", "Earth Diameters"])

        # Initialize Matplotlib canvas
        self.layout = QVBoxLayout(self.ui.widget)
        logger.debug("UVVisualizationTab UI populated and ready for visualization")

        # Connect signals for filter changes
        self.ui.comboBox.currentIndexChanged.connect(self.on_filter_changed)
        self.ui.listScans.itemChanged.connect(self.on_filter_changed)
        self.ui.listBaselines.itemChanged.connect(self.on_filter_changed)
        self.ui.listFrequencies.itemChanged.connect(self.on_filter_changed)
        self.ui.comboBox_2.currentIndexChanged.connect(self.on_filter_changed)

        # Cache data immediately
        self._cache_calculated_data()
        if sources:
            self.update_scans_for_source(sources[0])
            self.update_visualization()  # Trigger initial visualization

    def _get_frequencies(self) -> List[float]:
        """Retrieve the list of frequencies (in MHz) from the observation.

        Returns:
            List of frequencies in MHz.
        """
        response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_frequencies": None}
        })
        if response["status"]:
            frequencies = response["result"].get_items()
            freq_list = [float(f.get("frequency")) for f in frequencies]
            logger.debug(f"Retrieved frequencies: {freq_list}")
            return freq_list
        logger.error(f"Failed to retrieve frequencies: {response.get('error', 'Unknown error')}")
        return []

    def _cache_calculated_data(self):
        """Cache calculated data for the observation to optimize performance."""
        calc_data_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_calculated_data": {"keys": ["uv_coverage", "times"]}}
        })
        if calc_data_response["status"]:
            self.cached_data = calc_data_response["result"]
            logger.debug(f"Cached calculated data: {list(self.cached_data.keys())}")
        else:
            logger.error(f"Failed to cache calculated data: {calc_data_response.get('error', 'Unknown error')}")
            self.cached_data = {}

    def get_selected_source(self) -> Optional[str]:
        """Get the currently selected source name.

        Returns:
            Selected source name or None if no source is selected.
        """
        source = self.ui.comboBox.currentText() if self.ui.comboBox.currentText() else None
        logger.debug(f"Selected source: {source}")
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
        logger.debug(f"Selected scans: {selected_scans}")
        return selected_scans

    def get_selected_baselines(self) -> List[str]:
        """Get the list of selected baseline names.

        Returns:
            List of selected baseline pairs.
        """
        selected_baselines = []
        for i in range(self.ui.listBaselines.count()):
            item = self.ui.listBaselines.item(i)
            if item.checkState() == Qt.Checked:
                selected_baselines.append(item.text())
        logger.debug(f"Selected baselines: {selected_baselines}")
        return selected_baselines

    def get_selected_frequencies(self) -> List[float]:
        """Get the list of selected frequencies (in MHz).

        Returns:
            List of selected frequencies in MHz. Falls back to all frequencies if none selected.
        """
        selected_frequencies = []
        for i in range(self.ui.listFrequencies.count()):
            item = self.ui.listFrequencies.item(i)
            if item.checkState() == Qt.Checked:
                freq = float(item.data(Qt.UserRole))
                selected_frequencies.append(freq)
        if not selected_frequencies:
            selected_frequencies = self.frequencies
            logger.debug(f"No frequencies selected, falling back to all frequencies: {selected_frequencies}")
        return selected_frequencies

    def get_selected_units(self) -> str:
        """Get the selected units for UV coverage visualization.

        Returns:
            Selected units ('wavelengths' or 'earth_diameters').
        """
        units = self.ui.comboBox_2.currentText().lower().replace(" ", "_")
        logger.debug(f"Selected units: {units}")
        return units

    def _clear_canvas(self):
        """Aggressively clear the canvas, toolbar, and figure to release all resources."""
        logger.debug("Clearing canvas, toolbar, and figure")

        # Remove and delete canvas
        if self.canvas:
            try:
                self.layout.removeWidget(self.canvas)
                self.canvas.setParent(None)
                self.canvas.deleteLater()
                logger.debug("Canvas removed and scheduled for deletion")
            except Exception as e:
                logger.warning(f"Failed to remove canvas: {str(e)}")
            finally:
                self.canvas = None

        # Remove and delete toolbar
        if self.toolbar:
            try:
                self.layout.removeWidget(self.toolbar)
                self.toolbar.setParent(None)
                self.toolbar.deleteLater()
                logger.debug("Toolbar removed and scheduled for deletion")
            except Exception as e:
                logger.warning(f"Failed to remove toolbar: {str(e)}")
            finally:
                self.toolbar = None

        # Clear and close figure
        if self.figure:
            try:
                for ax in self.figure.axes:
                    ax.clear()
                    ax.remove()
                self.figure.clf()
                plt.close(self.figure)
                logger.debug(f"Figure {id(self.figure)} closed and cleared")
            except Exception as e:
                logger.warning(f"Failed to close figure {id(self.figure)}: {str(e)}")
            finally:
                self.figure = None

        # Force garbage collection and log open figures
        gc.collect(2)
        logger.debug(f"Number of open figures after cleanup: {len(plt.get_fignums())}")

    @Slot()
    def embed_figure(self, figure: Figure):
        """Embed a Matplotlib figure into the widget.

        Args:
            figure: Matplotlib Figure object to embed.
        """
        self._clear_canvas()  # Clear existing resources first
        self.figure = figure
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        self.canvas.draw()
        logger.debug(f"Embedded Matplotlib figure {id(figure)} in UVVisualizationTab")

    @Slot()
    def on_filter_changed(self):
        """Handle changes in filter selections by updating scans and visualization."""
        source_name = self.get_selected_source()
        logger.debug(f"Filter changed, updating scans for source '{source_name}'")
        self.update_scans_for_source(source_name)
        self.update_visualization()

    def update_scans_for_source(self, source_name: str):
        """Update the scans list based on the selected source, preserving check states.

        Args:
            source_name: Name of the selected source.
        """
        current_checks = {self.ui.listScans.item(i).data(Qt.UserRole): self.ui.listScans.item(i).checkState()
                          for i in range(self.ui.listScans.count())}
        logger.debug(f"Stored check states: {current_checks}")

        self.ui.listScans.clear()
        if not source_name:
            logger.debug("No source selected, clearing scans list")
            return

        if not self.cached_data or "uv_coverage" not in self.cached_data:
            logger.error("No cached UV coverage data available for updating scans")
            return

        scans = []
        if source_name in self.cached_data["uv_coverage"]["data"]:
            scan_data = self.cached_data["uv_coverage"]["data"][source_name]
            scans_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation,
                "attributes": {"get_scans": None}
            })
            if not scans_response["status"]:
                logger.error(f"Failed to retrieve scans: {scans_response.get('error', 'Unknown error')}")
                return

            scan_objects = scans_response["result"].get_items()
            for scan in scan_objects:
                scan_name = scan.get("name")
                if scan_name in scan_data:
                    start_time = Time(scan.get_start()).isot
                    duration = scan.get_duration() * u.s
                    end_time = (Time(scan.get_start()) + duration).isot
                    display_text = f"{start_time} - {end_time}"
                    item = QListWidgetItem(display_text)
                    item.setData(Qt.UserRole, scan_name)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    item.setCheckState(current_checks.get(scan_name, Qt.Checked))
                    self.ui.listScans.addItem(item)
                    scans.append(scan_name)
            logger.debug(f"Populated {len(scans)} scans for source '{source_name}'")
        else:
            logger.debug(f"No UV coverage data for source '{source_name}'")

    def update_visualization(self):
        """Update the UV coverage visualization based on current filter selections."""
        source_name = self.get_selected_source()
        frequencies = self.get_selected_frequencies()
        units = self.get_selected_units()
        scans = self.get_selected_scans()
        baselines = self.get_selected_baselines()
        logger.debug(f"Updating visualization: source='{source_name}', frequencies={frequencies}, "
                     f"units={units}, scans={scans}, baselines={baselines}")

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
            response = self.manipulator.process_request({
                "operation": "visualize",
                "obj": self.observation,
                "attributes": vis_attributes
            })
            logger.debug(f"Visualization response: {response}")
            if response["status"]:
                result = response.get("result", {})
                if not result or (result.get("baselines", 0) == 0 and result.get("frequencies", 0) == 0):
                    logger.debug("Empty visualization result, clearing canvas")
                    self._clear_canvas()
                    return
                figure = result.get("figure")
                if figure:
                    self.embed_figure(figure)
                    logger.debug(f"UV coverage visualization updated for source '{source_name}', frequencies {frequencies}")
                else:
                    logger.error("No figure returned from visualizer, clearing canvas")
                    self._clear_canvas()
            else:
                logger.error(f"Failed to update visualization: {response.get('message', 'Unknown error')}")
                self._clear_canvas()
        except Exception as e:
            logger.error(f"Exception during UV coverage visualization update: {str(e)}")
            self._clear_canvas()

    def closeEvent(self, event):
        """Ensure resources are cleaned up when the widget is closed."""
        self._clear_canvas()
        super().closeEvent(event)
        logger.debug(f"UVVisualizationTab closed, resources cleaned up")