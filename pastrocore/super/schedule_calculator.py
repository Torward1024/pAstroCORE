from common.super.super import Super
from common.utils.logging_setup import logger

from pastrocore.base.sources import Source
from pastrocore.base.telescopes import Telescope, SpaceTelescope
from pastrocore.base.scans import Scan
from pastrocore.base.observation import Observation
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
            logger.warning(f"No active scans in observation '{obj_code}'")
            return [], [], []
        if require_telescopes and len(telescopes) < min_telescopes:
            logger.warning(f"Insufficient active telescopes ({len(telescopes)} < {min_telescopes}) in '{obj_code}'")
            return [], [], []
        if not sources:
            logger.warning(f"No active sources in observation '{obj_code}'")
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
        if existing_data and not recalculate and existing_data["metadata"].get("time_step") == time_step:
            df = existing_data.get("data")
            if df is not None and not df.is_empty():
                logger.debug(f"Retrieved cached data for '{store_key}' in '{obj_name}'")
                return df
            logger.warning(f"Cached data for '{store_key}' in '{obj_name}' is empty; recalculating")

        logger.info(f"Calculating '{store_key}' for '{obj_name}' (recalculate={recalculate})")
        result_df = calc_func(obj, attributes)
        if result_df.is_empty():
            logger.warning(f"Calculation for '{store_key}' in '{obj_name}' returned empty result")
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
            observations = obj.get_items()
            if not observations:
                logger.warning(f"No observations in project '{obj.name}'")
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
                logger.info(f"Processed {len(observations)} observations for '{obj_name}', combined into DF with {combined_df.height} rows")
                return combined_df
            else:
                logger.warning(f"No data from observations in project '{obj_name}'")
                return pl.DataFrame()
        
        result_df = self._get_cached_or_calculate(obj, store_key, calc_func, attributes, metadata)
        if result_df.is_empty():
            logger.warning(f"No data computed for '{obj_name}' with store_key '{store_key}'")
        return result_df
    
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
                logger.error(f"Invalid time_step: {time_step}. Must be positive.")
                return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("times"))
            if time_threshold <= 0:
                logger.error(f"Invalid time_threshold: {time_threshold}. Must be positive.")
                return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("times"))

            def calculate_times(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, _, sources = self._get_active_components(obs)
                if not scans:
                    logger.warning(f"No active scans in observation '{obs.get_observation_code()}'")
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
                        logger.debug(f"Skipping scan '{scan.name}' in '{obs.get_observation_code()}': no active source")
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
                        logger.warning(f"Empty time array for scan '{scan.name}' in '{obs.get_observation_code()}'")
                        continue
                    
                    source_names.append(np.full_like(mjd_values, source_name, dtype=object))
                    scan_names.append(np.full_like(mjd_values, scan.name, dtype=object))
                    times_array.append(mjd_values)
                    start_times.append(start_mjd_rounded)
                    end_times.append(start_mjd_rounded + duration_rounded / 86400.0)
                    processed_scans += 1
                
                if processed_scans == 0:
                    logger.warning(f"No valid scans processed in '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("times"))
                
                source_names = np.concatenate(source_names) if source_names else np.array([])
                scan_names = np.concatenate(scan_names) if scan_names else np.array([])
                times_array = np.concatenate(times_array) if times_array else np.array([])
                
                df = pl.DataFrame({
                    "source_name": source_names,
                    "scan_name": scan_names,
                    "time": times_array
                }).with_columns([
                    pl.col("source_name").cast(pl.String),
                    pl.col("scan_name").cast(pl.String),
                    pl.col("time").cast(pl.Float64)
                ])
                
                logger.info(f"Calculated time arrays for {processed_scans} scans across {df['source_name'].unique().len()} sources in '{obs.get_observation_code()}', DF rows: {df.height}")
                return df

            metadata = {
                "time_step": time_step,
                "time_threshold": time_threshold,
                "start_time": np.nan,
                "end_time": np.nan,
                "scan_count": 0
            }
            
            df = self._process_object(obj, attributes, calculate_times, store_key, metadata)
            
            if not df.is_empty():
                metadata["start_time"] = df["time"].min()
                metadata["end_time"] = df["time"].max()
                metadata["scan_count"] = df["scan_name"].unique().len()
                if attributes.get("recalculate", False) or not obj.get_calculated_data_by_key(store_key):
                    obj.set_calculated_data_by_key(store_key, df, metadata)
            
            return df
        except Exception as e:
            logger.error(f"Failed to calculate time arrays for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {str(e)}")
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
                logger.error(f"Invalid time_step: {time_step}. Must be positive.")
                return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("interpolated_orbits"))

            def calculate_orbits(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, telescopes, _ = self._get_active_components(obs, require_scans=True, require_telescopes=True)
                if not scans:
                    logger.warning(f"No active scans in observation '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("interpolated_orbits"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                if times_df.is_empty():
                    logger.warning(f"No time arrays available for observation '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("interpolated_orbits"))

                active_space_telescopes = [
                    tel for tel in telescopes
                    if isinstance(tel, SpaceTelescope) and not tel.get("use_kep")
                ]
                if not active_space_telescopes:
                    logger.debug(f"No active SpaceTelescopes with use_kep=False in '{obs.get_observation_code()}'")
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
                            logger.debug(f"Skipping scan '{scan_name}' due to inactive or missing source")
                            continue

                        scan_times_df = times_df.filter(pl.col("scan_name") == scan_name)
                        if scan_times_df.is_empty():
                            logger.debug(f"No valid times for scan '{scan_name}' in source '{source.name}'")
                            continue

                        scan_times_mjd = scan_times_df["time"].to_numpy()
                        scan_telescopes = scan.get_telescopes(obs).get_active_items()
                        scan_space_telescopes = [
                            tel for tel in scan_telescopes
                            if isinstance(tel, SpaceTelescope) and not tel.get("use_kep")
                        ]
                        if not scan_space_telescopes:
                            logger.debug(f"No active SpaceTelescopes in scan '{scan_name}'")
                            continue

                        start_time = scan.get_start().mjd
                        end_time = start_time + scan.get_duration() / 86400.0

                        for tel in scan_space_telescopes:
                            tel_code = tel.get_code()
                            orbit_file = tel.get_orbit()
                            if not orbit_file:
                                logger.warning(f"No orbit file for telescope '{tel_code}' in scan '{scan_name}'; excluding")
                                excluded_telescopes.append(tel_code)
                                continue

                            try:
                                positions = self._interpolate_orbit(tel, scan_times_mjd, start_time, end_time)
                                if positions.shape[0] != len(scan_times_mjd):
                                    logger.warning(f"Position data length mismatch for '{tel_code}' in scan '{scan_name}': got {positions.shape[0]}, expected {len(scan_times_mjd)}")
                                    positions = np.full((len(scan_times_mjd), 3), np.nan)
                                    positions[:min(positions.shape[0], len(scan_times_mjd))] = positions[:len(scan_times_mjd)]

                                if np.any(np.isnan(positions)):
                                    logger.warning(f"Orbit data for '{tel_code}' in scan '{scan_name}' contains NaN values")

                                n_times = len(scan_times_mjd)
                                times_list.append(scan_times_mjd)
                                scan_names.append(np.full(n_times, scan_name, dtype=object))
                                telescope_codes.append(np.full(n_times, tel_code, dtype=object))
                                x_list.append(positions[:, 0])
                                y_list.append(positions[:, 1])
                                z_list.append(positions[:, 2])
                            except ValueError as e:
                                logger.warning(f"Excluding telescope '{tel_code}' in scan '{scan_name}' due to interpolation error: {str(e)}")
                                excluded_telescopes.append(tel_code)

                if excluded_telescopes:
                    logger.info(f"Excluded {len(set(excluded_telescopes))} telescopes: {', '.join(set(excluded_telescopes))}")

                if not times_list:
                    logger.warning(f"No valid orbit data computed for '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("interpolated_orbits"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "x": np.concatenate(x_list),
                    "y": np.concatenate(y_list),
                    "z": np.concatenate(z_list)
                }).with_columns([
                    pl.col("time").cast(pl.Float64),
                    pl.col("scan_name").cast(pl.String),
                    pl.col("telescope_code").cast(pl.String),
                    pl.col("x").cast(pl.Float64),
                    pl.col("y").cast(pl.Float64),
                    pl.col("z").cast(pl.Float64)
                ])

                logger.info(f"Calculated interpolated orbits for {df['scan_name'].unique().len()} scans across {df['telescope_code'].unique().len()} telescopes in '{obs.get_observation_code()}', DF rows: {df.height}")
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.get_items())
            }
            df = self._process_object(obj, attributes, calculate_orbits, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                if attributes.get("recalculate", False) or not obj.get_calculated_data_by_key(store_key):
                    obj.set_calculated_data_by_key(store_key, df, metadata)

            return df
        except Exception as e:
            logger.error(f"Failed to calculate interpolated orbits for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {str(e)}")
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
            logger.info(f"Skipping interpolation for '{telescope.get_code()}' as use_kep=True")
            return np.array([])

        orbit_file = telescope.get_orbit()
        if not orbit_file:
            logger.warning(f"No orbit file defined for telescope '{telescope.get_code()}'")
            return np.array([])

        try:
            if np.any(np.isnan(times_mjd)) or np.any(np.isinf(times_mjd)):
                logger.error(f"Invalid MJD values in times for '{telescope.get_code()}': {times_mjd}")
                return np.array([])

            orbit_data = self._load_orbit_data(orbit_file, start_time_mjd, end_time_mjd)
            if not orbit_data:
                logger.warning(f"No valid orbit data for '{telescope.get_code()}' in time range {start_time_mjd} to {end_time_mjd}")
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

            if not valid_interp_times.size:
                logger.warning(f"No valid interpolation times for '{telescope.get_code()}' in range {start_time_mjd} to {end_time_mjd}")
                return np.full((len(times_mjd), 3), np.nan)

            unique_indices = np.unique(data_times, return_index=True)[1]
            filtered_times = data_times[unique_indices]
            filtered_positions = positions[unique_indices]

            if len(filtered_times) < 2:
                logger.warning(f"Too few points ({len(filtered_times)}) for interpolation for '{telescope.get_code()}'")
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
                logger.warning(f"Interpolated positions for '{telescope.get_code()}' contain NaN values")

            logger.info(f"Interpolated orbit for '{telescope.get_code()}' using {method} with {len(valid_interp_times)} points")
            return full_positions

        except Exception as e:
            logger.error(f"Failed to interpolate orbit for '{telescope.get_code()}': {str(e)}")
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
                logger.warning(f"Orbit file '{orbit_file}' contains NaN values")
                return {}

            orbit_data = {
                "times": times_mjd,
                "positions": positions,
                "velocities": velocities
            }

            if start_time_mjd is not None and end_time_mjd is not None:
                mask = (times_mjd >= start_time_mjd) & (times_mjd <= end_time_mjd)
                if not np.any(mask):
                    logger.warning(f"No orbit data within time range {start_time_mjd} to {end_time_mjd} for file '{orbit_file}'")
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
                    logger.warning(f"No active scans in observation '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_positions"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                if times_df.is_empty():
                    logger.error(f"No time data for '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_positions"))

                has_orbit_telescopes = any(isinstance(tel, SpaceTelescope) and not tel.get("use_kep") for tel in telescopes)
                orbit_df = pl.DataFrame()
                if has_orbit_telescopes:
                    orbit_attrs = {"time_step": time_step, "store_key": "interpolated_orbits", "recalculate": recalculate}
                    orbit_df = self._calculate_interpolated_orbits(obs, orbit_attrs)
                    logger.debug(f"Orbit data for '{obs.get_observation_code()}': {not orbit_df.is_empty()}")

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
                            logger.warning(f"No valid times for scan '{scan_name}' in observation '{obs.get_observation_code()}'")
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
                    logger.info(f"Excluded {len(set(excluded_telescopes))} telescopes: {', '.join(set(excluded_telescopes))}")

                if not times_list:
                    logger.warning(f"No valid positions computed for '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_positions"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "x": np.concatenate(x_list),
                    "y": np.concatenate(y_list),
                    "z": np.concatenate(z_list)
                }).with_columns([
                    pl.col("time").cast(pl.Float64),
                    pl.col("scan_name").cast(pl.String),
                    pl.col("telescope_code").cast(pl.String),
                    pl.col("x").cast(pl.Float64),
                    pl.col("y").cast(pl.Float64),
                    pl.col("z").cast(pl.Float64)
                ])

                logger.info(f"Calculated positions for {df['scan_name'].unique().len()} scans in '{obs.get_observation_code()}', DF rows: {df.height}")
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.get_items())
            }
            df = self._process_object(obj, attributes, calculate_positions, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                if attributes.get("recalculate", False) or not obj.get_calculated_data_by_key(store_key):
                    obj.set_calculated_data_by_key(store_key, df, metadata)

            return df
        except Exception as e:
            logger.error(f"Failed to calculate telescope positions for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {str(e)}")
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
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return None

        scan_name = scan.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [tel for tel in scan_telescopes.get_items() if tel.isactive]
        if not active_telescopes:
            logger.warning(f"No active telescopes for scan '{scan_name}' starting at {scan.get_start().isot}")
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source.name}'")
            return None

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
                    logger.warning(f"No orbit data for telescope '{tel_code}' in scan '{scan_name}'")
                    continue
                positions = tel_orbit.select(["x", "y", "z"]).to_numpy()
                if len(positions) != n_times:
                    logger.warning(f"Orbit data length mismatch for '{tel_code}' in scan '{scan_name}': got {len(positions)}, expected {n_times}")
                    positions = np.full((n_times, 3), np.nan)
                    positions[:min(len(positions), n_times)] = tel_orbit.select(["x", "y", "z"]).to_numpy()[:n_times]
            else:
                positions = self._compute_telescope_position(tel, times_mjd)
                if positions.shape[0] != n_times:
                    logger.warning(f"Position data length mismatch for '{tel_code}' in scan '{scan_name}': got {positions.shape[0]}, expected {n_times}")
                    positions = np.full((n_times, 3), np.nan)
                    positions[:min(positions.shape[0], n_times)] = positions[:n_times]

            if np.all(np.isnan(positions)):
                logger.warning(f"All positions are NaN for telescope '{tel_code}' in scan '{scan_name}'")
                continue

            times_list.append(times_mjd)
            scan_names.append(np.full(n_times, scan_name, dtype=object))
            telescope_codes.append(np.full(n_times, tel_code, dtype=object))
            x_list.append(positions[:, 0])
            y_list.append(positions[:, 1])
            z_list.append(positions[:, 2])

        if not times_list:
            logger.warning(f"No valid positions computed for scan '{scan_name}'")
            return None

        logger.debug(f"Computed {len(telescope_codes)} telescope positions for scan '{scan_name}'")
        return (
            np.concatenate(times_list),
            np.concatenate(scan_names),
            np.concatenate(telescope_codes),
            np.concatenate(x_list),
            np.concatenate(y_list),
            np.concatenate(z_list)
        )

    def _compute_telescope_position(self, telescope: Telescope | SpaceTelescope, times_mjd: np.ndarray) -> np.ndarray:
        """Compute a telescope's GCRS position at specified times.

        Args:
            telescope (Telescope | SpaceTelescope): The telescope to compute position for.
            times_mjd (np.ndarray): Array of times for calculation (MJD as float).

        Returns:
            np.ndarray: GCRS coordinates (x, y, z) in meters, shape (n_times, 3).
        """
        n_times = len(times_mjd)
        nan_result = np.full((n_times, 3), np.nan, dtype=float)

        try:
            if isinstance(telescope, Telescope) and not isinstance(telescope, SpaceTelescope):
                x, y, z = telescope.get_coordinates()
                res = telescope.get(["vx", "vy", "vz"])
                vx, vy, vz = res["vx"], res["vy"], res["vz"]
                dt = (times_mjd - Time("2000-01-01T12:00:00").mjd) * 86400.0  # секунды с J2000
                itrs_coords = CartesianRepresentation(
                    x + vx * dt,
                    y + vy * dt,
                    z + vz * dt,
                    unit=u.m
                )
                itrs = ITRS(itrs_coords, obstime=Time(times_mjd, format="mjd", scale="utc"))
                gcrs = itrs.transform_to(GCRS(obstime=Time(times_mjd, format="mjd", scale="utc")))
                pos = np.stack([gcrs.cartesian.x.value, gcrs.cartesian.y.value, gcrs.cartesian.z.value], axis=-1)
                if np.any(np.isnan(pos)):
                    logger.warning(f"Computed NaN position for ground telescope '{telescope.get_code()}'")
                return pos
            elif isinstance(telescope, SpaceTelescope) and telescope.get("use_kep"):
                kepler = telescope.get("kepler_elements")
                if kepler is None:
                    logger.warning(f"No Keplerian elements defined for telescope '{telescope.get_code()}'")
                    return nan_result
                a = kepler["a"]  # semi-major axis (m)
                e = kepler["e"]  # eccentricity
                i = np.radians(kepler["i"])  # inclination (deg to rad)
                raan = np.radians(kepler["raan"])  # RA of ascending node (deg to rad)
                argp = np.radians(kepler["argp"])  # argument of periapsis (deg to rad)
                nu0 = np.radians(kepler["nu"])  # true anomaly at epoch (deg to rad)
                epoch = kepler["epoch"].mjd
                mu = kepler["mu"]  # gravitational parameter (m^3/s^2)
                n = np.sqrt(mu / a**3)
                dt = (times_mjd - epoch) * 86400.0  # секунды с эпохи
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
                pos = np.array([R @ p_i for p_i in p])
                if np.any(np.isnan(pos)):
                    logger.warning(f"Keplerian position for '{telescope.get_code()}' contains NaN")
                return pos
            else:
                logger.warning(f"Position for SpaceTelescope '{telescope.get_code()}' should be precomputed in interpolated_orbits")
                return nan_result
        except Exception as e:
            logger.warning(f"Unexpected error in computing position for '{telescope.get_code()}': {str(e)}")
            return nan_result

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
                    logger.warning(f"No active scans in observation '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("source_visibility"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": recalculate}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                position_df = self._calculate_telescope_positions(obs, position_attrs)

                if times_df.is_empty() or position_df.is_empty():
                    logger.error(f"Missing time or position data for '{obs.get_observation_code()}'")
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
                            logger.warning(f"No valid times for scan '{scan_name}' in observation '{obs.get_observation_code()}'")
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
                    logger.warning(f"No valid visibility data computed for '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("source_visibility"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "source_name": np.concatenate(source_names),
                    "visibility": np.concatenate(is_visible_list)
                }).with_columns([
                    pl.col("time").cast(pl.Float64),
                    pl.col("scan_name").cast(pl.String),
                    pl.col("telescope_code").cast(pl.String),
                    pl.col("source_name").cast(pl.String),
                    pl.col("visibility").cast(pl.Boolean)
                ])

                logger.info(f"Calculated visibility for {df['scan_name'].unique().len()} scans across {df['telescope_code'].unique().len()} telescopes in '{obs.get_observation_code()}', DF rows: {df.height}")
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.get_items()),
                "position_store_key": position_store_key
            }
            df = self._process_object(obj, attributes, calculate_visibility, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                if attributes.get("recalculate", False) or not obj.get_calculated_data_by_key(store_key):
                    obj.set_calculated_data_by_key(store_key, df, metadata)

            return df
        except Exception as e:
            logger.error(f"Failed to calculate source visibility for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {str(e)}")
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
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return None

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [tel for tel in scan_telescopes.get_items() if tel.isactive]
        if not active_telescopes:
            logger.warning(f"No active telescopes for scan '{scan_name}' starting at {scan.get_start().isot}")
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return None

        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')

        times_list = []
        scan_names = []
        telescope_codes = []
        source_names = []
        is_visible_list = []

        for tel in active_telescopes:
            tel_code = tel.get_code()
            tel_positions = position_df.filter(pl.col("telescope_code") == tel_code)
            if tel_positions.is_empty():
                logger.warning(f"No position data for telescope '{tel_code}' in scan '{scan_name}'")
                continue

            positions = tel_positions.select(["x", "y", "z"]).to_numpy()
            if len(positions) != n_times:
                logger.warning(f"Position data length mismatch for '{tel_code}' in scan '{scan_name}': got {len(positions)}, expected {n_times}")
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
                itrs = GCRS(gcrs_coords, obstime=Time(times_mjd, format="mjd", scale="utc")).transform_to(ITRS(obstime=Time(times_mjd, format="mjd", scale="utc")))
                locations = itrs.earth_location
                altaz = source_coord.transform_to(AltAz(obstime=Time(times_mjd, format="mjd", scale="utc"), location=locations))
                hadec = source_coord.transform_to(HADec(obstime=Time(times_mjd, format="mjd", scale="utc"), location=locations))
                el = altaz.alt.deg
                az = altaz.az.deg
                ha = hadec.ha.deg
                dec = hadec.dec.deg

                mount_type = tel.get("mount_type").value
                valid_positions = ~nan_positions
                if not np.any(valid_positions):
                    logger.warning(f"All positions are NaN for ground telescope '{tel_code}' in scan '{scan_name}'")
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
                    logger.warning(f"Unsupported mount type '{mount_type}' for telescope '{tel_code}' in scan '{scan_name}'")
                    continue

            times_list.append(times_mjd)
            scan_names.append(np.full(n_times, scan_name, dtype=object))
            telescope_codes.append(np.full(n_times, tel_code, dtype=object))
            source_names.append(np.full(n_times, source_name, dtype=object))
            is_visible_list.append(is_visible)

            logger.debug(f"Computed visibility for telescope '{tel_code}' in scan '{scan_name}': {np.sum(is_visible)} visible points")

        if not times_list:
            logger.warning(f"No visibility data computed for scan '{scan_name}'")
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
                logger.info(f"Ignoring 'freq_name' attribute for UV coverage calculation in geometric coordinates")

            def calculate_uv(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, telescopes, _ = self._get_active_components(obs, require_telescopes=True, min_telescopes=2)
                if not scans:
                    logger.warning(f"No active scans in observation '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("uv_coverage"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": recalculate}
                visibility_attrs = {"time_step": time_step, "store_key": "source_visibility", "recalculate": recalculate}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                position_df = self._calculate_telescope_positions(obs, position_attrs)
                visibility_df = self._calculate_source_visibility(obs, visibility_attrs)

                if times_df.is_empty() or position_df.is_empty() or visibility_df.is_empty():
                    logger.error(f"Missing time, position, or visibility data for '{obs.get_observation_code()}'")
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
                            logger.warning(f"No valid times for scan '{scan_name}' in observation '{obs.get_observation_code()}'")
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
                    logger.warning(f"No valid UV coverage data computed for '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("uv_coverage"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "source_name": np.concatenate(source_names),
                    "scan_name": np.concatenate(scan_names),
                    "baseline": np.concatenate(baselines),
                    "u": np.concatenate(u_list),
                    "v": np.concatenate(v_list),
                    "w": np.concatenate(w_list)
                }).with_columns([
                    pl.col("time").cast(pl.Float64),
                    pl.col("source_name").cast(pl.String),
                    pl.col("scan_name").cast(pl.String),
                    pl.col("baseline").cast(pl.String),
                    pl.col("u").cast(pl.Float64),
                    pl.col("v").cast(pl.Float64),
                    pl.col("w").cast(pl.Float64)
                ])

                logger.info(f"Calculated UV coverage for {df['scan_name'].unique().len()} scans across {df['baseline'].unique().len()} baselines in '{obs.get_observation_code()}', DF rows: {df.height}")
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.get_items())
            }
            df = self._process_object(obj, attributes, calculate_uv, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                metadata["baseline_count"] = df["baseline"].unique().len()
                if attributes.get("recalculate", False) or not obj.get_calculated_data_by_key(store_key):
                    obj.set_calculated_data_by_key(store_key, df, metadata)

            return df
        except Exception as e:
            logger.error(f"Failed to calculate UV coverage for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {str(e)}")
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
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return None

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        if len(active_telescopes) < 2:
            logger.warning(f"Insufficient telescopes ({len(active_telescopes)}) for UV coverage in scan '{scan_name}'")
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
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
                logger.warning(f"Missing or mismatched position data for telescope '{tel_code}' in scan '{scan_name}'")
            if not tel_visibility.is_empty() and len(tel_visibility) == n_times:
                visibility[i] = tel_visibility["visibility"].to_numpy()
            else:
                logger.warning(f"Missing or mismatched visibility data for telescope '{tel_code}' in scan '{scan_name}'")

        try:
            uv_points = self._compute_uv_at_time(active_telescopes, times_mjd, source, visibility, positions)
        except Exception as e:
            logger.error(f"Failed to calculate UV coverage for scan '{scan_name}': {str(e)}")
            return None

        if not uv_points:
            logger.warning(f"No valid UV points computed for scan '{scan_name}'")
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
                logger.debug(f"No valid UVW points for baseline '{pair}' in scan '{scan_name}'")
                continue
            times_list.append(times_mjd[valid_indices])
            scan_names.append(np.full(n_valid, scan_name, dtype=object))
            baselines.append(np.full(n_valid, pair, dtype=object))
            source_names.append(np.full(n_valid, source_name, dtype=object))
            u_list.append(uvw[valid_indices, 0])
            v_list.append(uvw[valid_indices, 1])
            w_list.append(uvw[valid_indices, 2])

        if not times_list:
            logger.warning(f"No valid UV coverage data computed for scan '{scan_name}'")
            return None

        logger.debug(f"Computed UV coverage for {len(uv_points)} baselines in scan '{scan_name}'")
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
            logger.warning(f"Insufficient telescopes ({len(telescopes)}) to compute (u,v,w)")
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
            logger.error(f"Visibility shape {visibility.shape} does not match expected ({n_tels}, {n_times})")
            return {}
        if gcrs_positions.shape != (n_tels, n_times, 3):
            logger.error(f"Position shape {gcrs_positions.shape} does not match expected ({n_tels}, {n_times}, 3)")
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
            logger.debug(f"Computed {valid_count} valid UVW points for baseline '{pair}' (total {n_times} points)")

        if not uv_points:
            logger.warning(f"No valid UVW points computed for any baseline")
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
                    logger.warning(f"No active scans in observation '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("sun_angles"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": recalculate}
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": recalculate}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                position_df = self._calculate_telescope_positions(obs, position_attrs)
                visibility_df = self._calculate_source_visibility(obs, visibility_attrs)

                if times_df.is_empty() or position_df.is_empty() or visibility_df.is_empty():
                    logger.error(f"Missing time, position, or visibility data for '{obs.get_observation_code()}'")
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
                            logger.warning(f"No valid times for scan '{scan_name}' in observation '{obs.get_observation_code()}'")
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
                    logger.warning(f"No valid sun angles computed for '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("sun_angles"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "source_name": np.concatenate(source_names),
                    "angle": np.concatenate(sun_angles_list)
                }).with_columns([
                    pl.col("time").cast(pl.Float64),
                    pl.col("scan_name").cast(pl.String),
                    pl.col("telescope_code").cast(pl.String),
                    pl.col("source_name").cast(pl.String),
                    pl.col("angle").cast(pl.Float64)
                ])

                logger.info(f"Calculated sun angles for {df['scan_name'].unique().len()} scans across {df['telescope_code'].unique().len()} telescopes in '{obs.get_observation_code()}', DF rows: {df.height}")
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.get_items()),
                "position_store_key": position_store_key,
                "visibility_store_key": visibility_store_key
            }
            df = self._process_object(obj, attributes, calculate_sun_angles, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                if attributes.get("recalculate", False) or not obj.get_calculated_data_by_key(store_key):
                    obj.set_calculated_data_by_key(store_key, df, metadata)

            return df
        except Exception as e:
            logger.error(f"Failed to calculate sun angles for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {str(e)}")
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
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return None

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [tel for tel in scan_telescopes.get_items() if tel.isactive]
        if not active_telescopes:
            logger.warning(f"No active telescopes for scan '{scan_name}' starting at {scan.get_start().isot}")
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return None

        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')

        times_list = []
        scan_names = []
        telescope_codes = []
        source_names = []
        sun_angles_list = []

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
                logger.warning(f"No position or visibility data for telescope '{tel_code}' in scan '{scan_name}'")
                continue

            positions = tel_positions.select(["x", "y", "z"]).to_numpy()
            visibility = tel_visibility["visibility"].to_numpy()
            if len(positions) != n_times or len(visibility) != n_times:
                logger.warning(f"Data length mismatch for '{tel_code}' in scan '{scan_name}': positions={len(positions)}, visibility={len(visibility)}, expected {n_times}")
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
                        logger.error(f"Invalid source vector for '{source_name}' in scan '{scan_name}': norm={source_norm}")
                        continue
                    source_unit = source_vec / source_norm
                    valid_sun_vec = sun_vec[is_visible]
                    sun_norm = np.linalg.norm(valid_sun_vec, axis=1)
                    valid = sun_norm > 0
                    if not np.any(valid):
                        logger.warning(f"No valid Sun vectors for space telescope '{tel_code}' in scan '{scan_name}'")
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
                    itrs = GCRS(gcrs_coords, obstime=Time(times_mjd, format="mjd", scale="utc")).transform_to(ITRS(obstime=Time(times_mjd, format="mjd", scale="utc")))
                    locations = itrs.earth_location
                    sun_altaz = sun_coord.transform_to(AltAz(obstime=Time(times_mjd, format="mjd", scale="utc"), location=locations))
                    source_altaz = source_coord.transform_to(AltAz(obstime=Time(times_mjd, format="mjd", scale="utc"), location=locations))
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

                logger.debug(f"Computed {np.sum(is_visible)} sun angles for telescope '{tel_code}' in scan '{scan_name}'")

            times_list.append(times_mjd)
            scan_names.append(np.full(n_times, scan_name, dtype=object))
            telescope_codes.append(np.full(n_times, tel_code, dtype=object))
            source_names.append(np.full(n_times, source_name, dtype=object))
            sun_angles_list.append(sun_angles)

        if not times_list:
            logger.warning(f"No sun angles computed for scan '{scan_name}'")
            return None

        logger.debug(f"Computed sun angles for {len(telescope_codes)} telescopes in scan '{scan_name}'")
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
                    logger.warning(f"No active scans in observation '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("az_el"))

                ground_telescopes = [tel for tel in telescopes if not isinstance(tel, SpaceTelescope)]
                if not ground_telescopes:
                    logger.debug(f"No ground telescopes in '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("az_el"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": recalculate}
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": recalculate}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                position_df = self._calculate_telescope_positions(obs, position_attrs)
                visibility_df = self._calculate_source_visibility(obs, visibility_attrs)

                if times_df.is_empty() or position_df.is_empty() or visibility_df.is_empty():
                    logger.error(f"Missing time, position, or visibility data for '{obs.get_observation_code()}'")
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
                            logger.warning(f"No valid times for scan '{scan_name}' in observation '{obs.get_observation_code()}'")
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
                    logger.warning(f"No valid az/el or ha/dec angles computed for '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("az_el"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "source_name": np.concatenate(source_names),
                    "az": np.concatenate(az_ha_list),
                    "el": np.concatenate(el_dec_list)
                }).with_columns([
                    pl.col("time").cast(pl.Float64),
                    pl.col("scan_name").cast(pl.String),
                    pl.col("telescope_code").cast(pl.String),
                    pl.col("source_name").cast(pl.String),
                    pl.col("az").cast(pl.Float64),
                    pl.col("el").cast(pl.Float64)
                ])

                logger.info(f"Calculated az/el or ha/dec for {df['scan_name'].unique().len()} scans across {df['telescope_code'].unique().len()} telescopes in '{obs.get_observation_code()}', DF rows: {df.height}")
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.get_items()),
                "position_store_key": position_store_key,
                "visibility_store_key": visibility_store_key
            }
            df = self._process_object(obj, attributes, calculate_az_el, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                if attributes.get("recalculate", False) or not obj.get_calculated_data_by_key(store_key):
                    obj.set_calculated_data_by_key(store_key, df, metadata)

            return df
        except Exception as e:
            logger.error(f"Failed to calculate az/el or ha/dec for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {str(e)}")
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
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return None

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive and not isinstance(t, SpaceTelescope)]
        if not active_telescopes:
            logger.warning(f"No active ground telescopes for scan '{scan_name}' starting at {scan.get_start().isot}")
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return None

        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')

        times_list = []
        scan_names = []
        telescope_codes = []
        source_names = []
        az_ha_list = []
        el_dec_list = []

        for tel in active_telescopes:
            tel_code = tel.get_code()
            mount_type = tel.get("mount_type").value
            if mount_type not in ["AZIM", "EQUA"]:
                logger.warning(f"Unsupported mount type '{mount_type}' for telescope '{tel_code}' in scan '{scan_name}'")
                continue

            tel_positions = position_df.filter(pl.col("telescope_code") == tel_code)
            tel_visibility = visibility_df.filter(pl.col("telescope_code") == tel_code)
            if tel_positions.is_empty() or tel_visibility.is_empty():
                logger.warning(f"No position or visibility data for telescope '{tel_code}' in scan '{scan_name}'")
                continue

            positions = tel_positions.select(["x", "y", "z"]).to_numpy()
            visibility = tel_visibility["visibility"].to_numpy()
            if len(positions) != n_times or len(visibility) != n_times:
                logger.warning(f"Data length mismatch for '{tel_code}' in scan '{scan_name}': positions={len(positions)}, visibility={len(visibility)}, expected {n_times}")
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
                itrs = GCRS(gcrs_coords, obstime=Time(times_mjd, format="mjd", scale="utc")).transform_to(ITRS(obstime=Time(times_mjd, format="mjd", scale="utc")))
                locations = itrs.earth_location
                if mount_type == "AZIM":
                    altaz = source_coord.transform_to(AltAz(obstime=Time(times_mjd, format="mjd", scale="utc"), location=locations))
                    az_ha[is_visible] = altaz.az.deg[is_visible]
                    el_dec[is_visible] = altaz.alt.deg[is_visible]
                else:  # EQUA
                    hadec = source_coord.transform_to(HADec(obstime=Time(times_mjd, format="mjd", scale="utc"), location=locations))
                    az_ha[is_visible] = hadec.ha.deg[is_visible]
                    el_dec[is_visible] = hadec.dec.deg[is_visible]

                logger.debug(f"Computed {np.sum(is_visible)} az/el or ha/dec angles for telescope '{tel_code}' in scan '{scan_name}'")

            times_list.append(times_mjd)
            scan_names.append(np.full(n_times, scan_name, dtype=object))
            telescope_codes.append(np.full(n_times, tel_code, dtype=object))
            source_names.append(np.full(n_times, source_name, dtype=object))
            az_ha_list.append(az_ha)
            el_dec_list.append(el_dec)

        if not times_list:
            logger.warning(f"No valid az/el or ha/dec angles computed for scan '{scan_name}'")
            return None

        logger.debug(f"Computed az/el or ha/dec for {len(telescope_codes)} telescopes in scan '{scan_name}'")
        return (
            np.concatenate(times_list),
            np.concatenate(scan_names),
            np.concatenate(telescope_codes),
            np.concatenate(source_names),
            np.concatenate(az_ha_list),
            np.concatenate(el_dec_list)
        )

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
                    logger.warning(f"No active scans in observation '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("time_on_source"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": recalculate}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                visibility_df = self._calculate_source_visibility(obs, visibility_attrs)

                if times_df.is_empty() or visibility_df.is_empty():
                    logger.error(f"Missing time or visibility data for '{obs.get_observation_code()}'")
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
                            logger.warning(f"No valid times for scan '{scan_name}' in observation '{obs.get_observation_code()}'")
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
                    logger.warning(f"No valid time-on-source blocks computed for '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("time_on_source"))

                df = pl.DataFrame({
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "source_name": np.concatenate(source_names),
                    "start": np.concatenate(start_mjd_list),
                    "end": np.concatenate(end_mjd_list),
                    "duration": np.concatenate(durations_list)
                }).with_columns([
                    pl.col("scan_name").cast(pl.String),
                    pl.col("telescope_code").cast(pl.String),
                    pl.col("source_name").cast(pl.String),
                    pl.col("start").cast(pl.Float64),
                    pl.col("end").cast(pl.Float64),
                    pl.col("duration").cast(pl.Float64)
                ])

                logger.info(f"Calculated time-on-source for {df['scan_name'].unique().len()} scans across {df['telescope_code'].unique().len()} telescopes in '{obs.get_observation_code()}', DF rows: {df.height}")
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.get_items()),
                "visibility_store_key": visibility_store_key
            }
            df = self._process_object(obj, attributes, calculate_time_on_source, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                if attributes.get("recalculate", False) or not obj.get_calculated_data_by_key(store_key):
                    obj.set_calculated_data_by_key(store_key, df, metadata)

            return df
        except Exception as e:
            logger.error(f"Failed to calculate time on source for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {str(e)}")
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
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return None

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        if not active_telescopes:
            logger.warning(f"No active telescopes for scan '{scan_name}' starting at {scan.get_start().isot}")
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
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
                logger.warning(f"No visibility data for telescope '{tel_code}' in scan '{scan_name}'")
                continue

            visibility = tel_visibility["visibility"].to_numpy()
            if len(visibility) != n_times:
                logger.warning(f"Visibility data length mismatch for '{tel_code}' in scan '{scan_name}': got {len(visibility)}, expected {n_times}")
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
                logger.debug(f"No visibility blocks for telescope '{tel_code}' in scan '{scan_name}'")
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

            logger.debug(f"Computed {n_blocks} time-on-source blocks for telescope '{tel_code}' in scan '{scan_name}'")

        if not scan_names:
            logger.warning(f"No time-on-source blocks computed for scan '{scan_name}'")
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
    def _calculate_beam_pattern(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame | Dict[str, pl.DataFrame]:
        """Calculate beam pattern for active telescopes in the observation or project, independent of frequency.

        Args:
            obj: The object to calculate beam pattern for.
            attributes: Parameters including "store_key", "recalculate", "theta_min", "theta_max", "theta_points".

        Returns:
            pl.DataFrame | Dict[str, pl.DataFrame]: For Observation, returns a Polars DataFrame with columns
                ["telescope_code", "theta", "pattern"], where theta and pattern are scalar float values (float64).
                For ScheduleProject, returns a dictionary mapping observation codes to Polars DataFrames.

        Notes:
            - Uses CalculatedDataStructure to validate DataFrame structure and metadata.
            - Stores results under 'beam_pattern' key in each Observation's calculated_data.
            - Beam pattern is computed as (2 * j1(x) / x)^2, where x = diameter * sin(theta), normalized by maximum.
            - Preserves NaN in pattern where input data is invalid.
        """
        try:
            store_key = attributes.get("store_key", "beam_pattern")
            recalculate = attributes.get("recalculate", False)
            theta_min = attributes.get("theta_min", -np.pi / 2)
            theta_max = attributes.get("theta_max", np.pi / 2)
            theta_points = attributes.get("theta_points", 5000)

            if not isinstance(theta_min, (int, float)) or not isinstance(theta_max, (int, float)):
                logger.error(f"Invalid theta_min or theta_max type for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}', must be float")
                return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("beam_pattern")) if isinstance(obj, Observation) else {}
            if theta_min >= theta_max:
                logger.error(f"Invalid theta range: theta_min ({theta_min}) must be less than theta_max ({theta_max})")
                return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("beam_pattern")) if isinstance(obj, Observation) else {}
            if not isinstance(theta_points, int) or theta_points <= 0:
                logger.error(f"Invalid theta_points {theta_points} for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}', must be positive integer")
                return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("beam_pattern")) if isinstance(obj, Observation) else {}

            def calculate_beam_pattern(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                _, telescopes, _ = self._get_active_components(obs, require_scans=False, require_telescopes=True)
                if not telescopes:
                    logger.debug(f"No active telescopes for observation '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("beam_pattern"))

                obs_type = obs.get_observation_type()
                if obs_type not in ["SINGLE_DISH", "VLBI"]:
                    logger.warning(f"Beam pattern calculation is only for SINGLE_DISH or VLBI, got {obs_type} in '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("beam_pattern"))

                valid_telescopes = []
                diameters = []
                for tel in telescopes:
                    diameter = tel.get("diameter")
                    if diameter is None or not isinstance(diameter, (int, float)) or np.isnan(diameter):
                        logger.debug(f"Invalid diameter {diameter} for telescope '{tel.get_code()}' in '{obs.get_observation_code()}'; will produce NaN in pattern")
                        valid_telescopes.append(tel)
                        diameters.append(np.nan)
                    elif diameter <= 0:
                        logger.warning(f"Non-positive diameter {diameter} for telescope '{tel.get_code()}' in '{obs.get_observation_code()}'; will produce NaN in pattern")
                        valid_telescopes.append(tel)
                        diameters.append(np.nan)
                    else:
                        valid_telescopes.append(tel)
                        diameters.append(float(diameter))

                if not valid_telescopes:
                    logger.warning(f"No telescopes in '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("beam_pattern"))

                theta = np.linspace(theta_min, theta_max, theta_points)
                diameters = np.array(diameters)
                x = diameters[:, None] * np.sin(theta)
                pattern = np.full_like(x, np.nan)
                valid_diameters = ~np.isnan(diameters)
                x_valid = x[valid_diameters]
                if x_valid.size > 0:
                    pattern[valid_diameters] = (2 * j1(x_valid) / x_valid) ** 2
                    pattern[valid_diameters] = np.where(np.isnan(pattern[valid_diameters]), 1.0, pattern[valid_diameters])
                    max_pattern = np.max(pattern[valid_diameters], axis=1, keepdims=True)
                    valid_max = (max_pattern != 0) & (~np.isnan(max_pattern))
                    pattern[valid_diameters] = np.where(valid_max, pattern[valid_diameters] / max_pattern, np.nan)

                beam_dfs = []  # Collect small DataFrames for concatenation
                for tel, pat in zip(valid_telescopes, pattern):
                    tel_code = tel.get_code()
                    valid_points = np.sum(~np.isnan(pat))
                    if valid_points > 0:
                        beam_dfs.append(pl.DataFrame({
                            "telescope_code": [tel_code] * len(theta),
                            "theta": theta,
                            "pattern": pat
                        }, schema=CalculatedDataStructure.get_dtypes("beam_pattern")))
                        logger.debug(f"Computed {valid_points} valid beam pattern points for telescope '{tel_code}' in '{obs.get_observation_code()}'")

                if beam_dfs:
                    result_df = pl.concat(beam_dfs, how="vertical")
                else:
                    logger.warning(f"No beam patterns computed for observation '{obs.get_observation_code()}'")
                    result_df = pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("beam_pattern"))

                logger.info(f"Computed beam pattern for {len(valid_telescopes)} telescopes in '{obs.get_observation_code()}'")
                return result_df

            metadata = {
                "telescope_count": len(obj.get_telescopes().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_telescopes().get_active_items()) for o in obj.get_observations()),
                "frequency_agnostic": True,
                "scale_instruction": "Multiply pattern by wavelength during visualization",
                "theta_min": float(theta_min),
                "theta_max": float(theta_max),
                "theta_points": theta_points
            }
            logger.debug(f"Metadata for '{store_key}' in '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {metadata}")
            return self._process_object(obj, attributes, calculate_beam_pattern, store_key, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate beam pattern for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {str(e)}")
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("beam_pattern")) if isinstance(obj, Observation) else {}

    @time_execution
    def _calculate_baseline_projections(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame | Dict[str, pl.DataFrame]:
        """Calculate baseline projections for VLBI observations in geometric coordinates (meters).

        Args:
            obj: The object to calculate projections for.
            attributes: Parameters including "time_step", "store_key", "recalculate", "freq_name" (ignored).

        Returns:
            pl.DataFrame | Dict[str, pl.DataFrame]: For Observation, returns a Polars DataFrame with columns
                ["time", "source_name", "scan_name", "baseline", "projection"], where "time" is MJD (float64).
                For ScheduleProject, returns a dictionary mapping observation codes to Polars DataFrames.

        Notes:
            - Uses CalculatedDataStructure to validate DataFrame structure.
            - Stores results under 'baseline_projections' key in each Observation's calculated_data.
            - Computes BL = sqrt(u² + v²) from UV data in meters.
            - Preserves NaN in projection where input UV data contains NaN.
        """
        try:
            time_step = attributes.get("time_step")
            if time_step is not None:
                if not isinstance(time_step, (int, float)):
                    logger.error(f"Invalid time_step type '{type(time_step)}' for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}', must be float")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections")) if isinstance(obj, Observation) else {}
                if time_step <= 0:
                    logger.error(f"Invalid time_step {time_step} for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}', must be positive")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections")) if isinstance(obj, Observation) else {}
            time_step = float(time_step) if time_step is not None else 0.0

            store_key = attributes.get("store_key", "baseline_projections")
            recalculate = attributes.get("recalculate", False)
            if "freq_name" in attributes:
                logger.info(f"Ignoring 'freq_name' attribute for baseline projections in geometric coordinates")

            def calculate_baseline_projections(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                if obs.get_observation_type() != "VLBI":
                    logger.warning(f"Baseline projections are only for VLBI, got {obs.get_observation_type()} in '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

                scans, telescopes, _ = self._get_active_components(obs, require_telescopes=True, min_telescopes=2)
                if not scans:
                    logger.debug(f"No active scans for observation '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

                uv_attrs = {"time_step": time_step, "store_key": "uv_coverage", "recalculate": recalculate}
                uv_data = self._calculate_uv_coverage(obs, uv_attrs)
                if uv_data.is_empty():
                    logger.error(f"No UV coverage data for '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                time_data = self._calculate_time_arrays(obs, time_attrs)
                if time_data.is_empty():
                    logger.error(f"No time data for '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

                baseline_dfs = []  # Collect small DataFrames for concatenation

                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_baseline_projections, scan, obs, time_step, uv_data, time_data): scan
                        for scan in scans
                    }
                    for future in futures:
                        scan_result = future.result()
                        if not scan_result.is_empty():
                            baseline_dfs.append(scan_result)

                if baseline_dfs:
                    result_df = pl.concat(baseline_dfs, how="vertical")
                else:
                    logger.warning(f"No baseline projections computed for observation '{obs.get_observation_code()}'")
                    result_df = pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

                logger.info(f"Computed baseline projections for {len(result_df['scan_name'].unique())} scans in '{obs.get_observation_code()}'")
                return result_df

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.get_observations()),
                "frequency_agnostic": True
            }
            logger.debug(f"Metadata for '{store_key}' in '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {metadata}")
            return self._process_object(obj, attributes, calculate_baseline_projections, store_key, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate baseline projections for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {str(e)}")
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections")) if isinstance(obj, Observation) else {}

    def _process_baseline_projections(self, scan: Scan, observation: Observation, time_step: Optional[float], 
                                    uv_data: pl.DataFrame, time_data: pl.DataFrame) -> pl.DataFrame:
        """Process baseline projections for a single scan in geometric coordinates (meters).

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds).
            uv_data (pl.DataFrame): Precomputed UV data with columns ["time", "source_name", "scan_name", "baseline", "u", "v", "w"].
            time_data (pl.DataFrame): Precomputed time arrays with columns ["time", "scan_name"], where "time" is MJD (float64).

        Returns:
            pl.DataFrame: Baseline projections with columns ["time", "source_name", "scan_name", "baseline", "projection"],
                where "time" is MJD (float64) and "projection" is in meters (float64).

        Notes:
            - Computes BL = sqrt(u² + v²) from UV data in meters.
            - Preserves NaN in projection where UV data is NaN or source is not visible.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_active_items() if t.isactive]

        if len(active_telescopes) < 2:
            start_time_mjd = scan.get_start().mjd if scan.get_start() else None
            logger.warning(f"Insufficient telescopes ({len(active_telescopes)}) for baseline projections in scan '{scan_name}' at MJD {start_time_mjd}")
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

        scan_times = time_data.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
        if len(scan_times) == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

        n_times = len(scan_times)
        scan_uv_data = uv_data.filter(pl.col("scan_name") == scan_name)
        if scan_uv_data.is_empty():
            logger.warning(f"No UV data for scan '{scan_name}' in source '{source_name}'")
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

        projections_dict = self._compute_projections_from_uv(scan_uv_data, active_telescopes, time_step, n_times)
        if not projections_dict:
            logger.warning(f"No valid baseline projections computed for scan '{scan_name}'")
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

        baseline_dfs = []  # Collect small DataFrames for concatenation
        for baseline, proj_array in projections_dict.items():
            valid_count = np.sum(~np.isnan(proj_array))
            if valid_count > 0:
                baseline_dfs.append(pl.DataFrame({
                    "time": scan_times,
                    "source_name": [source_name] * n_times,
                    "scan_name": [scan_name] * n_times,
                    "baseline": [baseline] * n_times,
                    "projection": proj_array
                }, schema=CalculatedDataStructure.get_dtypes("baseline_projections")))
                logger.debug(f"Computed {valid_count} valid projections for baseline '{baseline}' in scan '{scan_name}'")

        if baseline_dfs:
            result_df = pl.concat(baseline_dfs, how="vertical")
        else:
            logger.warning(f"No baseline projections computed for scan '{scan_name}'")
            result_df = pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

        return result_df

    def _compute_projections_from_uv(self, uv_data: pl.DataFrame, telescopes: List[Telescope | SpaceTelescope], 
                                    time_step: Optional[float], n_times: int) -> Dict[str, np.ndarray]:
        """Compute baseline projections BL = sqrt(u² + v²) from UV data in meters.

        Args:
            uv_data (pl.DataFrame): UV data with columns ["time", "source_name", "scan_name", "baseline", "u", "v", "w"].
            telescopes (List[Telescope | SpaceTelescope]): List of active telescopes.
            time_step (Optional[float]): Sampling interval (seconds).
            n_times (int): Expected number of time points to match.

        Returns:
            Dict[str, np.ndarray]: Baseline projections in meters, formatted as {baseline: np.array([proj1, ..., projn])}.

        Notes:
            - Computes BL = sqrt(u² + v²) for each baseline.
            - Preserves NaN in projections where u or v is NaN.
        """
        projections = {}
        pairs = [f"{telescopes[i].get_code()}-{telescopes[j].get_code()}" for i, j in zip(*np.triu_indices(len(telescopes), k=1))]

        # Batch filter UV data for all baselines
        filtered_uv_data = uv_data.filter(pl.col("baseline").is_in(pairs))

        for baseline in pairs:
            baseline_data = filtered_uv_data.filter(pl.col("baseline") == baseline)[["time", "u", "v", "w"]]
            if baseline_data.is_empty():
                logger.debug(f"No UV data for baseline '{baseline}'")
                projections[baseline] = np.full(n_times, np.nan, dtype=float)
                continue

            uvw = baseline_data[["u", "v", "w"]].to_numpy()
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
    def _calculate_mollweide_tracks(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame | Dict[str, pl.DataFrame]:
        """Calculate Mollweide projection tracks for telescopes in active scans.

        Args:
            obj: The object to calculate tracks for.
            attributes: Parameters including "time_step", "store_key", "recalculate".

        Returns:
            pl.DataFrame | Dict[str, pl.DataFrame]: For Observation, returns a Polars DataFrame with columns
                ["time", "scan_name", "telescope_code", "lon", "lat"], where "time" is MJD (float64) and lon/lat are in degrees (float64).
                For ScheduleProject, returns a dictionary mapping observation codes to Polars DataFrames.

        Notes:
            - Uses CalculatedDataStructure to validate DataFrame structure and metadata.
            - Stores results under 'mollweide_tracks' key in each Observation's calculated_data.
            - Computes lon/lat coordinates in degrees from telescope positions.
            - Preserves NaN in lon/lat where position data is NaN.
        """
        try:
            time_step = attributes.get("time_step")
            if time_step is None or not isinstance(time_step, (int, float)):
                logger.error(f"Invalid time_step type '{type(time_step)}' for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}', must be float")
                return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks")) if isinstance(obj, Observation) else {}
            if time_step <= 0:
                logger.error(f"Invalid time_step {time_step} for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}', must be positive")
                return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks")) if isinstance(obj, Observation) else {}
            time_step = float(time_step)

            store_key = attributes.get("store_key", "mollweide_tracks")
            recalculate = attributes.get("recalculate", False)

            def calculate_mollweide(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, _, _ = self._get_active_components(obs, require_scans=True)
                if not scans:
                    logger.debug(f"No active scans in observation '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": recalculate}
                time_data = self._calculate_time_arrays(obs, time_attrs)
                position_data = self._calculate_telescope_positions(obs, position_attrs)

                if time_data.is_empty():
                    logger.error(f"No time data for '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))
                if position_data.is_empty():
                    logger.error(f"No position data for '{obs.get_observation_code()}'")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))

                mollweide_dfs = []  # Collect small DataFrames for concatenation

                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_mollweide_tracks, scan, obs, time_step, time_data, position_data): scan
                        for scan in scans
                    }
                    for future in futures:
                        scan_result = future.result()
                        if not scan_result.is_empty():
                            mollweide_dfs.append(scan_result)

                if mollweide_dfs:
                    result_df = pl.concat(mollweide_dfs, how="vertical")
                else:
                    logger.warning(f"No Mollweide tracks computed for observation '{obs.get_observation_code()}'")
                    result_df = pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))

                logger.info(f"Computed Mollweide tracks for {len(result_df['scan_name'].unique())} scans in '{obs.get_observation_code()}'")
                return result_df

            sources_metadata = {}
            for source in obj.get_sources().get_active_items():
                ra = source.ra_degrees
                dec = source.dec_degrees
                if ra is None or dec is None or np.isnan(ra) or np.isnan(dec):
                    logger.debug(f"Invalid coordinates (ra={ra}, dec={dec}) for source '{source.name}'; storing NaN in metadata")
                    sources_metadata[source.name] = tuple([np.nan, np.nan])
                else:
                    lon = float(ra - 360.0 if ra > 180.0 else ra)
                    lat = float(np.clip(dec, -90.0, 90.0))
                    sources_metadata[source.name] = tuple([lon, lat])

            converters = CalculatedDataStructure.get_converters("mollweide_tracks")
            if "sources" in converters:
                try:
                    sources_metadata = converters["sources"](sources_metadata)
                except Exception as e:
                    logger.error(f"Failed to apply converter to 'sources' metadata in '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {str(e)}")
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks")) if isinstance(obj, Observation) else {}

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()) if isinstance(obj, Observation) else sum(len(o.get_scans().get_active_items()) for o in obj.get_observations()),
                "sources": sources_metadata
            }
            logger.debug(f"Metadata for '{store_key}' in '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {metadata}")
            return self._process_object(obj, attributes, calculate_mollweide, store_key, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate Mollweide tracks for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {str(e)}")
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks")) if isinstance(obj, Observation) else {}

    def _process_mollweide_tracks(self, scan: Scan, observation: Observation, time_step: Optional[float], 
                                time_data: pl.DataFrame, position_data: pl.DataFrame) -> pl.DataFrame:
        """Process Mollweide tracks for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds).
            time_data (pl.DataFrame): Precomputed time arrays with columns ["time", "scan_name"], where "time" is MJD (float64).
            position_data (pl.DataFrame): Precomputed telescope positions with columns ["time", "scan_name", "telescope_code", "x", "y", "z"].

        Returns:
            pl.DataFrame: Mollweide tracks with columns ["time", "scan_name", "telescope_code", "lon", "lat"],
                where "time" is MJD (float64) and lon/lat are in degrees (float64).

        Notes:
            - Computes lon/lat coordinates in degrees from telescope positions.
            - Preserves NaN in lon/lat where position data is NaN.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_active_items() if t.isactive]

        if not active_telescopes:
            start_time_mjd = scan.get_start().mjd if scan.get_start() else None
            logger.warning(f"No active telescopes for scan '{scan_name}' at MJD {start_time_mjd}")
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))

        scan_times = time_data.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
        if len(scan_times) == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))

        n_times = len(scan_times)
        scan_positions = position_data.filter(pl.col("scan_name") == scan_name)
        if scan_positions.is_empty():
            logger.warning(f"No position data for scan '{scan_name}' in observation '{observation.get_observation_code()}'")
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))

        tel_codes = [tel.get_code() for tel in active_telescopes]

        # Batch filter positions for all telescope codes
        filtered_positions = scan_positions.filter(pl.col("telescope_code").is_in(tel_codes))

        positions = np.array([
            filtered_positions.filter(pl.col("telescope_code") == code)[["x", "y", "z"]].to_numpy()
            if code in filtered_positions["telescope_code"] else np.full((n_times, 3), np.nan)
            for code in tel_codes
        ], dtype=float)

        mollweide_dfs = []  # Collect small DataFrames for concatenation

        try:
            r = np.sqrt(np.sum(positions**2, axis=2))
            valid_mask = r > 0
            ra_rad = np.full_like(r, np.nan)
            dec_rad = np.full_like(r, np.nan)
            ra_rad[valid_mask] = np.arctan2(positions[valid_mask, 1], positions[valid_mask, 0])
            dec_rad[valid_mask] = np.arcsin(positions[valid_mask, 2] / r[valid_mask])
            ra = np.degrees(ra_rad)
            dec = np.degrees(dec_rad)
            lon = np.where(ra > 180.0, ra - 360.0, ra)
            lat = np.clip(dec, -90.0, 90.0)

            for i, tel_code in enumerate(tel_codes):
                valid_points = np.sum(~np.isnan(lon[i]) & ~np.isnan(lat[i]))
                if valid_points > 0:
                    mollweide_dfs.append(pl.DataFrame({
                        "time": scan_times,
                        "scan_name": [scan_name] * n_times,
                        "telescope_code": [tel_code] * n_times,
                        "lon": lon[i],
                        "lat": lat[i]
                    }, schema=CalculatedDataStructure.get_dtypes("mollweide_tracks")))
                    logger.debug(f"Computed {valid_points} valid Mollweide coordinates for telescope '{tel_code}' in scan '{scan_name}'")

            if mollweide_dfs:
                result_df = pl.concat(mollweide_dfs, how="vertical")
            else:
                logger.warning(f"No Mollweide tracks computed for scan '{scan_name}'")
                result_df = pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))

            return result_df

        except Exception as e:
            logger.error(f"Failed to compute Mollweide tracks for scan '{scan_name}' at MJD {scan_times[0] if len(scan_times) > 0 else None}: {str(e)}")
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))