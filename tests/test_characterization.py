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

# **Times are compared in seconds, not relatively.** A time here is an MJD near 61000, and five
# parts in ten thousand of that is thirty days: a result shifted by an hour -- a time zone, a UTC
# taken for TAI -- sat far inside the relative tolerance and passed. It was only ever caught
# through some other column that happened to move with it; `time_on_source` lost one sampling
# step from `end` and the comparison saw it in `duration`, never in `end`. Measured, times
# recompute to exactly the saved value -- they are arithmetic, untouched by Earth orientation --
# so a millisecond is a margin rather than an estimate.
TIME_COLUMNS = ("time", "start", "end")
TIME_TOLERANCE_SECONDS = 1e-3


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
                elif column in TIME_COLUMNS:
                    # Expressed on the same scale as everything else: a time off by exactly
                    # the tolerance reports as exactly `RELATIVE_TOLERANCE`.
                    seconds = abs(left - right) * 86400.0
                    difference = seconds / TIME_TOLERANCE_SECONDS * RELATIVE_TOLERANCE
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


def test_the_comparison_notices_a_time_moved_by_one_second(saved_results):
    """Relative to an MJD, one second is two parts in ten billion, and an hour barely more.
    Every time column must notice a second, whatever else moved with it."""
    for key, saved in saved_results.items():
        frame = saved["data"]
        for column in (c for c in TIME_COLUMNS if c in frame.columns):
            moved = frame.with_columns(frame[column] + 1.0 / 86400.0)
            worst, where = worst_difference(moved, frame)
            assert worst > RELATIVE_TOLERANCE and where == column, (
                f"'{key}.{column}' moved by a second and the comparison did not see it")


def test_visibility_transforms_only_the_frame_the_mount_is_limited_in(project, monkeypatch):
    """An azimuthal dish is bounded in elevation and azimuth and never looks at the hour angle;
    an equatorial one is the other way round. Both transforms were computed for every station
    and one of them thrown away -- and each is an erfa transform over the whole time grid, so
    the step cost twice what it had to for an array of one kind, which every array here is.

    Counted rather than timed. What is asserted is that the work is not done, not that the
    clock moved.
    """
    from pastrocore.super import schedule_calculator
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    observation = project.observations()[0]
    mounts = {telescope.get("mount_type").value
              for telescope in observation.get_telescopes().get_items()}
    assert mounts == {"AZIM"}, f"this fixture is meant to be all azimuthal, it is {mounts}"

    built = []
    original = schedule_calculator.HADec
    monkeypatch.setattr(schedule_calculator, "HADec",
                        lambda *args, **kwargs: built.append(1) or original(*args, **kwargs))

    ScheduleManipulator(project).compute(
        obj=observation, method="run", calculations=["source_visibility"],
        time_step=600.0, recalculate=True)

    assert not built, (
        f"the hour-angle frame was built {len(built)} time(s) for an array that cannot be "
        f"limited in it")


@pytest.mark.parametrize("scans", [1, 6])
def test_the_three_steps_that_look_from_a_station_share_one_transform(monkeypatch, scans):
    """Visibility, az/el and the parallactic angle each rebuilt a station's location and
    transformed the source into the same frame over the same samples -- together more than half
    of a run's work. Then they shared it, but still one transform per scan per station, and
    each costs about twelve milliseconds before it touches a sample: fifty scans at ten stations
    spent six seconds on five hundred calls. Counted: one AltAz for the whole observation."""
    from astropy.time import Time

    from pastrocore.base.observation import Observation
    from pastrocore.super import schedule_calculator
    from pastrocore.super.schedule_manipulator import ScheduleManipulator
    from pastrocore.super.schedule_project import ScheduleProject

    observation = Observation(code="MANY")
    for code, x, y, z in (("Sv", 2730173.6, 1562442.8, 5529969.2),
                          ("Zc", 3451207.5, 3060375.4, 4391915.1),
                          ("Bd", -838201.1, 3865751.6, 4987670.9)):
        observation.get_telescopes().create_telescope(code=code, name=code, x=x, y=y, z=z)
    for index, (ra, dec) in enumerate([(0.2, 50.0), (9.0, 60.0)]):
        observation.get_sources().create_source(name=f"S{index}", ra_h=ra, de_d=dec)
    observation.get_frequencies().create_if(name="x", frequency=8400.0, bandwidth=16.0)
    for index in range(scans):
        observation.get_scans().create_scan(
            name=f"No{index:04d}", start=Time(Time("2026-03-01T00:00:00").jd + index * 700 / 86400,
                                              format="jd"),
            duration=600.0, source=observation.get_sources().get(f"S{index % 2}"),
            telescopes=observation.get_telescopes().get_items(),
            frequencies=observation.get_frequencies().get_items(), observation=observation)
    project = ScheduleProject(name="many")
    project.add_item(observation)

    built = []
    original = schedule_calculator.AltAz
    monkeypatch.setattr(schedule_calculator, "AltAz",
                        lambda *args, **kwargs: built.append(1) or original(*args, **kwargs))

    ScheduleManipulator(project).compute(
        obj=None, method="run", targets=[project.observations()[0]],
        calculations=["source_visibility", "az_el", "parallactic_angle"],
        time_step=120.0, force=True)

    assert len(built) == 1, f"{len(built)} AltAz frames for 3 stations over {scans} scan(s)"


def test_the_shared_transforms_stay_within_their_budget(manipulator, observation, monkeypatch):
    """Keyed by content, so nothing goes stale -- which also means nothing leaves unless
    something makes it. A day at a one-second step is 6 MB a station; the bound is bytes."""
    import numpy as np

    from pastrocore.super.schedule_calculator import ScheduleCalculator

    calculator = ScheduleCalculator(manipulator)
    monkeypatch.setattr(ScheduleCalculator, "TOPOCENTRIC_CACHE_BYTES", 200_000)
    source = observation.get_sources().get_items()[0]
    station = np.array(observation.get_telescopes().get_items()[0].get_coordinates())

    for offset in range(4):
        times = 61262.0 + offset + np.arange(3000) / 86400.0
        calculator._topocentric(source, np.tile(station, (len(times), 1)), times, "altaz")

    held = sum(values.nbytes for entry in calculator._topocentric_cache.values() for values in entry)
    assert held <= 200_000 or len(calculator._topocentric_cache) == 1
    assert held == calculator._topocentric_bytes, "the running count drifted from what is held"

    first = calculator._topocentric(source, np.tile(station, (3000, 1)), times, "altaz")
    again = calculator._topocentric(source, np.tile(station, (3000, 1)), times, "altaz")
    assert first is again, "the same question was answered twice"
    assert not first[0].flags.writeable, "a shared answer must not be editable by one reader"


def test_ground_stations_are_rotated_to_gcrs_in_one_transform(monkeypatch):
    """ITRS to GCRS depends on the moment and not on the station, so every station over every
    scan is one transform. It was one per scan per station: three seconds for ten stations over
    fifty scans. Counted over six scans and three stations."""
    from astropy.time import Time

    from pastrocore.base.observation import Observation
    from pastrocore.super import schedule_calculator
    from pastrocore.super.schedule_manipulator import ScheduleManipulator
    from pastrocore.super.schedule_project import ScheduleProject

    observation = Observation(code="MANY")
    for code, x, y, z in (("Sv", 2730173.6, 1562442.8, 5529969.2),
                          ("Zc", 3451207.5, 3060375.4, 4391915.1),
                          ("Bd", -838201.1, 3865751.6, 4987670.9)):
        observation.get_telescopes().create_telescope(code=code, name=code, x=x, y=y, z=z)
    observation.get_sources().create_source(name="S", ra_h=3.0, de_d=50.0)
    observation.get_frequencies().create_if(name="x", frequency=8400.0, bandwidth=16.0)
    for index in range(6):
        observation.get_scans().create_scan(
            name=f"No{index:04d}", start=Time(Time("2026-03-01T00:00:00").jd + index * 700 / 86400,
                                              format="jd"),
            duration=600.0, source=observation.get_sources().get("S"),
            telescopes=observation.get_telescopes().get_items(),
            frequencies=observation.get_frequencies().get_items(), observation=observation)
    project = ScheduleProject(name="many")
    project.add_item(observation)

    rotated = []
    original = schedule_calculator.ITRS
    monkeypatch.setattr(schedule_calculator, "ITRS",
                        lambda *args, **kwargs: rotated.append(args) or original(*args, **kwargs))

    ScheduleManipulator(project).compute(obj=None, method="run", targets=[project.observations()[0]],
                                         calculations=["telescope_positions"], time_step=120.0,
                                         force=True)

    # A frame built with data is a set of positions being rotated; one without is a destination.
    with_positions = [args for args in rotated if args]
    assert len(with_positions) == 1, f"{len(with_positions)} rotations for 3 stations over 6 scans"
