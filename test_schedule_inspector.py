# test_schedule_inspector.py
import unittest
from unittest.mock import MagicMock, patch
from astropy.time import Time
from unit_scheduling_2.super.schedule_inspector import ScheduleInspector
from unit_scheduling_2.super.schedule_project import ScheduleProject
from unit_scheduling_2.base.frequencies import IF, Frequencies
from unit_scheduling_2.base.sources import Source, Sources
from unit_scheduling_2.base.telescopes import Telescope, SpaceTelescope, Telescopes
from unit_scheduling_2.base.scans import Scan, Scans
from unit_scheduling_2.base.observation import Observation

class TestScheduleInspector(unittest.TestCase):
    def setUp(self):
        """Set up the test environment with a mocked Manipulator."""
        self.manipulator = MagicMock()
        self.manipulator.get_methods_for_type.side_effect = lambda cls: {
            IF: {"get_frequency": getattr(IF, "get_frequency"), "get_bandwidth": getattr(IF, "get_bandwidth")},
            Frequencies: {"get_frequencies": getattr(Frequencies, "get_frequencies"), "get_bandwidths": getattr(Frequencies, "get_bandwidths")},
            Source: {
                "get_name": getattr(Source, "get_name"),
                "ra_degrees": getattr(Source, "ra_degrees"),
                "dec_degrees": getattr(Source, "dec_degrees"),
                "get_flux": getattr(Source, "get_flux")
            },
            Sources: {"get_active_items": getattr(Sources, "get_active_items")},
            Telescope: {"get_code": getattr(Telescope, "get_code"), "get_coordinates": getattr(Telescope, "get_coordinates")},
            SpaceTelescope: {
                "get_code": getattr(SpaceTelescope, "get_code"),
                "get_state_vector": getattr(SpaceTelescope, "get_state_vector")
            },
            Telescopes: {"get_active_items": getattr(Telescopes, "get_active_items")},
            Scan: {
                "get_start": getattr(Scan, "get_start"),
                "get_duration": getattr(Scan, "get_duration"),
                "get_source_name": getattr(Scan, "get_source_name"),
                "get_telescope_names": getattr(Scan, "get_telescope_names"),
                "get_frequencies": getattr(Scan, "get_frequencies")
            },
            Scans: {"get_active_scans": getattr(Scans, "get_active_scans")},
            Observation: {
                "get_observation_code": getattr(Observation, "get_observation_code"),
                "get_calculated_data": getattr(Observation, "get_calculated_data")
            },
            ScheduleProject: {"get_name": getattr(ScheduleProject, "get_name"), "get_project": getattr(ScheduleProject, "get_project")}
        }.get(cls, {})
        self.inspector = ScheduleInspector(self.manipulator)

    def test_inspect_if(self):
        """Test inspecting an IF object."""
        if_obj = IF(name="IF1", frequency=1420.0, bandwidth=20.0)
        attributes = {"get_frequency": None, "get_bandwidth": None}
        result = self.inspector.execute(if_obj, attributes)
        self.assertEqual(result, {"get_frequency": 1420.0, "get_bandwidth": 20.0})

    def test_inspect_if_invalid_getter(self):
        """Test inspecting an IF with an invalid getter."""
        if_obj = IF(name="IF1")
        attributes = {"invalid_getter": None}
        result = self.inspector.execute(if_obj, attributes)
        self.assertEqual(result, {})

    def test_inspect_frequencies(self):
        """Test inspecting a Frequencies object."""
        freq_obj = Frequencies(name="FREQS")
        freq_obj.add(IF(name="IF1", frequency=1420.0))
        attributes = {"get_frequencies": None}
        result = self.inspector.execute(freq_obj, attributes)
        self.assertEqual(result, {"get_frequencies": [1420.0]})

    def test_inspect_frequencies_nested(self):
        """Test inspecting a nested IF within Frequencies."""
        freq_obj = Frequencies(name="FREQS")
        freq_obj.add(IF(name="IF1", frequency=1420.0))
        attributes = {"if_index": 0, "get_frequency": None}
        result = self.inspector.execute(freq_obj, attributes)
        self.assertEqual(result, {"get_frequency": 1420.0})

    def test_inspect_frequencies_nested_invalid_index(self):
        """Test inspecting a nested IF with an invalid index."""
        freq_obj = Frequencies(name="FREQS")
        attributes = {"if_index": 0, "get_frequency": None}
        result = self.inspector.execute(freq_obj, attributes)
        self.assertEqual(result, {})

    def test_inspect_source(self):
        """Test inspecting a Source object."""
        source_obj = Source(name="3C 286", ra_h=13, ra_m=31, ra_s=8.287)
        attributes = {"get_name": None, "ra_degrees": None}
        result = self.inspector.execute(source_obj, attributes)
        self.assertEqual(result, {"get_name": "3C 286", "ra_degrees": (13 + 31/60 + 8.287/3600) * 15})

    def test_inspect_sources(self):
        """Test inspecting a Sources object."""
        sources_obj = Sources(name="SRCS")
        sources_obj.add(Source(name="3C 286"))
        attributes = {"get_active_items": None}
        result = self.inspector.execute(sources_obj, attributes)
        self.assertEqual(len(result["get_active_items"]), 1)
        self.assertEqual(result["get_active_items"][0].name, "3C 286")

    def test_inspect_sources_nested(self):
        """Test inspecting a nested Source within Sources."""
        sources_obj = Sources(name="SRCS")
        sources_obj.add(Source(name="3C 286"))
        attributes = {"source_index": 0, "get_name": None}
        result = self.inspector.execute(sources_obj, attributes)
        self.assertEqual(result, {"get_name": "3C 286"})

    def test_inspect_telescope(self):
        """Test inspecting a Telescope object."""
        tel_obj = Telescope(name="GBT", code="GBT", x=0.0, y=0.0, z=0.0)
        attributes = {"get_code": None, "get_coordinates": None}
        result = self.inspector.execute(tel_obj, attributes)
        self.assertEqual(result, {"get_code": "GBT", "get_coordinates": (0.0, 0.0, 0.0)})

    def test_inspect_space_telescope(self):
        """Test inspecting a SpaceTelescope object."""
        tel_obj = SpaceTelescope(name="HST", code="HST")
        attributes = {"get_code": None}
        result = self.inspector.execute(tel_obj, attributes)
        self.assertEqual(result, {"get_code": "HST"})

    def test_inspect_telescopes(self):
        """Test inspecting a Telescopes object."""
        tels_obj = Telescopes(name="TELESCOPES")
        tels_obj.add(Telescope(name="GBT", code="GBT"))
        attributes = {"get_active_items": None}
        result = self.inspector.execute(tels_obj, attributes)
        self.assertEqual(len(result["get_active_items"]), 1)
        self.assertEqual(result["get_active_items"][0].get_code(), "GBT")

    def test_inspect_telescopes_nested(self):
        """Test inspecting a nested Telescope within Telescopes."""
        tels_obj = Telescopes(name="TELESCOPES")
        tels_obj.add(Telescope(name="GBT", code="GBT"))
        attributes = {"telescope_index": 0, "get_code": None}
        result = self.inspector.execute(tels_obj, attributes)
        self.assertEqual(result, {"get_code": "GBT"})

    def test_inspect_scan(self):
        """Test inspecting a Scan object."""
        scan_obj = Scan(name="SCAN1", start=Time("2025-04-16T12:00:00"), duration=300.0, source_name="3C 286")
        attributes = {"get_start": None, "get_source_name": None}
        result = self.inspector.execute(scan_obj, attributes)
        self.assertEqual(result["get_source_name"], "3C 286")
        self.assertEqual(result["get_start"], Time("2025-04-16T12:00:00"))

    def test_inspect_scan_with_observation(self):
        """Test inspecting a Scan with an observation-dependent getter."""
        scan_obj = Scan(name="SCAN1", source_name="3C 286")
        obs_obj = Observation(sources=Sources(items={"3C 286": Source(name="3C 286")}))
        attributes = {"get_source": {"observation": obs_obj}}
        result = self.inspector.execute(scan_obj, attributes)
        self.assertEqual(result["get_source"].name, "3C 286")

    def test_inspect_scan_invalid_observation(self):
        """Test inspecting a Scan with an invalid observation argument."""
        scan_obj = Scan(name="SCAN1")
        attributes = {"get_source": {"observation": object()}}
        result = self.inspector.execute(scan_obj, attributes)
        self.assertEqual(result, {})

    def test_inspect_scans(self):
        """Test inspecting a Scans object."""
        scans_obj = Scans(name="SCANS")
        scans_obj.add(Scan(name="SCAN1"))
        attributes = {"get_active_scans": None}
        result = self.inspector.execute(scans_obj, attributes)
        self.assertEqual(len(result["get_active_scans"]), 1)

    def test_inspect_scans_nested(self):
        """Test inspecting a nested Scan within Scans."""
        scans_obj = Scans(name="SCANS")
        scans_obj.add(Scan(name="SCAN1", source_name="3C 286"))
        attributes = {"scan_index": 0, "get_source_name": None}
        result = self.inspector.execute(scans_obj, attributes)
        self.assertEqual(result, {"get_source_name": "3C 286"})

    def test_inspect_observation(self):
        """Test inspecting an Observation object."""
        obs_obj = Observation(name="OBS001", code="OBS001")
        attributes = {"get_observation_code": None, "get_calculated_data": None}
        result = self.inspector.execute(obs_obj, attributes)
        self.assertEqual(result, {"get_observation_code": "OBS001", "get_calculated_data": {}})

    def test_inspect_project(self):
        """Test inspecting a ScheduleProject object."""
        project_obj = ScheduleProject(name="TEST_PROJECT")
        attributes = {"get_name": None}
        result = self.inspector.execute(project_obj, attributes)
        self.assertEqual(result, {"get_name": "TEST_PROJECT"})

    def test_inspect_project_nested(self):
        """Test inspecting a nested Observation within ScheduleProject."""
        project_obj = ScheduleProject(name="TEST_PROJECT")
        obs_obj = Observation(name="OBS001", code="OBS001")
        project_obj.add_item(obs_obj)
        attributes = {"observation_index": 0, "get_observation_code": None}
        result = self.inspector.execute(project_obj, attributes)
        self.assertEqual(result, {"get_observation_code": "OBS001"})

    def test_inspect_invalid_object(self):
        """Test inspecting an invalid object type."""
        invalid_obj = object()
        attributes = {"get_name": None}
        result = self.inspector.execute(invalid_obj, attributes)
        self.assertEqual(result, {})

if __name__ == '__main__':
    unittest.main()