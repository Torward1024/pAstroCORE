# base/base_entity.py
from abc import ABC
from typing import Dict, Any, Type, Union
from common.utils.logging_setup import logger

class EntityMeta(type):
    """Metaclass for BaseEntity to handle type annotations and enforce attribute validation.

    Automatically collects type annotations from the subclass and configures the entity to validate
    attributes against these types during initialization and updates.

    Attributes:
        _fields (Dict[str, type]): Dictionary of annotated attribute names and their expected types.
    """
    def __new__(cls, name, bases, attrs):
        new_class = super().__new__(cls, name, bases, attrs)
        # Collect type annotations from the class
        new_class._fields = getattr(new_class, '__annotations__', {})
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
    def __init__(self, name: str = None, isactive: bool = True, **kwargs):
        """Initialize the BaseEntity with a name, activation status, and optional typed attributes.

        Args:
            name (str, optional): An optional identifier for the entity. Defaults to None.
            isactive (bool): Initial activation status of the entity. Defaults to True.
            **kwargs: Arbitrary keyword arguments to set initial attributes, validated against type annotations.

        Raises:
            TypeError: If an attribute value does not match its annotated type.
            ValueError: If an unknown attribute is provided.
        """
        self.name = name
        self.isactive = isactive
        for key, value in kwargs.items():
            if key not in self._fields:
                raise ValueError(f"Unknown attribute '{key}' for {self.__class__.__name__}")
            expected_type = self._fields[key]
            if not isinstance(value, expected_type):
                raise TypeError(f"Attribute '{key}' must be of type {expected_type}, got {type(value)}")
            setattr(self, key, value)
        logger.info(f"Initialized {self.__class__.__name__} instance with name={name}, isactive={isactive}")

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
            expected_type = self._fields[key]
            if not isinstance(value, expected_type):
                raise TypeError(f"Attribute '{key}' must be of type {expected_type}, got {type(value)}")
            setattr(self, key, value)
        logger.info(f"Updated attributes of {self.__class__.__name__}: {params}")

    def get(self) -> Dict[str, Any]:
        """Retrieve all attributes of the entity as a dictionary.

        Returns:
            dict: A dictionary of the entity's current attributes based on annotations.
        """
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

    def to_dict(self) -> dict:
        """Convert the entity to a dictionary for serialization.

        Automatically serializes the entity's state by reflecting on all annotated attributes,
        including nested entities which are recursively serialized.

        Returns:
            dict: A dictionary containing the entity's serialized data.
        """
        data = {"name": self.name, "isactive": self.isactive}
        for key in self._fields:
            if hasattr(self, key):
                value = getattr(self, key)
                # If the value is a BaseEntity, recursively serialize it
                if isinstance(value, BaseEntity):
                    data[key] = value.to_dict()
                else:
                    data[key] = value
        return data

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
            expected_type = cls._fields[key]
            # If the expected type is a subclass of BaseEntity and value is a dict, deserialize it
            if isinstance(expected_type, type) and issubclass(expected_type, BaseEntity) and isinstance(value, dict):
                kwargs[key] = expected_type.from_dict(value)
            else:
                if not isinstance(value, expected_type):
                    raise TypeError(f"Attribute '{key}' must be of type {expected_type}, got {type(value)}")
                kwargs[key] = value
        return cls(name=data.get("name"), isactive=data.get("isactive", True), **kwargs)

    def __repr__(self) -> str:
        """Return a string representation of the BaseEntity.

        Returns:
            str: A formatted string with the class name, name (if set), activation status, and attributes.
        """
        attrs = [f"name={self.name!r}" if self.name else ""]
        attrs.append(f"isactive={self.isactive}")
        attrs.extend(f"{k}={getattr(self, k)!r}" for k in self._fields if hasattr(self, k))
        return f"{self.__class__.__name__}({', '.join(attr for attr in attrs if attr)})"