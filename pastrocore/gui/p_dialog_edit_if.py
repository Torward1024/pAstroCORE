# pastrocore/gui/p_dialog_edit_if.py
import uuid

from PySide6.QtWidgets import QDialog, QMessageBox

from msb_arch.utils.logging_setup import logger

from pastrocore.base.frequencies import IF, VALID_POLARIZATIONS
from pastrocore.gui.ui_dialog_edit_if import Ui_IFEditorDialog


class IFEditorDialog(QDialog):
    """Editing one band: its sky frequency, its width, and what it records there.

    Notes:
        - **What it covers is shown while it is being edited.** `frequency` is an edge rather
          than a middle, so 4828 upper and 4844 lower are the same 16 MHz written two ways --
          and a project holding both is refused with a message about a rule rather than about
          the two numbers on screen. Showing the span turns that from a puzzle into something
          visible before Save is pressed.
        - The two lists are filled from the model's own constants. A polarization added there
          appears here without this form being touched, and the form cannot offer one the model
          would refuse.
    """

    def __init__(self, if_obj: IF = None, parent=None):
        super().__init__(parent)
        self.ui = Ui_IFEditorDialog()
        self.ui.setupUi(self)
        self.if_obj = if_obj
        self._offer_choices()
        self.setup_connections()
        self.load_data()

    def _offer_choices(self):
        """Fill the two lists from the model, replacing what the form was drawn with.

        Notes:
            - The form carries the same items so that it is not empty in Designer. They are
              replaced here, because a list in a form is a second place for the answer to live
              and the two disagree the first time one changes.
        """
        for widget, offered in ((self.ui.polarizationsList, VALID_POLARIZATIONS),
                                (self.ui.sidebandsList, IF.VALID_SIDEBANDS)):
            widget.clear()
            widget.addItems(list(offered))

    def setup_connections(self):
        """Connect UI signals to slots."""
        self.ui.frequencyEdit.valueChanged.connect(self.update_derived)
        self.ui.bandwidthEdit.valueChanged.connect(self.update_derived)
        self.ui.sidebandsList.itemSelectionChanged.connect(self.update_derived)
        self.ui.clearPolarizationsButton.clicked.connect(self.clear_selections)
        self.ui.saveButton.clicked.connect(self.accept)
        self.ui.cancelButton.clicked.connect(self.reject)

    def load_data(self):
        """Load IF data into the dialog fields."""
        if not self.if_obj:
            self.if_obj = IF(name=f"if_{uuid.uuid4().hex[:32]}", frequency=1000.0,
                             bandwidth=16.0, polarizations=[], isactive=True)
            self.setWindowTitle("Add Intermediate Frequency")
            logger.debug("Creating new IF")
        else:
            self.setWindowTitle("Edit Intermediate Frequency")
            logger.debug("Editing existing IF '%s'", self.if_obj.name)

        self.ui.frequencyEdit.setValue(self.if_obj.frequency)
        self.ui.bandwidthEdit.setValue(self.if_obj.bandwidth)
        self.ui.isActiveCheckBox.setChecked(self.if_obj.isactive)
        self._select(self.ui.polarizationsList, self.if_obj.polarizations)
        self._select(self.ui.sidebandsList, self.if_obj.get_sidebands())

        self.update_derived()
        logger.info("Loaded IF '%s' into editor dialog", self.if_obj.name)

    @staticmethod
    def _select(widget, chosen):
        """Tick whatever the band already has."""
        for index in range(widget.count()):
            item = widget.item(index)
            item.setSelected(item.text() in (chosen or []))

    @staticmethod
    def _selected(widget):
        """Return what is ticked, in the order the list offers it."""
        return [widget.item(index).text() for index in range(widget.count())
                if widget.item(index).isSelected()]

    def update_derived(self):
        """Update the wavelength and the covered span from what is on screen.

        Notes:
            - The span is asked of `IF.band_of` rather than worked out here. It is the one
              place a sideband becomes numbers, and a second place would be a second chance to
              get the direction wrong.
        """
        frequency = self.ui.frequencyEdit.value()
        bandwidth = self.ui.bandwidthEdit.value()
        sidebands = self._selected(self.ui.sidebandsList)

        if frequency <= 0:
            self.ui.wavelengthDisplay.setText("N/A")
            self.ui.coverageDisplay.setText("N/A")
            logger.warning("Frequency is non-positive, wavelength set to N/A")
            return

        self.ui.wavelengthDisplay.setText(f"{29979.2458 / frequency:.3f}")

        if not sidebands:
            self.ui.coverageDisplay.setText("no sideband chosen")
            return
        low, high = IF.band_of(frequency, bandwidth, sidebands)
        self.ui.coverageDisplay.setText(f"{low:.3f} - {high:.3f}")

    def clear_selections(self):
        """Unselect every polarization and sideband."""
        for widget in (self.ui.polarizationsList, self.ui.sidebandsList):
            for index in range(widget.count()):
                widget.item(index).setSelected(False)
        self.update_derived()
        logger.debug("Cleared the polarizations and sidebands in the dialog")

    def get_if_object(self) -> IF:
        """Write what is on screen into the IF and return it.

        Notes:
            - No validation of its own. `polarizations` mixing circular and linear is refused
              by the model's own rule, wherever it is written from -- this dialog, a file, a
              command line -- and repeating it here would be a second version of it to keep
              in step.
        """
        self.if_obj.set({
            "frequency": self.ui.frequencyEdit.value(),
            "bandwidth": self.ui.bandwidthEdit.value(),
            "polarizations": self._selected(self.ui.polarizationsList),
            "sidebands": self._selected(self.ui.sidebandsList),
            "isactive": self.ui.isActiveCheckBox.isChecked(),
        })
        logger.debug("Updated IF '%s': %s MHz, %s MHz wide, %s, %s", self.if_obj.name,
                     self.if_obj.frequency, self.if_obj.bandwidth,
                     self.if_obj.polarizations, self.if_obj.sidebands)
        return self.if_obj

    def accept(self):
        """Validate and accept the dialog."""
        try:
            if self.ui.frequencyEdit.value() <= 0:
                logger.error("Frequency must be positive")
                QMessageBox.critical(self, "Error", "Frequency must be positive.")
                return
            if self.ui.bandwidthEdit.value() <= 0:
                logger.error("Bandwidth must be positive")
                QMessageBox.critical(self, "Error", "Bandwidth must be positive.")
                return
            if not self._selected(self.ui.sidebandsList):
                logger.error("No sideband chosen")
                QMessageBox.critical(
                    self, "Error",
                    "Choose at least one sideband.\n\n"
                    "It says which way the band runs from its sky frequency, and without it "
                    "there is no answer to what this setting records.")
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
