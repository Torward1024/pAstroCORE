# p_dialog_calculations.py
from PySide6.QtWidgets import QDialog, QListWidgetItem, QProgressDialog, QMessageBox
from PySide6.QtCore import Qt, QThread, Signal
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
from pastrocore.gui.ui_dialog_calculations import Ui_CalculationDialog
import pastrocore.gui.rc_icons

class CalculationThread(QThread):
    """Thread for performing calculations asynchronously."""
    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, manipulator, targets, calc_types, params):
        super().__init__()
        self.manipulator = manipulator
        self.targets = targets
        self.calc_types = calc_types
        self.params = params

    def run(self):
        """Execute calculations asynchronously and emit progress signals."""
        try:
            results = {}
            freq_dependent_calcs = ["Beam Pattern", "Synthesized Beam"]
            total = sum(len(target.frequencies.get_active_items()) if calc_type in freq_dependent_calcs else 1
                        for target in self.targets for calc_type in self.calc_types)
            current = 0
            for target in self.targets:
                freqs = [f.name for f in target.frequencies.get_active_items()] if isinstance(target, Observation) else [None]
                for calc_type in self.calc_types:
                    calc_params = self.params.get(calc_type, {}).copy()
                    time_step = calc_params.get("time_step", 600)
                    logger.debug(f"Time step for {calc_type} on {target.code} set to '{time_step}'")
                    # Map dialog calc types to calculator methods
                    method_map = {
                        "UV Coverage": "uv_coverage",
                        "Mollweide Tracks": "mollweide_tracks",
                        "Baseline Projections": "baseline_projections",
                        "Time on Source": "time_on_source",
                        "Sun Angles": "sun_angles",
                        "Azimuth/Elevation": "az_el"
                    }
                    method = method_map.get(calc_type, calc_type.lower().replace(" ", "_"))
                    # Process frequency-dependent calculations
                    if calc_type in freq_dependent_calcs:
                        for freq in freqs:
                            freq_params = calc_params.copy()
                            freq_params["freq_name"] = freq
                            freq_params["store_key"] = f"{method}_{freq}"
                            freq_params["time_step"] = time_step
                            request = {
                                "operation": "calculate",
                                "attributes": {
                                    "method": method,
                                    **freq_params
                                },
                                "obj": target
                            }
                            logger.debug(f"Executing calculation request for {calc_type} on {target.code} at {freq} with params: {freq_params}")
                            result = self.manipulator.process_request(request)
                            if not result.get("status", False):
                                raise ValueError(f"Calculation {calc_type} failed for {target.code} at {freq}: {result.get('message', 'Unknown error')}")
                            results[f"{target.code}_{calc_type}_{freq}"] = result["result"]
                            current += 1
                            self.progress.emit(int(current / total * 100), f"Calculating {calc_type} for {target.code} at {freq}")
                    else:
                        calc_params["store_key"] = f"{method}"
                        calc_params["time_step"] = time_step
                        request = {
                            "operation": "calculate",
                            "attributes": {
                                "method": method,
                                **calc_params
                            },
                            "obj": target
                        }
                        logger.debug(f"Executing calculation request for {calc_type} on {target.code} with params: {calc_params}")
                        result = self.manipulator.process_request(request)
                        if not result.get("status", False):
                            raise ValueError(f"Calculation {calc_type} failed for {target.code}: {result.get('message', 'Unknown error')}")
                        results[f"{target.code}_{calc_type}"] = result["result"]
                        current += 1
                        self.progress.emit(int(current / total * 100), f"Calculating {calc_type} for {target.code}")
            self.finished.emit(results)
        except Exception as e:
            logger.error(f"Calculation error in thread: {str(e)}")
            self.error.emit(str(e))

class CalculationDialog(QDialog):
    """Dialog for configuring and running multiple calculations."""
    time_step_updated = Signal(int)  # Новый сигнал для обновления time_step

    def __init__(self, manipulator, project, targets=None, calc_type=None, time_step=600, parent=None):
        super().__init__(parent)
        self.ui = Ui_CalculationDialog()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self.project = project
        self.targets = targets or []
        self.calc_type = calc_type
        self.time_step = time_step
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Initialize the dialog UI."""
        self.populate_calc_list()
        self.populate_targets()
        self.ui.calcList.itemChanged.connect(self.handle_calc_selection)
        self.ui.selectAllCalcButton.clicked.connect(self.select_all_calcs)
        self.ui.clearAllCalcButton.clicked.connect(self.clear_all_calcs)
        self.ui.selectAllObsButton.clicked.connect(self.select_all_targets)
        self.ui.clearAllObsButton.clicked.connect(self.clear_all_targets)
        self.ui.calcButton.clicked.connect(self.run_calculation)
        self.ui.cancelButton.clicked.connect(self.reject)

    def populate_calc_list(self):
        """Populate the calculation list with available calculations."""
        calc_types = [
            "UV Coverage",
            "Mollweide Tracks",
            "Baseline Projections",
            "Time on Source",
            "Sun Angles",
            "Azimuth/Elevation"
        ]
        dependencies = {
            "Synthesized Beam": ["UV Coverage"],
            "Baseline Projections": ["UV Coverage"]
        }
        self.ui.calcList.clear()
        for calc_type in calc_types:
            item = QListWidgetItem(calc_type)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            item.setData(Qt.UserRole, dependencies.get(calc_type, []))
            self.ui.calcList.addItem(item)
        logger.debug(f"Populated {self.ui.calcList.count()} calculations, all checked.")

    def populate_targets(self):
        """Populate the target list with project observations using observation code."""
        observations_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.project,
            "attributes": {"get_items": None}
        })
        self.ui.targetList.clear()
        if observations_response["status"]:
            if not observations_response["result"]:
                logger.warning("No observations found in the project.")
                return
            for _, obs in observations_response["result"].items():
                item = QListWidgetItem(obs.code)
                item.setData(Qt.UserRole, obs)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                self.ui.targetList.addItem(item)
            logger.debug(f"Populated {self.ui.targetList.count()} observations, all checked.")
        else:
            logger.error(f"Failed to retrieve observations: {observations_response.get('message', 'Unknown error')}")
            QMessageBox.critical(self, "Error", "Failed to load observations. Please check the project data.")

    def select_all_calcs(self):
        """Select all calculations in the list."""
        for i in range(self.ui.calcList.count()):
            self.ui.calcList.item(i).setCheckState(Qt.Checked)
        logger.debug("All calculations selected.")

    def clear_all_calcs(self):
        """Clear all calculation selections."""
        for i in range(self.ui.calcList.count()):
            self.ui.calcList.item(i).setCheckState(Qt.Unchecked)
        logger.debug("All calculation selections cleared.")

    def select_all_targets(self):
        """Select all targets in the list."""
        for i in range(self.ui.targetList.count()):
            self.ui.targetList.item(i).setCheckState(Qt.Checked)
        logger.debug("All targets selected.")

    def clear_all_targets(self):
        """Clear all target selections."""
        for i in range(self.ui.targetList.count()):
            self.ui.targetList.item(i).setCheckState(Qt.Unchecked)
        logger.debug("All target selections cleared.")

    def handle_calc_selection(self, item):
        """Handle changes in calculation selection, including dependencies."""
        if item.checkState() != Qt.Checked:
            return
        dependencies = item.data(Qt.UserRole)
        if not dependencies:
            return
        calc_type = item.text()
        logger.debug(f"Handling dependencies for {calc_type}: {dependencies}")
        for dep in dependencies:
            for i in range(self.ui.calcList.count()):
                if self.ui.calcList.item(i).text() == dep:
                    self.ui.calcList.item(i).setCheckState(Qt.Checked)
                    logger.debug(f"Enabled dependency: {dep}")
                    break
        self.update_params_ui()

    def update_params_ui(self):
        """Update the parameters UI based on selected calculations."""
        selected_calcs = [self.ui.calcList.item(i).text() for i in range(self.ui.calcList.count())
                          if self.ui.calcList.item(i).checkState() == Qt.Checked]
        self.ui.timeStepSpin.setEnabled("Beam Pattern" not in selected_calcs)
        logger.debug(f"Updated params UI, timeStepSpin enabled: {'Beam Pattern' not in selected_calcs}")

    def run_calculation(self):
        """Run the selected calculations in a separate thread."""
        selected_calcs = [self.ui.calcList.item(i).text() for i in range(self.ui.calcList.count())
                          if self.ui.calcList.item(i).checkState() == Qt.Checked]
        selected_targets = [self.ui.targetList.item(i).data(Qt.UserRole) for i in range(self.ui.targetList.count())
                            if self.ui.targetList.item(i).checkState() == Qt.Checked]
        if not selected_calcs or not selected_targets:
            QMessageBox.warning(self, "Warning", "Please select at least one calculation and one target.")
            return
        
        # Clear cache for all selected targets if recalculate is checked
        if self.ui.recalculateCheck.isChecked():
            for target in selected_targets:
                try:
                    target.clear_calculated_data()
                    logger.info(f"Cleared all cached data for '{target.get_observation_code()}'")
                except AttributeError as e:
                    logger.error(f"Failed to clear cache for '{target.get_observation_code()}': {str(e)}")
                    QMessageBox.critical(self, "Error", f"Failed to clear cache for {target.get_observation_code()}: {str(e)}")
                    return

        params = {
            "time_step": self.ui.timeStepSpin.value(),
            "recalculate": False
        }
        logger.debug(f"CalculationDialog: params set to {params}")
        calc_params = {calc: params for calc in selected_calcs}
        self.progress_dialog = QProgressDialog("Calculating...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.thread = CalculationThread(self.manipulator, selected_targets, selected_calcs, calc_params)
        self.thread.progress.connect(self.update_progress)
        self.thread.finished.connect(self.on_calculation_finished)
        self.thread.error.connect(self.on_calculation_error)
        self.thread.start()

        # Emit time_step_updated signal if time_step changed
        if self.ui.timeStepSpin.value() != self.time_step:
            self.time_step_updated.emit(self.ui.timeStepSpin.value())
            logger.debug(f"Emitted time_step_updated signal with value {self.ui.timeStepSpin.value()}")

    def update_progress(self, value, message):
        """Update the progress dialog."""
        self.progress_dialog.setValue(value)
        self.progress_dialog.setLabelText(message)
        if self.progress_dialog.wasCanceled():
            self.thread.terminate()

    def run_calculation_and_visualize(self):
        """Run calculations and open visualization dialog."""
        QMessageBox.information(self, "Info", "Visualization is not implemented yet.")
        self.run_calculation()

    def on_calculation_finished(self, results):
        """Handle calculation completion."""
        self.progress_dialog.close()
        QMessageBox.information(self, "Success", "Calculations completed successfully.")
        self.accept()

    def on_calculation_error(self, error):
        """Handle calculation errors."""
        self.progress_dialog.close()
        logger.error(f"Calculation error: {error}")
        QMessageBox.critical(self, "Error", f"Calculation failed: {error}")
        self.reject()

    def load_settings(self):
        """Load dialog-specific settings."""
        self.ui.timeStepSpin.setValue(self.time_step)
        logger.debug(f"Loaded time_step={self.time_step} into timeStepSpin")