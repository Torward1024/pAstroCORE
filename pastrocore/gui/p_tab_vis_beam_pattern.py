# pastrocore/gui/p_tab_vis_beam_pattern.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidgetItem, QApplication
from PySide6.QtCore import Slot, Qt
from .ui_tab_vis_beam_pattern import Ui_VisBeamPatternTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from pastrocore.base.frequencies import IF  # Импортируем IF для обработки объектов
from msb_arch.utils.logging_setup import logger
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from typing import List, Optional
import matplotlib.pyplot as plt
import gc

class BeamPatternVisualizationTab(QWidget):
    """Widget for beam pattern visualization with telescope and frequency selection."""

    def __init__(self, manipulator: ScheduleManipulator, observation: Observation, parent=None):
        """Initialize the beam pattern visualization tab.

        Args:
            manipulator: ScheduleManipulator instance for processing visualization requests.
            observation: Observation object containing beam pattern data.
            parent: Parent widget, typically a QDialog.
        """
        super().__init__(parent)
        self.ui = Ui_VisBeamPatternTab()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self.observation = observation
        self.canvas = None
        self.toolbar = None
        self.figure = None
        self.is_processing = False
        logger.debug("BeamPatternVisualizationTab initialized for observation id=%s", id(observation))

        self.layout = QVBoxLayout(self.ui.widget)
        self._populate_filters()
        logger.debug("BeamPatternVisualizationTab UI populated and ready for visualization")

        self.ui.listFrequencies.itemChanged.connect(self.filter_changed)
        self.ui.listTelescopes.itemChanged.connect(self.filter_changed)

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
                logger.debug("Retrieved frequencies: %s", frequencies)
            return freqs or []
        except Exception as e:
            logger.error("Failed to retrieve frequencies: %s", str(e))
            return []

    def _populate_filters(self):
        """Populate telescope and frequency filters from beam pattern DataFrame and observation."""
        try:
            # One request instead of reading the frame, checking it against the schema and
            # calling unique(). This tab has no sources or scans to choose -- only telescopes
            # and frequencies -- so it asks for the one column it needs.
            response = self.manipulator.export(
                obj=self.observation, method="distinct",
                key="beam_pattern", columns=["telescope_code"])
            values = (response["result"] if isinstance(response, dict) and "status" in response
                      else response) or {}
            telescopes = values.get("telescope_code", [])
            if not telescopes:
                logger.error("No valid beam pattern data available for populating filters")
                self.ui.listTelescopes.addItem(QListWidgetItem("No beam pattern data available"))
                return

            frequencies = self._get_frequencies()

            for telescope in telescopes:
                item = QListWidgetItem(telescope)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(Qt.Checked)
                self.ui.listTelescopes.addItem(item)
            for freq in sorted(frequencies):
                try:
                    item = QListWidgetItem(f"{float(freq):.2f} MHz")
                    item.setData(Qt.UserRole, float(freq))
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    item.setCheckState(Qt.Checked)
                    self.ui.listFrequencies.addItem(item)
                except (TypeError, ValueError) as e:
                    logger.error("Failed to format frequency %s: %s", freq, str(e))
                    continue
            logger.debug("Populated %s telescopes and %s frequencies", len(telescopes), len(frequencies))
        except Exception as e:
            logger.error("Failed to populate filters: %s", str(e))
            self.ui.listTelescopes.addItem(QListWidgetItem("Failed to retrieve filters"))

    def _lock_ui(self):
        """Lock UI elements during visualization processing."""
        self.ui.listTelescopes.setEnabled(False)
        self.ui.listFrequencies.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        logger.debug("UI locked for visualization processing")

    def _unlock_ui(self):
        """Unlock UI elements after visualization processing."""
        self.ui.listTelescopes.setEnabled(True)
        self.ui.listFrequencies.setEnabled(True)
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
            logger.error("Failed to embed figure: %s", str(e))
            self._clear_canvas()

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
        logger.debug("Selected frequencies: %s", selected_frequencies)
        return selected_frequencies

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
        logger.debug("Selected telescopes: %s", selected_telescopes)
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
            self.update_visualization()
        finally:
            self.is_processing = False
            self._unlock_ui()

    def update_visualization(self):
        """Update the beam pattern visualization based on current filter selections."""
        frequencies = self.get_selected_frequencies()
        telescopes = self.get_selected_telescopes()
        logger.debug("Updating visualization: frequencies=%s, telescopes=%s", frequencies, telescopes)

        if not frequencies or not telescopes:
            logger.debug("No frequencies or telescopes selected, clearing canvas")
            self._clear_canvas()
            return

        vis_attributes = {
            "plot_type": "beam_pattern",
            "show": False,
            "return_figure": True,
            "frequencies": frequencies,
            "telescopes": telescopes,
            "clear_previous": True
        }

        try:
            result = self.manipulator.visualize(obj=self.observation, **vis_attributes)
            logger.debug("Visualization result: %s", result)
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
            logger.error("Exception during beam pattern visualization update: %s", str(e))
            self._clear_canvas()

    def closeEvent(self, event):
        """Ensure resources are cleaned up when the widget is closed."""
        self._clear_canvas()
        super().closeEvent(event)
        logger.debug("BeamPatternVisualizationTab closed, resources cleaned up")