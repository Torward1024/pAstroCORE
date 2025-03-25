from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                               QComboBox, QTableWidget, QTableWidgetItem, QCheckBox, QDateTimeEdit, QHeaderView)
from PySide6.QtCore import Qt, QDateTime
from base.scans import Scan
from base.sources import Source
from base.telescopes import Telescopes
from base.frequencies import Frequencies
from utils.validation import check_positive, check_type
from utils.logging_setup import logger
from datetime import datetime
from typing import List, Optional

class EditScanDialog(QDialog):
    def __init__(self, scan: Scan = None, sources: List[Source] = None, telescopes: Telescopes = None, 
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

        # Start time (YYYY-MM-DD HH:MM:SS.SS) with QDateTimeEdit
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Start Time (YYYY-MM-DD HH:MM:SS.SS):"))
        self.start_input = QDateTimeEdit()
        self.start_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss.zz")  # До сотых секунд
        self.start_input.setCalendarPopup(True)  # Всплывающий календарь
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

        # Telescopes table (read-only with checkbox selection)
        telescopes_layout = QVBoxLayout()
        telescopes_layout.addWidget(QLabel("Telescopes:"))
        self.telescopes_table = QTableWidget(0, 2)
        self.telescopes_table.setHorizontalHeaderLabels(["", "Code"])  # Пустое название для Is Active
        self.telescopes_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.telescopes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # Растягиваем только "Code"
        self.telescopes_table.horizontalHeader().setMinimumSectionSize(20)  # Минимальная ширина для чекбокса
        self.telescopes_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)  # Фиксируем ширину чекбокса
        self.telescopes_table.setColumnWidth(0, 30)  # Устанавливаем ширину чекбокса ~30px
        telescopes_layout.addWidget(self.telescopes_table)
        layout.addLayout(telescopes_layout)

        # Frequencies table (read-only with checkbox selection)
        frequencies_layout = QVBoxLayout()
        frequencies_layout.addWidget(QLabel("Frequencies:"))
        self.frequencies_table = QTableWidget(0, 2)
        self.frequencies_table.setHorizontalHeaderLabels(["", "Frequency (MHz)"])  # Пустое название для Is Active
        self.frequencies_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.frequencies_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # Растягиваем только "Frequency"
        self.frequencies_table.horizontalHeader().setMinimumSectionSize(20)  # Минимальная ширина для чекбокса
        self.frequencies_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)  # Фиксируем ширину чекбокса
        self.frequencies_table.setColumnWidth(0, 30)  # Устанавливаем ширину чекбокса ~30px
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
            self.start_input.setDateTime(QDateTime.fromString(
                start_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-4], "yyyy-MM-dd HH:mm:ss.zz"))
            self.duration_input.setText(str(self.scan.get_duration()))
            source_index = self.scan.get_source_index()
            if source_index is not None and source_index < len(self.sources):
                self.source_combo.setCurrentText(self.sources[source_index].get_name())
            elif self.scan.is_off_source:
                self.source_combo.setCurrentText("None (OFF SOURCE)")
            self.active_combo.setCurrentText(str(self.scan.isactive))
        else:
            self.start_input.setDateTime(QDateTime.currentDateTime())
            self.duration_input.setText("1.0")
            self.active_combo.setCurrentText("True")

        # Populate telescopes table
        all_telescopes = self.telescopes.get_all_telescopes()
        self.telescopes_table.setRowCount(len(all_telescopes))
        active_telescope_indices = self.scan.get_telescope_indices() if self.scan else []
        for i, tel in enumerate(all_telescopes):
            checkbox = QCheckBox()
            is_active_in_scan = i in active_telescope_indices if self.scan else tel.isactive
            checkbox.setChecked(is_active_in_scan)
            self.telescopes_table.setCellWidget(i, 0, checkbox)
            self.telescopes_table.setItem(i, 1, QTableWidgetItem(tel.get_code()))

        # Populate frequencies table
        all_frequencies = self.frequencies.get_all_IF()
        self.frequencies_table.setRowCount(len(all_frequencies))
        active_frequency_indices = self.scan.get_frequency_indices() if self.scan else []
        for i, freq in enumerate(all_frequencies):
            checkbox = QCheckBox()
            is_active_in_scan = i in active_frequency_indices if self.scan else freq.isactive
            checkbox.setChecked(is_active_in_scan)
            self.frequencies_table.setCellWidget(i, 0, checkbox)
            self.frequencies_table.setItem(i, 1, QTableWidgetItem(str(freq.get_frequency())))

    def get_updated_scan(self) -> Scan:
        start_dt = self.start_input.dateTime().toPython()  # Получаем datetime из QDateTimeEdit
        start = start_dt.timestamp()
        
        try:
            duration = float(self.duration_input.text())
            check_positive(duration, "Duration")
        except ValueError as e:
            raise ValueError(f"Invalid duration: {e}")

        source_name = self.source_combo.currentText()
        source_index = None
        is_off_source = source_name == "None (OFF SOURCE)"
        if not is_off_source:
            source_index = next((i for i, s in enumerate(self.sources) if s.get_name() == source_name), None)
            if source_index is None and source_name != "None (OFF SOURCE)":
                raise ValueError(f"Source '{source_name}' not found in available sources")

        # Собираем индексы выбранных телескопов
        telescope_indices = []
        for i in range(self.telescopes_table.rowCount()):
            if self.telescopes_table.cellWidget(i, 0).isChecked():
                telescope_indices.append(i)

        # Собираем индексы выбранных частот
        frequency_indices = []
        for i in range(self.frequencies_table.rowCount()):
            if self.frequencies_table.cellWidget(i, 0).isChecked():
                frequency_indices.append(i)

        isactive = self.active_combo.currentText() == "True"
        return Scan(
            start=start,
            duration=duration,
            source_index=source_index,
            telescope_indices=telescope_indices,
            frequency_indices=frequency_indices,
            is_off_source=is_off_source,
            isactive=isactive
        )

    def on_ok(self):
        try:
            self.get_updated_scan()  # Validation happens here
            self.accept()
        except ValueError as e:
            logger.error(f"Invalid scan data: {e}")
            if self.parent() and hasattr(self.parent(), 'status_bar'):
                self.parent().status_bar.showMessage(f"Error: {e}")