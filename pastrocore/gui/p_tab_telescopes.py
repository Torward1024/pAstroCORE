from PySide6.QtWidgets import QWidget, QMessageBox, QMenu, QFileDialog, QDialog
from PySide6.QtCore import Signal, Slot, Qt, QRegularExpression, QPoint
from PySide6.QtGui import QStandardItem, QIcon
from pastrocore.gui.ui_tab_observation_any import Ui_observation_tab
from pastrocore.gui.p_dialog_edit_telescope import TelescopeEditorDialog
from pastrocore.gui.p_dialog_edit_space_telescope import SpaceTelescopeEditorDialog
from pastrocore.gui.p_dialog_telescopes_catalog import TelescopesCatalogDialog
from pastrocore.gui.p_custom_model import CustomStandardItemModel, CustomSortFilterProxyModel
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from pastrocore.base.telescope import Telescope
from pastrocore.base.spacetelescope import SpaceTelescope
from pastrocore.utils.catalogmanager import CatalogManager
from msb_arch.utils.logging_setup import logger
import json

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

        try:
            telescopes = self.manipulator.inspect(self.observation, get_telescopes=None)
            has_telescopes = False
            if telescopes:
                items = self.manipulator.inspect(telescopes, get_all=None)
                has_telescopes = isinstance(items, dict) and len(items) > 0
            else:
                logger.debug("No telescopes found in observation '%s'", self.observation.code)
        except Exception as e:
            logger.error("Exception while inspecting telescopes: %s", str(e))
            has_telescopes = False
            logger.debug("No telescopes found in observation '%s'", self.observation.code)

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
            try:
                telescope = self.manipulator.inspect(self.observation.get_telescopes(), get=telescope_name)
                if not telescope:
                    logger.error("Failed to get telescope '%s': No result returned", telescope_name)
                    return
                is_active = bool(self.manipulator.inspect(telescope, get="isactive"))
            except Exception as e:
                logger.error("Exception while inspecting telescope '%s': %s", telescope_name, str(e))
                return

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
        if dialog.exec() == QDialog.Accepted:
            try:
                telescope = dialog.get_telescope_object()
                self.manipulator.configure(self.observation.get_telescopes(), add=telescope)
                self.update()
                self.data_updated.emit(telescope.name, None, "add")
                logger.info("Added telescope '%s' to observation '%s'", telescope.code, self.observation.code)
            except Exception as e:
                logger.error("Exception while adding telescope: %s", str(e))
                QMessageBox.critical(self, "Error", f"Failed to add telescope: {str(e)}")

    @Slot()
    def add_space_telescope(self):
        """Add a new space telescope using SpaceTelescopeEditorDialog."""
        dialog = SpaceTelescopeEditorDialog(parent=self)
        dialog.ui.isActiveCheckBox.setChecked(True)
        if dialog.exec() == QDialog.Accepted:
            try:
                telescope = dialog.get_telescope_object()
                self.manipulator.configure(self.observation.get_telescopes(), add=telescope)
                self.update()
                self.data_updated.emit(telescope.name, None, "add")
                logger.info("Added space telescope '%s' to observation '%s'", telescope.code, self.observation.code)
            except Exception as e:
                logger.error("Exception while adding space telescope: %s", str(e))
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
            existing_telescopes = self.manipulator.inspect(self.observation.get_telescopes(), get_all=None)
            existing_codes = set()
            existing_names = set()
            if isinstance(existing_telescopes, dict):
                for name, telescope in existing_telescopes.items():
                    try:
                        code = self.manipulator.inspect(telescope, get="code")
                        if code:
                            existing_codes.add(code)
                        existing_names.add(name)
                    except Exception as e:
                        logger.error("Failed to retrieve code for telescope '%s': %s", name, str(e))
                        continue

            unique_telescopes = []
            skipped_telescopes = []
            for telescope in telescopes:
                if telescope.name in existing_names or telescope.code in existing_codes:
                    skipped_telescopes.append(telescope.name)
                    logger.info("Skipped telescope '%s' (code: '%s') as it already exists in observation '%s'", telescope.name, telescope.code, self.observation.code)
                    continue
                unique_telescopes.append(telescope)

            if not unique_telescopes:
                logger.warning("No new telescopes to add to observation '%s'", self.observation.code)
                QMessageBox.warning(self, "Warning", f"No new telescopes to add. Skipped: {', '.join(skipped_telescopes) if skipped_telescopes else 'None'}")
                return

            self.manipulator.configure(self.observation.get_telescopes(), add=unique_telescopes)
            for telescope in unique_telescopes:
                logger.info("Added telescope '%s' from catalog to observation '%s'", telescope.code, self.observation.code)
            self.data_updated.emit(None, None, "add_multiple")
            self.update()
            QMessageBox.information(self, "Success", f"Successfully added {len(unique_telescopes)} telescope(s) to observation.")
            if skipped_telescopes:
                QMessageBox.information(self, "Note", f"Skipped {len(skipped_telescopes)} telescope(s) already in observation: {', '.join(skipped_telescopes)}")
        except Exception as e:
            logger.error("Exception while adding telescopes from catalog: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to add telescopes: {str(e)}")

    @Slot()
    def import_new_telescope(self):
        """Import a new telescope into the observation."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Import New Telescope", "", "pAstroCORE Data (*.pastrod)")
        if not file_path:
            logger.info("Import new telescope cancelled: No file selected")
            return

        try:
            response = self.manipulator.load(self.observation.get_telescopes(), path=file_path)
            telescope = (response["result"]
                          if isinstance(response, dict) and "status" in response
                          else response)
            telescope.code = telescope.code
            telescope.name = telescope.name
            self.manipulator.configure(self.observation.get_telescopes(), add=telescope)
            self.update()
            self.data_updated.emit(telescope.name, None, "add")
            logger.info("New telescope '%s' imported successfully to observation '%s'", telescope.name, self.observation.code)
        except Exception as e:
            logger.error("Exception while importing new telescope: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to import telescope: {str(e)}")

    @Slot(str)
    def import_telescope(self, telescope_name: str):
        """Import a telescope to overwrite an existing one."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Telescope", "", "pAstroCORE Data (*.pastrod)")
        if not file_path:
            logger.info("Import telescope '%s' cancelled: No file selected", telescope_name)
            return

        try:
            response = self.manipulator.load(self.observation.get_telescopes(), path=file_path)
            telescope = (response["result"]
                          if isinstance(response, dict) and "status" in response
                          else response)
            telescope.name = telescope_name
            
            try:
                self.manipulator.configure(self.observation.get_telescopes(), set_item={"name": telescope_name, "item": telescope})
                self.update()
                self.data_updated.emit(telescope.name, None, "import")
                logger.info("Telescope '%s' overwritten successfully in observation '%s'", telescope_name, self.observation.code)
            except Exception as e:
                logger.error("Exception while overwriting telescope '%s': %s", telescope_name, str(e))
                QMessageBox.critical(self, "Error", f"Failed to import frequency: {str(e)}")
        except Exception as e:
            logger.error("Exception while importing telescope '%s': %s", telescope_name, str(e))
            QMessageBox.critical(self, "Error", f"Failed to import telescope: {str(e)}")

    @Slot(str)
    def export_telescope(self, telescope_name: str):
        """Export a telescope to a file."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Telescope", "", "pAstroCORE Data (*.pastrod)")
        if not file_path:
            logger.info("Export telescope '%s' cancelled: No file selected", telescope_name)
            return
        if not file_path.endswith(".pastrod"):
            file_path += ".pastrod"

        try:
            telescope = self.manipulator.inspect(self.observation.get_telescopes(), get=telescope_name)
            if not telescope:
                logger.error("Failed to get telescope '%s': No result returned", telescope_name)
                QMessageBox.critical(self, "Error", f"Telescope '{telescope_name}' not found")
                return
            self.manipulator.save(telescope, path=file_path)
            logger.info("Telescope '%s' exported to '%s'", telescope_name, file_path)
        except Exception as e:
            logger.error("Exception while exporting telescope '%s': %s", telescope_name, str(e))
            QMessageBox.critical(self, "Error", f"Failed to export telescope: {str(e)}")

    @Slot(str)
    def remove_telescope(self, telescope_name: str):
        """Remove a telescope from the observation."""
        try:
            self.manipulator.configure(self.observation.get_telescopes(), remove=telescope_name)
            self.update()
            self.data_updated.emit(telescope_name, None, "remove")
            logger.info("Removed telescope '%s' from observation '%s'", telescope_name, self.observation.code)
        except Exception as e:
            logger.error("Exception while removing telescope: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to remove telescope: {str(e)}")

    @Slot(str)
    def edit_telescope(self, telescope_name: str):
        """Edit an existing telescope using appropriate editor dialog."""
        try:
            telescope = self.manipulator.inspect(self.observation.get_telescopes(), get=telescope_name)
            if not telescope:
                logger.error("Failed to retrieve telescope '%s': No result returned", telescope_name)
                QMessageBox.critical(self, "Error", f"Failed to retrieve telescope: No result returned")
                return
            
            if isinstance(telescope, SpaceTelescope):
                dialog = SpaceTelescopeEditorDialog(telescope=telescope, parent=self)
            else:
                dialog = TelescopeEditorDialog(telescope=telescope, parent=self)
            
            if dialog.exec() == QDialog.Accepted:
                try:
                    telescope = dialog.get_telescope_object()
                    self.manipulator.configure(self.observation.get_telescopes(), set_item={"name": telescope_name, "item": telescope})
                    self.update()
                    self.data_updated.emit(telescope_name, telescope.isactive, "edit")
                    logger.info("Updated telescope '%s' in observation '%s'", telescope_name, self.observation.code)
                except Exception as e:
                    logger.error("Exception while updating telescope: %s", str(e))
                    QMessageBox.critical(self, "Error", f"Failed to update telescope: {str(e)}")
        except Exception as e:
            logger.error("Exception while editing telescope: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to edit telescope: {str(e)}")

    @Slot(str)
    def activate_telescope(self, telescope_name: str):
        """Activate the specified telescope."""
        try:
            response = self.manipulator.configure(self.observation.get_telescopes(), activate_item=telescope_name)
            logger.info("Telescope '%s' activated in observation '%s'", telescope_name, self.observation.code)
            self.update()
            self.data_updated.emit(telescope_name, True, "activate")
        except Exception as e:
            logger.error("Exception while activating telescope '%s': %s", telescope_name, str(e))
            QMessageBox.critical(self, "Error", f"Failed to activate telescope: {str(e)}")

    @Slot(str)
    def deactivate_telescope(self, telescope_name: str):
        """Deactivate the specified telescope."""
        try:
            self.manipulator.configure(self.observation.get_telescopes(), deactivate_item=telescope_name)
            self.update()
            self.data_updated.emit(telescope_name, False, "deactivate")
            logger.info("Telescope '%s' deactivated in observation '%s'", telescope_name, self.observation.code)
        except Exception as e:
            logger.error("Exception while deactivating telescope '%s': %s", telescope_name, str(e))
            QMessageBox.critical(self, "Error", f"Failed to deactivate telescope: {str(e)}")

    @Slot()
    def activate_all_telescopes(self):
        """Activate all telescopes in the observation."""
        try:
            self.manipulator.configure(self.observation.get_telescopes(), activate_all=None)
            self.update()
            self.data_updated.emit(None, None, "activate_all")
            logger.info("All telescopes activated in observation '%s'", self.observation.code)
        except Exception as e:
            logger.error("Exception while activating all telescopes: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to activate all telescopes: {str(e)}")

    @Slot()
    def deactivate_all_telescopes(self):
        """Deactivate all telescopes in the observation."""
        try:
            self.manipulator.configure(self.observation.get_telescopes(), deactivate_all=None)
            self.update()
            self.data_updated.emit(None, None, "deactivate_all")
            logger.info("All telescopes deactivated in observation '%s'", self.observation.code)
        except Exception as e:
            logger.error("Exception while deactivating all telescopes: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to deactivate all telescopes: {str(e)}")
    
    @Slot()
    def clear_telescopes(self):
        """Clear all telescopes from the observation."""
        try:
            self.manipulator.configure(self.observation.get_telescopes(), clear=None)
            self.update()
            self.data_updated.emit(None, None, "clear")
            logger.info("All telescopes cleared from observation '%s'", self.observation.code)
        except Exception as e:
            logger.error("Exception while clearing telescopes: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to clear telescopes: {str(e)}")


    @Slot()
    def drop_active_telescopes(self):
        """Remove all active telescopes from the observation."""
        try:
            self.manipulator.configure(self.observation.get_telescopes(), drop_active=None)
            self.update()
            self.data_updated.emit(None, None, "drop_active")
            logger.info("All active telescopes dropped from observation '%s'", self.observation.code)
        except Exception as e:
            logger.error("Exception while dropping active telescopes: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to drop active telescopes: {str(e)}")

    @Slot()
    def drop_inactive_telescopes(self):
        """Remove all inactive telescopes from the observation."""
        try:
            self.manipulator.configure(self.observation.get_telescopes(), drop_inactive=None)
            self.update()
            self.data_updated.emit(None, None, "drop_inactive")
            logger.info("All inactive telescopes dropped from observation '%s'", self.observation.code)
        except Exception as e:
            logger.error("Exception while dropping inactive telescopes: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to drop inactive telescopes: {str(e)}")

    @Slot()
    def update(self):
        """Update the telescopes table."""
        self.model.removeRows(0, self.model.rowCount())
        try:
            telescopes = self.manipulator.inspect(self.observation, get_telescopes=None)
            if not telescopes:
                return
            items = self.manipulator.inspect(telescopes, get_all=None)
            if not isinstance(items, dict):
                return

            idx = 1
            for name, telescope in items.items():
                try:
                    is_active = bool(self.manipulator.inspect(telescope, get="isactive"))
                except Exception as e:
                    logger.error("Failed to retrieve isactive from telescope '%s': %s", name, str(e))
                    is_active = False

                active_item = QStandardItem()
                active_item.setIcon(self.active_icon if is_active else self.inactive_icon)
                active_item.setToolTip("Active" if is_active else "Inactive")
                active_item.setTextAlignment(Qt.AlignCenter)

                try:
                    code = self.manipulator.inspect(telescope, get="code")
                except Exception as e:
                    code = "N/A"
                    logger.error("Failed to retrieve code from telescope '%s': %s", name, str(e))

                try:
                    name = self.manipulator.inspect(telescope, get="name")
                except Exception as e:
                    name = "N/A"
                    logger.error("Failed to retrieve name from telescope '%s': %s", name, str(e))

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
        except Exception as e:
            logger.error("Exception while updating telescopes table: %s", str(e))

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
            logger.error("Error cleaning up %s: %s", self.objectName(), str(e))

    def closeEvent(self, event):
        """Override closeEvent to perform cleanup before closing."""
        self._cleanup()
        super().closeEvent(event)
        logger.debug("closeEvent handled for %s", self.objectName())