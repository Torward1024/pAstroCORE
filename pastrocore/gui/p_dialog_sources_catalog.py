from PySide6.QtWidgets import QDialog, QMessageBox, QHeaderView, QPushButton, QAbstractItemView
from PySide6.QtCore import Slot, Qt, Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem
from pastrocore.gui.ui_dialog_catalog import Ui_CatalogDialog
from pastrocore.utils.catalogmanager import CatalogManager
from common.utils.logging_setup import logger

class SourcesCatalogDialog(QDialog):
    """Dialog for browsing the sources catalog."""
    source_selected = Signal(object)  # Signal to emit selected source

    def __init__(self, catalog_manager: CatalogManager, parent=None, allow_selection: bool = False):
        """Initialize the sources catalog dialog.

        Args:
            catalog_manager (CatalogManager): The catalog manager containing source data.
            parent (QWidget, optional): Parent widget. Defaults to None.
            allow_selection (bool, optional): If True, enables source selection mode with 'Add' button.
        """
        super().__init__(parent)
        self.ui = Ui_CatalogDialog()
        self.ui.setupUi(self)
        self.catalog_manager = catalog_manager
        self.model = QStandardItemModel(self)
        self.allow_selection = allow_selection
        self.selected_source = None
        self.setWindowTitle("Sources Catalog Browser")
        self.setup_ui()
        self.setup_connections()
        self.populate_table()

    def setup_ui(self):
        """Set up the UI components."""
        self.ui.catalogTable.setModel(self.model)
        self.model.setHorizontalHeaderLabels(["Name (B1950)", "J2000 Name", "Alt Name", "RA (hh:mm:ss.s)", "DEC (dd:mm:ss.s)"])
        self.ui.catalogTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ui.lbl_search.setText("Search by Name:")
        
        if self.allow_selection:
            self.ui.catalogTable.setSelectionMode(QAbstractItemView.SingleSelection)
            self.ui.catalogTable.setSelectionBehavior(QAbstractItemView.SelectRows)
            # Add 'Add' button
            self.add_button = QPushButton("Add", self)
            self.add_button.setStyleSheet("""
                QPushButton {
                    background-color: #0078d7;
                    color: #ffffff;
                    padding: 6px;
                    border-radius: 3px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #1a8cff;
                }
                QPushButton:pressed {
                    background-color: #005bb5;
                    padding-top: 7px;
                    padding-bottom: 5px;
                }
            """)
            # Remove horizontalSpacer from gridLayout to free up space
            self.ui.gridLayout.removeItem(self.ui.horizontalSpacer)
            # Add 'Add' button to gridLayout at position (1, 2)
            self.ui.gridLayout.addWidget(self.add_button, 1, 2, 1, 1)
            # Move closeButton to (1, 3) (it should already be there, but ensure consistency)
            self.ui.gridLayout.addWidget(self.ui.closeButton, 1, 3, 1, 1)

    def setup_connections(self):
        """Connect UI signals to slots."""
        self.ui.closeButton.clicked.connect(self.reject)
        self.ui.search.textChanged.connect(self.filter_sources)
        if self.allow_selection:
            self.add_button.clicked.connect(self.select_source)

    def populate_table(self):
        """Populate the table with sources from the catalog manager."""
        self.model.removeRows(0, self.model.rowCount())
        sources = self.catalog_manager.source_catalog.get_items()

        if not sources:
            logger.warning("Sources catalog is empty")
            QMessageBox.warning(self, "Warning", "Sources catalog is empty.")
            return

        for source in sources:
            ra_str = f"{int(source.ra_h):02d}:{int(source.ra_m):02d}:{source.ra_s:05.1f}"
            dec_sign = "+" if source.de_d >= 0 else "-"
            dec_str = f"{dec_sign}{abs(int(source.de_d)):02d}:{int(source.de_m):02d}:{source.de_s:05.1f}"
            items = [
                QStandardItem(source.name or ""),
                QStandardItem(source.name_J2000 or ""),
                QStandardItem(source.alt_name or ""),
                QStandardItem(ra_str),
                QStandardItem(dec_str)
            ]
            for item in items:
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.model.appendRow(items)

        logger.info(f"Populated sources catalog table with {len(sources)} sources")

    @Slot(str)
    def filter_sources(self, text: str):
        """Filter sources in the table based on search text.

        Args:
            text (str): The search text to filter by name, J2000 name, or alt name.
        """
        text = text.lower().strip()
        self.model.removeRows(0, self.model.rowCount())
        sources = self.catalog_manager.source_catalog.get_items()

        for source in sources:
            if (text in (source.name or "").lower() or
                text in (source.name_J2000 or "").lower() or
                text in (source.alt_name or "").lower()):
                ra_str = f"{int(source.ra_h):02d}:{int(source.ra_m):02d}:{source.ra_s:05.1f}"
                dec_sign = "+" if source.de_d >= 0 else "-"
                dec_str = f"{dec_sign}{abs(int(source.de_d)):02d}:{int(source.de_m):02d}:{source.de_s:05.1f}"
                items = [
                    QStandardItem(source.name or ""),
                    QStandardItem(source.name_J2000 or ""),
                    QStandardItem(source.alt_name or ""),
                    QStandardItem(ra_str),
                    QStandardItem(dec_str)
                ]
                for item in items:
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.model.appendRow(items)

        logger.info(f"Filtered sources catalog with search text '{text}', {self.model.rowCount()} sources displayed")

    @Slot()
    def select_source(self):
        """Handle selection of a source for adding to observation."""
        selected = self.ui.catalogTable.selectionModel().selectedRows()
        if not selected:
            logger.warning("No source selected for adding")
            QMessageBox.warning(self, "Warning", "Please select a source to add.")
            return

        row = selected[0].row()
        source_name = self.model.item(row, 0).text()
        sources = self.catalog_manager.source_catalog.get_items()
        for source in sources:
            if source.name == source_name:
                self.selected_source = source
                self.source_selected.emit(source)
                self.accept()
                logger.info(f"Selected source '{source_name}' for adding to observation")
                return
        logger.error(f"Source '{source_name}' not found in catalog")
        QMessageBox.critical(self, "Error", f"Source '{source_name}' not found in catalog.")