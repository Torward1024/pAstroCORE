import unittest
from typing import Dict, Any, Callable
from base.sources import Source, Sources
from base.telescopes import Telescope, Telescopes
from base.frequencies import IF, Frequencies
from base.scans import Scan, Scans
from base.observation import Observation
from base.project import Project
from super.inspector import Inspector, DefaultInspector

# Заглушка для Manipulator
class MockManipulator:
    def __init__(self, inspector):
        self.inspector = inspector

    def get_methods_for_type(self, obj_type: type) -> Dict[str, Callable]:
        if obj_type == IF:
            return {"get_frequency": IF.get_frequency, "get_bandwidth": IF.get_bandwidth}
        elif obj_type == Frequencies:
            return {"get_all_IF": Frequencies.get_all_IF, "get_frequencies": Frequencies.get_frequencies}
        elif obj_type == Source:
            return {"get_name": Source.get_name, "get_source_coordinates": Source.get_source_coordinates}
        elif obj_type == Sources:
            return {"get_all_sources": Sources.get_all_sources}
        elif obj_type == Telescope:
            return {"get_name": Telescope.get_name, "get_coordinates": Telescope.get_coordinates}
        elif obj_type == Telescopes:
            return {"get_all_telescopes": Telescopes.get_all_telescopes}
        elif obj_type == Scan:
            return {"get_start": Scan.get_start, "get_duration": Scan.get_duration, "get_source": Scan.get_source}
        elif obj_type == Scans:
            return {"get_all_scans": Scans.get_all_scans}
        elif obj_type == Observation:
            return {"get_observation_code": Observation.get_observation_code, "get_observation_type": Observation.get_observation_type}
        elif obj_type == Project:
            return {"get_name": Project.get_name, "get_observations": Project.get_observations}
        elif obj_type == Inspector:
            return {
                "_inspect_if": self.inspector._inspect_if,
                "_inspect_frequencies": self.inspector._inspect_frequencies,
                "_inspect_source": self.inspector._inspect_source,
                "_inspect_sources": self.inspector._inspect_sources,
                "_inspect_telescope": self.inspector._inspect_telescope,
                "_inspect_telescopes": self.inspector._inspect_telescopes,
                "_inspect_scan": self.inspector._inspect_scan,
                "_inspect_scans": self.inspector._inspect_scans,
                "_inspect_observation": self.inspector._inspect_observation,
                "_inspect_project": self.inspector._inspect_project
            }
        return {}

class TestInspector(unittest.TestCase):
    def setUp(self):
        # Создание тестовых данных
        self.inspector = DefaultInspector(None)  # Временно None
        self.manipulator = MockManipulator(self.inspector)
        self.inspector._manipulator = self.manipulator

        self.source = Source(name="TEST_SRC", ra_h=12, ra_m=30, ra_s=45.0, de_d=45, de_m=15, de_s=30.0,
                             flux_table={1420.0: 10.0}, spectral_index=-0.7)
        self.sources = Sources([self.source])

        self.telescope = Telescope(code="T1", name="Test Telescope", x=1000.0, y=2000.0, z=3000.0,
                                  diameter=25.0, sefd_table={1420.0: 500.0})
        self.telescopes = Telescopes([self.telescope])

        self.frequency = IF(freq=1420.0, bandwidth=32.0)
        self.frequencies = Frequencies([self.frequency])

        self.scan = Scan(start=1625097600.0, duration=300.0, source_index=0,
                         telescope_indices=[0], frequency_indices=[0])
        self.scans = Scans([self.scan])

        self.observation = Observation(observation_code="OBS001", sources=self.sources, telescopes=self.telescopes,
                                      frequencies=self.frequencies, scans=self.scans, observation_type="VLBI")

        self.project = Project(name="TEST_PROJECT", observations=[self.observation])

    def test_init(self):
        self.assertIsInstance(self.inspector, Inspector)
        self.assertEqual(repr(self.inspector), "Inspector()")

    def test_inspect_if(self):
        result = self.inspector.execute(self.frequency, {"get_frequency": None, "get_bandwidth": None})
        self.assertEqual(result, {"get_frequency": 1420.0, "get_bandwidth": 32.0})

    def test_inspect_frequencies(self):
        result = self.inspector.execute(self.frequencies, {"get_frequencies": None})
        self.assertEqual(result, {"get_frequencies": [1420.0]})
        # Тест вложенного объекта
        result = self.inspector.execute(self.frequencies, {"if_index": 0, "get_frequency": None})
        self.assertEqual(result, {"get_frequency": 1420.0})

    def test_inspect_source(self):
        result = self.inspector.execute(self.source, {"get_name": None, "get_source_coordinates": None})
        self.assertEqual(result, {"get_name": "TEST_SRC", "get_source_coordinates": (12, 30, 45.0, 45, 15, 30.0)})

    def test_inspect_sources(self):
        result = self.inspector.execute(self.sources, {"get_all_sources": None})
        self.assertEqual(len(result["get_all_sources"]), 1)
        self.assertEqual(result["get_all_sources"][0].get_name(), "TEST_SRC")
        # Тест вложенного объекта
        result = self.inspector.execute(self.sources, {"source_index": 0, "get_name": None})
        self.assertEqual(result, {"get_name": "TEST_SRC"})

    def test_inspect_telescope(self):
        result = self.inspector.execute(self.telescope, {"get_name": None, "get_coordinates": None})
        self.assertEqual(result, {"get_name": "Test Telescope", "get_coordinates": (1000.0, 2000.0, 3000.0)})

    def test_inspect_telescopes(self):
        result = self.inspector.execute(self.telescopes, {"get_all_telescopes": None})
        self.assertEqual(len(result["get_all_telescopes"]), 1)
        self.assertEqual(result["get_all_telescopes"][0].get_name(), "Test Telescope")
        # Тест вложенного объекта
        result = self.inspector.execute(self.telescopes, {"telescope_index": 0, "get_name": None})
        self.assertEqual(result, {"get_name": "Test Telescope"})

    def test_inspect_scan(self):
        result = self.inspector.execute(self.scan, {"get_start": None, "get_duration": None})
        self.assertEqual(result, {"get_start": 1625097600.0, "get_duration": 300.0})
        # Тест с observation
        result = self.inspector.execute(self.scan, {"get_source": {"observation": self.observation}})
        self.assertEqual(result["get_source"].get_name(), "TEST_SRC")

    def test_inspect_scans(self):
        result = self.inspector.execute(self.scans, {"get_all_scans": None})
        self.assertEqual(len(result["get_all_scans"]), 1)
        self.assertEqual(result["get_all_scans"][0].get_start(), 1625097600.0)
        # Тест вложенного объекта
        result = self.inspector.execute(self.scans, {"scan_index": 0, "get_start": None})
        self.assertEqual(result, {"get_start": 1625097600.0})

    def test_inspect_observation(self):
        result = self.inspector.execute(self.observation, {"get_observation_code": None, "get_observation_type": None})
        self.assertEqual(result, {"get_observation_code": "OBS001", "get_observation_type": "VLBI"})

    def test_inspect_project(self):
        result = self.inspector.execute(self.project, {"get_name": None, "get_observations": None})
        self.assertEqual(result["get_name"], "TEST_PROJECT")
        self.assertEqual(len(result["get_observations"]), 1)
        # Тест вложенного объекта
        result = self.inspector.execute(self.project, {"observation_index": 0, "get_observation_code": None})
        self.assertEqual(result, {"get_observation_code": "OBS001"})

    def test_invalid_getter(self):
        result = self.inspector.execute(self.frequency, {"invalid_getter": None})
        self.assertEqual(result, {})

    def test_invalid_index(self):
        result = self.inspector.execute(self.frequencies, {"if_index": 999, "get_frequency": None})
        self.assertEqual(result, {})

    def test_none_object(self):
        with self.assertRaises(ValueError):
            self.inspector.execute(None, {"get_name": None})

if __name__ == "__main__":
    unittest.main()