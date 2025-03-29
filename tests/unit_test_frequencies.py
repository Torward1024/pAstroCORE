import unittest
from base.frequencies import IF, Frequencies, VALID_POLARIZATIONS, C_MHZ_CM

class TestFrequencies(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test data before each test."""
        self.if1 = IF(
            freq=1000.0,
            bandwidth=32.0,
            polarization="RCP",
            isactive=True
        )
        self.if2 = IF(
            freq=2000.0,
            bandwidth=16.0,
            polarization="LL",
            isactive=False
        )
        self.frequencies = Frequencies([self.if1, self.if2])

    def test_if_init(self) -> None:
        """Test IF initialization."""
        self.assertEqual(self.if1.get_frequency(), 1000.0)
        self.assertEqual(self.if1.get_bandwidth(), 32.0)
        self.assertEqual(self.if1.get_polarization(), ["RCP"])
        self.assertTrue(self.if1.isactive)
        self.assertEqual(self.if2.get_polarization(), ["LL"])
        self.assertFalse(self.if2.isactive)

    def test_if_polarization_validation(self) -> None:
        """Test polarization validation."""
        self.if1.set_polarization(["RCP", "LCP"])
        self.assertEqual(self.if1.get_polarization(), ["RCP", "LCP"])
        with self.assertRaises(ValueError):
            self.if1.set_polarization(["RCP", "H"])  # Mixed groups
        with self.assertRaises(ValueError):
            self.if1.set_polarization("INVALID")  # Invalid polarization

    def test_if_wavelength(self) -> None:
        """Test wavelength calculation."""
        wavelength = self.if1.get_frequency_wavelength()
        self.assertAlmostEqual(wavelength, C_MHZ_CM / 1000.0, places=4)
        self.if1.set_frequency_wavelength(29.9792458)  # ~1000 MHz
        self.assertAlmostEqual(self.if1.get_frequency(), 1000.0, places=4)
        with self.assertRaises(ValueError):
            IF(freq=0.0)  # Zero frequency

    def test_frequencies_init_and_add(self) -> None:
        """Test Frequencies initialization and IF addition."""
        self.assertEqual(len(self.frequencies), 2)
        self.assertEqual(self.frequencies.get_by_index(0).get_frequency(), 1000.0)
        new_if = IF(freq=3000.0, bandwidth=8.0)
        self.frequencies.add_IF(new_if)
        self.assertEqual(len(self.frequencies), 3)
        with self.assertRaises(ValueError):
            self.frequencies.add_IF(IF(freq=1010.0, bandwidth=30.0))  # Overlap with 1000-1032

    def test_frequencies_activation(self) -> None:
        """Test IF activation/deactivation."""
        self.frequencies.deactivate_IF(0)
        self.assertFalse(self.frequencies.get_by_index(0).isactive)
        self.assertEqual(len(self.frequencies.get_active_frequencies()), 0)
        self.frequencies.activate_IF(0)
        self.assertTrue(self.frequencies.get_by_index(0).isactive)
        self.frequencies.activate_all()
        self.assertEqual(len(self.frequencies.get_active_frequencies()), 2)

    def test_frequencies_serialization(self) -> None:
        """Test Frequencies to/from dict serialization."""
        freq_dict = self.frequencies.to_dict()
        self.assertEqual(len(freq_dict["data"]), 2)
        restored_freqs = Frequencies.from_dict(freq_dict)
        self.assertEqual(restored_freqs.get_by_index(0).get_frequency(), 1000.0)
        self.assertEqual(restored_freqs.get_by_index(1).get_polarization(), ["LL"])

    def test_frequencies_overlap(self) -> None:
        """Test frequency overlap detection."""
        self.frequencies.clear()
        self.frequencies.add_IF(IF(freq=1000.0, bandwidth=50.0))  # 1000-1050
        with self.assertRaises(ValueError):
            self.frequencies.create_IF(freq=1040.0, bandwidth=20.0)  # 1040-1060 overlaps
        self.frequencies.add_IF(IF(freq=1060.0, bandwidth=10.0))  # No overlap
        self.assertEqual(len(self.frequencies), 2)

if __name__ == "__main__":
    unittest.main()