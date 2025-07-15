# pastrocore/gui/p_tab_vis_uv_coverage.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidgetItem
from PySide6.QtCore import Slot, Qt
from .ui_tab_vis_uv_coverage import Ui_tab_vis_uv_coverage
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from typing import List, Optional

class UVVisualizationTab(QWidget):
    """Widget for UV coverage visualization with source, scan, and baseline selection.

    This widget provides a UI for selecting a source, scans, and baselines to filter
    UV coverage data, which is then visualized using Matplotlib.

    Attributes:
        ui (Ui_tab_vis_uv_coverage): The UI instance for the UV visualization tab.
        manipulator (ScheduleManipulator): Manipulator for accessing observation data.
        observation (Observation): The observation to visualize.
        canvas (FigureCanvas): Matplotlib canvas for rendering the plot.
        toolbar (NavigationToolbar): Matplotlib toolbar for interactive controls.
    """

    def __init__(self, manipulator: ScheduleManipulator, observation: Observation,
                 sources: List[str], scans: List[str], baselines: List[str], parent=None):
        """Initialize the UV visualization tab.

        Args:
            manipulator (ScheduleManipulator): Manipulator for project operations and visualizations.
            observation (Observation): The observation to visualize.
            sources (List[str]): List of source names available for selection.
            scans (List[str]): List of scan names available for selection.
            baselines (List[str]): List of baseline names available for selection.
            parent (QWidget, optional): Parent widget for the tab.
        """
        super().__init__(parent)
        self.ui = Ui_tab_vis_uv_coverage()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self.observation = observation
        self.canvas = None
        self.toolbar = None
        logger.debug(f"UVVisualizationTab initialized for observation id={id(observation)}")

        # Populate UI elements
        self.ui.comboBox.addItems(sources)
        for scan in scans:
            item = QListWidgetItem(scan)
            item.setCheckState(Qt.Checked)
            self.ui.listScans.addItem(item)
        for baseline in baselines:
            item = QListWidgetItem(baseline)
            item.setCheckState(Qt.Checked)
            self.ui.listBaselines.addItem(item)

        # Initialize Matplotlib canvas
        self.layout = QVBoxLayout(self.ui.widget)
        self.figure = None
        logger.debug("UVVisualizationTab UI populated and ready for visualization")

        # Connect signals for filter changes
        self.ui.comboBox.currentIndexChanged.connect(self.on_filter_changed)
        self.ui.listScans.itemChanged.connect(self.on_filter_changed)
        self.ui.listBaselines.itemChanged.connect(self.on_filter_changed)

    def get_selected_source(self) -> Optional[str]:
        """Get the currently selected source name.

        Returns:
            Optional[str]: The selected source name or None if not selected.
        """
        return self.ui.comboBox.currentText() if self.ui.comboBox.currentText() else None

    def get_selected_scans(self) -> List[str]:
        """Get the list of selected scan names.

        Returns:
            List[str]: List of checked scan names.
        """
        selected_scans = []
        for i in range(self.ui.listScans.count()):
            item = self.ui.listScans.item(i)
            if item.checkState() == Qt.Checked:
                selected_scans.append(item.text())
        return selected_scans

    def get_selected_baselines(self) -> List[str]:
        """Get the list of selected baseline names.

        Returns:
            List[str]: List of checked baseline names.
        """
        selected_baselines = []
        for i in range(self.ui.listBaselines.count()):
            item = self.ui.listBaselines.item(i)
            if item.checkState() == Qt.Checked:
                selected_baselines.append(item.text())
        return selected_baselines

    @Slot()
    def embed_figure(self, figure):
        """Embed a Matplotlib figure into the widget.

        Args:
            figure: The Matplotlib figure to embed.
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
        logger.debug("Embedded Matplotlib figure in UVVisualizationTab")

    @Slot()
    def on_filter_changed(self):
        """Handle changes in filter selections by updating scans and visualization."""
        source_name = self.get_selected_source()
        logger.debug(f"Filter changed, updating scans for source '{source_name}'")
        self.update_scans_for_source(source_name)
        self.update_visualization()

    def update_visualization(self):
        """Update the UV coverage visualization based on current filter selections."""
        source_name = self.get_selected_source()
        logger.debug(f"Updating visualization for source '{source_name}'")
        vis_attributes = {
            "plot_type": "uv_coverage",
            "show": False,
            "return_figure": True,
            "source_name": source_name,
            "scans": self.get_selected_scans(),
            "baselines": self.get_selected_baselines()
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
                    logger.info(f"UV coverage visualization updated for source '{source_name}'")
                else:
                    logger.error("No figure returned from visualizer")
            else:
                logger.error(f"Failed to update visualization: {response.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception during UV visualization update: {str(e)}")
    
    def update_scans_for_source(self, source_name: str):
        """Update the scans list based on the selected source.

        Args:
            source_name (str): The name of the selected source.
        """
        self.ui.listScans.clear()
        if not source_name:
            logger.debug("No source selected, clearing scans list")
            return

        calc_data_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_calculated_data": None}
        })
        if not calc_data_response["status"]:
            logger.error(f"Failed to retrieve calculated data: {calc_data_response.get('error', 'Unknown error')}")
            return

        calc_data = calc_data_response["result"]
        scans = []
        if "baseline_projections" in calc_data and source_name in calc_data["baseline_projections"]["data"]:
            scans = sorted(list(calc_data["baseline_projections"]["data"][source_name].keys()))
        
        for scan in scans:
            item = QListWidgetItem(scan)
            item.setCheckState(Qt.Checked)
            self.ui.listScans.addItem(item)
        logger.debug(f"Populated {len(scans)} scans for source '{source_name}'")