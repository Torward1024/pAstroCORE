from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                               QComboBox, QTableWidget, QTableWidgetItem, QCheckBox)
from PySide6.QtCore import Qt
from base.scans import Scan
from base.sources import Source
from base.telescopes import Telescopes
from base.frequencies import Frequencies
from utils.validation import check_positive, check_type
from utils.logging_setup import logger
from datetime import datetime

class EditScanDialog(QDialog):
    def __init__(self, scan: Scan = None, sources: list[Source] = None, telescopes: Telescopes = None, 
                 frequencies: Frequencies = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Scan" if scan else "Add Scan")
        self.scan = scan
        self.sources = sources or []
        self.telescopes = telescopes or Telescopes()
        self.frequencies = frequencies or Frequencies()
        self.setup_ui()
        self.populate_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Start time (YYYY-MM-DD HH:MM:SS.SS)
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Start Time (YYYY-MM-DD HH:MM:SS.SS):"))
        self.start_input = QLineEdit()
        start_layout.addWidget(self.start_input)
        layout.addLayout(start_layout)

        # Duration
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duration (s):"))
        self.duration_input = QLineEdit()
        duration_layout.addWidget(self.duration_input)
        layout.addLayout(duration_layout)

        # Source selection
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Source:"))
        self.source_combo = QComboBox()
        self.source_combo.addItem("None (OFF SOURCE)")
        for src in self.sources:
            self.source_combo.addItem(src.get_name())
        source_layout.addWidget(self.source_combo)
        layout.addLayout(source_layout)

        # Telescopes table (read-only with isactive selection)
        telescopes_layout = QVBoxLayout()
        telescopes_layout.addWidget(QLabel("Telescopes:"))
        self.telescopes_table = QTableWidget(0, 2)
        self.telescopes_table.setHorizontalHeaderLabels(["Code", "Is Active"])
        self.telescopes_table.setEditTriggers(QTableWidget.NoEditTriggers)
        telescopes_layout.addWidget(self.telescopes_table)
        layout.addLayout(telescopes_layout)

        # Frequencies table (read-only with isactive selection)
        frequencies_layout = QVBoxLayout()
        frequencies_layout.addWidget(QLabel("Frequencies:"))
        self.frequencies_table = QTableWidget(0, 2)
        self.frequencies_table.setHorizontalHeaderLabels(["Frequency (MHz)", "Is Active"])
        self.frequencies_table.setEditTriggers(QTableWidget.NoEditTriggers)
        frequencies_layout.addWidget(self.frequencies_table)
        layout.addLayout(frequencies_layout)

        # Is Active
        active_layout = QHBoxLayout()
        active_layout.addWidget(QLabel("Is Active:"))
        self.active_combo = QComboBox()
        self.active_combo.addItems(["True", "False"])
        active_layout.addWidget(self.active_combo)
        layout.addLayout(active_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.on_ok)
        btn_layout.addWidget(ok_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setMinimumSize(500, 600)

    def populate_ui(self):
        # Fill fields with existing scan data or defaults
        if self.scan:
            start_dt = self.scan.get_start_datetime()
            self.start_input.setText(start_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-4])  # До сотых
            self.duration_input.setText(str(self.scan.get_duration()))
            if self.scan.get_source():
                self.source_combo.setCurrentText(self.scan.get_source().get_name())
            elif self.scan.is_off_source:
                self.source_combo.setCurrentText("None (OFF SOURCE)")
            self.active_combo.setCurrentText(str(self.scan.isactive))
        else:
            self.start_input.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S.00"))
            self.duration_input.setText("1.0")
            self.active_combo.setCurrentText("True")

        # Populate telescopes table
        self.telescopes_table.setRowCount(len(self.telescopes.get_all_telescopes()))
        active_telescopes = self.scan.get_telescopes().get_active_telescopes() if self.scan else []
        for i, tel in enumerate(self.telescopes.get_all_telescopes()):
            self.telescopes_table.setItem(i, 0, QTableWidgetItem(tel.get_telescope_code()))
            active_combo = QComboBox()
            active_combo.addItems(["True", "False"])
            # Если редактируем скан, проверяем, активен ли телескоп в этом скане
            is_active_in_scan = tel in active_telescopes if self.scan else tel.isactive
            active_combo.setCurrentText(str(is_active_in_scan))
            self.telescopes_table.setCellWidget(i, 1, active_combo)

        # Populate frequencies table
        self.frequencies_table.setRowCount(len(self.frequencies.get_all_frequencies()))
        active_frequencies = self.scan.get_frequencies().get_active_frequencies() if self.scan else []
        for i, freq in enumerate(self.frequencies.get_all_frequencies()):
            self.frequencies_table.setItem(i, 0, QTableWidgetItem(str(freq.get_frequency())))
            active_combo = QComboBox()
            active_combo.addItems(["True", "False"])
            # Если редактируем скан, проверяем, активна ли частота в этом скане
            is_active_in_scan = freq in active_frequencies if self.scan else freq.isactive
            active_combo.setCurrentText(str(is_active_in_scan))
            self.frequencies_table.setCellWidget(i, 1, active_combo)

    def get_updated_scan(self) -> Scan:
        start_str = self.start_input.text().strip()
        start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S.%f")
        start = start_dt.timestamp()
        duration = float(self.duration_input.text())
        check_positive(duration, "Duration")

        source_name = self.source_combo.currentText()
        source = next((s for s in self.sources if s.get_name() == source_name), None) if source_name != "None (OFF SOURCE)" else None
        is_off_source = source_name == "None (OFF SOURCE)"

        # Create new Telescopes and Frequencies based on selections
        selected_telescopes = Telescopes()
        for i in range(self.telescopes_table.rowCount()):
            tel = self.telescopes.get_telescope(i)
            is_active = self.telescopes_table.cellWidget(i, 1).currentText() == "True"
            if is_active:
                tel.activate()
            else:
                tel.deactivate()
            selected_telescopes.add_telescope(tel)

        selected_frequencies = Frequencies()
        for i in range(self.frequencies_table.rowCount()):
            freq = self.frequencies.get_frequency(i)
            is_active = self.frequencies_table.cellWidget(i, 1).currentText() == "True"
            if is_active:
                freq.activate()
            else:
                freq.deactivate()
            selected_frequencies.add_frequency(freq)

        isactive = self.active_combo.currentText() == "True"
        return Scan(start=start, duration=duration, source=source, telescopes=selected_telescopes, 
                    frequencies=selected_frequencies, is_off_source=is_off_source, isactive=isactive)

    def on_ok(self):
        try:
            self.get_updated_scan()  # Validation happens here
            self.accept()
        except ValueError as e:
            logger.error(f"Invalid scan data: {e}")
            if self.parent() and hasattr(self.parent(), 'status_bar'):
                self.parent().status_bar.showMessage(f"Error: {e}")