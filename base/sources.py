# base/sources.py
from base.base_entity import BaseEntity
from utils.validation import check_type, check_range, check_list_type
from utils.logging_setup import logger

class Source(BaseEntity):
    def __init__(self, name: str, ra_h: float, ra_m: float, ra_s: float, de_d: float, de_m: float, de_s: float,
                 name_J2000: str = None, alt_name: str = None, isactive: bool = True):
        """Initialize a Source object with name and J2000 coordinates.

        Args:
            name (str): Source name in B1950.
            ra_h (float): Right Ascension hours (0-23).
            ra_m (float): Right Ascension minutes (0-59).
            ra_s (float): Right Ascension seconds (0-59.999).
            de_d (float): Declination degrees (-90 to 90).
            de_m (float): Declination minutes (0-59).
            de_s (float): Declination seconds (0-59.999).
            name_J2000 (str, optional): Source name in J2000.
            alt_name (str, optional): Alternative source name (e.g., BL Lac).
            isactive (bool): Whether the source is active (default: True).
        """
        super().__init__(isactive)
        check_type(name, str, "Name")
        if name_J2000 is not None:
            check_type(name_J2000, str, "name_J2000")
        if alt_name is not None:
            check_type(alt_name, str, "alt_name")
        check_range(ra_h, 0, 23, "RA hours")
        check_range(ra_m, 0, 59, "RA minutes")
        check_range(ra_s, 0, 59.999, "RA seconds")
        check_range(de_d, -90, 90, "DEC degrees")
        check_range(de_m, 0, 59, "DEC minutes")
        check_range(de_s, 0, 59.999, "DEC seconds")
        self._name = name
        self._name_J2000 = name_J2000
        self._alt_name = alt_name
        self._ra_h = ra_h
        self._ra_m = ra_m
        self._ra_s = ra_s
        self._de_d = de_d
        self._de_m = de_m
        self._de_s = de_s
        logger.info(f"Initialized Source '{name}' at RA={ra_h}h{ra_m}m{ra_s}s, DEC={de_d}d{de_m}m{de_s}s")

    def set_source(self, name: str, ra_h: float, ra_m: float, ra_s: float, de_d: float, de_m: float, de_s: float,
                   name_J2000: str = None, alt_name: str = None, isactive: bool = True) -> None:
        """Set Source values."""
        check_type(name, str, "Name")
        if name_J2000 is not None:
            check_type(name_J2000, str, "name_J2000")
        if alt_name is not None:
            check_type(alt_name, str, "alt_name")
        check_range(ra_h, 0, 23, "RA hours")
        check_range(ra_m, 0, 59, "RA minutes")
        check_range(ra_s, 0, 59.999, "RA seconds")
        check_range(de_d, -90, 90, "DEC degrees")
        check_range(de_m, 0, 59, "DEC minutes")
        check_range(de_s, 0, 59.999, "DEC seconds")
        self._name = name
        self._name_J2000 = name_J2000
        self._alt_name = alt_name
        self._ra_h = ra_h
        self._ra_m = ra_m
        self._ra_s = ra_s
        self._de_d = de_d
        self._de_m = de_m
        self._de_s = de_s
        self.isactive = isactive
        logger.info(f"Set source '{name}' with new coordinates RA={ra_h}h{ra_m}m{ra_s}s, DEC={de_d}d{de_m}m{de_s}s")

    def set_coordinates_from_degrees(self, ra_deg: float, dec_deg: float) -> None:
        """Set source coordinates from RA and DEC in decimal degrees to hh:mm:ss and dd:mm:ss format.

        Args:
            ra_deg (float): Right Ascension in decimal degrees (0 to 360).
            dec_deg (float): Declination in decimal degrees (-90 to 90).
        """
        check_range(ra_deg, 0, 360, "RA degrees")
        check_range(dec_deg, -90, 90, "DEC degrees")
        # Нормализация RA до [0, 360)
        ra_deg = ra_deg % 360
        # Convert RA from deg to hh:mm:ss
        ra_hours = ra_deg / 15  # 360° = 24h, 1h = 15°
        self._ra_h = int(ra_hours)
        ra_minutes = (ra_hours - self._ra_h) * 60
        self._ra_m = int(ra_minutes)
        self._ra_s = (ra_minutes - self._ra_m) * 60
        # Convert DEC from deg to dd:mm:ss
        sign = 1 if dec_deg >= 0 else -1
        dec_abs = abs(dec_deg)
        self._de_d = sign * int(dec_abs)
        dec_minutes = (dec_abs - int(dec_abs)) * 60
        self._de_m = int(dec_minutes)
        self._de_s = (dec_minutes - self._de_m) * 60
        logger.info(f"Set coordinates from RA={ra_deg} deg, DEC={dec_deg} deg to RA={self._ra_h}h{self._ra_m}m{self._ra_s}s, DEC={self._de_d}d{self._de_m}m{self._de_s}s for source '{self._name}'")

    def activate(self) -> None:
        """Activate source."""
        super().activate()

    def deactivate(self) -> None:
        """Deactivate source."""
        super().deactivate()

    def get_name(self) -> str:
        """Get source name (B1950)."""
        return self._name

    def get_name_J2000(self) -> str | None:
        """Get source name in J2000."""
        return self._name_J2000

    def get_alt_name(self) -> str | None:
        """Get alternative source name."""
        return self._alt_name

    def get_ra(self) -> tuple[float, float, float]:
        """Get source RA in hh:mm:ss."""
        return self._ra_h, self._ra_m, self._ra_s

    def get_dec(self) -> tuple[float, float, float]:
        """Get source DEC in dd:mm:ss."""
        return self._de_d, self._de_m, self._de_s

    def get_source_coordinates(self) -> tuple[float, float, float, float, float, float]:
        """Get source RA, DEC in hh:mm:ss, dd:mm:ss."""
        return self._ra_h, self._ra_m, self._ra_s, self._de_d, self._de_m, self._de_s

    def get_ra_degrees(self) -> float:
        """Return RA in decimal degrees."""
        return (self._ra_h + self._ra_m / 60 + self._ra_s / 3600) * 15  # 15 = 360° / 24h

    def get_dec_degrees(self) -> float:
        """Return DEC in decimal degrees."""
        sign = 1 if self._de_d >= 0 else -1
        return sign * (abs(self._de_d) + self._de_m / 60 + self._de_s / 3600)

    def to_dict(self) -> dict:
        """Convert Source object to a dictionary for serialization."""
        logger.info(f"Converted source '{self._name}' to dictionary")
        return {
            "name": self._name,
            "ra_h": self._ra_h,
            "ra_m": self._ra_m,
            "ra_s": self._ra_s,
            "de_d": self._de_d,
            "de_m": self._de_m,
            "de_s": self._de_s,
            "name_J2000": self._name_J2000,
            "alt_name": self._alt_name,
            "isactive": self.isactive
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Source':
        """Create a Source object from a dictionary."""
        logger.info(f"Created source '{data['name']}' from dictionary")
        return cls(**data)

    def __repr__(self) -> str:
        """Return a string representation of Source."""
        names = f"name='{self._name}'"
        if self._name_J2000:
            names += f", name_J2000='{self._name_J2000}'"
        if self._alt_name:
            names += f", alt_name='{self._alt_name}'"
        return (f"Source({names}, RA={self._ra_h}h{self._ra_m}m{self._ra_s}s, "
                f"DEC={self._de_d}d{self._de_m}m{self._de_s}s, isactive={self.isactive})")

class Sources(BaseEntity):
    def __init__(self, sources: list[Source] = None):
        """Initialize Sources with a list of Source objects."""
        super().__init__()
        if sources is not None:
            check_list_type(sources, Source, "Sources")
        self._data = sources if sources is not None else []
        logger.info(f"Initialized Sources with {len(self._data)} sources")

    def _is_duplicate(self, source: 'Source', exclude_index: int = -1) -> bool:
        """Check if the source is a duplicate based on coordinates or names."""
        tolerance = 1e-6  # Допустимая погрешность для координат в градусах
        for i, existing in enumerate(self._data):
            if i == exclude_index:
                continue
            # Проверка по координатам
            if (abs(existing.get_ra_degrees() - source.get_ra_degrees()) < tolerance and
                abs(existing.get_dec_degrees() - source.get_dec_degrees()) < tolerance):
                return True
            # Проверка по именам
            if (existing.get_name() == source.get_name() or
                (existing.get_name_J2000() and source.get_name_J2000() and
                 existing.get_name_J2000() == source.get_name_J2000()) or
                (existing.get_alt_name() and source.get_alt_name() and
                 existing.get_alt_name() == source.get_alt_name())):
                return True
        return False

    def set_source(self, index: int, source: 'Source') -> None:
        """Set a source at a specific index."""
        check_type(source, Source, "Source")
        try:
            if self._is_duplicate(source, exclude_index=index):
                logger.error(f"Source with coordinates RA={source.get_ra_degrees():.6f} deg, "
                             f"DEC={source.get_dec_degrees():.6f} deg or matching names already exists at another index")
                raise ValueError(f"Duplicate source with coordinates or names!")
            self._data[index] = source
            logger.info(f"Set source '{source.get_name()}' at index {index}")
        except IndexError:
            logger.error(f"Invalid source index: {index}")
            raise IndexError("Invalid source index!")

    def add_source(self, source: 'Source') -> None:
        """Add a new source."""
        check_type(source, Source, "Source")
        if self._is_duplicate(source):
            logger.error(f"Source with coordinates RA={source.get_ra_degrees():.6f} deg, "
                         f"DEC={source.get_dec_degrees():.6f} deg or matching names already exists")
            raise ValueError(f"Duplicate source with coordinates or names!")
        self._data.append(source)
        logger.info(f"Added source '{source.get_name()}' to Sources")

    def remove_source(self, index: int) -> None:
        """Remove source by index."""
        try:
            self._data.pop(index)
            logger.info(f"Removed source at index {index} from Sources")
        except IndexError:
            logger.error(f"Invalid source index: {index}")
            raise IndexError("Invalid source index!")

    def get_source(self, index: int) -> 'Source':
        """Get source by index."""
        try:
            return self._data[index]
        except IndexError:
            logger.error(f"Invalid source index: {index}")
            raise IndexError("Invalid source index!")

    def get_all_sources(self) -> list['Source']:
        """Get all sources."""
        return self._data

    def get_active_sources(self) -> list['Source']:
        """Get active sources."""
        active = [src_obj for src_obj in self._data if src_obj.isactive]
        logger.debug(f"Retrieved {len(active)} active sources")
        return active

    def get_inactive_sources(self) -> list['Source']:
        """Get inactive sources."""
        inactive = [src_obj for src_obj in self._data if not src_obj.isactive]
        logger.debug(f"Retrieved {len(inactive)} inactive sources")
        return inactive

    def activate_all(self) -> None:
        """Activate all sources."""
        if not self._data:
            logger.error("No sources to activate")
            raise ValueError("No sources to activate!")
        for src_obj in self._data:
            src_obj.activate()
        logger.info("Activated all sources")

    def deactivate_all(self) -> None:
        """Deactivate all sources."""
        if not self._data:
            logger.error("No sources to deactivate")
            raise ValueError("No sources to deactivate!")
        for src_obj in self._data:
            src_obj.deactivate()
        logger.info("Deactivated all sources")

    def clear(self) -> None:
        """Clear sources data."""
        logger.info(f"Cleared {len(self._data)} sources from Sources")
        self._data.clear()

    def to_dict(self) -> dict:
        """Convert Sources object to a dictionary for serialization."""
        logger.info(f"Converted Sources with {len(self._data)} sources to dictionary")
        return {"data": [source.to_dict() for source in self._data]}

    @classmethod
    def from_dict(cls, data: dict) -> 'Sources':
        """Create a Sources object from a dictionary."""
        sources = [Source.from_dict(source_data) for source_data in data["data"]]
        logger.info(f"Created Sources with {len(sources)} sources from dictionary")
        return cls(sources=sources)

    def __len__(self) -> int:
        """Return the number of sources."""
        return len(self._data)

    def __repr__(self) -> str:
        """String representation of Sources."""
        active_count = len(self.get_active_sources())
        return f"Sources(count={len(self._data)}, active={active_count}, inactive={len(self._data) - active_count})"