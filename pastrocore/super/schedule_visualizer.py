# pastrocore/super/schedule_visualizer.py
from common.super.super import Super
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from pastrocore.base.telescopes import Telescope, SpaceTelescope, Telescopes
from pastrocore.base.sources import Source, Sources
from pastrocore.base.scans import Scan, Scans
from pastrocore.base.frequencies import IF, Frequencies
from common.utils.logging_setup import logger
from typing import Dict, Any, Callable, Union, List, Tuple
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

        # Default style configuration
        self._style_config = {
            'plt_style': 'seaborn-v0_8-whitegrid',
            'axes': {
                'facecolor': 'white',
                'edgecolor': 'black',
                'labelcolor': 'black',
            },
            'grid': {
                'color': 'lightgray',
                'linestyle': '--',
                'linewidth': 0.5
            },
            'xtick': {'color': 'black'},
            'ytick': {'color': 'black'},
            'font': {'family': 'Trebuchet MS', 'size': 12},
            'text': {'color': 'black'},
            'figure': {'facecolor': 'white'},
            'figsize': (10, 6),
            'dpi': 300,
            'legend': {'loc': 'center left', 'bbox_to_anchor': (1, 0.5), 'fontsize': 8},
            'colors': [
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
            ],
            'intersection_color': (255/255, 165/255, 0/255),
            'redpurple_cmap': LinearSegmentedColormap.from_list(
                "RedPurple",
                [(139/255, 0/255, 0/255), (255/255, 69/255, 0/255), (255/255, 255/255, 0/255),
                 (0/255, 255/255, 0/255), (0/255, 206/255, 209/255), (0/255, 0/255, 139/255)][::-1]
            )
        }

        # Apply global styles
        plt.style.use(self._style_config['plt_style'])
        plt.rc('axes', **self._style_config['axes'])
        plt.rc('grid', **self._style_config['grid'])
        plt.rc('xtick', **self._style_config['xtick'])
        plt.rc('ytick', **self._style_config['ytick'])
        plt.rc('font', **self._style_config['font'])
        plt.rc('text', **self._style_config['text'])
        plt.rc('figure', **self._style_config['figure'])

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

    def _setup_axes(self, fig: plt.Figure, plot_type: str, obj_name: str, projection: str = None, 
                    n_rows: int = 1, n_cols: int = 1, sharex: bool = False, sharey: bool = False) -> Union[plt.Axes, np.ndarray]:
        """Set up axes for plotting with consistent styling.

        Args:
            fig: Matplotlib figure object.
            plot_type: Type of plot being created.
            obj_name: Name of the object being visualized.
            projection: Matplotlib projection type (e.g., 'mollweide', '3d').
            n_rows: Number of subplot rows.
            n_cols: Number of subplot columns.
            sharex: Share x-axis across subplots.
            sharey: Share y-axis across subplots.

        Returns:
            Single Axes or array of Axes.
        """
        with self._lock:
            if projection:
                axes = fig.add_subplot(111, projection=projection)
            else:
                axes = fig.subplots(n_rows, n_cols, sharex=sharex, sharey=sharey)
                if n_rows * n_cols > 1:
                    axes = np.array(axes).flatten()
                else:
                    axes = np.array([axes])
            return axes

    def _finalize_plot(self, fig: plt.Figure, attributes: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize the plot by saving, displaying, or returning the figure.

        Args:
            fig: Matplotlib figure object.
            attributes: Visualization parameters (output_file, show, return_figure).
            result: Result dictionary to update.

        Returns:
            Updated result dictionary.
        """
        output_file = attributes.get("output_file")
        show = attributes.get("show", True)
        return_figure = attributes.get("return_figure", False)

        with self._lock:
            if output_file and output_file.strip():
                output_dir = os.path.dirname(output_file)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                fig.savefig(output_file, dpi=self._style_config['dpi'], bbox_inches='tight')
                logger.info(f"Visualization saved to '{output_file}'")

            if show:
                logger.debug("Displaying plot with plt.show()")
                plt.show()
                if not return_figure:
                    logger.debug("Closing figure after display")
                    plt.close(fig)
            else:
                plt.tight_layout()

            if return_figure:
                result["figure"] = fig
            elif not show:
                logger.debug("Closing figure")
                plt.close(fig)

        return result

    def _visualize(self, obj: Union[ScheduleProject, Observation, Telescope, SpaceTelescope, Telescopes, Source, Sources, Scan, Scans, IF, Frequencies], 
                   attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Visualize the specified object.

        Args:
            obj: The object to visualize.
            attributes: Dictionary containing visualization parameters, including 'plot_type', 'output_file', 'show', and 'return_figure'.

        Returns:
            Visualization result data or None if an error occurs.
        """
        plot_type = attributes.get("plot_type")
        if not plot_type:
            logger.error("No 'plot_type' specified in attributes")
            return None

        with self._lock:
            fig = plt.figure(figsize=attributes.get("figsize", self._style_config['figsize']))
        
        try:
            visualizer = None
            for types, func in self._object_visualizers.items():
                if isinstance(obj, types):
                    visualizer = func
                    break
            if not visualizer:
                logger.debug(f"Closing figure due to unsupported object type: {type(obj)}")
                plt.close(fig)
                raise ValueError(f"Unsupported object type: {type(obj)}")

            result = visualizer(obj, attributes, fig=fig)
            if result is None or not result:
                logger.debug("No data to plot, returning empty figure")
                plt.close(fig)
                return {}

            return self._finalize_plot(fig, attributes, result)

        except Exception as e:
            logger.error(f"Visualization failed: {str(e)}")
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

    def _filter_data(self, data: Dict, times_data: Dict, source_name: str, scans: List[str], time_range: Tuple[float, float]) -> Tuple[Dict, Dict, List[str]]:
        """Filter data and times based on source, scans, and time range.

        Args:
            data: Data dictionary to filter.
            times_data: Times data dictionary to filter.
            source_name: Source to filter by (or None for first source).
            scans: List of scans to include (or None for all).
            time_range: Tuple of (start_mjd, end_mjd) or None.

        Returns:
            Tuple of (filtered_data, filtered_times, scan_list).
        """
        if not isinstance(data, dict) or not isinstance(times_data, dict):
            logger.warning(f"Invalid data types: data={type(data)}, times_data={type(times_data)}")
            return {}, {}, []

        data = data.get("data", {})
        times_data = times_data.get("data", {})
        if not data or not times_data:
            logger.warning(f"Empty data: data={bool(data)}, times_data={bool(times_data)}")
            return {}, {}, []

        sources = [source_name] if source_name else list(data.keys())[:1]
        if not sources:
            logger.debug("No sources available")
            return {}, {}, []

        filtered_data = {}
        filtered_times = {}
        all_scans = set()
        for source in sources:
            if source not in data or source not in times_data:
                logger.warning(f"Source {source} not found in data")
                continue
            source_data = data[source]
            source_times = times_data[source]
            if not isinstance(source_data, dict) or not isinstance(source_times, dict):
                logger.warning(f"Invalid source data types: source_data={type(source_data)}, source_times={type(source_times)}")
                continue
            scan_list = scans if scans else list(source_data.keys())
            all_scans.update(scan_list)
            filtered_data[source] = {}
            filtered_times[source] = {}
            for scan in scan_list:
                if scan not in source_data or scan not in source_times:
                    continue
                filtered_data[source][scan] = source_data.get(scan, {})
                filtered_times[source][scan] = []
                for t in source_times.get(scan, []):
                    try:
                        if hasattr(t, 'mjd'):
                            if time_range and not (time_range[0] <= t.mjd <= time_range[1]):
                                continue
                            filtered_times[source][scan].append(t)
                    except (AttributeError, TypeError) as e:
                        logger.debug(f"Invalid time entry in scan {scan}, source {source}: {e}")
                        continue
                if not filtered_times[source][scan]:
                    filtered_data[source].pop(scan, None)
                    filtered_times[source].pop(scan, None)

        return filtered_data, filtered_times, list(all_scans)

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

            if not (source_name or baselines or scans or frequencies):
                logger.debug("No source, baselines, scans, or frequencies specified")
                return {}

            uv_data, times_data, scan_list = self._filter_data(
                obj.get_calculated_data_by_key(store_key),
                obj.get_calculated_data_by_key(times_key),
                source_name, scans, time_range
            )

            ax = self._setup_axes(fig, "uv_coverage", obj.get_observation_code())
            ax.set_xlabel(f"u, ({units})")
            ax.set_ylabel(f"v, ({units})")
            ax.set_title(f"Obs. code: {obj.code}\n(u,v) coverage")
            ax.invert_xaxis()

            if not uv_data or not times_data:
                return {"baselines": 0, "points": 0, "frequencies": 0}

            result = {"baselines": 0, "points": 0, "frequencies": len(frequencies) if frequencies else 0}
            plotted_pairs = set()
            EARTH_DIAMETER = 12742000.0
            SPEED_OF_LIGHT = 299792458.0

            for source in uv_data:
                source_uv = uv_data[source]
                source_times = times_data[source]

                all_times = []
                all_uv_points = {}
                for scan in scan_list:
                    if scan not in source_uv or scan not in source_times:
                        continue
                    times = [t.mjd for t in source_times[scan] if hasattr(t, 'mjd')]
                    if not times:
                        continue
                    all_times.extend(times)
                    uv_points = source_uv[scan]
                    for tel_code in uv_points:
                        if tel_code not in all_uv_points:
                            all_uv_points[tel_code] = []
                        all_uv_points[tel_code].extend([(pt[0], pt[1]) for pt in uv_points[tel_code] if len(pt) >= 2])

                if not all_times or not all_uv_points:
                    continue

                time_indices = np.argsort(all_times)
                all_times = [all_times[i] for i in time_indices]
                for tel_code in all_uv_points:
                    all_uv_points[tel_code] = [all_uv_points[tel_code][i] for i in time_indices if i < len(all_uv_points[tel_code])]

                for freq_mhz in (frequencies or [None]):
                    wavelength = SPEED_OF_LIGHT / (freq_mhz * 1e6) if freq_mhz else 1.0
                    scaling_factor = 1.0 if units == "wavelengths" else (wavelength / EARTH_DIAMETER)

                    for tel_code in all_uv_points:
                        if baselines and tel_code not in baselines:
                            continue
                        valid_points = [(pt[0], pt[1]) for pt in all_uv_points[tel_code] if len(pt) >= 2]
                        if not valid_points:
                            continue
                        u, v = zip(*valid_points)
                        u, v = np.array(u, dtype=float), np.array(v, dtype=float)
                        u_scaled = u / wavelength * scaling_factor if wavelength != 0 else u
                        v_scaled = v / wavelength * scaling_factor if wavelength != 0 else v
                        color_idx = (len(plotted_pairs) + (frequencies.index(freq_mhz) if frequencies and freq_mhz else 0)) % len(self._style_config['colors'])
                        label = f"{tel_code} ({freq_mhz} MHz)" if freq_mhz else f"{tel_code}"
                        ax.scatter(u_scaled, v_scaled, s=1, c=[self._style_config['colors'][color_idx]], label=label)
                        ax.scatter(-u_scaled, -v_scaled, s=1, c=[self._style_config['colors'][color_idx]])
                        plotted_pairs.add(f"{tel_code}_{freq_mhz}" if freq_mhz else tel_code)
                        result["points"] += len(u_scaled)

            result["baselines"] = len(plotted_pairs)
            if plotted_pairs:
                ax.legend(**self._style_config['legend'])
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
            ax = self._setup_axes(fig, "source_visibility", obj.get_observation_code())
            ax.set_xlabel("Time (MJD)")
            ax.set_ylabel("Visible (1 = Yes, 0 = No)")
            ax.set_title(f"Source Visibility for Observation: {obj.get_observation_code()}")

            all_data = {}
            result = {"scans": 0}
            plotted_telescopes = set()

            for scan_idx, scan_data in data.items():
                times = [Time(t).mjd for t in scan_data.get("times", []) if t]
                visibility = scan_data.get("visibility", {})
                source = scan_data.get("source")
                if not times:
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

            for tel_code, data in all_data.items():
                times_mjd = data["times"]
                vis_valid = data["visibility"]
                if times_mjd and vis_valid:
                    sorted_indices = np.argsort(times_mjd)
                    times_mjd = [times_mjd[i] for i in sorted_indices]
                    vis_valid = [vis_valid[i] for i in sorted_indices]
                    color_idx = len(plotted_telescopes) % len(self._style_config['colors'])
                    ax.plot(
                        times_mjd, vis_valid,
                        label=f"{tel_code}",
                        marker="o" if not attributes.get("time_step") else None,
                        color=self._style_config['colors'][color_idx]
                    )
                    plotted_telescopes.add(tel_code)

            if plotted_telescopes:
                ax.legend(**self._style_config['legend'])
            return result

    def _plot_sun_angles(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot angles to the Sun for an Observation with flexible filtering."""
        with self._lock:
            logger.debug(f"Plotting sun angles for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "sun_angles")
            times_key = attributes.get("times_key", "times")
            source_name = attributes.get("source_name", None)
            telescopes = attributes.get("telescopes", None)
            scans = attributes.get("scans", None)
            time_range = attributes.get("time_range", None)

            if not (source_name or telescopes or scans):
                logger.debug("No source, telescopes, or scans specified")
                return {}

            sun_angles_data, times_data, scan_list = self._filter_data(
                obj.get_calculated_data_by_key(store_key),
                obj.get_calculated_data_by_key(times_key),
                source_name, scans, time_range
            )

            ax = self._setup_axes(fig, "sun_angles", obj.get_observation_code())
            ax.set_xlabel("Time (MJD)")
            ax.set_ylabel("Angle to Sun (degrees)")
            ax.set_title(f"Sun Angles for Observation: {obj.get_observation_code()}")

            if not sun_angles_data or not times_data:
                return {"scans": 0, "telescopes": 0, "points": 0}

            result = {"scans": len(scan_list), "telescopes": 0, "points": 0}
            plotted_telescopes = set()

            for source in sun_angles_data:
                source_angles = sun_angles_data[source]
                source_times = times_data[source]

                all_times = []
                all_angles = {}
                for scan in scan_list:
                    if scan not in source_angles or scan not in source_times:
                        continue
                    times = [t for t in source_times[scan] if hasattr(t, 'mjd')]
                    if not times:
                        continue
                    all_times.extend(times)
                    angles = source_angles[scan]
                    for tel_code in angles:
                        if tel_code not in all_angles:
                            all_angles[tel_code] = []
                        all_angles[tel_code].extend(angles[tel_code])

                if not all_times:
                    continue
                time_indices = np.argsort(all_times)
                all_times = [all_times[i] for i in time_indices]
                for tel_code in all_angles:
                    all_angles[tel_code] = [all_angles[tel_code][i] for i in time_indices]

                tel_list = telescopes if telescopes else list(all_angles.keys())
                for tel_code in tel_list:
                    if tel_code not in all_angles:
                        continue
                    valid_pairs = [(t.mjd, float(a)) for t, a in zip(all_times, all_angles[tel_code]) if a is not None]
                    if valid_pairs:
                        times_mjd, angles_sorted = zip(*sorted(valid_pairs))
                        color_idx = len(plotted_telescopes) % len(self._style_config['colors'])
                        ax.plot(times_mjd, angles_sorted, label=f"{tel_code} ({source})",
                                color=self._style_config['colors'][color_idx])
                        plotted_telescopes.add(tel_code)
                        result["points"] += len(valid_pairs)

            result["telescopes"] = len(plotted_telescopes)
            if plotted_telescopes:
                ax.legend(**self._style_config['legend'])
            return result

    def _plot_az_el(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot Azimuth/Elevation or Hour Angle/Declination for an Observation with one subplot per telescope."""
        with self._lock:
            logger.debug(f"Plotting Az/El or HA/Dec for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "az_el")
            times_key = attributes.get("times_key", "times")
            source_name = attributes.get("source_name", None)
            telescopes = attributes.get("telescopes", None)
            scans = attributes.get("scans", None)
            time_range = attributes.get("time_range", None)
            coord_type = attributes.get("coord_type", "AzEl")

            valid_coord_types = ["AzEl", "HADec"]
            if coord_type not in valid_coord_types:
                logger.warning(f"Invalid coord_type '{coord_type}', defaulting to 'AzEl'")
                coord_type = "AzEl"

            if not (source_name or telescopes or scans):
                logger.debug("No source, telescopes, or scans specified")
                return {}

            az_el_data, times_data, scan_list = self._filter_data(
                obj.get_calculated_data_by_key(store_key),
                obj.get_calculated_data_by_key(times_key),
                source_name, scans, time_range
            )

            if not az_el_data or not times_data:
                return {"scans": 0, "telescopes": 0, "points": 0}

            all_telescopes = set()
            for source in az_el_data:
                for scan in az_el_data[source]:
                    all_telescopes.update(az_el_data[source][scan].keys())
            tel_list = sorted(telescopes if telescopes else list(all_telescopes))
            if not tel_list:
                return {"scans": len(scan_list), "telescopes": 0, "points": 0}

            n_tels = len(tel_list)
            n_cols = int(np.ceil(np.sqrt(n_tels)))
            n_rows = int(np.ceil(n_tels / n_cols))
            axes = self._setup_axes(fig, "az_el", obj.get_observation_code(), n_rows=n_rows, n_cols=n_cols, sharex=True, sharey=True)

            result = {"scans": len(scan_list), "telescopes": n_tels, "points": 0}
            plotted_telescopes = set()

            for source in az_el_data:
                source_coords = az_el_data[source]
                source_times = times_data[source]

                all_times = []
                all_coords = {}
                for scan in scan_list:
                    if scan not in source_coords or scan not in source_times:
                        continue
                    times = [t for t in source_times[scan] if hasattr(t, 'mjd')]
                    if not times:
                        continue
                    all_times.extend(times)
                    coords = source_coords[scan]
                    for tel in coords:
                        if tel not in all_coords:
                            all_coords[tel] = []
                        all_coords[tel].extend(coords[tel])

                if not all_times:
                    continue
                time_indices = np.argsort(all_times)
                all_times = [all_times[i] for i in time_indices]
                for tel in all_coords:
                    all_coords[tel] = [all_coords[tel][i] for i in time_indices]

                for tel_idx, tel_code in enumerate(tel_list):
                    if tel_code not in all_coords:
                        continue
                    coord_pairs = all_coords[tel_code]
                    valid_pairs = [(t.mjd, float(c[0]), float(c[1])) for t, c in zip(all_times, coord_pairs)
                                  if c[0] is not None and c[1] is not None]
                    if valid_pairs:
                        times_mjd, az, el = zip(*sorted(valid_pairs))
                        color_idx = tel_idx % len(self._style_config['colors'])
                        ax = axes[tel_idx] if tel_idx < len(axes) else axes[-1]
                        ax.plot(times_mjd, az, label=f"{source}, {coord_type[:2]}",
                                color=self._style_config['colors'][color_idx])
                        ax.plot(times_mjd, el, label=f"{source}, {coord_type[2:]}",
                                linestyle='--', color=self._style_config['colors'][color_idx])
                        ax.set_title(f"{tel_code}")
                        ax.set_xlabel("Time (MJD)")
                        ax.set_ylabel(f"Angle ({coord_type[:2]}/{coord_type[2:]}, deg)")
                        ax.legend(**self._style_config['legend'])
                        plotted_telescopes.add(tel_code)
                        result["points"] += len(valid_pairs)

            for idx in range(len(tel_list), len(axes)):
                axes[idx].set_visible(False)

            fig.suptitle(f"{coord_type} for Observation: {obj.get_observation_code()}", fontsize=14)
            plt.tight_layout(rect=[0, 0, 1, 0.95])
            return result

    def _plot_time_on_source(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot time on source for an Observation with flexible filtering."""
        with self._lock:
            logger.debug(f"Plotting time on source for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "time_on_source")
            source_name = attributes.get("source_name", None)
            telescopes = attributes.get("telescopes", None)
            scans = attributes.get("scans", None)
            time_range = attributes.get("time_range", None)

            if not (source_name or telescopes or scans):
                logger.debug("No source, telescopes, or scans specified")
                return {}

            data = obj.get_calculated_data_by_key(store_key)
            if not data:
                logger.error(f"No time on source data found for '{store_key}' in {obj.get_observation_code()}")
                return {}

            data = data.get("data", {})
            if not data:
                return {"scans": 0, "telescopes": 0, "points": 0, "intersections": 0}

            sources = [source_name] if source_name else list(data.keys())[:1]
            if not sources:
                return {"scans": 0, "telescopes": 0, "points": 0, "intersections": 0}

            ax = self._setup_axes(fig, "time_on_source", obj.get_observation_code())
            ax.set_xlabel("Time (MJD)")
            ax.set_ylabel("Telescope")
            ax.set_title(f"Time on Source for Observation: {obj.get_observation_code()}")

            result = {"scans": 0, "telescopes": 0, "points": 0, "intersections": 0}
            all_blocks = {}
            for source in sources:
                if source not in data:
                    continue
                source_data = data[source]
                scan_list = scans if scans else list(source_data.keys())
                result["scans"] += len(scan_list)

                for scan in scan_list:
                    if scan not in source_data:
                        continue
                    scan_data = source_data[scan]
                    tel_list = telescopes if telescopes else list(scan_data.keys())
                    for tel_code in tel_list:
                        if tel_code not in scan_data:
                            continue
                        blocks = scan_data[tel_code]
                        if isinstance(blocks, np.ndarray):
                            blocks = blocks.tolist()
                        if not blocks:
                            continue
                        if tel_code not in all_blocks:
                            all_blocks[tel_code] = []
                        for block in blocks:
                            try:
                                start_mjd = float(block[0]) if isinstance(block[0], (int, float)) else Time(block[0]).mjd
                                end_mjd = float(block[1]) if isinstance(block[1], (int, float)) else Time(block[1]).mjd
                                duration = float(block[2])
                                if time_range and (start_mjd >= time_range[1] or end_mjd <= time_range[0]):
                                    continue
                                all_blocks[tel_code].append((start_mjd, end_mjd, duration))
                            except (ValueError, TypeError) as e:
                                logger.error(f"Invalid block format for {tel_code} in scan {scan}: {str(e)}")
                                continue

            tel_list = sorted(all_blocks.keys())
            result["telescopes"] = len(tel_list)
            if not tel_list:
                return {"scans": result["scans"], "telescopes": 0, "points": 0, "intersections": 0}

            for i, tel in enumerate(tel_list):
                color_idx = i % len(self._style_config['colors'])
                for start_mjd, end_mjd, _ in all_blocks[tel]:
                    ax.fill_between(
                        [start_mjd, end_mjd],
                        [i, i],
                        [i + 1, i + 1],
                        color=self._style_config['colors'][color_idx],
                        alpha=0.5,
                        label=tel if tel not in set(ax.get_legend_handles_labels()[1]) else None
                    )
                    result["points"] += 1

            if tel_list and all_blocks:
                all_times = [[(start, end) for start, end, _ in all_blocks[tel]] for tel in tel_list]
                if all_times and all(all_times):
                    time_points = sorted(set(t for tel_times in all_times for start, end in tel_times for t in (start, end)))
                    intersection_times = []
                    for i in range(len(time_points) - 1):
                        start, end = time_points[i], time_points[i + 1]
                        all_active = all(any(start_t <= start and end <= end_t for start_t, end_t in tel_times) for tel_times in all_times)
                        if all_active:
                            intersection_times.append((start, end))

                    for i, (start, end) in enumerate(intersection_times):
                        duration = (end - start) * 86400
                        ax.fill_between(
                            [start, end],
                            [-1, -1],
                            [0, 0],
                            color=self._style_config['intersection_color'],
                            alpha=0.9,
                            label="Total Intersection" if i == 0 else None
                        )
                        ax.text(
                            (start + end) / 2, -0.5, f"{duration:.1f}s",
                            ha='center', va='center', fontsize=8, color='black',
                            bbox=dict(facecolor='white', alpha=0.8, edgecolor='none')
                        )
                    result["intersections"] = len(intersection_times)

            ax.set_yticks(np.arange(-1, len(tel_list)))
            ax.set_yticklabels(["Total Intersection"] + tel_list)
            if ax.get_legend_handles_labels()[0]:
                ax.legend(**self._style_config['legend'])
            return result

    def _plot_beam_pattern(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot beam patterns for an Observation with one subplot per telescope."""
        with self._lock:
            logger.debug(f"Plotting beam pattern for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "beam_pattern")
            freq_names = attributes.get("freq_names", None)
            telescopes = attributes.get("telescopes", None)
            SPEED_OF_LIGHT = 299792458.0

            if not (telescopes or freq_names):
                logger.debug("No telescopes or frequencies specified")
                return {}

            beam_data = obj.get_calculated_data_by_key(store_key)
            beam_data = beam_data.get("data", {}) if isinstance(beam_data, dict) else {}
            if not beam_data:
                return {"telescopes": 0, "frequencies": 0}

            tel_list = sorted(telescopes if telescopes else list(beam_data.keys()))
            if not tel_list:
                return {"telescopes": 0, "frequencies": 0}

            freq_list = (
                [float(f) for f in (freq_names if isinstance(freq_names, list) else [freq_names]) if f]
                if freq_names else [float(f.get("frequency")) for f in obj.get_frequencies().get_items()]
            )
            if not freq_list:
                return {"telescopes": len(tel_list), "frequencies": 0}

            n_tels = len(tel_list)
            n_cols = int(np.ceil(np.sqrt(n_tels)))
            n_rows = int(np.ceil(n_tels / n_cols))
            axes = self._setup_axes(fig, "beam_pattern", obj.get_observation_code(), n_rows=n_rows, n_cols=n_cols, sharex=True, sharey=True)

            result = {"telescopes": 0, "frequencies": len(freq_list)}
            plotted_telescopes = set()
            plotted_frequencies = set()

            for tel_idx, tel_code in enumerate(tel_list):
                if tel_code not in beam_data:
                    continue
                ax = axes[tel_idx] if tel_idx < len(axes) else axes[-1]
                ax.annotate(tel_code, xy=(0.05, 0.95), xycoords='axes fraction', fontsize=10,
                            bbox=dict(boxstyle="round", facecolor='white', alpha=0.8))

                beam = beam_data.get(tel_code, {})
                theta = np.array(beam.get("theta", []))
                pattern = np.array(beam.get("pattern", []))
                if len(theta) == 0 or len(pattern) == 0:
                    continue

                for freq_idx, freq_mhz in enumerate(freq_list):
                    wavelength = SPEED_OF_LIGHT / (freq_mhz * 1e6)
                    scaling_factor = 1.0 / wavelength**2
                    scaled_pattern = pattern * scaling_factor
                    color_idx = freq_idx % len(self._style_config['colors'])
                    ax.plot(theta, scaled_pattern, label=f"{freq_mhz:.2f} MHz",
                            color=self._style_config['colors'][color_idx])
                    theta_range = np.max(np.abs(theta)) * 1.1 if len(theta) > 0 else 1.0
                    ax.set_xlim(-theta_range, theta_range)
                    ax.legend(**self._style_config['legend'])
                    plotted_frequencies.add(freq_mhz)

                plotted_telescopes.add(tel_code)

            for idx in range(len(tel_list), len(axes)):
                axes[idx].set_visible(False)

            fig.text(0.5, 0.04, "Theta (radians)", ha='center', fontsize=12)
            fig.text(0.04, 0.5, "Normalized Peak Flux (Jy)", va='center', rotation='vertical', fontsize=12)
            fig.suptitle(f"Beam Pattern for Observation: {obj.get_observation_code()}", fontsize=14)
            plt.tight_layout(rect=[0.05, 0.05, 1, 0.95])
            result["telescopes"] = len(plotted_telescopes)
            result["frequencies"] = len(plotted_frequencies)
            return result

    def _plot_synthesized_beam(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot the synthesized beam for an Observation."""
        with self._lock:
            logger.debug(f"Plotting synthesized beam for {obj.get_observation_code()}")
            freq_name = attributes.get("freq_name")
            store_key = attributes.get("store_key", f"synthesized_beam_{freq_name}")
            data = obj.get_calculated_data_by_key(store_key)
            data = data.get("data", {}) if isinstance(data, dict) else {}
            if not data:
                return {}

            scan_data = data.get(0, {})
            theta_u = np.array(scan_data.get("theta_u", []))
            theta_v = np.array(scan_data.get("theta_v", []))
            beam_2d = scan_data.get("beam_2d", np.zeros((len(theta_v), len(theta_u))))
            if len(theta_u) == 0 or len(theta_v) == 0:
                return {}

            ax = self._setup_axes(fig, "synthesized_beam", obj.get_observation_code())
            theta_u_muas = theta_u * 3.6e9
            theta_v_muas = theta_v * 3.6e9
            im = ax.imshow(beam_2d, extent=[min(theta_u_muas), max(theta_u_muas), min(theta_v_muas), max(theta_v_muas)], 
                           cmap=self._style_config['redpurple_cmap'], aspect='equal')

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
        """Plot baseline projections for an Observation with flexible filtering and frequency scaling."""
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

            if not (source_name or baselines or scans or frequencies):
                logger.debug("No source, baselines, scans, or frequencies specified")
                return {}

            bl_data, times_data, scan_list = self._filter_data(
                obj.get_calculated_data_by_key(store_key),
                obj.get_calculated_data_by_key(times_key),
                source_name, scans, time_range
            )

            ax = self._setup_axes(fig, "baseline_projections", obj.get_observation_code())
            ax.set_xlabel("Time (MJD)")
            ax.set_ylabel(f"Baseline Length ({units})")
            ax.set_title(f"Baseline Projections for Observation: {obj.get_observation_code()}")

            if not bl_data or not times_data:
                return {"scans": 0, "baselines": 0, "projections": 0, "frequencies": 0}

            result = {"scans": len(scan_list), "baselines": 0, "projections": 0, "frequencies": len(frequencies) if frequencies else 0}
            plotted_pairs = set()
            SPEED_OF_LIGHT = 299792458.0
            EARTH_DIAMETER = 12742000.0

            for source in bl_data:
                source_bl = bl_data[source]
                source_times = times_data[source]

                all_times = []
                all_bl_points = {}
                for scan in scan_list:
                    if scan not in source_bl or scan not in source_times:
                        continue
                    times = [t.mjd for t in source_times[scan] if hasattr(t, 'mjd')]
                    if not times:
                        continue
                    all_times.extend(times)
                    bl_points = source_bl[scan]
                    for pair in bl_points:
                        if pair not in all_bl_points:
                            all_bl_points[pair] = []
                        all_bl_points[pair].extend([float(p) for p in bl_points[pair] if p is not None])

                if not all_times or not all_bl_points:
                    continue

                time_indices = np.argsort(all_times)
                all_times = [all_times[i] for i in time_indices]
                for pair in all_bl_points:
                    all_bl_points[pair] = [all_bl_points[pair][i] for i in time_indices if i < len(all_bl_points[pair])]

                for freq_mhz in (frequencies or [None]):
                    wavelength = SPEED_OF_LIGHT / (freq_mhz * 1e6) if freq_mhz else 1.0
                    scaling_factor = 1.0 if units == "meters" else (wavelength / EARTH_DIAMETER)
                    for pair in all_bl_points:
                        if baselines and pair not in baselines:
                            continue
                        valid_projs = np.array(all_bl_points[pair], dtype=float)
                        valid_projs = valid_projs[~np.isnan(valid_projs)]
                        if len(valid_projs) == 0:
                            continue
                        if len(valid_projs) != len(all_times):
                            min_len = min(len(all_times), len(valid_projs))
                            valid_projs = valid_projs[:min_len]
                            times_subset = all_times[:min_len]
                        else:
                            times_subset = all_times
                        bl_scaled = valid_projs / wavelength * scaling_factor if freq_mhz else valid_projs
                        color_idx = (len(plotted_pairs) + (frequencies.index(freq_mhz) if frequencies and freq_mhz else 0)) % len(self._style_config['colors'])
                        label = f"{pair} ({freq_mhz} MHz)" if freq_mhz else f"{pair}"
                        ax.scatter(times_subset, bl_scaled, s=10, c=[self._style_config['colors'][color_idx]], label=label, alpha=0.7)
                        plotted_pairs.add(f"{pair}_{freq_mhz}" if freq_mhz else pair)
                        result["projections"] += len(bl_scaled)

            result["baselines"] = len(plotted_pairs)
            if plotted_pairs:
                ax.legend(**self._style_config['legend'])
            return result

    def _plot_mollweide_tracks(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot Mollweide tracks for an Observation with flexible filtering."""
        with self._lock:
            logger.debug(f"Plotting Mollweide tracks for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "mollweide_tracks")
            telescopes = attributes.get("telescopes", None)
            scans = attributes.get("scans", None)
            time_range = attributes.get("time_range", None)

            if not (telescopes or scans):
                logger.debug("No telescopes or scans specified")
                return {}

            data = obj.get_calculated_data_by_key(store_key)
            data = data.get("data", {}) if isinstance(data, dict) else {}
            if not data:
                return {"scans": 0, "telescopes": 0, "sources": 0, "points": 0}

            metadata = data.get("metadata", {})
            ax = self._setup_axes(fig, "mollweide_tracks", obj.get_observation_code(), projection="mollweide")
            ax.set_title(f"Mollweide Tracks for Observation: {obj.get_observation_code()}")

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

            scan_list = scans if scans else list(data.keys())
            result["scans"] = len(scan_list)
            all_tracks = {}
            for scan_name in scan_list:
                if scan_name not in data:
                    continue
                scan_data = data[scan_name]
                tel_list = telescopes if telescopes else list(scan_data.keys())
                for tel_code in tel_list:
                    if tel_code not in scan_data:
                        continue
                    tracks = scan_data[tel_code]
                    if not isinstance(tracks, np.ndarray) or len(tracks) == 0 or tracks.ndim != 2 or tracks.shape[1] != 2:
                        continue
                    if tel_code not in all_tracks:
                        all_tracks[tel_code] = []
                    all_tracks[tel_code].append(tracks)

            for tel_code in all_tracks:
                tracks = np.vstack(all_tracks[tel_code]) if all_tracks[tel_code] else np.array([])
                if len(tracks) == 0:
                    continue
                lon, lat = tracks[:, 0], tracks[:, 1]
                valid_mask = (~np.isnan(lon)) & (~np.isnan(lat))
                lon = lon[valid_mask]
                lat = lat[valid_mask]
                if len(lon) == 0:
                    continue
                lon_rad = np.radians(lon)
                lat_rad = np.radians(lat)
                color_idx = len(plotted_telescopes) % len(self._style_config['colors'])
                ax.scatter(lon_rad, lat_rad, s=1, c=[self._style_config['colors'][color_idx]],
                          label=f"{tel_code}" if tel_code not in plotted_telescopes else None,
                          zorder=1)
                plotted_telescopes.add(tel_code)
                result["points"] += len(lon)

            result["telescopes"] = len(plotted_telescopes)
            if plotted_telescopes or plotted_sources:
                ax.legend(**self._style_config['legend'])
            return result

    def _visualize_telescopes(self, obj: Union[Telescope, SpaceTelescope, Telescopes], attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Visualize Telescope-related objects."""
        with self._lock:
            logger.debug(f"Visualizing telescopes for {type(obj).__name__}")
            plot_type = attributes.get("plot_type")
            if plot_type != "positions":
                logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
                return {}

            tels = obj.get_active_telescopes() if isinstance(obj, Telescopes) else [obj]
            if not tels:
                return {"telescopes": 0}

            ax = self._setup_axes(fig, "telescopes", "Telescope Positions", projection="3d")
            ax.set_xlabel("X, (m)")
            ax.set_ylabel("Y, (m)")
            ax.set_zlabel("Z, (m)")
            ax.set_title("Telescope Positions")

            for i, tel in enumerate(tels):
                x, y, z = tel.get_coordinates()
                ax.scatter(x, y, z, c=[self._style_config['colors'][i % len(self._style_config['colors'])]], label=tel.get_code())
            
            if tels:
                ax.legend(**self._style_config['legend'])
            return {"telescopes": len(tels)}

    def _visualize_sources(self, obj: Union[Source, Sources], attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Visualize Source-related objects."""
        with self._lock:
            logger.debug(f"Visualizing sources for {type(obj).__name__}")
            plot_type = attributes.get("plot_type")
            if plot_type != "sky_position":
                logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
                return {}

            sources = obj.get_items() if isinstance(obj, Sources) else [obj]
            if not sources:
                return {"sources": 0}

            ax = self._setup_axes(fig, "sources", "Source(s) Sky Position")
            ax.set_xlabel("Relative Right Ascension, (deg)")
            ax.set_ylabel("Relative Declination, (deg)")
            ax.set_title("Source(s) Sky Position")

            for i, source in enumerate(sources):
                ax.scatter(source.get_ra_degrees(), source.get_dec_degrees(),
                          c=[self._style_config['colors'][i % len(self._style_config['colors'])]], label=f"Source {i}")

            if sources:
                ax.legend(**self._style_config['legend'])
            return {"sources": len(sources)}

    def _visualize_scans(self, obj: Union[Scan, Scans], attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Visualize Scan-related objects."""
        with self._lock:
            logger.debug(f"Visualizing scans for {type(obj).__name__}")
            plot_type = attributes.get("plot_type")
            if plot_type != "timeline":
                logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
                return {}

            scans = obj.get_items() if isinstance(obj, Scans) else [obj]
            if not scans:
                return {"scans": 0}

            ax = self._setup_axes(fig, "scans", "Scan Timeline")
            ax.set_xlabel("Time, (MJD)")
            ax.set_ylabel("Scan Index")
            ax.set_title("Scan Timeline")

            for i, scan in enumerate(scans):
                start = Time(scan.get_start()).mjd
                end = (Time(scan.get_start()) + scan.get_duration() * u.s).mjd
                ax.plot([start, end], [i, i], label=f"Scan {i}",
                        color=self._style_config['colors'][i % len(self._style_config['colors'])])

            if scans:
                ax.legend(**self._style_config['legend'])
            return {"scans": len(scans)}

    def _visualize_frequencies(self, obj: Union[IF, Frequencies], attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Visualize Frequency-related objects."""
        with self._lock:
            logger.debug(f"Visualizing frequencies for {type(obj).__name__}")
            plot_type = attributes.get("plot_type")
            if plot_type != "spectrum":
                logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
                return {}

            freqs = obj.get_items() if isinstance(obj, Frequencies) else [obj]
            if not freqs:
                return {"frequencies": 0}

            ax = self._setup_axes(fig, "frequencies", "Frequency Spectrum")
            ax.set_xlabel("Frequency, (MHz)")
            ax.set_ylabel("Bandwidth, (MHz)")
            ax.set_title("Frequency Spectrum")

            for i, freq in enumerate(freqs):
                ax.bar(freq.get_frequency(), freq.get_bandwidth(), width=0.1, align='center',
                       color=self._style_config['colors'][i % len(self._style_config['colors'])])

            return {"frequencies": len(freqs)}