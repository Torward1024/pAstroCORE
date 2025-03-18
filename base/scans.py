# base/scans.py
from base.base_entity import BaseEntity
from base.sources import Source
from base.telescopes import Telescopes, Telescope, SpaceTelescope
from base.frequencies import Frequencies
from utils.validation import check_type, check_positive
from utils.logging_setup import logger
from datetime import datetime
import numpy as np

from typing import Optional
from base.base_entity import BaseEntity
from base.sources import Source
from base.telescopes import Telescopes, Telescope, SpaceTelescope
from base.frequencies import Frequencies
from utils.validation import check_type, check_positive
from utils.logging_setup import logger
from datetime import datetime
import numpy as np

class Scan(BaseEntity):
    def __init__(self, start: float, duration: float, source: Optional[Source] = None,
                 telescopes: Telescopes = None, frequencies: Frequencies = None,
                 is_off_source: bool = False, isactive: bool = True):
        """Initialize a Scan object with start time, duration, source (optional), telescopes, and frequencies.

        Args:
            start (float): Scan start time in seconds (Unix timestamp, UTC).
            duration (float): Scan duration in seconds.
            source (Source, optional): Observed source object (None for OFF SOURCE).
            telescopes (Telescopes, optional): List of participating telescopes.
            frequencies (Frequencies, optional): List of observed frequencies with polarizations.
            is_off_source (bool): Whether this is an OFF SOURCE scan (default: False).
            isactive (bool): Whether the scan is active (default: True).
        """
        super().__init__(isactive)
        check_type(start, (int, float), "Start time")
        check_positive(duration, "Duration")
        if source is not None:
            check_type(source, Source, "Source")
        if telescopes is not None:
            check_type(telescopes, Telescopes, "Telescopes")
        if frequencies is not None:
            check_type(frequencies, Frequencies, "Frequencies")
        check_type(is_off_source, bool, "is_off_source")
        self._start = start
        self._duration = duration
        self._source = source
        self._telescopes = telescopes if telescopes is not None else Telescopes()
        self._frequencies = frequencies if frequencies is not None else Frequencies()
        self.is_off_source = is_off_source
        source_str = "OFF SOURCE" if is_off_source else (f"source '{source.get_name()}'" if source else "no source")
        logger.info(f"Initialized Scan with start={start}, duration={duration}, {source_str}")

    def validate_frequencies_and_sefd(self) -> bool:
        """Validate that all telescopes have SEFD defined for the scan's frequencies."""
        active_freqs = self._frequencies.get_active_frequencies()
        if not active_freqs:
            logger.warning(f"Scan with start={self._start} has no active frequencies")
            return False
        
        active_tels = self._telescopes.get_active_telescopes()
        if not active_tels:
            logger.warning(f"Scan with start={self._start} has no active telescopes")
            return False
        
        for freq_obj in active_freqs:
            freq = freq_obj.get_frequency()
            for tel in active_tels:
                sefd = tel.get_sefd(freq)
                if sefd is None:
                    logger.warning(f"Telescope '{tel.get_telescope_code()}' has no SEFD for frequency {freq} MHz")
                    return False
        logger.debug(f"Validated frequencies and SEFD for scan with start={self._start}")
        return True

    def set_scan(self, start: float, duration: float, source: Optional[Source] = None,
                 telescopes: Telescopes = None, frequencies: Frequencies = None,
                 is_off_source: bool = False, isactive: bool = True) -> None:
        """Set all values for the scan."""
        check_type(start, (int, float), "Start time")
        check_positive(duration, "Duration")
        if source is not None:
            check_type(source, Source, "Source")
        if telescopes is not None:
            check_type(telescopes, Telescopes, "Telescopes")
        if frequencies is not None:
            check_type(frequencies, Frequencies, "Frequencies")
        check_type(is_off_source, bool, "is_off_source")
        self._start = start
        self._duration = duration
        self._source = source
        self._telescopes = telescopes if telescopes is not None else Telescopes()
        self._frequencies = frequencies if frequencies is not None else Frequencies()
        self.is_off_source = is_off_source
        self.isactive = isactive
        source_str = "OFF SOURCE" if is_off_source else (f"source '{source.get_name()}'" if source else "no source")
        logger.info(f"Set Scan with start={start}, duration={duration}, {source_str}")

    def set_start(self, start: float) -> None:
        """Set scan start time in seconds."""
        check_type(start, (int, float), "Start time")
        self._start = start
        logger.info(f"Set scan start to {start}")

    def set_duration(self, duration: float) -> None:
        """Set scan duration in seconds."""
        check_positive(duration, "Duration")
        self._duration = duration
        logger.info(f"Set scan duration to {duration}")

    def set_source(self, source: Optional[Source]) -> None:
        """Set scan source (can be None for OFF SOURCE)."""
        if source is not None:
            check_type(source, Source, "Source")
        self._source = source
        self.is_off_source = source is None
        logger.info(f"Set scan source to {'OFF SOURCE' if source is None else f"'{source.get_name()}'"}")

    def set_telescopes(self, telescopes: Telescopes) -> None:
        """Set scan telescopes."""
        if telescopes is not None:
            check_type(telescopes, Telescopes, "Telescopes")
        self._telescopes = telescopes if telescopes is not None else Telescopes()
        logger.info(f"Set scan telescopes with {len(self._telescopes.get_all_telescopes())} items")

    def set_frequencies(self, frequencies: Frequencies) -> None:
        """Set scan frequencies with polarizations."""
        if frequencies is not None:
            check_type(frequencies, Frequencies, "Frequencies")
        self._frequencies = frequencies if frequencies is not None else Frequencies()
        logger.info(f"Set scan frequencies with {len(self._frequencies.get_data())} items (polarizations included)")

    def get_start(self) -> float:
        """Get scan start time in seconds."""
        return self._start

    def get_start_datetime(self) -> datetime:
        """Get scan start time as a datetime object (UTC)."""
        return datetime.fromtimestamp(self._start)

    def get_MJD_starttime(self) -> float:
        """Get scan start time in Modified Julian Date (MJD)."""
        return (self._start / 86400) + 40587

    def get_MJD_endtime(self) -> float:
        """Get scan end time in Modified Julian Date (MJD)."""
        return ((self._start + self._duration) / 86400) + 40587

    def get_duration(self) -> float:
        """Get scan duration in seconds."""
        return self._duration

    def get_source(self) -> Optional[Source]:
        """Get source from scan (None if OFF SOURCE)."""
        return self._source

    def get_telescopes(self) -> Telescopes:
        """Get telescopes from scan."""
        return self._telescopes

    def get_frequencies(self) -> Frequencies:
        """Get frequencies from scan."""
        return self._frequencies

    def get_end(self) -> float:
        """Get end of the scan in seconds."""
        return self._start + self._duration

    def get_end_datetime(self) -> datetime:
        """Get scan end time as a datetime object (UTC)."""
        return datetime.fromtimestamp(self._start + self._duration)

    def activate(self) -> None:
        """Activate scan."""
        super().activate()

    def deactivate(self) -> None:
        """Deactivate scan."""
        super().deactivate()

    def to_dict(self) -> dict:
        """Convert Scan object to a dictionary for serialization."""
        logger.info(f"Converted scan with start={self._start} to dictionary")
        return {
            "start": self._start,
            "duration": self._duration,
            "source": self._source.to_dict() if self._source is not None else None,
            "telescopes": self._telescopes.to_dict(),
            "frequencies": self._frequencies.to_dict(),
            "is_off_source": self.is_off_source,
            "isactive": self.isactive
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Scan':
        """Create a Scan object from a dictionary."""
        logger.info(f"Created scan with start={data['start']} from dictionary")
        return cls(
            start=data["start"],
            duration=data["duration"],
            source=Source.from_dict(data["source"]) if data["source"] is not None else None,
            telescopes=Telescopes.from_dict(data["telescopes"]),
            frequencies=Frequencies.from_dict(data["frequencies"]),
            is_off_source=data["is_off_source"],
            isactive=data["isactive"]
        )

    def __repr__(self) -> str:
        """Return a string representation of Scan."""
        source_str = "OFF SOURCE" if self.is_off_source else f"source={self._source}" if self._source else "no source"
        freq_str = f"frequencies={len(self._frequencies)} (with polarizations)"
        return (f"Scan(start={self._start}, duration={self._duration}, {source_str}, "
                f"telescopes={self._telescopes}, {freq_str}, isactive={self.isactive})")

class Scans(BaseEntity):
    def __init__(self, scans: list[Scan] = None):
        """Initialize Scans with a list of Scan objects."""
        super().__init__()
        if scans is not None:
            check_type(scans, (list, tuple), "Scans")
            for scan in scans:
                check_type(scan, Scan, "Scan")
        self._data = scans if scans is not None else []
        logger.info(f"Initialized Scans with {len(self._data)} scans")

    def _check_overlap(self, scan: 'Scan', exclude_index: int = -1) -> tuple[bool, str]:
        """Check if the scan overlaps with existing scans by time and telescopes (source optional)."""
        for i, existing in enumerate(self._data):
            if i == exclude_index or not existing.isactive:
                continue
            # Проверка пересечения по времени
            time_overlap = (existing.get_start() < scan.get_start() + scan.get_duration() and
                            scan.get_start() < existing.get_start() + existing.get_duration())
            if not time_overlap:
                continue
            # Проверка по телескопам
            existing_tels = {t.get_telescope_code() for t in existing.get_telescopes().get_active_telescopes()}
            new_tels = {t.get_telescope_code() for t in scan.get_telescopes().get_active_telescopes()}
            common_tels = existing_tels.intersection(new_tels)
            if common_tels:
                return True, f"overlaps with scan {i} by telescopes {common_tels}"
        return False, ""

    def add_scan(self, scan: 'Scan') -> None:
        """Add a new scan with overlap checking for time, source, and telescopes."""
        check_type(scan, Scan, "Scan")
        overlap, reason = self._check_overlap(scan)
        if overlap:
            logger.error(f"Scan with start={scan.get_start()}, duration={scan.get_duration()} {reason}")
            raise ValueError(f"Scan conflicts: {reason}")
        self._data.append(scan)
        logger.info(f"Added scan with start={scan.get_start()}, duration={scan.get_duration()} to Scans")

    def set_scan(self, scan: 'Scan', index: int) -> None:
        """Set scan data by index with overlap checking."""
        check_type(scan, Scan, "Scan")
        try:
            overlap, reason = self._check_overlap(scan, exclude_index=index)
            if overlap:
                logger.error(f"Scan with start={scan.get_start()}, duration={scan.get_duration()} {reason}")
                raise ValueError(f"Scan conflicts: {reason}")
            self._data[index] = scan
            logger.info(f"Set scan with start={scan.get_start()} at index {index}")
        except IndexError:
            logger.error(f"Invalid scan index: {index}")
            raise IndexError("Invalid scan index!")

    def check_telescope_availability(self, time: float, source: Optional[Source] = None) -> dict[str, bool]:
        """Check telescope availability and source visibility at a given time, considering polarizations."""
        check_type(time, (int, float), "Time")
        availability = {}
        dt = datetime.fromtimestamp(time)
        active_scans = self.get_active_scans()
        if not active_scans:
            logger.debug(f"No active scans at time={time}")
            return availability
        
        for scan in active_scans:
            if scan.get_start() <= time <= scan.get_end():
                if scan.is_off_source:
                    for telescope in scan.get_telescopes().get_active_telescopes():
                        availability[telescope.get_telescope_code()] = True
                    continue
                current_source = source or scan.get_source()
                ra_rad = np.radians(current_source.get_ra_degrees())
                dec_rad = np.radians(current_source.get_dec_degrees())
                lst = (time / 86164.0905 * 360 + 280.46061837) % 360  # Примерная формула
                for telescope in scan.get_telescopes().get_active_telescopes():
                    code = telescope.get_telescope_code()
                    if isinstance(telescope, SpaceTelescope):
                        pos, _ = telescope.get_position_at_time(dt)
                        dist = np.linalg.norm(pos)
                        visible = dist < 1e9  # Условный порог
                    else:
                        x, y, z = telescope.get_telescope_coordinates()
                        lat = np.arcsin(z / np.sqrt(x**2 + y**2 + z**2))
                        ha = np.radians(lst - current_source.get_ra_degrees())
                        alt = np.arcsin(np.sin(lat) * np.sin(dec_rad) + 
                                        np.cos(lat) * np.cos(dec_rad) * np.cos(ha))
                        visible = alt > np.radians(15)
                    # Учитываем поляризации (например, проверка поддержки телескопом)
                    freqs = scan.get_frequencies().get_active_frequencies()
                    polarizations = {f.get_polarization() for f in freqs}
                    if polarizations and not all(p in {"RCP", "LCP", "H", "V"} for p in polarizations):
                        visible = False  # Условно: сложные поляризации (LL, RL, RR, LR) не поддерживаются всеми телескопами
                    availability[code] = visible
        logger.debug(f"Checked telescope availability at time={time}: {availability}")
        return availability
    
    def validate_all_sefd(self) -> bool:
        """Validate SEFD availability for all active scans."""
        active_scans = self.get_active_scans()
        if not active_scans:
            logger.warning("No active scans to validate SEFD")
            return False
        return all(scan.validate_frequencies_and_sefd() for scan in active_scans)

    def remove_scan(self, index: int) -> None:
        """Remove scan by index."""
        try:
            self._data.pop(index)
            logger.info(f"Removed scan at index {index} from Scans")
        except IndexError:
            logger.error(f"Invalid scan index: {index}")
            raise IndexError("Invalid scan index!")

    def get_scan(self, index: int) -> Scan:
        """Get scan by index."""
        try:
            return self._data[index]
        except IndexError:
            logger.error(f"Invalid scan index: {index}")
            raise IndexError("Invalid scan index!")

    def get_all_scans(self) -> list[Scan]:
        """Get all scans."""
        return self._data

    def get_active_scans(self) -> list[Scan]:
        """Get active scans."""
        active = [s for s in self._data if s.isactive]
        logger.debug(f"Retrieved {len(active)} active scans")
        return active

    def get_inactive_scans(self) -> list[Scan]:
        """Get inactive scans."""
        inactive = [s for s in self._data if not s.isactive]
        logger.debug(f"Retrieved {len(inactive)} inactive scans")
        return inactive

    def activate_all(self) -> None:
        """Activate all scans."""
        if not self._data:
            logger.error("No scans to activate")
            raise ValueError("No scans to activate!")
        for s in self._data:
            s.activate()
        logger.info("Activated all scans")

    def deactivate_all(self) -> None:
        """Deactivate all scans."""
        if not self._data:
            logger.error("No scans to deactivate")
            raise ValueError("No scans to deactivate!")
        for s in self._data:
            s.deactivate()
        logger.info("Deactivated all scans")

    def clear(self) -> None:
        """Clear scans data."""
        logger.info(f"Cleared {len(self._data)} scans from Scans")
        self._data.clear()

    def to_dict(self) -> dict:
        """Convert Scans object to a dictionary for serialization."""
        logger.info(f"Converted Scans with {len(self._data)} scans to dictionary")
        return {"data": [scan.to_dict() for scan in self._data]}

    @classmethod
    def from_dict(cls, data: dict) -> 'Scans':
        """Create a Scans object from a dictionary."""
        scans = [Scan.from_dict(scan_data) for scan_data in data["data"]]
        logger.info(f"Created Scans with {len(scans)} scans from dictionary")
        return cls(scans=scans)

    def __len__(self) -> int:
        """Return the number of scans."""
        return len(self._data)

    def __repr__(self) -> str:
        """Return a string representation of Scans."""
        active_count = len(self.get_active_scans())
        return f"Scans(count={len(self._data)}, active={active_count}, inactive={len(self._data) - active_count})"