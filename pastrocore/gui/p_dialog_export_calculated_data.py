# pastrocore/gui/p_dialog_export_calculated_data.py
from PySide6.QtWidgets import QDialog, QListWidgetItem, QMessageBox, QFileDialog
from PySide6.QtCore import Qt, QThread, Signal
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from common.utils.logging_setup import logger
from pastrocore.gui.ui_dialog_export_calculated_data import Ui_ExportCalculatedDataDialog
from pastrocore.gui.ui_dialog_calc_progress import Ui_ProgressDialog
from pastrocore.base.observation import Observation

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
                    if not data:
                        logger.debug(f"No data for {calc_type} in {obs_code}, skipping")
                        continue

                    per_source_keys = [
                        "uv_coverage", "baseline_projections", "time_on_source",
                        "sun_angles", "az_el", "source_visibility"
                    ]

                    if self.export_data:
                        if key in per_source_keys:
                            for source_name in data["data"].keys():
                                file_prefix = calc_type.replace(" ", "_").replace("/", "_")
                                file_name = f"{file_prefix}_{obs_code}_{source_name}"
                                txt_path = os.path.join(self.export_path, f"{file_name}.txt")
                                self._export_data_to_txt(data, calc_type, txt_path, obs_code, source_name=source_name, target=target)
                        else:
                            if calc_type == "Beam Pattern":
                                file_prefix = "Beam_Pattern"
                            elif calc_type == "Mollweide Tracks":
                                file_prefix = "Mollweide"
                            else:
                                file_prefix = calc_type.replace(" ", "_").replace("/", "_")
                            file_name = f"{file_prefix}_{obs_code}"
                            txt_path = os.path.join(self.export_path, f"{file_name}.txt")
                            self._export_data_to_txt(data, calc_type, txt_path, obs_code, source_name=None, target=target)
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
                        if key in per_source_keys:
                            for source_name in sources:
                                file_prefix = calc_type.replace(" ", "_").replace("/", "_")
                                file_name = f"{file_prefix}_{obs_code}_{source_name}"
                                png_path = os.path.join(self.export_path, f"{file_name}.png")
                                attributes = {
                                    "plot_type": key,
                                    "output_file": png_path,
                                    "dpi": 76,
                                    "source_name": source_name,
                                    "baselines": baselines if key in ["uv_coverage", "baseline_projections"] else [],
                                    "telescopes": telescopes if key in ["sun_angles", "az_el", "time_on_source"] else [],
                                    "scans": scans,
                                    "frequencies": frequencies if key in ["uv_coverage", "baseline_projections"] else [],
                                    "units": self.units if key in ["uv_coverage", "baseline_projections"] else None
                                }
                                try:
                                    self.manipulator.visualize(obj=target, **attributes)
                                except Exception as e:
                                    raise ValueError(f"Visualization export failed for {calc_type} in {obs_code} for source {source_name}: {str(e)}")
                        else:
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
                                "freq_names": frequencies if key == "beam_pattern" else []
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

    def _export_data_to_txt(self, data: Dict, calc_type: str, path: str, obs_code: str, source_name: Optional[str], target: Observation):
        """Export calculated data to tab-separated TXT file.

        Handles different calculation types with appropriate table structures.
        Uses 'times' from calculated_data for time alignment where applicable.
        Excludes 'Scan' column from output as it is not informative.
        """
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            times_data = target.get_calculated_data_by_key("times")
            times = times_data["data"] if times_data else None

            with open(path, 'w', encoding='utf-8') as f:
                key = calc_type.lower().replace(" ", "_").replace("/", "_")
                
                if key == "uv_coverage":
                    # Per source: Time, Baseline, U (m), V (m), W (m)
                    headers = ["Time (UTC)", "Baseline", "U (m)", "V (m)", "W (m)"]
                    f.write('\t'.join(headers) + '\n')
                    scans_data = data["data"][source_name]
                    for scan_name in sorted(scans_data):
                        uvw_dict = scans_data[scan_name]
                        scan_times = times[source_name][scan_name] if times else []
                        for baseline in sorted(uvw_dict):
                            uvw = uvw_dict[baseline]
                            for i, t in enumerate(scan_times):
                                row = [t.isot, baseline, uvw[i, 0], uvw[i, 1], uvw[i, 2]]
                                f.write('\t'.join(map(str, row)) + '\n')
                
                elif key == "baseline_projections":
                    headers = ["Time (UTC)", "Baseline", "Projection (m)"]
                    f.write('\t'.join(headers) + '\n')
                    scans_data = data["data"][source_name]
                    for scan_name in sorted(scans_data):
                        proj_dict = scans_data[scan_name]
                        scan_times = times[source_name][scan_name] if times else []
                        for baseline in sorted(proj_dict):
                            proj = proj_dict[baseline]
                            for i, t in enumerate(scan_times):
                                value = proj[i] if proj.ndim == 1 else proj[i, 0]
                                row = [t.isot, baseline, value]
                                f.write('\t'.join(map(str, row)) + '\n')
                
                elif key == "time_on_source":
                    headers = ["Telescope", "Start (UTC)", "End (UTC)", "Duration (s)"]
                    f.write('\t'.join(headers) + '\n')
                    scans_data = data["data"][source_name]
                    all_blocks = {}
                    for scan_name in sorted(scans_data):
                        tels_dict = scans_data[scan_name]
                        for tel_code in sorted(tels_dict):
                            blocks = tels_dict[tel_code]
                            if isinstance(blocks, np.ndarray):
                                blocks = blocks.tolist()
                            if not blocks:
                                continue
                            if tel_code not in all_blocks:
                                all_blocks[tel_code] = []
                            for block in blocks:
                                try:
                                    start_time = block[0]
                                    end_time = block[1]
                                    if isinstance(start_time, (float, np.floating)):
                                        start_time = Time(start_time, format='mjd')
                                    if isinstance(end_time, (float, np.floating)):
                                        end_time = Time(end_time, format='mjd')
                                    if not isinstance(start_time, Time) or not isinstance(end_time, Time):
                                        logger.debug(f"Invalid time format for scan '{scan_name}', telescope '{tel_code}', skipping")
                                        continue
                                    duration = float(block[2])
                                    row = [tel_code, start_time.isot, end_time.isot, duration]
                                    f.write('\t'.join(map(str, row)) + '\n')
                                    all_blocks[tel_code].append((start_time.mjd, end_time.mjd, duration))
                                except (ValueError, TypeError) as e:
                                    logger.debug(f"Failed to process time_on_source for scan '{scan_name}', telescope '{tel_code}': {str(e)}")
                                    continue
                    
                    tel_list = sorted(all_blocks.keys())
                    if tel_list:
                        all_times = [[(start, end) for start, end, _ in all_blocks[tel]] for tel in tel_list]
                        if all_times and all(all_times):
                            time_points = sorted(set(t for tel_times in all_times for start, end in tel_times for t in (start, end)))
                            intersection_times = []
                            for i in range(len(time_points) - 1):
                                start, end = time_points[i], time_points[i + 1]
                                all_active = all(any(start_t <= start and end <= end_t for start_t, end_t in tel_times)
                                                for tel_times in all_times)
                                if all_active:
                                    intersection_times.append((start, end))
                            
                            for start_mjd, end_mjd in intersection_times:
                                try:
                                    start_time = Time(start_mjd, format='mjd')
                                    end_time = Time(end_mjd, format='mjd')
                                    duration = (end_mjd - start_mjd) * 86400.0
                                    row = ["Total", start_time.isot, end_time.isot, duration]
                                    f.write('\t'.join(map(str, row)) + '\n')
                                    logger.debug(f"Added Total block: start={start_time.isot}, end={end_time.isot}, duration={duration}s")
                                except (ValueError, TypeError) as e:
                                    logger.debug(f"Failed to process Total block: {str(e)}")
                                    continue
                            if not intersection_times:
                                logger.debug(f"No intersection times found for Total in source '{source_name}'")
                
                elif key == "sun_angles":
                    headers = ["Time (UTC)", "Telescope", "Angle (deg)"]
                    f.write('\t'.join(headers) + '\n')
                    scans_data = data["data"][source_name]
                    for scan_name in sorted(scans_data):
                        tels_dict = scans_data[scan_name]
                        scan_times = times[source_name][scan_name] if times else []
                        for tel_code in sorted(tels_dict):
                            angles = tels_dict[tel_code]
                            for i, t in enumerate(scan_times):
                                row = [t.isot, tel_code, angles[i]]
                                f.write('\t'.join(map(str, row)) + '\n')
                
                elif key == "az_el":
                    headers = ["Time (UTC)", "Telescope", "Az (deg)", "El (deg)"]
                    f.write('\t'.join(headers) + '\n')
                    scans_data = data["data"][source_name]
                    for scan_name in sorted(scans_data):
                        tels_dict = scans_data[scan_name]
                        scan_times = times[source_name][scan_name] if times else []
                        for tel_code in sorted(tels_dict):
                            azel = tels_dict[tel_code]
                            for i, t in enumerate(scan_times):
                                row = [t.isot, tel_code, azel[i, 0], azel[i, 1]]
                                f.write('\t'.join(map(str, row)) + '\n')
                
                elif key == "source_visibility":
                    headers = ["Time (UTC)", "Telescope", "Visible"]
                    f.write('\t'.join(headers) + '\n')
                    scans_data = data["data"][source_name]
                    for scan_name in sorted(scans_data):
                        tels_dict = scans_data[scan_name]
                        scan_times = times[source_name][scan_name] if times else []
                        for tel_code in sorted(tels_dict):
                            vis = tels_dict[tel_code]
                            for i, t in enumerate(scan_times):
                                row = [t.isot, tel_code, bool(vis[i])]
                                f.write('\t'.join(map(str, row)) + '\n')
                
                elif key == "beam_pattern":
                    headers = ["Telescope", "Theta (arcsec)", "Pattern (normalized)"]
                    f.write('\t'.join(headers) + '\n')
                    beam_data = data["data"]
                    for tel_code in sorted(beam_data):
                        beam = beam_data[tel_code]
                        theta = beam["theta"]
                        pattern = beam["pattern"]
                        for i in range(len(theta)):
                            row = [tel_code, theta[i], pattern[i]]
                            f.write('\t'.join(map(str, row)) + '\n')
                
                elif key == "mollweide_tracks":
                    headers = ["Time (UTC)", "Telescope", "Longitude (deg)", "Latitude (deg)"]
                    f.write('\t'.join(headers) + '\n')
                    scans_data = data["data"]
                    for scan_name in sorted(scans_data):
                        scan = target.get_scans().get(scan_name)
                        if not scan:
                            logger.debug(f"Scan '{scan_name}' not found, skipping")
                            continue
                        src = scan.get_source(observation=target)
                        src_name_local = src.name if src else None
                        if not src_name_local:
                            logger.debug(f"No source name for scan '{scan_name}', skipping")
                            continue
                        scan_times = times.get(src_name_local, {}).get(scan_name, []) if times else []
                        tels_dict = scans_data[scan_name]
                        for tel_code in sorted(tels_dict):
                            tracks = tels_dict[tel_code]
                            for i, t in enumerate(scan_times):
                                row = [t.isot, tel_code, tracks[i, 0], tracks[i, 1]]
                                f.write('\t'.join(map(str, row)) + '\n')
                
                elif key == "telescope_positions":
                    headers = ["Time (UTC)", "Telescope", "X (m)", "Y (m)", "Z (m)"]
                    f.write('\t'.join(headers) + '\n')
                    scans_data = data["data"]
                    for scan_name in sorted(scans_data):
                        scan = target.get_scans().get(scan_name)
                        if not scan:
                            logger.debug(f"Scan '{scan_name}' not found, skipping")
                            continue
                        src = scan.get_source(observation=target)
                        src_name_local = src.name if src else None
                        if not src_name_local:
                            logger.debug(f"No source name for scan '{scan_name}', skipping")
                            continue
                        scan_times = times.get(src_name_local, {}).get(scan_name, []) if times else []
                        tels_dict = scans_data[scan_name]
                        for tel_code in sorted(tels_dict):
                            pos = tels_dict[tel_code]
                            for i, t in enumerate(scan_times):
                                row = [t.isot, tel_code, pos[i, 0], pos[i, 1], pos[i, 2]]
                                f.write('\t'.join(map(str, row)) + '\n')
                
                else:
                    logger.warning(f"Unsupported calc_type for TXT export: {calc_type}")
                    return

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