# /unit_scheduling_2/gui/editors.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton
from unit_scheduling_2.super.schedule_manipulator import ScheduleManipulator
from unit_scheduling_2.base.observation import Observation
from unit_scheduling_2.base.telescope import Telescope
from common.utils.logging_setup import logger

def get_editor_widget(obj: object, manipulator: ScheduleManipulator) -> QWidget:
    """Return the appropriate editor widget for the given object.

    Args:
        obj: The object to edit/view (e.g., Observation, Telescope).
        manipulator (ScheduleManipulator): Manipulator for interacting with the object.

    Returns:
        QWidget: The editor widget for the object, or None if unsupported.
    """
    if isinstance(obj, Observation):
        return ObservationEditor(obj, manipulator)
    # Add other types (Telescope, Source, Scan, etc.) as needed
    logger.warning(f"No editor available for object type: {type(obj).__name__}")
    return None

class TelescopeEditor(QWidget):
    """Editor widget for Telescope objects.

    Displays and allows editing of Telescope properties, such as name and coordinates.

    Args:
        telescope (Telescope): The Telescope object to edit.
        manipulator (ScheduleManipulator): Manipulator for applying changes.
    """
    def __init__(self, telescope: Telescope, manipulator: ScheduleManipulator):
        super().__init__()
        self._telescope = telescope
        self._manipulator = manipulator
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        
        # Name
        self._name_edit = QLineEdit(self._telescope.get_code())
        layout.addWidget(QLabel("Telescope Code:"))
        layout.addWidget(self._name_edit)

        # Coordinates
        x, y, z = self._telescope.get_coordinates()
        self._x_edit = QLineEdit(str(x))
        self._y_edit = QLineEdit(str(y))
        self._z_edit = QLineEdit(str(z))
        layout.addWidget(QLabel("Coordinates (X, Y, Z):"))
        layout.addWidget(self._x_edit)
        layout.addWidget(self._y_edit)
        layout.addWidget(self._z_edit)

        # Save Button
        save_button = QPushButton("Save")
        save_button.clicked.connect(self._save)
        layout.addWidget(save_button)

        layout.addStretch()
        self.setLayout(layout)

    def _save(self):
        """Save changes to the Telescope object."""
        try:
            new_name = self._name_edit.text()
            new_coords = {
                "x": float(self._x_edit.text()),
                "y": float(self._y_edit.text()),
                "z": float(self._z_edit.text())
            }
            self._manipulator.execute(
                self._telescope,
                {"configure": {
                    "set_code": new_name,
                    "set_coordinates": new_coords
                }}
            )
            logger.info(f"Saved Telescope: code='{new_name}'")
        except Exception as e:
            logger.error(f"Failed to save Telescope: {str(e)}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")

class ObservationEditor(QWidget):
    """Editor widget for Observation objects.

    Displays and allows editing of Observation properties, such as name and active status.

    Args:
        observation (Observation): The Observation object to edit.
        manipulator (ScheduleManipulator): Manipulator for applying changes.
    """
    def __init__(self, observation: Observation, manipulator: ScheduleManipulator):
        super().__init__()
        self._observation = observation
        self._manipulator = manipulator
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()

        # Name
        self._name_edit = QLineEdit(self._observation.get_observation_code())
        layout.addWidget(QLabel("Observation Code:"))
        layout.addWidget(self._name_edit)

        # Save Button
        save_button = QPushButton("Save")
        save_button.clicked.connect(self._save)
        layout.addWidget(save_button)

        layout.addStretch()
        self.setLayout(layout)

    def _save(self):
        """Save changes to the Observation object."""
        try:
            new_name = self._name_edit.text()
            self._manipulator.execute(
                self._observation,
                {"configure": {"set_observation_code": new_name}}
            )
            logger.info(f"Saved Observation: code='{new_name}'")
        except Exception as e:
            logger.error(f"Failed to save Observation: {str(e)}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")