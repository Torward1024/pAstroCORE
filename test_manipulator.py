import unittest
from typing import Dict, Any, Optional, List
from common.super.manipulator import Manipulator
from common.super.super import Super
from common.base.baseentity import BaseEntity
from common.utils.logging_setup import logger

# Тестовые классы для проверки
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

    def execute(self, obj: Any, attributes: Dict[str, Any] = None, method: str = None) -> bool:
        """Execute the configuration operation."""
        if attributes is None:
            attributes = {}
        obj_type_name = type(obj).__name__.lower()
        method_name = f"_configure_{obj_type_name}"
        method = getattr(self, method_name, None)
        if callable(method):
            return method(obj, attributes)
        logger.error(f"No configuration method found for {obj_type_name}")
        return False

class TestManipulator(unittest.TestCase):
    def setUp(self) -> None:
        """Подготовка перед каждым тестом."""
        self.manipulator = Manipulator(base_classes=[list, Observation])
        self.configurator = TestConfigurator(self.manipulator)
        self.manipulator.register_operation("configure", self.configurator)
        self.obs = Observation(name="TEST_OBS", value=42)
        logger.info("Set up TestManipulator")

    def test_initialization(self) -> None:
        """Тест инициализации Manipulator."""
        manip = Manipulator(managing_object=self.obs, base_classes=[list])
        self.assertEqual(manip.get_managing_object(), self.obs)
        self.assertEqual(len(manip._base_classes), 2)
        self.assertEqual(manip._base_classes[0], list)
        self.assertEqual(len(manip._operations), 0)
        logger.info("Manipulator initialization tested successfully")

    def test_set_managing_object(self) -> None:
        """Тест установки управляющего объекта."""
        manip = Manipulator()
        manip.set_managing_object(self.obs)
        self.assertEqual(manip.get_managing_object(), self.obs)
        logger.info("Set managing object tested successfully")

    def test_register_operation_valid(self) -> None:
        """Тест регистрации валидной операции."""
        manip = Manipulator()
        config = TestConfigurator(manip)
        manip.register_operation("configure", config)
        self.assertIn("configure", manip._operations)
        self.assertEqual(manip._operations["configure"], config)
        self.assertEqual(config._operation, "configure")
        self.assertIn(TestConfigurator, manip._registry)
        logger.info("Valid operation registration tested successfully")

    def test_register_operation_invalid(self) -> None:
        """Тест регистрации операции с невалидными аргументами."""
        manip = Manipulator()
        with self.assertRaises(ValueError):
            manip.register_operation("", TestConfigurator(manip))  # Пустое имя операции
        with self.assertRaises(ValueError):
            manip.register_operation("invalid", object())  # Нет метода execute
        logger.info("Invalid operation registration tested successfully")

    def test_get_methods_for_type(self) -> None:
        """Тест получения методов для типа."""
        methods = self.manipulator.get_methods_for_type(list)
        self.assertIn("append", methods)
        methods = self.manipulator.get_methods_for_type(Observation)
        self.assertIn("set", methods)
        with self.assertRaises(ValueError):
            self.manipulator.get_methods_for_type(str)  # Не зарегистрированный тип
        logger.info("Get methods for type tested successfully")

    def test_update_registry(self) -> None:
        """Тест обновления реестра методов."""
        manip = Manipulator(base_classes=[list])
        manip.update_registry(additional_classes=[Observation])
        self.assertIn(list, manip._registry)
        self.assertIn(Observation, manip._registry)
        manip.update_registry(clear_operations=True)
        self.assertEqual(len(manip._operations), 0)
        logger.info("Registry update tested successfully")

    def test_process_single_request_success(self) -> None:
        """Тест успешной обработки одиночного запроса."""
        # Тест с объектом Observation
        request = {
            "operation": "configure",
            "obj": self.obs,
            "attributes": {"value": 100}
        }
        result = self.manipulator.process_request(request)
        self.assertTrue(result)
        self.assertEqual(self.obs.value, 100)

        # Тест с объектом list
        test_list = []
        request = {
            "operation": "configure",
            "obj": test_list,
            "attributes": {"append": 42}
        }
        result = self.manipulator.process_request(request)
        self.assertTrue(result)
        self.assertEqual(test_list, [42])
        logger.info("Single request success tested successfully")

    def test_process_single_request_with_managing_object(self) -> None:
        """Тест обработки запроса с использованием managing_object."""
        manip = Manipulator(managing_object=self.obs)
        manip.register_operation("configure", TestConfigurator(manip))
        request = {"operation": "configure", "attributes": {"value": 200}}
        result = manip.process_request(request)
        self.assertTrue(result["success"])
        self.assertEqual(self.obs.value, 200)
        logger.info("Single request with managing object tested successfully")

    def test_process_single_request_missing_operation(self) -> None:
        """Тест обработки запроса без указания операции."""
        request = {"obj": self.obs, "attributes": {"value": 300}}
        result = self.manipulator.process_request(request)
        self.assertFalse(result["success"])
        self.assertEqual(self.obs.value, 42)  # Значение не изменилось
        logger.info("Missing operation in request tested successfully")

    def test_process_single_request_invalid_operation(self) -> None:
        """Тест обработки запроса с несуществующей операцией."""
        request = {"operation": "invalid", "obj": self.obs, "attributes": {"value": 300}}
        result = self.manipulator.process_request(request)
        self.assertFalse(result["success"])
        self.assertEqual(self.obs.value, 42)
        logger.info("Invalid operation in request tested successfully")

    def test_process_single_request_invalid_attributes(self) -> None:
        """Тест обработки запроса с невалидными атрибутами."""
        request = {"operation": "configure", "obj": self.obs, "attributes": "not_a_dict"}
        result = self.manipulator.process_request(request)
        self.assertFalse(result["success"])
        self.assertEqual(self.obs.value, 42)
        logger.info("Invalid attributes in request tested successfully")

    def test_process_sequence_request(self) -> None:
        """Тест обработки последовательности запросов."""
        test_list = []
        request = {
            "req1": {"operation": "configure", "obj": self.obs, "attributes": {"value": 500}},
            "req2": {"operation": "configure", "obj": test_list, "attributes": {"append": 1}},
            "req3": {"operation": "configure", "obj": test_list, "attributes": {"append": 2}}
        }
        results = self.manipulator.process_request(request)
        self.assertEqual(len(results), 3)
        self.assertTrue(results["req1"]["success"])
        self.assertTrue(results["req2"]["success"])
        self.assertTrue(results["req3"]["success"])
        self.assertEqual(self.obs.value, 500)
        self.assertEqual(test_list, [1, 2])
        logger.info("Sequence request tested successfully")

    def test_process_sequence_request_with_errors(self) -> None:
        """Тест обработки последовательности запросов с ошибками."""
        request = {
            "req1": {"operation": "configure", "obj": self.obs, "attributes": {"value": 600}},
            "req2": {"operation": "invalid", "obj": self.obs, "attributes": {"value": 700}},
            "req3": {"operation": "configure", "obj": self.obs, "attributes": "not_a_dict"}  # Добавлен obj
        }
        results = self.manipulator.process_request(request)
        self.assertEqual(len(results), 3)
        self.assertTrue(results["req1"]["success"])
        self.assertFalse(results["req2"]["success"])
        self.assertFalse(results["req3"]["success"])
        self.assertEqual(self.obs.value, 600)
        logger.info("Sequence request with errors tested successfully")

    def test_process_request_invalid_type(self) -> None:
        """Тест обработки запроса с невалидным типом запроса."""
        with self.assertRaises(TypeError):
            self.manipulator.process_request("not_a_dict")
        logger.info("Invalid request type tested successfully")

    def test_process_request_no_object(self) -> None:
        """Тест обработки запроса без объекта и managing_object."""
        manip = Manipulator()
        manip.register_operation("configure", TestConfigurator(manip))
        request = {"operation": "configure", "attributes": {"value": 42}}
        with self.assertRaises(ValueError):
            manip.process_request(request)
        logger.info("No object in request tested successfully")

    def test_get_supported_operations(self) -> None:
        """Тест получения списка поддерживаемых операций."""
        ops = self.manipulator.get_supported_operations()
        self.assertEqual(ops, ["configure"])
        manip = Manipulator()
        self.assertEqual(manip.get_supported_operations(), [])
        logger.info("Get supported operations tested successfully")

    def test_method_registry_caching(self) -> None:
        """Тест кэширования реестра методов."""
        manip = Manipulator(base_classes=[list])
        registry1 = manip._get_method_registry()
        registry2 = manip._get_method_registry()
        self.assertIs(registry1, registry2)  # Должны быть идентичны из-за кэширования
        manip.update_registry(additional_classes=[Observation])
        registry3 = manip._get_method_registry()
        self.assertIsNot(registry1, registry3)  # После обновления кэш сброшен
        self.assertIn(Observation, registry3)
        logger.info("Method registry caching tested successfully")

if __name__ == "__main__":
    unittest.main()