# pastrocore/gui/p_dialog_visualize.py
from PySide6.QtWidgets import QDialog, QMessageBox, QApplication, QVBoxLayout
from PySide6.QtCore import Slot, Qt
from .ui_dialog_visualize import Ui_VisualizationDialog
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from common.utils.logging_setup import logger
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import xarray as xr

class VisualizationDialog(QDialog):
    """Dialog for visualizing observation parameters using ScheduleVisualizer through ScheduleManipulator.

    This dialog allows users to select an observation from the current project and
    choose a visualization type based on available calculated data. It embeds Matplotlib
    figures into a QWidget for interactive visualization. Frequency selection is disabled,
    and frequency-dependent visualizations use the first available frequency.

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
        
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)

        # Set up Matplotlib canvas and toolbar
        self.figure = None  # Will be set during visualization
        self.canvas = None  # Will be initialized with the first figure
        self.toolbar = None
        self.layout = QVBoxLayout(self.ui.widget)
        logger.debug("Matplotlib canvas and toolbar will be initialized during first visualization")

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
        self.ui.comboBoxVisualizationType.clear()  # Clear visualization types when repopulating observations
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
                self.ui.pushButtonVisualize.setEnabled(True)  # Enable button if observations exist
            else:
                logger.info("No observations found in project")
                self.ui.pushButtonVisualize.setEnabled(False)
                self.ui.comboBoxVisualizationType.setEnabled(False)  # Disable visualization combo box
        else:
            logger.error(f"Failed to retrieve observations: {response.get('error', 'Unknown error')}")
            QMessageBox.critical(self, "Error", f"Failed to load observations: "
                                                f"{response.get('error', 'Unknown error')}")
            self.ui.pushButtonVisualize.setEnabled(False)
            self.ui.comboBoxVisualizationType.setEnabled(False)  # Disable visualization combo box

    @Slot()
    def update_visualization_types(self):
        """Update visualization types based on calculated data of the selected observation."""
        self.ui.comboBoxVisualizationType.clear()
        self.ui.comboBoxVisualizationType.setEnabled(False)
        self.ui.pushButtonVisualize.setEnabled(False)

        if self.ui.comboBoxObservation.count() == 0:
            logger.debug("No observations available, visualization types remain empty")
            return

        current_obs_name = self.ui.comboBoxObservation.currentData()
        if not current_obs_name:
            logger.debug("No observation selected, clearing visualization types")
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
        logger.debug(f"Calculated data keys available: {[str(k) for k in calc_data.keys()]}")
        if not isinstance(calc_data, dict):
            logger.error(f"calc_data is not a dictionary, got type {type(calc_data)}")
            self.ui.pushButtonVisualize.setEnabled(False)
            return

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
            if calc_key in calc_data:
                data = calc_data[calc_key]
                is_valid = False
                if isinstance(data, dict):
                    for source_name, source_data in data.items():
                        if isinstance(source_data, dict):
                            for scan_name, scan_data in source_data.items():
                                if isinstance(scan_data, xr.Dataset) and len(scan_data.data_vars) > 0:
                                    is_valid = True
                                    logger.debug(f"Valid xarray.Dataset for '{vis_name}' in source '{source_name}', scan '{scan_name}' "
                                                f"with data_vars: {list(scan_data.data_vars.keys())}")
                                    break
                            if is_valid:
                                available_visualizations.append(vis_name)
                                break
                        else:
                            logger.debug(f"Source data for '{vis_name}' in source '{source_name}' is not a dictionary, got type {type(source_data)}")
                else:
                    logger.debug(f"Data for '{vis_name}' is not a dictionary, got type {type(data)}")
            elif calc_key in freq_dependent_plots:
                for data_key in calc_data.keys():
                    if data_key.startswith(f"{calc_key}_"):
                        data = calc_data[data_key]
                        is_valid = False
                        if isinstance(data, dict):
                            for source_name, source_data in data.items():
                                if isinstance(source_data, dict):
                                    for scan_name, scan_data in source_data.items():
                                        if isinstance(scan_data, xr.Dataset) and len(scan_data.data_vars) > 0:
                                            is_valid = True
                                            logger.debug(f"Valid xarray.Dataset for frequency-dependent '{vis_name}' in source '{source_name}', scan '{scan_name}' "
                                                        f"with data_vars: {list(scan_data.data_vars.keys())}")
                                            break
                                    if is_valid:
                                        available_visualizations.append(vis_name)
                                        break
                                else:
                                    logger.debug(f"Source data for frequency-dependent '{vis_name}' in source '{source_name}' is not a dictionary, got type {type(source_data)}")
                        else:
                            logger.debug(f"Data for frequency-dependent '{vis_name}' is not a dictionary, got type {type(data)}")
                        if is_valid:
                            break
            else:
                logger.debug(f"No data found for visualization '{vis_name}' (calc_key: {calc_key})")

        self.ui.comboBoxVisualizationType.addItems(available_visualizations)
        logger.info(f"Populated {len(available_visualizations)} visualization types for observation '{current_obs_name}': {available_visualizations}")
        self.ui.comboBoxVisualizationType.setEnabled(bool(available_visualizations))
        self.ui.pushButtonVisualize.setEnabled(bool(available_visualizations))
        if not available_visualizations:
            logger.debug(f"No valid visualization data found for observation '{current_obs_name}'")

    @Slot()
    def perform_visualization(self):
        """Perform the selected visualization for the first available source and embed it in the QWidget."""
        obs_name = self.ui.comboBoxObservation.currentData()
        vis_type = self.ui.comboBoxVisualizationType.currentText()

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

        # Get calculated data to find the first available source
        calc_data_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": vis_obj,
            "attributes": {"get_calculated_data": None}
        })
        if not calc_data_response["status"]:
            logger.error(f"Failed to retrieve calculated data: {calc_data_response.get('error', 'Unknown error')}")
            QMessageBox.critical(self, "Error", f"Failed to load calculated data: "
                                                f"{calc_data_response.get('error', 'Unknown error')}")
            return

        calc_data = calc_data_response["result"]
        source_name = None
        store_key = vis_key
        if vis_type in ["Beam Pattern", "Synthesized Beam"]:
            # For frequency-dependent visualizations, select the first available frequency and source
            freq_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": vis_obj,
                "attributes": {"get_frequencies": None}
            })
            if not freq_response["status"]:
                logger.error(f"Failed to retrieve frequencies: {freq_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to load frequencies: "
                                                    f"{freq_response.get('error', 'Unknown error')}")
                return

            frequencies = freq_response["result"].get_active_items()
            freq_name = None
            for freq in frequencies:
                temp_store_key = f"{vis_key}_{freq.get('name').strip()}"
                if temp_store_key in calc_data and isinstance(calc_data[temp_store_key], dict):
                    for src_name, src_data in calc_data[temp_store_key].items():
                        if isinstance(src_data, dict) and any(
                            isinstance(scan_data, xr.Dataset) and len(scan_data.data_vars) > 0
                            for scan_data in src_data.values()
                        ):
                            freq_name = freq.get("name").strip()
                            source_name = src_name
                            store_key = temp_store_key
                            break
                    if freq_name:
                        break
            if not freq_name:
                for key in calc_data.keys():
                    if key.startswith(f"{vis_key}_"):
                        data = calc_data[key]
                        if isinstance(data, dict):
                            for src_name, src_data in data.items():
                                if isinstance(src_data, dict) and any(
                                    isinstance(scan_data, xr.Dataset) and len(scan_data.data_vars) > 0
                                    for scan_data in src_data.values()
                                ):
                                    freq_name = key[len(vis_key) + 1:]
                                    source_name = src_name
                                    store_key = key
                                    break
                            if freq_name:
                                break
            if not freq_name:
                logger.error(f"No valid frequency found for visualization '{vis_type}'")
                QMessageBox.critical(self, "Error", f"No valid frequency found for {vis_type}")
                return
            logger.debug(f"Selected frequency '{freq_name}' and source '{source_name}' for visualization '{vis_type}'")
        else:
            # For non-frequency-dependent visualizations, select the first source
            if vis_key in calc_data and isinstance(calc_data[vis_key], dict):
                for src_name, src_data in calc_data[vis_key].items():
                    if isinstance(src_data, dict) and any(
                        isinstance(scan_data, xr.Dataset) and len(scan_data.data_vars) > 0
                        for scan_data in src_data.values()
                    ):
                        source_name = src_name
                        break
                if not source_name:
                    logger.error(f"No valid source found for visualization '{vis_type}'")
                    QMessageBox.critical(self, "Error", f"No valid source found for {vis_type}")
                    return
            else:
                logger.error(f"No valid data for visualization '{vis_type}'")
                QMessageBox.critical(self, "Error", f"No valid data found for {vis_type}")
                return
            logger.debug(f"Selected source '{source_name}' for visualization '{vis_type}'")

        vis_attributes = {
            "plot_type": vis_key,
            "show": False,
            "return_figure": True,
            "source_name": source_name
        }
        if vis_type in ["Beam Pattern", "Synthesized Beam"]:
            vis_attributes["freq_name"] = freq_name
            vis_attributes["store_key"] = store_key

        try:
            self.ui.pushButtonVisualize.setEnabled(False)
            self.ui.pushButtonVisualize.setText("Visualizing...")
            QApplication.processEvents()
            response = self.manipulator.process_request({
                "operation": "visualize",
                "obj": vis_obj,
                "attributes": vis_attributes
            })
            logger.debug(f"Visualization response: {response}")
            if response["status"]:
                logger.info(f"Performed visualization '{vis_type}' for object '{obs_name or 'project'}', source '{source_name}'")
                # Clear existing canvas and toolbar
                if self.canvas:
                    self.layout.removeWidget(self.canvas)
                    self.canvas.deleteLater()
                    self.canvas = None
                if self.toolbar:
                    self.layout.removeWidget(self.toolbar)
                    self.toolbar.deleteLater()
                    self.toolbar = None

                # Get the figure
                figure = None
                if is_project:
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
                    result = response.get("result", {})
                    figure = result.get("figure")
                    logger.debug(f"Visualization result: {result}")
                    logger.debug(f"Retrieved figure: {figure}")
                    if not figure:
                        logger.error(f"No figure returned for visualization '{vis_type}' of observation '{obs_name}'")
                        QMessageBox.critical(self, "Error", "No figure returned from visualizer")
                        return

                # Set up new canvas and toolbar with the returned figure
                self.figure = figure
                self.canvas = FigureCanvas(self.figure)
                self.toolbar = NavigationToolbar(self.canvas, self)
                self.layout.addWidget(self.toolbar)
                self.layout.addWidget(self.canvas)
                self.canvas.draw()
                logger.debug("New Matplotlib figure embedded in QWidget")
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