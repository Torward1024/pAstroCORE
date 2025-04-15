# tests/test_telescopes.py
import unittest
from unittest.mock import MagicMock
from unit_scheduling_2.base.telescopes import Telescopes
from unit_scheduling_2.base.telescope import Telescope
from unit_scheduling_2.base.spacetelescope import SpaceTelescope
from common.utils.logging_setup import logger
import logging
from typing import Dict, Tuple
import numpy as np
from astropy.time import Time

class TestTelescopes(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test fixtures before each test."""
        self.telescopes = Telescopes(name="test_collection")
        self.telescope1 = Telescope(
            code="RT32", name="RT32", x=1000.0, y=2000.0, z=3000.0,
            diameter=32.0, sefd_table={1000.0: 500.0}, isactive=True
        )
        self.telescope2 = Telescope(
            code="RT16", name="RT16", x=4000.0, y=5000.0, z=6000.0,
            diameter=16.0, sefd_table={1000.0: 1000.0}, isactive=False
        )
        self.space_telescope = SpaceTelescope(
            code="ST01", name="ST01", diameter=4.0, orbit_file="dummy.oem", isactive=True
        )

    def test_init_empty(self) -> None:
        """Test initializing an empty Telescopes collection."""
        self.assertEqual(len(self.telescopes), 0)
        self.assertEqual(self.telescopes.name, "test_collection")
        self.assertTrue(self.telescopes.isactive)

    def test_init_with_items(self) -> None:
        """Test initializing with a dictionary of telescopes."""
        items = {"RT32": self.telescope1, "ST01": self.space_telescope}
        tels = Telescopes(items=items)
        self.assertEqual(len(tels), 2)
        self.assertEqual(tels["RT32"], self.telescope1)
        self.assertEqual(tels["ST01"], self.space_telescope)

    def test_create_telescope(self) -> None:
        """Test creating and adding a new telescope."""
        self.telescopes.create_telescope(
            code="RT32", name="Radio Telescope 32m", diameter=32.0,
            x=1000.0, y=2000.0, z=3000.0, sefd_table={1000.0: 500.0}
        )
        self.assertEqual(len(self.telescopes), 1)
        tel = self.telescopes["RT32"]
        self.assertEqual(tel.code, "RT32")
        self.assertEqual(tel.name, "RT32")
        self.assertEqual(tel.diameter, 32.0)
        self.assertEqual(tel.x, 1000.0)
        self.assertTrue(tel.isactive)

    def test_add_telescope(self) -> None:
        """Test adding an existing telescope."""
        self.telescopes.add(self.telescope1)
        self.assertEqual(len(self.telescopes), 1)
        self.assertEqual(self.telescopes["RT32"], self.telescope1)

    def test_add_duplicate_code(self) -> None:
        """Test adding a telescope with a duplicate code."""
        self.telescopes.add(self.telescope1)
        with self.assertRaises(ValueError):
            self.telescopes.add(Telescope(code="RT32", name="RT32", diameter=16.0))

    def test_add_invalid_code(self) -> None:
        """Test adding a telescope with an invalid code."""
        invalid_tel = Telescope(code="RT 32", name="RT 32", diameter=16.0)
        with self.assertRaises(ValueError):
            self.telescopes.add(invalid_tel)

    def test_remove_telescope(self) -> None:
        """Test removing a telescope by code."""
        self.telescopes.add(self.telescope1)
        self.telescopes.remove("RT32")
        self.assertEqual(len(self.telescopes), 0)
        with self.assertRaises(KeyError):
            self.telescopes["RT32"]

    def test_get_telescope(self) -> None:
        """Test retrieving a telescope by code."""
        self.telescopes.add(self.telescope1)
        tel = self.telescopes.get("RT32")
        self.assertEqual(tel, self.telescope1)
        with self.assertRaises(KeyError):
            self.telescopes.get("RT16")

    def test_get_all(self) -> None:
        """Test retrieving all telescopes."""
        self.telescopes.add(self.telescope1)
        self.telescopes.add(self.telescope2)
        items = self.telescopes.get_all()
        self.assertEqual(len(items), 2)
        self.assertEqual(items["RT32"], self.telescope1)
        self.assertEqual(items["RT16"], self.telescope2)

    def test_get_active_inactive(self) -> None:
        """Test retrieving active and inactive telescopes."""
        self.telescopes.add(self.telescope1)  # active
        self.telescopes.add(self.telescope2)  # inactive
        active = self.telescopes.get_active_items()
        inactive = self.telescopes.get_inactive_items()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0], self.telescope1)
        self.assertEqual(len(inactive), 1)
        self.assertEqual(inactive[0], self.telescope2)

    def test_activate_deactivate_item(self) -> None:
        """Test activating and deactivating a telescope with parent sync."""
        self.telescopes.add(self.telescope2)  # inactive
        self.telescopes._parent = MagicMock()
        self.telescopes.activate_item("RT16")
        self.assertTrue(self.telescope2.isactive)
        self.telescopes._parent._sync_scans_with_activation.assert_called_with("telescopes", "RT16", True)
        self.telescopes.deactivate_item("RT16")
        self.assertFalse(self.telescope2.isactive)
        self.telescopes._parent._sync_scans_with_activation.assert_called_with("telescopes", "RT16", False)

    def test_activate_deactivate_all(self) -> None:
        """Test activating and deactivating all telescopes."""
        self.telescopes.add(self.telescope1)  # active
        self.telescopes.add(self.telescope2)  # inactive
        self.telescopes.deactivate_all()
        self.assertFalse(self.telescope1.isactive)
        self.assertFalse(self.telescope2.isactive)
        self.telescopes.activate_all()
        self.assertTrue(self.telescope1.isactive)
        self.assertTrue(self.telescope2.isactive)

    def test_drop_active_inactive(self) -> None:
        """Test dropping active and inactive telescopes."""
        self.telescopes.add(self.telescope1)  # active
        self.telescopes.add(self.telescope2)  # inactive
        self.telescopes.drop_active()
        self.assertEqual(len(self.telescopes), 1)
        self.assertEqual(self.telescopes["RT16"], self.telescope2)
        self.telescopes.drop_inactive()
        self.assertEqual(len(self.telescopes), 0)

    def test_clear(self) -> None:
        """Test clearing the collection."""
        self.telescopes.add(self.telescope1)
        self.telescopes.add(self.telescope2)
        self.telescopes.clear()
        self.assertEqual(len(self.telescopes), 0)

    def test_to_dict_from_dict(self) -> None:
        """Test serialization and deserialization."""
        self.telescopes.add(self.telescope1)
        self.telescopes.add(self.space_telescope)
        data = self.telescopes.to_dict()
        self.assertEqual(data["name"], "test_collection")
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["items"]["RT32"]["code"], "RT32")
        self.assertEqual(data["items"]["ST01"]["code"], "ST01")
        new_tels = Telescopes.from_dict(data)
        self.assertEqual(len(new_tels), 2)
        self.assertEqual(new_tels["RT32"].code, "RT32")
        self.assertEqual(new_tels["ST01"].code, "ST01")

    def test_invalid_initialization(self) -> None:
        """Test initialization with invalid items."""
        with self.assertRaises(TypeError):
            Telescopes(items={"RT32": "not a telescope"})
        with self.assertRaises(TypeError):
            Telescopes(items={1: self.telescope1})

    def test_name_code_mismatch(self) -> None:
        """Test handling of name and code mismatch."""
        with self.assertLogs(logger, level=logging.WARNING):
            tel = Telescope(code="RT32", name="Different", diameter=32.0)
            self.telescopes.add(tel)
            self.assertEqual(tel.name, "RT32")

    def test_contains(self) -> None:
        """Test checking if a telescope exists."""
        self.telescopes.add(self.telescope1)
        self.assertIn("RT32", self.telescopes)
        self.assertNotIn("RT16", self.telescopes)

    def test_iteration(self) -> None:
        """Test iterating over telescopes."""
        self.telescopes.add(self.telescope1)
        self.telescopes.add(self.telescope2)
        codes = [tel.code for tel in self.telescopes]
        self.assertEqual(set(codes), {"RT32", "RT16"})

    def test_get_by_value(self) -> None:
        """Test retrieving telescopes by attribute values."""
        self.telescopes.add(self.telescope1)
        self.telescopes.add(self.telescope2)
        results = self.telescopes.get_by_value({"diameter": 32.0})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.telescope1)

    def test_clone(self) -> None:
        """Test cloning the Telescopes collection."""
        self.telescopes.add(self.telescope1)
        clone = self.telescopes.clone()
        self.assertEqual(len(clone), 1)
        self.assertEqual(clone["RT32"].code, "RT32")
        self.assertNotEqual(id(clone["RT32"]), id(self.telescope1))

if __name__ == '__main__':
    unittest.main()