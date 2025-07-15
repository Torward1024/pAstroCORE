# pastrocore/gui/p_dialog_visualize.py
from PySide6.QtWidgets import QDialog, QMessageBox, QApplication, QVBoxLayout, QWidget
from PySide6.QtCore import Slot, Qt
from .ui_dialog_visualize import Ui_VisualizationDialog
from .p_tab_vis_uv_coverage import UVVisualizationTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import numpy as np
from typing import Dict, Optional, List

class VisualizationDialog(QDialog):
    """Dialog for visualizing observation parameters using ScheduleVisualizer through ScheduleManipulator.

    This dialog allows users to select an observation and a visualization type. Each visualization type
    is displayed in a unique tab within a QTabWidget, ensuring only one tab per visualization type.
    Visualization tabs are dynamically created based on calculated data, and Matplotlib figures are
    embedded for interactive visualization.

    Attributes:
        ui (Ui_VisualizationDialog): The UI instance for the dialog.
        project (ScheduleProject): The current project containing observations.
        manipulator (ScheduleManipulator): Manipulator for accessing project data and performing visualizations.
        visualization_tabs (Dict[str, QWidget]): Dictionary mapping visualization types to their tab widgets.
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
        self.visualization_tabs: Dict[str, QWidget] = {}
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
        """Update visualization types based on calculated data of the selected observation."""
        self.ui.comboBoxVisualizationType.clear()
        current_obs_name = self.ui.comboBoxObservation.currentData()
        if not current_obs_name:
            logger.debug("No observation selected, clearing visualization types")
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
        freq_dependent_plots = ["beam_pattern", "synthesized_beam"]
        available_visualizations = []

        for calc_key, vis_name in visualization_map.items():
            if calc_key in calc_data and calc_data[calc_key].get("data"):
                available_visualizations.append(vis_name)
            elif calc_key in freq_dependent_plots:
                for data_key in calc_data.keys():
                    if data_key.startswith(f"{calc_key}_freq_") and calc_data[data_key].get("data"):
                        available_visualizations.append(vis_name)
                        break

        self.ui.comboBoxVisualizationType.addItems(available_visualizations)
        logger.info(f"Populated {len(available_visualizations)} visualization types for observation '{current_obs_name}'")
        self.ui.pushButtonVisualize.setEnabled(bool(available_visualizations))

    @Slot(int)
    def close_tab(self, index: int):
        """Close a specific tab and remove its visualization widget.

        Args:
            index (int): Index of the tab to close.
        """
        tab_widget = self.ui.tabWidget.widget(index)
        vis_type = tab_widget.property("vis_type")
        if vis_type in self.visualization_tabs:
            del self.visualization_tabs[vis_type]
        self.ui.tabWidget.removeTab(index)
        tab_widget.deleteLater()
        logger.debug(f"Closed tab for visualization type '{vis_type}' at index {index}")

    @Slot()
    def perform_visualization(self):
        """Perform the selected visualization and display it in a unique tab."""
        obs_name = self.ui.comboBoxObservation.currentData()
        vis_type = self.ui.comboBoxVisualizationType.currentText()

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

        # Map visualization type to store_key
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

        # Check if a tab for this visualization type already exists
        if vis_type in self.visualization_tabs:
            logger.debug(f"Visualization tab for '{vis_type}' exists, updating visualization")
            tab_widget = self.visualization_tabs[vis_type]
            if vis_type == "UV Coverage":
                tab_widget.update_visualization()
            else:
                # Handle other visualization types if needed
                pass
            self.ui.tabWidget.setCurrentWidget(tab_widget)
            return

        # Create visualization tab based on type
        tab_widget = None
        if vis_type == "UV Coverage":
            calc_data_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": observation,
                "attributes": {"get_calculated_data": None}
            })
            if not calc_data_response["status"]:
                logger.error(f"Failed to retrieve calculated data: {calc_data_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to load calculated data")
                return
            calc_data = calc_data_response["result"]

            # Extract sources, scans, and baselines for UV coverage
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

            tab_widget = UVVisualizationTab(self.manipulator, observation, sources, scans, baselines, parent=self)
        
        tab_widget.setProperty("vis_type", vis_type)
        self.visualization_tabs[vis_type] = tab_widget
        self.ui.tabWidget.addTab(tab_widget, vis_type)
        self.ui.tabWidget.setCurrentWidget(tab_widget)
        logger.debug(f"Created new tab for visualization type '{vis_type}'")

        # Perform visualization
        vis_attributes = {
            "plot_type": vis_key,
            "show": False,
            "return_figure": True
        }

        # Handle frequency-dependent visualizations
        if vis_type in ["Beam Pattern", "Synthesized Beam"]:
            freq_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": observation,
                "attributes": {"get_frequencies": None}
            })
            if not freq_response["status"]:
                logger.error(f"Failed to retrieve frequencies: {freq_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to load frequencies")
                return

            frequencies = freq_response["result"].get_active_items()
            calc_data = self.manipulator.process_request({
                "operation": "inspect",
                "obj": observation,
                "attributes": {"get_calculated_data": None}
            })["result"]

            freq_name = None
            for freq in frequencies:
                store_key = f"{vis_key}_{freq.get('name').strip()}"
                if store_key in calc_data:
                    freq_name = freq.get("name").strip()
                    break
            if not freq_name:
                for key in calc_data.keys():
                    if key.startswith(f"{vis_key}_freq_"):
                        freq_name = key[len(vis_key) + 1:]
                        break
            if freq_name:
                vis_attributes["freq_name"] = freq_name
                logger.debug(f"Selected frequency '{freq_name}' for visualization '{vis_type}'")
            else:
                logger.error(f"No valid frequency found for visualization '{vis_type}'")
                QMessageBox.critical(self, "Error", f"No valid frequency found for {vis_type}")
                return

        # Add filters for UV coverage
        if vis_type == "UV Coverage":
            vis_attributes.update({
                "source_name": tab_widget.get_selected_source(),
                "scans": tab_widget.get_selected_scans(),
                "baselines": tab_widget.get_selected_baselines()
            })

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
                if vis_type == "UV Coverage":
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