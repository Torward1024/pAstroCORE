# base/telescopes.py
from base.base_entity import BaseEntity
from utils.validation import check_type, check_non_empty_string
from utils.logging_setup import logger
import numpy as np
from scipy.interpolate import CubicSpline
from numpy.polynomial import chebyshev
from datetime import datetime
import re
from typing import Optional, Dict

class Telescope(BaseEntity):
    def __init__(self, code: str, name: str, x: float, y: float, z: float, 
                 vx: float, vy: float, vz: float, 
                 sefd_table: Optional[Dict[float, float]] = None, 
                 isactive: bool = True):
        """Initialize a Telescope object with code, name, coordinates (J2000), velocities (J2000), and SEFD.

        Args:
            code (str): Telescope short name.
            name (str): Telescope name.
            x (float): Telescope x coordinate (J2000) in meters.
            y (float): Telescope y coordinate (J2000) in meters.
            z (float): Telescope z coordinate (J2000) in meters.
            vx (float): Telescope vx velocity (J2000) in m/s.
            vy (float): Telescope vy velocity (J2000) in m/s.
            vz (float): Telescope vz velocity (J2000) in m/s.
            sefd_table (Dict[float, float], optional): SEFD table (frequency in MHz: SEFD in Jy).
            isactive (bool): Whether the telescope is active (default: True).
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
        if sefd_table is not None:
            check_type(sefd_table, dict, "SEFD table")
            for freq, sefd in sefd_table.items():
                check_type(freq, (int, float), "SEFD frequency")
                check_type(sefd, (int, float), "SEFD value")

        self._code = code
        self._name = name
        self._x = x
        self._y = y
        self._z = z
        self._vx = vx
        self._vy = vy
        self._vz = vz
        self._sefd_table = sefd_table if sefd_table is not None else {}
        logger.info(f"Initialized Telescope '{code}' at ({x}, {y}, {z}) m")

    def set_telescope(self, code: str, name: str, x: float, y: float, z: float, 
                      vx: float, vy: float, vz: float, 
                      sefd_table: Optional[Dict[float, float]] = None, 
                      isactive: bool = True) -> None:
        """Set Telescope values, including SEFD table."""
        check_non_empty_string(code, "Code")
        check_non_empty_string(name, "Name")
        check_type(x, (int, float), "X coordinate")
        check_type(y, (int, float), "Y coordinate")
        check_type(z, (int, float), "Z coordinate")
        check_type(vx, (int, float), "VX velocity")
        check_type(vy, (int, float), "VY velocity")
        check_type(vz, (int, float), "VZ velocity")
        if sefd_table is not None:
            check_type(sefd_table, dict, "SEFD table")
            for freq, sefd in sefd_table.items():
                check_type(freq, (int, float), "SEFD frequency")
                check_type(sefd, (int, float), "SEFD value")

        self._code = code
        self._name = name
        self._x = x
        self._y = y
        self._z = z
        self._vx = vx
        self._vy = vy
        self._vz = vz
        self._sefd_table = sefd_table if sefd_table is not None else {}
        self.isactive = isactive
        logger.info(f"Set telescope '{code}' with new parameters")

    def get_telescope_name(self) -> str:
        """Get telescope name."""
        return self._name

    def get_telescope_code(self) -> str:
        """Get telescope code."""
        return self._code

    def get_telescope_coordinates(self) -> tuple[float, float, float]:
        """Get telescope coordinates x, y, z in meters (J2000)."""
        logger.debug(f"Retrieved coordinates ({self._x}, {self._y}, {self._z}) m for telescope '{self._code}'")
        return self._x, self._y, self._z

    def get_telescope_velocities(self) -> tuple[float, float, float]:
        """Get telescope velocities vx, vy, vz in m/s (J2000)."""
        return self._vx, self._vy, self._vz

    def set_sefd(self, frequency: float, sefd: float) -> None:
        """Set SEFD for a specific frequency."""
        check_type(frequency, (int, float), "Frequency")
        check_type(sefd, (int, float), "SEFD")
        self._sefd_table[frequency] = sefd
        logger.info(f"Set SEFD={sefd} Jy for frequency {frequency} MHz on telescope '{self._code}'")

    def get_sefd(self, frequency: float) -> Optional[float]:
        """Get SEFD for a given frequency with interpolation if necessary."""
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

    def to_dict(self) -> dict:
        """Convert Telescope object to a dictionary for serialization."""
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
            "sefd_table": self._sefd_table,
            "isactive": self.isactive
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Telescope':
        """Create a Telescope object from a dictionary."""
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
            sefd_table=data.get("sefd_table", {}),
            isactive=data.get("isactive", True)
        )

    def __repr__(self) -> str:
        """Return a string representation of Telescope."""
        return (f"Telescope(code='{self._code}', name='{self._name}', "
                f"x={self._x}, y={self._y}, z={self._z}, "
                f"vx={self._vx}, vy={self._vy}, vz={self._vz}, "
                f"sefd_table={self._sefd_table}, isactive={self.isactive})")


class SpaceTelescope(Telescope):
    def __init__(self, code: str, name: str, orbit_file: str, 
                 sefd_table: Optional[Dict[float, float]] = None, 
                 isactive: bool = True):
        """Initialize a SpaceTelescope object with code, name, orbit file, and SEFD.

        Args:
            code (str): Telescope short name.
            name (str): Telescope name.
            orbit_file (str): Path to the orbit file (coordinates in km, velocities in km/s).
            sefd_table (Dict[float, float], optional): SEFD table (frequency in MHz: SEFD in Jy).
            isactive (bool): Whether the telescope is active (default: True).
        """
        super().__init__(code, name, 0, 0, 0, 0, 0, 0, sefd_table=sefd_table, isactive=isactive)
        check_non_empty_string(orbit_file, "Orbit file")
        self._orbit_file = orbit_file
        self._orbit_data = None
        self._kepler_elements = None
        if orbit_file:
            self.load_orbit_from_oem(orbit_file)
        logger.info(f"Initialized SpaceTelescope '{code}' with orbit file '{orbit_file}'")

    def load_orbit_from_oem(self, orbit_file: str) -> None:
        """Load orbit data from a CCSDS OEM 2.0 file."""
        # Код остаётся без изменений
        check_non_empty_string(orbit_file, "Orbit file")
        times, positions, velocities = [], [], []
        try:
            with open(orbit_file, 'r') as f:
                lines = f.readlines()
                data_section = False
                for line in lines:
                    line = line.strip()
                    if line.startswith('#'):
                        continue
                    if line.startswith("META_STOP"):
                        data_section = True
                        continue
                    if not data_section or not line:
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
        self._orbit_data = {
            "times": np.array(times),
            "positions": np.array(positions),
            "velocities": np.array(velocities)
        }
        self._orbit_file = orbit_file
        logger.info(f"Loaded orbit data from '{orbit_file}' for SpaceTelescope '{self._code}'")

    # Методы interpolate_orbit_chebyshev, interpolate_orbit_cubic_spline, set_orbit_from_kepler_elements,
    # get_position_velocity_from_kepler, _solve_kepler, get_position_at_time остаются без изменений

    def to_dict(self) -> dict:
        """Convert SpaceTelescope object to a dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "type": "SpaceTelescope",
            "orbit_file": self._orbit_file,
            "orbit_data": None if self._orbit_data is None else {
                "times": self._orbit_data["times"].tolist(),
                "positions": self._orbit_data["positions"].tolist(),
                "velocities": self._orbit_data["velocities"].tolist()
            },
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
        logger.info(f"Converted SpaceTelescope '{self._code}' to dictionary")
        return base_dict

    @classmethod
    def from_dict(cls, data: dict) -> 'SpaceTelescope':
        """Create a SpaceTelescope object from a dictionary."""
        obj = cls(
            code=data["code"],
            name=data["name"],
            orbit_file=data["orbit_file"],
            sefd_table=data.get("sefd_table", {}),
            isactive=data.get("isactive", True)
        )
        if data.get("orbit_data"):
            obj._orbit_data = {
                "times": np.array(data["orbit_data"]["times"]),
                "positions": np.array(data["orbit_data"]["positions"]),
                "velocities": np.array(data["orbit_data"]["velocities"])
            }
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
        logger.info(f"Created SpaceTelescope '{data['code']}' from dictionary")
        return obj

    def __repr__(self) -> str:
        """Return a string representation of SpaceTelescope."""
        orbit_info = f"orbit_file='{self._orbit_file}'" if self._orbit_file else "no orbit loaded"
        kep_info = "kepler_elements_set" if self._kepler_elements else "no kepler elements"
        return (f"SpaceTelescope(code='{self._code}', name='{self._name}', "
                f"{orbit_info}, {kep_info}, sefd_table={self._sefd_table}, isactive={self.isactive})")


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
        """Add a new telescope."""
        check_type(telescope, (Telescope, SpaceTelescope), "Telescope")
        if any(t.get_telescope_code() == telescope.get_telescope_code() for t in self._data):
            logger.error(f"Telescope with code '{telescope.get_telescope_code()}' already exists")
            raise ValueError(f"Telescope with code '{telescope.get_telescope_code()}' already exists!")
        self._data.append(telescope)
        logger.info(f"Added telescope '{telescope.get_telescope_code()}' to Telescopes")

    def remove_telescope(self, index: int) -> None:
        """Remove telescope by index."""
        try:
            self._data.pop(index)
            logger.info(f"Removed telescope at index {index} from Telescopes")
        except IndexError:
            logger.error(f"Invalid telescope index: {index}")
            raise IndexError("Invalid telescope index!")

    def get_telescope(self, index: int) -> Telescope | SpaceTelescope:
        """Get telescope by index."""
        try:
            return self._data[index]
        except IndexError:
            logger.error(f"Invalid telescope index: {index}")
            raise IndexError("Invalid telescope index!")

    def set_telescope(self, index: int, telescope: Telescope | SpaceTelescope) -> None:
        """Set telescope data by index."""
        check_type(telescope, (Telescope, SpaceTelescope), "Telescope")
        try:
            if any(t.get_telescope_code() == telescope.get_telescope_code() and i != index for i, t in enumerate(self._data)):
                logger.error(f"Telescope with code '{telescope.get_telescope_code()}' already exists")
                raise ValueError(f"Telescope with code '{telescope.get_telescope_code()}' already exists!")
            self._data[index] = telescope
            logger.info(f"Set telescope '{telescope.get_telescope_code()}' at index {index}")
        except IndexError:
            logger.error(f"Invalid telescope index: {index}")
            raise IndexError("Invalid telescope index!")

    def set_sefd_for_all(self, frequency: float, sefd_values: Dict[str, float]) -> None:
        """Set SEFD for all telescopes at a given frequency.

        Args:
            frequency (float): Frequency in MHz.
            sefd_values (Dict[str, float]): Dictionary of telescope codes and their SEFD values.
        """
        check_type(frequency, (int, float), "Frequency")
        check_type(sefd_values, dict, "SEFD values")
        for code, sefd in sefd_values.items():
            check_type(sefd, (int, float), f"SEFD for {code}")
            for telescope in self._data:
                if telescope.get_telescope_code() == code:
                    telescope.set_sefd(frequency, sefd)
                    break
            else:
                logger.warning(f"Telescope '{code}' not found in Telescopes for SEFD update")

    def get_all_telescopes(self) -> list[Telescope | SpaceTelescope]:
        """Get all telescopes."""
        return self._data

    def get_active_telescopes(self) -> list[Telescope | SpaceTelescope]:
        """Get active telescopes."""
        active = [t for t in self._data if t.isactive]
        logger.debug(f"Retrieved {len(active)} active telescopes")
        return active

    def get_inactive_telescopes(self) -> list[Telescope | SpaceTelescope]:
        """Get inactive telescopes."""
        inactive = [t for t in self._data if not t.isactive]
        logger.debug(f"Retrieved {len(inactive)} inactive telescopes")
        return inactive

    def activate_all(self) -> None:
        """Activate all telescopes."""
        if not self._data:
            logger.error("No telescopes to activate")
            raise ValueError("No telescopes to activate!")
        for t in self._data:
            t.activate()
        logger.info("Activated all telescopes")

    def deactivate_all(self) -> None:
        """Deactivate all telescopes."""
        if not self._data:
            logger.error("No telescopes to deactivate")
            raise ValueError("No telescopes to deactivate!")
        for t in self._data:
            t.deactivate()
        logger.info("Deactivated all telescopes")

    def clear(self) -> None:
        """Clear telescopes data."""
        logger.info(f"Cleared {len(self._data)} telescopes from Telescopes")
        self._data.clear()

    def to_dict(self) -> dict:
        """Convert Telescopes object to a dictionary for serialization."""
        logger.info(f"Converted Telescopes with {len(self._data)} telescopes to dictionary")
        return {"data": [t.to_dict() for t in self._data]}

    @classmethod
    def from_dict(cls, data: dict) -> 'Telescopes':
        """Create a Telescopes object from a dictionary."""
        telescopes = []
        for t_data in data["data"]:
            if t_data["type"] == "Telescope":
                telescopes.append(Telescope.from_dict(t_data))
            elif t_data["type"] == "SpaceTelescope":
                telescopes.append(SpaceTelescope.from_dict(t_data))
        logger.info(f"Created Telescopes with {len(telescopes)} telescopes from dictionary")
        return cls(telescopes=telescopes)

    def __len__(self) -> int:
        """Return the number of telescopes."""
        return len(self._data)

    def __repr__(self) -> str:
        """Return a string representation of Telescopes."""
        active_count = len(self.get_active_telescopes())
        return f"Telescopes(count={len(self._data)}, active={active_count}, inactive={len(self._data) - active_count})"