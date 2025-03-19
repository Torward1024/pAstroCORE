# super/vizualizator.py
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
import numpy as np
import matplotlib.pyplot as plt
from base.observation import Observation
from base.sources import Source
from utils.validation import check_type
from utils.logging_setup import logger
from astropy.coordinates import SkyCoord, AltAz
from astropy.time import Time
from astropy import units as u


class Vizualizator(ABC):
    """Abstract base class for visualizing observation data."""
    @abstractmethod
    def visualize_observation(self, observation: Observation) -> None:
        """Visualize the observation data."""
        pass

    def plot_uv_coverage(self, uv_coverage: Dict[Tuple[str, str], List[Tuple[float, float]]], filename: Optional[str] = None) -> None:
        """Plot u,v coverage for VLBI."""
        plt.figure(figsize=(8, 8))
        for (tel1, tel2), points in uv_coverage.items():
            u_vals, v_vals = zip(*points)
            plt.scatter(u_vals, v_vals, label=f"{tel1}-{tel2}", s=5)
            plt.scatter([-u for u in u_vals], [-v for v in v_vals], s=5)  # Symmetry
        plt.xlabel("u (m)")
        plt.ylabel("v (m)")
        plt.title("u,v Coverage")
        plt.legend()
        plt.grid(True)
        if filename:
            plt.savefig(filename)
            logger.info(f"Saved u,v coverage plot to '{filename}'")
        else:
            plt.show()
        plt.close()

    def plot_mollweide_tracks(self, tracks: Dict[str, List[Tuple[float, float]]], filename: Optional[str] = None) -> None:
        """Plot Mollweide tracks for telescopes."""
        plt.figure(figsize=(10, 6))
        for tel_code, track in tracks.items():
            x_vals, y_vals = zip(*track)
            plt.plot(x_vals, y_vals, label=tel_code)
        plt.xlabel("x (Mollweide)")
        plt.ylabel("y (Mollweide)")
        plt.title("Mollweide Tracks")
        plt.legend()
        plt.grid(True)
        if filename:
            plt.savefig(filename)
            logger.info(f"Saved Mollweide tracks plot to '{filename}'")
        else:
            plt.show()
        plt.close()

    def plot_beam_pattern(self, beam_patterns: Dict[str, np.ndarray], filename: Optional[str] = None) -> None:
        """Plot beam patterns for telescopes or baselines."""
        plt.figure(figsize=(8, 6))
        theta = np.linspace(-1, 1, 100)  # Assuming 100 points from -1 to 1 deg
        for tel_code, pattern in beam_patterns.items():
            plt.plot(theta, pattern, label=tel_code)
        plt.xlabel("Angle (deg)")
        plt.ylabel("Normalized Response")
        plt.title("Beam Pattern")
        plt.legend()
        plt.grid(True)
        if filename:
            plt.savefig(filename)
            logger.info(f"Saved beam pattern plot to '{filename}'")
        else:
            plt.show()
        plt.close()

    def plot_field_of_view(self, observation: Observation, scan_key: str, fov_data: Dict[str, Dict[str, Dict]], 
                          filename: Optional[str] = None) -> None:
        """Plot field of view with sources and Sun position for a specific scan."""
        plt.figure(figsize=(10, 10))
        scan_start = float(scan_key.split('_')[1])  # Extract start time from scan_key
        time = Time(scan_start, format='unix')
        
        for tel_code, freq_data in fov_data.items():
            loc = EarthLocation(x=observation.get_telescopes().get_telescope_by_code(tel_code).get_telescope_coordinates()[0]*u.m,
                               y=observation.get_telescopes().get_telescope_by_code(tel_code).get_telescope_coordinates()[1]*u.m,
                               z=observation.get_telescopes().get_telescope_by_code(tel_code).get_telescope_coordinates()[2]*u.m)
            altaz_frame = AltAz(obstime=time, location=loc)
            
            for freq_key, data in freq_data.items():
                radius = data["fov_radius"]
                sun_alt, sun_az = data["sun_alt"], data["sun_az"]
                plt.scatter(sun_az, sun_alt, c='yellow', s=100, 
                           label="Sun" if tel_code == list(fov_data.keys())[0] and freq_key == list(freq_data.keys())[0] else "")
                
                # Plot actual source positions
                for src_name in data["sources"]:
                    src = next((s for s in observation.get_sources().get_active_sources() if s.get_name() == src_name), None)
                    if src:
                        src_coord = SkyCoord(ra=src.get_ra_degrees()*u.deg, dec=src.get_dec_degrees()*u.deg, frame='icrs')
                        altaz_src = src_coord.transform_to(altaz_frame)
                        plt.scatter(altaz_src.az.deg, altaz_src.alt.deg, s=50, label=f"{tel_code} {freq_key}: {src_name}")
                
                circle = plt.Circle((0, 0), radius, fill=False, label=f"{tel_code} {freq_key} FOV")
                plt.gca().add_patch(circle)

        plt.xlabel("Azimuth (deg)")
        plt.ylabel("Altitude (deg)")
        plt.title(f"Field of View at {time.iso}")
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True)
        if filename:
            plt.savefig(filename, bbox_inches='tight')
            logger.info(f"Saved FOV plot to '{filename}'")
        else:
            plt.show()
        plt.close()


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