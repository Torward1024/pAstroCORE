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

The beam pattern is checked where its physics lives: a result holds one curve per dish, and it
is the plot that gives the curve a frequency.
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
def recomputed():
    """The fixture project and its orchestrator, every result recomputed by the code as it is now."""
    import copy
    import json

    import conftest
    from pastrocore.super.schedule_manipulator import ScheduleManipulator
    from pastrocore.super.schedule_project import ScheduleProject

    project = ScheduleProject.from_dict(copy.deepcopy(json.loads(conftest.FIXTURE.read_text(encoding="utf-8"))))
    observation = project.get_observations()[0]
    # What the fixture holds, recomputed: the same calculations, at the step they were saved at.
    held = ["time_arrays" if key == "times" else key for key in observation.calculated_data.keys()]
    observation.calculated_data.clear()
    core = ScheduleManipulator(project)
    outcome = core.compute(obj=None, method="run", targets=[observation], calculations=held,
                           time_step=300.0, force=True, concurrent=True)
    assert not outcome["failed"], f"could not recompute {outcome['failed']}"
    return core, observation


@pytest.fixture(scope="module")
def computed(recomputed):
    """The recomputed observation."""
    return recomputed[1]


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


@pytest.mark.parametrize("plot_type", ["uv_coverage", "baseline_projections"])
def test_a_baseline_in_earth_diameters_is_the_same_baseline_at_every_frequency(recomputed, plot_type):
    """An Earth diameter is a length, and a projected baseline measured in them is geometry.

    Both plots divided by the wavelength first and then by the Earth's diameter in wavelengths
    *at the lowest frequency drawn*, so the same baseline came out longer at every frequency
    above it -- twice as long at twice the frequency. Ticking a second band drew an array the
    schedule does not have.
    """
    core, observation = recomputed
    frame = stored(observation, "uv_coverage")
    baselines = sorted(frame["baseline"].unique().to_list())
    longest = float(np.nanmax(np.abs(np.concatenate([frame["u"].to_numpy(),
                                                     frame["v"].to_numpy()]))))
    if plot_type == "baseline_projections":
        projections = stored(observation, "baseline_projections")["projection"].to_numpy()
        longest = float(np.nanmax(np.abs(projections)))

    def drawn(frequencies):
        answer = core.visualize(obj=observation, plot_type=plot_type, return_figure=True,
                                show=False, raise_on_error=False, units="earth_diameters",
                                baselines=baselines, source_name="1228+126",
                                scans=[scan.name for scan in observation.get_scans().get_items()],
                                frequencies=frequencies)
        assert answer.ok, answer.error
        # The points themselves, which both plots draw as a scatter: `u` and `v` on one, the
        # baseline's length against time on the other, whose x is a moment rather than a length.
        reached = []
        for axes in answer.value["figure"].get_axes():
            for collection in axes.collections:
                offsets = np.asarray(collection.get_offsets())
                if len(offsets):
                    lengths = np.abs(offsets if plot_type == "uv_coverage" else offsets[:, 1])
                    reached.append(float(lengths.max()))
        assert reached, "the plot drew nothing to measure"
        return max(reached)

    earth = 12742000.0
    one = drawn([1000.0])
    assert one == pytest.approx(longest / earth, rel=1e-6), (
        "what is drawn is not the baseline over the Earth's diameter")
    assert drawn([1000.0, 2000.0]) == pytest.approx(one, rel=1e-6), (
        "the same baseline was drawn at two lengths because two frequencies were ticked")


@pytest.mark.parametrize("megahertz", [1000.0, 22000.0])
def test_the_drawn_beam_is_an_airy_pattern_at_the_chosen_frequency(recomputed, megahertz):
    """Half power at 1.029 lambda/D, first null at 1.2197 lambda/D.

    It was drawn pi times too wide at every frequency: the stored curve keeps `x = D sin(t)`, the
    Airy pattern has `x = pi D sin(theta) / lambda`, and the plot took `theta = t * lambda`.
    """
    core, observation = recomputed
    dishes = stations(observation)
    answer = core.visualize(
        obj=observation, plot_type="beam_pattern", return_figure=True, show=False,
        raise_on_error=False, telescopes=sorted(dishes), frequencies=[megahertz])
    assert answer.ok, answer.error
    wavelength = 299792458.0 / (megahertz * 1e6)

    checked = 0
    for axes in answer.value["figure"].get_axes():
        if not axes.get_visible() or not axes.get_lines():
            continue
        # The station's code is written inside its panel, where a title would sit on the panel above.
        code = axes.texts[0].get_text()
        diameter = dishes[code].diameter
        angle, level = (np.asarray(values, dtype=float) for values in axes.get_lines()[0].get_data())
        outward = angle > 0
        angle, level = angle[outward], level[outward]

        below = np.argmax(level < 0.5)
        half = np.interp(0.5, [level[below], level[below - 1]], [angle[below], angle[below - 1]])
        assert 2 * half == pytest.approx(np.degrees(1.029 * wavelength / diameter), rel=0.005), (
            f"{code} at {megahertz} MHz")

        rising = np.flatnonzero(np.diff(np.sign(np.diff(level))) > 0)
        first_null = angle[rising[0] + 1]
        spacing = float(np.median(np.diff(angle[: rising[0] + 2])))
        assert first_null == pytest.approx(
            np.degrees(np.arcsin(1.2197 * wavelength / diameter)), abs=2 * spacing)
        checked += 1
    assert checked == len(dishes)


def test_an_equatorial_mount_can_see_the_sky_before_transit():
    """An hour angle runs -180 to 180; a telescope is created with limits of 0 to 360.

    Read as a straight interval, every sample before transit fell outside them -- so switching a
    station to an equatorial mount silently cost it the whole approach to transit, and a station
    observing entirely before transit saw nothing at all. Six of thirty-six samples here, and
    nothing said. The limits are an arc on a circle.
    """
    from pastrocore.base.observation import Observation
    from pastrocore.super.schedule_manipulator import ScheduleManipulator
    from pastrocore.super.schedule_project import ScheduleProject

    observation = Observation(code="EQUATORIAL")
    stations = observation.get_telescopes()
    stations.create_telescope(code="Wb", name="WSTRBORK", x=3828445.659, y=445223.6,
                              z=5064921.568, diameter=25.0)
    # Two, because a VLBI scan with one station is not an active scan.
    stations.create_telescope(code="Sv", name="SVETLOE", x=2730173.7626, y=1562442.7288,
                              z=5529969.1054, diameter=32.0)
    dish = stations.get_items()[0]
    dish.set({"mount_type": "EQUA"})                    # and the limits it was created with
    assert dish.get_azimuth_range() == (0.0, 360.0)

    observation.get_sources().create_source(name="S", ra_h=12.0, de_d=40.0)
    observation.get_frequencies().create_if(name="x", frequency=8400.0, bandwidth=16.0)
    observation.get_scans().create_scan(
        name="No0001", start=Time("2026-03-01T00:00:00"), duration=21600.0,
        source=observation.get_sources().get_items()[0], telescopes=stations.get_items(),
        frequencies=observation.get_frequencies().get_items(), observation=observation)
    project = ScheduleProject(name="equatorial")
    project.add_item(observation)
    observation = project.get_observations()[0]

    ScheduleManipulator(project).compute(obj=None, method="run", targets=[observation],
                                         calculations=["source_visibility"], time_step=600.0,
                                         force=True)
    seen = stored(observation, "source_visibility").filter(pl.col("telescope_code") == "Wb")

    # The declination limit is 15 to 90 and the source stands at 40, so nothing here is out of
    # reach: an unlimited hour angle means every sample.
    assert seen.height == 36
    assert seen["visibility"].all(), (
        f"{(~seen['visibility']).sum()} of {seen.height} samples were refused for the hour angle")


def test_a_beam_is_the_dish_and_nothing_else(recomputed):
    """A dish's beam is a function of its diameter. It does not read the sources, and its schema
    says so -- yet with every source switched off the result came back empty, and the log said
    "No active telescopes in observation", which is not what was wrong and not even true.

    The components a calculation asks for and the parts it declares it depends on have to agree,
    or a result is withheld for want of something it never looks at.
    """
    import copy

    core, observation = recomputed
    apart = copy.deepcopy(observation)
    for source in apart.get_sources().get_items():
        source.isactive = False
    apart.clear_calculated_data()

    core.calculate(obj=apart, method="beam_pattern", recalculate=True, raise_on_error=False)
    drawn = apart.get_calculated_data_by_key("beam_pattern").get("data")

    assert drawn is not None and not drawn.is_empty(), (
        "a beam pattern was refused because no source was active")
    assert drawn["telescope_code"].n_unique() == len(apart.get_telescopes().get_active_items())


def test_a_moving_station_is_where_its_velocity_in_metres_per_year_puts_it():
    """Velocities are metres per year -- VEX `site_velocity`, CFX `TLSC_PAR`, the editor -- and
    the position multiplied them by seconds since J2000. Westerbork, Svetloe and Badary from a
    RadioAstron schedule came out 9 500 to 11 000 km from where they are. The fixture's two
    stations do not move, which is why every check above passed regardless.
    """
    from pastrocore.base.observation import Observation
    from pastrocore.super.schedule_manipulator import ScheduleManipulator
    from pastrocore.super.schedule_project import ScheduleProject

    observation = Observation(code="MOVING")
    stations = observation.get_telescopes()
    stations.create_telescope(code="Wb", name="WSTRBORK", x=3828445.659, y=445223.6, z=5064921.568,
                              vx=-0.01353, vy=0.01704, vz=0.00873)
    stations.create_telescope(code="Sv", name="SVETLOE", x=2730173.7626, y=1562442.7288,
                              z=5529969.1054, vx=-0.01817, vy=0.01272, vz=0.00832)
    observation.get_sources().create_source(name="S", ra_h=12.0, de_d=60.0)
    observation.get_frequencies().create_if(name="x", frequency=8400.0, bandwidth=16.0)
    observation.get_scans().create_scan(
        name="No0001", start=Time("2012-11-18T14:00:00"), duration=1200.0,
        source=observation.get_sources().get("S"), telescopes=stations.get_items(),
        frequencies=observation.get_frequencies().get_items(), observation=observation)
    project = ScheduleProject(name="moving")
    project.add_item(observation)
    observation = project.get_observations()[0]

    ScheduleManipulator(project).compute(obj=None, method="run", targets=[observation],
                                         calculations=["telescope_positions"], time_step=300.0,
                                         force=True)
    positions = stored(observation, "telescope_positions")
    j2000 = Time("2000-01-01T12:00:00").mjd

    for telescope in observation.get_telescopes().get_items():
        rows = positions.filter(pl.col("telescope_code") == telescope.get_code())
        years = (rows["time"].to_numpy() - j2000) / 365.25
        moved = (np.asarray(telescope.get_coordinates())[np.newaxis, :]
                 + np.asarray(telescope.get_velocities())[np.newaxis, :] * years[:, np.newaxis])
        when = Time(rows["time"].to_numpy(), format="mjd", scale="utc")
        expected = EarthLocation.from_geocentric(moved[:, 0], moved[:, 1], moved[:, 2],
                                                 unit=u.m).get_gcrs(obstime=when).cartesian
        ours = rows.select(["x", "y", "z"]).to_numpy()
        worst = np.max(np.linalg.norm(ours - expected.xyz.to_value(u.m).T, axis=1))
        assert worst < 0.01, f"{telescope.get_code()} is {worst:,.2f} m from where it is"


# --- a spacecraft placed by its orbital elements ----------------------------------------------------

def _kepler_position(a, e, i, raan, argp, nu0, mu, seconds):
    """Where an orbit puts a body, written out here rather than read back from the code.

    The true anomaly at the epoch is converted to an eccentric and then to a mean anomaly, which
    is the one that advances linearly in time; it is carried forward, solved back, and turned
    into the radius and the direction the geometry gives.
    """
    i, raan, argp, nu0 = np.radians([i, raan, argp, nu0])
    eccentric = 2.0 * np.arctan2(np.sqrt(1 - e) * np.sin(nu0 / 2), np.sqrt(1 + e) * np.cos(nu0 / 2))
    mean = eccentric - e * np.sin(eccentric) + np.sqrt(mu / a ** 3) * np.asarray(seconds, dtype=float)

    anomaly = mean.copy()
    for _ in range(200):                       # Newton, to well below a millimetre of arc
        anomaly = anomaly - (anomaly - e * np.sin(anomaly) - mean) / (1 - e * np.cos(anomaly))
    nu = 2.0 * np.arctan2(np.sqrt(1 + e) * np.sin(anomaly / 2), np.sqrt(1 - e) * np.cos(anomaly / 2))
    radius = a * (1 - e ** 2) / (1 + e * np.cos(nu))

    in_plane = np.stack([radius * np.cos(nu), radius * np.sin(nu), np.zeros_like(radius)], axis=-1)
    rotation = (np.array([[np.cos(raan), -np.sin(raan), 0], [np.sin(raan), np.cos(raan), 0], [0, 0, 1]])
                @ np.array([[1, 0, 0], [0, np.cos(i), -np.sin(i)], [0, np.sin(i), np.cos(i)]])
                @ np.array([[np.cos(argp), -np.sin(argp), 0], [np.sin(argp), np.cos(argp), 0], [0, 0, 1]]))
    return in_plane @ rotation.T


@pytest.mark.parametrize("e", [0.0, 0.3, 0.6, 0.94])
def test_a_spacecraft_stands_where_its_own_elements_say(e):
    """The editor asks for a **true** anomaly and the propagation took it for a mean one.

    They are the same number only on a circle. At e = 0.6 and nu = 90 degrees the spacecraft was
    placed 32 960 km from where its own elements put it, at twice the radius the orbit allows --
    at the epoch itself, before any time had passed. The one Keplerian test in the suite used
    e = 0.01, where the two anomalies agree to a degree, so everything was green.
    """
    from astropy.time import TimeDelta

    from pastrocore.base.telescopes import SpaceTelescope
    from pastrocore.super.schedule_calculator import ScheduleCalculator
    from pastrocore.super.schedule_manipulator import ScheduleManipulator
    from pastrocore.super.schedule_project import ScheduleProject

    a, mu, nu0 = 3.0e7, 398600.4418e9, 90.0
    epoch = Time("2026-01-01T00:00:00")
    telescope = SpaceTelescope(code="RA", name="RADIOASTRON", use_kep=True, kepler_elements={
        "a": a, "e": e, "i": 63.4, "raan": 30.0, "argp": 270.0, "nu": nu0,
        "epoch": epoch, "mu": mu})

    period = 2 * np.pi * np.sqrt(a ** 3 / mu)
    seconds = np.array([0.0, period / 8, period / 4, period / 2, period])
    times = (epoch + TimeDelta(seconds, format="sec")).mjd

    calculator = ScheduleCalculator(ScheduleManipulator(ScheduleProject(name="orbit")))
    ours = calculator._compute_telescope_position(telescope, times)
    theirs = _kepler_position(a, e, 63.4, 30.0, 270.0, nu0, mu, seconds)

    worst = np.max(np.linalg.norm(ours - theirs, axis=1))
    assert worst < 1.0, f"e={e}: {worst / 1e3:,.1f} km from where the elements put it"

    # And the radius at the epoch is the one the conic gives for that true anomaly, which is a
    # statement about the elements alone -- no propagation, nothing to get subtly right.
    assert np.linalg.norm(ours[0]) == pytest.approx(
        a * (1 - e ** 2) / (1 + e * np.cos(np.radians(nu0))), rel=1e-9)


# --- sensitivity (E1) ---------------------------------------------------------------------------------
#
# Each of these states the formula a second way: through astropy's constants and units, through a
# textbook identity, or through what the formula is claimed to preserve. None of them reads the
# code's own arithmetic back.

def test_an_sefd_is_twice_boltzmann_times_tsys_over_the_effective_area_in_janskys():
    """Checked through astropy's constants and units, so a lost factor of 1e26 cannot hide -- which
    is exactly what the old `calculate_sefd` did, giving 1.8e-25 for a dish of 18 Jy."""
    from astropy import constants

    from pastrocore.base.telescope import Telescope

    dish = Telescope(code="EF", name="Effelsberg", diameter=100.0,
                     system_temperature_table=[(4500.0, 5100.0, 25.0)],
                     surface_efficiency_table=[(4500.0, 5100.0, 0.55)])
    estimate = dish.get_sefd_estimate(4840.0)

    area = 0.55 * np.pi * 50.0 ** 2 * u.m ** 2
    expected = (2 * constants.k_B * 25.0 * u.K / area).to(u.Jy).value
    assert estimate["origin"] == "parameters"
    assert estimate["sefd"] == pytest.approx(expected, rel=1e-12)


def test_an_sefd_is_the_system_temperature_over_the_gain_of_one_kelvin_per_2760_square_metres():
    """The radio astronomer's identity: a gain of 1 K/Jy takes 2761 m^2 of effective area, so
    SEFD = Tsys * 2761 / A_eff. Written from the identity, not from the code's constants."""
    from pastrocore.base.telescope import Telescope

    dish = Telescope(code="G", name="G", diameter=32.0,
                     system_temperature_table=[(8000.0, 9000.0, 40.0)],
                     effective_area_table=[(8000.0, 9000.0, 450.0)])

    square_metres_per_kelvin_per_jansky = 2761.3  # 2 k / (1 Jy): the area that gives 1 K/Jy
    assert dish.get_sefd_estimate(8400.0)["sefd"] == pytest.approx(
        40.0 * square_metres_per_kelvin_per_jansky / 450.0, rel=1e-4)


def test_ruze_loses_one_e_fold_when_the_surface_error_is_a_wavelength_over_four_pi():
    from pastrocore.base.telescope import Telescope

    frequency = 22000.0
    wavelength = 299792458.0 / (frequency * 1e6)
    dish = Telescope(code="R", name="R", diameter=22.0,
                     surface_accuracy=wavelength / (4 * np.pi) * 1e6)

    assert dish.get_ruze_efficiency(frequency) == pytest.approx(np.exp(-1.0), rel=1e-12)


def test_an_efficiency_carried_by_ruze_keeps_what_the_surface_does_not_lose():
    """`eta = eta0 * ruze(nu)`: what is not the surface's -- illumination, spillover, blockage --
    is the same at every frequency, so eta / ruze is the same at the measurement and at the band."""
    from pastrocore.base.telescope import Telescope

    dish = Telescope(code="C", name="C", diameter=64.0, surface_accuracy=400.0,
                     surface_efficiency_table=[(1400.0, 1700.0, 0.62)])
    measured_at = np.sqrt(1400.0 * 1700.0)

    carried = dish.get_aperture_efficiency(22235.0)

    assert carried["value"] / dish.get_ruze_efficiency(22235.0) == pytest.approx(
        0.62 / dish.get_ruze_efficiency(measured_at), rel=1e-12)
    assert "carried by Ruze" in carried["basis"]


def test_a_flux_between_measurements_is_on_the_straight_line_in_log_log():
    from pastrocore.base.sources import Source

    source = Source(name="S", flux_table={610.0: 4.2, 1400.0: 2.9, 5000.0: 1.4})

    for frequency in (800.0, 1100.0, 2300.0, 4200.0):
        below, above = (610.0, 1400.0) if frequency < 1400.0 else (1400.0, 5000.0)
        flux_below, flux_above = source.flux_table[below], source.flux_table[above]
        fraction = np.log(frequency / below) / np.log(above / below)
        on_the_line = np.exp(np.log(flux_below) + fraction * np.log(flux_above / flux_below))
        assert source.get_flux(frequency) == pytest.approx(on_the_line, rel=1e-12)


def test_beyond_the_measurements_a_spectral_index_scales_from_the_nearest_one():
    from pastrocore.base.sources import Source

    source = Source(name="S", flux_table={1400.0: 2.0, 5000.0: 1.0}, spectral_index=-0.7)

    assert source.get_flux(22000.0) == pytest.approx(1.0 * (22000.0 / 5000.0) ** -0.7, rel=1e-12)
    assert source.get_flux(330.0) == pytest.approx(2.0 * (330.0 / 1400.0) ** -0.7, rel=1e-12)
    assert Source(name="T", flux_table={1400.0: 2.0}).get_flux(5000.0) is None, (
        "without an index the flux beyond the measurements is not guessed")
