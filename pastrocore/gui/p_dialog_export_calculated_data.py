# pastrocore/gui/p_dialog_export_calculated_data.py
from PySide6.QtWidgets import QDialog, QListWidgetItem, QMessageBox, QFileDialog
from PySide6.QtCore import Qt, QThread, Signal
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
from pastrocore.gui.ui_dialog_export_calculated_data import Ui_ExportCalculatedDataDialog
from pastrocore.gui.ui_dialog_calc_progress import Ui_ProgressDialog

from typing import Dict, Optional
import os
import numpy as np
from astropy.time import Time

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
        logger.debug(f"ProgressDialog updated: value={value}, message={message}")

class ExportThread(QThread):
    """Thread for exporting calculated data and visualizations asynchronously."""
    progress = Signal(int, str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, manipulator, targets, calc_types, export_data, export_vis, export_path):
        super().__init__()
        self.manipulator = manipulator
        self.targets = targets
        self.calc_types = calc_types
        self.export_data = export_data
        self.export_vis = export_vis
        self.export_path = export_path
        self._cancelled = False
        logger.debug(f"ExportThread initialized with calc_types: {self.calc_types}, export_data={export_data}, export_vis={export_vis}")

    def cancel(self):
        """Set cancellation flag."""
        self._cancelled = True
        logger.debug("ExportThread cancellation requested")

    def run(self):
        """Execute export asynchronously."""
        try:
            total = len(self.targets)
            current = 0
            for target in self.targets:
                if self._cancelled:
                    self.error.emit("Export cancelled by user")
                    return
                obs_code = target.code
                self.progress.emit(int(current / total * 100), f"Exporting for {obs_code}...")
                
                # Collect filters from Observation
                sources = list(target.get_sources()._items.keys())  # All source names
                telescopes = [telescope.get_code() for telescope in target.get_telescopes()._items.values()]  # All telescope codes
                scans = [scan.name for scan in target.get_scans().get_items()]  # All scan names
                frequencies = [if_obj.frequency for if_obj in target.get_frequencies().get_items()]  # All IF frequencies
                baselines = [f"{t1}-{t2}" for i, t1 in enumerate(telescopes) for t2 in telescopes[i+1:]]

                for calc_type in self.calc_types:
                    key = calc_type.lower().replace(" ", "_")
                    data = target.get_calculated_data_by_key(key)
                    if not data:
                        logger.debug(f"No data for {calc_type} in {obs_code}, skipping")
                        continue
                    # Export data if checked
                    if self.export_data:
                        file_name = f"{calc_type.replace(' ', '_')}_{obs_code}"
                        source_name = self._get_source_name_from_data(data, calc_type)
                        if source_name:
                            file_name += f"_{source_name}"
                        txt_path = os.path.join(self.export_path, f"{file_name}.txt")
                        self._export_data_to_txt(data, calc_type, txt_path, obs_code)
                    # Export visualization if checked
                    if self.export_vis:
                        # For plot_types requiring single source, iterate over all sources
                        if key in ["uv_coverage", "sun_angles", "az_el", "time_on_source", "baseline_projections"]:
                            for source_name in sources:
                                file_name = f"{calc_type.replace(' ', '_')}_{obs_code}_{source_name}"
                                png_path = os.path.join(self.export_path, f"{file_name}.png")
                                attributes = {
                                    "plot_type": key,
                                    "output_file": png_path,
                                    "dpi": 76,  # Explicitly set dpi as number
                                    "source_name": source_name,
                                    "baselines": baselines if key in ["uv_coverage", "baseline_projections"] else [],
                                    "telescopes": telescopes if key in ["sun_angles", "az_el", "time_on_source"] else [],
                                    "scans": scans,
                                    "frequencies": frequencies if key in ["uv_coverage", "baseline_projections"] else [],
                                    "units": "wavelengths" if key in ["uv_coverage", "baseline_projections"] else None
                                }
                                request = {
                                    "operation": "visualize",
                                    "attributes": attributes,
                                    "obj": target
                                }
                                result = self.manipulator.process_request(request)
                                if not result.get("status", False):
                                    raise ValueError(f"Visualization export failed for {calc_type} in {obs_code} for source {source_name}: {result.get('message')}")
                        # For plot_types supporting multiple sources
                        elif key == "mollweide_tracks":
                            file_name = f"{calc_type.replace(' ', '_')}_{obs_code}"
                            source_name = self._get_source_name_from_data(data, calc_type)
                            if source_name:
                                file_name += f"_{source_name}"
                            png_path = os.path.join(self.export_path, f"{file_name}.png")
                            attributes = {
                                "plot_type": key,
                                "output_file": png_path,
                                "dpi": 76,  # Explicitly set dpi as number
                                "telescopes": telescopes,
                                "scans": scans,
                                "sources": sources
                            }
                            request = {
                                "operation": "visualize",
                                "attributes": attributes,
                                "obj": target
                            }
                            result = self.manipulator.process_request(request)
                            if not result.get("status", False):
                                raise ValueError(f"Visualization export failed for {calc_type} in {obs_code}: {result.get('message')}")
                        # For other plot_types (e.g., beam_pattern)
                        else:
                            file_name = f"{calc_type.replace(' ', '_')}_{obs_code}"
                            source_name = self._get_source_name_from_data(data, calc_type)
                            if source_name:
                                file_name += f"_{source_name}"
                            png_path = os.path.join(self.export_path, f"{file_name}.png")
                            attributes = {
                                "plot_type": key,
                                "output_file": png_path,
                                "telescopes": telescopes,
                                "freq_names": frequencies if key == "beam_pattern" else []
                            }
                            request = {
                                "operation": "visualize",
                                "attributes": attributes,
                                "obj": target
                            }
                            result = self.manipulator.process_request(request)
                            if not result.get("status", False):
                                raise ValueError(f"Visualization export failed for {calc_type} in {obs_code}: {result.get('message')}")
                current += 1
                self.progress.emit(int(current / total * 100), f"Exported {obs_code}")
            self.finished.emit()
        except Exception as e:
            logger.error(f"Export error in thread: {str(e)}")
            self.error.emit(str(e))

    def _get_source_name_from_data(self, data: Dict, calc_type: str) -> Optional[str]:
        """Extract source name if applicable for the calculation type."""
        if "data" in data and isinstance(data["data"], dict) and data["data"]:
            return next(iter(data["data"].keys()))  # First source key
        return None

    def _export_data_to_txt(self, data: Dict, calc_type: str, path: str, obs_code: str):
        """Export calculated data to tab-separated TXT file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                # Implement specific export logic for each calc_type (stub for now; expand as in visualize export)
                if calc_type == "UV Coverage":
                    headers = ["Time (UTC)", "Telescope Pair", "U (m)", "V (m)"]
                    f.write('\t'.join(headers) + '\n')
                    # Extract rows from data["data"]...
                    pass  # Add extraction logic
                elif calc_type == "Mollweide Tracks":
                    headers = ["Time (UTC)", "Telescope", "Longitude (deg)", "Latitude (deg)"]
                    f.write('\t'.join(headers) + '\n')
                    # Extract from data...
                    pass
                # Add for other types: Baseline Projections, Time on Source, etc.
                logger.info(f"Exported data to {path}")
        except Exception as e:
            logger.error(f"Failed to export data to {path}: {str(e)}")
            raise

class ExportCalculatedDataDialog(QDialog):
    """Dialog for exporting calculated data and visualizations."""

    def __init__(self, manipulator: ScheduleManipulator, parent=None):
        super().__init__(parent)
        self.ui = Ui_ExportCalculatedDataDialog()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self.project = manipulator.get_managing_object()
        self.init_ui()
        logger.debug("ExportCalculatedDataDialog initialized")

    def init_ui(self):
        """Initialize the dialog UI."""
        self.populate_calc_list()
        self.populate_targets()
        self.ui.selectAllCalcButton.clicked.connect(self.select_all_calcs)
        self.ui.clearAllCalcButton.clicked.connect(self.clear_all_calcs)
        self.ui.selectAllObsButton.clicked.connect(self.select_all_targets)
        self.ui.clearAllObsButton.clicked.connect(self.clear_all_targets)
        self.ui.exportButton.clicked.connect(self.run_export)
        self.ui.cancelButton.clicked.connect(self.reject)
        self.ui.pushButton.clicked.connect(self.browse_path)

    def populate_calc_list(self):
        """Populate the calculation list."""
        calc_types = [
            "UV Coverage", "Mollweide Tracks", "Baseline Projections",
            "Time on Source", "Sun Angles", "Azimuth/Elevation", "Beam Pattern"
        ]
        self.ui.calcList.clear()
        for calc_type in calc_types:
            item = QListWidgetItem(calc_type)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.ui.calcList.addItem(item)
        logger.debug(f"Populated {self.ui.calcList.count()} calculations")

    def populate_targets(self):
        """Populate the target list with project observations."""
        observations_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.project,
            "attributes": {"get_items": None}
        })
        self.ui.targetList.clear()
        if observations_response["status"]:
            for _, obs in observations_response["result"].items():
                item = QListWidgetItem(obs.code)
                item.setData(Qt.UserRole, obs)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                self.ui.targetList.addItem(item)
            logger.debug(f"Populated {self.ui.targetList.count()} observations")

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
        path = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if path:
            self.ui.lineEdit.setText(path)
            logger.debug(f"Selected export path: {path}")

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

        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.ui.pushButtonCancel.clicked.connect(self.cancel_export)
        self.progress_dialog.show()

        self.thread = ExportThread(self.manipulator, selected_targets, selected_calcs,
                                   self.ui.chkExportData.isChecked(), self.ui.chkExportVisualizations.isChecked(), export_path)
        self.thread.progress.connect(self.progress_dialog.update_progress)
        self.thread.finished.connect(self.export_finished)
        self.thread.error.connect(self.export_error)
        self.thread.start()

    def cancel_export(self):
        self.thread.cancel()
        self.progress_dialog.update_progress(self.progress_dialog.ui.progressBar.value(), "Cancelling...")

    def export_finished(self):
        self.progress_dialog.close()
        QMessageBox.information(self, "Success", "Export completed successfully.")
        self.accept()

    def export_error(self, error):
        self.progress_dialog.close()
        QMessageBox.critical(self, "Error", f"Export failed: {error}")
        self.reject()