# PySide6 files
from PySide6.QtWidgets import (
                                QMainWindow, 
                                QApplication,
                                QFileDialog, QMessageBox,
                                QTreeView, QTabBar, QProgressDialog, QMenu,
                                QDialog,
                                QWidget
                                )
from PySide6 import QtCore
from PySide6.QtCore import Qt, Signal, Slot, QPoint, QObject
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
# Core files
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from pastrocore.utils.catalogmanager import CatalogManager
# UI files
from pastrocore.gui.ui_main_window import Ui_MainWindow
from pastrocore.gui.p_dialog_calculations import CalculationDialog
from pastrocore.gui.p_dialog_about import AboutDialog
from pastrocore.gui.p_dialog_preferences import PreferencesDialog
from pastrocore.gui.p_dialog_sources_catalog import SourcesCatalogDialog
from pastrocore.gui.p_dialog_telescopes_catalog import TelescopesCatalogDialog
from pastrocore.gui.p_tab_project import ProjectInfoTab
from pastrocore.gui.p_tab_observation import ObservationTab
from pastrocore.gui.p_dialog_add_observation import AddObservationDialog
from pastrocore.gui.p_dialog_visualize import VisualizationDialog
from pastrocore.gui.p_dialog_generate_observations import GenerateObservationsDialog
from pastrocore.gui.p_dialog_export_calculated_data import ExportCalculatedDataDialog
# Common/utils files
from common.utils.logging_setup import (
                                        logger, 
                                        setup_logging, 
                                        update_logging_level, 
                                        update_logging_clear
                                        )
import logging
import sys
import os
import json
# GUI resource file
import pastrocore.gui.rc_icons

class PAstroCoreMainWindow(QMainWindow):
    """Main application window for pAstroCORE."""
    project_updated = Signal()

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.settings = self.load_settings()
        self._dock_was_visible = True
        self._sync_in_progress = False 
    
        log_level_str = self.settings.get("log_level", "INFO")
        log_level = getattr(logging, log_level_str, logging.INFO)
        clear_log = self.settings.get("clear_log_on_start", False)
        logger = setup_logging(log_file="output.log", log_level=log_level, clear_log=clear_log)
        update_logging_level(log_level)
        update_logging_clear("output.log", clear_log)
        logger.debug(f"Logging initialized with clear_log={clear_log}")
    
        self.project = ScheduleProject(name="Untitled Project")
        self.manipulator = ScheduleManipulator(self.project)
        self.catalog_manager = self.initialize_catalog_manager()
    
        logger.debug(f"pAstroCORE initialized with project id: {id(self.project)}, manipulator id={id(self.manipulator)}, catalog_manager id={id(self.catalog_manager)}")
    
        self.current_project_path = None
        self._action_connections = {}
        self.setup_ui()
        self.setup_connections()

    def clear_connections(self, is_initial_setup: bool = False):
        """
        Disconnect all action signals to prevent duplicates.

        Args:
            is_initial_setup (bool): If True, skip disconnecting signals that may not be connected yet (used during initial setup).
        """
        if is_initial_setup:
            logger.debug("Skipping UI signal disconnection during initial setup")
            return

        for action, slot in self._action_connections.items():
            try:
                action.triggered.disconnect(slot)
                logger.debug(f"Disconnected signal for action {action.objectName()}")
            except TypeError as e:
                logger.debug(f"No signal to disconnect for action {action.objectName()}: {str(e)}")
        self._action_connections.clear()

        try:
            if self.receivers(QtCore.SIGNAL("project_updated()")) > 0:
                self.project_updated.disconnect()
                logger.debug("Disconnected project_updated signal")
            else:
                logger.debug("No active connections for project_updated signal")
        except TypeError as e:
            logger.debug(f"Error checking project_updated signal: {str(e)}")

        project_explorer = self.ui.dockWidget.findChild(QTreeView, "projectExplorer")
        if project_explorer:
            try:
                if project_explorer.receivers(QtCore.SIGNAL("clicked(QModelIndex)")) > 0:
                    project_explorer.clicked.disconnect(self.handle_project_explorer_click)
                    logger.debug("Disconnected project explorer clicked signal")
                else:
                    logger.debug("No active connections for project explorer clicked signal")
            except TypeError as e:
                logger.debug(f"Error checking project explorer clicked signal: {str(e)}")
        else:
            logger.debug("Project explorer widget not found during clear_connections")

        tab_container = self.ui.tabContainer
        if tab_container:
            try:
                if tab_container.receivers(QtCore.SIGNAL("tabCloseRequested(int)")) > 0:
                    tab_container.tabCloseRequested.disconnect(self.handle_tab_close)
                    logger.debug("Disconnected tabCloseRequested signal")
                else:
                    logger.debug("No active connections for tabCloseRequested signal")
            except TypeError as e:
                logger.debug(f"Error checking tabCloseRequested signal: {str(e)}")

        try:
            if self.ui.actionProject_Explorer.receivers(QtCore.SIGNAL("toggled(bool)")) > 0:
                self.ui.actionProject_Explorer.toggled.disconnect()
                logger.debug("Disconnected actionProject_Explorer.toggled signal")
            else:
                logger.debug("No active connections for actionProject_Explorer toggled signal")
        except TypeError as e:
            logger.debug(f"Error checking actionProject_Explorer toggled signal: {str(e)}")

        try:
            if self.ui.dockWidget.receivers(QtCore.SIGNAL("visibilityChanged(bool)")) > 0:
                self.ui.dockWidget.visibilityChanged.disconnect()
                logger.debug("Disconnected dockWidget.visibilityChanged signal")
            else:
                logger.debug("No active connections for dockWidget visibilityChanged signal")
        except TypeError as e:
            logger.debug(f"Error checking dockWidget visibilityChanged signal: {str(e)}")     
    
    def initialize_catalog_manager(self):
        """Initialize CatalogManager with paths from settings or defaults."""
        default_sources_path = os.path.join("catalogs", "sources.dat")
        default_telescopes_path = os.path.join("catalogs", "telescopes.dat")
        sources_path = self.settings.get("sources_catalog_path", default_sources_path)
        telescopes_path = self.settings.get("telescopes_catalog_path", default_telescopes_path)

        try:
            if not os.path.isfile(sources_path):
                logger.warning(f"Sources catalog file not found: {sources_path}. Initializing empty source catalog.")
            if not os.path.isfile(telescopes_path):
                logger.warning(f"Telescopes catalog file not found: {telescopes_path}. Initializing empty telescope catalog.")
                
            catalog_manager = CatalogManager(source_file=sources_path, telescope_file=telescopes_path)
            sources_count = len(catalog_manager.source_catalog.get_items())
            telescopes_count = len(catalog_manager.telescope_catalog.get_items())
            logger.info(f"Catalog initialized with {sources_count} sources and {telescopes_count} telescopes")
            return catalog_manager
        except Exception as e:
            logger.error(f"Failed to initialize CatalogManager with sources='{sources_path}', telescopes='{telescopes_path}': {str(e)}")
            QMessageBox.warning(self, "Warning", f"Failed to load catalogs: {str(e)}. Using empty catalogs.")
            return CatalogManager()

    def setup_ui(self):
        """Setup the UI components and their initial states."""

        self.ui.dockWidget.setVisible(True)
        self.ui.actionProject_Explorer.setChecked(True)
        self._dock_was_visible = True
        self.update_project_explorer()

        for i in range(self.ui.tabContainer.count()):
            if self.ui.tabContainer.widget(i).objectName() == "tabWelcome":
                self.ui.tabContainer.removeTab(i)
                break
        self.open_project_info_tab()
        self.ui.tabContainer.setTabsClosable(True)

        for i in range(self.ui.tabContainer.count()):
            if self.ui.tabContainer.widget(i).objectName() == "projectInfoTab":
                self.ui.tabContainer.tabBar().setTabButton(i, QTabBar.ButtonPosition.RightSide, None)

        project_explorer = self.ui.dockWidget.findChild(QTreeView, "projectExplorer")
        if project_explorer:
            project_explorer.setContextMenuPolicy(Qt.CustomContextMenu)
            project_explorer.customContextMenuRequested.connect(self.show_context_menu)
        else:
            logger.error("Project explorer widget not found during setup_ui")
        self.ui.actionProject_Explorer.toggled.connect(self.ui.dockWidget.setVisible)

    def setup_connections(self):
        """Setup UI signal connections."""
        self.clear_connections(is_initial_setup=True)
        
        self._action_connections = {
            self.ui.actionNewProject: self.new_project,
            self.ui.actionOpenProject: self.open_project,
            self.ui.actionSaveProject: self.save_project,
            self.ui.actionSave_Project_As: self.save_project_as,
            self.ui.actionExit: self.close,
            self.ui.actionPreferences: self.open_preferences,
            self.ui.actionAbout: self.show_about,
            self.ui.actionSource_Catalog_Manager: self.open_source_catalog_manager,
            self.ui.actionTelescope_Catalog_Manager: self.open_telescope_catalog_manager,
            self.ui.actionCalculate: self.open_calculation_dialog,
            self.ui.actionVisualize: self.open_visualization_dialog,
            self.ui.actionGenerate_Observations: self.handle_generate_observations,
            self.ui.actionExport_Calulcated_Data: self.open_export_dialog
        }

        for action, slot in self._action_connections.items():
            action.triggered.connect(slot)

        project_explorer = self.ui.dockWidget.findChild(QTreeView, "projectExplorer")
        if project_explorer:
            project_explorer.clicked.connect(self.handle_project_explorer_click)
        self.ui.tabContainer.tabCloseRequested.connect(self.handle_tab_close)
        self.ui.actionProject_Explorer.toggled.connect(self.ui.dockWidget.setVisible)
        self.ui.dockWidget.visibilityChanged.connect(self.sync_project_explorer_action)
        
        self.project_updated.connect(self.update_project_explorer)

    @Slot()
    def open_export_dialog(self):
        """Open the Export Calculated Data dialog."""
        try:
            dialog = ExportCalculatedDataDialog(self.manipulator, self)
            if dialog.exec() == QDialog.Accepted:
                logger.debug("Export Calculated Data dialog accepted")
            else:
                logger.debug("Export Calculated Data dialog rejected")
        except Exception as e:
            logger.error(f"Error opening Export Calculated Data dialog: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to open Export Calculated Data dialog: {str(e)}")

    @Slot()
    def open_calculation_dialog(self):
        """Open the calculation dialog with time_step from settings."""
        try:
            dialog = CalculationDialog(self.manipulator, time_step=self.settings.get("time_step", 600), parent=self)
            dialog.time_step_updated.connect(self.handle_time_step_updated)
            dialog.exec()
        except Exception as e:
            logger.error(f"Failed to open calculation dialog: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to open calculation dialog: {str(e)}")
    
    @Slot()
    def open_visualization_dialog(self):
        """Open the visualization dialog for the current project."""
        try:
            dialog = VisualizationDialog(self.manipulator, parent=self)
            dialog.exec()
        except Exception as e:
            logger.error(f"Failed to open visualization dialog: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to open visualization dialog: {str(e)}")

    def handle_tab_close(self, index):
        """Handle closing of tabs, prevent closing of project tab, and clean up resources."""
        widget = self.ui.tabContainer.widget(index)
        if widget and widget.objectName() == "projectInfoTab":
            return
        self._cleanup_widget(widget)
        self.ui.tabContainer.removeTab(index)
        logger.debug(f"Closed tab at index {index} and cleaned up resources")
    
    def _cleanup_widget(self, widget: QWidget):
        """Clean up widget resources and disconnect signals."""
        try:
            widget.blockSignals(True)
            if hasattr(widget, 'observation_updated'):
                try:
                    widget.observation_updated.disconnect()
                    logger.debug(f"Disconnected observation_updated signal for {widget.objectName()}")
                except Exception as e:
                    logger.debug(f"No observation_updated signal to disconnect: {str(e)}")
            if hasattr(widget, 'project_name_changed'):
                try:
                    widget.project_name_changed.disconnect()
                    logger.debug(f"Disconnected project_name_changed signal for {widget.objectName()}")
                except Exception as e:
                    logger.debug(f"No project_name_changed signal to disconnect: {str(e)}")

            for child in widget.findChildren(QObject):
                child.blockSignals(True)
                child.deleteLater()
            widget.deleteLater()
            logger.debug(f"Scheduled deletion of widget {widget.objectName()}")
        except Exception as e:
            logger.error(f"Error cleaning up widget {widget.objectName()}: {str(e)}")

    @Slot(dict)
    def handle_time_step_updated(self, time_step: int):
        """Handle time_step updated signal from CalculationDialog."""
        self.settings["time_step"] = time_step
        self.save_settings(self.settings)
        logger.debug(f"time_step updated to {time_step} and saved to settings")

    def show_context_menu(self, position: QPoint):
        """Show context menu for Project Explorer."""
        project_explorer = self.ui.dockWidget.findChild(QTreeView, "projectExplorer")
        if not project_explorer:
            return

        index = project_explorer.indexAt(position)
        if not index.isValid():
            return

        item = project_explorer.model().itemFromIndex(index)
        if not item:
            return

        item_type = item.data(Qt.UserRole)
        text = item.text()
        menu = QMenu(self)
        add_action = None
        add_obs_action = None
        remove_action = None
        edit_action = None

        if item_type == "project":
            menu.addAction(QIcon(":/icons/remove_project_icon.svg"), "New Project")
            menu.addAction(QIcon(":/icons/edit_observation_icon.svg"), "Edit Project")
            menu.addSeparator()
            add_action = menu.addAction(QIcon(":/icons/add_observation_icon.svg"), "Add Observation")
            add_obs_action = menu.addAction(QIcon(":/icons/add_icon.svg"), "Add Observations")
            menu.addSeparator()
            remove_action = menu.addAction(QIcon(":/icons/remove_project_icon.svg"), "Remove Observations")
        elif item_type == "observations" or item_type == "observation":
            add_action = menu.addAction(QIcon(":/icons/add_observation_icon.svg"), "Add Observation")
            if item_type == "observation":
                obs_name = item.data(Qt.UserRole + 1)
                obs_code = text
                edit_action = menu.addAction(QIcon(":/icons/edit_observation_icon.svg"), "Edit Observation")
                menu.addSeparator()
                remove_action = menu.addAction(QIcon(":/icons/remove_observation_icon.svg"), "Remove Observation")
                remove_action.triggered.connect(lambda: self.remove_observation(obs_name, obs_code))
                edit_action.triggered.connect(lambda: self.edit_observation(obs_name, obs_code))
            else:
                add_obs_action = menu.addAction(QIcon(":/icons/add_icon.svg"), "Add Observations")
                menu.addSeparator()
                remove_action = menu.addAction(QIcon(":/icons/remove_project_icon.svg"), "Remove Observations")
        else:
            return

        if add_action:
            add_action.triggered.connect(self.add_observation)
        if add_obs_action:
            add_obs_action.triggered.connect(self.handle_generate_observations)
        if remove_action and item_type in ["project", "observations"]:
            remove_action.triggered.connect(self.remove_observations)

        menu.exec(project_explorer.viewport().mapToGlobal(position))

    @Slot()
    def add_observation(self):
        """Add a new observation to the project via ScheduleManipulator."""
        dialog = AddObservationDialog(self.manipulator, self)
        dialog.observation_added.connect(self.handle_observation_added)
        dialog.exec()

    @Slot(str, str)
    def handle_observation_added(self, obs_code: str, obs_type: str):
        """Handle observation added signal.

        Args:
            obs_code (str): The code of the added observation.
            obs_type (str): The type of the added observation.

        Raises:
            Exception: If the observation cannot be retrieved from the project.
        """
        
        try:
            self.manipulator.inspect(self.project, get_observation_by_code=obs_code)
            logger.debug(f"Observation '{obs_code}' found in project after addition")
        except Exception as e:
            logger.error(f"Observation '{obs_code}' not found in project after addition: {str(e)}")
        self.project_updated.emit()

    @Slot(str)
    def remove_observation(self, obs_name: str, obs_code: str):
        """Remove an observation from the project via ScheduleManipulator.

        Args:
            obs_name (str): The name of the observation to remove.
            obs_code (str): The code of the observation to remove.

        Raises:
            Exception: If the observation cannot be found or removed.
        """
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete observation '{obs_code}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            logger.info(f"Deletion of observation '{obs_code}' cancelled")
            return

        tab_container = self.ui.tabContainer
        for i in range(tab_container.count()):
            widget = tab_container.widget(i)
            if widget.objectName() == f"observationTab_{obs_code}":
                self._cleanup_widget(widget)
                tab_container.removeTab(i)
                logger.debug(f"Closed observation tab for code '{obs_code}'")
                break

        try:
            self.manipulator.inspect(self.project, get_item=obs_name)
            self.manipulator.configure(self.project, remove_item=obs_name)
            logger.info(f"Observation with code '{obs_code}' and name '{obs_name}' removed from project '{self.project.get_name()}'")
            self.project_updated.emit()
        except Exception as e:
            logger.error(f"Failed to remove observation '{obs_code}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to remove observation: {str(e)}")

    @Slot()
    def remove_observations(self):
        """Remove all observations from the project via ScheduleManipulator.

        Raises:
            Exception: If the observations cannot be removed.
        """
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete all observations?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            logger.info(f"Deletion of observations cancelled")
            return
        
        tab_container = self.ui.tabContainer
        for i in range(self.ui.tabContainer.count() - 1, -1, -1):
            widget = self.ui.tabContainer.widget(i)
            if widget.objectName() != "projectInfoTab":
                self.ui.tabContainer.removeTab(i)

        try:
            self.manipulator.configure(self.project, clear=None)
            logger.info(f"All observations were removed from project '{self.project.get_name()}'")
            self.project_updated.emit()
        except Exception as e:
            logger.error(f"Failed to remove observations: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to remove observations: {str(e)}")

    @Slot(str)
    def edit_observation(self, obs_name: str, obs_code: str):
        """Open the ObservationTab for the specified observation."""
        logger.debug(f"Opening edit tab for observation with code '{obs_code}'")
        self.open_observation_tab(obs_name, obs_code)

    def update_project_explorer(self):
        """Update Project Explorer tree using ScheduleInspector.

        Raises:
            Exception: If project name or observations cannot be retrieved.
        """
        project_explorer = self.ui.dockWidget.findChild(QTreeView, "projectExplorer")
        if not project_explorer:
            logger.error("Project explorer widget not found")
            return

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Project Explorer"])
        root = model.invisibleRootItem()

        try:
            project_name = self.manipulator.inspect(self.project, get_name=None)
        except Exception as e:
            logger.error(f"Failed to get project name: {str(e)}")
            project_name = "Untitled Project"
        logger.debug(f"Updating project explorer: project id={id(self.project)}, name={project_name}")

        project_item = QStandardItem(f"Project: {project_name}")
        project_item.setData("project", Qt.UserRole)
        root.appendRow(project_item)

        observations_item = QStandardItem("Observations")
        observations_item.setData("observations", Qt.UserRole)
        project_item.appendRow(observations_item)

        try:
            observations = self.manipulator.inspect(self.project, get_items=None)
            if isinstance(observations, dict):
                if observations:
                    for obs_name, obs in observations.items():
                        try:
                            obs_code = self.manipulator.inspect(obs, get_observation_code=None)
                            obs_item = QStandardItem(obs_code)
                            obs_item.setData("observation", Qt.UserRole)
                            obs_item.setData(obs_name, Qt.UserRole + 1)
                            observations_item.appendRow(obs_item)
                            logger.debug(f"Added observation '{obs_code}' to Project Explorer")
                        except Exception as e:
                            logger.error(f"Failed to get code for observation '{obs_name}': {str(e)}")
                else:
                    logger.debug("No observations found in project")
            else:
                logger.error(f"Expected dict for observations, got {type(observations)}: {observations}")
        except Exception as e:
            logger.error(f"Failed to inspect observations: {str(e)}")

        project_explorer.setModel(model)
        project_explorer.expandAll()
        project_explorer.viewport().update()
        logger.debug("Project explorer updated and expanded")

    def load_settings(self) -> dict:
        """Load application settings from settings.pastro file."""
        settings_file = "settings.pastro"
        default_settings = {
            "sources_catalog_path": os.path.join("catalogs", "sources.dat"),
            "telescopes_catalog_path": os.path.join("catalogs", "telescopes.dat"),
            "log_level": "INFO", 
            "time_step": 600,
            "clear_log_on_start": False
        }
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r") as f:
                    loaded_settings = json.load(f)
            
                default_settings.update(loaded_settings)
                logger.info(f"Settings loaded from '{settings_file}'")
                return default_settings
            except Exception as e:
                logger.error(f"Failed to load settings from '{settings_file}': {str(e)}")
                QMessageBox.warning(self, "Error", f"Failed to load settings: {str(e)}")
        logger.info("No settings file found, using default settings")
        return default_settings

    def save_settings(self, settings: dict):
        """Save application settings to settings.pastro file."""
        try:
            with open("settings.pastro", "w") as f:
                json.dump(settings, f, indent=4)
            logger.info("Settings saved to 'settings.pastro'")
        except Exception as e:
            logger.error(f"Failed to save settings to 'settings.pastro': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")

    @Slot()
    def new_project(self):
        """Create a new project, cleaning up the old one."""
        try:
            self._cleanup_project()
            self._initialize_project()
            self.current_project_path = None
            self.clear_connections(is_initial_setup=False)
            self.setup_connections()
            self.open_project_info_tab()
            self.update_project_explorer()
            self.project_updated.emit()
            logger.info("Created new project")
        except Exception as e:
            logger.error(f"Error creating new project: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to create new project: {str(e)}")

    @Slot()
    def open_project(self):
        """Open a project from a file, cleaning up the old one."""
        try:
            file_name, _ = QFileDialog.getOpenFileName(
                self, "Open Project", "", "pAstro Project Files (*.pastro)"
            )
            if not file_name:
                logger.debug("Open project cancelled")
                return
                                 
            new_project = ScheduleProject.from_file(file_name)

            self._cleanup_project()

            self.project = new_project
            self.manipulator = ScheduleManipulator(self.project)
            self.current_project_path = file_name
            
            self.clear_connections(is_initial_setup=False)
            self.setup_connections()
            
            self.open_project_info_tab()
            self.update_project_explorer()
            self.project_updated.emit()
            logger.info(f"Opened project from {file_name}")
            
        except Exception as e:
            logger.error(f"Error opening project: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to open project: {str(e)}")

    @Slot()
    def save_project(self):
        """Save the current project."""
        if self.current_project_path:
            progress = QProgressDialog("Saving project...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setAutoClose(True)
            progress.show()
            try:
                self.project.to_file(self.current_project_path)
                logger.info(f"Project saved to '{self.current_project_path}'")
            except Exception as e:
                logger.error(f"Failed to save project: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to save project: {str(e)}")
            finally:
                progress.close()
        else:
            self.save_project_as()

    @Slot()
    def save_project_as(self):
        """Save the current project to a new file."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Project As", "", "pAstroCORE Project (*.pastro)")
        if file_path:
            if not file_path.endswith(".pastro"):
                file_path += ".pastro"
            self.current_project_path = file_path
            self.save_project()

    @Slot()
    def import_new_observation(self):
        """Import a new observation into the project.

        Raises:
            Exception: If the observation cannot be imported or an error occurs during file loading.
        """
        file_path, _ = QFileDialog.getOpenFileName(self, "Import New Observation", "", "pAstroCORE Data (*.pastrod)")
        if not file_path:
            logger.info("Import new observation cancelled: No file selected")
            return

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            imported_observation = Observation.from_dict(data)
            if not hasattr(imported_observation, 'observation_type') or imported_observation.observation_type not in ["VLBI", "SINGLE_DISH"]:
                imported_observation.observation_type = "VLBI"

            self.manipulator.configure(self.project, add_item=imported_observation)
            logger.info(f"New observation '{imported_observation.code}' imported successfully")
            self.project_updated.emit()
        except Exception as e:
            logger.error(f"Failed to import observation '{imported_observation.code if 'imported_observation' in locals() else ''}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to import observation: {str(e)}")

    @Slot(str)
    def import_observation(self, obs_name: str, obs_code: str):
        """Import an observation to overwrite an existing one.

        Args:
            obs_name (str): The name of the observation to overwrite.
            obs_code (str): The code of the observation to overwrite.

        Raises:
            Exception: If the observation cannot be found, imported, or overwritten.
        """
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Observation", "", "pAstroCORE Data (*.pastrod)")
        if not file_path:
            logger.info(f"Import observation '{obs_code}' cancelled: No file selected")
            return

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            existing_observation = self.manipulator.inspect(self.project, get_item=obs_name)
            if existing_observation is None:
                logger.error(f"Observation '{obs_code}' not found")
                QMessageBox.critical(self, "Error", f"Observation '{obs_code}' not found")
                return

            existing_name = existing_observation.name
            existing_code = existing_observation.code

            imported_observation = Observation.from_dict(data)
            imported_observation.name = existing_name
            imported_observation.code = existing_code

            self.manipulator.configure(self.project, set_item={"name": existing_name, "item": imported_observation})
            logger.info(f"Observation '{obs_code}' overwritten successfully")
            self.project_updated.emit()
        except Exception as e:
            logger.error(f"Failed to import observation '{obs_code}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to import observation: {str(e)}")

    @Slot(str)
    def export_observation(self, obs_name: str, obs_code: str):
        """Export an observation by prompting for observation code.

        Args:
            obs_name (str): The name of the observation to export.
            obs_code (str): The code of the observation to export.

        Raises:
            Exception: If the observation cannot be found or exported.
        """
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Observation", "", "pAstroCORE Data (*.pastrod)")
        if not file_path:
            logger.info(f"Export observation '{obs_code}' cancelled: No file selected")
            return
        if not file_path.endswith(".pastrod"):
            file_path += ".pastrod"

        try:
            observation = self.manipulator.inspect(self.project, get_item=obs_name)
            if observation is None:
                logger.error(f"Observation '{obs_code}' not found")
                QMessageBox.critical(self, "Error", f"Observation '{obs_code}' not found")
                return

            with open(file_path, "w") as f:
                json.dump(observation.to_dict(), f, indent=4)
            logger.info(f"Observation '{obs_code}' exported to '{file_path}'")
        except Exception as e:
            logger.error(f"Failed to export observation '{obs_code}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to export observation: {str(e)}")

    @Slot()
    def open_preferences(self):
        """Open the preferences dialog to configure settings."""
        dialog = PreferencesDialog(self.settings, self)
        dialog.settings_updated.connect(self.handle_settings_updated)
        dialog.exec()

    @Slot(dict, list)
    def handle_settings_updated(self, settings: dict, changed_keys: list):
        """Handle settings updated signal from PreferencesDialog.

        Args:
            settings (dict): Updated application settings.
            changed_keys (list): List of keys that have changed in the settings.
        """
        self.settings = settings
        self.save_settings(self.settings)

        if "log_level" in changed_keys:
            new_log_level_str = self.settings.get("log_level", "INFO")
            new_log_level = getattr(logging, new_log_level_str, logging.INFO)
            update_logging_level(new_log_level)
            logger.info(f"Logger level updated to {new_log_level_str}")

        if "clear_log_on_start" in changed_keys:
            clear_log = self.settings.get("clear_log_on_start", False)
            update_logging_clear("output.log", clear_log)
            logger.info(f"Log file clearing setting updated to {clear_log}. This will take effect now and on the next application start.")

        if "sources_catalog_path" in changed_keys:
            sources_path = self.settings.get("sources_catalog_path", os.path.join("catalogs", "sources.dat"))
            try:
                self.catalog_manager.source_catalog.clear()
                if sources_path:
                    self.catalog_manager.load_source_catalog(sources_path)
                sources_count = len(self.catalog_manager.source_catalog.get_items())
                logger.info(f"Sources catalog reloaded with {sources_count} sources from {sources_path}")
            except Exception as e:
                logger.error(f"Failed to reload sources catalog from '{sources_path}': {str(e)}")
                QMessageBox.warning(self, "Warning", f"Failed to reload sources catalog: {str(e)}")

        if "telescopes_catalog_path" in changed_keys:
            telescopes_path = self.settings.get("telescopes_catalog_path", os.path.join("catalogs", "telescopes.dat"))
            try:
                self.catalog_manager.telescope_catalog.clear()
                if telescopes_path:
                    self.catalog_manager.load_telescope_catalog(telescopes_path)
                telescopes_count = len(self.catalog_manager.telescope_catalog.get_items())
                logger.info(f"Telescopes catalog reloaded with {telescopes_count} telescopes from {telescopes_path}")
            except Exception as e:
                logger.error(f"Failed to reload telescopes catalog from '{telescopes_path}': {str(e)}")
                QMessageBox.warning(self, "Warning", f"Failed to reload telescopes catalog: {str(e)}")

        if changed_keys:
            logger.debug(f"Settings updated: {', '.join(changed_keys)}")
        else:
            logger.debug("No settings changes detected")

    @Slot()
    def open_telescope_catalog_manager(self):
        """Open the telescopes catalog browser dialog."""
        telescopes_path = self.settings.get("telescopes_catalog_path", os.path.join("catalogs", "telescopes.dat"))
        if not os.path.isfile(telescopes_path):
            logger.error(f"Telescopes catalog file not found: {telescopes_path}")
            QMessageBox.warning(self, "Warning", "Please set a valid telescopes catalog path in Preferences.")
            return

        telescopes = self.catalog_manager.telescope_catalog.get_items()
        if not telescopes:
            logger.warning("Telescopes catalog is empty")
            QMessageBox.warning(self, "Warning", "Telescopes catalog is empty. Check the catalog file or reload in Preferences.")
            return

        dialog = TelescopesCatalogDialog(self.catalog_manager, self)
        dialog.exec()
        logger.debug("Telescopes catalog browser dialog opened")

    @Slot()
    def open_source_catalog_manager(self):
        """Open the sources catalog browser dialog."""
        sources_path = self.settings.get("sources_catalog_path", os.path.join("catalogs", "sources.dat"))
        if not os.path.isfile(sources_path):
            logger.error(f"Sources catalog file not found: {sources_path}")
            QMessageBox.warning(self, "Warning", "Please set a valid sources catalog path in Preferences.")
            return

        sources = self.catalog_manager.source_catalog.get_items()
        if not sources:
            logger.warning("Sources catalog is empty")
            QMessageBox.warning(self, "Warning", "Sources catalog is empty. Check the catalog file or reload in Preferences.")
            return

        dialog = SourcesCatalogDialog(self.catalog_manager, self)
        dialog.exec()
        logger.debug("Sources catalog browser dialog opened")

    @Slot()
    def show_about(self):
        """Show about dialog."""
        dialog = AboutDialog(self)
        dialog.exec()

    @Slot()
    def handle_project_explorer_click(self, index):
        """Handle clicks on Project Explorer.

        Args:
            index: The index of the clicked item in the Project Explorer.

        Raises:
            Exception: If the observation cannot be retrieved by code.
        """
        item = self.ui.projectExplorer.model().itemFromIndex(index)
        if not item:
            return
        item_type = item.data(Qt.UserRole)
        text = item.text()
        if item_type == "project":
            self.open_project_info_tab()
        elif item_type == "observation":
            obs_code = text
            try:
                observation = self.manipulator.inspect(self.project, get_observation_by_code=obs_code)
                if observation is None:
                    logger.error(f"Observation with code '{obs_code}' not found")
                    QMessageBox.critical(self, "Error", f"Failed to open observation '{obs_code}': Observation not found")
                    return
                obs_name = observation.name
                self.open_observation_tab(obs_name, obs_code)
            except Exception as e:
                logger.error(f"Failed to get observation with code '{obs_code}': {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to open observation '{obs_code}': {str(e)}")

    def open_project_info_tab(self):
        """Open or switch to ProjectInfoTab."""
        tab_container = self.ui.tabContainer
        for i in range(tab_container.count()):
            if tab_container.widget(i).objectName() == "projectInfoTab":
                tab_container.setCurrentIndex(i)
                widget = tab_container.widget(i)
                widget.update_tab()
                tab_container.tabBar().setTabButton(i, QTabBar.ButtonPosition.RightSide, None)
                logger.debug("Reusing existing project info tab")
                return
        project_tab = ProjectInfoTab(self.manipulator, self)
        project_tab.setObjectName("projectInfoTab")
        tab_container.addTab(project_tab, "Project")
        tab_container.setCurrentWidget(project_tab)
        project_tab.update_tab()
        tab_container.tabBar().setTabButton(tab_container.indexOf(project_tab), QTabBar.ButtonPosition.RightSide, None)
        project_tab.project_name_changed.connect(self.handle_projectInfoTab_project_name_changed)
        self.project_updated.connect(project_tab.update_tab)
        logger.debug("Created new project info tab")

    @Slot(str)
    def handle_projectInfoTab_project_name_changed(self, name: str):
        """Handle project name change signal."""
        self.project_updated.emit()

    def open_observation_tab(self, obs_name: str, obs_code: str):
        """Open or switch to a tab for editing an observation.

        Args:
            obs_name (str): The name of the observation to open.
            obs_code (str): The code of the observation to open.

        Raises:
            Exception: If the observation cannot be retrieved.
        """
        tab_container = self.ui.tabContainer
        for i in range(tab_container.count()):
            widget = tab_container.widget(i)
            if widget.objectName() == f"observationTab_{obs_code}":
                tab_container.setCurrentIndex(i)
                widget.setFocus()
                widget.update_tab()
                return

        try:
            observation = self.manipulator.inspect(self.project, get_item=obs_name)
            if observation is None:
                logger.error(f"Observation '{obs_code}' not found")
                QMessageBox.critical(self, "Error", f"Failed to open observation tab: Observation not found")
                return
            observation_tab = ObservationTab(observation, self.manipulator, self.catalog_manager, self)
            observation_tab.setObjectName(f"observationTab_{obs_code}")
            tab_container.addTab(observation_tab, f"Observation: {obs_code}")
            tab_container.setCurrentWidget(observation_tab)
            observation_tab.setFocus()
            observation_tab.observation_updated.connect(self.handle_observationTab_observation_updated)
            self.project_updated.connect(observation_tab.update_tab)
            logger.debug(f"Opened observation tab for code '{obs_code}'")
        except Exception as e:
            logger.error(f"Failed to open observation tab for code '{obs_code}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to open observation tab: {str(e)}")

    @Slot()
    def handle_observationTab_observation_updated(self):
        """Handle observation update signal."""
        logger.debug("Observation updated")
        self.project_updated.emit()

    @Slot()
    def update_all_tabs(self):
        """Update all open tabs when project data changes."""
        for i in range(self.ui.tabContainer.count()):
            widget = self.ui.tabContainer.widget(i)
            if hasattr(widget, 'update_tab'):
                widget.update_tab()
        logger.debug("All tabs updated")
    
    @Slot(bool)
    def sync_project_explorer_action(self, visible: bool):
        """Synchronize the Project Explorer menu action with dockWidget visibility."""
        if self._sync_in_progress:
            return
            
        self._sync_in_progress = True
        try:
            if self.windowState() & QtCore.Qt.WindowMinimized:
                logger.debug("Skipping sync during minimization")
                return
                
            if self.ui.actionProject_Explorer.isChecked() != visible:
                logger.debug(f"Syncing action state to: {visible}")
                self.ui.actionProject_Explorer.setChecked(visible)
                
            self._dock_was_visible = visible
        finally:
            self._sync_in_progress = False
    
    def changeEvent(self, event):
        """Handle window state changes, such as minimization and restoration."""
        if event.type() == QtCore.QEvent.WindowStateChange:
            new_state = self.windowState()
            
            if new_state == QtCore.Qt.WindowNoState:
                if self.ui.dockWidget.isVisible() != self._dock_was_visible:
                    self.ui.dockWidget.setVisible(self._dock_was_visible)
                    self.sync_project_explorer_action(self._dock_was_visible)
        
        super().changeEvent(event)
    
    @Slot()
    def handle_generate_observations(self):
        """Handle the Generate Observations action from the Tools menu."""
        try:
            dialog = GenerateObservationsDialog(self.project, self.manipulator, self.catalog_manager, self)
            dialog.observation_generated.connect(self.handle_observation_generated)
            if dialog.exec() == QDialog.Accepted:
                logger.debug("Generate Observations dialog accepted")
            else:
                logger.debug("Generate Observations dialog rejected")
        except Exception as e:
            logger.error(f"Error opening Generate Observations dialog: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to open Generate Observations dialog: {str(e)}")

    @Slot(list)
    def handle_observation_generated(self, obs_codes: list):
        """Handle observation generated signal."""
        try:
            self.update_project_explorer()
            self.project_updated.emit()
        except Exception as e:
            logger.error(f"Error handling generated observations: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to handle generated observations: {str(e)}")

    def _cleanup_tabs(self):
        """Clean up all tabs in tabContainer."""
        tab_container = self.ui.tabContainer
        for i in range(tab_container.count() - 1, -1, -1):
            widget = tab_container.widget(i)
            if widget:
                try:
                    widget.blockSignals(True)
                                        
                    if hasattr(widget, '_cleanup'):
                        widget._cleanup()
                
                    for child in widget.children():
                        if isinstance(child, QtCore.QObject):
                            child.deleteLater()
                    tab_container.removeTab(i)
                    widget.deleteLater()
                    
                    logger.debug(f"Cleaned and removed tab {widget.objectName()}")
                except Exception as e:
                    logger.error(f"Error cleaning tab {widget.objectName()}: {str(e)}")
        logger.debug("All tabs cleaned up")

    def _cleanup_project(self):
        """Clean up the current project and its dependencies."""
        try:
            self._cleanup_tabs()
            
            try:
                self.project_updated.disconnect()
            except Exception:
                pass
            
            if self.manipulator:
                self.manipulator.clear_cache()
                self.manipulator.clear_base_classes()
                
                if hasattr(self.manipulator, '_project'):
                    self.manipulator._project = None
                self.manipulator = None
            
            if self.project:
                self.project.clear()
                
                for obs in self.project.get_items().values():
                    if hasattr(obs, 'cleanup'):
                        obs.cleanup()
                    for attr in ['_project', '_manipulator', '_parent']:
                        if hasattr(obs, attr):
                            setattr(obs, attr, None)
                
                self.project = None
            
        except Exception as e:
            logger.error(f"Error cleaning up project: {str(e)}")

    def _initialize_project(self):
        """Initialize a new project and its dependencies."""
        self.project = ScheduleProject(name="Untitled Project")
        self.manipulator = ScheduleManipulator(self.project)
        logger.debug(f"Initialized new project with id: {id(self.project)}, manipulator id={id(self.manipulator)}")
    
    def closeEvent(self, event):
        self.clear_connections()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f5f5;
            font-family: Arial, sans-serif;
        }
        QMenuBar {
            background-color: #ffffff;
            color: #333333;
            padding: 4px;
        }
        QMenuBar::item {
            background: #ffffff;
            padding: 4px 8px;
            color: #333333;
        }
        QMenuBar::item:selected {
            background: #0078d7;
            color: #ffffff;
        }
        QMenu {
            background-color: #ffffff;
            border: 1px solid #d3d3d3;
            color: #333333;
        }
        QMenu::item {
            padding: 4px 24px 4px 8px;
            background: #ffffff;
            color: #333333;
        }
        QMenu::item:selected {
            background: #0078d7;
            color: #ffffff;
        }
        QTableView {
            background-color: #ffffff;
            border: 1px solid #d3d3d3;
            gridline-color: #e0e0e0;
            selection-background-color: #0078d7;
            selection-color: #ffffff;
            font-size: 12px;
        }
        QTableView::item {
            padding: 4px;
        }
        QHeaderView::section {
            background-color: #f0f0f0;
            padding: 4px;
            border: 1px solid #d3d3d3;
        }
        QLineEdit {
            background-color: #ffffff;
            border: 1px solid #d3d3d3;
            padding: 4px;
            border-radius: 4px;
            color: #333333;
        }
        QLineEdit:focus {
            border: 1px solid #0078d7;
        }
        QLineEdit[readOnly="true"] {
            background-color: #f0f0f0;
            border: 1px solid #e0e0e0;
        }
        QWidget {
            color: #333333;
        }
        /* Vertical ScrollBar */
        QScrollBar:vertical {
            background-color: #f0f0f0;
            width: 12px;
            margin: 0px 0px 0px 0px;
            border: 1px solid #d3d3d3;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background-color: #ffffff;
            min-height: 20px;
            border: 1px solid #d3d3d3;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #0078d7;
            border: 1px solid #0078d7;
        }
        QScrollBar::add-line:vertical {
            background-color: #f0f0f0;
            height: 0px;
            subcontrol-position: bottom;
            subcontrol-origin: margin;
        }
        QScrollBar::sub-line:vertical {
            background-color: #f0f0f0;
            height: 0px;
            subcontrol-position: top;
            subcontrol-origin: margin;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background-color: #f5f5f5;
        }
        /* Horizontal ScrollBar */
        QScrollBar:horizontal {
            background-color: #f0f0f0;
            height: 12px;
            margin: 0px 0px 0px 0px;
            border: 1px solid #d3d3d3;
            border-radius: 4px;
        }
        QScrollBar::handle:horizontal {
            background-color: #ffffff;
            min-width: 20px;
            border: 1px solid #d3d3d3;
            border-radius: 4px;
        }
        QScrollBar::handle:horizontal:hover {
            background-color: #0078d7;
            border: 1px solid #0078d7;
        }
        QScrollBar::add-line:horizontal {
            background-color: #f0f0f0;
            width: 0px;
            subcontrol-position: right;
            subcontrol-origin: margin;
        }
        QScrollBar::sub-line:horizontal {
            background-color: #f0f0f0;
            width: 0px;
            subcontrol-position: left;
            subcontrol-origin: margin;
        }
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background-color: #f5f5f5;
        }
    """)
    window = PAstroCoreMainWindow()
    window.show()
    sys.exit(app.exec())
