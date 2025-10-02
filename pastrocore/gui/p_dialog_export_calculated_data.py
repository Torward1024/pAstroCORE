# pastrocore/gui/p_dialog_export_calculated_data.py
from PySide6.QtWidgets import QDialog, QListWidgetItem, QMessageBox, QFileDialog
from PySide6.QtCore import Qt, QThread, Signal
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from common.utils.logging_setup import logger
from pastrocore.gui.ui_dialog_export_calculated_data import Ui_ExportCalculatedDataDialog
from pastrocore.gui.ui_dialog_calc_progress import Ui_ProgressDialog
from pastrocore.base.observation import Observation
from pastrocore.base.data_structure import CalculatedDataStructure

from typing import Optional
import os
import pandas as pd
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
        logger.debug(f"ExportThread initialized with calc_types: {self.calc_types}, export_data={export_data}, export_vis={export_vis}, units={self.units}")

    def cancel(self):
        """Set cancellation flag."""
        self._cancelled = True
        logger.debug("ExportThread cancellation requested")

    def run(self):
        """Execute export asynchronously."""
        try:
            num_data_steps = 1 if self.export_data else 0
            num_vis_steps = 1 if self.export_vis else 0
            steps_per_target = len(self.calc_types) * (num_data_steps + num_vis_steps)
            total_steps = len(self.targets) * steps_per_target if steps_per_target > 0 else 1
            current_step = 0

            for target in self.targets:
                if self._cancelled:
                    self.error.emit("Export cancelled by user")
                    return
                obs_code = target.code
                self.progress.emit(int(current_step / total_steps * 100), f"Exporting for {obs_code}...")

                sources = list(target.get_sources()._items.keys())
                telescopes = [telescope.get_code() for telescope in target.get_telescopes()._items.values()]
                scans = [scan.name for scan in target.get_scans().get_items()]
                frequencies = [if_obj.frequency for if_obj in target.get_frequencies().get_items()]
                baselines = [f"{t1}-{t2}" for i, t1 in enumerate(telescopes) for t2 in telescopes[i+1:]]

                for calc_type in self.calc_types:
                    if self._cancelled:
                        self.error.emit("Export cancelled by user")
                        return

                    key = calc_type.lower().replace(" ", "_").replace("/", "_")
                    data = target.get_calculated_data_by_key(key)
                    if not isinstance(data, pd.DataFrame):
                        logger.debug(f"No data for {calc_type} in {obs_code}, skipping")
                        continue

                    if self.export_data:
                        if calc_type == "Beam Pattern":
                            file_prefix = "Beam_Pattern"
                        elif calc_type == "Mollweide Tracks":
                            file_prefix = "Mollweide"
                        else:
                            file_prefix = calc_type.replace(" ", "_").replace("/", "_")
                        file_name = f"{file_prefix}_{obs_code}"
                        txt_path = os.path.join(self.export_path, f"{file_name}.txt")
                        self._export_data_to_csv(data, calc_type, txt_path, obs_code, source_name=None, target=target)
                        current_step += 1
                        self.progress.emit(int(current_step / total_steps * 100), f"Exported data for {calc_type} in {obs_code}")

                    if self.export_vis:
                        visualizable_keys = [
                            "uv_coverage", "baseline_projections", "time_on_source",
                            "sun_angles", "az_el", "mollweide_tracks", "beam_pattern"
                        ]
                        if key not in visualizable_keys:
                            logger.debug(f"Skipping visualization for {calc_type} as it is not visualizable")
                            continue
                        if calc_type == "Beam Pattern":
                            file_prefix = "Beam_Pattern"
                        elif calc_type == "Mollweide Tracks":
                            file_prefix = "Mollweide"
                        else:
                            file_prefix = calc_type.replace(" ", "_").replace("/", "_")
                        file_name = f"{file_prefix}_{obs_code}"
                        png_path = os.path.join(self.export_path, f"{file_name}.png")
                        attributes = {
                            "plot_type": key,
                            "output_file": png_path,
                            "dpi": 76,
                            "telescopes": telescopes,
                            "scans": scans,
                            "sources": sources if key == "mollweide_tracks" else [],
                            "freq_names": frequencies if key == "beam_pattern" else [],
                            "baselines": baselines if key in ["uv_coverage", "baseline_projections"] else [],
                            "units": self.units if key in ["uv_coverage", "baseline_projections"] else None
                        }
                        try:
                            self.manipulator.visualize(obj=target, **attributes)
                        except Exception as e:
                            raise ValueError(f"Visualization export failed for {calc_type} in {obs_code}: {str(e)}")
                        current_step += 1
                        self.progress.emit(int(current_step / total_steps * 100), f"Exported vis for {calc_type} in {obs_code}")

            self.finished.emit()
        except Exception as e:
            logger.error(f"Export error in thread: {str(e)}")
            self.error.emit(str(e))

    def _export_data_to_csv(self, data: pd.DataFrame, calc_type: str, path: str, obs_code: str, source_name: Optional[str], target: Observation):
        """Export calculated data to a TXT file with tab separator.

        Uses pandas DataFrame to_csv for export with tab delimiter. Relies on CalculatedDataStructure converters
        for time-related columns to ensure proper formatting. For mollweide_tracks, adds source coordinates
        from df.attrs['sources'] as separate rows at the end of the file. Preserves NaN values as is.

        Args:
            data: pandas DataFrame containing calculated data.
            calc_type: Type of calculation (e.g., "UV Coverage").
            path: Output file path for TXT.
            obs_code: Observation code.
            source_name: Source name (ignored, kept for compatibility).
            target: Observation object.
        """
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            key = calc_type.lower().replace(" ", "_").replace("/", "_")
            
            expected_columns = CalculatedDataStructure.get_columns(key)
            if expected_columns is None:
                logger.error(f"Unsupported calc_type for TXT export: {calc_type}")
                raise ValueError(f"Unsupported calc_type for TXT export: {calc_type}")
            if not all(col in data.columns for col in expected_columns):
                missing_cols = [col for col in expected_columns if col not in data.columns]
                logger.error(f"Invalid DataFrame structure for key '{key}' in observation '{obs_code}': missing columns {missing_cols}")
                raise ValueError(f"Invalid DataFrame structure for key '{key}': missing columns {missing_cols}")

            df_out = data.copy()
            converters = CalculatedDataStructure.get_converters(key) or {}
            
            # Apply converters for all relevant columns
            for col, converter in converters.items():
                if col in df_out.columns:
                    try:
                        df_out[col] = df_out[col].apply(converter)
                    except Exception as e:
                        logger.error(f"Failed to apply converter for column '{col}' in key '{key}' of observation '{obs_code}': {str(e)}")
                        raise

            # Drop scan_name column if present
            df_out = df_out.drop(columns=["scan_name"], errors="ignore")

            # Reorder columns to match expected_columns (excluding scan_name if it was in the schema)
            expected_columns = [col for col in expected_columns if col != "scan_name"]
            df_out = df_out[expected_columns]

            # For mollweide_tracks, append source coordinates from df.attrs['sources']
            if key == "mollweide_tracks":
                sources = df_out.attrs.get("sources", {})
                logger.debug(f"Processing sources for {calc_type} in observation '{obs_code}': {sources}")

                if not isinstance(sources, dict):
                    logger.error(f"Invalid sources format in df.attrs for {calc_type} in observation '{obs_code}': expected dict, got {type(sources)}")
                    sources = {}
                
                source_rows = []
                for src_name, coords in sources.items():
                    try:
                        lon, lat = float(coords[0]), float(coords[1])
                        source_rows.append(["-----", src_name, lat, lon])
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to parse coordinates for source '{src_name}' in {calc_type}, observation '{obs_code}': {str(e)}")
                        continue
                
                if source_rows:
                    source_df = pd.DataFrame(source_rows, columns=["time", "telescope_code", "lat", "lon"])
                    df_out = pd.concat([df_out, source_df], ignore_index=True)
                else:
                    logger.warning(f"No valid sources to append for {calc_type} in observation '{obs_code}'")

            df_out.to_csv(path, index=False, sep='\t', encoding='utf-8', na_rep='NaN')
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
        self.default_export_path = parent.current_project_path if parent and hasattr(parent, 'current_project_path') and parent.current_project_path else os.getcwd()
        if self.default_export_path and os.path.isfile(self.default_export_path):
            self.default_export_path = os.path.dirname(self.default_export_path)
        logger.debug(f"Default export path set to: {self.default_export_path}")
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
        calc_types = [
            "UV Coverage", "Mollweide Tracks", "Baseline Projections",
            "Time on Source", "Sun Angles", "Azimuth/Elevation", "Beam Pattern",
            "Source Visibility", "Telescope Positions"
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
        try:
            observations = self.manipulator.inspect(obj=self.project, get_items=None)
            self.ui.targetList.clear()
            for _, obs in observations.items():
                item = QListWidgetItem(obs.code)
                item.setData(Qt.UserRole, obs)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                self.ui.targetList.addItem(item)
            logger.debug(f"Populated {self.ui.targetList.count()} observations")
        except Exception as e:
            logger.error(f"Failed to retrieve observations: {str(e)}")

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
        # Get selected UV units (lowercase, replace spaces)
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