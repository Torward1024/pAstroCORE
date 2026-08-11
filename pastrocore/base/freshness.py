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


def digest(observation: Any, key: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Fingerprint the inputs one calculation depends on.

    Args:
        observation (Observation): The object the result belongs to.
        key (str): The calculation's store key.
        metadata (Optional[Dict[str, Any]]): What it was computed with. Only the parameters in
            `PARAMETERS` are taken, because the rest of the metadata describes the *result*
            rather than its inputs, and including it would make every result stale against
            itself.

    Returns:
        Optional[str]: A short hex digest, or None if the observation could not be read -- in
            which case nothing can be said about freshness, and nothing is.
    """
    parts = {}
    try:
        for name in dependencies_of(key):
            accessor = getattr(observation, _ACCESSORS[name], None)
            if accessor is None:
                continue
            parts[name] = accessor().to_dict()
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


def is_stale(observation: Any, key: str) -> Optional[bool]:
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

    current = digest(observation, key, metadata)
    if current is None:
        return None
    return current != recorded


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
    return tuple(sorted(key for key in keys if is_stale(observation, key) is True))
