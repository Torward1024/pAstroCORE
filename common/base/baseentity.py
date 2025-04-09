# base/base_entity.py
from abc import ABC, abstractmethod
from typing import Dict, Any
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
        # сollect type annotations from the class
        new_class._fields = getattr(new_class, '__annotations__', {})
        return new_class

class BaseEntity(ABC, metaclass=EntityMeta):
    """Abstract base class for entities with attribute management, type validation, and serialization support.

    Provides a foundation for various entity classes in the system, such as Observation, Source, Sources,
    IF, Frequencies, Scan, Scans, Telescope, SpaceTelescope, and Telescopes. Defines common functionality
    for managing attributes with type checking, an active/inactive state, and requires subclasses to
    implement serialization methods.

    Attributes:
        name (str, optional): An optional identifier for the entity.
        isactive (bool): Indicates whether the entity is active or inactive.
        _attributes (Dict[str, Any]): Internal storage for entity attributes.
        _fields (Dict[str, type]): Class-level mapping of attribute names to their expected types (from annotations).

    Notes:
        - Logging is integrated via `common.utils.logging_setup.logger` to track initialization and state changes.
        - This is an abstract base class and cannot be instantiated directly; it must be subclassed.
        - Subclasses must implement `to_dict` and `from_dict` methods for serialization/deserialization.
        - Type validation is enforced using `__annotations__` via the metaclass `EntityMeta`.

    Examples:
        >>> class MyEntity(BaseEntity):
        ...     name: str
        ...     value: int
        ...     def to_dict(self):
        ...         return {"name": self.name, "value": self.value, "isactive": self.isactive}
        ...     @classmethod
        ...     def from_dict(cls, data):
        ...         return cls(name=data["name"], isactive=data["isactive"], value=data["value"])
        >>> entity = MyEntity(name="test", isactive=True, value=42)
        >>> entity.set({"value": 100})
        >>> print(entity)
        MyEntity(name=test, isactive=True, value=100)
        >>> entity.deactivate()
        >>> print(entity)
        MyEntity(name=test, isactive=False, value=100)
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
        self._attributes: Dict[str, Any] = {}
        if kwargs:
            self.set(kwargs)
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
            self._attributes[key] = value
        logger.info(f"Updated attributes of {self.__class__.__name__}: {params}")

    def get(self) -> Dict[str, Any]:
        """Retrieve all attributes of the entity as a dictionary.

        Returns:
            dict: A copy of the entity's current attributes.
        """
        return self._attributes.copy()

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

    @abstractmethod
    def to_dict(self) -> dict:
        """Convert the entity to a dictionary for serialization.

        Abstract method to be implemented by subclasses to define how the entity's state is represented as a dictionary.

        Returns:
            dict: A dictionary containing the entity's serialized data.
        """
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> 'BaseEntity':
        """Create an entity instance from a dictionary.

        Abstract method to be implemented by subclasses to define how an entity is reconstructed from serialized data.

        Args:
            data (dict): Dictionary containing the entity's serialized data, typically from `to_dict`.

        Returns:
            BaseEntity: A new instance of the subclass initialized with the dictionary data.
        """
        pass

    def __repr__(self) -> str:
        """Return a string representation of the BaseEntity.

        Returns:
            str: A formatted string with the class name, name (if set), activation status, and attributes.
        """
        attrs = [f"name={self.name!r}" if self.name else ""]
        attrs.append(f"isactive={self.isactive}")
        attrs.extend(f"{k}={v!r}" for k, v in self._attributes.items())
        return f"{self.__class__.__name__}({', '.join(attr for attr in attrs if attr)})"