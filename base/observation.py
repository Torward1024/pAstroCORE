# base/observation.py
from base.base_entity import BaseEntity
from base.sources import Source, Sources
from base.telescopes import Telescope, SpaceTelescope, Telescopes
from base.frequencies import Frequencies
from base.scans import Scans
from utils.validation import check_type, check_non_empty_string
from utils.logging_setup import logger
from datetime import datetime
import json
import re
from typing import Optional, List

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
        logger.info(f"Set sources for observation '{self._observation_code}'")

    def set_telescopes(self, telescopes: Telescopes) -> None:
        """Set observation telescopes."""
        check_type(telescopes, Telescopes, "Telescopes")
        self._telescopes = telescopes
        logger.info(f"Set telescopes for observation '{self._observation_code}'")

    def set_frequencies(self, frequencies: Frequencies) -> None:
        """Set observation frequencies with polarizations."""
        check_type(frequencies, Frequencies, "Frequencies")
        self._frequencies = frequencies
        logger.info(f"Set frequencies with polarizations for observation '{self._observation_code}'")

    def set_scans(self, scans: Scans) -> None:
        """Set observation scans."""
        check_type(scans, Scans, "Scans")
        self._scans = scans
        logger.info(f"Set scans for observation '{self._observation_code}'")

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
        """Validate the observation, including SEFD and polarizations."""
        active_scans = self._scans.get_active_scans()
        if not active_scans:
            logger.warning(f"Observation '{self._observation_code}' has no active scans")
            return False
        
        active_telescopes = self._telescopes.get_active_telescopes()
        if not active_telescopes:
            logger.warning(f"Observation '{self._observation_code}' has no active telescopes")
            return False
        if self._observation_type == "VLBI" and len(active_telescopes) < 2:
            logger.warning(f"VLBI observation '{self._observation_code}' requires at least 2 active telescopes, got {len(active_telescopes)}")
            return False
        elif self._observation_type == "SINGLE_DISH" and len(active_telescopes) != 1:
            logger.warning(f"SINGLE_DISH observation '{self._observation_code}' requires exactly 1 active telescope, got {len(active_telescopes)}")
            return False
        
        # Проверка источников
        active_sources = {s.get_name() for s in self._sources.get_active_sources()}
        for scan in active_scans:
            if not scan.is_off_source and scan.get_source().get_name() not in active_sources:
                logger.warning(f"Scan in '{self._observation_code}' uses source '{scan.get_source().get_name()}' not in observation sources")
                return False
            scan_telescopes = {t.get_telescope_code() for t in scan.get_telescopes().get_active_telescopes()}
            active_telescope_codes = {t.get_telescope_code() for t in active_telescopes}
            if not scan_telescopes.issubset(active_telescope_codes):
                logger.warning(f"Scan in '{self._observation_code}' uses telescopes not in observation telescopes")
                return False
        
        # Проверка SEFD
        obs_freqs = {f.get_frequency() for f in self._frequencies.get_active_frequencies()}
        for tel in active_telescopes:
            for freq in obs_freqs:
                if tel.get_sefd(freq) is None:
                    logger.warning(f"Telescope '{tel.get_telescope_code()}' has no SEFD for frequency {freq} MHz")
                    return False
        
        # Проверка синхронизации частот и поляризаций
        for scan in active_scans:
            scan_freqs = {f.get_frequency(): f.get_polarization() for f in scan.get_frequencies().get_active_frequencies()}
            for freq, pol in scan_freqs.items():
                if freq not in obs_freqs:
                    logger.warning(f"Scan in '{self._observation_code}' uses frequency {freq} MHz not in observation frequencies")
                    return False
                obs_pol = next((f.get_polarization() for f in self._frequencies.get_active_frequencies() if f.get_frequency() == freq), None)
                if pol != obs_pol:
                    logger.warning(f"Scan in '{self._observation_code}' uses polarization {pol} for {freq} MHz, observation has {obs_pol}")
                    return False
        
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
            "isactive": self.isactive
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Observation':
        """Create an Observation object from a dictionary."""
        logger.info(f"Created observation '{data['observation_code']}' from dictionary")
        return cls(
            observation_code=data["observation_code"],
            sources=Sources.from_dict(data["sources"]),
            telescopes=Telescopes.from_dict(data["telescopes"]),
            frequencies=Frequencies.from_dict(data["frequencies"]),
            scans=Scans.from_dict(data["scans"]),
            observation_type=data["observation_type"],
            isactive=data["isactive"]
        )

    def __repr__(self) -> str:
        """Return a string representation of Observation."""
        return (f"Observation(code='{self._observation_code}', sources={self._sources}, "
                f"telescopes={self._telescopes}, frequencies={self._frequencies}, "
                f"scans={self._scans}, isactive={self.isactive})")

class Project(BaseEntity):
    def __init__(self, project_name: str = "PROJECT_DEFAULT", observations: list[Observation] = None):
        """Initialize a Project object.

        Args:
            project_name (str): Project name.
            observations (list[Observation], optional): List of observations.
        """
        super().__init__()
        check_type(project_name, str, "Project name")
        if observations is not None:
            check_type(observations, (list, tuple), "Observations")
            for obs in observations:
                check_type(obs, Observation, "Observation")
        self._project_name = project_name
        self._observations = observations if observations is not None else []
        logger.info(f"Initialized Project '{project_name}' with {len(self._observations)} observations")

    def set_project_name(self, project_name: str) -> None:
        """Set project name."""
        check_type(project_name, str, "Project name")
        self._project_name = project_name
        logger.info(f"Set project name to '{project_name}'")

    def get_project_name(self) -> str:
        """Get project name."""
        return self._project_name

    def get_observations(self) -> list[Observation]:
        """Get all observations."""
        return self._observations

    def get_observation(self, obs_code: str) -> Observation:
        """Get observation by code."""
        for obs in self._observations:
            if obs.get_observation_code() == obs_code:
                return obs
        logger.error(f"No observation found with code '{obs_code}'")
        raise ValueError(f"No observation found with code '{obs_code}'")

    def save_project(self, filename: str) -> None:
        """Save project to a JSON file."""
        check_type(filename, str, "Filename")
        try:
            project_dict = {
                "project_name": self._project_name,
                "observations": [obs.to_dict() for obs in self._observations]
            }
            with open(filename, 'w') as f:
                json.dump(project_dict, f, indent=4)
            logger.info(f"Saved project '{self._project_name}' to '{filename}'")
        except TypeError as e:
            logger.error(f"Serialization error while saving project '{self._project_name}': {str(e)}")
            raise TypeError(f"Failed to serialize project: {str(e)}")
        except IOError as e:
            logger.error(f"IO error while saving project '{self._project_name}' to '{filename}': {str(e)}")
            raise IOError(f"Failed to save project to '{filename}': {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error while saving project '{self._project_name}': {str(e)}")
            raise Exception(f"Unexpected error: {str(e)}")

    def load_project(self, filename: str) -> None:
        """Load project from a JSON file."""
        check_type(filename, str, "Filename")
        try:
            with open(filename, 'r') as f:
                project_dict = json.load(f)
            self._project_name = project_dict["project_name"]
            self._observations = [Observation.from_dict(obs_dict) for obs_dict in project_dict["observations"]]
            logger.info(f"Loaded project '{self._project_name}' from '{filename}' with {len(self._observations)} observations")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error while loading project from '{filename}': {str(e)}")
            raise ValueError(f"Invalid JSON format in '{filename}': {str(e)}")
        except IOError as e:
            logger.error(f"IO error while loading project from '{filename}': {str(e)}")
            raise IOError(f"Failed to load project from '{filename}': {str(e)}")
        except KeyError as e:
            logger.error(f"Missing key in project data from '{filename}': {str(e)}")
            raise ValueError(f"Invalid project data in '{filename}': missing {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error while loading project from '{filename}': {str(e)}")
            raise Exception(f"Unexpected error: {str(e)}")

    def to_dict(self) -> dict:
        """Convert Project object to a dictionary for serialization."""
        logger.info(f"Converted project '{self._project_name}' to dictionary")
        return {
            "project_name": self._project_name,
            "observations": [obs.to_dict() for obs in self._observations]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Project':
        """Create a Project object from a dictionary."""
        logger.info(f"Created project '{data['project_name']}' from dictionary")
        return cls(
            project_name=data["project_name"],
            observations=[Observation.from_dict(obs_data) for obs_data in data["observations"]]
        )

    def __len__(self) -> int:
        """Return the number of observations."""
        return len(self._observations)

    def __repr__(self) -> str:
        """Return a string representation of Project."""
        return f"Project(name='{self._project_name}', observations={len(self._observations)})"

class CatalogManager:
    """Класс для управления каталогами источников и телескопов в текстовом формате."""

    def __init__(self, source_file: Optional[str] = None, telescope_file: Optional[str] = None):
        """Инициализация менеджера каталогов.

        Args:
            source_file (str, optional): Путь к файлу каталога источников.
            telescope_file (str, optional): Путь к файлу каталога телескопов.
        """
        check_type(source_file, str, "source_file", allow_none=True)
        check_type(telescope_file, str, "telescope_file", allow_none=True)
        self.source_catalog = Sources()
        self.telescope_catalog = Telescopes()

        if source_file:
            self.load_source_catalog(source_file)
        if telescope_file:
            self.load_telescope_catalog(telescope_file)
        logger.info("Initialized CatalogManager")

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
        check_non_empty_string(source_file, "source_file")
        sources = []
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = re.split(r'\s+', line)
                    if len(parts) < 5:
                        logger.error(f"Invalid source format in line: {line}")
                        raise ValueError(f"Invalid source format in line: {line}")

                    b1950_name = parts[0]
                    j2000_name = parts[1] if parts[1] != "ALT_NAME" else None
                    alt_name = parts[2] if parts[2] != "ALT_NAME" else None
                    ra_str, dec_str = parts[-2], parts[-1]

                    # Парсим RA (hh:mm:ss.ssss)
                    ra_match = re.match(r'(\d{2}):(\d{2}):(\d{2}\.\d+)', ra_str)
                    if not ra_match:
                        logger.error(f"Invalid RA format: {ra_str}")
                        raise ValueError(f"Invalid RA format: {ra_str}")
                    ra_h, ra_m, ra_s = map(float, ra_match.groups())

                    # Парсим DEC (±dd:mm:ss.ssss)
                    dec_match = re.match(r'([-+])?(\d{2}):(\d{2}):(\d{2}\.\d+)', dec_str)
                    if not dec_match:
                        logger.error(f"Invalid DEC format: {dec_str}")
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
            self.source_catalog.clear()  # Очищаем перед загрузкой нового каталога
            for source in sources:
                self.source_catalog.add_source(source)  # Используем метод add_source с проверкой дубликатов
            logger.info(f"Loaded {len(sources)} sources from '{source_file}'")
        except FileNotFoundError:
            logger.error(f"Source catalog file '{source_file}' not found")
            raise FileNotFoundError(f"Source catalog file '{source_file}' not found")
        except ValueError as e:
            logger.error(f"Error parsing source catalog: {str(e)}")
            raise ValueError(f"Error parsing source catalog: {e}")

    def get_source(self, name: str) -> Optional[Source]:
        """Получить источник по имени (B1950, J2000 или альтернативное имя)."""
        check_non_empty_string(name, "name")
        for source in self.source_catalog.get_all_sources():
            if (source.get_name() == name or 
                (source.get_name_J2000() and source.get_name_J2000() == name) or 
                (source.get_alt_name() and source.get_alt_name() == name)):
                return source
        return None

    def get_sources_by_ra_range(self, ra_min: float, ra_max: float) -> List[Source]:
        """Получить список источников в заданном диапазоне прямого восхождения (RA) в градусах."""
        check_type(ra_min, (int, float), "ra_min")
        check_type(ra_max, (int, float), "ra_max")
        return [s for s in self.source_catalog.get_all_sources() 
                if ra_min <= s.get_ra_degrees() <= ra_max]

    def get_sources_by_dec_range(self, dec_min: float, dec_max: float) -> List[Source]:
        """Получить список источников в заданном диапазоне склонения (DEC) в градусах."""
        check_type(dec_min, (int, float), "dec_min")
        check_type(dec_max, (int, float), "dec_max")
        return [s for s in self.source_catalog.get_all_sources() 
                if dec_min <= s.get_dec_degrees() <= dec_max]

    # --- Методы для работы с каталогом телескопов ---

    def load_telescope_catalog(self, telescope_file: str) -> None:
        """Загрузка каталога телескопов из текстового файла.

        Формат: number short_name full_name x y z [vx vy vz] [orbit_file]

        Args:
            telescope_file (str): Путь к файлу каталога телескопов.

        Raises:
            FileNotFoundError: Если файл не найден.
            ValueError: Если данные в файле некорректны.
        """
        check_non_empty_string(telescope_file, "telescope_file")
        telescopes = []
        try:
            with open(telescope_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = re.split(r'\s+', line)
                    if len(parts) < 6:
                        logger.error(f"Invalid telescope format in line: {line}")
                        raise ValueError(f"Invalid telescope format in line: {line}")

                    number, short_name, full_name = parts[0], parts[1], parts[2]
                    x, y, z = map(float, parts[3:6])
                    vx, vy, vz = 0.0, 0.0, 0.0
                    orbit_file = None

                    # Проверяем, есть ли дополнительные параметры (скорости или орбитальный файл)
                    if len(parts) >= 9:
                        try:
                            vx, vy, vz = map(float, parts[6:9])
                        except ValueError:
                            # Если не удалось распарсить скорости, считаем это орбитальным файлом
                            orbit_file = parts[6]

                    if orbit_file:
                        telescope = SpaceTelescope(
                            code=short_name,
                            name=full_name,
                            orbit_file=orbit_file,
                            isactive=True
                        )
                    else:
                        telescope = Telescope(
                            code=short_name,
                            name=full_name,
                            x=x, y=y, z=z,
                            vx=vx, vy=vy, vz=vz,
                            isactive=True
                        )
                    telescopes.append(telescope)
            self.telescope_catalog.clear()  # Очищаем перед загрузкой нового каталога
            for telescope in telescopes:
                self.telescope_catalog.add_telescope(telescope)  # Используем метод add_telescope с проверкой дубликатов
            logger.info(f"Loaded {len(telescopes)} telescopes from '{telescope_file}'")
        except FileNotFoundError:
            logger.error(f"Telescope catalog file '{telescope_file}' not found")
            raise FileNotFoundError(f"Telescope catalog file '{telescope_file}' not found")
        except ValueError as e:
            logger.error(f"Error parsing telescope catalog: {str(e)}")
            raise ValueError(f"Error parsing telescope catalog: {e}")

    def get_telescope(self, code: str) -> Optional[Telescope | SpaceTelescope]:
        """Получить телескоп по коду."""
        check_non_empty_string(code, "code")
        for telescope in self.telescope_catalog.get_all_telescopes():
            if telescope.get_telescope_code() == code:
                return telescope
        return None

    def get_telescopes_by_type(self, telescope_type: str = "Telescope") -> List[Telescope | SpaceTelescope]:
        """Получить список телескопов заданного типа."""
        check_non_empty_string(telescope_type, "telescope_type")
        if telescope_type == "Telescope":
            return [t for t in self.telescope_catalog.get_all_telescopes() if isinstance(t, Telescope) and not isinstance(t, SpaceTelescope)]
        elif telescope_type == "SpaceTelescope":
            return [t for t in self.telescope_catalog.get_all_telescopes() if isinstance(t, SpaceTelescope)]
        else:
            logger.error(f"Unknown telescope type: {telescope_type}")
            raise ValueError(f"Unknown telescope type: {telescope_type}")

    # --- Общие методы ---

    def clear_catalogs(self) -> None:
        """Очистить оба каталога."""
        self.source_catalog.clear()
        self.telescope_catalog.clear()
        logger.info("Cleared both source and telescope catalogs")

    def __repr__(self) -> str:
        """Строковое представление CatalogManager."""
        return (f"CatalogManager(sources={len(self.source_catalog)}, "
                f"telescopes={len(self.telescope_catalog)})")