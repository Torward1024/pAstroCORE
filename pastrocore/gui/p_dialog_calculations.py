# p_dialog_calculations.py
from PySide6.QtWidgets import QDialog, QInputDialog, QListWidgetItem, QMessageBox
from PySide6.QtCore import Qt, QThread, Signal
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from msb_arch.utils.logging_setup import logger
from pastrocore.base.data_structure import CalculatedDataStructure
from pastrocore.gui.ui_dialog_calculations import Ui_CalculationDialog
from pastrocore.gui.ui_dialog_calc_progress import Ui_ProgressDialog


class CalculationThread(QThread):
    """Thread for performing calculations asynchronously with robust error handling."""
    progress = Signal(int, str)
    finished = Signal(dict, list)
    error = Signal(str)

    def __init__(self, manipulator, targets, calc_types, params):
        super().__init__()
        self.manipulator = manipulator
        self.targets = targets
        self.calc_types = calc_types
        self.params = params
        self._cancelled = False
        logger.debug("CalculationThread initialized with calc_types: %s", self.calc_types)

        # Asked once when the work starts, so every step below spells a calculation the way
        # the manipulator does.
        response = manipulator.export(obj=None, method="catalogue", raise_on_error=False)
        offered = (response["result"] if isinstance(response, dict) and "status" in response
                   else response) or []
        self._keys_by_label = {entry["label"]: entry["key"] for entry in offered}

        # What is valid is what the manipulator offers, so a new calculation needs no second
        # list to be added to before it can be run.
        response = manipulator.export(obj=None, method="catalogue", raise_on_error=False)
        offered = (response["result"] if isinstance(response, dict) and "status" in response
                   else response) or []
        valid_calcs = {entry["label"] for entry in offered} | {entry["key"] for entry in offered}
        invalid_calcs = [calc for calc in calc_types if calc not in valid_calcs]
        if invalid_calcs:
            logger.error("Invalid calculation types provided: %s", invalid_calcs)
            raise ValueError(f"Invalid calculation types: {invalid_calcs}")

    def cancel(self):
        """Set cancellation flag to stop after current calculation."""
        self._cancelled = True
        logger.debug("CalculationThread cancellation requested")

    def run(self):
        """Execute calculations asynchronously with per-item error handling."""
        results = {}
        errors = []
        freq_dependent_calcs = ["Synthesized Beam"]

        try:
            total = sum(
                len(target.frequencies.get_active_items()) if calc_type in freq_dependent_calcs else 1
                for target in self.targets for calc_type in self.calc_types
            )
            current = 0

            for target in self.targets:
                if self._cancelled:
                    logger.info("Calculation cancelled by user")
                    self.error.emit("Calculation cancelled by user")
                    return

                freqs = ([f.name for f in target.frequencies.get_active_items()]
                         if isinstance(target, Observation) else [None])

                for calc_type in self.calc_types:
                    if self._cancelled:
                        logger.info("Calculation cancelled by user")
                        self.error.emit("Calculation cancelled by user")
                        return

                    calc_params = self.params.get(calc_type, {}).copy()
                    time_step = calc_params.get("time_step", 600)

                    # The label a user sees and the key a request needs are two spellings of
                    # one thing, and the manipulator knows both. A table here was a third copy.
                    method = self._keys_by_label.get(
                        calc_type, calc_type.lower().replace(" ", "_"))

                    if calc_type in freq_dependent_calcs:
                        for freq in freqs:
                            self._process_single_calc(target, calc_type, method, freq,
                                                      calc_params, time_step, results, errors, current, total)
                            current += 1
                    else:
                        self._process_single_calc(target, calc_type, method, None,
                                                  calc_params, time_step, results, errors, current, total)
                        current += 1

            if errors:
                logger.warning("Completed with %s errors. Results collected: %s", len(errors), len(results))
                self.finished.emit(results, errors)
            else:
                logger.info("All calculations completed successfully")
                self.finished.emit(results, [])

        except Exception as e:
            logger.error("Unexpected error in CalculationThread: %s", str(e))
            self.error.emit(f"Critical error: {str(e)}")

    def _process_single_calc(self, target, calc_type, method, freq, base_params,
                             time_step, results, errors, current, total):
        """Helper to process single calculation with isolated error handling."""
        try:
            calc_params = base_params.copy()
            calc_params["time_step"] = time_step

            if freq is not None:
                calc_params["freq_name"] = freq
                calc_params["store_key"] = f"{method}_{freq}"
                display_name = f"{calc_type} for {target.code} at {freq}"
            else:
                calc_params["store_key"] = method
                display_name = f"{calc_type} for {target.code}"

            logger.debug("Executing %s on %s with params: %s", calc_type, target.code, calc_params)

            result = self.manipulator.calculate(obj=target, method=method, **calc_params)
            key = f"{target.code}_{calc_type}" + (f"_{freq}" if freq else "")
            results[key] = result

            progress_pct = int((current + 1) / total * 100)
            self.progress.emit(progress_pct, f"Calculated {display_name}")

        except Exception as e:
            key = f"{target.code}_{calc_type}" + (f"_{freq}" if freq else "")
            err_msg = f"{calc_type} failed for {target.code}" + (f" at {freq}" if freq else "") + f": {str(e)}"
            errors.append(err_msg)
            logger.error(err_msg)

            progress_pct = int((current + 1) / total * 100)
            self.progress.emit(progress_pct, f"Failed {display_name}")


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
        logger.debug("ProgressDialog updated: value=%s, message=%s", value, message)


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
        # Which calculations cannot run without being told what to point at. The catalogue says
        # so, from the columns of the result, so nothing here lists them.
        self._needs_target = set()
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
        logger.debug("Calculation %s check state changed to: %s", item.text(), item.checkState())

    def populate_calc_list(self):
        """Populate the calculation list with available calculations."""
        # Asked, not listed. The manipulator works out what it offers from the handlers that
        # do the work, so a calculation added to the calculator appears here on its own -- and
        # the prerequisites come from the code that states them rather than from a table kept
        # by hand in a dialog.
        response = self.manipulator.export(obj=self.project, method="catalogue")
        catalogue = (response["result"] if isinstance(response, dict) and "status" in response
                     else response) or []

        self.ui.calcList.clear()
        for entry in catalogue:
            if not entry["offer"]:
                continue        # a step other calculations need, not one a user asks for
            item = QListWidgetItem(entry["label"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            item.setData(Qt.UserRole, entry["requires"])
            item.setData(Qt.UserRole + 1, entry["key"])
            self.ui.calcList.addItem(item)
            if entry.get("needs_target"):
                self._needs_target.add(entry["key"])
        logger.debug("Populated %s calculations, all checked.", self.ui.calcList.count())

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
            logger.debug("Populated %s observations, all checked.", self.ui.targetList.count())
        except Exception as e:
            logger.error("Failed to retrieve observations: %s", str(e))
            QMessageBox.critical(self, "Error", "Failed to load observations. Please check the project data.")

    def _key_for_label(self, label: str) -> str:
        """Return the result key an item in the list stands for.

        Notes:
            - The list shows labels because that is what a person reads; every request needs
              the key. The dialog holds the pairing from the catalogue rather than deriving it,
              since a label may be spelled anything.
        """
        for index in range(self.ui.calcList.count()):
            item = self.ui.calcList.item(index)
            if item.text() == label:
                return item.data(Qt.UserRole + 1)
        return label.lower().replace(" ", "_")

    def _ask_for_target(self, observations, calculations):
        """Return the code of the spacecraft to point at, or None to stop.

        Args:
            observations (list): The observations about to be calculated.
            calculations (list): The calculations that need a target, for the message.

        Returns:
            Optional[str]: A telescope code, or None when there is nothing to point at or the
                user cancelled.

        Notes:
            - Chosen once for the run rather than per calculation: pointing two of them at
                different spacecraft in one go is not something anyone has wanted, and the
                dialog would have to grow a table to express it.
            - With exactly one spacecraft in the selected observations, that is the answer and
              nothing is asked.
        """
        from pastrocore.base.telescopes import SpaceTelescope

        codes = []
        for observation in observations:
            for telescope in observation.get_telescopes().get_items():
                if isinstance(telescope, SpaceTelescope) and telescope.get_code() not in codes:
                    codes.append(telescope.get_code())

        if not codes:
            QMessageBox.warning(
                self, "Nothing to point at",
                "These calculations need a spacecraft to track:\n\n  "
                + "\n  ".join(sorted(calculations))
                + "\n\nThe selected observations hold no space telescope.")
            return None

        if len(codes) == 1:
            logger.debug("One spacecraft in the selection; pointing at '%s'", codes[0])
            return codes[0]

        chosen, accepted = QInputDialog.getItem(
            self, "Which spacecraft?",
            "These calculations track a spacecraft:\n  " + "\n  ".join(sorted(calculations))
            + "\n\nPoint at:", sorted(codes), 0, False)
        return chosen if accepted else None

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
        logger.debug("Handling dependencies for %s: %s", calc_type, dependencies)
        for dep in dependencies:
            for i in range(self.ui.calcList.count()):
                if self.ui.calcList.item(i).text() == dep:
                    self.ui.calcList.item(i).setCheckState(Qt.Checked)
                    logger.debug("Enabled dependency: %s", dep)
                    break
        self.update_params_ui()

    def update_params_ui(self):
        """Update the parameters UI based on selected calculations."""
        selected_keys = [self.ui.calcList.item(i).data(Qt.UserRole + 1)
                         for i in range(self.ui.calcList.count())
                         if self.ui.calcList.item(i).checkState() == Qt.Checked]
        # Whether a time step applies follows from what the calculations record, not from
        # comparing a title against the one calculation that happens not to be sampled.
        sampled = all(CalculatedDataStructure.uses_time_step(key) for key in selected_keys if key)
        self.ui.timeStepSpin.setEnabled(bool(selected_keys) and sampled)
        logger.debug("Updated params UI, timeStepSpin enabled: %s", sampled)

    def run_calculation(self):
        """Run the selected calculations in a separate thread."""
        selected_calcs = [self.ui.calcList.item(i).text() for i in range(self.ui.calcList.count())
                          if self.ui.calcList.item(i).checkState() == Qt.Checked]
        selected_targets = [self.ui.targetList.item(i).data(Qt.UserRole) for i in range(self.ui.targetList.count())
                            if self.ui.targetList.item(i).checkState() == Qt.Checked]

        logger.debug("Selected calculations: %s", selected_calcs)
        logger.debug("Selected targets: %s", [t.code for t in selected_targets])

        if not selected_calcs or not selected_targets:
            QMessageBox.warning(self, "Warning", "Please select at least one calculation and one target.")
            return

        if self.ui.recalculateCheck.isChecked():
            for target in selected_targets:
                try:
                    target.clear_calculated_data()
                    logger.info("Cleared cached data for '%s'", target.code)
                except Exception as e:
                    logger.error("Failed to clear cache for %s: %s", target.code, e)
                    QMessageBox.critical(self, "Error", f"Failed to clear cache: {e}")
                    return

        params = {
            "time_step": self.ui.timeStepSpin.value(),
            "recalculate": False
        }
        calc_params = {calc: params.copy() for calc in selected_calcs}

        # The list shows labels and the catalogue speaks keys, so compare on the key the item
        # carries. Matching on the label is how the target went missing in the first place.
        wanting_target = [calc for calc in selected_calcs
                          if self._key_for_label(calc) in self._needs_target]
        if wanting_target:
            target_code = self._ask_for_target(selected_targets, wanting_target)
            if target_code is None:
                return
            for calc in wanting_target:
                calc_params[calc]["target_telescope"] = target_code

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

    def calculation_finished(self, results: dict, errors: list):
        """Handle calculation completion — distinguish success from partial failure."""
        self.progress_dialog.close()

        if errors:
            error_text = "Some calculations completed with errors:\n\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                error_text += f"\n\n... and {len(errors)-10} more errors."
            QMessageBox.warning(self, "Partial Success", error_text)
            logger.warning("Calculations finished with %s errors.", len(errors))
        else:
            QMessageBox.information(self, "Success", "All calculations completed successfully.")
            logger.info("All calculations completed successfully.")

        self.accept()

    def calculation_error(self, error: str):
        """Handle critical thread errors."""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        logger.error("Calculation critical error: %s", error)
        QMessageBox.critical(self, "Error", f"Calculation failed: {error}")
        self.reject()

    def cancel_calculation(self):
        """Handle user cancellation."""
        logger.debug("Cancellation requested by user")
        if hasattr(self, 'thread') and self.thread:
            self.thread.cancel()
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.update_progress(
                    self.progress_dialog.ui.progressBar.value(),
                    "Cancelling after current calculation..."
                )

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
        logger.error("Calculation error: %s", error)
        QMessageBox.critical(self, "Error", f"Calculation failed: {error}")
        self.reject()

    def load_settings(self):
        """Load dialog-specific settings."""
        self.ui.timeStepSpin.setValue(self.time_step)
        logger.debug("Loaded time_step=%s into timeStepSpin", self.time_step)
    
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
                logger.info("Cleared calculated data for observation '%s'", target.code)
            QMessageBox.information(self, "Success", "Calculated data cleared for selected observations.")
        except Exception as e:
            logger.error("Failed to clear calculated data: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to clear calculated data: {str(e)}")