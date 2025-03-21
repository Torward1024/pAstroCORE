from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from base.observation import Observation, CatalogManager
from base.sources import Source
from base.telescopes import Telescope, SpaceTelescope
from base.frequencies import IF
from super.configurator import Configurator
from super.calculator import Calculator
from super.vizualizator import Vizualizator
from super.optimizator import Optimizator
from utils.validation import check_type, check_non_empty_string
from utils.logging_setup import logger
from typing import Union
import os

class Project:
    """Container for managing multiple observations."""
    def __init__(self, name: str, observations: List[Observation] = None):
        self._name = name
        self._observations = observations if observations else []
        logger.info(f"Initialized Project '{name}' with {len(self._observations)} observations")

    def add_observation(self, observation: Observation) -> None:
        self._observations.append(observation)
        logger.info(f"Added observation '{observation.get_observation_code()}' to Project '{self._name}'")
    
    def insert_observation(self, observation: Observation, index: int) -> None:
        """Insert an observation at the specified index."""
        check_type(observation, Observation, "Observation")
        if not (0 <= index <= len(self._observations)):
            logger.error(f"Invalid index {index} for insertion in Project '{self._name}'")
            raise IndexError(f"Index {index} out of range for Project with {len(self._observations)} observations")
        self._observations.insert(index, observation)
        logger.info(f"Inserted observation '{observation.get_observation_code()}' at index {index} in Project '{self._name}'")

    def remove_observation(self, index: int) -> None:
        try:
            obs = self._observations.pop(index)
            logger.info(f"Removed observation '{obs.get_observation_code()}' from Project '{self._name}'")
        except IndexError:
            logger.error(f"Invalid observation index: {index}")
            raise IndexError("Invalid observation index!")

    def get_observations(self) -> List[Observation]:
        return self._observations

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self._name, "observations": [obs.to_dict() for obs in self._observations]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        return cls(name=data["name"], observations=[Observation.from_dict(obs) for obs in data["observations"]])

    def get_name(self) -> str:
        return self._name

    def set_name(self, name: str) -> None:
        check_non_empty_string(name, "Project name")
        self._name = name
        logger.info(f"Set project name to '{name}'")


class Manipulator(ABC):
    """Abstract base class for managing projects and coordinating super-classes."""
    def __init__(self, project: Optional[Project] = None):
        self._project = project if project else Project(name="DefaultProject")
        self._configurator = None
        self._calculator = None
        self._vizualizator = None
        self._optimizator = None
        self._catalog_manager = CatalogManager()  # Добавляем CatalogManager
        logger.info(f"Initialized Manipulator with project '{self._project.get_name()}'")

    def set_project(self, project: Project) -> None:
        check_type(project, Project, "Project")
        self._project = project
        logger.info(f"Set project '{project.get_name()}' for Manipulator")

    def add_observation(self, observation: Observation) -> None:
        check_type(observation, Observation, "Observation")
        self._project.add_observation(observation)
    
    def insert_observation(self, observation: Observation, index: int) -> None:
        """Insert an observation at the specified index in the project."""
        check_type(observation, Observation, "Observation")
        self._project.insert_observation(observation, index)

    def remove_observation(self, index: int) -> None:
        self._project.remove_observation(index)

    def set_configurator(self, configurator: 'Configurator') -> None:
        check_type(configurator, Configurator, "Configurator")
        self._configurator = configurator
        logger.info("Configurator set in Manipulator")

    def set_calculator(self, calculator: 'Calculator') -> None:
        check_type(calculator, Calculator, "Calculator")
        self._calculator = calculator
        logger.info("Calculator set in Manipulator")

    def set_vizualizator(self, vizualizator: 'Vizualizator') -> None:
        check_type(vizualizator, Vizualizator, "Vizualizator")
        self._vizualizator = vizualizator
        logger.info("Vizualizator set in Manipulator")

    def set_optimizator(self, optimizator: 'Optimizator') -> None:
        check_type(optimizator, Optimizator, "Optimizator")
        self._optimizator = optimizator
        logger.info("Optimizator set in Manipulator")

    def get_catalog_manager(self) -> CatalogManager:
        """Get the CatalogManager instance."""
        return self._catalog_manager

    def load_catalogs(self, sources_path: str, telescopes_path: str) -> None:
        """Load source and telescope catalogs."""
        if os.path.exists(sources_path):
            try:
                self._catalog_manager.load_source_catalog(sources_path)
                logger.info(f"Loaded sources catalog from '{sources_path}'")
            except (FileNotFoundError, ValueError) as e:
                logger.error(f"Failed to load sources catalog: {e}")
        else:
            logger.warning(f"Sources catalog file '{sources_path}' not found")
        if os.path.exists(telescopes_path):
            try:
                self._catalog_manager.load_telescope_catalog(telescopes_path)
                logger.info(f"Loaded telescopes catalog from '{telescopes_path}'")
            except (FileNotFoundError, ValueError) as e:
                logger.error(f"Failed to load telescopes catalog: {e}")
        else:
            logger.warning(f"Telescopes catalog file '{telescopes_path}' not found")

    @abstractmethod
    def execute(self) -> None:
        """Execute the task."""
        pass

    def save_project(self, filepath: str) -> None:
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self._project.to_dict(), f, indent=4)
        logger.info(f"Project saved to '{filepath}'")

    def load_project(self, filepath: str) -> None:
        import json
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._project = Project.from_dict(data)
            logger.info(f"Project loaded from '{filepath}'")
        except FileNotFoundError:
            logger.error(f"Project file '{filepath}' not found")
            raise FileNotFoundError(f"Project file '{filepath}' not found!")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from '{filepath}': {e}")
            raise ValueError(f"Invalid JSON in '{filepath}': {e}")

    def get_project_name(self) -> str:
        """Get the project name."""
        return self._project.get_name()
    
    def get_observations(self) -> List[Observation]:
        """Get the list of observations in the project."""
        return self._project.get_observations()
    
    def configure_observation_code(self, observation: Observation, code: str) -> None:
        """Set observation code via Configurator."""
        self._configurator.set_observation_code(observation, code)

    def configure_observation_type(self, observation: Observation, obs_type: str) -> None:
        """Set observation type via Configurator."""
        self._configurator.set_observation_type(observation, obs_type)

    def add_source_to_observation(self, observation: Observation, source: Source) -> None:
        """Add source to observation via Configurator."""
        self._configurator.add_source(observation, source)

    def remove_source_from_observation(self, observation: Observation, index: int) -> None:
        """Remove source from observation via Configurator."""
        self._configurator.remove_source(observation, index)

    def add_telescope_to_observation(self, observation: Observation, telescope: Union[Telescope, SpaceTelescope]) -> None:
        """Add telescope to observation via Configurator."""
        self._configurator.add_telescope(observation, telescope)

    def remove_telescope_from_observation(self, observation: Observation, index: int) -> None:
        """Remove telescope by index via Configurator."""
        self._configurator.remove_telescope(observation, index)
    
    def add_frequency_to_observation(self, observation: Observation, if_obj: IF) -> None:
        """Add frequency object to observation via Configurator."""
        self._configurator.add_frequency(observation, if_obj)

    def remove_frequency_from_observation(self, observation: Observation, index: int) -> None:
        """Remove frequency from observation via Configurator."""
        self._configurator.remove_frequency(observation, index)

class DefaultManipulator(Manipulator):
    """Default implementation of Manipulator."""
    def execute(self) -> None:
        """Execute the default task: configure, calculate, and visualize all observations."""
        if not self._project.get_observations():
            logger.warning("No observations to execute")
            return
        for obs in self._project.get_observations():
            if self._configurator:
                self._configurator.configure_observation(obs)
            if self._calculator:
                self._calculator.calculate_all(obs)
            if self._vizualizator:
                self._vizualizator.visualize_observation(obs)
        logger.info(f"Executed all tasks for project '{self._project.get_name()}'")