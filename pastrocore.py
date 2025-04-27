import sys
import os
import json
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QFileDialog, QMessageBox, QDialog,
    QTreeView, QTabWidget, QWidget, QProgressDialog, QMenu, QInputDialog
)
from PySide6.QtCore import Qt, Signal, Slot, QEvent, QMetaObject, QPoint
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
# Core files
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.spacetelescope import SpaceTelescope
from pastrocore.base.frequencies import IF, Frequencies
from pastrocore.base.observation import Observation
# UI files
from pastrocore.gui.ui_main_window import Ui_MainWindow
from pastrocore.gui.ui_dialog_about import Ui_AboutDialog
from pastrocore.gui.ui_tab_project import Ui_ProjectInfoTab
from pastrocore.gui.p_dialog_about import AboutDialog
from pastrocore.gui.p_tab_project import ProjectInfoTab
from pastrocore.gui.p_tab_observation import ObservationTab
from common.utils.logging_setup import logger

import pastrocore.gui.rc_icons

class PAstroCoreMainWindow(QMainWindow):
    """Main application window for pAstroCORE."""
    project_updated = Signal()
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.settings = self.load_settings()
        self.project = ScheduleProject(name="Untitled Project")
        self.manipulator = ScheduleManipulator(self.project)
        logger.info(f"PAstroCoreMainWindow initialized with project id: {id(self.project)}, manipulator id={id(self.manipulator)}")
        self.current_project_path = None
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        self.update_project_explorer()
        self.open_project_info_tab()
        project_explorer = self.ui.dockWidget.findChild(QTreeView, "projectExplorer")
        if project_explorer:
            project_explorer.setContextMenuPolicy(Qt.CustomContextMenu)
            project_explorer.customContextMenuRequested.connect(self.show_context_menu)

    def setup_connections(self):
        """Connect UI signals to slots."""
        self.ui.actionNewProject.triggered.connect(self.new_project)
        self.ui.actionOpenProject.triggered.connect(self.open_project)
        self.ui.actionSaveProject.triggered.connect(self.save_project)
        self.ui.actionSave_Project_As.triggered.connect(self.save_project_as)
        self.ui.actionImport_Observation.triggered.connect(self.import_observation)
        self.ui.actionExport_Observation.triggered.connect(self.export_observation)
        self.ui.actionPreferences.triggered.connect(self.open_preferences)
        self.ui.actionTelescope_Catalog_Manager.triggered.connect(self.open_telescope_catalog_manager)
        self.ui.actionSource_Catalog_Manager.triggered.connect(self.open_source_catalog_manager)
        self.ui.actionAbout.triggered.connect(self.show_about)
        project_explorer = self.ui.dockWidget.findChild(QTreeView, "projectExplorer")
        if project_explorer:
            project_explorer.clicked.connect(self.handle_project_explorer_click)
        self.project_updated.connect(self.update_project_explorer)

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

        if item_type == "project":
            add_action = menu.addAction(QIcon(":/icons/add_observation_icon.svg"), "Add Observation")
            menu.addAction(QIcon(":/icons/remove_project_icon.svg"), "New Project")
            menu.addAction(QIcon(":/icons/edit_project_icon.svg"), "Edit Project")
        elif item_type == "observations" or item_type == "observation":
            add_action = menu.addAction(QIcon(":/icons/add_observation_icon.svg"), "Add Observation")
            if item_type == "observation":
                remove_action = menu.addAction(QIcon(":/icons/remove_observation_icon.svg"), "Remove Observation")
                edit_action = menu.addAction(QIcon(":/icons/edit_observation_icon.svg"), "Edit Observation")
                remove_action.triggered.connect(lambda: self.remove_observation(text))
                edit_action.triggered.connect(lambda: self.edit_observation(text))
            else:
                menu.addAction(QIcon(":/icons/remove_project_icon.svg"), "Remove Observations")
                menu.addAction(QIcon(":/icons/edit_project_icon.svg"), "Edit Observations")
        else:
            return

        add_action.triggered.connect(self.add_observation)
        for action in menu.actions():
            if action.text() not in ["Add Observation", "Remove Observation", "Edit Observation"]:
                action.triggered.connect(lambda: QMessageBox.information(self, "Info", f"{action.text()} not implemented yet."))

        menu.exec(project_explorer.viewport().mapToGlobal(position))

    @Slot()
    def add_observation(self):
        """Add a new observation to the project via ScheduleManipulator."""
        # observation editor dialog
        obs_code, ok = QInputDialog.getText(self, "Add Observation", "Enter observation code:", text="OBS_DEFAULT")
        if not ok or not obs_code.strip():
            logger.info("Add observation cancelled or empty code provided")
            return

        try:
            request = {
                "operation": "configure",
                "obj": self.project,
                "attributes": {
                    "create_item": {"item_code": obs_code, "isactive": True}
                }
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Observation '{obs_code}' added to project '{self.project.get_name()}'")
                self.project_updated.emit()
                QMessageBox.information(self, "Success", f"Observation '{obs_code}' added successfully.")
            else:
                logger.error(f"Failed to add observation '{obs_code}': {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to add observation: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while adding observation '{obs_code}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to add observation: {str(e)}")

    @Slot(str)
    def remove_observation(self, obs_code: str):
        """Remove an observation from the project via ScheduleManipulator."""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete observation '{obs_code}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            logger.info(f"Deletion of observation '{obs_code}' cancelled")
            return

        try:
            request = {
                "operation": "configure",
                "obj": self.project,
                "attributes": {
                    "remove_item": obs_code
                }
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Observation '{obs_code}' removed from project '{self.project.get_name()}'")
                self.project_updated.emit()
                # Закрыть вкладку, если она открыта
                tab_container = self.ui.tabContainer
                for i in range(tab_container.count()):
                    widget = tab_container.widget(i)
                    if widget.objectName() == f"observationTab_{obs_code}":
                        tab_container.removeTab(i)
                        break
                QMessageBox.information(self, "Success", f"Observation '{obs_code}' removed successfully.")
            else:
                logger.error(f"Failed to remove observation '{obs_code}': {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to remove observation: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while removing observation '{obs_code}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to remove observation: {str(e)}")

    @Slot(str)
    def edit_observation(self, obs_code: str):
        """Open the ObservationTab for the specified observation."""
        logger.info(f"Opening edit tab for observation '{obs_code}'")
        self.open_observation_tab(obs_code)

    @Slot()
    def update_project_explorer(self):
        """Update Project Explorer tree using ScheduleInspector."""
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Project Explorer"])
        root = model.invisibleRootItem()

        project_name_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.project,
            "attributes": {"get_name": None}
        })
        project_name = project_name_response["result"] if project_name_response["status"] else "BABS"
        direct_name = self.project.get_name()
        logger.info(f"update_project_explorer: project id={id(self.project)}, name={project_name}, direct_name={direct_name}")

        project_item = QStandardItem(f"Project: {project_name}")
        project_item.setData("project", Qt.UserRole)
        root.appendRow(project_item)

        observations_item = QStandardItem("Observations")
        observations_item.setData("observations", Qt.UserRole)
        project_item.appendRow(observations_item)

        observations_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.project,
            "attributes": {"get_items": None}
        })
        if observations_response["status"]:
            result = observations_response["result"]
            if isinstance(result, dict):
                if result:
                    for obs_code, obs in result.items():
                        if isinstance(obs, Observation):
                            obs_item = QStandardItem(f"{obs.get_observation_code()}")
                            obs_item.setData("observation", Qt.UserRole)
                            observations_item.appendRow(obs_item)
                        else:
                            logger.error(f"Invalid observation type for code '{obs_code}': {type(obs)}")
                else:
                    logger.info("No observations found in project")
            else:
                logger.error(f"Expected dict for observations, got {type(result)}: {result}")
        else:
            logger.error(f"Failed to inspect observations: {observations_response.get('error', 'Unknown error')}")

        project_explorer = self.ui.dockWidget.findChild(QTreeView, "projectExplorer")
        if project_explorer:
            project_explorer.setModel(None)
            project_explorer.setModel(model)
            project_explorer.expandAll()
            project_explorer.viewport().update()

    def load_settings(self) -> dict:
        """Load application settings from JSON file."""
        settings_file = "settings.json"
        default_settings = {"sources_dir": "", "telescopes_dir": ""}
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load settings: {e}")
        return default_settings

    def save_settings(self):
        """Save application settings to JSON file."""
        try:
            with open("settings.json", "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")

    @Slot()
    def new_project(self):
        """Create a new project."""
        self.project = ScheduleProject(name="Untitled Project")
        self.manipulator = ScheduleManipulator(self.project)
        logger.info(f"New project created with project id: {id(self.project)}, manipulator id={id(self.manipulator)}")
        self.current_project_path = None
        self.project_updated.emit()
        self.ui.tabContainer.setCurrentWidget(self.ui.tabWelcome)
        QMessageBox.information(self, "New Project", "New project created.")

    @Slot()
    def open_project(self):
        """Open an existing project from file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "pAstroCORE Project (*.pastro)")
        if file_path:
            progress = QProgressDialog("Opening project...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setAutoClose(True)
            progress.show()
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                self.project = ScheduleProject.from_dict(data)
                self.manipulator = ScheduleManipulator(self.project)
                logger.info(f"Project opened with project id: {id(self.project)}, manipulator id={id(self.manipulator)}")
                self.current_project_path = file_path
                self.project_updated.emit()
                QMessageBox.information(self, "Open Project", f"Project {file_path} opened.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open project: {e}")
            finally:
                progress.close()

    @Slot()
    def save_project(self):
        """Save the current project."""
        if self.current_project_path:
            progress = QProgressDialog("Saving project...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setAutoClose(True)
            progress.show()
            try:
                with open(self.current_project_path, "w") as f:
                    json.dump(self.project.to_dict(), f, indent=4)
                QMessageBox.information(self, "Save Project", "Project saved.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save project: {e}")
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
    def import_observation(self):
        """Import an observation (placeholder)."""
        QMessageBox.information(self, "Import Observation", "Import observation functionality not implemented yet.")

    @Slot()
    def export_observation(self):
        """Export an observation (placeholder)."""
        QMessageBox.information(self, "Export Observation", "Export observation functionality not implemented yet.")

    @Slot()
    def open_preferences(self):
        """Open preferences dialog (placeholder)."""
        QMessageBox.information(self, "Preferences", "Preferences dialog not implemented yet.")

    @Slot()
    def open_telescope_catalog_manager(self):
        """Open telescope catalog manager (placeholder)."""
        telescopes_dir = self.settings.get("telescopes_dir", "")
        if not telescopes_dir or not os.path.isdir(telescopes_dir):
            QMessageBox.warning(self, "Warning", "Please set a valid telescopes directory in Preferences.")
            return
        QMessageBox.information(self, "Telescope Catalog", "Telescope Catalog Manager not implemented yet.")

    @Slot()
    def open_source_catalog_manager(self):
        """Open source catalog manager (placeholder)."""
        QMessageBox.information(self, "Source Catalog Manager", "Source catalog manager not implemented yet.")

    @Slot()
    def show_about(self):
        """Show about dialog."""
        dialog = AboutDialog(self)
        dialog.exec()

    @Slot()
    def handle_project_explorer_click(self, index):
        """Handle clicks on Project Explorer."""
        item = self.ui.projectExplorer.model().itemFromIndex(index)
        if not item:
            return
        item_type = item.data(Qt.UserRole)
        text = item.text()
        if item_type == "project":
            self.open_project_info_tab()
        elif item_type == "observation":
            obs_code = text
            observation = self.project.get_observation(obs_code)
            self.open_observation_tab(obs_code)

    def open_project_info_tab(self):
        """Open or switch to ProjectInfoTab."""
        tab_container = self.ui.tabContainer
        for i in range(tab_container.count()):
            if tab_container.widget(i).objectName() == "projectInfoTab":
                tab_container.setCurrentIndex(i)
                return
        project_tab = ProjectInfoTab(self.project, self.manipulator, self)
        project_tab.setObjectName("projectInfoTab")
        tab_container.addTab(project_tab, "Project")
        tab_container.setCurrentWidget(project_tab)
        project_tab.project_name_changed.connect(self.on_projectInfoTab_project_name_changed)

    @Slot(str)
    def on_projectInfoTab_project_name_changed(self, name: str):
        """Handle project name change signal."""
        self.project_updated.emit()

    def open_observation_tab(self, obs_code: str):
        """Open or switch to a tab for editing an observation."""
        tab_container = self.ui.tabContainer
        for i in range(tab_container.count()):
            widget = tab_container.widget(i)
            if widget.objectName() == f"observationTab_{obs_code}":
                tab_container.setCurrentIndex(i)
                widget.setFocus()  # Установить фокус на вкладку
                return
        observation = self.project.get_observation(obs_code)
        observation_tab = ObservationTab(observation, self.manipulator, self)
        observation_tab.setObjectName(f"observationTab_{obs_code}")
        tab_container.addTab(observation_tab, f"Observation: {obs_code}")
        tab_container.setCurrentWidget(observation_tab)
        observation_tab.setFocus()  # Установить фокус на новую вкладку
        observation_tab.observation_updated.connect(self.on_observationTab_observation_updated)

    @Slot()
    def on_observationTab_observation_updated(self):
        """Handle observation update signal."""
        logger.info("Observation updated")
        self.project_updated.emit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Применение QSS
    app.setStyleSheet("""
        QMenuBar {
            background-color: #ffffff;
            font-family: Arial;
            color: #000000;
        }
        QMenuBar::item {
            background: #ffffff;
            padding: 4px 8px;
            color: #000000;
            spacing: 4px;
        }
        QMenuBar::item:selected {
            background: #0078d7;
            color: #ffffff;
        }
        QMenu {
            background-color: #ffffff;
            border: 1px solid #d3d3d3;
            font-family: Arial;
        }
        QMenu::item {
            padding: 4px 24px 4px 8px;
            background: #ffffff;
            color: #000000;
            icon-size: 24px;
        }
        QMenu::item:selected {
            background: #0078d7;
            color: #ffffff;
        }
        QMenu::item:hover {
            background: #e0e0e0;
            color: #000000;
        }
        QMenu::icon {
            padding-left: 4px;
        }
    """)
    window = PAstroCoreMainWindow()
    window.show()
    sys.exit(app.exec())