# /unit_scheduling/super/schedule_project.py
from typing import Dict, Any, Optional
from unit_scheduling_2.base.observation import Observation
from common.super.project import Project
from common.utils.validation import check_type, check_non_empty_string
from common.utils.logging_setup import logger

class ScheduleProject(Project):
    """Container for managing multiple observations, inheriting from Project.

    Represents a project that organizes a collection of Observation objects, indexed by their observation codes.
    Provides methods to add, create, set, retrieve, and manage observations, as well as serialize/deserialize the project.

    Examples:
        >>> project = ScheduleProject(name="MyProject")
        >>> project.create_item(item_code="OBS001")
        >>> project.get_observation("OBS001").get_observation_code()
        'OBS001'
        >>> project.set_item("OBS001", Observation(observation_code="OBS001", isactive=False))
        >>> project.get_observation("OBS001").isactive
        False
        >>> project.set_project(name="NewProject", items={})
        >>> project.get_project()["name"]
        'NewProject'
    """
    _item_type = Observation

    def __init__(self, name: str = "OBS_DEFAULT_PROJECT", items: Optional[Dict[str, Observation]] = None):
        """Initialize a ScheduleProject with a name and optional dictionary of observations.

        Args:
            name (str): The name of the project. Defaults to "OBS_DEFAULT_PROJECT".
            items (Dict[str, Observation], optional): Initial dictionary of observations, keyed by observation code.
                                                    Defaults to an empty dict if None.

        Raises:
            TypeError: If any item in the items dict is not an Observation object.
        """
        if items:
            for obs in items.values():
                check_type(obs, Observation, "Observation in items")
        super().__init__(name, items)
        logger.info(f"Initialized ScheduleProject '{name}' with {len(self._items)} observations")

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
        self.add_item(new_observation)
        logger.info(f"Created and added observation '{item_code}' to project '{self._name}'")

    def set_item(self, observation_code: str, item: Observation) -> None:
        """Set or replace an observation in the project by its code.

        Args:
            observation_code (str): The code of the observation to set.
            item (Observation): The Observation object to set.

        Raises:
            TypeError: If the item is not an Observation object.
        """
        check_type(item, Observation, "Observation")
        super().set_item(observation_code, item)
        logger.info(f"Set observation '{observation_code}' in project '{self._name}'")

    def get_observation(self, observation_code: str) -> Observation:
        """Retrieve an observation by its code.

        Args:
            observation_code (str): The code of the observation to retrieve.

        Returns:
            Observation: The Observation object with the specified code.

        Raises:
            KeyError: If the observation code is not found.
        """
        observation = self.get_item(observation_code)
        logger.info(f"Retrieved observation '{observation_code}' from project '{self._name}'")
        return observation

    def set_project(self, name: str, items: Dict[str, Observation]) -> None:
        """Set the entire project configuration, replacing name and observations.

        Args:
            name (str): The new name for the project. Must be a non-empty string.
            items (Dict[str, Observation]): The new dictionary of observations, keyed by observation code.

        Raises:
            TypeError: If any item in items is not an Observation object.
            ValueError: If name is not a non-empty string.
        """
        for obs in items.values():
            check_type(obs, Observation, "Observation in items")
        super().set_project(name, items)
        logger.info(f"Set ScheduleProject: '{name}' with {len(items)} observations")

    def get_project(self) -> Dict[str, Any]:
        """Get the entire project configuration as a dictionary.

        Returns:
            Dict[str, Any]: A dictionary containing the project name and a list of observation dictionaries.
        """
        result = super().get_project()
        result["observations"] = [obs.to_dict() for obs in self._items.get_items()]
        logger.info(f"Retrieved project configuration for '{self._name}' with {len(self._items)} observations")
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert ScheduleProject to a dictionary for serialization.

        Returns:
            Dict[str, Any]: A dictionary with the project name and observations.
        """
        result = super().to_dict()
        logger.info(f"Serialized ScheduleProject '{self._name}' with {len(self._items)} observations")
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduleProject':
        """Create a ScheduleProject from a dictionary.

        Supports both new format (with 'items') and legacy format (with 'observations').

        Args:
            data (Dict[str, Any]): A dictionary containing 'name' and either 'items' or 'observations'.

        Returns:
            ScheduleProject: A new ScheduleProject instance populated with the dictionary data.

        Raises:
            ValueError: If the data is invalid or cannot be deserialized.
        """
        try:
            name = data.get("name")
            check_non_empty_string(name, "Project name")
            items = {}
            
            # Handle new format ('items')
            if "items" in data:
                if not data["items"]:  # Check if items is empty
                    raise ValueError("Items dictionary cannot be empty")
                for code, item_data in data["items"].items():
                    items[code] = Observation.from_dict(item_data)
            else:
                raise ValueError("No 'items' or 'observations' key found in data")
            
            return cls(name=name, items=items)
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Failed to deserialize ScheduleProject from dict: {str(e)}")
            raise ValueError(f"Invalid ScheduleProject data: {str(e)}") from e

    def __repr__(self) -> str:
        """String representation of ScheduleProject.

        Returns:
            str: A string in the format "ScheduleProject(name='{name}', observations_count={count})".
        """
        return f"ScheduleProject(name='{self._name}', observations_count={len(self._items)})"