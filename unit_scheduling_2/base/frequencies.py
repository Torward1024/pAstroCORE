# base/frequencies.py
from typing import List, Optional, Union, Dict
from common.base.baseentity import BaseEntity
from common.base.basecontainer import BaseContainer
from common.utils.logging_setup import logger

# Speed of light constant in MHz * cm
C_MHZ_CM = 29979.2458

# Allowed polarization code values
CIRCULAR_POLARIZATIONS = {"RCP", "LCP"}
PAIRED_LINEAR_POLARIZATIONS = {"RR", "LL", "RL", "LR"}
SINGLE_LINEAR_POLARIZATIONS = {"H", "V"}
VALID_POLARIZATIONS = CIRCULAR_POLARIZATIONS.union(PAIRED_LINEAR_POLARIZATIONS).union(SINGLE_LINEAR_POLARIZATIONS)

class IF(BaseEntity):
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
    frequency: float
    bandwidth: float
    polarizations: List[str]
    name: Optional[str]
    isactive: bool

    def __init__(self, *, name: Optional[str] = None, frequency: float = 1000.0, bandwidth: float = 16.0,
                 polarizations: Optional[Union[str, List[str]]] = None, isactive: bool = True):
        """Initialize an IF object with frequency, bandwidth, polarizations, and active status."""
        polarizations = self._validate_polarizations(polarizations)
        super().__init__(name=name, frequency=frequency, bandwidth=bandwidth,
                         polarizations=polarizations, isactive=isactive)
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
            elif all(p in PAIRED_LINEAR_POLARIZATIONS for p in polarizations):
                group = "paired linear (RR, LL, RL, LR)"
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

    def get_active_frequencies(self) -> List[IF]:
        """Retrieve all active IF objects.

        Returns:
            List[IF]: List of active IF objects.
        """
        return [if_obj for if_obj in self.get_items() if if_obj.isactive]

    def get_inactive_frequencies(self) -> List[IF]:
        """Retrieve all inactive IF objects.

        Returns:
            List[IF]: List of inactive IF objects.
        """
        return [if_obj for if_obj in self.get_items() if not if_obj.isactive]

    def activate_all(self) -> None:
        """Activate all IF objects in the collection.

        Raises:
            ValueError: If the collection is empty.
        """
        if not self._items:
            logger.error("No IFs to activate")
            raise ValueError("No IFs to activate")
        for if_obj in self.get_items():
            if_obj.activate()
        logger.info("Activated all IFs")

    def deactivate_all(self) -> None:
        """Deactivate all IF objects in the collection.

        Raises:
            ValueError: If the collection is empty.
        """
        if not self._items:
            logger.error("No IFs to deactivate")
            raise ValueError("No IFs to deactivate")
        for if_obj in self.get_items():
            if_obj.deactivate()
        logger.info("Deactivated all IFs")

    def drop_active(self) -> None:
        """Remove all active IF objects from the collection.

        Raises:
            ValueError: If there are no active IFs.
        """
        active_names = [name for name, if_obj in self.get_all().items() if if_obj.isactive]
        if not active_names:
            logger.warning("No active IFs to drop")
            raise ValueError("No active IFs to remove")
        for name in active_names:
            self.remove(name)
        logger.info(f"Dropped {len(active_names)} active IFs")

    def drop_inactive(self) -> None:
        """Remove all inactive IF objects from the collection.

        Raises:
            ValueError: If there are no inactive IFs.
        """
        inactive_names = [name for name, if_obj in self.get_all().items() if not if_obj.isactive]
        if not inactive_names:
            logger.warning("No inactive IFs to drop")
            raise ValueError("No inactive IFs to remove")
        for name in inactive_names:
            self.remove(name)
        logger.info(f"Dropped {len(inactive_names)} inactive IFs")

    def _check_overlap(self, if_obj: IF, exclude_name: Optional[str]) -> None:
        """Check if an IF's frequency range overlaps with existing IFs.

        Args:
            if_obj: IF object to check.
            exclude_name: Name of IF to exclude from overlap check (for updates).

        Raises:
            ValueError: If frequency range overlaps with an existing IF.
        """
        new_freq = if_obj.frequency
        new_bw = if_obj.bandwidth
        new_end = new_freq + new_bw

        for name, existing_if in self.get_all().items():
            if name == exclude_name:
                continue
            ex_freq = existing_if.frequency
            ex_bw = existing_if.bandwidth
            ex_end = ex_freq + ex_bw
            if new_freq < ex_end and new_end > ex_freq:
                logger.error(f"Frequency range [{new_freq}, {new_end}] overlaps with [{ex_freq}, {ex_end}]")
                raise ValueError(f"Frequency range [{new_freq}, {new_end}] overlaps with [{ex_freq}, {ex_end}]")

    def __repr__(self) -> str:
        """Return a string representation of the Frequencies object."""
        active_count = len(self.get_active_frequencies())
        return f"Frequencies(name={self.name!r}, count={len(self._items)}, active={active_count}, inactive={len(self._items) - active_count})"