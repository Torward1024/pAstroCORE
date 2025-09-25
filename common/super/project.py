# /common/super/project.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, List, TypeVar
from common.utils.validation import check_non_empty_string
from common.utils.logging_setup import logger
from common.base.basecontainer import BaseContainer
from common.base.baseentity import BaseEntity
T = TypeVar('T', bound=BaseEntity)

class Project(ABC):
    """Abstract super-class for managing collections of BaseEntity items within a project using BaseContainer.

    Attributes:
        _name (str): The name of the project, must be a non-empty string.
        _items (BaseContainer[BaseEntity]): Container of BaseEntity items indexed by their names.
        _item_type (Type[BaseEntity]): The type of items stored in the container, defaults to BaseEntity.
    """
    name: str
    _item_type: Type[BaseEntity] = BaseEntity

    def __init__(self, name: str = "DEFAULT_PROJECT", items: Optional[Dict[str, BaseEntity]] = None):
        """Initialize a Project with a name and an optional dictionary of BaseEntity items."""
        check_non_empty_string(name, "Project name")
        self.name = name
        self._items = self._create_container(items=items, name=f"{name}_items")
        logger.info(f"Initialized project '{name}' with {len(self._items)} items")

    @classmethod
    def _create_container(cls, items: Optional[Dict[str, BaseEntity]] = None, name: str = None) -> BaseContainer:
        """Create a BaseContainer instance with the specified item type."""
        class TypedContainer(BaseContainer[cls._item_type]):
            pass
        return TypedContainer(items=items, name=name)

    def add_item(self, item: BaseEntity) -> None:
        """Add a BaseEntity item to the project's container.

        Args:
            item (BaseEntity): The item to add.

        Raises:
            TypeError: If the item type does not match the expected type.
            ValueError: If an item with the same name already exists in the project.
        """
        if not isinstance(item, self._item_type):
            raise TypeError(f"Item must be of type {self._item_type.__name__} for project '{self.name}', got {type(item).__name__}")
        if self._items.has_item(item.name):
            raise ValueError(f"Item with name '{item.name}' already exists in project '{self.name}'")
        self._items.add(item)
        logger.debug(f"Added item '{item.name}' to project '{self.name}'")

    @abstractmethod
    def create_item(self, item_code: str = "ITEM_DEFAULT", isactive: bool = True) -> None:
        """Create and add a new BaseEntity item to the project."""
        pass

    def set_item(self, name: str, item: BaseEntity) -> None:
        """Set an item in the project by its name."""
        self._items.set_item(name, item)
        logger.info(f"Set item '{item.name}' in project '{self.name}'")

    def remove_item(self, name: str) -> None:
        """Remove an item from the project by its name."""
        self._items.remove(name)
        logger.info(f"Removed item '{name}' from project '{self.name}'")
    
    def get_active_items(self) -> List[T]:
        """Retrieve all active items in the container.

        Returns:
            List[T]: A list of items where isactive is True.
        """
        return self._items.get_active_items()

    def get_inactive_items(self) -> List[T]:
        """Retrieve all inactive items in the container.

        Returns:
            List[T]: A list of items where isactive is False.
        """
        return self._items.get_inactive_items()

    def get_item(self, name: str) -> BaseEntity:
        """Retrieve an item from the project by its name."""
        item = self._items.get(name)
        logger.debug(f"Retrieved item '{name}' from project '{self.name}'")
        return item

    def get_items(self) -> Dict[str, BaseEntity]:
        """Retrieve all items in the project as a dictionary."""
        return self._items.get_all()

    def get_name(self) -> str:
        """Retrieve the project's name."""
        logger.debug(f"Retrieved name '{self.name}' for project")
        return self.name

    def set_name(self, name: str) -> None:
        """Set the project's name."""
        check_non_empty_string(name, "Project name")
        old_name = self.name
        self.name = name
        self._items.name = f"{name}_items"
        logger.info(f"Project name changed from '{old_name}' to '{name}'")

    def set_project(self, name: str, items: Dict[str, BaseEntity]) -> None:
        """Set the entire project configuration, replacing name and items."""
        check_non_empty_string(name, "Project name")
        old_name = self.name
        old_count = len(self._items)
        self.name = name
        self._items.set_items(items)
        self._items.name = f"{name}_items"
        logger.info(f"Project updated: name changed from '{old_name}' to '{name}', "
                    f"items count changed from {old_count} to {len(self._items)}")

    def get_project(self) -> Dict[str, Any]:
        """Get the entire project configuration as a dictionary."""
        result = {"name": self.name, "items": self._items.to_dict()["items"]}
        logger.info(f"Retrieved project configuration for '{self.name}' with {len(self._items)} items")
        return result
    
    def clear(self):
        """Clear all observations and their resources."""
        try:
            for obs in self._items.get_all().values():
                try:
                    obs.clear_calculated_data()
                except Exception as e:
                    logger.debug(f"Error clearing observation {obs.get_observation_code()}: {str(e)}")
            self._items.clear()
            logger.info(f"Cleared all observations from project '{self.name}'")
        except Exception as e:
            logger.error(f"Error clearing project '{self.name}': {str(e)}")

    def activate_item(self, name: str) -> None:
        """Activate an item in the project's container by its name.

        Args:
            name (str): The name of the item to activate.

        Raises:
            ValueError: If the item with the specified name does not exist.
        """
        self._items.activate_item(name)
        logger.info(f"Activated item '{name}' in project '{self.name}'")

    def deactivate_item(self, name: str) -> None:
        """Deactivate an item in the project's container by its name.

        Args:
            name (str): The name of the item to deactivate.

        Raises:
            ValueError: If the item with the specified name does not exist.
        """
        self._items.deactivate_item(name)
        logger.info(f"Deactivated item '{name}' in project '{self.name}'")
    
    def activate_all(self) -> None:
        """Activate all items in the container.

        Raises:
            ValueError: If the container is empty.
        """
        return self._items.activate_all()

    def deactivate_all(self) -> None:
        """Deactivate all items in the container.

        Raises:
            ValueError: If the container is empty.
        """
        return self._items.deactivate_all()

    def drop_active(self) -> None:
        """Remove all active items from the container.

        Raises:
            ValueError: If there are no active items.
        """
        return self._items.drop_active()

    def drop_inactive(self) -> None:
        """Remove all inactive items from the container.

        Raises:
            ValueError: If there are no inactive items.
        """
        return self._items.drop_inactive()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the project to a dictionary for serialization."""
        return {"name": self.name, "items": self._items.to_dict()["items"]}

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
        return f"Project(name='{self.name}', items_count={len(self._items)})"
    
    def __del__(self) -> None:
        """Ensure cleanup of references to prevent memory leaks."""
        try:
            self.clear()
            logger.debug(f"ScheduleProject {id(self)} deleted")
        except Exception as e:
            logger.error(f"Error during cleanup of Project '{self.name}': {str(e)}")