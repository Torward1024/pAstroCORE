# super/configurator.py
from abc import ABC, abstractmethod
from base.observation import Observation
from base.sources import Sources
from base.telescopes import Telescopes
from base.frequencies import Frequencies, IF
from base.scans import Scan, Scans
from catalog_manager import CatalogManager
from utils.logging_setup import logger

class Configurator(ABC):
    def __init__(self, catalog_manager: CatalogManager):
        if not isinstance(catalog_manager, CatalogManager):
            logger.error("Invalid catalog_manager type provided")
            raise TypeError("catalog_manager must be a CatalogManager instance!")
        self.catalog_manager = catalog_manager
        logger.info("Initialized Configurator with CatalogManager")

    @abstractmethod
    def configure_observation(self, observation: Observation) -> None:
        pass

    def set_observation_code(self, observation: Observation, code: str) -> None:
        if not isinstance(observation, Observation):
            logger.error("Invalid observation type provided")
            raise TypeError("observation must be an Observation instance!")
        observation.set_obs_code(code)
        logger.info(f"Set observation code to '{code}'")

    def add_source(self, observation: Observation, source_name: str) -> None:
        if not isinstance(observation, Observation):
            logger.error("Invalid observation type provided")
            raise TypeError("observation must be an Observation instance!")
        source = self.catalog_manager.get_source(source_name)
        if source:
            observation.sources.add_source(source)
            logger.info(f"Added source '{source_name}' to observation '{observation.observation_code}'")
        else:
            logger.error(f"Source '{source_name}' not found in catalog")
            raise ValueError(f"Source '{source_name}' not found in catalog!")

    def add_telescope(self, observation: Observation, telescope_code: str) -> None:
        if not isinstance(observation, Observation):
            logger.error("Invalid observation type provided")
            raise TypeError("observation must be an Observation instance!")
        telescope = self.catalog_manager.get_telescope(telescope_code)
        if telescope:
            observation.telescopes.add_telescope(telescope)
            logger.info(f"Added telescope '{telescope_code}' to observation '{observation.observation_code}'")
        else:
            logger.error(f"Telescope '{telescope_code}' not found in catalog")
            raise ValueError(f"Telescope '{telescope_code}' not found in catalog!")

    def add_frequency(self, observation: Observation, freq: float, bandwidth: float) -> None:
        if not isinstance(observation, Observation):
            logger.error("Invalid observation type provided")
            raise TypeError("observation must be an Observation instance!")
        if_obj = IF(freq=freq, bandwidth=bandwidth)
        observation.frequencies.add_frequency(if_obj)
        logger.info(f"Added frequency {freq} MHz with bandwidth {bandwidth} MHz to observation '{observation.observation_code}'")

    def add_scan(self, observation: Observation, start: float, duration: float, source_name: str,
                 telescope_codes: list[str], freqs: list[tuple[float, float]]) -> None:
        if not isinstance(observation, Observation):
            logger.error("Invalid observation type provided")
            raise TypeError("observation must be an Observation instance!")
        
        source = self.catalog_manager.get_source(source_name)
        if not source:
            logger.error(f"Source '{source_name}' not found in catalog")
            raise ValueError(f"Source '{source_name}' not found in catalog!")
        
        telescopes = Telescopes()
        for code in telescope_codes:
            telescope = self.catalog_manager.get_telescope(code)
            if telescope:
                telescopes.add_telescope(telescope)
            else:
                logger.error(f"Telescope '{code}' not found in catalog")
                raise ValueError(f"Telescope '{code}' not found in catalog!")
        
        frequencies = Frequencies()
        for freq, bw in freqs:
            frequencies.add_frequency(IF(freq=freq, bandwidth=bw))
        
        scan = Scan(start=start, duration=duration, source=source, telescopes=telescopes, frequencies=frequencies)
        observation.scans.add_scan(scan)
        logger.info(f"Added scan (start={start}, duration={duration}) to observation '{observation.observation_code}'")