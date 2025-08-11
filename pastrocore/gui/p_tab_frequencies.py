from PySide6.QtWidgets import QWidget, QMessageBox, QMenu, QDialog, QFileDialog
from PySide6.QtCore import Signal, Slot, Qt, QRegularExpression, QPoint
from PySide6.QtGui import QStandardItem, QIcon
from pastrocore.gui.p_dialog_edit_if import IFEditorDialog
from pastrocore.gui.ui_tab_observation_any import Ui_observation_tab
from pastrocore.gui.p_custom_model import CustomStandardItemModel, CustomSortFilterProxyModel
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from pastrocore.base.frequencies import IF
from common.utils.logging_setup import logger
import uuid
import json

class FrequenciesTab(QWidget):
    """Widget for displaying and managing frequencies in an observation."""
    data_updated = Signal(str, bool, str)

    def __init__(self, observation: Observation, manipulator: ScheduleManipulator, parent=None):
        super().__init__(parent)
        self.observation = observation
        self.project = manipulator.get_managing_object()
        self.manipulator = manipulator
        self.active_icon = QIcon(":/icons/active_icon.svg")
        self.inactive_icon = QIcon(":/icons/inactive_icon.svg")
        
        self.ui = Ui_observation_tab()
        self.ui.setupUi(self)
        self.ui.search.setPlaceholderText("Search frequencies...")

        self.model = CustomStandardItemModel()
        self.model.setHorizontalHeaderLabels([
            "#", " ", "IF ID", "IF (MHz)", "λ (cm)", "Bandwidth (MHz)", "Polarizations"
        ])
        self.proxy_model = CustomSortFilterProxyModel()
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
        self.ui.table.setColumnHidden(2, True)  
        self.ui.search.textChanged.connect(self.search_changed)
        self.ui.table.customContextMenuRequested.connect(self.show_context_menu)
        self.update()

    @Slot(str)
    def search_changed(self, text: str):
        """Handle search text change."""
        reg_exp = QRegularExpression(text)
        self.proxy_model.setFilterRegularExpression(reg_exp)

    def show_context_menu(self, position: QPoint):
        """Show context menu for the frequencies table."""
        menu = QMenu(self)
        
        add_action = menu.addAction(QIcon(":/icons/add_icon.svg"), "Add Frequency")
        import_new_action = menu.addAction(QIcon(":/icons/import_icon.svg"), "Import New Frequency")
        add_action.triggered.connect(self.add_frequency)
        import_new_action.triggered.connect(self.import_new_if)

        frequencies_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_frequencies": None}
        })
        has_frequencies = False
        if frequencies_response["status"] and frequencies_response["result"]:
            items_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": frequencies_response["result"],
                "attributes": {"get_all": None}
            })
            has_frequencies = items_response["status"] and isinstance(items_response["result"], dict) and len(items_response["result"]) > 0
        else:
            logger.info(f"No frequencies found in observation '{self.observation.code}'")

        if has_frequencies:
            activate_all_action = menu.addAction(QIcon(":/icons/active_icon.svg"), "Activate All")
            deactivate_all_action = menu.addAction(QIcon(":/icons/inactive_icon.svg"), "Deactivate All")
            drop_active_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Drop Active")
            drop_inactive_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Drop Inactive")
            clear_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Clear")
            activate_all_action.triggered.connect(self.activate_all_frequencies)
            deactivate_all_action.triggered.connect(self.deactivate_all_frequencies)
            drop_active_action.triggered.connect(self.drop_active_frequencies)
            drop_inactive_action.triggered.connect(self.drop_inactive_frequencies)
            clear_action.triggered.connect(self.clear_frequencies)

        index = self.ui.table.indexAt(position)
        if index.isValid():
            source_index = self.proxy_model.mapToSource(index)
            freq_name = self.model.item(source_index.row(), 0).data(Qt.UserRole)
            freq_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_frequencies(),
                "attributes": {"get": freq_name}
            })
            if not freq_response["status"] or not freq_response["result"]:
                logger.error(f"Failed to get frequency '{freq_name}': {freq_response.get('error', 'Unknown error')}")
                return
            if_obj = freq_response["result"]
            
            is_active_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": if_obj,
                "attributes": {"get": "isactive"}
            })
            is_active = is_active_response["status"] and bool(is_active_response["result"])

            menu.addSeparator()
            if is_active:
                deactivate_action = menu.addAction(QIcon(":/icons/inactive_icon.svg"), "Deactivate")
                deactivate_action.triggered.connect(lambda: self.deactivate_frequency(freq_name))
            else:
                activate_action = menu.addAction(QIcon(":/icons/active_icon.svg"), "Activate")
                activate_action.triggered.connect(lambda: self.activate_frequency(freq_name))

            menu.addSeparator()
            import_action = menu.addAction(QIcon(":/icons/import_icon.svg"), "Import Frequency")
            export_action = menu.addAction(QIcon(":/icons/export_icon.svg"), "Export Frequency")
            import_action.triggered.connect(lambda: self.import_if(freq_name))
            export_action.triggered.connect(lambda: self.export_if(freq_name))
            menu.addSeparator()
            remove_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Remove Frequency")
            edit_action = menu.addAction(QIcon(":/icons/edit_icon.svg"), "Edit Frequency")
            remove_action.triggered.connect(lambda: self.remove_frequency(freq_name))
            edit_action.triggered.connect(lambda: self.edit_frequency(freq_name))
        
        menu.exec(self.ui.table.viewport().mapToGlobal(position))

    @Slot()
    def add_frequency(self):
        """Add a new frequency to the observation using IFEditorDialog."""
        dialog = IFEditorDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            try:
                if_data = dialog.get_if_data()
                freq_name = f"freq_{uuid.uuid4().hex[:32]}"
                request = {
                    "operation": "configure",
                    "obj": self.observation.get_frequencies(),
                    "attributes": {
                        "create_if": {
                            "name": freq_name,
                            "frequency": if_data["frequency"],
                            "bandwidth": if_data["bandwidth"],
                            "polarizations": if_data["polarizations"],
                            "isactive": if_data["isactive"]
                        }
                    }
                }
                response = self.manipulator.process_request(request)
                if response["status"]:
                    logger.info(f"Added frequency '{freq_name}' to observation '{self.observation.code}'")
                    self.update()
                    self.data_updated.emit(freq_name, None, "add")
                else:
                    logger.error(f"Failed to add frequency: {response.get('error', 'Unknown error')}")
                    QMessageBox.critical(self, "Error", f"Failed to add frequency: {response.get('error', 'Unknown error')}")
            except ValueError as ve:
                logger.error(f"Validation error while adding frequency: {str(ve)}")
                QMessageBox.critical(self, "Error", f"Failed to add frequency: {str(ve)}")
            except Exception as e:
                logger.error(f"Exception while adding frequency: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to add frequency: {str(e)}")

    @Slot()
    def import_new_if(self):
        """Import a new frequency into the observation."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Import New Frequency", "", "pAstroCORE Data (*.pastrod)")
        if not file_path:
            logger.info("Import new frequency cancelled: No file selected")
            return

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            imported_if = IF.from_dict(data)
            freq_name = f"freq_{uuid.uuid4().hex[:32]}"
            imported_if.name = freq_name
            request = {
                "operation": "configure",
                "obj": self.observation.get_frequencies(),
                "attributes": {
                    "add": imported_if
                }
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"New frequency '{freq_name}' imported successfully to observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(freq_name, None, "add")
                QMessageBox.information(self, "Success", f"Frequency '{freq_name}' imported successfully.")
            else:
                logger.error(f"Failed to import frequency: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to import frequency: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while importing new frequency: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to import frequency: {str(e)}")

    @Slot(str)
    def import_if(self, freq_name: str):
        """Import a frequency to overwrite an existing one."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Frequency", "", "pAstroCORE Data (*.pastrod)")
        if not file_path:
            logger.info(f"Import frequency '{freq_name}' cancelled: No file selected")
            return

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            # Get existing frequency
            freq_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_frequencies(),
                "attributes": {"get": freq_name}
            })
            if not freq_response["status"] or not freq_response["result"]:
                logger.error(f"Failed to find frequency '{freq_name}': {freq_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Frequency '{freq_name}' not found")
                return

            # Create new IF object from file data
            imported_if = IF.from_dict(data)
            # Preserve existing name
            imported_if.name = freq_name
            # Update frequency through Manipulator
            request = {
                "operation": "configure",
                "obj": self.observation.get_frequencies(),
                "attributes": {
                    "set_item": {"name": freq_name, "item": imported_if}
                }
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Frequency '{freq_name}' overwritten successfully in observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit()
                QMessageBox.information(self, "Success", f"Frequency '{freq_name}' imported successfully.")
            else:
                logger.error(f"Failed to overwrite frequency '{freq_name}': {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to import frequency: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while importing frequency '{freq_name}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to import frequency: {str(e)}")

    @Slot(str)
    def export_if(self, freq_name: str):
        """Export a frequency to a file."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Frequency", "", "pAstroCORE Data (*.pastrod)")
        if not file_path:
            logger.info(f"Export frequency '{freq_name}' cancelled: No file selected")
            return
        if not file_path.endswith(".pastrod"):
            file_path += ".pastrod"

        try:
            # Get frequency object
            freq_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_frequencies(),
                "attributes": {"get": freq_name}
            })
            if not freq_response["status"] or not freq_response["result"]:
                logger.error(f"Failed to get frequency '{freq_name}': {freq_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Frequency '{freq_name}' not found")
                return

            if_obj = freq_response["result"]
            with open(file_path, "w") as f:
                json.dump(if_obj.to_dict(), f, indent=4)
            logger.info(f"Frequency '{freq_name}' exported to '{file_path}'")
            QMessageBox.information(self, "Success", f"Frequency '{freq_name}' exported successfully.")
        except Exception as e:
            logger.error(f"Exception while exporting frequency '{freq_name}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to export frequency: {str(e)}")

    @Slot(str)
    def remove_frequency(self, freq_name: str):
        """Remove a frequency from the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_frequencies(),
                "attributes": {"remove": freq_name}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Removed frequency '{freq_name}' from observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(freq_name, None, "remove")
            else:
                logger.error(f"Failed to remove frequency: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to remove frequency: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while removing frequency: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to remove frequency: {str(e)}")

    @Slot(str)
    def edit_frequency(self, freq_name: str):
        """Edit an existing frequency using IFEditorDialog."""
        try:
            freq_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_frequencies(),
                "attributes": {"get": freq_name}
            })
            if not freq_response["status"]:
                logger.error(f"Failed to retrieve frequency '{freq_name}': {freq_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to retrieve frequency: {freq_response.get('error', 'Unknown error')}")
                return
            
            if_obj = freq_response["result"]
            dialog = IFEditorDialog(if_obj=if_obj, parent=self)
            if dialog.exec() == QDialog.Accepted:
                try:
                    if_data = dialog.get_if_data()
                    request = {
                        "operation": "configure",
                        "obj": self.observation.get_frequencies(),
                        "attributes": {
                            "set_if": {
                                "name": freq_name,
                                "frequency": if_data["frequency"],
                                "bandwidth": if_data["bandwidth"],
                                "polarizations": if_data["polarizations"],
                                "isactive": if_data["isactive"]
                            }
                        }
                    }
                    response = self.manipulator.process_request(request)
                    if response["status"]:
                        logger.info(f"Updated frequency '{freq_name}' in observation '{self.observation.code}'")
                        self.update()
                        self.data_updated.emit(freq_name, if_data["isactive"], "edit")
                    else:
                        logger.error(f"Failed to update frequency: {response.get('error', 'Unknown error')}")
                        QMessageBox.critical(self, "Error", f"Failed to update frequency: {response.get('error', 'Unknown error')}")
                except ValueError as ve:
                    logger.error(f"Validation error while updating frequency: {str(ve)}")
                    QMessageBox.critical(self, "Error", f"Failed to update frequency: {str(ve)}")
        except Exception as e:
            logger.error(f"Exception while editing frequency: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to edit frequency: {str(e)}")

    @Slot(str)
    def activate_frequency(self, freq_name: str):
        """Activate the specified frequency."""
        try:
            freq_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_frequencies(),
                "attributes": {"get": freq_name}
            })
            if not freq_response["status"] or not freq_response["result"]:
                logger.error(f"Failed to get frequency '{freq_name}': {freq_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to activate frequency: {freq_response.get('error', 'Unknown error')}")
                return

            if_obj = freq_response["result"]
            request = {
                "operation": "configure",
                "obj": self.observation.get_frequencies(),
                "attributes": {
                    "set_if": {
                        "name": freq_name,
                        "isactive": True
                    }
                }
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Frequency '{freq_name}' activated in observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(freq_name, True, "activate")
            else:
                logger.error(f"Failed to activate frequency '{freq_name}': {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to activate frequency: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while activating frequency '{freq_name}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to activate frequency: {str(e)}")

    @Slot(str)
    def deactivate_frequency(self, freq_name: str):
        """Deactivate the specified frequency."""
        try:
            freq_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_frequencies(),
                "attributes": {"get": freq_name}
            })
            if not freq_response["status"] or not freq_response["result"]:
                logger.error(f"Failed to get frequency '{freq_name}': {freq_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to deactivate frequency: {freq_response.get('error', 'Unknown error')}")
                return

            if_obj = freq_response["result"]
            request = {
                "operation": "configure",
                "obj": self.observation.get_frequencies(),
                "attributes": {
                    "set_if": {
                        "name": freq_name,
                        "isactive": False
                    }
                }
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Frequency '{freq_name}' deactivated in observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(freq_name, False, "deactivate")
            else:
                logger.error(f"Failed to deactivate frequency '{freq_name}': {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to deactivate frequency: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while deactivating frequency '{freq_name}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to deactivate frequency: {str(e)}")

    @Slot()
    def activate_all_frequencies(self):
        """Activate all frequencies in the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_frequencies(),
                "attributes": {"activate_all": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All frequencies activated in observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(None, None, "activate_all")
            else:
                logger.error(f"Failed to activate all frequencies: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to activate all frequencies: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while activating all frequencies: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to activate all frequencies: {str(e)}")

    @Slot()
    def deactivate_all_frequencies(self):
        """Deactivate all frequencies in the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_frequencies(),
                "attributes": {"deactivate_all": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All frequencies deactivated in observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(None, None, "deactivate_all")
            else:
                logger.error(f"Failed to deactivate all frequencies: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to deactivate all frequencies: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while deactivating all frequencies: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to deactivate all frequencies: {str(e)}")

    @Slot()
    def drop_active_frequencies(self):
        """Remove all active frequencies from the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_frequencies(),
                "attributes": {"drop_active": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All active frequencies dropped from observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(None, None, "drop_active")
            else:
                logger.error(f"Failed to drop active frequencies: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to drop active frequencies: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while dropping active frequencies: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to drop active frequencies: {str(e)}")

    @Slot()
    def drop_inactive_frequencies(self):
        """Remove all inactive frequencies from the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_frequencies(),
                "attributes": {"drop_inactive": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All inactive frequencies dropped from observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(None, None, "drop_inactive")
            else:
                logger.error(f"Failed to drop inactive frequencies: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to drop inactive frequencies: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while dropping inactive frequencies: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to drop inactive frequencies: {str(e)}")

    @Slot()
    def clear_frequencies(self):
        """Clear all frequencies from the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_frequencies(),
                "attributes": {"clear": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All frequencies cleared from observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(None, None, "clear")
            else:
                logger.error(f"Failed to clear frequencies: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to clear frequencies: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while clearing frequencies: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to clear frequencies: {str(e)}")

    @Slot()
    def update(self):
        """Update the frequencies table."""
        self.model.removeRows(0, self.model.rowCount())
        frequencies_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_frequencies": None}
        })
        if frequencies_response["status"] and frequencies_response["result"]:
            freqs = frequencies_response["result"]
            items_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": freqs,
                "attributes": {"get_all": None}
            })
            if items_response["status"] and isinstance(items_response["result"], dict):
                idx = 1
                for name, if_obj in items_response["result"].items():
                    freq_response = self.manipulator.process_request({
                        "operation": "inspect",
                        "obj": if_obj,
                        "attributes": {"get": "frequency"}
                    })
                    frequency = "N/A"
                    if freq_response["status"]:
                        freq_value = freq_response["result"]
                        if isinstance(freq_value, (int, float)):
                            frequency = freq_value
                        else:
                            logger.warning(f"Unexpected frequency value type: {type(freq_value)} for freq '{name}'")
                            frequency = "N/A"

                    is_active_response = self.manipulator.process_request({
                        "operation": "inspect",
                        "obj": if_obj,
                        "attributes": {"get": "isactive"}
                    })
                    is_active = is_active_response["status"] and bool(is_active_response["result"])
                    active_item = QStandardItem()
                    active_item.setIcon(self.active_icon if is_active else self.inactive_icon)
                    active_item.setToolTip("Active" if is_active else "Inactive")
                    active_item.setTextAlignment(Qt.AlignCenter)

                    wavelength_response = self.manipulator.process_request({
                        "operation": "inspect",
                        "obj": if_obj,
                        "attributes": {"get_frequency_wavelength": None}
                    })
                    wavelength = wavelength_response['result'] if wavelength_response["status"] else "N/A"

                    bandwidth_response = self.manipulator.process_request({
                        "operation": "inspect",
                        "obj": if_obj,
                        "attributes": {"get": "bandwidth"}
                    })
                    bandwidth = "N/A"
                    if bandwidth_response["status"]:
                        bw_value = bandwidth_response["result"]
                        if isinstance(bw_value, (int, float)):
                            bandwidth = bw_value
                        else:
                            logger.warning(f"Unexpected bandwidth value type: {type(bw_value)} for freq '{name}'")
                            bandwidth = "N/A"

                    polarizations_response = self.manipulator.process_request({
                        "operation": "inspect",
                        "obj": if_obj,
                        "attributes": {"get": "polarizations"}
                    })
                    polarizations = ", ".join(polarizations_response["result"]) if polarizations_response["status"] and polarizations_response["result"] else "N/A"

                    row = [
                        QStandardItem(str(idx)),
                        active_item,
                        QStandardItem(name),
                        QStandardItem(f"{frequency:.0f}" if isinstance(frequency, (int, float)) else str(frequency)),
                        QStandardItem(f"{wavelength:.2f}" if isinstance(wavelength, (int, float)) else str(wavelength)),
                        QStandardItem(f"{bandwidth:.0f}" if isinstance(bandwidth, (int, float)) else str(bandwidth)),
                        QStandardItem(polarizations)
                    ]
                    for item in row:
                        item.setEditable(False)
                    row[0].setData(name, Qt.UserRole)
                    row[0].setData(idx, Qt.UserRole + 1)
                    self.model.appendRow(row)
                    idx += 1

        self.ui.table.resizeColumnsToContents()
    
    def _cleanup(self):
        """Clean up resources associated with this tab."""
        try:
            self.blockSignals(True)
            self.data_updated.disconnect()
            logger.debug(f"Disconnected data_updated signal for {self.objectName()}")

            self.ui.search.textChanged.disconnect(self.search_changed)
            self.ui.table.customContextMenuRequested.disconnect(self.show_context_menu)
            logger.debug(f"Disconnected UI signals for {self.objectName()}")

            self.ui.table.setModel(None)
            self.model.clear()
            self.proxy_model.deleteLater()
            self.model.deleteLater()
            logger.debug(f"Cleared table model and proxy model for {self.objectName()}")

            self.ui.deleteLater()
            logger.debug(f"Scheduled deletion of UI for {self.objectName()}")

            self.observation = None
            self.project = None
            self.manipulator = None
            self.active_icon = None
            self.inactive_icon = None
        except Exception as e:
            logger.error(f"Error cleaning up {self.objectName()}: {str(e)}")
        finally:
            self.deleteLater()
            logger.debug(f"Scheduled deletion of {self.objectName()}")

    def closeEvent(self, event):
        """Override closeEvent to perform cleanup before closing."""
        self._cleanup()
        super().closeEvent(event)
        logger.debug(f"closeEvent handled for {self.objectName()}")