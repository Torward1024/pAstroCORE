# super/visualizator.py
from abc import ABC, abstractmethod
from base.observation import Observation
from utils.logging_setup import logger

class Visualizator(ABC):
    @abstractmethod
    def visualize(self, observation: Observation) -> None:
        """Abstract method to visualize an observation."""
        logger.info(f"Visualizator not implemented for observation '{observation.get_observation_code()}'")