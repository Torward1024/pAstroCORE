# unit_scheduling/super/schedule_project.py
from typing import Dict, Any, List, Optional, Union
from pastrocore.base.observation import Observation
from pastrocore.base import freshness
from pastrocore.base.result_store import ResidencyBudget, ResultStore, json_safe
from pastrocore.base.scratch import ScratchSpace
from msb_arch import InvariantError, invariant
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

    # `SCHEMA_VERSION` and `migrate` are the base class's, and were reimplemented here to
    # forward to it. Raise the version when the shape of what `to_dict` writes changes -- a
    # renamed field, a field that means something new -- and override `migrate` to read the
    # older shape. Version 1 is the only version there has been, and it is written into the
    # file only once it is no longer 1, so nothing changes until it has to.
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
            for obs in items.values():
                check_type(obs, Observation, "Observation in items")

        super().__init__(name, items or {})
        logger.debug("Initialized ScheduleProject '%s' with %s observations", name, len(self._items))

    @invariant("two observations must not share an observation code")
    def _codes_are_unique(self) -> bool:
        """No two observations in a project may carry the same code.

        Raises:
            InvariantError: Naming the code and both observations that carry it.

        Notes:
            - A rule about the project rather than about any one observation, which is what an
              invariant is for. It was a `_validate_item` helper called by hand from four
              places, each passing a different pair of exclusions to work out which item was
              being replaced -- and `remove_item` and `set_project` could still leave a project
              nobody had checked. msb_arch 1.10.0 checks the rule after anything that changes
              what a project holds, and puts the items back when it refuses, so the exclusions
              are not needed: the rule reads the project as it would be.
            - The code, not the name. Names are unique because the container makes them so; the
              code is what an observation is called on paper, and duplicating one makes two
              observations indistinguishable everywhere a schedule is written out.
        """
        seen = {}
        for name, observation in self._items.get_all().items():
            code = observation.get_observation_code()
            if code in seen:
                raise InvariantError(
                    f"observations '{seen[code]}' and '{name}' both carry the code '{code}'")
            seen[code] = name
        return True

    def add_item(self, item: Observation) -> None:
        """Add an observation to the project.

        Args:
            item (Observation): The Observation object to add.

        Raises:
            TypeError: If the item is not an Observation object.
            InvariantError: If the observation code is not unique.
        """
        check_type(item, Observation, "Observation")
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
            InvariantError: If the observation code is not unique.
        """
        check_type(item, Observation, "Observation")
        super().set_item(name, item)
        logger.info("Set observation with name='%s' and code='%s' in project '%s'", name, item.get_observation_code(), self.name)

    def unsaved_results(self) -> int:
        """Return how many results live in this session's scratch rather than in the project.

        Returns:
            int: The count. Zero for a project that has been saved since its last calculation,
                and for one that has calculated nothing.

        Notes:
            - Results are written to a scratch directory the moment they are calculated and
              live there until the project is saved, so "in the scratch" means "not in the
              project". A window that closes without asking about these destroys them, which is
              what writing them through to disk exists to prevent.
            - Here rather than in the window: a command line closing a session and a server
              ending one ask the same question, and neither should be counting files.
        """
        try:
            scratch = self.scratch.path
            if scratch is None or not scratch.exists():
                return 0
            return len(list((scratch / ScratchSpace.RESULTS).rglob("*.parquet")))
        except Exception as e:                          # noqa: BLE001 - never block a close
            logger.error("Could not tell what this session still holds: %s", str(e),
                         exc_info=True)
            return 0

    def discard_scratch_if_empty(self) -> bool:
        """Remove this session's scratch directory when nothing in it would be lost.

        Returns:
            bool: Whether it was removed.

        Notes:
            - A project that is replaced -- by opening another, or by starting a new one --
              took its scratch with it and nothing discarded it, so every open and every new
              project left a directory that the next start offered to recover from a session
              that had ended normally with nothing in it.
            - One holding results is left where it is. That offer is the whole reason the
              directory survives a crash: litter is worth clearing, a day of calculation is not.
        """
        if self.unsaved_results():
            logger.info("Leaving '%s' behind: it holds results nobody has saved",
                        self.scratch.path)
            return False
        try:
            self.scratch.discard()
            return True
        except Exception as e:                          # noqa: BLE001 - never block a switch
            logger.error("Could not tidy up this session's scratch: %s", str(e),
                         exc_info=True)
            return False

    def observations(self) -> List[Observation]:
        """Return the observations this project holds, as a list.

        Returns:
            List[Observation]: The observations themselves, never their names.

        Notes:
            - `get_items()` was a dictionary on a project and a list on a container -- the same
              method name in two shapes -- so every caller guessed which it had. One guessed
              wrong for eight calculations: iterating a project yielded its *keys*, so
              `o.get_scans()` was called on a string, and the broad handler downstream turned
              that into an empty frame. Calculating for a whole project produced nothing and
              said nothing.
            - msb_arch 2.0.0 settled the shape -- a project answers with a list, exactly as a
              container does, and `get_all()` is the mapping. This stays because it says
              *observations* rather than items, which is what every caller here wants, and
              because a request may name it: `inspect(project, observations=None)`.
        """
        return list(self.get_items())

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
            InvariantError: If any two observations share a code.
        """
        if items:
            for obs in items.values():
                check_type(obs, Observation, "Observation in items")
        super().set_project(name, items)
        logger.info("Set project '%s' with %s observations", name, len(items))

    # `to_dict` is the base class's. The override here wrote the same two keys by hand, which
    # msb_arch 2.0.0 made pure duplication when `Project` became a `Serializable`: the
    # inherited one writes the schema version when there is one, and caches.

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

        # allow_nan=False so an unrepresentable number fails here, loudly, rather than
        # producing a file only a lenient parser can read.
        (root / self.MODEL_FILE).write_text(
            json.dumps(json_safe(model), indent=4, allow_nan=False), encoding="utf-8")

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
        # Results calculated before fingerprints existed carry none, and answering "unknown"
        # about them forever is honest and useless -- the user changes a scan, nothing is
        # reported, and staleness never once fires for a project that already exists. Record
        # what the configuration is now, so that changes from here on are visible. Metadata
        # only: no result is read.
        for observation in project._items.get_items():
            freshness.adopt_baseline(observation)

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

    def release(self) -> int:
        """Let go of everything this project holds, so it can be replaced.

        Returns:
            int: How many observations were released.

        Notes:
            - A window closing a project, a command line opening the next one and a server
              ending a session all want this, so it is here rather than in any of them. It was
              in the window, which is why the window reached into the model to do it.
            - The back references go before the observations do. An observation still pointing
              at the project, the orchestrator or its parent keeps all three alive, and the
              next project then shares a graph with the one that was closed.
        """
        released = 0
        for observation in self.observations():
            if hasattr(observation, "cleanup"):
                try:
                    observation.cleanup()
                except Exception as e:                  # noqa: BLE001 - one failure frees the rest
                    logger.debug("Could not clean up '%s': %s", observation.name, str(e))
            for reference in ("_project", "_manipulator", "_parent"):
                if hasattr(observation, reference):
                    setattr(observation, reference, None)
            released += 1

        self.remove_all()
        logger.info("Released project '%s' and the %s observation(s) it held", self.name, released)
        return released

    def remove_all(self) -> None:
        """Remove every observation, releasing the results each was holding first.

        Notes:
            - This was called `clear`, which msb_arch 1.9.0 deprecated and 2.0.0 removed: one
              name meant three different jobs depending on what it was called on. The name is
              now the one the framework uses, and it does the same work.
            - The results are released before the observations go, because an observation that
              has already left the project cannot be asked to let go of anything.
        """
        for observation in self.observations():
            try:
                observation.clear_calculated_data()
            except Exception as e:                      # noqa: BLE001 - one bad result frees the rest
                logger.debug("Could not release the results of '%s': %s",
                             observation.get_observation_code(), str(e))
        super().remove_all()
        logger.info("Removed every observation from project '%s'", self.name)

    def __repr__(self) -> str:
        """String representation of ScheduleProject.

        Returns:
            str: A string in the format "ScheduleProject(name='{name}', observations_count={count})".
        """
        return f"ScheduleProject(name='{self.name}', observations_count={len(self._items)})"