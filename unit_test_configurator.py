import unittest
from typing import Dict, Any, Callable
from base.sources import Source, Sources
from base.telescopes import Telescope, Telescopes
from base.frequencies import IF, Frequencies
from base.scans import Scan, Scans
from base.observation import Observation
from base.project import Project
from super.configurator import Configurator, DefaultConfigurator

# Заглушка для Manipulator
class MockManipulator:
    def get_methods_for_type(self, obj_type: type) -> Dict[str, Callable]:
        # Возвращает словарь методов для каждого типа объекта
        if obj_type == IF:
            return {"set_frequency": IF.set_frequency, "set_bandwidth": IF.set_bandwidth}
        elif obj_type == Frequencies:
            return {"add_IF": Frequencies.add_IF}
        elif obj_type == Source:
            return {"set_name": Source.set_name, "set_coordinates": Source.set_coordinates}
        elif obj_type == Sources:
            return {"add_source": Sources.add_source}
        elif obj_type == Telescope:
            return {"set_name": Telescope.set_name, "set_coordinates": Telescope.set_coordinates}
        elif obj_type == Telescopes:
            return {"add_telescope": Telescopes.add_telescope}
        elif obj_type == Scan:
            return {"set_start": Scan.set_start, "set_duration": Scan.set_duration}
        elif obj_type == Scans:
            return {"add_scan": Scans.add_scan}
        elif obj_type == Observation:
            return {"set_observation_code": Observation.set_observation_code, "set_observation_type": Observation.set_observation_type}
        elif obj_type == Project:
            return {"set_name": Project.set_name}
        elif obj_type == Configurator:
            return {
                "_configure_if": Configurator._configure_if,
                "_configure_frequencies": Configurator._configure_frequencies,
                "_configure_source": Configurator._configure_source,
                "_configure_sources": Configurator._configure_sources,
                "_configure_telescope": Configurator._configure_telescope,
                "_configure_telescopes": Configurator._configure_telescopes,
                "_configure_scan": Configurator._configure_scan,
                "_configure_scans": Configurator._configure_scans,
                "_configure_observation": Configurator._configure_observation,
                "_configure_project": Configurator._configure_project
            }
        return {}

class TestConfigurator(unittest.TestCase):
    def setUp(self):
        # Создание тестовых данных
        self.manipulator = MockManipulator()
        self.configurator = DefaultConfigurator(self.manipulator)

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
        self.assertIsInstance(self.configurator, Configurator)
        self.assertEqual(repr(self.configurator), "Configurator()")

    def test_configure_if(self):
        attributes = {"set_frequency": {"frequency": 1420.0}, "set_bandwidth": {"bandwidth": 64.0}}
        success = self.configurator._configure_if(self.frequency, attributes)
        self.assertTrue(success)
        self.assertEqual(self.frequency.get_frequency(), 1420.0)
        self.assertEqual(self.frequency.get_bandwidth(), 64.0)

        # Проверка с неверным методом
        self.assertFalse(self.configurator._configure_if(self.frequency, {"invalid_method": {}}))

    def test_configure_frequencies(self):
        attributes = {"if_index": 0, "set_frequency": {"frequency": 1420.0}}
        success = self.configurator._configure_frequencies(self.frequencies, attributes)
        self.assertTrue(success)
        self.assertEqual(self.frequencies.get_IF(0).get_frequency(), 1420.0)

        # Проверка с неверным индексом
        self.assertFalse(self.configurator._configure_frequencies(self.frequencies, {"if_index": 999}))

    def test_configure_source(self):
        attributes = {"set_name": {"name": "NEW_SRC"}, "set_coordinates": {"ra_h": 15, "ra_m": 0, "ra_s": 0.0, "de_d": 60, "de_m": 0, "de_s": 0.0}}
        success = self.configurator._configure_source(self.source, attributes)
        self.assertTrue(success)
        self.assertEqual(self.source.get_name(), "NEW_SRC")
        self.assertEqual(self.source.get_coordinates(), (15, 0, 0.0, 60, 0, 0.0))

    def test_configure_sources(self):
        attributes = {"source_index": 0, "set_name": {"name": "NEW_SRC"}}
        success = self.configurator._configure_sources(self.sources, attributes)
        self.assertTrue(success)
        self.assertEqual(self.sources.get_source(0).get_name(), "NEW_SRC")

    def test_configure_telescope(self):
        attributes = {"set_name": {"name": "New Telescope"}, "set_coordinates": {"x": 0.0, "y": 0.0, "z": 0.0}}
        success = self.configurator._configure_telescope(self.telescope, attributes)
        self.assertTrue(success)
        self.assertEqual(self.telescope.get_name(), "New Telescope")
        self.assertEqual(self.telescope.get_coordinates(), (0.0, 0.0, 0.0))

    def test_configure_telescopes(self):
        attributes = {"telescope_index": 0, "set_name": {"name": "New Telescope"}}
        success = self.configurator._configure_telescopes(self.telescopes, attributes)
        self.assertTrue(success)
        self.assertEqual(self.telescopes.get_by_index(0).get_name(), "New Telescope")

    def test_configure_scan(self):
        attributes = {"set_start": {"start": 1625097900.0}, "set_duration": {"duration": 600.0}, "observation": self.observation}
        success = self.configurator._configure_scan(self.scan, attributes)
        self.assertTrue(success)
        self.assertEqual(self.scan.get_start(), 1625097900.0)
        self.assertEqual(self.scan.get_duration(), 600.0)

        # Проверка с невалидной конфигурацией
        invalid_attrs = {"set_start": {"start": 1625097600.0}, "observation": self.observation}
        self.scans.add_scan(Scan(start=1625097600.0, duration=300.0, source_index=0, telescope_indices=[0], frequency_indices=[0]))
        self.assertFalse(self.configurator._configure_scan(self.scan, invalid_attrs))

    def test_configure_scans(self):
        attributes = {"scan_index": 0, "set_duration": {"duration": 600.0}}
        success = self.configurator._configure_scans(self.scans, attributes)
        self.assertTrue(success)
        self.assertEqual(self.scans.get_scan(0).get_duration(), 600.0)

        # Проверка перекрытия
        self.scans.add_scan(Scan(start=1625097800.0, duration=300.0, source_index=0, telescope_indices=[0], frequency_indices=[0]))
        overlap_attrs = {"scan_index": 0, "set_duration": {"duration": 1000.0}}
        self.assertFalse(self.configurator._configure_scans(self.scans, overlap_attrs))

    def test_configure_observation(self):
        attributes = {"set_observation_code": {"observation_code": "OBS002"}, "set_observation_type": {"observation_type": "SINGLE_DISH"}}
        success = self.configurator._configure_observation(self.observation, attributes)
        self.assertTrue(success)
        self.assertEqual(self.observation.get_observation_code(), "OBS002")
        self.assertEqual(self.observation.get_observation_type(), "SINGLE_DISH")

        # Проверка с невалидной конфигурацией
        invalid_attrs = {"set_observation_type": {"observation_type": "INVALID"}}
        self.assertFalse(self.configurator._configure_observation(self.observation, invalid_attrs))

    def test_configure_project(self):
        attributes = {"set_name": {"name": "NEW_PROJECT"}}
        success = self.configurator._configure_project(self.project, attributes)
        self.assertTrue(success)
        self.assertEqual(self.project.get_name(), "NEW_PROJECT")

        # Проверка вложенной конфигурации наблюдения
        nested_attrs = {"observation_index": 0, "set_observation_code": {"observation_code": "OBS_NEW"}}
        success = self.configurator._configure_project(self.project, nested_attrs)
        self.assertTrue(success)
        self.assertEqual(self.project.get_observation(0).get_observation_code(), "OBS_NEW")

    def test_execute(self):
        # Тестирование execute для разных типов объектов
        self.assertTrue(self.configurator.execute(self.frequency, {"set_frequency": {"frequency": 1420.0}}))
        self.assertTrue(self.configurator.execute(self.frequencies, {"if_index": 0, "set_bandwidth": {"bandwidth": 64.0}}))
        self.assertTrue(self.configurator.execute(self.source, {"set_name": {"name": "SRC_NEW"}}))
        self.assertTrue(self.configurator.execute(self.sources, {"source_index": 0, "set_name": {"name": "SRC_UPDATED"}}))
        self.assertTrue(self.configurator.execute(self.telescope, {"set_name": {"name": "TEL_NEW"}}))
        self.assertTrue(self.configurator.execute(self.telescopes, {"telescope_index": 0, "set_name": {"name": "TEL_UPDATED"}}))
        self.assertTrue(self.configurator.execute(self.scan, {"set_duration": {"duration": 900.0}, "observation": self.observation}))
        self.assertTrue(self.configurator.execute(self.scans, {"scan_index": 0, "set_start": {"start": 1625098000.0}}))
        self.assertTrue(self.configurator.execute(self.observation, {"set_observation_code": {"observation_code": "OBS_NEW"}}))
        self.assertTrue(self.configurator.execute(self.project, {"set_name": {"name": "PROJECT_NEW"}}))

        # Проверка ошибки для неподдерживаемого типа
        with self.assertRaises(ValueError):
            self.configurator.execute(None, {})

if __name__ == "__main__":
    unittest.main()