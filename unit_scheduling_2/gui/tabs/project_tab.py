# /gui/tabs/project_tab.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem
from PySide6.QtCore import Qt
from unit_scheduling.super.schedule_manipulator import ScheduleManipulator
from common.utils.logging_setup import logger
from typing import Optional, Dict, Any

class ProjectTab(QWidget):
    """Tab displaying a non-editable table of Observations in the Project.

    Attributes:
        manipulator: The ScheduleManipulator instance managing the project.
        parent: The MainWindow instance.
        table: QTableWidget displaying observation data.
    """
    def __init__(self, manipulator: ScheduleManipulator, parent=None):
        """Initialize the ProjectTab."""
        super().__init__(parent)
        self.manipulator = manipulator
        self.parent = parent
        self._setup_ui()
        logger.info("Initialized ProjectTab")

    def _setup_ui(self) -> None:
        """Set up the UI with a non-editable table."""
        self.layout = QVBoxLayout(self)
        self.table = QTableWidget(self)
        self.table.setColumnCount(3)  # Например: Code, Active, Telescope Count
        self.table.setHorizontalHeaderLabels(["Observation Code", "Active", "Telescope Count"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.layout.addWidget(self.table)
        self._populate_table()

    def _populate_table(self) -> None:
        """Populate the table with data from the Project."""
        project = self.manipulator.get_managing_object()
        if project is None:
            logger.error("No managing object in manipulator for ProjectTab")
            self.table.setRowCount(0)
            return
        observations = project.get_items()
        self.table.setRowCount(len(observations))

        for row, obs in enumerate(observations):
            self.table.setItem(row, 0, QTableWidgetItem(obs.get_observation_code()))
            self.table.setItem(row, 1, QTableWidgetItem(str(obs.get_isactive())))
            self.table.setItem(row, 2, QTableWidgetItem(str(len(obs.get_telescopes()))))

        self.table.resizeColumnsToContents()

    def refresh(self, selected_item: Optional[Dict[str, Any]]) -> None:
        """Refresh the table content."""
        self._populate_table()
        logger.debug("Refreshed ProjectTab table")