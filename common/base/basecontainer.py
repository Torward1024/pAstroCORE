# base/basecontainer.py
from abc import ABC
from copy import deepcopy
from typing import Dict, TypeVar, Generic, Any, Optional, List, Iterator, Union, get_type_hints, get_args, get_origin
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
        >>> print(container.get_items())
        [MyItem(name='item1', isactive=True, value=42)]
    """
    name: str
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
        
        if not hasattr(self.__class__, '_fields'):
            self.__class__._fields = get_type_hints(self.__class__)
        
        initial_items = items or {}
        if not isinstance(initial_items, dict):
            raise TypeError(f"'items' must be a dict, got {type(initial_items)}")
        
        generic_base = self.__orig_bases__[0]
        item_type = self._resolve_type(generic_base.__args__[0])
        for key, item in initial_items.items():
            if not isinstance(key, str):
                raise TypeError(f"Keys in '_items' must be str, got {type(key)}")
            self._validate_type(f"_items[{key}]", item, item_type)
        
        resolved_items_type = Dict[str, item_type]
        self._fields["_items"] = resolved_items_type
        
        generic_base = self.__orig_bases__[0]
        self._item_type = self._resolve_type(generic_base.__args__[0])
        super().__init__(name=name, isactive=isactive, _items=initial_items, _use_cache=use_cache, _cached_to_dict=None)
        self._validate_items(self._items)
        logger.debug(f"Initialized {self.__class__.__name__} with name={name}, isactive={isactive}, item_count={len(self._items)}")

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

    def add(self, item: Union[T, List[T], 'BaseContainer[T]'], copy_items: bool = True) -> None:
        """Add one or more items to the collection using their names as keys.

        Supports adding a single item, a list of items, or items from another BaseContainer of the same item type.
        By default, creates deep copies of items to prevent unintended modifications of original objects.

        Args:
            item (Union[T, List[T], BaseContainer[T]]): A single item, a list of items, or a BaseContainer
                containing items of type T to add to the container.
            copy_items (bool): If True, creates deep copies of items to ensure isolation. Defaults to True.

        Raises:
            ValueError: If any item's name is None, already exists in the container, or does not match its key.
            TypeError: If any item's type does not match the expected type T, or if the input type is unsupported.
            AttributeError: If an item or container lacks a 'copy' method when copy_items is True.
        """
        generic_base = self.__orig_bases__[0]
        item_type = self._resolve_type(generic_base.__args__[0])

        if isinstance(item, item_type):
            item_to_add = deepcopy(item) if copy_items else item
            if item_to_add.name is None:
                raise ValueError(f"Cannot add item with no name to {self.__class__.__name__}")
            self._validate_item(item_to_add)
            if item_to_add.name in self._items:
                raise ValueError(f"Item with name '{item_to_add.name}' already exists in {self.__class__.__name__}")
            self._items[item_to_add.name] = item_to_add
            logger.debug(f"Added item with name '{item_to_add.name}' to {self.__class__.__name__}")

        elif isinstance(item, list):
            for i, single_item in enumerate(item):
                item_to_add = deepcopy(single_item) if copy_items else single_item
                if not isinstance(item_to_add, item_type):
                    raise TypeError(f"Item at index {i} must be of type {item_type.__name__}, got {type(single_item).__name__}")
                if item_to_add.name is None:
                    raise ValueError(f"Cannot add item at index {i} with no name to {self.__class__.__name__}")
                self._validate_item(item_to_add)
                if item_to_add.name in self._items:
                    raise ValueError(f"Item with name '{item_to_add.name}' at index {i} already exists in {self.__class__.__name__}")
                self._items[item_to_add.name] = item_to_add
                logger.debug(f"Added item with name '{item_to_add.name}' to {self.__class__.__name__}")

        elif isinstance(item, BaseContainer):
            other_generic_base = item.__orig_bases__[0]
            other_item_type = item._resolve_type(other_generic_base.__args__[0])
            if other_item_type != item_type:
                raise TypeError(f"BaseContainer items must be of type {item_type.__name__}, got {other_item_type.__name__}")
            for single_item in item.get_items():
                item_to_add = deepcopy(single_item) if copy_items else single_item
                if item_to_add.name is None:
                    raise ValueError(f"Cannot add item with no name from BaseContainer to {self.__class__.__name__}")
                self._validate_item(item_to_add)
                if item_to_add.name in self._items:
                    raise ValueError(f"Item with name '{item_to_add.name}' from BaseContainer already exists in {self.__class__.__name__}")
                self._items[item_to_add.name] = item_to_add
                logger.debug(f"Added item with name '{item_to_add.name}' from BaseContainer to {self.__class__.__name__}")

        else:
            raise TypeError(f"Item must be of type {item_type.__name__}, List[{item_type.__name__}], or BaseContainer[{item_type.__name__}], got {type(item).__name__}")

        self._invalidate_cache()

    def set_item(self, name: str, item: T) -> None:
        """Set or replace an item in the container by its name.

        Args:
            name (str): The name of the item to set.
            item (T): The item to add or replace.

        Raises:
            ValueError: If the item's name does not match the provided name or if it fails validation.
            TypeError: If the item's type does not match the expected type T.
        """
        if item.name != name:
            raise ValueError(f"Item name '{item.name}' does not match key '{name}' in {self.__class__.__name__}")
        generic_base = self.__orig_bases__[0]
        item_type = self._resolve_type(generic_base.__args__[0])
        if not isinstance(item, item_type):
            raise TypeError(f"Item must be of type {item_type.__name__}, got {type(item).__name__}")
        self._validate_item(item)
        self._items[name] = item
        self._invalidate_cache()
        logger.debug(f"Set item with name '{name}' in {self.__class__.__name__}")

    def remove(self, name: str) -> None:
        """Remove an item from the container by its name.

        Args:
            name (str): The name of the item to remove.
        """
        if name not in self._items:
            logger.warning(f"Name '{name}' not found in {self.__class__.__name__}")
        del self._items[name]
        self._invalidate_cache()
        logger.debug(f"Removed item with name '{name}' from {self.__class__.__name__}")

    def get(self, name: str) -> Optional[T]:
        """
        Retrieve an item from the container by its name.

        Args:
            name (str): The name of the item to retrieve.

        Returns:
            Optional[T]: The item associated with the specified name, or None if not found.

        Notes:
            - Logs a warning if the item is not found, rather than raising an exception.
        """
        if name not in self._items:
            logger.warning(f"Name '{name}' not found in {self.__class__.__name__}")
            return None
        return self._items[name]

    def get_all(self) -> Dict[str, T]:
        """Retrieve all items in the container with their names as keys.

        Returns:
            Dict[str, T]: the items dictionary, mapping names to entities.
        """
        return self._items

    def get_items(self) -> List[T]:
        """Retrieve all items in the container as a list, without their names.

        Returns:
            List[T]: A list of all items in the container.
        """
        return list(self._items.values())
    
    def get_by_value(self, conditions: Dict[str, Any]) -> List[T]:
        """Retrieve items from the container where all specified attributes match the given values.

        Args:
            conditions (Dict[str, Any]): A dictionary where keys are attribute names and values are
                the desired values (e.g., {"frequency": 1000.0, "isactive": False}). If empty,
                returns all items.

        Returns:
            List[T]: A list of items where all specified attributes equal the given values.

        Raises:
            AttributeError: If any specified attribute does not exist in the items.
        """
        if not conditions:
            logger.debug(f"No conditions provided; returning all items from {self.__class__.__name__}")
            return self.get_items()

        try:
            result = []
            for item in self.get_items():
                matches = all(getattr(item, attr_name) == attr_value 
                             for attr_name, attr_value in conditions.items())
                if matches:
                    result.append(item)
            logger.debug(f"Retrieved {len(result)} items from {self.__class__.__name__} matching conditions {conditions}")
            return result
        except AttributeError as e:
            missing_attr = next((attr for attr in conditions if not hasattr(self._item_type, attr)), None)
            logger.error(f"Attribute '{missing_attr}' does not exist in items of {self.__class__.__name__}")
            raise AttributeError(f"Attribute '{missing_attr}' does not exist in items") from e

    def get_active_items(self) -> List[T]:
        """Retrieve all active items in the container.

        Returns:
            List[T]: A list of items where isactive is True.
        """
        return self.get_by_value({"isactive": True})

    def get_inactive_items(self) -> List[T]:
        """Retrieve all inactive items in the container.

        Returns:
            List[T]: A list of items where isactive is False.
        """
        return self.get_by_value({"isactive": False})
    
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
        if self._use_cache and hasattr(self, '_cached_to_dict'):
            self._cached_to_dict = None
        logger.debug(f"Updated attributes of {self.__class__.__name__}: {params}")

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
        self._invalidate_cache()
        logger.debug(f"Set {len(items)} items in {self.__class__.__name__}")

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
        self._invalidate_cache()
        logger.debug(f"Cleared all items from {self.__class__.__name__}")

    def clone(self, deep: bool = True) -> 'BaseContainer[T]':
        """Create a deep copy of the container.

        Returns:
            BaseContainer[T]: A new instance of the same class with identical items.
        """
        if deep:
            new_items = {name: item.clone() for name, item in self._items.items()}
        else:
            new_items = self._items.copy()
        return self.__class__(items=new_items, name=self.name, isactive=self.isactive, use_cache=self._use_cache)

    def activate_item(self, name: str) -> None:
        """Activate an item in the container by its name.

        Args:
            name (str): The name of the item to activate.
        """
        self.get(name).activate()
        self._invalidate_cache()
        logger.debug(f"Activated item with name '{name}' in {self.__class__.__name__}")

    def activate_all(self) -> None:
        """Activate all items in the container.

        Raises:
            ValueError: If the container is empty.
        """
        if not self._items:
            logger.error("No items to activate")
        for item in self.get_items():
            item.activate()
        self._invalidate_cache()
        logger.debug(f"Activated all items in {self.__class__.__name__}")

    def deactivate_all(self) -> None:
        """Deactivate all items in the container.

        Raises:
            ValueError: If the container is empty.
        """
        if not self._items:
            logger.error("No items to deactivate")
        for item in self.get_items():
            item.deactivate()
        self._invalidate_cache()
        logger.debug(f"Deactivated all items in {self.__class__.__name__}")

    def drop_active(self) -> None:
        """Remove all active items from the container.

        Raises:
            ValueError: If there are no active items.
        """
        active_names = [name for name, item in self.get_all().items() if item.isactive]
        if not active_names:
            logger.warning("No active items to drop")
        for name in active_names:
            self.remove(name)
        logger.debug(f"Dropped {len(active_names)} active items from {self.__class__.__name__}")

    def drop_inactive(self) -> None:
        """Remove all inactive items from the container.

        Raises:
            ValueError: If there are no inactive items.
        """
        inactive_names = [name for name, item in self.get_all().items() if not item.isactive]
        if not inactive_names:
            logger.warning("No inactive items to drop")
        for name in inactive_names:
            self.remove(name)
        logger.debug(f"Dropped {len(inactive_names)} inactive items from {self.__class__.__name__}")

    def deactivate_item(self, name: str) -> None:
        """Deactivate an item in the container by its name.

        Args:
            name (str): The name of the item to deactivate.
        """
        self.get(name).deactivate()
        self._invalidate_cache()
        logger.debug(f"Deactivated item with name '{name}' in {self.__class__.__name__}")

    def to_dict(self, handle_cyclic_refs: str = "mark") -> dict:
        """Convert the container to a dictionary for serialization.

        Serializes the container's state, including its name, activation status, and all items,
        with nested entities recursively serialized. Uses caching if enabled.

        Args:
            handle_cyclic_refs (str): How to handle cyclic references. Options:
                - "mark": Replace with "<cyclic reference>" (default).
                - "ignore": Skip cyclic references.
                - "raise": Raise an error on cyclic references.

        Returns:
            dict: A dictionary containing the container's serialized data.

        Raises:
            ValueError: If handle_cyclic_refs is invalid or cyclic reference is detected with "raise" option.
        """
        if self._use_cache and self._cached_to_dict is not None:
            return self._cached_to_dict
        if handle_cyclic_refs not in ("mark", "ignore", "raise"):
            raise ValueError(f"Invalid handle_cyclic_refs value: {handle_cyclic_refs}")
        data = super().to_dict()
        seen = {id(self)}
        items_dict = {}
        for name, item in self._items.items():
            if isinstance(item, BaseEntity) and id(item) in seen:
                if handle_cyclic_refs == "raise":
                    raise ValueError(f"Cyclic reference detected for item '{name}'")
                elif handle_cyclic_refs == "ignore":
                    continue
                else:  # mark
                    items_dict[name] = "<cyclic reference>"
            else:
                items_dict[name] = item.to_dict()
                seen.add(id(item))
        data["items"] = items_dict
        if self._use_cache:
            self._cached_to_dict = data
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'BaseContainer':
        """Create a container instance from a dictionary.

        Reconstructs a container instance from serialized data, including its name, activation status,
        and all items, with nested entities recursively deserialized. Handles Union types for items.

        Args:
            data (dict): Dictionary containing the container's serialized data, typically from `to_dict`.

        Returns:
            BaseContainer: A new instance of the subclass initialized with the dictionary data.

        Raises:
            TypeError: If the item type cannot be resolved or if data is invalid.
            ValueError: If item data cannot be mapped to a valid type in a Union.
        """
        generic_base = cls.__orig_bases__[0]
        item_type_hint = generic_base.__args__[0]
        item_types = cls._resolve_type(item_type_hint, field_path=f"{cls.__name__}.items")

        if item_types is Any:
            raise TypeError("Cannot instantiate items with unresolved type 'Any'")

        is_union = get_origin(item_type_hint) is Union
        if is_union:
            item_types = get_args(item_type_hint)
        else:
            item_types = [item_types]

        items = {}
        for key, item_data in data["items"].items():
            type_name = item_data.get("type")
            selected_type = None

            if type_name:
                for candidate_type in item_types:
                    if isinstance(candidate_type, str):
                        raise TypeError(f"Cannot resolve forward reference '{candidate_type}' in {cls.__name__}")
                    if candidate_type.__name__ == type_name:
                        selected_type = candidate_type
                        break
                if not selected_type:
                    raise ValueError(f"Invalid type '{type_name}' for item '{key}' in {cls.__name__}")
            elif is_union:
                raise ValueError(f"Item '{key}' missing 'type' field required for Union type in {cls.__name__}")
            else:
                selected_type = item_types[0]  # Use the single type for non-Union

            try:
                items[key] = selected_type.from_dict(item_data)
            except TypeError as e:
                raise TypeError(f"Failed to deserialize item '{key}' in {cls.__name__}: {str(e)}") from e
        return cls(items=items, name=data.get("name"), isactive=data.get("isactive", True))
    
    def _invalidate_cache(self) -> None:
        """Invalidate the cache of the container."""
        super()._invalidate_cache()
        for item in self._items.values():
            if hasattr(item, '_invalidate_cache'):
                item._invalidate_cache()

    @classmethod
    def _resolve_type(cls, type_hint, field_path=""):
        """Resolve forward references to actual types.

        Args:
            type_hint: The type hint to resolve, potentially a string (forward reference) or a type.

        Returns:
            The resolved type, or raises an error if unresolvable.

        Raises:
            TypeError: If the type hint cannot be resolved.
        """
        from typing import ForwardRef, TypeVar, get_args

        if type_hint in cls._type_cache:
            return cls._type_cache[type_hint]
        try:
            if isinstance(type_hint, ForwardRef):
                type_name = type_hint.__forward_arg__
                resolved = globals().get(type_name)
                if resolved is None:
                    from inspect import getmodule
                    module = getmodule(cls)
                    resolved = getattr(module, type_name, None) if module else None
                    if resolved is None:
                        raise TypeError(f"Cannot resolve forward reference '{type_name}' for {field_path or cls.__name__}")
                if hasattr(resolved, '_fields'):
                    for field, field_type in resolved._fields.items():
                        try:
                            cls._resolve_type(field_type, field_path=f"{field_path}.{field}" if field_path else field)
                        except TypeError as e:
                            raise TypeError(f"Failed to resolve nested type '{field}' in {resolved.__name__}: {str(e)}") from e
                cls._type_cache[type_hint] = resolved
                return resolved

            if isinstance(type_hint, str):
                resolved = globals().get(type_hint)
                if resolved is None:
                    from inspect import getmodule
                    module = getmodule(cls)
                    resolved = getattr(module, type_hint, None) if module else None
                    if resolved is None:
                        raise TypeError(f"Cannot resolve type hint '{type_hint}' for {field_path or cls.__name__}")
                cls._type_cache[type_hint] = resolved
                return resolved

            elif isinstance(type_hint, TypeVar):
                if hasattr(cls, '__orig_bases__'):
                    for base in cls.__orig_bases__:
                        args = get_args(base)
                        if args and isinstance(type_hint, TypeVar):
                            if len(args) > 0:
                                resolved = cls._resolve_type(args[0])
                                cls._type_cache[type_hint] = resolved
                                return resolved
                            bound = type_hint.__bound__
                            if bound:
                                resolved = cls._resolve_type(bound)
                                cls._type_cache[type_hint] = resolved
                                return resolved
                            constraints = type_hint.__constraints__
                            if constraints:
                                resolved = cls._resolve_type(constraints[0])
                                cls._type_cache[type_hint] = resolved
                                return resolved
                raise TypeError(f"Cannot resolve TypeVar '{type_hint}' in {cls.__name__}")

            elif hasattr(type_hint, "__origin__"):
                cls._type_cache[type_hint] = type_hint
                return type_hint

            cls._type_cache[type_hint] = type_hint
            return type_hint
        except TypeError as e:
            logger.error(f"Failed to resolve type hint {type_hint}: {str(e)}")
            raise TypeError(f"Type resolution failed for {type_hint} in {field_path or cls.__name__}: {str(e)}") from e
        except Exception as e:
            logger.error(f"Failed to resolve type hint {type_hint}: {str(e)}")
            raise TypeError(f"Type resolution failed for {type_hint} in {field_path or cls.__name__}: {str(e)}") from e
    
    def clear(self) -> None:
        """Clear all items from the container and release references."""
        self._items.clear()
        self._invalidate_cache()

    def __iter__(self) -> Iterator[T]:
        """Iterate over the items in the container.

        Returns:
            Iterator[T]: An iterator over the container's items.
        """
        return iter(self._items.values())
    
    def __getitem__(self, key: str) -> Optional[T]:
        """Retrieve an item from the container by its name using square brackets.

        Args:
            key (str): The name of the item to retrieve.

        Returns:
            Optional[T]: The item associated with the specified name, or None if not found.

        Notes:
            - Logs a warning if the item is not found, rather than raising an exception.
        """
        if key not in self._items:
            logger.warning(f"Name '{key}' not found in {self.__class__.__name__}")
            return None
        return self._items[key]

    def __setitem__(self, key: str, item: T) -> None:
        """Set an item in the container by its name using square brackets.

        Args:
            key (str): The name of the item to set.
            item (T): The item to add or replace.

        Raises:
            ValueError: If the item's name does not match the provided key or if it fails validation.
            TypeError: If the item's type does not match the expected type T.
        """
        self.set_item(key, item)

    def __getattribute__(self, name: str) -> Any:
        attr = super().__getattribute__(name)
        return attr

    def __delitem__(self, name: str) -> None:
        """Remove an item from the container by its name using del operator.

        Args:
            name (str): The name of the item to remove.
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
    
    def __setattr__(self, key: str, value: Any) -> None:
        super().__setattr__(key, value)
        if key != '_cached_to_dict':
            self._cached_to_dict = None
        logger.debug(f"Set attribute '{key}' of {self.__class__.__name__} to {value}")
    
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

    def __del__(self) -> None:
        """Ensure cleanup of references to prevent memory leaks."""
        try:
            self.clear()
        except Exception as e:
            logger.error(f"Error during cleanup of {self.__class__.__name__}: {str(e)}")