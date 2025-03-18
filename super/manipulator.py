# super/manipulator.py
from abc import ABC
from base.observation import Project, Observation
from utils.validation import check_type, check_non_empty_string
from utils.logging_setup import logger
import json

class Manipulator(ABC):
    def __init__(self, project: Project = None):
        """Initialize Manipulator with an optional Project."""
        if project is not None:
            check_type(project, Project, "Project")
        self._project = project if project is not None else Project()
        logger.info(f"Initialized Manipulator with project '{self._project.get_project_name()}'")

    def create_project(self, project_name: str) -> None:
        """Create a new project with the given name."""
        check_non_empty_string(project_name, "Project name")
        self._project = Project(project_name=project_name)
        logger.info(f"Created new project '{project_name}'")

    def get_project(self) -> Project:
        """Get the current project."""
        return self._project

    def add_observation(self, observation: Observation) -> None:
        """Add an observation to the project."""
        check_type(observation, Observation, "Observation")
        self._project.get_observations().append(observation)
        logger.info(f"Added observation '{observation.get_observation_code()}' to project '{self._project.get_project_name()}'")

    def remove_observation(self, obs_code: str) -> None:
        """Remove an observation by its code."""
        check_non_empty_string(obs_code, "Observation code")
        obs_list = self._project.get_observations()
        for i, obs in enumerate(obs_list):
            if obs.get_observation_code() == obs_code:
                obs_list.pop(i)
                logger.info(f"Removed observation '{obs_code}' from project '{self._project.get_project_name()}'")
                return
        raise ValueError(f"No observation found with code '{obs_code}'")

    def get_observation(self, obs_code: str) -> Observation:
        """Get an observation by its code."""
        return self._project.get_observation(obs_code)

    def save_project(self, filename: str) -> None:
        """Save the project to a JSON file."""
        check_non_empty_string(filename, "Filename")
        self._project.save_project(filename)

    def load_project(self, filename: str) -> None:
        """Load a project from a JSON file."""
        check_non_empty_string(filename, "Filename")
        temp_project = Project()
        temp_project.load_project(filename)
        self._project = temp_project
        logger.info(f"Loaded project '{self._project.get_project_name()}' from '{filename}'")

    def clear_project(self) -> None:
        """Clear all observations from the project."""
        self._project.get_observations().clear()
        logger.info(f"Cleared all observations from project '{self._project.get_project_name()}'")