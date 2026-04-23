# pastrocore/gui/p_dialog_edit_source.py
from PySide6.QtWidgets import QDialog, QMessageBox, QTableView, QHeaderView
from PySide6.QtCore import Slot
from PySide6.QtGui import QStandardItemModel, QStandardItem
from pastrocore.gui.ui_dialog_edit_source import Ui_SourceEditorDialog
from pastrocore.base.sources import Source
from msb_arch.utils.logging_setup import logger

class SourceEditorDialog(QDialog):
    """Dialog for editing or adding a source."""
    def __init__(self, source_obj: Source = None, parent=None):
        super().__init__(parent)
        self.ui = Ui_SourceEditorDialog()
        self.ui.setupUi(self)
        self.source_obj = source_obj
        self.model = QStandardItemModel(self)
        self.setup_ui()
        self.setup_connections()
        self.load_data()

    def setup_ui(self):
        """Set up the UI components."""
        self.ui.fluxTable.setModel(self.model)
        self.model.setHorizontalHeaderLabels(["Frequency (MHz)", "Flux (Jy)"])
        self.ui.fluxTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ui.fluxTable.setSelectionMode(QTableView.SingleSelection)
        self.ui.fluxTable.setSelectionBehavior(QTableView.SelectRows)

        self.ui.raHEdit.setRange(0, 23)
        self.ui.raMEdit.setRange(0, 59)
        self.ui.raSEdit.setRange(0, 59.999)
        self.ui.deDEdit.setRange(-90, 90)
        self.ui.deMEdit.setRange(0, 59)
        self.ui.deSEdit.setRange(0, 59.999)
        self.ui.spectralIndexEdit.setRange(-999, 999)

    def setup_connections(self):
        """Connect UI signals to slots."""
        self.ui.addFluxButton.clicked.connect(self.add_flux)
        self.ui.removeFluxButton.clicked.connect(self.remove_flux)
        self.ui.clearFluxButton.clicked.connect(self.clear_flux_table)
        self.ui.saveButton.clicked.connect(self.accept)
        self.ui.cancelButton.clicked.connect(self.reject)

    def load_data(self):
        """Load source data into the dialog fields."""
        if not self.source_obj:
            self.source_obj = Source(
                name=f"NEWSOURCE",
                ra_h=0.0, ra_m=0.0, ra_s=0.0,
                de_d=0.0, de_m=0.0, de_s=0.0,
                flux_table={},
                isactive=True
            )
            self.ui.nameEdit.setReadOnly(False)
            self.setWindowTitle("Add Source")
            logger.debug("Creating new source with editable name field")
        else:
            self.ui.nameEdit.setReadOnly(True)
            self.setWindowTitle(f"Edit Source '{self.source_obj.name}'")
            logger.debug(f"Editing existing source '{self.source_obj.name}' with read-only name field")

        self.ui.nameEdit.setText(self.source_obj.name or "")
        self.ui.nameJ2000Edit.setText(self.source_obj.name_J2000 or "")
        self.ui.altNameEdit.setText(self.source_obj.alt_name or "")
        self.ui.raHEdit.setValue(self.source_obj.ra_h)
        self.ui.raMEdit.setValue(self.source_obj.ra_m)
        self.ui.raSEdit.setValue(self.source_obj.ra_s)
        self.ui.deDEdit.setValue(self.source_obj.de_d)
        self.ui.deMEdit.setValue(self.source_obj.de_m)
        self.ui.deSEdit.setValue(self.source_obj.de_s)
        self.ui.spectralIndexEdit.setValue(self.source_obj.spectral_index or 0)
        self.ui.isActiveCheckBox.setChecked(self.source_obj.isactive)

        self.model.removeRows(0, self.model.rowCount())
        for freq, flux in self.source_obj.flux_table.items():
            freq_item = QStandardItem(f"{freq:.2f}")
            flux_item = QStandardItem(f"{flux:.2f}")
            freq_item.setEditable(True)
            flux_item.setEditable(True)
            self.model.appendRow([freq_item, flux_item])

        logger.info(f"Loaded source '{self.source_obj.name}' into editor dialog")

    @Slot()
    def add_flux(self):
        """Add a new flux entry to the flux table."""
        freq_item = QStandardItem("1.00")
        flux_item = QStandardItem("1.00")
        freq_item.setEditable(True)
        flux_item.setEditable(True)
        self.model.appendRow([freq_item, flux_item])
        logger.info("Added new flux entry to flux table")

    @Slot()
    def remove_flux(self):
        """Remove selected flux entry from the flux table."""
        selected = self.ui.fluxTable.selectionModel().selectedRows()
        if selected:
            self.model.removeRow(selected[0].row())
            logger.info("Removed selected flux entry from flux table")
        else:
            logger.warning("No flux entry selected for removal")
            QMessageBox.warning(self, "Warning", "Please select a flux entry to remove.")

    @Slot()
    def clear_flux_table(self):
        """Clear all entries from the flux table."""
        self.model.removeRows(0, self.model.rowCount())
        logger.info("Cleared flux table")

    def get_source_object(self) -> Source:
        """Retrieve the modified Source object from the dialog."""
        flux_table = {}
        for row in range(self.model.rowCount()):
            freq_text = self.model.item(row, 0).text()
            flux_text = self.model.item(row, 1).text()
            try:
                freq = float(freq_text)
                flux = float(flux_text)
                if freq <= 0:
                    raise ValueError(f"Frequency at row {row + 1} must be positive")
                if flux <= 0:
                    raise ValueError(f"Flux at row {row + 1} must be positive")
                flux_table[freq] = flux
            except ValueError as e:
                if "must be positive" in str(e):
                    raise
                raise ValueError(f"Invalid flux table entry at row {row + 1}: {str(e)}")

        source_data = {
            "name": self.ui.nameEdit.text().strip(),
            "ra_h": self.ui.raHEdit.value(),
            "ra_m": self.ui.raMEdit.value(),
            "ra_s": self.ui.raSEdit.value(),
            "de_d": self.ui.deDEdit.value(),
            "de_m": self.ui.deMEdit.value(),
            "de_s": self.ui.deSEdit.value(),
            "name_J2000": self.ui.nameJ2000Edit.text().strip() or None,
            "alt_name": self.ui.altNameEdit.text().strip() or None,
            "flux_table": flux_table,
            "spectral_index": self.ui.spectralIndexEdit.value() if self.ui.spectralIndexEdit.value() != 0 else None,
            "isactive": self.ui.isActiveCheckBox.isChecked()
        }

        self.source_obj.set(source_data)
        logger.debug(f"Updated Source object '{self.source_obj.name}' with params: {source_data}")
        return self.source_obj

    def accept(self):
        """Validate and accept the dialog."""
        try:
            name = self.ui.nameEdit.text().strip()
            if not name:
                logger.error("Source name cannot be empty")
                QMessageBox.critical(self, "Error", "Source name cannot be empty.")
                return
            self.get_source_object()
            super().accept()
            logger.info(f"Validated and saved source data for '{name}'")
        except ValueError as ve:
            logger.error(f"Validation error: {str(ve)}")
            QMessageBox.critical(self, "Error", f"Invalid input: {str(ve)}")
        except Exception as e:
            logger.error(f"Unexpected error while saving source: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save source: {str(e)}")