# tests/test_frequencies.py
import unittest
from unit_scheduling_2.base.frequencies import IF, Frequencies
from common.utils.logging_setup import logger
import logging

class TestFrequencies(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        logger.setLevel(logging.CRITICAL)  # Suppress logs during tests
        self.if1 = IF(name="IF1", frequency=1000.0, bandwidth=16.0, polarizations="RCP")
        self.if2 = IF(name="IF2", frequency=1020.0, bandwidth=16.0, polarizations=["LCP", "RCP"])
        self.freqs = Frequencies(name="TestFreqs")

    def test_if_initialization(self):
        """Test IF initialization and attribute access."""
        if_obj = IF(name="TestIF", frequency=1420.0, bandwidth=32.0, polarizations="LCP", isactive=False)
        self.assertEqual(if_obj.name, "TestIF")
        self.assertEqual(if_obj.frequency, 1420.0)
        self.assertEqual(if_obj.bandwidth, 32.0)
        self.assertEqual(if_obj.polarizations, ["LCP"])
        self.assertFalse(if_obj.isactive)
        self.assertAlmostEqual(if_obj.get_frequency_wavelength(), 29979.2458 / 1420.0)

    def test_if_validation(self):
        """Test IF validation for frequency, bandwidth, and polarizations."""
        with self.assertRaises(ValueError):
            IF(name="Invalid", frequency=0.0, bandwidth=16.0)  # Zero frequency
        with self.assertRaises(ValueError):
            IF(name="Invalid", frequency=1000.0, bandwidth=-1.0)  # Negative bandwidth
        with self.assertRaises(ValueError):
            IF(name="Invalid", polarizations="XYZ")  # Invalid polarizations
        with self.assertRaises(ValueError):
            IF(name="Invalid", polarizations=["RCP", "H"])  # Mixed polarizations groups

    def test_if_set_wavelength(self):
        """Test setting frequency via wavelength."""
        if_obj = IF(name="WavelengthIF")
        if_obj.set_frequency_wavelength(21.0)
        self.assertAlmostEqual(if_obj.frequency, 29979.2458 / 21.0)
        with self.assertRaises(ValueError):
            if_obj.set_frequency_wavelength(0.0)

    def test_if_serialization(self):
        """Test IF serialization and deserialization."""
        # Тест с непустым polarizations
        if_obj = IF(name="Serializable", frequency=1500.0, bandwidth=20.0, polarizations=["RR", "LL"])
        serialized = if_obj.to_dict()
        expected = {
            "name": "Serializable",
            "frequency": 1500.0,
            "bandwidth": 20.0,
            "polarizations": ["RR", "LL"],
            "isactive": True
        }
        self.assertEqual(serialized, expected)
        deserialized = IF.from_dict(serialized)
        self.assertEqual(deserialized, if_obj)

        # Тест с пустым polarizations
        if_obj_empty = IF(name="EmptyPol", frequency=1500.0, bandwidth=20.0, polarizations=None)
        serialized_empty = if_obj_empty.to_dict()
        expected_empty = {
            "name": "EmptyPol",
            "frequency": 1500.0,
            "bandwidth": 20.0,
            "polarizations": [],
            "isactive": True
        }
        self.assertEqual(serialized_empty, expected_empty)
        deserialized_empty = IF.from_dict(serialized_empty)
        self.assertEqual(deserialized_empty, if_obj_empty)

    def test_frequencies_initialization(self):
        """Test Frequencies initialization."""
        items = {"IF1": self.if1, "IF2": self.if2}
        freqs = Frequencies(name="InitTest", items=items)
        self.assertEqual(freqs.name, "InitTest")
        self.assertEqual(len(freqs), 2)
        self.assertEqual(freqs.get("IF1"), self.if1)
        self.assertEqual(freqs.get("IF2"), self.if2)

    def test_frequencies_add(self):
        """Test adding IF objects to Frequencies."""
        self.freqs.add(self.if1)
        self.assertEqual(len(self.freqs), 1)
        self.assertEqual(self.freqs.get("IF1"), self.if1)
        self.freqs.add(self.if2)
        self.assertEqual(len(self.freqs), 2)
        with self.assertRaises(ValueError):
            # Overlapping frequency range
            self.freqs.add(IF(name="IF3", frequency=1008.0, bandwidth=10.0))

    def test_frequencies_remove(self):
        """Test removing IF objects from Frequencies."""
        self.freqs.add(self.if1)
        self.freqs.remove("IF1")
        self.assertEqual(len(self.freqs), 0)
        with self.assertRaises(KeyError):
            self.freqs.get("IF1")
        with self.assertRaises(KeyError):
            self.freqs.remove("NonExistent")

    def test_frequencies_overlap(self):
        """Test frequency range overlap detection."""
        self.freqs.add(self.if1)  # [1000, 1016]
        with self.assertRaises(ValueError):
            self.freqs.add(IF(name="Overlap", frequency=1010.0, bandwidth=10.0))  # [1010, 1020]
        # Non-overlapping
        self.freqs.add(IF(name="NonOverlap", frequency=1030.0, bandwidth=10.0))  # [1030, 1040]

    def test_frequencies_get_methods(self):
        """Test getter methods for frequencies, bandwidths, polarizations, and wavelengths."""
        self.freqs.add(self.if1)
        self.freqs.add(self.if2)
        self.assertEqual(self.freqs.get_frequencies(), [1000.0, 1020.0])
        self.assertEqual(self.freqs.get_bandwidths(), [16.0, 16.0])
        self.assertEqual(self.freqs.get_polarizations(), [["RCP"], ["LCP", "RCP"]])
        self.assertEqual(self.freqs.get_wavelengths(), [self.if1.get_frequency_wavelength(),
                                                       self.if2.get_frequency_wavelength()])

    def test_frequencies_activation(self):
        """Test activation and deactivation of IF objects."""
        self.freqs.add(self.if1)
        self.freqs.add(self.if2)
        self.freqs.deactivate_item("IF1")
        self.assertFalse(self.freqs.get("IF1").isactive)
        self.assertTrue(self.freqs.get("IF2").isactive)
        self.assertEqual(len(self.freqs.get_active_frequencies()), 1)
        self.assertEqual(len(self.freqs.get_inactive_frequencies()), 1)
        self.freqs.activate_all()
        self.assertEqual(len(self.freqs.get_active_frequencies()), 2)
        self.freqs.deactivate_all()
        self.assertEqual(len(self.freqs.get_inactive_frequencies()), 2)

    def test_frequencies_drop(self):
        """Test dropping active and inactive IF objects."""
        self.freqs.add(self.if1)
        self.freqs.add(self.if2)
        self.freqs.deactivate_item("IF1")
        self.freqs.drop_active()
        self.assertEqual(len(self.freqs), 1)
        self.assertEqual(self.freqs.get("IF1").name, "IF1")
        self.freqs.drop_inactive()
        self.assertEqual(len(self.freqs), 0)
        with self.assertRaises(ValueError):
            self.freqs.drop_active() # Empty collection

    def test_frequencies_serialization(self):
        """Test Frequencies serialization and deserialization."""
        self.freqs.add(self.if1)
        self.freqs.add(self.if2)
        serialized = self.freqs.to_dict()
        expected = {
            "name": "TestFreqs",
            "isactive": True,
            "items": {
                "IF1": self.if1.to_dict(),
                "IF2": self.if2.to_dict()
            }
        }
        self.assertEqual(serialized, expected)
        deserialized = Frequencies.from_dict(serialized)
        self.assertEqual(deserialized.get("IF1"), self.if1)
        self.assertEqual(deserialized.get("IF2"), self.if2)

    def test_frequencies_clone(self):
        """Test cloning Frequencies object."""
        self.freqs.add(self.if1)
        clone = self.freqs.clone(deep=True)
        self.assertEqual(clone.get("IF1"), self.if1)
        self.assertNotEqual(id(clone.get("IF1")), id(self.if1))  # Deep copy
        self.freqs.deactivate_item("IF1")
        self.assertTrue(clone.get("IF1").isactive)

if __name__ == "__main__":
    unittest.main()