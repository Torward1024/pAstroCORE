# /gui/project_explorer.py
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu
from PySide6.QtCore import Signal, Qt, QPoint
from common.utils.logging_setup import logger
from unit_scheduling.super.schedule_manipulator import ScheduleManipulator
from unit_scheduling.super.schedule_project import ScheduleProject
from unit_scheduling.base.observation import Observation
from typing import Optional, Dict, Any

class ProjectExplorer(QTreeWidget):
    """Tree widget displaying the hierarchy of Projects and their components.

    Emits signals when items are modified to enable two-way communication with the Manipulator.
    Provides a context menu for adding, inserting, and removing observations.

    Signals:
        item_changed (dict): Emitted when an item is modified, carrying updated attributes.

    Attributes:
        manipulator: The ScheduleManipulator instance managing the project.
    """
    item_changed = Signal(dict)

    def __init__(self, manipulator: ScheduleManipulator, parent=None):
        """Initialize the ProjectExplorer."""
        super().__init__(parent)
        self.manipulator = manipulator
        self.setHeaderLabel("Project Hierarchy")
        self.setDragDropMode(QTreeWidget.InternalMove)
        self.itemChanged.connect(self._on_item_edited)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._populate_tree()
        logger.info("Initialized ProjectExplorer")

    def _populate_tree(self) -> None:
        """Populate the tree with the current project structure."""
        self.clear()
        project = self.manipulator.get_managing_object()
        if project is None:
            logger.error("No managing object in manipulator")
            return
        project_item = QTreeWidgetItem(self, [project.get_name()])
        project_item.setData(0, Qt.UserRole, {"type": "Project"})
        project_item.setFlags(project_item.flags() | Qt.ItemIsEditable)

        for i, obs in enumerate(project.get_items()):
            obs_item = QTreeWidgetItem(project_item, [obs.get_observation_code()])
            obs_item.setData(0, Qt.UserRole, {"type": "Observation", "index": i})
            obs_item.setFlags(obs_item.flags() | Qt.ItemIsEditable)
            self._add_nested_items(obs_item, obs)
        self.expandAll()

    def _add_nested_items(self, parent_item: QTreeWidgetItem, obs: Observation) -> None:
        """Add nested components of an Observation to the tree."""
        telescopes = QTreeWidgetItem(parent_item, ["Telescopes"])
        telescopes.setData(0, Qt.UserRole, {"type": "Telescopes"})
        for i, tel in enumerate(obs.get_telescopes()):
            tel_item = QTreeWidgetItem(telescopes, [tel.get_code()])
            tel_item.setData(0, Qt.UserRole, {"type": "Telescope", "index": i})

        sources = QTreeWidgetItem(parent_item, ["Sources"])
        sources.setData(0, Qt.UserRole, {"type": "Sources"})
        for i, src in enumerate(obs.get_sources()):
            src_item = QTreeWidgetItem(sources, [src.get_name()])
            src_item.setData(0, Qt.UserRole, {"type": "Source", "index": i})

        scans = QTreeWidgetItem(parent_item, ["Scans"])
        scans.setData(0, Qt.UserRole, {"type": "Scans"})
        for i, scan in enumerate(obs.get_scans()):
            scan_item = QTreeWidgetItem(scans, [f"Scan {i}"])
            scan_item.setData(0, Qt.UserRole, {"type": "Scan", "index": i})

        freqs = QTreeWidgetItem(parent_item, ["Frequencies"])
        freqs.setData(0, Qt.UserRole, {"type": "Frequencies"})
        for i, freq in enumerate(obs.get_frequencies()):
            freq_item = QTreeWidgetItem(freqs, [f"{freq.get_frequency()} MHz"])
            freq_item.setData(0, Qt.UserRole, {"type": "IF", "index": i})

    def _on_item_edited(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle item edits and emit changes to Manipulator."""
        data = item.data(0, Qt.UserRole)
        new_value = item.text(0)
        update_dict = {"type": data["type"], "index": data.get("index")}
        if data["type"] == "Project":
            update_dict["method"] = "set_project"
            update_dict["attributes"] = {"name": new_value, "observations": self.manipulator.get_managing_object().get_items()}
        elif data["type"] == "Observation":
            update_dict["method"] = "set_observation_code"
            update_dict["attributes"] = {"code": new_value}
            update_dict["observation_index"] = data["index"]
        self.item_changed.emit(update_dict)

    def _show_context_menu(self, position: QPoint) -> None:
        """Show context menu at the specified position."""
        item = self.itemAt(position)
        if not item:
            return

        menu = QMenu(self)
        data = item.data(0, Qt.UserRole)

        if data["type"] == "Project":
            add_action = menu.addAction("Add Observation")
            add_action.triggered.connect(self._add_observation)
        elif data["type"] == "Observation":
            insert_action = menu.addAction("Insert Observation")
            remove_action = menu.addAction("Remove Observation")
            insert_action.triggered.connect(lambda: self._insert_observation(data["index"]))
            remove_action.triggered.connect(lambda: self._remove_observation(data["index"]))

        menu.exec_(self.viewport().mapToGlobal(position))

    def _add_observation(self) -> None:
        """Add a new observation to the project."""
        project = self.manipulator.get_managing_object()
        if project is None:
            logger.error("Cannot add observation: No managing object in manipulator")
            return
        request = {
            "operation": "configure",
            "obj": project,
            "method": "_configure_project",
            "attributes": {
                "method": "create_item",
                "attributes": {"item_code": f"OBS_{len(project.get_items()) + 1}"}
            }
        }
        success = self.manipulator.process_request(request)
        if success:
            self._populate_tree()
            logger.info("Added new observation to project")
        else:
            logger.error("Failed to add new observation")

    def _insert_observation(self, index: int) -> None:
        """Insert a new observation at the specified index."""
        project = self.manipulator.get_managing_object()
        if project is None:
            logger.error("Cannot insert observation: No managing object in manipulator")
            return
        new_obs = Observation(observation_code=f"OBS_INSERT_{index + 1}")
        request = {
            "operation": "configure",
            "obj": project,
            "method": "_configure_project",
            "attributes": {
                "method": "insert_item",
                "attributes": {"item": new_obs, "index": index}
            }
        }
        success = self.manipulator.process_request(request)
        if success:
            self._populate_tree()
            logger.info(f"Inserted observation at index {index}")
        else:
            logger.error(f"Failed to insert observation at index {index}")

    def _remove_observation(self, index: int) -> None:
        """Remove an observation at the specified index."""
        project = self.manipulator.get_managing_object()
        if project is None:
            logger.error("Cannot remove observation: No managing object in manipulator")
            return
        request = {
            "operation": "configure",
            "obj": project,
            "method": "_configure_project",
            "attributes": {
                "method": "remove_item",
                "attributes": {"index": index}
            }
        }
        success = self.manipulator.process_request(request)
        if success:
            self._populate_tree()
            logger.info(f"Removed observation at index {index}")
        else:
            logger.error(f"Failed to remove observation at index {index}")

    def get_selected_item(self) -> Optional[Dict[str, Any]]:
        """Get data of the currently selected item."""
        selected = self.currentItem()
        return selected.data(0, Qt.UserRole) if selected else None