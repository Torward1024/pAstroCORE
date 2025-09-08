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
import pastrocore.gui.rc_icons

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

        # Icons for active/inactive status
        self.active_icon = QIcon(":/icons/active_icon.svg")
        self.inactive_icon = QIcon(":/icons/inactive_icon.svg")

        # Initialize models for QTableView
        self.telescopes_model = QStandardItemModel()
        self.frequencies_model = QStandardItemModel()
        self.ui.tab_telescopes.setModel(self.telescopes_model)
        self.ui.tab_frequencies.setModel(self.frequencies_model)

        # Configure telescopes table
        self.telescopes_model.setHorizontalHeaderLabels(["#", " ", " ", "Name"])
        self.ui.tab_telescopes.setAlternatingRowColors(True)
        self.ui.tab_telescopes.setSortingEnabled(False)
        self.ui.tab_telescopes.verticalHeader().setVisible(False)
        self.ui.tab_telescopes.setColumnWidth(0, 24)
        self.ui.tab_telescopes.setColumnWidth(1, 24)  # Check column
        self.ui.tab_telescopes.setColumnWidth(2, 24)  # Active column
        self.ui.tab_telescopes.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)

        # Configure frequencies table
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

        # Connect buttons
        self.ui.pushButton.clicked.connect(self.accept)
        self.ui.pushButton_2.clicked.connect(self.reject)
        self.ui.btnSelectAllTelescopes.clicked.connect(self.select_all_telescopes)
        self.ui.btnClearAllTelescopes.clicked.connect(self.clear_all_telescopes)
        self.ui.btnSelectAllFrequencies.clicked.connect(self.select_all_frequencies)
        self.ui.btnClearAllFrequencies.clicked.connect(self.clear_all_frequencies)

        # Connect checkbox signals
        self.ui.chk_offsource.stateChanged.connect(self.offsource_changed)

        # Connect model signals for debugging
        self.telescopes_model.itemChanged.connect(self.debug_item_changed)
        self.frequencies_model.itemChanged.connect(self.debug_item_changed)

        # Time and duration setup
        self.ui.startTimeEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.ui.endTimeEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.ui.endTimeEdit.setReadOnly(False)  # Ensure editable
        validator = QDoubleValidator(1.0, 2147483647.0, 0, self)  # Allow integers up to 2^31 - 1
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.ui.durationEdit.setValidator(validator)

        # Connect signals for time synchronization
        self.ui.startTimeEdit.dateTimeChanged.connect(self.update_from_start_or_duration)
        self.ui.durationEdit.textChanged.connect(self.update_from_start_or_duration)
        self.ui.endTimeEdit.dateTimeChanged.connect(self.update_from_end_time)

        self.selected_telescopes = set()
        self.selected_frequencies = set()

        # Log available telescopes
        telescopes = self.observation.get_telescopes().get_items()
        logger.debug(f"Available telescopes in observation: {telescopes}")

        # Populate UI
        self._populate_sources()
        self._populate_telescopes()
        self._populate_frequencies()

        # Set start time and duration for new scans based on the last scan's end time and duration
        if self.is_new:
            scans_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_scans(),
                "attributes": {"get_all": None}
            })
            if scans_response["status"] and isinstance(scans_response["result"], dict) and scans_response["result"]:
                # Find the last scan by start time + duration
                latest_end_time = None
                latest_duration = None
                for scan_name, scan_obj in scans_response["result"].items():
                    scan_attrs_response = self.manipulator.process_request({
                        "operation": "inspect",
                        "obj": scan_obj,
                        "attributes": {"get": ["start", "duration"]}
                    })
                    if scan_attrs_response["status"]:
                        scan_start = scan_attrs_response["result"]["start"]
                        scan_duration = scan_attrs_response["result"]["duration"]
                        logger.debug(f"Processing scan '{scan_name}': start={scan_start.isot}, duration={scan_duration}")
                        try:
                            # Calculate end time using TimeDelta
                            scan_end = scan_start + timedelta(seconds=scan_duration)
                            logger.debug(f"Calculated end time for scan '{scan_name}': {scan_end.isot}")
                            if latest_end_time is None or scan_end > latest_end_time:
                                latest_end_time = scan_end
                                latest_duration = scan_duration
                        except Exception as e:
                            logger.error(f"Error calculating end time for scan '{scan_name}': {str(e)}")
                            continue
                if latest_end_time and latest_duration is not None:
                    try:
                        start_dt = latest_end_time.to_datetime()
                        start_qdt = QDateTime.fromMSecsSinceEpoch(int(start_dt.timestamp() * 1000))
                        self.ui.startTimeEdit.setDateTime(start_qdt)
                        logger.debug(f"Set start time for new scan to end of latest scan: {start_dt}")
                        self.ui.durationEdit.setText(str(int(latest_duration)))
                        self.update_from_start_or_duration()  # Update endTime immediately
                        logger.debug(f"Set duration for new scan to match latest scan: {latest_duration}")
                    except Exception as e:
                        logger.error(f"Error converting latest end time to QDateTime: {str(e)}")
                        self._set_default_time()
                else:
                    self._set_default_time()
            else:
                self._set_default_time()
        else:
            self._load_scan_data()

        self.ui.chk_active.setChecked(self._check_scan_conditions())
        logger.debug(f"Set chk_active for {'new scan' if self.is_new else f'scan {self.scan.name}'} based on conditions: {self.ui.chk_active.isChecked()}")
        logger.debug(f"Initialized ScanEditorDialog for {'new scan' if self.is_new else f'scan {self.scan.name}'} in observation '{self.observation.code}'")

    def _set_default_time(self):
        """Set default start time to current and duration to 600s, update endTime."""
        current_time = QDateTime.currentDateTime()
        self.ui.startTimeEdit.setDateTime(current_time)
        self.ui.durationEdit.setText("600")
        self.update_from_start_or_duration()
        logger.debug(f"No scans available, set start time to current: {current_time.toString(Qt.ISODate)}, duration to default: 600")

    def debug_item_changed(self, item):
        """Debug signal for item changes in the model."""
        row = item.row()
        col = item.column()
        if col == 1:  # Check column
            model = item.model()
            name_item = model.item(row, 3) if model == self.telescopes_model else model.item(row, 3)
            if name_item and name_item.text():
                name = name_item.text()
            else:
                logger.error(f"Failed to retrieve name for row {row} in {'telescopes' if model == self.telescopes_model else 'frequencies'} model")
                name = "Unknown"
            check_state = item.checkState()
            logger.debug(f"Item changed: {name}, check_state={check_state}")
            target_set = self.selected_telescopes if model == self.telescopes_model else self.selected_frequencies
            if check_state == Qt.Checked:
                target_set.add(name)
            else:
                target_set.discard(name)
            logger.debug(f"Current selected {'telescopes' if model == self.telescopes_model else 'frequencies'}: {target_set}")
            # Update chk_active when selection changes
            self.ui.chk_active.setChecked(self._check_scan_conditions())
            logger.debug(f"Updated chk_active after selection change: {self.ui.chk_active.isChecked()}")

    def _populate_sources(self):
        """Populate the source combo box with available sources."""
        sources_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation.get_sources(),
            "attributes": {"get_all": None}
        })
        logger.debug(f"Sources response: {sources_response}")
        self.ui.sourceCombo.clear()
        if sources_response["status"] and isinstance(sources_response["result"], dict) and sources_response["result"]:
            for name, source in sources_response["result"].items():
                is_active_response = self.manipulator.process_request({
                    "operation": "inspect",
                    "obj": source,
                    "attributes": {"get": "isactive"}
                })
                is_active = is_active_response["status"] and bool(is_active_response["result"])
                logger.debug(f"Source {name} isactive: {is_active}")
                self.ui.sourceCombo.addItem(name, source)  # Store Source object as user data
                if not is_active:
                    index = self.ui.sourceCombo.findData(source)
                    self.ui.sourceCombo.model().item(index).setEnabled(False)
            self.ui.sourceCombo.setCurrentIndex(0)
            self.ui.chk_offsource.setChecked(False)
            self.ui.sourceCombo.setEnabled(True)
            logger.debug(f"Populated {len(sources_response['result'])} sources, selected first: {self.ui.sourceCombo.currentText()}")
        else:
            self.ui.chk_offsource.setChecked(True)
            self.ui.sourceCombo.setEnabled(False)
            logger.debug("No sources available, set OFF SOURCE to True and disabled sourceCombo")

    def _populate_telescopes(self):
        """Populate the telescopes table with available telescopes, all checked by default."""
        self.telescopes_model.removeRows(0, self.telescopes_model.rowCount())
        telescopes_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation.get_telescopes(),
            "attributes": {"get_all": None}
        })
        logger.debug(f"Telescopes response: {telescopes_response}")
        if telescopes_response["status"] and isinstance(telescopes_response["result"], dict):
            idx = 1
            for name, telescope in telescopes_response["result"].items():
                is_active_response = self.manipulator.process_request({
                    "operation": "inspect",
                    "obj": telescope,
                    "attributes": {"get": "isactive"}
                })
                is_active = is_active_response["status"] and bool(is_active_response["result"])
                logger.debug(f"Telescope {name} isactive: {is_active}")
                row = [
                    QStandardItem(str(idx)),  # #
                    QStandardItem(),  # Check
                    QStandardItem(),  # Active
                    QStandardItem(name)  # Name
                ]
                row[1].setCheckable(True)
                row[1].setCheckState(Qt.Checked)  # Check by default
                row[2].setIcon(self.active_icon if is_active else self.inactive_icon)
                row[2].setToolTip("Active" if is_active else "Inactive")
                row[2].setTextAlignment(Qt.AlignCenter)
                for item in row:
                    item.setEditable(False)
                row[0].setData(telescope, Qt.UserRole)  # Store Telescope/SpaceTelescope object
                row[3].setData(telescope, Qt.UserRole)
                self.telescopes_model.appendRow(row)
                self.selected_telescopes.add(name)  # Add to selected set
                logger.debug(f"Added telescope: {name}, checkable: True, active: {is_active}, checked: True")
                idx += 1
            logger.debug(f"Populated {self.telescopes_model.rowCount()} telescopes")
        else:
            logger.error(f"Failed to populate telescopes: {telescopes_response.get('error', 'Unknown error')}")

    def _populate_frequencies(self):
        """Populate the frequencies table with available frequencies, all checked by default."""
        self.frequencies_model.removeRows(0, self.frequencies_model.rowCount())
        frequencies_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation.get_frequencies(),
            "attributes": {"get_all": None}
        })
        logger.debug(f"Frequencies response: {frequencies_response}")
        if frequencies_response["status"] and isinstance(frequencies_response["result"], dict):
            idx = 1
            for name, if_obj in frequencies_response["result"].items():
                freq_response = self.manipulator.process_request({
                    "operation": "inspect",
                    "obj": if_obj,
                    "attributes": {"get": "frequency"}
                })
                frequency = freq_response["result"] if freq_response["status"] else "N/A"
                is_active_response = self.manipulator.process_request({
                    "operation": "inspect",
                    "obj": if_obj,
                    "attributes": {"get": "isactive"}
                })
                is_active = is_active_response["status"] and bool(is_active_response["result"])
                logger.debug(f"Frequency {name} isactive: {is_active}")
                bandwidth_response = self.manipulator.process_request({
                    "operation": "inspect",
                    "obj": if_obj,
                    "attributes": {"get": "bandwidth"}
                })
                bandwidth = bandwidth_response["result"] if bandwidth_response["status"] else "N/A"
                polarizations_response = self.manipulator.process_request({
                    "operation": "inspect",
                    "obj": if_obj,
                    "attributes": {"get": "polarizations"}
                })
                polarizations = ", ".join(polarizations_response["result"]) if polarizations_response["status"] and polarizations_response["result"] else "N/A"
                row = [
                    QStandardItem(str(idx)),  # #
                    QStandardItem(),  # Check
                    QStandardItem(),  # Active
                    QStandardItem(f"{float(frequency):.0f}" if isinstance(frequency, (int, float)) else str(frequency)),  # Frequency
                    QStandardItem(f"{float(bandwidth):.0f}" if isinstance(bandwidth, (int, float)) else str(bandwidth)),  # Bandwidth
                    QStandardItem(polarizations)  # Polarizations
                ]
                row[1].setCheckable(True)
                row[1].setCheckState(Qt.Checked)  # Check by default
                row[2].setIcon(self.active_icon if is_active else self.inactive_icon)
                row[2].setToolTip("Active" if is_active else "Inactive")
                row[2].setTextAlignment(Qt.AlignCenter)
                for item in row:
                    item.setEditable(False)
                row[0].setData(if_obj, Qt.UserRole)  # Store IF object
                row[3].setData(if_obj, Qt.UserRole)
                self.frequencies_model.appendRow(row)
                self.selected_frequencies.add(name)  # Add to selected set
                logger.debug(f"Added frequency: {name}, checkable: True, active: {is_active}, checked: True")
                idx += 1
            logger.debug(f"Populated {self.frequencies_model.rowCount()} frequencies")
        else:
            logger.error(f"Failed to populate frequencies: {frequencies_response.get('error', 'Unknown error')}")

    def _check_scan_conditions(self):
        """Check if scan conditions for activation are met (2 active telescopes, 1 active frequency, active source)."""
        active_telescopes = []
        for row in range(self.telescopes_model.rowCount()):
            telescope_item = self.telescopes_model.item(row, 3)
            check_item = self.telescopes_model.item(row, 1)
            active_item = self.telescopes_model.item(row, 2)
            telescope = telescope_item.data(Qt.UserRole) if telescope_item else None
            is_checked = check_item.checkState() == Qt.Checked if check_item else False
            is_active = active_item.toolTip() == "Active" if active_item else False
            if is_checked and is_active and telescope:
                active_telescopes.append(telescope)
        logger.debug(f"Active and selected telescopes: {[t.name for t in active_telescopes]}")

        active_frequencies = []
        for row in range(self.frequencies_model.rowCount()):
            frequency_item = self.frequencies_model.item(row, 3)
            check_item = self.frequencies_model.item(row, 1)
            active_item = self.frequencies_model.item(row, 2)
            frequency = frequency_item.data(Qt.UserRole) if frequency_item else None
            is_checked = check_item.checkState() == Qt.Checked if check_item else False
            is_active = active_item.toolTip() == "Active" if active_item else False
            if is_checked and is_active and frequency:
                active_frequencies.append(frequency)
        logger.debug(f"Active and selected frequencies: {[f.name for f in active_frequencies]}")

        is_off_source = self.ui.chk_offsource.isChecked()
        source = self.ui.sourceCombo.currentData()
        source_active = True
        if not is_off_source and source:
            is_active_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": source,
                "attributes": {"get": "isactive"}
            })
            source_active = is_active_response["status"] and bool(is_active_response["result"])
        logger.debug(f"Source {source.name if source else None} active: {source_active}, is_off_source: {is_off_source}")

        conditions_met = (
            len(active_telescopes) >= (1 if self.observation.get_observation_type() == "SINGLE_DISH" else 2) and
            len(active_frequencies) >= 1 and
            (is_off_source or source_active)
        )
        logger.debug(f"Scan conditions check: telescopes={len(active_telescopes)} (>= {1 if self.observation.get_observation_type() == 'SINGLE_DISH' else 2}), "
                     f"frequencies={len(active_frequencies)} (>=1), "
                     f"source_active={source_active or is_off_source}, "
                     f"conditions_met={conditions_met}")
        return conditions_met

    def _load_scan_data(self):
        """Load existing scan data into the dialog."""
        try:
            start_time = self.scan.start
            start_dt = start_time.to_datetime()
            self.ui.startTimeEdit.setDateTime(QDateTime.fromMSecsSinceEpoch(int(start_dt.timestamp() * 1000)))
            logger.info(f"Set start time to: {start_dt}")
        except Exception as e:
            logger.error(f"Failed to load start time '{self.scan.start.isot}': {str(e)}")
            current_time = QDateTime.currentDateTime()
            self.ui.startTimeEdit.setDateTime(current_time)
            logger.info(f"Fallback to current time: {current_time.toString(Qt.ISODate)}")

        self.ui.durationEdit.setText(str(int(self.scan.duration)))
        logger.info(f"Set duration: {int(self.scan.duration)}")
        self.update_from_start_or_duration()  # Update endTime based on loaded data

        self.ui.chk_offsource.setChecked(self.scan.is_off_source)
        if self.scan.is_off_source:
            self.ui.sourceCombo.setEnabled(False)
            self.ui.sourceCombo.setCurrentIndex(-1)
            logger.info(f"Set OFF SOURCE to True, sourceCombo disabled")
        elif self.scan.source:
            index = self.ui.sourceCombo.findData(self.scan.source)
            if index >= 0:
                self.ui.sourceCombo.setCurrentIndex(index)
                self.ui.sourceCombo.setEnabled(True)
                logger.info(f"Set source: {self.scan.source.name}")
            else:
                logger.warning(f"Source '{self.scan.source.name}' not found in combo box")
                self.ui.sourceCombo.setCurrentIndex(0)
                self.ui.sourceCombo.setEnabled(True)

        self.ui.chk_active.setChecked(self._check_scan_conditions())
        logger.info(f"Set active status based on conditions: {self.ui.chk_active.isChecked()} (original scan.isactive: {self.scan.isactive})")

        self.selected_telescopes.clear()
        for row in range(self.telescopes_model.rowCount()):
            item = self.telescopes_model.item(row, 3)
            telescope = item.data(Qt.UserRole) if item else None
            check_item = self.telescopes_model.item(row, 1)
            if telescope in self.scan.telescopes:
                check_item.setCheckState(Qt.Checked)
                self.selected_telescopes.add(telescope.name)
                logger.info(f"Checked telescope: {telescope.name}, check_state: {check_item.checkState()}")
            else:
                check_item.setCheckState(Qt.Unchecked)
                logger.info(f"Unchecked telescope: {telescope.name if telescope else None}, check_state: {check_item.checkState()}")
            self.telescopes_model.dataChanged.emit(check_item.index(), check_item.index(), [Qt.CheckStateRole])
        self.ui.tab_telescopes.viewport().update()

        self.selected_frequencies.clear()
        for row in range(self.frequencies_model.rowCount()):
            item = self.frequencies_model.item(row, 3)
            frequency = item.data(Qt.UserRole) if item else None
            check_item = self.frequencies_model.item(row, 1)
            if frequency in self.scan.frequencies:
                check_item.setCheckState(Qt.Checked)
                self.selected_frequencies.add(frequency.name)
                logger.debug(f"Checked frequency: {frequency.name}, check_state: {check_item.checkState()}")
            else:
                check_item.setCheckState(Qt.Unchecked)
                logger.debug(f"Unchecked frequency: {frequency.name if frequency else None}, check_state: {check_item.checkState()}")
            self.frequencies_model.dataChanged.emit(check_item.index(), check_item.index(), [Qt.CheckStateRole])
        self.ui.tab_frequencies.viewport().update()

    @Slot()
    def select_all_telescopes(self):
        """Select all telescopes in the table."""
        for row in range(self.telescopes_model.rowCount()):
            check_item = self.telescopes_model.item(row, 1)
            name_item = self.telescopes_model.item(row, 3)
            if check_item and name_item:
                check_item.setCheckState(Qt.Checked)
                self.selected_telescopes.add(name_item.text())
                self.telescopes_model.dataChanged.emit(check_item.index(), check_item.index(), [Qt.CheckStateRole])
        self.ui.tab_telescopes.viewport().update()
        self.ui.chk_active.setChecked(self._check_scan_conditions())
        logger.debug("Selected all telescopes")

    @Slot()
    def clear_all_telescopes(self):
        """Clear selection of all telescopes in the table."""
        for row in range(self.telescopes_model.rowCount()):
            check_item = self.telescopes_model.item(row, 1)
            name_item = self.telescopes_model.item(row, 3)
            if check_item and name_item:
                check_item.setCheckState(Qt.Unchecked)
                self.selected_telescopes.discard(name_item.text())
                self.telescopes_model.dataChanged.emit(check_item.index(), check_item.index(), [Qt.CheckStateRole])
        self.ui.tab_telescopes.viewport().update()
        self.ui.chk_active.setChecked(self._check_scan_conditions())
        logger.debug("Cleared all telescopes selection")

    @Slot()
    def select_all_frequencies(self):
        """Select all frequencies in the table."""
        for row in range(self.frequencies_model.rowCount()):
            check_item = self.frequencies_model.item(row, 1)
            name_item = self.frequencies_model.item(row, 3)
            if check_item and name_item:
                check_item.setCheckState(Qt.Checked)
                self.selected_frequencies.add(name_item.text())
                self.frequencies_model.dataChanged.emit(check_item.index(), check_item.index(), [Qt.CheckStateRole])
        self.ui.tab_frequencies.viewport().update()
        self.ui.chk_active.setChecked(self._check_scan_conditions())
        logger.debug("Selected all frequencies")

    @Slot()
    def clear_all_frequencies(self):
        """Clear selection of all frequencies in the table."""
        for row in range(self.frequencies_model.rowCount()):
            check_item = self.frequencies_model.item(row, 1)
            name_item = self.frequencies_model.item(row, 3)
            if check_item and name_item:
                check_item.setCheckState(Qt.Unchecked)
                self.selected_frequencies.discard(name_item.text())
                self.frequencies_model.dataChanged.emit(check_item.index(), check_item.index(), [Qt.CheckStateRole])
        self.ui.tab_frequencies.viewport().update()
        self.ui.chk_active.setChecked(self._check_scan_conditions())
        logger.debug("Cleared all frequencies selection")

    @Slot(int)
    def offsource_changed(self, state):
        """Handle OFF SOURCE checkbox state change."""
        is_off_source = bool(state)
        self.ui.sourceCombo.setEnabled(not is_off_source)
        if is_off_source:
            self.ui.sourceCombo.setCurrentIndex(-1)
        logger.debug(f"OFF SOURCE changed to: {is_off_source}, sourceCombo enabled: {self.ui.sourceCombo.isEnabled()}, selected: {self.ui.sourceCombo.currentText()}")
        self.ui.chk_active.setChecked(self._check_scan_conditions())
        logger.debug(f"Updated chk_active after offsource change: {self.ui.chk_active.isChecked()}")

    @Slot()
    def update_from_start_or_duration(self):
        """Update endTime based on startTime and duration."""
        start_qdt = self.ui.startTimeEdit.dateTime()
        try:
            duration = float(self.ui.durationEdit.text())
            if duration <= 0:
                raise ValueError("Duration must be positive")
            end_dt = start_qdt.addSecs(int(duration))
            self.ui.endTimeEdit.blockSignals(True)  # Prevent recursive signals
            self.ui.endTimeEdit.setDateTime(end_dt)
            self.ui.endTimeEdit.blockSignals(False)
            logger.debug(f"Updated endTime from start/duration: {end_dt.toString(Qt.ISODate)}")
        except ValueError:
            logger.warning("Invalid duration during update, skipping endTime update")
            pass  # Don't update if invalid

    @Slot()
    def update_from_end_time(self):
        """Update duration based on startTime and endTime, validate end > start."""
        start_qdt = self.ui.startTimeEdit.dateTime()
        end_qdt = self.ui.endTimeEdit.dateTime()
        if end_qdt <= start_qdt:
            QMessageBox.warning(self, "Invalid Time", "End time must be after start time.")
            # Reset to previous valid (add duration or 1s if invalid)
            try:
                duration = float(self.ui.durationEdit.text())
                if duration <= 0:
                    raise ValueError
                end_qdt = start_qdt.addSecs(int(duration))
            except ValueError:
                end_qdt = start_qdt.addSecs(1)
            self.ui.endTimeEdit.blockSignals(True)
            self.ui.endTimeEdit.setDateTime(end_qdt)
            self.ui.endTimeEdit.blockSignals(False)
            logger.warning(f"End time invalid, reset to start + {int(duration) if duration > 0 else 1}s")
        duration = start_qdt.secsTo(end_qdt)
        self.ui.durationEdit.blockSignals(True)  # Prevent recursive signals
        self.ui.durationEdit.setText(str(duration))
        self.ui.durationEdit.blockSignals(False)
        logger.debug(f"Updated duration from endTime: {duration}s")

    def get_scan_data(self):
        """Retrieve scan data from the dialog."""
        start_time = Time(self.ui.startTimeEdit.dateTime().toPython())
        start_time = start_time.to_datetime().replace(microsecond=0)
        start_time = Time(start_time)
        logger.info(f"Retrieved start time from dialog: {start_time.isot}")

        try:
            duration = float(self.ui.durationEdit.text())
            if duration <= 0:
                raise ValueError("Duration must be positive")
        except ValueError as e:
            logger.error(f"Invalid duration: {str(e)}")
            raise ValueError("Duration must be a positive integer number")

        # Validate endTime consistency (though signals should keep it synced)
        end_time = self.ui.endTimeEdit.dateTime()
        calculated_duration = self.ui.startTimeEdit.dateTime().secsTo(end_time)
        if calculated_duration != int(duration):
            logger.warning(f"Duration ({duration}s) and endTime ({end_time.toString(Qt.ISODate)}) mismatch, using duration")
            # Prioritize duration as per spec

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
            "name": self.scan.name if not self.is_new else f"scan_{uuid.uuid4().hex[:32]}",
            "start": start_time,
            "duration": duration,
            "source": source,
            "telescopes": telescopes,
            "frequencies": frequencies,
            "is_off_source": is_off_source,
            "isactive": isactive,
            "observation": self.observation
        }
        logger.info(f"Collected scan data: name={scan_data['name']}, start={start_time.isot}, "
                    f"source={'OFF SOURCE' if is_off_source else source.name if source else None}, "
                    f"telescopes={[t.name for t in telescopes]}, frequencies={[f.name for f in frequencies]}")
        return scan_data

    @Slot()
    def accept(self):
        """Handle OK button click, validate scan data."""
        try:
            self.get_scan_data()
            super().accept()
        except ValueError as ve:
            logger.error(f"Validation error: {str(ve)}")
            QMessageBox.critical(self, "Error", str(ve))
        except Exception as e:
            logger.error(f"Exception while validating scan: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to validate scan: {str(e)}")