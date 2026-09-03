from PySide6.QtWidgets import QDialog, QMessageBox, QHeaderView, QPushButton, QAbstractItemView
from PySide6.QtCore import Slot, Qt, Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem
from pastrocore.gui.ui_dialog_catalog import Ui_CatalogDialog
from pastrocore.utils.catalogmanager import CatalogManager
from msb_arch.utils.logging_setup import logger

class TelescopesCatalogDialog(QDialog):
    """Dialog for browsing and selecting telescopes from the catalog."""
    telescopes_selected = Signal(list)  # Signal to emit list of selected telescopes

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
            self.ui.catalogTable.setSelectionMode(QAbstractItemView.MultiSelection)
            self.ui.catalogTable.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.add_button = QPushButton("Add Selected", self)
            # No sheet of its own: `QPushButton` in pastrocore.qss is this
            # rule, and it reached every other button already.
            self.ui.gridLayout.removeItem(self.ui.horizontalSpacer)
            self.ui.gridLayout.addWidget(self.add_button, 1, 2, 1, 1)
            self.ui.gridLayout.addWidget(self.ui.closeButton, 1, 3, 1, 1)

    def setup_connections(self):
        """Connect UI signals to slots."""
        self.ui.closeButton.clicked.connect(self.reject)
        self.ui.search.textChanged.connect(self.filter_telescopes)
        if self.allow_selection:
            self.add_button.clicked.connect(self.select_telescopes)

    def populate_table(self):
        """Populate the table with telescopes from the catalog manager."""
        self.model.removeRows(0, self.model.rowCount())
        telescopes = self.manipulator.inspect(self.catalog_manager.telescope_catalog, get_items=None)

        if not telescopes:
            logger.warning("Telescopes catalog is empty")
            QMessageBox.warning(self, "Warning", "Telescopes catalog is empty.")
            return

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
            items[0].setData(telescope, Qt.UserRole)
            self.model.appendRow(items)

        logger.info("Populated telescopes catalog table with %s telescopes", len(telescopes))

    @Slot(str)
    def filter_telescopes(self, text: str):
        """Filter telescopes in the table based on search text.

        Args:
            text (str): The search text to filter by code or name.
        """
        text = text.lower().strip()
        self.model.removeRows(0, self.model.rowCount())
        telescopes = self.manipulator.inspect(self.catalog_manager.telescope_catalog, get_items=None)

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
                items[0].setData(telescope, Qt.UserRole)
                self.model.appendRow(items)

    @Slot()
    def select_telescopes(self):
        """Handle selection of multiple telescopes for adding to observation."""
        selected_rows = self.ui.catalogTable.selectionModel().selectedRows()
        if not selected_rows:
            logger.warning("No telescopes selected for adding")
            QMessageBox.warning(self, "Warning", "Please select one or more telescopes to add.")
            return

        selected_telescopes = []
        for index in selected_rows:
            telescope = self.model.item(index.row(), 0).data(Qt.UserRole)
            if telescope:
                selected_telescopes.append(telescope)

        if selected_telescopes:
            self.telescopes_selected.emit(selected_telescopes)
            self.accept()
            logger.info("Selected %s telescopes for adding to observation", len(selected_telescopes))
        else:
            logger.error("No valid telescopes found in selection")
            QMessageBox.critical(self, "Error", "No valid telescopes found in selection.")