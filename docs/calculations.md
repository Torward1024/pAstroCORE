# The calculations

Fourteen of them. Ten are things you ask for; four are steps the others need, which is why they
are not offered in the interface — being asked to choose "Telescope Positions" means nothing to
somebody who wants a uv plot.

None of this list is written down in the code. It is worked out from the calculations that
exist, so **adding one makes it appear here, in the interface, and in the exporter, without any
of the three being edited**. The block at the bottom of this page fails if this table and the
code disagree.

## What each produces

| Key | Shown as | Offered | Drawn | Columns of the result |
| --- | --- | --- | --- | --- |
| `az_el` | Az/El | yes | yes | `time`, `source_name`, `scan_name`, `telescope_code`, `az`, `el` |
| `baseline_projections` | Baseline Projections | yes | yes | `time`, `source_name`, `scan_name`, `baseline`, `projection` |
| `beam_pattern` | Beam Pattern | yes | yes | `telescope_code`, `theta`, `pattern` |
| `mollweide_tracks` | Mollweide Tracks | yes | yes | `time`, `scan_name`, `telescope_code`, `lon`, `lat` |
| `parallactic_angle` | Parallactic Angle | yes | yes | `time`, `source_name`, `scan_name`, `telescope_code`, `parallactic_angle` |
| `sun_angles` | Sun Angles | yes | yes | `time`, `source_name`, `scan_name`, `telescope_code`, `angle` |
| `telescope_az_el` | Space Telescope Pointing | yes | yes | `time`, `target_code`, `scan_name`, `telescope_code`, `az`, `el`, `range` |
| `telescope_visibility` | Space Telescope Visibility | yes | yes | `time`, `target_code`, `scan_name`, `telescope_code`, `visibility` |
| `time_on_source` | Time On Source | yes | yes | `source_name`, `scan_name`, `telescope_code`, `start`, `end`, `duration` |
| `uv_coverage` | UV Coverage | yes | yes | `time`, `source_name`, `scan_name`, `baseline`, `u`, `v`, `w` |
| `interpolated_orbits` | Interpolated Orbits | step | no | `time`, `scan_name`, `telescope_code`, `x`, `y`, `z` |
| `source_visibility` | Source Visibility | step | no | `time`, `source_name`, `scan_name`, `telescope_code`, `visibility` |
| `telescope_positions` | Telescope Positions | step | no | `time`, `scan_name`, `telescope_code`, `x`, `y`, `z` |
| `time_arrays` | Time Arrays | step | no | `source_name`, `scan_name`, `time` |

Note that a result is filed under a *store key*, and for `time_arrays` that key is `times`. It
is the only one where the two differ, and nothing but the schema needs to know.

## What needs what

Every calculation starts from `time_arrays` — the sampled moments of every active scan, one
block per active source. Above that:

```text
time_arrays
├── interpolated_orbits          (a spacecraft's position at those moments)
│   └── telescope_positions      (where every station is, Earth rotation included)
│       ├── source_visibility    (is the source within this station's limits)
│       │   ├── az_el
│       │   ├── sun_angles
│       │   ├── parallactic_angle
│       │   ├── time_on_source
│       │   └── uv_coverage
│       │       └── baseline_projections
│       ├── mollweide_tracks
│       └── telescope_az_el      (pointing at a spacecraft)
│           └── telescope_visibility
└── beam_pattern                 (needs neither: a dish and a frequency)
```

You never write this down when calculating. Ask for the top of a branch and the branch comes
with it:

```python
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject

manipulator = ScheduleManipulator(ScheduleProject(name="Demo"))
ordered = manipulator.plan_for("calculate", ["baseline_projections"])

assert ordered == ["time_arrays", "interpolated_orbits", "telescope_positions",
                   "source_visibility", "uv_coverage", "baseline_projections"]
```

## The two about a spacecraft

`telescope_az_el` and `telescope_visibility` point a *ground station at a spacecraft*, which is
not the same geometry as pointing at a source and cannot reuse it. A source is far enough away
that every station sees it in the same direction; a spacecraft at twenty thousand kilometres is
not, and two stations a baseline apart point measurably differently at it.

They are the only calculations that need to be told what to aim at, and the catalogue says so —
from the columns, since a result recording a `target_code` is about something being tracked:

```python
response = manipulator.compute(obj=None, method="catalogue")
catalogue = response

needing_a_target = {entry["key"] for entry in catalogue if entry["needs_target"]}
assert needing_a_target == {"telescope_az_el", "telescope_visibility"}
```

Pass it as `target_telescope="RADIO"`, naming a space telescope in the observation.

## What each result depends on

Separately from *which calculation* needs which, each result declares which **parts of the
model** it reads. That is what makes staleness granular: editing a scan makes `uv_coverage`
stale and leaves `beam_pattern` alone.

```python
from pastrocore.base.data_structure import CalculatedDataStructure

assert CalculatedDataStructure.get_dependencies("uv_coverage") == (
    "telescopes", "sources", "scans", "frequencies")
assert CalculatedDataStructure.get_dependencies("beam_pattern") == ("telescopes", "frequencies")
```

## This page against the code

If the two disagree, this fails rather than you. `DOCUMENT` is this page's own text, which the
harness hands to every block.

```python
import re

documented = set(re.findall(r"^\| `([a-z_]+)` \|", DOCUMENT, re.M))

response = manipulator.compute(obj=None, method="catalogue")
catalogue = response
existing = {entry["key"] for entry in catalogue}

assert documented == existing, (
    f"this page and the code disagree: only here {sorted(documented - existing)}, "
    f"only in the code {sorted(existing - documented)}")
```
