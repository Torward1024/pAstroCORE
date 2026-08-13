"""Telling whether a calculated result still describes the configuration in hand.

Measured before this existed: moving a telescope 1 000 km and recalculating returned the
previous numbers, unchanged and without a word. A cached result was keyed by its store key
alone, so nothing about what it had been computed from was ever compared against what was
there now.

The whole answer needs two halves, and neither works without the other. A hash notices that
something changed but not what depends on it; a dependency graph knows what depends on what but
not whether anything moved. What makes the useful part reachable now, without MSB's graph, is
that **each calculation already knows what it reads**. `beam_pattern` does not look at scans;
`times` does not look at telescopes. So each result declares what it reads, in its own schema
beside its columns and dtypes, and the hash is taken over that subset rather than over the
whole observation.

The declaration lives in the schema on purpose. A table in this module would be a second file
to remember when a calculation is added, and forgetting it fails quietly -- a result that
depends on everything looks stale whenever anything is edited. A calculation cannot be added
without a schema entry, so that is where the declaration belongs, and a test refuses a schema
that does not carry one.

**Where this ends up.** The machinery here is not specific to radio astronomy: fingerprint the
inputs, stamp the result, compare on read, answer in three values. That belongs in MSB
eventually, beside the dependency graph of P1 -- which needs the same declaration to know what
a change invalidates and to know which calculations may run at once. What is specific is only
the vocabulary: "telescopes", "sources", "scans", "frequencies" are this model's parts. It is
built here rather than there because putting half a mechanism into MSB before P1 is designed
would leave the graph to be built around a shape chosen for a smaller problem.

That is what keeps this from being unbearable. Hashing everything would mark every result stale
whenever anything at all was edited, and "everything" would then be the only thing left to
recompute -- which is the objection to staleness detection, and it is an objection to doing it
coarsely rather than to doing it.

Staleness is a **state, not an event**. Nothing here raises, blocks, recalculates or notifies.
A stale result stays readable and is labelled; what to do about it is the user's decision.
"""
import hashlib
import json
from typing import Any, Dict, Optional, Tuple

from msb_arch.utils.logging_setup import logger

from pastrocore.base.data_structure import CalculatedDataStructure

#: The metadata field a result's input fingerprint is stored under.
DIGEST_FIELD = "inputs_digest"

#: Parameters that change the answer without being part of the model.
PARAMETERS = ("time_step", "target_telescope", "units")

_ACCESSORS = {
    "telescopes": "get_telescopes",
    "sources": "get_sources",
    "scans": "get_scans",
    "frequencies": "get_frequencies",
}


def dependencies_of(key: str) -> Tuple[str, ...]:
    """Return the parts of an observation a result depends on.

    Args:
        key (str): The calculation's store key.

    Returns:
        Tuple[str, ...]: The parts it reads, or every part if it declares none.

    Notes:
        - Read from the result's own schema rather than from a table here. A new calculation
          already has to register there -- it cannot produce a frame without dtypes -- so the
          declaration cannot be forgotten in a second file that nobody thinks to open.
    """
    return CalculatedDataStructure.get_dependencies(key)


def digest(observation: Any, key: str, metadata: Optional[Dict[str, Any]] = None,
           parts_cache: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Fingerprint the inputs one calculation depends on.

    Args:
        observation (Observation): The object the result belongs to.
        key (str): The calculation's store key.
        metadata (Optional[Dict[str, Any]]): What it was computed with. Only the parameters in
            `PARAMETERS` are taken, because the rest of the metadata describes the *result*
            rather than its inputs, and including it would make every result stale against
            itself.
        parts_cache (Optional[Dict[str, Any]]): Somewhere to keep each part's serialization,
            for a caller asking about several results of one observation.

    Returns:
        Optional[str]: A short hex digest, or None if the observation could not be read -- in
            which case nothing can be said about freshness, and nothing is.
    """
    parts = {}
    # Serialising a part is not free -- a container of scans converts every scan inside it --
    # and a project has a dozen results whose dependencies overlap almost entirely. Without
    # this, opening one project converted the same scan ten times over, which is what a user
    # saw in the log.
    cache = parts_cache if parts_cache is not None else {}
    try:
        for name in dependencies_of(key):
            accessor = getattr(observation, _ACCESSORS[name], None)
            if accessor is None:
                continue
            if name not in cache:
                cache[name] = accessor().to_dict()
            parts[name] = cache[name]
        for name in PARAMETERS:
            if metadata and metadata.get(name) is not None:
                parts[name] = metadata[name]
    except Exception as e:
        logger.debug("Cannot fingerprint the inputs of '%s': %s", key, str(e))
        return None

    canonical = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


def stamp(observation: Any, key: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Return metadata carrying the fingerprint of the inputs it was computed from.

    Args:
        observation (Observation): What it was computed from.
        key (str): The calculation's store key.
        metadata (Dict[str, Any]): What is already known about the result.

    Returns:
        Dict[str, Any]: The same metadata with `inputs_digest` added, or unchanged if the
            fingerprint could not be taken.
    """
    fingerprint = digest(observation, key, metadata)
    if fingerprint is None:
        return metadata
    stamped = dict(metadata)
    stamped[DIGEST_FIELD] = fingerprint
    return stamped


def is_stale(observation: Any, key: str,
             parts_cache: Optional[Dict[str, Any]] = None) -> Optional[bool]:
    """Report whether a stored result was computed from a different configuration.

    Args:
        observation (Observation): The object holding the result.
        key (str): The calculation's store key.

    Returns:
        Optional[bool]: True if the inputs have changed since it was computed, False if they
            have not, and **None if it cannot be told** -- because the result predates this
            mechanism, or the fingerprint could not be taken.

    Notes:
        - Three answers rather than two, on purpose. A result saved before results carried
          fingerprints is not stale and is not fresh: nothing is known about it, and reporting
          "current" would be a claim, while reporting "stale" would send a user to recompute
          everything they own the first time they open an old project.
    """
    metadata = observation.get_calculated_metadata(key) or {}
    recorded = metadata.get(DIGEST_FIELD)
    if not recorded:
        return None

    current = digest(observation, key, metadata, parts_cache=parts_cache)
    if current is None:
        return None
    return current != recorded


#: Marks a fingerprint that was adopted when a project was opened rather than taken when the
#: result was calculated. The distinction is kept because it is a real one.
ADOPTED_FIELD = "inputs_digest_adopted"


def adopt_baseline(observation: Any) -> int:
    """Give results that carry no fingerprint the one their configuration has right now.

    Args:
        observation (Observation): The object whose results should get a baseline.

    Returns:
        int: How many results were given one.

    Notes:
        - Without this the mechanism is invisible to every project that already exists, which
          is every project anyone has. Answering "unknown" forever is honest and useless: a
          user changes a scan, nothing is reported, and the feature has never once fired.
        - It is **not** a claim that the results are current. It records what the configuration
          was when the project was opened, so that changes *from now on* are visible, and marks
          the fingerprint as adopted so nothing later mistakes it for one taken at calculation
          time.
        - Metadata only. No result is read and no frame is rewritten.
    """
    results = observation.calculated_data
    if not hasattr(results, "keys"):
        return 0

    adopted = 0
    cache: Dict[str, Any] = {}
    for key in list(results.keys()):
        metadata = observation.get_calculated_metadata(key) or {}
        if metadata.get(DIGEST_FIELD):
            continue
        fingerprint = digest(observation, key, metadata, parts_cache=cache)
        if fingerprint is None:
            continue
        updated = dict(metadata)
        updated[DIGEST_FIELD] = fingerprint
        updated[ADOPTED_FIELD] = True
        if _rewrite_metadata(results, observation.name, key, updated):
            adopted += 1

    if adopted:
        logger.info("Recorded the current configuration as the baseline for %s result(s) of "
                    "'%s'; changes from now on will be reported", adopted, observation.name)
    return adopted


def _rewrite_metadata(results: Any, owner: str, key: str, metadata: Dict[str, Any]) -> bool:
    """Replace one result's metadata without touching the result itself."""
    store = getattr(results, "_store", None)
    if store is None:
        held = results._resident.get(key) if hasattr(results, "_resident") else None
        if held is None:
            return False
        held["metadata"] = metadata
        return True
    try:
        store.write_metadata(owner, key, metadata)
        return True
    except Exception as e:
        logger.debug("Could not record a baseline for '%s' of '%s': %s", key, owner, str(e))
        return False


def same_metadata(one: Any, other: Any) -> bool:
    """Report whether two metadata mappings say the same thing.

    Args:
        one: A metadata mapping, or anything inside one.
        other: The same.

    Returns:
        bool: True when they are equal all the way down.

    Notes:
        - `==` is not enough. Mollweide records the source coordinates it draws against and
          those are numpy arrays, so comparing two such mappings produces an *array* rather
          than an answer, and asking whether it is true raises:

              The truth value of an array with more than one element is ambiguous

          which the calculator's broad handler turned into a failed calculation. It only bit
          when the two arrays were distinct objects -- that is, when the result had genuinely
          been recomputed -- because Python compares a mapping's values by identity first.
    """
    if one is other:
        return True
    if isinstance(one, dict) and isinstance(other, dict):
        return one.keys() == other.keys() and all(
            same_metadata(one[key], other[key]) for key in one)
    if isinstance(one, (list, tuple)) and isinstance(other, (list, tuple)):
        return len(one) == len(other) and all(
            same_metadata(a, b) for a, b in zip(one, other))
    if hasattr(one, "shape") or hasattr(other, "shape"):
        import numpy as np

        return bool(np.array_equal(np.asarray(one), np.asarray(other), equal_nan=True))
    return bool(one == other)


def record_metadata(observation: Any, key: str, metadata: Dict[str, Any]) -> bool:
    """Replace a result's metadata, leaving the result itself where it is.

    Args:
        observation (Observation): The owner.
        key (str): The store key.
        metadata (Dict[str, Any]): What to record.

    Returns:
        bool: Whether it was recorded.

    Notes:
        - The calculator stores a frame while computing it and then has to correct its
          metadata with the freshness stamp. Storing the frame a second time to carry the
          correction wrote the parquet twice for every calculation, which since results reach
          the disk when they are made is a real cost rather than a tidiness one.
    """
    return _rewrite_metadata(observation.calculated_data, observation.name, key, metadata)


def stale_results(observation: Any) -> Tuple[str, ...]:
    """Return the keys of every result whose inputs have changed.

    Args:
        observation (Observation): The object to check.

    Returns:
        Tuple[str, ...]: Sorted store keys. Empty when nothing is known to be stale, which
            includes the case where nothing can be told.

    Notes:
        - Reads no result. The answer comes from the metadata sidecars and the model, so
          asking costs a directory listing rather than the project.
    """
    results = observation.calculated_data
    keys = list(results.keys()) if hasattr(results, "keys") else []
    # One cache for the whole question: the dozen results of an observation depend on nearly
    # the same handful of parts, and the explorer asks this on every refresh.
    cache: Dict[str, Any] = {}
    return tuple(sorted(key for key in keys
                        if is_stale(observation, key, parts_cache=cache) is True))
