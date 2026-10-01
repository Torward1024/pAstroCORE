# pastrocore/gui/p_tab_vis_beam_pattern.py
"""The beam of a dish, per station and per frequency."""
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem
from msb_arch.utils.logging_setup import logger

from pastrocore.gui.p_tab_vis_base import VisualizationTab
from pastrocore.gui.ui_tab_vis_beam_pattern import Ui_VisBeamPatternTab


class BeamPatternVisualizationTab(VisualizationTab):
    """A beam pattern, filtered by telescope and frequency.

    Notes:
        - The odd one out: no source and no scan, a beam belonging to a dish at a wavelength
          rather than to a moment, which the base copes with by asking the form.
    """

    FORM = Ui_VisBeamPatternTab
    STORE_KEY = "beam_pattern"
    FILTERS = ("telescope_code",)
    #: Both, because a beam drawn for two stations at one frequency reports the
    #: frequency count and not the telescope count: judged on telescopes alone it looks empty.
    DRAWN = ("telescopes", "frequencies")

    def _populate_extra_filters(self):
        """Add the frequency list, which comes from the model rather than from the result.

        Notes:
            - A beam can be drawn at any frequency the observation defines, including one the
              stored result was not computed at.
        """
        for frequency in sorted(self._frequencies()):
            try:
                item = QListWidgetItem(f"{float(frequency):.2f} MHz")
                item.setData(Qt.UserRole, float(frequency))
            except (TypeError, ValueError) as e:
                logger.error("Not a frequency: %s (%s)", frequency, str(e))
                continue
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            self.ui.listFrequencies.addItem(item)

    def _frequencies(self) -> List[float]:
        """The observation's frequencies, in MHz."""
        try:
            bands = self.manipulator.inspect(obj=self.observation, get_frequencies=None)
            if not bands:
                return []
            return self.manipulator.inspect(bands, get_frequencies=None) or []
        except Exception as e:                          # noqa: BLE001 - an empty list, not a crash
            logger.error("Could not read the frequencies: %s", str(e), exc_info=True)
            return []

    def get_selected_frequencies(self) -> List[float]:
        """The ticked frequencies, in MHz."""
        return self._checked(self.ui.listFrequencies, Qt.UserRole)

    def _attributes(self) -> Optional[Dict[str, Any]]:
        """Telescopes and frequencies, with no source or scan to speak of."""
        telescopes = self.get_selected_telescopes()
        frequencies = self.get_selected_frequencies()
        if not telescopes or not frequencies:
            return None
        return {"plot_type": self.plot_type(), "show": False, "return_figure": True,
                "figure": self.figure, "telescopes": telescopes, "frequencies": frequencies}
