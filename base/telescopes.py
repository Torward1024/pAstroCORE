# base/telescopes.py
from base.base_entity import BaseEntity
from utils.validation import check_type, check_non_empty_string
from utils.logging_setup import logger
import numpy as np
from scipy.interpolate import CubicSpline
from numpy.polynomial import chebyshev
from datetime import datetime
import re

class Telescope(BaseEntity):
    def __init__(self, code: str, name: str, x: float, y: float, z: float, vx: float, vy: float, vz: float, isactive: bool = True):
        """Initialize a Telescope object with code, name, coordinates (J2000), and velocities (J2000).

        Args:
            code (str): Telescope short name.
            name (str): Telescope name.
            x (float): Telescope x coordinate (J2000) in meters.
            y (float): Telescope y coordinate (J2000) in meters.
            z (float): Telescope z coordinate (J2000) in meters.
            vx (float): Telescope vx velocity (J2000) in m/s.
            vy (float): Telescope vy velocity (J2000) in m/s.
            vz (float): Telescope vz velocity (J2000) in m/s.
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
        self._code = code
        self._name = name
        self._x = x
        self._y = y
        self._z = z
        self._vx = vx
        self._vy = vy
        self._vz = vz
        logger.info(f"Initialized Telescope '{code}' at ({x}, {y}, {z}) m")

    def set_telescope(self, code: str, name: str, x: float, y: float, z: float, vx: float, vy: float, vz: float, isactive: bool = True) -> None:
        """Set Telescope values."""
        check_non_empty_string(code, "Code")
        check_non_empty_string(name, "Name")
        check_type(x, (int, float), "X coordinate")
        check_type(y, (int, float), "Y coordinate")
        check_type(z, (int, float), "Z coordinate")
        check_type(vx, (int, float), "VX velocity")
        check_type(vy, (int, float), "VY velocity")
        check_type(vz, (int, float), "VZ velocity")
        self._code = code
        self._name = name
        self._x = x
        self._y = y
        self._z = z
        self._vx = vx
        self._vy = vy
        self._vz = vz
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
            "isactive": self.isactive
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Telescope':
        """Create a Telescope object from a dictionary."""
        logger.info(f"Created telescope '{data['code']}' from dictionary")
        return cls(**data)

    def __repr__(self) -> str:
        """Return a string representation of Telescope."""
        return (f"Telescope(code='{self._code}', name='{self._name}', "
                f"x={self._x}, y={self._y}, z={self._z}, "
                f"vx={self._vx}, vy={self._vy}, vz={self._vz}, isactive={self.isactive})")

class SpaceTelescope(Telescope):
    def __init__(self, code: str, name: str, orbit_file: str, isactive: bool = True):
        """Initialize a SpaceTelescope object with code, name, and orbit file.

        Args:
            code (str): Telescope short name.
            name (str): Telescope name.
            orbit_file (str): Path to the orbit file (coordinates in km, velocities in km/s).
            isactive (bool): Whether the telescope is active (default: True).
        """
        super().__init__(code, name, 0, 0, 0, 0, 0, 0, isactive)
        check_non_empty_string(orbit_file, "Orbit file")
        self._orbit_file = orbit_file
        self._orbit_data = None
        self._kepler_elements = None
        if orbit_file:
            self.load_orbit_from_oem(orbit_file)
        logger.info(f"Initialized SpaceTelescope '{code}' with orbit file '{orbit_file}'")

    def load_orbit_from_oem(self, orbit_file: str) -> None:
        """Load orbit data from a CCSDS OEM 2.0 file."""
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

    def interpolate_orbit_chebyshev(self, time: float, degree: int = 5) -> tuple[np.ndarray, np.ndarray]:
        """Interpolate orbit using Chebyshev polynomials."""
        logger.debug(f"Starting Chebyshev interpolation for '{self._code}' at time={time}")
        if self._orbit_data is None:
            logger.error("Orbit data not loaded")
            raise ValueError("Orbit data not loaded! Please load an OEM file first.")
        t = self._orbit_data["times"]
        positions = self._orbit_data["positions"]
        velocities = self._orbit_data["velocities"]
        if len(t) < degree + 1:
            logger.error(f"Number of data points ({len(t)}) must be at least degree + 1 ({degree + 1})")
            raise ValueError(f"Number of data points ({len(t)}) must be at least degree + 1 ({degree + 1})!")
        if not (t.min() <= time <= t.max()):
            logger.error("Requested time is outside the orbit data range")
            raise ValueError("Requested time is outside the orbit data range!")
        t_min, t_max = t.min(), t.max()
        t_normalized = 2 * (t - t_min) / (t_max - t_min) - 1
        time_normalized = 2 * (time - t_min) / (t_max - t_min) - 1
        pos_coeffs = np.zeros((3, degree + 1))
        vel_coeffs = np.zeros((3, degree + 1))
        for i in range(3):
            pos_coeffs[i] = chebyshev.chebfit(t_normalized, positions[:, i], degree)
            vel_coeffs[i] = chebyshev.chebfit(t_normalized, velocities[:, i], degree)
        pos = chebyshev.chebval(time_normalized, pos_coeffs)
        vel_coeffs_deriv = chebyshev.chebder(pos_coeffs)
        vel = chebyshev.chebval(time_normalized, vel_coeffs_deriv)
        vel *= 2 / (t_max - t_min)
        logger.info(f"Interpolated orbit for '{self._code}' at time={time} using Chebyshev")
        return pos, vel

    def interpolate_orbit_cubic_spline(self, time: float) -> tuple[np.ndarray, np.ndarray]:
        """Interpolate orbit using cubic spline at a given time (in seconds since J2000)."""
        logger.debug(f"Starting cubic spline interpolation for '{self._code}' at time={time}")
        if self._orbit_data is None:
            logger.error("Orbit data not loaded")
            raise ValueError("Orbit data not loaded! Please load an OEM file first.")
        t = self._orbit_data["times"]
        if not (t.min() <= time <= t.max()):
            logger.error("Requested time is outside the orbit data range")
            raise ValueError("Requested time is outside the orbit data range!")
        pos_spline = CubicSpline(t, self._orbit_data["positions"], axis=0)
        vel_spline = CubicSpline(t, self._orbit_data["velocities"], axis=0)
        logger.info(f"Interpolated orbit for '{self._code}' at time={time} using cubic spline")
        return pos_spline(time), vel_spline(time)

    def set_orbit_from_kepler_elements(self, a: float, e: float, i: float, raan: float, argp: float, nu: float, epoch: datetime, mu: float = 398600.4418) -> None:
        """Set orbit using Keplerian elements and store them.

        Args:
            a (float): Semi-major axis in km.
            e (float): Eccentricity.
            i (float): Inclination in degrees.
            raan (float): Right Ascension of Ascending Node in degrees.
            argp (float): Argument of Perigee in degrees.
            nu (float): True Anomaly in degrees.
            epoch (datetime): Epoch of the elements.
            mu (float): Gravitational parameter (default: Earth's, 398600.4418 km^3/s^2).
        """
        self._kepler_elements = {
            "a": a * 1000,  # km -> m
            "e": e,
            "i": np.radians(i),
            "raan": np.radians(raan),
            "argp": np.radians(argp),
            "nu": np.radians(nu),
            "epoch": epoch,
            "mu": mu * 1e9  # km^3/s^2 -> m^3/s^2
        }
        logger.info(f"Set Keplerian elements for '{self._code}' with a={a} km, e={e}")

    def get_position_velocity_from_kepler(self, time: datetime) -> tuple[np.ndarray, np.ndarray]:
        """Compute position (x, y, z) and velocity (vx, vy, vz) at a given time using stored Keplerian elements."""
        if self._kepler_elements is None:
            logger.error("Keplerian elements not set")
            raise ValueError("Keplerian elements not set! Please call set_orbit_from_kepler_elements first.")
        a = self._kepler_elements["a"]
        e = self._kepler_elements["e"]
        i = self._kepler_elements["i"]
        raan = self._kepler_elements["raan"]
        argp = self._kepler_elements["argp"]
        nu0 = self._kepler_elements["nu"]
        mu = self._kepler_elements["mu"]
        epoch = self._kepler_elements["epoch"]
        delta_t = (time - epoch).total_seconds()
        n = np.sqrt(mu / a**3)
        E0 = 2 * np.arctan2(np.sqrt(1 - e) * np.tan(nu0 / 2), np.sqrt(1 + e))
        M0 = E0 - e * np.sin(E0)
        M = M0 + n * delta_t
        E = self._solve_kepler(M, e)
        nu = 2 * np.arctan2(np.sqrt(1 + e) * np.sin(E / 2), np.sqrt(1 - e) * np.cos(E / 2))
        p = a * (1 - e**2)
        r = p / (1 + e * np.cos(nu))
        x_p = r * np.cos(nu)
        y_p = r * np.sin(nu)
        z_p = 0.0
        h = np.sqrt(mu * p)
        vx_p = -(mu / h) * np.sin(nu)
        vy_p = (mu / h) * (e + np.cos(nu))
        vz_p = 0.0
        cos_raan = np.cos(raan)
        sin_raan = np.sin(raan)
        cos_argp = np.cos(argp)
        sin_argp = np.sin(argp)
        cos_i = np.cos(i)
        sin_i = np.sin(i)
        R = np.array([
            [cos_raan * cos_argp - sin_raan * sin_argp * cos_i, -cos_raan * sin_argp - sin_raan * cos_argp * cos_i, sin_raan * sin_i],
            [sin_raan * cos_argp + cos_raan * sin_argp * cos_i, -sin_raan * sin_argp + cos_raan * cos_argp * cos_i, -cos_raan * sin_i],
            [sin_argp * sin_i, cos_argp * sin_i, cos_i]
        ])
        pos_p = np.array([x_p, y_p, z_p])
        vel_p = np.array([vx_p, vy_p, vz_p])
        pos = R @ pos_p
        vel = R @ vel_p
        logger.info(f"Computed position and velocity for '{self._code}' at time={time}")
        return pos, vel

    def _solve_kepler(self, M: float, e: float, tol: float = 1e-8, max_iter: int = 100) -> float:
        """Solve Kepler's equation (M = E - e * sin(E)) for eccentric anomaly E using Newton-Raphson."""
        E = M if e < 0.8 else np.pi
        for _ in range(max_iter):
            f = E - e * np.sin(E) - M
            f_prime = 1 - e * np.cos(E)
            E_new = E - f / f_prime
            if abs(E_new - E) < tol:
                return E_new
            E = E_new
        raise ValueError("Kepler's equation did not converge!")

    def get_position_at_time(self, time: float | datetime) -> tuple[np.ndarray, np.ndarray]:
        """Get position and velocity at a given time (datetime or seconds since J2000)."""
        if isinstance(time, datetime):
            j2000_epoch = datetime(2000, 1, 1, 12, 0, 0)
            time_sec = (time - j2000_epoch).total_seconds()
        else:
            time_sec = time
        if self._kepler_elements:
            return self.get_position_velocity_from_kepler(time if isinstance(time, datetime) else datetime.fromtimestamp(time_sec + 946728000))
        elif self._orbit_data:
            return self.interpolate_orbit_cubic_spline(time_sec)
        else:
            logger.error("No orbit data or Kepler elements available")
            raise ValueError("No orbit data or Kepler elements available!")

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
            isactive=data["isactive"]
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
                f"{orbit_info}, {kep_info}, isactive={self.isactive})")

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