from PySide6.QtWidgets import QWidget, QMessageBox, QMenu, QDialog
from PySide6.QtCore import Signal, Slot, Qt, QRegularExpression, QPoint
from PySide6.QtGui import QStandardItem, QIcon
from pastrocore.gui.ui_tab_observation_any import Ui_observation_tab
from pastrocore.gui.p_dialog_edit_source import SourceEditorDialog
from pastrocore.gui.p_dialog_sources_catalog import SourcesCatalogDialog
from pastrocore.gui.p_custom_model import CustomStandardItemModel, CustomSortFilterProxyModel
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from pastrocore.utils.catalogmanager import CatalogManager
from common.utils.logging_setup import logger
import uuid

class SourcesTab(QWidget):
    data_updated = Signal(str, bool, str)

    def __init__(self, observation: Observation, manipulator: ScheduleManipulator, catalog_manager: CatalogManager, parent=None):
        super().__init__(parent)
        self.observation = observation
        self.project = manipulator.get_managing_object()
        self.manipulator = manipulator
        self.catalog_manager = catalog_manager
        self.active_icon = QIcon(":/icons/active_icon.svg")
        self.inactive_icon = QIcon(":/icons/inactive_icon.svg")
        
        self.ui = Ui_observation_tab()
        self.ui.setupUi(self)
        self.ui.search.setPlaceholderText("Search sources...")

        self.model = CustomStandardItemModel()
        self.model.setHorizontalHeaderLabels(["#", " ", "Source Name", "Name J2000", "Alt. Name", "RA", "DEC"])
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
        self.ui.table.setColumnWidth(5, 100)
        self.ui.table.setColumnWidth(6, 100)

        self.ui.search.textChanged.connect(self.search_changed)
        self.ui.table.customContextMenuRequested.connect(self.show_context_menu)
        self.update()

        logger.info(f"SourcesTab initialized for observation '{observation.code}' with catalog_manager id={id(catalog_manager)}")

    @Slot(str)
    def search_changed(self, text: str):
        """Handle search text change."""
        reg_exp = QRegularExpression(text)
        self.proxy_model.setFilterRegularExpression(reg_exp)

    def show_context_menu(self, position: QPoint):
        """Show context menu for the sources table."""
        menu = QMenu(self)
        
        add_action = menu.addAction(QIcon(":/icons/add_icon.svg"), "Add Source")
        add_catalog_action = menu.addAction(QIcon(":/icons/import_icon.svg"), "Add Source from Catalog")
        add_action.triggered.connect(self.add_source)
        add_catalog_action.triggered.connect(self.add_source_from_catalog)

        sources_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_sources": None}
        })
        has_sources = False
        if sources_response["status"] and sources_response["result"]:
            items_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": sources_response["result"],
                "attributes": {"get_all": None}
            })
            has_sources = items_response["status"] and isinstance(items_response["result"], dict) and len(items_response["result"]) > 0
        else:
            logger.error(f"Failed to inspect sources: {sources_response.get('error', 'Unknown error')}")

        if has_sources:
            activate_all_action = menu.addAction(QIcon(":/icons/active_icon.svg"), "Activate All")
            deactivate_all_action = menu.addAction(QIcon(":/icons/inactive_icon.svg"), "Deactivate All")
            drop_active_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Drop Active")
            drop_inactive_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Drop Inactive")
            clear_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Clear")
            activate_all_action.triggered.connect(self.activate_all_sources)
            deactivate_all_action.triggered.connect(self.deactivate_all_sources)
            drop_active_action.triggered.connect(self.drop_active_sources)
            drop_inactive_action.triggered.connect(self.drop_inactive_sources)
            clear_action.triggered.connect(self.clear_sources)

        index = self.ui.table.indexAt(position)
        if index.isValid():
            source_index = self.proxy_model.mapToSource(index)
            source_name = self.model.item(source_index.row(), 0).data(Qt.UserRole)
            source_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_sources(),
                "attributes": {"get": source_name}
            })
            if not source_response["status"] or not source_response["result"]:
                logger.error(f"Failed to get source '{source_name}': {source_response.get('error', 'Unknown error')}")
                return
            source_obj = source_response["result"]
            
            is_active_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": source_obj,
                "attributes": {"get": "isactive"}
            })
            is_active = is_active_response["status"] and bool(is_active_response["result"])

            menu.addSeparator()
            if is_active:
                deactivate_action = menu.addAction(QIcon(":/icons/inactive_icon.svg"), "Deactivate")
                deactivate_action.triggered.connect(lambda: self.deactivate_source(source_name))
            else:
                activate_action = menu.addAction(QIcon(":/icons/active_icon.svg"), "Activate")
                activate_action.triggered.connect(lambda: self.activate_source(source_name))

            menu.addSeparator()
            edit_action = menu.addAction(QIcon(":/icons/edit_icon.svg"), "Edit Source")
            remove_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Remove Source")
            edit_action.triggered.connect(lambda: self.edit_source(source_name))
            remove_action.triggered.connect(lambda: self.remove_source(source_name))
        
        menu.exec(self.ui.table.viewport().mapToGlobal(position))

    @Slot()
    def add_source(self):
        """Add a new source to the observation using SourceEditorDialog."""
        dialog = SourceEditorDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            try:
                source_data = dialog.get_source_data()
                source_name = source_data["name"] or f"source_{uuid.uuid4().hex[:32]}"
                request = {
                    "operation": "configure",
                    "obj": self.observation.get_sources(),
                    "attributes": {
                        "create_source": {
                            "name": source_name,
                            "ra_h": source_data["ra_h"],
                            "ra_m": source_data["ra_m"],
                            "ra_s": source_data["ra_s"],
                            "de_d": source_data["de_d"],
                            "de_m": source_data["de_m"],
                            "de_s": source_data["de_s"],
                            "name_J2000": source_data["name_J2000"],
                            "alt_name": source_data["alt_name"],
                            "flux_table": source_data["flux_table"],
                            "spectral_index": source_data["spectral_index"],
                            "isactive": source_data["isactive"]
                        }
                    }
                }
                response = self.manipulator.process_request(request)
                if response["status"]:
                    logger.info(f"Added source '{source_name}' to observation '{self.observation.code}'")
                    self.update()
                    self.data_updated.emit(source_name, None, "add")
                else:
                    logger.error(f"Failed to add source: {response.get('error', 'Unknown error')}")
                    QMessageBox.critical(self, "Error", f"Failed to add source: {response.get('error', 'Unknown error')}")
            except ValueError as ve:
                logger.error(f"Validation error while adding source: {str(ve)}")
                QMessageBox.critical(self, "Error", f"Failed to add source: {str(ve)}")
            except Exception as e:
                logger.error(f"Exception while adding source: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to add source: {str(e)}")

    @Slot()
    def add_source_from_catalog(self):
        """Add a source from the catalog to the observation."""
        dialog = SourcesCatalogDialog(self.catalog_manager, parent=self, allow_selection=True)
        if dialog.exec() == QDialog.Accepted and dialog.selected_source:
            try:
                source = dialog.selected_source.copy()
                source_name = source.name
                request = {
                    "operation": "configure",
                    "obj": self.observation.get_sources(),
                    "attributes": {
                        "add": source
                    }
                }
                response = self.manipulator.process_request(request)
                if response["status"]:
                    logger.info(f"Added source '{source_name}' from catalog to observation '{self.observation.code}'")
                    self.update()
                    self.data_updated.emit(source_name, None, "add")
                else:
                    logger.error(f"Failed to add source from catalog: {response.get('error', 'Unknown error')}")
                    QMessageBox.critical(self, "Error", f"Failed to add source: {response.get('error', 'Unknown error')}")
            except Exception as e:
                logger.error(f"Exception while adding source from catalog: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to add source: {str(e)}")

    @Slot(str)
    def remove_source(self, source_name: str):
        """Remove a source from the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_sources(),
                "attributes": {"remove": source_name}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Removed source '{source_name}' from observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(source_name, None, "remove")
            else:
                logger.error(f"Failed to remove source: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to remove source: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while removing source: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to remove source: {str(e)}")

    @Slot(str)
    def edit_source(self, source_name: str):
        """Edit an existing source using SourceEditorDialog."""
        try:
            source_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_sources(),
                "attributes": {"get": source_name}
            })
            if not source_response["status"]:
                logger.error(f"Failed to retrieve source '{source_name}': {source_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to retrieve source: {source_response.get('error', 'Unknown error')}")
                return
            
            source_obj = source_response["result"]
            dialog = SourceEditorDialog(source_obj=source_obj, parent=self)
            if dialog.exec() == QDialog.Accepted:
                try:
                    source_data = dialog.get_source_data()
                    request = {
                        "operation": "configure",
                        "obj": self.observation.get_sources(),
                        "attributes": {
                            "set_source": {
                                "name": source_name,
                                "ra_h": source_data["ra_h"],
                                "ra_m": source_data["ra_m"],
                                "ra_s": source_data["ra_s"],
                                "de_d": source_data["de_d"],
                                "de_m": source_data["de_m"],
                                "de_s": source_data["de_s"],
                                "name_J2000": source_data["name_J2000"],
                                "alt_name": source_data["alt_name"],
                                "flux_table": source_data["flux_table"],
                                "spectral_index": source_data["spectral_index"],
                                "isactive": source_data["isactive"]
                            }
                        }
                    }
                    response = self.manipulator.process_request(request)
                    if response["status"]:
                        logger.info(f"Updated source '{source_name}' in observation '{self.observation.code}'")
                        self.update()
                        self.data_updated.emit(source_name, source_data["isactive"], "edit")
                    else:
                        logger.error(f"Failed to update source: {response.get('error', 'Unknown error')}")
                        QMessageBox.critical(self, "Error", f"Failed to update source: {response.get('error', 'Unknown error')}")
                except ValueError as ve:
                    logger.error(f"Validation error while updating source: {str(ve)}")
                    QMessageBox.critical(self, "Error", f"Failed to update source: {str(ve)}")
        except Exception as e:
            logger.error(f"Exception while editing source: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to edit source: {str(e)}")

    @Slot(str)
    def activate_source(self, source_name: str):
        """Activate the specified source."""
        try:
            source_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_sources(),
                "attributes": {"get": source_name}
            })
            if not source_response["status"] or not source_response["result"]:
                logger.error(f"Failed to get source '{source_name}': {source_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to activate source: {source_response.get('error', 'Unknown error')}")
                return

            request = {
                "operation": "configure",
                "obj": self.observation.get_sources(),
                "attributes": {"activate_item": source_name}
                }
            
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Source '{source_name}' activated in observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(source_name, True, "activate")
            else:
                logger.error(f"Failed to activate source '{source_name}': {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to activate source: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while activating source '{source_name}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to activate source: {str(e)}")

    @Slot(str)
    def deactivate_source(self, source_name: str):
        """Deactivate the specified source."""
        try:
            source_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_sources(),
                "attributes": {"get": source_name}
            })
            if not source_response["status"] or not source_response["result"]:
                logger.error(f"Failed to get source '{source_name}': {source_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to deactivate source: {source_response.get('error', 'Unknown error')}")
                return

            request = {
                "operation": "configure",
                "obj": self.observation.get_sources(),
                "attributes": {"deactivate_item": source_name}
                }
            
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Source '{source_name}' deactivated in observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(source_name, False, "deactivate")
            else:
                logger.error(f"Failed to deactivate source '{source_name}': {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to deactivate source: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while deactivating source '{source_name}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to deactivate source: {str(e)}")

    @Slot()
    def activate_all_sources(self):
        """Activate all sources in the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_sources(),
                "attributes": {"activate_all": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All sources activated in observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(None, None, "activate_all")
            else:
                logger.error(f"Failed to activate all sources: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to activate all sources: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while activating all sources: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to activate all sources: {str(e)}")

    @Slot()
    def deactivate_all_sources(self):
        """Deactivate all sources in the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_sources(),
                "attributes": {"deactivate_all": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All sources deactivated in observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(None, None, "deactivate_all")
            else:
                logger.error(f"Failed to deactivate all sources: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to deactivate all sources: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while deactivating all sources: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to deactivate all sources: {str(e)}")

    @Slot()
    def drop_active_sources(self):
        """Remove all active sources from the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_sources(),
                "attributes": {"drop_active": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All active sources dropped from observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(None, None, "drop_active")
            else:
                logger.error(f"Failed to drop active sources: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to drop active sources: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while dropping active sources: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to drop active sources: {str(e)}")

    @Slot()
    def drop_inactive_sources(self):
        """Remove all inactive sources from the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_sources(),
                "attributes": {"drop_inactive": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All inactive sources dropped from observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(None, None, "drop_inactive")
            else:
                logger.error(f"Failed to drop inactive sources: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to drop inactive sources: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while dropping inactive sources: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to drop inactive sources: {str(e)}")

    @Slot()
    def clear_sources(self):
        """Clear all sources from the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_sources(),
                "attributes": {"clear": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All sources cleared from observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(None, None, "clear")
            else:
                logger.error(f"Failed to clear sources: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to clear sources: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while clearing sources: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to clear sources: {str(e)}")

    @Slot()
    def update(self):
        """Update the sources table."""
        self.model.removeRows(0, self.model.rowCount())
        sources_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_sources": None}
        })
        if sources_response["status"] and sources_response["result"]:
            sources = sources_response["result"]
            items_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": sources,
                "attributes": {"get_all": None}
            })
            if items_response["status"] and isinstance(items_response["result"], dict):
                idx = 1
                for name, source_obj in items_response["result"].items():
                    # Получение активности источника
                    is_active_response = self.manipulator.process_request({
                        "operation": "inspect",
                        "obj": source_obj,
                        "attributes": {"get": "isactive"}
                    })
                    is_active = is_active_response["status"] and bool(is_active_response["result"])

                    # Создание элемента для иконки активности
                    active_item = QStandardItem()
                    active_item.setIcon(self.active_icon if is_active else self.inactive_icon)
                    active_item.setToolTip("Active" if is_active else "Inactive")
                    active_item.setTextAlignment(Qt.AlignCenter)

                    # Получение данных источника
                    attrs_response = self.manipulator.process_request({
                        "operation": "inspect",
                        "obj": source_obj,
                        "attributes": {
                            "get": [
                                "name", "name_J2000", "alt_name",
                                "ra_h", "ra_m", "ra_s",
                                "de_d", "de_m", "de_s"
                            ]
                        }
                    })
                    if not attrs_response["status"]:
                        logger.error(f"Failed to get attributes for source '{name}': {attrs_response.get('error', 'Unknown error')}")
                        continue

                    attrs = attrs_response["result"]
                    source_name = attrs.get("name", "N/A")
                    name_J2000 = attrs.get("name_J2000", "") or ""
                    alt_name = attrs.get("alt_name", "") or ""

                    # Форматирование RA
                    ra_h = attrs.get("ra_h", 0.0)
                    ra_m = attrs.get("ra_m", 0.0)
                    ra_s = attrs.get("ra_s", 0.0)
                    ra_str = f"{int(ra_h):02d}:{int(ra_m):02d}:{ra_s:05.1f}"

                    de_d = attrs.get("de_d", 0.0)
                    de_m = attrs.get("de_m", 0.0)
                    de_s = attrs.get("de_s", 0.0)
                    dec_sign = "+" if de_d >= 0 else "-"
                    dec_str = f"{dec_sign}{abs(int(de_d)):02d}:{int(de_m):02d}:{de_s:05.1f}"

                    row = [
                        QStandardItem(str(idx)),
                        active_item,             
                        QStandardItem(source_name),
                        QStandardItem(name_J2000),
                        QStandardItem(alt_name),
                        QStandardItem(ra_str),
                        QStandardItem(dec_str)
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

            self.ui.search.textChanged.disconnect(self.search_changed)
            self.ui.table.customContextMenuRequested.disconnect(self.show_context_menu)

            self.ui.table.setModel(None)
            self.model.clear()
            self.proxy_model.deleteLater()
            self.model.deleteLater()

            self.observation = None
            self.project = None
            self.manipulator = None
            self.catalog_manager = None
            self.active_icon = None
            self.inactive_icon = None
        except Exception as e:
            logger.error(f"Error cleaning up {self.objectName()}: {str(e)}")

    def closeEvent(self, event):
        """Override closeEvent to perform cleanup before closing."""
        self._cleanup()
        super().closeEvent(event)
        logger.debug(f"closeEvent handled for {self.objectName()}")