# base/sources.py
from copy import deepcopy
from typing import Annotated, Optional, Dict
from msb_arch.base.baseentity import BaseEntity
from msb_arch.base.basecontainer import BaseContainer
from msb_arch import InvariantError, invariant
from msb_arch.utils.logging_setup import logger
from msb_arch.utils.validation import Range
import math
import uuid

def _sexagesimal(value: float) -> tuple:
    """Split a positive decimal into whole units, whole minutes and seconds.

    Notes:
        - One place, because right ascension and declination were each doing it and each got it
          wrong the same way. Rounded to microseconds first, so 11.7308066500 does not come back
          as 43 minutes and 59.999999 seconds.
    """
    units = int(value)
    minutes_over = round((value - units) * 60, 9)
    minutes = int(minutes_over)
    seconds = round((minutes_over - minutes) * 60, 6)
    if seconds >= 60.0:
        seconds, minutes = 0.0, minutes + 1
    if minutes >= 60:
        minutes, units = 0, units + 1
    return float(units), float(minutes), seconds


class Source(BaseEntity):
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
    # The bounds are on the annotation rather than in a check called from `__init__`. The
    # check guarded construction and nothing else: `set` accepted ninety-nine hours of right
    # ascension, and so did `from_dict`, which is how a saved project carries one back.
    name: str
    ra_h: Annotated[float, Range(0, 23)]
    ra_m: Annotated[float, Range(0, 59)]
    ra_s: Annotated[float, Range(0, 59.999)]
    de_d: Annotated[float, Range(-90, 90)]
    de_m: Annotated[float, Range(0, 59)]
    de_s: Annotated[float, Range(0, 59.999)]
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
        logger.debug("Initialized Source '%s' at RA=%sh%sm%ss, DEC=%sd%sm%ss", name, ra_h, ra_m, ra_s, de_d, de_m, de_s)

    @invariant("a flux must be positive")
    def _fluxes_are_positive(self) -> bool:
        """A source radiates or it is not there, and a negative flux is neither.

        Raises:
            InvariantError: Naming the frequency and the value.

        Notes:
            - It was `_validate_flux_table`, called from `__init__` and nowhere else, so
              `set({"flux_table": {1000.0: -5.0}})` was accepted and `get_flux` handed the
              minus five straight to whatever asked -- a sensitivity, an integration time.
              The third of these found: the coordinate range and the polarization group were
              the same shape.
            - The *types* are MSB's, from the annotation, and it already refuses a key that is
              not a number. What an annotation cannot say is that the value must be above zero.
        """
        for frequency, flux in (self.flux_table or {}).items():
            if not isinstance(flux, (int, float)) or flux <= 0:
                raise InvariantError(
                    f"Source '{self.name}': flux at {frequency} MHz is {flux!r}; "
                    f"a flux must be positive")
        return True

    def get_flux(self, frequency: float) -> Optional[float]:
        """Retrieve the flux for a given frequency, with interpolation or extrapolation."""
        if not isinstance(frequency, (int, float)):
            raise TypeError(f"Frequency must be a number, got {type(frequency)}")
        if not self.flux_table:
            logger.warning("No flux data available for source '%s' at %s MHz", self.name, frequency)
            return None

        if frequency in self.flux_table:
            return self.flux_table[frequency]

        if self.spectral_index is not None and self.flux_table:
            ref_freq, ref_flux = next(iter(self.flux_table.items()))
            flux = ref_flux * (frequency / ref_freq) ** self.spectral_index
            logger.debug("Extrapolated flux=%s Jy for frequency %s MHz on '%s'", flux, frequency, self.name)
            return flux

        freqs = sorted(self.flux_table.keys())
        if frequency < freqs[0] or frequency > freqs[-1]:
            logger.debug("Frequency %s MHz out of flux table range for '%s'", frequency, self.name)
            return None
        for i in range(len(freqs) - 1):
            if freqs[i] <= frequency <= freqs[i + 1]:
                f1, f2 = freqs[i], freqs[i + 1]
                fl1, fl2 = self.flux_table[f1], self.flux_table[f2]
                interpolated_flux = fl1 + (fl2 - fl1) * (frequency - f1) / (f2 - f1)
                logger.debug("Interpolated flux=%s Jy for frequency %s MHz on '%s'", interpolated_flux, frequency, self.name)
                return interpolated_flux
        return None

    @property
    def ra_degrees(self) -> float:
        """Right Ascension in decimal degrees."""
        return (self.ra_h + self.ra_m / 60 + self.ra_s / 3600) * 15

    @property
    def dec_degrees(self) -> float:
        """Declination in decimal degrees.

        Notes:
            - The sign is taken with `copysign` rather than by comparing against zero, so that
              a source between -1 and 0 degrees comes back south of the equator. `de_d` is the
              only field that can carry the sign, and for those sources it is `-0.0`, which
              `>= 0` reads as positive.
        """
        sign = math.copysign(1.0, self.de_d)
        return sign * (abs(self.de_d) + self.de_m / 60 + self.de_s / 3600)

    def set_ra_degrees(self, ra_deg: float) -> None:
        """Set Right Ascension from decimal degrees.

        Notes:
            - **The hours field takes the whole hours and nothing else.** It used to take the
              whole value -- `338.1517` degrees became 22.543 hours, 32.6 minutes and 36.1
              seconds, and the fraction was then counted three times: reading it back gave
              346.455, eight degrees away. `ra_degrees` is what every calculation asks, so the
              source was simply somewhere else.
        """
        if not (0 <= ra_deg <= 360):
            raise ValueError(f"RA degrees must be in range [0, 360], got {ra_deg}")
        hours, minutes, seconds = _sexagesimal(ra_deg / 15)
        self.set({"ra_h": hours, "ra_m": minutes, "ra_s": seconds})
        logger.debug("Set RA=%s deg for source '%s'", ra_deg, self.name)

    def set_dec_degrees(self, dec_deg: float) -> None:
        """Set Declination from decimal degrees.

        Notes:
            - The same fault as `set_ra_degrees` had, and the same fix: the degrees field takes
              whole degrees, and the fraction goes to the minutes and seconds once.
            - The sign is carried by `de_d`, which is the only field that can: minutes and
              seconds are constrained to 0-59. For a source between -1 and 0 degrees that means
              **negative zero**, which is why `dec_degrees` reads the sign with `copysign`.
        """
        if not (-90 <= dec_deg <= 90):
            raise ValueError(f"DEC degrees must be in range [-90, 90], got {dec_deg}")
        degrees, minutes, seconds = _sexagesimal(abs(dec_deg))
        self.set({"de_d": math.copysign(degrees, dec_deg), "de_m": minutes, "de_s": seconds})
        logger.debug("Set DEC=%s deg for source '%s'", dec_deg, self.name)

    def add_flux(self, frequency: float, flux: float) -> None:
        """Add a flux value for a specific frequency."""
        if not isinstance(frequency, (int, float)):
            raise TypeError(f"Frequency must be a number, got {type(frequency)}")
        if not isinstance(flux, (int, float)) or flux <= 0:
            raise ValueError(f"Flux must be positive, got {flux}")
        new_flux_table = self.flux_table.copy()
        new_flux_table[frequency] = flux
        self.set({"flux_table": new_flux_table})
        logger.debug("Added flux=%s Jy for frequency %s MHz to source '%s'", flux, frequency, self.name)

    def remove_flux(self, frequency: float) -> None:
        """Remove a flux value for a specific frequency."""
        if not isinstance(frequency, (int, float)):
            raise TypeError(f"Frequency must be a number, got {type(frequency)}")
        new_flux_table = self.flux_table.copy()
        if frequency in new_flux_table:
            del new_flux_table[frequency]
            self.set({"flux_table": new_flux_table})
            logger.debug("Removed flux for frequency %s MHz from source '%s'", frequency, self.name)
        else:
            logger.warning("No flux value found for frequency %s MHz in source '%s'", frequency, self.name)

    def clear_flux_table(self) -> None:
        """Clear all entries from the flux table."""
        self.set({"flux_table": {}})
        logger.debug("Cleared flux table for source '%s'", self.name)
    
    def copy(self) -> 'Source':
        """Create a deep copy of the Source object."""
        return Source(
            name=self.name,
            ra_h=self.ra_h,
            ra_m=self.ra_m,
            ra_s=self.ra_s,
            de_d=self.de_d,
            de_m=self.de_m,
            de_s=self.de_s,
            name_J2000=self.name_J2000,
            alt_name=self.alt_name,
            flux_table=deepcopy(self.flux_table),
            spectral_index=self.spectral_index,
            isactive=self.isactive
        )
    

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
        logger.debug("Initialized Sources with name=%s, %s sources", name, len(self._items))

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
        logger.debug("Created and added source '%s' to Sources", name)
    
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

        existing_source = self._items[name]

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

        updated_source = Source(**params)

        self._items[name] = updated_source
        self._key_cache = list(self._items.keys())
        logger.debug("Updated source '%s' in Sources with params: %s", name, params)
    
    def copy(self) -> 'Sources':
        """Create a deep copy of the Sources object."""
        return Sources(
            name=self.name,
            items={name: item.copy() for name, item in self._items.items()},
            isactive=self.isactive,
            use_cache=self._use_cache
        )


    def __repr__(self) -> str:
        """Return a string representation of the Sources object."""
        active_count = len(self.get_active_items())
        attrs = [f"name={self.name!r}" if self.name else ""]
        attrs.append(f"count={len(self._items)}")
        attrs.append(f"active={active_count}")
        attrs.append(f"inactive={len(self._items) - active_count}")
        return f"Sources({', '.join(attr for attr in attrs if attr)})"