import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from common.base.baseentity import BaseEntity
from common.utils.logging_setup import logger

class UV(BaseEntity):
    """
    Класс для работы с UV-покрытием.
    Хранит данные о UVW-точках с учетом частоты, времени и базовых линий.
    """
    code: str
    name: str
    data: pd.DataFrame = None

    def __init__(self, *, code: str, name: str, **kwargs):
        super().__init__(code=code, name=name, **kwargs)
        self._use_logging = True
        self.data = pd.DataFrame(columns=['frequency', 'time', 'baseline', 'u', 'v', 'w', 'vis_real', 'vis_imag'])
        if self._use_logging:
            logger.info(f"Initialized UV instance with code={code}, name={name}")

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Переопределяем установку атрибутов, чтобы контролировать логирование.
        """
        if name == 'data' and not getattr(self, '_use_logging', True):
            object.__setattr__(self, name, value)  # Устанавливаем без логирования
        else:
            super().__setattr__(name, value)  # Используем логирование BaseEntity

    def load_from_file(self, file_path: str, column_mapping: Dict[str, int], frequency: Optional[float] = None, time: Optional[float] = None, baseline_col: Optional[int] = None, header_lines: int = 0, nrows: Optional[int] = None) -> None:
        """
        Загрузка данных из текстового файла с разделителями (пробелы или табуляция).
        
        :param file_path: Путь к файлу.
        :param column_mapping: Словарь с маппингом колонок ({'u': idx, 'v': idx}).
        :param frequency: Частота (если не в файле).
        :param time: Время (если не в файле).
        :param baseline_col: Индекс колонки с baseline (если есть).
        :param header_lines: Количество строк заголовка для пропуска (0 если заголовка нет).
        :param nrows: Количество строк для чтения (если указано).
        """
        if 'u' not in column_mapping or 'v' not in column_mapping:
            raise ValueError("Обязательные поля 'u' и 'v' должны быть указаны в column_mapping")

        # Формируем usecols
        usecols = [column_mapping['u'], column_mapping['v']]
        if baseline_col is not None:
            usecols.append(baseline_col)
        usecols = sorted(list(set(usecols)))  # Убираем дубликаты и сортируем

        # Читаем файл
        df = pd.read_csv(file_path, sep=r'\s+', header=None, skiprows=header_lines, usecols=usecols, nrows=nrows)

        # Отладочный вывод сырых данных
        # if self._use_logging:
        #     logger.info(f"Raw data head:\n{df.head().to_string()}")

        # Формируем словарь переименования столбцов
        rename_map = {}
        for i, col_idx in enumerate(usecols):
            if col_idx == column_mapping['u']:
                rename_map[i] = 'u'
            elif col_idx == column_mapping['v']:
                rename_map[i] = 'v'
            elif col_idx == baseline_col:
                rename_map[i] = 'baseline'
            else:
                rename_map[i] = f'col_{col_idx}'

        # Переименовываем столбцы
        df.columns = [rename_map[i] for i in range(len(usecols))]

        # Отладочный вывод столбцов
        if self._use_logging:
            logger.info(f"Loaded columns: {df.columns.tolist()}")

        # Проверка типов данных
        try:
            if 'u' in df.columns:
                pd.to_numeric(df['u'], errors='raise')
            if 'v' in df.columns:
                pd.to_numeric(df['v'], errors='raise')
            if 'baseline' in df.columns:
                df['baseline'] = df['baseline'].astype(str)
        except ValueError as e:
            if self._use_logging:
                logger.error(f"Ошибка в типах данных: {e}")
            raise ValueError(f"Ошибка в типах данных: {e}")

        # Заполняем baseline, если не задан
        if 'baseline' not in df.columns:
            df['baseline'] = 'default'

        # Заполняем w
        df['w'] = 0.0

        # Добавляем frequency и time
        df['frequency'] = frequency if frequency is not None else 0.0
        df['time'] = time if time is not None else 0.0

        # Проверяем обязательные колонки
        required_cols = ['frequency', 'time', 'baseline', 'u', 'v', 'w']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Отсутствует обязательная колонка '{col}'")

        # Приводим типы
        df = df.astype({
            'frequency': float,
            'time': float,
            'baseline': str,
            'u': float,
            'v': float,
            'w': float
        })

        # Добавляем vis_real и vis_imag
        df['vis_real'] = np.nan
        df['vis_imag'] = np.nan

        # Сохраняем данные
        if self.data.empty:
            self.data = df
        else:
            self.data = pd.concat([self.data, df], ignore_index=True)
        
        if self._use_logging:
            logger.info(f"Loaded {len(df)} UV points from file {file_path}")

    def get_numpy_data(self) -> np.ndarray:
        """
        Возвращает UVW-точки в виде NumPy массива.
        
        :return: Массив с колонками u, v, w.
        """
        return self.data[['u', 'v', 'w']].to_numpy()

    def to_dict(self) -> Dict[str, Any]:
        """
        Сериализация объекта в словарь.
        """
        data_dict = super().to_dict()
        data_dict['data'] = self.data.to_dict('records')
        return data_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UV':
        """
        Создание объекта из словаря.
        """
        data_copy = data.copy()
        data_copy.pop('type', None)
        instance = cls(code=data_copy.pop('code'), name=data_copy.pop('name'), **{k: v for k, v in data_copy.items() if k != 'data'})
        if 'data' in data:
            instance.data = pd.DataFrame(data['data'])
        return instance