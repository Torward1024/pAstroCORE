# unit_scheduling_2/base/observation.py
from common.base.baseentity import BaseEntity
from common.utils.validation import check_type, check_non_empty_string
from common.utils.logging_setup import logger
from unit_scheduling_2.base.sources import Sources
from unit_scheduling_2.base.telescopes import Telescopes
from unit_scheduling_2.base.frequencies import Frequencies
from unit_scheduling_2.base.scans import Scans
from astropy.time import Time
from typing import Optional, Dict, Any
import astropy.units as u
import numpy as np

class Observation(BaseEntity):
    """Base class representing an astronomical observation with sources, telescopes, frequencies, and scans.

    Encapsulates the structure and metadata of an observation, such as its unique code, type (VLBI or
    SINGLE_DISH), and associated entities. Manages calculated data (e.g., visibility, UV coverage) and
    provides methods for validation, synchronization, and serialization. Maintains consistency between
    scans and their referenced entities, updating names and availability as entities are modified.

    Attributes:
        observation_code (str): Unique identifier for the observation.
        observation_type (str): Type of observation, either 'VLBI' or 'SINGLE_DISH'.
        sources (Sources): Collection of source objects observed.
        telescopes (Telescopes): Collection of telescope objects used.
        frequencies (Frequencies): Collection of intermediate frequency (IF) objects.
        scans (Scans): Collection of scan objects defining observation timing and targets.
        calculated_data (Dict[str, Any]): Dictionary storing calculated results.
        isactive (bool): Indicates whether the observation is active.
    """
    observation_code: str
    observation_type: str
    sources: Sources
    telescopes: Telescopes
    frequencies: Frequencies
    scans: Scans
    calculated_data: Dict[str, Any]

    def __init__(self, observation_code: str = "OBS_DEFAULT", sources: Sources = None,
                 telescopes: Telescopes = None, frequencies: Frequencies = None,
                 scans: Scans = None, observation_type: str = "VLBI", 
                 calculated_data: Dict[str, Any] = None, isactive: bool = True):
        """Initialize an Observation with code, entities, type, calculated data, and active status."""
        if observation_type not in ("VLBI", "SINGLE_DISH"):
            logger.error(f"Observation type must be 'VLBI' or 'SINGLE_DISH', got {observation_type}")
            raise ValueError(f"Observation type must be 'VLBI' or 'SINGLE_DISH', got {observation_type}")
        check_type(observation_code, str, "Observation code")
        if sources is not None:
            check_type(sources, Sources, "Sources")
        if telescopes is not None:
            check_type(telescopes, Telescopes, "Telescopes")
        if frequencies is not None:
            check_type(frequencies, Frequencies, "Frequencies")
        if scans is not None:
            check_type(scans, Scans, "Scans")
        if calculated_data is not None:
            check_type(calculated_data, dict, "Calculated data")
        super().__init__(
            observation_code=observation_code,
            observation_type=observation_type,
            sources=sources if sources is not None else Sources(),
            telescopes=telescopes if telescopes is not None else Telescopes(),
            frequencies=frequencies if frequencies is not None else Frequencies(),
            scans=scans if scans is not None else Scans(),
            calculated_data=calculated_data if calculated_data is not None else {},
            isactive=isactive,
        )
        # Restore parent links for synchronization
        self.sources._parent = self
        self.telescopes._parent = self
        self.frequencies._parent = self
        self.scans._parent = self
        logger.info(f"Initialized Observation '{observation_code}' with type '{observation_type}'")

    def get_observation_code(self) -> str:
        """Retrieve the observation code."""
        return self.get("observation_code")

    def get_observation_type(self) -> str:
        """Retrieve the observation type."""
        return self.get("observation_type")

    def get_sources(self) -> Sources:
        """Retrieve the Sources object."""
        return self.get("sources")

    def get_frequencies(self) -> Frequencies:
        """Retrieve the Frequencies object."""
        return self.get("frequencies")

    def get_telescopes(self) -> Telescopes:
        """Retrieve the Telescopes object."""
        return self.get("telescopes")

    def get_scans(self) -> Scans:
        """Retrieve the Scans object."""
        return self.get("scans")

    def get_calculated_data(self) -> Dict[str, Any]:
        """Retrieve all calculated data."""
        return self.get("calculated_data")

    def get_calculated_data_by_key(self, key: str) -> Any:
        """Retrieve calculated data for a specific key."""
        check_non_empty_string(key, "Key")
        data = self.calculated_data.get(key)
        if data is not None:
            logger.debug(f"Retrieved calculated data '{key}' for observation '{self.observation_code}'")
        else:
            logger.debug(f"No calculated data found for key '{key}' in observation '{self.observation_code}'")
        return data

    def set_calculated_data_by_key(self, key: str, data: Any) -> None:
        """Set calculated data for a specific key."""
        check_non_empty_string(key, "Key")
        new_data = self.calculated_data.copy()
        new_data[key] = data
        self.set({"calculated_data": new_data})
        logger.info(f"Stored calculated data '{key}' for observation '{self.observation_code}'")

    def get_start_datetime(self) -> Optional[Time]:
        """Retrieve the earliest start time of active scans."""
        active_scans = self.scans.get_active_scans(self)
        if not active_scans:
            logger.debug(f"No active scans found for observation '{self.observation_code}'")
            return None
        start_time = min(scan.get_start() for scan in active_scans)
        logger.debug(f"Retrieved start datetime {start_time.isot} for observation '{self.observation_code}'")
        return start_time

    def validate(self) -> bool:
        """Validate the observation's data for consistency and completeness."""
        observation_code = self.get("observation_code")
        if not observation_code:
            logger.error("Observation code must be a non-empty string")
            return False

        observation_type = self.get("observation_type")
        if observation_type not in ["VLBI", "SINGLE_DISH"]:
            logger.error(f"Invalid observation type: {observation_type}. Must be 'VLBI' or 'SINGLE_DISH'")
            return False

        if not self.sources.get_active_items():
            logger.error("No active sources defined in observation")
            return False

        if not self.telescopes.get_active_items():
            logger.error("No active telescopes defined in observation")
            return False

        if not self.frequencies.get_active_items():
            logger.error("No active frequencies defined in observation")
            return False

        if not self.scans.get_active_scans(self):
            logger.error("No active scans defined in observation")
            return False

        active_scans = sorted(self.scans.get_active_scans(self), key=lambda x: x.get_start())
        telescope_scans = {}
        for scan in active_scans:
            scan_start = scan.get_start()
            scan_end = scan_start + scan.get_duration() * u.s

            if not scan.check_telescope_availability(self):
                logger.error(f"Telescope availability check failed for scan starting at {scan_start.isot}")
                return False

            for telescope in scan.get_telescopes(self).get_active_items():
                tel_code = telescope.get_code()
                if tel_code not in telescope_scans:
                    telescope_scans[tel_code] = []
                for prev_start, prev_end in telescope_scans[tel_code]:
                    if not (scan_end <= prev_start or scan_start >= prev_end):
                        logger.error(f"Scan overlap detected for telescope {tel_code}: "
                                     f"[{prev_start.isot}, {prev_end.isot}] vs [{scan_start.isot}, {scan_end.isot}]")
                        return False
                telescope_scans[tel_code].append((scan_start, scan_end))

        logger.info(f"Observation '{observation_code}' validated successfully")
        return True

    def _update_scan_names(self, entity_type: str, name: str, operation: str) -> None:
        """Update scan names after an entity is removed or added.

        Args:
            entity_type (str): Type of entity ('sources', 'telescopes', 'frequencies').
            name (str): Name of the entity (source name, telescope code, or frequency name).
            operation (str): Operation type ('remove' or 'add').
        """
        entity_map = {
            "sources": "source_name",
            "telescopes": "telescope_names",
            "frequencies": "frequency_names"
        }
        if entity_type not in entity_map:
            logger.error(f"Invalid entity type: {entity_type}")
            raise ValueError(f"Invalid entity type: {entity_type}")
        attr = entity_map[entity_type]

        for scan in self.scans.get_items():
            if entity_type == "sources":
                current_name = getattr(scan, attr)
                if operation == "remove" and current_name == name:
                    scan.set({"source_name": None, "is_off_source": True, "original_source_name": current_name})
                    logger.debug(f"Reset source name to None for scan '{scan.name}' in observation '{self.observation_code}'")
                elif operation == "add" and getattr(scan, "original_source_name", None) == name:
                    scan.set({"source_name": name, "is_off_source": False})
                    logger.debug(f"Restored source name '{name}' for scan '{scan.name}' in '{self.observation_code}'")
            else:
                current_names = getattr(scan, attr)
                if operation == "remove" and name in current_names:
                    updated_names = [n for n in current_names if n != name]
                    scan.set({attr: updated_names})
                    logger.debug(f"Removed {entity_type} name '{name}' from scan '{scan.name}' in '{self.observation_code}'")
                elif operation == "add":
                    # Note: Adding names typically happens via Manipulator, so we may not need to handle it here
                    pass

    def _sync_scans_with_activation(self, entity_type: str, name: str, is_active: bool) -> None:
        """Synchronize scan names with entity activation/deactivation."""
        entity_map = {
            "sources": "source_name",
            "telescopes": "telescope_names",
            "frequencies": "frequency_names"
        }
        original_map = {
            "sources": "original_source_name",
            "telescopes": "original_telescope_names",
            "frequencies": "original_frequency_names"
        }
        if entity_type not in entity_map:
            logger.error(f"Invalid entity type: {entity_type}")
            raise ValueError(f"Invalid entity type: {entity_type}")
        attr = entity_map[entity_type]
        original_attr = original_map[entity_type]

        for scan in self.scans.get_items():
            current_names = getattr(scan, attr, []) or []
            original_names = getattr(scan, original_attr, []) or []

            if entity_type == "sources":
                original_name = getattr(scan, original_attr, None)
                if original_name == name:
                    scan.set({
                        "source_name": None if not is_active else name,
                        "is_off_source": not is_active,
                        "original_source_name": name if not is_active else original_name
                    })
            else:
                entities = (self.telescopes.get_items() if entity_type == "telescopes"
                            else self.frequencies.get_items())
                if name in current_names and not is_active:
                    updated_names = [n for n in current_names if n != name]
                    if not getattr(scan, original_attr, None):
                        scan.set({original_attr: current_names[:]})
                    scan.set({attr: updated_names})
                elif is_active and name in original_names:
                    # Проверяем, есть ли активный объект с нужным именем
                    for entity in entities:
                        if entity.name == name and entity.isactive:
                            scan.set({attr: sorted(list(set(current_names + [name])))})
                            break

    def to_dict(self) -> dict:
        """Convert the Observation object to a dictionary for serialization."""
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

        data = super().to_dict()
        data["calculated_data"] = convert_quantity(self.calculated_data)
        logger.info(f"Converted observation '{self.observation_code}' to dictionary")
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Observation':
        """Create an Observation object from a dictionary."""
        kwargs = {
            "observation_code": data["observation_code"],
            "observation_type": data["observation_type"],
            "sources": Sources.from_dict(data["sources"]),
            "telescopes": Telescopes.from_dict(data["telescopes"]),
            "frequencies": Frequencies.from_dict(data["frequencies"]),
            "scans": Scans.from_dict(data["scans"]),
            "calculated_data": data.get("calculated_data", {}),
            "isactive": data.get("isactive", True),
        }
        obs = cls(**kwargs)
        logger.info(f"Created observation '{data['observation_code']}' from dictionary")
        return obs

    def __repr__(self) -> str:
        """Return a string representation of the Observation object."""
        return (f"Observation(code='{self.observation_code}', sources={self.sources}, "
                f"telescopes={self.telescopes}, frequencies={self.frequencies}, "
                f"scans={self.scans}, isactive={self.isactive}, "
                f"observation_type={self.observation_type}, "
                f"calculated_data={len(self.calculated_data)} items)")