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
        """Visualize the specified objectlettere

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
        """Plot UV coverage for an Observation with flexible filtering and frequency scaling.

        Args:
            obj: Observation object containing the UV coverage data.
            attributes: Dictionary with visualization parameters, including 'store_key', 'times_key', 
                    'baselines', 'source_name', 'scans', 'time_range', 'frequencies', and 'units'.
            fig: Matplotlib figure object for plotting.

        Returns:
            Dict containing metadata about the plotted data (e.g., number of baselines, points, and frequencies).
        """
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
            ax.set_title(f"Obs. code: {obj.code}\n(u,v) coverage")
            ax.grid(True)
            ax.invert_xaxis()

            # Check if required parameters are provided
            if not (source_name or baselines or scans or frequencies):
                logger.debug("No source, baselines, scans, or frequencies specified, returning empty plot")
                return {"baselines": 0, "points": 0, "frequencies": 0}

            # Retrieve UV coverage and time data
            uv_data = obj.get_calculated_data_by_key(store_key)
            times_data = obj.get_calculated_data_by_key(times_key)
            logger.debug(f"Retrieved uv_data: {uv_data}")
            logger.debug(f"Retrieved times_data: {times_data}")

            # Validate data structure
            if not isinstance(uv_data, dict) or not isinstance(times_data, dict):
                logger.warning(f"Invalid data type: uv_data={type(uv_data)}, times_data={type(times_data)} in {obj.get_observation_code()}")
                return {"baselines": 0, "points": 0, "frequencies": 0}

            uv_data = uv_data.get("data", {})
            times_data = times_data.get("data", {})
            logger.debug(f"UV data (post-extraction): {uv_data}")
            logger.debug(f"Times data (post-extraction): {times_data}")
            if not uv_data or not times_data:
                logger.warning(f"Empty data: uv_data={bool(uv_data)}, times_data={bool(times_data)} in {obj.get_observation_code()}")
                return {"baselines": 0, "points": 0, "frequencies": 0}

            # Default to first source if none specified
            sources = [source_name] if source_name else list(uv_data.keys())[:1]
            if not sources:
                logger.debug("No sources available, returning empty plot")
                return {"baselines": 0, "points": 0, "frequencies": 0}

            result = {"baselines": 0, "points": 0, "frequencies": len(frequencies) if frequencies else 0}
            plotted_pairs = set()
            EARTH_DIAMETER = 12742000.0  # Average Earth diameter in meters
            SPEED_OF_LIGHT = 299792458.0  # Speed of light in m/s

            for source in sources:
                if source not in uv_data or source not in times_data:
                    logger.warning(f"Source {source} not found in UV or times data")
                    continue
                source_uv = uv_data[source]
                source_times = times_data[source]
                logger.debug(f"Processing source {source}")

                # Collect all data across scans for this source
                all_times = []
                all_uv_points = {}
                scan_list = scans if scans else list(source_uv.keys())
                logger.debug(f"Scans to process: {scan_list}")

                for scan in scan_list:
                    if scan not in source_uv or scan not in source_times:
                        logger.debug(f"Scan {scan} not found for source {source}")
                        continue
                    times = []
                    for t in source_times[scan]:
                        if t and hasattr(t, 'mjd'):
                            times.append(t.mjd)
                        else:
                            logger.debug(f"Invalid time entry in scan {scan}, source {source}: {t}")
                    if not times:
                        logger.debug(f"No valid times for scan {scan}, source {source}")
                        continue
                    # Append times and UV points
                    all_times.extend(times)
                    uv_points = source_uv[scan]
                    for tel_code in uv_points:
                        if tel_code not in all_uv_points:
                            all_uv_points[tel_code] = []
                        all_uv_points[tel_code].extend([(pt[0], pt[1]) for pt in uv_points[tel_code] if len(pt) >= 2])

                # Ensure data consistency
                if not all_times or not all_uv_points:
                    logger.debug(f"No valid times or UV points for source {source}")
                    continue

                # Sort all times and UV points by time
                time_indices = np.argsort(all_times)
                all_times = [all_times[i] for i in time_indices]
                for tel_code in all_uv_points:
                    if len(all_uv_points[tel_code]) != len(all_times):
                        logger.warning(f"Mismatch in lengths for {tel_code}: times={len(all_times)}, uv_points={len(all_uv_points[tel_code])}")
                        min_len = min(len(all_times), len(all_uv_points[tel_code]))
                        all_times = all_times[:min_len]
                        all_uv_points[tel_code] = all_uv_points[tel_code][:min_len]
                    all_uv_points[tel_code] = [all_uv_points[tel_code][i] for i in time_indices if i < len(all_uv_points[tel_code])]

                # Apply time range filter if specified
                if time_range:
                    start_mjd, end_mjd = time_range
                    valid_indices = [i for i, t in enumerate(all_times) if start_mjd <= t <= end_mjd]
                    all_times = [all_times[i] for i in valid_indices]
                    for tel_code in all_uv_points:
                        all_uv_points[tel_code] = [all_uv_points[tel_code][i] for i in valid_indices if i < len(all_uv_points[tel_code])]
                    logger.debug(f"After time range filter: times={len(all_times)}")
                    if not all_times:
                        logger.debug(f"No valid times in range {time_range} for source {source}")
                        continue

                # Process each frequency
                for freq_mhz in (frequencies or [None]):
                    wavelength = SPEED_OF_LIGHT / (freq_mhz * 1e6) if freq_mhz else 1.0
                    scaling_factor = 1.0 if units == "wavelengths" else (wavelength / EARTH_DIAMETER)
                    logger.debug(f"Frequency {freq_mhz} MHz, wavelength={wavelength}, scaling_factor={scaling_factor}")

                    for tel_code in all_uv_points:
                        if baselines and tel_code not in baselines:
                            logger.debug(f"Skipping tel_code {tel_code} not in baselines {baselines}")
                            continue
                        if len(all_uv_points[tel_code]) == 0:
                            logger.debug(f"No valid UV points for {tel_code} in source {source}")
                            continue
                        try:
                            valid_points = [(pt[0], pt[1]) for pt in all_uv_points[tel_code] if len(pt) >= 2]
                            if not valid_points:
                                logger.debug(f"No valid UV points after filtering for {tel_code} in source {source}")
                                continue
                            u, v = zip(*valid_points)
                            u, v = np.array(u, dtype=float), np.array(v, dtype=float)
                            u_scaled = u / wavelength * scaling_factor if wavelength != 0 else u
                            v_scaled = v / wavelength * scaling_factor if wavelength != 0 else v
                            logger.debug(f"Scaled UV points: u={u_scaled[:5]}, v={v_scaled[:5]}")
                            color_idx = (len(plotted_pairs) + (frequencies.index(freq_mhz) if frequencies and freq_mhz else 0)) % len(self.moderate2_colors)
                            label = f"{tel_code} ({freq_mhz} MHz)" if freq_mhz else f"{tel_code}"
                            ax.scatter(u_scaled, v_scaled, s=1, c=[self.moderate2_colors[color_idx]], label=label)
                            ax.scatter(-u_scaled, -v_scaled, s=1, c=[self.moderate2_colors[color_idx]])
                            plotted_pairs.add(f"{tel_code}_{freq_mhz}" if freq_mhz else tel_code)
                            result["points"] += len(u_scaled)
                        except (ValueError, TypeError) as e:
                            logger.error(f"Error processing UV points for {tel_code} at {freq_mhz} MHz: {str(e)}")
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
            result = {"scans": 0}
            plotted_telescopes = set()

            # Collect data across all scans
            all_data = {}
            for scan_idx, scan_data in data.items():
                times = [Time(t).mjd for t in scan_data.get("times", []) if t]
                visibility = scan_data.get("visibility", {})
                source = scan_data.get("source")
                if not times:
                    logger.debug(f"No valid times for scan {scan_idx}, source {source}")
                    continue
                result["scans"] += 1
                for tel_code, vis in visibility.items():
                    if tel_code not in all_data:
                        all_data[tel_code] = {"times": [], "visibility": []}
                    valid_pairs = [(t, float(v)) for t, v in zip(times, vis) if v is not None]
                    if valid_pairs:
                        times_mjd, vis_valid = zip(*valid_pairs)
                        all_data[tel_code]["times"].extend(times_mjd)
                        all_data[tel_code]["visibility"].extend(vis_valid)

            # Plot combined data
            for tel_code, data in all_data.items():
                times_mjd = data["times"]
                vis_valid = data["visibility"]
                if times_mjd and vis_valid:
                    # Sort by time
                    sorted_indices = np.argsort(times_mjd)
                    times_mjd = [times_mjd[i] for i in sorted_indices]
                    vis_valid = [vis_valid[i] for i in sorted_indices]
                    color_idx = len(plotted_telescopes) % len(self.moderate2_colors)
                    ax.plot(
                        times_mjd,
                        vis_valid,
                        label=f"{tel_code}",
                        marker="o" if not attributes.get("time_step") else None,
                        color=self.moderate2_colors[color_idx],
                    )
                    plotted_telescopes.add(tel_code)

            ax.set_xlabel("Time (MJD)")
            ax.set_ylabel("Visible (1 = Yes, 0 = No)")
            ax.set_title(f"Source Visibility for {source}")
            ax.grid(True)
            if plotted_telescopes:
                ax.legend()
            logger.debug(f"Visualization result: {result}")
            return result

    def _plot_sun_angles(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot angles to the Sun for an Observation with flexible filtering.

        Args:
            obj: Observation object containing the sun angles data.
            attributes: Dictionary with visualization parameters, including 'store_key', 'times_key',
                    'source_name', 'telescopes', 'scans', and 'time_range'.
            fig: Matplotlib figure object for plotting.

        Returns:
            Dict containing metadata about the plotted data (e.g., number of scans, telescopes, and points).
        """
        with self._lock:
            logger.debug(f"Plotting sun angles for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "sun_angles")
            times_key = attributes.get("times_key", "times")
            source_name = attributes.get("source_name", None)
            telescopes = attributes.get("telescopes", None)
            scans = attributes.get("scans", None)
            time_range = attributes.get("time_range", None)

            logger.debug(f"Input attributes: store_key={store_key}, times_key={times_key}, "
                        f"source_name={source_name}, telescopes={telescopes}, scans={scans}, "
                        f"time_range={time_range}")

            # Create axis even if no data is plotted
            ax = fig.add_subplot(111)
            ax.set_xlabel("Time (MJD)")
            ax.set_ylabel("Angle to Sun (degrees)")
            ax.set_title(f"Sun Angles for Observation: {obj.get_observation_code()}")
            ax.grid(True)

            # Check if required parameters are provided
            if not (source_name or telescopes or scans):
                logger.debug("No source, telescopes, or scans specified, returning empty plot")
                return {"scans": 0, "telescopes": 0, "points": 0}

            # Retrieve sun angles and time data
            sun_angles_data = obj.get_calculated_data_by_key(store_key)
            times_data = obj.get_calculated_data_by_key(times_key)
            logger.debug(f"Retrieved sun_angles_data: {sun_angles_data}")
            logger.debug(f"Retrieved times_data: {times_data}")

            # Validate data structure
            if not isinstance(sun_angles_data, dict) or not isinstance(times_data, dict):
                logger.warning(f"Invalid data type: sun_angles_data={type(sun_angles_data)}, "
                            f"times_data={type(times_data)} in {obj.get_observation_code()}")
                return {"scans": 0, "telescopes": 0, "points": 0}

            sun_angles_data = sun_angles_data.get("data", {})
            times_data = times_data.get("data", {})
            logger.debug(f"Sun angles data (post-extraction): {sun_angles_data}")
            logger.debug(f"Times data (post-extraction): {times_data}")
            if not sun_angles_data or not times_data:
                logger.warning(f"Empty data: sun_angles_data={bool(sun_angles_data)}, "
                            f"times_data={bool(times_data)} in {obj.get_observation_code()}")
                return {"scans": 0, "telescopes": 0, "points": 0}

            # Default to first source if none specified
            sources = [source_name] if source_name else list(sun_angles_data.keys())[:1]
            if not sources:
                logger.debug("No sources available, returning empty plot")
                return {"scans": 0, "telescopes": 0, "points": 0}

            result = {"scans": 0, "telescopes": 0, "points": 0}
            plotted_telescopes = set()

            for source in sources:
                if source not in sun_angles_data or source not in times_data:
                    logger.warning(f"Source {source} not found in sun angles or times data")
                    continue
                source_angles = sun_angles_data[source]
                source_times = times_data[source]
                logger.debug(f"Processing source {source}")

                # Collect all data across scans
                all_times = []
                all_angles = {}
                scan_list = scans if scans else list(source_angles.keys())
                result["scans"] += len(scan_list)
                logger.debug(f"Scans to process: {scan_list}")

                for scan in scan_list:
                    if scan not in source_angles or scan not in source_times:
                        logger.debug(f"Scan {scan} not found for source {source}")
                        continue
                    times = []
                    for t in source_times[scan]:
                        if t and hasattr(t, 'mjd'):
                            times.append(t)
                        else:
                            logger.debug(f"Invalid time entry in scan {scan}, source {source}: {t}")
                    if not times:
                        logger.debug(f"No valid times for scan {scan}, source {source}")
                        continue
                    all_times.extend(times)
                    angles = source_angles[scan]
                    for tel_code in angles:
                        if tel_code not in all_angles:
                            all_angles[tel_code] = []
                        all_angles[tel_code].extend(angles[tel_code])

                # Sort all times and angles by time
                if not all_times:
                    logger.debug(f"No valid times for source {source} after collecting scans")
                    continue
                time_indices = np.argsort(all_times)
                all_times = [all_times[i] for i in time_indices]
                for tel_code in all_angles:
                    all_angles[tel_code] = [all_angles[tel_code][i] for i in time_indices]

                # Apply time range filter if specified
                if time_range:
                    start_mjd, end_mjd = time_range
                    valid_indices = [i for i, t in enumerate(all_times) if start_mjd <= t.mjd <= end_mjd]
                    all_times = [all_times[i] for i in valid_indices]
                    for tel_code in all_angles:
                        all_angles[tel_code] = [all_angles[tel_code][i] for i in valid_indices if i < len(all_angles[tel_code])]
                    logger.debug(f"After time range filter: times={len(all_times)}")
                    if not all_times:
                        logger.debug(f"No valid times in range {time_range} for source {source}")
                        continue

                # Process each telescope
                tel_list = telescopes if telescopes else list(all_angles.keys())
                for tel_code in tel_list:
                    if tel_code not in all_angles:
                        logger.debug(f"Telescope {tel_code} not found in source {source}")
                        continue
                    valid_pairs = [(t.mjd, float(a)) for t, a in zip(all_times, all_angles[tel_code]) if a is not None]
                    if valid_pairs:
                        times_mjd, angles_sorted = zip(*sorted(valid_pairs))
                        color_idx = len(plotted_telescopes) % len(self.moderate2_colors)
                        ax.plot(times_mjd, angles_sorted, label=f"{tel_code} ({source})",
                                color=self.moderate2_colors[color_idx])
                        plotted_telescopes.add(tel_code)
                        result["points"] += len(valid_pairs)

            result["telescopes"] = len(plotted_telescopes)
            if plotted_telescopes:
                ax.legend()
            logger.debug(f"Visualization result: {result}")
            return result

    def _plot_az_el(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot Azimuth/Elevation or Hour Angle/Declination for an Observation with one subplot per telescope.

        Args:
            obj: Observation object containing the Az/El or HA/Dec data.
            attributes: Dictionary with visualization parameters, including 'store_key', 'times_key',
                        'source_name', 'telescopes', 'scans', 'time_range', and 'coord_type'.
            fig: Matplotlib figure object for plotting.

        Returns:
            Dict containing metadata about the plotted data (e.g., number of scans, telescopes, and points).
        """
        with self._lock:
            logger.debug(f"Plotting Az/El or HA/Dec for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "az_el")
            times_key = attributes.get("times_key", "times")
            source_name = attributes.get("source_name", None)
            telescopes = attributes.get("telescopes", None)
            scans = attributes.get("scans", None)
            time_range = attributes.get("time_range", None)
            coord_type = attributes.get("coord_type", "AzEl")

            # Validate coord_type
            valid_coord_types = ["AzEl", "HADec"]
            if coord_type not in valid_coord_types:
                logger.warning(f"Invalid coord_type '{coord_type}', defaulting to 'AzEl'")
                coord_type = "AzEl"

            logger.debug(f"Input attributes: store_key={store_key}, times_key={times_key}, "
                        f"source_name={source_name}, telescopes={telescopes}, scans={scans}, "
                        f"time_range={time_range}, coord_type={coord_type}")

            # Check if required parameters are provided
            if not (source_name or telescopes or scans):
                logger.debug("No source, telescopes, or scans specified, creating empty plot")
                ax = fig.add_subplot(111)
                ax.set_xlabel("Time (MJD)")
                ax.set_ylabel(f"Angle ({coord_type[:2]}/{coord_type[2:]}, degrees)")
                ax.set_title(f"{coord_type} for Observation: {obj.get_observation_code()}")
                ax.grid(True)
                return {"scans": 0, "telescopes": 0, "points": 0}

            # Retrieve Az/El and time data
            az_el_data = obj.get_calculated_data_by_key(store_key)
            times_data = obj.get_calculated_data_by_key(times_key)

            # Validate data structure
            if not isinstance(az_el_data, dict) or not isinstance(times_data, dict):
                logger.warning(f"Invalid data type: az_el_data={type(az_el_data)}, "
                            f"times_data={type(times_data)} in {obj.get_observation_code()}")
                ax = fig.add_subplot(111)
                ax.set_xlabel("Time (MJD)")
                ax.set_ylabel(f"Angle ({coord_type[:2]}/{coord_type[2:]}, degrees)")
                ax.set_title(f"{coord_type} for Observation: {obj.get_observation_code()}")
                ax.grid(True)
                return {"scans": 0, "telescopes": 0, "points": 0}

            az_el_data = az_el_data.get("data", {})
            times_data = times_data.get("data", {})
            if not az_el_data or not times_data:
                logger.warning(f"Empty data: az_el_data={bool(az_el_data)}, "
                            f"times_data={bool(times_data)} in {obj.get_observation_code()}")
                ax = fig.add_subplot(111)
                ax.set_xlabel("Time (MJD)")
                ax.set_ylabel(f"Angle ({coord_type[:2]}/{coord_type[2:]}, degrees)")
                ax.set_title(f"{coord_type} for Observation: {obj.get_observation_code()}")
                ax.grid(True)
                return {"scans": 0, "telescopes": 0, "points": 0}

            # Default to first source if none specified
            sources = [source_name] if source_name else list(az_el_data.keys())[:1]
            if not sources:
                logger.debug("No sources available, creating empty plot")
                ax = fig.add_subplot(111)
                ax.set_xlabel("Time (MJD)")
                ax.set_ylabel(f"Angle ({coord_type[:2]}/{coord_type[2:]}, degrees)")
                ax.set_title(f"{coord_type} for Observation: {obj.get_observation_code()}")
                ax.grid(True)
                return {"scans": 0, "telescopes": 0, "points": 0}

            result = {"scans": 0, "telescopes": 0, "points": 0}
            plotted_telescopes = set()

            # Determine telescopes to plot
            all_telescopes = set()
            for source in sources:
                if source not in az_el_data:
                    logger.warning(f"Source {source} not found in Az/El data")
                    continue
                for scan in az_el_data[source]:
                    all_telescopes.update(az_el_data[source][scan].keys())
            tel_list = sorted(telescopes if telescopes else list(all_telescopes))
            result["telescopes"] = len(tel_list)

            # Create subplot grid
            n_tels = len(tel_list)
            if n_tels == 0:
                logger.debug("No telescopes to plot, creating empty plot")
                ax = fig.add_subplot(111)
                ax.set_xlabel("Time (MJD)")
                ax.set_ylabel(f"Angle ({coord_type[:2]}/{coord_type[2:]}, degrees)")
                ax.set_title(f"{coord_type} for Observation: {obj.get_observation_code()}")
                ax.grid(True)
                return {"scans": 0, "telescopes": 0, "points": 0}

            n_cols = int(np.ceil(np.sqrt(n_tels)))
            n_rows = int(np.ceil(n_tels / n_cols))
            logger.debug(f"Creating subplot grid: {n_rows} rows x {n_cols} cols for {n_tels} telescopes")
            axes = fig.subplots(n_rows, n_cols, sharex=True, sharey=True)
            axes = np.array(axes).flatten() if n_tels > 1 else [axes]

            # Plot data for each telescope
            for source in sources:
                if source not in az_el_data or source not in times_data:
                    logger.warning(f"Source {source} not found in Az/El or times data")
                    continue
                source_coords = az_el_data[source]
                source_times = times_data[source]

                # Collect all data across scans
                all_times = []
                all_coords = {}
                scan_list = scans if scans else list(source_coords.keys())
                result["scans"] += len(scan_list)

                for scan in scan_list:
                    if scan not in source_coords or scan not in source_times:
                        logger.debug(f"Scan {scan} not found for source {source}")
                        continue
                    times = [t for t in source_times[scan] if t and hasattr(t, 'mjd')]
                    if not times:
                        logger.debug(f"No valid times for scan {scan}, source {source}")
                        continue
                    all_times.extend(times)
                    coords = source_coords[scan]
                    for tel in coords:
                        if tel not in all_coords:
                            all_coords[tel] = []
                        all_coords[tel].extend(coords[tel])

                # Sort all times and coordinates by time
                if not all_times:
                    logger.debug(f"No valid times for source {source} after collecting scans")
                    continue
                time_indices = np.argsort(all_times)
                all_times = [all_times[i] for i in time_indices]
                for tel in all_coords:
                    all_coords[tel] = [all_coords[tel][i] for i in time_indices]

                # Apply time range filter
                if time_range:
                    start_mjd, end_mjd = time_range
                    valid_indices = [i for i, t in enumerate(all_times) if start_mjd <= t.mjd <= end_mjd]
                    all_times = [all_times[i] for i in valid_indices]
                    for tel in all_coords:
                        all_coords[tel] = [all_coords[tel][i] for i in valid_indices if i < len(all_coords[tel])]
                    if not all_times:
                        logger.debug(f"No valid times in range {time_range} for source {source}")
                        continue

                # Plot for each telescope
                for tel_idx, tel_code in enumerate(tel_list):
                    if tel_code not in all_coords:
                        logger.debug(f"Telescope {tel_code} not found in source {source}")
                        continue
                    coord_pairs = all_coords[tel_code]
                    valid_pairs = [(t.mjd, float(c[0]), float(c[1])) for t, c in zip(all_times, coord_pairs)
                                if c[0] is not None and c[1] is not None]
                    if valid_pairs:
                        times_mjd, az, el = zip(*sorted(valid_pairs))
                        color_idx = tel_idx % len(self.moderate2_colors)
                        ax = axes[tel_idx] if tel_idx < len(axes) else axes[-1]
                        ax.plot(times_mjd, az, label=f"{source}, {coord_type[:2]}",
                                color=self.moderate2_colors[color_idx])
                        ax.plot(times_mjd, el, label=f"{source}, {coord_type[2:]}",
                                linestyle='--', color=self.moderate2_colors[color_idx])
                        ax.set_title(f"{tel_code}")
                        ax.set_xlabel("Time (MJD)")
                        ax.set_ylabel(f"Angle ({coord_type[:2]}/{coord_type[2:]}, deg)")
                        ax.grid(True)
                        ax.legend()
                        plotted_telescopes.add(tel_code)
                        result["points"] += len(valid_pairs)

            # Hide unused subplots
            for idx in range(len(tel_list), len(axes)):
                axes[idx].set_visible(False)

            # Adjust layout
            fig.suptitle(f"{coord_type} for Observation: {obj.get_observation_code()}", fontsize=14)
            plt.tight_layout(rect=[0, 0, 1, 0.95])

            result["telescopes"] = len(plotted_telescopes)
            logger.debug(f"Visualization result: {result}")
            return result

    def _plot_time_on_source(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot time on source for an Observation with flexible filtering.

        Args:
            obj: Observation object containing the time on source data.
            attributes: Dictionary with visualization parameters, including 'store_key', 'source_name',
                        'telescopes', 'scans', and 'time_range'.
            fig: Matplotlib figure object for plotting.

        Returns:
            Dict containing metadata about the plotted data (e.g., number of scans, telescopes, and time blocks).
        """
        with self._lock:
            logger.debug(f"Plotting time on source for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "time_on_source")
            source_name = attributes.get("source_name", None)
            telescopes = attributes.get("telescopes", None)
            scans = attributes.get("scans", None)
            time_range = attributes.get("time_range", None)

            logger.debug(f"Input attributes: store_key={store_key}, source_name={source_name}, "
                        f"telescopes={telescopes}, scans={scans}, time_range={time_range}")

            # Create axis even if no data is plotted
            ax = fig.add_subplot(111)
            ax.set_xlabel("Time (MJD)")
            ax.set_ylabel("Telescope")
            ax.set_title(f"Time on Source for Observation: {obj.get_observation_code()}")
            ax.grid(True, axis="x")

            # Check if required parameters are provided
            if not (source_name or telescopes or scans):
                logger.debug("No source, telescopes, or scans specified, returning empty plot")
                return {"scans": 0, "telescopes": 0, "points": 0, "intersections": 0}

            # Retrieve time on source data
            data = obj.get_calculated_data_by_key(store_key)
            if not data:
                logger.error(f"No time on source data found for '{store_key}' in {obj.get_observation_code()}")
                return {"scans": 0, "telescopes": 0, "points": 0, "intersections": 0}

            # Validate data structure
            data = data.get("data", {})
            if not isinstance(data, dict):
                logger.warning(f"Invalid data type: data={type(data)} in {obj.get_observation_code()}")
                return {"scans": 0, "telescopes": 0, "points": 0, "intersections": 0}
            if not data:
                logger.warning(f"Empty time on source data in {obj.get_observation_code()}")
                return {"scans": 0, "telescopes": 0, "points": 0, "intersections": 0}

            # Default to first source if none specified
            sources = [source_name] if source_name else list(data.keys())[:1]
            if not sources:
                logger.debug("No sources available, returning empty plot")
                return {"scans": 0, "telescopes": 0, "points": 0, "intersections": 0}

            result = {"scans": 0, "telescopes": 0, "points": 0, "intersections": 0}
            plotted_telescopes = set()
            all_blocks = {}

            for source in sources:
                if source not in data:
                    logger.warning(f"Source {source} not found in time on source data")
                    continue
                source_data = data[source]

                # Filter scans (use all if none specified)
                scan_list = scans if scans else list(source_data.keys())
                result["scans"] += len(scan_list)
                logger.debug(f"Scans to process for source {source}: {scan_list}")

                for scan in scan_list:
                    if scan not in source_data:
                        logger.debug(f"Scan {scan} not found for source {source}")
                        continue
                    scan_data = source_data[scan]

                    # Determine telescopes to plot
                    tel_list = telescopes if telescopes else list(scan_data.keys())
                    for tel_code in tel_list:
                        if tel_code not in scan_data:
                            logger.debug(f"Telescope {tel_code} not found in scan {scan}, source {source}")
                            continue
                        blocks = scan_data[tel_code]
                        # Convert numpy array to list if necessary
                        if isinstance(blocks, np.ndarray):
                            blocks = blocks.tolist()
                        if not blocks or len(blocks) == 0:
                            logger.debug(f"No time blocks for {tel_code} in scan {scan}, source {source}")
                            continue
                        if tel_code not in all_blocks:
                            all_blocks[tel_code] = []
                        # Filter blocks by time range if specified
                        for block in blocks:
                            try:
                                if isinstance(block[0], (int, float)):
                                    start_mjd = float(block[0])
                                else:
                                    start_mjd = Time(block[0]).mjd
                                if isinstance(block[1], (int, float)):
                                    end_mjd = float(block[1])
                                else:
                                    end_mjd = Time(block[1]).mjd
                                duration = float(block[2])  # Duration in seconds
                                # Verify duration consistency
                                calculated_duration = (end_mjd - start_mjd) * 86400
                                if abs(calculated_duration - duration) > 1e-6:
                                    logger.warning(f"Duration mismatch for {tel_code} in scan {scan}, source {source}: "
                                                f"stored={duration}s, calculated={calculated_duration}s")
                                if time_range:
                                    start_range, end_range = time_range
                                    if start_mjd >= end_range or end_mjd <= start_range:
                                        continue
                                all_blocks[tel_code].append((start_mjd, end_mjd, duration))
                            except (ValueError, TypeError) as e:
                                logger.error(f"Invalid block format for {tel_code} in scan {scan}, source {source}: {block}, error: {str(e)}")
                                continue

            # Sort telescopes for consistent plotting
            tel_list = sorted(all_blocks.keys())
            result["telescopes"] = len(tel_list)
            if not tel_list:
                logger.debug("No valid telescopes to plot after filtering")
                return {"scans": result["scans"], "telescopes": 0, "points": 0, "intersections": 0}

            # Plot time blocks for each telescope
            for i, tel in enumerate(tel_list):
                color_idx = i % len(self.moderate2_colors)
                for start_mjd, end_mjd, _ in all_blocks[tel]:
                    ax.fill_between(
                        [start_mjd, end_mjd],
                        [i, i],
                        [i + 1, i + 1],
                        color=self.moderate2_colors[color_idx],
                        alpha=0.5,
                        label=tel if tel not in plotted_telescopes else None
                    )
                    plotted_telescopes.add(tel)

            # Calculate intersections
            if tel_list and all_blocks:
                all_times = [[(start, end) for start, end, _ in all_blocks[tel]] for tel in tel_list]
                if all_times and all(all_times):  # Проверяем, что списки не пустые
                    # Собираем все временные точки
                    time_points = sorted(set(t for tel_times in all_times for start, end in tel_times for t in (start, end)))
                    intersection_times = []
                    for i in range(len(time_points) - 1):
                        start, end = time_points[i], time_points[i + 1]
                        # Проверяем, что каждый телескоп активен в интервале [start, end]
                        all_active = all(
                            any(start_t <= end and end_t >= start for start_t, end_t in tel_times)
                            for tel_times in all_times
                        )
                        if all_active:
                            intersection_times.append((start, end))
                    
                    # Визуализация пересечений
                    for i, (start, end) in enumerate(intersection_times):
                        ax.fill_between(
                            [start, end],
                            [-1, -1],
                            [0, 0],
                            color=self.intersection_color,
                            alpha=0.9,
                            label="Total Intersection" if i == 0 else None
                        )
                    result["intersections"] = len(intersection_times)
                else:
                    logger.debug("No valid time blocks for intersection calculation")
            else:
                logger.debug("No telescopes or blocks to calculate intersections")

            # Set y-axis labels
            ax.set_yticks(np.arange(-1, len(tel_list)))
            ax.set_yticklabels(["Total Intersection"] + tel_list)
            if plotted_telescopes:
                ax.legend()

            logger.debug(f"Visualization result: {result}")
            return result

    def _plot_beam_pattern(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot beam patterns for an Observation with one subplot per telescope, showing patterns for specified frequencies.

        Args:
            obj: Observation object containing the beam pattern data.
            attributes: Dictionary with visualization parameters, including 'store_key', 'freq_names', and 'telescopes'.
            fig: Matplotlib figure object for plotting.

        Returns:
            Dict containing metadata about the plotted data (e.g., number of telescopes, frequencies).
        """
        with self._lock:
            logger.debug(f"Plotting beam pattern for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "beam_pattern")
            freq_names = attributes.get("freq_names", None)
            telescopes = attributes.get("telescopes", None)
            SPEED_OF_LIGHT = 299792458.0

            logger.debug(f"Input attributes: store_key={store_key}, freq_names={freq_names}, telescopes={telescopes}")

            if not (telescopes or freq_names):
                logger.debug("No telescopes or frequencies specified, returning empty plot")
                ax = fig.add_subplot(111)
                ax.set_xlabel("Theta (radians)")
                ax.set_ylabel("Normalized Peak Flux (Jy)")
                ax.grid(True)
                return {"telescopes": 0, "frequencies": 0}

            beam_data = obj.get_calculated_data_by_key(store_key)
            logger.debug(f"Retrieved beam_data: {beam_data}")

            if not isinstance(beam_data, dict):
                logger.warning(f"Invalid data type: beam_data={type(beam_data)} in {obj.get_observation_code()}")
                ax = fig.add_subplot(111)
                ax.set_xlabel("Theta (radians)")
                ax.set_ylabel("Normalized Peak Flux (Jy)")
                ax.grid(True)
                return {"telescopes": 0, "frequencies": 0}

            beam_data = beam_data.get("data", {})
            logger.debug(f"Beam data (post-extraction): {beam_data}")
            if not beam_data:
                logger.warning(f"Empty beam data in {obj.get_observation_code()}")
                ax = fig.add_subplot(111)
                ax.set_xlabel("Theta (radians)")
                ax.set_ylabel("Normalized Peak Flux (Jy)")
                ax.grid(True)
                return {"telescopes": 0, "frequencies": 0}

            all_telescopes = list(beam_data.keys())
            tel_list = sorted(telescopes if telescopes else all_telescopes)
            if not tel_list:
                logger.debug("No telescopes available, returning empty plot")
                ax = fig.add_subplot(111)
                ax.set_xlabel("Theta (radians)")
                ax.set_ylabel("Normalized Peak Flux (Jy)")
                ax.grid(True)
                return {"telescopes": 0, "frequencies": 0}

            freq_list = (
                [float(f) for f in (freq_names if isinstance(freq_names, list) else [freq_names]) if f]
                if freq_names else []
            )
            if not freq_list:
                freq_list = [float(f.get("frequency")) for f in obj.get_frequencies().get_items()]
                logger.debug(f"No frequencies specified, using observation frequencies: {freq_list}")
            if not freq_list:
                logger.warning(f"No valid frequencies available in observation or attributes")
                ax = fig.add_subplot(111)
                ax.set_xlabel("Theta (radians)")
                ax.set_ylabel("Normalized Peak Flux (Jy)")
                ax.grid(True)
                return {"telescopes": len(tel_list), "frequencies": 0}

            n_tels = len(tel_list)
            n_cols = int(np.ceil(np.sqrt(n_tels)))
            n_rows = int(np.ceil(n_tels / n_cols))
            logger.debug(f"Creating subplot grid: {n_rows} rows x {n_cols} cols for {n_tels} telescopes")
            axes = fig.subplots(n_rows, n_cols, sharex=True, sharey=True)
            axes = np.array(axes).flatten() if n_tels > 1 else [axes]

            result = {"telescopes": 0, "frequencies": len(freq_list)}
            plotted_telescopes = set()
            plotted_frequencies = set()

            for tel_idx, tel_code in enumerate(tel_list):
                if tel_code not in beam_data:
                    logger.debug(f"Telescope {tel_code} not found in beam_data, skipping")
                    continue
                ax = axes[tel_idx] if tel_idx < len(axes) else axes[-1]
                ax.grid(True)

                ax.annotate(
                    tel_code,
                    xy=(0.05, 0.95),
                    xycoords='axes fraction',
                    fontsize=10,
                    bbox=dict(boxstyle="round", facecolor='white', alpha=0.8)
                )

                beam = beam_data.get(tel_code, {})
                theta = np.array(beam.get("theta", []))
                pattern = np.array(beam.get("pattern", []))
                if len(theta) == 0 or len(pattern) == 0:
                    logger.debug(f"Empty theta or pattern for {tel_code}")
                    continue

                for freq_idx, freq_mhz in enumerate(freq_list):
                    wavelength = SPEED_OF_LIGHT / (freq_mhz * 1e6)
                    scaling_factor = 1.0 / wavelength**2
                    logger.debug(f"Tel {tel_code}, freq {freq_mhz} MHz, wavelength={wavelength}, scaling_factor={scaling_factor}")

                    scaled_pattern = pattern * scaling_factor
                    logger.debug(f"Scaled pattern for {tel_code} at {freq_mhz}: {scaled_pattern[:5]}")

                    color_idx = freq_idx % len(self.moderate2_colors)
                    ax.plot(
                        theta, scaled_pattern,
                        label=f"{freq_mhz:.2f} MHz",
                        color=self.moderate2_colors[color_idx]
                    )
                    theta_range = np.max(np.abs(theta)) * 1.1 if len(theta) > 0 else 1.0
                    ax.set_xlim(-theta_range, theta_range)
                    ax.legend(fontsize=8)

                    plotted_telescopes.add(tel_code)
                    plotted_frequencies.add(freq_mhz)

            for idx in range(len(tel_list), len(axes)):
                axes[idx].set_visible(False)

            fig.text(0.5, 0.04, "Theta (radians)", ha='center', fontsize=12)
            fig.text(0.04, 0.5, "Normalized Peak Flux (Jy)", va='center', rotation='vertical', fontsize=12)

            fig.suptitle(f"Beam Pattern for Observation: {obj.get_observation_code()}", fontsize=14)
            plt.tight_layout(rect=[0.05, 0.05, 1, 0.95])

            result["telescopes"] = len(plotted_telescopes)
            result["frequencies"] = len(plotted_frequencies)
            logger.debug(f"Visualization result: {result}")
            return result

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
        """Plot baseline projections for an Observation with flexible filtering and frequency scaling.

        Args:
            obj: Observation object containing the baseline projections data.
            attributes: Dictionary with visualization parameters, including 'store_key', 'times_key',
                        'baselines', 'source_name', 'scans', 'time_range', 'frequencies', and 'units'.
            fig: Matplotlib figure object for plotting.

        Returns:
            Dict containing metadata about the plotted data (e.g., number of scans, baselines, projections, and frequencies).
        """
        with self._lock:
            logger.debug(f"Plotting baseline projections for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "baseline_projections")
            times_key = attributes.get("times_key", "times")
            baselines = attributes.get("baselines", None)
            source_name = attributes.get("source_name", None)
            scans = attributes.get("scans", None)
            time_range = attributes.get("time_range", None)
            frequencies = attributes.get("frequencies", None)
            units = attributes.get("units", "meters")

            logger.debug(f"Input attributes: store_key={store_key}, times_key={times_key}, "
                        f"baselines={baselines}, source_name={source_name}, scans={scans}, "
                        f"time_range={time_range}, frequencies={frequencies}, units={units}")

            # Create axis even if no data is plotted
            ax = fig.add_subplot(111)
            ax.set_xlabel("Time (MJD)")
            ax.set_ylabel(f"Baseline Length ({units})")
            ax.set_title(f"Baseline Projections for Observation: {obj.get_observation_code()}")
            ax.grid(True)

            # Check if required parameters are provided
            if not (source_name or baselines or scans or frequencies):
                logger.debug("No source, baselines, scans, or frequencies specified, returning empty plot")
                return {"scans": 0, "baselines": 0, "projections": 0, "frequencies": 0}

            # Retrieve baseline projections and time data
            bl_data = obj.get_calculated_data_by_key(store_key)
            times_data = obj.get_calculated_data_by_key(times_key)
            logger.debug(f"Retrieved bl_data: {bl_data}")
            logger.debug(f"Retrieved times_data: {times_data}")

            # Validate data structure
            if not isinstance(bl_data, dict) or not isinstance(times_data, dict):
                logger.warning(f"Invalid data type: bl_data={type(bl_data)}, times_data={type(times_data)} in {obj.get_observation_code()}")
                return {"scans": 0, "baselines": 0, "projections": 0, "frequencies": 0}

            bl_data = bl_data.get("data", {})
            times_data = times_data.get("data", {})
            logger.debug(f"Baseline projections data (post-extraction): {bl_data}")
            logger.debug(f"Times data (post-extraction): {times_data}")
            if not bl_data or not times_data:
                logger.warning(f"Empty data: bl_data={bool(bl_data)}, times_data={bool(times_data)} in {obj.get_observation_code()}")
                return {"scans": 0, "baselines": 0, "projections": 0, "frequencies": 0}

            # Default to first source if none specified
            sources = [source_name] if source_name else list(bl_data.keys())[:1]
            if not sources:
                logger.debug("No sources available, returning empty plot")
                return {"scans": 0, "baselines": 0, "projections": 0, "frequencies": 0}

            result = {"scans": 0, "baselines": 0, "projections": 0, "frequencies": len(frequencies) if frequencies else 0}
            plotted_pairs = set()
            SPEED_OF_LIGHT = 299792458.0
            EARTH_DIAMETER = 12742000.0

            for source in sources:
                if source not in bl_data or source not in times_data:
                    logger.warning(f"Source {source} not found in baseline projections or times data")
                    continue
                source_bl = bl_data[source]
                source_times = times_data[source]
                logger.debug(f"Processing source {source}")

                # Collect all data across scans
                all_times = []
                all_bl_points = {}
                scan_list = scans if scans else list(source_bl.keys())
                result["scans"] += len(scan_list)
                logger.debug(f"Scans to process: {scan_list}")

                for scan in scan_list:
                    if scan not in source_bl or scan not in source_times:
                        logger.debug(f"Scan {scan} not found for source {source}")
                        continue
                    times = []
                    for t in source_times[scan]:
                        if t and hasattr(t, 'mjd'):
                            times.append(t.mjd)
                        else:
                            logger.debug(f"Invalid time entry in scan {scan}, source {source}: {t}")
                    if not times:
                        logger.debug(f"No valid times for scan {scan}, source {source}")
                        continue
                    all_times.extend(times)
                    bl_points = source_bl[scan]
                    for pair in bl_points:
                        if pair not in all_bl_points:
                            all_bl_points[pair] = []
                        all_bl_points[pair].extend([float(p) for p in bl_points[pair] if p is not None])

                # Ensure data consistency
                if not all_times or not all_bl_points:
                    logger.debug(f"No valid times or baseline points for source {source}")
                    continue

                # Sort all times and projections by time
                time_indices = np.argsort(all_times)
                all_times = [all_times[i] for i in time_indices]
                for pair in all_bl_points:
                    if len(all_bl_points[pair]) != len(all_times):
                        logger.warning(f"Mismatch in lengths for {pair}: times={len(all_times)}, bl_points={len(all_bl_points[pair])}")
                        min_len = min(len(all_times), len(all_bl_points[pair]))
                        all_times = all_times[:min_len]
                        all_bl_points[pair] = all_bl_points[pair][:min_len]
                    all_bl_points[pair] = [all_bl_points[pair][i] for i in time_indices if i < len(all_bl_points[pair])]

                # Apply time range filter
                if time_range:
                    start_mjd, end_mjd = time_range
                    valid_indices = [i for i, t in enumerate(all_times) if start_mjd <= t <= end_mjd]
                    all_times = [all_times[i] for i in valid_indices]
                    for pair in all_bl_points:
                        all_bl_points[pair] = [all_bl_points[pair][i] for i in valid_indices if i < len(all_bl_points[pair])]
                    logger.debug(f"After time range filter: times={len(all_times)}")
                    if not all_times:
                        logger.debug(f"No valid times in range {time_range} for source {source}")
                        continue

                # Process each frequency
                for freq_mhz in (frequencies or [None]):
                    wavelength = SPEED_OF_LIGHT / (freq_mhz * 1e6) if freq_mhz else 1.0
                    scaling_factor = 1.0 if units == "meters" else (wavelength / EARTH_DIAMETER)
                    logger.debug(f"Frequency {freq_mhz} MHz, wavelength={wavelength}, scaling_factor={scaling_factor}")

                    for pair in all_bl_points:
                        if baselines and pair not in baselines:
                            logger.debug(f"Skipping pair {pair} not in baselines {baselines}")
                            continue
                        if len(all_bl_points[pair]) == 0:
                            logger.debug(f"No valid baseline projections for {pair} in source {source}")
                            continue
                        try:
                            valid_projs = np.array(all_bl_points[pair], dtype=float)
                            valid_projs = valid_projs[~np.isnan(valid_projs)]
                            if len(valid_projs) == 0:
                                logger.debug(f"No valid projections after filtering for {pair} in source {source}")
                                continue
                            if len(valid_projs) != len(all_times):
                                logger.warning(f"Mismatch in lengths for {pair}: times={len(all_times)}, valid_projs={len(valid_projs)}")
                                min_len = min(len(all_times), len(valid_projs))
                                valid_projs = valid_projs[:min_len]
                                times_subset = all_times[:min_len]
                            else:
                                times_subset = all_times
                            bl_scaled = valid_projs / wavelength * scaling_factor if freq_mhz else valid_projs
                            logger.debug(f"Scaled projections: bl={bl_scaled[:5]}")
                            color_idx = (len(plotted_pairs) + (frequencies.index(freq_mhz) if frequencies and freq_mhz else 0)) % len(self.moderate2_colors)
                            label = f"{pair} ({freq_mhz} MHz)" if freq_mhz else f"{pair}"
                            ax.scatter(times_subset, bl_scaled, s=10, c=[self.moderate2_colors[color_idx]], label=label, alpha=0.7)
                            plotted_pairs.add(f"{pair}_{freq_mhz}" if freq_mhz else pair)
                            result["projections"] += len(bl_scaled)
                        except Exception as e:
                            logger.error(f"Error processing projections for {pair} at {freq_mhz} MHz: {str(e)}")
                            continue

            result["baselines"] = len(plotted_pairs)
            if plotted_pairs:
                ax.legend()
            logger.debug(f"Visualization result: {result}")
            return result

    def _plot_mollweide_tracks(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot Mollweide tracks for an Observation with flexible filtering.

        Args:
            obj: Observation object containing the Mollweide tracks data.
            attributes: Dictionary with visualization parameters, including 'store_key', 'scans',
                        'telescopes', and 'time_range'.
            fig: Matplotlib figure object for plotting.

        Returns:
            Dict containing metadata about the plotted data (e.g., number of scans, telescopes, sources, and points).
        """
        with self._lock:
            logger.debug(f"Plotting Mollweide tracks for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "mollweide_tracks")
            telescopes = attributes.get("telescopes", None)
            scans = attributes.get("scans", None)
            time_range = attributes.get("time_range", None)

            logger.debug(f"Input attributes: store_key={store_key}, "
                        f"telescopes={telescopes}, scans={scans}, time_range={time_range}")

            ax = fig.add_subplot(111, projection="mollweide")
            ax.set_title(f"Mollweide Tracks for Observation: {obj.get_observation_code()}")
            ax.grid(True)

            if not (telescopes or scans):
                logger.debug("No telescopes or scans specified, returning empty plot")
                return {"scans": 0, "telescopes": 0, "sources": 0, "points": 0}

            data = obj.get_calculated_data_by_key(store_key)
            if not data:
                logger.error(f"No Mollweide tracks data found for '{store_key}' in {obj.get_observation_code()}")
                return {"scans": 0, "telescopes": 0, "sources": 0, "points": 0}

            if not isinstance(data, dict):
                logger.warning(f"Invalid data type: data={type(data)} in {obj.get_observation_code()}")
                return {"scans": 0, "telescopes": 0, "sources": 0, "points": 0}

            metadata = data.get("metadata", {})
            tracks_data = data.get("data", {})
            if not tracks_data:
                logger.warning(f"Empty Mollweide tracks data in {obj.get_observation_code()}")
                return {"scans": 0, "telescopes": 0, "sources": 0, "points": 0}

            result = {"scans": 0, "telescopes": 0, "sources": 0, "points": 0}
            plotted_telescopes = set()
            plotted_sources = set()

            sources = metadata.get("sources", [])
            for source in sources:
                lon_rad = np.radians(source["lon"])
                lat_rad = np.radians(source["lat"])
                ax.scatter(lon_rad, lat_rad, c='red', marker='o', s=50, label=f"Source: {source['name']}",
                          zorder=2)
                plotted_sources.add(source['name'])
                result["sources"] += 1

            scan_list = scans if scans else list(tracks_data.keys())
            result["scans"] = len(scan_list)
            logger.debug(f"Scans to process: {scan_list}")

            # Collect all tracks by telescope
            all_tracks = {}
            for scan_name in scan_list:
                if scan_name not in tracks_data:
                    logger.debug(f"Scan {scan_name} not found in Mollweide tracks data")
                    continue
                scan_data = tracks_data[scan_name]
                tel_list = telescopes if telescopes else list(scan_data.keys())
                for tel_code in tel_list:
                    if tel_code not in scan_data:
                        logger.debug(f"Telescope {tel_code} not found in scan {scan_name}")
                        continue
                    tracks = scan_data[tel_code]
                    if not isinstance(tracks, np.ndarray) or len(tracks) == 0:
                        logger.debug(f"No valid tracks for {tel_code} in scan {scan_name}")
                        continue
                    if tracks.ndim != 2 or tracks.shape[1] != 2:
                        logger.warning(f"Invalid track format for {tel_code} in scan {scan_name}: shape={tracks.shape}")
                        continue
                    if tel_code not in all_tracks:
                        all_tracks[tel_code] = []
                    all_tracks[tel_code].append(tracks)

            # Plot combined tracks
            for tel_code in all_tracks:
                try:
                    tracks = np.vstack(all_tracks[tel_code]) if all_tracks[tel_code] else np.array([])
                    if len(tracks) == 0:
                        logger.debug(f"No valid tracks for {tel_code} after combining scans")
                        continue
                    lon, lat = tracks[:, 0], tracks[:, 1]
                    valid_mask = (~np.isnan(lon)) & (~np.isnan(lat))
                    lon = lon[valid_mask]
                    lat = lat[valid_mask]
                    if len(lon) == 0:
                        logger.debug(f"No valid track points for {tel_code}")
                        continue
                    lon_rad = np.radians(lon)
                    lat_rad = np.radians(lat)
                    color_idx = len(plotted_telescopes) % len(self.moderate2_colors)
                    ax.scatter(lon_rad, lat_rad, s=1, c=[self.moderate2_colors[color_idx]],
                              label=f"{tel_code}" if tel_code not in plotted_telescopes else None,
                              zorder=1)
                    plotted_telescopes.add(tel_code)
                    result["points"] += len(lon)
                except Exception as e:
                    logger.error(f"Error plotting tracks for {tel_code}: {str(e)}")
                    continue

            result["telescopes"] = len(plotted_telescopes)
            result["sources"] = len(plotted_sources)
            if plotted_telescopes or plotted_sources:
                ax.legend(loc='upper right', bbox_to_anchor=(1.15, 1), fontsize=8)

            logger.debug(f"Visualization result: {result}")
            return result

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