# pAstroCORE roadmap

**1.3 shipped.** What follows is what comes next, and what was decided against.

Every item has an **exit criterion**: a sentence that is true or false. An item is finished when
its criterion holds, not when it feels tidy. The failure mode of a project like this is not
running out of things to do -- it is never running out.

Four rules that earned their place the hard way:

- **Measure before deciding.** Numbers here were taken, not estimated. Twice a plausible
  optimisation was measured *slower* and dropped.
- **Build the check before the change.** Twice a change was made to code nothing exercised, and
  twice it broke something the suite could not see. G1 was only possible the second time because
  the pixel harness was written first -- and it caught a real mistake within the hour.
- **A characterization test cannot tell you the answer was always wrong.** It compares against
  what the code used to produce. Where an answer can be known independently, check against
  *that*: the orbit interpolation was out by up to 846 km with a green suite throughout.
- **Take it from MSB.** If the framework has it, use it; if it is missing there and belongs
  there, add it there. Sixteen of MSB's releases have come out of following that.

## Next

Nothing here is scheduled. In rough order of what would help most:

| | Item | Why it is next |
| --- | --- | --- |
| **N1--N4** | Analysis | A calculation finishes and that is the end of it. Visibility is a boolean per station per moment, and nobody can ask when, for how long, or where the gaps are. It is also the input a scheduling optimiser needs |
| **G1a** | The stylesheet editable from Preferences | The file exists and is loaded; changing it still means restarting |
| **G6** | The nine visualization tabs share a base | ~2500 lines over nine files with the same nine methods each -- but no method is byte-identical, so they are parallel variations rather than copies. It needs parameterising, not lifting |
| **L3** | Client-server | The last caller. Storage, identity, and what a long calculation looks like to a caller who is not watching |
| **Formats** | VEX, CFX, SKED | A project of their own; nothing else waits on them |

## Done

| Release | What it shipped |
| --- | --- |
| **0.4.0** | A test suite where there was none, CI, hygiene, the calculations, MSB 1.1.1. Over 500 lines removed |
| **0.5.0** | A project became a directory; results are parquet, read lazily and capped |
| **0.6.0** | The dialogs ask for a folder; the single-file format removed |
| **0.7.0** | A calculation reaches the disk when it is made, in a per-session scratch directory, with recovery |
| **0.8.0** | Adding a calculation stops at the calculator: one catalogue, derived. A space telescope can be pointed at. A result says when its inputs moved |
| **0.9.0** | `pip install .` gives a command. Running calculations is a plan the backend builds. Start-up 4.0 s to 1.4 s |
| **1.0.0** | The parts written under time pressure put in order, one measured stage at a time |
| **1.1.0** | **L1, L2.** `pastrocore-cli` -- the backend's second caller, which is the claim 1.0 was built on. A session is checked whole before any of it runs |
| **1.2.0** | The move to `msb_arch` 2.0.1. Three rules became `@invariant` |
| **1.2.2** | An audit. The orbit path was where everything was hiding |
| **1.3.0** | **R6, T4, G1.** A project as one file; which results a change would spoil; one stylesheet |

### What each of the recent ones cost

| | Item | Outcome |
| --- | --- | --- |
| L1 | A command line | 230 lines, every command one request, importing neither `pastrocore.gui` nor Qt -- which one test asserts and a second measures by running a command in a fresh process and reading `sys.modules` |
| L2 | Editing requests, in the half that matters | A session is checked whole before any of it runs, so an edited file with one bad step runs none of them. Everything it checks against is derived. **What is left is an editor inside the window, and a text editor is a better one** |
| R6 | A project as one file | `export(method="package")`. 150 KB with results; **1 KB** with `results=False`, which is what a bug report wants. The command line takes a package anywhere it takes a project |
| T4 | Which results a change invalidates | `compute(method="affected")`, asked *before* the change. Both halves derived: MSB's model graph says a `Telescope` is reached through `Scan` too, and each calculation's schema says what it reads |
| G1 | One stylesheet | 235 places became one 700-line `.qss` applied to the `QApplication`. Rules are by **type**, so every button looks like every other button -- which is the point, and why some forms changed |

### What was found on the way

Each of these was silent, and each is now a test:

| | |
| --- | --- |
| Chebyshev put a space telescope up to **846 km** from where it was | One polynomial of degree 30 over the whole orbit file. Linear was two orders of magnitude better, which is how it was noticed |
| An orbit was cut to the scan exactly | So the first and last moments of every scan were extrapolated to |
| An export that had written every file reported failure | `.value` read off an answer that was not a `Response` |
| Six interface sites called `.items()` on a list | One opened a modal nothing mocked, so the suite *hung* rather than failed; two others quietly showed an empty project |
| `get_observations()` never existed | Plotting a whole project raised on its first line |
| The window released its observations *after* emptying the project | The loop had never once had a body to run |
| A cache created and never used, guarded by a lock held over everything | Ten scans re-read the same orbit file ten times |
| Importing a telescope could not add one already here | The two lines meant to handle it assigned two fields to themselves |
| Closing the window destroyed the day's calculations | The scratch was discarded on every clean close |
| Calculating for a whole project produced an empty frame | Iterating a project yields its *names* |
| A run with a failed step reported complete success | A slot defined twice; PySide drops the arguments the winner does not accept |

Details of any of these are in `CHANGELOG.md` and in the commit that made the change.

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
| G1a | The stylesheet editable from Preferences | Changes apply without a restart. A user file beside the settings already **replaces** the shipped one at start-up; what is missing is editing it from inside and re-applying |
| G4 | A most-recently-used list | Survives a restart; a missing entry is removed when clicked |
| G5 | The visualizer configured from a file, with its own tab | Plot appearance changes without a restart; the file is editable by hand |
| G6 | One base class for the visualization tabs | Nine tabs, ~2500 lines, the same nine methods each -- and **no method byte-identical across them**, so this is parameterising nine variations rather than lifting a copy. The GUI smoke tests are the check |

### Formats

A project of its own. Three contracts with software nobody here controls.

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
| L3 | Client-server | The hard parts are storage, identity, and what a long calculation looks like to a caller who is not watching. Everything else is in place: a request is data, a session is a file, and a project is now one file too |

## Considered and rejected

| | Decision |
| --- | --- |
| Packing the *working* project into one file | **No.** Zip saves 0.6% -- parquet is already compressed -- and opening becomes 46x slower. As an **exchange** format neither cost applies, which is what R6 is: written once, unpacked once |
| A time window that is not a scan | **No.** A scan already means "these telescopes, this window". A second way to say *when* spreads to every calculation, tab and exporter |
| An asynchronous surface for long calculations | **Not needed.** `CalculationThread` already runs off the GUI thread with cancellation and progress; asyncio would need a bridge to Qt's loop and lose the cancellation |
| Parallel serialization | Measured slower: 1.69x with `asyncio.gather`, 1.11x with threads |
| An editor for sessions inside the window | A text editor is better, and both the command line and the panel check a session before running it |
| Moving save and load into MSB now | Right eventually, recorded there as **P18**. Half a mechanism before P1 is designed leaves the graph built around the wrong shape |

## Not in scope

Scheduling *optimisation* -- deciding what to observe. This describes and checks schedules; it
does not propose them. N1--N4 are the input such a thing would need, which is a different claim.
