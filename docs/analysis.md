# Asking something of the numbers

A calculation finishes and the numbers sit on disk. **Analysis is what you ask of them
afterwards** — when is the source up, for how long, where are the gaps, how long is the longest
baseline this array reaches, which stations carry it.

It is a fifth operation, `analyze`, and it *reads* results rather than producing them. In the
window it is **Tools → Analysis**; from a terminal it is `pastrocore-cli analyze`.

## Nothing here is written down twice

Which results exist, which of their columns are numbers, which are categories worth grouping or
slicing by, and which are true-or-false columns with runs in them — all of it comes from the
schemas the calculations already declare. A calculation added tomorrow can be summarised and
filtered without a line changing, and it appears in the tab with its own columns because the
tab is filled from the same answer.

```python
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject

project = ScheduleProject(name="Survey")
project.create_item(item_code="OBS1")
core = ScheduleManipulator(project)

described = core.analyze(obj=project, method="describe")
# Empty until something has been calculated -- there is nothing to analyse yet.
assert described == {}
```

Once there are results, each entry says what can be done with it:

```text
uv_coverage  (108 row(s))
  numbers    time, u, v, w
  categories source_name, scan_name, baseline
    baseline: ALMA-APEX
```

`describe` reads no result. A row count comes from the file's own metadata, and the distinct
values of a column read that column and nothing else — which is what the parquet store is for.

## The numbers

```bash
pastrocore-cli analyze survey.pastro summary --key uv_coverage --group-by baseline
```

```text
OBS_DEFAULT  ALMA-APEX  u
    count 108   min -794.434   max 1139.7
    mean 347.599   median 444.043   std 630.961   range 1934.14
```

`range` is there because it *is* the question: how much does this baseline sweep. Nobody wants
to subtract two numbers out of two separate answers.

**NaN is not a number and is not averaged.** A calculation writes NaN for a moment it has no
answer for — an elevation while the source is below the horizon — and those are excluded from
every statistic and **counted** as `missing`, because how many moments have no answer is itself
worth knowing:

```text
count 216   missing 360   min 15.19   max 54.75   mean 39.45
```

Three fifths of that scan the source was down.

## Slicing

A filter takes a value, several values, or a range with either end left open:

```bash
pastrocore-cli analyze survey.pastro summary --key az_el --columns el \
    --where telescope_code=ALMA el=20:
```

| Written | Means |
| --- | --- |
| `telescope_code=ALMA` | that one |
| `telescope_code=ALMA,APEX` | either |
| `el=20:` | 20 and above |
| `el=:80` | up to 80 |
| `el=20:80` | between |

A time is written as a date rather than as an MJD, and the analyzer converts:

```python
core.analyze(obj=project, method="summary", key="az_el",
             where={"time": {"from": "2026-08-10 16:00:00",
                             "to": "2026-08-10 17:00:00"}},
             raise_on_error=False)
```

That is why the tab can hand over what a calendar gave it without knowing what an MJD is.

## Windows and gaps

The primitive the rest is made of: runs of consecutive `True` in a boolean column, per station.

```bash
pastrocore-cli analyze survey.pastro windows --key source_visibility
pastrocore-cli analyze survey.pastro windows --key source_visibility --gaps
```

```text
OBS_DEFAULT  1228+126 ALMA   2026-08-10T15:20:00 to 2026-08-11T00:15:00   540.0 min
```

A run is bounded by the samples that make it, so its length is the time between the first and
last sample **plus one sampling step** — a single sample is a window of one step, not of zero.
The step is measured from the data, within each station's own samples.

The arithmetic that says both are right: **windows plus gaps come to the whole span, exactly.**

## Across stations

"Visible from at least two" is a real question — two is the least that makes a baseline — and
answering it used to mean pivoting a frame per station and lining the moments up.

```bash
pastrocore-cli analyze survey.pastro coverage --at-least 2
```

A moment counts a station once, so two scans sampling the same instant do not make an array of
two.

## Over a whole project

Any of these takes a project instead of an observation, and every row names the observation it
came from — so "which nights are usable" does not need a loop in the interface.

## Taking it away

```bash
pastrocore-cli analyze survey.pastro windows --key source_visibility --to windows.txt
```

Tab-separated with a BOM and `NaN` for what is missing, exactly as a calculated result is
written, so both open in the same spreadsheet. In the tab, **Export** writes the rows already on
screen rather than asking again — a file that does not match the table it came from is worse
than no file.

The columns written are whatever the answer carries. A handler that grows a field writes it
without anything here being told.
