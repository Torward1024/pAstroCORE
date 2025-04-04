from typing import List, Dict, Any
from unit_scheduling.base.observation import Observation

from common.super.project import Project
from common.utils.validation import check_type, check_non_empty_string
from common.utils.logging_setup import logger

class ScheduleProject(Project):
    """Container for managing multiple observations, inheriting from AbstractProject"""
    def __init__(self, name: str = "OBS_DEFAULT_PROJECT", observations: List[Observation] = None):
        """Initialize an ScheduleProject with a name and optional list of observations."""
        super().__init__(name, observations if observations else [])
        for obs in self._items:
            check_type(obs, Observation, "Observation in observations list")
        logger.info(f"Initialized project '{name}' with {len(self._items)} observations")

    def add_item(self, item: Observation) -> None:
        """Add an observation to the project"""
        check_type(item, Observation, "Observation")
        super().add_item(item)
        logger.info(f"Added observation '{item.get_observation_code()}' to project '{self._name}'")

    def create_item(self, item_code: str = "OBS_DEFAULT", isactive: bool = True) -> None:
        """Create and add a new Observation object to the project"""
        check_non_empty_string(item_code, "Observation code")
        new_observation = Observation(observation_code=item_code, isactive=isactive)
        self._items.append(new_observation)
        logger.info(f"Created and added observation '{item_code}' to project '{self._name}'")

    def insert_item(self, item: Observation, index: int) -> None:
        """Insert an observation at the specified index"""
        check_type(item, Observation, "Observation")
        super().insert_item(item, index)
        logger.info(f"Inserted observation '{item.get_observation_code()}' at index {index} in project '{self._name}'")

    def set_item(self, item: Observation, index: int) -> None:
        """Set an observation at the specified index"""
        check_type(item, Observation, "Observation")
        super().set_item(item, index)
        logger.info(f"Set observation '{item.get_observation_code()}' at index {index} in project '{self._name}'")

    def get_by_index(self, index: int) -> Observation:
        """Get an observation at the specified index"""
        obs = super().get_by_index(index)
        return obs

    def get_items(self) -> List[Observation]:
        """Get all observations in the project"""
        return super().get_items()

    def to_dict(self) -> Dict[str, Any]:
        """Convert ScheduleProject to a dictionary for serialization"""
        return {"name": self._name, "observations": [obs.to_dict() for obs in self._items]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduleProject':
        """Create an ScheduleProject from a dictionary"""
        return cls(name=data["name"], observations=[Observation.from_dict(obs) for obs in data["observations"]])

    def __repr__(self) -> str:
        """String representation of ScheduleProject"""
        return f"ScheduleProject(name='{self._name}', observations_count={len(self._items)})"