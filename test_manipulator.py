# tests/test_manipulator.py
import unittest
from typing import Dict, Any
from common.super.manipulator import Manipulator
from common.super.super import Super
from common.base.baseentity import BaseEntity
from common.utils.logging_setup import logger

class TestEntity(BaseEntity):
    value: int

class TestSuper(Super):
    def _test_operation(self, obj: TestEntity, attributes: Dict[str, Any]) -> bool:
        obj.value = attributes.get("value", 0)
        return True

class TestManipulator(unittest.TestCase):
    def setUp(self) -> None:
        self.manipulator = Manipulator()
        self.super_instance = TestSuper(self.manipulator)
        self.manipulator.register_operation("test", self.super_instance)

    def test_init(self) -> None:
        manip = Manipulator(managing_object=TestEntity(name="obj"))
        self.assertEqual(manip.get_managing_object().name, "obj")
        self.assertEqual(len(manip.get_supported_operations()), 0)
        logger.info("Manipulator initialized successfully")

    def test_register_operation(self) -> None:
        self.assertIn("test", self.manipulator.get_supported_operations())
        with self.assertRaises(ValueError):
            self.manipulator.register_operation("", self.super_instance)  # Empty operation name
        logger.info("Operation registration tested")

    def test_process_request(self) -> None:
        entity = TestEntity(name="test_obj")
        request = {"operation": "test", "obj": entity, "attributes": {"value": 42}}
        result = self.manipulator.process_request(request)
        self.assertTrue(result)
        self.assertEqual(entity.value, 42)
        logger.info("Single request processed successfully")

    def test_process_nested_requests(self) -> None:
        entity1 = TestEntity(name="obj1")
        entity2 = TestEntity(name="obj2")
        requests = {
            "req1": {"operation": "test", "obj": entity1, "attributes": {"value": 10}},
            "req2": {"operation": "test", "obj": entity2, "attributes": {"value": 20}}
        }
        results = self.manipulator.process_request(requests)
        self.assertEqual(results["req1"], True)
        self.assertEqual(results["req2"], True)
        self.assertEqual(entity1.value, 10)
        self.assertEqual(entity2.value, 20)
        logger.info("Nested requests processed successfully")

    def test_invalid_request(self) -> None:
        request = {"operation": "unknown", "obj": TestEntity(name="obj")}
        result = self.manipulator.process_request(request)
        self.assertFalse(result)
        logger.info("Invalid request handled correctly")

if __name__ == "__main__":
    unittest.main()