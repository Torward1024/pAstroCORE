# base/baseentity.py
from abc import ABC, ABCMeta
from typing import Dict, Any, get_origin, get_args
from common.utils.logging_setup import logger

class EntityMeta(ABCMeta):
    """Metaclass for BaseEntity to handle type annotations and enforce attribute validation.

    Automatically collects type annotations from the subclass and configures the entity to validate
    attributes against these types during initialization and updates.

    Attributes:
        _fields (Dict[str, type]): Dictionary of annotated attribute names and their expected types.
    """
    def __new__(cls, name, bases, attrs):
        new_class = super().__new__(cls, name, bases, attrs)
        annotations = {}
        for base in reversed(bases):
            if hasattr(base, '_fields'):
                annotations.update(base._fields)
            annotations.update(getattr(base, '__annotations__', {}))
        annotations.update(attrs.get('__annotations__', {}))
        new_class._fields = annotations
        return new_class

class BaseEntity(ABC, metaclass=EntityMeta):
    """Abstract base class for entities with attribute management, type validation, and universal serialization.

    Provides a foundation for base entity classes in the MBS system. Defines common functionality
    for managing attributes with type checking, an active/inactive state, and universal serialization methods,
    including support for nested entities.

    Attributes:
        name (str, optional): An optional identifier for the entity.
        isactive (bool): Indicates whether the entity is active or inactive.
        _fields (Dict[str, type]): Class-level mapping of attribute names to their expected types (from annotations).

    Notes:
        - Logging is integrated via `common.utils.logging_setup.logger` to track initialization and state changes.
        - This is an abstract base class and cannot be instantiated directly; it must be subclassed.
        - Attributes are validated against type annotations defined in `__annotations__`.
        - Serialization methods `to_dict` and `from_dict` automatically handle all annotated attributes, including nested entities.

    Examples:
        >>> class NestedEntity(BaseEntity):
        ...     value: int
        >>> class MyEntity(BaseEntity):
        ...     name: str
        ...     nested: NestedEntity
        >>> nested = NestedEntity(value=42)
        >>> entity = MyEntity(name="test", isactive=True, nested=nested)
        >>> print(entity.to_dict())
        {'name': 'test', 'isactive': True, 'nested': {'name': None, 'isactive': True, 'value': 42}}
        >>> new_entity = MyEntity.from_dict({'name': 'test', 'isactive': True, 'nested': {'name': None, 'isactive': True, 'value': 42}})
        >>> print(new_entity)
        MyEntity(name='test', isactive=True, nested=NestedEntity(isactive=True, value=42))
    """
    _type_cache: Dict[Any, Any] = {}
    _cached_to_dict: Dict[str, Any]
    _use_cache: bool

    def __init__(self, *, name: str = None, isactive: bool = True, use_cache: bool = False, **kwargs):
        """Initialize the BaseEntity with a name, activation status, and optional typed attributes.

        Args:
            name (str, optional): An optional identifier for the entity. Defaults to None.
            isactive (bool): Initial activation status of the entity. Defaults to True.
            **kwargs: Arbitrary keyword arguments to set initial attributes, validated against type annotations.

        Raises:
            TypeError: If an attribute value does not match its annotated type.
            ValueError: If an unknown attribute is provided.
        """
        
        super().__setattr__('_use_cache', use_cache)
        super().__setattr__('_cached_to_dict', None)
        super().__setattr__('name', name)
        super().__setattr__('isactive', isactive)

        for field in self._fields:
            if field in ('_use_cache', '_cached_to_dict', 'name', 'isactive') and field not in kwargs:
                continue
            value = kwargs.get(field, None)
            expected_type = self._resolve_type(self._fields[field])
            self._validate_type(field, value, expected_type)
            super().__setattr__(field, value)
        print(f"After init: _use_cache={self._use_cache}")

        unknown_attrs = set(kwargs.keys()) - set(self._fields.keys())
        if unknown_attrs:
            raise ValueError(f"Unknown attributes provided for {self.__class__.__name__}: {unknown_attrs}")
        
        logger.info(f"Initialized {self.__class__.__name__} instance with name={name}, isactive={isactive}")

    def _validate_type(self, key: str, value: Any, expected_type: Any) -> None:
        """Validate that a value matches the expected type.

        Args:
            key (str): The attribute name being validated.
            value (Any): The value to check.
            expected_type (Any): The expected type from type annotations.

        Raises:
            TypeError: If the value does not match the expected type and is not None.
        """
        if value is None:
            return
    
        resolved_type = self._resolve_type(expected_type)
        if resolved_type is Any:
            return
        
        base_type = get_origin(resolved_type) or resolved_type
        type_args = get_args(resolved_type)
        
        if base_type in (dict, Dict):
            if not isinstance(value, dict):
                raise TypeError(f"Attribute '{key}' must be a dict, got {type(value)}")
            if type_args:  # e.g., Dict[str, T]
                key_type, value_type = type_args
                resolved_value_type = self._resolve_type(value_type)
                if resolved_value_type is Any:  # Пропускаем валидацию для Any
                    return
                if not isinstance(resolved_value_type, (type, tuple)):
                    raise TypeError(f"Resolved value type '{resolved_value_type}' for '{key}' is not a valid type")
                for k, v in value.items():
                    if not isinstance(k, key_type):
                        raise TypeError(f"Key in '{key}' must be {key_type}, got {type(k)}")
                    if v is not None and not isinstance(v, resolved_value_type):
                        raise TypeError(f"Value in '{key}' must be {resolved_value_type}, got {type(v)}")
        elif not isinstance(value, base_type):
            raise TypeError(f"Attribute '{key}' must be of type {resolved_type}, got {type(value)}")

    def set(self, params: Dict[str, Any]) -> None:
        """Set entity attributes from a dictionary with type validation.

        Args:
            params (dict): Dictionary with attribute names and values to update.

        Raises:
            TypeError: If an attribute value does not match its annotated type.
            ValueError: If an attribute is not defined in the class annotations.

        Notes:
            - Only attributes defined in `__annotations__` can be set.
            - Logs an info message with updated attributes.
        """
        for key, value in params.items():
            if key not in self._fields:
                raise ValueError(f"Unknown attribute '{key}' for {self.__class__.__name__}")
            expected_type = self._resolve_type(self._fields[key])
            self._validate_type(key, value, expected_type)
            setattr(self, key, value)
        logger.info(f"Updated attributes of {self.__class__.__name__}: {params}")

    def get(self, key: str = None) -> Any:
        """Retrieve an attribute or all attributes of the entity.

        Args:
            key (str, optional): The name of the attribute to retrieve. If None, returns all attributes as a dictionary.

        Returns:
            Any: The value of the specified attribute if `key` is provided, otherwise a dictionary of all attributes.

        Raises:
            KeyError: If the specified `key` is not found in the entity's annotated fields.
        """
        if key is not None:
            if key not in self._fields:
                raise KeyError(f"Attribute '{key}' not found in {self.__class__.__name__}")
            return getattr(self, key) if hasattr(self, key) else None
        return {key: getattr(self, key) for key in self._fields if hasattr(self, key)}

    def activate(self) -> None:
        """Activate the entity, setting its status to active.

        Notes:
            - Logs an info message indicating the entity has been activated.
        """
        self.isactive = True
        logger.info(f"Activated {self.__class__.__name__} instance")

    def deactivate(self) -> None:
        """Deactivate the entity, setting its status to inactive.

        Notes:
            - Logs an info message indicating the entity has been deactivated.
        """
        self.isactive = False
        logger.info(f"Deactivated {self.__class__.__name__} instance")
    
    def has_attribute(self, key: str) -> bool:
        """Check if the entity has a specific attribute.

        Args:
            key (str): The name of the attribute to check.

        Returns:
            bool: True if the attribute exists in the entity's fields and is set, False otherwise.
        """
        return key in self._fields and hasattr(self, key)
    
    def clone(self) -> 'BaseEntity':
        """Create a deep copy of the entity.

        Returns:
            BaseEntity: A new instance of the same class with identical attributes.
        """
        return self.__class__.from_dict(self.to_dict())

    def to_dict(self) -> dict:
        """Convert the entity to a dictionary for serialization.

        Automatically serializes the entity's state by reflecting on all annotated attributes,
        including nested entities which are recursively serialized.

        Returns:
            dict: A dictionary containing the entity's serialized data.
        """
        print(f"to_dict called for {self}, use_cache={self._use_cache}, cached_to_dict={self._cached_to_dict}")
        if self._use_cache and self._cached_to_dict is not None:
            print("Returning cached dict")
            return self._cached_to_dict
        
        seen = set()
        data = {"name": self.name, "isactive": self.isactive}
        seen.add(id(self))
        for key in self._fields:
            if key.startswith('_'):
                continue
            if hasattr(self, key):
                value = getattr(self, key)
                if isinstance(value, BaseEntity):
                    if id(value) in seen:
                        data[key] = "<cyclic reference>"
                    else:
                        data[key] = value.to_dict()
                        seen.add(id(value))
                else:
                    data[key] = value
        
        if self._use_cache:
            self._cached_to_dict = data
            return self._cached_to_dict  # Явно возвращаем кэшированный объект
        return data  # Возвращаем новый объект, если кэш не используется

    @classmethod
    def from_dict(cls, data: dict) -> 'BaseEntity':
        """Create an entity instance from a dictionary.

        Automatically reconstructs an entity instance from serialized data, setting its name, activation status,
        and annotated attributes, including nested entities.

        Args:
            data (dict): Dictionary containing the entity's serialized data, typically from `to_dict`.

        Returns:
            BaseEntity: A new instance of the subclass initialized with the dictionary data.

        Raises:
            TypeError: If a value in the dictionary does not match the annotated type.
            ValueError: If an unknown attribute is provided in the dictionary.
        """
        kwargs = {}
        for key, value in data.items():
            if key in ("name", "isactive"):
                continue
            if key not in cls._fields:
                raise ValueError(f"Unknown attribute '{key}' for {cls.__name__}")
            expected_type = cls._resolve_type(cls._fields[key])
            if isinstance(expected_type, str):
                from inspect import getmodule
                module = getmodule(cls)
                expected_type = getattr(module, expected_type, None) if module else globals().get(expected_type)
                if expected_type is None:
                    raise TypeError(f"Cannot resolve forward reference '{cls._fields[key]}' for attribute '{key}'")
            if isinstance(expected_type, type) and issubclass(expected_type, BaseEntity) and isinstance(value, dict):
                kwargs[key] = expected_type.from_dict(value)
            elif value is not None:
                if not isinstance(value, expected_type):
                    raise TypeError(f"Attribute '{key}' must be of type {expected_type}, got {type(value)}")
                kwargs[key] = value
            else:
                kwargs[key] = None
        return cls(name=data.get("name"), isactive=data.get("isactive", True), **kwargs)
    
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
                        raise TypeError(f"Cannot resolve forward reference '{type_name}' in {cls.__name__}")
                # Рекурсивно проверяем вложенные типы
                if hasattr(resolved, '_fields'):
                    for field, field_type in resolved._fields.items():
                        cls._resolve_type(field_type)
                cls._type_cache[type_hint] = resolved
                return resolved

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
        except Exception as e:
            logger.error(f"Failed to resolve type hint {type_hint}: {str(e)}")
            raise TypeError(f"Type resolution failed for {type_hint} in {cls.__name__}: {str(e)}")

    def __getitem__(self, key: str) -> Any:
        """Access an attribute using dictionary-like syntax.

        Args:
            key (str): The name of the attribute to retrieve.

        Returns:
            Any: The value of the specified attribute.

        Raises:
            KeyError: If the key is not found in the entity's fields.
        """
        if key not in self._fields:
            raise KeyError(f"Attribute '{key}' not found in {self.__class__.__name__}")
        return getattr(self, key) if hasattr(self, key) else None

    def __setitem__(self, key: str, value: Any) -> None:
        """Set an attribute using dictionary-like syntax.

        Args:
            key (str): The name of the attribute to set.
            value (Any): The value to assign.

        Raises:
            KeyError: If the key is not found in the entity's fields.
            TypeError: If the value does not match the annotated type.
        """
        if key not in self._fields:
            raise KeyError(f"Attribute '{key}' not found in {self.__class__.__name__}")
        expected_type = self._resolve_type(self._fields[key])
        self._validate_type(key, value, expected_type)
        setattr(self, key, value)
        logger.info(f"Set attribute '{key}' of {self.__class__.__name__} to {value}")

    def __eq__(self, other: Any) -> bool:
        """Compare two entities for equality based on their attributes and state.

        Args:
            other (Any): The object to compare with.

        Returns:
            bool: True if the entities are equal, False otherwise.
        """
        if not isinstance(other, self.__class__):
            return False
        return (self.name == other.name and
                self.isactive == other.isactive and
                all(self.get(k) == other.get(k) for k in self._fields if k not in ("name", "isactive")))

    def __contains__(self, key: str) -> bool:
        """Check if an attribute exists in the entity.

        Args:
            key (str): The name of the attribute to check.

        Returns:
            bool: True if the attribute exists and is set, False otherwise.
        """
        return key in self._fields and hasattr(self, key)
    
    def __setattr__(self, key: str, value: Any) -> None:
        """Set an attribute with type validation.

        Args:
            key (str): The name of the attribute to set.
            value (Any): The value to assign.

        Raises:
            ValueError: If the key is not in the entity's fields (except for 'name' and 'isactive').
            TypeError: If the value does not match the annotated type.
        """
        internal_attrs = {"name", "isactive", "_use_cache", "_cached_to_dict"}
        if key in internal_attrs:
            super().__setattr__(key, value)
        elif key in self._fields:
            expected_type = self._resolve_type(self._fields[key])
            self._validate_type(key, value, expected_type)
            super().__setattr__(key, value)
            if hasattr(self, '_cached_to_dict') and self._use_cache:
                self._cached_to_dict = None
            logger.info(f"Set attribute '{key}' of {self.__class__.__name__} to {value}")
        else:
            raise ValueError(f"Unknown attribute '{key}' for {self.__class__.__name__}")

    def __repr__(self) -> str:
        """Return a string representation of the BaseEntity.

        Returns:
            str: A formatted string with the class name, name (if set), activation status, and attributes.
        """
        attrs = [f"name={self.name!r}" if self.name else ""]
        attrs.append(f"isactive={self.isactive}")
        for k in self._fields:
            if hasattr(self, k):
                value = getattr(self, k)
                if isinstance(value, BaseEntity):
                    attrs.append(f"{k}=<{value.__class__.__name__} at {id(value)}>")
                else:
                    attrs.append(f"{k}={value!r}")
        return f"{self.__class__.__name__}({', '.join(attr for attr in attrs if attr)})"