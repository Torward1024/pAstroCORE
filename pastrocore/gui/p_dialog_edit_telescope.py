# pastrocore/gui/p_dialog_edit_telescope.py
from PySide6.QtWidgets import QDialog, QMessageBox
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from pastrocore.gui.p_table_models import model_for
from pastrocore.gui.ui_dialog_edit_telescope import Ui_TelescopeEditorDialog
from pastrocore.base.telescope import Telescope, MountType
import re
from msb_arch.utils.logging_setup import logger

class TelescopeEditorDialog(QDialog):
    """Dialog for editing or adding Telescope objects."""
    def __init__(self, telescope: Telescope = None, parent=None):
        super().__init__(parent)
        self.ui = Ui_TelescopeEditorDialog()
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
        self.ui.saveButton.clicked.connect(self.accept)
        self.ui.cancelButton.clicked.connect(self.reject)

    def load_data(self):
        """Load telescope data into the dialog fields."""
        if not self.telescope:
            self.telescope = Telescope(
                code=f"NT",
                name=f"NEWTELESCOPE",
                x=0.0, y=0.0, z=0.0,
                vx=0.0, vy=0.0, vz=0.0,
                diameter=25.0,
                elevation_range=(0, 90),
                azimuth_range=(0, 360),
                mount_type=MountType.AZIMUTHAL,
                isactive=True
            )
            self.ui.codeEdit.setReadOnly(False)
            self.ui.nameEdit.setReadOnly(False)
            self.setWindowTitle("Add Telescope")
            logger.debug("Creating new telescope with editable code and name fields")
        else:
            self.ui.codeEdit.setReadOnly(True)
            self.ui.nameEdit.setReadOnly(True)
            self.setWindowTitle(f"Edit Telescope '{self.telescope.get_code()}'")
            logger.debug("Editing existing telescope '%s' with read-only code and name fields", self.telescope.get_code())

        self.ui.codeEdit.setText(self.telescope.get_code() or "")
        self.ui.nameEdit.setText(self.telescope.name or "")
        self.ui.xEdit.setValue(self.telescope.x)
        self.ui.yEdit.setValue(self.telescope.y)
        self.ui.zEdit.setValue(self.telescope.z)
        self.ui.vxEdit.setValue(self.telescope.vx)
        self.ui.vyEdit.setValue(self.telescope.vy)
        self.ui.vzEdit.setValue(self.telescope.vz)
        self.ui.diameterEdit.setValue(self.telescope.diameter)
        self.ui.surfaceAccuracyEdit.setValue(self.telescope.surface_accuracy or 0.0)
        self.ui.elevationMinEdit.setValue(self.telescope.elevation_range[0])
        self.ui.elevationMaxEdit.setValue(self.telescope.elevation_range[1])
        self.ui.azimuthMinEdit.setValue(self.telescope.azimuth_range[0])
        self.ui.azimuthMaxEdit.setValue(self.telescope.azimuth_range[1])
        self.ui.mountTypeCombo.setCurrentText(self.telescope.mount_type.value)
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

        logger.info("Loaded telescope '%s' into editor dialog", self.telescope.get_code())

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

    def get_telescope_object(self) -> Telescope:
        """Retrieve the modified Telescope object from the dialog."""
        mount_type_str = self.ui.mountTypeCombo.currentText()
        try:
            mount_type = MountType._value2member_map_[mount_type_str.upper()]
            logger.debug("Converted mount_type '%s' to %s", mount_type_str, mount_type)
        except KeyError as e:
            logger.error("Invalid mount_type value: %s", mount_type_str)
            raise ValueError(f"Invalid mount_type value: {mount_type_str}") from e

        params = {
            "code": self.ui.codeEdit.text().strip(),
            "name": self.ui.nameEdit.text().strip(),
            "x": self.ui.xEdit.value(),
            "y": self.ui.yEdit.value(),
            "z": self.ui.zEdit.value(),
            "vx": self.ui.vxEdit.value(),
            "vy": self.ui.vyEdit.value(),
            "vz": self.ui.vzEdit.value(),
            "diameter": self.ui.diameterEdit.value(),
            "surface_accuracy": self.ui.surfaceAccuracyEdit.value() or None,
            "elevation_range": (self.ui.elevationMinEdit.value(), self.ui.elevationMaxEdit.value()),
            "azimuth_range": (self.ui.azimuthMinEdit.value(), self.ui.azimuthMaxEdit.value()),
            "mount_type": mount_type,
            "isactive": self.ui.isActiveCheckBox.isChecked(),
            "sefd_table": self.sefd_model.get_data(),
            "surface_efficiency_table": self.surface_efficiency_model.get_data(),
            "effective_area_table": self.effective_area_model.get_data(),
            "system_temperature_table": self.system_temperature_model.get_data()
        }

        self.telescope.set(params)
        logger.debug("Updated Telescope object '%s' with params: %s", self.telescope.name, params)
        return self.telescope

    def refusal(self) -> str:
        """Return why what is on screen cannot be saved, or an empty string.

        Notes:
            - Asked of the fields before anything is written: the station this dialog is
              handed is the one the observation holds.
            - A range low to high and a positive diameter are the model's own rules, restated
              here only because a refused `set` leaves the fields already written (G16).
        """
        code = self.ui.codeEdit.text().strip()
        if not code or not self.ui.nameEdit.text().strip():
            return "Code and Name are required fields."
        if not re.match(r'^[a-zA-Z0-9_-]+$', code):
            return ("Code must contain only alphanumeric characters, underscores, or hyphens.\n\n"
                    "It is written as it stands into a schedule a correlator reads.")
        if self.ui.elevationMinEdit.value() > self.ui.elevationMaxEdit.value():
            return "The elevation range runs from its lowest to its highest."
        if self.ui.azimuthMinEdit.value() > self.ui.azimuthMaxEdit.value():
            return "The azimuth range runs from its lowest to its highest."
        if self.ui.diameterEdit.value() <= 0:
            return "Diameter must be positive."
        return ""

    def accept(self):
        """Validate and accept the dialog."""
        try:
            refusal = self.refusal()
            if refusal:
                logger.error("Telescope cannot be saved: %s", refusal)
                QMessageBox.critical(self, "Error", refusal)
                return
            telescope = self.get_telescope_object()
            super().accept()
            logger.info("Validated and saved telescope data for '%s'", telescope.get_code())
        except ValueError as ve:
            logger.error("Validation error: %s", str(ve))
            QMessageBox.critical(self, "Error", f"Invalid input: {str(ve)}")
        except Exception as e:
            logger.error("Unexpected error while saving telescope: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to save telescope: {str(e)}")