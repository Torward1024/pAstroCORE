# super/visualizator.py
from abc import ABC, abstractmethod
from base.observation import Observation
from utils.logging_setup import logger

class Visualizator(ABC):
    def __init__(self):
        logger.info("Initialized Visualizator")

    @abstractmethod
    def visualize(self, observation: Observation) -> None:
        pass

    def visualize_molweide_tracks(self, observation: Observation) -> None:
        logger.info(f"Visualized Molweide tracks for observation '{observation.observation_code}' (placeholder)")

    def visualize_uv_coverage(self, observation: Observation) -> None:
        logger.info(f"Visualized u,v coverage for observation '{observation.observation_code}' (placeholder)")

    def __repr__(self) -> str:
        return "Visualizator()"