# pastrocore/gui/p_tab_scans.py
from PySide6.QtWidgets import QWidget, QMessageBox, QMenu, QDialog
from PySide6.QtCore import Signal, Slot, Qt, QSortFilterProxyModel, QRegularExpression, QPoint
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
from .ui_tab_observation_any import Ui_observation_tab
from .p_dialog_edit_scan import ScanEditorDialog
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
import pastrocore.gui.rc_icons
import uuid

class ScansTab(QWidget):
    """Widget for displaying and managing scans in an observation."""
    data_updated = Signal()

    def __init__(self, observation: Observation, project: ScheduleProject, manipulator: ScheduleManipulator, parent=None):
        super().__init__(parent)
        self.observation = observation
        self.project = project
        self.manipulator = manipulator
        self.active_icon = QIcon(":/icons/active_icon.svg")
        self.inactive_icon = QIcon(":/icons/inactive_icon.svg")

        # Setup UI
        self.ui = Ui_observation_tab()
        self.ui.setupUi(self)
        self.ui.search.setPlaceholderText("Search scans...")

        # Setup table
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels([
            "#", " ", "Scan ID", "Start Time", "Duration (s)", "Source", "Telescopes", "Frequencies", "Polarizations"
        ])
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterKeyColumn(-1)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.ui.table.setModel(self.proxy_model)
        self.ui.table.setAlternatingRowColors(True)
        self.ui.table.setSortingEnabled(True)
        self.ui.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.table.verticalHeader().setVisible(False)
        self.ui.table.sortByColumn(0, Qt.AscendingOrder)
        self.ui.table.setColumnWidth(1, 24)
        self.ui.table.setColumnWidth(0, 50)

        # Connect signals
        self.ui.search.textChanged.connect(self.on_search_changed)
        self.ui.table.customContextMenuRequested.connect(self.show_context_menu)
        self.update()

        logger.info(f"ScansTab initialized for observation '{observation.code}'")

    @Slot(str)
    def on_search_changed(self, text: str):
        """Handle search text change."""
        reg_exp = QRegularExpression(text)
        self.proxy_model.setFilterRegularExpression(reg_exp)

    def show_context_menu(self, position: QPoint):
        """Show context menu for the scans table."""
        menu = QMenu(self)
        add_action = menu.addAction(QIcon(":/icons/add_icon.svg"), "Add Scan")
        add_action.triggered.connect(self.add_scan)

        # Check if there are any scans
        scans_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_scans": None}
        })
        has_scans = False
        if scans_response["status"] and scans_response["result"]:
            items_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": scans_response["result"],
                "attributes": {"get_all": None}
            })
            has_scans = items_response["status"] and isinstance(items_response["result"], dict) and len(items_response["result"]) > 0
        else:
            logger.error(f"Failed to inspect scans: {scans_response.get('error', 'Unknown error')}")

        if has_scans:
            activate_all_action = menu.addAction(QIcon(":/icons/active_icon.svg"), "Activate All")
            deactivate_all_action = menu.addAction(QIcon(":/icons/inactive_icon.svg"), "Deactivate All")
            drop_active_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Drop Active")
            drop_inactive_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Drop Inactive")
            clear_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Clear")
            activate_all_action.triggered.connect(self.activate_all_scans)
            deactivate_all_action.triggered.connect(self.deactivate_all_scans)
            drop_active_action.triggered.connect(self.drop_active_scans)
            drop_inactive_action.triggered.connect(self.drop_inactive_scans)
            clear_action.triggered.connect(self.clear_scans)

        # Check if a specific row is selected
        index = self.ui.table.indexAt(position)
        if index.isValid():
            source_index = self.proxy_model.mapToSource(index)
            scan_name = self.model.item(source_index.row(), 0).data(Qt.UserRole)
            scan_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_scans(),
                "attributes": {"get": scan_name}
            })
            if not scan_response["status"] or not scan_response["result"]:
                logger.error(f"Failed to get scan '{scan_name}': {scan_response.get('error', 'Unknown error')}")
                return
            scan_obj = scan_response["result"]

            is_active_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": scan_obj,
                "attributes": {"get": "isactive"}
            })
            is_active = is_active_response["status"] and bool(is_active_response["result"])

            menu.addSeparator()
            if is_active:
                deactivate_action = menu.addAction(QIcon(":/icons/inactive_icon.svg"), "Deactivate")
                deactivate_action.triggered.connect(lambda: self.deactivate_scan(scan_name))
            else:
                activate_action = menu.addAction(QIcon(":/icons/active_icon.svg"), "Activate")
                activate_action.triggered.connect(lambda: self.activate_scan(scan_name))

            menu.addSeparator()
            edit_action = menu.addAction(QIcon(":/icons/edit_icon.svg"), "Edit Scan")
            remove_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Remove Scan")
            edit_action.triggered.connect(lambda: self.edit_scan(scan_name))
            remove_action.triggered.connect(lambda: self.remove_scan(scan_name))

        menu.exec(self.ui.table.viewport().mapToGlobal(position))

    @Slot()
    def add_scan(self):
        """Add a new scan to the observation using ScanEditorDialog."""
        dialog = ScanEditorDialog(self.observation, self.manipulator, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.update()
            self.data_updated.emit()

    @Slot(str)
    def edit_scan(self, scan_name: str):
        """Edit an existing scan using ScanEditorDialog."""
        dialog = ScanEditorDialog(self.observation, self.manipulator, scan_name, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.update()
            self.data_updated.emit()

    @Slot(str)
    def remove_scan(self, scan_name: str):
        """Remove a scan from the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_scans(),
                "attributes": {"remove": scan_name}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Removed scan '{scan_name}' from observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit()
            else:
                logger.error(f"Failed to remove scan: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to remove scan: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while removing scan: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to remove scan: {str(e)}")

    @Slot(str)
    def activate_scan(self, scan_name: str):
        """Activate the specified scan."""
        try:
            scan_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_scans(),
                "attributes": {"get": scan_name}
            })
            if not scan_response["status"] or not scan_response["result"]:
                logger.error(f"Failed to get scan '{scan_name}': {scan_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to activate scan: {scan_response.get('error', 'Unknown error')}")
                return

            request = {
                "operation": "configure",
                "obj": self.observation.get_scans(),
                "attributes": {
                    "set_scan": {
                        "name": scan_name,
                        "isactive": True
                    }
                }
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Scan '{scan_name}' activated in observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit()
            else:
                logger.error(f"Failed to activate scan '{scan_name}': {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to activate scan: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while activating scan '{scan_name}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to activate scan: {str(e)}")

    @Slot(str)
    def deactivate_scan(self, scan_name: str):
        """Deactivate the specified scan."""
        try:
            scan_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_scans(),
                "attributes": {"get": scan_name}
            })
            if not scan_response["status"] or not scan_response["result"]:
                logger.error(f"Failed to get scan '{scan_name}': {scan_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to deactivate scan: {scan_response.get('error', 'Unknown error')}")
                return

            request = {
                "operation": "configure",
                "obj": self.observation.get_scans(),
                "attributes": {
                    "set_scan": {
                        "name": scan_name,
                        "isactive": False
                    }
                }
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Scan '{scan_name}' deactivated in observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit()
            else:
                logger.error(f"Failed to deactivate scan '{scan_name}': {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to deactivate scan: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while deactivating scan '{scan_name}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to deactivate scan: {str(e)}")

    @Slot()
    def activate_all_scans(self):
        """Activate all scans in the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_scans(),
                "attributes": {"activate_all": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All scans activated in observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit()
            else:
                logger.error(f"Failed to activate all scans: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to activate all scans: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while activating all scans: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to activate all scans: {str(e)}")

    @Slot()
    def deactivate_all_scans(self):
        """Deactivate all scans in the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_scans(),
                "attributes": {"deactivate_all": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All scans deactivated in observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit()
            else:
                logger.error(f"Failed to deactivate all scans: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to deactivate all scans: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while deactivating all scans: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to deactivate all scans: {str(e)}")

    @Slot()
    def drop_active_scans(self):
        """Remove all active scans from the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_scans(),
                "attributes": {"drop_active": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All active scans dropped from observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit()
            else:
                logger.error(f"Failed to drop active scans: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to drop active scans: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while dropping active scans: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to drop active scans: {str(e)}")

    @Slot()
    def drop_inactive_scans(self):
        """Remove all inactive scans from the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_scans(),
                "attributes": {"drop_inactive": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All inactive scans dropped from observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit()
            else:
                logger.error(f"Failed to drop inactive scans: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to drop inactive scans: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while dropping inactive scans: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to drop inactive scans: {str(e)}")

    @Slot()
    def clear_scans(self):
        """Clear all scans from the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_scans(),
                "attributes": {"clear": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All scans cleared from observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit()
            else:
                logger.error(f"Failed to clear scans: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to clear scans: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while clearing scans: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to clear scans: {str(e)}")

    @Slot()
    def update(self):
        """Update the scans table."""
        self.model.removeRows(0, self.model.rowCount())
        scans_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_scans": None}
        })
        if scans_response["status"] and scans_response["result"]:
            scans = scans_response["result"]
            items_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": scans,
                "attributes": {"get_all": None}
            })
            if items_response["status"] and isinstance(items_response["result"], dict):
                idx = 1
                for name, scan_obj in items_response["result"].items():
                    is_active_response = self.manipulator.process_request({
                        "operation": "inspect",
                        "obj": scan_obj,
                        "attributes": {"get": "isactive"}
                    })
                    is_active = is_active_response["status"] and bool(is_active_response["result"])
                    active_item = QStandardItem()
                    active_item.setIcon(self.active_icon if is_active else self.inactive_icon)
                    active_item.setToolTip("Active" if is_active else "Inactive")
                    active_item.setTextAlignment(Qt.AlignCenter)

                    attrs_response = self.manipulator.process_request({
                        "operation": "inspect",
                        "obj": scan_obj,
                        "attributes": {
                            "get": ["start", "duration", "source_name", "telescope_names", "frequency_names"]
                        }
                    })
                    if not attrs_response["status"]:
                        logger.error(f"Failed to get attributes for scan '{name}': {attrs_response.get('error', 'Unknown error')}")
                        continue

                    attrs = attrs_response["result"]
                    start_time = attrs["start"].isot if attrs["start"] else "N/A"
                    duration = f"{attrs['duration']:.1f}" if attrs["duration"] else "N/A"
                    source_name = attrs["source_name"] or "None"
                    telescopes = ", ".join(attrs["telescope_names"]) if attrs["telescope_names"] else "None"
                    frequencies = ", ".join(attrs["frequency_names"]) if attrs["frequency_names"] else "None"

                    # Polarizations (placeholder, as not stored directly in Scan)
                    polarizations = "N/A"  # Could be derived from frequencies if needed

                    row = [
                        QStandardItem(str(idx)),
                        active_item,
                        QStandardItem(name),
                        QStandardItem(start_time),
                        QStandardItem(duration),
                        QStandardItem(source_name),
                        QStandardItem(telescopes),
                        QStandardItem(frequencies),
                        QStandardItem(polarizations)
                    ]
                    for item in row:
                        item.setEditable(False)
                    row[0].setData(name, Qt.UserRole)
                    self.model.appendRow(row)
                    idx += 1

        self.ui.table.resizeColumnsToContents()