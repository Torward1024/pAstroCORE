from PySide6.QtWidgets import QWidget, QMessageBox
from PySide6.QtCore import Qt, Signal, Slot, QEvent
from PySide6.QtGui import QStandardItemModel, QStandardItem

from common.utils.logging_setup import logger
from pastrocore.gui.ui_tab_project import Ui_ProjectInfoTab


class ProjectInfoTab(QWidget):
    """Widget for displaying and editing project information."""
    project_name_changed = Signal(str)
    def __init__(self, project: 'ScheduleProject', manipulator: 'ScheduleManipulator', parent=None):
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
        response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.project,
            "attributes": {"get_name": None}
        })
        if response["status"]:
            return response["result"]
        logger.error(f"Failed to get project name: {response.get('error', 'Unknown error')}")
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