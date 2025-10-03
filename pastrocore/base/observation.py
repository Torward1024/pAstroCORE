# base/observation.py
import pandas as pd
import numpy as np
from astropy.time import Time
from typing import Optional, Dict
from common.base.baseentity import BaseEntity
from common.utils.validation import check_type, check_non_empty_string
from common.utils.logging_setup import logger
from .sources import Sources
from .telescopes import Telescopes
from .frequencies import Frequencies
from .scans import Scans
from .data_structure import CalculatedDataStructure
import astropy.units as u
import uuid
import base64
import io

class Observation(BaseEntity):
    """Base class representing an astronomical observation with sources, telescopes, frequencies, and scans.

    Encapsulates the structure and metadata of an observation, such as its unique code, type (VLBI or
    SINGLE_DISH), and associated entities. Manages calculated data using pandas DataFrames with metadata
    stored in df.attrs. Provides methods for validation, synchronization, and serialization using Parquet.

    Attributes:
        name (str): Unique identifier for the observation.
        code (str): Unique code for the observation.
        observation_type (str): Type of observation, either 'VLBI' or 'SINGLE_DISH'.
        sources (Sources): Collection of source objects observed.
        telescopes (Telescopes): Collection of telescope objects used.
        frequencies (Frequencies): Collection of intermediate frequency (IF) objects.
        scans (Scans): Collection of scan objects defining observation timing and targets.
        calculated_data (Dict[str, pd.DataFrame]): Dictionary storing calculated results as DataFrames.
        isactive (bool): Indicates whether the observation is active.
        _use_cache (bool): Flag to control caching behavior.
    """
    name: str
    code: str
    observation_type: str
    sources: Sources
    telescopes: Telescopes
    frequencies: Frequencies
    scans: Scans
    calculated_data: Dict[str, pd.DataFrame]
    _use_cache: bool

    def __init__(self, name: str = None, code: str = "OBS_DEFAULT", sources: Sources = None,
                 telescopes: Telescopes = None, frequencies: Frequencies = None,
                 scans: Scans = None, observation_type: str = "VLBI", 
                 calculated_data: Dict[str, pd.DataFrame] = None, isactive: bool = True,
                 use_cache: bool = False):
        """Initialize an Observation with code, entities, type, calculated data, and active status."""
        if name is None:
            name = f"obs_{uuid.uuid4().hex[:32]}"
        check_non_empty_string(name, "Name")
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
            for key, df in calculated_data.items():
                check_type(df, pd.DataFrame, f"Calculated data for key {key}")
        
        super().__init__(
            name=name,
            code=code,
            observation_type=observation_type,
            sources=sources if sources is not None else Sources(),
            telescopes=telescopes if telescopes is not None else Telescopes(),
            frequencies=frequencies if frequencies is not None else Frequencies(),
            scans=scans if scans is not None else Scans(),
            calculated_data=calculated_data if calculated_data is not None else {},
            isactive=isactive,
            use_cache=use_cache
        )
        
        if calculated_data is not None:
            for key, df in calculated_data.items():
                try:
                    self._validate_calculated_data_key(key, df)
                except ValueError as e:
                    logger.error(f"Validation failed for calculated_data key '{key}' in observation '{self.name}': {str(e)}")
                    raise
        
        logger.info(f"Initialized Observation '{name}' with type '{observation_type}'")

    def _validate_calculated_data_key(self, key: str, df: pd.DataFrame) -> None:
        """Validate the structure of a DataFrame for a specific calculated data key."""
        expected_columns = CalculatedDataStructure.get_columns(key)
        expected_metadata = CalculatedDataStructure.get_metadata_types(key)

        if expected_columns is None:
            logger.warning(f"Unknown calculated_data key '{key}' in observation '{self.name}'")
            return

        if not all(col in df.columns for col in expected_columns):
            missing_cols = [col for col in expected_columns if col not in df.columns]
            logger.error(f"Invalid DataFrame structure for key '{key}' in observation '{self.name}': missing columns {missing_cols}")
            raise ValueError(f"Invalid DataFrame structure for key '{key}': missing columns {missing_cols}")

        if not hasattr(df, "attrs"):
            logger.error(f"DataFrame for key '{key}' in observation '{self.name}' has no attrs for metadata")
            raise ValueError(f"DataFrame for key '{key}' has no attrs")
        
        for meta_key, meta_type in expected_metadata.items():
            if meta_key not in df.attrs:
                logger.error(f"Missing metadata '{meta_key}' for key '{key}' in observation '{self.name}'")
                raise ValueError(f"Missing metadata '{meta_key}' for key '{key}'")
            check_type(df.attrs[meta_key], meta_type, f"Metadata {meta_key} for {key}")

        logger.debug(f"Validated DataFrame structure for key '{key}' in observation '{self.name}'")

    def get_calculated_data_by_key(self, key: str) -> Optional[pd.DataFrame]:
        """Retrieve calculated data for a specific key as a pandas DataFrame."""
        check_non_empty_string(key, "Key")
        df = self.calculated_data.get(key)
        if df is not None:
            logger.debug(f"Retrieved calculated data '{key}' for observation '{self.name}'")
        else:
            logger.debug(f"No calculated data found for key '{key}' in observation '{self.name}'")
        return df

    def set_calculated_data_by_key(self, key: str, df: pd.DataFrame) -> None:
        """Set calculated data for a specific key as a pandas DataFrame."""
        check_non_empty_string(key, "Key")
        check_type(df, pd.DataFrame, "DataFrame")
        self._validate_calculated_data_key(key, df)
        new_data = self.calculated_data.copy()
        new_data[key] = df.copy()
        self.set({"calculated_data": new_data})
        logger.info(f"Stored calculated data '{key}' for observation '{self.name}'")

    def clear_calculated_data(self):
        """Clear all cached calculation data for this observation."""
        self.calculated_data.clear()
        logger.debug(f"Cleared calculated data for observation '{self.get_observation_code()}'")

    def to_dict(self) -> dict:
        """Convert the Observation object to a dictionary for serialization."""
        def convert_dataframe(df: pd.DataFrame, key: str) -> dict:
            """Convert a pandas DataFrame to a serializable dictionary with Parquet data."""
            converters = CalculatedDataStructure.get_converters(key) or {}
            df_copy = df.copy()
            
            for col, converter in converters.items():
                if col in df_copy.columns:
                    try:
                        df_copy[col] = df_copy[col].apply(converter)
                    except Exception as e:
                        logger.error(f"Failed to apply converter for column '{col}' in key '{key}' "
                                    f"of observation '{self.name}': {str(e)}")
                        raise
            
            metadata = df.attrs if hasattr(df, "attrs") else {}
            converted_metadata = {}
            for k, v in metadata.items():
                try:
                    if isinstance(v, Time):
                        converted_metadata[k] = v.isot if v.isscalar else v.isot.tolist()
                    elif isinstance(v, np.ndarray):
                        converted_metadata[k] = v.tolist()
                    elif isinstance(v, dict):
                        converted_metadata[k] = {
                            sk: sv.tolist() if isinstance(sv, np.ndarray) else sv
                            for sk, sv in v.items()
                        }
                    else:
                        converted_metadata[k] = v
                except Exception as e:
                    logger.error(f"Failed to convert metadata '{k}' for key '{key}' in "
                                f"observation '{self.name}': {str(e)}")
                    raise
            
            df_copy.attrs = converted_metadata
            buffer = io.BytesIO()
            try:
                df_copy.to_parquet(buffer, compression='snappy', engine="pyarrow", index=False)
            except Exception as e:
                logger.error(f"Failed to convert DataFrame for key '{key}' to Parquet in "
                            f"observation '{self.name}': {str(e)}")
                raise
                
            parquet_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
            
            return {
                "parquet_data": parquet_data,
                "metadata": converted_metadata
            }

        try:
            data = super().to_dict()
            data["calculated_data"] = {
                key: convert_dataframe(df, key) for key, df in self.calculated_data.items()
            }
            data["use_cache"] = self._use_cache
            logger.info(f"Converted observation '{self.name}' to dictionary")
            return data
        except Exception as e:
            logger.error(f"Failed to serialize observation '{self.name}': {str(e)}")
            raise

    @classmethod
    def from_dict(cls, data: dict) -> 'Observation':
        """Create an Observation object from a dictionary."""
        def restore_dataframe(calc_data: dict, key: str) -> pd.DataFrame:
            """Restore a pandas DataFrame from a serialized dictionary."""
            try:
                if "parquet_data" not in calc_data:
                    logger.error(f"Missing 'parquet_data' for calculated_data key '{key}'")
                    raise ValueError(f"Missing 'parquet_data' for calculated_data key '{key}'")
                
                try:
                    parquet_data = base64.b64decode(calc_data["parquet_data"])
                except Exception as e:
                    logger.error(f"Failed to decode parquet_data for key '{key}': {str(e)}")
                    raise ValueError(f"Invalid parquet_data for key '{key}': {str(e)}")
                
                buffer = io.BytesIO(parquet_data)
                try:
                    df = pd.read_parquet(buffer, engine="pyarrow")
                except Exception as e:
                    logger.error(f"Failed to read Parquet data for key '{key}': {str(e)}")
                    raise ValueError(f"Invalid Parquet data for key '{key}': {str(e)}")

                deserialization_converters = CalculatedDataStructure.get_deserialization_converters(key) or {}
                for col, converter in deserialization_converters.items():
                    if col in df.columns:
                        try:
                            df[col] = df[col].apply(converter)
                        except Exception as e:
                            logger.error(f"Failed to apply deserialization converter for column '{col}' in key '{key}': {str(e)}")
                            raise ValueError(f"Failed to apply deserialization converter for column '{col}' in key '{key}': {str(e)}")

                metadata = calc_data.get("metadata", {})
                restored_metadata = {}
                metadata_types = CalculatedDataStructure.get_metadata_types(key) or {}
                
                for meta_key, meta_value in metadata.items():
                    meta_type = metadata_types.get(meta_key)
                    try:
                        if meta_type is Time:
                            restored_metadata[meta_key] = Time(meta_value)
                        elif meta_type is float:
                            restored_metadata[meta_key] = float(meta_value)
                        elif meta_type is int:
                            restored_metadata[meta_key] = int(meta_value)
                        elif meta_type is dict and meta_key == "sources":
                            restored_metadata[meta_key] = {k: np.array(v) for k, v in meta_value.items()}
                        else:
                            restored_metadata[meta_key] = meta_value
                    except Exception as e:
                        logger.error(f"Failed to restore metadata '{meta_key}' for key '{key}': {str(e)}")
                        raise ValueError(f"Failed to restore metadata '{meta_key}' for key '{key}': {str(e)}")

                df.attrs = restored_metadata
                return df
            except Exception as e:
                logger.error(f"Failed to restore DataFrame for key '{key}': {str(e)}")
                raise

        try:
            if "name" not in data:
                logger.error("Missing 'name' field in dictionary for Observation")
                raise ValueError("Missing 'name' field in dictionary for Observation")
            
            check_non_empty_string(data["name"], "Observation name")
            
            # Process calculated_data with error handling
            calculated_data = {}
            for key, calc_data in data.get("calculated_data", {}).items():
                try:
                    calculated_data[key] = restore_dataframe(calc_data, key)
                except ValueError as e:
                    logger.error(f"Skipping invalid calculated_data key '{key}' due to error: {str(e)}")
                    continue  # Skip invalid calculated_data entries

            kwargs = {
                "name": data["name"],
                "code": data.get("code", "OBS_DEFAULT"),
                "observation_type": data.get("observation_type", "VLBI"),
                "sources": Sources.from_dict(data.get("sources", {})),
                "telescopes": Telescopes.from_dict(data.get("telescopes", {})),
                "frequencies": Frequencies.from_dict(data.get("frequencies", {})),
                "calculated_data": calculated_data,
                "isactive": data.get("isactive", True),
                "use_cache": data.get("use_cache", False),
            }
            
            obs = cls(**kwargs)
            kwargs["scans"] = Scans.from_dict(data.get("scans", {}), observation=obs)
            obs.set({"scans": kwargs["scans"]})
            obs.scans.activate_all(obs)
            logger.info(f"Created observation '{data['name']}' from dictionary with {len(kwargs['scans'].get_items())} scans")
            return obs
        except Exception as e:
            logger.error(f"Failed to deserialize observation from dictionary: {str(e)}")
            raise

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

    def get_calculated_data(self) -> Dict[str, pd.DataFrame]:
        """Retrieve all calculated data."""
        return self.get("calculated_data")

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
        """Retrieve the total observation duration in seconds by summing durations of active scans."""
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
            calculated_data={key: df.copy() for key, df in self.calculated_data.items()},
            isactive=self.isactive,
            use_cache=self._use_cache
        )

    def validate(self) -> bool:
        """Validate the observation's data for consistency and completeness."""
        if not self.name:
            logger.error("Observation name must be a non-empty string")
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
        for key, df in self.calculated_data.items():
            try:
                self._validate_calculated_data_key(key, df)
            except ValueError as e:
                logger.error(f"Validation failed for calculated_data key '{key}' in observation '{self.name}': {str(e)}")
                return False
        logger.info(f"Observation '{self.name}' validated successfully")
        return True

    def __repr__(self) -> str:
        """Return a string representation of the Observation object."""
        return (f"Observation(name='{self.name}', code='{self.code}', sources={self.sources}, "
                f"telescopes={self.telescopes}, frequencies={self.frequencies}, "
                f"scans={self.scans}, isactive={self.isactive}, "
                f"observation_type={self.observation_type}, "
                f"calculated_data={len(self.calculated_data)} DataFrames)")