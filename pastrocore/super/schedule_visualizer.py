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
import xarray as xr
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
        """Plot UV coverage for an Observation using scatter points.

        Args:
            obj: Observation object containing the UV coverage data.
            attributes: Dictionary with visualization parameters, including 'store_key'.
            fig: Matplotlib figure object for plotting.

        Returns:
            Dict containing metadata about the plotted data (e.g., number of baselines).
        """
        with self._lock:
            logger.debug(f"Plotting UV coverage for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "uv_coverage")
            data = obj.get_calculated_data_by_key(store_key)
            if not data or not data.data_vars:
                logger.error(f"No UV coverage data found for '{store_key}' in {obj.get_observation_code()}")
                return {}

            ax = fig.add_subplot(111)
            plotted_baselines = set()
            valid_points = 0

            for scan in data.scan.values:
                scan_data = data.sel(scan=scan)
                source = scan_data.source.values
                u = scan_data.get("uv_points").sel(coord="u").values
                v = scan_data.get("uv_points").sel(coord="v").values
                if "baseline" not in scan_data.coords:
                    logger.warning(f"No baseline coordinate found for scan {scan}")
                    continue
                for baseline in scan_data.baseline.values:
                    baseline_data = scan_data.sel(baseline=baseline)
                    u = baseline_data.uv_points.sel(coord="u").values.flatten()
                    v = baseline_data.uv_points.sel(coord="v").values.flatten()
                    mask = np.logical_and(~np.isnan(u), ~np.isnan(v))
                    if not mask.any():
                        logger.debug(f"No valid UV points for scan {scan}, baseline {baseline}")
                        continue
                    if baseline not in plotted_baselines:
                        color_idx = len(plotted_baselines) % len(self.moderate2_colors)
                        ax.scatter(u[mask], v[mask], s=1, c=[self.moderate2_colors[color_idx]], label=f"{baseline} ({source})")
                    ax.scatter(
                        -u[mask],
                        -v[mask],
                        s=1,
                        c=[self.moderate2_colors[color_idx]]                )
                    plotted_baselines.add(baseline)
                    valid_points += mask.sum()

            ax.set_xlabel("u (wavelengths)")
            ax.set_ylabel("v (wavelengths)")
            ax.set_title(f"UV Coverage for {obj.get_observation_code()}")
            ax.grid(True)
            ax.legend()
            ax.invert_xaxis
            return {"baselines": len(plotted_baselines), "points": valid_points, "scans": len(data.scan)}

    def _plot_source_visibility(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot source visibility for an Observation.

        Args:
            obj: Observation object containing the source visibility data.
            attributes: Dictionary with visualization parameters, including 'store_key' and 'time_step'.
            fig: Matplotlib figure object for plotting.

        Returns:
            Dict containing metadata about the plotted data (e.g., number of scans).
        """
        with self._lock:
            logger.debug(f"Plotting source visibility for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "source_visibility")
            data = obj.get_calculated_data_by_key(store_key)
            if not data or not data.data_vars:
                logger.error(f"No source visibility data found for '{store_key}' in {obj.get_observation_code()}")
                return {}

            ax = fig.add_subplot(111)
            plotted_telescopes = set()
            valid_points = 0

            for scan in data.scan.values:
                scan_data = data.sel(scan=scan)
                if "time" not in scan_data.coords or not scan_data.time.size:
                    logger.warning(f"No valid times for scan {scan}")
                    continue
                source = scan_data.source.item()  # Получаем скалярное значение source
                times_mjd = np.array([Time(t).mjd for t in scan_data.time.values])
                for telescope in scan_data.telescope.values:
                    visibility = scan_data.visibility.sel(telescope=telescope).values
                    mask = ~np.isnan(visibility)
                    if not mask.any():
                        logger.debug(f"No valid visibility data for telescope {telescope} in scan {scan}")
                        continue
                    if telescope not in plotted_telescopes:
                        color_idx = len(plotted_telescopes) % len(self.moderate2_colors)
                        ax.plot(
                            times_mjd[mask],
                            visibility[mask],
                            label=f"{telescope} ({source})",
                            marker="o" if not attributes.get("time_step") else None,
                            color=self.moderate2_colors[color_idx]
                        )
                        plotted_telescopes.add(telescope)
                        valid_points += mask.sum()

            ax.set_xlabel("Time (MJD)")
            ax.set_ylabel("Visible (1 = Yes, 0 = No)")
            ax.set_title(f"Source Visibility for {obj.get_observation_code()}")
            ax.legend()
            ax.grid(True)
            return {"scans": len(data.scan), "telescopes": len(plotted_telescopes), "points": valid_points}

    def _plot_sun_angles(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot angles to the Sun for an Observation.

        Args:
            obj: Observation object containing the sun angles data.
            attributes: Dictionary with visualization parameters, including 'store_key'.
            fig: Matplotlib figure object for plotting.

        Returns:
            Dict containing metadata about the plotted data (e.g., number of scans).
        """
        with self._lock:
            logger.debug(f"Plotting sun angles for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "sun_angles")
            data = obj.get_calculated_data_by_key(store_key)
            if not data or not data.data_vars:
                logger.error(f"No sun angles data found for '{store_key}' in {obj.get_observation_code()}")
                return {}

            ax = fig.add_subplot(111)
            plotted_telescopes = set()
            valid_points = 0

            for scan in data.scan.values:
                scan_data = data.sel(scan=scan)
                if "time" not in scan_data.coords or not scan_data.time.size:
                    logger.warning(f"No valid times for scan {scan}")
                    continue
                source = scan_data.source.item() if isinstance(scan_data.source, xr.DataArray) else scan_data.source
                times_mjd = [Time(t).mjd for t in scan_data.time.values]
                for telescope in scan_data.telescope.values:
                    # Используем 'sun_angles' вместо 'angles'
                    angles = scan_data.sun_angles.sel(telescope=telescope).values
                    mask = ~np.isnan(angles)
                    if not mask.any():
                        logger.debug(f"No valid angles for telescope {telescope} in scan {scan}")
                        continue
                    if telescope not in plotted_telescopes:
                        color_idx = len(plotted_telescopes) % len(self.moderate2_colors)
                        ax.plot(
                            np.array(times_mjd)[mask],
                            angles[mask],
                            label=f"{telescope} ({source})",
                            color=self.moderate2_colors[color_idx]
                        )
                        plotted_telescopes.add(telescope)
                        valid_points += mask.sum()

            ax.set_xlabel("Time (MJD)")
            ax.set_ylabel("Angle to Sun (degrees)")
            ax.set_title(f"Sun Angles for {obj.get_observation_code()}")
            ax.legend()
            ax.grid(True)
            return {"scans": len(data.scan), "telescopes": len(plotted_telescopes), "points": valid_points}

    def _plot_az_el(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot Azimuth/Elevation or Hour Angle/Declination for an Observation.

        Args:
            obj: Observation object containing the az/el data.
            attributes: Dictionary with visualization parameters, including 'store_key'.
            fig: Matplotlib figure object for plotting.

        Returns:
            Dict containing metadata about the plotted data (e.g., number of scans).
        """
        with self._lock:
            logger.debug(f"Plotting Az/El for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "az_el")
            data = obj.get_calculated_data_by_key(store_key)
            if not data or not data.data_vars:
                logger.error(f"No Az/El data found for '{store_key}' in {obj.get_observation_code()}")
                return {}

            all_telescopes = {}
            for scan in data.scan.values:
                scan_data = data.sel(scan=scan)
                if "time" not in scan_data.coords or not scan_data.time.size:
                    logger.warning(f"No valid times for scan {scan}")
                    continue
                source = scan_data.source.values
                times_mjd = [Time(t).mjd for t in scan_data.time.values]
                for telescope in scan_data.telescope.values:
                    if "coord" not in scan_data.coords:
                        logger.warning(f"No coord dimension for scan {scan}, telescope {telescope}")
                        continue
                    if telescope not in all_telescopes:
                        all_telescopes[telescope] = {"times": [], "az": [], "el": [], "coord_type": scan_data.attrs.get("coord_type", "AzEl")}
                    az = scan_data.coords.sel(telescope=telescope, coord="az").values
                    el = scan_data.coords.sel(telescope=telescope, coord="el").values
                    mask = ~np.isnan(az) & ~np.isnan(el)
                    if mask.any():
                        all_telescopes[telescope]["times"].extend(np.array(times_mjd)[mask])
                        all_telescopes[telescope]["az"].extend(az[mask])
                        all_telescopes[telescope]["el"].extend(el[mask])

            n_tels = len(all_telescopes)
            if n_tels == 0:
                logger.warning(f"No valid Az/El data for {obj.get_observation_code()}")
                return {}

            if n_tels == 1:
                ax = fig.add_subplot(111)
                axes = [ax]
            else:
                axes = fig.subplots(n_tels, 1, sharex=False, sharey=False)

            for i, (tel_code, tel_data) in enumerate(all_telescopes.items()):
                ax = axes[i] if n_tels > 1 else axes[0]
                color = self.moderate2_colors[i % len(self.moderate2_colors)]
                coord_type = tel_data["coord_type"]
                ax.plot(tel_data["times"], tel_data["az"], label=f"{coord_type[:2]}", color=color)
                ax.plot(tel_data["times"], tel_data["el"], label=f"{coord_type[2:]}", linestyle="--", color=color)
                ax.set_xlabel("Time (MJD)")
                ax.set_ylabel("Angle (deg)")
                ax.set_title(f"Telescope: {tel_code}")
                ax.legend(loc="upper right")
                ax.grid(True)

            fig.suptitle(f"Az/El or HA/Dec for {obj.get_observation_code()}", y=1.02)
            return {"scans": len(data.scan), "telescopes": n_tels}

    def _plot_time_on_source(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot time on source for an Observation.

        Args:
            obj: Observation object containing the time on source data.
            attributes: Dictionary with visualization parameters, including 'store_key'.
            fig: Matplotlib figure object for plotting.

        Returns:
            Dict containing metadata about the plotted data (e.g., number of telescopes).
        """
        with self._lock:
            logger.debug(f"Plotting time on source for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "time_on_source")
            data = obj.get_calculated_data_by_key(store_key)
            if not data or not data.data_vars:
                logger.error(f"No time on source data found for '{store_key}' in {obj.get_observation_code()}")
                return {}

            if "visibility_blocks" not in data.data_vars or "source" not in data.coords or "telescope" not in data.coords:
                logger.error(f"Missing visibility_blocks, source, or telescope in data for {store_key}")
                return {}

            telescopes = data.telescope.values
            logger.debug(f"Telescopes: {list(telescopes)}, Sources: {list(data.source.values)}, Blocks: {list(data.block.values)}")
            ax = fig.add_subplot(111)
            all_times = {tel: [] for tel in telescopes}
            valid_blocks = 0

            for source in data.source.values:
                source_data = data.sel(source=source)
                if "block" not in source_data.coords:
                    logger.warning(f"No block coordinate for source {source}")
                    continue
                for telescope in telescopes:
                    blocks = source_data.visibility_blocks.sel(telescope=telescope)
                    logger.debug(f"Processing blocks for source {source}, telescope {telescope}: {blocks.values}")
                    for block_idx in blocks.block.values:
                        block = blocks.sel(block=block_idx)
                        if block.isnull().item() or block.item() is None:
                            logger.debug(f"Skipping null block for telescope {telescope}, source {source}, block {block_idx}")
                            continue
                        block_dict = block.item()
                        if not isinstance(block_dict, dict):
                            logger.debug(f"Block is not a dict for telescope {telescope}, source {source}, block {block_idx}: {block_dict}")
                            continue
                        if "start" not in block_dict or "duration" not in block_dict:
                            logger.debug(f"Missing start or duration in block for telescope {telescope}, source {source}, block {block_idx}: {block_dict}")
                            continue
                        start = block_dict["start"]
                        duration = block_dict["duration"]
                        try:
                            start_mjd = Time(start).mjd
                            end_mjd = Time(start).mjd + (duration / 86400.0)  # duration в секундах, переводим в дни
                            logger.debug(f"Plotting block: telescope {telescope}, source {source}, block {block_idx}, start {start}, duration {duration}")
                        except Exception as e:
                            logger.debug(f"Invalid time data for telescope {telescope}, source {source}, block {block_idx}: {str(e)}")
                            continue
                        ax.fill_between(
                            [start_mjd, end_mjd],
                            [list(telescopes).index(telescope), list(telescopes).index(telescope)],
                            [list(telescopes).index(telescope) + 1, list(telescopes).index(telescope) + 1],
                            color=self.moderate2_colors[list(telescopes).index(telescope) % len(self.moderate2_colors)],
                            alpha=0.5
                        )
                        all_times[telescope].append((start_mjd, end_mjd))
                        valid_blocks += 1

            if valid_blocks == 0:
                logger.warning(f"No valid blocks found for plotting in {obj.get_observation_code()}")
                return {"telescopes": len(telescopes), "blocks": 0, "sources": len(data.source)}

            # Вычисление пересечений времени наблюдения
            intersections = []
            time_points = sorted(set(t for tel_times in all_times.values() for start, end in tel_times for t in (start, end)))
            logger.debug(f"Time points for intersections: {time_points}")
            for t in time_points:
                active = [sum(1 for start, end in tel_times if start <= t <= end) for tel_times in all_times.values()]
                if all(a >= 1 for a in active):  # Все телескопы активны
                    intersections.append(t)

            for i in range(0, len(intersections), 2):
                if i + 1 < len(intersections):
                    start, end = intersections[i], intersections[i + 1]
                    logger.debug(f"Plotting intersection: start {start}, end {end}")
                    ax.fill_between([start, end], [-1, -1], [0, 0], color=self.intersection_color, alpha=0.7)

            ax.set_yticks(np.arange(-1, len(telescopes)))
            ax.set_yticklabels(["Total Intersection"] + list(telescopes))
            ax.set_xlabel("Time (MJD)")
            ax.set_ylabel("Telescope")
            ax.set_title(f"Time on Source ({obj.get_observation_code()})")
            ax.grid(True, axis="x")
            logger.debug(f"Returning metadata: telescopes={len(telescopes)}, blocks={valid_blocks}, sources={len(data.source)}")
            return {"telescopes": len(telescopes), "blocks": valid_blocks, "sources": len(data.source)}

    def _plot_beam_pattern(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot beam patterns for an Observation.

        Args:
            obj: Observation object containing the beam pattern data.
            attributes: Dictionary with visualization parameters, including 'store_key' and 'freq_name'.
            fig: Matplotlib figure object for plotting.

        Returns:
            Dict containing metadata about the plotted data (e.g., number of telescopes).
        """
        with self._lock:
            logger.debug(f"Plotting beam pattern for {obj.get_observation_code()}")
            freq_name = attributes.get("freq_name")
            if not freq_name:
                logger.error("No freq_name specified for beam pattern plot")
                return {}
            store_key = attributes.get("store_key", f"beam_pattern_{freq_name}")
            data = obj.get_calculated_data_by_key(store_key)
            if not data or not data.data_vars:
                logger.error(f"No beam pattern data found for '{store_key}' in {obj.get_observation_code()}")
                return {}

            if "telescope" not in data.coords or "theta" not in data.dims:
                logger.error(f"Missing telescope or theta dimensions in data for {store_key}")
                return {}

            n_tels = len(data.telescope)
            if n_tels == 1:
                ax = fig.add_subplot(111)
                axes = [ax]
            else:
                axes = fig.subplots(n_tels, 1, sharex=False, sharey=False)

            valid_tels = 0
            for i, telescope in enumerate(data.telescope.values):
                tel_data = data.sel(telescope=telescope)
                if "theta" not in tel_data.coords or "pattern" not in tel_data.data_vars:
                    logger.debug(f"Missing theta or pattern for telescope {telescope}")
                    continue
                theta = tel_data.theta.values
                pattern = tel_data.pattern.values
                if not np.all(np.isfinite(theta)) or not np.all(np.isfinite(pattern)):
                    logger.debug(f"Invalid beam pattern data for telescope {telescope}")
                    continue
                ax = axes[i] if n_tels > 1 else axes[0]
                ax.plot(theta, pattern, label=telescope, color=self.moderate2_colors[i % len(self.moderate2_colors)])
                theta_range = np.max(np.abs(theta)) * 0.05
                ax.set_xlim(-theta_range, theta_range)
                ax.set_title(f"Beam Pattern for {telescope}")
                ax.grid(True)
                valid_tels += 1

            fig.text(0.04, 0.5, "Normalized Peak Flux (Jy)", va="center", rotation="vertical")
            axes[-1].set_xlabel("Theta (radians)")
            return {"telescopes": valid_tels}

    def _plot_synthesized_beam(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot the synthesized beam for an Observation.

        Args:
            obj: Observation object containing the synthesized beam data.
            attributes: Dictionary with visualization parameters, including 'store_key' and 'freq_name'.
            fig: Matplotlib figure object for plotting.

        Returns:
            Dict containing metadata about the plotted data.
        """
        with self._lock:
            logger.debug(f"Plotting synthesized beam for {obj.get_observation_code()}")
            freq_name = attributes.get("freq_name")
            if not freq_name:
                logger.error("No freq_name specified for synthesized beam plot")
                return {}
            store_key = attributes.get("store_key", f"synthesized_beam_{freq_name}")
            data = obj.get_calculated_data_by_key(store_key)
            if not data or not data.data_vars:
                logger.error(f"No synthesized beam data found for '{store_key}' in {obj.get_observation_code()}")
                return {}

            if "theta_u" not in data.dims or "theta_v" not in data.dims or "beam_2d" not in data.data_vars:
                logger.error(f"Missing required dimensions or variables in data for {store_key}")
                return {}

            scan_data = data.sel(scan=data.scan.values[0]) if data.scan.size > 0 else data
            theta_u = scan_data.theta_u.values
            theta_v = scan_data.theta_v.values
            beam_2d = scan_data.beam_2d.values

            if theta_u.size == 0 or theta_v.size == 0 or beam_2d.size == 0:
                logger.error(f"Missing or empty data for theta_u, theta_v, or beam_2d in {obj.get_observation_code()}")
                return {}

            theta_u_muas = theta_u * 3.6e9
            theta_v_muas = theta_v * 3.6e9

            ax = fig.add_subplot(111)
            im = ax.imshow(
                beam_2d,
                extent=[min(theta_u_muas), max(theta_u_muas), min(theta_v_muas), max(theta_v_muas)],
                cmap=self.redpurple_cmap,
                aspect="equal"
            )

            u_range = max(theta_u_muas) - min(theta_u_muas)
            v_range = max(theta_v_muas) - min(theta_v_muas)
            max_range = max(u_range, v_range) * 1.1
            u_center = (max(theta_u_muas) + min(theta_u_muas)) / 2
            v_center = (max(theta_v_muas) + min(theta_v_muas)) / 2
            ax.set_xlim(u_center - max_range / 2, u_center + max_range / 2)
            ax.set_ylim(v_center - max_range / 2, v_center + max_range / 2)

            fig.colorbar(im, label="Normalized Peak Flux (Jy)", ax=ax)
            ax.set_xlabel("Relative Right Ascension (μas)")
            ax.set_ylabel("Relative Declination (μas)")
            ax.set_title(f"Synthesized Beam at {obj.get_frequencies().get(freq_name).get('frequency')} MHz")
            return {"scans": len(data.scan)}

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
            if not data or not data.data_vars:
                logger.error(f"No baseline projections data found for '{store_key}' in {obj.get_observation_code()}")
                return {}

            if "baseline" not in data.coords or "time" not in data.coords:
                logger.error(f"Missing baseline or time coordinates in data for {store_key}")
                return {}

            ax = fig.add_subplot(111)
            plotted_pairs = set()
            valid_projections = 0

            for scan in data.scan.values:
                scan_data = data.sel(scan=scan)
                if "time" not in scan_data.coords or not scan_data.time.size:
                    logger.warning(f"No valid times for scan {scan}")
                    continue
                source = scan_data.source.values
                times_mjd = [Time(t).mjd for t in scan_data.time.values]
                for baseline in scan_data.baseline.values:
                    projections = scan_data.projections.sel(baseline=baseline).values
                    mask = ~np.isnan(projections)
                    if not mask.any():
                        logger.debug(f"No valid projections for baseline {baseline} in scan {scan}")
                        continue
                    if baseline not in plotted_pairs:
                        color_idx = len(plotted_pairs) % len(self.moderate2_colors)
                        ax.scatter(
                            np.array(times_mjd)[mask],
                            projections[mask],
                            label=f"{baseline} ({source})",
                            color=self.moderate2_colors[color_idx],
                            s=10,
                            alpha=0.7
                        )
                        plotted_pairs.add(baseline)
                        valid_projections += mask.sum()

            ax.set_xlabel("Time (MJD)")
            ax.set_ylabel("Baseline Length (meters)")
            ax.set_title(f"Baseline Projections for {obj.get_observation_code()}")
            ax.legend()
            ax.grid(True)
            return {"scans": len(data.scan), "baselines": len(plotted_pairs), "projections": valid_projections}

    def _plot_mollweide_tracks(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot Mollweide tracks for an Observation.

        Args:
            obj: Observation object containing the Mollweide tracks data.
            attributes: Dictionary with visualization parameters, including 'store_key'.
            fig: Matplotlib figure object for plotting.

        Returns:
            Dict containing metadata about the plotted data (e.g., number of scans).
        """
        with self._lock:
            logger.debug(f"Plotting Mollweide tracks for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "mollweide_tracks")
            data = obj.get_calculated_data_by_key(store_key)
            if not data or not data.data_vars:
                logger.error(f"No Mollweide tracks data found for '{store_key}' in {obj.get_observation_code()}")
                return {}

            if "telescope" not in data.coords or "source_lon" not in data.data_vars:
                logger.error(f"Missing required coordinates or variables in data for {store_key}")
                return {}

            ax = fig.add_subplot(111, projection="mollweide")
            plotted_telescopes = set()
            valid_points = 0

            for scan in data.scan.values:
                scan_data = data.sel(scan=scan)
                logger.debug(f"Processing scan {scan}: source_lon={scan_data.source_lon.values}, source_lat={scan_data.source_lat.values}")
                if "source_lon" not in scan_data.data_vars or "source_lat" not in scan_data.data_vars:
                    logger.warning(f"No source coordinates for scan {scan}")
                    continue
                source = scan_data.source.item() if isinstance(scan_data.source, xr.DataArray) else scan_data.source
                source_lon = scan_data.source_lon.values
                source_lat = scan_data.source_lat.values
                if np.isnan(source_lon) or np.isnan(source_lat):
                    logger.debug(f"Invalid source coordinates for scan {scan}: lon={source_lon}, lat={source_lat}")
                    continue
                ax.scatter(
                    source_lon,
                    source_lat,
                    c="red",
                    marker="o",
                    label=f"Source: {source}",
                    s=10,
                    zorder=2
                )
                for telescope in scan_data.telescope.values:
                    lon = scan_data.telescope_lon.sel(telescope=telescope).values
                    lat = scan_data.telescope_lat.sel(telescope=telescope).values
                    mask = ~np.isnan(lon) & ~np.isnan(lat)
                    if not mask.any():
                        logger.debug(f"No valid track data for telescope {telescope} in scan {scan}")
                        continue
                    if telescope not in plotted_telescopes:
                        color_idx = len(plotted_telescopes) % len(self.moderate2_colors)
                        ax.scatter(
                            lon[mask],
                            lat[mask],
                            c=[self.moderate2_colors[color_idx]],
                            label=telescope,
                            s=0.1,
                            zorder=1
                        )
                        plotted_telescopes.add(telescope)
                        valid_points += mask.sum()

            ax.set_title(f"Mollweide Tracks for {obj.get_observation_code()}")
            ax.grid(True)
            ax.legend(loc="upper right", bbox_to_anchor=(1.15, 1))
            logger.debug(f"Returning metadata: scans={len(data.scan)}, telescopes={len(plotted_telescopes)}, points={valid_points}")
            return {"scans": len(data.scan), "telescopes": len(plotted_telescopes), "points": valid_points}

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