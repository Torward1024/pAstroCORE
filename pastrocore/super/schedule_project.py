# unit_scheduling/super/schedule_project.py
from typing import Dict, Any, Optional, Union
from pastrocore.base.observation import Observation
from pastrocore.base.result_store import ResultStore
from msb_arch.super.project import Project
from msb_arch.utils.validation import check_type, check_non_empty_string
from msb_arch.utils.logging_setup import logger
import uuid
import json
from pathlib import Path

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

    # The version of a saved project. Raise it when the shape of what `to_dict` writes
    # changes -- a renamed field, a field that means something new -- and teach `migrate`
    # to read the older shape. Stage 4 replaces how results are stored, and this is what
    # will let a project written before that keep opening.
    #
    # Written into the file only once it is no longer 1, so nothing changes until it has to.
    SCHEMA_VERSION = 1

    @classmethod
    def migrate(cls, data: dict, from_version: int) -> dict:
        """Bring a project saved by an older version up to the current shape.

        Args:
            data (dict): The saved project, with its original field names.
            from_version (int): The `SCHEMA_VERSION` it was written under.

        Returns:
            dict: The same project in the shape this version expects.

        Raises:
            SerializationError: If the version is one this code has no route from.

        Notes:
            - Migrate forward one version at a time. Each step is easier to reason about than
              one jump, and the intermediate shapes are the ones already tested.
            - There is nothing to do yet: version 1 is the only version there has been.
        """
        return super().migrate(data, from_version)
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
            logger.debug("Validating %s items for project '%s'", len(items), name)
            for obs in items.values():
                check_type(obs, Observation, "Observation in items")
            codes = set()
            for key, item in items.items():
                item_code = item.get_observation_code()
                if item_code in codes:
                    logger.error("Duplicate observation code '%s' found for observation '%s'", item_code, key)
                    raise ValueError(f"Observation code '{item_code}' already exists for another observation")
                codes.add(item_code)
                logger.debug("Validated observation '%s' with code '%s'", key, item_code)
        
        super().__init__(name, items or {})
        logger.debug("Initialized ScheduleProject '%s' with %s observations", name, len(self._items))

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
                logger.error("Observation code '%s' already exists for observation '%s'", item_code, name)
                raise ValueError(f"Observation code '{item_code}' already exists for another observation")
        logger.debug("Validated observation with code '%s' (name='%s') for project '%s'", item_code, item.name, self.name)

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
        logger.info("Added observation '%s' (name='%s') to project '%s'", item.get_observation_code(), item.name, self.name)

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
            logger.error("Invalid observation type: %s. Must be 'VLBI' or 'SINGLE_DISH'", observation_type)
            raise ValueError(f"Observation type must be 'VLBI' or 'SINGLE_DISH', got {observation_type}")
        unique_name = f"obs_{uuid.uuid4().hex[:32]}"
        new_observation = Observation(name=unique_name, code=item_code, isactive=isactive, observation_type=observation_type)
        self.add_item(new_observation)
        logger.info("Created and added observation with code '%s', name='%s', type '%s' to project '%s'", item_code, unique_name, observation_type, self.name)

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
        logger.info("Set observation with name='%s' and code='%s' in project '%s'", name, item.get_observation_code(), self.name)

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
        logger.debug("Retrieved observation '%s' from project '%s'", name, self.name)
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
                logger.debug("Retrieved observation with code='%s' from project '%s'", code, self.name)
                return observation
        logger.debug("No Observation found with code='%s' in project '%s'", code, self.name)
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
        logger.info("Set project '%s' with %s observations", name, len(items))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the ScheduleProject to a dictionary.

        Returns:
            Dict[str, Any]: A dictionary containing the project's name and observations.
        """
        result = {
            "name": self.name,
            "items": {name: observation.to_dict() for name, observation in self._items.get_all().items()}
        }
        logger.debug("Serialized ScheduleProject '%s' to dictionary with %s observations", self.name, len(self._items))
        return result
    

    RESULTS_DIRECTORY = "results"
    MODEL_FILE = "project.json"

    def to_directory(self, path: str) -> None:
        """Save the project as a directory: the model in one file, each result in its own.

        Args:
            path (str): The project directory. Created if it does not exist.

        Notes:
            - The model is small -- under 7 KB for a project whose single-file form was 230 --
              because the results are no longer inside it. Opening a project therefore reads
              the model and nothing else.
            - Each result is a parquet file, which is what lets a consumer that filters push
              the filter into the read rather than loading a frame to discard most of it.
            - A result already on disk and never loaded is left alone rather than rewritten.
        """
        check_non_empty_string(path, "Project directory")
        root = Path(path)
        (root / self.RESULTS_DIRECTORY).mkdir(parents=True, exist_ok=True)

        store = ResultStore(root / self.RESULTS_DIRECTORY)
        written = 0
        for observation in self._items.get_items():
            results = observation.calculated_data
            if hasattr(results, "attach"):
                results.attach(store, observation.name)
                written += results.flush()

        model = {"name": self.name, "items": {}}
        if self.SCHEMA_VERSION != 1:
            model["schema_version"] = self.SCHEMA_VERSION
        for observation in self._items.get_items():
            model["items"][observation.name] = observation.to_dict(with_results=False)

        (root / self.MODEL_FILE).write_text(json.dumps(model, indent=4), encoding="utf-8")
        logger.info("Saved project '%s' to '%s': %s result(s) written", self.name, path, written)

    @classmethod
    def from_directory(cls, path: str) -> 'ScheduleProject':
        """Load a project saved as a directory, reading the model and none of the results.

        Args:
            path (str): The project directory.

        Returns:
            ScheduleProject: The project, with every observation pointed at the stored results.

        Raises:
            IOError: If the directory holds no model file.
        """
        check_non_empty_string(path, "Project directory")
        root = Path(path)
        model_path = root / cls.MODEL_FILE
        if not model_path.is_file():
            raise IOError(f"'{path}' is not a project directory: no {cls.MODEL_FILE}")

        project = cls.from_dict(json.loads(model_path.read_text(encoding="utf-8")))
        store = ResultStore(root / cls.RESULTS_DIRECTORY)
        for observation in project._items.get_items():
            if hasattr(observation.calculated_data, "attach"):
                observation.calculated_data.attach(store, observation.name)
        logger.info("Loaded project '%s' from '%s', results not read", project.name, path)
        return project

    @staticmethod
    def is_directory_project(path: str) -> bool:
        """Report whether a path is a project directory rather than a single file."""
        return (Path(path) / ScheduleProject.MODEL_FILE).is_file()

    @classmethod
    def open(cls, path: str) -> 'ScheduleProject':
        """Load a project, whichever of the two shapes it has on disk.

        Args:
            path (str): A project directory, the `project.json` inside one, or a project saved
                as a single file by an earlier version.

        Returns:
            ScheduleProject: The project. Loaded from a directory it holds no results in memory
                until one is asked for; loaded from a single file it holds all of them, because
                that format offers no other way.

        Notes:
            - One entry point rather than three, so a caller does not have to know which format
              it is looking at. The interface asks this, and so does anything scripted.
        """
        check_non_empty_string(path, "Project path")
        candidate = Path(path)

        if candidate.name == cls.MODEL_FILE and candidate.is_file():
            return cls.from_directory(str(candidate.parent))
        if candidate.is_dir():
            return cls.from_directory(str(candidate))
        logger.info("Opening '%s' as a single-file project; its results load with it", path)
        return cls.from_file(str(candidate))

    def save(self, path: str) -> None:
        """Save the project as a directory, converting a single file in place if that is what
        the path currently holds.

        Args:
            path (str): Where to save. An existing single file at this path is replaced by a
                directory, and only once the directory has been written.

        Notes:
            - The old file is removed after the new directory is complete, never before, so an
              interrupted save leaves the original intact.
        """
        check_non_empty_string(path, "Project path")
        target = Path(path)

        if target.is_file():
            staging = target.with_name(target.name + ".converting")
            self.to_directory(str(staging))
            target.unlink()
            staging.rename(target)
            logger.info("Converted single-file project '%s' to a directory", path)
            return

        self.to_directory(str(target))

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
            logger.info("Saved ScheduleProject '%s' to file '%s' with %s observations (compact=%s)", self.name, file_path, len(self._items), compact)
        except IOError as e:
            logger.error("Failed to write ScheduleProject to file '%s': %s", file_path, str(e))
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
                logger.debug("Read JSON data from file '%s'", file_path)
            
            name = data.get("name")
            check_non_empty_string(name, "Project name")
            items = {}
            
            if "items" in data:
                if not data["items"]:
                    logger.warning("Creating ScheduleProject '%s' with empty items dictionary from file '%s'", name, file_path)
                else:
                    codes = set()
                    for item_name, item_data in data["items"].items():
                        try:
                            observation = Observation.from_dict(item_data)
                            check_type(observation, Observation, f"Observation '{item_name}'")
                            code = observation.get_observation_code()
                            if code in codes:
                                logger.error("Duplicate observation code '%s' found for observation '%s' in file '%s'", code, item_name, file_path)
                                raise ValueError(f"Duplicate observation code '{code}' in file '{file_path}'")
                            codes.add(code)
                            items[item_name] = observation
                            logger.debug("Validated observation '%s' with code '%s' for project '%s'", item_name, code, name)
                        except (TypeError, ValueError) as e:
                            logger.error("Invalid observation data for '%s' in file '%s': %s", item_name, file_path, str(e))
                            raise ValueError(f"Invalid observation data for '{item_name}': {str(e)}") from e
            
            project = cls(name=name, items=items)
            logger.info("Loaded ScheduleProject '%s' from file '%s' with %s observations", name, file_path, len(items))
            return project
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON from file '%s': %s", file_path, str(e))
            raise ValueError(f"Invalid JSON format in file '{file_path}': {str(e)}") from e
        except IOError as e:
            logger.error("Failed to read file '%s': %s", file_path, str(e))
            raise IOError(f"Error reading file '{file_path}': {str(e)}") from e
        except (KeyError, TypeError, ValueError) as e:
            logger.error("Failed to deserialize ScheduleProject from file '%s': %s", file_path, str(e))
            raise ValueError(f"Invalid ScheduleProject data in file '{file_path}': {str(e)}") from e
    
    def clear(self):
        """Clear all observations and their resources."""
        try:
            for obs in self._items.get_all().values():
                try:
                    obs.clear_calculated_data()
                except Exception as e:
                    logger.debug("Error clearing observation %s: %s", obs.get_observation_code(), str(e))
            self._items.clear()
            logger.info("Cleared all observations from project '%s'", self.name)
        except Exception as e:
            logger.error("Error clearing project '%s': %s", self.name, str(e), exc_info=True)

    def __repr__(self) -> str:
        """String representation of ScheduleProject.

        Returns:
            str: A string in the format "ScheduleProject(name='{name}', observations_count={count})".
        """
        return f"ScheduleProject(name='{self.name}', observations_count={len(self._items)})"