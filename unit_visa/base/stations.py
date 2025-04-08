from common.base.base_entity import BaseEntity
from common.utils.validation import check_type, check_non_empty_string, check_range
from common.utils.logging_setup import logger
from unit_visa.base.celestialBodies import CelestialBody
from typing import Tuple, Optional

class Station(BaseEntity):
    def __init__(self, celestial_body: CelestialBody, code: str, name: str,
                 x: float = 0.0, y: float = 0.0, z: float = 0.0,
                 vx: float = 0.0, vy: float = 0.0, vz: float = 0.0,
                 elevation_range: Tuple[float, float] = (0.0, 90.0),
                 azimuth_range: Tuple[float, float] = (0.0, 360.0),
                 isactive: bool = True):
        super().__init__(isactive)
        check_type(celestial_body, CelestialBody, "Celestial body")
        check_non_empty_string(code, "Station code")
        check_non_empty_string(name, "Station name")
        check_type(x, (int, float), "X coordinate")
        check_type(y, (int, float), "Y coordinate")
        check_type(z, (int, float), "Z coordinate")
        check_type(vx, (int, float), "X velocity")
        check_type(vy, (int, float), "Y velocity")
        check_type(vz, (int, float), "Z velocity")
        check_type(elevation_range, tuple, "Elevation range")
        check_type(azimuth_range, tuple, "Azimuth range")
        check_range(elevation_range[0], -90.0, 90.0, "Elevation min")
        check_range(elevation_range[1], -90.0, 90.0, "Elevation max")
        if elevation_range[0] > elevation_range[1]:
            raise ValueError("Elevation min must be less than or equal to elevation max")
        check_range(azimuth_range[0], 0.0, 360.0, "Azimuth min")
        check_range(azimuth_range[1], 0.0, 360.0, "Azimuth max")
        if azimuth_range[0] > azimuth_range[1]:
            raise ValueError("Azimuth min must be less than or equal to azimuth max")

        self._celestial_body = celestial_body
        self._code = code
        self._name = name
        self._x = float(x)
        self._y = float(y)
        self._z = float(z)
        self._vx = float(vx)
        self._vy = float(vy)
        self._vz = float(vz)
        self._elevation_range = elevation_range
        self._azimuth_range = azimuth_range

        logger.info(f"Initialized Station '{code}' on {celestial_body.get_name()} at ({x}, {y}, {z}) m")

    def get_celestial_body(self) -> CelestialBody:
        return self._celestial_body

    def get_code(self) -> str:
        return self._code

    def get_name(self) -> str:
        return self._name

    def get_x(self) -> float:
        return self._x

    def get_y(self) -> float:
        return self._y

    def get_z(self) -> float:
        return self._z

    def get_vx(self) -> float:
        return self._vx

    def get_vy(self) -> float:
        return self._vy

    def get_vz(self) -> float:
        return self._vz

    def get_coordinates(self) -> Tuple[float, float, float]:
        return (self._x, self._y, self._z)

    def get_velocities(self) -> Tuple[float, float, float]:
        return (self._vx, self._vy, self._vz)

    def get_coordinates_and_velocities(self) -> Tuple[float, float, float, float, float, float]:
        return (self._x, self._y, self._z, self._vx, self._vy, self._vz)

    def get_elevation_range(self) -> Tuple[float, float]:
        return self._elevation_range

    def get_azimuth_range(self) -> Tuple[float, float]:
        return self._azimuth_range

    def set_celestial_body(self, celestial_body: CelestialBody) -> None:
        check_type(celestial_body, CelestialBody, "Celestial body")
        self._celestial_body = celestial_body
        logger.info(f"Set celestial body to '{celestial_body.get_name()}' for Station '{self._code}'")

    def set_code(self, code: str) -> None:
        check_non_empty_string(code, "Station code")
        self._code = code
        logger.info(f"Set code '{code}' for Station")

    def set_name(self, name: str) -> None:
        check_non_empty_string(name, "Station name")
        self._name = name
        logger.info(f"Set name '{name}' for Station '{self._code}'")

    def set_coordinates(self, coordinates: Tuple[float, float, float]) -> None:
        check_type(coordinates, tuple, "Coordinates")
        if len(coordinates) != 3:
            raise ValueError("Coordinates must be a tuple of 3 floats")
        for i, coord in enumerate(coordinates):
            check_type(coord, (int, float), f"Coordinate {i}")
        self._x, self._y, self._z = map(float, coordinates)
        logger.info(f"Set coordinates to {coordinates} for Station '{self._code}'")

    def set_velocities(self, velocities: Tuple[float, float, float]) -> None:
        check_type(velocities, tuple, "Velocities")
        if len(velocities) != 3:
            raise ValueError("Velocities must be a tuple of 3 floats")
        for i, vel in enumerate(velocities):
            check_type(vel, (int, float), f"Velocity {i}")
        self._vx, self._vy, self._vz = map(float, velocities)
        logger.info(f"Set velocities to {velocities} for Station '{self._code}'")

    def set_elevation_range(self, elevation_range: Tuple[float, float]) -> None:
        check_type(elevation_range, tuple, "Elevation range")
        check_range(elevation_range[0], -90.0, 90.0, "Elevation min")
        check_range(elevation_range[1], -90.0, 90.0, "Elevation max")
        if elevation_range[0] > elevation_range[1]:
            raise ValueError("Elevation min must be less than or equal to elevation max")
        self._elevation_range = elevation_range
        logger.info(f"Set elevation range to {elevation_range} for Station '{self._code}'")

    def set_azimuth_range(self, azimuth_range: Tuple[float, float]) -> None:
        check_type(azimuth_range, tuple, "Azimuth range")
        check_range(azimuth_range[0], 0.0, 360.0, "Azimuth min")
        check_range(azimuth_range[1], 0.0, 360.0, "Azimuth max")
        if azimuth_range[0] > azimuth_range[1]:
            raise ValueError("Azimuth min must be less than or equal to azimuth max")
        self._azimuth_range = azimuth_range
        logger.info(f"Set azimuth range to {azimuth_range} for Station '{self._code}'")

    def to_dict(self) -> dict:
        logger.info(f"Converted Station '{self._code}' to dictionary")
        return {
            "type": "Station",
            "code": self._code,
            "name": self._name,
            "x": self._x,
            "y": self._y,
            "z": self._z,
            "vx": self._vx,
            "vy": self._vy,
            "vz": self._vz,
            "elevation_range": self._elevation_range,
            "azimuth_range": self._azimuth_range,
            "isactive": self.isactive,
            # Добавляем информацию о celestial_body
            "celestial_body_id": self._celestial_body.get_body_id(),
            "celestial_body_name": self._celestial_body.get_name()
        }

    @classmethod
    def from_dict(cls, data: dict, celestial_body: CelestialBody) -> 'Station':
        required_keys = {"code", "name", "x", "y", "z", "vx", "vy", "vz", "elevation_range", "azimuth_range", "isactive"}
        if not all(key in data for key in required_keys):
            raise ValueError(f"Dictionary must contain keys: {required_keys}")
        # Проверяем, что переданный celestial_body соответствует данным в словаре
        if "celestial_body_id" in data and data["celestial_body_id"] != celestial_body.get_body_id():
            raise ValueError(
                f"Celestial body ID mismatch: expected {data['celestial_body_id']}, got {celestial_body.get_body_id()}"
            )
        if "celestial_body_name" in data and data["celestial_body_name"] != celestial_body.get_name():
            raise ValueError(
                f"Celestial body name mismatch: expected {data['celestial_body_name']}, got {celestial_body.get_name()}"
            )
        station = cls(
            celestial_body=celestial_body,  # Передаём celestial_body
            code=data["code"],
            name=data["name"],
            x=data["x"],
            y=data["y"],
            z=data["z"],
            vx=data["vx"],
            vy=data["vy"],
            vz=data["vz"],
            elevation_range=tuple(data["elevation_range"]),
            azimuth_range=tuple(data["azimuth_range"]),
            isactive=data["isactive"]
        )
        logger.info(f"Created Station '{data['code']}' from dictionary")
        return station

    def __repr__(self) -> str:
        return (f"Station(code='{self._code}', name='{self._name}', "
                f"position=({self._x}, {self._y}, {self._z}), "
                f"velocity=({self._vx}, self._vy, self._vz), "
                f"elevation_range={self._elevation_range}, "
                f"azimuth_range={self._azimuth_range}, isactive={self.isactive})")