# pastrocore/gui/p_tab_vis_time_on_source.py
"""How long each station spends on each source."""
from pastrocore.gui.p_tab_vis_base import VisualizationTab
from pastrocore.gui.ui_tab_vis_default import Ui_VisDefaultTab


class TimeOnSourceVisualizationTab(VisualizationTab):
    """Time on source, filtered by source, scan and telescope."""

    FORM = Ui_VisDefaultTab
    STORE_KEY = "time_on_source"
    FILTERS = ("source_name", "telescope_code")
