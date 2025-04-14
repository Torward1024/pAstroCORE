import unittest
from typing import Dict, Any, Optional
from common.super.manipulator import Manipulator
from common.super.super import Super
from common.super.project import Project
from common.base.baseentity import BaseEntity
from common.base.basecontainer import BaseContainer
from common.utils.logging_setup import logger

class Observation(BaseEntity):
    frequency: float
    duration: int
    nested_container: Optional['ObservationContainer'] = None

class ObservationContainer(BaseContainer[Observation]):
    def _validate_item(self, item: Observation) -> None:
        if item.frequency <= 0:
            raise ValueError("Frequency must be positive")
        if item.duration < 0:
            raise ValueError("Duration must be non-negative")

class ObservationProject(Project):
    _item_type = Observation

    def create_item(self, item_code: str = "OBS_DEFAULT", isactive: bool = True) -> None:
        self._items.add(Observation(name=item_code, isactive=isactive, frequency=1.4, duration=60))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ObservationProject':
        items = {k: Observation.from_dict(v) for k, v in data["items"].items()}
        return cls(name=data["name"], items=items)

class ObservationConfigurator(Super):
    def _configure_observation(self, obj: Observation, attrs: Dict[str, Any]) -> bool:
        if "isactive" in attrs:
            if attrs["isactive"]:
                obj.activate()
            else:
                obj.deactivate()
            attrs = {k: v for k, v in attrs.items() if k != "isactive"}
        obj.set(attrs)
        return True

    def _configure_basecontainer(self, obj: BaseContainer, attrs: Dict[str, Any]) -> bool:
        for name, item_attrs in attrs.get("items", {}).items():
            if name in obj:
                if "isactive" in item_attrs:
                    if item_attrs["isactive"]:
                        obj[name].activate()
                    else:
                        obj[name].deactivate()
                    item_attrs = {k: v for k, v in item_attrs.items() if k != "isactive"}
                obj[name].set(item_attrs)
                obj._invalidate_cache()
        return True

    def _configure_project(self, obj: ObservationProject, attrs: Dict[str, Any]) -> bool:
        """Configure an ObservationProject instance."""
        success = True
        if "name" in attrs:
            try:
                obj.set_name(attrs["name"])
            except ValueError as e:
                logger.error(f"Failed to set project name: {str(e)}")
                success = False

        if "items" in attrs:
            for name, item_attrs in attrs["items"].items():
                if name not in obj._items:
                    try:
                        obj.create_item(item_code=name, isactive=item_attrs.get("isactive", True))
                    except (TypeError, ValueError) as e:
                        logger.error(f"Failed to create item '{name}': {str(e)}")
                        success = False
                        continue
                item = obj._items[name]
                if "isactive" in item_attrs:
                    if item_attrs["isactive"]:
                        item.activate()
                    else:
                        item.deactivate()
                    item_attrs = {k: v for k, v in item_attrs.items() if k != "isactive"}
                try:
                    item.set(item_attrs)  # Применяем все атрибуты
                except (TypeError, ValueError) as e:
                    logger.error(f"Failed to configure item '{name}': {str(e)}")
                    success = False
                obj._items._invalidate_cache()
        return success

class TestManipulatorIntegration(unittest.TestCase):
    def setUp(self) -> None:
        """Подготовка перед каждым тестом."""
        self.manipulator = Manipulator(base_classes=[Observation, ObservationContainer, ObservationProject])
        self.configurator = ObservationConfigurator(manipulator=self.manipulator)
        self.manipulator.register_operation("configure", self.configurator)
        self.project = ObservationProject(name="TestProject")
        self.obs = Observation(name="OBS1", frequency=1.4, duration=60)
        self.container = ObservationContainer(name="TestContainer")
        logger.info("Set up TestManipulatorIntegration")

    def test_initialization_with_project(self) -> None:
        """Тест инициализации Manipulator с Project как managing_object."""
        manip = Manipulator(managing_object=self.project)
        self.assertEqual(manip.get_managing_object(), self.project)
        self.assertIn(ObservationProject, manip._base_classes)
        logger.info("Initialization with Project tested successfully")

    def test_configure_observation(self) -> None:
        """Тест конфигурации Observation через Manipulator."""
        self.project.add_item(self.obs)
        request = {
            "operation": "configure",
            "obj": self.obs,
            "attributes": {"frequency": 2.0, "duration": 120}
        }
        result = self.manipulator.process_request(request)
        self.assertEqual(result, {"success": True, "result": True})
        self.assertEqual(self.obs.frequency, 2.0)
        self.assertEqual(self.obs.duration, 120)
        logger.info("Observation configuration tested successfully")

    def test_configure_container(self) -> None:
        """Тест конфигурации BaseContainer через Manipulator."""
        self.container.add(self.obs)
        request = {
            "operation": "configure",
            "obj": self.container,
            "attributes": {
                "items": {"OBS1": {"frequency": 3.0, "isactive": False}}
            }
        }
        result = self.manipulator.process_request(request)
        self.assertEqual(result, {"success": True, "result": True})
        self.assertEqual(self.container["OBS1"].frequency, 3.0)
        self.assertFalse(self.container["OBS1"].isactive)
        logger.info("Container configuration tested successfully")

    def _configure_project(self, obj: ObservationProject, attrs: Dict[str, Any]) -> bool:
        """Configure an ObservationProject instance."""
        success = True
        if "name" in attrs:
            try:
                obj.set_name(attrs["name"])
            except ValueError as e:
                logger.error(f"Failed to set project name: {str(e)}")
                success = False

        if "items" in attrs:
            for name, item_attrs in attrs["items"].items():
                if name not in obj._items:
                    try:
                        obj.create_item(item_code=name, isactive=item_attrs.get("isactive", True))
                    except (TypeError, ValueError) as e:
                        logger.error(f"Failed to create item '{name}': {str(e)}")
                        success = False
                        continue
                item = obj._items[name]
                if "isactive" in item_attrs:
                    if item_attrs["isactive"]:
                        item.activate()
                    else:
                        item.deactivate()
                    item_attrs = {k: v for k, v in item_attrs.items() if k != "isactive"}
                # Исключаем атрибут 'name' из item_attrs
                item_attrs = {k: v for k, v in item_attrs.items() if k != "name"}
                try:
                    item.set(item_attrs)
                except (TypeError, ValueError) as e:
                    logger.error(f"Failed to configure item '{name}': {str(e)}")
                    success = False
                obj._items._invalidate_cache()
        return success

    def test_strict_type_check_failure(self) -> None:
        """Тест строгой проверки типов с неподдерживаемым объектом."""
        manip = Manipulator(strict_type_check=True)
        manip.register_operation("configure", ObservationConfigurator(manipulator=manip))
        request = {
            "operation": "configure",
            "obj": "invalid_type",  # String не в base_classes
            "attributes": {"value": 42}
        }
        with self.assertRaises(ValueError) as cm:
            manip.process_request(request)
        self.assertIn("Unsupported object type: <class 'str'>", str(cm.exception))
        logger.info("Strict type check failure tested successfully")

    def test_sequence_request_integration(self) -> None:
        """Тест последовательности запросов с интеграцией всех компонентов."""
        self.project.add_item(self.obs)
        self.container.add(self.obs.clone())
        request = {
            "req1": {"operation": "configure", "obj": self.obs, "attributes": {"frequency": 5.0}},
            "req2": {"operation": "configure", "obj": self.container, "attributes": {"items": {"OBS1": {"duration": 90}}}},
            "req3": {
                "operation": "configure",
                "obj": self.project,
                "method": "_configure_project",  # Явно указываем метод
                "attributes": {"name": "SeqProject"}
            }
        }
        results = self.manipulator.process_request(request)
        self.assertEqual(len(results), 3)
        self.assertTrue(results["req1"]["success"])
        self.assertTrue(results["req2"]["success"])
        self.assertTrue(results["req3"]["success"])
        self.assertEqual(self.obs.frequency, 5.0)
        self.assertEqual(self.container["OBS1"].duration, 90)
        self.assertEqual(self.project.get_name(), "SeqProject")
        logger.info("Sequence request integration tested successfully")

    def test_caching_with_container(self) -> None:
        """Тест кэширования в BaseContainer через Manipulator."""
        container = ObservationContainer(name="CacheContainer", use_cache=True)
        container.add(self.obs)
        dict1 = container.to_dict()
        request = {
            "operation": "configure",
            "obj": container,
            "attributes": {"items": {"OBS1": {"frequency": 6.0}}}
        }
        result = self.manipulator.process_request(request)
        self.assertTrue(result["success"])
        dict2 = container.to_dict()
        self.assertNotEqual(dict1, dict2)
        self.assertEqual(container["OBS1"].frequency, 6.0)
        dict3 = container.to_dict()
        self.assertIs(dict2, dict3)  # Кэш обновлён и используется
        logger.info("Caching with container tested successfully")

    def test_error_handling_invalid_attributes(self) -> None:
        """Тест обработки ошибок с невалидными атрибутами."""
        request = {
            "operation": "configure",
            "obj": self.obs,
            "attributes": {"frequency": "invalid"}  # Неверный тип
        }
        result = self.manipulator.process_request(request)
        self.assertTrue(result["success"])  # Super возвращает True, но BaseEntity не применяет
        self.assertEqual(self.obs.frequency, 1.4)  # Значение не изменилось
        logger.info("Error handling with invalid attributes tested successfully")

    def test_missing_operation(self) -> None:
        """Тест обработки запроса без операции."""
        request = {"obj": self.obs, "attributes": {"frequency": 7.0}}
        result = self.manipulator.process_request(request)
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "No operation specified in request")
        self.assertEqual(self.obs.frequency, 1.4)
        logger.info("Missing operation tested successfully")

    def test_invalid_operation(self) -> None:
        """Тест обработки запроса с несуществующей операцией."""
        request = {"operation": "invalid_op", "obj": self.obs, "attributes": {"frequency": 7.0}}
        result = self.manipulator.process_request(request)
        self.assertFalse(result["success"])
        self.assertIn("not registered", result["error"])
        self.assertEqual(self.obs.frequency, 1.4)
        logger.info("Invalid operation tested successfully")

    def test_large_scale_project_config(self) -> None:
        """Тест конфигурации большого проекта."""
        for i in range(100):
            self.project.create_item(f"OBS_LARGE_{i}")
        request = {
            "operation": "configure",
            "obj": self.project,
            "method": "_configure_project",  # Явно указываем метод
            "attributes": {
                "items": {f"OBS_LARGE_{i}": {"frequency": float(i + 1)} for i in range(100)}
            }
        }
        result = self.manipulator.process_request(request)
        self.assertTrue(result["success"])
        for i in range(100):
            self.assertEqual(self.project.get_item(f"OBS_LARGE_{i}").frequency, float(i + 1))
        logger.info("Large-scale project configuration tested successfully")

    def test_nested_container_in_project(self) -> None:
        """Тест конфигурации вложенного контейнера в проекте."""
        nested_container = ObservationContainer(name="NestedContainer")
        nested_obs = Observation(name="NESTED_OBS", frequency=1.0, duration=30)
        nested_container.add(nested_obs)
        self.project.add_item(self.obs)
        # Имитация вложенности через атрибут (для примера)
        self.project._items["OBS1"].nested_container = nested_container
        request = {
            "operation": "configure",
            "obj": nested_container,
            "attributes": {"items": {"NESTED_OBS": {"frequency": 2.0}}}
        }
        result = self.manipulator.process_request(request)
        self.assertTrue(result["success"])
        self.assertEqual(nested_container["NESTED_OBS"].frequency, 2.0)
        logger.info("Nested container in project tested successfully")

    def test_registry_update(self) -> None:
        """Тест обновления реестра с добавлением нового типа."""
        manip = Manipulator()
        manip.register_operation("configure", self.configurator)
        manip.update_registry(additional_classes=[ObservationContainer])
        self.assertIn(ObservationContainer, manip._registry)
        methods = manip.get_methods_for_type(ObservationContainer)
        self.assertIn("add", methods)
        logger.info("Registry update tested successfully")

    def test_managing_object_default(self) -> None:
        """Тест использования managing_object по умолчанию."""
        manip = Manipulator(managing_object=self.obs)
        manip.register_operation("configure", self.configurator)
        request = {"operation": "configure", "attributes": {"frequency": 8.0}}
        result = manip.process_request(request)
        self.assertTrue(result["success"])
        self.assertEqual(self.obs.frequency, 8.0)
        logger.info("Managing object default tested successfully")

if __name__ == "__main__":
    unittest.main()