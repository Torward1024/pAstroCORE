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
from astropy.time import Time

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
                "code": "ALMA", "name": "ALMA", "x": 2225061.164, "y": -5440057.37, "z": -2481681.15,
                "vx": 0.0, "vy": 0.0, "vz": 0.0, "diameter": 12.0, "sefd_table": {86e3: 100.0},
                "elevation_range": (5.0, 90.0), "azimuth_range": (0.0, 360.0), "mount_type": "AZIM"
            },
            {
                "code": "APEX", "name": "APEX", "x": 2225039.53, "y": -5441197.63, "z": -2479303.36,
                "vx": 0.0, "vy": 0.0, "vz": 0.0, "diameter": 12.0, "sefd_table": {86e3: 120.0},
                "elevation_range": (5.0, 90.0), "azimuth_range": (0.0, 360.0), "mount_type": "AZIM"
            },
            {
                "code": "SMT", "name": "SMT", "x": -1828796.2, "y": -5054406.8, "z": 3427865.2,
                "vx": 0.0, "vy": 0.0, "vz": 0.0, "diameter": 10.0, "sefd_table": {86e3: 150.0},
                "elevation_range": (5.0, 90.0), "azimuth_range": (0.0, 360.0), "mount_type": "AZIM"
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
        frequency_attributes = {"set_frequency": {"freq": 86e3}, "set_bandwidth": {"bandwidth": 4e3}}
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

        mean_time = Time("2025-03-28T12:00:00")
        source = observation.get_sources().get_by_index(0)
        visibility = self.manipulator._calculator._compute_visibility_at_time(source, telescopes.get_active_telescopes(), mean_time)
        logger.info(f"Visibility at {mean_time.isot}: {visibility}")

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
        freq = 86e9
        logger.debug(f"UV data structure: {uv_data}")
        for scan_idx, scan_data in uv_data.items():
            uv_points = scan_data["uv_points"][freq]
            logger.debug(f"UV points for scan {scan_idx}: {uv_points}")
            if "times" in scan_data:
                for uv_list in uv_points:
                    if isinstance(uv_list, (list, tuple)) and len(uv_list) == 2:  # Теперь точно 2 элемента
                        u, v = uv_list
                        u_points.append(float(u))
                        v_points.append(float(v))
                    else:
                        logger.warning(f"Unexpected uv_list format: {uv_list}")
            else:
                for uv_tuple in uv_points:
                    if isinstance(uv_tuple, (list, tuple)) and len(uv_tuple) == 2:
                        u, v = uv_tuple
                        u_points.append(float(u))
                        v_points.append(float(v))
                    else:
                        logger.warning(f"Unexpected uv_tuple format: {uv_tuple}")

    def tearDown(self):
        """Очистка после теста"""
        self.manipulator = None
        self.project = None
        logger.info("Tore down test environment")

if __name__ == "__main__":
    unittest.main()