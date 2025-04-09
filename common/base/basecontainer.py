# base/base_container.py
from abc import ABC
from typing import List, Generic
from common.base.base_entity import BaseEntity
from common.utils.logging_setup import logger

class BaseContainer(BaseEntity, ABC, Generic[T]):
    """Abstract base class for managing collections of BaseEntity objects."""
    
    _items: List[BaseEntity]

    def __init__(self, items: List[T] = None, name: str = None, isactive: bool = True):
        super().__init__(name=name, isactive=isactive, _items=items or [])
        self._validate_items(self._items)

    def _validate_items(self, items: List[T]) -> None:
        """Validate the initial list of items."""
        for item in items:
            self._validate_item(item)

    def _validate_item(self, item: T) -> None:
        """Hook for subclass-specific item validation."""
        pass

    def add(self, item: T) -> None:
        """Add an item to the collection."""
        self._validate_item(item)
        self._items.append(item)
        logger.info(f"Added item to {self.__class__.__name__}")

    def insert(self, index: int, item: T) -> None:
        """Insert an item at a specific index."""
        if not (0 <= index <= len(self._items)):
            raise IndexError(f"Index {index} out of range")
        self._validate_item(item)
        self._items.insert(index, item)
        logger.info(f"Inserted item at index {index} in {self.__class__.__name__}")

    def remove(self, index: int) -> None:
        """Remove an item by index."""
        if not (0 <= index < len(self._items)):
            raise IndexError(f"Index {index} out of range")
        self._items.pop(index)
        logger.info(f"Removed item at index {index} from {self.__class__.__name__}")

    def get_by_index(self, index: int) -> T:
        """Retrieve an item by index."""
        if not (0 <= index < len(self._items)):
            raise IndexError(f"Index {index} out of range")
        return self._items[index]

    def get_all(self) -> List[T]:
        """Retrieve all items."""
        return self._items.copy()

    def activate_item(self, index: int) -> None:
        """Activate an item by index."""
        self.get_by_index(index).activate()

    def deactivate_item(self, index: int) -> None:
        """Deactivate an item by index."""
        self.get_by_index(index).deactivate()

    def to_dict(self) -> dict:
        """Serialize the container to a dictionary."""
        data = super().to_dict()
        data["items"] = [item.to_dict() for item in self._items]
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'BaseContainer':
        """Deserialize the container from a dictionary."""
        item_type = cls._fields["_items"].__args__[0]  # Извлекаем тип T из List[T]
        items = [item_type.from_dict(item_data) for item_data in data["items"]]
        return cls(items=items, name=data.get("name"), isactive=data.get("isactive", True))

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        active_count = sum(1 for item in self._items if item.isactive)
        return f"{self.__class__.__name__}(count={len(self._items)}, active={active_count}, inactive={len(self._items) - active_count})"