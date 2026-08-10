# pastrocore/gui/p_dialog_edit_if.py
from PySide6.QtWidgets import QDialog, QMessageBox
from pastrocore.gui.ui_dialog_edit_if import Ui_IFEditorDialog
from pastrocore.base.frequencies import IF
from msb_arch.utils.logging_setup import logger
import uuid

class IFEditorDialog(QDialog):
    """Dialog for editing or adding an Intermediate Frequency (IF)."""
    def __init__(self, if_obj: IF = None, parent=None):
        super().__init__(parent)
        self.ui = Ui_IFEditorDialog()
        self.ui.setupUi(self)
        self.if_obj = if_obj
        self.valid_polarizations = {"RCP", "LCP", "H", "V"}
        self.setup_connections()
        self.load_data()

    def setup_connections(self):
        """Connect UI signals to slots."""
        self.ui.frequencyEdit.valueChanged.connect(self.update_wavelength)
        self.ui.clearPolarizationsButton.clicked.connect(self.clear_polarizations)
        self.ui.saveButton.clicked.connect(self.accept)
        self.ui.cancelButton.clicked.connect(self.reject)

    def load_data(self):
        """Load IF data into the dialog fields."""
        if not self.if_obj:
            self.if_obj = IF(
                name=f"if_{uuid.uuid4().hex[:32]}",
                frequency=1000.0,
                bandwidth=16.0,
                polarizations=[],
                isactive=True
            )
            self.setWindowTitle("Add Intermediate Frequency")
            logger.debug("Creating new IF")
        else:
            self.setWindowTitle(f"Edit Intermediate Frequency")
            logger.debug("Editing existing IF '%s'", self.if_obj.name)

        self.ui.frequencyEdit.setValue(self.if_obj.frequency)
        self.ui.bandwidthEdit.setValue(self.if_obj.bandwidth)
        self.ui.isActiveCheckBox.setChecked(self.if_obj.isactive)
        for index in range(self.ui.polarizationsList.count()):
            item = self.ui.polarizationsList.item(index)
            item.setSelected(item.text() in self.if_obj.polarizations)

        self.update_wavelength()
        logger.info("Loaded IF '%s' into editor dialog", self.if_obj.name)

    def update_wavelength(self):
        """Update the wavelength display based on frequency."""
        try:
            frequency = self.ui.frequencyEdit.value()
            if frequency <= 0:
                self.ui.wavelengthDisplay.setText("N/A")
                logger.warning("Frequency is non-positive, wavelength set to N/A")
                return
            wavelength = 29979.2458 / frequency
            self.ui.wavelengthDisplay.setText(f"{wavelength:.3f}")
        except Exception as e:
            logger.error("Error calculating wavelength: %s", str(e))
            self.ui.wavelengthDisplay.setText("N/A")

    def clear_polarizations(self):
        """Clear all selected polarizations."""
        for index in range(self.ui.polarizationsList.count()):
            item = self.ui.polarizationsList.item(index)
            item.setSelected(False)
        logger.debug("Cleared all polarizations in dialog")

    def get_if_object(self) -> IF:
        """Retrieve the modified IF object from the dialog."""
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
                logger.error("Polarizations mix different groups")
                raise ValueError("Polarizations must belong to a single group (circular or single linear)")

        self.if_obj.set({
            "frequency": frequency,
            "bandwidth": bandwidth,
            "polarizations": polarizations,
            "isactive": isactive
        })
        logger.debug("Updated IF object '%s' with frequency=%s, bandwidth=%s, polarizations=%s, isactive=%s", self.if_obj.name, frequency, bandwidth, polarizations, isactive)
        return self.if_obj

    def accept(self):
        """Validate and accept the dialog."""
        try:
            frequency = self.ui.frequencyEdit.value()
            bandwidth = self.ui.bandwidthEdit.value()
            if frequency <= 0:
                logger.error("Frequency must be positive")
                QMessageBox.critical(self, "Error", "Frequency must be positive.")
                return
            if bandwidth <= 0:
                logger.error("Bandwidth must be positive")
                QMessageBox.critical(self, "Error", "Bandwidth must be positive.")
                return
            self.get_if_object()
            super().accept()
            logger.info("Validated and saved IF data for '%s'", self.if_obj.name)
        except ValueError as ve:
            logger.error("Validation error: %s", str(ve))
            QMessageBox.critical(self, "Error", f"Invalid input: {str(ve)}")
        except Exception as e:
            logger.error("Unexpected error while saving IF: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to save IF: {str(e)}")