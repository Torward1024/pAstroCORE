"""Interpolating a space telescope's orbit, against an orbit whose answer is known.

The Chebyshev method was wrong by kilometres and nothing said so: it produced numbers, the
numbers were plotted, and only comparing `linear` against an independent tool showed that the
two disagreed. A characterization test cannot catch this -- it compares against what the code
used to produce, which was the wrong answer.

So the fixture here is a Kepler orbit, solved to machine precision. Every method is measured
against the position the telescope was actually at.
"""
import numpy as np
import pytest

from pastrocore.super.schedule_calculator import ScheduleCalculator
from pastrocore.super.schedule_manipulator import ScheduleManipulator

MU = 3.986004418e14                     # m^3/s^2
PERIGEE = 10_000e3
APOGEE = 350_000e3


def kepler_orbit(times):
    """Return positions on a Molniya-like orbit: eccentricity 0.94, period about 8.8 days.

    Fast through perigee and slow at apogee, which is the shape a single polynomial cannot
    describe and the reason RadioAstron-style orbits are the hard case.
    """
    semi_major = (PERIGEE + APOGEE) / 2.0
    eccentricity = (APOGEE - PERIGEE) / (APOGEE + PERIGEE)
    period = 2 * np.pi * np.sqrt(semi_major ** 3 / MU)

    mean = 2 * np.pi * np.asarray(times) / period
    E = mean.copy()
    for _ in range(90):                 # Newton on Kepler's equation
        E = E - (E - eccentricity * np.sin(E) - mean) / (1 - eccentricity * np.cos(E))

    x = semi_major * (np.cos(E) - eccentricity)
    y = semi_major * np.sqrt(1 - eccentricity ** 2) * np.sin(E)
    return np.stack([x, y, 0.2 * y], axis=-1), period


@pytest.fixture(scope="module")
def calculator():
    return ScheduleCalculator(ScheduleManipulator())


@pytest.fixture(scope="module")
def orbit():
    """An orbit file's worth of samples: one full period, every 600 seconds."""
    _, period = kepler_orbit(np.array([0.0]))
    times = np.arange(0.0, period, 600.0)
    positions, _ = kepler_orbit(times)
    return times, positions, period


def error_of(calculator, orbit, wanted):
    times, positions, _ = orbit
    truth, _ = kepler_orbit(wanted)
    got = calculator._chebyshev_positions(times, positions, wanted)
    return np.linalg.norm(got - truth, axis=1)


@pytest.mark.parametrize("where,offset,step,length", [
    ("apogee", 4 * 86400.0, 10.0, 3600.0),
    ("perigee", 0.0, 10.0, 3600.0),
    ("half a day", 2 * 86400.0, 60.0, 12 * 3600.0),
])
def test_a_scan_is_interpolated_to_within_a_few_kilometres(calculator, orbit, where, offset,
                                                           step, length):
    """Named per case so a failure says which part of the orbit broke.

    Perigee is the loose one at 5 km, and that belongs to the sampling rather than the method:
    600-second samples do not record the turn. Linear interpolation of the same samples is out
    by 172 km there.
    """
    wanted = np.arange(offset, offset + length, step)
    assert error_of(calculator, orbit, wanted).max() < 5_000.0


def test_the_whole_orbit_is_interpolated_without_the_error_it_used_to_have(calculator, orbit):
    """The case that was worst: times spread over the whole period and deliberately off the
    sample grid, so nothing is right by coincidence.

    One polynomial of degree 30 over the whole file gave 846 km at worst and 44.7 km on average.
    """
    times, _, period = orbit
    wanted = np.arange(137.0, period - 700.0, 137.0)
    error = error_of(calculator, orbit, wanted)

    assert error.mean() < 1_000.0, f"mean error {error.mean() / 1000:.3f} km"
    assert error.max() < 25_000.0, f"worst error {error.max() / 1000:.3f} km"


def test_chebyshev_beats_linear_on_the_orbit_it_is_offered_for(calculator, orbit):
    """The point of offering the method at all. It was *worse* than linear by two orders of
    magnitude, which is what sent a user to compare against an independent tool."""
    times, positions, _ = orbit
    wanted = np.arange(4 * 86400.0, 4 * 86400.0 + 3600.0, 10.0)
    truth, _ = kepler_orbit(wanted)

    chebyshev = np.linalg.norm(
        calculator._chebyshev_positions(times, positions, wanted) - truth, axis=1)
    linear = np.linalg.norm(
        np.array([np.interp(wanted, times, axis) for axis in positions.T]).T - truth, axis=1)

    assert chebyshev.mean() < linear.mean()


def test_every_requested_time_gets_a_position(calculator, orbit):
    """Arcs are cut along the samples and joined; a time falling on a join, or on the very last
    sample, must not come back NaN."""
    times, positions, _ = orbit
    wanted = np.concatenate([times[::7], times[:1], times[-1:]])
    wanted.sort()

    got = calculator._chebyshev_positions(times, positions, wanted)

    assert not np.isnan(got).any(), f"{int(np.isnan(got).any(axis=1).sum())} times came back NaN"


def test_a_single_requested_time_is_not_a_special_case(calculator, orbit):
    """A one-sample arc has no span to normalise by, which is a division by zero if unguarded."""
    times, positions, _ = orbit
    wanted = np.array([3 * 86400.0 + 12.5])

    got = calculator._chebyshev_positions(times, positions, wanted)
    truth, _ = kepler_orbit(wanted)

    assert not np.isnan(got).any()
    assert np.linalg.norm(got - truth, axis=1).max() < 5_000.0


def test_too_few_samples_to_fill_a_degree_still_answers(calculator):
    """An orbit file with a handful of points must not be refused, or fitted with a degree it
    cannot support."""
    times = np.arange(0.0, 5 * 600.0, 600.0)
    positions, _ = kepler_orbit(times)
    wanted = np.arange(100.0, 2000.0, 100.0)

    got = calculator._chebyshev_positions(times, positions, wanted)

    assert got.shape == (len(wanted), 3)
    assert not np.isnan(got).any()
