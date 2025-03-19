from PySide6.QtWidgets import (QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, 
                               QTabWidget, QWidget, QVBoxLayout, QLineEdit, QPushButton, 
                               QTableWidget, QTableWidgetItem, QStatusBar, QDockWidget, QHBoxLayout, QMenu, 
                               QDialog, QFileDialog, QLabel, QGridLayout, QComboBox, QHeaderView)
from PySide6.QtCore import Qt

class CatalogBrowserDialog(QDialog):
    def __init__(self, catalog_type, catalog_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{catalog_type} Catalog Browser")
        self.catalog_type = catalog_type
        self.catalog_data = catalog_data
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        if self.catalog_type == "Source":
            self.table = QTableWidget(len(self.catalog_data), 5)
            self.table.setHorizontalHeaderLabels(["B1950 Name", "J2000 Name", "Alt Name", "RA", "Dec"])
            for row, source in enumerate(self.catalog_data):
                self.table.setItem(row, 0, QTableWidgetItem(source.get_name()))
                self.table.setItem(row, 1, QTableWidgetItem(source.get_name_J2000() or ""))
                self.table.setItem(row, 2, QTableWidgetItem(source.get_alt_name() or ""))
                ra_deg = source.get_ra_degrees()
                ra_d = int(ra_deg)
                ra_m = int((ra_deg - ra_d) * 60)
                ra_s = ((ra_deg - ra_d) * 60 - ra_m) * 60
                ra_str = f"{ra_d}°{ra_m:02d}′{ra_s:05.2f}″"
                ra_item = QTableWidgetItem(ra_str)
                ra_item.setFlags(ra_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 3, ra_item)
                dec_deg = source.get_dec_degrees()
                sign = "-" if dec_deg < 0 else ""
                dec_deg = abs(dec_deg)
                dec_h = int(dec_deg / 15)
                dec_m = int((dec_deg / 15 - dec_h) * 60)
                dec_s = ((dec_deg / 15 - dec_h) * 60 - dec_m) * 60
                dec_str = f"{sign}{dec_h:02d}ʰ{dec_m:02d}′{dec_s:05.2f}″"
                dec_item = QTableWidgetItem(dec_str)
                dec_item.setFlags(dec_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 4, dec_item)
        else:  # Telescope
            self.table = QTableWidget(len(self.catalog_data), 5)
            self.table.setHorizontalHeaderLabels(["Code", "Name", "X (m)", "Y (m)", "Z (m)"])
            for row, telescope in enumerate(self.catalog_data):
                self.table.setItem(row, 0, QTableWidgetItem(telescope.get_telescope_code()))
                self.table.setItem(row, 1, QTableWidgetItem(telescope.get_telescope_name()))
                self.table.setItem(row, 2, QTableWidgetItem(str(telescope.get_telescope_x())))
                self.table.setItem(row, 3, QTableWidgetItem(str(telescope.get_telescope_y())))
                self.table.setItem(row, 4, QTableWidgetItem(str(telescope.get_telescope_z())))
                for col in range(5):
                    item = self.table.item(row, col)
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setFixedSize(80, 30)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.setMinimumSize(500, 400)