from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QTableView, QMessageBox, QMenu
from PySide6.QtCore import Signal, Slot, Qt, QSortFilterProxyModel, QRegularExpression, QPoint
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
import pastrocore.gui.rc_icons
import uuid

class SourcesTab(QWidget):
    data_updated = Signal()

    def __init__(self, observation: Observation, project: ScheduleProject, manipulator: ScheduleManipulator, parent=None):
        super().__init__(parent)
        self.observation = observation
        self.project = project
        self.manipulator = manipulator
        
        # Настройка UI
        self.layout = QVBoxLayout(self)
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search sources...")
        self.table = QTableView()
        self.layout.addWidget(self.search_bar)
        self.layout.addWidget(self.table)
        self.setLayout(self.layout)

        # Настройка таблицы
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Source Name"])
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
        """Show context menu for the sources table."""
        index = self.table.indexAt(position)
        menu = QMenu(self)
        add_action = menu.addAction(QIcon(":/icons/add_icon.svg"), "Add Source")
        add_action.triggered.connect(self.add_source)
        
        if index.isValid():
            source_index = self.proxy_model.mapToSource(index)
            source_name = self.model.item(source_index.row(), 0).text()
            remove_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Remove Source")
            edit_action = menu.addAction(QIcon(":/icons/edit_icon.svg"), "Edit Source")
            remove_action.triggered.connect(lambda: self.remove_source(source_name))
            edit_action.triggered.connect(lambda: self.edit_source(source_name))
        
        menu.exec(self.table.viewport().mapToGlobal(position))

    @Slot()
    def add_source(self):
        """Add a new source to the observation."""
        try:
            source_name = f"source_{uuid.uuid4().hex[:8]}"
            request = {
                "operation": "configure",
                "obj": self.observation.get_sources(),
                "attributes": {"add_item": {"name": source_name}}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Added source '{source_name}' to observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit()
            else:
                logger.error(f"Failed to add source: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to add source: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while adding source: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to add source: {str(e)}")

    @Slot(str)
    def remove_source(self, source_name: str):
        """Remove a source from the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_sources(),
                "attributes": {"remove_item": source_name}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Removed source '{source_name}' from observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit()
            else:
                logger.error(f"Failed to remove source: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to remove source: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while removing source: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to remove source: {str(e)}")

    @Slot(str)
    def edit_source(self, source_name: str):
        """Edit an existing source."""
        if self.parent().parent_widget:
            logger.info(f"Requesting edit for source '{source_name}' in observation '{self.observation.code}'")
            self.parent().parent_widget.edit_source(self.observation, source_name)
        else:
            logger.warning("No parent widget to handle source edit")
            QMessageBox.warning(self, "Warning", "Editing source is not implemented yet.")

    @Slot()
    def update(self):
        """Update the sources table."""
        self.model.removeRows(0, self.model.rowCount())
        sources_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_sources": None}
        })
        if sources_response["status"]:
            sources = sources_response["result"].get_items() if hasattr(sources_response["result"], 'get_items') else []
            for source in sources:
                item = QStandardItem(str(source.name))
                item.setEditable(False)
                self.model.appendRow([item])
        self.table.resizeColumnsToContents()