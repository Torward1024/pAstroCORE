# pAstroCORE roadmap

What is done, what is left before 1.0, and what waits until after it.

Every item has an **exit criterion**: a sentence that is true or false. An item is finished when
its criterion holds, not when it feels tidy. The failure mode of a project like this is not
running out of things to do -- it is never running out.

Two rules that earned their place the hard way:

- **Measure before deciding.** Numbers here were taken, not estimated.
- **Build the check before the change.** Twice a change was made to code nothing exercised, and
  twice it broke something the suite could not see.

## Done

| Release | What it shipped |
| --- | --- |
| **0.4.0** | A test suite where there was none, CI, hygiene, the calculations, MSB 1.1.1. Over 500 lines removed |
| **0.5.0** | A project became a directory; results are parquet, read lazily and capped |
| **0.5.1** | A project holding a space telescope could not be opened |
| **0.6.0** | The dialogs ask for a folder; the single-file format removed |
| **0.7.0** | A calculation reaches the disk when it is made, in a per-session scratch directory, with recovery |

| Stage | | Outcome |
| --- | --- | --- |
| 0 | Safety net | The saved project *is* the reference: clear its results, recompute, compare. Tolerance 5e-4, measured |
| 1 | Hygiene | 21 918 duplicated lines removed; missing dependencies declared |
| 2 | Calculations | Redundant recomputation removed: **730x** (0.4 ms against 292.3 ms) |
| 3 | Adopt MSB | Three MSB releases came out of it: 1.0.1, 1.1.0, 1.1.1 |
| 4 | Storage | Model **5.1 KB against 230.5 KB**; opening reads no results; one filtered draw **9.2x faster**; memory over 60 observations **407 MB → 71 MB**; results written when calculated, per-session scratch, recovery offered |
| 6 | Space telescope as a target | `telescope_az_el` and `telescope_visibility`, chosen by name. Checked against the law of cosines, not against a stored number |
| 9 | Logic into `Super` classes | `ScheduleData` owns export, save, load and four queries. Export dialog 312 → 210 lines. Twelve GUI modules reached for the model; **two remain and both are decided, not owed** |
| -- | Freshness | A result records what it was computed from and says when its inputs have changed. Three answers: stale, current, unknown |

Details of any of these are in `CHANGELOG.md` and in the commit that made the change.

## Before 1.0

| | Item | Exit criterion | Size |
| --- | --- | --- | --- |
| 1 | **D9** -- metadata disagrees with its data | Metadata records only what the frame cannot say; anything derivable is derived. No file the application writes contains `NaN`, asserted with a strict parser rather than the lenient one that wrote it | Hours |
| 2 | **R4** -- packaging | `pyproject.toml`, an entry point, the version in one place. `pip install .` gives a working command | Hours |
| 3 | **R1** -- release | Tagged, with a changelog saying what changed and what to do about it | Hours |
| 4 | **R3** -- documentation | `docs/` for somebody who has never seen the project: installing, running, adding an observation, reading a result, each with a runnable example | Days |
| 5 | **R5** -- stale pull requests | None open without a decision recorded | Hours |
| 6 | **G2** then **G3** -- profile the interface, then act | A measured list of what is actually slow, with numbers; each finding fixed or recorded as not worth fixing | Days |

**1.0 is reached when**: all of the above hold, the suite is green on CI, a project saved by 1.0
opens in 1.0.

Two known facts that shape D9, both measured on a real project: `times.parquet` held 288 rows
over one scan beside metadata claiming `scan_count: 0`, because three metadata fields restate
what the frame already says and the two drifted. And `json.dumps` writes bare `NaN`, which is
not valid JSON -- such a file is readable by us and by nothing else.

## After 1.0

### Analysis

A calculation finishes and that is the end of it. Visibility of a space telescope is a boolean
per station per moment, and the questions anyone has of it -- when, for how long, where are the
gaps, which station covers another's -- cannot be asked.

**Scope rule, because "analysis" has no natural end:** an operation earns its place when it
answers a question asked *while scheduling*. Not by being a statistic that exists.

Most of these are one primitive: runs of consecutive `True` in a boolean column, grouped by
station.

| # | Item | Exit criterion |
| --- | --- | --- |
| N1 | **`ScheduleAnalyzer`** -- runs of a boolean | Windows, gaps, longest run and total, as a frame of intervals |
| N2 | Coverage across stations | Visible from any, from all, from at least two -- without joining frames by hand |
| N3 | Summaries a scheduler reads | Time on source per station, fraction of the scan usable, the worst gap |
| N4 | The same over a whole project | "Which nights are usable" without a loop in the interface |

Out of scope: fitting, forecasting, anything that recommends a schedule.

### Interface

| # | Item | Exit criterion |
| --- | --- | --- |
| G1 | One stylesheet, in a file | No `setStyleSheet` in the codebase; all 22 forms render identically, checked by pixels |
| G1a | The stylesheet editable from Preferences | Applied to the `QApplication`, so dialogs created later see it; changes without a restart |
| G4 | A most-recently-used list | Survives a restart; a missing entry is removed when clicked |
| G5 | The visualizer configured from a file, with its own tab | Plot appearance changes without a restart; the file is editable by hand |

G1 was attempted and reverted. 209 styled widgets collapse to 25 distinct sheets, but all 22
forms carry a sheet on their *top-level* widget, which reaches every child -- moving that to
application level changes which rule wins, and not one form matched what it replaced. **It is
authoring, not extraction**, and the pixel harness is the acceptance test.

### Formats

A project of its own. Three contracts with software nobody here controls. Nothing before 1.0
depends on any of it.

A schedule in VEX is an observation rather than a study. **CFX** is what the ASC correlator
reads. **SKED** is what much geodetic VLBI is scheduled in.

| # | Item | Exit criterion |
| --- | --- | --- |
| V1 | Map the model onto the VEX blocks | Every required block, where its content comes from, what must be asked of the user. **The shared reading of the model is decided here**, since it is most of what CFX and SKED need |
| V2 | Export ground-telescope schedules | A file a VEX parser accepts, for a project the lab ran |
| V3 | Validate against a parser we did not write | Not optional. A file that looks right to its author is how you learn months later at a correlator that it was not |
| V4 | Characterization tests | A change that alters the file fails the build |
| V6 | Decide what happens to what the model cannot represent -- **before V5** | An importer that drops what it does not model, feeding an exporter that writes only what the model knows, is a lossy round trip that looks lossless. Keep unrecognised blocks verbatim, or refuse to export a lossily imported file |
| V5 | Import VEX | A real file from an experiment this lab did not schedule loads and can be analysed. Export-then-import does **not** replace V3: a round trip passes when reader and writer are wrong the same way |
| X1 | **`ScheduleCFX`** | A file the ASC correlator accepts, checked against a real one |
| K1 | **`ScheduleSKED`** | A SKED file a parser accepts, and a real one read back |
| A2 | One `Super` per format | Nothing about any format appears in `ScheduleData` |

Order: VEX, CFX, SKED. Space telescopes out of scope for V2.

### Reaching it from somewhere other than the window

| # | Item | Needs |
| --- | --- | --- |
| R6 | Import and export a project as one file | How a project reaches a colleague or a bug report |
| L1 | A command-line version | R4's packaging. Thin, now that operations exist to request |
| L2 | Scripts inside the application | L1 and MSB's `RequestJournal`. A journal that replays every calculation and saves nothing is a rehearsal -- which is why save became an operation first |
| L3 | Client-server | L1. The hard parts are storage, identity, and what a long calculation looks like to a caller who is not watching |
| T4 | Knowing *which* results a change invalidates | MSB's P1 dependency graph -- the same graph that lets independent calculations run at once |
| M6a | Running independent calculations concurrently | Also P1 |

## Considered and rejected

| | Decision |
| --- | --- |
| Packing a saved project into one file | **No.** Zip saves 0.6% -- parquet is already compressed -- and opening becomes 46x slower. The real want is an export: R6 |
| A time window that is not a scan | **No.** A scan already means "these telescopes, this window". A second way to say *when* spreads to every calculation, tab and exporter |
| An asynchronous surface for long calculations | **Not needed.** `CalculationThread` already runs off the GUI thread with cancellation and progress; asyncio would need a bridge to Qt's loop and lose the cancellation |
| Parallel serialization | Measured slower: 1.69x with `asyncio.gather`, 1.11x with threads |
| Moving save and load into MSB now | Right eventually, recorded there as **P18**, shipping with P1. Half a mechanism before P1 is designed leaves the graph built around the wrong shape |

## Not in scope

Scheduling *optimisation* -- deciding what to observe. This describes and checks schedules; it
does not propose them.
