# The calculations

Seventeen of them. Thirteen are things you ask for; four are steps the others need, which is why
they are not offered in the interface — being asked to choose "Telescope Positions" means nothing
to somebody who wants a uv plot.

None of this list is written down in the code. It is worked out from the calculations that
exist, so **adding one makes it appear here, in the interface, and in the exporter, without any
of the three being edited**. The block at the bottom of this page fails if this table and the
code disagree.

## What each produces

| Key | Shown as | Offered | Drawn | Columns of the result |
| --- | --- | --- | --- | --- |
| `az_el` | Az/El | yes | yes | `time`, `source_name`, `scan_name`, `telescope_code`, `az`, `el` |
| `baseline_projections` | Baseline Projections | yes | yes | `time`, `source_name`, `scan_name`, `baseline`, `projection` |
| `baseline_sensitivity` | Baseline Sensitivity | yes | yes | `time`, `scan_name`, `source_name`, `baseline`, `if_name`, `frequency`, `bandwidth`, `scan_duration`, `duration`, `sefd_1`, `sefd_2`, `noise_1s`, `noise`, `flux`, `flux_basis`, `snr`, `detected`, `min_duration`, `reason` |
| `beam_pattern` | Beam Pattern | yes | yes | `telescope_code`, `theta`, `pattern` |
| `mollweide_tracks` | Mollweide Tracks | yes | yes | `time`, `scan_name`, `telescope_code`, `lon`, `lat` |
| `parallactic_angle` | Parallactic Angle | yes | yes | `time`, `source_name`, `scan_name`, `telescope_code`, `parallactic_angle` |
| `sefd` | SEFD | yes | yes | `telescope_code`, `if_name`, `frequency`, `bandwidth`, `sefd`, `origin`, `tsys`, `effective_area`, `efficiency`, `basis`, `reason`, `filled` |
| `sefd_track` | SEFD Track | yes | yes | `time`, `scan_name`, `source_name`, `telescope_code`, `if_name`, `frequency`, `elevation`, `airmass`, `opacity`, `attenuation`, `tsys`, `gain`, `sefd_zenith`, `sefd`, `basis`, `reason` |
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
│       │   │   └── baseline_sensitivity   (with sefd_track)
│       │   └── uv_coverage
│       │       └── baseline_projections
│       ├── mollweide_tracks
│       ├── sefd_track           (with sefd: the SEFD where the source stands)
│       └── telescope_az_el      (pointing at a spacecraft)
│           └── telescope_visibility
├── beam_pattern                 (needs neither: one curve per dish)
└── sefd                         (needs no samples at all: a station and a band)
```

`sefd` hangs off nothing — it is the one calculation that reads no geometry, so it is drawn under
the root for want of anywhere else.

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
response = manipulator.inspect(obj=None, method="catalogue")
catalogue = response

needing_a_target = {entry["key"] for entry in catalogue if entry["needs_target"]}
assert needing_a_target == {"telescope_az_el", "telescope_visibility"}
```

Pass it as `target_telescope="RADIO"`, naming a space telescope in the observation.

## Sensitivity and detection

Three of them answer *how well would this be seen*, and each says where its numbers came from
instead of producing a number on its own.

**`sefd`** is a station's system equivalent flux density in a band. What was measured comes first
— a station's tables are rows of `(f_min, f_max, value)`, so a measurement says which frequencies
it holds for — and otherwise it is `2 k Tsys / A_eff`, with the effective area from the dish, what
its illumination leaves, and what its surface leaves at that wavelength by Ruze's formula:

```python
from pastrocore.base.telescope import Telescope

dish = Telescope(code="EF", name="Effelsberg", diameter=100.0, surface_accuracy=500.0,
                 system_temperature_table=[(4500.0, 5500.0, 25.0)],
                 surface_efficiency_table=[(4500.0, 5500.0, 0.55)])

estimate = dish.get_sefd_estimate(5000.0)
assert round(estimate["sefd"], 1) == 16.0
assert estimate["origin"] == "parameters"
assert estimate["basis"] == "measured over 4500-5500 MHz"

# Nothing covers the water line, and nothing is made up to cover it.
assert dish.get_sefd_estimate(22235.0)["sefd"] is None
assert dish.get_sefd_estimate(22235.0)["reason"] == (
    "no SEFD and no system temperature covers 22235 MHz")
```

Asked with `fill=True`, it writes what it computed into the station's own SEFD table, as a row
covering the band, and never over a row that was measured.

The flux it is compared against is the source's, and a spectrum is a power law rather than a
straight line:

```python
from pastrocore.base.sources import Source

source = Source(name="3C 286", flux_table={1400.0: 14.9, 5000.0: 7.3})

between = source.get_flux_estimate(2300.0)
assert round(between["flux"], 2) == 11.28
assert between["basis"] == "power law between 1400 and 5000 MHz"

# Beyond what was measured, only with a spectral index.
assert source.get_flux_estimate(22000.0)["flux"] is None
```

**`sefd_track`** follows that SEFD along every scan, on the same time grid as everything else: the
SEFD a station quotes is the one at zenith, through the atmosphere there, and away from the zenith

```text
SEFD(el) = SEFD_zenith * e^(tau0 (A - 1)) * Tsys(el) / Tsys_zenith * g(90) / g(el)
Tsys(el) = Tsys_zenith + T_atm (e^-tau0 - e^(-tau0 A)),   A = 1 / sin(el)
```

— the source dimmed through more air, the system warmed by what more air emits, and the dish's
gain where it is pointing. **None of that is a property of the station.** The weather is the day's
rather than the dish's, so it is a parameter of the calculation and the same at every station; a
gain curve is the dish's but belongs to no band on its own, so it is given by station code. They
are checked the way a station's tables are, and a result records what it was computed with:

```python
from pastrocore.super.schedule_calculator import ScheduleCalculator

weather = {"opacity": [[900.0, 1100.0, 0.05]], "t_atm": 270.0,
           "gain_curve": {"EF": [[900.0, 1100.0, [0.9, 0.004, -0.00003]]]}}
opacity, t_atm, curves = ScheduleCalculator._elevation_parameters(weather)

assert opacity == [[900.0, 1100.0, 0.05]] and t_atm == 270.0
assert curves["EF"] == [[900.0, 1100.0, [0.9, 0.004, -0.00003]]]
```

A curve is taken as the ratio `g(90) / g(el)`, so how it was normalised does not matter: one
peaking at 1 at 50 degrees and the same curve doubled give one answer. What is not given is not
applied, and the `basis` column says which of the two it was. An opacity with nothing to say how
warm that air is would be half a correction, so it is refused rather than half applied:

```python
# raises: ValueError
ScheduleCalculator._elevation_parameters({"opacity": [[900.0, 1100.0, 0.05]]})
```

**`baseline_sensitivity`** puts the two together for each scan and each pair of stations. The time
is the time *both* stations see the source — the overlap of their `time_on_source` blocks, which
is why the row carries the scan's length beside it — and the noise adds up over that time rather
than being taken at one SEFD:

```text
1 / sigma^2 = eta^2 2 dnu P sum(dt / (SEFD1(t) SEFD2(t)))
```

with `eta` what the recording keeps of the signal (2/pi at one bit, 0.8825 at two), `dnu` the
band's width and `P` its polarizations. With the SEFDs constant this is the radiometer equation
for the whole scan, `sqrt(SEFD1 SEFD2) / (eta sqrt(2 dnu tau P))` — which is how it is checked
against a published case: two VLBA antennas of 210 Jy at 6 cm, 128 MHz, one minute and `eta` 0.8
reach 2.1 mJy, as the VLBA's status summary says.

A detection is `snr >= threshold`, five by default, and `min_duration` is the shortest scan that
would reach it at the SEFDs this one had. The bands of a scan are reported one by one and again
together under `if_name` `all`, where signal-to-noise adds in quadrature. The source is taken as
unresolved — the correlated flux is the whole flux — and the result says so. Nothing that cannot
be worked out is guessed: a station with no SEFD, a source with no flux at that frequency, two
stations that never see it together, all leave the value empty and name the reason.

**What each takes is asked, not listed.** A parameter that changes an answer is recorded with
it — otherwise freshness could not tell one answer from another — so the catalogue reads a
calculation's parameters off what its result records, and the calculation dialog offers a
detection threshold beside baseline sensitivity and not beside a beam pattern:

```python
entries = {entry["key"]: entry for entry in manipulator.inspect(obj=None, method="catalogue")}

assert {"threshold", "bits", "opacity", "t_atm", "gain_curve"} <= set(
    entries["baseline_sensitivity"]["parameters"])
assert entries["sefd"]["parameters"] == ["fill"]
assert entries["beam_pattern"]["parameters"] == []

# The recordings on offer are the calculator's, with what each keeps of the signal.
assert [row["bits"] for row in manipulator.inspect(obj=None, method="recording")] == [1, 2]
```

A run that refuses a step says why in its report — an opacity with no air temperature is named
there, not only in the log.

Each of the three draws itself. `sefd` is a bar per station and band, on a log scale, with what
was computed hatched and what was measured plain; `sefd_track` is a line per scan with the zenith
behind it, so what the elevation costs is the distance between the two; `baseline_sensitivity` is
a grid of baselines by scans, coloured by signal-to-noise with the threshold marked on the colour
bar, and every cell that misses it crossed out.

## What each result depends on

Separately from *which calculation* needs which, each result declares which **parts of the
model** it reads. That is what makes staleness granular: editing a scan makes `uv_coverage`
stale and leaves `beam_pattern` alone -- and so does editing a band, because a beam is one curve
per dish that is given a frequency only when it is drawn (`sin(theta) = lambda sin(t) / pi`, with
`t` the stored `theta`).

```python
from pastrocore.base.data_structure import CalculatedDataStructure

assert CalculatedDataStructure.get_dependencies("uv_coverage") == (
    "telescopes", "sources", "scans", "frequencies")
assert CalculatedDataStructure.get_dependencies("beam_pattern") == ("telescopes",)
```

## This page against the code

If the two disagree, this fails rather than you. `DOCUMENT` is this page's own text, which the
harness hands to every block.

```python
import re

documented = set(re.findall(r"^\| `([a-z_]+)` \|", DOCUMENT, re.M))

response = manipulator.inspect(obj=None, method="catalogue")
catalogue = response
existing = {entry["key"] for entry in catalogue}

assert documented == existing, (
    f"this page and the code disagree: only here {sorted(documented - existing)}, "
    f"only in the code {sorted(existing - documented)}")
```
