from typing import Any, List, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog

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

    def row(self, source: Any) -> List[str]:
        ra_str, dec_str = self._position(source)
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
