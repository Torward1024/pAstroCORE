import sys
import os
import json
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QFileDialog, QMessageBox,
    QTreeView, QTabBar, QProgressDialog, QMenu
)
from PySide6.QtCore import Qt, Signal, Slot, QPoint
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
# Core files
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_visualizer import ScheduleVisualizer
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
        self.catalog_manager = self.initialize_catalog_manager()
        logger.debug(f"PAstroCoreMainWindow initialized with project id: {id(self.project)}, manipulator id={id(self.manipulator)}, catalog_manager id={id(self.catalog_manager)}")
        self.current_project_path = None
        self.setup_ui()
        self.setup_connections()

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
            logger.info(f"CatalogManager initialized with {sources_count} sources and {telescopes_count} telescopes")
            return catalog_manager
        except Exception as e:
            logger.error(f"Failed to initialize CatalogManager with sources='{sources_path}', telescopes='{telescopes_path}': {str(e)}")
            QMessageBox.warning(self, "Warning", f"Failed to load catalogs: {str(e)}. Using empty catalogs.")
            return CatalogManager()

    def setup_ui(self):
        self.update_project_explorer()
        # Удаляем вкладку Welcome, если она есть
        for i in range(self.ui.tabContainer.count()):
            if self.ui.tabContainer.widget(i).objectName() == "tabWelcome":
                self.ui.tabContainer.removeTab(i)
                break
        # Открываем вкладку проекта сразу
        self.open_project_info_tab()
        # Делаем вкладки закрываемыми
        self.ui.tabContainer.setTabsClosable(True)
        # Убираем кнопку закрытия для вкладки проекта
        for i in range(self.ui.tabContainer.count()):
            if self.ui.tabContainer.widget(i).objectName() == "projectInfoTab":
                self.ui.tabContainer.tabBar().setTabButton(i, QTabBar.ButtonPosition.RightSide, None)
        # Включаем контекстное меню для projectExplorer
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
        self.ui.actionImport_Observation.triggered.connect(self.import_new_observation)
        self.ui.actionExport_Observation.triggered.connect(self.export_observation)
        self.ui.actionPreferences.triggered.connect(self.open_preferences)
        self.ui.actionTelescope_Catalog_Manager.triggered.connect(self.open_telescope_catalog_manager)
        self.ui.actionSource_Catalog_Manager.triggered.connect(self.open_source_catalog_manager)
        self.ui.actionAbout.triggered.connect(self.show_about)
        self.ui.actionCalculate.triggered.connect(self.open_calculation_dialog)
        self.ui.actionVisualize.triggered.connect(self.open_visualization_dialog)
        project_explorer = self.ui.dockWidget.findChild(QTreeView, "projectExplorer")
        if project_explorer:
            project_explorer.clicked.connect(self.handle_project_explorer_click)
        self.project_updated.connect(self.update_project_explorer)
        self.ui.tabContainer.tabCloseRequested.connect(self.handle_tab_close)
        self.project_updated.connect(self.update_all_tabs)

    @Slot()
    def open_calculation_dialog(self):
        """Open the calculation dialog."""
        try:
            dialog = CalculationDialog(self.manipulator, self.project, parent=self)
            dialog.exec()
            logger.info("Calculation dialog opened and closed")
        except Exception as e:
            logger.error(f"Failed to open calculation dialog: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to open calculation dialog: {str(e)}")
    
    @Slot()
    def open_visualization_dialog(self):
        """Open the visualization dialog for the current project."""
        try:
            dialog = VisualizationDialog(self.project, self.manipulator, parent=self)
            dialog.exec()
            logger.info("Visualization dialog opened and closed")
        except Exception as e:
            logger.error(f"Failed to open visualization dialog: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to open visualization dialog: {str(e)}")

    def handle_tab_close(self, index):
        """Handle closing of tabs, prevent closing of project tab."""
        widget = self.ui.tabContainer.widget(index)
        if widget.objectName() == "projectInfoTab":
            return
        self.ui.tabContainer.removeTab(index)

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
                obs_name = item.data(Qt.UserRole + 1)
                obs_code = text
                remove_action = menu.addAction(QIcon(":/icons/remove_observation_icon.svg"), "Remove Observation")
                edit_action = menu.addAction(QIcon(":/icons/edit_observation_icon.svg"), "Edit Observation")
                remove_action.triggered.connect(lambda: self.remove_observation(obs_name, obs_code))
                edit_action.triggered.connect(lambda: self.edit_observation(obs_name, obs_code))
            else:
                remove_action = menu.addAction(QIcon(":/icons/remove_project_icon.svg"), "Remove Observations")
                remove_action.triggered.connect(lambda: self.remove_observations())
        else:
            return

        add_action.triggered.connect(self.add_observation)
        for action in menu.actions():
            if action.text() not in ["Add Observation", "Remove Observation", "Remove Observations", "Edit Observation"]:
                action.triggered.connect(lambda: QMessageBox.information(self, "Info", f"{action.text()} not implemented yet."))

        menu.exec(project_explorer.viewport().mapToGlobal(position))

    @Slot()
    def add_observation(self):
        """Add a new observation to the project via ScheduleManipulator."""
        dialog = AddObservationDialog(self.project, self.manipulator, self)
        dialog.observation_added.connect(self.handle_observation_added)
        dialog.exec()

    @Slot(str, str)
    def handle_observation_added(self, obs_code: str, obs_type: str):
        """Handle observation added signal."""
        logger.info(f"Observation '{obs_code}' (type: {obs_type}) added")
        self.project_updated.emit()

    @Slot(str)
    def remove_observation(self, obs_name: str, obs_code: str):
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
            obs_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.project,
                "attributes": {"get_item": obs_name}
            })
            if not obs_response["status"]:
                logger.error(f"Failed to find observation with code '{obs_code}': {obs_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Observation '{obs_code}' not found")
                return

            request = {
                "operation": "configure",
                "obj": self.project,
                "attributes": {
                    "remove_item": obs_name
                }
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Observation with code '{obs_code}' and name '{obs_name}' removed from project '{self.project.get_name()}'")
                self.project_updated.emit()

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

    @Slot()
    def remove_observations(self):
        """Remove all observations from the project via ScheduleManipulator."""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete all observations?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            logger.info(f"Deletion of observations cancelled")
            return

        try:
            request = {
                "operation": "configure",
                "obj": self.project,
                "attributes": {
                    "clear": None
                }
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"All observations were removed from project '{self.project.get_name()}'")
                self.project_updated.emit()

                tab_container = self.ui.tabContainer
                for i in range(self.ui.tabContainer.count() - 1, -1, -1):
                    widget = self.ui.tabContainer.widget(i)
                    if widget.objectName() != "projectInfoTab":
                        self.ui.tabContainer.removeTab(i)
            else:
                logger.error(f"Failed to remove observations: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to remove observations: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while removing observations: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to remove observations: {str(e)}")

    @Slot(str)
    def edit_observation(self, obs_name: str, obs_code: str):
        """Open the ObservationTab for the specified observation."""
        logger.debug(f"Opening edit tab for observation with code '{obs_code}'")
        self.open_observation_tab(obs_name, obs_code)

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
        project_name = project_name_response["result"] if project_name_response["status"] else "Untitled Project"
        direct_name = self.project.get_name()
        logger.debug(f"update_project_explorer: project id={id(self.project)}, name={project_name}, direct_name={direct_name}")

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
                    for obs_name, obs in result.items():
                        # Запрашиваем код наблюдения через Manipulator
                        code_response = self.manipulator.process_request({
                            "operation": "inspect",
                            "obj": obs,
                            "attributes": {"get_observation_code": None}
                        })
                        if code_response["status"]:
                            obs_item = QStandardItem(code_response["result"])  # Отображаем code
                            obs_item.setData("observation", Qt.UserRole)
                            obs_item.setData(obs_name, Qt.UserRole + 1)  # Сохраняем obs_name
                            observations_item.appendRow(obs_item)
                        else:
                            logger.error(f"Failed to get code for observation with name '{obs_name}': {code_response.get('error', 'Unknown error')}")
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
        """Load application settings from settings.pastro file."""
        settings_file = "settings.pastro"
        default_settings = {
            "sources_catalog_path": os.path.join("catalogs", "sources.dat"),
            "telescopes_catalog_path": os.path.join("catalogs", "telescopes.dat")
        }
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r") as f:
                    loaded_settings = json.load(f)
                # Merge with default settings to ensure all keys are present
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
        """Create a new project, ensuring all old project data is cleared."""
        # Отключаем все сигналы, связанные со старым проектом
        try:
            self.project_updated.disconnect()
        except Exception as e:
            logger.debug(f"No connections to disconnect for project_updated: {str(e)}")

        # Очищаем все вкладки
        for i in range(self.ui.tabContainer.count() - 1, -1, -1):
            widget = self.ui.tabContainer.widget(i)
            if widget:
                # Отключаем все сигналы виджета, если они есть
                try:
                    widget.disconnect()
                except Exception as e:
                    logger.debug(f"No signals to disconnect for widget {widget.objectName()}: {str(e)}")
                self.ui.tabContainer.removeTab(i)
                widget.deleteLater()  # Помечаем виджет для удаления из памяти

        # Создаем новый проект и манипулятор
        self.project = ScheduleProject(name="Untitled Project")
        self.manipulator = ScheduleManipulator(self.project)
        self.current_project_path = None
        logger.info(f"New project created with project id: {id(self.project)}, manipulator id={id(self.manipulator)}")

        # Очищаем projectExplorer
        project_explorer = self.ui.dockWidget.findChild(QTreeView, "projectExplorer")
        if project_explorer:
            project_explorer.setModel(None)  # Удаляем старую модель
            self.update_project_explorer()  # Создаем новую модель

        # Открываем вкладку проекта
        self.open_project_info_tab()

        # Восстанавливаем соединения сигналов
        self.setup_connections()
        logger.debug("Connections re-established for new project")

        # Обновляем интерфейс
        self.project_updated.emit()

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
                # Очищаем все вкладки, включая вкладку проекта
                for i in range(self.ui.tabContainer.count() - 1, -1, -1):
                    self.ui.tabContainer.removeTab(i)
                self.open_project_info_tab()
            except Exception as e:
                logger.error(f"Failed to open project: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to open project: {str(e)}")
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
        """Import a new observation into the project."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Import New Observation", "", "pAstroCORE Data (*.pastrod)")
        if not file_path:
            logger.info("Import new observation cancelled: No file selected")
            return

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            # Создаем новое наблюдение
            imported_observation = Observation.from_dict(data)
            if not hasattr(imported_observation, 'observation_type') or imported_observation.observation_type not in ["VLBI", "SINGLE_DISH"]:
                imported_observation.observation_type = "VLBI"  # Значение по умолчанию
            # Запрашиваем уникальный код наблюдения
            # Проверяем уникальность кода
            obs_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.project,
                "attributes": {"get_observation_by_code": imported_observation.code}
            })
            if obs_response["status"] and obs_response["result"] is not None:
                logger.error(f"Observation code '{imported_observation.code}' already exists")
                QMessageBox.critical(self, "Error", f"Observation code '{imported_observation.code}' already exists.")
                return
            # Добавляем наблюдение через Manipulator
            request = {
                "operation": "configure",
                "obj": self.project,
                "attributes": {
                    "add_item": imported_observation
                    }
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"New observation '{imported_observation.code}' imported successfully")
                self.project_updated.emit()
                QMessageBox.information(self, "Success", f"Observation '{imported_observation.code}' imported successfully.")
            else:
                logger.error(f"Failed to set observation data for '{imported_observation.code}': {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to import observation: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while importing new observation: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to import observation: {str(e)}")

    @Slot(str)
    def import_observation(self, obs_name: str, obs_code: str):
        """Import an observation to overwrite an existing one."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Observation", "", "pAstroCORE Data (*.pastrod)")
        if not file_path:
            logger.info(f"Import observation '{obs_code}' cancelled: No file selected")
            return

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            # Получаем существующее наблюдение
            obs_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.project,
                "attributes": {"get_item": obs_name}
            })
            if not obs_response["status"] or not obs_response["result"]:
                logger.error(f"Failed to find observation '{obs_code}': {obs_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Observation '{obs_code}' not found")
                return

            existing_observation = obs_response["result"]
            existing_name = existing_observation.name
            existing_code = existing_observation.code

            # Создаем новое наблюдение из данных файла
            imported_observation = Observation.from_dict(data)
            # Сохраняем существующие имя и код
            imported_observation.name = existing_name
            imported_observation.code = existing_code

            # Обновляем наблюдение через Manipulator
            request = {
                "operation": "configure",
                "obj": self.project,
                "attributes": {
                    "set_item": {"name": existing_name, "item": imported_observation}
                }
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Observation '{obs_code}' overwritten successfully")
                self.project_updated.emit()
                QMessageBox.information(self, "Success", f"Observation '{obs_code}' imported successfully.")
            else:
                logger.error(f"Failed to overwrite observation '{obs_code}': {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to import observation: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while importing observation '{obs_code}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to import observation: {str(e)}")

    @Slot(str)
    def export_observation(self, obs_name: str, obs_code: str):
        """Export an observation by prompting for observation code."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Observation", "", "pAstroCORE Data (*.pastrod)")
        if not file_path:
            logger.info(f"Export observation '{obs_code}' cancelled: No file selected")
            return
        if not file_path.endswith(".pastrod"):
            file_path += ".pastrod"

        try:
            # Получаем объект наблюдения
            obs_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.project,
                "attributes": {"get_item": obs_name}
            })
            if not obs_response["status"] or not obs_response["result"]:
                logger.error(f"Failed to get observation '{obs_code}': {obs_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Observation '{obs_code}' not found")
                return

            observation = obs_response["result"]
            with open(file_path, "w") as f:
                json.dump(observation.to_dict(), f, indent=4)
            logger.info(f"Observation '{obs_code}' exported to '{file_path}'")
            QMessageBox.information(self, "Success", f"Observation '{obs_code}' exported successfully.")
        except Exception as e:
            logger.error(f"Exception while exporting observation '{obs_code}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to export observation: {str(e)}")

    @Slot()
    def open_preferences(self):
        """Open the preferences dialog to configure settings."""
        dialog = PreferencesDialog(self.settings, self)
        dialog.settings_updated.connect(self.handle_settings_updated)
        dialog.exec()

    @Slot(dict)
    def handle_settings_updated(self, settings: dict):
        """Handle settings updated signal from PreferencesDialog."""
        self.settings = settings
        self.save_settings(self.settings)
        # Reinitialize CatalogManager with new settings
        self.catalog_manager = self.initialize_catalog_manager()
        logger.info(f"CatalogManager reinitialized with new settings, id={id(self.catalog_manager)}")

    @Slot()
    def open_telescope_catalog_manager(self):
        """Open the telescopes catalog browser dialog."""
        telescopes_path = self.settings.get("telescopes_catalog_path", os.path.join("catalogs", "telescopes.dat"))
        if not os.path.isfile(telescopes_path):
            logger.error(f"Telescopes catalog file not found: {telescopes_path}")
            QMessageBox.warning(self, "Warning", "Please set a valid telescopes catalog path in Preferences.")
            return

        telescopes = self.catalog_manager.telescope_catalog.get_items()  # Используем get_items()
        if not telescopes:
            logger.warning("Telescopes catalog is empty")
            QMessageBox.warning(self, "Warning", "Telescopes catalog is empty. Check the catalog file or reload in Preferences.")
            return

        dialog = TelescopesCatalogDialog(self.catalog_manager, self)
        dialog.exec()
        logger.info("Telescopes catalog browser dialog opened")

    @Slot()
    def open_source_catalog_manager(self):
        """Open the sources catalog browser dialog."""
        sources_path = self.settings.get("sources_catalog_path", os.path.join("catalogs", "sources.dat"))
        if not os.path.isfile(sources_path):
            logger.error(f"Sources catalog file not found: {sources_path}")
            QMessageBox.warning(self, "Warning", "Please set a valid sources catalog path in Preferences.")
            return

        sources = self.catalog_manager.source_catalog.get_items()  # Используем get_items()
        if not sources:
            logger.warning("Sources catalog is empty")
            QMessageBox.warning(self, "Warning", "Sources catalog is empty. Check the catalog file or reload in Preferences.")
            return

        dialog = SourcesCatalogDialog(self.catalog_manager, self)
        dialog.exec()
        logger.info("Sources catalog browser dialog opened")

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
            # Получаем наблюдение через Manipulator
            obs_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.project,
                "attributes": {"get_observation_by_code": obs_code}
            })
            obs_name = obs_response["result"].name
            if obs_response["status"]:
                self.open_observation_tab(obs_name, obs_code)
            else:
                logger.error(f"Failed to get observation with code '{obs_code}': {obs_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to open observation '{obs_code}': {obs_response.get('error', 'Unknown error')}")

    def open_project_info_tab(self):
        """Open or switch to ProjectInfoTab."""
        tab_container = self.ui.tabContainer
        for i in range(tab_container.count()):
            if tab_container.widget(i).objectName() == "projectInfoTab":
                tab_container.setCurrentIndex(i)
                # Обновляем вкладку проекта
                widget = tab_container.widget(i)
                widget.update_tab()
                # Убираем кнопку закрытия для вкладки проекта
                tab_container.tabBar().setTabButton(i, QTabBar.ButtonPosition.RightSide, None)
                return
        project_tab = ProjectInfoTab(self.project, self.manipulator, self)
        project_tab.setObjectName("projectInfoTab")
        tab_container.addTab(project_tab, "Project")
        tab_container.setCurrentWidget(project_tab)
        project_tab.update_tab()  # Обновляем вкладку сразу после создания
        # Убираем кнопку закрытия для новой вкладки проекта
        for i in range(tab_container.count()):
            if tab_container.widget(i).objectName() == "projectInfoTab":
                tab_container.tabBar().setTabButton(i, QTabBar.ButtonPosition.RightSide, None)
                break
        project_tab.project_name_changed.connect(self.handle_projectInfoTab_project_name_changed)
        # Подключаем сигнал project_updated для обновления вкладки
        self.project_updated.connect(project_tab.update_tab)

    @Slot(str)
    def handle_projectInfoTab_project_name_changed(self, name: str):
        """Handle project name change signal."""
        self.project_updated.emit()

    def open_observation_tab(self, obs_name: str, obs_code: str):
        """Open or switch to a tab for editing an observation."""
        tab_container = self.ui.tabContainer
        for i in range(tab_container.count()):
            widget = tab_container.widget(i)
            if widget.objectName() == f"observationTab_{obs_code}":
                tab_container.setCurrentIndex(i)
                widget.setFocus()

                widget.update_tab()
                return

        obs_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.project,
            "attributes": {"get_item": obs_name}
        })
        if obs_response["status"]:
            observation = obs_response["result"]
            observation_tab = ObservationTab(observation, self.project, self.manipulator, self.catalog_manager, self)
            observation_tab.setObjectName(f"observationTab_{obs_code}")
            tab_container.addTab(observation_tab, f"Observation: {obs_code}")
            tab_container.setCurrentWidget(observation_tab)
            observation_tab.setFocus()
            observation_tab.observation_updated.connect(self.handle_observationTab_observation_updated)
            # Подключаем сигнал project_updated для обновления вкладки
            self.project_updated.connect(observation_tab.update_tab)
        else:
            logger.error(f"Failed to open observation tab for code '{obs_code}': {obs_response.get('error', 'Unknown error')}")
            QMessageBox.critical(self, "Error", f"Failed to open observation tab: {obs_response.get('error', 'Unknown error')}")

    @Slot()
    def handle_observationTab_observation_updated(self):
        """Handle observation update signal."""
        logger.info("Observation updated")
        self.project_updated.emit()

    @Slot()
    def update_all_tabs(self):
        """Update all open tabs when project data changes."""
        for i in range(self.ui.tabContainer.count()):
            widget = self.ui.tabContainer.widget(i)
            if hasattr(widget, 'update_tab'):
                widget.update_tab()
        logger.info("All tabs updated")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Применение QSS
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
    """)
    window = PAstroCoreMainWindow()
    window.show()
    sys.exit(app.exec())