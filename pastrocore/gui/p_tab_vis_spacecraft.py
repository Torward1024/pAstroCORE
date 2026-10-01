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
        - The subject is a target rather than a source, the result naming it `target_code`,
          which is why `FILTERS` carries the column name rather than the base assuming it.
    """

    FORM = Ui_VisDefaultTab
    STORE_KEY = "telescope_az_el"
    FILTERS = ("target_code", "telescope_code")
    #: Declared, not implemented: asking `scan_times` by target rather than by source
    #: is the only way the refill differs from the base's.
    SCAN_BY = "target_code"

    def get_selected_target(self) -> Optional[str]:
        """The spacecraft being pointed at.

        Notes:
            - The same combo the base calls a source, named for what it holds here.
        """
        return self.get_selected_source()

    def _attributes(self) -> Optional[Dict[str, Any]]:
        """The base's request, with the chosen spacecraft as the target rather than a source.

        Notes:
            - Built on the base's answer. It was written from scratch and left out the tab's
              figure, so both spacecraft tabs drew into a figure nobody showed.
        """
        attributes = super()._attributes()
        if attributes is None:
            return None
        target = attributes.pop("source_name", None)
        if not target:
            return None
        attributes["target_code"] = target
        return attributes


class SpacecraftPointingVisualizationTab(SpacecraftVisualizationTab):
    """Azimuth, elevation and range to the spacecraft."""

    STORE_KEY = "telescope_az_el"


class SpacecraftVisibilityVisualizationTab(SpacecraftVisualizationTab):
    """Whether the spacecraft is above the horizon and unobstructed."""

    STORE_KEY = "telescope_visibility"
