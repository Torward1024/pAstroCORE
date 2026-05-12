# pastrocore/gui/p_tab_vis_parallactic.py
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
from astropy.time import Time
import matplotlib.pyplot as plt
import polars as pl
import gc

class ParallacticAngleVisualizationTab(QWidget):
    """Widget for Parallactic Angle visualization with source, scan, and telescope selection."""

    def __init__(self, manipulator: ScheduleManipulator, observation: Observation, parent=None):
        """Initialize the Parallactic Angle visualization tab.

        Args:
            manipulator: ScheduleManipulator instance for processing visualization requests.
            observation: Observation object containing parallactic angle data.
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

        logger.debug(f"ParallacticAngleVisualizationTab initialized for observation id={id(observation)}")

        self.layout = QVBoxLayout(self.ui.widget)
        self._populate_filters()
        logger.debug("ParallacticAngleVisualizationTab UI populated and ready for visualization")

        self.ui.cmbSource.currentIndexChanged.connect(self.filter_changed)
        self.ui.listScans.itemChanged.connect(self.filter_changed)
        self.ui.listTelescopes.itemChanged.connect(self.filter_changed)

        if self.ui.cmbSource.count() > 0:
            self.update_scans_for_source(self.ui.cmbSource.currentText())
            self.update_visualization()

    def _populate_filters(self):
        """Populate source and telescope filters from Parallactic Angle DataFrame."""
        try:
            df = self.manipulator.inspect(
                obj=self.observation, 
                get_calculated_data_by_key="parallactic_angle"
            ).get("data", {})

            if not isinstance(df, pl.DataFrame):
                logger.error("No valid parallactic angle data available for populating filters")
                self.ui.cmbSource.addItem("No parallactic angle data available")
                return

            expected_columns = CalculatedDataStructure.get_columns("parallactic_angle")
            if not expected_columns:
                logger.error("No schema defined for parallactic_angle data")
                self.ui.cmbSource.addItem("No schema defined")
                return

            missing_columns = [col for col in expected_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"DataFrame for parallactic_angle missing required columns: {missing_columns}")
                self.ui.cmbSource.addItem("Invalid parallactic angle data structure")
                return

            sources = df["source_name"].unique().to_list()
            telescopes = df["telescope_code"].unique().to_list()

            self.ui.cmbSource.addItems(sorted(sources))
            for telescope in sorted(telescopes):
                item = QListWidgetItem(telescope)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(Qt.Checked)
                self.ui.listTelescopes.addItem(item)

            logger.debug(f"Populated {len(sources)} sources and {len(telescopes)} telescopes for parallactic angle")
        except Exception as e:
            logger.error(f"Failed to populate filters: {str(e)}")
            self.ui.cmbSource.addItem("Failed to retrieve data")

    def _lock_ui(self):
        """Lock UI elements to prevent further changes during visualization."""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.ui.cmbSource.setEnabled(False)
        self.ui.listScans.setEnabled(False)
        self.ui.listTelescopes.setEnabled(False)
        logger.debug("UI locked in ParallacticAngleVisualizationTab")

    def _unlock_ui(self):
        """Unlock UI elements after visualization is complete."""
        QApplication.restoreOverrideCursor()
        self.ui.cmbSource.setEnabled(True)
        self.ui.listScans.setEnabled(True)
        self.ui.listTelescopes.setEnabled(True)
        logger.debug("UI unlocked in ParallacticAngleVisualizationTab")

    def _clear_canvas(self):
        """Safely clear the canvas, toolbar, and figure to release resources."""
        logger.debug("Clearing canvas, toolbar, and figure")
        if self.canvas:
            try:
                self.layout.removeWidget(self.canvas)
                self.canvas.setParent(None)
                self.canvas.deleteLater()
            except Exception as e:
                logger.warning(f"Failed to remove canvas: {str(e)}")
            finally:
                self.canvas = None

        if self.toolbar:
            try:
                self.layout.removeWidget(self.toolbar)
                self.toolbar.setParent(None)
                self.toolbar.deleteLater()
            except Exception as e:
                logger.warning(f"Failed to remove toolbar: {str(e)}")
            finally:
                self.toolbar = None

        if self.figure:
            try:
                for ax in self.figure.axes:
                    ax.clear()
                    ax.remove()
                self.figure.clf()
                plt.close(self.figure)
            except Exception as e:
                logger.warning(f"Failed to close figure: {str(e)}")
            finally:
                self.figure = None

        gc.collect(2)

    def embed_figure(self, figure: Figure):
        """Embed a Matplotlib figure into the widget."""
        self._clear_canvas()
        self.figure = figure
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        self.canvas.draw()
        logger.debug(f"Embedded Matplotlib figure {id(figure)} in ParallacticAngleVisualizationTab")

    def get_selected_source(self) -> Optional[str]:
        """Get the currently selected source name."""
        source = self.ui.cmbSource.currentText() if self.ui.cmbSource.currentText() else None
        return source

    def get_selected_scans(self) -> List[str]:
        """Get the list of selected scan names."""
        selected_scans = []
        for i in range(self.ui.listScans.count()):
            item = self.ui.listScans.item(i)
            if item.checkState() == Qt.Checked:
                selected_scans.append(item.data(Qt.UserRole))
        return selected_scans

    def get_selected_telescopes(self) -> List[str]:
        """Get the list of selected telescope codes."""
        selected_telescopes = []
        for i in range(self.ui.listTelescopes.count()):
            item = self.ui.listTelescopes.item(i)
            if item.checkState() == Qt.Checked:
                selected_telescopes.append(item.text())
        return selected_telescopes

    @Slot()
    def filter_changed(self):
        """Handle changes in filter selections by updating scans and visualization."""
        if self.is_processing:
            return
        self.is_processing = True
        self._lock_ui()
        try:
            source_name = self.get_selected_source()
            self.update_scans_for_source(source_name)
            self.update_visualization()
        finally:
            self.is_processing = False
            self._unlock_ui()

    def update_scans_for_source(self, source_name: Optional[str] = None):
        """Update the scans list based on the selected source."""
        current_checks = {
            self.ui.listScans.item(i).data(Qt.UserRole): self.ui.listScans.item(i).checkState()
            for i in range(self.ui.listScans.count())
        }

        self.ui.listScans.clear()
        if not source_name:
            return

        try:
            df = self.manipulator.inspect(
                obj=self.observation, 
                get_calculated_data_by_key="parallactic_angle"
            ).get("data", {})

            if not isinstance(df, pl.DataFrame):
                self.ui.listScans.addItem(QListWidgetItem("No parallactic angle data available"))
                return

            df_filtered = df.filter(pl.col("source_name") == source_name)
            if df_filtered.is_empty():
                self.ui.listScans.addItem(QListWidgetItem("No scans available"))
                return

            scan_times = df_filtered.group_by("scan_name").agg(
                time=pl.col("time").first()
            ).sort("time")

            for row in scan_times.iter_rows(named=True):
                scan_name = row["scan_name"]
                start_time = Time(row["time"], format="mjd").isot
                display_text = f"{start_time}"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, scan_name)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(current_checks.get(scan_name, Qt.Checked))
                self.ui.listScans.addItem(item)

        except Exception as e:
            logger.error(f"Failed to update scans for source '{source_name}': {str(e)}")
            self.ui.listScans.addItem(QListWidgetItem("Failed to retrieve scans"))

    def update_visualization(self):
        """Update the Parallactic Angle visualization based on current filter selections."""
        source_name = self.get_selected_source()
        scans = self.get_selected_scans()
        telescopes = self.get_selected_telescopes()

        if not source_name or not scans or not telescopes:
            self._clear_canvas()
            return

        vis_attributes = {
            "plot_type": "parallactic_angle",
            "show": False,
            "return_figure": True,
            "source_name": source_name,
            "scans": scans,
            "telescopes": telescopes
        }

        try:
            result = self.manipulator.visualize(obj=self.observation, **vis_attributes)
            if not result or (result.get("telescopes", 0) == 0):
                self._clear_canvas()
                return

            figure = result.get("figure")
            if figure:
                self.embed_figure(figure)
            else:
                self._clear_canvas()
        except Exception as e:
            logger.error(f"Exception during parallactic angle visualization update: {str(e)}")
            self._clear_canvas()

    def closeEvent(self, event):
        """Ensure resources are cleaned up when the widget is closed."""
        self._clear_canvas()
        super().closeEvent(event)
        logger.debug("ParallacticAngleVisualizationTab closed, resources cleaned up")