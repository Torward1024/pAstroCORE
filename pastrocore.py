import sys
import os
import json
from PySide6.QtWidgets import QMainWindow, QApplication, QFileDialog, QMessageBox, QMenuBar, QStatusBar, QDockWidget, QWidget, QDialog, QTreeView, QTabWidget
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice, Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem
# Импорты классов
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.super.schedule_manipulator import Manipulator
from pastrocore.base.spacetelescope import SpaceTelescope
from pastrocore.base.frequencies import IF, Frequencies
# Диалоги закомментированы, раскомментируйте, если файлы доступны
# from application_settings import ApplicationSettingsDialog
# from spacetelescope_editor import SpaceTelescopeEditorDialog
# from if_editor import IFEditorDialog

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.load_ui()

    def load_ui(self):
        ui_file_path = r"pastrocore/gui/main_window.ui"
        if not os.path.exists(ui_file_path):
            QMessageBox.critical(self, "Error", f"UI file not found: {ui_file_path}")
            sys.exit(1)
        self.ui = loadUi(ui_file_path, self)
        self.setCentralWidget(self.ui.mainCentralWidget)
        self.setMenuBar(self.ui.mainMenuBar)
        self.setStatusBar(self.ui.mainStatusBar)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.ui.dockWidget)

class PAstroCoreMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.load_ui()
        self.settings = self.load_settings()
        self.project = ScheduleProject(name="Untitled Project")  # Используем ScheduleProject
        self.setup_project_explorer()
        self.setup_connections()
        self.current_project_path = None
        self.manipulator = Manipulator(self.project)  # Инициализация Manipulator

    def load_ui(self):
        loader = QUiLoader()
        ui_file_path = r"pastrocore/gui/main_window.ui"
        file = QFile(ui_file_path)
        if not file.exists():
            QMessageBox.critical(self, "Error", f"UI file not found: {ui_file_path}")
            sys.exit(1)
        file.open(QIODevice.ReadOnly)
        self.ui = loader.load(file, self)
        file.close()
        self.setCentralWidget(self.ui.mainCentralWidget)
        self.setMenuBar(self.ui.mainMenuBar)
        self.setStatusBar(self.ui.mainStatusBar)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.ui.dockWidget)        

    def load_settings(self):
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
        try:
            with open("settings.json", "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")

    def setup_project_explorer(self):
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Project Explorer"])
        root = model.invisibleRootItem()
        telescopes_item = QStandardItem("Telescopes")
        frequencies_item = QStandardItem("Frequencies")
        sources_item = QStandardItem("Sources")
        root.appendRow(telescopes_item)
        root.appendRow(frequencies_item)
        root.appendRow(sources_item)
        project_explorer = self.ui.projectExplorer
        if not project_explorer:
            QMessageBox.critical(self, "Error", "Failed to find projectExplorer in UI file")
            sys.exit(1)
        project_explorer.setModel(model)
        project_explorer.expandAll()

    def setup_connections(self):
        # File menu
        self.ui.actionNewProject.triggered.connect(self.new_project)
        self.ui.actionOpenProject.triggered.connect(self.open_project)
        self.ui.actionSaveProject.triggered.connect(self.save_project)
        self.ui.actionSave_Project_As.triggered.connect(self.save_project_as)
        self.ui.actionImport_Observation.triggered.connect(self.import_observation)
        self.ui.actionExport_Observation.triggered.connect(self.export_observation)
        # Options menu
        self.ui.actionPreferences.triggered.connect(self.open_preferences)
        self.ui.actionTelescope_Catalog_Manager.triggered.connect(self.open_telescope_catalog_manager)
        self.ui.actionSource_Catalog_Manager.triggered.connect(self.open_source_catalog_manager)
        # Help menu
        self.ui.actionAbout.triggered.connect(self.show_about)
        # Project Explorer
        project_explorer = self.ui.dockWidget.findChild(QTreeView, "projectExplorer")
        if project_explorer:
            project_explorer.doubleClicked.connect(self.handle_project_explorer_double_click)

    def new_project(self):
        self.project_data = {"telescopes": [], "frequencies": [], "sources": []}
        self.current_project_path = None
        self.update_project_explorer()
        tab_container = self.central_widget.findChild(QTabWidget, "tabContainer")
        if tab_container:
            tab_container.setCurrentWidget(self.ui.findChild(QWidget, "tabWelcome"))
        QMessageBox.information(self, "New Project", "New project created.")

    def open_project(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "pAstroCORE Project (*.pastro)")
        if file_path:
            try:
                with open(file_path, "r") as f:
                    self.project_data = json.load(f)
                self.current_project_path = file_path
                self.update_project_explorer()
                QMessageBox.information(self, "Open Project", f"Project {file_path} opened.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open project: {e}")

    def save_project(self):
        if self.current_project_path:
            try:
                with open(self.current_project_path, "w") as f:
                    json.dump(self.project_data, f, indent=4)
                QMessageBox.information(self, "Save Project", "Project saved.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save project: {e}")
        else:
            self.save_project_as()

    def save_project_as(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Project As", "", "pAstroCORE Project (*.pastro)")
        if file_path:
            if not file_path.endswith(".pastro"):
                file_path += ".pastro"
            self.current_project_path = file_path
            self.save_project()

    def import_observation(self):
        QMessageBox.information(self, "Import Observation", "Import observation functionality not implemented yet.")

    def export_observation(self):
        QMessageBox.information(self, "Export Observation", "Export observation functionality not implemented yet.")

    def open_preferences(self):
        QMessageBox.information(self, "Preferences", "Preferences dialog not implemented yet.")
        """
        dialog = ApplicationSettingsDialog(
            sources_dir=self.settings.get("sources_dir", ""),
            telescopes_dir=self.settings.get("telescopes_dir", ""),
            parent=self
        )
        if dialog.exec():
            self.settings = dialog.get_settings()
            self.save_settings()
            QMessageBox.information(self, "Preferences", "Settings saved.")
        """

    def open_telescope_catalog_manager(self):
        telescopes_dir = self.settings.get("telescopes_dir", "")
        if not telescopes_dir or not os.path.isdir(telescopes_dir):
            QMessageBox.warning(self, "Warning", "Please set a valid telescopes directory in Preferences.")
            return
        QMessageBox.information(self, "Telescope Catalog", "Telescope Catalog Manager not implemented yet.")
        """
        telescope = SpaceTelescope(code="ST1", name="Sample Telescope", diameter=2.0)
        dialog = SpaceTelescopeEditorDialog(telescope, parent=self)
        if dialog.exec():
            self.project_data["telescopes"].append(telescope.to_dict())
            self.update_project_explorer()
            QMessageBox.information(self, "Telescope Catalog", "Telescope saved.")
        """

    def open_source_catalog_manager(self):
        QMessageBox.information(self, "Source Catalog Manager", "Source catalog manager not implemented yet.")

    def show_about(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def handle_project_explorer_double_click(self, index):
        item = self.ui.projectExplorer.model().itemFromIndex(index)
        if not item:
            return
        text = item.text()
        if text.startswith("Telescope:"):
            telescope_name = text.split(":", 1)[1].strip()
            for t in self.project_data["telescopes"]:
                if t.get("name") == telescope_name:
                    QMessageBox.information(self, "Edit Telescope", "Telescope Editor not implemented yet.")
                    break
                    """
                    telescope = SpaceTelescope(**t)
                    dialog = SpaceTelescopeEditorDialog(telescope, parent=self)
                    if dialog.exec():
                        self.project_data["telescopes"] = [t for t in self.project_data["telescopes"] if t.get("name") != telescope_name]
                        self.project_data["telescopes"].append(telescope.to_dict())
                        self.update_project_explorer()
                    break
                    """
        elif text.startswith("Frequency:"):
            QMessageBox.information(self, "Edit Frequency", "Frequency editing not fully implemented yet.")

    def update_project_explorer(self):
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Project Explorer"])
        root = model.invisibleRootItem()
        telescopes_item = QStandardItem("Telescopes")
        frequencies_item = QStandardItem("Frequencies")
        sources_item = QStandardItem("Sources")
        root.appendRow(telescopes_item)
        root.appendRow(frequencies_item)
        root.appendRow(sources_item)
        for t in self.project_data["telescopes"]:
            telescope_item = QStandardItem(f"Telescope: {t.get('name', 'Unknown')}")
            telescopes_item.appendRow(telescope_item)
        for f in self.project_data["frequencies"]:
            frequency_item = QStandardItem(f"Frequency: {f.get('name', 'Unknown')}")
            frequencies_item.appendRow(frequency_item)
        project_explorer = self.dock_widget.findChild(QTreeView, "projectExplorer")
        if project_explorer:
            project_explorer.setModel(model)
            project_explorer.expandAll()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PAstroCoreMainWindow()
    window.show()
    sys.exit(app.exec())