from copy import deepcopy
from .telescope import Telescope, MountType
from msb_arch.utils.logging_setup import logger
from typing import Optional, Dict, Tuple, Any
from astropy.time import Time
import os
import uuid

class SpaceTelescope(Telescope):
    """Class representing a space-based telescope with orbital parameters and SEFD properties.

    Inherits from Telescope, setting mount_type to 'NONE'. Stores orbit file path or Keplerian elements
    for position calculations, performed by ScheduleCalculator.
    """
    type: str
    orbit_file: str
    pitch_range: Tuple[float, float]
    yaw_range: Tuple[float, float]
    use_kep: bool
    kepler_elements: dict
    interpolation_method: str

    def __init__(self, *, code: str = "TS", name: str = "TEMPSPACETELESCOPE", type: str = "SpaceTelescope",
                 orbit_file: str = "dummy_orbit.oem", diameter: float = 1.0,
                 sefd_table: Optional[Dict[float, float]] = None,
                 pitch_range: Tuple[float, float] = (-90.0, 90.0),
                 yaw_range: Tuple[float, float] = (-180.0, 180.0),
                 isactive: bool = True, use_kep: bool = True,
                 kepler_elements: dict = None,
                 interpolation_method: str = "chebyshev",
                 surface_accuracy: Optional[float] = None,
                 surface_efficiency_table: Optional[Dict[float, float]] = None,
                 effective_area_table: Optional[Dict[float, float]] = None,
                 system_temperature_table: Optional[Dict[float, float]] = None):
        """Initialize a SpaceTelescope with orbital parameters and optional SEFD properties."""
        if name is None:
            name = f"stlsc_{uuid.uuid4().hex[:32]}"
        super().__init__(code=code, name=name, type=type, x=0.0, y=0.0, z=0.0, vx=0.0, vy=0.0, vz=0.0,
                        diameter=diameter, sefd_table=sefd_table or {}, mount_type="NONE",
                        elevation_range=(0.0, 0.0), azimuth_range=(0.0, 0.0), isactive=isactive,
                        surface_accuracy=surface_accuracy,
                        surface_efficiency_table=surface_efficiency_table or {},
                        effective_area_table=effective_area_table or {},
                        system_temperature_table=system_temperature_table or {})
        
        self.set({
            "orbit_file": orbit_file,
            "pitch_range": pitch_range,
            "yaw_range": yaw_range,
            "use_kep": use_kep,
            "kepler_elements": kepler_elements,
            "interpolation_method": interpolation_method
        })

        if use_kep and kepler_elements is not None:
            self._validate_kepler_elements(kepler_elements)
            logger.debug("Initialized SpaceTelescope '%s' with Keplerian elements, diameter=%s m", code, diameter)
        elif not use_kep and orbit_file and os.path.isfile(orbit_file):
            logger.debug("Initialized SpaceTelescope '%s' with orbit file '%s', diameter=%s m", code, orbit_file, diameter)
        else:
            logger.warning("Initialized SpaceTelescope '%s' without orbit data or Keplerian elements", code)
    
    def copy(self) -> 'SpaceTelescope':
        """Create a deep copy of the SpaceTelescope object, preserving all attributes."""
        return SpaceTelescope(
            code=self.code,
            name=self.name,
            type=self.type,
            orbit_file=self.orbit_file,
            diameter=self.diameter,
            sefd_table=deepcopy(self.sefd_table),
            pitch_range=self.pitch_range,
            yaw_range=self.yaw_range,
            isactive=self.isactive,
            use_kep=self.use_kep,
            kepler_elements=deepcopy(self.kepler_elements) if self.kepler_elements else None,
            interpolation_method=self.interpolation_method,
            surface_accuracy=self.surface_accuracy,
            surface_efficiency_table=deepcopy(self.surface_efficiency_table),
            effective_area_table=deepcopy(self.effective_area_table),
            system_temperature_table=deepcopy(self.system_temperature_table)
        )

    def _validate_type(self, key: str, value: Any, expected_type: Any) -> None:
        """Validate attribute types, with custom checks for SpaceTelescope attributes."""
        super()._validate_type(key, value, expected_type)
        if key == "orbit_file" and value is not None:
            if not isinstance(value, str):
                raise TypeError("Orbit file must be a string")
        elif key == "pitch_range" and value is not None:
            if not isinstance(value, tuple) or len(value) != 2:
                raise TypeError("Pitch range must be a tuple of two floats")
            min_p, max_p = value
            if not (-90 <= min_p <= max_p <= 90):
                raise ValueError("Pitch range must be within [-90, 90] with min <= max")
        elif key == "yaw_range" and value is not None:
            if not isinstance(value, tuple) or len(value) != 2:
                raise TypeError("Yaw range must be a tuple of two floats")
            min_y, max_y = value
            if not (-180 <= min_y <= max_y <= 180):
                raise ValueError("Yaw range must be within [-180, 180] with min <= max")
        elif key == "interpolation_method" and value is not None:
            valid_methods = {"linear", "chebyshev", "cubic_spline"}
            if value not in valid_methods:
                raise ValueError(f"Interpolation method must be one of {valid_methods}")

    def _validate_kepler_elements(self, kepler_elements: dict) -> None:
        """Validate Keplerian elements."""
        required_keys = {"a", "e", "i", "raan", "argp", "nu", "epoch", "mu"}
        if not isinstance(kepler_elements, dict) or not required_keys.issubset(kepler_elements):
            raise ValueError(f"Kepler elements must include: {required_keys}")
        if kepler_elements["a"] <= 0:
            raise ValueError("Semi-major axis must be positive")
        if not 0 <= kepler_elements["e"] < 1:
            raise ValueError("Eccentricity must be in [0, 1)")
        if not isinstance(kepler_elements["epoch"], Time):
            raise TypeError("Epoch must be an astropy Time object")
        if kepler_elements["mu"] <= 0:
            raise ValueError("Gravitational parameter must be positive")

    def get_orbit(self) -> Optional[str]:
        """Retrieve the orbit file path.

        Returns:
            Optional[str]: Path to the orbit file, or None if not set.
        """
        logger.debug("Retrieving orbit file for SpaceTelescope '%s': %s", self.code, self.orbit_file)
        return self.orbit_file

    def set_orbit(self, orbit_file: str) -> None:
        """Set the orbit file path.

        Args:
            orbit_file (str): Path to the orbit file.

        Raises:
            TypeError: If orbit_file is not a string.
            ValueError: If orbit_file is empty.
        """
        if not isinstance(orbit_file, str):
            raise TypeError("Orbit file must be a non-empty string")
        if not orbit_file.strip():
            raise ValueError("Orbit file path cannot be empty")
        self.orbit_file = orbit_file
        self.use_kep = False
        self.kepler_elements = None
        logger.info("Set orbit file to '%s' for SpaceTelescope '%s'", orbit_file, self.code)

    def get_pitch_range(self) -> Tuple[float, float]:
        """Retrieve the pitch range of the telescope."""
        logger.debug("Retrieving pitch range for SpaceTelescope '%s': %s", self.code, self.pitch_range)
        return self.pitch_range

    def get_yaw_range(self) -> Tuple[float, float]:
        """Retrieve the yaw range of the telescope."""
        logger.debug("Retrieving yaw range for SpaceTelescope '%s': %s", self.code, self.yaw_range)
        return self.yaw_range

    def set_interpolation_method(self, method: str) -> None:
        """Set the interpolation method for orbit data."""
        valid_methods = {"linear", "chebyshev", "cubic_spline"}
        if method not in valid_methods:
            raise ValueError(f"Interpolation method must be one of {valid_methods}")
        self.interpolation_method = method
        logger.debug("Set interpolation method to '%s' for SpaceTelescope '%s'", method, self.code)

    def set_keplerian(self, a: float, e: float, i: float, raan: float, argp: float, nu: float, epoch: Time, mu: float = 398600.4418e9) -> None:
        """Set Keplerian elements for orbit calculation."""
        kepler_elements = {
            "a": a, "e": e, "i": i, "raan": raan, "argp": argp, "nu": nu,
            "epoch": epoch, "mu": mu
        }
        self._validate_kepler_elements(kepler_elements)
        self.set({"kepler_elements": kepler_elements, "orbit_file": None, "use_kep": True})
        logger.debug("Set Keplerian elements for SpaceTelescope '%s'", self.code)

    @classmethod
    def from_dict(cls, data: dict) -> 'SpaceTelescope':
        """Create a SpaceTelescope from a dictionary, ignoring what the constructor derives.

        Args:
            data (dict): The serialized telescope.

        Returns:
            SpaceTelescope: The telescope.

        Notes:
            - A space telescope has no station geometry, no mount and no elevation limits: the
              constructor sets them and does not accept them. They are inherited fields all the
              same, so a file written before `to_dict` stopped emitting them still carries
              them, and every such project must keep opening. They are dropped here rather
              than rejected.
            - Without this, a project containing a space telescope could not be opened at all.
              The failure named `elevation_range`, which pointed at the field rather than at
              the rule.
        """
        derived = ("x", "y", "z", "vx", "vy", "vz",
                   "elevation_range", "azimuth_range", "mount_type")
        remaining = {key: value for key, value in data.items() if key not in derived}
        dropped = [key for key in data if key in derived]
        if dropped:
            logger.debug("Ignoring %s in saved SpaceTelescope '%s'; the constructor derives them",
                         dropped, data.get("code", "unknown"))
        return super().from_dict(remaining)

    def to_dict(self) -> dict:
        """Convert the SpaceTelescope object to a dictionary for serialization."""
        try:
            # A copy: on an object that caches, `to_dict` returns the cache itself, and
            # writing to it corrupts what every later call reports -- which MSB 1.9.0
            # turned from silent into a refusal.
            data = dict(super().to_dict())
            # A space telescope has no station geometry and no mount, so the constructor fixes
            # these rather than accepting them. Writing them out would produce a file whose
            # every key is a constructor argument except these -- which is exactly what
            # deserialization assumes, and why it used to fail on the first one it met.
            for key in ["x", "y", "z", "vx", "vy", "vz",
                        "elevation_range", "azimuth_range", "mount_type"]:
                data.pop(key, None)
            serialized_data = {
                "type": "SpaceTelescope",
                "orbit_file": self.orbit_file,
                "pitch_range": list(self.pitch_range),
                "yaw_range": list(self.yaw_range),
                "use_kep": self.use_kep,
                "kepler_elements": None if self.kepler_elements is None else {
                    "a": self.kepler_elements["a"],
                    "e": self.kepler_elements["e"],
                    "i": self.kepler_elements["i"],
                    "raan": self.kepler_elements["raan"],
                    "argp": self.kepler_elements["argp"],
                    "nu": self.kepler_elements["nu"],
                    "epoch": self.kepler_elements["epoch"].isot,
                    "mu": self.kepler_elements["mu"]
                },
                "interpolation_method": self.interpolation_method
            }
            data.update(serialized_data)
            return data
        except Exception as e:
            logger.error("Failed to serialize SpaceTelescope '%s': %s", self.code, str(e))
            raise ValueError(f"Serialization failed: {str(e)}")

