# /unit_scheduling/super/schedule_project.py
from typing import Dict, Any, Optional
from pastrocore.base.observation import Observation
from common.super.project import Project
from common.utils.validation import check_type, check_non_empty_string
from common.utils.logging_setup import logger
import uuid

class ScheduleProject(Project):
    """Container for managing multiple observations, inheriting from Project.

    Represents a project that organizes a collection of Observation objects, indexed by their observation names.
    Provides methods to add, create, set, retrieve, and manage observations, as well as serialize/deserialize the project.

    Examples:
        >>> project = ScheduleProject(name="MyProject")
        >>> project.create_item(item_name="OBS001")
        >>> project.get_observation("OBS001").get_observation_code()
        'OBS001'
        >>> project.set_item("OBS001", Observation(name="OBS001", isactive=False))
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
            items (Dict[str, Observation], optional): Initial dictionary of observations, keyed by observation name.
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
        logger.info(f"Added observation '{item.get_observation_code()}' to project '{self.name}'")

    def create_item(self, item_code: str = "OBS_DEFAULT", isactive: bool = True, observation_type: str = "VLBI") -> None:
        """Create and add a new Observation object to the project.

        Args:
            item_code (str): The code for the new observation. Defaults to "OBS_DEFAULT".
            isactive (bool): Whether the new observation is active. Defaults to True.
            observation_type (str): The type of observation ('VLBI' or 'SINGLE_DISH'). Defaults to "VLBI".

        Raises:
            ValueError: If item_code is not a non-empty string or observation_type is invalid.
        """
        check_non_empty_string(item_code, "Observation code")
        if observation_type not in ["VLBI", "SINGLE_DISH"]:
            logger.error(f"Invalid observation type: {observation_type}. Must be 'VLBI' or 'SINGLE_DISH'")
            raise ValueError(f"Observation type must be 'VLBI' or 'SINGLE_DISH', got {observation_type}")
        unique_name = f"obs_{uuid.uuid4().hex[:32]}"
        new_observation = Observation(name=unique_name, code=item_code, isactive=isactive, observation_type=observation_type)
        self.add_item(new_observation)
        logger.info(f"Created and added observation with code '{item_code}', name '{unique_name}', type '{observation_type}' to project '{self.name}'")

    def set_item(self, name: str, item: Observation) -> None:
        """Set or replace an observation in the project by its name.

        Args:
            name (str): The name of the observation to set.
            item (Observation): The Observation object to set.

        Raises:
            TypeError: If the item is not an Observation object.
        """
        check_type(item, Observation, "Observation")
        super().set_item(name, item)
        logger.info(f"Set observation with name='{name}' and code='{item.get_observation_code}' in project '{self.name}'")

    def get_observation(self, name: str) -> Observation:
        """Retrieve an observation by its name.

        Args:
            name (str): The name of the observation to retrieve.

        Returns:
            Observation: The Observation object with the specified name.

        Raises:
            KeyError: If the observation name is not found.
        """
        observation = self.get_item(name)
        logger.info(f"Retrieved observation '{name}' from project '{self.name}'")
        return observation
    
    def get_observation_by_code(self, code: str) -> Observation:
        """Retrieve an observation by its code.

        Args:
            code (str): The code of the observation to retrieve.

        Returns:
            Observation: The Observation object with the specified code.

        Raises:
            KeyError: If the observation code is not found.
            ValueError: If the code is not a non-empty string.
        """
        check_non_empty_string(code, "Observation code")
        for name, observation in self._items.get_all().items():
            if observation.get_observation_code() == code:
                logger.info(f"Retrieved observation with code='{code}' from project '{self.name}'")
                return observation
        logger.error(f"Observation with code='{code}' not found in project '{self.name}'")
        raise KeyError(f"Observation with code '{code}' not found")

    def set_project(self, name: str, items: Dict[str, Observation]) -> None:
        """Set the entire project configuration, replacing name and observations.

        Args:
            name (str): The new name for the project. Must be a non-empty string.
            items (Dict[str, Observation]): The new dictionary of observations, keyed by observation name.

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
        logger.info(f"Retrieved project configuration for '{self.name}' with {len(self._items)} observations")
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert ScheduleProject to a dictionary for serialization.

        Returns:
            Dict[str, Any]: A dictionary with the project name and observations.
        """
        result = super().to_dict()
        logger.info(f"Serialized ScheduleProject '{self.name}' with {len(self._items)} observations")
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
            
            if "items" in data:
                if not data["items"]:
                    raise ValueError("Items dictionary cannot be empty")
                for item_name, item_data in data["items"].items():
                    items[item_name] = Observation.from_dict(item_data)
                    logger.info(f"Imported Project: name='{name}'")
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
        return f"ScheduleProject(name='{self.name}', observations_count={len(self._items)})"