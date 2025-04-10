# tests/test_base.py
import unittest
from common.base.baseentity import BaseEntity
from common.base.basecontainer import BaseContainer

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

    def test_serialization(self):
        nested = TestEntity(name="nested", value=42)
        entity = TestEntity(name="test", value=100, nested=nested)
        data = entity.to_dict()
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
        self.assertEqual(entity1, entity2)

    def test_activate_deactivate(self):
        entity = TestEntity(name="test")
        entity.deactivate()
        self.assertFalse(entity.isactive)

class TestBaseContainer(unittest.TestCase):
    def test_init_without_items(self):
        container = TestContainer(name="test")
        self.assertEqual(len(container), 0)

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

    def test_add_remove(self):
        container = TestContainer(name="test")
        item = TestEntity(name="item1", value=42)
        container.add(item)
        container.remove("item1")
        with self.assertRaises(KeyError):
            container["item1"]

    def test_setitem_none_name(self):
        container = TestContainer(name="test")
        with self.assertRaises(ValueError):
            container["item1"] = TestEntity(name=None, value=42)

    def test_validation(self):
        container = TestContainer(name="test")
        with self.assertRaises(ValueError):
            container.add(TestEntity(name="item1", value=-1))

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

    def test_clone(self):
        container = TestContainer(name="test")
        container["item1"] = TestEntity(name="item1", value=42)
        clone = container.clone()
        self.assertEqual(container, clone)
        self.assertIsNot(container, clone)

if __name__ == "__main__":
    unittest.main()