# base/scans.py
from common.base.baseentity import BaseEntity
from common.base.basecontainer import BaseContainer
from common.utils.validation import check_type, check_positive
from common.utils.logging_setup import logger
from .frequencies import Frequencies
from .sources import Source
from .telescopes import Telescopes, SpaceTelescope
import numpy as np
from typing import Optional, List, Dict
from astropy.time import Time
import astropy.units as u
import uuid

class Scan(BaseEntity):
    """Base class representing a single observation scan with timing, source, telescopes, and frequencies."""
    name: str
    start: Time
    duration: float
    source_name: Optional[str]
    telescope_names: List[str]
    frequency_names: List[str]
    is_off_source: bool
    original_source_name: Optional[str]
    original_telescope_names: Optional[List[str]]
    original_frequency_names: Optional[List[str]]

    def __init__(self, name: str = None, start: Time = None, duration: float = 1.0, source_name: Optional[str] = None,
                 telescope_names: List[str] = None, frequency_names: List[str] = None,
                 is_off_source: bool = False, isactive: bool = True, observation: 'Observation' = None):
        """Initialize a Scan with name, start time, duration, and names referencing Observation data."""
        if start is None:
            start = Time.now()
        if name is None:
            name = f"scan_{uuid.uuid4().hex[:32]}"
        check_type(start, Time, "Start time")
        check_positive(duration, "Duration")
        if source_name is not None:
            check_type(source_name, str, "Source name")
        if telescope_names is None:
            telescope_names = []
        if frequency_names is None:
            frequency_names = []
        super().__init__(
            name=name,
            start=start,
            duration=duration,
            source_name=source_name,
            telescope_names=telescope_names,
            frequency_names=frequency_names,
            is_off_source=source_name is None or is_off_source,
            original_source_name=source_name,  # Set original_source_name
            original_telescope_names=telescope_names.copy() if telescope_names else None,
            original_frequency_names=frequency_names.copy() if frequency_names else None,
            isactive=isactive,
        )

        # Check activity status if observation is provided
        if observation:
            from pastrocore.base.observation import Observation
            check_type(observation, Observation, "Observation")
            isactive = self._check_activity_status(observation)
            if isactive != self.isactive:
                self.set({"isactive": isactive})
                logger.debug(f"Set scan '{name}' isactive={isactive} based on initial validation")

        source_str = "OFF SOURCE" if self.is_off_source else f"source_name={source_name}" if source_name else "no source"
        logger.info(f"Initialized Scan with name={name}, start={self.start.isot}, duration={duration}, {source_str}")
    
    def check_activity_status(self, observation: 'Observation') -> bool:
        from pastrocore.base.observation import Observation
        """Public method to check activity status."""
        return self._check_activity_status(observation)
    
    def _check_activity_status(self, observation: 'Observation') -> bool:
        from pastrocore.base.observation import Observation
        check_type(observation, Observation, "Observation")

        observation_type = observation.get_observation_type()
        min_telescopes = 1 if observation_type == "SINGLE_DISH" else 2
        logger.debug(f"Checking activity for scan '{self.name}', observation_type={observation_type}, min_telescopes={min_telescopes}")

        # Check telescope count
        telescope_items = observation.get_telescopes().get_items()  # List[Telescope]
        active_telescopes = [
            name for name in self.telescope_names
            if any(t.name == name and t.isactive for t in telescope_items)
        ]
        logger.debug(f"Scan '{self.name}' telescope_names={self.telescope_names}, active_telescopes={active_telescopes}, "
                    f"telescope_items_names={[t.name for t in telescope_items if hasattr(t, 'name')]}")

        # Check frequency count
        frequency_items = observation.get_frequencies().get_items()  # List[Frequency]
        active_frequencies = [
            name for name in self.frequency_names
            if any(f.name == name and f.isactive for f in frequency_items)
        ]
        logger.debug(f"Scan '{self.name}' frequency_names={self.frequency_names}, active_frequencies={active_frequencies}, "
                    f"frequency_items_names={[f.name for f in frequency_items if hasattr(f, 'name')]}")

        # Check source status
        source_items = observation.get_sources().get_items()  # List[Source]
        source_active = (
            self.source_name is None or self.is_off_source or
            any(s.name == self.source_name and s.isactive for s in source_items)
        )
        logger.debug(f"Scan '{self.name}' source_name={self.source_name}, is_off_source={self.is_off_source}, "
                    f"source_active={source_active}, source_items_names={[s.name for s in source_items if hasattr(s, 'name')]}")

        # Determine activity status
        should_be_active = (
            len(active_telescopes) >= min_telescopes and
            len(active_frequencies) >= 1 and
            source_active
        )

        logger.debug(f"Activity check for scan '{self.name}': "
                    f"telescope_count={len(active_telescopes)} (min={min_telescopes}), "
                    f"frequency_count={len(active_frequencies)}, "
                    f"source_active={source_active}, should_be_active={should_be_active}")
        return should_be_active

    def get_start(self) -> Time:
        """Retrieve the start time of the scan."""
        return self.get("start")

    def get_end(self) -> Time:
        """Retrieve the end time of the scan."""
        return self.start + self.duration * u.s

    def get_MJD_starttime(self) -> float:
        """Retrieve the start time in Modified Julian Date (MJD)."""
        return self.start.mjd

    def get_MJD_endtime(self) -> float:
        """Retrieve the end time in Modified Julian Date (MJD)."""
        return (self.start + self.duration * u.s).mjd

    def get_duration(self) -> float:
        """Retrieve the duration of the scan."""
        return self.get("duration")

    def get_source_name(self) -> Optional[str]:
        """Retrieve the source name."""
        return self.get("source_name")

    def get_telescope_names(self) -> List[str]:
        """Retrieve the list of telescope names."""
        return self.get("telescope_names")

    def get_frequency_names(self) -> List[str]:
        """Retrieve the list of frequency names."""
        return self.get("frequency_names")

    def get_source(self, observation: 'Observation') -> Optional[Source]:
        """Retrieve the source associated with this scan from an Observation."""
        from pastrocore.base.observation import Observation
        check_type(observation, Observation, "Observation")
        if self.source_name is None or self.is_off_source:
            return None
        sources = observation.get_sources()
        return sources.get(self.source_name)

    def get_telescopes(self, observation: 'Observation') -> Telescopes:
        """Retrieve the telescopes associated with this scan from an Observation."""
        from pastrocore.base.observation import Observation
        check_type(observation, Observation, "Observation")
        all_tels = observation.get_telescopes()
        selected = {name: t for name in self.telescope_names if (t := all_tels.get(name))}
        return Telescopes(items=selected)

    def get_frequencies(self, observation: 'Observation') -> Frequencies:
        from pastrocore.base.observation import Observation
        check_type(observation, Observation, "Observation")
        all_freqs = observation.get_frequencies()
        selected = {name: f for name in self.frequency_names if (f := all_freqs.get(name))}
        return Frequencies(items=selected)

    def set_start(self, start: Time) -> None:
        """Set the start time of the scan."""
        check_type(start, Time, "Start time")
        self.set({"start": start})
        logger.info(f"Set scan start to {start.isot}")

    def set_duration(self, duration: float) -> None:
        """Set the duration of the scan."""
        check_positive(duration, "Duration")
        self.set({"duration": duration})
        logger.info(f"Set scan duration to {duration}")

    def set_source_name(self, source_name: str, observation: 'Observation' = None) -> None:
        """Set the source name for the scan."""
        if source_name is not None:
            check_type(source_name, str, "Source name")
        params = {"source_name": source_name, "is_off_source": source_name is None}
        self.set(params)
        if observation:
            self.validate_with_observation(observation)
        logger.info(f"Set scan source_name to {'OFF SOURCE' if source_name is None else source_name}")

    def set_telescope_names(self, telescope_names: List[str], observation: 'Observation' = None) -> None:
        """Set the telescope names for the scan."""
        check_type(telescope_names, list, "Telescope names")
        if not self.original_telescope_names:
            self.set({"original_telescope_names": self.telescope_names.copy()})
        self.set({"telescope_names": telescope_names})
        if observation:
            self.validate_with_observation(observation)
        logger.info(f"Set scan telescope_names to {telescope_names}")

    def set_frequency_names(self, frequency_names: List[str], observation: 'Observation' = None) -> None:
        """Set the frequency names for the scan."""
        check_type(frequency_names, list, "Frequency names")
        if not self.original_frequency_names:
            self.set({"original_frequency_names": self.frequency_names.copy()})
        self.set({"frequency_names": frequency_names})
        if observation:
            self.validate_with_observation(observation)
        logger.info(f"Set scan frequency_names to {frequency_names}")

    def validate_with_observation(self, observation: 'Observation') -> bool:
        """Validate the scan's names against an Observation's data."""
        from pastrocore.base.observation import Observation
        check_type(observation, Observation, "Observation")
        
        if self.source_name is not None and not observation.get_sources().get(self.source_name):
            logger.error(f"Invalid source_name {self.source_name} for observation")
            return False
        
        all_tels = observation.get_telescopes()
        for name in self.telescope_names:
            if not all_tels.get(name):
                logger.error(f"Invalid telescope_name {name} for observation")
                return False
        
        all_freqs = observation.get_frequencies()
        for name in self.frequency_names:
            if not all_freqs.get(name):
                logger.error(f"Invalid frequency_name {name} for observation")
                return False
                
        logger.debug(f"Validated scan '{self.name}' with start={self.start.isot} against observation '{observation.get_observation_code()}'")
        return True

    def check_telescope_availability(self, observation: 'Observation', time: Time = None) -> dict[str, bool]:
        """Check telescope availability for this scan at a given time."""
        from pastrocore.base.observation import Observation
        check_type(observation, Observation, "Observation")
        if time is not None:
            check_type(time, Time, "Time")
        time = time if time is not None else self.start
        availability = {}
        source = self.get_source(observation) if not self.is_off_source else None
        
        for telescope in self.get_telescopes(observation).get_active_items():
            code = telescope.get_code()
            if self.is_off_source:
                availability[code] = True
                continue
            ra_rad = np.radians(source.ra_degrees)
            dec_rad = np.radians(source.dec_degrees)
            lst = (time.sidereal_time('apparent', 'greenwich').degree + 280.46061837) % 360
            if isinstance(telescope, SpaceTelescope):
                pos, _ = telescope.get_state_vector(time)
                dist = np.linalg.norm(pos)
                visible = dist < 1e9
                pitch_range = telescope.get_pitch_range()
                yaw_range = telescope.get_yaw_range()
                visible = (visible and 
                           pitch_range[0] <= 0 <= pitch_range[1] and 
                           yaw_range[0] <= 0 <= yaw_range[1])
            else:
                x, y, z = telescope.get_coordinates()
                lat = np.arcsin(z / np.sqrt(x**2 + y**2 + z**2))
                ha = np.radians(lst - source.ra_degrees)
                alt = np.arcsin(np.sin(lat) * np.sin(dec_rad) + 
                                np.cos(lat) * np.cos(dec_rad) * np.cos(ha))
                az = np.arctan2(
                    -np.sin(ha) * np.cos(dec_rad),
                    np.cos(lat) * np.sin(dec_rad) - np.sin(lat) * np.cos(dec_rad) * np.cos(ha)
                )
                alt_deg = np.degrees(alt)
                az_deg = np.degrees(az) % 360
                el_range = telescope.get_elevation_range()
                az_range = telescope.get_azimuth_range()
                visible = (el_range[0] <= alt_deg <= el_range[1] and 
                           az_range[0] <= az_deg <= az_range[1])
            availability[code] = visible
        logger.debug(f"Checked telescope availability for scan '{self.name}' at time={time.isot}: {availability}")
        return availability

    def to_dict(self) -> dict:
        """Convert the Scan object to a dictionary, serializing Time as ISO string."""
        data = super().to_dict()
        data["start"] = self.start.isot
        logger.info(f"Converted scan '{self.name}' with start={self.start.isot} to dictionary")
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Scan':
        """Create a Scan object from a dictionary, parsing ISO string to Time."""
        data = data.copy()
        start_time = Time(data.pop("start"))
        original_telescope_names = data.pop("original_telescope_names", None)
        original_frequency_names = data.pop("original_frequency_names", None)
        data.pop("type", None)  # Remove 'type' field if present
        scan = cls(
            name=data.get("name"),
            start=start_time,
            duration=data.get("duration"),
            source_name=data.get("source_name"),
            telescope_names=data.get("telescope_names"),
            frequency_names=data.get("frequency_names"),
            is_off_source=data.get("is_off_source"),
            isactive=data.get("isactive", True)
        )
        scan.original_telescope_names = original_telescope_names
        scan.original_frequency_names = original_frequency_names
        logger.info(f"Created scan '{scan.name}' with start={scan.start.isot} from dictionary")
        return scan


class Scans(BaseContainer[Scan]):
    """Base class representing a collection of Scan objects."""
    def __init__(self, items: Dict[str, Scan] = None, name: str = None, isactive: bool = True, use_cache: bool = False):
        """Initialize a Scans object with an optional dictionary of Scan objects."""
        if name is None:
            name = f"scans_{uuid.uuid4().hex[:32]}"
        super().__init__(items=items, name=name, isactive=isactive)
        self._key_cache = list(self._items.keys()) if items else []
        logger.info(f"Initialized Scans with name={name}, {len(self._items)} scans")

    def add(self, scan: Scan, observation: 'Observation' = None) -> None:
        """Add a Scan object to the collection with overlap checking."""
        from pastrocore.base.observation import Observation
        check_type(scan, Scan, "Scan")
        if observation:
            check_type(observation, Observation, "Observation")
            if not scan.validate_with_observation(observation):
                logger.error(f"Scan '{scan.name}' failed validation against observation '{observation.get_observation_code()}'")
                raise ValueError("Scan validation failed")
            # Check and update activity status
            should_be_active = scan._check_activity_status(observation)
            if should_be_active != scan.isactive:
                scan.set({"isactive": should_be_active})
                logger.debug(f"Set scan '{scan.name}' isactive={should_be_active} during add")

        overlap, reason = self._check_overlap(scan)
        if overlap:
            logger.error(f"Scan '{scan.name}' with start={scan.get_start().isot}, duration={scan.get_duration()} {reason}")
            raise ValueError(f"Scan conflicts: {reason}")
        super().add(scan)
        self._key_cache.append(scan.name)
        logger.info(f"Added scan '{scan.name}' with start={scan.get_start().isot} to Scans")

    def remove(self, name: str) -> None:
        """Remove a scan by its name."""
        super().remove(name)
        self._key_cache = list(self._items.keys())
        logger.info(f"Removed scan '{name}' from Scans")

    def create_scan(self, name: str = None, start: Time = None, duration: float = 1.0, source_name: Optional[str] = None,
                    telescope_names: List[str] = None, frequency_names: List[str] = None,
                    is_off_source: bool = False, isactive: bool = True, observation: 'Observation' = None) -> None:
        """Create and add a new Scan object to the collection."""
        scan = Scan(
            name=name,
            start=start,
            duration=duration,
            source_name=source_name,
            telescope_names=telescope_names,
            frequency_names=frequency_names,
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
        source_name: Optional[str] = None,
        telescope_names: Optional[List[str]] = None,
        frequency_names: Optional[List[str]] = None,
        is_off_source: Optional[bool] = None,
        isactive: Optional[bool] = None,
        observation: 'Observation' = None
    ) -> None:
        """Update an existing Scan object in the collection with new parameters.

        Args:
            name (str): The name of the Scan to update.
            start (Time, optional): The new start time.
            duration (float, optional): The new duration in seconds.
            source_name (str, optional): The new source name.
            telescope_names (List[str], optional): The new list of telescope names.
            frequency_names (List[str], optional): The new list of frequency names.
            is_off_source (bool, optional): The new off-source status.
            isactive (bool, optional): The new active status.
            observation (Observation, optional): Observation for validation.

        Raises:
            KeyError: If the Scan with the given name does not exist.
            ValueError: If the new parameters are invalid or cause time overlaps.
            TypeError: If the parameter types are incorrect.
        """
        from pastrocore.base.observation import Observation
        if name not in self._items:
            logger.error(f"Scan with name '{name}' not found in Scans")
            raise KeyError(f"Scan with name '{name}' not found in Scans")

        scan = self._items[name]
        
        # Prepare temporary parameters
        temp_start = start if start is not None else scan.start
        temp_duration = duration if duration is not None else scan.duration
        temp_source_name = source_name if source_name is not None else scan.source_name
        temp_telescope_names = telescope_names if telescope_names is not None else scan.telescope_names
        temp_frequency_names = frequency_names if frequency_names is not None else scan.frequency_names
        temp_is_off_source = is_off_source if is_off_source is not None else scan.is_off_source
        temp_isactive = isactive if isactive is not None else scan.isactive

        # Validate types and values
        check_type(temp_start, Time, "Start time")
        check_positive(temp_duration, "Duration")
        if temp_source_name is not None:
            check_type(temp_source_name, str, "Source name")
        check_type(temp_telescope_names, list, "Telescope names")
        check_type(temp_frequency_names, list, "Frequency names")

        # Create temporary Scan for overlap and validation
        temp_scan = Scan(
            name=name,
            start=temp_start,
            duration=temp_duration,
            source_name=temp_source_name,
            telescope_names=temp_telescope_names,
            frequency_names=temp_frequency_names,
            is_off_source=temp_is_off_source,
            isactive=temp_isactive,
            observation=observation
        )

        # Check for overlaps
        overlap, reason = self._check_overlap(temp_scan, exclude_name=name)
        if overlap:
            logger.error(f"Updated scan '{name}' {reason}")
            raise ValueError(f"Scan update conflicts: {reason}")

        # Validate with observation if provided
        if observation:
            check_type(observation, Observation, "Observation")
            if not temp_scan.validate_with_observation(observation):
                logger.error(f"Updated scan '{name}' failed validation against observation '{observation.get_observation_code()}'")
                raise ValueError("Scan validation failed")
        
        # Check activity status if observation is provided
        if observation and isactive is not None:
            temp_isactive = temp_scan._check_activity_status(observation)
            if temp_isactive != isactive:
                logger.debug(f"Overriding isactive={isactive} to {temp_isactive} for scan '{name}' based on validation")
                isactive = temp_isactive

        # Prepare parameters to update
        params = {}
        if start is not None:
            params["start"] = start
        if duration is not None:
            params["duration"] = duration
        if source_name is not None or is_off_source is not None:
            params["source_name"] = temp_source_name
            params["is_off_source"] = temp_is_off_source
        if telescope_names is not None:
            params["telescope_names"] = telescope_names
        if frequency_names is not None:
            params["frequency_names"] = frequency_names
        if isactive is not None:
            params["isactive"] = isactive

        # Update the scan
        if params:
            scan.set(params)
            logger.info(f"Updated scan '{name}' in Scans with params: {params}")
        else:
            logger.debug(f"No parameters to update for scan '{name}' in Scans")

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
                logger.debug(f"Activated scan '{scan.name}' in Scans '{self.name}'")
            elif not should_be_active and scan.isactive:
                scan.set({"isactive": False})
                skipped_count += 1
                logger.debug(f"Deactivated scan '{scan.name}' in Scans '{self.name}' as it does not meet activity conditions")
            elif not should_be_active:
                skipped_count += 1
                logger.debug(f"Skipped scan '{scan.name}' in Scans '{self.name}' as it does not meet activity conditions")
            else:
                logger.debug(f"Scan '{scan.name}' in Scans '{self.name}' already active and meets conditions")
        
        logger.info(f"Activated {activated_count} scans, skipped or deactivated {skipped_count} scans in Scans '{self.name}'")

    def get_active_scans(self, observation: 'Observation' = None) -> List[Scan]:
        """Retrieve all active scans, optionally filtering by entity activity in an Observation."""
        from pastrocore.base.observation import Observation
        active = []
        for scan in self.get_items():
            if not scan.isactive:
                continue
            if observation is None:
                active.append(scan)
                continue
            check_type(observation, Observation, "Observation")
            if scan.source_name is not None:
                source = observation.get_sources().get(scan.source_name)
                if source and not source.isactive:
                    continue
            all_tels = observation.get_telescopes()
            if any(name in all_tels._items and not all_tels.get(name).isactive for name in scan.telescope_names):
                continue
            all_freqs = observation.get_frequencies()
            if any(name in all_freqs._items and not all_freqs.get(name).isactive for name in scan.frequency_names):
                continue
            active.append(scan)
        logger.debug(f"Retrieved {len(active)} active scans" + 
                     (f" for observation '{observation.get_observation_code()}'" if observation else ""))
        return active

    def get_inactive_scans(self) -> List[Scan]:
        """Retrieve all inactive scans."""
        inactive = [s for s in self.get_items() if not s.isactive]
        logger.debug(f"Retrieved {len(inactive)} inactive scans")
        return inactive

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
                logger.debug(f"Overlap detected: {reason}")
                return True, reason
        logger.debug(f"No overlap detected for scan '{scan.name}' with start={scan.get_start().isot}")
        return False, ""

    def __repr__(self) -> str:
        """Return a string representation of the Scans object."""
        active_count = len(self.get_active_scans())
        attrs = [f"name={self.name!r}" if self.name else ""]
        attrs.append(f"count={len(self._items)}")
        attrs.append(f"active={active_count}")
        attrs.append(f"inactive={len(self._items) - active_count}")
        return f"Scans({', '.join(attr for attr in attrs if attr)})"