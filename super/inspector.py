# /super/inspector.py
from abc import ABC
from super.manipulator import Manipulator
from base.frequencies import IF, Frequencies
from base.sources import Source, Sources
from base.telescopes import Telescope, SpaceTelescope, Telescopes
from base.scans import Scan, Scans
from base.observation import Observation
from base.project import Project
from utils.logging_setup import logger
from typing import Dict, Any, Callable, Union, Optional
from functools import lru_cache
import inspect

class Inspector(ABC):
    """Super-class for inspecting data from Project and its components

    Attributes:
        _inspection_methods (dict): Cached dictionary mapping object types to inspection functions and getters

    Methods:
        inspect: Universal method to retrieve data from objects using getter calls in attributes dictionary
        _get_inspection_methods: Cached method to retrieve inspection method mappings
    """
    def __init__(self, manipulator: 'Manipulator'):
        """Initialize the Inspector"""
        self._manipulator = manipulator
        logger.info("Initialized Inspector")

    def _validate_and_apply_getter(self, obj: Any, getter_name: str, getter_args: Any, valid_getters: Dict[str, Callable]) -> Optional[Any]:
        """Validate and apply a getter to an object

        Args:
            obj: The object to inspect
            getter_name: Name of the getter to call
            getter_args: Arguments for the getter (if any)
            valid_getters: Dictionary of valid getters for the object's type

        Returns:
            Any: Result of the getter call, or None if failed
        """
        if getter_name not in valid_getters:
            logger.error(f"Invalid getter {getter_name} for {type(obj).__name__} object")
            return None
        if getter_args is not None and not isinstance(getter_args, dict):
            logger.error(f"Arguments for {getter_name} must be a dictionary or None, got {type(getter_args)}")
            return None

        getter = valid_getters[getter_name]
        sig = inspect.signature(getter)
        expected_params = set(sig.parameters.keys()) - {"self"}

        if getter_args:
            provided_params = set(getter_args.keys())
            if not provided_params.issubset(expected_params):
                logger.error(f"Invalid arguments for {getter_name}: expected {expected_params}, got {provided_params}")
                return None

        try:
            result = getter(obj, **getter_args) if getter_args else getter(obj)
            logger.debug(f"Applied {getter_name} to {type(obj).__name__}, result={result}")
            return result
        except Exception as e:
            logger.error(f"Failed to apply {getter_name} to {type(obj).__name__}: {str(e)}")
            return None
        
    def _inspect_nested(self, obj: Any, attributes: Dict[str, Any], index_key: str, getter_method: Callable, nested_inspector: Callable) -> Dict[str, Any]:
        """Inspect a nested object by index using a getter and a nested inspector function

        Args:
            obj: The parent object containing the nested object (e.g., Sources, Telescopes)
            attributes: Dictionary with inspection attributes
            index_key: Key for the index (e.g., 'source_index')
            getter_method: Method to retrieve the nested object (e.g., Sources.get_source)
            nested_inspector: Inspector function for the nested object (e.g., self._inspect_source)

        Returns:
            Dict[str, Any]: Inspection results for the nested object
        """
        index = attributes.get(index_key)
        if index is not None:
            if not isinstance(index, int) or not 0 <= index < len(obj):
                logger.error(f"Invalid {index_key} {index} for {type(obj).__name__}")
                return {}
            nested_obj = getter_method(index)
            nested_attrs = {k: v for k, v in attributes.items() if k != index_key}
            return nested_inspector(nested_obj, nested_attrs)
        return {}

    def _inspect_if(self, if_obj: IF, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect an IF object"""
        try:
            valid_getters = self._get_inspection_methods()[IF]["getters"]
            result = {}

            for getter_name, getter_args in attributes.items():
                value = self._validate_and_apply_getter(if_obj, getter_name, getter_args, valid_getters)
                if value is not None:
                    result[getter_name] = value

            if not result:
                logger.warning("No valid getters provided or applied for IF inspection")
                return {}

            logger.info(f"Successfully inspected IF: freq={if_obj.get_frequency()} MHz")
            return result
        except Exception as e:
            logger.error(f"Failed to inspect IF: {str(e)}")
            return {}

    def _inspect_frequencies(self, freq_obj: Frequencies, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Frequencies object"""
        try:
            valid_getters = self._get_inspection_methods()[Frequencies]["getters"]
            result = {}

            if "if_index" in attributes:
                if_index = attributes["if_index"]
                if not isinstance(if_index, int) or not 0 <= if_index < len(freq_obj):
                    logger.error(f"Invalid if_index {if_index} for Frequencies with {len(freq_obj)} IFs")
                    return {}
                if_obj = freq_obj.get_IF(if_index)
                nested_attrs = {k: v for k, v in attributes.items() if k != "if_index"}
                return self._inspect_if(if_obj, nested_attrs)

            for getter_name, getter_args in attributes.items():
                value = self._validate_and_apply_getter(freq_obj, getter_name, getter_args, valid_getters)
                if value is not None:
                    result[getter_name] = value

            if not result:
                logger.warning("No valid getters or nested IF inspection provided for Frequencies")
                return {}

            logger.info(f"Successfully inspected Frequencies: count={len(freq_obj)}")
            return result
        except Exception as e:
            logger.error(f"Failed to inspect Frequencies: {str(e)}")
            return {}

    def _inspect_source(self, source_obj: Source, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Source object"""
        try:
            valid_getters = self._get_inspection_methods()[Source]["getters"]
            result = {}

            for getter_name, getter_args in attributes.items():
                value = self._validate_and_apply_getter(source_obj, getter_name, getter_args, valid_getters)
                if value is not None:
                    result[getter_name] = value

            if not result:
                logger.warning("No valid getters provided or applied for Source inspection")
                return {}

            logger.info(f"Successfully inspected Source: name='{source_obj.get_name()}'")
            return result
        except Exception as e:
            logger.error(f"Failed to inspect Source: {str(e)}")
            return {}

    def _inspect_sources(self, sources_obj: Sources, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Sources object"""
        try:
            valid_getters = self._get_inspection_methods()[Sources]["getters"]
            result = {}

            if "source_index" in attributes:
                source_index = attributes["source_index"]
                if not isinstance(source_index, int) or not 0 <= source_index < len(sources_obj):
                    logger.error(f"Invalid source_index {source_index} for Sources with {len(sources_obj)} sources")
                    return {}
                source_obj = sources_obj.get_source(source_index)
                nested_attrs = {k: v for k, v in attributes.items() if k != "source_index"}
                return self._inspect_source(source_obj, nested_attrs)

            for getter_name, getter_args in attributes.items():
                value = self._validate_and_apply_getter(sources_obj, getter_name, getter_args, valid_getters)
                if value is not None:
                    result[getter_name] = value

            if not result:
                logger.warning("No valid getters or nested Source inspection provided for Sources")
                return {}

            logger.info(f"Successfully inspected Sources: count={len(sources_obj)}")
            return result
        except Exception as e:
            logger.error(f"Failed to inspect Sources: {str(e)}")
            return {}

    def _inspect_telescope(self, telescope_obj: Union[Telescope, SpaceTelescope], attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Telescope or SpaceTelescope object"""
        try:
            obj_type = type(telescope_obj)
            valid_getters = self._get_inspection_methods()[obj_type]["getters"]
            result = {}

            for getter_name, getter_args in attributes.items():
                value = self._validate_and_apply_getter(telescope_obj, getter_name, getter_args, valid_getters)
                if value is not None:
                    result[getter_name] = value

            if not result:
                logger.warning(f"No valid getters provided or applied for {obj_type.__name__} inspection")
                return {}

            logger.info(f"Successfully inspected {obj_type.__name__}: code='{telescope_obj.get_code()}'")
            return result
        except Exception as e:
            logger.error(f"Failed to inspect {type(telescope_obj).__name__}: {str(e)}")
            return {}

    def _inspect_telescopes(self, telescopes_obj: Telescopes, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Telescopes object"""
        try:
            valid_getters = self._get_inspection_methods()[Telescopes]["getters"]
            result = {}

            if "telescope_index" in attributes:
                telescope_index = attributes["telescope_index"]
                if not isinstance(telescope_index, int) or not 0 <= telescope_index < len(telescopes_obj):
                    logger.error(f"Invalid telescope_index {telescope_index} for Telescopes with {len(telescopes_obj)} telescopes")
                    return {}
                telescope_obj = telescopes_obj.get_telescope(telescope_index)
                nested_attrs = {k: v for k, v in attributes.items() if k != "telescope_index"}
                return self._inspect_telescope(telescope_obj, nested_attrs)

            for getter_name, getter_args in attributes.items():
                value = self._validate_and_apply_getter(telescopes_obj, getter_name, getter_args, valid_getters)
                if value is not None:
                    result[getter_name] = value

            if not result:
                logger.warning("No valid getters or nested Telescope inspection provided for Telescopes")
                return {}

            logger.info(f"Successfully inspected Telescopes: count={len(telescopes_obj)}")
            return result
        except Exception as e:
            logger.error(f"Failed to inspect Telescopes: {str(e)}")
            return {}

    def _inspect_scan(self, scan_obj: Scan, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Scan object"""
        try:
            valid_getters = self._get_inspection_methods()[Scan]["getters"]
            result = {}

            for getter_name, getter_args in attributes.items():
                if getter_name in {"get_source", "get_telescopes", "get_frequencies", "check_telescope_availability"}:
                    if not getter_args or "observation" not in getter_args:
                        logger.error(f"Getter {getter_name} requires an 'observation' argument for Scan")
                        continue
                    if not isinstance(getter_args["observation"], Observation):
                        logger.error(f"Argument 'observation' for {getter_name} must be an Observation object")
                        continue
                value = self._validate_and_apply_getter(scan_obj, getter_name, getter_args, valid_getters)
                if value is not None:
                    result[getter_name] = value

            if not result:
                logger.warning("No valid getters provided or applied for Scan inspection")
                return {}

            logger.info(f"Successfully inspected Scan: start={scan_obj.get_start()}")
            return result
        except Exception as e:
            logger.error(f"Failed to inspect Scan: {str(e)}")
            return {}

    def _inspect_scans(self, scans_obj: Scans, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Scans object"""
        try:
            valid_getters = self._get_inspection_methods()[Scans]["getters"]
            result = {}

            if "scan_index" in attributes:
                scan_index = attributes["scan_index"]
                if not isinstance(scan_index, int) or not 0 <= scan_index < len(scans_obj):
                    logger.error(f"Invalid scan_index {scan_index} for Scans with {len(scans_obj)} scans")
                    return {}
                scan_obj = scans_obj.get_scan(scan_index)
                nested_attrs = {k: v for k, v in attributes.items() if k != "scan_index"}
                return self._inspect_scan(scan_obj, nested_attrs)

            for getter_name, getter_args in attributes.items():
                if getter_name == "get_active_scans" and getter_args and "observation" in getter_args:
                    if not isinstance(getter_args["observation"], Observation):
                        logger.error(f"Argument 'observation' for {getter_name} must be an Observation object")
                        continue
                value = self._validate_and_apply_getter(scans_obj, getter_name, getter_args, valid_getters)
                if value is not None:
                    result[getter_name] = value

            if not result:
                logger.warning("No valid getters or nested Scan inspection provided for Scans")
                return {}

            logger.info(f"Successfully inspected Scans: count={len(scans_obj)}")
            return result
        except Exception as e:
            logger.error(f"Failed to inspect Scans: {str(e)}")
            return {}

    def _inspect_observation(self, obs_obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect an Observation object"""
        try:
            valid_getters = self._get_inspection_methods()[Observation]["getters"]
            result = {}

            # Nested inspection using _inspect_nested
            if "source_index" in attributes:
                return self._inspect_nested(obs_obj.get_sources(), attributes, "source_index", Sources.get_source, self._inspect_source)
            if "telescope_index" in attributes:
                return self._inspect_nested(obs_obj.get_telescopes(), attributes, "telescope_index", Telescopes.get_telescope, self._inspect_telescope)
            if "if_index" in attributes:
                return self._inspect_nested(obs_obj.get_frequencies(), attributes, "if_index", Frequencies.get_IF, self._inspect_if)
            if "scan_index" in attributes:
                return self._inspect_nested(obs_obj.get_scans(), attributes, "scan_index", Scans.get_scan, self._inspect_scan)

            # Direct inspection of Observation
            for getter_name, getter_args in attributes.items():
                value = self._validate_and_apply_getter(obs_obj, getter_name, getter_args, valid_getters)
                if value is not None:
                    result[getter_name] = value

            if not result:
                logger.warning("No valid getters or nested inspection provided for Observation")
                return {}

            logger.info(f"Successfully inspected Observation: code='{obs_obj.get_observation_code()}'")
            return result
        except Exception as e:
            logger.error(f"Failed to inspect Observation: {str(e)}")
            return {}

    def _inspect_project(self, project_obj: Project, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Project object"""
        try:
            valid_getters = self._get_inspection_methods()[Project]["getters"]
            result = {}

            if "observation_index" in attributes:
                observation_index = attributes["observation_index"]
                if not isinstance(observation_index, int) or not 0 <= observation_index < len(project_obj.get_observations()):
                    logger.error(f"Invalid observation_index {observation_index} for Project with {len(project_obj.get_observations())} observations")
                    return {}
                observation_obj = project_obj.get_observation(observation_index)
                nested_attrs = {k: v for k, v in attributes.items() if k != "observation_index"}
                return self._inspect_observation(observation_obj, nested_attrs)

            for getter_name, getter_args in attributes.items():
                value = self._validate_and_apply_getter(project_obj, getter_name, getter_args, valid_getters)
                if value is not None:
                    result[getter_name] = value

            if not result:
                logger.warning("No valid getters or nested inspection provided for Project")
                return {}

            logger.info(f"Successfully inspected Project: name='{project_obj.get_name()}'")
            return result
        except Exception as e:
            logger.error(f"Failed to inspect Project: {str(e)}")
            return {}

    def inspect(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Universal method to inspect an object using getter calls in a single attributes dictionary

        Args:
            obj: The object to inspect (e.g., IF, Frequencies, Source, Sources, Telescope, SpaceTelescope, Telescopes, Scan, Scans, Observation, Project)
            attributes: Dictionary where keys are getter names and values are their arguments (or None if no args).
                       Example: {"get_name": None}
                       For nested inspection: {"observation_index": 0, "get_observation_code": None}
                       For Project: {"get_observation": {"index": 0}}

        Returns:
            Dict[str, Any]: Dictionary with getter names as keys and their results as values

        Raises:
            ValueError: If the object type is not supported
        """
        if obj is None:
            logger.error("Inspection object cannot be None")
            raise ValueError("Inspection object cannot be None")

        inspection_methods = self._manipulator.get_registry_section("inspect")
        obj_type = type(obj)

        if obj_type not in inspection_methods:
            logger.error(f"Unsupported object type for inspection: {obj_type}")
            raise ValueError(f"Unsupported object type: {obj_type}")

        try:
            return inspection_methods[obj_type]["inspect_func"](obj, attributes)
        except Exception as e:
            logger.error(f"Failed to inspect {obj_type}: {str(e)}")
            return {}

    def __repr__(self) -> str:
        """String representation of Inspector"""
        return "Inspector()"

class DefaultInspector(Inspector):
    """Default implementation of Inspector for inspecting Project and its components"""
    def __init__(self, manipulator: 'Manipulator'):
        super().__init__(manipulator)
        logger.info("Initialized DefaultInspector")