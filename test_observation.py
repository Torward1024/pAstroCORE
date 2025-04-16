# tests/test_observation.py
import unittest
from astropy.time import Time
import astropy.units as u
import numpy as np
from unit_scheduling_2.base.observation import Observation
from unit_scheduling_2.base.sources import Sources, Source
from unit_scheduling_2.base.telescopes import Telescopes, Telescope
from unit_scheduling_2.base.frequencies import Frequencies, IF
from unit_scheduling_2.base.scans import Scans, Scan
from common.utils.logging_setup import logger
import logging

class TestObservation(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.logger_handler = logging.StreamHandler()
        logger.addHandler(self.logger_handler)
        logger.setLevel(logging.DEBUG)

        # Create sample entities
        self.source = Source(
            name="M87",
            ra_h=12.0, ra_m=30.0, ra_s=0.0,
            de_d=12.0, de_m=20.0, de_s=0.0,
            flux_table={1000.0: 1.0},
            isactive=True
        )
        self.sources = Sources(items={"M87": self.source})

        self.telescope = Telescope(
            code="RT32",
            name="RT32",
            x=0.0, y=0.0, z=6371000.0,
            diameter=32.0,
            elevation_range=(15.0, 90.0),
            azimuth_range=(0.0, 360.0),
            isactive=True
        )
        self.telescopes = Telescopes(items={"RT32": self.telescope})

        self.frequency = IF(
            name="IF1",
            frequency=1000.0,
            bandwidth=16.0,
            polarizations=["RCP"],
            isactive=True
        )
        self.frequencies = Frequencies(items={"IF1": self.frequency})

        self.scan = Scan(
            name="scan1",
            start=Time("2025-04-15T00:00:00"),
            duration=600.0,
            source_name="M87",
            telescope_names=["RT32"],
            frequency_names=["IF1"],
            isactive=True
        )
        self.scans = Scans(items={"scan1": self.scan})

        self.obs = Observation(
            name="TEST_OBS",
            observation_type="VLBI",
            sources=self.sources,
            telescopes=self.telescopes,
            frequencies=self.frequencies,
            scans=self.scans,
            isactive=True
        )

    def tearDown(self):
        """Clean up test fixtures."""
        logger.removeHandler(self.logger_handler)

    def test_initialization(self):
        """Test Observation initialization."""
        self.assertEqual(self.obs.get_observation_code(), "TEST_OBS")
        self.assertEqual(self.obs.get_observation_type(), "VLBI")
        self.assertTrue(self.obs.isactive)
        self.assertEqual(self.obs.get_sources(), self.sources)
        self.assertEqual(self.obs.get_telescopes(), self.telescopes)
        self.assertEqual(self.obs.get_frequencies(), self.frequencies)
        self.assertEqual(self.obs.get_scans(), self.scans)
        self.assertEqual(self.obs.get_calculated_data(), {})

    def test_initialization_with_calculated_data(self):
        """Test Observation initialization with explicit calculated_data."""
        calc_data = {"test_key": [1, 2, 3]}
        obs = Observation(
            name="TEST_CALC",
            observation_type="VLBI",
            sources=self.sources,
            telescopes=self.telescopes,
            frequencies=self.frequencies,
            scans=self.scans,
            calculated_data=calc_data,
            isactive=True
        )
        self.assertEqual(obs.get_calculated_data(), calc_data)
        obs_dict = obs.to_dict()
        self.assertEqual(obs_dict["calculated_data"], calc_data)
        new_obs = Observation.from_dict(obs_dict)
        self.assertEqual(new_obs.get_calculated_data(), calc_data)

    def test_invalid_observation_type(self):
        """Test initialization with invalid observation type."""
        with self.assertRaises(ValueError):
            Observation(name="INVALID", observation_type="INVALID")

    def test_invalid_types(self):
        """Test initialization with incorrect types."""
        with self.assertRaises(TypeError):
            Observation(name=123)
        with self.assertRaises(TypeError):
            Observation(name="TEST", sources="not_sources")

    def test_set_attributes(self):
        """Test setting attributes using set method."""
        self.obs.set({
            "name": "NEW_OBS",
            "observation_type": "SINGLE_DISH",
            "sources": Sources(),
            "telescopes": Telescopes(),
            "frequencies": Frequencies(),
            "scans": Scans()
        })
        self.obs.deactivate()
        self.assertEqual(self.obs.get_observation_code(), "NEW_OBS")
        self.assertEqual(self.obs.get_observation_type(), "SINGLE_DISH")
        self.assertFalse(self.obs.isactive)
        self.assertEqual(len(self.obs.get_sources().get_items()), 0)
        self.assertEqual(len(self.obs.get_telescopes().get_items()), 0)
        self.assertEqual(len(self.obs.get_frequencies().get_items()), 0)
        self.assertEqual(len(self.obs.get_scans().get_items()), 0)

    def test_calculated_data(self):
        """Test setting and getting calculated data."""
        self.obs.set_calculated_data_by_key("uv_coverage", np.array([1, 2, 3]))
        self.assertEqual(self.obs.get_calculated_data_by_key("uv_coverage").tolist(), [1, 2, 3])
        self.assertIsNone(self.obs.get_calculated_data_by_key("missing_key"))
        new_data = {"beam": [4, 5, 6]}
        self.obs.set({"calculated_data": new_data})
        self.assertEqual(self.obs.get_calculated_data(), new_data)

    def test_get_start_datetime(self):
        """Test retrieving the earliest scan start time."""
        start_time = self.obs.get_start_datetime()
        self.assertEqual(start_time, Time("2025-04-15T00:00:00"))
        empty_scans = Scans()
        self.obs.set({"scans": empty_scans})
        self.assertIsNone(self.obs.get_start_datetime())

    def test_validate(self):
        """Test observation validation."""
        self.assertTrue(self.obs.validate())
        # Test with no active entities
        self.obs.get_sources().deactivate_item("M87")
        self.assertFalse(self.obs.validate())
        self.obs.get_sources().activate_item("M87")
        self.obs.get_telescopes().deactivate_item("RT32")
        self.assertFalse(self.obs.validate())
        self.obs.get_telescopes().activate_item("RT32")
        self.obs.get_frequencies().deactivate_item("IF1")
        self.assertFalse(self.obs.validate())
        self.obs.get_frequencies().activate_item("IF1")
        self.obs.get_scans().deactivate_item("scan1")
        self.assertFalse(self.obs.validate())

    def test_validate_overlap(self):
        """Test validation with non-overlapping scans."""
        scan2 = Scan(
            name="scan2",
            start=Time("2025-04-15T00:15:00"),
            duration=600.0,
            source_name="M87",
            telescope_names=["RT32"],
            frequency_names=["IF1"],
            isactive=True
        )
        self.obs.get_scans().add(scan2, self.obs)
        self.assertTrue(self.obs.validate())

    def test_update_scan_names(self):
        """Test updating scan names after entity removal."""
        # Remove source
        self.obs._update_scan_names("sources", "M87", "remove")
        scan = self.obs.get_scans().get("scan1")
        self.assertIsNone(scan.get_source_name())
        self.assertTrue(scan.is_off_source)

        # Remove telescope
        self.obs._update_scan_names("telescopes", "RT32", "remove")
        scan = self.obs.get_scans().get("scan1")
        self.assertEqual(scan.get_telescope_names(), [])

        # Remove frequency
        self.obs._update_scan_names("frequencies", "IF1", "remove")
        scan = self.obs.get_scans().get("scan1")
        self.assertEqual(scan.get_frequency_names(), [])

    def test_sync_scans_with_activation(self):
        """Test synchronizing scans with entity activation/deactivation."""
        # Deactivate source
        self.obs._sync_scans_with_activation("sources", "M87", False)
        scan = self.obs.get_scans().get("scan1")
        self.assertIsNone(scan.get_source_name())
        self.assertTrue(scan.is_off_source)

        # Reactivate source
        self.obs._sync_scans_with_activation("sources", "M87", True)
        self.assertEqual(scan.get_source_name(), "M87")
        self.assertFalse(scan.is_off_source)

        # Deactivate telescope
        self.obs._sync_scans_with_activation("telescopes", "RT32", False)
        self.assertEqual(self.obs.get_scans().get("scan1").get_telescope_names(), [])

        # Reactivate telescope
        self.obs.get_scans().get("scan1").set({"original_telescope_names": ["RT32"]})
        self.obs._sync_scans_with_activation("telescopes", "RT32", True)
        self.assertIn("RT32", self.obs.get_scans().get("scan1").get_telescope_names())

        # Deactivate frequency
        self.obs._sync_scans_with_activation("frequencies", "IF1", False)
        self.assertEqual(self.obs.get_scans().get("scan1").get_frequency_names(), [])

        # Reactivate frequency
        self.obs.get_scans().get("scan1").set({"original_frequency_names": ["IF1"]})
        self.obs._sync_scans_with_activation("frequencies", "IF1", True)
        self.assertIn("IF1", self.obs.get_scans().get("scan1").get_frequency_names())

    def test_serialization(self):
        """Test to_dict and from_dict methods."""
        obs_dict = self.obs.to_dict()
        self.assertEqual(obs_dict["name"], "TEST_OBS")
        self.assertEqual(obs_dict["observation_type"], "VLBI")
        self.assertTrue(obs_dict["isactive"])
        self.assertEqual(len(obs_dict["sources"]["items"]), 1)
        self.assertEqual(len(obs_dict["telescopes"]["items"]), 1)
        self.assertEqual(len(obs_dict["frequencies"]["items"]), 1)
        self.assertEqual(len(obs_dict["scans"]["items"]), 1)
        self.assertEqual(obs_dict["scans"]["items"]["scan1"]["source_name"], "M87")
        self.assertEqual(obs_dict["scans"]["items"]["scan1"]["telescope_names"], ["RT32"])
        self.assertEqual(obs_dict["scans"]["items"]["scan1"]["frequency_names"], ["IF1"])
        new_obs = Observation.from_dict(obs_dict)
        self.assertEqual(new_obs.get_observation_code(), self.obs.get_observation_code())
        self.assertEqual(new_obs.get_observation_type(), self.obs.get_observation_type())
        self.assertEqual(new_obs.isactive, self.obs.isactive)
        self.assertEqual(len(new_obs.get_sources().get_items()), len(self.obs.get_sources().get_items()))
        self.assertEqual(len(new_obs.get_telescopes().get_items()), len(self.obs.get_telescopes().get_items()))
        self.assertEqual(len(new_obs.get_frequencies().get_items()), len(self.obs.get_frequencies().get_items()))
        self.assertEqual(len(new_obs.get_scans().get_items()), len(self.obs.get_scans().get_items()))
        self.assertEqual(new_obs.get_scans().get("scan1").get_source_name(), "M87")
        self.assertEqual(new_obs.get_scans().get("scan1").get_telescope_names(), ["RT32"])
        self.assertEqual(new_obs.get_scans().get("scan1").get_frequency_names(), ["IF1"])

    def test_serialization_with_calculated_data(self):
        """Test serialization with calculated data containing quantities."""
        self.obs.set_calculated_data_by_key("uv_coverage", u.Quantity([1, 2, 3], unit=u.m))
        obs_dict = self.obs.to_dict()
        self.assertEqual(obs_dict["calculated_data"]["uv_coverage"], [1, 2, 3])
        new_obs = Observation.from_dict(obs_dict)
        self.assertEqual(new_obs.get_calculated_data_by_key("uv_coverage"), [1, 2, 3])

    def test_equality(self):
        """Test equality comparison."""
        obs2 = Observation(
            name="TEST_OBS",
            observation_type="VLBI",
            sources=self.sources.clone(),
            telescopes=self.telescopes.clone(),
            frequencies=self.frequencies.clone(),
            scans=self.scans.clone(),
            isactive=True
        )
        self.assertEqual(self.obs, obs2)
        obs2.set({"name": "DIFFERENT"})
        self.assertNotEqual(self.obs, obs2)

    def test_contains_and_getitem(self):
        """Test __contains__ and __getitem__."""
        self.assertIn("name", self.obs)
        self.assertEqual(self.obs["name"], "TEST_OBS")
        with self.assertRaises(KeyError):
            _ = self.obs["invalid_key"]

    def test_sync_scans_with_activation(self):
        """Test synchronizing scans with entity activation/deactivation."""
        # Deactivate source
        self.obs._sync_scans_with_activation("sources", "M87", False)
        scan = self.obs.get_scans().get("scan1")
        self.assertIsNone(scan.get_source_name())
        self.assertTrue(scan.is_off_source)

        # Reactivate source
        self.obs._sync_scans_with_activation("sources", "M87", True)
        self.assertEqual(scan.get_source_name(), "M87")
        self.assertFalse(scan.is_off_source)

        # Deactivate telescope
        self.obs._sync_scans_with_activation("telescopes", "RT32", False)
        self.assertEqual(self.obs.get_scans().get("scan1").get_telescope_names(), [])

        # Reactivate telescope
        self.obs.get_scans().get("scan1").set({"original_telescope_names": ["RT32"]})
        print('ORIGINAL:', self.obs.get_scans().get("scan1").get("original_telescope_names"))
        print('TELESCOPES:', self.obs.get_scans().get("scan1").get_telescope_names())
        print('TELESCOPES CONTAINER:', list(self.telescopes.get_items()))
        self.telescopes.activate_item("RT32")
        print('TELESCOPE ACTIVE:', self.telescopes.get("RT32").isactive)
        self.obs._sync_scans_with_activation("telescopes", "RT32", True)
        print('AFTER SYNC:', self.obs.get_scans().get("scan1").get_telescope_names())

        # Deactivate frequency
        self.obs._sync_scans_with_activation("frequencies", "IF1", False)
        self.assertEqual(self.obs.get_scans().get("scan1").get_frequency_names(), [])

        # Reactivate frequency
        self.obs.get_scans().get("scan1").set({"original_frequency_names": ["IF1"]})
        print('ORIGINAL FREQS:', self.obs.get_scans().get("scan1").get("original_frequency_names"))
        print('FREQUENCIES CONTAINER:', list(self.frequencies.get_items()))
        self.frequencies.activate_item("IF1")
        print('FREQUENCY ACTIVE:', self.frequencies.get("IF1").isactive)
        self.obs._sync_scans_with_activation("frequencies", "IF1", True)
        print('AFTER SYNC FREQS:', self.obs.get_scans().get("scan1").get_frequency_names())

if __name__ == "__main__":
    unittest.main()