import sys
import os
import json
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QFileDialog, QMessageBox, QDialog,
    QTreeView, QTabWidget, QWidget, QProgressDialog
)
from PySide6.QtCore import Qt, Signal, Slot, QEvent, QMetaObject
from PySide6.QtGui import QStandardItemModel, QStandardItem
# Core files
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.spacetelescope import SpaceTelescope
from pastrocore.base.frequencies import IF, Frequencies
from pastrocore.base.observation import Observation
# UI files
from pastrocore.gui.main_window import Ui_MainWindow
from pastrocore.gui.dialog_about import Ui_AboutDialog
from pastrocore.gui.tab_project import Ui_ProjectInfoTab
from common.utils.logging_setup import logger

class AboutDialog(QDialog):
    """Dialog for displaying application information."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_AboutDialog()
        self.ui.setupUi(self)
        self.setModal(True)

class ProjectInfoTab(QWidget):
    """Widget for displaying and editing project information."""
    project_name_changed = Signal(str)  # Signal for project name changes

    def __init__(self, project: ScheduleProject, manipulator: ScheduleManipulator, parent=None):
        super().__init__(parent)
        self.ui = Ui_ProjectInfoTab()
        self.ui.setupUi(self)
        self.project = project
        self.manipulator = manipulator
        self._ignore_editing_finished = False
        logger.info(f"ProjectInfoTab initialized with project id: {id(self.project)}, manipulator id: {id(self.manipulator)}")
        self.setup_ui()

    def setup_ui(self):
        """Initialize UI elements and connect signals."""
        name = self.get_project_name()
        self.ui.lineEdit.setText(name)
        self.ui.lineEdit.setReadOnly(True)
        self.ui.lineEdit.editingFinished.connect(self.handle_project_name_confirmed)
        self.ui.lineEdit.installEventFilter(self)
        self.ui.lineEdit.setStyleSheet("QLineEdit[readOnly='true'] { border: none; background: transparent; }")
        self.setup_table()

    def keyPressEvent(self, event):
        """Handle key press events, including Esc."""
        if event.key() == Qt.Key_Escape and not self.ui.lineEdit.isReadOnly():
            logger.info(f"keyPressEvent: Esc pressed, current text={self.ui.lineEdit.text()}")
            self._ignore_editing_finished = True
            self.ui.lineEdit.setText(self.get_project_name())
            self.ui.lineEdit.setReadOnly(True)
            self._ignore_editing_finished = False
        super().keyPressEvent(event)

    def setup_table(self):
        """Set up project information table."""
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Property", "Value"])
        items = [
            ("Observations", str(len(self.project.get_items()))),
        ]
        for prop, val in items:
            model.appendRow([QStandardItem(prop), QStandardItem(val)])
        self.ui.projectInfoTable.setModel(model)
        self.ui.projectInfoTable.horizontalHeader().setStretchLastSection(True)

    def get_project_name(self) -> str:
        """Retrieve project name using ScheduleInspector."""
        direct_name = self.project.get_name()
        response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.project,
            "attributes": {"get_name": None}
        })
        if response["status"]:
            logger.info(f"get_project_name: project id={id(self.project)}, name={response['result']}, direct_name={direct_name}")
            return response["result"]
        logger.error(f"Failed to inspect project name: {response.get('error', 'Unknown error')}")
        return "NOSE"

    def eventFilter(self, obj, event):
        """Handle events for QLineEdit."""
        if obj == self.ui.lineEdit and event.type() == QEvent.MouseButtonDblClick:
            self.ui.lineEdit.setReadOnly(False)
            self.ui.lineEdit.setFocus()
            self.ui.lineEdit.selectAll()
            return True
        return super().eventFilter(obj, event)

    @Slot()
    def handle_project_name_confirmed(self):
        """Handle project name confirmation after editing."""
        logger.info(f"handle_project_name_confirmed: text={self.ui.lineEdit.text()}, ignore={self._ignore_editing_finished}")
        if self._ignore_editing_finished:
            logger.info("Ignoring editingFinished due to Esc key")
            return

        name = self.ui.lineEdit.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Project name cannot be empty.")
            self.ui.lineEdit.setText(self.get_project_name())
            self.ui.lineEdit.setReadOnly(True)
            return

        current_name = self.get_project_name()
        if name == current_name:
            logger.info(f"Project name '{name}' unchanged, skipping configure")
            self.ui.lineEdit.setReadOnly(True)
            return

        logger.info(f"Before configure: project id={id(self.project)}, name={current_name}, manipulator id={id(self.manipulator)}")
        response = self.manipulator.process_request({
            "operation": "configure",
            "obj": self.project,
            "attributes": {"set_name": name}
        })

        if response["status"]:
            self.project.set_name(name)
            logger.info(f"Project name updated to '{name}', project id={id(self.project)}")
            self.project_name_changed.emit(name)
        else:
            logger.error(f"Failed to update project name: {response.get('error', 'Unknown error')}")
            QMessageBox.critical(self, "Error", f"Failed to update project name: {response.get('error', 'Unknown error')}")
            self.ui.lineEdit.setText(self.get_project_name())

        self.ui.lineEdit.setReadOnly(True)
        self.setup_table()

class ObservationTab(QWidget):
    """Widget for editing observation details."""
    observation_updated = Signal()

    def __init__(self, observation: Observation, manipulator: ScheduleManipulator, parent=None):
        super().__init__(parent)
        self.observation = observation
        self.manipulator = manipulator
        self.setup_ui()

    def setup_ui(self):
        from PySide6.QtWidgets import QPushButton, QVBoxLayout
        layout = QVBoxLayout(self)
        button = QPushButton("Test Observation Update")
        button.clicked.connect(self.observation_updated.emit)
        layout.addWidget(button)

class PAstroCoreMainWindow(QMainWindow):
    """Main application window for pAstroCORE."""
    project_updated = Signal()  # Signal for project updates

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
                            obs_item = QStandardItem(f"Observation: {obs.get_observation_code()}")
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
        elif text.startswith("Observation:"):
            obs_code = text.split(":", 1)[1].strip()
            observation = self.project.get_observation(obs_code)
            QMessageBox.information(self, "Edit Observation", f"Editing observation {obs_code} not implemented yet.")

    def open_project_info_tab(self):
        """Open or switch to ProjectInfoTab."""
        tab_container = self.ui.tabContainer
        for i in range(tab_container.count()):
            if tab_container.widget(i).objectName() == "projectInfoTab":
                tab_container.setCurrentIndex(i)
                return
        project_tab = ProjectInfoTab(self.project, self.manipulator, self)
        project_tab.setObjectName("projectInfoTab")
        tab_container.addTab(project_tab, "Project Information")
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
                return
        observation = self.project.get_observation(obs_code)
        observation_tab = ObservationTab(observation, self.manipulator, self)
        observation_tab.setObjectName(f"observationTab_{obs_code}")
        tab_container.addTab(observation_tab, f"Observation: {obs_code}")
        tab_container.setCurrentWidget(observation_tab)
        observation_tab.observation_updated.connect(self.on_observationTab_observation_updated)

    @Slot()
    def on_observationTab_observation_updated(self):
        """Handle observation update signal."""
        logger.info("Observation updated")
        self.project_updated.emit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PAstroCoreMainWindow()
    window.show()
    sys.exit(app.exec())