import unittest
import matplotlib.pyplot as plt
from base.sources import Source, Sources
from base.telescopes import Telescope, Telescopes
from base.frequencies import IF, Frequencies
from base.scans import Scan, Scans
from base.observation import Observation
from base.project import Project
from super.manipulator import DefaultManipulator
from utils.logging_setup import logger

class TestEHTObservation(unittest.TestCase):
    def setUp(self):
        """Инициализация Manipulator и базовых данных"""
        self.manipulator = DefaultManipulator()
        self.project = Project(name="EHT_M87_PROJECT")
        self.manipulator.set_project(self.project)
        logger.info("Set up test environment with Manipulator and Project")

    def test_eht_observation_cycle(self):
        """Тест полного цикла: настройка, вычисление (u,v), визуализация"""
        # 1. Настройка источника M87 через Manipulator
        m87_attributes = {
            "set_source": {
                "name": "M87",
                "ra_h": 12, "ra_m": 30, "ra_s": 49.42,
                "de_d": 12, "de_m": 23, "de_s": 28.0
            },
            "set_flux": {"frequency": 86e3, "flux": 1.2}  # 86 GHz в МГц
        }
        m87_source = Source()
        self.manipulator.process_request("configure", "source", m87_attributes, m87_source)
        sources = Sources([m87_source])

        # 2. Настройка телескопов EHT через Manipulator
        telescope_data = [
            {
                "code": "ALMA", "name": "ALMA", "x": -2230000.0, "y": -5440000.0, "z": -2475000.0,
                "vx": 0.0, "vy": 0.0, "vz": 0.0, "diameter": 12.0, "sefd_table": {86e3: 100.0}
            },
            {
                "code": "APEX", "name": "APEX", "x": -2225000.0, "y": -5441000.0, "z": -2476000.0,
                "vx": 0.0, "vy": 0.0, "vz": 0.0, "diameter": 12.0, "sefd_table": {86e3: 120.0}
            },
            {
                "code": "SMT", "name": "SMT", "x": -1828000.0, "y": -5054000.0, "z": 3426000.0,
                "vx": 0.0, "vy": 0.0, "vz": 0.0, "diameter": 10.0, "sefd_table": {86e3: 150.0}
            },
        ]
        telescopes = Telescopes()
        configured_telescopes = []
        for tel_data in telescope_data:
            tel = Telescope()
            self.manipulator.process_request("configure", "telescope", {"set_telescope": tel_data}, tel)
            configured_telescopes.append(tel)
        for tel in configured_telescopes:
            telescopes.add_telescope(tel)

        # 3. Настройка частоты (86 GHz в МГц)
        frequency_attributes = {"set_frequency": {"freq": 86e3}, "set_bandwidth": {"bandwidth": 4e9}}
        frequency = IF()
        self.manipulator.process_request("configure", "if", frequency_attributes, frequency)
        frequencies = Frequencies([frequency])

        # 4. Настройка сканирования (1 час наблюдения, начиная с 2025-03-28T00:00:00 UTC)
        scan_attributes = {
            "set_scan": {
                "start": 1740614400.0,  # Unix timestamp для 2025-03-28T00:00:00 UTC
                "duration": 86400.0,     # 1 час
                "source_index": 0,
                "telescope_indices": [0, 1, 2],  # ALMA, APEX, SMT
                "frequency_indices": [0]
            }
        }
        scan = Scan()
        self.manipulator.process_request("configure", "scan", scan_attributes, scan)
        scans = Scans([scan])

        # 5. Создание наблюдения через Manipulator
        observation = Observation(observation_code="M87_OBS")
        obs_attributes = {
            "set_observation": {
                "observation_code": "M87_OBS",
                "sources": sources,
                "telescopes": telescopes,
                "frequencies": frequencies,
                "scans": scans,
                "observation_type": "VLBI",
                "isactive": True
            }
        }
        self.manipulator.process_request("configure", "observation", obs_attributes, observation)
        self.project.add_observation(observation)

        # 6. Вычисление (u,v)-покрытия через Manipulator
        calc_attributes = {
            "type": "uv_coverage",
            "time_step": 600.0,  # Шаг 10 минут
            "freq_idx": 0,
            "store_key": "uv_coverage_f0",
            "recalculate": True
        }
        uv_results = self.manipulator.process_request("calculate", "observation", calc_attributes, observation)
        self.assertTrue(uv_results, "UV calculation failed")

        # 7. Извлечение данных из observation._calculated_data
        calculated_data = observation.get_calculated_data_by_key("uv_coverage_f0")
        self.assertIn("data", calculated_data, "No 'data' in calculated results")
        uv_data = calculated_data["data"]

        # 8. Построение графика (u,v)-покрытия
        u_points = []
        v_points = []
        freq = 86e9  # Частота в Гц после преобразования в Calculator
        logger.debug(f"UV data structure: {uv_data}")  # Отладочный вывод структуры данных
        for scan_idx, scan_data in uv_data.items():
            uv_points = scan_data["uv_points"][freq]
            logger.debug(f"UV points for scan {scan_idx}: {uv_points}")
            if "times" in scan_data:
                # Обрабатываем случай, когда uv_points — список списков
                for uv_list in uv_points:
                    if isinstance(uv_list, (list, tuple)) and len(uv_list) == 2:
                        u, v = uv_list
                        u_points.append(u)
                        v_points.append(v)
                    else:
                        logger.warning(f"Unexpected uv_list format: {uv_list}")
            else:
                # Обрабатываем случай, когда uv_points — плоский список
                if isinstance(uv_points, (list, tuple)):
                    if len(uv_points) % 2 == 0:  # Проверяем, что длина чётная для парного распаковывания
                        for i in range(0, len(uv_points), 2):
                            u_points.append(uv_points[i])
                            v_points.append(uv_points[i + 1])
                    else:
                        logger.warning(f"UV points length is odd: {uv_points}")
                else:
                    logger.warning(f"Unexpected uv_points format: {uv_points}")

        plt.figure(figsize=(8, 8))
        plt.scatter(u_points, v_points, s=5, c="blue", label="UV Coverage")
        plt.scatter([-u for u in u_points], [-v for v in v_points], s=5, c="blue")  # Симметрия
        plt.xlabel("u (wavelengths)")
        plt.ylabel("v (wavelengths)")
        plt.title(f"UV Coverage for M87 Observation at 86 GHz")
        plt.grid(True)
        plt.legend()
        plt.axis("equal")
        plt.savefig("uv_coverage_m87.png")
        plt.close()

        logger.info("Generated UV coverage plot saved as 'uv_coverage_m87.png'")
        self.assertTrue(len(u_points) > 0, "No UV points calculated")

    def tearDown(self):
        """Очистка после теста"""
        self.manipulator = None
        self.project = None
        logger.info("Tore down test environment")

if __name__ == "__main__":
    unittest.main()