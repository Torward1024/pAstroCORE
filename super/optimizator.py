# super/optimizator.py
from abc import ABC, abstractmethod
from base.observation import Observation
from utils.logging_setup import logger

class Optimizator(ABC):
    @abstractmethod
    def optimize(self, observation: Observation) -> None:
        """Abstract method to optimize an observation."""
        logger.info(f"Optimizator not implemented for observation '{observation.get_observation_code()}'")