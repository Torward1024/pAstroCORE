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
import xarray as xr

import threading
import time
import re
import os

import multiprocessing

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
    
    def _get_cached_or_calculate(self, obj: Observation | ScheduleProject, store_key: str, calc_func, attributes: Dict[str, Any], metadata: Dict[str, Any]) -> xr.Dataset:
        """Retrieve cached data or perform calculation and cache the result as xarray.Dataset.

        Args:
            obj (Observation | ScheduleProject): The object to calculate for.
            store_key (str): Unique key for storing/retrieving calculated data.
            calc_func: The calculation function to execute if no valid cache exists.
            attributes (Dict[str, Any]): Calculation parameters (e.g., "recalculate", "time_step").
            metadata (Dict[str, Any]): Metadata to store with the result (e.g., time step, scan count).

        Returns:
            xr.Dataset: Calculated or cached data as an xarray Dataset.

        Notes:
            - If "recalculate" is False and valid cached data exists, returns cached result.
            - Uses thread-safe caching with a lock.
        """
        recalculate = attributes.get("recalculate", False)
        time_step = attributes.get("time_step")

        existing_data = obj.get_calculated_data_by_key(store_key)
        if existing_data is not None and not recalculate and existing_data.attrs.get("time_step") == time_step:
            if existing_data.data_vars:
                logger.info(f"Using cached data for '{store_key}' in '{obj.get_observation_code()}'")
                return existing_data
            else:
                logger.warning(f"Cached data for '{store_key}' in '{obj.get_observation_code()}' is empty, forcing recalculation")

        logger.info(f"Recalculating '{store_key}' for '{obj.get_observation_code()}' with recalculate={recalculate}")
        result = calc_func(obj, attributes)
        if not result.data_vars:
            logger.warning(f"Calculation for '{store_key}' returned empty result")
        with self._lock:
            obj.set_calculated_data_by_key(store_key, result.assign_attrs(metadata))
        return result

    @time_execution
    def _calculate_source_visibility(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> xr.Dataset:
        """Calculate source visibility for all scans.

        Args:
            obj (Observation | ScheduleProject): The object to calculate visibility for.
            attributes (Dict[str, Any]): Parameters including "time_step", "store_key", and "position_store_key".

        Returns:
            xr.Dataset: Visibility data per scan, telescope, and time, with source information.

        Notes:
            - Depends on precomputed telescope positions.
            - Uses parallel processing for multiple scans when beneficial.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "source_visibility")
            position_store_key = attributes.get("position_store_key", "telescope_positions")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return xr.Dataset()
                # Pre-allocate Dataset for all observations
                obs_codes = [obs.get_observation_code() for obs in observations]
                datasets = []
                max_workers = self._get_max_workers(len(observations), is_cpu_bound=True)
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [
                        executor.submit(self._calculate_source_visibility, obs, attributes)
                        for obs in observations
                    ]
                    for future in futures:
                        ds = future.result()
                        datasets.append(ds)
                if not datasets:
                    return xr.Dataset()
                return xr.concat(datasets, dim="observation").assign_coords({"observation": obs_codes})

            def calculate_visibility(obj, attrs):
                scans = obj.get_scans().get_active_items()
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": attrs.get("recalculate")}
                position_data = self._calculate_telescope_positions(obj, position_attrs)
                if "positions" not in position_data:
                    logger.error(f"Failed to obtain telescope positions for '{obj.get_observation_code()}'")
                    return xr.Dataset()

                # Pre-allocate Dataset dimensions
                scan_names = [scan.name for scan in scans]
                max_telescopes = max(len(scan.get_telescopes(obj).get_active_items()) for scan in scans) if scans else 0
                max_times = max(int(scan.get_duration() / time_step) if time_step else 1 for scan in scans) if scans else 0
                if not scans:
                    logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
                    return xr.Dataset()

                # Initialize empty Dataset
                visibility = np.zeros((len(scans), max_telescopes, max_times), dtype=bool)
                telescope_coords = []
                time_coords = []
                source_names = []

                for scan_idx, scan in enumerate(scans):
                    scan_name = scan.name
                    scan_positions = position_data.sel(scan=scan_name).get("positions", xr.DataArray())
                    if time_step and scan_positions.sizes.get("time", 0) != int(scan.get_duration() / time_step):
                        logger.warning(f"Mismatched position data length for scan {scan_name}")
                        return xr.Dataset()

                    ds = self._process_source_visibility(scan, obj, time_step, position_data)
                    if "visibility" not in ds:
                        continue
                    vis = ds["visibility"].values
                    tels = ds["telescope"].values
                    times = ds["time"].values
                    source = ds["source"].item()

                    # Pad visibility array to match max dimensions
                    pad_tel = max_telescopes - vis.shape[0]
                    pad_time = max_times - vis.shape[1]
                    if pad_tel > 0 or pad_time > 0:
                        vis = np.pad(vis, ((0, pad_tel), (0, pad_time)), mode='constant', constant_values=False)
                    visibility[scan_idx, :vis.shape[0], :vis.shape[1]] = vis
                    telescope_coords.append(tels)
                    time_coords.append(times)
                    source_names.append(source)

                # Create unified Dataset
                if not telescope_coords:
                    return xr.Dataset()

                # Use unique telescopes and times, preserving order
                all_telescopes = np.unique(np.concatenate(telescope_coords), return_index=False)
                all_times = np.unique(np.concatenate(time_coords), return_index=False)
                dataset = xr.Dataset(
                    data_vars={"visibility": (["scan", "telescope", "time"], visibility)},
                    coords={
                        "scan": scan_names,
                        "telescope": all_telescopes[:max_telescopes],
                        "time": all_times[:max_times],
                        "source": (["scan"], source_names)
                    }
                )
                return dataset

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items()), "observation_code": obj.get_observation_code()}
            return self._get_cached_or_calculate(obj, store_key, calculate_visibility, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate source visibility: {str(e)}")
            return xr.Dataset()
        
    def _process_source_visibility(self, scan: Scan, observation: Observation, time_step: Optional[float], position_data: xr.Dataset) -> xr.Dataset:
        """Process source visibility for a single scan.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): The parent observation.
            time_step (Optional[float]): Time interval for sampling (seconds).
            position_data (xr.Dataset): Precomputed telescope positions.

        Returns:
            xr.Dataset: Visibility data with dimensions [telescope, time] and source info.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        source = scan.get_source(observation)
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs') if source else None
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        scan_name = scan.name

        logger.debug(f"Processing visibility for scan {scan_name}: {len(active_telescopes)} telescopes")

        if not active_telescopes or not source_coord:
            logger.warning(f"No active telescopes or source for scan {scan_name}")
            return xr.Dataset(coords={"scan": [scan_name], "source": source.name if source else None})

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            times = Time([mean_time])
            positions = position_data.sel(scan=scan_name).get("positions", xr.DataArray())
            visibility = self._compute_visibility_at_time(source, active_telescopes, mean_time, {tel.get_code(): pos.values for tel, pos in zip(active_telescopes, positions.sel(time=mean_time.isot))}) if source else {tel.get_code(): False for tel in active_telescopes}
            visibility_array = np.array([visibility[tel.get_code()] for tel in active_telescopes], dtype=bool)
            return xr.Dataset(
                data_vars={"visibility": (["telescope", "time"], visibility_array[:, None])},
                coords={
                    "scan": [scan_name],
                    "telescope": [tel.get_code() for tel in active_telescopes],
                    "time": [mean_time.iso],
                    "source": source.name if source else None
                }
            )
        else:
            if time_step > duration:
                logger.error(f"time_step ({time_step}s) exceeds scan duration ({duration}s) for scan {scan_name}; calculation aborted")
                return xr.Dataset(coords={"scan": [scan_name], "source": source.name if source else None})
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
            positions = position_data.sel(scan=scan_name).get("positions", xr.DataArray())
            if not positions.size:
                logger.warning(f"No position data for scan {scan_name}")
                return xr.Dataset(coords={"scan": [scan_name], "source": source.name if source else None})

            visibility = np.zeros((len(active_telescopes), len(times)), dtype=bool)
            pos_arrays = {tel.get_code(): positions.sel(telescope=tel.get_code()).values for tel in active_telescopes if tel.get_code() in positions.telescope.values}

            if source_coord:
                for i, tel in enumerate(active_telescopes):
                    tel_code = tel.get_code()
                    if tel_code not in pos_arrays:
                        logger.warning(f"No position data for telescope '{tel_code}' in scan {scan_name}")
                        visibility[i] = False
                        continue
                    pos_array = pos_arrays[tel_code]
                    if pos_array.shape[0] != len(times):
                        logger.warning(f"Mismatched position data length for telescope '{tel_code}' in scan {scan_name}")
                        visibility[i] = False
                        continue

                    if isinstance(tel, SpaceTelescope):
                        # Compute visibility for space telescope using pitch/yaw ranges
                        # gcrs = GCRS(CartesianRepresentation(pos_array[:, 0], pos_array[:, 1], pos_array[:, 2], unit=u.m), obstime=times)
                        # itrs = gcrs.transform_to(ITRS(obstime=times))
                        # location = itrs.earth_location
                        # altaz = source_coord.transform_to(AltAz(obstime=times, location=location))
                        # pitch = altaz.alt.deg
                        # yaw = altaz.az.deg
                        # pitch_range = tel.get_pitch_range()
                        # yaw_range = tel.get_yaw_range()
                        # try:
                        #     visibility[i] = (pitch_range[0] <= pitch) & (pitch <= pitch_range[1]) & (yaw_range[0] <= yaw) & (yaw <= yaw_range[1])
                        # except (TypeError, ValueError) as e:
                        #     logger.warning(f"Invalid pitch/yaw ranges for telescope '{tel_code}': {e}")
                        visibility[i] = True
                    else:
                        gcrs = GCRS(CartesianRepresentation(pos_array[:, 0], pos_array[:, 1], pos_array[:, 2], unit=u.m), obstime=times)
                        itrs = gcrs.transform_to(ITRS(obstime=times))
                        location = itrs.earth_location
                        mount_type = tel.get("mount_type")
                        if mount_type.value == "AZIM":
                            altaz = source_coord.transform_to(AltAz(obstime=times, location=location))
                            el = altaz.alt.deg
                            az = altaz.az.deg
                            el_range = tel.get_elevation_range()
                            az_range = tel.get_azimuth_range()
                            try:
                                el_lower = np.asarray(float(el_range[0]) <= el, dtype=bool)
                                el_upper = np.asarray(el <= float(el_range[1]), dtype=bool)
                                az_lower = np.asarray(float(az_range[0]) <= az, dtype=bool)
                                az_upper = np.asarray(az <= float(az_range[1]), dtype=bool)
                                visibility[i] = el_lower & el_upper & az_lower & az_upper
                            except (TypeError, ValueError) as e:
                                logger.warning(f"Invalid az/el ranges for telescope '{tel_code}': {e}")
                                visibility[i] = False
                        elif mount_type.value == "EQUA":
                            hadec = source_coord.transform_to(HADec(obstime=times, location=location))
                            ha = hadec.ha.deg
                            dec = hadec.dec.deg
                            ha_range = tel.get_azimuth_range()
                            dec_range = tel.get_elevation_range()
                            try:
                                dec_lower = np.asarray(float(dec_range[0]) <= dec, dtype=bool)
                                dec_upper = np.asarray(dec <= float(dec_range[1]), dtype=bool)
                                ha_lower = np.asarray(float(ha_range[0]) <= ha, dtype=bool)
                                ha_upper = np.asarray(ha <= float(ha_range[1]), dtype=bool)
                                visibility[i] = dec_lower & dec_upper & ha_lower & ha_upper
                            except (TypeError, ValueError) as e:
                                logger.warning(f"Invalid ha/dec ranges for telescope '{tel_code}': {e}")
                                visibility[i] = False
                        else:
                            logger.debug(f"Unsupported mount type {mount_type.value} for telescope '{tel_code}'")
                            visibility[i] = False

            return xr.Dataset(
                data_vars={"visibility": (["telescope", "time"], visibility)},
                coords={
                    "scan": [scan_name],
                    "telescope": [tel.get_code() for tel in active_telescopes],
                    "time": [t.iso for t in times],
                    "source": source.name if source else None
                }
            )

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
    def _calculate_telescope_positions(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> xr.Dataset:
        """Calculate telescope positions for all scans.

        Args:
            obj (Observation | ScheduleProject): Object to calculate positions for.
            attributes (Dict[str, Any]): Parameters including "time_step" and "store_key".

        Returns:
            xr.Dataset: Positions per scan, telescope, and time.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "telescope_positions")

            def calculate_positions(obj, attrs):
                if isinstance(obj, ScheduleProject):
                    observations = obj.get_items()
                    if not observations:
                        logger.warning(f"No observations in project '{obj.name}'")
                        return xr.Dataset()
                    datasets = []
                    max_workers = self._get_max_workers(len(observations), is_cpu_bound=True)
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        futures = [
                            executor.submit(self._calculate_telescope_positions, obs, attrs)
                            for obs in observations
                        ]
                        for future in futures:
                            ds = future.result()
                            datasets.append(ds)
                    if not datasets:
                        return xr.Dataset()
                    obs_codes = [obs.get_observation_code() for obs in observations]
                    return xr.concat(datasets, dim="observation").assign_coords({"observation": obs_codes})

                scans = obj.get_scans().get_active_items()
                if not scans:
                    logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
                    return xr.Dataset()

                datasets = []
                for scan in scans:
                    # Define expected times for this scan
                    start_time = scan.get_start()
                    duration = scan.get_duration()
                    if time_step:
                        time_values = np.arange(0, duration, time_step) * u.s
                        times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
                        j2000_epoch = Time("2000-01-01T12:00:00", scale='utc')
                        expected_times = (times - j2000_epoch).sec
                    else:
                        expected_times = None
                    # Pass expected_times to _process_scan_positions
                    ds = self._process_scan_positions(scan, obj, time_step)
                    if not ds or "positions" not in ds:
                        continue
                    datasets.append(ds)
                
                if not datasets:
                    logger.warning(f"No valid position data for observation '{obj.get_observation_code()}'")
                    return xr.Dataset()
                
                return xr.concat(datasets, dim="scan")

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items()), "observation_code": obj.get_observation_code()}
            return self._get_cached_or_calculate(obj, store_key, calculate_positions, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate telescope positions: {str(e)}")
            return xr.Dataset()

    def _process_scan_positions(self, scan: Scan, observation: Observation, time_step: Optional[float]) -> xr.Dataset:
        """Process telescope positions for a single scan.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Time interval for position sampling (seconds).

        Returns:
            xr.Dataset: Positions with dimensions [telescope, time, coord].
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [tel for tel in scan_telescopes.get_items() if tel.isactive]
        scan_name = scan.name

        if not active_telescopes:
            logger.warning(f"No active telescopes for scan {scan_name} starting at {start_time.isot}")
            return xr.Dataset()

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            positions = np.array([self._compute_telescope_position(tel, mean_time) for tel in active_telescopes])
            valid_mask = ~np.any(np.isnan(positions), axis=1)
            if not np.any(valid_mask):
                logger.warning(f"No valid positions for scan {scan_name} at {mean_time.isot}")
                return xr.Dataset()
            valid_telescopes = [tel for tel, valid in zip(active_telescopes, valid_mask) if valid]
            positions = positions[valid_mask]
            return xr.Dataset(
                data_vars={"positions": (["telescope", "time", "coord"], positions[:, None, :])},
                coords={
                    "scan": [scan_name],
                    "telescope": [tel.get_code() for tel in valid_telescopes],
                    "time": [mean_time.iso],
                    "coord": ["x", "y", "z"]
                }
            )
        else:
            # Define unified time array for all telescopes
            j2000_epoch = Time("2000-01-01T12:00:00", scale='utc')
            if time_step > duration:
                logger.error(f"time_step ({time_step}s) exceeds scan duration ({duration}s) for scan {scan_name}; calculation aborted")
                return xr.Dataset(coords={"scan": [scan_name]})
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
            expected_times = (times - j2000_epoch).sec
            expected_times_count = len(expected_times)
            
            positions = np.full((len(active_telescopes), expected_times_count, 3), np.nan, dtype=float)
            valid_telescopes = []
            
            for tel_idx, tel in enumerate(active_telescopes):
                if isinstance(tel, SpaceTelescope) and not tel.get("use_kep"):
                    # Use cached or interpolated orbit data
                    orbit_data = self._orbit_cache.get(tel.get_code(), {})
                    if not orbit_data or orbit_data.get("time_range", (0, 0)) != (start_time.mjd, start_time.mjd + duration / 86400):
                        orbit_data = self._interpolate_orbit(tel, start_time, start_time + duration * u.s, time_step, expected_times)
                        self._orbit_cache[tel.get_code()] = orbit_data
                    
                    if not orbit_data:
                        logger.warning(f"No orbit data for telescope '{tel.get_code()}' in scan {scan_name}")
                        continue
                    
                    orbit_times = orbit_data.get("times", [])
                    orbit_positions = orbit_data.get("positions", [])
                    if len(orbit_times) != expected_times_count or np.any(np.isnan(orbit_positions)):
                        logger.warning(f"Mismatched orbit data for telescope '{tel.get_code()}' in scan {scan_name}: expected {expected_times_count} points, got {len(orbit_times)}")
                        continue
                    
                    positions[tel_idx] = orbit_positions
                    valid_telescopes.append(tel)
                else:
                    # Compute positions for ground-based or Keplerian telescopes
                    tel_positions = np.array([self._compute_telescope_position(tel, t) for t in times])
                    if tel_positions.shape[0] == expected_times_count and not np.any(np.isnan(tel_positions)):
                        positions[tel_idx] = tel_positions
                        valid_telescopes.append(tel)
                    else:
                        logger.warning(f"Invalid position data for telescope '{tel.get_code()}' in scan {scan_name}: expected {expected_times_count} points, got {tel_positions.shape[0]}")
            
            if not valid_telescopes:
                logger.warning(f"No valid position data for any telescope in scan {scan_name}")
                return xr.Dataset()
            
            positions = positions[:len(valid_telescopes)]
            return xr.Dataset(
                data_vars={"positions": (["telescope", "time", "coord"], positions)},
                coords={
                    "scan": [scan_name],
                    "telescope": [tel.get_code() for tel in valid_telescopes],
                    "time": [t.iso for t in times],
                    "coord": ["x", "y", "z"]
                }
            )

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
    def _calculate_uv_coverage(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> xr.Dataset:
        """Calculate (u,v,w) coverage for all scans in the observation or project in geometric coordinates (meters).

        Args:
            obj (Observation | ScheduleProject): The object to calculate UV coverage for.
            attributes (Dict[str, Any]): Parameters including "time_step" and "store_key".

        Returns:
            xr.Dataset: UV coverage data with dimensions [scan, baseline, time, coord].

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
                    return xr.Dataset()
                datasets = []
                max_workers = self._get_max_workers(len(observations), is_cpu_bound=True)
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._calculate_uv_coverage, obs, attributes): obs.get_observation_code()
                        for obs in observations
                    }
                    for future in futures:
                        obs_code = futures[future]
                        ds = future.result()
                        ds = ds.assign_coords({"observation": obs_code})
                        datasets.append(ds)
                logger.info(f"Calculated (u,v,w) coverage for {len(observations)} observations in project '{obj.name}' with '{max_workers}' workers")
                return xr.concat(datasets, dim="observation") if datasets else xr.Dataset()

            def calculate_uv(obj, attrs):
                scans = obj.get_scans().get_active_items()
                visibility_attrs = {"time_step": time_step, "store_key": "source_visibility", "recalculate": attrs.get("recalculate", False)}
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": attrs.get("recalculate", False)}
                visibility_data = self._calculate_source_visibility(obj, visibility_attrs)
                position_data = self._calculate_telescope_positions(obj, position_attrs)
                if "visibility" not in visibility_data or "positions" not in position_data:
                    logger.error(f"Missing visibility or position data for '{obj.get_observation_code()}'")
                    return xr.Dataset()

                scan_names = [scan.name for scan in scans]
                max_telescopes = max(len(scan.get_telescopes(obj).get_active_items()) for scan in scans) if scans else 0
                max_baselines = max((n * (n - 1)) // 2 for n in [len(scan.get_telescopes(obj).get_active_items()) for scan in scans]) if scans else 0
                max_times = max(int(scan.get_duration() / time_step) if time_step else 1 for scan in scans) if scans else 0
                if not scans:
                    logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
                    return xr.Dataset()

                uv_points = np.full((len(scans), max_baselines, max_times, 3), np.nan)
                baseline_coords = []
                time_coords = []
                source_names = []

                for scan_idx, scan in enumerate(scans):
                    scan_name = scan.name
                    ds = self._process_uv_coverage(scan, obj, time_step, visibility_data, position_data)
                    if "uv_points" not in ds:
                        continue
                    uv = ds["uv_points"].values
                    baselines = ds["baseline"].values
                    times = ds["time"].values
                    source = ds["source"].item()
                    pad_baseline = max_baselines - uv.shape[0]
                    pad_time = max_times - uv.shape[1]
                    if pad_baseline > 0 or pad_time > 0:
                        uv = np.pad(uv, ((0, pad_baseline), (0, pad_time), (0, 0)), mode='constant', constant_values=np.nan)
                    uv_points[scan_idx, :uv.shape[0], :uv.shape[1], :] = uv
                    baseline_coords.append(baselines)
                    time_coords.append(times)
                    source_names.append(source)

                if not baseline_coords:
                    return xr.Dataset()

                all_baselines = np.unique(np.concatenate(baseline_coords), return_index=False)
                all_times = np.unique(np.concatenate(time_coords), return_index=False)
                dataset = xr.Dataset(
                    data_vars={"uv_points": (["scan", "baseline", "time", "coord"], uv_points)},
                    coords={
                        "scan": scan_names,
                        "baseline": all_baselines[:max_baselines],
                        "time": all_times[:max_times],
                        "coord": ["u", "v", "w"],
                        "source": (["scan"], source_names)
                    }
                )
                return dataset

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items()), "observation_code": obj.get_observation_code()}
            return self._get_cached_or_calculate(obj, store_key, calculate_uv, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate (u,v,w) coverage: {str(e)}")
            return xr.Dataset()

    def _process_uv_coverage(self, scan: Scan, observation: Observation, time_step: Optional[float], visibility_data: xr.Dataset, position_data: xr.Dataset) -> xr.Dataset:
        """Process UV coverage for a single scan using vectorized computations in geometric coordinates (meters).

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds).
            visibility_data (xr.Dataset): Precomputed visibility data.
            position_data (xr.Dataset): Precomputed position data.

        Returns:
            xr.Dataset: UV points with dimensions [baseline, time, coord].
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        source = scan.get_source(observation)
        scan_name = scan.name

        if len(active_telescopes) < 2:
            logger.warning(f"Insufficient telescopes ({len(active_telescopes)}) for UV coverage in scan {scan_name}")
            return xr.Dataset(coords={"scan": [scan_name], "source": source.name if source else None})

        if time_step is None:
            times = Time(start_time + (duration / 2) * u.s)
            times = times.reshape(-1)
        else:
            if time_step > duration:
                logger.error(f"time_step ({time_step}s) exceeds scan duration ({duration}s) for scan {scan_name}; calculation aborted")
                return xr.Dataset(coords={"scan": [scan_name], "source": source.name if source else None})
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')

        scan_visibility = visibility_data.sel(scan=scan_name).get("visibility", xr.DataArray())
        scan_positions = position_data.sel(scan=scan_name).get("positions", xr.DataArray())
        if not scan_visibility.size or not scan_positions.size:
            logger.warning(f"No visibility or position data for scan {scan_name}")
            return xr.Dataset(coords={"scan": [scan_name], "time": [t.iso for t in times], "source": source.name if source else None})

        tel_codes = [tel.get_code() for tel in active_telescopes]
        visibility = scan_visibility.values
        positions = scan_positions.values

        if positions.shape[1] != len(times):
            logger.warning(f"Mismatched position data length for scan {scan_name}")
            return xr.Dataset(coords={"scan": [scan_name], "time": [t.iso for t in times], "source": source.name if source else None})

        uv_points = self._compute_uv_at_time(active_telescopes, times, source, visibility, positions)
        baseline_pairs = [f"{tel_codes[i]}-{tel_codes[j]}" for i in range(len(tel_codes)) for j in range(i + 1, len(tel_codes))]
        uv_array = np.zeros((len(baseline_pairs), len(times), 3))
        for time_idx, points in enumerate(uv_points):
            for pair, uuu, vvv, www in points:
                pair_idx = baseline_pairs.index(pair)
                uv_array[pair_idx, time_idx] = [uuu, vvv, www]

        return xr.Dataset(
            data_vars={"uv_points": (["baseline", "time", "coord"], uv_array)},
            coords={
                "scan": [scan_name],
                "baseline": baseline_pairs,
                "time": [t.iso for t in times],
                "coord": ["u", "v", "w"],
                "source": source.name if source else None
            }
        )

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
        i_indices = np.array([i for i in range(n_tels) for j in range(i + 1, n_tels)])  # shape: (n_pairs,)
        j_indices = np.array([j for i in range(n_tels) for j in range(i + 1, n_tels)])  # shape: (n_pairs,)
        tel_codes = [tel.get_code() for tel in telescopes]
        baseline_pairs = [f"{tel_codes[i]}-{tel_codes[j]}" for i, j in zip(i_indices, j_indices)]

        # Vectorized baseline computation
        baselines = gcrs_positions[i_indices, :, :] - gcrs_positions[j_indices, :, :]  # shape: (n_pairs, n_times, 3)
        X, Y, Z = baselines[:, :, 0], baselines[:, :, 1], baselines[:, :, 2]  # shape: (n_pairs, n_times)

        # Vectorized UVW computation in meters
        uu = -np.sin(ra) * X + np.cos(ra) * Y  # shape: (n_pairs, n_times)
        vv = -np.cos(ra) * np.sin(dec) * X - np.sin(ra) * np.sin(dec) * Y + np.cos(dec) * Z
        ww = np.cos(ra) * np.cos(dec) * X + np.sin(ra) * np.cos(dec) * Y + np.sin(dec) * Z
        uvw = np.stack([uu, vv, ww], axis=-1)  # shape: (n_pairs, n_times, 3)

        # Apply visibility mask
        vis_mask = visibility[i_indices, None, :] & visibility[j_indices, None, :]  # shape: (n_pairs, 1, n_times)
        vis_mask = vis_mask.squeeze(axis=1)  # shape: (n_pairs, n_times)

        # Collect valid UVW points
        valid_mask = vis_mask & ~np.any(np.isnan(uvw), axis=-1)  # shape: (n_pairs, n_times)
        valid_indices = np.where(valid_mask)  # tuple of (pair_indices, time_indices)
        valid_pairs = [baseline_pairs[pair_idx] for pair_idx in valid_indices[0]]
        valid_times = valid_indices[1]
        valid_uvw = uvw[valid_indices[0], valid_indices[1]]  # shape: (n_valid, 3)

        # Distribute points to time indices
        for time_idx in range(n_times):
            time_mask = valid_times == time_idx
            time_pairs = [valid_pairs[i] for i in np.where(time_mask)[0]]
            time_uvw = valid_uvw[time_mask]  # shape: (n_valid_at_time, 3)
            uv_points[time_idx] = [(pair, float(u), float(v), float(w)) for pair, (u, v, w) in zip(time_pairs, time_uvw)]

        for time_idx, points in enumerate(uv_points):
            if points:
                logger.debug(f"Computed {len(points)} UV points at time index {time_idx} for source '{source.name}'")

        return uv_points

    @time_execution
    def _calculate_sun_angles(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> xr.Dataset:
        """Calculate angular separation between source and Sun for all scans.

        Args:
            obj (Observation | ScheduleProject): The object to calculate sun angles for.
            attributes (Dict[str, Any]): Parameters including "time_step" and "store_key".

        Returns:
            xr.Dataset: Sun angles with dimensions [scan, telescope, time].
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "sun_angles")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return xr.Dataset()
                datasets = []
                max_workers = self._get_max_workers(len(observations), is_cpu_bound=True)
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._calculate_sun_angles, obs, attributes): obs.get_observation_code()
                        for obs in observations
                    }
                    for future in futures:
                        obs_code = futures[future]
                        ds = future.result()
                        ds = ds.assign_coords({"observation": obs_code})
                        datasets.append(ds)
                logger.info(f"Calculated sun angles for {len(observations)} observations in project '{obj.name}'")
                return xr.concat(datasets, dim="observation") if datasets else xr.Dataset()

            def calculate_sun_angles(obj, attrs):
                scans = obj.get_scans().get_active_items()
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": attrs.get("recalculate", False)}
                position_data = self._calculate_telescope_positions(obj, position_attrs)
                if "positions" not in position_data:
                    logger.error(f"Failed to obtain telescope positions for '{obj.get_observation_code()}'")
                    return xr.Dataset()

                scan_names = [scan.name for scan in scans]
                max_telescopes = max(len(scan.get_telescopes(obj).get_active_items()) for scan in scans) if scans else 0
                max_times = max(int(scan.get_duration() / time_step) if time_step else 1 for scan in scans) if scans else 0
                if not scans:
                    logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
                    return xr.Dataset()

                angles = np.full((len(scans), max_telescopes, max_times), np.nan, dtype=float)
                telescope_coords = []
                time_coords = []
                source_names = []

                for scan_idx, scan in enumerate(scans):
                    scan_name = scan.name
                    ds = self._process_sun_angles(scan, obj, time_step, position_data)
                    if "sun_angles" not in ds:
                        continue
                    ang = ds["sun_angles"].values
                    tels = ds["telescope"].values
                    times = ds["time"].values
                    source = ds["source"].item()
                    pad_tel = max_telescopes - ang.shape[0]
                    pad_time = max_times - ang.shape[1]
                    if pad_tel > 0 or pad_time > 0:
                        ang = np.pad(ang, ((0, pad_tel), (0, pad_time)), mode='constant', constant_values=np.nan)
                    angles[scan_idx, :ang.shape[0], :ang.shape[1]] = ang
                    telescope_coords.append(tels)
                    time_coords.append(times)
                    source_names.append(source)

                if not telescope_coords:
                    return xr.Dataset()

                all_telescopes = np.unique(np.concatenate(telescope_coords), return_index=False)
                all_times = np.unique(np.concatenate(time_coords), return_index=False)
                dataset = xr.Dataset(
                    data_vars={"sun_angles": (["scan", "telescope", "time"], angles)},
                    coords={
                        "scan": scan_names,
                        "telescope": all_telescopes[:max_telescopes],
                        "time": all_times[:max_times],
                        "source": (["scan"], source_names)
                    },
                    attrs={"unit": "degrees"}
                )
                return dataset

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items()), "observation_code": obj.get_observation_code()}
            return self._get_cached_or_calculate(obj, store_key, calculate_sun_angles, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate sun angles: {str(e)}")
            return xr.Dataset()

    def _process_sun_angles(self, scan: Scan, observation: Observation, time_step: Optional[float], position_data: xr.Dataset) -> xr.Dataset:
        """Process sun angles for a single scan using vectorized computations for all telescopes.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds). If None, uses mean time.
            position_data (xr.Dataset): Precomputed telescope positions.

        Returns:
            xr.Dataset: Sun angles with dimensions [telescope, time] for all active telescopes, or empty dataset if no source or telescopes.
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        source = scan.get_source(observation)
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        scan_name = scan.name

        # Check for source availability
        if not source:
            logger.warning(f"No source specified for scan {scan_name} in observation '{observation.get_observation_code()}'")
            return xr.Dataset(coords={"scan": [scan_name], "source": None})

        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
        if not np.isfinite(source_coord.ra.deg) or not np.isfinite(source_coord.dec.deg):
            logger.warning(f"Invalid source coordinates for scan {scan_name}: RA={source.ra_degrees}, Dec={source.dec_degrees}")
            return xr.Dataset(coords={"scan": [scan_name], "source": source.name})

        # Check for active telescopes
        if not active_telescopes:
            logger.warning(f"No active telescopes available for scan {scan_name} in observation '{observation.get_observation_code()}'")
            return xr.Dataset(coords={"scan": [scan_name], "source": source.name})

        # Set up time array
        if time_step is None:
            times = Time(start_time + (duration / 2) * u.s)
            times = times.reshape(-1)
        else:
            if time_step > duration:
                logger.error(f"time_step ({time_step}s) exceeds scan duration ({duration}s) for scan {scan_name}; calculation aborted")
                return xr.Dataset(coords={"scan": [scan_name], "source": source.name if source else None})
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')

        # Split telescopes into ground and space
        ground_tels = [tel for tel in active_telescopes if not isinstance(tel, SpaceTelescope)]
        space_tels = [tel for tel in active_telescopes if isinstance(tel, SpaceTelescope)]
        telescope_codes = [tel.get_code() for tel in active_telescopes]

        # Initialize angles array
        angles = np.full((len(active_telescopes), len(times)), np.nan, dtype=float)

        # Compute Sun position
        sun_gcrs = get_sun(times)
        sun_pos = np.array([
            sun_gcrs.cartesian.x.to(u.m).value,
            sun_gcrs.cartesian.y.to(u.m).value,
            sun_gcrs.cartesian.z.to(u.m).value
        ]).T  # shape: (n_times, 3)

        # Compute source direction
        source_icrs = source_coord.icrs
        source_dir = np.array([
            source_icrs.cartesian.x.value,
            source_icrs.cartesian.y.value,
            source_icrs.cartesian.z.value
        ])
        source_dir /= np.linalg.norm(source_dir)  # normalize

        # Process ground telescopes
        if ground_tels:
            ground_codes = [tel.get_code() for tel in ground_tels]
            ground_indices = [telescope_codes.index(code) for code in ground_codes]
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
            altaz_frame = AltAz(obstime=times, location=locations)
            source_altaz = source_coord.transform_to(altaz_frame)
            sun_altaz = sun_gcrs.transform_to(altaz_frame)
            separations = source_altaz.separation(sun_altaz).deg
            separations = np.where((source_altaz.alt.deg < 0) | (sun_altaz.alt.deg < 0), np.nan, separations)
            for idx, tel_idx in enumerate(ground_indices):
                angles[tel_idx] = separations[idx]

        # Process space telescopes
        if space_tels:
            space_codes = [tel.get_code() for tel in space_tels]
            space_indices = [telescope_codes.index(code) for code in space_codes]
            positions = position_data.sel(telescope=space_codes, scan=scan_name).get("positions", xr.DataArray()).values  # shape: (n_space_tels, n_times, 3)
            if positions.shape[0] != len(space_codes) or positions.shape[1] != len(times):
                logger.warning(f"Mismatched position data for space telescopes in scan {scan_name}: expected shape ({len(space_codes)}, {len(times)}, 3), got {positions.shape}")
                positions = np.full((len(space_codes), len(times), 3), np.nan)
            valid_mask = np.all(np.isfinite(positions), axis=-1)  # shape: (n_space_tels, n_times)
            vec_to_sun = sun_pos[None, :, :] - positions  # shape: (n_space_tels, n_times, 3)
            norm_vec_to_sun = vec_to_sun / np.linalg.norm(vec_to_sun, axis=-1, keepdims=True)  # normalize
            cos_angles = np.einsum('ijk,k->ij', norm_vec_to_sun, source_dir)  # shape: (n_space_tels, n_times)
            cos_angles = np.clip(cos_angles, -1.0, 1.0)
            tel_angles = np.degrees(np.arccos(cos_angles))  # shape: (n_space_tels, n_times)
            tel_angles[~valid_mask] = np.nan
            for idx, tel_idx in enumerate(space_indices):
                angles[tel_idx] = tel_angles[idx]
            if np.any(~valid_mask):
                invalid_tel_times = [(space_codes[i], times[j].isot) for i, j in np.where(~valid_mask)]
                logger.debug(f"Invalid positions for {len(invalid_tel_times)} space telescope-time pairs in scan {scan_name}: {invalid_tel_times}")

        # Check for valid data
        if not np.any(np.isfinite(angles)):
            logger.warning(f"No valid sun angles calculated for scan {scan_name}")
            return xr.Dataset(coords={"scan": [scan_name], "source": source.name, "time": [t.iso for t in times]})

        return xr.Dataset(
            data_vars={"sun_angles": (["telescope", "time"], angles)},
            coords={
                "scan": [scan_name],
                "telescope": telescope_codes,
                "time": [t.iso for t in times],
                "source": source.name
            },
            attrs={"unit": "degrees"}
        )

    @time_execution
    def _calculate_az_el(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> xr.Dataset:
        """Calculate Az/El or HA/Dec for ground telescopes across all scans.

        Args:
            obj (Observation | ScheduleProject): The object to calculate coordinates for.
            attributes (Dict[str, Any]): Parameters including "time_step" and "store_key".

        Returns:
            xr.Dataset: Az/El or HA/Dec data with dimensions [scan, telescope, time, coord].
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "az_el")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return xr.Dataset()
                datasets = []
                max_workers = self._get_max_workers(len(observations), is_cpu_bound=True)
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._calculate_az_el, obs, attributes): obs.get_observation_code()
                        for obs in observations
                    }
                    for future in futures:
                        obs_code = futures[future]
                        ds = future.result()
                        ds = ds.assign_coords({"observation": obs_code})
                        datasets.append(ds)
                logger.info(f"Calculated Az/El for {len(observations)} observations in project '{obj.name}'")
                return xr.concat(datasets, dim="observation") if datasets else xr.Dataset()

            def calculate_az_el(obj, attrs):
                scans = obj.get_scans().get_active_items()
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": attrs.get("recalculate", False)}
                position_data = self._calculate_telescope_positions(obj, position_attrs)
                if "positions" not in position_data:
                    logger.error(f"Failed to obtain telescope positions for '{obj.get_observation_code()}'")
                    return xr.Dataset()

                scan_names = [scan.name for scan in scans]
                max_telescopes = max(len([t for t in scan.get_telescopes(obj).get_items() if not isinstance(t, SpaceTelescope)]) for scan in scans) if scans else 0
                max_times = max(int(scan.get_duration() / time_step) if time_step else 1 for scan in scans) if scans else 0
                if not scans:
                    logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
                    return xr.Dataset()

                coords_data = np.full((len(scans), max_telescopes, max_times, 2), np.nan, dtype=float)
                telescope_coords = []
                time_coords = []
                source_names = []

                for scan_idx, scan in enumerate(scans):
                    scan_name = scan.name
                    ds = self._process_az_el(scan, obj, time_step, position_data)
                    if "coords" not in ds:
                        continue
                    coord = ds["coords"].values
                    tels = ds["telescope"].values
                    times = ds["time"].values
                    source = ds["source"].item()
                    pad_tel = max_telescopes - coord.shape[0]
                    pad_time = max_times - coord.shape[1]
                    if pad_tel > 0 or pad_time > 0:
                        coord = np.pad(coord, ((0, pad_tel), (0, pad_time), (0, 0)), mode='constant', constant_values=np.nan)
                    coords_data[scan_idx, :coord.shape[0], :coord.shape[1], :] = coord
                    telescope_coords.append(tels)
                    time_coords.append(times)
                    source_names.append(source)

                if not telescope_coords:
                    return xr.Dataset()

                all_telescopes = np.unique(np.concatenate(telescope_coords), return_index=False)
                all_times = np.unique(np.concatenate(time_coords), return_index=False)
                dataset = xr.Dataset(
                    data_vars={"coords": (["scan", "telescope", "time", "coord"], coords_data)},
                    coords={
                        "scan": scan_names,
                        "telescope": all_telescopes[:max_telescopes],
                        "time": all_times[:max_times],
                        "coord": ["az", "el"],
                        "source": (["scan"], source_names)
                    },
                    attrs={"unit": "degrees"}
                )
                return dataset

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items()), "observation_code": obj.get_observation_code()}
            return self._get_cached_or_calculate(obj, store_key, calculate_az_el, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate Az/El: {str(e)}")
            return xr.Dataset()

    def _process_az_el(self, scan: Scan, observation: Observation, time_step: Optional[float], position_data: xr.Dataset) -> xr.Dataset:
        """Process Az/El or HA/Dec for a single scan.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds).
            position_data (xr.Dataset): Precomputed telescope positions.

        Returns:
            xr.Dataset: Az/El or HA/Dec with dimensions [telescope, time].
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        source = scan.get_source(observation)
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs') if source else None
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive and not isinstance(t, SpaceTelescope)]
        scan_name = scan.name

        if not active_telescopes or not source_coord:
            logger.warning(f"No ground telescopes or source for scan {scan_name}")
            return xr.Dataset(coords={"scan": [scan_name], "source": source.name if source else None})

        if time_step is None:
            times = Time(start_time + (duration / 2) * u.s)
            times = times.reshape(-1)
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')

        tel_codes = [tel.get_code() for tel in active_telescopes]
        mount_types = [tel.get("mount_type").value for tel in active_telescopes]
        az_ranges = [tel.get_azimuth_range() for tel in active_telescopes]
        el_ranges = [tel.get_elevation_range() for tel in active_telescopes]
        x = np.array([tel.get_coordinates()[0] for tel in active_telescopes])
        y = np.array([tel.get_coordinates()[1] for tel in active_telescopes])
        z = np.array([tel.get_coordinates()[2] for tel in active_telescopes])
        vx = np.array([tel.get(["vx", "vy", "vz"])["vx"] for tel in active_telescopes])
        vy = np.array([tel.get(["vx", "vy", "vz"])["vy"] for tel in active_telescopes])
        vz = np.array([tel.get(["vx", "vy", "vz"])["vz"] for tel in active_telescopes])
        dt = (times - Time("2000-01-01T12:00:00")).sec
        itrs_coords = CartesianRepresentation(
            x[:, None] + vx[:, None] * dt,
            y[:, None] + vy[:, None] * dt,
            z[:, None] + vz[:, None] * dt,
            unit=u.m
        )
        itrs = ITRS(itrs_coords, obstime=times)
        locations = itrs.earth_location

        coords_data = np.full((len(tel_codes), len(times), 2), np.nan, dtype=float)
        azim_mask = np.array([mount == "AZIM" for mount in mount_types])
        if azim_mask.any():
            azim_indices = np.where(azim_mask)[0]
            azim_location = locations[azim_indices]
            az_min = np.array([az_ranges[i][0] for i in azim_indices])[:, None]  # Shape: (n_tel, 1)
            az_max = np.array([az_ranges[i][1] for i in azim_indices])[:, None]  # Shape: (n_tel, 1)
            el_min = np.array([el_ranges[i][0] for i in azim_indices])[:, None]  # Shape: (n_tel, 1)
            el_max = np.array([el_ranges[i][1] for i in azim_indices])[:, None]  # Shape: (n_tel, 1)
            altaz_frame = AltAz(obstime=times, location=azim_location)
            source_altaz = source_coord.transform_to(altaz_frame)
            az = source_altaz.az.deg  # Shape: (n_tel, n_times)
            el = source_altaz.alt.deg  # Shape: (n_tel, n_times)
            valid = (az_min <= az) & (az <= az_max) & (el_min <= el) & (el <= el_max)  # Broadcasting works
            coords_data[azim_indices] = np.where(valid[:, :, None], np.stack([az, el], axis=-1), np.nan)

        equa_mask = np.array([mount == "EQUA" for mount in mount_types])
        if equa_mask.any():
            equa_indices = np.where(equa_mask)[0]
            equa_location = locations[equa_indices]
            ha_min = np.array([az_ranges[i][0] for i in equa_indices])[:, None]  # Shape: (n_tel, 1)
            ha_max = np.array([az_ranges[i][1] for i in equa_indices])[:, None]  # Shape: (n_tel, 1)
            dec_min = np.array([el_ranges[i][0] for i in equa_indices])[:, None]  # Shape: (n_tel, 1)
            dec_max = np.array([el_ranges[i][1] for i in equa_indices])[:, None]  # Shape: (n_tel, 1)
            hadec_frame = HADec(obstime=times, location=equa_location)
            source_hadec = source_coord.transform_to(hadec_frame)
            ha = source_hadec.ha.deg  # Shape: (n_tel, n_times)
            dec = source_hadec.dec.deg  # Shape: (n_tel, n_times)
            valid = (ha_min <= ha) & (ha <= ha_max) & (dec_min <= dec) & (dec <= dec_max)  # Broadcasting works
            coords_data[equa_indices] = np.where(valid[:, :, None], np.stack([ha, dec], axis=-1), np.nan)

        for idx, (tel, code) in enumerate(zip(active_telescopes, tel_codes)):
            if mount_types[idx] not in ["AZIM", "EQUA"]:
                logger.warning(f"Unsupported mount type {tel.get('mount_type')} for telescope '{code}'")
                coords_data[idx] = np.full((len(times), 2), np.nan)

        return xr.Dataset(
            data_vars={"coords": (["telescope", "time", "coord"], coords_data)},
            coords={
                "scan": [scan_name],
                "telescope": tel_codes,
                "time": [t.iso for t in times],
                "coord": ["coord1", "coord2"],  # Use generic names for flexibility
                "source": source.name if source else None
            },
            attrs={"unit": "degrees"}
        )

    @time_execution
    def _calculate_time_on_source(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> xr.Dataset:
        """Calculate time on source for all sources and telescopes across all scans.

        Args:
            obj (Observation | ScheduleProject): The object to calculate time on source for.
            attributes (Dict[str, Any]): Parameters including "time_step" and "store_key".

        Returns:
            xr.Dataset: Visibility blocks with dimensions [source, telescope, block] and total time per source.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "time_on_source")
            visibility_store_key = attributes.get("store_key", "source_visibility")

            if not time_step:
                logger.error("Time step not provided for time on source calculation")
                return xr.Dataset()

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return xr.Dataset()
                datasets = []
                max_workers = min(len(observations), 4) if len(observations) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._calculate_time_on_source, obs, attributes): obs.get_observation_code()
                        for obs in observations
                    }
                    for future in futures:
                        obs_code = futures[future]
                        ds = future.result()
                        ds = ds.assign_coords({"observation": obs_code})
                        datasets.append(ds)
                logger.info(f"Calculated time on source for {len(observations)} observations in project '{obj.name}'")
                return xr.concat(datasets, dim="observation") if datasets else xr.Dataset()

            def calculate_time_on_source(obj, attrs):
                scans = obj.get_scans().get_active_scans(obj)
                # Собираем уникальные источники из активных сканов
                source_dict = {}
                for scan in scans:
                    source = scan.get_source(obj)
                    if source and source.isactive and source.name not in source_dict:
                        source_dict[source.name] = source
                sources = Sources(items=source_dict)
                telescopes = obj.get_telescopes()
                active_telescopes = telescopes.get_active_items()
                if not active_telescopes or not sources:
                    logger.warning(f"No active telescopes or sources in observation '{obj.get_observation_code()}'")
                    return xr.Dataset()
                source_names = [src.name for src in sources.get_items()]
                telescope_codes = [tel.get_code() for tel in active_telescopes]
                visibility_attrs = {
                    "time_step": time_step,
                    "store_key": visibility_store_key,
                    "recalculate": attrs.get("recalculate", False)
                }
                visibility_data = self._calculate_source_visibility(obj, visibility_attrs)
                if not visibility_data.data_vars:
                    logger.error(f"No visibility data for '{obj.get_observation_code()}'")
                    return xr.Dataset()
                max_blocks = 0
                datasets = []
                for scan in scans:
                    ds = self._process_time_on_source(scan, obj, time_step, visibility_data)
                    if ds.data_vars:
                        max_blocks = max(max_blocks, len(ds.coords["block"]))
                        datasets.append(ds)
                if not datasets:
                    logger.warning(f"No valid visibility blocks for observation '{obj.get_observation_code()}'")
                    return xr.Dataset()
                combined = xr.concat(datasets, dim="scan")
                total_times = np.zeros(len(source_names), dtype=float)
                padded_blocks = np.full((len(source_names), len(telescope_codes), max_blocks), None, dtype=object)
                for i, src_name in enumerate(source_names):
                    src_scans = combined.where(combined.source == src_name, drop=True)
                    if not src_scans.sizes.get("scan", 0):
                        continue
                    for tel_idx, tel_code in enumerate(telescope_codes):
                        tel_blocks = []
                        for scan in src_scans.scan.values:
                            scan_blocks = src_scans.sel(telescope=tel_code, scan=scan).visibility_blocks.values
                            scan_blocks = scan_blocks[scan_blocks != None]
                            tel_blocks.extend([b for b in scan_blocks if b])
                        if tel_blocks:
                            padded_blocks[i, tel_idx, :len(tel_blocks)] = tel_blocks
                        total_times[i] = sum(b["duration"] for b in tel_blocks if b)
                return xr.Dataset(
                    data_vars={
                        "visibility_blocks": (["source", "telescope", "block"], padded_blocks),
                        "total_time": (["source"], total_times)
                    },
                    coords={
                        "source": source_names,
                        "telescope": telescope_codes,
                        "block": np.arange(max_blocks)
                    },
                    attrs={"unit": "seconds"}
                )

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_scans(obj)),
                "observation_code": obj.get_observation_code()
            }
            return self._get_cached_or_calculate(obj, store_key, calculate_time_on_source, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate time on source: {str(e)}")
            return xr.Dataset()
        
    def _process_time_on_source(self, scan: Scan, observation: Observation, time_step: float, visibility_data: xr.Dataset) -> xr.Dataset:
        """Process time on source for a single scan.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (float): Sampling interval (seconds).
            visibility_data (xr.Dataset): Precomputed visibility data.

        Returns:
            xr.Dataset: Visibility blocks with dimensions [telescope, block].
        """
        start_time = scan.get_start()
        duration = scan.get_duration()
        source = scan.get_source(observation)
        scan_name = scan.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]

        if not source or not active_telescopes:
            logger.warning(f"No source or active telescopes for scan {scan_name} in observation '{observation.get_observation_code()}'")
            return xr.Dataset(coords={"scan": [scan_name], "source": source.name if source else None})

        time_values = np.arange(0, duration, time_step) * u.s
        times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')

        try:
            scan_data = visibility_data.sel(scan=scan_name)
            visibility = scan_data.get("visibility", None)
            if visibility is None or not visibility.size:
                logger.warning(f"No visibility data for scan {scan_name} in observation '{observation.get_observation_code()}'")
                return xr.Dataset(coords={"scan": [scan_name], "source": source.name})
        except KeyError:
            logger.warning(f"Scan {scan_name} not found in visibility data for observation '{observation.get_observation_code()}'")
            return xr.Dataset(coords={"scan": [scan_name], "source": source.name})

        blocks = []
        for tel_idx, tel in enumerate(active_telescopes):
            tel_code = tel.get_code()
            try:
                tel_visibility = visibility.sel(telescope=tel_code).values
            except KeyError:
                logger.warning(f"No visibility data for telescope '{tel_code}' in scan {scan_name}")
                tel_visibility = np.zeros(len(times), dtype=bool)
            tel_blocks = []
            start_block = None
            for t_idx, is_visible in enumerate(tel_visibility):
                current_time = times[t_idx]
                if is_visible and start_block is None:
                    start_block = current_time
                elif not is_visible and start_block is not None:
                    end_block = times[t_idx - 1] if t_idx > 0 else current_time
                    duration_block = (end_block - start_block).sec
                    tel_blocks.append({"start": start_block.isot, "end": end_block.isot, "duration": duration_block})
                    start_block = None
                if t_idx == len(tel_visibility) - 1 and start_block is not None:
                    end_block = current_time
                    duration_block = (end_block - start_block).sec
                    tel_blocks.append({"start": start_block.isot, "end": end_block.isot, "duration": duration_block})
            blocks.append(tel_blocks)

        max_blocks = max(len(b) for b in blocks) if blocks else 1
        padded_blocks = np.full((len(active_telescopes), max_blocks), None, dtype=object)
        for i, tel_blocks in enumerate(blocks):
            padded_blocks[i, :len(tel_blocks)] = tel_blocks

        return xr.Dataset(
            data_vars={"visibility_blocks": (["telescope", "block"], padded_blocks)},
            coords={
                "scan": [scan_name],
                "telescope": [tel.get_code() for tel in active_telescopes],
                "block": np.arange(max_blocks),
                "source": source.name
            },
            attrs={"unit": "seconds"}
        )

    @time_execution
    def _calculate_beam_pattern(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> xr.Dataset:
        """Calculate beam pattern for single-dish observations.

        Args:
            obj (Observation | ScheduleProject): The object to calculate beam pattern for.
            attributes (Dict[str, Any]): Parameters including "freq_name" and "store_key".

        Returns:
            xr.Dataset: Beam pattern data with dimensions [telescope, theta].
        """
        try:
            freq_name = attributes.get("freq_name")
            store_key = attributes.get("store_key", f"beam_pattern_{freq_name}")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return xr.Dataset()
                datasets = []
                for obs in observations:
                    ds = self._calculate_beam_pattern(obs, attributes)
                    if "pattern" in ds:
                        ds = ds.assign_coords({"observation": obs.get_observation_code()})
                        datasets.append(ds)
                logger.info(f"Calculated beam pattern for {len(observations)} observations in project '{obj.name}'")
                return xr.concat(datasets, dim="observation") if datasets else xr.Dataset()

            if obj.get_observation_type() != "SINGLE_DISH":
                logger.warning(f"Beam pattern calculation is only for SINGLE_DISH, got {obj.get_observation_type()}")
                return xr.Dataset()

            def calculate_beam_pattern(obj, attrs):
                telescopes = obj.get_telescopes().get_active_items()
                frequency = obj.get_frequencies().get(freq_name).get("frequency") * 1e6
                c = 299792458
                wavelength = c / frequency
                theta = np.linspace(-np.pi/2, np.pi/2, 5000)
                ground_tels = [tel for tel in telescopes if not isinstance(tel, SpaceTelescope)]
                if not ground_tels:
                    logger.warning(f"No ground telescopes available for beam pattern calculation in '{obj.get_observation_code()}'")
                    return xr.Dataset()
                tel_codes = [tel.get_code() for tel in ground_tels]
                diameters = np.array([tel.get("diameter") for tel in ground_tels])
                x = (np.pi * diameters[:, None] / wavelength) * np.sin(theta)
                patterns = (2 * j1(x) / x) ** 2
                patterns = np.where(np.isnan(patterns), 1.0, patterns)
                return xr.Dataset(
                    data_vars={"pattern": (["telescope", "theta"], patterns)},
                    coords={
                        "telescope": tel_codes,
                        "theta": theta
                    }
                )

            metadata = {"freq_name": freq_name, "observation_code": obj.get_observation_code()}
            return self._get_cached_or_calculate(obj, store_key, calculate_beam_pattern, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate beam pattern: {str(e)}")
            return xr.Dataset()

    @time_execution
    def _calculate_synthesized_beam(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> xr.Dataset:
        """Calculate synthesized beam for VLBI observations.

        Args:
            obj (Observation | ScheduleProject): The object to calculate synthesized beam for.
            attributes (Dict[str, Any]): Parameters including 'freq_name', 'time_step', and 'store_key'.

        Returns:
            xr.Dataset: Synthesized beam data with dimensions [scan, theta_u, theta_v] and coordinate 'source'.

        Notes:
            - Depends on precomputed UV coverage data from '_calculate_uv_coverage'.
            - Beam is computed as the 2D Fourier transform of the UV plane.
            - Stores results in obj._calculated_data with the specified store_key.
        """
        try:
            freq_name = attributes.get("freq_name")
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", f"synthesized_beam_{freq_name}")

            if not freq_name:
                logger.error("No 'freq_name' specified for synthesized beam calculation")
                return xr.Dataset()

            if isinstance(obj, Observation):
                if freq_name not in obj.get_frequencies():
                    logger.error(f"Frequency '{freq_name}' not found in observation '{obj.get_observation_code()}'")
                    return xr.Dataset()

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return xr.Dataset()
                datasets = []
                max_workers = self._get_max_workers(len(observations), is_cpu_bound=True)
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._calculate_synthesized_beam, obs, attributes): obs.get_observation_code()
                        for obs in observations
                    }
                    for future in futures:
                        obs_code = futures[future]
                        ds = future.result()
                        if "beam_2d" in ds:
                            ds = ds.assign_coords({"observation": obs_code})
                            datasets.append(ds)
                    logger.info(f"Calculated synthesized beam for {len(observations)} observations in project '{obj.name}'")
                return xr.concat(datasets, dim="observation") if datasets else xr.Dataset()

            if obj.get_observation_type() != "VLBI":
                logger.warning(f"Synthesized beam calculation is only for VLBI, got {obj.get_observation_type()}")
                return xr.Dataset()

            def calculate_synthesized_beam(obj, attrs):
                frequency = obj.get_frequencies().get(freq_name).get("frequency") * 1e6
                if frequency is None or frequency <= 0:
                    logger.error(f"Invalid frequency for freq_name '{freq_name}' in observation '{obj.get_observation_code()}'")
                    return xr.Dataset()

                uv_store_key = "uv_coverage"
                uv_data = self._calculate_uv_coverage(obj, {
                    "time_step": attrs.get("time_step"),
                    "store_key": uv_store_key,
                    "freq_name": freq_name,
                    "recalculate": attrs.get("recalculate", False)
                })
                if "uv_points" not in uv_data:
                    logger.warning(f"No UV data available for '{obj.get_observation_code()}'")
                    return xr.Dataset()

                scans = obj.get_scans().get_active_items()
                grid_size = attrs.get("grid_size", 512)
                scan_names = [scan.name for scan in scans]
                beam_2d_data = np.full((len(scans), grid_size, grid_size), np.nan, dtype=float)
                theta_u_coords = []
                theta_v_coords = []
                source_names = []

                for scan_idx, scan in enumerate(scans):
                    scan_name = scan.name
                    source = scan.get_source(obj)
                    if not source:
                        logger.warning(f"No source specified for scan '{scan_name}'")
                        continue

                    scan_uv_data = uv_data.sel(scan=scan_name).get("uv_points", xr.DataArray())
                    if not scan_uv_data.size:
                        logger.warning(f"No UV points for scan '{scan_name}' in observation '{obj.get_observation_code()}'")
                        continue

                    u = scan_uv_data.sel(coord="u").values.flatten()
                    v = scan_uv_data.sel(coord="v").values.flatten()
                    mask = ~np.isnan(u) & ~np.isnan(v)
                    u, v = u[mask], v[mask]
                    u = np.concatenate([u, -u])
                    v = np.concatenate([v, -v])

                    if not u.size or not v.size:
                        logger.warning(f"No valid UV points for scan '{scan_name}'")
                        continue

                    u_max = np.max(np.abs(u))
                    v_max = np.max(np.abs(v))
                    if u_max == 0 or v_max == 0:
                        logger.warning(f"Invalid UV range for scan '{scan_name}': u_max={u_max}, v_max={v_max}")
                        continue

                    u_grid = np.linspace(-u_max, u_max, grid_size)
                    v_grid = np.linspace(-v_max, v_max, grid_size)
                    uv_plane = np.zeros((grid_size, grid_size), dtype=complex)
                    u_idx = ((u + u_max) / (2 * u_max) * (grid_size - 1)).astype(int)
                    v_idx = ((v + v_max) / (2 * v_max) * (grid_size - 1)).astype(int)
                    valid = (0 <= u_idx) & (u_idx < grid_size) & (0 <= v_idx) & (v_idx < grid_size)
                    np.add.at(uv_plane, (v_idx[valid], u_idx[valid]), 1.0)

                    beam_2d = fftshift(fft2(uv_plane))
                    beam_2d = np.abs(beam_2d)
                    beam_2d /= np.max(beam_2d) if np.max(beam_2d) != 0 else 1.0

                    wavelength = 299792458 / frequency
                    theta_u_max = wavelength / (2 * u_max)
                    theta_v_max = wavelength / (2 * v_max)
                    theta_u = np.linspace(-theta_u_max, theta_u_max, grid_size)
                    theta_v = np.linspace(-theta_v_max, theta_v_max, grid_size)
                    theta_u_deg = np.degrees(theta_u)
                    theta_v_deg = np.degrees(theta_v)

                    beam_2d_data[scan_idx] = beam_2d
                    theta_u_coords.append(theta_u_deg)
                    theta_v_coords.append(theta_v_deg)
                    source_names.append(source.name)
                    logger.debug(f"Computed synthesized beam for scan '{scan_name}' with {len(u)//2} UV points, source '{source.name}'")

                if not source_names:
                    return xr.Dataset()

                # Use the first theta_u, theta_v (assuming consistent grid_size)
                dataset = xr.Dataset(
                    data_vars={"beam_2d": (["scan", "theta_v", "theta_u"], beam_2d_data)},
                    coords={
                        "scan": scan_names,
                        "theta_u": theta_u_coords[0] if theta_u_coords else np.linspace(-1, 1, grid_size),
                        "theta_v": theta_v_coords[0] if theta_v_coords else np.linspace(-1, 1, grid_size),
                        "source": (["scan"], source_names)
                    },
                    attrs={
                        "unit": "normalized",
                        "frequency": frequency / 1e6
                    }
                )
                return dataset

            metadata = {
                "freq_name": freq_name,
                "time_step": time_step,
                "observation_code": obj.get_observation_code(),
                "scan_count": len(obj.get_scans().get_active_items())
            }
            return self._get_cached_or_calculate(obj, store_key, calculate_synthesized_beam, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate synthesized beam for '{obj.get_observation_code()}': {str(e)}")
            return xr.Dataset()      

    @time_execution
    def _calculate_baseline_projections(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> xr.Dataset:
        """Calculate baseline projections for all scans in the observation or project in geometric coordinates (meters).

        Args:
            obj (Observation | ScheduleProject): The object to calculate baseline projections for.
            attributes (Dict[str, Any]): Parameters including "time_step" and "store_key".

        Returns:
            xr.Dataset: Baseline projection data with dimensions [scan, baseline, time].

        Notes:
            - Calculates projections in meters, accounting for source direction.
            - Depends on precomputed telescope positions and source visibility.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "baseline_projections")
            visibility_store_key = "source_visibility"
            position_store_key = "telescope_positions"

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return xr.Dataset()
                datasets = []
                max_workers = self._get_max_workers(len(observations), is_cpu_bound=True)
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._calculate_baseline_projections, obs, attributes): obs.get_observation_code()
                        for obs in observations
                    }
                    for future in futures:
                        obs_code = futures[future]
                        ds = future.result()
                        ds = ds.assign_coords({"observation": obs_code})
                        datasets.append(ds)
                logger.info(f"Calculated baseline projections for {len(observations)} observations in project '{obj.name}'")
                return xr.concat(datasets, dim="observation") if datasets else xr.Dataset()

            def calculate_projections(obj, attrs):
                scans = obj.get_scans().get_active_items()
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": attrs.get("recalculate", False)}
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": attrs.get("recalculate", False)}
                visibility_data = self._calculate_source_visibility(obj, visibility_attrs)
                position_data = self._calculate_telescope_positions(obj, position_attrs)
                if "visibility" not in visibility_data or "positions" not in position_data:
                    logger.error(f"Missing visibility or position data for '{obj.get_observation_code()}'")
                    return xr.Dataset()

                scan_names = [scan.name for scan in scans]
                max_telescopes = max(len(scan.get_telescopes(obj).get_active_items()) for scan in scans) if scans else 0
                max_baselines = max((n * (n - 1)) // 2 for n in [len(scan.get_telescopes(obj).get_active_items()) for scan in scans]) if scans else 0
                max_times = max(int(scan.get_duration() / time_step) if time_step else 1 for scan in scans) if scans else 0
                if not scans:
                    logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
                    return xr.Dataset()

                projections = np.full((len(scans), max_baselines, max_times), np.nan, dtype=float)
                baseline_coords = []
                time_coords = []
                source_names = []

                for scan_idx, scan in enumerate(scans):
                    scan_name = scan.name
                    ds = self._process_baseline_projections(scan, obj, time_step, visibility_data, position_data)
                    if "projections" not in ds:
                        continue
                    proj = ds["projections"].values
                    baselines = ds["baseline"].values
                    times = ds["time"].values
                    source = ds["source"].item()
                    pad_baseline = max_baselines - proj.shape[0]
                    pad_time = max_times - proj.shape[1]
                    if pad_baseline > 0 or pad_time > 0:
                        proj = np.pad(proj, ((0, pad_baseline), (0, pad_time)), mode='constant', constant_values=np.nan)
                    projections[scan_idx, :proj.shape[0], :proj.shape[1]] = proj
                    baseline_coords.append(baselines)
                    time_coords.append(times)
                    source_names.append(source)

                if not baseline_coords:
                    return xr.Dataset()

                all_baselines = np.unique(np.concatenate(baseline_coords), return_index=False)
                all_times = np.unique(np.concatenate(time_coords), return_index=False)
                dataset = xr.Dataset(
                    data_vars={"projections": (["scan", "baseline", "time"], projections)},
                    coords={
                        "scan": scan_names,
                        "baseline": all_baselines[:max_baselines],
                        "time": all_times[:max_times],
                        "source": (["scan"], source_names)
                    },
                    attrs={"unit": "meters"}
                )
                return dataset

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()),
                "observation_code": obj.get_observation_code()
            }
            return self._get_cached_or_calculate(obj, store_key, calculate_projections, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate baseline projections: {str(e)}")
            return xr.Dataset()

    def _process_baseline_projections(self, scan: Scan, observation: Observation, time_step: Optional[float], visibility_data: xr.Dataset, position_data: xr.Dataset) -> xr.Dataset:
        """Process baseline projections for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds).
            visibility_data (xr.Dataset): Precomputed visibility data.
            position_data (xr.Dataset): Precomputed telescope positions.

        Returns:
            xr.Dataset: Baseline projections with dimensions [baseline, time].
        """
        from astropy.coordinates import SkyCoord
        start_time = scan.get_start()
        duration = scan.get_duration()
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        source = scan.get_source(observation)
        scan_name = scan.name

        if not source:
            logger.error(f"No source specified for scan {scan_name}")
            return xr.Dataset(coords={"scan": [scan_name], "source": None})
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')

        if len(active_telescopes) < 2:
            logger.warning(f"Insufficient telescopes ({len(active_telescopes)}) for baseline projections in scan {scan_name}")
            return xr.Dataset(coords={"scan": [scan_name], "source": source.name})

        if time_step is None:
            times = Time(start_time + (duration / 2) * u.s)
            times = times.reshape(-1)
        else:
            if time_step > duration:
                logger.error(f"time_step ({time_step}s) exceeds scan duration ({duration}s) for scan {scan_name}; calculation aborted")
                return xr.Dataset(coords={"scan": [scan_name], "source": source.name if source else None})
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')

        scan_visibility = visibility_data.sel(scan=scan_name).get("visibility", xr.DataArray())
        scan_positions = position_data.sel(scan=scan_name).get("positions", xr.DataArray())
        if not scan_visibility.size or not scan_positions.size:
            logger.error(f"No visibility or position data for scan {scan_name}")
            return xr.Dataset(coords={"scan": [scan_name], "time": [t.iso for t in times], "source": source.name})

        tel_codes = [tel.get_code() for tel in active_telescopes]
        visibility = scan_visibility.values  # shape: (n_telescopes, n_times)
        positions = scan_positions.values  # shape: (n_telescopes, n_times, 3)
        if positions.shape[1] != len(times):
            logger.error(f"Mismatched position data length for scan {scan_name}: expected {len(times)}, got {positions.shape[1]}")
            return xr.Dataset(coords={"scan": [scan_name], "time": [t.iso for t in times], "source": source.name})

        # Compute baseline pairs
        n_tels = len(tel_codes)
        i_indices = np.array([i for i in range(n_tels) for j in range(i + 1, n_tels)])  # shape: (n_pairs,)
        j_indices = np.array([j for i in range(n_tels) for j in range(i + 1, n_tels)])  # shape: (n_pairs,)
        baseline_pairs = [f"{tel_codes[i]}-{tel_codes[j]}" for i, j in zip(i_indices, j_indices)]

        # Vectorized baseline computation
        baselines = positions[i_indices, :, :] - positions[j_indices, :, :]  # shape: (n_pairs, n_times, 3)

        # Compute source direction
        source_dir = np.array([
            source_coord.cartesian.x.value,
            source_coord.cartesian.y.value,
            source_coord.cartesian.z.value
        ])
        source_dir /= np.linalg.norm(source_dir)  # Normalize

        # Vectorized projection computation
        projections = np.abs(np.einsum('ijt,t->ij', baselines, source_dir))  # shape: (n_pairs, n_times)

        # Apply visibility mask
        vis_mask = visibility[i_indices, None, :] & visibility[j_indices, None, :]  # shape: (n_pairs, 1, n_times)
        vis_mask = vis_mask.squeeze(axis=1)  # shape: (n_pairs, n_times)
        projections[~vis_mask] = np.nan  # Set invisible baselines to NaN

        # Log invalid projections
        invalid_count = np.sum(~vis_mask)
        if invalid_count > 0:
            logger.debug(f"{invalid_count} baseline-time pairs have no visibility in scan {scan_name}")

        return xr.Dataset(
            data_vars={"projections": (["baseline", "time"], projections)},
            coords={
                "scan": [scan_name],
                "baseline": baseline_pairs,
                "time": [t.iso for t in times],
                "source": source.name
            },
            attrs={"unit": "meters"}
        )

    @time_execution
    def _calculate_mollweide_tracks(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> xr.Dataset:
        """Calculate Mollweide tracks for sources and telescopes across all scans.

        Args:
            obj (Observation | ScheduleProject): The object to calculate tracks for.
            attributes (Dict[str, Any]): Parameters including "time_step" and "store_key".

        Returns:
            xr.Dataset: Mollweide tracks with dimensions [scan, telescope, time] for telescope tracks and [scan] for source position.
            Returns empty dataset if no valid data is computed.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "mollweide_tracks")
            position_store_key = "telescope_positions"

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return xr.Dataset()
                datasets = []
                max_workers = self._get_max_workers(len(observations), is_cpu_bound=True)
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._calculate_mollweide_tracks, obs, attributes): obs.get_observation_code()
                        for obs in observations
                    }
                    for future in futures:
                        obs_code = futures[future]
                        try:
                            ds = future.result()
                            if ds and ("telescope_lon" in ds or "source_lon" in ds):
                                ds = ds.assign_coords({"observation": obs_code})
                                datasets.append(ds)
                            else:
                                logger.warning(f"No valid Mollweide tracks for observation '{obs_code}'")
                        except Exception as e:
                            logger.error(f"Error processing observation '{obs_code}': {str(e)}")
                logger.info(f"Calculated Mollweide tracks for {len(datasets)} observations in project '{obj.name}'")
                return xr.concat(datasets, dim="observation") if datasets else xr.Dataset()

            def calculate_mollweide(obj, attrs):
                scans = obj.get_scans().get_active_items()
                if not scans:
                    logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
                    return xr.Dataset()
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": attrs.get("recalculate", False)}
                position_data = self._calculate_telescope_positions(obj, position_attrs)
                if "positions" not in position_data:
                    logger.error(f"Failed to obtain telescope positions for '{obj.get_observation_code()}'")
                    return xr.Dataset()

                scan_names = [scan.name for scan in scans]
                max_telescopes = max(len(scan.get_telescopes(obj).get_active_items()) for scan in scans) if scans else 0
                max_times = max(int(scan.get_duration() / time_step) if time_step else 1 for scan in scans) if scans else 0
                telescope_lon = np.full((len(scans), max_telescopes, max_times), np.nan, dtype=float)
                telescope_lat = np.full((len(scans), max_telescopes, max_times), np.nan, dtype=float)
                source_lon = np.full(len(scans), np.nan, dtype=float)
                source_lat = np.full(len(scans), np.nan, dtype=float)
                telescope_coords = []
                time_coords = []
                source_names = []

                for scan_idx, scan in enumerate(scans):
                    scan_name = scan.name
                    ds = self._process_mollweide_tracks(scan, obj, time_step, position_data)
                    if "telescope_lon" not in ds and "source_lon" not in ds:
                        logger.warning(f"No valid data from _process_mollweide_tracks for scan '{scan_name}'")
                        continue
                    if "telescope_lon" in ds:
                        t_lon = ds["telescope_lon"].values
                        t_lat = ds["telescope_lat"].values
                        tels = ds["telescope"].values
                        times = ds["time"].values
                        pad_tel = max_telescopes - t_lon.shape[0]
                        pad_time = max_times - t_lon.shape[1]
                        if pad_tel > 0 or pad_time > 0:
                            t_lon = np.pad(t_lon, ((0, pad_tel), (0, pad_time)), mode='constant', constant_values=np.nan)
                            t_lat = np.pad(t_lat, ((0, pad_tel), (0, pad_time)), mode='constant', constant_values=np.nan)
                        telescope_lon[scan_idx, :t_lon.shape[0], :t_lon.shape[1]] = t_lon
                        telescope_lat[scan_idx, :t_lat.shape[0], :t_lat.shape[1]] = t_lat
                        telescope_coords.append(tels)
                        time_coords.append(times)
                    if "source_lon" in ds:
                        source_lon[scan_idx] = ds["source_lon"].values[0]
                        source_lat[scan_idx] = ds["source_lat"].values[0]
                        source_names.append(ds["source"].item())
                    else:
                        source_names.append(None)

                if not any(source_names):
                    logger.warning(f"No valid source coordinates computed for observation '{obj.get_observation_code()}'")
                    return xr.Dataset()

                # Handle empty telescope or time coordinates
                all_telescopes = []
                all_times = []
                if telescope_coords and any(len(coords) > 0 for coords in telescope_coords):
                    all_telescopes = np.unique(np.concatenate([coords for coords in telescope_coords if len(coords) > 0]))
                if time_coords and any(len(coords) > 0 for coords in time_coords):
                    all_times = np.unique(np.concatenate([coords for coords in time_coords if len(coords) > 0]))

                dataset = xr.Dataset(
                    data_vars={
                        "telescope_lon": (["scan", "telescope", "time"], telescope_lon),
                        "telescope_lat": (["scan", "telescope", "time"], telescope_lat),
                        "source_lon": (["scan"], source_lon),
                        "source_lat": (["scan"], source_lat)
                    },
                    coords={
                        "scan": scan_names,
                        "telescope": all_telescopes[:max_telescopes] if len(all_telescopes) > 0 else np.array([], dtype=str),
                        "time": all_times[:max_times] if len(all_times) > 0 else np.array([], dtype=str),
                        "source": (["scan"], [name if name is not None else "" for name in source_names])
                    },
                    attrs={"unit": "radians"}
                )
                logger.debug(f"Created Mollweide dataset for observation '{obj.get_observation_code()}' with {len(scan_names)} scans")
                return dataset

            metadata = {
                "time_step": time_step,
                "scan_count": len(obj.get_scans().get_active_items()),
                "observation_code": obj.get_observation_code()
            }
            return self._get_cached_or_calculate(obj, store_key, calculate_mollweide, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate Mollweide tracks for '{obj.get_observation_code() if isinstance(obj, Observation) else obj.name}': {str(e)}")
            return xr.Dataset()

    def _process_mollweide_tracks(self, scan: Scan, observation: Observation, time_step: Optional[float], position_data: xr.Dataset) -> xr.Dataset:
        """Process Mollweide tracks for a single scan.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            time_step (Optional[float]): Sampling interval (seconds).
            position_data (xr.Dataset): Precomputed telescope positions.

        Returns:
            xr.Dataset: Mollweide tracks with dimensions [telescope, time] for telescope tracks and [scan] for source position.
            Returns empty dataset with coordinates if computation fails.
        """
        logger.debug(f"Processing Mollweide tracks for scan {scan.name}")
        start_time = scan.get_start()
        duration = scan.get_duration()
        source = scan.get_source(observation)
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        scan_name = scan.name

        if not source:
            logger.error(f"No source specified for scan {scan_name}")
            return xr.Dataset(coords={"scan": [scan_name], "source": None})

        logger.debug(f"Source: {source.name}, RA={source.ra_degrees}, Dec={source.dec_degrees}")
        try:
            source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
            logger.debug(f"Created SkyCoord: frame={source_coord.frame.name}, ra={source_coord.ra.deg}, dec={source_coord.dec.deg}")
        except Exception as e:
            logger.error(f"Failed to create SkyCoord for scan {scan_name}: {str(e)}")
            return xr.Dataset(coords={"scan": [scan_name], "source": source.name})

        if not np.isfinite(source_coord.ra.deg) or not np.isfinite(source_coord.dec.deg):
            logger.error(f"Invalid source coordinates for scan {scan_name}: RA={source.ra_degrees}, Dec={source.dec_degrees}")
            return xr.Dataset(coords={"scan": [scan_name], "source": source.name})

        # Compute source coordinates in radians
        logger.debug("Computing Mollweide coordinates for source")
        source_lon, source_lat = self._compute_mollweide_coords(source_coord)
        logger.debug(f"Source Mollweide coords: lon={source_lon}, lat={source_lat}")
        if not np.isfinite(source_lon) or not np.isfinite(source_lat):
            logger.warning(f"Non-finite Mollweide coordinates for source in scan {scan_name}: lon={source_lon}, lat={source_lat}")
            source_lon, source_lat = np.nan, np.nan
        source_lon = np.radians(source_lon)
        source_lat = np.radians(source_lat)

        # Initialize dataset for source coordinates
        dataset = xr.Dataset(
            data_vars={
                "source_lon": (["scan"], [source_lon]),
                "source_lat": (["scan"], [source_lat])
            },
            coords={"scan": [scan_name], "source": source.name},
            attrs={"unit": "radians"}
        )

        if not active_telescopes:
            logger.warning(f"No active telescopes for scan {scan_name}")
            return dataset

        # Define time array
        if time_step is None:
            times = Time(start_time + (duration / 2) * u.s)
            times = times.reshape(-1)
        else:
            if time_step > duration:
                logger.error(f"time_step ({time_step}s) exceeds scan duration ({duration}s) for scan {scan_name}; calculation aborted")
                return xr.Dataset(coords={"scan": [scan_name], "source": source.name if source else None})
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')

        # Extract positions for the scan
        scan_positions = position_data.sel(scan=scan_name).get("positions", xr.DataArray())
        if not scan_positions.size:
            logger.error(f"No position data for scan {scan_name}")
            return dataset

        tel_codes = [tel.get_code() for tel in active_telescopes]
        positions = scan_positions.values  # shape: (n_telescopes, n_times, 3)
        logger.debug(f"Positions shape: {positions.shape}, expected times: {len(times)}")
        if positions.shape[1] != len(times):
            logger.error(f"Mismatched position data length for scan {scan_name}: expected {len(times)}, got {positions.shape[1]}")
            return dataset

        # Initialize arrays for telescope coordinates
        telescope_lon = np.full((len(active_telescopes), len(times)), np.nan, dtype=float)
        telescope_lat = np.full((len(active_telescopes), len(times)), np.nan, dtype=float)

        # Check for valid positions
        valid_mask = np.all(np.isfinite(positions), axis=-1)  # shape: (n_telescopes, n_times)
        logger.debug(f"Valid positions mask: {np.sum(valid_mask)} valid points")
        if not np.any(valid_mask):
            logger.warning(f"No valid position data for any telescope in scan {scan_name}")
            return dataset

        # Vectorized computation of Mollweide coordinates
        try:
            with np.errstate(invalid='ignore'):
                x, y, z = positions[:, :, 0], positions[:, :, 1], positions[:, :, 2]
                r = np.sqrt(x**2 + y**2 + z**2)
                # Avoid division by zero
                r = np.where(r == 0, np.nan, r)
                ra_rad = np.arctan2(y, x)
                dec_rad = np.arcsin(np.clip(z / r, -1.0, 1.0))
                lon = np.degrees(ra_rad)
                lon = np.where(lon > 180.0, lon - 360.0, lon)
                lat = np.degrees(dec_rad)
                lat = np.clip(lat, -90.0, 90.0)
                logger.debug(f"Computed telescope Mollweide coords: lon shape={lon.shape}, lat shape={lat.shape}")

                # Apply valid mask and convert to radians
                telescope_lon[valid_mask] = np.radians(lon[valid_mask])
                telescope_lat[valid_mask] = np.radians(lat[valid_mask])

                # Check for NaN or invalid coordinates
                if not np.any(np.isfinite(telescope_lon)) or not np.any(np.isfinite(telescope_lat)):
                    logger.warning(f"No valid Mollweide coordinates computed after vectorization for scan {scan_name}")
                    # Fallback to sequential processing
                    logger.info(f"Falling back to sequential Mollweide computation for scan {scan_name}")
                    for tel_idx, tel in enumerate(active_telescopes):
                        for time_idx, t in enumerate(times):
                            pos = positions[tel_idx, time_idx]
                            if np.all(np.isfinite(pos)):
                                lon, lat = self._compute_mollweide_coords_from_position(pos, t)
                                if np.isfinite(lon) and np.isfinite(lat):
                                    telescope_lon[tel_idx, time_idx] = np.radians(lon)
                                    telescope_lat[tel_idx, time_idx] = np.radians(lat)

                # Log invalid positions
                invalid_tel_times = [(tel_codes[i], times[j].isot) for i, j in np.where(~valid_mask)]
                if invalid_tel_times:
                    logger.debug(f"Invalid positions for {len(invalid_tel_times)} telescope-time pairs in scan {scan_name}")

        except Exception as e:
            logger.error(f"Vectorized Mollweide computation failed for scan {scan_name}: {str(e)}")
            # Fallback to sequential processing
            logger.info(f"Falling back to sequential Mollweide computation for scan {scan_name}")
            for tel_idx, tel in enumerate(active_telescopes):
                for time_idx, t in enumerate(times):
                    pos = positions[tel_idx, time_idx]
                    if np.all(np.isfinite(pos)):
                        lon, lat = self._compute_mollweide_coords_from_position(pos, t)
                        if np.isfinite(lon) and np.isfinite(lat):
                            telescope_lon[tel_idx, time_idx] = np.radians(lon)
                            telescope_lat[tel_idx, time_idx] = np.radians(lat)

        # Check if any valid coordinates were computed
        if not np.any(np.isfinite(telescope_lon)) and not np.any(np.isfinite(telescope_lat)):
            logger.warning(f"No valid Mollweide coordinates computed for telescopes in scan {scan_name}")
            return dataset

        # Update dataset with telescope coordinates
        dataset = dataset.assign({
            "telescope_lon": (["telescope", "time"], telescope_lon),
            "telescope_lat": (["telescope", "time"], telescope_lat)
        })
        dataset = dataset.assign_coords({
            "telescope": tel_codes,
            "time": [t.iso for t in times]
        })

        logger.debug(f"Completed Mollweide tracks for scan {scan_name}: {len(tel_codes)} telescopes, {len(times)} time points")
        return dataset
    
    def _compute_mollweide_coords_from_position(self, position: Tuple[float, float, float], time: Time) -> Tuple[float, float]:
        """Compute Mollweide coordinates from GCRS position in J2000.

        Args:
            position (Tuple[float, float, float]): GCRS position (x, y, z) in meters.
            time (Time): Observation time.

        Returns:
            Tuple[float, float]: RA (in [-180, 180] degrees) and Dec (in [-90, 90] degrees).
            Returns (np.nan, np.nan) if position is invalid.
        """
        logger.debug(f"Computing Mollweide coords from position: {position}")
        try:
            x, y, z = position
            if not all(np.isfinite([x, y, z])):
                logger.warning(f"Invalid position: x={x}, y={y}, z={z}")
                return np.nan, np.nan
            r = np.sqrt(x**2 + y**2 + z**2)
            if not np.isfinite(r) or r == 0:
                logger.warning(f"Invalid radius: r={r}")
                return np.nan, np.nan
            ra_rad = np.arctan2(y, x)
            dec_rad = np.arcsin(np.clip(z / r, -1.0, 1.0))
            ra = np.degrees(ra_rad)
            dec = np.degrees(dec_rad)
            lon = ra if ra <= 180.0 else ra - 360.0
            lat = np.clip(dec, -90.0, 90.0)
            logger.debug(f"Computed coords: lon={lon}, lat={lat}")
            return lon, lat
        except Exception as e:
            logger.error(f"Exception in _compute_mollweide_coords_from_position: {str(e)}")
            return np.nan, np.nan

    def _compute_mollweide_coords(self, coord: SkyCoord) -> Tuple[float, float]:
        """Compute coordinates for Mollweide projection in J2000.

        Args:
            coord (SkyCoord): Source coordinates.

        Returns:
            Tuple[float, float]: RA (in [-180, 180] degrees) and Dec (in [-90, 90] degrees).
            Returns (np.nan, np.nan) if coordinates are invalid.
        """
        logger.debug(f"Entering _compute_mollweide_coords with coord: {coord}")
        try:
            ra = coord.ra.deg  # 0° to 360°
            dec = coord.dec.deg
            logger.debug(f"Extracted RA={ra}, Dec={dec}")
            if not np.isfinite(ra) or not np.isfinite(dec):
                logger.warning(f"Invalid coordinates in SkyCoord: RA={ra}, Dec={dec}")
                return np.nan, np.nan
            lon = ra if ra <= 180.0 else ra - 360.0  # Map RA to [-180, 180]
            lat = np.clip(dec, -90.0, 90.0)  # Ensure Dec is in [-90, 90]
            logger.debug(f"Computed Mollweide coords: lon={lon}, lat={lat}")
            return lon, lat
        except Exception as e:
            logger.error(f"Exception in _compute_mollweide_coords: {str(e)}")
            return np.nan, np.nan

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

    def _interpolate_orbit(self, telescope: SpaceTelescope, start_time: Time, end_time: Time, time_step: float, expected_times: np.ndarray) -> Dict[str, Any]:
        """Interpolate orbit data for a space telescope over a time range using provided time points.

        Args:
            telescope (SpaceTelescope): The space telescope.
            start_time (Time): Start time of interpolation.
            end_time (Time): End time of interpolation.
            time_step (float): Time step for interpolation (seconds).
            expected_times (np.ndarray): Array of expected time points (in seconds since J2000) to interpolate.

        Returns:
            Dict[str, Any]: Interpolated orbit data with times, positions, velocities, and time_range. Returns empty dict if no data.
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
                logger.info(f"Orbit data for '{telescope.get_code()}' partially covers time range: {Time(data_start + j2000_epoch.jd, format='jd').isot} to {Time(data_end + j2000_epoch.jd, format='jd').isot}")
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
            
            # Use provided expected_times for interpolation
            valid_mask = (expected_times >= t_start) & (expected_times <= t_end)
            valid_interp_times = expected_times[valid_mask]
            if not valid_interp_times.size:
                logger.warning(f"No valid interpolation times for '{telescope.get_code()}' within {t_start} to {t_end}")
                return {}
            
            # Initialize arrays for full requested time range
            full_times = expected_times
            full_positions = np.full((len(full_times), 3), np.nan, dtype=float)
            full_velocities = np.full((len(full_times), 3), np.nan, dtype=float)
            
            method = telescope.get("interpolation_method") or "chebyshev"
            if method == "chebyshev":
                degree = min(30, len(filtered_times) - 1)
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
                "time_range": (t_start, t_end)
            }
            
            logger.info(f"Interpolated orbit for '{telescope.get_code()}' using {method} with {len(full_times)} points, expected {len(expected_times)}")
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
    
    def _get_max_workers(self, item_count: int, is_cpu_bound: bool = False) -> int:
        """Determine the optimal number of workers for parallel execution.

        Args:
            item_count (int): Number of items to process (e.g., observations or scans).
            is_cpu_bound (bool): True if the task is CPU-bound, False if I/O-bound.

        Returns:
            int: Number of workers to use in ThreadPoolExecutor.
        """
        cpu_count = multiprocessing.cpu_count()
        if item_count <= 1:
            return 1  # No parallelization for single item
        if is_cpu_bound:
            # For CPU-bound tasks, use number of CPU cores
            return min(item_count, cpu_count)
        else:
            # For I/O-bound tasks, use up to 2x CPU cores for better throughput
            return min(item_count, cpu_count * 2)