import unittest
from unittest.mock import Mock, patch
from typing import Dict, Any, Union
from common.super.super import Super
from common.super.manipulator import Manipulator
from common.utils.logging_setup import logger

class TestSuper(unittest.TestCase):
    def setUp(self):
        """Подготовка перед каждым тестом."""
        self.manipulator = Mock(spec=Manipulator)
        self.manipulator.get_methods_for_type.return_value = {}

    def test_init_basic(self):
        """Тест базовой инициализации Super."""
        super_instance = Super()
        self.assertIsNone(super_instance._manipulator)
        self.assertEqual(super_instance._methods, {})
        self.assertEqual(super_instance._method_cache, {})

    def test_init_with_manipulator(self):
        """Тест инициализации с Manipulator."""
        super_instance = Super(manipulator=self.manipulator)
        self.assertEqual(super_instance._manipulator, self.manipulator)
        self.assertEqual(super_instance._methods, {})
        self.assertEqual(super_instance._method_cache, {})

    def test_init_with_methods(self):
        """Тест инициализации с кастомным реестром методов."""
        methods = {list: {"append": lambda x: x.append(1)}}
        super_instance = Super(methods=methods)
        self.assertIsNone(super_instance._manipulator)
        self.assertEqual(super_instance._methods, methods)
        self.assertEqual(super_instance._method_cache, {})

    def test_get_methods_from_methods(self):
        """Тест получения методов из _methods."""
        methods = {list: {"append": lambda x: x.append(1)}}
        super_instance = Super(methods=methods)
        result = super_instance._get_methods(list)
        self.assertEqual(result, methods[list])

    def test_get_methods_from_manipulator(self):
        """Тест получения методов из Manipulator."""
        self.manipulator.get_methods_for_type.return_value = {"append": lambda x: x.append(1)}
        super_instance = Super(manipulator=self.manipulator)
        result = super_instance._get_methods(list)
        self.assertTrue(callable(result["append"]))
        test_list = []
        result["append"](test_list)
        self.assertEqual(test_list, [1])

    def test_get_methods_raises_value_error(self):
        """Тест выброса исключения при отсутствии методов."""
        super_instance = Super()
        with self.assertRaises(ValueError) as cm:
            super_instance._get_methods(list)
        self.assertEqual(str(cm.exception), "No methods available for list")

    def test_do_nested_valid_index(self):
        """Тест вложенной операции с корректным индексом."""
        class TestSuper(Super):
            def _test_method(self, obj, attrs):
                return obj + attrs.get("value", 0)

        super_instance = TestSuper()
        obj = [1, 2, 3]
        attributes = {"index": 1, "value": 10}
        result = super_instance._do_nested(
            obj, attributes, "index", lambda i: obj[i], super_instance._test_method
        )
        self.assertEqual(result, 12)  # 2 + 10

    def test_do_nested_invalid_index(self):
        """Тест вложенной операции с некорректным индексом."""
        class TestSuper(Super):
            def _default_nested_result(self):
                return {"success": False, "error": "Invalid index"}

        super_instance = TestSuper()
        obj = [1, 2, 3]
        attributes = {"index": 5, "value": 10}
        result = super_instance._do_nested(
            obj, attributes, "index", lambda i: obj[i], lambda x, y: x
        )
        self.assertEqual(result, {"success": False, "error": "Invalid index"})

    def test_do_nested_no_index(self):
        """Тест вложенной операции без индекса."""
        class TestSuper(Super):
            def _default_nested_result(self):
                return {"success": False, "error": "No index"}

        super_instance = TestSuper()
        obj = [1, 2, 3]
        attributes = {"value": 10}
        result = super_instance._do_nested(
            obj, attributes, "index", lambda i: obj[i], lambda x, y: x
        )
        self.assertEqual(result, {"success": False, "error": "No index"})

    def test_validate_and_apply_method_valid(self):
        """Тест валидации и применения метода с корректными аргументами."""
        class TestSuper(Super):
            def test_method(self, obj, value):
                return obj + value

        super_instance = TestSuper()
        valid_methods = {"test_method": super_instance.test_method}
        result = super_instance._validate_and_apply_method(
            obj=5, method_name="test_method", method_args={"value": 10}, valid_methods=valid_methods
        )
        self.assertTrue(result)

    def test_validate_and_apply_method_invalid_method(self):
        """Тест валидации с некорректным методом."""
        super_instance = Super()
        valid_methods = {}
        result = super_instance._validate_and_apply_method(
            obj=5, method_name="invalid_method", method_args={"value": 10}, valid_methods=valid_methods
        )
        self.assertIsNone(result)

    def test_validate_and_apply_method_invalid_args_type(self):
        """Тест валидации с некорректным типом аргументов."""
        class TestSuper(Super):
            def test_method(self, obj, value):
                return obj + value

        super_instance = TestSuper()
        valid_methods = {"test_method": super_instance.test_method}
        result = super_instance._validate_and_apply_method(
            obj=5, method_name="test_method", method_args="not_a_dict", valid_methods=valid_methods
        )
        self.assertIsNone(result)

    def test_validate_and_apply_method_invalid_args_keys(self):
        """Тест валидации с некорректными ключами аргументов."""
        class TestSuper(Super):
            def test_method(self, obj, value):
                return obj + value

        super_instance = TestSuper()
        valid_methods = {"test_method": super_instance.test_method}
        result = super_instance._validate_and_apply_method(
            obj=5, method_name="test_method", method_args={"wrong_key": 10}, valid_methods=valid_methods
        )
        self.assertIsNone(result)

    def test_register_method(self):
        """Тест регистрации кастомного метода."""
        super_instance = Super()
        mock_method = Mock()
        super_instance.register_method(list, "append", mock_method)
        self.assertIn(list, super_instance._methods)
        self.assertEqual(super_instance._methods[list]["append"], mock_method)
        self.assertEqual(super_instance._method_cache, {})  # Кэш очищен

    def test_execute_explicit_method(self):
        """Тест выполнения с явным методом."""
        class TestSuper(Super):
            def explicit_method(self, obj, attrs):
                return obj + attrs.get("value", 0)

        super_instance = TestSuper()
        super_instance._operation = "test"
        result = super_instance.execute(obj=5, attributes={"value": 10}, method="explicit_method")
        self.assertEqual(result, 15)
        # Проверка кэширования
        cached_result = super_instance.execute(obj=5, attributes={"value": 10}, method="explicit_method")
        self.assertEqual(cached_result, 15)

    def test_execute_method_from_attributes(self):
        """Тест выполнения метода из attributes."""
        class TestSuper(Super):
            def custom_method(self, obj, attrs):
                return obj + attrs.get("value", 0)

        super_instance = TestSuper()
        super_instance._operation = "test"
        result = super_instance.execute(obj=5, attributes={"method": "custom_method", "value": 10})
        self.assertEqual(result, 15)

    def test_execute_prefixed_method(self):
        """Тест выполнения метода с префиксом операции."""
        class TestSuper(Super):
            def _test_add(self, obj, attrs):
                return obj + attrs.get("value", 0)

        super_instance = TestSuper()
        super_instance._operation = "test"
        result = super_instance.execute(obj=5, attributes={"method": "add", "value": 10})
        self.assertEqual(result, 15)

    def test_execute_type_specific_method(self):
        """Тест выполнения метода для конкретного типа."""
        class TestSuper(Super):
            def _test_int(self, obj, attrs):
                return obj + attrs.get("value", 0)

        super_instance = TestSuper()
        super_instance._operation = "test"
        result = super_instance.execute(obj=5, attributes={"value": 10})
        self.assertEqual(result, 15)

    def test_execute_default_method(self):
        """Тест выполнения метода по умолчанию."""
        class TestSuper(Super):
            def _test(self, obj, attrs):
                return obj + attrs.get("value", 0)

        super_instance = TestSuper()
        super_instance._operation = "test"
        result = super_instance.execute(obj=5, attributes={"value": 10})
        self.assertEqual(result, 15)

    def test_execute_nested_attributes(self):
        """Тест выполнения с вложенными атрибутами."""
        class TestSuper(Super):
            def custom_method(self, obj, attrs):
                return obj + attrs.get("value", 0)

        super_instance = TestSuper()
        super_instance._operation = "test"
        result = super_instance.execute(obj=5, attributes={"attributes": {"method": "custom_method", "value": 10}})
        self.assertEqual(result, 15)

    def test_execute_no_method_found(self):
        """Тест выполнения, когда метод не найден."""
        class TestSuper(Super):
            def _default_result(self):
                return {"success": False, "error": "No method"}

        super_instance = TestSuper()
        super_instance._operation = "test"
        result = super_instance.execute(obj=5, attributes={"value": 10})
        self.assertEqual(result, {"success": False, "error": "No method"})

    def test_execute_value_error(self):
        """Тест обработки ValueError в execute."""
        class TestSuper(Super):
            def _test(self, obj, attrs):
                raise ValueError("Test error")

        super_instance = TestSuper()
        super_instance._operation = "test"
        result = super_instance.execute(obj=5, attributes={"value": 10})
        self.assertEqual(result, {"success": False, "error": "Operation not executed"})

    def test_execute_unexpected_error(self):
        """Тест обработки неожиданной ошибки в execute."""
        class TestSuper(Super):
            def _test(self, obj, attrs):
                raise Exception("Unexpected error")

        super_instance = TestSuper()
        super_instance._operation = "test"
        result = super_instance.execute(obj=5, attributes={"value": 10})
        self.assertEqual(result, {"success": False, "error": "Operation not executed"})

    def test_execute_caching(self):
        """Тест работы кэширования в execute."""
        class TestSuper(Super):
            def _test(self, obj, attrs):
                return obj + attrs.get("value", 0)

        super_instance = TestSuper()
        super_instance._operation = "test"
        result1 = super_instance.execute(obj=5, attributes={"value": 10})
        self.assertEqual(result1, 15)
        # Проверяем, что результат берется из кэша
        with patch.object(TestSuper, "_test") as mock_method:
            result2 = super_instance.execute(obj=5, attributes={"value": 10})
            self.assertEqual(result2, 15)
            mock_method.assert_not_called()

    def test_integration_with_manipulator(self):
        """Тест интеграции с Manipulator."""
        class TestSuper(Super):
            def _test(self, obj, attrs):
                return obj + attrs.get("value", 0)

        manip = Manipulator()
        super_instance = TestSuper(manipulator=manip)
        manip.register_operation("test", super_instance)
        request = {"operation": "test", "obj": 5, "attributes": {"value": 10}}
        result = manip.process_request(request)
        self.assertEqual(result, 15)

    def test_default_result(self):
        """Тест метода _default_result."""
        super_instance = Super()
        result = super_instance._default_result()
        self.assertEqual(result, {"success": False, "error": "Operation not executed"})

    def test_default_nested_result(self):
        """Тест метода _default_nested_result."""
        super_instance = Super()
        result = super_instance._default_nested_result()
        self.assertEqual(result, {"success": False, "error": "Operation not executed"})

    def test_repr(self):
        """Тест метода __repr__."""
        super_instance = Super()
        self.assertEqual(repr(super_instance), "Super()")

if __name__ == "__main__":
    unittest.main()