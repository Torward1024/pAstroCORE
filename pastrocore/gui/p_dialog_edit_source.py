from PySide6.QtWidgets import QDialog, QMessageBox, QTableView, QHeaderView
from PySide6.QtCore import Slot
from PySide6.QtGui import QStandardItemModel, QStandardItem
from pastrocore.gui.ui_dialog_edit_source import Ui_SourceEditorDialog
from pastrocore.base.sources import Source
from common.utils.logging_setup import logger

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
        if source_obj:
            self.load_source_data(source_obj)
            self.ui.nameEdit.setReadOnly(True)
            logger.debug(f"Editing existing source '{source_obj.name}' with read-only name field")
        else:
            self.ui.nameEdit.setReadOnly(False)
            logger.debug("Creating new source with editable name field")

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
        self.ui.saveButton.clicked.connect(self.validate_and_save)
        self.ui.cancelButton.clicked.connect(self.reject)

    def load_source_data(self, source: Source):
        """Load source data into the dialog fields."""
        self.ui.nameEdit.setText(source.name or "")
        self.ui.nameJ2000Edit.setText(source.name_J2000 or "")
        self.ui.altNameEdit.setText(source.alt_name or "")
        self.ui.raHEdit.setValue(source.ra_h)
        self.ui.raMEdit.setValue(source.ra_m)
        self.ui.raSEdit.setValue(source.ra_s)
        self.ui.deDEdit.setValue(source.de_d)
        self.ui.deMEdit.setValue(source.de_m)
        self.ui.deSEdit.setValue(source.de_s)
        self.ui.spectralIndexEdit.setValue(source.spectral_index or 0)
        self.ui.isActiveCheckBox.setChecked(source.isactive)

        # Populate flux table
        self.model.removeRows(0, self.model.rowCount())
        for freq, flux in source.flux_table.items():
            freq_item = QStandardItem(f"{freq:.2f}")
            flux_item = QStandardItem(f"{flux:.2f}")
            freq_item.setEditable(True)
            flux_item.setEditable(True)
            self.model.appendRow([freq_item, flux_item])

        logger.info(f"Loaded source '{source.name}' into editor dialog")

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

    @Slot()
    def validate_and_save(self):
        """Validate input and save the source data."""
        try:
            name = self.ui.nameEdit.text().strip()
            if not name:
                raise ValueError("Source name cannot be empty")

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
                "name": name,
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

            Source(**source_data)
            self._source_data = source_data
            self.accept()
            logger.info(f"Validated and saved source data for '{name}'")
        except ValueError as ve:
            logger.error(f"Validation error: {str(ve)}")
            QMessageBox.critical(self, "Error", f"Invalid input: {str(ve)}")
        except Exception as e:
            logger.error(f"Unexpected error while saving source: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save source: {str(e)}")

    def get_source_data(self):
        """Return the source data."""
        return getattr(self, '_source_data', {})