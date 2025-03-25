# base/sources.py
from base.base_entity import BaseEntity
from utils.validation import check_type, check_range, check_list_type, check_positive
from utils.logging_setup import logger
import numpy as np
from typing import Optional, Dict

"""Base-class of a Source object with name, J2000 coordinates, and optional flux and spectral index

    Notes: IF frequency range is supposed as follows: freq is the leftmost (lower) value + bandwidth
    Contains:
    Atributes:
        name (str): Source name in B1950
        ra_h (float): Right Ascension hours (0-23)
        ra_m (float): Right Ascension minutes (0-59)
        ra_s (float): Right Ascension seconds (0-59.999)
        de_d (float): Declination degrees (-90 to 90)
        de_m (float): Declination minutes (0-59)
        de_s (float): Declination seconds (0-59.999)
        name_J2000 (str, optional): Source name in J2000
        alt_name (str, optional): Alternative source name (e.g., BL Lac)
        flux_table (Dict[float, float], optional): Flux table (frequency in MHz: flux in Jy)
        spectral_index (float, optional): Spectral index for flux extrapolation (F ~ nu^alpha)
        isactive (bool): Whether the source is active (default: True)

    Methods:
        add_flux
        insert_flux
        remove_flux

        activate
        deactivate

        get_name
        get_name_J2000
        get_alt_name
        get_ra
        get_dec
        get_source_coordinates
        get_source_coordinates_deg
        get_ra_degrees
        get_dec_degrees
        get_spectral_index
        get_flux
        get_flux_table
        get_spectral_index

        set_source
        set_name
        set_name_J2000
        set_alt_name
        set_ra
        set_dec
        set_ra_degrees
        set_dec_degrees
        set_source_coordinates
        set_source_coordinates_deg (prev. set_coordinates_from_degrees)
        set_flux
        set_flux_table
        set_spectral_index

        clear_flux_table

        _check_flux
        __init__
        __repr__
    """

class Source(BaseEntity):
    def __init__(self, name: str, ra_h: float, ra_m: float, ra_s: float, de_d: float, de_m: float, de_s: float,
                 name_J2000: str = None, alt_name: str = None,
                 flux_table: Optional[Dict[float, float]] = None,
                 spectral_index: Optional[float] = None,
                 isactive: bool = True):
        """Initialize a Source object with name, J2000 coordinates, and optional flux and spectral index

        Args:
            name (str): Source name in B1950
            ra_h (float): Right Ascension hours (0-23)
            ra_m (float): Right Ascension minutes (0-59)
            ra_s (float): Right Ascension seconds (0-59.999)
            de_d (float): Declination degrees (-90 to 90)
            de_m (float): Declination minutes (0-59)
            de_s (float): Declination seconds (0-59.999)
            name_J2000 (str, optional): Source name in J2000
            alt_name (str, optional): Alternative source name (e.g., BL Lac)
            flux_table (Dict[float, float], optional): Flux table (frequency in MHz: flux in Jy)
            spectral_index (float, optional): Spectral index for flux extrapolation (F ~ nu^alpha)
            isactive (bool): Whether the source is active (default: True)
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
        """Add a flux value for a specific frequency to the table"""
        check_type(frequency, (int, float), "Frequency")
        check_positive(flux, "Flux")
        self._check_flux(frequency, flux)
        self._flux_table[frequency] = flux
        logger.info(f"Added flux={flux} Jy for frequency {frequency} MHz to source '{self._name}'")
    
    def insert_flux(self, frequency: float, flux: float) -> None:
        """Insert a flux value for a specific frequency into the table"""
        check_type(frequency, (int, float), "Frequency")
        check_positive(flux, "Flux")
        self._check_flux(frequency, flux)
        self._flux_table[frequency] = flux
        logger.info(f"Inserted flux={flux} Jy for frequency {frequency} MHz into source '{self._name}'")
    
    def remove_flux(self, frequency: float) -> None:
        """Remove a flux value for a specific frequency from the table"""
        check_type(frequency, (int, float), "Frequency")
        if frequency in self._flux_table:
            removed_flux = self._flux_table.pop(frequency)
            logger.info(f"Removed flux={removed_flux} Jy for frequency {frequency} MHz from source '{self._name}'")
        else:
            logger.warning(f"No flux value found for frequency {frequency} MHz in source '{self._name}'")

    def activate(self) -> None:
        """Activate source"""
        super().activate()

    def deactivate(self) -> None:
        """Deactivate source"""
        super().deactivate()

    def get_name(self) -> str:
        """Get source name (B1950)"""
        return self._name

    def get_name_J2000(self) -> str | None:
        """Get source name in J2000"""
        return self._name_J2000

    def get_alt_name(self) -> str | None:
        """Get alternative source name"""
        return self._alt_name

    def get_ra(self) -> tuple[float, float, float]:
        """Get source RA in hh:mm:ss"""
        return self._ra_h, self._ra_m, self._ra_s

    def get_dec(self) -> tuple[float, float, float]:
        """Get source DEC in dd:mm:ss"""
        return self._de_d, self._de_m, self._de_s
    
    def get_ra_degrees(self) -> float:
        """Return RA in decimal degrees"""
        return (self._ra_h + self._ra_m / 60 + self._ra_s / 3600) * 15  # 15 = 360° / 24h

    def get_dec_degrees(self) -> float:
        """Return DEC in decimal degrees"""
        sign = 1 if self._de_d >= 0 else -1
        return sign * (abs(self._de_d) + self._de_m / 60 + self._de_s / 3600)

    def get_source_coordinates(self) -> tuple[float, float, float, float, float, float]:
        """Get source RA, DEC in hh:mm:ss, dd:mm:ss"""
        return self._ra_h, self._ra_m, self._ra_s, self._de_d, self._de_m, self._de_s
    
    def get_source_coordinates_deg(self) -> tuple[float,float]:
        """Get source RA, DEC in degrees

        Returns:
            tuple[float, float]: A tuple containing (RA in degrees, DEC in degrees)
        """
        ra_deg = self.get_ra_degrees()
        dec_deg = self.get_dec_degrees()
        logger.debug(f"Retrieved coordinates RA={ra_deg:.6f} deg, DEC={dec_deg:.6f} deg for source '{self._name}'")
        return (ra_deg, dec_deg)
    
    def get_spectral_index(self) -> Optional[float]:
        """Get spectral index"""
        if self._spectral_index is None:
            logger.debug(f"No data for spectral index of source: '{self._name}'")
        return self._spectral_index

    def get_flux(self, frequency: float) -> Optional[float]:
        """Get flux for a given frequency, with interpolation or spectral index extrapolation"""
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
        """Retrieve flux table from Source"""
        if self._flux_table:
            return self._flux_table
        logger.debug(f"No data in flux table for source: '{self._name}'")
        return {}
    
    def set_source(self, name: str, ra_h: float, ra_m: float, ra_s: float, de_d: float, de_m: float, de_s: float,
                   name_J2000: str = None, alt_name: str = None,
                   flux_table: Optional[Dict[float, float]] = None,
                   spectral_index: Optional[float] = None,
                   isactive: bool = True) -> None:
        """Set Source values"""
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
        """Set source name (B1950)"""
        if name is not None:
            check_type(name, str, "Name")
            logger.debug(f"Changed source name to '{name}' for source:'{self._name}'.")
            self._name = name
        else:
            logger.debug(f"Incorrect name for source!")

    def set_name_J2000(self, name: str) -> None:
        """Set source name in J2000"""
        if name is not None:
            check_type(name, str, "name_J2000")
            self._name_J2000 = name
            logger.debug(f"Changed name_J2000 to '{name}' for source:'{self._name}'.")
        else:
            logger.debug(f"Incorrect name_J2000 for source!")

    def set_alt_name(self, name: str) -> None:
        """Set alternative source name"""
        if name is not None:
            check_type(name, str, "alt_name")
            self._alt_name = name
            logger.debug(f"Changed alt_name to '{name}' for source:'{self._name}'.")
        else:
            logger.debug(f"Incorrect alt_name for source!")
    
    def set_ra(self, ra_h: float, ra_m: float, ra_s: float) -> None:
        """Set source Right Ascension in hh:mm:ss format

        Args:
            ra_h (float): Right Ascension hours (0-23)
            ra_m (float): Right Ascension minutes (0-59)
            ra_s (float): Right Ascension seconds (0-59.999)
        """
        check_range(ra_h, 0, 23, "RA hours")
        check_range(ra_m, 0, 59, "RA minutes")
        check_range(ra_s, 0, 59.999, "RA seconds")
        
        self._ra_h = ra_h
        self._ra_m = ra_m
        self._ra_s = ra_s
        logger.info(f"Set RA={ra_h}h{ra_m}m{ra_s}s for source '{self._name}'")

    def set_dec(self, de_d: float, de_m: float, de_s: float) -> None:
        """Set source Declination in dd:mm:ss format

        Args:
            de_d (float): Declination degrees (-90 to 90)
            de_m (float): Declination minutes (0-59)
            de_s (float): Declination seconds (0-59.999)
        """
        check_range(de_d, -90, 90, "DEC degrees")
        check_range(de_m, 0, 59, "DEC minutes")
        check_range(de_s, 0, 59.999, "DEC seconds")
        
        self._de_d = de_d
        self._de_m = de_m
        self._de_s = de_s
        logger.info(f"Set DEC={de_d}d{de_m}m{de_s}s for source '{self._name}'")
    
    def set_ra_degrees(self, ra_deg: float) -> None:
        """Set source Right Ascension from decimal degrees to hh:mm:ss format

        Args:
            ra_deg (float): Right Ascension in decimal degrees (0 to 360)
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
        """Set source Declination from decimal degrees to dd:mm:ss format

        Args:
            dec_deg (float): Declination in decimal degrees (-90 to 90)
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
        """Set source RA and DEC coordinates in hh:mm:ss and dd:mm:ss format

        Args:
            ra_h (float): Right Ascension hours (0-23)
            ra_m (float): Right Ascension minutes (0-59)
            ra_s (float): Right Ascension seconds (0-59.999)
            de_d (float): Declination degrees (-90 to 90)
            de_m (float): Declination minutes (0-59)
            de_s (float): Declination seconds (0-59.999)
        """
        self.set_ra(ra_h, ra_m, ra_s)
        self.set_dec(de_d, de_m, de_s)

    def set_source_coordinates_deg(self, ra_deg: float, dec_deg: float) -> None:
        """Set source coordinates from RA and DEC in decimal degrees to hh:mm:ss and dd:mm:ss format

        Args:
            ra_deg (float): Right Ascension in decimal degrees (0 to 360)
            dec_deg (float): Declination in decimal degrees (-90 to 90)
        """
        check_range(ra_deg, 0, 360, "RA degrees")
        check_range(dec_deg, -90, 90, "DEC degrees")
        self.set_ra_degrees(ra_deg)
        self.set_dec_degrees(dec_deg)

    def set_flux(self, frequency: float, flux: float) -> None:
        """Set flux for a specific frequency"""
        check_type(frequency, (int, float), "Frequency")
        check_positive(flux, "Flux")
        self._flux_table[frequency] = flux
        logger.info(f"Set flux={flux} Jy for frequency {frequency} MHz on source '{self._name}'")
    
    def set_flux_table(self, flux_table: Dict[float, float]) -> None:
        """Set the flux table for the source

        Args:
            flux_table (Dict[float, float]): Flux table with frequency in MHz as keys and flux in Jy as values
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
        """Set spectral index"""
        check_type(spectral_index, (int, float), "Spectral index")
        self._spectral_index = spectral_index
        logger.info(f"Set spectral_index={spectral_index} for source '{self._name}'")

    def to_dict(self) -> dict:
        """Convert Source object to a dictionary for serialization"""
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
        """Clear the flux table for the source"""
        self._flux_table = {}
        logger.info(f"Cleared flux table for source '{self._name}'")

    @classmethod
    def from_dict(cls, data: dict) -> 'Source':
        """Create a Source object from a dictionary"""
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
        """Check if the flux value for the given frequency is a duplicate with a different value"""
        if frequency in self._flux_table:
            current_flux = self._flux_table[frequency]
            if current_flux != flux:
                logger.warning(f"Overwriting flux for frequency {frequency} MHz on source '{self._name}': "
                               f"old value={current_flux} Jy, new value={flux} Jy")
                return True
        return False

    def __repr__(self) -> str:
        """Return a string representation of Source"""
        names = f"name='{self._name}'"
        if self._name_J2000:
            names += f", name_J2000='{self._name_J2000}'"
        if self._alt_name:
            names += f", alt_name='{self._alt_name}'"
        flux_info = f", flux_table={self._flux_table}" if self._flux_table else ""
        spec_info = f", spectral_index={self._spectral_index}" if self._spectral_index is not None else ""
        return (f"Source({names}, RA={self._ra_h}h{self._ra_m}m{self._ra_s}s, "
                f"DEC={self._de_d}d{self._de_m}m{self._de_s}s{flux_info}{spec_info}, isactive={self.isactive})")

"""Base-class of Sources object with the list of object with Source type

    Contains:
    Atributes:
        data (Source): list of objsects of Source type

    Methods:
        add_source
        insert_source
        remove_source
    
        get_source
        get_all_sources      

        get_active_sources
        get_inactive_sources
        
        activate_source
        deactivate_source

        set_source

        activate_all
        deactivate_all

        drop_active
        drop_inactive
        clear

        to_dict
        from_dict

        _is_duplicate
        __len__
        __init__
        __repr__
    """

class Sources(BaseEntity):
    def __init__(self, sources: list[Source] = None):
        """Initialize Sources with a list of Source objects."""
        super().__init__()
        if sources is not None:
            check_list_type(sources, Source, "Sources")
        self._data = sources if sources is not None else []
        logger.info(f"Initialized Sources with {len(self._data)} sources")

    def add_source(self, source: 'Source') -> None:
        """Add a new source."""
        check_type(source, Source, "Source")
        if self._is_duplicate(source):
            logger.warning(f"Source '{source.get_name()}' already exists in Sources, skipping addition")
            return
        self._data.append(source)
        logger.info(f"Added source '{source.get_name()}' to Sources")
    
    def insert_source(self, index: int, source: 'Source') -> None:
        """Insert a new source at the specified index

        Args:
            index (int): The index at which to insert the source (0 to len(sources))
            source (Source): The Source object to insert

        Raises:
            IndexError: If the index is out of range
            ValueError: If the source is a duplicate based on name
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
        """Remove source by index"""
        try:
            self._data.pop(index)
            logger.info(f"Removed source at index {index} from Sources")
        except IndexError:
            logger.error(f"Invalid source index: {index}")
            raise IndexError("Invalid source index!")

    def get_source(self, index: int) -> 'Source':
        """Get source by index"""
        try:
            return self._data[index]
        except IndexError:
            logger.error(f"Invalid source index: {index}")
            raise IndexError("Invalid source index!")

    def get_all_sources(self) -> list['Source']:
        """Get all sources"""
        return self._data

    def get_active_sources(self) -> list['Source']:
        """Get active sources"""
        active = [src_obj for src_obj in self._data if src_obj.isactive]
        logger.debug(f"Retrieved {len(active)} active sources")
        return active

    def get_inactive_sources(self) -> list['Source']:
        """Get inactive sources"""
        inactive = [src_obj for src_obj in self._data if not src_obj.isactive]
        logger.debug(f"Retrieved {len(inactive)} inactive sources")
        return inactive
    
    def set_source(self, index: int, source: 'Source') -> None:
        """Set a source at a specific index"""
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
        """Activate source by index"""
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
        """Deactivate source by index"""
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
        """Activate all sources"""
        if not self._data:
            logger.error("No sources to activate")
            raise ValueError("No sources to activate!")
        for src_obj in self._data:
            src_obj.activate()
        logger.info("Activated all sources")

    def deactivate_all(self) -> None:
        """Deactivate all sources"""
        if not self._data:
            logger.error("No sources to deactivate")
            raise ValueError("No sources to deactivate!")
        for src_obj in self._data:
            src_obj.deactivate()
        logger.info("Deactivated all sources")
    
    def drop_active(self) -> None:
        """Remove all active sources from the Sources list

        Raises:
            ValueError: If there are no active sources to remove
        """
        active_sources = self.get_active_sources()
        if not active_sources:
            logger.warning("No active sources to drop")
            raise ValueError("No active sources to remove!")
        
        self._data = [src_obj for src_obj in self._data if not src_obj.isactive]
        logger.info(f"Dropped {len(active_sources)} active sources from Sources")

    def drop_inactive(self) -> None:
        """Remove all inactive sources from the Sources list

        Raises:
            ValueError: If there are no inactive sources to remove
        """
        inactive_sources = self.get_inactive_sources()
        if not inactive_sources:
            logger.warning("No inactive sources to drop")
            raise ValueError("No inactive sources to remove!")
        
        self._data = [src_obj for src_obj in self._data if src_obj.isactive]
        logger.info(f"Dropped {len(inactive_sources)} inactive sources from Sources")

    def clear(self) -> None:
        """Clear sources data"""
        logger.info(f"Cleared {len(self._data)} sources from Sources")
        self._data.clear()

    def to_dict(self) -> dict:
        """Convert Sources object to a dictionary for serialization"""
        logger.info(f"Converted Sources with {len(self._data)} sources to dictionary")
        return {"data": [source.to_dict() for source in self._data]}

    @classmethod
    def from_dict(cls, data: dict) -> 'Sources':
        """Create a Sources object from a dictionary"""
        sources = [Source.from_dict(source_data) for source_data in data["data"]]
        logger.info(f"Created Sources with {len(sources)} sources from dictionary")
        return cls(sources=sources)
    
    def _is_duplicate(self, source: 'Source', exclude_index: int = -1, tolerance: float = 2.78e-4) -> bool:
        """Check if the source is a duplicate based on names (B1950)"""
        for i, existing in enumerate(self._data):
            if i == exclude_index:
                continue
            # check by unique name
            if (existing.get_name() == source.get_name()):
                return True
        return False

    def __len__(self) -> int:
        """Return the number of sources"""
        return len(self._data)

    def __repr__(self) -> str:
        """String representation of Sources"""
        active_count = len(self.get_active_sources())
        return f"Sources(count={len(self._data)}, active={active_count}, inactive={len(self._data) - active_count})"