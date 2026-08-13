from msb_arch.super.super import Super
from msb_arch.utils.logging_setup import logger

from pastrocore.base.sources import Source
from pastrocore.base.telescopes import Telescope, SpaceTelescope
from pastrocore.base.scans import Scan
from pastrocore.base.observation import Observation
from pastrocore.base import freshness
from pastrocore.base.data_structure import CalculatedDataStructure
from pastrocore.super.schedule_project import ScheduleProject

from typing import Dict, Any, Optional, Tuple, List, Callable, Union
from concurrent.futures import ThreadPoolExecutor
from scipy.special import j1
from functools import wraps

import astropy.units as u
from astropy.time import Time
from astropy.coordinates import ITRS, GCRS, CartesianRepresentation, SkyCoord, AltAz, get_sun, HADec

import numpy as np
import polars as pl

import threading
import time
import re
import os

from scipy.interpolate import CubicSpline
from numpy.polynomial import chebyshev

from erfa import ErfaWarning
import warnings
warnings.filterwarnings("ignore", category=ErfaWarning)
warnings.filterwarnings("ignore", category=Warning, module="astropy")

def time_execution(func):
    """Decorator to measure and log the execution time of calculation methods.

    Args:
        func: The function to decorate.

    Returns:
        Callable: Wrapped function that logs execution duration.
    """
    @wraps(func)
    def wrapper(self, obj, attributes):
        start_time = time.perf_counter()
        result = func(self, obj, attributes)
        end_time = time.perf_counter()
        duration = (end_time - start_time)
        calc_type = func.__name__.replace('_calculate_', '')
        obj_name = obj.name if isinstance(obj, ScheduleProject) else obj.get_observation_code()
        logger.info(f"Calculation '{calc_type}' for '{obj_name}' completed in {duration:.3f} s")
        return result
    return wrapper


class ScheduleCalculator(Super):
    """Scheduler implementation of Calculator for performing astronomical scheduling calculations.

    Provides methods to calculate telescope positions, source visibility, UV coverage, sun angles, and more for Observations and Projects.
    Supports caching of results and multi-threaded execution for efficiency.

    Attributes:
        manipulator: The Manipulator instance used to manage object interactions.
        _lock (threading.Lock): Thread lock for safe data caching.
    """
    OPERATION = "calculate"
    
    def __init__(self, manipulator: 'Manipulator'):
        """Initialize the ScheduleCalculator.

        Args:
            manipulator: The Manipulator instance providing method validation and execution capabilities.
        """
        super().__init__(manipulator)
        self._lock = threading.Lock()
        self._orbit_cache = {} 
        self._orbit_cache_lock = threading.Lock()
        logger.debug("Initialized Scheduling Calculator")
    
    def _get_active_components(
        self,
        obj: Observation,
        require_scans: bool = True,
        require_telescopes: bool = False,
        min_telescopes: int = 1
    ) -> Tuple[List[Scan], List[Telescope | SpaceTelescope], List[Source]]:
        """Retrieve active scans, telescopes, and sources from an Observation.

        Args:
            obj: The Observation to check.
            require_scans: If True, requires at least one active scan.
            require_telescopes: If True, requires at least min_telescopes active telescopes.
            min_telescopes: Minimum number of active telescopes required.

        Returns:
            Tuple[List[Scan], List[Telescope | SpaceTelescope], List[Source]]: Active components.

        Notes:
            Logs warnings if required components are missing.
        """
        scans = obj.get_scans().get_active_items() if require_scans else []
        telescopes = obj.get_telescopes().get_active_items()
        sources = obj.get_sources().get_active_items()
        
        obj_code = obj.get_observation_code()
        if require_scans and not scans:
            logger.warning("No active scans in observation '%s'", obj_code)
            return [], [], []
        if require_telescopes and len(telescopes) < min_telescopes:
            logger.warning("Insufficient active telescopes (%s < %s) in '%s'", len(telescopes), min_telescopes, obj_code)
            return [], [], []
        if not sources:
            logger.warning("No active sources in observation '%s'", obj_code)
            return [], [], []
        
        return scans, telescopes, sources

    def _get_cached_or_calculate(self, obj: Observation | ScheduleProject, store_key: str, calc_func, attributes: Dict[str, Any], metadata: Dict[str, Any]) -> pl.DataFrame:
        """Retrieve cached data or perform calculation and cache the result.

        Args:
            obj (Observation | ScheduleProject): The object to calculate for.
            store_key (str): Unique key for storing/retrieving calculated data.
            calc_func: The calculation function to execute if no valid cache exists.
            attributes (Dict[str, Any]): Calculation parameters (e.g., "recalculate", "time_step").
            metadata (Dict[str, Any]): Metadata to store with the result (e.g., time step, scan count).

        Returns:
            pl.DataFrame: Calculated or cached data as Polars DataFrame.

        Notes:
            - Returns cached result if "recalculate" is False and valid cache exists.
            - Uses thread-safe caching with a lock.
            - Logs warnings for empty or invalid results.
        """
        if not store_key:
            logger.error("Empty store_key provided for caching")
            return pl.DataFrame()

        recalculate = attributes.get("recalculate", False)
        time_step = attributes.get("time_step")
        obj_name = obj.name if isinstance(obj, ScheduleProject) else obj.get_observation_code()

        existing_data = obj.get_calculated_data_by_key(store_key)
        if existing_data and not recalculate:
            stored_step = existing_data["metadata"].get("time_step")
            if stored_step != time_step:
                # A different step is a different calculation, not a stale cache, so
                # recomputing is right. Said out loud because the alternative is a caller
                # who omitted `time_step` wondering why the call took 300 ms instead of one.
                logger.info("Cached '%s' for '%s' was computed with time_step=%s, not %s; "
                            "recalculating", store_key, obj_name, stored_step, time_step)
        if existing_data and not recalculate and existing_data["metadata"].get("time_step") == time_step:
            df = existing_data.get("data")
            if df is not None and not df.is_empty():
                logger.debug("Retrieved cached data for '%s' in '%s'", store_key, obj_name)
                return df
            logger.warning("Cached data for '%s' in '%s' is empty; recalculating", store_key, obj_name)

        logger.info("Calculating '%s' for '%s' (recalculate=%s)", store_key, obj_name, recalculate)
        result_df = calc_func(obj, attributes)
        if result_df.is_empty():
            logger.warning("Calculation for '%s' in '%s' returned empty result", store_key, obj_name)
        with self._lock:
            obj.set_calculated_data_by_key(store_key, result_df, metadata)
        return result_df

    def _process_object(
        self,
        obj: Observation | ScheduleProject,
        attributes: Dict[str, Any],
        calc_func: Callable[[Observation, Dict[str, Any]], pl.DataFrame],
        store_key: str,
        metadata: Dict[str, Any]
    ) -> pl.DataFrame:
        """Process an object (Observation or ScheduleProject) with parallel execution for projects.

        Args:
            obj: The object to process (Observation or ScheduleProject).
            attributes: Calculation parameters.
            calc_func: Function to perform calculation for a single Observation.
            store_key: Key for caching results.
            metadata: Metadata for cache validation.

        Returns:
            pl.DataFrame: Calculated results as Polars DataFrame.
        """
        obj_name = obj.name if isinstance(obj, ScheduleProject) else obj.get_observation_code()
        
        if isinstance(obj, ScheduleProject):
            # The project answers with its observations. `get_items()` hands back a mapping,
            # and iterating that yields the *names* -- which is how a whole-project calculation
            # called `get_observation_code()` on a string and came back empty.
            observations = obj.observations()
            if not observations:
                logger.warning("No observations in project '%s'", obj.name)
                return pl.DataFrame()
            dfs = []
            max_workers = min(len(observations), 4) if len(observations) > 1 else 1
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._process_object, obs, attributes, calc_func, store_key, metadata): obs.get_observation_code()
                    for obs in observations
                }
                for future in futures:
                    obs_code = futures[future]
                    df = future.result()
                    if not df.is_empty():
                        dfs.append(df)
            if dfs:
                combined_df = pl.concat(dfs)
                logger.info("Processed %s observations for '%s', combined into DF with %s rows", len(observations), obj_name, combined_df.height)
                return combined_df
            else:
                logger.warning("No data from observations in project '%s'", obj_name)
                return pl.DataFrame()
        
        result_df = self._get_cached_or_calculate(obj, store_key, calc_func, attributes, metadata)
        if result_df.is_empty():
            logger.warning("No data computed for '%s' with store_key '%s'", obj_name, store_key)
        return result_df
    
    def _store_result(self, obj, store_key: str, df: "pl.DataFrame", metadata: Dict[str, Any]) -> None:
        """Store a result together with metadata that describes *this* frame.

        Args:
            obj: The observation or project the result belongs to.
            store_key (str): Where to file it.
            df (pl.DataFrame): The frame just computed or read from cache.
            metadata (Dict[str, Any]): What is known about how it was produced.

        Notes:
            - This replaces a guard that read "store it if recalculating, or if nothing is
              stored yet", which could never correct anything: `_process_object` has already
              stored the frame with the placeholder metadata by the time the guard is reached,
              so the second condition is false exactly when the correction is needed. A real
              project was found holding `times.parquet` with 288 rows over one scan beside
              metadata saying `scan_count: 0` and `start_time: NaN`.
            - Written only when the metadata actually differs, because a write now reaches the
              disk and re-writing an unchanged result on every call would be a real cost.
        """
        # A result belongs to an observation. Asked for a whole project, `_process_object` has
        # already stored one per observation and what it returns is the combination -- which
        # has nowhere to live, since a project holds observations rather than results. Storing
        # it was attempted and raised, and the broad handler above turned a whole-project
        # calculation into an empty frame with a line in the log.
        if not hasattr(obj, "get_calculated_metadata"):
            logger.debug("%s holds no results of its own; the observations hold theirs",
                         type(obj).__name__)
            return

        # Stamped with a fingerprint of the inputs this calculation actually reads, so a later
        # session can tell whether the configuration has moved underneath it. Taken over the
        # subset in `freshness.DEPENDENCIES` rather than the whole observation: editing a scan
        # must not make a beam pattern stale, or every edit would stale everything and
        # "everything" would be all there is to recompute.
        stamped = freshness.stamp(obj, store_key, metadata)
        # Compared all the way down rather than with `==`: a metadata mapping may hold numpy
        # arrays -- Mollweide records the source coordinates it draws against -- and comparing
        # two of those gives an array rather than an answer.
        if freshness.same_metadata(stamped, obj.get_calculated_metadata(store_key)):
            return

        # The frame is already where it belongs -- `_get_cached_or_calculate` put it there,
        # with the metadata it had at the time. Only the stamp is missing, so only the stamp is
        # written. Storing the frame again to carry a corrected sidecar wrote every result's
        # parquet twice, and since 0.7.0 a store reaches the disk.
        if freshness.record_metadata(obj, store_key, stamped):
            return
        obj.set_calculated_data_by_key(store_key, df, stamped)

    @time_execution
    def _calculate_time_arrays(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate time arrays for active scans grouped by active sources with a configurable time threshold.

        Args:
            obj: The object to calculate time arrays for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "time_threshold", "store_key".

        Returns:
            pl.DataFrame: DataFrame with columns ["source_name", "scan_name", "time"] (time as float MJD).
        """
        try:
            time_step = attributes.get("time_step")
            time_threshold = attributes.get("time_threshold", 1.0)
            store_key = attributes.get("store_key", "times")
            
            if time_step is not None and time_step <= 0:
                logger.error("Invalid time_step: %s. Must be positive.", time_step)
                return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("times"))
            if time_threshold <= 0:
                logger.error("Invalid time_threshold: %s. Must be positive.", time_threshold)
                return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("times"))

            def calculate_times(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, _, sources = self._get_active_components(obs)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("times"))
                
                source_names = []
                scan_names = []
                times_array = []
                start_times = []
                end_times = []
                processed_scans = 0
                
                for scan in scans:
                    source = scan.get_source(obs)
                    if source is None or not source.isactive:
                        logger.debug("Skipping scan '%s' in '%s': no active source", scan.name, obs.get_observation_code())
                        continue
                    source_name = source.name
                    start_time = scan.get_start()
                    duration = scan.get_duration()
                    
                    start_mjd_rounded = round(start_time.mjd * 86400.0 / time_threshold) * time_threshold / 86400.0
                    duration_rounded = round(duration / time_threshold) * time_threshold
                    
                    if time_step is None:
                        mjd_values = np.array([start_mjd_rounded + (duration_rounded / 2) / 86400.0])
                    else:
                        n_points = int(np.ceil(duration_rounded / time_step))
                        time_offsets = np.linspace(0, duration_rounded, n_points, endpoint=False) / 86400.0
                        mjd_values = start_mjd_rounded + time_offsets
                    
                    if len(mjd_values) == 0:
                        logger.warning("Empty time array for scan '%s' in '%s'", scan.name, obs.get_observation_code())
                        continue
                    
                    source_names.append(np.full_like(mjd_values, source_name, dtype=object))
                    scan_names.append(np.full_like(mjd_values, scan.name, dtype=object))
                    times_array.append(mjd_values)
                    start_times.append(start_mjd_rounded)
                    end_times.append(start_mjd_rounded + duration_rounded / 86400.0)
                    processed_scans += 1
                
                if processed_scans == 0:
                    logger.warning("No valid scans processed in '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("times"))
                
                source_names = np.concatenate(source_names) if source_names else np.array([])
                scan_names = np.concatenate(scan_names) if scan_names else np.array([])
                times_array = np.concatenate(times_array) if times_array else np.array([])
                
                df = pl.DataFrame({
                    "source_name": source_names,
                    "scan_name": scan_names,
                    "time": times_array
                }, schema=CalculatedDataStructure.get_dtypes("times"))
                
                logger.info("Calculated time arrays for %s scans across %s sources in '%s', DF rows: %s", processed_scans, df['source_name'].unique().len(), obs.get_observation_code(), df.height)
                return df

            # No placeholders for anything the frame itself will answer. They were NaN and 0
            # here, and a frame stored beside them kept them -- so a result with 288 rows over
            # one scan advertised itself as covering nothing.
            metadata = {
                "time_step": time_step,
                "time_threshold": time_threshold,
                "start_time": None,
                "end_time": None,
                "scan_count": 0
            }

            df = self._process_object(obj, attributes, calculate_times, store_key, metadata)

            if not df.is_empty():
                metadata["start_time"] = float(df["time"].min())
                metadata["end_time"] = float(df["time"].max())
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)
            
            return df
        except Exception as e:
            logger.error("Failed to calculate time arrays for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("times"))

    @time_execution
    def _calculate_interpolated_orbits(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate interpolated orbit data for active SpaceTelescopes in active scans.

        Args:
            obj: The object to calculate orbits for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "recalculate".

        Returns:
            pl.DataFrame: DataFrame with columns ["time", "scan_name", "telescope_code", "x", "y", "z"] (time as float MJD, positions in meters).
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "interpolated_orbits")
            recalculate = attributes.get("recalculate", False)

            if time_step is not None and time_step <= 0:
                logger.error("Invalid time_step: %s. Must be positive.", time_step)
                return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("interpolated_orbits"))

            def calculate_orbits(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, telescopes, _ = self._get_active_components(obs, require_scans=True, require_telescopes=True)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("interpolated_orbits"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                if times_df.is_empty():
                    logger.warning("No time arrays available for observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("interpolated_orbits"))

                active_space_telescopes = [
                    tel for tel in telescopes
                    if isinstance(tel, SpaceTelescope) and not tel.get("use_kep")
                ]
                if not active_space_telescopes:
                    logger.debug("No active SpaceTelescopes with use_kep=False in '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("interpolated_orbits"))

                times_list = []
                scan_names = []
                telescope_codes = []
                x_list = []
                y_list = []
                z_list = []
                excluded_telescopes = []

                with self._orbit_cache_lock:
                    for scan in scans:
                        scan_name = scan.name
                        source = scan.get_source(obs)
                        if not source or not source.isactive:
                            logger.debug("Skipping scan '%s' due to inactive or missing source", scan_name)
                            continue

                        scan_times_df = times_df.filter(pl.col("scan_name") == scan_name)
                        if scan_times_df.is_empty():
                            logger.debug("No valid times for scan '%s' in source '%s'", scan_name, source.name)
                            continue

                        scan_times_mjd = scan_times_df["time"].to_numpy()
                        scan_telescopes = scan.get_telescopes(obs).get_active_items()
                        scan_space_telescopes = [
                            tel for tel in scan_telescopes
                            if isinstance(tel, SpaceTelescope) and not tel.get("use_kep")
                        ]
                        if not scan_space_telescopes:
                            logger.debug("No active SpaceTelescopes in scan '%s'", scan_name)
                            continue

                        start_time = scan.get_start().mjd
                        end_time = start_time + scan.get_duration() / 86400.0

                        for tel in scan_space_telescopes:
                            tel_code = tel.get_code()
                            orbit_file = tel.get_orbit()
                            if not orbit_file:
                                logger.warning("No orbit file for telescope '%s' in scan '%s'; excluding", tel_code, scan_name)
                                excluded_telescopes.append(tel_code)
                                continue

                            try:
                                positions = self._interpolate_orbit(tel, scan_times_mjd, start_time, end_time)
                                if positions.shape[0] != len(scan_times_mjd):
                                    logger.warning("Position data length mismatch for '%s' in scan '%s': got %s, expected %s", tel_code, scan_name, positions.shape[0], len(scan_times_mjd))
                                    positions = np.full((len(scan_times_mjd), 3), np.nan)
                                    positions[:min(positions.shape[0], len(scan_times_mjd))] = positions[:len(scan_times_mjd)]

                                if np.any(np.isnan(positions)):
                                    logger.warning("Orbit data for '%s' in scan '%s' contains NaN values", tel_code, scan_name)

                                n_times = len(scan_times_mjd)
                                times_list.append(scan_times_mjd)
                                scan_names.append(np.full(n_times, scan_name, dtype=object))
                                telescope_codes.append(np.full(n_times, tel_code, dtype=object))
                                x_list.append(positions[:, 0])
                                y_list.append(positions[:, 1])
                                z_list.append(positions[:, 2])
                            except ValueError as e:
                                logger.warning("Excluding telescope '%s' in scan '%s' due to interpolation error: %s", tel_code, scan_name, str(e))
                                excluded_telescopes.append(tel_code)

                if excluded_telescopes:
                    logger.info("Excluded %s telescopes: %s", len(set(excluded_telescopes)), ', '.join(set(excluded_telescopes)))

                if not times_list:
                    logger.warning("No valid orbit data computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("interpolated_orbits"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "x": np.concatenate(x_list),
                    "y": np.concatenate(y_list),
                    "z": np.concatenate(z_list)
                }, schema=CalculatedDataStructure.get_dtypes("interpolated_orbits"))

                logger.info("Calculated interpolated orbits for %s scans across %s telescopes in '%s', DF rows: %s", df['scan_name'].unique().len(), df['telescope_code'].unique().len(), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.observations())
            }
            df = self._process_object(obj, attributes, calculate_orbits, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate interpolated orbits for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("interpolated_orbits"))

    def _interpolate_orbit(self, telescope: SpaceTelescope, times_mjd: np.ndarray, start_time_mjd: float, end_time_mjd: float) -> np.ndarray:
        """Interpolate orbit data for a space telescope over a given array of times.

        Args:
            telescope (SpaceTelescope): The space telescope.
            times_mjd (np.ndarray): Array of times for interpolation (MJD as float).
            start_time_mjd (float): Start time of the required range (MJD).
            end_time_mjd (float): End time of the required range (MJD).

        Returns:
            np.ndarray: Interpolated positions as np.array([[x, y, z], ...]) in meters.
        """
        if telescope.get("use_kep"):
            logger.info("Skipping interpolation for '%s' as use_kep=True", telescope.get_code())
            return np.array([])

        orbit_file = telescope.get_orbit()
        if not orbit_file:
            logger.warning("No orbit file defined for telescope '%s'", telescope.get_code())
            return np.array([])

        try:
            if np.any(np.isnan(times_mjd)) or np.any(np.isinf(times_mjd)):
                logger.error("Invalid MJD values in times for '%s': %s", telescope.get_code(), times_mjd)
                return np.array([])

            orbit_data = self._load_orbit_data(orbit_file, start_time_mjd, end_time_mjd)
            if not orbit_data:
                logger.warning("No valid orbit data for '%s' in time range %s to %s", telescope.get_code(), start_time_mjd, end_time_mjd)
                return np.full((len(times_mjd), 3), np.nan)

            data_times_mjd = orbit_data["times"]
            positions = orbit_data["positions"]

            j2000_mjd = Time("2000-01-01T12:00:00", scale='utc').mjd
            interp_times = (times_mjd - j2000_mjd) * 86400.0
            data_times = (data_times_mjd - j2000_mjd) * 86400.0

            t_start = max((start_time_mjd - j2000_mjd) * 86400.0, data_times[0])
            t_end = min((end_time_mjd - j2000_mjd) * 86400.0, data_times[-1])
            valid_mask = (interp_times >= t_start) & (interp_times <= t_end)
            valid_interp_times = interp_times[valid_mask]

            # What the orbit file does not cover comes back NaN, and NaN reaches a plot as a
            # blank rather than as a complaint -- the same silent-empty failure as the
            # baseline projections defect. Say it once, plainly, naming both spans.
            uncovered = int(np.sum(~valid_mask))
            if uncovered:
                covered_from = j2000_mjd + data_times[0] / 86400.0
                covered_to = j2000_mjd + data_times[-1] / 86400.0
                logger.warning(
                    "The orbit of '%s' covers MJD %.5f to %.5f, which leaves %s of %s requested "
                    "times outside it (MJD %.5f to %.5f). Those positions are unknown, not zero",
                    telescope.get_code(), covered_from, covered_to, uncovered, len(times_mjd),
                    float(np.min(times_mjd)), float(np.max(times_mjd)))

            if not valid_interp_times.size:
                logger.warning("The orbit of '%s' does not cover any of the requested times; "
                               "its position over this scan is unknown", telescope.get_code())
                return np.full((len(times_mjd), 3), np.nan)

            unique_indices = np.unique(data_times, return_index=True)[1]
            filtered_times = data_times[unique_indices]
            filtered_positions = positions[unique_indices]

            if len(filtered_times) < 2:
                logger.warning("Too few points (%s) for interpolation for '%s'", len(filtered_times), telescope.get_code())
                return np.full((len(times_mjd), 3), np.nan)

            method = telescope.get("interpolation_method") or "linear"
            full_positions = np.full((len(times_mjd), 3), np.nan, dtype=float)

            if method == "chebyshev":
                degree = min(30, len(filtered_times) - 1)
                norm_times = 2 * (filtered_times - t_start) / (t_end - t_start) - 1
                norm_interp_times = 2 * (valid_interp_times - t_start) / (t_end - t_start) - 1
                pos_polynomials = [chebyshev.Chebyshev.fit(norm_times, pos, degree) for pos in filtered_positions.T]
                full_positions[valid_mask] = np.array([poly(norm_interp_times) for poly in pos_polynomials]).T
            elif method == "cubic_spline":
                full_positions[valid_mask] = np.array([CubicSpline(filtered_times, pos)(valid_interp_times) for pos in filtered_positions.T]).T
            else:
                full_positions[valid_mask] = np.array([
                    np.interp(valid_interp_times, filtered_times, pos, left=np.nan, right=np.nan)
                    for pos in filtered_positions.T
                ]).T

            if np.any(np.isnan(full_positions)):
                logger.warning("Interpolated positions for '%s' contain NaN values", telescope.get_code())

            logger.info("Interpolated orbit for '%s' using %s with %s points", telescope.get_code(), method, len(valid_interp_times))
            return full_positions

        except Exception as e:
            logger.error("Failed to interpolate orbit for '%s': %s", telescope.get_code(), str(e), exc_info=True)
            return np.full((len(times_mjd), 3), np.nan)

    def _load_orbit_data(self, orbit_file: str, start_time_mjd: Optional[float] = None, end_time_mjd: Optional[float] = None) -> Dict[str, np.ndarray]:
        """Load orbit data from a CCSDS OEM 2.0 styled file, optionally filtering by time range.

        Args:
            orbit_file (str): Path to the orbit file.
            start_time_mjd (Optional[float]): Start time for filtering data (MJD).
            end_time_mjd (Optional[float]): End time for filtering data (MJD).

        Returns:
            Dict[str, np.ndarray]: Dictionary containing times (MJD), positions (meters), and velocities (m/s).
        """
        if not os.path.isfile(orbit_file):
            raise FileNotFoundError(f"Orbit file '{orbit_file}' not found")

        try:
            with open(orbit_file, 'r') as f:
                lines = f.readlines()

            data_lines = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
            data_section = False
            valid_lines = []

            for line in data_lines:
                if "META_STOP" in line:
                    data_section = True
                    continue
                if not data_section:
                    continue
                if "COVARIANCE_START" in line:
                    break
                parts = re.split(r'\s+', line.strip())
                if len(parts) == 7:
                    valid_lines.append(line)

            if len(valid_lines) < 2:
                raise ValueError(f"Orbit file must contain at least 2 data points, got {len(valid_lines)}")

            time_strs = [re.split(r'\s+', line)[0] for line in valid_lines]
            times = Time(time_strs, format='isot', scale='utc')
            times_mjd = times.mjd

            positions = np.zeros((len(valid_lines), 3))
            velocities = np.zeros((len(valid_lines), 3))
            for i, line in enumerate(valid_lines):
                parts = re.split(r'\s+', line)
                x, y, z = map(float, parts[1:4])  # km -> m
                vx, vy, vz = map(float, parts[4:7])  # km/s -> m/s
                positions[i] = [x * 1000, y * 1000, z * 1000]
                velocities[i] = [vx * 1000, vy * 1000, vz * 1000]

            if np.any(np.isnan(positions)) or np.any(np.isnan(velocities)):
                logger.warning("Orbit file '%s' contains NaN values", orbit_file)
                return {}

            orbit_data = {
                "times": times_mjd,
                "positions": positions,
                "velocities": velocities
            }

            if start_time_mjd is not None and end_time_mjd is not None:
                mask = (times_mjd >= start_time_mjd) & (times_mjd <= end_time_mjd)
                if not np.any(mask):
                    logger.warning("No orbit data within time range %s to %s for file '%s'", start_time_mjd, end_time_mjd, orbit_file)
                    return {}
                orbit_data = {
                    "times": orbit_data["times"][mask],
                    "positions": orbit_data["positions"][mask],
                    "velocities": orbit_data["velocities"][mask]
                }

            logger.info("Loaded orbit data from '%s' with %s points", orbit_file, len(orbit_data['times']))
            return orbit_data

        except FileNotFoundError:
            logger.error("Orbit file '%s' not found", orbit_file)
            raise
        except ValueError as e:
            logger.error("Error parsing orbit file: %s", str(e))
            raise
        except Exception as e:
            logger.warning("Unexpected error loading orbit file '%s': %s", orbit_file, str(e), exc_info=True)
            return {}

    @time_execution
    def _calculate_telescope_positions(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate telescope positions in GCRS (J2000) for all active scans using times from time_arrays and interpolated orbits.

        Args:
            obj: The object to calculate positions for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "recalculate".

        Returns:
            pl.DataFrame: DataFrame with columns ["time", "scan_name", "telescope_code", "x", "y", "z"].
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "telescope_positions")
            recalculate = attributes.get("recalculate", False)

            def calculate_positions(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, telescopes, _ = self._get_active_components(obs)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_positions"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                if times_df.is_empty():
                    logger.error("No time data for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_positions"))

                has_orbit_telescopes = any(isinstance(tel, SpaceTelescope) and not tel.get("use_kep") for tel in telescopes)
                orbit_df = pl.DataFrame()
                if has_orbit_telescopes:
                    orbit_attrs = {"time_step": time_step, "store_key": "interpolated_orbits", "recalculate": False}
                    orbit_df = self._calculate_interpolated_orbits(obs, orbit_attrs)
                    logger.debug("Orbit data for '%s': %s", obs.get_observation_code(), not orbit_df.is_empty())

                times_list = []
                scan_names = []
                telescope_codes = []
                x_list = []
                y_list = []
                z_list = []
                excluded_telescopes = []

                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s' in observation '%s'", scan_name, obs.get_observation_code())
                            excluded_telescopes.extend([tel.get_code() for tel in scan.get_telescopes(obs).get_active_items()])
                            continue
                        scan_orbits = orbit_df.filter(pl.col("scan_name") == scan_name) if not orbit_df.is_empty() else pl.DataFrame()
                        futures[executor.submit(
                            self._process_scan_positions, scan, obs, scan_times, scan_orbits
                        )] = scan_name

                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result is not None:
                            times, scan_name_arr, tel_codes, x, y, z = scan_result
                            times_list.append(times)
                            scan_names.append(scan_name_arr)
                            telescope_codes.append(tel_codes)
                            x_list.append(x)
                            y_list.append(y)
                            z_list.append(z)
                        else:
                            scan = next(s for s in scans if s.name == scan_name)
                            excluded_telescopes.extend([tel.get_code() for tel in scan.get_telescopes(obs).get_active_items()])

                if excluded_telescopes:
                    logger.info("Excluded %s telescopes: %s", len(set(excluded_telescopes)), ', '.join(set(excluded_telescopes)))

                if not times_list:
                    logger.warning("No valid positions computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_positions"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "x": np.concatenate(x_list),
                    "y": np.concatenate(y_list),
                    "z": np.concatenate(z_list)
                }, schema=CalculatedDataStructure.get_dtypes("telescope_positions"))

                logger.info("Calculated positions for %s scans in '%s', DF rows: %s", df['scan_name'].unique().len(), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.observations())
            }
            df = self._process_object(obj, attributes, calculate_positions, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate telescope positions for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_positions"))

    def _process_scan_positions(self, scan: Scan, observation: Observation, times_mjd: np.ndarray, orbit_df: pl.DataFrame) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Process telescope positions for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            times_mjd (np.ndarray): Precomputed times (MJD as float).
            orbit_df (pl.DataFrame): Precomputed orbit data filtered by scan_name.

        Returns:
            Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]: 
                Tuple of (times, scan_names, telescope_codes, x, y, z) as Numpy arrays, or None if no valid data.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning("No active source for scan '%s' in observation '%s'", scan.name, observation.get_observation_code())
            return None

        scan_name = scan.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [tel for tel in scan_telescopes.get_items() if tel.isactive]
        if not active_telescopes:
            logger.warning("No active telescopes for scan '%s' starting at %s", scan_name, scan.get_start().isot)
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning("No valid times for scan '%s' in source '%s'", scan_name, source.name)
            return None
        
        obstime=Time(times_mjd, format="mjd", scale="utc")

        times_list = []
        scan_names = []
        telescope_codes = []
        x_list = []
        y_list = []
        z_list = []

        for tel in active_telescopes:
            tel_code = tel.get_code()
            if isinstance(tel, SpaceTelescope) and not tel.get("use_kep"):
                tel_orbit = orbit_df.filter(pl.col("telescope_code") == tel_code)
                if tel_orbit.is_empty():
                    logger.warning("No orbit data for telescope '%s' in scan '%s'", tel_code, scan_name)
                    continue
                positions = tel_orbit.select(["x", "y", "z"]).to_numpy()
                if len(positions) != n_times:
                    logger.warning("Orbit data length mismatch for '%s' in scan '%s': got %s, expected %s", tel_code, scan_name, len(positions), n_times)
                    positions = np.full((n_times, 3), np.nan)
                    positions[:min(len(positions), n_times)] = tel_orbit.select(["x", "y", "z"]).to_numpy()[:n_times]
            else:
                positions = self._compute_telescope_position(tel, times_mjd, obstime=obstime)
                if positions.shape[0] != n_times:
                    logger.warning("Position data length mismatch for '%s' in scan '%s': got %s, expected %s", tel_code, scan_name, positions.shape[0], n_times)
                    positions = np.full((n_times, 3), np.nan)
                    positions[:min(positions.shape[0], n_times)] = positions[:n_times]

            if np.all(np.isnan(positions)):
                logger.warning("All positions are NaN for telescope '%s' in scan '%s'", tel_code, scan_name)
                continue

            times_list.append(times_mjd)
            scan_names.append(np.full(n_times, scan_name, dtype=object))
            telescope_codes.append(np.full(n_times, tel_code, dtype=object))
            x_list.append(positions[:, 0])
            y_list.append(positions[:, 1])
            z_list.append(positions[:, 2])

        if not times_list:
            logger.warning("No valid positions computed for scan '%s'", scan_name)
            return None

        logger.debug("Computed %s telescope positions for scan '%s'", len(telescope_codes), scan_name)
        return (
            np.concatenate(times_list),
            np.concatenate(scan_names),
            np.concatenate(telescope_codes),
            np.concatenate(x_list),
            np.concatenate(y_list),
            np.concatenate(z_list)
        )

    def _compute_telescope_position(self, telescope: Telescope | SpaceTelescope, times_mjd: np.ndarray, obstime: Optional[Time] = None) -> np.ndarray:
        """Compute a telescope's GCRS position at specified times.

        Optimized version:
        - Fully vectorized Kepler solver (no np.vectorize).
        - Single matrix multiplication for orbital rotation.
        - Lazy J2000 MJD caching on the calculator instance.
        - Single Time object for obstime.

        Args:
            telescope (Telescope | SpaceTelescope): The telescope to compute position for.
            times_mjd (np.ndarray): Array of times for calculation (MJD as float).

        Returns:
            np.ndarray: GCRS coordinates (x, y, z) in meters, shape (n_times, 3).
        """
        n_times = len(times_mjd)
        nan_result = np.full((n_times, 3), np.nan, dtype=float)

        if not hasattr(self, "_j2000_mjd"):
            self._j2000_mjd = Time("2000-01-01T12:00:00").mjd

        try:
            if isinstance(telescope, Telescope) and not isinstance(telescope, SpaceTelescope):
                x, y, z = telescope.get_coordinates()
                res = telescope.get(["vx", "vy", "vz"])
                vx, vy, vz = res["vx"], res["vy"], res["vz"]

                dt = (times_mjd - self._j2000_mjd) * 86400.0

                itrs_coords = CartesianRepresentation(
                    x + vx * dt,
                    y + vy * dt,
                    z + vz * dt,
                    unit=u.m
                )

                if obstime is None:
                    obstime=Time(times_mjd, format="mjd", scale="utc")

                itrs = ITRS(itrs_coords, obstime=obstime)
                gcrs = itrs.transform_to(GCRS(obstime=obstime))

                pos = np.stack([gcrs.cartesian.x.value,
                                gcrs.cartesian.y.value,
                                gcrs.cartesian.z.value], axis=-1)

                if np.any(np.isnan(pos)):
                    logger.warning("Computed NaN position for ground telescope '%s'", telescope.get_code())
                return pos

            elif isinstance(telescope, SpaceTelescope) and telescope.get("use_kep"):
                kepler = telescope.get("kepler_elements")
                if kepler is None:
                    logger.warning("No Keplerian elements defined for telescope '%s'", telescope.get_code())
                    return nan_result

                a = kepler["a"]          # m
                e = kepler["e"]
                i = np.radians(kepler["i"])
                raan = np.radians(kepler["raan"])
                argp = np.radians(kepler["argp"])
                nu0 = np.radians(kepler["nu"])
                epoch = kepler["epoch"].mjd
                mu = kepler["mu"]
                n = np.sqrt(mu / a**3)

                dt = (times_mjd - epoch) * 86400.0
                M = nu0 + n * dt

                E = self._solve_kepler(M, e)

                # True anomaly
                cos_nu = (np.cos(E) - e) / (1 - e * np.cos(E))
                sin_nu = (np.sqrt(1 - e**2) * np.sin(E)) / (1 - e * np.cos(E))
                nu = np.arctan2(sin_nu, cos_nu)

                r = a * (1 - e**2) / (1 + e * np.cos(nu))

                # position in orbital plane (n_times, 3)
                p = np.column_stack((
                    r * np.cos(nu),
                    r * np.sin(nu),
                    np.zeros_like(r)
                ))

                # rotation matrix (constant per telescope)
                c_raan, s_raan = np.cos(raan), np.sin(raan)
                c_i, s_i = np.cos(i), np.sin(i)
                c_argp, s_argp = np.cos(argp), np.sin(argp)

                R1 = np.array([[c_raan, -s_raan, 0],
                               [s_raan,  c_raan, 0],
                               [0,       0,      1]], dtype=float)
                R2 = np.array([[1, 0,      0],
                               [0, c_i, -s_i],
                               [0, s_i,  c_i]], dtype=float)
                R3 = np.array([[c_argp, -s_argp, 0],
                               [s_argp,  c_argp, 0],
                               [0,       0,      1]], dtype=float)

                R = R1 @ R2 @ R3

                # vectorized rotation: p (n,3) row-vectors → pos = p @ R.T
                pos = p @ R.T

                if np.any(np.isnan(pos)):
                    logger.warning("Keplerian position for '%s' contains NaN", telescope.get_code())
                return pos

            else:
                logger.warning("Position for SpaceTelescope '%s' should be precomputed in interpolated_orbits", telescope.get_code())
                return nan_result

        except Exception as e:
            logger.warning("Unexpected error in computing position for '%s': %s", telescope.get_code(), str(e), exc_info=True)
            return nan_result

    def _solve_kepler(self, M: np.ndarray, e: float, tol: float = 1e-8, max_iter: int = 200) -> np.ndarray:
        """Solve Kepler's equation for an array of mean anomalies (fully vectorized Newton-Raphson).

        This replaces the original scalar + np.vectorize version and gives 10-100x speedup
        for typical VLBI time arrays (n_times > 1000).

        Args:
            M (np.ndarray): Mean anomaly array (radians).
            e (float): Eccentricity (< 1).
            tol (float): Convergence tolerance.
            max_iter (int): Maximum iterations per element.

        Returns:
            np.ndarray: Eccentric anomaly array (radians).
        """
        if e >= 1.0:
            raise ValueError("Eccentricity must be < 1 for elliptical orbit")

        M_arr = np.asarray(M, dtype=float)
        n = len(M_arr)

        # starter value
        if e < 0.9:
            x = M_arr.copy()
        else:
            x = np.full(n, np.pi, dtype=float)

        for _ in range(max_iter):
            f = x - e * np.sin(x) - M_arr
            df = 1.0 - e * np.cos(x)

            # safe division
            dx = np.zeros_like(x)
            valid = np.abs(df) > 1e-12
            dx[valid] = -f[valid] / df[valid]

            x += dx

            if np.all(np.abs(dx) < tol):
                break
        else:
            n_unconv = np.sum(np.abs(dx) >= tol)
            logger.warning(
                f"Kepler's equation did not converge for {n_unconv}/{n} points "
                f"(e={e:.4f}, max|dx|={np.max(np.abs(dx)):.2e})"
            )

        return x

    @time_execution
    def _calculate_source_visibility(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate source visibility for all active scans in the observation or project.

        Args:
            obj: The object to calculate visibility for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "position_store_key", "recalculate".

        Returns:
            pl.DataFrame: DataFrame with columns ["time", "scan_name", "telescope_code", "source_name", "visibility"].
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "source_visibility")
            position_store_key = attributes.get("position_store_key", "telescope_positions")
            recalculate = attributes.get("recalculate", False)

            def calculate_visibility(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, _, _ = self._get_active_components(obs)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("source_visibility"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                position_df = self._calculate_telescope_positions(obs, position_attrs)

                if times_df.is_empty() or position_df.is_empty():
                    logger.error("Missing time or position data for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("source_visibility"))

                times_list = []
                scan_names = []
                telescope_codes = []
                source_names = []
                is_visible_list = []

                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s' in observation '%s'", scan_name, obs.get_observation_code())
                            continue
                        scan_positions = position_df.filter(pl.col("scan_name") == scan_name)
                        futures[executor.submit(
                            self._process_source_visibility, scan, obs, scan_times, scan_positions
                        )] = scan_name

                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result is not None:
                            times, scan_name_arr, tel_codes, source_name_arr, is_visible = scan_result
                            times_list.append(times)
                            scan_names.append(scan_name_arr)
                            telescope_codes.append(tel_codes)
                            source_names.append(source_name_arr)
                            is_visible_list.append(is_visible)

                if not times_list:
                    logger.warning("No valid visibility data computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("source_visibility"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "source_name": np.concatenate(source_names),
                    "visibility": np.concatenate(is_visible_list)
                }, schema=CalculatedDataStructure.get_dtypes("source_visibility"))

                logger.info("Calculated visibility for %s scans across %s telescopes in '%s', DF rows: %s", df['scan_name'].unique().len(), df['telescope_code'].unique().len(), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.observations()),
                "position_store_key": position_store_key
            }
            df = self._process_object(obj, attributes, calculate_visibility, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate source visibility for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("source_visibility"))

    def _process_source_visibility(self, scan: Scan, observation: Observation, times_mjd: np.ndarray, position_df: pl.DataFrame) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Process source visibility for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            times_mjd (np.ndarray): Precomputed times (MJD as float).
            position_df (pl.DataFrame): Precomputed telescope positions filtered by scan_name.

        Returns:
            Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]: 
                Tuple of (times, scan_names, telescope_codes, source_names, is_visible) as Numpy arrays, or None if no valid data.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning("No active source for scan '%s' in observation '%s'", scan.name, observation.get_observation_code())
            return None

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [tel for tel in scan_telescopes.get_items() if tel.isactive]
        if not active_telescopes:
            logger.warning("No active telescopes for scan '%s' starting at %s", scan_name, scan.get_start().isot)
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning("No valid times for scan '%s' in source '%s'", scan_name, source_name)
            return None

        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
        obstime=Time(times_mjd, format="mjd", scale="utc")

        times_list = []
        scan_names = []
        telescope_codes = []
        source_names = []
        is_visible_list = []

        for tel in active_telescopes:
            tel_code = tel.get_code()
            tel_positions = position_df.filter(pl.col("telescope_code") == tel_code)
            if tel_positions.is_empty():
                logger.warning("No position data for telescope '%s' in scan '%s'", tel_code, scan_name)
                continue

            positions = tel_positions.select(["x", "y", "z"]).to_numpy()
            if len(positions) != n_times:
                logger.warning("Position data length mismatch for '%s' in scan '%s': got %s, expected %s", tel_code, scan_name, len(positions), n_times)
                positions = np.full((n_times, 3), np.nan)
                positions[:min(len(positions), n_times)] = tel_positions.select(["x", "y", "z"]).to_numpy()[:n_times]

            nan_positions = np.any(np.isnan(positions), axis=1)
            is_visible = np.full(n_times, False, dtype=bool)

            if isinstance(tel, SpaceTelescope):
                is_visible[~nan_positions] = True
            else:
                gcrs_coords = CartesianRepresentation(
                    x=positions[:, 0] * u.m,
                    y=positions[:, 1] * u.m,
                    z=positions[:, 2] * u.m
                )
                itrs = GCRS(gcrs_coords, obstime=obstime).transform_to(ITRS(obstime=obstime))
                locations = itrs.earth_location
                altaz = source_coord.transform_to(AltAz(obstime=obstime, location=locations))
                hadec = source_coord.transform_to(HADec(obstime=obstime, location=locations))
                el = altaz.alt.deg
                az = altaz.az.deg
                ha = hadec.ha.deg
                dec = hadec.dec.deg

                mount_type = tel.get("mount_type").value
                valid_positions = ~nan_positions
                if not np.any(valid_positions):
                    logger.warning("All positions are NaN for ground telescope '%s' in scan '%s'", tel_code, scan_name)
                    continue

                if mount_type == "AZIM":
                    el_range = tel.get_elevation_range()
                    az_range = tel.get_azimuth_range()
                    is_visible[valid_positions] = (
                        (float(el_range[0]) <= el[valid_positions]) &
                        (el[valid_positions] <= float(el_range[1])) &
                        (float(az_range[0]) <= az[valid_positions]) &
                        (az[valid_positions] <= float(az_range[1]))
                    )
                elif mount_type == "EQUA":
                    ha_range = tel.get_azimuth_range()
                    dec_range = tel.get_elevation_range()
                    is_visible[valid_positions] = (
                        (float(dec_range[0]) <= dec[valid_positions]) &
                        (dec[valid_positions] <= float(dec_range[1])) &
                        (float(ha_range[0]) <= ha[valid_positions]) &
                        (ha[valid_positions] <= float(ha_range[1]))
                    )
                else:
                    logger.warning("Unsupported mount type '%s' for telescope '%s' in scan '%s'", mount_type, tel_code, scan_name)
                    continue

            times_list.append(times_mjd)
            scan_names.append(np.full(n_times, scan_name, dtype=object))
            telescope_codes.append(np.full(n_times, tel_code, dtype=object))
            source_names.append(np.full(n_times, source_name, dtype=object))
            is_visible_list.append(is_visible)

            logger.debug("Computed visibility for telescope '%s' in scan '%s': %s visible points", tel_code, scan_name, np.sum(is_visible))

        if not times_list:
            logger.warning("No visibility data computed for scan '%s'", scan_name)
            return None

        return (
            np.concatenate(times_list),
            np.concatenate(scan_names),
            np.concatenate(telescope_codes),
            np.concatenate(source_names),
            np.concatenate(is_visible_list)
        )

    @time_execution
    def _calculate_uv_coverage(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate (u,v,w) coverage for all scans in the observation or project in geometric coordinates (meters).

        Args:
            obj: The object to calculate UV coverage for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "recalculate".

        Returns:
            pl.DataFrame: DataFrame with columns ["time", "scan_name", "baseline", "source_name", "u", "v", "w"].
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "uv_coverage")
            recalculate = attributes.get("recalculate", False)
            if "freq_name" in attributes:
                logger.info("Ignoring 'freq_name' attribute for UV coverage calculation in geometric coordinates")

            def calculate_uv(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, telescopes, _ = self._get_active_components(obs, require_telescopes=True, min_telescopes=2)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("uv_coverage"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": False}
                visibility_attrs = {"time_step": time_step, "store_key": "source_visibility", "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                position_df = self._calculate_telescope_positions(obs, position_attrs)
                visibility_df = self._calculate_source_visibility(obs, visibility_attrs)

                if times_df.is_empty() or position_df.is_empty() or visibility_df.is_empty():
                    logger.error("Missing time, position, or visibility data for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("uv_coverage"))

                times_list = []
                scan_names = []
                baselines = []
                source_names = []
                u_list = []
                v_list = []
                w_list = []

                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s' in observation '%s'", scan_name, obs.get_observation_code())
                            continue
                        scan_positions = position_df.filter(pl.col("scan_name") == scan_name)
                        scan_visibility = visibility_df.filter(pl.col("scan_name") == scan_name)
                        futures[executor.submit(
                            self._process_uv_coverage, scan, obs, scan_times, scan_positions, scan_visibility
                        )] = scan_name

                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result is not None:
                            times, scan_name_arr, baseline_arr, source_name_arr, u, v, w = scan_result
                            times_list.append(times)
                            scan_names.append(scan_name_arr)
                            baselines.append(baseline_arr)
                            source_names.append(source_name_arr)
                            u_list.append(u)
                            v_list.append(v)
                            w_list.append(w)

                if not times_list:
                    logger.warning("No valid UV coverage data computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("uv_coverage"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "source_name": np.concatenate(source_names),
                    "scan_name": np.concatenate(scan_names),
                    "baseline": np.concatenate(baselines),
                    "u": np.concatenate(u_list),
                    "v": np.concatenate(v_list),
                    "w": np.concatenate(w_list)
                }, schema=CalculatedDataStructure.get_dtypes("uv_coverage"))

                logger.info("Calculated UV coverage for %s scans across %s baselines in '%s', DF rows: %s", df['scan_name'].unique().len(), df['baseline'].unique().len(), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.observations())
            }
            df = self._process_object(obj, attributes, calculate_uv, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                metadata["baseline_count"] = df["baseline"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate UV coverage for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("uv_coverage"))

    def _process_uv_coverage(self, scan: Scan, observation: Observation, times_mjd: np.ndarray, position_df: pl.DataFrame, visibility_df: pl.DataFrame) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Process UV coverage for a single scan using vectorized computations in geometric coordinates (meters).

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            times_mjd (np.ndarray): Precomputed times (MJD as float).
            position_df (pl.DataFrame): Precomputed telescope positions filtered by scan_name.
            visibility_df (pl.DataFrame): Precomputed visibility data filtered by scan_name.

        Returns:
            Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]: 
                Tuple of (times, scan_names, baselines, source_names, u, v, w) as Numpy arrays, or None if no valid data.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning("No active source for scan '%s' in observation '%s'", scan.name, observation.get_observation_code())
            return None

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        if len(active_telescopes) < 2:
            logger.warning("Insufficient telescopes (%s) for UV coverage in scan '%s'", len(active_telescopes), scan_name)
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning("No valid times for scan '%s' in source '%s'", scan_name, source_name)
            return None

        tel_codes = [tel.get_code() for tel in active_telescopes]
        n_tels = len(tel_codes)

        positions = np.full((n_tels, n_times, 3), np.nan, dtype=float)
        visibility = np.full((n_tels, n_times), False, dtype=bool)

        for i, tel_code in enumerate(tel_codes):
            tel_positions = position_df.filter(pl.col("telescope_code") == tel_code)
            tel_visibility = visibility_df.filter(pl.col("telescope_code") == tel_code)
            if not tel_positions.is_empty() and len(tel_positions) == n_times:
                positions[i] = tel_positions.select(["x", "y", "z"]).to_numpy()
            else:
                logger.warning("Missing or mismatched position data for telescope '%s' in scan '%s'", tel_code, scan_name)
            if not tel_visibility.is_empty() and len(tel_visibility) == n_times:
                visibility[i] = tel_visibility["visibility"].to_numpy()
            else:
                logger.warning("Missing or mismatched visibility data for telescope '%s' in scan '%s'", tel_code, scan_name)

        try:
            uv_points = self._compute_uv_at_time(active_telescopes, times_mjd, source, visibility, positions)
        except Exception as e:
            logger.error("Failed to calculate UV coverage for scan '%s': %s", scan_name, str(e), exc_info=True)
            return None

        if not uv_points:
            logger.warning("No valid UV points computed for scan '%s'", scan_name)
            return None

        times_list = []
        scan_names = []
        baselines = []
        source_names = []
        u_list = []
        v_list = []
        w_list = []

        for pair, uvw in uv_points.items():
            valid_indices = ~np.any(np.isnan(uvw), axis=1)
            n_valid = np.sum(valid_indices)
            if n_valid == 0:
                logger.debug("No valid UVW points for baseline '%s' in scan '%s'", pair, scan_name)
                continue
            times_list.append(times_mjd[valid_indices])
            scan_names.append(np.full(n_valid, scan_name, dtype=object))
            baselines.append(np.full(n_valid, pair, dtype=object))
            source_names.append(np.full(n_valid, source_name, dtype=object))
            u_list.append(uvw[valid_indices, 0])
            v_list.append(uvw[valid_indices, 1])
            w_list.append(uvw[valid_indices, 2])

        if not times_list:
            logger.warning("No valid UV coverage data computed for scan '%s'", scan_name)
            return None

        logger.debug("Computed UV coverage for %s baselines in scan '%s'", len(uv_points), scan_name)
        return (
            np.concatenate(times_list),
            np.concatenate(scan_names),
            np.concatenate(baselines),
            np.concatenate(source_names),
            np.concatenate(u_list),
            np.concatenate(v_list),
            np.concatenate(w_list)
        )

    def _compute_uv_at_time(self, telescopes: List[Telescope | SpaceTelescope], times_mjd: np.ndarray, source: Optional[Source] = None, visibility: Optional[np.ndarray] = None, gcrs_positions: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
        """Compute UVW coordinates for multiple times in geometric coordinates (meters) using vectorized operations.

        Args:
            telescopes (List[Telescope | SpaceTelescope]): List of telescopes.
            times_mjd (np.ndarray): Array of observation times (MJD as float).
            source (Optional[Source]): Source for UV calculation.
            visibility (Optional[np.ndarray]): Visibility array of shape (n_telescopes, n_times).
            gcrs_positions (Optional[np.ndarray]): GCRS positions of shape (n_telescopes, n_times, 3).

        Returns:
            Dict[str, np.ndarray]: UVW coordinates in meters per baseline, formatted as {baseline: np.array([[u,v,w], ...])},
            where the array has shape (n_times, 3) and contains NaN for non-visible times or invalid positions.
        """
        if not telescopes or len(telescopes) < 2:
            logger.warning("Insufficient telescopes (%s) to compute (u,v,w)", len(telescopes))
            return {}
        if source is None:
            logger.warning("No source provided; cannot calculate (u,v,w)")
            return {}
        if visibility is None or gcrs_positions is None:
            logger.warning("Missing visibility or position data; cannot calculate (u,v,w)")
            return {}

        n_tels = len(telescopes)
        n_times = len(times_mjd)
        if visibility.shape != (n_tels, n_times):
            logger.error("Visibility shape %s does not match expected (%s, %s)", visibility.shape, n_tels, n_times)
            return {}
        if gcrs_positions.shape != (n_tels, n_times, 3):
            logger.error("Position shape %s does not match expected (%s, %s, 3)", gcrs_positions.shape, n_tels, n_times)
            return {}

        i, j = np.triu_indices(n_tels, k=1)
        pairs = [f"{telescopes[i].get_code()}-{telescopes[j].get_code()}" for i, j in zip(i, j)]
        n_pairs = len(pairs)

        baselines = gcrs_positions[i] - gcrs_positions[j]  # shape: (n_pairs, n_times, 3)

        vis_mask = visibility[i] & visibility[j]  # shape: (n_pairs, n_times)
        pos_nan = np.any(np.isnan(gcrs_positions), axis=2)  # shape: (n_tels, n_times)
        baseline_nan = pos_nan[i] | pos_nan[j]  # shape: (n_pairs, n_times)
        vis_mask = vis_mask & ~baseline_nan

        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
        ra = source_coord.ra.rad
        dec = source_coord.dec.rad
        cos_ra, sin_ra = np.cos(ra), np.sin(ra)
        cos_dec, sin_dec = np.cos(dec), np.sin(dec)
        rotation_matrix = np.array([
            [-sin_ra, cos_ra, 0],
            [-cos_ra * sin_dec, -sin_ra * sin_dec, cos_dec],
            [cos_ra * cos_dec, sin_ra * cos_dec, sin_dec]
        ])  # shape: (3, 3)

        uvw = np.einsum('ijk,lk->ijl', baselines, rotation_matrix)  # shape: (n_pairs, n_times, 3)
        uvw[~vis_mask] = np.nan

        uv_points = {}
        for pair_idx, pair in enumerate(pairs):
            uv_points[pair] = uvw[pair_idx]
            valid_count = np.sum(~np.any(np.isnan(uvw[pair_idx]), axis=1))
            logger.debug("Computed %s valid UVW points for baseline '%s' (total %s points)", valid_count, pair, n_times)

        if not uv_points:
            logger.warning("No valid UVW points computed for any baseline")
        return uv_points

    @time_execution
    def _calculate_sun_angles(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate angular separation between source and Sun for all active scans in geometric coordinates.

        Args:
            obj: The object to calculate sun angles for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "position_store_key", "visibility_store_key", "recalculate".

        Returns:
            pl.DataFrame: DataFrame with columns ["time", "scan_name", "telescope_code", "source_name", "angle"] (angles in degrees).
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "sun_angles")
            position_store_key = attributes.get("position_store_key", "telescope_positions")
            visibility_store_key = attributes.get("visibility_store_key", "source_visibility")
            recalculate = attributes.get("recalculate", False)

            def calculate_sun_angles(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, _, _ = self._get_active_components(obs)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("sun_angles"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": False}
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                position_df = self._calculate_telescope_positions(obs, position_attrs)
                visibility_df = self._calculate_source_visibility(obs, visibility_attrs)

                if times_df.is_empty() or position_df.is_empty() or visibility_df.is_empty():
                    logger.error("Missing time, position, or visibility data for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("sun_angles"))

                times_list = []
                scan_names = []
                telescope_codes = []
                source_names = []
                sun_angles_list = []

                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s' in observation '%s'", scan_name, obs.get_observation_code())
                            continue
                        scan_positions = position_df.filter(pl.col("scan_name") == scan_name)
                        scan_visibility = visibility_df.filter(pl.col("scan_name") == scan_name)
                        futures[executor.submit(
                            self._process_sun_angles, scan, obs, scan_times, scan_positions, scan_visibility
                        )] = scan_name

                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result is not None:
                            times, scan_name_arr, tel_codes, source_name_arr, sun_angles = scan_result
                            times_list.append(times)
                            scan_names.append(scan_name_arr)
                            telescope_codes.append(tel_codes)
                            source_names.append(source_name_arr)
                            sun_angles_list.append(sun_angles)

                if not times_list:
                    logger.warning("No valid sun angles computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("sun_angles"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "source_name": np.concatenate(source_names),
                    "angle": np.concatenate(sun_angles_list)
                }, schema=CalculatedDataStructure.get_dtypes("sun_angles"))

                logger.info("Calculated sun angles for %s scans across %s telescopes in '%s', DF rows: %s", df['scan_name'].unique().len(), df['telescope_code'].unique().len(), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.observations()),
                "position_store_key": position_store_key,
                "visibility_store_key": visibility_store_key
            }
            df = self._process_object(obj, attributes, calculate_sun_angles, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate sun angles for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("sun_angles"))

    def _process_sun_angles(self, scan: Scan, observation: Observation, times_mjd: np.ndarray, position_df: pl.DataFrame, visibility_df: pl.DataFrame) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Process Sun angles for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            times_mjd (np.ndarray): Precomputed times (MJD as float).
            position_df (pl.DataFrame): Precomputed telescope positions filtered by scan_name.
            visibility_df (pl.DataFrame): Precomputed visibility data filtered by scan_name.

        Returns:
            Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]: 
                Tuple of (times, scan_names, telescope_codes, source_names, sun_angles) as Numpy arrays, or None if no valid data.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning("No active source for scan '%s' in observation '%s'", scan.name, observation.get_observation_code())
            return None

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [tel for tel in scan_telescopes.get_items() if tel.isactive]
        if not active_telescopes:
            logger.warning("No active telescopes for scan '%s' starting at %s", scan_name, scan.get_start().isot)
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning("No valid times for scan '%s' in source '%s'", scan_name, source_name)
            return None

        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')

        times_list = []
        scan_names = []
        telescope_codes = []
        source_names = []
        sun_angles_list = []
        obstime=Time(times_mjd, format="mjd", scale="utc")

        sun_coord = get_sun(Time(times_mjd, format="mjd", scale="utc"))
        sun_vec = np.array([
            sun_coord.cartesian.x.value,
            sun_coord.cartesian.y.value,
            sun_coord.cartesian.z.value
        ]).T  # shape: (n_times, 3)

        for tel in active_telescopes:
            tel_code = tel.get_code()
            tel_positions = position_df.filter(pl.col("telescope_code") == tel_code)
            tel_visibility = visibility_df.filter(pl.col("telescope_code") == tel_code)
            if tel_positions.is_empty() or tel_visibility.is_empty():
                logger.warning("No position or visibility data for telescope '%s' in scan '%s'", tel_code, scan_name)
                continue

            positions = tel_positions.select(["x", "y", "z"]).to_numpy()
            visibility = tel_visibility["visibility"].to_numpy()
            if len(positions) != n_times or len(visibility) != n_times:
                logger.warning("Data length mismatch for '%s' in scan '%s': positions=%s, visibility=%s, expected %s", tel_code, scan_name, len(positions), len(visibility), n_times)
                positions = np.full((n_times, 3), np.nan)[:min(len(positions), n_times)] if len(positions) > 0 else np.full((n_times, 3), np.nan)
                visibility = np.full(n_times, False)[:min(len(visibility), n_times)] if len(visibility) > 0 else np.full(n_times, False)

            nan_positions = np.any(np.isnan(positions), axis=1)
            if np.mean(nan_positions) > 0.5:
                logger.warning(f"High NaN ratio ({np.mean(nan_positions):.2%}) in positions for telescope '{tel_code}' in scan '{scan_name}'")
                continue

            sun_angles = np.full(n_times, np.nan, dtype=float)
            is_visible = visibility & ~nan_positions

            if np.any(is_visible):
                if isinstance(tel, SpaceTelescope):
                    source_vec = np.array([
                        source_coord.cartesian.x.value,
                        source_coord.cartesian.y.value,
                        source_coord.cartesian.z.value
                    ])
                    source_norm = np.linalg.norm(source_vec)
                    if source_norm == 0 or np.isnan(source_norm):
                        logger.error("Invalid source vector for '%s' in scan '%s': norm=%s", source_name, scan_name, source_norm)
                        continue
                    source_unit = source_vec / source_norm
                    valid_sun_vec = sun_vec[is_visible]
                    sun_norm = np.linalg.norm(valid_sun_vec, axis=1)
                    valid = sun_norm > 0
                    if not np.any(valid):
                        logger.warning("No valid Sun vectors for space telescope '%s' in scan '%s'", tel_code, scan_name)
                        continue
                    sun_unit = valid_sun_vec[valid] / sun_norm[valid][:, np.newaxis]
                    source_unit_expanded = np.repeat([source_unit], np.sum(valid), axis=0)
                    cos_sep = np.sum(sun_unit * source_unit_expanded, axis=1)
                    cos_sep = np.clip(cos_sep, -1.0, 1.0)
                    sep = np.degrees(np.arccos(cos_sep))
                    sun_angles[is_visible] = np.where(valid, sep, np.nan)
                else:
                    gcrs_coords = CartesianRepresentation(
                        x=positions[:, 0] * u.m,
                        y=positions[:, 1] * u.m,
                        z=positions[:, 2] * u.m
                    )
                    itrs = GCRS(gcrs_coords, obstime=obstime).transform_to(ITRS(obstime=obstime))
                    locations = itrs.earth_location
                    sun_altaz = sun_coord.transform_to(AltAz(obstime=obstime, location=locations))
                    source_altaz = source_coord.transform_to(AltAz(obstime=obstime, location=locations))
                    sun_el = sun_altaz.alt.deg
                    sun_az = sun_altaz.az.deg
                    source_el = source_altaz.alt.deg
                    source_az = source_altaz.az.deg
                    cos_sep = np.sin(np.radians(source_el)) * np.sin(np.radians(sun_el)) + \
                            np.cos(np.radians(source_el)) * np.cos(np.radians(sun_el)) * \
                            np.cos(np.radians(source_az - sun_az))
                    cos_sep = np.clip(cos_sep, -1.0, 1.0)
                    sep = np.degrees(np.arccos(cos_sep))
                    sun_angles[is_visible] = sep[is_visible]

                logger.debug("Computed %s sun angles for telescope '%s' in scan '%s'", np.sum(is_visible), tel_code, scan_name)

            times_list.append(times_mjd)
            scan_names.append(np.full(n_times, scan_name, dtype=object))
            telescope_codes.append(np.full(n_times, tel_code, dtype=object))
            source_names.append(np.full(n_times, source_name, dtype=object))
            sun_angles_list.append(sun_angles)

        if not times_list:
            logger.warning("No sun angles computed for scan '%s'", scan_name)
            return None

        logger.debug("Computed sun angles for %s telescopes in scan '%s'", len(telescope_codes), scan_name)
        return (
            np.concatenate(times_list),
            np.concatenate(scan_names),
            np.concatenate(telescope_codes),
            np.concatenate(source_names),
            np.concatenate(sun_angles_list)
        )

    @time_execution
    def _calculate_az_el(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate azimuth/elevation or hour angle/declination angles for active ground telescopes in all active scans.

        Args:
            obj: The object to calculate az/el or ha/dec angles for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "position_store_key", "visibility_store_key", "recalculate".

        Returns:
            pl.DataFrame: DataFrame with columns ["time", "scan_name", "telescope_code", "source_name", "az_ha", "el_dec"] (angles in degrees).
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "az_el")
            position_store_key = attributes.get("position_store_key", "telescope_positions")
            visibility_store_key = attributes.get("visibility_store_key", "source_visibility")
            recalculate = attributes.get("recalculate", False)

            def calculate_az_el(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, telescopes, _ = self._get_active_components(obs, require_telescopes=True)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("az_el"))

                ground_telescopes = [tel for tel in telescopes if not isinstance(tel, SpaceTelescope)]
                if not ground_telescopes:
                    logger.debug("No ground telescopes in '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("az_el"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": False}
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                position_df = self._calculate_telescope_positions(obs, position_attrs)
                visibility_df = self._calculate_source_visibility(obs, visibility_attrs)

                if times_df.is_empty() or position_df.is_empty() or visibility_df.is_empty():
                    logger.error("Missing time, position, or visibility data for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("az_el"))

                times_list = []
                scan_names = []
                telescope_codes = []
                source_names = []
                az_ha_list = []
                el_dec_list = []

                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s' in observation '%s'", scan_name, obs.get_observation_code())
                            continue
                        scan_positions = position_df.filter(pl.col("scan_name") == scan_name)
                        scan_visibility = visibility_df.filter(pl.col("scan_name") == scan_name)
                        futures[executor.submit(
                            self._process_az_el, scan, obs, scan_times, scan_positions, scan_visibility
                        )] = scan_name

                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result is not None:
                            times, scan_name_arr, tel_codes, source_name_arr, az_ha, el_dec = scan_result
                            times_list.append(times)
                            scan_names.append(scan_name_arr)
                            telescope_codes.append(tel_codes)
                            source_names.append(source_name_arr)
                            az_ha_list.append(az_ha)
                            el_dec_list.append(el_dec)

                if not times_list:
                    logger.warning("No valid az/el or ha/dec angles computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("az_el"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "source_name": np.concatenate(source_names),
                    "az": np.concatenate(az_ha_list),
                    "el": np.concatenate(el_dec_list)
                }, schema=CalculatedDataStructure.get_dtypes("az_el"))

                logger.info("Calculated az/el or ha/dec for %s scans across %s telescopes in '%s', DF rows: %s", df['scan_name'].unique().len(), df['telescope_code'].unique().len(), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.observations()),
                "position_store_key": position_store_key,
                "visibility_store_key": visibility_store_key
            }
            df = self._process_object(obj, attributes, calculate_az_el, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate az/el or ha/dec for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("az_el"))

    def _process_az_el(self, scan: Scan, observation: Observation, times_mjd: np.ndarray, position_df: pl.DataFrame, visibility_df: pl.DataFrame) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Process az/el or ha/dec angles for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            times_mjd (np.ndarray): Precomputed times (MJD as float).
            position_df (pl.DataFrame): Precomputed telescope positions filtered by scan_name.
            visibility_df (pl.DataFrame): Precomputed visibility data filtered by scan_name.

        Returns:
            Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]: 
                Tuple of (times, scan_names, telescope_codes, source_names, az_ha, el_dec) as Numpy arrays, or None if no valid data.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning("No active source for scan '%s' in observation '%s'", scan.name, observation.get_observation_code())
            return None

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive and not isinstance(t, SpaceTelescope)]
        if not active_telescopes:
            logger.warning("No active ground telescopes for scan '%s' starting at %s", scan_name, scan.get_start().isot)
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning("No valid times for scan '%s' in source '%s'", scan_name, source_name)
            return None

        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')

        times_list = []
        scan_names = []
        telescope_codes = []
        source_names = []
        az_ha_list = []
        el_dec_list = []
        obstime=Time(times_mjd, format="mjd", scale="utc")

        for tel in active_telescopes:
            tel_code = tel.get_code()
            mount_type = tel.get("mount_type").value
            if mount_type not in ["AZIM", "EQUA"]:
                logger.warning("Unsupported mount type '%s' for telescope '%s' in scan '%s'", mount_type, tel_code, scan_name)
                continue

            tel_positions = position_df.filter(pl.col("telescope_code") == tel_code)
            tel_visibility = visibility_df.filter(pl.col("telescope_code") == tel_code)
            if tel_positions.is_empty() or tel_visibility.is_empty():
                logger.warning("No position or visibility data for telescope '%s' in scan '%s'", tel_code, scan_name)
                continue

            positions = tel_positions.select(["x", "y", "z"]).to_numpy()
            visibility = tel_visibility["visibility"].to_numpy()
            if len(positions) != n_times or len(visibility) != n_times:
                logger.warning("Data length mismatch for '%s' in scan '%s': positions=%s, visibility=%s, expected %s", tel_code, scan_name, len(positions), len(visibility), n_times)
                positions = np.full((n_times, 3), np.nan)[:min(len(positions), n_times)] if len(positions) > 0 else np.full((n_times, 3), np.nan)
                visibility = np.full(n_times, False)[:min(len(visibility), n_times)] if len(visibility) > 0 else np.full(n_times, False)

            nan_positions = np.any(np.isnan(positions), axis=1)
            if np.mean(nan_positions) > 0.5:
                logger.warning(f"High NaN ratio ({np.mean(nan_positions):.2%}) in positions for telescope '{tel_code}' in scan '{scan_name}'")
                continue

            az_ha = np.full(n_times, np.nan, dtype=float)
            el_dec = np.full(n_times, np.nan, dtype=float)
            is_visible = visibility & ~nan_positions

            if np.any(is_visible):
                gcrs_coords = CartesianRepresentation(
                    x=positions[:, 0] * u.m,
                    y=positions[:, 1] * u.m,
                    z=positions[:, 2] * u.m
                )
                itrs = GCRS(gcrs_coords, obstime=obstime).transform_to(ITRS(obstime=obstime))
                locations = itrs.earth_location
                if mount_type == "AZIM":
                    altaz = source_coord.transform_to(AltAz(obstime=obstime, location=locations))
                    az_ha[is_visible] = altaz.az.deg[is_visible]
                    el_dec[is_visible] = altaz.alt.deg[is_visible]
                else:  # EQUA
                    hadec = source_coord.transform_to(HADec(obstime=obstime, location=locations))
                    az_ha[is_visible] = hadec.ha.deg[is_visible]
                    el_dec[is_visible] = hadec.dec.deg[is_visible]

                logger.debug("Computed %s az/el or ha/dec angles for telescope '%s' in scan '%s'", np.sum(is_visible), tel_code, scan_name)

            times_list.append(times_mjd)
            scan_names.append(np.full(n_times, scan_name, dtype=object))
            telescope_codes.append(np.full(n_times, tel_code, dtype=object))
            source_names.append(np.full(n_times, source_name, dtype=object))
            az_ha_list.append(az_ha)
            el_dec_list.append(el_dec)

        if not times_list:
            logger.warning("No valid az/el or ha/dec angles computed for scan '%s'", scan_name)
            return None

        logger.debug("Computed az/el or ha/dec for %s telescopes in scan '%s'", len(telescope_codes), scan_name)
        return (
            np.concatenate(times_list),
            np.concatenate(scan_names),
            np.concatenate(telescope_codes),
            np.concatenate(source_names),
            np.concatenate(az_ha_list),
            np.concatenate(el_dec_list)
        )

    @time_execution
    def _calculate_telescope_az_el(self, obj: "Observation | ScheduleProject", attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate where each ground station must point to see a space telescope.

        Args:
            obj: The observation, or a project of them.
            attributes: Parameters including "target_telescope" -- the code of the spacecraft to
                point at -- and "time_step", "store_key", "position_store_key",
                "orbit_store_key", "recalculate".

        Returns:
            pl.DataFrame: Columns ["time", "target_code", "scan_name", "telescope_code", "az",
                "el", "range"], with angles in degrees and range in metres.

        Notes:
            - A calculation of its own that the user asks for by name, never part of an
              ordinary observation. Pointing at a spacecraft is a different question from
              observing a source, and a project with no spacecraft in it must pay nothing.
            - The target is named by a parameter rather than by a new kind of observation or a
              time-dependent `Source`. An observation already holds its telescopes; asking when
              one of them is visible from the others needs no new entity, and the request is
              already data, so one more attribute is the shape the architecture has.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "telescope_az_el")
            position_store_key = attributes.get("position_store_key", "telescope_positions")
            orbit_store_key = attributes.get("orbit_store_key", "interpolated_orbits")
            target_code = attributes.get("target_telescope")
            recalculate = attributes.get("recalculate", False)

            if not target_code:
                logger.error("No 'target_telescope' given; there is nothing to point at")
                return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_az_el"))

            def calculate_telescope_az_el(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                empty = pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_az_el"))
                scans, telescopes, _ = self._get_active_components(obs, require_telescopes=True)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return empty

                target = next((tel for tel in telescopes
                               if isinstance(tel, SpaceTelescope) and tel.get_code() == target_code), None)
                if target is None:
                    logger.warning("No active space telescope '%s' in observation '%s'",
                                   target_code, obs.get_observation_code())
                    return empty

                observers = [tel for tel in telescopes
                             if not isinstance(tel, SpaceTelescope) and tel.get_code() != target_code]
                if not observers:
                    logger.warning("No ground stations to see '%s' from in observation '%s'",
                                   target_code, obs.get_observation_code())
                    return empty

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": False}
                orbit_attrs = {"time_step": time_step, "store_key": orbit_store_key, "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                position_df = self._calculate_telescope_positions(obs, position_attrs)
                orbit_df = self._calculate_interpolated_orbits(obs, orbit_attrs)

                if times_df.is_empty() or position_df.is_empty():
                    logger.error("Missing time or station position data for '%s'", obs.get_observation_code())
                    return empty

                collected = []
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s'", scan_name)
                            continue
                        futures[executor.submit(
                            self._process_telescope_az_el, scan, obs, scan_times,
                            position_df.filter(pl.col("scan_name") == scan_name),
                            orbit_df.filter(pl.col("scan_name") == scan_name),
                            target, observers)] = scan_name

                    for future in futures:
                        result = future.result()
                        if result is not None:
                            collected.append(result)

                if not collected:
                    logger.warning("No pointing computed towards '%s' in '%s'",
                                   target_code, obs.get_observation_code())
                    return empty

                df = pl.DataFrame({
                    "time": np.concatenate([c[0] for c in collected]),
                    "target_code": np.concatenate([c[1] for c in collected]),
                    "scan_name": np.concatenate([c[2] for c in collected]),
                    "telescope_code": np.concatenate([c[3] for c in collected]),
                    "az": np.concatenate([c[4] for c in collected]),
                    "el": np.concatenate([c[5] for c in collected]),
                    "range": np.concatenate([c[6] for c in collected])
                }, schema=CalculatedDataStructure.get_dtypes("telescope_az_el"))

                logger.info("Computed pointing towards '%s' from %s station(s) over %s scan(s), %s rows",
                            target_code, df["telescope_code"].unique().len(),
                            df["scan_name"].unique().len(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.observations()),
                "target_code": target_code,
                "position_store_key": position_store_key,
                "orbit_store_key": orbit_store_key
            }
            df = self._process_object(obj, attributes, calculate_telescope_az_el, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)
            return df
        except Exception as e:
            logger.error("Failed to compute pointing towards a space telescope for '%s': %s",
                         obj.get_observation_code() if isinstance(obj, Observation) else obj.name,
                         str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_az_el"))

    def _process_telescope_az_el(self, scan: Scan, observation: Observation, times_mjd: np.ndarray,
                                 position_df: pl.DataFrame, orbit_df: pl.DataFrame,
                                 target: SpaceTelescope, observers: List[Telescope]) -> Optional[Tuple]:
        """Point each ground station at the spacecraft, for one scan.

        Args:
            scan (Scan): The scan being processed.
            observation (Observation): Its parent.
            times_mjd (np.ndarray): The scan's time grid.
            position_df (pl.DataFrame): Ground station positions for this scan.
            orbit_df (pl.DataFrame): Spacecraft positions for this scan.
            target (SpaceTelescope): What is being pointed at.
            observers (List[Telescope]): The stations doing the pointing.

        Returns:
            Optional[Tuple]: Arrays of (times, target codes, scan names, station codes, az, el,
                range), or None if nothing could be computed.

        Notes:
            - The direction is the *vector from station to spacecraft*, not a fixed sky
              position. A source is far enough away that every station sees it in the same
              direction; a spacecraft in Earth orbit is not, and two stations a baseline apart
              point measurably differently at it. Using a source's geometry here would give
              answers that look plausible and are wrong by degrees.
            - Both positions are rotated into the Earth-fixed frame first, so the vector
              between them is taken between two things that are stationary with respect to
              each other's frame rather than between one that is and one that is not.
        """
        target_code = target.get_code()
        n_times = len(times_mjd)
        if n_times == 0:
            return None

        # The target need not take part in the scan. Asking when a station can see a spacecraft
        # is a question about the spacecraft, not about the observation it may or may not be
        # observing in -- so its position is computed here rather than read out of a result
        # that only covers scan participants.
        orbit_rows = orbit_df.filter(pl.col("telescope_code") == target_code)
        if orbit_rows.is_empty():
            spacecraft_xyz = self._compute_telescope_position(target, times_mjd)
        else:
            placed = self._on_time_grid(times_mjd, orbit_rows, ["x", "y", "z"], target_code, scan.name)
            spacecraft_xyz = np.column_stack([placed["x"], placed["y"], placed["z"]])

        if spacecraft_xyz is None or np.all(np.isnan(spacecraft_xyz)):
            logger.warning("The orbit of '%s' does not cover scan '%s'; nothing to point at",
                           target_code, scan.name)
            return None

        obstime = Time(times_mjd, format="mjd", scale="utc")
        target_itrs = self._to_earth_fixed(spacecraft_xyz, obstime)

        times_list, target_codes, scan_names, station_codes = [], [], [], []
        az_list, el_list, range_list = [], [], []

        for station in observers:
            code = station.get_code()
            station_rows = position_df.filter(pl.col("telescope_code") == code)
            if station_rows.is_empty():
                logger.debug("No position for station '%s' in scan '%s'", code, scan.name)
                continue

            placed = self._on_time_grid(times_mjd, station_rows, ["x", "y", "z"], code, scan.name)
            station_xyz = np.column_stack([placed["x"], placed["y"], placed["z"]])
            station_itrs = self._to_earth_fixed(station_xyz, obstime)

            az, el, distance = self._look_angles(station_itrs, target_itrs)

            times_list.append(times_mjd)
            target_codes.append(np.full(n_times, target_code, dtype=object))
            scan_names.append(np.full(n_times, scan.name, dtype=object))
            station_codes.append(np.full(n_times, code, dtype=object))
            az_list.append(az)
            el_list.append(el)
            range_list.append(distance)

        if not times_list:
            return None
        return (np.concatenate(times_list), np.concatenate(target_codes), np.concatenate(scan_names),
                np.concatenate(station_codes), np.concatenate(az_list), np.concatenate(el_list),
                np.concatenate(range_list))

    @staticmethod
    def _to_earth_fixed(positions: np.ndarray, obstime: Time) -> np.ndarray:
        """Rotate celestial-frame positions into the Earth-fixed frame.

        Args:
            positions (np.ndarray): An (n, 3) array of GCRS positions in metres.
            obstime (Time): The times they belong to.

        Returns:
            np.ndarray: The same positions in ITRS, in metres, NaN where the input was NaN.
        """
        finite = ~np.any(np.isnan(positions), axis=1)
        result = np.full_like(positions, np.nan, dtype=float)
        if not np.any(finite):
            return result

        gcrs = GCRS(CartesianRepresentation(x=positions[:, 0] * u.m, y=positions[:, 1] * u.m,
                                            z=positions[:, 2] * u.m), obstime=obstime)
        itrs = gcrs.transform_to(ITRS(obstime=obstime)).cartesian
        rotated = np.column_stack([itrs.x.to_value(u.m), itrs.y.to_value(u.m), itrs.z.to_value(u.m)])
        result[finite] = rotated[finite]
        return result

    @staticmethod
    def _look_angles(station: np.ndarray, target: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return azimuth, elevation and range from a station to a target, both Earth-fixed.

        Args:
            station (np.ndarray): An (n, 3) array of station positions in metres, ITRS.
            target (np.ndarray): An (n, 3) array of target positions in metres, ITRS.

        Returns:
            Tuple[np.ndarray, np.ndarray, np.ndarray]: Azimuth east of north in degrees,
                elevation above the horizon in degrees, and range in metres. NaN wherever
                either position is unknown.

        Notes:
            - The local east-north-up frame is built from the station's own geocentric
              direction, so this is geocentric rather than geodetic elevation. The difference
              reaches about 0.2 degrees at mid-latitudes, which matters for a horizon mask and
              is why it is written down here rather than left to be discovered.
        """
        count = station.shape[0]
        azimuth = np.full(count, np.nan)
        elevation = np.full(count, np.nan)
        distance = np.full(count, np.nan)

        usable = ~(np.any(np.isnan(station), axis=1) | np.any(np.isnan(target), axis=1))
        if not np.any(usable):
            return azimuth, elevation, distance

        s = station[usable]
        line = target[usable] - s

        radius = np.linalg.norm(s, axis=1)
        radius[radius == 0] = np.nan
        up = s / radius[:, None]

        # East is perpendicular to both the polar axis and the local vertical.
        east = np.column_stack([-s[:, 1], s[:, 0], np.zeros(len(s))])
        east_norm = np.linalg.norm(east, axis=1)
        east_norm[east_norm == 0] = np.nan          # directly over a pole: east is undefined
        east = east / east_norm[:, None]
        north = np.cross(up, east)

        length = np.linalg.norm(line, axis=1)
        length[length == 0] = np.nan

        azimuth[usable] = np.degrees(np.arctan2(np.sum(line * east, axis=1),
                                                np.sum(line * north, axis=1))) % 360.0
        elevation[usable] = np.degrees(np.arcsin(np.clip(np.sum(line * up, axis=1) / length, -1.0, 1.0)))
        distance[usable] = length
        return azimuth, elevation, distance

    @time_execution
    def _calculate_telescope_visibility(self, obj: "Observation | ScheduleProject", attributes: Dict[str, Any]) -> pl.DataFrame:
        """Report when each ground station can actually see the space telescope.

        Args:
            obj: The observation, or a project of them.
            attributes: Parameters including "target_telescope", and "time_step", "store_key",
                "az_el_store_key", "recalculate".

        Returns:
            pl.DataFrame: Columns ["time", "target_code", "scan_name", "telescope_code",
                "visibility"].

        Notes:
            - Above the horizon is not enough: a station has an elevation range it can drive
              to, and a spacecraft below that limit is as unreachable as one below the horizon.
              The same rule a source is checked against.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "telescope_visibility")
            az_el_store_key = attributes.get("az_el_store_key", "telescope_az_el")
            target_code = attributes.get("target_telescope")
            recalculate = attributes.get("recalculate", False)
            empty = pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_visibility"))

            if not target_code:
                logger.error("No 'target_telescope' given; there is nothing to be visible")
                return empty

            def calculate_telescope_visibility(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                angles = self._calculate_telescope_az_el(obs, {
                    "time_step": time_step, "store_key": az_el_store_key,
                    "target_telescope": target_code, "recalculate": False})
                if angles.is_empty():
                    return empty

                limits = {}
                for telescope in obs.get_telescopes().get_active_items():
                    if isinstance(telescope, SpaceTelescope):
                        continue
                    low, high = telescope.get("elevation_range")
                    limits[telescope.get_code()] = (float(low), float(high))

                elevation = angles["el"].to_numpy()
                codes = angles["telescope_code"].to_list()
                low = np.array([limits.get(code, (0.0, 90.0))[0] for code in codes])
                high = np.array([limits.get(code, (0.0, 90.0))[1] for code in codes])

                with np.errstate(invalid="ignore"):
                    visible = (elevation >= low) & (elevation <= high)
                visible &= ~np.isnan(elevation)

                df = pl.DataFrame({
                    "time": angles["time"].to_numpy(),
                    "target_code": angles["target_code"].to_list(),
                    "scan_name": angles["scan_name"].to_list(),
                    "telescope_code": codes,
                    "visibility": visible
                }, schema=CalculatedDataStructure.get_dtypes("telescope_visibility"))

                logger.info("'%s' is visible for %s of %s sampled moments across %s station(s)",
                            target_code, int(visible.sum()), len(visible),
                            df["telescope_code"].unique().len())
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.observations()),
                "target_code": target_code,
                "az_el_store_key": az_el_store_key
            }
            df = self._process_object(obj, attributes, calculate_telescope_visibility, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)
            return df
        except Exception as e:
            logger.error("Failed to compute visibility of a space telescope for '%s': %s",
                         obj.get_observation_code() if isinstance(obj, Observation) else obj.name,
                         str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_visibility"))

    @time_execution
    def _calculate_time_on_source(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate time-on-source blocks for all active scans in the observation or project.

        Args:
            obj: The object to calculate time on source for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "visibility_store_key", "recalculate".

        Returns:
            pl.DataFrame: DataFrame with columns ["scan_name", "telescope_code", "source_name", "start_mjd", "end_mjd", "duration"].
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "time_on_source")
            visibility_store_key = attributes.get("visibility_store_key", "source_visibility")
            recalculate = attributes.get("recalculate", False)

            def calculate_time_on_source(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, _, _ = self._get_active_components(obs)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("time_on_source"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                visibility_df = self._calculate_source_visibility(obs, visibility_attrs)

                if times_df.is_empty() or visibility_df.is_empty():
                    logger.error("Missing time or visibility data for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("time_on_source"))

                scan_names = []
                telescope_codes = []
                source_names = []
                start_mjd_list = []
                end_mjd_list = []
                durations_list = []

                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s' in observation '%s'", scan_name, obs.get_observation_code())
                            continue
                        scan_visibility = visibility_df.filter(pl.col("scan_name") == scan_name)
                        futures[executor.submit(
                            self._process_time_on_source, scan, obs, scan_times, scan_visibility
                        )] = scan_name

                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result is not None:
                            scan_name_arr, tel_codes, source_name_arr, start_mjd, end_mjd, durations = scan_result
                            scan_names.append(scan_name_arr)
                            telescope_codes.append(tel_codes)
                            source_names.append(source_name_arr)
                            start_mjd_list.append(start_mjd)
                            end_mjd_list.append(end_mjd)
                            durations_list.append(durations)

                if not scan_names:
                    logger.warning("No valid time-on-source blocks computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("time_on_source"))

                df = pl.DataFrame({
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "source_name": np.concatenate(source_names),
                    "start": np.concatenate(start_mjd_list),
                    "end": np.concatenate(end_mjd_list),
                    "duration": np.concatenate(durations_list)
                }, schema=CalculatedDataStructure.get_dtypes("time_on_source"))

                logger.info("Calculated time-on-source for %s scans across %s telescopes in '%s', DF rows: %s", df['scan_name'].unique().len(), df['telescope_code'].unique().len(), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.observations()),
                "visibility_store_key": visibility_store_key
            }
            df = self._process_object(obj, attributes, calculate_time_on_source, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate time on source for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("time_on_source"))

    def _process_time_on_source(self, scan: Scan, observation: Observation, times_mjd: np.ndarray, visibility_df: pl.DataFrame) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Process time-on-source blocks for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            times_mjd (np.ndarray): Precomputed times (MJD as float).
            visibility_df (pl.DataFrame): Precomputed visibility data filtered by scan_name.

        Returns:
            Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]: 
                Tuple of (scan_names, telescope_codes, source_names, start_mjd, end_mjd, durations) as Numpy arrays, or None if no valid data.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning("No active source for scan '%s' in observation '%s'", scan.name, observation.get_observation_code())
            return None

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        if not active_telescopes:
            logger.warning("No active telescopes for scan '%s' starting at %s", scan_name, scan.get_start().isot)
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning("No valid times for scan '%s' in source '%s'", scan_name, source_name)
            return None

        scan_names = []
        telescope_codes = []
        source_names = []
        start_mjd_list = []
        end_mjd_list = []
        durations_list = []

        for tel in active_telescopes:
            tel_code = tel.get_code()
            tel_visibility = visibility_df.filter(pl.col("telescope_code") == tel_code)
            if tel_visibility.is_empty():
                logger.warning("No visibility data for telescope '%s' in scan '%s'", tel_code, scan_name)
                continue

            visibility = tel_visibility["visibility"].to_numpy()
            if len(visibility) != n_times:
                logger.warning("Visibility data length mismatch for '%s' in scan '%s': got %s, expected %s", tel_code, scan_name, len(visibility), n_times)
                visibility = np.full(n_times, False)[:min(len(visibility), n_times)] if len(visibility) > 0 else np.full(n_times, False)

            diff = np.diff(visibility.astype(int))
            start_indices = np.where(diff == 1)[0] + 1
            end_indices = np.where(diff == -1)[0]
            if visibility[0]:
                start_indices = np.concatenate(([0], start_indices))
            if visibility[-1]:
                end_indices = np.concatenate((end_indices, [n_times - 1]))
            if len(start_indices) > len(end_indices):
                end_indices = np.concatenate((end_indices, [n_times - 1]))
            elif len(end_indices) > len(start_indices):
                start_indices = np.concatenate(([0], start_indices))

            if len(start_indices) == 0 or len(end_indices) == 0:
                logger.debug("No visibility blocks for telescope '%s' in scan '%s'", tel_code, scan_name)
                continue

            n_blocks = len(start_indices)
            blocks_start = times_mjd[start_indices]
            blocks_end = times_mjd[end_indices]
            blocks_duration = (blocks_end - blocks_start) * 86400.0  # Конвертация MJD в секунды

            scan_names.append(np.full(n_blocks, scan_name, dtype=object))
            telescope_codes.append(np.full(n_blocks, tel_code, dtype=object))
            source_names.append(np.full(n_blocks, source_name, dtype=object))
            start_mjd_list.append(blocks_start)
            end_mjd_list.append(blocks_end)
            durations_list.append(blocks_duration)

            logger.debug("Computed %s time-on-source blocks for telescope '%s' in scan '%s'", n_blocks, tel_code, scan_name)

        if not scan_names:
            logger.warning("No time-on-source blocks computed for scan '%s'", scan_name)
            return None

        return (
            np.concatenate(scan_names),
            np.concatenate(telescope_codes),
            np.concatenate(source_names),
            np.concatenate(start_mjd_list),
            np.concatenate(end_mjd_list),
            np.concatenate(durations_list)
        )
    
    @time_execution
    def _calculate_beam_pattern(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate beam pattern for active telescopes in the observation or project, independent of frequency.

        Args:
            obj: The object to calculate beam pattern for (Observation or ScheduleProject).
            attributes: Parameters including "store_key", "recalculate".

        Returns:
            pl.DataFrame: DataFrame with columns ["telescope_code", "theta", "pattern"] (theta in radians, pattern normalized).
        """
        try:
            store_key = attributes.get("store_key", "beam_pattern")
            recalculate = attributes.get("recalculate", False)

            def calculate_beam_pattern(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                _, telescopes, _ = self._get_active_components(obs, require_scans=False, require_telescopes=True)
                if not telescopes:
                    logger.warning("No active telescopes in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("beam_pattern"))

                obs_type = obs.get_observation_type()
                if obs_type not in ["SINGLE_DISH", "VLBI"]:
                    logger.warning("Beam pattern calculation is only for SINGLE_DISH or VLBI, got %s", obs_type)
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("beam_pattern"))

                theta = np.linspace(-np.pi / 2, np.pi / 2, 5000)  # radians
                telescope_codes = []
                theta_list = []
                pattern_list = []
                valid_telescopes = []
                diameters = []

                for tel in telescopes:
                    diameter = tel.get("diameter")
                    if diameter is None or diameter <= 0:
                        logger.warning("Invalid diameter for telescope '%s' in '%s'; skipping", tel.get_code(), obs.get_observation_code())
                        continue
                    valid_telescopes.append(tel)
                    diameters.append(diameter)
                    telescope_codes.append(np.full(len(theta), tel.get_code(), dtype=object))
                    theta_list.append(theta)
                    x = diameter * np.sin(theta)
                    pattern = (2 * j1(x) / x) ** 2
                    pattern = np.where(np.isnan(pattern), 1.0, pattern)
                    pattern = pattern / np.max(pattern)
                    pattern_list.append(pattern)

                if not valid_telescopes:
                    logger.warning("No telescopes with valid diameters in '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("beam_pattern"))

                df = pl.DataFrame({
                    "telescope_code": np.concatenate(telescope_codes),
                    "theta": np.concatenate(theta_list),
                    "pattern": np.concatenate(pattern_list)
                }, schema=CalculatedDataStructure.get_dtypes("beam_pattern"))

                logger.info("Calculated beam pattern for %s telescopes in '%s', DF rows: %s", len(valid_telescopes), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "telescope_count": len(obj.get_telescopes().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_telescopes().get_active_items()) for o in obj.observations()),
                "scale_instruction": "Multiply pattern by wavelength during visualization"
            }
            df = self._process_object(obj, attributes, calculate_beam_pattern, store_key, metadata)

            if not df.is_empty():
                metadata["telescope_count"] = df["telescope_code"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate beam pattern for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("beam_pattern"))

    @time_execution
    def _calculate_baseline_projections(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate baseline projections for VLBI observations in geometric coordinates (meters).

        Args:
            obj: The object to calculate projections for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "recalculate", "visibility_store_key".

        Returns:
            pl.DataFrame: DataFrame with columns ["time", "scan_name", "source_name", "baseline", "projection"] (projection in meters).
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "baseline_projections")
            visibility_store_key = attributes.get("visibility_store_key", "source_visibility")
            recalculate = attributes.get("recalculate", False)

            def calculate_baseline_projections(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                if obs.get_observation_type() != "VLBI":
                    logger.warning("Baseline projections are only for VLBI, got %s", obs.get_observation_type())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

                scans, telescopes, _ = self._get_active_components(obs, require_telescopes=True, min_telescopes=2)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                uv_attrs = {"time_step": time_step, "store_key": "uv_coverage", "recalculate": False}
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                uv_coverage_df = self._calculate_uv_coverage(obs, uv_attrs)
                visibility_df = self._calculate_source_visibility(obs, visibility_attrs)

                if times_df.is_empty() or uv_coverage_df.is_empty():
                    logger.error("Missing time or UV coverage data for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

                times_list = []
                scan_names = []
                source_names = []
                baselines = []
                projections_list = []

                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s' in observation '%s'", scan_name, obs.get_observation_code())
                            continue
                        scan_uv = uv_coverage_df.filter(pl.col("scan_name") == scan_name)
                        scan_visibility = visibility_df.filter(pl.col("scan_name") == scan_name)
                        futures[executor.submit(
                            self._process_baseline_projections, scan, obs, scan_times, scan_uv, scan_visibility, telescopes
                        )] = scan_name

                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result is not None:
                            times, scan_name_arr, source_name_arr, baseline_arr, projections = scan_result
                            times_list.append(times)
                            scan_names.append(scan_name_arr)
                            source_names.append(source_name_arr)
                            baselines.append(baseline_arr)
                            projections_list.append(projections)

                if not times_list:
                    logger.warning("No valid baseline projections computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "source_name": np.concatenate(source_names),
                    "baseline": np.concatenate(baselines),
                    "projection": np.concatenate(projections_list)
                }, schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

                logger.info("Calculated baseline projections for %s scans across %s baselines in '%s', DF rows: %s", df['scan_name'].unique().len(), df['baseline'].unique().len(), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.observations()),
                "visibility_store_key": visibility_store_key
            }
            df = self._process_object(obj, attributes, calculate_baseline_projections, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate baseline projections for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

    @staticmethod
    def _on_time_grid(times_mjd: np.ndarray, frame: pl.DataFrame, columns: List[str], baseline: str, scan_name: str) -> Dict[str, np.ndarray]:
        """Place a frame's columns on the scan's time grid, matching on time rather than on position.

        Args:
            times_mjd (np.ndarray): The scan's time grid, as MJD.
            frame (pl.DataFrame): Rows to place, carrying a "time" column.
            columns (List[str]): The columns to return.
            baseline (str): Named only so a dropped row can be reported usefully.
            scan_name (str): Likewise.

        Returns:
            Dict[str, np.ndarray]: One array per requested column, each the length of the grid,
                holding NaN where the frame has no row for that time.

        Notes:
            - Matching on time is the whole point. A calculation that covers only part of the
              grid -- UV coverage covers only the times the source is up -- produces fewer rows
              than the grid has, and the two are not aligned from the start. Copying such rows
              into the first N positions puts every value at the wrong time. Where the source
              rose partway through a scan, as it usually does, the result was that no value
              survived the visibility mask at all and every projection came out NaN.
        """
        placed = pl.DataFrame({"time": np.asarray(times_mjd, dtype=float)}).join(
            frame.select(["time"] + columns).unique(subset=["time"], keep="first"),
            on="time", how="left")
        matched = placed[columns[0]].len() - placed[columns[0]].null_count()
        if matched < frame.height:
            logger.debug("Only %s of %s rows for baseline '%s' in scan '%s' fall on the time grid",
                         matched, frame.height, baseline, scan_name)
        return {column: placed[column].cast(pl.Float64).fill_null(float("nan")).to_numpy()
                for column in columns}

    def _process_baseline_projections(self, scan: Scan, observation: Observation, times_mjd: np.ndarray, uv_coverage_df: pl.DataFrame, visibility_df: pl.DataFrame, telescopes: List[Telescope | SpaceTelescope]) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Process baseline projections for a single scan in geometric coordinates (meters).

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            times_mjd (np.ndarray): Precomputed times (MJD as float).
            uv_coverage_df (pl.DataFrame): Precomputed UV coverage data filtered by scan_name.
            visibility_df (pl.DataFrame): Precomputed visibility data filtered by scan_name.
            telescopes (List[Telescope | SpaceTelescope]): List of active telescopes.

        Returns:
            Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]: 
                Tuple of (times, scan_names, source_names, baselines, projections) as Numpy arrays, or None if no valid data.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning("No active source for scan '%s' in observation '%s'", scan.name, observation.get_observation_code())
            return None

        scan_name = scan.name
        source_name = source.name
        active_telescopes = [t for t in telescopes if t.isactive]
        if len(active_telescopes) < 2:
            logger.warning("Insufficient telescopes (%s) for baseline projections in scan '%s'", len(active_telescopes), scan_name)
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning("No valid times for scan '%s' in source '%s'", scan_name, source_name)
            return None

        times_list = []
        scan_names = []
        source_names = []
        baselines = []
        projections_list = []

        pairs = [f"{active_telescopes[i].get_code()}-{active_telescopes[j].get_code()}" for i, j in zip(*np.triu_indices(len(active_telescopes), k=1))]

        for baseline in pairs:
            tel1_code, tel2_code = baseline.split('-')
            uv_data = uv_coverage_df.filter(pl.col("baseline") == baseline)

            projections = np.full(n_times, np.nan, dtype=float)

            if uv_data.is_empty():
                logger.debug("No UV data for baseline '%s' in scan '%s'; filling with NaN", baseline, scan_name)
            else:
                aligned = self._on_time_grid(times_mjd, uv_data, ["u", "v"], baseline, scan_name)
                u, v = aligned["u"], aligned["v"]
                projections = np.sqrt(u**2 + v**2)

            for telescope_code in (tel1_code, tel2_code):
                telescope_visibility = visibility_df.filter(pl.col("telescope_code") == telescope_code)
                if telescope_visibility.is_empty():
                    continue
                aligned = self._on_time_grid(times_mjd, telescope_visibility, ["visibility"], baseline, scan_name)
                projections[~(aligned["visibility"] > 0)] = np.nan

            valid_count = np.sum(~np.isnan(projections))
            logger.debug("Computed %s valid projections for baseline '%s' in scan '%s'", valid_count, baseline, scan_name)

            times_list.append(times_mjd)
            scan_names.append(np.full(n_times, scan_name, dtype=object))
            source_names.append(np.full(n_times, source_name, dtype=object))
            baselines.append(np.full(n_times, baseline, dtype=object))
            projections_list.append(projections)

        if not times_list:
            logger.warning("No valid baseline projections computed for scan '%s'", scan_name)
            return None

        logger.debug("Computed baseline projections for %s baselines in scan '%s'", len(baselines), scan_name)
        return (
            np.concatenate(times_list),
            np.concatenate(scan_names),
            np.concatenate(source_names),
            np.concatenate(baselines),
            np.concatenate(projections_list)
        )

    @time_execution
    def _calculate_mollweide_tracks(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate Mollweide projection tracks for telescopes in active scans.

        Args:
            obj: The object to calculate tracks for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "recalculate".

        Returns:
            pl.DataFrame: DataFrame with columns ["time", "scan_name", "telescope_code", "lon", "lat"] (lon, lat in degrees).
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "mollweide_tracks")
            recalculate = attributes.get("recalculate", False)

            def calculate_mollweide(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, _, _ = self._get_active_components(obs, require_scans=True)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                position_df = self._calculate_telescope_positions(obs, position_attrs)

                if times_df.is_empty() or position_df.is_empty():
                    logger.error("Missing time or position data for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))

                times_list = []
                scan_names = []
                telescope_codes = []
                lons_list = []
                lats_list = []

                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s' in observation '%s'", scan_name, obs.get_observation_code())
                            continue
                        scan_positions = position_df.filter(pl.col("scan_name") == scan_name)
                        futures[executor.submit(
                            self._process_mollweide_tracks, scan, obs, scan_times, scan_positions
                        )] = scan_name

                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result is not None:
                            times, scan_name_arr, tel_codes, lons, lats = scan_result
                            times_list.append(times)
                            scan_names.append(scan_name_arr)
                            telescope_codes.append(tel_codes)
                            lons_list.append(lons)
                            lats_list.append(lats)

                if not times_list:
                    logger.warning("No valid Mollweide tracks computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "lon": np.concatenate(lons_list),
                    "lat": np.concatenate(lats_list)
                }, schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))

                logger.info("Calculated Mollweide tracks for %s scans across %s telescopes in '%s', DF rows: %s", df['scan_name'].unique().len(), df['telescope_code'].unique().len(), obs.get_observation_code(), df.height)
                return df

            sources_metadata = {}
            for source in obj.get_sources().get_active_items():
                ra = source.ra_degrees
                dec = source.dec_degrees
                lon = ra - 360.0 if ra > 180.0 else ra
                lat = np.clip(dec, -90.0, 90.0)
                sources_metadata[source.name] = np.array([lon, lat])

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.observations()),
                "sources": sources_metadata
            }
            df = self._process_object(obj, attributes, calculate_mollweide, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate Mollweide tracks for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))

    def _process_mollweide_tracks(self, scan: Scan, observation: Observation, times_mjd: np.ndarray, position_df: pl.DataFrame) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Process Mollweide tracks for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            times_mjd (np.ndarray): Precomputed times (MJD as float).
            position_df (pl.DataFrame): Precomputed telescope positions filtered by scan_name.

        Returns:
            Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]: 
                Tuple of (times, scan_names, telescope_codes, lons, lats) as Numpy arrays, or None if no valid data.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning("No active source for scan '%s' in observation '%s'", scan.name, observation.get_observation_code())
            return None

        scan_name = scan.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        if not active_telescopes:
            logger.warning("No active telescopes for scan '%s' starting at %s", scan_name, scan.get_start().isot)
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning("No valid times for scan '%s' in source '%s'", scan_name, source.name)
            return None

        times_list = []
        scan_names = []
        telescope_codes = []
        lons_list = []
        lats_list = []

        for tel in active_telescopes:
            tel_code = tel.get_code()
            tel_positions = position_df.filter(pl.col("telescope_code") == tel_code)
            if tel_positions.is_empty():
                logger.debug("No position data for telescope '%s' in scan '%s'; filling with NaN", tel_code, scan_name)
                positions = np.full((n_times, 3), np.nan, dtype=float)
            else:
                positions = tel_positions.select(["x", "y", "z"]).to_numpy()
                if len(positions) != n_times:
                    logger.debug("Position data length mismatch for '%s' in scan '%s': got %s, expected %s; adjusting with NaN", tel_code, scan_name, len(positions), n_times)
                    temp = np.full((n_times, 3), np.nan, dtype=float)
                    temp[:min(len(positions), n_times)] = positions[:n_times]
                    positions = temp

            r = np.sqrt(np.sum(positions**2, axis=1))
            valid_mask = r > 0  # avoid division by zero
            ra_rad = np.full(n_times, np.nan, dtype=float)
            dec_rad = np.full(n_times, np.nan, dtype=float)
            ra_rad[valid_mask] = np.arctan2(positions[valid_mask, 1], positions[valid_mask, 0])
            dec_rad[valid_mask] = np.arcsin(positions[valid_mask, 2] / r[valid_mask])
            ra = np.degrees(ra_rad)
            dec = np.degrees(dec_rad)
            lon = np.where(ra > 180.0, ra - 360.0, ra)
            lat = np.clip(dec, -90.0, 90.0)

            valid_points = np.sum(~np.isnan(lon) & ~np.isnan(lat))
            if valid_points == 0:
                logger.debug("No valid Mollweide coordinates for telescope '%s' in scan '%s'", tel_code, scan_name)
            else:
                logger.debug("Computed %s valid Mollweide coordinates for telescope '%s' in scan '%s'", valid_points, tel_code, scan_name)

            times_list.append(times_mjd)
            scan_names.append(np.full(n_times, scan_name, dtype=object))
            telescope_codes.append(np.full(n_times, tel_code, dtype=object))
            lons_list.append(lon)
            lats_list.append(lat)

        if not times_list:
            logger.warning("No valid Mollweide tracks computed for scan '%s'", scan_name)
            return None

        logger.debug("Computed Mollweide tracks for %s telescopes in scan '%s'", len(telescope_codes), scan_name)
        return (
            np.concatenate(times_list),
            np.concatenate(scan_names),
            np.concatenate(telescope_codes),
            np.concatenate(lons_list),
            np.concatenate(lats_list)
        )

    @time_execution
    def _calculate_parallactic_angle(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate parallactic angle for ground-based telescopes in all active scans.

        The parallactic angle is crucial for polarization observations as it describes
        the orientation of the feed relative to the sky.

        Args:
            obj: The object to calculate parallactic angle for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "recalculate",
                       "position_store_key", "visibility_store_key".

        Returns:
            pl.DataFrame: DataFrame with columns 
                ["time", "scan_name", "telescope_code", "source_name", "parallactic_angle"] 
                (angle in degrees, range usually -180 to +180).
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "parallactic_angle")
            position_store_key = attributes.get("position_store_key", "telescope_positions")
            visibility_store_key = attributes.get("visibility_store_key", "source_visibility")
            recalculate = attributes.get("recalculate", False)

            def calculate_parallactic(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, telescopes, _ = self._get_active_components(obs, require_telescopes=True)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("parallactic_angle"))

                # Only ground telescopes are relevant for parallactic angle
                ground_telescopes = [tel for tel in telescopes if not isinstance(tel, SpaceTelescope)]
                if not ground_telescopes:
                    logger.debug("No ground telescopes in '%s' for parallactic angle calculation", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("parallactic_angle"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": False}
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": False}

                times_df = self._calculate_time_arrays(obs, time_attrs)
                position_df = self._calculate_telescope_positions(obs, position_attrs)
                visibility_df = self._calculate_source_visibility(obs, visibility_attrs)

                if times_df.is_empty() or position_df.is_empty() or visibility_df.is_empty():
                    logger.error("Missing required data for parallactic angle in '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("parallactic_angle"))

                times_list = []
                scan_names = []
                telescope_codes = []
                source_names = []
                pa_list = []

                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s'", scan_name)
                            continue
                        scan_positions = position_df.filter(pl.col("scan_name") == scan_name)
                        scan_visibility = visibility_df.filter(pl.col("scan_name") == scan_name)
                        futures[executor.submit(
                            self._process_parallactic_angle,
                            scan, obs, scan_times, scan_positions, scan_visibility
                        )] = scan_name

                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result is not None:
                            times, scan_name_arr, tel_codes, source_name_arr, pa = scan_result
                            times_list.append(times)
                            scan_names.append(scan_name_arr)
                            telescope_codes.append(tel_codes)
                            source_names.append(source_name_arr)
                            pa_list.append(pa)

                if not times_list:
                    logger.warning("No valid parallactic angle data computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("parallactic_angle"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "source_name": np.concatenate(source_names),
                    "parallactic_angle": np.concatenate(pa_list)
                }, schema=CalculatedDataStructure.get_dtypes("parallactic_angle"))

                logger.info("Calculated parallactic angles for %s scans across %s telescopes in '%s', DF rows: %s", df['scan_name'].unique().len(), df['telescope_code'].unique().len(), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) 
                             else sum(len(o.get_scans().get_active_items()) for o in obj.observations()),
                "position_store_key": position_store_key,
                "visibility_store_key": visibility_store_key
            }

            df = self._process_object(obj, attributes, calculate_parallactic, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df

        except Exception as e:
            logger.error("Failed to calculate parallactic angle for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("parallactic_angle"))

    def _process_parallactic_angle(
            self,
            scan: Scan,
            observation: Observation,
            times_mjd: np.ndarray,
            position_df: pl.DataFrame,
            visibility_df: pl.DataFrame
        ) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Process parallactic angle for a single scan using robust vectorized calculation."""
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning("No active source for scan '%s'", scan.name)
            return None

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_ground_telescopes = [
            t for t in scan_telescopes.get_items() 
            if t.isactive and not isinstance(t, SpaceTelescope)
        ]

        if not active_ground_telescopes:
            logger.debug("No active ground telescopes for parallactic angle in scan '%s'", scan_name)
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning("No valid times for scan '%s'", scan_name)
            return None

        source_coord = SkyCoord(
            ra=source.ra_degrees * u.deg,
            dec=source.dec_degrees * u.deg,
            frame='icrs'
        )
        obstime = Time(times_mjd, format="mjd", scale="utc")

        times_list = []
        scan_names = []
        telescope_codes = []
        source_names = []
        pa_list = []

        for tel in active_ground_telescopes:
            tel_code = tel.get_code()

            tel_positions = position_df.filter(pl.col("telescope_code") == tel_code)
            tel_visibility = visibility_df.filter(pl.col("telescope_code") == tel_code)

            if tel_positions.is_empty() or tel_visibility.is_empty():
                logger.warning("Missing position or visibility data for '%s' in scan '%s'", tel_code, scan_name)
                continue

            positions = tel_positions.select(["x", "y", "z"]).to_numpy()
            visibility = tel_visibility["visibility"].to_numpy()

            if len(positions) != n_times or len(visibility) != n_times:
                logger.warning("Data length mismatch for '%s' in scan '%s'", tel_code, scan_name)
                positions = np.full((n_times, 3), np.nan, dtype=float)
                visibility = np.full(n_times, False, dtype=bool)

            nan_positions = np.any(np.isnan(positions), axis=1)
            is_visible = visibility & ~nan_positions

            parallactic = np.full(n_times, np.nan, dtype=float)

            if np.any(is_visible):
                try:
                    gcrs_coords = CartesianRepresentation(
                        x=positions[:, 0] * u.m,
                        y=positions[:, 1] * u.m,
                        z=positions[:, 2] * u.m
                    )
                    itrs = GCRS(gcrs_coords, obstime=obstime).transform_to(ITRS(obstime=obstime))
                    locations = itrs.earth_location

                    altaz_frame = AltAz(obstime=obstime[is_visible], location=locations[is_visible])
                    source_altaz = source_coord.transform_to(altaz_frame)

                    hadec_frame = HADec(obstime=obstime[is_visible], location=locations[is_visible])
                    source_hadec = source_coord.transform_to(hadec_frame)

                    ha = source_hadec.ha.rad
                    dec = np.radians(source_hadec.dec.deg)
                    lat = np.radians(locations[is_visible].lat.deg)

                    sin_pa = np.sin(ha) * np.cos(lat)
                    cos_pa = np.sin(lat) * np.cos(dec) - np.cos(lat) * np.sin(dec) * np.cos(ha)
                    pa_rad = np.arctan2(sin_pa, cos_pa)

                    pa_deg = np.degrees(pa_rad)
                    pa_deg = (pa_deg + 180) % 360 - 180

                    parallactic[is_visible] = pa_deg

                except Exception as inner_e:
                    logger.warning("Failed to compute parallactic angle for '%s' in scan '%s': %s", tel_code, scan_name, inner_e, exc_info=True)

            times_list.append(times_mjd)
            scan_names.append(np.full(n_times, scan_name, dtype=object))
            telescope_codes.append(np.full(n_times, tel_code, dtype=object))
            source_names.append(np.full(n_times, source_name, dtype=object))
            pa_list.append(parallactic)

            valid_count = np.sum(~np.isnan(parallactic))
            logger.debug("Computed parallactic angles for '%s' in scan '%s': %s/%s valid points", tel_code, scan_name, valid_count, n_times)

        if not times_list:
            logger.warning("No parallactic angle data computed for scan '%s'", scan_name)
            return None

        return (
            np.concatenate(times_list),
            np.concatenate(scan_names),
            np.concatenate(telescope_codes),
            np.concatenate(source_names),
            np.concatenate(pa_list)
        )