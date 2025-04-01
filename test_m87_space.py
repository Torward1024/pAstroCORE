import unittest
import matplotlib.pyplot as plt
from base.sources import Source, Sources
from base.telescopes import Telescope, SpaceTelescope, Telescopes
from base.frequencies import IF, Frequencies
from base.scans import Scan, Scans
from base.observation import Observation
from base.project import Project
from super.manipulator import DefaultManipulator
from utils.logging_setup import logger
import datetime
from datetime import timezone
import time
import os

class TestEHTObservationWithSpaceTelescope(unittest.TestCase):
    def setUp(self):
        """Инициализация Manipulator и базовых данных"""
        self.manipulator = DefaultManipulator()
        self.project = Project(name="EHT_M87_SPACE_PROJECT")
        self.manipulator.set_project(self.project)
        logger.info("Set up test environment with Manipulator and Project")

    def test_eht_observation_with_space_telescope(self):
        """Тест полного цикла с космическим телескопом: настройка, вычисление (u,v), визуализация"""
        # 1. Настройка источника M87
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

        # 2. Настройка телескопов (ALMA + космический телескоп)
        telescope_data = [
            {"code": "ALMA", "name": "ALMA", "x": 2225061.164, "y": -5440057.37, "z": -2481681.15,
             "vx": 0.0, "vy": 0.0, "vz": 0.0, "diameter": 12.0, "sefd_table": {86e3: 100.0},
             "elevation_range": (0.0, 90.0), "azimuth_range": (0.0, 360.0), "mount_type": "AZIM"},
            {"code": "APEX", "name": "APEX", "x": 2225039.53, "y": -5441197.63, "z": -2479303.36,
             "vx": 0.0, "vy": 0.0, "vz": 0.0, "diameter": 12.0, "sefd_table": {86e3: 120.0},
             "elevation_range": (0.0, 90.0), "azimuth_range": (0.0, 360.0), "mount_type": "AZIM"},
            {"code": "SMT", "name": "SMT", "x": -1828796.2, "y": -5054406.8, "z": 3427865.2,
             "vx": 0.0, "vy": 0.0, "vz": 0.0, "diameter": 10.0, "sefd_table": {86e3: 150.0},
             "elevation_range": (0.0, 90.0), "azimuth_range": (0.0, 360.0), "mount_type": "AZIM"},
        ]
        telescopes = Telescopes()
        for tel_data in telescope_data:
            tel = Telescope()
            self.manipulator.process_request("configure", "telescope", {"set_telescope": tel_data}, tel)
            telescopes.add_telescope(tel)

        # Добавляем космический телескоп с орбитальным файлом
        space_tel_attributes = {
            "set_telescope": {
                "code": "SPACE370",
                "use_kep": False,
                "name": "Space Telescope 370",
                "diameter": 10.0,
                "sefd_table": {86e3: 200.0},
                "pitch_range": (-90.0, 90.0),
                "yaw_range": (0.0, 180.0),
                "orbit_file": "i:\\pAstroCORE\\final_orbit370.txt"
            }
        }
        space_tel = SpaceTelescope(use_kep=False, orbit_file="i:\\pAstroCORE\\final_orbit370.txt")
        self.manipulator.process_request("configure", "telescope", space_tel_attributes, space_tel)
        #space_tel.interpolate_orbit_chebyshev()
        telescopes.add_telescope(space_tel)

        # 3. Настройка частоты (86 GHz)
        frequency_attributes = {"set_frequency": {"freq": 86e3}, "set_bandwidth": {"bandwidth": 4e3}}
        frequency = IF()
        self.manipulator.process_request("configure", "if", frequency_attributes, frequency)
        frequencies = Frequencies([frequency])

        # 4. Настройка сканирования (15.03.2031 - 17.03.2031, шаг 1 час)
        start_time = datetime.datetime(2031, 3, 15, 0, 0, 0, tzinfo=timezone.utc)
        epoch = datetime.datetime(1970, 1, 1, tzinfo=timezone.utc)
        ts = int((start_time - epoch).total_seconds())
        scan_attributes = {
            "set_scan": {
                "start": ts,
                "duration": 172800,  # 48 часов (2 дня)
                "source_index": 0,
                "telescope_indices": [0, 1],  # ALMA, SPACE370
                "frequency_indices": [0]
            }
        }
        scan = Scan()
        self.manipulator.process_request("configure", "scan", scan_attributes, scan)
        scans = Scans([scan])

        # 5. Создание наблюдения
        observation = Observation(observation_code="M87_SPACE_OBS")
        obs_attributes = {
            "set_observation": {
                "observation_code": "M87_SPACE_OBS",
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

        # 6. Вычисление (u,v)-покрытия с шагом 1 час
        calc_attributes = {
            "type": "uv_coverage",
            "time_step": 600.0,  # 1 час
            "freq_idx": 0,
            "store_key": "uv_coverage_f0",
            "recalculate": True
        }
        start = time.time()
        uv_results = self.manipulator.process_request("calculate", "observation", calc_attributes, observation)
        self.assertTrue(uv_results, "UV calculation failed")
        print(f"UV calculation took {time.time() - start:.2f} seconds")

        # 7. Визуализация
        uv_data = observation.get_calculated_data_by_key("uv_coverage_f0")["data"]
        freq = 86e9  # 86 GHz в Гц

        colors = {'ALMA-SPACE370': 'purple'}
        u_points_dict = {'ALMA-SPACE370': []}
        v_points_dict = {'ALMA-SPACE370': []}
        w_points_dict = {'ALMA-SPACE370': []}

        for scan_idx, scan_data in uv_data.items():
            uv_points = scan_data["uv_points"][freq]  # Список кортежей (pair, u, v, w)
            times = scan_data["times"]
            for t, (pair, uu, vv, ww) in zip(times, uv_points):
                if pair in u_points_dict:
                    u_points_dict[pair].append(float(uu))
                    v_points_dict[pair].append(float(vv))
                    w_points_dict[pair].append(float(ww))
                    logger.debug(f"Time: {t}, Pair: {pair}, u: {uu:.4f}, v: {vv:.4f}, w: {ww:.4f}")

        # Проверка данных
        self.assertGreater(len(u_points_dict['ALMA-SPACE370']), 0, "No points for ALMA-SPACE370 baseline")

        # Визуализация
        plt.figure(figsize=(10, 10))
        for pair in u_points_dict:
            plt.scatter(u_points_dict[pair], v_points_dict[pair], s=10, label=pair, color=colors[pair])  # Увеличиваем размер точек
        plt.xlabel("u (wavelengths)")
        plt.ylabel("v (wavelengths)")
        plt.title("UV Coverage for M87 Observation with Space Telescope (86 GHz)")
        plt.grid(True)
        plt.legend()
        # Убираем фиксированные пределы
        # plt.xlim(-5e9, 5e9)
        # plt.ylim(-5e9, 5e9)
        plt.gca().invert_xaxis()
        plt.savefig("uv_coverage_m87_space.png")
        plt.show()

    def tearDown(self):
        """Очистка после теста"""
        self.manipulator = None
        self.project = None
        logger.info("Tore down test environment")

if __name__ == "__main__":
    unittest.main()