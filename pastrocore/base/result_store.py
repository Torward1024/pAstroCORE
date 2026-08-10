"""Where calculated results live when they are not in memory.

A project used to be one JSON file with every result base64-encoded inside it, which meant
opening anything required reading everything. Measured on a real session -- 300 sources, a year
of daily observations, 12 telescopes -- that is 173 million rows of `uv_coverage` alone, 8.3 GB
resident before any other result exists.

So a project is a directory now:

    project.pastro/
        project.json                            the model, and nothing else
        results/
            <observation>/uv_coverage.parquet
            <observation>/source_visibility.parquet

Parquet rather than a zip or a database, for one reason that outweighs the tidiness of a single
file: `polars.scan_parquet` can push a filter into the read. Drawing one source of three hundred
touches 1 584 rows instead of 475 200, measured, and 2.6 times faster than reading everything
and filtering afterwards. Inside a container that property is lost, because the member has to be
unpacked first.

`CalculatedData` is what the rest of the application sees. It behaves like the dictionary it
replaces -- `results["uv_coverage"]`, `.get`, `.items`, `in`, `len` -- and reads from disk only
when a key is actually asked for.
"""
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import polars as pl
from msb_arch.utils.logging_setup import logger

__all__ = ["CalculatedData", "ResultStore"]

METADATA_SUFFIX = ".meta.json"


class ResultStore:
    """Reads and writes one parquet file per calculated result.

    Args:
        root (Path): The `results/` directory inside a project directory.

    Notes:
        - Nothing is written until `write` is called, and nothing is read until a key is asked
          for. A store pointed at a directory that does not exist yet is legal: it is created
          on the first write.
    """

    def __init__(self, root: Path):
        self.root = Path(root)

    def _paths(self, owner: str, key: str) -> tuple:
        """Return the parquet and metadata paths for one result."""
        directory = self.root / owner
        return directory / f"{key}.parquet", directory / f"{key}{METADATA_SUFFIX}"

    def metadata(self, owner: str, key: str) -> Optional[Dict[str, Any]]:
        """Return one result's metadata without reading the result.

        Args:
            owner (str): The observation the result belongs to.
            key (str): The calculation that produced it.

        Returns:
            Optional[Dict[str, Any]]: What was recorded about how the result was produced, or
                None if there is no such result.

        Notes:
            - Metadata lives in its own file beside the parquet precisely so this is cheap.
              Reaching it through the result itself pulls every row off disk to reach a
              dictionary of a few entries.
        """
        _, metadata_path = self._paths(owner, key)
        if not metadata_path.is_file():
            return None
        return json.loads(metadata_path.read_text(encoding="utf-8"))

    def rename_owner(self, old: str, new: str) -> None:
        """Move an owner's results to a new name, so a rename does not strand them.

        Args:
            old (str): The name the results are filed under.
            new (str): The name to file them under instead.

        Notes:
            - Results already written under the new name win, because they were produced by
              the object as it is now. The old directory is removed rather than merged.
        """
        source, target = self.root / old, self.root / new
        if not source.is_dir():
            return
        if target.exists():
            shutil.rmtree(source)
            logger.warning("Results already exist under '%s'; dropped those left under '%s'", new, old)
            return
        source.rename(target)
        logger.info("Moved results from '%s' to '%s'", old, new)

    def keys(self, owner: str) -> List[str]:
        """Return the result keys stored for an owner, without reading any of them."""
        directory = self.root / owner
        if not directory.is_dir():
            return []
        return sorted(path.stem for path in directory.glob("*.parquet"))

    def has(self, owner: str, key: str) -> bool:
        """Report whether a result is on disk, without reading it."""
        return self._paths(owner, key)[0].is_file()

    def read(self, owner: str, key: str) -> Dict[str, Any]:
        """Read one result and its metadata.

        Args:
            owner (str): The observation the result belongs to.
            key (str): Which calculation.

        Returns:
            Dict[str, Any]: `{"data": DataFrame, "metadata": dict}`.

        Raises:
            KeyError: If nothing is stored under that key.
        """
        data_path, meta_path = self._paths(owner, key)
        if not data_path.is_file():
            raise KeyError(f"no stored result '{key}' for '{owner}'")
        frame = pl.read_parquet(data_path)
        metadata = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
        logger.debug("Read result '%s' for '%s': %s rows", key, owner, frame.height)
        return {"data": frame, "metadata": metadata}

    def scan(self, owner: str, key: str) -> pl.LazyFrame:
        """Return a lazy view of a result, so a filter can be pushed into the read.

        Args:
            owner (str): The observation the result belongs to.
            key (str): Which calculation.

        Returns:
            pl.LazyFrame: Nothing is read until it is collected.

        Notes:
            - This is the point of the whole format. A consumer that filters -- the visualizer
              drawing one source, the exporter writing one telescope -- should filter here
              rather than after loading everything.
        """
        data_path, _ = self._paths(owner, key)
        if not data_path.is_file():
            raise KeyError(f"no stored result '{key}' for '{owner}'")
        return pl.scan_parquet(data_path)

    def write(self, owner: str, key: str, frame: pl.DataFrame, metadata: Dict[str, Any]) -> None:
        """Store one result, replacing whatever was there.

        Args:
            owner (str): The observation the result belongs to.
            key (str): Which calculation.
            frame (pl.DataFrame): The result.
            metadata (Dict[str, Any]): What it was computed with. Anything unserializable is
                dropped with a warning rather than failing the save, because losing a note
                about a result is not worth losing the result.
        """
        data_path, meta_path = self._paths(owner, key)
        data_path.parent.mkdir(parents=True, exist_ok=True)
        frame.write_parquet(data_path)

        keepable = {}
        for name, value in (metadata or {}).items():
            try:
                json.dumps(value)
                keepable[name] = value
            except (TypeError, ValueError):
                logger.warning("Dropping unserializable metadata '%s' for result '%s' of '%s'",
                               name, key, owner)
        meta_path.write_text(json.dumps(keepable, indent=2), encoding="utf-8")
        logger.debug("Wrote result '%s' for '%s': %s rows", key, owner, frame.height)

    def drop(self, owner: str, key: Optional[str] = None) -> None:
        """Remove one stored result, or every result of an owner."""
        if key is None:
            shutil.rmtree(self.root / owner, ignore_errors=True)
            return
        for path in self._paths(owner, key):
            path.unlink(missing_ok=True)


class CalculatedData:
    """The calculated results of one observation, read from disk only when asked for.

    Behaves like the dictionary it replaces, so nothing that reads results had to change:
    `results[key]`, `results.get(key)`, `results.items()`, `key in results`, `len(results)`.

    Args:
        owner (str): The observation these belong to.
        store (Optional[ResultStore]): Where results are kept. None means memory only, which
            is what an observation not yet part of a saved project has.
        resident (Optional[Dict[str, Dict]]): Results already in hand.

    Notes:
        - **A key on disk is a key that exists.** `in`, `len` and `keys` answer from the
          filenames, which costs a directory listing rather than a read.
        - Anything set is held and marked unwritten until `flush` is called. Saving a project
          is what calls it.
    """

    def __init__(self, owner: str, store: Optional[ResultStore] = None,
                 resident: Optional[Dict[str, Dict]] = None):
        self._owner = owner
        self._store = store
        self._resident: Dict[str, Dict] = dict(resident or {})
        self._unwritten = set(self._resident)

    def attach(self, store: ResultStore, owner: Optional[str] = None) -> None:
        """Point these results at a store, so what is held can be written and read back.

        Args:
            store (ResultStore): Where the results live on disk.
            owner (Optional[str]): The name they are filed under. Passing a different name
                than the one already in use is a rename, and the results move with it.

        Notes:
            - Results on disk are filed under the owner's name, so renaming an observation
              would otherwise strand them: the new name finds nothing, and the old directory
              is left for the next save to delete. They are moved here instead, which is the
              one moment both names are known.
        """
        renamed = (owner is not None and owner != self._owner
                   and self._store is not None and store.root == self._store.root)
        if renamed:
            self._store.rename_owner(self._owner, owner)

        self._store = store
        if owner is not None:
            self._owner = owner

    def metadata(self, key: str) -> Dict[str, Any]:
        """Return one result's metadata, reading the result only if it is not on disk yet."""
        if self._store:
            stored = self._store.metadata(self._owner, key)
            if stored is not None:
                return stored
        held = self._resident.get(key)
        return (held or {}).get("metadata", {}) or {}

    @property
    def owner(self) -> str:
        return self._owner

    def _stored_keys(self) -> List[str]:
        return self._store.keys(self._owner) if self._store else []

    def __contains__(self, key: str) -> bool:
        return key in self._resident or (bool(self._store) and self._store.has(self._owner, key))

    def __len__(self) -> int:
        return len(self.keys())

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def keys(self) -> List[str]:
        """Every result this observation has, whether or not any of them is in memory."""
        return sorted(set(self._resident) | set(self._stored_keys()))

    def __getitem__(self, key: str) -> Dict[str, Any]:
        if key in self._resident:
            return self._resident[key]
        if self._store and self._store.has(self._owner, key):
            loaded = self._store.read(self._owner, key)
            self._resident[key] = loaded
            return loaded
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __setitem__(self, key: str, value: Dict[str, Any]) -> None:
        self._resident[key] = value
        self._unwritten.add(key)

    def items(self):
        """Every result, loading each as it is reached.

        Notes:
            - This is the expensive way to read results and the only one the old dictionary
              offered. Prefer `keys()` and then one `[key]`, or `scan(key)` where a filter can
              be pushed into the read.
        """
        return [(key, self[key]) for key in self.keys()]

    def values(self):
        return [self[key] for key in self.keys()]

    def scan(self, key: str) -> pl.LazyFrame:
        """A lazy view of one result, so a filter reaches the read rather than the result.

        Raises:
            KeyError: If the result is neither held nor stored.
        """
        if self._store and self._store.has(self._owner, key):
            return self._store.scan(self._owner, key)
        if key in self._resident:
            return self._resident[key]["data"].lazy()
        raise KeyError(key)

    def clear(self) -> None:
        """Forget every result, in memory and on disk."""
        self._resident.clear()
        self._unwritten.clear()
        if self._store:
            self._store.drop(self._owner)

    def release(self, key: Optional[str] = None) -> None:
        """Drop what is held in memory, keeping what is on disk.

        Args:
            key (Optional[str]): One result, or every written one when None.

        Notes:
            - An unwritten result is never released, because there would be nowhere to read it
              back from. This is what the residency budget in D4 will call.
        """
        keys = [key] if key else list(self._resident)
        for name in keys:
            if name in self._unwritten:
                continue
            self._resident.pop(name, None)

    def copy(self) -> Dict[str, Dict]:
        """Every result as a plain dictionary. Loads all of them; use sparingly."""
        return {key: self[key] for key in self.keys()}

    def flush(self, store: Optional[ResultStore] = None) -> int:
        """Write everything held but not yet stored.

        Args:
            store (Optional[ResultStore]): Where to write, if not already attached.

        Returns:
            int: How many results were written.
        """
        if store is not None:
            self._store = store
        if self._store is None:
            raise ValueError(f"no store to flush results of '{self._owner}' to")
        for key in sorted(self._unwritten):
            entry = self._resident[key]
            self._store.write(self._owner, key, entry["data"], entry.get("metadata") or {})
        written = len(self._unwritten)
        self._unwritten.clear()
        return written

    def __repr__(self) -> str:
        return (f"CalculatedData(owner={self._owner!r}, resident={len(self._resident)}, "
                f"stored={len(self._stored_keys())})")
