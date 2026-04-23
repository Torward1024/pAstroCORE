# unit_scheduling/super/schedule_project.py
from typing import Dict, Any, Optional, Union
from pastrocore.base.observation import Observation
from msb_arch.super.project import Project
from msb_arch.utils.validation import check_type, check_non_empty_string
from msb_arch.utils.logging_setup import logger
import uuid
import json

class ScheduleProject(Project):
    """Container for managing multiple observations, inheriting from Project.

    Represents a project that organizes a collection of Observation objects, indexed by their observation names.
    Provides methods to add, create, set, retrieve, and manage observations, as well as serialize/deserialize the project.
    Ensures that observation codes are unique within the project using _validate_item.

    Examples:
        >>> project = ScheduleProject(name="MyProject")
        >>> project.create_item(item_code="OBS001")
        >>> project.get_observation_by_code("OBS001").get_observation_code()
        'OBS001'
        >>> project.set_item("OBS001", Observation(name="OBS001", code="OBS002", isactive=False))
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
            ValueError: If any observation codes are not unique or other validation fails.
        """
        check_non_empty_string(name, "Project name")
        if items:
            logger.debug(f"Validating {len(items)} items for project '{name}'")
            for obs in items.values():
                check_type(obs, Observation, "Observation in items")
            codes = set()
            for key, item in items.items():
                item_code = item.get_observation_code()
                if item_code in codes:
                    logger.error(f"Duplicate observation code '{item_code}' found for observation '{key}'")
                    raise ValueError(f"Observation code '{item_code}' already exists for another observation")
                codes.add(item_code)
                logger.debug(f"Validated observation '{key}' with code '{item_code}'")
        
        super().__init__(name, items or {})
        logger.debug(f"Initialized ScheduleProject '{name}' with {len(self._items)} observations")

    def _validate_item(self, item: Observation, exclude_name: Optional[str] = None, exclude_code: Optional[str] = None) -> None:
        """Validate an observation item, ensuring its code is unique within the project.

        Args:
            item (Observation): The observation to validate.
            exclude_name (str, optional): Name of the item to exclude from validation (used when updating existing items).
            exclude_code (str, optional): Code of the item to exclude from validation (used when updating items with the same code).

        Raises:
            TypeError: If the item is not an Observation object.
            ValueError: If the observation code is not unique (unless excluded by name or code).
        """
        check_type(item, Observation, "Observation")
        item_code = item.get_observation_code()
        for name, existing_item in self._items.get_all().items():
            existing_code = existing_item.get_observation_code()
            if (name != exclude_name and item_code == existing_code and
                    (exclude_code is None or existing_code != exclude_code)):
                logger.error(f"Observation code '{item_code}' already exists for observation '{name}'")
                raise ValueError(f"Observation code '{item_code}' already exists for another observation")
        logger.debug(f"Validated observation with code '{item_code}' (name='{item.name}') for project '{self.name}'")

    def add_item(self, item: Observation) -> None:
        """Add an observation to the project.

        Args:
            item (Observation): The Observation object to add.

        Raises:
            TypeError: If the item is not an Observation object.
            ValueError: If the observation code is not unique.
        """
        self._validate_item(item)
        super().add_item(item)
        logger.info(f"Added observation '{item.get_observation_code()}' (name='{item.name}') to project '{self.name}'")

    def create_item(self, item_code: str = "OBS_DEFAULT", isactive: bool = True, observation_type: str = "VLBI") -> None:
        """Create and add a new Observation object to the project.

        Args:
            item_code (str): The code for the new observation. Defaults to "OBS_DEFAULT".
            isactive (bool): Whether the new observation is active. Defaults to True.
            observation_type (str): The type of observation ('VLBI' or 'SINGLE_DISH'). Defaults to "VLBI".

        Raises:
            ValueError: If item_code is not a non-empty string, observation_type is invalid, or item_code already exists.
        """
        check_non_empty_string(item_code, "Observation code")
        if observation_type not in ["VLBI", "SINGLE_DISH"]:
            logger.error(f"Invalid observation type: {observation_type}. Must be 'VLBI' or 'SINGLE_DISH'")
            raise ValueError(f"Observation type must be 'VLBI' or 'SINGLE_DISH', got {observation_type}")
        unique_name = f"obs_{uuid.uuid4().hex[:32]}"
        new_observation = Observation(name=unique_name, code=item_code, isactive=isactive, observation_type=observation_type)
        self.add_item(new_observation)
        logger.info(f"Created and added observation with code '{item_code}', name='{unique_name}', type '{observation_type}' to project '{self.name}'")

    def set_item(self, name: str, item: Observation) -> None:
        """Set or replace an observation in the project by its name.

        Args:
            name (str): The name of the observation to set.
            item (Observation): The Observation object to set.

        Raises:
            TypeError: If the item is not an Observation object.
            ValueError: If the observation code is not unique (excluding the item being replaced).
        """
        check_type(item, Observation, "Observation")
        existing_code = None
        if name in self._items:
            existing_code = self._items[name].get_observation_code()
        self._validate_item(item, exclude_name=name, exclude_code=existing_code)
        super().set_item(name, item)
        logger.info(f"Set observation with name='{name}' and code='{item.get_observation_code()}' in project '{self.name}'")

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
        logger.debug(f"Retrieved observation '{name}' from project '{self.name}'")
        return observation

    def get_observation_by_code(self, code: str) -> Optional[Observation]:
        """Retrieve an observation by its code.

        Args:
            code (str): The code of the observation to retrieve.

        Returns:
            Optional[Observation]: The Observation object with the specified code, or None if not found.

        Raises:
            ValueError: If the code is not a non-empty string.
        """
        check_non_empty_string(code, "Observation code")
        for name, observation in self._items.get_all().items():
            if observation.get_observation_code() == code:
                logger.debug(f"Retrieved observation with code='{code}' from project '{self.name}'")
                return observation
        logger.debug(f"No Observation found with code='{code}' in project '{self.name}'")
        return None

    def set_project(self, name: str, items: Dict[str, Observation]) -> None:
        """Set the entire project configuration.

        Args:
            name (str): The new name of the project.
            items (Dict[str, Observation]): The new dictionary of observations.

        Raises:
            TypeError: If any item in the items dict is not an Observation object.
            ValueError: If any observation codes are not unique or other validation fails.
        """
        if items:
            for obs in items.values():
                check_type(obs, Observation, "Observation in items")
            for key, item in items.items():
                self._validate_item(item, exclude_name=key)
        super().set_project(name, items)
        logger.info(f"Set project '{name}' with {len(items)} observations")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the ScheduleProject to a dictionary.

        Returns:
            Dict[str, Any]: A dictionary containing the project's name and observations.
        """
        result = {
            "name": self.name,
            "items": {name: observation.to_dict() for name, observation in self._items.get_all().items()}
        }
        logger.debug(f"Serialized ScheduleProject '{self.name}' to dictionary with {len(self._items)} observations")
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduleProject':
        """Deserialize a ScheduleProject from a dictionary.

        Args:
            data (Dict[str, Any]): Dictionary containing the project data.

        Returns:
            ScheduleProject: A new ScheduleProject instance populated with the deserialized data.

        Raises:
            ValueError: If the data is invalid, missing required keys, or contains non-unique observation codes.
        """
        try:
            name = data.get("name")
            check_non_empty_string(name, "Project name")
            items = {}
            
            if "items" in data:
                if not data["items"]:
                    logger.warning(f"Creating ScheduleProject '{name}' with empty items dictionary")
                else:
                    for item_name, item_data in data["items"].items():
                        observation = Observation.from_dict(item_data)
                        items[item_name] = observation
                        logger.debug(f"Imported observation '{item_name}' for project '{name}'")
            
            project = cls(name=name, items=items)
            logger.info(f"Deserialized ScheduleProject '{name}' from dict with {len(items)} observations")
            return project
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Failed to deserialize ScheduleProject from dict: {str(e)}")
            raise ValueError(f"Invalid ScheduleProject data: {str(e)}") from e

    def to_file(self, file_path: str, compact: bool = False) -> None:
        """Serialize ScheduleProject to a JSON file without loading the full dictionary into memory.

        Args:
            file_path (str): Path to the output JSON file.
            compact (bool): If True, write compact JSON without indentation. Defaults to False.

        Raises:
            ValueError: If file_path is not a non-empty string.
            IOError: If there are issues with file writing.
        """
        check_non_empty_string(file_path, "File path")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                indent = None if compact else 4
                f.write('{' if compact else '{\n')
                name_line = f'"name": "{json.dumps(self.name)[1:-1]}"' if compact else f'  "name": "{json.dumps(self.name)[1:-1]}",\n'
                f.write(name_line)
                items_line = ',' if compact else ',\n'
                f.write('"items": {' if compact else '  "items": {\n')
                items = self._items.get_all().items()
                items_count = len(self._items)
                for i, (name, observation) in enumerate(items):
                    obs_dict = observation.to_dict()
                    name_prefix = '' if compact else '    '
                    f.write(f'{name_prefix}"{json.dumps(name)[1:-1]}": ')
                    json.dump(obs_dict, f, indent=indent)
                    if i < items_count - 1:
                        f.write(items_line)
                    else:
                        f.write('' if compact else '\n')
                f.write('}' if compact else '  }\n')
                f.write('}' if compact else '}\n')
            logger.info(f"Saved ScheduleProject '{self.name}' to file '{file_path}' with {len(self._items)} observations (compact={compact})")
        except IOError as e:
            logger.error(f"Failed to write ScheduleProject to file '{file_path}': {str(e)}")
            raise IOError(f"Error writing to file '{file_path}': {str(e)}") from e

    @classmethod
    def from_file(cls, file_path: str) -> 'ScheduleProject':
        """Deserialize a ScheduleProject from a JSON file with minimal memory usage.

        Args:
            file_path (str): Path to the input JSON file.

        Returns:
            ScheduleProject: A new ScheduleProject instance populated with the data from the file.

        Raises:
            ValueError: If file_path is not a non-empty string or the JSON data is invalid.
            IOError: If there are issues with file reading.
        """
        check_non_empty_string(file_path, "File path")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.debug(f"Read JSON data from file '{file_path}'")
            
            name = data.get("name")
            check_non_empty_string(name, "Project name")
            items = {}
            
            if "items" in data:
                if not data["items"]:
                    logger.warning(f"Creating ScheduleProject '{name}' with empty items dictionary from file '{file_path}'")
                else:
                    codes = set()
                    for item_name, item_data in data["items"].items():
                        try:
                            observation = Observation.from_dict(item_data)
                            check_type(observation, Observation, f"Observation '{item_name}'")
                            code = observation.get_observation_code()
                            if code in codes:
                                logger.error(f"Duplicate observation code '{code}' found for observation '{item_name}' in file '{file_path}'")
                                raise ValueError(f"Duplicate observation code '{code}' in file '{file_path}'")
                            codes.add(code)
                            items[item_name] = observation
                            logger.debug(f"Validated observation '{item_name}' with code '{code}' for project '{name}'")
                        except (TypeError, ValueError) as e:
                            logger.error(f"Invalid observation data for '{item_name}' in file '{file_path}': {str(e)}")
                            raise ValueError(f"Invalid observation data for '{item_name}': {str(e)}") from e
            
            project = cls(name=name, items=items)
            logger.info(f"Loaded ScheduleProject '{name}' from file '{file_path}' with {len(items)} observations")
            return project
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from file '{file_path}': {str(e)}")
            raise ValueError(f"Invalid JSON format in file '{file_path}': {str(e)}") from e
        except IOError as e:
            logger.error(f"Failed to read file '{file_path}': {str(e)}")
            raise IOError(f"Error reading file '{file_path}': {str(e)}") from e
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Failed to deserialize ScheduleProject from file '{file_path}': {str(e)}")
            raise ValueError(f"Invalid ScheduleProject data in file '{file_path}': {str(e)}") from e
    
    def clear(self):
        """Clear all observations and their resources."""
        try:
            for obs in self._items.get_all().values():
                try:
                    obs.clear_calculated_data()
                except Exception as e:
                    logger.debug(f"Error clearing observation {obs.get_observation_code()}: {str(e)}")
            self._items.clear()
            logger.info(f"Cleared all observations from project '{self.name}'")
        except Exception as e:
            logger.error(f"Error clearing project '{self.name}': {str(e)}")

    def __repr__(self) -> str:
        """String representation of ScheduleProject.

        Returns:
            str: A string in the format "ScheduleProject(name='{name}', observations_count={count})".
        """
        return f"ScheduleProject(name='{self.name}', observations_count={len(self._items)})"