from PySide6.QtWidgets import (QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, 
                               QTabWidget, QWidget, QVBoxLayout, QLineEdit, QPushButton, 
                               QTableWidget, QTableWidgetItem, QStatusBar, QDockWidget, QHBoxLayout, QMenu, 
                               QDialog, QFileDialog, QLabel, QGridLayout, QComboBox, QHeaderView)
from PySide6.QtGui import QIcon
import os
from utils.logging_setup import logger
class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About pvCORE")
        self.setFixedSize(400, 200)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_path = os.path.join(os.path.dirname(__file__), "pvcore_icon.png")
        if os.path.exists(icon_path):
            icon_label.setPixmap(QIcon(icon_path).pixmap(64, 64))
        else:
            logger.warning("pvcore_icon.png not found in project root")
        top_layout.addWidget(icon_label)
        info_label = QLabel(
            "pvCORE\n"
            "Version: 0.0.1\n"
            "A versatile tool for radio astronomy observation planning,\n"
            "configuration, optimization, and visualization.\n"
            "\n"
            "Developed by:  Alexey Rudnitskiy, Mikhail Shchurov\n"
            "                  Pavel Zapevalin, Tatiana Syachina\n"
            "\n"
            "© 2024-2025 ASC LPI, Ballistics Lab"
        )
        top_layout.addWidget(info_label)
        top_layout.addStretch()
        layout.addLayout(top_layout)
        ok_btn = QPushButton("OK", clicked=self.accept)
        ok_btn.setFixedWidth(80)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)