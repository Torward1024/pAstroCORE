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
from astropy.time import Time
import astropy.units as u
import matplotlib.pyplot as plt

class BeamPatternVisualizationTab(QWidget):
    """Widget for beam pattern visualization with frequency and telescope selection."""

    def __init__(self, manipulator: ScheduleManipulator, observation: Observation,
                 sources: List[str], scans: List[str], telescopes: List[str], frequencies: List[str], parent=None):
        """Initialize the beam pattern visualization tab."""
        super().__init__(parent)
        self.ui = Ui_VisBeamPatternTab()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self.observation = observation
        self.canvas = None
        self.toolbar = None
        self.cached_data = None
        logger.debug(f"BeamPatternVisualizationTab initialized for observation id={id(observation)}")

        # Populate UI elements
        self.ui.cmbSource.addItems(sources)
        for telescope in telescopes:
            item = QListWidgetItem(telescope)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.ui.listTelescopes.addItem(item)

        # Populate frequencies
        for freq in frequencies:
            item = QListWidgetItem(freq)
            item.setData(Qt.UserRole, freq)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            self.ui.listFrequencies.addItem(item)

        # Initialize Matplotlib canvas
        self.layout = QVBoxLayout(self.ui.widget)
        self.figure = None
        logger.debug("BeamPatternVisualizationTab UI populated and ready for visualization")

        # Connect signals for filter changes
        self.ui.cmbSource.currentIndexChanged.connect(self.on_filter_changed)
        self.ui.listFrequencies.itemChanged.connect(self.on_filter_changed)
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
            "attributes": {"get_calculated_data": {"keys": ["beam_pattern", "times"]}}
        })
        if calc_data_response["status"]:
            self.cached_data = calc_data_response["result"]
            logger.debug(f"Cached calculated data: {list(self.cached_data.keys())}")
        else:
            logger.error(f"Failed to cache calculated data: {calc_data_response.get('error', 'Unknown error')}")
            self.cached_data = {}

    def get_selected_source(self) -> Optional[str]:
        """Get the currently selected source name."""
        source = self.ui.cmbSource.currentText() if self.ui.cmbSource.currentText() else None
        logger.debug(f"Selected source: {source}")
        return source

    def get_selected_frequencies(self) -> List[str]:
        """Get the list of selected frequency names."""
        selected_frequencies = []
        for i in range(self.ui.listFrequencies.count()):
            item = self.ui.listFrequencies.item(i)
            if item.checkState() == Qt.Checked:
                selected_frequencies.append(item.data(Qt.UserRole))
        logger.debug(f"Selected frequencies: {selected_frequencies}")
        return selected_frequencies

    def get_selected_telescopes(self) -> List[str]:
        """Get the list of selected telescope names."""
        selected_telescopes = []
        for i in range(self.ui.listTelescopes.count()):
            item = self.ui.listTelescopes.item(i)
            if item.checkState() == Qt.Checked:
                selected_telescopes.append(item.text())
        logger.debug(f"Selected telescopes: {selected_telescopes}")
        return selected_telescopes

    def get_selected_scans(self) -> List[str]:
        """Get the list of selected scan names."""
        selected_scans = []
        if not self.cached_data or "beam_pattern" not in self.cached_data:
            logger.debug("No cached beam pattern data available for scans")
            return selected_scans
        source_name = self.get_selected_source()
        if source_name and source_name in self.cached_data["beam_pattern"]["data"]:
            selected_scans = list(self.cached_data["beam_pattern"]["data"][source_name].keys())
        logger.debug(f"Selected scans: {selected_scans}")
        return selected_scans

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
        """Handle changes in filter selections by updating scans and visualization."""
        source_name = self.get_selected_source()
        logger.debug(f"Filter changed, updating scans for source '{source_name}'")
        self.update_scans_for_source(source_name)
        self.update_visualization()

    def update_scans_for_source(self, source_name: str):
        """Update the scans list based on the selected source, preserving check states."""
        current_checks = {self.ui.listFrequencies.item(i).data(Qt.UserRole): self.ui.listFrequencies.item(i).checkState()
                          for i in range(self.ui.listFrequencies.count())}
        logger.debug(f"Stored frequency check states: {current_checks}")

        self.ui.listFrequencies.clear()
        if not source_name:
            logger.debug("No source selected, clearing frequencies list")
            return

        if not self.cached_data or "beam_pattern" not in self.cached_data:
            logger.error("No cached beam pattern data available for updating frequencies")
            return

        frequencies = []
        if source_name in self.cached_data["beam_pattern"]["data"]:
            scan_data = self.cached_data["beam_pattern"]["data"][source_name]
            for scan_name in scan_data:
                for freq_name in scan_data[scan_name]:
                    if freq_name not in frequencies:
                        item = QListWidgetItem(freq_name)
                        item.setData(Qt.UserRole, freq_name)
                        item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                        item.setCheckState(current_checks.get(freq_name, Qt.Checked))
                        self.ui.listFrequencies.addItem(item)
                        frequencies.append(freq_name)
            logger.debug(f"Populated {len(frequencies)} frequencies for source '{source_name}'")
        else:
            logger.debug(f"No beam pattern data for source '{source_name}'")

    def update_visualization(self):
        """Update the beam pattern visualization based on current filter selections."""
        source_name = self.get_selected_source()
        frequencies = self.get_selected_frequencies()
        telescopes = self.get_selected_telescopes()
        scans = self.get_selected_scans()
        logger.debug(f"Updating visualization: source='{source_name}', frequencies={frequencies}, telescopes={telescopes}, scans={scans}")

        vis_attributes = {
            "plot_type": "beam_pattern",
            "show": False,
            "return_figure": True,
            "source_name": source_name,
            "freq_names": frequencies,
            "telescopes": telescopes,
            "scans": scans
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
                    logger.debug(f"Beam pattern visualization updated for source '{source_name}'")
                else:
                    logger.error("No figure returned from visualizer")
            else:
                logger.error(f"Failed to update visualization: {response.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception during beam pattern visualization update: {str(e)}")