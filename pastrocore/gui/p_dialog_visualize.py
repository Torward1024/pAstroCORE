# pastrocore/gui/p_dialog_visualization.py
from PySide6.QtWidgets import QDialog, QMessageBox, QApplication
from PySide6.QtCore import Slot
from .ui_dialog_visualize import Ui_VisualizationDialog
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger

class VisualizationDialog(QDialog):
    """Dialog for visualizing observation parameters using ScheduleVisualizer through ScheduleManipulator.

    This dialog allows users to select an observation from the current project,
    choose a visualization type based on available calculated data, and select
    a frequency (IF) for visualization. It interacts with ScheduleVisualizer via
    ScheduleManipulator to perform visualizations and updates the UI dynamically.

    Attributes:
        ui (Ui_VisualizationDialog): The UI instance for the dialog.
        project (ScheduleProject): The current project containing observations.
        manipulator (ScheduleManipulator): Manipulator for accessing project data and performing visualizations.
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
        self.setup_connections()
        self.populate_observations()
        self.ui.comboBoxObservation.currentIndexChanged.connect(self.update_visualization_types)

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
        available_visualizations = [v for k, v in visualization_map.items() if k in calc_data]
        self.ui.comboBoxVisualizationType.addItems(available_visualizations)
        logger.info(f"Populated {len(available_visualizations)} visualization types for observation '{current_obs_name}'")
        self.ui.pushButtonVisualize.setEnabled(bool(available_visualizations))

        # Populate frequencies based on calculated data
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
        # Filter frequencies based on calculated data keys
        freq_dependent_plots = ["uv_coverage", "beam_pattern", "synthesized_beam", "baseline_projections"]
        available_frequencies = set()
        for freq in frequencies:
            freq_name = freq.get_name()
            # Check if any frequency-dependent plot has data for this frequency
            for plot_type in freq_dependent_plots:
                store_key = f"{plot_type}_{freq_name}"
                if store_key in calc_data:
                    available_frequencies.add(freq_name)
                    self.ui.comboBoxFrequency.addItem(str(freq.get_center_frequency()), freq)
                    break  # No need to check other plot types for this frequency
        logger.info(f"Populated {len(available_frequencies)} frequencies for observation '{current_obs_name}'")
        if not available_frequencies:
            logger.info(f"No relevant frequencies found for observation '{current_obs_name}'")
            self.ui.pushButtonVisualize.setEnabled(False)

    @Slot()
    def perform_visualization(self):
        """Perform the selected visualization using ScheduleVisualizer via ScheduleManipulator."""
        obs_name = self.ui.comboBoxObservation.currentData()
        vis_type = self.ui.comboBoxVisualizationType.currentText()
        frequency = self.ui.comboBoxFrequency.currentData()

        if not obs_name or not vis_type:
            logger.warning("No observation or visualization type selected")
            QMessageBox.warning(self, "Warning", "Please select an observation and visualization type.")
            return

        # Get the observation
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

        observation = obs_response["result"]
        # Map visualization type to calculated data key
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

        # Prepare visualization request
        vis_attributes = {
            "plot_type": vis_key,
            "show": True
        }
        if frequency:
            vis_attributes["freq_name"] = frequency.get_name()

        try:
            # Perform visualization through manipulator
            self.ui.pushButtonVisualize.setEnabled(False)
            self.ui.pushButtonVisualize.setText("Visualizing...")
            QApplication.processEvents()
            response = self.manipulator.process_request({
                "operation": "visualize",
                "obj": observation,
                "attributes": vis_attributes
            })
            if response["status"] == "success":
                logger.info(f"Performed visualization '{vis_type}' for observation '{obs_name}'")
                QMessageBox.information(self, "Success", f"Visualization '{vis_type}' completed successfully.")
            else:
                logger.error(f"Failed to perform visualization '{vis_type}': {response.get('message', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to perform visualization: {response.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception during visualization '{vis_type}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to perform visualization: {str(e)}")
        finally:
            self.ui.pushButtonVisualize.setEnabled(True)
            self.ui.pushButtonVisualize.setText("View")