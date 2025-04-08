import unittest
import warnings
import erfa
from astropy.time import Time
from jplephem.spk import SPK
import numpy as np
from common.utils.logging_setup import logger
from common.utils.validation import check_type, check_non_empty_string, check_positive, check_range
#
# Импорты классов
from unit_visa.base.celestialBodies import CelestialBody
from unit_visa.base.stations import Station
from unit_visa.base.stations_collection import Stations

# Подавляем предупреждения от erfa
warnings.filterwarnings("ignore", category=erfa.ErfaWarning)


ephemeris_name = 'de440.bsp'

class TestCelestialBodyStationAndStations(unittest.TestCase):
    def setUp(self):
        """Set up the test environment before each test."""
        # Настраиваем логирование
        logger.setLevel("DEBUG")
        logger.info("Setting up test environment")

        # Загружаем файл эфемерид DE440
        try:
            self.ephemeris = SPK.open(ephemeris_name)
            logger.info("Successfully loaded DE440 ephemeris file")
            # Логируем доступные пары (center, target) в эфемериде
            available_pairs = list(self.ephemeris.pairs.keys())
            logger.info(f"Available (center, target) pairs in ephemeris: {available_pairs}")
        except FileNotFoundError:
            logger.info(f"DE440 ephemeris file ({ephemeris_name}) not found. Please download it from JPL.")
            self.skipTest(f"DE440 ephemeris file ({ephemeris_name}) not found. Please download it from JPL.")

        # Создаём тестовый объект CelestialBody (Земля, JPL ID 399)
        logger.info("Creating CelestialBody for Earth (ID 399)")
        self.earth = CelestialBody(
            body_id=399,
            name="Earth",
            mu=398600.4418e9,
            ephemeris=self.ephemeris,
            default_epoch=Time("2000-01-01T12:00:00", scale='utc')
        )

        # Создаём тестовый объект CelestialBody (Луна, JPL ID 301)
        logger.info("Creating CelestialBody for Moon (ID 301)")
        self.moon = CelestialBody(
            body_id=301,
            name="Moon",
            mu=4902.8e9,
            ephemeris=self.ephemeris,
            default_epoch=Time("2000-01-01T12:00:00", scale='utc')
        )

        # Создаём тестовую станцию на Земле
        logger.info("Creating Station STN1 on Earth")
        self.station1 = Station(
            celestial_body=self.earth,
            code="STN1",
            name="Test Station 1",
            x=1000.0, y=2000.0, z=3000.0,
            vx=0.1, vy=0.2, vz=0.3,
            elevation_range=(20.0, 85.0),
            azimuth_range=(10.0, 350.0),
            isactive=True
        )

        # Создаём вторую тестовую станцию на Земле
        logger.info("Creating Station STN2 on Earth")
        self.station2 = Station(
            celestial_body=self.earth,
            code="STN2",
            name="Test Station 2",
            x=2000.0, y=3000.0, z=4000.0,
            vx=0.4, vy=0.5, vz=0.6,
            elevation_range=(15.0, 80.0),
            azimuth_range=(5.0, 355.0),
            isactive=False  # Неактивная станция
        )

        # Создаём третью тестовую станцию на Луне
        logger.info("Creating Station STN3 on Moon")
        self.station3 = Station(
            celestial_body=self.moon,
            code="STN3",
            name="Test Station 3",
            x=500.0, y=1500.0, z=2500.0,
            vx=0.7, vy=0.8, vz=0.9,
            elevation_range=(25.0, 75.0),
            azimuth_range=(0.0, 360.0),
            isactive=True
        )

    def tearDown(self):
        """Clean up after each test."""
        logger.info("Tearing down test environment")
        self.ephemeris.close()

    # Тесты для CelestialBody
    def test_celestial_body_initialization(self):
        """Test the initialization of a CelestialBody object."""
        logger.info("Testing CelestialBody initialization")
        self.assertEqual(self.earth.get_body_id(), 399)
        self.assertEqual(self.earth.get_name(), "Earth")
        self.assertEqual(self.earth.get_mu(), 398600.4418e9)
        self.assertEqual(self.earth.get_default_epoch().isot, "2000-01-01T12:00:00.000")
        self.assertTrue(self.earth.isactive)
        logger.info("CelestialBody initialization test passed")

    def test_celestial_body_invalid_initialization(self):
        """Test initialization of CelestialBody with invalid parameters."""
        logger.info("Testing CelestialBody invalid initialization")

        # Неверный тип body_id
        logger.info("Testing invalid body_id type")
        with self.assertRaises(TypeError):
            CelestialBody(
                body_id="399",  # Должно быть int
                name="Earth",
                mu=398600.4418e9,
                ephemeris=self.ephemeris
            )

        # Пустое имя
        logger.info("Testing empty name")
        with self.assertRaises(ValueError):
            CelestialBody(
                body_id=399,
                name="",
                mu=398600.4418e9,
                ephemeris=self.ephemeris
            )

        # Отрицательный mu
        logger.info("Testing negative mu")
        with self.assertRaises(ValueError):
            CelestialBody(
                body_id=399,
                name="Earth",
                mu=-398600.4418e9,
                ephemeris=self.ephemeris
            )

        # Несуществующий body_id
        logger.info("Testing invalid body_id")
        with self.assertRaises(ValueError):
            CelestialBody(
                body_id=9999,  # Несуществующий ID
                name="Invalid",
                mu=1.0,
                ephemeris=self.ephemeris
            )
        logger.info("CelestialBody invalid initialization test passed")

    def test_celestial_body_get_state_vector(self):
        """Test retrieving the state vector of a CelestialBody."""
        logger.info("Testing CelestialBody get_state_vector")
        time = Time("2025-04-08T12:00:00", scale='utc')
        logger.info(f"Requesting state vector at time: {time.isot}")
        position, velocity = self.earth.get_state_vector(time)

        # Проверяем, что возвращаются numpy массивы
        logger.info(f"Position: {position}, Velocity: {velocity}")
        self.assertIsInstance(position, np.ndarray)
        self.assertIsInstance(velocity, np.ndarray)
        self.assertEqual(position.shape, (3,))
        self.assertEqual(velocity.shape, (3,))

        # Проверяем, что значения не нулевые (Земля должна иметь ненулевую позицию и скорость)
        self.assertFalse(np.allclose(position, np.zeros(3)))
        self.assertFalse(np.allclose(velocity, np.zeros(3)))

        # Проверяем, что значения для J2000 (default_epoch) отличаются
        logger.info("Requesting state vector at default epoch (J2000)")
        position_default, velocity_default = self.earth.get_state_vector()
        logger.info(f"Default Position: {position_default}, Default Velocity: {velocity_default}")
        self.assertFalse(np.allclose(position, position_default))
        self.assertFalse(np.allclose(velocity, velocity_default))
        logger.info("CelestialBody get_state_vector test passed")

    def test_celestial_body_invalid_time(self):
        """Test state vector retrieval with an invalid time."""
        logger.info("Testing CelestialBody invalid time")
        # Время вне диапазона DE440 (DE440 покрывает примерно 1550-2650 годы)
        invalid_time = Time("3000-01-01T00:00:00", scale='utc')
        logger.info(f"Requesting state vector at invalid time: {invalid_time.isot}")
        with self.assertRaises(ValueError):
            self.earth.get_state_vector(invalid_time)
        logger.info("CelestialBody invalid time test passed")

    def test_celestial_body_serialization(self):
        """Test serialization and deserialization of a CelestialBody."""
        logger.info("Testing CelestialBody serialization")
        body_dict = self.earth.to_dict()
        logger.info(f"Serialized dict: {body_dict}")
        self.assertEqual(body_dict["body_id"], 399)
        self.assertEqual(body_dict["name"], "Earth")
        self.assertEqual(body_dict["mu"], 398600.4418e9)
        self.assertEqual(body_dict["default_epoch"], "2000-01-01T12:00:00.000")

        # Десериализация
        logger.info("Deserializing CelestialBody")
        new_body = CelestialBody.from_dict(body_dict, self.ephemeris)
        self.assertEqual(new_body.get_body_id(), self.earth.get_body_id())
        self.assertEqual(new_body.get_name(), self.earth.get_name())
        self.assertEqual(new_body.get_mu(), self.earth.get_mu())
        self.assertEqual(new_body.get_default_epoch().isot, self.earth.get_default_epoch().isot)
        self.assertEqual(new_body.isactive, self.earth.isactive)
        logger.info("CelestialBody serialization test passed")

    def test_celestial_body_setters(self):
        """Test setters for CelestialBody."""
        logger.info("Testing CelestialBody setters")
        self.earth.set_body_id(301)  # Луна
        self.assertEqual(self.earth.get_body_id(), 301)

        self.earth.set_name("Moon")
        self.assertEqual(self.earth.get_name(), "Moon")

        self.earth.set_mu(4902.8e9)  # Гравитационный параметр Луны
        self.assertEqual(self.earth.get_mu(), 4902.8e9)

        new_epoch = Time("2025-01-01T00:00:00", scale='utc')
        self.earth.set_default_epoch(new_epoch)
        self.assertEqual(self.earth.get_default_epoch().isot, "2025-01-01T00:00:00.000")

        # Проверяем активацию/деактивацию
        self.earth.deactivate()
        self.assertFalse(self.earth.isactive)
        self.earth.activate()
        self.assertTrue(self.earth.isactive)
        logger.info("CelestialBody setters test passed")

    # Тесты для Station
    def test_station_initialization(self):
        """Test the initialization of a Station object."""
        logger.info("Testing Station initialization")
        self.assertEqual(self.station1.get_code(), "STN1")
        self.assertEqual(self.station1.get_name(), "Test Station 1")
        self.assertEqual(self.station1.get_celestial_body().get_name(), "Earth")
        self.assertEqual(self.station1.get_coordinates(), (1000.0, 2000.0, 3000.0))
        self.assertEqual(self.station1.get_velocities(), (0.1, 0.2, 0.3))
        self.assertEqual(self.station1.get_elevation_range(), (20.0, 85.0))
        self.assertEqual(self.station1.get_azimuth_range(), (10.0, 350.0))
        self.assertTrue(self.station1.isactive)
        logger.info("Station initialization test passed")

    def test_station_invalid_initialization(self):
        """Test initialization of Station with invalid parameters."""
        logger.info("Testing Station invalid initialization")

        # Неверный тип celestial_body
        logger.info("Testing invalid celestial_body type")
        with self.assertRaises(TypeError):
            Station(
                celestial_body="Earth",  # Должно быть CelestialBody
                code="STN2",
                name="Invalid Station"
            )

        # Пустой код
        logger.info("Testing empty code")
        with self.assertRaises(ValueError):
            Station(
                celestial_body=self.earth,
                code="",
                name="Invalid Station"
            )

        # Неверный тип координат
        logger.info("Testing invalid coordinate type")
        with self.assertRaises(TypeError):
            Station(
                celestial_body=self.earth,
                code="STN2",
                name="Invalid Station",
                x="1000.0"  # Должно быть float
            )

        # Неверный диапазон возвышения
        logger.info("Testing invalid elevation range")
        with self.assertRaises(ValueError):
            Station(
                celestial_body=self.earth,
                code="STN2",
                name="Invalid Station",
                elevation_range=(100.0, 90.0)  # min > max
            )
        logger.info("Station invalid initialization test passed")

    def test_station_getters(self):
        """Test getter methods for Station."""
        logger.info("Testing Station getters")
        self.assertEqual(self.station1.get_x(), 1000.0)
        self.assertEqual(self.station1.get_y(), 2000.0)
        self.assertEqual(self.station1.get_z(), 3000.0)
        self.assertEqual(self.station1.get_vx(), 0.1)
        self.assertEqual(self.station1.get_vy(), 0.2)
        self.assertEqual(self.station1.get_vz(), 0.3)
        self.assertEqual(self.station1.get_coordinates_and_velocities(), (1000.0, 2000.0, 3000.0, 0.1, 0.2, 0.3))
        logger.info("Station getters test passed")

    def test_station_setters(self):
        """Test setter methods for Station."""
        logger.info("Testing Station setters")
        self.station1.set_code("STN2")
        self.assertEqual(self.station1.get_code(), "STN2")

        self.station1.set_name("New Station")
        self.assertEqual(self.station1.get_name(), "New Station")

        self.station1.set_coordinates((1500.0, 2500.0, 3500.0))
        self.assertEqual(self.station1.get_coordinates(), (1500.0, 2500.0, 3500.0))

        self.station1.set_velocities((0.4, 0.5, 0.6))
        self.assertEqual(self.station1.get_velocities(), (0.4, 0.5, 0.6))

        self.station1.set_elevation_range((25.0, 80.0))
        self.assertEqual(self.station1.get_elevation_range(), (25.0, 80.0))

        self.station1.set_azimuth_range((5.0, 355.0))
        self.assertEqual(self.station1.get_azimuth_range(), (5.0, 355.0))

        # Проверяем активацию/деактивацию
        self.station1.deactivate()
        self.assertFalse(self.station1.isactive)
        self.station1.activate()
        self.assertTrue(self.station1.isactive)
        logger.info("Station setters test passed")

    def test_station_serialization(self):
        """Test serialization and deserialization of a Station."""
        logger.info("Testing Station serialization")
        station_dict = self.station1.to_dict()
        logger.info(f"Serialized dict: {station_dict}")
        self.assertEqual(station_dict["code"], "STN1")
        self.assertEqual(station_dict["name"], "Test Station 1")
        self.assertEqual(station_dict["x"], 1000.0)
        self.assertEqual(station_dict["elevation_range"], (20.0, 85.0))

        # Десериализация
        logger.info("Deserializing Station")
        new_station = Station.from_dict(station_dict, celestial_body=self.earth)
        self.assertEqual(new_station.get_code(), self.station1.get_code())
        self.assertEqual(new_station.get_name(), self.station1.get_name())
        self.assertEqual(new_station.get_coordinates(), self.station1.get_coordinates())
        self.assertEqual(new_station.get_velocities(), self.station1.get_velocities())
        self.assertEqual(new_station.get_elevation_range(), self.station1.get_elevation_range())
        self.assertEqual(new_station.get_azimuth_range(), self.station1.get_azimuth_range())
        self.assertEqual(new_station.isactive, self.station1.isactive)
        logger.info("Station serialization test passed")

    def test_station_and_celestial_body_integration(self):
        """Test integration between Station and CelestialBody."""
        logger.info("Testing Station and CelestialBody integration")
        # Проверяем, что станция может получить координаты своего небесного тела
        time = Time("2025-04-08T12:00:00", scale='utc')
        logger.info(f"Requesting celestial body state vector at time: {time.isot}")
        body_position, body_velocity = self.station1.get_celestial_body().get_state_vector(time)
        logger.info(f"Celestial body position: {body_position}, velocity: {body_velocity}")
        self.assertIsInstance(body_position, np.ndarray)
        self.assertIsInstance(body_velocity, np.ndarray)

        # Проверяем, что можно изменить небесное тело у станции
        self.station1.set_celestial_body(self.moon)
        self.assertEqual(self.station1.get_celestial_body().get_name(), "Moon")
        logger.info("Station and CelestialBody integration test passed")

    # Тесты для Stations
    def test_stations_management(self):
        """Test adding, removing, and retrieving stations."""
        logger.info("Testing Stations management")
        stations = Stations()
        
        # Добавляем станции
        stations.add_station(self.station1)
        stations.add_station(self.station2)
        stations.add_station(self.station3)
        self.assertEqual(len(stations.get_all_stations()), 3)
        
        # Проверяем получение станции
        retrieved_station = stations.get_station("STN1")
        self.assertEqual(retrieved_station.get_code(), "STN1")
        
        # Проверяем фильтрацию по небесному телу
        earth_stations = stations.get_stations_by_celestial_body(self.earth)
        self.assertEqual(len(earth_stations), 2)
        moon_stations = stations.get_stations_by_celestial_body(self.moon)
        self.assertEqual(len(moon_stations), 1)
        
        # Проверяем фильтрацию активных станций
        active_stations = stations.get_active_stations()
        self.assertEqual(len(active_stations), 2)  # STN1 и STN3 активны
        
        # Удаляем станцию
        stations.remove_station("STN1")
        self.assertEqual(len(stations.get_all_stations()), 2)
        
        # Проверяем, что удалённая станция больше не доступна
        self.assertIsNone(stations.get_station("STN1"))
        logger.info("Stations management test passed")

    def test_stations_serialization(self):
        """Test serialization and deserialization of Stations."""
        logger.info("Testing Stations serialization")
        stations = Stations()
        stations.add_station(self.station1)
        stations.add_station(self.station2)
        
        # Сериализация
        stations_dict = stations.to_dict()
        self.assertEqual(len(stations_dict["stations"]), 2)
        
        # Десериализация
        celestial_bodies = {399: self.earth, 301: self.moon}
        new_stations = Stations.from_dict(stations_dict, celestial_bodies)
        self.assertEqual(len(new_stations.get_all_stations()), 2)
        self.assertEqual(new_stations.get_station("STN1").get_name(), "Test Station 1")
        self.assertEqual(new_stations.get_station("STN2").get_name(), "Test Station 2")
        logger.info("Stations serialization test passed")

    # Дополнительные тесты для сложных сценариев
    def test_stations_duplicate_code(self):
        """Test adding stations with duplicate codes."""
        logger.info("Testing Stations duplicate code handling")
        stations = Stations()
        stations.add_station(self.station1)
        
        # Пытаемся добавить станцию с таким же кодом
        duplicate_station = Station(
            celestial_body=self.earth,
            code="STN1",  # Такой же код, как у station1
            name="Duplicate Station",
            x=5000.0, y=6000.0, z=7000.0
        )
        with self.assertRaises(ValueError):
            stations.add_station(duplicate_station)
        self.assertEqual(len(stations.get_all_stations()), 1)  # Количество станций не изменилось
        logger.info("Stations duplicate code test passed")

    def test_stations_remove_nonexistent(self):
        """Test removing a station that doesn't exist."""
        logger.info("Testing Stations remove nonexistent station")
        stations = Stations()
        stations.add_station(self.station1)
        
        # Пытаемся удалить несуществующую станцию
        with self.assertRaises(ValueError):
            stations.remove_station("STN999")
        self.assertEqual(len(stations.get_all_stations()), 1)  # Количество станций не изменилось
        logger.info("Stations remove nonexistent test passed")

    def test_stations_serialization_with_missing_celestial_body(self):
        """Test deserialization of Stations with a missing celestial body."""
        logger.info("Testing Stations serialization with missing celestial body")
        stations = Stations()
        stations.add_station(self.station1)
        
        stations_dict = stations.to_dict()
        
        # Десериализация с отсутствующим celestial_body
        celestial_bodies = {301: self.moon}  # Нет ID 399 (Earth)
        with self.assertRaises(ValueError):
            Stations.from_dict(stations_dict, celestial_bodies)
        logger.info("Stations serialization with missing celestial body test passed")

    def test_stations_filtering_with_no_matches(self):
        """Test filtering stations when there are no matches."""
        logger.info("Testing Stations filtering with no matches")
        stations = Stations()
        stations.add_station(self.station1)  # На Земле
        stations.add_station(self.station2)  # На Земле
    
        # Создаём небесное тело, которого нет в станциях
        mars = CelestialBody(
            body_id=4,  # Исправлено с 499 на 4
            name="Mars",
            mu=42828.3e9,
            ephemeris=self.ephemeris
        )
    
        # Проверяем фильтрацию по небесному телу, которого нет
        mars_stations = stations.get_stations_by_celestial_body(mars)
        self.assertEqual(len(mars_stations), 0)
    
        # Деактивируем все станции и проверяем фильтрацию активных
        self.station1.deactivate()
        self.station2.deactivate()
        active_stations = stations.get_active_stations()
        self.assertEqual(len(active_stations), 0)
        logger.info("Stations filtering with no matches test passed")

if __name__ == "__main__":
    unittest.main()