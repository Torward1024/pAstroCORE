import unittest
from base.project import Project
from base.observation import Observation
from base.telescopes import Telescope
from base.frequencies import IF
from base.sources import Source
from base.scans import Scan
from super.manipulator import DefaultManipulator
from utils.logging_setup import logger
import numpy as np
import matplotlib.pyplot as plt
from astropy.time import Time

class TestVLBIM87Observation(unittest.TestCase):
    def setUp(self):
        """Инициализация теста: создание проекта и манипулятора"""
        self.manipulator = DefaultManipulator()
        self.project = Project(name="M87_EHT_VLBI")
        self.manipulator.set_project(self.project)
        logger.info("Set up test environment for M87 VLBI observation")

    def test_configure_and_calculate_uv_coverage(self):
        """Тест конфигурации наблюдения M87 и расчета (u,v)-покрытия через Manipulator"""
        # 1. Добавление пустого наблюдения в проект
        config_attrs = {
            "add_observation": Observation(observation_code="M87_VLBI_2025", observation_type="VLBI")
        }
        success = self.manipulator.process_request("configure", "project", config_attrs)
        self.assertTrue(success, "Failed to add observation")

        # 2. Конфигурация телескопов EHT
        eht_telescopes = [
            {"name": "ALMA", "code": "ALMA", "coordinates": (-2230000, -5440000, -2475000), "diameter": 12.0},
            {"name": "APEX", "code": "APEX", "coordinates": (-2225000, -5441000, -2479000), "diameter": 12.0},
            {"name": "JCMT", "code": "JCMT", "coordinates": (-5466000, -2493000, 2151000), "diameter": 15.0},
            {"name": "SMA", "code": "SMA", "coordinates": (-5466000, -2493000, 2151000), "diameter": 6.0},
            {"name": "LMT", "code": "LMT", "coordinates": (-768700, -5989000, 2063000), "diameter": 50.0},
            {"name": "SPT", "code": "SPT", "coordinates": (0, 0, -6356000), "diameter": 10.0},
            {"name": "PV", "code": "PV", "coordinates": (5089000, -301700, 3825000), "diameter": 30.0},
            {"name": "SMT", "code": "SMT", "coordinates": (-1829000, -5054000, 3426000), "diameter": 10.0}
        ]
        for i, tel in enumerate(eht_telescopes):
            # Добавляем пустой телескоп
            config_attrs = {
                "observation_index": 0,
                "add_telescope": Telescope(code=f"TEMP_{i}")
            }
            success = self.manipulator.process_request("configure", "project", config_attrs)
            self.assertTrue(success, f"Failed to add temporary telescope at index {i}")

            # Настраиваем телескоп
            config_attrs = {
                "observation_index": 0,
                "telescope_index": i,
                "set_telescope": {
                    "code": tel["code"],
                    "name": tel["name"],
                    "x": tel["coordinates"][0],
                    "y": tel["coordinates"][1],
                    "z": tel["coordinates"][2],
                    "vx": 0.0,
                    "vy": 0.0,
                    "vz": 0.0,
                    "diameter": tel["diameter"]
                }
            }
            success = self.manipulator.process_request("configure", "project", config_attrs)
            self.assertTrue(success, f"Failed to configure telescope {tel['code']}")

        # 3. Конфигурация источника M87
        config_attrs = {
            "observation_index": 0,
            "add_source": Source()  # Пустой источник
        }
        success = self.manipulator.process_request("configure", "project", config_attrs)
        self.assertTrue(success, "Failed to add source")

        config_attrs = {
            "observation_index": 0,
            "source_index": 0,
            "set_source": {
                "name": "M87",
                "ra_h": 12,
                "ra_m": 30,
                "ra_s": 49.42,
                "dec_deg": 12,
                "dec_m": 23,
                "dec_s": 28.0
            }
        }
        success = self.manipulator.process_request("configure", "project", config_attrs)
        self.assertTrue(success, "Failed to configure source M87")

        # 4. Конфигурация частот
        config_attrs = {
            "observation_index": 0,
            "add_IF": IF()  # Пустой IF
        }
        success = self.manipulator.process_request("configure", "project", config_attrs)
        self.assertTrue(success, "Failed to add IF")

        config_attrs = {
            "observation_index": 0,
            "if_index": 0,
            "set_frequency": {"freq": 230.0, "bw": 4.0}
        }
        success = self.manipulator.process_request("configure", "project", config_attrs)
        self.assertTrue(success, "Failed to configure frequency")

        # 5. Конфигурация скана (1 час наблюдения)
        start_time = Time("2025-04-01T00:00:00").unix
        config_attrs = {
            "observation_index": 0,
            "add_scan": Scan()  # Пустой скан
        }
        success = self.manipulator.process_request("configure", "project", config_attrs)
        self.assertTrue(success, "Failed to add scan")

        config_attrs = {
            "observation_index": 0,
            "scan_index": 0,
            "set_scan": {
                "start": start_time,
                "duration": 3600.0,
                "source_index": 0,
                "telescope_indices": list(range(len(eht_telescopes))),
                "frequency_indices": [0]
            }
        }
        success = self.manipulator.process_request("configure", "project", config_attrs)
        self.assertTrue(success, "Failed to configure scan")

        # 6. Проверка конфигурации через Inspector
        inspect_attrs = {
            "observation_index": 0,
            "get_observation_code": None,
            "get_sources": None,
            "get_telescopes": None,
            "get_scans": None
        }
        result = self.manipulator.process_request("inspect", "project", inspect_attrs)
        self.assertEqual(result["get_observation_code"], "M87_VLBI_2025", "Observation code mismatch")
        self.assertEqual(result["get_sources"].get_source(0).get_name(), "M87", "Source name mismatch")
        self.assertEqual(len(result["get_telescopes"]), len(eht_telescopes), "Telescope count mismatch")
        self.assertEqual(result["get_scans"].get_scan(0).get_duration(), 3600.0, "Scan duration mismatch")

        # 7. Расчет (u,v)-покрытия через Calculator
        calc_attrs = {
            "type": "uv_coverage",
            "time_step": 60.0,
            "freq_idx": 0
        }
        uv_result = self.manipulator.process_request("calculate", "project", calc_attrs)
        self.assertIn("M87_VLBI_2025", uv_result, "UV coverage calculation failed")

        # 8. Визуализация результата
        uv_data = uv_result["M87_VLBI_2025"]
        u_coords, v_coords = [], []
        frequency = 230.0 * 1e9  # GHz -> Hz
        for scan_idx, scan_data in uv_data.items():
            uv_points = scan_data["uv_points"][frequency]
            u, v = zip(*uv_points)
            u_coords.extend(u)
            v_coords.extend(v)

        plt.figure(figsize=(10, 10))
        plt.scatter(u_coords, v_coords, s=1, c="blue", label="UV Coverage")
        plt.scatter(-np.array(u_coords), -np.array(v_coords), s=1, c="blue")  # Симметрия
        plt.xlabel("u (wavelengths)")
        plt.ylabel("v (wavelengths)")
        plt.title("UV Coverage for M87 VLBI Observation with EHT")
        plt.legend()
        plt.grid(True)
        plt.axis("equal")
        plt.savefig("m87_uv_coverage.png")
        plt.close()
        logger.info("UV coverage plot saved as 'm87_uv_coverage.png'")

    def tearDown(self):
        """Очистка после теста"""
        self.manipulator = None
        self.project = None
        logger.info("Tear down test environment")

if __name__ == "__main__":
    unittest.main()