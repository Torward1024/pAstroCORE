from common.super.super import Super
from unit_scheduling.super.schedule_project import ScheduleProject
from unit_scheduling.base.observation import Observation
from unit_scheduling.base.telescopes import Telescope, SpaceTelescope, Telescopes
from unit_scheduling.base.sources import Source, Sources
from unit_scheduling.base.scans import Scan, Scans
from unit_scheduling.base.frequencies import IF, Frequencies
from common.utils.logging_setup import logger
from typing import Dict, Any, Optional, Callable, Union
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import numpy as np
from astropy.time import Time
import threading
import os
import seaborn as sns
import astropy.units as u

class ScheduleVisualizer(Super):
    """Default implementation of Visualizer for visualizing Project and its components"""
    def __init__(self, manipulator: 'Manipulator'):
        super().__init__(manipulator)
        self._lock = threading.Lock()
        logger.info("Initialized Scheduling Visualizer")
        plt.style.use('seaborn-v0_8')

        # Словарь для методов визуализации по типу объекта
        self._object_visualizers: Dict[type, Callable] = {
            (ScheduleProject, Observation): self._visualize_project_or_observation,
            (Telescope, SpaceTelescope, Telescopes): self._visualize_telescopes,
            (Source, Sources): self._visualize_sources,
            (Scan, Scans): self._visualize_scans,
            (IF, Frequencies): self._visualize_frequencies,
        }

        # Словарь для методов визуализации по plot_type для Project/Observation
        self._plot_types: Dict[str, Callable] = {
            "uv_coverage": self._plot_uv_coverage,
            "source_visibility": self._plot_source_visibility,
            "sun_angles": self._plot_sun_angles,
            "az_el": self._plot_az_el,
            "time_on_source": self._plot_time_on_source,
            "beam_pattern": self._plot_beam_pattern,
            "synthesized_beam": self._plot_synthesized_beam,
            "baseline_projections": self._plot_baseline_projections,
            "mollweide_tracks": self._plot_mollweide_tracks,
        }

    def _default_result(self) -> Dict[str, Any]:
        return {"status": "no visualization performed"}

    def _visualize(self, obj: Union[ScheduleProject, Observation, Telescope, SpaceTelescope, Telescopes, Source, Sources, Scan, Scans, IF, Frequencies], 
               attributes: Dict[str, Any]) -> Dict[str, Any]:
        plot_type = attributes.get("plot_type")
        output_file = attributes.get("output_file")
        show = attributes.get("show", True)

        if not plot_type:
            logger.error("No 'plot_type' specified in attributes")
            return {"status": "error", "message": "plot_type required"}

        fig = plt.figure(figsize=attributes.get("figsize", (10, 6)))
        result = {}

        try:
            visualizer = None
            for types, func in self._object_visualizers.items():
                if isinstance(obj, types):
                    visualizer = func
                    break
            if not visualizer:
                raise ValueError(f"Unsupported object type: {type(obj)}")

            result = visualizer(obj, attributes)

            if output_file:
                if not output_file.strip():  # Проверка на пустую строку
                    logger.warning("Empty output_file provided, skipping save")
                else:
                    output_dir = os.path.dirname(output_file)
                    if output_dir:  # Если есть директория в пути
                        os.makedirs(output_dir, exist_ok=True)
                    plt.savefig(output_file, dpi=attributes.get("dpi", 300), bbox_inches='tight')
                    logger.info(f"Visualization saved to '{output_file}'")
            if show:
                plt.show()
            else:
                plt.close(fig)
        except Exception as e:
            logger.error(f"Visualization failed: {str(e)}")
            result = {"status": "error", "message": str(e)}
            plt.close(fig)

        return result

    def _visualize_project_or_observation(self, obj: Union[ScheduleProject, Observation], attributes: Dict[str, Any]) -> Dict[str, Any]:
        plot_type = attributes.get("plot_type")

        if isinstance(obj, ScheduleProject):
            observations = obj.get_observations()
            if not observations:
                logger.warning(f"No observations in ScheduleProject '{obj.get_name()}'")
                return {"status": "no data"}
            with ThreadPoolExecutor() as executor:
                futures = {executor.submit(self._visualize_project_or_observation, obs, attributes): obs.get_observation_code() for obs in observations}
                results = {code: future.result() for future, code in futures.items()}
            return {"status": "success", "observations": results}

        # Используем словарь для выбора метода визуализации
        plot_func = self._plot_types.get(plot_type)
        if not plot_func:
            logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
            return {"status": "error", "message": f"Unsupported plot_type: {plot_type}"}
        
        return plot_func(obj, attributes)

    def _plot_uv_coverage(self, obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        freq_idx = attributes.get("freq_idx", 0)
        store_key = attributes.get("store_key", f"uv_coverage_f{freq_idx}")
        data = obj.get_calculated_data_by_key(store_key)
        if not data:
            logger.error(f"No UV coverage data found for '{store_key}' in {obj.get_observation_code()}")
            return {"status": "error", "message": f"No data for {store_key}"}

        frequency = obj.get_frequencies().get_by_index(freq_idx).get_frequency() * 1e6
        data = data.get("data", {})

        u, v = [], []
        for scan_data in data.values():
            uv_points = scan_data.get("uv_points", {}).get(frequency, [])
            u.extend([p[1] for p in uv_points])
            v.extend([p[2] for p in uv_points])

        plt.scatter(u, v, s=1, c='blue', label='UV points')
        plt.scatter([-uu for uu in u], [-vv for vv in v], s=1, c='blue')
        plt.xlabel('u (wavelengths)')
        plt.ylabel('v (wavelengths)')
        plt.title(f"UV Coverage at {frequency/1e6:.1f} MHz")
        plt.grid(True)
        plt.legend()
        return {"status": "success", "u_points": len(u)}

    def _plot_source_visibility(self, obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        store_key = attributes.get("store_key", "source_visibility")
        data = obj.get_calculated_data_by_key(store_key)
        if not data:
            logger.error(f"No source visibility data found for '{store_key}' in {obj.get_observation_code()}")
            return {"status": "error", "message": f"No data for {store_key}"}

        data = data.get("data", {})
        for scan_idx, scan_data in data.items():
            times = [Time(t) for t in scan_data.get("times", [])]
            visibility = scan_data.get("visibility", {})
            source = scan_data.get("source")
            for tel_code, vis in visibility.items():
                plt.plot(times, vis, label=f"{tel_code}", marker='o' if not attributes.get("time_step") else None)
        
        plt.xlabel("Time (UTC)")
        plt.ylabel("Visible (1 = Yes, 0 = No)")
        plt.title(f"Source Visibility for {source}")
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        return {"status": "success", "scans": len(data)}

    def _plot_sun_angles(self, obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        store_key = attributes.get("store_key", "sun_angles")
        data = obj.get_calculated_data_by_key(store_key)
        if not data:
            logger.error(f"No sun angles data found for '{store_key}' in {obj.get_observation_code()}")
            return {"status": "error", "message": f"No data for {store_key}"}

        data = data.get("data", {})
        for scan_idx, scan_data in data.items():
            times = [Time(t) for t in scan_data.get("times", [])]
            angles = scan_data.get("sun_angles", {})
            source = scan_data.get("source")
            for tel_code, angle_list in angles.items():
                plt.plot(times, angle_list, label=f"{tel_code}")
        
        plt.xlabel("Time (UTC)")
        plt.ylabel("Angle to Sun (degrees)")
        plt.title(f"Sun Angles for Source {source}")
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        return {"status": "success", "scans": len(data)}

    def _plot_az_el(self, obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        store_key = attributes.get("store_key", "az_el")
        data = obj.get_calculated_data_by_key(store_key)
        if not data:
            logger.error(f"No Az/El data found for '{store_key}' in {obj.get_observation_code()}")
            return {"status": "error", "message": f"No data for {store_key}"}

        data = data.get("data", {})
        for scan_idx, scan_data in data.items():
            times = [Time(t) for t in scan_data.get("times", [])]
            az_el = scan_data.get("az_el", {})
            source = scan_data.get("source")
            for tel_code, coords in az_el.items():
                coord_type = coords.get("coord_type", "AzEl")
                plt.plot(times, coords["coord1"], label=f"{tel_code} {coord_type[:2]}")
                plt.plot(times, coords["coord2"], label=f"{tel_code} {coord_type[2:]}", linestyle='--')
        
        plt.xlabel("Time (UTC)")
        plt.ylabel("Angle (degrees)")
        plt.title(f"Az/El or HA/Dec for Source {source}")
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        return {"status": "success", "scans": len(data)}

    def _plot_time_on_source(self, obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        store_key = attributes.get("store_key", "time_on_source")
        data = obj.get_calculated_data_by_key(store_key)
        if not data:
            logger.error(f"No time on source data found for '{store_key}' in {obj.get_observation_code()}")
            return {"status": "error", "message": f"No data for {store_key}"}

        data = data.get("data", {})
        sources = list(data.keys())
        telescopes = set()
        for source_data in data.values():
            telescopes.update(source_data["telescopes"].keys())
        telescopes = list(telescopes)
        
        total_times = {tel: [] for tel in telescopes}
        for source in sources:
            for tel in telescopes:
                blocks = data[source]["telescopes"].get(tel, [])
                total_time = sum(block["duration"] for block in blocks)
                total_times[tel].append(total_time)
        
        x = np.arange(len(sources))
        width = 0.8 / len(telescopes)
        for i, tel in enumerate(telescopes):
            plt.bar(x + i * width, total_times[tel], width, label=tel)
        
        plt.xlabel("Source")
        plt.ylabel("Time on Source (s)")
        plt.title("Time on Source per Telescope")
        plt.xticks(x + width * (len(telescopes) - 1) / 2, sources)
        plt.legend()
        plt.grid(True)
        return {"status": "success", "sources": len(sources)}

    def _plot_beam_pattern(self, obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        freq_idx = attributes.get("freq_idx", 0)
        store_key = attributes.get("store_key", f"beam_pattern_f{freq_idx}")
        data = obj.get_calculated_data_by_key(store_key)
        if not data:
            logger.error(f"No beam pattern data found for '{store_key}' in {obj.get_observation_code()}")
            return {"status": "error", "message": f"No data for {store_key}"}

        data = data.get("data", {})
        for tel_code, beam_data in data.items():
            theta = beam_data["theta"]
            pattern = beam_data["pattern"]
            plt.plot(theta, pattern, label=tel_code)
        
        plt.xlabel("Theta (radians)")
        plt.ylabel("Normalized Power")
        plt.title(f"Beam Pattern at {obj.get_frequencies().get_by_index(freq_idx).get_frequency()} MHz")
        plt.legend()
        plt.grid(True)
        return {"status": "success", "telescopes": len(data)}

    def _plot_synthesized_beam(self, obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        freq_idx = attributes.get("freq_idx", 0)
        store_key = attributes.get("store_key", f"synthesized_beam_f{freq_idx}")
        data = obj.get_calculated_data_by_key(store_key)
        if not data:
            logger.error(f"No synthesized beam data found for '{store_key}' in {obj.get_observation_code()}")
            return {"status": "error", "message": f"No data for {store_key}"}

        data = data.get("data", {})
        scan_data = data.get(0, {})
        theta_u = scan_data.get("theta_u", [])
        theta_v = scan_data.get("theta_v", [])
        beam_2d = scan_data.get("beam_2d", np.zeros((len(theta_v), len(theta_u))))
        
        plt.imshow(beam_2d, extent=[min(theta_u), max(theta_u), min(theta_v), max(theta_v)], cmap='viridis', aspect='equal')
        plt.colorbar(label='Normalized Intensity')
        plt.xlabel("Theta_u (degrees)")
        plt.ylabel("Theta_v (degrees)")
        plt.title(f"Synthesized Beam at {obj.get_frequencies().get_by_index(freq_idx).get_frequency()} MHz")
        return {"status": "success"}

    def _plot_baseline_projections(self, obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        freq_idx = attributes.get("freq_idx", 0)
        store_key = attributes.get("store_key", f"baseline_projections_f{freq_idx}")
        data = obj.get_calculated_data_by_key(store_key)
        if not data:
            logger.error(f"No baseline projections data found for '{store_key}' in {obj.get_observation_code()}")
            return {"status": "error", "message": f"No data for {store_key}"}

        data = data.get("data", {})
        for scan_idx, scan_data in data.items():
            times = [Time(t) for t in scan_data.get("times", [])]
            projections = scan_data.get("projections", {})
            for pair, bl_list in projections.items():
                plt.plot(times, bl_list, label=pair)
        
        plt.xlabel("Time (UTC)")
        plt.ylabel("Baseline Length (wavelengths)")
        plt.title(f"Baseline Projections at {obj.get_frequencies().get_by_index(freq_idx).get_frequency()} MHz")
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        return {"status": "success", "scans": len(data)}

    def _plot_mollweide_tracks(self, obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        store_key = attributes.get("store_key", "mollweide_tracks")
        data = obj.get_calculated_data_by_key(store_key)
        if not data:
            logger.error(f"No Mollweide tracks data found for '{store_key}' in {obj.get_observation_code()}")
            return {"status": "error", "message": f"No data for {store_key}"}

        data = data.get("data", {})
        ax = plt.subplot(111, projection="mollweide")
        for scan_idx, scan_data in data.items():
            source = scan_data["source"]
            ax.plot(np.radians(source["lon"]), np.radians(source["lat"]), 'r*', label=f"Source: {source['name']}", markersize=10)
            tracks = scan_data.get("telescope_tracks", {})
            for tel_code, track in tracks.items():
                ax.plot(np.radians(track["lon"]), np.radians(track["lat"]), label=tel_code)
        
        ax.set_title("Mollweide Tracks")
        ax.grid(True)
        ax.legend(loc='upper right', bbox_to_anchor=(1.15, 1))
        return {"status": "success", "scans": len(data)}

    def _visualize_telescopes(self, obj: Union[Telescope, SpaceTelescope, Telescopes], attributes: Dict[str, Any]) -> Dict[str, Any]:
        plot_type = attributes.get("plot_type")
        if plot_type == "positions":
            if isinstance(obj, Telescopes):
                tels = obj.get_active_telescopes()
            else:
                tels = [obj]
            x, y, z = zip(*[tel.get_coordinates() for tel in tels])
            ax = plt.axes(projection='3d')
            ax.scatter(x, y, z)
            ax.set_xlabel("X (m)")
            ax.set_ylabel("Y (m)")
            ax.set_zlabel("Z (m)")
            ax.set_title("Telescope Positions")
            return {"status": "success", "telescopes": len(tels)}
        logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
        return {"status": "error", "message": f"Unsupported plot_type: {plot_type}"}

    def _visualize_sources(self, obj: Union[Source, Sources], attributes: Dict[str, Any]) -> Dict[str, Any]:
        plot_type = attributes.get("plot_type")
        if plot_type == "sky_position":
            if isinstance(obj, Sources):
                sources = obj.get_items()
            else:
                sources = [obj]
            ra = [s.get_ra_degrees() for s in sources]
            dec = [s.get_dec_degrees() for s in sources]
            plt.scatter(ra, dec, c='red', label='Sources')
            plt.xlabel("RA (degrees)")
            plt.ylabel("Dec (degrees)")
            plt.title("Source Positions on Sky")
            plt.grid(True)
            plt.legend()
            return {"status": "success", "sources": len(sources)}
        logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
        return {"status": "error", "message": f"Unsupported plot_type: {plot_type}"}

    def _visualize_scans(self, obj: Union[Scan, Scans], attributes: Dict[str, Any]) -> Dict[str, Any]:
        plot_type = attributes.get("plot_type")
        if plot_type == "timeline":
            if isinstance(obj, Scans):
                scans = obj.get_items()
            else:
                scans = [obj]
            starts = [s.get_start().isot for s in scans]
            durations = [s.get_duration() for s in scans]
            ends = [(Time(starts[i]) + durations[i] * u.s).isot for i in range(len(starts))]
            for i, (start, end) in enumerate(zip(starts, ends)):
                plt.plot([Time(start), Time(end)], [i, i], label=f"Scan {i}")
            plt.xlabel("Time (UTC)")
            plt.ylabel("Scan Index")
            plt.title("Scan Timeline")
            plt.grid(True)
            plt.xticks(rotation=45)
            return {"status": "success", "scans": len(scans)}
        logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
        return {"status": "error", "message": f"Unsupported plot_type: {plot_type}"}

    def _visualize_frequencies(self, obj: Union[IF, Frequencies], attributes: Dict[str, Any]) -> Dict[str, Any]:
        plot_type = attributes.get("plot_type")
        if plot_type == "spectrum":
            if isinstance(obj, Frequencies):
                freqs = obj.get_items()
            else:
                freqs = [obj]
            frequencies = [f.get_frequency() for f in freqs]
            bandwidths = [f.get_bandwidth() for f in freqs]
            plt.bar(frequencies, bandwidths, width=0.1, align='center')
            plt.xlabel("Frequency (MHz)")
            plt.ylabel("Bandwidth (MHz)")
            plt.title("Frequency Spectrum")
            plt.grid(True)
            return {"status": "success", "frequencies": len(frequencies)}
        logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
        return {"status": "error", "message": f"Unsupported plot_type: {plot_type}"}