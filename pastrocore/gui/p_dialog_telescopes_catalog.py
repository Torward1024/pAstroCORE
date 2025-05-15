from PySide6.QtWidgets import QDialog, QMessageBox, QHeaderView, QPushButton, QAbstractItemView
from PySide6.QtCore import Slot, Qt, Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem
from pastrocore.gui.ui_dialog_catalog import Ui_CatalogDialog
from pastrocore.utils.catalogmanager import CatalogManager
from common.utils.logging_setup import logger

class TelescopesCatalogDialog(QDialog):
    """Dialog for browsing the telescopes catalog."""
    telescope_selected = Signal(object)  # Signal to emit selected telescope

    def __init__(self, catalog_manager: CatalogManager, parent=None, allow_selection: bool = False):
        """Initialize the telescopes catalog dialog.

        Args:
            catalog_manager (CatalogManager): The catalog manager containing telescope data.
            parent (QWidget, optional): Parent widget. Defaults to None.
            allow_selection (bool, optional): If True, enables telescope selection mode with 'Add' button.
        """
        super().__init__(parent)
        self.ui = Ui_CatalogDialog()
        self.ui.setupUi(self)
        self.catalog_manager = catalog_manager
        self.model = QStandardItemModel(self)
        self.allow_selection = allow_selection
        self.selected_telescope = None
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
        self.ui.search.textChanged.connect(self.filter_telescopes)
        if self.allow_selection:
            self.add_button.clicked.connect(self.select_telescope)

    def populate_table(self):
        """Populate the table with telescopes from the catalog manager."""
        self.model.removeRows(0, self.model.rowCount())
        telescopes = self.catalog_manager.telescope_catalog.get_items()

        if not telescopes:
            logger.warning("Telescopes catalog is empty")
            QMessageBox.warning(self, "Warning", "Telescopes catalog is empty.")
            return

        # Проверка уникальности имени
        names = [telescope.name for telescope in telescopes if telescope.name]
        unique_names = set(names)
        if len(names) != len(unique_names):
            logger.warning("Duplicate telescope names found in catalog")
            QMessageBox.warning(self, "Warning", "Catalog contains duplicate telescope names. Selection may be ambiguous.")

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
        telescopes = self.catalog_manager.telescope_catalog.get_items()

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

    @Slot()
    def select_telescope(self):
        """Handle selection of a telescope for adding to observation."""
        selected = self.ui.catalogTable.selectionModel().selectedRows()
        if not selected:
            logger.warning("No telescope selected for adding")
            QMessageBox.warning(self, "Warning", "Please select a telescope to add.")
            return

        row = selected[0].row()
        telescope_name = self.model.item(row, 1).text()  # Извлекаем name (второй столбец)
        telescopes = self.catalog_manager.telescope_catalog.get_items()
        matching_telescopes = [t for t in telescopes if t.name == telescope_name]

        if not matching_telescopes:
            logger.error(f"Telescope with name '{telescope_name}' not found in catalog")
            QMessageBox.critical(self, "Error", f"Telescope '{telescope_name}' not found in catalog.")
            return

        if len(matching_telescopes) > 1:
            logger.warning(f"Multiple telescopes with name '{telescope_name}' found in catalog")
            QMessageBox.warning(self, "Warning", f"Multiple telescopes with name '{telescope_name}' found. Selecting the first one.")

        self.selected_telescope = matching_telescopes[0]
        self.telescope_selected.emit(self.selected_telescope)
        self.accept()
        logger.info(f"Selected telescope '{telescope_name}' for adding to observation")