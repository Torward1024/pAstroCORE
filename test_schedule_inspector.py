import unittest
from unittest.mock import MagicMock
from astropy.time import Time
from unit_scheduling_2.super.schedule_inspector import ScheduleInspector
from unit_scheduling_2.super.schedule_project import ScheduleProject
from unit_scheduling_2.base.frequencies import IF, Frequencies
from unit_scheduling_2.base.sources import Source, Sources
from unit_scheduling_2.base.telescopes import Telescope, SpaceTelescope, Telescopes
from unit_scheduling_2.base.scans import Scan, Scans
from unit_scheduling_2.base.observation import Observation
from common.base.baseentity import BaseEntity
from common.utils.logging_setup import logger

class TestScheduleInspector(unittest.TestCase):
    def setUp(self):
        """Set up the test environment with a mocked Manipulator."""
        self.manipulator = MagicMock()
        self.manipulator.get_methods_for_type.side_effect = lambda cls: {
            IF: {"get": getattr(BaseEntity, "get")},
            Frequencies: {
                "get_frequencies": getattr(Frequencies, "get_frequencies"),
                "get_bandwidths": getattr(Frequencies, "get_bandwidths"),
                "get_active_items": getattr(Frequencies, "get_active_items"),
                "to_dict": getattr(Frequencies, "to_dict")
            },
            Source: {"get": getattr(BaseEntity, "get")},
            Sources: {"get_active_items": getattr(Sources, "get_active_items")},
            Telescope: {"get": getattr(BaseEntity, "get")},
            SpaceTelescope: {
                "get": getattr(BaseEntity, "get"),
                "get_state_vector": getattr(SpaceTelescope, "get_state_vector")
            },
            Telescopes: {"get_active_items": getattr(Telescopes, "get_active_items")},
            Scan: {
                "get": getattr(BaseEntity, "get"),
                "get_source": getattr(Scan, "get_source"),
                "get_telescopes": getattr(Scan, "get_telescopes"),
                "get_frequencies": getattr(Scan, "get_frequencies")
            },
            Scans: {"get_active_scans": getattr(Scans, "get_active_scans")},
            Observation: {
                "get": getattr(BaseEntity, "get"),
                "get_start_datetime": getattr(Observation, "get_start_datetime"),
                "validate": getattr(Observation, "validate")
            },
            ScheduleProject: {
                "get": getattr(BaseEntity, "get"),
                "get_project": getattr(ScheduleProject, "get_project")
            }
        }.get(cls, {})
        self.inspector = ScheduleInspector(self.manipulator)
        logger.info("Set up TestScheduleInspector")

    def test_inspect_if(self):
        """Test inspecting an IF object."""
        if_obj = IF(name="IF1", frequency=1420.0, bandwidth=20.0)
        attributes = {"get": ["frequency", "bandwidth"]}
        result = self.inspector.execute(if_obj, attributes)
        self.assertEqual(result, {"get": {"frequency": 1420.0, "bandwidth": 20.0}})
        logger.info("IF inspection tested successfully")

    def test_inspect_if_single_attribute(self):
        """Test inspecting a single attribute of an IF object."""
        if_obj = IF(name="IF1", frequency=1420.0, bandwidth=20.0)
        attributes = {"get": "frequency"}
        result = self.inspector.execute(if_obj, attributes)
        self.assertEqual(result, {"get": 1420.0})
        logger.info("Single attribute IF inspection tested successfully")

    def test_inspect_if_invalid_attribute(self):
        """Test inspecting an IF with an invalid attribute."""
        if_obj = IF(name="IF1", frequency=1420.0, bandwidth=20.0)
        attributes = {"get": "invalid_attribute"}
        result = self.inspector.execute(if_obj, attributes)
        self.assertEqual(result, {"status": False, "error": "Operation not executed"})
        logger.info("Invalid attribute IF inspection tested successfully")

    def test_inspect_frequencies(self):
        """Test inspecting a Frequencies object."""
        freq_obj = Frequencies(name="FREQS")
        freq_obj.add(IF(name="IF1", frequency=1420.0, bandwidth=20.0))
        attributes = {"get_frequencies": None}
        result = self.inspector.execute(freq_obj, attributes)
        self.assertEqual(result, {"get_frequencies": [1420.0]})
        logger.info("Frequencies inspection tested successfully")

    def test_inspect_frequencies_nested(self):
        """Test inspecting a nested IF within Frequencies."""
        freq_obj = Frequencies(name="FREQS")
        freq_obj.add(IF(name="IF1", frequency=1420.0, bandwidth=20.0))
        attributes = {"name": "IF1", "get": "frequency"}
        result = self.inspector.execute(freq_obj, attributes)
        self.assertEqual(result, {"get": 1420.0})
        logger.info("Nested IF inspection tested successfully")

    def test_inspect_frequencies_nested_not_found(self):
        """Test inspecting a nested IF that does not exist."""
        freq_obj = Frequencies(name="FREQS")
        attributes = {"name": "IF1", "get": "frequency"}
        result = self.inspector.execute(freq_obj, attributes)
        self.assertEqual(result, {"status": False, "error": "Operation not executed"})
        logger.info("Nested IF not found inspection tested successfully")

    def test_inspect_frequencies_active_items(self):
        """Test inspecting active items in a Frequencies object."""
        freq_obj = Frequencies(name="FREQS")
        freq_obj.add(IF(name="IF1", frequency=1420.0, bandwidth=20.0))
        freq_obj.add(IF(name="IF2", frequency=1500.0, bandwidth=30.0, isactive=False))
        attributes = {"get_active_items": None}
        result = self.inspector.execute(freq_obj, attributes)
        self.assertEqual(len(result["get_active_items"]), 1)
        self.assertEqual(result["get_active_items"][0].name, "IF1")
        logger.info("Frequencies active items inspection tested successfully")

    def test_inspect_source(self):
        """Test inspecting a Source object."""
        source_obj = Source(name="3C 286", ra_h=13.0, ra_m=31.0, ra_s=8.287)
        attributes = {"get": ["name", "ra_degrees"]}
        result = self.inspector.execute(source_obj, attributes)
        expected_ra = (13 + 31/60 + 8.287/3600) * 15
        self.assertAlmostEqual(result["get"]["ra_degrees"], expected_ra)
        self.assertEqual(result["get"]["name"], "3C 286")
        logger.info("Source inspection tested successfully")

    def test_inspect_sources(self):
        """Test inspecting a Sources object."""
        sources_obj = Sources(name="SRCS")
        sources_obj.add(Source(name="3C 286"))
        attributes = {"get_active_items": None}
        result = self.inspector.execute(sources_obj, attributes)
        self.assertEqual(len(result["get_active_items"]), 1)
        self.assertEqual(result["get_active_items"][0].name, "3C 286")
        logger.info("Sources inspection tested successfully")

    def test_inspect_sources_nested(self):
        """Test inspecting a nested Source within Sources."""
        sources_obj = Sources(name="SRCS")
        sources_obj.add(Source(name="3C 286"))
        attributes = {"name": "3C 286", "get": "name"}
        result = self.inspector.execute(sources_obj, attributes)
        self.assertEqual(result, {"get": "3C 286"})
        logger.info("Nested Source inspection tested successfully")

    def test_inspect_sources_nested_not_found(self):
        """Test inspecting a nested Source that does not exist."""
        sources_obj = Sources(name="SRCS")
        attributes = {"name": "3C 286", "get": "name"}
        result = self.inspector.execute(sources_obj, attributes)
        self.assertEqual(result, {"status": False, "error": "Operation not executed"})
        logger.info("Nested Source not found inspection tested successfully")

    def test_inspect_telescope(self):
        """Test inspecting a Telescope object."""
        tel_obj = Telescope(name="GBT", code="GBT", x=0.0, y=0.0, z=0.0)
        attributes = {"get": ["code", "coordinates"]}
        result = self.inspector.execute(tel_obj, attributes)
        self.assertEqual(result, {"get": {"code": "GBT", "coordinates": (0.0, 0.0, 0.0)}})
        logger.info("Telescope inspection tested successfully")

    def test_inspect_space_telescope(self):
        """Test inspecting a SpaceTelescope object."""
        tel_obj = SpaceTelescope(name="HST", code="HST")
        attributes = {"get": "code"}
        result = self.inspector.execute(tel_obj, attributes)
        self.assertEqual(result, {"get": "HST"})
        logger.info("SpaceTelescope inspection tested successfully")

    def test_inspect_telescopes(self):
        """Test inspecting a Telescopes object."""
        tels_obj = Telescopes(name="TELESCOPES")
        tels_obj.add(Telescope(name="GBT", code="GBT"))
        attributes = {"get_active_items": None}
        result = self.inspector.execute(tels_obj, attributes)
        self.assertEqual(len(result["get_active_items"]), 1)
        self.assertEqual(result["get_active_items"][0].get("code"), "GBT")
        logger.info("Telescopes inspection tested successfully")

    def test_inspect_telescopes_nested(self):
        """Test inspecting a nested Telescope within Telescopes."""
        tels_obj = Telescopes(name="TELESCOPES")
        tels_obj.add(Telescope(name="GBT", code="GBT"))
        attributes = {"name": "GBT", "get": "code"}
        result = self.inspector.execute(tels_obj, attributes)
        print("BABAH!", result)
        self.assertEqual(result, {"get": "GBT"})
        logger.info("Nested Telescope inspection tested successfully")

    def test_inspect_telescopes_nested_not_found(self):
        """Test inspecting a nested Telescope that does not exist."""
        tels_obj = Telescopes(name="TELESCOPES")
        attributes = {"name": "GBT", "get": "code"}
        result = self.inspector.execute(tels_obj, attributes)
        self.assertEqual(result, {"status": False, "error": "Operation not executed"})
        logger.info("Nested Telescope not found inspection tested successfully")

    def test_inspect_scan(self):
        """Test inspecting a Scan object."""
        scan_obj = Scan(name="SCAN1", start=Time("2025-04-16T12:00:00"), duration=300.0, source_name="3C 286")
        attributes = {"get": ["start", "source_name"]}
        result = self.inspector.execute(scan_obj, attributes)
        self.assertEqual(result["get"]["source_name"], "3C 286")
        self.assertEqual(result["get"]["start"], Time("2025-04-16T12:00:00"))
        logger.info("Scan inspection tested successfully")

    def test_inspect_scan_with_observation(self):
        """Test inspecting a Scan with an observation-dependent getter."""
        scan_obj = Scan(name="SCAN1", source_name="3C 286")
        obs_obj = Observation(sources=Sources(items={"3C 286": Source(name="3C 286")}))
        attributes = {"get_source": {"observation": obs_obj}}
        result = self.inspector.execute(scan_obj, attributes)
        self.assertEqual(result["get_source"].name, "3C 286")
        logger.info("Scan with observation inspection tested successfully")

    def test_inspect_scan_invalid_observation(self):
        """Test inspecting a Scan with an invalid observation argument."""
        scan_obj = Scan(name="SCAN1")
        attributes = {"get_source": {"observation": object()}}
        result = self.inspector.execute(scan_obj, attributes)
        self.assertEqual(result, {"status": False, "error": "Operation not executed"})
        logger.info("Scan with invalid observation inspection tested successfully")

    def test_inspect_scan_telescopes(self):
        """Test inspecting telescopes for a Scan."""
        scan_obj = Scan(name="SCAN1", telescope_names=["GBT"])
        obs_obj = Observation(telescopes=Telescopes(items={"GBT": Telescope(name="GBT", code="GBT")}))
        attributes = {"get_telescopes": {"observation": obs_obj}}
        result = self.inspector.execute(scan_obj, attributes)
        self.assertEqual(len(result["get_telescopes"].get_active_items()), 1)
        self.assertEqual(result["get_telescopes"].get_active_items()[0].get("code"), "GBT")
        logger.info("Scan telescopes inspection tested successfully")

    def test_inspect_scans(self):
        """Test inspecting a Scans object."""
        scans_obj = Scans(name="SCANS")
        scans_obj.add(Scan(name="SCAN1"))
        attributes = {"get_active_scans": None}
        result = self.inspector.execute(scans_obj, attributes)
        self.assertEqual(len(result["get_active_scans"]), 1)
        logger.info("Scans inspection tested successfully")

    def test_inspect_scans_with_observation(self):
        """Test inspecting active scans filtered by observation."""
        scans_obj = Scans(name="SCANS")
        scan = Scan(name="SCAN1", source_name="3C 286")
        scans_obj.add(scan)
        obs_obj = Observation(sources=Sources(items={"3C 286": Source(name="3C 286")}))
        attributes = {"get_active_scans": {"observation": obs_obj}}
        result = self.inspector.execute(scans_obj, attributes)
        self.assertEqual(len(result["get_active_scans"]), 1)
        self.assertEqual(result["get_active_scans"][0].name, "SCAN1")
        logger.info("Scans with observation inspection tested successfully")

    def test_inspect_scans_nested(self):
        """Test inspecting a nested Scan within Scans."""
        scans_obj = Scans(name="SCANS")
        scans_obj.add(Scan(name="SCAN1", source_name="3C 286"))
        attributes = {"name": "SCAN1", "get": "source_name"}
        result = self.inspector.execute(scans_obj, attributes)
        self.assertEqual(result, {"get": "3C 286"})
        logger.info("Nested Scan inspection tested successfully")

    def test_inspect_scans_nested_not_found(self):
        """Test inspecting a nested Scan that does not exist."""
        scans_obj = Scans(name="SCANS")
        attributes = {"name": "SCAN1", "get": "source_name"}
        result = self.inspector.execute(scans_obj, attributes)
        self.assertEqual(result, {"status": False, "error": "Operation not executed"})
        logger.info("Nested Scan not found inspection tested successfully")

    def test_inspect_observation(self):
        """Test inspecting an Observation object."""
        obs_obj = Observation(name="OBS1", code="OBS001")
        attributes = {"get": ["name", "code"]}
        result = self.inspector.execute(obs_obj, attributes)
        self.assertEqual(result, {"get": {"name": "OBS1", "code": "OBS001"}})
        logger.info("Observation inspection tested successfully")

    def test_inspect_project(self):
        """Test inspecting a ScheduleProject object."""
        project_obj = ScheduleProject(name="PROJECT1")
        project_obj.add_item(Observation(name="OBS1"))
        attributes = {"get_project": None}
        result = self.inspector.execute(project_obj, attributes)
        self.assertEqual(result["get_project"]["name"], "PROJECT1")
        logger.info("ScheduleProject inspection tested successfully")

    def test_inspect_project_nested(self):
        """Test inspecting a nested Observation within ScheduleProject."""
        project_obj = ScheduleProject(name="PROJECT1")
        obs_obj = Observation(name="OBS1", code="OBS001")
        project_obj.add_item(obs_obj)
        attributes = {"name": "OBS1", "get": "code"}
        result = self.inspector.execute(project_obj, attributes)
        self.assertEqual(result, {"get": "OBS001"})
        logger.info("Nested Observation in ScheduleProject inspection tested successfully")

    def test_inspect_project_nested_not_found(self):
        """Test inspecting a nested Observation that does not exist."""
        project_obj = ScheduleProject(name="PROJECT1")
        attributes = {"name": "OBS1", "get": "code"}
        result = self.inspector.execute(project_obj, attributes)
        self.assertEqual(result, {"status": False, "error": "Operation not executed"})
        logger.info("Nested Observation not found inspection tested successfully")

    def test_inspect_invalid_object(self):
        """Test inspecting an invalid object type."""
        invalid_obj = object()
        attributes = {"get": "value"}
        result = self.inspector.execute(invalid_obj, attributes)
        self.assertEqual(result, {"status": False, "error": "Operation not executed"})
        logger.info("Invalid object inspection tested successfully")

    def test_inspect_caching(self):
        """Test caching of inspection results."""
        freq_obj = Frequencies(name="FREQS")
        freq_obj.add(IF(name="IF1", frequency=1420.0, bandwidth=20.0))
        attributes = {"name": "IF1", "get": "frequency"}
        result1 = self.inspector.execute(freq_obj, attributes)
        self.assertEqual(result1, {"get": 1420.0})
        with unittest.mock.patch.object(self.inspector, "_inspect_if") as mock_method:
            result2 = self.inspector.execute(freq_obj, attributes)
            self.assertEqual(result2, {"get": 1420.0})
            mock_method.assert_not_called()
        logger.info("Inspection caching tested successfully")

if __name__ == '__main__':
    unittest.main()