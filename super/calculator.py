# super/calculator.py
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
import numpy as np
from astropy.coordinates import EarthLocation, AltAz, SkyCoord, ITRS, GCRS, get_sun
from astropy.time import Time
from astropy import units as u
from base.observation import Observation
from base.telescopes import Telescope, SpaceTelescope
from base.scans import Scan, Scans
from base.sources import Source
from base.frequencies import IF
from utils.validation import check_type
from utils.logging_setup import logger


class Calculator(ABC):
    """Abstract base class for observation parameter calculations."""
    @abstractmethod
    def calculate_all(self, observation: Observation) -> None:
        """Perform all calculations for the observation."""
        pass

    def _itrf_to_j2000(self, itrf_coords: np.ndarray, time: Time) -> np.ndarray:
        """Convert ITRF coordinates to J2000 (GCRS)."""
        loc = EarthLocation(x=itrf_coords[0]*u.m, y=itrf_coords[1]*u.m, z=itrf_coords[2]*u.m)
        itrs = loc.get_itrs(obstime=time)
        gcrs = itrs.transform_to(GCRS(obstime=time))
        cartesian = gcrs.cartesian
        return np.array([cartesian.x.value, cartesian.y.value, cartesian.z.value]) * u.m

    def calculate_telescope_positions(self, observation: Observation, time: float) -> Dict[str, np.ndarray]:
        """Calculate telescope positions in J2000 at a given time (e.g., scan start)."""
        check_type(observation, Observation, "Observation")
        check_type(time, (int, float), "Time")
        positions = {}
        dt = Time(time, format='unix')
        logger.info(f"Calculating telescope positions in J2000 for time={dt.iso} ({time})")
        for tel in observation.get_telescopes().get_active_telescopes():
            tel_code = tel.get_code()
            if isinstance(tel, SpaceTelescope):
                pos, _ = tel.get_state_vector(dt.datetime)
                # Преобразуем в np.ndarray, если это список
                pos = np.array(pos) if not isinstance(pos, np.ndarray) else pos
                logger.debug(f"Position for SpaceTelescope '{tel_code}': {pos}")
            else:
                itrf_coords = np.array(tel.get_coordinates())
                pos = self._itrf_to_j2000(itrf_coords, dt)
                logger.debug(f"Converted ITRF {itrf_coords} to J2000 {pos} for '{tel_code}'")
            positions[tel_code] = pos
        logger.info(f"Calculated positions for {len(positions)} telescopes")
        return positions

    def calculate_source_visibility(self, observation: Observation, scan: 'Scan') -> Dict[str, bool]:
        """Calculate precise source visibility for each telescope."""
        check_type(observation, Observation, "Observation")
        check_type(scan, Scan, "Scan")
        
        source_index = scan.get_source_index()
        if source_index is None or scan.is_off_source:
            logger.debug(f"Scan with start={scan.get_start()} is OFF SOURCE or has no source, skipping visibility calculation")
            return {}
        
        sources = observation.get_sources().get_all_sources()
        if source_index < 0 or source_index >= len(sources):
            logger.error(f"Invalid source_index {source_index} for observation with {len(sources)} sources")
            return {}
        source = sources[source_index]
        
        time = Time(scan.get_start(), format='unix')
        source_coord = SkyCoord(ra=source.get_ra_degrees()*u.deg, dec=source.get_dec_degrees()*u.deg, frame='icrs')
        visibility = {}
        
        all_tels = observation.get_telescopes().get_all_telescopes()
        active_tel_indices = scan.get_telescope_indices()
        if not active_tel_indices:
            logger.debug(f"Scan with start={scan.get_start()} has no active telescopes")
            return {}
        
        for tel_idx in active_tel_indices:
            if tel_idx < 0 or tel_idx >= len(all_tels):
                logger.warning(f"Invalid telescope index {tel_idx} in scan, skipping")
                continue
            tel = all_tels[tel_idx]
            if not tel.isactive:
                continue
            
            if isinstance(tel, SpaceTelescope):
                pos, _ = tel.get_position_at_time(time.datetime)
                visibility[tel.get_code()] = np.linalg.norm(pos) < 1e9
            else:
                loc = EarthLocation(x=tel.get_coordinates()[0]*u.m,
                                   y=tel.get_coordinates()[1]*u.m,
                                   z=tel.get_coordinates()[2]*u.m)
                altaz_frame = AltAz(obstime=time, location=loc)
                altaz = source_coord.transform_to(altaz_frame)
                el_range = tel.get_elevation_range()
                az_range = tel.get_azimuth_range()
                visible = (el_range[0] <= altaz.alt.deg <= el_range[1] and
                          az_range[0] <= (altaz.az.deg % 360) <= az_range[1])
                visibility[tel.get_code()] = visible
        
        logger.debug(f"Calculated visibility for scan with start={scan.get_start()}: {visibility}")
        return visibility

    def calculate_baseline_projections(self, observation: Observation, scan: 'Scan') -> Dict[str, np.ndarray]:
        """Calculate baseline projections relative to Earth's center."""
        if observation.get_observation_type() != "VLBI":
            return {}
        scan_key = f"scan_{scan.get_start()}"
        calculated_data = observation._calculated_data.get(scan_key, {})
        positions = calculated_data.get("telescope_positions")
        if positions is None:
            positions = self.calculate_telescope_positions(observation, scan.get_start())
            logger.debug(f"Recalculated telescope positions for scan with start={scan.get_start()}")
        baselines = {}
        tels = list(positions.keys())
        for i in range(len(tels)):
            for j in range(i + 1, len(tels)):
                tel_pair = f"{tels[i]}-{tels[j]}"
                pos_i = np.array(positions[tels[i]]) if not isinstance(positions[tels[i]], np.ndarray) else positions[tels[i]]
                pos_j = np.array(positions[tels[j]]) if not isinstance(positions[tels[j]], np.ndarray) else positions[tels[j]]
                baseline = pos_i - pos_j
                baselines[tel_pair] = baseline
        logger.debug(f"Calculated baseline projections for scan with start={scan.get_start()}: {baselines}")
        return baselines

    def calculate_uv_coverage(self, observation: Observation, scan: 'Scan') -> Dict[str, List[Tuple[float, float]]]:
        """Calculate u,v coverage for VLBI"""
        if observation.get_observation_type() != "VLBI":
            return {}
        
        source_index = scan.get_source_index()
        if source_index is None or scan.is_off_source:
            logger.debug(f"Scan with start={scan.get_start()} is OFF SOURCE or has no source, skipping UV coverage")
            return {}
        
        sources = observation.get_sources().get_all_sources()
        if source_index < 0 or source_index >= len(sources):
            logger.error(f"Invalid source_index {source_index} for observation with {len(sources)} sources")
            return {}
        source = sources[source_index]
        
        time_steps = np.linspace(scan.get_start(), scan.get_start() + scan.get_duration(), num=100)
        source_coord = SkyCoord(ra=source.get_ra_degrees()*u.deg, dec=source.get_dec_degrees()*u.deg, frame='icrs')
        uv_coverage = {}
        
        scan_key = f"scan_{scan.get_start()}"
        calculated_data = observation.get_calculated_data().get(scan_key, {})
        
        visibility = calculated_data.get("source_visibility")
        if visibility is None:
            visibility = self.calculate_source_visibility(observation, scan)
            logger.debug(f"Recalculated source visibility for scan with start={scan.get_start()}")
        
        baselines = calculated_data.get("baseline_projections")
        if baselines is None:
            baselines = self.calculate_baseline_projections(observation, scan)
            logger.debug(f"Recalculated baseline projections for scan with start={scan.get_start()}")
        
        for tel_pair, baseline in baselines.items():
            tel1, tel2 = tel_pair.split("-")
            if not (visibility.get(tel1, False) and visibility.get(tel2, False)):
                continue
            uv_points = []
            for t in time_steps:
                dt = Time(t, format='unix')
                lst = dt.sidereal_time('apparent', 'greenwich')
                ra_rad = source_coord.ra.rad
                dec_rad = source_coord.dec.rad
                h = (lst.rad - ra_rad)
                uu = baseline[0] * np.sin(h) + baseline[1] * np.cos(h)
                vv = -baseline[0] * np.sin(dec_rad) * np.cos(h) + \
                    baseline[1] * np.sin(dec_rad) * np.sin(h) + \
                    baseline[2] * np.cos(dec_rad)
                uv_points.append((uu.value, vv.value))
            uv_coverage[tel_pair] = uv_points
        logger.debug(f"Calculated UV coverage for scan with start={scan.get_start()}: {uv_coverage}")
        return uv_coverage

    def calculate_telescope_sensitivity(self, observation: Observation, freq: IF) -> Dict[str, float]:
        """Calculate SEFD for each telescope at the given frequency"""
        check_type(observation, Observation, "Observation")
        check_type(freq, IF, "Frequency")
        sensitivities = {}
        frequency_mhz = freq.get_frequency()
        for tel in observation.get_telescopes().get_active_telescopes():
            sefd = tel.get_sefd(frequency_mhz)
            if sefd is None:
                logger.warning(f"No SEFD data for telescope '{tel.get_code()}' at frequency {frequency_mhz} MHz")
                sensitivities[tel.get_code()] = None
            else:
                sensitivities[tel.get_code()] = sefd
                logger.debug(f"SEFD for '{tel.get_code()}' at {frequency_mhz} MHz: {sefd} Jy")
        return sensitivities

    def calculate_baseline_sensitivity(self, observation: Observation, scan: 'Scan', freq: IF) -> Dict[str, float]:
        """Calculate baseline sensitivity for VLBI at the given frequency."""
        if observation.get_observation_type() != "VLBI":
            return {}
        check_type(observation, Observation, "Observation")
        check_type(scan, Scan, "Scan")
        check_type(freq, IF, "Frequency")
        scan_key = f"scan_{scan.get_start()}"
        calculated_data = observation.get_calculated_data().get(scan_key, {})
        tel_sefd = calculated_data.get(f"telescope_sensitivity_{freq.get_frequency()}")
        if tel_sefd is None:
            tel_sefd = self.calculate_telescope_sensitivity(observation, freq)
            logger.debug(f"Recalculated telescope sensitivity for frequency {freq.get_frequency()} MHz")
        sensitivities = {}
        tels = observation.get_telescopes().get_active_telescopes()
        bandwidth = freq.get_bandwidth() * 1e6  # MHz -> Hz
        duration = scan.get_duration()
        for i in range(len(tels)):
            for j in range(i + 1, len(tels)):
                tel1, tel2 = tels[i], tels[j]
                tel_pair = f"{tel1.get_code()}-{tel2.get_code()}"
                sefd1 = tel_sefd[tel1.get_code()]
                sefd2 = tel_sefd[tel2.get_code()]
                if sefd1 is None or sefd2 is None:
                    sensitivity = None
                else:
                    sensitivity = np.sqrt(sefd1 * sefd2) / np.sqrt(2 * bandwidth * duration)
                sensitivities[tel_pair] = sensitivity
                logger.debug(f"Baseline sensitivity for {tel_pair} "
                            f"at {freq.get_frequency()} MHz: {sensitivity}")
        return sensitivities

    def calculate_mollweide_tracks(self, observation: Observation, scan: 'Scan') -> Dict[str, List[Tuple[float, float]]]:
        """Calculate Mollweide tracks for each telescope."""
        source_index = scan.get_source_index()
        if source_index is None or scan.is_off_source:
            logger.debug(f"Scan with start={scan.get_start()} is OFF SOURCE or has no source, skipping Mollweide tracks")
            return {}
        
        sources = observation.get_sources().get_all_sources()
        if source_index < 0 or source_index >= len(sources):
            logger.error(f"Invalid source_index {source_index} for observation with {len(sources)} sources")
            return {}
        source = sources[source_index]
        
        time_steps = np.linspace(scan.get_start(), scan.get_start() + scan.get_duration(), num=100)
        source_coord = SkyCoord(ra=source.get_ra_degrees()*u.deg, dec=source.get_dec_degrees()*u.deg, frame='icrs')
        tracks = {}
        
        all_tels = observation.get_telescopes().get_all_telescopes()
        active_tel_indices = scan.get_telescope_indices()
        for tel_idx in active_tel_indices:
            if tel_idx < 0 or tel_idx >= len(all_tels):
                logger.warning(f"Invalid telescope index {tel_idx} in scan, skipping")
                continue
            tel = all_tels[tel_idx]
            if not tel.isactive or isinstance(tel, SpaceTelescope):
                continue
            
            loc = EarthLocation(x=tel.get_coordinates()[0]*u.m,
                               y=tel.get_coordinates()[1]*u.m,
                               z=tel.get_coordinates()[2]*u.m)
            track = []
            for t in time_steps:
                dt = Time(t, format='unix')
                altaz = source_coord.transform_to(AltAz(obstime=dt, location=loc))
                ra_rad = source_coord.ra.rad
                dec_rad = source_coord.dec.rad
                x = 2 * np.sqrt(2) * np.cos(dec_rad) * np.sin(ra_rad / 2) / np.pi
                y = np.sqrt(2) * np.sin(dec_rad)
                track.append((x, y))
            tracks[tel.get_code()] = track
        return tracks

    def calculate_mollweide_distance(self, observation: Observation, scan: 'Scan') -> Dict[str, float]:
        """Calculate distance from source to Mollweide track."""
        source_index = scan.get_source_index()
        if source_index is None or scan.is_off_source:
            logger.debug(f"Scan with start={scan.get_start()} is OFF SOURCE or has no source, skipping Mollweide distance")
            return {}
        
        sources = observation.get_sources().get_all_sources()
        if source_index < 0 or source_index >= len(sources):
            logger.error(f"Invalid source_index {source_index} for observation with {len(sources)} sources")
            return {}
        source = sources[source_index]
        
        scan_key = f"scan_{scan.get_start()}"
        calculated_data = observation.get_calculated_data().get(scan_key, {})
        tracks = calculated_data.get("mollweide_tracks")
        if tracks is None:
            tracks = self.calculate_mollweide_tracks(observation, scan)
            logger.debug(f"Recalculated Mollweide tracks for scan with start={scan.get_start()}")
        
        source_coord = SkyCoord(ra=source.get_ra_degrees()*u.deg, dec=source.get_dec_degrees()*u.deg, frame='icrs')
        ra_rad = source_coord.ra.rad
        dec_rad = source_coord.dec.rad
        source_x = 2 * np.sqrt(2) * np.cos(dec_rad) * np.sin(ra_rad / 2) / np.pi
        source_y = np.sqrt(2) * np.sin(dec_rad)
        distances = {}
        for tel_code, track in tracks.items():
            min_dist = min(np.sqrt((x - source_x)**2 + (y - source_y)**2) for x, y in track)
            distances[tel_code] = min_dist
        return distances

    def calculate_field_of_view(self, observation: Observation, scan: 'Scan') -> Dict[str, Dict[str, Dict]]:
        """Calculate field of view per frequency and objects within it."""
        if observation.get_observation_type() != "SINGLE_DISH":
            return {}
        time = Time(scan.get_start(), format='unix')
        fov_data = {}
        sun_coord = get_sun(time)
        
        all_tels = observation.get_telescopes().get_all_telescopes()
        active_tel_indices = scan.get_telescope_indices()
        for tel_idx in active_tel_indices:
            if tel_idx < 0 or tel_idx >= len(all_tels):
                logger.warning(f"Invalid telescope index {tel_idx} in scan, skipping")
                continue
            tel = all_tels[tel_idx]
            if not tel.isactive or isinstance(tel, SpaceTelescope):
                continue
            
            loc = EarthLocation(x=tel.get_coordinates()[0]*u.m,
                            y=tel.get_coordinates()[1]*u.m,
                            z=tel.get_coordinates()[2]*u.m)
            altaz_frame = AltAz(obstime=time, location=loc)
            diameter = tel.get_diameter() * u.m
            tel_fov = {}
            for freq in observation.get_frequencies().get_active_frequencies():
                freq_hz = freq.get_frequency() * 1e6
                wavelength = (3e8 / freq_hz) * u.m
                fov_radius = (1.22 * wavelength / diameter).to(u.deg).value
                sources_in_fov = []
                for src in observation.get_sources().get_active_sources():
                    src_coord = SkyCoord(ra=src.get_ra_degrees()*u.deg, dec=src.get_dec_degrees()*u.deg, frame='icrs')
                    altaz_src = src_coord.transform_to(altaz_frame)
                    if altaz_src.separation(altaz_frame).deg < fov_radius:
                        sources_in_fov.append(src.get_name())
                sun_altaz = sun_coord.transform_to(altaz_frame)
                tel_fov[f"freq_{freq.get_frequency()}"] = {
                    "sources": sources_in_fov,
                    "sun_alt": sun_altaz.alt.deg,
                    "sun_az": sun_altaz.az.deg,
                    "fov_radius": fov_radius
                }
            fov_data[tel.get_code()] = tel_fov
        logger.debug(f"Calculated field of view for scan with start={scan.get_start()}: {fov_data}")
        return fov_data

    def calculate_sun_angles(self, observation: Observation, scan: 'Scan') -> Dict[str, float]:
        """Calculate angles between source and Sun directions."""
        source_index = scan.get_source_index()
        if source_index is None or scan.is_off_source:
            logger.debug(f"Scan with start={scan.get_start()} is OFF SOURCE or has no source, skipping sun angles")
            return {}
        
        sources = observation.get_sources().get_all_sources()
        if source_index < 0 or source_index >= len(sources):
            logger.error(f"Invalid source_index {source_index} for observation with {len(sources)} sources")
            return {}
        source = sources[source_index]
        
        time = Time(scan.get_start(), format='unix')
        source_coord = SkyCoord(ra=source.get_ra_degrees()*u.deg, dec=source.get_dec_degrees()*u.deg, frame='icrs')
        sun_coord = get_sun(time)
        angles = {}
        
        all_tels = observation.get_telescopes().get_all_telescopes()
        active_tel_indices = scan.get_telescope_indices()
        for tel_idx in active_tel_indices:
            if tel_idx < 0 or tel_idx >= len(all_tels):
                logger.warning(f"Invalid telescope index {tel_idx} in scan, skipping")
                continue
            tel = all_tels[tel_idx]
            if not tel.isactive:
                continue
            separation = source_coord.separation(sun_coord).deg
            angles[tel.get_code()] = separation
        logger.debug(f"Calculated sun angles for scan with start={scan.get_start()}: {angles}")
        return angles

    def calculate_beam_pattern(self, observation: Observation, scan: 'Scan') -> Dict[str, np.ndarray]:
        """Calculate beam pattern (SINGLE_DISH: Gaussian, VLBI: from u,v)."""
        beam_patterns = {}
        
        all_tels = observation.get_telescopes().get_all_telescopes()
        active_tel_indices = scan.get_telescope_indices()
        for tel_idx in active_tel_indices:
            if tel_idx < 0 or tel_idx >= len(all_tels):
                logger.warning(f"Invalid telescope index {tel_idx} in scan, skipping")
                continue
            tel = all_tels[tel_idx]
            if not tel.isactive:
                continue
            
            if observation.get_observation_type() == "SINGLE_DISH":
                diameter = tel.get_diameter() * u.m
                freq = observation.get_frequencies().get_active_frequencies()[0].get_frequency() * 1e6
                wavelength = (3e8 / freq) * u.m
                fwhm = (1.22 * wavelength / diameter).to(u.deg).value * 2
                theta = np.linspace(-1, 1, 100) * u.deg
                pattern = np.exp(-4 * np.log(2) * (theta / fwhm)**2)
                beam_patterns[tel.get_code()] = pattern
            elif observation.get_observation_type() == "VLBI":
                scan_key = f"scan_{scan.get_start()}"
                calculated_data = observation.get_calculated_data().get(scan_key, {})
                uv_coverage = calculated_data.get("uv_coverage")
                if uv_coverage is None:
                    uv_coverage = self.calculate_uv_coverage(observation, scan)
                    logger.debug(f"Recalculated UV coverage for scan with start={scan.get_start()}")
                if not uv_coverage:
                    beam_patterns[tel.get_code()] = np.ones(100)
                    continue
                u_vals = []
                v_vals = []
                for tel_pair, points in uv_coverage.items():
                    u_vals.extend([p[0] for p in points])
                    v_vals.extend([p[1] for p in points])
                u_vals = np.array(u_vals)
                v_vals = np.array(v_vals)
                grid_size = 100
                uv_grid = np.zeros((grid_size, grid_size), dtype=complex)
                u_max, v_max = max(abs(u_vals.max()), abs(u_vals.min())), max(abs(v_vals.max()), abs(v_vals.min()))
                for u, v in zip(u_vals, v_vals):
                    u_idx = int((u + u_max) / (2 * u_max) * (grid_size - 1))
                    v_idx = int((v + v_max) / (2 * v_max) * (grid_size - 1))
                    if 0 <= u_idx < grid_size and 0 <= v_idx < grid_size:
                        uv_grid[u_idx, v_idx] += 1
                beam = np.abs(np.fft.fftshift(np.fft.fft2(uv_grid)))
                beam_1d = beam[grid_size // 2, :]
                beam_patterns[tel.get_code()] = beam_1d / beam_1d.max()
        return beam_patterns


class DefaultCalculator(Calculator):
    """Default implementation of Calculator."""
    def calculate_all(self, observation: Observation) -> None:
        """Perform all calculations for the observation."""
        check_type(observation, Observation, "Observation")
        calculated_data = {}
        for scan in observation.get_scans().get_active_scans():
            scan_data = {}
            scan_data["telescope_positions"] = self.calculate_telescope_positions(observation, scan.get_start())
            scan_data["source_visibility"] = self.calculate_source_visibility(observation, scan)
            if observation.get_observation_type() == "VLBI":
                scan_data["baseline_projections"] = self.calculate_baseline_projections(observation, scan)
                scan_data["uv_coverage"] = self.calculate_uv_coverage(observation, scan)
                for freq in observation.get_frequencies().get_active_frequencies():
                    scan_data[f"baseline_sensitivity_{freq.get_frequency()}"] = self.calculate_baseline_sensitivity(
                        observation, scan, freq)
            for freq in observation.get_frequencies().get_active_frequencies():
                scan_data[f"telescope_sensitivity_{freq.get_frequency()}"] = self.calculate_telescope_sensitivity(
                    observation, freq)
            scan_data["mollweide_tracks"] = self.calculate_mollweide_tracks(observation, scan)
            scan_data["mollweide_distances"] = self.calculate_mollweide_distance(observation, scan)
            if observation.get_observation_type() == "SINGLE_DISH":
                scan_data["field_of_view"] = self.calculate_field_of_view(observation, scan)
            scan_data["sun_angles"] = self.calculate_sun_angles(observation, scan)
            scan_data["beam_pattern"] = self.calculate_beam_pattern(observation, scan)
            calculated_data[f"scan_{scan.get_start()}"] = scan_data
        observation.set_calculated_data(calculated_data)
        logger.info(f"Calculated all parameters for observation '{observation.get_observation_code()}'")