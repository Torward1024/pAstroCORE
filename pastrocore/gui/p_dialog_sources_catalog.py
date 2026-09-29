from typing import Any, List, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog

from pastrocore.gui.p_custom_model import position_text
from pastrocore.gui.p_dialog_catalog import CatalogDialog
from pastrocore.gui.p_dialog_edit_source import SourceEditorDialog


class SourcesCatalogDialog(CatalogDialog):
    """The sources catalogue: browsed and edited from the menu, picked from elsewhere."""

    KIND = "sources"
    TITLE = "Sources Catalog"
    ENTRY = "source"
    ENTRIES = "sources"
    HEADERS = ["Name (B1950)", "J2000 Name", "Alt Name", "RA (hh:mm:ss.s)", "DEC (dd:mm:ss.s)"]
    SEARCH_LABEL = "Search by Name:"

    sources_selected = Signal(list)  # Signal to emit list of selected sources

    def row(self, source: Any) -> List[str]:
        # The same two columns the sources tab draws, written by the same hand. They were
        # written twice, and only one of the two was ever corrected.
        ra_str, dec_str = position_text(self.manipulator, source)
        return [source.name or "", source.name_J2000 or "", source.alt_name or "", ra_str, dec_str]

    def searchable(self, source: Any) -> List[Optional[str]]:
        return [source.name, source.name_J2000, source.alt_name]

    def run_editor(self, source: Any = None, space: bool = False) -> Optional[Any]:
        dialog = SourceEditorDialog(source_obj=source, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return None
        return dialog.get_source_object()

    def picked(self, sources: List[Any]) -> None:
        self.sources_selected.emit(sources)
