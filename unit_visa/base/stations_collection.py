from typing import List, Dict, Optional
from common.base.base_entity import BaseEntity
from common.utils.logging_setup import logger
from common.utils.validation import check_type, check_non_empty_string
from unit_visa.base.stations import Station
from unit_visa.base.celestialBodies import CelestialBody

class Stations(BaseEntity):
    def __init__(self, isactive: bool = True):
        super().__init__(isactive)
        self._stations: Dict[str, Station] = {}  # Храним станции в словаре по их коду

    def add_station(self, station: Station) -> None:
        """Добавляет станцию в коллекцию."""
        check_type(station, Station, "Station")
        code = station.get_code()
        if code in self._stations:
            raise ValueError(f"Station with code '{code}' already exists")
        self._stations[code] = station
        logger.info(f"Added station '{code}' to Stations")

    def remove_station(self, code: str) -> None:
        """Удаляет станцию по её коду."""
        check_non_empty_string(code, "Station code")
        if code not in self._stations:
            raise ValueError(f"Station with code '{code}' not found")
        del self._stations[code]
        logger.info(f"Removed station '{code}' from Stations")

    def get_station(self, code: str) -> Optional[Station]:
        """Возвращает станцию по её коду."""
        check_non_empty_string(code, "Station code")
        return self._stations.get(code)

    def get_all_stations(self) -> List[Station]:
        """Возвращает список всех станций."""
        return list(self._stations.values())

    def get_stations_by_celestial_body(self, celestial_body: CelestialBody) -> List[Station]:
        """Возвращает список станций, связанных с указанным небесным телом."""
        check_type(celestial_body, CelestialBody, "Celestial body")
        return [station for station in self._stations.values()
                if station.get_celestial_body().get_body_id() == celestial_body.get_body_id()]

    def get_active_stations(self) -> List[Station]:
        """Возвращает список активных станций."""
        return [station for station in self._stations.values() if station.isactive]

    def to_dict(self) -> dict:
        """Сериализует коллекцию станций в словарь."""
        logger.info("Converting Stations to dictionary")
        return {
            "type": "Stations",
            "stations": [station.to_dict() for station in self._stations.values()],
            "isactive": self.isactive
        }

    @classmethod
    def from_dict(cls, data: dict, celestial_bodies: Dict[int, CelestialBody]) -> 'Stations':
        """Десериализует коллекцию станций из словаря."""
        required_keys = {"stations", "isactive"}
        if not all(key in data for key in required_keys):
            raise ValueError(f"Dictionary must contain keys: {required_keys}")
        
        stations = cls(isactive=data["isactive"])
        for station_dict in data["stations"]:
            celestial_body_id = station_dict.get("celestial_body_id")
            if celestial_body_id not in celestial_bodies:
                raise ValueError(f"Celestial body with ID {celestial_body_id} not found")
            celestial_body = celestial_bodies[celestial_body_id]
            station = Station.from_dict(station_dict, celestial_body)
            stations.add_station(station)
        logger.info("Created Stations from dictionary")
        return stations

    def __repr__(self) -> str:
        return f"Stations(stations={list(self._stations.keys())}, isactive={self.isactive})"