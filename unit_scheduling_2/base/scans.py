# base/scans.py
from common.base.base_entity import BaseEntity
from common.utils.validation import check_type, check_positive
from common.utils.logging_setup import logger

from unit_scheduling.base.frequencies import Frequencies
from unit_scheduling.base.sources import Source
from unit_scheduling.base.telescopes import Telescopes, SpaceTelescope
import numpy as np
from typing import Optional, List
from astropy.time import Time
import astropy.units as u

class Scan(BaseEntity):
    """Base class representing a single observation scan with timing, source, telescopes, and frequencies.

    This class defines a scan, which is a time-bound observation event with a start time, duration, and references
    to a source, telescopes, and frequencies via indices into an Observation object. It supports validation
    against an Observation, telescope availability checks, and serialization. Scans can be marked as off-source
    (no target) and maintain original indices for synchronization with entity activation/deactivation.

    Attributes:
        _start (Time): Start time of the scan as an astropy Time object (UTC).
        _duration (float): Duration of the scan in seconds. Must be positive.
        _source_index (Optional[int]): Index of the source in the Observation's Sources collection, or None if off-source.
        _telescope_indices (List[int]): List of indices referencing telescopes in the Observation's Telescopes collection.
        _frequency_indices (List[int]): List of indices referencing frequencies in the Observation's Frequencies collection.
        _original_telescope_indices (List[int]): Copy of initial telescope indices for synchronization.
        _original_frequency_indices (List[int]): Copy of initial frequency indices for synchronization.
        is_off_source (bool): Whether the scan is off-source (no target observed).
        isactive (bool): Whether the scan is active. Inherited from BaseEntity.

    Notes:
        - Indices reference entities in an Observation object and are validated against its collections.
        - The `is_off_source` flag is set to True if `_source_index` is None or explicitly specified.
        - Telescope availability checks include elevation/azimuth for ground telescopes and state vector/pitch/yaw for space telescopes.
        - Logging is integrated via `common.utils.logging_setup.logger` to track operations and errors.

    Examples:
        >>> from astropy.time import Time
        >>> scan = Scan(start=Time("2025-04-06T00:00:00"), duration=600.0, source_index=0, telescope_indices=[0, 1], frequency_indices=[0])
        >>> print(scan)
        Scan(start=2025-04-06T00:00:00.000, duration=600.0, source_index=0, telescope_indices=[0, 1], frequency_indices=[0], isactive=True)
        >>> scan.get_end().isot
        '2025-04-06T00:10:00.000'
    """
    def __init__(self, start: Time = None, duration: float = 1.0, source_index: Optional[int] = None,
                 telescope_indices: List[int] = None, frequency_indices: List[int] = None,
                 is_off_source: bool = False, isactive: bool = True):
        """Initialize a Scan with start time, duration, and indices referencing Observation data.

        Args:
            start (Time, optional): Start time of the scan (UTC). Defaults to current time if None.
            duration (float): Duration of the scan in seconds. Must be positive. Defaults to 1.0.
            source_index (Optional[int]): Index of the source in the Observation's Sources. Defaults to None.
            telescope_indices (List[int], optional): List of telescope indices in the Observation's Telescopes. Defaults to empty list if None.
            frequency_indices (List[int], optional): List of frequency indices in the Observation's Frequencies. Defaults to empty list if None.
            is_off_source (bool): Whether the scan is off-source. Defaults to False, overridden if source_index is None.
            isactive (bool): Whether the scan is active. Defaults to True.

        Raises:
            TypeError: If start is not a Time object, or source_index/telescope_indices/frequency_indices are of incorrect type.
            ValueError: If duration is not positive.
        """
        super().__init__(isactive)
        if start is None:
            start = Time.now()
        check_type(start, Time, "Start time")
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
        logger.info(f"Initialized Scan with start={self._start.isot}, duration={duration}, {source_str}")

    def activate(self):
        """Activate the scan, marking it as active."""
        return super().activate()

    def deactivate(self):
        """Deactivate the scan, marking it as inactive."""
        return super().deactivate()

    def get_start(self) -> Time:
        """Retrieve the start time of the scan.

        Returns:
            Time: The start time as an astropy Time object (UTC).
        """
        return self._start

    def get_end(self) -> Time:
        """Retrieve the end time of the scan.

        Returns:
            Time: The end time as an astropy Time object (UTC), calculated as start + duration.
        """
        return self._start + self._duration * u.s

    def get_MJD_starttime(self) -> float:
        """Retrieve the start time of the scan in Modified Julian Date (MJD).

        Returns:
            float: The MJD of the start time.
        """
        return self._start.mjd

    def get_MJD_endtime(self) -> float:
        """Retrieve the end time of the scan in Modified Julian Date (MJD).

        Returns:
            float: The MJD of the end time, calculated as start + duration.
        """
        return (self._start + self._duration * u.s).mjd

    def get_duration(self) -> float:
        """Retrieve the duration of the scan.

        Returns:
            float: The duration in seconds.
        """
        return self._duration

    def get_source_index(self) -> Optional[int]:
        """Retrieve the source index.

        Returns:
            Optional[int]: The index of the source in the Observation's Sources, or None if off-source.
        """
        return self._source_index

    def get_telescope_indices(self) -> List[int]:
        """Retrieve the list of telescope indices.

        Returns:
            List[int]: The list of indices referencing telescopes in the Observation's Telescopes.
        """
        return self._telescope_indices

    def get_frequency_indices(self) -> List[int]:
        """Retrieve the list of frequency indices.

        Returns:
            List[int]: The list of indices referencing frequencies in the Observation's Frequencies.
        """
        return self._frequency_indices

    def get_source(self, observation: 'Observation') -> Optional[Source]:
        """Retrieve the source associated with this scan from an Observation.

        Args:
            observation (Observation): The Observation object containing the sources.

        Returns:
            Optional[Source]: The Source object if source_index is valid and not off-source, otherwise None.

        Raises:
            TypeError: If observation is not an Observation instance.
        """
        from unit_scheduling.base.observation import Observation
        check_type(observation, Observation, "Observation")
        if self._source_index is None or self.is_off_source:
            return None
        sources = observation.get_sources().get_all_sources()
        return sources[self._source_index] if 0 <= self._source_index < len(sources) else None

    def get_telescopes(self, observation: 'Observation') -> Telescopes:
        """Retrieve the telescopes associated with this scan from an Observation.

        Args:
            observation (Observation): The Observation object containing the telescopes.

        Returns:
            Telescopes: A Telescopes object containing the selected telescopes.

        Raises:
            TypeError: If observation is not an Observation instance.
        """
        from unit_scheduling.base.observation import Observation
        check_type(observation, Observation, "Observation")
        all_tels = observation.get_telescopes().get_all_telescopes()
        selected = [all_tels[idx] for idx in self._telescope_indices if 0 <= idx < len(all_tels)]
        return Telescopes(selected)

    def get_frequencies(self, observation: 'Observation') -> Frequencies:
        """Retrieve the frequencies associated with this scan from an Observation.

        Args:
            observation (Observation): The Observation object containing the frequencies.

        Returns:
            Frequencies: A Frequencies object containing the selected frequencies.

        Raises:
            TypeError: If observation is not an Observation instance.
        """
        from unit_scheduling.base.observation import Observation
        check_type(observation, Observation, "Observation")
        all_freqs = observation.get_frequencies().get_all_IF()
        selected = [all_freqs[idx] for idx in self._frequency_indices if 0 <= idx < len(all_freqs)]
        return Frequencies(selected)

    def set_scan(self, start: Time, duration: float, source_index: Optional[int] = None,
                 telescope_indices: List[int] = None, frequency_indices: List[int] = None,
                 is_off_source: bool = False, isactive: bool = True) -> None:
        """Set all properties of the scan.

        Args:
            start (Time): Start time of the scan (UTC).
            duration (float): Duration of the scan in seconds. Must be positive.
            source_index (Optional[int]): Index of the source in the Observation's Sources. Defaults to None.
            telescope_indices (List[int], optional): List of telescope indices. Defaults to empty list if None.
            frequency_indices (List[int], optional): List of frequency indices. Defaults to empty list if None.
            is_off_source (bool): Whether the scan is off-source. Defaults to False, overridden if source_index is None.
            isactive (bool): Whether the scan is active. Defaults to True.

        Raises:
            TypeError: If start is not a Time object, or source_index/telescope_indices/frequency_indices are of incorrect type.
            ValueError: If duration is not positive.
        """
        check_type(start, Time, "Start time")
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
        logger.info(f"Set Scan with start={self._start.isot}, duration={duration}, {source_str}")

    def set_start(self, start: Time) -> None:
        """Set the start time of the scan.

        Args:
            start (Time): New start time (UTC).

        Raises:
            TypeError: If start is not a Time object.
        """
        check_type(start, Time, "Start time")
        self._start = start
        logger.info(f"Set scan start to {self._start.isot}")

    def set_duration(self, duration: float) -> None:
        """Set the duration of the scan.

        Args:
            duration (float): New duration in seconds. Must be positive.

        Raises:
            ValueError: If duration is not positive.
        """
        check_positive(duration, "Duration")
        self._duration = duration
        logger.info(f"Set scan duration to {duration}")

    def set_source_index(self, source_index: Optional[int], observation: 'Observation' = None) -> None:
        """Set the source index for the scan.

        Args:
            source_index (Optional[int]): New source index, or None for off-source.
            observation (Observation, optional): Observation object to validate against. Defaults to None.

        Raises:
            TypeError: If source_index is not an integer or None.
            ValueError: If observation is provided and validation fails.
        """
        if source_index is not None:
            check_type(source_index, int, "Source index")
        self._source_index = source_index
        self.is_off_source = source_index is None
        if observation:
            self.validate_with_observation(observation)
        logger.info(f"Set scan source_index to {'OFF SOURCE' if source_index is None else source_index}")

    def set_telescope_indices(self, telescope_indices: List[int], observation: 'Observation' = None) -> None:
        """Set the telescope indices for the scan.

        Args:
            telescope_indices (List[int]): New list of telescope indices.
            observation (Observation, optional): Observation object to validate against. Defaults to None.

        Raises:
            TypeError: If telescope_indices is not a list.
            ValueError: If observation is provided and validation fails.
        """
        check_type(telescope_indices, list, "Telescope indices")
        self._telescope_indices = telescope_indices
        if observation:
            self.validate_with_observation(observation)
        logger.info(f"Set scan telescope_indices to {telescope_indices}")

    def set_frequency_indices(self, frequency_indices: List[int], observation: 'Observation' = None) -> None:
        """Set the frequency indices for the scan.

        Args:
            frequency_indices (List[int]): New list of frequency indices.
            observation (Observation, optional): Observation object to validate against. Defaults to None.

        Raises:
            TypeError: If frequency_indices is not a list.
            ValueError: If observation is provided and validation fails.
        """
        check_type(frequency_indices, list, "Frequency indices")
        self._frequency_indices = frequency_indices
        if observation:
            self.validate_with_observation(observation)
        logger.info(f"Set scan frequency_indices to {frequency_indices}")

    def validate_with_observation(self, observation: 'Observation') -> bool:
        """Validate the scan's indices against an Observation's data.

        Checks:
        - Source index is within the bounds of Observation's sources (if not None).
        - Telescope indices are within the bounds of Observation's telescopes.
        - Frequency indices are within the bounds of Observation's frequencies.

        Args:
            observation (Observation): The Observation object to validate against.

        Returns:
            bool: True if all indices are valid, False otherwise. Errors are logged.

        Raises:
            TypeError: If observation is not an Observation instance.
        """
        from unit_scheduling.base.observation import Observation
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
                
        logger.debug(f"Validated scan with start={self._start.isot} against observation '{observation.get_observation_code()}'")
        return True

    def check_telescope_availability(self, observation: 'Observation', time: Time = None) -> dict[str, bool]:
        """Check telescope availability for this scan at a given time.

        For ground telescopes, checks elevation and azimuth ranges. For space telescopes, checks visibility
        based on state vector and pitch/yaw ranges (simplified). If off-source, assumes all telescopes are available.

        Args:
            observation (Observation): The Observation object containing telescope data.
            time (Time, optional): Time to check availability (UTC). Defaults to scan start time if None.

        Returns:
            dict[str, bool]: Dictionary mapping telescope codes to availability status.

        Raises:
            TypeError: If observation is not an Observation instance or time is not a Time object.
        """
        from unit_scheduling.base.observation import Observation
        check_type(observation, Observation, "Observation")
        if time is not None:
            check_type(time, Time, "Time")
        time = time if time is not None else self._start
        availability = {}
        source = self.get_source(observation) if not self.is_off_source else None
        
        for telescope in self.get_telescopes(observation).get_active_telescopes():
            code = telescope.get_code()
            if self.is_off_source:
                availability[code] = True
                continue
            ra_rad = np.radians(source.get_ra_degrees())
            dec_rad = np.radians(source.get_dec_degrees())
            # Rough LST estimation using Time
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
        logger.debug(f"Checked telescope availability for scan at time={time.isot}: {availability}")
        return availability

    def to_dict(self) -> dict:
        """Convert the Scan object to a dictionary for serialization.

        Returns:
            dict: A dictionary with scan properties, where start time is serialized as an ISO string.
        """
        logger.info(f"Converted scan with start={self._start.isot} to dictionary")
        return {
            "start": self._start.isot,  # Сохраняем как ISO-строку для сериализации
            "duration": self._duration,
            "source_index": self._source_index,
            "telescope_indices": self._telescope_indices,
            "frequency_indices": self._frequency_indices,
            "is_off_source": self.is_off_source,
            "isactive": self.isactive
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Scan':
        """Create a Scan object from a dictionary.

        Args:
            data (dict): Dictionary containing scan properties, typically from `to_dict`.

        Returns:
            Scan: A new Scan instance initialized with the dictionary data.
        """
        start = Time(data["start"])
        logger.info(f"Created scan with start={start.isot} from dictionary")
        return cls(
            start=start,
            duration=data["duration"],
            source_index=data["source_index"],
            telescope_indices=data["telescope_indices"],
            frequency_indices=data["frequency_indices"],
            is_off_source=data["is_off_source"],
            isactive=data["isactive"]
        )

    def __repr__(self) -> str:
        """Return a string representation of the Scan object.

        Returns:
            str: A formatted string with start time, duration, source info, indices, and active status.
        """
        source_str = "OFF SOURCE" if self.is_off_source else f"source_index={self._source_index}" if self._source_index is not None else "no source"
        return (f"Scan(start={self._start.isot}, duration={self._duration}, {source_str}, "
                f"telescope_indices={self._telescope_indices}, frequency_indices={self._frequency_indices}, "
                f"isactive={self.isactive})")


class Scans(BaseEntity):
    """Base class representing a collection of Scan objects.

    This class manages a list of scans, ensuring no time overlaps between active scans for the same telescopes.
    It provides methods to add, remove, modify, and query scans, with optional validation against an Observation
    object. Scans can be activated/deactivated individually or collectively, and the class supports serialization.

    Attributes:
        _data (List[Scan]): List of Scan objects in the collection.
        isactive (bool): Whether the Scans object itself is active. Inherited from BaseEntity.

    Notes:
        - Overlap checking is performed when adding or modifying scans, considering time ranges of active scans.
        - The `get_active_scans` method filters scans based on their own active status and the active status of
          referenced entities in an Observation (if provided).
        - Logging is integrated via `common.utils.logging_setup.logger` to track operations and errors.

    Examples:
        >>> from astropy.time import Time
        >>> scans = Scans()
        >>> scans.create_scan(start=Time("2025-04-06T00:00:00"), duration=600.0, source_index=0, telescope_indices=[0])
        >>> print(scans)
        Scans(count=1, active=1, inactive=0)
        >>> scans.create_scan(start=Time("2025-04-06T00:05:00"), duration=600.0, telescope_indices=[0])
        Traceback (most recent call last):
        ...
        ValueError: Scan conflicts: overlaps with scan at index 0 (start=2025-04-06T00:00:00.000, duration=600.0)
    """
    def __init__(self, scans: List[Scan] = None):
        """Initialize a Scans object with an optional list of Scan objects.

        Args:
            scans (List[Scan], optional): Initial list of Scan objects. Defaults to None (empty list).

        Raises:
            TypeError: If scans is not a list/tuple or contains non-Scan objects.
        """
        super().__init__()
        if scans is not None:
            check_type(scans, (list, tuple), "Scans")
            for scan in scans:
                check_type(scan, Scan, "Scan")
        self._data = scans if scans is not None else []
        logger.info(f"Initialized Scans with {len(self._data)} scans")

    def add_scan(self, scan: 'Scan', observation: 'Observation' = None) -> None:
        """Add an existing Scan object to the collection with overlap checking.

        Args:
            scan (Scan): The Scan object to add.
            observation (Observation, optional): Observation object to validate against. Defaults to None.

        Raises:
            TypeError: If scan is not a Scan instance.
            ValueError: If scan overlaps with an existing active scan or fails validation against observation.
        """
        check_type(scan, Scan, "Scan")
        if observation:
            if not scan.validate_with_observation(observation):
                logger.error(f"Scan with start={scan.get_start().isot} failed validation against observation '{observation.get_observation_code()}'")
                raise ValueError("Scan validation failed")
        overlap, reason = self._check_overlap(scan)
        if overlap:
            logger.error(f"Scan with start={scan.get_start().isot}, duration={scan.get_duration()} {reason}")
            raise ValueError(f"Scan conflicts: {reason}")
        self._data.append(scan)
        logger.info(f"Added scan with start={scan.get_start().isot}, duration={scan.get_duration()} to Scans")

    def create_scan(self, start: Time = None, duration: float = 1.0, source_index: Optional[int] = None,
                    telescope_indices: List[int] = None, frequency_indices: List[int] = None,
                    is_off_source: bool = False, isactive: bool = True, observation: 'Observation' = None) -> None:
        """Create and add a new Scan object to the collection.

        Args:
            start (Time, optional): Start time of the scan (UTC). Defaults to current time if None.
            duration (float): Duration of the scan in seconds. Must be positive. Defaults to 1.0.
            source_index (Optional[int]): Index of the source. Defaults to None.
            telescope_indices (List[int], optional): List of telescope indices. Defaults to None (empty list).
            frequency_indices (List[int], optional): List of frequency indices. Defaults to None (empty list).
            is_off_source (bool): Whether the scan is off-source. Defaults to False.
            isactive (bool): Whether the scan is active. Defaults to True.
            observation (Observation, optional): Observation object to validate against. Defaults to None.

        Raises:
            TypeError: If start is not a Time object or observation is not an Observation instance.
            ValueError: If duration is not positive, scan overlaps with an existing active scan, or validation fails.
        """
        if start is None:
            start = Time.now()
        check_type(start, Time, "Start time")
        new_scan = Scan(
            start=start,
            duration=duration,
            source_index=source_index,
            telescope_indices=telescope_indices,
            frequency_indices=frequency_indices,
            is_off_source=is_off_source,
            isactive=isactive
        )
        if observation:
            from unit_scheduling.base.observation import Observation
            check_type(observation, Observation, "Observation")
            if not new_scan.validate_with_observation(observation):
                logger.error(f"Scan with start={start.isot} failed validation against observation '{observation.get_observation_code()}'")
                raise ValueError("Scan validation failed")
        overlap, reason = self._check_overlap(new_scan)
        if overlap:
            logger.error(f"Scan with start={start.isot}, duration={duration} {reason}")
            raise ValueError(f"Scan conflicts: {reason}")
        self._data.append(new_scan)
        source_str = "OFF SOURCE" if is_off_source else f"source_index={source_index}"
        logger.info(f"Created and added scan with start={start.isot}, duration={duration}, {source_str} to Scans")

    def insert_scan(self, scan: 'Scan', index: int, observation: 'Observation' = None) -> None:
        """Insert a Scan object at a specific index with overlap checking.

        Args:
            scan (Scan): The Scan object to insert.
            index (int): The position to insert the scan (0 to len(scans)).
            observation (Observation, optional): Observation object to validate against. Defaults to None.

        Raises:
            TypeError: If scan is not a Scan instance or index is not an integer.
            IndexError: If index is out of range.
            ValueError: If scan overlaps with an existing active scan or fails validation.
        """
        check_type(scan, Scan, "Scan")
        check_type(index, int, "Index")
        if not (0 <= index <= len(self._data)):
            logger.error(f"Invalid insert index {index} for Scans with {len(self._data)} scans")
            raise IndexError(f"Insert index {index} out of range")
        if observation:
            if not scan.validate_with_observation(observation):
                logger.error(f"Scan with start={scan.get_start().isot} failed validation against observation '{observation.get_observation_code()}'")
                raise ValueError("Scan validation failed")
        overlap, reason = self._check_overlap(scan)
        if overlap:
            logger.error(f"Scan with start={scan.get_start().isot}, duration={scan.get_duration()} {reason}")
            raise ValueError(f"Scan conflicts: {reason}")
        self._data.insert(index, scan)
        logger.info(f"Inserted scan with start={scan.get_start().isot} at index {index} in Scans")

    def remove_scan(self, index: int) -> None:
        """Remove a scan by index.

        Args:
            index (int): The index of the scan to remove.

        Raises:
            IndexError: If index is out of range.
        """
        try:
            self._data.pop(index)
            logger.info(f"Removed scan at index {index} from Scans")
        except IndexError:
            logger.error(f"Invalid scan index: {index}")
            raise IndexError("Invalid scan index!")

    def set_scan(self, scan: 'Scan', index: int, observation: 'Observation' = None) -> None:
        """Replace a scan at a specific index with overlap checking.

        Args:
            scan (Scan): The new Scan object to set.
            index (int): The index to replace.
            observation (Observation, optional): Observation object to validate against. Defaults to None.

        Raises:
            TypeError: If scan is not a Scan instance.
            IndexError: If index is out of range.
            ValueError: If scan overlaps with another active scan or fails validation.
        """
        check_type(scan, Scan, "Scan")
        try:
            if observation:
                if not scan.validate_with_observation(observation):
                    logger.error(f"Scan with start={scan.get_start().isot} failed validation against observation '{observation.get_observation_code()}'")
                    raise ValueError("Scan validation failed")
            overlap, reason = self._check_overlap(scan, exclude_index=index)
            if overlap:
                logger.error(f"Scan with start={scan.get_start().isot}, duration={scan.get_duration()} {reason}")
                raise ValueError(f"Scan conflicts: {reason}")
            self._data[index] = scan
            logger.info(f"Set scan with start={scan.get_start().isot} at index {index}")
        except IndexError:
            logger.error(f"Invalid scan index: {index}")
            raise IndexError("Invalid scan index!")

    def get_by_index(self, index: int) -> Scan:
        """Retrieve a scan by index.

        Args:
            index (int): The index of the scan to retrieve.

        Returns:
            Scan: The Scan object at the specified index.

        Raises:
            IndexError: If index is out of range.
        """
        try:
            return self._data[index]
        except IndexError:
            logger.error(f"Invalid scan index: {index}")
            raise IndexError("Invalid scan index!")

    def get_all_scans(self) -> List[Scan]:
        """Retrieve all scans in the collection.

        Returns:
            List[Scan]: A list of all Scan objects.
        """
        return self._data

    def get_active_scans(self, observation: 'Observation' = None) -> List[Scan]:
        """Retrieve all active scans, optionally filtering by entity activity in an Observation.

        If an Observation is provided, only scans with active sources, telescopes, and frequencies are returned.

        Args:
            observation (Observation, optional): Observation object to filter by entity activity. Defaults to None.

        Returns:
            List[Scan]: A list of active Scan objects.
        """
        from unit_scheduling.base.observation import Observation
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

    def get_inactive_scans(self) -> List[Scan]:
        """Retrieve all inactive scans.

        Returns:
            List[Scan]: A list of inactive Scan objects.
        """
        inactive = [s for s in self._data if not s.isactive]
        logger.debug(f"Retrieved {len(inactive)} inactive scans")
        return inactive

    def activate_scan(self, index: int) -> None:
        """Activate a specific scan by index.

        Args:
            index (int): The index of the scan to activate.

        Raises:
            IndexError: If index is out of range.
        """
        try:
            scan = self._data[index]
            scan.activate()
            logger.info(f"Activated scan at index {index} with start={scan.get_start().isot}")
        except IndexError:
            logger.error(f"Invalid scan index: {index}")
            raise IndexError("Invalid scan index!")

    def deactivate_scan(self, index: int) -> None:
        """Deactivate a specific scan by index.

        Args:
            index (int): The index of the scan to deactivate.

        Raises:
            IndexError: If index is out of range.
        """
        try:
            scan = self._data[index]
            scan.deactivate()
            logger.info(f"Deactivated scan at index {index} with start={scan.get_start().isot}")
        except IndexError:
            logger.error(f"Invalid scan index: {index}")
            raise IndexError("Invalid scan index!")

    def activate_all(self) -> None:
        """Activate all scans in the collection.

        Raises:
            ValueError: If the collection is empty.
        """
        if not self._data:
            logger.error("No scans to activate")
            raise ValueError("No scans to activate!")
        for s in self._data:
            s.activate()
        logger.info("Activated all scans")

    def deactivate_all(self) -> None:
        """Deactivate all scans in the collection.

        Raises:
            ValueError: If the collection is empty.
        """
        if not self._data:
            logger.error("No scans to deactivate")
            raise ValueError("No scans to deactivate!")
        for s in self._data:
            s.deactivate()
        logger.info("Deactivated all scans")

    def drop_active(self) -> None:
        """Remove all active scans from the collection."""
        initial_len = len(self._data)
        self._data = [s for s in self._data if not s.isactive]
        removed = initial_len - len(self._data)
        if removed > 0:
            logger.info(f"Removed {removed} active scans from Scans")
        else:
            logger.debug("No active scans to drop")

    def drop_inactive(self) -> None:
        """Remove all inactive scans from the collection."""
        initial_len = len(self._data)
        self._data = [s for s in self._data if s.isactive]
        removed = initial_len - len(self._data)
        if removed > 0:
            logger.info(f"Removed {removed} inactive scans from Scans")
        else:
            logger.debug("No inactive scans to drop")

    def clear(self) -> None:
        """Remove all scans from the collection."""
        logger.info(f"Cleared {len(self._data)} scans from Scans")
        self._data.clear()

    def to_dict(self) -> dict:
        """Convert the Scans object to a dictionary for serialization.

        Returns:
            dict: A dictionary containing a list of scan dictionaries under the 'data' key.
        """
        logger.info(f"Converted Scans with {len(self._data)} scans to dictionary")
        return {"data": [scan.to_dict() for scan in self._data]}

    @classmethod
    def from_dict(cls, data: dict) -> 'Scans':
        """Create a Scans object from a dictionary.

        Args:
            data (dict): Dictionary with a 'data' key containing a list of scan dictionaries.

        Returns:
            Scans: A new Scans instance initialized with the dictionary data.
        """
        scans = [Scan.from_dict(scan_data) for scan_data in data["data"]]
        logger.info(f"Created Scans with {len(scans)} scans from dictionary")
        return cls(scans=scans)

    def _check_overlap(self, scan: 'Scan', exclude_index: int = -1, observation: 'Observation' = None) -> tuple[bool, str]:
        """Check if a scan overlaps with existing active scans by time.

        Args:
            scan (Scan): The Scan object to check for overlap.
            exclude_index (int): Index to exclude from overlap check (e.g., for replacement). Defaults to -1.
            observation (Observation, optional): Observation object (not used here but included for consistency). Defaults to None.

        Returns:
            tuple[bool, str]: (overlap_detected, reason). True if overlap occurs, with a descriptive reason.
        """
        from unit_scheduling.base.observation import Observation
        for i, existing in enumerate(self._data):
            if i == exclude_index or not existing.isactive or not scan.isactive:
                continue
            scan_start = scan.get_start()
            scan_end = scan.get_end()
            existing_start = existing.get_start()
            existing_end = existing.get_end()
            time_overlap = (existing_start < scan_end and scan_start < existing_end)
            if time_overlap:
                reason = (f"overlaps with scan at index {i} (start={existing_start.isot}, "
                          f"duration={existing.get_duration()})")
                logger.debug(f"Overlap detected: {reason}")
                return True, reason
        logger.debug(f"No overlap detected for scan with start={scan.get_start().isot}")
        return False, ""

    def __len__(self) -> int:
        """Return the number of scans in the collection.

        Returns:
            int: The total count of Scan objects.
        """
        return len(self._data)

    def __repr__(self) -> str:
        """Return a string representation of the Scans object.

        Returns:
            str: A formatted string with the count of total, active, and inactive scans.
        """
        active_count = len(self.get_active_scans())
        return f"Scans(count={len(self._data)}, active={active_count}, inactive={len(self._data) - active_count})"