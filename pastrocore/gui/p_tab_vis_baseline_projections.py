# pastrocore/gui/p_tab_vis_baseline_projections.py
"""How long each baseline is as the sky turns: its projection, over a scan."""
from pastrocore.gui.p_tab_vis_uv_coverage import BaselineVisualizationTab


class BaselineProjectionsVisualizationTab(BaselineVisualizationTab):
    """Baseline projections -- the same filters as the uv plane, a different plot."""

    STORE_KEY = "baseline_projections"
