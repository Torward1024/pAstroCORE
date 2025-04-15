# tests/test_frequencies.py
import unittest
from unit_scheduling_2.base.frequencies import IF, Frequencies
from common.utils.logging_setup import logger
import logging
from typing import List

class TestFrequencies(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        logger.setLevel(logging.INFO)
        self.if1 = IF(name="IF1", frequency=1000.0, bandwidth=16.0, polarizations="RCP")
        self.if2 = IF(name="IF2", frequency=1020.0, bandwidth=16.0, polarizations=["LCP", "RCP"])
        self.if3 = IF(name="IF3", frequency=1040.0, bandwidth=8.0, polarizations="RCP", isactive=False)
        self.freqs = Frequencies(name="TestFreqs")
        self.freqs.add(self.if1)  # [1000.0, 1016.0]
        self.freqs.add(self.if2)  # [1020.0, 1036.0]
        self.freqs.add(self.if3)  # [1040.0, 1048.0]

    def test_if_initialization(self):
        """Test IF initialization and attribute access."""
        if_obj = IF(name="TestIF", frequency=1420.0, bandwidth=32.0, polarizations="LCP", isactive=False)
        self.assertEqual(if_obj.name, "TestIF")
        self.assertEqual(if_obj.frequency, 1420.0)
        self.assertEqual(if_obj.bandwidth, 32.0)
        self.assertEqual(if_obj.polarizations, ["LCP"])
        self.assertFalse(if_obj.isactive)
        self.assertAlmostEqual(if_obj.get_frequency_wavelength(), 29979.2458 / 1420.0)

        # Test default initialization
        if_default = IF()
        self.assertIsNone(if_default.name)
        self.assertEqual(if_default.frequency, 1000.0)
        self.assertEqual(if_default.bandwidth, 16.0)
        self.assertEqual(if_default.polarizations, [])
        self.assertTrue(if_default.isactive)

    def test_if_get(self):
        """Test IF attribute retrieval using get method."""
        if_obj = IF(name="TestIF", frequency=1420.0, bandwidth=32.0, polarizations=["LCP"], isactive=False)
        
        # Test single attribute
        self.assertEqual(if_obj.get("frequency"), 1420.0)
        self.assertEqual(if_obj.get("isactive"), False)
        self.assertEqual(if_obj.get("polarizations"), ["LCP"])
        
        # Test multiple attributes
        result = if_obj.get(["frequency", "bandwidth", "isactive"])
        expected = {"frequency": 1420.0, "bandwidth": 32.0, "isactive": False}
        self.assertEqual(result, expected)
        
        # Test all attributes
        result = if_obj.get()
        expected = {
            "name": "TestIF",
            "isactive": False,
            "frequency": 1420.0,
            "bandwidth": 32.0,
            "polarizations": ["LCP"]
        }
        self.assertEqual(result, expected)
        
        # Test non-existent attribute
        with self.assertRaises(KeyError):
            if_obj.get("non_existent")
        
        # Test invalid keys in list
        with self.assertRaises(KeyError):
            if_obj.get(["frequency", "invalid_key"])
        
        # Test empty list
        result = if_obj.get([])
        self.assertEqual(result, {})

    def test_if_validation(self):
        """Test IF validation for frequency, bandwidth, and polarizations."""
        # Invalid frequency
        with self.assertRaises(ValueError):
            IF(name="Invalid", frequency=0.0, bandwidth=16.0)
        with self.assertRaises(ValueError):
            IF(name="Invalid", frequency=-1.0, bandwidth=16.0)
        
        # Invalid bandwidth
        with self.assertRaises(ValueError):
            IF(name="Invalid", frequency=1000.0, bandwidth=-1.0)
        with self.assertRaises(ValueError):
            IF(name="Invalid", frequency=1000.0, bandwidth=0.0)
        
        # Invalid polarizations
        with self.assertRaises(ValueError):
            IF(name="Invalid", polarizations="XYZ")
        with self.assertRaises(ValueError):
            IF(name="Invalid", polarizations=["RCP", "H"])
        with self.assertRaises(TypeError):
            IF(name="Invalid", polarizations=["RCP", 123])
        
        # Valid polarizations
        if_obj = IF(name="Valid", polarizations=["RR", "LL"])
        self.assertEqual(if_obj.polarizations, ["RR", "LL"])
        if_obj = IF(name="Valid", polarizations=None)
        self.assertEqual(if_obj.polarizations, [])
        if_obj = IF(name="Valid", polarizations=[])
        self.assertEqual(if_obj.polarizations, [])

    def test_if_set_wavelength(self):
        """Test setting frequency via wavelength."""
        if_obj = IF(name="WavelengthIF")
        if_obj.set_frequency_wavelength(21.0)
        self.assertAlmostEqual(if_obj.frequency, 29979.2458 / 21.0)
        with self.assertRaises(ValueError):
            if_obj.set_frequency_wavelength(0.0)
        with self.assertRaises(ValueError):
            if_obj.set_frequency_wavelength(-1.0)

    def test_if_serialization(self):
        """Test IF serialization and deserialization."""
        if_obj = IF(name="Serializable", frequency=1500.0, bandwidth=20.0, polarizations=["RR", "LL"])
        serialized = if_obj.to_dict()
        expected = {
            "name": "Serializable",
            "type": "IF",
            "frequency": 1500.0,
            "bandwidth": 20.0,
            "polarizations": ["RR", "LL"],
            "isactive": True
        }
        self.assertEqual(serialized, expected)
        deserialized = IF.from_dict(serialized)
        self.assertEqual(deserialized, if_obj)

        # Test empty polarizations
        if_obj_empty = IF(name="EmptyPol", frequency=1500.0, bandwidth=20.0, polarizations=None)
        serialized_empty = if_obj_empty.to_dict()
        expected_empty = {
            "name": "EmptyPol",
            "type": "IF",
            "frequency": 1500.0,
            "bandwidth": 20.0,
            "polarizations": [],
            "isactive": True
        }
        self.assertEqual(serialized_empty, expected_empty)
        deserialized_empty = IF.from_dict(serialized_empty)
        self.assertEqual(deserialized_empty, if_obj_empty)

    def test_if_clone(self):
        """Test cloning IF object."""
        if_obj = IF(name="CloneIF", frequency=1500.0, bandwidth=20.0, polarizations=["RCP"])
        clone = if_obj.clone()
        self.assertEqual(clone, if_obj)
        self.assertNotEqual(id(clone), id(if_obj))
        if_obj.set({"frequency": 1600.0})
        self.assertEqual(clone.frequency, 1500.0)

    def test_frequencies_initialization(self):
        """Test Frequencies initialization."""
        items = {"IF1": self.if1, "IF2": self.if2}
        freqs = Frequencies(name="InitTest", items=items)
        self.assertEqual(freqs.name, "InitTest")
        self.assertEqual(len(freqs), 2)
        self.assertEqual(freqs.get("IF1"), self.if1)
        self.assertEqual(freqs.get("IF2"), self.if2)
        
        # Test empty initialization
        empty_freqs = Frequencies()
        self.assertIsNone(empty_freqs.name)
        self.assertEqual(len(empty_freqs), 0)
        self.assertTrue(empty_freqs.isactive)

    def test_frequencies_add_remove(self):
        """Test adding and removing IF objects to/from Frequencies."""
        freqs = Frequencies(name="AddRemoveTest")
        freqs.add(self.if1)
        self.assertEqual(len(freqs), 1)
        self.assertEqual(freqs.get("IF1"), self.if1)
        freqs.add(self.if2)
        self.assertEqual(len(freqs), 2)
        
        freqs.remove("IF1")
        self.assertEqual(len(freqs), 1)
        self.assertEqual(freqs.get("IF2"), self.if2)
        with self.assertRaises(KeyError):
            freqs.get("IF1")
        with self.assertRaises(KeyError):
            freqs.remove("NonExistent")

        # Test adding with None name
        invalid_if = IF(frequency=1060.0, bandwidth=10.0)
        invalid_if.name = None
        with self.assertRaises(ValueError):
            freqs.add(invalid_if)

    def test_frequencies_overlap(self):
        """Test frequency range overlap detection."""
        freqs = Frequencies(name="OverlapTest")
        freqs.add(self.if1)  # [1000, 1016]
        with self.assertRaises(ValueError):
            freqs.add(IF(name="Overlap", frequency=1010.0, bandwidth=10.0))  # [1010, 1020]
        freqs.add(IF(name="NonOverlap", frequency=1030.0, bandwidth=10.0))  # [1030, 1040]
        
        # Test zero bandwidth
        with self.assertRaises(ValueError):
            freqs.add(IF(name="ZeroBW", frequency=1060.0, bandwidth=0.0))

    def test_frequencies_get_methods(self):
        """Test getter methods for frequencies, bandwidths, polarizations, and wavelengths."""
        self.assertEqual(self.freqs.get_frequencies(), [1000.0, 1020.0, 1040.0])
        self.assertEqual(self.freqs.get_bandwidths(), [16.0, 16.0, 8.0])
        self.assertEqual(self.freqs.get_polarizations(), [["RCP"], ["LCP", "RCP"], ["RCP"]])
        self.assertEqual(self.freqs.get_wavelengths(), [
            self.if1.get_frequency_wavelength(),
            self.if2.get_frequency_wavelength(),
            self.if3.get_frequency_wavelength()
        ])
        
        # Test empty frequencies
        empty_freqs = Frequencies()
        self.assertEqual(empty_freqs.get_frequencies(), [])
        self.assertEqual(empty_freqs.get_bandwidths(), [])
        self.assertEqual(empty_freqs.get_polarizations(), [])
        self.assertEqual(empty_freqs.get_wavelengths(), [])

    def test_frequencies_get_by_value(self):
        """Test filtering IF objects using get_by_value with various conditions."""
        # Test filtering by single attribute
        result = self.freqs.get_by_value({"polarizations": ["RCP"]})
        self.assertEqual(len(result), 2)
        self.assertEqual({item.name for item in result}, {"IF1", "IF3"})

        result = self.freqs.get_by_value({"bandwidth": 16.0})
        self.assertEqual(len(result), 2)
        self.assertEqual({item.name for item in result}, {"IF1", "IF2"})

        result = self.freqs.get_by_value({"frequency": 1040.0})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "IF3")

        # Test filtering by multiple attributes
        result = self.freqs.get_by_value({"polarizations": ["RCP"], "isactive": False})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "IF3")

        result = self.freqs.get_by_value({"frequency": 1000.0, "bandwidth": 16.0, "isactive": True})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "IF1")

        # Test active/inactive items using get_active_items and get_inactive_items
        result = self.freqs.get_active_items()
        self.assertEqual(len(result), 2)
        self.assertEqual({item.name for item in result}, {"IF1", "IF2"})

        result = self.freqs.get_inactive_items()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "IF3")

        # Test empty conditions
        result = self.freqs.get_by_value({})
        self.assertEqual(len(result), 3)
        self.assertEqual({item.name for item in result}, {"IF1", "IF2", "IF3"})

        # Test invalid attribute
        with self.assertRaises(AttributeError):
            self.freqs.get_by_value({"non_existent": True})

    def test_frequencies_activation(self):
        """Test activation and deactivation of IF objects."""
        self.freqs.deactivate_item("IF1")
        self.assertFalse(self.freqs.get("IF1").isactive)
        self.assertTrue(self.freqs.get("IF2").isactive)
        self.assertFalse(self.freqs.get("IF3").isactive)

        self.freqs.activate_all()
        self.assertEqual(len(self.freqs.get_active_items()), 3)
        self.freqs.deactivate_all()
        self.assertEqual(len(self.freqs.get_inactive_items()), 3)

        # Test activation of non-existent item
        with self.assertRaises(KeyError):
            self.freqs.activate_item("NonExistent")

    def test_frequencies_drop(self):
        """Test dropping active and inactive IF objects."""
        self.freqs.deactivate_item("IF1")
        self.freqs.drop_active()
        self.assertEqual(len(self.freqs), 2)  # IF1 and IF3 remain (both inactive)
        self.assertTrue(self.freqs.has_item("IF1"))
        self.assertTrue(self.freqs.has_item("IF3"))
        self.assertFalse(self.freqs.has_item("IF2"))
        self.assertEqual(len(self.freqs.get_inactive_items()), 2)
        self.freqs.drop_inactive()
        self.assertEqual(len(self.freqs), 0)

        # Test dropping with no active/inactive items
        freqs = Frequencies()
        freqs.drop_active()
        freqs.drop_inactive()
        self.assertEqual(len(freqs), 0)

    def test_frequencies_serialization(self):
        """Test Frequencies serialization and deserialization."""
        serialized = self.freqs.to_dict()
        expected = {
            "name": "TestFreqs",
            "isactive": True,
            "type": "Frequencies", 
            "items": {
                "IF1": self.if1.to_dict(),
                "IF2": self.if2.to_dict(),
                "IF3": self.if3.to_dict()
            }
        }
        self.assertEqual(serialized, expected)
        deserialized = Frequencies.from_dict(serialized)
        self.assertEqual(deserialized.get("IF1"), self.if1)
        self.assertEqual(deserialized.get("IF2"), self.if2)
        self.assertEqual(deserialized.get("IF3"), self.if3)

        # Test empty frequencies
        empty_freqs = Frequencies()
        serialized_empty = empty_freqs.to_dict()
        expected_empty = {"name": None, "isactive": True, "items": {}, "type": "Frequencies"}
        self.assertEqual(serialized_empty, expected_empty)
        deserialized_empty = Frequencies.from_dict(serialized_empty)
        self.assertEqual(len(deserialized_empty), 0)

    def test_frequencies_clone(self):
        """Test cloning Frequencies object."""
        clone = self.freqs.clone(deep=True)
        self.assertEqual(clone.get("IF1"), self.if1)
        self.assertEqual(clone.get("IF2"), self.if2)
        self.assertEqual(clone.get("IF3"), self.if3)
        self.assertNotEqual(id(clone.get("IF1")), id(self.if1))
        self.freqs.deactivate_item("IF1")
        self.assertTrue(clone.get("IF1").isactive)

    def test_frequencies_edge_cases(self):
        """Test edge cases for Frequencies and IF."""
        # Test IF with minimal configuration
        if_min = IF(name="MinIF", frequency=1.0, bandwidth=0.1, polarizations=[])
        self.assertEqual(if_min.polarizations, [])
        self.assertAlmostEqual(if_min.get_frequency_wavelength(), 29979.2458 / 1.0)

        # Test Frequencies with single item
        single_freqs = Frequencies(name="Single")
        single_freqs.add(if_min)
        self.assertEqual(single_freqs.get_frequencies(), [1.0])
        self.assertEqual(single_freqs.get_by_value({"frequency": 1.0}), [if_min])

        # Test overlapping edge case
        freqs = Frequencies()
        freqs.add(IF(name="Edge1", frequency=1000.0, bandwidth=10.0))
        with self.assertRaises(ValueError):
            freqs.add(IF(name="Edge2", frequency=1009.9, bandwidth=0.2))

if __name__ == "__main__":
    unittest.main()