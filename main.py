from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from gui.MainWindow import PvCoreWindow

import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PvCoreWindow()
    window.show()
    sys.exit(app.exec())