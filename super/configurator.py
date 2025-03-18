# super/configurator.py
from abc import ABC, abstractmethod
from base.observation import Observation, CatalogManager
from base.telescopes import Telescope, SpaceTelescope, Telescopes
from base.sources import Source, Sources
from base.frequencies import IF, Frequencies
from base.scans import Scan, Scans
from utils.validation import check_type, check_non_empty_string, check_positive
from utils.logging_setup import logger
from typing import Optional, List, Dict

class Configurator(ABC):
    def __init__(self, catalog_manager: CatalogManager):
        """Initialize Configurator with a CatalogManager."""
        check_type(catalog_manager, CatalogManager, "CatalogManager")
        self._catalog_manager = catalog_manager
        logger.info("Initialized Configurator with CatalogManager")

    @abstractmethod
    def configure_observation(self, observation: Observation) -> None:
        """Configure the observation (implemented in subclasses)."""
        pass

    def add_telescope(self, observation: Observation, telescope_code: str) -> None:
        """Add a telescope to the observation by code."""
        check_type(observation, Observation, "Observation")
        check_non_empty_string(telescope_code, "Telescope code")
        telescope = self._catalog_manager.get_telescope(telescope_code)
        if telescope is None:
            raise ValueError(f"Telescope '{telescope_code}' not found in catalog")
        observation.get_telescopes().add_telescope(telescope)
        logger.info(f"Added telescope '{telescope_code}' to observation '{observation.get_observation_code()}'")

    def remove_telescope(self, observation: Observation, index: int) -> None:
        """Remove a telescope from the observation by index."""
        check_type(observation, Observation, "Observation")
        observation.get_telescopes().remove_telescope(index)
        logger.info(f"Removed telescope at index {index} from observation '{observation.get_observation_code()}'")

    def add_source(self, observation: Observation, source_name: str) -> None:
        """Add a source to the observation by name."""
        check_type(observation, Observation, "Observation")
        check_non_empty_string(source_name, "Source name")
        source = self._catalog_manager.get_source(source_name)
        if source is None:
            raise ValueError(f"Source '{source_name}' not found in catalog")
        observation.get_sources().add_source(source)
        logger.info(f"Added source '{source_name}' to observation '{observation.get_observation_code()}'")

    def remove_source(self, observation: Observation, index: int) -> None:
        """Remove a source from the observation by index."""
        check_type(observation, Observation, "Observation")
        observation.get_sources().remove_source(index)
        logger.info(f"Removed source at index {index} from observation '{observation.get_observation_code()}'")

    def add_frequency(self, observation: Observation, freq: float, bandwidth: float, polarization: Optional[str] = None) -> None:
        """Add a frequency to the observation."""
        check_type(observation, Observation, "Observation")
        if_obj = IF(freq=freq, bandwidth=bandwidth, polarization=polarization)
        observation.get_frequencies().add_frequency(if_obj)
        logger.info(f"Added frequency {freq} MHz to observation '{observation.get_observation_code()}'")

    def remove_frequency(self, observation: Observation, index: int) -> None:
        """Remove a frequency from the observation by index."""
        check_type(observation, Observation, "Observation")
        observation.get_frequencies().remove_frequency(index)
        logger.info(f"Removed frequency at index {index} from observation '{observation.get_observation_code()}'")

    def add_scan(self, observation: Observation, start: float, duration: float, source_name: Optional[str] = None,
                 telescope_codes: List[str] = None, frequencies: List[IF] = None) -> None:
        """Add a scan to the observation."""
        check_type(observation, Observation, "Observation")
        check_positive(duration, "Duration")
        source = self._catalog_manager.get_source(source_name) if source_name else None
        telescopes = Telescopes()
        if telescope_codes:
            for code in telescope_codes:
                tel = self._catalog_manager.get_telescope(code)
                if tel is None:
                    raise ValueError(f"Telescope '{code}' not found in catalog")
                telescopes.add_telescope(tel)
        freqs = Frequencies(frequencies) if frequencies else observation.get_frequencies()
        scan = Scan(start=start, duration=duration, source=source, telescopes=telescopes, frequencies=freqs,
                    is_off_source=source is None)
        observation.get_scans().add_scan(scan)
        logger.info(f"Added scan with start={start} to observation '{observation.get_observation_code()}'")

    def remove_scan(self, observation: Observation, index: int) -> None:
        """Remove a scan from the observation by index."""
        check_type(observation, Observation, "Observation")
        observation.get_scans().remove_scan(index)
        logger.info(f"Removed scan at index {index} from observation '{observation.get_observation_code()}'")

    def set_observation_code(self, observation: Observation, code: str) -> None:
        """Set the observation code."""
        check_type(observation, Observation, "Observation")
        check_non_empty_string(code, "Observation code")
        observation.set_observation_code(code)
        logger.info(f"Set observation code to '{code}'")

class VLBIConfigurator(Configurator):
    def configure_observation(self, observation: Observation) -> None:
        """Configure a VLBI observation."""
        check_type(observation, Observation, "Observation")
        if observation.get_observation_type() != "VLBI":
            observation.set_observation(observation.get_observation_code(), observation_type="VLBI")
        if len(observation.get_telescopes().get_active_telescopes()) < 2:
            raise ValueError("VLBI observation requires at least 2 active telescopes")
        logger.info(f"Configured VLBI observation '{observation.get_observation_code()}'")

class SingleDishConfigurator(Configurator):
    def configure_observation(self, observation: Observation) -> None:
        """Configure a Single Dish observation."""
        check_type(observation, Observation, "Observation")
        if observation.get_observation_type() != "SINGLE_DISH":
            observation.set_observation(observation.get_observation_code(), observation_type="SINGLE_DISH")
        if len(observation.get_telescopes().get_active_telescopes()) != 1:
            raise ValueError("Single Dish observation requires exactly 1 active telescope")
        logger.info(f"Configured Single Dish observation '{observation.get_observation_code()}'")