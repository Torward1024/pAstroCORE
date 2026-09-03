# pastrocore/gui/p_dialog_export_calculated_data.py
from PySide6.QtWidgets import QDialog, QListWidgetItem, QMessageBox, QFileDialog
from PySide6.QtCore import Qt, QThread, Signal
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from msb_arch.utils.logging_setup import logger
from pastrocore.gui.ui_dialog_export_calculated_data import Ui_ExportCalculatedDataDialog
from pastrocore.gui.ui_dialog_calc_progress import Ui_ProgressDialog
import os

class ProgressDialog(QDialog):
    """Custom progress dialog for export progress."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_ProgressDialog()
        self.ui.setupUi(self)
        self.setWindowTitle("Export Progress")
        logger.debug("ProgressDialog initialized")

    def update_progress(self, value, message):
        """Update progress bar and label."""
        self.ui.progressBar.setValue(value)
        self.ui.label.setText(message)
        logger.debug("ProgressDialog updated: value=%s, message=%s", value, message)

class ExportThread(QThread):
    """Thread for exporting calculated data and visualizations asynchronously."""
    progress = Signal(int, str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, manipulator, targets, calc_types, export_data, export_vis, export_path, units: str):
        super().__init__()
        self.manipulator = manipulator
        self.targets = targets
        self.calc_types = calc_types
        self.export_data = export_data
        self.export_vis = export_vis
        self.export_path = export_path
        self.units = units
        self._cancelled = False
        logger.debug("ExportThread initialized with calc_types: %s, export_data=%s, export_vis=%s, units=%s", self.calc_types, export_data, export_vis, self.units)

    def cancel(self):
        """Set cancellation flag."""
        self._cancelled = True
        logger.debug("ExportThread cancellation requested")

    def run(self):
        """Ask the orchestrator to export, and pass on what it reports.

        Notes:
            - The 252 lines that used to be here are in `ScheduleData`, where a script or a
              server can reach them. What is left is the part that is genuinely a thread: it
              turns the operation's progress into Qt signals and its own cancellation flag into
              a question the operation can ask.
        """
        try:
            # `raise_on_error=False` is what makes this a `Response` rather than the bare
            # answer. Without it the call returns the value itself, `.value` raised
            # AttributeError on a plain dict, and the export -- which had already written every
            # file -- was reported to the user as a failure.
            response = self.manipulator.export(
                obj=self.targets,
                calc_types=self.calc_types,
                export_data=self.export_data,
                export_vis=self.export_vis,
                export_path=self.export_path,
                units=self.units,
                progress=lambda percent, message: self.progress.emit(percent, message),
                cancelled=lambda: self._cancelled,
                raise_on_error=False,
            )
            if not response.ok:
                self.error.emit(str(response.error))
                return
            result = response.value
            if result and result.get("cancelled"):
                self.error.emit("Export cancelled by user")
                return
            self.finished.emit()
        except Exception as e:
            logger.error("Export error in thread: %s", str(e))
            self.error.emit(str(e))


class ExportCalculatedDataDialog(QDialog):
    """Dialog for exporting calculated data and visualizations."""

    def __init__(self, manipulator: ScheduleManipulator, parent=None):
        super().__init__(parent)
        self.ui = Ui_ExportCalculatedDataDialog()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self.project = manipulator.get_managing_object()
        self.default_export_path = parent.current_project_path if parent and hasattr(parent, 'current_project_path') and parent.current_project_path else os.getcwd()
        if self.default_export_path and os.path.isfile(self.default_export_path):
            self.default_export_path = os.path.dirname(self.default_export_path)
        logger.debug("Default export path set to: %s", self.default_export_path)
        self.init_ui()
        logger.debug("ExportCalculatedDataDialog initialized")

    def init_ui(self):
        """Initialize the dialog UI."""
        self.populate_calc_list()
        self.populate_targets()
        self.ui.lineEdit.setText(self.default_export_path)
        self.ui.cmbUnits.addItems(["Wavelengths", "Earth Diameters"])
        self.ui.cmbUnits.setCurrentText("Earth Diameters")  # Default
        logger.debug("UV units combo box populated with Wavelengths and Earth Diameters")
        self.ui.selectAllCalcButton.clicked.connect(self.select_all_calcs)
        self.ui.clearAllCalcButton.clicked.connect(self.clear_all_calcs)
        self.ui.selectAllObsButton.clicked.connect(self.select_all_targets)
        self.ui.clearAllObsButton.clicked.connect(self.clear_all_targets)
        self.ui.exportButton.clicked.connect(self.run_export)
        self.ui.cancelButton.clicked.connect(self.reject)
        self.ui.pushButton.clicked.connect(self.browse_path)

    def populate_calc_list(self):
        """Populate the calculation list."""
        # Everything, including the steps other calculations need. Choosing what to *compute*
        # leaves those out because nobody asks for them by name; choosing what to *export*
        # includes them, because the numbers are the numbers and somebody may want them.
        response = self.manipulator.compute(obj=None, method="catalogue", raise_on_error=False)
        catalogue = response.value or []

        self.ui.calcList.clear()
        for entry in catalogue:
            item = QListWidgetItem(entry["label"])
            item.setData(Qt.UserRole, entry["key"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.ui.calcList.addItem(item)
        logger.debug("Populated %s calculations", self.ui.calcList.count())

    def populate_targets(self):
        """Populate the target list with project observations."""
        try:
            observations = self.manipulator.inspect(obj=self.project, observations=None)
            self.ui.targetList.clear()
            for obs in observations:
                item = QListWidgetItem(obs.code)
                item.setData(Qt.UserRole, obs)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                self.ui.targetList.addItem(item)
            logger.debug("Populated %s observations", self.ui.targetList.count())
        except Exception as e:
            logger.error("Failed to retrieve observations: %s", str(e))

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

    def browse_path(self):
        """Browse for export directory."""
        path = QFileDialog.getExistingDirectory(self, "Select Export Directory", self.default_export_path)
        if path:
            self.ui.lineEdit.setText(path)
            logger.debug("Selected export path: %s", path)

    def run_export(self):
        """Run the export in a separate thread."""
        selected_calcs = [self.ui.calcList.item(i).text() for i in range(self.ui.calcList.count())
                          if self.ui.calcList.item(i).checkState() == Qt.Checked]
        selected_targets = [self.ui.targetList.item(i).data(Qt.UserRole) for i in range(self.ui.targetList.count())
                            if self.ui.targetList.item(i).checkState() == Qt.Checked]
        export_path = self.ui.lineEdit.text().strip()
        if not selected_calcs or not selected_targets or not export_path or not os.path.isdir(export_path):
            QMessageBox.warning(self, "Warning", "Please select calculations, targets, and a valid export path.")
            return
        units = self.ui.cmbUnits.currentText().lower().replace(" ", "_")

        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.ui.pushButtonCancel.clicked.connect(self.cancel_export)
        self.progress_dialog.show()

        self.thread = ExportThread(self.manipulator, selected_targets, selected_calcs,
                                   self.ui.chkExportData.isChecked(), self.ui.chkExportVisualizations.isChecked(), export_path, units)
        self.thread.progress.connect(self.progress_dialog.update_progress)
        self.thread.finished.connect(self.export_finished)
        self.thread.error.connect(self.export_error)
        self.thread.start()

    def cancel_export(self):
        self.thread.cancel()
        self.progress_dialog.update_progress(self.progress_dialog.ui.progressBar.value(), "Cancelling...")

    def export_finished(self):
        self.progress_dialog.close()
        self.accept()

    def export_error(self, error):
        self.progress_dialog.close()
        QMessageBox.critical(self, "Error", f"Export failed: {error}")
        self.reject()