# /unit_scheduling_2/gui/main_window.py
from PySide6.QtWidgets import (
    QMainWindow, QDockWidget, QTreeView, QTabWidget, QStatusBar, QProgressBar,
    QMenuBar, QMessageBox, QApplication
)

from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex, Signal, QObject
from PySide6.QtGui import QAction
from typing import Dict, Any, Optional
from unit_scheduling_2.super.schedule_manipulator import ScheduleManipulator
from unit_scheduling_2.super.schedule_project import ScheduleProject
from common.utils.logging_setup import logger

class ProjectTreeModel(QAbstractItemModel):
    """Tree model for displaying ScheduleProject structure in QTreeView.

    Represents the hierarchical structure of a ScheduleProject, including observations,
    telescopes, sources, scans, and frequencies.

    Args:
        project (ScheduleProject): The project to display.
        manipulator (ScheduleManipulator): Manipulator for accessing project data.
    """
    def __init__(self, project: ScheduleProject, manipulator: ScheduleManipulator):
        super().__init__()
        self._project = project
        self._manipulator = manipulator
        self._root_items = self._build_tree()

    def _build_tree(self) -> list:
        """Build the tree structure from the project."""
        items = [{"type": "Project", "name": self._project.get_name(), "object": self._project, "children": []}]
        request = {"operation": "configure",
                   "attributes": {
                       "get_observations": None
                       }
                    }
        observations = self._manipulator.process_request(self._project, request)["result"]
        for obs in observations:
            obs_item = {"type": "Observation", "name": obs.get_observation_code(), "object": obs, "children": []}
            # Add telescopes, sources, scans, frequencies
            for entity_type in ["telescopes", "sources", "scans", "frequencies"]:
                entities = self._manipulator.execute(obs, {"get": entity_type})["result"]
                if isinstance(entities, list):
                    for entity in entities:
                        obs_item["children"].append({
                            "type": entity_type.capitalize()[:-1],  # e.g., Telescope, Source
                            "name": entity.get("name") if entity_type != "scans" else entity.get("start").isot,
                            "object": entity,
                            "children": []
                        })
            items[0]["children"].append(obs_item)
        return items

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        """Return the index for the item at (row, column) under parent."""
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        parent_item = self._get_item(parent)
        return self.createIndex(row, column, parent_item["children"][row])

    def parent(self, index: QModelIndex) -> QModelIndex:
        """Return the parent index for the given index."""
        if not index.isValid():
            return QModelIndex()
        item = index.internalPointer()
        parent_item = self._find_parent(item)
        if parent_item is None:
            return QModelIndex()
        row = self._find_row(parent_item)
        return self.createIndex(row, 0, parent_item)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of rows under parent."""
        parent_item = self._get_item(parent)
        return len(parent_item["children"])

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of columns."""
        return 1

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Return data for the given index and role."""
        if not index.isValid():
            return None
        item = index.internalPointer()
        if role == Qt.DisplayRole:
            return f"{item['type']}: {item['name']}"
        return None

    def _get_item(self, index: QModelIndex) -> dict:
        """Get the item dictionary for the given index."""
        if not index.isValid():
            return self._root_items[0]
        return index.internalPointer()

    def _find_parent(self, item: dict) -> Optional[dict]:
        """Find the parent item in the tree."""
        def search(items):
            for parent in items:
                if item in parent["children"]:
                    return parent
                found = search(parent["children"])
                if found:
                    return found
            return None
        return search(self._root_items)

    def _find_row(self, item: dict) -> int:
        """Find the row of the item in its parent's children."""
        parent = self._find_parent(item)
        if parent:
            return parent["children"].index(item)
        return 0

class ProgressHandler(QObject):
    """Handler for progress updates."""
    progress_updated = Signal(int)
    message_updated = Signal(str)

    def __init__(self):
        super().__init__()

class MainWindow(QMainWindow):
    """Main application window for pAstroCORE.

    Provides a GUI for managing ScheduleProject, including a Project Explorer (TreeView),
    tabbed interface for editing/viewing objects, and a status bar with progress indicator.

    Args:
        manipulator (ScheduleManipulator): Manipulator for interacting with project data.
    """
    def __init__(self, manipulator: ScheduleManipulator):
        super().__init__()
        self._manipulator = manipulator
        self._project = manipulator._managing_object
        self._init_ui()
        self._progress_handler = ProgressHandler()
        self._progress_handler.progress_updated.connect(self._update_progress)
        self._progress_handler.message_updated.connect(self._status_bar.showMessage)

    def _init_ui(self):
        """Initialize the UI components."""
        self.setWindowTitle("pAstroCORE")
        self.resize(1200, 800)

        # Main Menu
        self._create_menu()

        # Project Explorer
        self._project_explorer = QDockWidget("Project Explorer", self)
        self._tree_view = QTreeView()
        self._tree_view.setHeaderHidden(True)
        self._project_explorer.setWidget(self._tree_view)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._project_explorer)
        self._update_project_tree()

        # Tab Container
        self._tab_widget = QTabWidget()
        self._tab_widget.setTabsClosable(True)
        self._tab_widget.tabCloseRequested.connect(self._close_tab)
        self.setCentralWidget(self._tab_widget)
        self._tree_view.clicked.connect(self._on_tree_item_clicked)

        # Status Bar
        self._status_bar = QStatusBar()
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumWidth(200)
        self._progress_bar.setVisible(False)
        self._status_bar.addPermanentWidget(self._progress_bar)
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready")

    def _create_menu(self):
        """Create the main menu."""
        menu_bar = self.menuBar()
        
        # File Menu
        file_menu = menu_bar.addMenu("&File")
        new_project_action = QAction("&New Project", self)
        new_project_action.triggered.connect(self._new_project)
        file_menu.addAction(new_project_action)
        save_action = QAction("&Save Project", self)
        save_action.triggered.connect(self._save_project)
        file_menu.addAction(save_action)
        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Options Menu
        options_menu = menu_bar.addMenu("&Options")
        catalog_action = QAction("&Catalog Manager", self)
        catalog_action.triggered.connect(self._open_catalog_manager)
        options_menu.addAction(catalog_action)

        # Help Menu
        help_menu = menu_bar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _update_project_tree(self):
        """Update the Project Explorer tree view."""
        if self._project:
            model = ProjectTreeModel(self._project, self._manipulator)
            self._tree_view.setModel(model)
            self._tree_view.expandAll()

    def _on_tree_item_clicked(self, index: QModelIndex):
        """Handle clicks on items in the Project Explorer."""
        item = index.internalPointer()
        obj = item["object"]
        obj_type = item["type"]
        tab_title = f"{obj_type}: {item['name']}"
        
        # Check if tab already exists
        for i in range(self._tab_widget.count()):
            if self._tab_widget.tabText(i) == tab_title:
                self._tab_widget.setCurrentIndex(i)
                return
        
        # Create new tab with appropriate widget
        from .editors import get_editor_widget
        widget = get_editor_widget(obj, self._manipulator)
        if widget:
            self._tab_widget.addTab(widget, tab_title)
            self._tab_widget.setCurrentWidget(widget)
            logger.info(f"Opened tab for {obj_type}: {item['name']}")

    def _close_tab(self, index: int):
        """Close a tab by index."""
        self._tab_widget.removeTab(index)
        logger.info(f"Closed tab at index {index}")

    def _new_project(self):
        """Create a new project."""
        self._project = ScheduleProject(name="NewProject")
        self._manipulator.managing_object = self._project
        self._update_project_tree()
        self._status_bar.showMessage("Created new project")
        logger.info("Created new ScheduleProject")
    
    def _update_progress(self, value: int):
        """Update the progress bar."""
        self._progress_bar.setValue(value)
        self._progress_bar.setVisible(value > 0 and value < 100)

    def _save_project(self):
        """Save the current project with progress feedback."""
        try:
            project_dict = self._manipulator.execute(self._project, {"get": "project"})["result"]
            self._progress_handler.progress_updated.emit(50)
            self._progress_handler.message_updated.emit("Saving project...")
            # Placeholder: Save to JSON file
            import json
            with open("project.json", "w") as f:
                json.dump(project_dict, f, indent=2)
            self._progress_handler.progress_updated.emit(100)
            self._progress_handler.message_updated.emit("Project saved")
            logger.info(f"Saved project '{self._project.get_name()}' to project.json")
        except Exception as e:
            self._progress_handler.progress_updated.emit(0)
            QMessageBox.critical(self, "Error", f"Failed to save project: {str(e)}")
            logger.error(f"Failed to save project: {str(e)}")

    def _open_catalog_manager(self):
        """Open the catalog manager dialog."""
        from .dialogs import CatalogManagerDialog
        dialog = CatalogManagerDialog(self._manipulator, self)
        dialog.exec()
        logger.info("Opened Catalog Manager dialog")

    def _show_about_dialog(self):
        """Show the About dialog."""
        from .dialogs import AboutDialog
        dialog = AboutDialog(self)
        dialog.exec()
        logger.info("Opened About dialog")