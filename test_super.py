import unittest
from unittest.mock import Mock, patch
from typing import Dict, Any
from common.super.super import Super
from common.super.manipulator import Manipulator
from common.utils.logging_setup import logger
from collections import OrderedDict


class TestSuper(unittest.TestCase):
    def setUp(self):
        """Set up before each test."""
        self.manipulator = Mock(spec=Manipulator)
        self.manipulator.get_methods_for_type.return_value = {}

    def test_init_basic(self):
        """Test basic initialization of Super."""
        super_instance = Super()
        self.assertIsNone(super_instance._manipulator)
        self.assertEqual(super_instance._methods, {})
        self.assertIsInstance(super_instance._method_cache, OrderedDict)

    def test_init_with_manipulator(self):
        """Test initialization with Manipulator."""
        super_instance = Super(manipulator=self.manipulator)
        self.assertEqual(super_instance._manipulator, self.manipulator)
        self.assertEqual(super_instance._methods, {})
        self.assertIsInstance(super_instance._method_cache, OrderedDict)

    def test_init_with_methods(self):
        """Test initialization with custom method registry."""
        methods = {list: {"append": lambda x: x.append(1)}}
        super_instance = Super(methods=methods)
        self.assertIsNone(super_instance._manipulator)
        self.assertEqual(super_instance._methods, methods)
        self.assertIsInstance(super_instance._method_cache, OrderedDict)

    def test_get_methods_from_methods(self):
        """Test retrieving methods from _methods."""
        methods = {list: {"append": lambda x: x.append(1)}}
        super_instance = Super(methods=methods)
        result = super_instance._get_methods(list)
        self.assertEqual(result, methods[list])

    def test_get_methods_from_manipulator(self):
        """Test retrieving methods from Manipulator."""
        self.manipulator.get_methods_for_type.return_value = {"append": lambda x: x.append(1)}
        super_instance = Super(manipulator=self.manipulator)
        result = super_instance._get_methods(list)
        self.assertTrue(callable(result["append"]))
        test_list = []
        result["append"](test_list)
        self.assertEqual(test_list, [1])

    def test_get_methods_raises_value_error(self):
        """Test raising ValueError when no methods are available."""
        super_instance = Super()
        with self.assertRaises(ValueError) as cm:
            super_instance._get_methods(list)
        self.assertEqual(str(cm.exception), "No methods available for list")

    def test_build_response_success(self):
        """Test _build_response for successful operation."""
        super_instance = Super()
        obj = 5
        result = super_instance._build_response(
            obj=obj, status=True, method="test_method", result=15
        )
        self.assertEqual(
            result,
            {
                "status": True,
                "object": obj,
                "method": "test_method",
                "result": 15,
            },
        )
        self.assertNotIn("error", result)

    def test_build_response_failure(self):
        """Test _build_response for failed operation with error."""
        super_instance = Super()
        obj = 5
        result = super_instance._build_response(
            obj=obj, status=False, method=None, result=None, error="Test error"
        )
        self.assertEqual(
            result,
            {
                "status": False,
                "object": obj,
                "method": None,
                "result": None,
                "error": "Test error",
            },
        )

    def test_do_nested_valid_index(self):
        """Test nested operation with valid index."""
        class TestSuper(Super):
            def _test_method(self, obj, attrs):
                return obj + attrs.get("value", 0)

        super_instance = TestSuper()
        obj = [1, 2, 3]
        attributes = {"index": 1, "value": 10}
        result = super_instance._do_nested(
            obj, attributes, "index", lambda i: obj[i], super_instance._test_method
        )
        self.assertTrue(result["status"])
        self.assertEqual(result["object"], 2)
        self.assertEqual(result["method"], "_test_method")
        self.assertEqual(result["result"], 12)
        self.assertNotIn("error", result)

    def test_do_nested_invalid_index(self):
        """Test nested operation with invalid index."""
        class TestSuper(Super):
            pass

        super_instance = TestSuper()
        obj = [1, 2, 3]
        attributes = {"index": 5, "value": 10}
        result = super_instance._do_nested(
            obj, attributes, "index", lambda i: obj[i], lambda x, y: x
        )
        self.assertFalse(result["status"])
        self.assertEqual(result["object"], obj)
        self.assertIsNone(result["method"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "Operation not executed")

    def test_do_nested_no_index(self):
        """Test nested operation without index."""
        class TestSuper(Super):
            pass

        super_instance = TestSuper()
        obj = [1, 2, 3]
        attributes = {"value": 10}
        result = super_instance._do_nested(
            obj, attributes, "index", lambda i: obj[i], lambda x, y: x
        )
        self.assertFalse(result["status"])
        self.assertEqual(result["object"], obj)
        self.assertIsNone(result["method"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "Operation not executed")

    def test_validate_and_apply_method_valid(self):
        """Test validation and application of a valid method."""
        class TestSuper(Super):
            def test_method(self, obj, value):
                return obj + value

        super_instance = TestSuper()
        valid_methods = {"test_method": super_instance.test_method}
        result = super_instance._validate_and_apply_method(
            obj=5, method_name="test_method", method_args={"value": 10}, valid_methods=valid_methods
        )
        self.assertTrue(result["status"])
        self.assertEqual(result["object"], 5)
        self.assertEqual(result["method"], "test_method")
        self.assertEqual(result["result"], 15)
        self.assertNotIn("error", result)

    def test_validate_and_apply_method_invalid_method(self):
        """Test validation with an invalid method."""
        super_instance = Super()
        valid_methods = {}
        result = super_instance._validate_and_apply_method(
            obj=5, method_name="invalid_method", method_args={"value": 10}, valid_methods=valid_methods
        )
        self.assertFalse(result["status"])
        self.assertEqual(result["object"], 5)
        self.assertIsNone(result["method"], None)
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "Method 'invalid_method' not found")

    def test_validate_and_apply_method_invalid_args_type(self):
        """Test validation with invalid argument type."""
        class TestSuper(Super):
            def test_method(self, obj, value):
                return obj + value

        super_instance = TestSuper()
        valid_methods = {"test_method": super_instance.test_method}
        result = super_instance._validate_and_apply_method(
            obj=5, method_name="test_method", method_args="not_a_dict", valid_methods=valid_methods
        )
        self.assertFalse(result["status"])
        self.assertEqual(result["object"], 5)
        self.assertEqual(result["method"], "test_method")
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "Invalid argument type: <class 'str'>")

    def test_validate_and_apply_method_invalid_args_keys(self):
        """Test validation with invalid argument keys."""
        class TestSuper(Super):
            def test_method(self, obj, value):
                return obj + value

        super_instance = TestSuper()
        valid_methods = {"test_method": super_instance.test_method}
        result = super_instance._validate_and_apply_method(
            obj=5, method_name="test_method", method_args={"wrong_key": 10}, valid_methods=valid_methods
        )
        self.assertFalse(result["status"])
        self.assertEqual(result["object"], 5)
        self.assertEqual(result["method"], "test_method")
        self.assertIsNone(result["result"])
        self.assertIn("Invalid arguments", result["error"])

    def test_register_method(self):
        """Test registering a custom method."""
        super_instance = Super()
        mock_method = Mock()
        super_instance.register_method(list, "append", mock_method)
        self.assertIn(list, super_instance._methods)
        self.assertEqual(super_instance._methods[list]["append"], mock_method)
        self.assertEqual(super_instance._method_cache, {})

    def test_execute_explicit_method(self):
        """Test execution with an explicit method."""
        class TestSuper(Super):
            def explicit_method(self, obj, attrs):
                return obj + attrs.get("value", 0)

        super_instance = TestSuper()
        super_instance._operation = "test"
        result = super_instance.execute(obj=5, attributes={"value": 10}, method="explicit_method")
        self.assertTrue(result["status"])
        self.assertEqual(result["object"], 5)
        self.assertEqual(result["method"], "explicit_method")
        self.assertEqual(result["result"], 15)
        self.assertNotIn("error", result)

    def test_execute_method_from_attributes(self):
        """Test execution with method from attributes."""
        class TestSuper(Super):
            def custom_method(self, obj, attrs):
                return obj + attrs.get("value", 0)

        super_instance = TestSuper()
        super_instance._operation = "test"
        result = super_instance.execute(obj=5, attributes={"method": "custom_method", "value": 10})
        self.assertTrue(result["status"])
        self.assertEqual(result["object"], 5)
        self.assertEqual(result["method"], "custom_method")
        self.assertEqual(result["result"], 15)
        self.assertNotIn("error", result)

    def test_execute_prefixed_method(self):
        """Test execution with prefixed method."""
        class TestSuper(Super):
            def _test_add(self, obj, attrs):
                return obj + attrs.get("value", 0)

        super_instance = TestSuper()
        super_instance._operation = "test"
        result = super_instance.execute(obj=5, attributes={"method": "add", "value": 10})
        self.assertTrue(result["status"])
        self.assertEqual(result["object"], 5)
        self.assertEqual(result["method"], "_test_add")
        self.assertEqual(result["result"], 15)
        self.assertNotIn("error", result)

    def test_execute_type_specific_method(self):
        """Test execution with type-specific method."""
        class TestSuper(Super):
            def _test_int(self, obj, attrs):
                return obj + attrs.get("value", 0)

        super_instance = TestSuper()
        super_instance._operation = "test"
        result = super_instance.execute(obj=5, attributes={"value": 10})
        self.assertTrue(result["status"])
        self.assertEqual(result["object"], 5)
        self.assertEqual(result["method"], "_test_int")
        self.assertEqual(result["result"], 15)
        self.assertNotIn("error", result)

    def test_execute_default_method(self):
        """Test execution with default method."""
        class TestSuper(Super):
            def _test(self, obj, attrs):
                return obj + attrs.get("value", 0)

        super_instance = TestSuper()
        super_instance._operation = "test"
        result = super_instance.execute(obj=5, attributes={"value": 10})
        self.assertTrue(result["status"])
        self.assertEqual(result["object"], 5)
        self.assertEqual(result["method"], "_test")
        self.assertEqual(result["result"], 15)
        self.assertNotIn("error", result)

    def test_execute_nested_attributes(self):
        """Test execution with nested attributes."""
        class TestSuper(Super):
            def custom_method(self, obj, attrs):
                return obj + attrs.get("value", 0)

        super_instance = TestSuper()
        super_instance._operation = "test"
        result = super_instance.execute(obj=5, attributes={"attributes": {"method": "custom_method", "value": 10}})
        self.assertTrue(result["status"])
        self.assertEqual(result["object"], 5)
        self.assertEqual(result["method"], "custom_method")
        self.assertEqual(result["result"], 15)
        self.assertNotIn("error", result)

    def test_execute_no_method_found(self):
        """Test execution when no method is found."""
        super_instance = Super()
        super_instance._operation = "test"
        result = super_instance.execute(obj=5, attributes={"value": 10})
        self.assertFalse(result["status"])
        self.assertEqual(result["object"], 5)
        self.assertIsNone(result["method"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "No suitable method found for operation 'test' and object 'int' in Super")

    def test_execute_value_error(self):
        """Test handling ValueError in execute."""
        class TestSuper(Super):
            def _test(self, obj, attrs):
                raise ValueError("Test error")

        super_instance = TestSuper()
        super_instance._operation = "test"
        result = super_instance.execute(obj=5, attributes={"value": 10})
        self.assertFalse(result["status"])
        self.assertEqual(result["object"], 5)
        self.assertIsNone(result["method"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "Test error")

    def test_execute_unexpected_error(self):
        """Test handling unexpected error in execute."""
        class TestSuper(Super):
            def _test(self, obj, attrs):
                raise Exception("Unexpected error")

        super_instance = TestSuper()
        super_instance._operation = "test"
        result = super_instance.execute(obj=5, attributes={"value": 10})
        self.assertFalse(result["status"])
        self.assertEqual(result["object"], 5)
        self.assertIsNone(result["method"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "Unexpected error")

    def test_execute_caching(self):
        """Test caching behavior in execute."""
        class TestSuper(Super):
            def _test(self, obj, attrs):
                return obj + attrs.get("value", 0)

        super_instance = TestSuper()
        super_instance._operation = "test"
        result1 = super_instance.execute(obj=5, attributes={"value": 10})
        self.assertTrue(result1["status"])
        self.assertEqual(result1["object"], 5)
        self.assertEqual(result1["method"], "_test")
        self.assertEqual(result1["result"], 15)
        self.assertNotIn("error", result1)
        with patch.object(TestSuper, "_test") as mock_method:
            result2 = super_instance.execute(obj=5, attributes={"value": 10})
            self.assertTrue(result2["status"])
            self.assertEqual(result2["object"], 5)
            self.assertEqual(result2["method"], "_test")
            self.assertEqual(result2["result"], 15)
            self.assertNotIn("error", result2)
            mock_method.assert_not_called()

    def test_execute_cache_size_limit(self):
        """Test cache size limit enforcement."""
        class TestSuper(Super):
            def _test(self, obj, attrs):
                return obj + attrs.get("value", 0)

        super_instance = TestSuper(cache_size=1)
        super_instance._operation = "test"
        super_instance.execute(obj=5, attributes={"value": 10})
        super_instance.execute(obj=6, attributes={"value": 20})
        self.assertEqual(len(super_instance._method_cache), 1)

    def test_integration_with_manipulator(self):
        """Test integration with Manipulator."""
        class TestSuper(Super):
            def _test(self, obj, attrs):
                return obj + attrs.get("value", 0)

        manip = Manipulator()
        super_instance = TestSuper(manipulator=manip)
        manip.register_operation("test", super_instance)
        request = {"operation": "test", "obj": 5, "attributes": {"value": 10}}
        result = manip.process_request(request)
        self.assertTrue(result["status"])
        self.assertEqual(result["object"], 5)
        self.assertEqual(result["method"], "_test")
        self.assertEqual(result["result"], 15)
        self.assertNotIn("error", result)

    def test_default_result(self):
        """Test _default_result method."""
        super_instance = Super()
        obj = 5
        result = super_instance._default_result(obj)
        self.assertFalse(result["status"])
        self.assertEqual(result["object"], obj)
        self.assertIsNone(result["method"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "Operation not executed")

    def test_default_nested_result(self):
        """Test _default_nested_result method."""
        super_instance = Super()
        obj = [1, 2, 3]
        result = super_instance._default_nested_result(obj)
        self.assertFalse(result["status"])
        self.assertEqual(result["object"], obj)
        self.assertIsNone(result["method"])
        self.assertIsNone(result["result"])
        self.assertEqual(result["error"], "Operation not executed")

    def test_repr(self):
        """Test __repr__ method."""
        super_instance = Super()
        self.assertEqual(repr(super_instance), "Super()")


if __name__ == "__main__":
    unittest.main()