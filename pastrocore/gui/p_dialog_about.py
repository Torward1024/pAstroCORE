from PySide6.QtWidgets import QDialog

from pastrocore import __version__
from pastrocore.gui.ui_dialog_about import Ui_AboutDialog


class AboutDialog(QDialog):
    """Dialog for displaying application information.

    Notes:
        - The version is written here rather than in the form. It was in the `.ui`, which meant
          a release had to remember to change it in two places -- and 0.8.0 shipped with the
          form saying 0.7.0 until it was noticed.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_AboutDialog()
        self.ui.setupUi(self)
        self.ui.labelVersion.setText(f"Version {__version__}")
        self.setModal(True)
