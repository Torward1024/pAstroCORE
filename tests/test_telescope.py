# tests/test_telescope.py
import unittest
import numpy as np
from pastrocore.base.telescope import Telescope, MountType
from common.utils.logging_setup import logger
import logging

class TestTelescope(unittest.TestCase):
    def setUp(self):
        """Set up a test Telescope instance."""
        self.tel = Telescope(
            code="RT32",
            name="Radio Telescope 32m",
            x=1000.0, y=2000.0, z=3000.0,
            vx=0.1, vy=0.2, vz=0.3,
            diameter=32.0,
            sefd_table={1420.0: 500.0},
            elevation_range=(10.0, 85.0),
            azimuth_range=(0.0, 360.0),
            mount_type="AZIM",
            isactive=True,
            surface_accuracy=100.0,
            surface_efficiency_table={1420.0: 0.8},
            effective_area_table={1420.0: 643.0},
            system_temperature_table={1420.0: 25.0}
        )
        # Disable logging for tests
        logger.setLevel(logging.INFO)

    def test_initialization(self):
        """Test Telescope initialization with valid parameters."""
        self.assertEqual(self.tel.code, "RT32")
        self.assertEqual(self.tel.name, "Radio Telescope 32m")
        self.assertEqual(self.tel.x, 1000.0)
        self.assertEqual(self.tel.diameter, 32.0)
        self.assertEqual(self.tel.sefd_table, {1420.0: 500.0})
        self.assertEqual(self.tel.mount_type, MountType.AZIMUTHAL)
        self.assertTrue(self.tel.isactive)

    def test_invalid_types(self):
        """Test initialization with invalid types."""
        with self.assertRaises(TypeError):
            Telescope(code=123)  # code must be str
        with self.assertRaises(TypeError):
            Telescope(x="1000")  # x must be float
        with self.assertRaises(TypeError):
            Telescope(sefd_table={1420: "500"})  # sefd value must be float

    def test_invalid_values(self):
        """Test initialization with invalid values."""
        with self.assertRaises(ValueError):
            Telescope(diameter=-1.0)  # diameter must be positive
        with self.assertRaises(ValueError):
            Telescope(elevation_range=(90.0, 0.0))  # min > max
        with self.assertRaises(ValueError):
            Telescope(mount_type="INVALID")  # invalid mount type

    def test_get_set_attributes(self):
        """Test getting and setting attributes via get/set and []."""
        self.assertEqual(self.tel.get("code"), "RT32")
        self.assertEqual(self.tel["name"], "Radio Telescope 32m")
        self.tel.set({"code": "RT64", "x": 2000.0})
        self.assertEqual(self.tel.code, "RT64")
        self.assertEqual(self.tel.x, 2000.0)
        self.tel["y"] = 3000.0
        self.assertEqual(self.tel.y, 3000.0)
        with self.assertRaises(KeyError):
            self.tel.get("invalid_attr")
        with self.assertRaises(TypeError):
            self.tel.set({"x": "invalid"})

    def test_sefd_operations(self):
        """Test SEFD table operations."""
        self.tel.add_sefd(1500.0, 480.0)
        self.assertEqual(self.tel.sefd_table[1500.0], 480.0)
        self.assertAlmostEqual(self.tel.get_sefd(1450.0), 492.5, places=2)  # Исправлено ожидание
        self.assertIsNone(self.tel.get_sefd(1600.0))  # Out of range
        self.tel.remove_sefd(1500.0)
        self.assertNotIn(1500.0, self.tel.sefd_table)
        self.tel.clear_sefd_table()
        self.assertEqual(self.tel.sefd_table, {})

    def test_interpolation(self):
        """Test interpolation for SEFD, efficiency, area, and Tsys."""
        self.tel.add_sefd(1500.0, 480.0)
        self.assertAlmostEqual(self.tel.get_sefd(1460.0), 490.0, places=2)  # Исправлено ожидание
        self.tel.set({"surface_efficiency_table": {1400.0: 0.7, 1500.0: 0.9}})
        self.assertAlmostEqual(self.tel.get_surface_efficiency(1450.0), 0.8, places=2)
        self.tel.set({"effective_area_table": {1400.0: 600.0, 1500.0: 700.0}})
        self.assertAlmostEqual(self.tel.get_effective_area(1450.0), 650.0, places=2)
        self.tel.set({"system_temperature_table": {1400.0: 20.0, 1500.0: 30.0}})
        self.assertAlmostEqual(self.tel.get_system_temperature(1450.0), 25.0, places=2)

    def test_calculations(self):
        """Test surface efficiency, effective area, and SEFD calculations."""
        self.tel.calculate_surface_efficiency(1420.0)
        efficiency = np.exp(-(4 * np.pi * 100e-6 / (3e8 / (1420e6))) ** 2)
        self.assertAlmostEqual(self.tel.surface_efficiency_table[1420.0], efficiency, places=4)
        
        self.tel.calculate_effective_area(1420.0)
        geom_area = np.pi * (32.0 / 2) ** 2
        self.assertAlmostEqual(self.tel.effective_area_table[1420.0], geom_area * efficiency, places=2)
        
        self.tel.calculate_sefd(1420.0)
        sefd = 2 * 1.380649e-23 * 25.0 / (geom_area * efficiency)
        self.assertAlmostEqual(self.tel.sefd_table[1420.0], sefd, places=2)

    def test_serialization(self):
        """Test to_dict and from_dict."""
        data = self.tel.to_dict()
        self.assertEqual(data["code"], "RT32")
        self.assertEqual(data["mount_type"], "AZIM")
        new_tel = Telescope.from_dict(data)
        self.assertEqual(new_tel.code, self.tel.code)
        self.assertEqual(new_tel.sefd_table, self.tel.sefd_table)
        self.assertEqual(new_tel.mount_type, self.tel.mount_type)

    def test_activation(self):
        """Test activation and deactivation."""
        self.tel.deactivate()
        self.assertFalse(self.tel.isactive)
        self.tel.activate()
        self.assertTrue(self.tel.isactive)

    def test_clone(self):
        """Test cloning the Telescope."""
        clone = self.tel.clone()
        self.assertEqual(clone.code, self.tel.code)
        self.assertEqual(clone.sefd_table, self.tel.sefd_table)
        self.assertNotEqual(id(clone), id(self.tel))

    def test_equality(self):
        """Test equality comparison."""
        other = self.tel.clone()
        self.assertEqual(other, self.tel)  # Same attributes

if __name__ == "__main__":
    unittest.main()