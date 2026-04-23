# base/telescope.py
from copy import deepcopy
from pastrocore.base.baseentityn import BaseEntityN
from msb_arch.utils.validation import check_type, check_positive
from msb_arch.utils.logging_setup import logger
import numpy as np
from typing import Optional, Dict, Tuple, Any
from enum import Enum
import uuid

# Constants
SPEED_OF_LIGHT = 3e8  # m/s
BOLTZMANN_CONSTANT = 1.380649e-23  # J/K

class MountType(Enum):
    EQUATORIAL = "EQUA"
    AZIMUTHAL = "AZIM"
    SPACE = "NONE"

class Telescope(BaseEntityN):
    """Class representing a ground-based telescope with ITRF coordinates, velocities, and SEFD properties."""
    code: str
    name: str
    type: str
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    diameter: float
    sefd_table: Dict[float, float]
    elevation_range: Tuple[float, float]
    azimuth_range: Tuple[float, float]
    mount_type: MountType
    surface_accuracy: Optional[float]
    surface_efficiency_table: Dict[float, float]
    effective_area_table: Dict[float, float]
    system_temperature_table: Dict[float, float]

    def __init__(self, *, code: str = "TT", name: str = "TEMPTELESCOPE", type = "Telescope",
                 x: float = 0.0, y: float = 0.0, z: float = 0.0,
                 vx: float = 0.0, vy: float = 0.0, vz: float = 0.0,
                 diameter: float = 1.0, sefd_table: Optional[Dict[float, float]] = None,
                 elevation_range: Tuple[float, float] = (15.0, 90.0),
                 azimuth_range: Tuple[float, float] = (0.0, 360.0),
                 mount_type: str = "AZIM", isactive: bool = True,
                 surface_accuracy: Optional[float] = None,
                 surface_efficiency_table: Optional[Dict[float, float]] = None,
                 effective_area_table: Optional[Dict[float, float]] = None,
                 system_temperature_table: Optional[Dict[float, float]] = None):
        """Initialize a Telescope with ITRF coordinates, velocities, and optional SEFD properties."""
        if name is None:
            name = f"tlsc_{uuid.uuid4().hex[:32]}"
        if elevation_range[0] > elevation_range[1]:
            raise ValueError("elevation_range min must be less than max")
        
        if azimuth_range[0] > azimuth_range[1]:
            raise ValueError("azimuth_range min must be less than max")
        
        if diameter <= 0:
            raise ValueError("Diameter must be positive")
        
        if isinstance(mount_type, str):
            try:
                mount_type = MountType(mount_type.upper())
            except ValueError:
                raise ValueError(f"Invalid mount_type: {mount_type}")
        elif not isinstance(mount_type, MountType):
            raise TypeError("mount_type must be a string or MountType")
        
        sefd_table = sefd_table if sefd_table is not None else {}
        surface_efficiency_table = surface_efficiency_table if surface_efficiency_table is not None else {}
        effective_area_table = effective_area_table if effective_area_table is not None else {}
        system_temperature_table = system_temperature_table if system_temperature_table is not None else {}
        
        super().__init__(name=name, isactive=isactive,
                         code=code, type=type, x=x, y=y, z=z, vx=vx, vy=vy, vz=vz,
                         diameter=diameter, sefd_table=sefd_table,
                         elevation_range=elevation_range, azimuth_range=azimuth_range,
                         mount_type=mount_type, surface_accuracy=surface_accuracy,
                         surface_efficiency_table=surface_efficiency_table,
                         effective_area_table=effective_area_table,
                         system_temperature_table=system_temperature_table)
        logger.debug(f"Initialized Telescope '{code}' at ({x}, {y}, {z}) m, diameter={diameter} m")

    def set(self, params: Dict[str, Any]) -> None:
        """Set entity attributes from a dictionary with type validation, handling mount_type."""
        processed_params = params.copy()
        if "mount_type" in processed_params:
            mount_type = processed_params["mount_type"]
            if isinstance(mount_type, str):
                try:
                    processed_params["mount_type"] = MountType(mount_type.upper())
                except ValueError:
                    raise ValueError(f"Invalid mount_type: {mount_type}")
            elif not isinstance(mount_type, MountType):
                raise TypeError("mount_type must be a string or MountType")
        super().set(processed_params)

    def add_sefd(self, frequency: float, sefd: float) -> None:
        """Add an SEFD value for a specific frequency to the SEFD table."""
        check_type(frequency, (int, float), "Frequency")
        check_positive(sefd, "SEFD")
        self._check_sefd(frequency, sefd)
        self.sefd_table[frequency] = sefd
        logger.debug(f"Added SEFD={sefd} Jy for frequency {frequency} MHz to '{self.code}'")

    def remove_sefd(self, frequency: float) -> None:
        """Remove an SEFD value for a specific frequency from the SEFD table."""
        check_type(frequency, (int, float), "Frequency")
        if frequency in self.sefd_table:
            self.sefd_table.pop(frequency)
            logger.debug(f"Removed SEFD for frequency {frequency} MHz from '{self.code}'")
    
    def get_code(self) -> str:
        """Return the telescope's code.

        Returns:
            str: The unique code of the telescope.
        """
        return self.code
    
    def get_coordinates(self) -> Tuple[float, float, float]:
        """Return the telescope's ITRF coordinates.

        Returns:
            Tuple[float, float, float]: The (x, y, z) coordinates in meters.
        """
        return (self.x, self.y, self.z)
    
    def get_velocities(self) -> Tuple[float, float, float]:
        """Return the telescope's ITRF velocities.

        Returns:
            Tuple[float, float, float]: The (vx, vy, vz) velocities in meters.
        """
        return (self.vx, self.vy, self.vz)
    
    def get_elevation_range(self) -> Tuple[float,float]:
        """Return the telescope's elevation range.

        Returns:
            Tuple[float, float]: The minimum and maximum elevation angles in degrees.
        """
        return self.elevation_range
    
    def get_azimuth_range(self) -> Tuple[float,float]:
        """Return the telescope's azimuth range.
        
        Returns:
            Tuple[float, float]: The minimum and maximum azimuth angles in degrees.
        """
        return self.azimuth_range
        
    def get_sefd(self, frequency: float) -> Optional[float]:
        """Retrieve the SEFD for a given frequency, with linear interpolation if needed."""
        check_type(frequency, (int, float), "Frequency")
        if not self.sefd_table:
            return None
        freqs = sorted(self.sefd_table.keys())
        if frequency in self.sefd_table:
            return self.sefd_table[frequency]
        if len(freqs) == 1:
            logger.debug(f"Only one SEFD point at {freqs[0]} MHz, using it for {frequency} MHz")
            return self.sefd_table[freqs[0]]
        if frequency < freqs[0] or frequency > freqs[-1]:
            return None
        for i in range(len(freqs) - 1):
            if freqs[i] <= frequency <= freqs[i + 1]:
                f1, f2 = freqs[i], freqs[i + 1]
                s1, s2 = self.sefd_table[f1], self.sefd_table[f2]
                interpolated_sefd = s1 + (s2 - s1) * (frequency - f1) / (f2 - f1)
                return interpolated_sefd
        return None

    def get_surface_efficiency(self, frequency: float) -> Optional[float]:
        """Retrieve the surface efficiency for a given frequency, with linear interpolation."""
        check_type(frequency, (int, float), "Frequency")
        if not self.surface_efficiency_table:
            return None
        freqs = sorted(self.surface_efficiency_table.keys())
        if frequency in self.surface_efficiency_table:
            return self.surface_efficiency_table[frequency]
        if frequency < freqs[0] or frequency > freqs[-1]:
            return None
        for i in range(len(freqs) - 1):
            if freqs[i] <= frequency <= freqs[i + 1]:
                f1, f2 = freqs[i], freqs[i + 1]
                e1, e2 = self.surface_efficiency_table[f1], self.surface_efficiency_table[f2]
                interpolated_eff = e1 + (e2 - e1) * (frequency - f1) / (f2 - f1)
                return interpolated_eff
        return None

    def get_effective_area(self, frequency: float) -> Optional[float]:
        """Retrieve the effective area for a given frequency, with linear interpolation."""
        check_type(frequency, (int, float), "Frequency")
        if not self.effective_area_table:
            return None
        freqs = sorted(self.effective_area_table.keys())
        if frequency in self.effective_area_table:
            return self.effective_area_table[frequency]
        if frequency < freqs[0] or frequency > freqs[-1]:
            return None
        for i in range(len(freqs) - 1):
            if freqs[i] <= frequency <= freqs[i + 1]:
                f1, f2 = freqs[i], freqs[i + 1]
                a1, a2 = self.effective_area_table[f1], self.effective_area_table[f2]
                interpolated_area = a1 + (a2 - a1) * (frequency - f1) / (f2 - f1)
                return interpolated_area
        return None

    def get_system_temperature(self, frequency: float) -> Optional[float]:
        """Retrieve the system temperature for a given frequency, with linear interpolation."""
        check_type(frequency, (int, float), "Frequency")
        if not self.system_temperature_table:
            return None
        freqs = sorted(self.system_temperature_table.keys())
        if frequency in self.system_temperature_table:
            return self.system_temperature_table[frequency]
        if frequency < freqs[0] or frequency > freqs[-1]:
            return None
        for i in range(len(freqs) - 1):
            if freqs[i] <= frequency <= freqs[i + 1]:
                f1, f2 = freqs[i], freqs[i + 1]
                t1, t2 = self.system_temperature_table[f1], self.system_temperature_table[f2]
                interpolated_tsys = t1 + (t2 - t1) * (frequency - f1) / (f2 - f1)
                return interpolated_tsys
        return None

    def clear_sefd_table(self) -> None:
        """Clear all entries from the SEFD table."""
        self.sefd_table.clear()
        logger.debug(f"Cleared SEFD table for '{self.code}'")

    def calculate_surface_efficiency(self, frequency: float) -> Optional[float]:
        """Calculate surface efficiency using Ruze formula and add to table."""
        check_type(frequency, (int, float), "Frequency")
        check_positive(frequency, "Frequency")
        
        if self.surface_accuracy is None:
            logger.warning(f"Cannot calculate surface efficiency for '{self.code}': surface accuracy not set")
            return None
        
        rms_m = self.surface_accuracy * 1e-6
        freq_hz = frequency * 1e6
        wavelength = SPEED_OF_LIGHT / freq_hz
        efficiency = np.exp(-(4 * np.pi * rms_m / wavelength) ** 2)
        
        self.surface_efficiency_table[frequency] = efficiency
        logger.debug(f"Calculated surface efficiency={efficiency:.4f} for frequency {frequency} MHz on '{self.code}'")
        return efficiency

    def calculate_effective_area(self, frequency: float) -> Optional[float]:
        """Calculate effective area and add to table."""
        check_type(frequency, (int, float), "Frequency")
        check_positive(frequency, "Frequency")
        
        geom_area = np.pi * (self.diameter / 2) ** 2
        
        efficiency = self.surface_efficiency_table.get(frequency)
        if efficiency is None:
            efficiency = self.calculate_surface_efficiency(frequency)
            if efficiency is None:
                return None
        
        area = geom_area * efficiency
        self.effective_area_table[frequency] = area
        logger.debug(f"Calculated effective area={area:.2f} m² for frequency {frequency} MHz on '{self.code}'")
        return area

    def calculate_sefd(self, frequency: float) -> Optional[float]:
        """Calculate SEFD from effective area and system temperature, add to table."""
        check_type(frequency, (int, float), "Frequency")
        check_positive(frequency, "Frequency")
        
        tsys = self.system_temperature_table.get(frequency)
        if tsys is None:
            return None
        
        area = self.effective_area_table.get(frequency)
        if area is None:
            area = self.calculate_effective_area(frequency)
            if area is None:
                return None
        
        sefd = 2 * BOLTZMANN_CONSTANT * tsys / area
        self.sefd_table[frequency] = sefd
        logger.debug(f"Calculated SEFD={sefd:.2f} Jy for frequency {frequency} MHz on '{self.code}'")
        return sefd
    
    def copy(self) -> 'Telescope':
        """Create a deep copy of the Telescope object."""
        return Telescope(
            code=self.code,
            name=self.name,
            type=self.type,
            x=self.x,
            y=self.y,
            z=self.z,
            vx=self.vx,
            vy=self.vy,
            vz=self.vz,
            diameter=self.diameter,
            sefd_table=deepcopy(self.sefd_table),
            elevation_range=self.elevation_range,
            azimuth_range=self.azimuth_range,
            mount_type=self.mount_type,
            isactive=self.isactive,
            surface_accuracy=self.surface_accuracy,
            surface_efficiency_table=deepcopy(self.surface_efficiency_table),
            effective_area_table=deepcopy(self.effective_area_table),
            system_temperature_table=deepcopy(self.system_temperature_table)
        )
    
    def _check_sefd(self, frequency: float, sefd: float) -> bool:
        """Check if an SEFD value is a duplicate with a different value.

        Args:
            frequency (float): Frequency in MHz.
            sefd (float): SEFD value in Jy.

        Returns:
            bool: True if the frequency already exists with a different SEFD value, False otherwise.
        """
        if frequency in self.sefd_table and self.sefd_table[frequency] != sefd:
            logger.warning(f"Overwriting SEFD for frequency {frequency} MHz on '{self.code}': "
                           f"old={self.sefd_table[frequency]} Jy, new={sefd} Jy")
            return True
        return False

    def _check_surface_efficiency(self, frequency: float, efficiency: float) -> bool:
        """Check if a surface efficiency value is a duplicate with a different value."""
        if frequency in self.surface_efficiency_table and self.surface_efficiency_table[frequency] != efficiency:
            logger.warning(f"Overwriting surface efficiency for frequency {frequency} MHz on '{self.code}': "
                           f"old={self.surface_efficiency_table[frequency]}, new={efficiency}")
            return True
        return False

    def _check_effective_area(self, frequency: float, area: float) -> bool:
        """Check if an effective area value is a duplicate with a different value."""
        if frequency in self.effective_area_table and self.effective_area_table[frequency] != area:
            logger.warning(f"Overwriting effective area for frequency {frequency} MHz on '{self.code}': "
                           f"old={self.effective_area_table[frequency]} m², new={area} m²")
            return True
        return False

    def _check_system_temperature(self, frequency: float, tsys: float) -> bool:
        """Check if a system temperature value is a duplicate with a different value."""
        if frequency in self.system_temperature_table and self.system_temperature_table[frequency] != tsys:
            logger.warning(f"Overwriting system temperature for frequency {frequency} MHz on '{self.code}': "
                           f"old={self.system_temperature_table[frequency]} K, new={tsys} K")
            return True
        return False
    
    def to_dict(self) -> dict:
        """Convert the Telescope object to a dictionary for serialization."""
        data = super().to_dict()
        data.update({
            "mount_type": self.mount_type.value,
            "elevation_range": list(self.elevation_range),
            "azimuth_range": list(self.azimuth_range),
            "sefd_table": {str(k): v for k, v in self.sefd_table.items()},
            "surface_efficiency_table": {str(k): v for k, v in self.surface_efficiency_table.items()},
            "effective_area_table": {str(k): v for k, v in self.effective_area_table.items()},
            "system_temperature_table": {str(k): v for k, v in self.system_temperature_table.items()}
        })
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Telescope':
        """Create a Telescope object from a dictionary."""
        data = data.copy()
        for table in ["sefd_table", "surface_efficiency_table", "effective_area_table", "system_temperature_table"]:
            if table in data and isinstance(data[table], dict):
                data[table] = {float(k): v for k, v in data[table].items()}
        if "elevation_range" in data and isinstance(data["elevation_range"], (list, tuple)):
            data["elevation_range"] = tuple(data["elevation_range"])
        if "azimuth_range" in data and isinstance(data["azimuth_range"], (list, tuple)):
            data["azimuth_range"] = tuple(data["azimuth_range"])
        if "mount_type" in data and isinstance(data["mount_type"], str):
            try:
                data["mount_type"] = MountType(data["mount_type"].upper())
            except ValueError:
                raise ValueError(f"Invalid mount_type in data: {data['mount_type']}")
        
        data.setdefault("name", f"tlsc_{uuid.uuid4().hex[:32]}")
        data.setdefault("code", data["code"])
        data.setdefault("type", data["type"])
        data.setdefault("x", 0.0)
        data.setdefault("y", 0.0)
        data.setdefault("z", 0.0)
        data.setdefault("vx", 0.0)
        data.setdefault("vy", 0.0)
        data.setdefault("vz", 0.0)
        data.setdefault("diameter", 1.0)
        data.setdefault("sefd_table", {})
        data.setdefault("elevation_range", (15.0, 90.0))
        data.setdefault("azimuth_range", (0.0, 360.0))
        data.setdefault("mount_type", MountType.AZIMUTHAL)
        data.setdefault("isactive", True)
        data.setdefault("surface_accuracy", None)
        data.setdefault("surface_efficiency_table", {})
        data.setdefault("effective_area_table", {})
        data.setdefault("system_temperature_table", {})

        return cls(**data)

    def __repr__(self) -> str:
        """Return a string representation of the Telescope object."""
        return (f"Telescope(code='{self.code}', name='{self.name}', "
                f"x={self.x}, y={self.y}, z={self.z}, "
                f"diameter={self.diameter}, isactive={self.isactive})")