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

### What the model does not know and should

One thing, and it is physics rather than paperwork:

**Sideband.** A `chan_def` names a net sideband, `U` or `L`:

```
chan_def = :  4828.00 MHz : L :  16.00 MHz : &CH01 : &BBC01 : &L_Cal;
chan_def = :  4828.00 MHz : U :  16.00 MHz : &CH03 : &BBC01 : &L_Cal;
```

Those are different pieces of spectrum — 4812–4828 MHz and 4828–4844 MHz — and pAstroCORE
cannot presently tell them apart: an `IF` is a frequency and a bandwidth, which describes one
of them and not the other. The example experiment records **four** channels from what this
model would call one band: two polarizations by two sidebands.

CFX says the same thing in its own words, which is what settles it:

```
IF = 4828.00, L, U        sky frequency, polarization, sideband
IF = 4828.00, L, L
```

So `IF` gains a sideband. It is not a format detail: it says which 16 MHz of sky was recorded,
and the answer changes what a baseline actually measures.

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

**Where they come from is a decision, not a lookup**, and the honest options are: a per-station
file the user maintains, or a station catalogue in the same spirit as `catalogs/telescopes.dat`.
The second is better — it is one place, shared between experiments, and it is how `sched` and
`sked` have always worked. Either way an exporter **refuses** rather than guesses: a missing
`$DAS` is a file the correlator cannot use, and saying so at export time costs a minute.

Two of these are close to things the model has and are worth taking properly:
`antenna_motion` is a slew rate, which a scheduler wants anyway for slew time between scans;
`axis_offset` matters to delay at the millimetre level. Neither is needed to *write* a first
VEX file, and both are worth adding when there is a reason beyond the file format.

### What is left out on purpose

`$HEAD_POS`, `$PASS_ORDER` and `$ROLL` are marked obsolete in the example file itself, written
by `sched` as `<= obsolete definition`. They are not written.

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

1. **`IF` gains a sideband.** One field, with a migration, because every existing project has
   bands that do not say which half of the spectrum they are.
2. **Station hardware comes from a catalogue**, and an exporter refuses when it is missing
   rather than inventing it.
3. **CFX first or VEX first is a real choice.** CFX is smaller, its consumer is down the
   corridor, and the space telescope is already modelled. VEX is the one that reaches everyone
   else, and its `$FREQ`/`$IF`/`$BBC` chain is where the difficulty lives.
4. **Neither is finished until a parser nobody here wrote accepts the file.** That is the
   exit criterion in the roadmap, and it is the whole point.

SKED is not mapped here. The example files available are not certainly sked output, and writing
an exporter against a guess is what this page exists to prevent.
