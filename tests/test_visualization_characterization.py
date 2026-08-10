"""The plots must keep drawing the same points.

The visualizer had no tests at all, which mattered more than the number suggests: every plot
method is wrapped in `except Exception` that logs and returns an empty figure. A defect
introduced there does not raise, it quietly produces a blank plot -- so a test that only checks
"it did not crash" would pass through exactly the failure worth catching.

These tests therefore read the drawn artists back out of the figure and compare the coordinates
against a stored reference. A filter that starts dropping rows changes those coordinates, and
an exception that empties the plot removes them entirely. Both fail here.

The reference lives in `fixtures/visualization_reference.json` and is regenerated with:

    python -m tests.test_visualization_characterization --regenerate

Regenerating it is a deliberate act, and the reason belongs in the commit message that carries
the new file.
"""
import json
import math
import pathlib

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
        lines = []
        for line in axes.get_lines():
            x, y = line.get_data()
            lines.append([[_clean(v) for v in list(x)], [_clean(v) for v in list(y)]])
        collections = []
        for collection in axes.collections:
            offsets = collection.get_offsets()
            collections.append([[_clean(v) for v in point] for point in offsets.tolist()])
        axes_summary.append({
            "title": axes.get_title(),
            "xlabel": axes.get_xlabel(),
            "ylabel": axes.get_ylabel(),
            "lines": lines,
            "collections": collections,
            "images": len(axes.images),
        })
    return {"axes": axes_summary}


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
    if isinstance(response, dict) and "status" in response:
        response = response.get("result") if response["status"] else None
    if not response:
        return None
    return response.get("figure")


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
    observation = project.get_observation(next(iter(project.get_items())))

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
