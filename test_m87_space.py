from astropy.utils import iers
iers.conf.auto_download = False
iers.conf.iers_auto_url = None
from astropy.utils.iers import conf
conf.auto_max_age = None

from unit_scheduling.base.sources import Source, Sources
from unit_scheduling.base.telescopes import Telescope, SpaceTelescope, Telescopes
from unit_scheduling.base.frequencies import IF, Frequencies
from unit_scheduling.base.scans import Scan, Scans
from unit_scheduling.base.observation import Observation
from unit_scheduling.super.schedule_project import ScheduleProject
from unit_scheduling.super.schedule_manipulator import ScheduleManipulator

from common.utils.logging_setup import logger
from astropy.time import Time
import astropy.units as u
import numpy as np
import time
import unittest
import matplotlib.pyplot as plt

class TestEHTObservationWithSpaceTelescope(unittest.TestCase):
    def setUp(self):
        self.manipulator = ScheduleManipulator()
        self.project = ScheduleProject(name="EHT_M87_SPACE_PROJECT")
        self.manipulator.set_managing_object(self.project)
        logger.setLevel("DEBUG")  # Включаем отладочные логи
        logger.info("Set up test environment with Manipulator and Project")
        # Проверяем, что операции зарегистрированы корректно
        supported_ops = self.manipulator.get_supported_operations()
        logger.info(f"Supported operations: {supported_ops}")
        self.assertIn("configure", supported_ops, "Operation 'configure' not registered")

    def test_eht_observation_with_space_telescope(self):
        """Тест полного цикла с космическим телескопом: настройка, вычисление (u,v), проекций базы, визуализация + beam_pattern и synthesized_beam"""
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
        result = self.manipulator.process_request({
            "operation": "configure",
            "target": "source",
            "attributes": m87_attributes,
            "obj": m87_source
        })
        self.assertTrue(result, "Failed to configure M87 source")
        sources = Sources([m87_source])

        # 2. Настройка телескопов (ALMA + APEX + SMT + космический телескоп)
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
            result = self.manipulator.process_request({
                "operation": "configure",
                "target": "telescope",
                "attributes": {"set_telescope": tel_data},
                "obj": tel
            })
            self.assertTrue(result, f"Failed to configure telescope {tel_data['code']}")
            telescopes.add_telescope(tel)

        space_tel_attributes = {
            "set_telescope": {
                "code": "SPACE370",
                "use_kep": False,
                "name": "Space Telescope 370",
                "diameter": 10.0,
                "sefd_table": {86e3: 200.0},
                "pitch_range": (-90.0, 90.0),
                "yaw_range": (0.0, 180.0),
                "orbit_file": "i:\\pAstroCORE\\final_orbit370.txt",
                "interpolation_method": "linear"
            }
        }
        space_tel = SpaceTelescope(
            use_kep=False,
            orbit_file="i:\\pAstroCORE\\final_orbit370.txt",
            interpolation_method="linear"
        )
        result = self.manipulator.process_request({
            "operation": "configure",
            "target": "telescope",
            "attributes": space_tel_attributes,
            "obj": space_tel
        })
        self.assertTrue(result, "Failed to configure Space Telescope")
        telescopes.add_telescope(space_tel)

        # 3. Настройка частоты (86 GHz)
        frequency_attributes = {"set_frequency": {"freq": 86e3}, "set_bandwidth": {"bandwidth": 4e3}}
        frequency = IF()
        result = self.manipulator.process_request({
            "operation": "configure",
            "target": "if",
            "attributes": frequency_attributes,
            "obj": frequency
        })
        self.assertTrue(result, "Failed to configure frequency")
        frequencies = Frequencies([frequency])

        # 4. Настройка сканирования (10.03.2031 - 20.03.2031, шаг 10 минут)
        start_time = Time("2031-03-10T00:00:00", format="isot", scale="utc")
        duration = 365 * 24 * 3600 * u.s  # 1 год
        scan_attributes = {
            "set_scan": {
                "start": start_time,
                "duration": duration.value,
                "source_index": 0,
                "telescope_indices": [0, 1, 2, 3],  # ALMA, APEX, SMT, SPACE370
                "frequency_indices": [0]
            }
        }
        scan = Scan()
        result = self.manipulator.process_request({
            "operation": "configure",
            "target": "scan",
            "attributes": scan_attributes,
            "obj": scan
        })
        self.assertTrue(result, "Failed to configure scan")
        scans = Scans([scan])

        # 5. Создание VLBI наблюдения
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
        result = self.manipulator.process_request({
            "operation": "configure",
            "target": "observation",
            "attributes": obs_attributes,
            "obj": observation
        })
        self.assertTrue(result, "Failed to configure VLBI observation")
        self.project.add_observation(observation)

        # 6. Создание SINGLE_DISH наблюдения для beam_pattern
        single_dish_obs = Observation(observation_code="M87_SINGLE_DISH", observation_type="SINGLE_DISH")
        single_dish_attributes = {
            "set_observation": {
                "observation_code": "M87_SINGLE_DISH",
                "sources": sources,
                "telescopes": Telescopes([telescopes.get_by_index(0), telescopes.get_by_index(1)]),  # ALMA, APEX
                "frequencies": frequencies,
                "scans": Scans([Scan(start=start_time, duration=3600, source_index=0, telescope_indices=[0, 1], frequency_indices=[0])]),
                "observation_type": "SINGLE_DISH",
                "isactive": True
            }
        }
        result = self.manipulator.process_request({
            "operation": "configure",
            "target": "observation",
            "attributes": single_dish_attributes,
            "obj": single_dish_obs
        })
        self.assertTrue(result, "Failed to configure SINGLE_DISH observation")
        self.project.add_observation(single_dish_obs)

        # 7. Вычисление (u,v)-покрытия с шагом 10 минут
        calc_attributes = {
            "method": "uv_coverage",
            "time_step": 18000,
            "freq_idx": 0,
            "store_key": "uv_coverage_f0",
            "recalculate": False
        }
        start = time.time()
        uv_results = self.manipulator.process_request({
            "operation": "calculate",
            "attributes": calc_attributes,
            "obj": self.project.get_by_index(0)
        })
        self.assertTrue(uv_results, "UV calculation failed")
        print(f"UV calculation took {time.time() - start:.2f} seconds")

        # 8. Вычисление Mollweide tracks с шагом 10 минут
        calc_attributes_moll = {
            "method": "mollweide_tracks",
            "time_step": 18000,
            "store_key": "mollweide_tracks",
            "recalculate": False
        }
        start = time.time()
        moll_results = self.manipulator.process_request({
            "operation": "calculate",
            "attributes": calc_attributes_moll,
            "obj": self.project.get_by_index(0)
        })
        self.assertTrue(moll_results, "Mollweide calculation failed")
        print(f"Mollweide calculation took {time.time() - start:.2f} seconds")

        # 9. Вычисление проекций базы с шагом 10 минут
        calc_attributes_bl = {
            "method": "baseline_projections",
            "time_step": 18000,
            "freq_idx": 0,
            "store_key": "baseline_projections_f0",
            "recalculate": False
        }
        start = time.time()
        bl_results = self.manipulator.process_request({
            "operation": "calculate",
            "attributes": calc_attributes_bl,
            "obj": self.project.get_by_index(0)
        })
        self.assertTrue(bl_results, "Baseline projections calculation failed")
        print(f"Baseline projections calculation took {time.time() - start:.2f} seconds")

        # 10. Вычисление beam_pattern для SINGLE_DISH
        beam_attributes = {
            "method": "beam_pattern",
            "freq_idx": 0,
            "store_key": "beam_pattern_f0",
            "recalculate": False
        }
        start = time.time()
        beam_results = self.manipulator.process_request({
            "operation": "calculate",
            "attributes": beam_attributes,
            "obj": self.project.get_by_index(1)
        })
        self.assertTrue(beam_results, "Beam pattern calculation failed")
        print(f"Beam pattern calculation took {time.time() - start:.2f} seconds")

        # 11. Вычисление synthesized_beam для VLBI
        synth_attributes = {
            "method": "synthesized_beam",
            "freq_idx": 0,
            "store_key": "synthesized_beam_f0",
            "recalculate": False,
            "time_step": 18000
        }
        start = time.time()
        synth_results = self.manipulator.process_request({
            "operation": "calculate",
            "attributes": synth_attributes,
            "obj": self.project.get_by_index(0)
        })
        self.assertTrue(synth_results, "Synthesized beam calculation failed")
        print(f"Synthesized beam calculation took {time.time() - start:.2f} seconds")

        # Извлечение данных UV и визуализация (без изменений)
        uv_data = observation.get_calculated_data_by_key("uv_coverage_f0")["data"]
        freq = 86e9  # 86 GHz в Гц
        colors = {
            'ALMA-SPACE370': 'purple',
            'APEX-SPACE370': 'blue',
            'SMT-SPACE370': 'green',
            'ALMA-APEX': 'red',
            'ALMA-SMT': 'orange',
            'APEX-SMT': 'yellow'
        }
        u_points_dict = {pair: [] for pair in colors.keys()}
        v_points_dict = {pair: [] for pair in colors.keys()}
        w_points_dict = {pair: [] for pair in colors.keys()}
        u_conj_points_dict = {pair: [] for pair in colors.keys()}
        v_conj_points_dict = {pair: [] for pair in colors.keys()}

        for scan_idx, scan_data in uv_data.items():
            if "uv_points" not in scan_data or freq not in scan_data["uv_points"]:
                logger.error(f"No valid UV points for scan {scan_idx} at frequency {freq}")
                continue
            uv_points = scan_data["uv_points"][freq]
            for pair, uu, vv, ww in uv_points:
                if pair in u_points_dict:
                    u_points_dict[pair].append(float(uu))
                    v_points_dict[pair].append(float(vv))
                    w_points_dict[pair].append(float(ww))
                    u_conj_points_dict[pair].append(-float(uu))
                    v_conj_points_dict[pair].append(-float(vv))

        self.assertGreater(len(u_points_dict['ALMA-SPACE370']), 0, "No points for ALMA-SPACE370 baseline")
        self.assertGreater(len(u_points_dict['APEX-SPACE370']), 0, "No points for APEX-SPACE370 baseline")
        self.assertGreater(len(u_points_dict['SMT-SPACE370']), 0, "No points for SMT-SPACE370 baseline")

        plt.figure(figsize=(12, 12))
        for pair in u_points_dict:
            if u_points_dict[pair]:
                plt.scatter(u_points_dict[pair], v_points_dict[pair], s=10, label=f"{pair}", color=colors[pair])
                plt.scatter(u_conj_points_dict[pair], v_conj_points_dict[pair], s=10, color=colors[pair], 
                            alpha=0.5, marker='x', label=f"{pair} (conj)")
        plt.xlabel("u (wavelengths)")
        plt.ylabel("v (wavelengths)")
        plt.title("UV Coverage for M87 Observation with Space Telescope (86 GHz) with Conjugates")
        plt.grid(True)
        plt.legend()
        plt.gca().invert_xaxis()
        plt.savefig("uv_coverage_m87_space_with_conjugates.png")
        plt.show()

        # Извлечение данных Mollweide
        moll_data = observation.get_calculated_data_by_key("mollweide_tracks")["data"]
        self.assertGreater(len(moll_data), 0, "No Mollweide data calculated")

        # Визуализация Mollweide
        fig = plt.figure(figsize=(10, 6))
        ax = fig.add_subplot(111, projection='mollweide', facecolor='LightCyan')
        tel_codes = ['ALMA', 'APEX', 'SMT', 'SPACE370']
        colors_moll = ['blue', 'green', 'red', 'purple']
        for scan_idx, scan_data in moll_data.items():
            telescope_tracks = scan_data.get("telescope_tracks", {})
            for i, tel_code in enumerate(tel_codes):
                track = telescope_tracks.get(tel_code)
                if track and track["lon"]:
                    lon_points = np.radians(np.array(track["lon"]))
                    lat_points = np.radians(np.array(track["lat"]))
                    ax.scatter(lon_points, lat_points, s=20, c=colors_moll[i], label=f"{tel_code} Track")
                    ax.scatter(lon_points[0], lat_points[0], s=20, c=colors_moll[i], marker='o')
                    ax.scatter(lon_points[-1], lat_points[-1], s=20, c=colors_moll[i], marker='x')
            source_data = scan_data.get("source", {})
            source_lon_rad = np.radians(source_data.get("lon"))
            source_lat_rad = np.radians(source_data.get("lat"))
            ax.scatter([source_lon_rad], [source_lat_rad], s=100, c='black', marker='*', label=f"{source_data.get('name')} (J2000)")
        ra_ticks_rad = ax.get_xticks()
        ra_ticks_hours = (np.degrees(ra_ticks_rad) + 180) / 15.0
        dec_ticks_rad = ax.get_yticks()
        dec_ticks_deg = np.degrees(dec_ticks_rad)
        ax.set_xticks(ra_ticks_rad)
        ax.set_xticklabels([f"{int(np.round(h))}h" for h in ra_ticks_hours])
        ax.set_yticks(dec_ticks_rad)
        ax.set_yticklabels([f"{int(np.round(d))}°" for d in dec_ticks_deg])
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.set_title("Mollweide Projection of Telescope Tracks and M87 (J2000, 10-20 March 2031)")
        ax.set_xlabel("Right Ascension (hours)")
        ax.set_ylabel("Declination (degrees)")
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig("mollweide_track_m87_space_matplotlib_mollweide_j2000_fixed.png")
        plt.show()

        # Визуализация проекций базы
        bl_data = observation.get_calculated_data_by_key("baseline_projections_f0")["data"]
        self.assertGreater(len(bl_data), 0, "No baseline projections data calculated")

        c = 299792458  # м/с
        freq = 86e9  # 86 GHz в Гц
        wavelength = c / freq  # длина волны в метрах
        earth_diameter = 12742000  # метры

        # Извлечение данных проекций
        if not bl_data[0]:
            logger.error("No projection data available in bl_data[0]")
            projections = {}
            time_values = None
        elif "times" in bl_data[0]:
            times = bl_data[0]["times"]
            time_values = [Time(t).mjd for t in times]
            projections = bl_data[0]["projections"]
        else:
            projections = bl_data[0]["projections"]
            time_values = None

        plt.figure(figsize=(12, 6))
        if time_values and projections:
            for pair, bl_values in projections.items():
                if bl_values:
                    bl_meters = np.array(bl_values) * wavelength
                    bl_earth_diameters = bl_meters / earth_diameter
                    valid_indices = [i for i, bl in enumerate(bl_values) if bl is not None]
                    filtered_times = [time_values[i] for i in valid_indices]
                    filtered_bl_earth_diameters = [bl_earth_diameters[i] for i in valid_indices]
                    if filtered_times and filtered_bl_earth_diameters:
                        plt.plot(filtered_times, filtered_bl_earth_diameters, label=pair, color=colors.get(pair, 'black'))
                    else:
                        logger.debug(f"No valid data to plot for pair {pair}")
                else:
                    logger.debug(f"No baseline projections for pair {pair}")
            plt.xlabel("Time (MJD)")
        elif projections:
            pairs = list(projections.keys())
            bl_values = [projections[pair] for pair in pairs if pair in projections]
            bl_meters = np.array(bl_values) * wavelength
            bl_earth_diameters = bl_meters / earth_diameter
            plt.bar(pairs, bl_earth_diameters, color=[colors.get(pair, 'black') for pair in pairs])
            plt.xlabel("Baseline Pair")
        else:
            logger.warning("No data to plot for baseline projections")
        plt.ylabel("Baseline Projection (Earth Diameters)")
        plt.title("Baseline Projections for M87 Observation (86 GHz, 10-20 March 2031)")
        plt.grid(True)
        if projections and any(projections.values()):
            plt.legend()
        plt.tight_layout()
        plt.savefig("baseline_projections_m87_space.png")
        plt.show()

        # Визуализация beam_pattern
        plt.figure(figsize=(10, 6))
        for tel_code, data in beam_results.items():
            theta = np.array(data["theta"]) * 180 / np.pi  # Перевод в градусы
            pattern = data["pattern"]
            plt.plot(theta, pattern, label=f"{tel_code} (D={telescopes.get_by_index(0 if tel_code == 'ALMA' else 1).get_diameter()} m)")
        plt.xlabel("Угол (градусы)")
        plt.ylabel("Интенсивность (нормированная)")
        plt.title("Диаграмма направленности (Beam Pattern) при 86 ГГц")
        plt.grid(True)
        plt.legend()
        plt.savefig("beam_pattern_m87_single_dish.png")
        plt.show()

        plt.figure(figsize=(10, 8))
        for scan_idx, data in synth_results.items():
            theta_u = np.array(data["theta_u"])
            theta_v = np.array(data["theta_v"])
            beam_2d = np.array(data["beam_2d"])
            
            # Создаём тепловую карту
            plt.imshow(beam_2d, extent=[theta_u.min(), theta_u.max(), theta_v.min(), theta_v.max()],
                    cmap='viridis', origin='lower', aspect='equal')
            plt.colorbar(label='Нормированная интенсивность')
            plt.xlabel("Right Ascension (градусы)")
            plt.ylabel("Declination (градусы)")
            plt.title(f"2D Синтезированная диаграмма направленности (VLBI, 86 ГГц, Скан {scan_idx})")
        plt.grid(False)  # Убираем сетку для чистоты изображения
        plt.savefig("synthesized_beam_2d_m87_vlbi.png")
        plt.show()

        # 12. Вычисление time_on_source
        calc_attributes_time = {
            "method": "time_on_source",
            "time_step": 18000,
            "store_key": "time_on_source",
            "recalculate": False
        }
        start = time.time()
        time_results = self.manipulator.process_request({
            "operation": "calculate",
            "attributes": calc_attributes_time,
            "obj": self.project.get_by_index(0)
        })
        self.assertTrue(time_results, "Time on source calculation failed")
        print(f"Time on source calculation took {time.time() - start:.2f} seconds")

        # Извлечение данных time_on_source
        time_data = observation.get_calculated_data_by_key("time_on_source")["data"]
        self.assertGreater(len(time_data), 0, "No time on source data calculated")

        # Визуализация блок-диаграммы (Gantt chart)
        plt.figure(figsize=(12, 6))
        telescopes_list = ['ALMA', 'APEX', 'SMT', 'SPACE370']
        colors_time = {'ALMA': 'blue', 'APEX': 'green', 'SMT': 'red', 'SPACE370': 'purple'}
        y_pos = np.arange(len(telescopes_list))

        for source_name, source_data in time_data.items():
            tel_blocks = source_data["telescopes"]
            for i, tel_code in enumerate(telescopes_list):
                if tel_code in tel_blocks:
                    blocks = tel_blocks[tel_code]
                    for block in blocks:
                        start_mjd = Time(block["start"]).mjd
                        duration_days = block["duration"] / (24 * 3600)  # Переводим секунды в дни
                        plt.barh(i, duration_days, left=start_mjd, color=colors_time[tel_code], edgecolor='black', alpha=0.7)

        plt.yticks(y_pos, telescopes_list)
        plt.xlabel("Time (MJD)")
        plt.ylabel("Telescope")
        plt.title(f"Time on Source: {source_name} (10-20 March 2031)")
        plt.grid(True, axis='x', linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.savefig("time_on_source_m87_space.png")
        plt.show()

        # 13. Вычисление sun_angles
        calc_attributes_sun = {
            "method": "sun_angles",
            "time_step": 18000,
            "store_key": "sun_angles",
            "recalculate": False
        }
        start = time.time()
        sun_results = self.manipulator.process_request({
            "operation": "calculate",
            "attributes": calc_attributes_sun,
            "obj": self.project.get_by_index(0)
        })
        self.assertTrue(sun_results, "Sun angles calculation failed")
        print(f"Sun angles calculation took {time.time() - start:.2f} seconds")

        # Извлечение данных sun_angles
        sun_data = observation.get_calculated_data_by_key("sun_angles")["data"]
        self.assertGreater(len(sun_data), 0, "No sun angles data calculated")

        # Визуализация sun_angles
        plt.figure(figsize=(12, 6))
        telescopes_list = ['ALMA', 'APEX', 'SMT', 'SPACE370']
        colors_sun = {'ALMA': 'blue', 'APEX': 'green', 'SMT': 'red', 'SPACE370': 'purple'}
        for scan_idx, scan_data in sun_data.items():
            times = [Time(t).jd for t in scan_data["times"]]
            for tel_code in telescopes_list:
                if tel_code in scan_data["sun_angles"]:
                    angles = scan_data["sun_angles"][tel_code]
                    plt.plot(times, angles, label=f"{tel_code}", color=colors_sun[tel_code])
        plt.xlabel("Time (JD)")
        plt.ylabel("Sun Angle (degrees)")
        plt.title(f"Sun Angles for {scan_data['source']} from Telescopes (10-20 March 2031)")
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.legend()
        plt.tight_layout()
        plt.savefig("sun_angles_m87_space.png")
        plt.show()

        # 14. Вычисление az_el
        calc_attributes_azel = {
            "method": "az_el",
            "time_step": 18000,
            "store_key": "az_el",
            "recalculate": False
        }
        start = time.time()
        azel_results = self.manipulator.process_request({
            "operation": "calculate",
            "attributes": calc_attributes_azel,
            "obj": self.project.get_by_index(0)
        })
        self.assertTrue(azel_results, "Az/El calculation failed")
        print(f"Az/El calculation took {time.time() - start:.2f} seconds")

        # Извлечение данных az_el
        azel_data = observation.get_calculated_data_by_key("az_el")["data"]
        self.assertGreater(len(azel_data), 0, "No az/el data calculated")

        # Визуализация az_el (отдельно для Az/HA и El/Dec)
        telescopes_list = ['ALMA', 'APEX', 'SMT']  # Только наземные телескопы
        colors_azel = {'ALMA': 'blue', 'APEX': 'green', 'SMT': 'red'}  # Определяем цвета для Az/El

        # График для Azimuth/HA
        plt.figure(figsize=(12, 6))
        for scan_idx, scan_data in azel_data.items():
            times = [Time(t).mjd for t in scan_data["times"]]
            for tel_code in telescopes_list:
                if tel_code in scan_data["az_el"]:
                    coord_type = scan_data["az_el"][tel_code]["coord_type"]
                    coord1_label = "Azimuth" if coord_type == "AzEl" else "Hour Angle"
                    plt.plot(times, scan_data["az_el"][tel_code]["coord1"], label=f"{tel_code} ({coord1_label})", color=colors_azel[tel_code])
        plt.xlabel("Time (MJD)")
        plt.ylabel(f"{coord1_label} (degrees)")
        plt.title(f"{coord1_label} for M87 Observation (10-20 March 2031)")
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.legend()
        plt.tight_layout()
        plt.savefig("az_ha_m87_space.png")
        plt.show()

        # График для Elevation/Dec
        plt.figure(figsize=(12, 6))
        for scan_idx, scan_data in azel_data.items():
            times = [Time(t).mjd for t in scan_data["times"]]
            for tel_code in telescopes_list:
                if tel_code in scan_data["az_el"]:
                    coord_type = scan_data["az_el"][tel_code]["coord_type"]
                    coord2_label = "Elevation" if coord_type == "AzEl" else "Declination"
                    plt.plot(times, scan_data["az_el"][tel_code]["coord2"], label=f"{tel_code} ({coord2_label})", color=colors_azel[tel_code])
        plt.xlabel("Time (JD)")
        plt.ylabel(f"{coord2_label} (degrees)")
        plt.title(f"{coord2_label} for M87 Observation (10-20 March 2031)")
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.legend()
        plt.tight_layout()
        plt.savefig("el_dec_m87_space.png")
        plt.show()

if __name__ == "__main__":
    unittest.main()