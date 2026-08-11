# unit_scheduling/super/schedule_project.py
from typing import Dict, Any, Optional, Union
from pastrocore.base.observation import Observation
from pastrocore.base.result_store import ResidencyBudget, ResultStore
from pastrocore.base.scratch import ScratchSpace
from msb_arch.super.project import Project
from msb_arch.utils.validation import check_type, check_non_empty_string
from msb_arch.utils.logging_setup import logger
import uuid
import json
import shutil
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
            if not hasattr(results, "attach"):
                continue
            # Results calculated before the project had a directory are already on disk, in
            # this session's scratch. Saving moves them rather than asking for them again.
            written += results.migrate_to(store)
            results.attach(store, observation.name, budget=self.residency_budget)
            written += results.flush()

        model = {"name": self.name, "items": {}}
        if self.SCHEMA_VERSION != 1:
            model["schema_version"] = self.SCHEMA_VERSION
        for observation in self._items.get_items():
            model["items"][observation.name] = observation.to_dict(with_results=False)

        (root / self.MODEL_FILE).write_text(json.dumps(model, indent=4), encoding="utf-8")

        # Results belonging to observations the project no longer has. Left in place they are
        # not merely clutter: renaming an observation away and back would find the old results
        # still sitting there and treat them as current, which is how a stale number gets
        # reported as a fresh one.
        dropped = 0
        for directory in (root / self.RESULTS_DIRECTORY).iterdir():
            if directory.is_dir() and directory.name not in model["items"]:
                shutil.rmtree(directory)
                dropped += 1
        if dropped:
            logger.info("Dropped results for %s observation(s) no longer in the project", dropped)

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
                observation.calculated_data.attach(store, observation.name,
                                                   budget=project.residency_budget)
        logger.info("Loaded project '%s' from '%s', results not read", project.name, path)
        return project

    @property
    def residency_budget(self) -> ResidencyBudget:
        """How much memory this project's results may occupy in hand.

        Returns:
            ResidencyBudget: One budget shared by every observation, because the memory they
                compete for is one machine's, not one observation's.

        Notes:
            - Created on first use rather than in the constructor, so a project built by
              `from_dict` -- which every older saved file goes through -- has one too.
        """
        if getattr(self, "_residency_budget", None) is None:
            self._residency_budget = ResidencyBudget()
        return self._residency_budget

    def set_residency_share(self, share: float) -> None:
        """Set what share of available memory the results in hand may occupy.

        Args:
            share (float): Between 0 and 1, exclusive of 0.

        Raises:
            ValueError: If the share is outside that range. A budget of nothing would evict a
                result the instant it was read, and a budget above what is available is not a
                budget.
        """
        if not 0 < share <= 1:
            raise ValueError(f"Residency share must be above 0 and at most 1, got {share}")
        self.residency_budget.share = share
        logger.info("Results may occupy %.0f%% of available memory (%.1f GB just now)",
                    share * 100, self.residency_budget.limit / 1024 ** 3)

    @property
    def scratch(self) -> ScratchSpace:
        """Where this project's results are kept until it is saved.

        Returns:
            ScratchSpace: One per session, created on first use, so two windows never write
                into the same place.

        Notes:
            - A project that has been saved still calculates into its own directory rather than
              here; the scratch is what a project uses before it has one.
        """
        if getattr(self, "_scratch", None) is None:
            self._scratch = ScratchSpace()
            self._scratch.note_project(self.name)
        return self._scratch

    def attach_results_store(self, store: ResultStore) -> None:
        """Point every observation's results at a store.

        Args:
            store (ResultStore): Where results are written and read.
        """
        for observation in self._items.get_items():
            results = observation.calculated_data
            if hasattr(results, "attach"):
                results.attach(store, observation.name, budget=self.residency_budget)

    def hold_results_in_scratch(self) -> None:
        """Give results somewhere to live before the project has a directory of its own.

        Notes:
            - Called once the project is in place rather than in the constructor, because
              creating the scratch directory is what tells a later session that a session
              existed. A project that is opened and closed without calculating leaves nothing.
        """
        self.attach_results_store(self.scratch.store)

    @staticmethod
    def is_directory_project(path: str) -> bool:
        """Report whether a path is a project directory rather than a single file."""
        return (Path(path) / ScheduleProject.MODEL_FILE).is_file()

    @classmethod
    def open(cls, path: str) -> 'ScheduleProject':
        """Load a project from its directory.

        Args:
            path (str): The project directory, or the `project.json` inside it. Both are
                accepted because a file dialog can hand back either.

        Returns:
            ScheduleProject: The project, holding no results in memory until one is asked for.

        Raises:
            IOError: If the path is not a project directory.
        """
        check_non_empty_string(path, "Project path")
        candidate = Path(path)

        if candidate.name == cls.MODEL_FILE and candidate.is_file():
            return cls.from_directory(str(candidate.parent))
        return cls.from_directory(str(candidate))

    def save(self, path: str) -> None:
        """Save the project as a directory.

        Args:
            path (str): The project directory. Created if it does not exist.
        """
        check_non_empty_string(path, "Project path")
        self.to_directory(str(Path(path)))

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