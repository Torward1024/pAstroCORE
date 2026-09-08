# base/frequencies.py
from typing import Annotated, Any, Dict, List, Optional, Union
from msb_arch.base.baseentity import BaseEntity
from msb_arch.base.basecontainer import BaseContainer
from msb_arch import InvariantError, Positive, invariant
from msb_arch.utils.logging_setup import logger
import uuid

C_MHZ_CM = 29979.2458
#: Ordered rather than sets, so that anything offering them -- an editor, a report -- offers
#: them in one order without keeping a second list of its own to do it.
CIRCULAR_POLARIZATIONS = ("RCP", "LCP")
SINGLE_LINEAR_POLARIZATIONS = ("H", "V")
VALID_POLARIZATIONS = CIRCULAR_POLARIZATIONS + SINGLE_LINEAR_POLARIZATIONS

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
        - **`frequency` is the sky frequency at the edge of the band**, and `sidebands` says
          which way the band runs from it: `U` covers `[frequency, frequency + bandwidth]`,
          `L` covers `[frequency - bandwidth, frequency]`. Both are real and different pieces
          of spectrum, and a receiver commonly records both from one local oscillator.
    """

    #: Which way a band runs from its sky frequency. The letters are VEX's and CFX's.
    VALID_SIDEBANDS = ("U", "L")

    name: str
    frequency: Annotated[float, Positive()]
    bandwidth: Annotated[float, Positive()]
    polarizations: List[str]
    sidebands: List[str]
    isactive: bool

    def __init__(self, *, name: str = None, frequency: float = 1000.0, bandwidth: float = 16.0,
                 polarizations: Optional[Union[str, List[str]]] = None,
                 sidebands: Optional[Union[str, List[str]]] = None, isactive: bool = True):
        """Initialize an IF object with frequency, bandwidth, polarizations, and active status.

        Notes:
            - **`sidebands` is a list, like `polarizations`, and for the same reason.** One
              receiver setting at one sky frequency records what it records: a band with both
              sidebands and both circular polarizations is four channels, and it is still one
              setting. Making the sideband a property *of* the band would mean two `IF`s
              carrying the same frequency, kept in step by hand.
            - Defaults to `["U"]`, which is what every band written before this field existed
              was implicitly taken to be: the overlap rule read a band as
              `[frequency, frequency + bandwidth]`, and that is upper sideband.
        """
        polarizations = self._validate_polarizations(polarizations)
        super().__init__(name=name, frequency=frequency, bandwidth=bandwidth,
                         polarizations=polarizations,
                         sidebands=self._validate_sidebands(sidebands), isactive=isactive)
        if name is None:
            name = f"if_{uuid.uuid4().hex[:32]}"

    @staticmethod
    def _validate_sidebands(sidebands: Any) -> List[str]:
        """Return the sidebands as a list of `U` and `L`, accepting the words people write.

        Raises:
            ValueError: If any of them is neither.
            TypeError: If a list holds something that is not a string.
        """
        if sidebands is None:
            return ["U"]
        if isinstance(sidebands, str):
            sidebands = [sidebands]
        if not all(isinstance(one, str) for one in sidebands):
            raise TypeError("Sidebands must be a string or a list of strings")

        spelled = {"USB": "U", "UPPER": "U", "LSB": "L", "LOWER": "L"}
        found = []
        for one in sidebands:
            letter = spelled.get(one.strip().upper(), one.strip().upper())
            if letter not in IF.VALID_SIDEBANDS:
                raise ValueError(f"Sideband must be 'U' or 'L', got {one!r}")
            if letter not in found:
                found.append(letter)
        return found or ["U"]

    def get_sidebands(self) -> List[str]:
        """Which sidebands this band records: `U`, `L`, or both."""
        return self.sidebands

    def set_sidebands(self, sidebands: Union[str, List[str]]) -> None:
        """Set which sidebands are recorded. Takes `U`/`USB`/`upper`, `L`/`LSB`/`lower`."""
        self.sidebands = self._validate_sidebands(sidebands)

    @staticmethod
    def band_of(frequency: float, bandwidth: float, sidebands: List[str]) -> tuple:
        """Return the spectrum a setting would cover, as `(low, high)` in MHz.

        Args:
            frequency (float): The sky frequency, at the edge of the band.
            bandwidth (float): The bandwidth in MHz.
            sidebands (List[str]): `U`, `L`, or both.

        Notes:
            - **The one place a sideband is turned into numbers.** It takes loose values rather
              than an `IF` so that an editor can show what the fields on screen *would* cover
              before anything is saved -- which is the moment the answer is useful -- without
              subtracting a bandwidth itself and getting it wrong differently.
        """
        low = frequency - bandwidth if "L" in sidebands else frequency
        high = frequency + bandwidth if "U" in sidebands else frequency
        return (low, high)

    def get_band(self) -> tuple:
        """Return the spectrum this band actually covers, as `(low, high)` in MHz.

        Notes:
            - Everything that needs to know what a band covers -- the overlap rule, an
              exporter, a person asking what was recorded -- asks this or `band_of` rather
              than adding or subtracting a bandwidth itself.
            - With both sidebands it spans `[frequency - bandwidth, frequency + bandwidth]`:
              one setting recording either side of its sky frequency covers both.
        """
        return self.band_of(self.frequency, self.bandwidth, self.sidebands)

    def get_channel_count(self) -> int:
        """How many channels this one setting records: a polarization times a sideband.

        Notes:
            - What VEX writes as `chan_def` and CFX as `IF =`. One band at 4828 MHz with two
              circular polarizations and both sidebands is four of them, which is exactly what
              the RadioAstron example records.
        """
        return max(len(self.polarizations), 1) * len(self.sidebands)

    def get_center_frequency(self) -> float:
        """The middle of what this band covers, in MHz.

        Notes:
            - `frequency` is an edge, unless both sidebands are recorded, in which case it is
              already the middle. For anything wanting one representative frequency -- a
              wavelength to scale a baseline by -- this is the honest answer.
        """
        low, high = self.get_band()
        return (low + high) / 2.0

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
        logger.debug("Calculated wavelength=%s cm for IF frequency=%s MHz", wavelength, self.frequency)
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
        logger.info("Set IF frequency to %s MHz from wavelength=%s cm", self.frequency, wavelength_cm)
    
    def copy(self) -> 'IF':
        """Create a deep copy of the IF object."""
        return IF(
            name=self.name,
            frequency=self.frequency,
            bandwidth=self.bandwidth,
            polarizations=self.polarizations.copy(),
            sidebands=list(self.sidebands),
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
                logger.error("Invalid polarization value: %s", p)
                raise ValueError(f"Polarization must be one of {VALID_POLARIZATIONS}, got {p}")

        # The group rule is an `@invariant` rather than a check here, so that it also holds for
        # `set` and for a project being read back. This normalizes; the rule below refuses.
        return polarizations

    @invariant("polarizations must all be circular or all be linear")
    def _polarizations_are_one_group(self) -> bool:
        """A band is recorded in circular polarization or in linear, never in a mixture.

        Notes:
            - It was checked in `_validate_polarizations`, which runs from `__init__` and
              nowhere else: `set({"polarizations": ["RCP", "H"]})` was accepted, and so was a
              saved project carrying one back. The same shape as the coordinate range and the
              scan duration before them.
            - An empty list is not a mixture. A band with no polarization entered means nothing
              was said, and the exporter writes that as "not stated" rather than as an answer.
        """
        if not self.polarizations:
            return True
        return (all(p in CIRCULAR_POLARIZATIONS for p in self.polarizations)
                or all(p in SINGLE_LINEAR_POLARIZATIONS for p in self.polarizations))

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

    @invariant("frequency ranges must not overlap")
    def _bands_do_not_overlap(self) -> bool:
        """No two IFs may cover the same frequency.

        Raises:
            InvariantError: Naming both bands and what each covers.

        Notes:
            - A rule about the contents rather than about any one IF, which is what an
              invariant is for. It was a `_check_overlap` helper called by hand from six
              places -- the constructor, `add`, `create_if`, `set_if`, `set_item` and
              `set_items` -- so it held exactly where somebody had remembered it. msb_arch
              1.10.0 checks a container's rule after `add`, `remove`, `set_item`, `set_items`
              and `remove_all`, and puts the items back when it refuses.
            - Sorted rather than compared pairwise: the hand-written version asked one new band
              against every existing one, which is the same work per call and quadratic when
              the whole container is checked.
            - Raises its own error so the message still names the two bands. A rule that only
              answers False would say "frequency ranges must not overlap" and leave the user to
              find which two.
        """
        bands = []
        for name, if_obj in self.get_all().items():
            if if_obj.bandwidth <= 0:
                raise InvariantError(
                    f"IF '{name}' has a bandwidth of {if_obj.bandwidth}; it must be positive")
            # Asked of the band rather than added here: a lower sideband runs *down* from its
            # sky frequency, so 4828 U and 4828 L are adjacent rather than the same band twice.
            low, high = if_obj.get_band()
            bands.append((low, high, name))

        bands.sort()
        for (start, end, name), (next_start, next_end, next_name) in zip(bands, bands[1:]):
            if next_start < end:
                raise InvariantError(
                    f"'{name}' covers [{start}, {end}] and '{next_name}' covers "
                    f"[{next_start}, {next_end}]; frequency ranges must not overlap")
        return True

    def add(self, if_obj: IF) -> None:
        """Add an IF object to the collection.

        Args:
            if_obj (IF): The IF object to add.

        Raises:
            InvariantError: If the frequency range overlaps an IF already here.
        """
        super().add(if_obj)


    def create_if(
        self,
        name: str = None,
        frequency: float = 1000.0,
        bandwidth: float = 16.0,
        polarizations: Optional[Union[str, List[str]]] = None,
        sidebands: Optional[Union[str, List[str]]] = None,
        isactive: bool = True,
    ) -> None:
        """Create and add a new IF object to the collection.

        Args:
            name (str, optional): Unique identifier for the IF. If None, a UUID-based name is generated.
            frequency (float): The IF frequency in MHz. Default is 1000.0 MHz.
            bandwidth (float): The bandwidth in MHz. Default is 16.0 MHz.
            polarizations (Optional[Union[str, List[str]]]): Polarization codes. Default is None (empty list).
            sidebands (str | List[str]): Which sidebands are recorded -- `U`, `L`, or both.
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
            sidebands=sidebands,
            isactive=isactive,
        )
        self.add(new_if)
        logger.info("Created and added IF '%s' to Frequencies", new_if.name)
    
    def set_if(
        self,
        name: str,
        frequency: Optional[float] = None,
        bandwidth: Optional[float] = None,
        polarizations: Optional[Union[str, List[str]]] = None,
        sidebands: Optional[Union[str, List[str]]] = None,
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
            logger.error("IF with name '%s' not found in Frequencies", name)
            raise KeyError(f"IF with name '{name}' not found in Frequencies")

        if_obj = self._items[name]
        
        temp_frequency = frequency if frequency is not None else if_obj.frequency
        temp_bandwidth = bandwidth if bandwidth is not None else if_obj.bandwidth
        temp_polarizations = polarizations if polarizations is not None else if_obj.polarizations
        temp_sidebands = sidebands if sidebands is not None else if_obj.sidebands
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
            sidebands=temp_sidebands,
            isactive=temp_isactive,
        )

        params = {}
        if frequency is not None:
            params["frequency"] = frequency
        if bandwidth is not None:
            params["bandwidth"] = bandwidth
        if polarizations is not None:
            params["polarizations"] = temp_if.polarizations
        if sidebands is not None:
            params["sidebands"] = temp_if.sidebands
        if isactive is not None:
            params["isactive"] = isactive

        if params:
            # An IF is edited in place, so the container is never told and cannot check its
            # own rule. Written, checked, and put back when the rule refuses -- which is what
            # msb_arch does for a field, and the same reason: a refused change must leave the
            # object exactly as it was.
            was = {key: getattr(if_obj, key) for key in params}
            if_obj.set(params)
            try:
                self.check_invariants()
            except InvariantError:
                if_obj.set(was)
                raise
            logger.info("Updated IF '%s' in Frequencies with params: %s", name, params)
        else:
            logger.debug("No parameters to update for IF '%s' in Frequencies", name)

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
        # Through the container rather than into `_items`: writing the mapping directly is what
        # made this the one path where the overlap rule could be skipped, and it is also what
        # the container checks its rule after.
        super().set_item(name, item)
        logger.debug("Set IF with name '%s' in Frequencies", name)

    def set_items(self, items: Dict[str, IF]) -> None:
        """Set or replace all IF objects in the collection.

        Args:
            items: Dictionary of IF objects with names as keys.

        Raises:
            InvariantError: If any frequency range overlaps with another.
        """
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

    def __repr__(self) -> str:
        """Return a string representation of the Frequencies object."""
        active_count = len(self.get_active_items())
        return f"Frequencies(name={self.name!r}, count={len(self._items)}, active={active_count}, inactive={len(self._items) - active_count})"