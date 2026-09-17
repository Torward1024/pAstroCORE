from typing import Any, List, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog

from pastrocore.base.spacetelescope import SpaceTelescope
from pastrocore.gui.p_dialog_catalog import CatalogDialog
from pastrocore.gui.p_dialog_edit_space_telescope import SpaceTelescopeEditorDialog
from pastrocore.gui.p_dialog_edit_telescope import TelescopeEditorDialog


class TelescopesCatalogDialog(CatalogDialog):
    """The telescopes catalogue: browsed and edited from the menu, picked from elsewhere.

    Notes:
        - A space telescope can be kept here as well as a ground station. The `.dat` format had
          nowhere to put one; a JSON catalogue holds whatever a telescope has.
    """

    KIND = "telescopes"
    TITLE = "Telescopes Catalog"
    ENTRY = "telescope"
    ENTRIES = "telescopes"
    HEADERS = ["Code", "Name", "X (m)", "Y (m)", "Z (m)", "Diameter (m)"]
    SEARCH_LABEL = "Search by Code or Name:"
    OFFERS_SPACE = True

    telescopes_selected = Signal(list)  # Signal to emit list of selected telescopes

    def row(self, telescope: Any) -> List[str]:
        return [telescope.code or "", telescope.name or "", f"{telescope.x:.2f}",
                f"{telescope.y:.2f}", f"{telescope.z:.2f}", f"{telescope.diameter:.2f}"]

    def searchable(self, telescope: Any) -> List[Optional[str]]:
        return [telescope.code, telescope.name]

    def run_editor(self, telescope: Any = None, space: bool = False) -> Optional[Any]:
        if space or isinstance(telescope, SpaceTelescope):
            dialog = SpaceTelescopeEditorDialog(telescope=telescope, parent=self)
            if telescope is None:
                dialog.ui.isActiveCheckBox.setChecked(True)
        else:
            dialog = TelescopeEditorDialog(telescope=telescope, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return None
        return dialog.get_telescope_object()

    def picked(self, telescopes: List[Any]) -> None:
        self.telescopes_selected.emit(telescopes)
