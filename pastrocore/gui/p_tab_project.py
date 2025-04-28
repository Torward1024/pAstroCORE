from PySide6.QtWidgets import QWidget, QTableView, QMessageBox, QMenu
from PySide6.QtCore import Signal, Slot, Qt, QSortFilterProxyModel, QRegularExpression, QPoint
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
from pastrocore.gui.ui_tab_project import Ui_ProjectInfoTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
import pastrocore.gui.rc_icons  # Импорт ресурсов

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
        # Инициализация иконок из ресурсов
        self.active_icon = QIcon(":/icons/active_icon.svg")  # Зелёный кружок
        self.inactive_icon = QIcon(":/icons/inactive_icon.svg")  # Лососевый кружок

    def setup_table(self):
        """Set up the observations table with appropriate columns."""
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels([
            "#", " ", "Code", "Type", "Frequencies", "Start Time",
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
        # Optimize table appearance
        self.ui.projectInfoTable.setAlternatingRowColors(True)
        self.ui.projectInfoTable.setSortingEnabled(True)
        self.ui.projectInfoTable.sortByColumn(0, Qt.AscendingOrder)
        self.ui.projectInfoTable.verticalHeader().setVisible(False)
        # Устанавливаем ширину столбца Active для иконок
        self.ui.projectInfoTable.setColumnWidth(1, 30)

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
        finally:
            self.ui.lineEdit.setReadOnly(True)

    @Slot(str)
    def on_search_text_changed(self, text: str):
        """Handle search text change for filtering the table."""
        reg_exp = QRegularExpression(text)
        self.proxy_model.setFilterRegularExpression(reg_exp)

    @Slot()
    def update_tab(self):
        """Update the project info tab with current project data using Manipulator."""
        # Update project name
        project_name_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.project,
            "attributes": {"get_name": None}
        })
        project_name = project_name_response["result"] if project_name_response["status"] and isinstance(project_name_response["result"], str) else "Untitled Project"
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
        current_codes = set()
        for obs in result.values():
            code_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": obs,
                "attributes": {"get_observation_code": None}
            })
            if code_response["status"]:
                current_codes.add(code_response["result"])

        existing_codes = {self.model.item(i, 2).text() for i in range(self.model.rowCount()) if self.model.item(i, 2)}

        # Remove rows for observations that no longer exist
        for i in range(self.model.rowCount() - 1, -1, -1):
            obs_code = self.model.item(i, 2).text()
            if obs_code not in current_codes:
                self.model.removeRow(i)

        # Add or update rows for observations
        idx = 1
        for obs_name, obs in result.items():
            if not isinstance(obs, Observation):
                logger.error(f"Invalid observation type for name '{obs_name}': {type(obs)}")
                continue

            # Fetch observation code
            code_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": obs,
                "attributes": {"get_observation_code": None}
            })
            if not code_response["status"]:
                logger.error(f"Failed to get code for observation with name '{obs_name}': {code_response.get('error', 'Unknown error')}")
                continue
            obs_code = code_response["result"]

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
            is_active = is_active_response["status"] and is_active_response["result"]
            active_item = QStandardItem()
            active_item.setIcon(self.active_icon if is_active else self.inactive_icon)
            active_item.setToolTip("Active" if is_active else "Inactive")

            type_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": obs,
                "attributes": {"get": "observation_type"}
            })
            obs_type = type_response["result"] if type_response["status"] and type_response["result"] in ["VLBI", "SINGLE_DISH"] else "N/A"

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
                if bands_response["status"] and isinstance(bands_response["result"], list):
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
                "attributes": {"get_duration": None}
            })
            duration = str(duration_response["result"]) if duration_response["status"] and duration_response["result"] else "N/A"

            sources_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": obs,
                "attributes": {"get_sources": None}
            })
            sources = str(len(sources_response["result"])) if sources_response["status"] and isinstance(sources_response["result"], list) else "0"

            telescopes_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": obs,
                "attributes": {"get_telescopes": None}
            })
            telescopes = str(len(telescopes_response["result"])) if telescopes_response["status"] and isinstance(telescopes_response["result"], list) else "0"

            scans_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": obs,
                "attributes": {"get_scans": None}
            })
            scans = str(len(scans_response["result"])) if scans_response["status"] and isinstance(scans_response["result"], list) else "0"

            row = [
                QStandardItem(str(idx)),
                active_item,
                QStandardItem(obs_code),
                QStandardItem(obs_type),
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
            idx += 1

        # Adjust column widths
        self.ui.projectInfoTable.resizeColumnsToContents()

    def show_context_menu(self, position: QPoint):
        """Show context menu for the observations table."""
        index = self.ui.projectInfoTable.indexAt(position)
        menu = QMenu(self)
        add_action = menu.addAction(QIcon(":/icons/add_observation_icon.svg"), "Add Observation")

        if index.isValid():
            source_index = self.proxy_model.mapToSource(index)
            obs_code = self.model.item(source_index.row(), 2).text()  # Observation code in third column
            # Проверяем текущее состояние наблюдения
            obs_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.project,
                "attributes": {"get_observation_by_code": obs_code}
            })
            if not obs_response["status"] or not obs_response["result"]:
                logger.error(f"Failed to get observation '{obs_code}': {obs_response.get('error', 'Unknown error')}")
                return
            observation = obs_response["result"]
            
            is_active_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": observation,
                "attributes": {"get": "isactive"}
            })
            is_active = is_active_response["status"] and is_active_response["result"]

            # Добавляем пункты Activate/Deactivate в зависимости от текущего состояния
            if is_active:
                deactivate_action = menu.addAction(QIcon(":/icons/inactive_icon.svg"), "Deactivate")
                deactivate_action.triggered.connect(lambda: self.deactivate_observation(obs_code))
            else:
                activate_action = menu.addAction(QIcon(":/icons/active_icon.svg"), "Activate")
                activate_action.triggered.connect(lambda: self.activate_observation(obs_code))

            remove_action = menu.addAction(QIcon(":/icons/remove_observation_icon.svg"), "Remove Observation")
            edit_action = menu.addAction(QIcon(":/icons/edit_observation_icon.svg"), "Edit Observation")
            remove_action.triggered.connect(lambda: self.remove_observation(obs_code))
            edit_action.triggered.connect(lambda: self.edit_observation(obs_code))

        add_action.triggered.connect(self.add_observation)
        menu.exec(self.ui.projectInfoTable.viewport().mapToGlobal(position))

    @Slot(str)
    def activate_observation(self, obs_code: str):
        """Activate the specified observation."""
        try:
            # Получаем объект наблюдения
            obs_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.project,
                "attributes": {"get_observation_by_code": obs_code}
            })
            if not obs_response["status"] or not obs_response["result"]:
                logger.error(f"Failed to get observation '{obs_code}': {obs_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to activate observation: {obs_response.get('error', 'Unknown error')}")
                return

            observation = obs_response["result"]
            # Активируем наблюдение
            request = {
                "operation": "configure",
                "obj": observation,
                "attributes": {"set": {"params": {"isactive": True}}}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Observation '{obs_code}' activated")
                self.update_tab()  # Обновляем таблицу
                self.project_name_changed.emit(self.ui.lineEdit.text())  # Уведомляем о изменении
            else:
                logger.error(f"Failed to activate observation '{obs_code}': {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to activate observation: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while activating observation '{obs_code}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to activate observation: {str(e)}")

    @Slot(str)
    def deactivate_observation(self, obs_code: str):
        """Deactivate the specified observation."""
        try:
            # Получаем объект наблюдения
            obs_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.project,
                "attributes": {"get_observation_by_code": obs_code}
            })
            if not obs_response["status"] or not obs_response["result"]:
                logger.error(f"Failed to get observation '{obs_code}': {obs_response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to deactivate observation: {obs_response.get('error', 'Unknown error')}")
                return

            observation = obs_response["result"]
            # Деактивируем наблюдение
            request = {
                "operation": "configure",
                "obj": observation,
                "attributes": {"set": {"params": {"isactive": False}}}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Observation '{obs_code}' deactivated")
                self.update_tab()  # Обновляем таблицу
                self.project_name_changed.emit(self.ui.lineEdit.text())  # Уведомляем о изменении
            else:
                logger.error(f"Failed to deactivate observation '{obs_code}': {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to deactivate observation: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while deactivating observation '{obs_code}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to deactivate observation: {str(e)}")

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
        if index.isValid():
            source_index = self.proxy_model.mapToSource(index)
            obs_code = self.model.item(source_index.row(), 2).text()
            self.edit_observation(obs_code)