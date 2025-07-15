from abc import ABC
from common.super.super import Super
from common.utils.logging_setup import logger

from pastrocore.base.frequencies import Frequencies, IF
from pastrocore.base.sources import Sources, Source
from pastrocore.base.telescopes import Telescope, SpaceTelescope, Telescopes
from pastrocore.base.scans import Scan
from pastrocore.base.observation import Observation
from pastrocore.super.schedule_project import ScheduleProject

from typing import Dict, Any, Optional, Tuple, List
from concurrent.futures import ThreadPoolExecutor
from scipy.special import j1
from scipy.fft import fft2, fftshift
from functools import wraps

import astropy.units as u
from astropy.time import Time
from astropy.coordinates import ITRS, GCRS, CartesianRepresentation, SkyCoord, AltAz, get_sun, HADec

import numpy as np

import threading
import math
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

    Examples:
        >>> from unit_scheduling.super.manipulator import ScheduleManipulator
        >>> manipulator = ScheduleManipulator()
        >>> calculator = ScheduleCalculator(manipulator)
        >>> obs = Observation()
        >>> result = calculator.calculate(obs, {"store_key": "uv_coverage_f0", "freq_name": 0})
        >>> print(result)
        {'0': {'uv_points': {...}}}
    """
    def __init__(self, manipulator: 'Manipulator'):
        """Initialize the ScheduleCalculator.

        Args:
            manipulator: The Manipulator instance providing method validation and execution capabilities.
        """
        super().__init__(manipulator)
        self._lock = threading.Lock()
        self._orbit_cache = {}  # Temporary storage for orbit data: {telescope_code: orbit_data}
        self._orbit_cache_lock = threading.Lock()  # Lock for orbit cache
        logger.info("Initialized Scheduling Calculator")

    def _default_result(self) -> Dict[str, Any]:
        """Return the default result when calculation is not applied.

        Returns:
            Dict[str, Any]: An empty dictionary.
        """
        return {}
    
    def _get_cached_or_calculate(self, obj: Observation | ScheduleProject, store_key: str, calc_func, attributes: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve cached data or perform calculation and cache the result.

        Args:
            obj (Observation | ScheduleProject): The object (Observation or Project) to calculate for.
            store_key (str): Unique key for storing/retrieving calculated data.
            calc_func: The calculation function to execute if no valid cache exists.
            attributes (Dict[str, Any]): Calculation parameters (e.g., "recalculate", "time_step").
            metadata (Dict[str, Any]): Metadata to store with the result (e.g., time step, scan count).

        Returns:
            Dict[str, Any]: Calculated or cached data.

        Notes:
            - If "recalculate" is False and valid cached data exists, returns cached result.
            - Uses thread-safe caching with a lock.
        """
        recalculate = attributes.get("recalculate", False)
        time_step = attributes.get("time_step")

        existing_data = obj.get_calculated_data_by_key(store_key)
        if existing_data and not recalculate and existing_data["metadata"].get("time_step") == time_step:
            if existing_data["data"]:
                logger.info(f"Using cached data for '{store_key}' in '{obj.get_observation_code()}'")
                return existing_data["data"]
            else:
                logger.warning(f"Cached data for '{store_key}' in '{obj.get_observation_code()}' is empty, forcing recalculation")

        logger.info(f"Recalculating '{store_key}' for '{obj.get_observation_code()}' with recalculate={recalculate}")
        result = calc_func(obj, attributes)
        if not result:
            logger.error(f"Calculation for '{store_key}' returned empty result")
        with self._lock:
            obj.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": result})
        return result
    
    @time_execution
    def _calculate_time_arrays(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate time arrays for active scans grouped by active sources with a configurable time threshold.

        Args:
            obj (Observation | ScheduleProject): The object to calculate time arrays for.
            attributes (Dict[str, Any]): Parameters including "time_step", "time_threshold", "start_time", "end_time".

        Returns:
            Dict[str, Any]: Time arrays per source and scan, formatted as {source_name: {scan_name: astropy.time.Time}}.

        Notes:
            - Stores results in calculated_data under "times" as astropy.time.Time objects with scale='utc'.
            - Uses time_step for sampling; if None, uses a single midpoint time per scan.
            - Applies a time threshold (default 1 second) for rounding start_time and duration.
            - Metadata includes time_step, threshold, start_time, end_time, and scan_count for cache validation.
            - Considers only active scans and active sources.
        """
        try:
            time_step = attributes.get("time_step")
            time_threshold = attributes.get("time_threshold", 1.0)  # Default 1-second threshold
            store_key = attributes.get("store_key", "times")
            
            if time_step is not None and time_step <= 0:
                logger.error(f"Invalid time_step: {time_step}. Must be positive.")
                return {}
            if time_threshold <= 0:
                logger.error(f"Invalid time_threshold: {time_threshold}. Must be positive.")
                return {}

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {}
                results = {}
                max_workers = min(len(observations), 4) if len(observations) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._calculate_time_arrays, obs, attributes): obs.get_observation_code()
                        for obs in observations
                    }
                    for future in futures:
                        obs_code = futures[future]
                        results[obs_code] = future.result()
                logger.info(f"Calculated time arrays for {len(observations)} observations in project '{obj.name}'")
                return results

            def calculate_times(obj: Observation, attrs: Dict[str, Any]) -> Dict[str, Any]:
                scans = obj.get_scans().get_active_items()
                if not scans:
                    logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
                    return {}
                results = {}
                start_times = []
                end_times = []
                processed_scans = 0
                for scan in scans:
                    source = scan.get_source(obj)
                    if source is None:
                        logger.warning(f"No source for scan '{scan.name}' in observation '{obj.get_observation_code()}'; skipping")
                        continue
                    if not source.isactive:
                        logger.debug(f"Skipping scan '{scan.name}' due to inactive source '{source.name}'")
                        continue
                    source_name = source.name
                    if source_name not in results:
                        results[source_name] = {}
                    start_time = scan.get_start()
                    duration = scan.get_duration()
                    scan_name = scan.name
                    
                    # Apply threshold rounding
                    start_mjd_rounded = round(start_time.mjd * 86400.0 / time_threshold) * time_threshold / 86400.0
                    duration_rounded = round(duration / time_threshold) * time_threshold
                    start_time_rounded = Time(start_mjd_rounded, format='mjd', scale='utc')
                    
                    # Calculate times as astropy.time.Time with scale='utc'
                    if time_step is None:
                        times = Time(start_time_rounded.mjd + (duration_rounded / 2) / 86400.0, format='mjd', scale='utc')
                    else:
                        time_values = np.arange(0, duration_rounded, time_step) * u.s
                        times = Time(start_time_rounded.mjd + time_values.to(u.d).value, format='mjd', scale='utc')
                    
                    if times.size == 0:
                        logger.warning(f"Empty time array for scan '{scan_name}'")
                        times = Time([], format='mjd', scale='utc')
                    
                    results[source_name][scan_name] = times
                    start_times.append(start_time_rounded.mjd)
                    end_times.append((start_time_rounded + duration_rounded * u.s).mjd)
                    processed_scans += 1
                
                logger.info(f"Calculated time arrays for {processed_scans} scans across {len(results)} active sources in observation '{obj.get_observation_code()}'")
                return results

            # prepare metadata for cache validation
            scans = obj.get_scans().get_active_items() if isinstance(obj, Observation) else []
            start_times = [scan.get_start().mjd for scan in scans if scan.get_source(obj) and scan.get_source(obj).isactive] if scans else []
            end_times = [(scan.get_start() + scan.get_duration() * u.s).mjd for scan in scans if scan.get_source(obj) and scan.get_source(obj).isactive] if scans else []
            metadata = {
                "time_step": time_step,
                "time_threshold": time_threshold,
                "start_time": min(start_times) if start_times else np.nan,
                "end_time": max(end_times) if end_times else np.nan,
                "scan_count": len(start_times)
            }
            return self._get_cached_or_calculate(obj, store_key, calculate_times, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate time arrays: {str(e)}")
            return {}
        
    @time_execution
    def _calculate_telescope_positions(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate telescope positions in GCRS (J2000) for all active scans using times from time_arrays and interpolated orbits.

        Args:
            obj (Observation | ScheduleProject): The object to calculate positions for.
            attributes (Dict[str, Any]): Parameters including "time_step", "store_key", "recalculate".

        Returns:
            Dict[str, Any]: Telescope positions per scan, formatted as {scan_name: {telescope_code: np.array([[x, y, z], ...])}}.

        Notes:
            - Uses precomputed orbits from 'interpolated_orbits' for SpaceTelescopes.
            - Positions are stored as numpy arrays in meters.
            - Excludes telescopes with unavailable orbit data for SpaceTelescopes.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "telescope_positions")
            recalculate = attributes.get("recalculate", False)
            excluded_telescopes = []

            def calculate_positions(obj, attrs):
                if isinstance(obj, ScheduleProject):
                    observations = obj.get_items()
                    if not observations:
                        logger.warning(f"No observations in project '{obj.name}'")
                        return {}
                    results = {}
                    max_workers = min(len(observations), 4) if len(observations) > 1 else 1
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        futures = {
                            executor.submit(self._calculate_telescope_positions, obs, attrs): obs.get_observation_code()
                            for obs in observations
                        }
                        for future in futures:
                            obs_code = futures[future]
                            results[obs_code] = future.result()
                        logger.info(f"Calculated telescope positions for {len(observations)} observations in project '{obj.name}'")
                    return results

                # Get time arrays
                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                time_data = self._calculate_time_arrays(obj, time_attrs)
                if not time_data:
                    logger.warning(f"No time arrays available for observation '{obj.get_observation_code()}'")
                    return {}

                scans = obj.get_scans().get_active_items()
                if not scans:
                    logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
                    return {}

                # Get interpolated orbits
                orbit_attrs = {"time_step": time_step, "store_key": "interpolated_orbits", "recalculate": recalculate}
                orbit_data = self._calculate_interpolated_orbits(obj, orbit_attrs)
                if not orbit_data:
                    logger.info(f"No interpolated orbit data for observation '{obj.get_observation_code()}'")

                # Process each scan
                results = {}
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_scan_positions, scan, obj, time_step, time_data, orbit_data): scan
                        for scan in scans
                    }
                    for future in futures:
                        scan = futures[future]
                        scan_name = scan.name
                        results[scan_name] = future.result()
                        if not results[scan_name]:
                            excluded_telescopes.extend([tel.get_code() for tel in scan.get_telescopes(obj).get_active_items()])

                if excluded_telescopes:
                    logger.info(f"Excluded {len(set(excluded_telescopes))} telescopes: {', '.join(set(excluded_telescopes))}")
                logger.debug(f"Calculated telescope positions for {len(results)} scans in '{obj.get_observation_code()}'")
                return results

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items())}
            return self._get_cached_or_calculate(obj, store_key, calculate_positions, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate telescope positions for observation '{obj.get_observation_code()}': {str(e)}")
            return {}
        
    def _process_scan_positions(self, scan: Scan, observation: Observation, time_step: Optional[float], time_data: Dict[str, Any], orbit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process telescope positions for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds).
            time_data (Dict[str, Any]): Precomputed time arrays from _calculate_time_arrays.
            orbit_data (Dict[str, Any]): Precomputed orbit data as {scan_name: {spacetelescope_code: np.array([[x, y, z], ...])}}.

        Returns:
            Dict[str, Any]: Positions for active telescopes, formatted as {telescope_code: np.array([[x, y, z], ...])}.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return {}

        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [tel for tel in scan_telescopes.get_items() if tel.isactive]
        scan_name = scan.name
        source_name = source.name

        if not active_telescopes:
            logger.warning(f"No active telescopes for scan '{scan_name}' starting at {scan.get_start().isot}")
            return {}

        # Get times for the scan from time_data
        scan_times = time_data.get(source_name, {}).get(scan_name, None)
        if scan_times is None or not isinstance(scan_times, Time) or scan_times.size == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return {}

        positions = {}
        # Separate telescopes into ground and space (Keplerian and orbit-based)
        ground_tels = [tel for tel in active_telescopes if not isinstance(tel, SpaceTelescope)]
        kep_space_tels = [tel for tel in active_telescopes if isinstance(tel, SpaceTelescope) and tel.get("use_kep")]
        orbit_space_tels = [tel for tel in active_telescopes if isinstance(tel, SpaceTelescope) and not tel.get("use_kep")]

        # Process ground telescopes
        if ground_tels:
            x = np.array([tel.get_coordinates()[0] for tel in ground_tels])
            y = np.array([tel.get_coordinates()[1] for tel in ground_tels])
            z = np.array([tel.get_coordinates()[2] for tel in ground_tels])
            vx = np.array([tel.get(["vx", "vy", "vz"])["vx"] for tel in ground_tels])
            vy = np.array([tel.get(["vx", "vy", "vz"])["vy"] for tel in ground_tels])
            vz = np.array([tel.get(["vx", "vy", "vz"])["vz"] for tel in ground_tels])
            dt = (scan_times - Time("2000-01-01T12:00:00")).sec
            itrs_coords = CartesianRepresentation(
                x[:, None] + vx[:, None] * dt,
                y[:, None] + vy[:, None] * dt,
                z[:, None] + vz[:, None] * dt,
                unit=u.m
            )
            itrs = ITRS(itrs_coords, obstime=scan_times)
            gcrs = itrs.transform_to(GCRS(obstime=scan_times))
            ground_positions = np.stack([gcrs.cartesian.x.value, gcrs.cartesian.y.value, gcrs.cartesian.z.value], axis=-1)  # shape: (n_tels, n_times, 3)
            for i, tel in enumerate(ground_tels):
                tel_code = tel.get_code()
                if not np.all(np.isnan(ground_positions[i])):
                    positions[tel_code] = ground_positions[i]
                else:
                    logger.warning(f"All positions are NaN for ground telescope '{tel_code}' in scan '{scan_name}'")

        # Process Keplerian space telescopes
        if kep_space_tels:
            for tel in kep_space_tels:
                tel_code = tel.get_code()
                try:
                    pos_array = self._compute_telescope_position(tel, scan_times)
                    if not np.all(np.isnan(pos_array)):
                        positions[tel_code] = pos_array
                    else:
                        logger.warning(f"All positions are NaN for Keplerian telescope '{tel_code}' in scan '{scan_name}'")
                except ValueError as e:
                    logger.warning(f"Position calculation failed for Keplerian telescope '{tel_code}' in scan '{scan_name}': {str(e)}")

        # Process orbit-based space telescopes
        scan_orbit_data = orbit_data.get(scan_name, {})
        for tel in orbit_space_tels:
            tel_code = tel.get_code()
            orbit_positions = scan_orbit_data.get(tel_code, np.array([]))
            if orbit_positions.size > 0 and orbit_positions.shape[0] == len(scan_times):
                positions[tel_code] = orbit_positions
            else:
                logger.warning(f"No or mismatched orbit data for telescope '{tel_code}' in scan '{scan_name}'")

        if not positions:
            logger.warning(f"No valid positions computed for scan '{scan_name}'")
        return positions

    def _compute_telescope_position(self, telescope: Telescope | SpaceTelescope, time: Time) -> np.ndarray:
        """Compute a telescope's GCRS position at specified times.

        Args:
            telescope (Telescope | SpaceTelescope): The telescope to compute position for.
            time (Time): Single time or array of times for calculation.

        Returns:
            np.ndarray: GCRS coordinates (x, y, z) in meters, shape (n_times, 3) for array input
                        or (3,) for single time. Returns NaN array if computation fails.

        Notes:
            - For ground telescopes, applies velocity corrections and transforms ITRS to GCRS.
            - For SpaceTelescopes with use_kep=True, computes positions using Keplerian elements.
            - For SpaceTelescopes with use_kep=False, returns NaN (positions should be precomputed).
        """
        try:
            # Ensure time is iterable
            single_time = not isinstance(time, Time) or time.isscalar
            times = time if not single_time else Time([time])
            n_times = len(times)
            nan_result = np.full((3,) if single_time else (n_times, 3), np.nan, dtype=float)

            if isinstance(telescope, Telescope) and not isinstance(telescope, SpaceTelescope):
                # Ground telescope: vectorized computation
                x, y, z = telescope.get_coordinates()
                res = telescope.get(["vx", "vy", "vz"])
                vx, vy, vz = res["vx"], res["vy"], res["vz"]
                dt = (times - Time("2000-01-01T12:00:00")).sec
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
                return pos[0] if single_time else pos

            elif isinstance(telescope, SpaceTelescope):
                if telescope.get("use_kep"):
                    # Keplerian space telescope: vectorized computation
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
                    epoch = kepler["epoch"]
                    mu = kepler["mu"]  # gravitational parameter (m^3/s^2)

                    # Mean motion
                    n = np.sqrt(mu / a**3)  # rad/s
                    # Time since epoch
                    dt = (times - epoch).sec
                    # Mean anomaly
                    M = nu0 + n * dt
                    # Solve Kepler's equation for eccentric anomaly
                    solve_kepler_vec = np.vectorize(self._solve_kepler)
                    E = solve_kepler_vec(M, e)
                    # True anomaly
                    cos_nu = (np.cos(E) - e) / (1 - e * np.cos(E))
                    sin_nu = (np.sqrt(1 - e**2) * np.sin(E)) / (1 - e * np.cos(E))
                    nu = np.arctan2(sin_nu, cos_nu)
                    # Distance
                    r = a * (1 - e**2) / (1 + e * np.cos(nu))
                    # Position in orbital plane
                    p = np.array([r * np.cos(nu), r * np.sin(nu), np.zeros_like(r)]).T
                    # Rotation matrices
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
                    # Transform to GCRS
                    pos = np.array([R @ p_i for p_i in p]) if not single_time else (R @ p[0])
                    if np.any(np.isnan(pos)):
                        logger.warning(f"Keplerian position for '{telescope.get_code()}' at {times[0].isot} contains NaN")
                    return pos[0] if single_time else pos
                else:
                    # Orbit file-based space telescope: positions should be precomputed
                    logger.warning(f"Orbit file position for '{telescope.get_code()}' at {times[0].isot} should be precomputed in interpolated_orbits")
                    return nan_result

            raise ValueError(f"Unsupported telescope type: {type(telescope)}")
        except Exception as e:
            logger.warning(f"Unexpected error in computing position for '{telescope.get_code()}' at {times[0].isot}: {str(e)}")
            return np.full((3,) if single_time else (n_times, 3), np.nan, dtype=float)

    @time_execution
    def _calculate_source_visibility(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate source visibility for all active scans in the observation or project.

        Args:
            obj (Observation | ScheduleProject): The object to calculate visibility for.
            attributes (Dict[str, Any]): Parameters including "time_step", "store_key", "position_store_key", "recalculate".

        Returns:
            Dict[str, Any]: Visibility data per source and scan, formatted as:
                {source_name: {scan_name: {telescope_code: [True/False, ...]}}}

        Notes:
            - Depends on precomputed telescope positions and time arrays.
            - Uses parallel processing for multiple scans.
            - Stores results in calculated_data under the specified store_key.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "source_visibility")
            position_store_key = attributes.get("position_store_key", "telescope_positions")
            recalculate = attributes.get("recalculate", False)

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {}
                results = {}
                max_workers = min(len(observations), 4) if len(observations) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._calculate_source_visibility, obs, attributes): obs.get_observation_code()
                        for obs in observations
                    }
                    for future in futures:
                        obs_code = futures[future]
                        results[obs_code] = future.result()
                logger.info(f"Calculated source visibility for {len(observations)} observations in project '{obj.name}'")
                return results

            def calculate_visibility(obj, attrs):
                scans = obj.get_scans().get_active_items()
                if not scans:
                    logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
                    return {}
                
                # Get time arrays
                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                time_data = self._calculate_time_arrays(obj, time_attrs)
                if not time_data:
                    logger.error(f"No time arrays available for observation '{obj.get_observation_code()}'")
                    return {}

                # Get telescope positions
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": recalculate}
                position_data = self._calculate_telescope_positions(obj, position_attrs)
                if not position_data:
                    logger.error(f"No telescope positions available for observation '{obj.get_observation_code()}'")
                    return {}

                results = {}
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_source_visibility, scan, obj, time_step, time_data, position_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        source_name = scan_result.get("source")
                        if source_name and scan_result.get("visibility"):
                            if source_name not in results:
                                results[source_name] = {}
                            results[source_name][scan_name] = scan_result["visibility"]
                return results

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()),
                "position_store_key": position_store_key
            }
            return self._get_cached_or_calculate(obj, store_key, calculate_visibility, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate source visibility: {str(e)}")
            return {}

    def _process_source_visibility(self, scan: Scan, observation: Observation, time_step: Optional[float], time_data: Dict[str, Any], position_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process source visibility for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds). If None, uses mean time.
            time_data (Dict[str, Any]): Precomputed time arrays from _calculate_time_arrays.
            position_data (Dict[str, Any]): Precomputed telescope positions.

        Returns:
            Dict[str, Any]: Visibility data for the scan, formatted as:
                {
                    "source": source_name,
                    "visibility": {telescope_code: [True/False, ...]}
                }
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return {"source": None, "visibility": {}}

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        if not active_telescopes:
            logger.warning(f"No active telescopes for scan '{scan_name}' in observation '{observation.get_observation_code()}'")
            return {"source": source_name, "visibility": {}}

        # Get times for the scan
        scan_times = time_data.get(source_name, {}).get(scan_name, None)
        if scan_times is None or not isinstance(scan_times, Time) or scan_times.size == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return {"source": source_name, "visibility": {}}

        # Get telescope positions for the scan
        scan_positions = position_data.get(scan_name, {})
        if not scan_positions:
            logger.warning(f"No position data for scan '{scan_name}' in observation '{observation.get_observation_code()}'")
            return {"source": source_name, "visibility": {}}

        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
        visibility = {}

        # Separate telescopes by type
        ground_tels = [tel for tel in active_telescopes if not isinstance(tel, SpaceTelescope)]
        space_tels = [tel for tel in active_telescopes if isinstance(tel, SpaceTelescope)]

        # Process ground telescopes (AZIM and EQUA mounts)
        if ground_tels:
            # Prepare arrays for ground telescopes
            ground_codes = [tel.get_code() for tel in ground_tels]
            ground_positions = np.array([scan_positions.get(code, np.full((len(scan_times), 3), np.nan)) for code in ground_codes])  # shape: (n_tels, n_times, 3)
            mount_types = [tel.get("mount_type").value for tel in ground_tels]
            
            # Process AZIM mounts
            azim_tels = [tel for tel, mt in zip(ground_tels, mount_types) if mt == "AZIM"]
            if azim_tels:
                azim_codes = [tel.get_code() for tel in azim_tels]
                azim_indices = [i for i, mt in enumerate(mount_types) if mt == "AZIM"]
                azim_positions = ground_positions[azim_indices]  # shape: (n_azim_tels, n_times, 3)
                
                # Vectorized coordinate transformation for AZIM
                gcrs_coords = CartesianRepresentation(
                    x=azim_positions[:, :, 0] * u.m,
                    y=azim_positions[:, :, 1] * u.m,
                    z=azim_positions[:, :, 2] * u.m
                )
                gcrs = GCRS(gcrs_coords, obstime=scan_times)
                itrs = gcrs.transform_to(ITRS(obstime=scan_times))
                locations = itrs.earth_location
                altaz = source_coord.transform_to(AltAz(obstime=scan_times, location=locations))
                el = altaz.alt.deg  # shape: (n_tels, n_times)
                az = altaz.az.deg   # shape: (n_tels, n_times)
                
                # Check visibility for AZIM mounts
                for i, tel in enumerate(azim_tels):
                    el_range = tel.get_elevation_range()
                    az_range = tel.get_azimuth_range()
                    is_visible = (float(el_range[0]) <= el[i]) & (el[i] <= float(el_range[1])) & \
                                (float(az_range[0]) <= az[i]) & (az[i] <= float(az_range[1]))
                    visibility[tel.get_code()] = is_visible.tolist()
            
            # Process EQUA mounts
            equa_tels = [tel for tel, mt in zip(ground_tels, mount_types) if mt == "EQUA"]
            if equa_tels:
                equa_codes = [tel.get_code() for tel in equa_tels]
                equa_indices = [i for i, mt in enumerate(mount_types) if mt == "EQUA"]
                equa_positions = ground_positions[equa_indices]  # shape: (n_equa_tels, n_times, 3)
                
                # Vectorized coordinate transformation for EQUA
                gcrs_coords = CartesianRepresentation(
                    x=equa_positions[:, :, 0] * u.m,
                    y=equa_positions[:, :, 1] * u.m,
                    z=equa_positions[:, :, 2] * u.m
                )
                gcrs = GCRS(gcrs_coords, obstime=scan_times)
                itrs = gcrs.transform_to(ITRS(obstime=scan_times))
                locations = itrs.earth_location
                hadec = source_coord.transform_to(HADec(obstime=scan_times, location=locations))
                ha = hadec.ha.deg   # shape: (n_tels, n_times)
                dec = hadec.dec.deg # shape: (n_tels, n_times)
                
                # Check visibility for EQUA mounts
                for i, tel in enumerate(equa_tels):
                    ha_range = tel.get_azimuth_range()
                    dec_range = tel.get_elevation_range()
                    is_visible = (float(dec_range[0]) <= dec[i]) & (dec[i] <= float(dec_range[1])) & \
                                (float(ha_range[0]) <= ha[i]) & (ha[i] <= float(ha_range[1]))
                    visibility[tel.get_code()] = is_visible.tolist()
            
            # Handle unsupported mount types
            for tel in ground_tels:
                if tel.get("mount_type").value not in ["AZIM", "EQUA"]:
                    logger.warning(f"Unsupported mount type {tel.get('mount_type').value} for telescope '{tel.get_code()}'")
                    visibility[tel.get_code()] = [False] * len(scan_times)

        # Process space telescopes (temporary placeholder: always visible)
        if space_tels:
            for tel in space_tels:
                tel_code = tel.get_code()
                visibility[tel_code] = [True] * len(scan_times)  # Placeholder: assume always visible
                logger.debug(f"Space telescope '{tel_code}' in scan '{scan_name}' assumed always visible (placeholder)")

        return {"source": source_name, "visibility": visibility}  

    def _compute_visibility_at_time(self, source: Source, telescopes: List[Telescope | SpaceTelescope], time: Time, positions: Dict[str, Tuple[float, float, float]]) -> Dict[str, bool]:
        """Compute visibility of a source for telescopes at a given time using precomputed positions.

        Args:
            source (Source): The source to check visibility for.
            telescopes (List[Telescope | SpaceTelescope]): List of telescopes.
            time (Time): The time of observation.
            positions (Dict[str, Tuple[float, float, float]]): Precomputed GCRS positions.

        Returns:
            Dict[str, bool]: Visibility status per telescope code.
        """
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
        visibility = {}
        for tel in telescopes:
            pos = positions.get(tel.get_code())
            if pos is None:
                logger.debug(f"No position data for telescope '{tel.get_code()}' at {time.isot}")
                visibility[tel.get_code()] = False
                continue
            if isinstance(tel, SpaceTelescope):
                itrs = ITRS(CartesianRepresentation(*pos, unit=u.m), obstime=time)
                altaz = source_coord.transform_to(AltAz(obstime=time, location=itrs.earth_location))
                pitch = altaz.alt.deg
                yaw = altaz.az.deg
                pitch_range = tel.get_pitch_range()
                yaw_range = tel.get_yaw_range()
                is_visible = (pitch_range[0] <= pitch <= pitch_range[1]) and (yaw_range[0] <= yaw <= yaw_range[1])
            else:
                gcrs = GCRS(CartesianRepresentation(*pos, unit=u.m), obstime=time)
                itrs = gcrs.transform_to(ITRS(obstime=time))
                location = itrs.earth_location
                altaz = source_coord.transform_to(AltAz(obstime=time, location=location))
                el = altaz.alt.deg
                az = altaz.az.deg
                hadec = source_coord.transform_to(HADec(obstime=time, location=location))
                ha = hadec.ha.deg
                mount_type = tel.get("mount_type")
                if mount_type.value == "AZIM":
                    el_range = tel.get_elevation_range()
                    az_range = tel.get_azimuth_range()
                    is_visible = (el_range[0] <= el <= el_range[1]) and (az_range[0] <= az <= az_range[1])
                elif mount_type.value == "EQUA":
                    dec = hadec.dec.deg
                    ha_range = tel.get_azimuth_range()
                    dec_range = tel.get_elevation_range()
                    is_visible = (dec_range[0] <= dec <= dec_range[1]) and (ha_range[0] <= ha <= ha_range[1])
                else:
                    logger.debug(f"Unsupported mount type {mount_type.value} for telescope '{tel.get_code()}'")
                    is_visible = False
            visibility[tel.get_code()] = is_visible
        return visibility
    
    @time_execution
    def _calculate_uv_coverage(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate (u,v,w) coverage for all scans in the observation or project in geometric coordinates (meters).

        Args:
            obj (Observation | ScheduleProject): The object to calculate UV coverage for.
            attributes (Dict[str, Any]): Parameters including "time_step", "store_key", and "recalculate".

        Returns:
            Dict[str, Any]: UV coverage data per source and scan, formatted as:
                {source_name: {scan_name: {baseline: [[u, v, w], ...]}}}

        Notes:
            - Calculates UV coordinates in meters without frequency scaling.
            - Uses precomputed visibility and telescope positions from calculated_data.
            - Invokes _calculate_source_visibility and _calculate_telescope_positions if data is missing.
            - The 'freq_name' attribute, if provided, is ignored and logged for compatibility.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "uv_coverage")
            recalculate = attributes.get("recalculate", False)

            if "freq_name" in attributes:
                logger.info(f"Ignoring 'freq_name' attribute for UV coverage calculation in geometric coordinates")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {}
                results = {}
                max_workers = min(len(observations), 4) if len(observations) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._calculate_uv_coverage, obs, attributes): obs.get_observation_code()
                        for obs in observations
                    }
                    for future in futures:
                        obs_code = futures[future]
                        results[obs_code] = future.result()
                logger.info(f"Calculated (u,v,w) coverage for {len(observations)} observations in project '{obj.name}'")
                return results

            def calculate_uv(obj, attrs):
                scans = obj.get_scans().get_active_items()
                if not scans:
                    logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
                    return {}

                # Retrieve or calculate dependencies
                visibility_attrs = {"time_step": time_step, "store_key": "source_visibility", "recalculate": recalculate}
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": recalculate}
                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}

                time_data = self._calculate_time_arrays(obj, time_attrs)
                visibility_data = self._calculate_source_visibility(obj, visibility_attrs)
                position_data = self._calculate_telescope_positions(obj, position_attrs)

                if not (time_data and visibility_data and position_data):
                    logger.error(f"Missing required data (times, visibility, or positions) for '{obj.get_observation_code()}'")
                    return {}

                results = {}
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_uv_coverage, scan, obj, time_step, time_data, visibility_data, position_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        source_name = scan_result.get("source")
                        if source_name and scan_result.get("uv_points"):
                            if source_name not in results:
                                results[source_name] = {}
                            results[source_name][scan_name] = scan_result["uv_points"]
                if not results:
                    logger.warning(f"No UV coverage data computed for observation '{obj.get_observation_code()}'")
                return results

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items())}
            return self._get_cached_or_calculate(obj, store_key, calculate_uv, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate (u,v,w) coverage: {str(e)}")
            return {}

    def _process_uv_coverage(self, scan: Scan, observation: Observation, time_step: Optional[float], time_data: Dict[str, Any], visibility_data: Dict[str, Any], position_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process UV coverage for a single scan using vectorized computations in geometric coordinates (meters).

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds).
            time_data (Dict[str, Any]): Precomputed time arrays from _calculate_time_arrays.
            visibility_data (Dict[str, Any]): Precomputed visibility data.
            position_data (Dict[str, Any]): Precomputed position data.

        Returns:
            Dict[str, Any]: UV points in meters, formatted as:
                {"source": source_name, "uv_points": {baseline: [[u,v,w], ...]}}.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return {"source": None, "uv_points": {}}

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]

        if len(active_telescopes) < 2:
            logger.warning(f"Insufficient telescopes ({len(active_telescopes)}) for UV coverage in scan '{scan_name}'")
            return {"source": source_name, "uv_points": {}}

        # Get times for the scan
        scan_times = time_data.get(source_name, {}).get(scan_name, None)
        if scan_times is None or not isinstance(scan_times, Time) or scan_times.size == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return {"source": source_name, "uv_points": {}}

        # Get visibility and position data
        scan_visibility = visibility_data.get(source_name, {}).get(scan_name, {})
        scan_positions = position_data.get(scan_name, {})
        if not (scan_visibility and scan_positions):
            logger.warning(f"No visibility or position data for scan '{scan_name}' in observation '{observation.get_observation_code()}'")
            return {"source": source_name, "uv_points": {}}

        # Prepare arrays
        tel_codes = [tel.get_code() for tel in active_telescopes]
        visibility = np.array([scan_visibility.get(code, [False] * len(scan_times)) for code in tel_codes], dtype=bool)  # shape: (n_tels, n_times)
        positions = np.array([scan_positions.get(code, np.full((len(scan_times), 3), np.nan)) for code in tel_codes])  # shape: (n_tels, n_times, 3)

        if positions.shape[1] != len(scan_times):
            logger.warning(f"Mismatched position data length for scan '{scan_name}': {positions.shape[1]} positions vs {len(scan_times)} times")
            return {"source": source_name, "uv_points": {}}

        uv_points = self._compute_uv_at_time(active_telescopes, scan_times, source, visibility, positions)

        # Check for sufficient valid UV points
        valid_point_count = sum(len(points) for points in uv_points.values())
        min_points = len(active_telescopes) * (len(active_telescopes) - 1) // 2  # Minimum one point per possible baseline
        if valid_point_count < min_points:
            logger.warning(f"Insufficient valid UV points ({valid_point_count} < {min_points}) for scan '{scan_name}'")
            return {"source": source_name, "uv_points": {}}

        logger.debug(f"Computed {valid_point_count} UV points for scan '{scan_name}' across {len(uv_points)} baselines")
        return {"source": source_name, "uv_points": uv_points}

    def _compute_uv_at_time(self, telescopes: List[Telescope | SpaceTelescope], times: Time, source: Optional[Source] = None, visibility: Optional[np.ndarray] = None, gcrs_positions: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
        """Compute UVW coordinates for multiple times in geometric coordinates (meters) using vectorized operations.

        Args:
            telescopes (List[Telescope | SpaceTelescope]): List of telescopes.
            times (Time): Array of observation times.
            source (Optional[Source]): Source for UV calculation.
            visibility (Optional[np.ndarray]): Visibility array of shape (n_telescopes, n_times).
            gcrs_positions (Optional[np.ndarray]): GCRS positions of shape (n_telescopes, n_times, 3).

        Returns:
            Dict[str, np.ndarray]: UVW coordinates in meters per baseline, formatted as {baseline: np.array([[u,v,w], ...])}.
        """
        if not telescopes or len(telescopes) < 2:
            logger.warning(f"Insufficient telescopes ({len(telescopes)}) to compute (u,v,w) at {times[0].isot}")
            return {}

        if source is None:
            logger.warning("No source provided; cannot calculate (u,v,w)")
            return {}

        # Prepare source coordinates
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
        ra = source_coord.ra.rad
        dec = source_coord.dec.rad

        # Compute positions if not provided
        if gcrs_positions is None:
            gcrs_positions = np.array([self._compute_telescope_position(tel, times) for tel in telescopes])  # shape: (n_tels, n_times, 3)

        # Compute visibility if not provided
        if visibility is None:
            positions_dict = {tel.get_code(): pos for tel, pos in zip(telescopes, gcrs_positions[:, 0, :])}
            visibility = np.array([self._compute_visibility_at_time(source, telescopes, times[0], positions_dict)[tel.get_code()] for tel in telescopes])
            visibility = np.repeat(visibility[:, None], len(times), axis=1)  # shape: (n_tels, n_times)

        n_tels = len(telescopes)
        n_times = len(times)

        # Create indices for upper triangle to get unique baseline pairs
        i, j = np.triu_indices(n_tels, k=1)  # Indices for upper triangle (i < j)
        pairs = [f"{telescopes[i].get_code()}-{telescopes[j].get_code()}" for i, j in zip(i, j)]
        n_pairs = len(pairs)

        # Compute baselines: shape (n_pairs, n_times, 3)
        baselines = gcrs_positions[i] - gcrs_positions[j]  # shape: (n_pairs, n_times, 3)

        # Compute visibility mask for baselines
        vis_mask = visibility[i] & visibility[j]  # shape: (n_pairs, n_times)

        # Compute UVW coordinates using rotation matrix
        # Rotation matrix from GCRS to UVW coordinates based on source RA and Dec
        cos_ra, sin_ra = np.cos(ra), np.sin(ra)
        cos_dec, sin_dec = np.cos(dec), np.sin(dec)
        rotation_matrix = np.array([
            [-sin_ra, cos_ra, 0],
            [-cos_ra * sin_dec, -sin_ra * sin_dec, cos_dec],
            [cos_ra * cos_dec, sin_ra * cos_dec, sin_dec]
        ])  # shape: (3, 3)

        # Apply rotation to baselines: uvw = rotation_matrix @ baselines
        # Reshape baselines to (n_pairs * n_times, 3) for matrix multiplication
        baselines_flat = baselines.reshape(-1, 3)  # shape: (n_pairs * n_times, 3)
        uvw_flat = baselines_flat @ rotation_matrix.T  # shape: (n_pairs * n_times, 3)
        uvw = uvw_flat.reshape(n_pairs, n_times, 3)  # shape: (n_pairs, n_times, 3)

        # Apply visibility mask and filter out NaN values
        uvw[~vis_mask] = np.nan  # Set non-visible points to NaN
        uv_points = {}
        for pair_idx, pair in enumerate(pairs):
            uvw_pair = uvw[pair_idx]  # shape: (n_times, 3)
            # Select valid (non-NaN) points
            valid_mask = ~np.any(np.isnan(uvw_pair), axis=1)  # shape: (n_times,)
            if np.any(valid_mask):
                uv_points[pair] = uvw_pair[valid_mask]  # shape: (n_valid_times, 3)
                logger.debug(f"Computed {np.sum(valid_mask)} UVW points for baseline {pair}")
            else:
                logger.debug(f"No valid UVW points for baseline {pair}")

        return uv_points

    @time_execution
    def _calculate_sun_angles(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate angular separation between source and Sun for all active scans in geometric coordinates.

        Args:
            obj (Observation | ScheduleProject): The object to calculate sun angles for.
            attributes (Dict[str, Any]): Parameters including "time_step", "store_key", "recalculate",
                                        "position_store_key", "visibility_store_key".

        Returns:
            Dict[str, Any]: Sun angles per source, scan, and telescope, formatted as:
                {
                    "metadata": {"time_step": float, "scan_count": int, "position_store_key": str, "visibility_store_key": str},
                    "data": {
                        source_name: {
                            scan_name: {
                                telescope_code: np.array([angle1, angle2, ...])  # angles in degrees
                            }
                        }
                    }
                }

        Notes:
            - Depends on precomputed time arrays, telescope positions, and source visibility.
            - Invokes _calculate_time_arrays, _calculate_telescope_positions, and _calculate_source_visibility if needed.
            - Uses vectorized computations for efficiency.
            - Results are cached in obj.calculated_data under the specified store_key.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "sun_angles")
            position_store_key = attributes.get("position_store_key", "telescope_positions")
            visibility_store_key = attributes.get("visibility_store_key", "source_visibility")
            recalculate = attributes.get("recalculate", False)

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {}
                results = {}
                max_workers = min(len(observations), 4) if len(observations) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._calculate_sun_angles, obs, attributes): obs.get_observation_code()
                        for obs in observations
                    }
                    for future in futures:
                        obs_code = futures[future]
                        results[obs_code] = future.result()
                logger.info(f"Calculated sun angles for {len(observations)} observations in project '{obj.name}'")
                return results

            def calculate_sun_angles(obj: Observation, attrs: Dict[str, Any]) -> Dict[str, Any]:
                scans = obj.get_scans().get_active_items()
                if not scans:
                    logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
                    return {}

                # Retrieve or calculate dependencies
                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": recalculate}
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": recalculate}

                time_data = self._calculate_time_arrays(obj, time_attrs)
                position_data = self._calculate_telescope_positions(obj, position_attrs)
                visibility_data = self._calculate_source_visibility(obj, visibility_attrs)

                if not (time_data and position_data and visibility_data):
                    logger.error(f"Missing required data (times, positions, or visibility) for '{obj.get_observation_code()}'")
                    return {}

                results = {}
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(
                            self._process_sun_angles,
                            scan,
                            obj,
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
                            if source_name not in results:
                                results[source_name] = {}
                            results[source_name][scan_name] = scan_result["angles"]
                if not results:
                    logger.warning(f"No sun angles computed for observation '{obj.get_observation_code()}'")
                return results

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()),
                "position_store_key": position_store_key,
                "visibility_store_key": visibility_store_key
            }
            return self._get_cached_or_calculate(obj, store_key, calculate_sun_angles, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate sun angles: {str(e)}")
            return {}

    def _process_sun_angles(
        self,
        scan: Scan,
        observation: Observation,
        time_step: Optional[float],
        time_data: Dict[str, Any],
        position_data: Dict[str, Any],
        visibility_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process sun angles for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds).
            time_data (Dict[str, Any]): Precomputed time arrays from _calculate_time_arrays.
            position_data (Dict[str, Any]): Precomputed telescope positions.
            visibility_data (Dict[str, Any]): Precomputed source visibility data.

        Returns:
            Dict[str, Any]: Sun angles in degrees, formatted as:
                {
                    "source": source_name,
                    "angles": {telescope_code: np.array([angle1, angle2, ...])}
                }
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

        # Get times for the scan
        scan_times = time_data.get(source_name, {}).get(scan_name, None)
        if scan_times is None or not isinstance(scan_times, Time) or scan_times.size == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return {"source": source_name, "angles": {}}

        # Get telescope positions and visibility
        scan_positions = position_data.get(scan_name, {})
        scan_visibility = visibility_data.get(source_name, {}).get(scan_name, {})
        if not (scan_positions and scan_visibility):
            logger.warning(f"No position or visibility data for scan '{scan_name}' in observation '{observation.get_observation_code()}'")
            return {"source": source_name, "angles": {}}

        # Prepare source and sun coordinates
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
        sun_coord = get_sun(scan_times)

        angles = {}
        # Process telescopes
        tel_codes = [tel.get_code() for tel in active_telescopes]
        visibility = np.array([scan_visibility.get(code, [False] * len(scan_times)) for code in tel_codes], dtype=bool)  # shape: (n_tels, n_times)
        positions = np.array([scan_positions.get(code, np.full((len(scan_times), 3), np.nan)) for code in tel_codes])  # shape: (n_tels, n_times, 3)

        if positions.shape[1] != len(scan_times):
            logger.warning(f"Mismatched position data length for scan '{scan_name}': {positions.shape[1]} positions vs {len(scan_times)} times")
            return {"source": source_name, "angles": {}}

        # Vectorized angular separation calculation
        separations = source_coord.separation(sun_coord).deg  # shape: (n_times,)
        for i, tel_code in enumerate(tel_codes):
            tel_angles = np.full_like(separations, np.nan)  # Initialize with NaN
            tel_angles[visibility[i]] = separations[visibility[i]]  # Set angles where source is visible
            if np.any(~np.isnan(tel_angles)):
                angles[tel_code] = tel_angles
            else:
                logger.debug(f"No valid sun angles for telescope '{tel_code}' in scan '{scan_name}'")

        if not angles:
            logger.warning(f"No valid sun angles computed for scan '{scan_name}'")
        else:
            logger.debug(f"Computed sun angles for {len(angles)} telescopes in scan '{scan_name}'")

        return {"source": source_name, "angles": angles}

    def _compute_sun_angle(self, source_coord: SkyCoord, time: Time, telescopes: List[Telescope | SpaceTelescope]) -> Dict[str, float]:
        """Compute angle between the direction from telescope to source and to Sun for each telescope at a given time.

        Args:
            source_coord (SkyCoord): Source coordinates.
            time (Time): Time of calculation.
            telescopes (List[Telescope | SpaceTelescope]): List of telescopes.

        Returns:
            Dict[str, float]: Angular separation (degrees) per telescope code.
        """
        sun_gcrs = get_sun(time)
        angles = {}

        for tel in telescopes:
            if isinstance(tel, SpaceTelescope):

                tel_pos, _ = tel.get_state_vector(time)
                tel_pos = np.array(tel_pos)

                sun_pos = np.array([sun_gcrs.cartesian.x.to(u.m).value,
                                    sun_gcrs.cartesian.y.to(u.m).value,
                                    sun_gcrs.cartesian.z.to(u.m).value])

                source_icrs = source_coord.icrs
                source_dir = np.array([source_icrs.cartesian.x.value,
                                    source_icrs.cartesian.y.value,
                                    source_icrs.cartesian.z.value])
                source_dir /= np.linalg.norm(source_dir)

                vec_to_sun = sun_pos - tel_pos
                vec_to_sun /= np.linalg.norm(vec_to_sun)

                vec_to_source = source_dir

                cos_angle = np.clip(np.dot(vec_to_source, vec_to_sun), -1.0, 1.0)
                angle = np.degrees(np.arccos(cos_angle))

                angles[tel.get_code()] = angle
            else:
                x, y, z = tel.get_coordinates()
                vx, vy, vz = tel.get_velocities()
                
                dt = (time - Time("2000-01-01T12:00:00")).sec
                itrs_coords = CartesianRepresentation(x + vx * dt, y + vy * dt, z + vz * dt, unit=u.m)
                itrs = ITRS(itrs_coords, obstime=time)
                location = itrs.earth_location
                
                altaz_frame = AltAz(obstime=time, location=location)
                source_altaz = source_coord.transform_to(altaz_frame)
                sun_altaz = sun_gcrs.transform_to(altaz_frame)

                if source_altaz.alt.deg < 0 or sun_altaz.alt.deg < 0:
                    angle = float('nan')
                else:
                    angle = source_altaz.separation(sun_altaz).deg
                angles[tel.get_code()] = angle

        return angles

    @time_execution
    def _calculate_az_el(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate azimuth/elevation or hour angle/declination for ground telescopes in active scans.

        Args:
            obj (Observation | ScheduleProject): The object to calculate angles for.
            attributes (Dict[str, Any]): Parameters including "time_step", "store_key", "position_store_key",
                                        "visibility_store_key", "recalculate".

        Returns:
            Dict[str, Any]: Az/El or HA/Dec angles per source, scan, and telescope, formatted as:
                {
                    "metadata": {"time_step": float, "scan_count": int, "position_store_key": str, "visibility_store_key": str},
                    "data": {
                        source_name: {
                            scan_name: {
                                telescope_code: np.array([[az/ha, el/dec], ...])
                            }
                        }
                    }
                }

        Notes:
            - Uses precomputed time arrays, telescope positions, and source visibility from calculated_data.
            - Computes angles for ground telescopes only (AZIM or EQUA mounts).
            - Space telescopes are excluded as they use pitch/yaw.
            - Stores results in calculated_data under 'az_el' key.
            - Vectorized computations are used for efficiency.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "az_el")
            position_store_key = attributes.get("position_store_key", "telescope_positions")
            visibility_store_key = attributes.get("visibility_store_key", "source_visibility")
            recalculate = attributes.get("recalculate", False)

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {}
                results = {}
                max_workers = min(len(observations), 4) if len(observations) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._calculate_az_el, obs, attributes): obs.get_observation_code()
                        for obs in observations
                    }
                    for future in futures:
                        obs_code = futures[future]
                        results[obs_code] = future.result()
                logger.info(f"Calculated az/el or ha/dec for {len(observations)} observations in project '{obj.name}'")
                return results

            def calculate_az_el(obj: Observation, attrs: Dict[str, Any]) -> Dict[str, Any]:
                scans = obj.get_scans().get_active_items()
                if not scans:
                    logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
                    return {}

                # Retrieve or calculate dependencies
                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": recalculate}
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": recalculate}

                time_data = self._calculate_time_arrays(obj, time_attrs)
                position_data = self._calculate_telescope_positions(obj, position_attrs)
                visibility_data = self._calculate_source_visibility(obj, visibility_attrs)

                if not (time_data and position_data and visibility_data):
                    logger.error(f"Missing required data (times, positions, or visibility) for '{obj.get_observation_code()}'")
                    return {}

                results = {}
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_az_el, scan, obj, time_step, time_data, position_data, visibility_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        source_name = scan_result.get("source")
                        if source_name and scan_result.get("angles"):
                            if source_name not in results:
                                results[source_name] = {}
                            results[source_name][scan_name] = scan_result["angles"]
                if not results:
                    logger.warning(f"No az/el or ha/dec data computed for observation '{obj.get_observation_code()}'")
                return results

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()),
                "position_store_key": position_store_key,
                "visibility_store_key": visibility_store_key
            }
            return self._get_cached_or_calculate(obj, store_key, calculate_az_el, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate az/el or ha/dec: {str(e)}")
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

        # Get times for the scan
        scan_times = time_data.get(source_name, {}).get(scan_name, None)
        if scan_times is None or not isinstance(scan_times, Time) or scan_times.size == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return {"source": source_name, "angles": {}}

        # Get visibility and position data
        scan_visibility = visibility_data.get(source_name, {}).get(scan_name, {})
        scan_positions = position_data.get(scan_name, {})
        if not (scan_visibility and scan_positions):
            logger.warning(f"No visibility or position data for scan '{scan_name}' in observation '{observation.get_observation_code()}'")
            return {"source": source_name, "angles": {}}

        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
        angles = {}

        # Prepare arrays for ground telescopes
        tel_codes = [tel.get_code() for tel in active_telescopes]
        mount_types = [tel.get("mount_type").value for tel in active_telescopes]
        visibility = np.array([scan_visibility.get(code, [False] * len(scan_times)) for code in tel_codes], dtype=bool)  # shape: (n_tels, n_times)
        positions = np.array([scan_positions.get(code, np.full((len(scan_times), 3), np.nan)) for code in tel_codes])  # shape: (n_tels, n_times, 3)

        if positions.shape[1] != len(scan_times):
            logger.warning(f"Mismatched position data length for scan '{scan_name}': {positions.shape[1]} positions vs {len(scan_times)} times")
            return {"source": source_name, "angles": {}}

        # Process AZIM mounts
        azim_indices = [i for i, mt in enumerate(mount_types) if mt == "AZIM"]
        if azim_indices:
            azim_codes = [tel_codes[i] for i in azim_indices]
            azim_positions = positions[azim_indices]  # shape: (n_azim_tels, n_times, 3)
            azim_visibility = visibility[azim_indices]  # shape: (n_azim_tels, n_times)

            # Vectorized coordinate transformation
            gcrs_coords = CartesianRepresentation(
                x=azim_positions[:, :, 0] * u.m,
                y=azim_positions[:, :, 1] * u.m,
                z=azim_positions[:, :, 2] * u.m
            )
            gcrs = GCRS(gcrs_coords, obstime=scan_times)
            itrs = gcrs.transform_to(ITRS(obstime=scan_times))
            locations = itrs.earth_location
            altaz = source_coord.transform_to(AltAz(obstime=scan_times, location=locations))
            az = altaz.az.deg  # shape: (n_tels, n_times)
            el = altaz.alt.deg  # shape: (n_tels, n_times)

            # Apply visibility mask
            az[~azim_visibility] = np.nan
            el[~azim_visibility] = np.nan

            # Store results
            for i, code in enumerate(azim_codes):
                angles[code] = np.stack([az[i], el[i]], axis=-1)  # shape: (n_times, 2)

        # Process EQUA mounts
        equa_indices = [i for i, mt in enumerate(mount_types) if mt == "EQUA"]
        if equa_indices:
            equa_codes = [tel_codes[i] for i in equa_indices]
            equa_positions = positions[equa_indices]  # shape: (n_equa_tels, n_times, 3)
            equa_visibility = visibility[equa_indices]  # shape: (n_equa_tels, n_times)

            # Vectorized coordinate transformation
            gcrs_coords = CartesianRepresentation(
                x=equa_positions[:, :, 0] * u.m,
                y=equa_positions[:, :, 1] * u.m,
                z=equa_positions[:, :, 2] * u.m
            )
            gcrs = GCRS(gcrs_coords, obstime=scan_times)
            itrs = gcrs.transform_to(ITRS(obstime=scan_times))
            locations = itrs.earth_location
            hadec = source_coord.transform_to(HADec(obstime=scan_times, location=locations))
            ha = hadec.ha.deg   # shape: (n_tels, n_times)
            dec = hadec.dec.deg # shape: (n_tels, n_times)

            # Apply visibility mask
            ha[~equa_visibility] = np.nan
            dec[~equa_visibility] = np.nan

            # Store results
            for i, code in enumerate(equa_codes):
                angles[code] = np.stack([ha[i], dec[i]], axis=-1)  # shape: (n_times, 2)

        # Handle unsupported mount types
        for i, tel in enumerate(active_telescopes):
            if mount_types[i] not in ["AZIM", "EQUA"]:
                logger.warning(f"Unsupported mount type '{mount_types[i]}' for telescope '{tel.get_code()}' in scan '{scan_name}'")
                angles[tel.get_code()] = np.full((len(scan_times), 2), np.nan)

        # Check for valid angle data
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
            obj (Observation | ScheduleProject): The object to calculate time on source for.
            attributes (Dict[str, Any]): Parameters including "time_step", "store_key", "recalculate".

        Returns:
            Dict[str, Any]: Time-on-source blocks per source, scan, and telescope, formatted as:
                {
                    "metadata": {"time_step": float, "scan_count": int, "visibility_store_key": str},
                    "data": {
                        source_name: {
                            scan_name: {
                                telescope_code: np.array([[start_mjd, end_mjd, duration], ...])  # times in MJD, duration in seconds
                            }
                        }
                    }
                }

        Notes:
            - Depends on precomputed time arrays and source visibility from calculated_data.
            - Uses vectorized computations for efficiency.
            - Stores results in calculated_data under the specified store_key.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "time_on_source")
            visibility_store_key = attributes.get("visibility_store_key", "source_visibility")
            recalculate = attributes.get("recalculate", False)

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {"metadata": {}, "data": {}}
                results = {"metadata": {"time_step": time_step, "scan_count": len(observations), "visibility_store_key": visibility_store_key}, "data": {}}
                max_workers = min(len(observations), 4) if len(observations) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._calculate_time_on_source, obs, attributes): obs.get_observation_code()
                        for obs in observations
                    }
                    for future in futures:
                        obs_code = futures[future]
                        obs_result = future.result()
                        if obs_result and "data" in obs_result:
                            results["data"][obs_code] = obs_result["data"]
                logger.info(f"Calculated time on source for {len(observations)} observations in project '{obj.name}'")
                return results

            def calculate_time_on_source(obj, attrs):
                scans = obj.get_scans().get_active_items()
                if not scans:
                    logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
                    return {"metadata": {}, "data": {}}

                # Retrieve or calculate dependencies
                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": recalculate}
                time_data = self._calculate_time_arrays(obj, time_attrs)
                visibility_data = self._calculate_source_visibility(obj, visibility_attrs)

                if not (time_data and visibility_data):
                    logger.error(f"Missing required data (times or visibility) for '{obj.get_observation_code()}'")
                    return {"metadata": {}, "data": {}}

                results = {}
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_time_on_source, scan, obj, time_step, time_data, visibility_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        source_name = scan_result.get("source")
                        if source_name and scan_result.get("time_blocks"):
                            if source_name not in results:
                                results[source_name] = {}
                            results[source_name][scan_name] = scan_result["time_blocks"]
                if not results:
                    logger.warning(f"No time-on-source data computed for observation '{obj.get_observation_code()}'")
                return results

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()),
                "visibility_store_key": visibility_store_key
            }
            result = self._get_cached_or_calculate(obj, store_key, calculate_time_on_source, attributes, metadata)
            return {"metadata": metadata, "data": result}
        except Exception as e:
            logger.error(f"Failed to calculate time on source: {str(e)}")
            return {"metadata": {}, "data": {}}
        
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

        # Get times for the scan
        scan_times = time_data.get(source_name, {}).get(scan_name, None)
        if scan_times is None or not isinstance(scan_times, Time) or scan_times.size == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return {"source": source_name, "time_blocks": {}}

        # Get visibility data
        scan_visibility = visibility_data.get(source_name, {}).get(scan_name, {})
        if not scan_visibility:
            logger.warning(f"No visibility data for scan '{scan_name}' in source '{source_name}'")
            return {"source": source_name, "time_blocks": {}}

        # Prepare visibility array
        tel_codes = [tel.get_code() for tel in active_telescopes]
        visibility = np.array([scan_visibility.get(code, [False] * len(scan_times)) for code in tel_codes], dtype=bool)  # shape: (n_tels, n_times)

        # Compute time blocks
        time_blocks = {}
        time_mjd = scan_times.mjd  # MJD array
        if time_step is None:
            # Single-time case: treat as one block if visible
            for i, tel_code in enumerate(tel_codes):
                if visibility[i, 0]:
                    duration = scan.get_duration()
                    time_blocks[tel_code] = np.array([[time_mjd[0], time_mjd[0], duration]])
                else:
                    time_blocks[tel_code] = np.array([], dtype=float).reshape(0, 3)
        else:
            # Vectorized block computation
            time_step_sec = time_step if time_step is not None else scan.get_duration()
            for i, tel_code in enumerate(tel_codes):
                vis = visibility[i]
                # Find transitions in visibility (True -> False or False -> True)
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

                # Compute start, end, duration for each block
                blocks = np.zeros((len(start_indices), 3), dtype=float)
                blocks[:, 0] = time_mjd[start_indices]  # Start MJD
                blocks[:, 1] = time_mjd[end_indices]   # End MJD
                blocks[:, 2] = (blocks[:, 1] - blocks[:, 0]) * 86400.0  # Duration in seconds
                time_blocks[tel_code] = blocks

                # Log block count
                logger.debug(f"Computed {len(blocks)} time-on-source blocks for telescope '{tel_code}' in scan '{scan_name}'")

        return {"source": source_name, "time_blocks": time_blocks}

    @time_execution
    def _calculate_beam_pattern(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate beam pattern for active telescopes in the observation or project, independent of frequency.

        Args:
            obj (Observation | ScheduleProject): The object to calculate beam pattern for.
            attributes (Dict[str, Any]): Parameters including "store_key", "recalculate".

        Returns:
            Dict[str, Any]: Beam pattern data formatted as:
                {
                    "metadata": {
                        "telescope_count": int,
                        "frequency_agnostic": bool,
                        "scale_instruction": str
                    },
                    "data": {
                        telescope_code: {
                            "theta": List[float],  # Angles in radians
                            "pattern": List[float]  # Normalized beam pattern, to be scaled by pi*D/wavelength
                        }
                    }
                }

        Notes:
            - Supports both SINGLE_DISH and VLBI observations.
            - Calculates beam pattern for all active telescopes, including SpaceTelescope.
            - Beam pattern is computed in a frequency-agnostic manner; scaling by pi*D/wavelength is required during visualization.
            - Uses vectorized computations for efficiency.
            - Stores results in calculated_data under 'beam_pattern'.
        """
        try:
            store_key = attributes.get("store_key", "beam_pattern")
            recalculate = attributes.get("recalculate", False)

            if "freq_name" in attributes:
                logger.info("Ignoring 'freq_name' as beam pattern is calculated frequency-agnostic")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {"metadata": {"telescope_count": 0, "frequency_agnostic": True, "scale_instruction": "Multiply pattern by (pi*D/wavelength)^2 during visualization"}, "data": {}}
                results = {
                    "metadata": {
                        "telescope_count": 0,
                        "frequency_agnostic": True,
                        "scale_instruction": "Multiply pattern by (pi*D/wavelength)^2 during visualization"
                    },
                    "data": {}
                }
                max_workers = min(len(observations), 4) if len(observations) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._calculate_beam_pattern, obs, attributes): obs.get_observation_code()
                        for obs in observations
                    }
                    telescope_counts = []
                    for future in futures:
                        obs_code = futures[future]
                        obs_result = future.result()
                        if obs_result and "data" in obs_result:
                            results["data"][obs_code] = obs_result["data"]
                            telescope_counts.append(obs_result["metadata"].get("telescope_count", 0))
                    results["metadata"]["telescope_count"] = sum(telescope_counts)
                logger.info(f"Calculated beam pattern for {len(observations)} observations in project '{obj.name}'")
                return results

            def calculate_beam_pattern(obj: Observation, attrs: Dict[str, Any]) -> Dict[str, Any]:
                telescopes = obj.get_telescopes().get_active_items()
                if not telescopes:
                    logger.warning(f"No active telescopes in observation '{obj.get_observation_code()}'")
                    return {
                        "metadata": {
                            "telescope_count": 0,
                            "frequency_agnostic": True,
                            "scale_instruction": "Multiply pattern by (pi*D/wavelength)^2 during visualization"
                        },
                        "data": {}
                    }

                # Check observation type
                obs_type = obj.get_observation_type()
                if obs_type not in ["SINGLE_DISH", "VLBI"]:
                    logger.warning(f"Beam pattern calculation is only for SINGLE_DISH or VLBI, got {obs_type}")
                    return {
                        "metadata": {
                            "telescope_count": 0,
                            "frequency_agnostic": True,
                            "scale_instruction": "Multiply pattern by (pi*D/wavelength)^2 during visualization"
                        },
                        "data": {}
                    }

                # Vectorized computation
                theta = np.linspace(-np.pi / 2, np.pi / 2, 5000)  # radians
                results = {
                    "metadata": {
                        "telescope_count": len(telescopes),
                        "frequency_agnostic": True,
                        "scale_instruction": "Multiply pattern by (pi*D/wavelength)^2 during visualization"
                    },
                    "data": {}
                }

                # Collect diameters and filter valid telescopes
                diameters = []
                valid_telescopes = []
                for tel in telescopes:
                    diameter = tel.get("diameter")
                    if diameter is None or diameter <= 0:
                        logger.warning(f"Invalid or missing diameter for telescope '{tel.get_code()}'; skipping")
                        continue
                    diameters.append(diameter)
                    valid_telescopes.append(tel)

                if not valid_telescopes:
                    logger.warning(f"No telescopes with valid diameters in observation '{obj.get_observation_code()}'")
                    return {
                        "metadata": {
                            "telescope_count": 0,
                            "frequency_agnostic": True,
                            "scale_instruction": "Multiply pattern by (pi*D/wavelength)^2 during visualization"
                        },
                        "data": {}
                    }

                # Vectorize beam pattern calculation
                diameters = np.array(diameters)  # shape: (n_telescopes,)
                x = diameters[:, None] * np.sin(theta)  # shape: (n_telescopes, n_theta), frequency-agnostic
                pattern = (2 * j1(x) / x) ** 2  # shape: (n_telescopes, n_theta)
                pattern = np.where(np.isnan(pattern), 1.0, pattern)  # Handle division by zero at theta=0
                pattern = pattern / np.max(pattern, axis=1, keepdims=True)  # Normalize per telescope

                # Store results
                for tel, pat in zip(valid_telescopes, pattern):
                    results["data"][tel.get_code()] = {
                        "theta": theta.tolist(),
                        "pattern": pat.tolist()  # Convert to list for visualizer compatibility
                    }

                logger.info(f"Calculated frequency-agnostic beam pattern for {len(valid_telescopes)} telescopes in observation '{obj.get_observation_code()}'")
                return results

            metadata = {
                "telescope_count": len(obj.get_telescopes().get_active_items()),
                "frequency_agnostic": True,
                "scale_instruction": "Multiply pattern by (pi*D/wavelength)^2 during visualization"
            }
            result = self._get_cached_or_calculate(obj, store_key, calculate_beam_pattern, attributes, metadata)
            return {"metadata": metadata, "data": result}

        except Exception as e:
            logger.error(f"Failed to calculate beam pattern: {str(e)}")
            return {
                "metadata": {
                    "telescope_count": 0,
                    "frequency_agnostic": True,
                    "scale_instruction": "Multiply pattern by (pi*D/wavelength)^2 during visualization"
                },
                "data": {}
            } 

    @time_execution
    def _calculate_synthesized_beam(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate synthesized beam for VLBI observations across all active frequencies.

        Args:
            obj (Observation | ScheduleProject): The object to calculate synthesized beam for.
            attributes (Dict[str, Any]): Parameters including "time_step", "store_key", and "recalculate".

        Returns:
            Dict[str, Any]: Synthesized beam data per source, scan, and frequency, formatted as:
                {
                    "metadata": {
                        "time_step": float,
                        "scan_count": int,
                        "freq_names": List[str]
                    },
                    "data": {
                        source_name: {
                            scan_name: {
                                freq_name: np.array([[theta_u, theta_v, beam_x, beam_y], ...])
                            }
                        }
                    }
                }

        Notes:
            - Requires UV data in meters from _calculate_uv_coverage.
            - Computes 2D FFT of UV plane to derive the synthesized beam for each active frequency.
            - Results are cached under 'synthesized_beam' key in calculated_data.
            - Uses vectorized computations for efficiency.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "synthesized_beam")
            recalculate = attributes.get("recalculate", False)

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {"metadata": {"time_step": time_step, "scan_count": 0, "freq_names": []}, "data": {}}
                results = {
                    "metadata": {
                        "time_step": time_step,
                        "scan_count": 0,
                        "freq_names": []
                    },
                    "data": {}
                }
                max_workers = min(len(observations), 4) if len(observations) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._calculate_synthesized_beam, obs, attributes): obs.get_observation_code()
                        for obs in observations
                    }
                    scan_counts = []
                    freq_names_set = set()
                    for future in futures:
                        obs_code = futures[future]
                        obs_result = future.result()
                        if obs_result and "data" in obs_result:
                            results["data"][obs_code] = obs_result["data"]
                            scan_counts.append(obs_result["metadata"].get("scan_count", 0))
                            freq_names_set.update(obs_result["metadata"].get("freq_names", []))
                    results["metadata"]["scan_count"] = sum(scan_counts)
                    results["metadata"]["freq_names"] = sorted(list(freq_names_set))
                logger.info(f"Calculated synthesized beam for {len(observations)} observations in project '{obj.name}'")
                return results

            if obj.get_observation_type() != "VLBI":
                logger.warning(f"Synthesized beam calculation is only for VLBI, got {obj.get_observation_type()}")
                return {"metadata": {"time_step": time_step, "scan_count": 0, "freq_names": []}, "data": {}}

            def calculate_synthesized_beam(obj: Observation, attrs: Dict[str, Any]) -> Dict[str, Any]:
                scans = obj.get_scans().get_active_items()
                if not scans:
                    logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
                    return {"metadata": {"time_step": time_step, "scan_count": 0, "freq_names": []}, "data": {}}

                frequencies = obj.get_frequencies().get_active_items()
                if not frequencies:
                    logger.warning(f"No active frequencies in observation '{obj.get_observation_code()}'")
                    return {"metadata": {"time_step": time_step, "scan_count": len(scans), "freq_names": []}, "data": {}}

                freq_names = [freq.name for freq in frequencies]
                results = {"metadata": {"time_step": time_step, "scan_count": len(scans), "freq_names": freq_names}, "data": {}}

                # Retrieve or calculate UV coverage
                uv_store_key = "uv_coverage"
                uv_data = self._calculate_uv_coverage(obj, {
                    "time_step": time_step,
                    "store_key": uv_store_key,
                    "recalculate": recalculate
                })
                if not uv_data:
                    logger.warning(f"No UV data available for '{obj.get_observation_code()}'")
                    return {"metadata": {"time_step": time_step, "scan_count": len(scans), "freq_names": freq_names}, "data": {}}

                # Process scans in parallel
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_synthesized_beam, scan, obj, time_step, uv_data, frequencies): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        source_name = scan_result.get("source")
                        if source_name and scan_result.get("beam_data"):
                            if source_name not in results["data"]:
                                results["data"][source_name] = {}
                            results["data"][source_name][scan_name] = scan_result["beam_data"]

                if not results["data"]:
                    logger.warning(f"No synthesized beam data computed for observation '{obj.get_observation_code()}'")
                else:
                    logger.info(f"Calculated synthesized beam for {len(results['data'])} sources across {len(scans)} scans in '{obj.get_observation_code()}'")
                return results

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()),
                "freq_names": [freq.name for freq in obj.get_frequencies().get_active_items()]
            }
            return self._get_cached_or_calculate(obj, store_key, calculate_synthesized_beam, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate synthesized beam: {str(e)}")
            return {"metadata": {"time_step": time_step, "scan_count": 0, "freq_names": []}, "data": {}}
        
    def _process_synthesized_beam(self, scan: Scan, observation: Observation, time_step: Optional[float], uv_data: Dict[str, Any], frequencies: List[IF]) -> Dict[str, Any]:
        """Process synthesized beam for a single scan across all active frequencies.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds).
            uv_data (Dict[str, Any]): Precomputed UV data in meters.
            frequencies (List[IF]): List of active frequency setups.

        Returns:
            Dict[str, Any]: Synthesized beam data for the scan, formatted as:
                {
                    "source": source_name,
                    "beam_data": {
                        freq_name: np.array([[theta_u, theta_v, beam_x, beam_y], ...])
                    }
                }
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return {"source": None, "beam_data": {}}

        scan_name = scan.name
        source_name = source.name
        scan_uv_data = uv_data.get(source_name, {}).get(scan_name, {}).get("uv_points", {})
        if not scan_uv_data:
            logger.warning(f"No UV points for scan '{scan_name}' in source '{source_name}'")
            return {"source": source_name, "beam_data": {}}

        beam_data = {}
        c = 299792458  # Speed of light in m/s

        # Vectorized collection of UV points
        u_all, v_all = [], []
        for baseline, points in scan_uv_data.items():
            if points.size > 0:
                u_all.append(points[:, 0])  # u in meters
                v_all.append(points[:, 1])  # v in meters
                u_all.append(-points[:, 0])  # Conjugate points for Hermitian symmetry
                v_all.append(-points[:, 1])
        if not u_all or not v_all:
            logger.warning(f"No valid UV points for scan '{scan_name}' in source '{source_name}'")
            return {"source": source_name, "beam_data": {}}

        u = np.concatenate(u_all)
        v = np.concatenate(v_all)
        if len(u) < 10:  # Minimum threshold for reliable beam
            logger.warning(f"Too few UV points ({len(u)//2}) for reliable synthesized beam in scan '{scan_name}'")
            return {"source": source_name, "beam_data": {}}

        u_max = np.max(np.abs(u)) if u.size > 0 else 0
        v_max = np.max(np.abs(v)) if v.size > 0 else 0
        if u_max == 0 or v_max == 0:
            logger.warning(f"Invalid UV range for scan '{scan_name}': u_max={u_max}, v_max={v_max}")
            return {"source": source_name, "beam_data": {}}

        # Adaptive grid size based on number of UV points
        n_points = len(u) // 2
        grid_size = max(128, min(1024, int(np.sqrt(n_points) * 16)))  # Dynamic grid size
        if grid_size % 2 != 0:
            grid_size += 1  # Ensure even size for FFT
        logger.debug(f"Using grid_size={grid_size} for {n_points} UV points in scan '{scan_name}'")

        # Create UV grid
        u_grid = np.linspace(-u_max, u_max, grid_size)
        v_grid = np.linspace(-v_max, v_max, grid_size)
        uv_plane = np.zeros((grid_size, grid_size), dtype=complex)
        u_idx = ((u + u_max) / (2 * u_max) * (grid_size - 1)).astype(int)
        v_idx = ((v + v_max) / (2 * v_max) * (grid_size - 1)).astype(int)
        valid_idx = (0 <= u_idx) & (u_idx < grid_size) & (0 <= v_idx) & (v_idx < grid_size)
        np.add.at(uv_plane, (v_idx[valid_idx], u_idx[valid_idx]), 1.0)

        for freq in frequencies:
            freq_name = freq.name
            frequency = freq.get("frequency") * 1e6  # Convert MHz to Hz
            if frequency is None or frequency <= 0:
                logger.warning(f"Invalid frequency for '{freq_name}' in scan '{scan_name}'")
                continue

            # Compute synthesized beam
            wavelength = c / frequency
            beam_2d = fftshift(fft2(uv_plane))
            beam_2d = np.abs(beam_2d)
            beam_2d /= np.max(beam_2d) if np.max(beam_2d) != 0 else 1.0  # Normalize

            # Convert to angular coordinates
            theta_u_max = wavelength / (2 * u_max) if u_max > 0 else np.pi
            theta_v_max = wavelength / (2 * v_max) if v_max > 0 else np.pi
            theta_u = np.linspace(-theta_u_max, theta_u_max, grid_size)
            theta_v = np.linspace(-theta_v_max, theta_v_max, grid_size)
            theta_u_deg = np.degrees(theta_u)
            theta_v_deg = np.degrees(theta_v)

            # Create output array: [theta_u, theta_v, beam_x, beam_y]
            u_grid, v_grid = np.meshgrid(theta_u_deg, theta_v_deg)
            beam_array = np.stack([u_grid.ravel(), v_grid.ravel(), beam_2d.ravel(), beam_2d.ravel()], axis=-1)  # beam_x = beam_y for isotropic beam
            beam_data[freq_name] = beam_array

            logger.debug(f"Computed synthesized beam for scan '{scan_name}', source '{source_name}', frequency '{freq_name}' with {len(u)//2} UV points")

        if not beam_data:
            logger.warning(f"No synthesized beam data computed for scan '{scan_name}' in source '{source_name}'")
        return {"source": source_name, "beam_data": beam_data}

    @time_execution
    def _calculate_baseline_projections(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate baseline projections for VLBI observations in geometric coordinates (meters).

        Args:
            obj (Observation | ScheduleProject): The object to calculate projections for.
            attributes (Dict[str, Any]): Parameters including "time_step", "store_key", "recalculate".

        Returns:
            Dict[str, Any]: Baseline projection data per source and scan in meters, formatted as:
                For Observation:
                    {
                        source_name: {
                            scan_name: {
                                baseline: np.array([proj1, ..., projn])  # projections in meters
                            }
                        }
                    }
                For ScheduleProject:
                    {
                        obs_code: {
                            source_name: {
                                scan_name: {
                                    baseline: np.array([proj1, ..., projn])  # projections in meters
                                }
                            }
                        }
                    }
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "baseline_projections")
            recalculate = attributes.get("recalculate", False)

            if "freq_name" in attributes:
                logger.info(f"Ignoring 'freq_name' attribute for baseline projections in geometric coordinates")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {}
                results = {}
                max_workers = min(len(observations), 4) if len(observations) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._calculate_baseline_projections, obs, attributes): obs.get_observation_code()
                        for obs in observations
                    }
                    for future in futures:
                        obs_code = futures[future]
                        obs_result = future.result()
                        logger.debug(f"Processing result for observation '{obs_code}': {obs_result.keys()}")
                        if obs_result:
                            results[obs_code] = obs_result
                        else:
                            logger.warning(f"No valid data from observation '{obs_code}'")
                if not results:
                    logger.warning(f"No baseline projections computed for project '{obj.name}'")
                else:
                    logger.info(f"Calculated baseline projections for {len(observations)} observations in project '{obj.name}'")
                    logger.debug(f"Final structure for '{obj.name}': {list(results.keys())}")
                return results

            if obj.get_observation_type() != "VLBI":
                logger.warning(f"Baseline projections are only for VLBI, got {obj.get_observation_type()}")
                return {}

            def calculate_baseline_projections(obj: Observation, attrs: Dict[str, Any]) -> Dict[str, Any]:
                scans = obj.get_scans().get_active_items()
                if not scans:
                    logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
                    return {}

                telescopes = obj.get_telescopes()
                active_telescopes = telescopes.get_active_items()
                if len(active_telescopes) < 2:
                    logger.error(f"VLBI requires at least 2 active telescopes, got {len(active_telescopes)}")
                    return {}

                # Retrieve or calculate UV coverage
                uv_store_key = "uv_coverage"
                uv_attrs = {
                    "time_step": time_step,
                    "store_key": uv_store_key,
                    "recalculate": recalculate
                }
                uv_data = self._calculate_uv_coverage(obj, uv_attrs)
                if not uv_data:
                    logger.error(f"No UV coverage data for observation '{obj.get_observation_code()}'")
                    return {}

                results = {}
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_baseline_projections, scan, obj, time_step, uv_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        source_name = scan_result.get("source")
                        if source_name and scan_result.get("projections"):
                            if source_name not in results:
                                results[source_name] = {}
                            results[source_name][scan_name] = scan_result["projections"]
                            logger.debug(f"Added projections for scan '{scan_name}' in source '{source_name}'")

                if not results:
                    logger.warning(f"No baseline projections computed for observation '{obj.get_observation_code()}'")
                else:
                    logger.info(f"Calculated baseline projections for {len(results)} sources across {len(scans)} scans in '{obj.get_observation_code()}'")
                return results

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items())}
            result = self._get_cached_or_calculate(obj, store_key, calculate_baseline_projections, attributes, metadata)
            return result
        except Exception as e:
            logger.error(f"Failed to calculate baseline projections: {str(e)}")
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
            - Uses vectorized computations for efficiency.
            - Returns empty projections if UV data is invalid or insufficient.
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

        # Get UV data for the scan
        scan_uv_data = uv_data.get(source_name, {}).get(scan_name, {})
        if not scan_uv_data:
            logger.warning(f"No UV data for scan '{scan_name}' in source '{source_name}'")
            return {"source": source_name, "projections": {}}

        projections = self._compute_projections_from_uv(scan_uv_data, active_telescopes, time_step)
        if not projections:
            logger.warning(f"No valid baseline projections computed for scan '{scan_name}'")
        else:
            logger.debug(f"Computed {sum(len(proj) for proj in projections.values())} baseline projections for scan '{scan_name}' across {len(projections)} baselines")
        
        return {"source": source_name, "projections": projections}
        
    def _compute_projections_from_uv(self, uv_data: Dict[str, np.ndarray], telescopes: List[Telescope | SpaceTelescope], time_step: Optional[float]) -> Dict[str, np.ndarray]:
        """Compute baseline projections BL = sqrt(u² + v²) from UV data in meters.

        Args:
            uv_data (Dict[str, np.ndarray]): UV data as {baseline: np.array([[u,v,w], ...])}.
            telescopes (List[Telescope | SpaceTelescope]): List of active telescopes.
            time_step (Optional[float]): Sampling interval (seconds).

        Returns:
            Dict[str, np.ndarray]: Baseline projections in meters, formatted as {baseline: np.array([proj1, ..., projn])}.

        Notes:
            - Requires at least 10 UV points per baseline for reliable projections.
            - Filters out NaN values and logs invalid baselines.
        """
        projections = {}
        min_points = 10  # Minimum number of UV points for reliable projection
        for baseline, uvw in uv_data.items():
            if uvw.size == 0 or np.all(np.isnan(uvw)):
                logger.debug(f"Skipping baseline '{baseline}' due to empty or invalid UV data")
                continue
            if len(uvw) < min_points:
                logger.warning(f"Baseline '{baseline}' has too few UV points ({len(uvw)} < {min_points}); skipping")
                continue
            u, v = uvw[:, 0], uvw[:, 1]  # Extract u, v components in meters
            bl = np.sqrt(u**2 + v**2)  # BL = sqrt(u² + v²)
            valid_mask = ~np.isnan(bl)  # Filter out NaN values
            if np.any(valid_mask):
                projections[baseline] = bl[valid_mask]
                logger.debug(f"Computed {np.sum(valid_mask)} projections for baseline '{baseline}'")
            else:
                logger.debug(f"No valid projections for baseline '{baseline}'")
        
        if not projections:
            logger.warning(f"No valid baseline projections computed for provided UV data")
        return projections

    def _compute_baseline_projections_at_time(self, telescopes: List[Telescope | SpaceTelescope], time: Time, frequency: float, source_coord: Optional[SkyCoord] = None) -> Dict[str, float]:
        """Fallback method to compute BL = sqrt(u² + v²) at a given time if UV data is unavailable.

        Args:
            telescopes (List[Telescope | SpaceTelescope]): List of telescopes.
            time (Time): Time of calculation.
            frequency (float): Frequency in Hz.
            source_coord (Optional[SkyCoord]): Source coordinates (unused in this fallback).

        Returns:
            Dict[str, float]: Baseline projections per telescope pair.
        """
        logger.warning(f"Fallback to direct computation of baseline projections at {time.isot}")
        positions = [self._compute_telescope_position(tel, time) for tel in telescopes]
        c = 299792458  # m/s
        wavelength = c / frequency
        projections = {}
        
        for i, pos1 in enumerate(positions):
            for j, pos2 in enumerate(positions[i + 1:], i + 1):
                baseline = np.array(pos1) - np.array(pos2)
                uu = baseline[0] / wavelength
                vv = baseline[1] / wavelength
                bl = math.sqrt(uu * uu + vv * vv)  # BL = sqrt(u² + v²)
                pair = f"{telescopes[i].get_code()}-{telescopes[j].get_code()}"
                projections[pair] = bl
        
        return projections

    @time_execution
    def _calculate_mollweide_tracks(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Mollweide projection tracks for telescopes and source coordinates for active scans.

        Args:
            obj (Observation | ScheduleProject): The object to calculate tracks for.
            attributes (Dict[str, Any]): Parameters including "time_step", "store_key", "recalculate".

        Returns:
            Dict[str, Any]: Mollweide tracks and source coordinates, formatted as:
                For Observation:
                    {
                        source_name: {
                            scan_name: {
                                telescope_code: np.array([[lon1, lat1], [lon2, lat2], ...])  # in degrees
                            }
                        }
                    }
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "mollweide_tracks")
            recalculate = attributes.get("recalculate", False)

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {}
                results = {}
                max_workers = min(len(observations), 4) if len(observations) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._calculate_mollweide_tracks, obs, attributes): obs.get_observation_code()
                        for obs in observations
                    }
                    for future in futures:
                        obs_code = futures[future]
                        obs_result = future.result()
                        logger.debug(f"Processing result for observation '{obs_code}': {obs_result.keys()}")
                        if obs_result:
                            results[obs_code] = obs_result
                        else:
                            logger.warning(f"No valid data from observation '{obs_code}'")
                    if not results:
                        logger.warning(f"No Mollweide tracks computed for project '{obj.name}'")
                    else:
                        logger.info(f"Calculated Mollweide tracks for {len(observations)} observations in project '{obj.name}'")
                        logger.debug(f"Final structure for '{obj.name}': {list(results.keys())}")
                return results

            def calculate_mollweide(obj: Observation, attrs: Dict[str, Any]) -> Dict[str, Any]:
                scans = obj.get_scans().get_active_items()
                if not scans:
                    logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
                    return {}

                # Retrieve or calculate dependencies
                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": recalculate}
                time_data = self._calculate_time_arrays(obj, time_attrs)
                position_data = self._calculate_telescope_positions(obj, position_attrs)

                if not (time_data and position_data):
                    logger.error(f"Missing required data (times or positions) for '{obj.get_observation_code()}'")
                    return {}

                results = {}
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_mollweide_tracks, scan, obj, time_step, time_data, position_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        source_name = scan_result.get("source")
                        if source_name and scan_result.get("tracks"):
                            if source_name not in results:
                                results[source_name] = {}
                            results[source_name][scan_name] = scan_result["tracks"]
                            logger.debug(f"Added tracks for scan '{scan_name}' in source '{source_name}'")

                if not results:
                    logger.warning(f"No Mollweide tracks computed for observation '{obj.get_observation_code()}'")
                else:
                    logger.info(f"Calculated Mollweide tracks for {len(results)} sources across {len(scans)} scans in '{obj.get_observation_code()}'")
                return results

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()),
                "sources": []  # Only used for mollweide_tracks in cache
            }
            result = self._get_cached_or_calculate(obj, store_key, calculate_mollweide, attributes, metadata)
            return result
        except Exception as e:
            logger.error(f"Failed to calculate Mollweide tracks: {str(e)}")
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
                    "source": source_name,
                    "tracks": {
                        telescope_code: np.array([[lon1, lat1], [lon2, lat2], ...])  # in degrees
                    }
                }
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning(f"No active source for scan '{scan.name}' in observation '{observation.get_observation_code()}'")
            return {"source": None, "tracks": {}}

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]

        if not active_telescopes:
            logger.warning(f"No active telescopes for scan '{scan_name}' in observation '{observation.get_observation_code()}'")
            return {"source": source_name, "tracks": {}}

        # Get times for the scan
        scan_times = time_data.get(source_name, {}).get(scan_name, None)
        if scan_times is None or not isinstance(scan_times, Time) or scan_times.size == 0:
            logger.warning(f"No valid times for scan '{scan_name}' in source '{source_name}'")
            return {"source": source_name, "tracks": {}}

        # Get telescope positions for the scan
        scan_positions = position_data.get(scan_name, {})
        if not scan_positions:
            logger.warning(f"No position data for scan '{scan_name}' in observation '{observation.get_observation_code()}'")
            return {"source": source_name, "tracks": {}}

        # Prepare arrays for vectorized computation
        tel_codes = [tel.get_code() for tel in active_telescopes]
        positions = np.array([
            scan_positions.get(code, np.full((len(scan_times), 3), np.nan))
            for code in tel_codes
        ])  # shape: (n_tels, n_times, 3)

        # Vectorized Mollweide coordinate calculation
        tracks = {}
        r = np.sqrt(np.sum(positions**2, axis=2))  # shape: (n_tels, n_times)
        valid_mask = r > 0  # Avoid division by zero
        ra_rad = np.full_like(r, np.nan)
        dec_rad = np.full_like(r, np.nan)
        ra_rad[valid_mask] = np.arctan2(positions[valid_mask, 1], positions[valid_mask, 0])
        dec_rad[valid_mask] = np.arcsin(positions[valid_mask, 2] / r[valid_mask])
        ra = np.degrees(ra_rad)  # shape: (n_tels, n_times)
        dec = np.degrees(dec_rad)  # shape: (n_tels, n_times)
        lon = np.where(ra > 180.0, ra - 360.0, ra)  # shape: (n_tels, n_times)
        lat = np.clip(dec, -90.0, 90.0)  # shape: (n_tels, n_times)

        for i, tel_code in enumerate(tel_codes):
            if np.all(np.isnan(lon[i]) | np.isnan(lat[i])):
                logger.warning(f"No valid Mollweide coordinates for telescope '{tel_code}' in scan '{scan_name}'")
                continue
            valid_points = ~np.isnan(lon[i]) & ~np.isnan(lat[i])
            tracks[tel_code] = np.column_stack((lon[i, valid_points], lat[i, valid_points]))  # shape: (n_valid_times, 2)

        if not tracks:
            logger.warning(f"No valid Mollweide tracks computed for scan '{scan_name}'")
        else:
            logger.debug(f"Computed Mollweide tracks for {len(tracks)} telescopes in scan '{scan_name}'")
        return {"source": source_name, "tracks": tracks}
    
    def _compute_mollweide_coords_from_position(self, position: np.ndarray, time: Time) -> np.ndarray:
        """Compute Mollweide coordinates from GCRS position array in J2000.

        Args:
            position (np.ndarray): GCRS positions (x, y, z) in meters, shape (n_times, 3).
            time (Time): Observation times (used for logging).

        Returns:
            np.ndarray: Mollweide coordinates (lon, lat) in degrees, shape (n_times, 2).

        Notes:
            - Vectorized to handle multiple positions at once.
            - Returns NaN for invalid positions (e.g., zero radius).
        """
        try:
            position = np.asarray(position, dtype=float)  # Ensure array input
            if position.ndim == 1:
                position = position[None, :]  # Add time dimension for single position
            if position.shape[-1] != 3:
                logger.error(f"Invalid position shape {position.shape} for Mollweide calculation")
                return np.full((position.shape[0], 2), np.nan)

            r = np.sqrt(np.sum(position**2, axis=1))  # shape: (n_times,)
            valid_mask = r > 0  # Avoid division by zero
            ra_rad = np.full(r.shape, np.nan)
            dec_rad = np.full(r.shape, np.nan)
            ra_rad[valid_mask] = np.arctan2(position[valid_mask, 1], position[valid_mask, 0])
            dec_rad[valid_mask] = np.arcsin(position[valid_mask, 2] / r[valid_mask])
            ra = np.degrees(ra_rad)  # shape: (n_times,)
            dec = np.degrees(dec_rad)  # shape: (n_times,)
            lon = np.where(ra > 180.0, ra - 360.0, ra)  # shape: (n_times,)
            lat = np.clip(dec, -90.0, 90.0)  # shape: (n_times,)
            result = np.column_stack((lon, lat))  # shape: (n_times, 2)

            if np.any(np.isnan(result)):
                logger.warning(f"Mollweide coordinates contain NaN values at time {time.isot}")
            return result
        except Exception as e:
            logger.error(f"Failed to compute Mollweide coordinates: {str(e)}")
            return np.full((position.shape[0], 2), np.nan)

    def _compute_mollweide_coords(self, coord: SkyCoord) -> Tuple[float, float]:
        """Compute coordinates for Mollweide projection in J2000.

        Args:
            coord (SkyCoord): Source coordinates.

        Returns:
            Tuple[float, float]: RA (in [-180, 180] degrees) and Dec (in [-90, 90] degrees).
        """
        ra = coord.ra.deg  # 0° to 360°
        dec = coord.dec.deg

        lon = ra
        if lon > 180.0:
            lon -= 360.0
        lat = np.clip(dec, -90.0, 90.0)

        return lon, lat

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
                # Логируем первые несколько временных меток для диагностики
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
            
            # Check for NaN in loaded data
            if np.any(np.isnan(positions)) or np.any(np.isnan(velocities)):
                logger.warning(f"Orbit file '{orbit_file}' contains NaN values")
                return {}
            
            orbit_data = {
                "times": times_sec,
                "positions": positions,
                "velocities": velocities
            }
            
            # Filter by time range if provided
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

    def _get_state_vector_from_kepler(self, telescope: SpaceTelescope, time: Time) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate state vector using Keplerian elements.

        Args:
            telescope (SpaceTelescope): The space telescope.
            time (Time): Time for state vector calculation.

        Returns:
            Tuple[np.ndarray, np.ndarray]: Position and velocity vectors in meters and m/s.
        """
        kepler = telescope.get("kepler_elements")
        if kepler is None:
            raise ValueError(f"No Keplerian elements defined for telescope '{telescope.get_code()}'")
        
        a = kepler["a"]  # semi-major axis (m)
        e = kepler["e"]  # eccentricity
        i = np.radians(kepler["i"])  # inclination (deg to rad)
        raan = np.radians(kepler["raan"])  # RA of ascending node (deg to rad)
        argp = np.radians(kepler["argp"])  # argument of periapsis (deg to rad)
        nu0 = np.radians(kepler["nu"])  # true anomaly at epoch (deg to rad)
        epoch = kepler["epoch"]
        mu = kepler["mu"]  # gravitational parameter (m^3/s^2)
        
        # Mean motion
        n = np.sqrt(mu / a**3)  # rad/s
        # Time since epoch
        dt = (time - epoch).sec
        # Mean anomaly
        M = nu0 + n * dt
        # Solve Kepler's equation for eccentric anomaly
        E = self._solve_kepler(M, e)
        # True anomaly
        cos_nu = (np.cos(E) - e) / (1 - e * np.cos(E))
        sin_nu = (np.sqrt(1 - e**2) * np.sin(E)) / (1 - e * np.cos(E))
        nu = np.arctan2(sin_nu, cos_nu)
        # Distance
        r = a * (1 - e**2) / (1 + e * np.cos(nu))
        # Position in orbital plane
        p = np.array([r * np.cos(nu), r * np.sin(nu), 0.0])
        # Velocity in orbital plane
        v = np.array([
            -np.sqrt(mu / (a * (1 - e**2))) * np.sin(nu),
            np.sqrt(mu / (a * (1 - e**2))) * (e + np.cos(nu)),
            0.0
        ])
        # Rotation matrices
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
        # Transform to GCRS
        pos = R @ p
        vel = R @ v
        logger.debug(f"Calculated Keplerian state vector for '{telescope.get_code()}' at {time.isot}: pos={pos}, vel={vel}")
        return pos, vel

    @time_execution
    def _calculate_interpolated_orbits(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate interpolated orbit data for active SpaceTelescopes in active scans.

        Args:
            obj (Observation | ScheduleProject): The object to calculate orbits for.
            attributes (Dict[str, Any]): Parameters including "time_step", "store_key", "recalculate".

        Returns:
            Dict[str, Any]: Interpolated orbit data as {scan_name: {spacetelescope_code: np.array([[x, y, z], ...])}}.

        Notes:
            - Interpolates orbits only for SpaceTelescopes that are active in scans and have orbit files.
            - Stores results under 'interpolated_orbits' key in calculated_data.
            - Preserves data with NaN values, logging a warning instead of excluding.
            - Returns empty dict if no active SpaceTelescopes are found.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "interpolated_orbits")
            recalculate = attributes.get("recalculate", False)
            excluded_telescopes = []

            def calculate_orbits(obj, attrs):
                if isinstance(obj, ScheduleProject):
                    observations = obj.get_items()
                    if not observations:
                        logger.warning(f"No observations in project '{obj.name}'")
                        return {}
                    results = {}
                    max_workers = min(len(observations), 4) if len(observations) > 1 else 1
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        futures = {
                            executor.submit(self._calculate_interpolated_orbits, obs, attrs): obs.get_observation_code()
                            for obs in observations
                        }
                        for future in futures:
                            obs_code = futures[future]
                            results[obs_code] = future.result()
                        logger.info(f"Calculated interpolated orbits for {len(observations)} observations in project '{obj.name}'")
                    return results

                # Get time arrays
                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": recalculate}
                time_data = self._calculate_time_arrays(obj, time_attrs)
                if not time_data:
                    logger.warning(f"No time arrays available for observation '{obj.get_observation_code()}'")
                    return {}

                scans = obj.get_scans().get_active_items()
                if not scans:
                    logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
                    return {}

                # Check for active SpaceTelescopes in observation and scans
                telescopes = obj.get_telescopes()
                active_space_telescopes = [
                    tel for tel in telescopes.get_active_items()
                    if isinstance(tel, SpaceTelescope) and not tel.get("use_kep")
                ]
                if not active_space_telescopes:
                    logger.info(f"No active SpaceTelescopes in observation '{obj.get_observation_code()}'")
                    return {}

                # Initialize results dictionary
                results = {scan.name: {} for scan in scans}

                with self._orbit_cache_lock:
                    for scan in scans:
                        scan_name = scan.name
                        source = scan.get_source(obj)
                        if not source or not source.isactive:
                            logger.debug(f"Skipping scan '{scan_name}' due to inactive or missing source")
                            continue
                        scan_times = time_data.get(source.name, {}).get(scan_name, None)
                        if scan_times is None or not isinstance(scan_times, Time) or scan_times.size == 0:
                            logger.warning(f"No valid times for scan '{scan_name}' in source '{source.name}'")
                            continue

                        scan_telescopes = scan.get_telescopes(obj).get_active_items()
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
                                orbit_data = self._interpolate_orbit(tel, scan_times, scan.get_start(), scan.get_start() + scan.get_duration() * u.s)
                                if "positions" in orbit_data:
                                    results[scan_name][tel_code] = orbit_data["positions"]
                                    if np.any(np.isnan(orbit_data["positions"])):
                                        logger.warning(f"Orbit data for '{tel_code}' in scan '{scan_name}' contains NaN values")
                                else:
                                    logger.warning(f"No orbit data returned for '{tel_code}' in scan '{scan_name}'")
                                    excluded_telescopes.append(tel_code)
                            except ValueError as e:
                                logger.warning(f"Excluding telescope '{tel_code}' in scan '{scan_name}' due to interpolation error: {str(e)}")
                                excluded_telescopes.append(tel_code)

                if excluded_telescopes:
                    logger.info(f"Excluded {len(set(excluded_telescopes))} telescopes: {', '.join(set(excluded_telescopes))}")
                logger.debug(f"Calculated interpolated orbits for {len(results)} scans in '{obj.get_observation_code()}'")
                return results

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items())}
            return self._get_cached_or_calculate(obj, store_key, calculate_orbits, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate interpolated orbits: {str(e)}")
            return {}
        
    def _interpolate_orbit(self, telescope: SpaceTelescope, times: Time, start_time: Time, end_time: Time) -> Dict[str, Any]:
        """Interpolate orbit data for a space telescope over a given array of times.

        Args:
            telescope (SpaceTelescope): The space telescope.
            times (Time): Array of times for interpolation (must have scale='utc').
            start_time (Time): Start time of the required range (for validation, must have scale='utc').
            end_time (Time): End time of the required range (for validation, must have scale='utc').

        Returns:
            Dict[str, Any]: Interpolated orbit data with positions as np.array([[x, y, z], ...]). Includes NaN values with a warning.

        Notes:
            - Uses the provided times array directly for interpolation.
            - If orbit data partially covers the time range, interpolates only for the available portion.
            - Logs a warning if interpolated data contains NaN values.
        """
        if telescope.get("use_kep"):
            logger.info(f"Skipping interpolation for '{telescope.get_code()}' as use_kep=True")
            return {}

        orbit_file = telescope.get_orbit()
        if not orbit_file:
            logger.warning(f"No orbit file defined for telescope '{telescope.get_code()}'")
            return {}

        try:
            # Ensure times are in UTC
            if times.scale != 'utc':
                logger.debug(f"Converting times from scale '{times.scale}' to 'utc' for '{telescope.get_code()}'")
                times = times.utc
            if start_time.scale != 'utc':
                logger.debug(f"Converting start_time from scale '{start_time.scale}' to 'utc' for '{telescope.get_code()}'")
                start_time = start_time.utc
            if end_time.scale != 'utc':
                logger.debug(f"Converting end_time from scale '{end_time.scale}' to 'utc' for '{telescope.get_code()}'")
                end_time = end_time.utc

            # Log input times for diagnostics
            logger.debug(f"Input times for '{telescope.get_code()}': scale={times.scale}, sample={times.isot[:3]}")
            logger.debug(f"Start time: {start_time.isot}, End time: {end_time.isot}")

            # Validate MJD values
            mjd_values = times.mjd
            if np.any(np.isnan(mjd_values)) or np.any(np.isinf(mjd_values)):
                logger.error(f"Invalid MJD values in times for '{telescope.get_code()}': {mjd_values}")
                return {}

            # Check date range (1900–9999 years)
            years = times.ymdhms['year']
            if np.any(years < 1900) or np.any(years > 9999):
                logger.error(f"Times out of valid range (1900–9999) for '{telescope.get_code()}': years={years}")
                return {}

            # Load orbit data
            orbit_data = self._load_orbit_data(orbit_file, start_time, end_time)
            if not orbit_data:
                logger.warning(f"No valid orbit data for '{telescope.get_code()}' in time range {start_time.isot} to {end_time.isot}")
                return {}
            data_times = orbit_data["times"]
            positions = orbit_data["positions"]

            # Compute interpolation times in seconds since J2000
            j2000_mjd = Time("2000-01-01T12:00:00", scale='utc').mjd
            try:
                interp_times = (mjd_values - j2000_mjd) * 86400.0  # Convert MJD to seconds since J2000
                logger.debug(f"Computed interp_times for '{telescope.get_code()}': sample={interp_times[:3]}")
            except Exception as e:
                logger.error(f"Error converting MJD to seconds since J2000 for '{telescope.get_code()}': {str(e)}")
                return {}

            # Determine overlapping time range
            data_start = data_times[0]
            data_end = data_times[-1]
            t_start = (start_time.mjd - j2000_mjd) * 86400.0
            t_end = (end_time.mjd - j2000_mjd) * 86400.0

            # Adjust interpolation range to overlap with data
            t_start = max(t_start, data_times[0])
            t_end = min(t_end, data_times[-1])
            valid_mask = (interp_times >= t_start) & (interp_times <= t_end)
            valid_interp_times = interp_times[valid_mask]
            valid_times = times[valid_mask]

            if not valid_interp_times.size:
                logger.warning(f"No valid interpolation times for '{telescope.get_code()}' in range {Time(t_start / 86400.0 + j2000_mjd, format='mjd', scale='utc').isot} to {Time(t_end / 86400.0 + j2000_mjd, format='mjd', scale='utc').isot}")
                return {}

            # Filter and ensure unique times in orbit data
            unique_indices = np.unique(data_times, return_index=True)[1]
            filtered_times = data_times[unique_indices]
            filtered_positions = positions[unique_indices]

            if len(filtered_times) < 2:
                logger.warning(f"Too few points ({len(filtered_times)}) for interpolation for '{telescope.get_code()}'")
                return {}

            # Initialize arrays for full requested time range
            full_positions = np.full((len(times), 3), np.nan, dtype=float)

            # Interpolate
            method = telescope.get("interpolation_method") or "linear"
            logger.debug(f"Using interpolation method '{method}' for '{telescope.get_code()}'")
            if method == "chebyshev":
                degree = min(30, len(filtered_times) - 1)  # Adjust degree based on data points
                norm_times = 2 * (filtered_times - t_start) / (t_end - t_start) - 1
                norm_interp_times = 2 * (valid_interp_times - t_start) / (t_end - t_start) - 1
                pos_polynomials = [chebyshev.Chebyshev.fit(norm_times, pos, degree) for pos in filtered_positions.T]
                full_positions[valid_mask] = np.array([poly(norm_interp_times) for poly in pos_polynomials]).T
            elif method == "cubic_spline":
                full_positions[valid_mask] = np.array([CubicSpline(filtered_times, pos)(valid_interp_times) for pos in filtered_positions.T]).T
            else:  # linear
                # Ensure extrapolation is disabled by clamping to data bounds
                full_positions[valid_mask] = np.array([
                    np.interp(valid_interp_times, filtered_times, pos, left=np.nan, right=np.nan)
                    for pos in filtered_positions.T
                ]).T

            # Log warning if interpolated data contains NaN
            if np.any(np.isnan(full_positions)):
                logger.warning(f"Interpolated positions for '{telescope.get_code()}' contain NaN values in range {Time(t_start / 86400.0 + j2000_mjd, format='mjd', scale='utc').isot} to {Time(t_end / 86400.0 + j2000_mjd, format='mjd', scale='utc').isot}")

            logger.info(f"Interpolated orbit for '{telescope.get_code()}' using {method} with {len(valid_interp_times)} points")
            return {"positions": full_positions}

        except Exception as e:
            logger.error(f"Failed to interpolate orbit for '{telescope.get_code()}': {str(e)}")
            return {}