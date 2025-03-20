# gui/SourceSelectorDialog.py
from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QVBoxLayout, QTableWidget, QTableWidgetItem, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt

class SourceSelectorDialog(QDialog):
    def __init__(self, sources, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Sources")
        self.sources = sources
        self.selected_sources = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.textChanged.connect(self.filter_table)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # Таблица с чекбоксами для выбора
        self.table = QTableWidget(len(self.sources), 5)
        self.table.setHorizontalHeaderLabels(["B1950 Name", "J2000 Name", "Alt Name", "RA", "Dec"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.MultiSelection)
        
        for row, source in enumerate(self.sources):
            self.table.setItem(row, 0, QTableWidgetItem(source.get_name()))
            self.table.setItem(row, 1, QTableWidgetItem(source.get_name_J2000() or ""))
            self.table.setItem(row, 2, QTableWidgetItem(source.get_alt_name() or ""))
            ra_deg = source.get_ra_degrees()
            ra_d = int(ra_deg)
            ra_m = int((ra_deg - ra_d) * 60)
            ra_s = ((ra_deg - ra_d) * 60 - ra_m) * 60
            ra_str = f"{ra_d}°{ra_m:02d}′{ra_s:05.2f}″"
            self.table.setItem(row, 3, QTableWidgetItem(ra_str))
            dec_deg = source.get_dec_degrees()
            sign = "-" if dec_deg < 0 else ""
            dec_deg = abs(dec_deg)
            dec_h = int(dec_deg / 15)
            dec_m = int((dec_deg / 15 - dec_h) * 60)
            dec_s = ((dec_deg / 15 - dec_h) * 60 - dec_m) * 60
            dec_str = f"{sign}{dec_h:02d}ʰ{dec_m:02d}′{dec_s:05.2f}″"
            self.table.setItem(row, 4, QTableWidgetItem(dec_str))
            for col in range(5):
                item = self.table.item(row, col)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        # Кнопки OK и Cancel
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setFixedSize(80, 30)
        ok_btn.clicked.connect(self.on_ok)
        button_layout.addWidget(ok_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(80, 30)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setMinimumSize(500, 400)

    def on_ok(self):
        # Сохраняем выбранные источники
        selected_rows = [index.row() for index in self.table.selectionModel().selectedRows()]
        self.selected_sources = [self.sources[row] for row in selected_rows]
        self.accept()

    def get_selected_sources(self):
        return self.selected_sources
    
    def filter_table(self, text):
        text = text.lower()
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)