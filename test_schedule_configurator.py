import unittest
from unittest.mock import MagicMock, patch
from astropy.time import Time
from unit_scheduling_2.super.schedule_configurator import ScheduleConfigurator
from unit_scheduling_2.super.schedule_project import ScheduleProject
from unit_scheduling_2.base.frequencies import IF, Frequencies
from unit_scheduling_2.base.sources import Source, Sources
from unit_scheduling_2.base.telescopes import Telescope, SpaceTelescope, Telescopes
from unit_scheduling_2.base.scans import Scan, Scans
from unit_scheduling_2.base.observation import Observation

class TestScheduleConfigurator(unittest.TestCase):
    def setUp(self):
        """Set up the test environment with a mocked Manipulator and logger."""
        self.manipulator = MagicMock()
        self.manipulator.get_methods.side_effect = lambda cls: {
            IF: ["set"],
            Frequencies: ["add", "set_items"],
            Source: ["set", "set_ra_degrees", "set_dec_degrees", "add_flux"],
            Sources: ["add", "create_source"],
            Telescope: ["set", "add_sefd"],
            SpaceTelescope: ["set", "set_keplerian", "set_orbit"],
            Telescopes: ["add", "create_telescope"],
            Scan: ["set", "set_start", "set_duration", "set_source_name", "set_telescope_names", "set_frequency_names"],
            Scans: ["add", "create_scan"],
            Observation: ["set", "set_calculated_data_by_key"],
            ScheduleProject: ["add_item", "create_item", "set_project"]
        }.get(cls, [])
        self.configurator = ScheduleConfigurator(self.manipulator)
        self.patcher = patch('unit_scheduling_2.super.schedule_configurator.logger')
        self.mock_logger = self.patcher.start()

    def tearDown(self):
        """Clean up the logger patch."""
        self.patcher.stop()

    def test_configure_if(self):
        """Test configuring an IF object."""
        if_obj = IF()
        attributes = {"set": {"frequency": 1420.0, "bandwidth": 20.0}}
        result = self.configurator.execute(if_obj, attributes)
        self.assertTrue(result)
        self.assertEqual(if_obj.frequency, 1420.0)
        self.assertEqual(if_obj.bandwidth, 20.0)
        self.mock_logger.info.assert_called_with("Configured IF: frequency=1420.0, bandwidth=20.0")

    def test_configure_if_invalid_method(self):
        """Test configuring an IF with an invalid method."""
        if_obj = IF()
        attributes = {"invalid_method": {"value": 1}}
        result = self.configurator.execute(if_obj, attributes)
        self.assertFalse(result)
        self.mock_logger.warning.assert_called_with("No valid methods applied for IF configuration")

    def test_configure_frequencies_nested(self):
        """Test configuring a nested IF within Frequencies."""
        freq_obj = Frequencies()
        if_obj = IF(name="IF1")
        freq_obj.add(if_obj)
        attributes = {"if_name": "IF1", "set": {"frequency": 1420.0, "bandwidth": 20.0}}
        result = self.configurator.execute(freq_obj, attributes)
        self.assertTrue(result)
        self.assertEqual(freq_obj.get("IF1").frequency, 1420.0)
        self.assertEqual(freq_obj.get("IF1").bandwidth, 20.0)
        self.mock_logger.info.assert_called_with("Configured IF: frequency=1420.0, bandwidth=20.0")

    def test_configure_frequencies_nested_not_found(self):
        """Test configuring a nested IF that does not exist."""
        freq_obj = Frequencies()
        attributes = {"if_name": "IF1", "set": {"frequency": 1420.0}}
        result = self.configurator.execute(freq_obj, attributes)
        self.assertFalse(result)
        self.mock_logger.warning.assert_called_with("IF 'IF1' not found in Frequencies")

    def test_configure_source(self):
        """Test configuring a Source object."""
        source_obj = Source()
        attributes = {
            "set": {
                "name": "3C 286",
                "ra_h": 13,
                "ra_m": 31,
                "ra_s": 8.287,
                "de_d": 30,
                "de_m": 41,
                "de_s": 31.0
            }
        }
        result = self.configurator.execute(source_obj, attributes)
        self.assertTrue(result)
        self.assertEqual(source_obj.name, "3C 286")
        self.mock_logger.info.assert_called_with("Configured Source: name='3C 286'")

    def test_configure_sources_nested(self):
        """Test configuring a nested Source within Sources."""
        sources_obj = Sources()
        source_obj = Source(name="SOURCE1")
        sources_obj.add(source_obj)
        attributes = {"source_name": "SOURCE1", "set": {"name": "3C 286"}}
        result = self.configurator.execute(sources_obj, attributes)
        self.assertTrue(result)
        self.assertEqual(sources_obj.get("3C 286").name, "3C 286")
        self.mock_logger.info.assert_called_with("Configured Source: name='3C 286'")

    def test_configure_sources_nested_not_found(self):
        """Test configuring a nested Source that does not exist."""
        sources_obj = Sources()
        attributes = {"source_name": "SOURCE1", "set": {"name": "3C 286"}}
        result = self.configurator.execute(sources_obj, attributes)
        self.assertFalse(result)
        self.mock_logger.warning.assert_called_with("Source 'SOURCE1' not found in Sources")

    def test_configure_telescope(self):
        """Test configuring a Telescope object."""
        tel_obj = Telescope()
        attributes = {"set": {"code": "GBT", "x": 0.0, "y": 0.0, "z": 0.0}}
        result = self.configurator.execute(tel_obj, attributes)
        self.assertTrue(result)
        self.assertEqual(tel_obj.get_code(), "GBT")
        self.mock_logger.info.assert_called_with("Configured Telescope: code='GBT'")

    def test_configure_space_telescope(self):
        """Test configuring a SpaceTelescope object."""
        tel_obj = SpaceTelescope()
        attributes = {
            "set": {"code": "HST"},
            "set_keplerian": {
                "a": 7000e3,
                "e": 0.01,
                "i": 0.0,
                "raan": 0.0,
                "argp": 0.0,
                "nu": 0.0,
                "epoch": Time("2025-04-16T12:00:00"),
                "mu": 398600.4418e9
            }
        }
        result = self.configurator.execute(tel_obj, attributes)
        self.assertTrue(result)
        self.assertEqual(tel_obj.get_code(), "HST")
        self.mock_logger.info.assert_called_with("Configured SpaceTelescope: code='HST'")

    def test_configure_telescopes_nested(self):
        """Test configuring a nested Telescope within Telescopes."""
        tels_obj = Telescopes()
        tel_obj = Telescope(code="TEMP")
        tels_obj.add(tel_obj)
        attributes = {"telescope_code": "TEMP", "set": {"code": "VLA"}}
        result = self.configurator.execute(tels_obj, attributes)
        self.assertTrue(result)
        self.assertEqual(tels_obj.get("VLA").get_code(), "VLA")
        self.mock_logger.info.assert_called_with("Configured Telescope: code='VLA'")

    def test_configure_telescopes_nested_not_found(self):
        """Test configuring a nested Telescope that does not exist."""
        tels_obj = Telescopes()
        attributes = {"telescope_code": "VLA", "set": {"code": "VLA"}}
        result = self.configurator.execute(tels_obj, attributes)
        self.assertFalse(result)
        self.mock_logger.warning.assert_called_with("Telescope 'VLA' not found in Telescopes")

    def test_configure_scan(self):
        """Test configuring a Scan object."""
        scan_obj = Scan()
        attributes = {
            "set_start": {"start": Time("2025-04-16T12:00:00")},
            "set_duration": {"duration": 300.0},
            "set_source_name": {"source_name": "3C 286"}
        }
        result = self.configurator.execute(scan_obj, attributes)
        self.assertTrue(result)
        self.assertEqual(scan_obj.get_source_name(), "3C 286")
        self.assertEqual(scan_obj.get_duration(), 300.0)
        self.mock_logger.info.assert_called_with(
            f"Configured Scan: start={scan_obj.get_start().isot}, source_name=3C 286"
        )

    def test_configure_scans_nested(self):
        """Test configuring a nested Scan within Scans."""
        scans_obj = Scans()
        scan_obj = Scan(name="SCAN1")
        scans_obj.add(scan_obj)
        attributes = {"scan_name": "SCAN1", "set_source_name": {"source_name": "3C 286"}}
        result = self.configurator.execute(scans_obj, attributes)
        self.assertTrue(result)
        self.assertEqual(scans_obj.get("SCAN1").get_source_name(), "3C 286")
        self.mock_logger.info.assert_called_with(
            f"Configured Scan: start={scans_obj.get("SCAN1").get_start().isot}, source_name=3C 286"
        )

    def test_configure_scans_nested_not_found(self):
        """Test configuring a nested Scan that does not exist."""
        scans_obj = Scans()
        attributes = {"scan_name": "SCAN1", "set_source_name": {"source_name": "3C 286"}}
        result = self.configurator.execute(scans_obj, attributes)
        self.assertFalse(result)
        self.mock_logger.warning.assert_called_with("Scan 'SCAN1' not found in Scans")

    def test_configure_scans_overlap(self):
        """Test configuring a Scan with overlap detection."""
        scans_obj = Scans()
        scan1 = Scan(name="SCAN1")
        scan2 = Scan(name="SCAN2")
        scan1.set_start(Time("2025-04-16T12:00:00"))
        scan1.set_duration(600.0)
        scan2.set_start(Time("2025-04-16T12:05:00"))
        scans_obj.add(scan1)
        scans_obj.add(scan2)
        attributes = {"scan_name": "SCAN2", "set_duration": {"duration": 600.0}}
        with patch.object(scans_obj, '_check_overlap', return_value=(True, "overlaps with SCAN1")):
            result = self.configurator.execute(scans_obj, attributes)
        self.assertFalse(result)
        self.mock_logger.error.assert_called_with("Modified scan 'SCAN2' overlaps with SCAN1")

    def test_configure_observation(self):
        """Test configuring an Observation object."""
        obs_obj = Observation()
        attributes = {"set": {"observation_code": "OBS001"}}
        with patch.object(Observation, 'validate', return_value=True):
            result = self.configurator.execute(obs_obj, attributes)
        self.assertTrue(result)
        self.assertEqual(obs_obj.get_observation_code(), "OBS001")
        self.mock_logger.info.assert_called_with("Configured Observation: code='OBS001'")

    def test_configure_observation_invalid(self):
        """Test configuring an Observation that fails validation."""
        obs_obj = Observation()
        attributes = {"set": {"observation_code": "OBS001"}}
        with patch.object(Observation, 'validate', return_value=False):
            result = self.configurator.execute(obs_obj, attributes)
        self.assertFalse(result)
        self.mock_logger.error.assert_called_with("Observation 'OBS001' invalid after configuration")

    def test_configure_project_nested(self):
        """Test configuring a nested Observation within ScheduleProject."""
        project_obj = ScheduleProject()
        obs_obj = Observation(observation_code="OBS_DEFAULT")
        project_obj.add_item(obs_obj)
        attributes = {"observation_code": "OBS_DEFAULT", "set": {"observation_code": "OBS001"}}
        with patch.object(Observation, 'validate', return_value=True):
            result = self.configurator.execute(project_obj, attributes)
        self.assertTrue(result)
        self.assertEqual(project_obj.get_observation("OBS001").get_observation_code(), "OBS001")
        self.mock_logger.info.assert_called_with("Configured Observation: code='OBS001'")

    def test_configure_project_nested_not_found(self):
        """Test configuring a nested Observation that does not exist."""
        project_obj = ScheduleProject()
        attributes = {"observation_code": "OBS001", "set": {"observation_code": "OBS001"}}
        with patch.object(Observation, 'validate', return_value=True):
            result = self.configurator.execute(project_obj, attributes)
        self.assertFalse(result)
        self.mock_logger.warning.assert_called_with("Observation 'OBS001' not found in ScheduleProject")

    def test_configure_invalid_object(self):
        """Test configuring an invalid object type."""
        invalid_obj = object()  # Generic object not supported by configurator
        attributes = {"set": {"some_param": "value"}}
        result = self.configurator.execute(invalid_obj, attributes)
        self.assertFalse(result)
        self.mock_logger.warning.assert_any_call("No configuration method found for object")

if __name__ == '__main__':
    unittest.main()