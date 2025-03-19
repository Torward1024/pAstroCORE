# base/observation.py
from base.base_entity import BaseEntity
from base.sources import Source, Sources
from base.telescopes import Telescope, SpaceTelescope, Telescopes
from base.frequencies import Frequencies
from base.scans import Scans
from utils.validation import check_type, check_non_empty_string
from utils.logging_setup import logger
from datetime import datetime
from typing import Optional, List, Dict, Any
import re

class Observation(BaseEntity):
    def __init__(self, observation_code: str = "OBS_DEFAULT", sources: Sources = None,
                 telescopes: Telescopes = None, frequencies: Frequencies = None,
                 scans: Scans = None, observation_type: str = "VLBI", isactive: bool = True):
        """Initialize an Observation object."""
        super().__init__(isactive)
        check_type(observation_code, str, "Observation code")
        if observation_type not in ("VLBI", "SINGLE_DISH"):
            logger.error(f"Observation type must be 'VLBI' or 'SINGLE_DISH', got {observation_type}")
            raise ValueError(f"Observation type must be 'VLBI' or 'SINGLE_DISH', got {observation_type}")
        if sources is not None:
            check_type(sources, Sources, "Sources")
        if telescopes is not None:
            check_type(telescopes, Telescopes, "Telescopes")
        if frequencies is not None:
            check_type(frequencies, Frequencies, "Frequencies")
        if scans is not None:
            check_type(scans, Scans, "Scans")
        self._observation_code = observation_code
        self._observation_type = observation_type
        self._sources = sources if sources is not None else Sources()
        self._telescopes = telescopes if telescopes is not None else Telescopes()
        self._frequencies = frequencies if frequencies is not None else Frequencies()
        self._scans = scans if scans is not None else Scans()
        self._calculated_data: Dict[str, Any] = {}  # Хранилище для результатов Calculator
        logger.info(f"Initialized Observation '{observation_code}' with type '{observation_type}'")

    def set_observation(self, observation_code: str, sources: Sources = None,
                        telescopes: Telescopes = None, frequencies: Frequencies = None,
                        scans: Scans = None, observation_type: str = "VLBI", isactive: bool = True) -> None:
        """Set observation parameters."""
        check_type(observation_code, str, "Observation code")
        if observation_type not in ("VLBI", "SINGLE_DISH"):
            logger.error(f"Observation type must be 'VLBI' or 'SINGLE_DISH', got {observation_type}")
            raise ValueError(f"Observation type must be 'VLBI' or 'SINGLE_DISH', got {observation_type}")
        if sources is not None:
            check_type(sources, Sources, "Sources")
        if telescopes is not None:
            check_type(telescopes, Telescopes, "Telescopes")
        if frequencies is not None:
            check_type(frequencies, Frequencies, "Frequencies")
        if scans is not None:
            check_type(scans, Scans, "Scans")
        self._observation_code = observation_code
        self._observation_type = observation_type
        self._sources = sources if sources is not None else Sources()
        self._telescopes = telescopes if telescopes is not None else Telescopes()
        self._frequencies = frequencies if frequencies is not None else Frequencies()
        self._scans = scans if scans is not None else Scans()
        self.isactive = isactive
        self._calculated_data.clear()  # Очищаем результаты при полной переустановке параметров
        logger.info(f"Set observation '{observation_code}' with type '{observation_type}'")

    def set_observation_code(self, observation_code: str) -> None:
        """Set observation code."""
        check_type(observation_code, str, "Observation code")
        self._observation_code = observation_code
        logger.info(f"Set observation code to '{observation_code}'")

    def set_sources(self, sources: Sources) -> None:
        """Set observation sources."""
        check_type(sources, Sources, "Sources")
        self._sources = sources
        self._calculated_data.clear()  # Очищаем результаты, так как данные изменились
        logger.info(f"Set sources for observation '{self._observation_code}'")

    def set_telescopes(self, telescopes: Telescopes) -> None:
        """Set observation telescopes."""
        check_type(telescopes, Telescopes, "Telescopes")
        self._telescopes = telescopes
        self._calculated_data.clear()  # Очищаем результаты, так как данные изменились
        logger.info(f"Set telescopes for observation '{self._observation_code}'")

    def set_frequencies(self, frequencies: Frequencies) -> None:
        """Set observation frequencies with polarizations."""
        check_type(frequencies, Frequencies, "Frequencies")
        self._frequencies = frequencies
        self._calculated_data.clear()  # Очищаем результаты, так как данные изменились
        logger.info(f"Set frequencies with polarizations for observation '{self._observation_code}'")

    def set_scans(self, scans: Scans) -> None:
        """Set observation scans."""
        check_type(scans, Scans, "Scans")
        self._scans = scans
        self._calculated_data.clear()  # Очищаем результаты, так как данные изменились
        logger.info(f"Set scans for observation '{self._observation_code}'")

    def set_calculated_data(self, key: str, data: Any) -> None:
        """Save calculated data for this observation."""
        check_non_empty_string(key, "Key")
        self._calculated_data[key] = data
        logger.info(f"Stored calculated data '{key}' for observation '{self._observation_code}'")

    def get_calculated_data(self, key: str) -> Any:
        """Retrieve calculated data by key."""
        check_non_empty_string(key, "Key")
        return self._calculated_data.get(key)

    def get_observation_code(self) -> str:
        """Get observation code."""
        return self._observation_code
    
    def get_observation_type(self) -> str:
        """Get observation type."""
        return self._observation_type

    def get_sources(self) -> Sources:
        """Get observation sources."""
        return self._sources

    def get_telescopes(self) -> Telescopes:
        """Get observation telescopes."""
        return self._telescopes

    def get_frequencies(self) -> Frequencies:
        """Get observation frequencies."""
        return self._frequencies

    def get_scans(self) -> Scans:
        """Get observation scans."""
        return self._scans

    def get_start_datetime(self) -> Optional[datetime]:
        """Get observation start time as a datetime object (UTC), based on earliest scan."""
        active_scans = self._scans.get_active_scans()
        if not active_scans:
            return None
        return min(scan.get_start_datetime() for scan in active_scans)

    def validate(self) -> bool:
        """Validate the observation parameters."""
        from utils.validation import check_type, check_positive_float, check_list_not_empty

        # Check observation code
        if not self._observation_code or not isinstance(self._observation_code, str):
            logger.error("Observation code must be a non-empty string")
            return False

        # Check observation type
        if self._observation_type not in ["VLBI", "SingleDish"]:
            logger.error(f"Invalid observation type: {self._observation_type}. Must be 'VLBI' or 'SingleDish'")
            return False

        # Validate SEFD
        check_positive_float(self._sefd, "SEFD")

        # Validate sources
        if not self._sources.get_active_sources():
            logger.error("No active sources defined in observation")
            return False
        for source in self._sources.get_active_sources():
            if not source.validate():
                logger.error(f"Source validation failed for {source.get_name()}")
                return False

        # Validate telescopes
        if not self._telescopes.get_active_telescopes():
            logger.error("No active telescopes defined in observation")
            return False
        for telescope in self._telescopes.get_active_telescopes():
            if not telescope.validate():
                logger.error(f"Telescope validation failed for {telescope.get_telescope_code()}")
                return False

        # Validate frequencies
        if not self._frequencies.get_active_frequencies():
            logger.error("No active frequencies defined in observation")
            return False
        for freq in self._frequencies.get_active_frequencies():
            if not freq.validate():
                logger.error(f"Frequency validation failed for {freq}")
                return False

        # Validate scans
        if not self._scans.get_active_scans():
            logger.error("No active scans defined in observation")
            return False
        for scan in self._scans.get_active_scans():
            if not scan.validate():
                logger.error(f"Scan validation failed for start time {scan.get_start()}")
                return False

        # Check temporal consistency of scans
        active_scans = sorted(self._scans.get_active_scans(), key=lambda x: x.get_start())
        telescope_scans = {}  # Словарь для отслеживания занятости телескопов
        for scan in active_scans:
            scan_start = scan.get_start()
            scan_end = scan_start + scan.get_duration()
            
            # Проверка доступности телескопов для скана
            if not scan.check_telescope_availability():
                logger.error(f"Telescope availability check failed for scan starting at {scan_start}")
                return False

            # Проверка пересечений по времени для телескопов
            for telescope in scan.get_telescopes().get_active_telescopes():
                tel_code = telescope.get_telescope_code()
                if tel_code not in telescope_scans:
                    telescope_scans[tel_code] = []
                for prev_start, prev_end in telescope_scans[tel_code]:
                    if not (scan_end <= prev_start or scan_start >= prev_end):
                        logger.error(f"Scan overlap detected for telescope {tel_code}: "
                                    f"[{prev_start}, {prev_end}] vs [{scan_start}, {scan_end}]")
                        return False
                telescope_scans[tel_code].append((scan_start, scan_end))

        logger.info(f"Observation '{self._observation_code}' validated successfully")
        return True

    def activate(self) -> None:
        """Activate observation."""
        super().activate()

    def deactivate(self) -> None:
        """Deactivate observation."""
        super().deactivate()

    def to_dict(self) -> dict:
        """Convert Observation object to a dictionary for serialization."""
        logger.info(f"Converted observation '{self._observation_code}' to dictionary")
        return {
            "observation_code": self._observation_code,
            "observation_type": self._observation_type,
            "sources": self._sources.to_dict(),
            "telescopes": self._telescopes.to_dict(),
            "frequencies": self._frequencies.to_dict(),
            "scans": self._scans.to_dict(),
            "isactive": self.isactive,
            "calculated_data": self._calculated_data  # Добавляем результаты вычислений
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Observation':
        """Create an Observation object from a dictionary."""
        obs = cls(
            observation_code=data["observation_code"],
            sources=Sources.from_dict(data["sources"]),
            telescopes=Telescopes.from_dict(data["telescopes"]),
            frequencies=Frequencies.from_dict(data["frequencies"]),
            scans=Scans.from_dict(data["scans"]),
            observation_type=data["observation_type"],
            isactive=data["isactive"]
        )
        obs._calculated_data = data.get("calculated_data", {})  # Загружаем результаты вычислений
        logger.info(f"Created observation '{data['observation_code']}' from dictionary")
        return obs

    def __repr__(self) -> str:
        """Return a string representation of Observation."""
        return (f"Observation(code='{self._observation_code}', sources={self._sources}, "
                f"telescopes={self._telescopes}, frequencies={self._frequencies}, "
                f"scans={self._scans}, isactive={self.isactive}, "
                f"calculated_data={len(self._calculated_data)} items)")

class CatalogManager:
    """Класс для управления каталогами источников и телескопов в текстовом формате."""
    
    def __init__(self, source_file: Optional[str] = None, telescope_file: Optional[str] = None):
        """Инициализация менеджера каталогов.
        
        Args:
            source_file (str, optional): Путь к файлу каталога источников.
            telescope_file (str, optional): Путь к файлу каталога телескопов.
        """
        if source_file is not None and not isinstance(source_file, str):
            logger.error("source_file must be a string or None")
            raise TypeError("source_file must be a string or None!")
        if telescope_file is not None and not isinstance(telescope_file, str):
            logger.error("telescope_file must be a string or None")
            raise TypeError("telescope_file must be a string or None!")
        self.source_catalog = Sources()
        self.telescope_catalog = Telescopes()
        
        if source_file:
            self.load_source_catalog(source_file)
        if telescope_file:
            self.load_telescope_catalog(telescope_file)

    # --- Методы для работы с каталогом источников ---

    def load_source_catalog(self, source_file: str) -> None:
        """Загрузка каталога источников из текстового файла.
        
        Формат: b1950_name j2000_name alt_name ra_hh:mm:ss.ssss dec_dd:mm:ss.ssss
        
        Args:
            source_file (str): Путь к файлу каталога источников.
        
        Raises:
            FileNotFoundError: Если файл не найден.
            ValueError: Если данные в файле некорректны.
        """
        sources = []
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    # Разделяем строку на части
                    parts = re.split(r'\s+', line)
                    if len(parts) < 5:
                        raise ValueError(f"Invalid source format in line: {line}")

                    b1950_name = parts[0]
                    j2000_name = parts[1] if parts[1] != "ALT_NAME" else None
                    alt_name = parts[2] if parts[2] != "ALT_NAME" else None
                    ra_str, dec_str = parts[-2], parts[-1]

                    # Парсим RA (hh:mm:ss.ssss)
                    ra_match = re.match(r'(\d{2}):(\d{2}):(\d{2}\.\d+)', ra_str)
                    if not ra_match:
                        raise ValueError(f"Invalid RA format: {ra_str}")
                    ra_h, ra_m, ra_s = map(float, ra_match.groups())

                    # Парсим DEC (±dd:mm:ss.ssss)
                    dec_match = re.match(r'([-+])?(\d{2}):(\d{2}):(\d{2}\.\d+)', dec_str)
                    if not dec_match:
                        raise ValueError(f"Invalid DEC format: {dec_str}")
                    sign, de_d, de_m, de_s = dec_match.groups()
                    de_d = float(de_d) if sign != '-' else -float(de_d)
                    de_m, de_s = float(de_m), float(de_s)

                    source = Source(
                        name=b1950_name,
                        ra_h=ra_h, ra_m=ra_m, ra_s=ra_s,
                        de_d=de_d, de_m=de_m, de_s=de_s,
                        name_J2000=j2000_name,
                        alt_name=alt_name
                    )
                    sources.append(source)
            self.source_catalog = Sources(sources)
            logger.info(f"Loaded {len(sources)} sources from '{source_file}'")
        except FileNotFoundError:
            raise FileNotFoundError(f"Source catalog file '{source_file}' not found!")
        except ValueError as e:
            raise ValueError(f"Error parsing source catalog: {e}")

    def get_source(self, name: str) -> Optional[Source]:
        """Получить источник по имени (B1950 или J2000)."""
        return next((s for s in self.source_catalog.get_all_sources() 
                     if s.name == name or (s.name_J2000 and s.name_J2000 == name)), None)

    def get_sources_by_ra_range(self, ra_min: float, ra_max: float) -> List[Source]:
        """Получить список источников в заданном диапазоне прямого восхождения (RA) в градусах."""
        return [s for s in self.source_catalog.get_all_sources() 
                if ra_min <= s.get_ra_degrees() <= ra_max]

    def get_sources_by_dec_range(self, dec_min: float, dec_max: float) -> List[Source]:
        """Получить список источников в заданном диапазоне склонения (DEC) в градусах."""
        return [s for s in self.source_catalog.get_all_sources() 
                if dec_min <= s.get_dec_degrees() <= dec_max]

    # --- Методы для работы с каталогом телескопов ---

    def load_telescope_catalog(self, telescope_file: str) -> None:
        """Загрузка каталога телескопов из текстового файла.
        
        Формат: number short_name full_name x y z
        
        Args:
            telescope_file (str): Путь к файлу каталога телескопов.
        
        Raises:
            FileNotFoundError: Если файл не найден.
            ValueError: Если данные в файле некорректны.
        """
        telescopes = []
        try:
            with open(telescope_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    # Разделяем строку на части
                    parts = re.split(r'\s+', line)
                    if len(parts) < 6:
                        raise ValueError(f"Invalid telescope format in line: {line}")

                    number, short_name, full_name = parts[0], parts[1], parts[2]
                    x, y, z = map(float, parts[3:6])
                    # Скорости не указаны в каталоге, задаем 0
                    vx, vy, vz = 0.0, 0.0, 0.0
                    diameter = float(parts[6])

                    telescope = Telescope(
                        code=short_name,
                        name=full_name,
                        x=x, y=y, z=z,
                        vx=vx, vy=vy, vz=vz,
                        diameter=diameter,
                        isactive=True
                    )
                    telescopes.append(telescope)
            self.telescope_catalog = Telescopes(telescopes)
            logger.info(f"Loaded {len(telescopes)} telescopes from '{telescope_file}'")
        except FileNotFoundError:
            raise FileNotFoundError(f"Telescope catalog file '{telescope_file}' not found!")
        except ValueError as e:
            raise ValueError(f"Error parsing telescope catalog: {e}")

    def get_telescope(self, code: str) -> Optional[Telescope]:
        """Получить телескоп по коду."""
        return next((t for t in self.telescope_catalog.get_all_telescopes() if t.code == code), None)

    def get_telescopes_by_type(self, telescope_type: str = "Telescope") -> List[Telescope]:
        """Получить список телескопов заданного типа."""
        return [t for t in self.telescope_catalog.get_all_telescopes() 
                if (telescope_type == "Telescope" and isinstance(t, Telescope))]

    # --- Общие методы ---

    def clear_catalogs(self) -> None:
        """Очистить оба каталога."""
        self.source_catalog.clear()
        self.telescope_catalog.clear()

    def __repr__(self) -> str:
        """Строковое представление CatalogManager."""
        return (f"CatalogManager(sources={len(self.source_catalog)}, "
                f"telescopes={len(self.telescope_catalog)})")