# base/base_entity.py
from abc import ABC, abstractmethod
from utils.logging_setup import logger

""" Base entity class to be used for base-class objects:
    1) Obesrvation (observation.py)
    2) Source, Sources (sources.py)
    3) IF, Frequencies (frequencies.py)
    4) Scan, Scans (scans.py)
    5) Telescope, SpaceTelescope, Telescopes (telescopes.py)
    """

class BaseEntity(ABC):
    def __init__(self, isactive: bool = True):
        """Init the entity"""
        self.isactive = isactive

    def activate(self) -> None:
        """Activate the entity"""
        self.isactive = True
        logger.info(f"Activated {self.__class__.__name__} instance")

    def deactivate(self) -> None:
        """Deactivate the entity"""
        self.isactive = False
        logger.info(f"Deactivated {self.__class__.__name__} instance")

    @abstractmethod
    def to_dict(self) -> dict:
        """Convert the entity to a dictionary for serialization"""
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> 'BaseEntity':
        """Create an entity from a dictionary"""
        pass

    def __repr__(self) -> str:
        """Return a string representation of the entity"""
        return f"{self.__class__.__name__}(isactive={self.isactive})"