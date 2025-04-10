# tests/test_project.py
import unittest
from typing import Dict, Any
from common.super.project import Project
from common.base.baseentity import BaseEntity
from common.utils.logging_setup import logger

class TestObservation(BaseEntity):
    frequency: float

class TestObservationProject(Project):
    _item_type = TestObservation

    def create_item(self, item_code: str = "OBS_DEFAULT", isactive: bool = True) -> None:
        self._items.add(TestObservation(name=item_code, isactive=isactive, frequency=1.4))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestObservationProject':
        items = {k: TestObservation.from_dict(v) for k, v in data["items"].items()}
        return cls(name=data["name"], items=items)

class TestProject(unittest.TestCase):
    def setUp(self) -> None:
        self.project = TestObservationProject(name="TestProj")

    def test_init(self) -> None:
        proj = TestObservationProject(name="InitTest")
        self.assertEqual(proj.get_name(), "InitTest")
        self.assertEqual(len(proj.get_items()), 0)
        logger.info("Project initialized successfully")

    def test_init_empty_name(self) -> None:
        with self.assertRaises(ValueError):
            TestObservationProject(name="")
        logger.info("Empty name validation tested successfully")

    def test_add_item(self) -> None:
        item = TestObservation(name="OBS1", frequency=2.0)
        self.project.add_item(item)
        self.assertEqual(self.project.get_item("OBS1").frequency, 2.0)
        with self.assertRaises(ValueError):
            self.project.add_item(item)  # Duplicate name
        logger.info("Item added successfully")

    def test_add_invalid_item(self) -> None:
        invalid_item = BaseEntity(name="OBS_INVALID")  # Не TestObservation
        with self.assertRaises(TypeError):
            self.project.add_item(invalid_item)
        logger.info("Invalid item type validation tested successfully")

    def test_create_item(self) -> None:
        self.project.create_item("OBS2", isactive=False)
        item = self.project.get_item("OBS2")
        self.assertEqual(item.name, "OBS2")
        self.assertEqual(item.frequency, 1.4)
        self.assertFalse(item.isactive)
        logger.info("Item created successfully")

    def test_remove_item(self) -> None:
        self.project.create_item("OBS3")
        self.project.remove_item("OBS3")
        with self.assertRaises(KeyError):
            self.project.get_item("OBS3")
        logger.info("Item removed successfully")

    def test_remove_nonexistent_item(self) -> None:
        with self.assertRaises(KeyError):
            self.project.remove_item("OBS_NONEXISTENT")
        logger.info("Nonexistent item removal tested successfully")

    def test_serialization(self) -> None:
        self.project.create_item("OBS4")
        data = self.project.to_dict()
        self.assertEqual(data["name"], "TestProj")
        self.assertIn("OBS4", data["items"])
        new_proj = TestObservationProject.from_dict(data)
        self.assertEqual(new_proj.get_item("OBS4").frequency, 1.4)
        logger.info("Serialization/deserialization tested successfully")

    def test_set_project(self) -> None:
        new_items = {"OBS5": TestObservation(name="OBS5", frequency=3.0)}
        self.project.set_project("NewProj", new_items)
        self.assertEqual(self.project.get_name(), "NewProj")
        self.assertEqual(self.project.get_item("OBS5").frequency, 3.0)
        self.assertEqual(len(self.project.get_items()), 1)
        logger.info("Project configuration set successfully")

    def test_set_name(self) -> None:
        self.project.set_name("RenamedProj")
        self.assertEqual(self.project.get_name(), "RenamedProj")
        with self.assertRaises(ValueError):
            self.project.set_name("")  # Empty name
        logger.info("Name setting tested successfully")

    def test_get_project(self) -> None:
        self.project.create_item("OBS6")
        proj_data = self.project.get_project()
        self.assertEqual(proj_data["name"], "TestProj")
        self.assertIn("OBS6", proj_data["items"])
        self.assertEqual(proj_data["items"]["OBS6"]["frequency"], 1.4)
        logger.info("Get project configuration tested successfully")

    def test_item_activation(self) -> None:
        self.project.create_item("OBS7", isactive=False)
        item = self.project.get_item("OBS7")
        self.assertFalse(item.isactive)
        item.activate()
        self.assertTrue(self.project.get_item("OBS7").isactive)
        item.deactivate()
        self.assertFalse(self.project.get_item("OBS7").isactive)
        logger.info("Item activation/deactivation tested successfully")

    def test_large_number_of_items(self) -> None:
        for i in range(1000):
            self.project.create_item(f"OBS_LARGE_{i}")
        self.assertEqual(len(self.project.get_items()), 1000)
        self.project.remove_item("OBS_LARGE_500")
        self.assertEqual(len(self.project.get_items()), 999)
        logger.info("Large number of items tested successfully")

if __name__ == "__main__":
    unittest.main()