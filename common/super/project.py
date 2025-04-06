# /common/super/project.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from common.utils.validation import check_non_empty_string
from common.utils.logging_setup import logger

class Project(ABC):
    """Abstract class for managing collections of items within a project.

    Serves as a foundation for specific project types managed by a Manipulator. Provides basic functionality
    for adding, inserting, removing, retrieving, and configuring projects and their items, with serialization
    support. Subclasses must implement `create_item` and `from_dict` methods to define item creation and
    deserialization logic.

    Attributes:
        _name (str): The name of the project, must be a non-empty string.
        _items (List[Any]): List of items contained within the project.

    Notes:
        - Logging is integrated via `common.utils.logging_setup.logger` to track operations and errors.
        - The class is abstract and cannot be instantiated directly; it requires subclassing.

    Examples:
        >>> class MyProject(Project):
        ...     def create_item(self, item_code="ITEM_DEFAULT", isactive=True):
        ...         self._items.append({"code": item_code, "active": isactive})
        ...     @classmethod
        ...     def from_dict(cls, data):
        ...         return cls(name=data["name"], items=data["items"])
        >>> proj = MyProject(name="TestProject")
        >>> proj.add_item({"code": "ITEM1"})
        >>> proj.set_project(name="NewProject", items=[])
        >>> proj.get_project()
        {'name': 'NewProject', 'items': []}
    """
    def __init__(self, name: str = "DEFAULT_PROJECT", items: List[Any] = None):
        """Initialize a Project with a name and an optional list of items.

        Args:
            name (str): The name of the project. Must be a non-empty string. Defaults to "DEFAULT_PROJECT".
            items (List[Any], optional): Initial list of items. Defaults to None (empty list).

        Raises:
            TypeError: If name is not a string.
            ValueError: If name is empty.
        """
        check_non_empty_string(name, "Project name")
        self._name = name
        self._items = items if items else []
        logger.info(f"Initialized project '{name}' with {len(self._items)} items")

    def add_item(self, item: Any) -> None:
        """Add an item to the project's collection.

        Args:
            item (Any): The item to add to the project.

        Notes:
            - No type checking is performed on the item; it is the responsibility of subclasses to enforce type constraints if needed.
        """
        self._items.append(item)
        logger.info(f"Added item to project '{self._name}'")

    @abstractmethod
    def create_item(self, item_code: str = "ITEM_DEFAULT", isactive: bool = True) -> None:
        """Create and add a new item to the project.

        Abstract method to be implemented by subclasses to define how new items are created and added.

        Args:
            item_code (str): Identifier for the new item. Defaults to "ITEM_DEFAULT".
            isactive (bool): Activation status of the new item. Defaults to True.
        """
        pass

    def insert_item(self, item: Any, index: int) -> None:
        """Insert an item at a specified index in the project's collection.

        Args:
            item (Any): The item to insert.
            index (int): The position to insert the item (0 to len(items)).

        Raises:
            IndexError: If index is out of range (less than 0 or greater than the current number of items).
        """
        if not (0 <= index <= len(self._items)):
            logger.error(f"Invalid index {index} for insertion in project '{self._name}' with {len(self._items)} items")
            raise IndexError(f"Index {index} out of range for Project with {len(self._items)} items")
        self._items.insert(index, item)
        logger.info(f"Inserted item at index {index} in project '{self._name}'")

    def remove_item(self, index: int) -> None:
        """Remove an item from the project at the specified index.

        Args:
            index (int): The index of the item to remove.

        Raises:
            IndexError: If index is out of range (less than 0 or greater than or equal to the number of items).
        """
        if not (0 <= index < len(self._items)):
            logger.error(f"Invalid index {index} for removal in project '{self._name}' with {len(self._items)} items")
            raise IndexError(f"Index {index} out of range for Project with {len(self._items)} items")
        self._items.pop(index)
        logger.info(f"Removed item from project '{self._name}' at index {index}")

    def set_item(self, item: Any, index: int) -> None:
        """Replace an item at the specified index with a new item.

        Args:
            item (Any): The new item to set.
            index (int): The index of the item to replace.

        Raises:
            IndexError: If index is out of range (less than 0 or greater than or equal to the number of items).
        """
        if not (0 <= index < len(self._items)):
            logger.error(f"Invalid index {index} for setting item in project '{self._name}' with {len(self._items)} items")
            raise IndexError(f"Index {index} out of range for Project with {len(self._items)} items")
        self._items[index] = item
        logger.info(f"Set item at index {index} in project '{self._name}'")

    def get_by_index(self, index: int) -> Any:
        """Retrieve an item from the project by its index.

        Args:
            index (int): The index of the item to retrieve.

        Returns:
            Any: The item at the specified index.

        Raises:
            IndexError: If index is out of range (less than 0 or greater than or equal to the number of items).
        """
        if not (0 <= index < len(self._items)):
            logger.error(f"Invalid index {index} for retrieval in project '{self._name}' with {len(self._items)} items")
            raise IndexError(f"Index {index} out of range for Project with {len(self._items)} items")
        item = self._items[index]
        logger.info(f"Retrieved item from project '{self._name}' at index {index}")
        return item

    def get_items(self) -> List[Any]:
        """Retrieve all items in the project.

        Returns:
            List[Any]: A list of all items in the project.
        """
        return self._items

    def get_name(self) -> str:
        """Retrieve the project's name.

        Returns:
            str: The name of the project.

        Notes:
            - Provides access to the project's name attribute for external use or inspection.
        """
        logger.info(f"Retrieved name '{self._name}' for project")
        return self._name

    def set_name(self, name: str) -> None:
        """Set the project's name.

        Args:
            name (str): The new name for the project. Must be a non-empty string.

        Raises:
            TypeError: If name is not a string.
            ValueError: If name is empty.

        Notes:
            - Updates the project name and logs the change.
        """
        check_non_empty_string(name, "Project name")
        old_name = self._name
        self._name = name
        logger.info(f"Project name changed from '{old_name}' to '{name}'")

    def set_project(self, name: str, items: List[Any]) -> None:
        """Set the entire project configuration, replacing name and items.

        Args:
            name (str): The new name for the project. Must be a non-empty string.
            items (List[Any]): The new list of items to set.

        Raises:
            TypeError: If name is not a string.
            ValueError: If name is empty.

        Notes:
            - Replaces the current project name and items list with the provided values.
            - No type checking is performed on items; subclasses should enforce type constraints if needed.
            - Logs the update with the new name and item count.
        """
        check_non_empty_string(name, "Project name")
        old_name = self._name
        old_count = len(self._items)
        self._name = name
        self._items = items.copy()  # Используем копию для безопасности
        logger.info(f"Project updated: name changed from '{old_name}' to '{name}', "
                    f"items count changed from {old_count} to {len(self._items)}")

    def get_project(self) -> Dict[str, Any]:
        """Get the entire project configuration as a dictionary.

        Returns:
            Dict[str, Any]: A dictionary containing the project name and a list of items.
                - "name": The project name (str).
                - "items": List of items.

        Notes:
            - Provides a complete snapshot of the project state.
            - Items are included as-is; subclasses may override to_dict() for custom serialization.
        """
        result = {"name": self._name, "items": [item for item in self._items]}
        logger.info(f"Retrieved project configuration for '{self._name}' with {len(self._items)} items")
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert the project to a dictionary for serialization.

        Returns:
            Dict[str, Any]: A dictionary with 'name' and 'items' keys.

        Notes:
            - Items are included as-is; subclasses should override for custom item serialization if needed.
        """
        return {"name": self._name, "items": [item for item in self._items]}

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Create a project instance from a dictionary.

        Abstract method to be implemented by subclasses to define deserialization logic.

        Args:
            data (Dict[str, Any]): Dictionary containing project data, typically from `to_dict`.

        Returns:
            Project: A new instance of the subclass initialized with the dictionary data.
        """
        pass

    def __repr__(self) -> str:
        """Return a string representation of the Project.

        Returns:
            str: A formatted string with the project name and item count.
        """
        return f"Project(name='{self._name}', items_count={len(self._items)})"