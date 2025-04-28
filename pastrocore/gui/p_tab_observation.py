from PySide6.QtWidgets import QWidget, QMessageBox, QMenu
from PySide6.QtCore import Signal, Slot, Qt, QSortFilterProxyModel, QRegularExpression
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
from pastrocore.gui.ui_tab_observation import Ui_ObservationInfoTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
import uuid

class ObservationTab(QWidget):
    observation_updated = Signal()

    def __init__(self, observation: Observation, project: ScheduleProject, manipulator: ScheduleManipulator, parent=None):
        super().__init__(parent)
        self.ui = Ui_ObservationInfoTab()
        self.ui.setupUi(self)
        self.project = project
        self.observation = observation
        self.manipulator = manipulator
        self.parent_widget = parent
        self._updating = False  # Флаг для предотвращения рекурсивных обновлений
        self.setup_tables()
        self.setup_connections()
        self.update_tab()

    def setup_tables(self):
        """Set up tables for frequencies, sources, telescopes, and scans."""
        # Frequencies table
        self.freq_model = QStandardItemModel()
        self.freq_model.setHorizontalHeaderLabels(["Band (Hz)"])
        self.freq_proxy_model = QSortFilterProxyModel()
        self.freq_proxy_model.setSourceModel(self.freq_model)
        self.freq_proxy_model.setFilterKeyColumn(-1)
        self.freq_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.ui.frequencies_table.setModel(self.freq_proxy_model)
        self.ui.frequencies_table.setAlternatingRowColors(True)
        self.ui.frequencies_table.setSortingEnabled(True)
        self.ui.frequencies_table.verticalHeader().setVisible(False)

        # Sources table
        self.sources_model = QStandardItemModel()
        self.sources_model.setHorizontalHeaderLabels(["Source Name"])
        self.sources_proxy_model = QSortFilterProxyModel()
        self.sources_proxy_model.setSourceModel(self.sources_model)
        self.sources_proxy_model.setFilterKeyColumn(-1)
        self.sources_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.ui.sources_table.setModel(self.sources_proxy_model)
        self.ui.sources_table.setAlternatingRowColors(True)
        self.ui.sources_table.setSortingEnabled(True)
        self.ui.sources_table.verticalHeader().setVisible(False)

        # Telescopes table
        self.telescopes_model = QStandardItemModel()
        self.telescopes_model.setHorizontalHeaderLabels(["Telescope Name"])
        self.telescopes_proxy_model = QSortFilterProxyModel()
        self.telescopes_proxy_model.setSourceModel(self.telescopes_model)
        self.telescopes_proxy_model.setFilterKeyColumn(-1)
        self.telescopes_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.ui.telescopes_table.setModel(self.telescopes_proxy_model)
        self.ui.telescopes_table.setAlternatingRowColors(True)
        self.ui.telescopes_table.setSortingEnabled(True)
        self.ui.telescopes_table.verticalHeader().setVisible(False)

        # Scans table
        self.scans_model = QStandardItemModel()
        self.scans_model.setHorizontalHeaderLabels(["Scan ID"])
        self.scans_proxy_model = QSortFilterProxyModel()
        self.scans_proxy_model.setSourceModel(self.scans_model)
        self.scans_proxy_model.setFilterKeyColumn(-1)
        self.scans_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.ui.scans_table.setModel(self.scans_proxy_model)
        self.ui.scans_table.setAlternatingRowColors(True)
        self.ui.scans_table.setSortingEnabled(True)
        self.ui.scans_table.verticalHeader().setVisible(False)

        # Disable editing in obs_name_edit by default
        self.ui.obs_name_edit.setReadOnly(True)

    def setup_connections(self):
        """Connect UI signals to slots."""
        self.ui.search_freqs.textChanged.connect(self.on_search_freqs_changed)
        self.ui.search_sources.textChanged.connect(self.on_search_sources_changed)
        self.ui.search_telescopes.textChanged.connect(self.on_search_telescopes_changed)
        self.ui.search_scans.textChanged.connect(self.on_search_scans_changed)
        self.ui.obs_name_edit.editingFinished.connect(self.on_obs_name_confirmed)
        self.ui.combo_obs_type.currentTextChanged.connect(self.on_obs_type_changed)
        self.ui.obs_name_edit.mouseDoubleClickEvent = self.on_obs_name_edit_double_click

    @Slot(str)
    def on_search_freqs_changed(self, text: str):
        """Handle search text change for frequencies table."""
        reg_exp = QRegularExpression(text)
        self.freq_proxy_model.setFilterRegularExpression(reg_exp)

    @Slot(str)
    def on_search_sources_changed(self, text: str):
        """Handle search text change for sources table."""
        reg_exp = QRegularExpression(text)
        self.sources_proxy_model.setFilterRegularExpression(reg_exp)

    @Slot(str)
    def on_search_telescopes_changed(self, text: str):
        """Handle search text change for telescopes table."""
        reg_exp = QRegularExpression(text)
        self.telescopes_proxy_model.setFilterRegularExpression(reg_exp)

    @Slot(str)
    def on_search_scans_changed(self, text: str):
        """Handle search text change for scans table."""
        reg_exp = QRegularExpression(text)
        self.scans_proxy_model.setFilterRegularExpression(reg_exp)

    def on_obs_name_edit_double_click(self, event):
        """Enable editing of observation code on double-click."""
        self.ui.obs_name_edit.setReadOnly(False)
        self.ui.obs_name_edit.setFocus()
        self.ui.obs_name_edit.selectAll()
        event.accept()

    @Slot()
    def on_obs_name_confirmed(self):
        if self.ui.obs_name_edit.isReadOnly():
            return
        new_code = self.ui.obs_name_edit.text().strip()
        if not new_code:
            QMessageBox.warning(self, "Warning", "Observation code cannot be empty.")
            self.update_tab()
            return
        old_code = self.observation.code
        if new_code == old_code:
            self.ui.obs_name_edit.setReadOnly(True)
            return
        try:
            # Обновляем только code
            request = {
                "operation": "configure",
                "obj": self.observation,
                "attributes": {"set": {"params": {"code": new_code}}}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Observation code changed from '{old_code}' to '{new_code}'")
                self.observation.code = new_code
                self.observation_updated.emit()
            else:
                logger.error(f"Failed to change observation code: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to change observation code: {response.get('error', 'Unknown error')}")
                self.update_tab()
        except Exception as e:
            logger.error(f"Exception while changing observation code: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to change observation code: {str(e)}")
            self.observation.code = old_code
        finally:
            self.ui.obs_name_edit.setReadOnly(True)

    @Slot(str)
    def on_obs_type_changed(self, text: str):
        """Handle observation type change."""
        if not text or self._updating:
            return
        try:
            request = {
                "operation": "configure",
                "obj": self.observation,
                "attributes": {"set": {"params": {"observation_type": text}}}
            }
            response = self.manipulator.process_request(request)
            if response["status"]:
                logger.info(f"Observation type changed to '{text}' for code '{self.observation.get_observation_code()}'")
                self.observation_updated.emit()
            else:
                logger.error(f"Failed to change observation type: {response.get('error', 'Unknown error')}")
                QMessageBox.critical(self, "Error", f"Failed to change observation type: {response.get('error', 'Unknown error')}")
                self.update_tab()
        except Exception as e:
            logger.error(f"Exception while changing observation type: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to change observation type: {str(e)}")

    @Slot()
    def update_tab(self):
        """Update the observation tab with current observation data."""
        if self._updating:
            logger.debug(f"Skipping update_tab for code '{self.observation.get_observation_code()}' as it is already updating")
            return
        self._updating = True
        logger.debug(f"Starting update_tab for observation with code '{self.observation.get_observation_code()}'")
        try:
            # Check if observation still exists in project using Manipulator
            obs_code_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation,
                "attributes": {"get_observation_code": None}
            })
            if not obs_code_response["status"]:
                logger.error(f"Failed to get observation code: {obs_code_response.get('error', 'Unknown error')}")
                self.close_tab()
                return
            obs_code = obs_code_response["result"]

            # Проверяем, существует ли наблюдение в проекте
            obs_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.project,
                "attributes": {"get_observation_by_code": obs_code}
            })
            if not obs_response["status"] or not obs_response["result"]:
                logger.info(f"Observation with code '{obs_code}' no longer exists, closing tab")
                self.close_tab()
                return

            new_observation = obs_response["result"]
            # Проверяем, изменились ли данные наблюдения
            if new_observation != self.observation:
                logger.debug(f"Observation with code '{obs_code}' data updated, refreshing local reference")
                self.observation = new_observation

            # Update observation code (visible to user)
            self.ui.obs_name_edit.setText(self.observation.code)

            # Update observation code in tab title
            self.setObjectName(f"observationTab_{obs_code}")
            for i in range(self.parent_widget.ui.tabContainer.count()):
                if self.parent_widget.ui.tabContainer.widget(i) == self:
                    self.parent_widget.ui.tabContainer.setTabText(i, f"Observation: {obs_code}")
                    break

            # Update observation type
            type_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation,
                "attributes": {"get": "observation_type"}
            })
            obs_type = type_response["result"] if type_response["status"] and type_response["result"] in ["VLBI", "SINGLE_DISH"] else "VLBI"
            if self.ui.combo_obs_type.currentText() != obs_type:
                self.ui.combo_obs_type.blockSignals(True)
                self.ui.combo_obs_type.clear()
                self.ui.combo_obs_type.addItems(["VLBI", "SINGLE_DISH"])
                self.ui.combo_obs_type.setCurrentText(obs_type)
                self.ui.combo_obs_type.blockSignals(False)

            # Update start time and duration
            start_time_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation,
                "attributes": {"get_start_datetime": None}
            })
            start_time = str(start_time_response["result"]) if start_time_response["status"] and start_time_response["result"] else "N/A"

            duration_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation,
                "attributes": {"get_duration": None}
            })
            duration = str(duration_response["result"]) if duration_response["status"] and duration_response["result"] else "N/A"

            self.ui.lbl_obs_info.setText(f"Start Time/Date: {start_time} Duration: {duration} sec.")

            # Update frequencies table
            frequencies_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation,
                "attributes": {"get_frequencies": None}
            })
            self.freq_model.removeRows(0, self.freq_model.rowCount())
            if frequencies_response["status"] and frequencies_response["result"]:
                bands_response = self.manipulator.process_request({
                    "operation": "inspect",
                    "obj": frequencies_response["result"],
                    "attributes": {"get_bands": None}
                })
                if bands_response["status"] and isinstance(bands_response["result"], list):
                    for band in bands_response["result"]:
                        item = QStandardItem(f"{band} Hz")
                        item.setEditable(False)
                        self.freq_model.appendRow([item])

            # Update sources table
            sources_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation,
                "attributes": {"get_sources": None}
            })
            self.sources_model.removeRows(0, self.sources_model.rowCount())
            if sources_response["status"]:
                sources = sources_response["result"].get_items() if hasattr(sources_response["result"], 'get_items') else []
                for source in sources:
                    item = QStandardItem(str(source.name))
                    item.setEditable(False)
                    self.sources_model.appendRow([item])

            # Update telescopes table
            telescopes_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation,
                "attributes": {"get_telescopes": None}
            })
            self.telescopes_model.removeRows(0, self.telescopes_model.rowCount())
            if telescopes_response["status"]:
                telescopes = telescopes_response["result"].get_items() if hasattr(telescopes_response["result"], 'get_items') else []
                for telescope in telescopes:
                    item = QStandardItem(str(telescope.name))
                    item.setEditable(False)
                    self.telescopes_model.appendRow([item])

            # Update scans table
            scans_response = self.manipulator.process_request({
                "operation": "inspect",
                "obj": self.observation,
                "attributes": {"get_scans": None}
            })
            self.scans_model.removeRows(0, self.scans_model.rowCount())
            if scans_response["status"]:
                scans = scans_response["result"].get_items() if hasattr(scans_response["result"], 'get_items') else []
                for scan in scans:
                    item = QStandardItem(str(scan.name))
                    item.setEditable(False)
                    self.scans_model.appendRow([item])

            # Adjust column widths
            self.ui.frequencies_table.resizeColumnsToContents()
            self.ui.sources_table.resizeColumnsToContents()
            self.ui.telescopes_table.resizeColumnsToContents()
            self.ui.scans_table.resizeColumnsToContents()

            logger.info(f"Observation tab updated for code '{obs_code}'")
        except Exception as e:
            logger.error(f"Error updating observation tab for code '{obs_code}': {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to update observation tab: {str(e)}")
        finally:
            self._updating = False

    def close_tab(self):
        """Close the current observation tab."""
        tab_container = self.parent_widget.ui.tabContainer
        for i in range(tab_container.count()):
            if tab_container.widget(i) == self:
                tab_container.removeTab(i)
                break
        logger.info(f"Closed observation tab for code '{self.observation.get_observation_code()}'")

    @Slot()
    def on_observation_changed(self):
        """Handle changes in observation data."""
        if not self._updating:
            logger.info(f"Observation changed, emitting observation_updated for code '{self.observation.get_observation_code()}'")
            self.observation_updated.emit()