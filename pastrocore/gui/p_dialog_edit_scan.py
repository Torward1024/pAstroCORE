# pastrocore/gui/p_dialog_edit_scan.py
from PySide6.QtWidgets import QDialog, QMessageBox, QTableView, QHeaderView
from PySide6.QtCore import Slot, Qt, QDateTime
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIntValidator, QIcon
from .ui_dialog_edit_scan import Ui_ScanEditorDialog
from pastrocore.base.observation import Observation
from pastrocore.base.scans import Scan
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from common.utils.logging_setup import logger
from astropy.time import Time
from datetime import datetime
import uuid
import pastrocore.gui.rc_icons  # For active/inactive icons

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
        self.telescopes_model.setHorizontalHeaderLabels(["#", "Check", "Active", "Name"])
        self.ui.tab_telescopes.setAlternatingRowColors(True)
        self.ui.tab_telescopes.setSortingEnabled(False)
        self.ui.tab_telescopes.verticalHeader().setVisible(False)
        self.ui.tab_telescopes.setColumnWidth(1, 50)  # Check column
        self.ui.tab_telescopes.setColumnWidth(2, 50)  # Active column
        self.ui.tab_telescopes.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)

        # Configure frequencies table
        self.frequencies_model.setHorizontalHeaderLabels(["#", "Check", "Active", "Frequency (MHz)", "Bandwidth (MHz)", "Polarizations"])
        self.ui.tab_frequencies.setAlternatingRowColors(True)
        self.ui.tab_frequencies.setSortingEnabled(False)
        self.ui.tab_frequencies.verticalHeader().setVisible(False)
        self.ui.tab_frequencies.setColumnWidth(1, 50)  # Check column
        self.ui.tab_frequencies.setColumnWidth(2, 50)  # Active column
        self.ui.tab_frequencies.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.ui.tab_frequencies.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.ui.tab_frequencies.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)

        # Connect buttons
        self.ui.pushButton.clicked.connect(self.accept)
        self.ui.pushButton_2.clicked.connect(self.reject)

        # Connect checkbox signals
        self.ui.chk_offsource.stateChanged.connect(self.on_offsource_changed)

        # Connect model signals for debugging
        self.telescopes_model.itemChanged.connect(self.debug_item_changed)
        self.frequencies_model.itemChanged.connect(self.debug_item_changed)

        # Initialize UI components
        self.ui.startTimeEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.ui.durationEdit.setText("1")
        validator = QIntValidator(1, 999999, self)
        self.ui.durationEdit.setValidator(validator)
        self.ui.sourceCombo.addItem("None", None)

        # Track selected items manually
        self.selected_telescopes = set()
        self.selected_frequencies = set()

        # Log available telescopes
        telescopes = self.observation.get_telescopes().get_items()
        logger.debug(f"Available telescopes in observation: {telescopes}")

        # Populate UI
        self._populate_sources()
        self._populate_telescopes()
        self._populate_frequencies()

        # Load scan data if editing
        if not self.is_new:
            self._load_scan_data()
        else:
            ### NEW/CHANGED ### Set chk_active based on conditions for new scans
            self.ui.chk_active.setChecked(self._check_scan_conditions())
            logger.info(f"Set chk_active for new scan based on conditions: {self.ui.chk_active.isChecked()}")

        logger.info(f"Initialized ScanEditorDialog for {'new scan' if self.is_new else f'scan {self.scan.name}'} in observation '{self.observation.code}'")

    def debug_item_changed(self, item):
        """Debug signal for item changes in the model."""
        row = item.row()
        col = item.column()
        if col == 1:  # Check column
            model = item.model()
            name_item = model.item(row, 3) if model == self.telescopes_model else model.item(row, 3)
            name = name_item.data(Qt.UserRole) if name_item else "Unknown"
            check_state = item.checkState()
            logger.info(f"Item changed: {name}, check_state={check_state}")
            target_set = self.selected_telescopes if model == self.telescopes_model else self.selected_frequencies
            if check_state == Qt.Checked:
                target_set.add(name)
            else:
                target_set.discard(name)
            logger.debug(f"Current selected {'telescopes' if model == self.telescopes_model else 'frequencies'}: {target_set}")
            ### NEW/CHANGED ### Update chk_active when selection changes
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
        if sources_response["status"] and isinstance(sources_response["result"], dict) and sources_response["result"]:
            for name, source in sources_response["result"].items():
                ### NEW/CHANGED ### Log source activity status
                is_active_response = self.manipulator.process_request({
                    "operation": "inspect",
                    "obj": source,
                    "attributes": {"get": "isactive"}
                })
                is_active = is_active_response["status"] and bool(is_active_response["result"])
                logger.debug(f"Source {name} isactive: {is_active}")
                self.ui.sourceCombo.addItem(name, name)
            self.ui.sourceCombo.setCurrentIndex(0)
            self.ui.chk_offsource.setChecked(False)
            self.ui.sourceCombo.setEnabled(True)
            logger.info(f"Populated {len(sources_response['result'])} sources, selected first: {self.ui.sourceCombo.currentText()}")
        else:
            self.ui.chk_offsource.setChecked(True)
            self.ui.sourceCombo.setEnabled(False)
            logger.info("No sources available, set OFF SOURCE to True and disabled sourceCombo")

    def _populate_telescopes(self):
        """Populate the telescopes table with available telescopes."""
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
                ### NEW/CHANGED ### Log telescope activity status
                logger.debug(f"Telescope {name} isactive: {is_active}")

                row = [
                    QStandardItem(str(idx)),  # #
                    QStandardItem(),  # Check
                    QStandardItem(),  # Active
                    QStandardItem(name)  # Name
                ]
                row[1].setCheckable(True)
                row[1].setCheckState(Qt.Unchecked)
                row[2].setIcon(self.active_icon if is_active else self.inactive_icon)
                row[2].setToolTip("Active" if is_active else "Inactive")
                row[2].setTextAlignment(Qt.AlignCenter)
                for item in row:
                    item.setEditable(False)
                row[0].setData(name, Qt.UserRole)  # Store name in UserRole
                row[3].setData(name, Qt.UserRole)
                self.telescopes_model.appendRow(row)
                logger.info(f"Added telescope: {name}, checkable: True, active: {is_active}")
                idx += 1
            logger.debug(f"Populated {self.telescopes_model.rowCount()} telescopes")
        else:
            logger.error(f"Failed to populate telescopes: {telescopes_response.get('error', 'Unknown error')}")

    def _populate_frequencies(self):
        """Populate the frequencies table with available frequencies."""
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
                ### NEW/CHANGED ### Log frequency activity status
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
                row[1].setCheckState(Qt.Unchecked)
                row[2].setIcon(self.active_icon if is_active else self.inactive_icon)
                row[2].setToolTip("Active" if is_active else "Inactive")
                row[2].setTextAlignment(Qt.AlignCenter)
                for item in row:
                    item.setEditable(False)
                row[0].setData(name, Qt.UserRole)
                row[3].setData(name, Qt.UserRole)
                self.frequencies_model.appendRow(row)
                logger.info(f"Added frequency: {name}, checkable: True, active: {is_active}")
                idx += 1
            logger.debug(f"Populated {self.frequencies_model.rowCount()} frequencies")
        else:
            logger.error(f"Failed to populate frequencies: {frequencies_response.get('error', 'Unknown error')}")

    ### NEW/CHANGED ### New method to check scan activation conditions
    def _check_scan_conditions(self):
        """Check if scan conditions for activation are met (2 active telescopes, 1 active frequency, active source).

        Returns:
            bool: True if conditions are met, False otherwise.
        """
        # Check telescopes
        active_telescopes = []
        for row in range(self.telescopes_model.rowCount()):
            name_item = self.telescopes_model.item(row, 3)
            check_item = self.telescopes_model.item(row, 1)
            active_item = self.telescopes_model.item(row, 2)
            name = name_item.data(Qt.UserRole) if name_item else None
            is_checked = check_item.checkState() == Qt.Checked if check_item else False
            is_active = active_item.toolTip() == "Active" if active_item else False
            if is_checked and is_active and name:
                active_telescopes.append(name)
        logger.debug(f"Active and selected telescopes: {active_telescopes}")

        # Check frequencies
        active_frequencies = []
        for row in range(self.frequencies_model.rowCount()):
            name_item = self.frequencies_model.item(row, 3)
            check_item = self.frequencies_model.item(row, 1)
            active_item = self.frequencies_model.item(row, 2)
            name = name_item.data(Qt.UserRole) if name_item else None
            is_checked = check_item.checkState() == Qt.Checked if check_item else False
            is_active = active_item.toolTip() == "Active" if active_item else False
            if is_checked and is_active and name:
                active_frequencies.append(name)
        logger.debug(f"Active and selected frequencies: {active_frequencies}")

        # Check source
        is_off_source = self.ui.chk_offsource.isChecked()
        source_name = self.ui.sourceCombo.currentData()
        source_active = True
        if not is_off_source and source_name:
            source_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_sources(),
                "attributes": {"get": source_name}
            })
            if source_response["status"]:
                is_active_response = self.manipulator.process_request({
                    "operation": "inspect",
                    "obj": source_response["result"],
                    "attributes": {"get": "isactive"}
                })
                source_active = is_active_response["status"] and bool(is_active_response["result"])
        logger.debug(f"Source {source_name} active: {source_active}, is_off_source: {is_off_source}")

        # Assume VLBI observation requires 2 telescopes
        conditions_met = (
            len(active_telescopes) >= 2 and
            len(active_frequencies) >= 1 and
            (is_off_source or source_active)
        )
        logger.debug(f"Scan conditions check: telescopes={len(active_telescopes)} (>=2), "
                     f"frequencies={len(active_frequencies)} (>=1), "
                     f"source_active={source_active or is_off_source}, "
                     f"conditions_met={conditions_met}")
        return conditions_met

    def _load_scan_data(self):
        """Load existing scan data into the dialog."""
        try:
            start_time = self.scan.start
            start_dt = start_time.to_datetime()
            self.ui.startTimeEdit.setDateTime(QDateTime(start_dt))
            logger.info(f"Set start time to: {start_dt}")
        except Exception as e:
            logger.error(f"Failed to load start time '{self.scan.start.isot}': {str(e)}")
            current_time = QDateTime.currentDateTime()
            self.ui.startTimeEdit.setDateTime(current_time)
            logger.info(f"Fallback to current time: {current_time.toString(Qt.ISODate)}")

        self.ui.durationEdit.setText(str(int(self.scan.duration)))
        logger.info(f"Set duration: {int(self.scan.duration)}")

        source_name = self.scan.source_name
        self.ui.chk_offsource.setChecked(self.scan.is_off_source)
        if self.scan.is_off_source:
            self.ui.sourceCombo.setEnabled(False)
            self.ui.sourceCombo.setCurrentIndex(self.ui.sourceCombo.findData(None))
            logger.info(f"Set OFF SOURCE to True, sourceCombo disabled")
        elif source_name:
            index = self.ui.sourceCombo.findData(source_name)
            if index >= 0:
                self.ui.sourceCombo.setCurrentIndex(index)
                self.ui.sourceCombo.setEnabled(True)
                logger.info(f"Set source: {source_name}")
            else:
                logger.warning(f"Source '{source_name}' not found in combo box")
                self.ui.sourceCombo.setCurrentIndex(0)
                self.ui.sourceCombo.setEnabled(True)

        ### NEW/CHANGED ### Set chk_active based on conditions, not just scan.isactive
        self.ui.chk_active.setChecked(self._check_scan_conditions())
        logger.info(f"Set active status based on conditions: {self.ui.chk_active.isChecked()} (original scan.isactive: {self.scan.isactive})")

        # Load telescopes
        logger.debug(f"Loading telescopes for scan: {self.scan.telescope_names}")
        self.selected_telescopes.update(self.scan.telescope_names)
        for row in range(self.telescopes_model.rowCount()):
            item = self.telescopes_model.item(row, 3)  # Name column
            name = item.data(Qt.UserRole) if item else None
            if name in self.scan.telescope_names:
                check_item = self.telescopes_model.item(row, 1)
                check_item.setCheckState(Qt.Checked)
                self.telescopes_model.dataChanged.emit(check_item.index(), check_item.index(), [Qt.CheckStateRole])
                logger.info(f"Checked telescope: {name}, check_state: {check_item.checkState()}")
        self.ui.tab_telescopes.viewport().update()

        # Load frequencies
        logger.debug(f"Loading frequencies for scan: {self.scan.frequency_names}")
        self.selected_frequencies.update(self.scan.frequency_names)
        for row in range(self.frequencies_model.rowCount()):
            item = self.frequencies_model.item(row, 3)  # Frequency column
            name = item.data(Qt.UserRole) if item else None
            if name in self.scan.frequency_names:
                check_item = self.frequencies_model.item(row, 1)
                check_item.setCheckState(Qt.Checked)
                self.frequencies_model.dataChanged.emit(check_item.index(), check_item.index(), [Qt.CheckStateRole])
                logger.info(f"Checked frequency: {name}, check_state: {check_item.checkState()}")
        self.ui.tab_frequencies.viewport().update()

    @Slot(int)
    def on_offsource_changed(self, state):
        """Handle OFF SOURCE checkbox state change."""
        is_off_source = bool(state)
        self.ui.sourceCombo.setEnabled(not is_off_source)
        if is_off_source:
            self.ui.sourceCombo.setCurrentIndex(self.ui.sourceCombo.findData(None))
        logger.info(f"OFF SOURCE changed to: {is_off_source}, sourceCombo enabled: {self.ui.sourceCombo.isEnabled()}")
        ### NEW/CHANGED ### Update chk_active when offsource changes
        self.ui.chk_active.setChecked(self._check_scan_conditions())
        logger.debug(f"Updated chk_active after offsource change: {self.ui.chk_active.isChecked()}")

    def get_scan_data(self):
        """Retrieve scan data from the dialog.

        Returns:
            dict: Dictionary containing scan parameters.
        """
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
            raise ValueError("Duration must be a positive number")

        is_off_source = self.ui.chk_offsource.isChecked()
        source_name = None if is_off_source else self.ui.sourceCombo.currentData()

        # Log telescopes model state
        logger.debug("Telescopes model state:")
        telescope_names = []
        for row in range(self.telescopes_model.rowCount()):
            name_item = self.telescopes_model.item(row, 3)
            check_item = self.telescopes_model.item(row, 1)
            name = name_item.data(Qt.UserRole) if name_item else "Unknown"
            check_state = check_item.checkState() if check_item else Qt.Unchecked
            logger.debug(f"Telescope {name}: check_state={check_state}")
            if check_state == Qt.Checked:
                telescope_names.append(name)
                logger.info(f"Selected telescope: {name}")
        logger.debug(f"Selected telescopes from model: {telescope_names}")
        logger.debug(f"Manually tracked selected telescopes: {self.selected_telescopes}")

        # Log frequencies model state
        logger.debug("Frequencies model state:")
        frequency_names = []
        for row in range(self.frequencies_model.rowCount()):
            name_item = self.frequencies_model.item(row, 3)
            check_item = self.frequencies_model.item(row, 1)
            name = name_item.data(Qt.UserRole) if name_item else "Unknown"
            check_state = check_item.checkState() if check_item else Qt.Unchecked
            logger.debug(f"Frequency {name}: check_state={check_state}")
            if check_state == Qt.Checked:
                frequency_names.append(name)
                logger.info(f"Selected frequency: {name}")
        logger.debug(f"Selected frequencies from model: {frequency_names}")
        logger.debug(f"Manually tracked selected frequencies: {self.selected_frequencies}")

        # Fallback to selected sets if model is empty
        if not telescope_names and self.selected_telescopes:
            logger.warning("No telescopes in model, using manually tracked telescopes")
            telescope_names = list(self.selected_telescopes)
        if not frequency_names and self.selected_frequencies:
            logger.warning("No frequencies in model, using manually tracked frequencies")
            frequency_names = list(self.selected_frequencies)

        # Validate selections
        if not telescope_names:
            logger.error("No telescopes selected")
            raise ValueError("At least one telescope must be selected")
        if not frequency_names:
            logger.error("No frequencies selected")
            raise ValueError("At least one frequency must be selected")

        isactive = self.ui.chk_active.isChecked()
        ### NEW/CHANGED ### Warn if isactive=True but conditions not met
        conditions_met = self._check_scan_conditions()
        if isactive and not conditions_met:
            logger.warning("Scan marked as active but conditions not met (less than 2 active telescopes, no active frequency, or inactive source)")
            QMessageBox.warning(self, "Warning", 
                                "Scan is marked as active, but conditions are not met:\n"
                                "- At least 2 active telescopes required\n"
                                "- At least 1 active frequency required\n"
                                "- Source must be active (unless OFF SOURCE)")
        logger.debug(f"Retrieved isactive from chk_active: {isactive}, conditions_met: {conditions_met}")

        scan_data = {
            "name": self.scan.name if not self.is_new else f"scan_{uuid.uuid4().hex[:32]}",
            "start": start_time,
            "duration": duration,
            "source_name": source_name,
            "telescope_names": telescope_names,
            "frequency_names": frequency_names,
            "is_off_source": is_off_source,
            "isactive": isactive,
            "observation": self.observation
        }
        logger.info(f"Collected scan data: {scan_data}")
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