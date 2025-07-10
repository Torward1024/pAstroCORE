# p_dialog_preferences.py
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox
from PySide6.QtCore import Signal, Slot
from pastrocore.gui.ui_dialog_preferences import Ui_PreferencesDialog
from common.utils.logging_setup import logger
import os
import logging

class PreferencesDialog(QDialog):
    """Dialog for configuring application settings, such as catalog paths, logging level, and time step."""
    settings_updated = Signal(dict)

    def __init__(self, settings: dict, parent=None):
        """Initialize the preferences dialog with current settings.

        Args:
            settings (dict): Current application settings with keys 'sources_catalog_path', 
                            'telescopes_catalog_path', 'log_level', and 'time_step'.
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
        self.ui.timeStepSpin.setValue(self.settings.get("time_step", 600))  # Устанавливаем time_step
        # Make fields read-only to prevent manual editing
        self.ui.sourcesCatalogPath.setReadOnly(True)
        self.ui.telescopesCatalogPath.setReadOnly(True)
        # Populate logging level combo box
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        self.ui.comboLogging.addItems(log_levels)
        current_log_level = self.settings.get("log_level", "INFO")
        if current_log_level in log_levels:
            self.ui.comboLogging.setCurrentText(current_log_level)
        else:
            self.ui.comboLogging.setCurrentText("INFO")
            logger.warning(f"Invalid log level in settings: {current_log_level}. Defaulting to INFO.")

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
        log_level = self.ui.comboLogging.currentText()
        time_step = self.ui.timeStepSpin.value()

        # Validate file existence
        if sources_path and not os.path.isfile(sources_path):
            logger.error(f"Invalid sources catalog path: {sources_path}")
            QMessageBox.critical(self, "Error", "Sources catalog file does not exist.")
            return
        if telescopes_path and not os.path.isfile(telescopes_path):
            logger.error(f"Invalid telescopes catalog path: {telescopes_path}")
            QMessageBox.critical(self, "Error", "Telescopes catalog file does not exist.")
            return
        if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            logger.error(f"Invalid log level selected: {log_level}")
            QMessageBox.critical(self, "Error", "Invalid logging level selected.")
            return
        if time_step < 1:
            logger.error(f"Invalid time step value: {time_step}. Must be positive.")
            QMessageBox.critical(self, "Error", "Time step must be a positive number.")
            return

        # Update settings
        self.settings["sources_catalog_path"] = sources_path
        self.settings["telescopes_catalog_path"] = telescopes_path
        self.settings["ogeneska"] = log_level
        self.settings["time_step"] = time_step
        logger.info(f"Settings updated in PreferencesDialog: sources_path={sources_path}, telescopes_path={telescopes_path}, log_level={log_level}, time_step={time_step}")
        self.settings_updated.emit(self.settings)
        self.accept()