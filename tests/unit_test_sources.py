import unittest
from base.sources import Source, Sources
from typing import Dict, Optional

class TestSources(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test data before each test."""
        self.source1 = Source(
            name="TEST_SRC1",
            ra_h=12.0, ra_m=30.0, ra_s=45.0,
            de_d=45.0, de_m=15.0, de_s=30.0,
            name_J2000="J1230+4515",
            alt_name="BL Lac 1",
            flux_table={150.0: 2.5, 300.0: 1.8},
            spectral_index=-0.7,
            isactive=True
        )
        self.source2 = Source(
            name="TEST_SRC2",
            ra_h=15.0, ra_m=0.0, ra_s=0.0,
            de_d=-30.0, de_m=0.0, de_s=0.0
        )
        self.sources = Sources([self.source1, self.source2])

    def test_source_init(self) -> None:
        """Test Source initialization."""
        self.assertEqual(self.source1.get_name(), "TEST_SRC1")
        self.assertEqual(self.source1.get_name_J2000(), "J1230+4515")
        self.assertEqual(self.source1.get_alt_name(), "BL Lac 1")
        self.assertEqual(self.source1.get_ra(), (12.0, 30.0, 45.0))
        self.assertEqual(self.source1.get_dec(), (45.0, 15.0, 30.0))
        self.assertEqual(self.source1.get_flux_table(), {150.0: 2.5, 300.0: 1.8})
        self.assertEqual(self.source1.get_spectral_index(), -0.7)
        self.assertTrue(self.source1.isactive)

    def test_source_flux_operations(self) -> None:
        """Test flux table operations."""
        self.source1.add_flux(600.0, 1.2)
        self.assertEqual(self.source1.get_flux(600.0), 1.2)
        self.source1.remove_flux(150.0)
        self.assertNotIn(150.0, self.source1.get_flux_table())
        flux = self.source1.get_flux(200.0)  # Extrapolation using spectral index from 300.0
        self.assertAlmostEqual(flux, 2.3908, places=4)  # Corrected expectation

    def test_source_coordinates_conversion(self) -> None:
        """Test RA/DEC conversions."""
        ra_deg = self.source1.get_ra_degrees()
        dec_deg = self.source1.get_dec_degrees()
        self.assertAlmostEqual(ra_deg, 187.6875, places=4)  # 12h30m45s = 187.6875°
        self.assertAlmostEqual(dec_deg, 45.25833, places=4)  # 45d15m30s = 45.25833°
        self.source1.set_ra_degrees(180.0)
        self.source1.set_dec_degrees(-45.0)
        self.assertEqual(self.source1.get_ra(), (12.0, 0.0, 0.0))
        self.assertEqual(self.source1.get_dec(), (-45.0, 0.0, 0.0))

    def test_sources_init_and_add(self) -> None:
        """Test Sources initialization and source addition."""
        self.assertEqual(len(self.sources), 2)
        self.assertEqual(self.sources.get_by_index(0).get_name(), "TEST_SRC1")
        new_source = Source(name="TEST_SRC3")
        self.sources.add_source(new_source)
        self.assertEqual(len(self.sources), 3)
        with self.assertRaises(ValueError):
            self.sources.create_source(name="TEST_SRC1")  # Duplicate name

    def test_sources_activation(self) -> None:
        """Test source activation/deactivation."""
        self.sources.deactivate_source(0)
        self.assertFalse(self.sources.get_by_index(0).isactive)
        self.assertEqual(len(self.sources.get_active_sources()), 1)
        self.sources.activate_source(0)
        self.assertTrue(self.sources.get_by_index(0).isactive)
        self.sources.deactivate_all()
        self.assertEqual(len(self.sources.get_active_sources()), 0)

    def test_sources_serialization(self) -> None:
        """Test Sources to/from dict serialization."""
        sources_dict = self.sources.to_dict()
        self.assertEqual(len(sources_dict["data"]), 2)
        restored_sources = Sources.from_dict(sources_dict)
        self.assertEqual(restored_sources.get_by_index(0).get_name(), "TEST_SRC1")
        self.assertEqual(restored_sources.get_by_index(0).get_flux_table(), {150.0: 2.5, 300.0: 1.8})

if __name__ == "__main__":
    unittest.main()