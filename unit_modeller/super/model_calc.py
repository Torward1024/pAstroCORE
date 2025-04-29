from common.super.super import Super
from common.utils.logging_setup import logger

from typing import Dict, Any, Optional, Tuple, List

from unit_modeller.base.model import Model, Models

import numpy as np

import threading

class ModelCalculator(Super):
    """Implementation of Calculator for performing astronomical model calculations.

    Provides methods to calculate source visibility functions for UV coverage.
    Supports caching of results and multi-threaded execution for efficiency.

    Attributes:
        manipulator: The Manipulator instance used to manage object interactions.
        _lock (threading.Lock): Thread lock for safe data caching.

    """
    def __init__(self, manipulator: 'Manipulator'):
        """Initialize the ScheduleCalculator.

        Args:
            manipulator: The Manipulator instance providing method validation and execution capabilities.
        """
        super().__init__(manipulator)
        self._lock = threading.Lock()
        logger.info("Initialized Scheduling Calculator")

    def _default_result(self) -> Dict[str, Any]:
        """Return the default result when calculation is not applied.

        Returns:
            Dict[str, Any]: An empty dictionary.
        """
        return {}
    
    def _get_cached_or_calculate(self, obj: Model | Models, store_key: str, calc_func, attributes: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve cached data or perform calculation and cache the result.

        Args:
            obj (Observation | ScheduleProject): The object (Observation or Project) to calculate for.
            store_key (str): Unique key for storing/retrieving calculated data.
            calc_func: The calculation function to execute if no valid cache exists.
            attributes (Dict[str, Any]): Calculation parameters (e.g., "recalculate", "time_step").
            metadata (Dict[str, Any]): Metadata to store with the result (e.g., time step, scan count).

        Returns:
            Dict[str, Any]: Calculated or cached data.

        Notes:
            - If "recalculate" is False and valid cached data exists, returns cached result.
            - Uses thread-safe caching with a lock.
        """
        recalculate = attributes.get("recalculate", False)
        time_step = attributes.get("time_step")

        existing_data = obj.get_calculated_data_by_key(store_key)
        if existing_data and not recalculate and existing_data["metadata"].get("time_step") == time_step:
            if existing_data["data"]:
                logger.info(f"Using cached data for '{store_key}' in '{obj.get_observation_code()}'")
                return existing_data["data"]
            else:
                logger.warning(f"Cached data for '{store_key}' in '{obj.get_observation_code()}' is empty, forcing recalculation")

        logger.info(f"Recalculating '{store_key}' for '{obj.get_observation_code()}' with recalculate={recalculate}")
        result = calc_func(obj, attributes)
        if not result:
            logger.error(f"Calculation for '{store_key}' returned empty result")
        with self._lock:
            obj.set_calculated_data_by_key(store_key, {"metadata": metadata, "data": result})
        return result