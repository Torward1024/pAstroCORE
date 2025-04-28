from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QTableView, QMessageBox, QMenu
from PySide6.QtCore import Signal, Slot, Qt, QSortFilterProxyModel, QRegularExpression, QPoint
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
import pastrocore.gui.rc_icons
import uuid

class TelescopesTab(QWidget):
    data_updated = Signal()

    def __init__(self, observation: Observation, project: ScheduleProject, manipulator: ScheduleManipulator, parent=None):
        super().__init__(parent)
        self.observation = observation
        self.project = project
        self.manipulator = manipulator
        
        # Настройка UI
        self.layout = QVBoxLayout(self)
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search telescopes...")
        self.table = QTableView()
        self.layout.addWidget(self.search_bar)
        self.layout.addWidget(self.table)
        self.setLayout(self.layout)

        # Настройка таблицы
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Telescope Name"])
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterKeyColumn(-1)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.table.setModel(self.proxy_model)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.verticalHeader().setVisible(False)

        # Подключение сигналов
        self.search_bar.textChanged.connect(self.on_search_changed)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

    @Slot(str)
    def on_search_changed(self, text: str):
        """Handle search text change."""
        reg_exp = QRegularExpression(text)
        self.proxy_model.setFilterRegularExpression(reg_exp)

    def show_context_menu(self, position: QPoint):
        """Show context menu for the telescopes table."""
        index = self.table.indexAt(position)
        menu = QMenu(self)
        add_action = menu.addAction(QIcon(":/icons/add_icon.svg"), "Add Telescope")
        add_action.triggered.connect(self.add_telescope)
        
        if index.isValid():
            source_index = self.proxy_model.mapToSource(index)
            telescope_name = self.model.item(source_index.row(), 0).text()
            remove_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Remove Telescope")
            edit_action = menu.addAction(QIcon(":/icons/edit_icon.svg"), "Edit Telescope")
            remove_action.triggered.connect(lambda: self.remove_telescope(telescope_name))
            edit_action.triggered.connect(lambda: self.edit_telescope(telescope_name))
        
        menu.exec(self.table.viewport().mapToGlobal(position))

    @Slot()
    def add_telescope(self):
        """Add a new telescope to the observation."""
        try:
            telescope_name = f"telescope_{uuid.uuid4().hex[:8]}"
            request = {
                "operation": "configure",
                "obj": self.observation.get_telescopes(),
                "attributes": {"add_item": {"name": telescope_name}}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Added telescope '{telescope_name}' to observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit()
            else:
                logger.error(f"Failed to add telescope: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to add telescope: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while adding telescope: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to add telescope: {str(e)}")

    @Slot(str)
    def remove_telescope(self, telescope_name: str):
        """Remove a telescope from the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_telescopes(),
                "attributes": {"remove_item": telescope_name}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Removed telescope '{telescope_name}' from observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit()
            else:
                logger.error(f"Failed to remove telescope: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to remove telescope: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while removing telescope: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to remove telescope: {str(e)}")

    @Slot(str)
    def edit_telescope(self, telescope_name: str):
        """Edit an existing telescope."""
        if self.parent().parent_widget:
            logger.info(f"Requesting edit for telescope '{telescope_name}' in observation '{self.observation.code}'")
            self.parent().parent_widget.edit_telescope(self.observation, telescope_name)
        else:
            logger.warning("No parent widget to handle telescope edit")
            QMessageBox.warning(self, "Warning", "Editing telescope is not implemented yet.")

    @Slot()
    def update(self):
        """Update the telescopes table."""
        self.model.removeRows(0, self.model.rowCount())
        telescopes_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_telescopes": None}
        })
        if telescopes_response["status"]:
            telescopes = telescopes_response["result"].get_items() if hasattr(telescopes_response["result"], 'get_items') else []
            for telescope in telescopes:
                item = QStandardItem(str(telescope.name))
                item.setEditable(False)
                self.model.appendRow([item])
        self.table.resizeColumnsToContents()