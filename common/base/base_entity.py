# base/base_entity.py
from abc import ABC, abstractmethod
from common.utils.logging_setup import logger

class BaseEntity(ABC):
    """Abstract base class for entities with activation status and serialization support.

    Provides a foundation for various entity classes in the system, such as Observation, Source, Sources,
    IF, Frequencies, Scan, Scans, Telescope, SpaceTelescope, and Telescopes. Defines common functionality
    for managing an active/inactive state and requires subclasses to implement serialization methods.

    Attributes:
        isactive (bool): Indicates whether the entity is active or inactive.

    Notes:
        - Logging is integrated via `common.utils.logging_setup.logger` to track activation/deactivation events.
        - This is an abstract base class and cannot be instantiated directly; it must be subclassed.
        - Subclasses must implement `to_dict` and `from_dict` methods for serialization/deserialization.

    Examples:
        >>> class MyEntity(BaseEntity):
        ...     def to_dict(self):
        ...         return {"isactive": self.isactive}
        ...     @classmethod
        ...     def from_dict(cls, data):
        ...         return cls(isactive=data["isactive"])
        >>> entity = MyEntity(isactive=True)
        >>> entity.activate()
        >>> print(entity)
        MyEntity(isactive=True)
        >>> entity.deactivate()
        >>> print(entity)
        MyEntity(isactive=False)
    """
    def __init__(self, isactive: bool = True):
        """Initialize the BaseEntity with an activation status.

        Args:
            isactive (bool): Initial activation status of the entity. Defaults to True.
        """
        self.isactive = isactive

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
            str: A formatted string with the class name and activation status.
        """
        return f"{self.__class__.__name__}(isactive={self.isactive})"