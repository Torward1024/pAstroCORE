# pastrocore/gui/p_tab_vis_sefd.py
"""What each station's SEFD is in each band, and which of them was measured."""
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem
from msb_arch.utils.logging_setup import logger

from pastrocore.gui.p_tab_vis_base import VisualizationTab
from pastrocore.gui.ui_tab_vis_beam_pattern import Ui_VisBeamPatternTab


class SEFDVisualizationTab(VisualizationTab):
    """SEFDs, filtered by telescope and band.

    Notes:
        - No source and no scan, as the beam pattern has none: an SEFD belongs to a dish in a
          band rather than to a moment. It borrows that form for the same reason.
        - **The bands come from the result** rather than from the observation. A band added since
          the SEFDs were worked out has none, and offering it would offer an empty plot.
    """

    FORM = Ui_VisBeamPatternTab
    STORE_KEY = "sefd"
    FILTERS = ("telescope_code",)

    def _populate_extra_filters(self):
        """Fill the band list with the frequencies the result actually holds."""
        for frequency in self._distinct(["frequency"]).get("frequency", []):
            try:
                item = QListWidgetItem(f"{float(frequency):.2f} MHz")
                item.setData(Qt.UserRole, float(frequency))
            except (TypeError, ValueError) as e:
                logger.error("Not a frequency: %s (%s)", frequency, str(e))
                continue
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            self.ui.listFrequencies.addItem(item)

    def get_selected_frequencies(self) -> List[float]:
        """The ticked bands, in MHz."""
        return self._checked(self.ui.listFrequencies, Qt.UserRole)

    def _attributes(self) -> Optional[Dict[str, Any]]:
        """Telescopes and bands, with no source or scan to speak of."""
        telescopes = self.get_selected_telescopes()
        frequencies = self.get_selected_frequencies()
        if not telescopes or not frequencies:
            return None
        return {"plot_type": self.plot_type(), "show": False, "return_figure": True,
                "figure": self.figure, "telescopes": telescopes, "frequencies": frequencies}
