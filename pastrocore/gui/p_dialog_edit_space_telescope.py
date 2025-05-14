from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from pastrocore.gui.ui_dialog_edit_space_telescope import Ui_SpaceTelescopeEditorDialog
from astropy.time import Time
from common.utils.logging_setup import logger
import re

class SEFDTableModel(QAbstractTableModel):
    """Table model for SEFD (MHz, Jy) data."""
    def __init__(self, data=None):
        super().__init__()
        self._data = data if data else []

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return 2

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return str(self._data[index.row()][index.column()])
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            try:
                val = float(value)
                if index.column() == 0 and val <= 0:
                    return False
                if index.column() == 1 and val < 0:
                    return False
                self._data[index.row()][index.column()] = val
                self.dataChanged.emit(index, index)
                return True
            except ValueError:
                return False
        return False

    def flags(self, index):
        return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return ["Frequency (MHz)", "SEFD (Jy)"][section]
        return None

    def add_row(self, frequency=1000.0, sefd=1000.0):
        self.beginInsertRows(QModelIndex(), len(self._data), len(self._data))
        self._data.append([frequency, sefd])
        self.endInsertRows()

    def remove_row(self, row):
        self.beginRemoveRows(QModelIndex(), row, row)
        del self._data[row]
        self.endRemoveRows()

    def clear(self):
        self.beginResetModel()
        self._data = []
        self.endResetModel()

    def get_data(self):
        return {row[0]: row[1] for row in self._data}

class SurfaceEfficiencyTableModel(SEFDTableModel):
    """Table model for Surface Efficiency (MHz, Efficiency) data."""
    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return ["Frequency (MHz)", "Efficiency"][section]
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            try:
                val = float(value)
                if index.column() == 0 and val <= 0:
                    return False
                if index.column() == 1 and (val < 0 or val > 1):
                    return False
                self._data[index.row()][index.column()] = val
                self.dataChanged.emit(index, index)
                return True
            except ValueError:
                return False
        return False

class EffectiveAreaTableModel(SEFDTableModel):
    """Table model for Effective Area (MHz, m²) data."""
    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return ["Frequency (MHz)", "Area (m²)"][section]
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            try:
                val = float(value)
                if index.column() == 0 and val <= 0:
                    return False
                if index.column() == 1 and val < 0:
                    return False
                self._data[index.row()][index.column()] = val
                self.dataChanged.emit(index, index)
                return True
            except ValueError:
                return False
        return False

class SystemTemperatureTableModel(SEFDTableModel):
    """Table model for System Temperature (MHz, K) data."""
    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return ["Frequency (MHz)", "Temperature (K)"][section]
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            try:
                val = float(value)
                if index.column() == 0 and val <= 0:
                    return False
                if index.column() == 1 and val < 0:
                    return False
                self._data[index.row()][index.column()] = val
                self.dataChanged.emit(index, index)
                return True
            except ValueError:
                return False
        return False

class SpaceTelescopeEditorDialog(QDialog):
    """Dialog for editing SpaceTelescope objects."""
    def __init__(self, telescope=None, parent=None):
        super().__init__(parent)
        self.ui = Ui_SpaceTelescopeEditorDialog()
        self.ui.setupUi(self)
        self.telescope = telescope
        self.setup_models()
        self.setup_connections()
        if telescope:
            self.load_telescope_data()
            self.ui.codeEdit.setReadOnly(True)
            self.ui.nameEdit.setReadOnly(True)
            logger.debug(f"Editing existing space telescope '{telescope.get_code()}' with read-only name and code fields")
        else:
            self.ui.codeEdit.setReadOnly(False)
            self.ui.nameEdit.setReadOnly(False)
            logger.debug("Creating new space telescope with editable name and code fields")

    def setup_models(self):
        """Initialize table models."""
        self.sefd_model = SEFDTableModel()
        self.ui.sefdTable.setModel(self.sefd_model)
        self.surface_efficiency_model = SurfaceEfficiencyTableModel()
        self.ui.surfaceEfficiencyTable.setModel(self.surface_efficiency_model)
        self.effective_area_model = EffectiveAreaTableModel()
        self.ui.effectiveAreaTable.setModel(self.effective_area_model)
        self.system_temperature_model = SystemTemperatureTableModel()
        self.ui.systemTemperatureTable.setModel(self.system_temperature_model)

    def setup_connections(self):
        """Connect button signals."""
        self.ui.browseOrbitFileButton.clicked.connect(self.browse_orbit_file)
        self.ui.addSefdButton.clicked.connect(lambda: self.sefd_model.add_row())
        self.ui.removeSefdButton.clicked.connect(self.remove_sefd_row)
        self.ui.clearSefdButton.clicked.connect(self.sefd_model.clear)
        self.ui.addSurfaceEfficiencyButton.clicked.connect(lambda: self.surface_efficiency_model.add_row(frequency=1000.0, sefd=0.8))
        self.ui.removeSurfaceEfficiencyButton.clicked.connect(self.remove_surface_efficiency_row)
        self.ui.clearSurfaceEfficiencyButton.clicked.connect(self.surface_efficiency_model.clear)
        self.ui.addEffectiveAreaButton.clicked.connect(lambda: self.effective_area_model.add_row())
        self.ui.removeEffectiveAreaButton.clicked.connect(self.remove_effective_area_row)
        self.ui.clearEffectiveAreaButton.clicked.connect(self.effective_area_model.clear)
        self.ui.addSystemTemperatureButton.clicked.connect(lambda: self.system_temperature_model.add_row(frequency=1000.0, sefd=300.0))
        self.ui.removeSystemTemperatureButton.clicked.connect(self.remove_system_temperature_row)
        self.ui.clearSystemTemperatureButton.clicked.connect(self.system_temperature_model.clear)

    def browse_orbit_file(self):
        """Open file dialog to select orbit file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Orbit File", "", "All Files (*.*)")
        if file_path:
            self.ui.orbitFileEdit.setText(file_path)

    def load_telescope_data(self):
        """Load existing telescope data into the dialog."""
        self.ui.codeEdit.setText(self.telescope.get_code())
        self.ui.nameEdit.setText(self.telescope.name)
        self.ui.diameterEdit.setValue(self.telescope.diameter)
        self.ui.surfaceAccuracyEdit.setValue(self.telescope.surface_accuracy or 0.0)
        self.ui.orbitFileEdit.setText(self.telescope.orbit_file or "")
        self.ui.interpolationMethodCombo.setCurrentText(self.telescope.interpolation_method)
        self.ui.pitchMinEdit.setValue(self.telescope.pitch_range[0])
        self.ui.pitchMaxEdit.setValue(self.telescope.pitch_range[1])
        self.ui.yawMinEdit.setValue(self.telescope.yaw_range[0])
        self.ui.yawMaxEdit.setValue(self.telescope.yaw_range[1])
        self.ui.useKepCheckBox.setChecked(self.telescope.use_kep)
        self.ui.isActiveCheckBox.setChecked(self.telescope.isactive)
        
        if self.telescope.use_kep and self.telescope.kepler_elements:
            self.ui.semiMajorAxisEdit.setValue(self.telescope.kepler_elements["semi_major_axis"])
            self.ui.eccentricityEdit.setValue(self.telescope.kepler_elements["eccentricity"])
            self.ui.inclinationEdit.setValue(self.telescope.kepler_elements["inclination"])
            self.ui.raanEdit.setValue(self.telescope.kepler_elements["raan"])
            self.ui.argpEdit.setValue(self.telescope.kepler_elements["argp"])
            self.ui.nuEdit.setValue(self.telescope.kepler_elements["nu"])
            self.ui.epochEdit.setDateTime(self.telescope.kepler_elements["epoch"])
            self.ui.muEdit.setValue(self.telescope.kepler_elements["mu"])
        
        if self.telescope.sefd_table:
            for freq, sefd in self.telescope.sefd_table.items():
                self.sefd_model.add_row(freq, sefd)
        if self.telescope.surface_efficiency_table:
            for freq, eff in self.telescope.surface_efficiency_table.items():
                self.surface_efficiency_model.add_row(freq, eff)
        if self.telescope.effective_area_table:
            for freq, area in self.telescope.effective_area_table.items():
                self.effective_area_model.add_row(freq, area)
        if self.telescope.system_temperature_table:
            for freq, temp in self.telescope.system_temperature_table.items():
                self.system_temperature_model.add_row(freq, temp)

    def remove_sefd_row(self):
        selected = self.ui.sefdTable.selectionModel().selectedRows()
        if selected:
            self.sefd_model.remove_row(selected[0].row())

    def remove_surface_efficiency_row(self):
        selected = self.ui.surfaceEfficiencyTable.selectionModel().selectedRows()
        if selected:
            self.surface_efficiency_model.remove_row(selected[0].row())

    def remove_effective_area_row(self):
        selected = self.ui.effectiveAreaTable.selectionModel().selectedRows()
        if selected:
            self.effective_area_model.remove_row(selected[0].row())

    def remove_system_temperature_row(self):
        selected = self.ui.systemTemperatureTable.selectionModel().selectedRows()
        if selected:
            self.system_temperature_model.remove_row(selected[0].row())

    def get_telescope_data(self):
        """Retrieve telescope data from the dialog."""
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
        
        return {
            "code": self.ui.codeEdit.text().strip(),
            "name": self.ui.nameEdit.text().strip(),
            "diameter": self.ui.diameterEdit.value(),
            "surface_accuracy": self.ui.surfaceAccuracyEdit.value(),
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

    def accept(self):
        """Validate and accept the dialog."""
        data = self.get_telescope_data()
        if not data["code"] or not data["name"]:
            QMessageBox.critical(self, "Error", "Code and Name are required fields.")
            return
        if not re.match(r'^[a-zA-Z0-9_-]+$', data["code"]):
            QMessageBox.critical(self, "Error", "Code must contain only alphanumeric characters, underscores, or hyphens.")
            return
        if data["pitch_range"][0] >= data["pitch_range"][1]:
            QMessageBox.critical(self, "Error", "Minimum pitch must be less than maximum pitch.")
            return
        if data["yaw_range"][0] >= data["yaw_range"][1]:
            QMessageBox.critical(self, "Error", "Minimum yaw must be less than maximum yaw.")
            return
        if data["use_kep"] and not data["kepler_elements"]:
            QMessageBox.critical(self, "Error", "Keplerian elements are required when using Keplerian orbit.")
            return
        if not data["use_kep"] and not data["orbit_file"]:
            QMessageBox.critical(self, "Error", "An orbit file is required when not using Keplerian elements.")
            return
        super().accept()