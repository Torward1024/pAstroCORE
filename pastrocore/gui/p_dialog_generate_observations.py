from PySide6.QtWidgets import QDialog, QMessageBox, QMenu, QFileDialog, QListWidgetItem
from PySide6.QtCore import Signal, Slot, Qt, QPoint, QThread, QRegularExpression, QDateTime, QTime, QDate
from PySide6.QtGui import QIcon, QRegularExpressionValidator
from .ui_dialog_generate_observations import Ui_GenerateObservationsDialog
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.utils.catalogmanager import CatalogManager
from pastrocore.base.frequencies import Frequencies
from pastrocore.base.sources import Sources
from pastrocore.base.telescopes import Telescopes
from pastrocore.gui.p_dialog_edit_if import IFEditorDialog
from pastrocore.gui.p_dialog_sources_catalog import SourcesCatalogDialog
from pastrocore.gui.p_dialog_telescopes_catalog import TelescopesCatalogDialog
from pastrocore.gui.p_dialog_edit_source import SourceEditorDialog
from pastrocore.gui.p_dialog_edit_telescope import TelescopeEditorDialog
from pastrocore.gui.p_dialog_edit_space_telescope import SpaceTelescopeEditorDialog
from pastrocore.gui.p_dialog_progress import ProgressDialog, stop_and_wait
from msb_arch.utils.logging_setup import logger
import json
from datetime import datetime, timedelta

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
            # The generator's own answer, passed on as it is: it already says whether anything
            # was made, and what. Wrapping it as `{"status": True, "result": answer}` made
            # every run a success -- a range too short for a single observation closed the
            # dialog as if it had worked, and nobody was told why nothing appeared.
            answer = self.manipulator.configure(obj=self.project, generate_observations=self.attributes)
            self.finished.emit(answer if isinstance(answer, dict) else
                               {"status": False, "error": f"Unexpected answer: {answer!r}", "result": []})
        except Exception as e:
            logger.error("Error in GenerationThread: %s", str(e))
            self.error.emit(str(e))

class GenerateObservationsDialog(QDialog):
    """Dialog for generating observations in pAstroCORE."""
    observation_generated = Signal(list)

    def done(self, result):
        """Close, but never ahead of the work this dialog started."""
        stop_and_wait(self.worker)
        super().done(result)

    def __init__(self, project: ScheduleProject, manipulator: ScheduleManipulator, 
                 catalog_manager: CatalogManager, parent=None):
        super().__init__(parent)
        # Not `thread`: that name is `QObject.thread()`, and a dialog that had started nothing
        # found the method there, failed on `isRunning`, and would not close.
        self.worker = None
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
        self.load_presets()

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
        self.ui.presetCombo.currentIndexChanged.connect(self.apply_preset)
        self.ui.savePresetButton.clicked.connect(self.save_plan)
        self.ui.loadPresetButton.clicked.connect(self.load_plan)

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
                logger.info("Added frequency '%s' to frequencies collection", if_obj.name)
            except Exception as e:
                logger.error("Failed to add frequency: %s", str(e))
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
                    # The editor writes what is on screen into the band and hands it back; there
                    # was a `get_if_data` here, which it has never had, so editing a band in the
                    # generator has always ended in an error box.
                    edited = dialog.get_if_object()
                    self.update_frequency_list()
                    logger.info("Edited frequency '%s'", edited.name)
                except Exception as e:
                    logger.error("Failed to edit frequency: %s", str(e))
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
            logger.info("Removed frequency '%s' from frequencies collection", name)

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
            logger.debug("Moved source '%s' up to position %s", self._source_order[current_row - 1], current_row)

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
            logger.debug("Moved source '%s' down to position %s", self._source_order[current_row + 1], current_row + 2)

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
                logger.info("Added source '%s' manually to sources collection", source.name)
            except Exception as e:
                logger.error("Failed to add source manually: %s", str(e))
                QMessageBox.critical(self, "Error", f"Failed to add source: {str(e)}")

    @Slot()
    def add_sources_from_catalog(self):
        """Add sources from catalog."""
        dialog = SourcesCatalogDialog(self.catalog_manager, self.manipulator, parent=self,
                                       allow_selection=True)
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
                logger.info("Skipped source '%s' as it already exists in sources collection", source.name)
                continue
            self.sources.add(source)
            self._source_order.append(source.name)
            added_count += 1
            logger.info("Added source '%s' from catalog to sources collection", source.name)
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
            logger.info("Removed source '%s' from sources collection", name)

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
                logger.info("Added telescope '%s' to telescopes collection", telescope.name)
                QMessageBox.information(self, "Success", f"Added telescope '{telescope.name}'.")
            except Exception as e:
                logger.error("Failed to add telescope manually: %s", str(e))
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
                logger.info("Added space telescope '%s' to telescopes collection", telescope.name)
                QMessageBox.information(self, "Success", f"Added space telescope '{telescope.name}'.")
            except Exception as e:
                logger.error("Failed to add space telescope manually: %s", str(e))
                QMessageBox.critical(self, "Error", f"Failed to add space telescope: {str(e)}")

    @Slot()
    def add_telescopes_from_catalog(self):
        """Add telescopes from catalog."""
        dialog = TelescopesCatalogDialog(self.catalog_manager, self.manipulator, parent=self,
                                          allow_selection=True)
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
                logger.info("Skipped telescope '%s' as it already exists in telescopes collection", name)
                continue
            self.telescopes.add(telescope)
            self._telescope_order.append(name)
            added_count += 1
            logger.info("Added telescope '%s' from catalog to telescopes collection", name)
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
            logger.info("Removed telescope '%s' from telescopes collection", name)

    @Slot()
    def generate(self):
        """Generate the observations the plan describes, in a thread.

        Notes:
            - **The request is the plan.** What was here built the generator's attributes by hand
              from the widgets, one of which -- the end time -- the dialog had worked out with its
              own copy of the generator's arithmetic.
        """
        try:
            plan = self.plan()
            if not plan["sources"].get_all():
                raise ValueError("No sources selected")
            if not plan["telescopes"].get_all():
                raise ValueError("No telescopes selected")
            if not plan["frequencies"].get_all():
                raise ValueError("No frequencies added")
            if plan["scan_duration"] <= 0:
                raise ValueError("Scan duration must be positive")
            if plan["num_scans"] <= 0:
                raise ValueError("Number of scans must be positive")
            if not plan["naming_mask"]:
                raise ValueError("Naming mask cannot be empty")
            if not self.span().get("total"):
                raise ValueError("The pattern takes no time at all")

            logger.debug("Generating: %s source(s), %s station(s), %s band(s), %s s in all",
                         len(plan["sources"].get_all()), len(plan["telescopes"].get_all()),
                         len(plan["frequencies"].get_all()), self.span().get("total"))

            attributes = {"plan": plan, "cancelled": False}

            self.worker = GenerationThread(self.manipulator, self.project, attributes)
            self.progress_dialog = ProgressDialog(self, "Generating Observations",
                                                  "Generating observations...")
            self.worker.progress.connect(self.progress_dialog.update_progress)
            self.worker.finished.connect(self.generation_finished)
            self.worker.error.connect(self.generation_error)
            self.progress_dialog.cancelRequested.connect(self.worker.cancel)
            self.worker.start()
            self.progress_dialog.exec()

        except Exception as e:
            logger.error("Error during observation generation setup: %s", str(e))
            QMessageBox.critical(self, "Error", f"Error setting up observation generation: {str(e)}")

    @Slot(dict)
    def generation_finished(self, response):
        """Handle generation completion."""
        self.progress_dialog.finish()
        made = list(response.get("result") or [])
        if response.get("status"):
            self.observation_generated.emit(made)
            self.accept()
            return

        # Whatever was made before a cancel or a failure is in the project already, so the
        # project explorer has to hear about it either way.
        if made:
            self.observation_generated.emit(made)
        if response.get("cancelled"):
            logger.info("Generation cancelled after %s observation(s)", len(made))
            if made:
                self.accept()
            else:
                self.reject()
            return
        logger.error("Generation failed: %s. Partial results: %s observations",
                     response.get("error", "Unknown error"), len(made))
        QMessageBox.critical(self, "Error", f"Generation failed: {response.get('error', 'Unknown error')}")
        self.reject()

    @Slot(str)
    def generation_error(self, error):
        """Handle generation errors."""
        self.progress_dialog.finish()
        logger.error("Generation error: %s", error)
        QMessageBox.critical(self, "Error", f"Generation failed: {error}")
        self.reject()

    # --- the dialog as a plan (O1) -----------------------------------------------------------

    def plan(self) -> dict:
        """What the dialog is describing: what is selected, and the pattern the fields set.

        Returns:
            dict: The plan as a request carries it -- plain fields, and the collections themselves.

        Notes:
            - **One thing to send, and the backend answers everything about it.** How long the
              pattern takes, what a preset is and what a saved plan holds were worked out here
              before, in parallel with the generator's own arithmetic. Nothing here converts a
              model object: what crosses is a request.
        """
        def chosen(widget, kind):
            picked = [item.data(Qt.UserRole) for item in widget.selectedItems()]
            return kind(items={item.name: item for item in picked})

        return {
            "observation_type": self.ui.observationTypeCombo.currentText(),
            "start": self.ui.startTimeEdit.dateTime().toPython(),
            "scan_duration": self.ui.scanDurationSpinBox.value(),
            "num_scans": self.ui.numScansSpinBox.value(),
            "interval_sec": self.ui.intervalSpinBox.value(),
            "add_off_source": self.ui.addOffSourceCheck.isChecked(),
            "parallel": self.ui.chkParallel.isChecked(),
            "naming_mask": self.ui.namingMaskEdit.text(),
            "sources": chosen(self.ui.sourceList, Sources),
            "telescopes": chosen(self.ui.telescopeList, Telescopes),
            "frequencies": chosen(self.ui.frequencyList, Frequencies),
        }

    def show_plan(self, plan: dict, with_collections: bool = False):
        """Put a plan into the dialog.

        Args:
            plan (dict): A plan's fields, as a preset offers them or as reading one gives them back.
            with_collections (bool): Also show the plan's sources, stations and bands, selected. A
                preset carries none and leaves the selection alone; a plan read from a file carries
                all three, which is the whole point of saving one.
        """
        if plan.get("observation_type"):
            self.ui.observationTypeCombo.setCurrentText(plan["observation_type"])
        if plan.get("start"):
            self.ui.startTimeEdit.setDateTime(QDateTime(plan["start"]))
        for widget, value in ((self.ui.scanDurationSpinBox, plan.get("scan_duration")),
                              (self.ui.numScansSpinBox, plan.get("num_scans")),
                              (self.ui.intervalSpinBox, plan.get("interval_sec"))):
            if value is None:
                continue
            widget.blockSignals(True)
            widget.setValue(value)
            widget.blockSignals(False)
        self.ui.addOffSourceCheck.setChecked(bool(plan.get("add_off_source")))
        self.ui.chkParallel.setChecked(bool(plan.get("parallel")))
        if plan.get("naming_mask"):
            self.ui.namingMaskEdit.setText(plan["naming_mask"])

        if with_collections:
            for collection, order, refresh, widget in (
                    ("sources", "_source_order", self.update_source_list, self.ui.sourceList),
                    ("telescopes", "_telescope_order", self.update_telescope_list,
                     self.ui.telescopeList),
                    ("frequencies", "_frequency_order", self.update_frequency_list,
                     self.ui.frequencyList)):
                held = plan.get(collection)
                if held is None:
                    continue
                setattr(self, collection, held)
                setattr(self, order, list(held.get_all().keys()))
                refresh()
                widget.selectAll()

        self.update_end_time()

    @Slot()
    def load_presets(self):
        """Fill the preset list from the backend, because the interface lists nothing itself."""
        self.ui.presetCombo.blockSignals(True)
        self.ui.presetCombo.clear()
        self.ui.presetCombo.addItem("Preset...", None)
        for preset in (self.manipulator.inspect(obj=self.project, get_generation_presets=None) or []):
            self.ui.presetCombo.addItem(preset["name"], preset["plan"])
        self.ui.presetCombo.blockSignals(False)

    @Slot(int)
    def apply_preset(self, index: int):
        """Take the pattern of the chosen preset, and leave the selection as it is."""
        held = self.ui.presetCombo.itemData(index)
        if not held:
            return
        self.show_plan(held)
        logger.info("Applied the '%s' preset", self.ui.presetCombo.itemText(index))

    @Slot()
    def save_plan(self):
        """Write the whole plan -- pattern, times, and what it is for -- to a file."""
        path, _ = QFileDialog.getSaveFileName(self, "Save Generation Plan", "",
                                              "Generation plan (*.json)")
        if not path:
            return
        answer = self.manipulator.export(obj=self.project, method="generation_plan", path=path,
                                         plan=self.plan(), raise_on_error=False)
        if not answer.ok:
            logger.error("Failed to save the generation plan: %s", answer.error)
            QMessageBox.critical(self, "Error", f"Could not save the plan: {answer.error}")
            return
        logger.info("Saved the generation plan to '%s'", path)

    @Slot()
    def load_plan(self):
        """Read a plan back into the dialog, collections and all."""
        path, _ = QFileDialog.getOpenFileName(self, "Load Generation Plan", "",
                                              "Generation plan (*.json)")
        if not path:
            return
        answer = self.manipulator.load(obj=self.project, method="generation_plan", path=path,
                                       raise_on_error=False)
        if not answer.ok:
            logger.error("Failed to read the generation plan: %s", answer.error)
            QMessageBox.critical(self, "Error", f"Could not read the plan: {answer.error}")
            return
        self.show_plan(answer.value or {}, with_collections=True)
        logger.info("Loaded the generation plan from '%s'", path)

    # --- how long it takes, which is the backend's arithmetic ---------------------------------

    def span(self) -> dict:
        """How long what the dialog shows would take, asked of the backend."""
        return self.manipulator.inspect(obj=self.project,
                                        get_generation_span={"plan": self.plan()}) or {}

    @Slot()
    def update_end_time(self):
        """Show when the plan would end, as the backend works it out."""
        span = self.span()
        if not span.get("end"):
            logger.debug("No end time for this plan yet")
            return
        self.ui.endTimeEdit.blockSignals(True)
        self.ui.endTimeEdit.setDateTime(QDateTime.fromString(span["end"], "yyyy-MM-dd HH:mm:ss"))
        self.ui.endTimeEdit.blockSignals(False)
        logger.debug("The plan takes %s s and ends at %s", span.get("total"), span["end"])

    @Slot()
    def update_scan_duration_from_end(self):
        """An end time typed in is a scan duration: ask which one fits."""
        start_qdt = self.ui.startTimeEdit.dateTime()
        end_qdt = self.ui.endTimeEdit.dateTime()
        if end_qdt <= start_qdt:
            QMessageBox.warning(self, "Invalid Time", "End time must be after start time.")
            self.update_end_time()
            return

        duration = self.manipulator.inspect(
            obj=self.project,
            get_generation_scan_duration={"plan": self.plan(),
                                          "seconds": start_qdt.secsTo(end_qdt)})
        if not duration:
            QMessageBox.warning(self, "Invalid Duration",
                                "That is not long enough for the scans and the gaps between them.")
            self.update_end_time()
            return

        self.ui.scanDurationSpinBox.blockSignals(True)
        self.ui.scanDurationSpinBox.setValue(duration)
        self.ui.scanDurationSpinBox.blockSignals(False)
