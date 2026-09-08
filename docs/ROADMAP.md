# pAstroCORE roadmap

**1.4 shipped.** What follows is what comes next, and what was decided against.

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
| **Formats** | CFX (X1), then validating VEX against a real parser (V3) | The last thing anyone is blocked on: a schedule has to reach a correlator. [The map](formats.md) and [the VEX exporter](formats.md#writing-one) are done; CFX is smaller and its consumer is down the corridor |
| **G4** | A most-recently-used list | Small, and asked for by anyone who opens the same project twice a day |
| **G5** | The visualizer configured from a file | The plots are the one thing still styled in code |

**L3, client-server, is deliberately parked.** Everything it needs is in place -- a request is
data, a session is a file, a project is a file -- and none of that goes stale while it waits.
What it needs decided is storage, identity, and what a long calculation looks like to a caller
who is not watching, and those are answered by knowing who the callers are.

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
| **1.4.0** | **N1--N4, G6.** Asking something of the numbers, and nine tabs folded onto one base |

### What each of the recent ones cost

| | Item | Outcome |
| --- | --- | --- |
| L1 | A command line | 230 lines, every command one request, importing neither `pastrocore.gui` nor Qt -- which one test asserts and a second measures by running a command in a fresh process and reading `sys.modules` |
| L2 | Editing requests, in the half that matters | A session is checked whole before any of it runs, so an edited file with one bad step runs none of them. Everything it checks against is derived. **What is left is an editor inside the window, and a text editor is a better one** |
| R6 | A project as one file | `export(method="package")`. 150 KB with results; **1 KB** with `results=False`, which is what a bug report wants. The command line takes a package anywhere it takes a project |
| T4 | Which results a change invalidates | `compute(method="affected")`, asked *before* the change. Both halves derived: MSB's model graph says a `Telescope` is reached through `Scan` too, and each calculation's schema says what it reads |
| G1 | One stylesheet | 235 places became one 700-line `.qss` applied to the `QApplication`. Rules are by **type**, so every button looks like every other button -- which is the point, and why some forms changed |
| N1--N4 | Analysis | `analyze`: windows and gaps, coverage across stations, statistics with `range`, any of them over a whole project. Nothing names a column -- it is read from the schemas the calculations declare |
| G6 | One base for the visualization tabs | 2562 lines to 832. What varies is four declarations; a tab needing more overrides one method |

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

### Analysis -- done in 1.4.0

Shipped as `analyze`, with its own page: [asking something of the numbers](analysis.md).

**The scope rule it was built under, because "analysis" has no natural end:** an operation earns
its place when it answers a question asked *while scheduling*. Not by being a statistic that
exists. Four earned it -- `describe`, `summary`, `windows`, `coverage` -- and that is where it
stops. Histograms, correlations and fits are a different tool, and fitting and forecasting are
out of scope by the line below.

The primitive underneath all of it is one thing: runs of consecutive `True` in a boolean column,
grouped by station.

### Interface

| # | Item | Exit criterion |
| --- | --- | --- |
| G4 | A most-recently-used list | Survives a restart; a missing entry is removed when clicked |
| G5 | The visualizer configured from a file, with its own tab | Plot appearance changes without a restart; the file is editable by hand |

### Formats

A project of its own. Three contracts with software nobody here controls.

A schedule in VEX is an observation rather than a study. **CFX** is what the ASC correlator
reads. **SKED** is what much geodetic VLBI is scheduled in.

| # | Item | Exit criterion |
| --- | --- | --- |
| ~~V1~~ | ~~Map the model onto the VEX blocks~~ | **Done.** [The map](formats.md), written against `re03fr.vex` and the CFX of the same experiment. It found the one thing the model is missing -- a **sideband** on `IF`, which is physics rather than paperwork -- and drew the line the rest of the work follows: a schedule pAstroCORE owns, station hardware it must be given, and session facts that are none of its business |
| ~~V2~~ | ~~Export ground-telescope schedules~~ | **Done.** `vex(method="export")`, `pastrocore-cli vex`, **File → Export Schedule → VEX...**. The file is **structurally whole**: every block the format calls for is present, what the model knows carries real values, and what it cannot know is an empty field or a `def` whose statements are commented out — a form for `drudg` or a person at the station, rather than a file with holes. The exporter names the outstanding blocks, from the same declaration it writes them from |
| V3 | Validate against a parser we did not write | Not optional. A file that looks right to its author is how you learn months later at a correlator that it was not. **Open**: no third-party VEX parser is installable here. In the meantime `tests/test_vex.py` reads the file by VEX's punctuation and runs the same reading against `re03fr.vex` and `s16tj07a.vex` first -- a checker calibrated on `sched`'s output rather than on its own author's expectations. Worth more than a round trip through our own reader; less than a real parser |
| ~~V4~~ | ~~Characterization tests~~ | **Done.** `tests/fixtures/reference.vex` is the whole file rather than a digest, so a change shows as a diff. Regenerate deliberately: `--regenerate-vex` |
| V6 | Decide what happens to what the model cannot represent -- **before V5** | An importer that drops what it does not model, feeding an exporter that writes only what the model knows, is a lossy round trip that looks lossless. Keep unrecognised blocks verbatim, or refuse to export a lossily imported file |
| V5 | Import VEX | A real file from an experiment this lab did not schedule loads and can be analysed. Export-then-import does **not** replace V3: a round trip passes when reader and writer are wrong the same way |
| X1 | **`ScheduleCFX`** | A file the ASC correlator accepts, checked against a real one |
| ~~K1~~ | ~~**`ScheduleSKED`**~~ | **Dropped.** No file that is certainly sked output to check against, and an exporter written against a guess is the failure V3 exists to prevent. It waits for a real one |
| ~~A2~~ | ~~One `Super` per format~~ | **Done.** `ScheduleVEX`, reached as its own operation: `vex(method="export")`. The operation is the format and the method is what is done to it, so writing, reading and checking one contract stay together. Nothing about any format appears in `ScheduleData`, and the writing itself is in `pastrocore/formats/vex.py`, which knows no request |

Next: **X1, the CFX exporter**, which is smaller, whose consumer is down the corridor at the
ASC, and which models the spacecraft as an ordinary station with an orbit file -- the one thing
this model already does and `sched` does not.

Space telescopes were out of scope for V2 and are excluded by name in its report, which is a
VEX limitation rather than ours: 1.5 describes a station as a place on the Earth. CFX is where
they belong.

~~**Before either: `IF` gains a sideband.**~~ **Done**, as `sidebands` -- a list, like
`polarizations`, because one receiver setting records both sidebands in both polarizations and
is still one setting. `get_band()` is the one place it becomes numbers, and the overlap rule
asks it, which is what catches 4828 U and 4844 L being the same 16 MHz written two ways.

### Reaching it from somewhere other than the window

| # | Item | Needs |
| --- | --- | --- |
| L3 | Client-server | **Parked, not dropped.** Storage, identity, and what a long calculation looks like to a caller who is not watching -- none of which can be decided without knowing who the callers are. Everything it would be built on is already there and does not go stale: a request is data, a session is a file, a project is a file |

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
