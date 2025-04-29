from PySide6.QtWidgets import QWidget, QMessageBox, QVBoxLayout
from PySide6.QtCore import Signal, Slot, Qt
from pastrocore.utils.catalogmanager import CatalogManager
from pastrocore.gui.ui_tab_observation import Ui_ObservationInfoTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
from .p_tab_frequencies import FrequenciesTab
from .p_tab_sources import SourcesTab
from .p_tab_telescopes import TelescopesTab
from .p_tab_scans import ScansTab
import pastrocore.gui.rc_icons

class ObservationTab(QWidget):
    observation_updated = Signal()

    def __init__(self, observation: Observation, project: ScheduleProject, manipulator: ScheduleManipulator, catalog_manager: CatalogManager, parent=None):
        super().__init__(parent)
        self.ui = Ui_ObservationInfoTab()
        self.ui.setupUi(self)
        self.project = project
        self.observation = observation
        self.manipulator = manipulator
        self.catalog_manager = catalog_manager
        self.parent_widget = parent
        self._updating = False

        # Инициализация вкладок для таблиц
        self.frequencies_tab = FrequenciesTab(observation, project, manipulator, self)
        self.sources_tab = SourcesTab(self.observation, self.project, self.manipulator, self.catalog_manager, self)
        self.telescopes_tab = TelescopesTab(observation, self.project, self.manipulator, self.catalog_manager, self)
        self.scans_tab = ScansTab(observation, project, manipulator, self)

        # Создание вкладок и добавление их в tabWidget
        # Frequencies Tab
        self.tab_freq = QWidget()
        self.tab_freq.setObjectName("tab_freq")
        frequencies_layout = QVBoxLayout(self.tab_freq)
        frequencies_layout.addWidget(self.frequencies_tab)
        self.ui.tabWidget.addTab(self.tab_freq, "Frequencies")

        # Sources Tab
        self.tab_sources = QWidget()
        self.tab_sources.setObjectName("tab_sources")
        sources_layout = QVBoxLayout(self.tab_sources)
        sources_layout.addWidget(self.sources_tab)
        self.ui.tabWidget.addTab(self.tab_sources, "Sources")

        # Telescopes Tab
        self.tab_tels = QWidget()
        self.tab_tels.setObjectName("tab_tels")
        telescopes_layout = QVBoxLayout(self.tab_tels)
        telescopes_layout.addWidget(self.telescopes_tab)
        self.ui.tabWidget.addTab(self.tab_tels, "Telescopes")

        # Scans Tab
        self.tab_scans = QWidget()
        self.tab_scans.setObjectName("tab_scans")
        scans_layout = QVBoxLayout(self.tab_scans)
        scans_layout.addWidget(self.scans_tab)
        self.ui.tabWidget.addTab(self.tab_scans, "Scans")

        self.setup_connections()
        self.update_tab()

    def setup_connections(self):
        """Connect UI signals to slots."""
        self.ui.obs_name_edit.editingFinished.connect(self.on_obs_name_confirmed)
        self.ui.combo_obs_type.currentTextChanged.connect(self.on_obs_type_changed)
        self.ui.obs_name_edit.mouseDoubleClickEvent = self.on_obs_name_edit_double_click

        # Подключаем сигналы от дочерних вкладок
        self.frequencies_tab.data_updated.connect(self.observation_updated)
        self.sources_tab.data_updated.connect(self.observation_updated)
        self.telescopes_tab.data_updated.connect(self.observation_updated)
        self.scans_tab.data_updated.connect(self.observation_updated)

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
                # Обновляем зависимости дочерних вкладок
                self.frequencies_tab.observation = self.observation
                self.sources_tab.observation = self.observation
                self.telescopes_tab.observation = self.observation
                self.scans_tab.observation = self.observation

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

            # Обновляем дочерние вкладки
            self.frequencies_tab.update()
            self.sources_tab.update()
            self.telescopes_tab.update()
            self.scans_tab.update()

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