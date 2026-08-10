# telescopes.py
from msb_arch.base.basecontainer import BaseContainer
from msb_arch.utils.validation import check_type
from msb_arch.utils.logging_setup import logger
from typing import Optional, Dict, Tuple, Union, Any
from .telescope import Telescope
from .spacetelescope import SpaceTelescope
import re
import uuid

class Telescopes(BaseContainer[Union[Telescope, SpaceTelescope]]):
    """Class representing a collection of Telescope and SpaceTelescope objects.

    Manages a dictionary of telescopes, indexed by their code, ensuring no duplicates.
    Inherits from BaseContainer for collection management, activation/deactivation,
    and serialization. Supports synchronization with a parent Observation object.

    Attributes:
        _items (Dict[str, Telescope | SpaceTelescope]): Dictionary of telescope objects, keyed by code.
        isactive (bool): Whether the Telescopes object itself is active.

    Notes:
        - Telescopes are identified by their unique code (`get_code()`), used as the dictionary key.
        - Activation/deactivation triggers synchronization with a parent Observation via `_parent._sync_scans_with_activation`.
        - Both `name` and `code` must be unique and valid strings (no spaces or special characters).
        - Transition from index-based to code-based access requires updating dependent code to use telescope codes.

    Examples:
        >>> tels = Telescopes()
        >>> tels.create_telescope(code="RT32", name="Radio Telescope 32m", diameter=32.0)
        >>> print(tels)
        Telescopes(count=1, active=1, inactive=0)
        >>> tels.add(Telescope(code="RT32", name="Duplicate"))
        Traceback (most recent call last):
        ...
        ValueError: Telescope with code 'RT32' already exists in Telescopes
    """
    def __init__(self, items: Optional[Dict[str, Union[Telescope, SpaceTelescope]]] = None,
                 name: str = None, isactive: bool = True, use_cache: bool = False):
        """Initialize a Telescopes object with an optional dictionary of telescopes.

        Args:
            items (Dict[str, Telescope | SpaceTelescope], optional): Initial dictionary of telescopes, keyed by code.
            name (str, optional): Identifier for the collection. Defaults to None.
            isactive (bool): Initial activation status. Defaults to True.
            use_cache (bool): Enable caching for `to_dict` results. Defaults to False.

        Raises:
            TypeError: If items contains non-Telescope/SpaceTelescope objects or keys are not strings.
            ValueError: If a telescope's code does not match its dictionary key or is invalid.
        """
        if name is None:
            name = f"tlscs_{uuid.uuid4().hex[:32]}"
        super().__init__(items=items, name=name, isactive=isactive, use_cache=use_cache)
        logger.debug("Initialized Telescopes with %s telescopes", len(self._items))

    def _validate_item(self, item: Union[Telescope, SpaceTelescope], exclude_name: Optional[str] = None) -> None:
        """Validate that the item is a Telescope or SpaceTelescope and has a valid and unique name and code.

        Args:
            item (Telescope | SpaceTelescope): The telescope to validate.
            exclude_name (str, optional): Name of the item to exclude from uniqueness checks, used during updates.

        Raises:
            TypeError: If item is not a Telescope or SpaceTelescope.
            ValueError: If the telescope's name or code is empty, invalid, or not unique (except for excluded item).
        """
        check_type(item, (Telescope, SpaceTelescope), "Telescope")
        name = item.name
        code = item.get_code()
        
        if not name or not isinstance(name, str):
            raise ValueError("Telescope name must be a non-empty string")
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise ValueError(f"Telescope name '{name}' contains invalid characters")
        if name in self._items and self._items[name] is not item and name != exclude_name:
            raise ValueError(f"Telescope with name '{name}' already exists")

        if not code or not isinstance(code, str):
            raise ValueError("Telescope code must be a non-empty string")
        if not re.match(r'^[a-zA-Z0-9_-]+$', code):
            raise ValueError(f"Telescope code '{code}' contains invalid characters")

        for existing_item in self._items.values():
            if existing_item is not item and existing_item.get_code() == code and existing_item.name != exclude_name:
                raise ValueError(f"Telescope with code '{code}' already exists")
                
        logger.debug("Validated telescope with name='%s', code='%s'", name, code)

    def set_item(self, name: str, item: Union[Telescope, SpaceTelescope]) -> None:
        """Set or replace a telescope in the collection by its name.

        Args:
            name (str): The name of the telescope to set.
            item (Telescope | SpaceTelescope): The telescope to add or replace.

        Raises:
            ValueError: If the item's name does not match the provided name or if it fails validation.
            TypeError: If the item's type is not Telescope or SpaceTelescope.
        """
        if item.name != name:
            raise ValueError(f"Telescope name '{item.name}' does not match key '{name}'")
        check_type(item, (Telescope, SpaceTelescope), "Telescope")
        self._validate_item(item, exclude_name=name)
        self._items[name] = item
        self._invalidate_cache()
        logger.debug("Set telescope with name '%s' in Telescopes", name)

    def create_telescope(self, code: str = "TEMP", name: str = "Temporary Telescope",
                        x: float = 0.0, y: float = 0.0, z: float = 0.0,
                        vx: float = 0.0, vy: float = 0.0, vz: float = 0.0,
                        diameter: float = 1.0, sefd_table: Optional[Dict[float, float]] = None,
                        elevation_range: Tuple[float, float] = (15.0, 90.0),
                        azimuth_range: Tuple[float, float] = (0.0, 360.0),
                        mount_type: str = "AZIM", isactive: bool = True) -> None:
        """Create and add a new ground-based Telescope object to the collection.

        Args:
            code (str): Unique short name. Defaults to "TEMP".
            name (str): Full name. Defaults to "Temporary Telescope".
            x (float): X-coordinate in ITRF (meters). Defaults to 0.0.
            y (float): Y-coordinate in ITRF (meters). Defaults to 0.0.
            z (float): Z-coordinate in ITRF (meters). Defaults to 0.0.
            vx (float): X-velocity in ITRF (meters/year). Defaults to 0.0.
            vy (float): Y-velocity in ITRF (meters/year). Defaults to 0.0.
            vz (float): Z-velocity in ITRF (meters/year). Defaults to 0.0.
            diameter (float): Antenna diameter in meters. Defaults to 1.0.
            sefd_table (Optional[Dict[float, float]]): SEFD table (MHz: Jy). Defaults to None.
            elevation_range (Tuple[float, float]): Min and max elevation in degrees. Defaults to (15.0, 90.0).
            azimuth_range (Tuple[float, float]): Min and max azimuth in degrees. Defaults to (0.0, 360.0).
            mount_type (str): Mount type ('EQUA', 'AZIM', or 'NONE'). Defaults to "AZIM".
            isactive (bool): Whether the telescope is active. Defaults to True.

        Raises:
            TypeError: If inputs are of incorrect type.
            ValueError: If code or name is a duplicate, invalid, or other Telescope initialization errors occur.
        """
        if not re.match(r'^[a-zA-Z0-9_-]+$', code):
            raise ValueError(f"Invalid telescope code '{code}' (use alphanumeric, underscore, or hyphen)")
        new_telescope = Telescope(
            code=code, name=code, x=x, y=y, z=z, vx=vx, vy=vy, vz=vz,
            diameter=diameter, sefd_table=sefd_table,
            elevation_range=elevation_range, azimuth_range=azimuth_range,
            mount_type=mount_type, isactive=isactive
        )
        self.add(new_telescope)
        logger.debug("Created and added telescope '%s'", code)

    def create_space_telescope(self, code: str = "TS", name: str = "Temporary Space Telescope",
                          orbit_file: str = "dummy_orbit.oem", diameter: float = 1.0,
                          sefd_table: Optional[Dict[float, float]] = None,
                          pitch_range: Tuple[float, float] = (-90.0, 90.0),
                          yaw_range: Tuple[float, float] = (-180.0, 180.0),
                          isactive: bool = True, use_kep: bool = True,
                          kepler_elements: Optional[dict] = None,
                          interpolation_method: str = "chebyshev",
                          surface_accuracy: Optional[float] = None,
                          surface_efficiency_table: Optional[Dict[float, float]] = None,
                          effective_area_table: Optional[Dict[float, float]] = None,
                          system_temperature_table: Optional[Dict[float, float]] = None) -> None:
        """Create and add a new SpaceTelescope object to the collection.

        Args:
            code (str): Unique short name. Defaults to "TS".
            name (str): Full name (set to code for consistency). Defaults to "Temporary Space Telescope".
            orbit_file (str): Path to the orbit file. Defaults to "dummy_orbit.oem".
            diameter (float): Antenna diameter in meters. Defaults to 1.0.
            sefd_table (Optional[Dict[float, float]]): SEFD table (MHz: Jy). Defaults to None.
            pitch_range (Tuple[float, float]): Min and max pitch in degrees. Defaults to (-90.0, 90.0).
            yaw_range (Tuple[float, float]): Min and max yaw in degrees. Defaults to (-180.0, 180.0).
            isactive (bool): Whether the telescope is active. Defaults to True.
            use_kep (bool): Use Keplerian elements for orbit calculation. Defaults to True.
            kepler_elements (Optional[dict]): Keplerian elements for orbit calculation. Defaults to None.
            interpolation_method (str): Interpolation method for orbit data ('linear', 'chebyshev', 'cubic_spline'). Defaults to "chebyshev".
            surface_accuracy (Optional[float]): Surface accuracy in meters. Defaults to None.
            surface_efficiency_table (Optional[Dict[float, float]]): Surface efficiency table (MHz: efficiency). Defaults to None.
            effective_area_table (Optional[Dict[float, float]]): Effective area table (MHz: area). Defaults to None.
            system_temperature_table (Optional[Dict[float, float]]): System temperature table (MHz: Kelvin). Defaults to None.

        Raises:
            TypeError: If inputs are of incorrect type.
            ValueError: If code or name is a duplicate, invalid, or other SpaceTelescope initialization errors occur.
        """
        if not re.match(r'^[a-zA-Z0-9_-]+$', code):
            raise ValueError(f"Invalid space telescope code '{code}' (use alphanumeric, underscore, or hyphen)")
        new_telescope = SpaceTelescope(
            code=code, name=code, orbit_file=orbit_file, diameter=diameter, sefd_table=sefd_table,
            pitch_range=pitch_range, yaw_range=yaw_range, isactive=isactive, use_kep=use_kep,
            kepler_elements=kepler_elements, interpolation_method=interpolation_method,
            surface_accuracy=surface_accuracy, surface_efficiency_table=surface_efficiency_table,
            effective_area_table=effective_area_table, system_temperature_table=system_temperature_table
        )
        self.add(new_telescope)
        logger.debug("Created and added space telescope '%s'", code)

    def set_telescope(
        self,
        code: str,
        name: Optional[str] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        vx: Optional[float] = None,
        vy: Optional[float] = None,
        vz: Optional[float] = None,
        diameter: Optional[float] = None,
        sefd_table: Optional[Dict[float, float]] = None,
        elevation_range: Optional[Tuple[float, float]] = None,
        azimuth_range: Optional[Tuple[float, float]] = None,
        mount_type: Optional[str] = None,
        orbit_file: Optional[str] = None,
        pitch_range: Optional[Tuple[float, float]] = None,
        yaw_range: Optional[Tuple[float, float]] = None,
        use_kep: Optional[bool] = None,
        kepler_elements: Optional[dict] = None,
        interpolation_method: Optional[str] = None,
        surface_accuracy: Optional[float] = None,
        surface_efficiency_table: Optional[Dict[float, float]] = None,
        effective_area_table: Optional[Dict[float, float]] = None,
        system_temperature_table: Optional[Dict[float, float]] = None,
        isactive: Optional[bool] = None
    ) -> None:
        """Update an existing Telescope or SpaceTelescope object in the collection.

        Args:
            code (str): The code of the telescope to update.
            name (str, optional): New full name for the telescope.
            x (float, optional): New X-coordinate in ITRF (meters).
            y (float, optional): New Y-coordinate in ITRF (meters).
            z (float, optional): New Z-coordinate in ITRF (meters).
            vx (float, optional): New X-velocity in ITRF (meters/year).
            vy (float, optional): New Y-velocity in ITRF (meters/year).
            vz (float, optional): New Z-velocity in ITRF (meters/year).
            diameter (float, optional): New antenna diameter in meters.
            sefd_table (Dict[float, float], optional): New SEFD table (MHz: Jy).
            elevation_range (Tuple[float, float], optional): New min and max elevation in degrees.
            azimuth_range (Tuple[float, float], optional): New min and max azimuth in degrees.
            mount_type (str, optional): New mount type ('EQUA', 'AZIM', or 'NONE').
            orbit_file (str, optional): New path to the orbit file (for SpaceTelescope).
            pitch_range (Tuple[float, float], optional): New min and max pitch in degrees (for SpaceTelescope).
            yaw_range (Tuple[float, float], optional): New min and max yaw in degrees (for SpaceTelescope).
            use_kep (bool, optional): Use Keplerian elements for orbit calculation (for SpaceTelescope).
            kepler_elements (dict, optional): New Keplerian elements for orbit calculation (for SpaceTelescope).
            interpolation_method (str, optional): New interpolation method for orbit data (for SpaceTelescope).
            surface_accuracy (float, optional): New surface accuracy in meters (for SpaceTelescope).
            surface_efficiency_table (Dict[float, float], optional): New surface efficiency table (for SpaceTelescope).
            effective_area_table (Dict[float, float], optional): New effective area table (for SpaceTelescope).
            system_temperature_table (Dict[float, float], optional): New system temperature table (for SpaceTelescope).
            isactive (bool, optional): New active status.

        Raises:
            KeyError: If the telescope with the given code does not exist.
            ValueError: If the new name or code is invalid, not unique (except for the updated item), or if other telescope parameters are invalid.
            TypeError: If input types are incorrect.
        """

        telescope = next((t for t in self._items.values() if t.get_code() == code), None)
        if telescope is None:
            logger.error("Telescope with code '%s' not found in Telescopes", code)
            raise KeyError(f"Telescope with code '{code}' not found in Telescopes")

        params = {}
        if name is not None:
            if not re.match(r'^[a-zA-Z0-9_-]+$', name):
                raise ValueError(f"Invalid telescope name '{name}' (use alphanumeric, underscore, or hyphen)")
            params["name"] = name
        if x is not None:
            params["x"] = x
        if y is not None:
            params["y"] = y
        if z is not None:
            params["z"] = z
        if vx is not None:
            params["vx"] = vx
        if vy is not None:
            params["vy"] = vy
        if vz is not None:
            params["vz"] = vz
        if diameter is not None:
            if diameter <= 0:
                raise ValueError("Diameter must be positive")
            params["diameter"] = diameter
        if sefd_table is not None:
            params["sefd_table"] = sefd_table
        if elevation_range is not None:
            params["elevation_range"] = elevation_range
        if azimuth_range is not None:
            params["azimuth_range"] = azimuth_range
        if mount_type is not None:
            params["mount_type"] = mount_type
        if orbit_file is not None:
            if not isinstance(telescope, SpaceTelescope):
                raise ValueError("Orbit file can only be set for SpaceTelescope")
            params["orbit_file"] = orbit_file
        if pitch_range is not None:
            if not isinstance(telescope, SpaceTelescope):
                raise ValueError("Pitch range can only be set for SpaceTelescope")
            params["pitch_range"] = pitch_range
        if yaw_range is not None:
            if not isinstance(telescope, SpaceTelescope):
                raise ValueError("Yaw range can only be set for SpaceTelescope")
            params["yaw_range"] = yaw_range
        if use_kep is not None:
            if not isinstance(telescope, SpaceTelescope):
                raise ValueError("Use_kep can only be set for SpaceTelescope")
            params["use_kep"] = use_kep
        if kepler_elements is not None:
            if not isinstance(telescope, SpaceTelescope):
                raise ValueError("Kepler elements can only be set for SpaceTelescope")
            params["kepler_elements"] = kepler_elements
        if interpolation_method is not None:
            if not isinstance(telescope, SpaceTelescope):
                raise ValueError("Interpolation method can only be set for SpaceTelescope")
            params["interpolation_method"] = interpolation_method
        if surface_accuracy is not None:
            if not isinstance(telescope, SpaceTelescope):
                raise ValueError("Surface accuracy can only be set for SpaceTelescope")
            params["surface_accuracy"] = surface_accuracy
        if surface_efficiency_table is not None:
            if not isinstance(telescope, SpaceTelescope):
                raise ValueError("Surface efficiency table can only be set for SpaceTelescope")
            params["surface_efficiency_table"] = surface_efficiency_table
        if effective_area_table is not None:
            if not isinstance(telescope, SpaceTelescope):
                raise ValueError("Effective area table can only be set for SpaceTelescope")
            params["effective_area_table"] = effective_area_table
        if system_temperature_table is not None:
            if not isinstance(telescope, SpaceTelescope):
                raise ValueError("System temperature table can only be set for SpaceTelescope")
            params["system_temperature_table"] = system_temperature_table
        if isactive is not None:
            params["isactive"] = isactive

        if params:
            temp_telescope = telescope.copy()
            temp_telescope.set(params)
            self._validate_item(temp_telescope, exclude_name=telescope.name)

            old_name = telescope.name
            telescope.set(params)
            logger.info("Updated telescope '%s' with params: %s", code, params)

            if name is not None and name != old_name:
                self._items.pop(old_name)
                self._items[name] = telescope
                logger.debug("Updated telescope dictionary key from '%s' to '%s'", old_name, name)

            if self._parent is not None and hasattr(self._parent, '_sync_scans_with_activation'):
                self._parent._sync_scans_with_activation()
        else:
            logger.debug("No parameters to update for telescope '%s'", code)
    
    def copy(self) -> 'Telescopes':
        """Create a deep copy of the Telescopes object."""
        return Telescopes(
            items={name: item.copy() for name, item in self._items.items()},
            isactive=self.isactive,
            use_cache=self._use_cache
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Telescopes':
        """Create a Telescopes object from a dictionary.

        Ensures that both name and code of telescopes are unique during deserialization.

        Args:
            data (Dict[str, Any]): Dictionary containing telescope data.

        Returns:
            Telescopes: A new Telescopes object populated with deserialized telescopes.

        Raises:
            ValueError: If duplicate name or code is found, or if telescope data is invalid.
        """
        items = {}
        codes = set()
        for key, item_data in data.get("items", {}).items():
            try:
                telescope_type = item_data.get("type", "Telescope")
                if telescope_type == "SpaceTelescope":
                    telescope = SpaceTelescope.from_dict(item_data)
                else:
                    telescope = Telescope.from_dict(item_data)
                if telescope.name in items:
                    logger.error("Duplicate telescope name '%s' found for key '%s'", telescope.name, key)
                    raise ValueError(f"Telescope with name '{telescope.name}' already exists")
                if telescope.get_code() in codes:
                    logger.error("Duplicate telescope code '%s' found for key '%s'", telescope.get_code(), key)
                    raise ValueError(f"Telescope with code '{telescope.get_code()}' already exists")
                items[telescope.name] = telescope
                codes.add(telescope.get_code())
                logger.debug("Deserialized telescope with name='%s', code='%s' for key='%s'", telescope.name, telescope.code, key)
            except Exception as e:
                logger.error("Failed to deserialize telescope for key '%s': %s", key, str(e))
                raise ValueError(f"Invalid telescope data for key '{key}': {str(e)}") from e

        return cls(
            items=items,
            name=data.get("name", f"tlscs_{uuid.uuid4().hex[:32]}"),
            isactive=data.get("isactive", True),
            use_cache=data.get("use_cache", False)
        )