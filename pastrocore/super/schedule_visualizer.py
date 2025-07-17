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
import warnings
from erfa import ErfaWarning

from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D

warnings.filterwarnings("ignore", category=ErfaWarning)

class ScheduleVisualizer(Super):
    """Scheduler implementation of Visualizer for visualizing ScheduleProject and its components."""
    
    def __init__(self, manipulator: 'Manipulator'):
        super().__init__(manipulator)
        logger.info("Initialized Scheduling Visualizer")
        self._lock = threading.Lock()

        # Default style configuration
        self._style_config = {
            'plt_style': 'seaborn-v0_8-whitegrid',
            'axes': {
                'facecolor': 'white',
                'edgecolor': 'black',
                'labelcolor': 'black',
                'grid': True  # Explicitly enable grid
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
            "baseline_projections": self._plot_baseline_projections,
            "mollweide_tracks": self._plot_mollweide_tracks,
        }

    def execute(self, obj: Union[ScheduleProject, Observation, Telescope, SpaceTelescope, Telescopes, Source, Sources, Scan, Scans, IF, Frequencies], 
                attributes: Dict[str, Any] = None, method: str = None) -> Dict[str, Any]:
        """Execute visualization operation on the specified object."""
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
        
    def _create_empty_plot(self, fig: plt.Figure, plot_type: str, obj_name: str, 
                      projection: str = None, labels: Dict[str, str] = None) -> Dict[str, Any]:
        """Create an empty plot with consistent styling and labels.

        Args:
            fig: Matplotlib figure to plot on.
            plot_type: Type of the plot (e.g., 'uv_coverage', 'sun_angles').
            obj_name: Name of the object being visualized (e.g., observation code).
            projection: Optional projection type (e.g., 'mollweide').
            labels: Dictionary with 'xlabel', 'ylabel', 'title' for axis labels and title.

        Returns:
            Dictionary with default result values.
        """
        ax = self._setup_axes(fig, plot_type, obj_name, projection=projection)
        if labels:
            ax.set_xlabel(labels.get('xlabel', ''))
            ax.set_ylabel(labels.get('ylabel', ''))
            ax.set_title(labels.get('title', f"{plot_type.replace('_', ' ').title()} for {obj_name}"))
        logger.debug(f"Created empty plot for {plot_type} with obj_name={obj_name}")
        return {}
    
    def _check_filters(self, attributes: Dict[str, Any], required_filters: List[str]) -> bool:
        """Check if any of the required filters are provided.

        Args:
            attributes: Dictionary of visualization attributes.
            required_filters: List of filter keys to check (e.g., ['source_name', 'telescopes']).

        Returns:
            True if at least one filter is provided, False otherwise.
        """
        return any(attributes.get(key) for key in required_filters)
    
    def _plot_time_series(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure, 
                      plot_type: str, data_key: str, times_key: str, y_label: str,
                      value_extractors: List[Callable], labels: List[str]) -> Dict[str, Any]:
        """Generic method to plot time series data with flexible filtering and multi-value plotting.

        Args:
            obj: Observation object.
            attributes: Visualization attributes (source_name, telescopes, scans, time_range).
            fig: Matplotlib figure.
            plot_type: Type of plot (e.g., 'sun_angles', 'az_el').
            data_key: Key for calculated data.
            times_key: Key for time data.
            y_label: Label for y-axis.
            value_extractors: List of functions to extract values from data (e.g., [lambda x: x, lambda x: x[0], lambda x: x[1]]).
            labels: List of labels for each value series.

        Returns:
            Dictionary with counts of scans, telescopes, and points.
        """
        with self._lock:
            logger.debug(f"Plotting {plot_type} for {obj.get_observation_code()}")
            source_name = attributes.get("source_name", None)
            telescopes = attributes.get("telescopes", None)
            scans = attributes.get("scans", None)
            time_range = attributes.get("time_range", None)

            if not self._check_filters(attributes, ["source_name", "telescopes", "scans"]):
                logger.debug(f"No filters specified for {plot_type}, returning empty plot")
                return self._create_empty_plot(
                    fig, plot_type, obj.get_observation_code(),
                    labels={"xlabel": "Time (MJD)", "ylabel": y_label, 
                            "title": f"{plot_type.replace('_', ' ').title()} for Observation: {obj.get_observation_code()}"}
                )

            data, times_data, scan_list = self._filter_data(
                obj.get_calculated_data_by_key(data_key),
                obj.get_calculated_data_by_key(times_key),
                source_name, scans, time_range
            )

            if not data or not times_data:
                logger.debug(f"No data available for {plot_type}, returning empty plot")
                return self._create_empty_plot(
                    fig, plot_type, obj.get_observation_code(),
                    labels={"xlabel": "Time (MJD)", "ylabel": y_label, 
                            "title": f"{plot_type.replace('_', ' ').title()} for Observation: {obj.get_observation_code()}"}
                )

            n_tels = len(telescopes if telescopes else set(tel for src in data for scan in data[src] for tel in data[src][scan]))
            n_cols = int(np.ceil(np.sqrt(n_tels)))
            n_rows = int(np.ceil(n_tels / n_cols)) if plot_type == "az_el" else 1
            axes = self._setup_axes(fig, plot_type, obj.get_observation_code(), n_rows=n_rows, n_cols=n_cols, sharex=True, sharey=True)

            result = {"scans": len(scan_list), "telescopes": 0, "points": 0}
            plotted_telescopes = set()

            for source in data:
                source_data = data[source]
                source_times = times_data[source]
                all_times = []
                all_values = {tel: [[] for _ in value_extractors] for tel in (telescopes or [])}

                for scan in scan_list:
                    if scan not in source_data or scan not in source_times:
                        continue
                    times = [t for t in source_times[scan] if hasattr(t, 'mjd')]
                    if not times:
                        continue
                    all_times.extend(times)
                    for tel in source_data[scan]:
                        if tel not in all_values:
                            all_values[tel] = [[] for _ in value_extractors]
                        for i, extractor in enumerate(value_extractors):
                            all_values[tel][i].extend([extractor(v) for v in source_data[scan][tel] if v is not None])

                if not all_times:
                    continue
                time_indices = np.argsort(all_times)
                all_times = [all_times[i].mjd for i in time_indices]

                tel_list = telescopes if telescopes else list(all_values.keys())
                for tel_idx, tel in enumerate(tel_list):
                    if tel not in all_values:
                        continue
                    ax = axes[tel_idx] if plot_type == "az_el" and tel_idx < len(axes) else axes
                    for i, values in enumerate(all_values[tel]):
                        valid_pairs = [(t, float(v)) for t, v in zip(all_times, values) if v is not None]
                        if not valid_pairs:
                            continue
                        times_mjd, values_sorted = zip(*sorted(valid_pairs))
                        color_idx = (tel_idx * len(value_extractors) + i) % len(self._style_config['colors'])
                        linestyle = '--' if i > 0 and plot_type == "az_el" else '-'
                        ax.plot(times_mjd, values_sorted, label=f"{tel} ({source}, {labels[i]})",
                                color=self._style_config['colors'][color_idx], linestyle=linestyle)
                        result["points"] += len(valid_pairs)
                    if plot_type == "az_el":
                        ax.set_title(f"{tel}")
                    ax.set_xlabel("Time (MJD)")
                    ax.set_ylabel(y_label)
                    plotted_telescopes.add(tel)

            result["telescopes"] = len(plotted_telescopes)
            if plotted_telescopes:
                if plot_type == "az_el":
                    fig.suptitle(f"{labels[0][:2]}/{labels[0][2:]} for Observation: {obj.get_observation_code()}", fontsize=14)
                    plt.tight_layout(rect=[0, 0, 1, 0.95])
                else:
                    ax.set_title(f"{plot_type.replace('_', ' ').title()} for Observation: {obj.get_observation_code()}")
                for ax in np.atleast_1d(axes):
                    if ax.get_legend_handles_labels()[0]:
                        ax.legend(**self._style_config['legend'])
            return result

    def _setup_axes(self, fig: plt.Figure, plot_type: str, obj_name: str, projection: str = None, 
                n_rows: int = 1, n_cols: int = 1, sharex: bool = False, sharey: bool = False) -> Union[plt.Axes, np.ndarray]:
        """Set up axes for plotting with consistent styling.

        Returns a single plt.Axes for single-axis plots (n_rows=1, n_cols=1, no projection) or
        an np.ndarray of axes for multi-axis plots or when explicitly needed.
        """
        if projection:
            axes = fig.add_subplot(111, projection=projection)
        else:
            axes = fig.subplots(n_rows, n_cols, sharex=sharex, sharey=sharey)
            if n_rows * n_cols > 1:
                axes = np.array(axes).flatten()
            else:
                # Return single Axes object for single-axis plots to avoid wrapping in np.array
                axes = axes if n_rows == 1 and n_cols == 1 else np.array([axes])
        return axes

    def _finalize_plot(self, fig: plt.Figure, attributes: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize the plot by saving, displaying, or returning the figure."""
        output_file = attributes.get("output_file")
        show = attributes.get("show", False)  # Default to False for GUI
        return_figure = attributes.get("return_figure", False)

        if output_file and output_file.strip():
            output_dir = os.path.dirname(output_file)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            fig.savefig(output_file, dpi=self._style_config['dpi'], bbox_inches='tight')
            logger.info(f"Visualization saved to '{output_file}'")

        if show:
            logger.debug("Displaying plot with plt.show()")
            plt.show()
        elif not return_figure:
            logger.debug("Closing figure")
            plt.close(fig)

        if return_figure:
            result["figure"] = fig

        return result

    def _visualize(self, obj: Union[ScheduleProject, Observation, Telescope, SpaceTelescope, Telescopes, Source, Sources, Scan, Scans, IF, Frequencies], 
                   attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Visualize the specified object."""
        plot_type = attributes.get("plot_type")
        if not plot_type:
            logger.error("No 'plot_type' specified in attributes")
            return {}

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
                return {}

            result = visualizer(obj, attributes, fig=fig)
            if not result:
                logger.debug("No data to plot, returning empty figure")
                plt.close(fig)
                return {}

            return self._finalize_plot(fig, attributes, result)

        except Exception as e:
            logger.error(f"Visualization failed: {str(e)}")
            plt.close(fig)
            return {}

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
        """Plot UV coverage for an Observation with flexible filtering and frequency scaling.

        Args:
            obj: Observation object.
            attributes: Visualization attributes (source_name, baselines, scans, frequencies, units).
            fig: Matplotlib figure to plot on.

        Returns:
            Dictionary with counts of baselines, points, and frequencies.
        """
        with self._lock:
            logger.debug(f"Plotting UV coverage for {obj.get_observation_code()} with attributes: {attributes}")
            store_key = attributes.get("store_key", "uv_coverage")
            times_key = attributes.get("times_key", "times")
            baselines = attributes.get("baselines", [])
            source_name = attributes.get("source_name", None)
            scans = attributes.get("scans", [])
            frequencies = attributes.get("frequencies", [])
            units = attributes.get("units", "wavelengths")

            # Check if required filters are empty
            if not source_name or not baselines or not scans or not frequencies:
                logger.debug(f"Empty filter: source_name={source_name}, baselines={baselines}, "
                            f"scans={scans}, frequencies={frequencies}, returning empty plot")
                plt.close(fig)
                return {"baselines": 0, "points": 0, "frequencies": 0}

            # Fetch and filter data
            uv_data, times_data, scan_list = self._filter_data(
                obj.get_calculated_data_by_key(store_key),
                obj.get_calculated_data_by_key(times_key),
                source_name, scans, None  # time_range not used
            )

            # Return empty result if no data
            if not uv_data or not times_data:
                logger.debug("No UV data or times available, returning empty result")
                plt.close(fig)
                return {"baselines": 0, "points": 0, "frequencies": 0}

            # Filter valid frequencies
            freq_list = [float(f) for f in frequencies if isinstance(f, (int, float)) and f > 0]
            if not freq_list:
                logger.debug("No valid frequencies provided, returning empty result")
                plt.close(fig)
                return {"baselines": 0, "points": 0, "frequencies": 0}

            # Setup axes
            ax = self._setup_axes(fig, "uv_coverage", obj.get_observation_code())
            ax.invert_xaxis()

            # Constants for scaling
            SPEED_OF_LIGHT = 299792458.0
            EARTH_DIAMETER = 12742000.0

            # Choose reference frequency for scaling
            ref_freq = min(freq_list)
            ref_wavelength = SPEED_OF_LIGHT / (ref_freq * 1e6)
            logger.debug(f"Reference frequency: {ref_freq:.2f} MHz, reference wavelength: {ref_wavelength:.2e} m")

            # Process data
            result = {"baselines": 0, "points": 0, "frequencies": len(freq_list)}
            plotted_pairs = set()
            legend_handles = []
            legend_labels = []
            max_uv = 0.0  # For dynamic scaling of axes labels

            # Calculate max UV for scaling
            for source in uv_data:
                if source != source_name:
                    continue
                source_uv = uv_data[source]
                source_times = times_data[source]
                all_times = []
                all_uv_points = {}

                # Collect times and UV points
                for scan in scan_list:
                    if scan not in source_uv or scan not in source_times:
                        continue
                    times = [t.mjd for t in source_times[scan] if hasattr(t, 'mjd')]
                    if not times:
                        continue
                    all_times.extend(times)
                    uv_points = source_uv[scan]
                    for tel_code in uv_points:
                        if tel_code not in baselines:
                            continue
                        if tel_code not in all_uv_points:
                            all_uv_points[tel_code] = []
                        all_uv_points[tel_code].extend([(pt[0], pt[1]) for pt in uv_points[tel_code] if len(pt) >= 2])

                if not all_times or not all_uv_points:
                    continue

                # Sort times and points
                time_indices = np.argsort(all_times)
                all_times = [all_times[i] for i in time_indices]
                for tel_code in all_uv_points:
                    all_uv_points[tel_code] = [all_uv_points[tel_code][i] for i in time_indices if i < len(all_uv_points[tel_code])]

                # Calculate max UV for scaling
                for freq_mhz in freq_list:
                    wavelength = SPEED_OF_LIGHT / (freq_mhz * 1e6)
                    for tel_code in all_uv_points:
                        if tel_code not in baselines:
                            continue
                        valid_points = [(pt[0], pt[1]) for pt in all_uv_points[tel_code] if len(pt) >= 2]
                        if not valid_points:
                            continue
                        u, v = zip(*valid_points)
                        u, v = np.array(u, dtype=float), np.array(v, dtype=float)
                        if units == "wavelengths":
                            u_scaled = u / wavelength
                            v_scaled = v / wavelength
                        else:  # Earth diameters
                            u_scaled = (u / wavelength) / (EARTH_DIAMETER / ref_wavelength)
                            v_scaled = (v / wavelength) / (EARTH_DIAMETER / ref_wavelength)
                        max_uv = max(max_uv, np.max(np.abs(u_scaled)), np.max(np.abs(v_scaled)))

            # Determine SI prefix for wavelengths or Earth diameters
            if units == "wavelengths":
                if max_uv >= 1e12:
                    prefix, scale = "Tλ", 1e12
                elif max_uv >= 1e9:
                    prefix, scale = "Gλ", 1e9
                elif max_uv >= 1e6:
                    prefix, scale = "Mλ", 1e6
                elif max_uv >= 1e3:
                    prefix, scale = "kλ", 1e3
                else:
                    prefix, scale = "λ", 1.0
                ax.set_xlabel(f"u, ({prefix})")
                ax.set_ylabel(f"v, ({prefix})")
            else:
                prefix, scale = "xED", 1.0
                ax.set_xlabel("u, (xED)")
                ax.set_ylabel("v (xED)")

            # Plot UV points for each frequency and baseline
            for source in uv_data:
                if source != source_name:
                    continue
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
                        if tel_code not in baselines:
                            continue
                        if tel_code not in all_uv_points:
                            all_uv_points[tel_code] = []
                        all_uv_points[tel_code].extend([(pt[0], pt[1]) for pt in uv_points[tel_code] if len(pt) >= 2])

                if not all_times or not all_uv_points:
                    continue

                # Sort times and points
                time_indices = np.argsort(all_times)
                all_times = [all_times[i] for i in time_indices]
                for tel_code in all_uv_points:
                    all_uv_points[tel_code] = [all_uv_points[tel_code][i] for i in time_indices if i < len(all_uv_points[tel_code])]

                for freq_idx, freq_mhz in enumerate(freq_list):
                    wavelength = SPEED_OF_LIGHT / (freq_mhz * 1e6)
                    for tel_code in all_uv_points:
                        if tel_code not in baselines:
                            continue
                        valid_points = [(pt[0], pt[1]) for pt in all_uv_points[tel_code] if len(pt) >= 2]
                        if not valid_points:
                            continue
                        u, v = zip(*valid_points)
                        u, v = np.array(u, dtype=float), np.array(v, dtype=float)
                        if units == "wavelengths":
                            u_scaled = u / wavelength / scale
                            v_scaled = v / wavelength / scale
                        else:  # Earth diameters
                            u_scaled = (u / wavelength) / (EARTH_DIAMETER / ref_wavelength) / scale
                            v_scaled = (v / wavelength) / (EARTH_DIAMETER / ref_wavelength) / scale
                        color_idx = len(plotted_pairs) % len(self._style_config['colors'])
                        label = f"{tel_code} ({freq_mhz:.2f} MHz)"
                        handle = ax.scatter(
                            u_scaled, v_scaled, s=1, c=[self._style_config['colors'][color_idx]], label=label
                        )
                        ax.scatter(-u_scaled, -v_scaled, s=1, c=[self._style_config['colors'][color_idx]])
                        legend_handles.append(handle)
                        legend_labels.append((freq_mhz, tel_code))
                        plotted_pairs.add(f"{tel_code}_{freq_mhz}")
                        result["points"] += len(u_scaled)

            # If no data was plotted, return empty result
            if not plotted_pairs:
                logger.debug("No valid data plotted, returning empty result")
                plt.close(fig)
                return {"baselines": 0, "points": 0, "frequencies": 0}

            # Create grouped legend with frequencies as headers without markers
            if legend_handles:
                grouped_legend = {}
                for handle, (freq_mhz, tel_code) in zip(legend_handles, legend_labels):
                    freq_key = f"{freq_mhz:.2f} MHz"
                    if freq_key not in grouped_legend:
                        grouped_legend[freq_key] = []
                    grouped_legend[freq_key].append((handle, tel_code))

                legend_lines = []
                legend_texts = []
                for freq in sorted(grouped_legend.keys()):
                    # Add frequency header without marker
                    legend_lines.append(Line2D([0], [0], linestyle="none", marker="none"))
                    legend_texts.append(f"{freq}")
                    # Add baselines with markers
                    for handle, baseline in sorted(grouped_legend[freq], key=lambda x: x[1]):
                        legend_lines.append(handle)
                        legend_texts.append(f"    {baseline}")

                fig.legend(
                    legend_lines, legend_texts,
                    loc='center right', bbox_to_anchor=(0.98, 0.5),
                    fontsize=self._style_config['legend']['fontsize'],
                    title="Baselines:"
                )

            ax.set_title(f"(u,v) Coverage\nObs. code: {obj.get_observation_code()}")
            plt.tight_layout(rect=[0.05, 0.05, 0.85, 0.95])  # Adjusted for legend
            result["baselines"] = len(plotted_pairs)
            return result

    def _plot_sun_angles(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot angles to the Sun for an Observation with flexible filtering."""
        return self._plot_time_series(
            obj, attributes, fig, "sun_angles", 
            data_key=attributes.get("store_key", "sun_angles"),
            times_key=attributes.get("times_key", "times"),
            y_label="Angle to Sun (degrees)",
            value_extractors=[lambda x: x],
            labels=["Angle"]
        )

    def _plot_az_el(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot Azimuth/Elevation or Hour Angle/Declination for an Observation with one subplot per telescope."""
        coord_type = attributes.get("coord_type", "AzEl")
        if coord_type not in ["AzEl", "HADec"]:
            logger.warning(f"Invalid coord_type '{coord_type}', defaulting to 'AzEl'")
            coord_type = "AzEl"
        return self._plot_time_series(
            obj, attributes, fig, "az_el",
            data_key=attributes.get("store_key", "az_el"),
            times_key=attributes.get("times_key", "times"),
            y_label=f"Angle ({coord_type[:2]}/{coord_type[2:]}, deg)",
            value_extractors=[lambda x: x[0], lambda x: x[1]],
            labels=[f"{coord_type[:2]}", f"{coord_type[2:]}"]
        )

    def _plot_time_on_source(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot time on source for an Observation with flexible filtering."""
        with self._lock:
            logger.debug(f"Plotting time on source for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "time_on_source")
            source_name = attributes.get("source_name", None)
            telescopes = attributes.get("telescopes", None)
            scans = attributes.get("scans", None)
            time_range = attributes.get("time_range", None)

            if not self._check_filters(attributes, ["source_name", "telescopes", "scans"]):
                logger.debug("No filters specified, returning empty plot")
                return self._create_empty_plot(
                    fig, "time_on_source", obj.get_observation_code(),
                    labels={"xlabel": "Time (MJD)", "ylabel": "Telescope",
                            "title": f"Time on Source for Observation: {obj.get_observation_code()}"}
                )

            data = obj.get_calculated_data_by_key(store_key)
            data = data.get("data", {}) if isinstance(data, dict) else {}
            if not data:
                logger.debug("No time on source data, returning empty plot")
                return self._create_empty_plot(
                    fig, "time_on_source", obj.get_observation_code(),
                    labels={"xlabel": "Time (MJD)", "ylabel": "Telescope",
                            "title": f"Time on Source for Observation: {obj.get_observation_code()}"}
                )

            sources = [source_name] if source_name else list(data.keys())[:1]
            if not sources:
                logger.debug("No sources available, returning empty plot")
                return self._create_empty_plot(
                    fig, "time_on_source", obj.get_observation_code(),
                    labels={"xlabel": "Time (MJD)", "ylabel": "Telescope",
                            "title": f"Time on Source for Observation: {obj.get_observation_code()}"}
                )

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
                return self._create_empty_plot(
                    fig, "time_on_source", obj.get_observation_code(),
                    labels={"xlabel": "Time (MJD)", "ylabel": "Telescope",
                            "title": f"Time on {source_name}\n Obs.code: {obj.get_observation_code()}"}
                )

            # Plot time blocks
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

            # Compute and plot intersections
            if tel_list and all_blocks:
                all_times = [[(start, end) for start, end, _ in all_blocks[tel]] for tel in tel_list]
                if all_times and all(all_times):
                    time_points = sorted(set(t for tel_times in all_times for start, end in tel_times for t in (start, end)))
                    intersection_times = []
                    for i in range(len(time_points) - 1):
                        start, end = time_points[i], time_points[i + 1]
                        all_active = all(any(start_t <= start and end <= end_t for start_t, end_t in tel_times) 
                                        for tel_times in all_times)
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
                            label="Total" if i == 0 else None
                        )
                        ax.text(
                            (start + end) / 2, -0.5, f"{duration:.1f}s",
                            ha='center', va='center', fontsize=8, color='black',
                            bbox=dict(facecolor='white', alpha=0.8, edgecolor='none')
                        )
                        result["intersections"] = len(intersection_times)

            ax.set_yticks(np.arange(-1, len(tel_list)))
            ax.set_yticklabels(["Total"] + tel_list)
            if ax.get_legend_handles_labels()[0]:
                ax.legend(**self._style_config['legend'])
            return result

    def _plot_beam_pattern(self, obj: Observation, attributes: Dict[str, Any], fig: plt.Figure) -> Dict[str, Any]:
        """Plot beam patterns for an Observation with one subplot per telescope and a shared frequency legend.

        Args:
            obj: Observation object to visualize.
            attributes: Visualization attributes (freq_names, telescopes, store_key).
            fig: Matplotlib figure to plot on.

        Returns:
            Dictionary with counts of telescopes, frequencies, and plotted points.
        """
        with self._lock:
            logger.debug(f"Plotting beam pattern for {obj.get_observation_code()} with attributes: {attributes}")
            store_key = attributes.get("store_key", "beam_pattern")
            freq_names = attributes.get("freq_names", [])
            telescopes = attributes.get("telescopes", [])

            SPEED_OF_LIGHT = 299792458.0

            # Check if either telescopes or frequencies are empty
            if not telescopes or not freq_names:
                logger.debug(f"Empty filter: telescopes={telescopes}, freq_names={freq_names}, returning empty result")
                plt.close(fig)
                return {"telescopes": 0, "frequencies": 0}

            # Get beam data
            beam_data = obj.get_calculated_data_by_key(store_key)
            beam_data = beam_data.get("data", {}) if isinstance(beam_data, dict) else {}
            if not beam_data:
                logger.debug("No beam data available, returning empty result")
                plt.close(fig)
                return {"telescopes": 0, "frequencies": 0}

            # Filter telescopes to only those provided and present in beam_data
            tel_list = sorted([tel for tel in telescopes if tel in beam_data])
            if not tel_list:
                logger.debug("No valid telescopes in beam_data, returning empty result")
                plt.close(fig)
                return {"telescopes": 0, "frequencies": 0}

            # Filter frequencies to only those provided
            freq_list = [float(f) for f in freq_names if isinstance(f, (int, float)) and f > 0]
            if not freq_list:
                logger.debug("No valid frequencies provided, returning empty result")
                plt.close(fig)
                return {"telescopes": 0, "frequencies": 0}

            # Choose reference frequency (smallest frequency for scaling theta)
            ref_freq = min(freq_list)
            ref_wavelength = SPEED_OF_LIGHT / (ref_freq * 1e6)
            logger.debug(f"Reference frequency: {ref_freq:.2f} MHz, reference wavelength: {ref_wavelength:.2e} m")

            # Setup axes for plotting
            n_tels = len(tel_list)
            n_cols = int(np.ceil(np.sqrt(n_tels)))
            n_rows = int(np.ceil(n_tels / n_cols))
            axes = self._setup_axes(
                fig, "beam_pattern", obj.get_observation_code(),
                n_rows=n_rows, n_cols=n_cols, sharex=True, sharey=True
            )
            axes = np.atleast_1d(axes)  # Ensure axes is always an array for iteration

            result = {"telescopes": 0, "frequencies": len(freq_list)}
            plotted_telescopes = set()
            plotted_frequencies = set()
            legend_handles = []
            legend_labels = []

            for tel_idx, tel_code in enumerate(tel_list):
                ax = axes[tel_idx] if tel_idx < len(axes) else axes[-1]
                ax.set_title(tel_code)  # Set telescope code as subplot title

                beam = beam_data.get(tel_code, {})
                theta = np.array(beam.get("theta", []), dtype=float)
                pattern = np.array(beam.get("pattern", []), dtype=float)
                if len(theta) == 0 or len(pattern) == 0 or len(theta) != len(pattern):
                    logger.warning(f"Invalid beam data for {tel_code}: theta={len(theta)}, pattern={len(pattern)}")
                    continue

                for freq_idx, freq_mhz in enumerate(freq_list):
                    try:
                        wavelength = SPEED_OF_LIGHT / (freq_mhz * 1e6)
                        if wavelength <= 0:
                            logger.warning(f"Invalid frequency {freq_mhz} MHz for {tel_code}")
                            continue
                        # Scale theta based on frequency (θ ∝ λ/λ_ref)
                        theta_scaling_factor = ref_wavelength / wavelength  # = freq_mhz / ref_freq
                        scaled_theta = theta * theta_scaling_factor
                        # Normalize pattern to ensure maximum is 1.0
                        scaled_pattern = pattern / np.max(np.abs(pattern)) if np.max(np.abs(pattern)) > 0 else pattern
                        color_idx = freq_idx % len(self._style_config['colors'])
                        line, = ax.plot(
                            scaled_theta, scaled_pattern,
                            color=self._style_config['colors'][color_idx]
                        )
                        # collect legend info only once per frequency
                        label = f"{freq_mhz:.2f} MHz"
                        if label not in legend_labels:
                            legend_handles.append(line)
                            legend_labels.append(label)
                        theta_range = np.max(np.abs(scaled_theta)) * 1.1 if len(scaled_theta) > 0 else 1.0
                        ax.set_xlim(-theta_range, theta_range)
                        plotted_frequencies.add(freq_mhz)
                        logger.debug(f"Plotted beam for {tel_code} at {freq_mhz:.2f} MHz: "
                                    f"theta_scaling_factor={theta_scaling_factor:.2f}, "
                                    f"max_pattern={np.max(scaled_pattern):.2f}")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error plotting beam for {tel_code} at {freq_mhz} MHz: {str(e)}")
                        continue

                plotted_telescopes.add(tel_code)

            # Hide axes labels for all subplots except bottom-left
            for ax in axes:
                ax.set_xlabel("")
                ax.set_ylabel("")
            # Set single shared labels
            if plotted_telescopes:
                fig.text(0.5, 0.04, "Theta, (rad.)", ha='center', fontsize=12)
                fig.text(0.04, 0.5, "Normalized Peak Flux", va='center', rotation='vertical', fontsize=12)

            # Add a single shared legend for frequencies
            if legend_handles:
                fig.legend(
                    legend_handles, legend_labels,
                    loc='center right', bbox_to_anchor=(0.98, 0.5),
                    fontsize=self._style_config['legend']['fontsize'],
                    title="Frequencies:"
                )

            # Hide unused subplots
            for idx in range(len(tel_list), len(axes)):
                axes[idx].set_visible(False)

            # If no data was plotted, return empty result
            if not plotted_telescopes:
                logger.debug("No valid data plotted, returning empty result")
                plt.close(fig)
                return {"telescopes": 0, "frequencies": 0}

            fig.suptitle(f"Beam Pattern\nObs.code: {obj.get_observation_code()}", fontsize=14)
            plt.tight_layout(rect=[0.05, 0.05, 0.85, 0.95])  # Adjusted for legend and labels
            result["telescopes"] = len(plotted_telescopes)
            result["frequencies"] = len(plotted_frequencies)
            return result

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

            if not self._check_filters(attributes, ["source_name", "baselines", "scans", "frequencies"]):
                logger.debug("No filters specified, returning empty plot")
                return self._create_empty_plot(
                    fig, "baseline_projections", obj.get_observation_code(),
                    labels={"xlabel": "Time (MJD)", "ylabel": f"Baseline Length ({units})",
                            "title": f"Baseline Projections for Observation: {obj.get_observation_code()}"}
                )

            bl_data, times_data, scan_list = self._filter_data(
                obj.get_calculated_data_by_key(store_key),
                obj.get_calculated_data_by_key(times_key),
                source_name, scans, time_range
            )

            if not bl_data or not times_data:
                logger.debug("No data available, returning empty plot")
                return self._create_empty_plot(
                    fig, "baseline_projections", obj.get_observation_code(),
                    labels={"xlabel": "Time (MJD)", "ylabel": f"Baseline Length ({units})",
                            "title": f"Baseline Projections for Observation: {obj.get_observation_code()}"}
                )

            ax = self._setup_axes(fig, "baseline_projections", obj.get_observation_code())
            ax.set_xlabel("Time (MJD)")
            ax.set_ylabel(f"Baseline Length ({units})")
            ax.set_title(f"Baseline Projections for Observation: {obj.get_observation_code()}")

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

            if not self._check_filters(attributes, ["telescopes", "scans"]):
                logger.debug("No telescopes or scans specified, returning empty plot")
                return self._create_empty_plot(
                    fig, "mollweide_tracks", obj.get_observation_code(),
                    projection="mollweide",
                    labels={"title": f"Mollweide Tracks for Observation: {obj.get_observation_code()}"}
                )

            data = obj.get_calculated_data_by_key(store_key)
            if not data or not isinstance(data, dict):
                logger.warning(f"No valid Mollweide track data found for '{store_key}'")
                return self._create_empty_plot(
                    fig, "mollweide_tracks", obj.get_observation_code(),
                    projection="mollweide",
                    labels={"title": f"Mollweide Tracks for Observation: {obj.get_observation_code()}"}
                )

            metadata = data.get("metadata", {})
            scan_data = data.get("data", {})
            ax = self._setup_axes(fig, "mollweide_tracks", obj.get_observation_code(), projection="mollweide")
            ax.set_title(f"Mollweide Tracks for Observation: {obj.get_observation_code()}")

            result = {"scans": 0, "telescopes": 0, "sources": 0, "points": 0}
            plotted_telescopes = set()
            plotted_sources = set()

            # Plot sources
            for source_name, coords in metadata.get("sources", {}).items():
                if not isinstance(coords, (list, np.ndarray)) or len(coords) != 2:
                    logger.warning(f"Invalid source coordinates format for {source_name}: {coords}")
                    continue
                try:
                    lon, lat = float(coords[0]), float(coords[1])
                    lon_rad = np.radians(lon)
                    lat_rad = np.radians(lat)
                    ax.scatter(
                        lon_rad, lat_rad, c="red", marker="*", s=100,
                        label=f"Source: {source_name}" if source_name not in plotted_sources else None,
                        zorder=3, edgecolors="black"
                    )
                    plotted_sources.add(source_name)
                    result["sources"] += 1
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to plot source {source_name}: {str(e)}")
                    continue

            # Process scan data
            scan_list = scans if scans else list(scan_data.keys())
            result["scans"] = len(scan_list)
            all_tracks = {}
            for scan_name in scan_list:
                if scan_name not in scan_data:
                    continue
                scan = scan_data[scan_name]
                tel_list = telescopes if telescopes else list(scan.keys())
                for tel_code in tel_list:
                    if tel_code not in scan:
                        continue
                    tracks = scan[tel_code]
                    if not isinstance(tracks, np.ndarray) or len(tracks) == 0 or tracks.ndim != 2 or tracks.shape[1] != 2:
                        continue
                    if tel_code not in all_tracks:
                        all_tracks[tel_code] = []
                    all_tracks[tel_code].append(tracks)

            # Plot tracks
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
                color_idx = len(plotted_telescopes) % len(self._style_config["colors"])
                ax.scatter(
                    lon_rad, lat_rad, s=1, c=[self._style_config["colors"][color_idx]],
                    label=f"{tel_code}" if tel_code not in plotted_telescopes else None,
                    zorder=1
                )
                plotted_telescopes.add(tel_code)
                result["points"] += len(lon)

            result["telescopes"] = len(plotted_telescopes)
            if plotted_telescopes or plotted_sources:
                ax.legend(**self._style_config["legend"])
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