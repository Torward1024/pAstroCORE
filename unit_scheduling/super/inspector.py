# /super/inspector.py
from common.super.super import Super
from unit_scheduling.super.schedule_project import ScheduleProject
from unit_scheduling.base.frequencies import IF, Frequencies
from unit_scheduling.base.sources import Source, Sources
from unit_scheduling.base.telescopes import Telescope, SpaceTelescope, Telescopes
from unit_scheduling.base.scans import Scan, Scans
from unit_scheduling.base.observation import Observation
from common.utils.logging_setup import logger
from typing import Dict, Any, Union

class ScheduleInspector(Super):
    """Default implementation of Inspector for inspecting Project and its components
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
    def __init__(self, manipulator: 'Manipulator'):
        super().__init__(manipulator)
        logger.info("Initialized Scheduling Inspector")

    def _default_result(self) -> Dict[str, Any]:
        return {}
    
    def _inspect_if(self, if_obj: IF, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect an IF object"""
        valid_getters = self._manipulator.get_methods_for_type(IF)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(if_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters provided for IF inspection")
            return {}
        logger.info(f"Successfully inspected IF: freq={if_obj.get_frequency()} MHz")
        return result

    def _inspect_frequencies(self, freq_obj: Frequencies, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Frequencies object"""
        result = self._inspect_nested(freq_obj, attributes, "if_index", freq_obj.get_by_index, self._inspect_if)
        if result:
            return result
        valid_getters = self._manipulator.get_methods_for_type(Frequencies)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(freq_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters provided for Frequencies inspection")
            return {}
        logger.info(f"Successfully inspected Frequencies: count={len(freq_obj)}")
        return result

    def _inspect_source(self, source_obj: Source, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Source object"""
        valid_getters = self._manipulator.get_methods_for_type(Source)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(source_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters provided for Source inspection")
            return {}
        logger.info(f"Successfully inspected Source: name='{source_obj.get_name()}'")
        return result

    def _inspect_sources(self, sources_obj: Sources, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Sources object"""
        result = self._inspect_nested(sources_obj, attributes, "source_index", sources_obj.get_by_index, self._inspect_source)
        if result:
            return result
        valid_getters = self._manipulator.get_methods_for_type(Sources)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(sources_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters provided for Sources inspection")
            return {}
        logger.info(f"Successfully inspected Sources: count={len(sources_obj)}")
        return result

    def _inspect_telescope(self, telescope_obj: Union[Telescope, SpaceTelescope], attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Telescope or SpaceTelescope object"""
        obj_type = type(telescope_obj)
        valid_getters = self._manipulator.get_methods_for_type(obj_type)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(telescope_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning(f"No valid getters provided for {obj_type.__name__} inspection")
            return {}
        logger.info(f"Successfully inspected {obj_type.__name__}: code='{telescope_obj.get_code()}'")
        return result

    def _inspect_telescopes(self, telescopes_obj: Telescopes, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Telescopes object"""
        result = self._inspect_nested(telescopes_obj, attributes, "telescope_index", telescopes_obj.get_by_index, self._inspect_telescope)
        if result:
            return result
        valid_getters = self._manipulator.get_methods_for_type(Telescopes)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(telescopes_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters provided for Telescopes inspection")
            return {}
        logger.info(f"Successfully inspected Telescopes: count={len(telescopes_obj)}")
        return result

    def _inspect_scan(self, scan_obj: Scan, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Scan object"""
        valid_getters = self._manipulator.get_methods_for_type(Scan)
        result = {}
        for getter_name, getter_args in attributes.items():
            if getter_name in {"get_source", "get_telescopes", "get_frequencies", "check_telescope_availability"}:
                if not getter_args or "observation" not in getter_args:
                    logger.error(f"Getter {getter_name} requires an 'observation' argument for Scan")
                    continue
                if not isinstance(getter_args["observation"], Observation):
                    logger.error(f"Argument 'observation' for {getter_name} must be an Observation object")
                    continue
            value = self._validate_and_apply_method(scan_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters provided for Scan inspection")
            return {}
        logger.info(f"Successfully inspected Scan: start={scan_obj.get_start()}")
        return result

    def _inspect_scans(self, scans_obj: Scans, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Scans object"""
        result = self._inspect_nested(scans_obj, attributes, "scan_index", scans_obj.get_by_index, self._inspect_scan)
        if result:
            return result
        valid_getters = self._manipulator.get_methods_for_type(Scans)
        result = {}
        for getter_name, getter_args in attributes.items():
            if getter_name == "get_active_scans" and getter_args and "observation" in getter_args:
                if not isinstance(getter_args["observation"], Observation):
                    logger.error(f"Argument 'observation' for {getter_name} must be an Observation object")
                    continue
            value = self._validate_and_apply_method(scans_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters provided for Scans inspection")
            return {}
        logger.info(f"Successfully inspected Scans: count={len(scans_obj)}")
        return result

    def _inspect_observation(self, obs_obj: Observation, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect an Observation object"""
        valid_getters = self._manipulator.get_methods_for_type(Observation)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(obs_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters provided for Observation inspection")
            return {}
        logger.info(f"Successfully inspected Observation: code='{obs_obj.get_observation_code()}'")
        return result

    def _inspect_project(self, project_obj: ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Project object"""
        result = self._inspect_nested(project_obj, attributes, "observation_index", project_obj.get_by_index, self._inspect_observation)
        if result:
            return result
        valid_getters = self._manipulator.get_methods_for_type(ScheduleProject)
        result = {}
        for getter_name, getter_args in attributes.items():
            value = self._validate_and_apply_method(project_obj, getter_name, getter_args, valid_getters)
            if value is not None:
                result[getter_name] = value
        if not result:
            logger.warning("No valid getters provided for Project inspection")
            return {}
        logger.info(f"Successfully inspected Project: name='{project_obj.get_name()}'")
        return result