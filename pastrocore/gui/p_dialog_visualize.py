# pastrocore/gui/p_dialog_visualize.py
from PySide6.QtWidgets import QDialog, QMessageBox, QApplication, QVBoxLayout, QWidget, QProgressDialog
from PySide6.QtCore import Slot, Qt
from .ui_dialog_visualize import Ui_VisualizationDialog
from .p_tab_vis_uv_coverage import UVVisualizationTab
from .p_tab_vis_az_el import AzElVisualizationTab
from .p_tab_vis_sun_angles import SunAnglesVisualizationTab
from .p_tab_vis_beam_pattern import BeamPatternVisualizationTab
from .p_tab_vis_time_on_source import TimeOnSourceVisualizationTab
from .p_tab_vis_baseline_projections import BaselineProjectionsVisualizationTab  # Новый импорт

from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from typing import Dict, Optional, List

class VisualizationDialog(QDialog):
    """Dialog for visualizing observation parameters using ScheduleVisualizer through ScheduleManipulator."""

    def __init__(self, project: ScheduleProject, manipulator: ScheduleManipulator, parent=None):
        """Initialize the visualization dialog."""
        super().__init__(parent)
        self.ui = Ui_VisualizationDialog()
        self.ui.setupUi(self)
        self.project = project
        self.manipulator = manipulator
        self.visualization_tabs: Dict[str, QWidget] = {}
        self.cached_observations: Dict[str, Observation] = {}
        self.cached_calc_data: Dict[str, Dict] = {}
        logger.debug(f"VisualizationDialog initialized with project id={id(self.project)}, "
                     f"manipulator id={id(self.manipulator)}")

        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)

        self.setup_connections()
        self.populate_observations()
        self.ui.comboBoxObservation.currentIndexChanged.connect(self.update_visualization_types)
        if self.ui.comboBoxObservation.count() > 0:
            logger.debug("Triggering initial update_visualization_types for first observation")
            self.update_visualization_types()

    def setup_connections(self):
        """Connect UI signals to slots."""
        self.ui.pushButtonVisualize.clicked.connect(self.perform_visualization)
        self.ui.closeButton.clicked.connect(self.reject)
        self.ui.tabWidget.tabCloseRequested.connect(self.close_tab)
        logger.debug("VisualizationDialog connections set up")

    def populate_observations(self):
        """Populate the observation combo box with available observations from the project."""
        progress = QProgressDialog("Loading observations...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()

        # Clear combo boxes and disable them initially
        self.ui.comboBoxObservation.clear()
        self.ui.comboBoxObservation.setEnabled(False)
        self.ui.comboBoxVisualizationType.clear()
        self.ui.comboBoxVisualizationType.setEnabled(False)
        self.ui.pushButtonVisualize.setEnabled(False)

        response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.project,
            "attributes": {"get_items": None}
        })
        if response["status"]:
            observations = response["result"]
            if observations:
                for obs_name, obs in observations.items():
                    self.cached_observations[obs_name] = obs
                    code_response = self.manipulator.process_request({
                        "operation": "inspect",
                        "obj": obs,
                        "attributes": {"get_observation_code": None}
                    })
                    if code_response["status"]:
                        self.ui.comboBoxObservation.addItem(code_response["result"], obs_name)
                    else:
                        logger.error(f"Failed to get code for observation '{obs_name}': "
                                    f"{code_response.get('error', 'Unknown error')}")
                    # Cache calculated data for UV coverage, sun angles, beam pattern, times, time_on_source, and baseline_projections
                    calc_data_response = self.manipulator.process_request({
                        "operation": "inspect",
                        "obj": obs,
                        "attributes": {"get_calculated_data": {"keys": ["uv_coverage", "az_el", "sun_angles", "beam_pattern", "times", "time_on_source", "baseline_projections"]}}
                    })
                    if calc_data_response["status"]:
                        self.cached_calc_data[obs_name] = calc_data_response["result"]
                        logger.debug(f"Cached calculated data for observation '{obs_name}'")
                    else:
                        logger.error(f"Failed to cache data for '{obs_name}': {calc_data_response.get('error', 'Unknown error')}")
                logger.info(f"Populated {self.ui.comboBoxObservation.count()} observations in comboBoxObservation")
                # Enable comboBoxObservation if there are observations
                self.ui.comboBoxObservation.setEnabled(True)
            else:
                logger.info("No observations found in project")
        else:
            logger.error(f"Failed to retrieve observations: {response.get('error', 'Unknown error')}")
            QMessageBox.critical(self, "Error", f"Failed to load observations: "
                                                f"{response.get('error', 'Unknown error')}")
        progress.close()

    def update_visualization_types(self):
        """Update visualization types based on cached calculated data."""
        # Clear and disable visualization type combo box by default
        self.ui.comboBoxVisualizationType.clear()
        self.ui.comboBoxVisualizationType.setEnabled(False)
        self.ui.pushButtonVisualize.setEnabled(False)

        current_obs_name = self.ui.comboBoxObservation.currentData()
        if not current_obs_name:
            logger.debug("No observation selected, visualization types cleared and disabled")
            return

        calc_data = self.cached_calc_data.get(current_obs_name, {})
        if not calc_data:
            logger.debug(f"No calculated data for observation '{current_obs_name}', visualization types cleared and disabled")
            return

        visualization_map = {
            "uv_coverage": "UV Coverage",
            "sun_angles": "Sun Angles",
            "az_el": "Az/El or HA/Dec",
            "time_on_source": "Time on Source",
            "beam_pattern": "Beam Pattern",
            "baseline_projections": "Baseline Projections",
            "mollweide_tracks": "Mollweide Tracks"
        }
        available_visualizations = []

        for calc_key, vis_name in visualization_map.items():
            if calc_key in calc_data and isinstance(calc_data[calc_key], dict) and calc_data[calc_key].get("data"):
                    available_visualizations.append(vis_name)

        if available_visualizations:
            self.ui.comboBoxVisualizationType.addItems(available_visualizations)
            self.ui.comboBoxVisualizationType.setEnabled(True)
            self.ui.pushButtonVisualize.setEnabled(True)
            logger.info(f"Populated {len(available_visualizations)} visualization types for observation '{current_obs_name}'")
        else:
            logger.debug(f"No valid calculated data for visualization types in observation '{current_obs_name}'")

    @Slot(int)
    def close_tab(self, index: int):
        """Close a specific tab and remove its visualization widget."""
        tab_widget = self.ui.tabWidget.widget(index)
        vis_type = tab_widget.property("vis_type")
        if vis_type in self.visualization_tabs:
            del self.visualization_tabs[vis_type]
        self.ui.tabWidget.removeTab(index)
        tab_widget.deleteLater()
        logger.debug(f"Closed tab for visualization type '{vis_type}' at index {index}")

    def perform_visualization(self):
        """Perform the selected visualization and display it in a unique tab."""
        obs_name = self.ui.comboBoxObservation.currentData()
        vis_type = self.ui.comboBoxVisualizationType.currentText()

        if not obs_name or not vis_type:
            logger.warning("No observation or visualization type selected")
            QMessageBox.warning(self, "Warning", "Please select an observation and visualization type.")
            return

        observation = self.cached_observations.get(obs_name)
        if not observation:
            logger.error(f"Observation '{obs_name}' not found in cache")
            QMessageBox.critical(self, "Error", f"Failed to load observation: {obs_name}")
            return

        # Map visualization type to store_key
        visualization_map = {
            "UV Coverage": "uv_coverage",
            "Sun Angles": "sun_angles",
            "Az/El or HA/Dec": "az_el",
            "Time on Source": "time_on_source",
            "Beam Pattern": "beam_pattern",
            "Baseline Projections": "baseline_projections",
            "Mollweide Tracks": "mollweide_tracks"
        }
        vis_key = visualization_map.get(vis_type)
        if not vis_key:
            logger.error(f"Invalid visualization type: {vis_type}")
            QMessageBox.critical(self, "Error", f"Invalid visualization type: {vis_type}")
            return

        # Check if a tab for this visualization type already exists
        if vis_type in self.visualization_tabs:
            logger.debug(f"Visualization tab for '{vis_type}' exists, updating visualization")
            tab_widget = self.visualization_tabs[vis_type]
            if vis_type in ["UV Coverage", "Sun Angles", "Az/El or HA/Dec", "Beam Pattern", "Time on Source", "Baseline Projections"]:
                tab_widget.update_visualization()
            else:
                # Handle other visualization types if needed
                pass
            self.ui.tabWidget.setCurrentWidget(tab_widget)
            return

        # Create visualization tab based on type
        tab_widget = None
        if vis_type == "UV Coverage":
            calc_data = self.cached_calc_data.get(obs_name, {})
            # Extract sources, scans, and baselines for UV coverage
            sources = list(calc_data.get("uv_coverage", {}).get("data", {}).keys())
            scans = []
            baselines = []
            if "uv_coverage" in calc_data:
                for source_name in calc_data["uv_coverage"]["data"]:
                    scans.extend(list(calc_data["uv_coverage"]["data"][source_name].keys()))
                    for scan_name in calc_data["uv_coverage"]["data"][source_name]:
                        baselines.extend(list(calc_data["uv_coverage"]["data"][source_name][scan_name].keys()))
            scans = sorted(list(set(scans)))
            baselines = sorted(list(set(baselines)))
            tab_widget = UVVisualizationTab(self.manipulator, observation, sources, scans, baselines, parent=self)
        elif vis_type == "Sun Angles":
            calc_data = self.cached_calc_data.get(obs_name, {})
            # Extract sources, scans, and telescopes for Sun angles
            sources = list(calc_data.get("sun_angles", {}).get("data", {}).keys())
            scans = []
            telescopes = []
            if "sun_angles" in calc_data:
                for source_name in calc_data["sun_angles"]["data"]:
                    scans.extend(list(calc_data["sun_angles"]["data"][source_name].keys()))
                    for scan_name in calc_data["sun_angles"]["data"][source_name]:
                        telescopes.extend(list(calc_data["sun_angles"]["data"][source_name][scan_name].keys()))
            scans = sorted(list(set(scans)))
            telescopes = sorted(list(set(telescopes)))
            tab_widget = SunAnglesVisualizationTab(self.manipulator, observation, sources, scans, telescopes, parent=self)
        elif vis_type == "Az/El or HA/Dec":
            calc_data = self.cached_calc_data.get(obs_name, {})
            # Extract sources, scans, and telescopes for Az/El
            sources = list(calc_data.get("az_el", {}).get("data", {}).keys())
            scans = []
            telescopes = []
            if "az_el" in calc_data:
                for source_name in calc_data["az_el"]["data"]:
                    scans.extend(list(calc_data["az_el"]["data"][source_name].keys()))
                    for scan_name in calc_data["az_el"]["data"][source_name]:
                        telescopes.extend(list(calc_data["az_el"]["data"][source_name][scan_name].keys()))
            scans = sorted(list(set(scans)))
            telescopes = sorted(list(set(telescopes)))
            tab_widget = AzElVisualizationTab(self.manipulator, observation, sources, scans, telescopes, parent=self)
        elif vis_type == "Beam Pattern":
            calc_data = self.cached_calc_data.get(obs_name, {})
            telescopes = list(calc_data.get("beam_pattern", {}).get("data", {}).keys())
            telescopes = sorted(list(set(telescopes)))
            tab_widget = BeamPatternVisualizationTab(self.manipulator, observation, parent=self)
        elif vis_type == "Time on Source":
            calc_data = self.cached_calc_data.get(obs_name, {})
            # Extract sources, scans, and telescopes for Time on Source
            sources = list(calc_data.get("time_on_source", {}).get("data", {}).keys())
            scans = []
            telescopes = []
            if "time_on_source" in calc_data:
                for source_name in calc_data["time_on_source"]["data"]:
                    scans.extend(list(calc_data["time_on_source"]["data"][source_name].keys()))
                    for scan_name in calc_data["time_on_source"]["data"][source_name]:
                        telescopes.extend(list(calc_data["time_on_source"]["data"][source_name][scan_name].keys()))
            scans = sorted(list(set(scans)))
            telescopes = sorted(list(set(telescopes)))
            tab_widget = TimeOnSourceVisualizationTab(self.manipulator, observation, sources, scans, telescopes, parent=self)
        elif vis_type == "Baseline Projections":
            calc_data = self.cached_calc_data.get(obs_name, {})
            # Extract sources, scans, and baselines for Baseline Projections
            sources = list(calc_data.get("baseline_projections", {}).get("data", {}).keys())
            scans = []
            baselines = []
            if "baseline_projections" in calc_data:
                for source_name in calc_data["baseline_projections"]["data"]:
                    scans.extend(list(calc_data["baseline_projections"]["data"][source_name].keys()))
                    for scan_name in calc_data["baseline_projections"]["data"][source_name]:
                        baselines.extend(list(calc_data["baseline_projections"]["data"][source_name][scan_name].keys()))
            scans = sorted(list(set(scans)))
            baselines = sorted(list(set(baselines)))
            tab_widget = BaselineProjectionsVisualizationTab(self.manipulator, observation, sources, scans, baselines, parent=self)

        if tab_widget:
            tab_widget.setProperty("vis_type", vis_type)
            self.visualization_tabs[vis_type] = tab_widget
            self.ui.tabWidget.addTab(tab_widget, vis_type)
            self.ui.tabWidget.setCurrentWidget(tab_widget)
            logger.debug(f"Created new tab for visualization type '{vis_type}'")

        # Perform visualization
        vis_attributes = {
            "plot_type": vis_key,
            "show": False,
            "return_figure": True,
            "store_key": vis_key
        }

        # Add filters for specific visualizations
        if vis_type == "UV Coverage":
            frequencies = tab_widget.get_selected_frequencies()
            vis_attributes.update({
                "source_name": tab_widget.get_selected_source(),
                "scans": tab_widget.get_selected_scans(),
                "baselines": tab_widget.get_selected_baselines(),
                "frequencies": frequencies,
                "units": tab_widget.get_selected_units()
            })
        elif vis_type == "Sun Angles":
            vis_attributes.update({
                "source_name": tab_widget.get_selected_source(),
                "scans": tab_widget.get_selected_scans(),
                "telescopes": tab_widget.get_selected_telescopes()
            })
            logger.debug(f"Updated vis_attributes for Sun Angles: {vis_attributes}")
        elif vis_type == "Az/El or HA/Dec":
            vis_attributes.update({
                "source_name": tab_widget.get_selected_source(),
                "scans": tab_widget.get_selected_scans(),
                "telescopes": tab_widget.get_selected_telescopes(),
                "coord_type": "AzEl"
            })
            logger.debug(f"Updated vis_attributes for Az/El or HA/Dec: {vis_attributes}")
        elif vis_type == "Beam Pattern":
            vis_attributes.update({
                "telescopes": tab_widget.get_selected_telescopes(),
                "freq_names": tab_widget.get_selected_frequencies()
            })
            logger.debug(f"Updated vis_attributes for Beam Pattern: {vis_attributes}")
        elif vis_type == "Time on Source":
            vis_attributes.update({
                "source_name": tab_widget.get_selected_source(),
                "scans": tab_widget.get_selected_scans(),
                "telescopes": tab_widget.get_selected_telescopes()
            })
            logger.debug(f"Updated vis_attributes for Time on Source: {vis_attributes}")
        elif vis_type == "Baseline Projections":
            frequencies = tab_widget.get_selected_frequencies()
            vis_attributes.update({
                "source_name": tab_widget.get_selected_source(),
                "scans": tab_widget.get_selected_scans(),
                "baselines": tab_widget.get_selected_baselines(),
                "frequencies": frequencies,
                "units": tab_widget.get_selected_units()
            })
            logger.debug(f"Updated vis_attributes for Baseline Projections: {vis_attributes}")

        try:
            self.ui.pushButtonVisualize.setEnabled(False)
            self.ui.pushButtonVisualize.setText("Visualizing...")
            QApplication.processEvents()
            response = self.manipulator.process_request({
                "operation": "visualize",
                "obj": observation,
                "attributes": vis_attributes
            })
            logger.debug(f"Visualization response: {response}")
            if response["status"]:
                logger.info(f"Performed visualization '{vis_type}' for observation '{obs_name}'")
                figure = response.get("result", {}).get("figure")
                if not figure:
                    logger.error(f"No figure returned for visualization '{vis_type}'")
                    QMessageBox.critical(self, "Error", "No figure returned from visualizer")
                    return

                # Embed figure in the tab
                if vis_type in ["UV Coverage", "Sun Angles", "Az/El or HA/Dec", "Beam Pattern", "Time on Source", "Baseline Projections"]:
                    tab_widget.embed_figure(figure)
                else:
                    canvas = FigureCanvas(figure)
                    toolbar = NavigationToolbar(canvas, tab_widget)
                    layout = QVBoxLayout(tab_widget)
                    layout.addWidget(toolbar)
                    layout.addWidget(canvas)
                    canvas.draw()
            else:
                logger.error(f"Failed to perform visualization '{vis_type}': {response.get('message', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to perform visualization: "
                                                    f"{response.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception during visualization '{vis_type}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Visualization failed: {str(e)}")
        finally:
            self.ui.pushButtonVisualize.setEnabled(True)
            self.ui.pushButtonVisualize.setText("View")