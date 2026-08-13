# base/scans.py
from msb_arch.base.baseentity import BaseEntity
from msb_arch.base.basecontainer import BaseContainer
from msb_arch.utils.validation import check_type, check_positive
from msb_arch.utils.logging_setup import logger
from .frequencies import IF, Frequencies
from .sources import Source
from .telescopes import Telescope, SpaceTelescope, Telescopes
import numpy as np
from typing import Optional, List, Dict, Union
from astropy.time import Time
import astropy.units as u
import uuid

class Scan(BaseEntity):
    """Base class representing a single observation scan with timing, source, telescopes, and frequencies."""
    name: str
    start: Time
    duration: float
    source: Optional[Source]
    telescopes: List[Union[Telescope, SpaceTelescope]]
    frequencies: List[IF]
    is_off_source: bool

    def __init__(self, name: str = None, start: Time = None, duration: float = 1.0, source: Optional[Source] = None,
             telescopes: List[Union[Telescope, SpaceTelescope]] = None, frequencies: List[IF] = None,
             is_off_source: bool = False, isactive: bool = True, observation: 'Observation' = None):
        """Initialize a Scan with name, start time, duration, and references to observation entities."""
        if start is None:
            start = Time.now()
        start = Time(start.iso.split('.')[0], format='iso')
        if name is None:
            name = f"scan_{uuid.uuid4().hex[:32]}"
        check_type(start, Time, "Start time")
        check_positive(duration, "Duration")
        if source is not None:
            check_type(source, Source, "Source")
        if telescopes is None:
            telescopes = []
        if frequencies is None:
            frequencies = []
        check_type(telescopes, list, "Telescopes")
        check_type(frequencies, list, "Frequencies")
        for t in telescopes:
            check_type(t, (Telescope, SpaceTelescope), "Telescope")
        for f in frequencies:
            check_type(f, IF, "Frequency")
        super().__init__(
            name=name,
            start=start,
            duration=duration,
            source=source,
            telescopes=telescopes,
            frequencies=frequencies,
            is_off_source=source is None or is_off_source,
            isactive=isactive
        )
        if observation:
            from pastrocore.base.observation import Observation
            check_type(observation, Observation, "Observation")
            if source is not None:
                sources = observation.get_sources()
                source_from_obs = sources.get(source.name)
                if source_from_obs:
                    self.source = source_from_obs
                    logger.debug("Set scan '%s' source to reference '%s' from observation", name, source.name)
                else:
                    logger.error("Source '%s' not found in observation sources", source.name)
                    raise ValueError(f"Invalid source '{source.name}' for observation")
            isactive = self._check_activity_status(observation)
            if isactive != self.isactive:
                self.set({"isactive": isactive})
                logger.debug("Set scan '%s' isactive=%s based on initial validation", name, isactive)
        source_str = "OFF SOURCE" if self.is_off_source else f"source={source.name if source else None}"
        logger.info("Initialized Scan with name=%s, start=%s, duration=%s, %s", name, self.start.isot, duration, source_str)
    
    def check_activity_status(self, observation: 'Observation') -> bool:
        from pastrocore.base.observation import Observation
        """Public method to check activity status."""
        return self._check_activity_status(observation)
    
    def copy(self) -> 'Scan':
        """Create a deep copy of the Scan object."""
        return Scan(
            start=self.start,
            duration=self.duration,
            source=self.source,
            telescopes=self.telescopes.copy(),
            frequencies=self.frequencies.copy(),
            is_off_source=self.is_off_source,
            isactive=self.isactive
        )
    
    def _check_activity_status(self, observation: 'Observation') -> bool:
        """Check if the scan is active based on telescope, frequency, and source availability."""
        from pastrocore.base.observation import Observation
        check_type(observation, Observation, "Observation")
        observation_type = observation.get_observation_type()
        min_telescopes = 1 if observation_type == "SINGLE_DISH" else 2
        active_telescopes = [t for t in self.telescopes if t.isactive]
        active_frequencies = [f for f in self.frequencies if f.isactive]
        source_active = (
            self.is_off_source or
            self.source is None or
            (self.source in observation.get_sources().get_items() and self.source.isactive)
        )
        logger.debug(self.source)
        logger.debug(observation.get_sources().get_items())
        should_be_active = (
            len(active_telescopes) >= min_telescopes and
            len(active_frequencies) >= 1 and
            source_active
        )
        logger.debug("Activity check for scan '%s': telescope_count=%s (min=%s), frequency_count=%s, source_active=%s, should_be_active=%s", self.name, len(active_telescopes), min_telescopes, len(active_frequencies), source_active, should_be_active)
        return should_be_active

    def get_start(self) -> Time:
        """Retrieve the start time of the scan."""
        return self.get("start")

    def get_end(self) -> Time:
        """Retrieve the end time of the scan."""
        end_time = self.start + self.duration * u.s
        return Time(end_time.iso.split('.')[0], format='iso')

    def get_MJD_starttime(self) -> float:
        """Retrieve the start time in Modified Julian Date (MJD)."""
        return self.start.mjd

    def get_MJD_endtime(self) -> float:
        """Retrieve the end time in Modified Julian Date (MJD)."""
        return (self.start + self.duration * u.s).mjd

    def get_duration(self) -> float:
        """Retrieve the duration of the scan."""
        return self.get("duration")

    def get_source_name(self) -> str:
        """Retrieve the source name."""
        return self.source.name

    def get_telescope_names(self) -> List[str]:
        """Retrieve the list of telescope names."""
        return self.get("telescope_names")

    def get_frequency_names(self) -> List[str]:
        """Retrieve the list of frequency names."""
        return self.get("frequency_names")

    def get_source(self, observation: 'Observation') -> Source:
        """Retrieve the source associated with this scan."""
        from pastrocore.base.observation import Observation
        check_type(observation, Observation, "Observation")
        return self.source

    def get_telescopes(self, observation: 'Observation') -> Telescopes:
        """Retrieve the telescopes associated with this scan."""
        from pastrocore.base.observation import Observation
        check_type(observation, Observation, "Observation")
        return Telescopes(items={t.name: t for t in self.telescopes})

    def get_frequencies(self, observation: 'Observation') -> Frequencies:
        """Retrieve the frequencies associated with this scan."""
        from pastrocore.base.observation import Observation
        check_type(observation, Observation, "Observation")
        return Frequencies(items={f.name: f for f in self.frequencies})

    def set_start(self, start: Time) -> None:
        """Set the start time of the scan."""
        check_type(start, Time, "Start time")
        start = Time(start.iso.split('.')[0], format='iso')
        self.set({"start": start})
        logger.info("Set scan start to %s", start.isot)

    def set_duration(self, duration: float) -> None:
        """Set the duration of the scan."""
        check_positive(duration, "Duration")
        self.set({"duration": duration})
        logger.info("Set scan duration to %s", duration)

    def set_source(self, source: Optional[Source], observation: 'Observation' = None) -> None:
        """Set the source for the scan."""
        if source is not None:
            check_type(source, Source, "Source")
        if observation:
            from pastrocore.base.observation import Observation
            check_type(observation, Observation, "Observation")
            if source is not None:
                sources = observation.get_sources()
                source_from_obs = sources.get(source.name)
                if source_from_obs:
                    source = source_from_obs
                    logger.debug("Set scan '%s' source to reference '%s' from observation", self.name, source.name)
                else:
                    logger.error("Source '%s' not found in observation sources", source.name)
                    raise ValueError(f"Invalid source '{source.name}' for observation")
        self.set({"source": source, "is_off_source": source is None})
        if observation:
            self.validate_with_observation(observation)
        logger.info("Set scan source to %s", 'OFF SOURCE' if source is None else source.name)

    def set_telescopes(self, telescopes: List[Union[Telescope, SpaceTelescope]], observation: 'Observation' = None) -> None:
        """Set the telescopes for the scan."""
        check_type(telescopes, list, "Telescopes")
        for t in telescopes:
            check_type(t, (Telescope, SpaceTelescope), "Telescope")
        self.set({"telescopes": telescopes})
        if observation:
            self.validate_with_observation(observation)
        logger.info("Set scan telescopes to %s for scan '%s'", [t.name for t in telescopes], self.name)

    def set_frequencies(self, frequencies: List[IF], observation: 'Observation' = None) -> None:
        """Set the frequencies for the scan."""
        check_type(frequencies, list, "Frequencies")
        for f in frequencies:
            check_type(f, IF, "Frequency")
        self.set({"frequencies": frequencies})
        if observation:
            self.validate_with_observation(observation)
        logger.info("Set scan frequencies to %s for scan '%s'", [f.name for f in frequencies], self.name)

    def validate_with_observation(self, observation: 'Observation') -> bool:
        """Validate scan attributes against an observation.

        Ensures that telescopes and frequencies exist in the observation. For off-source scans,
        allows source to be None. Updates activity status based on observation context.

        Args:
            observation (Observation): The observation to validate against.

        Returns:
            bool: True if the scan is valid or can be made valid (e.g., off-source), False if critical validation fails.

        Raises:
            TypeError: If observation is not of type Observation.
        """
        from pastrocore.base.observation import Observation
        check_type(observation, Observation, "Observation")
        
        if self.source is not None and not self.is_off_source:
            sources = observation.get_sources()
            source_from_obs = sources.get(self.source.name)
            if source_from_obs is None:
                logger.warning("Source '%s' not found in observation, setting scan '%s' to off-source", self.source.name, self.name)
                self.set({"source": None, "is_off_source": True, "isactive": False})
            else:
                if self.source is not source_from_obs:
                    self.source = source_from_obs
                    logger.debug("Synced scan '%s' source '%s' with observation reference", self.name, self.source.name)
        
        valid_telescopes = []
        observation_telescopes = observation.get_telescopes()
        for telescope in self.telescopes:
            telescope_from_obs = observation_telescopes.get(telescope.name)
            if telescope_from_obs:
                valid_telescopes.append(telescope_from_obs)
            else:
                logger.warning("Telescope '%s' not found in observation, removed from scan '%s'", telescope.name, self.name)
        self.set({"telescopes": valid_telescopes})
        
        valid_frequencies = []
        observation_frequencies = observation.get_frequencies()
        for freq in self.frequencies:
            frequency_from_obs = observation_frequencies.get(freq.name)
            if frequency_from_obs:
                valid_frequencies.append(frequency_from_obs)
            else:
                logger.warning("Frequency '%s' not found in observation, removed from scan '%s'", freq.name, self.name)
        self.set({"frequencies": valid_frequencies})
        
        if not valid_telescopes:
            logger.warning("Scan '%s' has no valid telescopes assigned", self.name)
        if not valid_frequencies:
            logger.warning("Scan '%s' has no valid frequencies assigned", self.name)
        
        should_be_active = self._check_activity_status(observation)
        if should_be_active != self.isactive:
            self.set({"isactive": should_be_active})
            logger.debug("%s scan '%s' based on validation", 'Activated' if should_be_active else 'Deactivated', self.name)
        
        logger.debug("Validated scan '%s' with start=%s against observation '%s', is_off_source=%s, isactive=%s", self.name, self.start.isot, observation.get_observation_code(), self.is_off_source, self.isactive)
        return True
    
    def sync_with_observation(self, observation: 'Observation') -> bool:
        """Synchronize scan attributes with the provided observation.

        Updates source, telescopes, and frequencies to match references in the observation,
        validates the scan, and updates its activity status. If the source is not found,
        sets the scan to off-source and deactivates it.

        Args:
            observation (Observation): The observation to synchronize with.


        Returns:
            bool: True if synchronization is successful, False if critical validation fails.

        Raises:
            TypeError: If observation is not of type Observation.
        """
        from pastrocore.base.observation import Observation
        check_type(observation, Observation, "Observation")
        logger.debug("Starting synchronization for scan '%s' with observation '%s'", self.name, observation.get_observation_code())

        if self.source is not None and not self.is_off_source:
            sources = observation.get_sources()
            source_from_obs = sources.get(self.source.name)
            if source_from_obs:
                self.source = source_from_obs
                logger.debug("Synchronized scan '%s' source to '%s' (isactive=%s)", self.name, self.source.name, self.source.isactive)
            else:
                logger.warning("Source '%s' not found in observation sources, setting scan '%s' to off-source and deactivating", self.source.name, self.name)
                self.set({"source": None, "is_off_source": True, "isactive": False})

        observation_telescopes = observation.get_telescopes()
        valid_telescopes = []
        for telescope in self.telescopes:
            telescope_from_obs = observation_telescopes.get(telescope.name)
            if telescope_from_obs:
                valid_telescopes.append(telescope_from_obs)
                logger.debug("Synchronized telescope '%s' for scan '%s'", telescope.name, self.name)
            else:
                logger.warning("Telescope '%s' not found in observation, removing from scan '%s'", telescope.name, self.name)
        self.set({"telescopes": valid_telescopes})

        observation_frequencies = observation.get_frequencies()
        valid_frequencies = []
        for frequency in self.frequencies:
            frequency_from_obs = observation_frequencies.get(frequency.name)
            if frequency_from_obs:
                valid_frequencies.append(frequency_from_obs)
                logger.debug("Synchronized frequency '%s' for scan '%s'", frequency.name, self.name)
            else:
                logger.warning("Frequency '%s' not found in observation, removing from scan '%s'", frequency.name, self.name)
        self.set({"frequencies": valid_frequencies})

        is_valid = self.validate_with_observation(observation)
        if not is_valid:
            logger.error("Synchronization failed for scan '%s': validation against observation '%s' failed", self.name, observation.get_observation_code())
            return False

        logger.info("Successfully synchronized scan '%s' with observation '%s'", self.name, observation.get_observation_code())
        return True

    def to_dict(self) -> dict:
        """Convert the Scan object to a dictionary, serializing Time as ISO string."""
        data = super().to_dict()
        data["start"] = self.start.isot
        data["source"] = self.source.name if self.source else None
        data["telescopes"] = [t.name for t in self.telescopes]
        data["frequencies"] = [f.name for f in self.frequencies]
        # Debug, not info: freshness fingerprints the scans on every check, so this is emitted
        # several times per calculation and says nothing a reader of the log wants.
        logger.debug("Converted scan '%s' with start=%s to dictionary", self.name, self.start.isot)
        return data

    @classmethod
    def from_dict(cls, data: dict, observation: 'Observation' = None) -> 'Scan':
        """Create a Scan object from a dictionary, parsing ISO string to Time and resolving objects from Observation.

        Ensures the source reference is synchronized with the observation and activity status is validated.
        """
        from pastrocore.base.observation import Observation
        data = data.copy()
        start_time = Time(data.pop("start"))
        start_time = Time(start_time.iso.split('.')[0], format='iso')
        source_name = data.pop("source", None)
        telescope_names = data.pop("telescopes", [])
        frequency_names = data.pop("frequencies", [])
        is_off_source = data.pop("is_off_source", False)
        data.pop("type", None)

        source = None
        if observation and source_name and not is_off_source:
            check_type(observation, Observation, "Observation")
            sources = observation.get_sources()
            source = sources.get(source_name)
            if source:
                logger.debug("Resolved source '%s' for scan from observation, isactive=%s", source_name, source.isactive)
            else:
                logger.error("Source '%s' not found in observation sources", source_name)
                raise ValueError(f"Source '{source_name}' not found in observation sources")
        elif source_name and not observation:
            logger.error("Cannot resolve source '%s' without observation context", source_name)
            raise ValueError(f"Cannot resolve source '{source_name}' without observation context")

        telescopes = []
        if observation and telescope_names:
            all_telescopes = observation.get_telescopes()
            for name in telescope_names:
                telescope = all_telescopes.get(name)
                if telescope:
                    telescopes.append(telescope)
                    logger.debug("Resolved telescope '%s' for scan", name)
                else:
                    logger.warning("Telescope '%s' not found in observation telescopes", name)
        elif telescope_names:
            logger.warning("No observation provided, cannot resolve telescopes: %s", telescope_names)

        frequencies = []
        if observation and frequency_names:
            all_frequencies = observation.get_frequencies()
            for name in frequency_names:
                frequency = all_frequencies.get(name)
                if frequency:
                    frequencies.append(frequency)
                    logger.debug("Resolved frequency '%s' for scan", name)
                else:
                    logger.warning("Frequency '%s' not found in observation frequencies", name)
        elif frequency_names:
            logger.warning("No observation provided, cannot resolve frequencies: %s", frequency_names)

        scan = cls(
            name=data.get("name", f"scan_{uuid.uuid4().hex[:32]}"),
            start=start_time,
            duration=data.get("duration", 1.0),
            source=source,
            telescopes=telescopes,
            frequencies=frequencies,
            is_off_source=is_off_source,
            isactive=data.get("isactive", True),
            observation=observation
        )
        
        if observation:
            scan.validate_with_observation(observation)
            logger.debug("After validation: scan '%s' source=%s, isactive=%s, source_isactive=%s", scan.name, source_name, scan.isactive, scan.source.isactive if scan.source else None)
        logger.info("Created scan '%s' with start=%s, source=%s, telescopes=%s, frequencies=%s", scan.name, scan.start.isot, 'OFF SOURCE' if is_off_source else source_name or 'None', [t.name for t in telescopes] if telescopes else [], [f.name for f in frequencies] if frequencies else [])
        return scan

class Scans(BaseContainer[Scan]):
    """Base class representing a collection of Scan objects."""
    def __init__(self, items: Dict[str, Scan] = None, name: str = None, isactive: bool = True, use_cache: bool = False):
        """Initialize a Scans object with an optional dictionary of Scan objects."""
        if name is None:
            name = f"scans_{uuid.uuid4().hex[:32]}"
        super().__init__(items=items, name=name, isactive=isactive)
        self._key_cache = list(self._items.keys()) if items else []
        logger.info("Initialized Scans with name=%s, %s scans", name, len(self._items))

    def add(self, scan: Scan, observation: 'Observation' = None) -> None:
        """Add a Scan object to the collection with overlap checking."""
        from pastrocore.base.observation import Observation
        check_type(scan, Scan, "Scan")
        if observation:
            check_type(observation, Observation, "Observation")
            if not scan.validate_with_observation(observation):
                logger.error("Scan '%s' failed validation against observation '%s'", scan.name, observation.get_observation_code())
                raise ValueError("Scan validation failed")
            should_be_active = scan._check_activity_status(observation)
            if should_be_active != scan.isactive:
                scan.set({"isactive": should_be_active})
                logger.debug("Set scan '%s' isactive=%s during add", scan.name, should_be_active)
        overlap, reason = self._check_overlap(scan)
        if overlap:
            logger.error("Scan '%s' with start=%s, duration=%s %s", scan.name, scan.get_start().isot, scan.get_duration(), reason)
            raise ValueError(f"Scan conflicts: {reason}")
        super().add(scan)
        self._key_cache.append(scan.name)
        logger.info("Added scan '%s' with start=%s to Scans", scan.name, scan.get_start().isot)

    def remove(self, name: str) -> None:
        """Remove a scan by its name."""
        super().remove(name)
        self._key_cache = list(self._items.keys())
        logger.info("Removed scan '%s' from Scans", name)

    def create_scan(self, name: str = None, start: Time = None, duration: float = 1.0, source: Optional[Source] = None,
                    telescopes: List[Union[Telescope, SpaceTelescope]] = None, frequencies: List[IF] = None,
                    is_off_source: bool = False, isactive: bool = True, observation: 'Observation' = None) -> None:
        """Create and add a new Scan object to the collection."""
        scan = Scan(
            name=name,
            start=start,
            duration=duration,
            source=source,
            telescopes=telescopes,
            frequencies=frequencies,
            is_off_source=is_off_source,
            isactive=isactive,
            observation=observation
        )
        self.add(scan, observation)
    
    def set_scan(
        self,
        name: str,
        start: Optional[Time] = None,
        duration: Optional[float] = None,
        source: Optional[Source] = None,
        telescopes: Optional[List[Union[Telescope, SpaceTelescope]]] = None,
        frequencies: Optional[List[IF]] = None,
        is_off_source: Optional[bool] = None,
        isactive: Optional[bool] = None,
        observation: 'Observation' = None
    ) -> None:
        """Update an existing Scan object in the collection with new parameters."""
        from pastrocore.base.observation import Observation
        if name not in self._items:
            logger.error("Scan with name '%s' not found in Scans", name)
            raise KeyError(f"Scan with name '{name}' not found in Scans")
        scan = self._items[name]
        temp_start = start if start is not None else scan.start
        temp_duration = duration if duration is not None else scan.duration
        temp_source = source if source is not None else scan.source
        temp_telescopes = telescopes if telescopes is not None else scan.telescopes
        temp_frequencies = frequencies if frequencies is not None else scan.frequencies
        temp_is_off_source = is_off_source if is_off_source is not None else scan.is_off_source
        temp_isactive = isactive if isactive is not None else scan.isactive
        check_type(temp_start, Time, "Start time")
        check_positive(temp_duration, "Duration")
        if temp_source is not None:
            check_type(temp_source, Source, "Source")
        check_type(temp_telescopes, list, "Telescopes")
        check_type(temp_frequencies, list, "Frequencies")
        for t in temp_telescopes:
            check_type(t, (Telescope, SpaceTelescope), "Telescope")
        for f in temp_frequencies:
            check_type(f, IF, "Frequency")
        temp_scan = Scan(
            name=name,
            start=temp_start,
            duration=temp_duration,
            source=temp_source,
            telescopes=temp_telescopes,
            frequencies=temp_frequencies,
            is_off_source=temp_is_off_source,
            isactive=temp_isactive,
            observation=observation
        )
        overlap, reason = self._check_overlap(temp_scan, exclude_name=name)
        if overlap:
            logger.error("Updated scan '%s' %s", name, reason)
            raise ValueError(f"Scan update conflicts: {reason}")
        if observation:
            check_type(observation, Observation, "Observation")
            if not temp_scan.validate_with_observation(observation):
                logger.error("Updated scan '%s' failed validation against observation '%s'", name, observation.get_observation_code())
                raise ValueError("Scan validation failed")
        params = {}
        if start is not None:
            params["start"] = start
        if duration is not None:
            params["duration"] = duration
        if source is not None or is_off_source is not None:
            params["source"] = temp_source
            params["is_off_source"] = temp_is_off_source
        if telescopes is not None:
            params["telescopes"] = telescopes
        if frequencies is not None:
            params["frequencies"] = frequencies
        if isactive is not None:
            params["isactive"] = isactive
        if params:
            scan.set(params)
            logger.info("Updated scan '%s' in Scans with params: %s", name, params)
            if observation and isactive is None:
                should_be_active = scan._check_activity_status(observation)
                scan.set({"isactive": should_be_active})
                logger.debug("Scan '%s' %s based on validation", name, 'activated' if should_be_active else 'deactivated')
        else:
            logger.debug("No parameters to update for scan '%s' in Scans", name)

    def deactivate_all(self) -> None:
        """Deactivate all scans in the collection."""
        deactivated_count = 0
        for scan in self.get_items():
            if scan.isactive:
                scan.set({"isactive": False})
                deactivated_count += 1
                logger.debug("Deactivated scan '%s' in Scans '%s'", scan.name, self.name)
        logger.info("Deactivated %s scans in Scans '%s'", deactivated_count, self.name)

    def activate_all(self, observation: 'Observation') -> None:
        """Activate all scans in the collection that satisfy activity conditions."""
        from pastrocore.base.observation import Observation
        check_type(observation, Observation, "Observation")
        
        activated_count = 0
        skipped_count = 0
        
        for scan in self.get_items():
            should_be_active = scan._check_activity_status(observation)
            if should_be_active and not scan.isactive:
                scan.set({"isactive": True})
                activated_count += 1
                logger.debug("Activated scan '%s' in Scans '%s'", scan.name, self.name)
            elif not should_be_active and scan.isactive:
                scan.set({"isactive": False})
                skipped_count += 1
                logger.debug("Deactivated scan '%s' in Scans '%s' as it does not meet activity conditions", scan.name, self.name)
            elif not should_be_active:
                skipped_count += 1
                logger.debug("Skipped scan '%s' in Scans '%s' as it does not meet activity conditions", scan.name, self.name)
            else:
                logger.debug("Scan '%s' in Scans '%s' already active and meets conditions", scan.name, self.name)
        
        logger.info("Activated %s scans, skipped or deactivated %s scans in Scans '%s'", activated_count, skipped_count, self.name)

    def get_active_scans(self, observation: 'Observation' = None) -> List[Scan]:
        """Retrieve all active scans, optionally filtering by entity activity in an Observation."""
        from pastrocore.base.observation import Observation
        active = []
        for scan in self.get_items():
            if not scan.isactive:
                logger.debug("Scan '%s' is not active, skipping", scan.name)
                continue
            if observation is None:
                active.append(scan)
                logger.debug("Scan '%s' included as active (no observation context)", scan.name)
                continue
            check_type(observation, Observation, "Observation")
            if scan._check_activity_status(observation):
                active.append(scan)
                logger.debug("Scan '%s' included as active based on activity status", scan.name)
            else:
                logger.debug("Scan '%s' excluded due to failing activity status check", scan.name)
        logger.debug(f"Retrieved {len(active)} active scans" + 
                    (f" for observation '{observation.get_observation_code()}'" if observation else ""))
        return active

    def get_inactive_scans(self) -> List[Scan]:
        """Retrieve all inactive scans."""
        inactive = [s for s in self.get_items() if not s.isactive]
        logger.debug("Retrieved %s inactive scans", len(inactive))
        return inactive
    
    def copy(self) -> 'Scans':
        """Create a deep copy of the Scans object."""
        return Scans(
            name=self.name,
            items={name: item.copy() for name, item in self._items.items()},
            isactive=self.isactive,
            use_cache=self._use_cache
        )

    def _check_overlap(self, scan: Scan, exclude_name: str = None) -> tuple[bool, str]:
        """Check if a scan overlaps with existing active scans by time."""
        for name, existing in self._items.items():
            if name == exclude_name or not existing.isactive or not scan.isactive:
                continue
            scan_start = scan.get_start()
            scan_end = scan.get_end()
            existing_start = existing.get_start()
            existing_end = existing.get_end()
            time_overlap = (existing_start < scan_end and scan_start < existing_end)
            if time_overlap:
                reason = (f"overlaps with scan '{name}' (start={existing_start.isot}, "
                          f"duration={existing.get_duration()})")
                logger.debug("Overlap detected: %s", reason)
                return True, reason
        logger.debug("No overlap detected for scan '%s' with start=%s", scan.name, scan.get_start().isot)
        return False, ""
    
    @classmethod
    def from_dict(cls, data: dict, observation: 'Observation' = None) -> 'Scans':
        """Create a Scans object from a dictionary."""
        from pastrocore.base.observation import Observation
        items = {}
        for scan_data in data.get("items", {}).values():
            scan = Scan.from_dict(scan_data, observation=observation)
            items[scan.name] = scan
        scans = cls(
            name=data.get("name", f"scans_{uuid.uuid4().hex[:32]}"),
            items=items,
            isactive=data.get("isactive", True),
            use_cache=data.get("use_cache", False)
        )
        logger.info("Created Scans '%s' with %s scans from dictionary", scans.name, len(items))
        return scans

    def __repr__(self) -> str:
        """Return a string representation of the Scans object."""
        active_count = len(self.get_active_scans())
        attrs = [f"name={self.name!r}" if self.name else ""]
        attrs.append(f"count={len(self._items)}")
        attrs.append(f"active={active_count}")
        attrs.append(f"inactive={len(self._items) - active_count}")
        return f"Scans({', '.join(attr for attr in attrs if attr)})"