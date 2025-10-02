# pastrocore/gui/p_tab_vis_base.py
from PySide6.QtWidgets import QWidget, QListWidgetItem, QApplication
from PySide6.QtCore import Slot, Qt
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from typing import List, Optional, Dict, Any
from astropy.time import Time
import matplotlib.pyplot as plt
import gc

class BaseVisualizationTab(QWidget):
    """Base class for visualization tabs with common filtering and UI management."""

    def __init__(self, manipulator: ScheduleManipulator, observation: Observation,
                 plot_type: str, cached_data: Dict[str, Any], parent=None):
        """Initialize the base visualization tab.

        Args:
            manipulator: ScheduleManipulator instance for visualization requests.
            observation: Observation object to visualize.
            plot_type: Type of visualization (e.g., 'az_el', 'sun_angles').
            cached_data: Cached calculated data containing sources, scans, and times.
            parent: Parent widget, typically a QDialog.
        """
        super().__init__(parent)
        self.manipulator = manipulator
        self.observation = observation
        self.plot_type = plot_type
        self.cached_data = cached_data
        self.canvas = None
        self.toolbar = None
        self.figure = None
        self.is_processing = False
        self.sources = []
        self.telescopes = []
        self.frequencies = []
        self.scans = []
        logger.debug(f"BaseVisualizationTab initialized for plot_type={plot_type}, observation id={id(observation)}")

        # To be set by subclasses
        self.ui = None
        self.layout = None

    def _lock_ui(self):
        """Lock UI elements during visualization."""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        logger.debug(f"UI locked in {self.__class__.__name__}")

    def _unlock_ui(self):
        """Unlock UI elements after visualization."""
        QApplication.restoreOverrideCursor()
        logger.debug(f"UI unlocked in {self.__class__.__name__}")

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
        logger.debug(f"Embedded Matplotlib figure {id(figure)} in {self.__class__.__name__}")

    def get_selected_source(self) -> Optional[str]:
        """Get the currently selected source name."""
        source = self.ui.cmbSource.currentText() if hasattr(self.ui, 'cmbSource') and self.ui.cmbSource.currentText() else None
        logger.debug(f"Selected source: {source}")
        return source

    def get_selected_scans(self) -> List[str]:
        """Get the list of selected scan names."""
        selected_scans = []
        if hasattr(self.ui, 'listScans'):
            for i in range(self.ui.listScans.count()):
                item = self.ui.listScans.item(i)
                if item.checkState() == Qt.Checked:
                    selected_scans.append(item.data(Qt.UserRole))
        logger.debug(f"Selected scans: {selected_scans}")
        return selected_scans

    def get_selected_telescopes(self) -> List[str]:
        """Get the list of selected telescope codes."""
        selected_telescopes = []
        if hasattr(self.ui, 'listTelescopes'):
            for i in range(self.ui.listTelescopes.count()):
                item = self.ui.listTelescopes.item(i)
                if item.checkState() == Qt.Checked:
                    selected_telescopes.append(item.text())
        logger.debug(f"Selected telescopes: {selected_telescopes}")
        return selected_telescopes

    def get_selected_frequencies(self) -> List[float]:
        """Get the list of selected frequency values."""
        selected_frequencies = []
        if hasattr(self.ui, 'listFrequencies'):
            for i in range(self.ui.listFrequencies.count()):
                item = self.ui.listFrequencies.item(i)
                if item.checkState() == Qt.Checked:
                    selected_frequencies.append(float(item.data(Qt.UserRole)))
        logger.debug(f"Selected frequencies: {selected_frequencies}")
        return selected_frequencies

    def get_selected_baselines(self) -> List[str]:
        """Get the list of selected baseline pairs."""
        selected_baselines = []
        if hasattr(self.ui, 'listBaselines'):
            for i in range(self.ui.listBaselines.count()):
                item = self.ui.listBaselines.item(i)
                if item.checkState() == Qt.Checked:
                    selected_baselines.append(item.text())
        logger.debug(f"Selected baselines: {selected_baselines}")
        return selected_baselines

    def get_selected_units(self) -> Optional[str]:
        """Get the selected units for visualization."""
        units = self.ui.comboBox_2.currentText() if hasattr(self.ui, 'comboBox_2') and self.ui.comboBox_2.currentText() else None
        logger.debug(f"Selected units: {units}")
        return units

    def update_scans_for_source(self, source_name: Optional[str] = None):
        """Update the scans list based on the selected source using cached_data.

        Args:
            source_name: Name of the selected source, or None to include all scans.
        """
        if not hasattr(self.ui, 'listScans'):
            logger.debug(f"No scan list UI in {self.__class__.__name__}")
            return

        current_checks = {self.ui.listScans.item(i).data(Qt.UserRole): self.ui.listScans.item(i).checkState()
                          for i in range(self.ui.listScans.count())}
        logger.debug(f"Stored check states: {current_checks}")

        self.ui.listScans.clear()
        if not self.cached_data or self.plot_type not in self.cached_data:
            logger.error(f"No cached {self.plot_type} data available for updating scans")
            return

        scans = []
        scan_data = self.cached_data[self.plot_type]["data"]
        if source_name:
            if source_name in scan_data:
                scans = list(scan_data[source_name].keys())
            else:
                logger.debug(f"No {self.plot_type} data for source '{source_name}'")
                return
        else:
            scans = list(set(scan for source in scan_data for scan in scan_data[source].keys()))

        for scan_name in sorted(scans):
            time_data = self.cached_data.get("times", {}).get("data", {}).get(source_name, {}).get(scan_name, [])
            start_time = Time(time_data[0]).isot if time_data else "Unknown"
            display_text = f"{start_time}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, scan_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(current_checks.get(scan_name, Qt.Checked))
            self.ui.listScans.addItem(item)
        logger.debug(f"Populated {len(scans)} scans for source '{source_name}'")

    @Slot()
    def filter_changed(self):
        """Handle changes in filter selections by updating scans and visualization."""
        if self.is_processing:
            logger.debug("Filter change ignored, visualization is processing")
            return
        self.is_processing = True
        self._lock_ui()
        try:
            source_name = self.get_selected_source()
            logger.debug(f"Filter changed, updating scans for source '{source_name}'")
            self.update_scans_for_source(source_name)
            self.update_visualization()
        finally:
            self.is_processing = False
            self._unlock_ui()

    def update_visualization(self):
        """Update the visualization based on current filter selections.

        Must be implemented by subclasses.
        """
        raise NotImplementedError(f"update_visualization must be implemented in {self.__class__.__name__}")