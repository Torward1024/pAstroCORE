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
from unit_scheduling.super.schedule_calculator import ScheduleCalculator
from common.utils.logging_setup import logger
from astropy.time import Time
import astropy.units as u
import unittest
import time

class TestEHTObservationWithSpaceTelescope(unittest.TestCase):
    def setUp(self):
        self.manipulator = ScheduleManipulator()
        self.project = ScheduleProject(name="VISIBILITY_TEST_PROJECT")
        self.manipulator.set_managing_object(self.project)
        self.calculator = ScheduleCalculator(self.manipulator)
        self.manipulator.register_operation("calculate", self.calculator)

        # Настройка источника
        m87_source = Source()
        result = self.manipulator.process_request({
            "operation": "configure",
            "attributes": {
                "set_source": {
                    "name": "M87",
                    "ra_h": 12, "ra_m": 30, "ra_s": 49.42,
                    "de_d": 12, "de_m": 23, "de_s": 28.0
                },
                "set_flux": {"frequency": 86e3, "flux": 1.2}
            },
            "obj": m87_source
        })
        self.assertTrue(result, "Failed to configure M87 source")
        sources = Sources([m87_source])

        # Настройка телескопов
        telescopes = Telescopes()
        tel_configs = {
            "apex": {
                "operation": "configure",
                "attributes": {"set_telescope": {
                    "code": "APEX", "name": "APEX", "x": 2225039.53, "y": -5441197.63, "z": -2479303.36,
                    "vx": 0.0, "vy": 0.0, "vz": 0.0, "diameter": 12.0, "sefd_table": {86e3: 120.0},
                    "elevation_range": (0.0, 90.0), "azimuth_range": (0.0, 360.0), "mount_type": "AZIM"
                }},
                "obj": Telescope()
            },
            "space370": {
                "operation": "configure",
                "attributes": {"set_telescope": {
                    "code": "SPACE370", "use_kep": False, "name": "Space Telescope 370", "diameter": 10.0,
                    "sefd_table": {86e3: 200.0}, "pitch_range": (-90.0, 90.0), "yaw_range": (0.0, 180.0),
                    "orbit_file": "final_orbit370.txt", "interpolation_method": "linear"
                }},
                "obj": SpaceTelescope(use_kep=False, orbit_file="final_orbit370.txt", interpolation_method="linear")
            }
        }
        tel_results = self.manipulator.process_request(tel_configs)
        for tel_id, result in tel_results.items():
            self.assertTrue(result, f"Failed to configure telescope {tel_id}")
            telescopes.add_telescope(tel_configs[tel_id]["obj"])

        # Настройка частоты
        frequency = IF()
        result = self.manipulator.process_request({
            "operation": "configure",
            "attributes": {"set_frequency": {"freq": 86e3}, "set_bandwidth": {"bandwidth": 4e3}},
            "obj": frequency
        })
        self.assertTrue(result, "Failed to configure frequency")
        frequencies = Frequencies([frequency])

        # Настройка скана
        start_time = Time("2030-11-30T12:00:00", format="isot", scale="utc")
        duration = 3600 * u.s
        scan = Scan()
        result = self.manipulator.process_request({
            "operation": "configure",
            "attributes": {
                "set_scan": {
                    "start": start_time,
                    "duration": duration.value,
                    "source_index": 0,
                    "telescope_indices": [0, 1],
                    "frequency_indices": [0]
                }
            },
            "obj": scan
        })
        self.assertTrue(result, "Failed to configure scan")
        scans = Scans([scan])

        # Настройка наблюдения
        self.observation = Observation(observation_code="VIS_TEST_OBS")
        result = self.manipulator.process_request({
            "operation": "configure",
            "attributes": {
                "set_observation": {
                    "observation_code": "VIS_TEST_OBS",
                    "sources": sources,
                    "telescopes": telescopes,
                    "frequencies": frequencies,
                    "scans": scans,
                    "observation_type": "VLBI",
                    "isactive": True
                }
            },
            "obj": self.observation
        })
        self.assertTrue(result, "Failed to configure observation")
        self.project.add_item(self.observation)

        logger.setLevel("DEBUG")
        logger.info("Set up test environment completed")

    def test_universal_visibility(self):
        observation = self.observation

        # Проверка доступных телескопов
        telescopes = observation.get_telescopes()
        logger.info(f"Active telescopes: {[tel.get_code() for tel in telescopes.get_active_telescopes()]}")

        # Видимость КА с APEX
        spacecraft_request = {
            "operation": "calculate",
            "attributes": {
                "method": "source_visibility",
                "start_time": "2030-11-30T12:00:00.000",
                "end_time": "2030-12-30T12:00:00.000",
                "time_step": 3600,
                "telescope_code": "APEX",
                "target_index": 0,
                "store_key": "spacecraft_visibility_apex"
            },
            "obj": observation
        }
        
        start = time.time()
        
        spacecraft_result = self.manipulator.process_request(spacecraft_request)
        result = spacecraft_result[0]

        self.assertTrue(bool(result), "Failed to calculate spacecraft visibility (empty result)")
        self.assertIn("visibility", result, "Key 'visibility' missing in spacecraft_result")
        self.assertIn("APEX", result["visibility"], "APEX visibility data missing")
        self.assertEqual(result["visibility"]["APEX"][0] is not None, True)
        expected_points = int((Time("2030-12-30T12:00:00") - Time("2030-11-30T12:00:00")).sec / 3600) 
        self.assertEqual(len(result["times"]), expected_points, "Incorrect number of time points")
        print(f"Spacecraft visibility calculation took {time.time() - start:.2f} seconds")
        print(f"Spacecraft visibility calculated for {len(result['times'])} time points")

if __name__ == "__main__":
    unittest.main()