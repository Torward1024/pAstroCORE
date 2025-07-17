# pastrocore/gui/p_tab_vis_time_on_source.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidgetItem
from PySide6.QtCore import Slot, Qt
from .ui_tab_vis_default import Ui_VisDefaultTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from typing import List, Optional
from astropy.time import Time
import astropy.units as u
import matplotlib.pyplot as plt

class TimeOnSourceVisualizationTab(QWidget):
    """Widget for Time on Source visualization with source, scan, and telescope selection."""

    def __init__(self, manipulator: ScheduleManipulator, observation: Observation,
                 sources: List[str], scans: List[str], telescopes: List[str], parent=None):
        """Initialize the Time on Source visualization tab.

        Args:
            manipulator: ScheduleManipulator instance for processing visualization requests.
            observation: Observation object containing time on source data.
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
        self.cached_data = None
        logger.debug(f"TimeOnSourceVisualizationTab initialized for observation id={id(observation)}")

        # Populate UI elements
        self.ui.cmbSource.addItems(sources)
        for telescope in telescopes:
            item = QListWidgetItem(telescope)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.ui.listTelescopes.addItem(item)

        # Populate scans
        for scan in scans:
            item = QListWidgetItem(scan)
            item.setData(Qt.UserRole, scan)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            self.ui.listScans.addItem(item)

        # Initialize Matplotlib canvas
        self.layout = QVBoxLayout(self.ui.widget)
        self.figure = None
        logger.debug("TimeOnSourceVisualizationTab UI populated and ready for visualization")

        # Connect signals for filter changes
        self.ui.cmbSource.currentIndexChanged.connect(self.on_filter_changed)
        self.ui.listScans.itemChanged.connect(self.on_filter_changed)
        self.ui.listTelescopes.itemChanged.connect(self.on_filter_changed)

        # Cache data immediately
        self._cache_calculated_data()
        if sources:
            self.update_scans_for_source(sources[0])
            self.update_visualization()  # Trigger initial visualization

    def _cache_calculated_data(self):
        """Cache calculated data for the observation to optimize performance."""
        calc_data_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_calculated_data": {"keys": ["time_on_source"]}}
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
        """Clear the current canvas and toolbar if they exist."""
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
        logger.debug("Canvas, toolbar, and figure cleared")

    @Slot()
    def embed_figure(self, figure):
        """Embed a Matplotlib figure into the widget."""
        self._clear_canvas()  # Clear existing canvas and figure before embedding new one
        self.figure = figure
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        self.canvas.draw()
        logger.debug("Embedded Matplotlib figure in TimeOnSourceVisualizationTab")

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

        if not self.cached_data or "time_on_source" not in self.cached_data:
            logger.error("No cached time on source data available for updating scans")
            return

        scans = []
        if source_name in self.cached_data["time_on_source"]["data"]:
            scan_data = self.cached_data["time_on_source"]["data"][source_name]
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
            logger.debug(f"No time on source data for source '{source_name}'")

    def update_visualization(self):
        """Update the Time on Source visualization based on current filter selections."""
        source_name = self.get_selected_source()
        scans = self.get_selected_scans()
        telescopes = self.get_selected_telescopes()
        logger.debug(f"Updating visualization: source='{source_name}', scans={scans}, telescopes={telescopes}")

        if not source_name or not scans or not telescopes: self._clear_canvas(); return

        vis_attributes = {
            "plot_type": "time_on_source",
            "show": False,
            "return_figure": True,
            "store_key": "time_on_source",
            "source_name": source_name,
            "scans": scans,
            "telescopes": telescopes
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
                    logger.debug(f"Time on Source visualization updated for source '{source_name}'")
                else:
                    logger.error("No figure returned from visualizer")
                    self._clear_canvas()
            else:
                logger.error(f"Failed to update visualization: {response.get('message', 'Unknown error')}")
                self._clear_canvas()
        except Exception as e:
            logger.error(f"Exception during Time on Source visualization update: {str(e)}")
            self._clear_canvas()