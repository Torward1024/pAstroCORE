# tests/test_super.py
import unittest
from typing import Dict, Any
from common.super.super import Super
from common.super.manipulator import Manipulator
from common.base.baseentity import BaseEntity
from common.utils.logging_setup import logger

class TestEntity(BaseEntity):
    value: int

class TestSuper(Super):
    def _configure(self, obj: TestEntity, attributes: Dict[str, Any]) -> bool:
        obj.value = attributes.get("value", 0)
        return True

    def _configure_testentity(self, obj: TestEntity, attributes: Dict[str, Any]) -> bool:
        obj.value = attributes.get("value", 0) * 2
        return True

class TestSuperClass(unittest.TestCase):
    def setUp(self) -> None:
        self.manipulator = Manipulator()
        self.super_instance = TestSuper(self.manipulator)
        self.manipulator.register_operation("configure", self.super_instance)

    def test_init(self) -> None:
        super_instance = TestSuper()
        self.assertEqual(super_instance._methods, {})
        logger.info("Super initialized successfully")

    def test_execute_default(self) -> None:
        entity = TestEntity(name="test_obj")
        result = self.super_instance.execute(entity, {"value": 10})
        self.assertTrue(result)
        self.assertEqual(entity.value, 10)
        logger.info("Default method executed successfully")

    def test_execute_type_specific(self) -> None:
        entity = TestEntity(name="test_obj")
        result = self.super_instance.execute(entity, {"value": 10})
        self.assertTrue(result)
        self.assertEqual(entity.value, 20)  # _configure_testentity doubles the value
        logger.info("Type-specific method executed successfully")

    def test_register_method(self) -> None:
        def custom_method(obj: TestEntity, attrs: Dict[str, Any]) -> bool:
            obj.value = attrs.get("value", 0) + 1
            return True
        self.super_instance.register_method(TestEntity, "custom", custom_method)
        entity = TestEntity(name="test_obj")
        result = self.super_instance.execute(entity, {"method": "custom", "value": 5})
        self.assertTrue(result)
        self.assertEqual(entity.value, 6)
        logger.info("Custom method registered and executed")

    def test_invalid_method(self) -> None:
        entity = TestEntity(name="test_obj")
        with self.assertRaises(ValueError):
            self.super_instance.execute(entity, {"method": "unknown"})
        logger.info("Invalid method handled correctly")

if __name__ == "__main__":
    unittest.main()