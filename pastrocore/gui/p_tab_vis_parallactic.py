# pastrocore/gui/p_tab_vis_parallactic.py
"""Parallactic angle over a scan, per station."""
from pastrocore.gui.p_tab_vis_base import VisualizationTab
from pastrocore.gui.ui_tab_vis_default import Ui_VisDefaultTab


class ParallacticAngleVisualizationTab(VisualizationTab):
    """Parallactic angle, filtered by source, scan and telescope."""

    FORM = Ui_VisDefaultTab
    STORE_KEY = "parallactic_angle"
    FILTERS = ("source_name", "telescope_code")
