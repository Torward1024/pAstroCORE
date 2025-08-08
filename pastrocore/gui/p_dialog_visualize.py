# pastrocore/gui/p_dialog_visualize.py
from PySide6.QtWidgets import QDialog, QMessageBox, QApplication, QWidget, QFileDialog
from PySide6.QtCore import Slot, Qt
from .ui_dialog_visualize import Ui_VisualizationDialog
from .p_tab_vis_mollweide import MollweideVisualizationTab
from .p_tab_vis_uv_coverage import UVVisualizationTab
from .p_tab_vis_az_el import AzElVisualizationTab
from .p_tab_vis_sun_angles import SunAnglesVisualizationTab
from .p_tab_vis_beam_pattern import BeamPatternVisualizationTab
from .p_tab_vis_time_on_source import TimeOnSourceVisualizationTab
from .p_tab_vis_baseline_projections import BaselineProjectionsVisualizationTab

from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from typing import Dict, Optional, List, Any, Tuple, Iterator
from astropy.time import Time
import numpy as np


class VisualizationDialog(QDialog):
    """Dialog for visualizing observation parameters using ScheduleVisualizer through ScheduleManipulator."""

    def __init__(self, manipulator: ScheduleManipulator, parent=None):
        """Initialize the visualization dialog."""
        super().__init__(parent)
        self.ui = Ui_VisualizationDialog()
        self.ui.setupUi(self)
        self.project = manipulator.get_managing_object()
        self.manipulator = manipulator
        self.visualization_tabs: Dict[str, QWidget] = {}
        self.cached_observations: Dict[str, Observation] = {}
        self.cached_calc_data: Dict[str, Dict] = {}
        self.is_processing = False
        logger.debug(f"VisualizationDialog initialized with project id={id(self.project)}, "
                     f"manipulator id={id(self.manipulator)}")

        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)

        self.setup_connections()
        self.populate_observations()
        # Trigger initial validation for the first observation, if any
        if self.ui.comboBoxObservation.count() > 0:
            logger.debug("Triggering initial update_visualization_types for first observation")
            self.update_visualization_types()

    def setup_connections(self):
        """Connect UI signals to slots."""
        self.ui.pushButtonVisualize.clicked.connect(self.perform_visualization)
        self.ui.pushButton.clicked.connect(self.export_calculated_data)
        self.ui.closeButton.clicked.connect(self.reject)
        self.ui.tabWidget.tabCloseRequested.connect(self.close_tab)
        self.ui.comboBoxObservation.currentIndexChanged.connect(self.handle_observation_changed)
        logger.debug("VisualizationDialog connections set up")

    def populate_observations(self):
        """Populate the observation combo box with available observations from the project."""
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
                logger.info(f"Populated {self.ui.comboBoxObservation.count()} observations in comboBoxObservation")
                self.ui.comboBoxObservation.setEnabled(True)
            else:
                logger.info("No observations found in project")
        else:
            logger.error(f"Failed to retrieve observations: {response.get('error', 'Unknown error')}")
            QMessageBox.critical(self, "Error", f"Failed to load observations: "
                                                f"{response.get('error', 'Unknown error')}")

    @Slot()
    def handle_observation_changed(self):
        """Handle observation change by clearing tabs and updating visualization types."""
        logger.debug("Observation changed, clearing all visualization tabs")
        self.clear_visualization_tabs()
        self.update_visualization_types()

    def clear_visualization_tabs(self):
        """Remove all visualization tabs and clear cached tabs."""
        for vis_type in list(self.visualization_tabs.keys()):
            index = -1
            for i in range(self.ui.tabWidget.count()):
                if self.ui.tabWidget.widget(i).property("vis_type") == vis_type:
                    index = i
                    break
            if index >= 0:
                tab_widget = self.ui.tabWidget.widget(index)
                if hasattr(tab_widget, '_clear_canvas'):
                    tab_widget._clear_canvas()
                self.ui.tabWidget.removeTab(index)
                tab_widget.deleteLater()
        self.visualization_tabs.clear()
        logger.debug("All visualization tabs cleared")

    def update_visualization_types(self):
        """Update visualization types based on cached calculated data keys for the selected observation."""
        self.ui.comboBoxVisualizationType.clear()
        self.ui.comboBoxVisualizationType.setEnabled(False)
        self.ui.pushButtonVisualize.setEnabled(False)

        current_obs_name = self.ui.comboBoxObservation.currentData()
        if not current_obs_name:
            logger.debug("No observation selected, visualization types cleared and disabled")
            return

        # Check if calculated data is already cached
        if current_obs_name not in self.cached_calc_data:
            observation = self.cached_observations.get(current_obs_name)
            if not observation:
                logger.error(f"Observation '{current_obs_name}' not found in cache")
                QMessageBox.critical(self, "Error", f"Failed to load observation: {current_obs_name}")
                return
            # Cache calculated data keys
            calc_data_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": observation,
                "attributes": {
                    "get_calculated_data": {
                        "keys": ["uv_coverage", "az_el", "sun_angles", "beam_pattern", "times",
                                 "time_on_source", "baseline_projections", "mollweide_tracks"]
                    }
                }
            })
            if calc_data_response["status"]:
                self.cached_calc_data[current_obs_name] = calc_data_response["result"]
                logger.debug(f"Cached calculated data keys for observation '{current_obs_name}'")
            else:
                logger.error(f"Failed to cache data for '{current_obs_name}': "
                             f"{calc_data_response.get('error', 'Unknown error')}")
                self.cached_calc_data[current_obs_name] = {}
                return

        calc_data = self.cached_calc_data.get(current_obs_name, {})
        if not calc_data:
            logger.debug(f"No calculated data keys for observation '{current_obs_name}'")
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
        available_visualizations = [vis_name for calc_key, vis_name in visualization_map.items()
                                   if calc_key in calc_data]

        if available_visualizations:
            self.ui.comboBoxVisualizationType.addItems(available_visualizations)
            self.ui.comboBoxVisualizationType.setEnabled(True)
            self.ui.pushButtonVisualize.setEnabled(True)
            logger.info(f"Populated {len(available_visualizations)} visualization types for observation '{current_obs_name}'")
        else:
            logger.debug(f"No valid calculated data keys for visualization in observation '{current_obs_name}'")

    @Slot(int)
    def close_tab(self, index: int):
        """Close a specific tab and remove its visualization widget."""
        tab_widget = self.ui.tabWidget.widget(index)
        vis_type = tab_widget.property("vis_type")
        if hasattr(tab_widget, '_clear_canvas'):
            tab_widget._clear_canvas()
        if vis_type in self.visualization_tabs:
            del self.visualization_tabs[vis_type]
        self.ui.tabWidget.removeTab(index)
        tab_widget.deleteLater()
        logger.debug(f"Closed tab for visualization type '{vis_type}' at index {index}")

    def perform_visualization(self):
        """Perform the selected visualization and display it in a unique tab."""
        if self.is_processing:
            logger.debug("Visualization request ignored, processing in progress")
            return
        self.is_processing = True
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.ui.pushButtonVisualize.setEnabled(False)
        self.ui.pushButtonVisualize.setText("Visualizing...")
        QApplication.processEvents()
        try:
            obs_name = self.ui.comboBoxObservation.currentData()
            vis_type = self.ui.comboBoxVisualizationType.currentText()

            if not obs_name or not vis_type:
                logger.warning("No observation or visualization type selected")
                QMessageBox.warning(self, "Warning", "Please select an observation and visualization type.")
                return

            if vis_type in self.visualization_tabs:
                logger.debug(f"Visualization tab for '{vis_type}' exists, updating visualization")
                tab_widget = self.visualization_tabs[vis_type]
                tab_widget._clear_canvas()
                tab_widget.update_visualization()
                self.ui.tabWidget.setCurrentWidget(tab_widget)
                return

            observation = self.cached_observations.get(obs_name)
            if not observation:
                logger.error(f"Observation '{obs_name}' not found in cache")
                QMessageBox.critical(self, "Error", f"Failed to load observation: {obs_name}")
                return

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

            tab_widget = None
            if vis_type == "UV Coverage":
                calc_data = self.cached_calc_data.get(obs_name, {})
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
            elif vis_type == "Mollweide Tracks":
                calc_data = self.cached_calc_data.get(obs_name, {})
                sources = list(calc_data.get("mollweide_tracks", {}).get("metadata", {}).get("sources", {}).keys())
                scans = []
                telescopes = []
                if "mollweide_tracks" in calc_data:
                    scans = list(calc_data["mollweide_tracks"]["data"].keys())
                    for scan_name in calc_data["mollweide_tracks"]["data"]:
                        telescopes.extend(list(calc_data["mollweide_tracks"]["data"][scan_name].keys()))
                    scans = sorted(list(set(scans)))
                    telescopes = sorted(list(set(telescopes)))
                    logger.debug(f"Extracted {len(sources)} sources, {len(scans)} scans, {len(telescopes)} telescopes for Mollweide Tracks")
                    logger.debug(f"Sources: {sources}, Scans: {scans}, Telescopes: {telescopes}")
                    tab_widget = MollweideVisualizationTab(self.manipulator, observation, sources, scans, telescopes, parent=self)

            if tab_widget:
                tab_widget.setProperty("vis_type", vis_type)
                self.visualization_tabs[vis_type] = tab_widget
                self.ui.tabWidget.addTab(tab_widget, vis_type)
                self.ui.tabWidget.setCurrentWidget(tab_widget)
                logger.debug(f"Created new tab for visualization type '{vis_type}'")

            vis_attributes = {
                "plot_type": vis_key,
                "show": False,
                "return_figure": True,
                "store_key": vis_key
            }

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
            elif vis_type == "Mollweide Tracks":
                vis_attributes.update({
                    "scans": tab_widget.get_selected_scans(),
                    "telescopes": tab_widget.get_selected_telescopes(),
                    "sources": tab_widget.get_selected_sources()
                })
                logger.debug(f"Updated vis_attributes for Mollweide Tracks: {vis_attributes}")

            try:
                response = self.manipulator.process_request({
                    "operation": "visualize",
                    "obj": observation,
                    "attributes": vis_attributes
                })
                logger.debug(f"Visualization response: {response}")
                if response["status"]:
                    result = response.get("result", {})
                    if not result or (result.get("telescopes", 0) == 0 and result.get("frequencies", 0) == 0):
                        logger.debug("Empty visualization result, clearing tab")
                        if vis_type in ["UV Coverage", "Sun Angles", "Az/El or HA/Dec", "Beam Pattern",
                                        "Time on Source", "Baseline Projections", "Mollweide Tracks"]:
                            tab_widget._clear_canvas()
                        logger.info(f"Cleared visualization tab for '{vis_type}' due to empty result")
                        return
                    figure = result.get("figure")
                    if not figure:
                        logger.error(f"No figure returned for visualization '{vis_type}'")
                        QMessageBox.critical(self, "Error", "No figure returned from visualizer")
                        tab_widget._clear_canvas()
                        return

                    tab_widget.embed_figure(figure)
                    logger.info(f"Performed visualization '{vis_type}' for observation '{obs_name}'")
                else:
                    logger.error(f"Failed to perform visualization '{vis_type}': {response.get('message', 'Unknown error')}")
                    QMessageBox.critical(self, "Error", f"Failed to perform visualization: "
                                                        f"{response.get('message', 'Unknown error')}")
                    tab_widget._clear_canvas()
            except Exception as e:
                logger.error(f"Exception during visualization '{vis_type}': {str(e)}")
                QMessageBox.critical(self, "Error", f"Visualization failed: {str(e)}")
                tab_widget._clear_canvas()
        finally:
            self.is_processing = False
            self.ui.pushButtonVisualize.setEnabled(True)
            self.ui.pushButtonVisualize.setText("View")
            QApplication.restoreOverrideCursor()
            QApplication.processEvents()
            logger.debug("Visualization process completed, UI unlocked")

    def _filter_data(self, data: Dict[str, Any], times_data: Dict[str, Any], source_name: Optional[str],
                    scans: Optional[List[str]], time_range: Optional[Tuple[float, float]]) -> Tuple[Dict, Dict, List[str]]:
        """
        Filter data and times based on source, scans, and time range using generators for memory efficiency.

        Args:
            data: Dictionary containing calculated data.
            times_data: Dictionary containing time data.
            source_name: Name of the source to filter (optional).
            scans: List of scan IDs to filter (optional).
            time_range: Tuple of (start, end) MJD times to filter (optional).

        Returns:
            Tuple[Dict, Dict, List[str]]: Filtered data, filtered times, and list of valid scans.
        """
        logger.debug(f"Filtering data for source={source_name}, scans={scans}, time_range={time_range}")
        if not isinstance(data, dict) or not isinstance(times_data, dict):
            logger.warning(f"Invalid data types: data={type(data)}, times_data={type(times_data)}")
            return {}, {}, []

        data = data.get("data", {})
        times_data = times_data.get("data", {})
        if not data or not times_data:
            logger.warning(f"Empty data: data={bool(data)}, times_data={bool(times_data)}")
            return {}, {}, []

        sources = [source_name] if source_name else list(data.keys())[:1]
        if not sources:
            logger.debug("No sources available")
            return {}, {}, []

        filtered_data = {}
        filtered_times = {}
        all_scans = set()

        def filter_scans(source: str) -> Iterator[Tuple[str, Dict, List]]:
            """Generator for filtered scans and their data."""
            source_data = data.get(source, {})
            source_times = times_data.get(source, {})
            if not isinstance(source_data, dict) or not isinstance(source_times, dict):
                logger.warning(f"Invalid source data types for {source}: source_data={type(source_data)}, "
                              f"source_times={type(source_times)}")
                return

            scan_list = scans if scans else list(source_data.keys())
            for scan in scan_list:
                if scan not in source_data or scan not in source_times:
                    continue
                filtered_times_list = []
                for t in source_times.get(scan, []):
                    try:
                        if not hasattr(t, 'mjd'):
                            continue
                        if time_range and not (time_range[0] <= t.mjd <= time_range[1]):
                            continue
                        filtered_times_list.append(t)
                    except (AttributeError, TypeError) as e:
                        logger.debug(f"Invalid time entry in scan {scan}, source {source}: {e}")
                        continue
                if filtered_times_list:
                    yield scan, source_data.get(scan, {}), filtered_times_list

        for source in sources:
            if source not in data or source not in times_data:
                logger.warning(f"Source {source} not found in data")
                continue
            filtered_data[source] = {}
            filtered_times[source] = {}
            for scan, scan_data, scan_times in filter_scans(source):
                filtered_data[source][scan] = scan_data
                filtered_times[source][scan] = scan_times
                all_scans.add(scan)
            if not filtered_data[source]:
                del filtered_data[source]
                del filtered_times[source]

        return filtered_data, filtered_times, list(all_scans)

    @Slot()
    def export_calculated_data(self):
        """
        Export calculated data for the current visualization tab to a tab-separated text file.

        Uses times from cached_calc_data['times'][source_name][scan_name] for time-based data,
        filtered by selected scans, sources, telescopes, baselines, or frequencies as per visualization type.
        Data formats are aligned with those used in ScheduleVisualizer, handling numpy arrays correctly.
        """
        if self.is_processing:
            logger.debug("Export request ignored, processing in progress")
            return
        self.is_processing = True
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.ui.pushButton.setEnabled(False)
        self.ui.pushButton.setText("Exporting...")
        QApplication.processEvents()

        try:
            obs_name = self.ui.comboBoxObservation.currentData()
            vis_type = self.ui.tabWidget.tabText(self.ui.tabWidget.currentIndex())

            if not obs_name or not vis_type:
                logger.warning("No observation or visualization tab selected for export")
                QMessageBox.warning(self, "Warning", "Please select an observation and open a visualization tab.")
                return

            tab_widget = self.ui.tabWidget.currentWidget()
            if not tab_widget:
                logger.error("No active visualization tab found")
                QMessageBox.critical(self, "Error", "No active visualization tab found.")
                return

            visualization_map = {
                "UV Coverage": "uv_coverage",
                "Sun Angles": "sun_angles",
                "Az/El or HA/Dec": "az_el",
                "Time on Source": "time_on_source",
                "Beam Pattern": "beam_pattern",
                "Baseline Projections": "baseline_projections",
                "Mollweide Tracks": "mollweide_tracks"
            }
            data_key = visualization_map.get(vis_type)
            if not data_key:
                logger.error(f"Invalid visualization type for export: {vis_type}")
                QMessageBox.critical(self, "Error", f"Invalid visualization type: {vis_type}")
                return

            calc_data = self.cached_calc_data.get(obs_name, {}).get(data_key, {})
            times_data = self.cached_calc_data.get(obs_name, {}).get("times", {})
            if not calc_data:
                logger.error(f"No cached data available for {data_key} in observation '{obs_name}'")
                QMessageBox.critical(self, "Error", f"No data available for {vis_type}.")
                return
            if not times_data and vis_type != "Beam Pattern":
                logger.error(f"No cached times data available for observation '{obs_name}'")
                QMessageBox.critical(self, "Error", f"No times data available for {vis_type}.")
                return

            filters = {}
            if vis_type in ["UV Coverage", "Baseline Projections"]:
                filters["source_name"] = tab_widget.get_selected_source()
                filters["scans"] = tab_widget.get_selected_scans()
                filters["baselines"] = tab_widget.get_selected_baselines()
                filters["frequencies"] = tab_widget.get_selected_frequencies()
                filters["units"] = tab_widget.get_selected_units()
            elif vis_type in ["Sun Angles", "Az/El or HA/Dec", "Time on Source"]:
                filters["source_name"] = tab_widget.get_selected_source()
                filters["scans"] = tab_widget.get_selected_scans()
                filters["telescopes"] = tab_widget.get_selected_telescopes()
            elif vis_type == "Beam Pattern":
                filters["telescopes"] = tab_widget.get_selected_telescopes()
                filters["frequencies"] = tab_widget.get_selected_frequencies()
            elif vis_type == "Mollweide Tracks":
                filters["sources"] = tab_widget.get_selected_sources()
                filters["scans"] = tab_widget.get_selected_scans()
                filters["telescopes"] = tab_widget.get_selected_telescopes()

            required_filters = {
                "UV Coverage": ["source_name", "scans", "baselines", "frequencies", "units"],
                "Baseline Projections": ["source_name", "scans", "baselines", "frequencies", "units"],
                "Sun Angles": ["source_name", "scans", "telescopes"],
                "Az/El or HA/Dec": ["source_name", "scans", "telescopes"],
                "Time on Source": ["source_name", "scans", "telescopes"],
                "Beam Pattern": ["telescopes", "frequencies"],
                "Mollweide Tracks": ["sources", "scans", "telescopes"]
            }
            missing_filters = [f for f in required_filters.get(vis_type, []) if not filters.get(f)]
            if missing_filters:
                logger.warning(f"Missing filters for export: {missing_filters}")
                QMessageBox.warning(self, "Warning", f"Missing filters: {', '.join(missing_filters)}")
                return

            table_data = []
            headers = []

            SPEED_OF_LIGHT = 299792458.0  # m/s
            EARTH_DIAMETER = 12742000.0   # m

            if vis_type == "UV Coverage":
                source_name = filters["source_name"]
                scans = filters["scans"]
                baselines = filters["baselines"]
                frequencies = [float(f) for f in filters["frequencies"] if isinstance(f, (int, float)) and f > 0]
                units = filters["units"]
                if not frequencies:
                    logger.warning("No valid frequencies provided for export")
                    QMessageBox.warning(self, "Warning", "No valid frequencies provided.")
                    return
                ref_freq = min(frequencies)
                ref_wavelength = SPEED_OF_LIGHT / (ref_freq * 1e6)

                filtered_data, filtered_times, scan_list = self._filter_data(calc_data, times_data, source_name, scans, None)
                if not filtered_data or not filtered_times:
                    logger.warning(f"No data after filtering for {vis_type}")
                    QMessageBox.warning(self, "Warning", f"No data available after filtering for {vis_type}.")
                    return

                headers = ["Source", "Time (UTC)", "Baseline", "Frequency (MHz)", f"U ({units})", f"V ({units})"]
                all_data = {pair: [] for pair in baselines}

                for source in filtered_data:
                    if source != source_name:
                        continue
                    source_data = filtered_data[source]
                    source_times = filtered_times[source]
                    for scan in scan_list:
                        if scan not in source_data or scan not in source_times:
                            logger.debug(f"Scan {scan} not found in source {source}, skipping")
                            continue
                        times = [t for t in source_times[scan] if hasattr(t, 'mjd')]
                        if not times:
                            logger.debug(f"No valid times for scan {scan} in source {source}, skipping")
                            continue
                        times_isot = [t.isot for t in times]
                        for baseline in baselines:
                            uv_points = source_data.get(scan, {}).get(baseline, None)
                            if uv_points is None or not isinstance(uv_points, np.ndarray) or uv_points.size == 0 or uv_points.shape[-1] < 2:
                                logger.debug(f"No valid UV points for baseline {baseline} in scan {scan}")
                                continue
                            if uv_points.shape[0] != len(times):
                                logger.warning(f"Mismatch in uv_points ({uv_points.shape[0]}) and times ({len(times)}) for {baseline} in scan {scan}")
                                min_len = min(uv_points.shape[0], len(times))
                                uv_points = uv_points[:min_len]
                                times_isot = times_isot[:min_len]
                            for t, pt in zip(times_isot, uv_points):
                                all_data[baseline].append((t, pt[0], pt[1]))

                for baseline in baselines:
                    if not all_data[baseline]:
                        logger.debug(f"No data for baseline {baseline}, skipping")
                        continue
                    times_isot, u_coords, v_coords = zip(*all_data[baseline]) if all_data[baseline] else ([], [], [])
                    times_isot = np.array(times_isot)
                    u_coords = np.array(u_coords, dtype=float)
                    v_coords = np.array(v_coords, dtype=float)
                    if len(times_isot) == 0 or len(u_coords) == 0 or len(v_coords) == 0:
                        logger.debug(f"No valid data for baseline {baseline} after combining, skipping")
                        continue
                    times_mjd = np.array([Time(t).mjd for t in times_isot])
                    time_indices = np.argsort(times_mjd)
                    times_isot = times_isot[time_indices]
                    u_coords = u_coords[time_indices]
                    v_coords = v_coords[time_indices]
                    valid_mask = ~(np.isnan(u_coords) | np.isnan(v_coords))
                    if not np.any(valid_mask):
                        logger.debug(f"All UV points for baseline {baseline} are NaN, skipping")
                        continue
                    times_isot = times_isot[valid_mask]
                    u_coords = u_coords[valid_mask]
                    v_coords = v_coords[valid_mask]
                    if len(times_isot) != len(u_coords) or len(u_coords) != len(v_coords):
                        logger.error(f"After filtering, times ({len(times_isot)}), u ({len(u_coords)}), v ({len(v_coords)}) lengths mismatch for baseline {baseline}")
                        continue

                    for freq_mhz in frequencies:
                        wavelength = SPEED_OF_LIGHT / (freq_mhz * 1e6)
                        u_scaled = u_coords.copy()
                        v_scaled = v_coords.copy()
                        if units == "wavelengths":
                            u_scaled = u_scaled / wavelength
                            v_scaled = v_scaled / wavelength
                        else:
                            u_scaled = (u_scaled / wavelength) / (EARTH_DIAMETER / ref_wavelength)
                            v_scaled = (v_scaled / wavelength) / (EARTH_DIAMETER / ref_wavelength)
                        valid_mask = ~(np.isnan(u_scaled) | np.isnan(v_scaled))
                        if not np.any(valid_mask):
                            logger.debug(f"All scaled UV points for baseline {baseline} at {freq_mhz:.2f} MHz are NaN, skipping")
                            continue
                        valid_times_isot = times_isot[valid_mask]
                        valid_u_scaled = u_scaled[valid_mask]
                        valid_v_scaled = v_scaled[valid_mask]
                        if len(valid_times_isot) != len(valid_u_scaled) or len(valid_u_scaled) != len(valid_v_scaled):
                            logger.error(f"After scaling, times ({len(valid_times_isot)}), u ({len(valid_u_scaled)}), v ({len(valid_v_scaled)}) lengths mismatch for baseline {baseline} at {freq_mhz:.2f} MHz")
                            continue
                        for t, u, v in zip(valid_times_isot, valid_u_scaled, valid_v_scaled):
                            table_data.append([
                                source_name, t, baseline, f"{freq_mhz:.2f}", f"{u:.6f}", f"{v:.6f}"
                            ])
                            table_data.append([
                                source_name, t, baseline, f"{freq_mhz:.2f}", f"{-u:.6f}", f"{-v:.6f}"
                            ])
                        logger.debug(f"Exported {len(valid_times_isot)} points (with conjugates) for baseline {baseline} at {freq_mhz:.2f} MHz")

            elif vis_type == "Baseline Projections":
                source_name = filters["source_name"]
                scans = filters["scans"]
                baselines = filters["baselines"]
                frequencies = [float(f) for f in filters["frequencies"] if isinstance(f, (int, float)) and f > 0]
                units = filters["units"]
                if not frequencies:
                    logger.warning("No valid frequencies provided for export")
                    QMessageBox.warning(self, "Warning", "No valid frequencies provided.")
                    return
                ref_freq = min(frequencies)
                ref_wavelength = SPEED_OF_LIGHT / (ref_freq * 1e6)

                filtered_data, filtered_times, scan_list = self._filter_data(calc_data, times_data, source_name, scans, None)
                if not filtered_data or not filtered_times:
                    logger.warning(f"No data after filtering for {vis_type}")
                    QMessageBox.warning(self, "Warning", f"No data available after filtering for {vis_type}.")
                    return

                headers = ["Source", "Time (UTC)", "Baseline", "Frequency (MHz)", f"Projection ({units})"]
                all_data = {pair: [] for pair in baselines}

                for source in filtered_data:
                    if source != source_name:
                        continue
                    source_data = filtered_data[source]
                    source_times = filtered_times[source]
                    for scan in scan_list:
                        if scan not in source_data or scan not in source_times:
                            logger.debug(f"Scan {scan} not found in source {source}, skipping")
                            continue
                        times = [t for t in source_times[scan] if hasattr(t, 'mjd')]
                        if not times:
                            logger.debug(f"No valid times for scan {scan} in source {source}, skipping")
                            continue
                        times_isot = [t.isot for t in times]
                        for baseline in baselines:
                            projs = source_data.get(scan, {}).get(baseline, None)
                            if projs is None or not isinstance(projs, np.ndarray) or projs.size == 0:
                                logger.debug(f"No valid projections for baseline {baseline} in scan {scan}")
                                continue
                            if projs.shape[0] != len(times):
                                logger.warning(f"Mismatch in projections ({projs.shape[0]}) and times ({len(times)}) for {baseline} in scan {scan}")
                                min_len = min(projs.shape[0], len(times))
                                projs = projs[:min_len]
                                times_isot = times_isot[:min_len]
                            for t, proj in zip(times_isot, projs):
                                all_data[baseline].append((t, proj))

                for baseline in baselines:
                    if not all_data[baseline]:
                        logger.debug(f"No data for baseline {baseline}, skipping")
                        continue
                    times_isot, projections = zip(*all_data[baseline]) if all_data[baseline] else ([], [])
                    times_isot = np.array(times_isot)
                    projections = np.array(projections, dtype=float)
                    if len(times_isot) == 0 or len(projections) == 0:
                        logger.debug(f"No valid data for baseline {baseline} after combining, skipping")
                        continue
                    times_mjd = np.array([Time(t).mjd for t in times_isot])
                    time_indices = np.argsort(times_mjd)
                    times_isot = times_isot[time_indices]
                    projections = projections[time_indices]
                    valid_mask = ~np.isnan(projections)
                    if not np.any(valid_mask):
                        logger.debug(f"All projections for baseline {baseline} are NaN, skipping")
                        continue
                    times_isot = times_isot[valid_mask]
                    projections = projections[valid_mask]
                    if len(times_isot) != len(projections):
                        logger.error(f"After filtering, times ({len(times_isot)}) and projections ({len(projections)}) lengths mismatch for baseline {baseline}")
                        continue

                    for freq_mhz in frequencies:
                        wavelength = SPEED_OF_LIGHT / (freq_mhz * 1e6)
                        proj_scaled = projections.copy()
                        if units == "wavelengths":
                            proj_scaled = proj_scaled / wavelength
                        else:
                            proj_scaled = (proj_scaled / wavelength) / (EARTH_DIAMETER / ref_wavelength)
                        valid_mask = ~np.isnan(proj_scaled)
                        if not np.any(valid_mask):
                            logger.debug(f"All scaled projections for baseline {baseline} at {freq_mhz:.2f} MHz are NaN, skipping")
                            continue
                        valid_times_isot = times_isot[valid_mask]
                        valid_proj_scaled = proj_scaled[valid_mask]
                        if len(valid_times_isot) != len(valid_proj_scaled):
                            logger.error(f"After scaling, times ({len(valid_times_isot)}) and projections ({len(valid_proj_scaled)}) lengths mismatch for baseline {baseline} at {freq_mhz:.2f} MHz")
                            continue
                        for t, proj in zip(valid_times_isot, valid_proj_scaled):
                            table_data.append([
                                source_name, t, baseline, f"{freq_mhz:.2f}", f"{proj:.6f}"
                            ])
                            logger.debug(f"Exported {len(valid_times_isot)} points for baseline {baseline} at {freq_mhz:.2f} MHz")

            elif vis_type == "Sun Angles":
                source_name = filters["source_name"]
                scans = filters["scans"]
                telescopes = filters["telescopes"]
                filtered_data, filtered_times, scan_list = self._filter_data(calc_data, times_data, source_name, scans, None)
                if not filtered_data or not filtered_times:
                    logger.warning(f"No data after filtering for {vis_type}")
                    QMessageBox.warning(self, "Warning", f"No data available after filtering for {vis_type}.")
                    return

                headers = ["Source", "Time (UTC)", "Telescope", "Sun Angle (deg)"]
                for source in filtered_data:
                    if source != source_name:
                        continue
                    source_data = filtered_data[source]
                    source_times = filtered_times[source]
                    for scan in scan_list:
                        if scan not in source_data or scan not in source_times:
                            continue
                        times = [t.isot for t in source_times[scan] if hasattr(t, 'mjd')]
                        for tel in telescopes:
                            angles = source_data.get(scan, {}).get(tel, None)
                            if angles is None or not isinstance(angles, np.ndarray) or angles.size == 0:
                                continue
                            if angles.shape[0] != len(times):
                                logger.warning(f"Mismatch in angles ({angles.shape[0]}) and times ({len(times)}) for {tel} in scan {scan}")
                                continue
                            for t, angle in zip(times, angles):
                                if np.isnan(angle):
                                    continue
                                table_data.append([
                                    source, t, tel, f"{float(angle):.6f}"
                                ])

            elif vis_type == "Az/El or HA/Dec":
                source_name = filters["source_name"]
                scans = filters["scans"]
                telescopes = filters["telescopes"]
                filtered_data, filtered_times, scan_list = self._filter_data(calc_data, times_data, source_name, scans, None)
                if not filtered_data or not filtered_times:
                    logger.warning(f"No data after filtering for {vis_type}")
                    QMessageBox.warning(self, "Warning", f"No data available after filtering for {vis_type}.")
                    return

                headers = ["Source", "Time (UTC)", "Telescope", "Azimuth (deg)", "Elevation (deg)"]
                for source in filtered_data:
                    if source != source_name:
                        continue
                    source_data = filtered_data[source]
                    source_times = filtered_times[source]
                    for scan in scan_list:
                        if scan not in source_data or scan not in source_times:
                            continue
                        times = [t.isot for t in source_times[scan] if hasattr(t, 'mjd')]
                        for tel in telescopes:
                            az_el = source_data.get(scan, {}).get(tel, None)
                            if az_el is None or not isinstance(az_el, np.ndarray) or az_el.size == 0:
                                continue
                            if az_el.shape[0] != len(times) or az_el.shape[1] < 2:
                                logger.warning(f"Invalid az_el shape {az_el.shape} for {tel} in scan {scan}")
                                continue
                            for t, ae in zip(times, az_el):
                                if np.any(np.isnan(ae)):
                                    continue
                                az, el = float(ae[0]), float(ae[1])
                                table_data.append([
                                    source, t, tel, f"{az:.6f}", f"{el:.6f}"
                                ])

            elif vis_type == "Time on Source":
                source_name = filters["source_name"]
                scans = filters["scans"]
                telescopes = filters["telescopes"]
                filtered_data, filtered_times, scan_list = self._filter_data(calc_data, times_data, source_name, scans, None)
                if not filtered_data or not filtered_times:
                    logger.warning(f"No data after filtering for {vis_type}")
                    QMessageBox.warning(self, "Warning", f"No data available after filtering for {vis_type}.")
                    return

                headers = ["Source", "Telescope", "Start (UTC)", "End (UTC)", "Duration (s)"]
                for source in filtered_data:
                    if source != source_name:
                        continue
                    source_data = filtered_data[source]
                    for scan in scan_list:
                        if scan not in source_data:
                            continue
                        for tel in telescopes:
                            blocks = source_data.get(scan, {}).get(tel, None)
                            if blocks is None or not isinstance(blocks, np.ndarray) or blocks.size == 0:
                                continue
                            for block in blocks:
                                try:
                                    start_mjd = Time(block[0]).isot if not isinstance(block[0], (int, float)) else Time(block[0], format='mjd').isot
                                    end_mjd = Time(block[1]).isot if not isinstance(block[1], (int, float)) else Time(block[1], format='mjd').isot
                                    duration = float(block[2])
                                    table_data.append([
                                        source, tel, start_mjd, end_mjd, f"{duration:.6f}"
                                    ])
                                except (ValueError, TypeError) as e:
                                    logger.error(f"Invalid block format for {tel} in scan {scan}: {str(e)}")
                                    continue

            elif vis_type == "Beam Pattern":
                telescopes = filters["telescopes"]
                frequencies = [float(f) for f in filters["frequencies"] if isinstance(f, (int, float)) and f > 0]
                if not frequencies:
                    logger.warning("No valid frequencies provided for export")
                    QMessageBox.warning(self, "Warning", "No valid frequencies provided.")
                    return
                ref_freq = min(frequencies)
                ref_wavelength = SPEED_OF_LIGHT / (ref_freq * 1e6)

                headers = ["Telescope", "Frequency (MHz)", "Angle (arcsec)", "Power (dB)"]
                beam_data = calc_data.get("data", {})
                for tel in telescopes:
                    beam = beam_data.get(tel, {})
                    theta = np.array(beam.get("theta", []), dtype=float)
                    pattern = np.array(beam.get("pattern", []), dtype=float)
                    if theta.size == 0 or pattern.size == 0 or len(theta) != len(pattern):
                        logger.warning(f"Invalid beam data for {tel}: theta={theta.size}, pattern={pattern.size}")
                        continue
                    for freq_mhz in frequencies:
                        wavelength = SPEED_OF_LIGHT / (freq_mhz * 1e6)
                        theta_scaling_factor = ref_wavelength / wavelength
                        scaled_theta = theta * theta_scaling_factor
                        scaled_pattern = pattern / np.max(np.abs(pattern)) if np.max(np.abs(pattern)) > 0 else pattern
                        for t, p in zip(scaled_theta, scaled_pattern):
                            table_data.append([
                                tel, f"{freq_mhz:.2f}", f"{t * 3600:.6f}", f"{p:.6f}"
                            ])

            elif vis_type == "Mollweide Tracks":
                scans = filters["scans"]
                telescopes = filters["telescopes"]
                sources = filters["sources"]
                headers = ["Time (UTC)", "Telescope", "Longitude (deg)", "Latitude (deg)"]
                scan_data = calc_data.get("data", {})
                metadata = calc_data.get("metadata", {}).get("sources", {})
                times_data_full = times_data.get("data", {})

                table_data.append(metadata)

                if not scan_data or not metadata:
                    logger.warning(f"No data or metadata available for {vis_type}")
                    QMessageBox.warning(self, "Warning", f"No data available for {vis_type}.")
                    return

                for source in sources:
                    if source not in metadata:
                        logger.warning(f"Source {source} not found in metadata")
                        continue
                    source_times = times_data_full.get(source, {})
                    for scan in scans:
                        if scan not in scan_data or scan not in source_times:
                            continue
                        times = [t.isot for t in source_times.get(scan, []) if hasattr(t, 'mjd')]
                        for tel in telescopes:
                            tracks = scan_data.get(scan, {}).get(tel, None)
                            if tracks is None or not isinstance(tracks, np.ndarray) or tracks.size == 0 or tracks.ndim != 2 or tracks.shape[1] != 2:
                                continue
                            if len(times) != tracks.shape[0]:
                                min_len = min(len(times), tracks.shape[0])
                                times = times[:min_len]
                                tracks = tracks[:min_len]
                            for t, (lon, lat) in zip(times, tracks):
                                if np.any(np.isnan([lon, lat])):
                                    continue
                                table_data.append([
                                    t, tel, f"{lon:.6f}", f"{lat:.6f}"
                                ])

            if not table_data:
                logger.warning(f"No data to export for {vis_type}")
                QMessageBox.warning(self, "Warning", f"No data available to export for {vis_type}.")
                return

            file_name, _ = QFileDialog.getSaveFileName(
                self, "Export Calculated Data", "", "Text Files (*.txt);;All Files (*)"
            )
            if not file_name:
                logger.debug("Export cancelled by user")
                return

            try:
                with open(file_name, 'w', encoding='utf-8') as f:
                    f.write('\t'.join(headers) + '\n')
                    for row in table_data:
                        f.write('\t'.join(str(val) for val in row) + '\n')
                logger.info(f"Exported calculated data to {file_name}")
                QMessageBox.information(self, "Success", f"Data exported successfully to {file_name}")
            except Exception as e:
                logger.error(f"Failed to write to file {file_name}: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to export data: {str(e)}")

        finally:
            self.is_processing = False
            self.ui.pushButton.setEnabled(True)
            self.ui.pushButton.setText("Export")
            QApplication.restoreOverrideCursor()
            QApplication.processEvents()
            logger.debug("Export process completed, UI unlocked")