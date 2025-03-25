# base/observation.py
from base.base_entity import BaseEntity
from base.sources import Source, Sources
from base.telescopes import Telescope, SpaceTelescope, Telescopes
from base.frequencies import Frequencies, IF
from base.scans import Scans
from utils.validation import check_type, check_non_empty_string
from utils.logging_setup import logger
from datetime import datetime
from typing import Optional, Dict, Any, Union
import astropy.units as u
import numpy as np

"""Base-class of an Observation object with start_time, sources, telescopes, frequencies and scans

    Notes: 
    Contains:
    Atributes:
        observation code
        observation type
        sources
        telescopes
        frequencies
        scans

    Methods:
        activate
        deactivate

        set_observation
        set_observation_type
        set_observation_code
        set_sources
        set_frequencies
        set_telescopes
        set_scans
        set_calculated_data

        get_observation_type
        get_observation_code
        get_sources
        get_frequencies
        get_telescopes
        get_scans
        get_calculated_data

        get_start_datetime

        validate

        to_dict
        from_dict

        _update_scan_indices
        _sync_scans_with_activation

        __init__
        __repr__
    """

class Observation(BaseEntity):
    def __init__(self, observation_code: str = "OBS_DEFAULT", sources: Sources = None,
                 telescopes: Telescopes = None, frequencies: Frequencies = None,
                 scans: Scans = None, observation_type: str = "VLBI", isactive: bool = True):
        """Initialize an Observation object"""
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
        self._sources._parent = self
        self._telescopes._parent = self
        self._frequencies._parent = self
        self._scans._parent = self
        self._calculated_data: Dict[str, Any] = {} # Хранилище для результатов Calculator
        logger.info(f"Initialized Observation '{observation_code}' with type '{observation_type}'")

    def set_observation(self, observation_code: str, sources: Sources = None,
                        telescopes: Telescopes = None, frequencies: Frequencies = None,
                        scans: Scans = None, observation_type: str = "VLBI", isactive: bool = True) -> None:
        """Set observation parameters"""
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
        self._calculated_data.clear()
        logger.info(f"Set observation '{observation_code}' with type '{observation_type}'")
    
    def activate(self) -> None:
        """Activate observation"""
        super().activate()

    def deactivate(self) -> None:
        """Deactivate observation"""
        super().deactivate()

    def set_observation_type(self, observation_type: str) -> None:
        """Set observation type (VLBI or SINGLE_DISH)"""
        check_type(observation_type, str, "Observation type")
        if observation_type not in ("VLBI", "SINGLE_DISH"):
            logger.error(f"Observation type must be 'VLBI' or 'SINGLE_DISH', got {observation_type}")
            raise ValueError(f"Observation type must be 'VLBI' or 'SINGLE_DISH', got {observation_type}")
        self._observation_type = observation_type
        logger.info(f"Set observation type to '{observation_type}' for observation '{self._observation_code}'")

    def set_observation_code(self, observation_code: str) -> None:
        """Set observation code"""
        check_type(observation_code, str, "Observation code")
        self._observation_code = observation_code
        logger.info(f"Set observation code to '{observation_code}'")

    def set_sources(self, sources: Sources) -> None:
        """Set observation sources"""
        check_type(sources, Sources, "Sources")
        self._sources = sources
        self._calculated_data.clear()
        logger.info(f"Set sources for observation '{self._observation_code}'")

    def set_frequencies(self, frequencies: Frequencies) -> None:
        """Set observation frequencies with polarizations"""
        check_type(frequencies, Frequencies, "Frequencies")
        self._frequencies = frequencies
        self._calculated_data.clear()
        logger.info(f"Set frequencies with polarizations for observation '{self._observation_code}'")

    def set_telescopes(self, telescopes: Telescopes) -> None:
        """Set observation telescopes"""
        check_type(telescopes, Telescopes, "Telescopes")
        self._telescopes = telescopes
        self._calculated_data.clear()
        logger.info(f"Set telescopes for observation '{self._observation_code}'")    

    def set_scans(self, scans: Scans) -> None:
        """Set observation scans"""
        check_type(scans, Scans, "Scans")
        self._scans = scans
        self._calculated_data.clear()  # Очищаем результаты, так как данные изменились
        logger.info(f"Set scans for observation '{self._observation_code}'")

    def set_calculated_data(self, key: str, data: Any) -> None:
        """Save calculated data for this observation"""
        check_non_empty_string(key, "Key")
        self._calculated_data[key] = data
        logger.info(f"Stored calculated data '{key}' for observation '{self._observation_code}'")

    def get_observation_code(self) -> str:
        """Get observation code"""
        return self._observation_code
    
    def get_observation_type(self) -> str:
        """Get observation type"""
        return self._observation_type

    def get_sources(self) -> Sources:
        """Get observation sources"""
        return self._sources
    
    def get_frequencies(self) -> Frequencies:
        """Get observation frequencies"""
        return self._frequencies

    def get_telescopes(self) -> Telescopes:
        """Get observation telescopes."""
        return self._telescopes

    def get_scans(self) -> Scans:
        """Get observation scans"""
        return self._scans
    
    def get_calculated_data(self) -> Any:
        """Retrieve calculated data by key"""
        return self._calculated_data

    def get_start_datetime(self) -> Optional[datetime]:
        """Get observation start time as a datetime object (UTC), based on earliest scan"""
        active_scans = self._scans.get_active_scans(self)  # Передаем self
        if not active_scans:
            return None
        return min(scan.get_start_datetime() for scan in active_scans)
    
    def validate(self) -> bool:
        """Validate the observation parameters"""

        # check observation code
        if not self._observation_code or not isinstance(self._observation_code, str):
            logger.error("Observation code must be a non-empty string")
            return False

        # check observation type
        if self._observation_type not in ["VLBI", "SINGLE_DISH"]:
            logger.error(f"Invalid observation type: {self._observation_type}. Must be 'VLBI' or 'SINGLE_DISH'")
            return False

        # validate sources
        if not self._sources.get_active_sources():
            logger.error("No active sources defined in observation")
            return False
        for source in self._sources.get_active_sources():
            if not source.validate():
                logger.error(f"Source validation failed for {source.get_name()}")
                return False

        # validate telescopes
        if not self._telescopes.get_active_telescopes():
            logger.error("No active telescopes defined in observation")
            return False
        for telescope in self._telescopes.get_active_telescopes():
            if not telescope.validate():
                logger.error(f"Telescope validation failed for {telescope.get_telescope_code()}")
                return False

        # validate frequencies
        if not self._frequencies.get_active_frequencies():
            logger.error("No active frequencies defined in observation")
            return False
        for freq in self._frequencies.get_active_frequencies():
            if not freq.validate():
                logger.error(f"Frequency validation failed for {freq}")
                return False

        # validate scans
        if not self._scans.get_active_scans(self):
            logger.error("No active scans defined in observation")
            return False
        for scan in self._scans.get_active_scans(self):
            if not scan.validate():
                logger.error(f"Scan validation failed for start time {scan.get_start()}")
                return False

        # check temporal consistency of scans
        active_scans = sorted(self._scans.get_active_scans(), key=lambda x: x.get_start())
        telescope_scans = {}
        for scan in active_scans:
            scan_start = scan.get_start()
            scan_end = scan_start + scan.get_duration()
            
            # check telescope availability for scan
            if not scan.check_telescope_availability():
                logger.error(f"Telescope availability check failed for scan starting at {scan_start}")
                return False

            # check time overlap for telescopes
            for telescope in scan.get_telescopes().get_active_telescopes():
                tel_code = telescope.get_telescope_code()
                if tel_code not in telescope_scans:
                    telescope_scans[tel_code] = []
                for prev_start, prev_end in telescope_scans[tel_code]:
                    if not (scan_end <= prev_start or scan_start >= prev_end):
                        logger.error(f"Scan overlap detected for telescope {tel_code}: "
                                    f"[{prev_start}, {prev_end}] vs [{scan_start}, {scan_end}]")
                        return False
                telescope_scans[tel_code].append((scan_start, scan_end))

        logger.info(f"Observation '{self._observation_code}' validated successfully")
        return True
    
    def _update_scan_indices(self, entity_type: str, removed_index: Optional[int] = None, inserted_index: Optional[int] = None) -> None:
        """Update scan indices after adding/removing sources, telescopes, or frequencies."""
        entity_map = {"sources": "_source_index", "telescopes": "_telescope_indices", "frequencies": "_frequency_indices"}
        if entity_type not in entity_map:
            raise ValueError(f"Invalid entity type: {entity_type}")
        attr = entity_map[entity_type]
        
        for scan in self._scans.get_all_scans():
            if entity_type == "sources":
                current_idx = getattr(scan, attr)
                if removed_index is not None and current_idx is not None:
                    if current_idx == removed_index:
                        scan.set_source_index(None)  # Источник удалён, сбрасываем
                        scan.is_off_source = True
                    elif current_idx > removed_index:
                        scan.set_source_index(current_idx - 1)
                elif inserted_index is not None and current_idx is not None and current_idx >= inserted_index:
                    scan.set_source_index(current_idx + 1)
            else:  # telescopes or frequencies
                current_indices = getattr(scan, attr)
                updated_indices = []
                for idx in current_indices:
                    if removed_index is not None:
                        if idx == removed_index:
                            continue  # Пропускаем удалённый индекс
                        elif idx > removed_index:
                            updated_indices.append(idx - 1)
                        else:
                            updated_indices.append(idx)
                    elif inserted_index is not None:
                        if idx >= inserted_index:
                            updated_indices.append(idx + 1)
                        else:
                            updated_indices.append(idx)
                if removed_index is not None or inserted_index is not None:
                    if entity_type == "telescopes":
                        scan.set_telescope_indices(updated_indices)
                    else:
                        scan.set_frequency_indices(updated_indices)
        logger.debug(f"Updated scan indices for {entity_type} in observation '{self._observation_code}'")

    def _sync_scans_with_activation(self, entity_type: str, index: int, is_active: bool) -> None:
        """Sync scans when an entity (source, telescope, frequency) is activated/deactivated"""
        entity_map = {"sources": "_source_index", "telescopes": "_telescope_indices", "frequencies": "_frequency_indices"}
        original_map = {"telescopes": "_original_telescope_indices", "frequencies": "_original_frequency_indices"}
        if entity_type not in entity_map:
            raise ValueError(f"Invalid entity type: {entity_type}")
        attr = entity_map[entity_type]
        
        for scan in self._scans.get_all_scans():
            if entity_type == "sources":
                current_idx = getattr(scan, attr)
                if current_idx == index:
                    if not is_active:
                        scan.set_source_index(None)
                        scan.is_off_source = True
                        logger.debug(f"Scan source index reset to None due to deactivation in '{self._observation_code}'")
                    elif is_active and scan.is_off_source and current_idx is not None:
                        scan.set_source_index(index)
                        scan.is_off_source = False
                        logger.debug(f"Scan source index restored to {index} due to activation in '{self._observation_code}'")
            else:  # telescopes or frequencies
                current_indices = getattr(scan, attr)
                original_indices = getattr(scan, original_map[entity_type])  # Используем правильный атрибут
                if index in current_indices and not is_active:
                    updated_indices = [i for i in current_indices if i != index]
                    if entity_type == "telescopes":
                        scan.set_telescope_indices(updated_indices)
                    else:
                        scan.set_frequency_indices(updated_indices)
                    logger.debug(f"Removed {entity_type} index {index} from scan in '{self._observation_code}'")
                elif index not in current_indices and is_active:
                    all_entities = (self._telescopes.get_all_telescopes() if entity_type == "telescopes" 
                                    else self._frequencies.get_all_frequencies())
                    if index < len(all_entities) and all_entities[index].isactive:
                        if index in original_indices:
                            updated_indices = sorted(current_indices + [index])
                            if entity_type == "telescopes":
                                scan.set_telescope_indices(updated_indices)
                            else:
                                scan.set_frequency_indices(updated_indices)
                            logger.debug(f"Added {entity_type} index {index} to scan in '{self._observation_code}'")    

    def to_dict(self) -> dict:
        """Convert Observation object to a dictionary for serialization"""
        def convert_quantity(obj):
            if isinstance(obj, u.Quantity):
                return obj.value.tolist() if obj.isscalar else obj.value.tolist()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, bool):
                return bool(obj)
            elif isinstance(obj, dict):
                return {k: convert_quantity(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_quantity(item) for item in obj]
            return obj

        data = {
            "observation_code": self._observation_code,
            "observation_type": self._observation_type,
            "sources": self._sources.to_dict(),
            "telescopes": self._telescopes.to_dict(),
            "frequencies": self._frequencies.to_dict(),
            "scans": self._scans.to_dict(),
            "isactive": self.isactive,
            "calculated_data": convert_quantity(self._calculated_data) if hasattr(self, '_calculated_data') else {}
        }
        logger.info(f"Converted observation '{self._observation_code}' to dictionary")
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Observation':
        """Create an Observation object from a dictionary."""
        obs = cls(
            observation_code=data["observation_code"],
            observation_type=data["observation_type"],
            sources=Sources.from_dict(data["sources"]),
            telescopes=Telescopes.from_dict(data["telescopes"]),
            frequencies=Frequencies.from_dict(data["frequencies"]),
            scans=Scans.from_dict(data["scans"]),
            isactive=data.get("isactive", True)
        )
        if "calculated_data" in data:
            obs._calculated_data = data["calculated_data"]
        logger.info(f"Created observation '{data['observation_code']}' from dictionary")
        return obs

    def __repr__(self) -> str:
        """Return a string representation of Observation."""
        return (f"Observation(code='{self._observation_code}', sources={self._sources}, "
                f"telescopes={self._telescopes}, frequencies={self._frequencies}, "
                f"scans={self._scans}, isactive={self.isactive}, "
                f"calculated_data={len(self._calculated_data)} items)")