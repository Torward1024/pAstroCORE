# unit_scheduling_2/super/schedule_calculator.py
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
    """Decorator to measure and log the execution time of calculation methods."""
    @wraps(func)
    def wrapper(self, obj, attributes):
        start_time = time.perf_counter()
        result = func(self, obj, attributes)
        end_time = time.perf_counter()
        duration = end_time - start_time
        calc_type = func.__name__.replace('_calculate_', '')
        obj_name = obj.name if isinstance(obj, ScheduleProject) else obj.get_observation_code()
        logger.info(f"Calculation '{calc_type}' for '{obj_name}' completed in {duration:.3f} s")
        return result
    return wrapper

class ScheduleCalculator(Super):
    """Scheduler implementation of Calculator for performing astronomical scheduling calculations."""
    def __init__(self, manipulator: 'Manipulator'):
        super().__init__(manipulator)
        self._lock = threading.Lock()
        self._orbit_cache = {}
        self._orbit_cache_lock = threading.Lock()
        logger.info("Initialized Scheduling Calculator")

    def _default_result(self) -> Dict[str, Any]:
        """Return the default result when calculation is not applied."""
        return {"data": None, "metadata": {}}

    def _get_cached_or_calculate(self, obj: Observation | ScheduleProject, store_key: str, calc_func, attributes: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve cached data or perform calculation and cache the result."""
        recalculate = attributes.get("recalculate", False)
        time_step = attributes.get("time_step")

        existing_data = obj.get_calculated_data_by_key(store_key)
        if existing_data and not recalculate and existing_data["metadata"].get("time_step") == time_step:
            if existing_data["data"] is not None:
                logger.info(f"Using cached data for '{store_key}' in '{obj.get_observation_code()}'")
                return {"data": existing_data["data"], "metadata": existing_data["metadata"]}
            else:
                logger.warning(f"Cached data for '{store_key}' in '{obj.get_observation_code()}' is empty, forcing recalculation")

        logger.info(f"Recalculating '{store_key}' for '{obj.get_observation_code()}' with recalculate={recalculate}")
        result = calc_func(obj, attributes)
        with self._lock:
            obj.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": result["data"]})
        return result

    @time_execution
    def _calculate_telescope_positions(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate telescope positions in GCRS (J2000) for all scans or time range."""
        try:
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
                        return {"data": None, "metadata": {}}
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
                    return {"data": results, "metadata": {"time_step": time_step, "scan_count": len(observations)}}

                telescopes = obj.get_telescopes()
                active_telescopes = telescopes.get_active_items()
                if not active_telescopes:
                    logger.warning(f"No active telescopes in observation '{obj.get_observation_code()}'")
                    return {"data": None, "metadata": {}}

                if start_time and end_time:
                    start = Time(start_time)
                    end = Time(end_time)
                    use_scans = False
                else:
                    scans = obj.get_scans().get_active_items()
                    if not scans:
                        logger.warning(f"No scans or time range specified in observation '{obj.get_observation_code()}'")
                        return {"data": None, "metadata": {}}
                    start_times = [scan.get_start() for scan in scans]
                    end_times = [scan.get_start() + scan.get_duration() * u.s for scan in scans]
                    start = min(start_times)
                    end = max(end_times)
                    use_scans = True

                time_values = np.arange(0, (end - start).sec, time_step) * u.s if time_step else [((end - start).sec / 2) * u.s]
                times = Time(start.mjd + time_values.to(u.d).value, format='mjd')
                logger.debug(f"Calculating telescope positions for {len(times)} time points from {start.isot} to {end.isot}")

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

                active_telescopes = [tel for tel in active_telescopes if tel.get_code() not in excluded_telescopes]
                if not active_telescopes:
                    logger.warning(f"All telescopes excluded for observation '{obj.get_observation_code()}'")
                    return {"data": None, "metadata": {}}

                if use_scans and time_step:
                    scan_datasets = []
                    scan_names = []
                    for scan in scans:
                        scan_data = self._process_scan_positions(scan, obj, time_step)
                        if scan_data["data"] is not None:
                            scan_datasets.append(scan_data["data"])
                            scan_names.append(scan.name)
                    if not scan_datasets:
                        return {"data": None, "metadata": {}}
                    dataset = xr.concat(scan_datasets, dim="scan")
                    dataset = dataset.assign_coords({"scan": scan_names})
                else:
                    tel_positions = []
                    tel_codes = [tel.get_code() for tel in active_telescopes]
                    for tel in active_telescopes:
                        positions = []
                        for t in times:
                            try:
                                pos = self._compute_telescope_position(tel, t)
                                positions.append(pos)
                            except ValueError as e:
                                logger.warning(f"Position calculation failed for telescope '{tel.get_code()}' at {t.isot}: {str(e)}")
                                positions.append([np.nan, np.nan, np.nan])
                        tel_positions.append(positions)
                    dataset = xr.Dataset(
                        {"positions": (["telescope", "time", "component"], np.array(tel_positions))},
                        coords={
                            "telescope": tel_codes,
                            "time": times.isot,
                            "component": ["x", "y", "z"]
                        },
                        attrs={"units": {"positions": "meters"}}
                    )

                with self._orbit_cache_lock:
                    self._orbit_cache.clear()
                    logger.info("Cleared orbit cache after telescope position calculations")

                if excluded_telescopes:
                    logger.info(f"Excluded {len(excluded_telescopes)} telescopes: {', '.join(excluded_telescopes)}")
                return {"data": dataset, "metadata": {"time_step": time_step, "start_time": start.isot, "end_time": end.isot}}

            metadata = {"time_step": time_step, "start_time": start_time, "end_time": end_time}
            return self._get_cached_or_calculate(obj, store_key, calculate_positions, attributes, metadata)
        except Exception as e:
            logger.warning(f"Partial failure in calculating telescope positions: {str(e)}")
            return {"data": None, "metadata": {}}
        
    def _compute_telescope_position(self, telescope: Telescope | SpaceTelescope, time: Time) -> np.ndarray:
        """
        Compute the GCRS position of a telescope at a given time.

        Args:
            telescope (Telescope | SpaceTelescope): The telescope object.
            time (Time): The time at which to compute the position.

        Returns:
            np.ndarray: GCRS coordinates [x, y, z] in meters, or [np.nan, np.nan, np.nan] if computation fails.
        """
        try:
            if isinstance(telescope, SpaceTelescope):
                with self._orbit_cache_lock:
                    orbit_data = self._orbit_cache.get(telescope.get_code())
                if orbit_data and time.mjd in orbit_data:
                    pos = orbit_data[time.mjd]
                    return np.array([pos['x'], pos['y'], pos['z']]) * u.m.value
                else:
                    logger.warning(f"No orbit data for telescope '{telescope.get_code()}' at time {time.isot}")
                    return np.array([np.nan, np.nan, np.nan])
            else:
                # Ground-based telescope: use coordinates and velocity
                x, y, z = telescope.get_coordinates()
                vx, vy, vz = telescope.get(["vx", "vy", "vz"]).values()
                dt = (time - Time("2000-01-01T12:00:00")).sec
                itrs_coords = CartesianRepresentation(
                    x + vx * dt,
                    y + vy * dt,
                    z + vz * dt,
                    unit=u.m
                )
                itrs = ITRS(itrs_coords, obstime=time)
                gcrs = itrs.transform_to(GCRS(obstime=time))
                return np.array([gcrs.cartesian.x.value, gcrs.cartesian.y.value, gcrs.cartesian.z.value])
        except Exception as e:
            logger.warning(f"Failed to compute position for telescope '{telescope.get_code()}' at {time.isot}: {str(e)}")
            return np.array([np.nan, np.nan, np.nan])

    def _process_scan_positions(self, scan: Scan, observation: Observation, time_step: Optional[float]) -> Dict[str, Any]:
        """Process telescope positions for a single scan."""
        start_time = scan.get_start()
        duration = scan.get_duration()
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        scan_name = scan.name

        if not active_telescopes:
            logger.warning(f"No active telescopes for scan {scan_name} starting at {start_time.isot}")
            return {"data": None, "metadata": {}}

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            positions = []
            tel_codes = []
            for tel in active_telescopes:
                pos = self._compute_telescope_position(tel, mean_time)
                positions.append(pos)
                tel_codes.append(tel.get_code())
            dataset = xr.Dataset(
                {"positions": (["telescope", "component"], np.array(positions))},
                coords={"telescope": tel_codes, "component": ["x", "y", "z"]},
                attrs={"units": {"positions": "meters"}, "time": mean_time.isot}
            )
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
            tel_positions = []
            tel_codes = []
            for tel in active_telescopes:
                positions = []
                for t in times:
                    pos = self._compute_telescope_position(tel, t)
                    positions.append(pos)
                tel_positions.append(positions)
                tel_codes.append(tel.get_code())
            dataset = xr.Dataset(
                {"positions": (["telescope", "time", "component"], np.array(tel_positions))},
                coords={"telescope": tel_codes, "time": times.isot, "component": ["x", "y", "z"]},
                attrs={"units": {"positions": "meters"}}
            )
        return {"data": dataset, "metadata": {"time_step": time_step}}

    @time_execution
    def _calculate_source_visibility(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate source visibility for all scans."""
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "source_visibility")
            position_store_key = attributes.get("position_store_key", "telescope_positions")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {"data": None, "metadata": {}}
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
                return {"data": results, "metadata": {"time_step": time_step, "scan_count": len(observations)}}

            def calculate_visibility(obj, attrs):
                scans = obj.get_scans().get_active_items()
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": attrs.get("recalculate")}
                position_result = self._calculate_telescope_positions(obj, position_attrs)
                position_data = position_result["data"]
                if position_data is None:
                    logger.error(f"Failed to obtain telescope positions for '{obj.get_observation_code()}'")
                    return {"data": None, "metadata": {}}
                scan_datasets = []
                scan_names = []
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_source_visibility, scan, obj, time_step, position_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result["data"] is not None:
                            scan_datasets.append(scan_result["data"])
                            scan_names.append(scan_name)
                if not scan_datasets:
                    return {"data": None, "metadata": {}}
                dataset = xr.concat(scan_datasets, dim="scan")
                dataset = dataset.assign_coords({"scan": scan_names})
                return {"data": dataset, "metadata": {"time_step": time_step, "scan_count": len(scans)}}

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items())}
            return self._get_cached_or_calculate(obj, store_key, calculate_visibility, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate source visibility: {str(e)}")
            return {"data": None, "metadata": {}}

    def _process_source_visibility(self, scan: Scan, observation: Observation, time_step: Optional[float], position_data: xr.Dataset) -> Dict[str, Any]:
        """Process source visibility for a single scan."""
        start_time = scan.get_start()
        duration = scan.get_duration()
        source = scan.get_source(observation)
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs') if source else None
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        scan_name = scan.name

        logger.debug(f"Processing visibility for scan {scan_name}: {len(active_telescopes)} telescopes")

        if not active_telescopes or not source_coord:
            return {"data": None, "metadata": {}}

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            positions = position_data.sel(scan=scan_name) if "scan" in position_data.dims else position_data
            visibility = self._compute_visibility_at_time(source, active_telescopes, mean_time, positions)
            dataset = xr.Dataset(
                {"visibility": (["telescope"], np.array([visibility[tel.get_code()] for tel in active_telescopes], dtype=bool))},
                coords={"telescope": [tel.get_code() for tel in active_telescopes]},
                attrs={"source": source.name, "time": mean_time.isot, "units": {"visibility": "boolean"}}
            )
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
            positions = position_data.sel(scan=scan_name) if "scan" in position_data.dims else position_data
            visibility = np.zeros((len(active_telescopes), len(times)), dtype=bool)
            for i, tel in enumerate(active_telescopes):
                tel_code = tel.get_code()
                pos_array = positions["positions"].sel(telescope=tel_code).values if tel_code in positions["telescope"] else None
                if pos_array is None or len(pos_array) != len(times):
                    logger.warning(f"No or mismatched position data for telescope '{tel_code}' in scan {scan_name}")
                    visibility[i] = False
                    continue
                if isinstance(tel, SpaceTelescope):
                    visibility[i] = True  # Simplified for now
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
                        logger.debug(f"Unsupported mount type {mount_type.value} for telescope '{tel_code}'")
                        is_visible = np.zeros(len(times), dtype=bool)
                    visibility[i] = is_visible
            dataset = xr.Dataset(
                {"visibility": (["telescope", "time"], visibility)},
                coords={"telescope": [tel.get_code() for tel in active_telescopes], "time": times.isot},
                attrs={"source": source.name, "units": {"visibility": "boolean"}}
            )
        return {"data": dataset, "metadata": {"time_step": time_step}}

    def _compute_visibility_at_time(self, source: Source, telescopes: List[Telescope | SpaceTelescope], time: Time, positions: xr.Dataset) -> Dict[str, bool]:
        """Compute visibility of a source for telescopes at a given time."""
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
        visibility = {}
        for tel in telescopes:
            tel_code = tel.get_code()
            pos = positions["positions"].sel(telescope=tel_code).values if tel_code in positions["telescope"] else None
            if pos is None:
                logger.debug(f"No position data for telescope '{tel_code}' at {time.isot}")
                visibility[tel_code] = False
                continue
            if isinstance(tel, SpaceTelescope):
                visibility[tel_code] = True  # Simplified for now
            else:
                gcrs = GCRS(CartesianRepresentation(*pos, unit=u.m), obstime=time)
                itrs = gcrs.transform_to(ITRS(obstime=time))
                location = itrs.earth_location
                altaz = source_coord.transform_to(AltAz(obstime=time, location=location))
                el = altaz.alt.deg
                az = altaz.az.deg
                mount_type = tel.get("mount_type")
                if mount_type.value == "AZIM":
                    el_range = tel.get_elevation_range()
                    az_range = tel.get_azimuth_range()
                    is_visible = (el_range[0] <= el <= el_range[1]) and (az_range[0] <= az <= az_range[1])
                elif mount_type.value == "EQUA":
                    hadec = source_coord.transform_to(HADec(obstime=time, location=location))
                    ha = hadec.ha.deg
                    dec = hadec.dec.deg
                    ha_range = tel.get_azimuth_range()
                    dec_range = tel.get_elevation_range()
                    is_visible = (dec_range[0] <= dec <= dec_range[1]) and (ha_range[0] <= ha <= ha_range[1])
                else:
                    logger.debug(f"Unsupported mount type {mount_type.value} for telescope '{tel_code}'")
                    is_visible = False
                visibility[tel_code] = is_visible
        return visibility

    @time_execution
    def _calculate_uv_coverage(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate (u,v,w) coverage for all scans in geometric coordinates (meters)."""
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "uv_coverage")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {"data": None, "metadata": {}}
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
                return {"data": results, "metadata": {"time_step": time_step, "scan_count": len(observations)}}

            def calculate_uv(obj, attrs):
                scans = obj.get_scans().get_active_items()
                visibility_attrs = {"time_step": time_step, "store_key": "source_visibility", "recalculate": attrs.get("recalculate", False)}
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": attrs.get("recalculate", False)}
                visibility_result = self._calculate_source_visibility(obj, visibility_attrs)
                position_result = self._calculate_telescope_positions(obj, position_attrs)
                visibility_data = visibility_result["data"]
                position_data = position_result["data"]
                if visibility_data is None or position_data is None:
                    logger.error(f"Missing visibility or position data for '{obj.get_observation_code()}'")
                    return {"data": None, "metadata": {}}
                scan_datasets = []
                scan_names = []
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_uv_coverage, scan, obj, time_step, visibility_data, position_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result["data"] is not None:
                            scan_datasets.append(scan_result["data"])
                            scan_names.append(scan_name)
                if not scan_datasets:
                    return {"data": None, "metadata": {}}
                dataset = xr.concat(scan_datasets, dim="scan")
                dataset = dataset.assign_coords({"scan": scan_names})
                return {"data": dataset, "metadata": {"time_step": time_step, "scan_count": len(scans)}}

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items())}
            return self._get_cached_or_calculate(obj, store_key, calculate_uv, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate (u,v,w) coverage: {str(e)}")
            return {"data": None, "metadata": {}}

    def _process_uv_coverage(self, scan: Scan, observation: Observation, time_step: Optional[float], visibility_data: xr.Dataset, position_data: xr.Dataset) -> Dict[str, Any]:
        """Process UV coverage for a single scan using vectorized computations."""
        start_time = scan.get_start()
        duration = scan.get_duration()
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        source = scan.get_source(observation)
        scan_name = scan.name

        if len(active_telescopes) < 2:
            logger.warning(f"Insufficient telescopes ({len(active_telescopes)}) for UV coverage in scan {scan_name}")
            return {"data": None, "metadata": {}}

        if time_step is None:
            times = Time(start_time + (duration / 2) * u.s).reshape(-1)
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')

        scan_visibility = visibility_data.sel(scan=scan_name) if "scan" in visibility_data.dims else visibility_data
        scan_positions = position_data.sel(scan=scan_name) if "scan" in position_data.dims else position_data
        if not scan_visibility or not scan_positions:
            logger.warning(f"No visibility or position data for scan {scan_name}")
            return {"data": None, "metadata": {}}

        uv_points = self._compute_uv_at_time(active_telescopes, times, source, scan_visibility["visibility"].values, scan_positions["positions"].values)
        pairs = [f"{tel1.get_code()}-{tel2.get_code()}" for i, tel1 in enumerate(active_telescopes) for tel2 in active_telescopes[i+1:]]
        uvw_data = []
        pair_list = []
        time_indices = []
        for time_idx, points in enumerate(uv_points):
            for pair, uuu, vvv, www in points:
                uvw_data.append([uuu, vvv, www])
                pair_list.append(pair)
                time_indices.append(time_idx)
        if not uvw_data:
            return {"data": None, "metadata": {}}
        dataset = xr.Dataset(
            {"uvw": (["pair", "time", "component"], np.array(uvw_data).reshape(-1, len(times), 3))},
            coords={"pair": pair_list, "time": times.isot, "component": ["u", "v", "w"]},
            attrs={"source": source.name if source else None, "units": {"uvw": "meters"}}
        )
        return {"data": dataset, "metadata": {"time_step": time_step}}

    def _compute_uv_at_time(self, telescopes: List[Telescope | SpaceTelescope], times: Time, source: Optional[Source], visibility: np.ndarray, gcrs_positions: np.ndarray) -> List[List[Tuple[str, float, float, float]]]:
        """Compute UVW coordinates for multiple times in geometric coordinates."""
        uv_points = [[] for _ in range(len(times))]
        if not telescopes or len(telescopes) < 2 or source is None:
            logger.warning(f"Insufficient data for UV computation at {times[0].isot}")
            return uv_points

        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
        ra = source_coord.ra.rad
        dec = source_coord.dec.rad

        n_tels = len(telescopes)
        n_times = len(times)
        baselines = np.zeros((n_tels, n_tels, n_times, 3))
        for i in range(n_tels):
            for j in range(i + 1, n_tels):
                baselines[i, j] = gcrs_positions[i] - gcrs_positions[j]
                baselines[j, i] = -baselines[i, j]

        X, Y, Z = baselines[:, :, :, 0], baselines[:, :, :, 1], baselines[:, :, :, 2]
        uu = -np.sin(ra) * X + np.cos(ra) * Y
        vv = -np.cos(ra) * np.sin(dec) * X - np.sin(ra) * np.sin(dec) * Y + np.cos(dec) * Z
        ww = np.cos(ra) * np.cos(dec) * X + np.sin(ra) * np.cos(dec) * Y + np.sin(dec) * Z

        vis_mask = visibility[:, None, :] & visibility[None, :, :]
        uvw = np.stack([uu, vv, ww], axis=-1)
        for time_idx in range(n_times):
            for i in range(n_tels):
                for j in range(i + 1, n_tels):
                    if vis_mask[i, j, time_idx]:
                        pair = f"{telescopes[i].get_code()}-{telescopes[j].get_code()}"
                        uuu, vvv, www = uvw[i, j, time_idx]
                        uv_points[time_idx].append((pair, float(uuu), float(vvv), float(www)))
        return uv_points

    @time_execution
    def _calculate_sun_angles(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate angular separation between source and Sun for all scans."""
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "sun_angles")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {"data": None, "metadata": {}}
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
                return {"data": results, "metadata": {"time_step": time_step, "scan_count": len(observations)}}

            def calculate_sun_angles(obj, attrs):
                scans = obj.get_scans().get_active_items()
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": attrs.get("recalculate", False)}
                position_result = self._calculate_telescope_positions(obj, position_attrs)
                position_data = position_result["data"]
                if position_data is None:
                    logger.error(f"Failed to obtain telescope positions for '{obj.get_observation_code()}'")
                    return {"data": None, "metadata": {}}
                scan_datasets = []
                scan_names = []
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_sun_angles, scan, obj, time_step, position_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result["data"] is not None:
                            scan_datasets.append(scan_result["data"])
                            scan_names.append(scan_name)
                if not scan_datasets:
                    return {"data": None, "metadata": {}}
                dataset = xr.concat(scan_datasets, dim="scan")
                dataset = dataset.assign_coords({"scan": scan_names})
                return {"data": dataset, "metadata": {"time_step": time_step, "scan_count": len(scans)}}

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items())}
            return self._get_cached_or_calculate(obj, store_key, calculate_sun_angles, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate sun angles: {str(e)}")
            return {"data": None, "metadata": {}}

    def _process_sun_angles(self, scan: Scan, observation: Observation, time_step: Optional[float], position_data: xr.Dataset) -> Dict[str, Any]:
        """Process sun angles for a single scan."""
        start_time = scan.get_start()
        duration = scan.get_duration()
        source = scan.get_source(observation)
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs') if source else None
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        scan_name = scan.name

        if not active_telescopes or not source_coord:
            return {"data": None, "metadata": {}}

        if time_step is None:
            times = Time(start_time + (duration / 2) * u.s).reshape(-1)
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')

        ground_tels = [tel for tel in active_telescopes if not isinstance(tel, SpaceTelescope)]
        space_tels = [tel for tel in active_telescopes if isinstance(tel, SpaceTelescope)]
        angles = np.full((len(active_telescopes), len(times)), np.nan, dtype=float)
        scan_positions = position_data.sel(scan=scan_name) if "scan" in position_data.dims else position_data

        if ground_tels:
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
            altaz_frame = AltAz(obstime=times, location=locations)
            source_altaz = source_coord.transform_to(altaz_frame)
            sun_gcrs = get_sun(times)
            sun_altaz = sun_gcrs.transform_to(altaz_frame)
            separations = source_altaz.separation(sun_altaz).deg
            separations = np.where((source_altaz.alt.deg < 0) | (sun_altaz.alt.deg < 0), np.nan, separations)
            for idx, tel_code in enumerate(ground_codes):
                tel_idx = [tel.get_code() for tel in active_telescopes].index(tel_code)
                angles[tel_idx] = separations[idx]

        if space_tels:
            sun_gcrs = get_sun(times)
            sun_pos = np.array([
                sun_gcrs.cartesian.x.to(u.m).value,
                sun_gcrs.cartesian.y.to(u.m).value,
                sun_gcrs.cartesian.z.to(u.m).value
            ]).T
            source_icrs = source_coord.icrs
            source_dir = np.array([
                source_icrs.cartesian.x.value,
                source_icrs.cartesian.y.value,
                source_icrs.cartesian.z.value
            ])
            source_dir /= np.linalg.norm(source_dir)
            for tel in space_tels:
                tel_code = tel.get_code()
                tel_idx = [tel.get_code() for tel in active_telescopes].index(tel_code)
                pos_data = scan_positions["positions"].sel(telescope=tel_code).values if tel_code in scan_positions["telescope"] else None
                if pos_data is None or len(pos_data) != len(times):
                    logger.warning(f"No or mismatched position data for telescope '{tel_code}' in scan {scan_name}")
                    continue
                vec_to_sun = sun_pos - pos_data
                vec_to_sun /= np.linalg.norm(vec_to_sun, axis=1)[:, None]
                cos_angles = np.clip(np.dot(vec_to_sun, source_dir), -1.0, 1.0)
                tel_angles = np.degrees(np.arccos(cos_angles))
                angles[tel_idx] = tel_angles

        dataset = xr.Dataset(
            {"angles": (["telescope", "time"], angles)},
            coords={"telescope": [tel.get_code() for tel in active_telescopes], "time": times.isot},
            attrs={"source": source.name if source else None, "units": {"angles": "degrees"}}
        )
        return {"data": dataset, "metadata": {"time_step": time_step}}

    @time_execution
    def _calculate_az_el(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Az/El or HA/Dec for ground telescopes across all scans."""
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "az_el")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {"data": None, "metadata": {}}
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
                logger.info(f"Calculated Az/El for {len(observations)} observations in project '{obj.name}'")
                return {"data": results, "metadata": {"time_step": time_step, "scan_count": len(observations)}}

            def calculate_az_el(obj, attrs):
                scans = obj.get_scans().get_active_items()
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": attrs.get("recalculate", False)}
                position_result = self._calculate_telescope_positions(obj, position_attrs)
                position_data = position_result["data"]
                if position_data is None:
                    logger.error(f"Failed to obtain telescope positions for '{obj.get_observation_code()}'")
                    return {"data": None, "metadata": {}}
                scan_datasets = []
                scan_names = []
                max_workers = min(len(scans), 4) if len(scans) > 1 else 1
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_az_el, scan, obj, time_step, position_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result["data"] is not None:
                            scan_datasets.append(scan_result["data"])
                            scan_names.append(scan_name)
                if not scan_datasets:
                    return {"data": None, "metadata": {}}
                dataset = xr.concat(scan_datasets, dim="scan")
                dataset = dataset.assign_coords({"scan": scan_names})
                return {"data": dataset, "metadata": {"time_step": time_step, "scan_count": len(scans)}}

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items())}
            return self._get_cached_or_calculate(obj, store_key, calculate_az_el, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate Az/El: {str(e)}")
            return {"data": None, "metadata": {}}

    def _process_az_el(self, scan: Scan, observation: Observation, time_step: Optional[float], position_data: xr.Dataset) -> Dict[str, Any]:
        """Process Az/El or HA/Dec for a single scan."""
        start_time = scan.get_start()
        duration = scan.get_duration()
        source = scan.get_source(observation)
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs') if source else None
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive and not isinstance(t, SpaceTelescope)]
        scan_name = scan.name

        if not active_telescopes or not source_coord:
            return {"data": None, "metadata": {}}

        if time_step is None:
            times = Time(start_time + (duration / 2) * u.s).reshape(-1)
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')

        tel_codes = [tel.get_code() for tel in active_telescopes]
        mount_types = [tel.get("mount_type").value for tel in active_telescopes]
        az_ranges = [tel.get_azimuth_range() for tel in active_telescopes]
        el_ranges = [tel.get_elevation_range() for tel in active_telescopes]
        scan_positions = position_data.sel(scan=scan_name) if "scan" in position_data.dims else position_data
        coords1 = np.full((len(active_telescopes), len(times)), np.nan, dtype=float)
        coords2 = np.full((len(active_telescopes), len(times)), np.nan, dtype=float)

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

        azim_mask = np.array([mount == "AZIM" for mount in mount_types])
        if azim_mask.any():
            azim_indices = np.where(azim_mask)[0]
            azim_location = locations[azim_indices]
            altaz_frame = AltAz(obstime=times, location=azim_location)
            source_altaz = source_coord.transform_to(altaz_frame)
            az = source_altaz.az.deg
            el = source_altaz.alt.deg
            for idx in azim_indices:
                az_min, az_max = az_ranges[idx]
                el_min, el_max = el_ranges[idx]
                valid = (az_min <= az) & (az <= az_max) & (el_min <= el) & (el <= el_max)
                coords1[idx] = np.where(valid, az, np.nan)
                coords2[idx] = np.where(valid, el, np.nan)

        equa_mask = np.array([mount == "EQUA" for mount in mount_types])
        if equa_mask.any():
            equa_indices = np.where(equa_mask)[0]
            equa_location = locations[equa_indices]
            hadec_frame = HADec(obstime=times, location=equa_location)
            source_hadec = source_coord.transform_to(hadec_frame)
            ha = source_hadec.ha.deg
            dec = source_hadec.dec.deg
            for idx in equa_indices:
                ha_min, ha_max = az_ranges[idx]
                dec_min, dec_max = el_ranges[idx]
                valid = (ha_min <= ha) & (ha <= ha_max) & (dec_min <= dec) & (dec <= dec_max)
                coords1[idx] = np.where(valid, ha, np.nan)
                coords2[idx] = np.where(valid, dec, np.nan)

        for tel, code in zip(active_telescopes, tel_codes):
            if mount_types[tel_codes.index(code)] not in ["AZIM", "EQUA"]:
                logger.warning(f"Unsupported mount type {tel.get('mount_type')} for telescope '{code}'")
                coords1[tel_codes.index(code)] = 0.0
                coords2[tel_codes.index(code)] = 0.0

        dataset = xr.Dataset(
            {
                "coord1": (["telescope", "time"], coords1, {"description": "Azimuth (AZIM) or Hour Angle (EQUA)", "units": "degrees"}),
                "coord2": (["telescope", "time"], coords2, {"description": "Elevation (AZIM) or Declination (EQUA)", "units": "degrees"})
            },
            coords={"telescope": tel_codes, "time": times.isot},
            attrs={"source": source.name if source else None}
        )
        return {"data": dataset, "metadata": {"time_step": time_step}}

    @time_execution
    def _calculate_time_on_source(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate total time on source for all scans."""
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "time_on_source")
            visibility_store_key = "source_visibility"

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {"data": None, "metadata": {}}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_time_on_source(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"Calculated time on source for {len(observations)} observations in project '{obj.name}'")
                return {"data": results, "metadata": {"time_step": time_step, "scan_count": len(observations)}}

            def calculate_time_on_source(obj, attrs):
                scans = obj.get_scans().get_active_items()
                visibility_result = self._calculate_source_visibility(obj, {
                    "time_step": time_step,
                    "store_key": visibility_store_key,
                    "recalculate": attrs.get("recalculate", False)
                })
                visibility_data = visibility_result["data"]
                if visibility_data is None:
                    logger.error(f"Failed to obtain visibility data for '{obj.get_observation_code()}'")
                    return {"data": None, "metadata": {}}
                results = {}
                source_names = []
                telescope_codes = []
                durations = []
                with ThreadPoolExecutor() as executor:
                    futures = {
                        executor.submit(self._process_time_on_source, scan, obj, time_step, visibility_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result["data"] is not None:
                            source_name = scan_result["data"].attrs["source"]
                            for tel_code in scan_result["data"]["telescope"].values:
                                duration = scan_result["data"]["duration"].sel(telescope=tel_code).values
                                if not np.isnan(duration):
                                    source_names.append(source_name)
                                    telescope_codes.append(tel_code)
                                    durations.append(duration)
                if not durations:
                    return {"data": None, "metadata": {}}
                dataset = xr.Dataset(
                    {"duration": (["source", "telescope"], np.array(durations).reshape(-1, len(set(telescope_codes))))},
                    coords={"source": list(set(source_names)), "telescope": list(set(telescope_codes))},
                    attrs={"units": {"duration": "seconds"}}
                )
                return {"data": dataset, "metadata": {"time_step": time_step, "scan_count": len(scans)}}

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items())}
            return self._get_cached_or_calculate(obj, store_key, calculate_time_on_source, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate time on source: {str(e)}")
            return {"data": None, "metadata": {}}

    def _process_time_on_source(self, scan: Scan, observation: Observation, time_step: float, visibility_data: xr.Dataset) -> Dict[str, Any]:
        """Process time on source for a single scan."""
        start_time = scan.get_start()
        duration = scan.get_duration()
        source = scan.get_source(observation)
        scan_name = scan.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]

        time_values = np.arange(0, duration, time_step) * u.s
        times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
        scan_data = visibility_data.sel(scan=scan_name) if "scan" in visibility_data.dims else visibility_data
        visibility = scan_data["visibility"].values if scan_data else None
        if visibility is None:
            logger.warning(f"No visibility data for scan {scan_name} in observation '{observation.get_observation_code()}'")
            return {"data": None, "metadata": {}}

        durations = []
        tel_codes = [tel.get_code() for tel in active_telescopes]
        for tel_idx, tel in enumerate(active_telescopes):
            vis = visibility[tel_idx]
            blocks = []
            start_block = None
            for t_idx, is_visible in enumerate(vis):
                current_time = times[t_idx]
                if is_visible and start_block is None:
                    start_block = current_time
                elif not is_visible and start_block is not None:
                    end_block = times[t_idx - 1]
                    blocks.append((end_block - start_block).sec)
                    start_block = None
                if t_idx == len(vis) - 1 and start_block is not None:
                    end_block = current_time
                    blocks.append((end_block - start_block).sec)
            durations.append(sum(blocks))
        dataset = xr.Dataset(
            {"duration": (["telescope"], durations)},
            coords={"telescope": tel_codes},
            attrs={"source": source.name if source else None, "units": {"duration": "seconds"}}
        )
        return {"data": dataset, "metadata": {"time_step": time_step}}

    @time_execution
    def _calculate_beam_pattern(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate beam pattern for single-dish observations."""
        try:
            freq_name = attributes.get("freq_name")
            store_key = attributes.get("store_key", f"beam_pattern_{freq_name}")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {"data": None, "metadata": {}}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_beam_pattern(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"Calculated beam pattern for {len(observations)} observations in project '{obj.name}'")
                return {"data": results, "metadata": {"freq_name": freq_name, "scan_count": len(observations)}}

            if obj.get_observation_type() != "SINGLE_DISH":
                logger.warning(f"Beam pattern calculation is only for SINGLE_DISH, got {obj.get_observation_type()}")
                return {"data": None, "metadata": {}}

            def calculate_beam_pattern(obj, attrs):
                telescopes = obj.get_telescopes().get_active_items()
                frequency = obj.get_frequencies().get(freq_name).get("frequency") * 1e6
                c = 299792458
                wavelength = c / frequency
                theta = np.linspace(-np.pi/2, np.pi/2, 5000)
                patterns = []
                tel_codes = []
                for tel in telescopes:
                    if isinstance(tel, SpaceTelescope):
                        continue
                    D = tel.get("diameter")
                    x = (np.pi * D / wavelength) * np.sin(theta)
                    pattern = (2 * j1(x) / x) ** 2
                    pattern = np.where(np.isnan(pattern), 1.0, pattern)
                    patterns.append(pattern)
                    tel_codes.append(tel.get_code())
                dataset = xr.Dataset(
                    {"pattern": (["telescope", "theta"], np.array(patterns))},
                    coords={"telescope": tel_codes, "theta": np.degrees(theta)},
                    attrs={"units": {"pattern": "normalized", "theta": "degrees"}, "frequency": frequency}
                )
                return {"data": dataset, "metadata": {"freq_name": freq_name}}

            metadata = {"freq_name": freq_name}
            return self._get_cached_or_calculate(obj, store_key, calculate_beam_pattern, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate beam pattern: {str(e)}")
            return {"data": None, "metadata": {}}

    @time_execution
    def _calculate_synthesized_beam(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate synthesized beam for VLBI observations."""
        try:
            freq_name = attributes.get("freq_name")
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", f"synthesized_beam_{freq_name}")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {"data": None, "metadata": {}}
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
                return {"data": results, "metadata": {"freq_name": freq_name, "time_step": time_step, "scan_count": len(observations)}}

            if obj.get_observation_type() != "VLBI":
                logger.warning(f"Synthesized beam calculation is only for VLBI, got {obj.get_observation_type()}")
                return {"data": None, "metadata": {}}

            def calculate_synthesized_beam(obj, attrs):
                frequency = obj.get_frequencies().get(freq_name).get("frequency") * 1e6
                if frequency is None:
                    logger.error(f"No frequency found for freq_name '{freq_name}' in observation '{obj.get_observation_code()}'")
                    return {"data": None, "metadata": {}}
                uv_store_key = "uv_coverage"
                uv_result = self._calculate_uv_coverage(obj, {
                    "time_step": attrs.get("time_step"),
                    "store_key": uv_store_key,
                    "recalculate": attrs.get("recalculate", False)
                })
                uv_data = uv_result["data"]
                if uv_data is None:
                    logger.warning(f"No UV data available for '{obj.get_observation_code()}'")
                    return {"data": None, "metadata": {}}
                scans = obj.get_scans().get_active_items()
                scan_datasets = []
                scan_names = []
                for scan in scans:
                    scan_name = scan.name
                    scan_uv_data = uv_data.sel(scan=scan_name) if "scan" in uv_data.dims else uv_data
                    if not scan_uv_data or "uvw" not in scan_uv_data:
                        logger.warning(f"No UV points for scan '{scan_name}' in observation '{obj.get_observation_code()}'")
                        continue
                    u = scan_uv_data["uvw"].sel(component="u").values.flatten()
                    v = scan_uv_data["uvw"].sel(component="v").values.flatten()
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
                    grid_size = 512
                    u_grid = np.linspace(-u_max, u_max, grid_size)
                    v_grid = np.linspace(-v_max, v_max, grid_size)
                    uv_plane = np.zeros((grid_size, grid_size), dtype=complex)
                    for uu, vv in zip(u, v):
                        u_idx = int((uu + u_max) / (2 * u_max) * (grid_size - 1))
                        v_idx = int((vv + v_max) / (2 * v_max) * (grid_size - 1))
                        if 0 <= u_idx < grid_size and 0 <= v_idx < grid_size:
                            uv_plane[v_idx, u_idx] += 1.0
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
                    dataset = xr.Dataset(
                        {"beam_2d": (["theta_u", "theta_v"], beam_2d)},
                        coords={"theta_u": theta_u_deg, "theta_v": theta_v_deg},
                        attrs={"units": {"beam_2d": "normalized", "theta_u": "degrees", "theta_v": "degrees"}, "frequency": frequency}
                    )
                    scan_datasets.append(dataset)
                    scan_names.append(scan_name)
                if not scan_datasets:
                    return {"data": None, "metadata": {}}
                dataset = xr.concat(scan_datasets, dim="scan")
                dataset = dataset.assign_coords({"scan": scan_names})
                return {"data": dataset, "metadata": {"freq_name": freq_name, "time_step": time_step}}

            metadata = {"freq_name": freq_name, "time_step": time_step}
            return self._get_cached_or_calculate(obj, store_key, calculate_synthesized_beam, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate synthesized beam: {str(e)}")
            return {"data": None, "metadata": {}}

    @time_execution
    def _calculate_baseline_projections(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate baseline projections for VLBI observations in geometric coordinates."""
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "baseline_projections")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {"data": None, "metadata": {}}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_baseline_projections(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"Calculated baseline projections for {len(observations)} observations in project '{obj.name}'")
                return {"data": results, "metadata": {"time_step": time_step, "scan_count": len(observations)}}

            if obj.get_observation_type() != "VLBI":
                logger.warning(f"Baseline projections are only for VLBI, got {obj.get_observation_type()}")
                return {"data": None, "metadata": {}}

            def calculate_baseline_projections(obj, attrs):
                scans = obj.get_scans().get_active_items()
                telescopes = obj.get_telescopes()
                active_telescopes = telescopes.get_active_items()
                if len(active_telescopes) < 2:
                    logger.error(f"VLBI requires at least 2 active telescopes, got {len(active_telescopes)}")
                    return {"data": None, "metadata": {}}
                uv_store_key = "uv_coverage"
                uv_result = self._calculate_uv_coverage(obj, {
                    "time_step": time_step,
                    "store_key": uv_store_key,
                    "recalculate": attrs.get("recalculate", False)
                })
                uv_data = uv_result["data"]
                if uv_data is None:
                    logger.error(f"Failed to obtain UV coverage data for '{obj.get_observation_code()}'")
                    return {"data": None, "metadata": {}}
                scan_datasets = []
                scan_names = []
                with ThreadPoolExecutor() as executor:
                    futures = {
                        executor.submit(self._process_baseline_projections, scan, obj, time_step, uv_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result["data"] is not None:
                            scan_datasets.append(scan_result["data"])
                            scan_names.append(scan_name)
                if not scan_datasets:
                    return {"data": None, "metadata": {}}
                dataset = xr.concat(scan_datasets, dim="scan")
                dataset = dataset.assign_coords({"scan": scan_names})
                return {"data": dataset, "metadata": {"time_step": time_step, "scan_count": len(scans)}}

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items())}
            return self._get_cached_or_calculate(obj, store_key, calculate_baseline_projections, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate baseline projections: {str(e)}")
            return {"data": None, "metadata": {}}

    def _process_baseline_projections(self, scan: Scan, observation: Observation, time_step: Optional[float], uv_data: xr.Dataset) -> Dict[str, Any]:
        """Process baseline projections for a single scan."""
        start_time = scan.get_start()
        duration = scan.get_duration()
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        scan_name = scan.name

        if time_step is None:
            times = Time(start_time + (duration / 2) * u.s).reshape(-1)
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')

        scan_uv_data = uv_data.sel(scan=scan_name) if "scan" in uv_data.dims else uv_data
        if not scan_uv_data or "uvw" not in scan_uv_data:
            logger.error(f"No UV data available for scan {scan_name} at {start_time.isot}")
            return {"data": None, "metadata": {}}

        u = scan_uv_data["uvw"].sel(component="u").values
        v = scan_uv_data["uvw"].sel(component="v").values
        projections = np.sqrt(u**2 + v**2)
        dataset = xr.Dataset(
            {"projections": (["pair", "time"], projections)},
            coords={"pair": scan_uv_data["pair"].values, "time": times.isot},
            attrs={"units": {"projections": "meters"}}
        )
        return {"data": dataset, "metadata": {"time_step": time_step}}

    @time_execution
    def _calculate_mollweide_tracks(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Mollweide projection tracks for telescopes and source."""
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "mollweide_tracks")

            if isinstance(obj, ScheduleProject):
                observations = obj.get_items()
                if not observations:
                    logger.warning(f"No observations in project '{obj.name}'")
                    return {"data": None, "metadata": {}}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_mollweide_tracks(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"Calculated Mollweide tracks for {len(observations)} observations in project '{obj.name}'")
                return {"data": results, "metadata": {"time_step": time_step, "scan_count": len(observations)}}

            def calculate_mollweide_tracks(obj, attrs):
                scans = obj.get_scans().get_active_items()
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": attrs.get("recalculate", False)}
                position_result = self._calculate_telescope_positions(obj, position_attrs)
                position_data = position_result["data"]
                if position_data is None:
                    return {"data": None, "metadata": {}}
                scan_datasets = []
                scan_names = []
                with ThreadPoolExecutor() as executor:
                    futures = {
                        executor.submit(self._process_mollweide_tracks, scan, obj, time_step, position_data): scan.name
                        for scan in scans
                    }
                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result["data"] is not None:
                            scan_datasets.append(scan_result["data"])
                            scan_names.append(scan_name)
                if not scan_datasets:
                    return {"data": None, "metadata": {}}
                dataset = xr.concat(scan_datasets, dim="scan")
                dataset = dataset.assign_coords({"scan": scan_names})
                return {"data": dataset, "metadata": {"time_step": time_step, "scan_count": len(scans)}}

            metadata = {"time_step": time_step, "scan_count": len(obj.get_scans().get_active_items())}
            return self._get_cached_or_calculate(obj, store_key, calculate_mollweide_tracks, attributes, metadata)
        except Exception as e:
            logger.error(f"Failed to calculate Mollweide tracks: {str(e)}")
            return {"data": None, "metadata": {}}

    def _process_mollweide_tracks(self, scan: Scan, observation: Observation, time_step: Optional[float], position_data: xr.Dataset) -> Dict[str, Any]:
        """Process Mollweide projection tracks for a single scan."""
        start_time = scan.get_start()
        duration = scan.get_duration()
        source = scan.get_source(observation)
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        scan_name = scan.name
        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs') if source else None
        source_lon, source_lat = self._compute_mollweide_coords(source_coord) if source_coord else (np.nan, np.nan)

        if not position_data or ("scan" in position_data.dims and scan_name not in position_data["scan"]):
            logger.error(f"No position data for scan {scan_name}")
            return {"data": None, "metadata": {}}

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            scan_positions = position_data.sel(scan=scan_name) if "scan" in position_data.dims else position_data
            lon = []
            lat = []
            tel_codes = []
            for tel in active_telescopes:
                pos = scan_positions["positions"].sel(telescope=tel.get_code()).values
                if pos is not None and not np.any(np.isnan(pos)):
                    l, t = self._compute_mollweide_coords_from_position(pos, mean_time)
                    lon.append(l)
                    lat.append(t)
                    tel_codes.append(tel.get_code())
            dataset = xr.Dataset(
                {
                    "lon": (["telescope"], lon),
                    "lat": (["telescope"], lat),
                    "source_lon": ([], source_lon),
                    "source_lat": ([], source_lat)
                },
                coords={"telescope": tel_codes},
                attrs={"source": source.name if source else None, "time": mean_time.isot, "units": {"lon": "degrees", "lat": "degrees"}}
            )
        else:
            time_values = np.arange(0, duration, time_step) * u.s
            times = Time(start_time.mjd + time_values.to(u.d).value, format='mjd')
            scan_positions = position_data.sel(scan=scan_name) if "scan" in position_data.dims else position_data
            lon = []
            lat = []
            tel_codes = []
            for tel in active_telescopes:
                pos_data = scan_positions["positions"].sel(telescope=tel.get_code()).values
                if pos_data is None or np.any(np.isnan(pos_data)):
                    logger.warning(f"No valid position data for telescope '{tel.get_code()}' in scan {scan_name}")
                    continue
                tel_lon = []
                tel_lat = []
                for t_idx, t in enumerate(times):
                    pos = pos_data[t_idx]
                    if not np.any(np.isnan(pos)):
                        l, t_lat = self._compute_mollweide_coords_from_position(pos, t)
                        tel_lon.append(l)
                        tel_lat.append(t_lat)
                    else:
                        tel_lon.append(np.nan)
                        tel_lat.append(np.nan)
                if tel_lon:
                    lon.append(tel_lon)
                    lat.append(tel_lat)
                    tel_codes.append(tel.get_code())
            if not tel_codes:
                logger.warning(f"No valid Mollweide tracks for scan {scan_name}")
                return {"data": None, "metadata": {}}
            dataset = xr.Dataset(
                {
                    "lon": (["telescope", "time"], lon),
                    "lat": (["telescope", "time"], lat),
                    "source_lon": ([], source_lon),
                    "source_lat": ([], source_lat)
                },
                coords={"telescope": tel_codes, "time": times.isot},
                attrs={"source": source.name if source else None, "units": {"lon": "degrees", "lat": "degrees"}}
            )
        return {"data": dataset, "metadata": {"time_step": time_step}}
    
    def _compute_mollweide_coords_from_position(self, position: np.ndarray, time: Time) -> Tuple[float, float]:
        """Compute Mollweide projection coordinates from telescope position at a given time."""
        try:
            gcrs = GCRS(CartesianRepresentation(position, unit=u.m), obstime=time)
            itrs = gcrs.transform_to(ITRS(obstime=time))
            lon = itrs.earth_location.geodetic.lon.deg
            lat = itrs.earth_location.geodetic.lat.deg
            # Normalize longitude to [-180, 180]
            lon = ((lon + 180) % 360) - 180
            return float(lon), float(lat)
        except Exception as e:
            logger.warning(f"Failed to compute Mollweide coordinates: {str(e)}")
            return np.nan, np.nan

    def _compute_mollweide_coords(self, coord: SkyCoord) -> Tuple[float, float]:
        """Compute Mollweide projection coordinates for a SkyCoord object."""
        try:
            lon = coord.ra.deg
            lat = coord.dec.deg
            # Normalize longitude to [-180, 180]
            lon = ((lon + 180) % 360) - 180
            return float(lon), float(lat)
        except Exception as e:
            logger.warning(f"Failed to compute Mollweide coordinates for source: {str(e)}")
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