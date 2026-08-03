from msb_arch.super.super import Super
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.base.frequencies import IF, Frequencies
from pastrocore.base.sources import Source, Sources
from pastrocore.base.telescopes import Telescope, SpaceTelescope, Telescopes
from pastrocore.base.scans import Scan, Scans
from pastrocore.base.observation import Observation
from msb_arch.utils.logging_setup import logger
from typing import Dict, Any, Union
from astropy.time import Time
import astropy.units as u
import uuid
import random

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
    OPERATION = "configure"

    def __init__(self, manipulator: 'Manipulator'):
        super().__init__(manipulator=manipulator)
        logger.debug("Initialized ScheduleConfigurator")

    def _configure_if(self, if_obj: IF, attributes: Dict[str, Any]) -> Any:
        """Configure an IF object and return its get() result."""
        self._apply_methods(if_obj, attributes)
        final_result = if_obj.get()
        logger.info(f"Configured IF: frequency={if_obj.frequency}, bandwidth={if_obj.bandwidth}, result={final_result}")
        return final_result


    def _configure_frequencies(self, freq_obj: Frequencies, attributes: Dict[str, Any]) -> Any:
        """Configure a Frequencies object, supporting nested IF configuration."""
        if "name" in attributes:
            result = self._do_nested(
                freq_obj, attributes, "name", freq_obj.get, self._configure_if
            )
            if result["status"]:
                logger.info(f"Configured nested IF in Frequencies: name={attributes['name']}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to configure nested IF in Frequencies: name={attributes.get('name')}")
            raise ValueError(result.get("error", "Operation not executed"))
        self._apply_methods(freq_obj, attributes)
        final_result = len(freq_obj)
        logger.info(f"Configured Frequencies: count={final_result}, result={final_result}")
        return final_result


    def _configure_source(self, source_obj: Source, attributes: Dict[str, Any]) -> Any:
        """Configure a Source object and return its get() result."""
        self._apply_methods(source_obj, attributes)
        final_result = source_obj.get()
        logger.info(f"Configured Source: name='{source_obj.name}', result={final_result}")
        return final_result


    def _configure_sources(self, sources_obj: Sources, attributes: Dict[str, Any]) -> Any:
        """Configure a Sources object, supporting nested Source configuration."""
        if "name" in attributes:
            result = self._do_nested(
                sources_obj, attributes, "name", sources_obj.get, self._configure_source
            )
            if result["status"]:
                logger.info(f"Configured nested Source in Sources: name={attributes['name']}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to configure nested Source in Sources: name={attributes.get('name')}")
            raise ValueError(result.get("error", "Operation not executed"))
        self._apply_methods(sources_obj, attributes)
        final_result = len(sources_obj)
        logger.info(f"Configured Sources: count={final_result}, result={final_result}")
        return final_result


    def _configure_telescope(self, tel_obj: Union[Telescope, SpaceTelescope], attributes: Dict[str, Any]) -> Any:
        """Configure a Telescope or SpaceTelescope object and return its code."""
        self._apply_methods(tel_obj, attributes)
        final_result = tel_obj.get_code()
        logger.info(f"Configured Telescope: code='{final_result}', result={final_result}")
        return final_result


    def _configure_telescopes(self, tel_obj: Telescopes, attributes: Dict[str, Any]) -> Any:
        """Configure a Telescopes object, supporting nested Telescope configuration."""
        if "name" in attributes:
            result = self._do_nested(
                tel_obj, attributes, "name", tel_obj.get, self._configure_telescope
            )
            if result["status"]:
                logger.info(f"Configured nested Telescope in Telescopes: name={attributes['name']}, result={result['result']}")
                return result["result"]
            logger.warning(f"Failed to configure nested Telescope in Telescopes: name={attributes.get('name')}")
            raise ValueError(result.get("error", "Operation not executed"))
        self._apply_methods(tel_obj, attributes)
        final_result = len(tel_obj)
        logger.info(f"Configured Telescopes: count={final_result}, result={final_result}")
        return final_result


    def _configure_scan(self, scan_obj: Scan, attributes: Dict[str, Any]) -> Any:
        """Configure a Scan object and return its get() result."""
        self._apply_methods(scan_obj, attributes)
        final_result = scan_obj.get()
        logger.info(f"Configured Scan: name='{scan_obj.name}', result={final_result}")
        return final_result


    def _configure_scans(self, scans_obj: Scans, attributes: Dict[str, Any]) -> Any:
        """Configure a Scans object and return the number of scans."""
        self._apply_methods(scans_obj, attributes)
        final_result = len(scans_obj)
        logger.info(f"Configured Scans: count={final_result}, result={final_result}")
        return final_result


    def _configure_observation(self, obs_obj: Observation, attributes: Dict[str, Any]) -> Any:
        """Configure an Observation object and return its code."""
        self._apply_methods(obs_obj, attributes)
        final_result = obs_obj.get_observation_code()
        logger.info(f"Configured Observation: code='{final_result}', result={final_result}")
        return final_result


    def _configure_scheduleproject(self, project_obj: ScheduleProject, attributes: Dict[str, Any]) -> Any:
        """Configure a ScheduleProject object, supporting nested Observation configuration and observation generation."""
        try:
            if "generate_observations" in attributes:
                logger.info(f"Generating observations for project {project_obj.name}.")
                result = self._generate_observations(project_obj, attributes["generate_observations"])
                logger.debug(f"Generated observations for ScheduleProject: {result}")
                return result

            if "name" in attributes:
                result = self._do_nested(
                    project_obj, attributes, "name", project_obj.get_observation, self._configure_observation
                )
                if result["status"]:
                    logger.info(f"Configured nested Observation in ScheduleProject: name={attributes['name']}, result={result['result']}")
                    return result["result"]
                logger.warning(f"Failed to configure nested Observation in ScheduleProject: name={attributes.get('name')}")
                raise ValueError(result.get("error", "Operation not executed"))

            self._apply_methods(project_obj, attributes)
            final_result = project_obj.get_name()
            logger.info(f"Configured ScheduleProject: name='{final_result}', observations={len(project_obj.get_items())}, result={final_result}")
            return final_result
        except Exception as e:
            logger.error(f"Error configuring ScheduleProject: {str(e)}")
            raise ValueError(str(e))


    def _generate_observations(self, project_obj: ScheduleProject, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Generate observations for the project based on provided attributes.

        Creates unique copies of Sources, Telescopes, Frequencies, and Scans for each observation.
        Scans use the source, telescopes, and frequencies from the created Observation object.
        Supports parallel (all observations start at the same time) or sequential (one after another) modes.
        Uses fixed interval between scan groups (on+off pairs or single scans).
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
                - parallel (bool): If True, generate observations in parallel; else sequential.
                - pattern (dict): Pattern settings including:
                    - add_off_source (bool): Add off-source scans.
                    - randomize_order (bool): Randomize scan order.
                    - interval_sec (int): Interval between scans in seconds.
                    - naming_mask (str): Naming pattern for observation codes.
                - progress_callback (Callable, optional): Callback to report progress (value, message).

        Returns:
            Dict[str, Any]: Dictionary with status, result (list of observation codes), and message or error.
        """
        generated_codes = []
        try:
            sources = attributes.get("sources", Sources())
            telescopes = attributes.get("telescopes", Telescopes())
            frequencies = attributes.get("frequencies", Frequencies())
            observation_type = attributes.get("observation_type", "VLBI")
            time_range = attributes.get("time_range", {})
            scan_duration = attributes.get("scan_duration", 300.0)
            num_scans = attributes.get("num_scans", 5)
            parallel = attributes.get("parallel", False)
            pattern = attributes.get("pattern", {})
            add_off_source = pattern.get("add_off_source", False)
            randomize_order = pattern.get("randomize_order", False)
            interval_sec = pattern.get("interval_sec", 300)
            naming_mask = pattern.get("naming_mask", "OBS_{s}_{uuid}")
            progress_callback = attributes.get("progress_callback", None)

            if observation_type not in ["VLBI", "SINGLE_DISH"]:
                logger.error(f"Invalid observation type: {observation_type}")
                return {"status": False, "error": f"Invalid observation type: {observation_type}", "result": []}

            if not isinstance(sources, Sources):
                logger.error(f"Expected Sources object, got {type(sources)}")
                return {"status": False, "error": f"Expected Sources object, got {type(sources)}", "result": []}
            if not isinstance(telescopes, Telescopes):
                logger.error(f"Expected Telescopes object, got {type(telescopes)}")
                return {"status": False, "error": f"Expected Telescopes object, got {type(telescopes)}", "result": []}
            if not isinstance(frequencies, Frequencies):
                logger.error(f"Expected Frequencies object, got {type(frequencies)}")
                return {"status": False, "error": f"Expected Frequencies object, got {type(frequencies)}", "result": []}

            source_items = sources.get_items()
            telescope_items = telescopes.get_items()
            frequency_items = frequencies.get_items()
            logger.debug(f"Input collections: sources={len(source_items)} ({[s.name for s in source_items]}), "
                        f"telescopes={len(telescope_items)} ({[t.name for t in telescope_items]}), "
                        f"frequencies={len(frequency_items)} ({[f.name for f in frequency_items]})")
            if not source_items:
                logger.error("No sources provided")
                return {"status": False, "error": "No sources provided", "result": []}
            if not telescope_items:
                logger.error("No telescopes provided")
                return {"status": False, "error": "No telescopes provided", "result": []}
            if not frequency_items:
                logger.error("No frequencies provided")
                return {"status": False, "error": "No frequencies provided", "result": []}

            if not time_range or "start" not in time_range or "end" not in time_range:
                logger.error("Invalid time range: missing start or end")
                return {"status": False, "error": "Invalid time range", "result": []}
            try:
                start_time = Time(time_range["start"])
                end_time = Time(time_range["end"])
            except Exception as e:
                logger.error(f"Invalid time format: {str(e)}")
                return {"status": False, "error": f"Invalid time format: {str(e)}", "result": []}
            if start_time >= end_time:
                logger.error("Invalid time range: start time must be before end time")
                return {"status": False, "error": "Invalid time range", "result": []}

            if observation_type == "SINGLE_DISH":
                if not telescope_items:
                    logger.error("No telescopes available for SINGLE_DISH")
                    return {"status": False, "error": "No telescopes available for SINGLE_DISH", "result": []}
                telescopes = Telescopes(items={telescope_items[0].name: telescope_items[0].copy()})
                logger.debug(f"SINGLE_DISH mode: selected telescope '{telescope_items[0].name}'")

            multiplier = 2 if add_off_source else 1
            scan_group_duration = multiplier * scan_duration
            step_sec = scan_group_duration + interval_sec
            required_duration_sec = scan_group_duration + (num_scans - 1) * step_sec if num_scans > 0 else 0

            time_tolerance = 0.1 * u.s

            total_sources = len(source_items)
            current_start = start_time

            for i, source in enumerate(source_items, 1):
                if attributes.get("cancelled", False):
                    logger.info("Observation generation cancelled")
                    return {"status": False, "error": "Observation generation cancelled", "result": []}

                if parallel:
                    obs_start = start_time
                else:
                    obs_start = current_start

                # Check if observation fits within the time range
                obs_end = obs_start + required_duration_sec * u.s
                if (obs_end - end_time) > time_tolerance:
                    logger.warning(f"Insufficient time for observation on source '{source.name}' "
                                f"(required: {required_duration_sec}s, available: {(end_time - obs_start).to_value('s')}s)")
                    continue

                sources_copy = Sources(name=f"srcs_{source.name}_{uuid.uuid4().hex[:8]}")
                sources_copy.add(source.copy())
                logger.debug(f"Created sources_copy with {len(sources_copy.get_items())} sources: "
                            f"{[s.name for s in sources_copy.get_items()]}")

                try:
                    iso_time = obs_start.iso
                    time_parts = iso_time.split(' ') if ' ' in iso_time else [iso_time, '']
                    obs_code = naming_mask.format(
                        i=i,
                        s=source.name,
                        dt=iso_time,
                        t=time_parts[1],
                        d=time_parts[0],
                        uuid=uuid.uuid4().hex[:8]
                    )
                except KeyError as e:
                    logger.error(f"Invalid naming mask: unknown placeholder {str(e)}")
                    return {"status": False, "error": f"Invalid naming mask: unknown placeholder {str(e)}", "result": []}
                except IndexError as e:
                    logger.error(f"Error formatting time in naming mask: {str(e)}")
                    return {"status": False, "error": f"Error formatting time in naming mask: {str(e)}", "result": []}

                obs_telescopes = telescopes.copy()
                obs_frequencies = frequencies.copy()
                obs_telescopes_items = obs_telescopes.get_items()
                obs_frequencies_items = obs_frequencies.get_items()
                logger.debug(f"Observation '{obs_code}': telescopes={len(obs_telescopes_items)} "
                            f"({[t.name for t in obs_telescopes_items]}), "
                            f"frequencies={len(obs_frequencies_items)} ({[f.name for f in obs_frequencies_items]})")
                if not obs_telescopes_items or not obs_frequencies_items:
                    logger.error(f"Empty telescopes or frequencies for observation '{obs_code}'")
                    continue

                obs = Observation(
                    code=obs_code,
                    name=obs_code,
                    sources=sources_copy,
                    telescopes=obs_telescopes,
                    frequencies=obs_frequencies,
                    scans=Scans(name=f"scans_{source.name}_{uuid.uuid4().hex[:8]}"),
                    observation_type=observation_type,
                    isactive=True
                )
                logger.debug(f"Created observation '{obs_code}' for source '{source.name}'")

                scans_list = []
                for j in range(num_scans):
                    scan_start = obs_start + (j * step_sec) * u.s
                    scan_name = f"scan_{source.name}_{j+1}_{uuid.uuid4().hex[:8]}"
                    scan_telescopes = obs.telescopes.get_items()
                    scan_frequencies = obs.frequencies.get_items()
                    if not scan_telescopes or not scan_frequencies:
                        logger.error(f"Empty telescopes or frequencies for scan '{scan_name}' in observation '{obs_code}'")
                        continue
                    scan = Scan(
                        name=scan_name,
                        source=source,
                        telescopes=scan_telescopes,
                        frequencies=scan_frequencies,
                        start=scan_start,
                        duration=scan_duration,
                        is_off_source=False,
                        isactive=True,
                        observation=obs
                    )
                    scans_list.append(scan)

                    if add_off_source:
                        off_scan_name = f"off_scan_{source.name}_{j+1}_{uuid.uuid4().hex[:8]}"
                        off_start = scan_start + scan_duration * u.s
                        off_scan = Scan(
                            name=off_scan_name,
                            source=source,
                            telescopes=scan_telescopes,
                            frequencies=scan_frequencies,
                            start=off_start,
                            duration=scan_duration,
                            is_off_source=True,
                            isactive=True,
                            observation=obs
                        )
                        scans_list.append(off_scan)

                if not scans_list:
                    logger.error(f"No scans generated for observation '{obs_code}'")
                    continue

                if randomize_order:
                    random.shuffle(scans_list)

                for scan in scans_list:
                    obs.scans.add(scan)

                self._configure_scheduleproject(project_obj, {
                    "add_item": {"item": obs}
                })

                added_obs = project_obj.get_observation_by_code(obs_code)
                if not added_obs:
                    logger.error(f"Failed to add observation '{obs_code}' for source '{source.name}' to project")
                    continue

                generated_codes.append(obs_code)
                logger.info(f"Generated observation '{obs_code}' for source '{source.name}' with {len(scans_list)} scans")

                if not parallel:
                    current_start = obs_end

                if progress_callback and callable(progress_callback):
                    progress_value = int((i / total_sources) * 100)
                    progress_message = f"Generated observation {i}/{total_sources}: {obs_code}"
                    progress_callback(progress_value, progress_message)
                    logger.debug(f"Progress callback: {progress_value}% - {progress_message}")

            if not generated_codes:
                logger.error("No observations generated")
                return {"status": False, "error": "No observations generated", "result": []}

            logger.info(f"Successfully generated {len(generated_codes)} observations")
            return {
                "status": True,
                "result": generated_codes,
                "message": f"Generated {len(generated_codes)} observations"
            }

        except Exception as e:
            logger.error(f"Error generating observations: {str(e)}. Generated {len(generated_codes)} observations before failure")
            return {"status": False, "error": f"Error generating observations: {str(e)}", "result": []}