"""The plots must keep drawing the same points.

The visualizer had no tests at all, which mattered more than the number suggests: every plot
method is wrapped in `except Exception` that logs and returns an empty figure. A defect
introduced there does not raise, it quietly produces a blank plot -- so a test that only checks
"it did not crash" would pass through exactly the failure worth catching.

These tests therefore read the drawn artists back out of the figure and compare the coordinates
against a stored reference. A filter that starts dropping rows changes those coordinates, and
an exception that empties the plot removes them entirely. Both fail here.

The reference lives in `fixtures/visualization_reference.json` and is regenerated with:

    python tests/test_visualization_characterization.py --regenerate

Regenerating it is a deliberate act, and the reason belongs in the commit message that carries
the new file.
"""
import json
import math
import pathlib

import numpy as np
import pytest

REFERENCE = pathlib.Path(__file__).parent / "fixtures" / "visualization_reference.json"

# Plot coordinates come from the same Earth-orientation tables as the calculations underneath
# them, so they carry the same machine-to-machine spread. See `test_characterization` for why
# this number is measured rather than reasoned about.
RELATIVE_TOLERANCE = 5e-4
ABSOLUTE_FLOOR = 1e-8

PLOT_TYPES = ["uv_coverage", "sun_angles", "az_el", "time_on_source", "beam_pattern",
              "baseline_projections", "mollweide_tracks", "parallactic_angle"]


def drawn_points(figure):
    """Return every coordinate the figure actually draws, as plain numbers.

    Args:
        figure (Figure): A rendered matplotlib figure.

    Returns:
        dict: Counts of the artists, and their coordinates rounded to a fixed number of
            decimals. Rounding keeps the reference file readable and stable; the comparison
            below still applies a tolerance on top.

    Notes:
        - Lines and collections are read separately because the plots use both: tracks are
          lines, scatter plots are collections, and a change that empties one while leaving
          the other would otherwise pass unnoticed.
    """
    axes_summary = []
    for axes in figure.get_axes():
        raw_lines = [np.column_stack([np.asarray(x, dtype=float), np.asarray(y, dtype=float)])
                     for x, y in (line.get_data() for line in axes.get_lines())]
        raw_collections = [_collection_points(collection) for collection in axes.collections]

        # **Measured from the smallest coordinate the axes draw.** A relative tolerance on an
        # MJD near 61000 is thirty days wide, so a bar moved by a sampling step -- or by an hour
        # -- compared equal. From an origin, the same step is a visible part of the span.
        drawn = [points for points in raw_lines + raw_collections if len(points)]
        stacked = np.vstack(drawn) if drawn else np.zeros((0, 2))
        finite = stacked[np.all(np.isfinite(stacked), axis=1)]
        origin = finite.min(axis=0) if len(finite) else np.zeros(2)

        axes_summary.append({
            "title": axes.get_title(),
            "xlabel": axes.get_xlabel(),
            "ylabel": axes.get_ylabel(),
            "origin": [_clean(value) for value in origin],
            "lines": [_relative(points, origin, as_columns=True) for points in raw_lines],
            "collections": [_relative(points, origin) for points in raw_collections],
            # What a reader reads off the plot: the "Total" of time on source is a label, not
            # a coordinate, and nothing guarded it.
            "texts": [label.get_text() for label in axes.texts],
            "images": len(axes.images),
        })
    return {"axes": axes_summary}


def _collection_points(collection):
    """Return what a collection draws, as an (n, 2) array.

    Notes:
        - A scatter places copies of one marker at its offsets, so the offsets are the data. A
          filled region is the other way round: `fill_between` draws polygons whose offsets
          are a single `(0, 0)` and whose data is the vertices. Reading only offsets recorded
          every bar of `time_on_source` as the same point, so a bar of any length passed.
    """
    offsets = np.asarray(collection.get_offsets(), dtype=float).reshape(-1, 2)
    if len(offsets) and np.any(offsets != 0.0):
        return offsets
    paths = collection.get_paths()
    if not paths:
        return offsets
    return np.vstack([np.asarray(path.vertices, dtype=float) for path in paths])


def _relative(points, origin, as_columns=False):
    """Coordinates less the axes' origin, rounded, as lists -- columns for a line, rows otherwise."""
    shifted = np.asarray(points, dtype=float) - origin if len(points) else np.zeros((0, 2))
    if as_columns:
        return [[_clean(v) for v in shifted[:, 0]], [_clean(v) for v in shifted[:, 1]]]
    return [[_clean(v) for v in row] for row in shifted]


def _clean(value):
    """Make a coordinate JSON-safe and stable to write."""
    number = float(value)
    if math.isnan(number):
        return "nan"
    if math.isinf(number):
        return "inf" if number > 0 else "-inf"
    return round(number, 6)


def worst_difference(actual, expected, path="figure"):
    """Return the largest relative difference between two drawn-point structures.

    Args:
        actual: What the visualizer drew now.
        expected: What the reference records.
        path (str): Where in the structure the comparison currently is, so a failure names
            the axes and artist rather than a number alone.

    Returns:
        tuple: `(difference, path)`. Anything structural -- a differing count, a changed
            label, a number that became a string -- reports as infinite.
    """
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            return math.inf, f"{path}: structure changed"
        worst, where = 0.0, ""
        for key in expected:
            difference, spot = worst_difference(actual[key], expected[key], f"{path}.{key}")
            if difference > worst:
                worst, where = difference, spot
        return worst, where

    if isinstance(expected, list):
        if not isinstance(actual, list):
            return math.inf, f"{path}: structure changed"
        if len(actual) != len(expected):
            return math.inf, f"{path}: {len(expected)} -> {len(actual)} items"
        worst, where = 0.0, ""
        for index, (left, right) in enumerate(zip(actual, expected)):
            difference, spot = worst_difference(left, right, f"{path}[{index}]")
            if difference > worst:
                worst, where = difference, spot
        return worst, where

    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        scale = max(abs(float(actual)), abs(float(expected)), ABSOLUTE_FLOOR)
        return abs(float(actual) - float(expected)) / scale, path

    return (0.0 if actual == expected else math.inf), path


def filters_for(observation):
    """Return the filter values the plots need, read from the project rather than hardcoded.

    Args:
        observation (Observation): The object being plotted.

    Returns:
        dict: A source name, the telescope codes, the baselines the saved results mention,
            and the observation's active frequencies.

    Notes:
        - Five of the eight plots refuse to draw without at least one filter, which is a
          deliberate guard rather than a defect: plotting every source over every baseline
          produces something unreadable. A test that omits them measures the guard and
          nothing else -- that is what the first version of this file did, and seven of the
          eight references it recorded were blank.
        - Taking the values from the fixture's own results keeps them true if the fixture is
          ever replaced.
    """
    found = {"source_name": None, "telescopes": [], "baselines": [], "scans": [],
             "frequencies": [float(f) for f in observation.get_frequencies().get_frequencies()]}
    for key in ("uv_coverage", "az_el", "time_on_source"):
        stored = observation.get_calculated_data_by_key(key) or {}
        frame = stored.get("data")
        if frame is None or frame.is_empty():
            continue
        if found["source_name"] is None and "source_name" in frame.columns:
            found["source_name"] = frame["source_name"].unique().to_list()[0]
        for column, target in (("telescope_code", "telescopes"), ("baseline", "baselines"),
                               ("scan_name", "scans")):
            if column in frame.columns and not found[target]:
                # Sorted, because polars does not promise an order for `unique` and the plots
                # draw in the order they are given. Two runs otherwise produce the same picture
                # with its lines in a different sequence, and the comparison below calls that a
                # regression. It did, twice, before this sort was here.
                found[target] = sorted(frame[column].unique().to_list())
    return found


def render(manipulator, observation, plot_type):
    """Draw one plot and return its figure, or None if the visualizer produced nothing."""
    response = manipulator.visualize(obj=observation, plot_type=plot_type,
                                     return_figure=True, show=False, raise_on_error=False,
                                     **filters_for(observation))
    drawn = response.value if response.ok else None
    return drawn.get("figure") if drawn else None


@pytest.fixture(scope="module")
def reference():
    if not REFERENCE.is_file():
        pytest.skip("no stored reference; regenerate it with --regenerate")
    return json.loads(REFERENCE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("plot_type", PLOT_TYPES)
def test_the_plot_draws_what_it_always_drew(manipulator, observation, reference, plot_type):
    """The whole point. If this fails, a plot changed shape or lost its data."""
    if plot_type not in reference:
        pytest.skip(f"the reference holds no '{plot_type}'")

    figure = render(manipulator, observation, plot_type)
    assert figure is not None, (
        f"'{plot_type}' produced no figure at all. The plot methods swallow exceptions and "
        f"return an empty result, so look in the log for what was raised.")

    actual = drawn_points(figure)
    worst, where = worst_difference(actual, reference[plot_type])
    assert worst <= RELATIVE_TOLERANCE, (
        f"'{plot_type}' draws differently than the reference. Worst relative difference "
        f"{worst:.3e} at {where}, tolerance {RELATIVE_TOLERANCE:.0e}. If the change is "
        f"deliberate, regenerate the reference and say why in the commit.")


@pytest.mark.parametrize("plot_type", PLOT_TYPES)
def test_the_plot_is_not_blank(manipulator, observation, plot_type):
    """A reference recorded from an already-broken plot would lock the breakage in.

    This asserts independently of the reference that something was drawn, so the suite cannot
    be satisfied by eight empty figures agreeing with each other.
    """
    figure = render(manipulator, observation, plot_type)
    assert figure is not None, f"'{plot_type}' produced no figure"

    drawn = drawn_points(figure)
    artists = sum(len(axes["lines"]) + len(axes["collections"]) + axes["images"]
                  for axes in drawn["axes"])
    assert artists > 0, f"'{plot_type}' drew nothing"


def test_the_reference_covers_every_plot(reference):
    """A plot type quietly dropped from the reference would stop being checked."""
    missing = [name for name in PLOT_TYPES if name not in reference]
    assert not missing, f"the reference is missing {missing}"


def test_the_comparison_notices_a_moved_point():
    """A tolerance that let anything through would be worse than no test."""
    original = {"axes": [{"title": "t", "xlabel": "x", "ylabel": "y",
                          "lines": [[[1.0, 2.0], [3.0, 4.0]]], "collections": [], "images": 0}]}
    moved = json.loads(json.dumps(original))
    moved["axes"][0]["lines"][0][1][0] = 3.003

    worst, _ = worst_difference(moved, original)
    assert worst > RELATIVE_TOLERANCE, "a one-in-a-thousand move must not pass"


def test_the_comparison_notices_a_lost_artist():
    """Losing a line is the failure mode a filter regression actually produces."""
    original = {"axes": [{"title": "t", "xlabel": "x", "ylabel": "y",
                          "lines": [[[1.0], [2.0]], [[3.0], [4.0]]], "collections": [],
                          "images": 0}]}
    lost = json.loads(json.dumps(original))
    lost["axes"][0]["lines"].pop()

    worst, where = worst_difference(lost, original)
    assert worst == math.inf, f"a dropped line must fail, reported {worst} at {where}"


# --- filters -------------------------------------------------------------------------------

def test_the_tracks_are_narrowed_to_the_sources_that_were_asked_for(manipulator, observation):
    """Unticking a source has to take its tracks away, not only its marker.

    A track names a scan and a telescope; the scan is what carries the source. The filter went
    through a `source_name` column no track has ever had -- and it sat inside the branch that
    ran when a source was *not* in the metadata, so the ordinary case filtered nothing and the
    unknown case asked polars for a column that does not exist.

    The fixture observes one source, so the second one is added here: with a single source
    there is nothing a filter can be wrong about, which is why nothing caught this.
    """
    import polars as pl
    from astropy.time import Time

    from pastrocore.base.sources import Source

    theirs = observation.get_scans().get_items()[0]
    elsewhere = Source(name="OTHER", ra_h=1.0, de_d=10.0)
    observation.get_sources().add(elsewhere)
    # A day later, because one antenna may not be pointed at two sources at once.
    observation.get_scans().create_scan(
        name="second", start=Time(theirs.get_start().jd + 1.0, format="jd"),
        duration=theirs.duration, source=elsewhere, telescopes=list(theirs.telescopes))

    code = observation.get_telescopes().get_items()[0].get_code()
    frame = pl.DataFrame({"time": [1.0, 2.0], "scan_name": [theirs.name, "second"],
                          "telescope_code": [code, code], "lon": [10.0, 20.0],
                          "lat": [30.0, 40.0]})
    observation.set_calculated_data_by_key(
        "mollweide_tracks", frame,
        {"time_step": 600.0, "scan_count": 2,
         "sources": {source.name: [1.0, 2.0] for source in observation.get_sources().get_items()}})

    response = manipulator.visualize(obj=observation, plot_type="mollweide_tracks",
                                     return_figure=True, show=False, raise_on_error=False,
                                     telescopes=[code], sources=["OTHER"])
    assert response.ok, "the plot refused to draw at all"
    assert response.value.get("scans") == 1, (
        f"one of the two scans is on OTHER, so one track belongs in the plot; drew "
        f"{response.value.get('scans')}")


def regenerate():
    """Write the reference from the current behaviour.

    Notes:
        - Deliberately not a test. Regenerating turns whatever the visualizer does today into
          the expectation, which is only correct when the change was intended.
    """
    import conftest
    from pastrocore.super.schedule_manipulator import ScheduleManipulator
    from pastrocore.super.schedule_project import ScheduleProject

    project = ScheduleProject.from_dict(json.loads(conftest.FIXTURE.read_text(encoding="utf-8")))
    manipulator = ScheduleManipulator(project)
    observation = project.get_observations()[0]

    recorded = {}
    for plot_type in PLOT_TYPES:
        figure = render(manipulator, observation, plot_type)
        if figure is None:
            print(f"  {plot_type}: no figure, skipped")
            continue
        recorded[plot_type] = drawn_points(figure)
        drawn = sum(len(axes["lines"]) + len(axes["collections"])
                    for axes in recorded[plot_type]["axes"])
        print(f"  {plot_type}: {len(recorded[plot_type]['axes'])} axes, {drawn} artists")

    REFERENCE.write_text(json.dumps(recorded, indent=1), encoding="utf-8")
    print(f"wrote {REFERENCE} ({REFERENCE.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    import sys

    if "--regenerate" in sys.argv:
        sys.path.insert(0, str(pathlib.Path(__file__).parent))
        sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
        regenerate()
    else:
        print(__doc__)


def test_a_zero_length_block_does_not_take_the_plot_with_it(manipulator, observation):
    """Reported from a real project: `KeyError: 'ALMA'` and no time-on-source plot at all.

    A source visible for less than one time step produces a block whose start equals its end.
    The sweep sorted its events as plain tuples, and "end" sorts before "start", so the
    telescope was removed from the active set before it was ever added.
    """
    import polars as pl

    stored = observation.get_calculated_data_by_key("time_on_source")
    frame = stored["data"]
    zero_length = frame.with_columns(pl.col("start").alias("end"),
                                     pl.lit(0.0).alias("duration"))
    observation.set_calculated_data_by_key("time_on_source", zero_length,
                                           stored.get("metadata") or {})

    figure = render(manipulator, observation, "time_on_source")
    assert figure is not None, "a zero-length block must not destroy the plot"


def test_a_bar_moved_by_one_sampling_step_is_noticed(manipulator, observation, reference):
    """The harness has to see what `time_on_source` draws, and see it move.

    It saw neither. `fill_between` draws polygons whose offsets are a single `(0, 0)`, so every
    bar was recorded as the same point; and a relative tolerance on an MJD near 61000 is thirty
    days wide. A bar one sampling step longer -- which is exactly what correcting the block
    duration produced -- compared equal to the old one.
    """
    import polars as pl

    stored = observation.get_calculated_data_by_key("time_on_source")
    frame = stored["data"]
    longer = frame.with_columns((pl.col("end") + 300.0 / 86400.0).alias("end"),
                                (pl.col("duration") + 300.0).alias("duration"))
    observation.set_calculated_data_by_key("time_on_source", longer, stored.get("metadata") or {})

    worst, where = worst_difference(drawn_points(render(manipulator, observation, "time_on_source")),
                                    reference["time_on_source"])
    assert worst > RELATIVE_TOLERANCE, (
        f"a bar five minutes longer compared equal to the reference (worst {worst:.2e} at {where})")


def test_total_carries_across_scans_that_touch(manipulator, observation):
    """Two stations seeing a source for two hours, across two scans that meet end to start.

    "Total" kept the open telescopes in a set. At the seam the start of the second scan was a
    no-op and the end of the first removed the telescope, so the intersection stopped at the
    first scan: one hour reported for two. Touching scans are the ordinary case once a block
    lasts as long as its samples do.
    """
    import polars as pl

    from pastrocore.base.data_structure import CalculatedDataStructure

    hour = 1.0 / 24.0
    rows = [{"source_name": "1228+126", "scan_name": scan, "telescope_code": station,
             "start": 61000.0 + offset, "end": 61000.0 + offset + hour, "duration": 3600.0}
            for scan, offset in (("first", 0.0), ("second", hour))
            for station in ("ALMA", "APEX")]
    observation.set_calculated_data_by_key(
        "time_on_source", pl.DataFrame(rows, schema=CalculatedDataStructure.get_dtypes("time_on_source")),
        {"time_step": 300.0, "scan_count": 2, "visibility_store_key": "source_visibility"})

    answer = manipulator.visualize(obj=observation, plot_type="time_on_source", return_figure=True,
                                   show=False, raise_on_error=False, source_name="1228+126",
                                   telescopes=["ALMA", "APEX"])
    labels = [label.get_text() for label in answer.value["figure"].get_axes()[0].texts]

    assert answer.value["intersections"] == 1
    assert labels == ["7200.0s"], f"two hours in common across two scans, the plot said {labels}"


# --- Az/El stacked by station ----------------------------------------------------------------------

def twelve_stations(observation, times=None):
    """An az/el result for twelve stations, written straight into the observation.

    Every station's azimuth wraps from 350 to 10 degrees half way, and the source is below the
    horizon for a stretch in the middle of the second half -- the two places a line must break.
    """
    import numpy as np
    import polars as pl

    from pastrocore.base.data_structure import CalculatedDataStructure

    codes = [f"T{index:02d}" for index in range(12)]
    moments = np.arange(40) * 600.0 / 86400.0 + 61298.0
    azimuth = np.where(np.arange(40) < 20, 330.0 + np.arange(40), np.arange(40) - 10.0)
    elevation = np.where((np.arange(40) > 27) & (np.arange(40) < 33), np.nan, 40.0)
    rows = {"time": [], "source_name": [], "scan_name": [], "telescope_code": [], "az": [], "el": []}
    for code in codes:
        rows["time"].extend(moments)
        rows["source_name"].extend(["1228+126"] * 40)
        rows["scan_name"].extend(["s"] * 40)
        rows["telescope_code"].extend([code] * 40)
        rows["az"].extend(np.where(np.isnan(elevation), np.nan, azimuth))
        rows["el"].extend(elevation)
    observation.set_calculated_data_by_key(
        "az_el", pl.DataFrame(rows, schema=CalculatedDataStructure.get_dtypes("az_el")),
        {"time_step": 600.0, "scan_count": 1, "position_store_key": "telescope_positions",
         "visibility_store_key": "source_visibility"})
    return codes


def draw_az_el(manipulator, observation, codes):
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    figure = Figure(figsize=(15.5, 9.0), dpi=90)
    FigureCanvasAgg(figure)             # a renderer, so where things land can be measured
    answer = manipulator.visualize(obj=observation, plot_type="az_el", return_figure=True,
                                   show=False, raise_on_error=False, source_name="1228+126",
                                   telescopes=codes, scans=["s"], figure=figure)
    assert answer.ok, answer.error
    figure.canvas.draw()
    return figure


def test_every_ticked_station_gets_a_panel(manipulator, observation):
    """It stopped at ten, and the rest were left out without a word."""
    codes = twelve_stations(observation)
    figure = draw_az_el(manipulator, observation, codes)

    named = [text.get_text() for axes in figure.get_axes() for text in axes.texts]
    assert named == codes


def test_a_station_name_stays_inside_its_own_panel(manipulator, observation):
    """Each name was the title of its panel, and with twelve stacked it sat on the plot above."""
    codes = twelve_stations(observation)
    figure = draw_az_el(manipulator, observation, codes)
    renderer = figure.canvas.get_renderer()

    for axes in figure.get_axes():
        assert axes.get_title() == "", "a title needs a row the stacked panels do not have"
        name = axes.texts[0].get_window_extent(renderer)
        panel = axes.get_window_extent(renderer)
        assert (panel.x0 <= name.x0 and name.x1 <= panel.x1
                and panel.y0 <= name.y0 and name.y1 <= panel.y1), (
            f"{axes.texts[0].get_text()} spills out of its panel")


def test_the_panels_use_the_figure(manipulator, observation):
    """Fixed margins left a third of the figure empty around twelve squeezed panels."""
    codes = twelve_stations(observation)
    figure = draw_az_el(manipulator, observation, codes)

    boxes = [axes.get_position() for axes in figure.get_axes()]
    covered = sum(box.height for box in boxes)
    assert covered > 0.65, f"the panels cover {covered:.0%} of the figure's height"


def test_time_ticks_say_different_things(manipulator, observation):
    """`int(x)` labelled every tick of a day-long plot 61298 or 61299."""
    codes = twelve_stations(observation)
    figure = draw_az_el(manipulator, observation, codes)

    labels = [label.get_text() for label in figure.get_axes()[-1].get_xticklabels() if label.get_text()]
    assert len(labels) == len(set(labels)) > 2, labels


def test_a_line_breaks_where_azimuth_wraps_and_where_nothing_was_seen(manipulator, observation):
    """Drawn through, the azimuth crossed the whole panel for a step the dish never took, and the
    elevation ran flat across the hours the source was below the horizon."""
    import numpy as np

    codes = twelve_stations(observation)
    figure = draw_az_el(manipulator, observation, codes)
    azimuth, elevation = figure.get_axes()[0].get_lines()[:2]

    az = np.asarray(azimuth.get_ydata(), dtype=float)
    el = np.asarray(elevation.get_ydata(), dtype=float)
    assert np.isnan(az).sum() == 2, "one break where it wraps, one across the gap"
    assert np.isnan(el).sum() == 1, "one break across the gap"


# --- redrawing into the figure a tab keeps ------------------------------------------------------------

def figure_contents(figure):
    """What a figure holds, counted: its axes, the text and legends placed on the figure itself."""
    return {"axes": len(figure.axes), "texts": len(figure.texts), "legends": len(figure.legends),
            "drawn": drawn_points(figure)}


@pytest.mark.parametrize("plot_type", PLOT_TYPES)
def test_drawing_again_into_the_same_figure_replaces_what_was_there(manipulator, observation, plot_type):
    """A tab keeps one figure and hands it over for every redraw, and nothing emptied it: each
    redraw added its axes, labels and legend on top of the last. With the same selection they lay
    exactly over each other, so it looked fine -- until a station was unticked."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    figure = Figure(figsize=(12, 7), dpi=80)
    FigureCanvasAgg(figure)
    attributes = dict(plot_type=plot_type, return_figure=True, show=False, raise_on_error=False,
                      figure=figure, **filters_for(observation))

    manipulator.visualize(obj=observation, **attributes)
    once = figure_contents(figure)
    manipulator.visualize(obj=observation, **attributes)
    twice = figure_contents(figure)

    assert once["axes"] > 0, f"'{plot_type}' drew nothing to compare"
    assert twice == once, f"'{plot_type}' drawn twice holds more than drawn once"


def test_unticking_stations_leaves_only_their_panels(manipulator, observation):
    """The report: untick stations on the Az/El tab and axes, labels and legends pile up."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    codes = twelve_stations(observation)
    figure = Figure(figsize=(15.5, 9.0), dpi=90)
    FigureCanvasAgg(figure)

    for chosen in (codes, codes[:4], codes):
        manipulator.visualize(obj=observation, plot_type="az_el", return_figure=True, show=False,
                              raise_on_error=False, source_name="1228+126", telescopes=chosen,
                              scans=["s"], figure=figure)
        assert len(figure.axes) == len(chosen), f"{len(figure.axes)} panels for {len(chosen)} stations"
        assert len(figure.legends) == 1 and len(figure.texts) == 3


# --- the sky outside the Mollweide ellipse ------------------------------------------------------------

def test_the_cursor_leaving_the_mollweide_ellipse_asks_nothing_impossible(manipulator, observation):
    """matplotlib's inverse Mollweide takes `arcsin(y / sqrt 2)` of any point it is given, and it is
    given one outside the ellipse each time the cursor leaves the sky: the axes-leave event asks
    where the cursor is in longitude and latitude. `invalid value encountered in arcsin`, once a
    session -- found by reaching for the zoom button. Outside the ellipse there is no sky, so
    there is no coordinate; inside it, the answer is matplotlib's own."""
    import warnings
    from matplotlib.backend_bases import MouseEvent
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    figure = Figure(figsize=(12, 7), dpi=80)
    FigureCanvasAgg(figure)
    manipulator.visualize(obj=observation, plot_type="mollweide_tracks", return_figure=True,
                          show=False, raise_on_error=False, figure=figure, **filters_for(observation))
    figure.canvas.draw()
    (axes,) = figure.axes
    left, bottom, right, top = axes.bbox.extents

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for x, y in (((left + right) / 2, (bottom + top) / 2), ((left + right) / 2, top + 30)):
            MouseEvent("motion_notify_event", figure.canvas, x, y)._process()
        off_sky = axes.transData.inverted().transform([((left + right) / 2, top + 30),
                                                        (left + 2, top - 2)])
    assert [str(w.message) for w in caught] == []
    assert np.isnan(off_sky).all(), "above the sky, or in the box's corner beside it, is nowhere"

    from matplotlib.projections.geo import MollweideAxes
    on_sky = axes.transProjection.transform(np.radians([(0.0, 0.0), (-179.0, 10.0), (120.0, -89.5)]))
    stock = MollweideAxes.InvertedMollweideTransform(axes.RESOLUTION).transform_non_affine(on_sky)
    assert np.array_equal(axes.transProjection.inverted().transform_non_affine(on_sky), stock),         "on the sky the answer is matplotlib's own"


# --- beam patterns in a grid --------------------------------------------------------------------------

def draw_beam_for(manipulator, observation, count):
    """The fixture's beam, copied to `count` stations, drawn into a tab-sized figure."""
    import polars as pl
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    stored = observation.scan_calculated_data("beam_pattern").collect()
    one = stored.filter(pl.col("telescope_code") == stored["telescope_code"][0])
    codes = [f"T{index:02d}" for index in range(count)]
    observation.set_calculated_data_by_key(
        "beam_pattern",
        pl.concat([one.with_columns(pl.lit(code).alias("telescope_code")) for code in codes])
        .select(stored.columns),
        observation.get_calculated_metadata("beam_pattern"))
    figure = Figure(figsize=(8.8, 5.6), dpi=100)
    FigureCanvasAgg(figure)
    answer = manipulator.visualize(obj=observation, plot_type="beam_pattern", return_figure=True,
                                   show=False, raise_on_error=False, telescopes=codes,
                                   frequencies=[1000.0, 5000.0], figure=figure)
    assert answer.ok, answer.error
    figure.canvas.draw()
    return figure


@pytest.mark.parametrize("count", [2, 9, 12])
def test_beam_panels_names_labels_and_legend_do_not_overlap(manipulator, observation, count):
    """With nine stations each code was its panel's title and sat on the angle labels of the panel
    above; the legend, anchored by its right edge, lay over the top row's last title."""
    figure = draw_beam_for(manipulator, observation, count)
    renderer = figure.canvas.get_renderer()
    panels = [axes for axes in figure.get_axes() if axes.get_visible()]
    assert len(panels) == count

    def overlap(a, b):
        return a.x0 < b.x1 and b.x0 < a.x1 and a.y0 < b.y1 and b.y0 < a.y1

    tick_labels = [(axes, label.get_window_extent(renderer)) for axes in panels
                   for label in axes.get_xticklabels() + axes.get_yticklabels() if label.get_text()]
    legend = figure.legends[0].get_window_extent(renderer)
    for axes in panels:
        assert axes.get_title() == "", "a title needs a row the grid does not have"
        (name,) = axes.texts
        box = name.get_window_extent(renderer)
        panel = axes.get_window_extent(renderer)
        assert panel.x0 <= box.x0 and box.x1 <= panel.x1 and panel.y0 <= box.y0 and box.y1 <= panel.y1, \
            f"{name.get_text()} spills out of its panel"
        assert not [other for other, label in tick_labels if other is not axes and overlap(box, label)], \
            f"{name.get_text()} lies on another panel's labels"
        assert not overlap(legend, panel), f"the legend lies over {name.get_text()}"
        for label in (figure._suptitle, figure._supxlabel, figure._supylabel):
            assert not overlap(label.get_window_extent(renderer), panel), \
                f"'{label.get_text()}' lies over {name.get_text()}"
