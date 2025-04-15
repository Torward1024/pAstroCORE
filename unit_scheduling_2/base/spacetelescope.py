from unit_scheduling_2.base.telescope import Telescope
from common.utils.validation import check_type, check_non_empty_string, check_positive, check_range
from common.utils.logging_setup import logger
import numpy as np
from scipy.interpolate import CubicSpline
from numpy.polynomial import chebyshev
import re
from typing import Optional, Dict, Tuple
from astropy.time import Time

class SpaceTelescope(Telescope):
    """Class representing a space-based telescope with orbital parameters and SEFD properties.

    Inherits from Telescope, setting mount_type to 'NONE'. Adds orbital data (via file, direct data, or Keplerian elements),
    pitch and yaw ranges, and interpolation methods (linear, Chebyshev, or cubic spline) for orbit calculations.
    Provides state vector (position and velocity) retrieval at specific times.

    Attributes:
        _orbit_file (str): Path to the orbit file (e.g., CSDSS OEM 2.0 format).
        _pitch_range (Tuple[float, float]): Minimum and maximum pitch angles in degrees.
        _yaw_range (Tuple[float, float]): Minimum and maximum yaw angles in degrees.
        _use_kep (bool): Flag indicating if Keplerian elements are used instead of orbit data.
        _orbit_data (Optional[Dict[str, np.ndarray]]): Orbit data with times, positions, and velocities.
        _kepler_elements (Optional[dict]): Keplerian elements (a, e, i, raan, argp, nu, epoch, mu).
        _interpolation_method (str): Method for orbit interpolation ('linear', 'chebyshev', or 'cubic_spline').
        _interpolated_orbit (Optional[dict]): Precomputed interpolated orbit data.

    Notes:
        - Orbital data can be loaded from a file, set directly, or derived from Keplerian elements.
        - State vectors are calculated using Keplerian elements if `_use_kep` is True, otherwise from orbit data.
        - Interpolation is supported for non-Keplerian orbits over a specified time range.
        - Logging is integrated via `common.utils.logging_setup.logger`.

    Examples:
        >>> st = SpaceTelescope(code="HST", name="Hubble", orbit_file="hst_orbit.oem", diameter=2.4)
        >>> st.load_orbit("hst_orbit.oem")  # Assuming valid OEM file
        >>> time = Time("2025-04-06T12:00:00", scale='utc')
        >>> pos, vel = st.get_state_vector(time)
        >>> st.set_interpolation_method("cubic_spline")
        >>> st.interpolate_orbit(Time("2025-04-06T00:00:00"), Time("2025-04-06T23:59:59"), 3600.0)
    """
    def __init__(self, code: str = "TEMP_SPACE", name: str = "Temporary Space Telescope",
                 orbit_file: str = "dummy_orbit.oem", diameter: float = 1.0,
                 sefd_table: Optional[Dict[float, float]] = None,
                 pitch_range: Tuple[float, float] = (-90.0, 90.0),
                 yaw_range: Tuple[float, float] = (-180.0, 180.0),
                 isactive: bool = True, use_kep: bool = True,
                 kepler_elements: Optional[dict] = None,
                 orbit_data: Optional[Dict[str, np.ndarray]] = None,
                 interpolation_method: str = "linear",
                 surface_accuracy: Optional[float] = None,
                 surface_efficiency_table: Optional[Dict[float, float]] = None,
                 effective_area_table: Optional[Dict[float, float]] = None,
                 system_temperature_table: Optional[Dict[float, float]] = None):
        """Initialize a SpaceTelescope with orbital parameters and optional SEFD properties.

        Args:
            code (str): Unique short name. Defaults to "TEMP_SPACE".
            name (str): Full name. Defaults to "Temporary Space Telescope".
            orbit_file (str): Path to orbit file. Defaults to "dummy_orbit.oem".
            diameter (float): Antenna diameter in meters. Must be positive. Defaults to 1.0.
            sefd_table (Optional[Dict[float, float]]): SEFD table (MHz: Jy). Defaults to None.
            pitch_range (Tuple[float, float]): Min and max pitch in degrees. Defaults to (-90.0, 90.0).
            yaw_range (Tuple[float, float]): Min and max yaw in degrees. Defaults to (-180.0, 180.0).
            isactive (bool): Whether the telescope is active. Defaults to True.
            use_kep (bool): Use Keplerian elements if True, orbit data if False. Defaults to True.
            kepler_elements (Optional[dict]): Keplerian elements. Defaults to None.
            orbit_data (Optional[Dict[str, np.ndarray]]): Direct orbit data. Defaults to None.
            interpolation_method (str): Orbit interpolation method. Defaults to "linear".

        Raises:
            TypeError: If inputs are of incorrect type.
            ValueError: If diameter is not positive, ranges are invalid, or Keplerian elements are incomplete/invalid.
        """
        super().__init__(code=code, name=name, x=0.0, y=0.0, z=0.0, vx=0.0, vy=0.0, vz=0.0, 
                         diameter=diameter, sefd_table=sefd_table, isactive=isactive,
                         mount_type="NONE", surface_accuracy=surface_accuracy,
                         surface_efficiency_table=surface_efficiency_table,
                         effective_area_table=effective_area_table,
                         system_temperature_table=system_temperature_table)
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

        if orbit_data is not None:  
            self.set_orbit(orbit_data)
            self._use_kep = False  
            logger.info(f"Initialized SpaceTelescope '{code}' with direct orbit data, diameter={diameter} m")
        elif self._use_kep:
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
        """Load orbital data from a CSDSS OEM 2.0 styled file.

        Parses time, position (km), and velocity (km/s) data, converting to meters and meters/s.

        Args:
            orbit_file (str): Path to the orbit file.

        Raises:
            TypeError: If orbit_file is not a string.
            ValueError: If file format is invalid or contains fewer than 2 data points.
            FileNotFoundError: If the file does not exist.
        """
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

    def get_orbit(self) -> Optional[Dict[str, np.ndarray]]:
        """Retrieve the current orbit data.

        Returns:
            Optional[Dict[str, np.ndarray]]: Dictionary with 'times', 'positions', and 'velocities', or None if not set.
        """
        if self._orbit_data is not None:
            logger.info(f"Retrieved orbit data for SpaceTelescope '{self._code}': {len(self._orbit_data['times'])} points")
            return {
                "times": self._orbit_data["times"].copy(),
                "positions": self._orbit_data["positions"].copy(),
                "velocities": self._orbit_data["velocities"].copy()
            }
        logger.warning(f"No orbit data available for SpaceTelescope '{self._code}'")
        return None

    def set_orbit(self, orbit_data: Dict[str, np.ndarray]) -> None:
        """Set orbit data directly with times, positions, and velocities.

        Args:
            orbit_data (Dict[str, np.ndarray]): Dictionary with 'times' (sec), 'positions' (m), and 'velocities' (m/s).

        Raises:
            TypeError: If orbit_data is not a dict or contains invalid array types.
            ValueError: If arrays are incorrectly shaped, times are not increasing, or lengths mismatch.
        """
        check_type(orbit_data, dict, "Orbit data")
        required_keys = {"times", "positions", "velocities"}
        if not required_keys.issubset(orbit_data.keys()):
            raise ValueError(f"Orbit data must contain keys: {required_keys}")
        
        times = np.asarray(orbit_data["times"])
        positions = np.asarray(orbit_data["positions"])
        velocities = np.asarray(orbit_data["velocities"])

        if times.ndim != 1:
            raise ValueError("Times must be a 1D array")
        if positions.ndim != 2 or positions.shape[1] != 3:
            raise ValueError("Positions must be a 2D array with shape (N, 3)")
        if velocities.ndim != 2 or velocities.shape[1] != 3:
            raise ValueError("Velocities must be a 2D array with shape (N, 3)")
        if not (len(times) == positions.shape[0] == velocities.shape[0]):
            raise ValueError("Times, positions, and velocities must have the same length")

        if not np.all(np.diff(times) > 0):
            raise ValueError("Times must be in strictly increasing order")

        self._orbit_data = {
            "times": times.copy(),
            "positions": positions.copy(),
            "velocities": velocities.copy()
        }
        self._use_kep = False
        self._kepler_elements = None
        self._interpolated_orbit = None
        self._orbit_file = None
        logger.info(f"Set orbit data for SpaceTelescope '{self._code}' with {len(times)} points")

    def set_interpolation_method(self, method: str) -> None:
        """Set the interpolation method for orbit data.

        Args:
            method (str): Interpolation method ('linear', 'chebyshev', or 'cubic_spline').

        Raises:
            ValueError: If method is not one of the valid options.
        """
        valid_methods = {"linear", "chebyshev", "cubic_spline"}
        if method not in valid_methods:
            raise ValueError(f"Interpolation method must be one of {valid_methods}, got {method}")
        self._interpolation_method = method
        self._interpolated_orbit = None
        logger.info(f"Set interpolation method to '{method}' for SpaceTelescope '{self._code}'")

    def interpolate_orbit(self, start_time: Time, end_time: Time, time_step: float) -> None:
        """Interpolate orbit data over a time range using the specified method.

        Args:
            start_time (Time): Start time of interpolation (astropy Time object).
            end_time (Time): End time of interpolation (astropy Time object).
            time_step (float): Time step in seconds between interpolated points.

        Raises:
            ValueError: If no orbit data is loaded, time range is outside data, or too few points remain after filtering.
        """
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
            degree = 30  # degree of Chebyshev polynomial
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
        """Retrieve position and velocity vectors at a specific time.

        Uses Keplerian elements if `_use_kep` is True, otherwise interpolates from orbit data.

        Args:
            time (Time): Time at which to calculate the state vector (astropy Time object).

        Returns:
            tuple[np.ndarray, np.ndarray]: Position (m) and velocity (m/s) vectors, each with 3 elements.

        Raises:
            ValueError: If no orbit data or Keplerian elements are defined.
        """
        if self._use_kep:
            return self.get_state_vector_from_kepler(time)
        else:
            return self.get_state_vector_from_orbit(time)

    def get_state_vector_from_kepler(self, time: Time) -> tuple[np.ndarray, np.ndarray]:
        """Calculate state vector from Keplerian elements at a specific time.

        Args:
            time (Time): Time at which to calculate the state vector (astropy Time object).

        Returns:
            tuple[np.ndarray, np.ndarray]: Position (m) and velocity (m/s) vectors.

        Raises:
            ValueError: If no Keplerian elements are set or eccentricity is >= 1.
        """
        if self._kepler_elements is None:
            logger.error(f"No Keplerian elements set for '{self._code}'")
            raise ValueError("No Keplerian elements set!")
        a, e, i, raan, argp, nu0, epoch, mu = (
            self._kepler_elements[k] for k in ["a", "e", "i", "raan", "argp", "nu", "epoch", "mu"]
        )
        t = (time - epoch).sec
        M = np.sqrt(mu / a**3) * t + self._solve_kepler(nu0, e)  # mean anomaly
        E = self._solve_kepler(M, e)  # eccentric anomaly
        nu = 2 * np.arctan2(np.sqrt(1 + e) * np.sin(E / 2), np.sqrt(1 - e) * np.cos(E / 2))  # true anomaly
        r = a * (1 - e * np.cos(E))  # distance
        p = a * (1 - e**2)  # aemi-latus rectum
        h = np.sqrt(mu * p)  # angular momentum
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
        """Calculate state vector from orbit data or interpolated orbit at a specific time.

        Falls back to raw data interpolation if no precomputed interpolation exists.

        Args:
            time (Time): Time at which to calculate the state vector (astropy Time object).

        Returns:
            tuple[np.ndarray, np.ndarray]: Position (m) and velocity (m/s) vectors.

        Raises:
            ValueError: If no orbit data is defined.
        """
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
        """Retrieve the Keplerian elements.

        Returns:
            Optional[Dict[str, any]]: Dictionary of Keplerian elements, or None if not set.
        """
        if self._kepler_elements is not None:
            logger.debug(f"Retrieved Keplerian elements for SpaceTelescope '{self._code}': {self._kepler_elements}")
            return self._kepler_elements.copy()
        logger.debug(f"No Keplerian elements set for SpaceTelescope '{self._code}'")
        return None

    def get_pitch_range(self) -> Tuple[float, float]:
        """Retrieve the pitch range.

        Returns:
            Tuple[float, float]: A tuple of (min, max) pitch angles in degrees.
        """
        return self._pitch_range

    def get_yaw_range(self) -> Tuple[float, float]:
        """Retrieve the yaw range.

        Returns:
            Tuple[float, float]: A tuple of (min, max) yaw angles in degrees.
        """
        return self._yaw_range
    
    def get_use_kep(self) -> bool:
        """Retrieve the Keplerian usage flag.

        Returns:
            bool: True if using Keplerian elements, False if using orbit data.
        """
        return self._use_kep
    
    def set_telescope(self, code: str, name: str, orbit_file: str, diameter: float,
                      sefd_table: Optional[Dict[float, float]] = None,
                      pitch_range: Tuple[float, float] = (-90.0, 90.0),
                      yaw_range: Tuple[float, float] = (-180.0, 180.0),
                      isactive: bool = True, use_kep: bool = True,
                      kepler_elements: Optional[dict] = None,
                      orbit_data: Optional[Dict[str, np.ndarray]] = None,
                      interpolation_method: str = "chebyshev",
                      surface_accuracy: Optional[float] = None,
                      surface_efficiency_table: Optional[Dict[float, float]] = None,
                      effective_area_table: Optional[Dict[float, float]] = None,
                      system_temperature_table: Optional[Dict[float, float]] = None) -> None:
        """Set all properties of the space telescope.

        Args:
            code (str): Unique short name.
            name (str): Full name.
            orbit_file (str): Path to orbit file.
            diameter (float): Antenna diameter in meters. Must be positive.
            sefd_table (Optional[Dict[float, float]]): SEFD table (MHz: Jy). Defaults to None.
            pitch_range (Tuple[float, float]): Min and max pitch in degrees. Defaults to (-90.0, 90.0).
            yaw_range (Tuple[float, float]): Min and max yaw in degrees. Defaults to (-180.0, 180.0).
            isactive (bool): Whether the telescope is active. Defaults to True.
            use_kep (bool): Use Keplerian elements if True. Defaults to True.
            kepler_elements (Optional[dict]): Keplerian elements. Defaults to None.
            orbit_data (Optional[Dict[str, np.ndarray]]): Direct orbit data. Defaults to None.
            interpolation_method (str): Orbit interpolation method. Defaults to "chebyshev".

        Raises:
            TypeError: If inputs are of incorrect type.
            ValueError: If diameter is not positive, ranges are invalid, or Keplerian elements are incomplete/invalid.
        """
        super().set_telescope(code=code, name=name, x=0.0, y=0.0, z=0.0, vx=0.0, vy=0.0, vz=0.0,
                              diameter=diameter, sefd_table=sefd_table, mount_type="NONE", isactive=isactive,
                              surface_accuracy=surface_accuracy,
                              surface_efficiency_table=surface_efficiency_table,
                              effective_area_table=effective_area_table,
                              system_temperature_table=system_temperature_table)
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

        if orbit_data is not None:
            self.set_orbit(orbit_data)
            self._use_kep = False
        elif self._use_kep:
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
        """Set Keplerian elements for orbit calculation.

        Args:
            a (float): Semi-major axis in meters. Must be positive.
            e (float): Eccentricity (0 to 1).
            i (float): Inclination in degrees.
            raan (float): Right Ascension of the Ascending Node in degrees.
            argp (float): Argument of periapsis in degrees.
            nu (float): True anomaly in degrees.
            epoch (Time): Epoch time (astropy Time object).
            mu (float): Gravitational parameter in m^3/s^2. Defaults to Earth's value (398600.4418e9).

        Raises:
            TypeError: If inputs are of incorrect type.
            ValueError: If a is not positive, e is not in [0, 1), or mu is not positive.
        """
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
        """Set the pitch range.

        Args:
            pitch_range (Tuple[float, float]): A tuple of (min, max) pitch angles in degrees.

        Raises:
            TypeError: If pitch_range is not a tuple or contains non-numeric values.
            ValueError: If tuple does not contain exactly 2 values or range is invalid (min < -90 or max > 90 or min > max).
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
        """Set the yaw range.

        Args:
            yaw_range (Tuple[float, float]): A tuple of (min, max) yaw angles in degrees.

        Raises:
            TypeError: If yaw_range is not a tuple or contains non-numeric values.
            ValueError: If tuple does not contain exactly 2 values or range is invalid (min < -180 or max > 180 or min > max).
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
        """Set the Keplerian usage flag.

        Args:
            use_kep (bool): True to use Keplerian elements, False to use orbit data.

        Raises:
            TypeError: If use_kep is not a boolean.
        """
        check_type(use_kep, bool, "Use Keplerian flag")
        self._use_kep = use_kep
        logger.info(f"Set use_keplerian={use_kep} for SpaceTelescope '{self._code}'")

    def to_dict(self) -> dict:
        """Convert the SpaceTelescope object to a dictionary for serialization.

        Returns:
            dict: A dictionary containing all space telescope properties, including orbit and Keplerian data.
        """
        base_dict = super().to_dict()
        orbit_dict = self.get_orbit()
        base_dict.update({
            "type": "SpaceTelescope",
            "orbit_file": self._orbit_file,
            "pitch_range": self._pitch_range,
            "yaw_range": self._yaw_range,
            "use_kep": self._use_kep,
            "kepler_elements": None if self._kepler_elements is None else {
                "a": self._kepler_elements["a"],
                "e": self._kepler_elements["e"],
                "i": np.degrees(self._kepler_elements["i"]),
                "raan": np.degrees(self._kepler_elements["raan"]),
                "argp": np.degrees(self._kepler_elements["argp"]),
                "nu": np.degrees(self._kepler_elements["nu"]),
                "epoch": self._kepler_elements["epoch"].isot,
                "mu": self._kepler_elements["mu"]
            },
            "orbit_data": orbit_dict
        })
        logger.info(f"Converted SpaceTelescope '{self._code}' to dictionary")
        return base_dict

    @classmethod
    def from_dict(cls, data: dict) -> 'SpaceTelescope':
        """Create a SpaceTelescope object from a dictionary.

        Args:
            data (dict): Dictionary containing space telescope properties, typically from `to_dict`.

        Returns:
            SpaceTelescope: A new SpaceTelescope instance initialized with the dictionary data.
        """
        obj = cls(
            code=data["code"],
            name=data["name"],
            orbit_file=data["orbit_file"],
            diameter=data["diameter"],
            sefd_table=data.get("sefd_table", {}),
            pitch_range=tuple(data.get("pitch_range", (-90.0, 90.0))),
            yaw_range=tuple(data.get("yaw_range", (-180.0, 180.0))),
            isactive=data.get("isactive", True),
            use_kep=data.get("use_kep", True),
            kepler_elements=data.get("kepler_elements"),
            orbit_data=data.get("orbit_data"),
            surface_accuracy=data.get("surface_accuracy"),
            surface_efficiency_table=data.get("surface_efficiency_table"),
            effective_area_table=data.get("effective_area_table"),
            system_temperature_table=data.get("system_temperature_table")
        )
        if data.get("kepler_elements") and not data.get("orbit_data"):
            obj._kepler_elements = {
                "a": data["kepler_elements"]["a"],
                "e": data["kepler_elements"]["e"],
                "i": np.radians(data["kepler_elements"]["i"]),
                "raan": np.radians(data["kepler_elements"]["raan"]),
                "argp": np.radians(data["kepler_elements"]["argp"]),
                "nu": np.radians(data["kepler_elements"]["nu"]),
                "epoch": Time(data["kepler_elements"]["epoch"], scale='utc'),
                "mu": data["kepler_elements"]["mu"]
            }
        if obj._orbit_file and not data.get("orbit_data"):
            try:
                obj.load_orbit(obj._orbit_file)
            except (FileNotFoundError, ValueError) as e:
                logger.warning(f"Could not load orbit data from '{obj._orbit_file}' during deserialization: {e}")
        logger.info(f"Created SpaceTelescope '{data['code']}' from dictionary")
        return obj
    
    def _solve_kepler(self, initial: float, e: float, tol: float = 1e-8, max_iter: int = 200) -> float:
        """Solve Kepler's equation iteratively to find the eccentric anomaly.

        Args:
            initial (float): Initial mean anomaly or true anomaly guess in radians.
            e (float): Eccentricity (must be < 1).
            tol (float): Convergence tolerance. Defaults to 1e-8.
            max_iter (int): Maximum iterations. Defaults to 200.

        Returns:
            float: Eccentric anomaly in radians.

        Raises:
            ValueError: If eccentricity is >= 1 or convergence fails.
        """
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
        """Validate that orbit data or Keplerian elements are set.

        Returns:
            bool: True if either orbit data or Keplerian elements are defined, False otherwise.
        """
        return self._orbit_data is not None or self._kepler_elements is not None

    def __repr__(self) -> str:
        """Return a string representation of the SpaceTelescope object.

        Returns:
            str: A formatted string with code, name, orbit info, Keplerian status, diameter, ranges, and active status.
        """
        orbit_info = f"orbit_file='{self._orbit_file}'" if self._orbit_file else "no orbit loaded"
        kep_info = "kepler_elements_set" if self._kepler_elements else "no kepler elements"
        return (f"SpaceTelescope(code='{self._code}', name='{self._name}', "
                f"{orbit_info}, {kep_info}, diameter={self._diameter}, "
                f"pitch_range={self._pitch_range}, yaw_range={self._yaw_range}, isactive={self.isactive})")