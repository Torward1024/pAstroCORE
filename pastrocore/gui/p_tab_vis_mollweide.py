# pastrocore/gui/p_tab_vis_mollweide.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidgetItem, QApplication
from PySide6.QtCore import Slot, Qt
from .ui_tab_vis_mollweide import Ui_MollweideVisTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from pastrocore.base.data_structure import CalculatedDataStructure
from common.utils.logging_setup import logger
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from typing import List, Optional
import matplotlib.pyplot as plt
import polars as pl
import gc

class MollweideVisualizationTab(QWidget):
    """Widget for Mollweide tracks visualization with source, scan, and telescope selection."""

    def __init__(self, manipulator: ScheduleManipulator, observation: Observation, parent=None):
        """Initialize the Mollweide tracks visualization tab.

        Args:
            manipulator: ScheduleManipulator instance for handling visualization requests.
            observation: Observation object containing the Mollweide tracks data.
            parent: Parent widget, typically a QDialog.
        """
        super().__init__(parent)
        self.ui = Ui_MollweideVisTab()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self.observation = observation
        self.canvas = None
        self.toolbar = None
        self.figure = None
        self.is_processing = False
        logger.debug(f"MollweideVisualizationTab initialized for observation id={id(observation)}")

        self.ui.listWidget.setObjectName("listSources")
        self.layout = QVBoxLayout(self.ui.widget)
        self._populate_filters()
        logger.debug("MollweideVisualizationTab UI populated and ready for visualization")

        self.ui.listWidget.itemChanged.connect(self.filter_changed)
        self.ui.listScans.itemChanged.connect(self.filter_changed)
        self.ui.listTelescopes.itemChanged.connect(self.filter_changed)

        if self.ui.listWidget.count() > 0:
            self.update_scans()
            self.update_visualization()

    def _populate_filters(self):
        """Populate source and telescope filters from Mollweide tracks DataFrame and its metadata."""
        try:
            df = self.manipulator.inspect(obj=self.observation, get_calculated_data_by_key="mollweide_tracks")
            if not isinstance(df, pl.DataFrame):
                logger.error("No valid Mollweide tracks data available for populating filters")
                self.ui.listWidget.addItem(QListWidgetItem("No Mollweide tracks data available"))
                return

            expected_columns = CalculatedDataStructure.get_columns("mollweide_tracks")
            if not expected_columns:
                logger.error("No schema defined for Mollweide tracks data")
                self.ui.listWidget.addItem(QListWidgetItem("No schema defined"))
                return
            missing_columns = [col for col in expected_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"DataFrame for Mollweide tracks missing required columns: {missing_columns}")
                self.ui.listWidget.addItem(QListWidgetItem("Invalid Mollweide tracks data structure"))
                return

            sources_metadata = self.observation._calculated_data_metadata.get("mollweide_tracks", {}).get("sources", {})
            if not sources_metadata:
                logger.error("No valid 'sources' metadata in Mollweide tracks")
                self.ui.listWidget.addItem(QListWidgetItem("No sources metadata available"))
                return

            sources = list(sources_metadata.keys())
            telescopes = df["telescope_code"].unique().to_list()

            for source in sorted(sources):
                item = QListWidgetItem(source)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(Qt.Checked)
                self.ui.listWidget.addItem(item)

            for telescope in sorted(telescopes):
                item = QListWidgetItem(telescope)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(Qt.Checked)
                self.ui.listTelescopes.addItem(item)
            logger.debug(f"Populated {len(sources)} sources and {len(telescopes)} telescopes")
        except Exception as e:
            logger.error(f"Failed to populate filters: {str(e)}")
            self.ui.listWidget.addItem(QListWidgetItem("Failed to retrieve data"))

    def _lock_ui(self):
        """Lock UI elements to prevent further changes during visualization."""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.ui.listWidget.setEnabled(False)
        self.ui.listScans.setEnabled(False)
        self.ui.listTelescopes.setEnabled(False)
        logger.debug("UI locked in MollweideVisualizationTab")

    def _unlock_ui(self):
        """Unlock UI elements after visualization is complete."""
        QApplication.restoreOverrideCursor()
        self.ui.listWidget.setEnabled(True)
        self.ui.listScans.setEnabled(True)
        self.ui.listTelescopes.setEnabled(True)
        logger.debug("UI unlocked in MollweideVisualizationTab")

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
                logger.warning(f"Failed to remove canvas: {str(e)}")
            finally:
                self.canvas = None

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

        gc.collect(2)
        logger.debug(f"Number of open figures after cleanup: {len(plt.get_fignums())}")

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
        logger.debug(f"Embedded Matplotlib figure {id(figure)} in MollweideVisualizationTab")

    def get_selected_sources(self) -> List[str]:
        """Get the list of selected source names.

        Returns:
            List of selected source names.
        """
        selected_sources = []
        for i in range(self.ui.listWidget.count()):
            item = self.ui.listWidget.item(i)
            if item.checkState() == Qt.Checked:
                selected_sources.append(item.text())
        logger.debug(f"Selected sources: {selected_sources}")
        return selected_sources

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
        logger.debug(f"Selected telescopes: {selected_telescopes}")
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
            self.update_scans()
            self.update_visualization()
        finally:
            self.is_processing = False
            self._unlock_ui()

    def update_scans(self):
        """Update the scans list based on the Mollweide tracks DataFrame, preserving check states."""
        current_checks = {self.ui.listScans.item(i).data(Qt.UserRole): self.ui.listScans.item(i).checkState()
                          for i in range(self.ui.listScans.count())}
        logger.debug(f"Stored check states: {current_checks}")

        self.ui.listScans.clear()
        try:
            df = self.manipulator.inspect(obj=self.observation, get_calculated_data_by_key="mollweide_tracks")
            if not isinstance(df, pl.DataFrame):
                logger.error("No valid Mollweide tracks data available for updating scans")
                self.ui.listScans.addItem(QListWidgetItem("No Mollweide tracks data available"))
                return

            expected_columns = CalculatedDataStructure.get_columns("mollweide_tracks")
            if not expected_columns:
                logger.error("No schema defined for Mollweide tracks data")
                self.ui.listScans.addItem(QListWidgetItem("No schema defined for Mollweide tracks data"))
                return
            missing_columns = [col for col in expected_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"DataFrame for Mollweide tracks missing required columns: {missing_columns}")
                self.ui.listScans.addItem(QListWidgetItem("Invalid Mollweide tracks data structure"))
                return

            scan_times = df.group_by("scan_name").agg(time=pl.col("time").first()).sort("time")
            if scan_times.is_empty():
                logger.debug("No scans found in Mollweide tracks DataFrame")
                self.ui.listScans.addItem(QListWidgetItem("No scans available"))
                return

            scans = scan_times["scan_name"].to_list()
            for row in scan_times.iter_rows(named=True):
                scan_name = row["scan_name"]
                start_time = row["time"]  # MJD as float64
                display_text = f"{start_time:.6f} (MJD)"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, scan_name)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(current_checks.get(scan_name, Qt.Checked))
                self.ui.listScans.addItem(item)
            logger.debug(f"Populated {len(scans)} scans")
        except Exception as e:
            logger.error(f"Failed to update scans: {str(e)}")
            self.ui.listScans.addItem(QListWidgetItem("Failed to retrieve scans"))

    def update_visualization(self):
        """Update the Mollweide tracks visualization based on current filter selections."""
        sources = self.get_selected_sources()
        scans = self.get_selected_scans()
        telescopes = self.get_selected_telescopes()
        logger.debug(f"Updating visualization: sources={sources}, scans={scans}, telescopes={telescopes}")

        if not sources or not scans or not telescopes:
            logger.debug("Missing required filters (sources, scans, or telescopes), creating empty Mollweide plot")
            self._create_empty_mollweide()
            return

        vis_attributes = {
            "plot_type": "mollweide_tracks",
            "show": False,
            "return_figure": True,
            "store_key": "mollweide_tracks",
            "scans": scans,
            "telescopes": telescopes,
            "sources": sources
        }

        try:
            result = self.manipulator.visualize(obj=self.observation, **vis_attributes)
            logger.debug(f"Visualization result: {result}")
            figure = result.get("figure")
            if figure:
                self.embed_figure(figure)
                logger.debug("Mollweide tracks visualization updated")
            else:
                logger.warning("No figure returned from visualizer, embedding empty plot")
                self._create_empty_mollweide()
        except Exception as e:
            logger.error(f"Exception during Mollweide tracks visualization update: {str(e)}")
            self._create_empty_mollweide()

    def _create_empty_mollweide(self):
        """Create and embed an empty Mollweide projection plot."""
        logger.debug("Creating empty Mollweide projection")
        self._clear_canvas()
        try:
            widget_size = self.ui.widget.size()
            width, height = widget_size.width(), widget_size.height()
            logger.debug(f"Widget size: width={width}, height={height}")
            if width <= 0 or height <= 0:
                logger.error("Invalid widget size, using default size")
                width, height = 800, 600
            dpi = self.ui.widget.physicalDpiX() or 100
            figsize = (width / dpi, height / dpi)
            self.figure = Figure(figsize=figsize, dpi=dpi)
            ax = self.figure.add_subplot(111, projection="mollweide")
            ax.set_title(f"Mollweide Tracks\nObs. code: {self.observation.get_observation_code()}")
            self.figure.subplots_adjust(left=0.10, bottom=0.10, right=0.85, top=0.90)
            self.embed_figure(self.figure)
        except Exception as e:
            logger.error(f"Failed to create empty Mollweide plot: {str(e)}")
            self.figure = None

    def closeEvent(self, event):
        """Ensure resources are cleaned up when the widget is closed."""
        self._clear_canvas()
        super().closeEvent(event)
        logger.debug(f"MollweideVisualizationTab closed, resources cleaned up")