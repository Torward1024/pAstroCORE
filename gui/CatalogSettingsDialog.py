from PySide6.QtWidgets import (QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, 
                               QTabWidget, QWidget, QVBoxLayout, QLineEdit, QPushButton, 
                               QTableWidget, QTableWidgetItem, QStatusBar, QDockWidget, QHBoxLayout, QMenu, 
                               QDialog, QFileDialog, QLabel, QGridLayout, QComboBox, QHeaderView)
from PySide6.QtCore import Qt

class CatalogSettingsDialog(QDialog):
    def __init__(self, current_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Catalogs")
        self.current_settings = current_settings
        self.init_ui()

    def init_ui(self):
        layout = QGridLayout()
        layout.addWidget(QLabel("Sources Catalog:"), 0, 0)
        self.sources_path = QLineEdit(self.current_settings["catalogs"]["sources"])
        layout.addWidget(self.sources_path, 0, 1)
        sources_browse_btn = QPushButton("Browse", clicked=self.browse_sources)
        layout.addWidget(sources_browse_btn, 0, 2)
        layout.addWidget(QLabel("Telescopes Catalog:"), 1, 0)
        self.telescopes_path = QLineEdit(self.current_settings["catalogs"]["telescopes"])
        layout.addWidget(self.telescopes_path, 1, 1)
        telescopes_browse_btn = QPushButton("Browse", clicked=self.browse_telescopes)
        layout.addWidget(telescopes_browse_btn, 1, 2)
        ok_btn = QPushButton("OK", clicked=self.accept)
        cancel_btn = QPushButton("Cancel", clicked=self.reject)
        layout.addWidget(ok_btn, 2, 1)
        layout.addWidget(cancel_btn, 2, 2)
        self.setLayout(layout)

    def browse_sources(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Sources Catalog", "", "Data Files (*.dat)")
        if path:
            self.sources_path.setText(path)

    def browse_telescopes(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Telescopes Catalog", "", "Data Files (*.dat)")
        if path:
            self.telescopes_path.setText(path)

    def get_paths(self):
        return {
            "sources": self.sources_path.text(),
            "telescopes": self.telescopes_path.text()
        }