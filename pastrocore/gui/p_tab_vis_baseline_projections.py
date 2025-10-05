# pastrocore/gui/p_tab_vis_baseline_projections.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidgetItem, QApplication
from PySide6.QtCore import Slot, Qt
from .ui_tab_vis_uv_coverage import Ui_UVCoverageVisTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from pastrocore.base.data_structure import CalculatedDataStructure
from pastrocore.base.frequencies import IF
from common.utils.logging_setup import logger
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from typing import List, Optional
from astropy.time import Time
import matplotlib.pyplot as plt
import polars as pl
import gc

class BaselineProjectionsVisualizationTab(QWidget):
    """Widget for baseline projections visualization with source, scan, baseline, and frequency selection."""

    def __init__(self, manipulator: ScheduleManipulator, observation: Observation, parent=None):
        """Initialize the baseline projections visualization tab.

        Args:
            manipulator: ScheduleManipulator instance for processing requests.
            observation: Observation object to visualize.
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
        logger.debug(f"BaselineProjectionsVisualizationTab initialized for observation id={id(observation)}")

        self.layout = QVBoxLayout(self.ui.widget)
        self._populate_filters()
        logger.debug("BaselineProjectionsVisualizationTab UI populated and ready for visualization")

        self.ui.comboBox.currentIndexChanged.connect(self.filter_changed)
        self.ui.listScans.itemChanged.connect(self.filter_changed)
        self.ui.listBaselines.itemChanged.connect(self.filter_changed)
        self.ui.listFrequencies.itemChanged.connect(self.filter_changed)
        self.ui.comboBox_2.currentIndexChanged.connect(self.filter_changed)

        if self.ui.comboBox.count() > 0:
            self.update_scans_for_source(self.ui.comboBox.currentText())
            self.update_visualization()

    def _get_frequencies(self) -> List[float]:
        """Retrieve available frequencies from observation in MHz.

        Returns:
            List of frequency values in MHz.
        """
        try:
            frequencies = self.manipulator.inspect(obj=self.observation, get_frequencies=None)
            if frequencies:
                freqs = frequencies.get_frequencies()
                logger.debug(f"Retrieved frequencies: {freqs}")
            return freqs or []
        except Exception as e:
            logger.error(f"Failed to retrieve frequencies: {str(e)}")
            return []

    def _populate_filters(self):
        """Populate source, baseline, and frequency filters from baseline projections DataFrame and observation."""
        try:
            df = self.manipulator.inspect(obj=self.observation, get_calculated_data_by_key="baseline_projections").get("data", {})
            if not isinstance(df, pl.DataFrame):
                logger.error("No valid baseline projections data available for populating filters")
                self.ui.comboBox.addItem("No baseline projections data available")
                return

            expected_columns = CalculatedDataStructure.get_columns("baseline_projections")
            if not expected_columns:
                logger.error("No schema defined for baseline projections data")
                self.ui.comboBox.addItem("No schema defined")
                return
            missing_columns = [col for col in expected_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"DataFrame for baseline projections missing required columns: {missing_columns}")
                self.ui.comboBox.addItem("Invalid baseline projections data structure")
                return

            sources = df["source_name"].unique().to_list()
            baselines = df["baseline"].unique().to_list()

            self.ui.comboBox.addItems(sorted(sources))
            for baseline in sorted(baselines):
                item = QListWidgetItem(baseline)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(Qt.Checked)
                self.ui.listBaselines.addItem(item)
            for freq in sorted(self.frequencies):
                try:
                    item = QListWidgetItem(f"{float(freq):.2f} MHz")
                    item.setData(Qt.UserRole, float(freq))
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    item.setCheckState(Qt.Checked)
                    self.ui.listFrequencies.addItem(item)
                except (TypeError, ValueError) as e:
                    logger.error(f"Failed to format frequency {freq}: {str(e)}")
                    continue
            self.ui.comboBox_2.addItems(["Wavelengths", "Earth Diameters"])
            logger.debug(f"Populated {len(sources)} sources, {len(baselines)} baselines, {len(self.frequencies)} frequencies")
        except Exception as e:
            logger.error(f"Failed to populate filters: {str(e)}")
            self.ui.comboBox.addItem("Failed to retrieve filters")

    def _lock_ui(self):
        """Lock UI elements during visualization processing."""
        self.ui.comboBox.setEnabled(False)
        self.ui.listScans.setEnabled(False)
        self.ui.listBaselines.setEnabled(False)
        self.ui.listFrequencies.setEnabled(False)
        self.ui.comboBox_2.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        logger.debug("UI locked for visualization processing")

    def _unlock_ui(self):
        """Unlock UI elements after visualization processing."""
        self.ui.comboBox.setEnabled(True)
        self.ui.listScans.setEnabled(True)
        self.ui.listBaselines.setEnabled(True)
        self.ui.listFrequencies.setEnabled(True)
        self.ui.comboBox_2.setEnabled(True)
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
            logger.error(f"Failed to embed figure: {str(e)}")
            self._clear_canvas()

    def get_selected_source(self) -> Optional[str]:
        """Get the currently selected source name.

        Returns:
            Selected source name or None if no source is selected.
        """
        source_name = self.ui.comboBox.currentText()
        if not source_name or source_name in ["No baseline projections data available", "No schema defined", "Invalid baseline projections data structure", "Failed to retrieve filters"]:
            logger.debug("No valid source selected")
            return None
        logger.debug(f"Selected source: {source_name}")
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
        logger.debug(f"Selected scans: {selected_scans}")
        return selected_scans

    def get_selected_baselines(self) -> List[str]:
        """Get the list of selected baseline names.

        Returns:
            List of selected baseline names.
        """
        selected_baselines = []
        for i in range(self.ui.listBaselines.count()):
            item = self.ui.listBaselines.item(i)
            if item.checkState() == Qt.Checked:
                selected_baselines.append(item.text())
        logger.debug(f"Selected baselines: {selected_baselines}")
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
                freq = item.data(Qt.UserRole)
                if isinstance(freq, (int, float)):
                    selected_frequencies.append(float(freq))
        logger.debug(f"Selected frequencies: {selected_frequencies}")
        return selected_frequencies

    def get_selected_units(self) -> str:
        """Get the selected units for visualization.

        Returns:
            Selected units ('lambda' or 'meters').
        """
        units = self.ui.comboBox_2.currentText()
        logger.debug(f"Selected units: {units}")
        return units

    @Slot()
    def filter_changed(self):
        """Handle changes in filter selections by updating visualization."""
        if self.is_processing:
            logger.debug("Filter change ignored, visualization is processing")
            return
        self.is_processing = True
        self._lock_ui()
        try:
            self.update_scans_for_source(self.ui.comboBox.currentText())
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
            df = self.manipulator.inspect(obj=self.observation, get_calculated_data_by_key="baseline_projections").get("data", {})
            if not isinstance(df, pl.DataFrame):
                logger.error("No valid baseline projections data available for updating scans")
                self.ui.listScans.addItem(QListWidgetItem("No baseline projections data available"))
                return

            expected_columns = CalculatedDataStructure.get_columns("baseline_projections")
            if not expected_columns:
                logger.error("No schema defined for baseline projections data")
                self.ui.listScans.addItem(QListWidgetItem("No schema defined"))
                return
            missing_columns = [col for col in expected_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"DataFrame for baseline projections missing required columns: {missing_columns}")
                self.ui.listScans.addItem(QListWidgetItem("Invalid baseline projections data structure"))
                return

            df_filtered = df.filter(pl.col("source_name") == source_name)
            if df_filtered.is_empty():
                logger.debug(f"No data for source '{source_name}' in baseline projections DataFrame")
                self.ui.listScans.addItem(QListWidgetItem("No scans available"))
                return

            scan_times = df_filtered.group_by("scan_name").agg(time=pl.col("time").first()).sort("time")
            scans = scan_times["scan_name"].to_list()

            for row in scan_times.iter_rows(named=True):
                scan_name = row["scan_name"]
                start_time = Time(row["time"], format="mjd").isot
                display_text = f"{start_time}"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, scan_name)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(current_checks.get(scan_name, Qt.Checked))
                self.ui.listScans.addItem(item)
            logger.debug(f"Populated {len(scans)} scans for source '{source_name}'")
        except Exception as e:
            logger.error(f"Failed to update scans for source '{source_name}': {str(e)}")
            self.ui.listScans.addItem(QListWidgetItem("Failed to retrieve scans"))

    def update_visualization(self):
        """Update the baseline projections visualization based on current filter selections."""
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
            "plot_type": "baseline_projections",
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
            logger.debug(f"Visualization result: {result}")
            if not result or (result.get("baselines", 0) == 0 and result.get("frequencies", 0) == 0):
                logger.debug("Empty visualization result, clearing canvas")
                self._clear_canvas()
                return
            figure = result.get("figure")
            if figure:
                self.embed_figure(figure)
                logger.debug(f"Baseline projections visualization updated for source '{source_name}', frequencies {frequencies}")
            else:
                logger.error("No figure returned from visualizer, clearing canvas")
                self._clear_canvas()
        except Exception as e:
            logger.error(f"Exception during baseline projections visualization update: {str(e)}")
            self._clear_canvas()

    def closeEvent(self, event):
        """Ensure resources are cleaned up when the widget is closed."""
        self._clear_canvas()
        super().closeEvent(event)
        logger.debug("BaselineProjectionsVisualizationTab closed, resources cleaned up")