# base/scans.py
from common.base.baseentity import BaseEntity
from common.base.basecontainer import BaseContainer
from common.utils.validation import check_type, check_positive
from common.utils.logging_setup import logger
from unit_scheduling_2.base.frequencies import Frequencies
from unit_scheduling_2.base.sources import Source
from unit_scheduling_2.base.telescopes import Telescopes, SpaceTelescope
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
    source_index: Optional[int]
    telescope_indices: List[int]
    frequency_indices: List[int]
    is_off_source: bool
    original_telescope_indices: Optional[List[int]]
    original_frequency_indices: Optional[List[int]]

    def __init__(self, name: str = None, start: Time = None, duration: float = 1.0, source_index: Optional[int] = None,
                 telescope_indices: List[int] = None, frequency_indices: List[int] = None,
                 is_off_source: bool = False, isactive: bool = True):
        """Initialize a Scan with name, start time, duration, and indices referencing Observation data."""
        if start is None:
            start = Time.now()
        if name is None:
            name = f"scan_{uuid.uuid4().hex[:8]}"
        check_type(start, Time, "Start time")
        check_positive(duration, "Duration")
        if source_index is not None:
            check_type(source_index, int, "Source index")
        if telescope_indices is None:
            telescope_indices = []
        if frequency_indices is None:
            frequency_indices = []
        super().__init__(
            name=name,
            start=start,
            duration=duration,
            source_index=source_index,
            telescope_indices=telescope_indices,
            frequency_indices=frequency_indices,
            is_off_source=source_index is None or is_off_source,
            original_telescope_indices=telescope_indices.copy() if telescope_indices else None,
            original_frequency_indices=frequency_indices.copy() if frequency_indices else None,
            isactive=isactive
        )
        source_str = "OFF SOURCE" if self.is_off_source else f"source_index={source_index}" if source_index is not None else "no source"
        logger.info(f"Initialized Scan with name={name}, start={self.start.isot}, duration={duration}, {source_str}")

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

    def get_source_index(self) -> Optional[int]:
        """Retrieve the source index."""
        return self.get("source_index")

    def get_telescope_indices(self) -> List[int]:
        """Retrieve the list of telescope indices."""
        return self.get("telescope_indices")

    def get_frequency_indices(self) -> List[int]:
        """Retrieve the list of frequency indices."""
        return self.get("frequency_indices")

    def get_source(self, observation: 'Observation') -> Optional[Source]:
        """Retrieve the source associated with this scan from an Observation."""
        from unit_scheduling.base.observation import Observation
        check_type(observation, Observation, "Observation")
        if self.source_index is None or self.is_off_source:
            return None
        sources = observation.get_sources().get_all_sources()
        return sources[self.source_index] if 0 <= self.source_index < len(sources) else None

    def get_telescopes(self, observation: 'Observation') -> Telescopes:
        """Retrieve the telescopes associated with this scan from an Observation."""
        from unit_scheduling.base.observation import Observation
        check_type(observation, Observation, "Observation")
        all_tels = observation.get_telescopes().get_all_telescopes()
        selected = [all_tels[idx] for idx in self.telescope_indices if 0 <= idx < len(all_tels)]
        return Telescopes(selected)

    def get_frequencies(self, observation: 'Observation') -> Frequencies:
        """Retrieve the frequencies associated with this scan from an Observation."""
        from unit_scheduling.base.observation import Observation
        check_type(observation, Observation, "Observation")
        all_freqs = observation.get_frequencies().get_all_IF()
        selected = [all_freqs[idx] for idx in self.frequency_indices if 0 <= idx < len(all_freqs)]
        return Frequencies(selected)

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

    def set_source_index(self, source_index: Optional[int], observation: 'Observation' = None) -> None:
        """Set the source index for the scan."""
        if source_index is not None:
            check_type(source_index, int, "Source index")
        params = {"source_index": source_index, "is_off_source": source_index is None}
        self.set(params)
        if observation:
            self.validate_with_observation(observation)
        logger.info(f"Set scan source_index to {'OFF SOURCE' if source_index is None else source_index}")

    def set_telescope_indices(self, telescope_indices: List[int], observation: 'Observation' = None) -> None:
        """Set the telescope indices for the scan."""
        check_type(telescope_indices, list, "Telescope indices")
        self.set({"telescope_indices": telescope_indices})
        if observation:
            self.validate_with_observation(observation)
        logger.info(f"Set scan telescope_indices to {telescope_indices}")

    def set_frequency_indices(self, frequency_indices: List[int], observation: 'Observation' = None) -> None:
        """Set the frequency indices for the scan."""
        check_type(frequency_indices, list, "Frequency indices")
        self.set({"frequency_indices": frequency_indices})
        if observation:
            self.validate_with_observation(observation)
        logger.info(f"Set scan frequency_indices to {frequency_indices}")

    def validate_with_observation(self, observation: 'Observation') -> bool:
        """Validate the scan's indices against an Observation's data."""
        from unit_scheduling.base.observation import Observation
        check_type(observation, Observation, "Observation")
        
        if self.source_index is not None and (self.source_index < 0 or self.source_index >= len(observation.get_sources().get_all_sources())):
            logger.error(f"Invalid source_index {self.source_index} for observation with {len(observation.get_sources().get_all_sources())} sources")
            return False
        
        all_tels = observation.get_telescopes().get_all_telescopes()
        for idx in self.telescope_indices:
            if idx < 0 or idx >= len(all_tels):
                logger.error(f"Invalid telescope_index {idx} for observation with {len(all_tels)} telescopes")
                return False
        
        all_freqs = observation.get_frequencies().get_all_IF()
        for idx in self.frequency_indices:
            if idx < 0 or idx >= len(all_freqs):
                logger.error(f"Invalid frequency_index {idx} for observation with {len(all_freqs)} frequencies")
                return False
                
        logger.debug(f"Validated scan '{self.name}' with start={self.start.isot} against observation '{observation.get_observation_code()}'")
        return True

    def check_telescope_availability(self, observation: 'Observation', time: Time = None) -> dict[str, bool]:
        """Check telescope availability for this scan at a given time."""
        from unit_scheduling.base.observation import Observation
        check_type(observation, Observation, "Observation")
        if time is not None:
            check_type(time, Time, "Time")
        time = time if time is not None else self.start
        availability = {}
        source = self.get_source(observation) if not self.is_off_source else None
        
        for telescope in self.get_telescopes(observation).get_active_telescopes():
            code = telescope.get_code()
            if self.is_off_source:
                availability[code] = True
                continue
            ra_rad = np.radians(source.get_ra_degrees())
            dec_rad = np.radians(source.get_dec_degrees())
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
                ha = np.radians(lst - source.get_ra_degrees())
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
        data["start"] = Time(data["start"])
        logger.info(f"Created scan '{data['name']}' with start={data['start'].isot} from dictionary")
        return cls(**data)


class Scans(BaseContainer[Scan]):
    """Base class representing a collection of Scan objects."""
    def __init__(self, items: Dict[str, Scan] = None, name: str = None, isactive: bool = True):
        """Initialize a Scans object with an optional dictionary of Scan objects."""
        super().__init__(items=items, name=name, isactive=isactive)
        self._key_cache = list(self._items.keys()) if items else []
        logger.info(f"Initialized Scans with name={name}, {len(self._items)} scans")

    def add(self, scan: Scan, observation: 'Observation' = None) -> None:
        """Add a Scan object to the collection with overlap checking."""
        from unit_scheduling.base.observation import Observation
        check_type(scan, Scan, "Scan")
        if observation:
            check_type(observation, Observation, "Observation")
            if not scan.validate_with_observation(observation):
                logger.error(f"Scan '{scan.name}' failed validation against observation '{observation.get_observation_code()}'")
                raise ValueError("Scan validation failed")
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

    def create_scan(self, name: str = None, start: Time = None, duration: float = 1.0, source_index: Optional[int] = None,
                    telescope_indices: List[int] = None, frequency_indices: List[int] = None,
                    is_off_source: bool = False, isactive: bool = True, observation: 'Observation' = None) -> None:
        """Create and add a new Scan object to the collection."""
        scan = Scan(
            name=name,
            start=start,
            duration=duration,
            source_index=source_index,
            telescope_indices=telescope_indices,
            frequency_indices=frequency_indices,
            is_off_source=is_off_source,
            isactive=isactive
        )
        self.add(scan, observation)

    def get_by_index(self, index: int) -> Scan:
        """Retrieve a scan by its index in the items list."""
        check_type(index, int, "Index")
        try:
            return self._items[self._key_cache[index]]
        except IndexError:
            logger.error(f"Invalid scan index: {index}")
            raise IndexError("Invalid scan index!")

    def get_active_scans(self, observation: 'Observation' = None) -> List[Scan]:
        """Retrieve all active scans, optionally filtering by entity activity in an Observation."""
        from unit_scheduling.base.observation import Observation
        active = []
        for scan in self.get_items():
            if not scan.isactive:
                continue
            if observation is None:
                active.append(scan)
                continue
            check_type(observation, Observation, "Observation")
            if scan.source_index is not None and scan.source_index >= 0:
                if scan.source_index < len(observation.get_sources().get_all_sources()):
                    if not observation.get_sources().get_all_sources()[scan.source_index].isactive:
                        continue
            if any(idx >= 0 and idx < len(observation.get_telescopes().get_all_telescopes()) and 
                   not observation.get_telescopes().get_all_telescopes()[idx].isactive 
                   for idx in scan.telescope_indices):
                continue
            if any(idx >= 0 and idx < len(observation.get_frequencies().get_all_IF()) and 
                   not observation.get_frequencies().get_all_IF()[idx].isactive 
                   for idx in scan.frequency_indices):
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
        from unit_scheduling.base.observation import Observation
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