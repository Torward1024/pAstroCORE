# pastrocore/gui/p_dialog_edit_scan.py
from PySide6.QtWidgets import QDialog, QMessageBox, QHeaderView
from PySide6.QtCore import Slot, Qt, QDateTime
from PySide6.QtGui import QStandardItemModel, QStandardItem, QDoubleValidator, QIcon
from .ui_dialog_edit_scan import Ui_ScanEditorDialog
from pastrocore.base.observation import Observation
from pastrocore.base.scans import Scan
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from common.utils.logging_setup import logger
from astropy.time import Time
from datetime import timedelta
import uuid
import re

class ScanEditorDialog(QDialog):
    """Dialog for creating or editing a scan in an observation."""

    def __init__(self, observation: Observation, manipulator: ScheduleManipulator, scan: Scan = None, parent=None):
        """Initialize the ScanEditorDialog.

        Args:
            observation (Observation): The observation containing the scan.
            manipulator (ScheduleManipulator): Manipulator for data operations.
            scan (Scan, optional): The Scan object to edit. If None, creates a new scan.
            parent (QWidget, optional): Parent widget.
        """
        super().__init__(parent)
        self.ui = Ui_ScanEditorDialog()
        self.ui.setupUi(self)
        self.observation = observation
        self.manipulator = manipulator
        self.scan = scan
        self.is_new = scan is None

        self.active_icon = QIcon(":/icons/active_icon.svg")
        self.inactive_icon = QIcon(":/icons/inactive_icon.svg")

        self.telescopes_model = QStandardItemModel()
        self.frequencies_model = QStandardItemModel()
        self.setup_ui()
        self.setup_connections()
        self.load_data()

    def setup_ui(self):
        """Set up the UI components."""
        self.ui.tab_telescopes.setModel(self.telescopes_model)
        self.telescopes_model.setHorizontalHeaderLabels(["#", " ", " ", "Name"])
        self.ui.tab_telescopes.setAlternatingRowColors(True)
        self.ui.tab_telescopes.setSortingEnabled(False)
        self.ui.tab_telescopes.verticalHeader().setVisible(False)
        self.ui.tab_telescopes.setColumnWidth(0, 24)
        self.ui.tab_telescopes.setColumnWidth(1, 24)  # Check column
        self.ui.tab_telescopes.setColumnWidth(2, 24)  # Active column
        self.ui.tab_telescopes.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)

        self.ui.tab_frequencies.setModel(self.frequencies_model)
        self.frequencies_model.setHorizontalHeaderLabels(["#", " ", " ", "Frequency (MHz)", "Bandwidth (MHz)", "Polarizations"])
        self.ui.tab_frequencies.setAlternatingRowColors(True)
        self.ui.tab_frequencies.setSortingEnabled(False)
        self.ui.tab_frequencies.verticalHeader().setVisible(False)
        self.ui.tab_frequencies.setColumnWidth(0, 24)
        self.ui.tab_frequencies.setColumnWidth(1, 24)  # Check column
        self.ui.tab_frequencies.setColumnWidth(2, 24)  # Active column
        self.ui.tab_frequencies.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.ui.tab_frequencies.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.ui.tab_frequencies.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)

        self.ui.startTimeEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.ui.endTimeEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.ui.endTimeEdit.setReadOnly(False)
        validator = QDoubleValidator(1.0, 2147483647.0, 2, self)
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.ui.durationEdit.setValidator(validator)

    def setup_connections(self):
        """Connect UI signals to slots."""
        self.ui.pushButton.clicked.connect(self.accept)
        self.ui.pushButton_2.clicked.connect(self.reject)
        self.ui.btnSelectAllTelescopes.clicked.connect(self.select_all_telescopes)
        self.ui.btnClearAllTelescopes.clicked.connect(self.clear_all_telescopes)
        self.ui.btnSelectAllFrequencies.clicked.connect(self.select_all_frequencies)
        self.ui.btnClearAllFrequencies.clicked.connect(self.clear_all_frequencies)
        self.ui.chk_offsource.stateChanged.connect(self.offsource_changed)
        self.ui.startTimeEdit.dateTimeChanged.connect(self.adjust_duration_from_start)
        self.ui.endTimeEdit.dateTimeChanged.connect(self.adjust_duration_from_end)
        self.ui.durationEdit.textChanged.connect(self.adjust_end_time)
        self.telescopes_model.itemChanged.connect(self.debug_item_changed)
        self.frequencies_model.itemChanged.connect(self.debug_item_changed)

    def load_data(self):
        """Load scan data into the dialog fields."""
        if self.is_new:
            latest_end_time = None
            latest_duration = None
            try:
                scans = self.manipulator.inspect(obj=self.observation.get_scans(), get_all=None)
                if isinstance(scans, dict) and scans:
                    for scan_name, scan_obj in scans.items():
                        scan_attrs = self.manipulator.inspect(obj=scan_obj, get=["start", "duration"])
                        scan_start = scan_attrs["start"]
                        scan_duration = scan_attrs["duration"]
                        logger.debug(f"Processing scan '{scan_name}': start={scan_start.isot}, duration={scan_duration}")
                        scan_end = scan_start + timedelta(seconds=scan_duration)
                        if latest_end_time is None or scan_end > latest_end_time:
                            latest_end_time = scan_end
                            latest_duration = scan_duration
            except Exception as e:
                logger.error(f"Exception while inspecting scans: {str(e)}")

            start_time = latest_end_time if latest_end_time else Time.now()
            duration = latest_duration if latest_duration else 60.0
            self.scan = Scan(
                name=f"scan_{uuid.uuid4().hex[:32]}",
                start=start_time,
                duration=duration,
                source=None,
                telescopes=[],
                frequencies=[],
                is_off_source=False,
                isactive=True,
                observation=self.observation
            )
            self.setWindowTitle("Add Scan")
            logger.debug("Creating new scan with default parameters")
        else:
            self.setWindowTitle(f"Edit Scan")
            logger.debug(f"Editing existing scan '{self.scan.name}'")

        self.load_sources()
        self.load_telescopes()
        self.load_frequencies()

        self.ui.startTimeEdit.setDateTime(self.scan.start.to_datetime())
        self.ui.durationEdit.setText(f"{self.scan.duration:.2f}")
        self.ui.chk_offsource.setChecked(self.scan.is_off_source)
        self.ui.chk_active.setChecked(self.scan.isactive)
        self.adjust_end_time()

        logger.info(f"Loaded scan '{self.scan.name}' into editor dialog")

    def load_sources(self):
        """Populate the source combo box with available sources."""
        self.ui.sourceCombo.clear()
        self.ui.sourceCombo.addItem("Select Source", None)
        try:
            sources = self.manipulator.inspect(self.observation.get_sources(), get_all=None)
            if isinstance(sources, dict):
                for name, source in sources.items():
                    is_active = self.manipulator.inspect(source, get="isactive")
                    icon = self.active_icon if is_active else self.inactive_icon
                    self.ui.sourceCombo.addItem(icon, name, source)
                    if self.scan and self.scan.source == source:
                        self.ui.sourceCombo.setCurrentText(name)
                logger.debug(f"Populated {len(sources)} sources into source combo")
        except Exception as e:
            logger.error(f"Exception while populating sources: {str(e)}")

        if self.scan and self.scan.is_off_source:
            self.ui.sourceCombo.setEnabled(False)
        else:
            self.ui.sourceCombo.setEnabled(True)

    def load_telescopes(self):
        """Populate the telescopes table with available telescopes."""
        self.telescopes_model.removeRows(0, self.telescopes_model.rowCount())
        try:
            telescopes = self.manipulator.inspect(self.observation.get_telescopes(), get_all=None)
            if isinstance(telescopes, dict):
                idx = 1
                for name, telescope in telescopes.items():
                    is_active = self.manipulator.inspect(telescope, get="isactive")
                    icon = self.active_icon if is_active else self.inactive_icon
                    check_item = QStandardItem()
                    check_item.setCheckable(True)
                    check_item.setCheckState(Qt.Checked if self.scan and telescope in self.scan.telescopes else Qt.Unchecked)
                    active_item = QStandardItem()
                    active_item.setIcon(icon)
                    active_item.setTextAlignment(Qt.AlignCenter)
                    row = [
                        QStandardItem(str(idx)),
                        check_item,
                        active_item,
                        QStandardItem(name)
                    ]
                    row[3].setData(telescope, Qt.UserRole)
                    for item in row:
                        item.setEditable(False)
                    self.telescopes_model.appendRow(row)
                    idx += 1
                logger.debug(f"Populated {len(telescopes)} telescopes into table")
        except Exception as e:
            logger.error(f"Exception while populating telescopes: {str(e)}")

    def load_frequencies(self):
        """Populate the frequencies table with available frequencies."""
        self.frequencies_model.removeRows(0, self.frequencies_model.rowCount())
        try:
            frequencies = self.manipulator.inspect(self.observation.get_frequencies(), get_all=None)
            if isinstance(frequencies, dict):
                idx = 1
                for name, frequency in frequencies.items():
                    is_active = self.manipulator.inspect(frequency, get="isactive")
                    icon = self.active_icon if is_active else self.inactive_icon
                    check_item = QStandardItem()
                    check_item.setCheckable(True)
                    check_item.setCheckState(Qt.Checked if self.scan and frequency in self.scan.frequencies else Qt.Unchecked)
                    active_item = QStandardItem()
                    active_item.setIcon(icon)
                    active_item.setTextAlignment(Qt.AlignCenter)
                    freq_attrs = self.manipulator.inspect(frequency, get=["frequency", "bandwidth", "polarizations"])
                    row = [
                        QStandardItem(str(idx)),
                        check_item,
                        active_item,
                        QStandardItem(f"{freq_attrs['frequency']:.2f}"),
                        QStandardItem(f"{freq_attrs['bandwidth']:.2f}"),
                        QStandardItem(", ".join(freq_attrs["polarizations"]))
                    ]
                    row[3].setData(frequency, Qt.UserRole)
                    for item in row:
                        item.setEditable(False)
                    self.frequencies_model.appendRow(row)
                    idx += 1
                logger.debug(f"Populated {len(frequencies)} frequencies into table")
        except Exception as e:
            logger.error(f"Exception while populating frequencies: {str(e)}")

    @Slot()
    def select_all_telescopes(self):
        """Select all telescopes in the table."""
        for row in range(self.telescopes_model.rowCount()):
            check_item = self.telescopes_model.item(row, 1)
            check_item.setCheckState(Qt.Checked)
        logger.debug("Selected all telescopes")

    @Slot()
    def clear_all_telescopes(self):
        """Clear all telescope selections in the table."""
        for row in range(self.telescopes_model.rowCount()):
            check_item = self.telescopes_model.item(row, 1)
            check_item.setCheckState(Qt.Unchecked)
        logger.debug("Cleared all telescope selections")

    @Slot()
    def select_all_frequencies(self):
        """Select all frequencies in the table."""
        for row in range(self.frequencies_model.rowCount()):
            check_item = self.frequencies_model.item(row, 1)
            check_item.setCheckState(Qt.Checked)
        logger.debug("Selected all frequencies")

    @Slot()
    def clear_all_frequencies(self):
        """Clear all frequency selections in the table."""
        for row in range(self.frequencies_model.rowCount()):
            check_item = self.frequencies_model.item(row, 1)
            check_item.setCheckState(Qt.Unchecked)
        logger.debug("Cleared all frequency selections")

    @Slot(int)
    def offsource_changed(self, state):
        """Handle change in off-source checkbox state."""
        is_off_source = state == Qt.Checked
        self.ui.sourceCombo.setEnabled(not is_off_source)
        logger.debug(f"Off-source state changed to: {is_off_source}")

    @Slot()
    def debug_item_changed(self, item):
        """Log changes to table items (for debugging)."""
        if item.column() == 1:
            logger.debug(f"Item changed: row={item.row()}, checkState={item.checkState()}")

    @Slot()
    def adjust_duration_from_start(self):
        """Adjust duration based on start time change."""
        try:
            start_qdt = self.ui.startTimeEdit.dateTime()
            end_qdt = self.ui.endTimeEdit.dateTime()
            duration = start_qdt.secsTo(end_qdt)
            if duration <= 0:
                duration = 1
                end_qdt = start_qdt.addSecs(1)
                self.ui.endTimeEdit.blockSignals(True)
                self.ui.endTimeEdit.setDateTime(end_qdt)
                self.ui.endTimeEdit.blockSignals(False)
            self.ui.durationEdit.blockSignals(True)
            self.ui.durationEdit.setText(f"{duration:.2f}")
            self.ui.durationEdit.blockSignals(False)
            logger.debug(f"Adjusted duration from start time: {duration}s")
        except Exception as e:
            logger.error(f"Error adjusting duration from start: {str(e)}")

    @Slot()
    def adjust_duration_from_end(self):
        """Adjust duration based on end time change."""
        try:
            start_qdt = self.ui.startTimeEdit.dateTime()
            end_qdt = self.ui.endTimeEdit.dateTime()
            duration = start_qdt.secsTo(end_qdt)
            if duration <= 0:
                duration = 1
                end_qdt = start_qdt.addSecs(1)
                self.ui.endTimeEdit.blockSignals(True)
                self.ui.endTimeEdit.setDateTime(end_qdt)
                self.ui.endTimeEdit.blockSignals(False)
            self.ui.durationEdit.blockSignals(True)
            self.ui.durationEdit.setText(f"{duration:.2f}")
            self.ui.durationEdit.blockSignals(False)
            logger.debug(f"Adjusted duration from end time: {duration}s")
        except Exception as e:
            logger.error(f"Error adjusting duration from end: {str(e)}")

    @Slot()
    def adjust_end_time(self):
        """Adjust end time based on duration change."""
        try:
            start_qdt = self.ui.startTimeEdit.dateTime()
            duration_text = self.ui.durationEdit.text().strip()
            duration_text = re.sub(r'[^\d.]', '', duration_text)
            if not duration_text:
                raise ValueError("Duration is empty")
            duration = float(duration_text)
            if duration <= 0:
                duration = 1
                self.ui.durationEdit.blockSignals(True)
                self.ui.durationEdit.setText(f"{duration:.2f}")
                self.ui.durationEdit.blockSignals(False)
            end_qdt = start_qdt.addSecs(int(duration))
            self.ui.endTimeEdit.blockSignals(True)
            self.ui.endTimeEdit.setDateTime(end_qdt)
            self.ui.endTimeEdit.blockSignals(False)
            logger.debug(f"Adjusted end time to {end_qdt.toString(Qt.ISODate)} (start + duration {duration}s)")
        except ValueError as e:
            end_qdt = start_qdt.addSecs(1)
            self.ui.endTimeEdit.blockSignals(True)
            self.ui.endTimeEdit.setDateTime(end_qdt)
            self.ui.endTimeEdit.blockSignals(False)
            self.ui.durationEdit.blockSignals(True)
            self.ui.durationEdit.setText("1.00")
            self.ui.durationEdit.blockSignals(False)
            logger.debug(f"Adjusted end time to start + 1s (invalid duration: {str(e)})")
        except Exception as e:
            logger.error(f"Error adjusting end time: {str(e)}")

    def _check_scan_conditions(self):
        """Check if scan conditions are met for activation."""
        try:
            active_telescopes = sum(1 for row in range(self.telescopes_model.rowCount())
                                    if self.telescopes_model.item(row, 1).checkState() == Qt.Checked and
                                    self.telescopes_model.item(row, 2).icon().cacheKey() == self.active_icon.cacheKey())
            active_frequencies = sum(1 for row in range(self.frequencies_model.rowCount())
                                     if self.frequencies_model.item(row, 1).checkState() == Qt.Checked and
                                     self.frequencies_model.item(row, 2).icon().cacheKey() == self.active_icon.cacheKey())
            source = self.ui.sourceCombo.currentData()
            source_active = self.manipulator.inspect(source, get="isactive") if source else True
            min_telescopes = 1 if self.observation.get_observation_type() == 'SINGLE_DISH' else 2
            return (active_telescopes >= min_telescopes and active_frequencies >= 1 and
                    (self.ui.chk_offsource.isChecked() or source_active))
        except Exception as e:
            logger.error(f"Exception while checking scan conditions: {str(e)}")
            return False

    def get_scan_object(self) -> Scan:
        """Retrieve the modified Scan object from the dialog."""
        start_time = Time(self.ui.startTimeEdit.dateTime().toPython())
        start_time = start_time.to_datetime().replace(microsecond=0)
        start_time = Time(start_time)
        logger.debug(f"Retrieved start time from dialog: {start_time.isot}")

        try:
            duration_text = self.ui.durationEdit.text().strip()
            # Remove any non-numeric characters except decimal point
            duration_text = re.sub(r'[^\d.]', '', duration_text)
            if not duration_text:
                raise ValueError("Duration is empty")
            duration = float(duration_text)
            if duration <= 0:
                raise ValueError("Duration must be positive")
        except ValueError as e:
            logger.error(f"Invalid duration: {str(e)}")
            raise ValueError(f"Invalid duration: {str(e)}")

        end_time = self.ui.endTimeEdit.dateTime()
        calculated_duration = self.ui.startTimeEdit.dateTime().secsTo(end_time)
        if abs(calculated_duration - duration) > 1:  # Allow small discrepancies due to rounding
            logger.warning(f"Duration ({duration}s) and endTime ({end_time.toString(Qt.ISODate)}) mismatch, using duration")

        is_off_source = self.ui.chk_offsource.isChecked()
        source = None if is_off_source else self.ui.sourceCombo.currentData()

        telescopes = []
        for row in range(self.telescopes_model.rowCount()):
            telescope_item = self.telescopes_model.item(row, 3)
            check_item = self.telescopes_model.item(row, 1)
            telescope = telescope_item.data(Qt.UserRole) if telescope_item else None
            if check_item.checkState() == Qt.Checked and telescope:
                telescopes.append(telescope)
        logger.debug(f"Selected telescopes from model: {[t.name for t in telescopes]}")

        frequencies = []
        for row in range(self.frequencies_model.rowCount()):
            frequency_item = self.frequencies_model.item(row, 3)
            check_item = self.frequencies_model.item(row, 1)
            frequency = frequency_item.data(Qt.UserRole) if frequency_item else None
            if check_item.checkState() == Qt.Checked and frequency:
                frequencies.append(frequency)
        logger.debug(f"Selected frequencies from model: {[f.name for f in frequencies]}")

        if not telescopes:
            logger.error("No telescopes selected")
            raise ValueError("At least one telescope must be selected")
        if not frequencies:
            logger.error("No frequencies selected")
            raise ValueError("At least one frequency must be selected")
        if not is_off_source and not source:
            logger.error("No source selected")
            raise ValueError("A source must be selected unless OFF SOURCE is checked")

        isactive = self.ui.chk_active.isChecked()
        conditions_met = self._check_scan_conditions()
        if isactive and not conditions_met:
            logger.warning("Scan marked as active but conditions not met")
            QMessageBox.warning(self, "Warning",
                                "Scan is marked as active, but conditions are not met:\n"
                                f"- At least {1 if self.observation.get_observation_type() == 'SINGLE_DISH' else 2} active telescopes required\n"
                                "- At least 1 active frequency required\n"
                                "- Source must be active (unless OFF SOURCE)")

        scan_data = {
            "name": self.scan.name,
            "start": start_time,
            "duration": duration,
            "source": source,
            "telescopes": telescopes,
            "frequencies": frequencies,
            "is_off_source": is_off_source,
            "isactive": isactive
        }

        self.scan.set(scan_data)
        logger.debug(f"Updated Scan object '{self.scan.name}' with params: {scan_data}")
        return self.scan

    def accept(self):
        """Validate and accept the dialog."""
        try:
            self.get_scan_object()
            super().accept()
            logger.info(f"Validated and saved scan data for '{self.scan.name}'")
        except ValueError as ve:
            logger.error(f"Validation error: {str(ve)}")
            QMessageBox.critical(self, "Error", f"Invalid input: {str(ve)}")
        except Exception as e:
            logger.error(f"Unexpected error while saving scan: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save scan: {str(e)}")