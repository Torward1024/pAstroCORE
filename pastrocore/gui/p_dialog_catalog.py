# pastrocore/gui/p_dialog_catalog.py
"""A catalogue, browsed, picked from, and edited (C1).

The sources and the telescopes were two dialogs of one shape, written twice: a table, a search
and a button to take what was selected. Editing would have written everything a second time
again, so the shape lives here and each catalogue says only what differs -- its columns, what a
search matches, and which editor opens an entry.

Two modes, chosen by whoever opens it:

- **A manager**, from the Options menu: add, edit and remove entries, and save. An edit is made
  at once, so the generator and every "Add from catalog" see it in this session; closing with
  edits that are not saved asks whether to keep them.
- **A picker**, from an observation and the generator: choose entries to add, and nothing else.
"""
from pathlib import Path
from typing import Any, List, Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFileDialog, QHeaderView,
                               QMessageBox)

from msb_arch.utils.logging_setup import logger

from pastrocore.gui.ui_dialog_catalog import Ui_CatalogDialog

#: Where a row keeps the name of its entry, and the text a search looks in.
NAME_ROLE = Qt.UserRole
SEARCH_ROLE = Qt.UserRole + 1


class CatalogDialog(QDialog):
    """A table of one catalogue, to browse, pick from or edit.

    Subclasses set the class attributes and implement `row`, `searchable`, `run_editor` and
    `picked`.

    Args:
        catalog_manager (CatalogManager): Holds the catalogue, and knows its file.
        manipulator (ScheduleManipulator): The one entry point every request goes through.
            Passed in rather than built here: a second orchestrator in a process is exactly what
            MSB exists to avoid.
        parent (QWidget, optional): Parent widget.
        allow_selection (bool): A picker rather than a manager.
    """

    #: Which catalogue, as the catalogue manager names it.
    KIND = ""
    #: What the window is called, and what one entry and several are called in what it says.
    TITLE = "Catalog"
    ENTRY = "entry"
    ENTRIES = "entries"
    HEADERS: List[str] = []
    SEARCH_LABEL = "Search:"
    #: Whether an entry can also be a space telescope, which has an editor of its own.
    OFFERS_SPACE = False

    #: A catalogue was written to a file: its kind and the path. Whoever keeps the settings
    #: follows it, so the next start reads what was saved.
    catalog_saved = Signal(str, str)

    def __init__(self, catalog_manager, manipulator, parent=None, allow_selection: bool = False):
        super().__init__(parent)
        self.ui = Ui_CatalogDialog()
        self.ui.setupUi(self)
        self.catalog_manager = catalog_manager
        self.manipulator = manipulator
        self.model = QStandardItemModel(self)
        self.allow_selection = allow_selection
        self.setup_ui()
        self.setup_connections()
        self.populate_table()

        if self.allow_selection and not self.model.rowCount():
            logger.warning("The %s catalogue is empty", self.KIND)
            QMessageBox.warning(self, "Warning", f"The {self.TITLE.lower()} is empty.")

    # --- what a catalogue says about itself -------------------------------------------------

    def row(self, entry: Any) -> List[str]:
        """Return the texts of an entry's row, one for each of `HEADERS`."""
        raise NotImplementedError

    def searchable(self, entry: Any) -> List[Optional[str]]:
        """Return the texts a search looks in for an entry."""
        raise NotImplementedError

    def run_editor(self, entry: Any = None, space: bool = False) -> Optional[Any]:
        """Open the editor on an entry, or on a new one, and return what was saved or None."""
        raise NotImplementedError

    def picked(self, entries: List[Any]) -> None:
        """Hand the entries picked to whoever opened the picker."""
        raise NotImplementedError

    # --- the window ----------------------------------------------------------------------------

    def setup_ui(self):
        """Set up the table, and show the buttons of the mode the dialog was opened in."""
        self.ui.catalogTable.setModel(self.model)
        self.model.setHorizontalHeaderLabels(self.HEADERS)
        self.ui.catalogTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ui.lbl_search.setText(self.SEARCH_LABEL)

        editing = not self.allow_selection
        for button in (self.ui.addButton, self.ui.editButton, self.ui.removeButton,
                       self.ui.saveButton, self.ui.saveAsButton):
            button.setVisible(editing)
        self.ui.addSpaceButton.setVisible(editing and self.OFFERS_SPACE)
        self.ui.addSelectedButton.setVisible(self.allow_selection)
        if self.allow_selection:
            self.ui.catalogTable.setSelectionMode(QAbstractItemView.MultiSelection)
        self.refresh_title()

    def setup_connections(self):
        """Connect UI signals to slots."""
        self.ui.closeButton.clicked.connect(self.reject)
        self.ui.search.textChanged.connect(self.apply_search)
        if self.allow_selection:
            self.ui.addSelectedButton.clicked.connect(self.select_entries)
            return
        self.ui.addButton.clicked.connect(self.add_entry)
        self.ui.addSpaceButton.clicked.connect(self.add_space_entry)
        self.ui.editButton.clicked.connect(self.edit_selected)
        self.ui.removeButton.clicked.connect(self.remove_selected)
        self.ui.saveButton.clicked.connect(self.save_catalog)
        self.ui.saveAsButton.clicked.connect(self.save_catalog_as)
        self.ui.catalogTable.doubleClicked.connect(lambda index: self.edit_selected())
        self.ui.catalogTable.selectionModel().selectionChanged.connect(self.enable_editing)

    def catalogue(self) -> Any:
        """Return the catalogue this dialog shows, asked each time: a revert replaces it."""
        return self.catalog_manager.catalog(self.KIND)

    def refresh_title(self):
        """Name the file the catalogue is kept in, and mark it when it holds unsaved edits."""
        path = self.catalog_manager.path(self.KIND)
        self.setWindowTitle(f"{self.TITLE} - {Path(path).name if path else 'not saved'}[*]")
        self.setWindowModified(self.catalog_manager.is_modified(self.KIND))

    def populate_table(self):
        """Fill the table with the catalogue, keeping the search that is typed."""
        self.model.removeRows(0, self.model.rowCount())
        entries = self.manipulator.inspect(self.catalogue(), get_items=None) or []

        for entry in entries:
            items = [QStandardItem(text) for text in self.row(entry)]
            for item in items:
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            items[0].setData(entry.name, NAME_ROLE)
            items[0].setData(" ".join((text or "").lower() for text in self.searchable(entry)),
                             SEARCH_ROLE)
            self.model.appendRow(items)

        self.apply_search(self.ui.search.text())
        logger.debug("Filled the %s table with %s entries", self.KIND, len(entries))

    @Slot(str)
    def apply_search(self, text: str):
        """Show only the rows whose names hold what is typed.

        Notes:
            - Rows are hidden, not rebuilt. Rebuilding asked the catalogue for every entry and
              both halves of every position again on each key pressed -- more than a thousand
              requests a keystroke for the shipped sources, every one of them in the journal.
        """
        wanted = text.lower().strip()
        for row in range(self.model.rowCount()):
            held = self.model.item(row, 0).data(SEARCH_ROLE) or ""
            self.ui.catalogTable.setRowHidden(row, bool(wanted) and wanted not in held)
        self.enable_editing()

    def selected_names(self) -> List[str]:
        """Return the names of the entries selected in rows that are shown."""
        rows = sorted({index.row() for index in self.ui.catalogTable.selectionModel().selectedRows()})
        return [self.model.item(row, 0).data(NAME_ROLE) for row in rows
                if not self.ui.catalogTable.isRowHidden(row)]

    @Slot()
    def enable_editing(self):
        """Offer Edit for one selected entry and Remove for any."""
        count = len(self.selected_names())
        self.ui.editButton.setEnabled(count == 1)
        self.ui.removeButton.setEnabled(count > 0)

    def show_entry(self, name: Optional[str]):
        """Select an entry's row and bring it into view."""
        for row in range(self.model.rowCount()):
            if self.model.item(row, 0).data(NAME_ROLE) == name:
                self.ui.catalogTable.selectRow(row)
                self.ui.catalogTable.scrollTo(self.model.index(row, 0))
                return

    def changed(self, name: Optional[str] = None):
        """Show the catalogue as it is now."""
        self.populate_table()
        self.refresh_title()
        if name:
            self.show_entry(name)

    # --- editing -----------------------------------------------------------------------------

    @Slot()
    def add_entry(self):
        """Add a new entry, from its editor."""
        self._add(space=False)

    @Slot()
    def add_space_entry(self):
        """Add a space telescope, from its own editor."""
        self._add(space=True)

    def _add(self, space: bool):
        try:
            entry = self.run_editor(None, space=space)
            if entry is None:
                return
            self.manipulator.configure(self.catalogue(), add=entry)
        except Exception as e:
            logger.error("Failed to add a %s to the catalogue: %s", self.ENTRY, str(e))
            QMessageBox.critical(self, "Error", f"Failed to add the {self.ENTRY}: {str(e)}")
            return
        logger.info("Added the %s '%s' to the %s catalogue", self.ENTRY, entry.name, self.KIND)
        self.changed(entry.name)

    @Slot()
    def edit_selected(self):
        """Edit the one selected entry.

        Notes:
            - **The editor is given a copy.** It writes what it shows into the object it was
              given before its own checks run, so an edit it refused, then cancelled, stayed in
              the catalogue -- with no request to say so, and nothing to mark it unsaved.
        """
        names = self.selected_names()
        if self.allow_selection or len(names) != 1:
            return
        name = names[0]
        try:
            held = self.manipulator.inspect(self.catalogue(), get=name)
            # A working copy for the editor, taken here rather than asked for: it belongs to
            # nobody and changes nothing, and `inspect` calls only what is named as a read.
            edited = self.run_editor(held.clone())
            if edited is None:
                return
            self.manipulator.configure(self.catalogue(), set_item={"name": name, "item": edited})
        except Exception as e:
            logger.error("Failed to edit the %s '%s': %s", self.ENTRY, name, str(e))
            QMessageBox.critical(self, "Error", f"Failed to edit the {self.ENTRY}: {str(e)}")
            return
        logger.info("Edited the %s '%s' in the %s catalogue", self.ENTRY, name, self.KIND)
        self.changed(name)

    @Slot()
    def remove_selected(self):
        """Remove the selected entries, once asked."""
        names = self.selected_names()
        if not names:
            return
        what = f"'{names[0]}'" if len(names) == 1 else f"{len(names)} {self.ENTRIES}"
        if QMessageBox.question(self, "Remove", f"Remove {what} from the catalogue?",
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) != QMessageBox.Yes:
            return
        for name in names:
            try:
                self.manipulator.configure(self.catalogue(), remove=name)
            except Exception as e:
                logger.error("Failed to remove the %s '%s': %s", self.ENTRY, name, str(e))
                QMessageBox.critical(self, "Error", f"Failed to remove '{name}': {str(e)}")
                break
        logger.info("Removed %s from the %s catalogue", what, self.KIND)
        self.changed()

    # --- saving -----------------------------------------------------------------------------

    @Slot()
    def save_catalog(self) -> bool:
        """Save to the catalogue's own file, or ask where when it has to be a new one.

        Returns:
            bool: Whether it was saved.
        """
        path = self.catalog_manager.save_path(self.KIND)
        if path is None:
            return self.save_catalog_as()
        return self._write(path)

    @Slot()
    def save_catalog_as(self) -> bool:
        """Save to a new JSON file, which the application reads from then on.

        Returns:
            bool: Whether it was saved; not when the file dialog was cancelled.
        """
        path, _ = QFileDialog.getSaveFileName(
            self, f"Save {self.TITLE} As", self.catalog_manager.suggested_path(self.KIND),
            "Catalogue (*.json)")
        if not path:
            return False
        if not path.lower().endswith(".json"):
            path += ".json"
        return self._write(path)

    def _write(self, path: str) -> bool:
        try:
            self.catalog_manager.save(self.KIND, path, self.manipulator)
        except Exception as e:
            logger.error("Failed to save the %s catalogue to '%s': %s", self.KIND, path, str(e))
            QMessageBox.critical(self, "Error", f"Failed to save the catalogue: {str(e)}")
            return False
        self.catalog_saved.emit(self.KIND, path)
        self.refresh_title()
        return True

    def reject(self):
        """Close, asking first when there are edits that are not saved.

        Notes:
            - Close, Escape and the window's own close button all arrive here.
            - **Discard puts back what the file holds.** An edit is made at once, so leaving it
              would keep using a catalogue that is saved nowhere and gone at the next start.
        """
        if not self.allow_selection and self.catalog_manager.is_modified(self.KIND):
            answer = QMessageBox.question(
                self, "Unsaved changes",
                f"The {self.TITLE.lower()} has changes that are not saved. Save them?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
            if answer == QMessageBox.Cancel:
                return
            if answer == QMessageBox.Save and not self.save_catalog():
                return
            if answer == QMessageBox.Discard:
                self.catalog_manager.revert(self.KIND)
                logger.info("Discarded the edits to the %s catalogue", self.KIND)
        super().reject()

    # --- picking -------------------------------------------------------------------------------

    @Slot()
    def select_entries(self):
        """Hand the selected entries to whoever opened the picker."""
        names = self.selected_names()
        if not names:
            logger.warning("No %s selected for adding", self.ENTRIES)
            QMessageBox.warning(self, "Warning", f"Please select one or more {self.ENTRIES} to add.")
            return
        entries = [self.manipulator.inspect(self.catalogue(), get=name) for name in names]
        self.picked(entries)
        self.accept()
        logger.info("Selected %s %s for adding to observation", len(entries), self.ENTRIES)
