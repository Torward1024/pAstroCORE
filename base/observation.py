# base/observation.py
from base.base_entity import BaseEntity
from base.sources import Source, Sources
from base.telescopes import Telescope, SpaceTelescope, Telescopes
from base.frequencies import Frequencies
from base.scans import Scans
from utils.validation import check_type, check_non_empty_string
from utils.logging_setup import logger
from datetime import datetime
from typing import Optional, List, Dict, Any

class Observation(BaseEntity):
    def __init__(self, observation_code: str = "OBS_DEFAULT", sources: Sources = None,
                 telescopes: Telescopes = None, frequencies: Frequencies = None,
                 scans: Scans = None, observation_type: str = "VLBI", isactive: bool = True):
        """Initialize an Observation object."""
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
        self._calculated_data: Dict[str, Any] = {}  # Хранилище для результатов Calculator
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
        self._calculated_data.clear()  # Очищаем результаты при полной переустановке параметров
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
        self._calculated_data.clear()  # Очищаем результаты, так как данные изменились
        logger.info(f"Set sources for observation '{self._observation_code}'")

    def set_telescopes(self, telescopes: Telescopes) -> None:
        """Set observation telescopes."""
        check_type(telescopes, Telescopes, "Telescopes")
        self._telescopes = telescopes
        self._calculated_data.clear()  # Очищаем результаты, так как данные изменились
        logger.info(f"Set telescopes for observation '{self._observation_code}'")

    def set_frequencies(self, frequencies: Frequencies) -> None:
        """Set observation frequencies with polarizations."""
        check_type(frequencies, Frequencies, "Frequencies")
        self._frequencies = frequencies
        self._calculated_data.clear()  # Очищаем результаты, так как данные изменились
        logger.info(f"Set frequencies with polarizations for observation '{self._observation_code}'")

    def set_scans(self, scans: Scans) -> None:
        """Set observation scans."""
        check_type(scans, Scans, "Scans")
        self._scans = scans
        self._calculated_data.clear()  # Очищаем результаты, так как данные изменились
        logger.info(f"Set scans for observation '{self._observation_code}'")

    def set_calculated_data(self, key: str, data: Any) -> None:
        """Save calculated data for this observation."""
        check_non_empty_string(key, "Key")
        self._calculated_data[key] = data
        logger.info(f"Stored calculated data '{key}' for observation '{self._observation_code}'")

    def get_calculated_data(self, key: str) -> Any:
        """Retrieve calculated data by key."""
        check_non_empty_string(key, "Key")
        return self._calculated_data.get(key)

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
        """Validate the observation, including SEFD and polarizations."""
        active_scans = self._scans.get_active_scans()
        if not active_scans:
            logger.warning(f"Observation '{self._observation_code}' has no active scans")
            return False
        
        obs_freqs = {f.get_frequency() for f in self._frequencies.get_active_frequencies()}
        if not obs_freqs:
            logger.warning(f"Observation '{self._observation_code}' has no active frequencies")
            return False
        
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
        
        # Проверка источников
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
        
        # Проверка SEFD
        obs_freqs = {f.get_frequency() for f in self._frequencies.get_active_frequencies()}
        for tel in active_telescopes:
            for freq in obs_freqs:
                if tel.get_sefd(freq) is None:
                    logger.warning(f"Telescope '{tel.get_telescope_code()}' has no SEFD for frequency {freq} MHz")
                    return False
        
        # Проверка синхронизации частот и поляризаций
        for scan in active_scans:
            scan_freqs = {f.get_frequency(): f.get_polarization() for f in scan.get_frequencies().get_active_frequencies()}
            for freq, pol in scan_freqs.items():
                if freq not in obs_freqs:
                    logger.warning(f"Scan in '{self._observation_code}' uses frequency {freq} MHz not in observation frequencies")
                    return False
                obs_pol = next((f.get_polarization() for f in self._frequencies.get_active_frequencies() if f.get_frequency() == freq), None)
                if pol != obs_pol:
                    logger.warning(f"Scan in '{self._observation_code}' uses polarization {pol} for {freq} MHz, observation has {obs_pol}")
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
            "isactive": self.isactive,
            "calculated_data": self._calculated_data  # Добавляем результаты вычислений
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Observation':
        """Create an Observation object from a dictionary."""
        obs = cls(
            observation_code=data["observation_code"],
            sources=Sources.from_dict(data["sources"]),
            telescopes=Telescopes.from_dict(data["telescopes"]),
            frequencies=Frequencies.from_dict(data["frequencies"]),
            scans=Scans.from_dict(data["scans"]),
            observation_type=data["observation_type"],
            isactive=data["isactive"]
        )
        obs._calculated_data = data.get("calculated_data", {})  # Загружаем результаты вычислений
        logger.info(f"Created observation '{data['observation_code']}' from dictionary")
        return obs

    def __repr__(self) -> str:
        """Return a string representation of Observation."""
        return (f"Observation(code='{self._observation_code}', sources={self._sources}, "
                f"telescopes={self._telescopes}, frequencies={self._frequencies}, "
                f"scans={self._scans}, isactive={self.isactive}, "
                f"calculated_data={len(self._calculated_data)} items)")