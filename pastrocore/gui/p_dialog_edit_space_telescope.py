# pastrocore/gui/p_dialog_edit_space_telescope.py
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from pastrocore.gui.p_table_models import model_for
from pastrocore.gui.ui_dialog_edit_space_telescope import Ui_SpaceTelescopeEditorDialog
from pastrocore.base.spacetelescope import SpaceTelescope
from astropy.time import Time
from msb_arch.utils.logging_setup import logger
import re

class SpaceTelescopeEditorDialog(QDialog):
    """Dialog for editing or adding SpaceTelescope objects."""
    def __init__(self, telescope: SpaceTelescope = None, parent=None):
        super().__init__(parent)
        self.ui = Ui_SpaceTelescopeEditorDialog()
        self.ui.setupUi(self)
        self.telescope = telescope
        self.setup_models()
        self.setup_connections()
        self.load_data()

    def setup_models(self):
        """Set up table models for SEFD, surface efficiency, effective area, and system temperature."""
        self.sefd_model = model_for("sefd_table")
        self.ui.sefdTable.setModel(self.sefd_model)
        self.surface_efficiency_model = model_for("surface_efficiency_table")
        self.ui.surfaceEfficiencyTable.setModel(self.surface_efficiency_model)
        self.effective_area_model = model_for("effective_area_table")
        self.ui.effectiveAreaTable.setModel(self.effective_area_model)
        self.system_temperature_model = model_for("system_temperature_table")
        self.ui.systemTemperatureTable.setModel(self.system_temperature_model)

    def setup_connections(self):
        """Connect UI signals to slots."""
        self.ui.addSefdButton.clicked.connect(lambda: self.sefd_model.add_row())
        self.ui.removeSefdButton.clicked.connect(self.remove_sefd_row)
        self.ui.clearSefdButton.clicked.connect(self.sefd_model.clear)
        self.ui.addSurfaceEfficiencyButton.clicked.connect(lambda: self.surface_efficiency_model.add_row())
        self.ui.removeSurfaceEfficiencyButton.clicked.connect(self.remove_surface_efficiency_row)
        self.ui.clearSurfaceEfficiencyButton.clicked.connect(self.surface_efficiency_model.clear)
        self.ui.addEffectiveAreaButton.clicked.connect(lambda: self.effective_area_model.add_row())
        self.ui.removeEffectiveAreaButton.clicked.connect(self.remove_effective_area_row)
        self.ui.clearEffectiveAreaButton.clicked.connect(self.effective_area_model.clear)
        self.ui.addSystemTemperatureButton.clicked.connect(lambda: self.system_temperature_model.add_row())
        self.ui.removeSystemTemperatureButton.clicked.connect(self.remove_system_temperature_row)
        self.ui.clearSystemTemperatureButton.clicked.connect(self.system_temperature_model.clear)
        self.ui.browseOrbitFileButton.clicked.connect(self.browse_orbit_file)
        self.ui.saveButton.clicked.connect(self.accept)
        self.ui.cancelButton.clicked.connect(self.reject)

    def browse_orbit_file(self):
        """Open file dialog to select orbit file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Orbit File", "", "Orbit Files (*.txt *.csv)")
        if file_path:
            self.ui.orbitFileEdit.setText(file_path)
            logger.debug("Selected orbit file: %s", file_path)

    def load_data(self):
        """Load space telescope data into the dialog fields."""
        if not self.telescope:
            self.telescope = SpaceTelescope(
                code=f"ST",
                name=f"SPACETELESCOPE",
                diameter=10.0,
                pitch_range=(-90, 90),
                yaw_range=(-180, 180),
                isactive=True
            )
            self.ui.codeEdit.setReadOnly(False)
            self.ui.nameEdit.setReadOnly(False)
            self.setWindowTitle("Add Space Telescope")
            logger.debug("Creating new space telescope with editable code and name fields")
        else:
            self.ui.codeEdit.setReadOnly(True)
            self.ui.nameEdit.setReadOnly(True)
            self.setWindowTitle(f"Edit Space Telescope '{self.telescope.get_code()}'")
            logger.debug("Editing existing space telescope '%s' with read-only code and name fields", self.telescope.get_code())

        self.ui.codeEdit.setText(self.telescope.get_code() or "")
        self.ui.nameEdit.setText(self.telescope.name or "")
        self.ui.diameterEdit.setValue(self.telescope.diameter)
        self.ui.surfaceAccuracyEdit.setValue(self.telescope.surface_accuracy or 0.0)
        self.ui.orbitFileEdit.setText(self.telescope.orbit_file or "")
        self.ui.interpolationMethodCombo.setCurrentText(self.telescope.interpolation_method or "linear")
        self.ui.pitchMinEdit.setValue(self.telescope.pitch_range[0])
        self.ui.pitchMaxEdit.setValue(self.telescope.pitch_range[1])
        self.ui.yawMinEdit.setValue(self.telescope.yaw_range[0])
        self.ui.yawMaxEdit.setValue(self.telescope.yaw_range[1])
        self.ui.useKepCheckBox.setChecked(self.telescope.use_kep)
        if self.telescope.kepler_elements:
            self.ui.semiMajorAxisEdit.setValue(self.telescope.kepler_elements["a"])
            self.ui.eccentricityEdit.setValue(self.telescope.kepler_elements["e"])
            self.ui.inclinationEdit.setValue(self.telescope.kepler_elements["i"])
            self.ui.raanEdit.setValue(self.telescope.kepler_elements["raan"])
            self.ui.argpEdit.setValue(self.telescope.kepler_elements["argp"])
            self.ui.nuEdit.setValue(self.telescope.kepler_elements["nu"])
            self.ui.epochEdit.setDateTime(self.telescope.kepler_elements["epoch"].to_datetime())
            self.ui.muEdit.setValue(self.telescope.kepler_elements["mu"])
        self.ui.isActiveCheckBox.setChecked(self.telescope.isactive)

        self.sefd_model.clear()
        if self.telescope.sefd_table:
            for low, high, sefd in self.telescope.sefd_table:
                self.sefd_model.add_row(low, high, sefd)
        self.surface_efficiency_model.clear()
        if self.telescope.surface_efficiency_table:
            for low, high, eff in self.telescope.surface_efficiency_table:
                self.surface_efficiency_model.add_row(low, high, eff)
        self.effective_area_model.clear()
        if self.telescope.effective_area_table:
            for low, high, area in self.telescope.effective_area_table:
                self.effective_area_model.add_row(low, high, area)
        self.system_temperature_model.clear()
        if self.telescope.system_temperature_table:
            for low, high, temp in self.telescope.system_temperature_table:
                self.system_temperature_model.add_row(low, high, temp)

        logger.info("Loaded space telescope '%s' into editor dialog", self.telescope.get_code())

    def remove_sefd_row(self):
        """Remove selected SEFD entry from the table."""
        selected = self.ui.sefdTable.selectionModel().selectedRows()
        if selected:
            self.sefd_model.remove_row(selected[0].row())
            logger.info("Removed selected SEFD entry from table")
        else:
            logger.warning("No SEFD entry selected for removal")
            QMessageBox.warning(self, "Warning", "Please select an SEFD entry to remove.")

    def remove_surface_efficiency_row(self):
        """Remove selected surface efficiency entry from the table."""
        selected = self.ui.surfaceEfficiencyTable.selectionModel().selectedRows()
        if selected:
            self.surface_efficiency_model.remove_row(selected[0].row())
            logger.info("Removed selected surface efficiency entry from table")
        else:
            logger.warning("No surface efficiency entry selected for removal")
            QMessageBox.warning(self, "Warning", "Please select a surface efficiency entry to remove.")

    def remove_effective_area_row(self):
        """Remove selected effective area entry from the table."""
        selected = self.ui.effectiveAreaTable.selectionModel().selectedRows()
        if selected:
            self.effective_area_model.remove_row(selected[0].row())
            logger.info("Removed selected effective area entry from table")
        else:
            logger.warning("No effective area entry selected for removal")
            QMessageBox.warning(self, "Warning", "Please select an effective area entry to remove.")

    def remove_system_temperature_row(self):
        """Remove selected system temperature entry from the table."""
        selected = self.ui.systemTemperatureTable.selectionModel().selectedRows()
        if selected:
            self.system_temperature_model.remove_row(selected[0].row())
            logger.info("Removed selected system temperature entry from table")
        else:
            logger.warning("No system temperature entry selected for removal")
            QMessageBox.warning(self, "Warning", "Please select a system temperature entry to remove.")

    def get_telescope_object(self) -> SpaceTelescope:
        """Retrieve the modified SpaceTelescope object from the dialog."""
        kepler = None
        if self.ui.useKepCheckBox.isChecked():
            kepler = {
                "a": self.ui.semiMajorAxisEdit.value(),
                "e": self.ui.eccentricityEdit.value(),
                "i": self.ui.inclinationEdit.value(),
                "raan": self.ui.raanEdit.value(),
                "argp": self.ui.argpEdit.value(),
                "nu": self.ui.nuEdit.value(),
                "epoch": Time(self.ui.epochEdit.dateTime().toPython(), scale='utc'),
                "mu": self.ui.muEdit.value()
            }

        params = {
            "code": self.ui.codeEdit.text().strip(),
            "name": self.ui.nameEdit.text().strip(),
            "diameter": self.ui.diameterEdit.value(),
            "surface_accuracy": self.ui.surfaceAccuracyEdit.value() or None,
            "orbit_file": self.ui.orbitFileEdit.text().strip(),
            "interpolation_method": self.ui.interpolationMethodCombo.currentText(),
            "pitch_range": (self.ui.pitchMinEdit.value(), self.ui.pitchMaxEdit.value()),
            "yaw_range": (self.ui.yawMinEdit.value(), self.ui.yawMaxEdit.value()),
            "use_kep": self.ui.useKepCheckBox.isChecked(),
            "kepler_elements": kepler,
            "isactive": self.ui.isActiveCheckBox.isChecked(),
            "sefd_table": self.sefd_model.get_data(),
            "surface_efficiency_table": self.surface_efficiency_model.get_data(),
            "effective_area_table": self.effective_area_model.get_data(),
            "system_temperature_table": self.system_temperature_model.get_data()
        }

        self.telescope.set(params)
        logger.debug("Updated SpaceTelescope object '%s' with params: %s", self.telescope.name, params)
        return self.telescope

    def refusal(self) -> str:
        """Return why what is on screen cannot be saved, or an empty string.

        Notes:
            - **Asked of the fields, before anything is written.** The station this dialog is
              handed is the one the observation holds, and `accept` used to build the object
              to read its `__dict__` -- putting every value on it *first* and refusing
              afterwards. A code with a space in it stayed on the station through the
              refusal, through Cancel, and into a written schedule.
            - A range low to high and a positive diameter are the model's own rules, restated
              here only because a `set` that a constraint refuses leaves the fields it had
              already written (G16). They said `>=` where `_rises` says `<=`, which refused a
              mount fixed at one angle that the model allows.
        """
        code = self.ui.codeEdit.text().strip()
        if not code or not self.ui.nameEdit.text().strip():
            return "Code and Name are required fields."
        if not re.match(r'^[a-zA-Z0-9_-]+$', code):
            return ("Code must contain only alphanumeric characters, underscores, or hyphens.\n\n"
                    "It is written as it stands into a schedule a correlator reads.")
        if self.ui.pitchMinEdit.value() > self.ui.pitchMaxEdit.value():
            return "The pitch range runs from its lowest to its highest."
        if self.ui.yawMinEdit.value() > self.ui.yawMaxEdit.value():
            return "The yaw range runs from its lowest to its highest."
        if not self.ui.useKepCheckBox.isChecked() and not self.ui.orbitFileEdit.text().strip():
            return ("An orbit file is required when the orbit is not given as Keplerian "
                    "elements.")
        if self.ui.diameterEdit.value() <= 0:
            return "Diameter must be positive."
        return ""

    def accept(self):
        """Validate and accept the dialog."""
        try:
            refusal = self.refusal()
            if refusal:
                logger.error("Space telescope cannot be saved: %s", refusal)
                QMessageBox.critical(self, "Error", refusal)
                return
            telescope = self.get_telescope_object()
            super().accept()
            logger.info("Validated and saved space telescope data for '%s'", telescope.get_code())
        except ValueError as ve:
            logger.error("Validation error: %s", str(ve))
            QMessageBox.critical(self, "Error", f"Invalid input: {str(ve)}")
        except Exception as e:
            logger.error("Unexpected error while saving space telescope: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to save space telescope: {str(e)}")