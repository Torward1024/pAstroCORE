# pastrocore/gui/p_tab_vis_beam_pattern.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidgetItem
from PySide6.QtCore import Slot, Qt
from .ui_tab_vis_beam_pattern import Ui_VisBeamPatternTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from typing import List, Optional
import astropy.units as u
import matplotlib.pyplot as plt

class BeamPatternVisualizationTab(QWidget):
    """Widget for beam pattern visualization with telescope and frequency selection."""

    def __init__(self, manipulator: ScheduleManipulator, observation: Observation, parent=None):
        """Initialize the beam pattern visualization tab."""
        super().__init__(parent)
        self.ui = Ui_VisBeamPatternTab()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self.observation = observation
        self.canvas = None
        self.toolbar = None
        self.cached_data = None
        self.frequencies = self._get_frequencies()  # Get frequencies from observation
        self.telescopes = self._get_telescopes()  # Get telescopes from beam pattern data
        logger.debug(f"BeamPatternVisualizationTab initialized for observation id={id(observation)}")

        # Populate frequencies
        logger.debug(f"Populating frequencies: {self.frequencies}")
        for freq in self.frequencies:
            item = QListWidgetItem(f"{freq:.2f} MHz")
            item.setData(Qt.UserRole, freq)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            self.ui.listFrequencies.addItem(item)

        # Populate telescopes
        logger.debug(f"Populating telescopes: {self.telescopes}")
        for tel in self.telescopes:
            item = QListWidgetItem(tel)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            self.ui.listTelescopes.addItem(item)

        # Initialize Matplotlib canvas
        self.layout = QVBoxLayout(self.ui.widget)
        self.figure = None
        logger.debug("BeamPatternVisualizationTab UI populated and ready for visualization")

        # Connect signals for filter changes
        self.ui.listFrequencies.itemChanged.connect(self.on_filter_changed)
        self.ui.listTelescopes.itemChanged.connect(self.on_filter_changed)

        # Cache data immediately
        self._cache_calculated_data()

    def _get_frequencies(self) -> List[float]:
        """Retrieve the list of frequencies (in MHz) from observation."""
        response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_frequencies": None}
        })
        if response["status"]:
            frequencies = response["result"].get_items()
            freq_list = [float(f.get("frequency")) for f in frequencies]
            logger.debug(f"Retrieved frequencies from observation: {freq_list}")
            return freq_list
        logger.error(f"Failed to retrieve frequencies: {response.get('error', 'Unknown error')}")
        return []

    def _get_telescopes(self) -> List[str]:
        """Retrieve the list of telescope codes from beam pattern data."""
        response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_calculated_data": {"keys": ["beam_pattern"]}}
        })
        if response["status"]:
            beam_data = response["result"].get("beam_pattern", {}).get("data", {})
            telescopes = list(beam_data.keys())  # Extract only top-level keys (telescope codes)
            tel_list = sorted(telescopes)
            logger.debug(f"Retrieved telescopes from beam pattern data: {tel_list}")
            return tel_list
        logger.error(f"Failed to retrieve telescopes: {response.get('error', 'Unknown error')}")
        return []

    def _cache_calculated_data(self):
        """Cache calculated data for the observation to optimize performance."""
        calc_data_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_calculated_data": {"keys": ["beam_pattern", "times"]}}
        })
        if calc_data_response["status"]:
            self.cached_data = calc_data_response["result"]
            logger.debug(f"Cached calculated data: {list(self.cached_data.keys())}")
        else:
            logger.error(f"Failed to cache calculated data: {calc_data_response.get('error', 'Unknown error')}")
            self.cached_data = {}

    def get_selected_frequencies(self) -> List[float]:
        """Get the list of selected frequency values."""
        selected_frequencies = []
        for i in range(self.ui.listFrequencies.count()):
            item = self.ui.listFrequencies.item(i)
            if item.checkState() == Qt.Checked:
                freq = float(item.data(Qt.UserRole))
                selected_frequencies.append(freq)
        # Fallback to all frequencies if none are selected
        if not selected_frequencies:
            selected_frequencies = self.frequencies
            logger.debug(f"No frequencies selected, falling back to all frequencies: {selected_frequencies}")
        return selected_frequencies

    def get_selected_telescopes(self) -> List[str]:
        """Get the list of selected telescope codes."""
        selected_telescopes = []
        for i in range(self.ui.listTelescopes.count()):
            item = self.ui.listTelescopes.item(i)
            if item.checkState() == Qt.Checked:
                selected_telescopes.append(item.text())
        logger.debug(f"Selected telescopes: {selected_telescopes}")
        return selected_telescopes

    @Slot()
    def embed_figure(self, figure):
        """Embed a Matplotlib figure into the widget."""
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
        logger.debug("Embedded Matplotlib figure in BeamPatternVisualizationTab")

    @Slot()
    def on_filter_changed(self):
        """Handle changes in filter selections by updating visualization."""
        self.update_visualization()

    def update_visualization(self):
        """Update the beam pattern visualization based on current filter selections."""
        frequencies = self.get_selected_frequencies()
        telescopes = self.get_selected_telescopes()
        logger.debug(f"Updating visualization: frequencies={frequencies}, telescopes={telescopes}")

        vis_attributes = {
            "plot_type": "beam_pattern",
            "show": False,
            "return_figure": True,
            "freq_names": frequencies if frequencies != self.frequencies else None,
            "telescopes": telescopes if telescopes != self.telescopes else None
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
                    logger.debug(f"Beam pattern visualization updated")
                else:
                    logger.error("No figure returned from visualizer")
            else:
                logger.error(f"Failed to update visualization: {response.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception during beam pattern visualization update: {str(e)}")