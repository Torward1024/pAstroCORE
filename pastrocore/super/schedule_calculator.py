from abc import ABC
from common.super.super import Super
from common.utils.logging_setup import logger

from pastrocore.base.frequencies import Frequencies
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
    def _calculate_source_visibility(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate source visibility for all scans.

        args:
            obj (Observation | ScheduleProject): the object to calculate visibility for.
            attributes (Dict[str, Any]): parameters including "time_step", "store_key", and "position_store_key".

        returns:
            Dict[str, Any]: visibility data per scan, keyed by observation code (for Project) or scan index (for Observation).

        notes:
            - depends on precomputed telescope positions.
            - uses parallel processing for multiple scans.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "source_visibility")
            position_store_key = attributes.get("position_store_key", "telescope_positions")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"no observations in project '{obj.name}'")
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
                logger.info(f"calculated source visibility for {len(observations)} observations in project '{obj.name}'")
                return results

            def calculate_visibility(obj, attrs):
                scans = obj.get_scans().get_active_items()
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": attrs.get("recalculate")}
                position_data = self._calculate_telescope_positions(obj, position_attrs)
                if not position_data:
                    logger.error(f"failed to obtain telescope positions for '{obj.get_observation_code()}'")
                    return {}
                results = {}
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_source_visibility, scan, obj, time_step, position_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        results[scan_name] = future.result()
                return results

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items())}
            return self._get_cached_or_calculate(obj, store_key, calculate_visibility, attributes, metadata)
        except Exception as e:
            logger.error(f"failed to calculate source visibility: {str(e)}")
            return {}
        
    def _process_source_visibility(self, scan: Scan, observation: Observation, time_step: Optional[float], position_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process source visibility for a single scan.

        Args:
            scan (Scan): The scan to process.
            telescopes (Telescopes): Collection of telescopes.
            sources (Sources): Collection of sources.
            time_step (Optional[float]): Time interval for sampling (seconds).
            position_data (Dict[str, Any]): Precomputed telescope positions.
            observation (Observation): The parent observation.

        Returns:
            Dict[str, Any]: Visibility data including source name and visibility per telescope.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        source = scan.get_source(observation)
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs') if source else None
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        scan_name = scan.name

        logger.debug(f"Processing visibility for scan {scan_name}: {len(active_telescopes)} telescopes")

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            positions = position_data.get(scan_name, {}).get("telescope_positions", {})
            visibility = self._compute_visibility_at_time(source, active_telescopes, mean_time, positions) if source else {tel.get_code(): False for tel in active_telescopes}
            # Convert boolean values to numpy array for consistency
            visibility_array = np.array([visibility[tel.get_code()] for tel in active_telescopes], dtype=bool)
            visibility_dict = {tel.get_code(): visibility_array[i] for i, tel in enumerate(active_telescopes)}
            return {"source": source.name if source else None, "visibility": visibility_dict}
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
            positions = position_data.get(scan_name, {}).get("telescope_positions", {})
            
            # Initialize visibility array: shape (n_telescopes, n_times)
            visibility = np.zeros((len(active_telescopes), len(times)), dtype=bool)
            pos_arrays = {}
            for i, tel in enumerate(active_telescopes):
                tel_code = tel.get_code()
                pos_data = positions.get(tel_code, {})
                pos_array = np.array(pos_data.get("positions", [])) if "positions" in pos_data else None
                if pos_array is None or len(pos_array) != len(times):
                    logger.warning(f"No or mismatched position data for telescope '{tel_code}' in scan {scan_name}")
                    visibility[i] = False
                else:
                    pos_arrays[tel_code] = pos_array

            if source_coord:
                for i, tel in enumerate(active_telescopes):
                    tel_code = tel.get_code()
                    if tel_code not in pos_arrays:
                        continue
                    pos_array = pos_arrays[tel_code]
                    
                    if isinstance(tel, SpaceTelescope):
                        # itrs = ITRS(CartesianRepresentation(pos_array[:, 0], pos_array[:, 1], pos_array[:, 2], unit=u.m), obstime=times)
                        # altaz = source_coord.transform_to(AltAz(obstime=times, location=itrs.earth_location))
                        # pitch = altaz.alt.deg
                        # yaw = altaz.az.deg
                        # pitch_range = tel.get_pitch_range()
                        # yaw_range = tel.get_yaw_range()
                        
                        # pitch_lower = np.asarray(float(pitch_range[0]) <= pitch, dtype=bool)
                        # pitch_upper = np.asarray(pitch <= float(pitch_range[1]), dtype=bool)
                        # yaw_lower = np.asarray(float(yaw_range[0]) <= yaw, dtype=bool)
                        # yaw_upper = np.asarray(yaw <= float(yaw_range[1]), dtype=bool)
                        # is_visible = pitch_lower & pitch_upper & yaw_lower & yaw_upper
                        visibility[i] = True # is_visible
                    else:
                        gcrs = GCRS(CartesianRepresentation(pos_array[:, 0], pos_array[:, 1], pos_array[:, 2], unit=u.m), obstime=times)
                        itrs = gcrs.transform_to(ITRS(obstime=times))
                        location = itrs.earth_location
                        altaz = source_coord.transform_to(AltAz(obstime=times, location=location))
                        el = altaz.alt.deg
                        az = altaz.az.deg
                        mount_type = tel.get("mount_type")
                        if mount_type.value == "AZIM":
                            el_range = tel.get_elevation_range()
                            az_range = tel.get_azimuth_range()
                            el_lower = np.asarray(float(el_range[0]) <= el, dtype=bool)
                            el_upper = np.asarray(el <= float(el_range[1]), dtype=bool)
                            az_lower = np.asarray(float(az_range[0]) <= az, dtype=bool)
                            az_upper = np.asarray(az <= float(az_range[1]), dtype=bool)
                            is_visible = el_lower & el_upper & az_lower & az_upper
                        elif mount_type.value == "EQUA":
                            hadec = source_coord.transform_to(HADec(obstime=times, location=location))
                            ha = hadec.ha.deg
                            dec = hadec.dec.deg
                            ha_range = tel.get_azimuth_range()
                            dec_range = tel.get_elevation_range()

                            dec_lower = np.asarray(float(dec_range[0]) <= dec, dtype=bool)
                            dec_upper = np.asarray(dec <= float(dec_range[1]), dtype=bool)
                            ha_lower = np.asarray(float(ha_range[0]) <= ha, dtype=bool)
                            ha_upper = np.asarray(ha <= float(ha_range[1]), dtype=bool)
                            is_visible = dec_lower & dec_upper & ha_lower & ha_upper
                        else:
                            logger.debug(f"Unsupported mount type {mount_type.value} for telescope '{tel_code}'")
                            is_visible = np.zeros(len(times), dtype=bool)
                        visibility[i] = is_visible

            # Convert visibility array to dictionary for compatibility with visualizer
            visibility_dict = {tel.get_code(): visibility[i].tolist() for i, tel in enumerate(active_telescopes)}
            return {"source": source.name if source else None, "times": times.isot.tolist(), "visibility": visibility_dict}
    

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
    def _calculate_telescope_positions(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate telescope positions in GCRS (J2000) for all scans or time range.

        Args:
            obj (Observation | ScheduleProject): The object to calculate positions for.
            attributes (Dict[str, Any]): Parameters including "time_step", "start_time", "end_time".

        Returns:
            Dict[str, Any]: Telescope positions per scan or time range, keyed by index.

        Notes:
            - If a space telescope's orbit does not cover the requested time range, a warning is logged, and it is excluded.
            - If an orbit covers only part of the time range, positions are calculated for the available portion.
        """
        try:
            results = {}
            time_step = attributes.get("time_step")
            start_time = attributes.get("start_time")
            end_time = attributes.get("end_time")
            store_key = attributes.get("store_key", "telescope_positions")
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

                telescopes = obj.get_telescopes()
                active_telescopes = telescopes.get_active_items()
                if not active_telescopes:
                    logger.warning(f"No active telescopes in observation '{obj.get_observation_code()}'")
                    return {}

                if start_time and end_time:
                    start = Time(start_time)
                    end = Time(end_time)
                    use_scans = False
                else:
                    scans = obj.get_scans().get_active_items()
                    if not scans:
                        logger.warning(f"No scans or time range specified in observation '{obj.get_observation_code()}'")
                        return {}
                    start_times = [scan.get_start() for scan in scans]
                    end_times = [scan.get_start() + scan.get_duration() * u.s for scan in scans]
                    start = min(start_times)
                    end = max(end_times)
                    use_scans = True

                time_values = np.arange(0, (end - start).sec, time_step) * u.s if time_step else [((end - start).sec / 2) * u.s]
                times = Time(start.mjd + time_values.to(u.d).value, format='mjd')
                logger.debug(f"Calculating telescope positions for {len(times)} time points from {start.isot} to {end.isot}")

                # Load and interpolate orbits for SpaceTelescopes
                with self._orbit_cache_lock:
                    for tel in active_telescopes:
                        if isinstance(tel, SpaceTelescope) and time_step and not tel.get("use_kep"):
                            orbit_file = tel.get_orbit()
                            if orbit_file:
                                try:
                                    orbit_data = self._load_orbit_data(orbit_file, start, end)
                                    self._orbit_cache[tel.get_code()] = self._interpolate_orbit(tel, start, end, time_step)
                                except ValueError as e:
                                    logger.warning(f"Excluding telescope '{tel.get_code()}' due to unavailable orbit data: {str(e)}")
                                    self._orbit_cache[tel.get_code()] = {}
                                    excluded_telescopes.append(tel.get_code())
                            else:
                                logger.warning(f"No orbit file for telescope '{tel.get_code()}'; excluding from calculations")
                                self._orbit_cache[tel.get_code()] = {}
                                excluded_telescopes.append(tel.get_code())

                # Filter out excluded telescopes
                active_telescopes = [tel for tel in active_telescopes if tel.get_code() not in excluded_telescopes]
                if not active_telescopes:
                    logger.warning(f"All telescopes excluded for observation '{obj.get_observation_code()}'")
                    return {}

                results = {}
                if use_scans and time_step:
                    for scan in scans:
                        scan_start = scan.get_start()
                        scan_duration = scan.get_duration()
                        scan_times = times[(scan_start <= times) & (times <= scan_start + scan_duration * u.s)]
                        if not scan_times:
                            continue
                        scan_positions = self._process_scan_positions(scan, obj, time_step)
                        results[scan.name] = scan_positions
                else:
                    tel_positions = {}
                    for tel in active_telescopes:
                        positions = []
                        for t in times:
                            try:
                                pos = self._compute_telescope_position(tel, t)
                                positions.append(pos)
                            except ValueError as e:
                                logger.warning(f"Position calculation failed for telescope '{tel.get_code()}' at {t.isot}: {str(e)}")
                                positions.append([None, None, None])
                        tel_positions[tel.get_code()] = {
                            "times": [t.isot for t in times],
                            "positions": [p if p is not None else [None, None, None] for p in positions]
                        }
                    results[0] = {"telescope_positions": tel_positions}

                # Clear orbit cache after calculations
                with self._orbit_cache_lock:
                    self._orbit_cache.clear()
                    logger.info("Cleared orbit cache after telescope position calculations")

                if excluded_telescopes:
                    logger.info(f"Excluded {len(excluded_telescopes)} telescopes due to unavailable orbit data: {', '.join(excluded_telescopes)}")
                logger.debug(f"Calculated telescope positions for {len(results)} entries in '{obj.get_observation_code()}'")
                return results

            metadata = {"time_step": time_step, "start_time": start_time, "end_time": end_time}
            return self._get_cached_or_calculate(obj, store_key, calculate_positions, attributes, metadata)
        except Exception as e:
            logger.warning(f"Partial failure in calculating telescope positions: {str(e)}. Returning available data.")
            return results

    def _process_scan_positions(self, scan: Scan, observation: Observation, time_step: Optional[float]) -> Dict[str, Any]:
        """Process telescope positions for a single scan.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Time interval for position sampling (seconds).

        Returns:
            Dict[str, Any]: Positions for active telescopes, with times if time_step is provided.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [tel for tel in scan_telescopes.get_items() if tel.isactive]
        scan_name = scan.name

        if not active_telescopes:
            logger.warning(f"No active telescopes for scan {scan_name} starting at {start_time.isot}")
            return {"telescope_positions": {}}

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            positions = {}
            for tel in active_telescopes:
                pos = self._compute_telescope_position(tel, mean_time)
                positions[tel.get_code()] = pos
            pos_array = np.array(list(positions.values()), dtype=float)  # Преобразуем в массив float
            return {"telescope_positions": {tel.get_code(): pos_array[i].tolist() for i, tel in enumerate(active_telescopes)}}
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
            result = {}
            for tel in active_telescopes:
                positions = []
                for t in times:
                    pos = self._compute_telescope_position(tel, t)
                    positions.append(pos)
                result[tel.get_code()] = {
                    "times": times.isot.tolist(),
                    "positions": np.array(positions, dtype=float).tolist()  # Преобразуем в массив float
                }
            return {"telescope_positions": result}

    def _compute_telescope_position(self, telescope: Telescope | SpaceTelescope, time: Time) -> Tuple[float, float, float]:
        """Compute a telescope's GCRS position at a specific time.

        Args:
            telescope (Telescope | SpaceTelescope): The telescope to compute position for.
            time (Time): The time of calculation.

        Returns:
            Tuple[float, float, float]: GCRS coordinates (x, y, z) in meters, or (np.nan, np.nan, np.nan) if computation fails.
        """
        try:
            if isinstance(telescope, Telescope) and not isinstance(telescope, SpaceTelescope):
                x, y, z = telescope.get_coordinates()
                res = telescope.get(["vx", "vy", "vz"])
                vx, vy, vz = res["vx"], res["vy"], res["vz"]
                dt = (time - Time("2000-01-01T12:00:00")).sec
                itrs_coords = CartesianRepresentation(x + vx * dt, y + vy * dt, z + vz * dt, unit=u.m)
                itrs = ITRS(itrs_coords, obstime=time)
                gcrs = itrs.transform_to(GCRS(obstime=time))
                pos = (gcrs.cartesian.x.value, gcrs.cartesian.y.value, gcrs.cartesian.z.value)
                if any(np.isnan(pos)):
                    logger.warning(f"Computed NaN position for ground telescope '{telescope.get_code()}' at {time.isot}")
                return pos
            elif isinstance(telescope, SpaceTelescope):
                if telescope.get("use_kep"):
                    try:
                        pos, _ = self._get_state_vector_from_kepler(telescope, time)
                        pos = tuple(float(p) for p in pos)
                        if any(np.isnan(pos)):
                            logger.warning(f"Keplerian position for '{telescope.get_code()}' at {time.isot} contains NaN")
                        return pos
                    except ValueError as e:
                        logger.warning(f"Failed to compute Keplerian position for '{telescope.get_code()}' at {time.isot}: {str(e)}")
                        return (np.nan, np.nan, np.nan)
                else:
                    with self._orbit_cache_lock:
                        if telescope.get_code() in self._orbit_cache and self._orbit_cache[telescope.get_code()]:
                            try:
                                pos, _ = self._get_state_vector_from_cached_orbit(telescope, time, self._orbit_cache[telescope.get_code()])
                                pos = tuple(float(p) for p in pos)
                                if any(np.isnan(pos)):
                                    logger.warning(f"Cached orbit position for '{telescope.get_code()}' at {time.isot} contains NaN")
                                return pos
                            except ValueError as e:
                                logger.warning(f"Failed to compute position from cached orbit for '{telescope.get_code()}' at {time.isot}: {str(e)}")
                                return (np.nan, np.nan, np.nan)
                        else:
                            try:
                                pos, _ = self._get_state_vector_from_orbit(telescope, time)
                                pos = tuple(float(p) for p in pos)
                                if any(np.isnan(pos)):
                                    logger.warning(f"Orbit file position for '{telescope.get_code()}' at {time.isot} contains NaN")
                                return pos
                            except ValueError as e:
                                logger.warning(f"Failed to compute position from orbit file for '{telescope.get_code()}' at {time.isot}: {str(e)}")
                                return (np.nan, np.nan, np.nan)
            raise ValueError(f"Unsupported telescope type: {type(telescope)}")
        except Exception as e:
            logger.warning(f"Unexpected error in computing position for '{telescope.get_code()}' at {time.isot}: {str(e)}")
            return (np.nan, np.nan, np.nan)
    
    @time_execution
    def _calculate_uv_coverage(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate (u,v,w) coverage for all scans in the observation or project in geometric coordinates (meters).

        Args:
            obj (Observation | ScheduleProject): The object to calculate UV coverage for.
            attributes (Dict[str, Any]): Parameters including "time_step" and "store_key".

        Returns:
            Dict[str, Any]: UV coverage data per scan, including u, v, w coordinates in meters.
                    Format: {scan_name: {"times": [ISO times], "uv_points": {time_idx: {pair: (u, v, w)}}}}

        Notes:
            - Calculates UV coordinates in meters without frequency scaling.
            - The 'freq_name' attribute, if provided, is ignored and logged for compatibility.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "uv_coverage")

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
                results = {}

                visibility_attrs = {"time_step": time_step, "store_key": "source_visibility", "recalculate": attrs.get("recalculate", False)}
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": attrs.get("recalculate", False)}

                visibility_data = self._calculate_source_visibility(obj, visibility_attrs)
                position_data = self._calculate_telescope_positions(obj, position_attrs)
                
                if not visibility_data or not position_data:
                    logger.error(f"Missing visibility or position data for '{obj.get_observation_code()}'")
                    return {}

                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_uv_coverage, scan, obj, time_step, visibility_data, position_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        results[scan_name] = future.result()
                return results

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items())}
            return self._get_cached_or_calculate(obj, store_key, calculate_uv, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate (u,v,w) coverage: {str(e)}")
            return {}

    def _process_uv_coverage(self, scan: Scan, observation: Observation, time_step: Optional[float], visibility_data: Dict[str, Any], position_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process UV coverage for a single scan using vectorized computations in geometric coordinates (meters).

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds).
            visibility_data (Dict[str, Any]): Precomputed visibility data.
            position_data (Dict[str, Any]): Precomputed position data.

        Returns:
            Dict[str, Any]: UV points in meters, organized as {time_idx: {pair: (u, v, w)}}.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        source = scan.get_source(observation)
        scan_name = scan.name

        if len(active_telescopes) < 2:
            logger.warning(f"Insufficient telescopes ({len(active_telescopes)}) for UV coverage in scan {scan_name}")
            return {"times": [], "uv_points": {}} if time_step else {"uv_points": {}}

        # Define time array
        if time_step is None:
            times = Time(start_time + (duration / 2) * u.s)
            times = times.reshape(-1)  # Ensure 1D array
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')

        # Collect visibility and position data
        scan_visibility = visibility_data.get(scan_name, {}).get("visibility", {})
        scan_positions = position_data.get(scan_name, {}).get("telescope_positions", {})
        
        if not scan_visibility or not scan_positions:
            logger.warning(f"No visibility or position data for scan {scan_name}")
            return {"times": times.isot.tolist(), "uv_points": {}} if time_step else {"uv_points": {}}

        # Prepare arrays
        tel_codes = [tel.get_code() for tel in active_telescopes]
        visibility = np.array([scan_visibility.get(code, [False] * len(times)) for code in tel_codes], dtype=bool)  # shape: (n_tels, n_times)
        positions = np.array([scan_positions.get(code, {}).get("positions", [[]] * len(times))[0:len(times)] for code in tel_codes])  # shape: (n_tels, n_times, 3)

        if positions.shape[1] != len(times):
            logger.warning(f"Mismatched position data length for scan {scan_name}")
            return {"times": times.isot.tolist(), "uv_points": {}} if time_step else {"uv_points": {}}

        uv_points = self._compute_uv_at_time(active_telescopes, times, source, visibility, positions)
        formatted_uv_points = {t_idx: {} for t_idx in range(len(times))}
        for time_idx, points in enumerate(uv_points):
            for pair, uuu, vvv, www in points:
                formatted_uv_points[time_idx][pair] = (uuu, vvv, www)
        result = {"uv_points": formatted_uv_points}
        if time_step is not None:
            result["times"] = times.isot.tolist()
        return result

    def _compute_uv_at_time(self, telescopes: List[Telescope | SpaceTelescope], times: Time, source: Optional[Source] = None, visibility: Optional[np.ndarray] = None, gcrs_positions: Optional[np.ndarray] = None) -> List[List[Tuple[str, float, float, float]]]:
        """Compute UVW coordinates for multiple times in geometric coordinates (meters).

        Args:
            telescopes (List[Telescope | SpaceTelescope]): List of telescopes.
            times (Time): Array of observation times.
            source (Optional[Source]): Source for UV calculation.
            visibility (Optional[np.ndarray]): Visibility array of shape (n_telescopes, n_times).
            gcrs_positions (Optional[np.ndarray]): GCRS positions of shape (n_telescopes, n_times, 3).

        Returns:
            List[List[Tuple[str, float, float, float]]]: List of UVW coordinates in meters per time index, each containing tuples of (pair, u, v, w).
        """
        uv_points = [[] for _ in range(len(times))]
        if not telescopes or len(telescopes) < 2:
            logger.warning(f"Insufficient telescopes ({len(telescopes)}) to compute (u,v,w) at {times[0].isot}")
            return uv_points

        if source is None:
            logger.warning("No source provided; cannot calculate (u,v,w)")
            return uv_points

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

        # Compute baselines
        n_tels = len(telescopes)
        n_times = len(times)
        baselines = np.zeros((n_tels, n_tels, n_times, 3))
        for i in range(n_tels):
            for j in range(i + 1, n_tels):
                baselines[i, j] = gcrs_positions[i] - gcrs_positions[j]
                baselines[j, i] = -baselines[i, j]

        # Compute UVW coordinates in meters
        X, Y, Z = baselines[:, :, :, 0], baselines[:, :, :, 1], baselines[:, :, :, 2]
        uu = -np.sin(ra) * X + np.cos(ra) * Y
        vv = -np.cos(ra) * np.sin(dec) * X - np.sin(ra) * np.sin(dec) * Y + np.cos(dec) * Z
        ww = np.cos(ra) * np.cos(dec) * X + np.sin(ra) * np.cos(dec) * Y + np.sin(dec) * Z

        # Apply visibility mask
        vis_mask = visibility[:, None, :] & visibility[None, :, :]  # shape: (n_tels, n_times)

        # Collect UV points
        uvw = np.stack([uu, vv, ww], axis=-1)  # shape: (n_tels, n_tels, n_times, 3)
        for time_idx in range(n_times):
            for i in range(n_tels):
                for j in range(i + 1, n_tels):
                    if vis_mask[i, j, time_idx]:
                        pair = f"{telescopes[i].get_code()}-{telescopes[j].get_code()}"
                        uuu, vvv, www = uvw[i, j, time_idx]
                        uv_points[time_idx].append((pair, float(uuu), float(vvv), float(www)))
                        logger.debug(f"UV point for {pair} at time_idx {time_idx}: u={uuu}, v={vvv}, w={www}")

        return uv_points

    @time_execution
    def _calculate_sun_angles(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """calculate angular separation between source and Sun for all scans.

        args:
            obj (Observation | ScheduleProject): the object to calculate sun angles for.
            attributes (Dict[str, Any]): parameters including "time_step" and "store_key".

        returns:
            Dict[str, Any]: sun angles per scan, keyed by scan index or observation code.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "sun_angles")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"no observations in project '{obj.name}'")
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
                logger.info(f"calculated sun angles for {len(observations)} observations in project '{obj.name}'")
                return results

            def calculate_sun_angles(obj, attrs):
                scans = obj.get_scans().get_active_items()
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": attrs.get("recalculate", False)}
                position_data = self._calculate_telescope_positions(obj, position_attrs)
                if not position_data:
                    logger.error(f"failed to obtain telescope positions for '{obj.get_observation_code()}'")
                    return {}
                results = {}
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_sun_angles, scan, obj, time_step, position_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        results[scan_name] = future.result()
                return results

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items())}
            return self._get_cached_or_calculate(obj, store_key, calculate_sun_angles, attributes, metadata)
        except Exception as e:
            logger.error(f"failed to calculate sun angles: {str(e)}")
            return {}

    def _process_sun_angles(self, scan: Scan, observation: Observation, time_step: Optional[float], position_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process sun angles for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            sources (Sources): Collection of sources.
            telescopes (Telescopes): Collection of telescopes.
            time_step (Optional[float]): Sampling interval (seconds). If None, uses mean time.
            position_data (Dict[str, Any]): Precomputed telescope positions.

        Returns:
            Dict[str, Any]: Sun angles per telescope, with times if sampled.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        source = scan.get_source(observation)
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs') if source else None
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        scan_name = scan.name

        # Define time array
        if time_step is None:
            times = Time(start_time + (duration / 2) * u.s)
            times = times.reshape(-1)  # Ensure 1D array for consistency
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')

        # Split telescopes into ground and space
        ground_tels = [tel for tel in active_telescopes if not isinstance(tel, SpaceTelescope)]
        space_tels = [tel for tel in active_telescopes if isinstance(tel, SpaceTelescope)]

        # Initialize angles array
        angles = np.full((len(active_telescopes), len(times)), np.nan, dtype=float)
        scan_positions = position_data.get(scan_name, {}).get("telescope_positions", {})

        # Process ground telescopes
        if ground_tels and source_coord:
            # Vectorized computation of ITRS coordinates
            ground_codes = [tel.get_code() for tel in ground_tels]
            x = np.array([tel.get_coordinates()[0] for tel in ground_tels])
            y = np.array([tel.get_coordinates()[1] for tel in ground_tels])
            z = np.array([tel.get_coordinates()[2] for tel in ground_tels])
            vx = np.array([tel.get(["vx", "vy", "vz"])["vx"] for tel in ground_tels])
            vy = np.array([tel.get(["vx", "vy", "vz"])["vy"] for tel in ground_tels])
            vz = np.array([tel.get(["vx", "vy", "vz"])["vz"] for tel in ground_tels])
            dt = (times - Time("2000-01-01T12:00:00")).sec
            itrs_coords = CartesianRepresentation(
                x[:, None] + vx[:, None] * dt,
                y[:, None] + vy[:, None] * dt,
                z[:, None] + vz[:, None] * dt,
                unit=u.m
            )
            itrs = ITRS(itrs_coords, obstime=times)
            locations = itrs.earth_location

            # Transform source and Sun to AltAz
            altaz_frame = AltAz(obstime=times, location=locations)
            source_altaz = source_coord.transform_to(altaz_frame)
            sun_gcrs = get_sun(times)
            sun_altaz = sun_gcrs.transform_to(altaz_frame)

            # Compute separations
            separations = source_altaz.separation(sun_altaz).deg
            separations = np.where((source_altaz.alt.deg < 0) | (sun_altaz.alt.deg < 0), np.nan, separations)

            # Assign results
            for idx, tel_code in enumerate(ground_codes):
                tel_idx = [tel.get_code() for tel in active_telescopes].index(tel_code)
                angles[tel_idx] = separations[idx]

        # Process space telescopes
        if space_tels and source_coord:
            sun_gcrs = get_sun(times)
            sun_pos = np.array([
                sun_gcrs.cartesian.x.to(u.m).value,
                sun_gcrs.cartesian.y.to(u.m).value,
                sun_gcrs.cartesian.z.to(u.m).value
            ]).T  # shape: (n_times, 3)

            source_icrs = source_coord.icrs
            source_dir = np.array([
                source_icrs.cartesian.x.value,
                source_icrs.cartesian.y.value,
                source_icrs.cartesian.z.value
            ])
            source_dir /= np.linalg.norm(source_dir)  # normalize

            for tel in space_tels:
                tel_code = tel.get_code()
                tel_idx = [tel.get_code() for tel in active_telescopes].index(tel_code)
                pos_data = scan_positions.get(tel_code, {})
                positions = np.array(pos_data.get("positions", [])) if "positions" in pos_data else None
                if positions is None or len(positions) != len(times):
                    logger.warning(f"No or mismatched position data for telescope '{tel_code}' in scan {scan_name}")
                    continue

                # Vectorized computation
                vec_to_sun = sun_pos - positions  # shape: (n_times, 3)
                vec_to_sun /= np.linalg.norm(vec_to_sun, axis=1)[:, None]  # normalize each vector
                cos_angles = np.clip(np.dot(vec_to_sun, source_dir), -1.0, 1.0)
                tel_angles = np.degrees(np.arccos(cos_angles))
                angles[tel_idx] = tel_angles

        # Convert angles to dictionary for visualizer compatibility
        angles_dict = {tel.get_code(): angles[i].tolist() for i, tel in enumerate(active_telescopes)}

        # Format output
        result = {"source": source.name if source else None, "sun_angles": angles_dict}
        if time_step is not None:
            result["times"] = times.isot.tolist()
        return result

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
        """Calculate Az/El or HA/Dec for ground telescopes across all scans.

        Args:
            obj (Observation | ScheduleProject): The object to calculate coordinates for.
            attributes (Dict[str, Any]): Parameters including "time_step" and "store_key".

        Returns:
            Dict[str, Any]: Az/El or HA/Dec data per scan.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "az_el")

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
                logger.info(f"Calculated Az/El or HA/Dec for {len(observations)} observations in project '{obj.name}'")
                return results

            def calculate_az_el(obj, attrs):
                scans = obj.get_scans().get_active_items()
                results = {}
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_az_el, scan, obj, time_step): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        results[scan_name] = future.result()
                return results

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items())}
            return self._get_cached_or_calculate(obj, store_key, calculate_az_el, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate Az/El or HA/Dec: {str(e)}")
            return {}

    def _process_az_el(self, scan: Scan, observation: Observation, time_step: Optional[float]) -> Dict[str, Any]:
        """Process Az/El or HA/Dec for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            sources (Sources): Collection of sources.
            telescopes (Telescopes): Collection of telescopes.
            time_step (Optional[float]): Sampling interval (seconds). If None, uses mean time.

        Returns:
            Dict[str, Any]: Coordinate data per telescope, with times if sampled.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        source = scan.get_source(observation)
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs') if source else None
        scan_telescopes = scan.get_telescopes(observation)
        active_ground_tels = [tel for tel in scan_telescopes.get_items() if tel.isactive and not isinstance(tel, SpaceTelescope)]
        scan_name = scan.name

        if not active_ground_tels or not source_coord:
            logger.warning(f"No active ground telescopes or source for scan {scan_name} starting at {start_time.isot}")
            return {"source": source.name if source else None, "az_el": {}}

        # Define time array
        if time_step is None:
            times = Time(start_time + (duration / 2) * u.s)
            times = times.reshape(-1)  # Ensure 1D array for consistency
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')

        # Collect telescope properties
        tel_codes = [tel.get_code() for tel in active_ground_tels]
        mount_types = [tel.get("mount_type").value for tel in active_ground_tels]
        x = np.array([tel.get_coordinates()[0] for tel in active_ground_tels])
        y = np.array([tel.get_coordinates()[1] for tel in active_ground_tels])
        z = np.array([tel.get_coordinates()[2] for tel in active_ground_tels])
        vx = np.array([tel.get(["vx", "vy", "vz"])["vx"] for tel in active_ground_tels])
        vy = np.array([tel.get(["vx", "vy", "vz"])["vy"] for tel in active_ground_tels])
        vz = np.array([tel.get(["vx", "vy", "vz"])["vz"] for tel in active_ground_tels])
        az_ranges = np.array([tel.get_azimuth_range() for tel in active_ground_tels])  # [min, max]
        el_ranges = np.array([tel.get_elevation_range() for tel in active_ground_tels])  # [min, max]

        # Compute ITRS coordinates
        dt = (times - Time("2000-01-01T12:00:00")).sec
        itrs_coords = CartesianRepresentation(
            x[:, None] + vx[:, None] * dt,
            y[:, None] + vy[:, None] * dt,
            z[:, None] + vz[:, None] * dt,
            unit=u.m
        )
        itrs = ITRS(itrs_coords, obstime=times)
        locations = itrs.earth_location

        # Initialize result
        az_el = {code: {"coord1": [], "coord2": [], "coord_type": "AzEl" if mount == "AZIM" else "HADec"}
                for code, mount in zip(tel_codes, mount_types)}

        # Process AZIM mounts
        azim_mask = np.array([mount == "AZIM" for mount in mount_types])
        if azim_mask.any():
            azim_indices = np.where(azim_mask)[0]
            for idx in azim_indices:
                tel_code = tel_codes[idx]
                azim_location = locations[idx]
                altaz_frame = AltAz(obstime=times, location=azim_location)
                source_altaz = source_coord.transform_to(altaz_frame)
                az = source_altaz.az.deg
                el = source_altaz.alt.deg

                # Check ranges
                az_min, az_max = az_ranges[idx]
                el_min, el_max = el_ranges[idx]
                valid = (az_min <= az) & (az <= az_max) & (el_min <= el) & (el <= el_max)

                # Assign results
                coords = np.where(valid[:, None], np.vstack([az, el]).T, np.array([None, None]))
                az_el[tel_code]["coord1"] = coords[:, 0].tolist()
                az_el[tel_code]["coord2"] = coords[:, 1].tolist()

        # Process EQUA mounts
        equa_mask = np.array([mount == "EQUA" for mount in mount_types])
        if equa_mask.any():
            equa_indices = np.where(equa_mask)[0]
            for idx in equa_indices:
                tel_code = tel_codes[idx]
                equa_location = locations[idx]
                hadec_frame = HADec(obstime=times, location=equa_location)
                source_hadec = source_coord.transform_to(hadec_frame)
                ha = source_hadec.ha.deg
                dec = source_hadec.dec.deg

                # Check ranges
                ha_min, ha_max = az_ranges[idx]  # HA uses azimuth range
                dec_min, dec_max = el_ranges[idx]  # Dec uses elevation range
                valid = (ha_min <= ha) & (ha <= ha_max) & (dec_min <= dec) & (dec <= dec_max)

                # Assign results
                coords = np.where(valid[:, None], np.vstack([ha, dec]).T, np.array([None, None]))
                az_el[tel_code]["coord1"] = coords[:, 0].tolist()
                az_el[tel_code]["coord2"] = coords[:, 1].tolist()

        # Handle unsupported mount types
        for tel, code in zip(active_ground_tels, tel_codes):
            if mount_types[tel_codes.index(code)] not in ["AZIM", "EQUA"]:
                logger.warning(f"Unsupported mount type {tel.get('mount_type')} for telescope '{code}'")
                az_el[code]["coord1"] = [0.0] * len(times)
                az_el[code]["coord2"] = [0.0] * len(times)

        # Format output
        result = {"source": source.name if source else None, "az_el": az_el}
        if time_step is not None:
            result["times"] = times.isot.tolist()
        return result

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
        """Calculate total time on source for all scans.

        Args:
            obj (Observation | ScheduleProject): The object to calculate time for.
            attributes (Dict[str, Any]): Parameters including "time_step" and "store_key".

        Returns:
            Dict[str, Any]: Time on source per source and telescope.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "time_on_source")
            visibility_store_key = "source_visibility"

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_time_on_source(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"Calculated time on source for {len(observations)} observations in project '{obj.name}'")
                return results

            def calculate_time_on_source(obj, attrs):
                scans = obj.get_scans().get_active_items()
                sources = obj.get_sources()
                telescopes = obj.get_telescopes()
                visibility_data = self._calculate_source_visibility(obj, {
                    "time_step": time_step,
                    "store_key": visibility_store_key,
                    "recalculate": attrs.get("recalculate", False)
                })
                if not visibility_data:
                    logger.error(f"Failed to obtain visibility data for '{obj.get_observation_code()}'")
                    return {}

                results = {}
                with ThreadPoolExecutor() as executor:
                    futures = {
                        executor.submit(self._process_time_on_source, scan, obj, time_step, visibility_data): scan.name
                        for i, scan in enumerate(scans)
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        source_name = scan_result["source"]
                        if source_name not in results:
                            results[source_name] = {"telescopes": {}, "total_time": 0.0}
                        for tel_code, blocks in scan_result["visibility_blocks"].items():
                            if tel_code not in results[source_name]["telescopes"]:
                                results[source_name]["telescopes"][tel_code] = []
                            results[source_name]["telescopes"][tel_code].extend(blocks)
                            results[source_name]["total_time"] += sum(block["duration"] for block in blocks)
                return results

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items())}
            return self._get_cached_or_calculate(obj, store_key, calculate_time_on_source, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate time on source: {str(e)}")
            return {}
        
    def _process_time_on_source(self, scan: Scan, observation: Observation, time_step: float, visibility_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process time on source for a single scan.

        Args:
            scan (Scan): The scan to process.
            sources (Sources): Collection of sources.
            telescopes (Telescopes): Collection of telescopes.
            time_step (float): Sampling interval (seconds).
            visibility_data (Dict[str, Any]): Precomputed visibility data.
            observation (Observation): Parent observation.

        Returns:
            Dict[str, Any]: Visibility blocks per telescope.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        source = scan.get_source(observation)
        scan_name = scan.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]

        time_values = np.arange(0, duration, time_step) * u.s
        times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')

        scan_data = visibility_data.get(scan_name, {}) if isinstance(visibility_data, dict) else {}
        visibility = scan_data.get("visibility", {})
        if not visibility:
            logger.warning(f"No visibility data for scan {scan_name} in observation '{observation.get_observation_code()}'")
            return {"source": source.name if source else None, "visibility_blocks": {}}

        blocks = {tel.get_code(): [] for tel in active_telescopes}
        for tel in active_telescopes:
            tel_code = tel.get_code()
            vis = visibility.get(tel_code, [])
            if not vis:
                continue

            start_block = None
            for t_idx, is_visible in enumerate(vis):
                current_time = times[t_idx]
                if is_visible and start_block is None:
                    start_block = current_time
                elif not is_visible and start_block is not None:
                    end_block = times[t_idx - 1]
                    duration_block = (end_block - start_block).sec
                    blocks[tel_code].append({
                        "start": start_block.isot,
                        "end": end_block.isot,
                        "duration": duration_block
                    })
                    start_block = None

                if t_idx == len(vis) - 1 and start_block is not None:
                    end_block = current_time
                    duration_block = (end_block - start_block).sec
                    blocks[tel_code].append({
                        "start": start_block.isot,
                        "end": end_block.isot,
                        "duration": duration_block
                    })

        return {"source": source.name if source else None, "visibility_blocks": blocks}

    @time_execution
    def _calculate_beam_pattern(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """calculate beam pattern for single-dish observations.

        args:
            obj (Observation | ScheduleProject): the object to calculate beam pattern for.
            attributes (Dict[str, Any]): parameters including "freq_name" and "store_key".

        returns:
            Dict[str, Any]: beam pattern data per telescope.
        """
        try:
            freq_name = attributes.get("freq_name")
            store_key = attributes.get("store_key", f"beam_pattern_{freq_name}")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"no observations in project '{obj.name}'")
                    return {}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_beam_pattern(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"calculated beam pattern for {len(observations)} observations in project '{obj.name}'")
                return results

            if obj.get_observation_type() != "SINGLE_DISH":
                logger.warning(f"beam pattern calculation is only for SINGLE_DISH, got {obj.get_observation_type()}")
                return {}

            def calculate_beam_pattern(obj, attrs):
                telescopes = obj.get_telescopes().get_active_items()
                frequency = obj.get_frequencies().get(freq_name).get("frequency") * 1e6
                results = {}
                c = 299792458
                wavelength = c / frequency
                theta = np.linspace(-np.pi/2, np.pi/2, 5000)
                for tel in telescopes:
                    if isinstance(tel, SpaceTelescope):
                        continue
                    D = tel.get("diameter")
                    x = (np.pi * D / wavelength) * np.sin(theta)
                    pattern = (2 * j1(x) / x) ** 2
                    pattern = np.where(np.isnan(pattern), 1.0, pattern)
                    results[tel.get_code()] = {
                        "theta": theta.tolist(),
                        "pattern": pattern.tolist()  # convert to list for visualizer compatibility
                    }
                return results

            metadata = {"freq_name": freq_name}
            return self._get_cached_or_calculate(obj, store_key, calculate_beam_pattern, attributes, metadata)
        except Exception as e:
            logger.error(f"failed to calculate beam pattern: {str(e)}")
            return {}

    @time_execution
    def _calculate_synthesized_beam(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate synthesized beam for VLBI observations.

        Args:
            obj (Observation | ScheduleProject): The object to calculate synthesized beam for.
            attributes (Dict[str, Any]): Parameters including "freq_name", "time_step", and "store_key".

        Returns:
            Dict[str, Any]: Synthesized beam data per scan, formatted as {scan_name: {"theta_u": [...], "theta_v": [...], "beam_2d": [...]}}.

        Notes:
            - Expects UV data in meters from _calculate_uv_coverage.
            - Computes 2D FFT of UV plane to derive the synthesized beam.
            - Returns angles in degrees for visualizer compatibility.
        """
        try:
            freq_name = attributes.get("freq_name")
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", f"synthesized_beam_{freq_name}")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {}
                results = {}
                max_workers = min(len(observations), 4) if len(observations) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._calculate_synthesized_beam, obs, attributes): obs.get_observation_code()
                        for obs in observations
                    }
                    for future in futures:
                        obs_code = futures[future]
                        results[obs_code] = future.result()
                logger.info(f"Calculated synthesized beam for {len(observations)} observations in project '{obj.name}'")
                return results

            if obj.get_observation_type() != "VLBI":
                logger.warning(f"Synthesized beam calculation is only for VLBI, got {obj.get_observation_type()}")
                return {}

            def calculate_synthesized_beam(obj, attrs):
                frequency = obj.get_frequencies().get(freq_name).get("frequency") * 1e6  # Convert MHz to Hz
                if frequency is None:
                    logger.error(f"No frequency found for freq_name '{freq_name}' in observation '{obj.get_observation_code()}'")
                    return {}
                uv_store_key = "uv_coverage"  # Use the geometric UV coverage key
                uv_data = self._calculate_uv_coverage(obj, {
                    "time_step": attrs.get("time_step"),
                    "store_key": uv_store_key,
                    "recalculate": attrs.get("recalculate", False)
                })
                if not uv_data:
                    logger.warning(f"No UV data available for '{obj.get_observation_code()}'")
                    return {}

                results = {}
                scans = obj.get_scans().get_active_items()
                for scan in scans:
                    scan_name = scan.name
                    scan_uv_data = uv_data.get(scan_name, {})
                    uv_points = scan_uv_data.get("uv_points", {})
                    if not uv_points:
                        logger.warning(f"No UV points for scan '{scan_name}' in observation '{obj.get_observation_code()}'")
                        continue

                    # Collect UV points in meters
                    u = []
                    v = []
                    for time_idx, points in uv_points.items():
                        for baseline, (uuu, vvv, _) in points.items():
                            if not (np.isnan(uuu) or np.isnan(vvv)):
                                u.append(uuu)
                                v.append(vvv)
                                # Include conjugate points for Hermitian symmetry
                                u.append(-uuu)
                                v.append(-vvv)

                    if not u or not v:
                        logger.warning(f"No valid UV points for scan '{scan_name}'")
                        continue

                    # Create UV plane
                    u = np.array(u)
                    v = np.array(v)
                    u_max = np.max(np.abs(u))
                    v_max = np.max(np.abs(v))
                    if u_max == 0 or v_max == 0:
                        logger.warning(f"Invalid UV range for scan '{scan_name}': u_max={u_max}, v_max={v_max}")
                        continue

                    grid_size = 512  # Fixed grid size for FFT
                    u_grid = np.linspace(-u_max, u_max, grid_size)
                    v_grid = np.linspace(-v_max, v_max, grid_size)
                    uv_plane = np.zeros((grid_size, grid_size), dtype=complex)

                    # Populate UV plane
                    for uu, vv in zip(u, v):
                        u_idx = int((uu + u_max) / (2 * u_max) * (grid_size - 1))
                        v_idx = int((vv + v_max) / (2 * v_max) * (grid_size - 1))
                        if 0 <= u_idx < grid_size and 0 <= v_idx < grid_size:
                            uv_plane[v_idx, u_idx] += 1.0

                    # Compute synthesized beam via 2D FFT
                    beam_2d = fftshift(fft2(uv_plane))
                    beam_2d = np.abs(beam_2d)
                    beam_2d /= np.max(beam_2d) if np.max(beam_2d) != 0 else 1.0  # Normalize

                    # Convert UV to angular coordinates
                    wavelength = 299792458 / frequency  # meters
                    theta_u_max = wavelength / (2 * u_max)  # radians
                    theta_v_max = wavelength / (2 * v_max)  # radians
                    theta_u = np.linspace(-theta_u_max, theta_u_max, grid_size)
                    theta_v = np.linspace(-theta_v_max, theta_v_max, grid_size)
                    theta_u_deg = np.degrees(theta_u)
                    theta_v_deg = np.degrees(theta_v)

                    # Store results per scan
                    results[scan_name] = {
                        "theta_u": theta_u_deg.tolist(),
                        "theta_v": theta_v_deg.tolist(),
                        "beam_2d": beam_2d.tolist()  # Convert to list for visualizer
                    }
                    logger.debug(f"Computed synthesized beam for scan '{scan_name}' with {len(u)//2} UV points")

                if not results:
                    logger.warning(f"No synthesized beam data computed for observation '{obj.get_observation_code()}'")
                return results

            metadata = {"freq_name": freq_name, "time_step": time_step}
            return self._get_cached_or_calculate(obj, store_key, calculate_synthesized_beam, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate synthesized beam: {str(e)}")
            return {}
    
    @time_execution
    def _calculate_baseline_projections(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate baseline projections for VLBI observations in geometric coordinates (meters).

        Args:
            obj (Observation | ScheduleProject): The object to calculate projections for.
            attributes (Dict[str, Any]): Parameters including "time_step" and "store_key".

        Returns:
            Dict[str, Any]: Baseline projection data per scan in meters.
                    Format: {scan_name: {"times": [ISO times], "projections": {time_idx: {pair: bl}}}}

        Notes:
            - Calculates projections as BL = sqrt(u² + v²) in meters.
            - The 'freq_name' attribute, if provided, is ignored and logged for compatibility.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "baseline_projections")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_baseline_projections(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"Calculated baseline projections for {len(observations)} observations in project '{obj.name}'")
                return results

            if obj.get_observation_type() != "VLBI":
                logger.warning(f"Baseline projections are only for VLBI, got {obj.get_observation_type()}")
                return {}

            def calculate_baseline_projections(obj, attrs):
                scans = obj.get_scans().get_active_items()
                telescopes = obj.get_telescopes()
                active_telescopes = telescopes.get_active_items()
                if len(active_telescopes) < 2:
                    logger.error(f"VLBI requires at least 2 active telescopes, got {len(active_telescopes)}")
                    return {}
                uv_store_key = "uv_coverage"  # Use the new UV coverage key
                uv_data = self._calculate_uv_coverage(obj, {
                    "time_step": time_step,
                    "store_key": uv_store_key,
                    "recalculate": attrs.get("recalculate", False)
                })
                if not uv_data:
                    logger.error(f"Failed to obtain UV coverage data for '{obj.get_observation_code()}'")
                    return {}
                results = {}
                with ThreadPoolExecutor() as executor:
                    futures = {
                        executor.submit(self._process_baseline_projections, scan, obj, time_step, uv_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        results[scan_name] = future.result()
                return results

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items())}
            return self._get_cached_or_calculate(obj, store_key, calculate_baseline_projections, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate baseline projections: {str(e)}")
            return {}

    def _process_baseline_projections(self, scan: Scan, observation: Observation, time_step: Optional[float], uv_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process baseline projections for a single scan in geometric coordinates (meters).

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds).
            uv_data (Dict[str, Any]): Precomputed UV data in meters.

        Returns:
            Dict[str, Any]: Baseline projections in meters, formatted as {time_idx: {pair: bl}}.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        scan_name = scan.name

        logger.debug(f"Processing baseline projections for scan {scan_name}")

        scan_uv_data = uv_data.get(scan_name, {}) if isinstance(uv_data, dict) else {}
        if not scan_uv_data or "uv_points" not in scan_uv_data:
            logger.error(f"No UV data available for scan {scan_name} at {start_time.isot}")
            return {"times": [], "projections": {}}

        if time_step is None:
            projections = self._compute_projections_from_uv(scan_uv_data["uv_points"], active_telescopes)
            logger.debug(f"Computed {len(projections)} projections for single-time scan {scan_name}")
            return {"projections": {0: projections}}

        time_values = np.arange(0, duration, time_step) * u.s
        times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
        uv_points = scan_uv_data.get("uv_points", {})

        if not uv_points:
            logger.warning(f"No UV points found for scan {scan_name}")
            return {"times": times.isot.tolist(), "projections": {}}

        logger.debug(f"Found {len(uv_points)} UV points for scan {scan_name}")
        projections = {}
        for time_idx, uv_dict in uv_points.items():
            if time_idx >= len(times):
                logger.warning(f"Time index {time_idx} exceeds available times ({len(times)}) in scan {scan_name}")
                continue
            proj_dict = {}
            for pair, (uuu, vvv, _) in uv_dict.items():
                bl = np.sqrt(uuu * uuu + vvv * vvv)
                if not np.isnan(bl):
                    proj_dict[pair] = float(bl)
                else:
                    logger.debug(f"Skipping NaN baseline for pair {pair} at time_idx {time_idx}")
            if proj_dict:
                projections[time_idx] = proj_dict
            else:
                logger.debug(f"No valid projections for time_idx {time_idx} in scan {scan_name}")

        if not projections:
            logger.warning(f"No valid baseline projections computed for scan {scan_name}")

        return {
            "times": times.isot.tolist(),
            "projections": projections
        }
        
    def _compute_projections_from_uv(self, uv_points: Dict[int, Dict[str, Tuple[float, float, float]]], telescopes: List[Telescope | SpaceTelescope]) -> Dict[str, float]:
        """Compute baseline projection BL = sqrt(u² + v²) from pre-calculated (u,v) data in meters.

        Args:
            uv_points (Dict[int, Dict[str, Tuple[float, float, float]]]): UV data organized by time index.
            telescopes (List[Telescope | SpaceTelescope]): List of telescopes.

        Returns:
            Dict[str, float]: Baseline length per telescope pair in meters for the first time index.
        """
        projections = {}
        # Use the first time index (e.g., time_idx=0) for single-time calculations
        uv_dict = uv_points.get(0, {})
        for pair, (uuu, vvv, _) in uv_dict.items():
            bl = np.sqrt(uuu * uuu + vvv * vvv)  # BL = sqrt(u² + v²) in meters
            projections[pair] = float(bl)
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
        """Calculate Mollweide projection tracks for telescopes and source.

        Args:
            obj (Observation | ScheduleProject): The object to calculate tracks for.
            attributes (Dict[str, Any]): Parameters including "time_step" and "store_key".

        Returns:
            Dict[str, Any]: Mollweide coordinates per scan.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "mollweide_tracks")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_mollweide_tracks(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"Calculated Mollweide tracks for {len(observations)} observations in project '{obj.name}'")
                return results

            def calculate_mollweide_tracks(obj, attrs):
                scans = obj.get_scans().get_active_items()
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": attrs.get("recalculate", False)}
                position_data = self._calculate_telescope_positions(obj, position_attrs)
                results = {}
                with ThreadPoolExecutor() as executor:
                    futures = {
                        executor.submit(self._process_mollweide_tracks, scan, obj, time_step, position_data): i
                        for i, scan in enumerate(scans)
                    }
                    for future in futures:
                        scan_name = futures[future]
                        results[scan_name] = future.result()
                return results

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items())}
            return self._get_cached_or_calculate(obj, store_key, calculate_mollweide_tracks, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate Mollweide tracks: {str(e)}")
            return {}

    def _process_mollweide_tracks(self, scan: Scan, observation: Observation, time_step: Optional[float], position_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Mollweide tracks for a single scan.

        Args:
            scan (Scan): The scan to process.
            sources (Sources): Collection of sources.
            telescopes (Telescopes): Collection of telescopes.
            time_step (Optional[float]): Sampling interval (seconds).
            position_data (Dict[str, Any]): Precomputed position data.
            observation (Observation): Parent observation.

        Returns:
            Dict[str, Any]: Mollweide coordinates for source and telescopes.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        source = scan.get_source(observation)
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        scan_name = scan.name
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs') if source else None
        source_lon, source_lat = self._compute_mollweide_coords(source_coord) if source_coord else (None, None)

        if not position_data or scan_name not in position_data:
            logger.error(f"No position data for scan {scan_name}")
            return {"source": {"name": source.name if source else None, "lon": source_lon, "lat": source_lat}, "telescope_tracks": {}}
        
        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            tel_positions = position_data.get(scan_name, {}).get("telescope_positions", {})
            tracks = {}
            for tel in active_telescopes:
                pos = tel_positions.get(tel.get_code())
                if pos:
                    lon, lat = self._compute_mollweide_coords_from_position(pos, mean_time)
                    tracks[tel.get_code()] = {"lon": [lon], "lat": [lat]}
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
            tel_positions = position_data.get(scan_name, {}).get("telescope_positions", {})
            
            tracks = {tel.get_code(): {"lon": [], "lat": []} for tel in active_telescopes}
            for t_idx, t in enumerate(times):
                for tel in active_telescopes:
                    pos_data = tel_positions.get(tel.get_code(), {})
                    pos = pos_data.get("positions", [])[t_idx] if "positions" in pos_data else None
                    if pos:
                        lon, lat = self._compute_mollweide_coords_from_position(pos, t)
                        tracks[tel.get_code()]["lon"].append(lon)
                        tracks[tel.get_code()]["lat"].append(lat)

        return {
            "source": {"name": source.name if source else None, "lon": source_lon, "lat": source_lat},
            "times": times.isot.tolist() if time_step else [mean_time.isot],
            "telescope_tracks": tracks
        }
    
    def _compute_mollweide_coords_from_position(self, position: Tuple[float, float, float], time: Time) -> Tuple[float, float]:
        """Compute Mollweide coordinates from GCRS position in J2000.

        Args:
            position (Tuple[float, float, float]): GCRS position (x, y, z) in meters.
            time (Time): Observation time.

        Returns:
            Tuple[float, float]: RA (in [-180, 180] degrees) and Dec (in [-90, 90] degrees).
        """
        x, y, z = position
        r = np.sqrt(x**2 + y**2 + z**2)
        ra_rad = np.arctan2(y, x)  # RA
        dec_rad = np.arcsin(z / r)  # Dec
        
        ra = np.degrees(ra_rad)  # 0° to 360°
        dec = np.degrees(dec_rad)  # -90° to 90°

        lon = ra
        if lon > 180.0:
            lon -= 360.0
        lat = np.clip(dec, -90.0, 90.0)

        return lon, lat

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
            j2000_epoch = Time("2000-01-01T12:00:00", scale='utc')
            times = Time(time_strs, format='isot', scale='utc') - j2000_epoch
            times_sec = times.sec
            
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

    def _interpolate_orbit(self, telescope: SpaceTelescope, start_time: Time, end_time: Time, time_step: float) -> Dict[str, Any]:
        """Interpolate orbit data for a space telescope over a time range.

        Args:
            telescope (SpaceTelescope): The space telescope.
            start_time (Time): Start time of interpolation.
            end_time (Time): End time of interpolation.
            time_step (float): Time step for interpolation (seconds).

        Returns:
            Dict[str, Any]: Interpolated orbit data with times, positions, velocities, and time_range. Returns empty dict if no data.

        Notes:
            - If orbit data partially covers the time range, interpolates only for the available portion and fills with None.
            - Ensures no NaN values are included in the output.
        """
        if telescope.get("use_kep"):
            logger.info(f"Skipping interpolation for '{telescope.get_code()}' as use_kep=True")
            return {}
        
        orbit_file = telescope.get_orbit()
        if not orbit_file:
            logger.warning(f"No orbit file defined for telescope '{telescope.get_code()}'")
            return {}
        
        try:
            # Load orbit data
            orbit_data = self._load_orbit_data(orbit_file, start_time, end_time)
            if not orbit_data:
                logger.warning(f"No valid orbit data for '{telescope.get_code()}' in time range {start_time.isot} to {end_time.isot}")
                return {}
            times = orbit_data["times"]
            positions = orbit_data["positions"]
            velocities = orbit_data["velocities"]
            
            # Check for NaN or invalid data
            if np.any(np.isnan(positions)) or np.any(np.isnan(velocities)):
                logger.warning(f"Orbit data contains NaN for '{telescope.get_code()}': positions={positions}, velocities={velocities}")
                return {}
            
            j2000_epoch = Time("2000-01-01T12:00:00", scale='utc')
            t_start = (start_time - j2000_epoch).sec
            t_end = (end_time - j2000_epoch).sec
            
            # Check for partial coverage
            data_start = times[0]
            data_end = times[-1]
            if data_start > t_end or data_end < t_start:
                logger.warning(f"Orbit data for '{telescope.get_code()}' does not cover time range {start_time.isot} to {end_time.isot}")
                return {}
            elif data_start > t_start or data_end < t_end:
                logger.warning(f"Orbit data for '{telescope.get_code()}' partially covers time range: {Time(data_start, format='jd').isot} to {Time(data_end, format='jd').isot}")
                t_start = max(t_start, data_start)
                t_end = min(t_end, data_end)
            
            # Filter and ensure unique times
            unique_indices = np.unique(times, return_index=True)[1]
            filtered_times = times[unique_indices]
            filtered_positions = positions[unique_indices]
            filtered_velocities = velocities[unique_indices]
            
            if len(filtered_times) < 2:
                logger.warning(f"Too few points ({len(filtered_times)}) for interpolation for '{telescope.get_code()}'")
                return {}
            
            # Interpolate
            interp_times = np.arange(t_start, t_end + time_step, time_step)
            method = telescope.get("interpolation_method") or "chebyshev"
            
            # Initialize arrays for full requested time range
            full_times = np.arange((start_time - j2000_epoch).sec, (end_time - j2000_epoch).sec + time_step, time_step)
            full_positions = np.full((len(full_times), 3), np.nan, dtype=float)
            full_velocities = np.full((len(full_times), 3), np.nan, dtype=float)
            
            # Find indices for valid interpolation range
            valid_mask = (full_times >= t_start) & (full_times <= t_end)
            valid_interp_times = full_times[valid_mask]
            
            if not valid_interp_times.size:
                logger.warning(f"No valid interpolation times for '{telescope.get_code()}'")
                return {}
            
            if method == "chebyshev":
                degree = min(30, len(filtered_times) - 1)  # Adjust degree based on data points
                norm_times = 2 * (filtered_times - t_start) / (t_end - t_start) - 1
                norm_interp_times = 2 * (valid_interp_times - t_start) / (t_end - t_start) - 1
                pos_polynomials = [chebyshev.Chebyshev.fit(norm_times, pos, degree) for pos in filtered_positions.T]
                vel_polynomials = [chebyshev.Chebyshev.fit(norm_times, vel, degree) for vel in filtered_velocities.T]
                full_positions[valid_mask] = np.array([poly(norm_interp_times) for poly in pos_polynomials]).T
                full_velocities[valid_mask] = np.array([poly(norm_interp_times) for poly in vel_polynomials]).T
            elif method == "cubic_spline":
                full_positions[valid_mask] = np.array([CubicSpline(filtered_times, pos)(valid_interp_times) for pos in filtered_positions.T]).T
                full_velocities[valid_mask] = np.array([CubicSpline(filtered_times, vel)(valid_interp_times) for vel in filtered_velocities.T]).T
            else:  # linear
                full_positions[valid_mask] = np.array([np.interp(valid_interp_times, filtered_times, pos) for pos in filtered_positions.T]).T
                full_velocities[valid_mask] = np.array([np.interp(valid_interp_times, filtered_times, vel) for vel in filtered_velocities.T]).T
            
            # Check for NaN in interpolated data
            if np.any(np.isnan(full_positions)) or np.any(np.isnan(full_velocities)):
                logger.warning(f"Interpolated data contains NaN for '{telescope.get_code()}': positions={full_positions}, velocities={full_velocities}")
                return {}
            
            interpolated_data = {
                "times": full_times,
                "positions": full_positions,
                "velocities": full_velocities,
                "time_range": (t_start, t_end)  # Explicitly set time_range
            }
            
            logger.info(f"Interpolated orbit for '{telescope.get_code()}' using {method} with {len(valid_interp_times)} points")
            return interpolated_data
        except Exception as e:
            logger.warning(f"Failed to interpolate orbit for '{telescope.get_code()}': {str(e)}")
            return {}

    def _get_state_vector_from_orbit(self, telescope: SpaceTelescope, time: Time) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate state vector from orbit file at a specific time (fallback method).

        Args:
            telescope (SpaceTelescope): The space telescope.
            time (Time): Time for state vector calculation.

        Returns:
            Tuple[np.ndarray, np.ndarray]: Position and velocity vectors in meters and m/s.
        """
        logger.warning(f"Fallback to direct orbit file loading for '{telescope.get_code()}' at {time.isot}")
        orbit_file = telescope.get_orbit()
        if not orbit_file:
            raise ValueError(f"No orbit file defined for telescope '{telescope.get_code()}'")
        orbit_data = self._load_orbit_data(orbit_file)
        j2000_epoch = Time("2000-01-01T12:00:00", scale='utc')
        t = (time - j2000_epoch).sec
        times = orbit_data["times"]
        if t < times[0] or t > times[-1]:
            logger.warning(f"Time {time.isot} outside orbit data range for '{telescope.get_code()}'")
            return np.array([0.0, 0.0, 0.0]), np.array([0.0, 0.0, 0.0])
        
        pos_idx = np.searchsorted(times, t)
        t1, t2 = times[pos_idx - 1], times[pos_idx]
        pos1, pos2 = orbit_data["positions"][pos_idx - 1], orbit_data["positions"][pos_idx]
        vel1, vel2 = orbit_data["velocities"][pos_idx - 1], orbit_data["velocities"][pos_idx]
        frac = (t - t1) / (t2 - t1)
        pos = pos1 + (pos2 - pos1) * frac
        vel = vel1 + (vel2 - vel1) * frac
        logger.debug(f"Calculated state vector for '{telescope.get_code()}' at {time.isot}: pos={pos}, vel={vel}")
        return pos, vel
    
    def _get_state_vector_from_cached_orbit(self, telescope: SpaceTelescope, time: Time, orbit_data: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate state vector from cached interpolated orbit data.

        Args:
            telescope (SpaceTelescope): The space telescope.
            time (Time): Time for state vector calculation.
            orbit_data (Dict[str, Any]): Cached interpolated orbit data.

        Returns:
            Tuple[np.ndarray, np.ndarray]: Position and velocity vectors in meters and m/s.

        Raises:
            ValueError: If time is outside the cached orbit data range or data is invalid.
        """
        j2000_epoch = Time("2000-01-01T12:00:00", scale='utc')
        t = (time - j2000_epoch).sec
        interp_times = orbit_data.get("times", np.array([]))
        
        if not interp_times.size:
            logger.warning(f"No cached orbit data for '{telescope.get_code()}' at {time.isot}")
            raise ValueError("No cached orbit data available")
        
        # Use time_range if available, otherwise compute from interp_times
        t_min, t_max = orbit_data.get("time_range", (interp_times[0], interp_times[-1]) if interp_times.size else (float('inf'), float('-inf')))
        
        if np.any(np.isnan([t_min, t_max])) or t_min == float('inf') or t_max == float('-inf'):
            logger.warning(f"Invalid time range for '{telescope.get_code()}': t_min={t_min}, t_max={t_max}")
            raise ValueError("Invalid time range in cached orbit data")
        
        if t < t_min or t > t_max:
            logger.warning(f"Time {time.isot} outside cached orbit data range [{Time(t_min + j2000_epoch.jd, format='jd').isot}, {Time(t_max + j2000_epoch.jd, format='jd').isot}] for '{telescope.get_code()}'")
            raise ValueError(f"Time {time.isot} outside orbit data range")
        
        idx = np.searchsorted(interp_times, t)
        if idx == 0:
            pos = orbit_data["positions"][0]
            vel = orbit_data["velocities"][0]
        elif idx >= len(interp_times):
            pos = orbit_data["positions"][-1]
            vel = orbit_data["velocities"][-1]
        else:
            frac = (t - interp_times[idx - 1]) / (interp_times[idx] - interp_times[idx - 1])
            pos = (1 - frac) * orbit_data["positions"][idx - 1] + frac * orbit_data["positions"][idx]
            vel = (1 - frac) * orbit_data["velocities"][idx - 1] + frac * orbit_data["velocities"][idx]
        
        if np.any(np.isnan(pos)) or np.any(np.isnan(vel)):
            logger.warning(f"Interpolated position/velocity contains NaN for '{telescope.get_code()}' at {time.isot}: pos={pos}, vel={vel}")
            raise ValueError("Invalid interpolated data")
        
        logger.debug(f"Interpolated state vector from cache for '{telescope.get_code()}' at {time.isot}: pos={pos}, vel={vel}")
        return pos, vel