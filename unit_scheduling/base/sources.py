# base/sources.py
from common.base.base_entity import BaseEntity
from common.utils.validation import check_type, check_range, check_list_type, check_positive
from common.utils.logging_setup import logger
from typing import Optional, Dict

class Source(BaseEntity):
    """Base class representing an astronomical source with coordinates, names, and optional flux properties.

    This class encapsulates the properties of an astronomical source, including its name (B1950), J2000 coordinates
    (Right Ascension and Declination), optional J2000 name, alternative name, flux table, and spectral index.
    Coordinates can be set or retrieved in both sexagesimal (hh:mm:ss, dd:mm:ss) and decimal degree formats.
    Flux values can be stored for specific frequencies, with interpolation or extrapolation using a spectral index.

    Attributes:
        _name (str): Source name in B1950 notation.
        _ra_h (float): Right Ascension hours (0-23).
        _ra_m (float): Right Ascension minutes (0-59).
        _ra_s (float): Right Ascension seconds (0-59.999).
        _de_d (float): Declination degrees (-90 to 90).
        _de_m (float): Declination minutes (0-59).
        _de_s (float): Declination seconds (0-59.999).
        _name_J2000 (Optional[str]): Source name in J2000 notation. Defaults to None.
        _alt_name (Optional[str]): Alternative source name (e.g., 'BL Lac'). Defaults to None.
        _flux_table (Dict[float, float]): Flux table mapping frequencies (MHz) to flux values (Jy). Defaults to empty dict.
        _spectral_index (Optional[float]): Spectral index for flux extrapolation (F ~ nu^alpha). Defaults to None.
        isactive (bool): Whether the source is active. Inherited from BaseEntity.

    Notes:
        - RA and DEC are stored in sexagesimal format internally but can be converted to/from decimal degrees.
        - Flux extrapolation uses the spectral index if provided; otherwise, linear interpolation is used between
          table values. If neither is available, flux queries outside the table return None.
        - Logging is integrated via `common.utils.logging_setup.logger` to track operations and errors.

    Examples:
        >>> src = Source(name="3C 273", ra_h=12, ra_m=29, ra_s=6.7, de_d=2, de_m=2, de_s=0.2, flux_table={1420: 45.0}, spectral_index=-0.7)
        >>> print(src)
        Source(name='3C 273', RA=12h29m6.7s, DEC=2d2m0.2s, flux_table={1420: 45.0}, spectral_index=-0.7, isactive=True)
        >>> src.get_flux(1500)  # Extrapolated using spectral index
        43.127...  # Approximate value based on F ~ nu^-0.7
        >>> src.get_source_coordinates_deg()
        (187.27791666666666, 2.033388888888889)
    """
    def __init__(self, name: str = "SOURCE_DEFAULT", ra_h: float = 0.0, ra_m: float = 0.0, ra_s: float = 0.0,
                 de_d: float = 0.0, de_m: float = 0.0, de_s: float = 0.0,
                 name_J2000: Optional[str] = None, alt_name: Optional[str] = None,
                 flux_table: Optional[Dict[float, float]] = None,
                 spectral_index: Optional[float] = None,
                 isactive: bool = True):
        """Initialize a Source object with name, coordinates, and optional flux properties.

        Args:
            name (str): Source name in B1950 notation. Defaults to "SOURCE_DEFAULT".
            ra_h (float): Right Ascension hours (0-23). Defaults to 0.0.
            ra_m (float): Right Ascension minutes (0-59). Defaults to 0.0.
            ra_s (float): Right Ascension seconds (0-59.999). Defaults to 0.0.
            de_d (float): Declination degrees (-90 to 90). Defaults to 0.0.
            de_m (float): Declination minutes (0-59). Defaults to 0.0.
            de_s (float): Declination seconds (0-59.999). Defaults to 0.0.
            name_J2000 (Optional[str]): Source name in J2000 notation. Defaults to None.
            alt_name (Optional[str]): Alternative source name. Defaults to None.
            flux_table (Optional[Dict[float, float]]): Flux table (MHz: Jy). Defaults to None (empty dict).
            spectral_index (Optional[float]): Spectral index for flux extrapolation. Defaults to None.
            isactive (bool): Whether the source is active. Defaults to True.

        Raises:
            TypeError: If name, name_J2000, or alt_name are not strings; flux_table is not a dict; or spectral_index is not a number.
            ValueError: If RA/DEC components are out of range or flux values are not positive.
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
        if flux_table is not None:
            check_type(flux_table, dict, "Flux table")
            for freq, flux in flux_table.items():
                check_type(freq, (int, float), "Flux frequency")
                check_positive(flux, f"Flux at {freq} MHz")
        if spectral_index is not None:
            check_type(spectral_index, (int, float), "Spectral index")

        self._name = name
        self._name_J2000 = name_J2000
        self._alt_name = alt_name
        self._ra_h = ra_h
        self._ra_m = ra_m
        self._ra_s = ra_s
        self._de_d = de_d
        self._de_m = de_m
        self._de_s = de_s
        self._flux_table = flux_table if flux_table is not None else {}
        self._spectral_index = spectral_index
        logger.info(f"Initialized Source '{name}' at RA={ra_h}h{ra_m}m{ra_s}s, DEC={de_d}d{de_m}m{de_s}s")
    
    def add_flux(self, frequency: float, flux: float) -> None:
        """Add a flux value for a specific frequency to the flux table.

        Args:
            frequency (float): Frequency in MHz.
            flux (float): Flux value in Jy. Must be positive.

        Raises:
            TypeError: If frequency or flux are not numbers.
            ValueError: If flux is not positive.
        """
        check_type(frequency, (int, float), "Frequency")
        check_positive(flux, "Flux")
        self._check_flux(frequency, flux)
        self._flux_table[frequency] = flux
        logger.info(f"Added flux={flux} Jy for frequency {frequency} MHz to source '{self._name}'")
    
    def insert_flux(self, frequency: float, flux: float) -> None:
        """Insert a flux value for a specific frequency into the flux table (alias for add_flux).

        Args:
            frequency (float): Frequency in MHz.
            flux (float): Flux value in Jy. Must be positive.

        Raises:
            TypeError: If frequency or flux are not numbers.
            ValueError: If flux is not positive.
        """
        check_type(frequency, (int, float), "Frequency")
        check_positive(flux, "Flux")
        self._check_flux(frequency, flux)
        self._flux_table[frequency] = flux
        logger.info(f"Inserted flux={flux} Jy for frequency {frequency} MHz into source '{self._name}'")
    
    def remove_flux(self, frequency: float) -> None:
        """Remove a flux value for a specific frequency from the flux table.

        Args:
            frequency (float): Frequency in MHz to remove.

        Raises:
            TypeError: If frequency is not a number.
        """
        check_type(frequency, (int, float), "Frequency")
        if frequency in self._flux_table:
            removed_flux = self._flux_table.pop(frequency)
            logger.info(f"Removed flux={removed_flux} Jy for frequency {frequency} MHz from source '{self._name}'")
        else:
            logger.warning(f"No flux value found for frequency {frequency} MHz in source '{self._name}'")

    def activate(self) -> None:
        """Activate the source, marking it as active."""
        super().activate()

    def deactivate(self) -> None:
        """Deactivate the source, marking it as inactive."""
        super().deactivate()

    def get_name(self) -> str:
        """Retrieve the source name in B1950 notation.

        Returns:
            str: The B1950 source name.
        """
        return self._name

    def get_name_J2000(self) -> str | None:
        """Retrieve the source name in J2000 notation.

        Returns:
            str | None: The J2000 name, or None if not set.
        """
        return self._name_J2000

    def get_alt_name(self) -> str | None:
        """Retrieve the alternative source name.

        Returns:
            str | None: The alternative name, or None if not set.
        """
        return self._alt_name

    def get_ra(self) -> tuple[float, float, float]:
        """Retrieve the Right Ascension in sexagesimal format (hh:mm:ss).

        Returns:
            tuple[float, float, float]: A tuple of (hours, minutes, seconds).
        """
        return self._ra_h, self._ra_m, self._ra_s

    def get_dec(self) -> tuple[float, float, float]:
        """Retrieve the Declination in sexagesimal format (dd:mm:ss).

        Returns:
            tuple[float, float, float]: A tuple of (degrees, minutes, seconds).
        """
        return self._de_d, self._de_m, self._de_s
    
    def get_ra_degrees(self) -> float:
        """Retrieve the Right Ascension in decimal degrees.

        Returns:
            float: RA in degrees (0 to 360), calculated as (hours + minutes/60 + seconds/3600) * 15.
        """
        return (self._ra_h + self._ra_m / 60 + self._ra_s / 3600) * 15  # 15 = 360° / 24h

    def get_dec_degrees(self) -> float:
        """Retrieve the Declination in decimal degrees.

        Returns:
            float: DEC in degrees (-90 to 90), preserving the sign of the degrees component.
        """
        sign = 1 if self._de_d >= 0 else -1
        return sign * (abs(self._de_d) + self._de_m / 60 + self._de_s / 3600)

    def get_source_coordinates(self) -> tuple[float, float, float, float, float, float]:
        """Retrieve the source coordinates in sexagesimal format (hh:mm:ss, dd:mm:ss).

        Returns:
            tuple[float, float, float, float, float, float]: A tuple of (ra_h, ra_m, ra_s, de_d, de_m, de_s).
        """
        return self._ra_h, self._ra_m, self._ra_s, self._de_d, self._de_m, self._de_s
    
    def get_source_coordinates_deg(self) -> tuple[float,float]:
        """Retrieve the source coordinates in decimal degrees.

        Returns:
            tuple[float, float]: A tuple of (RA in degrees, DEC in degrees).
        """
        ra_deg = self.get_ra_degrees()
        dec_deg = self.get_dec_degrees()
        logger.debug(f"Retrieved coordinates RA={ra_deg:.6f} deg, DEC={dec_deg:.6f} deg for source '{self._name}'")
        return (ra_deg, dec_deg)
    
    def get_spectral_index(self) -> Optional[float]:
        """Retrieve the spectral index.

        Returns:
            Optional[float]: The spectral index, or None if not set.
        """
        if self._spectral_index is None:
            logger.debug(f"No data for spectral index of source: '{self._name}'")
        return self._spectral_index

    def get_flux(self, frequency: float) -> Optional[float]:
        """Retrieve the flux for a given frequency, with interpolation or extrapolation.

        If the frequency matches a table entry, returns that value. Otherwise, uses the spectral index
        for extrapolation (if set) or linear interpolation between table values (if within range).

        Args:
            frequency (float): Frequency in MHz.

        Returns:
            Optional[float]: Flux in Jy, or None if no data is available or frequency is out of range.

        Raises:
            TypeError: If frequency is not a number.
        """
        check_type(frequency, (int, float), "Frequency")
        if not self._flux_table:
            logger.warning(f"No flux data available for source '{self._name}' to calculate flux at {frequency} MHz")
            return None
        
        # direct check from freq/flux table
        if frequency in self._flux_table:
            return self._flux_table[frequency]
        
        # extrapolate by spectral index, if exists
        if self._spectral_index is not None and self._flux_table:
            ref_freq, ref_flux = next(iter(self._flux_table.items()))  # consider rightmost value
            flux = ref_flux * (frequency / ref_freq) ** self._spectral_index
            logger.debug(f"Extrapolated flux={flux} Jy for frequency {frequency} MHz using spectral index on '{self._name}'")
            return flux
        
        # liner interpolation between table values
        freqs = sorted(self._flux_table.keys())
        if frequency < freqs[0] or frequency > freqs[-1]:
            logger.debug(f"Frequency {frequency} MHz out of flux table range for '{self._name}'")
            return None
        for i in range(len(freqs) - 1):
            if freqs[i] <= frequency <= freqs[i + 1]:
                f1, f2 = freqs[i], freqs[i + 1]
                fl1, fl2 = self._flux_table[f1], self._flux_table[f2]
                interpolated_flux = fl1 + (fl2 - fl1) * (frequency - f1) / (f2 - f1)
                logger.debug(f"Interpolated flux={interpolated_flux} Jy for frequency {frequency} MHz on '{self._name}'")
                return interpolated_flux
        return None
    
    def get_flux_table(self) -> Dict[float, float]:
        """Retrieve the flux table.

        Returns:
            Dict[float, float]: A dictionary mapping frequencies (MHz) to flux values (Jy). Empty if no data.
        """
        if self._flux_table:
            return self._flux_table
        logger.debug(f"No data in flux table for source: '{self._name}'")
        return {}
    
    def set_source(self, name: str, ra_h: float, ra_m: float, ra_s: float, de_d: float, de_m: float, de_s: float,
                   name_J2000: str = None, alt_name: str = None,
                   flux_table: Optional[Dict[float, float]] = None,
                   spectral_index: Optional[float] = None,
                   isactive: bool = True) -> None:
        """Set all properties of the source.

        Args:
            name (str): Source name in B1950 notation.
            ra_h (float): Right Ascension hours (0-23).
            ra_m (float): Right Ascension minutes (0-59).
            ra_s (float): Right Ascension seconds (0-59.999).
            de_d (float): Declination degrees (-90 to 90).
            de_m (float): Declination minutes (0-59).
            de_s (float): Declination seconds (0-59.999).
            name_J2000 (str, optional): Source name in J2000 notation. Defaults to None.
            alt_name (str, optional): Alternative source name. Defaults to None.
            flux_table (Optional[Dict[float, float]]): Flux table (MHz: Jy). Defaults to None (empty dict).
            spectral_index (Optional[float]): Spectral index. Defaults to None.
            isactive (bool): Whether the source is active. Defaults to True.

        Raises:
            TypeError: If name, name_J2000, or alt_name are not strings; flux_table is not a dict; or spectral_index is not a number.
            ValueError: If RA/DEC components are out of range or flux values are not positive.
        """
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
        if flux_table is not None:
            check_type(flux_table, dict, "Flux table")
            for freq, flux in flux_table.items():
                check_type(freq, (int, float), "Flux frequency")
                check_positive(flux, f"Flux at {freq} MHz")
        if spectral_index is not None:
            check_type(spectral_index, (int, float), "Spectral index")

        self._name = name
        self._name_J2000 = name_J2000
        self._alt_name = alt_name
        self._ra_h = ra_h
        self._ra_m = ra_m
        self._ra_s = ra_s
        self._de_d = de_d
        self._de_m = de_m
        self._de_s = de_s
        self._flux_table = flux_table if flux_table is not None else {}
        self._spectral_index = spectral_index
        self.isactive = isactive
        logger.info(f"Set source '{name}' with new coordinates RA={ra_h}h{ra_m}m{ra_s}s, DEC={de_d}d{de_m}m{de_s}s")
    
    def set_name(self, name: str) -> None:
        """Set the source name in B1950 notation.

        Args:
            name (str): New B1950 name.

        Raises:
            TypeError: If name is not a string.
        """
        if name is not None:
            check_type(name, str, "Name")
            logger.debug(f"Changed source name to '{name}' for source:'{self._name}'.")
            self._name = name
        else:
            logger.debug(f"Incorrect name for source!")

    def set_name_J2000(self, name: str) -> None:
        """Set the source name in J2000 notation.

        Args:
            name (str): New J2000 name.

        Raises:
            TypeError: If name is not a string.
        """
        if name is not None:
            check_type(name, str, "name_J2000")
            self._name_J2000 = name
            logger.debug(f"Changed name_J2000 to '{name}' for source:'{self._name}'.")
        else:
            logger.debug(f"Incorrect name_J2000 for source!")

    def set_alt_name(self, name: str) -> None:
        """Set the alternative source name.

        Args:
            name (str): New alternative name.

        Raises:
            TypeError: If name is not a string.
        """
        if name is not None:
            check_type(name, str, "alt_name")
            self._alt_name = name
            logger.debug(f"Changed alt_name to '{name}' for source:'{self._name}'.")
        else:
            logger.debug(f"Incorrect alt_name for source!")
    
    def set_ra(self, ra_h: float, ra_m: float, ra_s: float) -> None:
        """Set the Right Ascension in sexagesimal format.

        Args:
            ra_h (float): Hours (0-23).
            ra_m (float): Minutes (0-59).
            ra_s (float): Seconds (0-59.999).

        Raises:
            ValueError: If RA components are out of range.
        """
        check_range(ra_h, 0, 23, "RA hours")
        check_range(ra_m, 0, 59, "RA minutes")
        check_range(ra_s, 0, 59.999, "RA seconds")
        
        self._ra_h = ra_h
        self._ra_m = ra_m
        self._ra_s = ra_s
        logger.info(f"Set RA={ra_h}h{ra_m}m{ra_s}s for source '{self._name}'")

    def set_dec(self, de_d: float, de_m: float, de_s: float) -> None:
        """Set the Declination in sexagesimal format.

        Args:
            de_d (float): Degrees (-90 to 90).
            de_m (float): Minutes (0-59).
            de_s (float): Seconds (0-59.999).

        Raises:
            ValueError: If DEC components are out of range.
        """
        check_range(de_d, -90, 90, "DEC degrees")
        check_range(de_m, 0, 59, "DEC minutes")
        check_range(de_s, 0, 59.999, "DEC seconds")
        
        self._de_d = de_d
        self._de_m = de_m
        self._de_s = de_s
        logger.info(f"Set DEC={de_d}d{de_m}m{de_s}s for source '{self._name}'")
    
    def set_ra_degrees(self, ra_deg: float) -> None:
        """Set the Right Ascension from decimal degrees.

        Converts RA from degrees (0-360) to sexagesimal format (hh:mm:ss).

        Args:
            ra_deg (float): RA in decimal degrees (0-360).

        Raises:
            ValueError: If ra_deg is out of range.
        """
        check_range(ra_deg, 0, 360, "RA degrees")
        # normalize RA to [0, 360)
        ra_deg = ra_deg % 360
        # convert RA from deg to hh:mm:ss
        ra_hours = ra_deg / 15  # 360° = 24h, 1h = 15°
        self._ra_h = int(ra_hours)
        ra_minutes = (ra_hours - self._ra_h) * 60
        self._ra_m = int(ra_minutes)
        self._ra_s = (ra_minutes - self._ra_m) * 60
        logger.info(f"Set RA={ra_deg} deg to RA={self._ra_h}h{self._ra_m}m{self._ra_s}s for source '{self._name}'")
    
    def set_dec_degrees(self, dec_deg: float) -> None:
        """Set the Declination from decimal degrees.

        Converts DEC from degrees (-90 to 90) to sexagesimal format (dd:mm:ss).

        Args:
            dec_deg (float): DEC in decimal degrees (-90 to 90).

        Raises:
            ValueError: If dec_deg is out of range.
        """
        check_range(dec_deg, -90, 90, "DEC degrees")
        # convert DEC from deg to dd:mm:ss
        sign = 1 if dec_deg >= 0 else -1
        dec_abs = abs(dec_deg)
        self._de_d = sign * int(dec_abs)
        dec_minutes = (dec_abs - int(dec_abs)) * 60
        self._de_m = int(dec_minutes)
        self._de_s = (dec_minutes - self._de_m) * 60
        logger.info(f"Set DEC={dec_deg} deg to DEC={self._de_d}d{self._de_m}m{self._de_s}s for source '{self._name}'")

    def set_source_coordinates(self, ra_h: float, ra_m: float, ra_s: float, de_d: float, de_m: float, de_s: float) -> None:
        """Set the source coordinates in sexagesimal format.

        Args:
            ra_h (float): Right Ascension hours (0-23).
            ra_m (float): Right Ascension minutes (0-59).
            ra_s (float): Right Ascension seconds (0-59.999).
            de_d (float): Declination degrees (-90 to 90).
            de_m (float): Declination minutes (0-59).
            de_s (float): Declination seconds (0-59.999).

        Raises:
            ValueError: If RA or DEC components are out of range.
        """
        self.set_ra(ra_h, ra_m, ra_s)
        self.set_dec(de_d, de_m, de_s)

    def set_source_coordinates_deg(self, ra_deg: float, dec_deg: float) -> None:
        """Set the source coordinates from decimal degrees.

        Args:
            ra_deg (float): Right Ascension in degrees (0-360).
            dec_deg (float): Declination in degrees (-90 to 90).

        Raises:
            ValueError: If ra_deg or dec_deg are out of range.
        """
        check_range(ra_deg, 0, 360, "RA degrees")
        check_range(dec_deg, -90, 90, "DEC degrees")
        self.set_ra_degrees(ra_deg)
        self.set_dec_degrees(dec_deg)

    def set_flux(self, frequency: float, flux: float) -> None:
        """Set the flux for a specific frequency.

        Args:
            frequency (float): Frequency in MHz.
            flux (float): Flux value in Jy. Must be positive.

        Raises:
            TypeError: If frequency or flux are not numbers.
            ValueError: If flux is not positive.
        """
        check_type(frequency, (int, float), "Frequency")
        check_positive(flux, "Flux")
        self._flux_table[frequency] = flux
        logger.info(f"Set flux={flux} Jy for frequency {frequency} MHz on source '{self._name}'")
    
    def set_flux_table(self, flux_table: Dict[float, float]) -> None:
        """Set the entire flux table.

        Args:
            flux_table (Dict[float, float]): New flux table (MHz: Jy). A copy is made to prevent external modification.

        Raises:
            TypeError: If flux_table is not a dict or contains non-numeric keys/values.
            ValueError: If any flux value is not positive.
        """
        if flux_table is not None:
            check_type(flux_table, dict, "Flux table")
            for freq, flux in flux_table.items():
                check_type(freq, (int, float), "Flux frequency")
                check_positive(flux, f"Flux at {freq} MHz")
            self._flux_table = flux_table.copy()
            logger.info(f"Set flux table with {len(flux_table)} entries for source '{self._name}'")
        else:
            self._flux_table = {}
            logger.info(f"Cleared flux table for source '{self._name}'")
   
    def set_spectral_index(self, spectral_index: float) -> None:
        """Set the spectral index.

        Args:
            spectral_index (float): New spectral index value.

        Raises:
            TypeError: If spectral_index is not a number.
        """
        check_type(spectral_index, (int, float), "Spectral index")
        self._spectral_index = spectral_index
        logger.info(f"Set spectral_index={spectral_index} for source '{self._name}'")

    def to_dict(self) -> dict:
        """Convert the Source object to a dictionary for serialization.

        Returns:
            dict: A dictionary containing all source properties.
        """
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
            "flux_table": self._flux_table,
            "spectral_index": self._spectral_index,
            "isactive": self.isactive
        }
    
    def clear_flux_table(self) -> None:
        """Clear all entries from the flux table."""
        self._flux_table = {}
        logger.info(f"Cleared flux table for source '{self._name}'")

    @classmethod
    def from_dict(cls, data: dict) -> 'Source':
        """Create a Source object from a dictionary.

        Args:
            data (dict): Dictionary containing source properties, typically from `to_dict`.

        Returns:
            Source: A new Source instance initialized with the dictionary data.
        """
        flux_table = data.get("flux_table", {})
        if flux_table:
            flux_table = {float(freq): float(flux) for freq, flux in flux_table.items()}

        logger.info(f"Created source '{data['name']}' from dictionary")
        return cls(
                name=data["name"],
                ra_h=data["ra_h"],
                ra_m=data["ra_m"],
                ra_s=data["ra_s"],
                de_d=data["de_d"],
                de_m=data["de_m"],
                de_s=data["de_s"],
                name_J2000=data.get("name_J2000"),
                alt_name=data.get("alt_name"),
                flux_table=flux_table,
                spectral_index=data.get("spectral_index"),
                isactive=data.get("isactive", True)
            )
    
    def _check_flux(self, frequency: float, flux: float) -> bool:
        """Check if a flux value for a given frequency is a duplicate with a different value.

        Args:
            frequency (float): Frequency in MHz to check.
            flux (float): Flux value in Jy to compare.

        Returns:
            bool: True if the frequency already exists with a different flux value, False otherwise.
        """
        if frequency in self._flux_table:
            current_flux = self._flux_table[frequency]
            if current_flux != flux:
                logger.warning(f"Overwriting flux for frequency {frequency} MHz on source '{self._name}': "
                               f"old value={current_flux} Jy, new value={flux} Jy")
                return True
        return False

    def __repr__(self) -> str:
        """Return a string representation of the Source object.

        Returns:
            str: A formatted string with names, coordinates, flux info, spectral index, and active status.
        """
        names = f"name='{self._name}'"
        if self._name_J2000:
            names += f", name_J2000='{self._name_J2000}'"
        if self._alt_name:
            names += f", alt_name='{self._alt_name}'"
        flux_info = f", flux_table={self._flux_table}" if self._flux_table else ""
        spec_info = f", spectral_index={self._spectral_index}" if self._spectral_index is not None else ""
        return (f"Source({names}, RA={self._ra_h}h{self._ra_m}m{self._ra_s}s, "
                f"DEC={self._de_d}d{self._de_m}m{self._de_s}s{flux_info}{spec_info}, isactive={self.isactive})")

class Sources(BaseEntity):
    """Base class representing a collection of Source objects.

    This class manages a list of astronomical sources, ensuring no duplicates based on B1950 names.
    It provides methods to add, remove, modify, and query sources, with support for activation/deactivation
    and synchronization with a parent Observation object. The collection can be serialized to/from a dictionary.

    Attributes:
        _data (list[Source]): List of Source objects in the collection.
        isactive (bool): Whether the Sources object itself is active. Inherited from BaseEntity.

    Notes:
        - Duplicate sources are identified by their B1950 name (`get_name()`).
        - Activation/deactivation of a source triggers synchronization with a parent Observation (if set) via `_parent._sync_scans_with_activation`.
        - Logging is integrated via `common.utils.logging_setup.logger` to track operations and errors.

    Examples:
        >>> srcs = Sources()
        >>> srcs.create_source(name="3C 273", ra_h=12, ra_m=29, ra_s=6.7, de_d=2, de_m=2, de_s=0.2)
        >>> print(srcs)
        Sources(count=1, active=1, inactive=0)
        >>> srcs.create_source(name="3C 273", ra_h=0, ra_m=0, ra_s=0, de_d=0, de_m=0, de_s=0)
        Traceback (most recent call last):
        ...
        ValueError: Source with name '3C 273' already exists!
    """
    def __init__(self, sources: list[Source] = None):
        """Initialize a Sources object with an optional list of Source objects.

        Args:
            sources (list[Source], optional): Initial list of Source objects. Defaults to None (empty list).

        Raises:
            TypeError: If sources is not a list or contains non-Source objects.
        """
        super().__init__()
        if sources is not None:
            check_list_type(sources, Source, "Sources")
        self._data = sources if sources is not None else []
        logger.info(f"Initialized Sources with {len(self._data)} sources")

    def add_source(self, source: 'Source') -> None:
        """Add an existing Source object to the collection.

        Args:
            source (Source): The Source object to add.

        Raises:
            TypeError: If source is not a Source instance.
            ValueError: If a source with the same B1950 name already exists (logged as a warning).
        """
        check_type(source, Source, "Source")
        if self._is_duplicate(source):
            logger.warning(f"Source '{source.get_name()}' already exists in Sources, skipping addition")
            return
        self._data.append(source)
        logger.info(f"Added source '{source.get_name()}' to Sources")

    def create_source(self, name: str = "SOURCE_DEFAULT", ra_h: float = 0.0, ra_m: float = 0.0, ra_s: float = 0.0,
                  de_d: float = 0.0, de_m: float = 0.0, de_s: float = 0.0,
                  name_J2000: Optional[str] = None, alt_name: Optional[str] = None,
                  flux_table: Optional[Dict[float, float]] = None,
                  spectral_index: Optional[float] = None,
                  isactive: bool = True) -> None:
        """Create and add a new Source object to the collection.

        Args:
            name (str): Source name in B1950 notation. Defaults to "SOURCE_DEFAULT".
            ra_h (float): Right Ascension hours (0-23). Defaults to 0.0.
            ra_m (float): Right Ascension minutes (0-59). Defaults to 0.0.
            ra_s (float): Right Ascension seconds (0-59.999). Defaults to 0.0.
            de_d (float): Declination degrees (-90 to 90). Defaults to 0.0.
            de_m (float): Declination minutes (0-59). Defaults to 0.0.
            de_s (float): Declination seconds (0-59.999). Defaults to 0.0.
            name_J2000 (Optional[str]): Source name in J2000 notation. Defaults to None.
            alt_name (Optional[str]): Alternative source name. Defaults to None.
            flux_table (Optional[Dict[float, float]]): Flux table (MHz: Jy). Defaults to None.
            spectral_index (Optional[float]): Spectral index. Defaults to None.
            isactive (bool): Whether the source is active. Defaults to True.

        Raises:
            TypeError: If inputs are of incorrect type (e.g., name not a string, flux_table not a dict).
            ValueError: If RA/DEC components are out of range, flux values are not positive, or source name is a duplicate.
        """
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
            flux_table=flux_table,
            spectral_index=spectral_index,
            isactive=isactive
        )

        # check for duplicates
        if self._is_duplicate(new_source):
            logger.error(f"Source with name '{name}' already exists")
            raise ValueError(f"Source with name '{name}' already exists!")

        # add the new source to the collection
        self._data.append(new_source)
        logger.info(f"Created and added source '{name}' to Sources")
    
    def insert_source(self, index: int, source: 'Source') -> None:
        """Insert a Source object at a specific index.

        Args:
            index (int): The position to insert the source (0 to len(sources)).
            source (Source): The Source object to insert.

        Raises:
            TypeError: If source is not a Source instance or index is not an integer.
            IndexError: If index is out of range.
            ValueError: If source name is a duplicate.
        """
        check_type(index, int, "Index")
        check_type(source, Source, "Source")
        
        if not (0 <= index <= len(self._data)):
            logger.error(f"Index {index} is out of range for Sources with {len(self._data)} elements")
            raise IndexError(f"Index {index} is out of range!")
        
        if self._is_duplicate(source):
            logger.warning(f"Source '{source.get_name()}' already exists in Sources, skipping insertion")
            raise ValueError(f"Source '{source.get_name()}' is a duplicate!")
        
        self._data.insert(index, source)
        logger.info(f"Inserted source '{source.get_name()}' at index {index} in Sources")

    def remove_source(self, index: int) -> None:
        """Remove a source by index.

        Args:
            index (int): The index of the source to remove.

        Raises:
            IndexError: If index is out of range.
        """
        try:
            self._data.pop(index)
            logger.info(f"Removed source at index {index} from Sources")
        except IndexError:
            logger.error(f"Invalid source index: {index}")
            raise IndexError("Invalid source index!")

    def get_by_index(self, index: int) -> 'Source':
        """Retrieve a source by index.

        Args:
            index (int): The index of the source to retrieve.

        Returns:
            Source: The Source object at the specified index.

        Raises:
            IndexError: If index is out of range.
        """
        try:
            return self._data[index]
        except IndexError:
            logger.error(f"Invalid source index: {index}")
            raise IndexError("Invalid source index!")

    def get_all_sources(self) -> list['Source']:
        """Retrieve all sources in the collection.

        Returns:
            list[Source]: A list of all Source objects.
        """
        return self._data

    def get_active_sources(self) -> list['Source']:
        """Retrieve all active sources.

        Returns:
            list[Source]: A list of Source objects that are active.
        """
        active = [src_obj for src_obj in self._data if src_obj.isactive]
        logger.debug(f"Retrieved {len(active)} active sources")
        return active

    def get_inactive_sources(self) -> list['Source']:
        """Retrieve all inactive sources.

        Returns:
            list[Source]: A list of Source objects that are inactive.
        """
        inactive = [src_obj for src_obj in self._data if not src_obj.isactive]
        logger.debug(f"Retrieved {len(inactive)} inactive sources")
        return inactive
    
    def set_source(self, index: int, source: 'Source') -> None:
        """Replace a source at a specific index.

        Args:
            index (int): The index to replace.
            source (Source): The new Source object.

        Raises:
            TypeError: If source is not a Source instance.
            IndexError: If index is out of range.
            ValueError: If source name is a duplicate at another index.
        """
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
    
    def activate_source(self, index: int) -> None:
        """"Activate a specific source by index.

        Triggers synchronization with a parent Observation if present.

        Args:
            index (int): The index of the source to activate.

        Raises:
            TypeError: If index is not an integer.
            IndexError: If index is out of range.
        """
        check_type(index, int, "Index")
        try:
            self._data[index].activate()
            if hasattr(self, '_parent') and self._parent:  # Проверяем наличие родителя
                self._parent._sync_scans_with_activation("sources", index, True)
            logger.info(f"Activated source '{self._data[index].get_name()}' at index {index}")
        except IndexError:
            logger.error(f"Invalid source index: {index}")
            raise IndexError("Invalid source index!")
        
    def deactivate_source(self, index: int) -> None:
        """Deactivate a specific source by index.

        Triggers synchronization with a parent Observation if present.

        Args:
            index (int): The index of the source to deactivate.

        Raises:
            TypeError: If index is not an integer.
            IndexError: If index is out of range.
        """
        check_type(index, int, "Index")
        try:
            self._data[index].deactivate()
            if hasattr(self, '_parent') and self._parent:  # Проверяем наличие родителя
                self._parent._sync_scans_with_activation("sources", index, False)
            logger.info(f"Deactivated source '{self._data[index].get_name()}' at index {index}")
        except IndexError:
            logger.error(f"Invalid source index: {index}")
            raise IndexError("Invalid source index!")

    def activate_all(self) -> None:
        """Activate all sources in the collection.

        Raises:
            ValueError: If the collection is empty.
        """
        if not self._data:
            logger.error("No sources to activate")
            raise ValueError("No sources to activate!")
        for src_obj in self._data:
            src_obj.activate()
        logger.info("Activated all sources")

    def deactivate_all(self) -> None:
        """Deactivate all sources in the collection.

        Raises:
            ValueError: If the collection is empty.
        """
        if not self._data:
            logger.error("No sources to deactivate")
            raise ValueError("No sources to deactivate!")
        for src_obj in self._data:
            src_obj.deactivate()
        logger.info("Deactivated all sources")
    
    def drop_active(self) -> None:
        """Remove all active sources from the collection.

        Raises:
            ValueError: If there are no active sources to remove.
        """
        active_sources = self.get_active_sources()
        if not active_sources:
            logger.warning("No active sources to drop")
            raise ValueError("No active sources to remove!")
        
        self._data = [src_obj for src_obj in self._data if not src_obj.isactive]
        logger.info(f"Dropped {len(active_sources)} active sources from Sources")

    def drop_inactive(self) -> None:
        """Remove all inactive sources from the collection.

        Raises:
            ValueError: If there are no inactive sources to remove.
        """
        inactive_sources = self.get_inactive_sources()
        if not inactive_sources:
            logger.warning("No inactive sources to drop")
            raise ValueError("No inactive sources to remove!")
        
        self._data = [src_obj for src_obj in self._data if src_obj.isactive]
        logger.info(f"Dropped {len(inactive_sources)} inactive sources from Sources")

    def clear(self) -> None:
        """Remove all sources from the collection."""
        logger.info(f"Cleared {len(self._data)} sources from Sources")
        self._data.clear()

    def to_dict(self) -> dict:
        """Convert the Sources object to a dictionary for serialization.

        Returns:
            dict: A dictionary with a 'data' key containing a list of source dictionaries.
        """
        logger.info(f"Converted Sources with {len(self._data)} sources to dictionary")
        return {"data": [source.to_dict() for source in self._data]}

    @classmethod
    def from_dict(cls, data: dict) -> 'Sources':
        """Create a Sources object from a dictionary.

        Args:
            data (dict): Dictionary with a 'data' key containing a list of source dictionaries.

        Returns:
            Sources: A new Sources instance initialized with the dictionary data.
        """
        sources = [Source.from_dict(source_data) for source_data in data["data"]]
        logger.info(f"Created Sources with {len(sources)} sources from dictionary")
        return cls(sources=sources)
    
    def _is_duplicate(self, source: 'Source', exclude_index: int = -1, tolerance: float = 2.78e-4) -> bool:
        """Check if a source is a duplicate based on B1950 name.

        Args:
            source (Source): The Source object to check.
            exclude_index (int): Index to exclude from the check (e.g., for replacement). Defaults to -1.
            tolerance (float): Unused in this implementation (kept for compatibility). Defaults to 2.78e-4 (1 arcsecond).

        Returns:
            bool: True if a source with the same B1950 name exists at a different index, False otherwise.
        """
        for i, existing in enumerate(self._data):
            if i == exclude_index:
                continue
            # check by unique name
            if (existing.get_name() == source.get_name()):
                return True
        return False

    def __len__(self) -> int:
        """Return the number of sources in the collection.

        Returns:
            int: The total count of Source objects.
        """
        return len(self._data)

    def __repr__(self) -> str:
        """Return a string representation of the Sources object.

        Returns:
            str: A formatted string with the count of total, active, and inactive sources.
        """
        active_count = len(self.get_active_sources())
        return f"Sources(count={len(self._data)}, active={active_count}, inactive={len(self._data) - active_count})"