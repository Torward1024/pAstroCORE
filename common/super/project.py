# /common/super/project.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type
from common.utils.validation import check_non_empty_string
from common.utils.logging_setup import logger
from common.base.basecontainer import BaseContainer
from common.base.baseentity import BaseEntity

class Project(ABC):
    """Abstract super-class for managing collections of BaseEntity items within a project using BaseContainer.

    Attributes:
        _name (str): The name of the project, must be a non-empty string.
        _items (BaseContainer[BaseEntity]): Container of BaseEntity items indexed by their names.
        _item_type (Type[BaseEntity]): The type of items stored in the container, defaults to BaseEntity.
    """
    _item_type: Type[BaseEntity] = BaseEntity

    def __init__(self, name: str = "DEFAULT_PROJECT", items: Optional[Dict[str, BaseEntity]] = None):
        """Initialize a Project with a name and an optional dictionary of BaseEntity items."""
        check_non_empty_string(name, "Project name")
        self._name = name
        self._items = self._create_container(items=items, name=f"{name}_items")
        logger.info(f"Initialized project '{name}' with {len(self._items)} items")

    @classmethod
    def _create_container(cls, items: Optional[Dict[str, BaseEntity]] = None, name: str = None) -> BaseContainer:
        """Create a BaseContainer instance with the specified item type."""
        class TypedContainer(BaseContainer[cls._item_type]):
            pass
        return TypedContainer(items=items, name=name)

    def add_item(self, item: BaseEntity) -> None:
        """Add a BaseEntity item to the project's container."""
        if not isinstance(item, self._item_type):
            raise TypeError(f"Item must be of type {self._item_type.__name__} for project '{self._name}', got {type(item).__name__}")
        self._items.add(item)
        logger.info(f"Added item '{item.name}' to project '{self._name}'")

    @abstractmethod
    def create_item(self, item_code: str = "ITEM_DEFAULT", isactive: bool = True) -> None:
        """Create and add a new BaseEntity item to the project."""
        pass

    def set_item(self, name: str, item: BaseEntity) -> None:
        """Set or replace an item in the project by its name."""
        if not isinstance(item, self._item_type):
            raise TypeError(f"Item must be of type {self._item_type.__name__} for project '{self._name}', got {type(item).__name__}")
        self._items.set_item(name, item)
        logger.info(f"Set item '{name}' in project '{self._name}'")

    def remove_item(self, name: str) -> None:
        """Remove an item from the project by its name."""
        self._items.remove(name)
        logger.info(f"Removed item '{name}' from project '{self._name}'")

    def get_item(self, name: str) -> BaseEntity:
        """Retrieve an item from the project by its name."""
        item = self._items.get(name)
        logger.info(f"Retrieved item '{name}' from project '{self._name}'")
        return item

    def get_items(self) -> Dict[str, BaseEntity]:
        """Retrieve all items in the project as a dictionary."""
        return self._items.get_all()

    def get_name(self) -> str:
        """Retrieve the project's name."""
        logger.info(f"Retrieved name '{self._name}' for project")
        return self._name

    def set_name(self, name: str) -> None:
        """Set the project's name."""
        check_non_empty_string(name, "Project name")
        old_name = self._name
        self._name = name
        self._items.name = f"{name}_items"
        logger.info(f"Project name changed from '{old_name}' to '{name}'")

    def set_project(self, name: str, items: Dict[str, BaseEntity]) -> None:
        """Set the entire project configuration, replacing name and items."""
        check_non_empty_string(name, "Project name")
        for item in items.values():
            if not isinstance(item, self._item_type):
                raise TypeError(f"Item must be of type {self._item_type.__name__} for project '{name}', got {type(item).__name__}")
        old_name = self._name
        old_count = len(self._items)
        self._name = name
        self._items.set_items(items)
        self._items.name = f"{name}_items"
        logger.info(f"Project updated: name changed from '{old_name}' to '{name}', "
                    f"items count changed from {old_count} to {len(self._items)}")

    def get_project(self) -> Dict[str, Any]:
        """Get the entire project configuration as a dictionary."""
        result = {"name": self._name, "items": self._items.to_dict()["items"]}
        logger.info(f"Retrieved project configuration for '{self._name}' with {len(self._items)} items")
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert the project to a dictionary for serialization."""
        return {"name": self._name, "items": self._items.to_dict()["items"]}

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Create a project instance from a dictionary.

        Args:
            data (Dict[str, Any]): Dictionary with project configuration.

        Returns:
            Project: A new instance of the subclass initialized with the dictionary data.

        Raises:
            ValueError: If the data is invalid or cannot be deserialized.
        """
        try:
            check_non_empty_string(data["name"], "Project name")
            items = {}
            for k, v in data.get("items", {}).items():
                try:
                    items[k] = cls._item_type.from_dict(v)
                except (TypeError, ValueError) as e:
                    logger.error(f"Failed to deserialize item '{k}' for project: {str(e)}")
                    raise ValueError(f"Invalid data for item '{k}': {str(e)}") from e
            return cls(name=data["name"], items=items)
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Failed to deserialize Project from dict with name '{data.get('name', 'unknown')}': {str(e)}")
            raise ValueError(f"Invalid project data: {str(e)}") from e

    def __repr__(self) -> str:
        """Return a string representation of the Project."""
        return f"Project(name='{self._name}', items_count={len(self._items)})"