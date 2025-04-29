from PySide6.QtWidgets import QWidget, QMessageBox, QMenu, QDialog
from PySide6.QtCore import Signal, Slot, Qt, QSortFilterProxyModel, QRegularExpression, QPoint
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
from pastrocore.gui.p_dialog_edit_if import IFEditorDialog
from pastrocore.gui.ui_tab_observation_any import Ui_observation_tab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
import pastrocore.gui.rc_icons
import uuid

class FrequenciesTab(QWidget):
    data_updated = Signal()

    def __init__(self, observation: Observation, project: ScheduleProject, manipulator: ScheduleManipulator, parent=None):
        super().__init__(parent)
        self.observation = observation
        self.project = project
        self.manipulator = manipulator
        self.active_icon = QIcon(":/icons/active_icon.svg")
        self.inactive_icon = QIcon(":/icons/inactive_icon.svg")
        
        # Настройка UI
        self.ui = Ui_observation_tab()
        self.ui.setupUi(self)
        self.ui.search.setPlaceholderText("Search frequencies...")

        # Настройка таблицы
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels([
            "#", " ", "IF (MHz)", "λ (cm)", "Bandwidth (MHz)", "Polarizations"
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

        # Подключение сигналов
        self.ui.search.textChanged.connect(self.on_search_changed)
        self.ui.table.customContextMenuRequested.connect(self.show_context_menu)

    @Slot(str)
    def on_search_changed(self, text: str):
        """Handle search text change."""
        reg_exp = QRegularExpression(text)
        self.proxy_model.setFilterRegularExpression(reg_exp)

    def show_context_menu(self, position: QPoint):
        """Show context menu for the frequencies table."""
        index = self.ui.table.indexAt(position)
        menu = QMenu(self)
        add_action = menu.addAction(QIcon(":/icons/add_icon.svg"), "Add Frequency")
        add_action.triggered.connect(self.add_frequency)
        
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

            if is_active:
                deactivate_action = menu.addAction(QIcon(":/icons/inactive_icon.svg"), "Deactivate")
                deactivate_action.triggered.connect(lambda: self.deactivate_frequency(freq_name))
            else:
                activate_action = menu.addAction(QIcon(":/icons/active_icon.svg"), "Activate")
                activate_action.triggered.connect(lambda: self.activate_frequency(freq_name))

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
                    self.data_updated.emit()
                else:
                    logger.error(f"Failed to add frequency: {response.get('error', 'Unknown error')}")
                    QMessageBox.critical(self, "Error", f"Failed to add frequency: {response.get('error', 'Unknown error')}")
            except ValueError as ve:
                logger.error(f"Validation error while adding frequency: {str(ve)}")
                QMessageBox.critical(self, "Error", f"Failed to add frequency: {str(ve)}")
            except Exception as e:
                logger.error(f"Exception while adding frequency: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to add frequency: {str(e)}")

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
                self.data_updated.emit()
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
                        self.data_updated.emit()
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
                self.data_updated.emit()
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
                self.data_updated.emit()
            else:
                logger.error(f"Failed to deactivate frequency '{freq_name}': {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to deactivate frequency: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while deactivating frequency '{freq_name}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to deactivate frequency: {str(e)}")

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
                        QStandardItem(f"{frequency:.0f}" if isinstance(frequency, (int, float)) else str(frequency)),
                        QStandardItem(f"{wavelength:.2f}" if isinstance(wavelength, (int, float)) else str(wavelength)),
                        QStandardItem(f"{bandwidth:.0f}" if isinstance(bandwidth, (int, float)) else str(bandwidth)),
                        QStandardItem(polarizations)
                    ]
                    for item in row:
                        item.setEditable(False)
                    row[0].setData(name, Qt.UserRole)
                    self.model.appendRow(row)
                    idx += 1

        self.ui.table.resizeColumnsToContents()