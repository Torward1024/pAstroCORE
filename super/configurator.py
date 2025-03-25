# super/configurator.py
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, Union
from base.observation import Observation
from utils.catalogmanager import CatalogManager
from base.sources import Source
from base.telescopes import Telescope, SpaceTelescope
from base.frequencies import IF
from base.scans import Scan
from utils.validation import check_type, check_non_empty_string, check_positive
from utils.logging_setup import logger

class Configurator(ABC):
    """Abstract base class for configuring observations"""
    def __init__(self, catalog_manager: Optional[CatalogManager] = None):
        self._catalog_manager = catalog_manager if catalog_manager else CatalogManager()
        logger.info("Initialized Configurator")

    @abstractmethod
    def configure_observation(self, observation: Observation) -> None:
        """Configure the observation"""
        pass

    def load_catalogs(self, source_file: Optional[str] = None, telescope_file: Optional[str] = None) -> None:
        """Load source and telescope catalogs"""
        if source_file:
            self._catalog_manager.load_source_catalog(source_file)
        if telescope_file:
            self._catalog_manager.load_telescope_catalog(telescope_file)

    def add_source(self, observation: Observation, source: Source) -> None:
        """Add a source to the observation"""
        check_type(observation, Observation, "Observation")
        check_type(source, Source, "Source")
        observation.get_sources().add_source(source)
    
    def insert_source(self, observation: Observation, source: Source, index: int) -> None:
        """Insert a source into the observation at the specified index"""
        check_type(observation, Observation, "Observation")
        check_type(source, Source, "Source")
        check_type(index, int, "Index")
        observation.get_sources().insert_source(source, index)
    
    def remove_source(self, observation: Observation, index: int) -> None:
        """Remove a source from the observation by index"""
        check_type(observation, Observation, "Observation")
        check_type(index, int, "Index")
        observation.get_sources().remove_source(index)

    def add_telescope(self, observation: Observation, telescope: Union[Telescope, SpaceTelescope]) -> None:
        """Add a telescope to the observation"""
        check_type(observation, Observation, "Observation")
        check_type(telescope, (Telescope, SpaceTelescope), "Telescope")
        observation.get_telescopes().add_telescope(telescope)
    
    def insert_telescope(self, observation: Observation, telescope: Union[Telescope, SpaceTelescope], index: int) -> None:
        """Insert a telescope into the observation at the specified index"""
        check_type(observation, Observation, "Observation")
        check_type(telescope, (Telescope, SpaceTelescope), "Telescope")
        check_type(index, int, "Index")
        observation.get_telescopes().insert_telescope(telescope, index)

    def remove_telescope(self, observation: Observation, index: int) -> None:
        """Remove a telescope from the observation by index"""
        check_type(observation, Observation, "Observation")
        check_type(index, int, "Index")
        observation.get_telescopes().remove_telescope(index)

    def add_frequency(self, observation: Observation, if_obj: IF) -> None:
        """Add a frequency object to the observation"""
        check_type(observation, Observation, "Observation")
        check_type(if_obj, IF, "IF")
        observation.get_frequencies().add_IF(if_obj)
    
    def insert_frequency(self, observation: Observation, if_obj: IF, index: int) -> None:
        """Insert a frequency into the observation at the specified index"""
        check_type(observation, Observation, "Observation")
        check_type(if_obj, IF, "IF")
        check_type(index, int, "Index")
        observation.get_frequencies().insert_IF(if_obj, index)

    def remove_frequency(self, observation: Observation, index: int) -> None:
        """Remove a frequency from the observation by index"""
        check_type(observation, Observation, "Observation")
        check_type(index, int, "Index")
        observation.get_frequencies().remove_frequency(index)  

    def add_scan(self, observation: Observation, scan: Scan) -> None:
        """Add a scan to the observation"""
        check_type(observation, Observation, "Observation")
        check_type(scan, Scan, "Scan")
        observation.get_scans().add_scan(scan)
        logger.info(f"Added scan with start={scan.get_start()} to observation '{observation.get_observation_code()}'")

    def insert_scan(self, observation: Observation, scan: Scan, index: int) -> None:
        """Insert a scan to the observation"""
        check_type(observation, Observation, "Observation")
        check_type(scan, Scan, "Scan")
        observation.get_scans().insert_scan(scan, index)
        logger.info(f"Added scan with start={scan.get_start()} to observation '{observation.get_observation_code()}'")          

    def remove_scan(self, observation: Observation, index: int) -> None:
        """Remove a scan from the observation by index"""
        check_type(observation, Observation, "Observation")
        check_type(index, int, "Index")
        scans = observation.get_scans()
        try:
            scan = scans.get_scan(index)
            scans.remove_scan(index)
            logger.info(f"Removed scan with start={scan.get_start()} from observation '{observation.get_observation_code()}'")
        except IndexError:
            logger.warning(f"Scan at index {index} not found in observation '{observation.get_observation_code()}'") 

    def get_sources(self, observation: Observation) -> List[Source]:
        """Get the list of active sources"""
        check_type(observation, Observation, "Observation")
        return observation.get_sources().get_sources()

    def get_telescopes(self, observation: Observation) -> List[Union[Telescope, SpaceTelescope]]:
        """Get the list of active telescopes"""
        check_type(observation, Observation, "Observation")
        return observation.get_telescopes().get_telescopes()

    def get_frequencies(self, observation: Observation) -> List[IF]:
        """Get the list of active frequencies"""
        check_type(observation, Observation, "Observation")
        return observation.get_frequencies().get_frequencies()

    def get_scans(self, observation: Observation) -> List[Scan]:
        """Get the list of active scans"""
        check_type(observation, Observation, "Observation")
        return observation.get_scans().get_scans()
    
    def get_observation_code(self, observation: Observation) -> str:
        """Get the observation code"""
        check_type(observation, Observation, "Observation")
        return observation.get_observation_code()

    def get_observation_type(self, observation: Observation) -> str:
        """Get the observation type"""
        check_type(observation, Observation, "Observation")
        return observation.get_observation_type()
    
    def set_observation_code(self, observation: Observation, code: str) -> None:
        """Set the observation code"""
        check_type(observation, Observation, "Observation")
        check_non_empty_string(code, "Observation code")
        observation._observation_code = code
        logger.info(f"Set observation code to '{code}'")

    def set_observation_type(self, observation: Observation, obs_type: str) -> None:
        """Set the observation type"""
        check_type(observation, Observation, "Observation")
        check_non_empty_string(obs_type, "Observation type")
        if obs_type not in ["VLBI", "SINGLE_DISH"]:
            logger.error(f"Invalid observation type: {obs_type}. Must be 'VLBI' or 'SINGLE_DISH'")
            raise ValueError("Observation type must be 'VLBI' or 'SINGLE_DISH'")
        observation._observation_type = obs_type
        logger.info(f"Set observation type to '{obs_type}'")

class DefaultConfigurator(Configurator):
    """Default implementation of Configurator"""
    def configure_observation(self, observation: Observation) -> None:
        """Basic observation configuration."""
        check_type(observation, Observation, "Observation")
        if not observation.validate():
            logger.warning(f"Observation '{observation.get_observation_code()}' validation failed during configuration")
        logger.info(f"Configured observation '{observation.get_observation_code()}'")