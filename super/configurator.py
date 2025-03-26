# /super/configurator.py
from abc import ABC
from base.frequencies import IF, Frequencies
from base.sources import Source, Sources
from base.telescopes import Telescope, SpaceTelescope, Telescopes
from base.scans import Scan, Scans
from base.observation import Observation
from base.project import Project 
from utils.logging_setup import logger
from typing import Dict, Any, Callable
from functools import lru_cache
import inspect

class Configurator(ABC):
    """Super-class for configuring Project and its components.

    Attributes:
        _config_methods (dict): Cached dictionary mapping object types to configuration functions and methods.

    Methods:
        configure: Universal method to configure objects using method calls in attributes dictionary.
        _get_config_methods: Cached method to retrieve configuration method mappings.
    """
    def __init__(self):
        """Initialize the Configurator"""
        logger.info("Initialized Configurator")

    def _validate_and_apply_method(self, obj: Any, method_name: str, method_args: Any, valid_methods: Dict[str, Callable], 
                                  extra_args: Dict[str, Any] = None) -> bool:
        """Validate and apply a method to an object

        Args:
            obj: The object to apply the method to
            method_name: Name of the method to call
            method_args: Arguments for the method
            valid_methods: Dictionary of valid methods for the object's type
            extra_args: Optional additional arguments to pass to the method (e.g., observation for Scan)

        Returns:
            bool: True if the method was applied successfully, False otherwise
        """
        if method_name not in valid_methods:
            logger.error(f"Invalid method {method_name} for {type(obj).__name__} object")
            return False
        if not isinstance(method_args, dict):
            logger.error(f"Arguments for {method_name} must be a dictionary, got {type(method_args)}")
            return False

        method = valid_methods[method_name]
        sig = inspect.signature(method)
        expected_params = set(sig.parameters.keys()) - {"self"}
        provided_params = set(method_args.keys())

        if not provided_params.issubset(expected_params):
            logger.error(f"Invalid arguments for {method_name}: expected {expected_params}, got {provided_params}")
            return False

        try:
            if extra_args:
                method_args = {**method_args, **extra_args}
            method(obj, **method_args)
            return True
        except Exception as e:
            logger.error(f"Failed to apply {method_name} to {type(obj).__name__}: {str(e)}")
            return False

    def _configure_if(self, if_obj: IF, attributes: Dict[str, Any]) -> bool:
        """Configure an IF object"""
        try:
            valid_methods = self._get_config_methods()[IF]["methods"]
            applied = False

            for method_name, method_args in attributes.items():
                if self._validate_and_apply_method(if_obj, method_name, method_args, valid_methods):
                    applied = True

            if not applied:
                logger.warning("No valid methods provided for IF configuration")
                return False

            logger.info(f"Successfully configured IF: freq={if_obj.get_frequency()}, bw={if_obj.get_bandwidth()}")
            return True
        except Exception as e:
            logger.error(f"Failed to configure IF: {str(e)}")
            return False

    def _configure_frequencies(self, freq_obj: Frequencies, attributes: Dict[str, Any]) -> bool:
        """Configure a Frequencies object"""
        try:
            valid_methods = self._get_config_methods()[Frequencies]["methods"]
            applied = False

            if "if_index" in attributes:
                if_index = attributes["if_index"]
                if not isinstance(if_index, int) or not 0 <= if_index < len(freq_obj):
                    logger.error(f"Invalid if_index {if_index} for Frequencies with {len(freq_obj)} IFs")
                    return False
                if_obj = freq_obj.get_IF(if_index)
                nested_attrs = {k: v for k, v in attributes.items() if k != "if_index"}
                return self._configure_if(if_obj, nested_attrs)

            for method_name, method_args in attributes.items():
                if self._validate_and_apply_method(freq_obj, method_name, method_args, valid_methods):
                    applied = True

            if not applied:
                logger.warning("No valid methods or nested IF configuration provided for Frequencies")
                return False

            logger.info(f"Successfully configured Frequencies: count={len(freq_obj)}")
            return True
        except Exception as e:
            logger.error(f"Failed to configure Frequencies: {str(e)}")
            return False

    def _configure_source(self, source_obj: Source, attributes: Dict[str, Any]) -> bool:
        """Configure a Source object"""
        try:
            valid_methods = self._get_config_methods()[Source]["methods"]
            applied = False

            for method_name, method_args in attributes.items():
                if self._validate_and_apply_method(source_obj, method_name, method_args, valid_methods):
                    applied = True

            if not applied:
                logger.warning("No valid methods provided for Source configuration")
                return False

            logger.info(f"Successfully configured Source: name='{source_obj.get_name()}'")
            return True
        except Exception as e:
            logger.error(f"Failed to configure Source: {str(e)}")
            return False

    def _configure_sources(self, sources_obj: Sources, attributes: Dict[str, Any]) -> bool:
        """Configure a Sources object."""
        try:
            valid_methods = self._get_config_methods()[Sources]["methods"]
            applied = False

            if "source_index" in attributes:
                source_index = attributes["source_index"]
                if not isinstance(source_index, int) or not 0 <= source_index < len(sources_obj):
                    logger.error(f"Invalid source_index {source_index} for Sources with {len(sources_obj)} sources")
                    return False
                source_obj = sources_obj.get_source(source_index)
                nested_attrs = {k: v for k, v in attributes.items() if k != "source_index"}
                return self._configure_source(source_obj, nested_attrs)

            for method_name, method_args in attributes.items():
                if self._validate_and_apply_method(sources_obj, method_name, method_args, valid_methods):
                    applied = True

            if not applied:
                logger.warning("No valid methods or nested Source configuration provided for Sources")
                return False

            logger.info(f"Successfully configured Sources: count={len(sources_obj)}")
            return True
        except Exception as e:
            logger.error(f"Failed to configure Sources: {str(e)}")
            return False

    def _configure_telescope(self, tel_obj: Telescope | SpaceTelescope, attributes: Dict[str, Any]) -> bool:
        """Configure a Telescope or SpaceTelescope object"""
        try:
            obj_type = type(tel_obj)
            valid_methods = self._get_config_methods()[obj_type]["methods"]
            applied = False

            for method_name, method_args in attributes.items():
                if self._validate_and_apply_method(tel_obj, method_name, method_args, valid_methods):
                    applied = True

            if not applied:
                logger.warning(f"No valid methods provided for {obj_type.__name__} configuration")
                return False

            logger.info(f"Successfully configured {obj_type.__name__}: code='{tel_obj.get_code()}'")
            return True
        except Exception as e:
            logger.error(f"Failed to configure {obj_type.__name__}: {str(e)}")
            return False

    def _configure_telescopes(self, tel_obj: Telescopes, attributes: Dict[str, Any]) -> bool:
        """Configure a Telescopes object"""
        try:
            valid_methods = self._get_config_methods()[Telescopes]["methods"]
            applied = False

            if "telescope_index" in attributes:
                telescope_index = attributes["telescope_index"]
                if not isinstance(telescope_index, int) or not 0 <= telescope_index < len(tel_obj):
                    logger.error(f"Invalid telescope_index {telescope_index} for Telescopes with {len(tel_obj)} telescopes")
                    return False
                telescope_obj = tel_obj.get_telescope(telescope_index)
                nested_attrs = {k: v for k, v in attributes.items() if k != "telescope_index"}
                return self._configure_telescope(telescope_obj, nested_attrs)

            for method_name, method_args in attributes.items():
                if self._validate_and_apply_method(tel_obj, method_name, method_args, valid_methods):
                    applied = True

            if not applied:
                logger.warning("No valid methods or nested Telescope configuration provided for Telescopes")
                return False

            logger.info(f"Successfully configured Telescopes: count={len(tel_obj)}")
            return True
        except Exception as e:
            logger.error(f"Failed to configure Telescopes: {str(e)}")
            return False

    def _configure_scan(self, scan_obj: Scan, attributes: Dict[str, Any]) -> bool:
        """Configure a Scan object, validating with observation if provided"""
        try:
            valid_methods = self._get_config_methods()[Scan]["methods"]
            applied = False
            observation = attributes.get("observation")

            for method_name, method_args in attributes.items():
                if method_name == "observation":
                    continue
                extra_args = {"observation": observation} if observation and "observation" in inspect.signature(valid_methods[method_name]).parameters else {}
                if self._validate_and_apply_method(scan_obj, method_name, method_args, valid_methods, extra_args):
                    applied = True
                    if observation and not scan_obj.validate_with_observation(observation):
                        logger.error(f"Scan became invalid after {method_name} with observation '{observation.get_observation_code()}'")
                        return False

            if not applied:
                logger.warning("No valid methods provided for Scan configuration")
                return False

            source_str = "OFF SOURCE" if scan_obj.is_off_source else f"source_index={scan_obj.get_source_index()}"
            logger.info(f"Successfully configured Scan: start={scan_obj.get_start()}, {source_str}")
            return True
        except Exception as e:
            logger.error(f"Failed to configure Scan: {str(e)}")
            return False

    def _configure_scans(self, scans_obj: Scans, attributes: Dict[str, Any]) -> bool:
        """Configure a Scans object, checking overlaps for nested Scan changes"""
        try:
            valid_methods = self._get_config_methods()[Scans]["methods"]
            applied = False

            if "scan_index" in attributes:
                scan_index = attributes["scan_index"]
                if not isinstance(scan_index, int) or not 0 <= scan_index < len(scans_obj):
                    logger.error(f"Invalid scan_index {scan_index} for Scans with {len(scans_obj)} scans")
                    return False
                scan_obj = scans_obj.get_scan(scan_index)
                nested_attrs = {k: v for k, v in attributes.items() if k != "scan_index"}
                success = self._configure_scan(scan_obj, nested_attrs)
                if success:
                    overlap, reason = scans_obj._check_overlap(scan_obj, exclude_index=scan_index)
                    if overlap:
                        logger.error(f"Modified scan at index {scan_index} {reason}")
                        return False
                return success

            for method_name, method_args in attributes.items():
                if self._validate_and_apply_method(scans_obj, method_name, method_args, valid_methods):
                    applied = True

            if not applied:
                logger.warning("No valid methods or nested Scan configuration provided for Scans")
                return False

            logger.info(f"Successfully configured Scans: count={len(scans_obj)}")
            return True
        except Exception as e:
            logger.error(f"Failed to configure Scans: {str(e)}")
            return False

    def _configure_observation(self, obs_obj: Observation, attributes: Dict[str, Any]) -> bool:
        """Configure an Observation object, validating its state afterward"""
        try:
            valid_methods = self._get_config_methods()[Observation]["methods"]
            applied = False

            for method_name, method_args in attributes.items():
                if self._validate_and_apply_method(obs_obj, method_name, method_args, valid_methods):
                    applied = True

            if not applied:
                logger.warning("No valid methods provided for Observation configuration")
                return False

            if not obs_obj.validate():
                logger.error(f"Observation '{obs_obj.get_observation_code()}' is invalid after configuration")
                return False

            logger.info(f"Successfully configured Observation: code='{obs_obj.get_observation_code()}'")
            return True
        except Exception as e:
            logger.error(f"Failed to configure Observation: {str(e)}")
            return False

    def _configure_project(self, project_obj: Project, attributes: Dict[str, Any]) -> bool:
        """Configure a Project object, including nested Observation configuration by index"""
        try:
            valid_methods = self._get_config_methods()[Project]["methods"]
            applied = False

            if "observation_index" in attributes:
                obs_index = attributes["observation_index"]
                if not isinstance(obs_index, int) or not 0 <= obs_index < len(project_obj.get_observations()):
                    logger.error(f"Invalid observation_index {obs_index} for Project '{project_obj.get_name()}' with {len(project_obj.get_observations())} observations")
                    return False
                obs_obj = project_obj.get_observation(obs_index)
                nested_attrs = {k: v for k, v in attributes.items() if k != "observation_index"}
                return self._configure_observation(obs_obj, nested_attrs)

            for method_name, method_args in attributes.items():
                if self._validate_and_apply_method(project_obj, method_name, method_args, valid_methods):
                    applied = True

            if not applied:
                logger.warning("No valid methods or nested Observation configuration provided for Project")
                return False

            logger.info(f"Successfully configured Project: name='{project_obj.get_name()}', observations_count={len(project_obj.get_observations())}")
            return True
        except Exception as e:
            logger.error(f"Failed to configure Project: {str(e)}")
            return False

    @lru_cache(maxsize=1)
    def _get_config_methods(self) -> Dict[type, Dict[str, Any]]:
        """Retrieve and cache the mapping of object types to configuration functions and valid methods"""
        return {
            IF: {
                "config_func": self._configure_if,
                "methods": {
                    "activate": IF.activate,
                    "deactivate": IF.deactivate,
                    "set_if": IF.set_if,
                    "set_frequency": IF.set_frequency,
                    "set_bandwidth": IF.set_bandwidth,
                    "set_polarization": IF.set_polarization,
                    "set_frequency_wavelength": IF.set_frequency_wavelength
                }
            },
            Frequencies: {
                "config_func": self._configure_frequencies,
                "methods": {
                    "add_IF": Frequencies.add_IF,
                    "insert_IF": Frequencies.insert_IF,
                    "remove_IF": Frequencies.remove_IF,
                    "set_IF": Frequencies.set_IF,
                    "activate_IF": Frequencies.activate_IF,
                    "deactivate_IF": Frequencies.deactivate_IF,
                    "activate_all": Frequencies.activate_all,
                    "deactivate_all": Frequencies.deactivate_all,
                    "drop_active": Frequencies.drop_active,
                    "drop_inactive": Frequencies.drop_inactive,
                    "clear": Frequencies.clear
                }
            },
            Source: {
                "config_func": self._configure_source,
                "methods": {
                    "add_flux": Source.add_flux,
                    "insert_flux": Source.insert_flux,
                    "remove_flux": Source.remove_flux,
                    "activate": Source.activate,
                    "deactivate": Source.deactivate,
                    "set_source": Source.set_source,
                    "set_name": Source.set_name,
                    "set_name_J2000": Source.set_name_J2000,
                    "set_alt_name": Source.set_alt_name,
                    "set_ra": Source.set_ra,
                    "set_dec": Source.set_dec,
                    "set_ra_degrees": Source.set_ra_degrees,
                    "set_dec_degrees": Source.set_dec_degrees,
                    "set_source_coordinates": Source.set_source_coordinates,
                    "set_source_coordinates_deg": Source.set_source_coordinates_deg,
                    "set_flux": Source.set_flux,
                    "set_flux_table": Source.set_flux_table,
                    "set_spectral_index": Source.set_spectral_index,
                    "clear_flux_table": Source.clear_flux_table
                }
            },
            Sources: {
                "config_func": self._configure_sources,
                "methods": {
                    "add_source": Sources.add_source,
                    "insert_source": Sources.insert_source,
                    "remove_source": Sources.remove_source,
                    "set_source": Sources.set_source,
                    "activate_source": Sources.activate_source,
                    "deactivate_source": Sources.deactivate_source,
                    "activate_all": Sources.activate_all,
                    "deactivate_all": Sources.deactivate_all,
                    "drop_active": Sources.drop_active,
                    "drop_inactive": Sources.drop_inactive,
                    "clear": Sources.clear
                }
            },
            Telescope: {
                "config_func": self._configure_telescope,
                "methods": {
                    "add_sefd": Telescope.add_sefd,
                    "insert_sefd": Telescope.insert_sefd,
                    "remove_sefd": Telescope.remove_sefd,
                    "activate": Telescope.activate,
                    "deactivate": Telescope.deactivate,
                    "set_telescope": Telescope.set_telescope,
                    "set_name": Telescope.set_name,
                    "set_code": Telescope.set_code,
                    "set_coordinates": Telescope.set_coordinates,
                    "set_velocities": Telescope.set_velocities,
                    "set_coordinates_and_velocities": Telescope.set_coordinates_and_velocities,
                    "set_x": Telescope.set_x,
                    "set_y": Telescope.set_y,
                    "set_z": Telescope.set_z,
                    "set_vx": Telescope.set_vx,
                    "set_vy": Telescope.set_vy,
                    "set_vz": Telescope.set_vz,
                    "set_diameter": Telescope.set_diameter,
                    "set_elevation_range": Telescope.set_elevation_range,
                    "set_azimuth_range": Telescope.set_azimuth_range,
                    "set_mount_type": Telescope.set_mount_type,
                    "set_sefd": Telescope.set_sefd,
                    "set_sefd_table": Telescope.set_sefd_table,
                    "clear_sefd_table": Telescope.clear_sefd_table
                }
            },
            SpaceTelescope: {
                "config_func": self._configure_telescope,
                "methods": {
                    "add_sefd": SpaceTelescope.add_sefd,
                    "insert_sefd": SpaceTelescope.insert_sefd,
                    "remove_sefd": SpaceTelescope.remove_sefd,
                    "activate": SpaceTelescope.activate,
                    "deactivate": SpaceTelescope.deactivate,
                    "set_telescope": SpaceTelescope.set_telescope,
                    "set_name": SpaceTelescope.set_name,
                    "set_code": SpaceTelescope.set_code,
                    "set_coordinates": SpaceTelescope.set_coordinates,
                    "set_velocities": SpaceTelescope.set_velocities,
                    "set_coordinates_and_velocities": SpaceTelescope.set_coordinates_and_velocities,
                    "set_x": SpaceTelescope.set_x,
                    "set_y": SpaceTelescope.set_y,
                    "set_z": SpaceTelescope.set_z,
                    "set_vx": SpaceTelescope.set_vx,
                    "set_vy": SpaceTelescope.set_vy,
                    "set_vz": SpaceTelescope.set_vz,
                    "set_diameter": SpaceTelescope.set_diameter,
                    "set_elevation_range": SpaceTelescope.set_elevation_range,
                    "set_azimuth_range": SpaceTelescope.set_azimuth_range,
                    "set_mount_type": SpaceTelescope.set_mount_type,
                    "set_sefd": SpaceTelescope.set_sefd,
                    "set_sefd_table": SpaceTelescope.set_sefd_table,
                    "clear_sefd_table": SpaceTelescope.clear_sefd_table,
                    "load_orbit": SpaceTelescope.load_orbit,
                    "interpolate_orbit_chebyshev": SpaceTelescope.interpolate_orbit_chebyshev,
                    "interpolate_orbit_cubic_spline": SpaceTelescope.interpolate_orbit_cubic_spline,
                    "set_space_telescope": SpaceTelescope.set_space_telescope,
                    "set_keplerian": SpaceTelescope.set_keplerian,
                    "set_pitch_range": SpaceTelescope.set_pitch_range,
                    "set_yaw_range": SpaceTelescope.set_yaw_range,
                    "set_use_kep": SpaceTelescope.set_use_kep
                }
            },
            Telescopes: {
                "config_func": self._configure_telescopes,
                "methods": {
                    "add_telescope": Telescopes.add_telescope,
                    "insert_telescope": Telescopes.insert_telescope,
                    "remove_telescope": Telescopes.remove_telescope,
                    "set_telescope": Telescopes.set_telescope,
                    "activate_telescope": Telescopes.activate_telescope,
                    "deactivate_telescope": Telescopes.deactivate_telescope,
                    "activate_all": Telescopes.activate_all,
                    "deactivate_all": Telescopes.deactivate_all,
                    "drop_active": Telescopes.drop_active,
                    "drop_inactive": Telescopes.drop_inactive,
                    "clear": Telescopes.clear
                }
            },
            Scan: {
                "config_func": self._configure_scan,
                "methods": {
                    "activate": Scan.activate,
                    "deactivate": Scan.deactivate,
                    "set_scan": Scan.set_scan,
                    "set_start": Scan.set_start,
                    "set_duration": Scan.set_duration,
                    "set_source_index": Scan.set_source_index,
                    "set_telescope_indices": Scan.set_telescope_indices,
                    "set_frequency_indices": Scan.set_frequency_indices
                }
            },
            Scans: {
                "config_func": self._configure_scans,
                "methods": {
                    "add_scan": Scans.add_scan,
                    "insert_scan": Scans.insert_scan,
                    "remove_scan": Scans.remove_scan,
                    "set_scan": Scans.set_scan,
                    "activate_scan": Scans.activate_scan,
                    "deactivate_scan": Scans.deactivate_scan,
                    "activate_all": Scans.activate_all,
                    "deactivate_all": Scans.deactivate_all,
                    "drop_active": Scans.drop_active,
                    "drop_inactive": Scans.drop_inactive,
                    "clear": Scans.clear
                }
            },
            Observation: {
                "config_func": self._configure_observation,
                "methods": {
                    "activate": Observation.activate,
                    "deactivate": Observation.deactivate,
                    "set_observation": Observation.set_observation,
                    "set_observation_type": Observation.set_observation_type,
                    "set_observation_code": Observation.set_observation_code,
                    "set_sources": Observation.set_sources,
                    "set_frequencies": Observation.set_frequencies,
                    "set_telescopes": Observation.set_telescopes,
                    "set_scans": Observation.set_scans,
                    "set_calculated_data": Observation.set_calculated_data,
                    "set_calculated_data_by_key": Observation.set_calculated_data_by_key
                }
            },
            Project: {
                "config_func": self._configure_project,
                "methods": {
                    "add_observation": Project.add_observation,
                    "insert_observation": Project.insert_observation,
                    "remove_observation": Project.remove_observation,
                    "set_observation": Project.set_observation,
                    "set_name": Project.set_name
                }
            }
        }

    def configure(self, obj: Any, attributes: Dict[str, Any]) -> bool:
        """Universal method to configure an object using method calls in a single attributes dictionary

        Args:
            obj: The object to configure (e.g., IF, Frequencies, Source, Sources, Telescope, SpaceTelescope, Scan, Observation, etc.)
            attributes: Dictionary where keys are method names and values are their arguments
                       Example: {"set_frequency": {"freq": 1420.0}}
                       For nested config: {"if_index": 0, "set_frequency": {"freq": 1420.0}}
                       For Source: {"set_source": {"name": "3C 286", "ra_h": 13, "ra_m": 31, ...}}
                       For Sources: {"source_index": 0, "set_name": {"name": "New Name"}}
                       For Telescope: {"set_coordinates": {"coordinates": (1000.0, 2000.0, 3000.0)}}
                       For Telescopes: {"telescope_index": 0, "set_name": {"name": "New Name"}}
                       For Scan: {"set_scan": {"start": 1234567890, "duration": 300.0}}
                       For Scans: {"scan_index": 0, "set_duration": {"duration": 600.0}}

        Returns:
            bool: True if configuration succeeds, False otherwise

        Raises:
            ValueError: If the object type is not supported
        """
        if obj is None:
            logger.error("Configuration object cannot be None")
            raise ValueError("Configuration object cannot be None")

        config_methods = self._get_config_methods()
        obj_type = type(obj)

        if obj_type not in config_methods:
            logger.error(f"Unsupported object type for configuration: {obj_type}")
            raise ValueError(f"Unsupported object type: {obj_type}")

        try:
            return config_methods[obj_type]["config_func"](obj, attributes)
        except Exception as e:
            logger.error(f"Failed to configure {obj_type}: {str(e)}")
            return False

    def __repr__(self) -> str:
        """String representation of Configurator"""
        return "Configurator()"

class DefaultConfigurator(Configurator):
    """Default implementation of Configurator for configuring Project and its components

    Inherits all configuration methods from Configurator and provides a ready-to-use instance
    for managing observations, telescopes, sources, frequencies, and scans
    """
    def __init__(self):
        super().__init__()
        logger.info("Initialized DefaultConfigurator")