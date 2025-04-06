# base/frequencies.py
from common.base.base_entity import BaseEntity
from common.utils.validation import check_type, check_positive, check_list_type
from common.utils.logging_setup import logger
from typing import Optional, Union, List

# Speed of light constant in MHz * cm
C_MHZ_CM = 29979.2458

# allowed polarization code values
CIRCULAR_POLARIZATIONS = {"RCP", "LCP"}
PAIRED_LINEAR_POLARIZATIONS = {"RR", "LL", "RL", "LR"}
SINGLE_LINEAR_POLARIZATIONS = {"H", "V"}
VALID_POLARIZATIONS = CIRCULAR_POLARIZATIONS.union(PAIRED_LINEAR_POLARIZATIONS).union(SINGLE_LINEAR_POLARIZATIONS)

class IF(BaseEntity):
    """Base class representing an Intermediate Frequency (IF) with frequency, bandwidth, and polarization properties.

    This class encapsulates the properties of an intermediate frequency used in radio astronomy observations,
    including its frequency, bandwidth, polarization type, and active status. The frequency range is defined as
    [freq, freq + bandwidth], where `freq` is the lower bound and `bandwidth` extends the range upward. The
    class supports serialization to/from dictionaries and provides methods to manipulate and retrieve its
    properties.

    Attributes:
        _frequency (float): The IF frequency in MHz. Must be positive.
        _bandwidth (float): The bandwidth in MHz. Must be positive.
        _polarizations (List[str]): A list of polarization codes (e.g., 'RCP', 'LCP', 'RR', 'LL', etc.) from
            VALID_POLARIZATIONS. Empty if no polarization is set.
        isactive (bool): Indicates whether the IF is active. Inherited from BaseEntity.

    Notes:
        - Polarization values must belong to a single group: circular (RCP, LCP), paired linear (RR, LL, RL, LR),
          or single linear (H, V). Mixing groups is not allowed.
        - The frequency wavelength is calculated as C_MHZ_CM / frequency, where C_MHZ_CM = 29979.2458 MHz*cm.
        - Logging is integrated via the `logger` from `common.utils.logging_setup` to track operations.

    Examples:
        >>> if_obj = IF(freq=1420.0, bandwidth=32.0, polarization="RCP")
        >>> print(if_obj)
        IF(frequency=1420.0 MHz, bandwidth=32.0 MHz, polarizations=['RCP'], isactive=True)
        >>> if_obj.get_frequency_wavelength()
        21.12411267605634  # Wavelength in cm for 1420 MHz (approx. H-line)

    Methods:
        __init__: Initialize the IF object with frequency, bandwidth, polarization, and active status.
        activate: Mark the IF as active.
        deactivate: Mark the IF as inactive.
        get_frequency: Retrieve the IF frequency in MHz.
        get_bandwidth: Retrieve the IF bandwidth in MHz.
        get_polarization: Retrieve the list of polarization codes.
        get_frequency_wavelength: Calculate the wavelength in centimeters.
        set_if: Set all properties of the IF object.
        set_frequency: Set the frequency in MHz.
        set_bandwidth: Set the bandwidth in MHz.
        set_polarization: Set the polarization values.
        set_frequency_wavelength: Set the frequency based on a wavelength in centimeters.
        to_dict: Convert the IF object to a dictionary.
        from_dict: Create an IF object from a dictionary.
        _validate_polarizations: Validate and normalize polarization values.
        __repr__: Return a string representation of the IF object.
    """
    def __init__(self, freq: float = 1000.0, bandwidth: float = 16.0, 
                 polarization: Optional[str] = None, isactive: bool = True):
        """Initialize an IF object representing an intermediate frequency with its properties.

        Args:
            freq (float): Frequency in MHz. Must be positive. Defaults to 1000.0.
            bandwidth (float): Bandwidth in MHz. Must be positive. Defaults to 16.0.
            polarization (str, optional): Polarization type (e.g., 'RCP', 'LCP', 'RR', 'LL', 'RL', 'LR', 'H', 'V').
                Must be a valid value from VALID_POLARIZATIONS. Defaults to None.
            isactive (bool): Whether the IF is active. Defaults to True.

        Raises:
            ValueError: If freq or bandwidth is not positive, or if polarization is invalid.
        """
        super().__init__(isactive)
        check_positive(freq, "Frequency")
        check_positive(bandwidth, "Bandwidth")
        self._frequency = freq
        self._bandwidth = bandwidth
        self._polarizations = self._validate_polarizations(polarization)
        logger.info(f"Initialized IF with frequency={freq} MHz, bandwidth={bandwidth} MHz, polarizations={self._polarizations}")

    def activate(self) -> None:
        """Activate the IF object, marking it as active."""
        super().activate()

    def deactivate(self) -> None:
        """Deactivate the IF object, marking it as inactive."""
        super().deactivate()

    def get_frequency(self) -> float:
        """Retrieve the IF frequency.

        Returns:
            float: The frequency in MHz.
        """
        logger.debug(f"Retrieved IF frequency={self._frequency} MHz for IF")
        return self._frequency

    def get_bandwidth(self) -> float:
        """Retrieve the IF bandwidth.

        Returns:
            float: The bandwidth in MHz.
        """
        logger.debug(f"Retrieved IF bandwidth={self._bandwidth} MHz for IF")
        return self._bandwidth

    def get_polarization(self) -> List[str]:
        """Retrieve the polarization values associated with the IF.

        Returns:
            List[str]: A list of polarization codes (e.g., ['RCP', 'LCP']). Empty if none set.
        """
        logger.debug(f"Retrieved IF polarizations={self._polarizations} for IF")
        return self._polarizations

    def get_frequency_wavelength(self) -> float:
        """Calculate the wavelength corresponding to the IF frequency.

        Returns:
            float: The wavelength in centimeters.

        Raises:
            ValueError: If the frequency is zero.
        """
        if self._frequency == 0:
            logger.error("IF frequency cannot be zero for wavelength calculation")
            raise ValueError("IF frequency cannot be zero for wavelength calculation!")
        wavelength = C_MHZ_CM / self._frequency
        logger.debug(f"Calculated wavelength={wavelength} cm for IF frequency={self._frequency} MHz")
        return wavelength
    
    def set_if(self, freq: float, bandwidth: float, 
               polarization: Optional[str] = None, isactive: bool = True) -> None:
        """Set all properties of the IF object.

        Args:
            freq (float): Frequency in MHz. Must be positive.
            bandwidth (float): Bandwidth in MHz. Must be positive.
            polarization (str, optional): Polarization type. Must be valid if provided. Defaults to None.
            isactive (bool): Whether the IF is active. Defaults to True.

        Raises:
            ValueError: If freq or bandwidth is not positive, or if polarization is invalid.
            TypeError: If polarization is provided but not a string.
        """
        check_positive(freq, "Frequency")
        check_positive(bandwidth, "Bandwidth")

        if polarization is not None:
            check_type(polarization, str, "Polarization")
            self._polarizations = self._validate_polarizations(polarization)
        
        self._frequency = freq
        self._bandwidth = bandwidth
        self._polarization = self._validate_polarizations(polarization).upper() if polarization else None
        self.isactive = isactive
        logger.info(f"Set IF to frequency={freq} MHz, bandwidth={bandwidth} MHz, polarizations={self._polarization}")

    def set_frequency(self, freq: float) -> None:
        """Set the IF frequency.

        Args:
            freq (float): Frequency in MHz. Must be positive.

        Raises:
            ValueError: If freq is not positive.
        """
        check_positive(freq, "Frequency")
        self._frequency = freq
        logger.info(f"Set IF frequency to {freq} MHz for IF")

    def set_bandwidth(self, bandwidth: float) -> None:
        """Set the IF bandwidth.

        Args:
            bandwidth (float): Bandwidth in MHz. Must be positive.

        Raises:
            ValueError: If bandwidth is not positive.
        """
        check_positive(bandwidth, "Bandwidth")
        self._bandwidth = bandwidth
        logger.info(f"Set IF bandwidth to {bandwidth} MHz for IF")
    
    def set_polarization(self, polarization: Union[str, List[str]]) -> None:
        """Set the IF polarization values.

        Args:
            polarization (Union[str, List[str]]): Single polarization code or list of codes.
                Must be valid values from VALID_POLARIZATIONS.

        Raises:
            ValueError: If polarization values are invalid or mix groups.
            TypeError: If polarization is neither a string nor a list of strings.
        """
        self._polarizations = self._validate_polarizations(polarization)
        logger.info(f"Set IF polarizations to {self._polarizations} for IF")

    def set_frequency_wavelength(self, wavelength_cm: float) -> None:
        """Set the IF frequency based on a wavelength.

        Args:
            wavelength_cm (float): Wavelength in centimeters. Must be positive.

        Raises:
            ValueError: If wavelength_cm is not positive.
        """
        check_positive(wavelength_cm, "Wavelength")
        self._frequency = C_MHZ_CM / wavelength_cm
        logger.info(f"Set IF frequency to {self._frequency} MHz from wavelength={wavelength_cm} cm for IF")

    def to_dict(self) -> dict:
        """Convert the IF object to a dictionary for serialization.

        Returns:
            dict: A dictionary containing frequency, bandwidth, polarizations, and isactive status.
        """
        logger.info(f"Converted IF (frequency={self._frequency} MHz) to dictionary")
        return {
            "frequency": self._frequency,
            "bandwidth": self._bandwidth,
            "polarizations": self._polarizations,
            "isactive": self.isactive
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'IF':
        """Create an IF object from a dictionary.

        Args:
            data (dict): Dictionary with keys 'frequency', 'bandwidth', 'polarizations', and 'isactive'.

        Returns:
            IF: A new IF instance initialized with the dictionary data.
        """
        logger.info(f"Created IF from dictionary with frequency={data['frequency']} MHz")
        return cls(
            freq=data["frequency"],
            bandwidth=data["bandwidth"],
            polarization=data.get("polarizations", data.get("polarization")),
            isactive=data["isactive"]
        )
    
    def _validate_polarizations(self, polarization: Optional[Union[str, List[str]]]) -> List[str]:
        """Validate and normalize polarization values.

        Args:
            polarization (Union[str, List[str]], optional): Polarization code(s) to validate.

        Returns:
            List[str]: A list of validated and uppercased polarization codes. Empty if None.

        Raises:
            ValueError: If polarization values are invalid or mix different groups.
            TypeError: If polarization is a list containing non-string elements.
        """
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
        """Return a string representation of the IF object.

        Returns:
            str: A formatted string with frequency, bandwidth, polarizations, and isactive status.
        """
        logger.debug(f"Generated string representation for IF with frequency={self._frequency} MHz")
        return (f"IF(frequency={self._frequency} MHz, bandwidth={self._bandwidth} MHz, "
                f"polarizations={self._polarizations}, isactive={self.isactive})")

class Frequencies(BaseEntity):
    """Base class representing a collection of Intermediate Frequency (IF) objects.

    This class manages a list of IF objects, providing functionality to add, remove, modify, and query
    intermediate frequencies used in an observation. It ensures no frequency ranges overlap (i.e., for any
    two IFs, their ranges [freq, freq + bandwidth] do not intersect unless they are the same object).
    The class supports activation/deactivation of individual IFs or the entire collection, as well as
    serialization to/from dictionaries.

    Attributes:
        _data (List[IF]): A list of IF objects representing the collection of intermediate frequencies.
        isactive (bool): Indicates whether the Frequencies object itself is active. Inherited from BaseEntity.

    Notes:
        - Frequency overlap is checked when adding or inserting IFs, raising a ValueError if detected.
        - Methods like `activate_IF` and `deactivate_IF` can synchronize with a parent Observation object
          if the `_parent` attribute is set (not shown in this code snippet but implied by the implementation).
        - Logging is integrated via the `logger` from `common.utils.logging_setup` to track operations.
        - The class assumes IF objects are immutable in terms of their frequency range once added, unless
          explicitly modified via `set_IF`.

    Examples:
        >>> freqs = Frequencies()
        >>> freqs.create_IF(freq=1000.0, bandwidth=16.0, polarization="RCP")
        >>> freqs.create_IF(freq=1020.0, bandwidth=16.0, polarization="LCP")
        >>> print(freqs)
        Frequencies(count=2, active=2, inactive=0)
        >>> freqs.get_frequencies()
        [1000.0, 1020.0]
        >>> freqs.deactivate_IF(0)
        >>> print(freqs.get_active_frequencies()[0].get_frequency())
        1020.0

    Methods:
        __init__: Initialize the Frequencies object with an optional list of IFs.
        add_IF: Add an existing IF object to the collection.
        create_IF: Create and add a new IF object to the collection.
        insert_IF: Insert an IF object at a specific index.
        remove_IF: Remove an IF object by index.
        set_IF: Replace an IF object at a specific index.
        get_by_index: Retrieve an IF object by index.
        get_all_IF: Retrieve all IF objects in the collection.
        get_frequencies: Retrieve a list of all IF frequencies.
        get_bandwidths: Retrieve a list of all IF bandwidths.
        get_polarizations: Retrieve a list of all IF polarizations.
        get_wavelengths: Retrieve a list of wavelengths for all IF frequencies.
        get_active_frequencies: Retrieve all active IF objects.
        get_inactive_frequencies: Retrieve all inactive IF objects.
        activate_IF: Activate an IF object by index.
        deactivate_IF: Deactivate an IF object by index.
        activate_all: Activate all IF objects in the collection.
        deactivate_all: Deactivate all IF objects in the collection.
        drop_active: Remove all active IF objects from the collection.
        drop_inactive: Remove all inactive IF objects from the collection.
        clear: Remove all IF objects from the collection.
        to_dict: Convert the Frequencies object to a dictionary.
        from_dict: Create a Frequencies object from a dictionary.
        _check_overlap: Check if an IF's frequency range overlaps with existing IFs.
        __len__: Return the number of IF objects in the collection.
        __repr__: Return a string representation of the Frequencies object.
    """
    def __init__(self, ifs: list[IF] = None):
        """Initialize a Frequencies object with a list of IF objects.

        Args:
            ifs (List[IF], optional): List of IF objects. Defaults to None, creating an empty list.

        Raises:
            TypeError: If ifs is provided but not a list of IF objects.
        """
        super().__init__()
        if ifs is not None:
            check_list_type(ifs, IF, "IFs")
        self._data = ifs if ifs is not None else []
        logger.info(f"Initialized Frequencies with {len(self._data)} IFs")

    def add_IF(self, if_obj: IF) -> None:
        """Add an existing IF object to the collection.

        Args:
            if_obj (IF): The IF object to add.

        Raises:
            TypeError: If if_obj is not an IF instance.
            ValueError: If the IF's frequency range overlaps with an existing IF.
        """
        check_type(if_obj, IF, "IF")
        self._check_overlap(if_obj)
        self._data.append(if_obj)
        logger.info(f"Added IF with frequency={if_obj.get_frequency()} MHz, bandwidth={if_obj.get_bandwidth()} MHz to Frequencies")
    
    def create_IF(self, freq: float = 1000.0, bandwidth: float = 16.0, 
              polarization: Optional[str] = None, isactive: bool = True) -> None:
        """Create and add a new IF object to the collection.

        Args:
            freq (float): Frequency in MHz. Must be positive. Defaults to 1000.0.
            bandwidth (float): Bandwidth in MHz. Must be positive. Defaults to 16.0.
            polarization (str, optional): Polarization type. Defaults to None.
            isactive (bool): Whether the IF is active. Defaults to True.

        Raises:
            ValueError: If freq or bandwidth is not positive, polarization is invalid, or frequency range overlaps.
        """
        # create a new IF object
        new_if = IF(
            freq=freq,
            bandwidth=bandwidth,
            polarization=polarization,
            isactive=isactive
        )

        # check for frequency overlap
        self._check_overlap(new_if)

        # add the new IF to the collection
        self._data.append(new_if)
        logger.info(f"Created and added IF with frequency={freq} MHz, bandwidth={bandwidth} MHz, "
                    f"polarizations={new_if.get_polarization()} to Frequencies")
    
    def insert_IF(self, index: int, if_obj: 'IF') -> None:
        """Insert an IF object at a specific index.

        Args:
            index (int): The position to insert the IF (0 to len(frequencies)).
            if_obj (IF): The IF object to insert.

        Raises:
            TypeError: If index is not an integer or if_obj is not an IF instance.
            IndexError: If index is out of range.
            ValueError: If the IF's frequency range overlaps with an existing IF.
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
        """Remove an IF object by index.

        Args:
            index (int): The index of the IF to remove.

        Raises:
            IndexError: If index is invalid.
        """
        try:
            self._data.pop(index)
            logger.info(f"Removed IF at index {index} from Frequencies")
        except IndexError:
            logger.error(f"Invalid IF index: {index}")
            raise IndexError("Invalid IF index!")
        
    def set_IF(self, if_obj: IF, index: int) -> None:
        """Replace an IF object at a specific index.

        Args:
            if_obj (IF): The new IF object to set.
            index (int): The index to replace.

        Raises:
            TypeError: If if_obj is not an IF instance.
            IndexError: If index is invalid.
            ValueError: If the new IF's frequency range overlaps with another existing IF.
        """
        check_type(if_obj, IF, "IF")
        self._check_overlap(if_obj)
        try:
            self._data[index] = if_obj
        except:
            logger.error(f"Invalid IF index: {index}")
            raise IndexError("Invalid IF index!")

    def get_by_index(self, index: int) -> IF:
        """Retrieve an IF object by index.

        Args:
            index (int): The index of the IF to retrieve.

        Returns:
            IF: The IF object at the specified index.

        Raises:
            IndexError: If index is invalid.
        """
        try:
            return self._data[index]
        except IndexError:
            logger.error(f"Invalid IF index: {index}")
            raise IndexError("Invalid IF index!")
        
    def get_all_IF(self) -> list[IF]:
        """Retrieve all IF objects in the collection.

        Returns:
            List[IF]: A list of all IF objects.
        """
        return self._data
        
    def get_frequencies(self) -> list[float]:
        """Retrieve a list of all IF frequencies.

        Returns:
            List[float]: A list of frequencies in MHz.
        """
        logger.debug(f"Retrieved IF frequencies with {len(self._data)} items")
        return [if_obj.get_frequency() for if_obj in self._data]

    def get_bandwidths(self) -> list[float]:
        """Retrieve a list of all IF bandwidths.

        Returns:
            List[float]: A list of bandwidths in MHz.
        """
        logger.debug(f"Retrieved IF bandwidths with {len(self._data)} items")
        return [if_obj.get_bandwidth() for if_obj in self._data]

    def get_polarizations(self) -> list[Optional[str]]:
        """Retrieve a list of all IF polarizations.

        Returns:
            List[Optional[str]]: A list of polarization lists (or empty lists if none set).
        """
        logger.debug(f"Retrieved polarizations with {len(self._data)} items")
        return [if_obj.get_polarization() for if_obj in self._data]
    
    def get_wavelengths(self) -> list[float]:
        """Retrieve a list of wavelengths for all IF frequencies.

        Returns:
            List[float]: A list of wavelengths in centimeters.
        """
        logger.debug(f"Retrieved IF wavelengths with {len(self._data)} items")
        return [if_obj.get_frequency_wavelength() for if_obj in self._data]

    def get_active_frequencies(self) -> list[IF]:
        """Retrieve all active IF objects.

        Returns:
            List[IF]: A list of IF objects that are currently active.
        """
        active = [if_obj for if_obj in self._data if if_obj.isactive]
        logger.debug(f"Retrieved {len(active)} active frequencies")
        return active

    def get_inactive_frequencies(self) -> list[IF]:
        """Retrieve all inactive IF objects.

        Returns:
            List[IF]: A list of IF objects that are currently inactive.
        """
        inactive = [if_obj for if_obj in self._data if not if_obj.isactive]
        logger.debug(f"Retrieved {len(inactive)} inactive frequencies")
        return inactive

    def activate_IF(self, index: int) -> None:
        """Activate an IF object by index.

        Args:
            index (int): The index of the IF to activate.

        Raises:
            IndexError: If index is invalid.
        """
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
        """Deactivate an IF object by index.

        Args:
            index (int): The index of the IF to deactivate.

        Raises:
            IndexError: If index is invalid.
        """
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
        """Activate all IF objects in the collection.

        Raises:
            ValueError: If the collection is empty.
        """
        if not self._data:
            logger.error("No IFs to activate")
            raise ValueError("No IFs to activate!")
        for if_obj in self._data:
            if_obj.activate()
        logger.info("Activated all IFs")

    def deactivate_all(self) -> None:
        """Deactivate all IF objects in the collection.

        Raises:
            ValueError: If the collection is empty.
        """
        if not self._data:
            logger.error("No IFs to deactivate")
            raise ValueError("No IFs to deactivate!")
        for if_obj in self._data:
            if_obj.deactivate()
        logger.info("Deactivated all IFs")
    
    def drop_active(self) -> None:
        """Remove all active IF objects from the collection.

        Raises:
            ValueError: If there are no active IFs to remove.
        """
        active_ifs = self.get_active_frequencies()
        if not active_ifs:
            logger.warning("No active IFs to drop")
            raise ValueError("No active IFs to remove!")
        
        self._data = [if_obj for if_obj in self._data if not if_obj.isactive]
        logger.info(f"Dropped {len(active_ifs)} active IFs from Frequencies")

    def drop_inactive(self) -> None:
        """Remove all inactive IF objects from the collection.

        Raises:
            ValueError: If there are no inactive IFs to remove.
        """
        inactive_ifs = self.get_inactive_frequencies()
        if not inactive_ifs:
            logger.warning("No inactive IFs to drop")
            raise ValueError("No inactive IFs to remove!")
        
        self._data = [if_obj for if_obj in self._data if if_obj.isactive]
        logger.info(f"Dropped {len(inactive_ifs)} inactive IFs from Frequencies")

    def clear(self) -> None:
        """Remove all IF objects from the collection."""
        logger.info(f"Cleared {len(self._data)} IFs from Frequencies")
        self._data.clear()

    def to_dict(self) -> dict:
        """Convert the Frequencies object to a dictionary for serialization.

        Returns:
            dict: A dictionary containing a list of IF dictionaries under the 'data' key.
        """
        logger.info(f"Converted Frequencies with {len(self._data)} IFs to dictionary")
        return {"data": [if_obj.to_dict() for if_obj in self._data]}

    @classmethod
    def from_dict(cls, data: dict) -> 'Frequencies':
        """Create a Frequencies object from a dictionary.

        Args:
            data (dict): Dictionary with a 'data' key containing a list of IF dictionaries.

        Returns:
            Frequencies: A new Frequencies instance initialized with the dictionary data.
        """
        ifs = [IF.from_dict(if_data) for if_data in data["data"]]
        logger.info(f"Created Frequencies with {len(ifs)} IFs from dictionary")
        return cls(ifs=ifs)

    def _check_overlap(self, if_obj:IF):
        """Check if the frequency range of an IF overlaps with existing IFs.

        Args:
            if_obj (IF): The IF object to check for overlap.

        Raises:
            ValueError: If the frequency range overlaps with an existing IF.
        """
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
        """Return the number of IF objects in the collection.

        Returns:
            int: The total count of IF objects.
        """
        return len(self._data)

    def __repr__(self) -> str:
        """Return a string representation of the Frequencies object.

        Returns:
            str: A formatted string with the count of total, active, and inactive IFs.
        """
        active_count = len(self.get_active_frequencies())
        logger.debug(f"Generated string representation for Frequencies")
        return f"Frequencies(count={len(self._data)}, active={active_count}, inactive={len(self._data) - active_count})"