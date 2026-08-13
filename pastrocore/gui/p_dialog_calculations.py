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
    """Runs a set of calculations off the interface thread.

    Args:
        manipulator (ScheduleManipulator): The orchestrator every request goes through.
        targets (list): The observations to calculate for.
        calc_types (list): The result keys asked for.
        params (dict): What to pass to every step -- `time_step`, `target_telescope`,
            `recalculate`.

    Notes:
        - One request. Which prerequisites are needed, what order they go in, and what to skip
          when a step fails are worked out by the backend from the handlers themselves, so a
          command line or a server sending the same request gets the same behaviour.
        - Progress and cancellation are carried by the request, not by a loop here.
    """

    progress = Signal(int, str)
    finished = Signal(dict, list, dict)
    error = Signal(str)

    def __init__(self, manipulator, targets, calc_types, params):
        super().__init__()
        self.manipulator = manipulator
        self.targets = targets
        self.calc_types = calc_types
        self.params = params or {}
        self._cancelled = False

    def cancel(self):
        """Ask the run to stop after the step in flight."""
        self._cancelled = True
        logger.debug("Calculation cancellation requested")

    def run(self):
        """Send the request and report what came back."""
        try:
            shared = {}
            for per_calculation in self.params.values():
                shared.update(per_calculation)

            outcome = self.manipulator.export(
                obj=None, method="run",
                targets=self.targets, calculations=self.calc_types,
                progress=lambda percent, message: self.progress.emit(percent, message),
                cancelled=lambda: self._cancelled,
                # Steps that wait for nothing run together. Measured at 1.30x over the fixture
                # project's thirteen-step plan; the ceiling is what the fan below the base
                # steps costs.
                concurrent=True,
                **shared)

            if outcome.get("cancelled"):
                self.error.emit("Calculation cancelled by user")
                return

            results = {name: True for name in outcome.get("ran", [])}
            errors = [f"{name} failed" for name in outcome.get("failed", [])]
            if errors:
                logger.warning("Completed with %s failed step(s)", len(errors))
            self.finished.emit(results, errors, outcome.get("summary", {}))

        except Exception as error:                       # noqa: BLE001 - shown to the user
            logger.error("Calculation run failed: %s", str(error))
            self.error.emit(f"Critical error: {error}")


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
        # Compared on the key: `requires` names results, the list shows labels. A prerequisite
        # that is not offered -- a step nobody asks for by name -- is not in the list at all,
        # and the backend adds it to the plan anyway.
        logger.debug("Ticking what %s needs: %s", item.data(Qt.UserRole + 1), dependencies)
        for index in range(self.ui.calcList.count()):
            other = self.ui.calcList.item(index)
            if other.data(Qt.UserRole + 1) in dependencies:
                other.setCheckState(Qt.Checked)
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
            # Every step that accepts it gets the target; the ones that do not ignore it.
            for calc in calc_params:
                calc_params[calc].setdefault("target_telescope", target_code)

        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.ui.pushButtonCancel.clicked.connect(self.cancel_calculation)
        self.progress_dialog.update_progress(0, "Preparing calculations...")
        self.progress_dialog.show()

        selected_keys = [self._key_for_label(label) for label in selected_calcs]
        self.thread = CalculationThread(self.manipulator, selected_targets, selected_keys,
                                        calc_params)
        self.thread.progress.connect(self.progress_dialog.update_progress)
        self.thread.finished.connect(self.calculation_finished)
        self.thread.error.connect(self.calculation_error)
        self.thread.start()

        if self.ui.timeStepSpin.value() != self.time_step:
            self.time_step_updated.emit(self.ui.timeStepSpin.value())

    def calculation_finished(self, results: dict, errors: list, report: dict = None):
        """Handle calculation completion — distinguish success from partial failure.

        Args:
            results (dict): The steps that ran.
            errors (list): The steps that did not.
            report (dict): What the run reports about itself -- how many steps, how long, and
                which was slowest. Worked out by the operation, not here: a command line and a
                server want the same three numbers.
        """
        self.progress_dialog.close()
        report = report or {}
        summary = (f"{report.get('steps', len(results))} calculation(s) in "
                   f"{report.get('seconds', 0.0):.1f} s"
                   + (f"; slowest {report['slowest']} at {report['slowest_seconds']:.1f} s"
                      if report.get("slowest") else ""))

        if errors:
            error_text = "Some calculations completed with errors:\n\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                error_text += f"\n\n... and {len(errors)-10} more errors."
            QMessageBox.warning(self, "Partial Success", f"{error_text}\n\n{summary}")
            logger.warning("Calculations finished with %s errors. %s", len(errors), summary)
        else:
            QMessageBox.information(self, "Success", f"All calculations completed.\n\n{summary}")
            logger.info("All calculations completed. %s", summary)

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