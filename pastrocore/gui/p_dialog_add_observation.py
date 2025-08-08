from PySide6.QtWidgets import QDialog, QMessageBox
from PySide6.QtCore import Signal, Slot
from pastrocore.gui.ui_dialog_add_observation import Ui_AddObservationDialog
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from common.utils.logging_setup import logger

class AddObservationDialog(QDialog):
    """Dialog for adding a new observation with code and type."""
    observation_added = Signal(str, str)

    def __init__(self, manipulator: ScheduleManipulator, parent=None):
        super().__init__(parent)
        self.ui = Ui_AddObservationDialog()
        self.ui.setupUi(self)
        self.project = manipulator.get_managing_object()
        self.manipulator = manipulator
        self.setup_dialog()
        self.setup_connections()

    def setup_dialog(self):
        """Initialize the dialog with default settings."""
        self.setWindowTitle("Add Observation")
        
        self.ui.combo_obs_type.addItems(["VLBI", "SINGLE_DISH"])
        self.ui.combo_obs_type.setCurrentText("VLBI")
        self.ui.obs_code.setText("OBS_DEFAULT")

        logger.info("AddObservationDialog initialized")

    def setup_connections(self):
        """Connect UI signals to slots."""
        self.ui.okButton.clicked.connect(self.accept)
        self.ui.closeButton.clicked.connect(self.reject)

        self.ui.obs_code.textChanged.connect(self.obs_code_changed)
        self.ui.combo_obs_type.currentTextChanged.connect(self.obs_type_changed)
        logger.debug("AddObservationDialog connections set up")

    @Slot(str)
    def obs_code_changed(self, text: str):
        """Handle changes to observation code input."""
        logger.debug(f"Observation code input changed to: {text}")

    @Slot(str)
    def obs_type_changed(self, text: str):
        """Handle changes to observation type selection."""
        logger.debug(f"Observation type changed to: {text}")

    def accept(self):
        """Handle OK button click to add observation."""
        obs_code = self.ui.obs_code.text().strip()
        obs_type = self.ui.combo_obs_type.currentText()

        if not obs_code:
            QMessageBox.critical(self, "Error", "Observation code cannot be empty.")
            logger.error("Attempted to add observation with empty code")
            return

        obs_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.project,
            "attributes": {"get_observation_by_code": obs_code}
        })
        if obs_response["status"] and obs_response["result"] is not None:
            QMessageBox.critical(self, "Error", f"Observation code '{obs_code}' already exists.")
            logger.error(f"Observation code '{obs_code}' already exists")
            return
        else:
            logger.debug(f"Observation code '{obs_code}' is unique")

        try:
            request = {
                "operation": "configure",
                "obj": self.project,
                "attributes": {
                    "create_item": {
                        "item_code": obs_code,
                        "isactive": True,
                        "observation_type": obs_type
                    }
                }
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Observation '{obs_code}' (type: {obs_type}) added to project '{self.project.get_name()}'")
                self.observation_added.emit(obs_code, obs_type)
                super().accept()
            else:
                logger.error(f"Failed to add observation '{obs_code}': {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to add observation: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while adding observation '{obs_code}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to add observation: {str(e)}")

    def reject(self):
        """Handle Cancel button click."""
        logger.info("Add observation cancelled")
        super().reject()