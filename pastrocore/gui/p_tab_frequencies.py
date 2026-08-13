from PySide6.QtWidgets import QWidget, QMessageBox, QMenu, QDialog, QFileDialog
from PySide6.QtCore import Signal, Slot, Qt, QRegularExpression, QPoint
from PySide6.QtGui import QStandardItem, QIcon
from pastrocore.gui.p_dialog_edit_if import IFEditorDialog
from pastrocore.gui.ui_tab_observation_any import Ui_observation_tab
from pastrocore.gui.p_custom_model import CustomStandardItemModel, CustomSortFilterProxyModel
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from pastrocore.base.frequencies import IF
from msb_arch.utils.logging_setup import logger
from msb_arch import ValidationError
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

        try:
            frequencies = self.manipulator.inspect(self.observation, get_frequencies=None)
            has_frequencies = False
            if frequencies:
                items = self.manipulator.inspect(frequencies, get_all=None)
                has_frequencies = isinstance(items, (list, dict)) and len(items) > 0
            else:
                logger.debug("No frequencies found in observation '%s'", self.observation.code)
        except Exception as e:
            has_frequencies = False
            logger.error("Exception while inspecting frequencies: %s", str(e))

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
            try:
                if_obj = self.manipulator.inspect(self.observation.get_frequencies(), get=freq_name)
                if not if_obj:
                    logger.error("Failed to get frequency '%s': No result returned", freq_name)
                    return
                is_active = self.manipulator.inspect(if_obj, get="isactive")
                is_active = bool(is_active)
            except Exception as e:
                logger.error("Exception while inspecting frequency '%s': %s", freq_name, str(e))
                return

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
                if_obj = dialog.get_if_object()
                freq_name = f"freq_{uuid.uuid4().hex[:32]}"
                self.manipulator.configure(self.observation.get_frequencies(), add=if_obj)
                self.update()
                self.data_updated.emit(freq_name, None, "add")
                logger.info("Added frequency '%s' to observation '%s'", freq_name, self.observation.code)
            except (ValidationError, ValueError) as ve:
                logger.error("Validation error while adding frequency: %s", str(ve))
                QMessageBox.critical(self, "Error", f"Failed to add frequency: {str(ve)}")
            except Exception as e:
                logger.error("Exception while adding frequency: %s", str(e))
                QMessageBox.critical(self, "Error", f"Failed to add frequency: {str(e)}")

    @Slot()
    def import_new_if(self):
        """Import a new frequency into the observation."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Import New Frequency", "", "pAstroCORE Data (*.pastrod)")
        if not file_path:
            logger.info("Import new frequency cancelled: No file selected")
            return

        try:
            response = self.manipulator.load(self.observation.get_frequencies(),
                                             path=file_path, kind=IF)
            imported_if = response["result"]["object"] if isinstance(response, dict) and "status" in response else response["object"]
            freq_name = f"freq_{uuid.uuid4().hex[:32]}"
            imported_if.name = freq_name
            self.manipulator.configure(self.observation.get_frequencies(), add=imported_if)
            logger.info("New frequency '%s' imported successfully to observation '%s'", freq_name, self.observation.code)
            self.update()
            self.data_updated.emit(freq_name, None, "add")
        except Exception as e:
            logger.error("Exception while importing new frequency: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to import frequency: {str(e)}")

    @Slot(str)
    def import_if(self, freq_name: str):
        """Import a frequency to overwrite an existing one."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Frequency", "", "pAstroCORE Data (*.pastrod)")
        if not file_path:
            logger.info("Import frequency '%s' cancelled: No file selected", freq_name)
            return

        try:
            try:
                freq = self.manipulator.inspect(self.observation.get_frequencies(), get=freq_name)
                if not freq:
                    logger.error("Failed to find frequency '%s': No result returned", freq_name)
                    QMessageBox.critical(self, "Error", f"Frequency '{freq_name}' not found")
                    return
            except Exception as e:
                logger.error("Exception while inspecting frequency '%s': %s", freq_name, str(e))
                QMessageBox.critical(self, "Error", f"Failed to find frequency '{freq_name}': {str(e)}")
                return

            response = self.manipulator.load(self.observation.get_frequencies(),
                                             path=file_path, kind=IF)
            imported_if = (response["result"]
                          if isinstance(response, dict) and "status" in response
                          else response)
            imported_if.name = freq_name
    
            try:
                self.manipulator.configure(self.observation.get_frequencies(), set_item={"name": freq_name, "item": imported_if})
                logger.info("Frequency '%s' overwritten successfully in observation '%s'", freq_name, self.observation.code)
                self.update()
                self.data_updated.emit(freq_name, None, "import")
            except Exception as e:
                logger.error("Exception while overwriting frequency '%s': %s", freq_name, str(e))
                QMessageBox.critical(self, "Error", f"Failed to import frequency: {str(e)}")
        except Exception as e:
            logger.error("Exception while importing frequency '%s': %s", freq_name, str(e))
            QMessageBox.critical(self, "Error", f"Failed to import frequency: {str(e)}")

    @Slot(str)
    def export_if(self, freq_name: str):
        """Export a frequency to a file."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Frequency", "", "pAstroCORE Data (*.pastrod)")
        if not file_path:
            logger.info("Export frequency '%s' cancelled: No file selected", freq_name)
            return
        if not file_path.endswith(".pastrod"):
            file_path += ".pastrod"

        try:
            if_obj = self.manipulator.inspect(self.observation.get_frequencies(), get=freq_name)
            if not if_obj:
                logger.error("Failed to get frequency '%s': No result returned", freq_name)
                QMessageBox.critical(self, "Error", f"Frequency '{freq_name}' not found")
                return
            self.manipulator.save(if_obj, path=file_path)
            logger.info("Frequency '%s' exported to '%s'", freq_name, file_path)
        except Exception as e:
            logger.error("Exception while exporting frequency '%s': %s", freq_name, str(e))
            QMessageBox.critical(self, "Error", f"Failed to export frequency: {str(e)}")

    @Slot(str)
    def remove_frequency(self, freq_name: str):
        """Remove a frequency from the observation."""
        try:
            self.manipulator.configure(self.observation.get_frequencies(), remove=freq_name)
            self.update()
            self.data_updated.emit(freq_name, None, "remove")
            logger.info("Removed frequency '%s' from observation '%s'", freq_name, self.observation.code)
        except Exception as e:
            logger.error("Exception while removing frequency: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to remove frequency: {str(e)}")

    @Slot(str)
    def edit_frequency(self, freq_name: str):
        """Edit an existing frequency using IFEditorDialog."""
        try:
            if_obj = self.manipulator.inspect(self.observation.get_frequencies(), get=freq_name)
            if not if_obj:
                logger.error("Failed to retrieve frequency '%s': No result returned", freq_name)
                QMessageBox.critical(self, "Error", f"Failed to retrieve frequency: No result returned")
                return
            
            dialog = IFEditorDialog(if_obj=if_obj, parent=self)
            if dialog.exec() == QDialog.Accepted:
                try:
                    updated_if = dialog.get_if_object()
                    self.manipulator.configure(self.observation.get_frequencies(), set_item={"name": freq_name, "item": updated_if})
                    self.update()
                    self.data_updated.emit(freq_name, updated_if.isactive, "edit")
                    logger.info("Updated frequency '%s' in observation '%s'", freq_name, self.observation.code)
                except (ValidationError, ValueError) as ve:
                    logger.error("Validation error while updating frequency: %s", str(ve))
                    QMessageBox.critical(self, "Error", f"Failed to update frequency: {str(ve)}")
                except Exception as e:
                    logger.error("Exception while updating frequency: %s", str(e))
                    QMessageBox.critical(self, "Error", f"Failed to update frequency: {str(e)}")
        except Exception as e:
            logger.error("Exception while editing frequency: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to edit frequency: {str(e)}")

    @Slot(str)
    def activate_frequency(self, freq_name: str):
        """Activate the specified frequency."""
        try:
            self.manipulator.configure(self.observation.get_frequencies(), activate_item=freq_name)
            self.update()
            self.data_updated.emit(freq_name, True, "activate")
            logger.info("Frequency '%s' activated in observation '%s'", freq_name, self.observation.code)
        except Exception as e:
            logger.error("Exception while activating frequency '%s': %s", freq_name, str(e))
            QMessageBox.critical(self, "Error", f"Failed to activate frequency: {str(e)}")

    @Slot(str)
    def deactivate_frequency(self, freq_name: str):
        """Deactivate the specified frequency."""
        try:
            self.manipulator.configure(self.observation.get_frequencies(), deactivate_item=freq_name)
            self.update()
            self.data_updated.emit(freq_name, False, "deactivate")
            logger.info("Frequency '%s' deactivated in observation '%s'", freq_name, self.observation.code)
        except Exception as e:
            logger.error("Exception while deactivating frequency '%s': %s", freq_name, str(e))
            QMessageBox.critical(self, "Error", f"Failed to deactivate frequency: {str(e)}")

    @Slot()
    def activate_all_frequencies(self):
        """Activate all frequencies in the observation."""
        try:
            self.manipulator.configure(self.observation.get_frequencies(), activate_all=None)
            self.update()
            self.data_updated.emit(None, None, "activate_all")
            logger.info("All frequencies activated in observation '%s'", self.observation.code)
        except Exception as e:
            logger.error("Exception while activating all frequencies: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to activate all frequencies: {str(e)}")

    @Slot()
    def deactivate_all_frequencies(self):
        """Deactivate all frequencies in the observation."""
        try:
            self.manipulator.configure(self.observation.get_frequencies(), deactivate_all=None)
            self.update()
            self.data_updated.emit(None, None, "deactivate_all")
            logger.info("All frequencies deactivated in observation '%s'", self.observation.code)
        except Exception as e:
            logger.error("Exception while deactivating all frequencies: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to deactivate all frequencies: {str(e)}")

    @Slot()
    def drop_active_frequencies(self):
        """Remove all active frequencies from the observation."""
        try:
            self.manipulator.configure(self.observation.get_frequencies(), drop_active=None)
            self.update()
            self.data_updated.emit(None, None, "drop_active")
            logger.info("All active frequencies dropped from observation '%s'", self.observation.code)
        except Exception as e:
            logger.error("Exception while dropping active frequencies: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to drop active frequencies: {str(e)}")

    @Slot()
    def drop_inactive_frequencies(self):
        """Remove all inactive frequencies from the observation."""
        try:
            self.manipulator.configure(self.observation.get_frequencies(), drop_inactive=None)
            self.update()
            self.data_updated.emit(None, None, "drop_inactive")
            logger.info("All inactive frequencies dropped from observation '%s'", self.observation.code)
        except Exception as e:
            logger.error("Exception while dropping inactive frequencies: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to drop inactive frequencies: {str(e)}")

    @Slot()
    def clear_frequencies(self):
        """Clear all frequencies from the observation."""
        try:
            self.manipulator.configure(self.observation.get_frequencies(), clear=None)
            self.update()
            self.data_updated.emit(None, None, "clear")
            logger.info("All frequencies cleared from observation '%s'", self.observation.code)
        except Exception as e:
            logger.error("Exception while clearing frequencies: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to clear frequencies: {str(e)}")

    @Slot()
    def update(self):
        """Update the frequencies table."""
        self.model.removeRows(0, self.model.rowCount())
        try:
            freqs = self.manipulator.inspect(self.observation, get_frequencies=None)
            if not freqs:
                return
            items = self.manipulator.inspect(freqs, get_all=None)
            if not isinstance(items, dict):
                return

            idx = 1
            for name, if_obj in items.items():
                try:
                    frequency = self.manipulator.inspect(if_obj, get="frequency")
                    if not isinstance(frequency, (int, float)):
                        logger.warning("Unexpected frequency value type: %s for freq '%s'", type(frequency), name)
                        frequency = "N/A"

                    is_active = bool(self.manipulator.inspect(if_obj, get="isactive"))
                    active_item = QStandardItem()
                    active_item.setIcon(self.active_icon if is_active else self.inactive_icon)
                    active_item.setToolTip("Active" if is_active else "Inactive")
                    active_item.setTextAlignment(Qt.AlignCenter)

                    wavelength = self.manipulator.inspect(if_obj, get_frequency_wavelength=None)
                    if not isinstance(wavelength, (int, float)):
                        wavelength = "N/A"

                    bandwidth = self.manipulator.inspect(if_obj, get="bandwidth")
                    if not isinstance(bandwidth, (int, float)):
                        logger.warning("Unexpected bandwidth value type: %s for freq '%s'", type(bandwidth), name)
                        bandwidth = "N/A"

                    polarizations = self.manipulator.inspect(if_obj, get="polarizations")
                    polarizations = ", ".join(polarizations) if polarizations else "N/A"

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
                except Exception as e:
                    logger.error("Exception while processing frequency '%s': %s", name, str(e))
                    continue

            self.ui.table.resizeColumnsToContents()
        except Exception as e:
            logger.error("Exception while updating frequencies table: %s", str(e))
    
    def _cleanup(self):
        """Clean up resources associated with this tab."""
        try:
            self.blockSignals(True)
            self.data_updated.disconnect()

            self.ui.search.textChanged.disconnect(self.search_changed)
            self.ui.table.customContextMenuRequested.disconnect(self.show_context_menu)

            self.ui.table.setModel(None)
            self.model.clear()
            self.proxy_model.deleteLater()
            self.model.deleteLater()

            self.observation = None
            self.project = None
            self.manipulator = None
            self.active_icon = None
            self.inactive_icon = None
        except Exception as e:
            logger.error("Error cleaning up %s: %s", self.objectName(), str(e))

    def closeEvent(self, event):
        """Override closeEvent to perform cleanup before closing."""
        self._cleanup()
        super().closeEvent(event)
        logger.debug("closeEvent handled for %s", self.objectName())