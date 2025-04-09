# /gui/main_window.py
from PySide6.QtWidgets import QMainWindow, QDockWidget, QTabWidget
from PySide6.QtCore import Qt
from common.utils.logging_setup import logger
from unit_scheduling.super.schedule_manipulator import ScheduleManipulator
from unit_scheduling.super.schedule_project import ScheduleProject
from unit_scheduling.gui.project_explorer import ProjectExplorer
from unit_scheduling.gui.tabs.project_tab import ProjectTab
from typing import Optional

class MainWindow(QMainWindow):
    """Main GUI window for pAstroCORE application.

    Combines a dockable Project Explorer on the left with tabbed interfaces for project data on the right.
    Manages two-way communication between UI elements and underlying astronomical scheduling objects via Manipulator.

    Attributes:
        manipulator: The ScheduleManipulator instance managing Project and super-class operations.
        project_explorer: The ProjectExplorer widget displaying the project hierarchy.
        tab_widget: The QTabWidget containing project-related tabs.
    """
    def __init__(self, project: Optional[ScheduleProject] = None):
        """Initialize the MainWindow."""
        super().__init__()
        self.manipulator = ScheduleManipulator(project if project else ScheduleProject(name="DefaultProject"))
        self.setWindowTitle("pAstroCORE")
        self.resize(1200, 800)
        self._setup_ui()
        logger.info("Initialized MainWindow")

    def _setup_ui(self) -> None:
        """Set up the UI components: Project Explorer and project tabs."""
        # Project Explorer (left dock)
        self.project_explorer = ProjectExplorer(self.manipulator, self)
        dock = QDockWidget("Project Explorer", self)
        dock.setWidget(self.project_explorer)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

        # Project tabs (right)
        self.tab_widget = QTabWidget(self)
        self.tab_widget.addTab(ProjectTab(self.manipulator, self), "Project")
        # Другие вкладки (Inspector, Calculator, Visualizer) можно добавить позже
        self.setCentralWidget(self.tab_widget)

        # Connect updates
        self.project_explorer.item_changed.connect(self._on_item_changed)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

    def _on_item_changed(self, item_data: dict) -> None:
        """Handle changes in Project Explorer items and propagate to Manipulator."""
        request = {"operation": "configure", "attributes": item_data}
        self.manipulator.process_request(request)
        self._update_tabs()

    def _on_tab_changed(self, index: int) -> None:
        """Refresh the active tab when switched."""
        current_tab = self.tab_widget.widget(index)
        current_tab.refresh(self.project_explorer.get_selected_item())

    def _update_tabs(self) -> None:
        """Update all tabs based on current project state."""
        selected_item = self.project_explorer.get_selected_item()
        for i in range(self.tab_widget.count()):
            self.tab_widget.widget(i).refresh(selected_item)