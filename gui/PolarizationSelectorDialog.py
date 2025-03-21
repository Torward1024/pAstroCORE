# gui/PolarizationSelectorDialog.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QPushButton, QLabel
from PySide6.QtCore import Qt
from utils.logging_setup import logger
from typing import List, Optional

class PolarizationSelectorDialog(QDialog):
    def __init__(self, current_polarizations: List[str], observation_type: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Polarizations")
        self.observation_type = observation_type
        self.selected_polarizations = current_polarizations.copy()
        
        layout = QVBoxLayout(self)
        
        if observation_type == "VLBI":
            self.valid_polarizations = ["LL", "RR", "RL", "LR"]
            layout.addWidget(QLabel("Select one or more polarizations (VLBI):"))
        else:  # SINGLE_DISH
            self.valid_polarizations = ["RCP", "LCP", "H", "V"]
            layout.addWidget(QLabel("Select one or both from RCP, LCP or H, V (SINGLE_DISH):"))

        self.checkboxes = {}
        for pol in self.valid_polarizations:
            cb = QCheckBox(pol)
            cb.setChecked(pol in current_polarizations)
            cb.stateChanged.connect(self.on_checkbox_changed)
            self.checkboxes[pol] = cb
            layout.addWidget(cb)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        layout.addWidget(self.ok_button)

        self.update_ok_button_state()

    def on_checkbox_changed(self, state):
        self.selected_polarizations = [pol for pol, cb in self.checkboxes.items() if cb.isChecked()]
        self.update_ok_button_state()

    def update_ok_button_state(self):
        count = len(self.selected_polarizations)
        if self.observation_type == "VLBI":
            self.ok_button.setEnabled(count >= 1)
        else:  # SINGLE_DISH
            if count == 0 or count > 2:
                self.ok_button.setEnabled(False)
            else:
                # Проверяем, что выбраны только RCP, LCP или только H, V
                has_circular = "RCP" in self.selected_polarizations or "LCP" in self.selected_polarizations
                has_linear = "H" in self.selected_polarizations or "V" in self.selected_polarizations
                self.ok_button.setEnabled(not (has_circular and has_linear))  # Запрещаем смешанные пары
        logger.debug(f"Polarization count: {count}, Selected: {self.selected_polarizations}, OK button enabled: {self.ok_button.isEnabled()}")

    def get_selected_polarizations(self) -> List[str]:
        return self.selected_polarizations