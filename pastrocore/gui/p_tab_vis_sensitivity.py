# pastrocore/gui/p_tab_vis_sensitivity.py
"""What each baseline reaches on each scan, and what misses the threshold."""
from typing import Any, Dict, Optional

from pastrocore.gui.p_tab_vis_base import VisualizationTab
from pastrocore.gui.ui_tab_vis_sensitivity import Ui_VisSensitivityTab


class BaselineSensitivityVisualizationTab(VisualizationTab):
    """Baseline sensitivity, filtered by source, scan, baseline and band.

    Notes:
        - **One band at a time**, because what is drawn is a grid of baselines by scans and a
          cell holds one number. `all` -- every band of a scan together, which is what fringe
          fitting across a recording gets -- is the first offer and the usual one.
    """

    FORM = Ui_VisSensitivityTab
    STORE_KEY = "baseline_sensitivity"
    FILTERS = ("source_name", "baseline")
    DRAWN = "baselines"

    #: The row holding every band of a scan together, spelled as the result spells it.
    TOGETHER = "all"

    def _filter_signals(self):
        """The common ones, and the band this plot is drawn for."""
        yield from super()._filter_signals()
        yield self.ui.cmbBand, self.ui.cmbBand.currentIndexChanged

    def _populate_extra_filters(self):
        """Offer the bands the result holds, with all of them together first."""
        bands = self._distinct(["if_name"]).get("if_name", [])
        ordered = ([self.TOGETHER] if self.TOGETHER in bands else [])
        ordered += sorted(band for band in bands if band != self.TOGETHER)
        self.ui.cmbBand.addItems(ordered)

    def get_selected_band(self) -> Optional[str]:
        """The band the grid is drawn for."""
        return self.ui.cmbBand.currentText() or None

    def _extra_attributes(self) -> Optional[Dict[str, Any]]:
        """The baselines and the band, without which there is nothing to draw."""
        baselines = self.get_selected_baselines()
        band = self.get_selected_band()
        if not baselines or not band:
            return None
        return {"baselines": baselines, "if_name": band}
