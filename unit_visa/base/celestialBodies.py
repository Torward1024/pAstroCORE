from common.base.base_entity import BaseEntity
from common.utils.validation import check_type, check_non_empty_string, check_positive
from common.utils.logging_setup import logger
from typing import Optional, Tuple
from astropy.time import Time
import numpy as np
from jplephem.spk import SPK

class CelestialBody(BaseEntity):
    """Class representing a celestial body with dynamically computed positions and velocities from JPL ephemerides."""
    def __init__(self, body_id: int, name: str, mu: float, ephemeris: SPK,
                 default_epoch: Optional[Time] = None, isactive: bool = True):
        super().__init__(isactive)
        check_type(body_id, int, "Body ID")
        check_non_empty_string(name, "Celestial body name")
        check_type(mu, (int, float), "Gravitational parameter")
        check_positive(mu, "Gravitational parameter")
        check_type(ephemeris, SPK, "Ephemeris")
        if default_epoch is not None:
            check_type(default_epoch, Time, "Default epoch")

        # Проверяем, поддерживает ли эфемерида указанное тело
        self._check_ephemeris_support(ephemeris, body_id)

        self._body_id = body_id
        self._name = name
        self._mu = mu
        self._ephemeris = ephemeris
        self._default_epoch = default_epoch if default_epoch is not None else Time("2000-01-01T12:00:00", scale='utc')

        logger.info(f"Initialized CelestialBody '{name}' (ID: {body_id}) with mu={mu} m^3/s^2")

    def _check_ephemeris_support(self, ephemeris: SPK, body_id: int) -> None:
        try:
            # Проверяем прямой ID (например, 4 для Марса)
            ephemeris[0, body_id]
            logger.info(f"Ephemeris supports body ID {body_id} directly")
        except KeyError:
            # Если body_id в формате JPL (например, 499 для Марса), преобразуем в короткий ID (4)
            if 100 <= body_id <= 999 and body_id % 100 == 99:
                short_id = body_id // 100
                if (0, short_id) in ephemeris.pairs:
                    logger.info(f"Ephemeris supports body ID {body_id} as short ID {short_id}")
                    return
            # Проверяем через барицентр (для тел вроде Земли и Луны)
            if body_id == 301:  # Специальный случай для Луны
                barycenter_id = 3  # Барицентр Земли
                if (0, barycenter_id) in ephemeris.pairs and (barycenter_id, body_id) in ephemeris.pairs:
                    logger.info(f"Ephemeris supports Moon (301) via barycenter ({barycenter_id})")
                    return
            # Общий случай для тел вроде Земли (399)
            barycenter_id = body_id // 100  # Для 399 -> 3, для 301 -> 3
            if (0, barycenter_id) in ephemeris.pairs and (barycenter_id, body_id) in ephemeris.pairs:
                logger.info(f"Ephemeris supports body ID {body_id} via barycenter ({barycenter_id})")
            else:
                logger.error(f"Body ID {body_id} is not supported by the provided ephemeris")
                raise ValueError(f"Body ID {body_id} is not supported by the provided ephemeris")

    def get_state_vector(self, time: Optional[Time] = None) -> Tuple[np.ndarray, np.ndarray]:
        """Retrieve the position and velocity of the celestial body at a specific time."""
        if time is None:
            time = self._default_epoch
        check_type(time, Time, "Time")

        # Преобразуем время в юлианские дни (JD) для jplephem
        jd = time.tdb.jd
        logger.debug(f"Computing state vector for JD {jd}")

        # Проверяем, что время находится в пределах диапазона эфемерид
        jd_start, jd_end = self._ephemeris.segments[0].start_jd, self._ephemeris.segments[-1].end_jd
        if not (jd_start <= jd <= jd_end):
            logger.error(f"Time {time.isot} (JD {jd}) is outside ephemeris range ({jd_start} to {jd_end})")
            raise ValueError(f"Time {time.isot} (JD {jd}) is outside ephemeris range ({jd_start} to {jd_end})")

        try:
            # Для Земли (399) и Луны (301) нужно учитывать барицентр Земля-Луна (3)
            if self._body_id in (399, 301):
                # Сначала получаем позицию барицентра Земля-Луна относительно Солнечной системы
                pos_barycenter_km, vel_barycenter_km_per_s = self._ephemeris[0, 3].compute_and_differentiate(jd)
                logger.debug(f"Barycenter (3) position: {pos_barycenter_km}, velocity: {vel_barycenter_km_per_s}")

                # Затем получаем позицию тела относительно барицентра Земля-Луна
                pos_relative_km, vel_relative_km_per_s = self._ephemeris[3, self._body_id].compute_and_differentiate(jd)
                logger.debug(f"Body {self._body_id} relative position: {pos_relative_km}, velocity: {vel_relative_km_per_s}")

                # Суммируем векторы
                position_km = pos_barycenter_km + pos_relative_km
                velocity_km_per_s = vel_barycenter_km_per_s + vel_relative_km_per_s
            else:
                # Для других тел получаем данные напрямую
                position_km, velocity_km_per_s = self._ephemeris[0, self._body_id].compute_and_differentiate(jd)
                logger.debug(f"Direct position for body {self._body_id}: {position_km}, velocity: {velocity_km_per_s}")

            # Преобразуем из километров в метры
            position = position_km * 1000.0  # км -> м
            velocity = velocity_km_per_s * 1000.0  # км/с -> м/с

            logger.debug(f"Computed state vector for '{self._name}' at {time.isot}: "
                         f"position={position} m, velocity={velocity} m/s")
            return position, velocity
        except Exception as e:
            logger.error(f"Failed to compute state vector for '{self._name}' at {time.isot}: {str(e)}")
            raise RuntimeError(f"Failed to compute state vector: {e}")

    def activate(self):
        """Activate the celestial body, marking it as active."""
        return super().activate()

    def deactivate(self):
        """Deactivate the celestial body, marking it as inactive."""
        return super().deactivate()

    def get_body_id(self) -> int:
        return self._body_id

    def get_name(self) -> str:
        return self._name

    def get_mu(self) -> float:
        return self._mu

    def get_default_epoch(self) -> Time:
        return self._default_epoch

    def set_celestial_body(self, body_id: int, name: str, mu: float, ephemeris: SPK,
                          default_epoch: Optional[Time] = None, isactive: bool = True) -> None:
        check_type(body_id, int, "Body ID")
        check_non_empty_string(name, "Celestial body name")
        check_type(mu, (int, float), "Gravitational parameter")
        check_positive(mu, "Gravitational parameter")
        check_type(ephemeris, SPK, "Ephemeris")
        if default_epoch is not None:
            check_type(default_epoch, Time, "Default epoch")

        self._check_ephemeris_support(ephemeris, body_id)

        self._body_id = body_id
        self._name = name
        self._mu = mu
        self._ephemeris = ephemeris
        self._default_epoch = default_epoch if default_epoch is not None else Time("2000-01-01T12:00:00", scale='utc')
        self.isactive = isactive
        logger.info(f"Set CelestialBody '{name}' (ID: {body_id}) with new parameters")

    def set_body_id(self, body_id: int) -> None:
        check_type(body_id, int, "Body ID")
        self._check_ephemeris_support(self._ephemeris, body_id)
        self._body_id = body_id
        logger.info(f"Set body ID {body_id} for CelestialBody '{self._name}'")

    def set_name(self, name: str) -> None:
        check_non_empty_string(name, "Celestial body name")
        self._name = name
        logger.info(f"Set name '{name}' for CelestialBody (ID: {self._body_id})")

    def set_mu(self, mu: float) -> None:
        check_type(mu, (int, float), "Gravitational parameter")
        check_positive(mu, "Gravitational parameter")
        self._mu = mu
        logger.info(f"Set mu={mu} m^3/s^2 for CelestialBody '{self._name}'")

    def set_default_epoch(self, default_epoch: Time) -> None:
        check_type(default_epoch, Time, "Default epoch")
        self._default_epoch = default_epoch
        logger.info(f"Set default epoch to {default_epoch.isot} for CelestialBody '{self._name}'")

    def set_ephemeris(self, ephemeris: SPK) -> None:
        check_type(ephemeris, SPK, "Ephemeris")
        self._check_ephemeris_support(ephemeris, self._body_id)
        self._ephemeris = ephemeris
        logger.info(f"Set new ephemeris for CelestialBody '{self._name}'")

    def to_dict(self) -> dict:
        logger.info(f"Converted CelestialBody '{self._name}' to dictionary")
        return {
            "type": "CelestialBody",
            "body_id": self._body_id,
            "name": self._name,
            "mu": self._mu,
            "default_epoch": self._default_epoch.isot,
            "isactive": self.isactive
        }

    @classmethod
    def from_dict(cls, data: dict, ephemeris: SPK) -> 'CelestialBody':
        required_keys = {"body_id", "name", "mu", "default_epoch", "isactive"}
        if not all(key in data for key in required_keys):
            raise ValueError(f"Dictionary must contain keys: {required_keys}")
        default_epoch = Time(data["default_epoch"], scale='utc')
        body = cls(
            body_id=data["body_id"],
            name=data["name"],
            mu=data["mu"],
            ephemeris=ephemeris,
            default_epoch=default_epoch,
            isactive=data["isactive"]
        )
        logger.info(f"Created CelestialBody '{data['name']}' from dictionary")
        return body

    def __repr__(self) -> str:
        return (f"CelestialBody(body_id={self._body_id}, name='{self._name}', mu={self._mu}, "
                f"default_epoch={self._default_epoch.isot}, isactive={self.isactive})")
    
