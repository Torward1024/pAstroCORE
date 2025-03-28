import unittest
from unittest.mock import patch
import numpy as np
from datetime import datetime
from base.telescopes import Telescope, SpaceTelescope, Telescopes, MountType

class TestTelescopes(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test data before each test."""
        self.tel1 = Telescope(
            code="TEL1",
            name="Test Telescope 1",
            x=1000.0, y=2000.0, z=3000.0,
            vx=0.1, vy=0.2, vz=0.3,
            diameter=25.0,
            sefd_table={1000.0: 500.0, 2000.0: 600.0},
            mount_type="AZIM"
        )
        self.tel2 = SpaceTelescope(
            code="STEL1",
            name="Space Telescope 1",
            orbit_file="dummy.oem",
            diameter=10.0,
            use_kep=True,
            kepler_elements={
                "a": 7000000.0, "e": 0.01, "i": 45.0, "raan": 0.0,
                "argp": 0.0, "nu": 0.0, "epoch": datetime(2023, 1, 1),
                "mu": 398600.4418e9
            }
        )
        self.telescopes = Telescopes([self.tel1, self.tel2])

    def test_telescope_init(self) -> None:
        """Test Telescope initialization."""
        self.assertEqual(self.tel1.get_code(), "TEL1")
        self.assertEqual(self.tel1.get_name(), "Test Telescope 1")
        self.assertEqual(self.tel1.get_coordinates(), (1000.0, 2000.0, 3000.0))
        self.assertEqual(self.tel1.get_velocities(), (0.1, 0.2, 0.3))
        self.assertEqual(self.tel1.get_diameter(), 25.0)
        self.assertEqual(self.tel1.get_sefd_table(), {1000.0: 500.0, 2000.0: 600.0})
        self.assertEqual(self.tel1.get_mount_type(), MountType.AZIMUTHAL)
        self.assertTrue(self.tel1.isactive)

    def test_telescope_sefd(self) -> None:
        """Test SEFD operations."""
        self.assertEqual(self.tel1.get_sefd(1000.0), 500.0)
        self.assertEqual(self.tel1.get_sefd(1500.0), 550.0)  # Linear interpolation
        self.assertIsNone(self.tel1.get_sefd(500.0))  # Out of range
        self.tel1.add_sefd(3000.0, 700.0)
        self.assertEqual(self.tel1.get_sefd(3000.0), 700.0)
        self.tel1.remove_sefd(1000.0)
        self.assertIsNone(self.tel1.get_sefd(1000.0))

    def test_telescope_setters(self) -> None:
        """Test Telescope setters."""
        self.tel1.set_coordinates((4000.0, 5000.0, 6000.0))
        self.assertEqual(self.tel1.get_coordinates(), (4000.0, 5000.0, 6000.0))
        self.tel1.set_diameter(30.0)
        self.assertEqual(self.tel1.get_diameter(), 30.0)
        self.tel1.set_elevation_range((20.0, 85.0))
        self.assertEqual(self.tel1.get_elevation_range(), (20.0, 85.0))
        with self.assertRaises(ValueError):
            self.tel1.set_mount_type("INVALID")

    def test_space_telescope_init(self) -> None:
        """Test SpaceTelescope initialization."""
        self.assertEqual(self.tel2.get_code(), "STEL1")
        self.assertEqual(self.tel2.get_diameter(), 10.0)
        self.assertEqual(self.tel2.get_pitch_range(), (-90.0, 90.0))
        self.assertTrue(self.tel2.get_use_kep())
        kep = self.tel2.get_keplerian()
        self.assertEqual(kep["a"], 7000000.0)
        self.assertEqual(self.tel2.get_mount_type(), MountType.SPACE)

    def test_space_telescope_orbit(self) -> None:
        """Test SpaceTelescope orbit methods."""
        dt = datetime(2023, 1, 1, 0, 1)  # 1 minute after epoch
        pos, vel = self.tel2.get_state_vector(dt)
        self.assertTrue(np.all(np.isfinite(pos)))
        self.assertTrue(np.all(np.isfinite(vel)))
        self.tel2.set_use_kep(False)
        with self.assertRaises(ValueError):
            self.tel2.get_state_vector(dt)  # No orbit data loaded yet

    def test_telescopes_init_and_add(self) -> None:
        """Test Telescopes initialization and addition."""
        self.assertEqual(len(self.telescopes), 2)
        self.assertEqual(self.telescopes.get_by_index(0).get_code(), "TEL1")
        new_tel = Telescope(code="TEL3", name="Test Telescope 3")
        self.telescopes.add_telescope(new_tel)
        self.assertEqual(len(self.telescopes), 3)
        with self.assertRaises(ValueError):
            self.telescopes.add_telescope(Telescope(code="TEL1"))  # Duplicate code

    def test_telescopes_activation(self) -> None:
        """Test Telescopes activation/deactivation."""
        self.telescopes.deactivate_telescope(0)
        self.assertFalse(self.telescopes.get_by_index(0).isactive)
        self.assertEqual(len(self.telescopes.get_active_telescopes()), 1)
        self.telescopes.activate_all()
        self.assertEqual(len(self.telescopes.get_active_telescopes()), 2)

    def test_telescopes_serialization(self) -> None:
        """Test Telescopes serialization."""
        tel_dict = self.telescopes.to_dict()
        self.assertEqual(len(tel_dict["data"]), 2)
        restored_tels = Telescopes.from_dict(tel_dict)
        self.assertEqual(restored_tels.get_by_index(0).get_code(), "TEL1")
        self.assertEqual(restored_tels.get_by_index(1).get_code(), "STEL1")

if __name__ == "__main__":
    unittest.main()