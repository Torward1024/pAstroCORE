from PySide6.QtWidgets import QWidget, QTableView, QMessageBox, QMenu
from PySide6.QtCore import Signal, Slot, Qt, QSortFilterProxyModel, QRegularExpression, QPoint
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
from pastrocore.gui.ui_tab_project import Ui_ProjectInfoTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger

class ProjectInfoTab(QWidget):
    """Widget for displaying and editing project information in a tab."""
    project_name_changed = Signal(str)

    def __init__(self, project: ScheduleProject, manipulator: ScheduleManipulator, parent=None):
        super().__init__(parent)
        self.ui = Ui_ProjectInfoTab()
        self.ui.setupUi(self)
        self.project = project
        self.manipulator = manipulator
        self.parent_widget = parent  # Reference to PAstroCoreMainWindow
        self.setup_table()
        self.setup_connections()
        self.update_tab()

    def setup_table(self):
        """Set up the observations table with appropriate columns."""
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels([
            "№", "Active", "Code", "Frequencies", "Start Time",
            "Duration", "Sources", "Telescopes", "Scans"
        ])
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterKeyColumn(-1)  # Filter across all columns
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.ui.projectInfoTable.setModel(self.proxy_model)
        self.ui.projectInfoTable.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.projectInfoTable.customContextMenuRequested.connect(self.show_context_menu)
        # Disable editing in lineEdit by default
        self.ui.lineEdit.setReadOnly(True)

    def setup_connections(self):
        """Connect signals to slots."""
        self.ui.lineEdit.editingFinished.connect(self.on_project_name_confirmed)
        self.ui.lineEdit_2.textChanged.connect(self.on_search_text_changed)
        self.ui.projectInfoTable.doubleClicked.connect(self.on_table_double_click)
        self.ui.lineEdit.mouseDoubleClickEvent = self.on_line_edit_double_click

    def on_line_edit_double_click(self, event):
        """Enable editing of project name on double-click."""
        self.ui.lineEdit.setReadOnly(False)
        self.ui.lineEdit.setFocus()
        self.ui.lineEdit.selectAll()
        event.accept()

    @Slot()
    def on_project_name_confirmed(self):
        """Handle project name confirmation after editing."""
        if self.ui.lineEdit.isReadOnly():
            return
        new_name = self.ui.lineEdit.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Warning", "Project name cannot be empty.")
            self.update_tab()  # Revert to previous name
            return
        try:
            request = {
                "operation": "configure",
                "obj": self.project,
                "attributes": {"set_name": new_name}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Project name changed to '{new_name}'")
                self.project_name_changed.emit(new_name)
            else:
                logger.error(f"Failed to change project name: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to change project name: {response.get('error', 'Unknown error')}")
                self.update_tab()  # Revert to previous name
        except Exception as e:
            logger.error(f"Exception while changing project name: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to change project name: {str(e)}")
            self.update_tab()  # Revert to previous name
        finally:
            self.ui.lineEdit.setReadOnly(True)

    @Slot(str)
    def on_search_text_changed(self, text: str):
        """Handle search text change for filtering the table."""
        reg_exp = QRegularExpression(text, Qt.CaseInsensitive, QRegularExpression.Wildcard)
        self.proxy_model.setFilterRegExp(reg_exp)

    @Slot()
    def update_tab(self):
        """Update the project info tab with current project data using Manipulator."""
        # Update project name
        project_name_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.project,
            "attributes": {"get_name": None}
        })
        project_name = project_name_response["result"] if project_name_response["status"] else "Untitled Project"
        self.ui.lineEdit.setText(project_name)

        # Get current observations
        observations_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.project,
            "attributes": {"get_items": None}
        })
        if not observations_response["status"]:
            logger.error(f"Failed to inspect observations: {observations_response.get('error', 'Unknown error')}")
            return

        result = observations_response["result"]
        if not isinstance(result, dict):
            logger.error(f"Expected dict for observations, got {type(result)}: {result}")
            return

        # Create a set of current observation codes
        current_codes = set(result.keys())
        existing_codes = {self.model.item(i, 2).text() for i in range(self.model.rowCount())}

        # Remove rows for observations that no longer exist
        for i in range(self.model.rowCount() - 1, -1, -1):
            obs_code = self.model.item(i, 2).text()
            if obs_code not in current_codes:
                self.model.removeRow(i)

        # Add or update rows for observations
        for idx, (obs_code, obs) in enumerate(result.items(), 1):
            if isinstance(obs, Observation):
                # Check if row exists
                row_idx = None
                for i in range(self.model.rowCount()):
                    if self.model.item(i, 2).text() == obs_code:
                        row_idx = i
                        break

                # Fetch observation data via Manipulator
                is_active_response = self.manipulator.process_request({
                    "operation": "inspect",
                    "obj": obs,
                    "attributes": {"get": "isactive"}
                })
                active = "Active" if is_active_response["result"] else "Inactive"

                frequencies_response = self.manipulator.process_request({
                    "operation": "inspect",
                    "obj": obs,
                    "attributes": {"get_frequencies": None}
                })
                freqs = "N/A"
                if frequencies_response["status"] and frequencies_response["result"]:
                    bands_response = self.manipulator.process_request({
                        "operation": "inspect",
                        "obj": frequencies_response["result"],
                        "attributes": {"get_bands": None}
                    })
                    if bands_response["status"] and bands_response["result"]:
                        freqs = ", ".join([f"{f} Hz" for f in bands_response["result"]])

                start_time_response = self.manipulator.process_request({
                    "operation": "inspect",
                    "obj": obs,
                    "attributes": {"get_start_datetime": None}
                })
                start_time = str(start_time_response["result"]) if start_time_response["status"] and start_time_response["result"] else "N/A"

                duration_response = self.manipulator.process_request({
                    "operation": "inspect",
                    "obj": obs,
                    "attributes": {"get_start_datetime": None}
                })
                duration = str(duration_response["result"]) if duration_response["status"] and duration_response["result"] else "N/A"

                sources_response = self.manipulator.process_request({
                    "operation": "inspect",
                    "obj": obs,
                    "attributes": {"get_sources": None}
                })
                sources = str(len(sources_response["result"])) if sources_response["status"] and sources_response["result"] else "0"

                telescopes_response = self.manipulator.process_request({
                    "operation": "inspect",
                    "obj": obs,
                    "attributes": {"get_telescopes": None}
                })
                telescopes = str(len(telescopes_response["result"])) if telescopes_response["status"] and telescopes_response["result"] else "0"

                scans_response = self.manipulator.process_request({
                    "operation": "inspect",
                    "obj": obs,
                    "attributes": {"get_scans": None}
                })
                scans = str(len(scans_response["result"])) if scans_response["status"] and scans_response["result"] else "0"

                row = [
                    QStandardItem(str(idx)),
                    QStandardItem(active),
                    QStandardItem(obs_code),
                    QStandardItem(freqs),
                    QStandardItem(start_time),
                    QStandardItem(duration),
                    QStandardItem(sources),
                    QStandardItem(telescopes),
                    QStandardItem(scans)
                ]
                for item in row:
                    item.setEditable(False)

                if row_idx is None:
                    self.model.appendRow(row)
                else:
                    for col, item in enumerate(row):
                        self.model.setItem(row_idx, col, item)
            else:
                logger.error(f"Invalid observation type for code '{obs_code}': {type(obs)}")

        # Adjust column widths
        for i in range(self.model.columnCount()):
            self.ui.projectInfoTable.setColumnWidth(i, 120)

    def show_context_menu(self, position: QPoint):
        """Show context menu for the observations table."""
        index = self.ui.projectInfoTable.indexAt(position)
        if not index.isValid():
            return

        source_index = self.proxy_model.mapToSource(index)
        obs_code = self.model.item(source_index.row(), 2).text()  # Observation code in third column

        menu = QMenu(self)
        add_action = menu.addAction(QIcon(":/icons/add_observation_icon.svg"), "Add Observation")
        remove_action = menu.addAction(QIcon(":/icons/remove_observation_icon.svg"), "Remove Observation")
        edit_action = menu.addAction(QIcon(":/icons/edit_observation_icon.svg"), "Edit Observation")

        add_action.triggered.connect(self.add_observation)
        remove_action.triggered.connect(lambda: self.remove_observation(obs_code))
        edit_action.triggered.connect(lambda: self.edit_observation(obs_code))

        menu.exec(self.ui.projectInfoTable.viewport().mapToGlobal(position))

    @Slot()
    def add_observation(self):
        """Add a new observation to the project."""
        if self.parent_widget:
            self.parent_widget.add_observation()

    @Slot(str)
    def remove_observation(self, obs_code: str):
        """Remove an observation from the project."""
        if self.parent_widget:
            self.parent_widget.remove_observation(obs_code)

    @Slot(str)
    def edit_observation(self, obs_code: str):
        """Edit an observation."""
        if self.parent_widget:
            self.parent_widget.edit_observation(obs_code)

    @Slot()
    def on_table_double_click(self, index):
        """Handle double-click on table to edit observation."""
        source_index = self.proxy_model.mapToSource(index)
        obs_code = self.model.item(source_index.row(), 2).text()
        self.edit_observation(obs_code)