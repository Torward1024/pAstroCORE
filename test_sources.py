# tests/test_sources.py
import unittest
from unit_scheduling_2.base.sources import Source, Sources

class TestSource(unittest.TestCase):
    def setUp(self) -> None:
        self.source = Source(
            name="3C 273",
            ra_h=12.0,
            ra_m=29.0,
            ra_s=6.7,
            de_d=2.0,
            de_m=2.0,
            de_s=0.2,
            name_J2000="J1229+0203",
            alt_name="Quasar",
            flux_table={1420.0: 45.0, 5000.0: 20.0},
            spectral_index=-0.7,
            isactive=True,
        )

    def test_initialization(self) -> None:
        self.assertEqual(self.source.name, "3C 273")
        self.assertEqual(self.source.ra_h, 12)
        self.assertEqual(self.source.ra_m, 29)
        self.assertEqual(self.source.ra_s, 6.7)
        self.assertEqual(self.source.de_d, 2)
        self.assertEqual(self.source.de_m, 2)
        self.assertEqual(self.source.de_s, 0.2)
        self.assertEqual(self.source.name_J2000, "J1229+0203")
        self.assertEqual(self.source.alt_name, "Quasar")
        self.assertEqual(self.source.flux_table, {1420.0: 45.0, 5000.0: 20.0})
        self.assertEqual(self.source.spectral_index, -0.7)
        self.assertTrue(self.source.isactive)

    def test_validation_coordinates(self) -> None:
        with self.assertRaises(ValueError):
            Source(name="Invalid", ra_h=24.0)  # RA hours out of range
        with self.assertRaises(ValueError):
            Source(name="Invalid", de_d=91.0)  # DEC degrees out of range

    def test_validation_flux_table(self) -> None:
        with self.assertRaises(ValueError):
            Source(name="Invalid", flux_table={1420.0: -1.0})  # Negative flux
        with self.assertRaises(TypeError):
            Source(name="Invalid", flux_table={"1420": 1.0})  # Non-numeric key

    def test_get_set_attributes(self) -> None:
        self.source.set({"name": "New Source", "ra_h": 10.0})
        self.assertEqual(self.source.get("name"), "New Source")
        self.assertEqual(self.source.get("ra_h"), 10.0)
        with self.assertRaises(ValueError):
            self.source.set({"invalid_attr": 123})  # Unknown attribute
        with self.assertRaises(TypeError):
            self.source.set({"ra_h": "invalid"})  # Wrong type

    def test_coordinates_degrees(self) -> None:
        self.assertAlmostEqual(self.source.ra_degrees, 187.27791666666666)
        self.assertAlmostEqual(self.source.dec_degrees, 2.033388888888889)
        self.source.set_ra_degrees(180.0)
        self.source.set_dec_degrees(-45.0)
        self.assertAlmostEqual(self.source.ra_h, 12.0)
        self.assertAlmostEqual(self.source.de_d, -45.0)

    def test_flux_operations(self) -> None:
        self.source.add_flux(3000.0, 30.0)
        self.assertEqual(self.source.flux_table[3000], 30.0)
        self.assertAlmostEqual(self.source.get_flux(1420.0), 45.0)  # Direct hit
        self.assertAlmostEqual(self.source.get_flux(1500.0), 43.306239512538355, places=3)  # Extrapolation
        self.assertAlmostEqual(self.source.get_flux(2000.0), 35.407344611027625, places=3)  # Interpolation
        self.source.remove_flux(3000.0)
        self.assertNotIn(3000.0, self.source.flux_table)
        self.source.clear_flux_table()
        self.assertEqual(self.source.flux_table, {})

    def test_serialization(self) -> None:
        data = self.source.to_dict()
        self.assertEqual(data["name"], "3C 273")
        self.assertEqual(data["ra_h"], 12.0)
        self.assertEqual(data["flux_table"], {1420.0: 45.0, 5000.0: 20.0})  # Исправлено
        new_source = Source.from_dict(data)
        self.assertEqual(new_source, self.source)

    def test_clone(self) -> None:
        clone = self.source.clone()
        self.assertEqual(clone.name, self.source.name)
        self.assertEqual(clone.flux_table, self.source.flux_table)
        clone.set({"name": "Cloned"})
        self.assertNotEqual(clone.name, self.source.name)

    def test_equality(self) -> None:
        other = Source(
            name="3C 273",
            ra_h=12.0,
            ra_m=29.0,
            ra_s=6.7,
            de_d=2.0,
            de_m=2.0,
            de_s=0.2,
            name_J2000="J1229+0203",  # Добавлено
            alt_name="Quasar",        # Добавлено
        )
        self.assertNotEqual(other, self.source)  # Разные flux_table и spectral_index
        other.set({"flux_table": {1420.0: 45.0, 5000.0: 20.0}, "spectral_index": -0.7})
        self.assertEqual(other, self.source)

class TestSources(unittest.TestCase):
    def setUp(self) -> None:
        self.sources = Sources()
        self.source1 = Source(name="3C 273", ra_h=12.0, ra_m=29.0, ra_s=6.7, de_d=2.0, flux_table={1420.0: 45.0})
        self.source2 = Source(name="3C 286", ra_h=13.0, ra_m=31.0, ra_s=18.4, de_d=30.0, isactive=False)

    def test_add_source(self) -> None:
        self.sources.create_source(name="3C 273", ra_h=12.0, ra_m=29.0, ra_s=6.7, de_d=2.0)
        self.assertEqual(len(self.sources), 1)
        self.assertEqual(self.sources.get("3C 273").name, "3C 273")
        with self.assertRaises(ValueError):
            self.sources.add(Source(name="3C 273"))  # Duplicate name

    def test_get_methods(self) -> None:
        self.sources.add(self.source1)
        self.sources.add(self.source2)
        self.assertEqual(self.sources.get("3C 273"), self.source1)
        self.assertEqual(self.sources.get_all(), {"3C 273": self.source1, "3C 286": self.source2})
        self.assertEqual(self.sources.get_active_items(), [self.source1])
        self.assertEqual(self.sources.get_inactive_items(), [self.source2])
        self.assertEqual(self.sources.get_by_value({"name": "3C 273"}), [self.source1])

    def test_remove_clear(self) -> None:
        self.sources.add(self.source1)
        self.sources.remove("3C 273")
        self.assertEqual(len(self.sources), 0)
        self.sources.add(self.source1)
        self.sources.add(self.source2)
        self.sources.clear()
        self.assertEqual(len(self.sources), 0)

    def test_activation(self) -> None:
        self.sources.add(self.source1)
        self.sources.add(self.source2)
        self.sources.activate_item("3C 286")
        self.assertTrue(self.sources.get("3C 286").isactive)
        self.sources.deactivate_all()
        self.assertEqual(self.sources.get_active_items(), [])
        self.sources.activate_all()
        self.assertEqual(len(self.sources.get_active_items()), 2)

    def test_drop_methods(self) -> None:
        self.sources.add(self.source1)
        self.sources.add(self.source2)
        self.sources.drop_inactive()
        self.assertEqual(len(self.sources), 1)
        self.assertEqual(self.sources.get("3C 273"), self.source1)
        self.sources.add(self.source2)
        self.sources.drop_active()
        self.assertEqual(len(self.sources), 1)
        self.assertEqual(self.sources.get("3C 286"), self.source2)

    def test_serialization(self) -> None:
        self.sources.add(self.source1)
        self.sources.add(self.source2)
        data = self.sources.to_dict()
        self.assertIn("items", data)
        self.assertEqual(set(data["items"].keys()), {"3C 273", "3C 286"})
        self.assertEqual(data["items"]["3C 273"]["name"], "3C 273")
        self.assertFalse(data["items"]["3C 286"]["isactive"])
        new_sources = Sources.from_dict(data)
        self.assertEqual(new_sources.get("3C 273"), self.source1)
        self.assertEqual(new_sources.get("3C 286"), self.source2)

    def test_clone(self) -> None:
        self.sources.add(self.source1)
        clone = self.sources.clone()
        self.assertEqual(len(clone), 1)
        clone.create_source(name="New Source")
        self.assertEqual(len(self.sources), 1)
        self.assertEqual(len(clone), 2)

    def test_equality(self) -> None:
        other = Sources()
        other.add(Source(name="3C 273", ra_h=12.0, ra_m=29.0, ra_s=6.7, de_d=2.0, flux_table={1420.0: 45.0}))
        self.sources.add(self.source1)
        self.assertEqual(other, self.sources)
        other.add(self.source2)
        self.assertNotEqual(other, self.sources)

if __name__ == "__main__":
    unittest.main()