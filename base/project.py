from typing import List, Dict, Any
from base.observation import Observation
from utils.validation import check_type, check_non_empty_string
from utils.logging_setup import logger

class Project:
    """Container for managing multiple observations"""
    def __init__(self, name: str, observations: List[Observation] = None):
        """Initialize a Project with a name and optional list of observations."""
        check_non_empty_string(name, "Project name")
        self._name = name
        self._observations = observations if observations else []
        for obs in self._observations:
            check_type(obs, Observation, "Observation in observations list")
        logger.info(f"Initialized Project '{name}' with {len(self._observations)} observations")

    def add_observation(self, observation: Observation) -> None:
        """Add an observation to the project"""
        check_type(observation, Observation, "Observation")
        self._observations.append(observation)
        logger.info(f"Added observation '{observation.get_observation_code()}' to Project '{self._name}'")

    def insert_observation(self, observation: Observation, index: int) -> None:
        """Insert an observation at the specified index"""
        check_type(observation, Observation, "Observation")
        if not (0 <= index <= len(self._observations)):
            logger.error(f"Invalid index {index} for insertion in Project '{self._name}' with {len(self._observations)} observations")
            raise IndexError(f"Index {index} out of range for Project with {len(self._observations)} observations")
        self._observations.insert(index, observation)
        logger.info(f"Inserted observation '{observation.get_observation_code()}' at index {index} in Project '{self._name}'")

    def remove_observation(self, index: int) -> None:
        """Remove an observation at the specified index"""
        if not (0 <= index < len(self._observations)):
            logger.error(f"Invalid index {index} for removal in Project '{self._name}' with {len(self._observations)} observations")
            raise IndexError(f"Index {index} out of range for Project with {len(self._observations)} observations")
        obs = self._observations.pop(index)
        logger.info(f"Removed observation '{obs.get_observation_code()}' from Project '{self._name}'")

    def set_observation(self, observation: Observation, index: int) -> None:
        """Set an observation at the specified index"""
        check_type(observation, Observation, "Observation")
        if not (0 <= index < len(self._observations)):
            logger.error(f"Invalid index {index} for setting observation in Project '{self._name}' with {len(self._observations)} observations")
            raise IndexError(f"Index {index} out of range for Project with {len(self._observations)} observations")
        self._observations[index] = observation
        logger.info(f"Set observation '{observation.get_observation_code()}' at index {index} in Project '{self._name}'")

    def get_observation(self, index: int) -> Observation:
        """Get an observation at the specified index"""
        if not (0 <= index < len(self._observations)):
            logger.error(f"Invalid index {index} for retrieval in Project '{self._name}' with {len(self._observations)} observations")
            raise IndexError(f"Index {index} out of range for Project with {len(self._observations)} observations")
        obs = self._observations[index]
        logger.info(f"Retrieved observation '{obs.get_observation_code()}' from Project '{self._name}'")
        return obs

    def get_observations(self) -> List[Observation]:
        """Get all observations in the project"""
        return self._observations

    def to_dict(self) -> Dict[str, Any]:
        """Convert Project to a dictionary for serialization"""
        return {"name": self._name, "observations": [obs.to_dict() for obs in self._observations]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Create a Project from a dictionary"""
        return cls(name=data["name"], observations=[Observation.from_dict(obs) for obs in data["observations"]])

    def get_name(self) -> str:
        """Get the project name"""
        return self._name

    def set_name(self, name: str) -> None:
        """Set the project name."""
        check_non_empty_string(name, "Project name")
        self._name = name
        logger.info(f"Set project name to '{name}'")

    def __repr__(self) -> str:
        """String representation of Project"""
        return f"Project(name='{self._name}', observations_count={len(self._observations)})"