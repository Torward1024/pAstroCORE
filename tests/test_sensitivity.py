"""Sensitivity and detection (E1): each station's SEFD, each baseline's noise, and whether it detects.

The numbers are checked against the equations written out here, not read back from the code, and
against a published case: the VLBA Observational Status Summary's table 5.1, which gives the
baseline sensitivity of identical antennas, `SEFD / (eta_s sqrt(2 dnu tau))`, with eta_s = 0.8,
128 MHz and one minute.
"""
import copy
import json

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
    outcome = core.compute(obj=None, method="run", targets=[observation],
                           calculations=list(calculations), time_step=600.0, **asked)
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


def test_detection_can_be_asked_of_the_analyzer_like_any_other_result(observed):
    project, observation, core = observed
    run(core, observation, "baseline_sensitivity")

    summary = core.analyze(obj=project, method="summary", key="baseline_sensitivity",
                           columns=["snr"], group_by=["baseline"], where={"if_name": "all"})

    assert summary and summary[0]["column"] == "snr" and summary[0]["count"] == 1
