# super/calculator.py
from abc import ABC, abstractmethod
from base.observation import Observation
import numpy as np
from utils.logging_setup import logger

class Calculator(ABC):
    def __init__(self):
        self._cache = {}
        logger.info("Initialized Calculator")

    @abstractmethod
    def calculate(self, observation: Observation) -> dict:
        pass

    def calculate_molweide_tracks(self, observation: Observation) -> dict:
        logger.info(f"Calculated Molweide tracks for observation '{observation.observation_code}' (placeholder)")
        return {"tracks": []}

    def calculate_uv_coverage(self, observation: Observation) -> dict:
        logger.info(f"Calculated u,v coverage for observation '{observation.observation_code}' (placeholder)")
        return {"uv": []}

    def calculate_source_visibility(self, observation: Observation, telescope_code: str, source_name: str) -> bool:
        if not isinstance(observation, Observation):
            logger.error("Invalid observation type provided")
            raise TypeError("observation must be an Observation instance!")
        
        cache_key = f"visibility_{observation.observation_code}_{telescope_code}_{source_name}"
        if cache_key in self._cache:
            logger.info(f"Retrieved cached visibility result for '{cache_key}'")
            return self._cache[cache_key]

        telescope = next((t for t in observation.telescopes.get_all_telescopes() if t.code == telescope_code), None)
        source = next((s for s in observation.sources.get_all_sources() if s.name == source_name or s.name_J2000 == source_name), None)
        
        if not telescope or not source:
            logger.error(f"Telescope '{telescope_code}' or source '{source_name}' not found in observation")
            raise ValueError(f"Telescope '{telescope_code}' or source '{source_name}' not found in observation!")
        
        ra_rad = np.radians(source.get_ra_degrees())
        dec_rad = np.radians(source.get_dec_degrees())
        tel_pos = np.array([telescope.x, telescope.y, telescope.z]) / 1000  # Convert to km
        
        for scan in observation.scans.get_all_scans():
            if scan.source.name != source_name and scan.source.name_J2000 != source_name:
                continue
            
            gmst = (scan.get_start() / 86400.0 * 360.0 + 280.46061837) % 360  # Rough GMST in degrees
            lst = gmst + np.degrees(np.arctan2(tel_pos[1], tel_pos[0]))  # LST in degrees
            ha = np.radians(lst - source.get_ra_degrees())
            
            sin_alt = (np.sin(dec_rad) * np.sin(np.arctan2(tel_pos[2], np.sqrt(tel_pos[0]**2 + tel_pos[1]**2))) +
                       np.cos(dec_rad) * np.cos(ha) * np.cos(np.arctan2(tel_pos[2], np.sqrt(tel_pos[0]**2 + tel_pos[1]**2))))
            alt = np.arcsin(sin_alt)
            
            if alt > 0:
                self._cache[cache_key] = True
                logger.info(f"Source '{source_name}' is visible from telescope '{telescope_code}' in observation '{observation.observation_code}'")
                return True
        
        self._cache[cache_key] = False
        logger.info(f"Source '{source_name}' is not visible from telescope '{telescope_code}' in observation '{observation.observation_code}'")
        return False