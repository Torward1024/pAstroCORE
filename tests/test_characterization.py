"""Recomputing a saved project must reproduce what it was saved holding.

These are characterization tests, and the distinction from unit tests matters. They do not
claim the physics is right -- that is established by the author and by the science. They claim
it does not *change*, which is the only thing a refactoring can break and the only thing a
machine can check.

The reference is the project file itself. It holds eleven results the author computed and
trusts; clearing them and calculating again has to produce the same numbers. Nothing has to be
recorded separately and nothing can drift out of date.

Shape and columns must match exactly. Values are compared with a tolerance, for a reason worth
reading before changing it -- see `RELATIVE_TOLERANCE`.
"""
import math

import pytest

# How far a recomputed value may sit from the saved one and still count as the same number.
#
# The first version of this file hashed the values, and a digest cannot express a tolerance.
# Five calculations then failed on a build machine while passing locally: `telescope_positions`,
# `uv_coverage`, `az_el`, `mollweide_tracks` and `parallactic_angle`. None of them was broken.
# All five depend on astropy's Earth-orientation tables, which are updated, so identical code
# legitimately produces slightly different numbers depending on which revision is in hand.
#
# Freezing the tables is not the answer either, and was tried: the bundled data ends in March
# 2025 while the fixture observes in August 2026, so pinning makes astropy extrapolate
# seventeen months and the numbers move *further* -- nine failures instead of five.
#
# So the comparison carries a tolerance, and the number comes from measurement rather than
# from estimation -- because the estimate was wrong by fifty times. Reasoning from polar motion
# and UT1 drift suggested a relative difference near 1e-6; a build machine actually reported
# 4.98e-05 on `telescope_positions.y` and 1.14e-05 on `az_el.az`. Five parts in a hundred
# thousand of a coordinate near 1e6 metres is fifty metres, which is about a tenth of a second
# of UT1 -- entirely ordinary for a prediction months ahead, and so it is noise rather than a
# defect.
#
# 5e-4 sits ten times above the largest difference observed and twenty times below the parts in
# a hundred that a changed formula moves. The test below nudges a column by one part in a
# thousand and requires that to fail, so the gap is asserted rather than assumed.
RELATIVE_TOLERANCE = 5e-4

# Below this magnitude a relative comparison is meaningless, so it becomes an absolute one.
ABSOLUTE_FLOOR = 1e-8


def worst_difference(actual, expected):
    """Return the largest relative difference between two frames, and the column it is in.

    Args:
        actual: The recomputed frame.
        expected: The frame the project was saved holding.

    Returns:
        tuple: `(difference, column)`. A non-numeric value that differs reports as infinite,
            so the assertion names the column rather than hiding behind a number.
    """
    worst, where = 0.0, ""
    for column in expected.columns:
        for left, right in zip(actual[column].to_list(), expected[column].to_list()):
            if isinstance(left, float) and isinstance(right, float):
                if math.isnan(left) and math.isnan(right):
                    continue
                if math.isnan(left) or math.isnan(right):
                    # A value that gained or lost its NaN is a real change, and this branch
                    # exists because the arithmetic below cannot report it: the difference
                    # comes out NaN, and `NaN > worst` is false, so it was silently ignored.
                    # That hid a genuine defect -- baseline projections were entirely NaN and
                    # this comparison called the recomputation identical.
                    difference = math.inf
                else:
                    scale = max(abs(left), abs(right), ABSOLUTE_FLOOR)
                    difference = abs(left - right) / scale
            else:
                difference = 0.0 if left == right else math.inf
            if difference > worst:
                worst, where = difference, column
    return worst, where


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
        - `time_step` is passed back in because the cache is keyed partly on it, and because a
          different step produces different numbers. Omitting it would compare two different
          calculations and call the difference a regression.
    """
    attributes = {"method": key, "recalculate": True}
    if metadata.get("time_step") is not None:
        attributes["time_step"] = metadata["time_step"]

    response = manipulator.calculate(observation, raise_on_error=False, **attributes)
    return response.value if response.ok else None


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
        f"{expected_frame.height} rows")

    assert actual_frame.height == expected_frame.height, (
        f"'{method}' changed shape: {expected_frame.height} -> {actual_frame.height} rows")
    assert list(actual_frame.columns) == list(expected_frame.columns), (
        f"'{method}' changed columns")

    worst, column = worst_difference(actual_frame, expected_frame)
    assert worst <= RELATIVE_TOLERANCE, (
        "'{method}' produces different numbers than the saved project. "
        "Worst relative difference {worst:.3e} in column '{column}', tolerance {limit:.0e}. "
        "If the change is deliberate, recompute the fixture and commit it with the reason. "
        "If it is barely over the tolerance on a build machine and not on yours, it is the "
        "Earth-orientation tables, and the tolerance is what needs revisiting."
    ).format(method=method, worst=worst, column=column, limit=RELATIVE_TOLERANCE)


def test_the_fixture_actually_holds_results():
    """A fixture whose calculations are all empty would let every test above pass vacuously."""
    import json

    from conftest import FIXTURE

    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    observation = next(iter(data["items"].values()))
    stored = observation.get("calculated_data", {})
    assert len(stored) >= 10, f"the fixture holds only {len(stored)} results"


def test_the_comparison_notices_a_real_change(manipulator, observation, saved_results):
    """A tolerance that let anything through would be worse than no test.

    A formula change moves a value by parts in a hundred; the tolerance is parts in a hundred
    thousand. This asserts the gap between the two is real rather than assumed.
    """
    saved = saved_results["telescope_positions"]["data"]
    nudged = saved.with_columns(saved[saved.columns[-1]] * 1.001)

    worst, _ = worst_difference(nudged, saved)
    assert worst > RELATIVE_TOLERANCE, "a one-in-a-thousand change must not pass"
