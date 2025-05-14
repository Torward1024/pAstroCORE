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
from pastrocore.gui.p_tab_telescopes import TelescopesTab
from pastrocore.gui.p_tab_frequencies import FrequenciesTab
from pastrocore.gui.p_tab_sources import SourcesTab
import pastrocore.gui.rc_icons
import uuid

class ScansTab(QWidget):
    """Widget for displaying and managing scans in an observation."""
    data_updated = Signal()

    def __init__(self, observation: Observation, project: ScheduleProject, manipulator: ScheduleManipulator,
                 telescopes_tab: 'TelescopesTab' = None, frequencies_tab: 'FrequenciesTab' = None,
                 sources_tab: 'SourcesTab' = None, parent=None):
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
            "#", " ", "Scan ID", "Start Time", "Duration (s)", "Source", "Telescopes", "Frequencies"
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
        self.ui.table.setColumnHidden(2, True)  # Скрываем столбец "Scan ID"

        # Connect signals
        self.ui.search.textChanged.connect(self.on_search_changed)
        self.ui.table.customContextMenuRequested.connect(self.show_context_menu)

        # Connect data_updated signals from other tabs
        if telescopes_tab:
            telescopes_tab.data_updated.connect(self.handle_data_updated)
        if frequencies_tab:
            frequencies_tab.data_updated.connect(self.handle_data_updated)
        if sources_tab:
            sources_tab.data_updated.connect(self.handle_data_updated)
            
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
        """Add a new scan to the observation using ScanEditorDialog after checking prerequisites."""
        # Check prerequisites: telescopes, sources, frequencies
        missing_components = []

        # Check observation type
        obs_type_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get": "observation_type"}
        })
        if not obs_type_response["status"]:
            logger.error(f"Failed to get observation type: {obs_type_response.get('error', 'Unknown error')}")
            QMessageBox.critical(self, "Error", f"Failed to get observation type: {obs_type_response.get('error', 'Unknown error')}")
            return
        obs_type = obs_type_response["result"]

        # Check telescopes
        telescopes_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_telescopes": None}
        })
        if not telescopes_response["status"] or not telescopes_response["result"]:
            logger.error(f"Failed to get telescopes: {telescopes_response.get('error', 'Unknown error')}")
            missing_components.append("telescopes")
        else:
            telescopes_items_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": telescopes_response["result"],
                "attributes": {"get_all": None}
            })
            if not telescopes_items_response["status"] or not isinstance(telescopes_items_response["result"], dict):
                logger.error(f"Failed to get telescope items: {telescopes_items_response.get('error', 'Unknown error')}")
                missing_components.append("telescopes")
            else:
                telescope_count = len(telescopes_items_response["result"])
                if obs_type == "VLBI" and telescope_count < 2:
                    missing_components.append("at least 2 telescopes (required for VLBI)")
                elif obs_type == "SINGLE_DISH" and telescope_count < 1:
                    missing_components.append("at least 1 telescope (required for SINGLE_DISH)")

        # Check frequencies
        frequencies_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_frequencies": None}
        })
        if not frequencies_response["status"] or not frequencies_response["result"]:
            logger.error(f"Failed to get frequencies: {frequencies_response.get('error', 'Unknown error')}")
            missing_components.append("frequencies")
        else:
            frequencies_items_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": frequencies_response["result"],
                "attributes": {"get_all": None}
            })
            if not frequencies_items_response["status"] or not isinstance(frequencies_items_response["result"], dict) or len(frequencies_items_response["result"]) < 1:
                logger.error(f"No frequencies found: {frequencies_items_response.get('error', 'No frequencies available')}")
                missing_components.append("at least 1 frequency")

        # If there are missing components, show a message and return
        if missing_components:
            logger.warning(f"Cannot add scan: missing components: {', '.join(missing_components)}")
            QMessageBox.information(
                self,
                "Cannot Add Scan",
                f"Cannot add a scan. Please add the following to the observation:\n- {', '.join(missing_components)}",
                QMessageBox.Ok
            )
            return

        # Proceed with scan creation if all prerequisites are met
        dialog = ScanEditorDialog(self.observation, self.manipulator, scan=None, parent=self)
        if dialog.exec() == QDialog.Accepted:
            try:
                scan_data = dialog.get_scan_data()
                request = {
                    "operation": "configure",
                    "obj": self.observation.get_scans(),
                    "attributes": {
                        "create_scan": {
                            "name": scan_data["name"],
                            "start": scan_data["start"],
                            "duration": scan_data["duration"],
                            "source_name": scan_data["source_name"],
                            "telescope_names": scan_data["telescope_names"],
                            "frequency_names": scan_data["frequency_names"],
                            "isactive": scan_data["isactive"],
                            "original_source_name": scan_data["original_source_name"],
                            "original_telescope_names": scan_data["original_telescope_names"],
                            "original_frequency_names": scan_data["original_frequency_names"],
                            "observation": self.observation
                        }
                    }
                }
                logger.info(f"Sending create_scan request: {request}")
                response = self.manipulator.process_request(request)
                if response["status"]:
                    logger.info(f"Added scan '{scan_data['name']}' to observation '{self.observation.code}'")
                    self.update()
                    self.data_updated.emit()
                else:
                    logger.error(f"Failed to add scan: {response.get('error', 'Unknown error')}")
                    QMessageBox.critical(self, "Error", f"Failed to add scan: {response.get('error', 'Unknown error')}")
            except ValueError as ve:
                logger.error(f"Validation error while adding scan: {str(ve)}")
                QMessageBox.critical(self, "Error", f"Failed to add scan: {str(ve)}")
            except Exception as e:
                logger.error(f"Exception while adding scan: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to add scan: {str(e)}")

    @Slot(str)
    def edit_scan(self, scan_name: str):
        """Edit an existing scan using ScanEditorDialog."""
        try:
            scan_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_scans(),
                "attributes": {"get": scan_name}
            })
            if not scan_response["status"]:
                logger.error(f"Failed to retrieve scan '{scan_name}': {scan_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to retrieve scan: {scan_response.get('error', 'Unknown error')}")
                return
            
            scan_obj = scan_response["result"]
            dialog = ScanEditorDialog(self.observation, self.manipulator, scan=scan_obj, parent=self)
            if dialog.exec() == QDialog.Accepted:
                try:
                    scan_data = dialog.get_scan_data()
                    request = {
                        "operation": "configure",
                        "obj": self.observation.get_scans(),
                        "attributes": {
                            "set_scan": {
                                "name": scan_name,
                                "start": scan_data["start"],
                                "duration": scan_data["duration"],
                                "source_name": scan_data["source_name"],
                                "telescope_names": scan_data["telescope_names"],
                                "frequency_names": scan_data["frequency_names"],
                                "isactive": scan_data["isactive"],
                                "original_source_name": scan_data["original_source_name"],
                                "original_telescope_names": scan_data["original_telescope_names"],
                                "original_frequency_names": scan_data["original_frequency_names"],
                                "observation": self.observation
                            }
                        }
                    }
                    logger.info(f"Sending set_scan request for '{scan_name}': {request}")
                    response = self.manipulator.process_request(request)
                    if response["status"]:
                        logger.info(f"Updated scan '{scan_name}' in observation '{self.observation.code}' with start={scan_data['start'].isot}")
                        self.update()
                        self.data_updated.emit()
                    else:
                        logger.error(f"Failed to update scan: {response.get('error', 'Unknown error')}")
                        QMessageBox.critical(self, "Error", f"Failed to update scan: {response.get('error', 'Unknown error')}")
                except ValueError as ve:
                    logger.error(f"Validation error while updating scan: {str(ve)}")
                    QMessageBox.critical(self, "Error", f"Failed to update scan: {str(ve)}")
                except Exception as e:
                    logger.error(f"Exception while updating scan: {str(e)}")
                    QMessageBox.critical(self, "Error", f"Failed to update scan: {str(e)}")
        except Exception as e:
            logger.error(f"Exception while editing scan: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to edit scan: {str(e)}")

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

            scan_obj = scan_response["result"]
            # Check if scan can be activated
            check_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": scan_obj,
                "attributes": {"check_activity_status": self.observation}
            })
            if not check_response["status"]:
                logger.error(f"Failed to check activity status for scan '{scan_name}': {check_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to check scan status: {check_response.get('error', 'Unknown error')}")
                return

            can_activate = check_response["result"]
            if not can_activate:
                logger.warning(f"Scan '{scan_name}' cannot be activated due to invalid configuration")
                QMessageBox.warning(self, "Cannot Activate", "The scan cannot be activated due to missing or inactive telescopes, frequencies, or source.")
                return

            request = {
                "operation": "configure",
                "obj": self.observation.get_scans(),
                "attributes": {
                    "set_scan": {
                        "name": scan_name,
                        "isactive": True,
                        "observation": self.observation
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
                        "isactive": False,
                        "observation": self.observation
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
                "attributes": {"activate_all": self.observation}
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
    
    @Slot(str, bool, str)
    def handle_data_updated(self, entity_name: str, is_active: bool, operation: str):
        """Handle data_updated signal for all entity types and operations."""
        logger.debug(f"Handling data_updated: entity_name={entity_name}, is_active={is_active}, operation={operation}")
        entity_type_map = {
            SourcesTab: "sources",
            TelescopesTab: "telescopes",
            FrequenciesTab: "frequencies"
        }
        sender = self.sender()
        entity_type = entity_type_map.get(type(sender), None)
        if not entity_type:
            logger.error(f"Unknown sender for data_updated signal: {sender}")
            return

        # Handle specific operations
        if operation in ("activate", "deactivate", "edit") and entity_name and is_active is not None:
            self.observation._sync_scans_with_activation(entity_type, entity_name, is_active)
        elif operation in ("add", "remove") and entity_name:
            self.observation._update_scan_names(entity_type, entity_name, operation)
        elif operation in ("activate_all", "deactivate_all", "clear", "drop_active", "drop_inactive"):
            # Handle bulk operations efficiently
            items_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get(entity_type),
                "attributes": {"get_all": None}
            })
            if not items_response["status"] or not isinstance(items_response["result"], dict):
                logger.warning(f"No {entity_type} found for bulk operation '{operation}'")
                return

            items = items_response["result"]
            if operation == "activate_all":
                for name in items:
                    self.observation._sync_scans_with_activation(entity_type, name, True)
            elif operation == "deactivate_all":
                for name in items:
                    self.observation._sync_scans_with_activation(entity_type, name, False)
            elif operation in ("clear", "drop_active", "drop_inactive"):
                for name, item in items.items():
                    # Check activity status for drop_active/drop_inactive
                    is_active_response = self.manipulator.process_request({
                        "operation": "inspect",
                        "obj": item,
                        "attributes": {"get": "isactive"}
                    })
                    item_active = is_active_response["status"] and bool(is_active_response["result"])
                    if (operation == "clear" or
                        (operation == "drop_active" and item_active) or
                        (operation == "drop_inactive" and not item_active)):
                        self.observation._update_scan_names(entity_type, name, "remove")

        self.update()
        self.data_updated.emit()
        logger.info(f"Completed handling data_updated for {entity_type}, operation={operation}")

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
                    start_time = attrs["start"].strftime("%d.%m.%Y %H:%M:%S") if attrs["start"] else "N/A"
                    duration = f"{attrs['duration']:.1f}" if attrs["duration"] else "N/A"
                    source_name = attrs["source_name"] or "None"
                    telescopes = ", ".join(attrs["telescope_names"]) if attrs["telescope_names"] else "None"

                    # Retrieve frequency values in MHz using scan_obj.get_frequencies
                    try:
                        frequencies_obj = scan_obj.get_frequencies(self.observation)
                        frequency_values = frequencies_obj.get_frequencies()
                        frequencies = ", ".join(f"{freq:.2f} MHz" for freq in frequency_values) if frequency_values else "None"
                    except Exception as e:
                        logger.error(f"Failed to retrieve frequencies for scan '{name}': {str(e)}")
                        frequencies = "N/A"

                    row = [
                        QStandardItem(str(idx)),
                        active_item,
                        QStandardItem(name),
                        QStandardItem(start_time),
                        QStandardItem(duration),
                        QStandardItem(source_name),
                        QStandardItem(telescopes),
                        QStandardItem(frequencies)
                    ]
                    for item in row:
                        item.setEditable(False)
                    row[0].setData(name, Qt.UserRole)
                    self.model.appendRow(row)
                    idx += 1

        self.ui.table.resizeColumnsToContents()