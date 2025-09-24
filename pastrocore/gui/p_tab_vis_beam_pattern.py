# pastrocore/gui/p_tab_vis_beam_pattern.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidgetItem, QApplication
from PySide6.QtCore import Slot, Qt
from .ui_tab_vis_beam_pattern import Ui_VisBeamPatternTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from typing import List
import matplotlib.pyplot as plt
import gc

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
        self.figure = None
        self.is_processing = False
        self.frequencies = self._get_frequencies()
        self.telescopes = self._get_telescopes()
        logger.debug(f"BeamPatternVisualizationTab initialized for observation id={id(observation)}")

        logger.debug(f"Populating frequencies: {self.frequencies}")
        for freq in self.frequencies:
            item = QListWidgetItem(f"{freq:.2f} MHz")
            item.setData(Qt.UserRole, freq)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            self.ui.listFrequencies.addItem(item)

        logger.debug(f"Populating telescopes: {self.telescopes}")
        for tel in self.telescopes:
            item = QListWidgetItem(tel)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            self.ui.listTelescopes.addItem(item)

        self.layout = QVBoxLayout(self.ui.widget)
        logger.debug("BeamPatternVisualizationTab UI populated and ready for visualization")

        self.ui.listFrequencies.itemChanged.connect(self.filter_changed)
        self.ui.listTelescopes.itemChanged.connect(self.filter_changed)

        self._cache_calculated_data()
    
    def _lock_ui(self):
        """Lock UI elements to prevent further changes during visualization."""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.ui.listFrequencies.setEnabled(False)
        self.ui.listTelescopes.setEnabled(False)
        logger.debug("UI locked in BaselineProjectionsVisualizationTab")

    def _unlock_ui(self):
        """Unlock UI elements after visualization is complete."""
        QApplication.restoreOverrideCursor()
        self.ui.listFrequencies.setEnabled(True)
        self.ui.listTelescopes.setEnabled(True)
        logger.debug("UI unlocked in BaselineProjectionsVisualizationTab")

    def _get_frequencies(self) -> List[float]:
        """Retrieve the list of frequencies (in MHz) from observation."""
        try:
            frequencies = self.manipulator.inspect(obj=self.observation, get_frequencies=None)
            freq_list = [float(f.get("frequency")) for f in frequencies.get_items()]
            logger.debug(f"Retrieved frequencies from observation: {freq_list}")
            return freq_list
        except Exception as e:
            logger.error(f"Failed to retrieve frequencies: {str(e)}")
            return []

    def _get_telescopes(self) -> List[str]:
        """Retrieve the list of telescope codes from beam pattern data."""
        try:
            beam_data = self.manipulator.inspect(obj=self.observation, get_calculated_data={"keys": ["beam_pattern"]})
            telescopes = list(beam_data.get("beam_pattern", {}).get("data", {}).keys())
            tel_list = sorted(telescopes)
            logger.debug(f"Retrieved telescopes from beam pattern data: {tel_list}")
            return tel_list
        except Exception as e:
            logger.error(f"Failed to retrieve telescopes: {str(e)}")
            return []

    def _cache_calculated_data(self):
        """Cache calculated data for the observation to optimize performance."""
        try:
            self.cached_data = self.manipulator.inspect(obj=self.observation, get_calculated_data={"keys": ["beam_pattern", "times"]})
            logger.debug(f"Cached calculated data: {list(self.cached_data.keys())}")
        except Exception as e:
            logger.error(f"Failed to cache calculated data: {str(e)}")
            self.cached_data = {}

    def get_selected_frequencies(self) -> List[float]:
        """Get the list of selected frequency values."""
        selected_frequencies = []
        for i in range(self.ui.listFrequencies.count()):
            item = self.ui.listFrequencies.item(i)
            if item.checkState() == Qt.Checked:
                freq = float(item.data(Qt.UserRole))
                selected_frequencies.append(freq)
        logger.debug(f"Selected frequencies: {selected_frequencies}")
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

        gc.collect(2)
        logger.debug(f"Number of open figures after cleanup: {len(plt.get_fignums())}")

    def embed_figure(self, figure: Figure):
        """Embed a Matplotlib figure into the widget."""
        self._clear_canvas()
        self.figure = figure
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        self.canvas.draw()
        logger.debug(f"Embedded Matplotlib figure {id(figure)} in BeamPatternVisualizationTab")

    @Slot()
    def filter_changed(self):
        """Handle changes in filter selections by updating visualization."""
        if self.is_processing:
            logger.debug("Filter change ignored, visualization is processing")
            return
        self.is_processing = True
        self._lock_ui()
        try:
            self.update_visualization()
        finally:
            self.is_processing = False
            self._unlock_ui()

    def update_visualization(self):
        """Update the beam pattern visualization based on current filter selections."""
        frequencies = self.get_selected_frequencies()
        telescopes = self.get_selected_telescopes()
        logger.debug(f"Updating visualization: frequencies={frequencies}, telescopes={telescopes}")

        if not frequencies or not telescopes:
            logger.debug("No frequencies or telescopes selected, clearing canvas")
            self._clear_canvas()
            return

        vis_attributes = {
            "plot_type": "beam_pattern",
            "show": False,
            "return_figure": True,
            "freq_names": frequencies,
            "telescopes": telescopes,
            "clear_previous": True
        }

        try:
            result = self.manipulator.visualize(obj=self.observation, **vis_attributes)
            logger.debug(f"Visualization result: {result}")
            if not result or (result.get("telescopes", 0) == 0 and result.get("frequencies", 0) == 0):
                logger.debug("Empty visualization result, clearing canvas")
                self._clear_canvas()
                return
            figure = result.get("figure")
            if figure:
                self.embed_figure(figure)
                logger.debug("Beam pattern visualization updated successfully")
            else:
                logger.error("No figure returned from visualizer, clearing canvas")
                self._clear_canvas()
        except Exception as e:
            logger.error(f"Exception during beam pattern visualization update: {str(e)}")
            self._clear_canvas()

    def closeEvent(self, event):
        """Ensure resources are cleaned up when the widget is closed."""
        self._clear_canvas()
        super().closeEvent(event)
        logger.debug(f"BeamPatternVisualizationTab closed, resources cleaned up")