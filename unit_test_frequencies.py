# tests/test_frequencies.py
import unittest
from base.frequencies import IF, Frequencies, VALID_POLARIZATIONS, C_MHZ_CM

class TestIF(unittest.TestCase):
    def setUp(self):
        """Инициализация тестового объекта IF"""
        self.if_obj = IF(freq=1000.0, bandwidth=16.0, polarization="RCP", isactive=True)

    def test_init_valid(self):
        """Тест корректной инициализации IF"""
        self.assertEqual(self.if_obj.get_frequency(), 1000.0)
        self.assertEqual(self.if_obj.get_bandwidth(), 16.0)
        self.assertEqual(self.if_obj.get_polarization(), ["RCP"])
        self.assertTrue(self.if_obj.isactive)

    def test_init_invalid_polarization(self):
        """Тест инициализации с некорректной поляризацией"""
        with self.assertRaises(ValueError):
            IF(freq=1000.0, bandwidth=16.0, polarization="INVALID")

    def test_init_negative_freq(self):
        """Тест инициализации с отрицательной частотой"""
        with self.assertRaises(ValueError):
            IF(freq=-1000.0, bandwidth=16.0)

    def test_set_frequency_wavelength(self):
        """Тест установки частоты через длину волны"""
        self.if_obj.set_frequency_wavelength(29.9792458)  # соответствует 1000 MHz
        self.assertAlmostEqual(self.if_obj.get_frequency(), 1000.0, places=5)

    def test_get_frequency_wavelength(self):
        """Тест расчета длины волны"""
        wavelength = self.if_obj.get_frequency_wavelength()
        self.assertAlmostEqual(wavelength, C_MHZ_CM / 1000.0, places=5)

    def test_activate_deactivate(self):
        """Тест активации и деактивации"""
        self.if_obj.deactivate()
        self.assertFalse(self.if_obj.isactive)
        self.if_obj.activate()
        self.assertTrue(self.if_obj.isactive)

    def test_to_dict_from_dict(self):
        """Тест сериализации и десериализации"""
        if_dict = self.if_obj.to_dict()
        new_if = IF.from_dict(if_dict)
        self.assertEqual(new_if.get_frequency(), 1000.0)
        self.assertEqual(new_if.get_polarization(), ["RCP"])

class TestFrequencies(unittest.TestCase):
    def setUp(self):
        """Инициализация тестового объекта Frequencies"""
        self.freqs = Frequencies()
        self.if1 = IF(freq=1000.0, bandwidth=16.0, polarization="RCP")
        self.if2 = IF(freq=1020.0, bandwidth=16.0, polarization="LCP")
        self.freqs.add_IF(self.if1)
        self.freqs.add_IF(self.if2)

    def test_add_IF(self):
        """Тест добавления IF"""
        self.assertEqual(len(self.freqs), 2)
        self.assertEqual(self.freqs.get_frequencies(), [1000.0, 1020.0])

    def test_create_IF_overlap(self):
        """Тест создания IF с перекрытием частот"""
        with self.assertRaises(ValueError):
            self.freqs.create_IF(freq=1008.0, bandwidth=16.0)  # Перекрытие с 1000-1016

    def test_insert_IF(self):
        """Тест вставки IF по индексу"""
        new_if = IF(freq=1040.0, bandwidth=16.0)
        self.freqs.insert_IF(1, new_if)
        self.assertEqual(self.freqs.get_frequencies(), [1000.0, 1040.0, 1020.0])

    def test_remove_IF(self):
        """Тест удаления IF"""
        self.freqs.remove_IF(0)
        self.assertEqual(len(self.freqs), 1)
        self.assertEqual(self.freqs.get_frequencies(), [1020.0])

    def test_activate_deactivate_IF(self):
        """Тест активации/деактивации IF по индексу"""
        self.freqs.deactivate_IF(0)
        self.assertFalse(self.freqs.get_by_index(0).isactive)
        self.freqs.activate_IF(0)
        self.assertTrue(self.freqs.get_by_index(0).isactive)

    def test_drop_active(self):
        """Тест удаления активных IF"""
        self.freqs.deactivate_IF(1)
        self.freqs.drop_active()
        self.assertEqual(len(self.freqs), 1)
        self.assertEqual(self.freqs.get_frequencies(), [1020.0])

    def test_to_dict_from_dict(self):
        """Тест сериализации и десериализации Frequencies"""
        freqs_dict = self.freqs.to_dict()
        new_freqs = Frequencies.from_dict(freqs_dict)
        self.assertEqual(len(new_freqs), 2)
        self.assertEqual(new_freqs.get_frequencies(), [1000.0, 1020.0])

if __name__ == "__main__":
    unittest.main()