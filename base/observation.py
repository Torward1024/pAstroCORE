# base/observation.py
from base.base_entity import BaseEntity
from base.sources import Sources
from base.telescopes import Telescopes
from base.frequencies import Frequencies
from base.scans import Scans
from utils.validation import check_type
from utils.logging_setup import logger
from datetime import datetime
import json
from typing import Optional

class Observation(BaseEntity):
    def __init__(self, observation_code: str = "OBS_DEFAULT", sources: Sources = None,
                 telescopes: Telescopes = None, frequencies: Frequencies = None,
                 scans: Scans = None, observation_type: str = "VLBI", isactive: bool = True):
        """Initialize an Observation object.

        Args:
            observation_code (str): Unique observation identifier.
            sources (Sources, optional): Sources for observation.
            telescopes (Telescopes, optional): Telescopes for observation.
            frequencies (Frequencies, optional): Frequencies for observation.
            scans (Scans, optional): Scans for observation.
            observation_type (str): Type of observation ("VLBI" or "SINGLE_DISH", default: "VLBI").
            isactive (bool): Whether the observation is active (default: True).
        """
        super().__init__(isactive)
        check_type(observation_code, str, "Observation code")
        if observation_type not in ("VLBI", "SINGLE_DISH"):
            logger.error(f"Observation type must be 'VLBI' or 'SINGLE_DISH', got {observation_type}")
            raise ValueError(f"Observation type must be 'VLBI' or 'SINGLE_DISH', got {observation_type}")
        if sources is not None:
            check_type(sources, Sources, "Sources")
        if telescopes is not None:
            check_type(telescopes, Telescopes, "Telescopes")
        if frequencies is not None:
            check_type(frequencies, Frequencies, "Frequencies")
        if scans is not None:
            check_type(scans, Scans, "Scans")
        self._observation_code = observation_code
        self._observation_type = observation_type
        self._sources = sources if sources is not None else Sources()
        self._telescopes = telescopes if telescopes is not None else Telescopes()
        self._frequencies = frequencies if frequencies is not None else Frequencies()
        self._scans = scans if scans is not None else Scans()
        logger.info(f"Initialized Observation '{observation_code}' with type '{observation_type}'")

    def set_observation(self, observation_code: str, sources: Sources = None,
                        telescopes: Telescopes = None, frequencies: Frequencies = None,
                        scans: Scans = None, observation_type: str = "VLBI", isactive: bool = True) -> None:
        """Set observation parameters."""
        check_type(observation_code, str, "Observation code")
        if observation_type not in ("VLBI", "SINGLE_DISH"):
            logger.error(f"Observation type must be 'VLBI' or 'SINGLE_DISH', got {observation_type}")
            raise ValueError(f"Observation type must be 'VLBI' or 'SINGLE_DISH', got {observation_type}")
        if sources is not None:
            check_type(sources, Sources, "Sources")
        if telescopes is not None:
            check_type(telescopes, Telescopes, "Telescopes")
        if frequencies is not None:
            check_type(frequencies, Frequencies, "Frequencies")
        if scans is not None:
            check_type(scans, Scans, "Scans")
        self._observation_code = observation_code
        self._observation_type = observation_type
        self._sources = sources if sources is not None else Sources()
        self._telescopes = telescopes if telescopes is not None else Telescopes()
        self._frequencies = frequencies if frequencies is not None else Frequencies()
        self._scans = scans if scans is not None else Scans()
        self.isactive = isactive
        logger.info(f"Set observation '{observation_code}' with type '{observation_type}'")

    def set_observation_code(self, observation_code: str) -> None:
        """Set observation code."""
        check_type(observation_code, str, "Observation code")
        self._observation_code = observation_code
        logger.info(f"Set observation code to '{observation_code}'")

    def set_sources(self, sources: Sources) -> None:
        """Set observation sources."""
        check_type(sources, Sources, "Sources")
        self._sources = sources
        logger.info(f"Set sources for observation '{self._observation_code}'")

    def set_telescopes(self, telescopes: Telescopes) -> None:
        """Set observation telescopes."""
        check_type(telescopes, Telescopes, "Telescopes")
        self._telescopes = telescopes
        logger.info(f"Set telescopes for observation '{self._observation_code}'")

    def set_frequencies(self, frequencies: Frequencies) -> None:
        """Set observation frequencies."""
        check_type(frequencies, Frequencies, "Frequencies")
        self._frequencies = frequencies
        logger.info(f"Set frequencies for observation '{self._observation_code}'")

    def set_scans(self, scans: Scans) -> None:
        """Set observation scans."""
        check_type(scans, Scans, "Scans")
        self._scans = scans
        logger.info(f"Set scans for observation '{self._observation_code}'")

    def get_observation_code(self) -> str:
        """Get observation code."""
        return self._observation_code
    
    def get_observation_type(self) -> str:
        """Get observation type."""
        return self._observation_type

    def get_sources(self) -> Sources:
        """Get observation sources."""
        return self._sources

    def get_telescopes(self) -> Telescopes:
        """Get observation telescopes."""
        return self._telescopes

    def get_frequencies(self) -> Frequencies:
        """Get observation frequencies."""
        return self._frequencies

    def get_scans(self) -> Scans:
        """Get observation scans."""
        return self._scans

    def get_start_datetime(self) -> Optional[datetime]:
        """Get observation start time as a datetime object (UTC), based on earliest scan."""
        active_scans = self._scans.get_active_scans()
        if not active_scans:
            return None
        return min(scan.get_start_datetime() for scan in active_scans)

    def validate(self) -> bool:
        """Validate the observation.

        Returns:
            bool: True if the observation is valid, False otherwise.
        """
        # Проверка наличия хотя бы одного активного скана
        active_scans = self._scans.get_active_scans()
        if not active_scans:
            logger.warning(f"Observation '{self._observation_code}' has no active scans")
            return False
        
        # Проверка наличия активных телескопов в зависимости от типа наблюдения
        active_telescopes = self._telescopes.get_active_telescopes()
        if not active_telescopes:
            logger.warning(f"Observation '{self._observation_code}' has no active telescopes")
            return False
        if self._observation_type == "VLBI" and len(active_telescopes) < 2:
            logger.warning(f"VLBI observation '{self._observation_code}' requires at least 2 active telescopes, got {len(active_telescopes)}")
            return False
        elif self._observation_type == "SINGLE_DISH" and len(active_telescopes) != 1:
            logger.warning(f"SINGLE_DISH observation '{self._observation_code}' requires exactly 1 active telescope, got {len(active_telescopes)}")
            return False
        
        # Проверка источников (для OFF SOURCE допустимо отсутствие активных источников в некоторых случаях)
        active_sources = {s.get_name() for s in self._sources.get_active_sources()}
        for scan in active_scans:
            if not scan.is_off_source and scan.get_source().get_name() not in active_sources:
                logger.warning(f"Scan in '{self._observation_code}' uses source '{scan.get_source().get_name()}' not in observation sources")
                return False
            scan_telescopes = {t.get_telescope_code() for t in scan.get_telescopes().get_active_telescopes()}
            active_telescope_codes = {t.get_telescope_code() for t in active_telescopes}
            if not scan_telescopes.issubset(active_telescope_codes):
                logger.warning(f"Scan in '{self._observation_code}' uses telescopes not in observation telescopes")
                return False
        
        logger.info(f"Observation '{self._observation_code}' validated successfully")
        return True

    def activate(self) -> None:
        """Activate observation."""
        super().activate()

    def deactivate(self) -> None:
        """Deactivate observation."""
        super().deactivate()

    def to_dict(self) -> dict:
        """Convert Observation object to a dictionary for serialization."""
        logger.info(f"Converted observation '{self._observation_code}' to dictionary")
        return {
            "observation_code": self._observation_code,
            "observation_type": self._observation_type,
            "sources": self._sources.to_dict(),
            "telescopes": self._telescopes.to_dict(),
            "frequencies": self._frequencies.to_dict(),
            "scans": self._scans.to_dict(),
            "isactive": self.isactive
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Observation':
        """Create an Observation object from a dictionary."""
        logger.info(f"Created observation '{data['observation_code']}' from dictionary")
        return cls(
            observation_code=data["observation_code"],
            sources=Sources.from_dict(data["sources"]),
            telescopes=Telescopes.from_dict(data["telescopes"]),
            frequencies=Frequencies.from_dict(data["frequencies"]),
            scans=Scans.from_dict(data["scans"]),
            observation_type=data["observation_type"],
            isactive=data["isactive"]
        )

    def __repr__(self) -> str:
        """Return a string representation of Observation."""
        return (f"Observation(code='{self._observation_code}', sources={self._sources}, "
                f"telescopes={self._telescopes}, frequencies={self._frequencies}, "
                f"scans={self._scans}, isactive={self.isactive})")

class Project(BaseEntity):
    def __init__(self, project_name: str = "PROJECT_DEFAULT", observations: list[Observation] = None):
        """Initialize a Project object.

        Args:
            project_name (str): Project name.
            observations (list[Observation], optional): List of observations.
        """
        super().__init__()
        check_type(project_name, str, "Project name")
        if observations is not None:
            check_type(observations, (list, tuple), "Observations")
            for obs in observations:
                check_type(obs, Observation, "Observation")
        self._project_name = project_name
        self._observations = observations if observations is not None else []
        logger.info(f"Initialized Project '{project_name}' with {len(self._observations)} observations")

    def set_project_name(self, project_name: str) -> None:
        """Set project name."""
        check_type(project_name, str, "Project name")
        self._project_name = project_name
        logger.info(f"Set project name to '{project_name}'")

    def get_project_name(self) -> str:
        """Get project name."""
        return self._project_name

    def get_observations(self) -> list[Observation]:
        """Get all observations."""
        return self._observations

    def get_observation(self, obs_code: str) -> Observation:
        """Get observation by code."""
        for obs in self._observations:
            if obs.get_observation_code() == obs_code:
                return obs
        logger.error(f"No observation found with code '{obs_code}'")
        raise ValueError(f"No observation found with code '{obs_code}'")

    def save_project(self, filename: str) -> None:
        """Save project to a JSON file."""
        check_type(filename, str, "Filename")
        try:
            project_dict = {
                "project_name": self._project_name,
                "observations": [obs.to_dict() for obs in self._observations]
            }
            with open(filename, 'w') as f:
                json.dump(project_dict, f, indent=4)
            logger.info(f"Saved project '{self._project_name}' to '{filename}'")
        except TypeError as e:
            logger.error(f"Serialization error while saving project '{self._project_name}': {str(e)}")
            raise TypeError(f"Failed to serialize project: {str(e)}")
        except IOError as e:
            logger.error(f"IO error while saving project '{self._project_name}' to '{filename}': {str(e)}")
            raise IOError(f"Failed to save project to '{filename}': {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error while saving project '{self._project_name}': {str(e)}")
            raise Exception(f"Unexpected error: {str(e)}")

    def load_project(self, filename: str) -> None:
        """Load project from a JSON file."""
        check_type(filename, str, "Filename")
        try:
            with open(filename, 'r') as f:
                project_dict = json.load(f)
            self._project_name = project_dict["project_name"]
            self._observations = [Observation.from_dict(obs_dict) for obs_dict in project_dict["observations"]]
            logger.info(f"Loaded project '{self._project_name}' from '{filename}' with {len(self._observations)} observations")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error while loading project from '{filename}': {str(e)}")
            raise ValueError(f"Invalid JSON format in '{filename}': {str(e)}")
        except IOError as e:
            logger.error(f"IO error while loading project from '{filename}': {str(e)}")
            raise IOError(f"Failed to load project from '{filename}': {str(e)}")
        except KeyError as e:
            logger.error(f"Missing key in project data from '{filename}': {str(e)}")
            raise ValueError(f"Invalid project data in '{filename}': missing {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error while loading project from '{filename}': {str(e)}")
            raise Exception(f"Unexpected error: {str(e)}")

    def to_dict(self) -> dict:
        """Convert Project object to a dictionary for serialization."""
        logger.info(f"Converted project '{self._project_name}' to dictionary")
        return {
            "project_name": self._project_name,
            "observations": [obs.to_dict() for obs in self._observations]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Project':
        """Create a Project object from a dictionary."""
        logger.info(f"Created project '{data['project_name']}' from dictionary")
        return cls(
            project_name=data["project_name"],
            observations=[Observation.from_dict(obs_data) for obs_data in data["observations"]]
        )

    def __len__(self) -> int:
        """Return the number of observations."""
        return len(self._observations)

    def __repr__(self) -> str:
        """Return a string representation of Project."""
        return f"Project(name='{self._project_name}', observations={len(self._observations)})"