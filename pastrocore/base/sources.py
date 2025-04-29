# base/sources.py
from abc import ABC
from typing import Optional, Dict
from common.base.baseentity import BaseEntity
from common.base.basecontainer import BaseContainer
from common.utils.logging_setup import logger
import uuid

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
        if name is None:
            name = f"src_{uuid.uuid4().hex[:32]}"
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
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Source':
        """Create a Source instance from a dictionary, converting flux_table keys to float."""
        data = data.copy()
        data.pop("type", None)
        
        # Convert flux_table keys from str to float
        if "flux_table" in data and isinstance(data["flux_table"], dict):
            try:
                flux_table = {
                    float(key): float(value) if isinstance(value, (str, int, float)) else value
                    for key, value in data["flux_table"].items()
                }
                data["flux_table"] = flux_table
            except (ValueError, TypeError) as e:
                logger.error(f"Failed to convert flux_table keys to float: {str(e)}")
                raise ValueError(f"Invalid flux_table format: keys must be convertible to float, got {data['flux_table']}") from e

        kwargs = {}
        for key, value in data.items():
            if key in ("name", "isactive"):
                continue
            if key not in cls._fields:
                raise ValueError(f"Unknown attribute '{key}' for {cls.__name__}")
            expected_type = cls._resolve_type(cls._fields[key])
            if isinstance(expected_type, type) and issubclass(expected_type, BaseEntity) and isinstance(value, dict):
                kwargs[key] = expected_type.from_dict(value)
            else:
                kwargs[key] = value
        return cls(name=data.get("name"), isactive=data.get("isactive", True), **kwargs)

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
    def __init__(self, items: Dict[str, Source] = None, name: str = None, isactive: bool = True, use_cache: bool = False):
        """Initialize a Scans object with an optional dictionary of Scan objects."""
        if name is None:
            name = f"srcs_{uuid.uuid4().hex[:32]}"
        super().__init__(items=items, name=name, isactive=isactive)
        self._key_cache = list(self._items.keys()) if items else []
        logger.info(f"Initialized Sources with name={name}, {len(self._items)} sources")

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
    
    def set_source(
        self,
        name: str,
        ra_h: Optional[float] = None,
        ra_m: Optional[float] = None,
        ra_s: Optional[float] = None,
        de_d: Optional[float] = None,
        de_m: Optional[float] = None,
        de_s: Optional[float] = None,
        name_J2000: Optional[str] = None,
        alt_name: Optional[str] = None,
        flux_table: Optional[Dict[float, float]] = None,
        spectral_index: Optional[float] = None,
        isactive: Optional[bool] = None,
    ) -> None:
        """Update an existing Source object in the collection with provided parameters.

        Args:
            name (str): Name of the source to update.
            ra_h (Optional[float]): Right Ascension hours (0-23).
            ra_m (Optional[float]): Right Ascension minutes (0-59).
            ra_s (Optional[float]): Right Ascension seconds (0-59.999).
            de_d (Optional[float]): Declination degrees (-90 to 90).
            de_m (Optional[float]): Declination minutes (0-59).
            de_s (Optional[float]): Declination seconds (0-59.999).
            name_J2000 (Optional[str]): Source name in J2000 notation.
            alt_name (Optional[str]): Alternative source name.
            flux_table (Optional[Dict[float, float]]): Flux table mapping frequencies (MHz) to flux values (Jy).
            spectral_index (Optional[float]): Spectral index for flux extrapolation.
            isactive (Optional[bool]): Whether the source is active.

        Raises:
            KeyError: If the source with the given name does not exist.
            ValueError: If provided parameters fail validation.
        """
        if name not in self._items:
            raise KeyError(f"Source '{name}' not found in Sources")

        # Get the existing source
        existing_source = self._items[name]

        # Prepare parameters, using existing values if not provided
        params = {
            "name": name,
            "ra_h": ra_h if ra_h is not None else existing_source.ra_h,
            "ra_m": ra_m if ra_m is not None else existing_source.ra_m,
            "ra_s": ra_s if ra_s is not None else existing_source.ra_s,
            "de_d": de_d if de_d is not None else existing_source.de_d,
            "de_m": de_m if de_m is not None else existing_source.de_m,
            "de_s": de_s if de_s is not None else existing_source.de_s,
            "name_J2000": name_J2000 if name_J2000 is not None else existing_source.name_J2000,
            "alt_name": alt_name if alt_name is not None else existing_source.alt_name,
            "flux_table": flux_table if flux_table is not None else existing_source.flux_table,
            "spectral_index": spectral_index if spectral_index is not None else existing_source.spectral_index,
            "isactive": isactive if isactive is not None else existing_source.isactive,
        }

        # Create a new Source object to validate parameters
        updated_source = Source(**params)

        # Update the source in the collection
        self._items[name] = updated_source
        self._key_cache = list(self._items.keys())
        logger.info(f"Updated source '{name}' in Sources with params: {params}")
    
    def activate_item(self, name: str) -> None:
        """Activate a specific source by its name.

        Triggers synchronization with a parent Observation if present.

        Args:
            name (str): The name of the source to activate.

        Raises:
            KeyError: If the name is not found in the collection.
        """
        super().activate_item(name)
        if hasattr(self, '_parent') and self._parent:
            self._parent._sync_scans_with_activation("sources", name, True)

    def deactivate_item(self, name: str) -> None:
        """Deactivate a specific source by its name.

        Triggers synchronization with a parent Observation if present.

        Args:
            name (str): The name of the source to deactivate.

        Raises:
            KeyError: If the name is not found in the collection.
        """
        super().deactivate_item(name)
        if hasattr(self, '_parent') and self._parent:
            self._parent._sync_scans_with_activation("sources", name, False)

    @classmethod
    def from_dict(cls, data: dict) -> "Sources":
        """Create a Sources object from a dictionary"""
        data.pop("type", None)
        return super().from_dict(data)

    def __repr__(self) -> str:
        """Return a string representation of the Sources object."""
        active_count = len(self.get_active_items())
        attrs = [f"name={self.name!r}" if self.name else ""]
        attrs.append(f"count={len(self._items)}")
        attrs.append(f"active={active_count}")
        attrs.append(f"inactive={len(self._items) - active_count}")
        return f"Sources({', '.join(attr for attr in attrs if attr)})"