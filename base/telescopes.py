from base.base_entity import BaseEntity
from utils.validation import check_type, check_non_empty_string, check_positive, check_range
from utils.logging_setup import logger
import numpy as np
from scipy.interpolate import CubicSpline
from numpy.polynomial import chebyshev
from datetime import datetime
import re
from typing import Optional, Dict, Tuple
from enum import Enum

class MountType(Enum):
    EQUATORIAL = "EQUA"
    AZIMUTHAL = "AZIM"
    SPACE = 'NONE'

"""Base class of a Telescope object with code, name, coordinates (ITRF), velocities (ITRF), diameter, and additional parameters

    Notes:  All coordinates are stored in meters in ITRF
            Telescope name and short name (code) MUST be unique
    Contains:
    Atributes:
        code (str): Telescope short name
        name (str): Telescope name
        x (float): Telescope x coordinate (ITRF) in meters
        y (float): Telescope y coordinate (ITRF) in meters
        z (float): Telescope z coordinate (ITRF) in meters
        vx (float): Telescope vx velocity (ITRF) in m/s
        vy (float): Telescope vy velocity (ITRF) in m/s
        vz (float): Telescope vz velocity (ITRF) in m/s
        diameter (float): Antenna diameter in meters
        sefd_table (Dict[float, float], optional): SEFD table (frequency in MHz: SEFD in Jy)
        elevation_range (Tuple[float, float]): Min and max elevation in degrees (default: 15-90)
        azimuth_range (Tuple[float, float]): Min and max azimuth in degrees (default: 0-360)
        mount_type (str): Mount type ('EQUA' or 'AZIM' or 'NONE' (for SpaceTelescope), default: 'AZIM')
        isactive (bool): Whether the telescope is active (default: True)
        
    Methods:
        add_sefd
        insert_sefd
        remove_sefd

        activate
        deactivate

        get_name
        get_code
        get_coordinates
        get_velocities
        get_coordinates_and_velocities
        get_x
        get_y
        get_z
        get_vx
        get_vy
        get_vz
        get_diameter
        get_elevation_range
        get_azimuth_range
        get_mount_type
        get_sefd
        get_sefd_table
        
        set_telescope
        set_name
        set__code
        set_coordinates
        set_velocities
        set_coordinate_and_velocities
        set_x
        set_y
        set_z
        set_vx
        set_vy
        set_vz
        set_diameter
        set_elevation_range
        set_azimuth_range
        set_mount_type
        set_sefd
        set_sefd_table

        clear_sefd_table
        to_dict
        from_dict
        _check_sefd
        __init__
        __repr__
    """

class Telescope(BaseEntity):
    def __init__(self, code: str, name: str, x: float, y: float, z: float, 
                 vx: float, vy: float, vz: float, diameter: float,
                 sefd_table: Optional[Dict[float, float]] = None,
                 elevation_range: Tuple[float, float] = (15.0, 90.0),
                 azimuth_range: Tuple[float, float] = (0.0, 360.0),
                 mount_type: str = "AZIM",
                 isactive: bool = True):
        """Initialize a Telescope object with code, name, coordinates (ITRF), velocities (ITRF), diameter, and additional parameters

        Args:
            code (str): Telescope short name
            name (str): Telescope name
            x (float): Telescope x coordinate (ITRF) in meters
            y (float): Telescope y coordinate (ITRF) in meters
            z (float): Telescope z coordinate (ITRF) in meters
            vx (float): Telescope vx velocity (ITRF) in m/s
            vy (float): Telescope vy velocity (ITRF) in m/s
            vz (float): Telescope vz velocity (ITRF) in m/s
            diameter (float): Antenna diameter in meters
            sefd_table (Dict[float, float], optional): SEFD table (frequency in MHz: SEFD in Jy)
            elevation_range (Tuple[float, float]): Min and max elevation in degrees (default: 15-90)
            azimuth_range (Tuple[float, float]): Min and max azimuth in degrees (default: 0-360)
            mount_type (str): Mount type ('EQUA' or 'AZIM', default: 'AZIM')
            isactive (bool): Whether the telescope is active (default: True)
        """
        super().__init__(isactive)
        check_non_empty_string(code, "Code")
        check_non_empty_string(name, "Name")
        check_type(x, (int, float), "X coordinate")
        check_type(y, (int, float), "Y coordinate")
        check_type(z, (int, float), "Z coordinate")
        check_type(vx, (int, float), "VX velocity")
        check_type(vy, (int, float), "VY velocity")
        check_type(vz, (int, float), "VZ velocity")
        check_positive(diameter, "Diameter")
        if sefd_table is not None:
            check_type(sefd_table, dict, "SEFD table")
            for freq, sefd in sefd_table.items():
                check_type(freq, (int, float), "SEFD frequency")
                check_type(sefd, (int, float), "SEFD value")
        check_type(elevation_range, tuple, "Elevation range")
        check_range(elevation_range[0], 0, 90, "Min elevation")
        check_range(elevation_range[1], elevation_range[0], 90, "Max elevation")
        check_type(azimuth_range, tuple, "Azimuth range")
        check_range(azimuth_range[0], 0, 360, "Min azimuth")
        check_range(azimuth_range[1], azimuth_range[0], 360, "Max azimuth")
        if mount_type.upper() not in {mt.value for mt in MountType}:
            raise ValueError(f"Mount type must be one of {[mt.value for mt in MountType]}, got {mount_type}")

        self._code = code
        self._name = name
        self._x = x
        self._y = y
        self._z = z
        self._vx = vx
        self._vy = vy
        self._vz = vz
        self._diameter = diameter
        self._sefd_table = sefd_table if sefd_table is not None else {}
        self._elevation_range = elevation_range
        self._azimuth_range = azimuth_range
        self._mount_type = MountType(mount_type.upper())
        logger.info(f"Initialized Telescope '{code}' at ({x}, {y}, {z}) m, diameter={diameter} m")

    def add_sefd(self, frequency: float, sefd: float) -> None:
        """Add an SEFD value for a specific frequency to the table"""
        check_type(frequency, (int, float), "Frequency")
        check_positive(sefd, "SEFD")
        self._check_sefd(frequency, sefd)
        self._sefd_table[frequency] = sefd
        logger.info(f"Added SEFD={sefd} Jy for frequency {frequency} MHz to telescope '{self._code}'")
    
    def insert_sefd(self, frequency: float, sefd: float) -> None:
        """Insert an SEFD value for a specific frequency into the table"""
        check_type(frequency, (int, float), "Frequency")
        check_positive(sefd, "SEFD")
        self._check_sefd(frequency, sefd)  # Проверка на дубликат
        self._sefd_table[frequency] = sefd
        logger.info(f"Inserted SEFD={sefd} Jy for frequency {frequency} MHz into telescope '{self._code}'")
    
    def remove_sefd(self, frequency: float) -> None:
        """Remove an SEFD value for a specific frequency from the table"""
        check_type(frequency, (int, float), "Frequency")
        if frequency in self._sefd_table:
            removed_sefd = self._sefd_table.pop(frequency)
            logger.info(f"Removed SEFD={removed_sefd} Jy for frequency {frequency} MHz from telescope '{self._code}'")
        else:
            logger.warning(f"No SEFD value found for frequency {frequency} MHz in telescope '{self._code}'")

    def activate(self):
        """Activate telescope"""
        return super().activate()
    
    def deactivate(self):
        """Deactivate telescope"""
        return super().deactivate()

    def get_name(self) -> str:
        """Get telescope name"""
        return self._name

    def get_code(self) -> str:
        """Get telescope code"""
        return self._code

    def get_coordinates(self) -> tuple[float, float, float]:
        """Get telescope coordinates x, y, z in meters (ITRF)"""
        logger.debug(f"Retrieved coordinates ({self._x}, {self._y}, {self._z}) m for telescope '{self._code}'")
        return self._x, self._y, self._z
    
    def get_velocities(self) -> tuple[float, float, float]:
        """Get telescope velocities vx, vy, vz in m/s (ITRF)"""
        return self._vx, self._vy, self._vz
    
    def get_coordinates_and_velocities(self) -> tuple[float, float, float, float, float, float]:
        """Get telescope coordinates and velocities x, y, z, vx, vy, vz in m/s (ITRF)"""
        return self._x, self._y, self._z, self._vx, self._vy, self._vz
    
    def get_x(self) -> float:
        """Get telescope coordinate x in meters (ITRF)"""
        logger.debug(f"Retrieved coordinate X={self._x} m for telescope '{self._code}'")
        return self._x
    
    def get_y(self) -> float:
        """Get telescope coordinate y in meters (ITRF)"""
        logger.debug(f"Retrieved coordinate Y={self._y} m for telescope '{self._code}'")
        return self._y
    
    def get_z(self) -> tuple[float, float, float]:
        """Get telescope coordinate z in meters (ITRF)"""
        logger.debug(f"Retrieved coordinate Z={self._z} m for telescope '{self._code}'")
        return self._z
    
    def get_vx(self) -> float:
        """Get telescope velocity vx in meters (ITRF)"""
        logger.debug(f"Retrieved velocity Vx={self._x} m for telescope '{self._code}'")
        return self._vx
    
    def get_vy(self) -> float:
        """Get telescope velocity vy in meters (ITRF)"""
        logger.debug(f"Retrieved velocity Vy={self._y} m for telescope '{self._code}'")
        return self._vy
    
    def get_vz(self) -> tuple[float, float, float]:
        """Get telescope velocity vz in meters (ITRF)"""
        logger.debug(f"Retrieved velocit Vz={self._z} m for telescope '{self._code}'")
        return self._vz

    def get_diameter(self) -> float:
        """Get telescope diameter in meters"""
        return self._diameter

    def get_elevation_range(self) -> Tuple[float, float]:
        """Get elevation range in degrees"""
        return self._elevation_range

    def get_azimuth_range(self) -> Tuple[float, float]:
        """Get azimuth range in degrees"""
        return self._azimuth_range

    def get_mount_type(self) -> MountType:
        """Get mount type"""
        return self._mount_type

    def get_sefd(self, frequency: float) -> Optional[float]:
        """Get SEFD for a given frequency with interpolation if necessary"""
        check_type(frequency, (int, float), "Frequency")
        if not self._sefd_table:
            logger.debug(f"No SEFD data available for telescope '{self._code}'")
            return None
        freqs = sorted(self._sefd_table.keys())
        if frequency in self._sefd_table:
            return self._sefd_table[frequency]
        if frequency < freqs[0] or frequency > freqs[-1]:
            logger.debug(f"Frequency {frequency} MHz out of SEFD table range for '{self._code}'")
            return None
        for i in range(len(freqs) - 1):
            if freqs[i] <= frequency <= freqs[i + 1]:
                f1, f2 = freqs[i], freqs[i + 1]
                s1, s2 = self._sefd_table[f1], self._sefd_table[f2]
                interpolated_sefd = s1 + (s2 - s1) * (frequency - f1) / (f2 - f1)
                logger.debug(f"Interpolated SEFD={interpolated_sefd} Jy for frequency {frequency} MHz on '{self._code}'")
                return interpolated_sefd
        return None
    
    def get_sefd_table(self) -> Dict[float, float]:
        """Get the SEFD table (frequency in MHz: SEFD in Jy)"""
        logger.debug(f"Retrieved SEFD table {self._sefd_table} for telescope '{self._code}'")
        return self._sefd_table
    
    def set_telescope(self, code: str, name: str, x: float, y: float, z: float, 
                      vx: float, vy: float, vz: float, diameter: float,
                      sefd_table: Optional[Dict[float, float]] = None,
                      elevation_range: Tuple[float, float] = (15.0, 90.0),
                      azimuth_range: Tuple[float, float] = (0.0, 360.0),
                      mount_type: str = "AZIM",
                      isactive: bool = True) -> None:
        """Set Telescope values, including SEFD table"""
        check_non_empty_string(code, "Code")
        check_non_empty_string(name, "Name")
        check_type(x, (int, float), "X coordinate")
        check_type(y, (int, float), "Y coordinate")
        check_type(z, (int, float), "Z coordinate")
        check_type(vx, (int, float), "VX velocity")
        check_type(vy, (int, float), "VY velocity")
        check_type(vz, (int, float), "VZ velocity")
        check_positive(diameter, "Diameter")

        if sefd_table is not None:
            check_type(sefd_table, dict, "SEFD table")
            for freq, sefd in sefd_table.items():
                check_type(freq, (int, float), "SEFD frequency")
                check_type(sefd, (int, float), "SEFD value")

        check_type(elevation_range, tuple, "Elevation range")
        check_range(elevation_range[0], 0, 90, "Min elevation")
        check_range(elevation_range[1], elevation_range[0], 90, "Max elevation")
        check_type(azimuth_range, tuple, "Azimuth range")
        check_range(azimuth_range[0], 0, 360, "Min azimuth")
        check_range(azimuth_range[1], azimuth_range[0], 360, "Max azimuth")
        if mount_type.upper() not in {mt.value for mt in MountType}:
            raise ValueError(f"Mount type must be one of {[mt.value for mt in MountType]}, got {mount_type}")

        self._code = code
        self._name = name
        self._x = x
        self._y = y
        self._z = z
        self._vx = vx
        self._vy = vy
        self._vz = vz
        self._diameter = diameter
        self._sefd_table = sefd_table if sefd_table is not None else {}
        self._elevation_range = elevation_range
        self._azimuth_range = azimuth_range
        self._mount_type = MountType(mount_type.upper())
        self.isactive = isactive
        logger.info(f"Set telescope '{code}' with new parameters")
    
    def set_name(self, name: str) -> None:
        """Set telescope name."""
        check_non_empty_string(name, "Name")
        self._name = name
        logger.info(f"Set name '{name}' for telescope '{self._code}'")

    def set_code(self, code: str) -> None:
        """Set telescope code."""
        check_non_empty_string(code, "Code")
        self._code = code
        logger.info(f"Set code '{code}' for telescope with name '{self._name}'")
    
    def set_coordinates(self, coordinates: Tuple[float, float, float]) -> None:
        """Set telescope coordinates x, y, z in meters (ITRF)"""
        check_type(coordinates, tuple, "Coordinates")
        if len(coordinates) != 3:
            raise ValueError("Coordinates must contain exactly 3 values (x, y, z)")
        x, y, z = coordinates
        check_type(x, (int, float), "X coordinate")
        check_type(y, (int, float), "Y coordinate")
        check_type(z, (int, float), "Z coordinate")
        self._x, self._y, self._z = x, y, z
        logger.info(f"Set coordinates ({x}, {y}, {z}) m for telescope '{self._code}'")

    def set_velocities(self, velocities: Tuple[float, float, float]) -> None:
        """Set telescope velocities vx, vy, vz in m/s (ITRF)"""
        check_type(velocities, tuple, "Velocities")
        if len(velocities) != 3:
            raise ValueError("Velocities must contain exactly 3 values (vx, vy, vz)")
        vx, vy, vz = velocities
        check_type(vx, (int, float), "VX velocity")
        check_type(vy, (int, float), "VY velocity")
        check_type(vz, (int, float), "VZ velocity")
        self._vx, self._vy, self._vz = vx, vy, vz
        logger.info(f"Set velocities ({vx}, {vy}, {vz}) m/s for telescope '{self._code}'")
    
    def set_coordinates_and_velocities(self, coordinates: Tuple[float, float, float], 
                                      velocities: Tuple[float, float, float]) -> None:
        """Set telescope coordinates x, y, z in meters and velocities vx, vy, vz in m/s (ITRF)"""
        check_type(coordinates, tuple, "Coordinates")
        check_type(velocities, tuple, "Velocities")
        if len(coordinates) != 3:
            raise ValueError("Coordinates must contain exactly 3 values (x, y, z)")
        if len(velocities) != 3:
            raise ValueError("Velocities must contain exactly 3 values (vx, vy, vz)")
        x, y, z = coordinates
        vx, vy, vz = velocities
        check_type(x, (int, float), "X coordinate")
        check_type(y, (int, float), "Y coordinate")
        check_type(z, (int, float), "Z coordinate")
        check_type(vx, (int, float), "VX velocity")
        check_type(vy, (int, float), "VY velocity")
        check_type(vz, (int, float), "VZ velocity")
        self._x, self._y, self._z = x, y, z
        self._vx, self._vy, self._vz = vx, vy, vz
        logger.info(f"Set coordinates ({x}, {y}, {z}) m and velocities ({vx}, {vy}, {vz}) m/s for telescope '{self._code}'")

    def set_x(self, x: float) -> None:
        """Set telescope x coordinate in meters (ITRF)"""
        check_type(x, (int, float), "X coordinate")
        self._x = x
        logger.info(f"Set x={x} m for telescope '{self._code}'")

    def set_y(self, y: float) -> None:
        """Set telescope y coordinate in meters (ITRF)"""
        check_type(y, (int, float), "Y coordinate")
        self._y = y
        logger.info(f"Set y={y} m for telescope '{self._code}'")

    def set_z(self, z: float) -> None:
        """Set telescope z coordinate in meters (ITRF)"""
        check_type(z, (int, float), "Z coordinate")
        self._z = z
        logger.info(f"Set z={z} m for telescope '{self._code}'")
    
    def set_vx(self, vx: float) -> None:
        """Set telescope vx velocity in m/s (ITRF)"""
        check_type(vx, (int, float), "VX velocity")
        self._vx = vx
        logger.info(f"Set vx={vx} m/s for telescope '{self._code}'")

    def set_vy(self, vy: float) -> None:
        """Set telescope vy velocity in m/s (ITRF)"""
        check_type(vy, (int, float), "VY velocity")
        self._vy = vy
        logger.info(f"Set vy={vy} m/s for telescope '{self._code}'")

    def set_vz(self, vz: float) -> None:
        """Set telescope vz velocity in m/s (ITRF)"""
        check_type(vz, (int, float), "VZ velocity")
        self._vz = vz
        logger.info(f"Set vz={vz} m/s for telescope '{self._code}'")
    
    def set_diameter(self, diameter: float) -> None:
        """Set telescope diameter in meters"""
        check_positive(diameter, "Diameter")
        self._diameter = diameter
        logger.info(f"Set diameter={diameter} m for telescope '{self._code}'")
    
    def set_elevation_range(self, elevation_range: Tuple[float, float]) -> None:
        """Set elevation range in degrees"""
        check_type(elevation_range, tuple, "Elevation range")
        if len(elevation_range) != 2:
            raise ValueError("Elevation range must contain exactly 2 values (min, max)")
        min_el, max_el = elevation_range
        check_range(min_el, 0, 90, "Min elevation")
        check_range(max_el, min_el, 90, "Max elevation")
        self._elevation_range = (min_el, max_el)
        logger.info(f"Set elevation range={elevation_range} degrees for telescope '{self._code}'")
    
    def set_azimuth_range(self, azimuth_range: Tuple[float, float]) -> None:
        """Set azimuth range in degrees"""
        check_type(azimuth_range, tuple, "Azimuth range")
        if len(azimuth_range) != 2:
            raise ValueError("Azimuth range must contain exactly 2 values (min, max)")
        min_az, max_az = azimuth_range
        check_range(min_az, 0, 360, "Min azimuth")
        check_range(max_az, min_az, 360, "Max azimuth")
        self._azimuth_range = (min_az, max_az)
        logger.info(f"Set azimuth range={azimuth_range} degrees for telescope '{self._code}'")
    
    def set_mount_type(self, mount_type: str) -> None:
        """Set mount type ('EQUA', 'AZIM', or 'NONE')"""
        check_non_empty_string(mount_type, "Mount type")
        if mount_type.upper() not in {mt.value for mt in MountType}:
            raise ValueError(f"Mount type must be one of {[mt.value for mt in MountType]}, got {mount_type}")
        self._mount_type = MountType(mount_type.upper())
        logger.info(f"Set mount type='{self._mount_type.value}' for telescope '{self._code}'")
    
    def set_sefd(self, frequency: float, sefd: float) -> None:
        """Set SEFD for a specific frequency."""
        check_type(frequency, (int, float), "Frequency")
        check_positive(sefd, "SEFD")
        self._check_sefd(frequency, sefd)  # Проверка на дубликат
        self._sefd_table[frequency] = sefd
        logger.info(f"Set SEFD={sefd} Jy for frequency {frequency} MHz on telescope '{self._code}'")
    
    def set_sefd_table(self, sefd_table: Dict[float, float]) -> None:
        """Set the entire SEFD table (frequency in MHz: SEFD in Jy) -- overwrites existing table"""
        check_type(sefd_table, dict, "SEFD table")
        for freq, sefd in sefd_table.items():
            check_type(freq, (int, float), "SEFD frequency")
            check_positive(sefd, "SEFD value")
        self._sefd_table = sefd_table.copy()
        logger.info(f"Set SEFD table with {len(sefd_table)} entries for telescope '{self._code}'")
    
    def clear_sefd_table(self) -> None:
        """Clear the SEFD table"""
        self._sefd_table.clear()
        logger.info(f"Cleared SEFD table for telescope '{self._code}'")

    def to_dict(self) -> dict:
        """Convert Telescope object to a dictionary for serialization"""
        logger.info(f"Converted telescope '{self._code}' to dictionary")
        return {
            "type": "Telescope",
            "code": self._code,
            "name": self._name,
            "x": self._x,
            "y": self._y,
            "z": self._z,
            "vx": self._vx,
            "vy": self._vy,
            "vz": self._vz,
            "diameter": self._diameter,
            "sefd_table": self._sefd_table,
            "elevation_range": self._elevation_range,
            "azimuth_range": self._azimuth_range,
            "mount_type": self._mount_type.value,
            "isactive": self.isactive
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Telescope':
        """Create a Telescope object from a dictionary"""
        sefd_table = data.get("sefd_table", {})
        if sefd_table:
            sefd_table = {float(freq): float(flux) for freq, flux in sefd_table.items()}

        logger.info(f"Created telescope '{data['code']}' from dictionary")
        return cls(
            code=data["code"],
            name=data["name"],
            x=data["x"],
            y=data["y"],
            z=data["z"],
            vx=data["vx"],
            vy=data["vy"],
            vz=data["vz"],
            diameter=data["diameter"],
            sefd_table=sefd_table,
            elevation_range=tuple(data.get("elevation_range", (15.0, 90.0))),
            azimuth_range=tuple(data.get("azimuth_range", (0.0, 360.0))),
            mount_type=data.get("mount_type", "AZIM"),
            isactive=data.get("isactive", True)
        )
    
    def _check_sefd(self, frequency: float, sefd: float) -> bool:
        """Check if the SEFD value for the given frequency is a duplicate with a different value"""
        if frequency in self._sefd_table:
            current_sefd = self._sefd_table[frequency]
            if current_sefd != sefd:
                logger.warning(f"Overwriting SEFD for frequency {frequency} MHz on telescope '{self._code}': "
                               f"old value={current_sefd} Jy, new value={sefd} Jy")
                return True
        return False

    def __repr__(self) -> str:
        """Return a string representation of Telescope."""
        return (f"Telescope(code='{self._code}', name='{self._name}', "
                f"x={self._x}, y={self._y}, z={self._z}, "
                f"vx={self._vx}, vy={self._vy}, vz={self._vz}, "
                f"diameter={self._diameter}, sefd_table={self._sefd_table}, "
                f"elevation_range={self._elevation_range}, azimuth_range={self._azimuth_range}, "
                f"mount_type={self._mount_type.value}, isactive={self.isactive})")


"""Base classe of a SpaceTelescope object with code, name, orbit file, diameter, and additional parameters.

    Contains:
    Atributes:
        code (str): Telescope short name
        name (str): Telescope name
        orbit_file (str): Path to the orbit file (coordinates in km, velocities in km/s)
        diameter (float): Antenna diameter in meters
        sefd_table (Dict[float, float], optional): SEFD table (frequency in MHz: SEFD in Jy)
        pitch_range (Tuple[float, float]): Min and max pitch in degrees (default: -90 to 90)
        yaw_range (Tuple[float, float]): Min and max yaw in degrees (default: -180 to 180)
        isactive (bool): Whether the telescope is active (default: True)
        keplerian (bool): Whether to use keplerian elements of orbit file (default: True -- will use keplerian)
    
    Methods:
        inherits basic methods from Telescope

    Additional Methods:
        load_orbit

        interpolate_orbit_chebyshev
        interpolate_orbit_cubic_spline

        get_state_vector_from_orbit
        get_state_vector_from_kepler

        get_keplerian
        get_pitch_range
        get_yaw_range
        get_use_kep

        set_space_telescope
        set_keplerian
        set_pitch_range
        set_yaw_range
        set_use_kep

        to_dict
        from_dict

        _solve_kepler
        _validate_orbit_data

        __init__
        __repr__

    """

class SpaceTelescope(Telescope):
    def __init__(self, code: str, name: str, orbit_file: str, diameter: float,
                 sefd_table: Optional[Dict[float, float]] = None,
                 pitch_range: Tuple[float, float] = (-90.0, 90.0),
                 yaw_range: Tuple[float, float] = (-180.0, 180.0),
                 isactive: bool = True,
                 use_kep: bool = True,
                 kepler_elements: Optional[dict] = None):
        """Initialize a SpaceTelescope object with code, name, orbit file, diameter, and additional parameters

        Args:
            code (str): Telescope short name
            name (str): Telescope name
            orbit_file (str): Path to the orbit file (coordinates in km, velocities in km/s)
            diameter (float): Antenna diameter in meters
            sefd_table (Dict[float, float], optional): SEFD table (frequency in MHz: SEFD in Jy)
            pitch_range (Tuple[float, float]): Min and max pitch in degrees (default: -90 to 90)
            yaw_range (Tuple[float, float]): Min and max yaw in degrees (default: -180 to 180)
            isactive (bool): Whether the telescope is active (default: True)
            use_kep (bool): Whether to use Keplerian elements (True) or orbit file (False) (default: True)
            kepler_elements (dict, optional): Keplerian elements dictionary with keys: a, e, i, raan, argp, nu, epoch, mu
        """
        super().__init__(code, name, 0, 0, 0, 0, 0, 0, diameter, sefd_table=sefd_table, isactive=isactive)
        check_non_empty_string(orbit_file, "Orbit file")
        check_positive(diameter, "Diameter")
        check_type(pitch_range, tuple, "Pitch range")
        check_range(pitch_range[0], -90, 90, "Min pitch")
        check_range(pitch_range[1], pitch_range[0], 90, "Max pitch")
        check_type(yaw_range, tuple, "Yaw range")
        check_range(yaw_range[0], -180, 180, "Min yaw")
        check_range(yaw_range[1], yaw_range[0], 180, "Max yaw")
        check_type(use_kep, bool, "Use Keplerian flag")

        self._orbit_file = orbit_file
        self._pitch_range = pitch_range
        self._yaw_range = yaw_range
        self._use_kep = use_kep
        self._orbit_data = None
        self._kepler_elements = None

        if self._use_kep:
            if kepler_elements is not None:
                required_keys = {"a", "e", "i", "raan", "argp", "nu", "epoch", "mu"}
                if not isinstance(kepler_elements, dict) or not required_keys.issubset(kepler_elements.keys()):
                    raise ValueError("kepler_elements must be a dict with keys: a, e, i, raan, argp, nu, epoch, mu")
                check_positive(kepler_elements["a"], "Semi-major axis")
                check_range(kepler_elements["e"], 0, 1, "Eccentricity")
                check_type(kepler_elements["i"], (int, float), "Inclination")
                check_type(kepler_elements["raan"], (int, float), "RAAN")
                check_type(kepler_elements["argp"], (int, float), "Argument of periapsis")
                check_type(kepler_elements["nu"], (int, float), "True anomaly")
                check_type(kepler_elements["epoch"], datetime, "Epoch")
                check_positive(kepler_elements["mu"], "Gravitational parameter")
                self._kepler_elements = kepler_elements.copy()
            else:
                logger.warning(f"Initialized SpaceTelescope '{code}' with use_kep=True but no kepler_elements provided")
            self._orbit_data = None  # Сбрасываем орбитальные данные, если используем Kepler
        else:
            if orbit_file:
                self.load_orbit(orbit_file)
                logger.info(f"Initialized SpaceTelescope '{code}' with orbit file '{orbit_file}', diameter={diameter} m")
            else:
                logger.warning(f"Initialized SpaceTelescope '{code}' with use_kep=False but no orbit_file provided")
            self._kepler_elements = None  # Сбрасываем Kepler, если используем orbit_file

    def load_orbit(self, orbit_file: str) -> None:
        """Load orbit data from a CCSDS OEM 2.0 file into memory"""
        check_non_empty_string(orbit_file, "Orbit file")
        times, positions, velocities = [], [], []
        try:
            with open(orbit_file, 'r') as f:
                lines = f.readlines()
                data_section = False
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if line.startswith("META_STOP"):
                        data_section = True
                        continue
                    if line.startswith("COVARIANCE_START"):
                        break
                    if not data_section:
                        continue
                    parts = re.split(r'\s+', line)
                    if len(parts) != 7:
                        continue
                    time_str = parts[0]
                    time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%f")
                    j2000_epoch = datetime(2000, 1, 1, 12, 0, 0)
                    time_sec = (time - j2000_epoch).total_seconds()
                    x, y, z = map(float, parts[1:4])  # km -> m
                    vx, vy, vz = map(float, parts[4:7])  # km/s -> m/s
                    times.append(time_sec)
                    positions.append([x * 1000, y * 1000, z * 1000])
                    velocities.append([vx * 1000, vy * 1000, vz * 1000])
        except FileNotFoundError:
            logger.error(f"Orbit file '{orbit_file}' not found")
            raise FileNotFoundError(f"Orbit file '{orbit_file}' not found!")
        except ValueError as e:
            logger.error(f"Error parsing orbit file: {str(e)}")
            raise ValueError(f"Error parsing orbit file: {e}")
        if len(times) < 2:
            logger.error(f"Orbit file '{orbit_file}' contains insufficient data points ({len(times)} < 2)")
            raise ValueError(f"Orbit file must contain at least 2 data points, got {len(times)}")
        self._orbit_data = {
            "times": np.array(times),
            "positions": np.array(positions),
            "velocities": np.array(velocities)
        }
        self._orbit_file = orbit_file
        logger.info(f"Loaded orbit data from '{orbit_file}' into memory for SpaceTelescope '{self._code}'")

    def interpolate_orbit_chebyshev(self, degree: int = 5) -> None:
        """Interpolate orbit data using Chebyshev polynomials"""
        if self._orbit_data is None:
            logger.error(f"No orbit data loaded for '{self._code}'")
            raise ValueError("No orbit data loaded!")
        times = self._orbit_data["times"]
        t_min, t_max = min(times), max(times)
        norm_times = 2 * (times - t_min) / (t_max - t_min) - 1  # Нормализация к [-1, 1]
        positions = self._orbit_data["positions"]
        velocities = self._orbit_data["velocities"]
        self._chebyshev_coeffs = {
            "time_range": (t_min, t_max),
            "positions": [chebyshev.Chebyshev.fit(norm_times, pos, degree) for pos in positions.T],
            "velocities": [chebyshev.Chebyshev.fit(norm_times, vel, degree) for vel in velocities.T]
        }
        logger.info(f"Interpolated orbit for '{self._code}' using Chebyshev polynomials (degree={degree})")

    def interpolate_orbit_cubic_spline(self) -> None:
        """Interpolate orbit data using cubic splines"""
        if self._orbit_data is None:
            logger.error(f"No orbit data loaded for '{self._code}'")
            raise ValueError("No orbit data loaded!")
        times = self._orbit_data["times"]
        positions = self._orbit_data["positions"]
        velocities = self._orbit_data["velocities"]
        self._cubic_splines = {
            "time_range": (min(times), max(times)),
            "positions": [CubicSpline(times, pos) for pos in positions.T],
            "velocities": [CubicSpline(times, vel) for vel in velocities.T]
        }
        logger.info(f"Interpolated orbit for '{self._code}' using cubic splines")

    def get_state_vector_from_kepler(self, dt: datetime) -> tuple[np.ndarray, np.ndarray]:
        """Get position and velocity from Keplerian elements at a given time"""
        if self._kepler_elements is None:
            logger.error(f"No Keplerian elements set for '{self._code}'")
            raise ValueError("No Keplerian elements set!")
        a, e, i, raan, argp, nu0, epoch, mu = (
            self._kepler_elements[k] for k in ["a", "e", "i", "raan", "argp", "nu", "epoch", "mu"]
        )
        t = (dt - epoch).total_seconds()
        M = np.sqrt(mu / a**3) * t + self._solve_kepler(nu0, e)  # Mean anomaly
        E = self._solve_kepler(M, e)  # Eccentric anomaly
        nu = 2 * np.arctan2(np.sqrt(1 + e) * np.sin(E / 2), np.sqrt(1 - e) * np.cos(E / 2))  # True anomaly
        r = a * (1 - e * np.cos(E))  # Distance
        p = a * (1 - e**2)  # Semi-latus rectum
        h = np.sqrt(mu * p)  # Angular momentum
        # Position and velocity in perifocal frame
        pos_p = np.array([r * np.cos(nu), r * np.sin(nu), 0])
        vel_p = np.array([-np.sin(nu), e + np.cos(nu), 0]) * (h / p)
        # Rotation matrices
        R1 = np.array([[np.cos(raan), -np.sin(raan), 0], [np.sin(raan), np.cos(raan), 0], [0, 0, 1]])
        R2 = np.array([[1, 0, 0], [0, np.cos(i), -np.sin(i)], [0, np.sin(i), np.cos(i)]])
        R3 = np.array([[np.cos(argp), -np.sin(argp), 0], [np.sin(argp), np.cos(argp), 0], [0, 0, 1]])
        R = R1 @ R2 @ R3
        pos = R @ pos_p
        vel = R @ vel_p
        logger.debug(f"Calculated position={pos}, velocity={vel} for '{self._code}' at {dt}")
        return pos, vel

    def get_state_vector_from_orbit(self, dt: datetime) -> tuple[np.ndarray, np.ndarray]:
        """Get position and velocity at a given time"""
        if not self._validate_orbit_data():
            logger.error(f"No orbit data or Kepler elements defined for '{self._code}'")
            raise ValueError("No orbit data or Kepler elements available! Define orbit file or Kepler elements first.")
        t = (dt - datetime(2000, 1, 1, 12, 0, 0)).total_seconds()
        if self._kepler_elements:
            return self.get_position_velocity_from_kepler(dt)
        times = self._orbit_data["times"]
        if t < times[0] or t > times[-1]:
            logger.debug(f"Time {t} outside orbit data range for '{self._code}'")
            return np.array([self._x, self._y, self._z]), np.array([self._vx, self._vy, self._vz])
        if hasattr(self, "_cubic_splines") and self._cubic_splines:
            pos = np.array([spline(t) for spline in self._cubic_splines["positions"]])
            vel = np.array([spline(t, 1) for spline in self._cubic_splines["velocities"]])
        elif hasattr(self, "_chebyshev_coeffs") and self._chebyshev_coeffs:
            t_min, t_max = self._chebyshev_coeffs["time_range"]
            norm_t = 2 * (t - t_min) / (t_max - t_min) - 1
            pos = np.array([coeff(norm_t) for coeff in self._chebyshev_coeffs["positions"]])
            vel = np.array([coeff.deriv()(norm_t) for coeff in self._chebyshev_coeffs["velocities"]])
        else:
            pos_idx = np.searchsorted(times, t)
            t1, t2 = times[pos_idx - 1], times[pos_idx]
            pos1, pos2 = self._orbit_data["positions"][pos_idx - 1], self._orbit_data["positions"][pos_idx]
            vel1, vel2 = self._orbit_data["velocities"][pos_idx - 1], self._orbit_data["velocities"][pos_idx]
            frac = (t - t1) / (t2 - t1)
            pos = pos1 + (pos2 - pos1) * frac
            vel = vel1 + (vel2 - vel1) * frac
            logger.warning(f"Using linear interpolation for position and velocity at time {t} for '{self._code}' (consider using splines or Chebyshev)")
        logger.debug(f"Retrieved position={pos}, velocity={vel} for '{self._code}' at {dt}")
        return pos, vel
    
    def get_keplerian(self) -> Optional[Dict[str, any]]:
        """Get the Keplerian elements of the SpaceTelescope

        Returns:
            Optional[Dict[str, any]]: Dictionary of Keplerian elements (a, e, i, raan, argp, nu, epoch, mu) if set, None otherwise
        """
        if self._kepler_elements is not None:
            logger.debug(f"Retrieved Keplerian elements for SpaceTelescope '{self._code}': {self._kepler_elements}")
            return self._kepler_elements.copy()
        logger.debug(f"No Keplerian elements set for SpaceTelescope '{self._code}'")
        return None

    def get_pitch_range(self) -> Tuple[float, float]:
        """Get pitch range in degrees"""
        return self._pitch_range

    def get_yaw_range(self) -> Tuple[float, float]:
        """Get yaw range in degrees"""
        return self._yaw_range
    
    def get_use_kep(self) -> bool:
        """Get whether Keplerian elements are used for orbit calculations

        Returns:
            bool: True if Keplerian elements are used, False if orbit file data is used
        """
        logger.debug(f"Retrieved use_keplerian={self._use_kep} for SpaceTelescope '{self._code}'")
        return self._use_kep
    
    def set_space_telescope(self, code: str, name: str, orbit_file: str, diameter: float,
                           sefd_table: Optional[Dict[float, float]] = None,
                           pitch_range: Tuple[float, float] = (-90.0, 90.0),
                           yaw_range: Tuple[float, float] = (-180.0, 180.0),
                           isactive: bool = True,
                           use_kep: bool = True,
                           kepler_elements: Optional[dict] = None) -> None:
        """Set SpaceTelescope parameters, choosing between orbit file or Keplerian elements based on use_kep

        Args:
            code (str): Telescope short name
            name (str): Telescope name
            orbit_file (str): Path to the orbit file (coordinates in km, velocities in km/s)
            diameter (float): Antenna diameter in meters
            sefd_table (Dict[float, float], optional): SEFD table (frequency in MHz: SEFD in Jy)
            pitch_range (Tuple[float, float]): Min and max pitch in degrees (default: -90 to 90)
            yaw_range (Tuple[float, float]): Min and max yaw in degrees (default: -180 to 180)
            isactive (bool): Whether the telescope is active (default: True)
            use_kep (bool): Whether to use Keplerian elements (True) or orbit file (False) (default: True)
            kepler_elements (dict, optional): Keplerian elements dictionary with keys: a, e, i, raan, argp, nu, epoch, mu
        """
        check_non_empty_string(code, "Code")
        check_non_empty_string(name, "Name")
        check_non_empty_string(orbit_file, "Orbit file")
        check_positive(diameter, "Diameter")
        if sefd_table is not None:
            check_type(sefd_table, dict, "SEFD table")
            for freq, sefd in sefd_table.items():
                check_type(freq, (int, float), "SEFD frequency")
                check_type(sefd, (int, float), "SEFD value")
        check_type(pitch_range, tuple, "Pitch range")
        check_range(pitch_range[0], -90, 90, "Min pitch")
        check_range(pitch_range[1], pitch_range[0], 90, "Max pitch")
        check_type(yaw_range, tuple, "Yaw range")
        check_range(yaw_range[0], -180, 180, "Min yaw")
        check_range(yaw_range[1], yaw_range[0], 180, "Max yaw")
        check_type(use_kep, bool, "Use Keplerian flag")

        self._code = code
        self._name = name
        self._orbit_file = orbit_file
        self._diameter = diameter
        self._sefd_table = sefd_table if sefd_table is not None else {}
        self._pitch_range = pitch_range
        self._yaw_range = yaw_range
        self._use_kep = use_kep
        self.isactive = isactive

        if self._use_kep:
            if kepler_elements is not None:
                required_keys = {"a", "e", "i", "raan", "argp", "nu", "epoch", "mu"}
                if not isinstance(kepler_elements, dict) or not required_keys.issubset(kepler_elements.keys()):
                    raise ValueError("kepler_elements must be a dict with keys: a, e, i, raan, argp, nu, epoch, mu")
                check_positive(kepler_elements["a"], "Semi-major axis")
                check_range(kepler_elements["e"], 0, 1, "Eccentricity")
                check_type(kepler_elements["i"], (int, float), "Inclination")
                check_type(kepler_elements["raan"], (int, float), "RAAN")
                check_type(kepler_elements["argp"], (int, float), "Argument of periapsis")
                check_type(kepler_elements["nu"], (int, float), "True anomaly")
                check_type(kepler_elements["epoch"], datetime, "Epoch")
                check_positive(kepler_elements["mu"], "Gravitational parameter")
                self._kepler_elements = kepler_elements.copy()
            else:
                logger.warning(f"Set SpaceTelescope '{code}' with use_kep=True but no kepler_elements provided")
            self._orbit_data = None
        else:
            if orbit_file:
                self.load_orbit(orbit_file)
            else:
                logger.warning(f"Set SpaceTelescope '{code}' with use_kep=False but no orbit_file provided")
            self._kepler_elements = None

        logger.info(f"Set SpaceTelescope '{code}' with use_kep={use_kep}, diameter={diameter} m")
    
    def set_keplerian(self, a: float, e: float, i: float, raan: float, argp: float, nu: float, epoch: datetime, mu: float = 398600.4418e9) -> None:
        """Set orbit from Keplerian elements (angles in degrees)"""
        check_positive(a, "Semi-major axis")
        check_range(e, 0, 1, "Eccentricity")
        check_type(i, (int, float), "Inclination")
        check_type(raan, (int, float), "RAAN")
        check_type(argp, (int, float), "Argument of periapsis")
        check_type(nu, (int, float), "True anomaly")
        check_type(epoch, datetime, "Epoch")
        check_positive(mu, "Gravitational parameter")
        self._kepler_elements = {
            "a": a, "e": e, "i": i, "raan": raan, "argp": argp, "nu": nu,
            "epoch": epoch, "mu": mu
        }
        self._orbit_data = None
        logger.info(f"Set Keplerian elements for '{self._code}'")
    
    def set_pitch_range(self, pitch_range: Tuple[float, float]) -> None:
        """Set pitch range in degrees for the SpaceTelescope

        Args:
            pitch_range (Tuple[float, float]): Min and max pitch in degrees (must be within -90 to 90)
        """
        check_type(pitch_range, tuple, "Pitch range")
        if len(pitch_range) != 2:
            raise ValueError("Pitch range must contain exactly 2 values (min, max)")
        min_pitch, max_pitch = pitch_range
        check_range(min_pitch, -90, 90, "Min pitch")
        check_range(max_pitch, min_pitch, 90, "Max pitch")
        self._pitch_range = (min_pitch, max_pitch)
        logger.info(f"Set pitch range={pitch_range} degrees for SpaceTelescope '{self._code}'")

    def set_yaw_range(self, yaw_range: Tuple[float, float]) -> None:
        """Set yaw range in degrees for the SpaceTelescope

        Args:
            yaw_range (Tuple[float, float]): Min and max yaw in degrees (must be within -180 to 180)
        """
        check_type(yaw_range, tuple, "Yaw range")
        if len(yaw_range) != 2:
            raise ValueError("Yaw range must contain exactly 2 values (min, max)")
        min_yaw, max_yaw = yaw_range
        check_range(min_yaw, -180, 180, "Min yaw")
        check_range(max_yaw, min_yaw, 180, "Max yaw")
        self._yaw_range = (min_yaw, max_yaw)
        logger.info(f"Set yaw range={yaw_range} degrees for SpaceTelescope '{self._code}'")

    def set_use_kep(self, use_kep: bool) -> None:
        """Set whether to use Keplerian elements for orbit calculations.

        Args:
            use_kep (bool): True to use Keplerian elements, False to use orbit file data.
        """
        check_type(use_kep, bool, "Use Keplerian flag")
        self._use_kep = use_kep
        logger.info(f"Set use_keplerian={use_kep} for SpaceTelescope '{self._code}'")


    def to_dict(self) -> dict:
        """Convert SpaceTelescope object to a dictionary for serialization
        Orbit data is not serialized, only the file path is stored"""
        base_dict = super().to_dict()
        base_dict.update({
            "type": "SpaceTelescope",
            "orbit_file": self._orbit_file,
            "pitch_range": self._pitch_range,
            "yaw_range": self._yaw_range,
            "kepler_elements": None if self._kepler_elements is None else {
                "a": self._kepler_elements["a"],
                "e": self._kepler_elements["e"],
                "i": np.degrees(self._kepler_elements["i"]),
                "raan": np.degrees(self._kepler_elements["raan"]),
                "argp": np.degrees(self._kepler_elements["argp"]),
                "nu": np.degrees(self._kepler_elements["nu"]),
                "epoch": self._kepler_elements["epoch"].isoformat(),
                "mu": self._kepler_elements["mu"]
            }
        })
        logger.info(f"Converted SpaceTelescope '{self._code}' to dictionary (orbit data not serialized)")
        return base_dict

    @classmethod
    def from_dict(cls, data: dict) -> 'SpaceTelescope':
        """Create a SpaceTelescope object from a dictionary.
        Orbit data is not deserialized; it will be loaded from file if specified."""
        obj = cls(
            code=data["code"],
            name=data["name"],
            orbit_file=data["orbit_file"],
            diameter=data["diameter"],
            sefd_table=data.get("sefd_table", {}),
            pitch_range=tuple(data.get("pitch_range", (-90.0, 90.0))),
            yaw_range=tuple(data.get("yaw_range", (-180.0, 180.0))),
            isactive=data.get("isactive", True)
        )
        if data.get("kepler_elements"):
            obj._kepler_elements = {
                "a": data["kepler_elements"]["a"],
                "e": data["kepler_elements"]["e"],
                "i": np.radians(data["kepler_elements"]["i"]),
                "raan": np.radians(data["kepler_elements"]["raan"]),
                "argp": np.radians(data["kepler_elements"]["argp"]),
                "nu": np.radians(data["kepler_elements"]["nu"]),
                "epoch": datetime.fromisoformat(data["kepler_elements"]["epoch"]),
                "mu": data["kepler_elements"]["mu"]
            }
        # load orbit from file
        if obj._orbit_file:
            try:
                obj.load_orbit(obj._orbit_file)
            except (FileNotFoundError, ValueError) as e:
                logger.warning(f"Could not load orbit data from '{obj._orbit_file}' during deserialization: {e}")
        logger.info(f"Created SpaceTelescope '{data['code']}' from dictionary")
        return obj
    
    def _solve_kepler(self, initial: float, e: float, tol: float = 1e-8, max_iter: int = 200) -> float:
        """Solve Kepler's equation using Newton-Raphson"""
        if e >= 1:
            logger.error(f"Eccentricity {e} not supported for elliptical orbit")
            raise ValueError("Eccentricity must be < 1 for elliptical orbit!")
        x = initial if e < 0.9 else np.pi
        for _ in range(max_iter):
            f = x - e * np.sin(x) - initial
            df = 1 - e * np.cos(x)
            dx = -f / df
            x += dx
            if abs(dx) < tol:
                return x
        logger.warning(f"Kepler's equation did not converge for e={e}, initial={initial} after {max_iter} iterations")
        return x

    def _validate_orbit_data(self) -> bool:
        """Check if orbit data is available (either from file or Kepler elements)"""
        return self._orbit_data is not None or self._kepler_elements is not None

    def __repr__(self) -> str:
        """Return a string representation of SpaceTelescope"""
        orbit_info = f"orbit_file='{self._orbit_file}'" if self._orbit_file else "no orbit loaded"
        kep_info = "kepler_elements_set" if self._kepler_elements else "no kepler elements"
        return (f"SpaceTelescope(code='{self._code}', name='{self._name}', "
                f"{orbit_info}, {kep_info}, diameter={self._diameter}, "
                f"pitch_range={self._pitch_range}, yaw_range={self._yaw_range}, isactive={self.isactive})")

"""Base-class of Telescopes object with the list of object with Telescope/SpaceTelescope type

    Contains:
    Atributes:
        data (Telescope/SpaceTelescope): list of objsects of Telescope/SpaceTelescope type

    Methods:
        add_telescope
        insert_telescope
        remove_telescope
    
        get_telescope
        get_all_telescopes      

        get_active_telescopes
        get_inactive_telescopes

        set_telescope
        
        activate_telescope
        deactivate_telescope

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
class Telescopes(BaseEntity):
    def __init__(self, telescopes: list[Telescope | SpaceTelescope] = None):
        """Initialize Telescopes with a list of Telescope or SpaceTelescope objects."""
        super().__init__()
        if telescopes is not None:
            check_type(telescopes, (list, tuple), "Telescopes")
            for t in telescopes:
                check_type(t, (Telescope, SpaceTelescope), "Telescope")
        self._data = telescopes if telescopes is not None else []
        logger.info(f"Initialized Telescopes with {len(self._data)} telescopes")

    def add_telescope(self, telescope: Telescope | SpaceTelescope) -> None:
        """Add a new telescope"""
        check_type(telescope, (Telescope, SpaceTelescope), "Telescope")
        if self._is_duplicate(telescope):
            logger.error(f"Telescope with code '{telescope.get_code()}' already exists")
            raise ValueError(f"Telescope with code '{telescope.get_code()}' already exists!")
        self._data.append(telescope)
        logger.info(f"Added telescope '{telescope.get_code()}' to Telescopes")
    
    def insert_telescope(self, index: int, telescope: Telescope | SpaceTelescope) -> None:
        """Insert a new telescope at the specified index.

        Args:
            index (int): Index at which to insert the telescope.
            telescope (Telescope | SpaceTelescope): Telescope object to insert.
        """
        check_type(index, int, "Index")
        check_type(telescope, (Telescope, SpaceTelescope), "Telescope")
        if not 0 <= index <= len(self._data):
            logger.error(f"Invalid index {index} for insertion, must be between 0 and {len(self._data)}")
            raise IndexError(f"Index {index} out of range!")
        if self._is_duplicate(telescope):
            logger.error(f"Telescope with code '{telescope.get_code()}' already exists")
            raise ValueError(f"Telescope with code '{telescope.get_code()}' already exists!")
        self._data.insert(index, telescope)
        logger.info(f"Inserted telescope '{telescope.get_code()}' at index {index}")

    def remove_telescope(self, index: int) -> None:
        """Remove telescope by index"""
        try:
            self._data.pop(index)
            logger.info(f"Removed telescope at index {index} from Telescopes")
        except IndexError:
            logger.error(f"Invalid telescope index: {index}")
            raise IndexError("Invalid telescope index!")

    def get_telescope(self, index: int) -> Telescope | SpaceTelescope:
        """Get telescope by index"""
        try:
            return self._data[index]
        except IndexError:
            logger.error(f"Invalid telescope index: {index}")
            raise IndexError("Invalid telescope index!")

    def set_telescope(self, index: int, telescope: Telescope | SpaceTelescope) -> None:
        """Set telescope data by index."""
        check_type(telescope, (Telescope, SpaceTelescope), "Telescope")
        try:
            if any(t.get_code() == telescope.get_code() and i != index for i, t in enumerate(self._data)):
                logger.error(f"Telescope with code '{telescope.get_code()}' already exists")
                raise ValueError(f"Telescope with code '{telescope.get_code()}' already exists!")
            self._data[index] = telescope
            logger.info(f"Set telescope '{telescope.get_code()}' at index {index}")
        except IndexError:
            logger.error(f"Invalid telescope index: {index}")
            raise IndexError("Invalid telescope index!")

    def get_all_telescopes(self) -> list[Telescope | SpaceTelescope]:
        """Get all telescopes"""
        return self._data

    def get_active_telescopes(self) -> list[Telescope | SpaceTelescope]:
        """Get active telescopes"""
        active = [t for t in self._data if t.isactive]
        logger.debug(f"Retrieved {len(active)} active telescopes")
        return active

    def get_inactive_telescopes(self) -> list[Telescope | SpaceTelescope]:
        """Get inactive telescopes"""
        inactive = [t for t in self._data if not t.isactive]
        logger.debug(f"Retrieved {len(inactive)} inactive telescopes")
        return inactive
    
    def activate_telescope(self, index: int) -> None:
        """Activate telescope by index"""
        check_type(index, int, "Index")
        try:
            self._data[index].activate()
            if hasattr(self, '_parent') and self._parent:  # Проверяем наличие родителя
                self._parent._sync_scans_with_activation("telescopes", index, True)
            logger.info(f"Activated telescope '{self._data[index].get_code()}' at index {index}")
        except IndexError:
            logger.error(f"Invalid telescope index: {index}")
            raise IndexError("Invalid telescope index!")

    def deactivate_telescope(self, index: int) -> None:
        """Deactivate telescope by index"""
        check_type(index, int, "Index")
        try:
            self._data[index].deactivate()
            if hasattr(self, '_parent') and self._parent:  # Проверяем наличие родителя
                self._parent._sync_scans_with_activation("telescopes", index, False)
            logger.info(f"Deactivated telescope '{self._data[index].get_code()}' at index {index}")
        except IndexError:
            logger.error(f"Invalid telescope index: {index}")
            raise IndexError("Invalid telescope index!")

    def activate_all(self) -> None:
        """Activate all telescopes"""
        if not self._data:
            logger.error("No telescopes to activate")
            raise ValueError("No telescopes to activate!")
        for t in self._data:
            t.activate()
        logger.info("Activated all telescopes")

    def deactivate_all(self) -> None:
        """Deactivate all telescopes"""
        if not self._data:
            logger.error("No telescopes to deactivate")
            raise ValueError("No telescopes to deactivate!")
        for t in self._data:
            t.deactivate()
        logger.info("Deactivated all telescopes")

    def drop_active(self) -> None:
        """Remove all active telescopes from the list"""
        active_count = len(self.get_active_telescopes())
        if active_count == 0:
            logger.debug("No active telescopes to drop")
            return
        self._data = [t for t in self._data if not t.isactive]
        logger.info(f"Dropped {active_count} active telescopes from Telescopes")
    
    def drop_inactive(self) -> None:
        """Remove all inactive telescopes from the list"""
        inactive_count = len(self.get_inactive_telescopes())
        if inactive_count == 0:
            logger.debug("No inactive telescopes to drop")
            return
        self._data = [t for t in self._data if t.isactive]
        logger.info(f"Dropped {inactive_count} inactive telescopes from Telescopes")

    def clear(self) -> None:
        """Clear telescopes data"""
        logger.info(f"Cleared {len(self._data)} telescopes from Telescopes")
        self._data.clear()

    def to_dict(self) -> dict:
        """Convert Telescopes object to a dictionary for serialization"""
        logger.info(f"Converted Telescopes with {len(self._data)} telescopes to dictionary")
        return {"data": [t.to_dict() for t in self._data]}

    @classmethod
    def from_dict(cls, data: dict) -> 'Telescopes':
        """Create a Telescopes object from a dictionary"""
        telescopes = []
        for t_data in data["data"]:
            if t_data["type"] == "Telescope":
                telescopes.append(Telescope.from_dict(t_data))
            elif t_data["type"] == "SpaceTelescope":
                telescopes.append(SpaceTelescope.from_dict(t_data))
        logger.info(f"Created Telescopes with {len(telescopes)} telescopes from dictionary")
        return cls(telescopes=telescopes)
    
    def _is_duplicate(self, telescope: Telescope | SpaceTelescope) -> bool:
        """Check if a telescope with the same code already exists

        Args:
            telescope (Telescope | SpaceTelescope): Telescope to check

        Returns:
            bool: True if a duplicate exists, False otherwise
        """
        check_type(telescope, (Telescope, SpaceTelescope), "Telescope")
        is_dup = any(t.get_code() == telescope.get_code() for t in self._data)
        logger.debug(f"Checked for duplicate: code '{telescope.get_code()}', result={is_dup}")
        return is_dup

    def __len__(self) -> int:
        """Return the number of telescopes"""
        return len(self._data)

    def __repr__(self) -> str:
        """Return a string representation of Telescopes"""
        active_count = len(self.get_active_telescopes())
        return f"Telescopes(count={len(self._data)}, active={active_count}, inactive={len(self._data) - active_count})"