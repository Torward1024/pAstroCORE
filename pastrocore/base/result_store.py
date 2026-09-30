"""Where calculated results live when they are not in memory.

A project is a directory:

    project.pastro/
        project.json                            the model
        results/
            <observation>/uv_coverage.parquet
            <observation>/source_visibility.parquet

Parquet, because `polars.scan_parquet` pushes a filter into the read: drawing one source of
three hundred touches 1 584 rows instead of 475 200, 2.6 times faster than reading everything
and filtering after. A member of a zip has to be unpacked first, which loses that.

`CalculatedData` is what the rest of the application sees. It behaves like a dictionary --
`results["uv_coverage"]`, `.get`, `.items`, `in`, `len` -- and reads a key from disk only when
one is asked for.
"""
import json
import math
import os
import shutil
import time
import weakref
from collections import OrderedDict
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Dict, Iterator, List, Optional

import polars as pl
from msb_arch.utils.logging_setup import logger

from pastrocore.utils.machine import available_memory

__all__ = ["CalculatedData", "ResultStore"]

METADATA_SUFFIX = ".meta.json"

#: Appended to a file while it is being written. Nothing globs for it: `*.parquet` does not match
#: `uv_coverage.parquet.partial`, so a write interrupted half way is never taken for a result.
PARTIAL_SUFFIX = ".partial"


def _partial(path: Path) -> Path:
    """The sibling a file is written to before it replaces `path`."""
    return path.with_name(path.name + PARTIAL_SUFFIX)


def remove_tree(path: Path, attempts: int = 5) -> None:
    """Delete a directory, allowing Windows the moment it takes to let go of a fresh file.

    Args:
        path (Path): What to delete.
        attempts (int): How many times to try before the error is real.

    Raises:
        OSError: If it still cannot be removed.

    Notes:
        - A file written a moment ago may be held by the indexer or the antivirus, its delete
          only pending, and the directory's removal then fails with WinError 145.
    """
    for attempt in range(attempts):
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            return
        except OSError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.05 * 2 ** attempt)


def remove_file(path: Path, attempts: int = 5) -> None:
    """Delete a file, allowing the machine the moment it takes to let go of a fresh one.

    Args:
        path (Path): What to delete. A path that is already gone is not an error.
        attempts (int): How many times to try before the error is real.

    Raises:
        OSError: If it still cannot be removed.

    Notes:
        - The same pending delete `remove_tree` waits out, on the path that removes one
          result rather than a whole observation's.
    """
    for attempt in range(attempts):
        try:
            path.unlink(missing_ok=True)
            return
        except FileNotFoundError:
            return
        except OSError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.05 * 2 ** attempt)


def _discard_partials(*paths: Path) -> None:
    for path in paths:
        try:
            _partial(path).unlink(missing_ok=True)
        except OSError:
            pass


def json_safe(value: Any) -> Any:
    """Return a value JSON can actually represent, replacing what it cannot with None.

    Args:
        value (Any): Anything about to be written to a file.

    Returns:
        Any: The same value, with NaN and infinity replaced by None throughout.

    Notes:
        - `json.dumps` writes bare `NaN` and `Infinity`, which no other JSON parser accepts.
        - A span that could not be determined is absent, and `null` is how JSON says absent.
    """
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]

    # A calculation records coordinates as a numpy array, which `json.dumps` refuses.
    if hasattr(value, "tolist") and not isinstance(value, (str, bytes)):
        return json_safe(value.tolist())
    if hasattr(value, "item") and type(value).__module__ == "numpy":
        return json_safe(value.item())
    return value


class ResultStore:
    """Reads and writes one parquet file per calculated result.

    Args:
        root (Path): The `results/` directory inside a project directory.

    Notes:
        - A store pointed at a directory that does not exist is legal; the first write
          creates it.
    """

    def __init__(self, root: Path):
        self.root = Path(root)

    def _paths(self, owner: str, key: str) -> tuple:
        """Return the parquet and metadata paths for one result."""
        directory = self.root / owner
        return directory / f"{key}.parquet", directory / f"{key}{METADATA_SUFFIX}"

    def write_metadata(self, owner: str, key: str, metadata: Dict[str, Any]) -> None:
        """Replace one result's metadata, leaving the result itself untouched.

        Args:
            owner (str): The observation it belongs to.
            key (str): The calculation that produced it.
            metadata (Dict[str, Any]): What to record.

        Notes:
            - Metadata lives in its own file, which is what makes this cheap: nothing is read
              and no parquet is rewritten.
        """
        _, metadata_path = self._paths(owner, key)
        if not metadata_path.parent.is_dir():
            raise IOError(f"no results stored for '{owner}'")
        text = json.dumps(json_safe(metadata), indent=2, allow_nan=False)
        try:
            _partial(metadata_path).write_text(text, encoding="utf-8")
            os.replace(_partial(metadata_path), metadata_path)
        except BaseException:
            _discard_partials(metadata_path)
            raise

    def metadata(self, owner: str, key: str) -> Optional[Dict[str, Any]]:
        """Return one result's metadata without reading the result.

        Args:
            owner (str): The observation the result belongs to.
            key (str): The calculation that produced it.

        Returns:
            Optional[Dict[str, Any]]: What was recorded about how the result was produced, or
                None if there is no such result.

        Notes:
            - Metadata is a file of its own beside the parquet, so this reads no rows.
        """
        _, metadata_path = self._paths(owner, key)
        if not metadata_path.is_file():
            return None
        return json.loads(metadata_path.read_text(encoding="utf-8-sig"))

    def rename_owner(self, old: str, new: str) -> None:
        """Move an owner's results to a new name, so a rename does not strand them.

        Args:
            old (str): The name the results are filed under.
            new (str): The name to file them under instead.

        Notes:
            - Results already under the new name win; the old directory is removed, not
              merged.
        """
        source, target = self.root / old, self.root / new
        if not source.is_dir():
            return
        if target.exists():
            remove_tree(source)
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
        metadata = json.loads(meta_path.read_text(encoding="utf-8-sig")) if meta_path.is_file() else {}
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
            - A caller that filters should filter here rather than after loading every row.
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

        # Whatever the caller says about the frame, the frame is the authority.
        recorded = dict(metadata or {})
        recorded.update(derived_metadata(frame))

        keepable = {}
        for name, value in recorded.items():
            try:
                keepable[name] = json_safe(value)
                json.dumps(keepable[name], allow_nan=False)
            except (TypeError, ValueError):
                keepable.pop(name, None)
                logger.warning("Dropping unserializable metadata '%s' for result '%s' of '%s'",
                               name, key, owner)

        # Beside the old ones and only then moved over them: `write_parquet` truncates
        # before it encodes, so a write that fails half way would leave nothing readable.
        try:
            frame.write_parquet(_partial(data_path))
            _partial(meta_path).write_text(json.dumps(keepable, indent=2, allow_nan=False),
                                           encoding="utf-8")
            os.replace(_partial(data_path), data_path)
            os.replace(_partial(meta_path), meta_path)
        except BaseException:
            _discard_partials(data_path, meta_path)
            raise
        logger.debug("Wrote result '%s' for '%s': %s rows", key, owner, frame.height)

    def drop(self, owner: str, key: Optional[str] = None) -> None:
        """Remove one stored result, or every result of an owner.

        Args:
            owner (str): The observation whose results to remove.
            key (Optional[str]): One result, or all of them when None.

        Raises:
            OSError: If they could not be removed, after waiting out a pending delete.

        Notes:
            - Errors are raised rather than swallowed: keys are answered from the filenames,
              so a file that stayed would be listed again as a result.
        """
        if key is None:
            remove_tree(self.root / owner)
            return
        for path in self._paths(owner, key):
            remove_file(path)


def derived_metadata(frame: "pl.DataFrame") -> Dict[str, Any]:
    """Return the metadata fields that are a restatement of the frame itself.

    Args:
        frame (pl.DataFrame): The result being stored.

    Returns:
        Dict[str, Any]: `scan_count`, and `start_time`/`end_time` when the frame records a
            time. Absent keys for a frame that has no such column, rather than nulls.

    Notes:
        - Computed here, where the frame is in hand, and they replace whatever a caller
          passed: the frame is the authority on itself.
        - Kept in metadata so a caller can read them without reading the result.
    """
    derived: Dict[str, Any] = {}
    if frame is None or frame.height == 0:
        return derived

    if "scan_name" in frame.columns:
        derived["scan_count"] = frame["scan_name"].n_unique()

    moment = next((column for column in ("time", "start") if column in frame.columns), None)
    if moment is not None:
        # `min()` over a column of nulls is None and `float(None)` raises, so a span that
        # cannot be determined is left absent.
        first = frame[moment].min()
        last = frame["end" if "end" in frame.columns else moment].max()
        if first is not None and last is not None:
            derived["start_time"] = float(first)
            derived["end_time"] = float(last)
    return derived


class ResidencyBudget:
    """How much of the machine's memory the results in hand are allowed to occupy.

    Args:
        share (float): The fraction of *available* memory to allow, between 0 and 1.
        limit_bytes (Optional[int]): An explicit ceiling, which wins over the share. Mainly
            for tests, which need a budget small enough to overflow deliberately.

    Notes:
        - A share of what is available rather than of what is installed, so the same project
          suits a laptop and a workstation.
        - It governs what may be kept, never what may be read: a result larger than the whole
          budget is still returned, and evicted as soon as anything needs room.
        - Only a result already on disk can be evicted; one not yet written has nowhere to be
          read back from.
    """

    #: Used when nothing else says otherwise. Half of what is free leaves room for the plots,
    #: which build their own arrays from what they read.
    DEFAULT_SHARE = 0.5

    def __init__(self, share: float = DEFAULT_SHARE, limit_bytes: Optional[int] = None):
        self.share = share
        self._explicit_limit = limit_bytes
        # (owner, key) in least-recently-used order.
        self._sizes: "OrderedDict[tuple, int]" = OrderedDict()
        # Weakly, so bookkeeping is never the last thing holding a result: an observation
        # the project has let go of must not keep its results resident.
        self._holders: "weakref.WeakValueDictionary[str, Any]" = weakref.WeakValueDictionary()
        self._lock = RLock()

    def __deepcopy__(self, memo: Dict) -> "ResidencyBudget":
        """Return the same budget: two would each claim the whole ceiling, and it holds a lock."""
        return self

    __copy__ = __deepcopy__

    @property
    def limit(self) -> int:
        """The current ceiling in bytes, re-read each time so it follows the machine."""
        if self._explicit_limit is not None:
            return self._explicit_limit
        return int(available_memory() * self.share)

    @property
    def held(self) -> int:
        """How many bytes of results are currently in hand."""
        with self._lock:
            return sum(self._sizes.values())

    def note(self, holder: "CalculatedData", key: str, size: int) -> None:
        """Record that a result is in hand, and evict until the budget is met again.

        Args:
            holder (CalculatedData): Who is holding it.
            key (str): Which result.
            size (int): Its size in bytes.
        """
        with self._lock:
            entry = (holder.owner, key)
            self._sizes.pop(entry, None)
            self._sizes[entry] = size
            self._holders[holder.owner] = holder
            self._evict_to_fit(keep=entry)

    def touch(self, holder: "CalculatedData", key: str) -> None:
        """Record a use, so the least recently used is the one evicted."""
        with self._lock:
            entry = (holder.owner, key)
            if entry in self._sizes:
                self._sizes.move_to_end(entry)

    def forget(self, owner: str, key: Optional[str] = None) -> None:
        """Stop counting a result that has been released by other means."""
        with self._lock:
            for entry in [e for e in self._sizes if e[0] == owner and (key is None or e[1] == key)]:
                self._sizes.pop(entry, None)

    def _evict_to_fit(self, keep: Optional[tuple] = None) -> int:
        """Release least-recently-used results until the budget is met.

        Args:
            keep (Optional[tuple]): An entry never to evict -- the one just read, which the
                caller is about to use.

        Returns:
            int: How many results were released.
        """
        limit = self.limit
        released = 0
        for entry in [e for e in self._sizes if e != keep]:
            if sum(self._sizes.values()) <= limit:
                break
            holder = self._holders.get(entry[0])
            if holder is None:
                self._sizes.pop(entry, None)
                continue
            if not holder.release_for_budget(entry[1]):
                # Not written yet, so there is nowhere to read it back from. Leave it, and
                # stop counting it against a budget it cannot be evicted to satisfy.
                self._sizes.pop(entry, None)
                continue
            self._sizes.pop(entry, None)
            released += 1
        if released:
            logger.debug("Residency budget released %s result(s); %.1f MB of %.1f MB in hand",
                         released, self.held / 1e6, limit / 1e6)
        return released


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
                 resident: Optional[Dict[str, Dict]] = None,
                 budget: Optional[ResidencyBudget] = None):
        self._owner = owner
        self._store = store
        self._resident: Dict[str, Dict] = dict(resident or {})
        self._unwritten = set(self._resident)
        self._budget = budget

    def attach(self, store: ResultStore, owner: Optional[str] = None,
               budget: Optional["ResidencyBudget"] = None) -> None:
        """Point these results at a store, so what is held can be written and read back.

        Args:
            store (ResultStore): Where the results live on disk.
            owner (Optional[str]): The name they are filed under. Passing a different name
                than the one already in use is a rename, and the results move with it.

        Notes:
            - Results are filed under the owner's name, and this is the one moment both
              names are known, so a rename moves them here.
        """
        renamed = (owner is not None and owner != self._owner
                   and self._store is not None and store.root == self._store.root)
        if renamed:
            self._store.rename_owner(self._owner, owner)

        self._store = store
        if budget is not None:
            self._budget = budget
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
            if self._budget:
                self._budget.touch(self, key)
            return self._resident[key]
        if self._store and self._store.has(self._owner, key):
            loaded = self._store.read(self._owner, key)
            self._resident[key] = loaded
            if self._budget:
                frame = loaded.get("data")
                self._budget.note(self, key, frame.estimated_size() if frame is not None else 0)
            return loaded
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __setitem__(self, key: str, value: Dict[str, Any]) -> None:
        """Hold a result, writing it through to the store at once if there is one.

        Notes:
            - Written on arrival, not at save time: the budget cannot evict what it cannot
              read back, and a result held only in memory is lost to a crash.
            - A write that fails leaves the result held and unwritten rather than raising, so
              a full disk costs the protection and not the calculation.
        """
        # Corrected here as well as in the store, so a project with nowhere to write yet is
        # described as truthfully as one that has been saved.
        frame = value.get("data") if isinstance(value, dict) else None
        if frame is not None:
            value = dict(value)
            value["metadata"] = {**(value.get("metadata") or {}), **derived_metadata(frame)}

        self._resident[key] = value
        self._unwritten.add(key)

        if self._store is None:
            return
        try:
            self._store.write(self._owner, key, value["data"], value.get("metadata") or {})
        except Exception as e:
            logger.warning("Could not write '%s' for '%s' yet, keeping it in memory: %s",
                           key, self._owner, str(e))
            return

        self._unwritten.discard(key)
        if self._budget:
            frame = value.get("data")
            self._budget.note(self, key, frame.estimated_size() if frame is not None else 0)

    def items(self):
        """Every result, loading each as it is reached. Prefer `keys()` and one `[key]`."""
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
        """Forget every result, in memory and on disk.

        Raises:
            OSError: If what is on disk could not be removed. Nothing is forgotten then, so
                what is held and what is stored still describe the same thing.
        """
        if self._store:
            self._store.drop(self._owner)
        self._resident.clear()
        self._unwritten.clear()

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
            if self._budget:
                self._budget.forget(self._owner, name)

    def release_for_budget(self, key: str) -> bool:
        """Drop one result at the budget's request.

        Args:
            key (str): The result to drop.

        Returns:
            bool: True if it was dropped, False if it cannot be -- which means it has not been
                written yet, and dropping it would lose it.
        """
        if key in self._unwritten:
            return False
        return self._resident.pop(key, None) is not None

    def copy(self) -> Dict[str, Dict]:
        """Every result as a plain dictionary. Loads all of them; use sparingly."""
        return {key: self[key] for key in self.keys()}

    def to_write(self, store: ResultStore) -> List[str]:
        """Name every result saving into a store would write, in the order it would write them.

        Args:
            store (ResultStore): The store a save is about to write into.

        Returns:
            List[str]: The results `migrate_to` would copy across, then those `flush` would
                write. A result recalculated since it was stored appears in both, because both
                writes happen.

        Notes:
            - What a save's progress is counted in. Asked before anything is written, so the
              first file already knows how many there are.
        """
        across = []
        if self._store is not None and store.root != self._store.root:
            across = [key for key in self._store.keys(self._owner) if not store.has(self._owner, key)]
        return across + sorted(self._unwritten)

    def migrate_to(self, store: ResultStore,
                   writing: Optional[Callable[[str], None]] = None) -> int:
        """Copy results already on disk into another store.

        Args:
            store (ResultStore): Where they should live from now on -- a project's own
                `results/` directory, when a project that was calculating into scratch is
                saved for the first time.
            writing (Optional[Callable[[str], None]]): Told each result's key before it is
                written.

        Returns:
            int: How many results were copied.

        Notes:
            - Copied, not moved: a save that fails halfway must leave the results where they
              were. Whoever owns the scratch clears it afterwards.
            - A result already in the destination is left alone; `attach` and `flush` write
              what was calculated since.
        """
        if self._store is None or store.root == self._store.root:
            return 0

        copied = 0
        for key in self._store.keys(self._owner):
            if store.has(self._owner, key):
                continue
            if writing is not None:
                writing(key)
            entry = self._store.read(self._owner, key)
            store.write(self._owner, key, entry["data"], entry.get("metadata") or {})
            copied += 1
        if copied:
            logger.info("Moved %s result(s) for '%s' out of scratch", copied, self._owner)
        return copied

    def write_through_to(self, store: ResultStore,
                         writing: Optional[Callable[[str], None]] = None) -> int:
        """Write what is held but unstored into another store, staying attached to this one.

        Args:
            store (ResultStore): Where to write the copies.
            writing (Optional[Callable[[str], None]]): Told each result's key before it is
                written.

        Returns:
            int: How many results were written.

        Notes:
            - `flush` writes the same results and moves in. This is for a copy -- packing a
              project to send -- where they must also go on living where they are.
        """
        for key in sorted(self._unwritten):
            if writing is not None:
                writing(key)
            entry = self._resident[key]
            store.write(self._owner, key, entry["data"], entry.get("metadata") or {})
        return len(self._unwritten)

    def flush(self, store: Optional[ResultStore] = None,
              writing: Optional[Callable[[str], None]] = None) -> int:
        """Write everything held but not yet stored.

        Args:
            store (Optional[ResultStore]): Where to write, if not already attached.
            writing (Optional[Callable[[str], None]]): Told each result's key before it is
                written.

        Returns:
            int: How many results were written.
        """
        if store is not None:
            self._store = store
        if self._store is None:
            raise ValueError(f"no store to flush results of '{self._owner}' to")
        for key in sorted(self._unwritten):
            if writing is not None:
                writing(key)
            entry = self._resident[key]
            self._store.write(self._owner, key, entry["data"], entry.get("metadata") or {})
        written = len(self._unwritten)
        self._unwritten.clear()
        return written

    def __eq__(self, other: Any) -> bool:
        """Two sets of results are equal when they hold the same results, however they hold them.

        Args:
            other (Any): The object to compare with.

        Returns:
            bool: True when both are `CalculatedData` and answer to the same keys.

        Notes:
            - On the keys, not the frames: reading every frame to answer `==` would load
              both projects. It is the rule `keys()` and `in` already use.
        """
        if not isinstance(other, CalculatedData):
            return NotImplemented
        return sorted(self.keys()) == sorted(other.keys())

    def __repr__(self) -> str:
        return (f"CalculatedData(owner={self._owner!r}, resident={len(self._resident)}, "
                f"stored={len(self._stored_keys())})")
