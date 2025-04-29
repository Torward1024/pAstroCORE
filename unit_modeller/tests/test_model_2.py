import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

import unittest
import numpy as np
import os
from unit_modeller.base.model import Model, crescent_function
from pastrocore.base.sources import Source
from pastrocore.base.frequencies import IF
import matplotlib.pyplot as plt

class TestModel(unittest.TestCase):
    """Юнит-тесты для класса Model."""

    def setUp(self):
        """Инициализация тестового окружения."""
        self.source = Source(name="TestSource")
        self.frequency = IF(name="TestIF", frequency=1000.0, bandwidth=16.0)
        self.model = Model(code="TEST", name="TestModel", source=self.source, 
                          frequency=self.frequency, vis_width=40.0, resolution=256)

    def test_initialize_from_function(self):
        """Тест инициализации модели из функции и визуализации."""
        def brightness_function(x, y):
            params = [{"A": 1, "r0": 10, "sigma": 2, "t0": 0, "n": 2}]
            return crescent_function(x, y, params)
        
        self.model.initialize_from_function(brightness_function, phase_noise=0.1)
        self.assertIsNotNone(self.model.data)
        self.assertEqual(self.model.data.shape, (256, 256))
        
        # Визуализация амплитуды и фазы
        self.model.visualize(show_phase=False)  # Амплитуда
        self.model.visualize(show_phase=True)   # Фаза

    def test_load_from_file(self):
        file_path = "d:\\prog\\python\\pAstroCORE\\unit_modeller\\tests\\CrescentR20W5.dat"
        if os.path.exists(file_path):
            self.model.load_from_file(file_path)
            self.assertIsNotNone(self.model.data)  # Проверка, что данные загружены
            self.assertEqual(self.model.data.shape, (self.model.resolution, self.model.resolution))  # Проверка формы
            self.model.visualize(show_phase=False)
        else:
            print(f"File {file_path} not found, skipping load_from_file test")

if __name__ == "__main__":
    unittest.main()