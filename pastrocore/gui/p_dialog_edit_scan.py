# pastrocore/gui/p_dialog_edit_scan.py
from PySide6.QtWidgets import QDialog, QMessageBox, QListView, QStyledItemDelegate
from PySide6.QtCore import Slot, Qt, QDateTime
from PySide6.QtGui import QStandardItemModel, QStandardItem
from .ui_dialog_edit_scan import Ui_ScanEditorDialog
from pastrocore.base.observation import Observation
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from common.utils.logging_setup import logger
from astropy.time import Time
import uuid

class ScanEditorDialog(QDialog):
    """Dialog for creating or editing a scan in an observation."""

    def __init__(self, observation: Observation, manipulator: ScheduleManipulator, scan_name: str = None, parent=None):
        """Initialize the ScanEditorDialog.

        Args:
            observation (Observation): The observation containing the scan.
            manipulator (ScheduleManipulator): Manipulator for data operations.
            scan_name (str, optional): Name of the scan to edit. If None, creates a new scan.
            parent (QWidget, optional): Parent widget.
        """
        super().__init__(parent)
        self.ui = Ui_ScanEditorDialog()
        self.ui.setupUi(self)
        self.observation = observation
        self.manipulator = manipulator
        self.scan_name = scan_name
        self.is_new = scan_name is None

        # Initialize models for QListView
        self.telescopes_model = QStandardItemModel()
        self.frequencies_model = QStandardItemModel()
        self.ui.listView.setModel(self.telescopes_model)
        self.ui.listView_2.setModel(self.frequencies_model)

        # Enable multiple selection and checkboxes
        self.ui.listView.setSelectionMode(QListView.ExtendedSelection)
        self.ui.listView_2.setSelectionMode(QListView.ExtendedSelection)
        self.ui.listView.setEditTriggers(QListView.NoEditTriggers)
        self.ui.listView_2.setEditTriggers(QListView.NoEditTriggers)
        self.ui.listView.setItemDelegate(QStyledItemDelegate())
        self.ui.listView_2.setItemDelegate(QStyledItemDelegate())

        # Connect buttons
        self.ui.pushButton.clicked.connect(self.accept)
        self.ui.pushButton_2.clicked.connect(self.reject)

        # Connect model signal for debugging
        self.telescopes_model.itemChanged.connect(self.debug_item_changed)

        # Initialize UI components
        self.ui.startTimeEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.ui.startTimeEdit.setMinimumDateTime(QDateTime.currentDateTime())
        self.ui.durationEdit.setText("1.0")
        self.ui.sourceCombo.addItem("None", None)

        # Populate combo boxes and lists
        self._populate_sources()
        self._populate_telescopes()
        self._populate_frequencies()

        # Load scan data if editing
        if not self.is_new:
            self._load_scan_data()

        logger.info(f"Initialized ScanEditorDialog for {'new scan' if self.is_new else f'scan {self.scan_name}'} in observation '{self.observation.code}'")

    def debug_item_changed(self, item):
        """Debug signal for item changes in the model."""
        logger.info(f"Item changed: {item.text()}, check_state={item.data(Qt.CheckStateRole)}")

    def _populate_sources(self):
        """Populate the source combo box with available sources."""
        sources_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation.get_sources(),
            "attributes": {"get_all": None}
        })
        if sources_response["status"] and isinstance(sources_response["result"], dict):
            for name, source in sources_response["result"].items():
                self.ui.sourceCombo.addItem(name, name)
        else:
            logger.error(f"Failed to populate sources: {sources_response.get('error', 'Unknown error')}")

    def _populate_telescopes(self):
        """Populate the telescopes list with available telescopes."""
        telescopes_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation.get_telescopes(),
            "attributes": {"get_all": None}
        })
        if telescopes_response["status"] and isinstance(telescopes_response["result"], dict):
            for name, telescope in telescopes_response["result"].items():
                item = QStandardItem(name)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                item.setData(Qt.Unchecked, Qt.CheckStateRole)
                self.telescopes_model.appendRow(item)
                logger.info(f"Added telescope item: {name}, checkable: {item.isCheckable()}, state: {item.data(Qt.CheckStateRole)}")
        else:
            logger.error(f"Failed to populate telescopes: {telescopes_response.get('error', 'Unknown error')}")

    def _populate_frequencies(self):
        """Populate the frequencies list with available frequencies."""
        frequencies_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation.get_frequencies(),
            "attributes": {"get_all": None}
        })
        if frequencies_response["status"] and isinstance(frequencies_response["result"], dict):
            for name, freq in frequencies_response["result"].items():
                item = QStandardItem(name)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                item.setData(Qt.Unchecked, Qt.CheckStateRole)
                self.frequencies_model.appendRow(item)
                logger.info(f"Added frequency item: {name}, checkable: {item.isCheckable()}, state: {item.data(Qt.CheckStateRole)}")
        else:
            logger.error(f"Failed to populate frequencies: {frequencies_response.get('error', 'Unknown error')}")

    def _load_scan_data(self):
        """Load existing scan data into the dialog."""
        scan_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation.get_scans(),
            "attributes": {"get": self.scan_name}
        })
        if not scan_response["status"] or not scan_response["result"]:
            logger.error(f"Failed to load scan '{self.scan_name}': {scan_response.get('error', 'Unknown error')}")
            QMessageBox.critical(self, "Error", f"Failed to load scan: {scan_response.get('error', 'Unknown error')}")
            self.reject()
            return

        scan = scan_response["result"]
        attrs_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": scan,
            "attributes": {
                "get": ["start", "duration", "source_name", "telescope_names", "frequency_names"]
            }
        })
        if attrs_response["status"]:
            attrs = attrs_response["result"]
            # Convert start time to QDateTime
            try:
                self.ui.startTimeEdit.setDateTime(QDateTime.fromString(attrs["start"].isot, Qt.ISODate))
            except Exception as e:
                logger.error(f"Failed to parse start time '{attrs['start'].isot}': {str(e)}")
                QMessageBox.critical(self, "Error", f"Invalid start time format: {str(e)}")
                self.reject()
                return

            self.ui.durationEdit.setText(str(attrs["duration"]))
            source_name = attrs["source_name"]
            if source_name:
                index = self.ui.sourceCombo.findData(source_name)
                if index >= 0:
                    self.ui.sourceCombo.setCurrentIndex(index)

            # Set checked telescopes
            for row in range(self.telescopes_model.rowCount()):
                item = self.telescopes_model.item(row)
                if item.text() in attrs["telescope_names"]:
                    item.setData(Qt.Checked, Qt.CheckStateRole)
                    logger.info(f"Checked telescope: {item.text()}, state: {item.data(Qt.CheckStateRole)}")

            # Set checked frequencies
            for row in range(self.frequencies_model.rowCount()):
                item = self.frequencies_model.item(row)
                if item.text() in attrs["frequency_names"]:
                    item.setData(Qt.Checked, Qt.CheckStateRole)
                    logger.info(f"Checked frequency: {item.text()}, state: {item.data(Qt.CheckStateRole)}")
        else:
            logger.error(f"Failed to load scan attributes: {attrs_response.get('error', 'Unknown error')}")
            QMessageBox.critical(self, "Error", f"Failed to load scan attributes: {attrs_response.get('error', 'Unknown error')}")
            self.reject()

    def get_scan_data(self):
        """Retrieve scan data from the dialog.

        Returns:
            dict: Dictionary containing scan parameters.
        """
        start_time = Time(self.ui.startTimeEdit.dateTime().toPython())
        try:
            duration = float(self.ui.durationEdit.text())
            if duration <= 0:
                raise ValueError("Duration must be positive")
        except ValueError as e:
            logger.error(f"Invalid duration: {str(e)}")
            raise ValueError("Duration must be a positive number")

        source_name = self.ui.sourceCombo.currentData()
        telescope_names = []
        logger.info(f"Total telescope rows: {self.telescopes_model.rowCount()}")
        for row in range(self.telescopes_model.rowCount()):
            item = self.telescopes_model.item(row)
            check_state = item.data(Qt.CheckStateRole)
            logger.info(f"Telescope {item.text()}: check_state={check_state}")
            if check_state == 2:  # Qt.Checked is 2
                telescope_names.append(item.text())
                logger.info(f"Added telescope to selection: {item.text()}")

        frequency_names = []
        logger.info(f"Total frequency rows: {self.frequencies_model.rowCount()}")
        for row in range(self.frequencies_model.rowCount()):
            item = self.frequencies_model.item(row)
            check_state = item.data(Qt.CheckStateRole)
            logger.info(f"Frequency {item.text()}: check_state={check_state}")
            if check_state == 2:  # Qt.Checked is 2
                frequency_names.append(item.text())
                logger.info(f"Added frequency to selection: {item.text()}")

        if not telescope_names:
            logger.error("No telescopes selected")
            raise ValueError("At least one telescope must be selected")
        if not frequency_names:
            logger.error("No frequencies selected")
            raise ValueError("At least one frequency must be selected")

        scan_data = {
            "name": self.scan_name if not self.is_new else f"scan_{uuid.uuid4().hex[:32]}",
            "start": start_time,
            "duration": duration,
            "source_name": source_name,
            "telescope_names": telescope_names,
            "frequency_names": frequency_names,
            "isactive": True
        }
        logger.info(f"Collected scan data: {scan_data}")
        return scan_data

    @Slot()
    def accept(self):
        """Handle OK button click, validate and save scan data."""
        try:
            scan_data = self.get_scan_data()
            request = {
                "operation": "configure",
                "obj": self.observation.get_scans(),
                "attributes": {
                    "create_scan" if self.is_new else "set_item": scan_data
                }
            }
            logger.info(f"Sending request to Manipulator: {request}")
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"{'Created' if self.is_new else 'Updated'} scan '{scan_data['name']}' in observation '{self.observation.code}'")
                super().accept()
            else:
                logger.error(f"Failed to {'create' if self.is_new else 'update'} scan: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to {'create' if self.is_new else 'update'} scan: {response.get('error', 'Unknown error')}")
        except ValueError as ve:
            logger.error(f"Validation error: {str(ve)}")
            QMessageBox.critical(self, "Error", str(ve))
        except Exception as e:
            logger.error(f"Exception while saving scan: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save scan: {str(e)}")