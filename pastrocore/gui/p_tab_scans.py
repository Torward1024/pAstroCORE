from PySide6.QtWidgets import QWidget, QMessageBox, QMenu
from PySide6.QtCore import Signal, Slot, Qt, QSortFilterProxyModel, QRegularExpression, QPoint
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
from pastrocore.gui.ui_tab_observation_any import Ui_observation_tab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
import pastrocore.gui.rc_icons
import uuid

class ScansTab(QWidget):
    data_updated = Signal()

    def __init__(self, observation: Observation, project: ScheduleProject, manipulator: ScheduleManipulator, parent=None):
        super().__init__(parent)
        self.observation = observation
        self.project = project
        self.manipulator = manipulator
        
        # Настройка UI
        self.ui = Ui_observation_tab()
        self.ui.setupUi(self)
        self.ui.search.setPlaceholderText("Search scans...")

        # Настройка таблицы
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Scan ID"])
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterKeyColumn(-1)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.ui.table.setModel(self.proxy_model)
        self.ui.table.setAlternatingRowColors(True)
        self.ui.table.setSortingEnabled(True)
        self.ui.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.table.verticalHeader().setVisible(False)

        # Подключение сигналов
        self.ui.search.textChanged.connect(self.on_search_changed)
        self.ui.table.customContextMenuRequested.connect(self.show_context_menu)

    @Slot(str)
    def on_search_changed(self, text: str):
        """Handle search text change."""
        reg_exp = QRegularExpression(text)
        self.proxy_model.setFilterRegularExpression(reg_exp)

    def show_context_menu(self, position: QPoint):
        """Show context menu for the scans table."""
        index = self.ui.table.indexAt(position)
        menu = QMenu(self)
        add_action = menu.addAction(QIcon(":/icons/add_icon.svg"), "Add Scan")
        add_action.triggered.connect(self.add_scan)
        
        if index.isValid():
            source_index = self.proxy_model.mapToSource(index)
            scan_name = self.model.item(source_index.row(), 0).text()
            remove_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Remove Scan")
            edit_action = menu.addAction(QIcon(":/icons/edit_icon.svg"), "Edit Scan")
            remove_action.triggered.connect(lambda: self.remove_scan(scan_name))
            edit_action.triggered.connect(lambda: self.edit_scan(scan_name))
        
        menu.exec(self.ui.table.viewport().mapToGlobal(position))

    @Slot()
    def add_scan(self):
        """Add a new scan to the observation."""
        try:
            scan_name = f"scan_{uuid.uuid4().hex[:8]}"
            request = {
                "operation": "configure",
                "obj": self.observation.get_scans(),
                "attributes": {"add_item": {"name": scan_name}}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Added scan '{scan_name}' to observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit()
            else:
                logger.error(f"Failed to add scan: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to add scan: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while adding scan: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to add scan: {str(e)}")

    @Slot(str)
    def remove_scan(self, scan_name: str):
        """Remove a scan from the observation."""
        try:
            request = {
                "operation": "configure",
                "obj": self.observation.get_scans(),
                "attributes": {"remove_item": scan_name}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Removed scan '{scan_name}' from observation '{self.observation.code}'")
                self.update()
                self.data_updated.emit()
            else:
                logger.error(f"Failed to remove scan: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to remove scan: {response.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Exception while removing scan: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to remove scan: {str(e)}")

    @Slot(str)
    def edit_scan(self, scan_name: str):
        """Edit an existing scan."""
        if self.parent().parent_widget:
            logger.info(f"Requesting edit for scan '{scan_name}' in observation '{self.observation.code}'")
            self.parent().parent_widget.edit_scan(self.observation, scan_name)
        else:
            logger.warning("No parent widget to handle scan edit")
            QMessageBox.warning(self, "Warning", "Editing scan is not implemented yet.")

    @Slot()
    def update(self):
        """Update the scans table."""
        self.model.removeRows(0, self.model.rowCount())
        scans_response = self.manipulator.process_request({
            "operation": "inspect",
            "obj": self.observation,
            "attributes": {"get_scans": None}
        })
        if scans_response["status"]:
            scans = scans_response["result"].get_items() if hasattr(scans_response["result"], 'get_items') else []
            for scan in scans:
                item = QStandardItem(str(scan.name))
                item.setEditable(False)
                self.model.appendRow([item])
        self.ui.table.resizeColumnsToContents()