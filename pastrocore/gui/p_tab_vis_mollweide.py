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
        logger.debug("Embedded Matplotlib figure in MollweideVisualizationTab")

    @Slot()
    def on_filter_changed(self):
        """Handle changes in filter selections by updating visualization."""
        logger.debug("Filter changed, updating visualization")
        self.update_visualization()

    def update_visualization(self):
        """Update the Mollweide tracks visualization based on current filter selections."""
        scans = self.get_selected_scans()
        telescopes = self.get_selected_telescopes()
        sources = self.get_selected_sources()
        logger.debug(f"Updating visualization: scans={scans}, telescopes={telescopes}, sources={sources}")

        vis_attributes = {
            "plot_type": "mollweide_tracks",
            "show": False,
            "return_figure": True,
            "store_key": "mollweide_tracks",
            "scans": scans,
            "telescopes": telescopes,
            "sources": sources  # Pass selected sources for plotting their positions
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
                    logger.debug("Mollweide tracks visualization updated")
                else:
                    logger.error("No figure returned from visualizer")
                    self._clear_canvas()
            else:
                logger.error(f"Failed to update visualization: {response.get('message', 'Unknown error')}")
                self._clear_canvas()
        except Exception as e:
            logger.error(f"Exception during Mollweide tracks visualization update: {str(e)}")
            self._clear_canvas()