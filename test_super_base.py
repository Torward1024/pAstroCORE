# tests/test_msb_integration.py
import unittest
from typing import Dict, Any, Optional
from unittest.mock import Mock
from common.base.baseentity import BaseEntity
from common.base.basecontainer import BaseContainer
from common.super.super import Super
from common.super.project import Project
from common.super.manipulator import Manipulator
from common.utils.logging_setup import logger

# Определяем тестовые сущности
class Observation(BaseEntity):
    frequency: float
    duration: int

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

class TestMSBIntegration(unittest.TestCase):
    def setUp(self) -> None:
        """Подготовка перед каждым тестом."""
        self.manipulator = Manipulator()
        self.configurator = ObservationConfigurator(manipulator=self.manipulator)
        self.manipulator.register_operation("configure", self.configurator)
        self.project = ObservationProject(name="IntegrationTest")
        self.obs1 = Observation(name="OBS1", frequency=1.4, duration=60)
        self.obs2 = Observation(name="OBS2", frequency=2.0, duration=120)

    def test_base_entity_initialization(self) -> None:
        """Тест инициализации BaseEntity."""
        obs = Observation(name="OBS_TEST", frequency=1.6, duration=30)
        self.assertEqual(obs.name, "OBS_TEST")
        self.assertEqual(obs.frequency, 1.6)
        self.assertEqual(obs.duration, 30)
        self.assertTrue(obs.isactive)
        logger.info("BaseEntity initialized successfully")

    def test_base_entity_validation(self) -> None:
        """Тест валидации типов в BaseEntity."""
        with self.assertRaises(TypeError):
            Observation(name="OBS_INVALID", frequency="invalid", duration=60)
        obs = Observation(name="OBS_VALID")
        with self.assertRaises(TypeError):
            obs["frequency"] = "invalid"
        logger.info("BaseEntity type validation tested successfully")

    def test_base_container_initialization(self) -> None:
        """Тест инициализации BaseContainer."""
        container = ObservationContainer(name="TestContainer")
        container.add(self.obs1)
        self.assertEqual(container["OBS1"], self.obs1)
        self.assertEqual(len(container), 1)
        logger.info("BaseContainer initialized successfully")

    def test_base_container_validation(self) -> None:
        """Тест валидации в BaseContainer."""
        container = ObservationContainer(name="TestContainer")
        invalid_obs = Observation(name="OBS_INVALID", frequency=-1.0, duration=60)  # Изменено на float
        with self.assertRaises(ValueError):
            container.add(invalid_obs)
        with self.assertRaises(ValueError):
            container["OBS_MISMATCH"] = Observation(name="OBS_DIFF", frequency=1.4, duration=60)
        logger.info("BaseContainer validation tested successfully")

    def test_project_crud_operations(self) -> None:
        """Тест CRUD операций в Project."""
        self.project.add_item(self.obs1)
        self.assertEqual(self.project.get_item("OBS1"), self.obs1)
        self.project.create_item("OBS_NEW")
        self.assertEqual(self.project.get_item("OBS_NEW").frequency, 1.4)
        self.project.remove_item("OBS1")
        with self.assertRaises(KeyError):
            self.project.get_item("OBS1")
        self.assertEqual(len(self.project.get_items()), 1)
        logger.info("Project CRUD operations tested successfully")

    def test_project_serialization(self) -> None:
        """Тест сериализации/десериализации Project."""
        self.project.add_item(self.obs1)
        data = self.project.to_dict()
        self.assertEqual(data["name"], "IntegrationTest")
        self.assertIn("OBS1", data["items"])
        restored = ObservationProject.from_dict(data)
        self.assertEqual(restored.get_item("OBS1").frequency, 1.4)
        self.assertEqual(restored.get_item("OBS1").duration, 60)
        logger.info("Project serialization tested successfully")

    def test_super_configuration(self) -> None:
        """Тест конфигурации через Super."""
        self.project.add_item(self.obs1)
        request = {
            "operation": "configure",
            "obj": self.obs1,
            "attributes": {"frequency": 2.5, "duration": 90}
        }
        result = self.manipulator.process_request(request)
        self.assertTrue(result)
        self.assertEqual(self.obs1.frequency, 2.5)
        self.assertEqual(self.obs1.duration, 90)
        logger.info("Super configuration of Observation tested successfully")

    def test_super_container_configuration(self) -> None:
        """Тест конфигурации контейнера через Super."""
        self.project.add_item(self.obs1)
        self.project.add_item(self.obs2)
        request = {
            "operation": "configure",
            "obj": self.project._items,
            "attributes": {
                "items": {
                    "OBS1": {"frequency": 3.0},
                    "OBS2": {"duration": 180}
                }
            }
        }
        result = self.manipulator.process_request(request)
        self.assertTrue(result)
        self.assertEqual(self.project.get_item("OBS1").frequency, 3.0)
        self.assertEqual(self.project.get_item("OBS2").duration, 180)
        logger.info("Super configuration of BaseContainer tested successfully")

    def test_nested_operations(self) -> None:
        """Тест вложенных операций через Super."""
        container = ObservationContainer(name="NestedContainer")
        container.add(self.obs1)
        request = {
            "operation": "configure",
            "obj": container,
            "attributes": {
                "items": {"OBS1": {"frequency": 4.0}}
            }
        }
        result = self.manipulator.process_request(request)
        self.assertTrue(result)
        self.assertEqual(container["OBS1"].frequency, 4.0)
        logger.info("Nested operations tested successfully")

    def test_caching_integration(self) -> None:
        """Тест кэширования в BaseEntity и BaseContainer."""
        obs = Observation(name="OBS_CACHE", frequency=1.4, duration=60, use_cache=True)
        container = ObservationContainer(name="TestCacheContainer", use_cache=True)
        container.add(obs)
        dict1 = container.to_dict()
        dict2 = container.to_dict()
        self.assertIs(dict1, dict2)
        # Изменяем через Super или set, а не прямой доступ
        request = {
            "operation": "configure",
            "obj": container,
            "attributes": {"items": {"OBS_CACHE": {"frequency": 2.0}}}
        }
        result = self.manipulator.process_request(request)
        self.assertTrue(result)
        dict3 = container.to_dict()
        self.assertIsNot(dict1, dict3)
        self.assertEqual(container["OBS_CACHE"].frequency, 2.0)
        logger.info("Caching integration tested successfully")

    def test_large_scale_operations(self) -> None:
        """Тест работы с большим количеством объектов."""
        for i in range(1000):
            self.project.create_item(f"OBS_LARGE_{i}")
        self.assertEqual(len(self.project.get_items()), 1000)
        request = {
            "operation": "configure",
            "obj": self.project._items,
            "attributes": {"items": {f"OBS_LARGE_{i}": {"frequency": 2.0} for i in range(0, 1000, 2)}}
        }
        result = self.manipulator.process_request(request)
        self.assertTrue(result)
        for i in range(0, 1000, 2):
            self.assertEqual(self.project.get_item(f"OBS_LARGE_{i}").frequency, 2.0)
        logger.info("Large-scale operations tested successfully")

    def test_activation_integration(self) -> None:
        """Тест интеграции активации/деактивации."""
        self.project.add_item(self.obs1)
        self.project.get_item("OBS1").deactivate()
        self.assertFalse(self.project.get_item("OBS1").isactive)
        request = {
            "operation": "configure",
            "obj": self.obs1,
            "attributes": {"isactive": True}
        }
        result = self.manipulator.process_request(request)
        self.assertTrue(result)  # Добавляем проверку результата
        self.assertTrue(self.project.get_item("OBS1").isactive)
        logger.info("Activation integration tested successfully")

    def test_error_handling(self) -> None:
        """Тест обработки ошибок."""
        request = {
            "operation": "configure",
            "obj": self.obs1,
            "attributes": {"frequency": "invalid"}  # Неверный тип
        }
        result = self.manipulator.process_request(request)
        self.assertTrue(result)  # Super возвращает True, но BaseEntity обработает ошибку
        self.assertEqual(self.obs1.frequency, 1.4)  # Значение не изменилось
        logger.info("Error handling tested successfully")

    def test_project_container_sync(self) -> None:
        """Тест синхронизации Project и его контейнера."""
        self.project.add_item(self.obs1)
        self.project._items.remove("OBS1")
        with self.assertRaises(KeyError):
            self.project.get_item("OBS1")
        self.project._items.add(self.obs2)
        self.assertEqual(self.project.get_item("OBS2"), self.obs2)
        logger.info("Project and container sync tested successfully")

if __name__ == "__main__":
    unittest.main()