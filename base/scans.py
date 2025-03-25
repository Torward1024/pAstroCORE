# base/scans.py
from base.base_entity import BaseEntity
from base.frequencies import Frequencies
from base.sources import Source
from base.telescopes import Telescopes, SpaceTelescope

from utils.validation import check_type, check_positive
from utils.logging_setup import logger
from datetime import datetime
import numpy as np
from typing import Optional, List

"""Base-class of a Scan object with start_time, duration (s), source, telescopes and frequencies

    Notes: 
    Contains:
    Atributes:
        isactive (bool): whether the frequency is active (default: True)

    Methods:
        activate
        deactivate

        get_start
        get_end
        get_start_datetime
        get_end_datetime
        get_MJD_starttime
        get_MJD_endtime
        get_duration
        get_source_index
        get_telescope_indices
        get_frequency_indices

        get_source
        get_telescopes
        get_frequencies

        set_scan
        set_start
        set_duration
        set_source_index
        set_telescope_indices
        set_frequency_indices

        validate_with_observation
        check_telescope_availability

        to_dict
        from_dict

        __init__
        __repr__
    """

class Scan(BaseEntity):
    def __init__(self, start: float, duration: float, source_index: Optional[int] = None,
                 telescope_indices: List[int] = None, frequency_indices: List[int] = None,
                 is_off_source: bool = False, isactive: bool = True):
        """Initialize a Scan with start time, duration, and indices referencing Observation data."""
        super().__init__(isactive)
        check_type(start, (int, float), "Start time")
        check_positive(duration, "Duration")
        if source_index is not None:
            check_type(source_index, int, "Source index")
        if telescope_indices is not None:
            check_type(telescope_indices, list, "Telescope indices")
        if frequency_indices is not None:
            check_type(frequency_indices, list, "Frequency indices")
        self._start = start
        self._duration = duration
        self._source_index = source_index
        self._telescope_indices = telescope_indices if telescope_indices is not None else []
        self._frequency_indices = frequency_indices if frequency_indices is not None else []
        self._original_telescope_indices = self._telescope_indices.copy()
        self._original_frequency_indices = self._frequency_indices.copy()
        self.is_off_source = source_index is None or is_off_source
        source_str = "OFF SOURCE" if self.is_off_source else f"source_index={source_index}" if source_index is not None else "no source"
        logger.info(f"Initialized Scan with start={start}, duration={duration}, {source_str}")
    
    def activate(self):
        """Activate scan"""
        return super().activate()
    
    def deactivate(self):
        """Deactivate scan"""
        return super().deactivate()
    
    def get_start(self) -> float:
        """Get start time of scan"""
        return self._start
    
    def get_end(self) -> float:
        """Get end time of scan"""
        return self._start + self._duration

    def get_start_datetime(self) -> datetime:
        """Get start time of scan in DateTime format"""
        return datetime.fromtimestamp(self._start)
    
    def get_end_datetime(self) -> datetime:
        """Get end time of scan in DateTime format"""
        return datetime.fromtimestamp(self._start + self._duration)

    def get_MJD_starttime(self) -> float:
        """Get start time of scan in MJD"""
        return (self._start / 86400) + 40587

    def get_MJD_endtime(self) -> float:
        """Get end time of scan in MJD"""
        return ((self._start + self._duration) / 86400) + 40587

    def get_duration(self) -> float:
        """Get scan duration (s)"""
        return self._duration

    def get_source_index(self) -> Optional[int]:
        """Get scan source index"""
        return self._source_index

    def get_telescope_indices(self) -> List[int]:
        """Get scan telescope indices"""
        return self._telescope_indices

    def get_frequency_indices(self) -> List[int]:
        """Get scan frequency indices"""
        return self._frequency_indices   

    def get_source(self, observation: 'Observation') -> Optional[Source]:
        """Get the source associated with this scan from the Observation"""
        from base.observation import Observation
        check_type(observation, Observation, "Observation")
        if self._source_index is None or self.is_off_source:
            return None
        sources = observation.get_sources().get_all_sources()
        return sources[self._source_index] if 0 <= self._source_index < len(sources) else None

    def get_telescopes(self, observation: 'Observation') -> Telescopes:
        """Get the telescopes associated with this scan from the Observation"""
        from base.observation import Observation
        check_type(observation, Observation, "Observation")
        all_tels = observation.get_telescopes().get_all_telescopes()
        selected = [all_tels[idx] for idx in self._telescope_indices if 0 <= idx < len(all_tels)]
        return Telescopes(selected)
    
    def get_frequencies(self, observation: 'Observation') -> Frequencies:
        """Get the frequencies associated with this scan from the Observation"""
        from base.observation import Observation
        check_type(observation, Observation, "Observation")
        all_freqs = observation.get_frequencies().get_all_IF()
        selected = [all_freqs[idx] for idx in self._frequency_indices if 0 <= idx < len(all_freqs)]
        return Frequencies(selected)

    def set_scan(self, start: float, duration: float, source_index: Optional[int] = None,
                 telescope_indices: List[int] = None, frequency_indices: List[int] = None,
                 is_off_source: bool = False, isactive: bool = True) -> None:
        """Set all values for the scan using indices"""
        check_type(start, (int, float), "Start time")
        check_positive(duration, "Duration")
        if source_index is not None:
            check_type(source_index, int, "Source index")
        if telescope_indices is not None:
            check_type(telescope_indices, list, "Telescope indices")
        if frequency_indices is not None:
            check_type(frequency_indices, list, "Frequency indices")
        self._start = start
        self._duration = duration
        self._source_index = source_index
        self._telescope_indices = telescope_indices if telescope_indices is not None else []
        self._frequency_indices = frequency_indices if frequency_indices is not None else []
        self.is_off_source = source_index is None or is_off_source
        self.isactive = isactive
        source_str = "OFF SOURCE" if self.is_off_source else f"source_index={source_index}" if source_index is not None else "no source"
        logger.info(f"Set Scan with start={start}, duration={duration}, {source_str}")

    def set_start(self, start: float) -> None:
        """Set start time of scan"""
        check_type(start, (int, float), "Start time")
        self._start = start
        logger.info(f"Set scan start to {start}")

    def set_duration(self, duration: float) -> None:
        """Set duration of scan in (s)"""
        check_positive(duration, "Duration")
        self._duration = duration
        logger.info(f"Set scan duration to {duration}")

    def set_source_index(self, source_index: Optional[int], observation: 'Observation' = None) -> None:
        """Set source index for scan"""
        if source_index is not None:
            check_type(source_index, int, "Source index")
        self._source_index = source_index
        self.is_off_source = source_index is None
        if observation:
            self.validate_with_observation(observation)
        logger.info(f"Set scan source_index to {'OFF SOURCE' if source_index is None else source_index}")

    def set_telescope_indices(self, telescope_indices: List[int], observation: 'Observation' = None) -> None:
        """Set telescope indices for scan"""
        check_type(telescope_indices, list, "Telescope indices")
        self._telescope_indices = telescope_indices
        if observation:
            self.validate_with_observation(observation)
        logger.info(f"Set scan telescope_indices to {telescope_indices}")

    def set_frequency_indices(self, frequency_indices: List[int], observation: 'Observation' = None) -> None:
        """Set frequency indices for scan"""
        check_type(frequency_indices, list, "Frequency indices")
        self._frequency_indices = frequency_indices
        if observation:
            self.validate_with_observation(observation)
        logger.info(f"Set scan frequency_indices to {frequency_indices}")

    def validate_with_observation(self, observation: 'Observation') -> bool:
        """Validate scan against an Observation's data"""
        from base.observation import Observation
        check_type(observation, Observation, "Observation")
        
        if self._source_index is not None and (self._source_index < 0 or self._source_index >= len(observation.get_sources().get_all_sources())):
            logger.error(f"Invalid source_index {self._source_index} for observation with {len(observation.get_sources().get_all_sources())} sources")
            return False
        
        all_tels = observation.get_telescopes().get_all_telescopes()
        for idx in self._telescope_indices:
            if idx < 0 or idx >= len(all_tels):
                logger.error(f"Invalid telescope_index {idx} for observation with {len(all_tels)} telescopes")
                return False
        
        all_freqs = observation.get_frequencies().get_all_IF()
        for idx in self._frequency_indices:
            if idx < 0 or idx >= len(all_freqs):
                logger.error(f"Invalid frequency_index {idx} for observation with {len(all_freqs)} frequencies")
                return False
                
        logger.debug(f"Validated scan with start={self._start} against observation '{observation.get_observation_code()}'")
        return True
    
    def check_telescope_availability(self, observation: 'Observation', time: float = None) -> dict[str, bool]:
        """Check telescope availability for this scan at a given time (defaults to scan start)"""
        from base.observation import Observation
        check_type(observation, Observation, "Observation")
        check_type(time, (int, float), "Time", allow_none=True)
        time = time if time is not None else self._start
        availability = {}
        dt = datetime.fromtimestamp(time)
        source = self.get_source(observation) if not self.is_off_source else None
        
        for telescope in self.get_telescopes(observation).get_active_telescopes():
            code = telescope.get_telescope_code()
            if self.is_off_source:
                availability[code] = True
                continue
            ra_rad = np.radians(source.get_ra_degrees())
            dec_rad = np.radians(source.get_dec_degrees())
            # rough LST estimation
            lst = (time / 86164.0905 * 360 + 280.46061837) % 360  
            if isinstance(telescope, SpaceTelescope):
                pos, _ = telescope.get_position_at_time(dt)
                dist = np.linalg.norm(pos)
                # conditional visibility threshold
                visible = dist < 1e9  
                pitch_range = telescope.get_pitch_range()
                yaw_range = telescope.get_yaw_range()
                visible = (visible and 
                           pitch_range[0] <= 0 <= pitch_range[1] and 
                           yaw_range[0] <= 0 <= yaw_range[1])
            else:
                x, y, z = telescope.get_telescope_coordinates()
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
        logger.debug(f"Checked telescope availability for scan at time={time}: {availability}")
        return availability

    def to_dict(self) -> dict:
        logger.info(f"Converted scan with start={self._start} to dictionary")
        return {
            "start": self._start,
            "duration": self._duration,
            "source_index": self._source_index,
            "telescope_indices": self._telescope_indices,
            "frequency_indices": self._frequency_indices,
            "is_off_source": self.is_off_source,
            "isactive": self.isactive
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Scan':
        logger.info(f"Created scan with start={data['start']} from dictionary")
        return cls(
            start=data["start"],
            duration=data["duration"],
            source_index=data["source_index"],
            telescope_indices=data["telescope_indices"],
            frequency_indices=data["frequency_indices"],
            is_off_source=data["is_off_source"],
            isactive=data["isactive"]
        )

    def __repr__(self) -> str:
        source_str = "OFF SOURCE" if self.is_off_source else f"source_index={self._source_index}" if self._source_index is not None else "no source"
        return (f"Scan(start={self._start}, duration={self._duration}, {source_str}, "
                f"telescope_indices={self._telescope_indices}, frequency_indices={self._frequency_indices}, "
                f"isactive={self.isactive})")

"""Base-class of a Scan object with start_time, duration (s), source, telescopes and frequencies

    Notes: 
    Contains:
    Atributes:
        isactive (bool): whether the scan is active (default: True)

    Methods:
        add_scan
        insert_scan
        remove_scan
        set_scan

        get_scan
        get_all_scans
        get_active_scans
        get_inactive_scans

        activate_scan
        deactivate_scan

        activate_all
        deactivate_all

        drop_active
        drop_inactive
        clear
        to_dict
        from_dict

        _check_overlap
        __init__
        __repr__
    """

class Scans(BaseEntity):
    def __init__(self, scans: list[Scan] = None):
        """Initialize Scans with a list of Scan objects"""
        super().__init__()
        if scans is not None:
            check_type(scans, (list, tuple), "Scans")
            for scan in scans:
                check_type(scan, Scan, "Scan")
        self._data = scans if scans is not None else []
        logger.info(f"Initialized Scans with {len(self._data)} scans")

    def add_scan(self, scan: 'Scan', observation: 'Observation' = None) -> None:
        """Add a new scan with overlap checking for time and telescopes"""
        check_type(scan, Scan, "Scan")
        if observation:
            if not scan.validate_with_observation(observation):
                logger.error(f"Scan with start={scan.get_start()} failed validation against observation '{observation.get_observation_code()}'")
                raise ValueError("Scan validation failed")
        overlap, reason = self._check_overlap(scan)
        if overlap:
            logger.error(f"Scan with start={scan.get_start()}, duration={scan.get_duration()} {reason}")
            raise ValueError(f"Scan conflicts: {reason}")
        self._data.append(scan)
        logger.info(f"Added scan with start={scan.get_start()}, duration={scan.get_duration()} to Scans")
    
    def insert_scan(self, scan: 'Scan', index: int, observation: 'Observation' = None) -> None:
        """Insert a scan at the specified index with overlap checking"""
        check_type(scan, Scan, "Scan")
        check_type(index, int, "Index")
        if not (0 <= index <= len(self._data)):
            logger.error(f"Invalid insert index {index} for Scans with {len(self._data)} scans")
            raise IndexError(f"Insert index {index} out of range")
        if observation:
            if not scan.validate_with_observation(observation):
                logger.error(f"Scan with start={scan.get_start()} failed validation against observation '{observation.get_observation_code()}'")
                raise ValueError("Scan validation failed")
        overlap, reason = self._check_overlap(scan)
        if overlap:
            logger.error(f"Scan with start={scan.get_start()}, duration={scan.get_duration()} {reason}")
            raise ValueError(f"Scan conflicts: {reason}")
        self._data.insert(index, scan)
        logger.info(f"Inserted scan with start={scan.get_start()} at index {index} in Scans")

    def remove_scan(self, index: int) -> None:
        """Remove scan by index"""
        try:
            self._data.pop(index)
            logger.info(f"Removed scan at index {index} from Scans")
        except IndexError:
            logger.error(f"Invalid scan index: {index}")
            raise IndexError("Invalid scan index!")

    def set_scan(self, scan: 'Scan', index: int, observation: 'Observation' = None) -> None:
        """Set scan data by index with overlap checking"""
        check_type(scan, Scan, "Scan")
        try:
            if observation:
                if not scan.validate_with_observation(observation):
                    logger.error(f"Scan with start={scan.get_start()} failed validation against observation '{observation.get_observation_code()}'")
                    raise ValueError("Scan validation failed")
            overlap, reason = self._check_overlap(scan, exclude_index=index)
            if overlap:
                logger.error(f"Scan with start={scan.get_start()}, duration={scan.get_duration()} {reason}")
                raise ValueError(f"Scan conflicts: {reason}")
            self._data[index] = scan
            logger.info(f"Set scan with start={scan.get_start()} at index {index}")
        except IndexError:
            logger.error(f"Invalid scan index: {index}")
            raise IndexError("Invalid scan index!")

    def get_scan(self, index: int) -> Scan:
        """Get scan by index"""
        try:
            return self._data[index]
        except IndexError:
            logger.error(f"Invalid scan index: {index}")
            raise IndexError("Invalid scan index!")

    def get_all_scans(self) -> list[Scan]:
        """Get all scans"""
        return self._data

    def get_active_scans(self, observation: 'Observation' = None) -> list[Scan]:
        """Get active scans, ensuring referenced entities are active. Requires Observation for context"""
        from base.observation import Observation
        active = []
        for scan in self._data:
            if not scan.isactive:
                continue
            if observation is None:
                active.append(scan)
                continue
            if scan._source_index is not None and scan._source_index >= 0:
                if scan._source_index < len(observation.get_sources().get_all_sources()):
                    if not observation.get_sources().get_all_sources()[scan._source_index].isactive:
                        continue
            if any(idx >= 0 and idx < len(observation.get_telescopes().get_all_telescopes()) and 
                   not observation.get_telescopes().get_all_telescopes()[idx].isactive 
                   for idx in scan._telescope_indices):
                continue
            if any(idx >= 0 and idx < len(observation.get_frequencies().get_all_IF()) and 
                   not observation.get_frequencies().get_all_IF()[idx].isactive 
                   for idx in scan._frequency_indices):
                continue
            active.append(scan)
        logger.debug(f"Retrieved {len(active)} active scans" + 
                     (f" for observation '{observation.get_observation_code()}'" if observation else ""))
        return active

    def get_inactive_scans(self) -> list[Scan]:
        """Get inactive scans"""
        inactive = [s for s in self._data if not s.isactive]
        logger.debug(f"Retrieved {len(inactive)} inactive scans")
        return inactive
    
    def activate_scan(self, index: int) -> None:
        """Activate a specific scan by index"""
        try:
            scan = self._data[index]
            scan.activate()
            logger.info(f"Activated scan at index {index} with start={scan.get_start()}")
        except IndexError:
            logger.error(f"Invalid scan index: {index}")
            raise IndexError("Invalid scan index!")
    
    def deactivate_scan(self, index: int) -> None:
        """Deactivate a specific scan by index"""
        try:
            scan = self._data[index]
            scan.deactivate()
            logger.info(f"Deactivated scan at index {index} with start={scan.get_start()}")
        except IndexError:
            logger.error(f"Invalid scan index: {index}")
            raise IndexError("Invalid scan index!")

    def activate_all(self) -> None:
        """Activate all scans"""
        if not self._data:
            logger.error("No scans to activate")
            raise ValueError("No scans to activate!")
        for s in self._data:
            s.activate()
        logger.info("Activated all scans")

    def deactivate_all(self) -> None:
        """Deactivate all scans"""
        if not self._data:
            logger.error("No scans to deactivate")
            raise ValueError("No scans to deactivate!")
        for s in self._data:
            s.deactivate()
        logger.info("Deactivated all scans")

    def drop_active(self) -> None:
        """Remove all active scans"""
        initial_len = len(self._data)
        self._data = [s for s in self._data if not s.isactive]
        removed = initial_len - len(self._data)
        if removed > 0:
            logger.info(f"Removed {removed} active scans from Scans")
        else:
            logger.debug("No active scans to drop")
        
    def drop_inactive(self) -> None:
        """Remove all inactive scans"""
        initial_len = len(self._data)
        self._data = [s for s in self._data if s.isactive]
        removed = initial_len - len(self._data)
        if removed > 0:
            logger.info(f"Removed {removed} inactive scans from Scans")
        else:
            logger.debug("No inactive scans to drop")

    def clear(self) -> None:
        """Clear scans data"""
        logger.info(f"Cleared {len(self._data)} scans from Scans")
        self._data.clear()

    def to_dict(self) -> dict:
        """Convert Scans object to a dictionary for serialization"""
        logger.info(f"Converted Scans with {len(self._data)} scans to dictionary")
        return {"data": [scan.to_dict() for scan in self._data]}

    @classmethod
    def from_dict(cls, data: dict) -> 'Scans':
        """Create a Scans object from a dictionary"""
        scans = [Scan.from_dict(scan_data) for scan_data in data["data"]]
        logger.info(f"Created Scans with {len(scans)} scans from dictionary")
        return cls(scans=scans)
    
    def _check_overlap(self, scan: 'Scan', exclude_index: int = -1) -> tuple[bool, str]:
        """Check if the scan overlaps with existing scans by time and telescopes (source optional)."""
        for i, existing in enumerate(self._data):
            # check whether scans are active
            if i == exclude_index or not existing.isactive or not scan.isactive:  
                continue
            # check time overlap
            time_overlap = (existing.get_start() < scan.get_start() + scan.get_duration() and
                            scan.get_start() < existing.get_start() + existing.get_duration())
            if not time_overlap:
                continue
            # check telescope overlap
            existing_tels = {t.get_telescope_code() for t in existing.get_telescopes().get_active_telescopes()}
            new_tels = {t.get_telescope_code() for t in scan.get_telescopes().get_active_telescopes()}
            common_tels = existing_tels.intersection(new_tels)
            if common_tels:
                return True, f"overlaps with scan {i} by telescopes {common_tels}"
        return False, ""

    def __len__(self) -> int:
        """Return the number of scans."""
        return len(self._data)

    def __repr__(self) -> str:
        """Return a string representation of Scans."""
        active_count = len(self.get_active_scans())
        return f"Scans(count={len(self._data)}, active={active_count}, inactive={len(self._data) - active_count})"