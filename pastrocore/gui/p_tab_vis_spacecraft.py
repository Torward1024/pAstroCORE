# pastrocore/gui/p_tab_vis_spacecraft.py
"""Where a ground station points to reach a spacecraft, and whether it can.

Two plots that differ only in which result they read, which is why they are two declarations
rather than two implementations -- this file was already written that way before the rest of
the tabs were, and it is what the shared base was drawn from.
"""
from typing import Any, Dict, Optional

from pastrocore.gui.p_tab_vis_base import VisualizationTab
from pastrocore.gui.ui_tab_vis_default import Ui_VisDefaultTab


class SpacecraftVisualizationTab(VisualizationTab):
    """One spacecraft result, filtered by target, scan and station.

    Notes:
        - The subject is a **target** rather than a source: what is pointed at is a spacecraft,
          and the result names it `target_code`. The combo is the same combo; only the word for
          what is in it differs, which is why `FILTERS` carries the column name rather than the
          base assuming one.
    """

    FORM = Ui_VisDefaultTab
    STORE_KEY = "telescope_az_el"
    FILTERS = ("target_code", "telescope_code")

    def get_selected_target(self) -> Optional[str]:
        """The spacecraft being pointed at.

        Notes:
            - The same combo the base calls a source. Named for what it holds here, because a
              caller of this tab is asking about a target and should not have to know that the
              widget is shared with the plots that track a source.
        """
        return self.get_selected_source()

    def update_scans_for_source(self, source_name: Optional[str] = None):
        """As the base does, but the scans are asked for by target rather than by source."""
        if not self._has(self.ui, "listScans"):
            return
        if not source_name:
            self.ui.listScans.clear()
            return
        self._fill_scans({"key": self.STORE_KEY, "target_code": source_name})

    def _fill_scans(self, asked: Dict[str, Any]):
        """Refill the scans list from a `scan_times` request, keeping what was ticked."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QListWidgetItem
        from msb_arch.utils.logging_setup import logger

        was_checked = {self.ui.listScans.item(index).data(Qt.UserRole):
                       self.ui.listScans.item(index).checkState()
                       for index in range(self.ui.listScans.count())}
        self.ui.listScans.clear()

        try:
            scan_times = self.manipulator.export(
                obj=self.observation, method="scan_times", **asked) or []
        except Exception as e:                          # noqa: BLE001 - an empty list, not a crash
            logger.error("Could not read the scans of '%s': %s", self.STORE_KEY, str(e),
                         exc_info=True)
            self.ui.listScans.addItem(QListWidgetItem("Failed to retrieve scans"))
            return

        if not scan_times:
            self.ui.listScans.addItem(QListWidgetItem("No scans available"))
            return

        for entry in scan_times:
            item = QListWidgetItem(entry["start"])
            item.setData(Qt.UserRole, entry["scan_name"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(was_checked.get(entry["scan_name"], Qt.Checked))
            self.ui.listScans.addItem(item)

    def _attributes(self) -> Optional[Dict[str, Any]]:
        """Target, scans and stations."""
        target = self.get_selected_source()
        scans = self.get_selected_scans()
        stations = self.get_selected_telescopes()
        if not target or not scans or not stations:
            return None
        return {"plot_type": self.plot_type(), "show": False, "return_figure": True,
                "target_code": target, "scans": scans, "telescopes": stations}


class SpacecraftPointingVisualizationTab(SpacecraftVisualizationTab):
    """Azimuth, elevation and range to the spacecraft."""

    STORE_KEY = "telescope_az_el"


class SpacecraftVisibilityVisualizationTab(SpacecraftVisualizationTab):
    """Whether the spacecraft is above the horizon and unobstructed."""

    STORE_KEY = "telescope_visibility"
