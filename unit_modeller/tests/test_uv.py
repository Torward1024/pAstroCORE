import os
import sys
from pathlib import Path
import unittest
import pandas as pd
import numpy as np

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from unit_modeller.base.UV import UV
from common.utils.logging_setup import setup_logging

class TestUV(unittest.TestCase):
    def setUp(self):
        self.logger = setup_logging(log_file=None)
        self.uv = UV(code="test_uv", name="Test UV")
        self.uv._use_logging = True
        self.uv._logger = self.logger
        self.file_path = Path(__file__).parent / "M87_colid_4sat_tst_W10.txt"
        self.assertTrue(self.file_path.exists(), f"Файл {self.file_path} не найден")

    def test_init(self):
        """Тест инициализации UV."""
        self.assertEqual(self.uv.code, "test_uv")
        self.assertEqual(self.uv.name, "Test UV")
        self.assertTrue(self.uv._use_logging)
        self.assertIsInstance(self.uv.data, pd.DataFrame)
        self.assertListEqual(list(self.uv.data.columns), 
                            ['frequency', 'time', 'baseline', 'u', 'v', 'w', 'vis_real', 'vis_imag'])
        self.assertEqual(len(self.uv.data), 0)

    def test_load_required_fields(self):
        """Тест загрузки только u, v."""
        column_mapping = {'u': 3, 'v': 4}
        self.uv.load_from_file(str(self.file_path), column_mapping, frequency=1.4e9, time=0.0, header_lines=1, nrows=100)
        
        self.assertEqual(len(self.uv.data), 100)
        self.assertListEqual(list(self.uv.data.columns), 
                            ['u', 'v', 'baseline', 'w', 'frequency', 'time', 'vis_real', 'vis_imag'])
        self.assertTrue(self.uv.data['u'].dtype == float)
        self.assertTrue(self.uv.data['v'].dtype == float)
        self.assertTrue(self.uv.data['baseline'].dtype == object)
        self.assertTrue(self.uv.data['w'].dtype == float)
        self.assertTrue(self.uv.data['frequency'].dtype == float)
        self.assertTrue(self.uv.data['time'].dtype == float)
        self.assertTrue((self.uv.data['baseline'] == 'default').all())
        self.assertAlmostEqual(self.uv.data['frequency'].iloc[0], 1.4e9)
        self.assertAlmostEqual(self.uv.data['time'].iloc[0], 0.0)
        self.assertAlmostEqual(self.uv.data['w'].iloc[0], 0.0)
        self.assertTrue(self.uv.data['vis_real'].isna().all())
        self.assertTrue(self.uv.data['vis_imag'].isna().all())

    def test_load_with_baseline(self):
        """Тест загрузки с baseline."""
        column_mapping = {'u': 3, 'v': 4}
        self.uv.load_from_file(str(self.file_path), column_mapping, frequency=1.4e9, time=0.0, baseline_col=1, header_lines=1, nrows=100)
        
        self.assertEqual(len(self.uv.data), 100)
        self.assertListEqual(list(self.uv.data.columns), 
                            ['baseline', 'u', 'v', 'w', 'frequency', 'time', 'vis_real', 'vis_imag'])
        self.assertTrue(set(self.uv.data['baseline']).issubset({'1-2', '1-3', '1-4', '2-3', '2-4', '3-4'}))
        self.assertAlmostEqual(self.uv.data['u'].iloc[0], -0.773538, places=6)
        self.assertAlmostEqual(self.uv.data['v'].iloc[0], 0.157361, places=6)
        self.assertEqual(self.uv.data['baseline'].iloc[0], '1-2')

    def test_load_full_file(self):
        """Тест загрузки всего файла."""
        column_mapping = {'u': 3, 'v': 4}
        self.uv.load_from_file(str(self.file_path), column_mapping, frequency=1.4e9, time=0.0, baseline_col=1, header_lines=1, nrows=None)
        
        self.assertEqual(len(self.uv.data), 259200)
        self.assertTrue(set(self.uv.data['baseline']).issubset({'1-2', '1-3', '1-4', '2-3', '2-4', '3-4'}))

    def test_load_missing_required(self):
        """Тест ошибки при отсутствии u или v."""
        column_mapping = {'u': 3}
        with self.assertRaises(ValueError):
            self.uv.load_from_file(str(self.file_path), column_mapping, frequency=1.4e9, time=0.0, header_lines=1)

    def test_load_invalid_types(self):
        """Тест ошибки при неверных типах."""
        column_mapping = {'u': 1, 'v': 4}  # u на baseline (строки)
        with self.assertRaises(ValueError):
            self.uv.load_from_file(str(self.file_path), column_mapping, frequency=1.4e9, time=0.0, header_lines=1, nrows=100)

    def test_load_file_not_found(self):
        """Тест ошибки при отсутствии файла."""
        column_mapping = {'u': 3, 'v': 4}
        with self.assertRaises(FileNotFoundError):
            self.uv.load_from_file("non_existent.txt", column_mapping, frequency=1.4e9, time=0.0, header_lines=1)

    def test_get_numpy_data(self):
        """Тест получения numpy массива."""
        column_mapping = {'u': 3, 'v': 4}
        self.uv.load_from_file(str(self.file_path), column_mapping, frequency=1.4e9, time=0.0, header_lines=1, nrows=100)
        
        numpy_data = self.uv.get_numpy_data()
        self.assertIsInstance(numpy_data, np.ndarray)
        self.assertEqual(numpy_data.shape, (100, 3))
        self.assertAlmostEqual(numpy_data[0, 0], -0.773538, places=6)
        self.assertAlmostEqual(numpy_data[0, 1], 0.157361, places=6)
        self.assertAlmostEqual(numpy_data[0, 2], 0.0, places=6)

    def test_to_dict_from_dict(self):
        """Тест сериализации и десериализации."""
        column_mapping = {'u': 3, 'v': 4}
        self.uv.load_from_file(str(self.file_path), column_mapping, frequency=1.4e9, time=0.0, baseline_col=1, header_lines=1, nrows=100)
        
        uv_dict = self.uv.to_dict()
        self.assertEqual(uv_dict['code'], "test_uv")
        self.assertEqual(uv_dict['name'], "Test UV")
        self.assertEqual(len(uv_dict['data']), 100)
        self.assertEqual(uv_dict['data'][0]['baseline'], '1-2')
        self.assertAlmostEqual(uv_dict['data'][0]['u'], -0.773538, places=6)

        new_uv = UV.from_dict(uv_dict)
        self.assertEqual(new_uv.code, self.uv.code)
        self.assertEqual(new_uv.name, self.uv.name)
        self.assertEqual(len(new_uv.data), len(self.uv.data))
        pd.testing.assert_frame_equal(new_uv.data, self.uv.data)

    def test_logging_enabled(self):
        """Тест логирования."""
        column_mapping = {'u': 3, 'v': 4}
        with self.assertLogs('root', level='INFO') as cm:
            self.uv.load_from_file(str(self.file_path), column_mapping, frequency=1.4e9, time=0.0, header_lines=1, nrows=100)
        self.assertTrue(any("Loaded 100 UV points" in msg for msg in cm.output))

    def test_logging_disabled(self):
        """Тест отключения логирования."""
        self.uv._use_logging = False
        column_mapping = {'u': 3, 'v': 4}
        with self.assertNoLogs('root', level='INFO'):
            self.uv.load_from_file(str(self.file_path), column_mapping, frequency=1.4e9, time=0.0, header_lines=1, nrows=100)

if __name__ == '__main__':
    unittest.main()