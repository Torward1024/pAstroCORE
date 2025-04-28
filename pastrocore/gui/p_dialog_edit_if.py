from PySide6.QtWidgets import QWidget, QMessageBox, QMenu, QDialog
from PySide6.QtCore import Signal, Slot, Qt, QSortFilterProxyModel, QRegularExpression, QPoint
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
from pastrocore.gui.ui_tab_observation import Ui_ObservationInfoTab
from pastrocore.gui.ui_dialog_edit_if import Ui_IFEditorDialog  # Импорт интерфейса диалога
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from pastrocore.base.frequencies import IF, Frequencies 
from common.utils.logging_setup import logger

class IFEditorDialog(QDialog):
    """Dialog for editing or adding an Intermediate Frequency (IF)."""
    def __init__(self, if_obj: IF = None, parent=None):
        super().__init__(parent)
        self.ui = Ui_IFEditorDialog()
        self.ui.setupUi(self)
        self.if_obj = if_obj  # Существующий объект IF для редактирования, если передан
        self.setup_dialog()
        self.setup_connections()

    def setup_dialog(self):
        """Initialize the dialog with IF data or defaults."""
        # Устанавливаем доступные поляризации из frequencies.py
        self.valid_polarizations = {"RCP", "LCP", "RR", "LL", "RL", "LR", "H", "V"}
        
        # Если редактируем существующий IF
        if self.if_obj:
            self.ui.frequencyEdit.setValue(self.if_obj.frequency)
            self.ui.bandwidthEdit.setValue(self.if_obj.bandwidth)
            self.ui.isActiveCheckBox.setChecked(self.if_obj.isactive)
            # Устанавливаем выбранные поляризации
            for index in range(self.ui.polarizationsList.count()):
                item = self.ui.polarizationsList.item(index)
                if item.text() in self.if_obj.polarizations:
                    item.setSelected(True)
            self.setWindowTitle(f"Edit IF")
        else:
            # Значения по умолчанию для нового IF
            self.ui.frequencyEdit.setValue(1000.0)
            self.ui.bandwidthEdit.setValue(16.0)
            self.ui.isActiveCheckBox.setChecked(True)
            self.setWindowTitle("Add Intermediate Frequency")

        # Обновляем длину волны при инициализации
        self.update_wavelength()

    def setup_connections(self):
        """Connect UI signals to slots."""
        self.ui.frequencyEdit.valueChanged.connect(self.update_wavelength)
        self.ui.clearPolarizationsButton.clicked.connect(self.clear_polarizations)

    def update_wavelength(self):
        """Update the wavelength display based on frequency."""
        try:
            frequency = self.ui.frequencyEdit.value()
            if frequency <= 0:
                self.ui.wavelengthDisplay.setText("N/A")
                return
            # Используем константу C_MHZ_CM из frequencies.py
            wavelength = 29979.2458 / frequency  # C_MHZ_CM / frequency
            self.ui.wavelengthDisplay.setText(f"{wavelength:.3f}")
        except Exception as e:
            logger.error(f"Error calculating wavelength: {str(e)}")
            self.ui.wavelengthDisplay.setText("N/A")

    def clear_polarizations(self):
        """Clear all selected polarizations."""
        for index in range(self.ui.polarizationsList.count()):
            item = self.ui.polarizationsList.item(index)
            item.setSelected(False)

    def get_if_data(self):
        """Retrieve the IF data from the dialog."""
        frequency = self.ui.frequencyEdit.value()
        bandwidth = self.ui.bandwidthEdit.value()
        isactive = self.ui.isActiveCheckBox.isChecked()
        
        # Получаем выбранные поляризации
        polarizations = []
        for index in range(self.ui.polarizationsList.count()):
            item = self.ui.polarizationsList.item(index)
            if item.isSelected():
                polarizations.append(item.text())

        # Валидация поляризаций (аналогично frequencies.py)
        if polarizations:
            circular = {"RCP", "LCP"}
            paired_linear = {"RR", "LL", "RL", "LR"}
            single_linear = {"H", "V"}
            
            if all(p in circular for p in polarizations):
                group = "circular"
            elif all(p in paired_linear for p in polarizations):
                group = "paired linear"
            elif all(p in single_linear for p in polarizations):
                group = "single linear"
            else:
                raise ValueError("Polarizations must belong to a single group (circular, paired linear, or single linear)")
        
        return {
            "frequency": frequency,
            "bandwidth": bandwidth,
            "polarizations": polarizations,
            "isactive": isactive
        }