from abc import ABC
from common.super.super import Super
from common.utils.logging_setup import logger

from unit_scheduling_2.base.frequencies import Frequencies
from unit_scheduling_2.base.sources import Sources, Source
from unit_scheduling_2.base.telescopes import Telescope, SpaceTelescope, Telescopes
from unit_scheduling_2.base.scans import Scan
from unit_scheduling_2.base.observation import Observation
from unit_scheduling_2.super.schedule_project import ScheduleProject

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
        """calculate source visibility for all scans.

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
                observations = obj.get_observations()
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
                telescopes = obj.get_telescopes()
                sources = obj.get_sources()
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": attrs.get("recalculate")}
                position_data = self._calculate_telescope_positions(obj, position_attrs)
                if not position_data:
                    logger.error(f"failed to obtain telescope positions for '{obj.get_observation_code()}'")
                    return {}
                results = {}
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_source_visibility, scan, telescopes, sources, time_step, position_data, obj): scan.name
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
        
    def _process_source_visibility(self, scan: Scan, telescopes: Telescopes, sources: Sources, time_step: Optional[float], position_data: Dict[str, Any], observation: Observation) -> Dict[str, Any]:
        """process source visibility for a single scan.

        args:
            scan (Scan): the scan to process.
            telescopes (Telescopes): collection of telescopes.
            sources (Sources): collection of sources.
            time_step (Optional[float]): time interval for sampling (seconds).
            position_data (Dict[str, Any]): precomputed telescope positions.
            observation (Observation): the parent observation.

        returns:
            Dict[str, Any]: visibility data including source name and visibility per telescope.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        source_name = scan.get_source_name()
        source = sources.get(source_name)
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
        telescope_names = scan.get_telescope_names()
        active_telescopes = [telescopes.get(i) for i in telescope_names if telescopes.get(i).isactive]
        scan_name = scan.name

        logger.debug(f"processing visibility for scan {scan_name}: {len(active_telescopes)} telescopes")

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            positions = position_data.get(scan_name, {}).get("telescope_positions", {})
            visibility = self._compute_visibility_at_time(source, active_telescopes, mean_time, positions)
            # convert boolean values to numpy array for consistency
            visibility_array = np.array([visibility[tel.get_code()] for tel in active_telescopes], dtype=bool)
            visibility_dict = {tel.get_code(): visibility_array[i] for i, tel in enumerate(active_telescopes)}
            return {"source": source.name, "visibility": visibility_dict}
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
            positions = position_data.get(scan_name, {}).get("telescope_positions", {})
            
            # initialize visibility array: shape (n_telescopes, n_times)
            visibility = np.zeros((len(active_telescopes), len(times)), dtype=bool)
            pos_arrays = {}
            for i, tel in enumerate(active_telescopes):
                tel_code = tel.get_code()
                pos_data = positions.get(tel_code, {})
                pos_array = np.array(pos_data.get("positions", [])) if "positions" in pos_data else None
                if pos_array is None or len(pos_array) != len(times):
                    logger.warning(f"no or mismatched position data for telescope '{tel_code}' in scan {scan_name}")
                    visibility[i] = False
                else:
                    pos_arrays[tel_code] = pos_array

            for i, tel in enumerate(active_telescopes):
                tel_code = tel.get_code()
                if tel_code not in pos_arrays:
                    continue
                pos_array = pos_arrays[tel_code]
                
                if isinstance(tel, SpaceTelescope):
                    itrs = ITRS(CartesianRepresentation(pos_array[:, 0], pos_array[:, 1], pos_array[:, 2], unit=u.m), obstime=times)
                    altaz = source_coord.transform_to(AltAz(obstime=times, location=itrs.earth_location))
                    pitch = altaz.alt.deg
                    yaw = altaz.az.deg
                    pitch_range = tel.get_pitch_range()
                    yaw_range = tel.get_yaw_range()
                    is_visible = (pitch_range[0] <= pitch) & (pitch <= pitch_range[1]) & (yaw_range[0] <= yaw) & (yaw <= yaw_range[1])
                    visibility[i] = is_visible
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
                        is_visible = (el_range[0] <= el) & (el <= el_range[1]) & (az_range[0] <= az) & (az <= az_range[1])
                    elif mount_type.value == "EQUA":
                        hadec = source_coord.transform_to(HADec(obstime=times, location=location))
                        ha = hadec.ha.deg
                        dec = hadec.dec.deg
                        ha_range = tel.get_azimuth_range()
                        dec_range = tel.get_elevation_range()
                        is_visible = (dec_range[0] <= dec) & (dec <= dec_range[1]) & (ha_range[0] <= ha) & (ha <= ha_range[1])
                    else:
                        logger.debug(f"unsupported mount type {mount_type.value} for telescope '{tel_code}'")
                        is_visible = np.zeros(len(times), dtype=bool)
                    visibility[i] = is_visible

            # convert visibility array to dictionary for compatibility with visualizer
            visibility_dict = {tel.get_code(): visibility[i].tolist() for i, tel in enumerate(active_telescopes)}
            return {"source": source.name, "times": times.isot.tolist(), "visibility": visibility_dict}
    

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
        """calculate telescope positions in GCRS (J2000) for all scans or time range.

        args:
            obj (Observation | ScheduleProject): the object to calculate positions for.
            attributes (Dict[str, Any]): parameters including "time_step", "start_time", "end_time".

        returns:
            Dict[str, Any]: telescope positions per scan or time range, keyed by index.
        """
        try:
            time_step = attributes.get("time_step")
            start_time = attributes.get("start_time")
            end_time = attributes.get("end_time")
            store_key = attributes.get("store_key", "telescope_positions")

            def calculate_positions(obj, attrs):
                if isinstance(obj, ScheduleProject):
                    observations = obj.get_observations()
                    if not observations:
                        logger.warning(f"no observations in project '{obj.name}'")
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
                    logger.info(f"calculated telescope positions for {len(observations)} observations in project '{obj.name}'")
                    return results

                telescopes = obj.get_telescopes()
                active_telescopes = telescopes.get_active_items()
                if not active_telescopes:
                    logger.warning(f"no active telescopes in observation '{obj.get_observation_code()}'")
                    return {}

                if start_time and end_time:
                    start = Time(start_time)
                    end = Time(end_time)
                    use_scans = False
                else:
                    scans = obj.get_scans().get_active_items()
                    if not scans:
                        logger.warning(f"no scans or time range specified in observation '{obj.get_observation_code()}'")
                        return {}
                    start_times = [scan.get_start() for scan in scans]
                    end_times = [scan.get_start() + scan.get_duration() * u.s for scan in scans]
                    start = min(start_times)
                    end = max(end_times)
                    use_scans = True

                time_values = np.arange(0, (end - start).sec, time_step) * u.s if time_step else [((end - start).sec / 2) * u.s]
                times = Time(start.mjd + time_values.to(u.d).value, format='mjd')
                logger.debug(f"calculating telescope positions for {len(times)} time points from {start.isot} to {end.isot}")

                # cache orbit interpolations for SpaceTelescopes
                for tel in active_telescopes:
                    if isinstance(tel, SpaceTelescope) and time_step and not tel.get("use_kep"):
                        tel.interpolate_orbit(start, end, time_step)

                results = {}
                if use_scans and time_step:
                    for scan in scans:
                        scan_start = scan.get_start()
                        scan_duration = scan.get_duration()
                        scan_times = times[(scan_start <= times) & (times <= scan_start + scan_duration * u.s)]
                        if not scan_times:
                            continue
                        tel_positions = {}
                        for tel in active_telescopes:
                            if isinstance(tel, Telescope) and not isinstance(tel, SpaceTelescope):
                                # vectorized computation for ground telescopes
                                x, y, z = tel.get_coordinates()
                                res = tel.get(["vx", "vy", "vz"])
                                vx, vy, vz = res["vx"], res["vy"], res["vz"]
                                dt = (scan_times - Time("2000-01-01T12:00:00")).sec
                                itrs_coords = CartesianRepresentation(
                                    x + vx * dt, y + vy * dt, z + vz * dt, unit=u.m
                                )
                                itrs = ITRS(itrs_coords, obstime=scan_times)
                                gcrs = itrs.transform_to(GCRS(obstime=scan_times))
                                positions = np.vstack([
                                    gcrs.cartesian.x.value,
                                    gcrs.cartesian.y.value,
                                    gcrs.cartesian.z.value
                                ]).T  # shape: (n_times, 3)
                            else:
                                # use cached orbit for SpaceTelescope
                                positions = np.array([self._compute_telescope_position(tel, t) for t in scan_times])
                            tel_positions[tel.get_code()] = {
                                "times": [t.isot for t in scan_times],
                                "positions": positions.tolist()  # convert to list for visualizer compatibility
                            }
                        results[scan.name] = {"telescope_positions": tel_positions}
                else:
                    tel_positions = {}
                    for tel in active_telescopes:
                        if isinstance(tel, Telescope) and not isinstance(tel, SpaceTelescope):
                            # vectorized computation for ground telescopes
                            x, y, z = tel.get_coordinates()
                            res = tel.get(["vx", "vy", "vz"])
                            vx, vy, vz = res["vx"], res["vy"], res["vz"]
                            dt = (times - Time("2000-01-01T12:00:00")).sec
                            itrs_coords = CartesianRepresentation(
                                x + vx * dt, y + vy * dt, z + vz * dt, unit=u.m
                            )
                            itrs = ITRS(itrs_coords, obstime=times)
                            gcrs = itrs.transform_to(GCRS(obstime=times))
                            positions = np.vstack([
                                gcrs.cartesian.x.value,
                                gcrs.cartesian.y.value,
                                gcrs.cartesian.z.value
                            ]).T  # shape: (n_times, 3)
                        else:
                            # use cached orbit for SpaceTelescope
                            positions = np.array([self._compute_telescope_position(tel, t) for t in times])
                        tel_positions[tel.get_code()] = {
                            "times": [t.isot for t in times],
                            "positions": positions.tolist()  # convert to list for visualizer compatibility
                        }
                    results[0] = {"telescope_positions": tel_positions}

                logger.debug(f"calculated telescope positions for {len(results)} entries in '{obj.get_observation_code()}'")
                return results

            metadata = {"time_step": time_step, "start_time": start_time, "end_time": end_time}
            return self._get_cached_or_calculate(obj, store_key, calculate_positions, attributes, metadata)
        except Exception as e:
            logger.error(f"failed to calculate telescope positions: {str(e)}")
            return {}    

    def _process_scan_positions(self, scan: Scan, telescopes: Telescopes, time_step: Optional[float]) -> Dict[str, Any]:
        """process telescope positions for a single scan.

        args:
            scan (Scan): the scan to process.
            telescopes (Telescopes): collection of telescopes involved in the scan.
            time_step (Optional[float]): time interval for position sampling (seconds). if None, uses mean time.

        returns:
            Dict[str, Any]: positions for active telescopes, with times if time_step is provided.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        telescope_names = scan.get_telescope_names()
        active_telescopes = [telescopes.get(i) for i in telescope_names if telescopes.get(i).isactive]

        if not active_telescopes:
            logger.warning(f"no active telescopes for scan starting at {start_time.isot}")
            return {"telescope_positions": {}}

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            positions = {tel.get_code(): self._compute_telescope_position(tel, mean_time) for tel in active_telescopes}
            # convert to numpy array for consistency
            pos_array = np.array(list(positions.values()))  # shape: (n_telescopes, 3)
            return {"telescope_positions": {tel.get_code(): pos_array[i].tolist() for i, tel in enumerate(active_telescopes)}}
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
            result = {}
            for tel in active_telescopes:
                if isinstance(tel, Telescope) and not isinstance(tel, SpaceTelescope):
                    # vectorized computation for ground telescopes
                    x, y, z = tel.get_coordinates()
                    res = tel.get(["vx", "vy", "vz"])
                    vx, vy, vz = res["vx"], res["vy"], res["vz"]
                    dt = (times - Time("2000-01-01T12:00:00")).sec
                    itrs_coords = CartesianRepresentation(
                        x + vx * dt, y + vy * dt, z + vz * dt, unit=u.m
                    )
                    itrs = ITRS(itrs_coords, obstime=times)
                    gcrs = itrs.transform_to(GCRS(obstime=times))
                    positions = np.vstack([
                        gcrs.cartesian.x.value,
                        gcrs.cartesian.y.value,
                        gcrs.cartesian.z.value
                    ]).T  # shape: (n_times, 3)
                else:
                    # use cached orbit for SpaceTelescope
                    positions = np.array([self._compute_telescope_position(tel, t) for t in times])
                result[tel.get_code()] = {
                    "times": times.isot.tolist(),
                    "positions": positions.tolist()  # convert to list for visualizer compatibility
                }
            return {"telescope_positions": result}

    def _compute_telescope_position(self, telescope: Telescope | SpaceTelescope, time: Time) -> Tuple[float, float, float]:
        """Compute a telescope's GCRS position at a specific time.

        Args:
            telescope (Telescope | SpaceTelescope): The telescope to compute position for.
            time (Time): The time of calculation.

        Returns:
            Tuple[float, float, float]: GCRS coordinates (x, y, z) in meters.

        Raises:
            ValueError: If telescope type is unsupported.
        """
        if isinstance(telescope, Telescope) and not isinstance(telescope, SpaceTelescope):
            x, y, z = telescope.get_coordinates()
            res = telescope.get(["vx", "vy", "vz"])
            vx, vy, vz = res["vx"], res["vy"], res["vz"]
            dt = (time - Time("2000-01-01T12:00:00")).sec
            itrs_coords = CartesianRepresentation(x + vx * dt, y + vy * dt, z + vz * dt, unit=u.m)
            itrs = ITRS(itrs_coords, obstime=time)
            gcrs = itrs.transform_to(GCRS(obstime=time))
            return (gcrs.cartesian.x.value, gcrs.cartesian.y.value, gcrs.cartesian.z.value)
        elif isinstance(telescope, SpaceTelescope):
            pos, _ = telescope.get_state_vector(time)
            return tuple(float(p) for p in pos)
        raise ValueError(f"Unsupported telescope type: {type(telescope)}")
    
    @time_execution
    def _calculate_uv_coverage(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """calculate (u,v) coverage for all scans in the observation or project.

        args:
            obj (Observation | ScheduleProject): the object to calculate UV coverage for.
            attributes (Dict[str, Any]): parameters including "time_step", "freq_name", and "store_key".

        returns:
            Dict[str, Any]: UV coverage data per scan, including u, v, w coordinates.
        """
        try:
            time_step = attributes.get("time_step")
            freq_name = attributes.get("freq_name")
            store_key = attributes.get("store_key", f"uv_coverage_{freq_name}")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_observations()
                if not observations:
                    logger.warning(f"no observations in project '{obj.name}'")
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
                logger.info(f"calculated (u,v) coverage for {len(observations)} observations in project '{obj.name}'")
                return results

            def calculate_uv(obj, attrs):
                scans = obj.get_scans().get_active_items()
                telescopes = obj.get_telescopes()
                frequencies = obj.get_frequencies()
                results = {}

                visibility_attrs = {"time_step": time_step, "store_key": "source_visibility", "recalculate": attrs.get("recalculate", False)}
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": attrs.get("recalculate", False)}

                visibility_data = self._calculate_source_visibility(obj, visibility_attrs)
                position_data = self._calculate_telescope_positions(obj, position_attrs)
                
                if not visibility_data or not position_data:
                    logger.error(f"missing visibility or position data for '{obj.get_observation_code()}'")
                    return {}

                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_uv_coverage, scan, telescopes, frequencies, time_step, freq_name, obj, visibility_data, position_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        results[scan_name] = future.result()
                return results

            metadata = {"time_step": time_step, "freq_name": freq_name, "scan_count": len(obj.get_scans().get_active_items())}
            return self._get_cached_or_calculate(obj, store_key, calculate_uv, attributes, metadata)
        except Exception as e:
            logger.error(f"failed to calculate (u,v) coverage: {str(e)}")
            return {}

    def _process_uv_coverage(self, scan: Scan, telescopes: Telescopes, frequencies: Frequencies, time_step: Optional[float], freq_name: Optional[str], observation: Observation, visibility_data: Dict[str, Any], position_data: Dict[str, Any]) -> Dict[str, Any]:
        """process UV coverage for a single scan using vectorized computations.

        args:
            scan (Scan): the scan to process.
            telescopes (Telescopes): collection of telescopes.
            frequencies (Frequencies): collection of frequencies.
            time_step (Optional[float]): sampling interval (seconds).
            freq_name (Optional[str]): frequency index to use.
            observation (Observation): parent observation.
            visibility_data (Dict[str, Any]): precomputed visibility data.
            position_data (Dict[str, Any]): precomputed position data.

        returns:
            Dict[str, Any]: UV points per frequency, with times if sampled.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        active_telescopes = [telescopes.get(i) for i in scan.get_telescope_names() if telescopes.get(i).isactive]
        freqs = [frequencies.get(i).get("frequency") * 1e6 for i in (scan.get_frequency_names() if freq_name is None else [freq_name]) if frequencies.get(i).isactive]
        source = observation.get_sources().get(scan.source_name)
        scan_name = scan.name

        if len(active_telescopes) < 2:
            logger.warning(f"insufficient telescopes ({len(active_telescopes)}) for UV coverage in scan {scan_name}")
            return {"uv_points": {f: [] for f in freqs}} if time_step is None else {"times": [], "uv_points": {f: [] for f in freqs}}

        # define time array
        if time_step is None:
            times = Time(start_time + (duration / 2) * u.s)
            times = times.reshape(-1)  # ensure 1D array
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')

        # collect visibility and position data
        scan_visibility = visibility_data.get(scan_name, {}).get("visibility", {})
        scan_positions = position_data.get(scan_name, {}).get("telescope_positions", {})
        
        if not scan_visibility or not scan_positions:
            logger.warning(f"no visibility or position data for scan {scan_name}")
            return {"uv_points": {f: [] for f in freqs}} if time_step is None else {"times": times.isot.tolist(), "uv_points": {f: [] for f in freqs}}

        # prepare arrays
        tel_codes = [tel.get_code() for tel in active_telescopes]
        visibility = np.array([scan_visibility.get(code, [False] * len(times)) for code in tel_codes], dtype=bool)  # shape: (n_tels, n_times)
        positions = np.array([scan_positions.get(code, {}).get("positions", [[]] * len(times))[0:len(times)] for code in tel_codes])  # shape: (n_tels, n_times, 3)

        if positions.shape[1] != len(times):
            logger.warning(f"mismatched position data length for scan {scan_name}")
            return {"uv_points": {f: [] for f in freqs}} if time_step is None else {"times": times.isot.tolist(), "uv_points": {f: [] for f in freqs}}

        # compute UV points
        uv_points = self._compute_uv_at_time(active_telescopes, times, freqs, source, visibility, positions)

        # convert uv_points to list of tuples for visualizer compatibility
        for freq in uv_points:
            uv_points[freq] = [(pair, u, v, w) for pair, u, v, w in uv_points[freq]]

        # format output
        result = {"uv_points": uv_points}
        if time_step is not None:
            result["times"] = times.isot.tolist()
        return result

    def _compute_uv_at_time(self, telescopes: List[Telescope | SpaceTelescope], times: Time, frequencies: List[float], source: Optional[Source] = None, visibility: Optional[np.ndarray] = None, gcrs_positions: Optional[np.ndarray] = None) -> Dict[float, List[Tuple[str, float, float, float]]]:
        """compute UV coordinates for multiple times using vectorized operations.

        args:
            telescopes (List[Telescope | SpaceTelescope]): list of telescopes.
            times (Time): array of observation times.
            frequencies (List[float]): frequencies in Hz.
            source (Optional[Source]): source for UV calculation.
            visibility (Optional[np.ndarray]): visibility array of shape (n_telescopes, n_times).
            gcrs_positions (Optional[np.ndarray]): GCRS positions of shape (n_telescopes, n_times, 3).

        returns:
            Dict[float, List[Tuple[str, float, float, float]]]: UVW coordinates per frequency and baseline.
        """
        uv_points = {f: [] for f in frequencies}
        c = 299792458  # m/s

        if not telescopes or len(telescopes) < 2:
            logger.warning(f"insufficient telescopes ({len(telescopes)}) to compute (u,v) at {times[0].isot}")
            return uv_points

        if source is None:
            logger.warning("no source provided; cannot calculate (u,v,w)")
            return uv_points

        # prepare source coordinates
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
        ra = source_coord.ra.rad
        dec = source_coord.dec.rad

        # compute positions if not provided
        if gcrs_positions is None:
            gcrs_positions = np.array([self._compute_telescope_position(tel, times) for tel in telescopes])  # shape: (n_tels, n_times, 3)

        # compute visibility if not provided
        if visibility is None:
            positions_dict = {tel.get_code(): pos for tel, pos in zip(telescopes, gcrs_positions[:, 0, :])}
            visibility = np.array([self._compute_visibility_at_time(source, telescopes, times[0], positions_dict)[tel.get_code()] for tel in telescopes])
            visibility = np.repeat(visibility[:, None], len(times), axis=1)  # shape: (n_tels, n_times)

        # compute baselines
        n_tels = len(telescopes)
        n_times = len(times)
        baselines = np.zeros((n_tels, n_tels, n_times, 3))
        for i in range(n_tels):
            for j in range(i + 1, n_tels):
                baselines[i, j] = gcrs_positions[i] - gcrs_positions[j]
                baselines[j, i] = -baselines[i, j]

        # compute UVW coordinates
        X, Y, Z = baselines[:, :, :, 0], baselines[:, :, :, 1], baselines[:, :, :, 2]
        uu = -np.sin(ra) * X + np.cos(ra) * Y
        vv = -np.cos(ra) * np.sin(dec) * X - np.sin(ra) * np.sin(dec) * Y + np.cos(dec) * Z
        ww = np.cos(ra) * np.cos(dec) * X + np.sin(ra) * np.cos(dec) * Y + np.sin(dec) * Z

        # apply visibility mask
        vis_mask = visibility[:, None, :] & visibility[None, :, :]  # shape: (n_tels, n_tels, n_times)

        # collect UV points for each frequency
        for freq in frequencies:
            wavelength = c / freq
            uvw_scaled = np.stack([uu / wavelength, vv / wavelength, ww / wavelength], axis=-1)  # shape: (n_tels, n_tels, n_times, 3)
            uvw_array = []
            pairs = []
            for i in range(n_tels):
                for j in range(i + 1, n_tels):
                    pair = f"{telescopes[i].get_code()}-{telescopes[j].get_code()}"
                    valid = vis_mask[i, j]
                    if valid.any():
                        uvw_points = uvw_scaled[i, j][valid]  # shape: (n_valid, 3)
                        uvw_array.extend(uvw_points)
                        pairs.extend([pair] * len(uvw_points))
            if uvw_array:
                uvw_array = np.array(uvw_array)  # shape: (n_points, 3)
                for idx, pair in enumerate(pairs):
                    uv_points[freq].append((pair, float(uvw_array[idx, 0]), float(uvw_array[idx, 1]), float(uvw_array[idx, 2])))

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
                observations = obj.get_observations()
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
                sources = obj.get_sources()
                telescopes = obj.get_telescopes()
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": attrs.get("recalculate", False)}
                position_data = self._calculate_telescope_positions(obj, position_attrs)
                if not position_data:
                    logger.error(f"failed to obtain telescope positions for '{obj.get_observation_code()}'")
                    return {}
                results = {}
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_sun_angles, scan, sources, telescopes, time_step, position_data): scan.name
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

    def _process_sun_angles(self, scan: Scan, sources: Sources, telescopes: Telescopes, time_step: Optional[float], position_data: Dict[str, Any]) -> Dict[str, Any]:
        """process sun angles for a single scan using vectorized computations.

        args:
            scan (Scan): the scan to process.
            sources (Sources): collection of sources.
            telescopes (Telescopes): collection of telescopes.
            time_step (Optional[float]): sampling interval (seconds). if None, uses mean time.
            position_data (Dict[str, Any]): precomputed telescope positions.

        returns:
            Dict[str, Any]: sun angles per telescope, with times if sampled.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        source = sources.get(scan.get_source_name())
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
        telescope_names = scan.get_telescope_names()
        active_telescopes = [telescopes.get(i) for i in telescope_names if telescopes.get(i).isactive]
        scan_name = scan.name

        # define time array
        if time_step is None:
            times = Time(start_time + (duration / 2) * u.s)
            times = times.reshape(-1)  # ensure 1D array for consistency
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')

        # split telescopes into ground and space
        ground_tels = [tel for tel in active_telescopes if not isinstance(tel, SpaceTelescope)]
        space_tels = [tel for tel in active_telescopes if isinstance(tel, SpaceTelescope)]

        # initialize angles array
        angles = np.full((len(active_telescopes), len(times)), np.nan, dtype=float)
        scan_positions = position_data.get(scan_name, {}).get("telescope_positions", {})

        # process ground telescopes
        if ground_tels:
            # vectorized computation of ITRS coordinates
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

            # transform source and Sun to AltAz
            altaz_frame = AltAz(obstime=times, location=locations)
            source_altaz = source_coord.transform_to(altaz_frame)
            sun_gcrs = get_sun(times)
            sun_altaz = sun_gcrs.transform_to(altaz_frame)

            # compute separations
            separations = source_altaz.separation(sun_altaz).deg
            separations = np.where((source_altaz.alt.deg < 0) | (sun_altaz.alt.deg < 0), np.nan, separations)

            # assign results
            for idx, tel_code in enumerate(ground_codes):
                tel_idx = [tel.get_code() for tel in active_telescopes].index(tel_code)
                angles[tel_idx] = separations[idx]

        # process space telescopes
        if space_tels:
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
                    logger.warning(f"no or mismatched position data for telescope '{tel_code}' in scan {scan_name}")
                    continue

                # vectorized computation
                vec_to_sun = sun_pos - positions  # shape: (n_times, 3)
                vec_to_sun /= np.linalg.norm(vec_to_sun, axis=1)[:, None]  # normalize each vector
                cos_angles = np.clip(np.dot(vec_to_sun, source_dir), -1.0, 1.0)
                tel_angles = np.degrees(np.arccos(cos_angles))
                angles[tel_idx] = tel_angles

        # convert angles to dictionary for visualizer compatibility
        angles_dict = {tel.get_code(): angles[i].tolist() for i, tel in enumerate(active_telescopes)}

        # format output
        result = {"source": source.name, "sun_angles": angles_dict}
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
                res = tel.get(["vx", "vy", "vz"])
                vx = res["vx"]
                vy = res["vy"]
                vz = res["vz"]
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
                observations = obj.get_observations()
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
                sources = obj.get_sources()
                telescopes = obj.get_telescopes()
                results = {}
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_az_el, scan, sources, telescopes, time_step): scan.name
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

    def _process_az_el(self, scan: Scan, sources: Sources, telescopes: Telescopes, time_step: Optional[float]) -> Dict[str, Any]:
        """Process Az/El or HA/Dec for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            sources (Sources): Collection of sources.
            telescopes (Telescopes): Collection of telescopes.
            time_step (Optional[float]): Sampling interval (seconds). If None, uses mean time.

        Returns:
            Dict[str, Any]: Coordinate data per telescope, with times if sampled彼此: Dict[str, Any]: Coordinate data per telescope, with times if sampled.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        source = sources.get(scan.get_source_name())
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
        telescope_names = scan.get_telescope_names()
        active_ground_tels = [tel for tel in (telescopes.get(i) for i in telescope_names)
                            if tel.isactive and not isinstance(tel, SpaceTelescope)]
        scan_name = scan.name

        if not active_ground_tels:
            logger.warning(f"No active ground telescopes for scan {scan_name} starting at {start_time.isot}")
            return {"source": source.name, "az_el": {}}

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
        result = {"source": source.name, "az_el": az_el}
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
                observations = obj.get_observations()
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
                        executor.submit(self._process_time_on_source, scan, sources, telescopes, time_step, visibility_data, obj): scan.name
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
        
    def _process_time_on_source(self, scan: Scan, sources: Sources, telescopes: Telescopes, time_step: float, visibility_data: Dict[str, Any], observation: Observation) -> Dict[str, Any]:
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
        source = sources.get(scan.source_name)
        scan_name = scan.name
        telescope_names = scan.get_telescope_names()
        active_telescopes = [telescopes.get(i) for i in telescope_names if telescopes.get(i).isactive]

        time_values = np.arange(0, duration, time_step) * u.s
        times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')

        scan_data = visibility_data.get(scan_name, {}) if isinstance(visibility_data, dict) else {}
        visibility = scan_data.get("visibility", {})
        if not visibility:
            logger.warning(f"No visibility data for scan {scan_name} in observation '{observation.get_observation_code()}'")
            return {"source": source.name, "visibility_blocks": {}}

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

        return {"source": source.name, "visibility_blocks": blocks}

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
                observations = obj.get_observations()
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
        """calculate synthesized beam for VLBI observations.

        args:
            obj (Observation | ScheduleProject): the object to calculate synthesized beam for.
            attributes (Dict[str, Any]): parameters including "freq_name", "time_step", and "store_key".

        returns:
            Dict[str, Any]: synthesized beam data.
        """
        try:
            freq_name = attributes.get("freq_name")
            store_key = attributes.get("store_key", f"synthesized_beam_{freq_name}")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_observations()
                results = {}
                for obs in observations:
                    obs_result = self._calculate_synthesized_beam(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                return results

            if obj.get_observation_type() != "VLBI":
                logger.warning(f"synthesized beam calculation is only for VLBI, got {obj.get_observation_type()}")
                return {}

            def calculate_synthesized_beam(obj, attrs):
                frequency = obj.get_frequencies().get(freq_name).get("frequency") * 1e6
                uv_store_key = f"uv_coverage_{freq_name}"
                uv_data = self._calculate_uv_coverage(obj, {
                    "time_step": attrs.get("time_step"),
                    "freq_name": freq_name,
                    "store_key": uv_store_key,
                    "recalculate": attrs.get("recalculate", False)
                })
                if not uv_data:
                    logger.warning(f"no UV data available for '{obj.get_observation_code()}'")
                    return {}

                u = []
                v = []
                for scan_name, scan_data in uv_data.items():
                    uv_points = scan_data.get("uv_points", {}).get(frequency, [])
                    if not uv_points:
                        continue
                    u.extend([point[1] for point in uv_points])
                    v.extend([point[2] for point in uv_points])
                if not u or not v:
                    logger.warning(f"no valid UV points for frequency {frequency/1e6} MHz")
                    return {}

                u = np.array(u)
                v = np.array(v)
                u_max = np.max(np.abs(u))
                v_max = np.max(np.abs(v))
                grid_size = 512
                u_grid = np.linspace(-u_max, u_max, grid_size)
                v_grid = np.linspace(-v_max, v_max, grid_size)
                uv_plane = np.zeros((grid_size, grid_size), dtype=complex)
                for uu, vv in zip(u, v):
                    u_idx = int((uu + u_max) / (2 * u_max) * (grid_size - 1))
                    v_idx = int((vv + v_max) / (2 * v_max) * (grid_size - 1))
                    if 0 <= u_idx < grid_size and 0 <= v_idx < grid_size:
                        uv_plane[v_idx, u_idx] = 1.0
                    u_idx = int((-uu + u_max) / (2 * u_max) * (grid_size - 1))
                    v_idx = int((-vv + v_max) / (2 * v_max) * (grid_size - 1))
                    if 0 <= u_idx < grid_size and 0 <= v_idx < grid_size:
                        uv_plane[v_idx, u_idx] = 1.0
                beam_2d = fftshift(fft2(uv_plane))
                beam_2d = np.abs(beam_2d)
                beam_2d /= np.max(beam_2d)
                wavelength = 299792458 / frequency
                theta_u_max = wavelength / (2 * u_max)
                theta_v_max = wavelength / (2 * v_max)
                theta_u = np.linspace(-theta_u_max, theta_u_max, grid_size)
                theta_v = np.linspace(-theta_v_max, theta_v_max, grid_size)
                theta_u_deg = np.degrees(theta_u)
                theta_v_deg = np.degrees(theta_v)
                return {
                    0: {
                        "theta_u": theta_u_deg.tolist(),
                        "theta_v": theta_v_deg.tolist(),
                        "beam_2d": beam_2d.tolist()  # convert to list for visualizer compatibility
                    }
                }

            metadata = {"freq_name": freq_name, "time_step": attributes.get("time_step")}
            return self._get_cached_or_calculate(obj, store_key, calculate_synthesized_beam, attributes, metadata)
        except Exception as e:
            logger.error(f"failed to calculate synthesized beam: {str(e)}")
            return {}
    
    @time_execution
    def _calculate_baseline_projections(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """calculate baseline projections for VLBI observations.

        args:
            obj (Observation | ScheduleProject): the object to calculate projections for.
            attributes (Dict[str, Any]): parameters including "time_step", "freq_name", and "store_key".

        returns:
            Dict[str, Any]: baseline projection data per scan.
        """
        try:
            time_step = attributes.get("time_step")
            freq_name = attributes.get("freq_name")
            store_key = attributes.get("store_key", f"baseline_projections_{freq_name}")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_observations()
                if not observations:
                    logger.warning(f"no observations in project '{obj.name}'")
                    return {}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_baseline_projections(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"calculated baseline projections for {len(observations)} observations in project '{obj.name}'")
                return results

            if obj.get_observation_type() != "VLBI":
                logger.warning(f"baseline projections are only for VLBI, got {obj.get_observation_type()}")
                return {}

            def calculate_baseline_projections(obj, attrs):
                scans = obj.get_scans().get_active_items()
                telescopes = obj.get_telescopes()
                frequencies = obj.get_frequencies()
                active_telescopes = telescopes.get_active_items()
                if len(active_telescopes) < 2:
                    logger.error(f"VLBI requires at least 2 active telescopes, got {len(active_telescopes)}")
                    return {}
                uv_store_key = f"uv_coverage_{freq_name}"
                uv_data = self._calculate_uv_coverage(obj, {
                    "time_step": time_step,
                    "freq_name": freq_name,
                    "store_key": uv_store_key,
                    "recalculate": attrs.get("recalculate", False)
                })
                if not uv_data:
                    logger.error(f"failed to obtain UV coverage data for '{obj.get_observation_code()}'")
                    return {}
                results = {}
                with ThreadPoolExecutor() as executor:
                    futures = {
                        executor.submit(self._process_baseline_projections, scan, telescopes, frequencies, time_step, freq_name, uv_data, obj): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        results[scan_name] = future.result()
                return results

            metadata = {"time_step": time_step, "freq_name": freq_name, "scan_count": len(obj.get_scans().get_active_items())}
            return self._get_cached_or_calculate(obj, store_key, calculate_baseline_projections, attributes, metadata)
        except Exception as e:
            logger.error(f"failed to calculate baseline projections: {str(e)}")
            return {}

    def _process_baseline_projections(self, scan: Scan, telescopes: Telescopes, frequencies: Frequencies, time_step: Optional[float], freq_name: int, uv_data: Dict[str, Any], observation: Observation) -> Dict[str, Any]:
        """process baseline projections for a single scan.

        args:
            scan (Scan): the scan to process.
            telescopes (Telescopes): collection of telescopes.
            frequencies (Frequencies): collection of frequencies.
            time_step (Optional[float]): sampling interval (seconds).
            freq_name (int): frequency index.
            uv_data (Dict[str, Any]): precomputed UV data.
            observation (Observation): parent observation.

        returns:
            Dict[str, Any]: baseline projections per telescope pair.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        telescope_names = scan.get_telescope_names()
        active_telescopes = [telescopes.get(i) for i in telescope_names if telescopes.get(i).isactive]
        frequency = frequencies.get(freq_name).get("frequency") * 1e6
        scan_name = scan.name

        scan_uv_data = uv_data.get(scan_name, {}) if isinstance(uv_data, dict) else {}
        if not scan_uv_data or "uv_points" not in scan_uv_data:
            logger.error(f"no UV data available for scan {scan_name} at {start_time.isot}")
            return {"projections": {} if time_step is None else {"times": [], "projections": {}}}

        if time_step is None:
            projections = self._compute_projections_from_uv(scan_uv_data["uv_points"], active_telescopes, frequency)
            return {"projections": projections}
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
            projections = {
                f"{t1.get_code()}-{t2.get_code()}": np.full(len(times), np.nan, dtype=float)
                for i, t1 in enumerate(active_telescopes)
                for t2 in active_telescopes[i+1:]
            }
            uv_points = scan_uv_data.get("uv_points", {}).get(frequency, [])
            if not uv_points:
                logger.warning(f"no UV points found for frequency {frequency} in scan {scan_name}")
                return {"times": times.isot.tolist(), "projections": {k: v.tolist() for k, v in projections.items()}}

            # collect UV points into arrays
            for uv_point in uv_points:
                pair, uuu, vvv, _ = uv_point
                bl = np.sqrt(uuu * uuu + vvv * vvv)
                if pair in projections:
                    # assume UV points align with times; fill first available NaN
                    idx = np.where(np.isnan(projections[pair]))[0]
                    if len(idx) > 0:
                        projections[pair][idx[0]] = bl

            return {"times": times.isot.tolist(), "projections": {k: v.tolist() for k, v in projections.items()}}
        
    def _compute_projections_from_uv(self, uv_points: Dict[float, List[Tuple[str, float, float, float]]], telescopes: List[Telescope | SpaceTelescope], frequency: float) -> Dict[str, float]:
        """compute baseline projection BL = sqrt(u² + v²) from pre-calculated (u,v) data.

        args:
            uv_points (Dict[float, List[Tuple[str, float, float, float]]]): UV data.
            telescopes (List[Telescope | SpaceTelescope]): list of telescopes.
            frequency (float): frequency in Hz.

        returns:
            Dict[str, float]: baseline length per telescope pair.
        """
        projections = {}
        uv_list = uv_points.get(frequency, [])
        for pair, uuu, vvv, _ in uv_list:
            bl = np.sqrt(uuu * uuu + vvv * vvv)  # BL = sqrt(u² + v²)
            projections[pair] = bl
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
                observations = obj.get_observations()
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
                sources = obj.get_sources()
                telescopes = obj.get_telescopes()
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": attrs.get("recalculate", False)}
                position_data = self._calculate_telescope_positions(obj, position_attrs)
                results = {}
                with ThreadPoolExecutor() as executor:
                    futures = {
                        executor.submit(self._process_mollweide_tracks, scan, sources, telescopes, time_step, position_data, obj): i
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

    def _process_mollweide_tracks(self, scan: Scan, sources: Sources, telescopes: Telescopes, time_step: Optional[float], position_data: Dict[str, Any], observation: Observation) -> Dict[str, Any]:
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
        source = sources.get(scan.source_name)
        telescope_names = scan.telescope_names
        active_telescopes = [telescopes.get(i) for i in telescope_names if telescopes.get(i).isactive]
        scan_name = scan.name
        if not position_data or scan_name not in position_data:
            source = sources.get(scan.get_source_name)
            source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
            source_lon, source_lat = self._compute_mollweide_coords(source_coord)
            logger.error(f"No position data for scan {scan_name}")
            return {"source": {"name": source.name, "lon": source_lon, "lat": source_lat}, "telescope_tracks": {}}
        
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
        source_lon, source_lat = self._compute_mollweide_coords(source_coord)      
        
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
            "source": {"name": source.name, "lon": source_lon, "lat": source_lat},
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
    

