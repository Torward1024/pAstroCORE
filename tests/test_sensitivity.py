"""Sensitivity and detection (E1): each station's SEFD, each baseline's noise, and whether it detects.

The numbers are checked against the equations written out here, not read back from the code, and
against a published case: the VLBA Observational Status Summary's table 5.1, which gives the
baseline sensitivity of identical antennas, `SEFD / (eta_s sqrt(2 dnu tau))`, with eta_s = 0.8,
128 MHz and one minute.
"""
import copy
import json
import pathlib

import numpy as np
import polars as pl
import pytest

import conftest
from pastrocore.base.sources import Source
from pastrocore.super.schedule_calculator import ScheduleCalculator
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject


@pytest.fixture
def observed():
    """The fixture project with the two stations' system temperatures and efficiencies set, and a
    flux for its source, at the band it observes (1000 MHz, 16 MHz wide)."""
    project = ScheduleProject.from_dict(copy.deepcopy(json.loads(conftest.FIXTURE.read_text(encoding="utf-8"))))
    observation = project.get_observations()[0]
    for telescope in observation.get_telescopes().get_items():
        telescope.set({"system_temperature_table": [(900.0, 1100.0, 40.0)],
                       "surface_efficiency_table": [(900.0, 1100.0, 0.6)]})
    observation.get_sources().get_items()[0].set({"flux_table": {1000.0: 1.5}})
    return project, observation, ScheduleManipulator(project)


def run(core, observation, *calculations, **asked):
    asked.setdefault("force", True)
    asked.setdefault("time_step", 600.0)
    outcome = core.compute(obj=None, method="run", targets=[observation],
                           calculations=list(calculations), **asked)
    assert not outcome["failed"], outcome["failed"]


def frame(observation, key):
    return observation.get_calculated_data_by_key(key)["data"]


# --- the published case --------------------------------------------------------------------------------

@pytest.mark.parametrize("band,sefd,published", [
    ("6 cm", 210.0, 2.1), ("4 cm", 327.0, 3.3), ("2 cm", 543.0, 5.5), ("1 cm", 640.0, 6.5)])
def test_a_baseline_of_identical_antennas_is_as_sensitive_as_the_vlba_says(band, sefd, published):
    """VLBA OSS table 5.1, column 7: 128 MHz, one minute, eta_s = 0.8, in mJy to one decimal."""
    class Band:
        name, frequency, bandwidth, polarizations = band, 5000.0, 128.0, []

    source = Source(name="S", flux_table={5000.0: 1.0})
    sefds = {"sefd_1": sefd, "sefd_2": sefd, "sefd": sefd, "reason": None}
    common = {"time": 0.0, "scan_name": "s", "source_name": "S", "baseline": "A-B",
              "scan_duration": 60.0, "duration": 60.0}

    row = ScheduleCalculator._band_sensitivity(common, Band, source, sefds, 0.8, 5.0)

    assert row["noise"] * 1e3 == pytest.approx(published, abs=0.05)


# --- the equations ----------------------------------------------------------------------------------

def test_a_baseline_s_noise_is_the_radiometer_equation_over_the_time_both_stations_see_the_source(observed):
    project, observation, core = observed
    run(core, observation, "baseline_sensitivity")

    sefds = {row["telescope_code"]: row["sefd"] for row in frame(observation, "sefd").iter_rows(named=True)}
    blocks = frame(observation, "time_on_source")
    band = frame(observation, "baseline_sensitivity").filter(pl.col("if_name") != "all").row(0, named=True)

    first, second = band["baseline"].split("-")
    spans = {code: [(r["start"], r["end"]) for r in blocks.filter(pl.col("telescope_code") == code).iter_rows(named=True)]
             for code in (first, second)}
    together = sum(max(0.0, min(b1, b2) - max(a1, a2))
                   for a1, b1 in spans[first] for a2, b2 in spans[second]) * 86400.0
    expected = np.sqrt(sefds[first] * sefds[second]) / (0.8825 * np.sqrt(2 * 16e6 * together))

    assert band["duration"] == pytest.approx(together)
    assert band["noise"] == pytest.approx(expected, rel=1e-12)
    assert band["snr"] == pytest.approx(1.5 / expected, rel=1e-12)


def test_the_shortest_scan_is_the_one_that_reaches_the_threshold_exactly(observed):
    project, observation, core = observed
    run(core, observation, "baseline_sensitivity", threshold=7.0)

    for row in frame(observation, "baseline_sensitivity").iter_rows(named=True):
        if row["if_name"] == "all":
            continue
        noise_then = row["noise_1s"] / np.sqrt(row["min_duration"])
        assert row["flux"] / noise_then == pytest.approx(7.0, rel=1e-12)


def test_the_bands_together_add_signal_to_noise_in_quadrature(observed):
    project, observation, core = observed
    # A flux at both bands: with it only at the first, the second is left out of the sum and adding
    # in quadrature cannot be told from adding -- which is how this first passed a broken sum.
    observation.get_sources().get_items()[0].set({"flux_table": {1000.0: 1.5, 1100.0: 1.3}})
    observation.get_frequencies().create_if(name="second", frequency=1050.0, bandwidth=32.0)
    second = observation.get_frequencies().get("second")
    for scan in observation.get_scans().get_items():
        scan.set({"frequencies": list(scan.frequencies) + [second]})
    run(core, observation, "baseline_sensitivity")

    rows = frame(observation, "baseline_sensitivity")
    bands = rows.filter(pl.col("if_name") != "all")
    together = rows.filter(pl.col("if_name") == "all").row(0, named=True)

    assert bands.height == 2 and bands["snr"].null_count() == 0, "both bands must count"
    assert together["snr"] == pytest.approx(np.sqrt((bands["snr"] ** 2).sum()), rel=1e-12)
    per_second = ((bands["flux"] / bands["noise_1s"]) ** 2).sum()
    assert together["min_duration"] == pytest.approx(25.0 / per_second, rel=1e-12)


def test_one_bit_keeps_two_over_pi_of_the_signal_and_two_bits_more(observed):
    project, observation, core = observed
    run(core, observation, "baseline_sensitivity", bits=2)
    two = frame(observation, "baseline_sensitivity").filter(pl.col("if_name") != "all")["snr"][0]
    run(core, observation, "baseline_sensitivity", bits=1)
    one = frame(observation, "baseline_sensitivity").filter(pl.col("if_name") != "all")["snr"][0]

    assert one / two == pytest.approx((2 / np.pi) / 0.8825, rel=1e-12)
    assert observation.get_calculated_data_by_key("baseline_sensitivity")["metadata"]["bits"] == 1


# --- the elevation ------------------------------------------------------------------------------------

def test_the_sefd_away_from_the_zenith_is_dimmed_by_more_air_and_warmed_by_it(observed):
    """`SEFD(el) = SEFD_zenith e^(tau0 (A - 1)) Tsys(el) / Tsys_zenith`, A = 1/sin(el)."""
    project, observation, core = observed
    run(core, observation, "sefd_track", opacity=[[900.0, 1100.0, 0.08]], t_atm=270.0)

    track = frame(observation, "sefd_track").filter(pl.col("sefd").is_not_null())

    assert track.height > 0, "nothing was above the horizon"
    for row in track.iter_rows(named=True):
        airmass = 1.0 / np.sin(np.radians(row["elevation"]))
        tsys = 40.0 + 270.0 * (np.exp(-0.08) - np.exp(-0.08 * airmass))
        assert row["airmass"] == pytest.approx(airmass, rel=1e-12)
        assert row["tsys"] == pytest.approx(tsys, rel=1e-12)
        assert row["sefd"] == pytest.approx(
            row["sefd_zenith"] * np.exp(0.08 * (airmass - 1.0)) * tsys / 40.0, rel=1e-12)
    assert (track["sefd"] > track["sefd_zenith"]).all(), "below the zenith a station is worse"


def test_a_schedule_that_starts_well_and_goes_wrong_later_is_still_a_result(observed):
    """A column whose first rows are empty and whose later ones are not was the broken case.

    polars reads the type of a numpy array of objects from what it starts with: a reason column
    beginning with None and holding strings further down is an `Object` column, and casting one to
    a string raises `cannot cast 'Object' type` -- logged, swallowed by the handler, and the whole
    calculation came back empty. The fixture's day-long scan starts below the horizon, so its very
    first row carries a reason and nothing ever noticed.
    """
    project, observation, core = observed
    # The first scan is one the stations can observe throughout; a later one is not.
    a_schedule_of(observation)
    run(core, observation, "sefd_track", time_step=300.0)

    followed = frame(observation, "sefd_track").sort(["time", "telescope_code"])

    assert followed.height, "the whole calculation came back empty"
    assert followed["reason"][0] is None, "this needs a result that begins without a reason"
    assert 0 < followed["reason"].null_count() < followed.height, "and carries one later"


def test_there_is_no_sefd_at_an_elevation_the_dish_does_not_point_at(observed):
    """A flat atmosphere's airmass runs away at the horizon: 1/sin(0.5 deg) is 115, and the SEFD
    it gives is tens of millions of janskys at an elevation the station never observes at."""
    project, observation, core = observed
    station = observation.get_telescopes().get_items()[0]
    station.set({"elevation_range": (30.0, 90.0)})
    run(core, observation, "sefd_track", opacity=[[900.0, 1100.0, 0.08]], t_atm=270.0)

    followed = frame(observation, "sefd_track").filter(pl.col("telescope_code") == station.get_code())
    worked_out = followed.filter(pl.col("sefd").is_not_null())
    refused = followed.filter(pl.col("sefd").is_null() & (pl.col("elevation") > 0)
                              & (pl.col("elevation") < 30.0))

    assert worked_out.height and worked_out["elevation"].min() >= 30.0
    assert refused.height, "the fixture has to hold a sample below the limit for this to say anything"
    assert "outside what" in refused["reason"][0] and "30-90 deg" in refused["reason"][0]


def test_a_gain_curve_is_a_ratio_to_the_zenith_so_its_normalisation_does_not_matter(observed):
    project, observation, core = observed
    code = observation.get_telescopes().get_items()[0].get_code()
    coefficients = [0.9, 0.004, -0.00003]

    def followed(curve):
        run(core, observation, "sefd_track", gain_curve={code: [[900.0, 1100.0, curve]]})
        return frame(observation, "sefd_track").filter(
            (pl.col("telescope_code") == code) & pl.col("sefd").is_not_null())

    once = followed(coefficients)
    twice = followed([2.0 * c for c in coefficients])

    row = once.row(0, named=True)
    polynomial = np.polynomial.polynomial.polyval
    gain = polynomial(row["elevation"], coefficients) / polynomial(90.0, coefficients)
    assert gain != pytest.approx(1.0), "a curve that does nothing proves nothing"
    assert row["gain"] == pytest.approx(gain, rel=1e-12)
    assert row["sefd"] == pytest.approx(row["sefd_zenith"] / gain, rel=1e-12)
    assert twice["sefd"].to_list() == pytest.approx(once["sefd"].to_list(), rel=1e-12)


def test_a_baseline_adds_up_the_noise_over_the_sefds_it_had_through_the_scan(observed):
    """`1/sigma^2 = eta^2 2 dnu sum(dt / (SEFD1 SEFD2))`, so the noise is `1/(eta sqrt(2 dnu sum))`."""
    project, observation, core = observed
    run(core, observation, "baseline_sensitivity", opacity=[[900.0, 1100.0, 0.08]], t_atm=270.0)

    band = frame(observation, "baseline_sensitivity").filter(pl.col("if_name") != "all").row(0, named=True)
    first, second = band["baseline"].split("-")
    track = frame(observation, "sefd_track").filter(pl.col("scan_name") == band["scan_name"])
    blocks = frame(observation, "time_on_source").filter(pl.col("scan_name") == band["scan_name"])
    spans = {code: [(r["start"], r["end"]) for r
                    in blocks.filter(pl.col("telescope_code") == code).iter_rows(named=True)]
             for code in (first, second)}
    sefd_at = {(r["telescope_code"], r["time"]): r["sefd"] for r in track.iter_rows(named=True)}
    times = sorted({r["time"] for r in track.iter_rows(named=True)})
    spacing = times[1] - times[0]

    def on_source(code, start, end):
        return sum(max(0.0, min(stop, end) - max(begins, start)) for begins, stop in spans[code])

    together, inverse = 0.0, 0.0
    for start in times:
        seconds = min(on_source(first, start, start + spacing),
                      on_source(second, start, start + spacing)) * 86400.0
        if seconds <= 0:
            continue
        together += seconds
        inverse += seconds / (sefd_at[(first, start)] * sefd_at[(second, start)])

    assert band["duration"] == pytest.approx(together)
    assert band["noise"] == pytest.approx(1.0 / (0.8825 * np.sqrt(2 * 16e6 * inverse)), rel=1e-9)

    zenith = {row["telescope_code"]: row["sefd"] for row in frame(observation, "sefd").iter_rows(named=True)}
    at_zenith = np.sqrt(zenith[first] * zenith[second]) / (0.8825 * np.sqrt(2 * 16e6 * together))
    assert band["noise"] > 1.05 * at_zenith, "the elevation has to reach the noise"


def test_a_station_is_followed_by_its_elevation_whatever_its_mount_is_limited_in(observed):
    """An equatorial mount is bounded in declination, and `az_el` reports that: it is not an elevation."""
    project, observation, core = observed
    equatorial, azimuthal = observation.get_telescopes().get_items()
    equatorial.set({"mount_type": "EQUA", "elevation_range": (-90.0, 90.0),
                    "azimuth_range": (-180.0, 180.0)})
    run(core, observation, "sefd_track", "az_el")

    track = frame(observation, "sefd_track")
    pointing = frame(observation, "az_el")

    def followed(where, code):
        column = "el" if where is pointing else "elevation"
        return where.filter(pl.col("telescope_code") == code).sort("time")[column].to_list()

    # `az_el` leaves out what the mount cannot point at; the track follows the source anyway.
    def of(where, code):
        column = "el" if where is pointing else "elevation"
        return where.filter(pl.col("telescope_code") == code).select(["time", column]).unique()

    both = (of(track, azimuthal.get_code()).join(of(pointing, azimuthal.get_code()), on="time")
            .filter(pl.col("el").is_not_nan() & pl.col("elevation").is_not_null()))
    assert both.height > 0, "the azimuthal station saw nothing to compare against"
    assert both["elevation"].to_list() == pytest.approx(both["el"].to_list(), abs=1e-9)

    declination = observation.get_sources().get_items()[0].dec_degrees
    reported = [value for value in followed(pointing, equatorial.get_code())
                if value is not None and not np.isnan(value)]
    assert reported and max(reported) - min(reported) < 0.01
    assert reported[0] == pytest.approx(declination, abs=0.5), "that is the source's declination"
    elevations = [value for value in followed(track, equatorial.get_code()) if value is not None]
    assert max(elevations) - min(elevations) > 1.0, "an elevation moves; a declination does not"


def test_other_weather_is_another_answer_rather_than_the_one_already_stored(observed):
    project, observation, core = observed
    run(core, observation, "baseline_sensitivity")
    dry = frame(observation, "baseline_sensitivity").filter(pl.col("if_name") != "all")["noise"][0]

    run(core, observation, "baseline_sensitivity", force=False,
        opacity=[[900.0, 1100.0, 0.08]], t_atm=270.0)
    wet = frame(observation, "baseline_sensitivity").filter(pl.col("if_name") != "all")["noise"][0]

    assert wet > dry


def test_weather_that_cannot_be_used_is_refused_rather_than_half_applied(observed):
    project, observation, core = observed

    with pytest.raises(ValueError, match="t_atm"):
        ScheduleCalculator._elevation_parameters({"opacity": [[900.0, 1100.0, 0.08]]})
    with pytest.raises(ValueError, match="overlap"):
        ScheduleCalculator._elevation_parameters(
            {"opacity": [[900.0, 1100.0, 0.08], [1000.0, 1200.0, 0.1]], "t_atm": 270.0})

    outcome = core.compute(obj=None, method="run", targets=[observation],
                           calculations=["sefd_track"], time_step=600.0, force=True,
                           opacity=[[900.0, 1100.0, 0.08]])

    assert outcome["failed"], "an opacity alone cannot say what the air adds"
    assert not observation.get_calculated_data_by_key("sefd_track"), "and nothing was stored"
    refused = [row for row in outcome["report"] if row["outcome"] == "failed"]
    assert refused and "t_atm" in refused[0]["error"], (
        "the report has to say why, or it says 'failed' and sends the user to the log")


# --- what cannot be worked out is said ---------------------------------------------------------------

def test_a_station_without_a_system_temperature_is_named_and_nothing_is_guessed(observed):
    project, observation, core = observed
    station = observation.get_telescopes().get_items()[0]
    station.set({"system_temperature_table": []})
    run(core, observation, "baseline_sensitivity")

    sefd = frame(observation, "sefd").filter(pl.col("telescope_code") == station.get_code()).row(0, named=True)
    band = frame(observation, "baseline_sensitivity").filter(pl.col("if_name") != "all").row(0, named=True)

    assert sefd["sefd"] is None and sefd["origin"] == "none"
    assert "no SEFD and no system temperature" in sefd["reason"]
    assert band["snr"] is None and band["detected"] is None
    assert station.get_code() in band["reason"]


def test_a_source_without_a_flux_at_the_band_is_named_and_nothing_is_guessed(observed):
    project, observation, core = observed
    observation.get_sources().get_items()[0].set({"flux_table": {5000.0: 1.0}})
    run(core, observation, "baseline_sensitivity")

    band = frame(observation, "baseline_sensitivity").filter(pl.col("if_name") != "all").row(0, named=True)

    assert band["flux"] is None and band["snr"] is None and band["min_duration"] is None
    assert band["noise"] is not None, "the noise does not need a flux"
    assert "no spectral index" in band["reason"]


# --- filling the table ------------------------------------------------------------------------------

def test_filling_writes_a_computed_sefd_over_the_band_and_never_over_a_measurement(observed):
    project, observation, core = observed
    measured, computed = observation.get_telescopes().get_items()
    measured.set({"sefd_table": [(990.0, 1010.0, 999.0)]})

    run(core, observation, "sefd", fill=True)

    rows = {row["telescope_code"]: row for row in frame(observation, "sefd").iter_rows(named=True)}
    assert rows[measured.get_code()]["origin"] == "table" and not rows[measured.get_code()]["filled"]
    assert measured.sefd_table == [(990.0, 1010.0, 999.0)], "a measured SEFD was replaced"
    assert rows[computed.get_code()]["filled"]
    assert computed.sefd_table == [(1000.0, 1016.0, rows[computed.get_code()]["sefd"])]


def test_a_filled_row_that_would_overlap_a_measured_one_is_not_written_and_says_why(observed):
    project, observation, core = observed
    station = observation.get_telescopes().get_items()[0]
    station.set({"sefd_table": [(1010.0, 1100.0, 400.0)]})

    run(core, observation, "sefd", fill=True)

    row = frame(observation, "sefd").filter(pl.col("telescope_code") == station.get_code()).row(0, named=True)
    assert row["origin"] == "parameters" and not row["filled"]
    assert "not written" in row["reason"] and "overlap" in row["reason"]
    assert station.sefd_table == [(1010.0, 1100.0, 400.0)]


# --- what it draws ------------------------------------------------------------------------------------

def draw(core, observation, plot_type, **attributes):
    """Draw one plot and hand back its figure, as the visualization tab does."""
    response = core.visualize(obj=observation, plot_type=plot_type, return_figure=True,
                              show=False, raise_on_error=False, **attributes)
    assert response.ok, response.error
    figure = (response.value or {}).get("figure")
    assert figure is not None, f"'{plot_type}' drew nothing at all"
    return figure


def test_the_sefd_plot_says_which_sefd_was_measured_and_which_was_worked_out(observed):
    project, observation, core = observed
    measured, computed = observation.get_telescopes().get_items()
    measured.set({"sefd_table": [(990.0, 1010.0, 999.0)]})
    run(core, observation, "sefd")

    figure = draw(core, observation, "sefd")
    axes = figure.get_axes()[0]
    bars = {round(bar.get_height(), 6): bar.get_hatch() for bar in axes.patches}
    worked_out = frame(observation, "sefd").filter(
        pl.col("telescope_code") == computed.get_code())["sefd"][0]

    assert axes.get_yscale() == "log", "a 25-metre dish beside a 100-metre one needs it"
    assert len(axes.patches) == 2
    assert bars[999.0] is None, "a measurement is drawn plainly"
    assert bars[round(worked_out, 6)] == "//", "and what was computed is hatched"


def test_a_station_with_no_sefd_gets_no_bar_but_is_named(observed):
    project, observation, core = observed
    station = observation.get_telescopes().get_items()[0]
    station.set({"system_temperature_table": []})
    run(core, observation, "sefd")

    figure = draw(core, observation, "sefd")
    axes = figure.get_axes()[0]

    assert len(axes.patches) == 1, "a bar of zero would read as an infinitely sensitive station"
    assert [text.get_text() for text in axes.texts] == ["no SEFD"]


def test_the_track_plot_draws_the_sefds_it_followed_and_the_zenith_behind_them(observed):
    project, observation, core = observed
    run(core, observation, "sefd_track", opacity=[[900.0, 1100.0, 0.08]], t_atm=270.0)

    figure = draw(core, observation, "sefd_track")
    axes = figure.get_axes()[0]
    followed = frame(observation, "sefd_track").filter(pl.col("sefd").is_not_null())
    stations = followed["telescope_code"].unique().len()
    drawn = sorted(value for line in axes.get_lines() for value in line.get_ydata()
                   if line.get_linestyle() != "--")

    assert sorted(followed["sefd"].to_list()) == pytest.approx(drawn, rel=1e-12)
    assert sum(1 for line in axes.get_lines() if line.get_linestyle() == "--") == stations, \
        "the zenith goes behind each station"


def a_schedule_of(observation, count=9):
    """Replace the fixture's day-long scan with a run of short ones through the night.

    Notes:
        - One scan is one cell of a grid and one point of a track, which is not enough to say
          anything about either. The stations lose the source part-way through, which is the
          other half of what these plots are for.
    """
    from astropy.time import Time

    scans = observation.get_scans()
    first = scans.get_items()[0]
    source = observation.get_sources().get_items()[0]
    for existing in list(scans.get_items()):
        scans.remove(existing.name)
    for index in range(count):
        scans.create_scan(name=f"scan_{index:02d}",
                          start=Time(first.get_start().mjd + 0.6 + index * 0.045, format="mjd"),
                          duration=600.0, source=source, telescopes=list(first.telescopes),
                          frequencies=list(first.frequencies))


def rendered(figure):
    """Draw the figure for real, so what is measured is what a reader would see."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    FigureCanvasAgg(figure)
    figure.canvas.draw()
    return figure.canvas.get_renderer()


@pytest.mark.parametrize("plot_type", ["sefd", "sefd_track"])
def test_the_legend_sits_beside_the_plot_and_not_on_top_of_it(observed, plot_type):
    """"from parameters" was written across the bars: the margin was a fixed fraction of the
    figure and the legend is as wide as its longest label."""
    project, observation, core = observed
    run(core, observation, plot_type)

    figure = draw(core, observation, plot_type)
    renderer = rendered(figure)
    legend = figure.legends[0]

    assert legend.get_window_extent(renderer).x0 >= figure.get_axes()[0].get_window_extent(renderer).x1


def test_the_colour_bar_counts_sigmas_in_plain_numbers_and_red_is_the_poor_end(observed):
    project, observation, core = observed
    # Several scans at different elevations, so the bar has a range to label -- and a narrow one,
    # which is where a logarithmic bar puts its ticks outside what is drawn.
    a_schedule_of(observation)
    run(core, observation, "baseline_sensitivity", time_step=300.0,
        opacity=[[900.0, 1100.0, 0.06]], t_atm=270.0)

    figure = draw(core, observation, "baseline_sensitivity")
    rendered(figure)
    grid, bar = figure.get_axes()
    colours = grid.collections[0].cmap

    assert "sigma" in bar.get_ylabel(), "a signal-to-noise of five is five of something"
    labels = [text.get_text() for text in bar.get_yticklabels() if text.get_text()]
    assert labels, "the bar has to be readable at all"
    # A unicode minus is still a number; "2 x 10^0" is not, and that is what a logarithmic bar
    # writes for a signal-to-noise of two.
    numbers = [float(label.replace("\N{MINUS SIGN}", "-")) for label in labels]
    low, high = grid.collections[0].get_clim()
    inside = [number for number in numbers if low <= number <= high]
    assert len(inside) >= 3, (
        f"the bar is coloured over {low:.2f}-{high:.2f} and labelled {numbers}: a logarithmic "
        f"bar over a range this narrow puts its ticks at 0.1, 1, 10 and 100")

    poorest, best = colours(0.0), colours(1.0)
    assert poorest[0] > poorest[2], "the lowest signal-to-noise is red"
    assert best[2] > best[0], "and the highest is not"


def test_the_sensitivity_grid_marks_every_baseline_that_misses_the_threshold(observed):
    project, observation, core = observed
    run(core, observation, "baseline_sensitivity")
    reached = frame(observation, "baseline_sensitivity").filter(pl.col("if_name") == "all")["snr"][0]

    figure = draw(core, observation, "baseline_sensitivity")
    grid = figure.get_axes()[0].collections[0].get_array()
    marks = [collection for collection in figure.get_axes()[0].collections[1:]]

    assert grid.compressed().tolist() == pytest.approx([reached], rel=1e-12)
    assert not marks, "it is detected, so nothing is crossed out"

    run(core, observation, "baseline_sensitivity", threshold=reached * 2.0)
    crossed = draw(core, observation, "baseline_sensitivity").get_axes()[0].collections[1]

    assert len(crossed.get_offsets()) == 1, "and now it is not"


# --- asked for in the interface -----------------------------------------------------------------------

def dialog_for(project, qt_application):
    """The calculation dialog, as the window opens it."""
    from pastrocore.gui.p_dialog_calculations import CalculationDialog

    return CalculationDialog(ScheduleManipulator(project), time_step=600)


def tick_only(dialog, label):
    """Tick one calculation and untick the rest, as a user clicking would."""
    from PySide6.QtCore import Qt

    for index in range(dialog.ui.calcList.count()):
        item = dialog.ui.calcList.item(index)
        item.setCheckState(Qt.Checked if item.text() == label else Qt.Unchecked)
    dialog.update_params_ui()


def test_the_dialog_offers_the_parameters_a_calculation_takes_and_no_others(observed, qt_application):
    """Asked, not listed: a detection threshold beside a beam pattern would be this dialog
    knowing which calculation is which."""
    project, observation, core = observed
    dialog = dialog_for(project, qt_application)
    try:
        tick_only(dialog, "Beam Pattern")
        assert not dialog.ui.thresholdSpin.isEnabled()
        assert not dialog.ui.opacityTable.isEnabled()

        tick_only(dialog, "Baseline Sensitivity")
        assert dialog.ui.thresholdSpin.isEnabled() and dialog.ui.bitsCombo.isEnabled()
        assert dialog.ui.opacityTable.isEnabled() and dialog.ui.airTemperatureSpin.isEnabled()
        assert dialog.ui.gainCurveTable.isEnabled()

        tick_only(dialog, "SEFD")
        assert dialog.ui.fillCheck.isEnabled(), "filling the table is the SEFD's to be asked"
        assert not dialog.ui.thresholdSpin.isEnabled()
    finally:
        dialog.close()


def test_the_bits_offered_are_the_ones_the_calculator_knows(observed, qt_application):
    """How much quantising leaves is physics; a combo box holding 1 and 2 because somebody typed
    them is that physics written down twice."""
    from pastrocore.super.schedule_calculator import ScheduleCalculator

    project, observation, core = observed
    dialog = dialog_for(project, qt_application)
    try:
        offered = [dialog.ui.bitsCombo.itemData(index)
                   for index in range(dialog.ui.bitsCombo.count())]
        assert offered == sorted(ScheduleCalculator.RECORDING_EFFICIENCY)
    finally:
        dialog.close()


def test_what_is_typed_into_the_dialog_is_what_the_request_carries(observed, qt_application, monkeypatch):
    """The boxes are only worth having if what they hold reaches the calculation."""
    from PySide6.QtCore import QObject, Signal

    from pastrocore.gui import p_dialog_calculations

    sent = {}

    class Recorder(QObject):
        progress = Signal(int, str)
        finished = Signal(dict, list, dict)
        error = Signal(str)

        def __init__(self, manipulator, targets, keys, params):
            super().__init__()
            sent.update(keys=keys, params=params)

        def start(self):
            pass

    monkeypatch.setattr(p_dialog_calculations, "CalculationThread", Recorder)

    project, observation, core = observed
    dialog = dialog_for(project, qt_application)
    try:
        tick_only(dialog, "Baseline Sensitivity")
        dialog.ui.thresholdSpin.setValue(7.0)
        dialog.ui.bitsCombo.setCurrentIndex(0)
        dialog.ui.airTemperatureSpin.setValue(270.0)
        dialog.opacity_model.add_row(900.0, 1100.0, 0.08)
        dialog.gain_curve_model.add_row("ALMA", 900.0, 1100.0, [0.9, 0.004, -0.00003])
        dialog.run_calculation()

        # Per calculation, by the label the list shows.
        asked = sent["params"]["Baseline Sensitivity"]
        assert asked["threshold"] == 7.0
        assert asked["bits"] == dialog.ui.bitsCombo.itemData(0)
        assert asked["t_atm"] == 270.0
        assert asked["opacity"] == [[900.0, 1100.0, 0.08]]
        assert asked["gain_curve"] == {"ALMA": [[900.0, 1100.0, [0.9, 0.004, -0.00003]]]}
        assert "fill" not in asked, "what was not ticked is not sent"
    finally:
        dialog.worker = None
        dialog.close()


def test_a_gain_curve_is_typed_however_it_is_written_down_and_refused_when_it_is_not_one(observed, qt_application):
    from PySide6.QtCore import Qt

    from pastrocore.gui.p_table_models import GainCurveTableModel

    model = GainCurveTableModel()
    model.add_row("EF", 900.0, 1100.0, [1.0])

    assert model.setData(model.index(0, 3), "0.9 0.004 -3e-05", Qt.EditRole)
    assert model.get_data() == {"EF": [[900.0, 1100.0, [0.9, 0.004, -3e-05]]]}
    assert model.setData(model.index(0, 3), "0.9, 0.004", Qt.EditRole), "commas are how they are quoted"
    assert not model.setData(model.index(0, 3), "a curve", Qt.EditRole)
    assert not model.setData(model.index(0, 1), "-5", Qt.EditRole), "a frequency is positive"
    assert model.get_data() == {"EF": [[900.0, 1100.0, [0.9, 0.004]]]}

    model.add_row("", 900.0, 1100.0, [1.0])
    assert set(model.get_data()) == {"EF"}, "a row nobody has named yet is not a curve"


# --- living with the rest ---------------------------------------------------------------------------

def test_a_new_flux_makes_the_sensitivity_stale_and_leaves_the_sefd_alone(observed):
    """What each reads is declared beside it: an SEFD reads stations and bands, not sources."""
    from pastrocore.base import freshness

    project, observation, core = observed
    run(core, observation, "baseline_sensitivity")
    assert freshness.is_stale(observation, "baseline_sensitivity") is False

    observation.get_sources().get_items()[0].set({"flux_table": {1000.0: 3.0}})

    assert freshness.is_stale(observation, "baseline_sensitivity") is True
    assert freshness.is_stale(observation, "sefd") is False


def test_asking_for_another_threshold_is_asking_another_question(observed):
    """The weather, the recording and the threshold are not the model, so the fingerprint that
    watches the model cannot see them move.

    A run that reused the stored result would answer a question about seven sigma with the
    numbers worked out for five: the detections would be the old ones and the duration needed
    to reach the threshold would be the old one too, silently. The rule lives in the cache and
    is driven by what each result records, so it holds for every parameter of every calculation.
    """
    project, observation, core = observed
    run(core, observation, "baseline_sensitivity", threshold=5.0)
    at_five = frame(observation, "baseline_sensitivity").filter(pl.col("if_name") != "all").row(0, named=True)

    run(core, observation, "baseline_sensitivity", threshold=7.0, force=False)
    at_seven = frame(observation, "baseline_sensitivity").filter(pl.col("if_name") != "all").row(0, named=True)

    assert observation.get_calculated_metadata("baseline_sensitivity")["threshold"] == 7.0
    # The time needed to reach the threshold goes as its square: (7/5)^2 of what five needed.
    assert at_seven["min_duration"] == pytest.approx(at_five["min_duration"] * (7.0 / 5.0) ** 2)


def test_the_same_question_twice_is_not_worked_out_twice(observed):
    """The half that keeps the rule above from being "recompute everything, always"."""
    project, observation, core = observed
    run(core, observation, "baseline_sensitivity", threshold=5.0)
    first = frame(observation, "baseline_sensitivity")

    run(core, observation, "baseline_sensitivity", threshold=5.0, force=False)

    assert frame(observation, "baseline_sensitivity") is first, (
        "the same question was worked out again rather than answered from what is stored")


def test_the_new_results_export_like_any_other(observed, tmp_path):
    """Nothing lists what can be exported: the dialog asks the catalogue and the columns come
    from the schema, so a calculation that exists is one that can be written out."""
    project, observation, core = observed
    run(core, observation, "baseline_sensitivity")

    labels = {entry["key"]: entry["label"] for entry in core.inspect(obj=None, method="catalogue")}
    response = core.export(obj=observation, export_data=True, export_vis=False,
                           export_path=str(tmp_path), raise_on_error=False,
                           calc_types=[labels[key] for key in
                                       ("sefd", "sefd_track", "baseline_sensitivity")])

    assert response.ok, response.error
    written = {pathlib.Path(path).stem.split("_")[-1]: pathlib.Path(path)
               for path in response.value["written"]}
    assert len(response.value["written"]) == 3, sorted(written)

    detection = next(path for path in written.values() if "sensitivity" in path.name.lower())
    header = detection.read_text(encoding="utf-8").splitlines()[0]
    assert "snr" in header and "scan_duration" in header and "min_duration" in header


def test_detection_can_be_asked_of_the_analyzer_like_any_other_result(observed):
    project, observation, core = observed
    run(core, observation, "baseline_sensitivity")

    summary = core.analyze(obj=project, method="summary", key="baseline_sensitivity",
                           columns=["snr"], group_by=["baseline"], where={"if_name": "all"})

    assert summary and summary[0]["column"] == "snr" and summary[0]["count"] == 1
