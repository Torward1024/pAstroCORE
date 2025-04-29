# base/telescope.py
from common.base.baseentity import BaseEntity
from common.base.basecontainer import BaseContainer
from common.utils.logging_setup import logger
import numpy as np
from pastrocore.base.sources import Source
from pastrocore.base.frequencies import IF
import matplotlib.pyplot as plt
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

    def initialize_from_function(self, brightness_function: callable, phase_noise: float = 0.0):
        """Инициализация данных модели с использованием функции распределения яркости.

        Args:
            brightness_function: Функция, возвращающая двумерный массив значений.
            phase_noise: Амплитуда случайного фазового шума (по умолчанию 0).
        """
        if self.resolution is None:
            raise ValueError("Resolution must be set before initializing from function")
        if self.vis_width is None:
            raise ValueError("vis_width must be set before initializing from function")
        
        # Генерация сетки координат
        x = np.linspace(-self.vis_width / 2, self.vis_width / 2, self.resolution)
        y = np.linspace(-self.vis_width / 2, self.vis_width / 2, self.resolution)
        X, Y = np.meshgrid(x, y)
        
        # Применение функции распределения яркости
        result = brightness_function(X, Y)
        
        # Проверка формы результата
        if result.shape != (self.resolution, self.resolution):
            raise ValueError(f"brightness_function must return an array of shape ({self.resolution}, {self.resolution})")
        
        # Преобразование в комплексные числа, если результат вещественный
        if np.isrealobj(result):
            data = result.astype(np.complex128)
        else:
            data = result
        
        # Добавление фазового шума, если указано
        if phase_noise > 0:
            noise = np.random.normal(0, phase_noise, data.shape)
            data = np.abs(data) * np.exp(1j * (np.angle(data) + noise))
        
        self.data = data
        self._validate_data()

    def visualize(self, show_phase: bool = False):
        """Визуализация модели в виде цветовой карты.

        Args:
            show_phase: Если True, отображается фаза, иначе амплитуда (по умолчанию False).
        """
        if self.data is None:
            raise ValueError("Data is not initialized")
        
        plt.figure(figsize=(8, 6))
        if show_phase:
            img = plt.imshow(np.angle(self.data), cmap='hsv', 
                            extent=[-self.vis_width/2, self.vis_width/2, -self.vis_width/2, self.vis_width/2])
            plt.title("Phase of the Model")
        else:
            img = plt.imshow(np.abs(self.data), cmap='viridis', 
                            extent=[-self.vis_width/2, self.vis_width/2, -self.vis_width/2, self.vis_width/2])
            plt.title("Amplitude of the Model")
        plt.colorbar(img, label="Phase (radians)" if show_phase else "Amplitude")
        plt.xlabel("X (Field of View)")
        plt.ylabel("Y (Field of View)")
        plt.show()

def crescent_function(x, y, params_list):
    """Функция распределения яркости в форме серпа.

    Args:
        x, y: Координатные сетки.
        params_list: Список словарей с параметрами серпа (A, r0, sigma, t0, n).

    Returns:
        Двумерный массив значений яркости.
    """
    r = np.sqrt(x**2 + y**2)
    t = np.arctan2(y, x)
    result = np.zeros_like(x, dtype=float)
    for params in params_list:
        A = params.get("A", 1)
        r0 = params["r0"]
        sigma = params["sigma"]
        t0 = params.get("t0", 0)
        n = params.get("n", 2)
        fr = A * np.exp(-((r - r0) / (2 * sigma))**2)
        ft = (np.sin((t - t0) / 2))**n
        result += fr * ft
    return result

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
    
