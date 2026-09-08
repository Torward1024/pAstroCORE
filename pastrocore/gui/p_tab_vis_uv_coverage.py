# pastrocore/gui/p_tab_vis_uv_coverage.py
"""What the array samples of the sky: the uv plane, per baseline and frequency."""
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem
from msb_arch.utils.logging_setup import logger

from pastrocore.gui.p_tab_vis_base import VisualizationTab
from pastrocore.gui.ui_tab_vis_uv_coverage import Ui_UVCoverageVisTab


class BaselineVisualizationTab(VisualizationTab):
    """Shared by the two plots that are about baselines rather than about stations.

    Notes:
        - The form calls its source combo `comboBox` and its units combo `comboBox_2`, where
          every other form calls them `cmbSource` and nothing. That is the form's business and
          it is generated, so the names are answered for here rather than renamed.
        - A baseline plot is drawn in wavelengths, which is why these two carry a frequency
          list and the others do not: u and v are held in metres and divided by one.
    """

    FORM = Ui_UVCoverageVisTab
    FILTERS = ("source_name", "baseline")

    #: The units offered, and what the visualizer calls each.
    UNITS = ("Wavelengths", "Earth Diameters")

    def _filter_signals(self):
        """This form's widgets, by the names it gives them."""
        yield self.ui.comboBox, self.ui.comboBox.currentIndexChanged
        yield self.ui.comboBox_2, self.ui.comboBox_2.currentIndexChanged
        for name in ("listScans", "listBaselines", "listFrequencies"):
            widget = getattr(self.ui, name)
            yield widget, widget.itemChanged

    def _populate_filters(self):
        """Sources into the combo, baselines and frequencies into their lists."""
        values = self._distinct(self.FILTERS)
        sources = values.get("source_name", [])
        if sources:
            self.ui.comboBox.addItems(sources)
        else:
            self.ui.comboBox.addItem(f"No {self.STORE_KEY} data available")

        for baseline in values.get("baseline", []):
            item = QListWidgetItem(baseline)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            self.ui.listBaselines.addItem(item)

        for frequency in sorted(self._frequencies()):
            item = QListWidgetItem(f"{frequency:.2f} MHz")
            item.setData(Qt.UserRole, frequency)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            self.ui.listFrequencies.addItem(item)

        self.ui.comboBox_2.addItems(list(self.UNITS))

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

    def get_selected_source(self) -> Optional[str]:
        return self.ui.comboBox.currentText() or None

    def get_selected_baselines(self) -> List[str]:
        return self._checked(self.ui.listBaselines)

    def get_selected_frequencies(self) -> List[float]:
        return self._checked(self.ui.listFrequencies, Qt.UserRole)

    def get_selected_units(self) -> Optional[str]:
        return self.ui.comboBox_2.currentText().lower() or None

    def _first_draw(self):
        if self.ui.comboBox.count() > 0:
            self.update_scans_for_source(self.ui.comboBox.currentText())
        self.update_visualization()

    def _attributes(self) -> Optional[Dict[str, Any]]:
        source = self.get_selected_source()
        scans = self.get_selected_scans()
        baselines = self.get_selected_baselines()
        frequencies = self.get_selected_frequencies()
        if not source or not scans or not baselines or not frequencies:
            return None
        return {"plot_type": self.plot_type(), "show": False, "return_figure": True,
                "figure": self.figure, "source_name": source, "scans": scans,
                "baselines": baselines, "frequencies": frequencies,
                "units": self.get_selected_units()}

    def update_visualization(self):
        """As the base does, but drawn-ness here is baselines *or* frequencies."""
        attributes = self._attributes()
        if attributes is None:
            self._clear_canvas()
            return

        try:
            result = self.manipulator.visualize(obj=self.observation, **attributes)
        except Exception as e:                          # noqa: BLE001 - a blank tab, not a crash
            logger.error("Could not draw '%s': %s", self.plot_type(), str(e), exc_info=True)
            self._clear_canvas()
            return

        drawn = bool(result) and (result.get("baselines", 0) or result.get("frequencies", 0))
        if not drawn or result.get("figure") is None:
            self._clear_canvas()
            return
        self._show()


class UVVisualizationTab(BaselineVisualizationTab):
    """The uv plane."""

    STORE_KEY = "uv_coverage"
