from common.super.super import Super
from common.utils.logging_setup import logger

from pastrocore.base.sources import Source
from pastrocore.base.telescopes import Telescope, SpaceTelescope
from pastrocore.base.scans import Scan
from pastrocore.base.observation import Observation
from pastrocore.base.data_structure import CalculatedDataStructure
from pastrocore.super.schedule_project import ScheduleProject

from typing import Dict, Any, Optional, Tuple, List, Callable
from concurrent.futures import ThreadPoolExecutor
from scipy.special import j1
from functools import wraps

import astropy.units as u
from astropy.time import Time
from astropy.coordinates import ITRS, GCRS, CartesianRepresentation, SkyCoord, AltAz, get_sun, HADec

import numpy as np
import pandas as pd

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
        duration = (end_time - start_time) # seconds
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
            logger.warning(f"No active scans in observation '{obj_code}'")
            return [], [], []
        if require_telescopes and len(telescopes) < min_telescopes:
            logger.warning(f"Insufficient active telescopes ({len(telescopes)} < {min_telescopes}) in '{obj_code}'")
            return [], [], []
        if not sources:
            logger.warning(f"No active sources in observation '{obj_code}'")
            return [], [], []
        
        return scans, telescopes, sources
    
    def _get_cached_or_calculate(self, obj: Observation | ScheduleProject, store_key: str, calc_func, attributes: Dict[str, Any], metadata: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Retrieve cached data or perform calculation and cache the result as a DataFrame.

        Args:
            obj (Observation | ScheduleProject): The object to calculate for.
            store_key (str): Unique key for storing/retrieving calculated data.
            calc_func: The calculation function to execute if no valid cache exists.
            attributes (Dict[str, Any]): Calculation parameters (e.g., "recalculate", "time_step").
            metadata (Dict[str, Any]): Metadata to store with the result (e.g., time step, scan count).

        Returns:
            Optional[pd.DataFrame]: For Observation, returns the calculated or cached DataFrame.
                For ScheduleProject, returns None as calculations are stored in each Observation's calculated_data.

        Notes:
            - For Observation, returns cached DataFrame if "recalculate" is False and valid cache exists.
            - For ScheduleProject, performs calculations for each Observation and stores results in their calculated_data.
            - Uses thread-safe caching with a lock.
            - Logs warnings for empty or invalid results.
        """
        if not store_key:
            logger.error("Empty store_key provided for caching")
            return None

        expected_columns = CalculatedDataStructure.get_columns(store_key)
        expected_metadata_types = CalculatedDataStructure.get_metadata_types(store_key)
        if expected_columns is None or expected_metadata_types is None:
            logger.error(f"Invalid store_key '{store_key}' not found in CalculatedDataStructure")
            return None

        recalculate = attributes.get("recalculate", False)
        time_step = attributes.get("time_step")
        obj_name = obj.name if isinstance(obj, ScheduleProject) else obj.get_observation_code()

        if isinstance(obj, ScheduleProject):
            for observation in obj.get_observations():
                existing_df = observation.get_calculated_data_by_key(store_key)
                if existing_df is not None and not recalculate and existing_df.attrs.get("time_step") == time_step:
                    if not existing_df.empty:
                        logger.debug(f"Retrieved cached data for '{store_key}' in observation '{observation.get_observation_code()}'")
                        continue
                    logger.warning(f"Cached data for '{store_key}' in observation '{observation.get_observation_code()}' is empty; recalculating")

                logger.info(f"Calculating '{store_key}' for observation '{observation.get_observation_code()}' (recalculate={recalculate})")
                result_df = calc_func(observation, attributes)
                if result_df.empty:
                    logger.warning(f"Calculation for '{store_key}' in observation '{observation.get_observation_code()}' returned empty result")
                    result_df = pd.DataFrame(columns=expected_columns)
                else:
                    if not all(col in result_df.columns for col in expected_columns):
                        logger.error(f"Invalid DataFrame structure for '{store_key}' in observation '{observation.get_observation_code()}': missing columns")
                        result_df = pd.DataFrame(columns=expected_columns)
                    else:
                        result_df.attrs.update(metadata)
                        for meta_key, meta_type in expected_metadata_types.items():
                            if meta_key in result_df.attrs and not isinstance(result_df.attrs[meta_key], meta_type):
                                logger.error(f"Invalid metadata type for '{meta_key}' in '{store_key}' for observation '{observation.get_observation_code()}'")
                                result_df = pd.DataFrame(columns=expected_columns)
                                break
                with self._lock:
                    observation.set_calculated_data_by_key(store_key, result_df)
            return None

        existing_df = obj.get_calculated_data_by_key(store_key)
        if existing_df is not None and not recalculate and existing_df.attrs.get("time_step") == time_step:
            if not existing_df.empty:
                logger.debug(f"Retrieved cached data for '{store_key}' in '{obj_name}'")
                return existing_df
            logger.warning(f"Cached data for '{store_key}' in '{obj_name}' is empty; recalculating")

        logger.info(f"Calculating '{store_key}' for '{obj_name}' (recalculate={recalculate})")
        result_df = calc_func(obj, attributes)
        if result_df.empty:
            logger.warning(f"Calculation for '{store_key}' in '{obj_name}' returned empty result")
            result_df = pd.DataFrame(columns=expected_columns)
        else:
            if not all(col in result_df.columns for col in expected_columns):
                logger.error(f"Invalid DataFrame structure for '{store_key}' in '{obj_name}': missing columns")
                result_df = pd.DataFrame(columns=expected_columns)
            else:
                result_df.attrs.update(metadata)
                for meta_key, meta_type in expected_metadata_types.items():
                    if meta_key in result_df.attrs and not isinstance(result_df.attrs[meta_key], meta_type):
                        logger.error(f"Invalid metadata type for '{meta_key}' in '{store_key}' for '{obj_name}'")
                        result_df = pd.DataFrame(columns=expected_columns)
                        break

        with self._lock:
            obj.set_calculated_data_by_key(store_key, result_df)

        logger.warning(result_df.head())
        return result_df
    
    def _process_object(
        self,
        obj: Observation | ScheduleProject,
        attributes: Dict[str, Any],
        calc_func: Callable[[Observation, Dict[str, Any]], pd.DataFrame],
        store_key: str,
        metadata: Dict[str, Any]
    ) -> pd.DataFrame | Dict[str, pd.DataFrame]:
        """Process an object (Observation or ScheduleProject) with parallel execution for projects.

        Args:
            obj: The object to process (Observation or ScheduleProject).
            attributes: Calculation parameters.
            calc_func: Function to perform calculation for a single Observation, returning a DataFrame.
            store_key: Key for caching results.
            metadata: Metadata for cache validation.

        Returns:
            pd.DataFrame | Dict[str, pd.DataFrame]: For Observation, returns a single DataFrame.
                For ScheduleProject, returns a dictionary mapping observation codes to DataFrames.
        """
        obj_name = obj.name if isinstance(obj, ScheduleProject) else obj.get_observation_code()
        
        if isinstance(obj, ScheduleProject):
            observations = obj.get_observations()
            if not observations:
                logger.warning(f"No observations in project '{obj_name}'")
                return {}
            results = {}
            max_workers = min(len(observations), 4) if len(observations) > 1 else 1
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._process_object, obs, attributes, calc_func, store_key, metadata): obs.get_observation_code()
                    for obs in observations
                }
                for future in futures:
                    obs_code = futures[future]
                    result_df = future.result()
                    if result_df.empty:
                        logger.warning(f"No data computed for observation '{obs_code}' with store_key '{store_key}'")
                    results[obs_code] = result_df
            logger.info(f"Processed {len(observations)} observations for '{obj_name}'")
            return results
        
        result_df = self._get_cached_or_calculate(obj, store_key, calc_func, attributes, metadata)
        if result_df is None or result_df.empty:
            logger.warning(f"No data computed for '{obj_name}' with store_key '{store_key}'")
            expected_columns = CalculatedDataStructure.get_columns(store_key) or []
            return pd.DataFrame(columns=expected_columns)
        return result_df
    

    @time_execution
    def _calculate_time_arrays(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pd.DataFrame | Dict[str, pd.DataFrame]:
        """Calculate time arrays for active scans grouped by active sources with a configurable time threshold.

        Args:
            obj: The object to calculate time arrays for.
            attributes: Parameters including "time_step", "time_threshold", "store_key", "recalculate".

        Returns:
            pd.DataFrame | Dict[str, pd.DataFrame]: For Observation, returns a DataFrame with columns
                ["source_name", "scan_name", "time"]. For ScheduleProject, returns a dictionary mapping
                observation codes to DataFrames.

        Notes:
            - Uses CalculatedDataStructure to validate DataFrame structure and metadata.
            - Stores results in Observation's calculated_data under the specified store_key.
            - Returns empty DataFrame or dict if no valid scans or sources are found.
        """
        try:
            time_step = attributes.get("time_step")
            time_threshold = attributes.get("time_threshold", 1.0)
            store_key = attributes.get("store_key", "times")
            recalculate = attributes.get("recalculate", False)

            if time_step is not None and time_step <= 0:
                logger.error(f"Invalid time_step: {time_step}. Must be positive.")
                return pd.DataFrame(columns=CalculatedDataStructure.get_columns("times")) if isinstance(obj, Observation) else {}
            if time_threshold <= 0:
                logger.error(f"Invalid time_threshold: {time_threshold}. Must be positive.")
                return pd.DataFrame(columns=CalculatedDataStructure.get_columns("times")) if isinstance(obj, Observation) else {}

            def calculate_times(obs: Observation, attrs: Dict[str, Any]) -> pd.DataFrame:
                scans, _, sources = self._get_active_components(obs)
                if not scans:
                    logger.debug(f"No active scans for observation '{obs.get_observation_code()}'")
                    return pd.DataFrame(columns=CalculatedDataStructure.get_columns("times"))

                source_names = []
                scan_names = []
                time_values = []
                start_times = []
                end_times = []
                processed_scans = 0

                for scan in scans:
                    source = scan.get_source(obs)
                    if source is None or not source.isactive:
                        logger.debug(f"Skipping scan '{scan.name}' in '{obs.get_observation_code()}': no active source")
                        continue
                    source_name = source.name
                    start_time = scan.get_start()
                    duration = scan.get_duration()

                    start_mjd_rounded = round(start_time.mjd * 86400.0 / time_threshold) * time_threshold / 86400.0
                    duration_rounded = round(duration / time_threshold) * time_threshold
                    start_time_rounded = Time(start_mjd_rounded, format='mjd', scale='utc')

                    if time_step is None:
                        times = [start_time_rounded.mjd + (duration_rounded / 2) / 86400.0]
                    else:
                        time_values_array = np.arange(0, duration_rounded, time_step) * u.s
                        times = start_time_rounded.mjd + time_values_array.to(u.d).value

                    times = Time(times, format='mjd', scale='utc')
                    if times.size == 0:
                        logger.warning(f"Empty time array for scan '{scan.name}' in '{obs.get_observation_code()}'")
                        continue

                    source_names.extend([source_name] * times.size)
                    scan_names.extend([scan.name] * times.size)
                    time_values.extend(times)
                    start_times.append(start_time_rounded.mjd)
                    end_times.append((start_time_rounded + duration_rounded * u.s).mjd)
                    processed_scans += 1

                result_df = pd.DataFrame({
                    "source_name": source_names,
                    "scan_name": scan_names,
                    "time": time_values
                })

                if result_df.empty:
                    result_df = pd.DataFrame(columns=CalculatedDataStructure.get_columns("times"))

                logger.info(f"Calculated time arrays for {processed_scans} scans across {len(set(source_names))} sources in '{obs.get_observation_code()}'")
                return result_df

            start_times = []
            end_times = []
            if isinstance(obj, Observation):
                scans = obj.get_scans().get_active_scans(obj)
                start_times = [scan.get_start().mjd for scan in scans]
                end_times = [(scan.get_start() + scan.get_duration() * u.s).mjd for scan in scans]

            metadata = {
                "time_step": time_step,
                "time_threshold": time_threshold,
                "start_time": Time(min(start_times), format='mjd', scale='utc') if start_times else None,
                "end_time": Time(max(end_times), format='mjd', scale='utc') if end_times else None,
                "scan_count": len(start_times)
            }

            return self._process_object(obj, attributes, calculate_times, store_key, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate time arrays for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {str(e)}")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("times")) if isinstance(obj, Observation) else {}

    @time_execution
    def _calculate_interpolated_orbits(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pd.DataFrame | Dict[str, pd.DataFrame]:
        """Calculate interpolated orbit data for active SpaceTelescopes in active scans.

        Args:
            obj: The object to calculate orbits for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "recalculate".

        Returns:
            pd.DataFrame | Dict[str, pd.DataFrame]: For Observation, returns a DataFrame with columns
                ["scan_name", "telescope_code", "x", "y", "z"]. For ScheduleProject, returns a dictionary
                mapping observation codes to DataFrames.

        Notes:
            - Interpolates orbits only for SpaceTelescopes with use_kep=False in active scans.
            - Uses CalculatedDataStructure to validate DataFrame structure and metadata.
            - Stores results under 'interpolated_orbits' key in each Observation's calculated_data.
            - Preserves data with NaN values, logging a warning instead of excluding.
            - Returns empty DataFrame or dict if no active SpaceTelescopes are found.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "interpolated_orbits")
            recalculate = attributes.get("recalculate", False)

            if time_step is not None and time_step <= 0:
                logger.error(f"Invalid time_step: {time_step}. Must be positive.")
                return pd.DataFrame(columns=CalculatedDataStructure.get_columns("interpolated_orbits")) if isinstance(obj, Observation) else {}

            def calculate_orbits(obs: Observation, attrs: Dict[str, Any]) -> pd.DataFrame:
                scans, telescopes, _ = self._get_active_components(obs, require_scans=True, require_telescopes=True)
                if not scans:
                    logger.debug(f"No active scans for observation '{obs.get_observation_code()}'")
                    return pd.DataFrame(columns=CalculatedDataStructure.get_columns("interpolated_orbits"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                time_data = self._calculate_time_arrays(obs, time_attrs)
                if time_data.empty:
                    logger.warning(f"No time arrays available for observation '{obs.get_observation_code()}'")
                    return pd.DataFrame(columns=CalculatedDataStructure.get_columns("interpolated_orbits"))

                active_space_telescopes = [
                    tel for tel in telescopes
                    if isinstance(tel, SpaceTelescope) and not tel.get("use_kep")
                ]
                if not active_space_telescopes:
                    logger.debug(f"No active SpaceTelescopes with use_kep=False in '{obs.get_observation_code()}'")
                    return pd.DataFrame(columns=CalculatedDataStructure.get_columns("interpolated_orbits"))

                scan_names = []
                telescope_codes = []
                x_values = []
                y_values = []
                z_values = []
                excluded_telescopes = []

                with self._orbit_cache_lock:
                    for scan in scans:
                        scan_name = scan.name
                        source = scan.get_source(obs)
                        if not source or not source.isactive:
                            logger.debug(f"Skipping scan '{scan_name}' due to inactive or missing source")
                            continue
                        scan_times = time_data[time_data["scan_name"] == scan_name]
                        if scan_times.empty:
                            logger.debug(f"No valid times for scan '{scan_name}' in source '{source.name}'")
                            continue

                        scan_telescopes = scan.get_telescopes(obs).get_active_items()
                        scan_space_telescopes = [
                            tel for tel in scan_telescopes
                            if isinstance(tel, SpaceTelescope) and not tel.get("use_kep")
                        ]
                        if not scan_space_telescopes:
                            logger.debug(f"No active SpaceTelescopes in scan '{scan_name}'")
                            continue

                        for tel in scan_space_telescopes:
                            tel_code = tel.get_code()
                            orbit_file = tel.get_orbit()
                            if not orbit_file:
                                logger.warning(f"No orbit file for telescope '{tel_code}' in scan '{scan_name}'; excluding")
                                excluded_telescopes.append(tel_code)
                                continue

                            try:
                                orbit_data = self._interpolate_orbit(tel, Time(scan_times["time"]), scan.get_start(), scan.get_start() + scan.get_duration() * u.s)
                                if not orbit_data.empty:
                                    scan_names.extend([scan_name] * len(orbit_data))
                                    telescope_codes.extend([tel_code] * len(orbit_data))
                                    x_values.extend(orbit_data["x"])
                                    y_values.extend(orbit_data["y"])
                                    z_values.extend(orbit_data["z"])
                                    if orbit_data[["x", "y", "z"]].isna().any().any():
                                        logger.warning(f"Orbit data for '{tel_code}' in scan '{scan_name}' contains NaN values")
                                else:
                                    logger.warning(f"No orbit data returned for '{tel_code}' in scan '{scan_name}'")
                                    excluded_telescopes.append(tel_code)
                            except ValueError as e:
                                logger.warning(f"Excluding telescope '{tel_code}' in scan '{scan_name}' due to interpolation error: {str(e)}")
                                excluded_telescopes.append(tel_code)

                result_df = pd.DataFrame({
                    "scan_name": scan_names,
                    "telescope_code": telescope_codes,
                    "x": x_values,
                    "y": y_values,
                    "z": z_values
                })

                if excluded_telescopes:
                    logger.info(f"Excluded {len(set(excluded_telescopes))} telescopes: {', '.join(set(excluded_telescopes))}")
                logger.debug(f"Calculated interpolated orbits for {len(result_df['scan_name'].unique())} scans in '{obs.get_observation_code()}'")
                return result_df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_scans(obj)) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_scans(o)) for o in obj.get_observations())
            }
            return self._process_object(obj, attributes, calculate_orbits, store_key, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate interpolated orbits for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {str(e)}")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("interpolated_orbits")) if isinstance(obj, Observation) else {}

    def _interpolate_orbit(self, telescope: SpaceTelescope, times: Time, start_time: Time, end_time: Time) -> pd.DataFrame:
        """Interpolate orbit data for a space telescope over a given array of times.

        Args:
            telescope (SpaceTelescope): The space telescope.
            times (Time): Array of times for interpolation (must have scale='utc').
            start_time (Time): Start time of the required range (for validation, must have scale='utc').
            end_time (Time): End time of the required range (for validation, must have scale='utc').

        Returns:
            pd.DataFrame: Interpolated orbit data with columns ["x", "y", "z"].

        Notes:
            - Uses the provided times array directly for interpolation.
            - If orbit data partially covers the time range, interpolates only for the available portion.
            - Logs a warning if interpolated data contains NaN values.
            - Returns empty DataFrame with columns from CalculatedDataStructure if no valid data.
        """
        if telescope.get("use_kep"):
            logger.info(f"Skipping interpolation for '{telescope.get_code()}' as use_kep=True")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("interpolated_orbits")[2:])  # Only x, y, z

        orbit_file = telescope.get_orbit()
        if not orbit_file:
            logger.warning(f"No orbit file defined for telescope '{telescope.get_code()}'")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("interpolated_orbits")[2:])  # Only x, y, z

        if times.scale != 'utc':
            logger.debug(f"Converting times from scale '{times.scale}' to 'utc' for '{telescope.get_code()}'")
            times = times.utc
        if start_time.scale != 'utc':
            logger.debug(f"Converting start_time from scale '{start_time.scale}' to 'utc' for '{telescope.get_code()}'")
            start_time = start_time.utc
        if end_time.scale != 'utc':
            logger.debug(f"Converting end_time from scale '{end_time.scale}' to 'utc' for '{telescope.get_code()}'")
            end_time = end_time.utc

        logger.debug(f"Input times for '{telescope.get_code()}': scale={times.scale}, sample={times.isot[:3]}")
        logger.debug(f"Start time: {start_time.isot}, End time: {end_time.isot}")

        mjd_values = times.mjd
        if np.any(np.isnan(mjd_values)) or np.any(np.isinf(mjd_values)):
            logger.error(f"Invalid MJD values in times for '{telescope.get_code()}': {mjd_values}")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("interpolated_orbits")[2:])  # Only x, y, z

        years = times.ymdhms['year']
        if np.any(years < 1900) or np.any(years > 9999):
            logger.error(f"Times out of valid range (1900–9999) for '{telescope.get_code()}': years={years}")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("interpolated_orbits")[2:])  # Only x, y, z

        try:
            orbit_data = self._load_orbit_data(orbit_file, start_time, end_time)
            if not orbit_data:
                logger.warning(f"No valid orbit data for '{telescope.get_code()}' in time range {start_time.isot} to {end_time.isot}")
                return pd.DataFrame(columns=CalculatedDataStructure.get_columns("interpolated_orbits")[2:])  # Only x, y, z
            data_times = orbit_data["times"]
            positions = orbit_data["positions"]

            j2000_mjd = Time("2000-01-01T12:00:00", scale='utc').mjd
            interp_times = (mjd_values - j2000_mjd) * 86400.0  # Convert MJD to seconds since J2000
            logger.debug(f"Computed interp_times for '{telescope.get_code()}': sample={interp_times[:3]}")

            data_start = data_times[0]
            data_end = data_times[-1]
            t_start = (start_time.mjd - j2000_mjd) * 86400.0
            t_end = (end_time.mjd - j2000_mjd) * 86400.0

            t_start = max(t_start, data_times[0])
            t_end = min(t_end, data_times[-1])
            valid_mask = (interp_times >= t_start) & (interp_times <= t_end)
            valid_interp_times = interp_times[valid_mask]
            valid_times = times[valid_mask]

            if not valid_interp_times.size:
                logger.warning(f"No valid interpolation times for '{telescope.get_code()}' in range {Time(t_start / 86400.0 + j2000_mjd, format='mjd', scale='utc').isot} to {Time(t_end / 86400.0 + j2000_mjd, format='mjd', scale='utc').isot}")
                return pd.DataFrame(columns=CalculatedDataStructure.get_columns("interpolated_orbits")[2:])  # Only x, y, z

            unique_indices = np.unique(data_times, return_index=True)[1]
            filtered_times = data_times[unique_indices]
            filtered_positions = positions[unique_indices]

            if len(filtered_times) < 2:
                logger.warning(f"Too few points ({len(filtered_times)}) for interpolation for '{telescope.get_code()}'")
                return pd.DataFrame(columns=CalculatedDataStructure.get_columns("interpolated_orbits")[2:])  # Only x, y, z

            full_positions = np.full((len(times), 3), np.nan, dtype=float)

            method = telescope.get("interpolation_method") or "linear"
            logger.debug(f"Using interpolation method '{method}' for '{telescope.get_code()}'")
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
                logger.warning(f"Interpolated positions for '{telescope.get_code()}' contain NaN values in range {Time(t_start / 86400.0 + j2000_mjd, format='mjd', scale='utc').isot} to {Time(t_end / 86400.0 + j2000_mjd, format='mjd', scale='utc').isot}")

            result_df = pd.DataFrame({
                "x": full_positions[:, 0],
                "y": full_positions[:, 1],
                "z": full_positions[:, 2]
            })

            logger.info(f"Interpolated orbit for '{telescope.get_code()}' using {method} with {len(valid_interp_times)} points")
            return result_df

        except Exception as e:
            logger.error(f"Failed to interpolate orbit for '{telescope.get_code()}': {str(e)}")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("interpolated_orbits")[2:])  # Only x, y, z

    def _load_orbit_data(self, orbit_file: str, start_time: Optional[Time] = None, end_time: Optional[Time] = None) -> Dict[str, np.ndarray]:
        """Load orbit data from a CCSDS OEM 2.0 styled file, optionally filtering by time range.

        Args:
            orbit_file (str): Path to the orbit file.
            start_time (Optional[Time]): Start time for filtering data.
            end_time (Optional[Time]): End time for filtering data.

        Returns:
            Dict[str, np.ndarray]: Dictionary containing times, positions, and velocities. Returns empty dict if no valid data.

        Raises:
            FileNotFoundError: If orbit file does not exist.
            ValueError: If file format is invalid or insufficient data points.
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
            try:
                logger.debug(f"Sample time strings from orbit file '{orbit_file}': {time_strs[:3]}")
                times = Time(time_strs, format='isot', scale='utc')
            except ValueError as e:
                logger.error(f"Failed to parse time strings in orbit file '{orbit_file}': {str(e)}")
                raise ValueError(f"Invalid time format in orbit file: {str(e)}")
            
            j2000_epoch = Time("2000-01-01T12:00:00", scale='utc')
            try:
                times_sec = (times - j2000_epoch).sec
            except Exception as e:
                logger.error(f"Error converting times to seconds since J2000 for '{orbit_file}': {str(e)}")
                raise ValueError(f"Time conversion error: {str(e)}")
            
            positions = np.zeros((len(valid_lines), 3))
            velocities = np.zeros((len(valid_lines), 3))
            for i, line in enumerate(valid_lines):
                parts = re.split(r'\s+', line)
                try:
                    x, y, z = map(float, parts[1:4])  # km -> m
                    vx, vy, vz = map(float, parts[4:7])  # km/s -> m/s
                    positions[i] = [x * 1000, y * 1000, z * 1000]
                    velocities[i] = [vx * 1000, vy * 1000, vz * 1000]
                except ValueError as e:
                    logger.warning(f"Invalid data in orbit file '{orbit_file}' at line {i+1}: {str(e)}")
                    return {}
            
            if np.any(np.isnan(positions)) or np.any(np.isnan(velocities)):
                logger.warning(f"Orbit file '{orbit_file}' contains NaN values")
                return {}
            
            orbit_data = {
                "times": times_sec,
                "positions": positions,
                "velocities": velocities
            }
            
            if start_time is not None and end_time is not None:
                t_start = (start_time - j2000_epoch).sec
                t_end = (end_time - j2000_epoch).sec
                mask = (orbit_data["times"] >= t_start) & (orbit_data["times"] <= t_end)
                if not np.any(mask):
                    logger.warning(f"No orbit data within time range {start_time.isot} to {end_time.isot} for file '{orbit_file}'")
                    return {}
                orbit_data = {
                    "times": orbit_data["times"][mask],
                    "positions": orbit_data["positions"][mask],
                    "velocities": orbit_data["velocities"][mask]
                }
            
            logger.info(f"Loaded orbit data from '{orbit_file}' with {len(orbit_data['times'])} points")
            return orbit_data
        
        except FileNotFoundError:
            logger.error(f"Orbit file '{orbit_file}' not found")
            raise
        except ValueError as e:
            logger.error(f"Error parsing orbit file: {str(e)}")
            raise
        except Exception as e:
            logger.warning(f"Unexpected error loading orbit file '{orbit_file}': {str(e)}")
            return {}

    def _solve_kepler(self, initial: float, e: float, tol: float = 1e-8, max_iter: int = 200) -> float:
        """Solve Kepler's equation iteratively to find the eccentric anomaly.

        Args:
            initial (float): Mean anomaly (radians).
            e (float): Eccentricity (must be < 1).
            tol (float): Convergence tolerance.
            max_iter (int): Maximum iterations.

        Returns:
            float: Eccentric anomaly (radians).
        """
        if e >= 1:
            raise ValueError("Eccentricity must be < 1 for elliptical orbit")
        x = initial if e < 0.9 else np.pi
        for _ in range(max_iter):
            f = x - e * np.sin(x) - initial
            df = 1 - e * np.cos(x)
            dx = -f / df
            x += dx
            if abs(dx) < tol:
                return x
        logger.warning(f"Kepler's equation did not converge for e={e}, initial={initial}")
        return x

    @time_execution
    def _calculate_telescope_positions(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pd.DataFrame | Dict[str, pd.DataFrame]:
        """Calculate telescope positions in GCRS (J2000) for all active scans using times from time_arrays and interpolated orbits.

        Args:
            obj: The object to calculate positions for.
            attributes: Parameters including "time_step", "store_key", "recalculate".

        Returns:
            pd.DataFrame | Dict[str, pd.DataFrame]: For Observation, returns a DataFrame with columns
                ["scan_name", "telescope_code", "x", "y", "z"]. For ScheduleProject, returns a dictionary
                mapping observation codes to DataFrames.

        Notes:
            - Uses CalculatedDataStructure to validate DataFrame structure and metadata.
            - Stores results under 'telescope_positions' key in each Observation's calculated_data.
            - Returns empty DataFrame or dict if no valid scans or telescopes are found.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "telescope_positions")
            recalculate = attributes.get("recalculate", False)
            excluded_telescopes = []

            def calculate_positions(obs: Observation, attrs: Dict[str, Any]) -> pd.DataFrame:
                scans, telescopes, _ = self._get_active_components(obs)
                if not scans:
                    logger.debug(f"No active scans for observation '{obs.get_observation_code()}'")
                    return pd.DataFrame(columns=CalculatedDataStructure.get_columns("telescope_positions"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                time_data = self._calculate_time_arrays(obs, time_attrs)
                if time_data.empty:
                    logger.warning(f"No time arrays available for observation '{obs.get_observation_code()}'")
                    return pd.DataFrame(columns=CalculatedDataStructure.get_columns("telescope_positions"))

                has_orbit_telescopes = any(isinstance(tel, SpaceTelescope) and not tel.get("use_kep") for tel in telescopes)
                orbit_data = pd.DataFrame(columns=CalculatedDataStructure.get_columns("interpolated_orbits"))
                if has_orbit_telescopes:
                    orbit_attrs = {"time_step": time_step, "store_key": "interpolated_orbits", "recalculate": recalculate}
                    orbit_data = self._calculate_interpolated_orbits(obs, orbit_attrs)
                    logger.debug(f"Orbit data for '{obs.get_observation_code()}': {'available' if not orbit_data.empty else 'not available'}")

                scan_names = []
                telescope_codes = []
                x_values = []
                y_values = []
                z_values = []

                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_scan_positions, scan, obs, time_step, time_data, orbit_data): scan
                        for scan in scans
                    }
                    for future in futures:
                        scan = futures[future]
                        scan_name = scan.name
                        scan_positions = future.result()
                        if not scan_positions.empty:
                            scan_names.extend([scan_name] * len(scan_positions))
                            telescope_codes.extend(scan_positions["telescope_code"])
                            x_values.extend(scan_positions["x"])
                            y_values.extend(scan_positions["y"])
                            z_values.extend(scan_positions["z"])
                        else:
                            excluded_telescopes.extend([tel.get_code() for tel in scan.get_telescopes(obs).get_active_items()])

                result_df = pd.DataFrame({
                    "scan_name": scan_names,
                    "telescope_code": telescope_codes,
                    "x": x_values,
                    "y": y_values,
                    "z": z_values
                })

                if excluded_telescopes:
                    logger.info(f"Excluded {len(set(excluded_telescopes))} telescopes: {', '.join(set(excluded_telescopes))}")
                logger.debug(f"Calculated positions for {len(result_df['scan_name'].unique())} scans in '{obs.get_observation_code()}'")
                return result_df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_scans(obj)) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_scans(o)) for o in obj.get_observations())
            }
            return self._process_object(obj, attributes, calculate_positions, store_key, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate telescope positions for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {str(e)}")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("telescope_positions")) if isinstance(obj, Observation) else {}

    def _process_scan_positions(self, scan: Scan, observation: Observation, time_step: Optional[float], time_data: pd.DataFrame, orbit_data: pd.DataFrame) -> pd.DataFrame:
        """Process telescope positions for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds).
            time_data (pd.DataFrame): Precomputed time arrays from _calculate_time_arrays.
            orbit_data (pd.DataFrame): Precomputed orbit data with columns ["scan_name", "telescope_code", "x", "y", "z"].

        Returns:
            pd.DataFrame: Positions for active telescopes with columns ["telescope_code", "x", "y", "z"].
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("telescope_positions")[1:])  # Exclude scan_name

        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [tel for tel in scan_telescopes.get_active_items() if tel.isactive]
        scan_name = scan.name
        source_name = source.name

        if not active_telescopes:
            logger.warning(f"No active telescopes for scan '{scan_name}' starting at {scan.get_start().isot}")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("telescope_positions")[1:])  # Exclude scan_name

        scan_times = time_data[time_data["scan_name"] == scan_name]["time"]
        logger.debug(f"scan_times type: {type(scan_times)}, content: {scan_times.values}")
        if scan_times.empty:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("telescope_positions")[1:])  # Exclude scan_name

        if isinstance(scan_times, pd.Series):
            try:
                scan_times = Time(scan_times.values)
            except Exception as e:
                logger.error(f"Failed to convert scan_times to Time for scan '{scan_name}': {str(e)}")
                return pd.DataFrame(columns=CalculatedDataStructure.get_columns("telescope_positions")[1:])

        telescope_codes = []
        x_values = []
        y_values = []
        z_values = []

        ground_tels = [tel for tel in active_telescopes if not isinstance(tel, SpaceTelescope)]
        kep_space_tels = [tel for tel in active_telescopes if isinstance(tel, SpaceTelescope) and tel.get("use_kep")]
        orbit_space_tels = [tel for tel in active_telescopes if isinstance(tel, SpaceTelescope) and not tel.get("use_kep")]

        if ground_tels:
            x = np.array([tel.get_coordinates()[0] for tel in ground_tels])
            y = np.array([tel.get_coordinates()[1] for tel in ground_tels])
            z = np.array([tel.get_coordinates()[2] for tel in ground_tels])
            vx = np.array([tel.get(["vx", "vy", "vz"])["vx"] for tel in ground_tels])
            vy = np.array([tel.get(["vx", "vy", "vz"])["vy"] for tel in ground_tels])
            vz = np.array([tel.get(["vx", "vy", "vz"])["vz"] for tel in ground_tels])
            logger.debug(f"Ground telescope coordinates shape: x={x.shape}, vx={vx.shape}")
            dt = np.array((scan_times - Time("2000-01-01T12:00:00")).sec)
            itrs_coords = CartesianRepresentation(
                x[:, None] + vx[:, None] * dt,
                y[:, None] + vy[:, None] * dt,
                z[:, None] + vz[:, None] * dt,
                unit=u.m
            )
            itrs = ITRS(itrs_coords, obstime=scan_times)
            gcrs = itrs.transform_to(GCRS(obstime=scan_times))
            ground_positions = np.stack([gcrs.cartesian.x.value, gcrs.cartesian.y.value, gcrs.cartesian.z.value], axis=-1)
            for i, tel in enumerate(ground_tels):
                tel_code = tel.get_code()
                if not np.all(np.isnan(ground_positions[i])):
                    telescope_codes.extend([tel_code] * len(scan_times))
                    x_values.extend(ground_positions[i, :, 0])
                    y_values.extend(ground_positions[i, :, 1])
                    z_values.extend(ground_positions[i, :, 2])
                else:
                    logger.warning(f"All positions are NaN for ground telescope '{tel_code}' in scan '{scan_name}'")

        if kep_space_tels:
            for tel in kep_space_tels:
                tel_code = tel.get_code()
                try:
                    pos_df = self._compute_telescope_position(tel, scan_times)
                    if not pos_df[["x", "y", "z"]].isna().all().all():
                        telescope_codes.extend([tel_code] * len(pos_df))
                        x_values.extend(pos_df["x"])
                        y_values.extend(pos_df["y"])
                        z_values.extend(pos_df["z"])
                    else:
                        logger.warning(f"All positions are NaN for Keplerian telescope '{tel_code}' in scan '{scan_name}'")
                except ValueError as e:
                    logger.warning(f"Position calculation failed for Keplerian telescope '{tel_code}' in scan '{scan_name}': {str(e)}")

        if orbit_space_tels:
            scan_orbit_data = orbit_data[orbit_data["scan_name"] == scan_name]
            for tel in orbit_space_tels:
                tel_code = tel.get_code()
                tel_positions = scan_orbit_data[scan_orbit_data["telescope_code"] == tel_code]
                if not tel_positions.empty and len(tel_positions) == len(scan_times):
                    telescope_codes.extend([tel_code] * len(tel_positions))
                    x_values.extend(tel_positions["x"])
                    y_values.extend(tel_positions["y"])
                    z_values.extend(tel_positions["z"])
                else:
                    logger.warning(f"No or mismatched orbit data for telescope '{tel_code}' in scan '{scan_name}'")

        result_df = pd.DataFrame({
            "telescope_code": telescope_codes,
            "x": x_values,
            "y": y_values,
            "z": z_values
        })

        if result_df.empty:
            logger.warning(f"No valid positions computed for scan '{scan_name}'")
        return result_df

    def _compute_telescope_position(self, telescope: Telescope | SpaceTelescope, time: Time) -> pd.DataFrame:
        """Compute a telescope's GCRS position at specified times.

        Args:
            telescope (Telescope | SpaceTelescope): The telescope to compute position for.
            time (Time): Single time or array of times for calculation.

        Returns:
            pd.DataFrame: GCRS coordinates with columns ["x", "y", "z"]. Returns empty DataFrame if computation fails.

        Notes:
            - For ground telescopes, applies velocity corrections and transforms ITRS to GCRS.
            - For SpaceTelescopes with use_kep=True, computes positions using Keplerian elements.
            - For SpaceTelescopes with use_kep=False, returns empty DataFrame (positions should be precomputed).
            - Uses CalculatedDataStructure for column validation.
        """
        try:
            single_time = not isinstance(time, Time) or time.isscalar
            times = time if not single_time else Time([time])
            n_times = len(times)
            empty_result = pd.DataFrame(columns=CalculatedDataStructure.get_columns("telescope_positions")[2:])  # Only x, y, z

            if isinstance(telescope, Telescope) and not isinstance(telescope, SpaceTelescope):
                x, y, z = telescope.get_coordinates()
                res = telescope.get(["vx", "vy", "vz"])
                vx, vy, vz = res["vx"], res["vy"], res["vz"]
                # Log input types for debugging
                logger.debug(f"Input types for telescope '{telescope.get_code()}': x={type(x)}, vx={type(vx)}")
                # Ensure coordinates and velocities are NumPy arrays
                x, y, z = np.array(x), np.array(y), np.array(z)
                vx, vy, vz = np.array(vx), np.array(vy), np.array(vz)
                # Ensure dt is a NumPy array for vectorized operations
                dt = np.array((times - Time("2000-01-01T12:00:00")).sec)
                itrs_coords = CartesianRepresentation(
                    x + vx * dt,
                    y + vy * dt,
                    z + vz * dt,
                    unit=u.m
                )
                itrs = ITRS(itrs_coords, obstime=times)
                gcrs = itrs.transform_to(GCRS(obstime=times))
                pos = np.stack([gcrs.cartesian.x.value, gcrs.cartesian.y.value, gcrs.cartesian.z.value], axis=-1)
                if np.any(np.isnan(pos)):
                    logger.warning(f"Computed NaN position for ground telescope '{telescope.get_code()}' at {times[0].isot}")
                result_df = pd.DataFrame({
                    "x": pos[:, 0],
                    "y": pos[:, 1],
                    "z": pos[:, 2]
                })
                return result_df.iloc[0:1] if single_time else result_df

            elif isinstance(telescope, SpaceTelescope):
                if telescope.get("use_kep"):
                    kepler = telescope.get("kepler_elements")
                    if kepler is None:
                        logger.warning(f"No Keplerian elements defined for telescope '{telescope.get_code()}'")
                        return empty_result

                    a = kepler["a"]  # semi-major axis (m)
                    e = kepler["e"]  # eccentricity
                    i = np.radians(kepler["i"])  # inclination (deg to rad)
                    raan = np.radians(kepler["raan"])  # RA of ascending node (deg to rad)
                    argp = np.radians(kepler["argp"])  # argument of periapsis (deg to rad)
                    nu0 = np.radians(kepler["nu"])  # true anomaly at epoch (deg to rad)
                    epoch = kepler["epoch"]
                    mu = kepler["mu"]  # gravitational parameter (m^3/s^2)

                    n = np.sqrt(mu / a**3)
                    dt = np.array((times - epoch).sec)  # Ensure dt is a NumPy array
                    M = nu0 + n * dt

                    solve_kepler_vec = np.vectorize(self._solve_kepler)
                    E = solve_kepler_vec(M, e)

                    cos_nu = (np.cos(E) - e) / (1 - e * np.cos(E))
                    sin_nu = (np.sqrt(1 - e**2) * np.sin(E)) / (1 - e * np.cos(E))
                    nu = np.arctan2(sin_nu, cos_nu)

                    r = a * (1 - e**2) / (1 + e * np.cos(nu))
                    p = np.array([r * np.cos(nu), r * np.sin(nu), np.zeros_like(r)]).T

                    R1 = np.array([
                        [np.cos(raan), -np.sin(raan), 0],
                        [np.sin(raan), np.cos(raan), 0],
                        [0, 0, 1]
                    ])
                    R2 = np.array([
                        [1, 0, 0],
                        [0, np.cos(i), -np.sin(i)],
                        [0, np.sin(i), np.cos(i)]
                    ])
                    R3 = np.array([
                        [np.cos(argp), -np.sin(argp), 0],
                        [np.sin(argp), np.cos(argp), 0],
                        [0, 0, 1]
                    ])
                    R = R1 @ R2 @ R3
                    pos = np.array([R @ p_i for p_i in p]) if not single_time else (R @ p[0])
                    if np.any(np.isnan(pos)):
                        logger.warning(f"Keplerian position for '{telescope.get_code()}' at {times[0].isot} contains NaN")
                    result_df = pd.DataFrame({
                        "x": pos[:, 0] if not single_time else [pos[0]],
                        "y": pos[:, 1] if not single_time else [pos[1]],
                        "z": pos[:, 2] if not single_time else [pos[2]]
                    })
                    return result_df
                else:
                    logger.warning(f"Orbit file position for '{telescope.get_code()}' at {times[0].isot} should be precomputed in interpolated_orbits")
                    return empty_result

            raise ValueError(f"Unsupported telescope type: {type(telescope)}")
        except Exception as e:
            logger.warning(f"Unexpected error in computing position for '{telescope.get_code()}' at {times[0].isot}: {str(e)}")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("telescope_positions")[2:])

    @time_execution
    def _calculate_source_visibility(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pd.DataFrame | Dict[str, pd.DataFrame]:
        """Calculate source visibility for all active scans in the observation or project.

        Args:
            obj: The object to calculate visibility for.
            attributes: Parameters including "time_step", "store_key", "position_store_key", "recalculate".

        Returns:
            pd.DataFrame | Dict[str, pd.DataFrame]: For Observation, returns a DataFrame with columns
                ["source_name", "scan_name", "telescope_code", "visibility"]. For ScheduleProject, returns
                a dictionary mapping observation codes to DataFrames.

        Notes:
            - Uses CalculatedDataStructure to validate DataFrame structure and metadata.
            - Stores results under 'source_visibility' key in each Observation's calculated_data.
            - Returns empty DataFrame or dict if no valid scans or telescopes are found.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "source_visibility")
            position_store_key = attributes.get("position_store_key", "telescope_positions")
            recalculate = attributes.get("recalculate", False)

            def calculate_visibility(obs: Observation, attrs: Dict[str, Any]) -> pd.DataFrame:
                scans, _, _ = self._get_active_components(obs)
                if not scans:
                    logger.debug(f"No active scans for observation '{obs.get_observation_code()}'")
                    return pd.DataFrame(columns=CalculatedDataStructure.get_columns("source_visibility"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": recalculate}
                time_data = self._calculate_time_arrays(obs, time_attrs)
                position_data = self._calculate_telescope_positions(obs, position_attrs)

                if time_data.empty or position_data.empty:
                    logger.error(f"Missing time or position data for '{obs.get_observation_code()}'")
                    return pd.DataFrame(columns=CalculatedDataStructure.get_columns("source_visibility"))

                source_names = []
                scan_names = []
                telescope_codes = []
                visibility_values = []

                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_source_visibility, scan, obs, time_step, time_data, position_data): scan
                        for scan in scans
                    }
                    for future in futures:
                        scan = futures[future]
                        scan_result = future.result()
                        if not scan_result.empty:
                            source_names.extend(scan_result["source_name"])
                            scan_names.extend(scan_result["scan_name"])
                            telescope_codes.extend(scan_result["telescope_code"])
                            visibility_values.extend(scan_result["visibility"])

                result_df = pd.DataFrame({
                    "source_name": source_names,
                    "scan_name": scan_names,
                    "telescope_code": telescope_codes,
                    "visibility": visibility_values
                })

                if result_df.empty:
                    logger.warning(f"No visibility data computed for observation '{obs.get_observation_code()}'")
                    result_df = pd.DataFrame(columns=CalculatedDataStructure.get_columns("source_visibility"))

                logger.debug(f"Computed visibility for {len(result_df['scan_name'].unique())} scans in '{obs.get_observation_code()}'")
                return result_df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_scans(obj)) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_scans(o)) for o in obj.get_observations()),
                "position_store_key": position_store_key
            }
            return self._process_object(obj, attributes, calculate_visibility, store_key, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate source visibility for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {str(e)}")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("source_visibility")) if isinstance(obj, Observation) else {}

    def _process_source_visibility(self, scan: Scan, observation: Observation, time_step: Optional[float], time_data: pd.DataFrame, position_data: pd.DataFrame) -> pd.DataFrame:
        """Process source visibility for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds). If None, uses mean time.
            time_data (pd.DataFrame): Precomputed time arrays from _calculate_time_arrays.
            position_data (pd.DataFrame): Precomputed telescope positions.

        Returns:
            pd.DataFrame: Visibility data for the scan with columns ["source_name", "scan_name", "telescope_code", "visibility"].

        Notes:
            - Ensures visibility array length matches scan_times length.
            - Sets visibility to False for times where telescope positions are NaN.
            - Supports both ground and space telescopes with appropriate visibility checks.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("source_visibility"))

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_active_items() if t.isactive]
        if not active_telescopes:
            logger.warning(f"No active telescopes for scan '{scan_name}' in observation '{observation.get_observation_code()}'")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("source_visibility"))

        scan_times = time_data[time_data["scan_name"] == scan_name]["time"]
        if scan_times.empty:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("source_visibility"))

        scan_positions = position_data[position_data["scan_name"] == scan_name]
        if scan_positions.empty:
            logger.warning(f"No position data for scan '{scan_name}' in observation '{observation.get_observation_code()}'")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("source_visibility"))

        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
        tel_codes = [tel.get_code() for tel in active_telescopes]
        n_times = len(scan_times)

        source_names = []
        scan_names = []
        telescope_codes = []
        visibility_values = []

        positions = np.array([
            scan_positions[scan_positions["telescope_code"] == code][["x", "y", "z"]].values
            if code in scan_positions["telescope_code"].values else np.full((n_times, 3), np.nan)
            for code in tel_codes
        ])

        nan_positions = np.any(np.isnan(positions), axis=2)

        visibility_array = np.full((len(tel_codes), n_times), False, dtype=bool)

        ground_tels = [tel for tel in active_telescopes if not isinstance(tel, SpaceTelescope)]
        space_tels = [tel for tel in active_telescopes if isinstance(tel, SpaceTelescope)]

        if ground_tels:
            ground_codes = [tel.get_code() for tel in ground_tels]
            ground_indices = [tel_codes.index(code) for code in ground_codes]
            ground_positions = positions[ground_indices]
            ground_nan = nan_positions[ground_indices]

            gcrs_coords = CartesianRepresentation(
                x=ground_positions[:, :, 0] * u.m,
                y=ground_positions[:, :, 1] * u.m,
                z=ground_positions[:, :, 2] * u.m
            )
            itrs = GCRS(gcrs_coords, obstime=scan_times).transform_to(ITRS(obstime=scan_times))
            locations = itrs.earth_location

            altaz = source_coord.transform_to(AltAz(obstime=scan_times, location=locations))
            hadec = source_coord.transform_to(HADec(obstime=scan_times, location=locations))
            el = altaz.alt.deg
            az = altaz.az.deg
            ha = hadec.ha.deg
            dec = hadec.dec.deg

            for i, tel in enumerate(ground_tels):
                tel_code = tel.get_code()
                mount_type = tel.get("mount_type").value
                is_visible = np.full(n_times, False, dtype=bool)

                valid_positions = ~ground_nan[i]
                if not np.any(valid_positions):
                    logger.warning(f"All positions are NaN for ground telescope '{tel_code}' in scan '{scan_name}'")
                    visibility_array[ground_indices[i]] = is_visible
                    continue

                if mount_type == "AZIM":
                    el_range = tel.get_elevation_range()
                    az_range = tel.get_azimuth_range()
                    is_visible[valid_positions] = (
                        (float(el_range[0]) <= el[i, valid_positions]) &
                        (el[i, valid_positions] <= float(el_range[1])) &
                        (float(az_range[0]) <= az[i, valid_positions]) &
                        (az[i, valid_positions] <= float(az_range[1]))
                    )
                elif mount_type == "EQUA":
                    ha_range = tel.get_azimuth_range()
                    dec_range = tel.get_elevation_range()
                    is_visible[valid_positions] = (
                        (float(dec_range[0]) <= dec[i, valid_positions]) &
                        (dec[i, valid_positions] <= float(dec_range[1])) &
                        (float(ha_range[0]) <= ha[i, valid_positions]) &
                        (ha[i, valid_positions] <= float(ha_range[1]))
                    )
                else:
                    logger.warning(f"Unsupported mount type '{mount_type}' for telescope '{tel_code}' in scan '{scan_name}'")
                    is_visible = np.full(n_times, False, dtype=bool)

                visibility_array[ground_indices[i]] = is_visible
                logger.debug(f"Computed visibility for ground telescope '{tel_code}' in scan '{scan_name}': {np.sum(is_visible)} visible points")

        if space_tels:
            space_codes = [tel.get_code() for tel in space_tels]
            space_indices = [tel_codes.index(code) for code in space_codes]
            space_nan = nan_positions[space_indices]

            for i, tel in enumerate(space_tels):
                tel_code = tel.get_code()
                is_visible = np.full(n_times, False, dtype=bool)
                valid_positions = ~space_nan[i]
                is_visible[valid_positions] = True
                visibility_array[space_indices[i]] = is_visible
                logger.debug(f"Computed visibility for space telescope '{tel_code}' in scan '{scan_name}': {np.sum(is_visible)} visible points")

        for i, tel_code in enumerate(tel_codes):
            source_names.extend([source_name] * n_times)
            scan_names.extend([scan_name] * n_times)
            telescope_codes.extend([tel_code] * n_times)
            visibility_values.extend(visibility_array[i].tolist())

        result_df = pd.DataFrame({
            "source_name": source_names,
            "scan_name": scan_names,
            "telescope_code": telescope_codes,
            "visibility": visibility_values
        })

        if result_df.empty:
            logger.warning(f"No visibility data computed for scan '{scan_name}'")
            result_df = pd.DataFrame(columns=CalculatedDataStructure.get_columns("source_visibility"))

        logger.debug(f"Computed visibility for {len(tel_codes)} telescopes in scan '{scan_name}'")
        return result_df
    
    @time_execution
    def _calculate_uv_coverage(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pd.DataFrame | Dict[str, pd.DataFrame]:
        """Calculate (u,v,w) coverage for all scans in the observation or project in geometric coordinates (meters).

        Args:
            obj: The object to calculate UV coverage for.
            attributes: Parameters including "time_step", "store_key", "recalculate".

        Returns:
            pd.DataFrame | Dict[str, pd.DataFrame]: For Observation, returns a DataFrame with columns
                ["source_name", "scan_name", "baseline", "u", "v", "w"]. For ScheduleProject, returns
                a dictionary mapping observation codes to DataFrames.

        Notes:
            - Uses CalculatedDataStructure to validate DataFrame structure and metadata.
            - Stores results under 'uv_coverage' key in each Observation's calculated_data.
            - Returns empty DataFrame or dict if no valid scans or telescopes are found.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "uv_coverage")
            recalculate = attributes.get("recalculate", False)
            if "freq_name" in attributes:
                logger.info(f"Ignoring 'freq_name' attribute for UV coverage calculation in geometric coordinates")

            def calculate_uv(obs: Observation, attrs: Dict[str, Any]) -> pd.DataFrame:
                scans, telescopes, _ = self._get_active_components(obs, require_telescopes=True, min_telescopes=2)
                if not scans:
                    logger.debug(f"No active scans for observation '{obs.get_observation_code()}'")
                    return pd.DataFrame(columns=CalculatedDataStructure.get_columns("uv_coverage"))

                visibility_attrs = {"time_step": time_step, "store_key": "source_visibility", "recalculate": recalculate}
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": recalculate}
                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                time_data = self._calculate_time_arrays(obs, time_attrs)
                visibility_data = self._calculate_source_visibility(obs, visibility_attrs)
                position_data = self._calculate_telescope_positions(obs, position_attrs)

                if time_data.empty or visibility_data.empty or position_data.empty:
                    logger.error(f"Missing required data for '{obs.get_observation_code()}'")
                    return pd.DataFrame(columns=CalculatedDataStructure.get_columns("uv_coverage"))

                source_names = []
                scan_names = []
                baselines = []
                u_values = []
                v_values = []
                w_values = []

                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_uv_coverage, scan, obs, time_step, time_data, visibility_data, position_data): scan
                        for scan in scans
                    }
                    for future in futures:
                        scan = futures[future]
                        scan_result = future.result()
                        if not scan_result.empty:
                            source_names.extend(scan_result["source_name"])
                            scan_names.extend(scan_result["scan_name"])
                            baselines.extend(scan_result["baseline"])
                            u_values.extend(scan_result["u"])
                            v_values.extend(scan_result["v"])
                            w_values.extend(scan_result["w"])

                result_df = pd.DataFrame({
                    "source_name": source_names,
                    "scan_name": scan_names,
                    "baseline": baselines,
                    "u": u_values,
                    "v": v_values,
                    "w": w_values
                })

                if result_df.empty:
                    logger.warning(f"No UV coverage data computed for observation '{obs.get_observation_code()}'")
                    result_df = pd.DataFrame(columns=CalculatedDataStructure.get_columns("uv_coverage"))

                logger.debug(f"Computed UV coverage for {len(result_df['scan_name'].unique())} scans in '{obs.get_observation_code()}'")
                return result_df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_scans(obj)) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_scans(o)) for o in obj.get_observations())
            }
            return self._process_object(obj, attributes, calculate_uv, store_key, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate UV coverage for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {str(e)}")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("uv_coverage")) if isinstance(obj, Observation) else {}

    def _process_uv_coverage(self, scan: Scan, observation: Observation, time_step: Optional[float], time_data: pd.DataFrame, visibility_data: pd.DataFrame, position_data: pd.DataFrame) -> pd.DataFrame:
        """Process UV coverage for a single scan using vectorized computations in geometric coordinates (meters).

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds).
            time_data (pd.DataFrame): Precomputed time arrays from _calculate_time_arrays.
            visibility_data (pd.DataFrame): Precomputed visibility data.
            position_data (pd.DataFrame): Precomputed position data.

        Returns:
            pd.DataFrame: UV points in meters with columns ["source_name", "scan_name", "baseline", "u", "v", "w"].

        Notes:
            - Outputs NaN for UVW points where source is not visible or telescope positions are NaN.
            - Ensures output array size matches input times for index correspondence.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("uv_coverage"))

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_active_items() if t.isactive]

        if len(active_telescopes) < 2:
            logger.warning(f"Insufficient telescopes ({len(active_telescopes)}) for UV coverage in scan '{scan_name}'")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("uv_coverage"))

        scan_times = time_data[time_data["scan_name"] == scan_name]["time"]
        if scan_times.empty:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("uv_coverage"))

        scan_visibility = visibility_data[visibility_data["scan_name"] == scan_name]
        scan_positions = position_data[position_data["scan_name"] == scan_name]
        if scan_visibility.empty or scan_positions.empty:
            logger.warning(f"No visibility or position data for scan '{scan_name}' in observation '{observation.get_observation_code()}'")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("uv_coverage"))

        tel_codes = [tel.get_code() for tel in active_telescopes]
        n_times = len(scan_times)

        visibility = np.full((len(tel_codes), n_times), False, dtype=bool)
        for i, code in enumerate(tel_codes):
            vis_data = scan_visibility[scan_visibility["telescope_code"] == code]["visibility"].values
            if vis_data.size != n_times:
                logger.warning(f"Visibility data for telescope '{code}' in scan '{scan_name}' has incorrect length ({vis_data.size} vs expected {n_times})")
                visibility[i, :] = False
            else:
                try:
                    visibility[i, :] = vis_data.astype(bool)
                except Exception as e:
                    logger.error(f"Failed to process visibility data for telescope '{code}' in scan '{scan_name}': {str(e)}")
                    visibility[i, :] = False

        positions = np.array([
            scan_positions[scan_positions["telescope_code"] == code][["x", "y", "z"]].values
            if code in scan_positions["telescope_code"].values else np.full((n_times, 3), np.nan)
            for code in tel_codes
        ])

        if positions.shape[1] != n_times:
            logger.error(f"Mismatched position data length for scan '{scan_name}': {positions.shape[1]} positions vs {n_times} times")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("uv_coverage"))

        try:
            uv_points_df = self._compute_uv_at_time(active_telescopes, scan_times, source, visibility, positions)
        except Exception as e:
            logger.error(f"Failed to calculate UV coverage for scan '{scan_name}': {str(e)}")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("uv_coverage"))

        if uv_points_df.empty:
            logger.warning(f"No valid UV points computed for scan '{scan_name}'")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("uv_coverage"))

        result_df = uv_points_df.assign(
            source_name=source_name,
            scan_name=scan_name
        )[["source_name", "scan_name", "baseline", "u", "v", "w"]]

        valid_point_count = len(result_df[~result_df[["u", "v", "w"]].isna().any(axis=1)])
        logger.debug(f"Computed {valid_point_count} valid UV points for scan '{scan_name}' across {len(result_df['baseline'].unique())} baselines")
        return result_df

    def _compute_uv_at_time(self, telescopes: List[Telescope | SpaceTelescope], times: Time, source: Optional[Source] = None, visibility: Optional[np.ndarray] = None, gcrs_positions: Optional[np.ndarray] = None) -> pd.DataFrame:
        """Compute UVW coordinates for multiple times in geometric coordinates (meters) using vectorized operations.

        Args:
            telescopes (List[Telescope | SpaceTelescope]): List of telescopes.
            times (Time): Array of observation times.
            source (Optional[Source]): Source for UV calculation.
            visibility (Optional[np.ndarray]): Visibility array of shape (n_telescopes, n_times).
            gcrs_positions (Optional[np.ndarray]): GCRS positions of shape (n_telescopes, n_times, 3).

        Returns:
            pd.DataFrame: UVW coordinates in meters with columns ["baseline", "u", "v", "w"],
            where rows contain NaN for non-visible times or invalid positions.

        Notes:
            - Uses CalculatedDataStructure to validate DataFrame structure.
        """
        if not telescopes or len(telescopes) < 2:
            logger.warning(f"Insufficient telescopes ({len(telescopes)}) to compute (u,v,w) at {times[0].isot}")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("uv_coverage")[2:])  # Only baseline, u, v, w

        if source is None:
            logger.warning("No source provided; cannot calculate (u,v,w)")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("uv_coverage")[2:])

        if visibility is None or gcrs_positions is None:
            logger.warning("Missing visibility or position data; cannot calculate (u,v,w)")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("uv_coverage")[2:])

        n_tels = len(telescopes)
        n_times = len(times)
        if visibility.shape != (n_tels, n_times):
            logger.error(f"Visibility shape {visibility.shape} does not match expected ({n_tels}, {n_times})")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("uv_coverage")[2:])

        if gcrs_positions.shape != (n_tels, n_times, 3):
            logger.error(f"Position shape {gcrs_positions.shape} does not match expected ({n_tels}, {n_times}, 3)")
            return pd.DataFrame(columns=CalculatedDataStructure.get_columns("uv_coverage")[2:])

        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
        ra = source_coord.ra.rad
        dec = source_coord.dec.rad

        i, j = np.triu_indices(n_tels, k=1)
        pairs = [f"{telescopes[i].get_code()}-{telescopes[j].get_code()}" for i, j in zip(i, j)]
        n_pairs = len(pairs)

        baselines = gcrs_positions[i] - gcrs_positions[j]
        vis_mask = visibility[i] & visibility[j]
        pos_nan = np.any(np.isnan(gcrs_positions), axis=2)
        baseline_nan = pos_nan[i] | pos_nan[j]
        vis_mask = vis_mask & ~baseline_nan

        cos_ra, sin_ra = np.cos(ra), np.sin(ra)
        cos_dec, sin_dec = np.cos(dec), np.sin(dec)
        rotation_matrix = np.array([
            [-sin_ra, cos_ra, 0],
            [-cos_ra * sin_dec, -sin_ra * sin_dec, cos_dec],
            [cos_ra * cos_dec, sin_ra * cos_dec, sin_dec]
        ])

        baselines_flat = baselines.reshape(-1, 3)
        uvw_flat = baselines_flat @ rotation_matrix.T
        uvw = uvw_flat.reshape(n_pairs, n_times, 3)
        uvw[~vis_mask] = np.nan

        baselines_list = []
        u_values = []
        v_values = []
        w_values = []

        for pair_idx, pair in enumerate(pairs):
            uvw_pair = uvw[pair_idx]
            valid_count = np.sum(~np.any(np.isnan(uvw_pair), axis=1))
            logger.debug(f"Computed {valid_count} valid UVW points for baseline '{pair}' (total {n_times} points)")
            baselines_list.extend([pair] * n_times)
            u_values.extend(uvw_pair[:, 0])
            v_values.extend(uvw_pair[:, 1])
            w_values.extend(uvw_pair[:, 2])

        result_df = pd.DataFrame({
            "baseline": baselines_list,
            "u": u_values,
            "v": v_values,
            "w": w_values
        })

        if result_df.empty:
            logger.warning(f"No valid UVW points computed for any baseline")
            result_df = pd.DataFrame(columns=CalculatedDataStructure.get_columns("uv_coverage")[2:])

        return result_df

    @time_execution
    def _calculate_sun_angles(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate angular separation between source and Sun for all active scans in geometric coordinates.

        Args:
            obj: The object to calculate sun angles for.
            attributes: Parameters including "time_step", "store_key", "position_store_key", "visibility_store_key", "recalculate".

        Returns:
            Dict[str, Any]: Sun angles per source, scan, and telescope, formatted as:
                {source_name: {scan_name: {telescope_code: np.array([angle1, angle2, ...])}}.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "sun_angles")
            position_store_key = attributes.get("position_store_key", "telescope_positions")
            visibility_store_key = attributes.get("visibility_store_key", "source_visibility")
            recalculate = attributes.get("recalculate", False)

            def calculate_sun_angles(obs: Observation, attrs: Dict[str, Any]) -> Dict[str, Any]:
                scans, _, _ = self._get_active_components(obs)
                if not scans:
                    return {}

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": recalculate}
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": recalculate}
                time_data = self._calculate_time_arrays(obs, time_attrs)
                position_data = self._calculate_telescope_positions(obs, position_attrs)
                visibility_data = self._calculate_source_visibility(obs, visibility_attrs)

                if not (time_data and position_data and visibility_data):
                    logger.error(f"Missing required data for '{obs.get_observation_code()}'")
                    return {}

                results = {}
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(
                            self._process_sun_angles,
                            scan,
                            obs,
                            time_step,
                            time_data,
                            position_data,
                            visibility_data
                        ): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        source_name = scan_result.get("source")
                        if source_name and scan_result.get("angles"):
                            results.setdefault(source_name, {})[scan_name] = scan_result["angles"]
                return results

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()),
                "position_store_key": position_store_key,
                "visibility_store_key": visibility_store_key
            }
            return self._process_object(obj, attributes, calculate_sun_angles, store_key, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate sun angles for '{obj.get_observation_code()}': {str(e)}")
            return {}

    def _process_sun_angles(self, scan: Scan, observation: Observation, time_step: Optional[float], 
                       time_data: Dict[str, Any], position_data: Dict[str, Any], 
                       visibility_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Sun angles for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds).
            time_data (Dict[str, Any]): Precomputed time arrays from _calculate_time_arrays.
            position_data (Dict[str, Any]): Precomputed telescope positions.
            visibility_data (Dict[str, Any]): Precomputed visibility data.

        Returns:
            Dict[str, Any]: Sun angles for the scan, formatted as:
                {
                    "source": source_name,
                    "angles": {telescope_code: np.array([angle1, angle2, ...])}  # angles in degrees
                }

        Notes:
            - Handles NaN positions by assigning NaN angles, preserving array dimensions.
            - Uses vectorized computations for efficiency.
            - Logs warning if significant portion of positions are NaN or if vector normalization fails.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return {"source": None, "angles": {}}

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]

        if not active_telescopes:
            logger.warning(f"No active telescopes for scan '{scan_name}' in observation '{observation.get_observation_code()}'")
            return {"source": source_name, "angles": {}}

        scan_times = time_data.get(source_name, {}).get(scan_name, None)
        if scan_times is None or not isinstance(scan_times, Time) or scan_times.size == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return {"source": source_name, "angles": {}}

        scan_visibility = visibility_data.get(source_name, {}).get(scan_name, {})
        scan_positions = position_data.get(scan_name, {})
        if not (scan_visibility and scan_positions):
            logger.warning(f"No visibility or position data for scan '{scan_name}' in observation '{observation.get_observation_code()}'")
            return {"source": source_name, "angles": {}}

        tel_codes = [tel.get_code() for tel in active_telescopes]
        positions = np.array([
            scan_positions.get(code, np.full((len(scan_times), 3), np.nan))
            for code in tel_codes
        ])
        visibility = np.array([
            scan_visibility.get(code, [False] * len(scan_times))
            for code in tel_codes
        ], dtype=bool)

        logger.debug(f"Scan '{scan_name}': scan_times.shape={len(scan_times)}, positions.shape={positions.shape}, visibility.shape={visibility.shape}")
        if positions.shape[1] != len(scan_times):
            logger.error(f"Mismatch in position data length for scan '{scan_name}': {positions.shape[1]} positions vs {len(scan_times)} times")
            return {"source": source_name, "angles": {}}
        if visibility.shape[1] != len(scan_times):
            logger.error(f"Mismatch in visibility data length for scan '{scan_name}': {visibility.shape[1]} visibility points vs {len(scan_times)} times")
            return {"source": source_name, "angles": {}}

        nan_positions = np.any(np.isnan(positions), axis=2)
        nan_ratio = np.mean(nan_positions, axis=1)
        for i, tel_code in enumerate(tel_codes):
            if nan_ratio[i] > 0.5:
                logger.warning(f"High NaN ratio ({nan_ratio[i]:.2%}) in positions for telescope '{tel_code}' in scan '{scan_name}'")

        
        sun_coord = get_sun(scan_times)
        sun_vec = np.array([
            sun_coord.cartesian.x.value,
            sun_coord.cartesian.y.value,
            sun_coord.cartesian.z.value
        ]).T  

        angles = {}
        ground_tels = [tel for tel in active_telescopes if not isinstance(tel, SpaceTelescope)]
        space_tels = [tel for tel in active_telescopes if isinstance(tel, SpaceTelescope)]

        if ground_tels:
            ground_codes = [tel.get_code() for tel in ground_tels]
            ground_indices = [tel_codes.index(code) for code in ground_codes]
            ground_positions = positions[ground_indices]  
            ground_nan = nan_positions[ground_indices]  
            ground_visibility = visibility[ground_indices]

            gcrs_coords = CartesianRepresentation(
                x=ground_positions[:, :, 0] * u.m,
                y=ground_positions[:, :, 1] * u.m,
                z=ground_positions[:, :, 2] * u.m
            )
            itrs = GCRS(gcrs_coords, obstime=scan_times).transform_to(ITRS(obstime=scan_times))
            locations = itrs.earth_location

            source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
            sun_altaz = sun_coord.transform_to(AltAz(obstime=scan_times, location=locations))
            source_altaz = source_coord.transform_to(AltAz(obstime=scan_times, location=locations))
            sun_el = sun_altaz.alt.deg  
            sun_az = sun_altaz.az.deg   
            source_el = source_altaz.alt.deg  
            source_az = source_altaz.az.deg

            for i, tel in enumerate(ground_tels):
                tel_code = tel.get_code()
                is_visible = ground_visibility[i] & ~ground_nan[i]  
                angles[tel_code] = np.full(len(scan_times), np.nan, dtype=float)
                if np.any(is_visible):
                    cos_sep = np.sin(np.radians(source_el[i])) * np.sin(np.radians(sun_el[i])) + \
                            np.cos(np.radians(source_el[i])) * np.cos(np.radians(sun_el[i])) * \
                            np.cos(np.radians(source_az[i] - sun_az[i]))
                    cos_sep = np.clip(cos_sep, -1.0, 1.0)
                    sep = np.degrees(np.arccos(cos_sep))
                    angles[tel_code][is_visible] = sep[is_visible]
                    logger.debug(f"Computed {np.sum(is_visible)} sun angles for ground telescope '{tel_code}' in scan '{scan_name}'")

        if space_tels:
            space_codes = [tel.get_code() for tel in space_tels]
            space_indices = [tel_codes.index(code) for code in space_codes]
            space_positions = positions[space_indices]  
            space_nan = nan_positions[space_indices]  
            space_visibility = visibility[space_indices] 

            source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
            source_vec = np.array([
                source_coord.cartesian.x.value,
                source_coord.cartesian.y.value,
                source_coord.cartesian.z.value
            ])  

            source_norm = np.linalg.norm(source_vec)
            if source_norm == 0 or np.isnan(source_norm):
                logger.error(f"Invalid source vector for '{source_name}' in scan '{scan_name}': norm={source_norm}")
                return {"source": source_name, "angles": {}}

            source_unit = source_vec / source_norm

            for i, tel in enumerate(space_tels):
                tel_code = tel.get_code()
                tel_pos = space_positions[i]
                is_visible = space_visibility[i] & ~space_nan[i]
                angles[tel_code] = np.full(len(scan_times), np.nan, dtype=float)

                if not np.any(is_visible):
                    logger.debug(f"No valid positions or visibility for space telescope '{tel_code}' in scan '{scan_name}'")
                    continue

                valid_tel_pos = tel_pos[is_visible]  
                valid_sun_vec = sun_vec[is_visible]  
                logger.debug(f"Space telescope '{tel_code}' in scan '{scan_name}': "
                            f"valid_times={np.sum(is_visible)}, "
                            f"valid_tel_pos.shape={valid_tel_pos.shape}, "
                            f"valid_sun_vec.shape={valid_sun_vec.shape}")

                tel_norm = np.linalg.norm(valid_tel_pos, axis=1)  
                sun_norm = np.linalg.norm(valid_sun_vec, axis=1)  
                valid = (tel_norm > 0) & (sun_norm > 0) 

                if not np.any(valid):
                    logger.warning(f"No valid vectors after normalization for space telescope '{tel_code}' in scan '{scan_name}'")
                    continue

                tel_unit = valid_tel_pos[valid] / tel_norm[valid][:, np.newaxis]
                sun_unit = valid_sun_vec[valid] / sun_norm[valid][:, np.newaxis]
                source_unit_expanded = np.repeat([source_unit], np.sum(valid), axis=0)

                cos_sep = np.sum(sun_unit * source_unit_expanded, axis=1)
                cos_sep = np.clip(cos_sep, -1.0, 1.0)
                sep = np.degrees(np.arccos(cos_sep))

                logger.debug(f"Space telescope '{tel_code}' in scan '{scan_name}': "
                            f"cos_sep_range=[{np.min(cos_sep):.3f}, {np.max(cos_sep):.3f}], "
                            f"sep_range=[{np.min(sep):.3f}, {np.max(sep):.3f}] degrees")

                angles[tel_code][is_visible] = np.where(valid, sep, np.nan)

        if not angles:
            logger.warning(f"No sun angles computed for scan '{scan_name}'")
        else:
            logger.debug(f"Computed sun angles for {len(angles)} telescopes in scan '{scan_name}'")
        return {"source": source_name, "angles": angles}

    @time_execution
    def _calculate_az_el(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate azimuth/elevation or hour angle/declination angles for active ground telescopes in all active scans.

        Args:
            obj: The object to calculate az/el or ha/dec angles for.
            attributes: Parameters including "time_step", "store_key", "position_store_key", "visibility_store_key", "recalculate".

        Returns:
            Dict[str, Any]: Angles data, formatted as:
                {source_name: {scan_name: {telescope_code: np.array([[az/ha, el/dec], ...])}}} for Observation,
                {obs_code: {source_name: {scan_name: {telescope_code: np.array([[az/ha, el/dec], ...])}}}} for ScheduleProject.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "az_el")
            position_store_key = attributes.get("position_store_key", "telescope_positions")
            visibility_store_key = attributes.get("visibility_store_key", "source_visibility")
            recalculate = attributes.get("recalculate", False)

            def calculate_az_el(obs: Observation, attrs: Dict[str, Any]) -> Dict[str, Any]:
                scans, telescopes, sources = self._get_active_components(obs, require_telescopes=True)
                if not scans:
                    return {}

                ground_telescopes = [tel for tel in telescopes if not isinstance(tel, SpaceTelescope)]
                if not ground_telescopes:
                    logger.debug(f"No ground telescopes in '{obs.get_observation_code()}'")
                    return {}

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": recalculate}
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": recalculate}
                time_data = self._calculate_time_arrays(obs, time_attrs)
                position_data = self._calculate_telescope_positions(obs, position_attrs)
                visibility_data = self._calculate_source_visibility(obs, visibility_attrs)

                if not (time_data and position_data and visibility_data):
                    logger.error(f"Missing required data (times, positions, or visibility) for '{obs.get_observation_code()}'")
                    return {}

                results = {}
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(
                            self._process_az_el, scan, obs, time_step, time_data, position_data, visibility_data
                        ): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        source_name = scan_result.get("source")
                        if source_name and scan_result.get("angles"):
                            results.setdefault(source_name, {})[scan_name] = scan_result["angles"]

                logger.info(f"Calculated az/el or ha/dec for {len(results)} sources in '{obs.get_observation_code()}'")
                return results

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()),
                "position_store_key": position_store_key,
                "visibility_store_key": visibility_store_key
            }
            return self._process_object(obj, attributes, calculate_az_el, store_key, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate az/el or ha/dec for '{obj.get_observation_code()}': {str(e)}")
            return {}

    def _process_az_el(self, scan: Scan, observation: Observation, time_step: Optional[float], time_data: Dict[str, Any], position_data: Dict[str, Any], visibility_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process az/el or ha/dec angles for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds). If None, uses mean time.
            time_data (Dict[str, Any]): Precomputed time arrays from _calculate_time_arrays.
            position_data (Dict[str, Any]): Precomputed telescope positions from _calculate_telescope_positions.
            visibility_data (Dict[str, Any]): Precomputed visibility data from _calculate_source_visibility.

        Returns:
            Dict[str, Any]: Angles data for the scan, formatted as:
                {
                    "source": source_name,
                    "angles": {telescope_code: np.array([[az/ha, el/dec], ...])}
                }

        Notes:
            - Computes az/el for AZIM mounts and ha/dec for EQUA mounts.
            - Applies visibility mask to set angles to NaN for non-visible times.
            - Excludes space telescopes as they use pitch/yaw.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return {"source": None, "angles": {}}

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive and not isinstance(t, SpaceTelescope)]
        if not active_telescopes:
            logger.warning(f"No active ground telescopes for scan '{scan_name}' in observation '{observation.get_observation_code()}'")
            return {"source": source_name, "angles": {}}

        scan_times = time_data.get(source_name, {}).get(scan_name, None)
        if scan_times is None or not isinstance(scan_times, Time) or scan_times.size == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return {"source": source_name, "angles": {}}

        scan_visibility = visibility_data.get(source_name, {}).get(scan_name, {})
        scan_positions = position_data.get(scan_name, {})
        if not (scan_visibility and scan_positions):
            logger.warning(f"No visibility or position data for scan '{scan_name}' in observation '{observation.get_observation_code()}'")
            return {"source": source_name, "angles": {}}

        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
        angles = {}

        tel_codes = [tel.get_code() for tel in active_telescopes]
        mount_types = [tel.get("mount_type").value for tel in active_telescopes]
        visibility = np.array([scan_visibility.get(code, [False] * len(scan_times)) for code in tel_codes], dtype=bool)  # shape: (n_tels, n_times)
        positions = np.array([scan_positions.get(code, np.full((len(scan_times), 3), np.nan)) for code in tel_codes])  # shape: (n_tels, n_times, 3)

        if positions.shape[1] != len(scan_times):
            logger.warning(f"Mismatched position data length for scan '{scan_name}': {positions.shape[1]} positions vs {len(scan_times)} times")
            return {"source": source_name, "angles": {}}

        azim_indices = [i for i, mt in enumerate(mount_types) if mt == "AZIM"]
        if azim_indices:
            azim_codes = [tel_codes[i] for i in azim_indices]
            azim_positions = positions[azim_indices]  
            azim_visibility = visibility[azim_indices]  

            gcrs_coords = CartesianRepresentation(
                x=azim_positions[:, :, 0] * u.m,
                y=azim_positions[:, :, 1] * u.m,
                z=azim_positions[:, :, 2] * u.m
            )
            gcrs = GCRS(gcrs_coords, obstime=scan_times)
            itrs = gcrs.transform_to(ITRS(obstime=scan_times))
            locations = itrs.earth_location
            altaz = source_coord.transform_to(AltAz(obstime=scan_times, location=locations))
            az = altaz.az.deg  
            el = altaz.alt.deg  

            az[~azim_visibility] = np.nan
            el[~azim_visibility] = np.nan

            for i, code in enumerate(azim_codes):
                angles[code] = np.stack([az[i], el[i]], axis=-1)  # shape: (n_times, 2)

        equa_indices = [i for i, mt in enumerate(mount_types) if mt == "EQUA"]
        if equa_indices:
            equa_codes = [tel_codes[i] for i in equa_indices]
            equa_positions = positions[equa_indices]  
            equa_visibility = visibility[equa_indices]  

            gcrs_coords = CartesianRepresentation(
                x=equa_positions[:, :, 0] * u.m,
                y=equa_positions[:, :, 1] * u.m,
                z=equa_positions[:, :, 2] * u.m
            )
            gcrs = GCRS(gcrs_coords, obstime=scan_times)
            itrs = gcrs.transform_to(ITRS(obstime=scan_times))
            locations = itrs.earth_location
            hadec = source_coord.transform_to(HADec(obstime=scan_times, location=locations))
            ha = hadec.ha.deg   
            dec = hadec.dec.deg

            ha[~equa_visibility] = np.nan
            dec[~equa_visibility] = np.nan

            for i, code in enumerate(equa_codes):
                angles[code] = np.stack([ha[i], dec[i]], axis=-1)

        for i, tel in enumerate(active_telescopes):
            if mount_types[i] not in ["AZIM", "EQUA"]:
                logger.warning(f"Unsupported mount type '{mount_types[i]}' for telescope '{tel.get_code()}' in scan '{scan_name}'")
                angles[tel.get_code()] = np.full((len(scan_times), 2), np.nan)

        valid_angle_count = sum(np.any(~np.isnan(angles[code]), axis=0)[0] for code in angles)
        if valid_angle_count == 0:
            logger.warning(f"No valid az/el or ha/dec angles computed for scan '{scan_name}'")
            return {"source": source_name, "angles": {}}

        logger.debug(f"Computed az/el or ha/dec for {valid_angle_count} telescopes in scan '{scan_name}'")
        return {"source": source_name, "angles": angles}

    def _compute_az_el_at_time(self, source_coord: SkyCoord, telescopes: List[Telescope], time: Time) -> Dict[str, Tuple[float, float]]:
        """Compute Az/El or HA/Dec for ground telescopes at a given time, depending on mount type.

        Args:
            source_coord (SkyCoord): Source coordinates.
            telescopes (List[Telescope]): List of ground telescopes.
            time (Time): Time of calculation.

        Returns:
            Dict[str, Tuple[float, float]]: Coordinates per telescope code (Az/El or HA/Dec).
        """
        az_el = {}
        for tel in telescopes:
            x, y, z = tel.get_coordinates()
            res = tel.get(["vx", "vy", "vz"])
            vx = res["vx"]
            vy = res["vy"]
            vz = res["vz"]
            dt = (time - Time("2000-01-01T12:00:00")).sec
            itrs_coords = CartesianRepresentation(x + vx * dt, y + vy * dt, z + vz * dt, unit=u.m)
            itrs = ITRS(itrs_coords, obstime=time)
            location = itrs.earth_location
            mount_type = tel.get("mount_type")
           
            if mount_type.value == "AZIM":
                altaz = source_coord.transform_to(AltAz(obstime=time, location=location))
                az, el = altaz.az.deg, altaz.alt.deg
                el_range = tel.get_elevation_range()
                az_range = tel.get_azimuth_range()
                if not (el_range[0] <= el <= el_range[1] and az_range[0] <= az <= az_range[1]):
                    az_el[tel.get_code()] = (None, None)
                else:
                    az_el[tel.get_code()] = (az, el)
            elif mount_type.value == "EQUA":
                hadec = source_coord.transform_to(HADec(obstime=time, location=location))
                ha, dec = hadec.ha.deg, hadec.dec.deg
                ha_range = tel.get_azimuth_range()
                dec_range = tel.get_elevation_range()
                if not (ha_range[0] <= ha <= ha_range[1] and dec_range[0] <= dec <= dec_range[1]):
                    az_el[tel.get_code()] = (None, None)
                else:
                    az_el[tel.get_code()] = (ha, dec)
            else:
                logger.warning(f"Unsupported mount type {mount_type} for telescope '{tel.get_code()}'")
                az_el[tel.get_code()] = (0.0, 0.0)
        return az_el

    @time_execution
    def _calculate_time_on_source(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate time-on-source blocks for all active scans in the observation or project.

        Args:
            obj: The object to calculate time on source for.
            attributes: Parameters including "time_step", "store_key", "visibility_store_key", "recalculate".

        Returns:
            Dict[str, Any]: Time-on-source blocks per source, scan, and telescope, formatted as:
                {source_name: {scan_name: {telescope_code: np.array([[start_mjd, end_mjd, duration], ...])}}.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "time_on_source")
            visibility_store_key = attributes.get("visibility_store_key", "source_visibility")
            recalculate = attributes.get("recalculate", False)

            def calculate_time_on_source(obs: Observation, attrs: Dict[str, Any]) -> Dict[str, Any]:
                scans, _, _ = self._get_active_components(obs)
                if not scans:
                    return {}

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": recalculate}
                time_data = self._calculate_time_arrays(obs, time_attrs)
                visibility_data = self._calculate_source_visibility(obs, visibility_attrs)

                if not (time_data and visibility_data):
                    logger.error(f"Missing time or visibility data for '{obs.get_observation_code()}'")
                    return {}

                results = {}
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_time_on_source, scan, obs, time_step, time_data, visibility_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        source_name = scan_result.get("source")
                        if source_name and scan_result.get("time_blocks"):
                            results.setdefault(source_name, {})[scan_name] = scan_result["time_blocks"]
                return results

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()),
                "visibility_store_key": visibility_store_key
            }
            return self._process_object(obj, attributes, calculate_time_on_source, store_key, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate time on source for '{obj.get_observation_code()}': {str(e)}")
            return {}
        
    def _process_time_on_source(self, scan: Scan, observation: Observation, time_step: Optional[float], time_data: Dict[str, Any], visibility_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process time-on-source blocks for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds).
            time_data (Dict[str, Any]): Precomputed time arrays from _calculate_time_arrays.
            visibility_data (Dict[str, Any]): Precomputed visibility data.

        Returns:
            Dict[str, Any]: Time-on-source blocks, formatted as:
                {
                    "source": source_name,
                    "time_blocks": {telescope_code: np.array([[start_mjd, end_mjd, duration], ...])}
                }
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return {"source": None, "time_blocks": {}}

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        if not active_telescopes:
            logger.warning(f"No active telescopes for scan '{scan_name}' in observation '{observation.get_observation_code()}'")
            return {"source": source_name, "time_blocks": {}}

        scan_times = time_data.get(source_name, {}).get(scan_name, None)
        if scan_times is None or not isinstance(scan_times, Time) or scan_times.size == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return {"source": source_name, "time_blocks": {}}

        scan_visibility = visibility_data.get(source_name, {}).get(scan_name, {})
        if not scan_visibility:
            logger.warning(f"No visibility data for scan '{scan_name}' in source '{source_name}'")
            return {"source": source_name, "time_blocks": {}}

        tel_codes = [tel.get_code() for tel in active_telescopes]
        visibility = np.array([scan_visibility.get(code, [False] * len(scan_times)) for code in tel_codes], dtype=bool)  # shape: (n_tels, n_times)

        time_blocks = {}
        time_mjd = scan_times.mjd
        if time_step is None:
            for i, tel_code in enumerate(tel_codes):
                if visibility[i, 0]:
                    duration = scan.get_duration()
                    time_blocks[tel_code] = np.array([[time_mjd[0], time_mjd[0], duration]])
                else:
                    time_blocks[tel_code] = np.array([], dtype=float).reshape(0, 3)
        else:
            time_step_sec = time_step if time_step is not None else scan.get_duration()
            for i, tel_code in enumerate(tel_codes):
                vis = visibility[i]
                diff = np.diff(vis.astype(int))
                start_indices = np.where(diff == 1)[0] + 1
                end_indices = np.where(diff == -1)[0]
                if vis[0]:
                    start_indices = np.concatenate(([0], start_indices))
                if vis[-1]:
                    end_indices = np.concatenate((end_indices, [len(vis) - 1]))
                if len(start_indices) > len(end_indices):
                    end_indices = np.concatenate((end_indices, [len(vis) - 1]))
                elif len(end_indices) > len(start_indices):
                    start_indices = np.concatenate(([0], start_indices))

                if len(start_indices) == 0 or len(end_indices) == 0:
                    time_blocks[tel_code] = np.array([], dtype=float).reshape(0, 3)
                    continue

                blocks = np.zeros((len(start_indices), 3), dtype=float)
                blocks[:, 0] = time_mjd[start_indices]
                blocks[:, 1] = time_mjd[end_indices]
                blocks[:, 2] = (blocks[:, 1] - blocks[:, 0]) * 86400.0
                time_blocks[tel_code] = blocks

                logger.debug(f"Computed {len(blocks)} time-on-source blocks for telescope '{tel_code}' in scan '{scan_name}'")

        return {"source": source_name, "time_blocks": time_blocks}

    @time_execution
    def _calculate_beam_pattern(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate beam pattern for active telescopes in the observation or project, independent of frequency.

        Args:
            obj: The object to calculate beam pattern for.
            attributes: Parameters including "store_key", "recalculate".

        Returns:
            Dict[str, Any]: Beam pattern data formatted as:
                For Observation: {telescope_code: {"theta": List[float], "pattern": List[float]}}
                For ScheduleProject: {obs_code: {telescope_code: {"theta": List[float], "pattern": List[float]}}}
        """
        try:
            store_key = attributes.get("store_key", "beam_pattern")
            recalculate = attributes.get("recalculate", False)

            def calculate_beam_pattern(obs: Observation, attrs: Dict[str, Any]) -> Dict[str, Any]:
                _, telescopes, _ = self._get_active_components(obs, require_scans=False, require_telescopes=True)
                if not telescopes:
                    return {}

                obs_type = obs.get_observation_type()
                if obs_type not in ["SINGLE_DISH", "VLBI"]:
                    logger.warning(f"Beam pattern calculation is only for SINGLE_DISH or VLBI, got {obs_type}")
                    return {}

                theta = np.linspace(-np.pi / 2, np.pi / 2, 5000)  # radians
                results = {}
                diameters = []
                valid_telescopes = []
                for tel in telescopes:
                    diameter = tel.get("diameter")
                    if diameter is None or diameter <= 0:
                        logger.warning(f"Invalid diameter for telescope '{tel.get_code()}' in '{obs.get_observation_code()}'; skipping")
                        continue
                    diameters.append(diameter)
                    valid_telescopes.append(tel)

                if not valid_telescopes:
                    logger.warning(f"No telescopes with valid diameters in '{obs.get_observation_code()}'")
                    return {}

                diameters = np.array(diameters)
                x = diameters[:, None] * np.sin(theta)
                pattern = (2 * j1(x) / x) ** 2
                pattern = np.where(np.isnan(pattern), 1.0, pattern)
                pattern = pattern / np.max(pattern, axis=1, keepdims=True)

                for tel, pat in zip(valid_telescopes, pattern):
                    results[tel.get_code()] = {
                        "theta": theta.tolist(),
                        "pattern": pat.tolist()
                    }

                logger.info(f"Calculated beam pattern for {len(valid_telescopes)} telescopes in '{obs.get_observation_code()}'")
                return results

            metadata = {
                "telescope_count": len(obj.get_telescopes().get_active_items()),
                "scale_instruction": "Multiply pattern by wavelength during visualization"
            }
            return self._process_object(obj, attributes, calculate_beam_pattern, store_key, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate beam pattern for '{obj.get_observation_code()}': {str(e)}")
            return {}

    @time_execution
    def _calculate_baseline_projections(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate baseline projections for VLBI observations in geometric coordinates (meters).

        Args:
            obj: The object to calculate projections for.
            attributes: Parameters including "time_step", "store_key", "recalculate".

        Returns:
            Dict[str, Any]: Baseline projection data per source and scan, formatted as:
                {source_name: {scan_name: {baseline: np.array([proj1, ..., projn])}} for Observation,
                {obs_code: {source_name: {scan_name: {baseline: np.array([proj1, ..., projn])}}} for ScheduleProject.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "baseline_projections")
            recalculate = attributes.get("recalculate", False)
            if "freq_name" in attributes:
                logger.info(f"Ignoring 'freq_name' attribute for baseline projections in geometric coordinates")

            def calculate_baseline_projections(obs: Observation, attrs: Dict[str, Any]) -> Dict[str, Any]:
                if obs.get_observation_type() != "VLBI":
                    logger.warning(f"Baseline projections are only for VLBI, got {obs.get_observation_type()}")
                    return {}

                scans, telescopes, _ = self._get_active_components(obs, require_telescopes=True, min_telescopes=2)
                if not scans:
                    return {}

                uv_attrs = {"time_step": time_step, "store_key": "uv_coverage", "recalculate": recalculate}
                uv_data = self._calculate_uv_coverage(obs, uv_attrs)
                if not uv_data:
                    logger.error(f"No UV coverage data for '{obs.get_observation_code()}'")
                    return {}

                results = {}
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_baseline_projections, scan, obs, time_step, uv_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        source_name = scan_result.get("source")
                        if source_name and scan_result.get("projections"):
                            results.setdefault(source_name, {})[scan_name] = scan_result["projections"]
                return results

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items())}
            return self._process_object(obj, attributes, calculate_baseline_projections, store_key, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate baseline projections for '{obj.get_observation_code()}': {str(e)}")
            return {}
    
    def _process_baseline_projections(self, scan: Scan, observation: Observation, time_step: Optional[float], uv_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process baseline projections for a single scan in geometric coordinates (meters).

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds).
            uv_data (Dict[str, Any]): Precomputed UV data from _calculate_uv_coverage.

        Returns:
            Dict[str, Any]: Baseline projections in meters, formatted as:
                {
                    "source": source_name,
                    "projections": {
                        baseline: np.array([proj1, ..., projn])  # projections in meters
                    }
                }

        Notes:
            - Computes BL = sqrt(u² + v²) from UV data in meters.
            - Outputs NaN for times where UV data is NaN or source is not visible.
            - Ensures output array size matches input times for index correspondence.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return {"source": None, "projections": {}}

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]

        if len(active_telescopes) < 2:
            logger.warning(f"Insufficient telescopes ({len(active_telescopes)}) for baseline projections in scan '{scan_name}'")
            return {"source": source_name, "projections": {}}

        scan_uv_data = uv_data.get(source_name, {}).get(scan_name, {})
        if not scan_uv_data:
            logger.warning(f"No UV data for scan '{scan_name}' in source '{source_name}'")
            return {"source": source_name, "projections": {}}

        time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
        time_data = self._calculate_time_arrays(observation, time_attrs)
        scan_times = time_data.get(source_name, {}).get(scan_name, None)
        if scan_times is None or not isinstance(scan_times, Time) or scan_times.size == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return {"source": source_name, "projections": {}}

        projections = self._compute_projections_from_uv(scan_uv_data, active_telescopes, time_step, len(scan_times))
        if not projections:
            logger.warning(f"No valid baseline projections computed for scan '{scan_name}'")
        else:
            logger.debug(f"Computed {sum(len(proj) for proj in projections.values())} baseline projections for scan '{scan_name}' across {len(projections)} baselines")
        
        return {"source": source_name, "projections": projections}
        
    def _compute_projections_from_uv(self, uv_data: Dict[str, np.ndarray], telescopes: List[Telescope | SpaceTelescope], time_step: Optional[float], n_times: int) -> Dict[str, np.ndarray]:
        """Compute baseline projections BL = sqrt(u² + v²) from UV data in meters.

        Args:
            uv_data (Dict[str, np.ndarray]): UV data as {baseline: np.array([[u,v,w], ...])}.
            telescopes (List[Telescope | SpaceTelescope]): List of active telescopes.
            time_step (Optional[float]): Sampling interval (seconds).
            n_times (int): Expected number of time points to match.

        Returns:
            Dict[str, np.ndarray]: Baseline projections in meters, formatted as {baseline: np.array([proj1, ..., projn])}.
        """
        projections = {}
        pairs = [f"{telescopes[i].get_code()}-{telescopes[j].get_code()}" for i, j in zip(*np.triu_indices(len(telescopes), k=1))]
        
        for baseline in pairs:
            uvw = uv_data.get(baseline, np.full((n_times, 3), np.nan, dtype=float))
            if uvw.shape[0] != n_times:
                logger.warning(f"UV data for baseline '{baseline}' has length {uvw.shape[0]}, expected {n_times}; adjusting with NaN")
                temp = np.full((n_times, 3), np.nan, dtype=float)
                temp[:min(uvw.shape[0], n_times)] = uvw[:n_times]
                uvw = temp
            u, v = uvw[:, 0], uvw[:, 1]
            bl = np.sqrt(u**2 + v**2)
            projections[baseline] = bl
            valid_count = np.sum(~np.isnan(bl))
            logger.debug(f"Computed {valid_count} valid projections for baseline '{baseline}'")

        if not projections:
            logger.warning(f"No valid baseline projections computed for provided UV data")
        return projections

    @time_execution
    def _calculate_mollweide_tracks(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Mollweide projection tracks for telescopes in active scans.

        Args:
            obj (Observation | ScheduleProject): The object to calculate tracks for.
            attributes (Dict[str, Any]): Parameters including "time_step", "store_key", "recalculate".

        Returns:
            Dict[str, Any]: Mollweide tracks, formatted as:
                For Observation: {scan_name: {telescope_code: np.array([[lon1, lat1], ...])}} in meters
                For ScheduleProject: {obs_code: {scan_name: {telescope_code: np.array([[lon1, lat1], ...])}}}

        Notes:
            - Uses precomputed times and telescope positions.
            - Stores metadata (time_step, scan_count, sources) in calculated_data.
            - Handles both Observation and ScheduleProject with parallel processing for projects.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "mollweide_tracks")
            recalculate = attributes.get("recalculate", False)

            def calculate_mollweide(obs: Observation, attrs: Dict[str, Any]) -> Dict[str, Any]:
                scans, _, _ = self._get_active_components(obs, require_scans=True)
                if not scans:
                    logger.warning(f"No active scans in observation '{obs.get_observation_code()}'")
                    return {}

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": recalculate}
                time_data = self._calculate_time_arrays(obs, time_attrs)
                position_data = self._calculate_telescope_positions(obs, position_attrs)

                if not (time_data and position_data):
                    logger.error(f"Missing required data (times or positions) for '{obs.get_observation_code()}'")
                    return {}

                results = {}
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_mollweide_tracks, scan, obs, time_step, time_data, position_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result.get("tracks"):
                            results[scan_name] = scan_result["tracks"]
                            logger.debug(f"Computed tracks for scan '{scan_name}' in '{obs.get_observation_code()}'")
                        else:
                            logger.warning(f"No tracks for scan '{scan_name}' in '{obs.get_observation_code()}'")

                if not results:
                    logger.warning(f"No Mollweide tracks computed for observation '{obs.get_observation_code()}'")
                return results

            sources_metadata = {}
            for source in obj.get_sources().get_active_items():
                ra = source.ra_degrees  
                dec = source.dec_degrees  
                lon = ra - 360.0 if ra > 180.0 else ra
                lat = np.clip(dec, -90.0, 90.0)
                sources_metadata[source.name] = np.array([lon, lat])

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.get_items()),
                "sources": sources_metadata
            }

            result = self._process_object(obj, attributes, calculate_mollweide, store_key, metadata)
            if not result:
                logger.warning(f"No Mollweide tracks computed for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}'")
            return result

        except Exception as e:
            logger.error(f"Failed to calculate Mollweide tracks for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {str(e)}")
            return {}

    def _process_mollweide_tracks(self, scan: Scan, observation: Observation, time_step: Optional[float], time_data: Dict[str, Any], position_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Mollweide tracks for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds).
            time_data (Dict[str, Any]): Precomputed time arrays from _calculate_time_arrays.
            position_data (Dict[str, Any]): Precomputed telescope positions.

        Returns:
            Dict[str, Any]: Mollweide tracks for the scan, formatted as:
                {
                    "tracks": {
                        telescope_code: np.array([[lon1, lat1], [lon2, lat2], ...])  # in degrees
                    }
                }

        Notes:
            - Outputs NaN for coordinates where telescope positions are NaN.
            - Ensures output array size matches input times for index correspondence.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return {"tracks": {}}

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]

        if not active_telescopes:
            logger.warning(f"No active telescopes for scan '{scan_name}' in observation '{observation.get_observation_code()}'")
            return {"tracks": {}}

        scan_times = time_data.get(source_name, {}).get(scan_name, None)
        if scan_times is None or not isinstance(scan_times, Time) or scan_times.size == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return {"tracks": {}}

        scan_positions = position_data.get(scan_name, {})
        if not scan_positions:
            logger.warning(f"No position data for scan '{scan_name}' in observation '{observation.get_observation_code()}'")
            return {"tracks": {}}

        tel_codes = [tel.get_code() for tel in active_telescopes]
        positions = np.array([
            scan_positions.get(code, np.full((len(scan_times), 3), np.nan))
            for code in tel_codes
        ])  # shape: (n_tels, n_times, 3)

        tracks = {}
        r = np.sqrt(np.sum(positions**2, axis=2))
        valid_mask = r > 0  # Avoid division by zero
        ra_rad = np.full_like(r, np.nan)
        dec_rad = np.full_like(r, np.nan)
        ra_rad[valid_mask] = np.arctan2(positions[valid_mask, 1], positions[valid_mask, 0])
        dec_rad[valid_mask] = np.arcsin(positions[valid_mask, 2] / r[valid_mask])
        ra = np.degrees(ra_rad)  
        dec = np.degrees(dec_rad)  
        lon = np.where(ra > 180.0, ra - 360.0, ra)  
        lat = np.clip(dec, -90.0, 90.0)

        for i, tel_code in enumerate(tel_codes):
            tracks[tel_code] = np.column_stack((lon[i], lat[i]))
            valid_points = np.sum(~np.isnan(lon[i]) & ~np.isnan(lat[i]))
            if valid_points == 0:
                logger.warning(f"No valid Mollweide coordinates for telescope '{tel_code}' in scan '{scan_name}'")
            else:
                logger.debug(f"Computed {valid_points} valid Mollweide coordinates for telescope '{tel_code}' in scan '{scan_name}'")

        if not tracks:
            logger.warning(f"No valid Mollweide tracks computed for scan '{scan_name}'")
        return {"tracks": tracks}