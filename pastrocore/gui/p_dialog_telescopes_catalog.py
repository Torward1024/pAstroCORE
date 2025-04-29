from PySide6.QtWidgets import QDialog, QMessageBox, QHeaderView
from PySide6.QtCore import Slot, Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem
from pastrocore.gui.ui_dialog_catalog import Ui_CatalogDialog
from pastrocore.utils.catalogmanager import CatalogManager
from common.utils.logging_setup import logger

class TelescopesCatalogDialog(QDialog):
    """Dialog for browsing the telescopes catalog."""

    def __init__(self, catalog_manager: CatalogManager, parent=None):
        """Initialize the telescopes catalog dialog.

        Args:
            catalog_manager (CatalogManager): The catalog manager containing telescope data.
            parent (QWidget, optional): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.ui = Ui_CatalogDialog()
        self.ui.setupUi(self)
        self.catalog_manager = catalog_manager
        self.model = QStandardItemModel(self)
        self.setWindowTitle("Telescopes Catalog Browser")
        self.setup_ui()
        self.setup_connections()
        self.populate_table()

    def setup_ui(self):
        """Set up the UI components."""
        self.ui.catalogTable.setModel(self.model)
        self.model.setHorizontalHeaderLabels(["Code", "Name", "X (m)", "Y (m)", "Z (m)", "Diameter (m)"])
        self.ui.catalogTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ui.lbl_search.setText("Search by Code or Name:")

    def setup_connections(self):
        """Connect UI signals to slots."""
        self.ui.closeButton.clicked.connect(self.accept)
        self.ui.search.textChanged.connect(self.filter_telescopes)

    def populate_table(self):
        """Populate the table with telescopes from the catalog manager."""
        self.model.removeRows(0, self.model.rowCount())
        telescopes = self.catalog_manager.telescope_catalog.get_items()  # Используем get_items()

        if not telescopes:
            logger.warning("Telescopes catalog is empty")
            QMessageBox.warning(self, "Warning", "Telescopes catalog is empty.")
            return

        for telescope in telescopes:
            items = [
                QStandardItem(telescope.code or ""),
                QStandardItem(telescope.name or ""),
                QStandardItem(f"{telescope.x:.2f}"),
                QStandardItem(f"{telescope.y:.2f}"),
                QStandardItem(f"{telescope.z:.2f}"),
                QStandardItem(f"{telescope.diameter:.2f}")
            ]
            for item in items:
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.model.appendRow(items)

        logger.info(f"Populated telescopes catalog table with {len(telescopes)} telescopes")

    @Slot(str)
    def filter_telescopes(self, text: str):
        """Filter telescopes in the table based on search text.

        Args:
            text (str): The search text to filter by code or name.
        """
        text = text.lower().strip()
        self.model.removeRows(0, self.model.rowCount())
        telescopes = self.catalog_manager.telescope_catalog.get_items()  # Используем get_items()

        for telescope in telescopes:
            if (text in (telescope.code or "").lower() or
                text in (telescope.name or "").lower()):
                items = [
                    QStandardItem(telescope.code or ""),
                    QStandardItem(telescope.name or ""),
                    QStandardItem(f"{telescope.x:.2f}"),
                    QStandardItem(f"{telescope.y:.2f}"),
                    QStandardItem(f"{telescope.z:.2f}"),
                    QStandardItem(f"{telescope.diameter:.2f}")
                ]
                for item in items:
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.model.appendRow(items)

        logger.info(f"Filtered telescopes catalog with search text '{text}', {self.model.rowCount()} telescopes displayed")