# base/sources.py
from abc import ABC
from typing import Optional, Dict
from common.base.baseentity import BaseEntity
from common.base.basecontainer import BaseContainer
from common.utils.logging_setup import logger

class Source(BaseEntity, ABC):
    """Base class representing an astronomical source with coordinates, names, and optional flux properties.

    Attributes:
        name (str): Source name in B1950 notation.
        ra_h (float): Right Ascension hours (0-23).
        ra_m (float): Right Ascension minutes (0-59).
        ra_s (float): Right Ascension seconds (0-59.999).
        de_d (float): Declination degrees (-90 to 90).
        de_m (float): Declination minutes (0-59).
        de_s (float): Declination seconds (0-59.999).
        name_J2000 (Optional[str]): Source name in J2000 notation.
        alt_name (Optional[str]): Alternative source name.
        flux_table (Dict[float, float]): Flux table mapping frequencies (MHz) to flux values (Jy).
        spectral_index (Optional[float]): Spectral index for flux extrapolation.
        isactive (bool): Whether the source is active.
    """
    name: str
    ra_h: float
    ra_m: float
    ra_s: float
    de_d: float
    de_m: float
    de_s: float
    name_J2000: Optional[str]
    alt_name: Optional[str]
    flux_table: Dict[float, float]
    spectral_index: Optional[float]

    def __init__(
        self,
        name: str = "SOURCE_DEFAULT",
        ra_h: float = 0.0,
        ra_m: float = 0.0,
        ra_s: float = 0.0,
        de_d: float = 0.0,
        de_m: float = 0.0,
        de_s: float = 0.0,
        name_J2000: Optional[str] = None,
        alt_name: Optional[str] = None,
        flux_table: Optional[Dict[float, float]] = None,
        spectral_index: Optional[float] = None,
        isactive: bool = True,
    ):
        super().__init__(
            name=name,
            ra_h=ra_h,
            ra_m=ra_m,
            ra_s=ra_s,
            de_d=de_d,
            de_m=de_m,
            de_s=de_s,
            name_J2000=name_J2000,
            alt_name=alt_name,
            flux_table=flux_table or {},
            spectral_index=spectral_index,
            isactive=isactive,
        )
        self._validate_coordinates()
        self._validate_flux_table()
        logger.info(f"Initialized Source '{name}' at RA={ra_h}h{ra_m}m{ra_s}s, DEC={de_d}d{de_m}m{de_s}s")

    def _validate_coordinates(self) -> None:
        """Validate coordinate ranges."""
        if not (0 <= self.ra_h <= 23):
            raise ValueError(f"RA hours must be in range [0, 23], got {self.ra_h}")
        if not (0 <= self.ra_m <= 59):
            raise ValueError(f"RA minutes must be in range [0, 59], got {self.ra_m}")
        if not (0 <= self.ra_s <= 59.999):
            raise ValueError(f"RA seconds must be in range [0, 59.999], got {self.ra_s}")
        if not (-90 <= self.de_d <= 90):
            raise ValueError(f"DEC degrees must be in range [-90, 90], got {self.de_d}")
        if not (0 <= self.de_m <= 59):
            raise ValueError(f"DEC minutes must be in range [0, 59], got {self.de_m}")
        if not (0 <= self.de_s <= 59.999):
            raise ValueError(f"DEC seconds must be in range [0, 59.999], got {self.de_s}")

    def _validate_flux_table(self) -> None:
        """Validate flux table entries."""
        for freq, flux in self.flux_table.items():
            if not isinstance(freq, (int, float)):
                raise TypeError(f"Flux frequency must be a number, got {type(freq)}")
            if not isinstance(flux, (int, float)) or flux <= 0:
                raise ValueError(f"Flux at {freq} MHz must be positive, got {flux}")

    def get_flux(self, frequency: float) -> Optional[float]:
        """Retrieve the flux for a given frequency, with interpolation or extrapolation."""
        if not isinstance(frequency, (int, float)):
            raise TypeError(f"Frequency must be a number, got {type(frequency)}")
        if not self.flux_table:
            logger.warning(f"No flux data available for source '{self.name}' at {frequency} MHz")
            return None

        if frequency in self.flux_table:
            return self.flux_table[frequency]

        if self.spectral_index is not None and self.flux_table:
            ref_freq, ref_flux = next(iter(self.flux_table.items()))
            flux = ref_flux * (frequency / ref_freq) ** self.spectral_index
            logger.debug(f"Extrapolated flux={flux} Jy for frequency {frequency} MHz on '{self.name}'")
            return flux

        freqs = sorted(self.flux_table.keys())
        if frequency < freqs[0] or frequency > freqs[-1]:
            logger.debug(f"Frequency {frequency} MHz out of flux table range for '{self.name}'")
            return None
        for i in range(len(freqs) - 1):
            if freqs[i] <= frequency <= freqs[i + 1]:
                f1, f2 = freqs[i], freqs[i + 1]
                fl1, fl2 = self.flux_table[f1], self.flux_table[f2]
                interpolated_flux = fl1 + (fl2 - fl1) * (frequency - f1) / (f2 - f1)
                logger.debug(f"Interpolated flux={interpolated_flux} Jy for frequency {frequency} MHz on '{self.name}'")
                return interpolated_flux
        return None

    @property
    def ra_degrees(self) -> float:
        """Right Ascension in decimal degrees."""
        return (self.ra_h + self.ra_m / 60 + self.ra_s / 3600) * 15

    @property
    def dec_degrees(self) -> float:
        """Declination in decimal degrees."""
        sign = 1 if self.de_d >= 0 else -1
        return sign * (abs(self.de_d) + self.de_m / 60 + self.de_s / 3600)

    def set_ra_degrees(self, ra_deg: float) -> None:
        """Set Right Ascension from decimal degrees."""
        if not (0 <= ra_deg <= 360):
            raise ValueError(f"RA degrees must be in range [0, 360], got {ra_deg}")
        ra_hours = ra_deg / 15
        self.set({"ra_h": ra_hours, "ra_m": ((ra_hours % 1) * 60), "ra_s": ((ra_hours % 1) * 60 % 1) * 60})
        logger.info(f"Set RA={ra_deg} deg for source '{self.name}'")

    def set_dec_degrees(self, dec_deg: float) -> None:
        """Set Declination from decimal degrees."""
        if not (-90 <= dec_deg <= 90):
            raise ValueError(f"DEC degrees must be in range [-90, 90], got {dec_deg}")
        sign = 1 if dec_deg >= 0 else -1
        dec_abs = abs(dec_deg)
        self.set(
            {
                "de_d": sign * (dec_abs),
                "de_m": ((dec_abs % 1) * 60),
                "de_s": ((dec_abs % 1) * 60 % 1) * 60,
            }
        )
        logger.info(f"Set DEC={dec_deg} deg for source '{self.name}'")

    def add_flux(self, frequency: float, flux: float) -> None:
        """Add a flux value for a specific frequency."""
        if not isinstance(frequency, (int, float)):
            raise TypeError(f"Frequency must be a number, got {type(frequency)}")
        if not isinstance(flux, (int, float)) or flux <= 0:
            raise ValueError(f"Flux must be positive, got {flux}")
        new_flux_table = self.flux_table.copy()
        new_flux_table[frequency] = flux
        self.set({"flux_table": new_flux_table})
        logger.info(f"Added flux={flux} Jy for frequency {frequency} MHz to source '{self.name}'")

    def remove_flux(self, frequency: float) -> None:
        """Remove a flux value for a specific frequency."""
        if not isinstance(frequency, (int, float)):
            raise TypeError(f"Frequency must be a number, got {type(frequency)}")
        new_flux_table = self.flux_table.copy()
        if frequency in new_flux_table:
            del new_flux_table[frequency]
            self.set({"flux_table": new_flux_table})
            logger.info(f"Removed flux for frequency {frequency} MHz from source '{self.name}'")
        else:
            logger.warning(f"No flux value found for frequency {frequency} MHz in source '{self.name}'")

    def clear_flux_table(self) -> None:
        """Clear all entries from the flux table."""
        self.set({"flux_table": {}})
        logger.info(f"Cleared flux table for source '{self.name}'")

    def __repr__(self) -> str:
        """Return a string representation of the Source object."""
        names = f"name='{self.name}'"
        if self.name_J2000:
            names += f", name_J2000='{self.name_J2000}'"
        if self.alt_name:
            names += f", alt_name='{self.alt_name}'"
        flux_info = f", flux_table={self.flux_table}" if self.flux_table else ""
        spec_info = f", spectral_index={self.spectral_index}" if self.spectral_index is not None else ""
        return (
            f"Source({names}, RA={self.ra_h}h{self.ra_m}m{self.ra_s}s, "
            f"DEC={self.de_d}d{self.de_m}m{self.de_s}s{flux_info}{spec_info}, isactive={self.isactive})"
        )

class Sources(BaseContainer[Source]):
    """Base class representing a collection of Source objects.

    Manages a dictionary of astronomical sources indexed by their B1950 names,
    ensuring uniqueness and providing methods for querying and manipulation.

    Attributes:
        _items (Dict[str, Source]): Dictionary mapping source names to Source objects.
        isactive (bool): Whether the Sources object itself is active.
    """

    def create_source(
        self,
        name: str = "SOURCE_DEFAULT",
        ra_h: float = 0.0,
        ra_m: float = 0.0,
        ra_s: float = 0.0,
        de_d: float = 0.0,
        de_m: float = 0.0,
        de_s: float = 0.0,
        name_J2000: Optional[str] = None,
        alt_name: Optional[str] = None,
        flux_table: Optional[Dict[float, float]] = None,
        spectral_index: Optional[float] = None,
        isactive: bool = True,
    ) -> None:
        """Create and add a new Source object to the collection."""
        new_source = Source(
            name=name,
            ra_h=ra_h,
            ra_m=ra_m,
            ra_s=ra_s,
            de_d=de_d,
            de_m=de_m,
            de_s=de_s,
            name_J2000=name_J2000,
            alt_name=alt_name,
            flux_table=flux_table or {},
            spectral_index=spectral_index,
            isactive=isactive,
        )
        self.add(new_source)
        logger.info(f"Created and added source '{name}' to Sources")

    @classmethod
    def from_dict(cls, data: dict) -> "Sources":
        """Create a Sources object from a dictionary, supporting legacy format."""
        if "data" in data:
            # Legacy format: {"data": [...]}
            items = {item_data["name"]: Source.from_dict(item_data) for item_data in data["data"]}
            return cls(items=items, name=data.get("name"), isactive=data.get("isactive", True))
        # New format: {"items": {...}}
        return super().from_dict(data)

    def __repr__(self) -> str:
        """Return a string representation of the Sources object."""
        active_count = len(self.get_active_items())
        return f"Sources(count={len(self._items)}, active={active_count}, inactive={len(self._items) - active_count})"