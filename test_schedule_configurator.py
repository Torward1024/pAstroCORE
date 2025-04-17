import unittest
from unittest.mock import MagicMock, patch
from astropy.time import Time
from unit_scheduling_2.super.schedule_configurator import ScheduleConfigurator
#from unit_scheduling_2.super.schedule_configurator_mshch import ScheduleConfigurator
from unit_scheduling_2.super.schedule_project import ScheduleProject
from unit_scheduling_2.base.frequencies import IF, Frequencies
from unit_scheduling_2.base.sources import Source, Sources
from unit_scheduling_2.base.telescopes import Telescope, SpaceTelescope, Telescopes
from unit_scheduling_2.base.scans import Scan, Scans
from unit_scheduling_2.base.observation import Observation


class TestScheduleConfigurator(unittest.TestCase):
    def setUp(self):
        """Set up the test environment with a mocked Manipulator."""
        self.manipulator = MagicMock()
        self.manipulator.get_methods_for_type.side_effect = lambda cls: {
            IF: {"set": getattr(IF, "set")},
            Frequencies: {"add": getattr(Frequencies, "add"), "set_items": getattr(Frequencies, "set_items")},
            Source: {
                "set": getattr(Source, "set"),
                "set_ra_degrees": getattr(Source, "set_ra_degrees"),
                "set_dec_degrees": getattr(Source, "set_dec_degrees"),
                "add_flux": getattr(Source, "add_flux")
            },
            Sources: {"add": getattr(Sources, "add"), "create_source": getattr(Sources, "create_source")},
            Telescope: {"set": getattr(Telescope, "set"), "add_sefd": getattr(Telescope, "add_sefd")},
            SpaceTelescope: {
                "set": getattr(SpaceTelescope, "set"),
                "set_keplerian": getattr(SpaceTelescope, "set_keplerian"),
                "set_orbit": getattr(SpaceTelescope, "set_orbit")
            },
            Telescopes: {"add": getattr(Telescopes, "add"), "create_telescope": getattr(Telescopes, "create_telescope")},
            Scan: {
                "set": getattr(Scan, "set"),
                "set_start": getattr(Scan, "set_start"),
                "set_duration": getattr(Scan, "set_duration"),
                "set_source_name": getattr(Scan, "set_source_name"),
                "set_telescope_names": getattr(Scan, "set_telescope_names"),
                "set_frequency_names": getattr(Scan, "set_frequency_names")
            },
            Scans: {"add": getattr(Scans, "add"), "create_scan": getattr(Scans, "create_scan")},
            Observation: {"set": getattr(Observation, "set"), "set_calculated_data_by_key": getattr(Observation, "set_calculated_data_by_key")},
            ScheduleProject: {
                "add_item": getattr(ScheduleProject, "add_item"),
                "create_item": getattr(ScheduleProject, "create_item"),
                "set_project": getattr(ScheduleProject, "set_project")
            }
        }.get(cls, {})
        self.configurator = ScheduleConfigurator(self.manipulator)

    def test_configure_if(self):
        """Test configuring an IF object."""
        if_obj = IF(name="IF1")
        attributes = {"set": {"params": {"frequency": 1420.0, "bandwidth": 20.0}}}
        result = self.configurator.execute(if_obj, attributes)
        self.assertTrue(result["status"])
        self.assertEqual(result["method"], "_configure_if")
        self.assertEqual(result["result"], if_obj.get())
        self.assertEqual(if_obj.frequency, 1420.0)
        self.assertEqual(if_obj.bandwidth, 20.0)
        self.assertEqual(result["result"]["frequency"], 1420.0)
        self.assertEqual(result["result"]["bandwidth"], 20.0)

    def test_configure_if_invalid_method(self):
        """Test configuring an IF with an invalid method."""
        if_obj = IF(name="IF1")
        attributes = {"invalid_method": {"value": 1}}
        result = self.configurator.execute(if_obj, attributes)
        self.assertFalse(result["status"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "Method 'invalid_method' not found")

    def test_configure_frequencies_nested(self):
        """Test configuring a nested IF within Frequencies."""
        freq_obj = Frequencies(name="FRSSSQS")
        if_obj = IF(name="IF1")
        freq_obj.add(if_obj)
        attributes = {"name": "IF1", "set": {"params": {"frequency": 1420.0, "bandwidth": 20.0}}}
        result = self.configurator.execute(freq_obj, attributes)
        self.assertTrue(result["status"])
        self.assertEqual(result["method"], "_configure_frequencies")
        self.assertEqual(result["result"], freq_obj.get("IF1").get())
        self.assertEqual(freq_obj.get("IF1").frequency, 1420.0)
        self.assertEqual(freq_obj.get("IF1").bandwidth, 20.0)
        self.assertEqual(result["result"]["frequency"], 1420.0)
        self.assertEqual(result["result"]["bandwidth"], 20.0)

    def test_configure_frequencies_nested_not_found(self):
        """Test configuring a nested IF that does not exist."""
        freq_obj = Frequencies(name="FQS")
        attributes = {"name": "IF1", "set": {"params": {"frequency": 1420.0}}}
        result = self.configurator.execute(freq_obj, attributes)
        self.assertFalse(result["status"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "\"Name 'IF1' not found in Frequencies\"")

    def test_configure_frequencies_direct(self):
        """Test configuring a Frequencies object directly."""
        freq_obj = Frequencies(name="FQS")
        if_obj = IF(name="IF1")
        attributes = {"add": {"if_obj": if_obj}}
        result = self.configurator.execute(freq_obj, attributes)
        self.assertTrue(result["status"])
        self.assertEqual(result["method"], "_configure_frequencies")
        self.assertEqual(result["result"], 1)
        self.assertEqual(len(freq_obj), 1)

    def test_configure_source(self):
        """Test configuring a Source object."""
        source_obj = Source(name="SOURCE1")
        attributes = {
            "set": {
                "params": {
                    "name": "3C 286",
                    "ra_h": 13.0,
                    "ra_m": 31.0,
                    "ra_s": 8.287,
                    "de_d": 30.0,
                    "de_m": 41.0,
                    "de_s": 31.0
                }
            }
        }
        result = self.configurator.execute(source_obj, attributes)
        self.assertTrue(result["status"])
        self.assertEqual(result["method"], "_configure_source")
        self.assertEqual(result["result"], source_obj.get())
        self.assertEqual(source_obj.name, "3C 286")
        self.assertEqual(result["result"]["name"], "3C 286")

    def test_configure_sources_nested(self):
        """Test configuring a nested Source within Sources."""
        sources_obj = Sources(name="SRCS")
        source_obj = Source(name="SOURCE1")
        sources_obj.add(source_obj)
        attributes = {"name": "SOURCE1", "set": {"params": {"name": "3C 286"}}}
        result = self.configurator.execute(sources_obj, attributes)
        self.assertTrue(result["status"])
        self.assertEqual(result["method"], "_configure_sources")
        self.assertEqual(result["result"], sources_obj.get("SOURCE1").get())
        self.assertEqual(sources_obj.get("SOURCE1").name, "3C 286")
        self.assertEqual(result["result"]["name"], "3C 286")

    def test_configure_sources_nested_not_found(self):
        """Test configuring a nested Source that does not exist."""
        sources_obj = Sources(name="SRCSS")
        attributes = {"name": "SOURCE1", "set": {"params": {"name": "3C 286"}}}
        result = self.configurator.execute(sources_obj, attributes)
        self.assertFalse(result["status"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "\"Name 'SOURCE1' not found in Sources\"")

    def test_configure_telescope(self):
        """Test configuring a Telescope object."""
        tel_obj = Telescope(name="TLSCSPS")
        attributes = {"set": {"params": {"code": "GBT", "x": 0.0, "y": 0.0, "z": 0.0}}}
        result = self.configurator.execute(tel_obj, attributes)
        self.assertTrue(result["status"])
        self.assertEqual(result["method"], "_configure_telescope")
        self.assertEqual(result["result"], "GBT")
        self.assertEqual(tel_obj.get_code(), "GBT")

    def test_configure_space_telescope(self):
        """Test configuring a SpaceTelescope object."""
        tel_obj = SpaceTelescope(name="SCPSD")
        attributes = {
            "set": {"params": {"code": "HST"}},
            "method": "_configure_telescope",
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
        self.assertTrue(result["status"])
        self.assertEqual(result["method"], "_configure_telescope")
        self.assertEqual(result["result"], "HST")
        self.assertEqual(tel_obj.get_code(), "HST")

    def test_configure_telescopes_nested(self):
        """Test configuring a nested Telescope within Telescopes."""
        tels_obj = Telescopes(name="TELESCOPEEES")
        tel_obj = Telescope(name="TEMP")
        tels_obj.add(tel_obj)
        attributes = {"name": "TEMP", "set": {"params": {"code": "VLA"}}}
        result = self.configurator.execute(tels_obj, attributes)
        self.assertTrue(result["status"])
        self.assertEqual(result["method"], "_configure_telescopes")
        self.assertEqual(result["result"], "VLA")
        self.assertEqual(tels_obj.get("TEMP").get_code(), "VLA")

    def test_configure_telescopes_nested_not_found(self):
        """Test configuring a nested Telescope that does not exist."""
        tels_obj = Telescopes(name="TELESCOPEEE33S")
        attributes = {"name": "VLA", "set": {"params": {"code": "VLA"}}}
        result = self.configurator.execute(tels_obj, attributes)
        self.assertFalse(result["status"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "\"Name 'VLA' not found in Telescopes\"")

    def test_configure_scan(self):
        """Test configuring a Scan object."""
        scan_obj = Scan(name="SCAN1")
        attributes = {
            "set_start": {"start": Time("2025-04-16T12:00:00")},
            "set_duration": {"duration": 300.0},
            "set_source_name": {"source_name": "3C 286"}
        }
        result = self.configurator.execute(scan_obj, attributes)
        self.assertTrue(result["status"])
        self.assertEqual(result["method"], "_configure_scan")
        self.assertEqual(result["result"], scan_obj.get())
        self.assertEqual(scan_obj.get_source_name(), "3C 286")
        self.assertEqual(scan_obj.get_duration(), 300.0)
        self.assertEqual(result["result"]["source_name"], "3C 286")
        self.assertEqual(result["result"]["duration"], 300.0)

    def test_configure_scans_nested(self):
        """Test configuring a nested Scan within Scans."""
        scans_obj = Scans(name="SCANEEES")
        scan_obj = Scan(name="SCAN1")
        scans_obj.add(scan_obj)
        attributes = {"name": "SCAN1", "set_source_name": {"source_name": "3C 286"}}
        result = self.configurator.execute(scans_obj, attributes)
        self.assertTrue(result["status"])
        self.assertEqual(result["method"], "_configure_scans")
        self.assertEqual(result["result"], scans_obj.get("SCAN1").get())
        self.assertEqual(scans_obj.get("SCAN1").get_source_name(), "3C 286")
        self.assertEqual(result["result"]["source_name"], "3C 286")

    def test_configure_scans_nested_not_found(self):
        """Test configuring a nested Scan that does not exist."""
        scans_obj = Scans(name="SCANEIS")
        attributes = {"name": "SCAN1", "set_source_name": {"source_name": "3C 286"}}
        result = self.configurator.execute(scans_obj, attributes)
        self.assertFalse(result["status"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "\"Name 'SCAN1' not found in Scans\"")

    def test_configure_scans_overlap(self):
        """Test configuring a Scan with overlap detection."""
        scans_obj = Scans(name="SCANDORO")
        scan1 = Scan(name="SCAN1")
        scan2 = Scan(name="SCAN2")
        scan1.set_start(Time("2025-04-16T12:00:00"))
        scan1.set_duration(300.0)
        scan2.set_start(Time("2025-04-16T12:10:00"))
        scans_obj.add(scan1)
        scans_obj.add(scan2)
        attributes = {"name": "SCAN2", "set_duration": {"duration": 600.0}}
        with patch.object(scans_obj, '_check_overlap', return_value=(True, "overlaps with SCAN1")):
            result = self.configurator.execute(scans_obj, attributes)
        self.assertFalse(result["status"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "Modified scan 'SCAN2' overlaps with SCAN1")

    def test_configure_observation(self):
        """Test configuring an Observation object."""
        obs_obj = Observation()
        attributes = {"set": {"params": {"name": "OBS001", "code": "OBS001"}}}
        with patch.object(Observation, 'validate', return_value=True):
            result = self.configurator.execute(obs_obj, attributes)
        self.assertTrue(result["status"])
        self.assertEqual(result["method"], "_configure_observation")
        self.assertEqual(result["result"], "OBS001")
        self.assertEqual(obs_obj.get_observation_code(), "OBS001")

    def test_configure_observation_invalid(self):
        """Test configuring an Observation that fails validation."""
        obs_obj = Observation()
        attributes = {"set": {"params": {"name": "OBS001", "code": "OBS001"}}}
        with patch.object(Observation, 'validate', return_value=False):
            result = self.configurator.execute(obs_obj, attributes)
        self.assertFalse(result["status"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "Observation invalid after configuration")

    def test_configure_project(self):
        """Test configuring a ScheduleProject."""
        project_obj = ScheduleProject()
        attributes = {"set_project": {"name": "TEST_PROJECT", "items": {}}}
        result = self.configurator.execute(project_obj, attributes)
        self.assertTrue(result["status"])
        self.assertEqual(result["method"], "_configure_scheduleproject")
        self.assertEqual(result["result"], "TEST_PROJECT")
        self.assertEqual(project_obj.get_name(), "TEST_PROJECT")

    def test_configure_project_nested(self):
        """Test configuring a nested Observation within ScheduleProject."""
        project_obj = ScheduleProject(name="PORJE")
        obs_obj = Observation(name="OBS_DEFAULT", code="DEF")
        project_obj.add_item(obs_obj)
        attributes = {"name": "OBS_DEFAULT", "set": {"params": {"code": "OBS001"}}}
        with patch.object(Observation, 'validate', return_value=True) as mock_validate:
            result = self.configurator.execute(project_obj, attributes)
            mock_validate.assert_called()
        self.assertTrue(result["status"])
        self.assertEqual(result["method"], "_configure_scheduleproject")
        self.assertEqual(project_obj.get_observation("OBS_DEFAULT").get_observation_code(), "OBS001")

    def test_configure_project_nested_not_found(self):
        """Test configuring a nested Observation that does not exist in ScheduleProject."""
        project_obj = ScheduleProject()
        attributes = {"name": "OBS001", "set": {"params": {"code": "OBS001"}}}
        result = self.configurator.execute(project_obj, attributes)
        self.assertFalse(result["status"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "\"Name 'OBS001' not found in TypedContainer\"")

    def test_configure_invalid_object(self):
        """Test configuring an invalid object type."""
        invalid_obj = object()
        attributes = {"set": {"params": {"value": "TEST"}}}
        result = self.configurator.execute(invalid_obj, attributes)
        self.assertFalse(result["status"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], f"No suitable method found for operation 'configure' and object 'object' in ScheduleConfigurator")

    def test_configure_nested_caching(self):
        """Test caching of nested configuration."""
        freq_obj = Frequencies(name="FREQS")
        if_obj = IF(name="IF1")
        freq_obj.add(if_obj)
        attributes = {"name": "IF1", "set": {"params": {"frequency": 1420.0, "bandwidth": 20.0}}}
        result1 = self.configurator.execute(freq_obj, attributes)
        self.assertTrue(result1["status"])
        self.assertEqual(result1["method"], "_configure_frequencies")
        self.assertEqual(result1["result"], freq_obj.get("IF1").get())
        with patch.object(self.configurator, "_configure_frequencies") as mock_method:
            result2 = self.configurator.execute(freq_obj, attributes)
            self.assertTrue(result2["status"])
            self.assertEqual(result2["method"], "_configure_frequencies")
            self.assertEqual(result2["result"], freq_obj.get("IF1").get())
            mock_method.assert_not_called()


if __name__ == '__main__':
    unittest.main()
