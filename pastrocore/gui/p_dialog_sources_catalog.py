from PySide6.QtWidgets import QDialog, QMessageBox, QHeaderView, QPushButton, QAbstractItemView
from PySide6.QtCore import Slot, Qt, Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem
from pastrocore.gui.ui_dialog_catalog import Ui_CatalogDialog
from pastrocore.utils.catalogmanager import CatalogManager
from msb_arch.utils.logging_setup import logger

class SourcesCatalogDialog(QDialog):
    """Dialog for browsing and selecting sources from the catalog."""
    sources_selected = Signal(list)  # Signal to emit list of selected sources

    def __init__(self, catalog_manager: CatalogManager, manipulator, parent=None,
                 allow_selection: bool = False):
        """Initialize the sources catalog dialog.

        Args:
            catalog_manager (CatalogManager): The catalog manager containing source data.
            manipulator (ScheduleManipulator): The one entry point every request goes
                through. Passed in rather than built here: a second orchestrator in a
                process is exactly what MSB exists to avoid.
            parent (QWidget, optional): Parent widget. Defaults to None.
            allow_selection (bool, optional): If True, enables source selection mode with 'Add' button.
        """
        super().__init__(parent)
        self.ui = Ui_CatalogDialog()
        self.ui.setupUi(self)
        self.catalog_manager = catalog_manager
        self.manipulator = manipulator
        self.model = QStandardItemModel(self)
        self.allow_selection = allow_selection
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
        self.ui.search.textChanged.connect(self.filter_sources)
        if self.allow_selection:
            self.add_button.clicked.connect(self.select_sources)

    def _position(self, source) -> tuple:
        """Return a source's right ascension and declination as the table shows them.

        Notes:
            - Asked of the source. The sign came from `de_d >= 0`, which is true of `-0.0`, so
              every source between -1 and 0 degrees was listed north of the equator; and seconds
              rounded on their own showed 59.96 as `60.0`.
        """
        hours, minutes, seconds = self.manipulator.inspect(source, right_ascension_parts=1)
        sign, degrees, arcminutes, arcseconds = self.manipulator.inspect(source, declination_parts=1)
        return (f"{hours:02d}:{minutes:02d}:{seconds:04.1f}",
                f"{sign}{degrees:02d}:{arcminutes:02d}:{arcseconds:04.1f}")

    def populate_table(self):
        """Populate the table with sources from the catalog manager."""
        self.model.removeRows(0, self.model.rowCount())
        sources = self.manipulator.inspect(self.catalog_manager.source_catalog, get_items=None)

        if not sources:
            logger.warning("Sources catalog is empty")
            QMessageBox.warning(self, "Warning", "Sources catalog is empty.")
            return

        for source in sources:
            ra_str, dec_str = self._position(source)
            items = [
                QStandardItem(source.name or ""),
                QStandardItem(source.name_J2000 or ""),
                QStandardItem(source.alt_name or ""),
                QStandardItem(ra_str),
                QStandardItem(dec_str)
            ]
            for item in items:
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            items[0].setData(source, Qt.UserRole)
            self.model.appendRow(items)

        logger.info("Populated sources catalog table with %s sources", len(sources))

    @Slot(str)
    def filter_sources(self, text: str):
        """Filter sources in the table based on search text.

        Args:
            text (str): The search text to filter by name, J2000 name, or alt name.
        """
        text = text.lower().strip()
        self.model.removeRows(0, self.model.rowCount())
        sources = self.manipulator.inspect(self.catalog_manager.source_catalog, get_items=None)

        for source in sources:
            if (text in (source.name or "").lower() or
                text in (source.name_J2000 or "").lower() or
                text in (source.alt_name or "").lower()):
                ra_str, dec_str = self._position(source)
                items = [
                    QStandardItem(source.name or ""),
                    QStandardItem(source.name_J2000 or ""),
                    QStandardItem(source.alt_name or ""),
                    QStandardItem(ra_str),
                    QStandardItem(dec_str)
                ]
                for item in items:
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                items[0].setData(source, Qt.UserRole)
                self.model.appendRow(items)

    @Slot()
    def select_sources(self):
        """Handle selection of multiple sources for adding to observation."""
        selected_rows = self.ui.catalogTable.selectionModel().selectedRows()
        if not selected_rows:
            logger.warning("No sources selected for adding")
            QMessageBox.warning(self, "Warning", "Please select one or more sources to add.")
            return

        selected_sources = []
        for index in selected_rows:
            source = self.model.item(index.row(), 0).data(Qt.UserRole)
            if source:
                selected_sources.append(source)

        if selected_sources:
            self.sources_selected.emit(selected_sources)
            self.accept()
            logger.info("Selected %s sources for adding to observation", len(selected_sources))
        else:
            logger.error("No valid sources found in selection")
            QMessageBox.critical(self, "Error", "No valid sources found in selection.")