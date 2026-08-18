# pAstroCORE roadmap

**1.0 shipped.** What follows is what comes next, and what was decided against.

Every item has an **exit criterion**: a sentence that is true or false. An item is finished when
its criterion holds, not when it feels tidy. The failure mode of a project like this is not
running out of things to do -- it is never running out.

Three rules that earned their place the hard way:

- **Measure before deciding.** Numbers here were taken, not estimated. Twice a plausible
  optimisation was measured *slower* and dropped.
- **Build the check before the change.** Twice a change was made to code nothing exercised, and
  twice it broke something the suite could not see.
- **Take it from MSB.** If the framework has it, use it; if it is missing there and belongs
  there, add it there. Three of MSB's releases came out of following that during 1.0.

## Next

Nothing here is scheduled. In rough order of what would help most:

| | Item | Why it is next |
| --- | --- | --- |
| ~~**L2**~~ | ~~Editing requests~~ | **Done, in the half that matters.** A session is checked whole before any of it runs, so an edited file with one bad step runs none of them -- `pastrocore-cli check` says what is wrong, and both the command line and the panel refuse with the list rather than the first thing that broke. Everything it checks against is derived: which operations exist, which methods each has, and what each reads. An attribute no handler reads is a **warning**, since `accepts` is a lower bound by construction. What is left is an editor inside the window, and a text editor is a better one |
| ~~**L1**~~ | ~~A command line~~ | **Done.** `pastrocore-cli` with `info`, `calculations`, `run`, `export` and `replay` -- 230 lines, every command one request. It imports neither `pastrocore.gui` nor Qt, which a test asserts and a second one measures by running it in a process and looking at `sys.modules`. It also earned its keep immediately: replaying a session that contained a *run* called a string, because a journal records a callable as `<function>` and the handler called it back |
| **N1--N4** | Analysis | A calculation finishes and that is the end of it. Visibility is a boolean per station per moment, and nobody can ask when, for how long, or where the gaps are |
| **R6** | A project as one file | How a project reaches a colleague or a bug report |
| **T4** | Which results a change invalidates | `depends_on` says which *parts* a result reads; MSB's model graph says what reaching a part reaches |
| **G1** | One stylesheet | Attempted and reverted once. It is authoring, not extraction |

The sections below are the detail of those, plus the formats -- which are a project of their
own, and which nothing else waits on.

## Done

| Release | What it shipped |
| --- | --- |
| **0.4.0** | A test suite where there was none, CI, hygiene, the calculations, MSB 1.1.1. Over 500 lines removed |
| **0.5.0** | A project became a directory; results are parquet, read lazily and capped |
| **0.5.1** | A project holding a space telescope could not be opened |
| **0.6.0** | The dialogs ask for a folder; the single-file format removed |
| **0.7.0** | A calculation reaches the disk when it is made, in a per-session scratch directory, with recovery |
| **0.8.0** | Adding a calculation stops at the calculator: one catalogue, derived. A space telescope can be pointed at. A result says when its inputs moved |
| **0.9.0** | `pip install .` gives a command. Running calculations is a plan the backend builds. Start-up 4.0 s to 1.4 s |
| **1.0.0** | Everything below |

### What 1.0 required, and what each cost

| | Item | Outcome |
| --- | --- | --- |
| D9 | The frame is the authority | `scan_count`, `start_time` and `end_time` are computed where the frame and its metadata are both in hand, so a caller cannot supply a wrong one. Nothing written contains `NaN` |
| R4 | Packaging | `pip install .` gives a `pastrocore` command; the version is stated once. It exposed the real defect: every path was relative to the directory the application was started from, so an install found no catalogues and wrote settings wherever the user happened to be |
| R5 | Stale pull requests | None open |
| R1 | Release | 0.9.0, tagged, with an upgrading table |
| M1 | Independent branches run at once | **1.30x** measured (1.885 s against 1.453 s, median of five alternating rounds over a thirteen-step plan) |
| M2 | Honest timing | Measured on the interceptor, per step. Progress advances when a step *finishes* |
| M4 | The run says what it did | One report, a row per step with its time and outcome, kept for **Tools → Last Run Report** |
| M3 | The journal reaches the interface | **Tools → Session**: look at it, write it to a file, replay it against another project. Possible because MSB 1.6.0 stopped holding what it recorded |
| G3a | Every result was written twice | `times` 10 stores → 1, `telescope_positions` 4 → 1 |
| R3 | Documentation | Four pages, and **every Python block on them is executed by the suite** |
| G2/G3 | Profile the interface | Measured: window 136 ms, explorer 0.4 ms, observation tab 4.4 ms warm, dialogs 4--36 ms. 191 `inspect` calls cost 4.1 ms between them. Nothing needs fixing, and now there is evidence rather than an impression |

### What was found on the way

Each of these was silent, and each is now a test:

| | |
| --- | --- |
| Closing the window destroyed the day's calculations | The scratch was discarded on every clean close |
| Every File → New Project and Open orphaned a scratch | Which the next start offered to recover |
| Calculating for a whole project produced an empty frame | Iterating a project yields its *names* |
| A source going inactive left `time_arrays` looking current | Found by checking `depends_on` against what MSB derives the handler to touch |
| A run with a failed step reported complete success | A slot defined twice; PySide drops the arguments the winner does not accept |
| An observation labelled "12 stale" could not be opened | The explorer looked it up by its label |
| Exporting pictures failed for every calculation | `self.manipulator` where the attribute is `_manipulator` |
| Four rules guarded the constructor and nothing else | `set` and `from_dict` walked past them |

Details of any of these are in `CHANGELOG.md` and in the commit that made the change.

### Three MSB releases came out of it

| | |
| --- | --- |
| **1.5.0** | `accepts` -- the attribute keys a handler reads, derived. It replaced five hand-written lists here and found a plot missing from two of them |
| **1.6.0** | A journal is a record, not a retainer. An entry held the live object *and* the response, so it pinned every result frame it had seen |
| **1.7.0** | `plan_for` -- the six lines every application writes to turn "what I want" into "what to run, in order" |

Ten of MSB's releases have come out of this project in total.

## The detail

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
