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
from msb_arch.utils import (logger, 
                            setup_logging, 
                            update_logging_level, 
                            update_logging_clear
                            )
import logging
import sys
import threading
import os
from pathlib import Path
import json
# GUI resource file
import pastrocore.gui.rc_icons

def _portable(path: str) -> str:
    r"""Return a path that resolves on the platform it is read on.

    Args:
        path (str): A path as stored in the settings file.

    Returns:
        str: The same path with separators the running platform understands.

    Notes:
        - Settings are saved with the separator of whichever platform wrote them, and the file
          the repository ships was written on Windows. On Linux `catalogs\sources.dat` is not
          a directory and a file: it is one filename containing a backslash, so the catalogs
          silently failed to load.
    """
    return os.path.normpath(path.replace("\\", "/")) if path else path


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
    
        # Logging is configured at the entry point, before anything can emit a record;
        # here the level is only re-applied in case the settings differ from the defaults.
        log_level_str = self.settings.get("log_level", "INFO")
        update_logging_level(getattr(logging, log_level_str, logging.INFO))
        logger.debug("Logging re-applied at window start with level=%s", log_level_str)
    
        self.project = ScheduleProject(name="Untitled Project")
        self.manipulator = ScheduleManipulator(self.project)
        self._apply_residency_budget()
        self.catalog_manager = self.initialize_catalog_manager()
    
        logger.debug("pAstroCORE initialized with project id: %s, manipulator id=%s, catalog_manager id=%s", id(self.project), id(self.manipulator), id(self.catalog_manager))
    
        self.current_project_path = None
        self._action_connections = {}
        self.setup_ui()
        self.setup_connections()

    def _apply_residency_budget(self):
        """Tell the current project how much memory its results may occupy.

        Notes:
            - Called whenever the project changes, not only when the setting does, because a
              newly opened project starts with the default and would otherwise ignore what the
              user chose until they opened the preferences again.
        """
        if self.project is None:
            return
        try:
            self.project.set_residency_share(float(self.settings.get("results_memory_share", 0.5)))
        except (TypeError, ValueError) as e:
            logger.error("Ignoring invalid results memory share in settings: %s", str(e))

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
                logger.debug("Disconnected signal for action %s", action.objectName())
            except TypeError as e:
                logger.debug("No signal to disconnect for action %s: %s", action.objectName(), str(e))
        self._action_connections.clear()

        try:
            if self.receivers(QtCore.SIGNAL("project_updated()")) > 0:
                self.project_updated.disconnect()
                logger.debug("Disconnected project_updated signal")
            else:
                logger.debug("No active connections for project_updated signal")
        except TypeError as e:
            logger.debug("Error checking project_updated signal: %s", str(e))

        project_explorer = self.ui.dockWidget.findChild(QTreeView, "projectExplorer")
        if project_explorer:
            try:
                if project_explorer.receivers(QtCore.SIGNAL("clicked(QModelIndex)")) > 0:
                    project_explorer.clicked.disconnect(self.handle_project_explorer_click)
                    logger.debug("Disconnected project explorer clicked signal")
                else:
                    logger.debug("No active connections for project explorer clicked signal")
            except TypeError as e:
                logger.debug("Error checking project explorer clicked signal: %s", str(e))
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
                logger.debug("Error checking tabCloseRequested signal: %s", str(e))

        try:
            if self.ui.actionProject_Explorer.receivers(QtCore.SIGNAL("toggled(bool)")) > 0:
                self.ui.actionProject_Explorer.toggled.disconnect()
                logger.debug("Disconnected actionProject_Explorer.toggled signal")
            else:
                logger.debug("No active connections for actionProject_Explorer toggled signal")
        except TypeError as e:
            logger.debug("Error checking actionProject_Explorer toggled signal: %s", str(e))

        try:
            if self.ui.dockWidget.receivers(QtCore.SIGNAL("visibilityChanged(bool)")) > 0:
                self.ui.dockWidget.visibilityChanged.disconnect()
                logger.debug("Disconnected dockWidget.visibilityChanged signal")
            else:
                logger.debug("No active connections for dockWidget visibilityChanged signal")
        except TypeError as e:
            logger.debug("Error checking dockWidget visibilityChanged signal: %s", str(e))     
    
    def initialize_catalog_manager(self):
        """Initialize CatalogManager with paths from settings or defaults."""
        default_sources_path = os.path.join("catalogs", "sources.dat")
        default_telescopes_path = os.path.join("catalogs", "telescopes.dat")
        sources_path = _portable(self.settings.get("sources_catalog_path", default_sources_path))
        telescopes_path = _portable(self.settings.get("telescopes_catalog_path", default_telescopes_path))

        try:
            if not os.path.isfile(sources_path):
                logger.warning("Sources catalog file not found: %s. Initializing empty source catalog.", sources_path)
            if not os.path.isfile(telescopes_path):
                logger.warning("Telescopes catalog file not found: %s. Initializing empty telescope catalog.", telescopes_path)
                
            catalog_manager = CatalogManager(source_file=sources_path, telescope_file=telescopes_path)
            sources_count = len(catalog_manager.source_catalog.get_items())
            telescopes_count = len(catalog_manager.telescope_catalog.get_items())
            logger.info("Catalog initialized with %s sources and %s telescopes", sources_count, telescopes_count)
            return catalog_manager
        except Exception as e:
            # Logged, not shown. A modal dialog inside a constructor waits for a click that
            # nobody is there to give: on a build machine this hung for ten minutes, and to a
            # user with a bad catalog path it would look like an application that will not
            # start. Degrading to empty catalogs is what the next line already did anyway.
            logger.error("Failed to initialize CatalogManager with sources='%s', telescopes='%s': %s",
                         sources_path, telescopes_path, str(e), exc_info=True)
            self._catalog_error = str(e)
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
            logger.error("Error opening Export Calculated Data dialog: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to open Export Calculated Data dialog: {str(e)}")

    @Slot()
    def open_calculation_dialog(self):
        """Open the calculation dialog with time_step from settings."""
        try:
            dialog = CalculationDialog(self.manipulator, time_step=self.settings.get("time_step", 600), parent=self)
            dialog.time_step_updated.connect(self.handle_time_step_updated)
            dialog.exec()
        except Exception as e:
            logger.error("Failed to open calculation dialog: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to open calculation dialog: {str(e)}")
    
    @Slot()
    def open_visualization_dialog(self):
        """Open the visualization dialog for the current project."""
        try:
            dialog = VisualizationDialog(self.manipulator, parent=self)
            dialog.exec()
        except Exception as e:
            logger.error("Failed to open visualization dialog: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to open visualization dialog: {str(e)}")

    def handle_tab_close(self, index):
        """Handle closing of tabs, prevent closing of project tab, and clean up resources."""
        widget = self.ui.tabContainer.widget(index)
        if widget and widget.objectName() == "projectInfoTab":
            return
        self._cleanup_widget(widget)
        self.ui.tabContainer.removeTab(index)
        logger.debug("Closed tab at index %s and cleaned up resources", index)
    
    def _cleanup_widget(self, widget: QWidget):
        """Clean up widget resources and disconnect signals."""
        try:
            widget.blockSignals(True)
            if hasattr(widget, 'observation_updated'):
                try:
                    widget.observation_updated.disconnect()
                    logger.debug("Disconnected observation_updated signal for %s", widget.objectName())
                except Exception as e:
                    logger.debug("No observation_updated signal to disconnect: %s", str(e))
            if hasattr(widget, 'project_name_changed'):
                try:
                    widget.project_name_changed.disconnect()
                    logger.debug("Disconnected project_name_changed signal for %s", widget.objectName())
                except Exception as e:
                    logger.debug("No project_name_changed signal to disconnect: %s", str(e))

            for child in widget.findChildren(QObject):
                child.blockSignals(True)
                child.deleteLater()
            widget.deleteLater()
            logger.debug("Scheduled deletion of widget %s", widget.objectName())
        except Exception as e:
            logger.error("Error cleaning up widget %s: %s", widget.objectName(), str(e))

    @Slot(dict)
    def handle_time_step_updated(self, time_step: int):
        """Handle time_step updated signal from CalculationDialog."""
        self.settings["time_step"] = time_step
        self.save_settings(self.settings)
        logger.debug("time_step updated to %s and saved to settings", time_step)

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
            logger.debug("Observation '%s' found in project after addition", obs_code)
        except Exception as e:
            logger.error("Observation '%s' not found in project after addition: %s", obs_code, str(e))
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
            logger.info("Deletion of observation '%s' cancelled", obs_code)
            return

        tab_container = self.ui.tabContainer
        for i in range(tab_container.count()):
            widget = tab_container.widget(i)
            if widget.objectName() == f"observationTab_{obs_code}":
                self._cleanup_widget(widget)
                tab_container.removeTab(i)
                logger.debug("Closed observation tab for code '%s'", obs_code)
                break

        try:
            self.manipulator.inspect(self.project, get_item=obs_name)
            self.manipulator.configure(self.project, remove_item=obs_name)
            logger.info("Observation with code '%s' and name '%s' removed from project '%s'", obs_code, obs_name, self.project.get_name())
            self.project_updated.emit()
        except Exception as e:
            logger.error("Failed to remove observation '%s': %s", obs_code, str(e))
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
            logger.info("Deletion of observations cancelled")
            return
        
        for i in range(self.ui.tabContainer.count() - 1, -1, -1):
            widget = self.ui.tabContainer.widget(i)
            if widget.objectName() != "projectInfoTab":
                self.ui.tabContainer.removeTab(i)

        try:
            self.manipulator.configure(self.project, clear=None)
            logger.info("All observations were removed from project '%s'", self.project.get_name())
            self.project_updated.emit()
        except Exception as e:
            logger.error("Failed to remove observations: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to remove observations: {str(e)}")

    @Slot(str)
    def edit_observation(self, obs_name: str, obs_code: str):
        """Open the ObservationTab for the specified observation."""
        logger.debug("Opening edit tab for observation with code '%s'", obs_code)
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
            logger.error("Failed to get project name: %s", str(e))
            project_name = "Untitled Project"
        logger.debug("Updating project explorer: project id=%s, name=%s", id(self.project), project_name)

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
                            logger.debug("Added observation '%s' to Project Explorer", obs_code)
                        except Exception as e:
                            logger.error("Failed to get code for observation '%s': %s", obs_name, str(e))
                else:
                    logger.debug("No observations found in project")
            else:
                logger.error("Expected dict for observations, got %s: %s", type(observations), observations)
        except Exception as e:
            logger.error("Failed to inspect observations: %s", str(e))

        project_explorer.setModel(model)
        project_explorer.expandAll()
        project_explorer.viewport().update()
        logger.debug("Project explorer updated and expanded")

    @staticmethod
    def load_settings() -> dict:
        """Load application settings from settings.pastro file.

        Notes:
            - Static so that the entry point can read the settings before the window
              exists, which is where logging is configured.
        """
        settings_file = "settings.pastro"
        default_settings = {
            "sources_catalog_path": os.path.join("catalogs", "sources.dat"),
            "telescopes_catalog_path": os.path.join("catalogs", "telescopes.dat"),
            "log_level": "INFO", 
            "time_step": 600,
            "clear_log_on_start": False,
            # What share of available memory the calculated results in hand may occupy before
            # the least recently used are dropped. They can always be read back from the
            # project directory, so this costs a read rather than a recalculation.
            "results_memory_share": 0.5
        }
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r") as f:
                    loaded_settings = json.load(f)
            
                default_settings.update(loaded_settings)
                logger.info("Settings loaded from '%s'", settings_file)
                return default_settings
            except Exception as e:
                logger.error("Failed to load settings from '%s': %s", settings_file, str(e))
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
            logger.error("Failed to save settings to 'settings.pastro': %s", str(e))
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
            logger.error("Error creating new project: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to create new project: {str(e)}")

    @Slot()
    def open_project(self):
        """Open a project from a file, cleaning up the old one."""
        try:
            file_name, _ = QFileDialog.getOpenFileName(
                self, "Open Project", "", "pAstro Project (*.pastro project.json)"
            )
            if not file_name:
                logger.debug("Open project cancelled")
                return
                                 
            # One entry point: a directory, the project.json inside one, or a single
            # file written by an earlier version. The model decides which it is.
            new_project = ScheduleProject.open(file_name)

            self._cleanup_project()

            self.project = new_project
            self.manipulator = ScheduleManipulator(self.project)
            self._apply_residency_budget()
            # What gets remembered is the project, not the file inside it. A user who
            # navigated in and picked project.json would otherwise have that path saved
            # over on the next save -- turning the model file itself into a directory.
            self.current_project_path = str(Path(file_name).parent) if Path(
                file_name).name == ScheduleProject.MODEL_FILE else file_name
            
            self.clear_connections(is_initial_setup=False)
            self.setup_connections()
            
            self.open_project_info_tab()
            self.update_project_explorer()
            self.project_updated.emit()
            logger.info("Opened project from %s", file_name)
            
        except Exception as e:
            logger.error("Error opening project: %s", str(e))
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
                # Saves a directory: the model in one small file and each result in
                # its own parquet beside it. A single file at this path is converted,
                # and only after the directory is complete.
                self.project.save(self.current_project_path)
                logger.info("Project saved to '%s'", self.current_project_path)
            except Exception as e:
                logger.error("Failed to save project: %s", str(e))
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
            logger.info("New observation '%s' imported successfully", imported_observation.code)
            self.project_updated.emit()
        except Exception as e:
            logger.error("Failed to import observation '%s': %s", imported_observation.code if 'imported_observation' in locals() else '', str(e))
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
            logger.info("Import observation '%s' cancelled: No file selected", obs_code)
            return

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            existing_observation = self.manipulator.inspect(self.project, get_item=obs_name)
            if existing_observation is None:
                logger.error("Observation '%s' not found", obs_code)
                QMessageBox.critical(self, "Error", f"Observation '{obs_code}' not found")
                return

            existing_name = existing_observation.name
            existing_code = existing_observation.code

            imported_observation = Observation.from_dict(data)
            imported_observation.name = existing_name
            imported_observation.code = existing_code

            self.manipulator.configure(self.project, set_item={"name": existing_name, "item": imported_observation})
            logger.info("Observation '%s' overwritten successfully", obs_code)
            self.project_updated.emit()
        except Exception as e:
            logger.error("Failed to import observation '%s': %s", obs_code, str(e))
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
            logger.info("Export observation '%s' cancelled: No file selected", obs_code)
            return
        if not file_path.endswith(".pastrod"):
            file_path += ".pastrod"

        try:
            observation = self.manipulator.inspect(self.project, get_item=obs_name)
            if observation is None:
                logger.error("Observation '%s' not found", obs_code)
                QMessageBox.critical(self, "Error", f"Observation '{obs_code}' not found")
                return

            with open(file_path, "w") as f:
                json.dump(observation.to_dict(), f, indent=4)
            logger.info("Observation '%s' exported to '%s'", obs_code, file_path)
        except Exception as e:
            logger.error("Failed to export observation '%s': %s", obs_code, str(e))
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
            logger.info("Logger level updated to %s", new_log_level_str)

        if "results_memory_share" in changed_keys:
            self._apply_residency_budget()

        if "clear_log_on_start" in changed_keys:
            clear_log = self.settings.get("clear_log_on_start", False)
            update_logging_clear("output.log", clear_log)
            logger.info("Log file clearing setting updated to %s. This will take effect now and on the next application start.", clear_log)

        if "sources_catalog_path" in changed_keys:
            sources_path = self.settings.get("sources_catalog_path", os.path.join("catalogs", "sources.dat"))
            try:
                self.catalog_manager.source_catalog.clear()
                if sources_path:
                    self.catalog_manager.load_source_catalog(sources_path)
                sources_count = len(self.catalog_manager.source_catalog.get_items())
                logger.info("Sources catalog reloaded with %s sources from %s", sources_count, sources_path)
            except Exception as e:
                logger.error("Failed to reload sources catalog from '%s': %s", sources_path, str(e))
                QMessageBox.warning(self, "Warning", f"Failed to reload sources catalog: {str(e)}")

        if "telescopes_catalog_path" in changed_keys:
            telescopes_path = self.settings.get("telescopes_catalog_path", os.path.join("catalogs", "telescopes.dat"))
            try:
                self.catalog_manager.telescope_catalog.clear()
                if telescopes_path:
                    self.catalog_manager.load_telescope_catalog(telescopes_path)
                telescopes_count = len(self.catalog_manager.telescope_catalog.get_items())
                logger.info("Telescopes catalog reloaded with %s telescopes from %s", telescopes_count, telescopes_path)
            except Exception as e:
                logger.error("Failed to reload telescopes catalog from '%s': %s", telescopes_path, str(e))
                QMessageBox.warning(self, "Warning", f"Failed to reload telescopes catalog: {str(e)}")

        if changed_keys:
            logger.debug("Settings updated: %s", ', '.join(changed_keys))
        else:
            logger.debug("No settings changes detected")

    @Slot()
    def open_telescope_catalog_manager(self):
        """Open the telescopes catalog browser dialog."""
        telescopes_path = self.settings.get("telescopes_catalog_path", os.path.join("catalogs", "telescopes.dat"))
        if not os.path.isfile(telescopes_path):
            logger.error("Telescopes catalog file not found: %s", telescopes_path)
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
            logger.error("Sources catalog file not found: %s", sources_path)
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
                    logger.error("Observation with code '%s' not found", obs_code)
                    QMessageBox.critical(self, "Error", f"Failed to open observation '{obs_code}': Observation not found")
                    return
                obs_name = observation.name
                self.open_observation_tab(obs_name, obs_code)
            except Exception as e:
                logger.error("Failed to get observation with code '%s': %s", obs_code, str(e))
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
                logger.error("Observation '%s' not found", obs_code)
                QMessageBox.critical(self, "Error", f"Failed to open observation tab: Observation not found")
                return
            observation_tab = ObservationTab(observation, self.manipulator, self.catalog_manager, self)
            observation_tab.setObjectName(f"observationTab_{obs_code}")
            tab_container.addTab(observation_tab, f"Observation: {obs_code}")
            tab_container.setCurrentWidget(observation_tab)
            observation_tab.setFocus()
            observation_tab.observation_updated.connect(self.handle_observationTab_observation_updated)
            self.project_updated.connect(observation_tab.update_tab)
            logger.debug("Opened observation tab for code '%s'", obs_code)
        except Exception as e:
            logger.error("Failed to open observation tab for code '%s': %s", obs_code, str(e))
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
                logger.debug("Syncing action state to: %s", visible)
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
            logger.error("Error opening Generate Observations dialog: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to open Generate Observations dialog: {str(e)}")

    @Slot(list)
    def handle_observation_generated(self, obs_codes: list):
        """Handle observation generated signal."""
        try:
            self.update_project_explorer()
            self.project_updated.emit()
        except Exception as e:
            logger.error("Error handling generated observations: %s", str(e))
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
                    
                    logger.debug("Cleaned and removed tab %s", widget.objectName())
                except Exception as e:
                    logger.error("Error cleaning tab %s: %s", widget.objectName(), str(e))
        logger.debug("All tabs cleaned up")

    def _cleanup_project(self):
        """Clean up the current project and its dependencies."""
        try:
            self._cleanup_tabs()
            
            try:
                self.project_updated.disconnect()
            except RuntimeError:
                # Qt raises when a signal has no connections, and offers no way to ask
                # beforehand, so this is the only way to disconnect idempotently.
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
            logger.error("Error cleaning up project: %s", str(e))

    def _initialize_project(self):
        """Initialize a new project and its dependencies."""
        self.project = ScheduleProject(name="Untitled Project")
        self.manipulator = ScheduleManipulator(self.project)
        self._apply_residency_budget()
        logger.debug("Initialized new project with id: %s, manipulator id=%s", id(self.project), id(self.manipulator))
    
    def closeEvent(self, event):
        self.clear_connections()
        super().closeEvent(event)

def _warm_coordinate_tables() -> None:
    """Do one throwaway coordinate transform, so the user's first calculation is not the one
    that pays for loading astropy's reference tables.

    Notes:
        - Measured: the first `transform_to` in a process costs about 760 ms and every one
          after it about 3, because the first pulls in the IERS and leap-second tables. That
          made the first calculation 1 077 ms against 290 for the rest, and the difference was
          entirely this.
        - Runs on a daemon thread so the window still appears immediately, and swallows
          everything: a warm-up that fails must never stop the application starting.
    """
    def warm():
        try:
            from astropy.coordinates import AltAz, EarthLocation, SkyCoord
            from astropy.time import Time
            import astropy.units as u

            location = EarthLocation.from_geocentric(4033947.0, 486990.0, 4900431.0, unit=u.m)
            SkyCoord(ra=0.0 * u.deg, dec=0.0 * u.deg, frame="icrs").transform_to(
                AltAz(obstime=Time("2026-01-01T00:00:00"), location=location))
            logger.debug("Coordinate tables warmed")
        except Exception:
            logger.debug("Could not warm the coordinate tables", exc_info=True)

    threading.Thread(target=warm, name="astropy-warmup", daemon=True).start()


def main() -> None:
    """Start the application.

    Notes:
        - Logging is configured first: `msb_arch` does not configure it on import, so any
          record emitted before this would be swallowed by the package `NullHandler`.
          Defaults come first because reading the settings already logs.
    """
    # Configure logging first: msb_arch 0.2.0 no longer configures it on import, so any
    # record emitted before this line would be swallowed by the package NullHandler.
    # Defaults come first because reading the settings already logs; the level and the
    # clear-on-start flag are applied as soon as the settings are known.
    setup_logging(log_file="output.log")
    _startup_settings = PAstroCoreMainWindow.load_settings()
    _startup_level_name = _startup_settings.get("log_level", "INFO")
    update_logging_level(getattr(logging, _startup_level_name, logging.INFO))
    update_logging_clear("output.log", _startup_settings.get("clear_log_on_start", False))
    logger.debug("Logging initialized at start-up with level=%s", _startup_level_name)

    _warm_coordinate_tables()

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


if __name__ == "__main__":
    main()
