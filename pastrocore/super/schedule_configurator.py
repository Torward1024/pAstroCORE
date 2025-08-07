from common.super.super import Super
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.frequencies import IF, Frequencies
from pastrocore.base.sources import Source, Sources
from pastrocore.base.telescopes import Telescope, SpaceTelescope, Telescopes
from pastrocore.base.scans import Scan, Scans
from pastrocore.base.observation import Observation
from common.utils.logging_setup import logger
from typing import Dict, Any, Union
from astropy.time import Time
import astropy.units as u
import uuid

class ScheduleConfigurator(Super):
    """Implementation of Configurator for configuring scheduling entities using the Super framework.

    Provides methods to configure astronomical scheduling entities with validation and nested configuration support.
    Integrates with Manipulator for method validation. Returns the result of the final method called on the object
    (e.g., get, get_code) as the result in the response dictionary.

    Args:
        manipulator: The Manipulator instance for method lookup and validation.

    Returns:
        Dict[str, Any]: A dictionary with results of the configuration operation, managed by Super.execute.
    """
    def __init__(self, manipulator: 'Manipulator'):
        super().__init__(manipulator=manipulator)
        self._operation = "configure"
        logger.info("Initialized ScheduleConfigurator")

    def _configure_if(self, if_obj: IF, attributes: Dict[str, Any]) -> Any:
        """Configure an IF object and return its get() result."""
        valid_methods = self._get_methods(IF)
        applied = False
        for method_name, method_args in attributes.items():
            result = self._validate_and_apply_method(if_obj, method_name, method_args, valid_methods)
            if result["status"]:
                applied = True
            else:
                logger.warning(f"Invalid method '{method_name}' for IF configuration: {result['error']}")
                raise ValueError(result["error"])
        if not applied:
            logger.warning("No valid methods applied for IF configuration")
            raise ValueError("No valid methods applied")
        final_result = if_obj.get()
        logger.info(f"Configured IF: frequency={if_obj.frequency}, bandwidth={if_obj.bandwidth}, result={final_result}")
        return final_result

    def _configure_frequencies(self, freq_obj: Frequencies, attributes: Dict[str, Any]) -> Any:
        """Configure a Frequencies object, supporting nested IF configuration."""
        if "name" in attributes:
            name = attributes["name"]
            if_obj = freq_obj.get(name)
            if if_obj is None:
                logger.error(f"IF '{name}' not found in Frequencies")
                raise ValueError(f"Name '{name}' not found in Frequencies")
            result = self._do_nested(
                freq_obj, attributes, "name", lambda k: freq_obj.get(k), self._configure_if
            )
            if result["status"]:
                logger.info(f"Configured nested IF in Frequencies: name={attributes['name']}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to configure nested IF in Frequencies: name={attributes.get('name')}")
            raise ValueError(result.get("error", "Operation not executed"))
        valid_methods = self._get_methods(Frequencies)
        applied = False
        for method_name, method_args in attributes.items():
            result = self._validate_and_apply_method(freq_obj, method_name, method_args, valid_methods)
            if result["status"]:
                applied = True
        if not applied:
            logger.warning("No valid methods applied for Frequencies configuration")
            raise ValueError("No valid methods applied")
        final_result = len(freq_obj)
        logger.info(f"Configured Frequencies: count={final_result}, result={final_result}")
        return final_result

    def _configure_source(self, source_obj: Source, attributes: Dict[str, Any]) -> Any:
        """Configure a Source object and return its get() result."""
        valid_methods = self._get_methods(Source)
        applied = False
        for method_name, method_args in attributes.items():
            result = self._validate_and_apply_method(source_obj, method_name, method_args, valid_methods)
            if result["status"]:
                applied = True
        if not applied:
            logger.warning("No valid methods applied for Source configuration")
            raise ValueError("No valid methods applied")
        final_result = source_obj.get()
        logger.info(f"Configured Source: name='{source_obj.name}', result={final_result}")
        return final_result

    def _configure_sources(self, sources_obj: Sources, attributes: Dict[str, Any]) -> Any:
        """Configure a Sources object, supporting nested Source configuration."""
        if "name" in attributes:
            name = attributes["name"]
            source_obj = sources_obj.get(name)
            if source_obj is None:
                logger.error(f"Source '{name}' not found in Sources")
                raise ValueError(f"Name '{name}' not found in Sources")
            result = self._do_nested(
                sources_obj, attributes, "name", lambda k: sources_obj.get(k), self._configure_source
            )
            if result["status"]:
                logger.info(f"Configured nested Source in Sources: name={attributes['name']}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to configure nested Source in Sources: name={attributes.get('name')}")
            raise ValueError(result.get("error", "Operation not executed"))
        valid_methods = self._get_methods(Sources)
        applied = False
        for method_name, method_args in attributes.items():
            result = self._validate_and_apply_method(sources_obj, method_name, method_args, valid_methods)
            if result["status"]:
                applied = True
        if not applied:
            logger.warning("No valid methods applied for Sources configuration")
            raise ValueError("No valid methods applied")
        final_result = len(sources_obj)
        logger.info(f"Configured Sources: count={final_result}, result={final_result}")
        return final_result

    def _configure_telescope(self, tel_obj: Union[Telescope, SpaceTelescope], attributes: Dict[str, Any]) -> str:
        """Configure a Telescope or SpaceTelescope object and return its get_code() result."""
        obj_type = type(tel_obj)
        valid_methods = self._get_methods(obj_type)
        applied = False
        for method_name, method_args in attributes.items():
            result = self._validate_and_apply_method(tel_obj, method_name, method_args, valid_methods)
            if result["status"]:
                applied = True
        if not applied:
            logger.warning(f"No valid methods applied for {obj_type.__name__} configuration")
            raise ValueError("No valid methods applied")
        final_result = tel_obj.get_code()
        logger.info(f"Configured {obj_type.__name__}: code='{final_result}', result={final_result}")
        return final_result

    def _configure_telescopes(self, tel_obj: Telescopes, attributes: Dict[str, Any]) -> Any:
        """Configure a Telescopes object, supporting nested Telescope configuration."""
        if "name" in attributes:
            name = attributes["name"]
            telescope_obj = tel_obj.get(name)
            if telescope_obj is None:
                logger.error(f"Telescope '{name}' not found in Telescopes")
                raise ValueError(f"Name '{name}' not found in Telescopes")
            result = self._do_nested(
                tel_obj, attributes, "name", lambda k: tel_obj.get(k), self._configure_telescope
            )
            if result["status"]:
                logger.info(f"Configured nested Telescope in Telescopes: name={attributes['name']}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to configure nested Telescope in Telescopes: name={attributes.get('name')}")
            raise ValueError(result.get("error", "Operation not executed"))
        valid_methods = self._get_methods(Telescopes)
        applied = False
        for method_name, method_args in attributes.items():
            result = self._validate_and_apply_method(tel_obj, method_name, method_args, valid_methods)
            if result["status"]:
                applied = True
        if not applied:
            logger.warning("No valid methods applied for Telescopes configuration")
            raise ValueError("No valid methods applied")
        final_result = len(tel_obj)
        logger.info(f"Configured Telescopes: count={final_result}, result={final_result}")
        return final_result

    def _configure_scan(self, scan_obj: Scan, attributes: Dict[str, Any]) -> Any:
        """Configure a Scan object, optionally validating with an observation, and return its get() result."""
        valid_methods = self._get_methods(Scan)
        applied = False
        observation = attributes.get("observation")
        for method_name, method_args in attributes.items():
            if method_name == "observation":
                continue
            extra_args = {"observation": observation} if observation else None
            result = self._validate_and_apply_method(scan_obj, method_name, method_args, valid_methods, extra_args)
            if result["status"]:
                applied = True
                if observation and not scan_obj.validate_with_observation(observation):
                    logger.error(f"Scan invalid after {method_name}: observation='{observation.get_observation_code()}'")
                    raise ValueError(f"Scan invalid after {method_name}")
        if not applied:
            logger.warning("No valid methods applied for Scan configuration")
            raise ValueError("No valid methods applied")
        final_result = scan_obj.get()
        source_str = "OFF SOURCE" if scan_obj.is_off_source else f"source_name={scan_obj.get_source_name()}"
        logger.info(f"Configured Scan: start={scan_obj.get_start().isot}, {source_str}, result={final_result}")
        return final_result

    def _configure_scans(self, scans_obj: Scans, attributes: Dict[str, Any]) -> Any:
        """Configure a Scans object, checking for overlaps in nested Scan changes."""
        if "name" in attributes:
            name = attributes["name"]
            scan_obj = scans_obj.get(name)
            if scan_obj is None:
                logger.error(f"Scan '{name}' not found in Scans")
                raise ValueError(f"Name '{name}' not found in Scans")
            if not isinstance(scan_obj, Scan):
                logger.error(f"Object with name '{name}' is not a Scan, got {type(scan_obj).__name__}")
                raise ValueError(f"Object with name '{name}' is not a Scan")
            nested_attrs = {k: v for k, v in attributes.items() if k != "name"}
            result = self._configure_scan(scan_obj, nested_attrs)
            overlap, reason = scans_obj._check_overlap(scan_obj, exclude_name=name)
            if overlap:
                logger.error(f"Modified scan '{name}' {reason}")
                raise ValueError(f"Modified scan '{name}' {reason}")
            logger.info(f"Configured nested Scan in Scans: name={name}, result={result}")
            return result
        valid_methods = self._get_methods(Scans)
        applied = False
        for method_name, method_args in attributes.items():
            result = self._validate_and_apply_method(scans_obj, method_name, method_args, valid_methods)
            if result["status"]:
                applied = True
        if not applied:
            logger.warning("No valid methods applied for Scans configuration")
            raise ValueError("No valid methods applied")
        final_result = len(scans_obj)
        logger.info(f"Configured Scans: count={final_result}, result={final_result}")
        return final_result

    def _configure_observation(self, obs_obj: Observation, attributes: Dict[str, Any]) -> str:
        """Configure an Observation object, validating its state, and return its get_observation_code() result."""
        valid_methods = self._get_methods(Observation)
        applied = False
        for method_name, method_args in attributes.items():
            result = self._validate_and_apply_method(obs_obj, method_name, method_args, valid_methods)
            if result["status"]:
                applied = True
            else:
                logger.warning(f"Invalid method '{method_name}' for Observation configuration")
                raise ValueError(result["error"])
        if not applied:
            logger.warning("No valid methods applied for Observation configuration")
            raise ValueError("No valid methods applied")
        if not obs_obj.validate():
            logger.error(f"Observation '{obs_obj.get_observation_code()}' invalid after configuration")
            raise ValueError("Observation invalid after configuration")
        final_result = obs_obj.get_observation_code()
        logger.info(f"Configured Observation: code='{final_result}', result={final_result}")
        return final_result

    def _configure_scheduleproject(self, project_obj: ScheduleProject, attributes: Dict[str, Any]) -> Any:
        """Configure a ScheduleProject object, supporting nested Observation configuration and observation generation."""
        try:
            if "generate_observations" in attributes:
                result = self._generate_observations(project_obj, attributes["generate_observations"])
                logger.info(f"Generated observations for ScheduleProject: {result}")
                return result

            if "name" in attributes:
                name = attributes["name"]
                obs_obj = project_obj.get_observation(name)
                if obs_obj is None:
                    logger.error(f"Observation '{name}' not found in ScheduleProject")
                    raise ValueError(f"Name '{name}' not found in ScheduleProject")
                result = self._do_nested(
                    project_obj, attributes, "name", lambda k: project_obj.get_observation(k), self._configure_observation
                )
                if result["status"]:
                    logger.info(f"Configured nested Observation in ScheduleProject: name={attributes['name']}, result={result['result']}")
                    return result["result"]
                logger.warning(f"Failed to configure nested Observation in ScheduleProject: name={attributes.get('name')}")
                raise ValueError(result.get("error", "Operation not executed"))

            valid_methods = self._get_methods(ScheduleProject)
            applied = False
            for method_name, method_args in attributes.items():
                result = self._validate_and_apply_method(project_obj, method_name, method_args, valid_methods)
                if result["status"]:
                    applied = True
                else:
                    logger.warning(f"Invalid method '{method_name}' for ScheduleProject configuration: {result['error']}")
                    raise ValueError(result["error"])
            if not applied:
                logger.warning("No valid methods applied for ScheduleProject configuration")
                raise ValueError("No valid methods applied")
            final_result = project_obj.get_name()
            logger.info(f"Configured ScheduleProject: name='{final_result}', observations={len(project_obj.get_items())}, result={final_result}")
            return final_result
        except Exception as e:
            logger.error(f"Error configuring ScheduleProject: {str(e)}")
            raise ValueError(str(e))

    def _configure_if(self, if_obj: IF, attributes: Dict[str, Any]) -> Any:
        """Configure an IF object and return its get() result."""
        valid_methods = self._get_methods(IF)
        applied = False
        for method_name, method_args in attributes.items():
            result = self._validate_and_apply_method(if_obj, method_name, method_args, valid_methods)
            if result["status"]:
                applied = True
            else:
                logger.warning(f"Invalid method '{method_name}' for IF configuration: {result['error']}")
                raise ValueError(result["error"])
        if not applied:
            logger.warning("No valid methods applied for IF configuration")
            raise ValueError("No valid methods applied")
        final_result = if_obj.get()
        logger.info(f"Configured IF: frequency={if_obj.frequency}, bandwidth={if_obj.bandwidth}, result={final_result}")
        return final_result

    def _generate_observations(self, project_obj: ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Generate observations for the project based on provided attributes.

        Creates unique copies of Sources, Telescopes, Frequencies, and Scans for each observation.
        Scans use the source, telescopes, and frequencies from the created Observation object.
        Emits progress updates via an optional callback function.

        Args:
            project_obj (ScheduleProject): The project to add observations to.
            attributes (Dict[str, Any]): Dictionary containing:
                - sources (Sources): Sources object containing source items.
                - telescopes (Telescopes): Telescopes object containing telescope items.
                - frequencies (Frequencies): Frequencies object containing IF items.
                - observation_type (str): Type of observation ('VLBI' or 'SINGLE_DISH').
                - time_range (dict): Dictionary with 'start' and 'end' times (datetime).
                - scan_duration (float): Duration of each scan in seconds.
                - num_scans (int): Number of scans per observation.
                - progress_callback (Callable, optional): Callback to report progress (value, message).

        Returns:
            Dict[str, Any]: Dictionary with status, result (list of observation codes), and message or error.
        """
        try:
            sources = attributes.get("sources", Sources())
            telescopes = attributes.get("telescopes", Telescopes())
            frequencies = attributes.get("frequencies", Frequencies())
            observation_type = attributes.get("observation_type", "VLBI")
            time_range = attributes.get("time_range", {})
            scan_duration = attributes.get("scan_duration", 300.0)
            num_scans = attributes.get("num_scans", 5)
            progress_callback = attributes.get("progress_callback", None)

            if observation_type not in ["VLBI", "SINGLE_DISH"]:
                logger.error(f"Invalid observation type: {observation_type}")
                return {"status": False, "error": f"Invalid observation type: {observation_type}"}

            # Validate input objects
            if not isinstance(sources, Sources):
                logger.error(f"Expected Sources object, got {type(sources)}")
                return {"status": False, "error": f"Expected Sources object, got {type(sources)}"}
            if not isinstance(telescopes, Telescopes):
                logger.error(f"Expected Telescopes object, got {type(telescopes)}")
                return {"status": False, "error": f"Expected Telescopes object, got {type(telescopes)}"}
            if not isinstance(frequencies, Frequencies):
                logger.error(f"Expected Frequencies object, got {type(frequencies)}")
                return {"status": False, "error": f"Expected Frequencies object, got {type(frequencies)}"}

            if not sources.get_all():
                logger.error("No sources provided")
                return {"status": False, "error": "No sources provided"}
            if not telescopes.get_all():
                logger.error("No telescopes provided")
                return {"status": False, "error": "No telescopes provided"}
            if not frequencies.get_all():
                logger.error("No frequencies provided")
                return {"status": False, "error": "No frequencies provided"}

            if not time_range or "start" not in time_range or "end" not in time_range:
                logger.error("Invalid time range: missing start or end")
                return {"status": False, "error": "Invalid time range"}

            try:
                start_time = Time(time_range["start"])
                end_time = Time(time_range["end"])
            except Exception as e:
                logger.error(f"Invalid time format: {str(e)}")
                return {"status": False, "error": f"Invalid time format: {str(e)}"}

            if start_time >= end_time:
                logger.error("Invalid time range: start time must be before end time")
                return {"status": False, "error": "Invalid time range"}

            generated_codes = []
            source_items = sources.get_items()
            total_sources = len(source_items)

            for i, source in enumerate(source_items, 1):
                if attributes.get("cancelled", False):
                    logger.info("Observation generation cancelled")
                    return {"status": False, "error": "Observation generation cancelled"}

                # Create unique Sources object with a copy of the current source
                sources_copy = Sources(name=f"Source_{source.name}_{uuid.uuid4().hex[:8]}")
                sources_copy.add(source.copy())

                # Create Observation with copied objects
                obs_code = f"OBS_{source.name}_{uuid.uuid4().hex[:8]}"
                obs = Observation(
                    code=obs_code,
                    name=obs_code,
                    sources=sources_copy,
                    telescopes=telescopes.copy(),
                    frequencies=frequencies.copy(),
                    scans=Scans(name=f"Scans_{source.name}_{uuid.uuid4().hex[:8]}"),
                    observation_type=observation_type,
                    isactive=True
                )
                logger.debug(f"Created observation '{obs_code}' for source '{source.name}'")

                total_duration = (end_time - start_time).sec
                if total_duration < scan_duration * num_scans:
                    logger.warning(f"Time range too short for {num_scans} scans of {scan_duration}s for source '{source.name}'")
                    continue

                time_step = total_duration / num_scans
                for j in range(num_scans):
                    scan_start = start_time + (j * time_step) * u.s
                    scan_name = f"scan_{source.name}_{j+1}_{uuid.uuid4().hex[:8]}"
                    scan = Scan(
                        name=scan_name,
                        source=obs.sources.get_items()[0],
                        telescopes=obs.telescopes.get_items(),
                        frequencies=obs.frequencies.get_items(),
                        start=scan_start,
                        duration=scan_duration,
                        isactive=True
                    )
                    obs.scans.add(scan)
                    logger.debug(f"Created scan '{scan_name}' for source '{source.name}'")

                self._configure_scheduleproject(project_obj, {
                    "add_item": {"item": obs}
                })

                added_obs = project_obj.get_observation_by_code(obs_code)
                if not added_obs:
                    logger.error(f"Failed to add observation '{obs_code}' for source '{source.name}' to project")
                    continue

                generated_codes.append(obs_code)
                logger.info(f"Generated observation '{obs_code}' for source '{source.name}' with {num_scans} scans")

                if progress_callback and callable(progress_callback):
                    progress_value = int((i / total_sources) * 100)
                    progress_message = f"Generated observation {i}/{total_sources}: {obs_code}"
                    progress_callback(progress_value, progress_message)
                    logger.debug(f"Progress callback: {progress_value}% - {progress_message}")

            return {
                "status": True,
                "result": generated_codes,
                "message": f"Generated {len(generated_codes)} observations"
            }

        except Exception as e:
            logger.error(f"Error generating observations: {str(e)}")
            return {"status": False, "error": str(e)}