# base/telescope.py
from common.base.baseentity import BaseEntity
from common.base.basecontainer import BaseContainer
from common.utils.logging_setup import logger
import numpy as np
from pastrocore.base.sources import Source
from pastrocore.base.frequencies import IF

class Model(BaseEntity):
    """
    Класс, представляющий модель источника для телескопических наблюдений или симуляций.

    Атрибуты:
        code (str): Уникальный идентификатор модели.
        name (str): Читаемое имя модели.
        source (Source): Объект источника, представляющий астрономический объект.
        frequency (IF): Частота наблюдения или моделирования.
        vis_width (float): Ширина поля зрения.
        resolution (int, optional): Разрешение модели (размер сетки по одной оси).
        data (np.ndarray, optional): Двумерный массив комплексных чисел, представляющий данные модели.
    """
    code: str
    name: str
    source: Source
    frequency: IF
    vis_width: float
    resolution: int = None
    data: np.ndarray = None

    def __init__(self, **kwargs):
        """
        Инициализация модели с валидацией атрибутов.

        Args:
            **kwargs: Словарь с атрибутами модели (code, name, source, frequency, vis_width, resolution, data).

        Raises:
            ValueError: Если обязательный атрибут отсутствует или равен None.
            TypeError: Если data не является np.ndarray.
            ValueError: Если data не двумерный или имеет неправильную форму.
        """
        super().__init__(**kwargs)
        required_fields = ['code', 'name', 'source', 'frequency', 'vis_width']
        for field in required_fields:
            if getattr(self, field) is None:
                raise ValueError(f"Атрибут '{field}' обязателен и не может быть None")
        # Проверка data и resolution только если оба предоставлены
        if self.data is not None and self.resolution is not None:
            self._validate_data()

    def _validate_data(self):
        """
        Проверка и преобразование data в двумерный массив комплексных чисел с формой (resolution, resolution).

        Raises:
            TypeError: Если data не является np.ndarray.
            ValueError: Если data не двумерный или имеет неправильную форму.
        """
        if not isinstance(self.data, np.ndarray):
            raise TypeError("data должен быть типа numpy.ndarray")
        if self.data.ndim != 2:
            raise ValueError("data должен быть двумерным массивом")
        if self.data.shape != (self.resolution, self.resolution):
            raise ValueError(f"Форма data должна быть ({self.resolution}, {self.resolution}), получено {self.data.shape}")
        if not np.issubdtype(self.data.dtype, np.complexfloating):
            if np.issubdtype(self.data.dtype, np.floating):
                self.data = self.data.astype(np.complex128)
            else:
                raise ValueError("data должен содержать вещественные или комплексные числа")

    def load_from_file(self, file_path: str):
        """
        Загрузка данных из текстового файла.

        Файл может содержать один столбец (амплитуды) или два столбца (реальная и мнимая части).
        Разрешение вычисляется автоматически как квадратный корень из количества записей.

        Args:
            file_path (str): Путь к файлу.

        Raises:
            ValueError: Если файл имеет некорректное количество столбцов или данные не образуют квадрат.
        """
        try:
            data = np.loadtxt(file_path)
        except Exception as e:
            raise ValueError(f"Не удалось загрузить данные из файла: {str(e)}")

        # Определяем количество записей
        num_entries = data.shape[0] if data.ndim > 1 else len(data)
        
        # Вычисляем resolution как квадратный корень из числа записей
        resolution = int(num_entries ** 0.5)
        if resolution * resolution != num_entries:
            raise ValueError(f"Количество записей ({num_entries}) не является полным квадратом")
        
        # Устанавливаем resolution
        self.resolution = resolution

        # Обрабатываем данные
        if data.ndim == 1:
            # Один столбец: амплитуды
            self.data = data.reshape((self.resolution, self.resolution)).astype(np.complex128)
        elif data.ndim == 2 and data.shape[1] == 2:
            # Два столбца: реальная и мнимая части
            real = data[:, 0].reshape((self.resolution, self.resolution))
            imag = data[:, 1].reshape((self.resolution, self.resolution))
            self.data = real + 1j * imag
        else:
            raise ValueError("Файл должен содержать один или два столбца")

        self._validate_data()

class Models(BaseContainer[Model]):
    """
    Контейнер для хранения коллекции объектов Model.

    Наследуется от BaseContainer и параметризован типом Model.
    """
    def get_by_source_name(self, source_name: str) -> list[Model]:
        """
        Возвращает список моделей, у которых имя источника совпадает с указанным.

        Args:
            source_name (str): Имя источника для фильтрации.

        Returns:
            list[Model]: Список моделей, соответствующих указанному имени источника.

        Raises:
            AttributeError: Если атрибут 'source.name' отсутствует у моделей.
        """
        result = self.get_by_value({"source.name": source_name})
        logger.debug(f"Retrieved {len(result)} models with source name '{source_name}'")
        return result

    def get_by_frequency(self, frequency: float) -> list[Model]:
        """
        Возвращает список моделей, у которых частота совпадает с указанной.

        Args:
            frequency (float): Частота (значение атрибута frequency.frequency) для фильтрации.

        Returns:
            list[Model]: Список моделей, соответствующих указанным имени источника и частоте.

        Raises:
            AttributeError: Если атрибуты 'source.name' или 'frequency.frequency' отсутствуют у моделей.
        """
        result = self.get_by_value({"frequency.frequency": frequency})
        logger.debug(f"Retrieved {len(result)} models with frequency {frequency}")
        return result
    
