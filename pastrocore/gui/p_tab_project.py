from PySide6.QtWidgets import QWidget, QMessageBox, QMenu
from PySide6.QtCore import Signal, Slot, Qt, QRegularExpression, QPoint, QEvent
from PySide6.QtGui import QStandardItem, QIcon
from pastrocore.gui.ui_tab_project import Ui_ProjectInfoTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from msb_arch.utils.logging_setup import logger
from pastrocore.gui.p_custom_model import CustomStandardItemModel, CustomSortFilterProxyModel

class ProjectInfoTab(QWidget):
    """Widget for displaying and editing project information in a tab."""
    project_name_changed = Signal(str)

    def __init__(self, manipulator: ScheduleManipulator, parent=None):
        super().__init__(parent)
        self.ui = Ui_ProjectInfoTab()
        self.ui.setupUi(self)
        self.project = manipulator.get_managing_object()
        self.manipulator = manipulator
        self.parent_widget = parent
        self.setup_table()
        self.setup_connections()
        self.active_icon = QIcon(":/icons/active_icon.svg")
        self.inactive_icon = QIcon(":/icons/inactive_icon.svg")
        self.ui.search.setPlaceholderText("Search observations...")

    def setup_table(self):
        """Set up the observations table with appropriate columns."""
        self.model = CustomStandardItemModel()
        self.model.setHorizontalHeaderLabels([
            "#", " ", "Name", "Code", "Type", "Frequencies", "Start Time",
            "Duration", "Sources", "Telescopes", "Scans"
        ])
        self.proxy_model = CustomSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterKeyColumn(-1)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.ui.projectInfoTable.setModel(self.proxy_model)
        self.ui.projectInfoTable.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.projectInfoTable.customContextMenuRequested.connect(self.show_context_menu)
        self.ui.lineEdit.setReadOnly(True)
        self.ui.projectInfoTable.setAlternatingRowColors(True)
        self.ui.projectInfoTable.setSortingEnabled(True)
        self.ui.projectInfoTable.sortByColumn(0, Qt.AscendingOrder)
        self.ui.projectInfoTable.verticalHeader().setVisible(False)
        self.ui.projectInfoTable.setColumnWidth(1, 24)
        self.ui.projectInfoTable.setColumnHidden(2, True)

    def setup_connections(self):
        """Connect signals to slots."""
        self.ui.lineEdit.editingFinished.connect(self.handle_project_name_confirmed)
        self.ui.search.textChanged.connect(self.handle_search_text_changed)
        self.ui.projectInfoTable.doubleClicked.connect(self.handle_table_double_click)
        self.ui.lineEdit.mouseDoubleClickEvent = self.line_edit_double_click

    def line_edit_double_click(self, event):
        """Enable editing of project name on double-click."""
        self.ui.lineEdit.setReadOnly(False)
        self.ui.lineEdit.setFocus()
        self.ui.lineEdit.selectAll()
        event.accept()

    @Slot()
    def handle_project_name_confirmed(self):
        """Handle project name confirmation after editing."""
        if self.ui.lineEdit.isReadOnly():
            return
        new_name = self.ui.lineEdit.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Warning", "Project name cannot be empty.")
            self.update_tab()
            return
        try:
            self.manipulator.configure(self.project, set_name=new_name)
            self.project_name_changed.emit(new_name)
        except Exception as e:
            logger.error(f"Exception while changing project name: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to change project name: {str(e)}")
            self.update_tab()
        finally:
            self.ui.lineEdit.setReadOnly(True)

    @Slot(str)
    def handle_search_text_changed(self, text: str):
        """Handle search text change for filtering the table."""
        reg_exp = QRegularExpression(text)
        self.proxy_model.setFilterRegularExpression(reg_exp)

    @Slot()
    def update_tab(self):
        """Update the project info tab with current project data using Manipulator."""
        try:
            project_name = self.manipulator.inspect(self.project, get_name=None)
            project_name = project_name if isinstance(project_name, str) else "Untitled Project"
            self.ui.lineEdit.setText(project_name)

            observations = self.manipulator.inspect(self.project, get_items=None)
            if not isinstance(observations, dict):
                logger.error(f"Expected dict for observations, got {type(observations)}: {observations}")
                return

            current_codes = set()
            for obs in observations.values():
                try:
                    code = self.manipulator.inspect(obs, get_observation_code=None)
                    if code:
                        current_codes.add(code)
                except Exception as e:
                    logger.error(f"Failed to get code for observation: {str(e)}")
                    continue

            for i in range(self.model.rowCount() - 1, -1, -1):
                obs_code = self.model.item(i, 3).text()
                if obs_code not in current_codes:
                    self.model.removeRow(i)

            idx = 1
            for obs_name, obs in observations.items():
                if not isinstance(obs, Observation):
                    logger.error(f"Invalid observation type for name '{obs_name}': {type(obs)}")
                    continue

                try:
                    obs_code = self.manipulator.inspect(obs, get_observation_code=None)
                    if not obs_code:
                        logger.error(f"Failed to get code for observation with name '{obs_name}': No result returned")
                        continue

                    row_idx = None
                    for i in range(self.model.rowCount()):
                        if self.model.item(i, 3).text() == obs_code:
                            row_idx = i
                            break

                    is_active = bool(self.manipulator.inspect(obs, get="isactive"))
                    active_item = QStandardItem()
                    active_item.setIcon(self.active_icon if is_active else self.inactive_icon)
                    active_item.setToolTip("Active" if is_active else "Inactive")
                    active_item.setTextAlignment(Qt.AlignCenter)

                    obs_type = self.manipulator.inspect(obs, get="observation_type")
                    obs_type = obs_type if obs_type in ["VLBI", "SINGLE_DISH"] else "N/A"

                    freqs = "N/A"
                    frequencies = self.manipulator.inspect(obs, get_frequencies=None)
                    if frequencies:
                        active_freqs = self.manipulator.inspect(frequencies, get_active_items=None)
                        if isinstance(active_freqs, list):
                            frequencies_list = []
                            for if_obj in active_freqs:
                                try:
                                    freq = self.manipulator.inspect(if_obj, get="frequency")
                                    if isinstance(freq, (int, float)):
                                        frequencies_list.append(f"{freq:.0f} MHz")
                                except Exception as e:
                                    logger.error(f"Failed to get frequency for observation '{obs_name}': {str(e)}")
                                    continue
                            if frequencies_list:
                                freqs = ", ".join(frequencies_list)

                    start_time = self.manipulator.inspect(obs, get_start_datetime=None)
                    start_time = start_time.strftime("%d.%m.%Y %H:%M:%S") if start_time else "N/A"

                    duration = self.manipulator.inspect(obs, get_duration=None)
                    duration = str(duration) if duration else "N/A"

                    sources = self.manipulator.inspect(obs, get_sources=None)
                    sources_count = str(len(sources.get_items())) if sources and hasattr(sources, 'get_items') else "0"

                    telescopes = self.manipulator.inspect(obs, get_telescopes=None)
                    telescopes_count = str(len(telescopes.get_items())) if telescopes and hasattr(telescopes, 'get_items') else "0"

                    scans = self.manipulator.inspect(obs, get_scans=None)
                    scans_count = str(len(scans.get_items())) if scans and hasattr(scans, 'get_items') else "0"

                    row = [
                        QStandardItem(str(idx)),
                        active_item,
                        QStandardItem(obs_name),
                        QStandardItem(obs_code),
                        QStandardItem(obs_type),
                        QStandardItem(freqs),
                        QStandardItem(start_time),
                        QStandardItem(duration),
                        QStandardItem(sources_count),
                        QStandardItem(telescopes_count),
                        QStandardItem(scans_count)
                    ]
                    for item in row:
                        item.setEditable(False)

                    row[0].setData(obs_name, Qt.UserRole)
                    row[0].setData(idx, Qt.UserRole + 1)

                    if row_idx is None:
                        self.model.appendRow(row)
                    else:
                        for col, item in enumerate(row):
                            self.model.setItem(row_idx, col, item)
                    idx += 1
                except Exception as e:
                    logger.error(f"Exception while processing observation '{obs_name}': {str(e)}")
                    continue

            self.ui.projectInfoTable.resizeColumnsToContents()
        except Exception as e:
            logger.error(f"Exception while updating project info tab: {str(e)}")

    def show_context_menu(self, position: QPoint):
        """Show context menu for the observations table."""
        menu = QMenu(self)
        
        add_action = menu.addAction(QIcon(":/icons/add_observation_icon.svg"), "Add Observation")
        import_new_action = menu.addAction(QIcon(":/icons/import_icon.svg"), "Import New Observation")
        add_action.triggered.connect(self.add_observation)
        import_new_action.triggered.connect(self.import_new_observation)
        
        try:
            observations = self.manipulator.inspect(self.project, get_items=None)
            has_observations = isinstance(observations, dict) and len(observations) > 0
        except Exception as e:
            logger.error(f"Exception while inspecting observations: {str(e)}")
            has_observations = False

        if has_observations:
            activate_all_action = menu.addAction(QIcon(":/icons/active_icon.svg"), "Activate All")
            deactivate_all_action = menu.addAction(QIcon(":/icons/inactive_icon.svg"), "Deactivate All")
            drop_active_action = menu.addAction(QIcon(":/icons/remove_observation_icon.svg"), "Drop Active")
            drop_inactive_action = menu.addAction(QIcon(":/icons/remove_observation_icon.svg"), "Drop Inactive")
            clear_action = menu.addAction(QIcon(":/icons/remove_observation_icon.svg"), "Clear")
            clear_action.triggered.connect(self.clear)
            activate_all_action.triggered.connect(self.activate_all_observations)
            deactivate_all_action.triggered.connect(self.deactivate_all_observations)
            drop_active_action.triggered.connect(self.drop_active_observations)
            drop_inactive_action.triggered.connect(self.drop_inactive_observations)

            index = self.ui.projectInfoTable.indexAt(position)
            if index.isValid():
                source_index = self.proxy_model.mapToSource(index)
                obs_name = self.model.item(source_index.row(), 0).data(Qt.UserRole)
                obs_code = self.model.item(source_index.row(), 3).text()

                try:
                    observation = self.manipulator.inspect(self.project, get_item=obs_name)
                except Exception as e:
                    logger.error(f"Failed to get observation '{obs_code}': {str(e)}")
                
                is_active = self.manipulator.inspect(observation, get="isactive")

                menu.addSeparator()
                if is_active:
                    deactivate_action = menu.addAction(QIcon(":/icons/inactive_icon.svg"), "Deactivate")
                    deactivate_action.triggered.connect(lambda: self.deactivate_observation(obs_name, obs_code))
                else:
                    activate_action = menu.addAction(QIcon(":/icons/active_icon.svg"), "Activate")
                    activate_action.triggered.connect(lambda: self.activate_observation(obs_name, obs_code))

                menu.addSeparator()
                import_action = menu.addAction(QIcon(":/icons/import_icon.svg"), "Import Observation")
                export_action = menu.addAction(QIcon(":/icons/export_icon.svg"), "Export Observation")
                import_action.triggered.connect(lambda: self.import_observation(obs_name, obs_code))
                export_action.triggered.connect(lambda: self.export_observation(obs_name, obs_code))
                menu.addSeparator()
                remove_action = menu.addAction(QIcon(":/icons/remove_observation_icon.svg"), "Remove Observation")
                edit_action = menu.addAction(QIcon(":/icons/edit_observation_icon.svg"), "Edit Observation")
                remove_action.triggered.connect(lambda: self.remove_observation(obs_name, obs_code))
                edit_action.triggered.connect(lambda: self.edit_observation(obs_name, obs_code))

        menu.exec(self.ui.projectInfoTable.viewport().mapToGlobal(position))

    @Slot()
    def import_new_observation(self):
        """Import a new observation into the project."""
        if self.parent_widget:
            self.parent_widget.import_new_observation()

    @Slot(str)
    def import_observation(self, obs_name: str, obs_code: str):
        """Import specific observation."""
        if self.parent_widget:
            self.parent_widget.import_observation(obs_name, obs_code)

    @Slot(str)
    def export_observation(self, obs_name: str, obs_code: str):
        """Export specific observation."""
        if self.parent_widget:
            self.parent_widget.export_observation(obs_name, obs_code)

    @Slot(str)
    def activate_observation(self, obs_name: str, obs_code: str):
        """Activate the specified observation."""
        try:
            self.manipulator.configure(self.project, activate_item=obs_name)
            self.update_tab()
            self.project_name_changed.emit(self.ui.lineEdit.text())
            logger.info(f"Observation '{obs_code}' activated")
        except Exception as e:
            logger.error(f"Exception while activating observation '{obs_code}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to activate observation: {str(e)}")

    @Slot(str)
    def deactivate_observation(self, obs_name: str, obs_code: str):
        """Deactivate the specified observation."""
        try:
            self.manipulator.configure(self.project, deactivate_item=obs_name)
            self.update_tab()
            self.project_name_changed.emit(self.ui.lineEdit.text())
            logger.info(f"Observation '{obs_name}' deactivated")
        except Exception as e:
            logger.error(f"Exception while deactivating observation '{obs_name}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to deactivate observation: {str(e)}")

    @Slot()
    def clear(self):
        """Clear all observations in the project."""
        if self.parent_widget:
            self.parent_widget.remove_observations()

    @Slot()
    def activate_all_observations(self):
        """Activate all observations in the project."""
        try:
            self.manipulator.configure(self.project, activate_all=None)
            self.update_tab()
            self.project_name_changed.emit(self.ui.lineEdit.text())
            logger.info("All observations activated")
        except Exception as e:
            logger.error(f"Exception while activating all observations: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to activate all observations: {str(e)}")

    @Slot()
    def deactivate_all_observations(self):
        """Deactivate all observations in the project."""
        try:
            self.manipulator.configure(self.project, deactivate_all=None)
            self.update_tab()
            self.project_name_changed.emit(self.ui.lineEdit.text())
            logger.info("All observations deactivated")
        except Exception as e:
            logger.error(f"Exception while deactivating all observations: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to deactivate all observations: {str(e)}")

    @Slot()
    def drop_active_observations(self):
        """Remove all active observations from the project."""
        try:
            self.manipulator.configure(self.project, drop_active=None)
            self.update_tab()
            self.project_name_changed.emit(self.ui.lineEdit.text())
            logger.info("All active observations dropped")
        except Exception as e:
            logger.error(f"Exception while dropping active observations: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to drop active observations: {str(e)}")

    @Slot()
    def drop_inactive_observations(self):
        """Remove all inactive observations from the project."""
        try:
            self.manipulator.configure(self.project, drop_inactive=None)
            self.update_tab()
            self.project_name_changed.emit(self.ui.lineEdit.text())
            logger.info("All inactive observations dropped")
        except Exception as e:
            logger.error(f"Exception while dropping inactive observations: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to drop inactive observations: {str(e)}")

    @Slot()
    def add_observation(self):
        """Add a new observation to the project."""
        if self.parent_widget:
            self.parent_widget.add_observation()

    @Slot(str)
    def remove_observation(self, obs_name: str, obs_code: str):
        """Remove an observation from the project."""
        if self.parent_widget:
            self.parent_widget.remove_observation(obs_name, obs_code)

    @Slot(str)
    def edit_observation(self, obs_name: str, obs_code: str):
        """Edit an observation."""
        if self.parent_widget:
            self.parent_widget.edit_observation(obs_name, obs_code)

    @Slot()
    def handle_table_double_click(self, index):
        """Handle double-click on table to edit observation."""
        if index.isValid():
            source_index = self.proxy_model.mapToSource(index)
            obs_name = self.model.item(source_index.row(), 0).data(Qt.UserRole)
            obs_code = self.model.item(source_index.row(), 3).text()
            self.edit_observation(obs_name, obs_code)

    def _cleanup(self):
        """Clean up resources associated with this tab."""
        try:
            self.blockSignals(True)
            
            try:
                self.project_name_changed.disconnect()
                logger.debug(f"Disconnected project_name_changed signal for {self.objectName()}")
            except TypeError as e:
                logger.debug(f"No connections to disconnect for project_name_changed signal in {self.objectName()}: {str(e)}")

            self.ui.projectInfoTable.setModel(None)
            if self.model:
                self.model.clear()
                self.model.deleteLater()
            if self.proxy_model:
                self.proxy_model.deleteLater()

            self.project = None
            self.manipulator = None
            self.parent_widget = None
            self.model = None
            self.proxy_model = None
            
            logger.debug(f"Cleaned up resources for {self.objectName()}")
        except Exception as e:
            logger.error(f"Error cleaning up {self.objectName()}: {str(e)}")

    def closeEvent(self, event: QEvent):
        """Override closeEvent to perform cleanup before closing."""
        self._cleanup()
        super().closeEvent(event)
    