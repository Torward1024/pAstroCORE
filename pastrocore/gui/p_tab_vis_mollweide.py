# pastrocore/gui/p_tab_vis_mollweide.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidgetItem
from PySide6.QtCore import Slot, Qt
from .ui_tab_vis_mollweide import Ui_MollweideVisTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from typing import List, Optional
from astropy.time import Time
import astropy.units as u
import matplotlib.pyplot as plt


class MollweideVisualizationTab(QWidget):
    """Widget for Mollweide tracks visualization with source, scan, and telescope selection."""

    def __init__(self, manipulator: ScheduleManipulator, observation: Observation,
                 sources: List[str], scans: List[str], telescopes: List[str], parent=None):
        """Initialize the Mollweide tracks visualization tab.

        Args:
            manipulator: ScheduleManipulator instance for handling visualization requests.
            observation: Observation object containing the Mollweide tracks data.
            sources: List of source names available for visualization.
            scans: List of scan names available for visualization.
            telescopes: List of telescope codes available for visualization.
            parent: Parent widget (optional).
        """
        super().__init__(parent)
        self.ui = Ui_MollweideVisTab()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self.observation = observation
        self.canvas = None
        self.toolbar = None
        self.cached_data = None
        logger.debug(f"MollweideVisualizationTab initialized for observation id={id(observation)}")

        # Populate UI elements
        self.ui.listWidget.setObjectName("listSources")  # Rename for clarity
        self.ui.listWidget.addItems(sources)
        for source in sources:
            item = self.ui.listWidget.findItems(source, Qt.MatchExactly)[0]
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)

        for telescope in telescopes:
            item = QListWidgetItem(telescope)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.ui.listTelescopes.addItem(item)

        for scan in scans:
            item = QListWidgetItem(scan)
            item.setData(Qt.UserRole, scan)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            self.ui.listScans.addItem(item)

        # Initialize Matplotlib canvas
        self.layout = QVBoxLayout(self.ui.widget)
        self.figure = None
        logger.debug("MollweideVisualizationTab UI populated and ready for visualization")

        # Connect signals for filter changes
        self.ui.listWidget.itemChanged.connect(self.on_filter_changed)
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
            "attributes": {"get_calculated_data": {"keys": ["mollweide_tracks", "times"]}}
        })
        if calc_data_response["status"]:
            self.cached_data = calc_data_response["result"]
            logger.debug(f"Cached calculated data: {list(self.cached_data.keys())}")
        else:
            logger.error(f"Failed to cache calculated data: {calc_data_response.get('error', 'Unknown error')}")
            self.cached_data = {}

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

    @Slot()
    def embed_figure(self, figure):
        """Embed a Matplotlib figure into the widget.

        Args:
            figure: Matplotlib figure to embed.
        """
        if self.canvas:
            self.layout.removeWidget(self.canvas)
            self.canvas.deleteLater()
            self.canvas = None
        if self.toolbar:
            self.layout.removeWidget(self.toolbar)
            self.toolbar.deleteLater()
            self.toolbar = None

        self.figure = figure
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        self.canvas.draw()
        logger.debug("Embedded Matplotlib figure in MollweideVisualizationTab")

    @Slot()
    def on_filter_changed(self):
        """Handle changes in filter selections by updating scans and visualization."""
        sources = self.get_selected_sources()
        logger.debug(f"Filter changed, updating scans for sources: {sources}")
        if sources:
            self.update_scans_for_source(sources[0])  # Update scans based on first selected source
        else:
            self.ui.listScans.clear()
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

        if not self.cached_data or "mollweide_tracks" not in self.cached_data:
            logger.error("No cached Mollweide tracks data available for updating scans")
            return

        scans = []
        if source_name in self.cached_data["mollweide_tracks"]["data"]:
            scan_data = self.cached_data["mollweide_tracks"]["data"][source_name]
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
            logger.debug(f"No Mollweide tracks data for source '{source_name}'")

    def update_visualization(self):
        """Update the Mollweide tracks visualization based on current filter selections."""
        sources = self.get_selected_sources()
        source_name = sources[0] if sources else None  # Use first selected source
        scans = self.get_selected_scans()
        telescopes = self.get_selected_telescopes()
        logger.debug(f"Updating visualization: source='{source_name}', scans={scans}, telescopes={telescopes}")

        vis_attributes = {
            "plot_type": "mollweide_tracks",
            "show": False,
            "return_figure": True,
            "store_key": "mollweide_tracks",
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
                figure = response.get("result", {}).get("figure")
                if figure:
                    self.embed_figure(figure)
                    logger.debug(f"Mollweide tracks visualization updated for source '{source_name}'")
                else:
                    logger.error("No figure returned from visualizer")
            else:
                logger.error(f"Failed to update visualization: {response.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception during Mollweide tracks visualization update: {str(e)}")