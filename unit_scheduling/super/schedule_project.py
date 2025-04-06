# /unit_scheduling/super/schedule_project.py
from typing import List, Dict, Any
from unit_scheduling.base.observation import Observation

from common.super.project import Project
from common.utils.validation import check_type, check_non_empty_string
from common.utils.logging_setup import logger

class ScheduleProject(Project):
    """Container for managing multiple observations, inheriting from Project.

    Represents a project that organizes a collection of Observation objects, providing methods
    to add, create, insert, set, and retrieve observations, as well as manage the project itself.
    Supports serialization to and from dictionaries for data persistence.

    Examples:
        >>> project = ScheduleProject(name="MyProject")
        >>> project.create_item(item_code="OBS001")
        >>> project.get_by_index(0).get_observation_code()
        'OBS001'
        >>> project.set_project(name="NewProject", observations=[])
        >>> project.get_project()["name"]
        'NewProject'
    """
    def __init__(self, name: str = "OBS_DEFAULT_PROJECT", observations: List[Observation] = None):
        """Initialize a ScheduleProject with a name and optional list of observations.

        Args:
            name (str): The name of the project. Defaults to "OBS_DEFAULT_PROJECT".
            observations (List[Observation], optional): Initial list of observations. Defaults to an empty list if None.

        Raises:
            TypeError: If any item in the observations list is not an Observation object.
        """
        super().__init__(name, observations if observations else [])
        for obs in self._items:
            check_type(obs, Observation, "Observation in observations list")

    def add_item(self, item: Observation) -> None:
        """Add an observation to the project.

        Args:
            item (Observation): The Observation object to add.

        Raises:
            TypeError: If the item is not an Observation object.
        """
        check_type(item, Observation, "Observation")
        super().add_item(item)
        logger.info(f"Added observation '{item.get_observation_code()}' to project '{self._name}'")

    def create_item(self, item_code: str = "OBS_DEFAULT", isactive: bool = True) -> None:
        """Create and add a new Observation object to the project.

        Args:
            item_code (str): The code for the new observation. Defaults to "OBS_DEFAULT".
            isactive (bool): Whether the new observation is active. Defaults to True.

        Raises:
            ValueError: If item_code is not a non-empty string.
        """
        check_non_empty_string(item_code, "Observation code")
        new_observation = Observation(observation_code=item_code, isactive=isactive)
        self._items.append(new_observation)
        logger.info(f"Created and added observation '{item_code}' to project '{self._name}'")

    def insert_item(self, item: Observation, index: int) -> None:
        """Insert an observation at the specified index.

        Args:
            item (Observation): The Observation object to insert.
            index (int): The index at which to insert the observation.

        Raises:
            TypeError: If the item is not an Observation object.
            IndexError: If the index is out of range.
        """
        check_type(item, Observation, "Observation")
        super().insert_item(item, index)
        logger.info(f"Inserted observation '{item.get_observation_code()}' at index {index} in project '{self._name}'")

    def set_item(self, item: Observation, index: int) -> None:
        """Set an observation at the specified index.

        Args:
            item (Observation): The Observation object to set.
            index (int): The index at which to set the observation.

        Raises:
            TypeError: If the item is not an Observation object.
            IndexError: If the index is out of range.
        """
        check_type(item, Observation, "Observation")
        super().set_item(item, index)
        logger.info(f"Set observation '{item.get_observation_code()}' at index {index} in project '{self._name}'")

    def get_by_index(self, index: int) -> Observation:
        """Get an observation at the specified index.

        Args:
            index (int): The index of the observation to retrieve.

        Returns:
            Observation: The Observation object at the specified index.

        Raises:
            IndexError: If the index is out of range.
        """
        return super().get_by_index(index)

    def get_items(self) -> List[Observation]:
        """Get all observations in the project.

        Returns:
            List[Observation]: A list of all Observation objects in the project.
        """
        return super().get_items()

    def set_project(self, name: str, observations: List[Observation]) -> None:
        """Set the entire project configuration, replacing name and observations.

        Args:
            name (str): The new name for the project. Must be a non-empty string.
            observations (List[Observation]): The new list of observations to set.

        Raises:
            TypeError: If any item in observations is not an Observation object.
            ValueError: If name is not a non-empty string.
        """
        for obs in observations:
            check_type(obs, Observation, "Observation in observations list")
        super().set_project(name, observations)
        logger.info(f"Set project: '{name}' with {len(observations)} observations")

    def get_project(self) -> Dict[str, Any]:
        """Get the entire project configuration as a dictionary.

        Returns:
            Dict[str, Any]: A dictionary containing the project name and a list of observation dictionaries.
        """
        result = super().get_project()
        result["observations"] = [obs.to_dict() for obs in self._items]  # Переопределяем для сериализации Observation
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert ScheduleProject to a dictionary for serialization.

        Returns:
            Dict[str, Any]: A dictionary with the project name and a list of observation dictionaries.
        """
        return {"name": self._name, "observations": [obs.to_dict() for obs in self._items]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduleProject':
        """Create a ScheduleProject from a dictionary.

        Args:
            data (Dict[str, Any]): A dictionary containing "name" and "observations" keys.

        Returns:
            ScheduleProject: A new ScheduleProject instance populated with the dictionary data.
        """
        return cls(name=data["name"], observations=[Observation.from_dict(obs) for obs in data["observations"]])

    def __repr__(self) -> str:
        """String representation of ScheduleProject.

        Returns:
            str: A string in the format "ScheduleProject(name='{name}', observations_count={count})".
        """
        return f"ScheduleProject(name='{self._name}', observations_count={len(self._items)})"