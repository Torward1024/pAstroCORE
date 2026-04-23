# base/frequencies.py
from typing import List, Optional, Union, Dict
from pastrocore.base.baseentityn import BaseEntityN
from msb_arch.base.basecontainer import BaseContainer
from msb_arch.utils.logging_setup import logger
import uuid

C_MHZ_CM = 29979.2458
CIRCULAR_POLARIZATIONS = {"RCP", "LCP"}
SINGLE_LINEAR_POLARIZATIONS = {"H", "V"}
VALID_POLARIZATIONS = CIRCULAR_POLARIZATIONS.union(SINGLE_LINEAR_POLARIZATIONS)

class IF(BaseEntityN):
    """Base class representing an Intermediate Frequency (IF) with frequency, bandwidth, and polarization properties.

    Attributes:
        name (str, optional): Unique identifier for the IF.
        frequency (float): The IF frequency in MHz. Must be positive.
        bandwidth (float): The bandwidth in MHz. Must be positive.
        polarizations (List[str]): List of polarization codes from VALID_POLARIZATIONS.
        isactive (bool): Indicates whether the IF is active.

    Notes:
        - Polarizations must belong to a single group: circular, paired linear, or single linear.
        - Wavelength is calculated as C_MHZ_CM / frequency.
    """
    name: str
    frequency: float
    bandwidth: float
    polarizations: List[str]
    isactive: bool

    def __init__(self, *, name: str = None, frequency: float = 1000.0, bandwidth: float = 16.0,
                 polarizations: Optional[Union[str, List[str]]] = None, isactive: bool = True):
        """Initialize an IF object with frequency, bandwidth, polarizations, and active status."""
        polarizations = self._validate_polarizations(polarizations)
        super().__init__(name=name, frequency=frequency, bandwidth=bandwidth,
                         polarizations=polarizations, isactive=isactive)
        if name is None:
            name = f"if_{uuid.uuid4().hex[:32]}"
        if frequency <= 0:
            raise ValueError("Frequency must be positive")
        if bandwidth <= 0:
            raise ValueError("Bandwidth must be positive")

    def get_frequency_wavelength(self) -> float:
        """Calculate the wavelength corresponding to the IF frequency.

        Returns:
            float: Wavelength in centimeters.

        Raises:
            ValueError: If frequency is zero.
        """
        if self.frequency == 0:
            logger.error("IF frequency cannot be zero for wavelength calculation")
            raise ValueError("Frequency cannot be zero for wavelength calculation")
        wavelength = C_MHZ_CM / self.frequency
        logger.debug(f"Calculated wavelength={wavelength} cm for IF frequency={self.frequency} MHz")
        return wavelength

    def set_frequency_wavelength(self, wavelength_cm: float) -> None:
        """Set frequency based on a wavelength.

        Args:
            wavelength_cm (float): Wavelength in centimeters. Must be positive.

        Raises:
            ValueError: If wavelength_cm is not positive.
        """
        if wavelength_cm <= 0:
            logger.error("Wavelength must be positive")
            raise ValueError("Wavelength must be positive")
        self.frequency = C_MHZ_CM / wavelength_cm
        logger.info(f"Set IF frequency to {self.frequency} MHz from wavelength={wavelength_cm} cm")
    
    def copy(self) -> 'IF':
        """Create a deep copy of the IF object."""
        return IF(
            name=self.name,
            frequency=self.frequency,
            bandwidth=self.bandwidth,
            polarizations=self.polarizations.copy(),
            isactive=self.isactive
        )

    def _validate_polarizations(self, polarization: Optional[Union[str, List[str]]]) -> List[str]:
        """Validate and normalize polarization values.

        Args:
            polarization: Polarization code(s) to validate.

        Returns:
            List[str]: Validated and uppercased polarization codes.

        Raises:
            ValueError: If polarizations are invalid or mix groups.
            TypeError: If polarization is a list with non-string elements.
        """
        if polarization is None:
            return []
        if isinstance(polarization, str):
            polarization = [polarization]
        if not all(isinstance(p, str) for p in polarization):
            raise TypeError("Polarization must be a string or list of strings")
        polarizations = [p.upper() for p in polarization if p]

        for p in polarizations:
            if p not in VALID_POLARIZATIONS:
                logger.error(f"Invalid polarization value: {p}")
                raise ValueError(f"Polarization must be one of {VALID_POLARIZATIONS}, got {p}")

        if polarizations:
            if all(p in CIRCULAR_POLARIZATIONS for p in polarizations):
                group = "circular (RCP, LCP)"
            elif all(p in SINGLE_LINEAR_POLARIZATIONS for p in polarizations):
                group = "single linear (H, V)"
            else:
                logger.error(f"Polarizations {polarizations} mix different groups")
                raise ValueError(f"Polarizations must belong to a single group: {VALID_POLARIZATIONS}")
            logger.debug(f"Validated polarizations {polarizations} as {group}")
        return polarizations

    def __repr__(self) -> str:
        """Return a string representation of the IF object."""
        return (f"IF(name={self.name!r}, frequency={self.frequency} MHz, "
                f"bandwidth={self.bandwidth} MHz, polarizations={self.polarizations}, "
                f"isactive={self.isactive})")

class Frequencies(BaseContainer[IF]):
    """Base class representing a collection of Intermediate Frequency (IF) objects.

    Manages a dictionary of IF objects indexed by their names, ensuring no frequency range overlaps.
    Inherits from BaseContainer for universal collection management and serialization.

    Attributes:
        _items (Dict[str, IF]): Dictionary of IF objects with names as keys.
        name (str, optional): Identifier for the Frequencies object.
        isactive (bool): Indicates whether the Frequencies object is active.

    Notes:
        - Frequency ranges [freq, freq + bandwidth] must not overlap.
        - IF objects must have unique non-None names.
    """
    def __init__(self, *, name: Optional[str] = None, items: Dict[str, IF] = None, isactive: bool = True, use_cache: bool = False):
        """Initialize a Frequencies object with optional IFs."""
        if name is None:
            name = f"fqs_{uuid.uuid4().hex[:32]}"
        super().__init__(name=name, items=items or {}, isactive=isactive, use_cache=use_cache)
        for if_name, if_obj in (items or {}).items():
            self._check_overlap(if_obj, exclude_name=if_name)

    def add(self, if_obj: IF) -> None:
        """Add an IF object to the collection.

        Args:
            if_obj (IF): The IF object to add.

        Raises:
            ValueError: If frequency range overlaps with existing IFs.
        """
        self._check_overlap(if_obj, exclude_name=None)
        super().add(if_obj)
    
    def create_if(
        self,
        name: str = None,
        frequency: float = 1000.0,
        bandwidth: float = 16.0,
        polarizations: Optional[Union[str, List[str]]] = None,
        isactive: bool = True,
    ) -> None:
        """Create and add a new IF object to the collection.

        Args:
            name (str, optional): Unique identifier for the IF. If None, a UUID-based name is generated.
            frequency (float): The IF frequency in MHz. Default is 1000.0 MHz.
            bandwidth (float): The bandwidth in MHz. Default is 16.0 MHz.
            polarizations (Optional[Union[str, List[str]]]): Polarization codes. Default is None (empty list).
            isactive (bool): Whether the IF is active. Default is True.

        Raises:
            ValueError: If frequency or bandwidth is not positive, or if frequency range overlaps with existing IFs.
            ValueError: If polarizations are invalid or mix groups.
            TypeError: If polarizations contain non-string elements.
        """
        new_if = IF(
            name=name,
            frequency=frequency,
            bandwidth=bandwidth,
            polarizations=polarizations,
            isactive=isactive,
        )
        self.add(new_if)
        logger.info(f"Created and added IF '{new_if.name}' to Frequencies")
    
    def set_if(
        self,
        name: str,
        frequency: Optional[float] = None,
        bandwidth: Optional[float] = None,
        polarizations: Optional[Union[str, List[str]]] = None,
        isactive: Optional[bool] = None,
    ) -> None:
        """Update an existing IF object in the collection with new parameters.

        Args:
            name (str): The name of the IF to update.
            frequency (float, optional): The new IF frequency in MHz.
            bandwidth (float, optional): The new bandwidth in MHz.
            polarizations (Optional[Union[str, List[str]]], optional): The new polarization codes.
            isactive (bool, optional): The new active status.

        Raises:
            KeyError: If the IF with the given name does not exist.
            ValueError: If the new frequency range overlaps with existing IFs, or if frequency/bandwidth is not positive.
            ValueError: If polarizations are invalid or mix groups.
            TypeError: If polarizations contain non-string elements.
        """
        if name not in self._items:
            logger.error(f"IF with name '{name}' not found in Frequencies")
            raise KeyError(f"IF with name '{name}' not found in Frequencies")

        if_obj = self._items[name]
        
        temp_frequency = frequency if frequency is not None else if_obj.frequency
        temp_bandwidth = bandwidth if bandwidth is not None else if_obj.bandwidth
        temp_polarizations = polarizations if polarizations is not None else if_obj.polarizations
        temp_isactive = isactive if isactive is not None else if_obj.isactive

        if temp_frequency <= 0:
            logger.error("Frequency must be positive")
            raise ValueError("Frequency must be positive")
        if temp_bandwidth <= 0:
            logger.error("Bandwidth must be positive")
            raise ValueError("Bandwidth must be positive")

        temp_if = IF(
            name=name,
            frequency=temp_frequency,
            bandwidth=temp_bandwidth,
            polarizations=temp_polarizations,
            isactive=temp_isactive,
        )

        self._check_overlap(temp_if, exclude_name=name)

        params = {}
        if frequency is not None:
            params["frequency"] = frequency
        if bandwidth is not None:
            params["bandwidth"] = bandwidth
        if polarizations is not None:
            params["polarizations"] = temp_if.polarizations
        if isactive is not None:
            params["isactive"] = isactive

        if params:
            if_obj.set(params)
            logger.info(f"Updated IF '{name}' in Frequencies with params: {params}")
        else:
            logger.debug(f"No parameters to update for IF '{name}' in Frequencies")

    def set_item(self, name: str, item: IF) -> None:
        """Set or replace an IF object in the collection by its name.

        Args:
            name (str): The name of the IF to set.
            item (IF): The IF object to add or replace.

        Raises:
            ValueError: If the item's name does not match the provided name or if its frequency range overlaps with other IFs (except itself).
            TypeError: If the item is not of type IF.
        """
        if item.name != name:
            raise ValueError(f"IF name '{item.name}' does not match key '{name}'")
        if not isinstance(item, IF):
            raise TypeError(f"Item must be of type IF, got {type(item).__name__}")
        self._check_overlap(item, exclude_name=name)
        self._items[name] = item
        self._invalidate_cache()
        logger.debug(f"Set IF with name '{name}' in Frequencies")

    def set_items(self, items: Dict[str, IF]) -> None:
        """Set or replace all IF objects in the collection.

        Args:
            items: Dictionary of IF objects with names as keys.

        Raises:
            ValueError: If any frequency range overlaps with another.
        """
        for if_name, if_obj in items.items():
            self._check_overlap(if_obj, exclude_name=None)
        super().set_items(items)

    def get_frequencies(self) -> List[float]:
        """Retrieve a list of all IF frequencies.

        Returns:
            List[float]: List of frequencies in MHz.
        """
        return [if_obj.frequency for if_obj in self.get_items()]

    def get_bandwidths(self) -> List[float]:
        """Retrieve a list of all IF bandwidths.

        Returns:
            List[float]: List of bandwidths in MHz.
        """
        return [if_obj.bandwidth for if_obj in self.get_items()]

    def get_polarizations(self) -> List[List[str]]:
        """Retrieve a list of all IF polarizations.

        Returns:
            List[List[str]]: List of polarization lists.
        """
        return [if_obj.polarizations for if_obj in self.get_items()]

    def get_wavelengths(self) -> List[float]:
        """Retrieve a list of wavelengths for all IF frequencies.

        Returns:
            List[float]: List of wavelengths in centimeters.
        """
        return [if_obj.get_frequency_wavelength() for if_obj in self.get_items()]
    
    def copy(self) -> 'Frequencies':
        """Create a deep copy of the Frequencies object."""
        return Frequencies(
            items={name: item.copy() for name, item in self._items.items()},
            isactive=self.isactive,
            use_cache=self._use_cache
        )

    def _check_overlap(self, if_obj: IF, exclude_name: Optional[str]) -> None:
        """Check if an IF's frequency range overlaps with existing IFs.

        Args:
            if_obj: IF object to check.
            exclude_name: Name of IF to exclude from overlap check (for updates).

        Raises:
            ValueError: If frequency range overlaps with an existing IF or bandwidth is zero.
        """
        new_freq = if_obj.frequency
        new_bw = if_obj.bandwidth
        if new_bw <= 0:
            logger.error("Bandwidth must be positive for overlap check")
            raise ValueError("Bandwidth must be positive")
        new_end = new_freq + new_bw

        for name, existing_if in self.get_all().items():
            if name == exclude_name:
                continue
            ex_freq = existing_if.frequency
            ex_bw = existing_if.bandwidth
            if ex_bw <= 0:
                logger.error(f"Existing IF {name} has non-positive bandwidth")
                raise ValueError(f"Existing IF {name} has non-positive bandwidth")
            ex_end = ex_freq + ex_bw
            if new_freq < ex_end and new_end > ex_freq:
                logger.error(f"Frequency range [{new_freq}, {new_end}] overlaps with [{ex_freq}, {ex_end}]")
                raise ValueError(f"Frequency range [{new_freq}, {new_end}] overlaps with [{ex_freq}, {ex_end}]")

    def __repr__(self) -> str:
        """Return a string representation of the Frequencies object."""
        active_count = len(self.get_active_items())
        return f"Frequencies(name={self.name!r}, count={len(self._items)}, active={active_count}, inactive={len(self._items) - active_count})"