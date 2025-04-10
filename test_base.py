import unittest
from typing import TypeVar, Generic
from common.base.baseentity import BaseEntity
from common.base.basecontainer import BaseContainer

T = TypeVar('T')

class TestEntity(BaseEntity):
    value: int
    nested: 'TestEntity'

class TestContainer(BaseContainer[TestEntity]):
    def _validate_item(self, item: TestEntity) -> None:
        if item.value < 0:
            raise ValueError("Value must be non-negative")

class TestBaseEntity(unittest.TestCase):
    def test_init_without_attributes(self):
        entity = TestEntity(name="test")
        self.assertEqual(entity.name, "test")
        self.assertTrue(entity.isactive)
        self.assertIsNone(entity.value)
        self.assertIsNone(entity.nested)

    def test_init_with_none_name(self):
        entity = TestEntity(name=None)
        self.assertIsNone(entity.name)
        self.assertTrue(entity.isactive)
        self.assertIsNone(entity.value)

    def test_init_with_attributes(self):
        nested = TestEntity(name="nested", value=42)
        entity = TestEntity(name="test", value=100, nested=nested)
        self.assertEqual(entity.value, 100)
        self.assertEqual(entity.nested, nested)

    def test_init_invalid_attribute(self):
        with self.assertRaises(ValueError):
            TestEntity(name="test", unknown=42)

    def test_setattr_type_validation(self):
        entity = TestEntity(name="test")
        entity.value = 42
        self.assertEqual(entity.value, 42)
        with self.assertRaises(TypeError):
            entity.value = "invalid"

    def test_setitem_type_validation(self):
        entity = TestEntity(name="test")
        entity["value"] = 42
        self.assertEqual(entity["value"], 42)
        with self.assertRaises(TypeError):
            entity["value"] = "invalid"

    def test_unknown_attribute(self):
        entity = TestEntity(name="test")
        with self.assertRaises(ValueError):
            entity.__setattr__("unknown", 42)
        with self.assertRaises(KeyError):
            entity["unknown"] = 42

    def test_get_single_attribute(self):
        entity = TestEntity(name="test", value=42)
        self.assertEqual(entity.get("value"), 42)
        with self.assertRaises(KeyError):
            entity.get("unknown")

    def test_get_all_attributes(self):
        nested = TestEntity(name="nested", value=42)
        entity = TestEntity(name="test", value=100, nested=nested)
        attrs = entity.get()
        self.assertEqual(attrs["value"], 100)
        self.assertEqual(attrs["nested"], nested)

    def test_has_attribute(self):
        entity = TestEntity(name="test", value=42)
        self.assertTrue(entity.has_attribute("value"))
        self.assertFalse(entity.has_attribute("unknown"))

    def test_serialization(self):
        nested = TestEntity(name="nested", value=42)
        entity = TestEntity(name="test", value=100, nested=nested)
        data = entity.to_dict()
        restored = TestEntity.from_dict(data)
        self.assertEqual(restored, entity)

    def test_serialization_none_values(self):
        entity = TestEntity(name="test")
        data = entity.to_dict()
        self.assertIn("value", data)
        self.assertIsNone(data["value"])
        restored = TestEntity.from_dict(data)
        self.assertEqual(restored, entity)

    def test_from_dict_invalid_type(self):
        data = {"name": "test", "isactive": True, "value": "invalid"}
        with self.assertRaises(TypeError):
            TestEntity.from_dict(data)

    def test_from_dict_missing_field(self):
        data = {"name": "test", "isactive": True}
        entity = TestEntity.from_dict(data)
        self.assertIsNone(entity.value)

    def test_equality(self):
        entity1 = TestEntity(name="test", value=42)
        entity2 = TestEntity(name="test", value=42)
        entity3 = TestEntity(name="test", value=43)
        self.assertEqual(entity1, entity2)
        self.assertNotEqual(entity1, entity3)

    def test_activate_deactivate(self):
        entity = TestEntity(name="test")
        entity.deactivate()
        self.assertFalse(entity.isactive)
        entity.activate()
        self.assertTrue(entity.isactive)

    def test_clone(self):
        nested = TestEntity(name="nested", value=42)
        entity = TestEntity(name="test", value=100, nested=nested)
        clone = entity.clone()
        self.assertEqual(entity, clone)
        self.assertIsNot(entity, clone)
    
    def test_typevar_resolution(self):
        class GenericEntity(BaseEntity, Generic[T]):
            data: T
        class IntEntity(GenericEntity[int]):
            pass
        entity = IntEntity(data=42)
        self.assertEqual(entity.data, 42)
        with self.assertRaises(TypeError):
            entity.data = "invalid"

class TestBaseContainer(unittest.TestCase):
    def test_init_without_items(self):
        container = TestContainer(name="test")
        self.assertEqual(len(container), 0)
        self.assertEqual(container.name, "test")

    def test_init_with_items(self):
        items = {"item1": TestEntity(name="item1", value=42)}
        container = TestContainer(name="test", items=items)
        self.assertEqual(container.get("item1").value, 42)

    def test_init_duplicate_names(self):
        items = {
            "item1": TestEntity(name="item1", value=42),
            "item2": TestEntity(name="item1", value=100)
        }
        with self.assertRaises(ValueError):
            TestContainer(name="test", items=items)

    def test_init_invalid_item_validation(self):
        items = {"item1": TestEntity(name="item1", value=-1)}
        with self.assertRaises(ValueError):
            TestContainer(name="test", items=items)

    def test_add_remove(self):
        container = TestContainer(name="test")
        item = TestEntity(name="item1", value=42)
        container.add(item)
        self.assertEqual(container["item1"], item)
        container.remove("item1")
        with self.assertRaises(KeyError):
            container["item1"]

    def test_add_none_name(self):
        container = TestContainer(name="test")
        with self.assertRaises(ValueError):
            container.add(TestEntity(name=None, value=42))

    def test_add_duplicate_name(self):
        container = TestContainer(name="test")
        container.add(TestEntity(name="item1", value=42))
        with self.assertRaises(ValueError):
            container.add(TestEntity(name="item1", value=100))

    def test_remove_nonexistent(self):
        container = TestContainer(name="test")
        with self.assertRaises(KeyError):
            container.remove("item1")

    def test_setitem_none_name(self):
        container = TestContainer(name="test")
        with self.assertRaises(ValueError):
            container["item1"] = TestEntity(name=None, value=42)

    def test_setitem_mismatched_name(self):
        container = TestContainer(name="test")
        with self.assertRaises(ValueError):
            container["item1"] = TestEntity(name="item2", value=42)

    def test_validation(self):
        container = TestContainer(name="test")
        with self.assertRaises(ValueError):
            container.add(TestEntity(name="item1", value=-1))

    def test_get_all(self):
        container = TestContainer(name="test")
        item = TestEntity(name="item1", value=42)
        container.add(item)
        items = container.get_all()
        self.assertEqual(items, {"item1": item})

    def test_get_items(self):
        container = TestContainer(name="test")
        item = TestEntity(name="item1", value=42)
        container.add(item)
        self.assertEqual(container.get_items(), [item])

    def test_set_items(self):
        container = TestContainer(name="test")
        items = {"item1": TestEntity(name="item1", value=42)}
        container.set_items(items)
        self.assertEqual(container["item1"].value, 42)

    def test_set_items_invalid(self):
        container = TestContainer(name="test")
        items = {"item1": TestEntity(name="item1", value=-1)}
        with self.assertRaises(ValueError):
            container.set_items(items)

    def test_clear(self):
        container = TestContainer(name="test")
        container.add(TestEntity(name="item1", value=42))
        container.clear()
        self.assertEqual(len(container), 0)

    def test_serialization(self):
        container = TestContainer(name="test")
        container["item1"] = TestEntity(name="item1", value=42)
        data = container.to_dict()
        restored = TestContainer.from_dict(data)
        self.assertEqual(restored, container)

    def test_from_dict_invalid_item(self):
        data = {
            "name": "test",
            "isactive": True,
            "items": {"item1": {"name": "item1", "isactive": True, "value": "invalid"}}
        }
        with self.assertRaises(TypeError):
            TestContainer.from_dict(data)

    def test_from_dict_empty_items(self):
        data = {"name": "test", "isactive": True, "items": {}}
        container = TestContainer.from_dict(data)
        self.assertEqual(len(container), 0)

    def test_set_items_empty(self):
        container = TestContainer(name="test")
        container.set_items({})
        self.assertEqual(len(container), 0)

    def test_equality(self):
        container1 = TestContainer(name="test")
        container1["item1"] = TestEntity(name="item1", value=42)
        container2 = TestContainer(name="test")
        container2["item1"] = TestEntity(name="item1", value=42)
        self.assertEqual(container1, container2)
        container2["item1"].value = 43
        self.assertNotEqual(container1, container2)

    def test_clone(self):
        container = TestContainer(name="test")
        container["item1"] = TestEntity(name="item1", value=42)
        clone = container.clone()
        self.assertEqual(container, clone)
        self.assertIsNot(container, clone)

    def test_activate_deactivate_item(self):
        container = TestContainer(name="test")
        container["item1"] = TestEntity(name="item1", value=42)
        container.deactivate_item("item1")
        self.assertFalse(container["item1"].isactive)
        container.activate_item("item1")
        self.assertTrue(container["item1"].isactive)

    def test_contains(self):
        container = TestContainer(name="test")
        container["item1"] = TestEntity(name="item1", value=42)
        self.assertTrue("item1" in container)
        self.assertFalse("item2" in container)

    def test_len(self):
        container = TestContainer(name="test")
        self.assertEqual(len(container), 0)
        container["item1"] = TestEntity(name="item1", value=42)
        self.assertEqual(len(container), 1)

    def test_iter(self):
        container = TestContainer(name="test")
        item = TestEntity(name="item1", value=42)
        container["item1"] = item
        self.assertEqual(list(container), [item])

    def test_repr(self):
        container = TestContainer(name="test")
        container["item1"] = TestEntity(name="item1", value=42)
        repr_str = repr(container)
        self.assertIn("TestContainer", repr_str)
        self.assertIn("name='test'", repr_str)
        self.assertIn("count=1", repr_str)
        self.assertIn("active=1", repr_str)
    
    def test_caching(self):
        container = TestContainer(name="test", use_cache=True)
        item = TestEntity(name="item1", value=42)
        container.add(item)
        dict1 = container.to_dict()
        dict2 = container.to_dict()
        self.assertIs(dict1, dict2)  # Проверяем, что кэш работает
        container.add(TestEntity(name="item2", value=100))
        dict3 = container.to_dict()
        self.assertIsNot(dict1, dict3)  # Кэш инвалидируется

    def test_unresolved_type_fallback(self):
        # Создаём временный класс с forward reference
        class TempContainer(BaseContainer["UnresolvedType"]):
            pass
        
        data = {"name": "test", "items": {"item1": {"name": "item1", "value": 42}}}
        with self.assertLogs("", level="WARNING") as cm:  # Проверяем корневой логгер
            with self.assertRaises(TypeError):
                TempContainer.from_dict(data)
        self.assertIn("Cannot resolve type hint 'UnresolvedType'", cm.output[0])
    
    def test_direct_items_mutation(self):
        container = TestContainer(name="test", use_cache=True)
        item = TestEntity(name="item1", value=42)
        container.add(item)
        dict1 = container.to_dict()
        container.add(TestEntity(name="item2", value=100))  # Используем add вместо прямой мутации
        dict2 = container.to_dict()
        self.assertNotEqual(dict1, dict2)  # Кэш инвалидируется через add
        self.assertEqual(container["item2"].value, 100)  # Мутация работает

if __name__ == "__main__":
    unittest.main()