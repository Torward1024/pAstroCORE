import os
import sys
from pathlib import Path
import unittest
import pandas as pd
import plotly.express as px

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from unit_modeller.base.UV import UV
from common.utils.logging_setup import setup_logging

class TestUVVisualization(unittest.TestCase):
    def setUp(self):
        # Настраиваем логгер для вывода в консоль
        self.logger = setup_logging(log_file=None)
        self.uv = UV(code="m87_test", name="M87 UV Coverage")
        self.uv._use_logging = True
        self.uv._logger = self.logger

    def test_load_and_visualize_m87(self):
        # Путь к файлу
        file_path = Path(__file__).parent / "M87_colid_4sat_tst_W10.txt"
        
        # Проверяем, что файл существует
        self.assertTrue(file_path.exists(), f"Файл {file_path} не найден")

        # Маппинг: Baseline (1), U [ED] (3), V [ED] (4)
        column_mapping = {'u': 3, 'v': 4}
        baseline_col = 1
        frequency = 0.0
        time = 0.0
        header_lines = 1
        nrows = None

        # Загружаем данные
        self.uv.load_from_file(str(file_path), column_mapping, frequency=frequency, time=time, baseline_col=baseline_col, header_lines=header_lines, nrows=nrows)

        # Проверяем загрузку
        self.assertGreater(len(self.uv.data), 0, "Данные не загружены")
#        self.assertEqual(len(self.uv.data), nrows, f"Ожидалось {nrows} строк, получено {len(self.uv.data)}")

        # Используем self.uv.data напрямую
        data = self.uv.data
        data = data[data['baseline'].isin(['1-2', '2-3'])]
        
        # Отладочный вывод
        print("Первые 5 строк данных:")
        print(data[['u', 'v', 'baseline']].head())

        # Scatter-график с Plotly
        fig = px.scatter(data, x='u', y='v', color='baseline', 
                         title='UV Coverage for M87_colid_4sat_tst_W10',
                         labels={'u': 'U [ED]', 'v': 'V [ED]'},
                         hover_data=['baseline'])

        # Настройка графика
        fig.update_traces(marker=dict(size=3))
        fig.update_layout(showlegend=True, width=800, height=600)

        # Показываем график
        fig.show()

if __name__ == '__main__':
    unittest.main()