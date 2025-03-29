import unittest
from typing import Dict, Any, Callable
from base.sources import Source, Sources
from base.telescopes import Telescope, Telescopes
from base.frequencies import IF, Frequencies
from base.scans import Scan, Scans
from base.observation import Observation
from base.project import Project
from super.manipulator import Manipulator, DefaultManipulator
from super.configurator import Configurator, DefaultConfigurator
from super.inspector import DefaultInspector
from super.calculator import DefaultCalculator
from utils.logging_setup import logger

# Заглушка для супер-классов с минимальной реализацией execute
class MockConfigurator:
    def __init__(self, manipulator):
        self._manipulator = manipulator

    def execute(self, obj: Any, attributes: Dict[str, Any]) -> bool:
        if isinstance(obj, Source) and "set_name" in attributes:
            obj.set_name(**attributes["set_name"])
            return True
        return False

class MockInspector:
    def __init__(self, manipulator):
        self._manipulator = manipulator

    def execute(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(obj, Source) and "get_name" in attributes:
            return {"get_name": obj.get_name()}
        return {}

class MockCalculator:
    def __init__(self, manipulator):
        self._manipulator = manipulator

    def execute(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(obj, Observation) and "type" in attributes and attributes["type"] == "telescope_positions":
            return {"mock_calc": "positions"}
        return {}

class TestManipulator(unittest.TestCase):
    def setUp(self):
        # Создание тестовых данных
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

        # Инициализация Manipulator с заглушками
        self.manipulator = DefaultManipulator(project=self.project)
        self.manipulator._configurator = MockConfigurator(self.manipulator)
        self.manipulator._inspector = MockInspector(self.manipulator)
        self.manipulator._calculator = MockCalculator(self.manipulator)

    def test_init(self):
        manipulator = DefaultManipulator()
        self.assertIsInstance(manipulator, Manipulator)
        self.assertEqual(repr(manipulator), "Manipulator(project='None')")
        self.assertEqual(manipulator.get_project(), None)
        logger.info("Tested Manipulator initialization without project")

    def test_init_with_project(self):
        self.assertEqual(self.manipulator.get_project(), self.project)
        self.assertEqual(repr(self.manipulator), "Manipulator(project='TEST_PROJECT')")
        logger.info("Tested Manipulator initialization with project")

    def test_set_project(self):
        manipulator = DefaultManipulator()
        manipulator.set_project(self.project)
        self.assertEqual(manipulator.get_project(), self.project)
        logger.info("Tested set_project with valid project")

    def test_set_project_invalid(self):
        manipulator = DefaultManipulator()
        with self.assertRaises(ValueError):
            manipulator.set_project("not_a_project")
        logger.info("Tested set_project with invalid input")

    def test_get_method_registry(self):
        registry = self.manipulator._get_method_registry()
        self.assertIn(Project, registry)
        self.assertIn(Observation, registry)
        self.assertIn(Source, registry)
        self.assertIn(Configurator, registry)
        self.assertTrue(len(registry) > 10)  # Проверка, что реестр содержит множество типов
        logger.info("Tested _get_method_registry initialization")

    def test_process_request_configure(self):
        attributes = {"set_name": {"name": "NEW_SRC"}}
        result = self.manipulator.process_request("configure", "source", attributes, self.source)
        self.assertTrue(result)  # MockConfigurator возвращает True
        self.assertEqual(self.source.get_name(), "NEW_SRC")
        logger.info("Tested process_request for configure operation")

    def test_process_request_inspect(self):
        attributes = {"get_name": None}
        result = self.manipulator.process_request("inspect", "source", attributes, self.source)
        self.assertEqual(result, {"get_name": "TEST_SRC"})
        logger.info("Tested process_request for inspect operation")

    def test_process_request_calculate(self):
        attributes = {"type": "telescope_positions"}
        result = self.manipulator.process_request("calculate", "observation", attributes, self.observation)
        self.assertEqual(result, {"mock_calc": "positions"})
        logger.info("Tested process_request for calculate operation")

    def test_process_request_invalid_operation(self):
        with self.assertRaises(ValueError):
            self.manipulator.process_request("invalid_op", "source", {"get_name": None}, self.source)
        logger.info("Tested process_request with invalid operation")

    def test_process_request_no_project_no_obj(self):
        manipulator = DefaultManipulator()
        with self.assertRaises(ValueError):
            manipulator.process_request("inspect", "source", {"get_name": None})
        logger.info("Tested process_request with no project and no object")

    def test_process_request_invalid_attributes(self):
        with self.assertRaises(ValueError):
            self.manipulator.process_request("configure", "source", "not_a_dict", self.source)
        logger.info("Tested process_request with invalid attributes")

    def test_get_methods_for_type(self):
        methods = self.manipulator.get_methods_for_type(Source)
        self.assertIn("get_name", methods)
        self.assertIn("set_name", methods)
        logger.info("Tested get_methods_for_type for Source")

    def test_get_methods_for_type_invalid(self):
        with self.assertRaises(ValueError):
            self.manipulator.get_methods_for_type(str)
        logger.info("Tested get_methods_for_type with invalid type")

if __name__ == "__main__":
    unittest.main()