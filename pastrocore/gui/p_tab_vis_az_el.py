# pastrocore/gui/p_tab_vis_az_el.py
"""Where a station points at a source: azimuth and elevation over a scan."""
from typing import Any, Dict

from pastrocore.gui.p_tab_vis_base import VisualizationTab
from pastrocore.gui.ui_tab_vis_default import Ui_VisDefaultTab


class AzElVisualizationTab(VisualizationTab):
    """Azimuth and elevation, filtered by source, scan and telescope."""

    FORM = Ui_VisDefaultTab
    STORE_KEY = "az_el"
    FILTERS = ("source_name", "telescope_code")

    #: Which pair of angles the plot draws. The visualizer takes the same plot in two
    #: coordinate systems, and this is the tab that says which.
    COORD_TYPE = "AzEl"

    def _extra_attributes(self) -> Dict[str, Any]:
        return {"coord_type": self.COORD_TYPE}
