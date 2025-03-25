# utils/catalogmanager.py
from base.sources import Source, Sources
from base.telescopes import Telescope, Telescopes

from utils.logging_setup import logger
from typing import Optional, List
import re

class CatalogManager:
    """Class to control catalogs"""
    
    def __init__(self, source_file: Optional[str] = None, telescope_file: Optional[str] = None):
        """Initialize catalog manager
        
        Args:
            source_file (str, optional): path to sources catalog file
            telescope_file (str, optional): path to telescopes catalog file
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
        """Load sources catalog from text file
        
        Format: name j2000_name alt_name ra_hh:mm:ss.ssss dec_dd:mm:ss.ssss
        
        Args:
            source_file (str): path to sources catalog file
        
        Raises:
            FileNotFoundError: file not found
            ValueError: incorrect data in the catalog
        """
        sources = []
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
                        sources.append(source)
                    except ValueError as e:
                        logger.warning(f"Failed to parse source '{line}': {e}")
                        failed_count += 1
                        continue
            self.source_catalog = Sources(sources)
            if failed_count > 0:
                logger.warning(f"Loaded {len(sources)} sources from '{source_file}', {failed_count} failed")
            else:
                logger.info(f"Successfully loaded {len(sources)} sources from '{source_file}'")
        except FileNotFoundError:
            raise FileNotFoundError(f"Source catalog file '{source_file}' not found!")
        except ValueError as e:
            raise ValueError(f"Error parsing source catalog: {e}")

    def get_source(self, name: str) -> Optional[Source]:
        """Get source from catalog by name (B1950 или J2000)"""
        return next((s for s in self.source_catalog.get_all_sources() 
                     if s.name == name or (s.name_J2000 and s.name_J2000 == name)), None)

    def get_sources_by_ra_range(self, ra_min: float, ra_max: float) -> List[Source]:
        """Get list of sources in the range of (RA) (degrees)"""
        return [s for s in self.source_catalog.get_all_sources() 
                if ra_min <= s.get_ra_degrees() <= ra_max]

    def get_sources_by_dec_range(self, dec_min: float, dec_max: float) -> List[Source]:
        """Get list of sources in the range of (DEC) (degrees)"""
        return [s for s in self.source_catalog.get_all_sources() 
                if dec_min <= s.get_dec_degrees() <= dec_max]

    def load_telescope_catalog(self, telescope_file: str) -> None:
        """Load telescope catalog from text file
        
        Format: number short_name full_name x y z diameter
        
        Args:
            telescope_file (str): path to telescopes catalog file
        
        Raises:
            FileNotFoundError: file not found
            ValueError: incorrect data in the catalog
        """
        telescopes = []
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
                        telescopes.append(telescope)
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse telescope '{line}': {e}")
                        failed_count += 1
                        continue
            self.telescope_catalog = Telescopes(telescopes)
            if failed_count > 0:
                logger.warning(f"Loaded {len(telescopes)} telescopes from '{telescope_file}', {failed_count} failed")
            else:
                logger.info(f"Successfully loaded {len(telescopes)} telescopes from '{telescope_file}'")
        except FileNotFoundError:
            raise FileNotFoundError(f"Telescope catalog file '{telescope_file}' not found!")
        except ValueError as e:
            raise ValueError(f"Error parsing telescope catalog: {e}")

    def get_telescope(self, code: str) -> Optional[Telescope]:
        """Get telescope by code"""
        return next((t for t in self.telescope_catalog.get_all_telescopes() if t.code == code), None)

    def get_telescopes_by_type(self, telescope_type: str = "Telescope") -> List[Telescope]:
        """Get telescopes by type"""
        return [t for t in self.telescope_catalog.get_all_telescopes() 
                if (telescope_type == "Telescope" and isinstance(t, Telescope))]

    def clear_catalogs(self) -> None:
        """Clear both catalogs"""
        self.source_catalog.clear()
        self.telescope_catalog.clear()

    def __repr__(self) -> str:
        """String representation of CatalogManager"""
        return (f"CatalogManager(sources={len(self.source_catalog)}, "
                f"telescopes={len(self.telescope_catalog)})")