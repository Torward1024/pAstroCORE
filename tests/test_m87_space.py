from astropy.utils import iers
iers.conf.auto_download = False
iers.conf.iers_auto_url = None
from astropy.utils.iers import conf
conf.auto_max_age = None

from pastrocore.base.sources import Source, Sources
from pastrocore.base.telescopes import Telescope, SpaceTelescope, Telescopes
from pastrocore.base.frequencies import IF, Frequencies
from pastrocore.base.scans import Scan, Scans
from pastrocore.base.observation import Observation
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.super.schedule_manipulator import ScheduleManipulator

from common.utils.logging_setup import logger
from astropy.time import Time
import astropy.units as u
import time
import unittest

class TestEHTObservationWithSpaceTelescope(unittest.TestCase):
    def setUp(self):
        self.manipulator = ScheduleManipulator()
        self.project = ScheduleProject(name="EHT_M87_SPACE_PROJECT")
        self.manipulator.set_managing_object(self.project)
        logger.setLevel("DEBUG")
        logger.info("Set up test environment with Manipulator and Project")
        supported_ops = self.manipulator.get_supported_operations()
        logger.info(f"Supported operations: {supported_ops}")
        self.assertIn("configure", supported_ops, "Operation 'configure' not registered")
        self.assertIn("visualize", supported_ops, "Operation 'visualize' not registered")
        self.assertIn("inspect", supported_ops, "Operation 'inspect' not registered")

    def test_eht_observation_with_space_telescope(self):

        m87_source = Source()
        result = self.manipulator.process_request({
            "operation": "configure",
            "attributes": {
                "set": {"params":{
                    "name": "M87",
                    "ra_h": 12.0, "ra_m": 30.0, "ra_s": 49.42,
                    "de_d": 12.0, "de_m": 23.0, "de_s": 28.0
                }},
                "add_flux": {"frequency": 86e3, "flux": 1.2}
            },
            "obj": m87_source
        })
        self.assertTrue(result, "Failed to configure M87 source")
        sources = Sources()
        sources.add(m87_source)
        telescopes = Telescopes()
        tel_configs = {
            "alma": {
                "operation": "configure",
                "attributes": {"set": {"params": {
                    "code": "ALMA", "name": "ALMA", "x": 2225061.164, "y": -5440057.37, "z": -2481681.15,
                    "vx": 0.0, "vy": 0.0, "vz": 0.0, "diameter": 12.0, "sefd_table": {86e3: 100.0},
                    "elevation_range": (0.0, 90.0), "azimuth_range": (0.0, 360.0), "mount_type": "AZIM"
                }}},
                "obj": Telescope()
            },
            "apex": {
                "operation": "configure",
                "attributes": {"set": {"params": {
                    "code": "APEX", "name": "APEX", "x": 2225039.53, "y": -5441197.63, "z": -2479303.36,
                    "vx": 0.0, "vy": 0.0, "vz": 0.0, "diameter": 12.0, "sefd_table": {86e3: 120.0},
                    "elevation_range": (0.0, 90.0), "azimuth_range": (0.0, 360.0), "mount_type": "AZIM"
                }}},
                "obj": Telescope(name="APEX")
            },
            "smt": {
                "operation": "configure",
                "attributes": {"set": {"params": {
                    "code": "SMT", "name": "SMT", "x": -1828796.2, "y": -5054406.8, "z": 3427865.2,
                    "vx": 0.0, "vy": 0.0, "vz": 0.0, "diameter": 10.0, "sefd_table": {86e3: 150.0},
                    "elevation_range": (0.0, 90.0), "azimuth_range": (0.0, 360.0), "mount_type": "AZIM"
                }}},
                "obj": Telescope(name="SSMT")
            },
            "space370": {
                "operation": "configure",
                "method": "_configure_telescope",
                "attributes": { "set": {"params": {
                    "code": "SPACE370", "use_kep": False, "name": "SPACE370", "diameter": 10.0,
                    "sefd_table": {86e3: 200.0}, "pitch_range": (-90.0, 90.0), "yaw_range": (0.0, 180.0),
                    "orbit_file": "final_orbit370.txt", "interpolation_method": "linear"
                }}},
                "obj": SpaceTelescope(name="SPSPT", use_kep=False, orbit_file="final_orbit370.txt", interpolation_method="linear")
            }
        }
        tel_results = self.manipulator.process_request(tel_configs)
        for tel_id, result in tel_results.items():
            self.assertTrue(result, f"Failed to configure telescope {tel_id}")
            telescopes.add(tel_configs[tel_id]["obj"])

        frequency = IF(name="IF1")
        result = self.manipulator.process_request({
            "operation": "configure",
            "attributes": {"set": {"params": {"frequency": 86e3}, "set_bandwidth": {"bandwidth": 4e3}}},
            "obj": frequency
        })
        self.assertTrue(result, "Failed to configure frequency")
        frequencies = Frequencies()
        frequencies.add(frequency)

        start_time = Time("2031-03-10T00:00:00", format="isot", scale="utc")
        duration = 864000 * u.s
        scan = Scan()
        result = self.manipulator.process_request({
            "operation": "configure",
            "attributes": {
                "set": {"params": {
                    "name": "SCAN01",
                    "start": start_time,
                    "duration": duration.value,
                    "source_name": "M87",
                    "telescope_names": ["ALMA", "APEX", "SMT", "SPACE370"],
                    "frequency_names": ["IF1"]
                }}
            },
            "obj": scan
        })
        self.assertTrue(result, "Failed to configure scan")
        scans = Scans()
        scans.add(scan)

        observation = Observation(name="M87_SPACE_OBS")
        single_dish_obs = Observation(name="M87_SINGLE_DISH", observation_type="SINGLE_DISH")
        obs_configs = {
            "vlbi": {
                "operation": "configure",
                "attributes": {
                    "set": {"params": {
                        "code": "M87_SPACE_OBS",
                        "sources": sources,
                        "telescopes": telescopes,
                        "frequencies": frequencies,
                        "scans": scans,
                        "observation_type": "VLBI",
                        "isactive": True
                    }}
                },
                "obj": observation
            },
            "single_dish": {
                "operation": "configure",
                "attributes": {
                    "set": {"params": {
                        "code": "M87_SINGLE_DISH",
                        "sources": sources,
                        "telescopes": Telescopes({telescopes.get("ALMA").name: telescopes.get("ALMA"), telescopes.get("APEX").name: telescopes.get("APEX")}),
                        "frequencies": frequencies,
                        "scans": Scans(items={"SCAN1": Scan(name="SCAN1", start=start_time, duration=3600.0, source_name="M87", telescope_names=["ALMA", "APEX"], frequency_names=["IF1"])}),
                        "observation_type": "SINGLE_DISH",
                        "isactive": True
                    }}
                },
                "obj": single_dish_obs
            }
        }
        obs_results = self.manipulator.process_request(obs_configs)
        self.assertTrue(obs_results["vlbi"], "Failed to configure VLBI observation")
        self.assertTrue(obs_results["single_dish"], "Failed to configure SINGLE_DISH observation")
        self.project.add_item(observation)
        self.project.add_item(single_dish_obs)

        # 6. Вычисления через серию запросов
        calc_requests = {
            "uv_coverage": {
                "operation": "calculate",
                "attributes": {
                    "method": "uv_coverage",
                    "time_step": 600,
                    "freq_name": "IF1",
                    "recalculate": False
                },
                "obj": observation
            },
            "mollweide_tracks": {
                "operation": "calculate",
                "attributes": {
                    "method": "mollweide_tracks",
                    "time_step": 600,
                    "store_key": "mollweide_tracks",
                    "recalculate": False
                },
                "obj": observation
            },
            "baseline_projections": {
                "operation": "calculate",
                "attributes": {
                    "method": "baseline_projections",
                    "time_step": 600,
                    "freq_name": "IF1",
                    "recalculate": False
                },
                "obj": observation
            },
            "beam_pattern": {
                "operation": "calculate",
                "attributes": {
                    "method": "beam_pattern",
                    "freq_name": "IF1",
                    "recalculate": False
                },
                "obj": single_dish_obs
            },
            "synthesized_beam": {
                "operation": "calculate",
                "attributes": {
                    "method": "synthesized_beam",
                    "freq_name": "IF1",
                    "recalculate": False,
                    "time_step": 600
                },
                "obj": observation
            },
            "time_on_source": {
                "operation": "calculate",
                "attributes": {
                    "method": "time_on_source",
                    "time_step": 600,
                    "store_key": "time_on_source",
                    "recalculate": False
                },
                "obj": observation
            },
            "sun_angles": {
                "operation": "calculate",
                "attributes": {
                    "method": "sun_angles",
                    "time_step": 600,
                    "store_key": "sun_angles",
                    "recalculate": False
                },
                "obj": observation
            },
            "az_el": {
                "operation": "calculate",
                "attributes": {
                    "method": "az_el",
                    "time_step": 600,
                    "store_key": "az_el",
                    "recalculate": False
                },
                "obj": observation
            }
        }
        start = time.time()
        calc_results = self.manipulator.process_request(calc_requests)
        for calc_id, result in calc_results.items():
            self.assertTrue(result, f"{calc_id} calculation failed")
        print(f"All calculations took {time.time() - start:.2f} seconds")

        vis_requests = {
            "uv_coverage": {
                "operation": "visualize",
                "attributes": {
                    "method": "_visualize",
                    "plot_type": "uv_coverage",
                    "time_step": 600,
                    "freq_name": "IF1",
                    "output_file": "uv_coverage_m87_space_with_conjugates.png",
                    "show": True,
                    "figsize": (12, 12)
                },
                "obj": observation
            },
            "mollweide_tracks": {
                "operation": "visualize",
                "attributes": {
                    "method": "_visualize",
                    "plot_type": "mollweide_tracks",
                    "time_step": 600,
                    "output_file": "mollweide_track_m87_space_matplotlib_mollweide_j2000_fixed.png",
                    "show": True,
                    "figsize": (10, 6)
                },
                "obj": observation
            },
            "baseline_projections": {
                "operation": "visualize",
                "attributes": {
                    "method": "_visualize",
                    "plot_type": "baseline_projections",
                    "time_step": 600,
                    "freq_name": "IF1",
                    "output_file": "baseline_projections_m87_space.png",
                    "show": True,
                    "figsize": (12, 6)
                },
                "obj": observation
            },
            "beam_pattern": {
                "operation": "visualize",
                "attributes": {
                    "method": "_visualize",
                    "plot_type": "beam_pattern",
                    "freq_name": "IF1",
                    "output_file": "beam_pattern_m87_single_dish.png",
                    "show": True,
                    "figsize": (10, 6)
                },
                "obj": single_dish_obs
            },
            "synthesized_beam": {
                "operation": "visualize",
                "attributes": {
                    "method": "_visualize",
                    "plot_type": "synthesized_beam",
                    "freq_name": "IF1",
                    "output_file": "synthesized_beam_2d_m87_vlbi.png",
                    "show": True,
                    "figsize": (10, 8)
                },
                "obj": observation
            },
            "time_on_source": {
                "operation": "visualize",
                "attributes": {
                    "method": "_visualize",
                    "plot_type": "time_on_source",
                    "time_step": 600,
                    "output_file": "time_on_source_m87_space.png",
                    "show": True,
                    "figsize": (12, 6)
                },
                "obj": observation
            },
            "sun_angles": {
                "operation": "visualize",
                "attributes": {
                    "method": "_visualize",
                    "plot_type": "sun_angles",
                    "time_step": 600,
                    "output_file": "sun_angles_m87_space.png",
                    "show": True,
                    "figsize": (12, 6)
                },
                "obj": observation
            },
            "az_el": {
                "operation": "visualize",
                "attributes": {
                    "method": "_visualize",
                    "plot_type": "az_el",
                    "time_step": 600,
                    "output_file": "az_el_m87_space.png",
                    "show": True,
                    "figsize": (12, 6)
                },
                "obj": observation
            }
        }
        start = time.time()
        vis_results = self.manipulator.process_request(vis_requests)
        for vis_id, result in vis_results.items():
            self.assertEqual(result["status"], True)
        print(f"All visualizations took {time.time() - start:.2f} seconds")

if __name__ == "__main__":
    unittest.main()