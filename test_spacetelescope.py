import unittest
import numpy as np
from unittest.mock import mock_open, patch
from astropy.time import Time
from unit_scheduling_2.base.telescope import MountType
from unit_scheduling_2.base.spacetelescope import SpaceTelescope
from common.utils.logging_setup import logger

class TestSpaceTelescope(unittest.TestCase):
    def setUp(self):
        """Set up common test data and configurations."""
        base_time = Time("2025-04-15T12:00:00", scale='utc')
        j2000_epoch = Time("2000-01-01T12:00:00", scale='utc')
        time_offset = (base_time - j2000_epoch).sec
        self.valid_kepler_elements = {
            "a": 7000000.0,  # Semi-major axis in meters
            "e": 0.1,        # Eccentricity
            "i": np.radians(30.0),  # Inclination in radians
            "raan": np.radians(45.0),  # RAAN in radians
            "argp": np.radians(60.0),  # Argument of periapsis in radians
            "nu": np.radians(0.0),    # True anomaly in radians
            "epoch": base_time,
            "mu": 398600.4418e9  # Earth's gravitational parameter
        }
        self.valid_orbit_data = {
            "times": np.array([0.0, 3600.0, 7200.0]) + time_offset,
            "positions": np.array([[7000000.0, 0.0, 0.0], [6990000.0, 100000.0, 0.0], [6980000.0, 200000.0, 0.0]]),
            "velocities": np.array([[0.0, 7450.0, 0.0], [100.0, 7440.0, 0.0], [200.0, 7430.0, 0.0]])
        }
        self.oem_file_content = (
            "# CSDSS OEM 2.0 format\n"
            "META_START\n"
            "META_STOP\n"
            f"{base_time.isot} 7000.0 0.0 0.0 0.0 7.45 0.0\n"
            f"{(base_time + 3600.0).isot} 6990.0 100.0 0.0 0.1 7.44 0.0\n"
            "COVARIANCE_START\n"
        )

    def test_initialization_default(self):
        """Test default initialization of SpaceTelescope."""
        st = SpaceTelescope()
        self.assertEqual(st.code, "TEMP_SPACE")
        self.assertEqual(st.name, "Temporary Space Telescope")
        self.assertEqual(st._orbit_file, "dummy_orbit.oem")
        self.assertEqual(st.diameter, 1.0)
        self.assertEqual(st._pitch_range, (-90.0, 90.0))
        self.assertEqual(st._yaw_range, (-180.0, 180.0))
        self.assertTrue(st.isactive)
        self.assertTrue(st._use_kep)
        self.assertIsNone(st._kepler_elements)
        self.assertIsNone(st._orbit_data)
        self.assertEqual(st._interpolation_method, "linear")
        self.assertEqual(st.mount_type, MountType.SPACE)

    def test_initialization_with_kepler_elements(self):
        """Test initialization with valid Keplerian elements."""
        st = SpaceTelescope(
            code="HST", name="Hubble", diameter=2.4,
            kepler_elements=self.valid_kepler_elements, use_kep=True
        )
        self.assertEqual(st.code, "HST")
        self.assertEqual(st.name, "Hubble")
        self.assertEqual(st.diameter, 2.4)
        self.assertEqual(st._kepler_elements, self.valid_kepler_elements)
        self.assertTrue(st._use_kep)
        self.assertIsNone(st._orbit_data)

    def test_initialization_with_orbit_data(self):
        """Test initialization with valid orbit data."""
        st = SpaceTelescope(
            code="HST", name="Hubble", diameter=2.4,
            orbit_data=self.valid_orbit_data, use_kep=False
        )
        self.assertEqual(st.code, "HST")
        self.assertEqual(st.diameter, 2.4)
        self.assertEqual(st._orbit_data["times"].tolist(), self.valid_orbit_data["times"].tolist())
        self.assertFalse(st._use_kep)
        self.assertIsNone(st._kepler_elements)

    def test_invalid_orbit_file(self):
        """Test initialization with invalid orbit file string."""
        with self.assertRaises(TypeError):
            SpaceTelescope(orbit_file="")
        
        with self.assertLogs(logger, level='WARNING') as cm:
            st = SpaceTelescope(orbit_file=None)
            self.assertIn(
                "Initialized SpaceTelescope 'TEMP_SPACE' without orbit data or Keplerian elements",
                cm.output[0]
            )

    def test_invalid_diameter(self):
        """Test initialization with invalid diameter."""
        with self.assertRaises(TypeError):
            SpaceTelescope(diameter=0.0)
        with self.assertRaises(TypeError):
            SpaceTelescope(diameter=-1.0)

    def test_invalid_pitch_range(self):
        """Test initialization with invalid pitch range."""
        with self.assertRaises(ValueError):
            SpaceTelescope(pitch_range=(90.0, -90.0))
        with self.assertRaises(ValueError):
            SpaceTelescope(pitch_range=(-91.0, 90.0))
        with self.assertRaises(TypeError):
            SpaceTelescope(pitch_range=("a", "b"))

    def test_invalid_yaw_range(self):
        """Test initialization with invalid yaw range."""
        with self.assertRaises(ValueError):
            SpaceTelescope(yaw_range=(180.0, -180.0))
        with self.assertRaises(ValueError):
            SpaceTelescope(yaw_range=(-181.0, 180.0))
        with self.assertRaises(TypeError):
            SpaceTelescope(yaw_range=("a", "b"))

    def test_invalid_kepler_elements(self):
        """Test initialization with invalid Keplerian elements."""
        invalid_kep = self.valid_kepler_elements.copy()
        invalid_kep.pop("a")
        with self.assertRaises(ValueError):
            SpaceTelescope(kepler_elements=invalid_kep)
        invalid_kep = self.valid_kepler_elements.copy()
        invalid_kep["e"] = 1.0
        with self.assertRaises(ValueError):
            SpaceTelescope(kepler_elements=invalid_kep)

    def test_load_orbit_valid_file(self):
        """Test loading valid OEM orbit file."""
        with patch("builtins.open", mock_open(read_data=self.oem_file_content)):
            st = SpaceTelescope(code="HST")
            st.load_orbit("test.oem")
            self.assertIsNotNone(st._orbit_data)
            self.assertEqual(len(st._orbit_data["times"]), 2)
            self.assertFalse(st._use_kep)
            self.assertIsNone(st._kepler_elements)
            self.assertEqual(st._orbit_file, "test.oem")

    def test_load_orbit_file_not_found(self):
        """Test loading non-existent orbit file."""
        with self.assertRaises(FileNotFoundError):
            st = SpaceTelescope()
            st.load_orbit("nonexistent.oem")

    def test_load_orbit_invalid_format(self):
        """Test loading orbit file with invalid format."""
        invalid_content = (
            "# Invalid OEM\n"
            "META_START\n"
            "META_STOP\n"
            "2025-04-15T12:00:00.000 7000.0\n"  # Incomplete data
        )
        with patch("builtins.open", mock_open(read_data=invalid_content)):
            st = SpaceTelescope()
            with self.assertRaises(ValueError):
                st.load_orbit("invalid.oem")

    def test_set_orbit_valid(self):
        """Test setting valid orbit data."""
        st = SpaceTelescope(code="HST")
        st.set_orbit(self.valid_orbit_data)
        self.assertEqual(st._orbit_data["times"].tolist(), self.valid_orbit_data["times"].tolist())
        self.assertFalse(st._use_kep)
        self.assertIsNone(st._kepler_elements)
        self.assertIsNone(st._interpolated_orbit)

    def test_set_orbit_invalid(self):
        """Test setting invalid orbit data."""
        st = SpaceTelescope()
        invalid_data = self.valid_orbit_data.copy()
        invalid_data["times"] = np.array([7200.0, 3600.0, 0.0])  # Not increasing
        with self.assertRaises(ValueError):
            st.set_orbit(invalid_data)
        invalid_data = self.valid_orbit_data.copy()
        invalid_data["positions"] = np.array([[7000000.0, 0.0]])  # Wrong shape
        with self.assertRaises(ValueError):
            st.set_orbit(invalid_data)

    def test_set_interpolation_method(self):
        """Test setting valid and invalid interpolation methods."""
        st = SpaceTelescope()
        st.set_interpolation_method("cubic_spline")
        self.assertEqual(st._interpolation_method, "cubic_spline")
        st.set_interpolation_method("chebyshev")
        self.assertEqual(st._interpolation_method, "chebyshev")
        with self.assertRaises(ValueError):
            st.set_interpolation_method("invalid")

    def test_interpolate_orbit_linear(self):
        """Test orbit interpolation with linear method."""
        st = SpaceTelescope(code="HST")
        st.set_orbit(self.valid_orbit_data)
        start_time = Time("2025-04-15T12:00:00", scale='utc')
        end_time = Time("2025-04-15T14:00:00", scale='utc')
        st.set_interpolation_method("linear")
        st.interpolate_orbit(start_time, end_time, 1800.0)
        self.assertIsNotNone(st._interpolated_orbit)
        self.assertEqual(len(st._interpolated_orbit["times"]), 5)
        pos = st._interpolated_orbit["positions"]
        self.assertTrue(np.allclose(pos[0], [7000000.0, 0.0, 0.0], atol=1e-3))

    def test_interpolate_orbit_cubic_spline(self):
        """Test orbit interpolation with cubic spline method."""
        st = SpaceTelescope(code="HST")
        st.set_orbit(self.valid_orbit_data)
        start_time = Time("2025-04-15T12:00:00", scale='utc')
        end_time = Time("2025-04-15T14:00:00", scale='utc')
        st.set_interpolation_method("cubic_spline")
        st.interpolate_orbit(start_time, end_time, 1800.0)
        self.assertIsNotNone(st._interpolated_orbit)
        pos = st._interpolated_orbit["positions"]
        self.assertTrue(np.allclose(pos[0], [7000000.0, 0.0, 0.0], atol=1e-3))

    def test_interpolate_orbit_chebyshev(self):
        """Test orbit interpolation with Chebyshev method."""
        st = SpaceTelescope(code="HST")
        st.set_orbit(self.valid_orbit_data)
        start_time = Time("2025-04-15T12:00:00", scale='utc')
        end_time = Time("2025-04-15T14:00:00", scale='utc')
        st.set_interpolation_method("chebyshev")
        st.interpolate_orbit(start_time, end_time, 1800.0)
        self.assertIsNotNone(st._interpolated_orbit)
        pos = st._interpolated_orbit["positions"]
        self.assertTrue(np.allclose(pos[0], [7000000.0, 0.0, 0.0], atol=1e-2))

    def test_interpolate_orbit_no_data(self):
        """Test interpolation with no orbit data."""
        st = SpaceTelescope(use_kep=False)
        start_time = Time("2025-04-15T12:00:00", scale='utc')
        end_time = Time("2025-04-15T14:00:00", scale='utc')
        with self.assertRaises(ValueError):
            st.interpolate_orbit(start_time, end_time, 1800.0)

    def test_interpolate_orbit_kepler(self):
        """Test interpolation attempt with Keplerian elements."""
        st = SpaceTelescope(kepler_elements=self.valid_kepler_elements, use_kep=True)
        start_time = Time("2025-04-15T12:00:00", scale='utc')
        end_time = Time("2025-04-15T14:00:00", scale='utc')
        with self.assertLogs(logger, level='INFO') as cm:
            st.interpolate_orbit(start_time, end_time, 1800.0)
            self.assertIn("Using Keplerian elements, skipping interpolation", cm.output[0])

    def test_get_state_vector_kepler(self):
        """Test state vector calculation using Keplerian elements."""
        st = SpaceTelescope(kepler_elements=self.valid_kepler_elements, use_kep=True)
        time = Time("2025-04-15T12:00:00", scale='utc')
        pos, vel = st.get_state_vector(time)
        self.assertEqual(pos.shape, (3,))
        self.assertEqual(vel.shape, (3,))
        expected_pos_norm = np.sqrt(7000000.0**2 * (1 - 0.1**2))
        self.assertAlmostEqual(np.linalg.norm(pos), expected_pos_norm, delta=1000)

    def test_get_state_vector_orbit(self):
        """Test state vector calculation using orbit data."""
        st = SpaceTelescope(code="HST")
        st.set_orbit(self.valid_orbit_data)
        time = Time("2025-04-15T12:30:00", scale='utc')
        pos, vel = st.get_state_vector(time)
        self.assertTrue(np.allclose(pos, [6995000.0, 50000.0, 0.0], atol=1e-3))
        self.assertTrue(np.allclose(vel, [50.0, 7445.0, 0.0], atol=1e-3))

    def test_get_state_vector_interpolated(self):
        """Test state vector calculation using interpolated orbit."""
        st = SpaceTelescope(code="HST")
        st.set_orbit(self.valid_orbit_data)
        start_time = Time("2025-04-15T12:00:00", scale='utc')
        end_time = Time("2025-04-15T14:00:00", scale='utc')
        st.set_interpolation_method("linear")
        st.interpolate_orbit(start_time, end_time, 1800.0)
        time = Time("2025-04-15T12:30:00", scale='utc')
        pos, vel = st.get_state_vector(time)
        self.assertTrue(np.allclose(pos, [6995000.0, 50000.0, 0.0], atol=1e-3))

    def test_get_state_vector_no_data(self):
        """Test state vector retrieval with no orbit data or Kepler elements."""
        st = SpaceTelescope(use_kep=False)
        time = Time("2025-04-15T12:00:00", scale='utc')
        with self.assertRaises(ValueError):
            st.get_state_vector(time)

    def test_set_keplerian(self):
        """Test setting Keplerian elements."""
        st = SpaceTelescope()
        st.set_keplerian(
            a=7000000.0, e=0.1, i=np.radians(30.0), raan=np.radians(45.0),
            argp=np.radians(60.0), nu=np.radians(0.0),
            epoch=Time("2025-04-15T12:00:00", scale='utc'), mu=398600.4418e9
        )
        self.assertEqual(st._kepler_elements["a"], 7000000.0)
        self.assertTrue(st._use_kep)
        self.assertIsNone(st._orbit_data)

    def test_set_keplerian_invalid(self):
        """Test setting invalid Keplerian elements."""
        st = SpaceTelescope()
        with self.assertRaises(ValueError):
            st.set_keplerian(
                a=0.0, e=0.1, i=np.radians(30.0), raan=np.radians(45.0),
                argp=np.radians(60.0), nu=np.radians(0.0),
                epoch=Time("2025-04-15T12:00:00", scale='utc'), mu=398600.4418e9
            )
        with self.assertRaises(ValueError):
            st.set_keplerian(
                a=7000000.0, e=1.0, i=np.radians(30.0), raan=np.radians(45.0),
                argp=np.radians(60.0), nu=np.radians(0.0),
                epoch=Time("2025-04-15T12:00:00", scale='utc'), mu=398600.4418e9
            )

    def test_to_dict_from_dict(self):
        """Test serialization and deserialization."""
        st = SpaceTelescope(
            code="HST", name="Hubble", diameter=2.4,
            kepler_elements=self.valid_kepler_elements, use_kep=True,
            pitch_range=(-45.0, 45.0), yaw_range=(-90.0, 90.0),
            sefd_table={1000.0: 2000.0}
        )
        data = st.to_dict()
        self.assertEqual(data["code"], "HST")
        self.assertEqual(data["kepler_elements"]["a"], 7000000.0)
        self.assertEqual(data["pitch_range"], (-45.0, 45.0))
        self.assertEqual(data["sefd_table"], {1000.0: 2000.0})

        new_st = SpaceTelescope.from_dict(data)
        self.assertEqual(new_st.code, st.code)
        self.assertEqual(new_st._kepler_elements["a"], st._kepler_elements["a"])
        self.assertEqual(new_st._pitch_range, st._pitch_range)
        self.assertEqual(new_st.sefd_table, st.sefd_table)

    def test_to_dict_with_orbit_data(self):
        """Test serialization with orbit data."""
        st = SpaceTelescope(code="HST", orbit_data=self.valid_orbit_data, use_kep=False)
        data = st.to_dict()
        self.assertEqual(data["orbit_data"]["times"], self.valid_orbit_data["times"].tolist())
        self.assertFalse(data["use_kep"])
        self.assertIsNone(data["kepler_elements"])

    def test_activate_deactivate(self):
        """Test activation and deactivation."""
        st = SpaceTelescope(code="HST")
        self.assertTrue(st.isactive)
        st.deactivate()
        self.assertFalse(st.isactive)
        st.activate()
        self.assertTrue(st.isactive)

    def test_sefd_operations(self):
        """Test SEFD table operations inherited from Telescope."""
        st = SpaceTelescope(code="HST")
        st.add_sefd(1000.0, 2000.0)
        self.assertEqual(st.get_sefd(1000.0), 2000.0)
        self.assertAlmostEqual(st.get_sefd(1005.0), 2000.0, delta=1e-3)  # Interpolation
        st.remove_sefd(1000.0)
        self.assertIsNone(st.get_sefd(1000.0))
        st.clear_sefd_table()
        self.assertEqual(st.sefd_table, {})

    def test_clone(self):
        """Test cloning the SpaceTelescope."""
        st = SpaceTelescope(
            code="HST", kepler_elements=self.valid_kepler_elements, use_kep=True
        )
        clone = st.clone()
        self.assertEqual(st.code, clone.code)
        self.assertEqual(st._kepler_elements, clone._kepler_elements)
        self.assertNotEqual(id(st), id(clone))
        self.assertNotEqual(id(st._kepler_elements), id(clone._kepler_elements))

    def test_equality(self):
        """Test equality comparison."""
        st1 = SpaceTelescope(code="HST", kepler_elements=self.valid_kepler_elements)
        st2 = SpaceTelescope(code="HST", kepler_elements=self.valid_kepler_elements)
        st3 = SpaceTelescope(code="JWST", kepler_elements=self.valid_kepler_elements)
        self.assertEqual(st1, st2)
        self.assertNotEqual(st1, st3)

    def test_solve_kepler(self):
        """Test Kepler's equation solver."""
        st = SpaceTelescope()
        e = 0.1
        M = np.radians(30.0)
        E = st._solve_kepler(M, e)
        self.assertAlmostEqual(E - e * np.sin(E), M, delta=1e-6)
        with self.assertRaises(ValueError):
            st._solve_kepler(M, 1.0)  # Parabolic orbit not supported

    def test_get_orbit_none(self):
        """Test get_orbit when no orbit data is set."""
        st = SpaceTelescope(use_kep=True)
        self.assertIsNone(st.get_orbit())

    def test_get_state_vector_outside_range(self):
        """Test state vector retrieval outside orbit data range."""
        st = SpaceTelescope()
        st.set_orbit(self.valid_orbit_data)
        time = Time("2025-04-15T15:00:00", scale='utc')
        with self.assertLogs(logger, level='WARNING'):
            pos, vel = st.get_state_vector(time)
            self.assertTrue(np.allclose(pos, [0.0, 0.0, 0.0], atol=1e-3))
            self.assertTrue(np.allclose(vel, [0.0, 0.0, 0.0], atol=1e-3))

if __name__ == '__main__':
    unittest.main()