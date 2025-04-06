from common.super.super import Super
from unit_scheduling.super.schedule_project import ScheduleProject
from unit_scheduling.base.observation import Observation
from unit_scheduling.base.telescopes import Telescope, SpaceTelescope, Telescopes
from unit_scheduling.base.sources import Source, Sources
from unit_scheduling.base.scans import Scan, Scans
from unit_scheduling.base.frequencies import IF, Frequencies
from common.utils.logging_setup import logger
from typing import Dict, Any, Callable, Union
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import numpy as np
from astropy.time import Time
import threading
import os
import seaborn as sns
import astropy.units as u
from matplotlib.colors import LinearSegmentedColormap
import warnings
from erfa import ErfaWarning

warnings.filterwarnings("ignore", category=ErfaWarning)

class ScheduleVisualizer(Super):
    """Scheduler implementation of Visualizer for visualizing ScheduleProject and its components.

    Provides a suite of visualization methods for astronomical scheduling objects, generating plots such as UV coverage,
    source visibility, and beam patterns. Supports multi-threading for project-level visualization and customizable
    output options (e.g., saving to file, displaying plots).

    Attributes:
        manipulator: The Manipulator instance used to manage object interactions.
        _lock (threading.Lock): Thread lock for thread-safe plotting.
        moderate2_colors (List[tuple]): Custom color palette for plotting.
        redpurple_cmap: Custom colormap for synthesized beam plots.
        _object_visualizers (Dict[type, Callable]): Mapping of object types to visualization methods.
        _plot_types (Dict[str, Callable]): Mapping of plot types to plotting functions.

    Examples:
        >>> from unit_scheduling.super.manipulator import ScheduleManipulator
        >>> manipulator = ScheduleManipulator()
        >>> visualizer = ScheduleVisualizer(manipulator)
        >>> obs = Observation()
        >>> result = visualizer.visualize(obs, {"plot_type": "uv_coverage", "freq_idx": 0})
        {'status': 'success', 'baselines': 3}
    """
    def __init__(self, manipulator: 'Manipulator'):
        """Initialize the ScheduleVisualizer with plotting settings and operation mappings.

        Args:
            manipulator: The Manipulator instance for managing object interactions.

        Notes:
            - Sets up Matplotlib with a custom style (seaborn-v0_8-whitegrid) and font (Trebuchet MS).
            - Defines a custom color palette (moderate2_colors) and a red-purple colormap (redpurple_cmap).
            - Registers visualization methods for object types and plot types.
            - Initializes a thread lock for safe plotting.
            - Logs initialization upon completion.
        """
        super().__init__(manipulator)
        self._lock = threading.Lock()
        logger.info("Initialized Scheduling Visualizer")

        plt.style.use('seaborn-v0_8-whitegrid')
        plt.rc('axes', facecolor='white', edgecolor='black', labelcolor='black')
        plt.rc('xtick', color='black')
        plt.rc('ytick', color='black')
        plt.rc('grid', color='lightgray', linestyle='--', linewidth=0.5)
        plt.rc('font', family='Trebuchet MS', size=12)
        plt.rc('text', color='black')
        plt.rc('figure', facecolor='white')

        self.moderate2_colors = [
            (163/255, 193/255, 218/255),
            (74/255, 144/255, 226/255),
            (80/255, 200/255, 120/255),
            (46/255, 139/255, 87/255),
            (255/255, 99/255, 71/255),
            (255/255, 165/255, 0/255),
            (255/255, 140/255, 0/255),
            (218/255, 112/255, 214/255),
            (255/255, 215/255, 0/255),
            (139/255, 69/255, 19/255),
        ]
        self.intersection_color = (255/255, 165/255, 0/255)

        redpurple_colors = [
            (139/255, 0/255, 0/255),
            (255/255, 69/255, 0/255),
            (255/255, 255/255, 0/255),
            (0/255, 255/255, 0/255),
            (0/255, 206/255, 209/255),
            (0/255, 0/255, 139/255),
        ]

        redpurple_colors = redpurple_colors[::-1]
        self.redpurple_cmap = LinearSegmentedColormap.from_list("RedPurple", redpurple_colors)

        self._object_visualizers: Dict[type, Callable] = {
            (ScheduleProject, Observation): self._visualize_project_or_observation,
            (Telescope, SpaceTelescope, Telescopes): self._visualize_telescopes,
            (Source, Sources): self._visualize_sources,
            (Scan, Scans): self._visualize_scans,
            (IF, Frequencies): self._visualize_frequencies,
        }

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
        """Return the default result when no visualization is performed.

        Returns:
            Dict[str, Any]: A dictionary with a status message indicating no visualization occurred.
        """
        return {"status": "no visualization performed"}

    def _visualize(self, obj: Union[ScheduleProject, Observation, Telescope, SpaceTelescope, Telescopes, Source, Sources, Scan, Scans, IF, Frequencies], 
               attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Visualize the specified object based on provided attributes.

        Args:
            obj: The object to visualize (e.g., ScheduleProject, Observation, Telescope, etc.).
            attributes (Dict[str, Any]): Dictionary specifying visualization parameters (e.g., "plot_type", "output_file", "show").

        Returns:
            Dict[str, Any]: Result of the visualization, including status and additional data (e.g., {"status": "success", "baselines": 3}).

        Raises:
            ValueError: If the object type is not supported.

        Notes:
            - Requires a "plot_type" in attributes to proceed.
            - Supports saving to file and showing plots based on attributes.
            - Handles exceptions and ensures figures are closed on failure.
        """
        plot_type = attributes.get("plot_type")
        output_file = attributes.get("output_file")
        show = attributes.get("show", True)

        if not plot_type:
            logger.error("No 'plot_type' specified in attributes")
            return {"status": "error", "message": "plot_type required"}

        fig = None if plot_type in ["time_on_source", "beam_pattern", "synthesized_beam", "az_el"] else plt.figure(figsize=attributes.get("figsize", (10, 6)))
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
                if not output_file.strip():
                    logger.warning("Empty output_file provided, skipping save")
                else:
                    output_dir = os.path.dirname(output_file)
                    if output_dir:
                        os.makedirs(output_dir, exist_ok=True)
                    plt.savefig(output_file, dpi=attributes.get("dpi", 300), bbox_inches='tight')
                    logger.info(f"Visualization saved to '{output_file}'")
            if show:
                plt.show()
            else:
                plt.close(fig if fig else plt.gcf())
        except Exception as e:
            logger.error(f"Visualization failed: {str(e)}")
            result = {"status": "error", "message": str(e)}
            plt.close(fig if fig else plt.gcf())

        return result

    def _visualize_project_or_observation(self, obj: Union[ScheduleProject, Observation], attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Visualize a ScheduleProject or Observation object.

        Args:
            obj (ScheduleProject | Observation): The object to visualize.
            attributes (Dict[str, Any]): Visualization parameters, including "plot_type".

        Returns:
            Dict[str, Any]: Visualization result, including status and data specific to the plot type.

        Notes:
            - For ScheduleProject, processes all observations in parallel using ThreadPoolExecutor.
            - For Observation, delegates to the appropriate plot function based on "plot_type".
        """
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

        plot_func = self._plot_types.get(plot_type)
        if not plot_func:
            logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
            return {"status": "error", "message": f"Unsupported plot_type: {plot_type}"}
        
        return plot_func(obj, attributes)

    def _plot_uv_coverage(self, obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Plot UV coverage for an Observation.

        Args:
            obj (Observation): The Observation object to visualize.
            attributes (Dict[str, Any]): Parameters including "freq_idx" (default 0) and "store_key".

        Returns:
            Dict[str, Any]: Result with status and number of baselines plotted.

        Notes:
            - Plots UV points in wavelength units, including mirrored points for symmetry.
            - Uses pre-calculated data from the observation's store_key.
        """
        freq_idx = attributes.get("freq_idx", 0)
        store_key = attributes.get("store_key", f"uv_coverage_f{freq_idx}")
        data = obj.get_calculated_data_by_key(store_key)
        if not data:
            logger.error(f"No UV coverage data found for '{store_key}' in {obj.get_observation_code()}")
            return {"status": "error", "message": f"No data for {store_key}"}

        frequency = obj.get_frequencies().get_by_index(freq_idx).get_frequency() * 1e6
        data = data.get("data", {})
        
        baselines = {}
        for scan_data in data.values():
            uv_points = scan_data.get("uv_points", {}).get(frequency, [])
            for point in uv_points:
                try:
                    baseline, u, v, *_ = point
                    if baseline not in baselines:
                        baselines[baseline] = {"u": [], "v": []}
                    baselines[baseline]["u"].append(float(u))
                    baselines[baseline]["v"].append(float(v))
                except (ValueError, TypeError) as e:
                    logger.error(f"Invalid UV point format: {point}, error: {str(e)}")
                    return {"status": "error", "message": f"Invalid UV point format: {point}"}

        for i, (baseline, coords) in enumerate(baselines.items()):
            color = self.moderate2_colors[i % len(self.moderate2_colors)]
            plt.scatter(coords["u"], coords["v"], s=1, c=[color], label=f"{baseline}")
            plt.scatter([-u for u in coords["u"]], [-v for v in coords["v"]], s=1, c=[color])

        plt.xlabel('u (wavelengths)')
        plt.ylabel('v (wavelengths)')
        plt.title(f"UV Coverage at {frequency/1e6:.1f} MHz")
        plt.grid(True)
        plt.legend()
        return {"status": "success", "baselines": len(baselines)}

    def _plot_source_visibility(self, obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Plot source visibility over time for an Observation.

        Args:
            obj (Observation): The Observation object to visualize.
            attributes (Dict[str, Any]): Parameters including "store_key".

        Returns:
            Dict[str, Any]: Result with status and number of scans plotted.

        Notes:
            - Plots visibility (1 = visible, 0 = not visible) against MJD time for each telescope.
        """
        store_key = attributes.get("store_key", "source_visibility")
        data = obj.get_calculated_data_by_key(store_key)
        if not data:
            logger.error(f"No source visibility data found for '{store_key}' in {obj.get_observation_code()}")
            return {"status": "error", "message": f"No data for {store_key}"}

        data = data.get("data", {})
        for scan_idx, scan_data in data.items():
            times = [Time(t).mjd for t in scan_data.get("times", []) if t]
            visibility = scan_data.get("visibility", {})
            source = scan_data.get("source")
            for i, (tel_code, vis) in enumerate(visibility.items()):
                valid_pairs = [(t, float(v)) for t, v in zip(times, vis) if v is not None]
                if valid_pairs:
                    times_mjd, vis_valid = zip(*valid_pairs)
                    plt.plot(times_mjd, vis_valid, label=f"{tel_code}", marker='o' if not attributes.get("time_step") else None,
                             color=self.moderate2_colors[i % len(self.moderate2_colors)])
        
        plt.xlabel("Time (MJD)")
        plt.ylabel("Visible (1 = Yes, 0 = No)")
        plt.title(f"Source Visibility for {source}")
        plt.legend()
        plt.grid(True)
        return {"status": "success", "scans": len(data)}

    def _plot_sun_angles(self, obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Plot angles to the Sun for an Observation.

        Args:
            obj (Observation): The Observation object to visualize.
            attributes (Dict[str, Any]): Parameters including "store_key".

        Returns:
            Dict[str, Any]: Result with status and number of scans plotted.

        Notes:
            - Plots Sun angles in degrees against MJD time for each telescope.
        """
        store_key = attributes.get("store_key", "sun_angles")
        data = obj.get_calculated_data_by_key(store_key)
        if not data:
            logger.error(f"No sun angles data found for '{store_key}' in {obj.get_observation_code()}")
            return {"status": "error", "message": f"No data for {store_key}"}

        data = data.get("data", {})
        for scan_idx, scan_data in data.items():
            times = [Time(t) for t in scan_data.get("times", []) if t]
            angles = scan_data.get("sun_angles", {})
            source = scan_data.get("source")
            for i, (tel_code, angle_list) in enumerate(angles.items()):
                valid_pairs = [(t.mjd, float(a)) for t, a in zip(times, angle_list) if a is not None]
                if valid_pairs:
                    times_mjd, angles_sorted = zip(*sorted(valid_pairs))
                    plt.plot(times_mjd, angles_sorted, label=f"{tel_code}", color=self.moderate2_colors[i % len(self.moderate2_colors)])
            
        plt.xlabel("Time (MJD)")
        plt.ylabel("Angle to Sun (degrees)")
        plt.title(f"Sun Angles for Source {source}")
        plt.legend()
        plt.grid(True)
        return {"status": "success", "scans": len(data)}

    def _plot_az_el(self, obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Plot Azimuth/Elevation or Hour Angle/Declination for an Observation.

        Args:
            obj (Observation): The Observation object to visualize.
            attributes (Dict[str, Any]): Parameters including "store_key".

        Returns:
            Dict[str, Any]: Result with status and number of scans plotted.

        Notes:
            - Creates subplots for each telescope, showing Az/El or HA/Dec over MJD time.
        """
        store_key = attributes.get("store_key", "az_el")
        data = obj.get_calculated_data_by_key(store_key)
        if not data:
            logger.error(f"No Az/El data found for '{store_key}' in {obj.get_observation_code()}")
            return {"status": "error", "message": f"No data for {store_key}"}

        data = data.get("data", {})
        source = None
        all_telescopes = {}
        for scan_idx, scan_data in data.items():
            times = [Time(t) for t in scan_data.get("times", []) if t]
            az_el = scan_data.get("az_el", {})
            source = scan_data.get("source")
            for tel_code, coords in az_el.items():
                if tel_code not in all_telescopes:
                    all_telescopes[tel_code] = {"times": [], "az": [], "el": [], "coord_type": coords.get("coord_type", "AzEl")}
                valid_az = [(t.mjd, float(c)) for t, c in zip(times, coords["coord1"]) if c is not None]
                valid_el = [(t.mjd, float(c)) for t, c in zip(times, coords["coord2"]) if c is not None]
                if valid_az and valid_el:
                    times_az, az = zip(*sorted(valid_az))
                    times_el, el = zip(*sorted(valid_el))
                    all_telescopes[tel_code]["times"].extend(times_az)
                    all_telescopes[tel_code]["az"].extend(az)
                    all_telescopes[tel_code]["el"].extend(el)

        n_tels = len(all_telescopes)
        if n_tels == 0:
            logger.warning(f"No valid Az/El data for {obj.get_observation_code()}")
            return {"status": "no data"}

        fig, axes = plt.subplots(n_tels, 1, figsize=(10, 3 * n_tels), sharex=False, sharey=False)
        if n_tels == 1:
            axes = [axes]

        for i, (tel_code, data) in enumerate(all_telescopes.items()):
            ax = axes[i] if n_tels > 1 else axes
            color = self.moderate2_colors[i % len(self.moderate2_colors)]
            coord_type = data["coord_type"]
            ax.plot(data["times"], data["az"], label=f"{coord_type[:2]}", color=color)
            ax.plot(data["times"], data["el"], label=f"{coord_type[2:]}", linestyle='--', color=color)
            ax.set_xlabel("Time, (MJD)")
            ax.set_ylabel("Angle, (deg)")
            ax.set_title(f"Telescope: {tel_code}")
            ax.legend(loc='upper right')
            ax.grid(True)

        fig.suptitle(f"Az/El or HA/Dec for {source}", y=1.02)
        plt.tight_layout()
        return {"status": "success", "scans": len(data)}

    def _plot_time_on_source(self, obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Plot time on source for an Observation.

        Args:
            obj (Observation): The Observation object to visualize.
            attributes (Dict[str, Any]): Parameters including "store_key".

        Returns:
            Dict[str, Any]: Result with status and number of telescopes plotted.

        Notes:
            - Visualizes time blocks per telescope and highlights intersection periods.
        """
        store_key = attributes.get("store_key", "time_on_source")
        data = obj.get_calculated_data_by_key(store_key)
        if not data:
            logger.error(f"No time on source data found for '{store_key}' in {obj.get_observation_code()}")
            return {"status": "error", "message": f"No data for {store_key}"}

        data = data.get("data", {})
        telescopes = set()
        all_blocks = {}
        source_name = None
        for source, source_data in data.items():
            source_name = source
            for tel, blocks in source_data["telescopes"].items():
                telescopes.add(tel)
                if tel not in all_blocks:
                    all_blocks[tel] = []
                all_blocks[tel].extend(blocks)

        telescopes = sorted(telescopes)
        fig, ax = plt.subplots(figsize=(12, len(telescopes)))

        for i, tel in enumerate(telescopes):
            for block in all_blocks.get(tel, []):
                start = Time(block["start"]).mjd
                end = Time(block["start"]) + block["duration"] * u.s
                end = end.mjd
                ax.fill_between([start, end], [i, i], [i + 1, i + 1], color=self.moderate2_colors[i % len(self.moderate2_colors)], alpha=0.5)

        all_times = [[] for _ in range(len(telescopes))]
        for i, tel in enumerate(telescopes):
            for block in all_blocks.get(tel, []):
                all_times[i].append((Time(block["start"]).mjd, (Time(block["start"]) + block["duration"] * u.s).mjd))
        
        intersections = []
        for t in sorted(set(t for tel_times in all_times for start, end in tel_times for t in (start, end))):
            active = [sum(1 for start, end in tel_times if start <= t <= end) for tel_times in all_times]
            if all(a == 1 for a in active):
                intersections.append(t)
        
        for i in range(0, len(intersections), 2):
            if i + 1 < len(intersections):
                start, end = intersections[i], intersections[i + 1]
                ax.fill_between([start, end], [-1, -1], [0, 0], color=self.intersection_color, alpha=0.7)

        ax.set_yticks(np.arange(-1, len(telescopes)))
        ax.set_yticklabels(["Total Intersection"] + telescopes)
        ax.set_xlabel("Time (MJD)")
        ax.set_ylabel("Telescope")
        ax.set_title(f"Time on Source ({source_name})")
        ax.grid(True, axis="x")
        return {"status": "success", "telescopes": len(telescopes)}

    def _plot_beam_pattern(self, obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Plot beam patterns for an Observation.

        Args:
            obj (Observation): The Observation object to visualize.
            attributes (Dict[str, Any]): Parameters including "freq_idx" (default 0) and "store_key".

        Returns:
            Dict[str, Any]: Result with status and number of telescopes plotted.

        Notes:
            - Plots normalized beam patterns against theta (radians) for each telescope.
        """
        freq_idx = attributes.get("freq_idx", 0)
        store_key = attributes.get("store_key", f"beam_pattern_f{freq_idx}")
        data = obj.get_calculated_data_by_key(store_key)
        if not data:
            logger.error(f"No beam pattern data found for '{store_key}' in {obj.get_observation_code()}")
            return {"status": "error", "message": f"No data for {store_key}"}

        data = data.get("data", {})
        n_tels = len(data)
        fig, axes = plt.subplots(n_tels, 1, figsize=(10, 3 * n_tels), sharex=False, sharey=False)

        if n_tels == 1:
            axes = [axes]

        for i, (tel_code, beam_data) in enumerate(data.items()):
            theta = np.array(beam_data["theta"])
            pattern = beam_data["pattern"]
            ax = axes[i]
            ax.plot(theta, pattern, label=tel_code, color=self.moderate2_colors[i % len(self.moderate2_colors)])
            
            theta_range = np.max(np.abs(theta)) * 0.05
            ax.set_xlim(-theta_range, theta_range)
            
            ax.set_title(f"Beam Pattern for {tel_code}")
            ax.grid(True)

        fig.text(0.04, 0.5, "Normalized Peak Flux, (Jy)", va='center', rotation='vertical')
        axes[-1].set_xlabel("Theta (radians)")
        plt.tight_layout()
        plt.subplots_adjust(left=0.15)
        return {"status": "success", "telescopes": len(data)}

    def _plot_synthesized_beam(self, obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Plot the synthesized beam for an Observation.

        Args:
            obj (Observation): The Observation object to visualize.
            attributes (Dict[str, Any]): Parameters including "freq_idx" (default 0) and "store_key".

        Returns:
            Dict[str, Any]: Result with status.

        Notes:
            - Displays a 2D beam pattern in microarcseconds using a custom red-purple colormap.
        """
        freq_idx = attributes.get("freq_idx", 0)
        store_key = attributes.get("store_key", f"synthesized_beam_f{freq_idx}")
        data = obj.get_calculated_data_by_key(store_key)
        if not data:
            logger.error(f"No synthesized beam data found for '{store_key}' in {obj.get_observation_code()}")
            return {"status": "error", "message": f"No data for {store_key}"}

        data = data.get("data", {})
        scan_data = data.get(0, {})
        theta_u = np.array(scan_data.get("theta_u", []))
        theta_v = np.array(scan_data.get("theta_v", []))
        beam_2d = scan_data.get("beam_2d", np.zeros((len(theta_v), len(theta_u))))

        if len(theta_u) == 0 or len(theta_v) == 0:
            logger.error(f"Missing or empty data for 'theta_u' or 'theta_v' in {obj.get_observation_code()}")
            return {"status": "error", "message": "Missing or empty data for theta_u or theta_v"}

        theta_u_muas = theta_u * 3.6e9
        theta_v_muas = theta_v * 3.6e9

        figsize = attributes.get("figsize", (10, 10))
        fig, ax = plt.subplots(figsize=figsize)

        im = ax.imshow(beam_2d, extent=[min(theta_u_muas), max(theta_u_muas), min(theta_v_muas), max(theta_v_muas)], 
                    cmap=self.redpurple_cmap, aspect='equal')

        u_range = max(theta_u_muas) - min(theta_u_muas)
        v_range = max(theta_v_muas) - min(theta_v_muas)
        max_range = max(u_range, v_range) * 1.1
        
        u_center = (max(theta_u_muas) + min(theta_u_muas)) / 2
        v_center = (max(theta_v_muas) + min(theta_v_muas)) / 2
        
        ax.set_xlim(u_center - max_range / 2, u_center + max_range / 2)
        ax.set_ylim(v_center - max_range / 2, v_center + max_range / 2)

        plt.colorbar(im, label='Normalized Peak Flux, (Jy)', ax=ax)
        ax.set_xlabel("Relative Right Ascension, (μas)")
        ax.set_ylabel("Relative Declination, (μas)")
        ax.set_title(f"Synthesized Beam at {obj.get_frequencies().get_by_index(freq_idx).get_frequency()} MHz")
        
        plt.tight_layout()
        return {"status": "success"}

    def _plot_baseline_projections(self, obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Plot baseline projections for an Observation.

        Args:
            obj (Observation): The Observation object to visualize.
            attributes (Dict[str, Any]): Parameters including "freq_idx" (default 0) and "store_key".

        Returns:
            Dict[str, Any]: Result with status and number of scans plotted.

        Notes:
            - Plots baseline lengths in wavelengths against MJD time for each telescope pair.
        """
        freq_idx = attributes.get("freq_idx", 0)
        store_key = attributes.get("store_key", f"baseline_projections_f{freq_idx}")
        data = obj.get_calculated_data_by_key(store_key)
        if not data:
            logger.error(f"No baseline projections data found for '{store_key}' in {obj.get_observation_code()}")
            return {"status": "error", "message": f"No data for {store_key}"}

        frequency = obj.get_frequencies().get_by_index(freq_idx).get_frequency()
        data = data.get("data", {})
        
        for scan_idx, scan_data in data.items():
            times = scan_data.get("times", [])
            projections = scan_data.get("projections", {})
            for i, (pair, bl_list) in enumerate(projections.items()):
                valid_pairs = [(Time(t).mjd, float(bl)) for t, bl in zip(times, bl_list) if t and bl is not None]
                if valid_pairs:
                    times_mjd, bl_valid = zip(*valid_pairs)
                    plt.plot(times_mjd, bl_valid, label=pair, color=self.moderate2_colors[i % len(self.moderate2_colors)])
                else:
                    logger.debug(f"No valid projection data for {pair} in scan {scan_idx}")

        plt.xlabel("Time (MJD)")
        plt.ylabel("Baseline Length (wavelengths)")
        plt.title(f"Baseline Projections at {frequency} MHz")
        plt.legend()
        plt.grid(True)
        return {"status": "success", "scans": len(data)}

    def _plot_mollweide_tracks(self, obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Plot Mollweide tracks for an Observation.

        Args:
            obj (Observation): The Observation object to visualize.
            attributes (Dict[str, Any]): Parameters including "store_key".

        Returns:
            Dict[str, Any]: Result with status and number of scans plotted.

        Notes:
            - Displays telescope tracks and source position in a Mollweide projection.
        """
        store_key = attributes.get("store_key", "mollweide_tracks")
        data = obj.get_calculated_data_by_key(store_key)
        if not data:
            logger.error(f"No Mollweide tracks data found for '{store_key}' in {obj.get_observation_code()}")
            return {"status": "error", "message": f"No data for {store_key}"}

        data = data.get("data", {})
        ax = plt.subplot(111, projection="mollweide")
        for scan_idx, scan_data in data.items():
            tracks = scan_data.get("telescope_tracks", {})
            for i, (tel_code, track) in enumerate(tracks.items()):
                ax.scatter(np.radians(track["lon"]), np.radians(track["lat"]), 
                           c=[self.moderate2_colors[i % len(self.moderate2_colors)]], label=tel_code, s=0.1, zorder=1)
                
            source = scan_data["source"]
            ax.scatter(np.radians(source["lon"]), np.radians(source["lat"]), c='red', marker='o', 
                       label=f"Source: {source['name']}", s=10, zorder=2)
        
        ax.set_title("Mollweide Tracks")
        ax.grid(True)
        ax.legend(loc='upper right', bbox_to_anchor=(1.15, 1))
        return {"status": "success", "scans": len(data)}

    def _visualize_telescopes(self, obj: Union[Telescope, SpaceTelescope, Telescopes], attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Visualize Telescope-related objects.

        Args:
            obj (Telescope | SpaceTelescope | Telescopes): The telescope object(s) to visualize.
            attributes (Dict[str, Any]): Parameters including "plot_type".

        Returns:
            Dict[str, Any]: Result with status and number of telescopes plotted.

        Notes:
            - Supports "positions" plot type, showing 3D coordinates of telescopes.
        """
        plot_type = attributes.get("plot_type")
        if plot_type == "positions":
            if isinstance(obj, Telescopes):
                tels = obj.get_active_telescopes()
            else:
                tels = [obj]
            x, y, z = zip(*[tel.get_coordinates() for tel in tels])
            ax = plt.axes(projection='3d')
            for i in range(len(tels)):
                ax.scatter(x[i], y[i], z[i], c=[self.moderate2_colors[i % len(self.moderate2_colors)]], label=tels[i].get_code())
            ax.set_xlabel("X, (m)")
            ax.set_ylabel("Y, (m)")
            ax.set_zlabel("Z, (m)")
            ax.set_title("Telescope Positions")
            ax.legend()
            return {"status": "success", "telescopes": len(tels)}
        logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
        return {"status": "error", "message": f"Unsupported plot_type: {plot_type}"}

    def _visualize_sources(self, obj: Union[Source, Sources], attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Visualize Source-related objects.

        Args:
            obj (Source | Sources): The source object(s) to visualize.
            attributes (Dict[str, Any]): Parameters including "plot_type".

        Returns:
            Dict[str, Any]: Result with status and number of sources plotted.

        Notes:
            - Supports "sky_position" plot type, showing RA/Dec coordinates.
        """
        plot_type = attributes.get("plot_type")
        if plot_type == "sky_position":
            if isinstance(obj, Sources):
                sources = obj.get_items()
            else:
                sources = [obj]
            ra = [s.get_ra_degrees() for s in sources]
            dec = [s.get_dec_degrees() for s in sources]
            for i in range(len(sources)):
                plt.scatter(ra[i], dec[i], c=[self.moderate2_colors[i % len(self.moderate2_colors)]], label=f"Source {i}")
            plt.xlabel("Relative Right Ascencion, (deg)")
            plt.ylabel("Relative Declination, (deg)")
            plt.title("Source(s) Sky Position")
            plt.grid(True)
            plt.legend()
            return {"status": "success", "sources": len(sources)}
        logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
        return {"status": "error", "message": f"Unsupported plot_type: {plot_type}"}

    def _visualize_scans(self, obj: Union[Scan, Scans], attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Visualize Scan-related objects.

        Args:
            obj (Scan | Scans): The scan object(s) to visualize.
            attributes (Dict[str, Any]): Parameters including "plot_type".

        Returns:
            Dict[str, Any]: Result with status and number of scans plotted.

        Notes:
            - Supports "timeline" plot type, showing scan durations over MJD time.
        """
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
                plt.plot([Time(start).mjd, Time(end).mjd], [i, i], label=f"Scan {i}", 
                         color=self.moderate2_colors[i % len(self.moderate2_colors)])
            plt.xlabel("Time, (MJD)")
            plt.ylabel("Scan Index")
            plt.title("Scan Timeline")
            plt.grid(True)
            return {"status": "success", "scans": len(scans)}
        logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
        return {"status": "error", "message": f"Unsupported plot_type: {plot_type}"}

    def _visualize_frequencies(self, obj: Union[IF, Frequencies], attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Visualize Frequency-related objects.

        Args:
            obj (IF | Frequencies): The frequency object(s) to visualize.
            attributes (Dict[str, Any]): Parameters including "plot_type".

        Returns:
            Dict[str, Any]: Result with status and number of frequencies plotted.

        Notes:
            - Supports "spectrum" plot type, showing frequency and bandwidth as bars.
        """
        plot_type = attributes.get("plot_type")
        if plot_type == "spectrum":
            if isinstance(obj, Frequencies):
                freqs = obj.get_items()
            else:
                freqs = [obj]
            frequencies = [f.get_frequency() for f in freqs]
            bandwidths = [f.get_bandwidth() for f in freqs]
            for i in range(len(frequencies)):
                plt.bar(frequencies[i], bandwidths[i], width=0.1, align='center', 
                        color=self.moderate2_colors[i % len(self.moderate2_colors)])
            plt.xlabel("Frequency, (MHz)")
            plt.ylabel("Bandwidth, (MHz)")
            plt.title("Frequency Spectrum")
            plt.grid(True)
            return {"status": "success", "frequencies": len(frequencies)}
        logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
        return {"status": "error", "message": f"Unsupported plot_type: {plot_type}"}