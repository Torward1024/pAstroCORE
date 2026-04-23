# pastrocore/gui/p_tab_scans.py
from PySide6.QtWidgets import QWidget, QMessageBox, QMenu, QDialog
from PySide6.QtCore import Signal, Slot, Qt, QRegularExpression, QPoint
from PySide6.QtGui import QStandardItem, QIcon
from .ui_tab_observation_any import Ui_observation_tab
from .p_dialog_edit_scan import ScanEditorDialog
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from msb_arch.utils.logging_setup import logger
from pastrocore.gui.p_tab_telescopes import TelescopesTab
from pastrocore.gui.p_tab_frequencies import FrequenciesTab
from pastrocore.gui.p_tab_sources import SourcesTab
from pastrocore.gui.p_custom_model import CustomStandardItemModel, CustomSortFilterProxyModel

class ScansTab(QWidget):
    """Widget for displaying and managing scans in an observation."""
    data_updated = Signal()

    def __init__(self, observation: Observation, manipulator: ScheduleManipulator,
                 telescopes_tab: 'TelescopesTab' = None, frequencies_tab: 'FrequenciesTab' = None,
                 sources_tab: 'SourcesTab' = None, parent=None):
        super().__init__(parent)
        self.observation = observation
        self.project = manipulator.get_managing_object()
        self.manipulator = manipulator
        self.active_icon = QIcon(":/icons/active_icon.svg")
        self.inactive_icon = QIcon(":/icons/inactive_icon.svg")

        self.ui = Ui_observation_tab()
        self.ui.setupUi(self)
        self.ui.search.setPlaceholderText("Search scans...")
        
        self.model = CustomStandardItemModel()
        self.model.setHorizontalHeaderLabels([
            "#", " ", "Scan ID", "Start Time", "Duration (s)", "Source", "Telescopes", "Frequencies"
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
        self.ui.table.setColumnWidth(0, 50)
        self.ui.table.setColumnHidden(2, True)  
        
        self.ui.search.textChanged.connect(self.search_changed)
        self.ui.table.customContextMenuRequested.connect(self.show_context_menu)

        if telescopes_tab:
            telescopes_tab.data_updated.connect(self.handle_data_updated)
        if frequencies_tab:
            frequencies_tab.data_updated.connect(self.handle_data_updated)
        if sources_tab:
            sources_tab.data_updated.connect(self.handle_data_updated)
            
        self.update()
        logger.info(f"ScansTab initialized for observation '{observation.code}'")

    @Slot(str)
    def search_changed(self, text: str):
        """Handle search text change."""
        reg_exp = QRegularExpression(text)
        self.proxy_model.setFilterRegularExpression(reg_exp)

    def show_context_menu(self, position: QPoint):
        """Show context menu for the scans table."""
        menu = QMenu(self)
        add_action = menu.addAction(QIcon(":/icons/add_icon.svg"), "Add Scan")
        add_action.triggered.connect(self.add_scan)

        try:
            scans = self.manipulator.inspect(self.observation, get_scans=None)
            has_scans = False
            if scans:
                items = self.manipulator.inspect(scans, get_all=None)
                has_scans = isinstance(items, dict) and len(items) > 0
            else:
                logger.debug(f"No scans found in observation '{self.observation.code}'")
        except Exception as e:
            logger.error(f"Exception while inspecting scans: {str(e)}")
            has_scans = False
            logger.debug(f"No scans found in observation '{self.observation.code}'")

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

        index = self.ui.table.indexAt(position)
        if index.isValid():
            source_index = self.proxy_model.mapToSource(index)
            scan_name = self.model.item(source_index.row(), 0).data(Qt.UserRole)
            try:
                scan_obj = self.manipulator.inspect(self.observation.get_scans(), get=scan_name)
                if not scan_obj:
                    logger.error(f"Failed to get scan '{scan_name}': No result returned")
                    return
                is_active = bool(self.manipulator.inspect(scan_obj, get="isactive"))
            except Exception as e:
                logger.error(f"Exception while inspecting scan '{scan_name}': {str(e)}")
                return

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
        missing_components = []

        obs_type = self.manipulator.inspect(self.observation, get="observation_type")
        if not obs_type:
            logger.error(f"Failed to get observation type: No result returned")
            QMessageBox.critical(self, "Error", f"Failed to get observation type: No result returned")
            return

        telescopes = self.manipulator.inspect(self.observation, get_telescopes=None)
        if not telescopes:
            logger.warning(f"No telescopes found in observation")
            missing_components.append("telescopes")
        else:
            telescopes_items = self.manipulator.inspect(telescopes, get_all=None)
            if not telescopes_items:
                logger.warning(f"No telescopes found in observation")
                missing_components.append("telescopes")
            else:
                telescope_count = len(telescopes_items)
                if obs_type == "VLBI" and telescope_count < 2:
                    missing_components.append("at least 2 telescopes (required for VLBI)")
                elif obs_type == "SINGLE_DISH" and telescope_count < 1:
                    missing_components.append("at least 1 telescope (required for SINGLE_DISH)")

        frequencies = self.manipulator.inspect(self.observation, get_frequencies=None)
        if not frequencies:
            logger.warning(f"No frequencies found in observation")
            missing_components.append("frequencies")
        else:
            frequencies_items = self.manipulator.inspect(frequencies, get_all=None)
            if not frequencies_items or len(frequencies_items) < 1:
                logger.error(f"No frequencies found found in observation")
                missing_components.append("at least 1 frequency")

        if missing_components:
            logger.warning(f"Cannot add scan: missing components: {', '.join(missing_components)}")
            QMessageBox.information(
                self,
                "Cannot Add Scan",
                f"Cannot add a scan. Please add the following to the observation:\n- {', '.join(missing_components)}",
                QMessageBox.Ok
            )
            return

        dialog = ScanEditorDialog(self.observation, self.manipulator, scan=None, parent=self)
        if dialog.exec() == QDialog.Accepted:
            try:
                scan = dialog.get_scan_object()
                self.manipulator.configure(self.observation.get_scans(), add=scan)
                self.update()
                self.data_updated.emit()
                logger.info(f"Added scan '{scan.name}' to observation '{self.observation.code}'")
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
            scan = self.manipulator.inspect(self.observation.get_scans(), get=scan_name)
            if not scan:
                logger.error(f"Failed to retrieve scan '{scan_name}': No result returned")
                QMessageBox.critical(self, "Error", f"Failed to retrieve scan: No result returned")
                return
            
            dialog = ScanEditorDialog(self.observation, self.manipulator, scan=scan, parent=self)
            if dialog.exec() == QDialog.Accepted:
                try:
                    scan = dialog.get_scan_object()
                    self.manipulator.configure(self.observation.get_scans(), set_item={"name": scan_name, "item": scan})
                    self.update()
                    self.data_updated.emit()
                    logger.info(f"Updated scan '{scan_name}' in observation '{self.observation.code}' with start={scan.start.isot}")
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
            self.manipulator.configure(self.observation.get_scans(), remove=scan_name)
            self.update()
            self.data_updated.emit()
            logger.info(f"Removed scan '{scan_name}' from observation '{self.observation.code}'")
        except Exception as e:
            logger.error(f"Exception while removing scan: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to remove scan: {str(e)}")

    @Slot(str)
    def activate_scan(self, scan_name: str):
        """Activate the specified scan."""
        try:
            scan_obj = self.manipulator.inspect(self.observation.get_scans(), get=scan_name)
            if not scan_obj:
                logger.error(f"Failed to get scan '{scan_name}': No result returned")
                QMessageBox.critical(self, "Error", f"Failed to activate scan: No result returned")
                return

            can_activate = self.manipulator.inspect(scan_obj, check_activity_status=self.observation)
            if not can_activate:
                logger.warning(f"Scan '{scan_name}' cannot be activated due to invalid configuration")
                QMessageBox.warning(self, "Cannot Activate", "The scan cannot be activated due to missing or inactive telescopes, frequencies, or source.")
                return

            self.manipulator.configure(self.observation.get_scans(), activate_item=scan_name)
            self.update()
            self.data_updated.emit()
            logger.info(f"Scan '{scan_name}' activated in observation '{self.observation.code}'")
        except Exception as e:
            logger.error(f"Exception while activating scan '{scan_name}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to activate scan: {str(e)}")

    @Slot(str)
    def deactivate_scan(self, scan_name: str):
        """Deactivate the specified scan."""
        try:
            self.manipulator.configure(self.observation.get_scans(), deactivate_item=scan_name)
            self.update()
            self.data_updated.emit()
            logger.info(f"Scan '{scan_name}' deactivated in observation '{self.observation.code}'")
        except Exception as e:
            logger.error(f"Exception while deactivating scan '{scan_name}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to deactivate scan: {str(e)}")

    @Slot()
    def activate_all_scans(self):
        """Activate all scans in the observation."""
        try:
            self.manipulator.configure(self.observation.get_scans(), activate_all=self.observation)
            self.update()
            self.data_updated.emit()
            logger.info(f"All scans activated in observation '{self.observation.code}'")
        except Exception as e:
            logger.error(f"Exception while activating all scans: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to activate all scans: {str(e)}")

    @Slot()
    def deactivate_all_scans(self):
        """Deactivate all scans in the observation."""
        try:
            self.manipulator.configure(self.observation.get_scans(), deactivate_all=None)
            self.update()
            self.data_updated.emit()
            logger.info(f"All scans deactivated in observation '{self.observation.code}'")
        except Exception as e:
            logger.error(f"Exception while deactivating all scans: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to deactivate all scans: {str(e)}")

    @Slot()
    def drop_active_scans(self):
        """Remove all active scans from the observation."""
        try:
            self.manipulator.configure(self.observation.get_scans(), drop_active=None)
            self.update()
            self.data_updated.emit()
            logger.info(f"All active scans dropped from observation '{self.observation.code}'")
        except Exception as e:
            logger.error(f"Exception while dropping active scans: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to drop active scans: {str(e)}")

    @Slot()
    def drop_inactive_scans(self):
        """Remove all inactive scans from the observation."""
        try:
            self.manipulator.configure(self.observation.get_scans(), drop_inactive=None)
            self.update()
            self.data_updated.emit()
            logger.info(f"All inactive scans dropped from observation '{self.observation.code}'")
        except Exception as e:
            logger.error(f"Exception while dropping inactive scans: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to drop inactive scans: {str(e)}")

    @Slot()
    def clear_scans(self):
        """Clear all scans from the observation."""
        try:
            self.manipulator.configure(self.observation.get_scans(), clear=None)
            self.update()
            self.data_updated.emit()
            logger.info(f"All scans cleared from observation '{self.observation.code}'")
        except Exception as e:
            logger.error(f"Exception while clearing scans: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to clear scans: {str(e)}")
    
    @Slot(str, bool, str)
    def handle_data_updated(self, entity_name: str, is_active: bool, operation: str):
        """Handle data_updated signal for entity changes by synchronizing all scans.

        Synchronizes each scan in the observation with the current observation state
        using the synchronize_with_observation method, then updates the table.

        Args:
            entity_name (str): Name of the entity that was updated.
            is_active (bool): Activity status of the updated entity.
            operation (str): Type of operation performed (e.g., 'activate', 'deactivate', 'edit').
        """
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

        try:
            scans = self.manipulator.inspect(self.observation.get_scans(), get_all=None)
            if isinstance(scans, dict):
                for scan_name, scan_obj in scans.items():
                    try:
                        self.manipulator.configure(scan_obj, sync_with_observation={"observation": self.observation, "strict": False})
                        logger.debug(f"Synchronized scan '{scan_name}' with observation '{self.observation.code}'")
                    except Exception as e:
                        logger.error(f"Exception while synchronizing scan '{scan_name}': {str(e)}")
                        QMessageBox.warning(
                            self,
                            "Synchronization Warning",
                            f"Failed to synchronize scan '{scan_name}': {str(e)}"
                        )

            self.update()
            self.data_updated.emit()
            logger.info(f"Completed handling data_updated for {entity_type}, operation={operation}, synchronized {len(scans)} scans")
        except Exception as e:
            logger.error(f"Exception while inspecting scans: {str(e)}")
            self.update()
            self.data_updated.emit()
            logger.info(f"Completed handling data_updated for {entity_type}, operation={operation}, no scans synchronized due to error")

    @Slot()
    def update(self):
        """Update the scans table."""
        self.model.removeRows(0, self.model.rowCount())
        try:
            scans = self.manipulator.inspect(self.observation, get_scans=None)
            if not scans:
                logger.debug(f"No scans found in observation '{self.observation.code}'")
                return
            items = self.manipulator.inspect(scans, get_all=None)
            if not isinstance(items, dict):
                logger.debug(f"No valid scans found in observation '{self.observation.code}'")
                return

            idx = 1
            for name, scan_obj in items.items():
                try:
                    is_active = bool(self.manipulator.inspect(scan_obj, get="isactive"))
                    active_item = QStandardItem()
                    active_item.setIcon(self.active_icon if is_active else self.inactive_icon)
                    active_item.setToolTip("Active" if is_active else "Inactive")
                    active_item.setTextAlignment(Qt.AlignCenter)

                    attrs = self.manipulator.inspect(scan_obj, get=["start", "duration", "source", "telescopes", "frequencies", "is_off_source"])
                    if not attrs:
                        logger.error(f"Failed to get attributes for scan '{name}': No result returned")
                        continue

                    start_time = attrs["start"].strftime("%d.%m.%Y %H:%M:%S") if attrs["start"] else "N/A"
                    duration = f"{attrs['duration']:.1f}" if attrs["duration"] else "N/A"
                    source_name = "OFF SOURCE" if attrs["is_off_source"] else (attrs["source"].name if attrs["source"] else "None")
                    telescopes = ", ".join(t.name for t in attrs["telescopes"]) if attrs["telescopes"] else "None"
                    frequencies = ", ".join(f"{f.frequency:.2f} MHz" for f in attrs["frequencies"]) if attrs["frequencies"] else "None"

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
                    row[0].setData(idx, Qt.UserRole + 1)
                    self.model.appendRow(row)
                    idx += 1
                except Exception as e:
                    logger.error(f"Exception while processing scan '{name}': {str(e)}")
                    continue

            self.ui.table.resizeColumnsToContents()
            logger.debug(f"Updated scans table with {self.model.rowCount()} scans for observation '{self.observation.code}'")
        except Exception as e:
            logger.error(f"Exception while updating scans table: {str(e)}")
            logger.debug(f"Updated scans table with {self.model.rowCount()} scans for observation '{self.observation.code}'")

    def _cleanup(self):
        """Clean up resources associated with this tab."""
        try:
            self.blockSignals(True)
            self.data_updated.disconnect()

            self.ui.search.textChanged.disconnect(self.search_changed)
            self.ui.table.customContextMenuRequested.disconnect(self.show_context_menu)

            if self.sender() and hasattr(self.sender(), 'data_updated'):
                self.sender().data_updated.disconnect(self.handle_data_updated)

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
            logger.error(f"Error cleaning up {self.objectName()}: {str(e)}")

    def closeEvent(self, event):
        """Override closeEvent to perform cleanup before closing."""
        self._cleanup()
        super().closeEvent(event)
        logger.debug(f"closeEvent handled for {self.objectName()}")