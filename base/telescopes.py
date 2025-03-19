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

class Telescope(BaseEntity):
    def __init__(self, code: str, name: str, x: float, y: float, z: float, 
                 vx: float, vy: float, vz: float, diameter: float,
                 sefd_table: Optional[Dict[float, float]] = None,
                 efficiency_table: Optional[Dict[float, float]] = None,
                 elevation_range: Tuple[float, float] = (15.0, 90.0),
                 azimuth_range: Tuple[float, float] = (0.0, 360.0),
                 mount_type: str = "AZIM",
                 isactive: bool = True):
        """Initialize a Telescope object with code, name, coordinates (J2000), velocities (J2000), diameter, and additional parameters.

        Args:
            code (str): Telescope short name.
            name (str): Telescope name.
            x (float): Telescope x coordinate (J2000) in meters.
            y (float): Telescope y coordinate (J2000) in meters.
            z (float): Telescope z coordinate (J2000) in meters.
            vx (float): Telescope vx velocity (J2000) in m/s.
            vy (float): Telescope vy velocity (J2000) in m/s.
            vz (float): Telescope vz velocity (J2000) in m/s.
            diameter (float): Antenna diameter in meters.
            sefd_table (Dict[float, float], optional): SEFD table (frequency in MHz: SEFD in Jy).
            efficiency_table (Dict[float, float], optional): Efficiency table (frequency in MHz: efficiency 0-1).
            elevation_range (Tuple[float, float]): Min and max elevation in degrees (default: 15-90).
            azimuth_range (Tuple[float, float]): Min and max azimuth in degrees (default: 0-360).
            mount_type (str): Mount type ('EQUA' or 'AZIM', default: 'AZIM').
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
        check_positive(diameter, "Diameter")
        if sefd_table is not None:
            check_type(sefd_table, dict, "SEFD table")
            for freq, sefd in sefd_table.items():
                check_type(freq, (int, float), "SEFD frequency")
                check_type(sefd, (int, float), "SEFD value")
        if efficiency_table is not None:
            check_type(efficiency_table, dict, "Efficiency table")
            for freq, eff in efficiency_table.items():
                check_type(freq, (int, float), "Efficiency frequency")
                check_range(eff, 0, 1, f"Efficiency at {freq} MHz")
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
        self._efficiency_table = efficiency_table if efficiency_table is not None else {}
        self._elevation_range = elevation_range
        self._azimuth_range = azimuth_range
        self._mount_type = MountType(mount_type.upper())
        logger.info(f"Initialized Telescope '{code}' at ({x}, {y}, {z}) m, diameter={diameter} m")

    def set_telescope(self, code: str, name: str, x: float, y: float, z: float, 
                      vx: float, vy: float, vz: float, diameter: float,
                      sefd_table: Optional[Dict[float, float]] = None,
                      efficiency_table: Optional[Dict[float, float]] = None,
                      elevation_range: Tuple[float, float] = (15.0, 90.0),
                      azimuth_range: Tuple[float, float] = (0.0, 360.0),
                      mount_type: str = "AZIM",
                      isactive: bool = True) -> None:
        """Set Telescope values, including SEFD and efficiency tables."""
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
        if efficiency_table is not None:
            check_type(efficiency_table, dict, "Efficiency table")
            for freq, eff in efficiency_table.items():
                check_type(freq, (int, float), "Efficiency frequency")
                check_range(eff, 0, 1, f"Efficiency at {freq} MHz")
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
        self._efficiency_table = efficiency_table if efficiency_table is not None else {}
        self._elevation_range = elevation_range
        self._azimuth_range = azimuth_range
        self._mount_type = MountType(mount_type.upper())
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

    def get_diameter(self) -> float:
        """Get telescope diameter in meters."""
        return self._diameter

    def set_efficiency(self, frequency: float, efficiency: float) -> None:
        """Set efficiency for a specific frequency."""
        check_type(frequency, (int, float), "Frequency")
        check_range(efficiency, 0, 1, "Efficiency")
        self._efficiency_table[frequency] = efficiency
        logger.info(f"Set efficiency={efficiency} for frequency {frequency} MHz on telescope '{self._code}'")

    def get_efficiency(self, frequency: float) -> Optional[float]:
        """Get efficiency for a given frequency with interpolation if necessary."""
        check_type(frequency, (int, float), "Frequency")
        if not self._efficiency_table:
            logger.debug(f"No efficiency data available for telescope '{self._code}'")
            return None
        freqs = sorted(self._efficiency_table.keys())
        if frequency in self._efficiency_table:
            return self._efficiency_table[frequency]
        if frequency < freqs[0] or frequency > freqs[-1]:
            logger.debug(f"Frequency {frequency} MHz out of efficiency table range for '{self._code}'")
            return None
        for i in range(len(freqs) - 1):
            if freqs[i] <= frequency <= freqs[i + 1]:
                f1, f2 = freqs[i], freqs[i + 1]
                e1, e2 = self._efficiency_table[f1], self._efficiency_table[f2]
                interpolated_eff = e1 + (e2 - e1) * (frequency - f1) / (f2 - f1)
                logger.debug(f"Interpolated efficiency={interpolated_eff} for frequency {frequency} MHz on '{self._code}'")
                return interpolated_eff
        return None

    def get_effective_area(self, frequency: float) -> Optional[float]:
        efficiency = self.get_efficiency(frequency)
        if efficiency is None:
            logger.debug(f"Cannot calculate effective area for frequency {frequency} MHz on '{self._code}': no efficiency data")
            return None
        area = efficiency * np.pi * (self._diameter / 2) ** 2
        logger.debug(f"Calculated effective area={area} m^2 for frequency {frequency} MHz on '{self._code}'")
        return area

    def get_elevation_range(self) -> Tuple[float, float]:
        """Get elevation range in degrees."""
        return self._elevation_range

    def get_azimuth_range(self) -> Tuple[float, float]:
        """Get azimuth range in degrees."""
        return self._azimuth_range

    def get_mount_type(self) -> MountType:
        """Get mount type."""
        return self._mount_type

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
    
    def set_sefd(self, frequency: float, sefd: float) -> None:
        """Set SEFD for a specific frequency."""
        check_type(frequency, (int, float), "Frequency")
        check_positive(sefd, "SEFD")
        self._sefd_table[frequency] = sefd
        logger.info(f"Set SEFD={sefd} Jy for frequency {frequency} MHz on telescope '{self._code}'")

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
            "diameter": self._diameter,
            "sefd_table": self._sefd_table,
            "efficiency_table": self._efficiency_table,
            "elevation_range": self._elevation_range,
            "azimuth_range": self._azimuth_range,
            "mount_type": self._mount_type.value,
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
            diameter=data["diameter"],
            sefd_table=data.get("sefd_table", {}),
            efficiency_table=data.get("efficiency_table", {}),
            elevation_range=tuple(data.get("elevation_range", (15.0, 90.0))),
            azimuth_range=tuple(data.get("azimuth_range", (0.0, 360.0))),
            mount_type=data.get("mount_type", "AZIM"),
            isactive=data.get("isactive", True)
        )

    def __repr__(self) -> str:
        """Return a string representation of Telescope."""
        return (f"Telescope(code='{self._code}', name='{self._name}', "
                f"x={self._x}, y={self._y}, z={self._z}, "
                f"vx={self._vx}, vy={self._vy}, vz={self._vz}, "
                f"diameter={self._diameter}, sefd_table={self._sefd_table}, "
                f"efficiency_table={self._efficiency_table}, "
                f"elevation_range={self._elevation_range}, azimuth_range={self._azimuth_range}, "
                f"mount_type={self._mount_type.value}, isactive={self.isactive})")


class SpaceTelescope(Telescope):
    def __init__(self, code: str, name: str, orbit_file: str, diameter: float,
                 sefd_table: Optional[Dict[float, float]] = None,
                 efficiency_table: Optional[Dict[float, float]] = None,
                 pitch_range: Tuple[float, float] = (-90.0, 90.0),
                 yaw_range: Tuple[float, float] = (-180.0, 180.0),
                 isactive: bool = True):
        """Initialize a SpaceTelescope object with code, name, orbit file, diameter, and additional parameters.

        Args:
            code (str): Telescope short name.
            name (str): Telescope name.
            orbit_file (str): Path to the orbit file (coordinates in km, velocities in km/s).
            diameter (float): Antenna diameter in meters.
            sefd_table (Dict[float, float], optional): SEFD table (frequency in MHz: SEFD in Jy).
            efficiency_table (Dict[float, float], optional): Efficiency table (frequency in MHz: efficiency 0-1).
            pitch_range (Tuple[float, float]): Min and max pitch in degrees (default: -90 to 90).
            yaw_range (Tuple[float, float]): Min and max yaw in degrees (default: -180 to 180).
            isactive (bool): Whether the telescope is active (default: True).
        """
        super().__init__(code, name, 0, 0, 0, 0, 0, 0, diameter, sefd_table=sefd_table,
                         efficiency_table=efficiency_table, isactive=isactive)
        check_non_empty_string(orbit_file, "Orbit file")
        check_positive(diameter, "Diameter")
        check_type(pitch_range, tuple, "Pitch range")
        check_range(pitch_range[0], -90, 90, "Min pitch")
        check_range(pitch_range[1], pitch_range[0], 90, "Max pitch")
        check_type(yaw_range, tuple, "Yaw range")
        check_range(yaw_range[0], -180, 180, "Min yaw")
        check_range(yaw_range[1], yaw_range[0], 180, "Max yaw")
        self._orbit_file = orbit_file
        self._pitch_range = pitch_range
        self._yaw_range = yaw_range
        self._orbit_data = None
        self._kepler_elements = None
        if orbit_file:
            self.load_orbit_from_oem(orbit_file)
        logger.info(f"Initialized SpaceTelescope '{code}' with orbit file '{orbit_file}', diameter={diameter} m")

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
                    if not line or line.startswith('#'):  # Игнорируем пустые строки и комментарии
                        continue
                    if line.startswith("META_STOP"):
                        data_section = True
                        continue
                    if line.startswith("COVARIANCE_START"):  # Пропускаем ковариационные данные
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
        logger.info(f"Loaded orbit data from '{orbit_file}' for SpaceTelescope '{self._code}'")

    def interpolate_orbit_chebyshev(self, degree: int = 5) -> None:
        """Interpolate orbit data using Chebyshev polynomials."""
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
        """Interpolate orbit data using cubic splines."""
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

    def set_orbit_from_kepler_elements(self, a: float, e: float, i: float, raan: float, argp: float, nu: float, epoch: datetime, mu: float = 398600.4418e9) -> None:
        """Set orbit from Keplerian elements (angles in radians)."""
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
        self._orbit_data = None  # Сбрасываем табличные данные
        logger.info(f"Set Keplerian elements for '{self._code}'")

    def get_position_velocity_from_kepler(self, dt: datetime) -> tuple[np.ndarray, np.ndarray]:
        """Get position and velocity from Keplerian elements at a given time."""
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

    def _solve_kepler(self, initial: float, e: float, tol: float = 1e-8, max_iter: int = 200) -> float:
        """Solve Kepler's equation using Newton-Raphson."""
        if e >= 1:
            logger.error(f"Eccentricity {e} not supported for elliptical orbit")
            raise ValueError("Eccentricity must be < 1 for elliptical orbit!")
        x = initial if e < 0.9 else np.pi  # Улучшенное начальное приближение
        for _ in range(max_iter):
            f = x - e * np.sin(x) - initial
            df = 1 - e * np.cos(x)
            dx = -f / df
            x += dx
            if abs(dx) < tol:
                return x
        logger.warning(f"Kepler's equation did not converge for e={e}, initial={initial} after {max_iter} iterations")
        return x

    def get_position_at_time(self, dt: datetime) -> tuple[np.ndarray, np.ndarray]:
        """Get position and velocity at a given time."""
        t = (dt - datetime(2000, 1, 1, 12, 0, 0)).total_seconds()
        if self._kepler_elements:
            return self.get_position_velocity_from_kepler(dt)
        if self._orbit_data is None:
            logger.error(f"No orbit data or Kepler elements for '{self._code}'")
            raise ValueError("No orbit data or Kepler elements available!")
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

    def get_pitch_range(self) -> Tuple[float, float]:
        """Get pitch range in degrees."""
        return self._pitch_range

    def get_yaw_range(self) -> Tuple[float, float]:
        """Get yaw range in degrees."""
        return self._yaw_range

    def to_dict(self) -> dict:
        """Convert SpaceTelescope object to a dictionary for serialization.
            Keplerian elements angles (i, raan, argp, nu) are stored in degrees."""
        base_dict = super().to_dict()
        base_dict.update({
            "type": "SpaceTelescope",
            "orbit_file": self._orbit_file,
            "pitch_range": self._pitch_range,
            "yaw_range": self._yaw_range,
            "orbit_data": None if self._orbit_data is None else {
                "times": self._orbit_data["times"].tolist(),
                "positions": self._orbit_data["positions"].tolist(),
                "velocities": self._orbit_data["velocities"].tolist()
            },
        "kepler_elements": None if self._kepler_elements is None else {
            "a": self._kepler_elements["a"],
            "e": self._kepler_elements["e"],
            "i": np.degrees(self._kepler_elements["i"]),  # Stored in degrees for serialization, converted back to radians in from_dict
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
        logger.info(f"Created SpaceTelescope '{data['code']}' from dictionary")
        obj = cls(
            code=data["code"],
            name=data["name"],
            orbit_file=data["orbit_file"],
            diameter=data["diameter"],
            sefd_table=data.get("sefd_table", {}),
            efficiency_table=data.get("efficiency_table", {}),
            pitch_range=tuple(data.get("pitch_range", (-90.0, 90.0))),
            yaw_range=tuple(data.get("yaw_range", (-180.0, 180.0))),
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
        return obj

    def __repr__(self) -> str:
        """Return a string representation of SpaceTelescope."""
        orbit_info = f"orbit_file='{self._orbit_file}'" if self._orbit_file else "no orbit loaded"
        kep_info = "kepler_elements_set" if self._kepler_elements else "no kepler elements"
        return (f"SpaceTelescope(code='{self._code}', name='{self._name}', "
                f"{orbit_info}, {kep_info}, diameter={self._diameter}, "
                f"sefd_table={self._sefd_table}, efficiency_table={self._efficiency_table}, "
                f"pitch_range={self._pitch_range}, yaw_range={self._yaw_range}, isactive={self.isactive})")


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