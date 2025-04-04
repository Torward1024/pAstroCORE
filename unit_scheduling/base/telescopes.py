from common.base.base_entity import BaseEntity
from common.utils.validation import check_type, check_non_empty_string, check_positive, check_range
from common.utils.logging_setup import logger
import numpy as np
from scipy.interpolate import CubicSpline
from numpy.polynomial import chebyshev
import re
from typing import Optional, Dict, Tuple
from enum import Enum
from astropy.time import Time

class MountType(Enum):
    EQUATORIAL = "EQUA"
    AZIMUTHAL = "AZIM"
    SPACE = 'NONE'

"""Base class of a Telescope object with code, name, coordinates (ITRF), velocities (ITRF), diameter, and additional parameters

    Notes:  All coordinates are stored in meters in ITRF
            Telescope name and short name (code) MUST be unique
    Contains:
    Attributes:
        code (str): Telescope short name
        name (str): Telescope name
        x (float): Telescope x coordinate (ITRF) in meters
        y (float): Telescope y coordinate (ITRF) in meters
        z (float): Telescope z coordinate (ITRF) in meters
        vx (float): Telescope vx velocity (ITRF) in m/year
        vy (float): Telescope vy velocity (ITRF) in m/year
        vz (float): Telescope vz velocity (ITRF) in m/year
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
        set_code
        set_coordinates
        set_velocities
        set_coordinates_and_velocities
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
    def __init__(self, code: str = "TEMP", name: str = "Temporary Telescope",
                 x: float = 0.0, y: float = 0.0, z: float = 0.0,
                 vx: float = 0.0, vy: float = 0.0, vz: float = 0.0,
                 diameter: float = 1.0, sefd_table: Optional[Dict[float, float]] = None,
                 elevation_range: Tuple[float, float] = (15.0, 90.0),
                 azimuth_range: Tuple[float, float] = (0.0, 360.0),
                 mount_type: str = "AZIM", isactive: bool = True):
        """Initialize a Telescope object with code, name, coordinates (ITRF), velocities (ITRF), diameter, and additional parameters."""
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
        check_type(frequency, (int, float), "Frequency")
        check_positive(sefd, "SEFD")
        self._check_sefd(frequency, sefd)
        self._sefd_table[frequency] = sefd
        logger.info(f"Added SEFD={sefd} Jy for frequency {frequency} MHz to telescope '{self._code}'")
    
    def insert_sefd(self, frequency: float, sefd: float) -> None:
        check_type(frequency, (int, float), "Frequency")
        check_positive(sefd, "SEFD")
        self._check_sefd(frequency, sefd)
        self._sefd_table[frequency] = sefd
        logger.info(f"Inserted SEFD={sefd} Jy for frequency {frequency} MHz into telescope '{self._code}'")
    
    def remove_sefd(self, frequency: float) -> None:
        check_type(frequency, (int, float), "Frequency")
        if frequency in self._sefd_table:
            removed_sefd = self._sefd_table.pop(frequency)
            logger.info(f"Removed SEFD={removed_sefd} Jy for frequency {frequency} MHz from telescope '{self._code}'")
        else:
            logger.warning(f"No SEFD value found for frequency {frequency} MHz in telescope '{self._code}'")

    def activate(self):
        return super().activate()
    
    def deactivate(self):
        return super().deactivate()

    def get_name(self) -> str:
        return self._name

    def get_code(self) -> str:
        return self._code

    def get_coordinates(self) -> tuple[float, float, float]:
        logger.debug(f"Retrieved coordinates ({self._x}, {self._y}, {self._z}) m for telescope '{self._code}'")
        return self._x, self._y, self._z
    
    def get_velocities(self) -> tuple[float, float, float]:
        return self._vx, self._vy, self._vz
    
    def get_coordinates_and_velocities(self) -> tuple[float, float, float, float, float, float]:
        return self._x, self._y, self._z, self._vx, self._vy, self._vz
    
    def get_x(self) -> float:
        logger.debug(f"Retrieved coordinate X={self._x} m for telescope '{self._code}'")
        return self._x
    
    def get_y(self) -> float:
        logger.debug(f"Retrieved coordinate Y={self._y} m for telescope '{self._code}'")
        return self._y
    
    def get_z(self) -> float:
        logger.debug(f"Retrieved coordinate Z={self._z} m for telescope '{self._code}'")
        return self._z
    
    def get_vx(self) -> float:
        logger.debug(f"Retrieved velocity Vx={self._vx} m for telescope '{self._code}'")
        return self._vx
    
    def get_vy(self) -> float:
        logger.debug(f"Retrieved velocity Vy={self._vy} m for telescope '{self._code}'")
        return self._vy
    
    def get_vz(self) -> float:
        logger.debug(f"Retrieved velocity Vz={self._vz} m for telescope '{self._code}'")
        return self._vz

    def get_diameter(self) -> float:
        return self._diameter

    def get_elevation_range(self) -> Tuple[float, float]:
        return self._elevation_range

    def get_azimuth_range(self) -> Tuple[float, float]:
        return self._azimuth_range

    def get_mount_type(self) -> MountType:
        return self._mount_type

    def get_sefd(self, frequency: float) -> Optional[float]:
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
        logger.debug(f"Retrieved SEFD table {self._sefd_table} for telescope '{self._code}'")
        return self._sefd_table
    
    def set_telescope(self, code: str, name: str, x: float, y: float, z: float, 
                      vx: float, vy: float, vz: float, diameter: float,
                      sefd_table: Optional[Dict[float, float]] = None,
                      elevation_range: Tuple[float, float] = (15.0, 90.0),
                      azimuth_range: Tuple[float, float] = (0.0, 360.0),
                      mount_type: str = "AZIM",
                      isactive: bool = True) -> None:
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
        check_non_empty_string(name, "Name")
        self._name = name
        logger.info(f"Set name '{name}' for telescope '{self._code}'")

    def set_code(self, code: str) -> None:
        check_non_empty_string(code, "Code")
        self._code = code
        logger.info(f"Set code '{code}' for telescope with name '{self._name}'")
    
    def set_coordinates(self, coordinates: Tuple[float, float, float]) -> None:
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
        check_type(x, (int, float), "X coordinate")
        self._x = x
        logger.info(f"Set x={x} m for telescope '{self._code}'")

    def set_y(self, y: float) -> None:
        check_type(y, (int, float), "Y coordinate")
        self._y = y
        logger.info(f"Set y={y} m for telescope '{self._code}'")

    def set_z(self, z: float) -> None:
        check_type(z, (int, float), "Z coordinate")
        self._z = z
        logger.info(f"Set z={z} m for telescope '{self._code}'")
    
    def set_vx(self, vx: float) -> None:
        check_type(vx, (int, float), "VX velocity")
        self._vx = vx
        logger.info(f"Set vx={vx} m/s for telescope '{self._code}'")

    def set_vy(self, vy: float) -> None:
        check_type(vy, (int, float), "VY velocity")
        self._vy = vy
        logger.info(f"Set vy={vy} m/s for telescope '{self._code}'")

    def set_vz(self, vz: float) -> None:
        check_type(vz, (int, float), "VZ velocity")
        self._vz = vz
        logger.info(f"Set vz={vz} m/s for telescope '{self._code}'")
    
    def set_diameter(self, diameter: float) -> None:
        check_positive(diameter, "Diameter")
        self._diameter = diameter
        logger.info(f"Set diameter={diameter} m for telescope '{self._code}'")
    
    def set_elevation_range(self, elevation_range: Tuple[float, float]) -> None:
        check_type(elevation_range, tuple, "Elevation range")
        if len(elevation_range) != 2:
            raise ValueError("Elevation range must contain exactly 2 values (min, max)")
        min_el, max_el = elevation_range
        check_range(min_el, 0, 90, "Min elevation")
        check_range(max_el, min_el, 90, "Max elevation")
        self._elevation_range = (min_el, max_el)
        logger.info(f"Set elevation range={elevation_range} degrees for telescope '{self._code}'")
    
    def set_azimuth_range(self, azimuth_range: Tuple[float, float]) -> None:
        check_type(azimuth_range, tuple, "Azimuth range")
        if len(azimuth_range) != 2:
            raise ValueError("Azimuth range must contain exactly 2 values (min, max)")
        min_az, max_az = azimuth_range
        check_range(min_az, 0, 360, "Min azimuth")
        check_range(max_az, min_az, 360, "Max azimuth")
        self._azimuth_range = (min_az, max_az)
        logger.info(f"Set azimuth range={azimuth_range} degrees for telescope '{self._code}'")
    
    def set_mount_type(self, mount_type: str) -> None:
        check_non_empty_string(mount_type, "Mount type")
        if mount_type.upper() not in {mt.value for mt in MountType}:
            raise ValueError(f"Mount type must be one of {[mt.value for mt in MountType]}, got {mount_type}")
        self._mount_type = MountType(mount_type.upper())
        logger.info(f"Set mount type='{self._mount_type.value}' for telescope '{self._code}'")
    
    def set_sefd(self, frequency: float, sefd: float) -> None:
        check_type(frequency, (int, float), "Frequency")
        check_positive(sefd, "SEFD")
        self._check_sefd(frequency, sefd)
        self._sefd_table[frequency] = sefd
        logger.info(f"Set SEFD={sefd} Jy for frequency {frequency} MHz on telescope '{self._code}'")
    
    def set_sefd_table(self, sefd_table: Dict[float, float]) -> None:
        check_type(sefd_table, dict, "SEFD table")
        for freq, sefd in sefd_table.items():
            check_type(freq, (int, float), "SEFD frequency")
            check_positive(sefd, "SEFD value")
        self._sefd_table = sefd_table.copy()
        logger.info(f"Set SEFD table with {len(sefd_table)} entries for telescope '{self._code}'")
    
    def clear_sefd_table(self) -> None:
        self._sefd_table.clear()
        logger.info(f"Cleared SEFD table for telescope '{self._code}'")

    def to_dict(self) -> dict:
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
        if frequency in self._sefd_table:
            current_sefd = self._sefd_table[frequency]
            if current_sefd != sefd:
                logger.warning(f"Overwriting SEFD for frequency {frequency} MHz on telescope '{self._code}': "
                               f"old value={current_sefd} Jy, new value={sefd} Jy")
                return True
        return False

    def __repr__(self) -> str:
        return (f"Telescope(code='{self._code}', name='{self._name}', "
                f"x={self._x}, y={self._y}, z={self._z}, "
                f"vx={self._vx}, vy={self._vy}, vz={self._vz}, "
                f"diameter={self._diameter}, sefd_table={self._sefd_table}, "
                f"elevation_range={self._elevation_range}, azimuth_range={self._azimuth_range}, "
                f"mount_type={self._mount_type.value}, isactive={self.isactive})")


class SpaceTelescope(Telescope):
    def __init__(self, code: str = "TEMP_SPACE", name: str = "Temporary Space Telescope",
                 orbit_file: str = "dummy_orbit.oem", diameter: float = 1.0,
                 sefd_table: Optional[Dict[float, float]] = None,
                 pitch_range: Tuple[float, float] = (-90.0, 90.0),
                 yaw_range: Tuple[float, float] = (-180.0, 180.0),
                 isactive: bool = True, use_kep: bool = True,
                 kepler_elements: Optional[dict] = None,
                 interpolation_method: str = "linear"):
        super().__init__(code=code, name=name, x=0.0, y=0.0, z=0.0, vx=0.0, vy=0.0, vz=0.0, 
                         diameter=diameter, sefd_table=sefd_table, isactive=isactive,
                         mount_type="NONE")
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

        self._interpolation_method = interpolation_method
        self._interpolated_orbit = None

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
                check_type(kepler_elements["epoch"], Time, "Epoch")
                check_positive(kepler_elements["mu"], "Gravitational parameter")
                self._kepler_elements = kepler_elements.copy()
            else:
                logger.warning(f"Initialized SpaceTelescope '{code}' with use_kep=True but no kepler_elements provided")
            self._orbit_data = None
        else:
            if orbit_file:
                self.load_orbit(orbit_file)
                logger.info(f"Initialized SpaceTelescope '{code}' with orbit file '{orbit_file}', diameter={diameter} m")
            else:
                logger.warning(f"Initialized SpaceTelescope '{code}' with use_kep=False but no orbit_file provided")
            self._kepler_elements = None

    def load_orbit(self, orbit_file: str) -> None:
        """Parse CSDSS OEM 2.0 styled orbit file"""
        check_non_empty_string(orbit_file, "Orbit file")
        try:
            with open(orbit_file, 'r') as f:
                lines = f.readlines()
            
            data_lines = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
            data_section = False
            valid_lines = []
            
            for line in data_lines:
                if "META_STOP" in line:
                    data_section = True
                    continue
                if not data_section:
                    continue
                if "COVARIANCE_START" in line:
                    break
                parts = re.split(r'\s+', line.strip())
                if len(parts) == 7:
                    valid_lines.append(line)
            
            if len(valid_lines) < 2:
                raise ValueError(f"Orbit file must contain at least 2 data points, got {len(valid_lines)}")
            
            time_strs = [re.split(r'\s+', line)[0] for line in valid_lines]
            j2000_epoch = Time("2000-01-01T12:00:00", scale='utc')
            times = Time(time_strs, format='isot', scale='utc') - j2000_epoch
            times_sec = times.sec
            
            positions = np.zeros((len(valid_lines), 3))
            velocities = np.zeros((len(valid_lines), 3))
            for i, line in enumerate(valid_lines):
                parts = re.split(r'\s+', line)
                x, y, z = map(float, parts[1:4])  # km -> m
                vx, vy, vz = map(float, parts[4:7])  # km/s -> m/s
                positions[i] = [x * 1000, y * 1000, z * 1000]
                velocities[i] = [vx * 1000, vy * 1000, vz * 1000]
            
            self._orbit_data = {
                "times": times_sec,
                "positions": positions,
                "velocities": velocities
            }
            self._orbit_file = orbit_file
            logger.info(f"Loaded orbit data from '{orbit_file}' with {len(valid_lines)} points")
        
        except FileNotFoundError:
            logger.error(f"Orbit file '{orbit_file}' not found")
            raise FileNotFoundError(f"Orbit file '{orbit_file}' not found!")
        except ValueError as e:
            logger.error(f"Error parsing orbit file: {str(e)}")
            raise ValueError(f"Error parsing orbit file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing orbit file: {str(e)}")
            raise

    def set_interpolation_method(self, method: str) -> None:
        valid_methods = {"linear", "chebyshev", "cubic_spline"}
        if method not in valid_methods:
            raise ValueError(f"Interpolation method must be one of {valid_methods}, got {method}")
        self._interpolation_method = method
        self._interpolated_orbit = None
        logger.info(f"Set interpolation method to '{method}' for SpaceTelescope '{self._code}'")

    def interpolate_orbit(self, start_time: Time, end_time: Time, time_step: float) -> None:
        if self._use_kep:
            logger.info(f"Using Keplerian elements for '{self._code}', skipping interpolation")
            return
        if self._orbit_data is None:
            raise ValueError(f"No orbit data loaded for '{self._code}'")
        times = self._orbit_data["times"]
        positions = self._orbit_data["positions"]
        velocities = self._orbit_data["velocities"]
        j2000_epoch = Time("2000-01-01T12:00:00", scale='utc')
        t_start = (start_time - j2000_epoch).sec
        t_end = (end_time - j2000_epoch).sec
        logger.info(f"Interpolating orbit for '{self._code}' from {start_time.isot} to {end_time.isot}")
        mask = (times >= t_start) & (times <= t_end)
        if not np.any(mask):
            raise ValueError(f"No orbit data within time range {start_time.isot} to {end_time.isot}")
        filtered_times = times[mask]
        filtered_positions = positions[mask]
        filtered_velocities = velocities[mask]

        unique_indices = np.unique(filtered_times, return_index=True)[1]
        filtered_times = filtered_times[unique_indices]
        filtered_positions = filtered_positions[unique_indices]
        filtered_velocities = filtered_velocities[unique_indices]

        if len(filtered_times) < 2:
            raise ValueError(f"After removing duplicates, too few points ({len(filtered_times)}) for interpolation")

        interp_times = np.arange(t_start, t_end + time_step, time_step)
        if self._interpolation_method == "chebyshev":
            degree = 20  # degree of Chebyshev polynomial
            norm_times = 2 * (filtered_times - t_start) / (t_end - t_start) - 1  
            norm_interp_times = 2 * (interp_times - t_start) / (t_end - t_start) - 1

            pos_polynomials = [chebyshev.Chebyshev.fit(norm_times, pos, degree) for pos in filtered_positions.T]
            vel_polynomials = [chebyshev.Chebyshev.fit(norm_times, vel, degree) for vel in filtered_velocities.T]

            self._interpolated_orbit = {
                "time_range": (t_start, t_end),
                "times": interp_times,
                "positions": [poly(norm_interp_times) for poly in pos_polynomials],
                "velocities": [poly(norm_interp_times) for poly in vel_polynomials]
            }
        elif self._interpolation_method == "cubic_spline":
            self._interpolated_orbit = {
                "time_range": (t_start, t_end),
                "times": interp_times,
                "positions": [CubicSpline(filtered_times, pos)(interp_times) for pos in filtered_positions.T],
                "velocities": [CubicSpline(filtered_times, vel)(interp_times) for vel in filtered_velocities.T]
            }
        else:  # linear
            self._interpolated_orbit = {
                "time_range": (t_start, t_end),
                "times": interp_times,
                "positions": [np.interp(interp_times, filtered_times, pos) for pos in filtered_positions.T],
                "velocities": [np.interp(interp_times, filtered_times, vel) for vel in filtered_velocities.T]
            }
        logger.info(f"Interpolated orbit for '{self._code}' using {self._interpolation_method} from {start_time.isot} to {end_time.isot}")
    
    def get_state_vector(self, time: Time) -> tuple[np.ndarray, np.ndarray]:
        if self._use_kep:
            return self.get_state_vector_from_kepler(time)
        else:
            return self.get_state_vector_from_orbit(time)

    def get_state_vector_from_kepler(self, time: Time) -> tuple[np.ndarray, np.ndarray]:
        if self._kepler_elements is None:
            logger.error(f"No Keplerian elements set for '{self._code}'")
            raise ValueError("No Keplerian elements set!")
        a, e, i, raan, argp, nu0, epoch, mu = (
            self._kepler_elements[k] for k in ["a", "e", "i", "raan", "argp", "nu", "epoch", "mu"]
        )
        t = (time - epoch).sec  # Разница в секундах
        M = np.sqrt(mu / a**3) * t + self._solve_kepler(nu0, e)  # Mean anomaly
        E = self._solve_kepler(M, e)  # Eccentric anomaly
        nu = 2 * np.arctan2(np.sqrt(1 + e) * np.sin(E / 2), np.sqrt(1 - e) * np.cos(E / 2))  # True anomaly
        r = a * (1 - e * np.cos(E))  # Distance
        p = a * (1 - e**2)  # Semi-latus rectum
        h = np.sqrt(mu * p)  # Angular momentum
        pos_p = np.array([r * np.cos(nu), r * np.sin(nu), 0])
        vel_p = np.array([-np.sin(nu), e + np.cos(nu), 0]) * (h / p)
        R1 = np.array([[np.cos(raan), -np.sin(raan), 0], [np.sin(raan), np.cos(raan), 0], [0, 0, 1]])
        R2 = np.array([[1, 0, 0], [0, np.cos(i), -np.sin(i)], [0, np.sin(i), np.cos(i)]])
        R3 = np.array([[np.cos(argp), -np.sin(argp), 0], [np.sin(argp), np.cos(argp), 0], [0, 0, 1]])
        R = R1 @ R2 @ R3
        pos = R @ pos_p
        vel = R @ vel_p
        logger.debug(f"Calculated position={pos}, velocity={vel} for '{self._code}' at {time.isot}")
        return pos, vel

    def get_state_vector_from_orbit(self, time: Time) -> tuple[np.ndarray, np.ndarray]:
        """Get position and velocity vectors from orbit data or interpolated orbit at a given time."""
        if self._orbit_data is None:
            raise ValueError(f"No orbit data defined for '{self._code}'")
        
        j2000_epoch = Time("2000-01-01T12:00:00", scale='utc')
        t = (time - j2000_epoch).sec

        if self._interpolated_orbit and "time_range" in self._interpolated_orbit:
            t_min, t_max = self._interpolated_orbit["time_range"]
            interp_times = self._interpolated_orbit["times"]
            if t_min <= t <= t_max:

                idx = np.searchsorted(interp_times, t)
                if idx == 0:
                    pos = np.array([p[0] for p in self._interpolated_orbit["positions"]])
                    vel = np.array([v[0] for v in self._interpolated_orbit["velocities"]])
                elif idx >= len(interp_times):
                    pos = np.array([p[-1] for p in self._interpolated_orbit["positions"]])
                    vel = np.array([v[-1] for v in self._interpolated_orbit["velocities"]])
                else:
                    pos = np.array([p[idx - 1] for p in self._interpolated_orbit["positions"]])
                    vel = np.array([v[idx - 1] for v in self._interpolated_orbit["velocities"]])
                logger.debug(f"Retrieved interpolated state vector for '{self._code}' at {time.isot}: pos={pos}, vel={vel}")
                return pos, vel
            else:
                logger.warning(f"Time {time.isot} outside interpolated range ({Time(t_min, format='sec', scale='utc').isot} to {Time(t_max, format='sec', scale='utc').isot}) for '{self._code}'")
        
        if self._interpolated_orbit is None:
            logger.warning(f"No interpolated orbit data available for '{self._code}' at {time.isot}, falling back to raw orbit data")
        
        times = self._orbit_data["times"]
        if t < times[0] or t > times[-1]:
            logger.warning(f"Time {time.isot} outside raw orbit data range ({Time(times[0], format='sec', scale='utc').isot} to {Time(times[-1], format='sec', scale='utc').isot}), using last known state")
            return np.array([self._x, self._y, self._z]), np.array([self._vx, self._vy, self._vz])
        
        pos_idx = np.searchsorted(times, t)
        t1, t2 = times[pos_idx - 1], times[pos_idx]
        pos1, pos2 = self._orbit_data["positions"][pos_idx - 1], self._orbit_data["positions"][pos_idx]
        vel1, vel2 = self._orbit_data["velocities"][pos_idx - 1], self._orbit_data["velocities"][pos_idx]
        frac = (t - t1) / (t2 - t1)
        pos = pos1 + (pos2 - pos1) * frac
        vel = vel1 + (vel2 - vel1) * frac
        logger.debug(f"Calculated state vector from raw data for '{self._code}' at {time.isot}: pos={pos}, vel={vel}")
        return pos, vel
    
    def get_keplerian(self) -> Optional[Dict[str, any]]:
        if self._kepler_elements is not None:
            logger.debug(f"Retrieved Keplerian elements for SpaceTelescope '{self._code}': {self._kepler_elements}")
            return self._kepler_elements.copy()
        logger.debug(f"No Keplerian elements set for SpaceTelescope '{self._code}'")
        return None

    def get_pitch_range(self) -> Tuple[float, float]:
        return self._pitch_range

    def get_yaw_range(self) -> Tuple[float, float]:
        return self._yaw_range
    
    def get_use_kep(self) -> bool:
        logger.debug(f"Retrieved use_keplerian={self._use_kep} for SpaceTelescope '{self._code}'")
        return self._use_kep
    
    def set_telescope(self, code: str, name: str, orbit_file: str, diameter: float,
                      sefd_table: Optional[Dict[float, float]] = None,
                      pitch_range: Tuple[float, float] = (-90.0, 90.0),
                      yaw_range: Tuple[float, float] = (-180.0, 180.0),
                      isactive: bool = True,
                      use_kep: bool = True,
                      kepler_elements: Optional[dict] = None,
                      interpolation_method: str = "chebyshev") -> None:
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
                check_type(kepler_elements["epoch"], Time, "Epoch")
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

        self._interpolation_method = interpolation_method
        self._interpolated_orbit = None
        logger.info(f"Set SpaceTelescope '{code}' with use_kep={use_kep}, diameter={diameter} m")
    
    def set_keplerian(self, a: float, e: float, i: float, raan: float, argp: float, nu: float, epoch: Time, mu: float = 398600.4418e9) -> None:
        check_positive(a, "Semi-major axis")
        check_range(e, 0, 1, "Eccentricity")
        check_type(i, (int, float), "Inclination")
        check_type(raan, (int, float), "RAAN")
        check_type(argp, (int, float), "Argument of periapsis")
        check_type(nu, (int, float), "True anomaly")
        check_type(epoch, Time, "Epoch")
        check_positive(mu, "Gravitational parameter")
        self._kepler_elements = {
            "a": a, "e": e, "i": i, "raan": raan, "argp": argp, "nu": nu,
            "epoch": epoch, "mu": mu
        }
        self._orbit_data = None
        logger.info(f"Set Keplerian elements for '{self._code}'")
    
    def set_pitch_range(self, pitch_range: Tuple[float, float]) -> None:
        check_type(pitch_range, tuple, "Pitch range")
        if len(pitch_range) != 2:
            raise ValueError("Pitch range must contain exactly 2 values (min, max)")
        min_pitch, max_pitch = pitch_range
        check_range(min_pitch, -90, 90, "Min pitch")
        check_range(max_pitch, min_pitch, 90, "Max pitch")
        self._pitch_range = (min_pitch, max_pitch)
        logger.info(f"Set pitch range={pitch_range} degrees for SpaceTelescope '{self._code}'")

    def set_yaw_range(self, yaw_range: Tuple[float, float]) -> None:
        check_type(yaw_range, tuple, "Yaw range")
        if len(yaw_range) != 2:
            raise ValueError("Yaw range must contain exactly 2 values (min, max)")
        min_yaw, max_yaw = yaw_range
        check_range(min_yaw, -180, 180, "Min yaw")
        check_range(max_yaw, min_yaw, 180, "Max yaw")
        self._yaw_range = (min_yaw, max_yaw)
        logger.info(f"Set yaw range={yaw_range} degrees for SpaceTelescope '{self._code}'")

    def set_use_kep(self, use_kep: bool) -> None:
        check_type(use_kep, bool, "Use Keplerian flag")
        self._use_kep = use_kep
        logger.info(f"Set use_keplerian={use_kep} for SpaceTelescope '{self._code}'")

    def to_dict(self) -> dict:
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
                "epoch": self._kepler_elements["epoch"].isot,  # Используем isot для сериализации
                "mu": self._kepler_elements["mu"]
            }
        })
        logger.info(f"Converted SpaceTelescope '{self._code}' to dictionary (orbit data not serialized)")
        return base_dict

    @classmethod
    def from_dict(cls, data: dict) -> 'SpaceTelescope':
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
                "epoch": Time(data["kepler_elements"]["epoch"], scale='utc'),  # Десериализация в Time
                "mu": data["kepler_elements"]["mu"]
            }
        if obj._orbit_file:
            try:
                obj.load_orbit(obj._orbit_file)
            except (FileNotFoundError, ValueError) as e:
                logger.warning(f"Could not load orbit data from '{obj._orbit_file}' during deserialization: {e}")
        logger.info(f"Created SpaceTelescope '{data['code']}' from dictionary")
        return obj
    
    def _solve_kepler(self, initial: float, e: float, tol: float = 1e-8, max_iter: int = 200) -> float:
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
        return self._orbit_data is not None or self._kepler_elements is not None

    def __repr__(self) -> str:
        orbit_info = f"orbit_file='{self._orbit_file}'" if self._orbit_file else "no orbit loaded"
        kep_info = "kepler_elements_set" if self._kepler_elements else "no kepler elements"
        return (f"SpaceTelescope(code='{self._code}', name='{self._name}', "
                f"{orbit_info}, {kep_info}, diameter={self._diameter}, "
                f"pitch_range={self._pitch_range}, yaw_range={self._yaw_range}, isactive={self.isactive})")


class Telescopes(BaseEntity):
    def __init__(self, telescopes: list[Telescope | SpaceTelescope] = None):
        super().__init__()
        if telescopes is not None:
            check_type(telescopes, (list, tuple), "Telescopes")
            for t in telescopes:
                check_type(t, (Telescope, SpaceTelescope), "Telescope")
        self._data = telescopes if telescopes is not None else []
        logger.info(f"Initialized Telescopes with {len(self._data)} telescopes")

    def add_telescope(self, telescope: Telescope | SpaceTelescope) -> None:
        check_type(telescope, (Telescope, SpaceTelescope), "Telescope")
        if self._is_duplicate(telescope):
            logger.error(f"Telescope with code '{telescope.get_code()}' already exists")
            raise ValueError(f"Telescope with code '{telescope.get_code()}' already exists!")
        self._data.append(telescope)
        logger.info(f"Added telescope '{telescope.get_code()}' to Telescopes")

    def create_telescope(self, code: str = "TEMP", name: str = "Temporary Telescope",
                         x: float = 0.0, y: float = 0.0, z: float = 0.0,
                         vx: float = 0.0, vy: float = 0.0, vz: float = 0.0,
                         diameter: float = 1.0, sefd_table: Optional[Dict[float, float]] = None,
                         elevation_range: Tuple[float, float] = (15.0, 90.0),
                         azimuth_range: Tuple[float, float] = (0.0, 360.0),
                         mount_type: str = "AZIM", isactive: bool = True) -> None:
        new_telescope = Telescope(
            code=code, name=name, x=x, y=y, z=z, vx=vx, vy=vy, vz=vz,
            diameter=diameter, sefd_table=sefd_table,
            elevation_range=elevation_range, azimuth_range=azimuth_range,
            mount_type=mount_type, isactive=isactive
        )
        if self._is_duplicate(new_telescope):
            logger.error(f"Telescope with code '{code}' already exists")
            raise ValueError(f"Telescope with code '{code}' already exists!")
        self._data.append(new_telescope)
        logger.info(f"Created and added telescope '{code}' to Telescopes")
    
    def insert_telescope(self, index: int, telescope: Telescope | SpaceTelescope) -> None:
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
        try:
            self._data.pop(index)
            logger.info(f"Removed telescope at index {index} from Telescopes")
        except IndexError:
            logger.error(f"Invalid telescope index: {index}")
            raise IndexError("Invalid telescope index!")

    def get_by_index(self, index: int) -> Telescope | SpaceTelescope:
        try:
            return self._data[index]
        except IndexError:
            logger.error(f"Invalid telescope index: {index}")
            raise IndexError("Invalid telescope index!")

    def set_telescope(self, index: int, telescope: Telescope | SpaceTelescope) -> None:
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
        return self._data

    def get_active_telescopes(self) -> list[Telescope | SpaceTelescope]:
        active = [t for t in self._data if t.isactive]
        logger.debug(f"Retrieved {len(active)} active telescopes")
        return active

    def get_inactive_telescopes(self) -> list[Telescope | SpaceTelescope]:
        inactive = [t for t in self._data if not t.isactive]
        logger.debug(f"Retrieved {len(inactive)} inactive telescopes")
        return inactive
    
    def activate_telescope(self, index: int) -> None:
        check_type(index, int, "Index")
        try:
            self._data[index].activate()
            if hasattr(self, '_parent') and self._parent:
                self._parent._sync_scans_with_activation("telescopes", index, True)
            logger.info(f"Activated telescope '{self._data[index].get_code()}' at index {index}")
        except IndexError:
            logger.error(f"Invalid telescope index: {index}")
            raise IndexError("Invalid telescope index!")

    def deactivate_telescope(self, index: int) -> None:
        check_type(index, int, "Index")
        try:
            self._data[index].deactivate()
            if hasattr(self, '_parent') and self._parent:
                self._parent._sync_scans_with_activation("telescopes", index, False)
            logger.info(f"Deactivated telescope '{self._data[index].get_code()}' at index {index}")
        except IndexError:
            logger.error(f"Invalid telescope index: {index}")
            raise IndexError("Invalid telescope index!")

    def activate_all(self) -> None:
        if not self._data:
            logger.error("No telescopes to activate")
            raise ValueError("No telescopes to activate!")
        for t in self._data:
            t.activate()
        logger.info("Activated all telescopes")

    def deactivate_all(self) -> None:
        if not self._data:
            logger.error("No telescopes to deactivate")
            raise ValueError("No telescopes to deactivate!")
        for t in self._data:
            t.deactivate()
        logger.info("Deactivated all telescopes")

    def drop_active(self) -> None:
        active_count = len(self.get_active_telescopes())
        if active_count == 0:
            logger.debug("No active telescopes to drop")
            return
        self._data = [t for t in self._data if not t.isactive]
        logger.info(f"Dropped {active_count} active telescopes from Telescopes")
    
    def drop_inactive(self) -> None:
        inactive_count = len(self.get_inactive_telescopes())
        if inactive_count == 0:
            logger.debug("No inactive telescopes to drop")
            return
        self._data = [t for t in self._data if t.isactive]
        logger.info(f"Dropped {inactive_count} inactive telescopes from Telescopes")

    def clear(self) -> None:
        logger.info(f"Cleared {len(self._data)} telescopes from Telescopes")
        self._data.clear()

    def to_dict(self) -> dict:
        logger.info(f"Converted Telescopes with {len(self._data)} telescopes to dictionary")
        return {"data": [t.to_dict() for t in self._data]}

    @classmethod
    def from_dict(cls, data: dict) -> 'Telescopes':
        telescopes = []
        for t_data in data["data"]:
            if t_data["type"] == "Telescope":
                telescopes.append(Telescope.from_dict(t_data))
            elif t_data["type"] == "SpaceTelescope":
                telescopes.append(SpaceTelescope.from_dict(t_data))
        logger.info(f"Created Telescopes with {len(telescopes)} telescopes from dictionary")
        return cls(telescopes=telescopes)
    
    def _is_duplicate(self, telescope: Telescope | SpaceTelescope) -> bool:
        check_type(telescope, (Telescope, SpaceTelescope), "Telescope")
        is_dup = any(t.get_code() == telescope.get_code() for t in self._data)
        logger.debug(f"Checked for duplicate: code '{telescope.get_code()}', result={is_dup}")
        return is_dup

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        active_count = len(self.get_active_telescopes())
        return f"Telescopes(count={len(self._data)}, active={active_count}, inactive={len(self._data) - active_count})"