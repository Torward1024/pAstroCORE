import unittest
from unit_scheduling_2.base.observation import Observation
from unit_scheduling_2.super.schedule_project import ScheduleProject
import logging

class TestScheduleProject(unittest.TestCase):
    def setUp(self):
        """Set up a ScheduleProject instance and sample observations for testing."""
        self.project = ScheduleProject(name="TestProject")
        self.obs1 = Observation(name="OBS001", observation_type="VLBI")
        self.obs2 = Observation(name="OBS002", observation_type="SINGLE_DISH", isactive=False)
        logging.basicConfig(level=logging.DEBUG)

    def test_initialization(self):
        """Test ScheduleProject initialization with and without items."""
        # Test empty initialization
        project = ScheduleProject(name="EmptyProject")
        self.assertEqual(project._name, "EmptyProject")
        self.assertEqual(len(project._items), 0)

        # Test initialization with items
        items = {"OBS001": self.obs1, "OBS002": self.obs2}
        project = ScheduleProject(name="PopulatedProject", items=items)
        self.assertEqual(project._name, "PopulatedProject")
        self.assertEqual(len(project._items), 2)
        self.assertEqual(project.get_observation("OBS001").get_observation_code(), "OBS001")
        self.assertEqual(project.get_observation("OBS002").isactive, False)

    def test_add_item(self):
        """Test adding an observation to the project."""
        self.project.add_item(self.obs1)
        self.assertEqual(len(self.project._items), 1)
        self.assertEqual(self.project.get_observation("OBS001").get_observation_code(), "OBS001")

        # Test adding non-Observation raises TypeError
        with self.assertRaises(TypeError):
            self.project.add_item("NotAnObservation")

    def test_create_item(self):
        """Test creating and adding a new observation."""
        self.project.create_item(item_code="OBS003", isactive=True)
        self.assertEqual(len(self.project._items), 1)
        obs = self.project.get_observation("OBS003")
        self.assertEqual(obs.get_observation_code(), "OBS003")
        self.assertTrue(obs.isactive)

        # Test invalid observation code
        with self.assertRaises(ValueError):
            self.project.create_item(item_code="")

    def test_set_item(self):
        """Test setting or replacing an observation."""
        self.project.add_item(self.obs1)
        new_obs = Observation(name="OBS001", observation_type="SINGLE_DISH")
        self.project.set_item("OBS001", new_obs)
        self.assertEqual(self.project.get_observation("OBS001").get_observation_type(), "SINGLE_DISH")

        # Test setting with non-Observation raises TypeError
        with self.assertRaises(TypeError):
            self.project.set_item("OBS001", "InvalidItem")

    def test_get_observation(self):
        """Test retrieving an observation by code."""
        self.project.add_item(self.obs1)
        obs = self.project.get_observation("OBS001")
        self.assertEqual(obs.get_observation_code(), "OBS001")

        # Test retrieving non-existent observation raises KeyError
        with self.assertRaises(KeyError):
            self.project.get_observation("OBS999")

    def test_set_project(self):
        """Test setting project name and items."""
        new_items = {"OBS001": self.obs1, "OBS002": self.obs2}
        self.project.set_project(name="NewProject", items=new_items)
        self.assertEqual(self.project._name, "NewProject")
        self.assertEqual(len(self.project._items), 2)
        self.assertEqual(self.project.get_observation("OBS002").isactive, False)

        # Test setting with invalid items raises TypeError
        with self.assertRaises(TypeError):
            self.project.set_project(name="Invalid", items={"OBS001": "NotAnObservation"})

        # Test setting with empty name raises ValueError
        with self.assertRaises(ValueError):
            self.project.set_project(name="", items={})

    def test_get_project(self):
        """Test retrieving project configuration as a dictionary."""
        self.project.add_item(self.obs1)
        project_dict = self.project.get_project()
        self.assertEqual(project_dict["name"], "TestProject")
        self.assertEqual(len(project_dict["observations"]), 1)
        self.assertEqual(project_dict["observations"][0]["name"], "OBS001")

    def test_to_dict(self):
        """Test serialization of ScheduleProject to dictionary."""
        self.project.add_item(self.obs1)
        self.project.add_item(self.obs2)
        project_dict = self.project.to_dict()
        self.assertEqual(project_dict["name"], "TestProject")
        self.assertEqual(len(project_dict["items"]), 2)
        self.assertEqual(project_dict["items"]["OBS001"]["name"], "OBS001")
        self.assertFalse(project_dict["items"]["OBS002"]["isactive"])

    def test_from_dict(self):
        """Test deserialization of ScheduleProject from dictionary."""
        data = {
            "name": "TestProject",
            "items": {
                "OBS001": self.obs1.to_dict(),
                "OBS002": self.obs2.to_dict()
            }
        }
        project = ScheduleProject.from_dict(data)
        self.assertEqual(project._name, "TestProject")
        self.assertEqual(len(project._items), 2)
        self.assertEqual(project.get_observation("OBS001").get_observation_type(), "VLBI")
        self.assertFalse(project.get_observation("OBS002").isactive)

        # Test invalid data raises ValueError
        invalid_data = {"name": "Invalid", "items": {}}
        with self.assertRaises(ValueError):
            ScheduleProject.from_dict(invalid_data)

if __name__ == "__main__":
    unittest.main()