# pastrocore/super/schedule_visualizer.py
from common.super.super import Super
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from pastrocore.base.telescopes import Telescope, SpaceTelescope, Telescopes
from pastrocore.base.sources import Source, Sources
from pastrocore.base.scans import Scan, Scans
from pastrocore.base.frequencies import IF, Frequencies
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
    """Scheduler implementation of Visualizer for visualizing ScheduleProject and its components."""
    
    def __init__(self, manipulator: 'Manipulator'):
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

    def execute(self, obj: Union[ScheduleProject, Observation, Telescope, SpaceTelescope, Telescopes, Source, Sources, Scan, Scans, IF, Frequencies], 
                attributes: Dict[str, Any] = None, method: str = None) -> Dict[str, Any]:
        """Execute visualization operation on the specified object.

        Args:
            obj: The object to visualize.
            attributes: Dictionary containing visualization parameters, including 'plot_type', 'output_file', 'show', and 'return_figure'.
            method: Optional explicit method to call.

        Returns:
            Dict containing the visualization result data or error message in standardized format.
        """
        if attributes is None:
            attributes = {}
        logger.debug(f"Executing visualization on {type(obj).__name__} with attributes={attributes}, method={method}")

        try:
            # If an explicit method is provided, use it
            if method:
                method_func = getattr(self, method, None)
                if callable(method_func):
                    result = method_func(obj, attributes)
                    return self._build_response(obj, True, method, result)

            # Check for method in attributes
            method_name = attributes.get("method")
            if method_name:
                method = getattr(self, method_name, None)
                if callable(method):
                    result = method(obj, attributes)
                    return self._build_response(obj, True, method_name, result)

                prefixed_method_name = f"_visualize_{method_name}"
                method = getattr(self, prefixed_method_name, None)
                if callable(method):
                    result = method(obj, attributes)
                    return self._build_response(obj, True, prefixed_method_name, result)

            # Try type-specific visualization method
            obj_type_name = type(obj).__name__.lower()
            auto_method_name = f"_visualize_{obj_type_name}"
            method = getattr(self, auto_method_name, None)
            if callable(method):
                result = method(obj, attributes)
                return self._build_response(obj, True, auto_method_name, result)

            # Fallback to default visualize method
            result = self._visualize(obj, attributes)
            if result is None:
                return self._build_response(obj, False, "_visualize", None, "Visualization failed")
            return self._build_response(obj, True, "_visualize", result)

        except Exception as e:
            logger.error(f"Visualization execution failed: {str(e)}")
            return self._build_response(obj, False, None, None, str(e))

    def _visualize(self, obj: Union[ScheduleProject, Observation, Telescope, SpaceTelescope, Telescopes, Source, Sources, Scan, Scans, IF, Frequencies], 
                   attributes: Dict[str, Any]) -> Any:
        """Visualize the specified object based on provided attributes.

        Args:
            obj: The object to visualize.
            attributes: Dictionary containing visualization parameters, including 'plot_type', 'output_file', 'show', and 'return_figure'.

        Returns:
            Any: Visualization result data or None if an error occurs.
        """
        plot_type = attributes.get("plot_type")
        output_file = attributes.get("output_file")
        show = attributes.get("show", True)
        return_figure = attributes.get("return_figure", False)

        if not plot_type:
            logger.error("No 'plot_type' specified in attributes")
            return None

        # Create a new figure with specified size
        with self._lock:
            logger.debug(f"Creating new figure for plot_type={plot_type}")
            fig = plt.figure(figsize=attributes.get("figsize", (10, 6)))
        
        try:
            visualizer = None
            for types, func in self._object_visualizers.items():
                if isinstance(obj, types):
                    visualizer = func
                    break
            if not visualizer:
                with self._lock:
                    logger.debug(f"Closing figure due to unsupported object type: {type(obj)}")
                    plt.close(fig)
                raise ValueError(f"Unsupported object type: {type(obj)}")

            # Pass the figure explicitly to the visualizer
            visualizer_result = visualizer(obj, attributes, fig=fig)
            logger.debug(f"Visualization result for {plot_type}: {visualizer_result}")

            if output_file:
                with self._lock:
                    if not output_file.strip():
                        logger.warning("Empty output_file provided, skipping save")
                    else:
                        output_dir = os.path.dirname(output_file)
                        if output_dir:
                            os.makedirs(output_dir, exist_ok=True)
                        fig.savefig(output_file, dpi=attributes.get("dpi", 300), bbox_inches='tight')
                        logger.info(f"Visualization saved to '{output_file}'")

            if show:
                logger.debug("Displaying plot with plt.show()")
                plt.show()
                logger.debug("Plot displayed, continuing execution")
                # Close figure after display if not returning it
                if not return_figure:
                    with self._lock:
                        logger.debug(f"Closing figure after plt.show() for plot_type={plot_type}")
                        plt.close(fig)
            else:
                with self._lock:
                    plt.tight_layout()

            # Add figure to result only if requested
            if return_figure:
                visualizer_result["figure"] = fig
            elif not show:
                with self._lock:
                    logger.debug(f"Closing figure for plot_type={plot_type}")
                    plt.close(fig)

            return visualizer_result

        except Exception as e:
            logger.error(f"Visualization failed: {str(e)}")
            with self._lock:
                logger.debug(f"Closing figure due to error: {str(e)}")
                plt.close(fig)
            return None

    def _visualize_project_or_observation(self, obj: Union[ScheduleProject, Observation], attributes: Dict[str, Any], fig: plt.Figure = None) -> Dict[str, Any]:
        """Visualize a ScheduleProject or Observation object."""
        plot_type = attributes.get("plot_type")

        if isinstance(obj, ScheduleProject):
            observations = obj.get_observations()
            if not observations:
                logger.warning(f"No observations in ScheduleProject '{obj.get_name()}'")
                return {}
            with ThreadPoolExecutor() as executor:
                futures = {executor.submit(self._visualize, obs, attributes): obs.get_observation_code() for obs in observations}
                results = {code: future.result() for future, code in futures.items() if future.result() is not None}
            return results
        
        plot_func = self._plot_types.get(plot_type)
        if not plot_func:
            logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
            return {}
        
        return plot_func(obj, attributes, fig=fig)

    def _plot_uv_coverage(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot UV coverage for an Observation with flexible filtering and frequency scaling."""
        with self._lock:
            logger.debug(f"Plotting UV coverage for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "uv_coverage")
            times_key = attributes.get("times_key", "times")
            baselines = attributes.get("baselines", None)
            source_name = attributes.get("source_name", None)
            scans = attributes.get("scans", None)
            time_range = attributes.get("time_range", None)
            frequencies = attributes.get("frequencies", None)
            units = attributes.get("units", "wavelengths")

            logger.debug(f"Input attributes: store_key={store_key}, times_key={times_key}, "
                        f"baselines={baselines}, source_name={source_name}, scans={scans}, "
                        f"time_range={time_range}, frequencies={frequencies}, units={units}")

            # Create axis even if no data is plotted
            ax = fig.add_subplot(111)
            ax.set_xlabel(f"u, ({units})")
            ax.set_ylabel(f"v, ({units})")
            ax.set_title(f"Obs. code: {obj.code}\n(u,v) coverage for: {source_name if source_name else 'No Source'}")
            ax.grid(True)
            ax.invert_xaxis()

            # If no frequencies are selected, return empty plot
            if not frequencies:
                logger.debug("No frequencies selected, returning empty UV plot")
                return {"baselines": 0, "points": 0, "frequencies": 0}

            # Retrieve UV coverage and time data
            uv_data = obj.get_calculated_data_by_key(store_key)
            times_data = obj.get_calculated_data_by_key(times_key)
            logger.debug(f"Retrieved uv_data: {uv_data}")
            logger.debug(f"Retrieved times_data: {times_data}")

            # Validate data structure
            if not isinstance(uv_data, dict) or not isinstance(times_data, dict):
                logger.warning(f"Invalid data type: uv_data={type(uv_data)}, times_data={type(times_data)} in {obj.get_observation_code()}")
                return {"baselines": 0, "points": 0, "frequencies": len(frequencies)}

            uv_data = uv_data.get("data", {})
            times_data = times_data.get("data", {})
            logger.debug(f"UV data (post-extraction): {uv_data}")
            logger.debug(f"Times data (post-extraction): {times_data}")
            if not uv_data or not times_data:
                logger.warning(f"Empty data: uv_data={bool(uv_data)}, times_data={bool(times_data)} in {obj.get_observation_code()}")
                return {"baselines": 0, "points": 0, "frequencies": len(frequencies)}

            # Default to first source if none specified
            if not source_name:
                sources = list(uv_data.keys())[:1] if uv_data else []
                logger.debug(f"No source specified, defaulting to first source: {sources}")
            else:
                sources = [source_name]

            result = {"baselines": 0, "points": 0, "frequencies": len(frequencies)}
            plotted_pairs = set()
            EARTH_DIAMETER = 12742000.0  # Average Earth diameter in meters
            SPEED_OF_LIGHT = 299792458.0  # Speed of light in m/s

            for source in sources:
                if source not in uv_data or source not in times_data:
                    logger.warning(f"Source {source} not found in UV or times data")
                    continue
                source_uv = uv_data[source]
                source_times = times_data[source]
                logger.debug(f"Processing source {source}: uv={source_uv}, times={source_times}")

                # Filter scans (use all if none specified)
                scan_list = scans if scans else list(source_uv.keys())
                logger.debug(f"Scans to process: {scan_list}")
                for scan in scan_list:
                    if scan not in source_uv or scan not in source_times:
                        logger.debug(f"Scan {scan} not found for source {source}")
                        continue

                    # Validate times
                    times = []
                    for t in source_times[scan]:
                        if t and hasattr(t, 'mjd'):
                            times.append(t.mjd)
                        else:
                            logger.debug(f"Invalid time entry in scan {scan}, source {source}: {t}")
                    logger.debug(f"Valid times for scan {scan}: {times}")
                    if not times:
                        logger.debug(f"No valid times for scan {scan}, source {source}")
                        continue
                    uv_points = source_uv[scan]
                    logger.debug(f"UV points for scan {scan}: {uv_points}")

                    # Apply time range filter if specified
                    if time_range:
                        start_mjd, end_mjd = time_range
                        valid_indices = [i for i, t in enumerate(times) if start_mjd <= t <= end_mjd]
                        times = [times[i] for i in valid_indices]
                        for tel_code in uv_points:
                            uv_points[tel_code] = [uv_points[tel_code][i] for i in valid_indices if i < len(uv_points[tel_code])]
                        logger.debug(f"After time range filter: times={times}, uv_points={uv_points}")
                        if not times:
                            logger.debug(f"No valid times in range {time_range} for scan {scan}, source {source}")
                            continue

                    # Process each frequency
                    for freq_mhz in frequencies:
                        wavelength = SPEED_OF_LIGHT / (freq_mhz * 1e6) if freq_mhz else 1.0  # Avoid division by zero
                        scaling_factor = 1.0 if units == "wavelengths" else (1.0 / EARTH_DIAMETER)
                        logger.debug(f"Frequency {freq_mhz} MHz, wavelength={wavelength}, scaling_factor={scaling_factor}")

                        for tel_code in uv_points:
                            if baselines and tel_code not in baselines:
                                logger.debug(f"Skipping tel_code {tel_code} not in baselines {baselines}")
                                continue
                            if not uv_points[tel_code]:
                                logger.debug(f"No valid UV points for {tel_code} in source {source}, scan {scan}")
                                continue
                            try:
                                # Validate UV points format
                                valid_points = [
                                    pt for pt in uv_points[tel_code]
                                    if pt is not None and isinstance(pt, (list, tuple)) and len(pt) >= 2 and not np.any(np.isnan(pt[:2]))
                                ]
                                logger.debug(f"Valid UV points for {tel_code}: {len(valid_points)}")
                                if not valid_points:
                                    logger.debug(f"No valid UV points after filtering for {tel_code} in source {source}, scan {scan}")
                                    continue
                                u, v = zip(*[(pt[0], pt[1]) for pt in valid_points])
                                u, v = np.array(u, dtype=float), np.array(v, dtype=float)
                                # Scale UV points based on units
                                u_scaled = u / wavelength * scaling_factor if wavelength != 0 else u
                                v_scaled = v / wavelength * scaling_factor if wavelength != 0 else v
                                logger.debug(f"Scaled UV points: u={u_scaled[:5]}, v={v_scaled[:5]}")
                                color_idx = (len(plotted_pairs) + frequencies.index(freq_mhz)) % len(self.moderate2_colors)
                                label = f"{tel_code} ({freq_mhz} MHz)"
                                ax.scatter(u_scaled, v_scaled, s=1, c=[self.moderate2_colors[color_idx]], label=label)
                                ax.scatter(-u_scaled, -v_scaled, s=1, c=[self.moderate2_colors[color_idx]])
                                plotted_pairs.add(f"{tel_code}_{freq_mhz}")
                                result["points"] += len(u_scaled)
                            except (ValueError, TypeError) as e:
                                logger.error(f"Invalid UV point format for {tel_code} at {freq_mhz} MHz: {str(e)}")
                                continue

            result["baselines"] = len(plotted_pairs)
            if plotted_pairs:
                ax.legend()
            logger.debug(f"Visualization result: {result}")
            return result

    def _plot_source_visibility(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot source visibility over time for an Observation."""
        with self._lock:
            logger.debug(f"Plotting source visibility for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "source_visibility")
            data = obj.get_calculated_data_by_key(store_key)
            if not data:
                logger.error(f"No source visibility data found for '{store_key}' in {obj.get_observation_code()}")
                return {}

            data = data.get("data", {})
            ax = fig.add_subplot(111)
            for scan_idx, scan_data in data.items():
                times = [Time(t).mjd for t in scan_data.get("times", []) if t]
                visibility = scan_data.get("visibility", {})
                source = scan_data.get("source")
                for i, (tel_code, vis) in enumerate(visibility.items()):
                    valid_pairs = [(t, float(v)) for t, v in zip(times, vis) if v is not None]
                    if valid_pairs:
                        times_mjd, vis_valid = zip(*valid_pairs)
                        ax.plot(times_mjd, vis_valid, label=f"{tel_code}", marker='o' if not attributes.get("time_step") else None,
                                color=self.moderate2_colors[i % len(self.moderate2_colors)])
            
            ax.set_xlabel("Time (MJD)")
            ax.set_ylabel("Visible (1 = Yes, 0 = No)")
            ax.set_title(f"Source Visibility for {source}")
            ax.legend()
            ax.grid(True)
            return {"scans": len(data)}

    def _plot_sun_angles(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot angles to the Sun for an Observation."""
        with self._lock:
            logger.debug(f"Plotting sun angles for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "sun_angles")
            data = obj.get_calculated_data_by_key(store_key)
            if not data:
                logger.error(f"No sun angles data found for '{store_key}' in {obj.get_observation_code()}")
                return {}

            data = data.get("data", {})
            ax = fig.add_subplot(111)
            for scan_idx, scan_data in data.items():
                times = [Time(t) for t in scan_data.get("times", []) if t]
                angles = scan_data.get("sun_angles", {})
                source = scan_data.get("source")
                for i, (tel_code, angle_list) in enumerate(angles.items()):
                    valid_pairs = [(t.mjd, float(a)) for t, a in zip(times, angle_list) if a is not None]
                    if valid_pairs:
                        times_mjd, angles_sorted = zip(*sorted(valid_pairs))
                        ax.plot(times_mjd, angles_sorted, label=f"{tel_code}", color=self.moderate2_colors[i % len(self.moderate2_colors)])
            
            ax.set_xlabel("Time (MJD)")
            ax.set_ylabel("Angle to Sun (degrees)")
            ax.set_title(f"Sun Angles for Source {source}")
            ax.legend()
            ax.grid(True)
            return {"scans": len(data)}

    def _plot_az_el(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot Azimuth/Elevation or Hour Angle/Declination for an Observation."""
        with self._lock:
            logger.debug(f"Plotting Az/El for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "az_el")
            data = obj.get_calculated_data_by_key(store_key)
            if not data:
                logger.error(f"No Az/El data found for '{store_key}' in {obj.get_observation_code()}")
                return {}

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
                return {}

            if n_tels == 1:
                ax = fig.add_subplot(111)
                axes = [ax]
            else:
                axes = fig.subplots(n_tels, 1, sharex=False, sharey=False)

            for i, (tel_code, data) in enumerate(all_telescopes.items()):
                ax = axes[i]
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
            return {"scans": len(data)}

    def _plot_time_on_source(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot time on source for an Observation."""
        with self._lock:
            logger.debug(f"Plotting time on source for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "time_on_source")
            data = obj.get_calculated_data_by_key(store_key)
            if not data:
                logger.error(f"No time on source data found for '{store_key}' in {obj.get_observation_code()}")
                return {}

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
            ax = fig.add_subplot(111)

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
            return {"telescopes": len(telescopes)}

    def _plot_beam_pattern(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot beam patterns for an Observation."""
        with self._lock:
            logger.debug(f"Plotting beam pattern for {obj.get_observation_code()}")
            freq_name = attributes.get("freq_name")
            store_key = attributes.get("store_key", f"beam_pattern_{freq_name}")
            data = obj.get_calculated_data_by_key(store_key)
            if not data:
                logger.error(f"No beam pattern data found for '{store_key}' in {obj.get_observation_code()}")
                return {}

            data = data.get("data", {})
            n_tels = len(data)
            if n_tels == 1:
                ax = fig.add_subplot(111)
                axes = [ax]
            else:
                axes = fig.subplots(n_tels, 1, sharex=False, sharey=False)

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
            return {"telescopes": len(data)}

    def _plot_synthesized_beam(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot the synthesized beam for an Observation."""
        with self._lock:
            logger.debug(f"Plotting synthesized beam for {obj.get_observation_code()}")
            freq_name = attributes.get("freq_name")
            store_key = attributes.get("store_key", f"synthesized_beam_{freq_name}")
            data = obj.get_calculated_data_by_key(store_key)
            if not data:
                logger.error(f"No synthesized beam data found for '{store_key}' in {obj.get_observation_code()}")
                return {}

            data = data.get("data", {})
            scan_data = data.get(0, {})
            theta_u = np.array(scan_data.get("theta_u", []))
            theta_v = np.array(scan_data.get("theta_v", []))
            beam_2d = scan_data.get("beam_2d", np.zeros((len(theta_v), len(theta_u))))

            if len(theta_u) == 0 or len(theta_v) == 0:
                logger.error(f"Missing or empty data for 'theta_u' or 'theta_v' in {obj.get_observation_code()}")
                return {}

            theta_u_muas = theta_u * 3.6e9
            theta_v_muas = theta_v * 3.6e9

            ax = fig.add_subplot(111)

            im = ax.imshow(beam_2d, extent=[min(theta_u_muas), max(theta_u_muas), min(theta_v_muas), max(theta_v_muas)], 
                           cmap=self.redpurple_cmap, aspect='equal')

            u_range = max(theta_u_muas) - min(theta_u_muas)
            v_range = max(theta_v_muas) - min(theta_v_muas)
            max_range = max(u_range, v_range) * 1.1
            
            u_center = (max(theta_u_muas) + min(theta_u_muas)) / 2
            v_center = (max(theta_v_muas) + min(theta_v_muas)) / 2
            
            ax.set_xlim(u_center - max_range / 2, u_center + max_range / 2)
            ax.set_ylim(v_center - max_range / 2, v_center + max_range / 2)

            fig.colorbar(im, label='Normalized Peak Flux, (Jy)', ax=ax)
            ax.set_xlabel("Relative Right Ascension, (μas)")
            ax.set_ylabel("Relative Declination, (μas)")
            ax.set_title(f"Synthesized Beam at {obj.get_frequencies().get(freq_name).get('frequency')} MHz")
            
            return {}

    def _plot_baseline_projections(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot baseline projections for an Observation using scatter points.

        Args:
            obj: Observation object containing the baseline projections data.
            attributes: Dictionary with visualization parameters, including 'store_key'.
            fig: Matplotlib figure object for plotting.

        Returns:
            Dict containing metadata about the plotted data (e.g., number of scans, baselines, and projections).
        """
        with self._lock:
            logger.debug(f"Plotting baseline projections for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "baseline_projections")
            data = obj.get_calculated_data_by_key(store_key)
            if not data:
                logger.error(f"No baseline projections data found for '{store_key}' in {obj.get_observation_code()}")
                return {}

            data = data.get("data", {})
            plotted_pairs = set()
            valid_projections = 0
            pair_data = {}

            for scan_idx, scan_data in data.items():
                times_mjd = [Time(t).mjd for t in scan_data.get("times", []) if t]
                if not times_mjd:
                    logger.debug(f"No valid times for scan {scan_idx} in {obj.get_observation_code()}")
                    continue
                projections = scan_data.get("projections", {})
                if not projections:
                    logger.debug(f"No projection data for scan {scan_idx} in {obj.get_observation_code()}")
                    continue

                for time_idx, proj_dict in projections.items():
                    if time_idx >= len(times_mjd):
                        logger.warning(f"Time index {time_idx} exceeds available times ({len(times_mjd)}) in scan {scan_idx}")
                        continue
                    for pair, bl in proj_dict.items():
                        if bl is None or np.isnan(bl):
                            logger.debug(f"Skipping invalid baseline for pair {pair} at time_idx {time_idx}: {bl}")
                            continue
                        if pair not in pair_data:
                            pair_data[pair] = {"times": [], "bl": []}
                        pair_data[pair]["times"].append(times_mjd[time_idx])
                        pair_data[pair]["bl"].append(float(bl))  # Ensure float for plotting
                        valid_projections += 1

            if not pair_data:
                logger.warning(f"No valid projection data to plot for {obj.get_observation_code()}. Scans processed: {len(data)}")
                return {}

            ax = fig.add_subplot(111)
            for i, (pair, data) in enumerate(pair_data.items()):
                color_idx = i % len(self.moderate2_colors)
                ax.scatter(
                    data["times"],
                    data["bl"],
                    label=pair if pair not in plotted_pairs else None,
                    color=self.moderate2_colors[color_idx],
                    s=10,
                    alpha=0.7
                )
                plotted_pairs.add(pair)

            ax.set_xlabel("Time (MJD)")
            ax.set_ylabel("Baseline Length (meters)")
            ax.set_title("Baseline Projections")
            ax.legend()
            ax.grid(True)
            return {"scans": len(data), "baselines": len(plotted_pairs), "projections": valid_projections}

    def _plot_mollweide_tracks(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot Mollweide tracks for an Observation."""
        with self._lock:
            logger.debug(f"Plotting Mollweide tracks for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "mollweide_tracks")
            data = obj.get_calculated_data_by_key(store_key)
            if not data:
                logger.error(f"No Mollweide tracks data found for '{store_key}' in {obj.get_observation_code()}")
                return {}

            data = data.get("data", {})
            ax = fig.add_subplot(111, projection="mollweide")
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
            return {"scans": len(data)}

    def _visualize_telescopes(self, obj: Union[Telescope, SpaceTelescope, Telescopes], attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Visualize Telescope-related objects."""
        with self._lock:
            logger.debug(f"Visualizing telescopes for {type(obj).__name__}")
            plot_type = attributes.get("plot_type")
            if plot_type == "positions":
                if isinstance(obj, Telescopes):
                    tels = obj.get_active_telescopes()
                else:
                    tels = [obj]
                x, y, z = zip(*[tel.get_coordinates() for tel in tels])
                ax = fig.add_subplot(111, projection='3d')
                for i in range(len(tels)):
                    ax.scatter(x[i], y[i], z[i], c=[self.moderate2_colors[i % len(self.moderate2_colors)]], label=tels[i].get_code())
                ax.set_xlabel("X, (m)")
                ax.set_ylabel("Y, (m)")
                ax.set_zlabel("Z, (m)")
                ax.set_title("Telescope Positions")
                ax.legend()
                return {"telescopes": len(tels)}
            logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
            return {}

    def _visualize_sources(self, obj: Union[Source, Sources], attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Visualize Source-related objects."""
        with self._lock:
            logger.debug(f"Visualizing sources for {type(obj).__name__}")
            plot_type = attributes.get("plot_type")
            if plot_type == "sky_position":
                if isinstance(obj, Sources):
                    sources = obj.get_items()
                else:
                    sources = [obj]
                ra = [s.get_ra_degrees() for s in sources]
                dec = [s.get_dec_degrees() for s in sources]
                ax = fig.add_subplot(111)
                for i in range(len(sources)):
                    ax.scatter(ra[i], dec[i], c=[self.moderate2_colors[i % len(self.moderate2_colors)]], label=f"Source {i}")
                ax.set_xlabel("Relative Right Ascension, (deg)")
                ax.set_ylabel("Relative Declination, (deg)")
                ax.set_title("Source(s) Sky Position")
                ax.grid(True)
                ax.legend()
                return {"sources": len(sources)}
            logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
            return {}

    def _visualize_scans(self, obj: Union[Scan, Scans], attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Visualize Scan-related objects."""
        with self._lock:
            logger.debug(f"Visualizing scans for {type(obj).__name__}")
            plot_type = attributes.get("plot_type")
            if plot_type == "timeline":
                if isinstance(obj, Scans):
                    scans = obj.get_items()
                else:
                    scans = [obj]
                starts = [s.get_start().isot for s in scans]
                durations = [s.get_duration() for s in scans]
                ends = [(Time(starts[i]) + durations[i] * u.s).isot for i in range(len(starts))]
                ax = fig.add_subplot(111)
                for i, (start, end) in enumerate(zip(starts, ends)):
                    ax.plot([Time(start).mjd, Time(end).mjd], [i, i], label=f"Scan {i}", 
                            color=self.moderate2_colors[i % len(self.moderate2_colors)])
                ax.set_xlabel("Time, (MJD)")
                ax.set_ylabel("Scan Index")
                ax.set_title("Scan Timeline")
                ax.grid(True)
                return {"scans": len(scans)}
            logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
            return {}

    def _visualize_frequencies(self, obj: Union[IF, Frequencies], attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Visualize Frequency-related objects."""
        with self._lock:
            logger.debug(f"Visualizing frequencies for {type(obj).__name__}")
            plot_type = attributes.get("plot_type")
            if plot_type == "spectrum":
                if isinstance(obj, Frequencies):
                    freqs = obj.get_items()
                else:
                    freqs = [obj]
                frequencies = [f.get_frequency() for f in freqs]
                bandwidths = [f.get_bandwidth() for f in freqs]
                ax = fig.add_subplot(111)
                for i in range(len(frequencies)):
                    ax.bar(frequencies[i], bandwidths[i], width=0.1, align='center', 
                           color=self.moderate2_colors[i % len(self.moderate2_colors)])
                ax.set_xlabel("Frequency, (MHz)")
                ax.set_ylabel("Bandwidth, (MHz)")
                ax.set_title("Frequency Spectrum")
                ax.grid(True)
                return {"frequencies": len(frequencies)}
            logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
            return {}