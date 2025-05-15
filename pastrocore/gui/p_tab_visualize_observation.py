from PySide6.QtWidgets import QWidget, QMessageBox
from PySide6.QtCore import Signal, Slot
from pastrocore.gui.ui_tab_visualize_observation import Ui_tab_visualize_observation
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_visualizer import ScheduleVisualizer
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger

class VisualizeObservationTab(QWidget):
    """Widget for visualizing observation data using ScheduleVisualizer."""
    data_updated = Signal()

    def __init__(self, observation: Observation, project: ScheduleProject, manipulator: ScheduleManipulator, parent=None):
        super().__init__(parent)
        self.ui = Ui_tab_visualize_observation()
        self.ui.setupUi(self)
        self.observation = observation
        self.project = project
        self.manipulator = manipulator
        self.visualizer = ScheduleVisualizer(manipulator)
        self._updating = False

        # Подключение сигналов
        self.ui.btn_visualize.clicked.connect(self.on_visualize_clicked)
        self.ui.combo_plot_type.currentTextChanged.connect(self.on_plot_type_changed)

        # Обновление списка частот
        self.update_frequencies()
        self.on_plot_type_changed(self.ui.combo_plot_type.currentText())

    @Slot()
    def update(self):
        """Update the visualization tab with current observation data."""
        if self._updating:
            logger.debug(f"Skipping update for visualization tab of observation '{self.observation.get_observation_code()}' as it is already updating")
            return
        self._updating = True
        try:
            # Проверка существования наблюдения
            obs_code_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation,
                "attributes": {"get_observation_code": None}
            })
            if not obs_code_response["status"]:
                logger.error(f"Failed to get observation code: {obs_code_response.get('error', 'Unknown error')}")
                self.close_tab()
                return
            obs_code = obs_code_response["result"]

            obs_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.project,
                "attributes": {"get_observation_by_code": obs_code}
            })
            if not obs_response["status"] or not obs_response["result"]:
                logger.info(f"Observation '{obs_code}' no longer exists, closing visualization tab")
                self.close_tab()
                return

            # Обновление списка частот
            self.update_frequencies()

            logger.info(f"Visualization tab updated for observation '{obs_code}'")
        except Exception as e:
            logger.error(f"Error updating visualization tab for observation '{obs_code}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to update visualization tab: {str(e)}")
        finally:
            self._updating = False

    def update_frequencies(self):
        """Update the frequency combo box with available IFs."""
        self.ui.combo_freq.clear()
        frequencies_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_frequencies": None}
        })
        if frequencies_response["status"] and frequencies_response["result"]:
            items_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": frequencies_response["result"],
                "attributes": {"get_all": None}
            })
            if items_response["status"] and isinstance(items_response["result"], dict):
                for name, if_obj in items_response["result"].items():
                    is_active_response = self.manipulator.process_request({
                        "operation": "inspect",
                        "obj": if_obj,
                        "attributes": {"get": "isactive"}
                    })
                    if is_active_response["status"] and is_active_response["result"]:
                        self.ui.combo_freq.addItem(name)
        self.ui.combo_freq.setEnabled(self.ui.combo_freq.count() > 0 and self.is_frequency_required())

    @Slot(str)
    def on_plot_type_changed(self, text: str):
        """Handle plot type selection change."""
        self.ui.combo_freq.setEnabled(self.is_frequency_required())
        self.ui.lbl_status.setText("Status: Ready")

    def is_frequency_required(self):
        """Check if the selected plot type requires a frequency selection."""
        plot_type = self.ui.combo_plot_type.currentText()
        freq_required_plots = ["UV Coverage", "Beam Pattern", "Synthesized Beam", "Baseline Projections"]
        return plot_type in freq_required_plots

    @Slot()
    def on_visualize_clicked(self):
        """Handle visualize button click."""
        plot_type = self.ui.combo_plot_type.currentText()
        freq_name = self.ui.combo_freq.currentText() if self.is_frequency_required() else None

        # Маппинг отображаемых названий на ключи ScheduleVisualizer
        plot_type_mapping = {
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

        if not plot_type:
            self.ui.lbl_status.setText("Status: Error - No plot type selected")
            QMessageBox.critical(self, "Error", "Please select a visualization type.")
            return

        if self.is_frequency_required() and not freq_name:
            self.ui.lbl_status.setText("Status: Error - No frequency selected")
            QMessageBox.critical(self, "Error", "Please select a frequency for this visualization.")
            return

        try:
            attributes = {
                "plot_type": plot_type_mapping[plot_type],
                "show": True,
                "output_file": None,
                "freq_name": freq_name
            }
            request = {
                "operation": "visualize",
                "obj": self.observation,
                "attributes": attributes
            }
            response = self.manipulator.process_request(request)
            if response["status"] == "success":
                logger.info(f"Visualization '{plot_type}' completed for observation '{self.observation.get_observation_code()}'")
                self.ui.lbl_status.setText(f"Status: Success - {response.get('baselines', response.get('scans', 'Plot displayed'))}")
            else:
                error_msg = response.get("message", "Unknown error")
                logger.error(f"Visualization failed: {error_msg}")
                self.ui.lbl_status.setText(f"Status: Error - {error_msg}")
                QMessageBox.critical(self, "Error", f"Visualization failed: {error_msg}")
        except Exception as e:
            logger.error(f"Exception during visualization: {str(e)}")
            self.ui.lbl_status.setText(f"Status: Error - {str(e)}")
            QMessageBox.critical(self, "Error", f"Visualization failed: {str(e)}")

    def close_tab(self):
        """Close the visualization tab."""
        parent_tab_container = self.parentWidget().parentWidget().parentWidget().ui.tabContainer
        for i in range(parent_tab_container.count()):
            if parent_tab_container.widget(i) == self.parentWidget().parentWidget():
                parent_tab_container.removeTab(i)
                break
        logger.info(f"Closed visualization tab for observation '{self.observation.get_observation_code()}'")