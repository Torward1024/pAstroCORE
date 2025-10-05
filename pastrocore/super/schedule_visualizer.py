# pastrocore/super/schedule_visualizer.py
from common.super.super import Super
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.observation import Observation
from pastrocore.base.telescopes import Telescope, SpaceTelescope, Telescopes
from pastrocore.base.sources import Source, Sources
from pastrocore.base.scans import Scan, Scans
from pastrocore.base.frequencies import IF, Frequencies
from common.utils.logging_setup import logger
from typing import Dict, Any, Callable, Union, List
from concurrent.futures import ThreadPoolExecutor

import threading
import os
import warnings

import gc

import numpy as np
import polars as pl
from astropy.time import Time


import matplotlib
import matplotlib.ticker
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D

from erfa import ErfaWarning
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
            },
            'lines': {
                'width': 2
            }
        }

        self._apply_style_config()

        self._object_visualizers: Dict[type, Callable] = {
            (ScheduleProject, Observation): self._visualize_project_or_observation
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
        
        logger.debug("Initialized Scheduling Visualizer")

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
    
    def _check_filters(self, attributes: Dict[str, Any], required_filters: List[str]) -> bool:
        """Check if any of the required filters are provided."""
        return any(attributes.get(key) for key in required_filters)
    
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
                    gc.collect()
            except Exception as e:
                logger.error(f"Failed to save visualization to {output_file}: {str(e)}")
                result["status"] = False
                result["message"] = f"Failed to save visualization: {str(e)}"
        
        return result

    def _plot_uv_coverage(self, obj: Observation, attributes: Dict[str, Any], fig: Figure) -> Dict[str, Any]:
        """
        Plot UV coverage for an Observation with flexible filtering and frequency scaling using Polars DataFrame.

        Args:
            obj: Observation object to visualize.
            attributes: Dictionary with visualization parameters (source_name, baselines, scans, frequencies, units).
            fig: Matplotlib Figure object for plotting.

        Returns:
            Dict[str, Any]: Dictionary with visualization results (baselines, points, frequencies).
        """
        with self._lock:
            logger.debug(f"Plotting UV coverage for {obj.get_observation_code()} with attributes: {attributes}")
            store_key = attributes.get("store_key", "uv_coverage")
            baselines = attributes.get("baselines", [])
            source_name = attributes.get("source_name", None)
            scans = attributes.get("scans", [])
            frequencies = attributes.get("frequencies", [])
            units = attributes.get("units", "wavelengths")

            if not self._check_filters(attributes, ["source_name", "baselines", "scans", "frequencies"]):
                logger.debug(f"Missing required filters: source_name={source_name}, baselines={baselines}, "
                             f"scans={scans}, frequencies={frequencies}, returning empty plot")
                return self._create_empty_plot(
                    fig, "uv_coverage", obj.get_observation_code(),
                    labels={"xlabel": "u, (wavelengths)", "ylabel": "v, (wavelengths)",
                            "title": f"(u,v) coverage\nObs. code: {obj.get_observation_code()}"}
                )

            uv_data = obj.get_calculated_data_by_key(store_key)
            if uv_data is None or uv_data.is_empty():
                logger.debug("No UV data available, returning empty plot")
                return self._create_empty_plot(
                    fig, "uv_coverage", obj.get_observation_code(),
                    labels={"xlabel": "u, (wavelengths)", "ylabel": "v, (wavelengths)",
                            "title": f"(u,v) coverage\nObs. code: {obj.get_observation_code()}"}
                )

            filtered_df = uv_data
            if source_name:
                filtered_df = filtered_df.filter(pl.col("source_name") == source_name)
            if baselines:
                filtered_df = filtered_df.filter(pl.col("baseline").is_in(baselines))
            if scans:
                filtered_df = filtered_df.filter(pl.col("scan_name").is_in(scans))

            if filtered_df.is_empty():
                logger.debug("No data after filtering, returning empty plot")
                return self._create_empty_plot(
                    fig, "uv_coverage", obj.get_observation_code(),
                    labels={"xlabel": "u, (wavelengths)", "ylabel": "v, (wavelengths)",
                            "title": f"(u,v) coverage\nObs. code: {obj.get_observation_code()}"}
                )

            freq_list = [float(f) for f in frequencies if isinstance(f, (int, float)) and f > 0]
            if not freq_list:
                logger.debug("No valid frequencies provided, returning empty plot")
                return self._create_empty_plot(
                    fig, "uv_coverage", obj.get_observation_code(),
                    labels={"xlabel": "u, (wavelengths)", "ylabel": "v, (wavelengths)",
                            "title": f"(u,v) coverage\nObs. code: {obj.get_observation_code()}"}
                )

            ax = self._setup_axes(fig, "uv_coverage", obj.get_observation_code())
            ax.tick_params(axis='both', labelsize=self._style_config['font']['tick_size'])

            ref_freq = min(freq_list)
            ref_wavelength = self.SPEED_OF_LIGHT / (ref_freq * 1e6)
            logger.debug(f"Reference frequency: {ref_freq:.2f} MHz, reference wavelength: {ref_wavelength:.2e} m")

            result = {"baselines": 0, "points": 0, "frequencies": len(freq_list)}
            plotted_pairs = set()
            legend_handles = []
            legend_labels = []
            max_uv = 0.0

            for freq_idx, freq_mhz in enumerate(freq_list):
                wavelength = self.SPEED_OF_LIGHT / (freq_mhz * 1e6)
                for baseline in filtered_df["baseline"].unique():
                    baseline_data = filtered_df.filter(pl.col("baseline") == baseline)
                    if baseline_data.is_empty():
                        continue

                    u = baseline_data["u"].to_numpy()
                    v = baseline_data["v"].to_numpy()

                    if units == "wavelengths":
                        u_scaled = u / wavelength
                        v_scaled = v / wavelength
                    else:
                        u_scaled = (u / wavelength) / (self.EARTH_DIAMETER / ref_wavelength)
                        v_scaled = (v / wavelength) / (self.EARTH_DIAMETER / ref_wavelength)

                    max_uv = max(max_uv, np.max(np.abs(u_scaled)), np.max(np.abs(v_scaled)))

                    color_idx = (filtered_df["baseline"].unique().to_list().index(baseline)) % len(self._style_config["colors"])
                    color = self._style_config["colors"][color_idx]
                    label = f"{baseline} ({freq_mhz:.2f} MHz)"
                    handle = ax.scatter(
                        u_scaled, v_scaled,
                        s=self._style_config["markers"]["scatter_size"],
                        c=[color],
                        label=label,
                        marker=self._style_config["markers"]["track_style"]
                    )
                    ax.scatter(
                        -u_scaled, -v_scaled,
                        s=self._style_config["markers"]["scatter_size"],
                        c=[color],
                        marker=self._style_config["markers"]["track_style"]
                    )
                    legend_handles.append(handle)
                    legend_labels.append((freq_mhz, baseline))
                    plotted_pairs.add(f"{baseline}_{freq_mhz}")
                    result["points"] += len(u_scaled)

            if not plotted_pairs:
                logger.debug("No valid data plotted, returning empty result")
                return self._create_empty_plot(
                    fig, "uv_coverage", obj.get_observation_code(),
                    labels={"xlabel": "u, (wavelengths)", "ylabel": "v, (wavelengths)",
                            "title": f"(u,v) coverage\nObs. code: {obj.get_observation_code()}"}
                )

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
                ax.set_xlabel(f"u, ({prefix})", fontsize=self._style_config["font"]["label_size"])
                ax.set_ylabel(f"v, ({prefix})", fontsize=self._style_config["font"]["label_size"])
            else:
                prefix, scale = "xED", 1.0
                ax.set_xlabel("u, (xED)", fontsize=self._style_config["font"]["label_size"])
                ax.set_ylabel("v, (xED)", fontsize=self._style_config["font"]["label_size"])

            max_uv_scaled = max_uv / scale
            if max_uv_scaled > 0:
                ax.set_xlim(-max_uv_scaled * 1.1, max_uv_scaled * 1.1)
                ax.set_ylim(-max_uv_scaled * 1.1, max_uv_scaled * 1.1)

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
                    loc=self._style_config["legend"]["loc"],
                    bbox_to_anchor=self._style_config["legend"]["bbox_to_anchor"],
                    fontsize=self._style_config["legend"]["fontsize"],
                    title="Baselines:",
                    title_fontsize=self._style_config["legend"]["title_fontsize"]
                )

            ax.invert_xaxis()
            ax.set_title(f"(u,v) coverage\nObs. code: {obj.get_observation_code()}\nSource: {source_name}",
                         fontsize=self._style_config["font"]["title_size"])
            fig.subplots_adjust(left=0.10, bottom=0.10, right=0.85, top=0.90)
            result["baselines"] = len(plotted_pairs)
            return result

    def _plot_sun_angles(self, obj: Observation, attributes: Dict[str, Any], fig: Figure) -> Dict[str, Any]:
        """
        Plot angles to the Sun for an Observation with flexible filtering using Polars DataFrame.

        Args:
            obj: Observation object to visualize.
            attributes: Dictionary with visualization parameters (source_name, telescopes, scans, time_range, etc.).
            fig: Matplotlib Figure object for plotting.

        Returns:
            Dict[str, Any]: Dictionary with visualization results (scans, telescopes, points).
        """
        with self._lock:
            logger.debug(f"Plotting sun angles for {obj.get_observation_code()} with attributes: {attributes}")
            store_key = attributes.get("store_key", "sun_angles")
            source_name = attributes.get("source_name", None)
            telescopes = attributes.get("telescopes", [])
            scans = attributes.get("scans", None)
            time_range = attributes.get("time_range", None)

            if not self._check_filters(attributes, ["source_name", "telescopes"]):
                logger.debug(f"Missing required filters: source_name={source_name}, telescopes={telescopes}, "
                             f"returning empty plot")
                return self._create_empty_plot(
                    fig, "sun_angles", obj.get_observation_code(),
                    labels={"xlabel": "Time, (MJD)", "ylabel": "Angle, (deg.)",
                            "title": f"Sun Angles\nObs. code: {obj.get_observation_code()}"}
                )

            data_df = obj.get_calculated_data_by_key(store_key)
            if data_df is None or data_df.is_empty():
                logger.debug("No sun angles data available, returning empty plot")
                return self._create_empty_plot(
                    fig, "sun_angles", obj.get_observation_code(),
                    labels={"xlabel": "Time, (MJD)", "ylabel": "Angle, (deg.)",
                            "title": f"Sun Angles\nObs. code: {obj.get_observation_code()}"}
                )

            filtered_df = data_df
            if source_name:
                filtered_df = filtered_df.filter(pl.col("source_name") == source_name)
            if telescopes:
                filtered_df = filtered_df.filter(pl.col("telescope_code").is_in(telescopes))
            if scans:
                filtered_df = filtered_df.filter(pl.col("scan_name").is_in(scans))
            if time_range:
                start_time, end_time = time_range
                filtered_df = filtered_df.filter(
                    (pl.col("time") >= float(start_time)) & (pl.col("time") <= float(end_time))
                )

            if filtered_df.is_empty():
                logger.debug("No data after filtering, returning empty plot")
                return self._create_empty_plot(
                    fig, "sun_angles", obj.get_observation_code(),
                    labels={"xlabel": "Time, (MJD)", "ylabel": "Angle, (deg.)",
                            "title": f"Sun Angles\nObs. code: {obj.get_observation_code()}"}
                )

            ax = self._setup_axes(fig, "sun_angles", obj.get_observation_code())
            ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{int(x)}"))
            ax.set_xlabel("Time, (MJD)", fontsize=self._style_config["font"]["label_size"])
            ax.set_ylabel("Angle, (deg.)", fontsize=self._style_config["font"]["label_size"])
            ax.set_title(f"Sun Angles\nObs. code: {obj.get_observation_code()}\nSource: {source_name}",
                         fontsize=self._style_config["font"]["title_size"])
            ax.tick_params(axis="both", labelsize=self._style_config["font"]["tick_size"])

            result = {"scans": len(filtered_df["scan_name"].unique()), "telescopes": 0, "points": 0}
            plotted_telescopes = set()
            legend_handles = []
            legend_labels = []

            for tel_idx, tel in enumerate(filtered_df["telescope_code"].unique()):
                if telescopes and tel not in telescopes:
                    continue
                tel_data = filtered_df.filter(pl.col("telescope_code") == tel)
                if tel_data.is_empty():
                    logger.debug(f"No data for telescope {tel}, skipping")
                    continue

                # Sort by time for consistent plotting
                tel_data = tel_data.sort("time")
                times_mjd = tel_data["time"].to_numpy()
                angles = tel_data["angle"].to_numpy()
                valid_mask = ~np.isnan(angles)
                if not np.any(valid_mask):
                    logger.debug(f"All angles for telescope {tel} are NaN, skipping")
                    continue
                valid_times_mjd = times_mjd[valid_mask]
                valid_angles = angles[valid_mask]

                color = self._style_config["colors"][tel_idx % len(self._style_config["colors"])]
                handle = ax.plot(
                    valid_times_mjd, valid_angles,
                    color=color,
                    linestyle=self._style_config.get("lines", {}).get("style", "-"),
                    linewidth=self._style_config.get("lines", {}).get("width", 1.5),
                    label=tel,
                    alpha=0.7
                )[0]
                points_plotted = len(valid_angles)
                logger.debug(f"Plotted {points_plotted} points for telescope {tel}")

                if points_plotted > 0:
                    legend_handles.append(handle)
                    legend_labels.append(tel)
                    plotted_telescopes.add(tel)
                    result["points"] += points_plotted

            if not plotted_telescopes:
                logger.debug("No valid data plotted, returning empty result")
                return self._create_empty_plot(
                    fig, "sun_angles", obj.get_observation_code(),
                    labels={"xlabel": "Time, (MJD)", "ylabel": "Angle, (deg.)",
                            "title": f"Sun Angles\nObs. code: {obj.get_observation_code()}"}
                )

            if legend_handles:
                fig.subplots_adjust(left=0.10, bottom=0.10, right=0.85, top=0.90)
                fig.legend(
                    handles=legend_handles,
                    labels=legend_labels,
                    loc=self._style_config["legend"]["loc"],
                    bbox_to_anchor=self._style_config["legend"]["bbox_to_anchor"],
                    fontsize=self._style_config["legend"]["fontsize"],
                    title="Telescopes:",
                    title_fontsize=self._style_config["legend"]["title_fontsize"]
                )

            result["telescopes"] = len(plotted_telescopes)
            logger.debug(f"Visualization result: {result}")
            return result
        
    def _plot_az_el(self, obj: Observation, attributes: Dict[str, Any], fig: Figure) -> Dict[str, Any]:
        """
        Plot Azimuth/Elevation or Hour Angle/Declination for an Observation with flexible filtering using Polars DataFrame.

        Args:
            obj: Observation object to visualize.
            attributes: Dictionary with visualization parameters (coord_type, source_name, telescopes, scans, time_range, etc.).
            fig: Matplotlib Figure object for plotting.

        Returns:
            Dict[str, Any]: Dictionary with visualization results (scans, telescopes, points).
        """
        with self._lock:
            logger.debug(f"Plotting az_el for {obj.get_observation_code()} with attributes: {attributes}")
            store_key = attributes.get("store_key", "az_el")
            source_name = attributes.get("source_name", None)
            telescopes = attributes.get("telescopes", [])
            scans = attributes.get("scans", None)
            time_range = attributes.get("time_range", None)
            coord_type = attributes.get("coord_type", "AzEl")

            if coord_type not in ["AzEl", "HADec"]:
                logger.warning(f"Invalid coord_type '{coord_type}', defaulting to 'AzEl'")
                coord_type = "AzEl"

            if not self._check_filters(attributes, ["source_name", "telescopes"]):
                logger.debug(f"Missing required filters: source_name={source_name}, telescopes={telescopes}, "
                             f"returning empty plot")
                return self._create_empty_plot(
                    fig, "az_el", obj.get_observation_code(),
                    labels={"xlabel": "Time, (MJD)", "ylabel": f"{coord_type[:2]}/{coord_type[2:]}, (deg)",
                            "title": f"Az/El or Ha/Dec\nObs. code: {obj.get_observation_code()}"}
                )

            data_df = obj.get_calculated_data_by_key(store_key)
            if data_df is None or data_df.is_empty():
                logger.debug("No az_el data available, returning empty plot")
                return self._create_empty_plot(
                    fig, "az_el", obj.get_observation_code(),
                    labels={"xlabel": "Time, (MJD)", "ylabel": f"{coord_type[:2]}/{coord_type[2:]}, (deg)",
                            "title": f"Az/El or Ha/Dec\nObs. code: {obj.get_observation_code()}"}
                )

            # Apply filters using Polars
            filtered_df = data_df
            if source_name:
                filtered_df = filtered_df.filter(pl.col("source_name") == source_name)
            if telescopes:
                filtered_df = filtered_df.filter(pl.col("telescope_code").is_in(telescopes))
            if scans:
                filtered_df = filtered_df.filter(pl.col("scan_name").is_in(scans))
            if time_range:
                start_time, end_time = time_range
                filtered_df = filtered_df.filter(
                    (pl.col("time") >= float(start_time)) & (pl.col("time") <= float(end_time))
                )

            if filtered_df.is_empty():
                logger.debug("No data after filtering, returning empty plot")
                return self._create_empty_plot(
                    fig, "az_el", obj.get_observation_code(),
                    labels={"xlabel": "Time, (MJD)", "ylabel": f"{coord_type[:2]}/{coord_type[2:]}, (deg)",
                            "title": f"Az/El or Ha/Dec\nObs. code: {obj.get_observation_code()}"}
                )

            # Check valid telescopes
            valid_telescopes = []
            for tel in filtered_df["telescope_code"].unique():
                tel_data = filtered_df.filter(pl.col("telescope_code") == tel)
                az_values = tel_data["az"].to_numpy()
                el_values = tel_data["el"].to_numpy()
                valid_mask = ~(np.isnan(az_values) | np.isnan(el_values))
                if np.any(valid_mask) and len(tel_data.filter(valid_mask)) > 0:
                    valid_telescopes.append(tel)
            if not valid_telescopes:
                logger.debug("No telescopes with valid data, returning empty plot")
                return self._create_empty_plot(
                    fig, "az_el", obj.get_observation_code(),
                    labels={"xlabel": "Time, (MJD)", "ylabel": f"{coord_type[:2]}/{coord_type[2:]}, (deg)",
                            "title": f"Az/El or Ha/Dec\nObs. code: {obj.get_observation_code()}"}
                )

            n_tels = len(valid_telescopes)
            n_rows = min(n_tels, self._style_config.get("max_subplots", 10)) if n_tels > 1 else 1
            n_cols = 1
            axes = self._setup_axes(
                fig, "az_el", obj.get_observation_code(), n_rows=n_rows, n_cols=n_cols, sharex=True, sharey=True
            )
            axes = np.atleast_1d(axes).tolist()

            result = {"scans": len(filtered_df["scan_name"].unique()), "telescopes": 0, "points": 0}
            plotted_telescopes = set()

            az_color = self._style_config["colors"][2]
            el_color = self._style_config["colors"][4]
            linewidth = self._style_config.get("lines", {}).get("width", 1.5)

            for tel_idx, tel in enumerate(valid_telescopes):
                if n_tels > 1 and tel_idx >= self._style_config.get("max_subplots", 10):
                    break
                tel_data = filtered_df.filter(pl.col("telescope_code") == tel)
                if tel_data.is_empty():
                    logger.debug(f"No data for telescope {tel}, skipping")
                    continue

                tel_data = tel_data.sort("time")
                times_mjd = tel_data["time"].to_numpy()
                az_values = tel_data["az"].to_numpy()
                el_values = tel_data["el"].to_numpy()
                valid_mask = ~(np.isnan(az_values) | np.isnan(el_values))
                if not np.any(valid_mask):
                    logger.debug(f"All az/el values for telescope {tel} are NaN, skipping")
                    continue
                valid_times_mjd = times_mjd[valid_mask]
                valid_az = az_values[valid_mask]
                valid_el = el_values[valid_mask]

                ax = axes[0] if n_tels == 1 else axes[tel_idx]

                # Plot lines for Az and El
                ax.plot(
                    valid_times_mjd, valid_az,
                    color=az_color,
                    label=f"{coord_type[:2]}" if tel_idx == 0 else "",
                    linewidth=linewidth,
                    alpha=0.7
                )
                ax.plot(
                    valid_times_mjd, valid_el,
                    color=el_color,
                    label=f"{coord_type[2:]}" if tel_idx == 0 else "",
                    linewidth=linewidth,
                    alpha=0.7
                )
                logger.debug(f"Plotted {len(valid_az)} points for telescope {tel}")
                plotted_telescopes.add(tel)
                result["points"] += len(valid_az) + len(valid_el)

                ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{int(x)}"))
                if n_tels > 1:
                    ax.set_title(f"{tel}", fontsize=self._style_config["font"]["title_size"] - 2, pad=5)
                ax.tick_params(axis="both", labelsize=self._style_config["font"]["tick_size"])

            if not plotted_telescopes:
                logger.debug("No valid data plotted, returning empty result")
                return self._create_empty_plot(
                    fig, "az_el", obj.get_observation_code(),
                    labels={"xlabel": "Time, (MJD)", "ylabel": f"{coord_type[:2]}/{coord_type[2:]}, (deg)",
                            "title": f"Az/El or Ha/Dec\nObs. code: {obj.get_observation_code()}"}
                )

            # Adjust layout and labels
            fig.tight_layout()
            if n_tels > 1:
                fig.subplots_adjust(left=0.15, bottom=0.15, right=0.85, top=0.80, hspace=0.3)
                fig.text(0.5, 0.05, "Time, (MJD)", ha="center", fontsize=self._style_config["font"]["label_size"])
                fig.text(0.05, 0.5, f"{coord_type[:2]}/{coord_type[2:]}, (deg)", va="center", rotation="vertical",
                         fontsize=self._style_config["font"]["label_size"])
                fig.suptitle(f"Az/El or Ha/Dec\nObs. code: {obj.get_observation_code()}\nSource: {source_name}",
                             fontsize=self._style_config["font"]["title_size"], y=0.98)
            else:
                axes[0].set_xlabel("Time, (MJD)", fontsize=self._style_config["font"]["label_size"])
                axes[0].set_ylabel(f"{coord_type[:2]}/{coord_type[2:]}, (deg)", fontsize=self._style_config["font"]["label_size"])
                axes[0].set_title(f"Az/El or Ha/Dec\nObs. code: {obj.get_observation_code()}\nSource: {source_name}",
                                  fontsize=self._style_config["font"]["title_size"], pad=10)
                axes[0].xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{int(x)}"))
                axes[0].tick_params(axis="both", labelsize=self._style_config["font"]["tick_size"])

            # Create legend for Az and El only
            if n_tels >= 1:
                legend_handles = [
                    Line2D([0], [0], color=az_color, label=f"{coord_type[:2]}", linewidth=linewidth),
                    Line2D([0], [0], color=el_color, label=f"{coord_type[2:]}", linewidth=linewidth)
                ]
                fig.legend(
                    handles=legend_handles,
                    loc=self._style_config["legend"]["loc"],
                    bbox_to_anchor=self._style_config["legend"]["bbox_to_anchor"],
                    fontsize=self._style_config["legend"]["fontsize"],
                    title="Coordinates:",
                    title_fontsize=self._style_config["legend"]["title_fontsize"]
                )

            # Hide unused axes
            for ax in axes[len(plotted_telescopes) if n_tels > 1 else 1:]:
                ax.set_visible(False)

            result["telescopes"] = len(plotted_telescopes)
            logger.debug(f"Visualization result: {result}")
            return result

    def _plot_time_on_source(self, obj: Observation, attributes: Dict[str, Any], fig: Figure) -> Dict[str, Any]:
        """
        Plot time on source for an Observation with flexible filtering using Polars DataFrame.

        Args:
            obj: Observation object to visualize.
            attributes: Dictionary with visualization parameters (source_name, telescopes, scans, time_range, etc.).
            fig: Matplotlib Figure object for plotting.

        Returns:
            Dict[str, Any]: Dictionary with visualization results (scans, telescopes, points, intersections).
        """
        with self._lock:
            logger.debug(f"Plotting time on source for {obj.get_observation_code()} with attributes: {attributes}")
            store_key = attributes.get("store_key", "time_on_source")
            source_name = attributes.get("source_name", None)
            telescopes = attributes.get("telescopes", None)
            scans = attributes.get("scans", None)
            time_range = attributes.get("time_range", None)

            # Validate required filters
            if not source_name or not telescopes:
                logger.debug(f"Missing required filters: source_name={source_name}, telescopes={telescopes}, returning empty plot")
                return self._create_empty_plot(
                    fig, "time_on_source", obj.get_observation_code(),
                    labels={"xlabel": "Time, (MJD)", "ylabel": "Telescope",
                            "title": f"Time on {source_name or 'Source'}\nObs. code: {obj.get_observation_code()}"}
                )

            # Get DataFrame from calculated data
            data_df = obj.get_calculated_data_by_key(store_key)
            if data_df is None or data_df.is_empty():
                logger.debug("No time on source data, returning empty plot")
                return self._create_empty_plot(
                    fig, "time_on_source", obj.get_observation_code(),
                    labels={"xlabel": "Time, (MJD)", "ylabel": "Telescope",
                            "title": f"Time on {source_name}\nObs. code: {obj.get_observation_code()}"}
                )

            # Apply filters using Polars
            filtered_df = data_df
            if source_name:
                filtered_df = filtered_df.filter(pl.col("source_name") == source_name)
            if telescopes:
                filtered_df = filtered_df.filter(pl.col("telescope_code").is_in(telescopes))
            if scans:
                filtered_df = filtered_df.filter(pl.col("scan_name").is_in(scans))
            if time_range:
                start_time, end_time = time_range
                filtered_df = filtered_df.filter(
                    (pl.col("start") >= float(start_time)) & (pl.col("end") <= float(end_time))
                )

            if filtered_df.is_empty():
                logger.debug(f"No data after filtering for source {source_name}, returning empty plot")
                return self._create_empty_plot(
                    fig, "time_on_source", obj.get_observation_code(),
                    labels={"xlabel": "Time, (MJD)", "ylabel": "Telescope",
                            "title": f"Time on {source_name}\nObs. code: {obj.get_observation_code()}"}
                )

            # Setup axes
            ax = self._setup_axes(fig, "time_on_source", obj.get_observation_code())
            ax.set_xlabel("Time, (MJD)", fontsize=self._style_config["font"]["label_size"])
            ax.set_ylabel("Telescope", fontsize=self._style_config["font"]["label_size"])
            ax.set_title(f"Time on {source_name}\nObs. code: {obj.get_observation_code()}",
                         fontsize=self._style_config["font"]["title_size"])
            ax.tick_params(axis="both", labelsize=self._style_config["font"]["tick_size"])

            result = {"scans": len(filtered_df["scan_name"].unique()), "telescopes": 0, "points": 0, "intersections": 0}
            all_blocks = {}
            legend_handles = []
            legend_labels = []

            tel_list = sorted(filtered_df["telescope_code"].unique())
            for tel in tel_list:
                tel_data = filtered_df.filter(pl.col("telescope_code") == tel)
                all_blocks[tel] = []
                for row in tel_data.iter_rows(named=True):
                    try:
                        start_mjd = float(row["start"])
                        end_mjd = float(row["end"])
                        duration = float(row["duration"])
                        all_blocks[tel].append((start_mjd, end_mjd, duration))
                    except (ValueError, TypeError) as e:
                        logger.error(f"Invalid block format for {tel} in scan {row['scan_name']}: {str(e)}")
                        continue

            result["telescopes"] = len(tel_list)
            if not tel_list:
                logger.debug(f"No telescopes found after filtering, returning empty plot")
                return self._create_empty_plot(
                    fig, "time_on_source", obj.get_observation_code(),
                    labels={"xlabel": "Time, (MJD)", "ylabel": "Telescope",
                            "title": f"Time on {source_name}\nObs. code: {obj.get_observation_code()}"}
                )

            # Plot time blocks for each telescope
            for i, tel in enumerate(tel_list):
                color_idx = i % len(self._style_config["colors"])
                for start_mjd, end_mjd, _ in all_blocks[tel]:
                    handle = ax.fill_between(
                        [start_mjd, end_mjd],
                        [i, i],
                        [i + 1, i + 1],
                        color=self._style_config["colors"][color_idx],
                        alpha=0.5,
                        label=tel if tel not in set(legend_labels) else None
                    )
                    if tel not in set(legend_labels):
                        legend_handles.append(handle)
                        legend_labels.append(tel)
                    result["points"] += 1

            # Calculate intersection times
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
                        duration = (end - start) * 86400  # Convert MJD to seconds
                        handle = ax.fill_between(
                            [start, end],
                            [-1, -1],
                            [0, 0],
                            color=self._style_config["intersection_color"],
                            alpha=0.9,
                            label="Total" if i == 0 else None
                        )
                        ax.text(
                            (start + end) / 2, -0.5, f"{duration:.1f}s",
                            ha="center", va="center", fontsize=self._style_config["font"]["tick_size"],
                            color="black",
                            bbox=dict(facecolor="white", alpha=0.8, edgecolor="none")
                        )
                        if i == 0:
                            legend_handles.append(handle)
                            legend_labels.append("Total")
                        result["intersections"] = len(intersection_times)

            # Set y-ticks and labels
            ax.set_yticks(np.arange(-1, len(tel_list)))
            ax.set_yticklabels(["Total"] + tel_list, fontsize=self._style_config["font"]["tick_size"])
            fig.subplots_adjust(left=0.10, bottom=0.10, right=0.88, top=0.90)

            # Add legend
            if legend_handles:
                fig.legend(
                    legend_handles, legend_labels,
                    loc=self._style_config["legend"]["loc"],
                    bbox_to_anchor=self._style_config["legend"]["bbox_to_anchor"],
                    fontsize=self._style_config["legend"]["fontsize"],
                    title="Telescopes:",
                    title_fontsize=self._style_config["legend"]["title_fontsize"]
                )

            return result

    def _plot_beam_pattern(self, obj: Observation, attributes: Dict[str, Any], fig: Figure) -> Dict[str, Any]:
        """
        Plot beam patterns for an Observation with one subplot per telescope and a shared frequency legend using Polars DataFrame.

        Args:
            obj: Observation object to visualize.
            attributes: Dictionary with visualization parameters (telescopes, frequencies, etc.).
            fig: Matplotlib Figure object for plotting.

        Returns:
            Dict[str, Any]: Dictionary with visualization results (telescopes, frequencies).
        """
        with self._lock:
            logger.debug(f"Plotting beam pattern for {obj.get_observation_code()} with attributes: {attributes}")
            store_key = attributes.get("store_key", "beam_pattern")
            frequencies = attributes.get("frequencies", [])
            telescopes = attributes.get("telescopes", [])

            if not telescopes or not frequencies:
                logger.debug(f"Empty filter: telescopes={telescopes}, frequencies={frequencies}, returning empty result")
                return self._create_empty_plot(
                    fig, "beam_pattern", obj.get_observation_code(),
                    labels={"xlabel": "Theta, (rad.)", "ylabel": "Normalized Peak Flux",
                            "title": f"Beam Pattern for Observation: {obj.get_observation_code()}"}
                )

            beam_data = obj.get_calculated_data_by_key(store_key)
            if beam_data is None or beam_data.is_empty():
                logger.debug("No beam data available, returning empty result")
                return self._create_empty_plot(
                    fig, "beam_pattern", obj.get_observation_code(),
                    labels={"xlabel": "Theta, (rad.)", "ylabel": "Normalized Peak Flux",
                            "title": f"Beam Pattern for Observation: {obj.get_observation_code()}"}
                )

            metadata = obj._calculated_data_metadata.get(store_key) or {}
            frequency_agnostic = metadata.get("frequency_agnostic", False)
            if frequency_agnostic and len(frequencies) > 1:
                logger.warning("Beam pattern is frequency-agnostic, using first frequency only")
                frequencies = [frequencies[0]]

            filtered_df = beam_data.filter(pl.col("telescope_code").is_in(telescopes))
            if filtered_df.is_empty():
                logger.debug("No valid telescopes in beam_data, returning empty result")
                return self._create_empty_plot(
                    fig, "beam_pattern", obj.get_observation_code(),
                    labels={"xlabel": "Theta, (rad.)", "ylabel": "Normalized Peak Flux",
                            "title": f"Beam Pattern for Observation: {obj.get_observation_code()}"}
                )

            freq_list = [float(f) for f in frequencies if isinstance(f, (int, float)) and f > 0]
            if not freq_list:
                logger.debug("No valid frequencies provided, returning empty result")
                return self._create_empty_plot(
                    fig, "beam_pattern", obj.get_observation_code(),
                    labels={"xlabel": "Theta, (rad.)", "ylabel": "Normalized Peak Flux",
                            "title": f"Beam Pattern for Observation: {obj.get_observation_code()}"}
                )

            ref_freq = min(freq_list)
            ref_wavelength = self.SPEED_OF_LIGHT / (ref_freq * 1e6)
            logger.debug(f"Reference frequency: {ref_freq:.2f} MHz, reference wavelength: {ref_wavelength:.2e} m")

            tel_list = sorted(filtered_df["telescope_code"].unique())
            n_tels = len(tel_list)
            n_cols = int(np.ceil(np.sqrt(n_tels)))
            n_rows = int(np.ceil(n_tels / n_cols))
            axes = self._setup_axes(
                fig, "beam_pattern", obj.get_observation_code(),
                n_rows=n_rows, n_cols=n_cols, sharex=True, sharey=True
            )
            axes = np.atleast_1d(axes)

            norm = plt.Normalize(min(freq_list), max(freq_list)) if freq_list else None
            cmap = self._style_config["colormaps"]["redpurple"] if freq_list else None

            result = {"telescopes": 0, "frequencies": len(freq_list)}
            plotted_telescopes = set()
            plotted_frequencies = set()
            legend_handles = []
            legend_labels = []

            for tel_idx, tel_code in enumerate(tel_list):
                ax = axes[tel_idx] if tel_idx < len(axes) else axes[-1]
                ax.set_title(tel_code, fontsize=self._style_config["font"]["title_size"])
                ax.tick_params(axis="both", labelsize=self._style_config["font"]["tick_size"])

                tel_data = filtered_df.filter(pl.col("telescope_code") == tel_code)
                if tel_data.is_empty():
                    logger.warning(f"No beam data for {tel_code}")
                    continue

                theta = tel_data["theta"].to_numpy()
                pattern = tel_data["pattern"].to_numpy()
                if len(theta) == 0 or len(pattern) == 0 or len(theta) != len(pattern):
                    logger.warning(f"Invalid beam data for {tel_code}: theta={len(theta)}, pattern={len(pattern)}")
                    continue

                for freq_idx, freq_mhz in enumerate(freq_list):
                    try:
                        wavelength = self.SPEED_OF_LIGHT / (freq_mhz * 1e6)
                        if wavelength <= 0:
                            logger.warning(f"Invalid frequency {freq_mhz} MHz for {tel_code}")
                            continue
                        theta_scaling_factor = ref_wavelength / wavelength if not frequency_agnostic else 1.0
                        scaled_theta = theta * theta_scaling_factor
                        scaled_pattern = pattern / np.max(np.abs(pattern)) if np.max(np.abs(pattern)) > 0 else pattern
                        color = cmap(norm(freq_mhz)) if cmap and not frequency_agnostic else self._style_config["colors"][freq_idx % len(self._style_config["colors"])]
                        line, = ax.plot(
                            scaled_theta, scaled_pattern,
                            color=color,
                            linestyle=self._style_config["linestyles"]["default"]
                        )
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

            # Set shared axis labels
            for ax in axes:
                ax.set_xlabel("")
                ax.set_ylabel("")
            if plotted_telescopes:
                fig.text(0.5, 0.04, "Theta, (rad.)", ha="center", fontsize=self._style_config["font"]["label_size"])
                fig.text(0.04, 0.5, "Normalized Peak Flux", va="center", rotation="vertical",
                         fontsize=self._style_config["font"]["label_size"])

            # Adjust layout and add legend
            fig.subplots_adjust(left=0.10, bottom=0.10, right=0.86, top=0.85)
            if legend_handles:
                fig.legend(
                    legend_handles, legend_labels,
                    loc=self._style_config["legend"]["loc"],
                    bbox_to_anchor=(0.87, 0.99),
                    fontsize=self._style_config["legend"]["fontsize"],
                    title="Frequencies:",
                    title_fontsize=self._style_config["legend"]["title_fontsize"],
                    bbox_transform=fig.transFigure
                )

            for idx in range(len(tel_list), len(axes)):
                axes[idx].set_visible(False)

            if not plotted_telescopes:
                logger.debug("No valid data plotted, returning empty result")
                return self._create_empty_plot(
                    fig, "beam_pattern", obj.get_observation_code(),
                    labels={"xlabel": "Theta, (rad.)", "ylabel": "Normalized Peak Flux",
                            "title": f"Beam Pattern for Observation: {obj.get_observation_code()}"}
                )

            fig.suptitle(f"Beam Pattern\nObs. code: {obj.get_observation_code()}",
                         fontsize=self._style_config["font"]["title_size"])
            result["telescopes"] = len(plotted_telescopes)
            result["frequencies"] = len(plotted_frequencies)
            return result

    def _plot_baseline_projections(self, obj: Observation, attributes: Dict[str, Any], fig: Figure) -> Dict[str, Any]:
        """
        Plot baseline projections for an Observation with flexible filtering, frequency scaling, and grouped legend using Polars DataFrame.

        Args:
            obj: Observation object to visualize.
            attributes: Dictionary with visualization parameters (store_key, baselines, source_name, scans, time_range, frequencies, units).
            fig: Matplotlib Figure object for plotting.

        Returns:
            Dict[str, Any]: Dictionary with visualization results (scans, baselines, projections, frequencies).
        """
        with self._lock:
            logger.debug(f"Plotting baseline projections for {obj.get_observation_code()} with attributes: {attributes}")
            store_key = attributes.get("store_key", "baseline_projections")
            baselines = attributes.get("baselines", [])
            source_name = attributes.get("source_name", None)
            scans = attributes.get("scans", None)
            time_range = attributes.get("time_range", None)
            frequencies = attributes.get("frequencies", [])
            units = attributes.get("units", "wavelengths")

            if not self._check_filters(attributes, ["source_name", "baselines", "scans", "frequencies"]):
                logger.debug(f"Missing required filters: source_name={source_name}, baselines={baselines}, "
                             f"scans={scans}, frequencies={frequencies}, returning empty plot")
                return self._create_empty_plot(
                    fig, "baseline_projections", obj.get_observation_code(),
                    labels={"xlabel": "Time, (MJD)", "ylabel": f"Baseline Projection, ({units})",
                            "title": f"Baseline Projections\nObs. code: {obj.get_observation_code()}"}
                )

            bl_data = obj.get_calculated_data_by_key(store_key)
            if bl_data is None or bl_data.is_empty():
                logger.debug("No baseline projection data available, returning empty plot")
                return self._create_empty_plot(
                    fig, "baseline_projections", obj.get_observation_code(),
                    labels={"xlabel": "Time, (MJD)", "ylabel": f"Baseline Projection, ({units})",
                            "title": f"Baseline Projections\nObs. code: {obj.get_observation_code()}"}
                )

            # Apply filters using Polars
            filtered_df = bl_data
            if source_name:
                filtered_df = filtered_df.filter(pl.col("source_name") == source_name)
            if baselines:
                filtered_df = filtered_df.filter(pl.col("baseline").is_in(baselines))
            if scans:
                filtered_df = filtered_df.filter(pl.col("scan_name").is_in(scans))
            if time_range:
                start_time, end_time = time_range
                filtered_df = filtered_df.filter(
                    (pl.col("time") >= float(start_time)) & (pl.col("time") <= float(end_time))
                )

            if filtered_df.is_empty():
                logger.debug("No data after filtering, returning empty plot")
                return self._create_empty_plot(
                    fig, "baseline_projections", obj.get_observation_code(),
                    labels={"xlabel": "Time, (MJD)", "ylabel": f"Baseline Length, ({units})",
                            "title": f"Baseline Projections\nObs. code: {obj.get_observation_code()}"}
                )

            freq_list = [float(f) for f in frequencies if isinstance(f, (int, float)) and f > 0]
            if not freq_list:
                logger.debug("No valid frequencies provided, returning empty plot")
                return self._create_empty_plot(
                    fig, "baseline_projections", obj.get_observation_code(),
                    labels={"xlabel": "Time, (MJD)", "ylabel": f"Baseline Length, ({units})",
                            "title": f"Baseline Projections\nObs. code: {obj.get_observation_code()}"}
                )

            ref_freq = min(freq_list)
            ref_wavelength = self.SPEED_OF_LIGHT / (ref_freq * 1e6)
            logger.debug(f"Reference frequency: {ref_freq:.2f} MHz, reference wavelength: {ref_wavelength:.2e} m")

            ax = self._setup_axes(fig, "baseline_projections", obj.get_observation_code())
            ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{int(x)}"))
            ax.set_xlabel("Time, (MJD)", fontsize=self._style_config["font"]["label_size"])
            ax.set_title(f"Baseline Projections\nObs. code: {obj.get_observation_code()}\nSource: {source_name}",
                         fontsize=self._style_config["font"]["title_size"])
            ax.tick_params(axis="both", labelsize=self._style_config["font"]["tick_size"])

            result = {"scans": len(filtered_df["scan_name"].unique()), "baselines": 0, "projections": 0, "frequencies": len(freq_list)}
            plotted_pairs = set()
            legend_handles = []
            legend_labels = []
            max_bl = 0.0

            # Process data for each baseline and frequency
            for pair_idx, pair in enumerate(filtered_df["baseline"].unique()):
                pair_data = filtered_df.filter(pl.col("baseline") == pair)
                if pair_data.is_empty():
                    logger.debug(f"No data for baseline {pair}, skipping")
                    continue

                # Sort by time and extract valid projections
                pair_data = pair_data.sort("time")
                times_mjd = pair_data["time"].to_numpy()
                projections = pair_data["projection"].to_numpy()
                valid_mask = ~np.isnan(projections)
                if not np.any(valid_mask):
                    logger.debug(f"All projections for baseline {pair} are NaN, skipping")
                    continue
                valid_times_mjd = times_mjd[valid_mask]
                valid_projections = projections[valid_mask]

                color = self._style_config["colors"][pair_idx % len(self._style_config["colors"])]

                for freq_idx, freq_mhz in enumerate(freq_list):
                    wavelength = self.SPEED_OF_LIGHT / (freq_mhz * 1e6)
                    if units == "wavelengths":
                        bl_scaled = valid_projections / wavelength
                    else:
                        bl_scaled = (valid_projections / wavelength) / (self.EARTH_DIAMETER / ref_wavelength)

                    valid_mask = ~np.isnan(bl_scaled)
                    if not np.any(valid_mask):
                        logger.debug(f"All scaled projections for baseline {pair} at {freq_mhz:.2f} MHz are NaN, skipping")
                        continue
                    valid_times_mjd = valid_times_mjd[valid_mask]
                    valid_bl_scaled = bl_scaled[valid_mask]

                    max_bl = max(max_bl, np.max(np.abs(valid_bl_scaled)))
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
                    ax.set_ylabel(f"Baseline Length, ({prefix})", fontsize=self._style_config["font"]["label_size"])

                    label = f"{pair} ({freq_mhz:.2f} MHz)"
                    bl_plot = valid_bl_scaled / scale
                    handle = ax.scatter(
                        valid_times_mjd, bl_plot,
                        s=self._style_config["markers"]["scatter_size"],
                        c=[color],
                        label=label,
                        alpha=0.7,
                        marker=self._style_config["markers"]["track_style"]
                    )
                    logger.debug(f"Plotted {len(bl_plot)} points for baseline {pair} at {freq_mhz:.2f} MHz")
                    legend_handles.append(handle)
                    legend_labels.append((freq_mhz, pair))
                    plotted_pairs.add(f"{pair}_{freq_mhz}")
                    result["projections"] += len(bl_plot)

            if not plotted_pairs:
                logger.debug("No valid data plotted, returning empty result")
                return self._create_empty_plot(
                    fig, "baseline_projections", obj.get_observation_code(),
                    labels={"xlabel": "Time, (MJD)", "ylabel": f"Baseline Length, ({units})",
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
                    loc=self._style_config["legend"]["loc"],
                    bbox_to_anchor=self._style_config["legend"]["bbox_to_anchor"],
                    fontsize=self._style_config["legend"]["fontsize"],
                    title="Baselines:",
                    title_fontsize=self._style_config["legend"]["title_fontsize"]
                )

            result["baselines"] = len(plotted_pairs)
            logger.debug(f"Visualization result: {result}")
            return result

    def _plot_mollweide_tracks(self, obj: Observation, attributes: Dict[str, Any], fig: Figure) -> Dict[str, Any]:
        """
        Plot Mollweide tracks for an Observation with flexible filtering and grouped legend using Polars DataFrame.

        Args:
            obj: Observation object to visualize.
            attributes: Dictionary with visualization parameters (telescopes, scans, sources, max_points, etc.).
            fig: Matplotlib Figure object for plotting.

        Returns:
            Dict[str, Any]: Dictionary with visualization results (scans, telescopes, sources, points).
        """
        with self._lock:
            logger.debug(f"Plotting Mollweide tracks for {obj.get_observation_code()} with attributes: {attributes}")
            store_key = attributes.get("store_key", "mollweide_tracks")
            telescopes = attributes.get("telescopes", [])
            scans = attributes.get("scans", [])
            sources = attributes.get("sources", [])
            max_points = attributes.get("max_points", 10000)

            ax = self._setup_axes(fig, "mollweide_tracks", obj.get_observation_code(), projection="mollweide")
            ax.set_title(f"Mollweide Tracks\nObs. code: {obj.get_observation_code()}",
                         fontsize=self._style_config["font"]["title_size"])
            ax.tick_params(axis="both", labelsize=self._style_config["font"]["tick_size"])

            data = obj.get_calculated_data_by_key(store_key)
            if data is None or data.is_empty():
                logger.warning(f"No valid Mollweide track data found for '{store_key}'")
                return self._create_empty_plot(
                    fig, "mollweide_tracks", obj.get_observation_code(),
                    projection="mollweide",
                    labels={"title": f"Mollweide Tracks\nObs. code: {obj.get_observation_code()}"}
                )

            sources_metadata = obj._calculated_data_metadata.get(store_key, {}).get("sources", {})
            if not sources_metadata:
                logger.warning("No source metadata found in _calculated_data_metadata['sources']")
                return self._create_empty_plot(
                    fig, "mollweide_tracks", obj.get_observation_code(),
                    projection="mollweide",
                    labels={"title": f"Mollweide Tracks\nObs. code: {obj.get_observation_code()}"}
                )

            # Apply filters using Polars
            filtered_df = data
            if telescopes:
                filtered_df = filtered_df.filter(pl.col("telescope_code").is_in(telescopes))
            if scans:
                filtered_df = filtered_df.filter(pl.col("scan_name").is_in(scans))
            if sources:
                if not all(source in sources_metadata for source in sources):
                    logger.error(f"Some sources {sources} not found in _calculated_data_metadata['sources']")
                    filtered_df = filtered_df.filter(pl.col("source_name").is_in(sources))

            if filtered_df.is_empty():
                logger.debug("No data after filtering, returning empty Mollweide plot")
                return self._create_empty_plot(
                    fig, "mollweide_tracks", obj.get_observation_code(),
                    projection="mollweide",
                    labels={"title": f"Mollweide Tracks\nObs. code: {obj.get_observation_code()}"}
                )

            result = {"scans": len(filtered_df["scan_name"].unique()), "telescopes": 0, "sources": 0, "points": 0}
            plotted_telescopes = set()
            plotted_sources = set()
            legend_handles = []
            legend_labels = []

            # Plot sources from metadata
            source_colors = {}
            for source_name in sources_metadata:
                if sources and source_name not in sources:
                    continue
                coords = sources_metadata.get(source_name, [])
                try:
                    lon, lat = float(coords[0]), float(coords[1])
                    lon_rad = np.radians(lon)
                    lat_rad = np.radians(lat)
                    color = 'black'
                    source_colors[source_name] = color
                    handle = ax.scatter(
                        lon_rad, lat_rad,
                        c=[color],
                        marker=self._style_config["markers"]["source_style"],
                        s=self._style_config["markers"]["default_size"],
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

            # Subsample data if necessary
            total_points = len(filtered_df)
            if total_points > max_points:
                logger.warning(f"Total points ({total_points}) exceeds max_points ({max_points}), subsampling tracks")
                subsample_factor = total_points // max_points + 1
            else:
                subsample_factor = 1

            cmap = self._style_config["colormaps"]["redpurple"] if telescopes else None

            # Plot telescope tracks
            for tel_idx, tel_code in enumerate(filtered_df["telescope_code"].unique()):
                tel_data = filtered_df.filter(pl.col("telescope_code") == tel_code)
                if tel_data.is_empty():
                    logger.debug(f"No data for telescope {tel_code}, skipping")
                    continue

                lon = tel_data["lon"].to_numpy()
                lat = tel_data["lat"].to_numpy()
                valid_mask = (~np.isnan(lon)) & (~np.isnan(lat))
                lon = lon[valid_mask]
                lat = lat[valid_mask]
                if len(lon) == 0:
                    logger.debug(f"No valid points for {tel_code} after filtering")
                    continue
                if subsample_factor > 1:
                    lon = lon[::subsample_factor]
                    lat = lat[::subsample_factor]
                lon_rad = np.radians(lon)
                lat_rad = np.radians(lat)
                color = cmap(tel_idx / len(telescopes)) if cmap else self._style_config["colors"][tel_idx % len(self._style_config["colors"])]
                handle = ax.scatter(
                    lon_rad, lat_rad,
                    s=self._style_config["markers"]["track_size"],
                    c=[color],
                    marker=self._style_config["markers"]["track_style"],
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
                    loc=self._style_config["legend"]["loc"],
                    bbox_to_anchor=self._style_config["legend"]["bbox_to_anchor"],
                    fontsize=self._style_config["legend"]["fontsize"],
                    title="",
                    title_fontsize=self._style_config["legend"]["title_fontsize"],
                    bbox_transform=fig.transFigure
                )

            # Handle empty plot case
            if not plotted_telescopes and not plotted_sources:
                logger.debug("No telescopes or sources plotted, returning empty Mollweide plot")
                return self._create_empty_plot(
                    fig, "mollweide_tracks", obj.get_observation_code(),
                    projection="mollweide",
                    labels={"title": f"Mollweide Tracks\nObs. code: {obj.get_observation_code()}"}
                )

            return result