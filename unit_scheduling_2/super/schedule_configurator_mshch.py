from common.super.super import Super
from unit_scheduling_2.super.schedule_project import ScheduleProject
from unit_scheduling_2.base.frequencies import IF, Frequencies
from unit_scheduling_2.base.sources import Source, Sources
from unit_scheduling_2.base.telescopes import Telescope, SpaceTelescope, Telescopes
from unit_scheduling_2.base.scans import Scan, Scans
from unit_scheduling_2.base.observation import Observation
from common.utils.logging_setup import logger
from typing import Dict, Any, Union, Callable


class ScheduleConfigurator(Super):
    """Implementation of Configurator for configuring scheduling entities using the Super framework."""
    CONFIGURATION_MAP = {
        "IF": ("_configure_object", "get"),
        "Frequencies": ("_configure_container", "len", "IF", "get"),
        "Source": ("_configure_object", "get"),
        "Sources": ("_configure_container", "len", "Source", "get"),
        "Telescope": ("_configure_object", "get_code"),
        "Telescopes": ("_configure_container", "len", "Telescope", "get_code"),
        "Scan": ("_configure_object", "get"),
        "Scans": ("_configure_container", "len", "Scan", "get"),
        "Observation": ("_configure_object", "get_observation_code"),
        "ScheduleProject": ("_configure_container", "get_name", "Observation", "get_observation_code"),
    }

    def __init__(self, manipulator: 'Manipulator'):
        super().__init__(manipulator=manipulator)
        self._operation = "configure"
        logger.info("Initialized ScheduleConfigurator")

    def _configure_object(self, obj: Any, attributes: Dict[str, Any], final_method: str, 
                          validator: Callable = None, extra_args: Dict[str, Any] = None) -> Any:
        valid_methods = self._get_methods(type(obj))
        applied = False
        for method_name, method_args in attributes.items():
            if method_name == "name":
                continue
            result = self._validate_and_apply_method(obj, method_name, method_args, valid_methods, extra_args)
            if result["status"]:
                applied = True
            else:
                raise ValueError(result["error"])
        if not applied:
            raise ValueError("No methods were applied")
        if validator and not validator():
            raise ValueError("Validation failed after configuration")
        final_result = getattr(obj, final_method)()
        logger.info(f"Configured {type(obj).__name__}: result={final_result}")
        return final_result

    def _configure_container(self, container: Any, attributes: Dict[str, Any], 
                             item_type: str, item_final_method: str, container_final_method: str) -> Any:
        if "name" in attributes:
            name = attributes["name"]
            item_obj = container.get(name)
            if item_obj is None:
                raise ValueError(f"Item '{name}' not found in {container.__class__.__name__}")
            item_config_method = self.CONFIGURATION_MAP[item_type][0]
            config_method = getattr(self, item_config_method, None)
            if config_method is None:
                raise NotImplementedError(f"Configuration method for {item_type} not implemented")
            nested_attrs = {k: v for k, v in attributes.items() if k != "name"}
            return config_method(item_obj, nested_attrs, item_final_method)
        else:
            valid_methods = self._get_methods(type(container))
            applied = False
            for method_name, method_args in attributes.items():
                logger.debug(f"Processing method '{method_name}' with args {method_args} for container {container.__class__.__name__}")
                if method_name in valid_methods and isinstance(method_args, dict):
                    obj_key = next((k for k in method_args if k.endswith('_obj')), None)
                    if obj_key:
                        logger.debug(f"Extracting object from '{obj_key}': {method_args[obj_key]}")
                        result = self._validate_and_apply_method(container, method_name, method_args[obj_key], valid_methods)
                    else:
                        result = self._validate_and_apply_method(container, method_name, method_args, valid_methods)
                else:
                    result = self._validate_and_apply_method(container, method_name, method_args, valid_methods)
                logger.debug(f"Result of applying '{method_name}': {result}")
                if result["status"]:
                    applied = True
                else:
                    logger.error(f"Failed to apply method '{method_name}': {result['error']}")
                    raise ValueError(result["error"])
            if not applied:
                raise ValueError("No methods were applied")
            final_result = getattr(container, container_final_method)()
            logger.info(f"Сконфигурирован {container.__class__.__name__}: результат={final_result}")
            return final_result

    def _configure_if(self, if_obj: IF, attributes: Dict[str, Any]) -> Any:
        return self._configure_object(if_obj, attributes, "get")

    def _configure_frequencies(self, freq_obj: Frequencies, attributes: Dict[str, Any]) -> Any:
        return self._configure_container(freq_obj, attributes, "IF", "get", "len")

    def _configure_source(self, source_obj: Source, attributes: Dict[str, Any]) -> Any:
        return self._configure_object(source_obj, attributes, "get")

    def _configure_sources(self, sources_obj: Sources, attributes: Dict[str, Any]) -> Any:
        return self._configure_container(sources_obj, attributes, "Source", "get", "len")

    def _configure_telescope(self, tel_obj: Union[Telescope, SpaceTelescope], attributes: Dict[str, Any]) -> str:
        return self._configure_object(tel_obj, attributes, "get_code")

    def _configure_telescopes(self, tel_obj: Telescopes, attributes: Dict[str, Any]) -> Any:
        return self._configure_container(tel_obj, attributes, "Telescope", "get_code", "len")

    def _configure_scan(self, scan_obj: Scan, attributes: Dict[str, Any]) -> Any:
        observation = attributes.get("observation")
        validator = lambda: scan_obj.validate_with_observation(observation) if observation else True
        extra_args = {"observation": observation} if observation else None
        return self._configure_object(scan_obj, attributes, "get", validator=validator, extra_args=extra_args)

    def _configure_scans(self, scans_obj: Scans, attributes: Dict[str, Any]) -> Any:
        result = self._configure_container(scans_obj, attributes, "Scan", "get", "len")
        if "name" in attributes:
            name = attributes["name"]
            scan_obj = scans_obj.get(name)
            overlap, reason = scans_obj._check_overlap(scan_obj, exclude_name=name)
            if overlap:
                raise ValueError(f"Scan '{name}' overlaps: {reason}")
        return result

    def _configure_observation(self, obs_obj: Observation, attributes: Dict[str, Any]) -> str:
        validator = lambda: obs_obj.validate()
        return self._configure_object(obs_obj, attributes, "get_observation_code", validator=validator)

    def _configure_scheduleproject(self, project_obj: ScheduleProject, attributes: Dict[str, Any]) -> Any:
        return self._configure_container(project_obj, attributes, "Observation", "get_observation_code", "get_name")