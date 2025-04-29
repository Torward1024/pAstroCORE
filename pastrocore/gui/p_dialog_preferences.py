from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox
from PySide6.QtCore import Signal, Slot
from pastrocore.gui.ui_dialog_preferences import Ui_PreferencesDialog
from common.utils.logging_setup import logger
import os

class PreferencesDialog(QDialog):
    """Dialog for configuring application settings, such as catalog paths."""
    settings_updated = Signal(dict)

    def __init__(self, settings: dict, parent=None):
        """Initialize the preferences dialog with current settings.

        Args:
            settings (dict): Current application settings with keys 'sources_catalog_path' and 'telescopes_catalog_path'.
            parent (QWidget, optional): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.ui = Ui_PreferencesDialog()
        self.ui.setupUi(self)
        self.settings = settings.copy()
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """Set up the UI with current settings."""
        self.ui.sourcesCatalogPath.setText(self.settings.get("sources_catalog_path", ""))
        self.ui.telescopesCatalogPath.setText(self.settings.get("telescopes_catalog_path", ""))
        # Make fields read-only to prevent manual editing
        self.ui.sourcesCatalogPath.setReadOnly(True)
        self.ui.telescopesCatalogPath.setReadOnly(True)

    def setup_connections(self):
        """Connect UI signals to slots."""
        self.ui.openSourcesCatalogButton.clicked.connect(self.select_sources_catalog)
        self.ui.openTelescopesCatalogButton.clicked.connect(self.select_telescopes_catalog)
        self.ui.okButton.clicked.connect(self.accept_settings)
        self.ui.cancelButton.clicked.connect(self.reject)

    @Slot()
    def select_sources_catalog(self):
        """Open a file dialog to select the sources catalog file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Sources Catalog", "", "Catalog Files (*.dat);;All Files (*)"
        )
        if file_path:
            self.ui.sourcesCatalogPath.setText(file_path)
            logger.info(f"Selected sources catalog path: {file_path}")

    @Slot()
    def select_telescopes_catalog(self):
        """Open a file dialog to select the telescopes catalog file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Telescopes Catalog", "", "Catalog Files (*.dat);;All Files (*)"
        )
        if file_path:
            self.ui.telescopesCatalogPath.setText(file_path)
            logger.info(f"Selected telescopes catalog path: {file_path}")

    @Slot()
    def accept_settings(self):
        """Validate and save the selected settings."""
        sources_path = self.ui.sourcesCatalogPath.text().strip()
        telescopes_path = self.ui.telescopesCatalogPath.text().strip()

        # Validate file existence
        if sources_path and not os.path.isfile(sources_path):
            logger.error(f"Invalid sources catalog path: {sources_path}")
            QMessageBox.critical(self, "Error", "Sources catalog file does not exist.")
            return
        if telescopes_path and not os.path.isfile(telescopes_path):
            logger.error(f"Invalid telescopes catalog path: {telescopes_path}")
            QMessageBox.critical(self, "Error", "Telescopes catalog file does not exist.")
            return

        # Update settings
        self.settings["sources_catalog_path"] = sources_path
        self.settings["telescopes_catalog_path"] = telescopes_path
        logger.info("Settings updated in PreferencesDialog")
        self.settings_updated.emit(self.settings)
        self.accept()