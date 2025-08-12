from PySide6.QtWidgets import QWidget, QMessageBox, QMenu, QFileDialog, QDialog
from PySide6.QtCore import Signal, Slot, Qt, QRegularExpression, QPoint
from PySide6.QtGui import QStandardItem, QIcon
from pastrocore.gui.ui_tab_observation_any import Ui_observation_tab
from pastrocore.gui.p_dialog_edit_telescope import TelescopeEditorDialog
from pastrocore.gui.p_dialog_edit_space_telescope import SpaceTelescopeEditorDialog
from pastrocore.gui.p_dialog_telescopes_catalog import TelescopesCatalogDialog
from pastrocore.gui.p_custom_model import CustomStandardItemModel, CustomSortFilterProxyModel
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from pastrocore.base.telescope import Telescope
from pastrocore.base.spacetelescope import SpaceTelescope
from pastrocore.utils.catalogmanager import CatalogManager
from common.utils.logging_setup import logger
import json
import uuid

class TelescopesTab(QWidget):
    """Widget for displaying and managing telescopes in an observation."""
    data_updated = Signal(str, bool, str)

    def __init__(self, observation: Observation, manipulator: ScheduleManipulator, catalog_manager: CatalogManager, parent=None):
        super().__init__(parent)
        self.observation = observation
        self.project = manipulator.get_managing_object()
        self.manipulator = manipulator
        self.catalog_manager = catalog_manager
        self.active_icon = QIcon(":/icons/active_icon.svg")
        self.inactive_icon = QIcon(":/icons/inactive_icon.svg")
        
        # Setup UI
        self.ui = Ui_observation_tab()
        self.ui.setupUi(self)
        self.ui.search.setPlaceholderText("Search telescopes...")

        # Setup table
        self.model = CustomStandardItemModel()
        self.model.setHorizontalHeaderLabels(["#", " ", "Code", "Name", "Type"])
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

        # Connect signals
        self.ui.search.textChanged.connect(self.search_changed)
        self.ui.table.customContextMenuRequested.connect(self.show_context_menu)
        self.update()

    @Slot(str)
    def search_changed(self, text: str):
        """Handle search text change."""
        reg_exp = QRegularExpression(text)
        self.proxy_model.setFilterRegularExpression(reg_exp)

    def show_context_menu(self, position: QPoint):
        """Show context menu for the telescopes table."""
        menu = QMenu(self)
        
        add_telescope_action = menu.addAction(QIcon(":/icons/add_icon.svg"), "Add Telescope")
        add_space_telescope_action = menu.addAction(QIcon(":/icons/add_icon.svg"), "Add Space Telescope")
        add_telescope_from_catalog_action = menu.addAction(QIcon(":/icons/import_icon.svg"), "Add Telescope from Catalog")
        import_new_action = menu.addAction(QIcon(":/icons/import_icon.svg"), "Import New Telescope")
        add_telescope_action.triggered.connect(self.add_telescope)
        add_space_telescope_action.triggered.connect(self.add_space_telescope)
        add_telescope_from_catalog_action.triggered.connect(self.add_telescope_from_catalog)
        import_new_action.triggered.connect(self.import_new_telescope)

        telescopes_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_telescopes": None}
        })
        has_telescopes = False
        if telescopes_response["status"] and telescopes_response["result"]:
            items_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": telescopes_response["result"],
                "attributes": {"get_all": None}
            })
            has_telescopes = items_response["status"] and isinstance(items_response["result"], dict) and len(items_response["result"]) > 0
        else:
            logger.debug(f"No telescopes found in observation '{self.observation.code}'")

        if has_telescopes:
            activate_all_action = menu.addAction(QIcon(":/icons/active_icon.svg"), "Activate All")
            deactivate_all_action = menu.addAction(QIcon(":/icons/inactive_icon.svg"), "Deactivate All")
            drop_active_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Drop Active")
            drop_inactive_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Drop Inactive")
            clear_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Clear")
            activate_all_action.triggered.connect(self.activate_all_telescopes)
            deactivate_all_action.triggered.connect(self.deactivate_all_telescopes)
            drop_active_action.triggered.connect(self.drop_active_telescopes)
            drop_inactive_action.triggered.connect(self.drop_inactive_telescopes)
            clear_action.triggered.connect(self.clear_telescopes)

        index = self.ui.table.indexAt(position)
        if index.isValid():
            source_index = self.proxy_model.mapToSource(index)
            telescope_name = self.model.item(source_index.row(), 0).data(Qt.UserRole)
            telescope_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_telescopes(),
                "attributes": {"get": telescope_name}
            })
            if not telescope_response["status"] or not telescope_response["result"]:
                logger.error(f"Failed to get telescope '{telescope_name}': {telescope_response.get('error', 'Unknown error')}")
                return
            telescope = telescope_response["result"]
            
            is_active_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": telescope,
                "attributes": {"get": "isactive"}
            })
            is_active = is_active_response["status"] and bool(is_active_response["result"])

            menu.addSeparator()
            if is_active:
                deactivate_action = menu.addAction(QIcon(":/icons/inactive_icon.svg"), "Deactivate")
                deactivate_action.triggered.connect(lambda: self.deactivate_telescope(telescope_name))
            else:
                activate_action = menu.addAction(QIcon(":/icons/active_icon.svg"), "Activate")
                activate_action.triggered.connect(lambda: self.activate_telescope(telescope_name))

            menu.addSeparator()
            import_action = menu.addAction(QIcon(":/icons/import_icon.svg"), "Import Telescope")
            export_action = menu.addAction(QIcon(":/icons/export_icon.svg"), "Export Telescope")
            import_action.triggered.connect(lambda: self.import_telescope(telescope_name))
            export_action.triggered.connect(lambda: self.export_telescope(telescope_name))
            menu.addSeparator()
            remove_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Remove Telescope")
            edit_action = menu.addAction(QIcon(":/icons/edit_icon.svg"), "Edit Telescope")
            remove_action.triggered.connect(lambda: self.remove_telescope(telescope_name))
            edit_action.triggered.connect(lambda: self.edit_telescope(telescope_name))
        
        menu.exec(self.ui.table.viewport().mapToGlobal(position))

    @Slot()
    def add_telescope(self):
        """Add a new ground-based telescope using TelescopeEditorDialog."""
        dialog = TelescopeEditorDialog(parent=self)
        dialog.ui.codeEdit.setText(f"NT")
        dialog.ui.nameEdit.setText(f"NEWTELESCOPE")
        if dialog.exec() == QDialog.Accepted:
            try:
                telescope_data = dialog.get_telescope_data()
                telescope = Telescope(**telescope_data)
                request = {
                    "operation": "configure",
                    "obj": self.observation.get_telescopes(),
                    "attributes": {"add": telescope}
                }
                response = self.manipulator.process_request(request)
                if response["status"]:
                    logger.info(f"Added telescope '{telescope_data['code']}' to observation '{self.observation.code}'")
                    self.update()
                    self.data_updated.emit(telescope_data['name'], None, "add")
                else:
                    logger.error(f"Failed to add telescope: {response.get('error', 'Unknown error')}")
                    QMessageBox.critical(self, "Error", f"Failed to add telescope: {response.get('error', 'Unknown error')}")
            except Exception as e:
                logger.error(f"Exception while adding telescope: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to add telescope: {str(e)}")

    @Slot()
    def add_space_telescope(self):
        """Add a new space telescope using SpaceTelescopeEditorDialog."""
        dialog = SpaceTelescopeEditorDialog(parent=self)
        dialog.ui.codeEdit.setText(f"ST")
        dialog.ui.nameEdit.setText(f"SPACETELESCOPE")
        dialog.ui.isActiveCheckBox.setChecked(True)
        if dialog.exec() == QDialog.Accepted:
            try:
                telescope_data = dialog.get_telescope_data()
                logger.debug(f"SpaceTelescope data: {telescope_data}")  # Log data for debugging
                telescope = SpaceTelescope(**telescope_data)
                request = {
                    "operation": "configure",
                    "obj": self.observation.get_telescopes(),
                    "attributes": {"add": telescope}
                }
                response = self.manipulator.process_request(request)
                if response["status"]:
                    logger.info(f"Added space telescope '{telescope_data['code']}' to observation '{self.observation.code}'")
                    self.update()
                    self.data_updated.emit(telescope_data['name'], None, "add")
                else:
                    logger.error(f"Failed to add space telescope: {response.get('error', 'Unknown error')}")
                    QMessageBox.critical(self, "Error", f"Failed to add space telescope: {response.get('error', 'Unknown error')}")
            except Exception as e:
                logger.error(f"Exception while adding space telescope: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to add space telescope: {str(e)}")

    @Slot()
    def add_telescope_from_catalog(self):
        """Add multiple telescopes from the catalog to the observation."""
        dialog = TelescopesCatalogDialog(self.catalog_manager, parent=self, allow_selection=True)
        dialog.telescopes_selected.connect(self.handle_telescopes_selected)
        dialog.exec()

    @Slot(list)
    def handle_telescopes_selected(self, telescopes: list):
        """Handle the addition of multiple selected telescopes from the catalog.

        Skips telescopes that already exist in the observation by name or code.

        Args:
            telescopes (list): List of selected Telescope or SpaceTelescope objects.
        """
        try:
            existing_telescopes_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_telescopes(),
                "attributes": {"get_all": None}
            })
            existing_codes = set()
            existing_names = set()
            if existing_telescopes_response["status"] and isinstance(existing_telescopes_response["result"], dict):
                for name, telescope in existing_telescopes_response["result"].items():
                    code_response = self.manipulator.process_request({
                        "operation": "inspect",
                        "obj": telescope,
                        "attributes": {"get": "code"}
                    })
                    if code_response["status"]:
                        existing_codes.add(code_response["result"])
                    existing_names.add(name)

            unique_telescopes = []
            skipped_telescopes = []
            for telescope in telescopes:
                if telescope.name in existing_names or telescope.code in existing_codes:
                    skipped_telescopes.append(telescope.name)
                    logger.info(f"Skipped telescope '{telescope.name}' (code: '{telescope.code}') as it already exists in observation '{self.observation.code}'")
                    continue
                unique_telescopes.append(telescope)

            if not unique_telescopes:
                logger.warning(f"No new telescopes to add to observation '{self.observation.code}'")
                QMessageBox.warning(self, "Warning", f"No new telescopes to add. Skipped: {', '.join(skipped_telescopes) if skipped_telescopes else 'None'}")
                return

            # Add telescopes using BaseContainer.add (copying handled internally)
            request = {
                "operation": "configure",
                "obj": self.observation.get_telescopes(),
                "attributes": {"add": unique_telescopes}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                for telescope in unique_telescopes:
                    logger.info(f"Added telescope '{telescope.code}' from catalog to observation '{self.observation.code}'")
                self.data_updated.emit(None, None, "add_multiple")  # Single emit for all additions
                self.update()
                QMessageBox.information(self, "Success", f"Successfully added {len(unique_telescopes)} telescope(s) to observation.")
                if skipped_telescopes:
                    QMessageBox.information(self, "Note", f"Skipped {len(skipped_telescopes)} telescope(s) already in observation: {', '.join(skipped_telescopes)}")
            else:
                logger.error(f"Failed to add telescopes: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to add telescopes: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while adding telescopes from catalog: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to add telescopes: {str(e)}")

    @Slot()
    def import_new_telescope(self):
        """Import a new telescope into the observation."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Import New Telescope", "", "pAstroCORE Data (*.pastrod)")
        if not file_path:
            logger.info("Import new telescope cancelled: No file selected")
            return

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            telescope_type = data.get("type", "Telescope")
            if telescope_type == "SpaceTelescope":
                telescope = SpaceTelescope.from_dict(data)
            else:
                telescope = Telescope.from_dict(data)
            telescope.code = telescope.code
            telescope.name = telescope.name
            request = {
                "operation": "configure",
                "obj": self.observation.get_telescopes(),
                "attributes": {"add": telescope}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"New telescope '{telescope.name}' imported successfully to observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(telescope.name, None, "add")
                QMessageBox.information(self, "Success", f"Telescope '{telescope.name}' imported successfully.")
            else:
                logger.error(f"Failed to import telescope: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to import telescope: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while importing new telescope: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to import telescope: {str(e)}")

    @Slot(str)
    def import_telescope(self, telescope_name: str):
        """Import a telescope to overwrite an existing one."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Telescope", "", "pAstroCORE Data (*.pastrod)")
        if not file_path:
            logger.info(f"Import telescope '{telescope_name}' cancelled: No file selected")
            return

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            telescope_type = data.get("type", "Telescope")
            data.pop("type", None)
            if telescope_type == "SpaceTelescope":
                telescope = SpaceTelescope.from_dict(data)
            else:
                telescope = Telescope.from_dict(data)
            telescope.name = telescope_name
            request = {
                "operation": "configure",
                "obj": self.observation.get_telescopes(),
                "attributes": {"set_item": {"name": telescope_name, "item": telescope}}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Telescope '{telescope_name}' overwritten successfully in observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit()
                QMessageBox.information(self, "Success", f"Telescope '{telescope_name}' imported successfully.")
            else:
                logger.error(f"Failed to overwrite telescope '{telescope_name}': {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to import telescope: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while importing telescope '{telescope_name}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to import telescope: {str(e)}")

    @Slot(str)
    def export_telescope(self, telescope_name: str):
        """Export a telescope to a file."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Telescope", "", "pAstroCORE Data (*.pastrod)")
        if not file_path:
            logger.info(f"Export telescope '{telescope_name}' cancelled: No file selected")
            return
        if not file_path.endswith(".pastrod"):
            file_path += ".pastrod"

        try:
            telescope_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_telescopes(),
                "attributes": {"get": telescope_name}
            })
            if not telescope_response["status"] or not telescope_response["result"]:
                logger.error(f"Failed to get telescope '{telescope_name}': {telescope_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Telescope '{telescope_name}' not found")
                return
            telescope = telescope_response["result"]
            with open(file_path, "w") as f:
                json.dump(telescope.to_dict(), f, indent=4)
            logger.info(f"Telescope '{telescope_name}' exported to '{file_path}'")
            QMessageBox.information(self, "Success", f"Telescope '{telescope_name}' exported successfully.")
        except Exception as e:
            logger.error(f"Exception while exporting telescope '{telescope_name}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to export telescope: {str(e)}")

    @Slot(str)
    def remove_telescope(self, telescope_name: str):
        """Remove a telescope from the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_telescopes(),
                "attributes": {"remove": telescope_name}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Removed telescope '{telescope_name}' from observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(telescope_name, None, "remove")
            else:
                logger.error(f"Failed to remove telescope: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to remove telescope: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while removing telescope: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to remove telescope: {str(e)}")

    @Slot(str)
    def edit_telescope(self, telescope_name: str):
        """Edit an existing telescope using appropriate editor dialog."""
        try:
            telescope_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_telescopes(),
                "attributes": {"get": telescope_name}
            })
            if not telescope_response["status"] or not telescope_response["result"]:
                logger.error(f"Failed to retrieve telescope '{telescope_name}': {telescope_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to retrieve telescope: {telescope_response.get('error', 'Unknown error')}")
                return
            
            telescope = telescope_response["result"]
            if isinstance(telescope, SpaceTelescope):
                dialog = SpaceTelescopeEditorDialog(telescope=telescope, parent=self)
            else:
                dialog = TelescopeEditorDialog(telescope=telescope, parent=self)
            
            if dialog.exec() == QDialog.Accepted:
                try:
                    telescope_data = dialog.get_telescope_data()
                    for key, value in telescope_data.items():
                        if hasattr(telescope, key):
                            setattr(telescope, key, value)
                        else:
                            logger.warning(f"Attribute '{key}' not found in telescope object")
                    
                    request = {
                        "operation": "configure",
                        "obj": self.observation.get_telescopes(),
                        "attributes": {"set_item": {"name": telescope_name, "item": telescope}}
                    }
                    response = self.manipulator.process_request(request)
                    if response["status"]:
                        logger.info(f"Updated telescope '{telescope_name}' in observation '{self.observation.code}'")
                        self.update()
                        self.data_updated.emit(telescope_name, telescope_data["isactive"], "edit")
                    else:
                        logger.error(f"Failed to update telescope: {response.get('error', 'Unknown error')}")
                        QMessageBox.critical(self, "Error", f"Failed to update telescope: {response.get('error', 'Unknown error')}")
                except Exception as e:
                    logger.error(f"Exception while updating telescope: {str(e)}")
                    QMessageBox.critical(self, "Error", f"Failed to update telescope: {str(e)}")
        except Exception as e:
            logger.error(f"Exception while editing telescope: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to edit telescope: {str(e)}")

    @Slot(str)
    def activate_telescope(self, telescope_name: str):
        """Activate the specified telescope."""
        try:
            telescope_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_telescopes(),
                "attributes": {"get": telescope_name}
            })
            if not telescope_response["status"] or not telescope_response["result"]:
                logger.error(f"Failed to get telescope '{telescope_name}': {telescope_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to activate telescope: {telescope_response.get('error', 'Unknown error')}")
                return

            request = {
                "operation": "configure",
                "obj": self.observation.get_telescopes(),
                "attributes": {"activate_item": telescope_name}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Telescope '{telescope_name}' activated in observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(telescope_name, True, "activate")
            else:
                logger.error(f"Failed to activate telescope '{telescope_name}': {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to activate telescope: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while activating telescope '{telescope_name}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to activate telescope: {str(e)}")

    @Slot(str)
    def deactivate_telescope(self, telescope_name: str):
        """Deactivate the specified telescope."""
        try:
            telescope_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation.get_telescopes(),
                "attributes": {"get": telescope_name}
            })
            if not telescope_response["status"] or not telescope_response["result"]:
                logger.error(f"Failed to get telescope '{telescope_name}': {telescope_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to deactivate telescope: {telescope_response.get('error', 'Unknown error')}")
                return

            request = {
                "operation": "configure",
                "obj": self.observation.get_telescopes(),
                "attributes": {"deactivate_item": telescope_name}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Telescope '{telescope_name}' deactivated in observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(telescope_name, False, "deactivate")
            else:
                logger.error(f"Failed to deactivate telescope '{telescope_name}': {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to deactivate telescope: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while deactivating telescope '{telescope_name}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to deactivate telescope: {str(e)}")

    @Slot()
    def activate_all_telescopes(self):
        """Activate all telescopes in the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_telescopes(),
                "attributes": {"activate_all": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All telescopes activated in observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(None, None, "activate_all")
            else:
                logger.error(f"Failed to activate all telescopes: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to activate all telescopes: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while activating all telescopes: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to activate all telescopes: {str(e)}")

    @Slot()
    def deactivate_all_telescopes(self):
        """Deactivate all telescopes in the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_telescopes(),
                "attributes": {"deactivate_all": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All telescopes deactivated in observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(None, None, "deactivate_all")
            else:
                logger.error(f"Failed to deactivate all telescopes: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to deactivate all telescopes: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while deactivating all telescopes: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to deactivate all telescopes: {str(e)}")
    
    @Slot()
    def clear_telescopes(self):
        """Clear all telescopes from the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_telescopes(),
                "attributes": {"clear": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All telescopes cleared from observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(None, None, "clear")
            else:
                logger.error(f"Failed to clear telescopes: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to clear telescopes: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while clearing telescopes: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to clear telescopes: {str(e)}")


    @Slot()
    def drop_active_telescopes(self):
        """Remove all active telescopes from the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_telescopes(),
                "attributes": {"drop_active": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All active telescopes dropped from observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(None, None, "drop_active")
            else:
                logger.error(f"Failed to drop active telescopes: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to drop active telescopes: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while dropping active telescopes: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to drop active telescopes: {str(e)}")

    @Slot()
    def drop_inactive_telescopes(self):
        """Remove all inactive telescopes from the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_telescopes(),
                "attributes": {"drop_inactive": None}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All inactive telescopes dropped from observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit(None, None, "drop_inactive")
            else:
                logger.error(f"Failed to drop inactive telescopes: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to drop inactive telescopes: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while dropping inactive telescopes: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to drop inactive telescopes: {str(e)}")

    @Slot()
    def update(self):
        """Update the telescopes table."""
        self.model.removeRows(0, self.model.rowCount())
        telescopes_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_telescopes": None}
        })
        if telescopes_response["status"] and telescopes_response["result"]:
            telescopes = telescopes_response["result"]
            items_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": telescopes,
                "attributes": {"get_all": None}
            })
            if items_response["status"] and isinstance(items_response["result"], dict):
                idx = 1
                for name, telescope in items_response["result"].items():
                    is_active_response = self.manipulator.process_request({
                        "operation": "inspect",
                        "obj": telescope,
                        "attributes": {"get": "isactive"}
                    })
                    is_active = is_active_response["status"] and bool(is_active_response["result"])
                    active_item = QStandardItem()
                    active_item.setIcon(self.active_icon if is_active else self.inactive_icon)
                    active_item.setToolTip("Active" if is_active else "Inactive")
                    active_item.setTextAlignment(Qt.AlignCenter)

                    code_response = self.manipulator.process_request({
                        "operation": "inspect",
                        "obj": telescope,
                        "attributes": {"get": "code"}
                    })
                    code = code_response["result"] if code_response["status"] else "N/A"

                    name_response = self.manipulator.process_request({
                        "operation": "inspect",
                        "obj": telescope,
                        "attributes": {"get": "name"}
                    })
                    name = name_response["result"] if name_response["status"] else "N/A"

                    telescope_type = "Space Telescope" if isinstance(telescope, SpaceTelescope) else "Ground Telescope"

                    row = [
                        QStandardItem(str(idx)),
                        active_item,
                        QStandardItem(code),
                        QStandardItem(name),
                        QStandardItem(telescope_type)
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