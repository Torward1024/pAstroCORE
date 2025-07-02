# pastrocore/gui/p_dialog_visualization.py
from PySide6.QtWidgets import QDialog, QMessageBox, QApplication, QVBoxLayout
from PySide6.QtCore import Slot
from .ui_dialog_visualize import Ui_VisualizationDialog
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from typing import Dict, Any

class VisualizationDialog(QDialog):
    """Dialog for visualizing observation parameters using ScheduleVisualizer through ScheduleManipulator.

    This dialog allows users to select an observation from the current project,
    choose a visualization type based on available calculated data, and select
    a frequency (IF) for visualization. It embeds Matplotlib figures into a QWidget
    for interactive visualization.

    Attributes:
        ui (Ui_VisualizationDialog): The UI instance for the dialog.
        project (ScheduleProject): The current project containing observations.
        manipulator (ScheduleManipulator): Manipulator for accessing project data and performing visualizations.
        canvas (FigureCanvas): Matplotlib canvas for rendering plots.
        toolbar (NavigationToolbar): Matplotlib toolbar for interactive controls.
    """

    def __init__(self, project: ScheduleProject, manipulator: ScheduleManipulator, parent=None):
        """Initialize the visualization dialog.

        Args:
            project (ScheduleProject): The current project instance.
            manipulator (ScheduleManipulator): The manipulator for project operations and visualizations.
            parent (QWidget, optional): Parent widget for the dialog.
        """
        super().__init__(parent)
        self.ui = Ui_VisualizationDialog()
        self.ui.setupUi(self)
        self.project = project
        self.manipulator = manipulator
        logger.debug(f"VisualizationDialog initialized with project id={id(self.project)}, "
                    f"manipulator id={id(self.manipulator)}")

        # Set up Matplotlib canvas and toolbar
        self.figure = plt.Figure(figsize=(8, 5))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout = QVBoxLayout(self.ui.widget)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        logger.debug("Matplotlib canvas and toolbar initialized in VisualizationDialog")

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
        logger.debug("VisualizationDialog connections set up")

    def populate_observations(self):
        """Populate the observation combo box with available observations from the project."""
        self.ui.comboBoxObservation.clear()
        response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.project,
            "attributes": {"get_items": None}
        })
        if response["status"]:
            observations = response["result"]
            if observations:
                for obs_name, obs in observations.items():
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
                logger.info(f"Populated {self.ui.comboBoxObservation.count()} observations in comboBoxObservation")
            else:
                logger.info("No observations found in project")
                self.ui.pushButtonVisualize.setEnabled(False)
        else:
            logger.error(f"Failed to retrieve observations: {response.get('error', 'Unknown error')}")
            QMessageBox.critical(self, "Error", f"Failed to load observations: "
                                                f"{response.get('error', 'Unknown error')}")
            self.ui.pushButtonVisualize.setEnabled(False)

    @Slot()
    def update_visualization_types(self):
        """Update visualization types and frequencies based on calculated data of the selected observation."""
        self.ui.comboBoxVisualizationType.clear()
        self.ui.comboBoxFrequency.clear()
        current_obs_name = self.ui.comboBoxObservation.currentData()
        if not current_obs_name:
            logger.debug("No observation selected, clearing visualization types and frequencies")
            self.ui.pushButtonVisualize.setEnabled(False)
            return

        # Get the observation object
        obs_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.project,
            "attributes": {"get_item": current_obs_name}
        })
        if not obs_response["status"]:
            logger.error(f"Failed to retrieve observation '{current_obs_name}': "
                        f"{obs_response.get('error', 'Unknown error')}")
            QMessageBox.critical(self, "Error", f"Failed to load observation: "
                                                f"{obs_response.get('error', 'Unknown error')}")
            return

        observation = obs_response["result"]
        # Get calculated data
        calc_data_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": observation,
            "attributes": {"get_calculated_data": None}
        })
        if not calc_data_response["status"]:
            logger.error(f"Failed to retrieve calculated data: {calc_data_response.get('error', 'Unknown error')}")
            self.ui.pushButtonVisualize.setEnabled(False)
            return

        calc_data = calc_data_response["result"]
        logger.debug(f"Calculated data type: {type(calc_data)}, keys: {[str(k) for k in calc_data.keys()]}")
        if not isinstance(calc_data, dict):
            logger.error(f"calc_data is not a dictionary, got type {type(calc_data)}")
            self.ui.pushButtonVisualize.setEnabled(False)
            return

        # Map calculated data keys to visualization types
        visualization_map = {
            "uv_coverage": "UV Coverage",
            "source_visibility": "Source Visibility",
            "sun_angles": "Sun Angles",
            "az_el": "Az/El or HA/Dec",
            "time_on_source": "Time on Source",
            "beam_pattern": "Beam Pattern",
            "synthesized_beam": "Synthesized Beam",
            "baseline_projections": "Baseline Projections",
            "mollweide_tracks": "Mollweide Tracks"
        }
        freq_dependent_plots = ["uv_coverage", "beam_pattern", "synthesized_beam", "baseline_projections"]
        available_visualizations = []

        for calc_key, calc_value in visualization_map.items():
            if calc_key in calc_data:
                available_visualizations.append(calc_value)
            elif calc_key in freq_dependent_plots:
                for data_key in calc_data.keys():
                    if data_key.startswith(f"{calc_key}_freq_"):
                        available_visualizations.append(calc_value)
                        break

        self.ui.comboBoxVisualizationType.addItems(available_visualizations)
        logger.info(f"Populated {len(available_visualizations)} visualization types for observation '{current_obs_name}'")
        self.ui.pushButtonVisualize.setEnabled(bool(available_visualizations))

        # Populate frequencies
        freq_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": observation,
            "attributes": {"get_frequencies": None}
        })
        if not freq_response["status"]:
            logger.error(f"Failed to retrieve frequencies: {freq_response.get('error', 'Unknown error')}")
            self.ui.pushButtonVisualize.setEnabled(False)
            return

        frequencies = freq_response["result"].get_active_items()
        logger.debug(f"Retrieved {len(frequencies)} frequencies: {[f.get('name') for f in frequencies]}")
        available_frequencies = set()

        for freq in frequencies:
            freq_name = freq.get("name").strip()
            for plot_type in freq_dependent_plots:
                store_key = f"{plot_type}_{freq_name}"
                if store_key in calc_data:
                    available_frequencies.add(freq_name)
                    self.ui.comboBoxFrequency.addItem(f"{freq.get('frequency')} MHz", freq)
                    break

        if not available_frequencies:
            logger.debug("No frequencies found via store_key, attempting to extract from calc_data keys")
            for key in calc_data.keys():
                for plot_type in freq_dependent_plots:
                    if key.startswith(f"{plot_type}_freq_"):
                        freq_name = key[len(plot_type) + 1:]
                        available_frequencies.add(freq_name)
                        for freq in frequencies:
                            if freq.get("name").strip() == freq_name:
                                self.ui.comboBoxFrequency.addItem(f"{freq.get('frequency')} MHz", freq)
                                break

        logger.info(f"Populated {len(available_frequencies)} frequencies for observation '{current_obs_name}'")
        self.ui.pushButtonVisualize.setEnabled(bool(available_frequencies))

    @Slot()
    def perform_visualization(self):
        """Perform the selected visualization and embed it in the QWidget."""
        obs_name = self.ui.comboBoxObservation.currentData()
        vis_type = self.ui.comboBoxVisualizationType.currentText()
        frequency = self.ui.comboBoxFrequency.currentData()

        if not obs_name or not vis_type:
            logger.warning("No observation or visualization type selected")
            QMessageBox.warning(self, "Warning", "Please select an observation and visualization type.")
            return

        # Get the observation or project
        vis_obj = self.project
        is_project = False
        if obs_name:
            obs_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.project,
                "attributes": {"get_item": obs_name}
            })
            if not obs_response["status"]:
                logger.error(f"Failed to retrieve observation '{obs_name}': "
                            f"{obs_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to load observation: "
                                                    f"{obs_response.get('error', 'Unknown error')}")
                return
            vis_obj = obs_response["result"]
        else:
            is_project = True
            logger.debug("Visualizing entire ScheduleProject")

        visualization_map = {
            "UV Coverage": "uv_coverage",
            "Source Visibility": "source_visibility",
            "Sun Angles": "sun_angles",
            "Az/El or HA/Dec": "az_el",
            "Time on Source": "time_on_source",
            "Beam Pattern": "beam_pattern",
            "Synthesized Beam": "synthesized_beam",
            "Baseline Projections": "baseline_projections",
            "Mollweide Tracks": "mollweide_tracks"
        }
        vis_key = visualization_map.get(vis_type)
        if not vis_key:
            logger.error(f"Invalid visualization type: {vis_type}")
            QMessageBox.critical(self, "Error", f"Invalid visualization type: {vis_type}")
            return

        vis_attributes = {
            "plot_type": vis_key,
            "show": False,  # Prevent displaying in a separate window
            "return_figure": True  # Request the figure object
        }
        if frequency:
            vis_attributes["freq_name"] = frequency.get("name")

        try:
            self.ui.pushButtonVisualize.setEnabled(False)
            self.ui.pushButtonVisualize.setText("Visualizing...")
            QApplication.processEvents()
            response = self.manipulator.process_request({
                "operation": "visualize",
                "obj": vis_obj,
                "attributes": vis_attributes
            })
            logger.debug(response)
            if response["status"]:
                logger.info(f"Performed visualization '{vis_type}' for object '{obs_name or 'project'}'")
                # Clear the current figure
                self.figure.clear()
                figure = None
                if is_project:
                    # Handle ScheduleProject: extract the first valid figure from results
                    results = response.get("result", {})
                    for obs_code, obs_result in results.items():
                        if obs_result.get("status") and obs_result.get("figure"):
                            figure = obs_result["figure"]
                            logger.debug(f"Using figure '{figure}' from observation '{obs_code}'")
                            break
                    if not figure:
                        logger.error("No valid figure found in project visualization results")
                        QMessageBox.critical(self, "Error", "No valid figure returned from project visualization")
                        return
                else:
                    # Handle single Observation
                    result = response.get("result", {})
                    figure = result.get("figure")
                    logger.debug(result)
                    logger.debug(figure)
                    if not figure:
                        logger.error(f"No figure returned for visualization '{vis_type}' of observation '{obs_name}'")
                        QMessageBox.critical(self, "Error", "No figure returned from visualizer")
                        return

                # Embed the figure's axes in the dialog's canvas
                for ax in figure.axes:
                    self.figure.add_axes(ax)
                self.canvas.draw()
                logger.debug("Matplotlib figure embedded in QWidget")
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