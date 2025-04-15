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

    This class encapsulates the structure and metadata of an observation, such as its unique code, type (VLBI or
    SINGLE_DISH), and associated entities (sources, telescopes, frequencies, and scans). It manages calculated
    data (e.g., visibility, UV coverage) in a dictionary and provides methods for validation, synchronization,
    and serialization. The class is designed to maintain consistency between scans and their referenced entities,
    updating indices and availability as entities are modified.

    Attributes:
        _observation_code (str): Unique identifier for the observation.
        _observation_type (str): Type of observation, either 'VLBI' or 'SINGLE_DISH'.
        _sources (Sources): Collection of source objects observed.
        _telescopes (Telescopes): Collection of telescope objects used.
        _frequencies (Frequencies): Collection of intermediate frequency (IF) objects.
        _scans (Scans): Collection of scan objects defining observation timing and targets.
        _calculated_data (Dict[str, Any]): Dictionary storing calculated results (e.g., UV coverage, beam patterns).
        isactive (bool): Indicates whether the observation is active. Inherited from BaseEntity.

    Notes:
        - The class links itself as the `_parent` of its `Sources`, `Telescopes`, `Frequencies`, and `Scans` objects
          to enable synchronization (e.g., updating scan indices when entities are activated/deactivated).
        - Calculated data is cleared when sources, telescopes, frequencies, or scans are replaced to ensure consistency.
        - Logging is integrated via `common.utils.logging_setup.logger` to track operations and errors.
        - Validation checks for active entities, non-overlapping telescope schedules, and telescope availability.

    Examples:
        >>> from astropy.time import Time
        >>> obs = Observation(observation_code="M87_OBS", observation_type="VLBI")
        >>> obs.get_sources().create_source(name="M87", ra_h=12, ra_m=30, ra_s=0, de_d=12, de_m=20, de_s=0)
        >>> obs.get_scans().create_scan(start=Time("2025-04-06T00:00:00"), duration=600.0, source_index=0, telescope_indices=[0, 1])
        >>> print(obs)
        Observation(code='M87_OBS', sources=Sources(count=1, active=1, inactive=0), telescopes=Telescopes(count=0, active=0, inactive=0), frequencies=Frequencies(count=0, active=0, inactive=0), scans=Scans(count=1, active=1, inactive=0), isactive=True, observation_type=VLBI, calculated_data=0 items)
        >>> obs.validate()
        False  # Fails due to no active telescopes or frequencies

    Methods:
        __init__: Initialize the Observation with code, entities, type, and active status.
        set_observation: Set all properties of the Observation.
        activate: Mark the Observation as active.
        deactivate: Mark the Observation as inactive.
        set_observation_type: Set the observation type (VLBI or SINGLE_DISH).
        set_observation_code: Set the observation code.
        set_sources: Set the Sources object.
        set_frequencies: Set the Frequencies object.
        set_telescopes: Set the Telescopes object.
        set_scans: Set the Scans object.
        set_calculated_data: Set the entire calculated data dictionary.
        set_calculated_data_by_key: Set calculated data for a specific key.
        get_observation_code: Retrieve the observation code.
        get_observation_type: Retrieve the observation type.
        get_sources: Retrieve the Sources object.
        get_frequencies: Retrieve the Frequencies object.
        get_telescopes: Retrieve the Telescopes object.
        get_scans: Retrieve the Scans object.
        get_calculated_data: Retrieve all calculated data.
        get_calculated_data_by_key: Retrieve calculated data by key.
        get_start_datetime: Retrieve the earliest start time of active scans.
        validate: Validate the observation for consistency and completeness.
        _update_scan_indices: Update scan indices after entity removal or insertion.
        _sync_scans_with_activation: Synchronize scans with entity activation/deactivation.
        to_dict: Convert the Observation to a dictionary.
        from_dict: Create an Observation from a dictionary.
        __repr__: Return a string representation of the Observation.
    """
    def __init__(self, observation_code: str = "OBS_DEFAULT", sources: Sources = None,
                 telescopes: Telescopes = None, frequencies: Frequencies = None,
                 scans: Scans = None, observation_type: str = "VLBI", isactive: bool = True):
        """Initialize an Observation object with code, sources, telescopes, frequencies, scans, and type.

        Args:
            observation_code (str): Unique identifier for the observation. Defaults to "OBS_DEFAULT".
            sources (Sources, optional): Sources object containing source data. Defaults to None (empty Sources).
            telescopes (Telescopes, optional): Telescopes object containing telescope data. Defaults to None (empty Telescopes).
            frequencies (Frequencies, optional): Frequencies object containing IF data. Defaults to None (empty Frequencies).
            scans (Scans, optional): Scans object containing scan data. Defaults to None (empty Scans).
            observation_type (str): Type of observation ('VLBI' or 'SINGLE_DISH'). Defaults to "VLBI".
            isactive (bool): Whether the observation is active. Defaults to True.

        Raises:
            TypeError: If observation_code is not a string, or sources/telescopes/frequencies/scans are of incorrect type.
            ValueError: If observation_type is not 'VLBI' or 'SINGLE_DISH'.
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
        self._sources._parent = self
        self._telescopes._parent = self
        self._frequencies._parent = self
        self._scans._parent = self
        self._calculated_data: Dict[str, Any] = {}
        logger.info(f"Initialized Observation '{observation_code}' with type '{observation_type}'")

    def set_observation(self, observation_code: str, sources: Sources = None,
                        telescopes: Telescopes = None, frequencies: Frequencies = None,
                        scans: Scans = None, observation_type: str = "VLBI", isactive: bool = True) -> None:
        """Set all properties of the Observation object.

        Args:
            observation_code (str): Unique identifier for the observation.
            sources (Sources, optional): Sources object. Defaults to None (empty Sources).
            telescopes (Telescopes, optional): Telescopes object. Defaults to None (empty Telescopes).
            frequencies (Frequencies, optional): Frequencies object. Defaults to None (empty Frequencies).
            scans (Scans, optional): Scans object. Defaults to None (empty Scans).
            observation_type (str): Type of observation ('VLBI' or 'SINGLE_DISH'). Defaults to "VLBI".
            isactive (bool): Whether the observation is active. Defaults to True.

        Raises:
            TypeError: If observation_code is not a string, or sources/telescopes/frequencies/scans are of incorrect type.
            ValueError: If observation_type is not 'VLBI' or 'SINGLE_DISH'.
        """
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
        """Activate the Observation object, marking it as active."""
        super().activate()

    def deactivate(self) -> None:
        """Deactivate the Observation object, marking it as inactive."""
        super().deactivate()

    def set_observation_type(self, observation_type: str) -> None:
        """Set the observation type.

        Args:
            observation_type (str): Type of observation ('VLBI' or 'SINGLE_DISH').

        Raises:
            TypeError: If observation_type is not a string.
            ValueError: If observation_type is not 'VLBI' or 'SINGLE_DISH'.
        """
        check_type(observation_type, str, "Observation type")
        if observation_type not in ("VLBI", "SINGLE_DISH"):
            logger.error(f"Observation type must be 'VLBI' or 'SINGLE_DISH', got {observation_type}")
            raise ValueError(f"Observation type must be 'VLBI' or 'SINGLE_DISH', got {observation_type}")
        self._observation_type = observation_type
        logger.info(f"Set observation type to '{observation_type}' for observation '{self._observation_code}'")

    def set_observation_code(self, observation_code: str) -> None:
        """Set the observation code.

        Args:
            observation_code (str): New unique identifier for the observation.

        Raises:
            TypeError: If observation_code is not a string.
        """
        check_type(observation_code, str, "Observation code")
        self._observation_code = observation_code
        logger.info(f"Set observation code to '{observation_code}'")

    def set_sources(self, sources: Sources) -> None:
        """Set the Sources object for the observation.

        Args:
            sources (Sources): New Sources object.

        Raises:
            TypeError: If sources is not a Sources instance.
        """
        check_type(sources, Sources, "Sources")
        self._sources = sources
        self._calculated_data.clear()
        logger.info(f"Set sources for observation '{self._observation_code}'")

    def set_frequencies(self, frequencies: Frequencies) -> None:
        """Set the Frequencies object for the observation.

        Args:
            frequencies (Frequencies): New Frequencies object.

        Raises:
            TypeError: If frequencies is not a Frequencies instance.
        """
        check_type(frequencies, Frequencies, "Frequencies")
        self._frequencies = frequencies
        self._calculated_data.clear()
        logger.info(f"Set frequencies with polarizations for observation '{self._observation_code}'")

    def set_telescopes(self, telescopes: Telescopes) -> None:
        """Set the Telescopes object for the observation.

        Args:
            telescopes (Telescopes): New Telescopes object.

        Raises:
            TypeError: If telescopes is not a Telescopes instance.
        """
        check_type(telescopes, Telescopes, "Telescopes")
        self._telescopes = telescopes
        self._calculated_data.clear()
        logger.info(f"Set telescopes for observation '{self._observation_code}'")    

    def set_scans(self, scans: Scans) -> None:
        """Set the Scans object for the observation.

        Args:
            scans (Scans): New Scans object.

        Raises:
            TypeError: If scans is not a Scans instance.
        """
        check_type(scans, Scans, "Scans")
        self._scans = scans
        self._calculated_data.clear()
        logger.info(f"Set scans for observation '{self._observation_code}'")

    def set_calculated_data(self, data: Any) -> None:
        """Set the entire calculated data dictionary.

        Args:
            data (Any): Data to store, typically a dictionary of calculated results. A copy is made to prevent external modification.
        """
        self._calculated_data = data.copy()
        logger.info(f"Stored calculated data for observation '{self._observation_code}'")

    def set_calculated_data_by_key(self, key: str, data: Any) -> None:
        """Set calculated data for a specific key.

        Args:
            key (str): The key under which to store the data. Must be a non-empty string.
            data (Any): The data to store.

        Raises:
            TypeError: If key is not a non-empty string.
        """
        check_non_empty_string(key, "Key")
        self._calculated_data[key] = data
        logger.info(f"Stored calculated data '{key}' for observation '{self._observation_code}'")

    def get_observation_code(self) -> str:
        """Retrieve the observation code.

        Returns:
            str: The unique identifier for the observation.
        """
        return self._observation_code
    
    def get_observation_type(self) -> str:
        """Retrieve the observation type.

        Returns:
            str: The type of observation ('VLBI' or 'SINGLE_DISH').
        """
        return self._observation_type

    def get_sources(self) -> Sources:
        """Retrieve the Sources object.

        Returns:
            Sources: The Sources object containing source data.
        """
        return self._sources
    
    def get_frequencies(self) -> Frequencies:
        """Retrieve the Frequencies object.

        Returns:
            Frequencies: The Frequencies object containing IF data.
        """
        return self._frequencies

    def get_telescopes(self) -> Telescopes:
        """Retrieve the Telescopes object.

        Returns:
            Telescopes: The Telescopes object containing telescope data.
        """
        return self._telescopes

    def get_scans(self) -> Scans:
        """Retrieve the Scans object.

        Returns:
            Scans: The Scans object containing scan data.
        """
        return self._scans
    
    def get_calculated_data(self) -> Any:
        """Retrieve all calculated data.

        Returns:
            Any: The stored calculated data, typically a dictionary.
        """
        return self._calculated_data
    
    def get_calculated_data_by_key(self, key: str) -> Any:
        """Retrieve calculated data for a specific key.

        Args:
            key (str): The key to retrieve data for. Must be a non-empty string.

        Returns:
            Any: The data associated with the key, or None if not found.

        Raises:
            TypeError: If key is not a non-empty string.
        """
        check_non_empty_string(key, "Key")
        if self._calculated_data.get(key):
            logger.info(f"Retrieved calculated data '{key}' for observation '{self._observation_code}'")
        return self._calculated_data.get(key)

    def get_start_datetime(self) -> Optional[Time]:
        """Retrieve the earliest start time of active scans.

        Returns:
            Time | None: The earliest start time as an astropy Time object (UTC), or None if no active scans exist.
        """
        active_scans = self._scans.get_active_scans(self)
        if not active_scans:
            return None
        return min(scan.get_start() for scan in active_scans)
    
    def validate(self) -> bool:
        """Validate the observation's data for consistency and completeness.

        Checks:
        - Observation code is a non-empty string.
        - Observation type is 'VLBI' or 'SINGLE_DISH'.
        - At least one active source, telescope, frequency, and scan exist.
        - No overlapping telescope schedules in active scans.
        - Telescope availability for each scan.

        Returns:
            bool: True if the observation is valid, False otherwise. Errors are logged with details.
        """
        if not self._observation_code or not isinstance(self._observation_code, str):
            logger.error("Observation code must be a non-empty string")
            return False

        if self._observation_type not in ["VLBI", "SINGLE_DISH"]:
            logger.error(f"Invalid observation type: {self._observation_type}. Must be 'VLBI' or 'SINGLE_DISH'")
            return False

        if not self._sources.get_active_sources():
            logger.error("No active sources defined in observation")
            return False

        if not self._telescopes.get_active_telescopes():
            logger.error("No active telescopes defined in observation")
            return False

        if not self._frequencies.get_active_frequencies():
            logger.error("No active frequencies defined in observation")
            return False

        if not self._scans.get_active_scans(self):
            logger.error("No active scans defined in observation")
            return False

        active_scans = sorted(self._scans.get_active_scans(), key=lambda x: x.get_start())
        telescope_scans = {}
        for scan in active_scans:
            scan_start = scan.get_start()
            scan_end = scan_start + scan.get_duration()
            
            if not scan.check_telescope_availability(self):
                logger.error(f"Telescope availability check failed for scan starting at {scan_start.isot}")
                return False

            for telescope in scan.get_telescopes(self).get_active_telescopes():
                tel_code = telescope.get_code()
                if tel_code not in telescope_scans:
                    telescope_scans[tel_code] = []
                for prev_start, prev_end in telescope_scans[tel_code]:
                    if not (scan_end <= prev_start or scan_start >= prev_end):
                        logger.error(f"Scan overlap detected for telescope {tel_code}: "
                                    f"[{prev_start.isot}, {prev_end.isot}] vs [{scan_start.isot}, {scan_end.isot}]")
                        return False
                telescope_scans[tel_code].append((scan_start, scan_end))

        logger.info(f"Observation '{self._observation_code}' validated successfully")
        return True
    
    def _update_scan_indices(self, entity_type: str, removed_index: Optional[int] = None, inserted_index: Optional[int] = None) -> None:
        """Update scan indices after an entity is removed or inserted.

        Adjusts source, telescope, or frequency indices in all scans when an entity is removed or inserted in
        the respective collection. For sources, removal sets the index to None and marks the scan as off-source.
        For telescopes and frequencies, indices are shifted or removed as needed.

        Args:
            entity_type (str): Type of entity ('sources', 'telescopes', 'frequencies').
            removed_index (int, optional): Index of the removed entity. Defaults to None.
            inserted_index (int, optional): Index where an entity was inserted. Defaults to None.

        Raises:
            ValueError: If entity_type is not one of 'sources', 'telescopes', or 'frequencies'.
        """
        entity_map = {"sources": "_source_index", "telescopes": "_telescope_indices", "frequencies": "_frequency_indices"}
        if entity_type not in entity_map:
            raise ValueError(f"Invalid entity type: {entity_type}")
        attr = entity_map[entity_type]
        
        for scan in self._scans.get_all_scans():
            if entity_type == "sources":
                current_idx = getattr(scan, attr)
                if removed_index is not None and current_idx is not None:
                    if current_idx == removed_index:
                        scan.set_source_index(None)
                        scan.is_off_source = True
                    elif current_idx > removed_index:
                        scan.set_source_index(current_idx - 1)
                elif inserted_index is not None and current_idx is not None and current_idx >= inserted_index:
                    scan.set_source_index(current_idx + 1)
            else:
                current_indices = getattr(scan, attr)
                updated_indices = []
                for idx in current_indices:
                    if removed_index is not None:
                        if idx == removed_index:
                            continue
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
        """Synchronize scan indices with entity activation/deactivation.

        Updates scan indices when a source, telescope, or frequency is activated or deactivated. For sources,
        deactivation sets the index to None and marks the scan as off-source; activation restores it if previously
        off-source. For telescopes and frequencies, indices are added or removed based on original values.

        Args:
            entity_type (str): Type of entity ('sources', 'telescopes', 'frequencies').
            index (int): Index of the entity being activated/deactivated.
            is_active (bool): Whether the entity is being activated (True) or deactivated (False).

        Raises:
            ValueError: If entity_type is not one of 'sources', 'telescopes', or 'frequencies'.
        """
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
            else:
                current_indices = getattr(scan, attr)
                original_indices = getattr(scan, original_map[entity_type])
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
        """Convert the Observation object to a dictionary for serialization.

        Converts all properties, including calculated data, to a serializable format. Astropy Quantity objects
        and NumPy arrays are converted to lists, and nested structures are recursively processed.

        Returns:
            dict: A dictionary containing all observation properties, with quantities converted to serializable formats.
        """
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
        """Create an Observation object from a dictionary.

        Args:
            data (dict): Dictionary containing observation properties, typically from `to_dict`.

        Returns:
            Observation: A new Observation instance initialized with the dictionary data.
        """
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
        """Return a string representation of the Observation object.

        Returns:
            str: A formatted string with observation code, components, status, observation type, and calculated data count.
        """
        return (f"Observation(code='{self._observation_code}', sources={self._sources}, "
                f"telescopes={self._telescopes}, frequencies={self._frequencies}, "
                f"scans={self._scans}, isactive={self.isactive}, "
                f"observation_type={self._observation_type}, "
                f"calculated_data={len(self._calculated_data)} items)")