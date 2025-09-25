# pastrocore/gui/p_dialog_edit_telescope.py
from PySide6.QtWidgets import QDialog, QMessageBox
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from pastrocore.gui.ui_dialog_edit_telescope import Ui_TelescopeEditorDialog
from pastrocore.base.telescope import Telescope, MountType
import re
from common.utils.logging_setup import logger

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
        self.sefd_model = SEFDTableModel()
        self.ui.sefdTable.setModel(self.sefd_model)
        self.surface_efficiency_model = SurfaceEfficiencyTableModel()
        self.ui.surfaceEfficiencyTable.setModel(self.surface_efficiency_model)
        self.effective_area_model = EffectiveAreaTableModel()
        self.ui.effectiveAreaTable.setModel(self.effective_area_model)
        self.system_temperature_model = SystemTemperatureTableModel()
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
                mount_type=MountType.AZEL,
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
            logger.debug(f"Editing existing telescope '{self.telescope.get_code()}' with read-only code and name fields")

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
            for freq, sefd in self.telescope.sefd_table.items():
                self.sefd_model.add_row(freq, sefd)
        self.surface_efficiency_model.clear()
        if self.telescope.surface_efficiency_table:
            for freq, eff in self.telescope.surface_efficiency_table.items():
                self.surface_efficiency_model.add_row(freq, eff)
        self.effective_area_model.clear()
        if self.telescope.effective_area_table:
            for freq, area in self.telescope.effective_area_table.items():
                self.effective_area_model.add_row(freq, area)
        self.system_temperature_model.clear()
        if self.telescope.system_temperature_table:
            for freq, temp in self.telescope.system_temperature_table.items():
                self.system_temperature_model.add_row(freq, temp)

        logger.info(f"Loaded telescope '{self.telescope.get_code()}' into editor dialog")

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
            logger.debug(f"Converted mount_type '{mount_type_str}' to {mount_type}")
        except KeyError as e:
            logger.error(f"Invalid mount_type value: {mount_type_str}")
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
        logger.debug(f"Updated Telescope object '{self.telescope.name}' with params: {params}")
        return self.telescope

    def accept(self):
        """Validate and accept the dialog."""
        try:
            data = self.get_telescope_object().__dict__
            if not data["code"] or not data["name"]:
                logger.error("Code and Name are required fields")
                QMessageBox.critical(self, "Error", "Code and Name are required fields.")
                return
            if not re.match(r'^[a-zA-Z0-9_-]+$', data["code"]):
                logger.error("Code must contain only alphanumeric characters, underscores, or hyphens")
                QMessageBox.critical(self, "Error", "Code must contain only alphanumeric characters, underscores, or hyphens.")
                return
            if data["elevation_range"][0] >= data["elevation_range"][1]:
                logger.error("Minimum elevation must be less than maximum elevation")
                QMessageBox.critical(self, "Error", "Minimum elevation must be less than maximum elevation.")
                return
            if data["azimuth_range"][0] >= data["azimuth_range"][1]:
                logger.error("Minimum azimuth must be less than maximum azimuth")
                QMessageBox.critical(self, "Error", "Minimum azimuth must be less than maximum azimuth.")
                return
            if data["diameter"] <= 0:
                logger.error("Diameter must be positive")
                QMessageBox.critical(self, "Error", "Diameter must be positive.")
                return
            super().accept()
            logger.info(f"Validated and saved telescope data for '{data['code']}'")
        except ValueError as ve:
            logger.error(f"Validation error: {str(ve)}")
            QMessageBox.critical(self, "Error", f"Invalid input: {str(ve)}")
        except Exception as e:
            logger.error(f"Unexpected error while saving telescope: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save telescope: {str(e)}")