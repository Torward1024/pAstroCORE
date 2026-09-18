# p_dialog_calculations.py
from PySide6.QtWidgets import QDialog, QInputDialog, QListWidgetItem, QMessageBox
from PySide6.QtCore import Qt, QThread, Signal
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from msb_arch.utils.logging_setup import logger
from pastrocore.base.data_structure import CalculatedDataStructure
from pastrocore.gui.ui_dialog_calculations import Ui_CalculationDialog
from pastrocore.gui.p_dialog_progress import ProgressDialog, stop_and_wait
from pastrocore.gui.p_table_models import Column, FrequencyTableModel, GainCurveTableModel


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

            outcome = self.manipulator.compute(
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
            # The whole outcome, not a summary of it: the report is assembled by the operation
            # and the window only renders it.
            self.finished.emit(results, errors, outcome)

        except Exception as error:                       # noqa: BLE001 - shown to the user
            logger.error("Calculation run failed: %s", str(error))
            self.error.emit(f"Critical error: {error}")


class CalculationDialog(QDialog):
    """Dialog for configuring and running multiple calculations."""
    time_step_updated = Signal(int)

    def done(self, result):
        """Close, but never ahead of the work this dialog started."""
        stop_and_wait(self.worker)
        super().done(result)

    def __init__(self, manipulator: ScheduleManipulator, targets=None, calc_type=None, time_step=600, parent=None):
        super().__init__(parent)
        # Not `thread`: that name is `QObject.thread()`, and a dialog that had started nothing
        # found the method there, failed on `isRunning`, and would not close.
        self.worker = None
        self.ui = Ui_CalculationDialog()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self.project = manipulator.get_managing_object()
        self.targets = targets or []
        # Which calculations cannot run without being told what to point at. The catalogue says
        # so, from the columns of the result, so nothing here lists them.
        self._needs_target = set()
        # What each calculation takes beyond the model, as the catalogue reports it. Which box a
        # person types it into is this dialog's business; which calculation takes what is not.
        self._parameters = {}
        self.calc_type = calc_type
        self.time_step = time_step
        self.init_ui()
        self.load_settings()

    #: Which boxes stand for which parameter. What a parameter *is* and which calculation takes
    #: it are the model's to say; where it is typed is this dialog's.
    PARAMETER_WIDGETS = {
        "threshold": ("labelThreshold", "thresholdSpin"),
        "bits": ("labelBits", "bitsCombo"),
        "fill": ("fillCheck",),
        "t_atm": ("labelAirTemperature", "airTemperatureSpin"),
        "opacity": ("labelOpacity", "opacityTable", "opacityAdd", "opacityRemove"),
        "gain_curve": ("labelGainCurves", "gainCurveTable", "gainCurveAdd", "gainCurveRemove"),
    }

    def init_ui(self):
        """Initialize the dialog UI."""
        self.populate_calc_list()
        self.populate_targets()
        self.setup_sensitivity()
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
        response = self.manipulator.inspect(obj=self.project, method="catalogue")
        catalogue = response or []

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
            self._parameters[entry["key"]] = set(entry.get("parameters") or ())
        logger.debug("Populated %s calculations, all checked.", self.ui.calcList.count())

    def populate_targets(self):
        """Populate the target list with project observations using observation code."""
        try:
            observations = self.manipulator.inspect(obj=self.project, get_observations=None)
            self.ui.targetList.clear()
            if not observations:
                logger.debug("No observations found in the project.")
                return
            for obs in observations:
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
        # Asked, not walked. What can be pointed at is a question about the model, and a
        # command line running the same calculations asks it the same way.
        response = self.manipulator.inspect(obj=None, method="targets", targets=observations,
                                            raise_on_error=False)
        codes = response.value or []

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

    def setup_sensitivity(self):
        """Build the boxes E1's calculations are asked with, and fill what the model answers.

        Notes:
            - **The recordings come from the backend.** How much of the correlation two-level
              quantising leaves is physics, and a combo box holding 1 and 2 because somebody
              typed them is that physics written down a second time.
            - The two grids hold an assumption of the run rather than anything of the model's,
              so they start empty: nothing is applied that was not asked for.
        """
        self.opacity_model = FrequencyTableModel(Column("Opacity at zenith", default=0.05))
        self.ui.opacityTable.setModel(self.opacity_model)
        self.gain_curve_model = GainCurveTableModel()
        self.ui.gainCurveTable.setModel(self.gain_curve_model)

        self.ui.opacityAdd.clicked.connect(lambda: self.opacity_model.add_row())
        self.ui.opacityRemove.clicked.connect(
            lambda: self._remove_selected(self.ui.opacityTable, self.opacity_model))
        self.ui.gainCurveAdd.clicked.connect(lambda: self.gain_curve_model.add_row())
        self.ui.gainCurveRemove.clicked.connect(
            lambda: self._remove_selected(self.ui.gainCurveTable, self.gain_curve_model))

        recordings = self.manipulator.inspect(obj=None, method="recording") or []
        self.ui.bitsCombo.clear()
        for recording in recordings:
            self.ui.bitsCombo.addItem(
                f"{recording['bits']} ({recording['efficiency']:.3f})", recording["bits"])
        if self.ui.bitsCombo.count():
            self.ui.bitsCombo.setCurrentIndex(self.ui.bitsCombo.count() - 1)
        self.update_params_ui()

    @staticmethod
    def _remove_selected(view, model):
        """Take out the rows somebody has selected, from the bottom so the indexes hold."""
        rows = sorted({index.row() for index in view.selectionModel().selectedIndexes()},
                      reverse=True)
        for row in rows:
            model.remove_row(row)

    def update_params_ui(self):
        """Offer exactly the parameters the selected calculations take.

        Notes:
            - Asked, not listed. A calculation says what it takes -- the catalogue reads it off
              what the result records -- so a detection threshold is not offered beside a beam
              pattern, and a parameter added to a calculation appears here on its own.
        """
        selected_keys = [self.ui.calcList.item(i).data(Qt.UserRole + 1)
                         for i in range(self.ui.calcList.count())
                         if self.ui.calcList.item(i).checkState() == Qt.Checked]
        # Whether a time step applies follows from what the calculations record, not from
        # comparing a title against the one calculation that happens not to be sampled.
        sampled = all(CalculatedDataStructure.uses_time_step(key) for key in selected_keys if key)
        self.ui.timeStepSpin.setEnabled(bool(selected_keys) and sampled)

        wanted = self._wanted_parameters(selected_keys)
        for parameter, widgets in self.PARAMETER_WIDGETS.items():
            for name in widgets:
                getattr(self.ui, name).setEnabled(parameter in wanted)
        logger.debug("Updated params UI, timeStepSpin enabled: %s, parameters offered: %s",
                     sampled, sorted(wanted))

    def _wanted_parameters(self, keys) -> set:
        """What the selected calculations take between them."""
        wanted = set()
        for key in keys:
            wanted |= self._parameters.get(key, set())
        return wanted

    def _asked_parameters(self, keys) -> dict:
        """Read the parameters the selected calculations take off the boxes that stand for them.

        Notes:
            - What is not asked for is not sent: no opacity means the calculation applies none
              and says so, which is not the same as an opacity of zero.
        """
        wanted = self._wanted_parameters(keys)
        asked = {}
        if "threshold" in wanted:
            asked["threshold"] = self.ui.thresholdSpin.value()
        if "bits" in wanted and self.ui.bitsCombo.currentData() is not None:
            asked["bits"] = int(self.ui.bitsCombo.currentData())
        if "fill" in wanted and self.ui.fillCheck.isChecked():
            asked["fill"] = True
        if "opacity" in wanted and self.opacity_model.get_data():
            asked["opacity"] = [list(row) for row in self.opacity_model.get_data()]
        if "t_atm" in wanted and self.ui.airTemperatureSpin.value() > 0:
            asked["t_atm"] = self.ui.airTemperatureSpin.value()
        if "gain_curve" in wanted and self.gain_curve_model.get_data():
            asked["gain_curve"] = self.gain_curve_model.get_data()
        return asked

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

        # Not a clearance any more. Ticking it used to throw away *every* result the selected
        # observations held -- including calculations nobody had asked for on this run -- and
        # then let the run recompute what it needed. Now it asks the run to recompute what it
        # would otherwise have kept, which is the thing the box is for.
        params = {
            "time_step": self.ui.timeStepSpin.value(),
            "force": self.ui.recalculateCheck.isChecked()
        }
        # What the selected calculations take beyond the model: a detection threshold, the
        # recording, the weather assumed, the gain curves. A step that takes none of them is
        # handed them all the same and ignores them, as it does the time step.
        params.update(self._asked_parameters([self._key_for_label(label)
                                              for label in selected_calcs]))
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

        self.progress_dialog = ProgressDialog(self, "Calculation Progress")
        self.progress_dialog.cancelRequested.connect(self.cancel_calculation)
        self.progress_dialog.update_progress(0, "Preparing calculations...")
        self.progress_dialog.show()

        selected_keys = [self._key_for_label(label) for label in selected_calcs]
        self.worker = CalculationThread(self.manipulator, selected_targets, selected_keys,
                                        calc_params)
        self.worker.progress.connect(self.progress_dialog.update_progress)
        self.worker.finished.connect(self.calculation_finished)
        self.worker.error.connect(self.calculation_error)
        self.worker.start()

        if self.ui.timeStepSpin.value() != self.time_step:
            self.time_step_updated.emit(self.ui.timeStepSpin.value())

    def calculation_finished(self, results: dict, errors: list, outcome: dict = None):
        """Show what the run did, rather than whether it went well.

        Args:
            results (dict): The steps that ran.
            errors (list): The steps that did not.
            outcome (dict): What `compute(method="run")` returned, report and summary included.

        Notes:
            - A message box saying "All calculations completed successfully" is the wrong shape
              twice over: it says nothing when everything worked, and when a step failed it has
              nowhere to put the detail, so the detail went to `output.log` and nobody read it.
              One report instead, which the window keeps so it can be reopened.
        """
        self.progress_dialog.finish()
        self.outcome = outcome or {}
        summary = self.outcome.get("summary", {})

        if errors:
            logger.warning("Calculations finished with %s failed step(s) in %.2f s",
                           len(errors), summary.get("seconds", 0.0))
        else:
            logger.info("All %s calculation(s) completed in %.2f s",
                        summary.get("steps", len(results)), summary.get("seconds", 0.0))

        # Shown by the window once this dialog has closed, not from inside it. A modal dialog
        # opened from a slot nests one event loop inside another, and the first version of this
        # blocked the suite exactly as the catalogue's modal warning once did.
        self.accept()

    def calculation_error(self, error: str):
        """Handle critical thread errors."""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.finish()
        logger.error("Calculation critical error: %s", error)
        QMessageBox.critical(self, "Error", f"Calculation failed: {error}")
        self.reject()

    def cancel_calculation(self):
        """Handle user cancellation."""
        logger.debug("Cancellation requested by user")
        if self.worker is not None:
            self.worker.cancel()

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
            outcome = self.manipulator.compute(obj=None, method="clear",
                                               targets=selected_targets)
            cleared = len(outcome.get("cleared", selected_targets))
            QMessageBox.information(self, "Success",
                                    f"Cleared the results of {cleared} observation(s).")
        except Exception as e:
            logger.error("Failed to clear calculated data: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to clear calculated data: {str(e)}")