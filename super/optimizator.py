# super/optimizator.py
from abc import ABC, abstractmethod
from base.observation import Observation
from utils.logging_setup import logger

class Optimizator(ABC):
    def __init__(self):
        logger.info("Initialized Optimizator")

    @abstractmethod
    def optimize(self, observation: Observation) -> None:
        pass

    def __repr__(self) -> str:
        return "Optimizator()"