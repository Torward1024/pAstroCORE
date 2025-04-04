from abc import ABC, abstractmethod
from typing import List, Dict, Any
from common.utils.validation import check_non_empty_string
from common.utils.logging_setup import logger

class Project(ABC):
    """Abstract base class for project containers managed by Manipulator"""
    def __init__(self, name: str = "ABSTRACT_PROJECT_DEFAULT", items: List[Any] = None):
        """Initialize an abstract project with a name and optional list of items."""
        check_non_empty_string(name, "Project name")
        self._name = name
        self._items = items if items else []
        logger.info(f"Initialized AbstractProject '{name}' with {len(self._items)} items")

    def add_item(self, item: Any) -> None:
        """Add an item to the project"""
        self._items.append(item)
        logger.info(f"Added item to AbstractProject '{self._name}'")

    @abstractmethod
    def create_item(self, item_code: str = "ITEM_DEFAULT", isactive: bool = True) -> None:
        """Create and add a new item to the project"""
        pass

    def insert_item(self, item: Any, index: int) -> None:
        """Insert an item at the specified index"""
        if not (0 <= index <= len(self._items)):
            logger.error(f"Invalid index {index} for insertion in AbstractProject '{self._name}' with {len(self._items)} items")
            raise IndexError(f"Index {index} out of range for Project with {len(self._items)} items")
        self._items.insert(index, item)
        logger.info(f"Inserted item at index {index} in AbstractProject '{self._name}'")

    def remove_item(self, index: int) -> None:
        """Remove an item at the specified index"""
        if not (0 <= index < len(self._items)):
            logger.error(f"Invalid index {index} for removal in AbstractProject '{self._name}' with {len(self._items)} items")
            raise IndexError(f"Index {index} out of range for Project with {len(self._items)} items")
        self._items.pop(index)
        logger.info(f"Removed item from AbstractProject '{self._name}' at index {index}")

    def set_item(self, item: Any, index: int) -> None:
        """Set an item at the specified index"""
        if not (0 <= index < len(self._items)):
            logger.error(f"Invalid index {index} for setting item in AbstractProject '{self._name}' with {len(self._items)} items")
            raise IndexError(f"Index {index} out of range for Project with {len(self._items)} items")
        self._items[index] = item
        logger.info(f"Set item at index {index} in AbstractProject '{self._name}'")

    def get_by_index(self, index: int) -> Any:
        """Get an item at the specified index"""
        if not (0 <= index < len(self._items)):
            logger.error(f"Invalid index {index} for retrieval in AbstractProject '{self._name}' with {len(self._items)} items")
            raise IndexError(f"Index {index} out of range for Project with {len(self._items)} items")
        item = self._items[index]
        logger.info(f"Retrieved item from AbstractProject '{self._name}' at index {index}")
        return item

    def get_items(self) -> List[Any]:
        """Get all items in the project"""
        return self._items

    def to_dict(self) -> Dict[str, Any]:
        """Convert project to a dictionary for serialization"""
        return {"name": self._name, "items": [item for item in self._items]}

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Create a project from a dictionary"""
        pass

    def get_name(self) -> str:
        """Get the project name"""
        return self._name

    def set_name(self, name: str) -> None:
        """Set the project name"""
        check_non_empty_string(name, "Project name")
        self._name = name
        logger.info(f"Set Project name to '{name}'")

    def __repr__(self) -> str:
        """String representation of Project"""
        return f"AbstractProject(name='{self._name}', items_count={len(self._items)})"