from PySide6.QtWidgets import QDialog
from pastrocore.gui.ui_dialog_about import Ui_AboutDialog

class AboutDialog(QDialog):
    """Dialog for displaying application information."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_AboutDialog()
        self.ui.setupUi(self)
        self.setModal(True)