# utils/catalogmanager.py
from pastrocore.base.sources import Source, Sources
from pastrocore.base.telescopes import SpaceTelescope, Telescope, Telescopes

from msb_arch.utils.logging_setup import logger
from pathlib import Path
from typing import Any, Dict, Optional, List
import json
import re

#: What a name column holds when there is no name. `$` is what the shipped files use;
#: `ALT_NAME` is what this reader used to look for, and never found in them.
NO_NAME = {"$", "ALT_NAME"}

#: A source line: the names, then right ascension and declination, which never hold a space.
SOURCE_LINE = re.compile(r"^(?P<names>.*?)\s+(?P<ra>\S+)\s+(?P<dec>\S+)\s*$")


class CatalogManager:
    """Manages catalogs of astronomical sources and telescopes.

    Reads them from files, keeps where each came from and whether it has changed since, and
    writes them back. Supports B1950/J2000 source names, RA/DEC ranges, and telescope codes/types.

    Attributes:
        source_catalog (Sources): Collection of Source objects.
        telescope_catalog (Telescopes): Collection of Telescope objects.

    Notes:
        - Logging is integrated via `msb_arch.utils.logging_setup.logger`.
        - **A catalogue is JSON** (C1): the same `Sources` and `Telescopes` a project writes, so a
          space telescope, an SEFD table and any field added later have somewhere to go.
        - A `.dat` catalogue still opens, and is saved as JSON. Source file format:
          `name j2000_name alt_name ra_hh:mm:ss.ssss dec_dd:mm:ss.ssss`, the names separated by
          tabs; telescope file format: `number short_name full_name x y z diameter`.
        - Lines starting with '#' or empty lines are skipped when reading a `.dat`.

    Examples:
        >>> cm = CatalogManager(source_file="sources.json", telescope_file="telescopes.json")
        >>> source = cm.get_source("3C273")
        >>> telescopes = cm.get_telescopes_by_type("Telescope")
        >>> print(cm)
        CatalogManager(sources=<num>, telescopes=<num>)
    """

    #: Each catalogue this keeps: the attribute holding it and the container it is.
    KINDS = {"sources": ("source_catalog", Sources),
             "telescopes": ("telescope_catalog", Telescopes)}

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
        self.source_catalog = Sources(name="sources")
        self.telescope_catalog = Telescopes(name="telescopes")
        #: The file each catalogue was read from or last saved to, and whether that file is JSON.
        self._paths: Dict[str, Optional[str]] = {kind: None for kind in self.KINDS}
        self._json: Dict[str, bool] = {kind: False for kind in self.KINDS}
        #: What each catalogue held when it was last read or saved, to tell whether it changed.
        self._saved: Dict[str, str] = {kind: self.catalog(kind).fingerprint()
                                       for kind in self.KINDS}

        if source_file:
            self.load_source_catalog(source_file)
        if telescope_file:
            self.load_telescope_catalog(telescope_file)

    # the catalogues as files

    def catalog(self, kind: str) -> Any:
        """Return the catalogue of a kind.

        Args:
            kind (str): `sources` or `telescopes`.

        Raises:
            KeyError: For any other kind, naming the ones there are.
        """
        if kind not in self.KINDS:
            raise KeyError(f"No catalogue of '{kind}'; there are {', '.join(self.KINDS)}")
        return getattr(self, self.KINDS[kind][0])

    def path(self, kind: str) -> Optional[str]:
        """Return the file a catalogue was read from or last saved to, if any."""
        self.catalog(kind)
        return self._paths[kind]

    def load(self, kind: str, path: str) -> None:
        """Read a catalogue from a file, replacing what is held.

        Args:
            kind (str): `sources` or `telescopes`.
            path (str): A JSON catalogue, or a `.dat` one.

        Raises:
            FileNotFoundError: If there is no such file.
            ValueError: If the file cannot be read as a catalogue of that kind.

        Notes:
            - **JSON or not is decided by what the file holds**, not by what it is called: a
              catalogue kept as `.txt` is still one or the other.
            - A JSON file of the other kind is refused by name. Read field for field it would come
              back as an empty catalogue or an error about a missing coordinate.
        """
        attribute, container = self.KINDS[kind]
        text = self._read(path)
        if text.lstrip().startswith("{"):
            catalogue = self._from_json(kind, path, text)
            self._json[kind] = True
        else:
            reader = self._sources_from_dat if kind == "sources" else self._telescopes_from_dat
            catalogue = reader(path, text)
            self._json[kind] = False
        setattr(self, attribute, catalogue)
        self._paths[kind] = str(path)
        self._saved[kind] = catalogue.fingerprint()

    def is_modified(self, kind: str) -> bool:
        """Report whether a catalogue holds something its file does not.

        Notes:
            - By content, not by counting writes: an item edited and edited back is not a change,
              and an item written to in place is one, which a container's own revision misses.
        """
        return self.catalog(kind).fingerprint() != self._saved[kind]

    def save(self, kind: str, path: str, manipulator: Any) -> str:
        """Write a catalogue to a file, as JSON, and remember that it is saved there.

        Args:
            kind (str): `sources` or `telescopes`.
            path (str): Where to write.
            manipulator (Manipulator): The orchestrator the write is asked of. MSB's `save`
                writes atomically -- a file beside the target, then a rename -- and the journal
                records it with the edits that came before.

        Returns:
            str: The path written.
        """
        catalogue = self.catalog(kind)
        manipulator.save(catalogue, path=str(path))
        self._paths[kind] = str(path)
        self._json[kind] = True
        self._saved[kind] = catalogue.fingerprint()
        logger.info("Saved the %s catalogue, %s entries, to '%s'", kind, len(catalogue), path)
        return str(path)

    def revert(self, kind: str) -> None:
        """Put a catalogue back to what its file holds, or to empty if it has no file."""
        path = self.path(kind)
        if path and Path(path).is_file():
            self.load(kind, path)
            return
        attribute, container = self.KINDS[kind]
        setattr(self, attribute, container(name=kind))
        self._saved[kind] = self.catalog(kind).fingerprint()

    def save_path(self, kind: str) -> Optional[str]:
        """Return where Save writes a catalogue without asking, or None if it has to ask.

        Returns:
            Optional[str]: The file it came from, when that is the user's own JSON. None for a
                catalogue with no file, one shipped with the application -- an upgrade replaces
                those and an install may not be writable -- and a `.dat`, which is saved as JSON
                and so under another name.
        """
        from pastrocore.paths import is_shipped

        path = self.path(kind)
        if not path or not self._json[kind] or is_shipped(path):
            return None
        return path

    def suggested_path(self, kind: str) -> str:
        """Return where Save As starts: a name for the catalogue, in the right folder.

        Returns:
            str: Beside a `.dat` it was read from, with a `.json` name; in the user's catalogue
                folder for a shipped catalogue or one with no file; its own file otherwise.
        """
        from pastrocore.paths import is_shipped, user_catalogs

        path = self.path(kind)
        if not path:
            return str(user_catalogs() / f"{kind}.json")
        if is_shipped(path):
            return str(user_catalogs() / f"{Path(path).stem}.json")
        return str(Path(path).with_suffix(".json"))

    @staticmethod
    def _read(path: str) -> str:
        try:
            return Path(path).read_text(encoding="utf-8")
        except FileNotFoundError:
            raise FileNotFoundError(f"Catalog file '{path}' not found!")

    def _from_json(self, kind: str, path: str, text: str) -> Any:
        container = self.KINDS[kind][1]
        try:
            data = json.loads(text)
        except ValueError as e:
            raise ValueError(f"'{path}' is not valid JSON: {e}")
        written = data.get("type") if isinstance(data, dict) else None
        if written != container.__name__:
            raise ValueError(f"'{path}' holds {written or 'something else'}, "
                             f"not a {kind} catalogue")
        catalogue = container.from_dict(data)
        logger.debug("Read %s %s from '%s'", len(catalogue), kind, path)
        return catalogue

    # sources catalog

    def load_source_catalog(self, source_file: str) -> None:
        """Load a sources catalog from a JSON or `.dat` file into the source_catalog attribute.

        Args:
            source_file (str): Path to the sources catalog file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If there is an error parsing the catalog data.
        """
        self.load("sources", source_file)

    def _sources_from_dat(self, source_file: str, text: str) -> Sources:
        """Read the text format: `name j2000_name alt_name ra dec`, one source a line.

        Notes:
            - **The names are separated by tabs** where the line has any, because a name may hold
              a space: split on every space, `Mrk 1419` became a source called `Mrk` with the
              J2000 name `1419`. A line with no tab is split on spaces, as before.
            - `$` in a name column is no name. It was read as one, so 138 of the shipped sources
              had an alternative name of `$`.
            - Right ascension and declination are the last two fields whichever way the line is
              separated, and neither holds a space.
        """
        catalogue = Sources(name=Path(source_file).stem)
        failed_count = 0
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            match = SOURCE_LINE.match(line)
            names = []
            if match:
                held = match.group("names")
                names = [name.strip() for name in (held.split("\t") if "\t" in held
                                                   else held.split())]
                names = [name for name in names if name]
            if len(names) < 3:
                logger.warning("Skipping invalid source format: %s", line)
                failed_count += 1
                continue

            b1950_name = names[0]
            j2000_name = names[1] if names[1] not in NO_NAME else None
            alt_name = names[2] if names[2] not in NO_NAME else None
            ra_str, dec_str = match.group("ra"), match.group("dec")

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

                catalogue.add(Source(
                    name=b1950_name,
                    ra_h=ra_h, ra_m=ra_m, ra_s=ra_s,
                    de_d=de_d, de_m=de_m, de_s=de_s,
                    name_J2000=j2000_name,
                    alt_name=alt_name
                ))
            except ValueError as e:
                logger.warning("Failed to parse source '%s': %s", line, e)
                failed_count += 1
                continue
        if failed_count > 0:
            logger.warning("Loaded %s sources from '%s', %s failed", len(catalogue), source_file, failed_count)
        else:
            logger.debug("Successfully loaded %s sources from '%s'", len(catalogue), source_file)
        return catalogue

    def get_source(self, name: str) -> Optional[Source]:
        """Retrieve a source from the catalog by its B1950 or J2000 name.

        Args:
            name (str): The B1950 or J2000 name of the source.

        Returns:
            Optional[Source]: The matching Source object, or None if not found.
        """
        return next((s for s in self.source_catalog.get_items()
                     if s.name == name or (s.name_J2000 and s.name_J2000 == name)), None)

    def get_sources_by_ra_range(self, ra_min: float, ra_max: float) -> List[Source]:
        """Retrieve sources within a specified right ascension (RA) range in degrees.

        Args:
            ra_min (float): Minimum RA in degrees.
            ra_max (float): Maximum RA in degrees.

        Returns:
            List[Source]: List of Source objects within the RA range.
        """
        return [s for s in self.source_catalog.get_items()
                if ra_min <= s.ra_degrees <= ra_max]

    def get_sources_by_dec_range(self, dec_min: float, dec_max: float) -> List[Source]:
        """Retrieve sources within a specified declination (DEC) range in degrees.

        Args:
            dec_min (float): Minimum DEC in degrees.
            dec_max (float): Maximum DEC in degrees.

        Returns:
            List[Source]: List of Source objects within the DEC range.
        """
        return [s for s in self.source_catalog.get_items()
                if dec_min <= s.dec_degrees <= dec_max]

    def load_telescope_catalog(self, telescope_file: str) -> None:
        """Load a telescopes catalog from a JSON or `.dat` file into the telescope_catalog attribute.

        Args:
            telescope_file (str): Path to the telescopes catalog file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If there is an error parsing the catalog data.
        """
        self.load("telescopes", telescope_file)

    def _telescopes_from_dat(self, telescope_file: str, text: str) -> Telescopes:
        """Read the text format: `number short_name full_name x y z diameter`, one a line.

        Notes:
            - Logs warnings for invalid lines and a summary of loaded/failed telescopes.
            - Velocities (vx, vy, vz) are set to 0.0 as they are not provided in the catalog format.
            - The columns after the diameter are not read. A JSON catalogue holds everything a
              telescope has, so that is where a pointing limit or an SEFD table is kept.
        """
        catalogue = Telescopes(name=Path(telescope_file).stem)
        failed_count = 0
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = re.split(r'\s+', line)
            # Seven, not six: the diameter is `parts[6]`, so a line of exactly six
            # fields passed this guard and then failed on the read below -- reported
            # as a line that could not be parsed rather than one that is too short.
            if len(parts) < 7:
                logger.warning("Skipping invalid telescope format: %s", line)
                failed_count += 1
                continue

            try:
                number, short_name, full_name = parts[0], parts[1], parts[2]
                x, y, z = map(float, parts[3:6])
                diameter = float(parts[6])
                vx, vy, vz = 0.0, 0.0, 0.0  # Скорости не указаны в каталоге

                catalogue.add(Telescope(
                    code=short_name,
                    name=full_name,
                    x=x, y=y, z=z,
                    vx=vx, vy=vy, vz=vz,
                    diameter=diameter,
                    isactive=True
                ))
            except (ValueError, IndexError) as e:
                logger.warning("Failed to parse telescope '%s': %s", line, e)
                failed_count += 1
                continue
        if failed_count > 0:
            logger.warning("Loaded %s telescopes from '%s', %s failed", len(catalogue), telescope_file, failed_count)
        else:
            logger.debug("Successfully loaded %s telescopes from '%s'", len(catalogue), telescope_file)
        return catalogue

    def get_telescope(self, code: str) -> Optional[Telescope]:
        """Retrieve a telescope from the catalog by its code.

        Args:
            code (str): The unique code of the telescope.

        Returns:
            Optional[Telescope]: The matching Telescope object, or None if not found.
        """
        return next((t for t in self.telescope_catalog.get_items() if t.code == code), None)

    def get_telescopes_by_type(self, telescope_type: str = "Telescope") -> List[Telescope]:
        """Retrieve telescopes filtered by type.

        Args:
            telescope_type (str): The type of telescope to filter by (currently only "Telescope" is supported). Defaults to "Telescope".

        Returns:
            List[Telescope]: List of Telescope objects matching the specified type.
        """
        # `SpaceTelescope` is a `Telescope`, so asking by class alone cannot tell them apart:
        # this read `telescope_type == "Telescope" and isinstance(t, Telescope)`, which returned
        # every telescope including the spacecraft for one spelling and an empty list for every
        # other -- so the one type the caller would actually want to single out was the one it
        # could never return.
        wanted = {"Telescope": lambda t: not isinstance(t, SpaceTelescope),
                  "SpaceTelescope": lambda t: isinstance(t, SpaceTelescope)}.get(telescope_type)
        if wanted is None:
            logger.warning("No telescope type called '%s'; there is Telescope and SpaceTelescope",
                           telescope_type)
            return []
        return [t for t in self.telescope_catalog.get_items() if wanted(t)]

    def clear_source_catalog(self) -> None:
        """Empty the source catalogue, keeping the telescopes.

        Notes:
            - One catalogue is reloaded on its own when its path changes in Preferences, and
              the window emptied it by reaching into `source_catalog` to do so.
        """
        self.source_catalog.remove_all()

    def clear_telescope_catalog(self) -> None:
        """Empty the telescope catalogue, keeping the sources."""
        self.telescope_catalog.remove_all()

    def clear_catalogs(self) -> None:
        """Empty both catalogues."""
        self.clear_source_catalog()
        self.clear_telescope_catalog()

    def __repr__(self) -> str:
        """Return a string representation of the CatalogManager.

        Returns:
            str: A formatted string with the count of sources and telescopes.
        """
        return (f"CatalogManager(sources={len(self.source_catalog)}, "
                f"telescopes={len(self.telescope_catalog)})")

    # `clear()` was here and did nothing: it set `_sources` and `_telescopes`, while the
    # catalogues are held in `source_catalog` and `telescope_catalog` -- so it created two
    # attributes nobody reads and left both catalogues full. Nothing called it. `clear_catalogs`
    # is the method that does the job, and `clear` is the name msb_arch 2.0.0 removed anyway.
