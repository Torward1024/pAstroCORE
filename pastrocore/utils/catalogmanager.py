# utils/catalogmanager.py
from pastrocore.base.sources import Source, Sources
from pastrocore.base.telescopes import Telescope, Telescopes

from common.utils.logging_setup import logger
from typing import Optional, List
import re

class CatalogManager:
    """Manages catalogs of astronomical sources and telescopes.

    Loads and stores source and telescope data from text files, providing methods to query and filter the catalogs.
    Supports B1950/J2000 source names, RA/DEC ranges, and telescope codes/types.

    Attributes:
        source_catalog (Sources): Collection of Source objects.
        telescope_catalog (Telescopes): Collection of Telescope objects.

    Notes:
        - Logging is integrated via `common.utils.logging_setup.logger`.
        - Source file format: `name j2000_name alt_name ra_hh:mm:ss.ssss dec_dd:mm:ss.ssss`.
        - Telescope file format: `number short_name full_name x y z diameter`.
        - Lines starting with '#' or empty lines are skipped during loading.

    Examples:
        >>> cm = CatalogManager(source_file="sources.txt", telescope_file="telescopes.txt")
        >>> source = cm.get_source("3C273")
        >>> telescopes = cm.get_telescopes_by_type("Telescope")
        >>> print(cm)
        CatalogManager(sources=<num>, telescopes=<num>)
    """
    def __init__(self, source_file: Optional[str] = None, telescope_file: Optional[str] = None):
        """Initialize the CatalogManager with optional source and telescope catalog files.

        Args:
            source_file (Optional[str]): Path to the sources catalog file. Defaults to None.
            telescope_file (Optional[str]): Path to the telescopes catalog file. Defaults to None.

        Raises:
            TypeError: If source_file or telescope_file is neither a string nor None.
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

    # sources catalog

    def load_source_catalog(self, source_file: str) -> None:
        """Load a sources catalog from a text file into the source_catalog attribute.

        Expected format: `name j2000_name alt_name ra_hh:mm:ss.ssss dec_dd:mm:ss.ssss`.

        Args:
            source_file (str): Path to the sources catalog file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If there is an error parsing the catalog data (e.g., invalid RA/DEC format).

        Notes:
            - Logs warnings for invalid lines and a summary of loaded/failed sources.
        """
        sources = {}
        failed_count = 0
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = re.split(r'\s+', line)
                    if len(parts) < 5:
                        logger.warning(f"Skipping invalid source format: {line}")
                        failed_count += 1
                        continue

                    b1950_name = parts[0]
                    j2000_name = parts[1] if parts[1] != "ALT_NAME" else None
                    alt_name = parts[2] if parts[2] != "ALT_NAME" else None
                    ra_str, dec_str = parts[-2], parts[-1]

                    try:
                        ra_match = re.match(r'(\d{2}):(\d{2}):(\d{2}\.\d+)', ra_str)
                        if not ra_match:
                            raise ValueError(f"Invalid RA format: {ra_str}")
                        ra_h, ra_m, ra_s = map(float, ra_match.groups())

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
                        self.source_catalog.add(source)
                    except ValueError as e:
                        logger.warning(f"Failed to parse source '{line}': {e}")
                        failed_count += 1
                        continue
            if failed_count > 0:
                logger.warning(f"Loaded {len(self.source_catalog)} sources from '{source_file}', {failed_count} failed")
            else:
                logger.debug(f"Successfully loaded {len(self.source_catalog)} sources from '{source_file}'")
        except FileNotFoundError:
            raise FileNotFoundError(f"Source catalog file '{source_file}' not found!")
        except ValueError as e:
            raise ValueError(f"Error parsing source catalog: {e}")

    def get_source(self, name: str) -> Optional[Source]:
        """Retrieve a source from the catalog by its B1950 or J2000 name.

        Args:
            name (str): The B1950 or J2000 name of the source.

        Returns:
            Optional[Source]: The matching Source object, or None if not found.
        """
        return next((s for s in self.source_catalog.get_all_sources() 
                     if s.name == name or (s.name_J2000 and s.name_J2000 == name)), None)

    def get_sources_by_ra_range(self, ra_min: float, ra_max: float) -> List[Source]:
        """Retrieve sources within a specified right ascension (RA) range in degrees.

        Args:
            ra_min (float): Minimum RA in degrees.
            ra_max (float): Maximum RA in degrees.

        Returns:
            List[Source]: List of Source objects within the RA range.
        """
        return [s for s in self.source_catalog.get_all_sources() 
                if ra_min <= s.get_ra_degrees() <= ra_max]

    def get_sources_by_dec_range(self, dec_min: float, dec_max: float) -> List[Source]:
        """Retrieve sources within a specified declination (DEC) range in degrees.

        Args:
            dec_min (float): Minimum DEC in degrees.
            dec_max (float): Maximum DEC in degrees.

        Returns:
            List[Source]: List of Source objects within the DEC range.
        """
        return [s for s in self.source_catalog.get_all_sources() 
                if dec_min <= s.get_dec_degrees() <= dec_max]

    def load_telescope_catalog(self, telescope_file: str) -> None:
        """Load a telescopes catalog from a text file into the telescope_catalog attribute.

        Expected format: `number short_name full_name x y z diameter`.

        Args:
            telescope_file (str): Path to the telescopes catalog file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If there is an error parsing the catalog data (e.g., invalid numeric values).

        Notes:
            - Logs warnings for invalid lines and a summary of loaded/failed telescopes.
            - Velocities (vx, vy, vz) are set to 0.0 as they are not provided in the catalog format.
        """
        telescopes = {}
        failed_count = 0
        try:
            with open(telescope_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = re.split(r'\s+', line)
                    if len(parts) < 6:
                        logger.warning(f"Skipping invalid telescope format: {line}")
                        failed_count += 1
                        continue

                    try:
                        number, short_name, full_name = parts[0], parts[1], parts[2]
                        x, y, z = map(float, parts[3:6])
                        diameter = float(parts[6])
                        vx, vy, vz = 0.0, 0.0, 0.0  # Скорости не указаны в каталоге

                        telescope = Telescope(
                            code=short_name,
                            name=full_name,
                            x=x, y=y, z=z,
                            vx=vx, vy=vy, vz=vz,
                            diameter=diameter,
                            isactive=True
                        )
                        self.telescope_catalog.add(telescope)
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse telescope '{line}': {e}")
                        failed_count += 1
                        continue
            if failed_count > 0:
                logger.warning(f"Loaded {len(self.telescope_catalog)} telescopes from '{telescope_file}', {failed_count} failed")
            else:
                logger.debug(f"Successfully loaded {len(self.telescope_catalog)} telescopes from '{telescope_file}'")
        except FileNotFoundError:
            raise FileNotFoundError(f"Telescope catalog file '{telescope_file}' not found!")
        except ValueError as e:
            raise ValueError(f"Error parsing telescope catalog: {e}")

    def get_telescope(self, code: str) -> Optional[Telescope]:
        """Retrieve a telescope from the catalog by its code.

        Args:
            code (str): The unique code of the telescope.

        Returns:
            Optional[Telescope]: The matching Telescope object, or None if not found.
        """
        return next((t for t in self.telescope_catalog.get_all_telescopes() if t.code == code), None)

    def get_telescopes_by_type(self, telescope_type: str = "Telescope") -> List[Telescope]:
        """Retrieve telescopes filtered by type.

        Args:
            telescope_type (str): The type of telescope to filter by (currently only "Telescope" is supported). Defaults to "Telescope".

        Returns:
            List[Telescope]: List of Telescope objects matching the specified type.
        """
        return [t for t in self.telescope_catalog.get_all_telescopes() 
                if (telescope_type == "Telescope" and isinstance(t, Telescope))]

    def clear_catalogs(self) -> None:
        """Clear both the source and telescope catalogs.

        Notes:
            - Resets source_catalog and telescope_catalog to empty collections.
        """
        self.source_catalog.clear()
        self.telescope_catalog.clear()

    def __repr__(self) -> str:
        """Return a string representation of the CatalogManager.

        Returns:
            str: A formatted string with the count of sources and telescopes.
        """
        return (f"CatalogManager(sources={len(self.source_catalog)}, "
                f"telescopes={len(self.telescope_catalog)})")
    
    def clear(self):
        """Clear all catalog data."""
        self._sources = None
        self._telescopes = None
        logger.debug("Cleared CatalogManager data")