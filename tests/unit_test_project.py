import unittest
from datetime import datetime
import astropy.units as u
from base.sources import Source, Sources
from base.telescopes import Telescope, Telescopes
from base.frequencies import Frequencies, IF
from base.scans import Scan, Scans
from base.observation import Observation

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
                                      frequencies=self.frequencies, scans=self.scans, observation_type="VLBI")

    def test_init(self):
        self.assertEqual(self.observation.get_observation_code(), "OBS001")
        self.assertEqual(self.observation.get_observation_type(), "VLBI")
        self.assertEqual(self.observation.get_sources(), self.sources)
        self.assertEqual(self.observation.get_telescopes(), self.telescopes)
        self.assertEqual(self.observation.get_frequencies(), self.frequencies)
        self.assertEqual(self.observation.get_scans(), self.scans)
        self.assertTrue(self.observation.isactive)
        self.assertEqual(self.observation.get_calculated_data(), {})

        # Проверка инициализации с пустыми значениями
        empty_obs = Observation(observation_code="OBS_EMPTY")
        self.assertIsInstance(empty_obs.get_sources(), Sources)
        self.assertIsInstance(empty_obs.get_telescopes(), Telescopes)
        self.assertIsInstance(empty_obs.get_frequencies(), Frequencies)
        self.assertIsInstance(empty_obs.get_scans(), Scans)

    def test_set_observation(self):
        new_source = Source(name="NEW_SRC", ra_h=15, ra_m=0, ra_s=0.0, de_d=60, de_m=0, de_s=0.0)
        new_sources = Sources([new_source])
        self.observation.set_observation(observation_code="OBS002", sources=new_sources, telescopes=self.telescopes,
                                        frequencies=self.frequencies, scans=self.scans, observation_type="SINGLE_DISH", isactive=False)
        self.assertEqual(self.observation.get_observation_code(), "OBS002")
        self.assertEqual(self.observation.get_observation_type(), "SINGLE_DISH")
        self.assertEqual(self.observation.get_sources().get_all_sources()[0].get_name(), "NEW_SRC")
        self.assertFalse(self.observation.isactive)
        self.assertEqual(self.observation.get_calculated_data(), {})  # Проверка очистки calculated_data

    def test_set_methods(self):
        self.observation.set_observation_code("OBS_NEW")
        self.assertEqual(self.observation.get_observation_code(), "OBS_NEW")

        self.observation.set_observation_type("SINGLE_DISH")
        self.assertEqual(self.observation.get_observation_type(), "SINGLE_DISH")

        new_telescopes = Telescopes([Telescope(code="T2", name="New Telescope", x=0, y=0, z=0, diameter=10.0)])
        self.observation.set_telescopes(new_telescopes)
        self.assertEqual(self.observation.get_telescopes(), new_telescopes)

        with self.assertRaises(ValueError):
            self.observation.set_observation_type("INVALID_TYPE")

    def test_calculated_data(self):
        data = {"SNR": 10.0, "visibility": [1, 2, 3]}
        self.observation.set_calculated_data(data)
        self.assertEqual(self.observation.get_calculated_data(), data)

        self.observation.set_calculated_data_by_key("test_key", 42)
        self.assertEqual(self.observation.get_calculated_data_by_key("test_key"), 42)

    def test_serialization(self):
        obs_dict = self.observation.to_dict()
        self.assertEqual(obs_dict["observation_code"], "OBS001")
        self.assertEqual(obs_dict["observation_type"], "VLBI")
        self.assertEqual(len(obs_dict["sources"]["data"]), 1)
        self.assertEqual(len(obs_dict["telescopes"]["data"]), 1)
        self.assertEqual(len(obs_dict["frequencies"]["data"]), 1)
        self.assertEqual(len(obs_dict["scans"]["data"]), 1)
        self.assertTrue(obs_dict["isactive"])
        self.assertEqual(obs_dict["calculated_data"], {})

    def test_deserialization(self):
        obs_dict = self.observation.to_dict()
        new_obs = Observation.from_dict(obs_dict)
        self.assertEqual(new_obs.get_observation_code(), "OBS001")
        self.assertEqual(new_obs.get_observation_type(), "VLBI")
        self.assertEqual(new_obs.get_sources().get_all_sources()[0].get_name(), "TEST_SRC")
        self.assertEqual(new_obs.get_telescopes().get_all_telescopes()[0].get_code(), "T1")
        self.assertEqual(new_obs.get_frequencies().get_all_IF()[0].get_frequency(), 1400.0)
        self.assertEqual(new_obs.get_scans().get_all_scans()[0].get_start(), 1625097600.0)

    def test_get_start_datetime(self):
        start_dt = self.observation.get_start_datetime()
        self.assertEqual(start_dt, datetime.fromtimestamp(1625097600.0))
        
        self.observation.get_scans().deactivate_all()
        self.assertIsNone(self.observation.get_start_datetime())

    def test_validate(self):
        self.assertTrue(self.observation.validate())

        # Проверка с пустыми данными
        invalid_obs = Observation(observation_code="OBS_INVALID")
        self.assertFalse(invalid_obs.validate())

        # Проверка с перекрытием сканирований
        overlapping_scan = Scan(start=1625097600.0, duration=600.0, source_index=0,
                                telescope_indices=[0], frequency_indices=[0])
        self.observation.set_scans(Scans([self.scan, overlapping_scan]))
        self.assertFalse(self.observation.validate())

    def test_update_scan_indices(self):
        new_source = Source(name="NEW_SRC", ra_h=15, ra_m=0, ra_s=0.0, de_d=60, de_m=0, de_s=0.0)
        self.sources.add_source(new_source)
        self.observation._update_scan_indices("sources", inserted_index=1)
        self.assertEqual(self.scan.get_source_index(), 0)  # Индекс не изменился, так как был меньше inserted_index

        self.sources.remove_source(0)
        self.observation._update_scan_indices("sources", removed_index=0)
        self.assertIsNone(self.scan.get_source_index())
        self.assertTrue(self.scan.is_off_source)

    def test_sync_scans_with_activation(self):
        self.telescopes.deactivate_telescope(0)
        self.observation._sync_scans_with_activation("telescopes", 0, False)
        self.assertEqual(self.scan.get_telescope_indices(), [])

        self.telescopes.activate_telescope(0)
        self.observation._sync_scans_with_activation("telescopes", 0, True)
        self.assertEqual(self.scan.get_telescope_indices(), [0])

    def test_activation_deactivation(self):
        self.observation.deactivate()
        self.assertFalse(self.observation.isactive)
        self.assertEqual(len(self.observation.get_scans().get_active_scans(self.observation)), 1)  # Скан всё ещё активен
        
        self.observation.get_scans().deactivate_all()
        self.assertEqual(len(self.observation.get_scans().get_active_scans(self.observation)), 0)
        
        self.observation.activate()
        self.assertTrue(self.observation.isactive)

    def test_repr(self):
        repr_str = repr(self.observation)
        self.assertIn("OBS001", repr_str)
        self.assertIn("VLBI", repr_str)
        self.assertIn("isactive=True", repr_str)

if __name__ == "__main__":
    unittest.main()