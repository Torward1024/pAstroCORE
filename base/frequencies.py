# base/frequencies.py
from base.base_entity import BaseEntity
from utils.validation import check_type, check_non_negative, check_positive, check_list_type, check_non_zero
from utils.logging_setup import logger
from typing import Optional, Union, List

# Speed of light constant in MHz * cm
C_MHZ_CM = 29979.2458

# allowed polarization code values
CIRCULAR_POLARIZATIONS = {"RCP", "LCP"}
PAIRED_LINEAR_POLARIZATIONS = {"RR", "LL", "RL", "LR"}
SINGLE_LINEAR_POLARIZATIONS = {"H", "V"}
VALID_POLARIZATIONS = CIRCULAR_POLARIZATIONS.union(PAIRED_LINEAR_POLARIZATIONS).union(SINGLE_LINEAR_POLARIZATIONS)


"""Base-class of an IF object with frequency, bandwidth, and polarization

    Notes: IF frequency range is supposed as follows: freq is the leftmost (lower) value + bandwidth
    Contains:
    Atributes:
        freq (float): IF frequency in MHz.
        bandwidth (float): Bandwidth in MHz.
        polarization (str, optional): polarization type (RCP, LCP, LL, RL, RR, LR, H, V) from VALID_POLARIZATIONS
        isactive (bool): whether the frequency is active (default: True).

    Methods:
        activate
        deactivate

        get_frequency
        get_bandwidth
        get_polarization
        get_frequency_wavelength

        set_if
        set_frequency
        set_bandwidth
        set_frequency_wavelength
        set_polarization

        to_dict
        from_dict
        _validate_polarizations
        __init__
        __repr__
    """
class IF(BaseEntity):
    def __init__(self, freq: float, bandwidth: float, 
                 polarization: Optional[str] = None, isactive: bool = True):
        """Initialize an IF object with frequency, bandwidth, and polarization

        Args:
            freq (float): Frequency in MHz.
            bandwidth (float): Bandwidth in MHz.
            polarization (str, optional): Polarization type (RCP, LCP, LL, RL, RR, LR, H, V).
            isactive (bool): Whether the frequency is active (default: True).
        """
        super().__init__(isactive)
        check_non_negative(freq, "Frequency")
        check_non_negative(bandwidth, "Bandwidth")
        self._frequency = freq
        self._bandwidth = bandwidth
        self._polarizations = self._validate_polarizations(polarization)
        logger.info(f"Initialized IF with frequency={freq} MHz, bandwidth={bandwidth} MHz, polarizations={self._polarizations}")

    def activate(self) -> None:
        """Activate IF frequency"""
        super().activate()

    def deactivate(self) -> None:
        """Deactivate IF frequency"""
        super().deactivate()

    def get_frequency(self) -> float:
        """Return the IF frequency value in MHz"""
        logger.debug(f"Retrieved IF frequency={self._frequency} MHz for IF")
        return self._frequency

    def get_bandwidth(self) -> float:
        """Return the IF bandwidth value in MHz"""
        logger.debug(f"Retrieved IF bandwidth={self._bandwidth} MHz for IF")
        return self._bandwidth

    def get_polarization(self) -> List[str]:
        """Return the IF polarization values as a list"""
        logger.debug(f"Retrieved IF polarizations={self._polarizations} for IF")
        return self._polarizations

    def get_frequency_wavelength(self) -> float:
        """Get wavelength in cm for the IF frequency"""
        if self._frequency == 0:
            logger.error("IF frequency cannot be zero for wavelength calculation")
            raise ValueError("IF frequency cannot be zero for wavelength calculation!")
        wavelength = C_MHZ_CM / self._frequency
        logger.debug(f"Calculated wavelength={wavelength} cm for IF frequency={self._frequency} MHz")
        return wavelength
    
    def set_if(self, freq: float, bandwidth: float, 
               polarization: Optional[str] = None, isactive: bool = True) -> None:
        """Set IF values"""
        check_non_negative(freq, "Frequency")
        check_non_negative(bandwidth, "Bandwidth")

        if polarization is not None:
            check_type(polarization, str, "Polarization")
            self._polarizations = self._validate_polarizations(polarization)
        
        self._frequency = freq
        self._bandwidth = bandwidth
        self._polarization = self._validate_polarizations(polarization).upper() if polarization else None
        self.isactive = isactive
        logger.info(f"Set IF to frequency={freq} MHz, bandwidth={bandwidth} MHz, polarizations={self._polarization}")

    def set_frequency(self, freq: float, isactive: bool = True) -> None:
        """Set IF frequency value in MHz"""
        check_non_negative(freq, "Frequency")
        self._frequency = freq
        self.isactive = isactive
        logger.info(f"Set IF frequency to {freq} MHz for IF")

    def set_bandwidth(self, bandwidth: float) -> None:
        """Set IF bandwidth value in MHz"""
        check_non_negative(bandwidth, "Bandwidth")
        self._bandwidth = bandwidth
        logger.info(f"Set IF bandwidth to {bandwidth} MHz for IF")
    
    def set_polarization(self, polarization: Union[str, List[str]]) -> None:
        """Set IF polarization value(s)"""
        self._polarizations = self._validate_polarizations(polarization)
        logger.info(f"Set IF polarizations to {self._polarizations} for IF")

    def set_frequency_wavelength(self, wavelength_cm: float) -> None:
        """Set IF frequency value in MHz through wavelength value in cm"""
        check_positive(wavelength_cm, "Wavelength")
        check_non_zero(wavelength_cm, "Wavelength")
        self._frequency = C_MHZ_CM / wavelength_cm
        logger.info(f"Set IF frequency to {self._frequency} MHz from wavelength={wavelength_cm} cm for IF")

    def to_dict(self) -> dict:
        """Convert IF object to a dictionary for serialization"""
        logger.info(f"Converted IF (frequency={self._frequency} MHz) to dictionary")
        return {
            "frequency": self._frequency,
            "bandwidth": self._bandwidth,
            "polarizations": self._polarizations,
            "isactive": self.isactive
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'IF':
        """Create an IF object from a dictionary"""
        logger.info(f"Created IF from dictionary with frequency={data['frequency']} MHz")
        return cls(
            freq=data["frequency"],
            bandwidth=data["bandwidth"],
            polarization=data.get("polarizations", data.get("polarization")),  # Поддержка старого формата
            isactive=data["isactive"]
        )
    
    def _validate_polarizations(self, polarization: Optional[Union[str, List[str]]]) -> List[str]:
        """Validate polarizations values ensuring they belong to only one group"""
        if polarization is None:
            return []
        if isinstance(polarization, str):
            polarization = [polarization]
        check_list_type(polarization, str, "Polarization")
        polarizations = [p.upper() for p in polarization if p]

        # general check for polariozatons validity
        for p in polarizations:
            if p not in VALID_POLARIZATIONS:
                logger.error(f"Invalid polarization value: {p}")
                raise ValueError(f"Polarization must be one of {VALID_POLARIZATIONS}, got {p}")

        # check group belonging
        if not polarizations:
            return polarizations

        # check whether polarization belongs to a specific group
        if all(p in CIRCULAR_POLARIZATIONS for p in polarizations):
            group = "circular (RCP, LCP)"
        elif all(p in PAIRED_LINEAR_POLARIZATIONS for p in polarizations):
            group = "paired linear (RR, LL, RL, LR)"
        elif all(p in SINGLE_LINEAR_POLARIZATIONS for p in polarizations):
            group = "single linear (H, V)"
        else:
            logger.error(f"Polarizations {polarizations} mix different groups")
            raise ValueError(f"Polarizations {polarizations} must belong to a single group: "
                            f"either {CIRCULAR_POLARIZATIONS}, {PAIRED_LINEAR_POLARIZATIONS}, or {SINGLE_LINEAR_POLARIZATIONS}")

        logger.debug(f"Validated polarizations {polarizations} as {group}")
        return polarizations  

    def __repr__(self) -> str:
        """Return a string representation of IF"""
        logger.debug(f"Generated string representation for IF with frequency={self._frequency} MHz")
        return (f"IF(frequency={self._frequency} MHz, bandwidth={self._bandwidth} MHz, "
                f"polarizations={self._polarizations}, isactive={self.isactive})")

"""Base-class of an Frequencies object with the list of IFs

    Contains:
    Atributes:
        data (IF): list of objsects of IF type

    Methods:
        add_IF
        insert_IF
        remove_IF
        set_IF

        get_IF
        get_all_IF

        get_frequencies
        get_bandwidths
        get_polarizations
        get_wavelengths
        get_active_frequencies
        get_inactive_frequencies
        
        activate_IF
        deactivate_IF

        activate_all
        deactivate_all

        drop_active
        drop_inactive
        clear

        to_dict
        from_dict
        _check_overlap
        __len__
        __init__
        __repr__
    """

class Frequencies(BaseEntity):
    def __init__(self, ifs: list[IF] = None):
        """Initialize Frequencies with a list of IF objects"""
        super().__init__()
        if ifs is not None:
            check_list_type(ifs, IF, "IFs")
        self._data = ifs if ifs is not None else []
        logger.info(f"Initialized Frequencies with {len(self._data)} IFs")

    def add_IF(self, if_obj: IF) -> None:
        """Add a new IF object

        Args:
            if_obj (IF): IF object to add

        Raises:
            ValueError: If an IF with overlapping frequency range already exists
        """
        check_type(if_obj, IF, "IF")
        self._check_overlap(if_obj)
        self._data.append(if_obj)
        logger.info(f"Added IF with frequency={if_obj.get_frequency()} MHz, bandwidth={if_obj.get_bandwidth()} MHz to Frequencies")
    
    def insert_IF(self, index: int, if_obj: 'IF') -> None:
        """Insert a new IF object at the specified index

        Args:
            index (int): The index at which to insert the IF (0 to len(frequencies))
            if_obj (IF): The IF object to insert

        Raises:
            IndexError: If the index is out of range
            ValueError: If the IF frequency range overlaps with an existing range
        """
        check_type(index, int, "Index")
        check_type(if_obj, IF, "IF")
        
        if not (0 <= index <= len(self._data)):
            logger.error(f"Index {index} is out of range for Frequencies with {len(self._data)} elements")
            raise IndexError(f"Index {index} is out of range!")
        
        self._check_overlap(if_obj)
        self._data.insert(index, if_obj)
        logger.info(f"Inserted IF with frequency={if_obj.get_frequency()} MHz, bandwidth={if_obj.get_bandwidth()} MHz at index {index} in Frequencies")

    def remove_IF(self, index: int) -> None:
        """Remove IF by index"""
        try:
            self._data.pop(index)
            logger.info(f"Removed IF at index {index} from Frequencies")
        except IndexError:
            logger.error(f"Invalid IF index: {index}")
            raise IndexError("Invalid IF index!")
        
    def set_IF(self, if_obj: IF, index: int) -> None:
        """ Replace IF data with index with new IF"""
        check_type(if_obj, IF, "IF")
        self._check_overlap(if_obj)
        try:
            self._data[index] = if_obj
        except:
            logger.error(f"Invalid IF index: {index}")
            raise IndexError("Invalid IF index!")

    def get_IF(self, index: int) -> IF:
        """Get IF by index"""
        try:
            return self._data[index]
        except IndexError:
            logger.error(f"Invalid IF index: {index}")
            raise IndexError("Invalid IF index!")
        
    def get_all_IF(self) -> list[IF]:
        """Get list of IF objects"""
        return self._data
        
    def get_frequencies(self) -> list[float]:
        """Get list of IF frequencies in MHz"""
        logger.debug(f"Retrieved IF frequencies with {len(self._data)} items")
        return [if_obj.get_frequency() for if_obj in self._data]

    def get_bandwidths(self) -> list[float]:
        """Get list of IF bandwidths in MHz"""
        logger.debug(f"Retrieved IF bandwidths with {len(self._data)} items")
        return [if_obj.get_bandwidth() for if_obj in self._data]

    def get_polarizations(self) -> list[Optional[str]]:
        """Get list of IF polarizations"""
        logger.debug(f"Retrieved polarizations with {len(self._data)} items")
        return [if_obj.get_polarization() for if_obj in self._data]
    
    def get_wavelengths(self) -> list[float]:
        """Get list of IF wavelengths in cm"""
        logger.debug(f"Retrieved IF wavelengths with {len(self._data)} items")
        return [if_obj.get_frequency_wavelength() for if_obj in self._data]

    def get_active_frequencies(self) -> list[IF]:
        """Get active IF frequencies"""
        active = [if_obj for if_obj in self._data if if_obj.isactive]
        logger.debug(f"Retrieved {len(active)} active frequencies")
        return active

    def get_inactive_frequencies(self) -> list[IF]:
        """Get inactive IF frequencies"""
        inactive = [if_obj for if_obj in self._data if not if_obj.isactive]
        logger.debug(f"Retrieved {len(inactive)} inactive frequencies")
        return inactive

    def activate_IF(self, index: int) -> None:
        """Activate IF by index"""
        check_type(index, int, "Index")
        try:
            self._data[index].activate()
            if hasattr(self, '_parent') and self._parent:  # Проверяем наличие родителя
                self._parent._sync_scans_with_activation("frequencies", index, True)
            logger.info(f"Activated IF {self._data[index].get_frequency()} MHz at index {index}")
        except IndexError:
            logger.error(f"Invalid IF index: {index}")
            raise IndexError("Invalid IF index!")

    def deactivate_IF(self, index: int) -> None:
        """Deactivate IF by index"""
        check_type(index, int, "Index")
        try:
            self._data[index].deactivate()
            if hasattr(self, '_parent') and self._parent:  # Проверяем наличие родителя
                self._parent._sync_scans_with_activation("frequencies", index, False)
            logger.info(f"Deactivated IF {self._data[index].get_frequency()} MHz at index {index}")
        except IndexError:
            logger.error(f"Invalid IF index: {index}")
            raise IndexError("Invalid IF index!")

    def activate_all(self) -> None:
        """Activate all IF"""
        if not self._data:
            logger.error("No IFs to activate")
            raise ValueError("No IFs to activate!")
        for if_obj in self._data:
            if_obj.activate()
        logger.info("Activated all IFs")

    def deactivate_all(self) -> None:
        """Deactivate all IF"""
        if not self._data:
            logger.error("No IFs to deactivate")
            raise ValueError("No IFs to deactivate!")
        for if_obj in self._data:
            if_obj.deactivate()
        logger.info("Deactivated all IFs")
    
    def drop_active(self) -> None:
        """Remove all active IFs from the Frequencies list

        Raises:
            ValueError: If there are no active IFs to remove
        """
        active_ifs = self.get_active_frequencies()
        if not active_ifs:
            logger.warning("No active IFs to drop")
            raise ValueError("No active IFs to remove!")
        
        self._data = [if_obj for if_obj in self._data if not if_obj.isactive]
        logger.info(f"Dropped {len(active_ifs)} active IFs from Frequencies")

    def drop_inactive(self) -> None:
        """Remove all inactive IFs from the Frequencies list

        Raises:
            ValueError: If there are no inactive IFs to remove
        """
        inactive_ifs = self.get_inactive_frequencies()
        if not inactive_ifs:
            logger.warning("No inactive IFs to drop")
            raise ValueError("No inactive IFs to remove!")
        
        self._data = [if_obj for if_obj in self._data if if_obj.isactive]
        logger.info(f"Dropped {len(inactive_ifs)} inactive IFs from Frequencies")

    def clear(self) -> None:
        """Clear IF data"""
        logger.info(f"Cleared {len(self._data)} IFs from Frequencies")
        self._data.clear()

    def to_dict(self) -> dict:
        """Convert Frequencies object to a dictionary for serialization"""
        logger.info(f"Converted Frequencies with {len(self._data)} IFs to dictionary")
        return {"data": [if_obj.to_dict() for if_obj in self._data]}

    @classmethod
    def from_dict(cls, data: dict) -> 'Frequencies':
        """Create a Frequencies object from a dictionary"""
        ifs = [IF.from_dict(if_data) for if_data in data["data"]]
        logger.info(f"Created Frequencies with {len(ifs)} IFs from dictionary")
        return cls(ifs=ifs)

    def _check_overlap(self, if_obj:IF):
        """Check IF frequency overlapping with existis IF frequencies"""
        new_freq = if_obj.get_frequency()
        new_bw = if_obj.get_bandwidth()
        new_end = new_freq + new_bw

        for existing_if in self._data:
            ex_freq = existing_if.get_frequency()
            ex_bw = existing_if.get_bandwidth()
            ex_end = ex_freq + ex_bw
            if (new_freq < ex_end and new_end > ex_freq):
                logger.error(f"Frequency range [{new_freq}, {new_end}] overlaps with existing range [{ex_freq}, {ex_end}]")
                raise ValueError(f"Frequency range [{new_freq}, {new_end}] overlaps with existing range [{ex_freq}, {ex_end}]")

    def __len__(self) -> int:
        """Return the number of IFs in Frequencies"""
        return len(self._data)

    def __repr__(self) -> str:
        """String representation of Frequencies"""
        active_count = len(self.get_active_frequencies())
        logger.debug(f"Generated string representation for Frequencies")
        return f"Frequencies(count={len(self._data)}, active={active_count}, inactive={len(self._data) - active_count})"