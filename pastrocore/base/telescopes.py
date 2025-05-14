# telescopes.py
from common.base.basecontainer import BaseContainer
from common.utils.validation import check_type
from common.utils.logging_setup import logger
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
        isactive (bool): Whether the Telescopes object itself is active. Inherited from BaseEntity.

    Notes:
        - Telescopes are identified by their unique code (`get_code()`), used as the dictionary key.
        - Activation/deactivation triggers synchronization with a parent Observation via `_parent._sync_scans_with_activation`.
        - The `code` must be a valid string (no spaces or special characters) to ensure compatibility with dictionary keys.
        - Transition from index-based to code-based access requires updating dependent code to use telescope codes.

    Examples:
        >>> tels = Telescopes()
        >>> tels.create_telescope(code="RT32", name="Radio Telescope 32m", diameter=32.0)
        >>> print(tels)
        Telescopes(count=1, active=1, inactive=0)
        >>> tels.add(Telescope(code="RT32", name="Duplicate"))
        Traceback (most recent call last):
        ...
        ValueError: Item with name 'RT32' already exists in Telescopes
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
        logger.info(f"Initialized Telescopes with {len(self._items)} telescopes")

    def _validate_item(self, item: Union[Telescope, SpaceTelescope]) -> None:
        """Validate that the item is a Telescope or SpaceTelescope and has a valid code.

        Args:
            item (Telescope | SpaceTelescope): The telescope to validate.

        Raises:
            TypeError: If item is not a Telescope or SpaceTelescope.
            ValueError: If the telescope's code is empty, invalid, or does not match name.
        """
        check_type(item, (Telescope, SpaceTelescope), "Telescope")
        name = item.name
        code = item.get_code()
        if not name or not isinstance(name, str):
            raise ValueError("Telescope name must be a non-empty string")
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise ValueError(f"Telescope name '{name}' contains invalid characters...")
        if not code or not isinstance(code, str):
            raise ValueError("Telescope code must be a non-empty string")
        if not re.match(r'^[a-zA-Z0-9_-]+$', code):
            raise ValueError(f"Telescope code '{code}' contains invalid characters...")
        if name in self._items and self._items[name] is not item:
            raise ValueError(f"Telescope with name '{name}' already exists")
        logger.debug(f"Validated telescope with name='{name}', code='{code}'")

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
            name (str): Full name (set to code for consistency). Defaults to "Temporary Telescope".
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
            ValueError: If code is a duplicate, invalid, or other Telescope initialization errors occur.
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
        logger.info(f"Created and added telescope '{code}'")

    def activate_item(self, name: str) -> None:
        """Activate a specific telescope by its name.

        Triggers synchronization with a parent Observation if present.

        Args:
            name (str): The name of the telescope to activate.

        Raises:
            KeyError: If the name is not found in the collection.
        """
        super().activate_item(name)
        if hasattr(self, '_parent') and self._parent:
            self._parent._sync_scans_with_activation("telescopes", name, True)

    def deactivate_item(self, name: str) -> None:
        """Deactivate a specific telescope by its name.

        Triggers synchronization with a parent Observation if present.

        Args:
            name (str): The name of the telescope to deactivate.

        Raises:
            KeyError: If the name is not found in the collection.
        """
        super().deactivate_item(name)
        if hasattr(self, '_parent') and self._parent:
            self._parent._sync_scans_with_activation("telescopes", name, False)
    
    def copy(self) -> 'Telescopes':
        """Create a deep copy of the Telescopes object."""
        return Telescopes(
            items={name: item.copy() for name, item in self._items.items()},
            name=self.name,
            isactive=self.isactive,
            use_cache=self._use_cache
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Telescopes':
        """Create a Telescopes object from a dictionary."""
        items = {}
        for key, item_data in data.get("items", {}).items():
            try:
                telescope_type = item_data.get("type", "Telescope")
                if telescope_type == "SpaceTelescope":
                    telescope = SpaceTelescope.from_dict(item_data)
                else:
                    telescope = Telescope.from_dict(item_data)
                if telescope.name in items:
                    logger.error(f"Duplicate telescope name '{telescope.name}' found for key '{key}'")
                    raise ValueError(f"Telescope with name '{telescope.name}' already exists")
                items[telescope.name] = telescope
                logger.debug(f"Deserialized telescope with name='{telescope.name}', code='{telescope.code}' for key='{key}'")
            except Exception as e:
                logger.error(f"Failed to deserialize telescope for key '{key}': {str(e)}")
                raise ValueError(f"Invalid telescope data for key '{key}': {str(e)}") from e

        return cls(
            items=items,
            name=data.get("name", f"tlscs_{uuid.uuid4().hex[:32]}"),
            isactive=data.get("isactive", True),
            use_cache=data.get("use_cache", False)
        )