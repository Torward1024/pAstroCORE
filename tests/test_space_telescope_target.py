"""Pointing a ground station at a spacecraft.

The geometry differs from pointing at a source in one way that matters: a source is far enough
away that every station sees it in the same direction, and a spacecraft in Earth orbit is not.
Two stations a baseline apart point measurably differently at it, so the source machinery would
give answers that look plausible and are wrong by degrees.

These tests check the result against geometry worked out a different way -- the law of cosines
on the two geocentric distances -- rather than against a stored number. A characterization test
would only say the answer had not changed; this says it is right.
"""
import json
import math
import sys

import numpy as np
import polars as pl
import pytest

import conftest
from pastrocore.base.spacetelescope import SpaceTelescope
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject

EARTH_RADIUS = 6_378_137.0
SEMI_MAJOR_AXIS = 2.5e7


@pytest.fixture
def observation_with_a_spacecraft():
    """The fixture observation, with a spacecraft in a circular orbit added to it.

    Notes:
        - Deliberately not added to the scan. The scan supplies the time window and the ground
          stations; the spacecraft only supplies what to point at, and a downlink target does
          not take part in the observation it is being tracked during.
    """
    project = ScheduleProject.from_dict(json.loads(conftest.FIXTURE.read_text(encoding="utf-8")))
    observation = project.observations()[0]
    first_scan = observation.get_scans().get_active_items()[0]

    observation.get_telescopes().add(SpaceTelescope(
        code="RADIO", name="RadioAstron", use_kep=True,
        kepler_elements={"a": SEMI_MAJOR_AXIS, "e": 0.01, "i": 63.4, "raan": 30.0,
                         "argp": 270.0, "nu": 0.0, "epoch": first_scan.get_start(),
                         "mu": 3.986004418e14}))
    return project, observation, ScheduleManipulator(project)


def compute(manipulator, observation, method, **extra):
    """Run one calculation and return the frame, or None."""
    response = manipulator.calculate(observation, method=method, target_telescope="RADIO",
                                     time_step=300.0, recalculate=True, raise_on_error=False,
                                     **extra)
    return response.value if response.ok else None


def test_a_station_can_be_pointed_at_a_spacecraft(observation_with_a_spacecraft):
    """F1. Every station in the observation gets a direction at every sampled moment."""
    _, observation, manipulator = observation_with_a_spacecraft
    frame = compute(manipulator, observation, "telescope_az_el")

    assert frame is not None and not frame.is_empty()
    assert set(frame.columns) == {"time", "target_code", "scan_name", "telescope_code",
                                  "az", "el", "range"}
    assert sorted(frame["telescope_code"].unique().to_list()) == ["ALMA", "APEX"]
    assert frame["target_code"].unique().to_list() == ["RADIO"]


def test_the_angles_are_in_range(observation_with_a_spacecraft):
    """A bearing outside 0-360 or an elevation outside -90..90 is not a bearing."""
    _, observation, manipulator = observation_with_a_spacecraft
    frame = compute(manipulator, observation, "telescope_az_el")
    finite = frame.filter(pl.col("el").is_not_nan())

    assert finite.height > 0
    assert 0.0 <= finite["az"].min() and finite["az"].max() < 360.0
    assert -90.0 <= finite["el"].min() and finite["el"].max() <= 90.0


def test_the_range_matches_what_the_orbit_allows(observation_with_a_spacecraft):
    """The strongest cheap check: the distance to a spacecraft at a known geocentric radius,
    seen from the Earth's surface, is bounded by simple arithmetic.

    Closest when it is overhead, furthest when it is on the far side of the Earth. The orbit
    is slightly eccentric, so both bounds get a margin of `a * e`.
    """
    _, observation, manipulator = observation_with_a_spacecraft
    frame = compute(manipulator, observation, "telescope_az_el")
    distances = frame.filter(pl.col("range").is_not_nan())["range"].to_numpy()

    margin = SEMI_MAJOR_AXIS * 0.01
    assert distances.min() >= SEMI_MAJOR_AXIS - EARTH_RADIUS - margin
    assert distances.max() <= SEMI_MAJOR_AXIS + EARTH_RADIUS + margin


def test_the_elevation_agrees_with_the_law_of_cosines(observation_with_a_spacecraft):
    """Worked out a second way, from the two geocentric distances and the range.

    In the triangle Earth-centre, station, spacecraft, the angle at the station between the
    local vertical and the line of sight follows from the three sides. Elevation is ninety
    degrees less that angle. This shares no code with the calculation it checks.
    """
    _, observation, manipulator = observation_with_a_spacecraft
    frame = compute(manipulator, observation, "telescope_az_el")

    positions = compute(manipulator, observation, "telescope_positions")
    if positions is None or positions.is_empty():
        pytest.skip("no station positions to check against")

    joined = frame.join(positions, on=["time", "scan_name", "telescope_code"], how="inner")
    joined = joined.filter(pl.col("el").is_not_nan() & pl.col("x").is_not_nan())
    assert joined.height > 0, "nothing to compare"

    station_radius = np.sqrt(joined["x"].to_numpy() ** 2 + joined["y"].to_numpy() ** 2
                             + joined["z"].to_numpy() ** 2)
    line_of_sight = joined["range"].to_numpy()
    elevation = joined["el"].to_numpy()

    # Distance from the Earth's centre to the spacecraft, from the law of cosines applied at
    # the station, where the interior angle is 90 + elevation.
    interior = np.radians(90.0 + elevation)
    spacecraft_radius = np.sqrt(station_radius ** 2 + line_of_sight ** 2
                                - 2 * station_radius * line_of_sight * np.cos(interior))

    # It has to come out as the orbit's radius, within its eccentricity.
    assert np.all(np.abs(spacecraft_radius - SEMI_MAJOR_AXIS) < SEMI_MAJOR_AXIS * 0.05), (
        f"implied orbital radius {spacecraft_radius.min():.0f}..{spacecraft_radius.max():.0f} m "
        f"does not match the orbit's {SEMI_MAJOR_AXIS:.0f} m")


def test_two_stations_do_not_see_it_in_the_same_direction(observation_with_a_spacecraft):
    """The whole reason this cannot reuse the source geometry.

    A source is far enough away that a baseline does not change its direction. A spacecraft at
    twenty thousand kilometres is not, and if the two stations agree exactly then something is
    treating it as infinitely distant.
    """
    _, observation, manipulator = observation_with_a_spacecraft
    frame = compute(manipulator, observation, "telescope_az_el")

    by_station = {code: frame.filter(pl.col("telescope_code") == code).sort("time")
                  for code in frame["telescope_code"].unique().to_list()}
    first, second = by_station["ALMA"], by_station["APEX"]

    difference = np.abs(first["el"].to_numpy() - second["el"].to_numpy())
    difference = difference[~np.isnan(difference)]

    assert difference.size > 0
    assert difference.max() > 0.01, (
        "the two stations see the spacecraft at identical elevations, which would mean the "
        "geometry is treating it as infinitely far away")


def test_visibility_follows_the_elevation_limits(observation_with_a_spacecraft):
    """F2. Above the horizon is not enough: a station has a range it can drive to."""
    _, observation, manipulator = observation_with_a_spacecraft
    angles = compute(manipulator, observation, "telescope_az_el")
    visibility = compute(manipulator, observation, "telescope_visibility")

    assert visibility is not None and not visibility.is_empty()
    assert visibility.height == angles.height

    limits = {telescope.get_code(): telescope.get("elevation_range")
              for telescope in observation.get_telescopes().get_active_items()
              if not isinstance(telescope, SpaceTelescope)}

    joined = angles.join(visibility, on=["time", "scan_name", "telescope_code", "target_code"],
                         how="inner")
    for row in joined.iter_rows(named=True):
        low, high = limits[row["telescope_code"]]
        if row["el"] is None or math.isnan(row["el"]):
            assert row["visibility"] is False
        else:
            assert row["visibility"] == (low <= row["el"] <= high)


def test_it_is_sometimes_visible_and_sometimes_not(observation_with_a_spacecraft):
    """A visibility column that is all True or all False would satisfy the test above and
    mean nothing."""
    _, observation, manipulator = observation_with_a_spacecraft
    visibility = compute(manipulator, observation, "telescope_visibility")

    values = visibility["visibility"].to_list()
    assert any(values), "the spacecraft is never visible, over a whole day"
    assert not all(values), "the spacecraft never sets, over a whole day"


def test_asking_without_a_target_is_refused_rather_than_guessed(observation_with_a_spacecraft):
    """There is no sensible default: an observation may hold several spacecraft."""
    _, observation, manipulator = observation_with_a_spacecraft
    response = manipulator.calculate(observation, method="telescope_az_el", time_step=300.0,
                                     recalculate=True, raise_on_error=False)
    frame = response.value
    assert frame is None or frame.is_empty()


def test_a_target_that_is_not_there_is_refused(observation_with_a_spacecraft):
    _, observation, manipulator = observation_with_a_spacecraft
    response = manipulator.calculate(observation, method="telescope_az_el",
                                     target_telescope="NOT_THERE", time_step=300.0,
                                     recalculate=True, raise_on_error=False)
    frame = response.value
    assert frame is None or frame.is_empty()


def test_an_observation_without_a_spacecraft_pays_nothing():
    """This calculation is chosen, never run as part of an ordinary observation."""
    project = ScheduleProject.from_dict(json.loads(conftest.FIXTURE.read_text(encoding="utf-8")))
    observation = project.observations()[0]
    manipulator = ScheduleManipulator(project)

    response = manipulator.calculate(observation, method="telescope_az_el",
                                     target_telescope="RADIO", time_step=300.0,
                                     recalculate=True, raise_on_error=False)
    frame = response.value
    assert frame is None or frame.is_empty()

    # The shared machinery records that the question was asked and had no answer, which is
    # different from recording an answer. What must not happen is a frame with rows in it.
    stored = observation.calculated_data.get("telescope_az_el")
    assert stored is None or stored["data"].is_empty(), (
        "an observation with no spacecraft must not acquire pointing data")


def test_an_orbit_that_does_not_cover_the_scan_says_so():
    """F5. An uncovered time comes back NaN, and NaN reaches a plot as a blank rather than as a
    complaint -- the same silent failure as the baseline projections defect. It has to be said.
    """
    import logging

    from msb_arch.utils.logging_setup import logger as msb_logger

    from pastrocore.super.schedule_calculator import ScheduleCalculator

    project = ScheduleProject.from_dict(json.loads(conftest.FIXTURE.read_text(encoding="utf-8")))
    observation = project.observations()[0]
    scan = observation.get_scans().get_active_items()[0]

    # An orbit file covering one hour, a decade before the scan it will be asked about.
    telescope = SpaceTelescope(code="RADIO", name="RadioAstron", use_kep=False)
    observation.get_telescopes().add(telescope)

    covered = np.linspace(50000.0, 50000.0 + 1 / 24, 13)
    calculator = ScheduleCalculator(ScheduleManipulator(project))
    calculator._load_orbit_data = lambda *a, **k: {
        "times": covered,
        "positions": np.tile(np.array([[2.0e7, 0.0, 0.0]]), (len(covered), 1))}

    said = []

    class Listener(logging.Handler):
        def emit(self, record):
            said.append(record.getMessage())

    # Two obstacles, both of which made an earlier version of this test pass on an empty
    # string: msb_arch's logger does not propagate, so caplog never sees it, and the suite's
    # `quiet_logging` fixture holds it at CRITICAL so nothing is emitted at all.
    listener = Listener(level=logging.WARNING)
    previous = msb_logger.level
    msb_logger.setLevel(logging.WARNING)
    msb_logger.addHandler(listener)
    try:
        start = scan.get_start().mjd
        positions = calculator._interpolate_orbit(
            telescope, np.linspace(start, start + 0.1, 25), start, start + 0.1)
    finally:
        msb_logger.removeHandler(listener)
        msb_logger.setLevel(previous)

    assert np.all(np.isnan(positions)), "an uncovered span must not be extrapolated"
    spoken = " ".join(said)
    assert "does not cover" in spoken, f"the user was told nothing useful: {spoken}"
    assert "50000" in spoken and "61262" in spoken, (
        f"the message must name both spans so the gap is obvious: {spoken}")


def test_the_calculations_are_offered_in_the_interface(observation_with_a_spacecraft):
    """F3. A calculation nobody can choose is a calculation nobody has.

    Asserted against the catalogue rather than against a dialog's source, because the dialog no
    longer holds a list: it asks the manipulator what exists. That is the point of A5 -- adding
    a calculation makes it appear without the interface being touched, and this is what that
    claim means in practice.
    """
    project, observation, manipulator = observation_with_a_spacecraft

    response = manipulator.compute(obj=project, method="catalogue", raise_on_error=False)
    catalogue = response.value

    offered = {entry["key"] for entry in catalogue if entry["offer"]}
    assert "telescope_az_el" in offered
    assert "telescope_visibility" in offered

    labels = {entry["key"]: entry["label"] for entry in catalogue}
    assert labels["telescope_az_el"] == "Space Telescope Pointing"


def test_a_step_nobody_asks_for_is_not_offered(observation_with_a_spacecraft):
    """Positions and visibility exist so other calculations can use them. Offering them would
    be offering the user a choice that means nothing to them."""
    project, _, manipulator = observation_with_a_spacecraft

    response = manipulator.compute(obj=project, method="catalogue", raise_on_error=False)
    catalogue = response.value

    steps = {entry["key"] for entry in catalogue if not entry["offer"]}
    assert steps == {"time_arrays", "telescope_positions", "interpolated_orbits",
                     "source_visibility"}
