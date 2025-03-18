# tests/test_super_classes.py
import unittest
from super.manipulator import Manipulator
from super.configurator import Configurator
from super.calculator import Calculator
from base.observation import Observation, Project
from base.frequencies import IF, Frequencies
from base.telescopes import Telescope, Telescopes
from base.sources import Source, Sources
from base.scans import Scan, Scans
from catalog_manager import CatalogManager

class TestManipulator(unittest.TestCase):
    def setUp(self):
        self.project = Project(project_name="Test Project")
        self.manipulator = Manipulator(self.project)
        self.obs = Observation(observation_code="OBS1")
        self.manipulator.add_observation(self.obs)

    def test_add_observation(self):
        self.assertEqual(len(self.manipulator.get_all_observations()), 1)
        self.assertEqual(self.manipulator.get_observation(0).observation_code, "OBS1")

    def test_remove_observation(self):
        self.manipulator.remove_observation(0)
        self.assertEqual(len(self.manipulator.get_all_observations()), 0)

    def test_save_load_project(self):
        self.manipulator.save_project("test_project.json")
        new_manipulator = Manipulator()
        new_manipulator.load_project("test_project.json")
        self.assertEqual(new_manipulator.project.project_name, "Test Project")

class TestConfigurator(unittest.TestCase):
    def setUp(self):
        self.catalog_manager = CatalogManager()
        self.configurator = Configurator(self.catalog_manager)
        self.obs = Observation(observation_code="OBS1")
        # Mock catalog data
        self.catalog_manager.source_catalog.add_source(Source("Src1", 12, 0, 0, 30, 0, 0))
        self.catalog_manager.telescope_catalog.add_telescope(Telescope("T1", "Telescope1", 0, 0, 0, 0, 0, 0))

    def test_add_source(self):
        self.configurator.add_source(self.obs, "Src1")
        self.assertEqual(len(self.obs.sources), 1)

    def test_add_telescope(self):
        self.configurator.add_telescope(self.obs, "T1")
        self.assertEqual(len(self.obs.telescopes), 1)

    def test_add_frequency(self):
        self.configurator.add_frequency(self.obs, 1400, 32)
        self.assertEqual(len(self.obs.frequencies), 1)

class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.calculator = Calculator()
        self.obs = Observation(observation_code="OBS1")
        self.obs.telescopes.add_telescope(Telescope("T1", "Telescope1", 0, 0, 6371e3, 0, 0, 0))  # At pole
        self.obs.sources.add_source(Source("Src1", 12, 0, 0, 0, 0, 0))  # Equator
        self.obs.scans.add_scan(Scan(start=0, duration=3600, source=self.obs.sources.get_source(0)))

    def test_source_visibility(self):
        visibility = self.calculator.calculate_source_visibility(self.obs, "T1", "Src1")
        self.assertTrue(visibility)  # Should be visible from pole to equator at t=0

if __name__ == '__main__':
    unittest.main()