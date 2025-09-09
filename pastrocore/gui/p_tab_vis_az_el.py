# pastrocore/gui/p_tab_vis_az_el.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidgetItem, QApplication
from PySide6.QtCore import Slot, Qt
from .ui_tab_vis_default import Ui_VisDefaultTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from typing import List, Optional
from astropy.time import Time
import matplotlib.pyplot as plt
import gc

class AzElVisualizationTab(QWidget):
    """Widget for Az/El or HA/Dec visualization with source, scan, and telescope selection."""

    def __init__(self, manipulator: ScheduleManipulator, observation: Observation,
                 sources: List[str], scans: List[str], telescopes: List[str], parent=None):
        """Initialize the Az/El or HA/Dec visualization tab.

        Args:
            manipulator: ScheduleManipulator instance for processing visualization requests.
            observation: Observation object containing Az/El or HA/Dec data.
            sources: List of available source names.
            scans: List of available scan names.
            telescopes: List of available telescope codes.
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
        self.cached_data = None
        self.is_processing = False
        self.coord_type = "AzEl"
        logger.debug(f"AzElVisualizationTab initialized for observation id={id(observation)}")

        self.ui.cmbSource.addItems(sources)
        for telescope in telescopes:
            item = QListWidgetItem(telescope)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            self.ui.listTelescopes.addItem(item)

        for scan in scans:
            item = QListWidgetItem(scan)
            item.setData(Qt.UserRole, scan)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            self.ui.listScans.addItem(item)

        self.layout = QVBoxLayout(self.ui.widget)
        logger.debug("AzElVisualizationTab UI populated and ready for visualization")

        self.ui.cmbSource.currentIndexChanged.connect(self.filter_changed)
        self.ui.listScans.itemChanged.connect(self.filter_changed)
        self.ui.listTelescopes.itemChanged.connect(self.filter_changed)

        self._cache_calculated_data()
        if sources:
            self.update_scans_for_source(sources[0])
            self.update_visualization()
    
    def _lock_ui(self):
        """Lock UI elements to prevent further changes during visualization."""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.ui.cmbSource.setEnabled(False)
        self.ui.listScans.setEnabled(False)
        self.ui.listTelescopes.setEnabled(False)
        logger.debug("UI locked in AzElVisualizationTab")

    def _unlock_ui(self):
        """Unlock UI elements after visualization is complete."""
        QApplication.restoreOverrideCursor()
        self.ui.cmbSource.setEnabled(True)
        self.ui.listScans.setEnabled(True)
        self.ui.listTelescopes.setEnabled(True)
        logger.debug("UI unlocked in AzElVisualizationTab")

    def _cache_calculated_data(self):
        """Cache calculated data for the observation to optimize performance."""
        calc_data_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_calculated_data": {"keys": ["az_el", "times"]}}
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
        source = self.ui.cmbSource.currentText() if self.ui.cmbSource.currentText() else None
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

    def get_selected_telescopes(self) -> List[str]:
        """Get the list of selected telescope names.

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

    def _clear_canvas(self):
        """Aggressively clear the canvas, toolbar, and figure to release all resources."""
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
        logger.debug(f"Embedded Matplotlib figure {id(figure)} in AzElVisualizationTab")

    @Slot()
    def filter_changed(self):
        """Handle changes in filter selections by updating scans and visualization."""
        if self.is_processing:
            logger.debug("Filter change ignored, visualization is processing")
            return
        self.is_processing = True
        self._lock_ui()  # Lock UI immediately to prevent new signals
        try:
            source_name = self.get_selected_source()
            logger.debug(f"Filter changed, updating scans for source '{source_name}'")
            self.update_scans_for_source(source_name)
            self.update_visualization()
        finally:
            self.is_processing = False
            self._unlock_ui()

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

        if not self.cached_data or "az_el" not in self.cached_data:
            logger.error("No cached Az/El data available for updating scans")
            return

        scans = []
        if source_name in self.cached_data["az_el"]["data"]:
            scan_data = self.cached_data["az_el"]["data"][source_name]
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
                    display_text = f"{start_time}"
                    item = QListWidgetItem(display_text)
                    item.setData(Qt.UserRole, scan_name)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    item.setCheckState(current_checks.get(scan_name, Qt.Checked))
                    self.ui.listScans.addItem(item)
                    scans.append(scan_name)
            logger.debug(f"Populated {len(scans)} scans for source '{source_name}'")
        else:
            logger.debug(f"No Az/El data for source '{source_name}'")

    def update_visualization(self):
        """Update the Az/El or HA/Dec visualization based on current filter selections."""
        source_name = self.get_selected_source()
        scans = self.get_selected_scans()
        telescopes = self.get_selected_telescopes()
        logger.debug(f"Updating visualization: source='{source_name}', scans={scans}, telescopes={telescopes}")

        # Check if any required filters are missing
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
            response = self.manipulator.process_request({
                "operation": "visualize",
                "obj": self.observation,
                "attributes": vis_attributes
            })
            logger.debug(f"Visualization response: {response}")
            if response["status"]:
                result = response.get("result", {})
                if not result or (result.get("telescopes", 0) == 0):
                    logger.debug("Empty visualization result, clearing canvas")
                    self._clear_canvas()
                    return
                figure = result.get("figure")
                if figure:
                    self.embed_figure(figure)
                    logger.debug(f"Az/El visualization updated for source '{source_name}'")
                else:
                    logger.error("No figure returned from visualizer, clearing canvas")
                    self._clear_canvas()
            else:
                logger.error(f"Failed to update visualization: {response.get('message', 'Unknown error')}")
                self._clear_canvas()
        except Exception as e:
            logger.error(f"Exception during Az/El visualization update: {str(e)}")
            self._clear_canvas()

    def closeEvent(self, event):
        """Ensure resources are cleaned up when the widget is closed."""
        self._clear_canvas()
        super().closeEvent(event)
        logger.debug(f"AzElVisualizationTab closed, resources cleaned up")