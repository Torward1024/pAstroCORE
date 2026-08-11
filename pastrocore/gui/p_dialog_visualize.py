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
from .p_tab_vis_parallactic import ParallacticAngleVisualizationTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from pastrocore.base.data_structure import CalculatedDataStructure
from msb_arch.utils.logging_setup import logger
from typing import Dict
SPEED_OF_LIGHT = 299792458.0  # m/s

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
        self.is_processing = False

        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)

        self.setup_connections()
        self.populate_observations()

        if self.ui.comboBoxObservation.count() > 0:
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

        try:
            observations = self.manipulator.inspect(obj=self.project, get_items=None)
            if observations:
                for obs_name, obs in observations.items():
                    self.cached_observations[obs_name] = obs
                    try:
                        obs_code = self.manipulator.inspect(obj=obs, get_observation_code=None)
                        self.ui.comboBoxObservation.addItem(obs_code, obs_name)
                    except Exception as e:
                        logger.error("Failed to get code for observation '%s': %s", obs_name, str(e))
                logger.debug("Populated %s observations in comboBoxObservation", self.ui.comboBoxObservation.count())
                self.ui.comboBoxObservation.setEnabled(True)
            else:
                logger.debug("No observations found in project")
        except Exception as e:
            logger.error("Failed to retrieve observations: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to load observations: {str(e)}")

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
                self.close_tab(index)
        self.visualization_tabs.clear()
        logger.debug("All visualization tabs cleared")

    def update_visualization_types(self):
        """Update visualization types based on available calculated data keys for the selected observation."""
        self.ui.comboBoxVisualizationType.clear()
        self.ui.comboBoxVisualizationType.setEnabled(False)
        self.ui.pushButtonVisualize.setEnabled(False)

        current_obs_name = self.ui.comboBoxObservation.currentData()
        if not current_obs_name:
            logger.debug("No observation selected, visualization types cleared and disabled")
            return

        observation = self.cached_observations.get(current_obs_name)
        if not observation:
            logger.error("Observation '%s' not found in cache", current_obs_name)
            QMessageBox.critical(self, "Error", f"Failed to load observation: {current_obs_name}")
            return

        try:
            # Asked, not listed. A calculation that can be drawn appears here because the
            # visualizer has a handler for it, not because somebody added it to a table.
            described = self.manipulator.export(obj=observation, method="catalogue")
            catalogue = (described["result"] if isinstance(described, dict) and "status" in described
                         else described) or []
            vis_types = {entry["key"]: entry["label"] for entry in catalogue if entry["can_plot"]}

            # One request, counted from the parquet footers rather than by reading the frames.
            # This loop used to read *every* result to decide what to offer -- 142 ms and
            # eleven frames held in memory on a small project, to fill one combo box.
            response = self.manipulator.export(
                obj=observation, method="available", keys=list(vis_types))
            available = (response["result"] if isinstance(response, dict) and "status" in response
                         else response) or []
            available_types = [vis_types[key] for key in available if key in vis_types]
            self.ui.comboBoxVisualizationType.addItems(sorted(available_types))
            self.ui.comboBoxVisualizationType.setEnabled(bool(available_types))
            self.ui.pushButtonVisualize.setEnabled(bool(available_types))
            logger.debug("Populated visualization types: %s", available_types)
        except Exception as e:
            logger.error("Failed to retrieve calculated data keys: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to load visualization types: {str(e)}")

    @Slot(int)
    def close_tab(self, index: int):
        """Close the visualization tab at the specified index.

        Args:
            index: Index of the tab to close.
        """
        if self.is_processing:
            logger.debug("Tab close request at index %s ignored, processing in progress", index)
            return

        self.is_processing = True
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            tab_widget = self.ui.tabWidget.widget(index)
            if not tab_widget:
                logger.warning("No widget found at tab index %s", index)
                return

            vis_type = tab_widget.property("vis_type")
            if not vis_type:
                logger.warning("No visualization type defined for tab at index %s", index)
            else:
                logger.debug("Closing tab '%s' at index %s", vis_type, index)

            if hasattr(tab_widget, '_clear_canvas'):
                try:
                    tab_widget._clear_canvas()
                    logger.debug("Canvas cleared for tab '%s'", vis_type)
                except Exception as e:
                    logger.error("Failed to clear canvas for tab '%s': %s", vis_type, str(e))

            self.ui.tabWidget.removeTab(index)
            tab_widget.deleteLater()
            logger.debug("Tab widget at index %s removed and scheduled for deletion", index)

            if vis_type in self.visualization_tabs:
                del self.visualization_tabs[vis_type]
                logger.debug("Removed '%s' from visualization_tabs", vis_type)
        except Exception as e:
            logger.error("Failed to close tab at index %s: %s", index, str(e))
            QMessageBox.critical(self, "Error", f"Failed to close tab: {str(e)}")
        finally:
            self.is_processing = False
            QApplication.restoreOverrideCursor()
            QApplication.processEvents()
            logger.debug("Tab close process completed, UI unlocked")

    @Slot()
    def perform_visualization(self):
        """Perform visualization for the selected observation and visualization type."""
        if self.is_processing:
            logger.debug("Visualization request ignored, processing in progress")
            return
        self.is_processing = True
        self.ui.pushButtonVisualize.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            current_obs_name = self.ui.comboBoxObservation.currentData()
            vis_type = self.ui.comboBoxVisualizationType.currentText()
            observation = self.cached_observations.get(current_obs_name)
            if not observation:
                logger.error("Observation '%s' not found", current_obs_name)
                QMessageBox.critical(self, "Error", f"Observation '{current_obs_name}' not found")
                return

            if vis_type in self.visualization_tabs:
                logger.debug("Visualization tab for '%s' already exists, setting as current", vis_type)
                for i in range(self.ui.tabWidget.count()):
                    if self.ui.tabWidget.widget(i).property("vis_type") == vis_type:
                        self.ui.tabWidget.setCurrentIndex(i)
                        break
                self.is_processing = False
                self.ui.pushButtonVisualize.setEnabled(True)
                QApplication.restoreOverrideCursor()
                return

            # Which widget draws which result: a fact about this interface, and the one thing
            # here the model cannot answer. Keyed by the result rather than by its label, so a
            # label can be reworded without silently unbinding a tab.
            tab_classes = {
                "az_el": AzElVisualizationTab,
                "sun_angles": SunAnglesVisualizationTab,
                "time_on_source": TimeOnSourceVisualizationTab,
                "uv_coverage": UVVisualizationTab,
                "baseline_projections": BaselineProjectionsVisualizationTab,
                "beam_pattern": BeamPatternVisualizationTab,
                "mollweide_tracks": MollweideVisualizationTab,
                "parallactic_angle": ParallacticAngleVisualizationTab,
            }
            tab_class = tab_classes.get(vis_key)
            if not tab_class:
                logger.error("No tab class defined for visualization type '%s'", vis_type)
                QMessageBox.critical(self, "Error", f"Visualization type '{vis_type}' not supported")
                return

            tab_widget = tab_class(self.manipulator, observation, parent=self)
            tab_widget.setProperty("vis_type", vis_type)
            self.ui.tabWidget.addTab(tab_widget, vis_type)
            self.ui.tabWidget.setCurrentWidget(tab_widget)
            self.visualization_tabs[vis_type] = tab_widget
            logger.debug("Added visualization tab for '%s'", vis_type)
        except Exception as e:
            logger.error("Failed to create visualization tab for '%s': %s", vis_type, str(e))
            QMessageBox.critical(self, "Error", f"Failed to visualize {vis_type}: {str(e)}")
        finally:
            self.is_processing = False
            self.ui.pushButtonVisualize.setEnabled(True)
            QApplication.restoreOverrideCursor()
            QApplication.processEvents()
            logger.debug("Visualization process completed, UI unlocked")

    @Slot()
    def export_calculated_data(self):
        """Export calculated data for the current observation and visualization type to a text file."""
        if self.is_processing:
            logger.debug("Export request ignored, processing in progress")
            return
        self.is_processing = True
        self.ui.pushButton.setEnabled(False)
        self.ui.pushButton.setText("Exporting...")
        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            current_obs_name = self.ui.comboBoxObservation.currentData()
            vis_type = self.ui.comboBoxVisualizationType.currentText()
            observation = self.cached_observations.get(current_obs_name)
            if not observation:
                logger.error("Observation '%s' not found", current_obs_name)
                QMessageBox.critical(self, "Error", f"Observation '{current_obs_name}' not found")
                return

            described = self.manipulator.export(obj=observation, method="catalogue")
            catalogue = (described["result"] if isinstance(described, dict) and "status" in described
                         else described) or []
            # The label a user picked and the key a request needs are two spellings of one
            # thing, and the catalogue holds both.
            vis_key = next((entry["key"] for entry in catalogue
                            if entry["label"] == vis_type and entry["can_plot"]), None)
            if not vis_key:
                logger.error("Invalid visualization type '%s'", vis_type)
                QMessageBox.critical(self, "Error", f"Invalid visualization type: {vis_type}")
                return

            # Asked before reading: this is the one place the dialog genuinely needs the rows,
            # so it checks that there are any without pulling them in first.
            response = self.manipulator.export(obj=observation, method="available",
                                               keys=[vis_key])
            available = (response["result"] if isinstance(response, dict) and "status" in response
                         else response) or []
            if vis_key not in available:
                logger.error("No valid data for visualization type '%s'", vis_type)
                QMessageBox.critical(self, "Error", f"No data available for {vis_type}")
                return

            calc_data = self.manipulator.inspect(obj=observation, get_calculated_data_by_key=vis_key)
            df = calc_data.get("data", {})

            headers = CalculatedDataStructure.get_columns(vis_key)
            if not headers:
                logger.error("No schema defined for visualization type '%s'", vis_type)
                QMessageBox.critical(self, "Error", f"No schema defined for {vis_type}")
                return
            missing_columns = [col for col in headers if col not in df.columns]
            if missing_columns:
                logger.error("DataFrame for '%s' missing required columns: %s", vis_type, missing_columns)
                QMessageBox.critical(self, "Error", f"DataFrame for {vis_type} missing columns: {missing_columns}")
                return

            if df.is_empty():
                logger.warning("No data to export for %s", vis_type)
                QMessageBox.warning(self, "Warning", f"No data available for {vis_type}")
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
                    for row in df.iter_rows(named=True):
                        row_data = [str(row[col]) for col in headers]
                        f.write('\t'.join(row_data) + '\n')
                logger.info("Exported calculated data to %s", file_name)
                QMessageBox.information(self, "Success", f"Data exported successfully to {file_name}")
            except Exception as e:
                logger.error("Failed to write to file %s: %s", file_name, str(e))
                QMessageBox.critical(self, "Error", f"Failed to export data: {str(e)}")
        finally:
            self.is_processing = False
            self.ui.pushButton.setEnabled(True)
            self.ui.pushButton.setText("Export")
            QApplication.restoreOverrideCursor()
            QApplication.processEvents()
            logger.debug("Export process completed, UI unlocked")