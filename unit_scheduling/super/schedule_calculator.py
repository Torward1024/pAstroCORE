from abc import ABC
from common.super.super import Super
from common.utils.logging_setup import logger

from unit_scheduling.base.frequencies import Frequencies
from unit_scheduling.base.sources import Sources, Source
from unit_scheduling.base.telescopes import Telescope, SpaceTelescope, Telescopes, MountType
from unit_scheduling.base.scans import Scan
from unit_scheduling.base.observation import Observation
from unit_scheduling.super.schedule_project import ScheduleProject

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
        obj_name = obj.get_name() if isinstance(obj, ScheduleProject) else obj.get_observation_code()
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
        >>> result = calculator.calculate(obs, {"store_key": "uv_coverage_f0", "freq_idx": 0})
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
        """Calculate visibility of a source or spacecraft from telescopes over a time range.

        Args:
            obj (Observation | ScheduleProject): The object to calculate visibility for.
            attributes (Dict[str, Any]): Parameters including "time_step", "target_type", "start_time", "end_time".

        Returns:
            Dict[str, Any]: Visibility data per scan or time range.
        """
        try:
            time_step = attributes.get("time_step", 3600)
            start_time = attributes.get("start_time")
            end_time = attributes.get("end_time")
            telescope_code = attributes.get("telescope_code")
            target_type = attributes.get("target_type", "source")
            target_index = attributes.get("target_index", 0)
            store_key = attributes.get("store_key", "visibility")
            position_store_key = attributes.get("position_store_key", "telescope_positions")
            recalculate = attributes.get("recalculate", False)

            if isinstance(obj, ScheduleProject):
                observations = obj.get_observations()
                if not observations:
                    logger.warning(f"No observations in project '{obj.get_name()}'")
                    return {}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_source_visibility(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"Calculated visibility for {len(observations)} observations in project '{obj.get_name()}'")
                return results

            telescopes = obj.get_telescopes()
            active_telescopes = telescopes.get_active_telescopes()
            if not active_telescopes:
                logger.warning(f"No active telescopes in observation '{obj.get_observation_code()}'")
                return {}
            if telescope_code:
                target_telescope = next((tel for tel in active_telescopes if tel.get_code() == telescope_code), None)
                if not target_telescope:
                    logger.error(f"Telescope '{telescope_code}' not found in observation '{obj.get_observation_code()}'")
                    return {}
                active_telescopes = [target_telescope]

            if target_type == "source":
                sources = obj.get_sources()
                target = sources.get_by_index(target_index)
                target_name = target.get_name()
            elif target_type == "spacecraft":
                all_telescopes = telescopes.get_all_telescopes()
                target = next((tel for tel in all_telescopes if isinstance(tel, SpaceTelescope)), None)
                if not target:
                    logger.error(f"No SpaceTelescope found in observation '{obj.get_observation_code()}'")
                    return {}
                target_name = target.get_code()
            else:
                logger.error(f"Unsupported target_type: {target_type}. Use 'source' or 'spacecraft'")
                return {}

            def calculate_visibility(obj, attrs):
                # Определяем временной диапазон
                if start_time and end_time:
                    start = Time(start_time)
                    end = Time(end_time)
                    use_scans = False
                else:
                    scans = obj.get_scans().get_active_scans(obj)
                    if not scans:
                        logger.warning(f"No active scans or time range in observation '{obj.get_observation_code()}'")
                        return {}
                    start_times = [scan.get_start() for scan in scans]
                    end_times = [scan.get_start() + scan.get_duration() * u.s for scan in scans]
                    start = min(start_times)
                    end = max(end_times)
                    use_scans = True

                time_values = np.arange(0, (end - start).sec, time_step) * u.s
                times = Time(start.mjd + time_values.to(u.d).value, format='mjd')
                logger.info(f"Calculating visibility for {len(times)} time points from {start.isot} to {end.isot}")

                if target_type == "spacecraft":
                    logger.info(f"Interpolating orbit for {target_name}")
                    target.interpolate_orbit(start, end, time_step)

                position_attrs = {
                    "time_step": time_step,
                    "store_key": position_store_key,
                    "recalculate": recalculate,
                    "start_time": start.isot,
                    "end_time": end.isot
                }
                position_data = self._calculate_telescope_positions(obj, position_attrs)
                if not position_data:
                    logger.error(f"Failed to obtain telescope positions for '{obj.get_observation_code()}'")
                    return {}

                if use_scans:
                    results = {}
                    for i, scan in enumerate(scans):
                        scan_start = scan.get_start()
                        scan_duration = scan.get_duration()
                        scan_times = [t for t in times if scan_start <= t <= scan_start + scan_duration * u.s]
                        if not scan_times:
                            continue
                        visibility = {tel.get_code(): [] for tel in active_telescopes}
                        tel_positions_data = position_data.get(i, {}).get("telescope_positions", {})
                        for t in scan_times:
                            tel_positions = {}
                            for tel in active_telescopes:
                                pos_data = tel_positions_data.get(tel.get_code(), {})
                                t_idx = pos_data["times"].index(t.isot) if "times" in pos_data else 0
                                tel_positions[tel.get_code()] = pos_data["positions"][t_idx]
                            vis = self._compute_visibility_at_time(target, active_telescopes, t, tel_positions, target_type)
                            for tel_code, is_visible in vis.items():
                                visibility[tel_code].append(is_visible)
                        results[i] = {
                            "target": target_name,
                            "target_type": target_type,
                            "times": [t.isot for t in scan_times],
                            "visibility": visibility
                        }
                    #logger.info(f"Visibility calculated for {len(results)} scans")
                    return results
                else:
                    visibility = {tel.get_code(): [] for tel in active_telescopes}
                    tel_positions_data = position_data.get(0, {}).get("telescope_positions", {})
                    for t_idx, t in enumerate(times):
                        tel_positions = {}
                        for tel in active_telescopes:
                            pos_data = tel_positions_data.get(tel.get_code(), {})
                            if "positions" not in pos_data or t_idx >= len(pos_data["positions"]):
                                logger.warning(f"No position data for {tel.get_code()} at {t.isot}, using default")
                                tel_positions[tel.get_code()] = (0.0, 0.0, 0.0)
                            else:
                                tel_positions[tel.get_code()] = pos_data["positions"][t_idx]
                        vis = self._compute_visibility_at_time(target, active_telescopes, t, tel_positions, target_type)
                        for tel_code, is_visible in vis.items():
                            visibility[tel_code].append(is_visible)
                    result = {
                        "target": target_name,
                        "target_type": target_type,
                        "times": times.isot.tolist(),
                        "visibility": visibility
                    }
                    #logger.info(f"Visibility calculation result: {result}")
                    return {0: result}

            metadata = {"time_step": time_step, "start_time": start_time, "end_time": end_time, "telescope_code": telescope_code}
            return self._get_cached_or_calculate(obj, store_key, calculate_visibility, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate visibility: {str(e)}")
            return {}
    

    def _compute_visibility_at_time(self, target: Source | SpaceTelescope, telescopes: List[Telescope | SpaceTelescope], time: Time, positions: Dict[str, Tuple[float, float, float]], target_type: str) -> Dict[str, bool]:
        """Compute visibility of a target (source or spacecraft) for telescopes at a given time.

        Args:
            target (Source | SpaceTelescope): The target to check visibility for.
            telescopes (List[Telescope | SpaceTelescope]): List of telescopes.
            time (Time): The time of observation.
            positions (Dict[str, Tuple[float, float, float]]): Precomputed GCRS positions.
            target_type (str): "source" or "spacecraft".

        Returns:
            Dict[str, bool]: Visibility status per telescope code.
        """
        visibility = {}

        # Координаты цели
        if target_type == "source":
            target_coord = SkyCoord(ra=target.get_ra_degrees() * u.deg, dec=target.get_dec_degrees() * u.deg, frame='icrs')
        elif target_type == "spacecraft":
            spacecraft_pos, _ = target.get_state_vector(time)
            target_coord = GCRS(CartesianRepresentation(*spacecraft_pos, unit=u.m), obstime=time)
        else:
            logger.error(f"Invalid target_type: {target_type}")
            return {}

        for tel in telescopes:
            pos = positions.get(tel.get_code())
            if not pos:
                logger.warning(f"No position data for telescope '{tel.get_code()}' at {time.isot}")
                visibility[tel.get_code()] = False
                continue

            itrs = ITRS(CartesianRepresentation(*pos, unit=u.m), obstime=time)
            location = itrs.earth_location
            altaz = target_coord.transform_to(AltAz(obstime=time, location=location))

            if isinstance(tel, SpaceTelescope):
                pitch = altaz.alt.deg
                yaw = altaz.az.deg
                pitch_range = tel.get_pitch_range()
                yaw_range = tel.get_yaw_range()
                is_visible = (pitch_range[0] <= pitch <= pitch_range[1]) and (yaw_range[0] <= yaw <= yaw_range[1])
            else:
                el = altaz.alt.deg
                az = altaz.az.deg
                hadec = target_coord.transform_to(HADec(obstime=time, location=location))
                ha = hadec.ha.deg
                mount_type = tel.get_mount_type()
                if mount_type == MountType.AZIMUTHAL:
                    el_range = tel.get_elevation_range()
                    az_range = tel.get_azimuth_range()
                    is_visible = (el_range[0] <= el <= el_range[1]) and (az_range[0] <= az <= az_range[1])
                elif mount_type == MountType.EQUATORIAL:
                    dec = hadec.dec.deg
                    ha_range = tel.get_azimuth_range()
                    dec_range = tel.get_elevation_range()
                    is_visible = (dec_range[0] <= dec <= dec_range[1]) and (ha_range[0] <= ha <= ha_range[1])
                else:
                    logger.warning(f"Unsupported mount type {mount_type} for telescope '{tel.get_code()}'")
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
        """
        try:
            time_step = attributes.get("time_step", 3600)
            start_time = attributes.get("start_time")
            end_time = attributes.get("end_time")
            store_key = attributes.get("store_key", "telescope_positions")
            recalculate = attributes.get("recalculate", False)

            def calculate_positions(obj, attrs):
                if isinstance(obj, ScheduleProject):
                    observations = obj.get_observations()
                    if not observations:
                        logger.warning(f"No observations in project '{obj.get_name()}'")
                        return {}
                    results = {}
                    with ThreadPoolExecutor() as executor:
                        futures = {
                            executor.submit(self._calculate_telescope_positions, obs, attrs): obs.get_observation_code()
                            for obs in observations
                        }
                        for future in futures:
                            obs_code = futures[future]
                            results[obs_code] = future.result()
                    logger.info(f"Calculated telescope positions for {len(observations)} observations in project '{obj.get_name()}'")
                    return results

                telescopes = obj.get_telescopes()
                active_telescopes = telescopes.get_active_telescopes()
                if not active_telescopes:
                    logger.warning(f"No active telescopes in observation '{obj.get_observation_code()}'")
                    return {}

                # Определяем временной диапазон
                if start_time and end_time:
                    start = Time(start_time)
                    end = Time(end_time)
                    use_scans = False
                else:
                    scans = obj.get_scans().get_active_scans(obj)
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
                logger.info(f"Calculating telescope positions for {len(times)} time points from {start.isot} to {end.isot}")

                # Интерполяция орбит для космических телескопов
                for tel in active_telescopes:
                    if isinstance(tel, SpaceTelescope) and time_step and not tel.get_use_kep():
                        logger.info(f"Interpolating orbit for {tel.get_code()}")
                        tel.interpolate_orbit(start, end, time_step)

                # Вычисляем позиции
                results = {}
                if use_scans and time_step:
                    for i, scan in enumerate(scans):
                        scan_start = scan.get_start()
                        scan_duration = scan.get_duration()
                        scan_times = [t for t in times if scan_start <= t <= scan_start + scan_duration * u.s]
                        if not scan_times:
                            continue
                        tel_positions = {}
                        for tel in active_telescopes:
                            positions = [self._compute_telescope_position(tel, t) for t in scan_times]
                            tel_positions[tel.get_code()] = {"times": [t.isot for t in scan_times], "positions": positions}
                        results[i] = {"telescope_positions": tel_positions}
                else:
                    tel_positions = {}
                    for tel in active_telescopes:
                        positions = [self._compute_telescope_position(tel, t) for t in times]
                        tel_positions[tel.get_code()] = {"times": [t.isot for t in times], "positions": positions}
                    results[0] = {"telescope_positions": tel_positions}

                logger.info(f"Calculated telescope positions for {len(results)} entries in '{obj.get_observation_code()}'")
                return results

            metadata = {"time_step": time_step, "start_time": start_time, "end_time": end_time}
            return self._get_cached_or_calculate(obj, store_key, calculate_positions, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate telescope positions: {str(e)}")
            return {}
    
    # @time_execution
    # def _calculate_telescope_positions(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
    #     """Calculate telescope positions in GCRS (J2000) for all scans.

    #     Args:
    #         obj (Observation | ScheduleProject): The object to calculate positions for.
    #         attributes (Dict[str, Any]): Parameters including "time_step" (sampling interval in seconds) and "store_key".

    #     Returns:
    #         Dict[str, Any]: Telescope positions per scan, keyed by observation code (for Project) or scan index (for Observation).

    #     Notes:
    #         - For Projects, processes all observations in parallel.
    #         - For SpaceTelescopes, interpolates orbits if needed.
    #         - Returns empty dict on failure with error logging.
    #     """
    #     try:
    #         time_step = attributes.get("time_step")
    #         store_key = attributes.get("store_key", "telescope_positions")

    #         def calculate_positions(obj, attrs):
    #             if isinstance(obj, ScheduleProject):
    #                 observations = obj.get_observations()
    #                 if not observations:
    #                     logger.warning(f"No observations in project '{obj.get_name()}'")
    #                     return {}
    #                 results = {}
    #                 with ThreadPoolExecutor() as executor:
    #                     futures = {
    #                         executor.submit(self._calculate_telescope_positions, obs, attrs): obs.get_observation_code()
    #                         for obs in observations
    #                     }
    #                     for future in futures:
    #                         obs_code = futures[future]
    #                         try:
    #                             results[obs_code] = future.result()
    #                         except Exception as e:
    #                             logger.error(f"Failed to process observation '{obs_code}': {str(e)}")
    #                 logger.info(f"Calculated telescope positions for {len(observations)} observations in project '{obj.get_name()}'")
    #                 return results

    #             telescopes = obj.get_telescopes()
    #             scans = obj.get_scans().get_active_scans(obj)
    #             if not scans:
    #                 logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
    #                 return {}

    #             if time_step and scans:
    #                 start_times = [scan.get_start() for scan in scans]
    #                 end_times = [scan.get_start() + scan.get_duration() * u.s for scan in scans]
    #                 obs_start = min(start_times)
    #                 obs_end = max(end_times)
    #                 for tel in telescopes.get_active_telescopes():
    #                     if isinstance(tel, SpaceTelescope) and not tel.get_use_kep():
    #                         logger.info(f"Interpolating orbit for {tel.get_code()}")
    #                         tel.interpolate_orbit(obs_start, obs_end, time_step)

    #             results = {}
    #             with ThreadPoolExecutor() as executor:
    #                 futures = {
    #                     executor.submit(self._process_scan_positions, scan, telescopes, time_step): i
    #                     for i, scan in enumerate(scans)
    #                 }
    #                 for future in futures:
    #                     scan_idx = futures[future]
    #                     try:
    #                         results[scan_idx] = future.result()
    #                     except Exception as e:
    #                         logger.error(f"Failed to process scan {scan_idx}: {str(e)}")
    #             logger.info(f"Calculated telescope positions for {len(scans)} scans in '{obj.get_observation_code()}'")
    #             return results

    #         metadata = {
    #             "time_step": time_step,
    #             "scan_count": len(obj.get_scans().get_active_scans(obj)) if not isinstance(obj, ScheduleProject) else None,
    #             "telescope_count": len(obj.get_telescopes().get_active_telescopes()) if not isinstance(obj, ScheduleProject) else None
    #         }
    #         return self._get_cached_or_calculate(obj, store_key, calculate_positions, attributes, metadata)
    #     except Exception as e:
    #         logger.error(f"Failed to calculate telescope positions: {str(e)}")
    #         return {}

    def _process_scan_positions(self, scan: Scan, telescopes: Telescopes, time_step: Optional[float]) -> Dict[str, Any]:
        """Process telescope positions for a single scan.

        Args:
            scan (Scan): The scan to process.
            telescopes (Telescopes): Collection of telescopes involved in the scan.
            time_step (Optional[float]): Time interval for position sampling (seconds). If None, uses mean time.

        Returns:
            Dict[str, Any]: Positions for active telescopes, with times if time_step is provided.

        Notes:
            - Returns positions at mean time if time_step is None, otherwise samples over duration.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        telescope_indices = scan.get_telescope_indices()
        active_telescopes = [telescopes.get_by_index(i) for i in telescope_indices if telescopes.get_by_index(i).isactive]

        if not active_telescopes:
            logger.warning(f"No active telescopes for scan starting at {start_time.isot}")
            return {"telescope_positions": {}}

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            positions = {tel.get_code(): self._compute_telescope_position(tel, mean_time) for tel in active_telescopes}
            return {"telescope_positions": positions}
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
            result = {}
            for tel in active_telescopes:
                tel_positions = [self._compute_telescope_position(tel, t) for t in times]
                result[tel.get_code()] = {"times": times.isot.tolist(), "positions": tel_positions}
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
            vx, vy, vz = telescope.get_velocities()
            dt = (time - Time("2000-01-01T12:00:00")).sec
            itrs_coords = CartesianRepresentation(x + vx * dt, y + vy * dt, z + vz * dt, unit=u.m)
            itrs = ITRS(itrs_coords, obstime=time)
            gcrs = itrs.transform_to(GCRS(obstime=time))
            return (gcrs.cartesian.x.value, gcrs.cartesian.y.value, gcrs.cartesian.z.value)
        elif isinstance(telescope, SpaceTelescope):
            pos, _ = telescope.get_state_vector(time)
            return tuple(float(p) for p in pos)
        raise ValueError(f"Unsupported telescope type: {type(telescope)}")

    

    def _process_source_visibility(self, scan: Scan, telescopes: Telescopes, sources: Sources, time_step: Optional[float], position_data: Dict[str, Any], observation: Observation) -> Dict[str, Any]:
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
        source_idx = scan.get_source_index()
        source = sources.get_by_index(source_idx)
        telescope_indices = scan.get_telescope_indices()
        active_telescopes = [telescopes.get_by_index(i) for i in telescope_indices if telescopes.get_by_index(i).isactive]
        scan_idx = list(observation.get_scans().get_active_scans(observation)).index(scan)

        logger.info(f"Processing visibility for scan {scan_idx}: {len(active_telescopes)} telescopes")

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            positions = position_data.get(scan_idx, {}).get("telescope_positions", {})
            visibility = self._compute_visibility_at_time(source, active_telescopes, mean_time, positions)
            return {"source": source.get_name(), "visibility": visibility}
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
            visibility = {tel.get_code(): [] for tel in active_telescopes}
            positions = position_data.get(scan_idx, {}).get("telescope_positions", {})
            for t_idx, t in enumerate(times):
                pos_at_time = {}
                for tel in active_telescopes:
                    pos_data = positions.get(tel.get_code(), {})
                    if "positions" in pos_data:
                        pos_at_time[tel.get_code()] = pos_data["positions"][t_idx]
                    else:
                        pos_at_time[tel.get_code()] = pos_data
                vis = self._compute_visibility_at_time(source, active_telescopes, t, pos_at_time)
                for tel_code, is_visible in vis.items():
                    visibility[tel_code].append(is_visible)
            return {"source": source.get_name(), "times": times.isot.tolist(), "visibility": visibility}
    

        # @time_execution
    # def _calculate_source_visibility(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
    #     """Calculate source visibility for all scans.

    #     Args:
    #         obj (Observation | ScheduleProject): The object to calculate visibility for.
    #         attributes (Dict[str, Any]): Parameters including "time_step", "store_key", and "position_store_key".

    #     Returns:
    #         Dict[str, Any]: Visibility data per scan, keyed by observation code (for Project) or scan index (for Observation).

    #     Notes:
    #         - Depends on precomputed telescope positions.
    #         - Uses parallel processing for multiple scans.
    #     """
    #     try:
    #         time_step = attributes.get("time_step")
    #         store_key = attributes.get("store_key", "source_visibility")
    #         position_store_key = attributes.get("position_store_key", "telescope_positions")

    #         if isinstance(obj, ScheduleProject):
    #             observations = obj.get_observations()
    #             if not observations:
    #                 logger.warning(f"No observations in project '{obj.get_name()}'")
    #                 return {}
    #             results = {}
    #             for obs in observations:
    #                 obs_result = self._calculate_source_visibility(obs, attributes)
    #                 results[obs.get_observation_code()] = obs_result
    #             logger.info(f"Calculated source visibility for {len(observations)} observations in project '{obj.get_name()}'")
    #             return results

    #         def calculate_visibility(obj, attrs):
    #             scans = obj.get_scans().get_active_scans(obj)
    #             telescopes = obj.get_telescopes()
    #             sources = obj.get_sources()
    #             position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": attrs.get("recalculate", False)}
    #             position_data = self._calculate_telescope_positions(obj, position_attrs)
    #             if not position_data:
    #                 logger.error(f"Failed to obtain telescope positions for '{obj.get_observation_code()}'")
    #                 return {}
    #             results = {}
    #             if len(scans) > 1:
    #                 with ThreadPoolExecutor() as executor:
    #                     futures = {
    #                         executor.submit(self._process_source_visibility, scan, telescopes, sources, time_step, position_data, obj): i
    #                         for i, scan in enumerate(scans)
    #                     }
    #                     for future in futures:
    #                         scan_idx = futures[future]
    #                         results[scan_idx] = future.result()
    #             else:
    #                 results[0] = self._process_source_visibility(scans[0], telescopes, sources, time_step, position_data, obj)
    #             return results

    #         metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_scans(obj))}
    #         return self._get_cached_or_calculate(obj, store_key, calculate_visibility, attributes, metadata)
    #     except Exception as e:
    #         logger.error(f"Failed to calculate source visibility: {str(e)}")
    #         return {}
        
    # def _compute_visibility_at_time(self, source: Source, telescopes: List[Telescope | SpaceTelescope], time: Time, positions: Dict[str, Tuple[float, float, float]]) -> Dict[str, bool]:
    #     """Compute visibility of a source for telescopes at a given time using precomputed positions.

    #     Args:
    #         source (Source): The source to check visibility for.
    #         telescopes (List[Telescope | SpaceTelescope]): List of telescopes.
    #         time (Time): The time of observation.
    #         positions (Dict[str, Tuple[float, float, float]]): Precomputed GCRS positions.

    #     Returns:
    #         Dict[str, bool]: Visibility status per telescope code.
    #     """
    #     source_coord = SkyCoord(ra=source.get_ra_degrees() * u.deg, dec=source.get_dec_degrees() * u.deg, frame='icrs')
    #     visibility = {}
    #     for tel in telescopes:
    #         pos = positions.get(tel.get_code())
    #         if pos is None:
    #             logger.warning(f"No position data for telescope '{tel.get_code()}' at {time.isot}")
    #             visibility[tel.get_code()] = False
    #             continue

    #         if isinstance(tel, SpaceTelescope):
    #             itrs = ITRS(CartesianRepresentation(*pos, unit=u.m), obstime=time)
    #             altaz = source_coord.transform_to(AltAz(obstime=time, location=itrs.earth_location))
    #             pitch = altaz.alt.deg
    #             yaw = altaz.az.deg
    #             pitch_range = tel.get_pitch_range()
    #             yaw_range = tel.get_yaw_range()
    #             is_visible = (pitch_range[0] <= pitch <= pitch_range[1]) and (yaw_range[0] <= yaw <= yaw_range[1])
    #         else:
    #             gcrs = GCRS(CartesianRepresentation(*pos, unit=u.m), obstime=time)
    #             itrs = gcrs.transform_to(ITRS(obstime=time))
    #             location = itrs.earth_location
    #             altaz = source_coord.transform_to(AltAz(obstime=time, location=location))
    #             el = altaz.alt.deg
    #             az = altaz.az.deg
    #             hadec = source_coord.transform_to(HADec(obstime=time, location=location))
    #             ha = hadec.ha.deg

    #             mount_type = tel.get_mount_type()
    #             if mount_type == MountType.AZIMUTHAL:
    #                 el_range = tel.get_elevation_range()
    #                 az_range = tel.get_azimuth_range()
    #                 is_visible = (el_range[0] <= el <= el_range[1]) and (az_range[0] <= az <= az_range[1])
    #             elif mount_type == MountType.EQUATORIAL:
    #                 dec = hadec.dec.deg
    #                 ha_range = tel.get_azimuth_range()
    #                 dec_range = tel.get_elevation_range()
    #                 is_visible = (dec_range[0] <= dec <= dec_range[1]) and (ha_range[0] <= ha <= ha_range[1])
    #             else:
    #                 logger.warning(f"Unsupported mount type {mount_type} for telescope '{tel.get_code()}'")
    #                 is_visible = False
    #         visibility[tel.get_code()] = is_visible
    #     return visibility
    
    @time_execution
    def _calculate_uv_coverage(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate (u,v) coverage for all scans in the observation or project.

        Args:
            obj (Observation | ScheduleProject): The object to calculate UV coverage for.
            attributes (Dict[str, Any]): Parameters including "time_step", "freq_idx", and "store_key".

        Returns:
            Dict[str, Any]: UV coverage data per scan, including u, v, w coordinates.

        Notes:
            - Requires visibility and position data.
            - Computes UV points for all baselines at specified frequency.
        """
        try:
            time_step = attributes.get("time_step")
            freq_idx = attributes.get("freq_idx", 0)
            store_key = attributes.get("store_key", f"uv_coverage_f{freq_idx}")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_observations()
                if not observations:
                    logger.warning(f"No observations in project '{obj.get_name()}'")
                    return {}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_uv_coverage(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"Calculated (u,v) coverage for {len(observations)} observations in project '{obj.get_name()}'")
                return results

            def calculate_uv(obj, attrs):
                scans = obj.get_scans().get_active_scans(obj)
                telescopes = obj.get_telescopes()
                frequencies = obj.get_frequencies()
                results = {}

                visibility_attrs = {"time_step": time_step, "store_key": "source_visibility", "recalculate": attrs.get("recalculate", False)}
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": attrs.get("recalculate", False)}

                visibility_data = self._calculate_source_visibility(obj, visibility_attrs)
                position_data = self._calculate_telescope_positions(obj, position_attrs)
                
                if len(scans) > 1:
                    with ThreadPoolExecutor() as executor:
                        futures = {
                            executor.submit(self._process_uv_coverage, scan, telescopes, frequencies, time_step, freq_idx, obj, visibility_data, position_data): i
                            for i, scan in enumerate(scans)
                        }
                        for future in futures:
                            scan_idx = futures[future]
                            results[scan_idx] = future.result()
                else:
                    results[0] = self._process_uv_coverage(scans[0], telescopes, frequencies, time_step, freq_idx, obj, visibility_data, position_data)
                return results

            metadata = {"time_step": time_step, "freq_idx": freq_idx, "scan_count": len(obj.get_scans().get_active_scans(obj))}
            return self._get_cached_or_calculate(obj, store_key, calculate_uv, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate (u,v) coverage: {str(e)}")
            return {}

    def _process_uv_coverage(self, scan: Scan, telescopes: Telescopes, frequencies: Frequencies, time_step: Optional[float], freq_idx: Optional[int], observation: Observation, visibility_data: Dict[str, Any], position_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process UV coverage for a single scan.

        Args:
            scan (Scan): The scan to process.
            telescopes (Telescopes): Collection of telescopes.
            frequencies (Frequencies): Collection of frequencies.
            time_step (Optional[float]): Sampling interval (seconds).
            freq_idx (Optional[int]): Frequency index to use.
            observation (Observation): Parent observation.
            visibility_data (Dict[str, Any]): Precomputed visibility data.
            position_data (Dict[str, Any]): Precomputed position data.

        Returns:
            Dict[str, Any]: UV points per frequency, with times if sampled.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        active_telescopes = [telescopes.get_by_index(i) for i in scan.get_telescope_indices() if telescopes.get_by_index(i).isactive]
        freqs = [frequencies.get_by_index(i).get_frequency() * 1e6 for i in (scan.get_frequency_indices() if freq_idx is None else [freq_idx]) if frequencies.get_by_index(i).isactive]
        source = scan.get_source(observation=observation)
        scan_idx = list(observation.get_scans().get_active_scans(observation)).index(scan)

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            visibility = visibility_data.get(scan_idx, {}).get("visibility") if visibility_data else None
            gcrs_positions = position_data.get(scan_idx, {}).get("telescope_positions", {})
            gcrs_positions = [gcrs_positions[tel.get_code()] for tel in active_telescopes] if gcrs_positions else None
            uv = self._compute_uv_at_time(active_telescopes, mean_time, freqs, source, visibility, gcrs_positions)
            return {"uv_points": uv}
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
            uv_points = {f: [] for f in freqs}
            for t_idx, t in enumerate(times):
                visibility = visibility_data.get(scan_idx, {}).get("visibility", {})
                visibility = {tel_code: vis[t_idx] for tel_code, vis in visibility.items()} if visibility else None
                gcrs_positions = position_data.get(scan_idx, {}).get("telescope_positions", {})
                gcrs_positions = {tel_code: pos["positions"][t_idx] for tel_code, pos in gcrs_positions.items()} if gcrs_positions else {}
                gcrs_positions = [gcrs_positions.get(tel.get_code()) for tel in active_telescopes] if gcrs_positions else None
                uv = self._compute_uv_at_time(active_telescopes, t, freqs, source, visibility, gcrs_positions)
                for f, points in uv.items():
                    uv_points[f].extend(points)
            return {"times": times.isot.tolist(), "uv_points": uv_points}

    def _compute_uv_at_time(self, telescopes: List[Telescope | SpaceTelescope], time: Time, frequencies: List[float], source: Optional[Source] = None, visibility: Optional[Dict[str, bool]] = None, gcrs_positions: Optional[List[Tuple[float, float, float]]] = None) -> Dict[float, List[Tuple[str, float, float, float]]]:
        """Compute UV coordinates at a specific time.

        Args:
            telescopes (List[Telescope | SpaceTelescope]): List of telescopes.
            time (Time): Time of calculation.
            frequencies (List[float]): Frequencies in Hz.
            source (Optional[Source]): Source for UV calculation.
            visibility (Optional[Dict[str, bool]]): Visibility status per telescope.
            gcrs_positions (Optional[List[Tuple[float, float, float]]]): Precomputed GCRS positions.

        Returns:
            Dict[float, List[Tuple[str, float, float, float]]]: UVW coordinates per frequency and baseline.
        """
        uv_points = {f: [] for f in frequencies}
        c = 299792458  # m/s

        if not telescopes or len(telescopes) < 2:
            logger.warning(f"Insufficient telescopes ({len(telescopes)}) to compute (u,v) at {time.isot}")
            return uv_points

        if gcrs_positions is None:
            gcrs_positions = [self._compute_telescope_position(tel, time) for tel in telescopes]

        if source is None:
            logger.warning("No source provided; cannot calculate (u,v,w)")
            return uv_points

        source_coord = SkyCoord(ra=source.get_ra_degrees() * u.deg, dec=source.get_dec_degrees() * u.deg, frame='icrs')
        ra = source_coord.ra.rad
        dec = source_coord.dec.rad

        if visibility is None:
            positions_dict = {tel.get_code(): pos for tel, pos in zip(telescopes, gcrs_positions)}
            visibility = self._compute_visibility_at_time(source, telescopes, time, positions_dict)

        def compute_baseline(i, j):
            tel1, tel2 = telescopes[i], telescopes[j]
            if not visibility[tel1.get_code()] or not visibility[tel2.get_code()]:
                return []
            pos1 = np.array(gcrs_positions[i])
            pos2 = np.array(gcrs_positions[j])
            baseline = pos1 - pos2
            X, Y, Z = baseline
            uu = -math.sin(ra) * X + math.cos(ra) * Y
            vv = -math.cos(ra) * math.sin(dec) * X - math.sin(ra) * math.sin(dec) * Y + math.cos(dec) * Z
            ww = math.cos(ra) * math.cos(dec) * X + math.sin(ra) * math.cos(dec) * Y + math.sin(dec) * Z
            pair = f"{tel1.get_code()}-{tel2.get_code()}"
            return [(pair, uu / (c / freq), vv / (c / freq), ww / (c / freq)) for freq in frequencies]

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(compute_baseline, i, j) for i in range(len(telescopes)) for j in range(i + 1, len(telescopes))]
            for future in futures:
                points = future.result()
                for freq, point in zip(frequencies, points):
                    uv_points[freq].append(point)

        return uv_points

    @time_execution
    def _calculate_sun_angles(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate angular separation between source and Sun for all scans.

        Args:
            obj (Observation | ScheduleProject): The object to calculate sun angles for.
            attributes (Dict[str, Any]): Parameters including "time_step" and "store_key".

        Returns:
            Dict[str, Any]: Sun angles per scan, keyed by scan index or observation code.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "sun_angles")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_observations()
                if not observations:
                    logger.warning(f"No observations in project '{obj.get_name()}'")
                    return {}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_sun_angles(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"Calculated Sun angles for {len(observations)} observations in project '{obj.get_name()}'")
                return results

            def calculate_sun_angles(obj, attrs):
                scans = obj.get_scans().get_active_scans(obj)
                sources = obj.get_sources()
                telescopes = obj.get_telescopes()
                results = {}
                with ThreadPoolExecutor() as executor:
                    futures = {
                        executor.submit(self._process_sun_angles, scan, sources, telescopes, time_step): i
                        for i, scan in enumerate(scans)
                    }
                    for future in futures:
                        scan_idx = futures[future]
                        results[scan_idx] = future.result()
                return results

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_scans(obj))}
            return self._get_cached_or_calculate(obj, store_key, calculate_sun_angles, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate Sun angles: {str(e)}")
            return {}

    def _process_sun_angles(self, scan: Scan, sources: Sources, telescopes: Telescopes, time_step: Optional[float]) -> Dict[str, Any]:
        """Compute angle between the direction from telescope to source and to Sun for each telescope at a given time.

        Args:
            source_coord (SkyCoord): Source coordinates.
            time (Time): Time of calculation.
            telescopes (List[Telescope | SpaceTelescope]): List of telescopes.

        Returns:
            Dict[str, float]: Angular separation (degrees) per telescope code.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        source = sources.get_by_index(scan.get_source_index())
        source_coord = SkyCoord(ra=source.get_ra_degrees() * u.deg, dec=source.get_dec_degrees() * u.deg, frame='icrs')
        telescope_indices = scan.get_telescope_indices()
        active_telescopes = [telescopes.get_by_index(i) for i in telescope_indices if telescopes.get_by_index(i).isactive]

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            angles = self._compute_sun_angle(source_coord, mean_time, active_telescopes)
            return {"source": source.get_name(), "sun_angles": angles}
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
            angles = {tel.get_code(): [] for tel in active_telescopes}
            for t in times:
                tel_angles = self._compute_sun_angle(source_coord, t, active_telescopes)
                for tel_code, angle in tel_angles.items():
                    angles[tel_code].append(angle)
            return {"source": source.get_name(), "times": times.isot.tolist(), "sun_angles": angles}

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
                observations = obj.get_observations()
                if not observations:
                    logger.warning(f"No observations in project '{obj.get_name()}'")
                    return {}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_az_el(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"Calculated Az/El or HA/Dec for {len(observations)} observations in project '{obj.get_name()}'")
                return results

            def calculate_az_el(obj, attrs):
                scans = obj.get_scans().get_active_scans(obj)
                telescopes = obj.get_telescopes()
                sources = obj.get_sources()
                results = {}
                with ThreadPoolExecutor() as executor:
                    futures = {
                        executor.submit(self._process_az_el, scan, telescopes, sources, time_step): i
                        for i, scan in enumerate(scans)
                    }
                    for future in futures:
                        scan_idx = futures[future]
                        results[scan_idx] = future.result()
                return results

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_scans(obj))}
            return self._get_cached_or_calculate(obj, store_key, calculate_az_el, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate Az/El or HA/Dec: {str(e)}")
            return {}

    def _process_az_el(self, scan: Scan, telescopes: Telescopes, sources: Sources, time_step: Optional[float]) -> Dict[str, Any]:
        """Process Az/El or HA/Dec for a single scan.

        Args:
            scan (Scan): The scan to process.
            telescopes (Telescopes): Collection of telescopes.
            sources (Sources): Collection of sources.
            time_step (Optional[float]): Sampling interval (seconds).

        Returns:
            Dict[str, Any]: Coordinate data per telescope, with times if sampled.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        source = sources.get_by_index(scan.get_source_index())
        source_coord = SkyCoord(ra=source.get_ra_degrees() * u.deg, dec=source.get_dec_degrees() * u.deg, frame='icrs')
        telescope_indices = scan.get_telescope_indices()
        active_ground_tels = [tel for tel in (telescopes.get_by_index(i) for i in telescope_indices) 
                            if tel.isactive and not isinstance(tel, SpaceTelescope)]

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            az_el = self._compute_az_el_at_time(source_coord, active_ground_tels, mean_time)
            return {"source": source.get_name(), "az_el": az_el}
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')  # Массовое создание Time
            az_el = {tel.get_code(): {"coord1": [], "coord2": []} for tel in active_ground_tels}
            for t in times:
                result = self._compute_az_el_at_time(source_coord, active_ground_tels, t)
                for tel_code, (coord1, coord2) in result.items():
                    az_el[tel_code]["coord1"].append(coord1)
                    az_el[tel_code]["coord2"].append(coord2)
            for tel in active_ground_tels:
                mount_type = tel.get_mount_type()
                az_el[tel.get_code()]["coord_type"] = "AzEl" if mount_type == MountType.AZIMUTHAL else "HADec"
            return {"source": source.get_name(), "times": times.isot.tolist(), "az_el": az_el}

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
            vx, vy, vz = tel.get_velocities()
            dt = (time - Time("2000-01-01T12:00:00")).sec
            itrs_coords = CartesianRepresentation(x + vx * dt, y + vy * dt, z + vz * dt, unit=u.m)
            itrs = ITRS(itrs_coords, obstime=time)
            location = itrs.earth_location
            mount_type = tel.get_mount_type()
            
            if mount_type == MountType.AZIMUTHAL:
                altaz = source_coord.transform_to(AltAz(obstime=time, location=location))
                az, el = altaz.az.deg, altaz.alt.deg
                el_range = tel.get_elevation_range()
                az_range = tel.get_azimuth_range()
                if not (el_range[0] <= el <= el_range[1] and az_range[0] <= az <= az_range[1]):
                    az_el[tel.get_code()] = (None, None)
                else:
                    az_el[tel.get_code()] = (az, el)
            elif mount_type == MountType.EQUATORIAL:
                hadec = source_coord.transform_to(HADec(obstime=time, location=location))
                ha, dec = hadec.ha.deg, hadec.dec.deg
                ha_range = tel.get_azimuth_range()  # HA uses azimuth range
                dec_range = tel.get_elevation_range()  # Dec uses elevation range
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
                    logger.warning(f"No observations in project '{obj.get_name()}'")
                    return {}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_time_on_source(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"Calculated time on source for {len(observations)} observations in project '{obj.get_name()}'")
                return results

            def calculate_time_on_source(obj, attrs):
                scans = obj.get_scans().get_active_scans(obj)
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
                        executor.submit(self._process_time_on_source, scan, sources, telescopes, time_step, visibility_data, obj): i
                        for i, scan in enumerate(scans)
                    }
                    for future in futures:
                        scan_idx = futures[future]
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

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_scans(obj))}
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
        source = sources.get_by_index(scan.get_source_index())
        scan_idx = list(observation.get_scans().get_active_scans(observation)).index(scan)
        telescope_indices = scan.get_telescope_indices()
        active_telescopes = [telescopes.get_by_index(i) for i in telescope_indices if telescopes.get_by_index(i).isactive]

        time_values = np.arange(0, duration, time_step) * u.s
        times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')

        scan_data = visibility_data.get(scan_idx, {}) if isinstance(visibility_data, dict) else {}
        visibility = scan_data.get("visibility", {})
        if not visibility:
            logger.warning(f"No visibility data for scan {scan_idx} in observation '{observation.get_observation_code()}'")
            return {"source": source.get_name(), "visibility_blocks": {}}

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

        return {"source": source.get_name(), "visibility_blocks": blocks}

    @time_execution
    def _calculate_beam_pattern(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate beam pattern for single-dish observations.

        Args:
            obj (Observation | ScheduleProject): The object to calculate beam pattern for.
            attributes (Dict[str, Any]): Parameters including "freq_idx" and "store_key".

        Returns:
            Dict[str, Any]: Beam pattern data per telescope.
        """
        try:
            freq_idx = attributes.get("freq_idx", 0)
            store_key = attributes.get("store_key", f"beam_pattern_f{freq_idx}")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_observations()
                if not observations:
                    logger.warning(f"No observations in project '{obj.get_name()}'")
                    return {}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_beam_pattern(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"Calculated beam pattern for {len(observations)} observations in project '{obj.get_name()}'")
                return results

            if obj.get_observation_type() != "SINGLE_DISH":
                logger.warning(f"Beam pattern calculation is only for SINGLE_DISH, got {obj.get_observation_type()}")
                return {}

            def calculate_beam_pattern(obj, attrs):
                telescopes = obj.get_telescopes().get_active_telescopes()
                frequency = obj.get_frequencies().get_by_index(freq_idx).get_frequency() * 1e6
                results = {}
                c = 299792458
                wavelength = c / frequency
                for tel in telescopes:
                    if isinstance(tel, SpaceTelescope):
                        continue
                    D = tel.get_diameter()
                    theta = np.linspace(-np.pi/2, np.pi/2, 1000)
                    x = (np.pi * D / wavelength) * np.sin(theta)
                    pattern = (2 * j1(x) / x) ** 2
                    pattern[np.isnan(pattern)] = 1.0
                    results[tel.get_code()] = {"theta": theta.tolist(), "pattern": pattern.tolist()}
                return results

            metadata = {"freq_idx": freq_idx}
            return self._get_cached_or_calculate(obj, store_key, calculate_beam_pattern, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate beam pattern: {str(e)}")
            return {}

    @time_execution
    def _calculate_synthesized_beam(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate synthesized beam for VLBI observations.

        Args:
            obj (Observation | ScheduleProject): The object to calculate synthesized beam for.
            attributes (Dict[str, Any]): Parameters including "freq_idx", "time_step", and "store_key".

        Returns:
            Dict[str, Any]: Synthesized beam data.
        """
        try:
            freq_idx = attributes.get("freq_idx", 0)
            store_key = attributes.get("store_key", f"synthesized_beam_f{freq_idx}")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_observations()
                results = {}
                for obs in observations:
                    obs_result = self._calculate_synthesized_beam(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                return results

            if obj.get_observation_type() != "VLBI":
                logger.warning(f"Synthesized beam calculation is only for VLBI, got {obj.get_observation_type()}")
                return {}

            def calculate_synthesized_beam(obj, attrs):
                frequency = obj.get_frequencies().get_by_index(freq_idx).get_frequency() * 1e6
                uv_store_key = f"uv_coverage_f{freq_idx}"
                uv_data = self._calculate_uv_coverage(obj, {
                    "time_step": attrs.get("time_step"),
                    "freq_idx": freq_idx,
                    "store_key": uv_store_key,
                    "recalculate": attrs.get("recalculate", False)
                })
                if not uv_data:
                    logger.warning(f"No UV data available for '{obj.get_observation_code()}'")
                    return {}

                u = []
                v = []
                for scan_idx, scan_data in uv_data.items():  # Убрано .get('data', {})
                    uv_points = scan_data.get("uv_points", {}).get(frequency, [])
                    if not uv_points:
                        continue
                    u.extend([point[1] for point in uv_points])
                    v.extend([point[2] for point in uv_points])
                if not u or not v:
                    logger.warning(f"No valid UV points for frequency {frequency/1e6} MHz")
                    return {}

                u_max = max(abs(min(u)), abs(max(u)))
                v_max = max(abs(min(v)), abs(max(v)))
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
                beam_2d /= beam_2d.max()
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
                        "beam_2d": beam_2d.tolist()  # Сериализация для кэша
                    }
                }

            metadata = {"freq_idx": freq_idx, "time_step": attributes.get("time_step")}
            return self._get_cached_or_calculate(obj, store_key, calculate_synthesized_beam, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate synthesized beam: {str(e)}")
            return {}
    
    @time_execution
    def _calculate_baseline_projections(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate baseline projections for VLBI observations.

        Args:
            obj (Observation | ScheduleProject): The object to calculate projections for.
            attributes (Dict[str, Any]): Parameters including "time_step", "freq_idx", and "store_key".

        Returns:
            Dict[str, Any]: Baseline projection data per scan.
        """
        try:
            time_step = attributes.get("time_step")
            freq_idx = attributes.get("freq_idx", 0)
            store_key = attributes.get("store_key", f"baseline_projections_f{freq_idx}")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_observations()
                if not observations:
                    logger.warning(f"No observations in project '{obj.get_name()}'")
                    return {}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_baseline_projections(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"Calculated baseline projections for {len(observations)} observations in project '{obj.get_name()}'")
                return results

            if obj.get_observation_type() != "VLBI":
                logger.warning(f"Baseline projections are only for VLBI, got {obj.get_observation_type()}")
                return {}

            def calculate_baseline_projections(obj, attrs):
                scans = obj.get_scans().get_active_scans(obj)
                telescopes = obj.get_telescopes()
                frequencies = obj.get_frequencies()
                active_telescopes = telescopes.get_active_telescopes()
                if len(active_telescopes) < 2:
                    logger.error(f"VLBI requires at least 2 active telescopes, got {len(active_telescopes)}")
                    return {}
                uv_store_key = f"uv_coverage_f{freq_idx}"
                uv_data = self._calculate_uv_coverage(obj, {
                    "time_step": time_step,
                    "freq_idx": freq_idx,
                    "store_key": uv_store_key,
                    "recalculate": attrs.get("recalculate", False)
                })
                if not uv_data:
                    logger.error(f"Failed to obtain UV coverage data for '{obj.get_observation_code()}'")
                    return {}
                results = {}
                with ThreadPoolExecutor() as executor:
                    futures = {
                        executor.submit(self._process_baseline_projections, scan, telescopes, frequencies, time_step, freq_idx, uv_data, obj): i
                        for i, scan in enumerate(scans)
                    }
                    for future in futures:
                        scan_idx = futures[future]
                        results[scan_idx] = future.result()
                return results

            metadata = {"time_step": time_step, "freq_idx": freq_idx, "scan_count": len(obj.get_scans().get_active_scans(obj))}
            return self._get_cached_or_calculate(obj, store_key, calculate_baseline_projections, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate baseline projections: {str(e)}")
            return {}

    def _process_baseline_projections(self, scan: Scan, telescopes: Telescopes, frequencies: Frequencies, time_step: Optional[float], freq_idx: int, uv_data: Dict[str, Any], observation: Observation) -> Dict[str, Any]:
        """Process baseline projections for a single scan.

        Args:
            scan (Scan): The scan to process.
            telescopes (Telescopes): Collection of telescopes.
            frequencies (Frequencies): Collection of frequencies.
            time_step (Optional[float]): Sampling interval (seconds).
            freq_idx (int): Frequency index.
            uv_data (Dict[str, Any]): Precomputed UV data.
            observation (Observation): Parent observation.

        Returns:
            Dict[str, Any]: Baseline projections per telescope pair.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        telescope_indices = scan.get_telescope_indices()
        active_telescopes = [telescopes.get_by_index(i) for i in telescope_indices if telescopes.get_by_index(i).isactive]
        frequency = frequencies.get_by_index(freq_idx).get_frequency() * 1e6
        scan_idx = list(observation.get_scans().get_active_scans(observation)).index(scan)


        scan_uv_data = uv_data.get(scan_idx, {}) if isinstance(uv_data, dict) else {}
        if not scan_uv_data or "uv_points" not in scan_uv_data:
            logger.error(f"No UV data available for scan {scan_idx} at {start_time.isot}")
            return {"projections": {} if time_step is None else {"times": [], "projections": {}}}

        if time_step is None:
            projections = self._compute_projections_from_uv(scan_uv_data["uv_points"], active_telescopes, frequency)
            logger.info(f"Static projections: {projections}")
            return {"projections": projections}
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
            projections = {
                f"{t1.get_code()}-{t2.get_code()}": [] 
                for i, t1 in enumerate(active_telescopes) 
                for t2 in active_telescopes[i+1:]
            }
            uv_points = scan_uv_data.get("uv_points", {}).get(frequency, [])
            if not uv_points:
                logger.warning(f"No UV points found for frequency {frequency} in scan {scan_idx}")
                return {"times": times.isot.tolist(), "projections": projections}

            for uv_list in uv_points:
                proj = self._compute_projections_from_uv({frequency: [uv_list]}, active_telescopes, frequency)
                for pair, bl in proj.items():
                    if pair in projections:
                        projections[pair].append(bl)

            return {"times": times.isot.tolist(), "projections": projections}
        
    def _compute_projections_from_uv(self, uv_points: Dict[float, List[Tuple[str, float, float, float]]], telescopes: List[Telescope | SpaceTelescope], frequency: float) -> Dict[str, float]:
        """Compute baseline projection BL = sqrt(u² + v²) from pre-calculated (u,v) data.

        Args:
            uv_points (Dict[float, List[Tuple[str, float, float, float]]]): UV data.
            telescopes (List[Telescope | SpaceTelescope]): List of telescopes.
            frequency (float): Frequency in Hz.

        Returns:
            Dict[str, float]: Baseline length per telescope pair.
        """
        projections = {}
        uv_list = uv_points.get(frequency, [])
        for pair, uuu, vvv, _ in uv_list:
            bl = math.sqrt(uuu * uuu + vvv * vvv)  # BL = sqrt(u² + v²)
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
                    logger.warning(f"No observations in project '{obj.get_name()}'")
                    return {}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_mollweide_tracks(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"Calculated Mollweide tracks for {len(observations)} observations in project '{obj.get_name()}'")
                return results

            def calculate_mollweide_tracks(obj, attrs):
                scans = obj.get_scans().get_active_scans(obj)
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
                        scan_idx = futures[future]
                        results[scan_idx] = future.result()
                return results

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_scans(obj))}
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
        source = sources.get_by_index(scan.get_source_index())
        telescope_indices = scan.get_telescope_indices()
        active_telescopes = [telescopes.get_by_index(i) for i in telescope_indices if telescopes.get_by_index(i).isactive]
        scan_idx = list(observation.get_scans().get_active_scans(observation)).index(scan)

        if not position_data or scan_idx not in position_data:
            source = sources.get_by_index(scan.get_source_index())
            source_coord = SkyCoord(ra=source.get_ra_degrees() * u.deg, dec=source.get_dec_degrees() * u.deg, frame='icrs')
            source_lon, source_lat = self._compute_mollweide_coords(source_coord)
            logger.error(f"No position data for scan {scan_idx}")
            return {"source": {"name": source.get_name(), "lon": source_lon, "lat": source_lat}, "telescope_tracks": {}}
        
        source_coord = SkyCoord(ra=source.get_ra_degrees() * u.deg, dec=source.get_dec_degrees() * u.deg, frame='icrs')
        source_lon, source_lat = self._compute_mollweide_coords(source_coord)      
        
        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            tel_positions = position_data.get(scan_idx, {}).get("telescope_positions", {})
            tracks = {}
            for tel in active_telescopes:
                pos = tel_positions.get(tel.get_code())
                if pos:
                    lon, lat = self._compute_mollweide_coords_from_position(pos, mean_time)
                    tracks[tel.get_code()] = {"lon": [lon], "lat": [lat]}
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
            tel_positions = position_data.get(scan_idx, {}).get("telescope_positions", {})
            
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
            "source": {"name": source.get_name(), "lon": source_lon, "lat": source_lat},
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
    

