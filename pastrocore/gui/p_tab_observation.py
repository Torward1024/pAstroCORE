from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

class ObservationTab(QWidget):
    """Widget for editing observation details."""
    observation_updated = Signal()

    def __init__(self, observation: 'Observation', manipulator: 'ScheduleManipulator', parent=None):
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