# /unit_scheduling_2/gui/dialogs.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from unit_scheduling_2.super.schedule_manipulator import ScheduleManipulator
from common.utils.logging_setup import logger

class AboutDialog(QDialog):
    """About dialog for pAstroCORE.

    Displays application information, version, and credits.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About pAstroCORE")
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        layout.addWidget(QLabel("pAstroCORE\nVersion: 1.0.0\nA flexible tool for VLBI scheduling and visualization."))
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        self.setLayout(layout)

class CatalogManagerDialog(QDialog):
    """Dialog for managing source and telescope catalogs.

    Allows browsing and editing of CatalogManager data.

    Args:
        manipulator (ScheduleManipulator): Manipulator for accessing catalog data.
        parent: Parent widget.
    """
    def __init__(self, manipulator: ScheduleManipulator, parent=None):
        super().__init__(parent)
        self._manipulator = manipulator
        self.setWindowTitle("Catalog Manager")
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Catalog Manager (Sources and Telescopes)"))
        # Placeholder for catalog browsing/editing UI
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        self.setLayout(layout)