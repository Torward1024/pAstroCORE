# super/configurator.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from base.observation import Observation, CatalogManager
from base.sources import Source, Sources
from base.telescopes import Telescope, SpaceTelescope, Telescopes
from base.frequencies import IF, Frequencies
from base.scans import Scan, Scans
from utils.validation import check_type, check_non_empty_string
from utils.logging_setup import logger


class Configurator(ABC):
    """Abstract base class for configuring observations."""
    def __init__(self, catalog_manager: Optional[CatalogManager] = None):
        self._catalog_manager = catalog_manager if catalog_manager else CatalogManager()
        logger.info("Initialized Configurator")

    @abstractmethod
    def configure_observation(self, observation: Observation) -> None:
        """Configure the observation."""
        pass

    def load_catalogs(self, source_file: Optional[str] = None, telescope_file: Optional[str] = None) -> None:
        """Load source and telescope catalogs."""
        if source_file:
            self._catalog_manager.load_source_catalog(source_file)
        if telescope_file:
            self._catalog_manager.load_telescope_catalog(telescope_file)

    def add_source(self, observation: Observation, source: Source) -> None:
        """Add a source to the observation."""
        check_type(observation, Observation, "Observation")
        check_type(source, Source, "Source")
        observation.get_sources().add_source(source)
        logger.info(f"Added source '{source.get_name()}' to observation '{observation.get_observation_code()}'")

    def add_telescope(self, observation: Observation, telescope: Telescope | SpaceTelescope) -> None:
        """Add a telescope to the observation."""
        check_type(observation, Observation, "Observation")
        check_type(telescope, (Telescope, SpaceTelescope), "Telescope")
        observation.get_telescopes().add_telescope(telescope)
        logger.info(f"Added telescope '{telescope.get_telescope_code()}' to observation '{observation.get_observation_code()}'")

    def add_frequency(self, observation: Observation, freq: float, bandwidth: float, polarization: Optional[str] = None) -> None:
        """Add a frequency to the observation."""
        check_type(observation, Observation, "Observation")
        if_obj = IF(freq=freq, bandwidth=bandwidth, polarization=polarization)
        observation.get_frequencies().add_frequency(if_obj)
        logger.info(f"Added frequency {freq} MHz to observation '{observation.get_observation_code()}'")

    def add_scan(self, observation: Observation, start: float, duration: float, source: Optional[Source] = None,
                 telescopes: Optional[Telescopes] = None, frequencies: Optional[Frequencies] = None,
                 is_off_source: bool = False) -> None:
        """Add a scan to the observation."""
        check_type(observation, Observation, "Observation")
        scan = Scan(start=start, duration=duration, source=source, telescopes=telescopes,
                    frequencies=frequencies, is_off_source=is_off_source)
        observation.get_scans().add_scan(scan)
        logger.info(f"Added scan with start={start} to observation '{observation.get_observation_code()}'")

    def bulk_configure(self, observation: Observation, sources: List[Source], telescopes: List[Telescope | SpaceTelescope],
                       frequencies: List[Tuple[float, float]], scans: List[Tuple[float, float]]) -> None:
        """Configure observation with multiple sources, telescopes, frequencies, and scans."""
        for src in sources:
            self.add_source(observation, src)
        for tel in telescopes:
            self.add_telescope(observation, tel)
        for freq, bw in frequencies:
            self.add_frequency(observation, freq, bw)
        for start, duration in scans:
            self.add_scan(observation, start, duration, source=observation.get_sources().get_active_sources()[0],
                          telescopes=observation.get_telescopes(), frequencies=observation.get_frequencies())


class DefaultConfigurator(Configurator):
    """Default implementation of Configurator."""
    def configure_observation(self, observation: Observation) -> None:
        """Basic observation configuration."""
        check_type(observation, Observation, "Observation")
        if not observation.validate():
            logger.warning(f"Observation '{observation.get_observation_code()}' validation failed during configuration")
        logger.info(f"Configured observation '{observation.get_observation_code()}'")