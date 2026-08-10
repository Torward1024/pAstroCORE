"""Recomputing a saved project must reproduce what it was saved holding.

These are characterization tests, and the distinction from unit tests matters. They do not
claim the physics is right -- that is established by the author and by the science. They claim
it does not *change*, which is the only thing a refactoring can break and the only thing a
machine can check.

The reference is the project file itself. It holds eleven results the author computed and
trusts; clearing them and calculating again has to produce the same numbers. Nothing has to be
recorded, nothing can drift out of date, and a failure means exactly one thing.

Comparison is by fingerprint -- shape, columns, and a digest of the values rounded to a
tolerance -- rather than field by field, because a frame of ten thousand rows compared
element-wise is slow to run and unreadable when it fails.
"""
import hashlib

import pytest

# Rounding before hashing, so the last bits of a float do not make the suite fragile across
# platforms while a real change of formula still moves the digest.
TOLERANCE = 6


def fingerprint(frame):
    """Reduce a result to something small, stable and comparable.

    Args:
        frame: A Polars DataFrame.

    Returns:
        tuple: `(rows, columns, digest)`.
    """
    columns = list(frame.columns)
    digest = hashlib.sha256()
    digest.update(",".join(columns).encode())
    for column in columns:
        for value in frame[column].to_list():
            if isinstance(value, float):
                value = round(value, TOLERANCE)
            digest.update(repr(value).encode())
    return frame.height, columns, digest.hexdigest()[:32]


def recompute(manipulator, observation, key, metadata):
    """Calculate one result from scratch, with the parameters it was originally computed with.

    Args:
        manipulator (ScheduleManipulator): The entry point.
        observation (Observation): The object to calculate for.
        key (str): The calculation to run.
        metadata (dict): What the saved result recorded about how it was produced.

    Returns:
        The recomputed frame, or None if the request failed.

    Notes:
        - `time_step` is passed back in because the cache is keyed partly on it, and because
          a different step produces different numbers. Omitting it would compare two different
          calculations and call the difference a regression.
    """
    attributes = {"method": key, "recalculate": True}
    if metadata.get("time_step") is not None:
        attributes["time_step"] = metadata["time_step"]

    response = manipulator.calculate(observation, raise_on_error=False, **attributes)
    if isinstance(response, dict) and "status" in response:
        if response["status"] is False:
            return None
        return response["result"]
    return response


# The saved project stores results under these keys. `times` is what the calculator calls
# `time_arrays`; the rest are named after their calculation.
STORE_KEYS = ["times", "telescope_positions", "source_visibility", "uv_coverage",
              "sun_angles", "az_el", "time_on_source", "beam_pattern",
              "baseline_projections", "mollweide_tracks", "parallactic_angle"]


@pytest.mark.parametrize("key", STORE_KEYS)
def test_recomputing_reproduces_the_saved_result(manipulator, observation, saved_results, key):
    """The whole point of stage 0. If this fails, a formula moved."""
    if key not in saved_results:
        pytest.skip(f"the fixture project holds no '{key}'")

    saved = saved_results[key]
    expected_frame = saved["data"]
    method = "time_arrays" if key == "times" else key

    observation.calculated_data.clear()
    actual_frame = recompute(manipulator, observation, method, saved.get("metadata") or {})

    assert actual_frame is not None, f"'{method}' could not be recomputed at all"
    assert not actual_frame.is_empty(), (
        f"'{method}' recomputed to an empty frame where the project holds "
        f"{expected_frame.height} rows"
    )

    actual = fingerprint(actual_frame)
    expected = fingerprint(expected_frame)

    assert actual[0] == expected[0], f"'{method}' changed shape: {expected[0]} -> {actual[0]} rows"
    assert actual[1] == expected[1], f"'{method}' changed columns"
    assert actual[2] == expected[2], (
        f"'{method}' produces different numbers than the saved project.\n"
        f"  If this change is deliberate, recompute the fixture and commit it with the reason."
    )


def test_the_fixture_actually_holds_results():
    """A fixture whose calculations are all empty would let every test above pass vacuously."""
    import json
    import pathlib

    from conftest import FIXTURE

    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    observation = next(iter(data["items"].values()))
    stored = observation.get("calculated_data", {})
    assert len(stored) >= 10, f"the fixture holds only {len(stored)} results"
