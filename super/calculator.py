# super/calculator.py
from abc import ABC
from base.frequencies import Frequencies
from base.sources import Sources, Source
from base.telescopes import Telescope, SpaceTelescope, Telescopes, MountType
from base.scans import Scan, Scans
from base.observation import Observation
from base.project import Project
from utils.logging_setup import logger
from typing import Dict, Any, Optional, Tuple, List
from functools import lru_cache
import numpy as np
from astropy.time import Time
from astropy.coordinates import ITRS, GCRS, CartesianRepresentation, SkyCoord, AltAz, get_sun, EarthLocation, HADec
import astropy.units as u
from concurrent.futures import ThreadPoolExecutor
import threading
from scipy.special import j1

class Calculator(ABC):
    """Super-class for performing calculations on Project and its components

    Attributes:
        _calculation_methods (dict): Cached dictionary mapping object types to calculation functions
        _lock (threading.Lock): Thread-safe lock for calculated data updates
    """
    def __init__(self):
        """Initialize the Calculator"""
        self._lock = threading.Lock()
        logger.info("Initialized Calculator")

    def _calculate_telescope_positions(self, observation: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate telescope positions in J2000 for all scans in the observation"""
        try:
            time_step = attributes.get("time_step")  # None для среднего значения
            store_key = attributes.get("store_key", "telescope_positions")
            recalculate = attributes.get("recalculate", False)
            telescopes = observation.get_telescopes()
            scans = observation.get_scans().get_active_scans(observation)

            if not scans:
                logger.warning(f"No active scans in observation '{observation.get_observation_code()}'")
                return {}

            existing_data = observation.get_calculated_data_by_key(store_key)
            if existing_data and not recalculate and existing_data["metadata"]["time_step"] == time_step:
                logger.info(f"Using cached telescope positions for '{observation.get_observation_code()}'")
                return existing_data["data"]

            results = {}
            with ThreadPoolExecutor() as executor:
                futures = {
                    executor.submit(self._process_scan_positions, scan, telescopes, time_step): i
                    for i, scan in enumerate(scans)
                }
                for future in futures:
                    scan_idx = futures[future]
                    try:
                        results[scan_idx] = future.result()
                    except Exception as e:
                        logger.error(f"Failed to process scan {scan_idx}: {str(e)}")

            metadata = {"time_step": time_step, "scan_count": len(scans), "telescope_count": len(telescopes.get_active_telescopes())}
            with self._lock:
                observation.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": results})
            logger.info(f"Calculated telescope positions for {len(scans)} scans in '{observation.get_observation_code()}'")
            return results
        except Exception as e:
            logger.error(f"Failed to calculate telescope positions: {str(e)}")
            return {}

    def _process_scan_positions(self, scan: Scan, telescopes: Telescopes, time_step: Optional[float]) -> Dict[str, Any]:
        """Process telescope positions for a single scan"""
        start_time = scan.get_start_datetime()
        duration = scan.get_duration()
        end_time = Time(start_time) + duration * u.s
        telescope_indices = scan.get_telescope_indices()
        active_telescopes = [telescopes.get_telescope(i) for i in telescope_indices if telescopes.get_telescope(i).isactive]

        if not active_telescopes:
            logger.warning(f"No active telescopes for scan starting at {start_time}")
            return {"telescope_positions": {}}

        if time_step is None:
            mean_time = Time(start_time) + (duration / 2) * u.s
            positions = self._compute_positions_at_time(active_telescopes, mean_time)
            return {"telescope_positions": {tel.get_code(): pos for tel, pos in positions.items()}}
        else:
            times = np.arange(0, duration, time_step) * u.s + Time(start_time)
            result = {}
            for tel in active_telescopes:
                tel_positions = [self._compute_telescope_position(tel, t) for t in times]
                result[tel.get_code()] = {"times": [t.isot for t in times], "positions": tel_positions}
            return {"telescope_positions": result}

    def _compute_telescope_position(self, telescope: Telescope | SpaceTelescope, time: Time) -> Tuple[float, float, float]:
        """Compute the J2000 position of a telescope at a given time"""
        if isinstance(telescope, Telescope) and not isinstance(telescope, SpaceTelescope):
            x, y, z = telescope.get_coordinates()
            vx, vy, vz = telescope.get_velocities()
            dt = (time - Time("2000-01-01T12:00:00")).sec
            itrs_coords = CartesianRepresentation(x + vx * dt, y + vy * dt, z + vz * dt, unit=u.m)
            itrs = ITRS(itrs_coords, obstime=time)
            gcrs = itrs.transform_to(GCRS(obstime=time))
            return (gcrs.x.value, gcrs.y.value, gcrs.z.value)
        elif isinstance(telescope, SpaceTelescope):
            pos, _ = telescope.get_state_vector(time.to_datetime())
            return tuple(float(p) for p in pos)
        raise ValueError(f"Unsupported telescope type: {type(telescope)}")

    def _calculate_source_visibility(self, observation: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate source visibility for all scans"""
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "source_visibility")
            recalculate = attributes.get("recalculate", False)
            scans = observation.get_scans().get_active_scans(observation)
            telescopes = observation.get_telescopes()
            sources = observation.get_sources()

            existing_data = observation.get_calculated_data_by_key(store_key)
            if existing_data and not recalculate and existing_data["metadata"]["time_step"] == time_step:
                logger.info(f"Using cached source visibility for '{observation.get_observation_code()}'")
                return existing_data["data"]

            results = {}
            with ThreadPoolExecutor() as executor:
                futures = {
                    executor.submit(self._process_source_visibility, scan, telescopes, sources, time_step): i
                    for i, scan in enumerate(scans)
                }
                for future in futures:
                    scan_idx = futures[future]
                    results[scan_idx] = future.result()

            metadata = {"time_step": time_step, "scan_count": len(scans)}
            with self._lock:
                observation.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": results})
            logger.info(f"Calculated source visibility for {len(scans)} scans in '{observation.get_observation_code()}'")
            return results
        except Exception as e:
            logger.error(f"Failed to calculate source visibility: {str(e)}")
            return {}

    def _process_source_visibility(self, scan: Scan, telescopes: Telescopes, sources: Sources, time_step: Optional[float]) -> Dict[str, Any]:
        """Process source visibility for a single scan"""
        start_time = Time(scan.get_start_datetime())
        duration = scan.get_duration()
        source_idx = scan.get_source_index()
        source = sources.get_source(source_idx)
        telescope_indices = scan.get_telescope_indices()
        active_telescopes = [telescopes.get_telescope(i) for i in telescope_indices if telescopes.get_telescope(i).isactive]

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            visibility = self._compute_visibility_at_time(source, active_telescopes, mean_time)
            return {"source": source.get_name(), "visibility": visibility}
        else:
            times = np.arange(0, duration, time_step) * u.s + start_time
            visibility = {tel.get_code(): [] for tel in active_telescopes}
            for t in times:
                vis = self._compute_visibility_at_time(source, active_telescopes, t)
                for tel_code, is_visible in vis.items():
                    visibility[tel_code].append(is_visible)
            return {"source": source.get_name(), "times": [t.isot for t in times], "visibility": visibility}

    def _compute_visibility_at_time(self, source: Source, telescopes: List[Telescope | SpaceTelescope], time: Time) -> Dict[str, bool]:
        """Compute visibility of a source for telescopes at a given time, considering mount type"""
        source_coord = SkyCoord(ra=source.get_ra_degrees() * u.deg, dec=source.get_dec_degrees() * u.deg, frame='icrs')
        visibility = {}
        for tel in telescopes:
            if isinstance(tel, SpaceTelescope):
                # Space Telescope -- simple orientation
                pos, _ = tel.get_state_vector(time.to_datetime())
                itrs = ITRS(CartesianRepresentation(*pos, unit=u.m), obstime=time)
                altaz = source_coord.transform_to(AltAz(obstime=time, location=itrs.earth_location))
                pitch = altaz.alt.deg  
                yaw = altaz.az.deg     
                pitch_range = tel.get_pitch_range()
                yaw_range = tel.get_yaw_range()
                is_visible = (pitch_range[0] <= pitch <= pitch_range[1]) and (yaw_range[0] <= yaw <= yaw_range[1])
            else:  # ground telescopes
                pos = self._compute_telescope_position(tel, time)
                itrs = ITRS(CartesianRepresentation(*pos, unit=u.m), obstime=time)
                mount_type = tel.get_mount_type()
                location = itrs.earth_location
                
                if mount_type == MountType.AZIMUTHAL:
                    altaz = source_coord.transform_to(AltAz(obstime=time, location=location))
                    el = altaz.alt.deg
                    az = altaz.az.deg
                    el_range = tel.get_elevation_range()
                    az_range = tel.get_azimuth_range()
                    is_visible = (el_range[0] <= el <= el_range[1]) and (az_range[0] <= az <= az_range[1])
                elif mount_type == MountType.EQUATORIAL:
                    
                    hadec = source_coord.transform_to(HADec(obstime=time, location=location))
                    ha = hadec.ha.deg
                    dec = hadec.dec.deg

                    dec_range = tel.get_elevation_range()  
                    ha_range = tel.get_azimuth_range()
                    
                    ha_min = ha_range[0] - 180 if ha_range[0] >= 0 else ha_range[0]
                    ha_max = ha_range[1] - 180 if ha_range[1] > 180 else ha_range[1]
                    is_visible = (dec_range[0] <= dec <= dec_range[1]) and (ha_min <= ha <= ha_max)
                else:
                    logger.warning(f"Unsupported mount type {mount_type} for telescope '{tel.get_code()}'")
                    is_visible = False
            
            visibility[tel.get_code()] = is_visible
        return visibility

    def _process_uv_coverage(self, scan: Scan, telescopes: Telescopes, frequencies: Frequencies, time_step: Optional[float], freq_idx: Optional[int]) -> Dict[str, Any]:
        """Process (u,v) coverage for a single scan"""
        start_time = Time(scan.get_start_datetime())
        duration = scan.get_duration()
        telescope_indices = scan.get_telescope_indices()
        active_telescopes = [telescopes.get_telescope(i) for i in telescope_indices if telescopes.get_telescope(i).isactive]
        freq_indices = scan.get_frequency_indices() if freq_idx is None else [freq_idx]
        freqs = [frequencies.get_IF(i).get_frequency() * 1e6 for i in freq_indices if frequencies.get_IF(i).isactive]  # MHz -> Hz

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            uv = self._compute_uv_at_time(active_telescopes, mean_time, freqs)
            return {"uv_points": uv}
        else:
            times = np.arange(0, duration, time_step) * u.s + start_time
            uv_points = {f: [] for f in freqs}
            for t in times:
                uv = self._compute_uv_at_time(active_telescopes, t, freqs)
                for f, points in uv.items():
                    uv_points[f].extend(points)
            return {"times": [t.isot for t in times], "uv_points": uv_points}

    def _compute_uv_at_time(self, telescopes: List[Telescope | SpaceTelescope], time: Time, frequencies: List[float]) -> Dict[float, List[Tuple[float, float]]]:
        """Compute (u,v) points at a given time for given frequencies"""
        positions = [self._compute_telescope_position(tel, time) for tel in telescopes]
        uv_points = {f: [] for f in frequencies}
        c = 299792458  # m/s
        for i, pos1 in enumerate(positions):
            for j, pos2 in enumerate(positions[i + 1:], i + 1):
                baseline = np.array(pos1) - np.array(pos2)  # meters
                for freq in frequencies:
                    wavelength = c / freq
                    u, v = baseline[0] / wavelength, baseline[1] / wavelength  # dimensionless
                    uv_points[freq].append((u, v))
        return uv_points

    def _calculate_sun_angles(self, observation: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate angles between source and Sun for all scans"""
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "sun_angles")
            recalculate = attributes.get("recalculate", False)
            scans = observation.get_scans().get_active_scans(observation)
            sources = observation.get_sources()

            existing_data = observation.get_calculated_data_by_key(store_key)
            if existing_data and not recalculate and existing_data["metadata"]["time_step"] == time_step:
                logger.info(f"Using cached Sun angles for '{observation.get_observation_code()}'")
                return existing_data["data"]

            results = {}
            with ThreadPoolExecutor() as executor:
                futures = {
                    executor.submit(self._process_sun_angles, scan, sources, time_step): i
                    for i, scan in enumerate(scans)
                }
                for future in futures:
                    scan_idx = futures[future]
                    results[scan_idx] = future.result()

            metadata = {"time_step": time_step, "scan_count": len(scans)}
            with self._lock:
                observation.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": results})
            logger.info(f"Calculated Sun angles for {len(scans)} scans in '{observation.get_observation_code()}'")
            return results
        except Exception as e:
            logger.error(f"Failed to calculate Sun angles: {str(e)}")
            return {}

    def _process_sun_angles(self, scan: Scan, sources: Sources, time_step: Optional[float]) -> Dict[str, Any]:
        """Process Sun angles for a single scan"""
        start_time = Time(scan.get_start_datetime())
        duration = scan.get_duration()
        source = sources.get_source(scan.get_source_index())
        source_coord = SkyCoord(ra=source.get_ra_degrees() * u.deg, dec=source.get_dec_degrees() * u.deg, frame='icrs')

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            angle = self._compute_sun_angle(source_coord, mean_time)
            return {"source": source.get_name(), "sun_angle": angle}
        else:
            times = np.arange(0, duration, time_step) * u.s + start_time
            angles = [self._compute_sun_angle(source_coord, t) for t in times]
            return {"source": source.get_name(), "times": [t.isot for t in times], "sun_angles": angles}

    def _compute_sun_angle(self, source_coord: SkyCoord, time: Time) -> float:
        """Compute angle between source and Sun at a given time"""
        sun = get_sun(time)
        return source_coord.separation(sun).deg

    def _calculate_az_el(self, observation: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate azimuth/elevation or hour angle/declination for ground telescopes"""
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "az_el")
            recalculate = attributes.get("recalculate", False)
            scans = observation.get_scans().get_active_scans(observation)
            telescopes = observation.get_telescopes()
            sources = observation.get_sources()

            existing_data = observation.get_calculated_data_by_key(store_key)
            if existing_data and not recalculate and existing_data["metadata"]["time_step"] == time_step:
                logger.info(f"Using cached Az/El or HA/Dec for '{observation.get_observation_code()}'")
                return existing_data["data"]

            results = {}
            with ThreadPoolExecutor() as executor:
                futures = {
                    executor.submit(self._process_az_el, scan, telescopes, sources, time_step): i
                    for i, scan in enumerate(scans)
                }
                for future in futures:
                    scan_idx = futures[future]
                    results[scan_idx] = future.result()

            metadata = {"time_step": time_step, "scan_count": len(scans)}
            with self._lock:
                observation.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": results})
            logger.info(f"Calculated Az/El or HA/Dec for {len(scans)} scans in '{observation.get_observation_code()}'")
            return results
        except Exception as e:
            logger.error(f"Failed to calculate Az/El or HA/Dec: {str(e)}")
            return {}

    def _process_az_el(self, scan: Scan, telescopes: Telescopes, sources: Sources, time_step: Optional[float]) -> Dict[str, Any]:
        """Process Az/El or HA/Dec for a single scan"""
        start_time = Time(scan.get_start_datetime())
        duration = scan.get_duration()
        source = sources.get_source(scan.get_source_index())
        source_coord = SkyCoord(ra=source.get_ra_degrees() * u.deg, dec=source.get_dec_degrees() * u.deg, frame='icrs')
        telescope_indices = scan.get_telescope_indices()
        active_ground_tels = [tel for tel in (telescopes.get_telescope(i) for i in telescope_indices) 
                             if tel.isactive and not isinstance(tel, SpaceTelescope)]

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            az_el = self._compute_az_el_at_time(source_coord, active_ground_tels, mean_time)
            return {"source": source.get_name(), "az_el": az_el}
        else:
            times = np.arange(0, duration, time_step) * u.s + start_time
            az_el = {tel.get_code(): {"coord1": [], "coord2": []} for tel in active_ground_tels}  # coord1: Az/HA, coord2: El/Dec
            for t in times:
                result = self._compute_az_el_at_time(source_coord, active_ground_tels, t)
                for tel_code, (coord1, coord2) in result.items():
                    az_el[tel_code]["coord1"].append(coord1)
                    az_el[tel_code]["coord2"].append(coord2)
            # metadata for coordinates type
            for tel in active_ground_tels:
                mount_type = tel.get_mount_type()
                az_el[tel.get_code()]["coord_type"] = "AzEl" if mount_type == MountType.AZIMUTHAL else "HADec"
            return {"source": source.get_name(), "times": [t.isot for t in times], "az_el": az_el}

    def _compute_az_el_at_time(self, source_coord: SkyCoord, telescopes: List[Telescope], time: Time) -> Dict[str, Tuple[float, float]]:
        """Compute Az/El or HA/Dec for ground telescopes at a given time, depending on mount type"""
        az_el = {}
        for tel in telescopes:
            pos = self._compute_telescope_position(tel, time)
            itrs = ITRS(CartesianRepresentation(*pos, unit=u.m), obstime=time)
            mount_type = tel.get_mount_type()
            location = itrs.earth_location

            if mount_type == MountType.AZIMUTHAL:
                # AZIM mount
                altaz = source_coord.transform_to(AltAz(obstime=time, location=location))
                az_el[tel.get_code()] = (altaz.az.deg, altaz.alt.deg)
            elif mount_type == MountType.EQUATORIAL:
                # EQUA mount
                hadec = source_coord.transform_to(HADec(obstime=time, location=location))
                ha = hadec.ha.deg
                dec = hadec.dec.deg
                az_el[tel.get_code()] = (ha, dec)
            else:
                logger.warning(f"Unsupported mount type {mount_type} for telescope '{tel.get_code()}' in Az/El calculation")
                az_el[tel.get_code()] = (0.0, 0.0)  # Заглушка для неподдерживаемых типов

        return az_el

    def _calculate_time_on_source(self, observation: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate time on source for all scans"""
        try:
            store_key = attributes.get("store_key", "time_on_source")
            recalculate = attributes.get("recalculate", False)
            scans = observation.get_scans().get_active_scans(observation)
            sources = observation.get_sources()

            existing_data = observation.get_calculated_data_by_key(store_key)
            if existing_data and not recalculate:
                logger.info(f"Using cached time on source for '{observation.get_observation_code()}'")
                return existing_data["data"]

            time_on_source = {}
            for i, scan in enumerate(scans):
                source_name = sources.get_source(scan.get_source_index()).get_name()
                duration = scan.get_duration()
                time_on_source.setdefault(source_name, []).append({"scan_idx": i, "duration": duration})

            results = {source: {"total_time": sum(s["duration"] for s in scans), "scans": scans} 
                      for source, scans in time_on_source.items()}
            metadata = {"scan_count": len(scans)}
            with self._lock:
                observation.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": results})
            logger.info(f"Calculated time on source for {len(scans)} scans in '{observation.get_observation_code()}'")
            return results
        except Exception as e:
            logger.error(f"Failed to calculate time on source: {str(e)}")
            return {}

    def _calculate_beam_pattern(self, observation: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Gaussian beam pattern for SINGLE_DISH observation"""
        if observation.get_observation_type() != "SINGLE_DISH":
            logger.warning(f"Beam pattern calculation is only for SINGLE_DISH, got {observation.get_observation_type()}")
            return {}
        try:
            freq_idx = attributes.get("freq_idx", 0)
            store_key = attributes.get("store_key", f"beam_pattern_f{freq_idx}")
            recalculate = attributes.get("recalculate", False)
            telescopes = observation.get_telescopes().get_active_telescopes()
            frequency = observation.get_frequencies().get_IF(freq_idx).get_frequency() * 1e6  # MHz -> Hz

            existing_data = observation.get_calculated_data_by_key(store_key)
            if existing_data and not recalculate:
                logger.info(f"Using cached beam pattern for '{observation.get_observation_code()}'")
                return existing_data["data"]

            results = {}
            c = 299792458  # m/s
            wavelength = c / frequency
            for tel in telescopes:
                if isinstance(tel, SpaceTelescope):
                    continue
                D = tel.get_diameter()
                theta = np.linspace(-np.pi/2, np.pi/2, 1000)  # radians
                x = (np.pi * D / wavelength) * np.sin(theta)
                pattern = (2 * j1(x) / x) ** 2  # Gaussian approximation
                pattern[np.isnan(pattern)] = 1.0  # Center fix
                results[tel.get_code()] = {"theta": theta.tolist(), "pattern": pattern.tolist()}

            metadata = {"freq_idx": freq_idx}
            with self._lock:
                observation.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": results})
            logger.info(f"Calculated beam pattern for '{observation.get_observation_code()}' at {frequency/1e6} MHz")
            return results
        except Exception as e:
            logger.error(f"Failed to calculate beam pattern: {str(e)}")
            return {}

    def _calculate_synthesized_beam(self, observation: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate synthesized beam for VLBI observation"""
        if observation.get_observation_type() != "VLBI":
            logger.warning(f"Synthesized beam calculation is only for VLBI, got {observation.get_observation_type()}")
            return {}
        try:
            freq_idx = attributes.get("freq_idx", 0)
            store_key = attributes.get("store_key", f"synthesized_beam_f{freq_idx}")
            recalculate = attributes.get("recalculate", False)
            frequency = observation.get_frequencies().get_IF(freq_idx).get_frequency() * 1e6  # MHz -> Hz

            existing_data = observation.get_calculated_data_by_key(store_key)
            if existing_data and not recalculate:
                logger.info(f"Using cached synthesized beam for '{observation.get_observation_code()}'")
                return existing_data["data"]

            uv_data = self._calculate_uv_coverage(observation, {"time_step": attributes.get("time_step"), "freq_idx": freq_idx})
            results = {}
            c = 299792458  # m/s
            wavelength = c / frequency
            for scan_idx, scan_data in uv_data.items():
                uv_points = scan_data["uv_points"][frequency] if "times" in scan_data else scan_data["uv_points"]
                u, v = zip(*uv_points)
                max_baseline = np.max(np.sqrt(np.array(u)**2 + np.array(v)**2)) * wavelength
                theta_fwhm = 1.22 * wavelength / max_baseline  # radians
                theta = np.linspace(-theta_fwhm*2, theta_fwhm*2, 1000)
                pattern = np.exp(-4 * np.log(2) * (theta / theta_fwhm) ** 2)  # Gaussian
                results[scan_idx] = {"theta": theta.tolist(), "pattern": pattern.tolist()}

            metadata = {"freq_idx": freq_idx}
            with self._lock:
                observation.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": results})
            logger.info(f"Calculated synthesized beam for '{observation.get_observation_code()}' at {frequency/1e6} MHz")
            return results
        except Exception as e:
            logger.error(f"Failed to calculate synthesized beam: {str(e)}")
            return {}

    @lru_cache(maxsize=1)
    def _get_calculation_methods(self) -> Dict[type, Dict[str, Any]]:
        """Retrieve and cache the mapping of object types to calculation functions"""
        return {
            Observation: {
                "calc_func": {
                    "telescope_positions": self._calculate_telescope_positions,
                    "source_visibility": self._calculate_source_visibility,
                    "uv_coverage": self._calculate_uv_coverage,
                    "sun_angles": self._calculate_sun_angles,
                    "az_el": self._calculate_az_el,
                    "time_on_source": self._calculate_time_on_source,
                    "beam_pattern": self._calculate_beam_pattern,
                    "synthesized_beam": self._calculate_synthesized_beam
                }
            }
        }

    def calculate(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Universal method to perform calculations on an object

        Args:
            obj: The object to calculate (e.g., Observation)
            attributes: Dictionary with calculation parameters (e.g., {"type": "telescope_positions", "time_step": 10.0})

        Returns:
            Dict[str, Any]: Results of the calculation
        """
        if obj is None:
            logger.error("Calculation object cannot be None")
            raise ValueError("Calculation object cannot be None")

        calc_methods = self._get_calculation_methods()
        obj_type = type(obj)
        calc_type = attributes.get("type", "telescope_positions")

        if obj_type not in calc_methods or calc_type not in calc_methods[obj_type]["calc_func"]:
            logger.error(f"Unsupported object type {obj_type} or calculation type {calc_type}")
            raise ValueError(f"Unsupported calculation for {obj_type}: {calc_type}")

        try:
            return calc_methods[obj_type]["calc_func"][calc_type](obj, attributes)
        except Exception as e:
            logger.error(f"Failed to calculate {calc_type} for {obj_type}: {str(e)}")
            return {}

    def __repr__(self) -> str:
        return "Calculator()"

class DefaultCalculator(Calculator):
    """Default implementation of Calculator"""
    def __init__(self):
        super().__init__()
        logger.info("Initialized DefaultCalculator")