# super/configurator.py
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict
from base.observation import Observation, CatalogManager
from base.sources import Source, Sources
from base.telescopes import Telescope, SpaceTelescope, Telescopes
from base.frequencies import IF, Frequencies
from base.scans import Scan, Scans
from utils.validation import check_type, check_non_empty_string
from utils.logging_setup import logger

class Configurator(ABC):
    """Абстрактный супер-класс для конфигурирования одиночного наблюдения."""

    def __init__(self, catalog_manager: CatalogManager):
        """Инициализация конфигуратора с менеджером каталогов.

        Args:
            catalog_manager (CatalogManager): Экземпляр менеджера каталогов.
        """
        check_type(catalog_manager, CatalogManager, "catalog_manager")
        self.catalog_manager = catalog_manager
        logger.info("Initialized Configurator with CatalogManager")

    @abstractmethod
    def configure_observation(self, observation: Observation) -> None:
        """Абстрактный метод для полной конфигурации наблюдения."""
        pass

    # --- Общие методы конфигурации ---

    def set_observation_code(self, observation: Observation, code: str) -> None:
        """Установить код наблюдения."""
        check_type(observation, Observation, "observation")
        check_non_empty_string(code, "code")
        observation.set_observation_code(code)
        logger.info(f"Set observation code to '{code}'")

    def set_observation_type(self, observation: Observation, obs_type: str) -> None:
        """Установить тип наблюдения."""
        check_type(observation, Observation, "observation")
        check_non_empty_string(obs_type, "obs_type")
        observation.set_observation_type(obs_type)
        logger.info(f"Set observation type to '{obs_type}' for '{observation.get_observation_code()}'")

    def add_source(self, observation: Observation, source_name: str) -> None:
        """Добавить источник из каталога."""
        check_type(observation, Observation, "observation")
        check_non_empty_string(source_name, "source_name")
        source = self.catalog_manager.get_source(source_name)
        if not source:
            logger.error(f"Source '{source_name}' not found in catalog")
            raise ValueError(f"Source '{source_name}' not found in catalog")
        observation.set_sources(observation.get_sources() or Sources())
        observation.get_sources().add_source(source)
        logger.info(f"Added source '{source_name}' to observation '{observation.get_observation_code()}'")

    def add_sources(self, observation: Observation, source_names: List[str]) -> None:
        """Добавить несколько источников."""
        check_type(observation, Observation, "observation")
        check_type(source_names, list, "source_names")
        for name in source_names:
            self.add_source(observation, name)

    def remove_source(self, observation: Observation, source_name: str) -> None:
        """Удалить источник."""
        check_type(observation, Observation, "observation")
        check_non_empty_string(source_name, "source_name")
        sources = observation.get_sources()
        if not sources:
            logger.warning(f"No sources to remove from '{observation.get_observation_code()}'")
            return
        source = self.catalog_manager.get_source(source_name)
        if not source or source not in sources.get_all_sources():
            logger.warning(f"Source '{source_name}' not found in '{observation.get_observation_code()}'")
            return
        sources.remove_source(source)
        logger.info(f"Removed source '{source_name}' from '{observation.get_observation_code()}'")

    def add_telescope(self, observation: Observation, telescope_code: str) -> None:
        """Добавить телескоп из каталога."""
        check_type(observation, Observation, "observation")
        check_non_empty_string(telescope_code, "telescope_code")
        telescope = self.catalog_manager.get_telescope(telescope_code)
        if not telescope:
            logger.error(f"Telescope '{telescope_code}' not found in catalog")
            raise ValueError(f"Telescope '{telescope_code}' not found in catalog")
        observation.set_telescopes(observation.get_telescopes() or Telescopes())
        observation.get_telescopes().add_telescope(telescope)
        logger.info(f"Added telescope '{telescope_code}' to '{observation.get_observation_code()}'")

    def add_telescopes(self, observation: Observation, telescope_codes: List[str]) -> None:
        """Добавить несколько телескопов."""
        check_type(observation, Observation, "observation")
        check_type(telescope_codes, list, "telescope_codes")
        for code in telescope_codes:
            self.add_telescope(observation, code)

    def remove_telescope(self, observation: Observation, telescope_code: str) -> None:
        """Удалить телескоп."""
        check_type(observation, Observation, "observation")
        check_non_empty_string(telescope_code, "telescope_code")
        telescopes = observation.get_telescopes()
        if not telescopes:
            logger.warning(f"No telescopes to remove from '{observation.get_observation_code()}'")
            return
        telescope = self.catalog_manager.get_telescope(telescope_code)
        if not telescope or telescope not in telescopes.get_all_telescopes():
            logger.warning(f"Telescope '{telescope_code}' not found in '{observation.get_observation_code()}'")
            return
        telescopes.remove_telescope(telescope)
        logger.info(f"Removed telescope '{telescope_code}' from '{observation.get_observation_code()}'")

    def add_frequency(self, observation: Observation, freq: float, bandwidth: float) -> None:
        """Добавить частоту."""
        check_type(observation, Observation, "observation")
        check_type(freq, (int, float), "freq")
        check_type(bandwidth, (int, float), "bandwidth")
        if_obj = IF(freq=freq, bandwidth=bandwidth)
        observation.set_frequencies(observation.get_frequencies() or Frequencies())
        observation.get_frequencies().add_frequency(if_obj)
        logger.info(f"Added frequency {freq} MHz with bandwidth {bandwidth} MHz to '{observation.get_observation_code()}'")

    def add_frequencies(self, observation: Observation, freq_bandwidth_pairs: List[Tuple[float, float]]) -> None:
        """Добавить несколько частот."""
        check_type(observation, Observation, "observation")
        check_type(freq_bandwidth_pairs, list, "freq_bandwidth_pairs")
        for freq, bw in freq_bandwidth_pairs:
            self.add_frequency(observation, freq, bw)

    def remove_frequency(self, observation: Observation, freq: float) -> None:
        """Удалить частоту."""
        check_type(observation, Observation, "observation")
        check_type(freq, (int, float), "freq")
        frequencies = observation.get_frequencies()
        if not frequencies:
            logger.warning(f"No frequencies to remove from '{observation.get_observation_code()}'")
            return
        if_obj = next((f for f in frequencies.get_all_frequencies() if f.get_freq() == freq), None)
        if not if_obj:
            logger.warning(f"Frequency {freq} MHz not found in '{observation.get_observation_code()}'")
            return
        frequencies.remove_frequency(if_obj)
        logger.info(f"Removed frequency {freq} MHz from '{observation.get_observation_code()}'")

    def add_scan(self, observation: Observation, start: float, duration: float, source_name: str,
                 telescope_codes: List[str], freq_bandwidth_pairs: List[Tuple[float, float]], 
                 is_off_source: bool = False) -> None:
        """Добавить скан."""
        check_type(observation, Observation, "observation")
        check_type(start, (int, float), "start")
        check_type(duration, (int, float), "duration")
        check_non_empty_string(source_name, "source_name")
        check_type(telescope_codes, list, "telescope_codes")
        check_type(freq_bandwidth_pairs, list, "freq_bandwidth_pairs")
        check_type(is_off_source, bool, "is_off_source")

        source = self.catalog_manager.get_source(source_name)
        if not source:
            logger.error(f"Source '{source_name}' not found in catalog")
            raise ValueError(f"Source '{source_name}' not found in catalog")

        telescopes = Telescopes()
        for code in telescope_codes:
            telescope = self.catalog_manager.get_telescope(code)
            if not telescope:
                logger.error(f"Telescope '{code}' not found in catalog")
                raise ValueError(f"Telescope '{code}' not found in catalog")
            telescopes.add_telescope(telescope)

        frequencies = Frequencies()
        for freq, bw in freq_bandwidth_pairs:
            frequencies.add_frequency(IF(freq=freq, bandwidth=bw))

        scan = Scan(start=start, duration=duration, source=source, telescopes=telescopes, 
                    frequencies=frequencies, is_off_source=is_off_source)
        observation.set_scans(observation.get_scans() or Scans())
        observation.get_scans().add_scan(scan)
        logger.info(f"Added scan (start={start}, duration={duration}) to '{observation.get_observation_code()}'")

    def remove_scan(self, observation: Observation, start: float) -> None:
        """Удалить скан по времени начала."""
        check_type(observation, Observation, "observation")
        check_type(start, (int, float), "start")
        scans = observation.get_scans()
        if not scans:
            logger.warning(f"No scans to remove from '{observation.get_observation_code()}'")
            return
        scan = next((s for s in scans.get_active_scans() if s.get_start() == start), None)
        if not scan:
            logger.warning(f"Scan with start {start} not found in '{observation.get_observation_code()}'")
            return
        scans.remove_scan(scan)
        logger.info(f"Removed scan with start {start} from '{observation.get_observation_code()}'")

    def configure_from_dict(self, observation: Observation, config: Dict) -> None:
        """Конфигурировать наблюдение из словаря."""
        check_type(observation, Observation, "observation")
        check_type(config, dict, "config")
        if "code" in config:
            self.set_observation_code(observation, config["code"])
        if "type" in config:
            self.set_observation_type(observation, config["type"])
        if "sources" in config:
            self.add_sources(observation, config["sources"])
        if "telescopes" in config:
            self.add_telescopes(observation, config["telescopes"])
        if "frequencies" in config:
            self.add_frequencies(observation, config["frequencies"])
        if "scans" in config:
            for scan_config in config["scans"]:
                self.add_scan(
                    observation,
                    start=scan_config["start"],
                    duration=scan_config["duration"],
                    source_name=scan_config["source"],
                    telescope_codes=scan_config["telescopes"],
                    freq_bandwidth_pairs=scan_config["frequencies"],
                    is_off_source=scan_config.get("is_off_source", False)
                )
        logger.info(f"Configured observation '{observation.get_observation_code()}' from dictionary")

# super/configurator.py (продолжение)

class SingleDishConfigurator(Configurator):
    """Конфигуратор для наблюдений типа SINGLE_DISH."""

    def configure_observation(self, observation: Observation, code: str, telescope_code: str,
                             source_names: List[str], freq_bandwidth_pairs: List[Tuple[float, float]],
                             scans_config: List[Dict]) -> None:
        """Полная конфигурация наблюдения типа SINGLE_DISH.

        Args:
            observation (Observation): Наблюдение для конфигурации.
            code (str): Код наблюдения.
            telescope_code (str): Код единственного телескопа.
            source_names (List[str]): Список источников.
            freq_bandwidth_pairs (List[Tuple[float, float]]): Список пар (частота, полоса).
            scans_config (List[Dict]): Конфигурация сканов.
        """
        check_type(observation, Observation, "observation")
        check_non_empty_string(code, "code")
        check_non_empty_string(telescope_code, "telescope_code")
        check_type(source_names, list, "source_names")
        check_type(freq_bandwidth_pairs, list, "freq_bandwidth_pairs")
        check_type(scans_config, list, "scans_config")

        # Устанавливаем код и тип
        self.set_observation_code(observation, code)
        self.set_observation_type(observation, "SINGLE_DISH")

        # Добавляем один телескоп (SINGLE_DISH допускает только один)
        self.add_telescope(observation, telescope_code)
        if len(observation.get_telescopes().get_all_telescopes()) > 1:
            logger.error("SINGLE_DISH observation can only have one telescope")
            raise ValueError("SINGLE_DISH observation can only have one telescope")

        # Добавляем источники
        self.add_sources(observation, source_names)

        # Добавляем частоты
        self.add_frequencies(observation, freq_bandwidth_pairs)

        # Добавляем сканы (поддерживаем ON/OFF)
        for scan_config in scans_config:
            self.add_scan(
                observation,
                start=scan_config["start"],
                duration=scan_config["duration"],
                source_name=scan_config["source"],
                telescope_codes=[telescope_code],  # Только один телескоп
                freq_bandwidth_pairs=scan_config["frequencies"],
                is_off_source=scan_config.get("is_off_source", False)
            )

        logger.info(f"Fully configured SINGLE_DISH observation '{code}' with {len(source_names)} sources and {len(scans_config)} scans")

    def add_telescope(self, observation: Observation, telescope_code: str) -> None:
        """Переопределённый метод для SINGLE_DISH: только один телескоп."""
        check_type(observation, Observation, "observation")
        check_non_empty_string(telescope_code, "telescope_code")
        if observation.get_telescopes() and observation.get_telescopes().get_all_telescopes():
            logger.error("SINGLE_DISH observation already has a telescope")
            raise ValueError("SINGLE_DISH observation can only have one telescope")
        super().add_telescope(observation, telescope_code)

    def add_telescopes(self, observation: Observation, telescope_codes: List[str]) -> None:
        """Переопределённый метод: запрещаем добавление нескольких телескопов."""
        check_type(observation, Observation, "observation")
        check_type(telescope_codes, list, "telescope_codes")
        if len(telescope_codes) > 1:
            logger.error("SINGLE_DISH observation can only have one telescope")
            raise ValueError("SINGLE_DISH observation can only have one telescope")
        if telescope_codes:
            self.add_telescope(observation, telescope_codes[0])

# super/configurator.py (продолжение)

class VLBIConfigurator(Configurator):
    """Конфигуратор для наблюдений типа VLBI."""

    def configure_observation(self, observation: Observation, code: str, telescope_codes: List[str],
                             source_names: List[str], freq_bandwidth_pairs: List[Tuple[float, float]],
                             scans_config: List[Dict]) -> None:
        """Полная конфигурация наблюдения типа VLBI.

        Args:
            observation (Observation): Наблюдение для конфигурации.
            code (str): Код наблюдения.
            telescope_codes (List[str]): Список кодов телескопов (минимум 2).
            source_names (List[str]): Список источников.
            freq_bandwidth_pairs (List[Tuple[float, float]]): Список пар (частота, полоса).
            scans_config (List[Dict]): Конфигурация сканов.
        """
        check_type(observation, Observation, "observation")
        check_non_empty_string(code, "code")
        check_type(telescope_codes, list, "telescope_codes")
        check_type(source_names, list, "source_names")
        check_type(freq_bandwidth_pairs, list, "freq_bandwidth_pairs")
        check_type(scans_config, list, "scans_config")

        # Устанавливаем код и тип
        self.set_observation_code(observation, code)
        self.set_observation_type(observation, "VLBI")

        # Добавляем телескопы (VLBI требует минимум 2)
        self.add_telescopes(observation, telescope_codes)
        if len(observation.get_telescopes().get_all_telescopes()) < 2:
            logger.error("VLBI observation requires at least two telescopes")
            raise ValueError("VLBI observation requires at least two telescopes")

        # Добавляем источники
        self.add_sources(observation, source_names)

        # Добавляем частоты
        self.add_frequencies(observation, freq_bandwidth_pairs)

        # Добавляем сканы (все телескопы участвуют в каждом скане)
        for scan_config in scans_config:
            self.add_scan(
                observation,
                start=scan_config["start"],
                duration=scan_config["duration"],
                source_name=scan_config["source"],
                telescope_codes=telescope_codes,  # Все телескопы из списка
                freq_bandwidth_pairs=scan_config["frequencies"],
                is_off_source=scan_config.get("is_off_source", False)
            )

        logger.info(f"Fully configured VLBI observation '{code}' with {len(telescope_codes)} telescopes, {len(source_names)} sources, and {len(scans_config)} scans")

    def add_telescopes(self, observation: Observation, telescope_codes: List[str]) -> None:
        """Переопределённый метод: проверка на минимум 2 телескопа."""
        check_type(observation, Observation, "observation")
        check_type(telescope_codes, list, "telescope_codes")
        super().add_telescopes(observation, telescope_codes)
        if len(observation.get_telescopes().get_all_telescopes()) < 2:
            logger.error("VLBI observation requires at least two telescopes")
            raise ValueError("VLBI observation requires at least two telescopes")