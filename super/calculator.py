# super/calculator.py
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
import numpy as np
from astropy.coordinates import EarthLocation, AltAz, SkyCoord, ITRS, GCRS
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
        return np.array([gcrs.x.value, gcrs.y.value, gcrs.z.value]) * u.m

    def calculate_telescope_positions(self, observation: Observation, time: float) -> Dict[str, np.ndarray]:
        """Calculate telescope positions in J2000 at given time."""
        positions = {}
        dt = Time(time, format='unix')
        for tel in observation.get_telescopes().get_active_telescopes():
            if isinstance(tel, SpaceTelescope):
                pos, _ = tel.get_position_at_time(dt.datetime)
            else:
                itrf_coords = np.array(tel.get_telescope_coordinates())
                pos = self._itrf_to_j2000(itrf_coords, dt)
            positions[tel.get_telescope_code()] = pos
        return positions

    def calculate_source_visibility(self, observation: Observation, scan: 'Scan') -> Dict[str, bool]:
        """Calculate precise source visibility for each telescope."""
        source = scan.get_source()
        if not source or scan.is_off_source:
            return {}
        time = Time(scan.get_start(), format='unix')
        source_coord = SkyCoord(ra=source.get_ra_degrees()*u.deg, dec=source.get_dec_degrees()*u.deg, frame='icrs')
        visibility = {}
        for tel in scan.get_telescopes().get_active_telescopes():
            if isinstance(tel, SpaceTelescope):
                pos, _ = tel.get_position_at_time(time.datetime)
                visibility[tel.get_telescope_code()] = np.linalg.norm(pos) < 1e9  # Simplified check
            else:
                loc = EarthLocation(x=tel.get_telescope_coordinates()[0]*u.m,
                                   y=tel.get_telescope_coordinates()[1]*u.m,
                                   z=tel.get_telescope_coordinates()[2]*u.m)
                altaz_frame = AltAz(obstime=time, location=loc)
                altaz = source_coord.transform_to(altaz_frame)
                el_range = tel.get_elevation_range()
                az_range = tel.get_azimuth_range()
                visible = (el_range[0] <= altaz.alt.deg <= el_range[1] and
                          az_range[0] <= (altaz.az.deg % 360) <= az_range[1])
                visibility[tel.get_telescope_code()] = visible
        return visibility

    def calculate_baseline_projections(self, observation: Observation, scan: 'Scan') -> Dict[Tuple[str, str], np.ndarray]:
        """Calculate baseline projections relative to Earth's center."""
        if observation.get_observation_type() != "VLBI":
            return {}
        positions = self.calculate_telescope_positions(observation, scan.get_start())
        baselines = {}
        tels = list(positions.keys())
        for i in range(len(tels)):
            for j in range(i + 1, len(tels)):
                baseline = positions[tels[i]] - positions[tels[j]]
                baselines[(tels[i], tels[j])] = baseline
        return baselines

    def calculate_uv_coverage(self, observation: Observation, scan: 'Scan') -> Dict[Tuple[str, str], List[Tuple[float, float]]]:
        """Calculate u,v coverage for VLBI."""
        if observation.get_observation_type() != "VLBI":
            return {}
        source = scan.get_source()
        if not source:
            return {}
        time_steps = np.linspace(scan.get_start(), scan.get_start() + scan.get_duration(), num=100)
        source_coord = SkyCoord(ra=source.get_ra_degrees()*u.deg, dec=source.get_dec_degrees()*u.deg, frame='icrs')
        uv_coverage = {}
        visibility = self.calculate_source_visibility(observation, scan)
        baselines = self.calculate_baseline_projections(observation, scan)
        
        for (tel1, tel2), baseline in baselines.items():
            if not (visibility.get(tel1, False) and visibility.get(tel2, False)):
                continue
            uv_points = []
            for t in time_steps:
                dt = Time(t, format='unix')
                # Точный расчет часового угла через LST
                lst = dt.sidereal_time('apparent', 'greenwich')  # Примерно для Земли, можно уточнить для телескопа
                ra_rad = source_coord.ra.rad
                dec_rad = source_coord.dec.rad
                h = (lst.rad - ra_rad)  # Часовой угол в радианах
                u = baseline[0] * np.sin(h) + baseline[1] * np.cos(h)
                v = -baseline[0] * np.sin(dec_rad) * np.cos(h) + \
                    baseline[1] * np.sin(dec_rad) * np.sin(h) + \
                    baseline[2] * np.cos(dec_rad)
                uv_points.append((u.value, v.value))  # Убираем единицы для хранения
            uv_coverage[(tel1, tel2)] = uv_points
        return uv_coverage

    def calculate_telescope_sensitivity(self, observation: Observation, freq: IF) -> Dict[str, float]:
        """Calculate SEFD for each telescope using get_sefd()."""
        sensitivities = {}
        for tel in observation.get_telescopes().get_active_telescopes():
            sefd = tel.get_sefd()  # Directly use telescope's SEFD
            sensitivities[tel.get_telescope_code()] = sefd
        return sensitivities

    def calculate_baseline_sensitivity(self, observation: Observation, scan: 'Scan', freq: IF) -> Dict[Tuple[str, str], float]:
        """Calculate baseline sensitivity for VLBI."""
        if observation.get_observation_type() != "VLBI":
            return {}
        sensitivities = {}
        tels = observation.get_telescopes().get_active_telescopes()
        tel_sefd = self.calculate_telescope_sensitivity(observation, freq)
        bandwidth = freq.get_bandwidth() * 1e6  # MHz -> Hz
        duration = scan.get_duration()
        for i in range(len(tels)):
            for j in range(i + 1, len(tels)):
                tel1, tel2 = tels[i], tels[j]
                sefd1 = tel_sefd[tel1.get_telescope_code()]
                sefd2 = tel_sefd[tel2.get_telescope_code()]
                sensitivity = np.sqrt(sefd1 * sefd2) / np.sqrt(2 * bandwidth * duration)
                sensitivities[(tel1.get_telescope_code(), tel2.get_telescope_code())] = sensitivity
        return sensitivities

    def calculate_mollweide_tracks(self, observation: Observation, scan: 'Scan') -> Dict[str, List[Tuple[float, float]]]:
        """Calculate Mollweide tracks for each telescope."""
        source = scan.get_source()
        if not source:
            return {}
        time_steps = np.linspace(scan.get_start(), scan.get_start() + scan.get_duration(), num=100)
        source_coord = SkyCoord(ra=source.get_ra_degrees()*u.deg, dec=source.get_dec_degrees()*u.deg, frame='icrs')
        tracks = {}
        for tel in scan.get_telescopes().get_active_telescopes():
            if isinstance(tel, SpaceTelescope):
                continue  # Skip space telescopes for now
            loc = EarthLocation(x=tel.get_telescope_coordinates()[0]*u.m,
                               y=tel.get_telescope_coordinates()[1]*u.m,
                               z=tel.get_telescope_coordinates()[2]*u.m)
            track = []
            for t in time_steps:
                dt = Time(t, format='unix')
                altaz = source_coord.transform_to(AltAz(obstime=dt, location=loc))
                ra_rad = source_coord.ra.rad
                dec_rad = source_coord.dec.rad
                x = 2 * np.sqrt(2) * np.cos(dec_rad) * np.sin(ra_rad / 2) / np.pi
                y = np.sqrt(2) * np.sin(dec_rad)
                track.append((x, y))
            tracks[tel.get_telescope_code()] = track
        return tracks

    def calculate_mollweide_distance(self, observation: Observation, scan: 'Scan') -> Dict[str, float]:
        """Calculate distance from source to Mollweide track."""
        source = scan.get_source()
        if not source:
            return {}
        tracks = self.calculate_mollweide_tracks(observation, scan)
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
        sun_coord = SkyCoord.from_name("Sun").transform_to(GCRS(obstime=time))
        for tel in scan.get_telescopes().get_active_telescopes():
            if isinstance(tel, SpaceTelescope):
                continue
            loc = EarthLocation(x=tel.get_telescope_coordinates()[0]*u.m,
                               y=tel.get_telescope_coordinates()[1]*u.m,
                               z=tel.get_telescope_coordinates()[2]*u.m)
            altaz_frame = AltAz(obstime=time, location=loc)
            diameter = tel.get_diameter() * u.m
            tel_fov = {}
            for freq in observation.get_frequencies().get_active_frequencies():
                freq_hz = freq.get_freq() * 1e6  # MHz -> Hz
                wavelength = (3e8 / freq_hz) * u.m  # Speed of light / frequency
                fov_radius = (1.22 * wavelength / diameter).to(u.deg).value  # Angular resolution in degrees
                sources_in_fov = []
                for src in observation.get_sources().get_active_sources():
                    src_coord = SkyCoord(ra=src.get_ra_degrees()*u.deg, dec=src.get_dec_degrees()*u.deg, frame='icrs')
                    altaz_src = src_coord.transform_to(altaz_frame)
                    if altaz_src.separation(altaz_frame).deg < fov_radius:
                        sources_in_fov.append(src.get_name())
                sun_altaz = sun_coord.transform_to(altaz_frame)
                tel_fov[f"freq_{freq.get_freq()}"] = {
                    "sources": sources_in_fov,
                    "sun_alt": sun_altaz.alt.deg,
                    "sun_az": sun_altaz.az.deg,
                    "fov_radius": fov_radius
                }
            fov_data[tel.get_telescope_code()] = tel_fov
        return fov_data

    def calculate_sun_angles(self, observation: Observation, scan: 'Scan') -> Dict[str, float]:
        """Calculate angles between source and Sun directions."""
        source = scan.get_source()
        if not source:
            return {}
        time = Time(scan.get_start(), format='unix')
        source_coord = SkyCoord(ra=source.get_ra_degrees()*u.deg, dec=source.get_dec_degrees()*u.deg, frame='icrs')
        sun_coord = SkyCoord.from_name("Sun").transform_to(GCRS(obstime=time))
        angles = {}
        for tel in scan.get_telescopes().get_active_telescopes():
            separation = source_coord.separation(sun_coord).deg
            angles[tel.get_telescope_code()] = separation
        return angles

    def calculate_beam_pattern(self, observation: Observation, scan: 'Scan') -> Dict[str, np.ndarray]:
        """Calculate beam pattern (SINGLE_DISH: Gaussian, VLBI: from u,v)."""
        beam_patterns = {}
        for tel in scan.get_telescopes().get_active_telescopes():
            if observation.get_observation_type() == "SINGLE_DISH":
                # Gaussian beam based on FOV
                diameter = tel.get_diameter() * u.m
                freq = observation.get_frequencies().get_active_frequencies()[0].get_freq() * 1e6  # MHz -> Hz
                wavelength = (3e8 / freq) * u.m
                fwhm = (1.22 * wavelength / diameter).to(u.deg).value * 2  # Approximate FWHM
                theta = np.linspace(-1, 1, 100) * u.deg
                pattern = np.exp(-4 * np.log(2) * (theta / fwhm)**2)
                beam_patterns[tel.get_telescope_code()] = pattern
            elif observation.get_observation_type() == "VLBI":
                # Synthesized beam from u,v coverage
                uv_coverage = self.calculate_uv_coverage(observation, scan)
                if not uv_coverage:
                    beam_patterns[tel.get_telescope_code()] = np.ones(100)  # Fallback
                    continue
                # Simplified: FFT of u,v points to get synthesized beam
                u_vals = []
                v_vals = []
                for baseline, points in uv_coverage.items():
                    u_vals.extend([p[0] for p in points])
                    v_vals.extend([p[1] for p in points])
                u_vals = np.array(u_vals)
                v_vals = np.array(v_vals)
                # Create a coarse grid for FFT (placeholder resolution)
                grid_size = 100
                uv_grid = np.zeros((grid_size, grid_size), dtype=complex)
                u_max, v_max = max(abs(u_vals.max()), abs(u_vals.min())), max(abs(v_vals.max()), abs(v_vals.min()))
                for u, v in zip(u_vals, v_vals):
                    u_idx = int((u + u_max) / (2 * u_max) * (grid_size - 1))
                    v_idx = int((v + v_max) / (2 * v_max) * (grid_size - 1))
                    if 0 <= u_idx < grid_size and 0 <= v_idx < grid_size:
                        uv_grid[u_idx, v_idx] += 1
                beam = np.abs(np.fft.fftshift(np.fft.fft2(uv_grid)))
                beam_1d = beam[grid_size // 2, :]  # Take central slice
                beam_patterns[tel.get_telescope_code()] = beam_1d / beam_1d.max()  # Normalize
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
                    scan_data[f"baseline_sensitivity_{freq.get_freq()}"] = self.calculate_baseline_sensitivity(
                        observation, scan, freq)
            for freq in observation.get_frequencies().get_active_frequencies():
                scan_data[f"telescope_sensitivity_{freq.get_freq()}"] = self.calculate_telescope_sensitivity(
                    observation, freq)
            scan_data["mollweide_tracks"] = self.calculate_mollweide_tracks(observation, scan)
            scan_data["mollweide_distances"] = self.calculate_mollweide_distance(observation, scan)
            if observation.get_observation_type() == "SINGLE_DISH":
                scan_data["field_of_view"] = self.calculate_field_of_view(observation, scan)
            scan_data["sun_angles"] = self.calculate_sun_angles(observation, scan)
            scan_data["beam_pattern"] = self.calculate_beam_pattern(observation, scan)
            calculated_data[f"scan_{scan.get_start()}"] = scan_data
        observation._calculated_data = calculated_data
        logger.info(f"Calculated all parameters for observation '{observation.get_observation_code()}'")