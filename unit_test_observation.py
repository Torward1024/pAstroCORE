import unittest
from datetime import datetime
from base.sources import Source, Sources
from base.telescopes import Telescope, Telescopes
from base.frequencies import Frequencies, IF  # Предполагается, что класс IF определён в frequencies.py
from base.scans import Scan, Scans
from base.observation import Observation  # Предполагаемый класс Observation

class TestObservation(unittest.TestCase):
    def setUp(self):
        # Создание тестовых данных
        self.source = Source(name="TEST_SRC", ra_h=12, ra_m=30, ra_s=45.0, de_d=45, de_m=15, de_s=30.0,
                             flux_table={1400.0: 10.0}, spectral_index=-0.7)
        self.sources = Sources([self.source])

        self.telescope = Telescope(code="T1", name="Test Telescope", x=1000.0, y=2000.0, z=3000.0,
                                  diameter=25.0, sefd_table={1400.0: 500.0})
        self.telescopes = Telescopes([self.telescope])

        self.frequency = IF(freq=1400.0, bandwidth=32.0)
        self.frequencies = Frequencies([self.frequency])

        self.scan = Scan(start=1625097600.0, duration=300.0, source_index=0,
                         telescope_indices=[0], frequency_indices=[0])
        self.scans = Scans([self.scan])

        self.observation = Observation(observation_code="OBS001", sources=self.sources, telescopes=self.telescopes,
                                      frequencies=self.frequencies, scans=self.scans)

    def test_init(self):
        self.assertEqual(self.observation.get_observation_code(), "OBS001")
        self.assertEqual(self.observation.get_sources(), self.sources)
        self.assertEqual(self.observation.get_telescopes(), self.telescopes)
        self.assertEqual(self.observation.get_frequencies(), self.frequencies)
        self.assertEqual(self.observation.get_scans(), self.scans)
        self.assertTrue(self.observation.isactive)

    def test_get_methods(self):
        self.assertEqual(self.observation.get_observation_code(), "OBS001")
        self.assertEqual(len(self.observation.get_sources().get_all_sources()), 1)
        self.assertEqual(len(self.observation.get_telescopes().get_all_telescopes()), 1)
        self.assertEqual(len(self.observation.get_frequencies().get_all_IF()), 1)
        self.assertEqual(len(self.observation.get_scans().get_all_scans()), 1)

    def test_set_observation(self):
        new_source = Source(name="NEW_SRC", ra_h=15, ra_m=0, ra_s=0.0, de_d=60, de_m=0, de_s=0.0)
        new_sources = Sources([new_source])
        self.observation.set_observation(observation_code="OBS002", sources=new_sources, telescopes=self.telescopes,
                                        frequencies=self.frequencies, scans=self.scans)
        self.assertEqual(self.observation.get_observation_code(), "OBS002")
        self.assertEqual(self.observation.get_sources().get_all_sources()[0].get_name(), "NEW_SRC")

    def test_serialization(self):
        obs_dict = self.observation.to_dict()
        self.assertEqual(obs_dict["observation_code"], "OBS001")
        self.assertEqual(len(obs_dict["sources"]["data"]), 1)
        self.assertEqual(len(obs_dict["telescopes"]["data"]), 1)
        self.assertEqual(len(obs_dict["frequencies"]["data"]), 1)
        self.assertEqual(len(obs_dict["scans"]["data"]), 1)
        self.assertTrue(obs_dict["isactive"])

    def test_deserialization(self):
        obs_dict = self.observation.to_dict()
        new_obs = Observation.from_dict(obs_dict)
        self.assertEqual(new_obs.get_observation_code(), "OBS001")
        self.assertEqual(new_obs.get_sources().get_all_sources()[0].get_name(), "TEST_SRC")
        self.assertEqual(new_obs.get_telescopes().get_all_telescopes()[0].get_code(), "T1")
        self.assertEqual(new_obs.get_frequencies().get_all_IF()[0].get_frequency(), 1400.0)
        self.assertEqual(new_obs.get_scans().get_all_scans()[0].get_start(), 1625097600.0)

    def test_scan_validation(self):
        # Проверка валидации сканирования с корректными индексами
        self.assertTrue(self.scan.validate_with_observation(self.observation))

        # Проверка с некорректным индексом источника
        invalid_scan = Scan(start=1625097900.0, duration=300.0, source_index=999,
                            telescope_indices=[0], frequency_indices=[0])
        self.assertFalse(invalid_scan.validate_with_observation(self.observation))

    def test_telescope_availability(self):
        # Проверка доступности телескопа для сканирования
        availability = self.scan.check_telescope_availability(self.observation)
        self.assertIn("T1", availability)
        self.assertTrue(availability["T1"])  # Предполагаем, что источник виден для простоты

    def test_activation_deactivation(self):
        self.observation.deactivate()
        self.assertFalse(self.observation.isactive)
        self.assertEqual(len(self.observation.get_scans().get_active_scans(self.observation)), 1)  # Скан всё ещё активен
        self.observation.get_scans().deactivate_all()
        self.assertEqual(len(self.observation.get_scans().get_active_scans(self.observation)), 0)
        self.observation.activate()
        self.assertTrue(self.observation.isactive)

if __name__ == "__main__":
    unittest.main()