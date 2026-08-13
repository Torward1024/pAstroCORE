# base/observation.py
import polars as pl
import numpy as np
from astropy.time import Time
from typing import Annotated, Any, Optional, Dict
from msb_arch.base.baseentity import BaseEntity
from pastrocore.base.result_store import CalculatedData
from msb_arch.utils.validation import Predicate, check_type, check_non_empty_string
from msb_arch.utils.logging_setup import logger
from .sources import Sources
from .telescopes import Telescopes
from .frequencies import Frequencies
from .scans import Scans
from .data_structure import CalculatedDataStructure
import astropy.units as u
import uuid
import base64
import io

#: What an observation may be. Named once, so the annotation and anything that offers
#: a choice read the same list.
OBSERVATION_TYPES = ("VLBI", "SINGLE_DISH")


class Observation(BaseEntity):
    """Base class representing an astronomical observation with sources, telescopes, frequencies, and scans.

    Encapsulates the structure and metadata of an observation, such as its unique code, type (VLBI or
    SINGLE_DISH), and associated entities. Manages calculated data using Polars DataFrames with metadata
    stored in a dictionary under the same key. Provides methods for validation, synchronization, and serialization using Parquet.

    Attributes:
        name (str): Unique identifier for the observation.
        code (str): Unique code for the observation.
        observation_type (str): Type of observation, either 'VLBI' or 'SINGLE_DISH'.
        sources (Sources): Collection of source objects observed.
        telescopes (Telescopes): Collection of telescope objects used.
        frequencies (Frequencies): Collection of intermediate frequency (IF) objects.
        scans (Scans): Collection of scan objects defining observation timing and targets.
        calculated_data (Dict[str, Dict]): Dictionary with keys mapping to {'data': pl.DataFrame, 'metadata': Dict}.
        isactive (bool): Indicates whether the observation is active.
        _use_cache (bool): Flag to control caching behavior.
    """
    name: str
    code: str
    # One of two, on the annotation. The check in `__init__` guarded construction and left
    # `set` and `from_dict` to accept anything -- and `from_dict` is how a saved project brings
    # a value back.
    observation_type: Annotated[str, Predicate(lambda value: value in OBSERVATION_TYPES,
                                               f"one of {sorted(OBSERVATION_TYPES)}")]
    sources: Sources
    telescopes: Telescopes
    frequencies: Frequencies
    scans: Scans
    # Not `Dict[str, Dict]` any more: it is a `CalculatedData`, which behaves like the
    # mapping it replaces but reads a result from disk only when one is asked for.
    calculated_data: Any
    _use_cache: bool

    def __init__(self, name: str = None, code: str = "OBS_DEFAULT", sources: Sources = None,
                 telescopes: Telescopes = None, frequencies: Frequencies = None,
                 scans: Scans = None, observation_type: str = "VLBI", 
                 calculated_data: Dict[str, Dict] = None, 
                 isactive: bool = True, use_cache: bool = False):
        """Initialize an Observation with code, entities, type, calculated data, and active status."""
        if name is None:
            name = f"obs_{uuid.uuid4().hex[:32]}"
        check_non_empty_string(name, "Name")
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
            for key, calc_dict in calculated_data.items():
                check_type(calc_dict, dict, f"Calculated data dictionary for key {key}")
                check_type(calc_dict.get("data"), pl.DataFrame, f"Data for key {key}")
                check_type(calc_dict.get("metadata", {}), dict, f"Metadata for key {key}")

        super().__init__(
            name=name,
            code=code,
            observation_type=observation_type,
            sources=sources if sources is not None else Sources(),
            telescopes=telescopes if telescopes is not None else Telescopes(),
            frequencies=frequencies if frequencies is not None else Frequencies(),
            scans=scans if scans is not None else Scans(),
            # Wrapped once, here, so every later reader gets the lazy mapping without
            # knowing about it. An observation not yet part of a saved project has no
            # store, and then this is simply a dictionary that lives in memory.
            calculated_data=CalculatedData(name, resident=dict(calculated_data or {})),
            isactive=isactive,
            use_cache=use_cache
        )
        
        if calculated_data is not None:
            for key, calc_dict in calculated_data.items():
                try:
                    self._validate_calculated_data_key(key, calc_dict.get("data"), calc_dict.get("metadata", {}))
                except ValueError as e:
                    logger.error("Validation failed for calculated_data key '%s' in observation '%s': %s", key, self.name, str(e))
                    raise
        
        logger.info("Initialized Observation '%s' with type '%s'", name, observation_type)

    def _validate_calculated_data_key(self, key: str, df: pl.DataFrame, metadata: Dict) -> None:
        """Validate the structure of a DataFrame and metadata for a specific calculated data key."""
        expected_columns = CalculatedDataStructure.get_columns(key)
        expected_metadata = CalculatedDataStructure.get_metadata_types(key)

        if expected_columns is None:
            logger.warning("Unknown calculated_data key '%s' in observation '%s'", key, self.name)
            return

        if df is None or not isinstance(df, pl.DataFrame):
            logger.error("Invalid DataFrame for key '%s' in observation '%s': DataFrame is None or not a Polars DataFrame", key, self.name)
            raise ValueError(f"Invalid DataFrame for key '{key}': DataFrame is None or not a Polars DataFrame")

        if not all(col in df.columns for col in expected_columns):
            missing_cols = [col for col in expected_columns if col not in df.columns]
            logger.error("Invalid DataFrame structure for key '%s' in observation '%s': missing columns %s", key, self.name, missing_cols)
            raise ValueError(f"Invalid DataFrame structure for key '{key}': missing columns {missing_cols}")

        for meta_key, meta_type in expected_metadata.items():
            if meta_key not in metadata:
                logger.error("Missing metadata '%s' for key '%s' in observation '%s'", meta_key, key, self.name)
                raise ValueError(f"Missing metadata '{meta_key}' for key '{key}'")
            check_type(metadata[meta_key], meta_type, f"Metadata {meta_key} for {key}")

        logger.debug("Validated DataFrame structure for key '%s' in observation '%s'", key, self.name)

    def get_calculated_data_by_key(self, key: str) -> Optional[Dict[str, any]]:
        """Retrieve calculated data and metadata for a specific key as a dictionary."""
        check_non_empty_string(key, "Key")
        calc_dict = self.calculated_data.get(key)
        if calc_dict is not None:
            logger.debug("Retrieved calculated data '%s' for observation '%s'", key, self.name)
            return {"data": calc_dict.get("data"), "metadata": calc_dict.get("metadata", {})}
        else:
            logger.debug("No calculated data found for key '%s' in observation '%s'", key, self.name)
            return {}

    def scan_calculated_data(self, key: str) -> Optional[pl.LazyFrame]:
        """A lazy view of one calculated result, so a filter reaches the read.

        Args:
            key (str): The calculation whose result is wanted.

        Returns:
            Optional[pl.LazyFrame]: A view that reads nothing until it is collected, or None
                if the observation has no such result.

        Notes:
            - This is the counterpart of `get_calculated_data_by_key` for a consumer that is
              about to filter. Reading the whole result and then discarding most of it costs
              both the read and the memory to hold what was discarded; a filter applied to
              this view is pushed into the parquet read instead, so the rows that fail it are
              never materialised.
            - Falls back to a lazy view of what is held in memory when the result has not been
              written yet, so a caller does not have to know where the result currently lives.
        """
        check_non_empty_string(key, "Key")
        results = self.calculated_data
        if hasattr(results, "scan"):
            try:
                return results.scan(key)
            except KeyError:
                logger.debug("No calculated data found for key '%s' in observation '%s'", key, self.name)
                return None

        stored = (results or {}).get(key)
        frame = stored.get("data") if stored else None
        return frame.lazy() if frame is not None else None

    def get_calculated_metadata(self, key: str) -> Dict[str, any]:
        """Return what was recorded about how a result was produced, without reading it.

        Args:
            key (str): The calculation whose metadata is wanted.

        Returns:
            Dict[str, any]: The metadata, empty if there is no such result.

        Notes:
            - Several plots need only the metadata -- the sources a track covers, the
              frequency a beam was computed at. Reaching it through the result read every row
              off disk to arrive at a handful of entries.
        """
        check_non_empty_string(key, "Key")
        results = self.calculated_data
        if hasattr(results, "metadata"):
            return results.metadata(key)
        stored = (results or {}).get(key)
        return (stored or {}).get("metadata", {}) or {}

    def is_result_stale(self, key: str) -> Optional[bool]:
        """Report whether a result was computed from a different configuration than the one now.

        Args:
            key (str): The calculation's store key.

        Returns:
            Optional[bool]: True if the inputs it depends on have changed, False if they have
                not, and None if it cannot be told -- a result saved before results carried
                fingerprints is neither stale nor fresh, and claiming either would be a guess.

        Notes:
            - A state, not an event. Nothing here raises, blocks or recalculates; a stale
              result stays perfectly readable and what to do about it is the user's decision.
        """
        from pastrocore.base import freshness

        return freshness.is_stale(self, key)

    def stale_results(self) -> tuple:
        """Return the keys of every result whose inputs have changed.

        Returns:
            tuple: Sorted store keys, empty when nothing is known to be stale.

        Notes:
            - Reads no result: the answer comes from the metadata beside them, so asking costs
              a directory listing rather than the project.
        """
        from pastrocore.base import freshness

        return freshness.stale_results(self)

    def set_calculated_data_by_key(self, key: str, df: pl.DataFrame, metadata: Dict = None) -> None:
        """Set calculated data and metadata for a specific key as a Polars DataFrame and dictionary."""
        check_non_empty_string(key, "Key")
        check_type(df, pl.DataFrame, "DataFrame")
        if metadata is None:
            metadata = {}
        check_type(metadata, dict, "Metadata")
        self._validate_calculated_data_key(key, df, metadata)
        # Set in place rather than copying the mapping and re-assigning it. The copy loaded
        # every stored result to store one, which is exactly the cost this format exists to
        # avoid -- and on a project of a year of observations it would load all of them.
        self.calculated_data[key] = {"data": df, "metadata": metadata}
        self._invalidate_cache()
        logger.info("Stored calculated data '%s' for observation '%s'", key, self.name)

    def clear_calculated_data(self):
        """Clear all cached calculation data and metadata for this observation."""
        self.calculated_data.clear()
        logger.debug("Cleared calculated data for observation '%s'", self.get_observation_code())

    def to_dict(self, with_results: bool = True) -> dict:
        """Convert the Observation object to a dictionary for serialization.

        Args:
            with_results (bool): Embed the calculated results as base64 parquet, which is the
                single-file format. Defaults to True so that anything calling `to_dict()` --
                including msb_arch, which calls it with no arguments -- behaves as it did.

        Notes:
            - The directory format passes False. Results then live in their own parquet files
              beside the model, so the mapping this returns stays small and reading it does not
              mean reading gigabytes: the single-file form of the small test project is 97.1%
              base64, with the model under 7 KB of 230.
        """
        def convert_dataframe(df: pl.DataFrame, key: str, metadata: Dict) -> dict:
            """Convert a Polars DataFrame and metadata to a serializable dictionary with Parquet data."""
            converters = CalculatedDataStructure.get_converters(key) or {}
            df_copy = df.clone()

            for col, converter in converters.items():
                if col in df_copy.columns:
                    try:
                        df_copy = df_copy.with_columns(pl.col(col).map_elements(converter, return_dtype=pl.Float64))
                    except Exception as e:
                        logger.error("Failed to apply converter for column '%s' in key '%s' of observation '%s': %s", col, key, self.name, str(e))
                        raise

            converted_metadata = {}
            for k, v in metadata.items():
                try:
                    if k in converters:
                        converted_metadata[k] = converters[k](v)
                    elif isinstance(v, np.ndarray):
                        converted_metadata[k] = v.tolist()
                    else:
                        converted_metadata[k] = v
                except Exception as e:
                    logger.error("Failed to convert metadata '%s' for key '%s' in observation '%s': %s", k, key, self.name, str(e))
                    raise

            buffer = io.BytesIO()
            try:
                df_copy.write_parquet(buffer, use_pyarrow=True)
                return {
                    "data": base64.b64encode(buffer.getvalue()).decode('utf-8'),
                    "metadata": converted_metadata
                }
            except Exception as e:
                logger.error("Failed to serialize DataFrame for key '%s' in observation '%s': %s", key, self.name, str(e))
                raise

        try:
            calculated_data = {}
            failed_keys = []
            for key, calc_dict in (self.calculated_data.items() if with_results else []):
                try:
                    calc_data = convert_dataframe(calc_dict["data"], key, calc_dict.get("metadata", {}))
                    calculated_data[key] = calc_data
                    logger.debug("Successfully serialized calculated_data key '%s' for observation '%s'", key, self.name)
                except Exception as e:
                    logger.warning("Skipping calculated_data key '%s' due to serialization error: %s", key, str(e))
                    failed_keys.append(key)
                    continue

            if failed_keys:
                logger.warning("Failed to serialize %s calculated_data keys: %s", len(failed_keys), failed_keys)

            if not with_results:
                calculated_data = {}

            data = {
                "name": self.name,
                "code": self.code,
                "observation_type": self.observation_type,
                "sources": self.sources.to_dict(),
                "telescopes": self.telescopes.to_dict(),
                "frequencies": self.frequencies.to_dict(),
                "scans": self.scans.to_dict(),
                "calculated_data": calculated_data,
                "isactive": self.isactive,
                "use_cache": self._use_cache
            }
            logger.debug("Serialized observation '%s' to dictionary with %s calculated_data entries", self.name, len(calculated_data))
            return data
        except Exception as e:
            logger.error("Failed to serialize observation '%s' to dictionary: %s", self.name, str(e))
            raise

    @classmethod
    def from_dict(cls, data: dict) -> 'Observation':
        """Create an Observation object from a dictionary."""
        def restore_dataframe(calc_data: dict, key: str) -> dict:
            """Restore a Polars DataFrame and its metadata from serialized data."""
            try:
                buffer = io.BytesIO(base64.b64decode(calc_data["data"]))
                df = pl.read_parquet(buffer, use_pyarrow=True)
                deserialization_converters = CalculatedDataStructure.get_deserialization_converters(key) or {}

                for col, converter in deserialization_converters.items():
                    if col in df.columns:
                        try:
                            df = df.with_columns(pl.col(col).map_elements(converter, return_dtype=pl.Object))
                        except Exception as e:
                            logger.error("Failed to apply deserialization converter for column '%s' in key '%s': %s", col, key, str(e))
                            raise ValueError(f"Failed to apply deserialization converter for column '{col}' in key '{key}': {str(e)}")

                metadata = calc_data.get("metadata", {})
                restored_metadata = {}
                metadata_types = CalculatedDataStructure.get_metadata_types(key) or {}

                for meta_key, meta_value in metadata.items():
                    meta_type = metadata_types.get(meta_key)
                    try:
                        if meta_type is float and meta_value is not None:
                            restored_metadata[meta_key] = float(meta_value)
                        elif meta_type is int and meta_value is not None:
                            restored_metadata[meta_key] = int(meta_value)
                        elif meta_type is dict and meta_key in deserialization_converters:
                            restored_metadata[meta_key] = deserialization_converters[meta_key](meta_value)
                        else:
                            restored_metadata[meta_key] = meta_value
                    except Exception as e:
                        logger.error("Failed to restore metadata '%s' for key '%s': %s", meta_key, key, str(e))
                        raise ValueError(f"Failed to restore metadata '{meta_key}' for key '{key}': {str(e)}")

                return {"data": df, "metadata": restored_metadata}
            except Exception as e:
                logger.error("Failed to restore DataFrame for key '%s': %s", key, str(e))
                raise

        try:
            if "name" not in data:
                logger.error("Missing 'name' field in dictionary for Observation")
                raise ValueError("Missing 'name' field in dictionary for Observation")

            check_non_empty_string(data["name"], "Observation name")

            calculated_data = {}
            failed_keys = []
            for key, calc_data in data.get("calculated_data", {}).items():
                try:
                    calc_dict = restore_dataframe(calc_data, key)
                    calculated_data[key] = calc_dict
                    logger.debug("Successfully deserialized calculated_data key '%s' for observation '%s'", key, data['name'])
                except Exception as e:
                    logger.warning("Skipping calculated_data key '%s' due to deserialization error: %s", key, str(e))
                    failed_keys.append(key)
                    continue

            if failed_keys:
                logger.warning("Failed to deserialize %s calculated_data keys: %s", len(failed_keys), failed_keys)

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
            logger.info("Created observation '%s' from dictionary with %s scans", data['name'], len(kwargs['scans'].get_items()))
            return obs
        except Exception as e:
            logger.error("Failed to deserialize observation from dictionary: %s", str(e))
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

    def get_calculated_data(self) -> Dict[str, Dict]:
        """Retrieve all calculated data."""
        return self.get("calculated_data")

    def get_start_datetime(self) -> Optional[Time]:
        """Retrieve the earliest start time of active scans."""
        active_scans = self.scans.get_active_scans(self)
        if not active_scans:
            logger.debug("No active scans found for observation '%s'", self.name)
            return None
        start_time = min(scan.get_start() for scan in active_scans)
        logger.debug("Retrieved start datetime %s for observation '%s'", start_time.isot, self.name)
        return start_time

    def get_duration(self) -> Optional[int]:
        """Retrieve the total observation duration in seconds by summing durations of active scans."""
        active_scans = self.scans.get_active_scans(self)
        if not active_scans:
            logger.debug("No active scans found for observation '%s'", self.name)
            return None
        total_duration = sum(scan.get_duration() for scan in active_scans)
        logger.debug("Retrieved total duration %s seconds for observation '%s'", total_duration, self.name)
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
            calculated_data={key: {"data": calc_dict["data"].clone(), "metadata": calc_dict["metadata"].copy()}
                            for key, calc_dict in self.calculated_data.items()},
            isactive=self.isactive,
            use_cache=self._use_cache
        )

    def validate(self) -> bool:
        """Validate the observation's data for consistency and completeness."""
        if not self.name:
            logger.error("Observation name must be a non-empty string")
            return False
        if self.observation_type not in ["VLBI", "SINGLE_DISH"]:
            logger.warning("Invalid observation type: %s", self.observation_type)
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
                        logger.error("Scan overlap detected for telescope %s: [%s, %s] vs [%s, %s]", tel_code, prev_start.isot, prev_end.isot, scan_start.isot, scan_end.isot)
                        return False
                telescope_scans[tel_code].append((scan_start, scan_end))
        for key, calc_dict in self.calculated_data.items():
            try:
                self._validate_calculated_data_key(key, calc_dict.get("data"), calc_dict.get("metadata", {}))
            except ValueError as e:
                logger.error("Validation failed for calculated_data key '%s' in observation '%s': %s", key, self.name, str(e))
                return False
        logger.info("Observation '%s' validated successfully", self.name)
        return True

    def __repr__(self) -> str:
        """Return a string representation of the Observation object."""
        return (f"Observation(name='{self.name}', code='{self.code}', sources={self.sources}, "
                f"telescopes={self.telescopes}, frequencies={self.frequencies}, "
                f"scans={self.scans}, isactive={self.isactive}, "
                f"observation_type={self.observation_type}, "
                f"calculated_data={len(self.calculated_data)} entries)")