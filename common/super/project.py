# /common/super/project.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from common.utils.validation import check_non_empty_string
from common.utils.logging_setup import logger
from common.base.basecontainer import BaseContainer
from common.base.baseentity import BaseEntity

class Project(ABC):
    """Abstract super-class for managing collections of BaseEntity items within a project using BaseContainer.

    Serves as a foundation for specific project types managed by a Manipulator in the MSB architecture. 
    Provides functionality for adding, removing, retrieving, and configuring projects and their items,
    leveraging BaseContainer for efficient storage and serialization.

    Attributes:
        _name (str): The name of the project, must be a non-empty string.
        _items (BaseContainer[BaseEntity]): Container of BaseEntity items indexed by their names.

    Notes:
        - Logging is integrated via `common.utils.logging_setup.logger` to track operations and errors.
        - The class is abstract and cannot be instantiated directly; it requires subclassing.
        - Items must be instances of BaseEntity or its subclasses, with unique names as keys.

    Examples:
        >>> class Observation(BaseEntity):
        ...     frequency: float
        >>> class ObservationProject(Project):
        ...     def create_item(self, item_code="OBS_DEFAULT", isactive=True):
        ...         self._items.add(Observation(name=item_code, isactive=isactive, frequency=1.4))
        ...     @classmethod
        ...     def from_dict(cls, data):
        ...         items = {k: Observation.from_dict(v) for k, v in data["items"].items()}
        ...         return cls(name=data["name"], items=items)
        >>> proj = ObservationProject(name="RadioObs")
        >>> proj.create_item("OBS1")
        >>> proj.to_dict()
        {'name': 'RadioObs', 'items': {'OBS1': {'name': 'OBS1', 'isactive': True, 'frequency': 1.4}}}
    """
    def __init__(self, name: str = "DEFAULT_PROJECT", items: Optional[Dict[str, BaseEntity]] = None):
        """Initialize a Project with a name and an optional dictionary of BaseEntity items.

        Args:
            name (str): The name of the project. Must be a non-empty string. Defaults to "DEFAULT_PROJECT".
            items (Optional[Dict[str, BaseEntity]]): Initial dictionary of items, where keys are item names. Defaults to None (empty container).

        Raises:
            TypeError: If name is not a string.
            ValueError: If name is empty or items contain non-BaseEntity values.
        """
        check_non_empty_string(name, "Project name")
        self._name = name
        self._items = BaseContainer[BaseEntity](items=items, name=f"{name}_items")
        logger.info(f"Initialized project '{name}' with {len(self._items)} items")

    def add_item(self, item: BaseEntity) -> None:
        """Add a BaseEntity item to the project's container.

        Args:
            item (BaseEntity): The item to add, must have a unique name.

        Raises:
            ValueError: If item.name is None or already exists in the container.
        """
        self._items.add(item)
        logger.info(f"Added item '{item.name}' to project '{self._name}'")

    @abstractmethod
    def create_item(self, item_code: str = "ITEM_DEFAULT", isactive: bool = True) -> None:
        """Create and add a new BaseEntity item to the project.

        Abstract method to be implemented by subclasses to define how new items are created and added.

        Args:
            item_code (str): Identifier for the new item, used as its name. Defaults to "ITEM_DEFAULT".
            isactive (bool): Activation status of the new item. Defaults to True.
        """
        pass

    def remove_item(self, name: str) -> None:
        """Remove an item from the project by its name.

        Args:
            name (str): The name of the item to remove.

        Raises:
            KeyError: If the name is not found in the container.
        """
        self._items.remove(name)
        logger.info(f"Removed item '{name}' from project '{self._name}'")

    def get_item(self, name: str) -> BaseEntity:
        """Retrieve an item from the project by its name.

        Args:
            name (str): The name of the item to retrieve.

        Returns:
            BaseEntity: The item associated with the specified name.

        Raises:
            KeyError: If the name is not found in the container.
        """
        item = self._items.get(name)
        logger.info(f"Retrieved item '{name}' from project '{self._name}'")
        return item

    def get_items(self) -> Dict[str, BaseEntity]:
        """Retrieve all items in the project as a dictionary.

        Returns:
            Dict[str, BaseEntity]: A dictionary mapping item names to their BaseEntity instances.
        """
        return self._items.get_all()

    def get_name(self) -> str:
        """Retrieve the project's name.

        Returns:
            str: The name of the project.
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
        """
        check_non_empty_string(name, "Project name")
        old_name = self._name
        self._name = name
        self._items.name = f"{name}_items"  # Обновляем имя контейнера
        logger.info(f"Project name changed from '{old_name}' to '{name}'")

    def set_project(self, name: str, items: Dict[str, BaseEntity]) -> None:
        """Set the entire project configuration, replacing name and items.

        Args:
            name (str): The new name for the project. Must be a non-empty string.
            items (Dict[str, BaseEntity]): The new dictionary of items to set.

        Raises:
            TypeError: If name is not a string.
            ValueError: If name is empty or items contain non-BaseEntity values.
        """
        check_non_empty_string(name, "Project name")
        old_name = self._name
        old_count = len(self._items)
        self._name = name
        self._items.set_items(items)
        self._items.name = f"{name}_items"
        logger.info(f"Project updated: name changed from '{old_name}' to '{name}', "
                    f"items count changed from {old_count} to {len(self._items)}")

    def get_project(self) -> Dict[str, Any]:
        """Get the entire project configuration as a dictionary.

        Returns:
            Dict[str, Any]: A dictionary containing the project name and serialized items.
                - "name": The project name (str).
                - "items": Dictionary of serialized items.
        """
        result = {"name": self._name, "items": self._items.to_dict()["items"]}
        logger.info(f"Retrieved project configuration for '{self._name}' with {len(self._items)} items")
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert the project to a dictionary for serialization.

        Returns:
            Dict[str, Any]: A dictionary with 'name' and serialized 'items'.
        """
        return {"name": self._name, "items": self._items.to_dict()["items"]}

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