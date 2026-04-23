from PySide6.QtWidgets import QDialog, QMessageBox, QMenu, QFileDialog, QListWidgetItem
from PySide6.QtCore import Signal, Slot, Qt, QPoint, QThread, QRegularExpression, QDateTime, QTime, QDate
from PySide6.QtGui import QIcon, QRegularExpressionValidator
from .ui_dialog_generate_observations import Ui_GenerateObservationsDialog
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.utils.catalogmanager import CatalogManager
from pastrocore.base.frequencies import IF, Frequencies
from pastrocore.base.sources import Source, Sources
from pastrocore.base.telescopes import Telescope, SpaceTelescope, Telescopes
from pastrocore.gui.p_dialog_edit_if import IFEditorDialog
from pastrocore.gui.p_dialog_sources_catalog import SourcesCatalogDialog
from pastrocore.gui.p_dialog_telescopes_catalog import TelescopesCatalogDialog
from pastrocore.gui.p_dialog_edit_source import SourceEditorDialog
from pastrocore.gui.p_dialog_edit_telescope import TelescopeEditorDialog
from pastrocore.gui.p_dialog_edit_space_telescope import SpaceTelescopeEditorDialog
from .ui_dialog_calc_progress import Ui_ProgressDialog
from msb_arch.utils.logging_setup import logger
import uuid
import json
from datetime import datetime, timedelta

class ProgressDialog(QDialog):
    """Dialog for displaying progress of observation generation."""
    cancelRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_ProgressDialog()
        self.ui.setupUi(self)
        self.setWindowTitle("Generating Observations")
        self.ui.label.setText("Generating observations...")
        self.ui.pushButtonCancel.clicked.connect(self.cancel)
        self.cancel_requested = False

    def update_progress(self, value, message):
        """Update progress bar and label."""
        self.ui.progressBar.setValue(value)
        self.ui.label.setText(message)
        logger.debug(f"Progress updated: {value}% - {message}")

    def cancel(self):
        """Emit cancelRequested signal and update UI."""
        self.cancel_requested = True
        self.ui.pushButtonCancel.setEnabled(False)
        self.ui.label.setText("Cancelling after current observation...")
        logger.debug("Cancellation requested for observation generation")
        self.cancelRequested.emit()

class GenerationThread(QThread):
    """Thread for performing observation generation asynchronously."""
    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, manipulator: ScheduleManipulator, project: ScheduleProject, attributes: dict):
        super().__init__()
        self.manipulator = manipulator
        self.project = project
        self.attributes = attributes
        self.attributes["cancelled"] = False
        self.attributes["progress_callback"] = self._progress_callback
        logger.debug("GenerationThread initialized")

    def cancel(self):
        """Set cancellation flag to stop after current observation."""
        self.attributes["cancelled"] = True
        logger.debug("GenerationThread cancellation requested")

    def _progress_callback(self, value: int, message: str):
        """Callback to emit progress signal."""
        self.progress.emit(value, message)

    def run(self):
        """Execute observation generation asynchronously and emit progress signals."""
        try:
            result = self.manipulator.configure(obj=self.project, generate_observations=self.attributes)
            self.finished.emit({"status": True, "result": result})
        except Exception as e:
            logger.error(f"Error in GenerationThread: {str(e)}")
            self.error.emit(str(e))

class GenerateObservationsDialog(QDialog):
    """Dialog for generating observations in pAstroCORE."""
    observation_generated = Signal(list)

    def __init__(self, project: ScheduleProject, manipulator: ScheduleManipulator, 
                 catalog_manager: CatalogManager, parent=None):
        super().__init__(parent)
        self.ui = Ui_GenerateObservationsDialog()
        self.ui.setupUi(self)
        self.project = project
        self.manipulator = manipulator
        self.catalog_manager = catalog_manager
        self.frequencies = Frequencies()
        self.sources = Sources()
        self.telescopes = Telescopes()
        self._source_order = []
        self._telescope_order = []
        self._frequency_order = []
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """Populate lists and set up initial UI state."""

        self.ui.sourceList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.telescopeList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.frequencyList.setContextMenuPolicy(Qt.CustomContextMenu)
        

        self.ui.namingMaskEdit.setText("Observation_{i}_{s}_{dt}")

        mask_validator = QRegularExpressionValidator(QRegularExpression(r'^[a-zA-Z0-9_{}]+$'))
        self.ui.namingMaskEdit.setValidator(mask_validator)
        
        self.ui.addOffSourceCheck.setChecked(False)
        self.ui.randomizeOrderCheck.setChecked(False)
        self.ui.intervalSpinBox.setValue(0)

        current_date = datetime.now().date()
        start_qdt = QDateTime(QDate(current_date.year, current_date.month, current_date.day), QTime(0, 0, 0))
        end_qdt = start_qdt.addSecs(86400)
        self.ui.startTimeEdit.setDateTime(start_qdt)
        self.ui.endTimeEdit.setDateTime(end_qdt)
        self.ui.chkParallel.setChecked(True)
        
        self.update_frequency_list()
        self.update_source_list()
        self.update_telescope_list()

    def setup_connections(self):
        """Connect UI signals to slots."""
        self.ui.sourceSelectAllButton.clicked.connect(self.ui.sourceList.selectAll)
        self.ui.sourceClearButton.clicked.connect(self.ui.sourceList.clearSelection)
        self.ui.sourceUpButton.clicked.connect(self.move_source_up)
        self.ui.sourceDownButton.clicked.connect(self.move_source_down)
        self.ui.telescopeSelectAllButton.clicked.connect(self.ui.telescopeList.selectAll)
        self.ui.telescopeClearButton.clicked.connect(self.ui.telescopeList.clearSelection)
        self.ui.frequencySelectAllButton.clicked.connect(self.ui.frequencyList.selectAll)
        self.ui.frequencyClearButton.clicked.connect(self.ui.frequencyList.clearSelection)
        self.ui.sourceList.customContextMenuRequested.connect(self.show_source_context_menu)
        self.ui.telescopeList.customContextMenuRequested.connect(self.show_telescope_context_menu)
        self.ui.frequencyList.customContextMenuRequested.connect(self.show_frequency_context_menu)
        self.ui.generateButton.clicked.connect(self.generate)
        self.ui.presetCombo.currentIndexChanged.connect(self.load_preset)
        self.ui.savePresetButton.clicked.connect(self.save_preset)
        self.ui.loadPresetButton.clicked.connect(self.load_preset_from_file)

        self.ui.startTimeEdit.dateTimeChanged.connect(self.update_end_time)
        self.ui.scanDurationSpinBox.valueChanged.connect(self.update_end_time)
        self.ui.intervalSpinBox.valueChanged.connect(self.update_end_time)
        self.ui.numScansSpinBox.valueChanged.connect(self.update_end_time)
        self.ui.chkParallel.stateChanged.connect(self.update_end_time)
        self.ui.sourceList.itemSelectionChanged.connect(self.update_end_time)
        self.ui.addOffSourceCheck.stateChanged.connect(self.update_end_time)
        self.ui.endTimeEdit.dateTimeChanged.connect(self.update_scan_duration_from_end)

    def update_frequency_list(self):
        """Update the frequency list UI from self.frequencies."""
        self.ui.frequencyList.clear()
        for name in self._frequency_order:
            if name in self.frequencies.get_all():
                if_obj = self.frequencies.get_all()[name]
                item = QListWidgetItem(f"{if_obj.frequency:.0f} MHz, BW: {if_obj.bandwidth:.0f} MHz, Pol: {', '.join(if_obj.polarizations)}")
                item.setData(Qt.UserRole, if_obj)
                item.setData(Qt.UserRole + 1, name)
                self.ui.frequencyList.addItem(item)

    def update_source_list(self):
        """Update the source list UI from self.sources, respecting _source_order."""
        self.ui.sourceList.clear()
        for name in self._source_order:
            if name in self.sources.get_all():
                source = self.sources.get_all()[name]
                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, source)
                self.ui.sourceList.addItem(item)

    def update_telescope_list(self):
        """Update the telescope list UI from self.telescopes, respecting _telescope_order."""
        self.ui.telescopeList.clear()
        for name in self._telescope_order:
            if name in self.telescopes.get_all():
                telescope = self.telescopes.get_all()[name]
                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, telescope)
                self.ui.telescopeList.addItem(item)

    @Slot(QPoint)
    def show_frequency_context_menu(self, position: QPoint):
        """Show context menu for the frequency list."""
        menu = QMenu(self)
        add_action = menu.addAction(QIcon(":/icons/add_icon.svg"), "Add Frequency")
        add_action.triggered.connect(self.add_frequency)
        index = self.ui.frequencyList.indexAt(position)
        if index.isValid():
            menu.addSeparator()
            edit_action = menu.addAction(QIcon(":/icons/edit_icon.svg"), "Edit Frequency")
            remove_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Remove Frequency")
            edit_action.triggered.connect(lambda: self.edit_frequency(index.row()))
            remove_action.triggered.connect(lambda: self.remove_frequency(index.row()))
        menu.exec(self.ui.frequencyList.viewport().mapToGlobal(position))

    @Slot()
    def add_frequency(self):
        """Add a new frequency using IFEditorDialog."""
        dialog = IFEditorDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            try:
                if_obj = dialog.get_if_object()
                self.frequencies.add(if_obj)
                self._frequency_order.append(if_obj.name)
                self.update_frequency_list()
                logger.info(f"Added frequency '{if_obj.name}' to frequencies collection")
            except Exception as e:
                logger.error(f"Failed to add frequency: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to add frequency: {str(e)}")

    @Slot(int)
    def edit_frequency(self, row: int):
        """Edit a frequency using IFEditorDialog."""
        item = self.ui.frequencyList.item(row)
        if item:
            if_obj = item.data(Qt.UserRole)
            dialog = IFEditorDialog(if_obj=if_obj, parent=self)
            if dialog.exec() == QDialog.Accepted:
                try:
                    if_data = dialog.get_if_data()
                    if_obj.set(if_data)
                    self.update_frequency_list()
                    logger.info(f"Edited frequency '{if_obj.name}'")
                except Exception as e:
                    logger.error(f"Failed to edit frequency: {str(e)}")
                    QMessageBox.critical(self, "Error", f"Failed to edit frequency: {str(e)}")

    @Slot(int)
    def remove_frequency(self, row: int):
        """Remove a frequency from frequencies collection."""
        item = self.ui.frequencyList.item(row)
        if item:
            name = item.data(Qt.UserRole + 1)
            self.frequencies.remove(name)
            self._frequency_order.remove(name)
            self.update_frequency_list()
            logger.info(f"Removed frequency '{name}' from frequencies collection")

    @Slot()
    def move_source_up(self):
        """Move the selected source up in the list."""
        current_row = self.ui.sourceList.currentRow()
        if current_row > 0:
            self._source_order[current_row], self._source_order[current_row - 1] = (
                self._source_order[current_row - 1], self._source_order[current_row]
            )
            self.update_source_list()
            self.ui.sourceList.setCurrentRow(current_row - 1)
            logger.debug(f"Moved source '{self._source_order[current_row - 1]}' up to position {current_row}")

    @Slot()
    def move_source_down(self):
        """Move the selected source down in the list."""
        current_row = self.ui.sourceList.currentRow()
        if current_row < self.ui.sourceList.count() - 1 and current_row >= 0:
            self._source_order[current_row], self._source_order[current_row + 1] = (
                self._source_order[current_row + 1], self._source_order[current_row]
            )
            self.update_source_list()
            self.ui.sourceList.setCurrentRow(current_row + 1)
            logger.debug(f"Moved source '{self._source_order[current_row + 1]}' down to position {current_row + 2}")

    @Slot(QPoint)
    def show_source_context_menu(self, position: QPoint):
        """Show context menu for the sources list."""
        menu = QMenu(self)
        add_action = menu.addAction(QIcon(":/icons/add_icon.svg"), "Add Source")
        add_catalog_action = menu.addAction(QIcon(":/icons/import_icon.svg"), "Add from Catalog")
        add_action.triggered.connect(self.add_source)
        add_catalog_action.triggered.connect(self.add_sources_from_catalog)
        index = self.ui.sourceList.indexAt(position)
        if index.isValid():
            menu.addSeparator()
            remove_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Remove Source")
            remove_action.triggered.connect(lambda: self.remove_source(index.row()))
        menu.exec(self.ui.sourceList.viewport().mapToGlobal(position))

    @Slot()
    def add_source(self):
        """Add a new source manually using SourceEditorDialog."""
        dialog = SourceEditorDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            try:
                source = dialog.get_source_object()
                self.sources.add(source)
                self._source_order.append(source.name)
                self.update_source_list()
                logger.info(f"Added source '{source.name}' manually to sources collection")
            except Exception as e:
                logger.error(f"Failed to add source manually: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to add source: {str(e)}")

    @Slot()
    def add_sources_from_catalog(self):
        """Add sources from catalog."""
        dialog = SourcesCatalogDialog(self.catalog_manager, parent=self, allow_selection=True)
        dialog.sources_selected.connect(self.handle_sources_selected)
        dialog.exec()

    @Slot(list)
    def handle_sources_selected(self, sources: list):
        """Handle sources selected from catalog."""
        added_count = 0
        skipped_sources = []
        for source in sources:
            if source.name in self.sources.get_all():
                skipped_sources.append(source.name)
                logger.info(f"Skipped source '{source.name}' as it already exists in sources collection")
                continue
            self.sources.add(source)
            self._source_order.append(source.name)
            added_count += 1
            logger.info(f"Added source '{source.name}' from catalog to sources collection")
        self.update_source_list()
        if added_count:
            QMessageBox.information(self, "Success", f"Added {added_count} source(s) from catalog.")
        if skipped_sources:
            QMessageBox.information(self, "Note", f"Skipped {len(skipped_sources)} source(s) already in collection: {', '.join(skipped_sources)}")
        if not added_count and not skipped_sources:
            QMessageBox.warning(self, "Warning", "No sources added.")

    @Slot(int)
    def remove_source(self, row: int):
        """Remove a source from sources collection."""
        item = self.ui.sourceList.item(row)
        if item:
            name = item.text()
            self.sources.remove(name)
            self._source_order.remove(name)
            self.update_source_list()
            logger.info(f"Removed source '{name}' from sources collection")

    @Slot(QPoint)
    def show_telescope_context_menu(self, position: QPoint):
        """Show context menu for the telescopes list."""
        menu = QMenu(self)
        add_telescope_action = menu.addAction(QIcon(":/icons/add_icon.svg"), "Add Telescope")
        add_space_telescope_action = menu.addAction(QIcon(":/icons/add_icon.svg"), "Add Space Telescope")
        add_catalog_action = menu.addAction(QIcon(":/icons/import_icon.svg"), "Add from Catalog")
        add_telescope_action.triggered.connect(self.add_telescope)
        add_space_telescope_action.triggered.connect(self.add_space_telescope)
        add_catalog_action.triggered.connect(self.add_telescopes_from_catalog)
        index = self.ui.telescopeList.indexAt(position)
        if index.isValid():
            menu.addSeparator()
            remove_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Remove Telescope")
            remove_action.triggered.connect(lambda: self.remove_telescope(index.row()))
        menu.exec(self.ui.telescopeList.viewport().mapToGlobal(position))

    @Slot()
    def add_telescope(self):
        """Add a new ground-based telescope manually using TelescopeEditorDialog."""
        dialog = TelescopeEditorDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            try:
                telescope = dialog.get_telescope_object()
                self.telescopes.add(telescope)
                self._telescope_order.append(telescope.name)
                self.update_telescope_list()
                logger.info(f"Added telescope '{telescope.name}' to telescopes collection")
                QMessageBox.information(self, "Success", f"Added telescope '{telescope.name}'.")
            except Exception as e:
                logger.error(f"Failed to add telescope manually: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to add telescope: {str(e)}")

    @Slot()
    def add_space_telescope(self):
        """Add a new space telescope manually using SpaceTelescopeEditorDialog."""
        dialog = SpaceTelescopeEditorDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            try:
                telescope = dialog.get_telescope_object()
                self.telescopes.add(telescope)
                self._telescope_order.append(telescope.name)
                self.update_telescope_list()
                logger.info(f"Added space telescope '{telescope.name}' to telescopes collection")
                QMessageBox.information(self, "Success", f"Added space telescope '{telescope.name}'.")
            except Exception as e:
                logger.error(f"Failed to add space telescope manually: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to add space telescope: {str(e)}")

    @Slot()
    def add_telescopes_from_catalog(self):
        """Add telescopes from catalog."""
        dialog = TelescopesCatalogDialog(self.catalog_manager, parent=self, allow_selection=True)
        dialog.telescopes_selected.connect(self.handle_telescopes_selected)
        dialog.exec()

    @Slot(list)
    def handle_telescopes_selected(self, telescopes: list):
        """Handle telescopes selected from catalog."""
        added_count = 0
        skipped_telescopes = []
        for telescope in telescopes:
            name = telescope.name
            if name in self.telescopes.get_all():
                skipped_telescopes.append(name)
                logger.info(f"Skipped telescope '{name}' as it already exists in telescopes collection")
                continue
            self.telescopes.add(telescope)
            self._telescope_order.append(name)
            added_count += 1
            logger.info(f"Added telescope '{name}' from catalog to telescopes collection")
        self.update_telescope_list()
        if added_count:
            QMessageBox.information(self, "Success", f"Added {added_count} telescope(s) from catalog.")
        if skipped_telescopes:
            QMessageBox.information(self, "Note", f"Skipped {len(skipped_telescopes)} telescope(s) already in collection: {', '.join(skipped_telescopes)}")
        if not added_count and not skipped_telescopes:
            QMessageBox.warning(self, "Warning", "No telescopes added.")

    @Slot(int)
    def remove_telescope(self, row: int):
        """Remove a telescope from telescopes collection."""
        item = self.ui.telescopeList.item(row)
        if item:
            name = item.text()
            self.telescopes.remove(name)
            self._telescope_order.remove(name)
            self.update_telescope_list()
            logger.info(f"Removed telescope '{name}' from telescopes collection")

    @Slot()
    def save_preset(self):
        """Save current settings as a preset to a file."""
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Preset", "", "JSON Files (*.json)")
        if file_name:
            try:
                preset_data = {
                    "observation_type": self.ui.observationTypeCombo.currentText(),
                    "start_time": self.ui.startTimeEdit.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
                    "end_time": self.ui.endTimeEdit.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
                    "scan_duration": self.ui.scanDurationSpinBox.value(),
                    "num_scans": self.ui.numScansSpinBox.value(),
                    "naming_mask": self.ui.namingMaskEdit.text(),
                    "add_off_source": self.ui.addOffSourceCheck.isChecked(),
                    "randomize_order": self.ui.randomizeOrderCheck.isChecked(),
                    "interval_min": self.ui.intervalSpinBox.value(),
                    "parallel": self.ui.chkParallel.isChecked()
                }
                with open(file_name, 'w') as f:
                    json.dump(preset_data, f)
                logger.info(f"Saved preset to {file_name}")
            except Exception as e:
                logger.error(f"Failed to save preset: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to save preset: {str(e)}")

    @Slot()
    def load_preset_from_file(self):
        """Load preset from a file."""
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Preset", "", "JSON Files (*.json)")
        if file_name:
            try:
                with open(file_name, 'r') as f:
                    preset_data = json.load(f)
                self.ui.observationTypeCombo.setCurrentText(preset_data.get("observation_type", "VLBI"))
                self.ui.startTimeEdit.setDateTime(QDateTime.fromString(preset_data.get("start_time", datetime.now().strftime("yyyy-MM-dd HH:mm:ss")), "yyyy-MM-dd HH:mm:ss"))
                self.ui.endTimeEdit.setDateTime(QDateTime.fromString(preset_data.get("end_time", (datetime.now() + timedelta(hours=24)).strftime("yyyy-MM-dd HH:mm:ss")), "yyyy-MM-dd HH:mm:ss"))
                self.ui.scanDurationSpinBox.setValue(preset_data.get("scan_duration", 300))
                self.ui.numScansSpinBox.setValue(preset_data.get("num_scans", 5))
                self.ui.namingMaskEdit.setText(preset_data.get("naming_mask", "Observation_{i}_{s}_{dt}"))
                self.ui.addOffSourceCheck.setChecked(preset_data.get("add_off_source", False))
                self.ui.randomizeOrderCheck.setChecked(preset_data.get("randomize_order", False))
                self.ui.intervalSpinBox.setValue(preset_data.get("interval_min", 5))
                self.ui.chkParallel.setChecked(preset_data.get("parallel", True))
                logger.info(f"Loaded preset from {file_name}")
            except Exception as e:
                logger.error(f"Failed to load preset: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to load preset: {str(e)}")

    @Slot(int)
    def load_preset(self, index: int):
        """Load a predefined preset based on combo box selection."""
        preset = self.ui.presetCombo.currentText()
        if preset == "Standard VLBI":
            self.ui.observationTypeCombo.setCurrentText("VLBI")
            self.ui.scanDurationSpinBox.setValue(300)
            self.ui.numScansSpinBox.setValue(10)
            self.ui.addOffSourceCheck.setChecked(False)
            self.ui.randomizeOrderCheck.setChecked(False)
            self.ui.intervalSpinBox.setValue(5)
            self.ui.chkParallel.setChecked(True)
        elif preset == "Quick Single Dish":
            self.ui.observationTypeCombo.setCurrentText("SINGLE_DISH")
            self.ui.scanDurationSpinBox.setValue(60)
            self.ui.numScansSpinBox.setValue(5)
            self.ui.addOffSourceCheck.setChecked(True)
            self.ui.randomizeOrderCheck.setChecked(True)
            self.ui.intervalSpinBox.setValue(1)
            self.ui.chkParallel.setChecked(False)
        logger.info(f"Loaded preset '{preset}'")

    @Slot()
    def generate(self):
        """Generate observations based on user inputs and start the generation thread."""
        try:
            source_items = [item.data(Qt.UserRole) for item in self.ui.sourceList.selectedItems()]
            telescope_items = [item.data(Qt.UserRole) for item in self.ui.telescopeList.selectedItems()]
            frequency_items = [item.data(Qt.UserRole) for item in self.ui.frequencyList.selectedItems()]
            observation_type = self.ui.observationTypeCombo.currentText()
            start_time = self.ui.startTimeEdit.dateTime().toPython()
            end_time = self.ui.endTimeEdit.dateTime().toPython()
            scan_duration = self.ui.scanDurationSpinBox.value()
            num_scans = self.ui.numScansSpinBox.value()
            naming_mask = self.ui.namingMaskEdit.text()

            sources = Sources(items={s.name: s for s in source_items})
            telescopes = Telescopes(items={t.name: t for t in telescope_items})
            frequencies = Frequencies(items={f.name: f for f in frequency_items})

            if not sources.get_all():
                raise ValueError("No sources selected")
            if not telescopes.get_all():
                raise ValueError("No telescopes selected")
            if not frequencies.get_all():
                raise ValueError("No frequencies added")
            if start_time >= end_time:
                raise ValueError("Start time must be before end time")
            if scan_duration <= 0:
                raise ValueError("Scan duration must be positive")
            if num_scans <= 0:
                raise ValueError("Number of scans must be positive")
            if not naming_mask:
                raise ValueError("Naming mask cannot be empty")

            logger.debug(f"Generating with: sources={len(source_items)} ({[s.name for s in source_items]}), "
                        f"telescopes={len(telescope_items)} ({[t.name for t in telescope_items]}, Types: {[type(t).__name__ for t in telescope_items]}), "
                        f"frequencies={len(frequency_items)} ({[f.name for f in frequency_items]})")

            pattern_attributes = {
                "add_off_source": self.ui.addOffSourceCheck.isChecked(),
                "randomize_order": self.ui.randomizeOrderCheck.isChecked(),
                "interval_sec": self.ui.intervalSpinBox.value(),
                "naming_mask": naming_mask
            }

            attributes = {
                "sources": sources,
                "telescopes": telescopes,
                "frequencies": frequencies,
                "observation_type": observation_type,
                "time_range": {"start": start_time, "end": end_time},
                "scan_duration": scan_duration,
                "num_scans": num_scans,
                "pattern": pattern_attributes,
                "cancelled": False,
                "parallel": self.ui.chkParallel.isChecked()
            }

            self.thread = GenerationThread(self.manipulator, self.project, attributes)
            self.progress_dialog = ProgressDialog(self)
            self.thread.progress.connect(self.progress_dialog.update_progress)
            self.thread.finished.connect(self.generation_finished)
            self.thread.error.connect(self.generation_error)
            self.progress_dialog.cancelRequested.connect(self.thread.cancel)
            self.thread.start()
            self.progress_dialog.exec()

        except Exception as e:
            logger.error(f"Error during observation generation setup: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error setting up observation generation: {str(e)}")

    @Slot(dict)
    def generation_finished(self, response):
        """Handle generation completion."""
        self.progress_dialog.close()
        if response["status"]:
            self.observation_generated.emit(response["result"])
            self.accept()
        else:
            logger.error(f"Generation failed: {response.get('error', 'Unknown error')}. "
                        f"Partial results: {len(response.get('result', []))} observations")
            QMessageBox.critical(self, "Error", f"Generation failed: {response.get('error', 'Unknown error')}")
            self.reject()

    @Slot(str)
    def generation_error(self, error):
        """Handle generation errors."""
        self.progress_dialog.close()
        logger.error(f"Generation error: {error}")
        QMessageBox.critical(self, "Error", f"Generation failed: {error}")
        self.reject()

    def update_end_time(self):
        """Update end time based on current parameters."""
        start_qdt = self.ui.startTimeEdit.dateTime()
        scan_duration = self.ui.scanDurationSpinBox.value()
        num_scans = self.ui.numScansSpinBox.value()
        gap = self.ui.intervalSpinBox.value()
        is_parallel = self.ui.chkParallel.isChecked()
        num_sources = len(self.ui.sourceList.selectedItems()) if not is_parallel else 1

        if num_scans <= 0 or scan_duration <= 0 or gap < 0 or num_sources <= 0:
            logger.debug("Invalid parameters for end time update, skipping")
            return

        add_off_source = self.ui.addOffSourceCheck.isChecked()
        multiplier = 2 if add_off_source else 1
        scans_block = (scan_duration * multiplier + gap) * num_scans - gap
        total_seconds = round(scans_block if is_parallel else scans_block * num_sources)
        end_qdt = start_qdt.addSecs(int(total_seconds))
        self.ui.endTimeEdit.blockSignals(True)
        self.ui.endTimeEdit.setDateTime(end_qdt)
        self.ui.endTimeEdit.blockSignals(False)
        logger.debug(f"Updated end time: parallel={is_parallel}, num_sources={num_sources}, "
                    f"add_off={add_off_source}, total_seconds={total_seconds}, end={end_qdt.toString(Qt.ISODate)}")
    
    @Slot()
    def update_scan_duration_from_end(self):
        """Update scan duration to fit the end time based on other parameters."""
        start_qdt = self.ui.startTimeEdit.dateTime()
        end_qdt = self.ui.endTimeEdit.dateTime()
        if end_qdt <= start_qdt:
            QMessageBox.warning(self, "Invalid Time", "End time must be after start time.")
            self.update_end_time()
            return

        total_seconds = start_qdt.secsTo(end_qdt)
        num_scans = self.ui.numScansSpinBox.value()
        gap = self.ui.intervalSpinBox.value()
        is_parallel = self.ui.chkParallel.isChecked()
        add_off_source = self.ui.addOffSourceCheck.isChecked()
        multiplier = 2 if add_off_source else 1
        num_sources = len(self.ui.sourceList.selectedItems()) if not is_parallel else 1  # Factor for sequential

        if num_scans <= 0 or gap < 0 or num_sources <= 0:
            logger.debug("Invalid parameters for duration update, skipping")
            return

        gap_total = gap * (num_scans - 1) * num_sources if not is_parallel else gap * (num_scans - 1)
        remaining_seconds = total_seconds - gap_total
        if remaining_seconds <= 0:
            QMessageBox.warning(self, "Invalid Duration", "Total time too short for gaps.")
            self.update_end_time()
            return

        new_duration = remaining_seconds / (multiplier * num_scans * num_sources if not is_parallel else multiplier * num_scans)
        if new_duration <= 0:
            QMessageBox.warning(self, "Invalid Duration", "Calculated duration not positive.")
            self.update_end_time()
            return

        self.ui.scanDurationSpinBox.blockSignals(True)
        self.ui.scanDurationSpinBox.setValue(new_duration)
        self.ui.scanDurationSpinBox.blockSignals(False)
        logger.debug(f"Updated scan duration from end: new_duration={new_duration}, total_seconds={total_seconds}, "
                     f"multiplier={multiplier}, num_sources={num_sources}")