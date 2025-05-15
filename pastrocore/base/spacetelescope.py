from copy import deepcopy
from .telescope import Telescope
from common.utils.logging_setup import logger
import numpy as np
from scipy.interpolate import CubicSpline
from numpy.polynomial import chebyshev
import re
from typing import Optional, Dict, Tuple, Any, Union
from astropy.time import Time
from enum import Enum
import os
import uuid

class MountType(Enum):
    EQUATORIAL = "EQUA"
    AZIMUTHAL = "AZIM"
    SPACE = "NONE"

class SpaceTelescope(Telescope):
    """Class representing a space-based telescope with orbital parameters and SEFD properties.

    Inherits from Telescope, setting mount_type to 'NONE'. Adds orbital data (via file, direct data, or Keplerian elements),
    pitch and yaw ranges, and interpolation methods (linear, Chebyshev, or cubic spline) for orbit calculations.
    Provides state vector (position and velocity) retrieval at specific times.
    """
    type: str
    orbit_file: str
    pitch_range: Tuple[float, float]
    yaw_range: Tuple[float, float]
    use_kep: bool
    kepler_elements: dict
    orbit_data: dict
    interpolation_method: str
    interpolated_orbit: dict

    def __init__(self, *, code: str = "TS", name: str = "TEMPSPACETELESCOPE", type: str = "SpaceTelescope",
                 orbit_file: str = "dummy_orbit.oem", diameter: float = 1.0,
                 sefd_table: Optional[Dict[float, float]] = None,
                 pitch_range: Tuple[float, float] = (-90.0, 90.0),
                 yaw_range: Tuple[float, float] = (-180.0, 180.0),
                 isactive: bool = True, use_kep: bool = True,
                 kepler_elements: dict = None,
                 interpolation_method: str = "linear",
                 surface_accuracy: Optional[float] = None,
                 surface_efficiency_table: Optional[Dict[float, float]] = None,
                 effective_area_table: Optional[Dict[float, float]] = None,
                 system_temperature_table: Optional[Dict[float, float]] = None,
                 interpolated_orbit: dict = None):
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
            "interpolation_method": interpolation_method,
            "interpolated_orbit": interpolated_orbit,
            "orbit_data": None  # Explicitly set to None initially
        })

        if use_kep and kepler_elements is not None:
            self._validate_kepler_elements(kepler_elements)
            self.orbit_data = None
            logger.info(f"Initialized SpaceTelescope '{code}' with Keplerian elements, diameter={diameter} m")
        elif not use_kep and orbit_file and os.path.isfile(orbit_file):
            try:
                self.load_orbit(orbit_file)
                logger.info(f"Initialized SpaceTelescope '{code}' with orbit file '{orbit_file}', diameter={diameter} m")
            except FileNotFoundError:
                logger.warning(f"Orbit file '{orbit_file}' not found; initializing without orbit data")
                self.orbit_data = None
                self.use_kep = False
                self.kepler_elements = None
        else:
            logger.warning(f"Initialized SpaceTelescope '{code}' without orbit data or Keplerian elements")
            self.orbit_data = None
            self.use_kep = use_kep
            self.kepler_elements = None

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

    def load_orbit(self, orbit_file: str) -> None:
        """Load orbital data from a CSDSS OEM 2.0 styled file."""
        if not isinstance(orbit_file, str) or not orbit_file.strip():
            raise TypeError("Orbit file must be a non-empty string")
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
            
            self.orbit_data = {
                "times": times_sec,
                "positions": positions,
                "velocities": velocities
            }
            self.orbit_file = orbit_file
            self.use_kep = False
            self.kepler_elements = None
            self.interpolated_orbit = None
            logger.info(f"Loaded orbit data from '{orbit_file}' with {len(valid_lines)} points")
        
        except FileNotFoundError:
            logger.error(f"Orbit file '{orbit_file}' not found")
            raise
        except ValueError as e:
            logger.error(f"Error parsing orbit file: {str(e)}")
            raise

    def get_orbit(self) -> Optional[Dict[str, np.ndarray]]:
        """Retrieve the current orbit data."""
        if self.orbit_data is not None:
            return {
                "times": self.orbit_data["times"].copy(),
                "positions": self.orbit_data["positions"].copy(),
                "velocities": self.orbit_data["velocities"].copy()
            }
        return None
    
    def copy(self) -> 'SpaceTelescope':
        """Create a deep copy of the SpaceTelescope object, validating orbital parameters."""
        copied = SpaceTelescope(
            code=self.code,
            name=self.name,
            orbit_file=self.orbit_file,
            diameter=self.diameter,
            sefd_table=deepcopy(self.sefd_table),
            pitch_range=self.pitch_range,
            yaw_range=self.yaw_range,
            isactive=self.isactive,
            use_kep=self.use_kep,
            kepler_elements=deepcopy(self.kepler_elements),
            orbit_data=deepcopy(self.orbit_data),
            interpolation_method=self.interpolation_method,
            surface_accuracy=self.surface_accuracy,
            surface_efficiency_table=deepcopy(self.surface_efficiency_table),
            effective_area_table=deepcopy(self.effective_area_table),
            system_temperature_table=deepcopy(self.system_temperature_table),
            interpolated_orbit=deepcopy(self.interpolated_orbit)
        )
        if copied.kepler_elements:
            copied._validate_kepler_elements(copied.kepler_elements)
        if copied.orbit_data:
            copied.set_orbit(copied.orbit_data)  # Validates orbit data
        return copied

    def set_orbit(self, orbit_data: Dict[str, np.ndarray]) -> None:
        """Set orbit data directly with times, positions, and velocities."""
        required_keys = {"times", "positions", "velocities"}
        if not isinstance(orbit_data, dict) or not required_keys.issubset(orbit_data):
            raise ValueError(f"Orbit data must be a dict with keys: {required_keys}")
        
        times = np.asarray(orbit_data["times"])
        positions = np.asarray(orbit_data["positions"])
        velocities = np.asarray(orbit_data["velocities"])

        if times.ndim != 1:
            raise ValueError("Times must be a 1D array")
        if positions.ndim != 2 or positions.shape[1] != 3:
            raise ValueError("Positions must be a 2D array with shape (N, 3)")
        if velocities.ndim != 2 or velocities.shape[1] != 3:
            raise ValueError("Velocities must be a 2D array with shape (N, 3)")
        if len(times) != positions.shape[0] or len(times) != velocities.shape[0]:
            raise ValueError("Times, positions, and velocities must have the same length")
        if not np.all(np.diff(times) > 0):
            raise ValueError("Times must be in strictly increasing order")

        self.orbit_data = {
            "times": times.copy(),
            "positions": positions.copy(),
            "velocities": velocities.copy()
        }
        self.use_kep = False
        self.kepler_elements = None
        self.interpolated_orbit = None
        self.orbit_file = None
        logger.info(f"Set orbit data with {len(times)} points")

    def set_interpolation_method(self, method: str) -> None:
        """Set the interpolation method for orbit data."""
        valid_methods = {"linear", "chebyshev", "cubic_spline"}
        if method not in valid_methods:
            raise ValueError(f"Interpolation method must be one of {valid_methods}")
        self.interpolation_method = method
        self.interpolated_orbit = None
        logger.info(f"Set interpolation method to '{method}'")

    def interpolate_orbit(self, start_time: Time, end_time: Time, time_step: float) -> None:
        """Interpolate orbit data over a time range using the specified method."""
        if self.use_kep:
            logger.info("Using Keplerian elements, skipping interpolation")
            return
        if self.orbit_data is None:
            raise ValueError("No orbit data loaded")
        times = self.orbit_data["times"]
        positions = self.orbit_data["positions"]
        velocities = self.orbit_data["velocities"]
        j2000_epoch = Time("2000-01-01T12:00:00", scale='utc')
        t_start = (start_time - j2000_epoch).sec
        t_end = (end_time - j2000_epoch).sec
        logger.info(f"Interpolating orbit for {self.name} from {start_time.isot} to {end_time.isot}")
        
        start_idx = np.searchsorted(times, t_start, side='left')
        end_idx = np.searchsorted(times, t_end, side='right')
        if start_idx >= end_idx:
            raise ValueError(f"No orbit data within time range {start_time.isot} to {end_time.isot}")
        filtered_times = times[start_idx:end_idx]
        filtered_positions = positions[start_idx:end_idx]
        filtered_velocities = velocities[start_idx:end_idx]

        unique_indices = np.unique(filtered_times, return_index=True)[1]
        filtered_times = filtered_times[unique_indices]
        filtered_positions = filtered_positions[unique_indices]
        filtered_velocities = filtered_velocities[unique_indices]

        if len(filtered_times) < 2:
            raise ValueError(f"Too few points ({len(filtered_times)}) for interpolation")

        interp_times = np.arange(t_start, t_end + time_step, time_step)
        if self.interpolation_method == "chebyshev":
            degree = 30
            norm_times = 2 * (filtered_times - t_start) / (t_end - t_start) - 1
            norm_interp_times = 2 * (interp_times - t_start) / (t_end - t_start) - 1
            pos_polynomials = [chebyshev.Chebyshev.fit(norm_times, pos, degree) for pos in filtered_positions.T]
            vel_polynomials = [chebyshev.Chebyshev.fit(norm_times, vel, degree) for vel in filtered_velocities.T]
            self.interpolated_orbit = {
                "time_range": (t_start, t_end),
                "times": interp_times,
                "positions": np.array([poly(norm_interp_times) for poly in pos_polynomials]).T,
                "velocities": np.array([poly(norm_interp_times) for poly in vel_polynomials]).T
            }
        elif self.interpolation_method == "cubic_spline":
            self.interpolated_orbit = {
                "time_range": (t_start, t_end),
                "times": interp_times,
                "positions": np.array([CubicSpline(filtered_times, pos)(interp_times) for pos in filtered_positions.T]).T,
                "velocities": np.array([CubicSpline(filtered_times, vel)(interp_times) for vel in filtered_velocities.T]).T
            }
        else:  # linear
            self.interpolated_orbit = {
                "time_range": (t_start, t_end),
                "times": interp_times,
                "positions": np.array([np.interp(interp_times, filtered_times, pos) for pos in filtered_positions.T]).T,
                "velocities": np.array([np.interp(interp_times, filtered_times, vel) for vel in filtered_velocities.T]).T
            }
        logger.info(f"Interpolated orbit using {self.interpolation_method}")

    def get_pitch_range(self) -> Tuple[float, float]:
        """Retrieve the pitch range."""
        return self.pitch_range
    
    def get_yaw_range(self) -> Tuple[float, float]:
        """Retrieve the yaw range."""
        return self.yaw_range

    def get_state_vector(self, time: Time) -> Tuple[np.ndarray, np.ndarray]:
        """Retrieve position and velocity vectors at a specific time."""
        if self.use_kep:
            return self.get_state_vector_from_kepler(time)
        return self.get_state_vector_from_orbit(time)

    def get_state_vector_from_kepler(self, time: Time) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate state vector from Keplerian elements at a specific time."""
        if self.kepler_elements is None:
            raise ValueError("No Keplerian elements set")
        a, e, i, raan, argp, nu0, epoch, mu = (
            self.kepler_elements[k] for k in ["a", "e", "i", "raan", "argp", "nu", "epoch", "mu"]
        )
        t = (time - epoch).sec
        M = np.sqrt(mu / a**3) * t + self._solve_kepler(nu0, e)
        E = self._solve_kepler(M, e)
        nu = 2 * np.arctan2(np.sqrt(1 + e) * np.sin(E / 2), np.sqrt(1 - e) * np.cos(E / 2))
        r = a * (1 - e * np.cos(E))
        p = a * (1 - e**2)
        h = np.sqrt(mu * p)
        pos_p = np.array([r * np.cos(nu), r * np.sin(nu), 0])
        vel_p = np.array([-np.sin(nu), e + np.cos(nu), 0]) * (h / p)
        R1 = np.array([[np.cos(raan), -np.sin(raan), 0], [np.sin(raan), np.cos(raan), 0], [0, 0, 1]])
        R2 = np.array([[1, 0, 0], [0, np.cos(i), -np.sin(i)], [0, np.sin(i), np.cos(i)]])
        R3 = np.array([[np.cos(argp), -np.sin(argp), 0], [np.sin(argp), np.cos(argp), 0], [0, 0, 1]])
        R = R1 @ R2 @ R3
        pos = R @ pos_p
        vel = R @ vel_p
        logger.debug(f"Calculated position={pos}, velocity={vel} at {time.isot}")
        return pos, vel

    def get_state_vector_from_orbit(self, time: Time) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate state vector from orbit data or interpolated orbit at a specific time."""
        if self.orbit_data is None:
            raise ValueError("No orbit data defined")
        j2000_epoch = Time("2000-01-01T12:00:00", scale='utc')
        t = (time - j2000_epoch).sec
        if self.interpolated_orbit and "time_range" in self.interpolated_orbit:
            t_min, t_max = self.interpolated_orbit["time_range"]
            interp_times = self.interpolated_orbit["times"]
            if t_min <= t <= t_max:
                idx = np.searchsorted(interp_times, t)
                if idx == 0:
                    pos = self.interpolated_orbit["positions"][0]
                    vel = self.interpolated_orbit["velocities"][0]
                elif idx >= len(interp_times):
                    pos = self.interpolated_orbit["positions"][-1]
                    vel = self.interpolated_orbit["velocities"][-1]
                else:
                    frac = (t - interp_times[idx - 1]) / (interp_times[idx] - interp_times[idx - 1])
                    pos = (1 - frac) * self.interpolated_orbit["positions"][idx - 1] + frac * self.interpolated_orbit["positions"][idx]
                    vel = (1 - frac) * self.interpolated_orbit["velocities"][idx - 1] + frac * self.interpolated_orbit["velocities"][idx]
                logger.debug(f"Interpolated state vector at {time.isot}: pos={pos}, vel={vel}")
                return pos, vel
        times = self.orbit_data["times"]
        if t < times[0] or t > times[-1]:
            logger.warning(f"Time {time.isot} outside orbit data range")
            return np.array([self.x, self.y, self.z]), np.array([self.vx, self.vy, self.vz])
        pos_idx = np.searchsorted(times, t)
        t1, t2 = times[pos_idx - 1], times[pos_idx]
        pos1, pos2 = self.orbit_data["positions"][pos_idx - 1], self.orbit_data["positions"][pos_idx]
        vel1, vel2 = self.orbit_data["velocities"][pos_idx - 1], self.orbit_data["velocities"][pos_idx]
        frac = (t - t1) / (t2 - t1)
        pos = pos1 + (pos2 - pos1) * frac
        vel = vel1 + (vel2 - vel1) * frac
        logger.debug(f"Calculated state vector at {time.isot}: pos={pos}, vel={vel}")
        return pos, vel

    def set_keplerian(self, a: float, e: float, i: float, raan: float, argp: float, nu: float, epoch: Time, mu: float = 398600.4418e9) -> None:
        """Set Keplerian elements for orbit calculation."""
        kepler_elements = {
            "a": a, "e": e, "i": i, "raan": raan, "argp": argp, "nu": nu,
            "epoch": epoch, "mu": mu
        }
        self._validate_kepler_elements(kepler_elements)
        self.set({"kepler_elements": kepler_elements, "orbit_data": None, "use_kep": True})
        logger.info("Set Keplerian elements")
    
    def _solve_kepler(self, initial: float, e: float, tol: float = 1e-8, max_iter: int = 200) -> float:
        """Solve Kepler's equation iteratively to find the eccentric anomaly.

        Args:
            initial (float): Initial guess for mean anomaly (radians).
            e (float): Orbital eccentricity (must be < 1 for elliptical orbits).
            tol (float): Convergence tolerance. Defaults to 1e-8.
            max_iter (int): Maximum number of iterations. Defaults to 200.

        Returns:
            float: Eccentric anomaly (radians).

        Raises:
            ValueError: If eccentricity is >= 1 (non-elliptical orbit).
        """
        if e >= 1:
            raise ValueError("Eccentricity must be < 1 for elliptical orbit")
        x = initial if e < 0.9 else np.pi
        for _ in range(max_iter):
            f = x - e * np.sin(x) - initial
            df = 1 - e * np.cos(x)
            dx = -f / df
            x += dx
            if abs(dx) < tol:
                return x
        logger.warning(f"Kepler's equation did not converge for e={e}, initial={initial}")
        return x

    def to_dict(self) -> dict:
        """Convert the SpaceTelescope object to a dictionary for serialization.

        Excludes orbit_data to prevent storing temporary in-memory data.
        """
        data = super().to_dict()
        for key in ["x", "y", "z", "vx", "vy", "vz"]:
            data.pop(key, None)
        data.update({
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
            "interpolation_method": self.interpolation_method,
            "interpolated_orbit": None if self.interpolated_orbit is None else {
                "time_range": list(self.interpolated_orbit["time_range"]),
                "times": self.interpolated_orbit["times"].tolist(),
                "positions": self.interpolated_orbit["positions"].tolist(),
                "velocities": self.interpolated_orbit["velocities"].tolist()
            }
        })
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'SpaceTelescope':
        """Create a SpaceTelescope object from a dictionary.

        Loads orbit_data from orbit_file if provided, otherwise uses kepler_elements.
        """
        data = data.copy()
        
        # Handle Telescope attributes
        for table in ["sefd_table", "surface_efficiency_table", "effective_area_table", "system_temperature_table"]:
            if table in data and isinstance(data[table], dict):
                data[table] = {float(k): v for k, v in data[table].items()}
        
        # Convert lists to tuples for ranges
        if "elevation_range" in data and isinstance(data["elevation_range"], (list, tuple)):
            data["elevation_range"] = tuple(data["elevation_range"])
        if "azimuth_range" in data and isinstance(data["azimuth_range"], (list, tuple)):
            data["azimuth_range"] = tuple(data["azimuth_range"])
        if "pitch_range" in data and isinstance(data["pitch_range"], (list, tuple)):
            data["pitch_range"] = tuple(data["pitch_range"])
        if "yaw_range" in data and isinstance(data["yaw_range"], (list, tuple)):
            data["yaw_range"] = tuple(data["yaw_range"])
        
        # Handle mount_type
        if "mount_type" in data and isinstance(data["mount_type"], str):
            try:
                data["mount_type"] = MountType(data["mount_type"].upper())
            except ValueError:
                raise ValueError(f"Invalid mount_type in data: {data['mount_type']}")
        
        # Handle Keplerian elements
        if "kepler_elements" in data and data["kepler_elements"] is not None:
            kepler = data["kepler_elements"]
            data["kepler_elements"] = {
                "a": kepler["a"],
                "e": kepler["e"],
                "i": kepler["i"],
                "raan": kepler["raan"],
                "argp": kepler["argp"],
                "nu": kepler["nu"],
                "epoch": Time(kepler["epoch"], scale='utc'),
                "mu": kepler["mu"]
            }
        
        # Handle interpolated orbit
        if "interpolated_orbit" in data and data["interpolated_orbit"] is not None:
            interp_orbit = data["interpolated_orbit"]
            data["interpolated_orbit"] = {
                "time_range": tuple(interp_orbit["time_range"]),
                "times": np.array(interp_orbit["times"]),
                "positions": np.array(interp_orbit["positions"]),
                "velocities": np.array(interp_orbit["velocities"])
            }
        
        # Define valid parameters for SpaceTelescope.__init__
        valid_init_params = {
            "code", "name", "type", "orbit_file", "diameter", "sefd_table", "pitch_range", "yaw_range",
            "isactive", "use_kep", "kepler_elements", "interpolation_method",
            "surface_accuracy", "surface_efficiency_table", "effective_area_table", "system_temperature_table",
            "interpolated_orbit"
        }
        
        # Filter data to include only valid parameters
        init_data = {k: v for k, v in data.items() if k in valid_init_params}
        
        # Set defaults for required fields
        init_data.setdefault("name", f"stlsc_{uuid.uuid4().hex[:32]}")
        init_data.setdefault("code", data.get("code", "TS"))
        init_data.setdefault("type", "SpaceTelescope")
        init_data.setdefault("orbit_file", "dummy_orbit.oem")
        init_data.setdefault("diameter", 1.0)
        init_data.setdefault("sefd_table", {})
        init_data.setdefault("pitch_range", (-90.0, 90.0))
        init_data.setdefault("yaw_range", (-180.0, 180.0))
        init_data.setdefault("isactive", True)
        init_data.setdefault("use_kep", True)
        init_data.setdefault("kepler_elements", None)
        init_data.setdefault("interpolation_method", "linear")
        init_data.setdefault("surface_accuracy", None)
        init_data.setdefault("surface_efficiency_table", {})
        init_data.setdefault("effective_area_table", {})
        init_data.setdefault("system_temperature_table", {})
        init_data.setdefault("interpolated_orbit", None)
        
        # Create instance
        instance = cls(**init_data)
        
        # Load orbit data from file if provided and exists
        if not instance.use_kep and instance.orbit_file and os.path.isfile(instance.orbit_file):
            try:
                instance.load_orbit(instance.orbit_file)
                logger.info(f"Loaded orbit data from '{instance.orbit_file}' during deserialization")
            except FileNotFoundError:
                logger.warning(f"Orbit file '{instance.orbit_file}' not found during deserialization")
                instance.orbit_data = None
        
        return instance