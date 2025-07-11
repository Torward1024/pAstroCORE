# unit_scheduling_2/base/observation.py
from copy import deepcopy
from common.base.baseentity import BaseEntity
from common.utils.validation import check_type, check_non_empty_string
from common.utils.logging_setup import logger
from .sources import Sources
from .telescopes import Telescopes
from .frequencies import Frequencies
from .scans import Scans
from astropy.time import Time
from typing import Optional, Dict, Any
import astropy.units as u
import numpy as np
import uuid
import xarray as xr

class Observation(BaseEntity):
    """Base class representing an astronomical observation with sources, telescopes, frequencies, and scans.

    Encapsulates the structure and metadata of an observation, such as its unique code, type (VLBI or
    SINGLE_DISH), and associated entities. Manages calculated data (e.g., visibility, UV coverage) and
    provides methods for validation, synchronization, and serialization. Maintains consistency between
    scans and their referenced entities, updating names and availability as entities are modified.

    Attributes:
        code (str): Unique identifier for the observation.
        observation_type (str): Type of observation, either 'VLBI' or 'SINGLE_DISH'.
        sources (Sources): Collection of source objects observed.
        telescopes (Telescopes): Collection of telescope objects used.
        frequencies (Frequencies): Collection of intermediate frequency (IF) objects.
        scans (Scans): Collection of scan objects defining observation timing and targets.
        calculated_data (Dict[str, Any]): Dictionary storing calculated results.
        isactive (bool): Indicates whether the observation is active.
    """
    name: str
    code: str
    observation_type: str
    sources: Sources
    telescopes: Telescopes
    frequencies: Frequencies
    scans: Scans
    calculated_data: Dict[str, Any]

    def __init__(self, name: str = None, code: str = "OBS_DEFAULT", sources: Sources = None,
                 telescopes: Telescopes = None, frequencies: Frequencies = None,
                 scans: Scans = None, observation_type: str = "VLBI", 
                 calculated_data: Dict[str, Any] = None, isactive: bool = True):
        """Initialize an Observation with code, entities, type, calculated data, and active status."""
        if name is None:
            name = f"obs_{uuid.uuid4().hex[:32]}"
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
        if calculated_data is not None:
            check_type(calculated_data, dict, "Calculated data")
        super().__init__(name=name, code=code,
            observation_type=observation_type,
            sources=sources if sources is not None else Sources(),
            telescopes=telescopes if telescopes is not None else Telescopes(),
            frequencies=frequencies if frequencies is not None else Frequencies(),
            scans=scans if scans is not None else Scans(),
            calculated_data=calculated_data if calculated_data is not None else {},
            isactive=isactive,
        )
        logger.info(f"Initialized Observation '{name}' with type '{observation_type}'")

    def get_observation_code(self) -> str:
        """Retrieve the observation code."""
        return self.code

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

    def get_calculated_data_by_key(self, key: str) -> Optional[Dict[str, xr.Dataset]]:
        """Retrieve calculated data by key.

        Args:
            key (str): The key to retrieve data for.

        Returns:
            Optional[Dict[str, xr.Dataset]]: Dictionary of calculated data for each scan, or None if not found.
        """
        data = self.calculated_data.get(key)
        if data is not None:
            if not isinstance(data, dict):
                logger.warning(f"Expected dictionary for key '{key}' in observation '{self.get_observation_code()}', got {type(data)}")
                return None
            for scan_name, scan_data in data.items():
                if not isinstance(scan_data, xr.Dataset):
                    logger.warning(f"Expected xarray.Dataset for scan '{scan_name}' in key '{key}', got {type(scan_data)}")
                    return None
            logger.debug(f"Retrieved calculated data for key '{key}' from observation '{self.get_observation_code()}'")
        return data

    def set_calculated_data_by_key(self, key: str, data: Dict[str, xr.Dataset]) -> None:
        """Set calculated data for a specific key.

        Args:
            key (str): The key to store the data under.
            data (Dict[str, xr.Dataset]): Dictionary of calculated data for each scan, where values are xarray Datasets.
        """
        check_non_empty_string(key, "key")
        if not isinstance(data, dict):
            logger.error(f"Expected dictionary for key '{key}' in observation '{self.get_observation_code()}', got {type(data)}")
            raise ValueError(f"Data must be a dictionary, got {type(data)}")
        for scan_name, scan_data in data.items():
            if not isinstance(scan_data, xr.Dataset):
                logger.error(f"Expected xarray.Dataset for scan '{scan_name}' in key '{key}', got {type(scan_data)}")
                raise ValueError(f"Data for scan '{scan_name}' must be an xarray.Dataset, got {type(scan_data)}")
        self.calculated_data[key] = data
        logger.debug(f"Stored calculated data for key '{key}' with {len(data)} scans in observation '{self.get_observation_code()}'")

    def get_start_datetime(self) -> Optional[Time]:
        """Retrieve the earliest start time of active scans."""
        active_scans = self.scans.get_active_scans(self)
        if not active_scans:
            logger.debug(f"No active scans found for observation '{self.name}'")
            return None
        start_time = min(scan.get_start() for scan in active_scans)
        logger.debug(f"Retrieved start datetime {start_time.isot} for observation '{self.name}'")
        return start_time
    
    def get_duration(self) -> Optional[int]:
        """Retrieve the total observation duration in seconds by summing durations of active scans.

        Returns:
            Optional[int]: Total duration in seconds, or None if no active scans are found.
        """
        active_scans = self.scans.get_active_scans(self)
        if not active_scans:
            logger.debug(f"No active scans found for observation '{self.name}'")
            return None
        total_duration = sum(scan.get_duration() for scan in active_scans)
        logger.debug(f"Retrieved total duration {total_duration} seconds for observation '{self.name}'")
        return int(total_duration)
    
    def copy(self) -> 'Observation':
        """Create a deep copy of the Observation object."""
        return Observation(
            name=self.name,
            code=self.code,
            sources=self.sources.copy(),
            telescopes=self.telescopes.copy(),
            frequencies=self.frequencies.copy(),
            scans=self.scans.copy(),
            observation_type=self.observation_type,
            calculated_data=deepcopy(self.calculated_data),
            isactive=self.isactive
        )

    def validate(self) -> bool:
        """Validate the observation's data for consistency and completeness."""
        if not self.name:
            logger.error("Observation code must be a non-empty string")
            return False
        if self.observation_type not in ["VLBI", "SINGLE_DISH"]:
            logger.warning(f"Invalid observation type: {self.observation_type}")
            return False
        if not self.sources.get_active_items():
            logger.warning("No active sources defined in observation")
            return True
        if not self.telescopes.get_active_items():
            logger.warning("No active telescopes defined in observation")
            return False
        if not self.frequencies.get_active_items():
            logger.warning("No active frequencies defined in observation")
            return True
        if not self.scans.get_active_scans(self):
            logger.warning("No active scans defined in observation")
            return True
        active_scans = sorted(self.scans.get_active_scans(self), key=lambda x: x.get_start())
        telescope_scans = {}
        for scan in active_scans:
            scan_start = scan.get_start()
            scan_end = scan_start + scan.get_duration() * u.s
            if not scan.check_telescope_availability(self):
                logger.error(f"Telescope availability check failed for scan starting at {scan_start.isot}")
                return False
            for telescope in scan.telescopes:
                if not telescope.isactive:
                    continue
                tel_code = telescope.get_code()
                if tel_code not in telescope_scans:
                    telescope_scans[tel_code] = []
                for prev_start, prev_end in telescope_scans[tel_code]:
                    if not (scan_end <= prev_start or scan_start >= prev_end):
                        logger.error(f"Scan overlap detected for telescope {tel_code}: "
                                     f"[{prev_start.isot}, {prev_end.isot}] vs [{scan_start.isot}, {scan_end.isot}]")
                        return False
                telescope_scans[tel_code].append((scan_start, scan_end))
        logger.info(f"Observation '{self.name}' validated successfully")
        return True
    
    def clear_calculated_data(self):
        """Clear all cached calculation data for this observation."""
        self.calculated_data.clear()
        logger.debug(f"Cleared calculated data for observation '{self.get_observation_code()}'")
                
    def to_dict(self) -> dict:
        """Convert the Observation object to a dictionary for serialization.

        Returns:
            dict: Dictionary representation of the Observation, including serialized xarray.Dataset objects in calculated_data.
        """
        def convert_quantity(obj):
            if isinstance(obj, u.Quantity):
                return obj.value.tolist() if obj.isscalar else obj.value.tolist()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, bool):
                return bool(obj)
            elif isinstance(obj, dict):
                # Handle dictionary of xarray.Dataset (new format)
                return {k: convert_quantity(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_quantity(item) for item in obj]
            elif isinstance(obj, xr.Dataset):
                # Serialize xarray.Dataset to dictionary
                return obj.to_dict()
            return obj

        data = super().to_dict()
        data["calculated_data"] = {key: convert_quantity(value) for key, value in self.calculated_data.items()}
        logger.info(f"Converted observation '{self.name}' to dictionary with {len(self.calculated_data)} calculated datasets")
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Observation':
        """Create an Observation object from a dictionary.

        Args:
            data (dict): Dictionary containing observation data, including serialized xarray.Dataset objects in calculated_data.

        Returns:
            Observation: A new Observation instance populated with the provided data.
        """
        # Prepare calculated_data by converting dictionary representations to xarray.Dataset
        calculated_data = {}
        for key, value in data.get("calculated_data", {}).items():
            if isinstance(value, dict):
                scan_data = {}
                for scan_name, scan_value in value.items():
                    if isinstance(scan_value, dict) and 'data_vars' in scan_value and 'coords' in scan_value:
                        try:
                            scan_data[scan_name] = xr.Dataset.from_dict(scan_value)
                        except Exception as e:
                            logger.warning(f"Failed to deserialize xarray.Dataset for key '{key}', scan '{scan_name}' in observation '{data['name']}': {str(e)}")
                            continue
                    else:
                        logger.warning(f"Invalid calculated_data format for key '{key}', scan '{scan_name}' in observation '{data['name']}'")
                if scan_data:
                    calculated_data[key] = scan_data
            else:
                logger.warning(f"Expected dictionary for key '{key}' in observation '{data['name']}', got {type(value)}")
                calculated_data[key] = value

        kwargs = {
            "name": data["name"],
            "code": data["code"],
            "observation_type": data["observation_type"],
            "sources": Sources.from_dict(data["sources"]),
            "telescopes": Telescopes.from_dict(data["telescopes"]),
            "frequencies": Frequencies.from_dict(data["frequencies"]),
            "calculated_data": calculated_data,
            "isactive": data.get("isactive", True),
        }
        # Create Observation without scans first
        obs = cls(**kwargs)
        # Deserialize scans with the observation instance
        kwargs["scans"] = Scans.from_dict(data["scans"], observation=obs)
        # Update the observation with scans
        obs.set({"scans": kwargs["scans"]})
        # Synchronize all scans to ensure source references and activity status are consistent
        obs.scans.activate_all(obs)
        logger.info(f"Created observation '{data['name']}' from dictionary with {len(kwargs['scans'].get_items())} scans and {len(calculated_data)} calculated datasets")
        return obs

    def __repr__(self) -> str:
        """Return a string representation of the Observation object."""
        return (f"Observation(name='{self.name}', code='{self.code}', sources={self.sources}, "
                f"telescopes={self.telescopes}, frequencies={self.frequencies}, "
                f"scans={self.scans}, isactive={self.isactive}, "
                f"observation_type={self.observation_type}, "
                f"calculated_data={len(self.calculated_data)} items)")