from PySide6.QtWidgets import QDialog, QMessageBox, QMenu, QFileDialog, QListWidgetItem
from PySide6.QtCore import Signal, Slot, Qt, QPoint, QThread, QRegularExpression
from PySide6.QtGui import QIcon, QRegularExpressionValidator
from .ui_dialog_generate_observations import Ui_GenerateObservationsDialog
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.utils.catalogmanager import CatalogManager
from pastrocore.base.frequencies import IF, Frequencies
from pastrocore.base.sources import Sources
from pastrocore.base.telescopes import Telescopes
from pastrocore.gui.p_dialog_edit_if import IFEditorDialog
from pastrocore.gui.p_dialog_sources_catalog import SourcesCatalogDialog
from pastrocore.gui.p_dialog_telescopes_catalog import TelescopesCatalogDialog
from .ui_dialog_calc_progress import Ui_ProgressDialog
from common.utils.logging_setup import logger
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
            response = self.manipulator.process_request({
                "operation": "configure",
                "obj": self.project,
                "attributes": {"generate_observations": self.attributes}
            })
            if response["status"]:
                self.finished.emit(response)
            else:
                self.error.emit(response["error"])
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
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """Populate lists and set up initial UI state."""
        # Populate source list
        sources = self.catalog_manager.source_catalog.get_items()
        for source in sources:
            item = QListWidgetItem(source.name)
            item.setData(Qt.UserRole, source)
            self.ui.sourceList.addItem(item)

        # Populate telescope list
        telescopes = self.catalog_manager.telescope_catalog.get_items()
        for telescope in telescopes:
            item = QListWidgetItem(telescope.get("name"))
            item.setData(Qt.UserRole, telescope)
            self.ui.telescopeList.addItem(item)

        # Set context menu policies
        self.ui.sourceList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.telescopeList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.frequencyList.setContextMenuPolicy(Qt.CustomContextMenu)
        
        # Set default naming mask
        self.ui.namingMaskEdit.setText("Observation_{i}_{s}_{dt}")
        # Add validator for naming mask
        mask_validator = QRegularExpressionValidator(QRegularExpression(r'^[a-zA-Z0-9_{}]+$'))
        self.ui.namingMaskEdit.setValidator(mask_validator)
        
        # Set pattern defaults
        self.ui.addOffSourceCheck.setChecked(False)
        self.ui.randomizeOrderCheck.setChecked(False)
        self.ui.intervalSpinBox.setValue(5)
        
        # Set default time range
        current_time = datetime.now()
        self.ui.startTimeEdit.setDateTime(current_time)
        self.ui.endTimeEdit.setDateTime(current_time + timedelta(hours=24))
        
        self.update_frequency_list()

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

    def update_frequency_list(self):
        """Update the frequency list UI from self.frequencies."""
        self.ui.frequencyList.clear()
        for name, if_obj in self.frequencies.get_all().items():
            item = QListWidgetItem(f"{if_obj.frequency:.0f} MHz, BW: {if_obj.bandwidth:.0f} MHz, Pol: {', '.join(if_obj.polarizations)}")
            item.setData(Qt.UserRole, if_obj)
            item.setData(Qt.UserRole + 1, name)
            self.ui.frequencyList.addItem(item)

    @Slot(QPoint)
    def show_source_context_menu(self, position: QPoint):
        """Show context menu for the sources list."""
        menu = QMenu(self)
        add_catalog_action = menu.addAction(QIcon(":/icons/import_icon.svg"), "Add from Catalog")
        add_catalog_action.triggered.connect(self.add_sources_from_catalog)
        index = self.ui.sourceList.indexAt(position)
        if index.isValid():
            menu.addSeparator()
            remove_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Remove Source")
            remove_action.triggered.connect(lambda: self.remove_source(index.row()))
        menu.exec(self.ui.sourceList.viewport().mapToGlobal(position))

    @Slot()
    def add_sources_from_catalog(self):
        """Add sources from catalog to sourceList."""
        dialog = SourcesCatalogDialog(self.catalog_manager, parent=self, allow_selection=True)
        dialog.sources_selected.connect(self.handle_sources_selected)
        dialog.exec()

    @Slot(list)
    def handle_sources_selected(self, sources: list):
        """Handle sources selected from catalog."""
        existing_names = {self.ui.sourceList.item(i).data(Qt.UserRole).name for i in range(self.ui.sourceList.count())}
        added_count = 0
        for source in sources:
            if source.name not in existing_names:
                item = QListWidgetItem(source.name)
                item.setData(Qt.UserRole, source)
                self.ui.sourceList.addItem(item)
                added_count += 1
                logger.info(f"Added source '{source.name}' from catalog to source list")
        if added_count:
            QMessageBox.information(self, "Success", f"Added {added_count} source(s) from catalog.")
        else:
            QMessageBox.warning(self, "Warning", "No new sources added (all selected sources already in list).")

    @Slot(int)
    def remove_source(self, row: int):
        """Remove a source from sourceList."""
        item = self.ui.sourceList.takeItem(row)
        logger.info(f"Removed source '{item.data(Qt.UserRole).name}' from source list")

    @Slot(QPoint)
    def show_telescope_context_menu(self, position: QPoint):
        """Show context menu for the telescopes list."""
        menu = QMenu(self)
        add_catalog_action = menu.addAction(QIcon(":/icons/import_icon.svg"), "Add from Catalog")
        add_catalog_action.triggered.connect(self.add_telescopes_from_catalog)
        index = self.ui.telescopeList.indexAt(position)
        if index.isValid():
            menu.addSeparator()
            remove_action = menu.addAction(QIcon(":/icons/remove_icon.svg"), "Remove Telescope")
            remove_action.triggered.connect(lambda: self.remove_telescope(index.row()))
        menu.exec(self.ui.telescopeList.viewport().mapToGlobal(position))

    @Slot()
    def add_telescopes_from_catalog(self):
        """Add telescopes from catalog to telescopeList."""
        dialog = TelescopesCatalogDialog(self.catalog_manager, parent=self, allow_selection=True)
        dialog.telescopes_selected.connect(self.handle_telescopes_selected)
        dialog.exec()

    @Slot(list)
    def handle_telescopes_selected(self, telescopes: list):
        """Handle telescopes selected from catalog."""
        existing_names = {self.ui.telescopeList.item(i).data(Qt.UserRole).get("name") for i in range(self.ui.telescopeList.count())}
        added_count = 0
        for telescope in telescopes:
            name = telescope.get("name")
            if name not in existing_names:
                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, telescope)
                self.ui.telescopeList.addItem(item)
                added_count += 1
                logger.info(f"Added telescope '{name}' from catalog to telescope list")
        if added_count:
            QMessageBox.information(self, "Success", f"Added {added_count} telescope(s) from catalog.")
        else:
            QMessageBox.warning(self, "Warning", "No new telescopes added (all selected telescopes already in list).")

    @Slot(int)
    def remove_telescope(self, row: int):
        """Remove a telescope from telescopeList."""
        item = self.ui.telescopeList.takeItem(row)
        logger.info(f"Removed telescope '{item.data(Qt.UserRole).get('name')}' from telescope list")

    @Slot(QPoint)
    def show_frequency_context_menu(self, position: QPoint):
        """Show context menu for the frequencies list."""
        menu = QMenu(self)
        add_action = menu.addAction(QIcon(":/icons/add_icon.svg"), "Add Frequency")
        import_action = menu.addAction(QIcon(":/icons/import_icon.svg"), "Import Frequency")
        export_action = menu.addAction(QIcon(":/icons/export_icon.svg"), "Export All Frequencies")
        add_action.triggered.connect(self.add_frequency)
        import_action.triggered.connect(self.import_frequency)
        export_action.triggered.connect(self.export_frequencies)

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
                if_data = dialog.get_if_data()
                if_id = f"IF_{uuid.uuid4().hex[:8]}"
                if_obj = IF(
                    name=if_id,
                    frequency=if_data["frequency"],
                    bandwidth=if_data["bandwidth"],
                    polarizations=if_data["polarizations"],
                    isactive=if_data["isactive"]
                )
                self.frequencies.add(if_obj)
                self.update_frequency_list()
                logger.info(f"Added frequency '{if_id}' with {if_data['frequency']} MHz")
            except Exception as e:
                logger.error(f"Failed to add frequency: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to add frequency: {str(e)}")

    @Slot(int)
    def edit_frequency(self, row: int):
        """Edit an existing frequency using IFEditorDialog."""
        item = self.ui.frequencyList.item(row)
        if_obj = item.data(Qt.UserRole)
        if_name = item.data(Qt.UserRole + 1)
        dialog = IFEditorDialog(if_obj=if_obj, parent=self)
        if dialog.exec() == QDialog.Accepted:
            try:
                if_data = dialog.get_if_data()
                self.frequencies.update_item(
                    name=if_name,
                    frequency=if_data["frequency"],
                    bandwidth=if_data["bandwidth"],
                    polarizations=if_data["polarizations"],
                    isactive=if_data["isactive"]
                )
                self.update_frequency_list()
                logger.info(f"Edited frequency '{if_name}' with {if_data['frequency']} MHz")
            except Exception as e:
                logger.error(f"Failed to edit frequency: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to edit frequency: {str(e)}")

    @Slot(int)
    def remove_frequency(self, row: int):
        """Remove a frequency from the list."""
        item = self.ui.frequencyList.item(row)
        if_name = item.data(Qt.UserRole + 1)
        self.frequencies.drop_item(if_name)
        self.update_frequency_list()
        logger.info(f"Removed frequency '{if_name}'")

    @Slot()
    def import_frequency(self):
        """Import a frequency from a JSON file."""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Import Frequency", "", "JSON Files (*.json);;All Files (*)"
        )
        if file_name:
            try:
                with open(file_name, 'r') as f:
                    if_data = json.load(f)
                if_id = f"IF_{uuid.uuid4().hex[:8]}"
                if_obj = IF(
                    name=if_id,
                    frequency=if_data.get("frequency", 1000.0),
                    bandwidth=if_data.get("bandwidth", 16.0),
                    polarizations=if_data.get("polarizations", []),
                    isactive=if_data.get("isactive", True)
                )
                self.frequencies.add(if_obj)
                self.update_frequency_list()
                logger.info(f"Imported frequency '{if_id}' from {file_name}")
            except Exception as e:
                logger.error(f"Failed to import frequency: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to import frequency: {str(e)}")

    @Slot()
    def export_frequencies(self):
        """Export all frequencies to a JSON file."""
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Export Frequencies", "", "JSON Files (*.json);;All Files (*)"
        )
        if file_name:
            try:
                freq_data = []
                for name, if_obj in self.frequencies.get_all().items():
                    freq_data.append({
                        "name": name,
                        "frequency": if_obj.frequency,
                        "bandwidth": if_obj.bandwidth,
                        "polarizations": if_obj.polarizations,
                        "isactive": if_obj.isactive
                    })
                with open(file_name, 'w') as f:
                    json.dump(freq_data, f, indent=4)
                logger.info(f"Exported {len(freq_data)} frequencies to {file_name}")
            except Exception as e:
                logger.error(f"Failed to export frequencies: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to export frequencies: {str(e)}")

    @Slot()
    def move_source_up(self):
        """Move selected source up in sourceList."""
        current = self.ui.sourceList.currentRow()
        if current > 0:
            item = self.ui.sourceList.takeItem(current)
            self.ui.sourceList.insertItem(current - 1, item)
            self.ui.sourceList.setCurrentRow(current - 1)
            logger.debug(f"Moved source '{item.data(Qt.UserRole).name}' up to position {current - 1}")

    @Slot()
    def move_source_down(self):
        """Move selected source down in sourceList."""
        current = self.ui.sourceList.currentRow()
        if current < self.ui.sourceList.count() - 1:
            item = self.ui.sourceList.takeItem(current)
            self.ui.sourceList.insertItem(current + 1, item)
            self.ui.sourceList.setCurrentRow(current + 1)
            logger.debug(f"Moved source '{item.data(Qt.UserRole).name}' down to position {current + 1}")

    @Slot(int)
    def load_preset(self, index):
        """Load preset settings based on combo box selection."""
        preset = self.ui.presetCombo.currentText()
        if preset == "Standard VLBI":
            self.ui.addOffSourceCheck.setChecked(False)
            self.ui.randomizeOrderCheck.setChecked(False)
            self.ui.intervalSpinBox.setValue(10)
            logger.debug("Loaded Standard VLBI preset")
        elif preset == "Quick Single Dish":
            self.ui.addOffSourceCheck.setChecked(True)
            self.ui.randomizeOrderCheck.setChecked(True)
            self.ui.intervalSpinBox.setValue(2)
            logger.debug("Loaded Quick Single Dish preset")

    @Slot()
    def save_preset(self):
        """Save current pattern settings as a JSON preset."""
        preset_data = {
            "add_off_source": self.ui.addOffSourceCheck.isChecked(),
            "randomize_order": self.ui.randomizeOrderCheck.isChecked(),
            "interval_min": self.ui.intervalSpinBox.value()
        }
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Preset", "", "JSON Files (*.json)")
        if file_name:
            try:
                with open(file_name, 'w') as f:
                    json.dump(preset_data, f, indent=4)
                logger.info(f"Saved preset to {file_name}")
            except Exception as e:
                logger.error(f"Failed to save preset: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to save preset: {str(e)}")

    @Slot()
    def load_preset_from_file(self):
        """Load pattern settings from a JSON preset file."""
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Preset", "", "JSON Files (*.json)")
        if file_name:
            try:
                with open(file_name, 'r') as f:
                    preset_data = json.load(f)
                self.ui.addOffSourceCheck.setChecked(preset_data.get("add_off_source", False))
                self.ui.randomizeOrderCheck.setChecked(preset_data.get("randomize_order", False))
                self.ui.intervalSpinBox.setValue(preset_data.get("interval_min", 5))
                logger.info(f"Loaded preset from {file_name}")
            except Exception as e:
                logger.error(f"Failed to load preset: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to load preset: {str(e)}")

    @Slot()
    def generate(self):
        """Generate observations based on user inputs and start the generation thread."""
        try:
            # Clear previous observations in the project
            # self.project.clear()
            # logger.debug("Cleared previous observations in ScheduleProject")

            source_items = [item.data(Qt.UserRole) for item in self.ui.sourceList.selectedItems()]
            telescope_items = [item.data(Qt.UserRole) for item in self.ui.telescopeList.selectedItems()]
            observation_type = self.ui.observationTypeCombo.currentText()
            start_time = self.ui.startTimeEdit.dateTime().toPython()
            end_time = self.ui.endTimeEdit.dateTime().toPython()
            scan_duration = self.ui.scanDurationSpinBox.value()
            num_scans = self.ui.numScansSpinBox.value()
            naming_mask = self.ui.namingMaskEdit.text()

            # Create Sources and Telescopes objects
            sources = Sources(items={s.name: s for s in source_items})
            telescopes = Telescopes(items={t.name: t for t in telescope_items})

            # Validate inputs
            if not sources.get_all():
                raise ValueError("No sources selected")
            if not telescopes.get_all():
                raise ValueError("No telescopes selected")
            if not self.frequencies.get_all():
                raise ValueError("No frequencies added")
            if start_time >= end_time:
                raise ValueError("Start time must be before end time")
            if scan_duration <= 0:
                raise ValueError("Scan duration must be positive")
            if num_scans <= 0:
                raise ValueError("Number of scans must be positive")
            if not naming_mask:
                raise ValueError("Naming mask cannot be empty")

            # Log input collections
            logger.debug(f"Generating with: sources={len(source_items)} ({[s.name for s in source_items]}), "
                        f"telescopes={len(telescope_items)} ({[t.name for t in telescope_items]}), "
                        f"frequencies={len(self.frequencies.get_items())} ({[f.name for f in self.frequencies.get_items()]})")

            # Collect pattern settings
            pattern_attributes = {
                "add_off_source": self.ui.addOffSourceCheck.isChecked(),
                "randomize_order": self.ui.randomizeOrderCheck.isChecked(),
                "interval_min": self.ui.intervalSpinBox.value(),
                "naming_mask": naming_mask
            }

            attributes = {
                "sources": sources,
                "telescopes": telescopes,
                "frequencies": self.frequencies,
                "observation_type": observation_type,
                "time_range": {"start": start_time, "end": end_time},
                "scan_duration": scan_duration,
                "num_scans": num_scans,
                "pattern": pattern_attributes,
                "cancelled": False
            }

            # Create and start generation thread
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
            logger.info(f"Generated {len(response['result'])} observations")
            self.observation_generated.emit(response["result"])
            QMessageBox.information(self, "Success", "Observations generated successfully.")
            self.accept()
        else:
            logger.error(f"Generation failed: {response['error']}")
            QMessageBox.critical(self, "Error", f"Generation failed: {response['error']}")
            self.reject()

    @Slot(str)
    def generation_error(self, error):
        """Handle generation errors."""
        self.progress_dialog.close()
        logger.error(f"Generation error: {error}")
        QMessageBox.critical(self, "Error", f"Generation failed: {error}")
        self.reject()