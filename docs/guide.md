# A first project

Everything below runs. The suite executes every block on this page, in order, in one namespace —
so if the code here has drifted from the code that ships, the build fails rather than you.

By the end you will have built an observation, calculated something from it, read the numbers
back, and saved it.

## The one thing to know first

**Nothing calls the model directly.** You describe the data as objects, and everything you *do*
to them is a request sent to one orchestrator — the manipulator. A window sends those requests,
and so will a command line, and so would a server. That is why the window has no logic worth
speaking of, and why this guide is not a description of the interface.

```python
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject

project = ScheduleProject(name="Demo")
manipulator = ScheduleManipulator(project)

assert manipulator.get_managing_object() is project
```

## An observation

A project holds observations. An observation holds telescopes, sources, frequencies and scans —
and, once you calculate, results.

```python
project.create_item(item_code="OBS1", observation_type="VLBI")
observation = project.get_observation_by_code("OBS1")

assert observation.code == "OBS1"
assert project.observations() == [observation]
```

### What it observes with

Two stations, given where they are on the Earth in metres (ITRF), and how far they can point:

```python
observation.get_telescopes().create_telescope(
    code="ALMA", name="Atacama Large Millimeter Array",
    x=2225061.164, y=-5440057.37, z=-2481681.15,
    diameter=12.0, elevation_range=(10.0, 90.0))

observation.get_telescopes().create_telescope(
    code="APEX", name="Atacama Pathfinder Experiment",
    x=2225039.53, y=-5441197.63, z=-2479303.36,
    diameter=12.0, elevation_range=(10.0, 90.0))

assert [t.get_code() for t in observation.get_telescopes().get_items()] == ["ALMA", "APEX"]
```

A source, in B1950 hours and degrees, and one intermediate frequency in MHz:

```python
observation.get_sources().create_source(
    name="1228+126", ra_h=12.0, ra_m=30.0, ra_s=49.42,
    de_d=12.0, de_m=23.0, de_s=28.0)

observation.get_frequencies().create_if(name="IF1", frequency=22000.0, bandwidth=64.0)

assert [s.name for s in observation.get_sources().get_items()] == ["1228+126"]
```

### When

A scan is "these telescopes, this source, this window". It is the only way to say *when*: there
is deliberately no second kind of time interval, because a second one would have to be
understood by every calculation, tab and exporter.

```python
from astropy.time import Time

observation.get_scans().create_scan(
    name="scan1", start=Time("2026-08-13T00:00:00"), duration=3600.0,
    source=observation.get_sources().get_items()[0],
    telescopes=list(observation.get_telescopes().get_items()),
    frequencies=list(observation.get_frequencies().get_items()),
    observation=observation)

assert [s.name for s in observation.get_scans().get_items()] == ["scan1"]
```

## What can be calculated

Ask. The list is not written down anywhere — it is worked out from the calculations that exist,
so a new one appears here the moment somebody writes it.

```python
response = manipulator.compute(obj=project, method="catalogue")
catalogue = response["result"] if isinstance(response, dict) and "status" in response else response

offered = {entry["key"] for entry in catalogue if entry["offer"]}
assert "uv_coverage" in offered and "az_el" in offered

uv = next(entry for entry in catalogue if entry["key"] == "uv_coverage")
assert uv["label"] == "UV Coverage"
assert "source_visibility" in uv["requires"]
```

`requires` is why you never have to run things in the right order yourself.

## Calculating

One request. Ask for what you want; everything it needs comes with it, in an order that works,
and independent branches run at once.

```python
outcome = manipulator.compute(obj=None, method="run",
                              targets=[observation], calculations=["az_el"],
                              time_step=600.0)

assert outcome["failed"] == []
assert [step.split("/")[-1] for step in outcome["ran"]] == [
    "time_arrays", "interpolated_orbits", "telescope_positions", "source_visibility", "az_el"]
```

You asked for one calculation and five ran. The four others are what `az_el` needs, and you did
not have to know that.

The outcome describes itself, which is what the window shows and what a command line would
print:

```python
assert outcome["summary"]["steps"] == 5
assert outcome["summary"]["seconds"] > 0.0
assert {row["outcome"] for row in outcome["report"]} == {"ok"}
```

### Running it again does nothing

A second run recomputes what has gone **stale** — nothing here has changed, so nothing is
recomputed:

```python
from pastrocore.base import freshness

assert freshness.is_stale(observation, "az_el") is False

again = manipulator.compute(obj=None, method="run", targets=[observation],
                            calculations=["az_el"], time_step=600.0)
assert again["failed"] == []
```

Move a telescope, and the result knows:

```python
telescope = observation.get_telescopes().get_items()[0]
telescope.set({"x": telescope.x + 1000.0})

assert freshness.is_stale(observation, "az_el") is True
```

The next run recomputes it. To recompute something that is *not* stale — after changing the
calculation itself, which nothing can detect — pass `force=True`.

## Reading a result

A result is a [Polars](https://pola.rs) frame. Its columns are part of the calculation's
schema, so they are the same every time:

```python
result = observation.get_calculated_data_by_key("az_el")
frame = result["data"]

assert frame.columns == ["time", "source_name", "scan_name", "telescope_code", "az", "el"]
assert frame.height > 0
assert set(frame["telescope_code"].unique()) == {"ALMA", "APEX"}
```

Beside it is metadata describing that frame — what it was computed with, and a fingerprint of
the configuration it came from, which is how staleness is decided:

```python
metadata = observation.get_calculated_metadata("az_el")
assert metadata["time_step"] == 600.0
assert metadata["scan_count"] == 1
```

**Read it lazily when you are about to filter.** The whole point of the storage format is that
a plot of one source does not read the other 299:

```python
import polars as pl

view = observation.scan_calculated_data("az_el")
above = view.filter(pl.col("el") > 0.0).collect()
assert above.height <= frame.height
```

## Saving

A project is a **directory**, not a file: a small `project.json` and one parquet file per
result.

```python
destination = TMP / "demo.pastro"
manipulator.save(obj=project, path=str(destination))

assert (destination / "project.json").is_file()
assert list((destination / "results").rglob("*.parquet"))
```

Opening one reads the model and **no results at all** — each is read when something asks for it:

```python
reopened = ScheduleProject.open(str(destination))
back = reopened.get_observation_by_code("OBS1")

assert [t.get_code() for t in back.get_telescopes().get_items()] == ["ALMA", "APEX"]
assert back.get_calculated_data_by_key("az_el")["data"].height == frame.height
```

**Until you save, results live in a scratch directory** that survives a crash — and closing the
window asks before discarding it. Saving moves them into the project.

## What was asked

Every request is recorded, which is what a bug report never manages to say:

```python
history = manipulator.history()
calculations = [row for row in history if row["operation"] == "calculate"]

assert calculations
assert calculations[0]["object"] == observation.name
assert calculations[0]["status"] is True
```

It is plain data — no live objects — so a session can be written to a file and replayed later,
against this project or another one:

```python
written = manipulator.export(obj=project, method="journal", path=str(TMP / "session.json"))
assert written["steps"] == len(history)
```

## Where to go next

- [The calculations](calculations.md) — what each one produces, and what it needs.
- [Installing and running](installing.md).
- [The roadmap](ROADMAP.md) — what is done, what is left, and what was decided against.
