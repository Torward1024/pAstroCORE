import unittest
from typing import Dict, Any, Callable
from base.sources import Source, Sources
from base.telescopes import Telescope, Telescopes, MountType
from base.frequencies import IF, Frequencies
from base.scans import Scan, Scans
from base.observation import Observation
from base.project import Project
from super.calculator import Calculator, DefaultCalculator
from astropy.time import Time
import numpy as np

# Заглушка для Manipulator
class MockManipulator:
    def __init__(self, calculator):
        self.calculator = calculator

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
            return {"get_start": Scan.get_start, "get_duration": Scan.get_duration, "get_by_index": Scan.get_by_index}
        elif obj_type == Scans:
            return {"get_active_scans": Scans.get_active_scans}
        elif obj_type == Observation:
            return {"get_observation_code": Observation.get_observation_code, "get_observation_type": Observation.get_observation_type}
        elif obj_type == Project:
            return {"get_name": Project.get_name, "get_observations": Project.get_observations}
        elif obj_type == Calculator:
            return {
                "_calculate_telescope_positions": self.calculator._calculate_telescope_positions,
                "_calculate_source_visibility": self.calculator._calculate_source_visibility,
                "_calculate_uv_coverage": self.calculator._calculate_uv_coverage,
                "_calculate_sun_angles": self.calculator._calculate_sun_angles,
                "_calculate_az_el": self.calculator._calculate_az_el,
                "_calculate_time_on_source": self.calculator._calculate_time_on_source,
                "_calculate_beam_pattern": self.calculator._calculate_beam_pattern,
                "_calculate_synthesized_beam": self.calculator._calculate_synthesized_beam,
                "_calculate_baseline_projections": self.calculator._calculate_baseline_projections,
                "_calculate_mollweide_tracks": self.calculator._calculate_mollweide_tracks
            }
        return {}

class TestCalculator(unittest.TestCase):
    def setUp(self):
        # Создание тестовых данных
        self.calculator = DefaultCalculator(None)
        self.manipulator = MockManipulator(self.calculator)
        self.calculator._manipulator = self.manipulator

        self.source = Source(name="TEST_SRC", ra_h=12, ra_m=30, ra_s=45.0, de_d=45, de_m=15, de_s=30.0,
                            flux_table={1420.0: 10.0}, spectral_index=-0.7)
        self.sources = Sources([self.source])

        self.telescope1 = Telescope(code="T1", name="Test Telescope 1", x=1000.0, y=2000.0, z=3000.0,
                                    diameter=25.0, sefd_table={1420.0: 500.0}, mount_type="AZIM", isactive=True)
        self.telescope2 = Telescope(code="T2", name="Test Telescope 2", x=-1000.0, y=-2000.0, z=-3000.0,
                                    diameter=25.0, sefd_table={1420.0: 500.0}, mount_type="EQUA", isactive=True)
        self.telescopes = Telescopes([self.telescope1, self.telescope2])
        self.telescopes.activate_all()  

        self.frequency = IF(freq=1420.0, bandwidth=32.0)
        self.frequencies = Frequencies([self.frequency])

        self.scan = Scan(start=1625097600.0, duration=300.0, source_index=0,
                        telescope_indices=[0, 1], frequency_indices=[0], isactive=True)
        self.scans = Scans([self.scan])

        self.observation_vlbi = Observation(observation_code="OBS_VLBI", sources=self.sources, telescopes=self.telescopes,
                                            frequencies=self.frequencies, scans=self.scans, observation_type="VLBI")
        self.observation_single = Observation(observation_code="OBS_SINGLE", sources=self.sources, telescopes=self.telescopes,
                                            frequencies=self.frequencies, scans=self.scans, observation_type="SINGLE_DISH")

        self.project = Project(name="TEST_PROJECT", observations=[self.observation_vlbi, self.observation_single])

    def test_init(self):
        self.assertIsInstance(self.calculator, Calculator)
        self.assertEqual(repr(self.calculator), "Calculator()")

    def test_calculate_telescope_positions(self):
        result = self.calculator.execute(self.observation_vlbi, {"type": "telescope_positions", "time_step": None})
        print(result)
        self.assertIn(0, result)
        self.assertIn("telescope_positions", result[0])
        self.assertEqual(set(result[0]["telescope_positions"].keys()), {"T1", "T2"})
        # Проверка с шагом времени
        result = self.calculator.execute(self.observation_vlbi, {"type": "telescope_positions", "time_step": 100.0})
        self.assertIn("times", result[0])
        self.assertTrue(len(result[0]["telescope_positions"]["T1"]["positions"]) > 1)

    def test_calculate_source_visibility(self):
        result = self.calculator.execute(self.observation_vlbi, {"type": "source_visibility", "time_step": None})
        self.assertIn(0, result)
        self.assertEqual(result[0]["source"], "TEST_SRC")
        self.assertEqual(set(result[0]["visibility"].keys()), {"T1", "T2"})
        # Проверка с шагом времени
        result = self.calculator.execute(self.observation_vlbi, {"type": "source_visibility", "time_step": 100.0})
        self.assertIn("times", result[0])
        self.assertTrue(len(result[0]["visibility"]["T1"]) > 1)

    def test_calculate_uv_coverage(self):
        result = self.calculator.execute(self.observation_vlbi, {"type": "uv_coverage", "time_step": None})
        self.assertIn(0, result)
        self.assertIn("uv_points", result[0])
        self.assertTrue(len(result[0]["uv_points"][1420e6]) == 1)
        # Проверка с шагом времени
        result = self.calculator.execute(self.observation_vlbi, {"type": "uv_coverage", "time_step": 100.0})
        self.assertIn("times", result[0])
        self.assertTrue(len(result[0]["uv_points"][1420e6]) > 1)

    def test_calculate_sun_angles(self):
        result = self.calculator.execute(self.observation_vlbi, {"type": "sun_angles", "time_step": None})
        self.assertIn(0, result)
        self.assertEqual(result[0]["source"], "TEST_SRC")
        self.assertTrue(isinstance(result[0]["sun_angle"], float))
        # Проверка с шагом времени
        result = self.calculator.execute(self.observation_vlbi, {"type": "sun_angles", "time_step": 100.0})
        self.assertIn("times", result[0])
        self.assertTrue(len(result[0]["sun_angles"]) > 1)

    def test_calculate_az_el(self):
        result = self.calculator.execute(self.observation_vlbi, {"type": "az_el", "time_step": None})
        self.assertIn(0, result)
        self.assertEqual(result[0]["source"], "TEST_SRC")
        self.assertEqual(set(result[0]["az_el"].keys()), {"T1", "T2"})
        # Проверка с шагом времени
        result = self.calculator.execute(self.observation_vlbi, {"type": "az_el", "time_step": 100.0})
        self.assertIn("times", result[0])
        self.assertTrue(len(result[0]["az_el"]["T1"]["coord1"]) > 1)

    def test_calculate_time_on_source(self):
        result = self.calculator.execute(self.observation_vlbi, {"type": "time_on_source"})
        self.assertIn("TEST_SRC", result)
        self.assertEqual(result["TEST_SRC"]["total_time"], 300.0)
        self.assertEqual(len(result["TEST_SRC"]["scans"]), 1)

    def test_calculate_beam_pattern(self):
        result = self.calculator.execute(self.observation_single, {"type": "beam_pattern", "freq_idx": 0})
        self.assertIn("T1", result)
        self.assertIn("theta", result["T1"])
        self.assertIn("pattern", result["T1"])
        self.assertEqual(len(result["T1"]["theta"]), 1000)
        # Проверка ошибки для VLBI
        result = self.calculator.execute(self.observation_vlbi, {"type": "beam_pattern"})
        self.assertEqual(result, {})

    def test_calculate_synthesized_beam(self):
        result = self.calculator.execute(self.observation_vlbi, {"type": "synthesized_beam", "freq_idx": 0})
        self.assertIn(0, result)
        self.assertIn("theta", result[0])
        self.assertIn("pattern", result[0])
        self.assertEqual(len(result[0]["theta"]), 1000)
        # Проверка ошибки для SINGLE_DISH
        result = self.calculator.execute(self.observation_single, {"type": "synthesized_beam"})
        self.assertEqual(result, {})

    def test_calculate_baseline_projections(self):
        result = self.calculator.execute(self.observation_vlbi, {"type": "baseline_projections", "time_step": None})
        self.assertIn(0, result)
        self.assertIn("projections", result[0])
        self.assertIn("T1-T2", result[0]["projections"])
        self.assertEqual(len(result[0]["projections"]["T1-T2"]), 3)  # u, v, w
        # Проверка с шагом времени
        result = self.calculator.execute(self.observation_vlbi, {"type": "baseline_projections", "time_step": 100.0})
        self.assertIn("times", result[0])
        self.assertTrue(len(result[0]["projections"]["T1-T2"]["u"]) > 1)

    def test_calculate_mollweide_tracks(self):
        result = self.calculator.execute(self.observation_vlbi, {"type": "mollweide_tracks", "time_step": None})
        self.assertIn(0, result)
        self.assertEqual(result[0]["source"], "TEST_SRC")
        self.assertIn("mollweide", result[0])
        self.assertTrue(isinstance(result[0]["mollweide"]["lon"], float))
        # Проверка с шагом времени
        result = self.calculator.execute(self.observation_vlbi, {"type": "mollweide_tracks", "time_step": 100.0})
        self.assertIn("times", result[0])
        self.assertTrue(len(result[0]["mollweide"]["lon"]) > 1)

    def test_project_calculations(self):
        result = self.calculator.execute(self.project, {"type": "telescope_positions", "time_step": None})
        self.assertIn("OBS_VLBI", result)
        self.assertIn("OBS_SINGLE", result)
        self.assertIn(0, result["OBS_VLBI"])

    def test_invalid_type(self):
        with self.assertRaises(ValueError):
            self.calculator.execute(self.observation_vlbi, {"type": "invalid_calculation"})

    def test_none_object(self):
        with self.assertRaises(ValueError):
            self.calculator.execute(None, {"type": "telescope_positions"})

    def test_missing_type(self):
        with self.assertRaises(ValueError):
            self.calculator.execute(self.observation_vlbi, {})

if __name__ == "__main__":
    unittest.main()