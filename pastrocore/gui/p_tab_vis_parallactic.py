# pastrocore/gui/p_tab_vis_parallactic.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidgetItem, QApplication
from PySide6.QtCore import Slot, Qt
from .ui_tab_vis_default import Ui_VisDefaultTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from msb_arch.utils.logging_setup import logger
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from typing import List, Optional
import matplotlib.pyplot as plt
import gc

class ParallacticAngleVisualizationTab(QWidget):
    """Widget for Parallactic Angle visualization with source, scan, and telescope selection."""

    def __init__(self, manipulator: ScheduleManipulator, observation: Observation, parent=None):
        """Initialize the Parallactic Angle visualization tab.

        Args:
            manipulator: ScheduleManipulator instance for processing visualization requests.
            observation: Observation object containing parallactic angle data.
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
        self.is_processing = False

        logger.debug("ParallacticAngleVisualizationTab initialized for observation id=%s", id(observation))

        self.layout = QVBoxLayout(self.ui.widget)
        self._populate_filters()
        logger.debug("ParallacticAngleVisualizationTab UI populated and ready for visualization")

        self.ui.cmbSource.currentIndexChanged.connect(self.filter_changed)
        self.ui.listScans.itemChanged.connect(self.filter_changed)
        self.ui.listTelescopes.itemChanged.connect(self.filter_changed)

        if self.ui.cmbSource.count() > 0:
            self.update_scans_for_source(self.ui.cmbSource.currentText())
            self.update_visualization()

    def _populate_filters(self):
        """Populate source and telescope filters from Parallactic Angle DataFrame."""
        try:
            # One request instead of reading the frame, checking it against the schema and
            # calling unique() twice.
            response = self.manipulator.export(
                obj=self.observation, method="distinct",
                key="parallactic_angle", columns=["source_name", "telescope_code"])
            values = (response["result"] if isinstance(response, dict) and "status" in response
                      else response) or {}
            sources = values.get("source_name", [])
            telescopes = values.get("telescope_code", [])
            if not sources:
                logger.error("No valid parallactic angle data available for populating filters")
                self.ui.cmbSource.addItem("No parallactic angle data available")
                return

            self.ui.cmbSource.addItems(sources)
            for telescope in telescopes:
                item = QListWidgetItem(telescope)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(Qt.Checked)
                self.ui.listTelescopes.addItem(item)

            logger.debug("Populated %s sources and %s telescopes for parallactic angle", len(sources), len(telescopes))
        except Exception as e:
            logger.error("Failed to populate filters: %s", str(e))
            self.ui.cmbSource.addItem("Failed to retrieve data")

    def _lock_ui(self):
        """Lock UI elements to prevent further changes during visualization."""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.ui.cmbSource.setEnabled(False)
        self.ui.listScans.setEnabled(False)
        self.ui.listTelescopes.setEnabled(False)
        logger.debug("UI locked in ParallacticAngleVisualizationTab")

    def _unlock_ui(self):
        """Unlock UI elements after visualization is complete."""
        QApplication.restoreOverrideCursor()
        self.ui.cmbSource.setEnabled(True)
        self.ui.listScans.setEnabled(True)
        self.ui.listTelescopes.setEnabled(True)
        logger.debug("UI unlocked in ParallacticAngleVisualizationTab")

    def _clear_canvas(self):
        """Safely clear the canvas, toolbar, and figure to release resources."""
        logger.debug("Clearing canvas, toolbar, and figure")
        if self.canvas:
            try:
                self.layout.removeWidget(self.canvas)
                self.canvas.setParent(None)
                self.canvas.deleteLater()
            except Exception as e:
                logger.warning("Failed to remove canvas: %s", str(e))
            finally:
                self.canvas = None

        if self.toolbar:
            try:
                self.layout.removeWidget(self.toolbar)
                self.toolbar.setParent(None)
                self.toolbar.deleteLater()
            except Exception as e:
                logger.warning("Failed to remove toolbar: %s", str(e))
            finally:
                self.toolbar = None

        if self.figure:
            try:
                for ax in self.figure.axes:
                    ax.clear()
                    ax.remove()
                self.figure.clf()
                plt.close(self.figure)
            except Exception as e:
                logger.warning("Failed to close figure: %s", str(e))
            finally:
                self.figure = None

        gc.collect(2)

    def embed_figure(self, figure: Figure):
        """Embed a Matplotlib figure into the widget."""
        self._clear_canvas()
        self.figure = figure
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        self.canvas.draw()
        logger.debug("Embedded Matplotlib figure %s in ParallacticAngleVisualizationTab", id(figure))

    def get_selected_source(self) -> Optional[str]:
        """Get the currently selected source name."""
        source = self.ui.cmbSource.currentText() if self.ui.cmbSource.currentText() else None
        return source

    def get_selected_scans(self) -> List[str]:
        """Get the list of selected scan names."""
        selected_scans = []
        for i in range(self.ui.listScans.count()):
            item = self.ui.listScans.item(i)
            if item.checkState() == Qt.Checked:
                selected_scans.append(item.data(Qt.UserRole))
        return selected_scans

    def get_selected_telescopes(self) -> List[str]:
        """Get the list of selected telescope codes."""
        selected_telescopes = []
        for i in range(self.ui.listTelescopes.count()):
            item = self.ui.listTelescopes.item(i)
            if item.checkState() == Qt.Checked:
                selected_telescopes.append(item.text())
        return selected_telescopes

    @Slot()
    def filter_changed(self):
        """Handle changes in filter selections by updating scans and visualization."""
        if self.is_processing:
            return
        self.is_processing = True
        self._lock_ui()
        try:
            source_name = self.get_selected_source()
            self.update_scans_for_source(source_name)
            self.update_visualization()
        finally:
            self.is_processing = False
            self._unlock_ui()

    def update_scans_for_source(self, source_name: Optional[str] = None):
        """Update the scans list based on the selected source."""
        current_checks = {
            self.ui.listScans.item(i).data(Qt.UserRole): self.ui.listScans.item(i).checkState()
            for i in range(self.ui.listScans.count())
        }

        self.ui.listScans.clear()
        if not source_name:
            return

        try:
            # One request instead of a read, a filter, a group-by and a time conversion.
            response = self.manipulator.export(
                obj=self.observation, method="scan_times",
                key="parallactic_angle", source_name=source_name)
            scan_times = (response["result"] if isinstance(response, dict) and "status" in response
                          else response) or []
            if not scan_times:
                self.ui.listScans.addItem(QListWidgetItem("No scans available"))
                return

            for entry in scan_times:
                scan_name = entry["scan_name"]
                display_text = entry["start"]
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, scan_name)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(current_checks.get(scan_name, Qt.Checked))
                self.ui.listScans.addItem(item)

        except Exception as e:
            logger.error("Failed to update scans for source '%s': %s", source_name, str(e))
            self.ui.listScans.addItem(QListWidgetItem("Failed to retrieve scans"))

    def update_visualization(self):
        """Update the Parallactic Angle visualization based on current filter selections."""
        source_name = self.get_selected_source()
        scans = self.get_selected_scans()
        telescopes = self.get_selected_telescopes()

        if not source_name or not scans or not telescopes:
            self._clear_canvas()
            return

        vis_attributes = {
            "plot_type": "parallactic_angle",
            "show": False,
            "return_figure": True,
            "source_name": source_name,
            "scans": scans,
            "telescopes": telescopes
        }

        try:
            result = self.manipulator.visualize(obj=self.observation, **vis_attributes)
            if not result or (result.get("telescopes", 0) == 0):
                self._clear_canvas()
                return

            figure = result.get("figure")
            if figure:
                self.embed_figure(figure)
            else:
                self._clear_canvas()
        except Exception as e:
            logger.error("Exception during parallactic angle visualization update: %s", str(e))
            self._clear_canvas()

    def closeEvent(self, event):
        """Ensure resources are cleaned up when the widget is closed."""
        self._clear_canvas()
        super().closeEvent(event)
        logger.debug("ParallacticAngleVisualizationTab closed, resources cleaned up")