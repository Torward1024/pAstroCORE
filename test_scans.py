# tests/test_scans.py
import unittest
from unittest.mock import MagicMock, PropertyMock
from astropy.time import Time
import numpy as np
import astropy.units as u
from common.utils.logging_setup import logger
from unit_scheduling_2.base.scans import Scan, Scans
from unit_scheduling_2.base.observation import Observation
from unit_scheduling_2.base.sources import Source
from unit_scheduling_2.base.telescope import Telescope
from unit_scheduling_2.base.spacetelescope import SpaceTelescope
from unit_scheduling_2.base.telescopes import Telescopes
from unit_scheduling_2.base.frequencies import IF, Frequencies

class TestScan(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.start = Time("2025-04-06T00:00:00")
        self.scan = Scan(
            name="scan1",
            start=self.start,
            duration=600.0,
            source_name="source1",
            telescope_names=["TEL1", "TEL2"],
            frequency_names=["FREQ1"],
            is_off_source=False,
            isactive=True
        )
        self.observation = MagicMock(spec=Observation)
        self.observation.get_observation_code.return_value = "OBS001"
        source = MagicMock(spec=Source)
        source.name = "source1"
        source.isactive = True
        
        type(source).ra_degrees = PropertyMock(return_value=180.0)
        type(source).dec_degrees = PropertyMock(return_value=30.0)
        type(source).ra_degrees = PropertyMock(return_value=180.0)
        type(source).dec_degrees = PropertyMock(return_value=30.0)
        
        sources_container = MagicMock()
        sources_container.get.side_effect = lambda x: {"source1": source}.get(x)  # Returns None for invalid_source
        sources_container._items = {"source1": source}
        self.observation.get_sources.return_value = sources_container
        self.observation.get_sources.return_value = sources_container
        telescope1 = MagicMock(spec=Telescope)
        telescope1.name = "TEL1"
        telescope1.isactive = True
        telescope1.get_code.return_value = "TEL1"
        telescope1.get_coordinates.return_value = (0, 0, 6371e3)
        telescope1.get_elevation_range.return_value = (5, 85)
        telescope1.get_azimuth_range.return_value = (0, 360)
        telescope2 = MagicMock(spec=SpaceTelescope)
        telescope2.name = "TEL2"
        telescope2.isactive = True
        telescope2.get_code.return_value = "TEL2"
        telescope2.get_state_vector.return_value = (np.array([1e6, 0, 0]), np.array([0, 0, 0]))
        telescope2.get_pitch_range.return_value = (-90, 90)
        telescope2.get_yaw_range.return_value = (-180, 180)
        telescopes_container = MagicMock()
        telescopes_container.get.side_effect = lambda x: {"TEL1": telescope1, "TEL2": telescope2}.get(x)
        telescopes_container._items = {"TEL1": telescope1, "TEL2": telescope2}
        telescopes_container.get_all_telescopes.return_value = [telescope1, telescope2]
        telescopes_container.get_active_telescopes.return_value = [telescope1, telescope2]
        self.observation.get_telescopes.return_value = telescopes_container
        freq = MagicMock(spec=IF)
        freq.name = "FREQ1"
        freq.isactive = True
        freq.frequency = 1000.0  # Add frequency attribute
        freq.bandwidth = 16.0    # Add bandwidth attribute
        frequencies_container = MagicMock()
        frequencies_container.get.return_value = freq
        frequencies_container._items = {"FREQ1": freq}
        frequencies_container.get_all_IF.return_value = [freq]
        self.observation.get_frequencies.return_value = frequencies_container

    def test_init(self):
        """Test Scan initialization."""
        self.assertEqual(self.scan.name, "scan1")
        self.assertEqual(self.scan.start, self.start)
        self.assertEqual(self.scan.duration, 600.0)
        self.assertEqual(self.scan.source_name, "source1")
        self.assertEqual(self.scan.telescope_names, ["TEL1", "TEL2"])
        self.assertEqual(self.scan.frequency_names, ["FREQ1"])
        self.assertFalse(self.scan.is_off_source)
        self.assertTrue(self.scan.isactive)
        self.assertEqual(self.scan.original_telescope_names, ["TEL1", "TEL2"])
        self.assertEqual(self.scan.original_frequency_names, ["FREQ1"])

    def test_auto_name(self):
        """Test automatic name generation."""
        scan = Scan(start=self.start, duration=600.0)
        self.assertTrue(scan.name.startswith("scan_"))
        self.assertEqual(len(scan.name), 37)  # scan_ + 32 chars

    def test_get_methods(self):
        """Test getter methods."""
        self.assertEqual(self.scan.get_start(), self.start)
        self.assertEqual(self.scan.get_duration(), 600.0)
        self.assertEqual(self.scan.get_source_name(), "source1")
        self.assertEqual(self.scan.get_telescope_names(), ["TEL1", "TEL2"])
        self.assertEqual(self.scan.get_frequency_names(), ["FREQ1"])
        self.assertEqual(self.scan.get_end(), self.start + 600.0 * u.s)
        self.assertAlmostEqual(self.scan.get_MJD_starttime(), self.start.mjd)
        self.assertAlmostEqual(self.scan.get_MJD_endtime(), (self.start + 600.0 * u.s).mjd)

    def test_set_methods(self):
        """Test setter methods."""
        new_start = Time("2025-04-06T01:00:00")
        self.scan.set_start(new_start)
        self.assertEqual(self.scan.start, new_start)
        
        self.scan.set_duration(1200.0)
        self.assertEqual(self.scan.duration, 1200.0)
        
        self.scan.set_source_name("source2")
        self.assertEqual(self.scan.source_name, "source2")
        
        self.scan.set_telescope_names(["TEL3"])
        self.assertEqual(self.scan.telescope_names, ["TEL3"])
        
        self.scan.set_frequency_names(["FREQ2"])
        self.assertEqual(self.scan.frequency_names, ["FREQ2"])

    def test_invalid_duration(self):
        """Test invalid duration raises ValueError."""
        with self.assertRaises(ValueError):
            Scan(name="scan2", start=self.start, duration=-1.0)

    def test_get_source(self):
        """Test retrieving source from observation."""
        source = self.scan.get_source(self.observation)
        self.assertIsNotNone(source)
        self.assertEqual(source.ra_degrees, 180.0)

    def test_get_telescopes(self):
        """Test retrieving telescopes from observation."""
        telescopes = self.scan.get_telescopes(self.observation)
        self.assertIsInstance(telescopes, Telescopes)
        self.assertEqual(len(telescopes.get_items()), 2)

    def test_get_frequencies(self):
        """Test retrieving frequencies from observation."""
        frequencies = self.scan.get_frequencies(self.observation)
        self.assertIsInstance(frequencies, Frequencies)
        self.assertEqual(len(frequencies.get_items()), 1)

    def test_validate_with_observation(self):
        """Test validation against observation."""
        self.assertTrue(self.scan.validate_with_observation(self.observation))
        
        invalid_scan = Scan(name="scan3", source_name="invalid_source")
        self.assertFalse(invalid_scan.validate_with_observation(self.observation))

    def test_check_telescope_availability(self):
        """Test checking telescope availability."""
        availability = self.scan.check_telescope_availability(self.observation)
        self.assertIn("TEL1", availability)
        self.assertIn("TEL2", availability)
        self.assertTrue(availability["TEL2"])  # Space telescope simplified check

    def test_to_dict_from_dict(self):
        """Test serialization and deserialization."""
        scan_dict = self.scan.to_dict()
        self.assertEqual(scan_dict["name"], "scan1")
        self.assertEqual(scan_dict["start"], self.start.isot)
        self.assertEqual(scan_dict["duration"], 600.0)
        
        new_scan = Scan.from_dict(scan_dict)
        self.assertEqual(new_scan.name, self.scan.name)
        self.assertEqual(new_scan.start, self.scan.start)
        self.assertEqual(new_scan.duration, self.scan.duration)
        self.assertEqual(new_scan.isactive, self.scan.isactive)

    def test_activate_deactivate(self):
        """Test activation and deactivation."""
        self.scan.deactivate()
        self.assertFalse(self.scan.isactive)
        self.scan.activate()
        self.assertTrue(self.scan.isactive)

    def test_clone(self):
        """Test cloning a scan."""
        clone = self.scan.clone()
        self.assertEqual(clone.name, self.scan.name)
        self.assertEqual(clone.start, self.scan.start)
        self.assertNotEqual(id(clone), id(self.scan))

    def test_equality(self):
        """Test equality comparison."""
        scan2 = Scan(
            name="scan1",
            start=self.start,
            duration=600.0,
            source_name="source1",
            telescope_names=["TEL1", "TEL2"],
            frequency_names=["FREQ1"]
        )
        self.assertEqual(self.scan, scan2)
        scan2.set_duration(1200.0)
        self.assertNotEqual(self.scan, scan2)


class TestScans(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.start = Time("2025-04-06T00:00:00")
        self.scan1 = Scan(
            name="scan1",
            start=self.start,
            duration=600.0,
            source_name="source1",
            telescope_names=["TEL1"],
            frequency_names=["FREQ1"],
            isactive=True
        )
        self.scan2 = Scan(
            name="scan2",
            start=self.start + 600.0 * u.s,
            duration=600.0,
            source_name="source2",
            telescope_names=["TEL2"],
            frequency_names=["FREQ2"],
            isactive=False
        )
        self.scans = Scans(name="test_scans")
        self.observation = MagicMock(spec=Observation)
        self.observation.get_observation_code.return_value = "OBS001"
        source1 = MagicMock(spec=Source)
        source1.name = "source1"
        source1.isactive = True
        source2 = MagicMock(spec=Source)
        source2.name = "source2"
        source2.isactive = False
        sources_container = MagicMock()
        sources_container.get.side_effect = lambda x: {"source1": source1, "source2": source2}.get(x)
        sources_container._items = {"source1": source1, "source2": source2}
        self.observation.get_sources.return_value = sources_container
        telescope1 = MagicMock(spec=Telescope)
        telescope1.name = "TEL1"
        telescope1.isactive = True
        telescope2 = MagicMock(spec=Telescope)
        telescope2.name = "TEL2"
        telescope2.isactive = False
        telescopes_container = MagicMock()
        telescopes_container.get.side_effect = lambda x: {"TEL1": telescope1, "TEL2": telescope2}.get(x)
        telescopes_container._items = {"TEL1": telescope1, "TEL2": telescope2}
        self.observation.get_telescopes.return_value = telescopes_container
        freq1 = MagicMock(spec=IF)
        freq1.name = "FREQ1"
        freq1.isactive = True
        freq2 = MagicMock(spec=IF)
        freq2.name = "FREQ2"
        freq2.isactive = False
        frequencies_container = MagicMock()
        frequencies_container.get.side_effect = lambda x: {"FREQ1": freq1, "FREQ2": freq2}.get(x)
        frequencies_container._items = {"FREQ1": freq1, "FREQ2": freq2}
        self.observation.get_frequencies.return_value = frequencies_container

    def test_init(self):
        """Test Scans initialization."""
        self.assertEqual(self.scans.name, "test_scans")
        self.assertTrue(self.scans.isactive)
        self.assertEqual(len(self.scans), 0)

    def test_add_scan(self):
        """Test adding a scan."""
        self.scans.add(self.scan1, self.observation)
        self.assertEqual(len(self.scans), 1)
        self.assertEqual(self.scans.get("scan1"), self.scan1)

    def test_create_scan(self):
        """Test creating and adding a scan."""
        self.scans.create_scan(
            name="scan3",
            start=self.start + 1200.0 * u.s,
            duration=600.0,
            source_name="source1",
            telescope_names=["TEL1"],
            frequency_names=["FREQ1"],
            observation=self.observation
        )
        self.assertEqual(len(self.scans), 1)
        self.assertTrue(self.scans.has_item("scan3"))

    def test_overlap_conflict(self):
        """Test adding a scan with overlapping time raises ValueError."""
        self.scans.add(self.scan1)
        overlap_scan = Scan(
            name="scan4",
            start=self.start + 300.0 * u.s,
            duration=600.0,
            source_name="source1",
            telescope_names=["TEL1"],
            frequency_names=["FREQ1"]
        )
        with self.assertRaises(ValueError):
            self.scans.add(overlap_scan)

    def test_remove_scan(self):
        """Test removing a scan."""
        self.scans.add(self.scan1)
        self.scans.remove("scan1")
        self.assertEqual(len(self.scans), 0)
        self.assertFalse(self.scans.has_item("scan1"))

    def test_get_active_scans(self):
        """Test retrieving active scans."""
        self.scans.add(self.scan1)
        self.scans.add(self.scan2)
        active = self.scans.get_active_scans()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0], self.scan1)
        
        active_obs = self.scans.get_active_scans(self.observation)
        self.assertEqual(len(active_obs), 1)  # scan2 has inactive source/telescope/frequency

    def test_get_inactive_scans(self):
        """Test retrieving inactive scans."""
        self.scans.add(self.scan1)
        self.scans.add(self.scan2)
        inactive = self.scans.get_inactive_scans()
        self.assertEqual(len(inactive), 1)
        self.assertEqual(inactive[0], self.scan2)

    def test_activate_deactivate_item(self):
        """Test activating and deactivating a scan."""
        self.scans.add(self.scan1)
        self.scans.deactivate_item("scan1")
        self.assertFalse(self.scans.get("scan1").isactive)
        self.scans.activate_item("scan1")
        self.assertTrue(self.scans.get("scan1").isactive)

    def test_activate_deactivate_all(self):
        """Test activating and deactivating all scans."""
        self.scans.add(self.scan1)
        self.scans.add(self.scan2)
        self.scans.deactivate_all()
        self.assertEqual(len(self.scans.get_active_scans()), 0)
        self.scans.activate_all()
        self.assertEqual(len(self.scans.get_active_scans()), 2)

    def test_drop_active_inactive(self):
        """Test dropping active and inactive scans."""
        self.scans.add(self.scan1)
        self.scans.add(self.scan2)
        self.scans.drop_active()
        self.assertEqual(len(self.scans), 1)
        self.assertEqual(self.scans.get("scan2"), self.scan2)
        
        self.scans.add(self.scan1)
        self.scans.drop_inactive()
        self.assertEqual(len(self.scans), 1)
        self.assertEqual(self.scans.get("scan1"), self.scan1)

    def test_clear(self):
        """Test clearing all scans."""
        self.scans.add(self.scan1)
        self.scans.add(self.scan2)
        self.scans.clear()
        self.assertEqual(len(self.scans), 0)

    def test_to_dict_from_dict(self):
        """Test serialization and deserialization."""
        self.scans.add(self.scan1)
        scans_dict = self.scans.to_dict()
        self.assertEqual(len(scans_dict["items"]), 1)
        self.assertEqual(scans_dict["items"]["scan1"]["name"], "scan1")
        
        new_scans = Scans.from_dict(scans_dict)
        self.assertEqual(len(new_scans), 1)
        self.assertEqual(new_scans.get("scan1").start, self.scan1.start)

    def test_clone(self):
        """Test cloning Scans."""
        self.scans.add(self.scan1)
        clone = self.scans.clone()
        self.assertEqual(len(clone), 1)
        self.assertEqual(clone.get("scan1").start, self.scan1.start)
        self.assertNotEqual(id(clone), id(self.scans))

    def test_equality(self):
        """Test equality comparison."""
        self.scans.add(self.scan1)
        other_scans = Scans(name="test_scans")
        other_scans.add(self.scan1)
        self.assertEqual(self.scans, other_scans)
        other_scans.add(self.scan2)
        self.assertNotEqual(self.scans, other_scans)

    def test_iteration(self):
        """Test iterating over scans."""
        self.scans.add(self.scan1)
        self.scans.add(self.scan2)
        scans_list = list(self.scans)
        self.assertEqual(len(scans_list), 2)
        self.assertIn(self.scan1, scans_list)
        self.assertIn(self.scan2, scans_list)

    def test_contains(self):
        """Test checking if a scan exists."""
        self.scans.add(self.scan1)
        self.assertTrue("scan1" in self.scans)
        self.assertFalse("scan2" in self.scans)


if __name__ == "__main__":
    unittest.main()