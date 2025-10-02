# pastrocore/super/schedule_visualizer.py
from common.super.super import Super
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from pastrocore.base.telescopes import Telescope, SpaceTelescope, Telescopes
from pastrocore.base.sources import Source, Sources
from pastrocore.base.scans import Scan, Scans
from pastrocore.base.frequencies import IF, Frequencies

from common.utils.logging_setup import logger
from typing import Dict, Any, Callable, Union, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np
from astropy.time import Time
import threading
import os
import warnings
from erfa import ErfaWarning
import gc
import pandas as pd

from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D

warnings.filterwarnings("ignore", category=ErfaWarning)

class ScheduleVisualizer(Super):
    SPEED_OF_LIGHT: float = 299792458.0  # Speed of light in m/s
    EARTH_DIAMETER: float = 12742000.0   # Earth diameter in meters

    OPERATION = "visualize"

    def __init__(self, manipulator: 'Manipulator'):
        super().__init__(manipulator)
        self._lock = threading.Lock()
        
        # Default style configuration
        self._style_config = {
            'plt_style': 'seaborn-v0_8-whitegrid',
            'figure': {
                'figsize': (10, 6),
                'dpi': 76,
                'facecolor': 'white'
            },
            'axes': {
                'facecolor': 'white',
                'edgecolor': 'black',
                'labelcolor': 'black',
                'grid': True
            },
            'grid': {
                'color': 'lightgray',
                'linestyle': '--',
                'linewidth': 0.5
            },
            'font': {
                'family': 'Trebuchet MS',
                'size': 12,
                'title_size': 14,
                'label_size': 12,
                'tick_size': 12,
                'legend_size': 12
            },
            'text': {
                'color': 'black'
            },
            'xtick': {
                'color': 'black',
                'labelsize': 12
            },
            'ytick': {
                'color': 'black',
                'labelsize': 12
            },
            'legend': {
                'loc': 'upper right',
                'bbox_to_anchor': (1.0, 0.95),
                'fontsize': 11,
                'title_fontsize': 12
            },
            'colors': [
                (163/255, 193/255, 218/255),  # Light blue
                (74/255, 144/255, 226/255),   # Blue
                (80/255, 200/255, 120/255),   # Green
                (46/255, 139/255, 87/255),    # Dark green
                (255/255, 99/255, 71/255),    # Tomato
                (255/255, 165/255, 0/255),    # Orange
                (255/255, 140/255, 0/255),    # Dark orange
                (218/255, 112/255, 214/255),  # Orchid
                (255/255, 215/255, 0/255),    # Gold
                (139/255, 69/255, 19/255),    # Brown
            ],
            'colormaps': {
                'redpurple': LinearSegmentedColormap.from_list(
                    "RedPurple",
                    [(139/255, 0/255, 0/255), (255/255, 69/255, 0/255), (255/255, 255/255, 0/255),
                     (0/255, 255/255, 0/255), (0/255, 206/255, 209/255), (0/255, 0/255, 139/255)][::-1]
                )
            },
            'intersection_color': (255/255, 165/255, 0/255),  # Orange for intersections
            'markers': {
                'default_size': 50,
                'source_style': '*',
                'track_style': 'o',
                'track_size': 0.5,
                'scatter_size': 5
            },
            'linestyles': {
                'default': '-',
                'secondary': '--'
            }
        }

        self._apply_style_config()

        self._object_visualizers: Dict[type, Callable] = {
            (ScheduleProject, Observation): self._visualize_project_or_observation
        }

        self._plot_types: Dict[str, Callable] = {
                "uv_coverage": lambda obj, attrs, fig=None: self._plot_uv_coverage(
                    obj, attrs, fig or Figure(figsize=self._style_config['figure']['figsize'])
                ),
                "sun_angles": lambda obj, attrs, fig=None: self._plot_time_series(
                    obj, attrs, fig or Figure(figsize=self._style_config['figure']['figsize']),
                    "sun_angles", "sun_angles", "times", "Angle, (deg.)",
                    [lambda row: row["angle"]], ["Angle"]
                ),
                "az_el": lambda obj, attrs, fig=None: self._plot_time_series(
                    obj, attrs, fig or Figure(figsize=self._style_config['figure']['figsize']),
                    "az_el", "az_el", "times", "Angle, (deg.)",
                    [lambda row: row["az"], lambda row: row["el"]], ["Az", "El"]
                ),
                "time_on_source": lambda obj, attrs, fig=None: self._plot_time_on_source(
                    obj, attrs, fig or Figure(figsize=self._style_config['figure']['figsize'])
                ),
                "beam_pattern": lambda obj, attrs, fig=None: self._plot_beam_pattern(
                    obj, attrs, fig or Figure(figsize=self._style_config['figure']['figsize'])
                ),
                "baseline_projections": lambda obj, attrs, fig=None: self._plot_baseline_projections(
                    obj, attrs, fig or Figure(figsize=self._style_config['figure']['figsize'])
                ),
                "mollweide_tracks": lambda obj, attrs, fig=None: self._plot_mollweide_tracks(
                    obj, attrs, fig or Figure(figsize=self._style_config['figure']['figsize'])
                ),
            }
        logger.debug("Initialized ScheduleVisualizer")

    def _apply_style_config(self) -> None:
        """Apply the style configuration to matplotlib."""
        plt.style.use(self._style_config['plt_style'])
        plt.rc('axes', **self._style_config['axes'])
        plt.rc('grid', **self._style_config['grid'])
        plt.rc('xtick', **self._style_config['xtick'])
        plt.rc('ytick', **self._style_config['ytick'])
        
        valid_font_params = {k: v for k, v in self._style_config['font'].items() 
                            if k in ['family', 'size', 'weight', 'style', 'variant', 'stretch']}
        plt.rc('font', **valid_font_params)
        plt.rc('text', **self._style_config['text'])
        plt.rc('figure', **self._style_config['figure'])
        
        valid_legend_params = {k: v for k, v in self._style_config['legend'].items() 
                            if k in ['fontsize', 'title_fontsize', 'loc', 'frameon', 'shadow', 
                                        'framealpha', 'edgecolor', 'facecolor', 'numpoints', 
                                        'scatterpoints', 'markerscale', 'labelspacing', 'columnspacing', 
                                        'handlelength', 'handletextpad', 'borderpad', 'borderaxespad']}
        plt.rc('legend', **valid_legend_params)

    def get_style_config(self) -> Dict[str, Any]:
        """Return the current style configuration.

        Returns:
            Dict[str, Any]: A copy of the current style configuration dictionary.
        """
        import copy
        logger.debug("Retrieving style configuration")
        return copy.deepcopy(self._style_config)

    def set_style_config(self, config: Dict[str, Any], partial: bool = False) -> None:
        """Set a new style configuration and apply it.

        Args:
            config (Dict[str, Any]): New style configuration dictionary or partial updates.
            partial (bool): If True, update only provided keys; if False, replace entire config.

        Raises:
            ValueError: If the provided configuration is invalid.
        """
        logger.debug(f"Setting style configuration (partial={partial}): {config}")

        def validate_config(config: Dict[str, Any]) -> None:
            """Validate configuration values."""
            if not isinstance(config, dict):
                raise ValueError("Configuration must be a dictionary")
            if 'plt_style' in config and not isinstance(config['plt_style'], str):
                raise ValueError("plt_style must be a string")
            if 'figure' in config:
                if not isinstance(config['figure'], dict):
                    raise ValueError("figure must be a dictionary")
                if 'figsize' in config['figure'] and not isinstance(config['figure']['figsize'], (tuple, list)):
                    raise ValueError("figsize must be a tuple or list")
                if 'dpi' in config['figure'] and not isinstance(config['figure']['dpi'], (int, float)):
                    raise ValueError("dpi must be a number")
            if 'font' in config:
                if not isinstance(config['font'], dict):
                    raise ValueError("font must be a dictionary")
                for key in ['size', 'title_size', 'label_size', 'tick_size', 'legend_size']:
                    if key in config['font'] and not isinstance(config['font'][key], (int, float)):
                        raise ValueError(f"font.{key} must be a number")
            if 'colors' in config and not isinstance(config['colors'], (list, tuple)):
                raise ValueError("colors must be a list or tuple")
            if 'colormaps' in config and not isinstance(config['colormaps'], dict):
                raise ValueError("colormaps must be a dictionary")
            if 'intersection_color' in config and not isinstance(config['intersection_color'], (tuple, list)):
                raise ValueError("intersection_color must be a tuple or list")
            if 'markers' in config:
                if not isinstance(config['markers'], dict):
                    raise ValueError("markers must be a dictionary")
                for key in ['default_size', 'track_size', 'scatter_size']:
                    if key in config['markers'] and not isinstance(config['markers'][key], (int, float)):
                        raise ValueError(f"markers.{key} must be a number")
                for key in ['source_style', 'track_style']:
                    if key in config['markers'] and not isinstance(config['markers'][key], str):
                        raise ValueError(f"markers.{key} must be a string")
            if 'linestyles' in config:
                if not isinstance(config['linestyles'], dict):
                    raise ValueError("linestyles must be a dictionary")
                for key in ['default', 'secondary']:
                    if key in config['linestyles'] and not isinstance(config['linestyles'][key], str):
                        raise ValueError(f"linestyles.{key} must be a string")

        with self._lock:
            if partial:
                import copy
                new_config = copy.deepcopy(self._style_config)
                for key, value in config.items():
                    if isinstance(value, dict) and key in new_config and isinstance(new_config[key], dict):
                        new_config[key].update(value)
                    else:
                        new_config[key] = value
            else:
                required_keys = {'plt_style', 'figure', 'axes', 'grid', 'font', 'text', 'xtick', 'ytick', 'legend', 'colors', 'colormaps', 'intersection_color', 'markers', 'linestyles'}
                if not all(key in config for key in required_keys):
                    missing = required_keys - set(config.keys())
                    logger.error(f"Invalid style configuration: missing keys {missing}")
                    raise ValueError(f"Style configuration must include all required keys: {missing}")
                new_config = config

            try:
                validate_config(new_config)
            except ValueError as e:
                logger.error(f"Invalid style configuration: {str(e)}")
                raise

            self._style_config = new_config
            self._apply_style_config()
            logger.info("Style configuration updated and applied")

    def execute(self, obj: Union[ScheduleProject, Observation, Telescope, SpaceTelescope, Telescopes, Source, Sources, Scan, Scans, IF, Frequencies], 
                attributes: Dict[str, Any] = None, method: str = None) -> Dict[str, Any]:
        """Execute visualization operation on the specified object."""
        if attributes is None:
            attributes = {}
        logger.debug(f"Executing visualization on {type(obj).__name__} with attributes={attributes}, method={method}")

        try:
            if method:
                method_func = getattr(self, method, None)
                if callable(method_func):
                    result = method_func(obj, attributes)
                    return self._build_response(obj, True, method, result)

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

            obj_type_name = type(obj).__name__.lower()
            auto_method_name = f"_visualize_{obj_type_name}"
            method = getattr(self, auto_method_name, None)
            if callable(method):
                result = method(obj, attributes)
                return self._build_response(obj, True, auto_method_name, result)

            result = self._visualize(obj, attributes)
            if result is None:
                return self._build_response(obj, False, "_visualize", None, "Visualization failed")
            return self._build_response(obj, True, "_visualize", result)

        except Exception as e:
            logger.error(f"Visualization execution failed: {str(e)}")
            return self._build_response(obj, False, None, None, str(e))
        
    def _create_empty_plot(self, fig: Figure, plot_type: str, obj_name: str, 
                      projection: str = None, labels: Dict[str, str] = None) -> Dict[str, Any]:
        """Create an empty plot with consistent styling and labels."""
        ax = self._setup_axes(fig, plot_type, obj_name, projection=projection)
        if labels:
            ax.set_xlabel(labels.get('xlabel', ''), fontsize=self._style_config['font']['label_size'])
            ax.set_ylabel(labels.get('ylabel', ''), fontsize=self._style_config['font']['label_size'])
            ax.set_title(labels.get('title', f"{plot_type.replace('_', ' ').title()} for {obj_name}"),
                        fontsize=self._style_config['font']['title_size'])
            ax.tick_params(axis='both', labelsize=self._style_config['font']['tick_size'])
        logger.debug(f"Created empty plot for {plot_type} with obj_name={obj_name}")
        return {}
    
    def _filter_dataframe(self, data: pd.DataFrame, times_data: pd.DataFrame, 
                     source_name: Optional[str] = None, scans: Optional[List[str]] = None, 
                     telescopes: Optional[List[str]] = None, 
                     time_range: Optional[Tuple[Time, Time]] = None) -> Tuple[pd.DataFrame, List[str]]:
        """
        Filter pandas DataFrame based on provided criteria.

        Args:
            data: DataFrame with calculated data.
            times_data: DataFrame with time data.
            source_name: Source name to filter by.
            scans: List of scan names to filter by.
            telescopes: List of telescope codes to filter by.
            time_range: Tuple of (start_time, end_time) as astropy.Time objects.

        Returns:
            Tuple[pd.DataFrame, List[str]]: Filtered DataFrame and list of valid scan names.
        """
        logger.debug(f"Filtering data with source_name={source_name}, scans={scans}, "
                    f"telescopes={telescopes}, time_range={time_range}")
        
        filtered_data = data.copy()
        valid_scans = scans if scans else data.get("scan_name", pd.Series([])).unique().tolist()

        if source_name and "source_name" in filtered_data.columns:
            filtered_data = filtered_data[filtered_data["source_name"] == source_name]
            if filtered_data.empty:
                logger.debug(f"No data for source {source_name}")
                return pd.DataFrame(), []

        if scans and "scan_name" in filtered_data.columns:
            filtered_data = filtered_data[filtered_data["scan_name"].isin(scans)]
            valid_scans = [s for s in scans if s in filtered_data["scan_name"].values]
            if filtered_data.empty:
                logger.debug(f"No data for scans {scans}")
                return pd.DataFrame(), []

        if telescopes and "telescope_code" in filtered_data.columns:
            filtered_data = filtered_data[filtered_data["telescope_code"].isin(telescopes)]
            if filtered_data.empty:
                logger.debug(f"No data for telescopes {telescopes}")
                return pd.DataFrame(), []

        if time_range and "time" in filtered_data.columns:
            start_time, end_time = time_range
            filtered_data = filtered_data[
                (filtered_data["time"] >= start_time) & (filtered_data["time"] <= end_time)
            ]
            if filtered_data.empty:
                logger.debug(f"No data within time range {time_range}")
                return pd.DataFrame(), []

        filtered_times = times_data.copy()
        if scans and "scan_name" in filtered_times.columns:
            filtered_times = filtered_times[filtered_times["scan_name"].isin(valid_scans)]
        if source_name and "source_name" in filtered_times.columns:
            filtered_times = filtered_times[filtered_times["source_name"] == source_name]
        if time_range and "time" in filtered_times.columns:
            filtered_times = filtered_times[
                (filtered_times["time"] >= start_time) & (filtered_times["time"] <= end_time)
            ]

        logger.debug(f"Filtered data: {len(filtered_data)} rows, valid scans: {valid_scans}")
        return filtered_data, valid_scans
    
    def _check_filters(self, attributes: Dict[str, Any], required_filters: List[str]) -> bool:
        """Check if any of the required filters are provided."""
        return any(attributes.get(key) for key in required_filters)
    
    def _plot_time_series(self, obj: Observation, attributes: Dict[str, Any], fig: Figure, 
                      plot_type: str, data_key: str, times_key: str, y_label: str,
                      value_extractors: List[Callable], labels: List[str]) -> Dict[str, Any]:
        """
        Generic method to plot time series data with flexible filtering and multi-value plotting.
        
        Args:
            obj: Observation object to visualize.
            attributes: Dictionary with visualization parameters (source_name, telescopes, scans, etc.).
            fig: Matplotlib Figure object for plotting.
            plot_type: Type of plot ('sun_angles', 'az_el', etc.).
            data_key: Key for accessing calculated data.
            times_key: Key for accessing time data.
            y_label: Label for the y-axis.
            value_extractors: List of functions to extract values from data.
            labels: List of labels for the plotted values.

        Returns:
            Dict[str, Any]: Dictionary with visualization results (scans, telescopes, points).
        """
        with self._lock:
            logger.debug(f"Plotting {plot_type} for {obj.get_observation_code()}")
            source_name = attributes.get("source_name")
            telescopes = attributes.get("telescopes")
            scans = attributes.get("scans")
            time_range = attributes.get("time_range")

            if not self._check_filters(attributes, ["source_name", "telescopes", "scans"]):
                logger.debug(f"No filters specified for {plot_type}, returning empty plot")
                return self._create_empty_plot(
                    fig, plot_type, obj.get_observation_code(),
                    labels={"xlabel": "Time (ISOT)", "ylabel": y_label, 
                            "title": f"{plot_type.replace('_', ' ').title()}\nObs. code: {obj.get_observation_code()}"}
                )

            data = obj.get_calculated_data_by_key(data_key)
            times_data = obj.get_calculated_data_by_key(times_key)
            
            if not isinstance(data, pd.DataFrame) or not isinstance(times_data, pd.DataFrame):
                logger.debug(f"Invalid data format for {plot_type}, returning empty plot")
                return self._create_empty_plot(
                    fig, plot_type, obj.get_observation_code(),
                    labels={"xlabel": "Time (ISOT)", "ylabel": y_label, 
                            "title": f"{plot_type.replace('_', ' ').title()}\nObs. code: {obj.get_observation_code()}"}
                )

            filtered_data, valid_scans = self._filter_dataframe(data, times_data, source_name, scans, telescopes, time_range)
            
            if filtered_data.empty:
                logger.debug(f"No data after filtering for {plot_type}, returning empty plot")
                return self._create_empty_plot(
                    fig, plot_type, obj.get_observation_code(),
                    labels={"xlabel": "Time (ISOT)", "ylabel": y_label, 
                            "title": f"{plot_type.replace('_', ' ').title()}\nObs. code: {obj.get_observation_code()}"}
                )

            n_tels = len(telescopes) if telescopes else filtered_data["telescope_code"].nunique()
            n_rows = n_tels if plot_type == "az_el" else 1
            n_cols = 1
            axes = self._setup_axes(fig, plot_type, obj.get_observation_code(), n_rows=n_rows, n_cols=n_cols, sharex=True, sharey=True)
            axes = np.atleast_1d(axes).tolist()

            result = {"scans": len(valid_scans), "telescopes": 0, "points": 0}
            plotted_telescopes = set()
            legend_handles = []
            legend_labels = []

            grouped_data = filtered_data.groupby("telescope_code")
            tel_list = telescopes if telescopes else filtered_data["telescope_code"].unique()

            for tel_idx, tel in enumerate(tel_list):
                if tel not in grouped_data.groups:
                    continue
                tel_data = grouped_data.get_group(tel)
                times = tel_data["time"].apply(lambda x: x.isot if isinstance(x, Time) else x)
                ax = axes[tel_idx] if plot_type == "az_el" and n_tels > 1 else axes[0]
                
                for i, (extractor, label) in enumerate(zip(value_extractors, labels)):
                    values = tel_data.apply(extractor, axis=1)
                    valid_mask = ~values.isna()
                    valid_times = times[valid_mask]
                    valid_values = values[valid_mask]
                    
                    if valid_times.empty:
                        continue
                    
                    color_idx = tel_idx % len(self._style_config['colors'])
                    linestyle = self._style_config['linestyles']['secondary'] if i > 0 and plot_type == "az_el" else self._style_config['linestyles']['default']
                    line, = ax.plot(
                        valid_times, valid_values,
                        label=f"{tel} ({label})" if plot_type == "az_el" else f"{tel}",
                        color=self._style_config['colors'][color_idx],
                        linestyle=linestyle
                    )
                    if tel not in plotted_telescopes:
                        legend_handles.append(line)
                        legend_labels.append(f"{tel}")
                    result["points"] += len(valid_values)
                
                if plot_type == "az_el" and n_tels > 1:
                    ax.set_title(f"{tel}", fontsize=self._style_config['font']['title_size'])
                ax.tick_params(axis='both', labelsize=self._style_config['font']['tick_size'])
                plotted_telescopes.add(tel)

            result["telescopes"] = len(plotted_telescopes)
            if plotted_telescopes:
                if plot_type == "az_el" and n_tels > 1:
                    fig.text(0.5, 0.04, "Time (ISOT)", ha='center', fontsize=self._style_config['font']['label_size'])
                    fig.text(0.04, 0.5, y_label, va='center', rotation='vertical', fontsize=self._style_config['font']['label_size'])
                    fig.suptitle(f"Az/El or Ha/Dec\nObs. code: {obj.get_observation_code()}\nSource: {source_name}", fontsize=self._style_config['font']['title_size'])
                    if legend_handles:
                        grouped_legend = {}
                        for handle, label in zip(legend_handles, legend_labels):
                            tel_key = label
                            if tel_key not in grouped_legend:
                                grouped_legend[tel_key] = []
                            grouped_legend[tel_key].append(handle)

                        legend_lines = []
                        legend_texts = []
                        for tel in sorted(grouped_legend.keys()):
                            legend_lines.append(grouped_legend[tel][0])
                            legend_texts.append(f"    {tel}")

                        fig.subplots_adjust(left=0.10, bottom=0.10, right=0.88, top=0.85)
                        fig.legend(
                            legend_lines, legend_texts,
                            loc=self._style_config['legend']['loc'], 
                            bbox_to_anchor=self._style_config['legend']['bbox_to_anchor'],
                            fontsize=self._style_config['legend']['fontsize'],
                            title="Telescopes:",
                            title_fontsize=self._style_config['legend']['title_fontsize'],
                            bbox_transform=fig.transFigure
                        )
                else:
                    axes[0].set_xlabel("Time (ISOT)", fontsize=self._style_config['font']['label_size'])
                    axes[0].set_ylabel(y_label, fontsize=self._style_config['font']['label_size'])
                    axes[0].set_title(f"{plot_type.replace('_', ' ').title()}\nObs. code: {obj.get_observation_code()}\nSource: {source_name}", 
                                    fontsize=self._style_config['font']['title_size'])
                    axes[0].tick_params(axis='both', labelsize=self._style_config['font']['tick_size'])
                    if legend_handles:
                        fig.subplots_adjust(left=0.10, bottom=0.10, right=0.88, top=0.90)
                        fig.legend(
                            legend_handles, legend_labels,
                            loc=self._style_config['legend']['loc'], 
                            bbox_to_anchor=self._style_config['legend']['bbox_to_anchor'],
                            fontsize=self._style_config['legend']['fontsize'],
                            title="Telescopes:",
                            title_fontsize=self._style_config['legend']['title_fontsize']
                        )

            for ax in axes[max(1, len(plotted_telescopes) if plot_type == "az_el" else 1):]:
                ax.set_visible(False)
            return result

    def _setup_axes(self, fig: Figure, plot_type: str, obj_name: str, projection: str = None, 
                    n_rows: int = 1, n_cols: int = 1, sharex: bool = False, sharey: bool = False) -> Union[plt.Axes, np.ndarray]:
        """Set up axes for plotting with consistent styling."""
        if projection:
            axes = fig.add_subplot(111, projection=projection)
        else:
            axes = fig.subplots(n_rows, n_cols, sharex=sharex, sharey=sharey)
            if n_rows * n_cols > 1:
                axes = np.array(axes).flatten()
            else:
                axes = axes if n_rows == 1 and n_cols == 1 else np.array([axes])
        return axes

    def _finalize_plot(self, fig: Figure, attributes: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Finalize the plot by saving, displaying, or returning the figure.

        Args:
            fig: Matplotlib Figure object to finalize.
            attributes: Dictionary with visualization parameters (output_file, show, return_figure).
            result: Dictionary with visualization results.

        Returns:
            Dict[str, Any]: Updated result dictionary with figure reference (if return_figure=True).
        """
        output_file = attributes.get("output_file")
        show = attributes.get("show", False)
        return_figure = attributes.get("return_figure", False)

        if output_file and output_file.strip():
            output_dir = os.path.dirname(output_file)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            fig.savefig(output_file, dpi=self._style_config['figure']['dpi'], bbox_inches='tight')
            logger.info(f"Visualization saved to '{output_file}'")

        if show:
            logger.debug("Displaying plot with plt.show()")
            plt.show()

        if not return_figure:
            logger.debug(f"Closing figure {id(fig)}")
            plt.close(fig)
            if len(plt.get_fignums()) > 10:  # Check for excessive open figures
                logger.warning(f"Excessive open figures detected: {len(plt.get_fignums())}")
                plt.close('all')

        result["figure"] = fig if return_figure else None
        return result

    def _visualize(self, obj: Union[ScheduleProject, Observation, Telescope, SpaceTelescope, Telescopes, Source, Sources, Scan, Scans, IF, Frequencies], 
                   attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Visualize the specified object."""
        plot_type = attributes.get("plot_type")
        if not plot_type:
            logger.error("No 'plot_type' specified in attributes")
            return {}

        fig = Figure(figsize=attributes.get("figsize", self._style_config['figure']['figsize']))
        
        try:
            visualizer = None
            for types, func in self._object_visualizers.items():
                if isinstance(obj, types):
                    visualizer = func
                    break
            if not visualizer:
                logger.debug(f"Closing figure due to unsupported object type: {type(obj)}")
                fig.clf()
                plt.close(fig)
                gc.collect(2)
                return {}

            result = visualizer(obj, attributes, fig=fig)
            if not result:
                logger.debug("No data to plot, returning empty figure")
                fig.clf()
                plt.close(fig)
                gc.collect(2)
                return {}

            return self._finalize_plot(fig, attributes, result)

        except Exception as e:
            logger.error(f"Visualization failed: {str(e)}")
            fig.clf()
            plt.close(fig)
            gc.collect(2)
            return {}

    def _visualize_project_or_observation(self, obj: Union[ScheduleProject, Observation], attributes: Dict[str, Any], fig: Figure = None) -> Dict[str, Any]:
        """Visualize a ScheduleProject or Observation object."""
        logger.debug(f"Visualizing {type(obj).__name__} with attributes: {attributes}")
        plot_type = attributes.get("plot_type")
        output_file = attributes.get("output_file")
        dpi = attributes.get("dpi", self._style_config['figure']['dpi'])  # Use default dpi from config if not specified

        # Validate dpi
        if not isinstance(dpi, (int, float)):
            logger.error(f"Invalid dpi type: expected int or float, got {type(dpi)}: {dpi}")
            raise ValueError(f"dpi must be a number, got {type(dpi)}: {dpi}")

        logger.debug(f"Using dpi={dpi} for visualization of plot_type={plot_type}")

        if isinstance(obj, ScheduleProject):
            observations = obj.get_observations()
            if not observations:
                logger.warning(f"No observations in ScheduleProject '{obj.get_name()}'")
                return {}
            with ThreadPoolExecutor() as executor:
                futures = {executor.submit(self._visualize, obs, attributes, None): obs.get_observation_code() for obs in observations}
                results = {code: future.result() for future, code in futures.items() if future.result() is not None}
            return results
        
        plot_func = self._plot_types.get(plot_type)
        if not plot_func:
            logger.warning(f"Unsupported plot_type '{plot_type}' for {type(obj).__name__}")
            return {}
        
        result = plot_func(obj, attributes, fig=fig)
        
        if not isinstance(result, dict):
            logger.error(f"Plot function {plot_type} returned invalid result: {type(result)}")
            return {"status": False, "message": f"Invalid result from {plot_type}"}
        
        if output_file and result.get("status", False):
            try:
                with self._lock:
                    fig = result.get("figure", plt.gcf())
                    logger.debug(f"Saving visualization to {output_file} with dpi={dpi}")
                    fig.savefig(output_file, dpi=float(dpi), bbox_inches="tight")
                    logger.info(f"Saved visualization to {output_file} with dpi={dpi}")
                    plt.close(fig)
                    gc.collect()  # Clean up memory
            except Exception as e:
                logger.error(f"Failed to save visualization to {output_file}: {str(e)}")
                result["status"] = False
                result["message"] = f"Failed to save visualization: {str(e)}"
        
        return result

    def _plot_uv_coverage(self, obj: Observation, attributes: Dict[str, Any], fig: Figure) -> Dict[str, Any]:
        """
        Plot UV coverage for an Observation with flexible filtering and grouped legend.

        Args:
            obj: Observation object to visualize.
            attributes: Dictionary with visualization parameters (store_key, times_key, baselines, source_name, scans, time_range, frequencies, units).
            fig: Matplotlib Figure object for plotting.

        Returns:
            Dict[str, Any]: Dictionary with visualization results (scans, baselines, points, frequencies).
        """
        with self._lock:
            logger.debug(f"Plotting UV coverage for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "uv_coverage")
            times_key = attributes.get("times_key", "times")
            baselines = attributes.get("baselines", [])
            source_name = attributes.get("source_name")
            scans = attributes.get("scans")
            time_range = attributes.get("time_range")
            frequencies = attributes.get("frequencies", [])
            units = attributes.get("units", "wavelengths")

            if not self._check_filters(attributes, ["source_name", "baselines", "scans", "frequencies"]):
                logger.debug(f"Missing required filters for UV coverage, returning empty plot")
                return self._create_empty_plot(
                    fig, "uv_coverage", obj.get_observation_code(),
                    labels={"xlabel": f"U, ({units})", "ylabel": f"V, ({units})",
                            "title": f"UV Coverage\nObs. code: {obj.get_observation_code()}"}
                )

            data = obj.get_calculated_data_by_key(store_key)
            times_data = obj.get_calculated_data_by_key(times_key)
            
            if not isinstance(data, pd.DataFrame) or not isinstance(times_data, pd.DataFrame):
                logger.debug(f"Invalid data format for UV coverage, returning empty plot")
                return self._create_empty_plot(
                    fig, "uv_coverage", obj.get_observation_code(),
                    labels={"xlabel": f"U, ({units})", "ylabel": f"V, ({units})",
                            "title": f"UV Coverage\nObs. code: {obj.get_observation_code()}"}
                )

            filtered_data, valid_scans = self._filter_dataframe(data, times_data, source_name, scans, None, time_range)
            
            if filtered_data.empty:
                logger.debug(f"No data after filtering for UV coverage, returning empty plot")
                return self._create_empty_plot(
                    fig, "uv_coverage", obj.get_observation_code(),
                    labels={"xlabel": f"U, ({units})", "ylabel": f"V, ({units})",
                            "title": f"UV Coverage\nObs. code: {obj.get_observation_code()}"}
                )

            ax = self._setup_axes(fig, "uv_coverage", obj.get_observation_code())
            ax.set_xlabel(f"U, ({units})", fontsize=self._style_config['font']['label_size'])
            ax.set_ylabel(f"V, ({units})", fontsize=self._style_config['font']['label_size'])
            ax.set_title(f"UV Coverage\nObs. code: {obj.get_observation_code()}\nSource: {source_name}", 
                        fontsize=self._style_config['font']['title_size'])
            ax.tick_params(axis='both', labelsize=self._style_config['font']['tick_size'])

            freq_list = [float(f) for f in frequencies if isinstance(f, (int, float)) and f > 0]
            if not freq_list:
                logger.debug("No valid frequencies provided, returning empty plot")
                return self._create_empty_plot(
                    fig, "uv_coverage", obj.get_observation_code(),
                    labels={"xlabel": f"U, ({units})", "ylabel": f"V, ({units})",
                            "title": f"UV Coverage\nObs. code: {obj.get_observation_code()}"}
                )

            ref_freq = min(freq_list)
            ref_wavelength = self.SPEED_OF_LIGHT / (ref_freq * 1e6)
            logger.debug(f"Reference frequency: {ref_freq:.2f} MHz, wavelength: {ref_wavelength:.2e} m")

            result = {"scans": len(valid_scans), "baselines": 0, "points": 0, "frequencies": len(freq_list)}
            plotted_pairs = set()
            legend_handles = []
            legend_labels = []

            grouped_data = filtered_data.groupby("baseline")
            baseline_list = [b for b in baselines if b in grouped_data.groups]

            for pair_idx, pair in enumerate(baseline_list):
                pair_data = grouped_data.get_group(pair)
                u = pair_data["u"].astype(float)
                v = pair_data["v"].astype(float)
                valid_mask = (~u.isna()) & (~v.isna())
                u_valid = u[valid_mask]
                v_valid = v[valid_mask]
                
                if u_valid.empty:
                    logger.debug(f"No valid data for baseline {pair}, skipping")
                    continue

                for freq_idx, freq_mhz in enumerate(freq_list):
                    wavelength = self.SPEED_OF_LIGHT / (freq_mhz * 1e6)
                    u_scaled = u_valid / wavelength if units == "wavelengths" else u_valid / self.EARTH_DIAMETER
                    v_scaled = v_valid / wavelength if units == "wavelengths" else v_valid / self.EARTH_DIAMETER
                    
                    max_uv = max(np.max(np.abs(u_scaled)), np.max(np.abs(v_scaled)))
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
                    else:
                        prefix, scale = "xED", 1.0

                    ax.set_xlabel(f"U, ({prefix})", fontsize=self._style_config['font']['label_size'])
                    ax.set_ylabel(f"V, ({prefix})", fontsize=self._style_config['font']['label_size'])
                    
                    color = self._style_config['colors'][pair_idx % len(self._style_config['colors'])]
                    handle = ax.scatter(
                        u_scaled / scale, v_scaled / scale,
                        s=self._style_config['markers']['scatter_size'],
                        c=[color],
                        label=f"{pair} ({freq_mhz:.2f} MHz)",
                        alpha=0.7,
                        marker=self._style_config['markers']['track_style']
                    )
                    legend_handles.append(handle)
                    legend_labels.append((freq_mhz, pair))
                    plotted_pairs.add(f"{pair}_{freq_mhz}")
                    result["points"] += len(u_scaled)

            if not plotted_pairs:
                logger.debug("No valid data plotted, returning empty plot")
                return self._create_empty_plot(
                    fig, "uv_coverage", obj.get_observation_code(),
                    labels={"xlabel": f"U, ({units})", "ylabel": f"V, ({units})",
                            "title": f"UV Coverage\nObs. code: {obj.get_observation_code()}"}
                )

            if legend_handles:
                grouped_legend = {}
                for handle, (freq_mhz, baseline) in zip(legend_handles, legend_labels):
                    freq_key = f"{freq_mhz:.2f} MHz"
                    if freq_key not in grouped_legend:
                        grouped_legend[freq_key] = []
                    grouped_legend[freq_key].append((handle, baseline))

                legend_lines = []
                legend_texts = []
                for freq in sorted(grouped_legend.keys()):
                    legend_lines.append(Line2D([0], [0], linestyle="none", marker="none"))
                    legend_texts.append(f"{freq}")
                    for handle, baseline in sorted(grouped_legend[freq], key=lambda x: x[1]):
                        legend_lines.append(handle)
                        legend_texts.append(f"    {baseline}")

                fig.subplots_adjust(left=0.10, bottom=0.10, right=0.85, top=0.90)
                fig.legend(
                    legend_lines, legend_texts,
                    loc=self._style_config['legend']['loc'], 
                    bbox_to_anchor=self._style_config['legend']['bbox_to_anchor'],
                    fontsize=self._style_config['legend']['fontsize'],
                    title="Baselines:",
                    title_fontsize=self._style_config['legend']['title_fontsize']
                )

            result["baselines"] = len(plotted_pairs)
            return result

    def _plot_sun_angles(self, obj: Observation, attributes: Dict[str, Any], fig: Figure) -> Dict[str, Any]:
        """Plot angles to the Sun for an Observation with flexible filtering."""
        logger.debug(f"Plotting sun angles for {obj.get_observation_code()}")
        source_name = attributes.get("source_name", None)
        telescopes = attributes.get("telescopes", None)

        if not source_name or not telescopes:
            logger.debug(f"Missing required filters: source_name={source_name}, telescopes={telescopes}, returning empty plot")
            return self._create_empty_plot(
                fig, "sun_angles", obj.get_observation_code(),
                labels={"xlabel": "Time, (MJD)", "ylabel": "a, (deg.)",
                        "title": f"Sun Angles\nObs. code: {obj.get_observation_code()}"}
                )

        return self._plot_time_series(
            obj, attributes, fig, "sun_angles", 
            data_key=attributes.get("store_key", "sun_angles"),
            times_key=attributes.get("times_key", "times"),
            y_label="a, (deg.)",
            value_extractors=[lambda x: x],
            labels=["Angle"]
        )

    def _plot_az_el(self, obj: Observation, attributes: Dict[str, Any], fig: Figure) -> Dict[str, Any]:
        """
        Plot Azimuth/Elevation or Hour Angle/Declination for an Observation with one subplot per telescope.

        Args:
            obj: Observation object to visualize.
            attributes: Dictionary with visualization parameters (coord_type, source_name, telescopes, etc.).
            fig: Matplotlib Figure object for plotting.

        Returns:
            Dict[str, Any]: Dictionary with visualization results.
        """
        logger.debug(f"Plotting az_el for {obj.get_observation_code()}")
        source_name = attributes.get("source_name", None)
        telescopes = attributes.get("telescopes", None)

        if not source_name or not telescopes:
            logger.debug(f"Missing required filters: source_name={source_name}, telescopes={telescopes}, returning empty plot")
            return self._create_empty_plot(
                fig, "az_el", obj.get_observation_code(),
                labels={"xlabel": "Time, (MJD)", "ylabel": f"{attributes.get('coord_type', 'AzEl')}, (deg)",
                        "title": f"Az/El or Ha/Dec\nObs. code: {obj.get_observation_code()}"}
                )

        coord_type = attributes.get("coord_type", "AzEl")
        if coord_type not in ["AzEl", "HADec"]:
            logger.warning(f"Invalid coord_type '{coord_type}', defaulting to 'AzEl'")
            coord_type = "AzEl"

        return self._plot_time_series(
            obj, attributes, fig, "az_el",
            data_key=attributes.get("store_key", "az_el"),
            times_key=attributes.get("times_key", "times"),
            y_label=f"{coord_type[:2]}/{coord_type[2:]}, (deg)",
            value_extractors=[lambda x: x[0], lambda x: x[1]],
            labels=[f"{coord_type[:2]}", f"{coord_type[2:]}"]
            )

    def _plot_time_on_source(self, obj: Observation, attributes: Dict[str, Any], fig: Figure) -> Dict[str, Any]:
        """
        Plot time on source for an Observation with flexible filtering.

        Args:
            obj: Observation object to visualize.
            attributes: Dictionary with visualization parameters (source_name, telescopes, scans, time_range).
            fig: Matplotlib Figure object for plotting.

        Returns:
            Dict[str, Any]: Dictionary with visualization results (scans, telescopes, points).
        """
        with self._lock:
            logger.debug(f"Plotting time on source for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "time_on_source")
            times_key = attributes.get("times_key", "times")
            source_name = attributes.get("source_name")
            telescopes = attributes.get("telescopes")
            scans = attributes.get("scans")
            time_range = attributes.get("time_range")

            if not self._check_filters(attributes, ["source_name", "telescopes", "scans"]):
                logger.debug(f"No filters specified for time_on_source, returning empty plot")
                return self._create_empty_plot(
                    fig, "time_on_source", obj.get_observation_code(),
                    labels={"xlabel": "Time (ISOT)", "ylabel": "Duration, (s)",
                            "title": f"Time on Source\nObs. code: {obj.get_observation_code()}"}
                )

            data = obj.get_calculated_data_by_key(store_key)
            times_data = obj.get_calculated_data_by_key(times_key)
            
            if not isinstance(data, pd.DataFrame) or not isinstance(times_data, pd.DataFrame):
                logger.debug(f"Invalid data format for time_on_source, returning empty plot")
                return self._create_empty_plot(
                    fig, "time_on_source", obj.get_observation_code(),
                    labels={"xlabel": "Time (ISOT)", "ylabel": "Duration, (s)",
                            "title": f"Time on Source\nObs. code: {obj.get_observation_code()}"}
                )

            filtered_data, valid_scans = self._filter_dataframe(data, times_data, source_name, scans, telescopes, time_range)
            
            if filtered_data.empty:
                logger.debug(f"No data after filtering for time_on_source, returning empty plot")
                return self._create_empty_plot(
                    fig, "time_on_source", obj.get_observation_code(),
                    labels={"xlabel": "Time (ISOT)", "ylabel": "Duration, (s)",
                            "title": f"Time on Source\nObs. code: {obj.get_observation_code()}"}
                )

            ax = self._setup_axes(fig, "time_on_source", obj.get_observation_code())
            ax.set_xlabel("Time (ISOT)", fontsize=self._style_config['font']['label_size'])
            ax.set_ylabel("Duration, (s)", fontsize=self._style_config['font']['label_size'])
            ax.set_title(f"Time on Source\nObs. code: {obj.get_observation_code()}\nSource: {source_name}", 
                        fontsize=self._style_config['font']['title_size'])
            ax.tick_params(axis='both', labelsize=self._style_config['font']['tick_size'])

            result = {"scans": len(valid_scans), "telescopes": 0, "points": 0}
            plotted_telescopes = set()
            legend_handles = []
            legend_labels = []

            grouped_data = filtered_data.groupby("telescope_code")
            tel_list = telescopes if telescopes else filtered_data["telescope_code"].unique()

            for tel_idx, tel in enumerate(tel_list):
                if tel not in grouped_data.groups:
                    continue
                tel_data = grouped_data.get_group(tel)
                times = tel_data["start"].apply(lambda x: x.isot if isinstance(x, Time) else x)
                durations = tel_data["duration"].astype(float)
                valid_mask = (~times.isna()) & (~durations.isna())
                valid_times = times[valid_mask]
                valid_durations = durations[valid_mask]
                
                if valid_times.empty:
                    continue

                color = self._style_config['colors'][tel_idx % len(self._style_config['colors'])]
                handle = ax.bar(
                    valid_times, valid_durations,
                    label=tel,
                    color=color,
                    alpha=0.7
                )
                legend_handles.append(handle)
                legend_labels.append(tel)
                plotted_telescopes.add(tel)
                result["points"] += len(valid_durations)

            result["telescopes"] = len(plotted_telescopes)
            if plotted_telescopes:
                fig.subplots_adjust(left=0.10, bottom=0.10, right=0.88, top=0.90)
                fig.legend(
                    legend_handles, legend_labels,
                    loc=self._style_config['legend']['loc'],
                    bbox_to_anchor=self._style_config['legend']['bbox_to_anchor'],
                    fontsize=self._style_config['legend']['fontsize'],
                    title="Telescopes:",
                    title_fontsize=self._style_config['legend']['title_fontsize']
                )

            if not plotted_telescopes:
                logger.debug("No valid data plotted, returning empty plot")
                return self._create_empty_plot(
                    fig, "time_on_source", obj.get_observation_code(),
                    labels={"xlabel": "Time (ISOT)", "ylabel": "Duration, (s)",
                            "title": f"Time on Source\nObs. code: {obj.get_observation_code()}"}
                )

            return result

    def _plot_beam_pattern(self, obj: Observation, attributes: Dict[str, Any], fig: Figure) -> Dict[str, Any]:
        """
        Plot beam pattern for an Observation with flexible filtering and grouped legend.

        Args:
            obj: Observation object to visualize.
            attributes: Dictionary with visualization parameters (telescopes, freq_names).
            fig: Matplotlib Figure object for plotting.

        Returns:
            Dict[str, Any]: Dictionary with visualization results (telescopes, frequencies).
        """
        with self._lock:
            logger.debug(f"Plotting beam pattern for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "beam_pattern")
            telescopes = attributes.get("telescopes", [])
            freq_names = attributes.get("freq_names", [])

            if not self._check_filters(attributes, ["telescopes", "freq_names"]):
                logger.debug(f"No filters specified for beam_pattern, returning empty plot")
                return self._create_empty_plot(
                    fig, "beam_pattern", obj.get_observation_code(),
                    labels={"xlabel": "Theta, (rad.)", "ylabel": "Normalized Peak Flux",
                            "title": f"Beam Pattern\nObs. code: {obj.get_observation_code()}"}
                )

            beam_data = obj.get_calculated_data_by_key(store_key)
            if not isinstance(beam_data, pd.DataFrame):
                logger.debug("Invalid beam data format, returning empty plot")
                return self._create_empty_plot(
                    fig, "beam_pattern", obj.get_observation_code(),
                    labels={"xlabel": "Theta, (rad.)", "ylabel": "Normalized Peak Flux",
                            "title": f"Beam Pattern\nObs. code: {obj.get_observation_code()}"}
                )

            filtered_data = beam_data[beam_data["telescope_code"].isin(telescopes)] if telescopes else beam_data
            if filtered_data.empty:
                logger.debug("No data after filtering telescopes, returning empty plot")
                return self._create_empty_plot(
                    fig, "beam_pattern", obj.get_observation_code(),
                    labels={"xlabel": "Theta, (rad.)", "ylabel": "Normalized Peak Flux",
                            "title": f"Beam Pattern\nObs. code: {obj.get_observation_code()}"}
                )

            freq_list = [float(f) for f in freq_names if isinstance(f, (int, float)) and f > 0]
            if not freq_list:
                logger.debug("No valid frequencies provided, returning empty plot")
                return self._create_empty_plot(
                    fig, "beam_pattern", obj.get_observation_code(),
                    labels={"xlabel": "Theta, (rad.)", "ylabel": "Normalized Peak Flux",
                            "title": f"Beam Pattern\nObs. code: {obj.get_observation_code()}"}
                )

            ref_freq = min(freq_list)
            ref_wavelength = self.SPEED_OF_LIGHT / (ref_freq * 1e6)
            logger.debug(f"Reference frequency: {ref_freq:.2f} MHz, wavelength: {ref_wavelength:.2e} m")

            n_tels = len(telescopes) if telescopes else filtered_data["telescope_code"].nunique()
            n_cols = int(np.ceil(np.sqrt(n_tels)))
            n_rows = int(np.ceil(n_tels / n_cols))
            axes = self._setup_axes(fig, "beam_pattern", obj.get_observation_code(), n_rows=n_rows, n_cols=n_cols, sharex=True, sharey=True)
            axes = np.atleast_1d(axes)

            norm = plt.Normalize(min(freq_list), max(freq_list)) if freq_list else None
            cmap = self._style_config['colormaps']['redpurple'] if freq_list else None

            result = {"telescopes": 0, "frequencies": len(freq_list)}
            plotted_telescopes = set()
            legend_handles = []
            legend_labels = []

            grouped_data = filtered_data.groupby("telescope_code")
            tel_list = telescopes if telescopes else filtered_data["telescope_code"].unique()

            for tel_idx, tel_code in enumerate(tel_list):
                if tel_code not in grouped_data.groups:
                    continue
                ax = axes[tel_idx] if tel_idx < len(axes) else axes[-1]
                ax.set_title(tel_code, fontsize=self._style_config['font']['title_size'])
                ax.tick_params(axis='both', labelsize=self._style_config['font']['tick_size'])

                tel_data = grouped_data.get_group(tel_code)
                theta = tel_data["theta"].astype(float)
                pattern = tel_data["pattern"].astype(float)
                valid_mask = (~theta.isna()) & (~pattern.isna())
                theta = theta[valid_mask]
                pattern = pattern[valid_mask]
                
                if theta.empty:
                    logger.warning(f"No valid beam data for {tel_code}")
                    continue

                for freq_idx, freq_mhz in enumerate(freq_list):
                    wavelength = self.SPEED_OF_LIGHT / (freq_mhz * 1e6)
                    if wavelength <= 0:
                        logger.warning(f"Invalid frequency {freq_mhz} MHz for {tel_code}")
                        continue
                    theta_scaling_factor = ref_wavelength / wavelength
                    scaled_theta = theta * theta_scaling_factor
                    scaled_pattern = pattern / np.max(np.abs(pattern)) if np.max(np.abs(pattern)) > 0 else pattern
                    color = cmap(norm(freq_mhz)) if cmap else self._style_config['colors'][freq_idx % len(self._style_config['colors'])]
                    line, = ax.plot(
                        scaled_theta, scaled_pattern,
                        color=color,
                        linestyle=self._style_config['linestyles']['default'],
                        label=f"{freq_mhz:.2f} MHz"
                    )
                    if f"{freq_mhz:.2f} MHz" not in legend_labels:
                        legend_handles.append(line)
                        legend_labels.append(f"{freq_mhz:.2f} MHz")
                    theta_range = np.max(np.abs(scaled_theta)) * 1.1 if len(scaled_theta) > 0 else 1.0
                    ax.set_xlim(-theta_range, theta_range)
                    result["frequencies"] = len(set(legend_labels))

                plotted_telescopes.add(tel_code)

            for ax in axes:
                ax.set_xlabel("")
                ax.set_ylabel("")
            if plotted_telescopes:
                fig.text(0.5, 0.04, "Theta, (rad.)", ha='center', fontsize=self._style_config['font']['label_size'])
                fig.text(0.04, 0.5, "Normalized Peak Flux", va='center', rotation='vertical', fontsize=self._style_config['font']['label_size'])

            fig.subplots_adjust(left=0.10, bottom=0.10, right=0.86, top=0.85)
            if legend_handles:
                fig.legend(
                    legend_handles, legend_labels,
                    loc=self._style_config['legend']['loc'], 
                    bbox_to_anchor=(0.87, 0.99),
                    fontsize=self._style_config['legend']['fontsize'],
                    title="Frequencies:",
                    title_fontsize=self._style_config['legend']['title_fontsize'],
                    bbox_transform=fig.transFigure
                )

            for idx in range(len(tel_list), len(axes)):
                axes[idx].set_visible(False)

            if not plotted_telescopes:
                logger.debug("No valid data plotted, returning empty plot")
                return self._create_empty_plot(
                    fig, "beam_pattern", obj.get_observation_code(),
                    labels={"xlabel": "Theta, (rad.)", "ylabel": "Normalized Peak Flux",
                            "title": f"Beam Pattern\nObs. code: {obj.get_observation_code()}"}
                )

            result["telescopes"] = len(plotted_telescopes)
            fig.suptitle(f"Beam Pattern\nObs. code: {obj.get_observation_code()}", fontsize=self._style_config['font']['title_size'])
            return result

    def _plot_baseline_projections(self, obj: Observation, attributes: Dict[str, Any], fig: Figure) -> Dict[str, Any]:
        """
        Plot baseline projections for an Observation with flexible filtering, frequency scaling, and grouped legend.

        Args:
            obj: Observation object to visualize.
            attributes: Dictionary with visualization parameters (store_key, times_key, baselines, source_name, scans, time_range, frequencies, units).
            fig: Matplotlib Figure object for plotting.

        Returns:
            Dict[str, Any]: Dictionary with visualization results (scans, baselines, projections, frequencies).
        """
        with self._lock:
            logger.debug(f"Plotting baseline projections for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "baseline_projections")
            times_key = attributes.get("times_key", "times")
            baselines = attributes.get("baselines", [])
            source_name = attributes.get("source_name")
            scans = attributes.get("scans")
            time_range = attributes.get("time_range")
            frequencies = attributes.get("frequencies", [])
            units = attributes.get("units", "wavelengths")

            if not self._check_filters(attributes, ["source_name", "baselines", "scans", "frequencies"]):
                logger.debug(f"No filters specified for baseline_projections, returning empty plot")
                return self._create_empty_plot(
                    fig, "baseline_projections", obj.get_observation_code(),
                    labels={"xlabel": "Time (ISOT)", "ylabel": f"Baseline Length, ({units})",
                            "title": f"Baseline Projections\nObs. code: {obj.get_observation_code()}"}
                )

            data = obj.get_calculated_data_by_key(store_key)
            times_data = obj.get_calculated_data_by_key(times_key)
            
            if not isinstance(data, pd.DataFrame) or not isinstance(times_data, pd.DataFrame):
                logger.debug(f"Invalid data format for baseline_projections, returning empty plot")
                return self._create_empty_plot(
                    fig, "baseline_projections", obj.get_observation_code(),
                    labels={"xlabel": "Time (ISOT)", "ylabel": f"Baseline Length, ({units})",
                            "title": f"Baseline Projections\nObs. code: {obj.get_observation_code()}"}
                )

            filtered_data, valid_scans = self._filter_dataframe(data, times_data, source_name, scans, None, time_range)
            
            if filtered_data.empty:
                logger.debug(f"No data after filtering for baseline_projections, returning empty plot")
                return self._create_empty_plot(
                    fig, "baseline_projections", obj.get_observation_code(),
                    labels={"xlabel": "Time (ISOT)", "ylabel": f"Baseline Length, ({units})",
                            "title": f"Baseline Projections\nObs. code: {obj.get_observation_code()}"}
                )

            ax = self._setup_axes(fig, "baseline_projections", obj.get_observation_code())
            ax.set_xlabel("Time (ISOT)", fontsize=self._style_config['font']['label_size'])
            ax.set_ylabel(f"Baseline Length, ({units})", fontsize=self._style_config['font']['label_size'])
            ax.set_title(f"Baseline Projections\nObs. code: {obj.get_observation_code()}\nSource: {source_name}", 
                        fontsize=self._style_config['font']['title_size'])
            ax.tick_params(axis='both', labelsize=self._style_config['font']['tick_size'])

            freq_list = [float(f) for f in frequencies if isinstance(f, (int, float)) and f > 0]
            if not freq_list:
                logger.debug("No valid frequencies provided, returning empty plot")
                return self._create_empty_plot(
                    fig, "baseline_projections", obj.get_observation_code(),
                    labels={"xlabel": "Time (ISOT)", "ylabel": f"Baseline Length, ({units})",
                            "title": f"Baseline Projections\nObs. code: {obj.get_observation_code()}"}
                )

            ref_freq = min(freq_list)
            ref_wavelength = self.SPEED_OF_LIGHT / (ref_freq * 1e6)
            logger.debug(f"Reference frequency: {ref_freq:.2f} MHz, wavelength: {ref_wavelength:.2e} m")

            result = {"scans": len(valid_scans), "baselines": 0, "projections": 0, "frequencies": len(freq_list)}
            plotted_pairs = set()
            legend_handles = []
            legend_labels = []

            grouped_data = filtered_data.groupby("baseline")
            baseline_list = [b for b in baselines if b in grouped_data.groups]

            for pair_idx, pair in enumerate(baseline_list):
                pair_data = grouped_data.get_group(pair)
                times = pair_data["time"].apply(lambda x: x.isot if isinstance(x, Time) else x)
                projections = pair_data["projection"].astype(float)
                valid_mask = (~times.isna()) & (~projections.isna())
                valid_times = times[valid_mask]
                valid_projections = projections[valid_mask]
                
                if valid_times.empty:
                    logger.debug(f"No valid data for baseline {pair}, skipping")
                    continue

                for freq_idx, freq_mhz in enumerate(freq_list):
                    wavelength = self.SPEED_OF_LIGHT / (freq_mhz * 1e6)
                    bl_scaled = valid_projections / wavelength if units == "wavelengths" else valid_projections / self.EARTH_DIAMETER
                    max_bl = np.max(np.abs(bl_scaled)) if not bl_scaled.empty else 0.0
                    
                    if units == "wavelengths":
                        if max_bl >= 1e12:
                            prefix, scale = "Tλ", 1e12
                        elif max_bl >= 1e9:
                            prefix, scale = "Gλ", 1e9
                        elif max_bl >= 1e6:
                            prefix, scale = "Mλ", 1e6
                        elif max_bl >= 1e3:
                            prefix, scale = "kλ", 1e3
                        else:
                            prefix, scale = "λ", 1.0
                    else:
                        prefix, scale = "xED", 1.0

                    ax.set_ylabel(f"Baseline Length, ({prefix})", fontsize=self._style_config['font']['label_size'])
                    color = self._style_config['colors'][pair_idx % len(self._style_config['colors'])]
                    handle = ax.scatter(
                        valid_times, bl_scaled / scale,
                        s=self._style_config['markers']['scatter_size'],
                        c=[color],
                        label=f"{pair} ({freq_mhz:.2f} MHz)",
                        alpha=0.7,
                        marker=self._style_config['markers']['track_style']
                    )
                    legend_handles.append(handle)
                    legend_labels.append((freq_mhz, pair))
                    plotted_pairs.add(f"{pair}_{freq_mhz}")
                    result["projections"] += len(bl_scaled)

            if not plotted_pairs:
                logger.debug("No valid data plotted, returning empty plot")
                return self._create_empty_plot(
                    fig, "baseline_projections", obj.get_observation_code(),
                    labels={"xlabel": "Time (ISOT)", "ylabel": f"Baseline Length, ({units})",
                            "title": f"Baseline Projections\nObs. code: {obj.get_observation_code()}"}
                )

            if legend_handles:
                grouped_legend = {}
                for handle, (freq_mhz, baseline) in zip(legend_handles, legend_labels):
                    freq_key = f"{freq_mhz:.2f} MHz"
                    if freq_key not in grouped_legend:
                        grouped_legend[freq_key] = []
                    grouped_legend[freq_key].append((handle, baseline))

                legend_lines = []
                legend_texts = []
                for freq in sorted(grouped_legend.keys()):
                    legend_lines.append(Line2D([0], [0], linestyle="none", marker="none"))
                    legend_texts.append(f"{freq}")
                    for handle, baseline in sorted(grouped_legend[freq], key=lambda x: x[1]):
                        legend_lines.append(handle)
                        legend_texts.append(f"    {baseline}")

                fig.subplots_adjust(left=0.10, bottom=0.10, right=0.85, top=0.90)
                fig.legend(
                    legend_lines, legend_texts,
                    loc=self._style_config['legend']['loc'], 
                    bbox_to_anchor=self._style_config['legend']['bbox_to_anchor'],
                    fontsize=self._style_config['legend']['fontsize'],
                    title="Baselines:",
                    title_fontsize=self._style_config['legend']['title_fontsize']
                )

            result["baselines"] = len(plotted_pairs)
            return result

    def _plot_mollweide_tracks(self, obj: Observation, attributes: Dict[str, Any], fig: Figure) -> Dict[str, Any]:
        """
        Plot Mollweide tracks for an Observation with flexible filtering and grouped legend.

        Args:
            obj: Observation object to visualize.
            attributes: Dictionary with visualization parameters (telescopes, scans, sources, max_points).
            fig: Matplotlib Figure object for plotting.

        Returns:
            Dict[str, Any]: Dictionary with visualization results (scans, telescopes, sources, points).
        """
        with self._lock:
            logger.debug(f"Plotting Mollweide tracks for {obj.get_observation_code()}")
            store_key = attributes.get("store_key", "mollweide_tracks")
            telescopes = attributes.get("telescopes", [])
            scans = attributes.get("scans", [])
            sources = attributes.get("sources", [])
            max_points = attributes.get("max_points", 10000)

            ax = self._setup_axes(fig, "mollweide_tracks", obj.get_observation_code(), projection="mollweide")
            ax.set_title(f"Mollweide Tracks\nObs. code: {obj.get_observation_code()}", fontsize=self._style_config['font']['title_size'])
            ax.tick_params(axis='both', labelsize=self._style_config['font']['tick_size'])

            data = obj.get_calculated_data_by_key(store_key)
            if not isinstance(data, pd.DataFrame):
                logger.warning(f"No valid Mollweide track data found for '{store_key}'")
                return self._create_empty_plot(
                    fig, "mollweide_tracks", obj.get_observation_code(),
                    projection="mollweide",
                    labels={"title": f"Mollweide Tracks\nObs. code: {obj.get_observation_code()}"}
                )

            filtered_data = data
            if telescopes:
                filtered_data = filtered_data[filtered_data["telescope_code"].isin(telescopes)]
            if scans:
                filtered_data = filtered_data[filtered_data["scan_name"].isin(scans)]
            
            if filtered_data.empty:
                logger.debug("No data after filtering, returning empty plot")
                return self._create_empty_plot(
                    fig, "mollweide_tracks", obj.get_observation_code(),
                    projection="mollweide",
                    labels={"title": f"Mollweide Tracks\nObs. code: {obj.get_observation_code()}"}
                )

            metadata = obj.get_calculated_data_by_key(store_key).get("metadata", {})
            result = {"scans": len(scans) if scans else filtered_data["scan_name"].nunique(), 
                    "telescopes": 0, "sources": 0, "points": 0}
            plotted_telescopes = set()
            plotted_sources = set()
            legend_handles = []
            legend_labels = []

            source_colors = {}
            if sources and "sources" in metadata:
                for idx, source_name in enumerate(metadata["sources"].keys()):
                    if source_name not in sources:
                        continue
                    coords = metadata["sources"].get(source_name, [])
                    if not isinstance(coords, (list, np.ndarray)) or len(coords) != 2:
                        logger.warning(f"Invalid source coordinates format for {source_name}: {coords}")
                        continue
                    try:
                        lon, lat = float(coords[0]), float(coords[1])
                        lon_rad = np.radians(lon)
                        lat_rad = np.radians(lat)
                        color_idx = idx % len(self._style_config["colors"])
                        color = self._style_config["colors"][color_idx]
                        source_colors[source_name] = color
                        handle = ax.scatter(
                            lon_rad, lat_rad, 
                            c=[color], 
                            marker=self._style_config['markers']['source_style'], 
                            s=self._style_config['markers']['default_size'],
                            label=source_name if source_name not in plotted_sources else None,
                            zorder=3, edgecolors="none"
                        )
                        if source_name not in plotted_sources:
                            legend_handles.append(handle)
                            legend_labels.append(source_name)
                        plotted_sources.add(source_name)
                        result["sources"] += 1
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to plot source {source_name}: {str(e)}")
                        continue

            grouped_data = filtered_data.groupby("telescope_code")
            tel_list = telescopes if telescopes else filtered_data["telescope_code"].unique()
            total_points = len(filtered_data)

            if total_points > max_points:
                logger.warning(f"Total points ({total_points}) exceeds max_points ({max_points}), subsampling tracks")
                subsample_factor = total_points // max_points + 1
            else:
                subsample_factor = 1

            norm = plt.Normalize(0, len(tel_list)) if tel_list else None
            cmap = self._style_config['colormaps']['redpurple'] if tel_list else None

            for tel_idx, tel_code in enumerate(tel_list):
                if tel_code not in grouped_data.groups:
                    continue
                tel_data = grouped_data.get_group(tel_code)
                lon = tel_data["lon"].astype(float)
                lat = tel_data["lat"].astype(float)
                valid_mask = (~lon.isna()) & (~lat.isna())
                lon = lon[valid_mask]
                lat = lat[valid_mask]
                
                if lon.empty:
                    logger.debug(f"No valid points for {tel_code}")
                    continue

                if subsample_factor > 1:
                    lon = lon[::subsample_factor]
                    lat = lat[::subsample_factor]

                lon_rad = np.radians(lon)
                lat_rad = np.radians(lat)
                color = cmap(tel_idx / len(tel_list)) if cmap else self._style_config["colors"][len(plotted_telescopes) % len(self._style_config["colors"])]
                handle = ax.scatter(
                    lon_rad, lat_rad, 
                    s=self._style_config['markers']['track_size'], 
                    c=[color],
                    marker=self._style_config['markers']['track_style'],
                    label=tel_code if tel_code not in plotted_telescopes else None,
                    zorder=1
                )
                if tel_code not in plotted_telescopes:
                    legend_handles.append(handle)
                    legend_labels.append(tel_code)
                plotted_telescopes.add(tel_code)
                result["points"] += len(lon)

            result["telescopes"] = len(plotted_telescopes)

            if legend_handles:
                grouped_legend = {"Sources": [], "Telescopes": []}
                for handle, label in zip(legend_handles, legend_labels):
                    if label in plotted_sources:
                        grouped_legend["Sources"].append((handle, label))
                    else:
                        grouped_legend["Telescopes"].append((handle, label))

                legend_lines = []
                legend_texts = []
                for group, items in [("Sources:", sorted(grouped_legend["Sources"], key=lambda x: x[1])),
                                    ("Telescopes:", sorted(grouped_legend["Telescopes"], key=lambda x: x[1]))]:
                    if items:
                        legend_lines.append(Line2D([0], [0], linestyle="none", marker="none"))
                        legend_texts.append(group)
                        for handle, label in items:
                            legend_lines.append(handle)
                            legend_texts.append(f"    {label}")

                fig.subplots_adjust(left=0.10, bottom=0.10, right=0.85, top=0.90)
                fig.legend(
                    legend_lines, legend_texts,
                    loc=self._style_config['legend']['loc'], 
                    bbox_to_anchor=self._style_config['legend']['bbox_to_anchor'],
                    fontsize=self._style_config['legend']['fontsize'],
                    title="",
                    title_fontsize=self._style_config['legend']['title_fontsize'],
                    bbox_transform=fig.transFigure
                )

            if not plotted_telescopes and not plotted_sources:
                logger.debug("No valid data plotted, returning empty plot")
                return self._create_empty_plot(
                    fig, "mollweide_tracks", obj.get_observation_code(),
                    projection="mollweide",
                    labels={"title": f"Mollweide Tracks\nObs. code: {obj.get_observation_code()}"}
                )

            return result