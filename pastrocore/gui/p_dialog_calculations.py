# p_dialog_calculations.py
from PySide6.QtWidgets import QDialog, QListWidgetItem, QMessageBox
from PySide6.QtCore import Qt, QThread, Signal
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from msb_arch.utils.logging_setup import logger
from pastrocore.gui.ui_dialog_calculations import Ui_CalculationDialog
from pastrocore.gui.ui_dialog_calc_progress import Ui_ProgressDialog

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
        self._cancelled = False
        logger.debug(f"CalculationThread initialized with calc_types: {self.calc_types}")
        valid_calcs = [
            "UV Coverage", "Mollweide Tracks", "Baseline Projections",
            "Time on Source", "Sun Angles", "Azimuth/Elevation", "Beam Pattern"
        ]
        invalid_calcs = [calc for calc in calc_types if calc not in valid_calcs]
        if invalid_calcs:
            logger.error(f"Invalid calculation types provided: {invalid_calcs}")
            raise ValueError(f"Invalid calculation types: {invalid_calcs}")

    def cancel(self):
        """Set cancellation flag to stop after current calculation."""
        self._cancelled = True
        logger.debug("CalculationThread cancellation requested")

    def run(self):
        """Execute calculations asynchronously and emit progress signals."""
        try:
            results = {}
            freq_dependent_calcs = ["Synthesized Beam"]
            total = sum(len(target.frequencies.get_active_items()) if calc_type in freq_dependent_calcs else 1
                        for target in self.targets for calc_type in self.calc_types)
            current = 0
            for target in self.targets:
                freqs = [f.name for f in target.frequencies.get_active_items()] if isinstance(target, Observation) else [None]
                for calc_type in self.calc_types:
                    if self._cancelled:
                        logger.info("Calculation cancelled by user")
                        self.error.emit("Calculation cancelled by user")
                        return
                    calc_params = self.params.get(calc_type, {}).copy()
                    time_step = calc_params.get("time_step", 600)
                    logger.debug(f"Time step for {calc_type} on {target.code} set to '{time_step}'")
                    method_map = {
                        "UV Coverage": "uv_coverage",
                        "Mollweide Tracks": "mollweide_tracks",
                        "Baseline Projections": "baseline_projections",
                        "Beam Pattern": "beam_pattern",
                        "Time on Source": "time_on_source",
                        "Sun Angles": "sun_angles",
                        "Azimuth/Elevation": "az_el"
                    }
                    method = method_map.get(calc_type, calc_type.lower().replace(" ", "_"))
                    if calc_type in freq_dependent_calcs:
                        for freq in freqs:
                            if self._cancelled:
                                logger.info("Calculation cancelled by user during frequency loop")
                                self.error.emit("Calculation cancelled by user")
                                return
                            freq_params = calc_params.copy()
                            freq_params["freq_name"] = freq
                            freq_params["store_key"] = f"{method}_{freq}"
                            freq_params["time_step"] = time_step
                            logger.debug(f"Executing calculation request for {calc_type} on {target.code} at {freq} with params: {freq_params}")
                            try:
                                result = self.manipulator.calculate(obj=target, method=method, **freq_params)
                                results[f"{target.code}_{calc_type}_{freq}"] = result
                                current += 1
                                self.progress.emit(int(current / total * 100), f"Calculating {calc_type} for {target.code} at {freq}")
                            except Exception as e:
                                raise ValueError(f"Calculation {calc_type} failed for {target.code} at {freq}: {str(e)}")
                    else:
                        calc_params["store_key"] = f"{method}"
                        calc_params["time_step"] = time_step
                        logger.debug(f"Executing calculation request for {calc_type} on {target.code} with params: {calc_params}")
                        try:
                            result = self.manipulator.calculate(obj=target, method=method, **calc_params)
                            results[f"{target.code}_{calc_type}"] = result
                            current += 1
                            self.progress.emit(int(current / total * 100), f"Calculating {calc_type} for {target.code}")
                        except Exception as e:
                            raise ValueError(f"Calculation {calc_type} failed for {target.code}: {str(e)}")
            self.finished.emit(results)
        except Exception as e:
            logger.error(f"Calculation error in thread: {str(e)}")
            self.error.emit(str(e))

class ProgressDialog(QDialog):
    """Custom progress dialog for calculation progress."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_ProgressDialog()
        self.ui.setupUi(self)
        self.setWindowTitle("Calculation Progress")
        logger.debug("ProgressDialog initialized")

    def update_progress(self, value, message):
        """Update progress bar and label."""
        self.ui.progressBar.setValue(value)
        self.ui.label.setText(message)
        logger.debug(f"ProgressDialog updated: value={value}, message={message}")

    def cancel(self):
        """Emit cancellation signal (handled by parent dialog)."""
        logger.debug("ProgressDialog cancel requested")
        self.reject()

class CalculationDialog(QDialog):
    """Dialog for configuring and running multiple calculations."""
    time_step_updated = Signal(int)

    def __init__(self, manipulator: ScheduleManipulator, targets=None, calc_type=None, time_step=600, parent=None):
        super().__init__(parent)
        self.ui = Ui_CalculationDialog()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self.project = manipulator.get_managing_object()
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
        self.ui.calcList.itemChanged.connect(self.log_calc_selection)
        self.ui.selectAllCalcButton.clicked.connect(self.select_all_calcs)
        self.ui.clearAllCalcButton.clicked.connect(self.clear_all_calcs)
        self.ui.selectAllObsButton.clicked.connect(self.select_all_targets)
        self.ui.clearAllObsButton.clicked.connect(self.clear_all_targets)
        self.ui.calcButton.clicked.connect(self.run_calculation)
        self.ui.cancelButton.clicked.connect(self.reject)
        self.ui.clrButton.clicked.connect(self.clear_selected_data)

    def log_calc_selection(self, item):
        """Log changes in calculation selection for debugging."""
        logger.debug(f"Calculation {item.text()} check state changed to: {item.checkState()}")

    def populate_calc_list(self):
        """Populate the calculation list with available calculations."""
        calc_types = [
            "UV Coverage",
            "Mollweide Tracks",
            "Baseline Projections",
            "Beam Pattern",
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
        try:
            observations = self.manipulator.inspect(obj=self.project, get_items=None)
            self.ui.targetList.clear()
            if not observations:
                logger.debug("No observations found in the project.")
                return
            for _, obs in observations.items():
                item = QListWidgetItem(obs.code)
                item.setData(Qt.UserRole, obs)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                self.ui.targetList.addItem(item)
            logger.debug(f"Populated {self.ui.targetList.count()} observations, all checked.")
        except Exception as e:
            logger.error(f"Failed to retrieve observations: {str(e)}")
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
        logger.debug(f"Selected calculations: {selected_calcs}")
        logger.debug(f"Selected targets: {[target.code for target in selected_targets]}")
        
        if not selected_calcs or not selected_targets:
            QMessageBox.warning(self, "Warning", "Please select at least one calculation and one target.")
            return

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
        calc_params = {calc: params.copy() for calc in selected_calcs}

        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.ui.pushButtonCancel.clicked.connect(self.cancel_calculation)
        self.progress_dialog.update_progress(0, "Preparing calculations...")
        self.progress_dialog.show()

        self.thread = CalculationThread(self.manipulator, selected_targets, selected_calcs, calc_params)
        self.thread.progress.connect(self.progress_dialog.update_progress)
        self.thread.finished.connect(self.calculation_finished)
        self.thread.error.connect(self.calculation_error)
        self.thread.start()

        if self.ui.timeStepSpin.value() != self.time_step:
            self.time_step_updated.emit(self.ui.timeStepSpin.value())
            logger.debug(f"Emitted time_step_updated signal with value {self.ui.timeStepSpin.value()}")

    def update_progress(self, value, message):
        """Update the progress dialog (kept for compatibility, delegates to ProgressDialog)."""
        self.progress_dialog.update_progress(value, message)

    def cancel_calculation(self):
        """Handle cancellation of the calculation thread."""
        logger.debug("Cancellation requested by user")
        self.thread.cancel()
        self.progress_dialog.update_progress(self.progress_dialog.ui.progressBar.value(), "Cancelling after current calculation...")

    def calculation_finished(self, results):
        """Handle calculation completion."""
        self.progress_dialog.close()
        QMessageBox.information(self, "Success", "Calculations completed successfully.")
        self.accept()

    def calculation_error(self, error):
        """Handle calculation errors."""
        self.progress_dialog.close()
        logger.error(f"Calculation error: {error}")
        QMessageBox.critical(self, "Error", f"Calculation failed: {error}")
        self.reject()

    def load_settings(self):
        """Load dialog-specific settings."""
        self.ui.timeStepSpin.setValue(self.time_step)
        logger.debug(f"Loaded time_step={self.time_step} into timeStepSpin")
    
    def clear_selected_data(self):
        """Clear calculated data for selected observations."""
        selected_targets = [
            self.ui.targetList.item(i).data(Qt.UserRole)
            for i in range(self.ui.targetList.count())
            if self.ui.targetList.item(i).checkState() == Qt.Checked
        ]
        
        if not selected_targets:
            QMessageBox.warning(self, "Warning", "No observations selected for clearing data.")
            logger.warning("Attempted to clear data with no observations selected.")
            return

        try:
            for target in selected_targets:
                target.clear_calculated_data()
                logger.info(f"Cleared calculated data for observation '{target.code}'")
            QMessageBox.information(self, "Success", "Calculated data cleared for selected observations.")
        except Exception as e:
            logger.error(f"Failed to clear calculated data: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to clear calculated data: {str(e)}")