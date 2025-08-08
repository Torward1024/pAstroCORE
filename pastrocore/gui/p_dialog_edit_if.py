from PySide6.QtWidgets import QDialog
from pastrocore.gui.ui_dialog_edit_if import Ui_IFEditorDialog
from pastrocore.base.frequencies import IF
from common.utils.logging_setup import logger

class IFEditorDialog(QDialog):
    """Dialog for editing or adding an Intermediate Frequency (IF)."""
    def __init__(self, if_obj: IF = None, parent=None):
        super().__init__(parent)
        self.ui = Ui_IFEditorDialog()
        self.ui.setupUi(self)
        self.if_obj = if_obj
        self.setup_dialog()
        self.setup_connections()

    def setup_dialog(self):
        """Initialize the dialog with IF data or defaults."""
        self.valid_polarizations = {"RCP", "LCP", "H", "V"}
        
        if self.if_obj:
            self.ui.frequencyEdit.setValue(self.if_obj.frequency)
            self.ui.bandwidthEdit.setValue(self.if_obj.bandwidth)
            self.ui.isActiveCheckBox.setChecked(self.if_obj.isactive)
            for index in range(self.ui.polarizationsList.count()):
                item = self.ui.polarizationsList.item(index)
                if item.text() in self.if_obj.polarizations:
                    item.setSelected(True)
            self.setWindowTitle(f"Edit IF")
        else:
            self.ui.frequencyEdit.setValue(1000.0)
            self.ui.bandwidthEdit.setValue(16.0)
            self.ui.isActiveCheckBox.setChecked(True)
            self.setWindowTitle("Add Intermediate Frequency")
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
            wavelength = 29979.2458 / frequency
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
        
        polarizations = []
        for index in range(self.ui.polarizationsList.count()):
            item = self.ui.polarizationsList.item(index)
            if item.isSelected():
                polarizations.append(item.text())

        if polarizations:
            circular = {"RCP", "LCP"}
            single_linear = {"H", "V"}
            
            if all(p in circular for p in polarizations):
                group = "circular"
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