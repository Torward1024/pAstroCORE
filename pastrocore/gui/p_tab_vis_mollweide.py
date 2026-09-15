# pastrocore/gui/p_tab_vis_mollweide.py
"""Where each station's line of sight goes on the sky, all-sky."""
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem
from msb_arch.utils.logging_setup import logger

from pastrocore.gui.p_tab_vis_base import VisualizationTab
from pastrocore.gui.ui_tab_vis_mollweide import Ui_MollweideVisTab


class MollweideVisualizationTab(VisualizationTab):
    """Mollweide tracks, filtered by source, scan and telescope.

    Notes:
        - Its sources come from the result's **metadata** rather than from a column: a track is
          drawn per telescope, and the sources are the coordinates it is drawn against. Reading
          metadata does not touch the result, which is what makes asking cheap.
        - Several sources at once, so they are a checkable list rather than a combo -- which is
          why the scans list is not narrowed to one source here.
    """

    FORM = Ui_MollweideVisTab
    STORE_KEY = "mollweide_tracks"
    FILTERS = ("telescope_code",)

    def _populate_extra_filters(self):
        """Add the source list, from the metadata beside the result."""
        self.ui.listWidget.setObjectName("listSources")
        for source in sorted(self._sources()):
            item = QListWidgetItem(source)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            self.ui.listWidget.addItem(item)

    def _sources(self) -> List[str]:
        """The sources the tracks were drawn against, from the result's metadata."""
        try:
            metadata = self.manipulator.inspect(
                obj=self.observation, get_calculated_metadata=self.STORE_KEY) or {}
            return list((metadata.get("sources") or {}).keys())
        except Exception as e:                          # noqa: BLE001 - an empty list, not a crash
            logger.error("Could not read the sources of the tracks: %s", str(e), exc_info=True)
            return []

    def _filter_signals(self):
        """The base's, plus the source list this form calls `listWidget`."""
        yield from super()._filter_signals()
        yield self.ui.listWidget, self.ui.listWidget.itemChanged

    def get_selected_sources(self) -> List[str]:
        """The ticked sources."""
        return self._checked(self.ui.listWidget)

    def _first_draw(self):
        """Every scan, since the scans here are not narrowed by a single source."""
        self.update_scans_for_source(None)
        self.update_visualization()

    def _extra_attributes(self) -> Optional[Dict[str, Any]]:
        """However many sources are ticked; the base asks for the scans and telescopes.

        Notes:
            - **Added to the base's request rather than written instead of it.** This built its
              own dictionary and left out the tab's figure, so the visualizer drew into a figure
              of its own and the tab showed its empty one: the Mollweide tab opened and never
              drew a thing.
        """
        sources = self.get_selected_sources()
        if not sources:
            return None
        return {"store_key": self.STORE_KEY, "sources": sources}
