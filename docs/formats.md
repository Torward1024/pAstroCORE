# Getting a schedule to a correlator

A schedule that stays inside pAstroCORE is a study. To be an observation it has to reach
software nobody here controls: **VEX**, which is what stations and most correlators read, and
**CFX**, which is what the ASC correlator reads.

This page is the map: every block those formats require, where its content comes from, and what
has to be asked of a user because the model does not know it. It is written before any exporter,
because deciding this once is most of what both formats need — and because the alternative is
finding out at a correlator, months later, that a file which looked right was not.

The examples it was written against are one experiment in both formats: `re03fr.vex` and
`RADIOASTRON_RAES03FR_C_...cfx` — RadioAstron AGN fringe survey, 2012-11-18, six ground stations
and the spacecraft.

## The three kinds of content

Everything in these files falls into one of three, and the distinction is what makes the work
finite:

| | |
| --- | --- |
| **The schedule** | What is observed, by whom, when, at what frequency. pAstroCORE knows all of it |
| **The station** | What the antenna and its electronics are: axis type, slew rates, recorder, BBC assignments. Facts about hardware, not about this observation |
| **The session** | Clocks, data file names, correlator output settings. Only known *after* observing |

pAstroCORE is a scheduling tool, so it owns the first, needs the second from somewhere, and has
no business with the third. **An exporter writes the first, is given the second, and leaves the
third out.**

## VEX, block by block

### What the model already answers

| Block | Comes from |
| --- | --- |
| `$GLOBAL` | one `ref $EXPER` |
| `$EXPER` | `Observation.code` as `exper_name`; nominal start and stop are the first and last active scan |
| `$SOURCE` | `Source`: `ra_h/m/s` and `de_d/m/s` as `ra`/`dec`, `name_J2000` and `alt_name` as the alternate names, `ref_coord_frame = J2000` |
| `$SITE` | `Telescope`: `name` as `site_name`, `code` as `site_ID`, `x/y/z` as `site_position`, `vx/vy/vz` as `site_velocity`, `site_type = fixed` |
| `$ANTENNA` | `mount_type` as `axis_type` (`AZIM` → `az : el`, equatorial → `ha : dec`) |
| `$FREQ` | `IF.frequency` as the sky frequency, `IF.bandwidth`, one `chan_def` per polarization **per sideband** |
| `$IF` | `IF.polarizations` as `R`/`L` per `if_def` |
| `$SCHED` | `Scan`: `start`, `duration` as `data_stop`, `source`, and the `telescopes` it names |
| `$STATION` | one `def` per telescope, referring to its `$SITE`, `$ANTENNA` and `$DAS` |
| `$MODE` | the distinct combinations of frequency setup across the scans |

### What the model was missing, and now has

One thing, and it was physics rather than paperwork:

**Sideband.** A `chan_def` names a net sideband, `U` or `L`:

```
chan_def = :  4828.00 MHz : L :  16.00 MHz : &CH01 : &BBC01 : &L_Cal;
chan_def = :  4828.00 MHz : U :  16.00 MHz : &CH03 : &BBC01 : &L_Cal;
```

Those are different pieces of spectrum — 4812–4828 MHz and 4828–4844 MHz — and pAstroCORE
could not tell them apart: an `IF` was a frequency and a bandwidth, which describes one of them
and not the other. The example experiment records **four** channels from what that model saw as
one band: two polarizations by two sidebands.

CFX says the same thing in its own words, which is what settled it:

```
IF = 4828.00, L, U        sky frequency, polarization, sideband
IF = 4828.00, L, L
```

So `IF` gained `sidebands` — **a list, exactly like `polarizations`**, and for the same reason:
one receiver setting at one sky frequency records what it records, and a band with both
sidebands and both circular polarizations is four channels while remaining one setting. The
alternative, a sideband *per* `IF`, would have meant two objects carrying one frequency and kept
in step by hand.

`get_band()` is the one place a sideband becomes numbers, and the overlap rule asks it rather
than adding a bandwidth itself. That is what catches the confusion this field exists for: 4828 U
and 4844 L are the same 16 MHz written two ways, and the rule now says so by name.

### What must be supplied, and cannot be derived

These are facts about a station's hardware. A scheduling model that invented them would be
writing a file that looks right and is not:

| | |
| --- | --- |
| `$DAS` | recorder and rack type — `Mark5B`, `Mark4`, number of drives |
| `$BBC` | which baseband converter each channel goes through, and to which IF |
| `$TRACKS` | recording format and fan-out — `MARK5B.4Ch2bit1to1` |
| `$PHASE_CAL_DETECT` | phase-cal tone spacing and which tones are detected |
| `$PROCEDURES` | the setup procedure a station runs before a scan |
| `axis_offset`, `antenna_motion` | axis offset in metres; slew rates and settling time |
| `site_position_epoch` | when the coordinates were measured |

**Nobody here can know these, and that is not a gap to be filled.** Which backend is installed
at a given station *today* is not published anywhere central, changes without notice, and is
known to the station and to whoever is running the session. A scheduling tool that wrote a
`$DAS` block would be stating something it cannot check, and a plausible wrong answer is worse
than an absent one — the correlator would take it.

#### The shape stays; the claims do not

Absent is not the same as missing, and this is the difference the exporter turns on:

> **The file has every block the format calls for. What we cannot state is left as an empty
> field or a commented template — never as a value.**

A VEX file that simply omits `$DAS` is a file whose structure the next tool has to invent. A
VEX file that *has* `$DAS`, with a `def` per station and its statements commented out, is a form
waiting to be filled — and filling it is what `drudg`, `vex2` and the people at the stations do
anyway, because they are the only ones who know what is in the rack this week.

Both halves of that are the format's own idiom, not an invention:

| | |
| --- | --- |
| **An empty field** | `chan_def = :  4828.00 MHz : U : ...` — the example's own band-ID field is empty in every line `sched` wrote |
| **A commented statement** | `*    ref $HEAD_POS = DiskVoid <= obsolete definition` — `sched` comments out a whole `ref` rather than dropping it |
| **An empty `def`** | `def DiskVoid; * ... irrelevant for Disk: empty def` `enddef;` — a `def` holding only comments is legal and `sched` writes them |

So **pAstroCORE writes a structurally complete VEX file and states only what it knows.** The
schedule, the sites, the antennas, the sources and the frequency setup carry real values; the
hardware blocks are present, empty, and annotated with what belongs in them. The exporter also
reports them by name, so nobody has to read the file to find out what is outstanding.

That is a normal way to work — `sched` writes complete files because it is given a station
catalogue that someone maintains; we are not that, and pretending otherwise is how a file that
looks right reaches a correlator.

A user who *does* have that information for their stations can supply it, and then it is
written. What is not acceptable is inventing it.

Two of these are close to things the model has and are worth taking properly:
`antenna_motion` is a slew rate, which a scheduler wants anyway for slew time between scans;
`axis_offset` matters to delay at the millimetre level. Neither is needed to *write* a first
VEX file, and both are worth adding when there is a reason beyond the file format.

### What is left out on purpose

`$HEAD_POS` and `$PASS_ORDER` are marked obsolete in the example file itself — `sched` writes
the blocks and comments out the `ref` lines as `<= obsolete definition`. They are not written at
all. `$ROLL` is tape-era too but is still referred to live, so it is written like the other
station blocks: present, empty, and annotated.

## CFX, and why it is nearly free after VEX

CFX carries a **subset** of the same schedule, in a different syntax:

| CFX | Same as |
| --- | --- |
| `[$SOURCE]` name, RA, DEC in degrees, EPOCH | `$SOURCE`, in decimal rather than sexagesimal |
| `[$skan]` start, duration, source, telescopes | `$SCHED`, one section per scan |
| `TLSC_PAR` x, y, z, vx, vy, vz, axis_offset, epoch, mount | `$SITE` and `$ANTENNA` together, one line |
| `IF = freq, pol, sideband` | `chan_def`, flattened |
| `ORB_FILE` | `SpaceTelescope.orbit_file` — **the space telescope is a station here**, `name = RASTRON` |

The rest of a CFX file is the *session*: `FILE00..NN` naming recorded data, `CLOCK` offsets
measured after the fact, `POLY_FILE`, and an `[$OUTPAR]` block of correlator settings. None of
it is a scheduler's to write, and a CFX exporter writes the sections above and leaves the file
to be completed by whoever runs the correlation.

**One thing CFX has that VEX does not need**: the spacecraft appears as an ordinary station with
an orbit file. pAstroCORE already models exactly that, and it is the reason CFX is worth doing
first for this lab even though VEX is the wider format.

## What this means for the work

1. ~~**`IF` gains a sideband.**~~ **Done** — `sidebands`, a list, defaulting to `["U"]`, which
   is what every band written before the field existed was implicitly taken to be.
2. **A VEX file is written whole and claims only what we know**, with the hardware blocks
   present but empty, annotated in place, and named in the report rather than guessed at.
3. **VEX went first.** CFX is smaller and its consumer is down the corridor, but the sideband
   work was VEX's, and the `$FREQ`/`$IF`/`$BBC` chain is where the difficulty is: doing it
   first meant doing the hard part while the map was still in mind. CFX is next.
4. **Neither is finished until a parser nobody here wrote accepts the file.** That is the
   exit criterion in the roadmap, and it is the whole point. It is not met yet: no third-party
   VEX parser is installable here, so what the suite does instead is read the file by VEX's
   punctuation and check the same reading against `re03fr.vex` and `s16tj07a.vex` — files
   written by `sched` and by people this project has never met. A checker calibrated on someone
   else's output is worth more than a round trip through our own reader and less than a real
   parser. The item stays open.

## Writing one

```bash
pastrocore-cli vex myproject schedule.vex
```

or **File → Export Schedule → VEX...**, which asks for a filename for one observation and a
directory for a project of several — a VEX file is one experiment, so several observations are
several files. Both print, or show, the same thing: what was written, what was left out, and
every block waiting for a station's answer.

In a program it is one request, like everything else:

```python
from astropy.time import Time

from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject

project = ScheduleProject(name="Survey")
project.create_item(item_code="RE03FR", observation_type="VLBI")
observation = project.get_observation_by_code("RE03FR")

observation.get_telescopes().create_telescope(
    code="Sv", name="SVETLOE", x=2730173.7626, y=1562442.7288, z=5529969.1054)
observation.get_telescopes().create_telescope(
    code="Bd", name="BADARY", x=-838200.9324, y=3865751.5664, z=4987670.908)
observation.get_sources().create_source(
    name="2230+114", ra_h=22.0, ra_m=32.0, ra_s=36.41, de_d=11.0, de_m=43.0, de_s=50.9)

# One receiver setting, both sidebands, both circular polarizations: four channels.
observation.get_frequencies().create_if(
    name="C", frequency=4828.0, bandwidth=16.0,
    polarizations=["RCP", "LCP"], sidebands=["U", "L"])

observation.get_scans().create_scan(
    name="scan1", start=Time("2012-11-18T13:50:00"), duration=570.0,
    source=observation.get_sources().get_items()[0],
    telescopes=list(observation.get_telescopes().get_items()),
    frequencies=list(observation.get_frequencies().get_items()),
    observation=observation)

core = ScheduleManipulator(project)
report = core.vex(obj=observation, method="export", path=str(TMP / "re03fr.vex"))

assert report["scans"] == 1
assert report["stations"] == ["Bd", "Sv"]
assert report["channels"] == 4          # 2 sidebands x 2 polarizations, from one IF
```

The report is not a courtesy. It names every block the file leaves open, so nobody has to read
the file to find out what is outstanding:

```python
outstanding = {entry["block"] for entry in report["to_complete"]}

assert "$DAS" in outstanding             # which recorder is in the rack this week
assert "$BBC" in outstanding             # which converter each channel goes through

written = (TMP / "re03fr.vex").read_text(encoding="utf-8")

assert "$DAS;" in written                # the block is there, and empty
assert "record_transport_type" in written    # with what belongs in it, commented out
```

A space telescope is excluded rather than dropped, because VEX 1.5 has no orbiting station —
and the report says so by name:

```python
observation.get_telescopes().create_space_telescope(code="RA", use_kep=False)
scan = observation.get_scans().get_items()[0]
scan.set_telescopes(list(observation.get_telescopes().get_items()), observation=observation)

report = core.vex(obj=observation, method="export", path=str(TMP / "again.vex"))

assert [entry["telescope"] for entry in report["excluded"]] == ["RA"]
assert "RA" not in report["stations"]
```

SKED is not mapped here. The example files available are not certainly sked output, and writing
an exporter against a guess is what this page exists to prevent.
