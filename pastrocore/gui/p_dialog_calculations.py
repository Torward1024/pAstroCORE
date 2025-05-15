from PySide6.QtWidgets import QDialog, QCheckBox, QTableWidgetItem, QListWidgetItem, QProgressDialog, QMessageBox, QFileDialog
from PySide6.QtCore import Qt, QThread, Signal
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_calculator import ScheduleCalculator
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
from pastrocore.gui.ui_dialog_calculations import Ui_CalculationDialog
import pastrocore.gui.rc_icons

class CalculationThread(QThread):
    """Thread for performing calculations asynchronously."""
    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, manipulator, targets, calc_types, params, freqs=None):
        super().__init__()
        self.manipulator = manipulator
        self.targets = targets
        self.calc_types = calc_types
        self.params = params
        self.freqs = freqs

    def run(self):
        try:
            results = {}
            total = len(self.targets) * len(self.calc_types) * (len(self.freqs) if self.freqs else 1)
            current = 0
            for target in self.targets:
                freqs = self.freqs or [f.name for f in target.frequencies.get_active_items()] if isinstance(target, Observation) else [None]
                for calc_type in self.calc_types:
                    for freq in freqs:
                        calc_params = self.params.get(calc_type, {})
                        if freq:
                            calc_params["freq_name"] = freq
                        # Map dialog calc types to calculator methods
                        method_map = {
                            "UV Coverage": "uv_coverage",
                            "Mollweide Tracks": "mollweide_tracks",
                            "Baseline Projections": "baseline_projections",
                            "Beam Pattern": "beam_pattern",
                            "Synthesized Beam": "synthesized_beam",
                            "Time on Source": "time_on_source",
                            "Sun Angles": "sun_angles",
                            "Azimuth/Elevation": "az_el"
                        }
                        method = method_map.get(calc_type, calc_type.lower().replace(" ", "_"))
                        # Add store_key for specific methods
                        if calc_type in ["Mollweide Tracks", "Time on Source", "Sun Angles", "Azimuth/Elevation"]:
                            calc_params["store_key"] = method
                        request = {
                            "operation": "calculate",
                            "attributes": {
                                "method": method,
                                **calc_params
                            },
                            "obj": target
                        }
                        result = self.manipulator.process_request(request)
                        if not result.get("status", False):
                            raise ValueError(f"Calculation {calc_type} failed for {target.name}: {result.get('message', 'Unknown error')}")
                        results[f"{target.name}_{calc_type}_{freq or 'all'}"] = result["result"]
                        current += 1
                        self.progress.emit(int(current / total * 100), f"Calculating {calc_type} for {freq or 'all'} on {target.name}")
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

class CalculationDialog(QDialog):
    """Dialog for configuring and running multiple calculations."""
    def __init__(self, manipulator, project, targets=None, calc_type=None, parent=None):
        super().__init__(parent)
        self.ui = Ui_CalculationDialog()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self.project = project
        self.targets = targets or []
        self.calc_type = calc_type
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Initialize the dialog UI."""
        self.populate_calc_table()
        self.populate_targets()
        self.ui.calcTable.itemChanged.connect(self.handle_calc_selection)
        self.ui.selectAllButton.clicked.connect(self.select_all_targets)
        self.ui.limitFreqsCheck.toggled.connect(self.update_freq_list)
        self.ui.calcButton.clicked.connect(self.run_calculation)
        self.ui.calcVizButton.clicked.connect(self.run_calculation_and_visualize)
        self.ui.exportButton.clicked.connect(self.export_script)
        self.ui.cancelButton.clicked.connect(self.reject)

    def populate_calc_table(self):
        """Populate the calculation table with available calculations."""
        calc_types = [
            "UV Coverage",
            "Mollweide Tracks",
            "Baseline Projections",
            "Beam Pattern",
            "Synthesized Beam",
            "Time on Source",
            "Sun Angles",
            "Azimuth/Elevation"
        ]
        dependencies = {
            "UV Coverage": ["Time on Source"],
            "Synthesized Beam": ["UV Coverage"],
            "Baseline Projections": ["UV Coverage"]
        }
        self.ui.calcTable.setRowCount(len(calc_types))
        for row, calc_type in enumerate(calc_types):
            checkbox = QCheckBox()
            if self.calc_type == calc_type:
                checkbox.setChecked(True)
            self.ui.calcTable.setCellWidget(row, 0, checkbox)
            item = QTableWidgetItem(calc_type)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.ui.calcTable.setItem(row, 1, item)
            status = self.check_calc_status(calc_type)
            self.ui.calcTable.setItem(row, 2, QTableWidgetItem(status))
            deps = ", ".join(dependencies.get(calc_type, []))
            self.ui.calcTable.setItem(row, 3, QTableWidgetItem(deps))
        self.ui.calcTable.resizeColumnsToContents()

    def check_calc_status(self, calc_type):
        """Check if calculation results are cached."""
        try:
            method_map = {
                "UV Coverage": "uv_coverage",
                "Mollweide Tracks": "mollweide_tracks",
                "Baseline Projections": "baseline_projections",
                "Beam Pattern": "beam_pattern",
                "Synthesized Beam": "synthesized_beam",
                "Time on Source": "time_on_source",
                "Sun Angles": "sun_angles",
                "Azimuth/Elevation": "az_el"
            }
            method = method_map.get(calc_type, calc_type.lower().replace(" ", "_"))
            return "Cached" if self.calculator.has_cached_data(self.project, method) else "Not Calculated"
        except AttributeError:
            return "Not Calculated"

    def populate_targets(self):
        """Populate the target list with project and observations."""
        item = QListWidgetItem(self.project.name)
        item.setData(Qt.UserRole, self.project)
        if not self.targets or self.project in self.targets:
            item.setSelected(True)
        self.ui.targetList.addItem(item)
        observations_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.project,
            "attributes": {"get_items": None}
        })
        if observations_response["status"]:
            for obs_name, obs in observations_response["result"].items():
                item = QListWidgetItem(obs_name)
                item.setData(Qt.UserRole, obs)
                if obs in self.targets:
                    item.setSelected(True)
                self.ui.targetList.addItem(item)

    def select_all_targets(self):
        """Select all targets in the list."""
        for i in range(self.ui.targetList.count()):
            self.ui.targetList.item(i).setSelected(True)
        self.update_freq_list()

    def update_freq_list(self):
        """Update the frequency list based on selected targets."""
        self.ui.freqList.clear()
        if not self.ui.limitFreqsCheck.isChecked():
            return
        selected_targets = [self.ui.targetList.item(i).data(Qt.UserRole) for i in range(self.ui.targetList.count())
                            if self.ui.targetList.item(i).isSelected()]
        freqs = set()
        for target in selected_targets:
            if isinstance(target, Observation):
                freq_response = self.manipulator.process_request({
                    "operation": "inspect",
                    "obj": target,
                    "attributes": {"get_frequencies": None}
                })
                if freq_response["status"]:
                    freqs.update(f.name for f in freq_response["result"].get_active_items())
        for freq in sorted(freqs):
            item = QListWidgetItem(freq)
            item.setSelected(True)
            self.ui.freqList.addItem(item)

    def handle_calc_selection(self, item):
        """Handle changes in calculation selection, including dependencies."""
        if self.ui.ignoreDepsCheck.isChecked():
            return
        row = item.row()
        checkbox = self.ui.calcTable.cellWidget(row, 0)
        calc_type = self.ui.calcTable.item(row, 1).text()
        dependencies = self.ui.calcTable.item(row, 3).text().split(", ") if self.ui.calcTable.item(row, 3).text() else []
        if checkbox.isChecked() and dependencies:
            for dep in dependencies:
                if not dep:
                    continue
                for r in range(self.ui.calcTable.rowCount()):
                    if self.ui.calcTable.item(r, 1).text() == dep:
                        self.ui.calcTable.cellWidget(r, 0).setChecked(True)
                        break
        self.update_params_ui()

    def update_params_ui(self):
        """Update the parameters UI based on selected calculations."""
        selected_calcs = [self.ui.calcTable.item(r, 1).text() for r in range(self.ui.calcTable.rowCount())
                          if self.ui.calcTable.cellWidget(r, 0).isChecked()]
        self.ui.timeStepSpin.setEnabled("Beam Pattern" not in selected_calcs)
        self.update_freq_list()

    def run_calculation(self):
        """Run the selected calculations in a separate thread."""
        selected_calcs = [self.ui.calcTable.item(r, 1).text() for r in range(self.ui.calcTable.rowCount())
                          if self.ui.calcTable.cellWidget(r, 0).isChecked()]
        selected_targets = [self.ui.targetList.item(i).data(Qt.UserRole) for i in range(self.ui.targetList.count())
                            if self.ui.targetList.item(i).isSelected()]
        if not selected_calcs or not selected_targets:
            QMessageBox.warning(self, "Warning", "Please select at least one calculation and one target.")
            return
        params = {
            "time_step": self.ui.timeStepSpin.value(),
            "recalculate": self.ui.recalculateCheck.isChecked()
        }
        calc_params = {calc: params for calc in selected_calcs}
        freqs = [self.ui.freqList.item(i).text() for i in range(self.ui.freqList.count())
                 if self.ui.freqList.item(i).isSelected()] if self.ui.limitFreqsCheck.isChecked() else None
        self.progress_dialog = QProgressDialog("Calculating...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.thread = CalculationThread(self.manipulator, selected_targets, selected_calcs, calc_params, freqs)
        self.thread.progress.connect(self.update_progress)
        self.thread.finished.connect(self.on_calculation_finished)
        self.thread.error.connect(self.on_calculation_error)
        self.thread.start()

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

    def open_visualization(self, results):
        """Open visualization dialog with calculation results (placeholder)."""
        logger.info("Visualization requested but not implemented.")
        QMessageBox.information(self, "Info", "Visualization is not implemented yet.")

    def export_script(self):
        """Generate and save a Python script for the calculations."""
        selected_calcs = [self.ui.calcTable.item(r, 1).text() for r in range(self.ui.calcTable.rowCount())
                          if self.ui.calcTable.cellWidget(r, 0).isChecked()]
        selected_targets = [self.ui.targetList.item(i).data(Qt.UserRole) for i in range(self.ui.targetList.count())
                            if self.ui.targetList.item(i).isSelected()]
        if not selected_calcs or not selected_targets:
            QMessageBox.warning(self, "Warning", "Please select at least one calculation and one target.")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Script", "", "Python Script (*.py)")
        if not file_path:
            return
        if not file_path.endswith(".py"):
            file_path += ".py"
        params = {
            "time_step": self.ui.timeStepSpin.value(),
            "recalculate": self.ui.recalculateCheck.isChecked()
        }
        freqs = [self.ui.freqList.item(i).text() for i in range(self.ui.freqList.count())
                 if self.ui.freqList.item(i).isSelected()] if self.ui.limitFreqsCheck.isChecked() else None
        method_map = {
            "UV Coverage": "uv_coverage",
            "Mollweide Tracks": "mollweide_tracks",
            "Baseline Projections": "baseline_projections",
            "Beam Pattern": "beam_pattern",
            "Synthesized Beam": "synthesized_beam",
            "Time on Source": "time_on_source",
            "Sun Angles": "sun_angles",
            "Azimuth/Elevation": "az_el"
        }
        try:
            with open(file_path, "w") as f:
                f.write("from pastrocore import ScheduleManipulator, ScheduleCalculator\n")
                f.write("# Script generated by pAstroCORE for calculations\n\n")
                f.write("manipulator = ScheduleManipulator(project)  # Replace with your project\n")
                f.write("calculator = ScheduleCalculator()\n\n")
                for target in selected_targets:
                    target_name = target.name
                    freq_list = freqs or [f.name for f in target.frequencies.get_active_items()] if isinstance(target, Observation) else [None]
                    for calc_type in selected_calcs:
                        method = method_map.get(calc_type, calc_type.lower().replace(" ", "_"))
                        for freq in freq_list:
                            f.write(f"# Calculation: {calc_type} for {target_name} {'with ' + freq if freq else ''}\n")
                            f.write("request = {\n")
                            f.write("    'operation': 'calculate',\n")
                            f.write("    'attributes': {\n")
                            f.write(f"        'method': '{method}',\n")
                            if freq:
                                f.write(f"        'freq_name': '{freq}',\n")
                            f.write(f"        'time_step': {params['time_step']},\n")
                            f.write(f"        'recalculate': {params['recalculate']}\n")
                            if calc_type in ["Mollweide Tracks", "Time on Source", "Sun Angles", "Azimuth/Elevation"]:
                                f.write(f"        'store_key': '{method}'\n")
                            f.write("    },\n")
                            f.write(f"    'obj': '{target_name}'\n")
                            f.write("}\n")
                            f.write("result = manipulator.process_request(request)\n")
                            f.write(f"print(f'Result for {calc_type} on {target_name}: {{result}}')\n\n")
            logger.info(f"Calculation script exported to '{file_path}'")
            QMessageBox.information(self, "Success", f"Script exported to '{file_path}'.")
        except Exception as e:
            logger.error(f"Failed to export script: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to export script: {str(e)}")

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
        """Load dialog-specific settings (placeholder)."""
        # Can load settings like default time_step from settings.pastro
        pass