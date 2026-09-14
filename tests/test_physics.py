"""The numbers are right, not merely unchanged.

`test_characterization` holds a recomputation to what the fixture project was saved holding. It
cannot say whether what was saved is correct, and once it could not: a telescope position was
846 km off in a suite that was entirely green. So each result here is derived a second way --
from astropy directly, or from the geometry the result claims to be -- and the two must agree.

What is compared is a fresh recomputation of the fixture, done once for the module, so it is the
code that is checked rather than a file it once wrote. Between this and characterization a
formula has to be both unchanged and right.

Tolerances are measured, and stated with the reason they are not zero:

- Topocentric directions agree with astropy to about 5e-6 degrees; allowed 1e-4.
- The Sun angle is taken between directions rather than through AltAz, which leaves out diurnal
  aberration -- 0.21" measured; allowed 1".
- uvw, baseline projections and Mollweide tracks are geometry of the saved positions, exact to
  rounding, so they are held to a millimetre and a microdegree.

The beam pattern is not here, because it is not right: see `test_the_beam_pattern_is_not_yet_physical`.
"""
import warnings

import numpy as np
import polars as pl
import pytest

import astropy.units as u
from astropy.coordinates import AltAz, EarthLocation, HADec, SkyCoord, get_body
from astropy.time import Time

warnings.filterwarnings("ignore", module="erfa")


@pytest.fixture(scope="module")
def computed():
    """The fixture project's observation, every result recomputed by the code as it is now."""
    import copy
    import json

    import conftest
    from pastrocore.super.schedule_manipulator import ScheduleManipulator
    from pastrocore.super.schedule_project import ScheduleProject

    project = ScheduleProject.from_dict(copy.deepcopy(json.loads(conftest.FIXTURE.read_text(encoding="utf-8"))))
    observation = project.observations()[0]
    # What the fixture holds, recomputed: the same calculations, at the step they were saved at.
    held = ["time_arrays" if key == "times" else key for key in observation.calculated_data.keys()]
    observation.calculated_data.clear()
    core = ScheduleManipulator(project)
    outcome = core.compute(obj=None, method="run", targets=[observation], calculations=held,
                           time_step=300.0, force=True, concurrent=True)
    assert not outcome["failed"], f"could not recompute {outcome['failed']}"
    return observation


def stored(observation, key):
    return observation.get_calculated_data_by_key(key)["data"]


def source_of(observation):
    source = observation.get_sources().get_items()[0]
    return SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame="icrs")


def stations(observation):
    return {telescope.get_code(): telescope for telescope in observation.get_telescopes().get_items()}


def location(telescope):
    return EarthLocation.from_geocentric(*telescope.get_coordinates(), unit=u.m)


def per_station(frame, column):
    """Each station's rows, in time order, with the column's NaNs left out."""
    for (code,), part in frame.filter(pl.col(column).is_not_nan()).group_by("telescope_code"):
        part = part.sort("time")
        yield code, part, Time(part["time"].to_numpy(), format="mjd", scale="utc")


def wrapped(difference, period=360.0):
    return (np.asarray(difference) + period / 2) % period - period / 2


def test_azimuth_and_elevation_are_what_astropy_says(computed):
    observation = computed
    source, by_code = source_of(observation), stations(observation)
    checked = 0
    for code, part, times in per_station(stored(observation, "az_el"), "el"):
        expected = source.transform_to(AltAz(obstime=times, location=location(by_code[code])))
        assert np.max(np.abs(wrapped(part["az"].to_numpy() - expected.az.deg))) < 1e-4, code
        assert np.max(np.abs(part["el"].to_numpy() - expected.alt.deg)) < 1e-4, code
        checked += part.height
    assert checked > 0, "nothing was visible, so nothing was checked"


def test_the_parallactic_angle_is_the_textbook_one(computed):
    """q = atan2(sin H, tan(phi) cos(dec) - sin(dec) cos H), from astropy's own hour angle."""
    observation = computed
    source, by_code = source_of(observation), stations(observation)
    for code, part, times in per_station(stored(observation, "parallactic_angle"), "parallactic_angle"):
        place = location(by_code[code])
        apparent = source.transform_to(HADec(obstime=times, location=place))
        hour, dec, latitude = apparent.ha.rad, apparent.dec.rad, place.lat.rad
        expected = np.degrees(np.arctan2(np.sin(hour), np.tan(latitude) * np.cos(dec)
                                         - np.sin(dec) * np.cos(hour)))
        assert np.max(np.abs(wrapped(part["parallactic_angle"].to_numpy() - expected))) < 1e-4, code


def test_the_sun_angle_is_the_one_seen_from_the_station(computed):
    observation = computed
    source, by_code = source_of(observation), stations(observation)
    for code, part, times in per_station(stored(observation, "sun_angles"), "angle"):
        sun = get_body("sun", times, location(by_code[code]))
        expected = sun.separation(source.transform_to(sun.frame)).deg
        worst = np.max(np.abs(part["angle"].to_numpy() - expected)) * 3600
        assert worst < 1.0, f"{code}: {worst:.3f} arcsec from astropy"


def test_a_source_is_visible_exactly_when_it_is_inside_the_mount_limits(computed):
    observation = computed
    source, by_code = source_of(observation), stations(observation)
    visibility = stored(observation, "source_visibility")
    for (code,), part in visibility.group_by("telescope_code"):
        telescope = by_code[code]
        times = Time(part["time"].to_numpy(), format="mjd", scale="utc")
        sky = source.transform_to(AltAz(obstime=times, location=location(telescope)))
        low, high = telescope.get_elevation_range()
        first, last = telescope.get_azimuth_range()
        expected = ((sky.alt.deg >= low) & (sky.alt.deg <= high)
                    & (sky.az.deg >= first) & (sky.az.deg <= last))
        assert np.array_equal(part["visibility"].to_numpy(), expected), code


def baseline_vectors(observation, frame):
    """The GCRS baseline, first station minus second, at each row's time."""
    positions = stored(observation, "telescope_positions")
    first, second = frame["baseline"][0].split("-")
    joined = (frame
              .join(positions.filter(pl.col("telescope_code") == first)
                    .select(["time", "x", "y", "z"]), on="time")
              .join(positions.filter(pl.col("telescope_code") == second)
                    .select(["time", "x", "y", "z"]), on="time", suffix="_second"))
    vectors = (joined.select(["x", "y", "z"]).to_numpy()
               - joined.select(["x_second", "y_second", "z_second"]).to_numpy())
    return joined, vectors


def j2000_basis(observation):
    cartesian = source_of(observation).cartesian
    towards = np.array([cartesian.x.value, cartesian.y.value, cartesian.z.value])
    towards /= np.linalg.norm(towards)
    east = np.cross([0.0, 0.0, 1.0], towards)
    east /= np.linalg.norm(east)
    return east, np.cross(towards, east), towards


def test_uvw_is_the_baseline_in_the_source_frame(computed):
    """u east, v north, w towards the source, in J2000 -- the frame a correlator uses -- for
    the baseline first station minus second."""
    observation = computed
    joined, vectors = baseline_vectors(observation, stored(observation, "uv_coverage"))
    east, north, towards = j2000_basis(observation)
    assert joined.height > 0
    for column, axis in (("u", east), ("v", north), ("w", towards)):
        assert np.max(np.abs(joined[column].to_numpy() - vectors @ axis)) < 1e-3, column


def test_a_baseline_projection_is_its_length_across_the_line_of_sight(computed):
    observation = computed
    frame = stored(observation, "baseline_projections").filter(pl.col("projection").is_not_nan())
    joined, vectors = baseline_vectors(observation, frame)
    _, _, towards = j2000_basis(observation)
    across = np.linalg.norm(vectors - (vectors @ towards)[:, np.newaxis] * towards, axis=1)
    assert joined.height > 0
    assert np.max(np.abs(joined["projection"].to_numpy() - across)) < 1e-3


def test_a_mollweide_track_is_where_the_station_points_from_the_geocentre(computed):
    observation = computed
    tracks = stored(observation, "mollweide_tracks")
    positions = stored(observation, "telescope_positions")
    joined = tracks.join(positions, on=["time", "telescope_code", "scan_name"])
    xyz = joined.select(["x", "y", "z"]).to_numpy()
    right_ascension = np.degrees(np.arctan2(xyz[:, 1], xyz[:, 0]))
    declination = np.degrees(np.arcsin(xyz[:, 2] / np.linalg.norm(xyz, axis=1)))
    assert joined.height == tracks.height
    assert np.max(np.abs(wrapped(joined["lon"].to_numpy() - right_ascension))) < 1e-6
    assert np.max(np.abs(joined["lat"].to_numpy() - declination)) < 1e-6


def test_time_on_source_is_the_visible_samples_times_the_spacing(computed):
    """A sample stands for the spacing that follows it, so k visible samples are k spacings."""
    observation = computed
    visibility = stored(observation, "source_visibility")
    on_source = stored(observation, "time_on_source")
    spacing = float(np.median(np.diff(np.unique(visibility["time"].to_numpy())))) * 86400.0
    for (code,), part in on_source.group_by("telescope_code"):
        seen = visibility.filter(pl.col("telescope_code") == code)["visibility"].sum()
        assert part["duration"].sum() == pytest.approx(seen * spacing, abs=1e-3), code


def test_the_beam_pattern_is_not_yet_physical(computed):
    """Recorded rather than asserted correct.

    The pattern is `(2 J1(x) / x)^2` with `x = D sin(theta)`, where the Airy pattern has
    `x = pi D sin(theta) / lambda`. That is the pattern at a wavelength of pi metres -- 95 MHz --
    whatever band the observation uses: a 70 m dish at 1 GHz is drawn with a half-power width of
    2.7 degrees where it has 0.25. This fails the day that is corrected, so the correction also
    has to replace it with a real check.
    """
    observation = computed
    pattern = stored(observation, "beam_pattern")
    dish = max(stations(observation).values(), key=lambda telescope: telescope.diameter)
    part = pattern.filter((pl.col("telescope_code") == dish.get_code()) & (pl.col("theta") > 0)).sort("theta")
    half_power = part.filter(pl.col("pattern") < 0.5)["theta"][0]
    at_pi_metres = np.arcsin(1.6163 / dish.diameter)
    one_sample = float(np.median(np.diff(part["theta"].to_numpy())))
    assert half_power == pytest.approx(at_pi_metres, abs=one_sample)
