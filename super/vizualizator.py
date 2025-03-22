# super/vizualizator.py
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
import numpy as np
import matplotlib.pyplot as plt
from base.observation import Observation
from base.sources import Source
from utils.validation import check_type
from utils.logging_setup import logger
from astropy.coordinates import SkyCoord, AltAz, EarthLocation
from astropy.time import Time
from astropy import units as u
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt


class Vizualizator(ABC):
    """Abstract base class for visualizing observation data."""
    @abstractmethod
    def visualize_observation(self, observation: Observation) -> None:
        """Visualize the observation data."""
        pass

    def plot_uv_coverage(self, uv_coverage: Dict[str, List[Tuple[float, float]]], canvas: FigureCanvas) -> None:
        """Plot u,v coverage for VLBI on the provided canvas."""
        fig = canvas.figure
        fig.clf()
        ax = fig.add_subplot(111)
        for tel_pair, points in uv_coverage.items():
            tel1, tel2 = tel_pair.split("-")
            u_vals, v_vals = zip(*points)
            ax.scatter(u_vals, v_vals, label=f"{tel1}-{tel2}", s=5)
            ax.scatter([-u for u in u_vals], [-v for v in v_vals], s=5)
        ax.set_xlabel("u (m)")
        ax.set_ylabel("v (m)")
        ax.set_title("u,v Coverage")
        ax.legend()
        ax.grid(True)
        canvas.draw()

    def plot_mollweide_tracks(self, tracks: Dict[str, List[Tuple[float, float]]], canvas: FigureCanvas) -> None:
        """Plot Mollweide tracks for telescopes in Mollweide projection on the provided canvas."""
        fig = canvas.figure
        fig.clf()
        ax = fig.add_subplot(111, projection='mollweide')  # Устанавливаем проекцию Мольвейде
        for tel_code, track in tracks.items():
            ra_vals, dec_vals = zip(*track)  # Предполагаем, что track содержит (ra, dec) в градусах
            # Преобразуем RA (инвертируем и переводим в радианы)
            ra_rad = [np.deg2rad(360 - ra) if ra <= 360 else np.deg2rad(360 - (ra % 360)) for ra in ra_vals]
            # Преобразуем Dec в радианы
            dec_rad = [np.deg2rad(dec) for dec in dec_vals]
            ax.plot(ra_rad, dec_rad, label=tel_code, linewidth=1.5)
        ax.set_xlabel("Right Ascension (radians)")
        ax.set_ylabel("Declination (radians)")
        ax.set_title("Mollweide Tracks of Telescopes")
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True)
        canvas.draw()

    def plot_beam_pattern(self, beam_patterns: Dict[str, np.ndarray], canvas: FigureCanvas) -> None:
        """Plot beam patterns for telescopes or baselines on the provided canvas."""
        fig = canvas.figure
        fig.clf()
        ax = fig.add_subplot(111)
        theta = np.linspace(-1, 1, 100)
        for tel_code, pattern in beam_patterns.items():
            ax.plot(theta, pattern, label=tel_code)
        ax.set_xlabel("Angle (deg)")
        ax.set_ylabel("Normalized Response")
        ax.set_title("Beam Pattern")
        ax.legend()
        ax.grid(True)
        canvas.draw()

    def plot_field_of_view(self, observation: Observation, scan_key: str, fov_data: Dict[str, Dict[str, Dict]], 
                          canvas: FigureCanvas) -> None:
        """Plot field of view with sources and Sun position for a specific scan on the provided canvas."""
        fig = canvas.figure
        fig.clf()
        ax = fig.add_subplot(111)
        scan_start = float(scan_key.split('_')[1])
        time = Time(scan_start, format='unix')
        
        for tel_code, freq_data in fov_data.items():
            loc = EarthLocation(x=observation.get_telescopes().get_telescope_by_code(tel_code).get_telescope_coordinates()[0]*u.m,
                               y=observation.get_telescopes().get_telescope_by_code(tel_code).get_telescope_coordinates()[1]*u.m,
                               z=observation.get_telescopes().get_telescope_by_code(tel_code).get_telescope_coordinates()[2]*u.m)
            altaz_frame = AltAz(obstime=time, location=loc)
            
            for freq_key, data in freq_data.items():
                radius = data["fov_radius"]
                sun_alt, sun_az = data["sun_alt"], data["sun_az"]
                ax.scatter(sun_az, sun_alt, c='yellow', s=100, 
                          label="Sun" if tel_code == list(fov_data.keys())[0] and freq_key == list(freq_data.keys())[0] else "")
                
                fov_center_az, fov_center_alt = None, None
                for src_name in data["sources"]:
                    src = next((s for s in observation.get_sources().get_active_sources() if s.get_name() == src_name), None)
                    if src:
                        src_coord = SkyCoord(ra=src.get_ra_degrees()*u.deg, dec=src.get_dec_degrees()*u.deg, frame='icrs')
                        altaz_src = src_coord.transform_to(altaz_frame)
                        ax.scatter(altaz_src.az.deg, altaz_src.alt.deg, s=50, label=f"{tel_code} {freq_key}: {src_name}")
                        if fov_center_az is None:
                            fov_center_az, fov_center_alt = altaz_src.az.deg, altaz_src.alt.deg
                    else:
                        logger.warning(f"Source '{src_name}' not found in active sources for FOV plot")
                
                fov_center_az = fov_center_az if fov_center_az is not None else 0
                fov_center_alt = fov_center_alt if fov_center_alt is not None else 0
                circle = plt.Circle((fov_center_az, fov_center_alt), radius, fill=False, label=f"{tel_code} {freq_key} FOV")
                ax.add_patch(circle)

        ax.set_xlabel("Azimuth (deg)")
        ax.set_ylabel("Altitude (deg)")
        ax.set_title(f"Field of View at {time.iso}")
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True)
        canvas.draw()

    def plot_sensitivity(self, sensitivity_data: Dict[str, float], ylabel: str, title: str, canvas: FigureCanvas) -> None:
        """Plot sensitivity data for telescopes or baselines on the provided canvas."""
        fig = canvas.figure
        fig.clf()
        ax = fig.add_subplot(111)
        keys = list(sensitivity_data.keys())
        values = [sensitivity_data[k] if sensitivity_data[k] is not None else 0 for k in keys]
        ax.bar(keys, values)
        ax.set_xlabel("Telescope / Baseline")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.tick_params(axis='x', rotation=45)
        canvas.draw()


class DefaultVizualizator(Vizualizator):
    """Default implementation of Vizualizator."""
    def visualize_observation(self, observation: Observation, plot_types: Optional[List[str]] = None) -> None:
        """Visualize selected calculated data for the observation."""
        check_type(observation, Observation, "Observation")
        if not hasattr(observation, '_calculated_data') or not observation._calculated_data:
            logger.error("No calculated data available for visualization")
            return

        all_plots = ["uv_coverage", "mollweide_tracks", "beam_pattern", "field_of_view"]
        plots_to_show = plot_types if plot_types else all_plots

        for scan_key, scan_data in observation._calculated_data.items():
            logger.info(f"Visualizing data for {scan_key}")
            if "uv_coverage" in plots_to_show and "uv_coverage" in scan_data and scan_data["uv_coverage"]:
                self.plot_uv_coverage(scan_data["uv_coverage"])
            if "mollweide_tracks" in plots_to_show and "mollweide_tracks" in scan_data and scan_data["mollweide_tracks"]:
                self.plot_mollweide_tracks(scan_data["mollweide_tracks"])
            if "beam_pattern" in plots_to_show and "beam_pattern" in scan_data and scan_data["beam_pattern"]:
                self.plot_beam_pattern(scan_data["beam_pattern"])
            if "field_of_view" in plots_to_show and "field_of_view" in scan_data and scan_data["field_of_view"]:
                self.plot_field_of_view(observation, scan_key, scan_data["field_of_view"])