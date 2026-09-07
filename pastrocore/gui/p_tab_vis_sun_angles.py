# pastrocore/gui/p_tab_vis_sun_angles.py
"""The angle between a source and the Sun, over a scan."""
from pastrocore.gui.p_tab_vis_base import VisualizationTab
from pastrocore.gui.ui_tab_vis_default import Ui_VisDefaultTab


class SunAnglesVisualizationTab(VisualizationTab):
    """Sun angles, filtered by source, scan and telescope."""

    FORM = Ui_VisDefaultTab
    STORE_KEY = "sun_angles"
    FILTERS = ("source_name", "telescope_code")
