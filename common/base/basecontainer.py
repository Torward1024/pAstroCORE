# base/basecontainer.py
from abc import ABC
from typing import Dict, TypeVar, Generic, Any, List, Iterator, get_type_hints
from common.base.baseentity import BaseEntity
from common.utils.logging_setup import logger

T = TypeVar('T', bound=BaseEntity)

class BaseContainer(BaseEntity, ABC, Generic[T]):
    """Abstract base class for managing collections of BaseEntity objects using a dictionary.

    Provides a foundation for container classes in the MBS system. Manages a collection of entities
    indexed by their `name` attribute, with support for validation, activation state management,
    and universal serialization. Subclasses can extend validation logic or add specialized behavior.

    Attributes:
        _items (Dict[str, T]): Dictionary mapping entity names to their instances.
        _fields (Dict[str, type]): Inherited from BaseEntity, contains type annotations including `_items`.
        _use_cache (bool): Flag to enable caching for `to_dict` results.
        _cached_to_dict (dict, optional): Cached result of `to_dict` to improve performance.

    Notes:
        - Logging is integrated via `common.utils.logging_setup.logger` to track operations.
        - This is an abstract base class and cannot be instantiated directly; it must be subclassed.
        - The `name` attribute of contained entities is used as the key, ensuring uniqueness within the container.
        - Serialization methods `to_dict` and `from_dict` handle the entire collection, including nested entities.
        - Optional caching in `to_dict` can be enabled by setting `_use_cache=True`.
        - Direct modification of `_items` bypasses validation and cache invalidation. Use `add`, `remove`, or `set_items` instead.

    Examples:
        >>> class MyItem(BaseEntity):
        ...     value: int
        >>> class MyContainer(BaseContainer[MyItem]):
        ...     pass
        >>> container = MyContainer(name="test_container")
        >>> item = MyItem(name="item1", value=42)
        >>> container.add(item)
        >>> print(container.to_dict())
        {'name': 'test_container', 'isactive': True, 'items': {'item1': {'name': 'item1', 'isactive': True, 'value': 42}}}
        >>> new_container = MyContainer.from_dict({'name': 'test_container', 'isactive': True, 'items': {'item1': {'name': 'item1', 'isactive': True, 'value': 42}}})
        >>> print(new_container.get_items())
        [MyItem(name='item1', isactive=True, value=42)]
    """
    _items: Dict[str, T]
    _use_cache: bool
    _cached_to_dict: Dict[str, Any]
    _type_cache: Dict[Any, Any] = {}
    _item_type: type

    def __init__(self, items: Dict[str, T] = None, name: str = None, isactive: bool = True, use_cache: bool = False):
        """Initialize the BaseContainer with a name, activation status, and optional items.

        Args:
            items (Dict[str, T], optional): Initial dictionary of items where keys are entity names.
            name (str, optional): An optional identifier for the container. Defaults to None.
            isactive (bool): Initial activation status of the container. Defaults to True.
            use_cache (bool): Enable caching for `to_dict` results. Defaults to False.

        Raises:
            TypeError: If items or its values do not match expected types.
            ValueError: If an item's name does not match its dictionary key.
        """
        # workaround for Generic[T] breaking EntityMeta's _fields setup
        if not hasattr(self.__class__, '_fields'):
            self.__class__._fields = get_type_hints(self.__class__)
        
        # prepare items with type validation
        initial_items = items or {}
        if not isinstance(initial_items, dict):
            raise TypeError(f"'items' must be a dict, got {type(initial_items)}")
        
        # extract T from Generic[T] and validate each item
        generic_base = self.__orig_bases__[0]
        item_type = self._resolve_type(generic_base.__args__[0])  # Resolve T to actual type (e.g., TestEntity)
        for key, item in initial_items.items():
            if not isinstance(key, str):
                raise TypeError(f"Keys in '_items' must be str, got {type(key)}")
            self._validate_type(f"_items[{key}]", item, item_type)
        
        # pass the resolved type to BaseEntity
        resolved_items_type = Dict[str, item_type]
        self._fields["_items"] = resolved_items_type  # update _fields with resolved type
        
        generic_base = self.__orig_bases__[0]
        self._item_type = self._resolve_type(generic_base.__args__[0])  # Кэшируем тип
        super().__init__(name=name, isactive=isactive, _items=initial_items, _use_cache=use_cache, _cached_to_dict=None)
        self._validate_items(self._items)
        logger.info(f"Initialized {self.__class__.__name__} with name={name}, isactive={isactive}, item_count={len(self._items)}")

    def _validate_items(self, items: Dict[str, T]) -> None:
        """Validate the initial dictionary of items.

        Ensures that each item's `name` attribute matches its key in the dictionary and calls
        subclass-specific validation.

        Args:
            items (Dict[str, T]): The dictionary of items to validate.

        Raises:
            ValueError: If an item's name does not match its key.
        """
        for key, item in items.items():
            if item.name != key:
                raise ValueError(f"Item name '{item.name}' does not match key '{key}' in {self.__class__.__name__}")
            self._validate_item(item)

    def _validate_item(self, item: T) -> None:
        """Hook for subclass-specific item validation.

        Subclasses can override this method to implement custom validation logic for items.

        Args:
            item (T): The item to validate.

        Raises:
            ValueError: If the item fails subclass-specific validation criteria.
        """
        pass

    def add(self, item: T) -> None:
        """Add an item to the collection using its name as the key.

        Args:
            item (T): The item to add to the container.

        Raises:
            ValueError: If the item's name is None or already exists in the container.
            TypeError: If the item's type does not match the expected type T.
        """
        if item.name is None:
            raise ValueError(f"Cannot add item with no name to {self.__class__.__name__}")
        generic_base = self.__orig_bases__[0]
        item_type = self._resolve_type(generic_base.__args__[0])
        if not isinstance(item, item_type):
            raise TypeError(f"Item must be of type {item_type.__name__}, got {type(item).__name__}")
        self._validate_item(item)
        if item.name in self._items:
            raise ValueError(f"Item with name '{item.name}' already exists in {self.__class__.__name__}")
        self._items[item.name] = item
        self._cached_to_dict = None  # Invalidate cache
        logger.info(f"Added item with name '{item.name}' to {self.__class__.__name__}")

    def remove(self, name: str) -> None:
        """Remove an item from the container by its name.

        Args:
            name (str): The name of the item to remove.

        Raises:
            KeyError: If the name is not found in the container.
        """
        if name not in self._items:
            raise KeyError(f"Name '{name}' not found in {self.__class__.__name__}")
        del self._items[name]
        self._cached_to_dict = None  # Invalidate cache
        logger.info(f"Removed item with name '{name}' from {self.__class__.__name__}")

    def get(self, name: str) -> T:
        """Retrieve an item from the container by its name.

        Args:
            name (str): The name of the item to retrieve.

        Returns:
            T: The item associated with the specified name.

        Raises:
            KeyError: If the name is not found in the container.
        """
        if name not in self._items:
            raise KeyError(f"Name '{name}' not found in {self.__class__.__name__}")
        return self._items[name]

    def get_all(self) -> Dict[str, T]:
        """Retrieve all items in the container with their names as keys.

        Returns:
            Dict[str, T]: A copy of the items dictionary, mapping names to entities.
        """
        return self._items.copy()

    def get_items(self) -> List[T]:
        """Retrieve all items in the container as a list, without their names.

        Returns:
            List[T]: A list of all items in the container.
        """
        return list(self._items.values())
    
    def set(self, params: Dict[str, Any]) -> None:
        """Set container attributes from a dictionary with type validation.

        Args:
            params (Dict[str, Any]): Dictionary with attribute names and values to update.

        Raises:
            ValueError: If an attribute is not defined in the class annotations.
            TypeError: If an attribute value does not match its annotated type.
        """
        for key, value in params.items():
            if key == "_items":
                self.set_items(value)
            elif key not in self._fields:
                raise ValueError(f"Unknown attribute '{key}' for {self.__class__.__name__}")
            else:
                expected_type = self._resolve_type(self._fields[key])
                self._validate_type(key, value, expected_type)
                setattr(self, key, value)
        self._cached_to_dict = None  # Invalidate cache
        logger.info(f"Updated attributes of {self.__class__.__name__}: {params}")

    def set_items(self, items: Dict[str, T]) -> None:
        """Set or replace all items in the container.

        Args:
            items (Dict[str, T]): Dictionary of items to set.

        Raises:
            ValueError: If any item fails validation or has a mismatched name.
        """
        self._items.clear()
        self._validate_items(items)
        self._items.update(items)
        self._cached_to_dict = None  # Invalidate cache
        logger.info(f"Set {len(items)} items in {self.__class__.__name__}")

    def has_item(self, name: str) -> bool:
        """Check if an item with the specified name exists in the container.

        Args:
            name (str): The name of the item to check.

        Returns:
            bool: True if the item exists, False otherwise.
        """
        return name in self._items

    def clear(self) -> None:
        """Remove all items from the container.

        Notes:
            - Logs an info message indicating the container has been cleared.
        """
        self._items.clear()
        self._cached_to_dict = None  # Invalidate cache
        logger.info(f"Cleared all items from {self.__class__.__name__}")

    def clone(self) -> 'BaseContainer[T]':
        """Create a deep copy of the container.

        Returns:
            BaseContainer[T]: A new instance of the same class with identical items.
        """
        new_items = {name: item.clone() for name, item in self._items.items()}
        return self.__class__(items=new_items, name=self.name, isactive=self.isactive, use_cache=self._use_cache)

    def activate_item(self, name: str) -> None:
        """Activate an item in the container by its name.

        Args:
            name (str): The name of the item to activate.

        Raises:
            KeyError: If the name is not found in the container.
        """
        self.get(name).activate()
        self._cached_to_dict = None  # Invalidate cache
        logger.info(f"Activated item with name '{name}' in {self.__class__.__name__}")

    def deactivate_item(self, name: str) -> None:
        """Deactivate an item in the container by its name.

        Args:
            name (str): The name of the item to deactivate.

        Raises:
            KeyError: If the name is not found in the container.
        """
        self.get(name).deactivate()
        self._cached_to_dict = None  # Invalidate cache
        logger.info(f"Deactivated item with name '{name}' in {self.__class__.__name__}")

    def to_dict(self) -> dict:
        """Convert the container to a dictionary for serialization.

        Serializes the container's state, including its name, activation status, and all items,
        with nested entities recursively serialized. Uses caching if enabled.

        Returns:
            dict: A dictionary containing the container's serialized data.
        """
        if self._use_cache and self._cached_to_dict is not None:
            return self._cached_to_dict
        
        data = super().to_dict()
        data["items"] = {name: item.to_dict() for name, item in self._items.items()}
        
        if self._use_cache:
            self._cached_to_dict = data
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'BaseContainer':
        """Create a container instance from a dictionary.

        Reconstructs a container instance from serialized data, including its name, activation status,
        and all items, with nested entities recursively deserialized.

        Args:
            data (dict): Dictionary containing the container's serialized data, typically from `to_dict`.

        Returns:
            BaseContainer: A new instance of the subclass initialized with the dictionary data.

        Raises:
            TypeError: If the item type cannot be resolved or if data is invalid.
        """
        from inspect import getmodule
        if not hasattr(cls, '_fields'):
            cls._fields = get_type_hints(cls)
        generic_base = cls.__orig_bases__[0]
        item_type = cls._resolve_type(generic_base.__args__[0])
        if item_type is Any:
            raise TypeError("Cannot instantiate items with unresolved type 'Any'")
        items = {key: item_type.from_dict(item_data) for key, item_data in data["items"].items()}
        return cls(items=items, name=data.get("name"), isactive=data.get("isactive", True))
    
    @classmethod
    def _resolve_type(cls, type_hint):
        """Resolve forward references to actual types.

        Args:
            type_hint: The type hint to resolve, potentially a string (forward reference) or a type.

        Returns:
            The resolved type, or raises an error if unresolvable.

        Raises:
            TypeError: If the type hint cannot be resolved.
        """
        from typing import ForwardRef

        # check cache
        if type_hint in cls._type_cache:
            return cls._type_cache[type_hint]

        # resolve ForwardRef
        if isinstance(type_hint, ForwardRef):
            type_name = type_hint.__forward_arg__
            resolved = globals().get(type_name)
            if resolved is None:
                from inspect import getmodule
                module = getmodule(cls)
                resolved = getattr(module, type_name, None) if module else None
                if resolved is None:
                    raise TypeError(f"Cannot resolve forward reference '{type_name}' in {cls.__name__}")
            cls._type_cache[type_hint] = resolved
            return resolved

        # resolve annotations
        if isinstance(type_hint, str):
            resolved = globals().get(type_hint)
            if resolved is None:
                from inspect import getmodule
                module = getmodule(cls)
                resolved = getattr(module, type_hint, None) if module else None
                if resolved is None:
                    raise TypeError(f"Cannot resolve type hint '{type_hint}' in {cls.__name__}")
            cls._type_cache[type_hint] = resolved
            return resolved

        # support for generic types (e.g., Dict[str, T])
        elif hasattr(type_hint, "__origin__"):
            cls._type_cache[type_hint] = type_hint
            return type_hint

        # regular types
        cls._type_cache[type_hint] = type_hint
        return type_hint

    def __iter__(self) -> Iterator[T]:
        """Iterate over the items in the container.

        Returns:
            Iterator[T]: An iterator over the container's items.
        """
        return iter(self._items.values())
    
    def __getitem__(self, name: str) -> T:
        """Retrieve an item from the container by its name using square brackets.

        Args:
            name (str): The name of the item to retrieve.

        Returns:
            T: The item associated with the specified name.

        Raises:
            KeyError: If the name is not found in the container.
        """
        return self.get(name)

    def __setitem__(self, key: str, item: T) -> None:
        """Set an item in the container by its name using square brackets.

        Args:
            key (str): The name of the item to set.
            item (T): The item to add.

        Raises:
            ValueError: If the item's name does not match the provided key or if it fails validation.
        """
        if item.name != key:
            raise ValueError(f"Item name '{item.name}' does not match key '{key}'")
        self.add(item)

    def __delitem__(self, name: str) -> None:
        """Remove an item from the container by its name using del operator.

        Args:
            name (str): The name of the item to remove.

        Raises:
            KeyError: If the name is not found in the container.
        """
        self.remove(name)

    def __contains__(self, name: str) -> bool:
        """Check if an item with the specified name exists in the container using 'in' operator.

        Args:
            name (str): The name of the item to check.

        Returns:
            bool: True if the item exists, False otherwise.
        """
        return self.has_item(name)

    def __eq__(self, other: Any) -> bool:
        """Compare two containers for equality based on their items and state.

        Args:
            other (Any): The object to compare with.

        Returns:
            bool: True if the containers are equal, False otherwise.
        """
        if not isinstance(other, self.__class__):
            return False
        return (self.name == other.name and
                self.isactive == other.isactive and
                self.get_all() == other.get_all())

    def __len__(self) -> int:
        """Return the number of items in the container.

        Returns:
            int: The number of items currently stored in the container.
        """
        return len(self._items)
    
    @property
    def items(self) -> Dict[str, T]:
        """Read-only access to the items dictionary."""
        return self._items.copy()

    def __repr__(self) -> str:
        """Return a string representation of the BaseContainer.

        Returns:
            str: A formatted string with the class name, name (if set), item count, and active/inactive counts.
        """
        active_count = sum(1 for item in self._items.values() if item.isactive)
        attrs = [f"name={self.name!r}" if self.name else ""]
        attrs.append(f"count={len(self._items)}")
        attrs.append(f"active={active_count}")
        attrs.append(f"inactive={len(self._items) - active_count}")
        return f"{self.__class__.__name__}({', '.join(attr for attr in attrs if attr)})"