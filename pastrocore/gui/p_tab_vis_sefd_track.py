# pastrocore/gui/p_tab_vis_sefd_track.py
"""How each station's SEFD moves along the scans, as the source rises and sets."""
from pastrocore.gui.p_tab_vis_base import VisualizationTab
from pastrocore.gui.ui_tab_vis_default import Ui_VisDefaultTab


class SEFDTrackVisualizationTab(VisualizationTab):
    """The SEFD along the scans, filtered by source, scan and telescope."""

    FORM = Ui_VisDefaultTab
    STORE_KEY = "sefd_track"
    FILTERS = ("source_name", "telescope_code")
