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
| 9 | Logic into `Super` classes | `ScheduleData` owns export, save, load and five queries. Export dialog 312 → 210 lines. Twelve GUI modules reached for the model; **two remain and both are decided, not owed** |
| -- | One catalogue (A5) | Nine hardcoded copies across three dialogs became one request. The manipulator works out what it offers from its own handlers -- MSB 1.2.0 -- so adding a calculation touches the calculator and the schema and nothing in the interface, which a test asserts by adding one |
| -- | Freshness | A result records what it was computed from and says when its inputs have changed. Three answers: stale, current, unknown |

Details of any of these are in `CHANGELOG.md` and in the commit that made the change.

## Before 1.0

| | Item | Exit criterion | Size |
| --- | --- | --- | --- |
| ~~1~~ | ~~**D9**~~ | **Done.** The frame is the authority: `scan_count`, `start_time` and `end_time` are computed where the frame and its metadata are both in hand, so a caller cannot supply a wrong value -- whatever it passes is replaced, on the way into memory and on the way to disk alike. Kept beside the parquet rather than removed, because reading them without reading the result is worth more than having them nowhere. Nothing written contains `NaN`: unrepresentable numbers become `null` and the write uses `allow_nan=False`, checked with a strict parser rather than the lenient one that wrote it | -- |
| ~~1~~ | ~~**R4**~~ | **Done.** `pyproject.toml` with the version in one place -- `pastrocore/__init__.py`, since MSB tagged a release with one of its two numbers bumped and PyPI refused the build. `pip install .` gives a `pastrocore` command, and `requirements.txt` installs the project rather than repeating its dependencies. The packaging exposed the real defect: every path the application used was relative to the directory it was started from, so an install found no catalogues and wrote settings wherever the user happened to be. The catalogues ship inside the package; the settings live in one per-user file, adopting a `settings.pastro` left in a working directory once so nobody's is lost; a catalogue the user chose is kept, and one that has been deleted falls back to the shipped one with a line in the log rather than an empty application | -- |
| ~~2~~ | ~~**R5**~~ | **Done.** No pull request is open. The last, #39, merged with 0.4.0; nothing has been left without a decision since | -- |
| ~~3~~ | ~~**R1**~~ | **Done.** 0.9.0, tagged and released, with a changelog saying what changed and an upgrading table saying what to do about it. The version is stated once and the About dialog and the README are held to it by tests -- 0.8.0 shipped with the form still saying 0.7.0 | -- |
| 1 | **M1** -- run the plan's independent branches at once | **Measured: 1.30x** (1.885 s against 1.453 s, median of five alternating rounds over the fixture project's thirteen-step plan). The ceiling is what the fan costs: three steps must be sequential and nine wait only on those. Taken, because it is one flag on a request rather than a mechanism. Cancellation and the skipping of a failed branch must behave as they do in sequence, which a test asserts | Hours |
| 2 | **M2** -- honest timing, on an interceptor | Every calculation's own duration is measured where every request passes, not estimated by the caller. Available afterwards as a table. Progress advances when a step **finishes**, so a bar cannot sit at 80% through the longest step of the run | Hours |
| 3 | **M4** -- the run says what it did, in one place | Today a run ends in one message box saying everything worked, and everything else is in `output.log`. **Neither a dialog per event nor silence:** one report, listing every step with its time and its outcome, reachable after the run rather than only during it. A failure is visible in the window without opening a log file | Days |
| 4 | **M3** -- the request journal reaches the interface | A session's calculations are recorded and can be replayed against another project. `RequestJournal` exists in MSB and is exercised by one test here; nothing in the application writes to it | Days |
| 5 | **R3** -- documentation | `docs/` for somebody who has never seen the project: installing, running, adding an observation, reading a result, each with a runnable example | Days |
| 6 | **G2** then **G3** -- profile the interface, then act | A measured list of what is actually slow, with numbers; each finding fixed or recorded as not worth fixing. **The instrument is MSB's, not ours**: `RequestMetrics` counts and times every request per operation and `cache_statistics()` says what the caches are doing, so the measuring costs one interceptor rather than a harness. Two candidates already have a name: whether `fingerprint()` -- one serialisation per freshness check -- shows up at all, and whether `revision` would answer the same question for less | Days |

**M1--M4 are one sentence: use what MSB 1.5.0 already has.** The pipeline, the interceptors and
the journal are built and tested there; here they are reached by one caller each. **Measure
before deciding** applied to M1 and the number came back modest but real -- parallel
serialization was measured *slower* twice in this project's history, so the claim was not
assumed.

**M2 and M4 are the same mechanism seen from two ends.** The interceptor sits where every
request passes: it already carries progress and cancellation, and timing is the third thing it
can see without anybody instrumenting a calculation. What M4 shows is what M2 measures.

**A5 is the dependency graph in disguise, and worth saying so.** A result's schema already
declares `depends_on` -- which *parts of the model* it reads, which is what makes freshness
granular. A5 adds `requires`: which *other results* a calculation needs. Those are the two edge
types of one graph, and the second is the one MSB's P1 will schedule on. Declaring it for a
dialog's benefit is the same declaration that later says what may run in parallel and what a
change invalidates. So this is not a GUI convenience with a graph hidden in it; it is the node
table and one edge set, arriving early because a dialog needed them first.

**1.0 is reached when**: all of the above hold, the suite is green on CI, a project saved by 1.0
opens in 1.0.

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
| L2 | Scripts inside the application -- **editing** requests, not only replaying them | L1, and M3 first. Viewing, saving, loading and replaying a journal is M3 and belongs before 1.0; *editing* a request in a window is a scripting environment, which is its own product and needs deciding what a half-edited plan may do |
| L3 | Client-server | L1. The hard parts are storage, identity, and what a long calculation looks like to a caller who is not watching |
| T4 | Knowing *which* results a change invalidates | MSB's `describe_model()` and `dependents_of()` -- which type holds which, read from the annotations. `depends_on` says which *parts* a result reads; the model graph says what reaching a part reaches, and between them a change names the results it invalidates |
| M6a | ~~Running independent calculations concurrently~~ | **Done before 1.0, as M1.** Measured 1.30x |

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
