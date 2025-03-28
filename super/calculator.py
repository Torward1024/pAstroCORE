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
import astropy.coordinates as coord
import astropy.units as u
from concurrent.futures import ThreadPoolExecutor
import threading
from scipy.special import j1


class Calculator(ABC):
    """Super-class for performing calculations on Project or Observation objects"""
    def __init__(self, manipulator: 'Manipulator'):
        """Initialize the Calculator"""
        self._manipulator = manipulator
        self._lock = threading.Lock()
        logger.info("Initialized Calculator")

    def _calculate_telescope_positions(self, obj: Observation | Project, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate telescope positions in J2000 for all scans in the observation or project"""
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "telescope_positions")
            recalculate = attributes.get("recalculate", False)

            if isinstance(obj, Project):
                observations = obj.get_observations()
                if not observations:
                    logger.warning(f"No observations in project '{obj.get_name()}'")
                    return {}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_telescope_positions(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"Calculated telescope positions for {len(observations)} observations in project '{obj.get_name()}'")
                return results

            telescopes = obj.get_telescopes()
            scans = obj.get_scans().get_active_scans(obj)

            if not scans:
                logger.warning(f"No active scans in observation '{obj.get_observation_code()}'")
                return {}

            existing_data = obj.get_calculated_data_by_key(store_key)
            if existing_data and not recalculate and existing_data["metadata"]["time_step"] == time_step:
                logger.info(f"Using cached telescope positions for '{obj.get_observation_code()}'")
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
                obj.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": results})
            logger.info(f"Calculated telescope positions for {len(scans)} scans in '{obj.get_observation_code()}'")
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
        active_telescopes = [telescopes.get_by_index(i) for i in telescope_indices if telescopes.get_by_index(i).isactive]

        if not active_telescopes:
            logger.warning(f"No active telescopes for scan starting at {start_time}")
            return {"telescope_positions": {}}

        if time_step is None:
            mean_time = Time(start_time) + (duration / 2) * u.s
            positions = {tel.get_code(): self._compute_telescope_position(tel, mean_time) for tel in active_telescopes}
            return {"telescope_positions": positions}
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
            return (gcrs.cartesian.x.value, gcrs.cartesian.y.value, gcrs.cartesian.z.value)
        elif isinstance(telescope, SpaceTelescope):
            pos, _ = telescope.get_state_vector(time.to_datetime())
            return tuple(float(p) for p in pos)
        raise ValueError(f"Unsupported telescope type: {type(telescope)}")

    def _calculate_source_visibility(self, obj: Observation | Project, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate source visibility for all scans in the observation or project"""
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "source_visibility")
            recalculate = attributes.get("recalculate", False)

            if isinstance(obj, Project):
                observations = obj.get_observations()
                if not observations:
                    logger.warning(f"No observations in project '{obj.get_name()}'")
                    return {}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_source_visibility(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"Calculated source visibility for {len(observations)} observations in project '{obj.get_name()}'")
                return results

            scans = obj.get_scans().get_active_scans(obj)
            telescopes = obj.get_telescopes()
            sources = obj.get_sources()

            existing_data = obj.get_calculated_data_by_key(store_key)
            if existing_data and not recalculate and existing_data["metadata"]["time_step"] == time_step:
                logger.info(f"Using cached source visibility for '{obj.get_observation_code()}'")
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
                obj.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": results})
            logger.info(f"Calculated source visibility for {len(scans)} scans in '{obj.get_observation_code()}'")
            return results
        except Exception as e:
            logger.error(f"Failed to calculate source visibility: {str(e)}")
            return {}

    def _process_source_visibility(self, scan: Scan, telescopes: Telescopes, sources: Sources, time_step: Optional[float]) -> Dict[str, Any]:
        """Process source visibility for a single scan"""
        start_time = Time(scan.get_start_datetime())
        duration = scan.get_duration()
        source_idx = scan.get_source_index()
        source = sources.get_by_index(source_idx)
        telescope_indices = scan.get_telescope_indices()
        active_telescopes = [telescopes.get_by_index(i) for i in telescope_indices if telescopes.get_by_index(i).isactive]

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
    
    def _calculate_uv_coverage(self, obj: Observation | Project, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate (u,v) coverage for all scans in the observation or project"""
        try:
            time_step = attributes.get("time_step")
            freq_idx = attributes.get("freq_idx", 0)
            store_key = attributes.get("store_key", f"uv_coverage_f{freq_idx}")
            recalculate = attributes.get("recalculate", False)

            if isinstance(obj, Project):
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

            scans = obj.get_scans().get_active_scans(obj)
            telescopes = obj.get_telescopes()
            frequencies = obj.get_frequencies()

            existing_data = obj.get_calculated_data_by_key(store_key)
            if existing_data and not recalculate and existing_data["metadata"]["time_step"] == time_step:
                logger.info(f"Using cached (u,v) coverage for '{obj.get_observation_code()}'")
                return existing_data["data"]

            results = {}
            with ThreadPoolExecutor() as executor:
                futures = {
                    executor.submit(self._process_uv_coverage, scan, telescopes, frequencies, time_step, freq_idx): i
                    for i, scan in enumerate(scans)
                }
                for future in futures:
                    scan_idx = futures[future]
                    results[scan_idx] = future.result()

            metadata = {"time_step": time_step, "freq_idx": freq_idx, "scan_count": len(scans)}
            with self._lock:
                obj.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": results})
            logger.info(f"Calculated (u,v) coverage for {len(scans)} scans in '{obj.get_observation_code()}'")
            return results
        except Exception as e:
            logger.error(f"Failed to calculate (u,v) coverage: {str(e)}")
            return {}

    def _process_uv_coverage(self, scan: Scan, telescopes: Telescopes, frequencies: Frequencies, time_step: Optional[float], freq_idx: Optional[int]) -> Dict[str, Any]:
        """Process (u,v) coverage for a single scan"""
        start_time = Time(scan.get_start_datetime())
        duration = scan.get_duration()
        telescope_indices = scan.get_telescope_indices()
        active_telescopes = [telescopes.get_by_index(i) for i in telescope_indices if telescopes.get_by_index(i).isactive]
        freq_indices = scan.get_frequency_indices() if freq_idx is None else [freq_idx]
        freqs = [frequencies.get_by_index(i).get_frequency() * 1e6 for i in freq_indices if frequencies.get_by_index(i).isactive]  # MHz -> Hz

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
        """Compute (u,v) points at a given time for given frequencies, relative to Earth's center"""
        positions = [self._compute_telescope_position(tel, time) for tel in telescopes]
        itrs_center = ITRS(CartesianRepresentation(0, 0, 0, unit=u.m), obstime=time)
        gcrs_center = itrs_center.transform_to(GCRS(obstime=time))
        center_pos = np.array([gcrs_center.cartesian.x.value, gcrs_center.cartesian.y.value, gcrs_center.cartesian.z.value])

        uv_points = {f: [] for f in frequencies}
        c = 299792458  # m/s
        for i, pos1 in enumerate(positions):
            for j, pos2 in enumerate(positions[i + 1:], i + 1):
                baseline = (np.array(pos1) - center_pos) - (np.array(pos2) - center_pos)  # meters
                for freq in frequencies:
                    wavelength = c / freq
                    uu, vv = baseline[0] / wavelength, baseline[1] / wavelength  # in wavelength numbers
                    uv_points[freq].append((uu, vv))
        return uv_points

    def _calculate_sun_angles(self, obj: Observation | Project, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate angles between source and Sun for all scans in the observation or project"""
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "sun_angles")
            recalculate = attributes.get("recalculate", False)

            if isinstance(obj, Project):
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

            scans = obj.get_scans().get_active_scans(obj)
            sources = obj.get_sources()

            existing_data = obj.get_calculated_data_by_key(store_key)
            if existing_data and not recalculate and existing_data["metadata"]["time_step"] == time_step:
                logger.info(f"Using cached Sun angles for '{obj.get_observation_code()}'")
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
                obj.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": results})
            logger.info(f"Calculated Sun angles for {len(scans)} scans in '{obj.get_observation_code()}'")
            return results
        except Exception as e:
            logger.error(f"Failed to calculate Sun angles: {str(e)}")
            return {}

    def _process_sun_angles(self, scan: Scan, sources: Sources, time_step: Optional[float]) -> Dict[str, Any]:
        """Process Sun angles for a single scan"""
        start_time = Time(scan.get_start_datetime())
        duration = scan.get_duration()
        source = sources.get_by_index(scan.get_source_index())
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

    def _calculate_az_el(self, obj: Observation | Project, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate azimuth/elevation or hour angle/declination for ground telescopes in the observation or project"""
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "az_el")
            recalculate = attributes.get("recalculate", False)

            if isinstance(obj, Project):
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

            scans = obj.get_scans().get_active_scans(obj)
            telescopes = obj.get_telescopes()
            sources = obj.get_sources()

            existing_data = obj.get_calculated_data_by_key(store_key)
            if existing_data and not recalculate and existing_data["metadata"]["time_step"] == time_step:
                logger.info(f"Using cached Az/El or HA/Dec for '{obj.get_observation_code()}'")
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
                obj.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": results})
            logger.info(f"Calculated Az/El or HA/Dec for {len(scans)} scans in '{obj.get_observation_code()}'")
            return results
        except Exception as e:
            logger.error(f"Failed to calculate Az/El or HA/Dec: {str(e)}")
            return {}

    def _process_az_el(self, scan: Scan, telescopes: Telescopes, sources: Sources, time_step: Optional[float]) -> Dict[str, Any]:
        """Process Az/El or HA/Dec for a single scan"""
        start_time = Time(scan.get_start_datetime())
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

    def _calculate_time_on_source(self, obj: Observation | Project, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate time on source for all scans in the observation or project"""
        try:
            store_key = attributes.get("store_key", "time_on_source")
            recalculate = attributes.get("recalculate", False)

            if isinstance(obj, Project):
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

            scans = obj.get_scans().get_active_scans(obj)
            sources = obj.get_sources()

            existing_data = obj.get_calculated_data_by_key(store_key)
            if existing_data and not recalculate:
                logger.info(f"Using cached time on source for '{obj.get_observation_code()}'")
                return existing_data["data"]

            time_on_source = {}
            for i, scan in enumerate(scans):
                source_name = sources.get_by_index(scan.get_source_index()).get_name()
                duration = scan.get_duration()
                time_on_source.setdefault(source_name, []).append({"scan_idx": i, "duration": duration})

            results = {source: {"total_time": sum(s["duration"] for s in scans), "scans": scans} 
                      for source, scans in time_on_source.items()}
            metadata = {"scan_count": len(scans)}
            with self._lock:
                obj.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": results})
            logger.info(f"Calculated time on source for {len(scans)} scans in '{obj.get_observation_code()}'")
            return results
        except Exception as e:
            logger.error(f"Failed to calculate time on source: {str(e)}")
            return {}

    def _calculate_beam_pattern(self, obj: Observation | Project, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Gaussian beam pattern for SINGLE_DISH observation or project"""
        try:
            freq_idx = attributes.get("freq_idx", 0)
            store_key = attributes.get("store_key", f"beam_pattern_f{freq_idx}")
            recalculate = attributes.get("recalculate", False)

            if isinstance(obj, Project):
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

            telescopes = obj.get_telescopes().get_active_telescopes()
            frequency = obj.get_frequencies().get_by_index(freq_idx).get_frequency() * 1e6  # MHz -> Hz

            existing_data = obj.get_calculated_data_by_key(store_key)
            if existing_data and not recalculate:
                logger.info(f"Using cached beam pattern for '{obj.get_observation_code()}'")
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
                obj.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": results})
            logger.info(f"Calculated beam pattern for '{obj.get_observation_code()}' at {frequency/1e6} MHz")
            return results
        except Exception as e:
            logger.error(f"Failed to calculate beam pattern: {str(e)}")
            return {}

    def _calculate_synthesized_beam(self, obj: Observation | Project, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate synthesized beam for VLBI observation or project"""
        try:
            freq_idx = attributes.get("freq_idx", 0)
            store_key = attributes.get("store_key", f"synthesized_beam_f{freq_idx}")
            recalculate = attributes.get("recalculate", False)

            if isinstance(obj, Project):
                observations = obj.get_observations()
                if not observations:
                    logger.warning(f"No observations in project '{obj.get_name()}'")
                    return {}
                results = {}
                for obs in observations:
                    obs_result = self._calculate_synthesized_beam(obs, attributes)
                    results[obs.get_observation_code()] = obs_result
                logger.info(f"Calculated synthesized beam for {len(observations)} observations in project '{obj.get_name()}'")
                return results

            if obj.get_observation_type() != "VLBI":
                logger.warning(f"Synthesized beam calculation is only for VLBI, got {obj.get_observation_type()}")
                return {}

            frequency = obj.get_frequencies().get_by_index(freq_idx).get_frequency() * 1e6  # MHz -> Hz

            existing_data = obj.get_calculated_data_by_key(store_key)
            if existing_data and not recalculate:
                logger.info(f"Using cached synthesized beam for '{obj.get_observation_code()}'")
                return existing_data["data"]

            uv_data = self._calculate_uv_coverage(obj, {"time_step": attributes.get("time_step"), "freq_idx": freq_idx})
            if not uv_data:
                logger.error(f"No UV data available for synthesized beam calculation in '{obj.get_observation_code()}'")
                return {}

            results = {}
            c = 299792458  # m/s
            wavelength = c / frequency
            for scan_idx, scan_data in uv_data.items():
                if "times" in scan_data:
                    uv_points = scan_data["uv_points"].get(frequency, [])
                else:
                    uv_points = scan_data["uv_points"].get(frequency, [])
                
                if not uv_points or not isinstance(uv_points, (list, tuple)):
                    logger.warning(f"No valid UV points for scan {scan_idx} at frequency {frequency/1e6} MHz")
                    continue

                u, v = zip(*uv_points)
                max_baseline = np.max(np.sqrt(np.array(u)**2 + np.array(v)**2)) * wavelength
                theta_fwhm = 1.22 * wavelength / max_baseline  # radians
                theta = np.linspace(-theta_fwhm*2, theta_fwhm*2, 1000)
                pattern = np.exp(-4 * np.log(2) * (theta / theta_fwhm) ** 2)  # Gaussian
                results[scan_idx] = {"theta": theta.tolist(), "pattern": pattern.tolist()}

            metadata = {"freq_idx": freq_idx}
            with self._lock:
                obj.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": results})
            logger.info(f"Calculated synthesized beam for '{obj.get_observation_code()}' at {frequency/1e6} MHz")
            return results
        except Exception as e:
            logger.error(f"Failed to calculate synthesized beam: {str(e)}")
            return {}
        
    def _calculate_baseline_projections(self, obj: Observation | Project, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate baseline projections for VLBI observation or project, reusing (u,v) if available"""
        try:
            time_step = attributes.get("time_step")
            freq_idx = attributes.get("freq_idx", 0)
            store_key = attributes.get("store_key", f"baseline_projections_f{freq_idx}")
            recalculate = attributes.get("recalculate", False)

            if isinstance(obj, Project):
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

            scans = obj.get_scans().get_active_scans(obj)
            telescopes = obj.get_telescopes()
            frequencies = obj.get_frequencies()

            active_telescopes = telescopes.get_active_telescopes()
            if len(active_telescopes) < 2:
                logger.error(f"VLBI requires at least 2 active telescopes, got {len(active_telescopes)}")
                return {}

            existing_data = obj.get_calculated_data_by_key(store_key)
            if existing_data and not recalculate:
                logger.info(f"Using cached baseline projections for '{obj.get_observation_code()}'")
                return existing_data["data"]

            uv_store_key = attributes.get("uv_store_key", f"uv_coverage_f{freq_idx}")
            uv_data = obj.get_calculated_data_by_key(uv_store_key)
            if uv_data and not recalculate and uv_data["metadata"]["time_step"] == time_step:
                logger.info(f"Reusing existing (u,v) data for baseline projections in '{obj.get_observation_code()}'")
            else:
                uv_data = self._calculate_uv_coverage(obj, {"time_step": time_step, "freq_idx": freq_idx, "store_key": uv_store_key})
                if not uv_data:
                    logger.error(f"Failed to calculate (u,v) coverage for baseline projections")
                    return {}

            results = {}
            with ThreadPoolExecutor() as executor:
                futures = {
                    executor.submit(self._process_baseline_projections, scan, telescopes, frequencies, time_step, freq_idx, uv_data.get(i, {}), obj): i
                    for i, scan in enumerate(scans)
                }
                for future in futures:
                    scan_idx = futures[future]
                    try:
                        results[scan_idx] = future.result()
                    except Exception as e:
                        logger.error(f"Failed to process scan {scan_idx} in baseline projections: {str(e)}")
                        results[scan_idx] = {}

            metadata = {"time_step": time_step, "freq_idx": freq_idx, "scan_count": len(scans)}
            with self._lock:
                obj.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": results})
            logger.info(f"Calculated baseline projections for {len(scans)} scans in '{obj.get_observation_code()}'")
            return results
        except Exception as e:
            logger.error(f"Failed to calculate baseline projections: {str(e)}")
            return {}

    def _process_baseline_projections(self, scan: Scan, telescopes: Telescopes, frequencies: Frequencies, time_step: Optional[float], freq_idx: int, uv_data: Dict[str, Any], observation: Observation) -> Dict[str, Any]:
        """Process baseline projections for a single scan, using pre-calculated (u,v) if available"""
        start_time = Time(scan.get_start_datetime())
        duration = scan.get_duration()
        telescope_indices = scan.get_telescope_indices()
        active_telescopes = [telescopes.get_by_index(i) for i in telescope_indices if telescopes.get_by_index(i).isactive]
        frequency = frequencies.get_by_index(freq_idx).get_frequency() * 1e6  # MHz -> Hz
        source = scan.get_source(observation=observation)
        source_coord = SkyCoord(ra=source.get_ra_degrees() * u.deg, dec=source.get_dec_degrees() * u.deg, frame='icrs') if source else None

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            if uv_data and "uv_points" in uv_data:
                projections = self._compute_projections_from_uv(uv_data["uv_points"], active_telescopes, frequency)
            else:
                projections = self._compute_baseline_projections_at_time(active_telescopes, mean_time, frequency, source_coord)
            return {"projections": projections}
        else:
            times = np.arange(0, duration, time_step) * u.s + start_time
            projections = {}
            if uv_data and "uv_points" in uv_data and "times" in uv_data:
                for t, uv_points in zip(uv_data["times"], uv_data["uv_points"][frequency]):
                    proj = self._compute_projections_from_uv({frequency: uv_points}, active_telescopes, frequency)
                    for pair, (uu, vv, ww) in proj.items():
                        projections.setdefault(pair, {"u": [], "v": [], "w": []})
                        projections[pair]["u"].append(uu)
                        projections[pair]["v"].append(vv)
                        projections[pair]["w"].append(ww)
            else:
                for t in times:
                    proj = self._compute_baseline_projections_at_time(active_telescopes, t, frequency, source_coord)
                    for pair, (uu, vv, ww) in proj.items():
                        projections.setdefault(pair, {"u": [], "v": [], "w": []})
                        projections[pair]["u"].append(uu)
                        projections[pair]["v"].append(vv)
                        projections[pair]["w"].append(ww)
            return {"times": [t.isot for t in times], "projections": projections}
        
    def _compute_baseline_projections_at_time(self, telescopes: List[Telescope | SpaceTelescope], time: Time, frequency: float, source_coord: Optional[SkyCoord] = None) -> Dict[str, Tuple[float, float, float]]:
        """Compute (u, v, w) baseline projections at a given time for a given frequency"""
        positions = [self._compute_telescope_position(tel, time) for tel in telescopes]
        c = 299792458  # m/s
        wavelength = c / frequency
        projections = {}
        
        # Если источник не указан, используем упрощенную систему (w = 0)
        if source_coord is None:
            for i, pos1 in enumerate(positions):
                for j, pos2 in enumerate(positions[i + 1:], i + 1):
                    baseline = np.array(pos1) - np.array(pos2)  # meters
                    uu, vv, ww = baseline[0] / wavelength, baseline[1] / wavelength, 0.0
                    pair = f"{telescopes[i].get_code()}-{telescopes[j].get_code()}"
                    projections[pair] = (uu, vv, ww)
        else:
            # Полное вычисление с учетом направления источника
            source_vec = source_coord.cartesian.xyz.value  # Единичный вектор источника
            for i, pos1 in enumerate(positions):
                for j, pos2 in enumerate(positions[i + 1:], i + 1):
                    baseline = np.array(pos1) - np.array(pos2)  # meters
                    uvw = np.dot(baseline, source_vec) / wavelength  # Проекция на источник
                    uu, vv = baseline[0] / wavelength, baseline[1] / wavelength  # Упрощенные u, v
                    ww = uvw  # w как проекция на линию визирования
                    pair = f"{telescopes[i].get_code()}-{telescopes[j].get_code()}"
                    projections[pair] = (uu, vv, ww)
    
        return projections

    def _compute_projections_from_uv(self, uv_points: Dict[float, List[Tuple[float, float]]], telescopes: List[Telescope | SpaceTelescope], frequency: float) -> Dict[str, Tuple[float, float, float]]:
        """Compute (u, v, w) projections from pre-calculated (u,v) data"""
        projections = {}
        uv_list = uv_points[frequency]
        idx = 0
        for i, tel1 in enumerate(telescopes):
            for j, tel2 in enumerate(telescopes[i + 1:], i + 1):
                uu, vv = uv_list[idx]
                # w вычисляем как заглушку (нужно полное моделирование для точного w, здесь упрощение)
                ww = 0.0  # Для точного w требуется направление источника и полная геометрия
                pair = f"{tel1.get_code()}-{tel2.get_code()}"
                projections[pair] = (uu, vv, ww)
                idx += 1
        return projections

    def _calculate_mollweide_tracks(self, obj: Observation | Project, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Mollweide projection tracks for VLBI or SINGLE_DISH observation or project"""
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "mollweide_tracks")
            recalculate = attributes.get("recalculate", False)

            if isinstance(obj, Project):
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

            scans = obj.get_scans().get_active_scans(obj)
            sources = obj.get_sources()

            existing_data = obj.get_calculated_data_by_key(store_key)
            if existing_data and not recalculate:
                logger.info(f"Using cached Mollweide tracks for '{obj.get_observation_code()}'")
                return existing_data["data"]

            results = {}
            with ThreadPoolExecutor() as executor:
                futures = {
                    executor.submit(self._process_mollweide_tracks, scan, sources, time_step): i
                    for i, scan in enumerate(scans)
                }
                for future in futures:
                    scan_idx = futures[future]
                    results[scan_idx] = future.result()

            metadata = {"time_step": time_step, "scan_count": len(scans)}
            with self._lock:
                obj.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": results})
            logger.info(f"Calculated Mollweide tracks for {len(scans)} scans in '{obj.get_observation_code()}'")
            return results
        except Exception as e:
            logger.error(f"Failed to calculate Mollweide tracks: {str(e)}")
            return {}

    def _process_mollweide_tracks(self, scan: Scan, sources: Sources, time_step: Optional[float]) -> Dict[str, Any]:
        """Process Mollweide tracks for a single scan with precession and nutation"""
        start_time = Time(scan.get_start_datetime())
        duration = scan.get_duration()
        source = sources.get_by_index(scan.get_source_index())
        source_coord = SkyCoord(ra=source.get_ra_degrees() * u.deg, dec=source.get_dec_degrees() * u.deg, frame='icrs')

        if time_step is None:
            mean_time = start_time + (duration / 2) * u.s
            lon, lat = self._compute_mollweide_coords(source_coord, mean_time)
            return {"source": source.get_name(), "mollweide": {"lon": lon, "lat": lat}}
        else:
            times = np.arange(0, duration, time_step) * u.s + start_time
            tracks = {"lon": [], "lat": []}
            for t in times:
                lon, lat = self._compute_mollweide_coords(source_coord, t)
                tracks["lon"].append(lon)
                tracks["lat"].append(lat)
            return {"source": source.get_name(), "times": [t.isot for t in times], "mollweide": tracks}

    def _compute_mollweide_coords(self, coord: SkyCoord, time: Time) -> Tuple[float, float]:
        """Compute Mollweide projection coordinates with precession and nutation"""
        from astropy.coordinates import CIRS
        
        cirs_coord = coord.transform_to(CIRS(obstime=time))
        
        # Получаем RA и Dec в радианах
        ra = cirs_coord.ra.rad
        dec = cirs_coord.dec.rad
        
        # Mollweide-проекция
        theta = dec
        if abs(dec) >= np.pi / 2:
            lat = np.sign(dec) * np.pi / 2
        else:
            lat = dec
        lon = ra - np.pi  # Центрирование на 0
        
        return np.degrees(lon), np.degrees(lat)

    def execute(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
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

        obj_type = type(obj)
        calc_methods = self._manipulator.get_methods_for_type(Calculator)

        calc_type = attributes.get("type")
        if not calc_type:
            logger.error("Calculation type must be specified in attributes")
            raise ValueError("Calculation type must be specified in attributes")

        calc_method_name = f"_calculate_{calc_type}"
        if calc_method_name not in calc_methods:
            logger.error(f"No calculation method found for type '{calc_type}'")
            raise ValueError(f"No calculation method for type '{calc_type}'")

        try:
            return calc_methods[calc_method_name](obj, attributes)
        except Exception as e:
            logger.error(f"Failed to calculate {calc_type} for {obj_type}: {str(e)}")
            return {}

    def __repr__(self) -> str:
        return "Calculator()"

class DefaultCalculator(Calculator):
    """Default implementation of Calculator"""
    def __init__(self, manipulator: 'Manipulator'):
        super().__init__(manipulator)
        logger.info("Initialized DefaultCalculator")