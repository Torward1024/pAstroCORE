# super/calculator.py
from abc import ABC
from base.observation import Observation
from base.telescopes import Telescope, SpaceTelescope
from base.sources import Source
from base.scans import Scans
from utils.validation import check_type
from utils.logging_setup import logger
import numpy as np
from datetime import datetime

class Calculator(ABC):
    def __init__(self):
        logger.info("Initialized Calculator")

    def calculate_source_visibility(self, observation: Observation, time: float) -> Dict[str, bool]:
        """Calculate visibility of the source for each telescope at a given time with caching."""
        check_type(observation, Observation, "Observation")
        check_type(time, (int, float), "Time")
        key = f"visibility_at_{time}"
        cached_result = observation.get_calculated_data(key)
        if cached_result is not None:
            return cached_result
        
        scans = observation.get_scans()
        result = scans.check_telescope_availability(time)
        observation.set_calculated_data(key, result)
        return result

    def calculate_uv_coverage(self, observation: Observation) -> np.ndarray:
        """Calculate (u,v) coverage for a VLBI observation with caching."""
        check_type(observation, Observation, "Observation")
        if observation.get_observation_type() != "VLBI":
            raise ValueError("UV coverage is only applicable to VLBI observations")
        
        cached_uv = observation.get_calculated_data("uv_coverage")
        if cached_uv is not None:
            return np.array(cached_uv)
        
        active_tels = observation.get_telescopes().get_active_telescopes()
        if len(active_tels) < 2:
            raise ValueError("UV coverage requires at least 2 active telescopes")
        
        active_scans = observation.get_scans().get_active_scans()
        if not active_scans:
            raise ValueError("No active scans to calculate UV coverage")
        
        uv_points = []
        for scan in active_scans:
            if scan.is_off_source:
                continue
            source = scan.get_source()
            ra_rad = np.radians(source.get_ra_degrees())
            dec_rad = np.radians(source.get_dec_degrees())
            start_time = scan.get_start()
            duration = scan.get_duration()
            time_steps = np.linspace(start_time, start_time + duration, 10)
            
            for t in time_steps:
                dt = datetime.fromtimestamp(t)
                positions = []
                for tel in active_tels:
                    if isinstance(tel, SpaceTelescope):
                        pos, _ = tel.get_position_at_time(dt)
                    else:
                        pos = np.array(tel.get_telescope_coordinates())
                    positions.append(pos)
                
                lst = (t / 86164.0905 * 360 + 280.46061837) % 360
                ha = np.radians(lst - source.get_ra_degrees())
                H = ha
                for i in range(len(positions)):
                    for j in range(i + 1, len(positions)):
                        baseline = positions[i] - positions[j]
                        u = baseline[0] * np.sin(H) + baseline[1] * np.cos(H)
                        v = (-baseline[0] * np.sin(dec_rad) * np.cos(H) + 
                             baseline[1] * np.sin(dec_rad) * np.sin(H) + 
                             baseline[2] * np.cos(dec_rad))
                        uv_points.append([u, v])
        
        uv_array = np.array(uv_points)
        observation.set_calculated_data("uv_coverage", uv_array.tolist())
        logger.info(f"Calculated and cached {len(uv_array)} UV points for observation '{observation.get_observation_code()}'")
        return uv_array