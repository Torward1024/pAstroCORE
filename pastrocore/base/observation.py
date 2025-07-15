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

    def get_calculated_data_by_key(self, key: str) -> Any:
        """Retrieve calculated data for a specific key."""
        check_non_empty_string(key, "Key")
        data = self.calculated_data.get(key)
        if data is not None:
            logger.debug(f"Retrieved calculated data '{key}' for observation '{self.name}'")
        else:
            logger.debug(f"No calculated data found for key '{key}' in observation '{self.name}'")
        return data

    def set_calculated_data_by_key(self, key: str, data: Any) -> None:
        """Set calculated data for a specific key."""
        check_non_empty_string(key, "Key")
        new_data = self.calculated_data.copy()
        new_data[key] = data
        self.set({"calculated_data": new_data})
        logger.info(f"Stored calculated data '{key}' for observation '{self.name}'")

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

        Handles special serialization for astropy.time.Time arrays in calculated_data['times'],
        numpy.ndarray in calculated_data['telescope_positions'], and boolean arrays in 
        calculated_data['source_visibility'], ensuring all data is JSON-serializable.

        Raises:
            TypeError: If an object in calculated_data cannot be serialized to JSON.
        """
        def convert_quantity(obj):
            try:
                if isinstance(obj, u.Quantity):
                    return obj.value.tolist() if hasattr(obj.value, 'tolist') else float(obj.value)
                elif isinstance(obj, np.ndarray):
                    # Handle numpy arrays, including object arrays and nested arrays
                    if obj.dtype == np.object_ or np.issubdtype(obj.dtype, np.ndarray):
                        return [convert_quantity(item) for item in obj]
                    return obj.tolist()
                elif isinstance(obj, Time):
                    # Handle astropy.time.Time, which may be a single time or array
                    return obj.isot if obj.isscalar else obj.isot.tolist()
                elif isinstance(obj, (bool, int, float, str)):
                    return obj
                elif isinstance(obj, dict):
                    return {k: convert_quantity(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [convert_quantity(item) for item in obj]
                elif hasattr(obj, 'tolist'):
                    return obj.tolist()
                else:
                    logger.error(f"Cannot serialize object of type {type(obj)}: {obj}")
                    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            except Exception as e:
                logger.error(f"Serialization error for object {obj}: {str(e)}")
                raise

        try:
            logger.debug(f"Serializing calculated_data: {self.calculated_data}")
            data = super().to_dict()
            data["calculated_data"] = convert_quantity(self.calculated_data)
            logger.info(f"Converted observation '{self.name}' to dictionary")
            return data
        except Exception as e:
            logger.error(f"Failed to serialize observation '{self.name}': {str(e)}")
            raise
        
    @classmethod
    def from_dict(cls, data: dict) -> 'Observation':
        """
        Create an Observation object from a dictionary.

        Restores calculated_data according to specified formats, handling astropy.time.Time,
        numpy.ndarray, and astropy.units.Quantity as needed.

        Args:
            data (dict): Dictionary containing observation data.

        Returns:
            Observation: Deserialized Observation object.

        Raises:
            ValueError: If critical data fields are missing or invalid.
            TypeError: If data structure is invalid.
        """
        def restore_calculated_data(calculated_data: Dict[str, Any]) -> Dict[str, Any]:
            """
            Restore calculated_data according to specified formats in data_formats.txt.

            Args:
                calculated_data (Dict[str, Any]): Raw calculated data dictionary.

            Returns:
                Dict[str, Any]: Restored calculated data with proper types.

            Raises:
                ValueError: If data format is invalid.
                TypeError: If data structure is unexpected.
            """
            restored = {}
            for key, value in calculated_data.items():
                if not isinstance(value, dict) or "data" not in value:
                    logger.error(f"Invalid structure for {key}: expected dict with 'data' key, got {type(value)}")
                    raise ValueError(f"Invalid structure for {key} in calculated_data")

                restored_data = {}
                metadata = value.get("metadata", {})
                data = value.get("data", {})

                if key == "times":
                    restored_metadata = {}
                    for meta_key, meta_value in metadata.items():
                        if meta_key in ("time_step", "time_threshold"):
                            restored_metadata[meta_key] = float(meta_value)
                        elif meta_key in ("start_time", "end_time"):
                            if isinstance(meta_value, (int, float)):
                                restored_metadata[meta_key] = Time(meta_value, format="mjd")
                            elif isinstance(meta_value, str):
                                restored_metadata[meta_key] = Time(meta_value)
                            else:
                                logger.error(f"Invalid type for {meta_key} in times.metadata: {type(meta_value)}")
                                raise ValueError(f"Invalid {meta_key} in times.metadata")
                        elif meta_key == "scan_count":
                            restored_metadata[meta_key] = int(meta_value)
                        else:
                            restored_metadata[meta_key] = meta_value
                        logger.debug(f"Restored {meta_key} in times.metadata: {meta_value}")

                    if not isinstance(data, dict):
                        logger.error(f"Expected dict for times.data, got {type(data)}")
                        raise TypeError(f"Invalid times.data structure")
                    for source_name, scans in data.items():
                        if not isinstance(scans, dict):
                            logger.error(f"Expected dict for scans in source {source_name}, got {type(scans)}")
                            raise TypeError(f"Invalid scans structure for source {source_name}")
                        restored_scans = {}
                        for scan_name, times in scans.items():
                            try:
                                if isinstance(times, (list, tuple)):
                                    restored_scans[scan_name] = Time([t if isinstance(t, str) else float(t) for t in times], format="mjd" if all(isinstance(t, (int, float)) for t in times) else None)
                                elif isinstance(times, str):
                                    restored_scans[scan_name] = Time(times)
                                else:
                                    logger.error(f"Invalid time format in scan {scan_name}: {type(times)}")
                                    raise ValueError(f"Invalid time format in scan {scan_name}")
                                logger.debug(f"Restored times for scan {scan_name} in source {source_name}")
                            except Exception as e:
                                logger.error(f"Failed to convert times for scan {scan_name}: {str(e)}")
                                raise ValueError(f"Invalid time data in scan {scan_name}")
                        restored_data[source_name] = restored_scans
                    restored[key] = {"metadata": restored_metadata, "data": restored_data}

                elif key in ("telescope_positions", "interpolated_orbits"):
                    restored_metadata = metadata  # No specific processing for metadata
                    if not isinstance(data, dict):
                        logger.error(f"Expected dict for {key}.data, got {type(data)}")
                        raise TypeError(f"Invalid {key}.data structure")
                    for scan_name, telescopes in data.items():
                        if not isinstance(telescopes, dict):
                            logger.error(f"Expected dict for telescopes in scan {scan_name}, got {type(telescopes)}")
                            raise TypeError(f"Invalid telescopes structure in scan {scan_name}")
                        restored_telescopes = {}
                        for telescope_code, positions in telescopes.items():
                            try:
                                restored_telescopes[telescope_code] = np.array(positions) * u.m
                                logger.debug(f"Restored {key} for {telescope_code} in scan {scan_name}")
                            except Exception as e:
                                logger.error(f"Failed to convert {key} for {telescope_code}: {str(e)}")
                                raise ValueError(f"Invalid {key} data for {telescope_code}")
                        restored_data[scan_name] = restored_telescopes
                    restored[key] = {"metadata": restored_metadata, "data": restored_data}

                elif key == "source_visibility":
                    restored_metadata = metadata
                    if not isinstance(data, dict):
                        logger.error(f"Expected dict for source_visibility.data, got {type(data)}")
                        raise TypeError(f"Invalid source_visibility.data structure")
                    for source_name, scans in data.items():
                        if not isinstance(scans, dict):
                            logger.error(f"Expected dict for scans in source {source_name}, got {type(scans)}")
                            raise TypeError(f"Invalid scans structure for source {source_name}")
                        restored_scans = {}
                        for scan_name, telescopes in scans.items():
                            if not isinstance(telescopes, dict):
                                logger.error(f"Expected dict for telescopes in scan {scan_name}, got {type(telescopes)}")
                                raise TypeError(f"Invalid telescopes structure in scan {scan_name}")
                            restored_telescopes = {}
                            for telescope_code, visibility in telescopes.items():
                                try:
                                    restored_telescopes[telescope_code] = np.array(visibility, dtype=bool)
                                    logger.debug(f"Restored source_visibility for {telescope_code} in scan {scan_name}")
                                except Exception as e:
                                    logger.error(f"Failed to convert source_visibility for {telescope_code}: {str(e)}")
                                    raise ValueError(f"Invalid source_visibility data for {telescope_code}")
                            restored_scans[scan_name] = restored_telescopes
                        restored_data[source_name] = restored_scans
                    restored[key] = {"metadata": restored_metadata, "data": restored_data}

                elif key == "beam_pattern":
                    restored_metadata = metadata
                    if not isinstance(data, dict):
                        logger.error(f"Expected dict for beam_pattern.data, got {type(data)}")
                        raise TypeError(f"Invalid beam_pattern.data structure")
                    for telescope_code, beam_data in data.items():
                        try:
                            restored_data[telescope_code] = np.array(beam_data)
                            logger.debug(f"Restored beam_pattern for {telescope_code}")
                        except Exception as e:
                            logger.error(f"Failed to convert beam_pattern for {telescope_code}: {str(e)}")
                            raise ValueError(f"Invalid beam_pattern data for {telescope_code}")
                    restored[key] = {"metadata": restored_metadata, "data": restored_data}

                elif key == "time_on_source":
                    restored_metadata = metadata
                    if not isinstance(data, dict):
                        logger.error(f"Expected dict for time_on_source.data, got {type(data)}")
                        raise TypeError(f"Invalid time_on_source.data structure")
                    for source_name, scans in data.items():
                        if not isinstance(scans, dict):
                            logger.error(f"Expected dict for scans in source {source_name}, got {type(scans)}")
                            raise TypeError(f"Invalid scans structure for source {source_name}")
                        restored_scans = {}
                        for scan_name, telescopes in scans.items():
                            if not isinstance(telescopes, dict):
                                logger.error(f"Expected dict for telescopes in scan {scan_name}, got {type(telescopes)}")
                                raise TypeError(f"Invalid telescopes structure in scan {scan_name}")
                            restored_telescopes = {}
                            for telescope_code, time_blocks in telescopes.items():
                                try:
                                    restored_blocks = []
                                    for block in time_blocks:
                                        if isinstance(block, (list, tuple)) and len(block) == 3:
                                            start, end, duration = block
                                            restored_block = [
                                                Time(start) if isinstance(start, str) else Time(start, format="mjd"),
                                                Time(end) if isinstance(end, str) else Time(end, format="mjd"),
                                                float(duration)
                                            ]
                                            restored_blocks.append(restored_block)
                                        else:
                                            logger.error(f"Invalid time block format in {telescope_code}: {block}")
                                            raise ValueError(f"Invalid time block format in {telescope_code}")
                                    restored_telescopes[telescope_code] = np.array(restored_blocks)
                                    logger.debug(f"Restored time_on_source for {telescope_code} in scan {scan_name}")
                                except Exception as e:
                                    logger.error(f"Failed to convert time_on_source for {telescope_code}: {str(e)}")
                                    raise ValueError(f"Invalid time_on_source data for {telescope_code}")
                            restored_scans[scan_name] = restored_telescopes
                        restored_data[source_name] = restored_scans
                    restored[key] = {"metadata": restored_metadata, "data": restored_data}

                elif key == "az_el":
                    restored_metadata = metadata
                    if not isinstance(data, dict):
                        logger.error(f"Expected dict for az_el.data, got {type(data)}")
                        raise TypeError(f"Invalid az_el.data structure")
                    for source_name, scans in data.items():
                        if not isinstance(scans, dict):
                            logger.error(f"Expected dict for scans in source {source_name}, got {type(scans)}")
                            raise TypeError(f"Invalid scans structure for source {source_name}")
                        restored_scans = {}
                        for scan_name, telescopes in scans.items():
                            if not isinstance(telescopes, dict):
                                logger.error(f"Expected dict for telescopes in scan {scan_name}, got {type(telescopes)}")
                                raise TypeError(f"Invalid telescopes structure in scan {scan_name}")
                            restored_telescopes = {}
                            for telescope_code, az_el_data in telescopes.items():
                                try:
                                    restored_telescopes[telescope_code] = np.array(az_el_data) * u.deg
                                    logger.debug(f"Restored az_el for {telescope_code} in scan {scan_name}")
                                except Exception as e:
                                    logger.error(f"Failed to convert az_el for {telescope_code}: {str(e)}")
                                    raise ValueError(f"Invalid az_el data for {telescope_code}")
                            restored_scans[scan_name] = restored_telescopes
                        restored_data[source_name] = restored_scans
                    restored[key] = {"metadata": restored_metadata, "data": restored_data}

                elif key == "sun_angles":
                    restored_metadata = metadata
                    if not isinstance(data, dict):
                        logger.error(f"Expected dict for sun_angles.data, got {type(data)}")
                        raise TypeError(f"Invalid sun_angles.data structure")
                    for source_name, scans in data.items():
                        if not isinstance(scans, dict):
                            logger.error(f"Expected dict for scans in source {source_name}, got {type(scans)}")
                            raise TypeError(f"Invalid scans structure for source {source_name}")
                        restored_scans = {}
                        for scan_name, telescopes in scans.items():
                            if not isinstance(telescopes, dict):
                                logger.error(f"Expected dict for telescopes in scan {scan_name}, got {type(telescopes)}")
                                raise TypeError(f"Invalid telescopes structure in scan {scan_name}")
                            restored_telescopes = {}
                            for telescope_code, angles in telescopes.items():
                                try:
                                    restored_telescopes[telescope_code] = np.array(angles) * u.deg
                                    logger.debug(f"Restored sun_angles for {telescope_code} in scan {scan_name}")
                                except Exception as e:
                                    logger.error(f"Failed to convert sun_angles for {telescope_code}: {str(e)}")
                                    raise ValueError(f"Invalid sun_angles data for {telescope_code}")
                            restored_scans[scan_name] = restored_telescopes
                        restored_data[source_name] = restored_scans
                    restored[key] = {"metadata": restored_metadata, "data": restored_data}

                elif key == "synthesized_beam":
                    restored_metadata = {
                        "time_step": float(metadata.get("time_step", 0.0)),
                        "scan_count": int(metadata.get("scan_count", 0)),
                        "freq_names": metadata.get("freq_names", [])
                    }
                    if not isinstance(data, dict):
                        logger.error(f"Expected dict for synthesized_beam.data, got {type(data)}")
                        raise TypeError(f"Invalid synthesized_beam.data structure")
                    for source_name, scans in data.items():
                        if not isinstance(scans, dict):
                            logger.error(f"Expected dict for scans in source {source_name}, got {type(scans)}")
                            raise TypeError(f"Invalid scans structure for source {source_name}")
                        restored_scans = {}
                        for scan_name, freqs in scans.items():
                            if not isinstance(freqs, dict):
                                logger.error(f"Expected dict for frequencies in scan {scan_name}, got {type(freqs)}")
                                raise TypeError(f"Invalid frequencies structure in scan {scan_name}")
                            restored_freqs = {}
                            for freq_name, beam_data in freqs.items():
                                try:
                                    restored_freqs[freq_name] = np.array(beam_data)
                                    logger.debug(f"Restored synthesized_beam for {freq_name} in scan {scan_name}")
                                except Exception as e:
                                    logger.error(f"Failed to convert synthesized_beam for {freq_name}: {str(e)}")
                                    raise ValueError(f"Invalid synthesized_beam data for {freq_name}")
                            restored_scans[scan_name] = restored_freqs
                        restored_data[source_name] = restored_scans
                    restored[key] = {"metadata": restored_metadata, "data": restored_data}
                
                elif key == "uv_coverage":
                    restored_metadata = {
                        "time_step": float(metadata.get("time_step", 0.0)),
                        "scan_count": int(metadata.get("scan_count", 0))
                    }
                    if not isinstance(data, dict):
                        logger.error(f"Expected dict for uv_coverage.data, got {type(data)}")
                        raise TypeError(f"Invalid uv_coverage.data structure")
                    for source_name, scans in data.items():
                        if not isinstance(scans, dict):
                            logger.error(f"Expected dict for scans in source {source_name}, got {type(scans)}")
                            raise TypeError(f"Invalid scans structure for source {source_name}")
                        restored_scans = {}
                        for scan_name, baselines in scans.items():
                            if not isinstance(baselines, dict):
                                logger.error(f"Expected dict for baselines in scan {scan_name}, got {type(baselines)}")
                                raise TypeError(f"Invalid baselines structure in scan {scan_name}")
                            restored_baselines = {}
                            for baseline, uvw in baselines.items():
                                try:
                                    restored_baselines[baseline] = np.array(uvw)
                                    logger.debug(f"Restored uv_coverage for {baseline} in scan {scan_name}")
                                except Exception as e:
                                    logger.error(f"Failed to convert baseline_projections for {baseline}: {str(e)}")
                                    raise ValueError(f"Invalid baseline_projections data for {baseline}")
                            restored_scans[scan_name] = restored_baselines
                        restored_data[source_name] = restored_scans
                    restored[key] = {"metadata": restored_metadata, "data": restored_data}

                elif key == "baseline_projections":
                    restored_metadata = metadata
                    if not isinstance(data, dict):
                        logger.error(f"Expected dict for baseline_projections.data, got {type(data)}")
                        raise TypeError(f"Invalid baseline_projections.data structure")
                    for source_name, scans in data.items():
                        if not isinstance(scans, dict):
                            logger.error(f"Expected dict for scans in source {source_name}, got {type(scans)}")
                            raise TypeError(f"Invalid scans structure for source {source_name}")
                        restored_scans = {}
                        for scan_name, baselines in scans.items():
                            if not isinstance(baselines, dict):
                                logger.error(f"Expected dict for baselines in scan {scan_name}, got {type(baselines)}")
                                raise TypeError(f"Invalid baselines structure in scan {scan_name}")
                            restored_baselines = {}
                            for baseline, projections in baselines.items():
                                try:
                                    restored_baselines[baseline] = np.array(projections)
                                    logger.debug(f"Restored baseline_projections for {baseline} in scan {scan_name}")
                                except Exception as e:
                                    logger.error(f"Failed to convert baseline_projections for {baseline}: {str(e)}")
                                    raise ValueError(f"Invalid baseline_projections data for {baseline}")
                            restored_scans[scan_name] = restored_baselines
                        restored_data[source_name] = restored_scans
                    restored[key] = {"metadata": restored_metadata, "data": restored_data}

                elif key == "mollweide_tracks":
                    restored_metadata = {
                        "time_step": float(metadata.get("time_step", 0.0)),
                        "scan_count": int(metadata.get("scan_count", 0)),
                        "sources": metadata.get("sources", [])
                    }
                    if not isinstance(data, dict):
                        logger.error(f"Expected dict for mollweide_tracks.data, got {type(data)}")
                        raise TypeError(f"Invalid mollweide_tracks.data structure")
                    for source_name, scans in data.items():
                        if not isinstance(scans, dict):
                            logger.error(f"Expected dict for scans in source {source_name}, got {type(scans)}")
                            raise TypeError(f"Invalid scans structure for source {source_name}")
                        restored_scans = {}
                        for scan_name, telescopes in scans.items():
                            if not isinstance(telescopes, dict):
                                logger.error(f"Expected dict for telescopes in scan {scan_name}, got {type(telescopes)}")
                                raise TypeError(f"Invalid telescopes structure in scan {scan_name}")
                            restored_telescopes = {}
                            for telescope_code, tracks in telescopes.items():
                                try:
                                    restored_telescopes[telescope_code] = np.array(tracks) * u.deg
                                    logger.debug(f"Restored mollweide_tracks for {telescope_code} in scan {scan_name}")
                                except Exception as e:
                                    logger.error(f"Failed to convert mollweide_tracks for {telescope_code}: {str(e)}")
                                    raise ValueError(f"Invalid mollweide_tracks data for {telescope_code}")
                            restored_scans[scan_name] = restored_telescopes
                        restored_data[source_name] = restored_scans
                    restored[key] = {"metadata": restored_metadata, "data": restored_data}

                else:
                    logger.warning(f"Unknown calculated_data key {key}, storing as-is")
                    restored[key] = value

            return restored

        try:
            kwargs = {
                "name": data["name"],
                "code": data["code"],
                "observation_type": data["observation_type"],
                "sources": Sources.from_dict(data["sources"]),
                "telescopes": Telescopes.from_dict(data["telescopes"]),
                "frequencies": Frequencies.from_dict(data["frequencies"]),
                "calculated_data": restore_calculated_data(data.get("calculated_data", {})),
                "isactive": data.get("isactive", True),
            }
            obs = cls(**kwargs)
            kwargs["scans"] = Scans.from_dict(data["scans"], observation=obs)
            obs.set({"scans": kwargs["scans"]})
            obs.scans.activate_all(obs)
            logger.info(f"Created observation '{data['name']}' from dictionary with {len(kwargs['scans'].get_items())} scans")
            return obs
        except Exception as e:
            logger.error(f"Failed to deserialize observation from dictionary: {str(e)}")
            raise

    def __repr__(self) -> str:
        """Return a string representation of the Observation object."""
        return (f"Observation(name='{self.name}', code='{self.code}', sources={self.sources}, "
                f"telescopes={self.telescopes}, frequencies={self.frequencies}, "
                f"scans={self.scans}, isactive={self.isactive}, "
                f"observation_type={self.observation_type}, "
                f"calculated_data={len(self.calculated_data)} items)")