import unittest
from typing import Dict, Any, Optional, List, Union
from common.super.manipulator import Manipulator
from common.super.super import Super
from common.base.baseentity import BaseEntity
from common.utils.logging_setup import logger


class Observation(BaseEntity):
    value: int

class TestConfigurator(Super):
    def _configure_observation(self, obj: Observation, attrs: Dict[str, Any]) -> bool:
        obj.set(attrs)
        return True

    def _configure_list(self, obj: List, attrs: Dict[str, Any]) -> bool:
        if "append" in attrs:
            obj.append(attrs["append"])
            return True
        return False

    def execute(self, obj: Any, attributes: Dict[str, Any] = None, method: str = None) -> Dict[str, Any]:
        if attributes is None:
            attributes = {}
        obj_type_name = type(obj).__name__.lower()
        method_name = f"_configure_{obj_type_name}"
        method = getattr(self, method_name, None)
        if callable(method):
            result = method(obj, attributes)
            return {"status": True, "object": obj, "method": method_name, "result": result}
        logger.error(f"No configuration method found for {obj_type_name}")
        return {"status": False, "object": obj, "method": None, "result": None, "error": "No configuration method found"}

class TestManipulator(unittest.TestCase):
    def setUp(self) -> None:
        """Set up before each test."""
        self.manipulator = Manipulator(base_classes=[list, Observation])
        self.configurator = TestConfigurator(self.manipulator)
        self.manipulator.register_operation("configure", self.configurator)
        self.obs = Observation(name="TEST_OBS", value=42)
        logger.info("Set up TestManipulator")

    def test_initialization(self) -> None:
        """Test Manipulator initialization."""
        manip = Manipulator(managing_object=self.obs, base_classes=[list])
        self.assertEqual(manip.get_managing_object(), self.obs)
        self.assertEqual(len(manip._base_classes), 2)
        self.assertEqual(manip._base_classes[0], list)
        self.assertEqual(len(manip._operations), 0)
        logger.info("Manipulator initialization tested successfully")

    def test_set_managing_object(self) -> None:
        """Test setting the managing object."""
        manip = Manipulator()
        manip.set_managing_object(self.obs)
        self.assertEqual(manip.get_managing_object(), self.obs)
        logger.info("Set managing object tested successfully")

    def test_register_operation_valid(self) -> None:
        """Test registering a valid operation."""
        manip = Manipulator()
        config = TestConfigurator(manip)
        manip.register_operation("configure", config)
        self.assertIn("configure", manip._operations)
        self.assertEqual(manip._operations["configure"], config)
        self.assertEqual(config._operation, "configure")
        self.assertIn(TestConfigurator, manip._registry)
        logger.info("Valid operation registration tested successfully")

    def test_register_operation_invalid(self) -> None:
        """Test registering an operation with invalid arguments."""
        manip = Manipulator()
        with self.assertRaises(ValueError):
            manip.register_operation("", TestConfigurator(manip))
        with self.assertRaises(ValueError):
            manip.register_operation("invalid", object())
        logger.info("Invalid operation registration tested successfully")

    def test_get_methods_for_type(self) -> None:
        """Test retrieving methods for a type."""
        methods = self.manipulator.get_methods_for_type(list)
        self.assertIn("append", methods)
        methods = self.manipulator.get_methods_for_type(Observation)
        self.assertIn("set", methods)
        with self.assertRaises(ValueError):
            self.manipulator.get_methods_for_type(str)
        logger.info("Get methods for type tested successfully")

    def test_update_registry(self) -> None:
        """Test updating the method registry."""
        manip = Manipulator(base_classes=[list])
        manip.update_registry(additional_classes=[Observation])
        self.assertIn(list, manip._registry)
        self.assertIn(Observation, manip._registry)
        manip.update_registry(clear_operations=True)
        self.assertEqual(len(manip._operations), 0)
        logger.info("Registry update tested successfully")

    def test_process_single_request_success(self) -> None:
        """Test successful processing of a single request."""
        request = {
            "operation": "configure",
            "obj": self.obs,
            "attributes": {"value": 100}
        }
        result = self.manipulator.process_request(request)
        self.assertTrue(result["status"])
        self.assertEqual(result["object"], self.obs)
        self.assertEqual(result["method"], "_configure_observation")
        self.assertTrue(result["result"])
        self.assertEqual(self.obs.value, 100)
        self.assertNotIn("error", result)

        test_list = []
        request = {
            "operation": "configure",
            "obj": test_list,
            "attributes": {"append": 42}
        }
        result = self.manipulator.process_request(request)
        self.assertTrue(result["status"])
        self.assertEqual(result["object"], test_list)
        self.assertEqual(result["method"], "_configure_list")
        self.assertTrue(result["result"])
        self.assertEqual(test_list, [42])
        self.assertNotIn("error", result)
        logger.info("Single request success tested successfully")

    def test_process_single_request_with_managing_object(self) -> None:
        """Test processing a request with managing_object."""
        manip = Manipulator(managing_object=self.obs)
        manip.register_operation("configure", TestConfigurator(manip))
        request = {"operation": "configure", "attributes": {"value": 200}}
        result = manip.process_request(request)
        self.assertTrue(result["status"])
        self.assertEqual(result["object"], self.obs)
        self.assertEqual(result["method"], "_configure_observation")
        self.assertTrue(result["result"])
        self.assertEqual(self.obs.value, 200)
        self.assertNotIn("error", result)
        logger.info("Single request with managing object tested successfully")

    def test_process_single_request_missing_operation(self) -> None:
        """Test processing a request without an operation."""
        request = {"obj": self.obs, "attributes": {"value": 300}}
        result = self.manipulator.process_request(request)
        self.assertFalse(result["status"])
        self.assertEqual(result["object"], self.obs)
        self.assertIsNone(result["method"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "No operation specified in request")
        self.assertEqual(self.obs.value, 42)
        logger.info("Missing operation in request tested successfully")

    def test_process_single_request_invalid_operation(self) -> None:
        """Test processing a request with an invalid operation."""
        request = {"operation": "invalid", "obj": self.obs, "attributes": {"value": 300}}
        result = self.manipulator.process_request(request)
        self.assertFalse(result["status"])
        self.assertEqual(result["object"], self.obs)
        self.assertIsNone(result["method"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "Operation 'invalid' not registered")
        self.assertEqual(self.obs.value, 42)
        logger.info("Invalid operation in request tested successfully")

    def test_process_single_request_invalid_attributes(self) -> None:
        """Test processing a request with invalid attributes."""
        request = {"operation": "configure", "obj": self.obs, "attributes": "not_a_dict"}
        result = self.manipulator.process_request(request)
        self.assertFalse(result["status"])
        self.assertEqual(result["object"], self.obs)
        self.assertIsNone(result["method"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "Invalid attributes type")
        self.assertEqual(self.obs.value, 42)
        logger.info("Invalid attributes in request tested successfully")

    def test_process_sequence_request(self) -> None:
        """Test processing a sequence of requests."""
        test_list = []
        request = {
            "req1": {"operation": "configure", "obj": self.obs, "attributes": {"value": 500}},
            "req2": {"operation": "configure", "obj": test_list, "attributes": {"append": 1}},
            "req3": {"operation": "configure", "obj": test_list, "attributes": {"append": 2}}
        }
        results = self.manipulator.process_request(request)
        self.assertEqual(len(results), 3)
        self.assertTrue(results["req1"]["status"])
        self.assertEqual(results["req1"]["object"], self.obs)
        self.assertEqual(results["req1"]["method"], "_configure_observation")
        self.assertTrue(results["req1"]["result"])
        self.assertNotIn("error", results["req1"])
        self.assertTrue(results["req2"]["status"])
        self.assertEqual(results["req2"]["object"], test_list)
        self.assertEqual(results["req2"]["method"], "_configure_list")
        self.assertTrue(results["req2"]["result"])
        self.assertNotIn("error", results["req2"])
        self.assertTrue(results["req3"]["status"])
        self.assertEqual(results["req3"]["object"], test_list)
        self.assertEqual(results["req3"]["method"], "_configure_list")
        self.assertTrue(results["req3"]["result"])
        self.assertNotIn("error", results["req3"])
        self.assertEqual(self.obs.value, 500)
        self.assertEqual(test_list, [1, 2])
        logger.info("Sequence request tested successfully")

    def test_process_sequence_request_with_errors(self) -> None:
        """Test processing a sequence of requests with errors."""
        request = {
            "req1": {"operation": "configure", "obj": self.obs, "attributes": {"value": 600}},
            "req2": {"operation": "invalid", "obj": self.obs, "attributes": {"value": 700}},
            "req3": {"operation": "configure", "obj": self.obs, "attributes": "not_a_dict"}
        }
        results = self.manipulator.process_request(request)
        self.assertEqual(len(results), 3)
        self.assertTrue(results["req1"]["status"])
        self.assertEqual(results["req1"]["object"], self.obs)
        self.assertEqual(results["req1"]["method"], "_configure_observation")
        self.assertTrue(results["req1"]["result"])
        self.assertNotIn("error", results["req1"])
        self.assertFalse(results["req2"]["status"])
        self.assertEqual(results["req2"]["object"], self.obs)
        self.assertIsNone(results["req2"]["method"])
        self.assertIsNone(results["req2"]["result"])
        self.assertEqual(results["req2"]["error"], "Operation 'invalid' not registered")
        self.assertFalse(results["req3"]["status"])
        self.assertEqual(results["req3"]["object"], self.obs)
        self.assertIsNone(results["req3"]["method"])
        self.assertIsNone(results["req3"]["result"])
        self.assertEqual(results["req3"]["error"], "Invalid attributes type")
        self.assertEqual(self.obs.value, 600)
        logger.info("Sequence request with errors tested successfully")

    def test_process_request_invalid_type(self) -> None:
        """Test processing a request with an invalid type."""
        with self.assertRaises(TypeError):
            self.manipulator.process_request("not_a_dict")
        logger.info("Invalid request type tested successfully")

    def test_process_request_no_object(self) -> None:
        """Test processing a request without an object or managing_object."""
        manip = Manipulator()
        manip.register_operation("configure", TestConfigurator(manip))
        request = {"operation": "configure", "attributes": {"value": 42}}
        result = manip.process_request(request)
        self.assertFalse(result["status"])
        self.assertIsNone(result["object"])
        self.assertIsNone(result["method"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "No request object or managing object provided")
        logger.info("No object in request tested successfully")

    def test_get_supported_operations(self) -> None:
        """Test retrieving supported operations."""
        ops = self.manipulator.get_supported_operations()
        self.assertEqual(ops, ["configure"])
        manip = Manipulator()
        self.assertEqual(manip.get_supported_operations(), [])
        logger.info("Get supported operations tested successfully")

    def test_method_registry_caching(self) -> None:
        """Test method registry caching."""
        manip = Manipulator(base_classes=[list])
        registry1 = manip._get_method_registry()
        registry2 = manip._get_method_registry()
        self.assertIs(registry1, registry2)
        manip.update_registry(additional_classes=[Observation])
        registry3 = manip._get_method_registry()
        self.assertIsNot(registry1, registry3)
        self.assertIn(Observation, registry3)
        logger.info("Method registry caching tested successfully")

if __name__ == "__main__":
    unittest.main()