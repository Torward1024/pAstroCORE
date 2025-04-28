from PySide6.QtWidgets import QWidget, QMessageBox
from PySide6.QtCore import Signal, Slot
from pastrocore.gui.ui_tab_observation import Ui_ObservationInfoTab
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger

class ObservationTab(QWidget):
    observation_updated = Signal()
    
    def __init__(self, observation: Observation, manipulator: ScheduleManipulator, parent=None):
        super().__init__(parent)
        self.ui = Ui_ObservationInfoTab()
        self.ui.setupUi(self)
        self.observation = observation
        self.manipulator = manipulator
        self.parent_widget = parent
        self.update_tab()

    @Slot()
    def update_tab(self):
        """Update the observation tab with current observation data."""
        # Проверяем, существует ли наблюдение в проекте
        project = self.parent_widget.project
        updated_observation = project.get_observation(self.observation.get_observation_code())
        if updated_observation:
            self.observation = updated_observation
            # Здесь обновляем UI элементы вкладки (предполагаем, что они есть)
            logger.info(f"Observation tab updated for '{self.observation.get_observation_code()}'")
        else:
            # Если наблюдение удалено, закрываем вкладку
            logger.info(f"Observation '{self.observation.get_observation_code()}' no longer exists, closing tab")
            tab_container = self.parent_widget.ui.tabContainer
            for i in range(tab_container.count()):
                widget = tab_container.widget(i)
                if widget == self:
                    tab_container.removeTab(i)
                    break

    @Slot()
    def on_observation_changed(self):
        """Handle changes in observation data."""
        # Здесь логика сохранения изменений в наблюдении через manipulator
        self.observation_updated.emit()