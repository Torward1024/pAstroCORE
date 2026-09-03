# Changelog

All notable changes to pAstroCORE are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Dates are ISO-8601.

What is planned, and what was measured on the way to deciding it, is in
[`docs/ROADMAP.md`](docs/ROADMAP.md).

## [1.2.0] - 2026-09-03

The move to `msb_arch` 2.0.1. Three of its changes were breaking, and each broke something here
that had been wrong for longer than the framework had -- which is the usual way a breaking change
earns its keep.

### Fixed

- **The interface stopped guessing what shape a project answers with.** 2.0.0 made
  `Project.get_items()` return a list, exactly as a container does, with `get_all()` for the
  mapping. Six places called `.items()` on the answer:

  - The calculation dialog, the export dialog and the visualize dialog each raised, caught it,
    and opened a modal error. In the suite nothing mocked `QMessageBox.critical`, so the tests
    **stopped** instead of failing -- a hang is what a missing mock looks like.
  - The project table and its context menu asked `isinstance(observations, dict)` and quietly
    returned. A project full of observations looked empty, and said nothing about it.

  Each asks for `observations` now -- the method that exists precisely so no caller has to know
  which shape the framework returns.

- **Plotting a whole project raised on its first line.** It called `get_observations()`, which
  has never existed on a project.

- **The window released its observations after emptying the project**, so the loop that was
  meant to release them walked an empty list. It had never once had a body to run. Releasing a
  project is a request now -- `compute(method="release")` -- which is model work leaving the
  interface, and it is what a command line opening one project after another needs anyway.

- **A restored project never equalled the one it was written from.** 2.0.0 gave `Project` an
  `__eq__` so that `load(...) == project` holds; here it still did not, because
  `CalculatedData` had none and every observation therefore compared by identity. It compares
  on the keys a result set answers to, which is the same rule `in` and `len` already use --
  comparing frames would mean loading both projects to answer `==`.

- **`_compute_replay` overwrote its own `attributes` parameter inside its loop**, so from the
  second step onwards `skip_failures` was read out of that step's attributes rather than out of
  the request.

### Changed

- **Three rules moved from helpers called by hand to `@invariant`**, which 1.10.0 added: a rule
  about a whole object, checked when it is built, when it is restored, and after anything that
  changes what it holds, with the change undone when it refuses.

  | Rule | Was called from | Was not checked when |
  | --- | --- | --- |
  | Frequency bands must not overlap | six places | `set_item` wrote into `_items` directly |
  | Active scans must not overlap | `add`, `set_scan` | `set_item`, `set_items`, or the object was built from a file -- which is where a conflicting pair comes from |
  | Observation codes must be unique | four places | `remove_item` and `set_project` |

  Each rule names both offenders rather than stating the rule, which a method that only answers
  False cannot do. Both containers sort by start rather than comparing pairwise, so checking the
  whole costs one sort instead of a square. `set_if` and `set_scan` edit an item in place, where
  a container is never told -- so they write, check, and put the old values back on a refusal,
  which is what msb_arch does for a field and for the same reason.

  A refusal is now an `InvariantError`. It is a `ValueError`, so anything catching that still
  catches this.

- `SCHEMA_VERSION`, `migrate`, `to_dict` and `clear` came off `ScheduleProject`. The first three
  were reimplementations of what `Project` provides once it is a `Serializable`; `clear` was the
  name 2.0.0 removed, and its work is in `remove_all`.

### Upgrading from 1.1.0

Install `msb_arch` 2.0.1. A project written by 1.1.0 opens unchanged.

Two things are refused that were previously accepted only because nothing checked: a saved
project whose active scans overlap, and one holding two observations with the same code. Both
are schedules that could not be run; if a file of yours does not open, that is what it is saying.

## [1.1.0] - 2026-08-18

The release where the backend gets a second caller, which is the claim 1.0 was built on and
could not yet prove.

### Added

- **`pastrocore-cli`** -- the same work without a window: `info`, `calculations`, `run`,
  `export`, `check` and `replay`. About two hundred lines, every command one request, and no
  knowledge about calculations at all: what can be run, what each needs, what order they go in
  and what a run did are all asked of the orchestrator.

  Two tests are the point rather than the commands. One refuses any mention of `pastrocore.gui`
  or Qt in its source; the other runs a command in a fresh process and looks at `sys.modules`
  afterwards, because an import that sneaks in through a chain would pass the first and fail the
  second. `pastrocore` still opens the window.

- **A session is checked before it is replayed.** The command line turned a session into a file,
  and a file gets edited. `compute(method="check")` reports every problem without running a
  step -- an operation nobody has, a method that operation lacks, an object this project does not
  hold and where it was looked for, an attribute the handler never reads.

  A **problem** stops the replay: one bad step among good ones runs none of them. An unread
  attribute is a **warning**, because `accepts` is a lower bound by construction and refusing on
  it would refuse valid sessions. `replay` checks first, the command line has `check`, and
  **Tools → Session** says the same, since all three ask the same operation.

- **A session row says which object, not just its name.** Two observations may hold a source
  called `1228+126`; the panel showed the bare name and the two rows were indistinguishable.
  `where` is the recorded path made readable, and it is a column now.

### Fixed

- **A replayed step reaches the object it ran on.** Replay resolved by name, and `find` does not
  descend into an observation at all -- so a step that edited a source, a telescope or a scan
  came back unresolved every time, and only calculations could be replayed. It resolves by
  **path** now. That works against the same project, reopened; it cannot work against a project
  built separately, because nothing there shares a name.

- **Replaying a session that contained a run called a string.** A run carries two callables --
  one to report progress, one to ask whether to stop -- a journal cannot record a callable so it
  records `<function>`, and replay handed that back for the handler to call. Only a command line
  writes a session containing its own run, so nothing had met it.

- **Importing a frequency from a file raised** `NotFoundError: Attribute 'object' not found in
  IF`. It asked `load` for a shape that stopped existing when that contract became MSB's own,
  and no test covered the path.

- **Three `to_dict` overrides wrote into the mapping they were handed.** On an object that
  caches, that mapping *is* the cache, and MSB 1.9.0 turned writing to it into a refusal.
  Nothing constructs with caching on today, so this was a rake with a label on it.

### Changed

- **Nothing unwraps a response by hand.** MSB 1.8.0 gave a request's answer one type, and 53
  places here carried the line it replaces. That line is *wrong* for a request naming one
  method, and 26 of the 53 were dead as well -- the call never asked for the whole response. A
  ratchet forbids its return, in the source, the tests and the documentation.

- Requires `msb_arch` 1.9.2, which came out of this: `address` and `locate` were documented as
  inverses and were not, for two independent reasons, both found by trying to use them here.

### Upgrading from 1.0.0

Nothing to do. `pastrocore` opens the window as before; `pastrocore-cli` is new. A session
recorded by 1.0.0 still replays -- it has no paths, so it falls back to names, which is what it
did before.

## [1.0.0] - 2026-08-13

The release that says the shape is settled: **a project saved by 1.0 opens in 1.0**, the
interface is one caller of a backend rather than the place the work happens, and every claim on
this page was measured or tested rather than felt.

### Added

- **Tools → Session.** What has been asked of this project -- operation, object, method, how
  long, whether it worked -- written to a file, and a saved session replayed against whatever
  project is open. Each step names its object and is resolved on replay, so a session recorded
  against one project runs against another. A step naming something this project lacks is
  reported rather than skipped: a session that half ran is worse than one that refused.
- **Tools → Last Run Report.** What a run did, a row per step with its own time and its
  outcome, kept after the dialog closes and copyable as text for a bug report.
- **Independent calculations run at once.** Measured 1.30x on a thirteen-step plan (1.885 s
  against 1.453 s, median of five alternating rounds). Cancellation and the skipping of a
  failed branch behave as they do in sequence.
- **Documentation** for somebody who has never seen the project: [a first
  project](docs/guide.md), [the calculations](docs/calculations.md), [installing and
  running](docs/installing.md). **Every Python block on those pages is executed by the test
  suite**, in order, in one namespace, so an example that has drifted fails the build.

### Changed

- **A run recomputes what has gone stale**, which freshness already knew and the run ignored --
  and then re-stamped the reused result as current, so freshness stopped saying so. Forcing a
  recomputation of what is *current* is a separate thing to ask for, and the tick box says so:
  it is "Recompute everything" now, off by default, and it no longer clears every result the
  observation holds.
- **The interface reaches the model only through the orchestrator**, checked by a test rather
  than believed. Six places did not: the calculation dialog walked the telescopes and cleared
  results itself, two tabs read the frequencies, and the window asked an observation what was
  stale, saved the project by calling it, and wrote an observation to a file with `json.dump`.
- **`save` and `load` are MSB's**, inherited rather than written again: atomic writes, an
  overwrite guard, and the framework's own error types. 59 lines removed.
- **Every result is calculated and written once.** Measured on one `source_visibility` request:
  `times` 10 stores → 1, `telescope_positions` 4 → 1, `source_visibility` 2 → 1.
- Four rules moved from `__init__` onto the annotation, where they hold at every way in: the
  source coordinates, the observation type, a scan's duration, and a telescope's pointing
  ranges. Each of them accepted anything through `set` and through `from_dict`.
- Requires `msb_arch` 1.7.0.

### Fixed

- **Closing the window destroyed the day's calculations.** Results live in a scratch directory
  until the project is saved, and `closeEvent` discarded it on every clean close. It asks now.
- **Every File → New Project and Open orphaned a scratch**, which the next start offered to
  recover from a session that had ended normally with nothing in it.
- **Calculating for a whole project produced an empty frame and said nothing.** Iterating a
  project yields its *names*, so thirteen calculations called `get_scans()` on a string.
- **A source going inactive left the time arrays looking current.** Found by checking each
  result's declared `depends_on` against what MSB derives the handler to touch.
- **A run with a failed step reported complete success.** A slot defined twice, and the winner
  took one argument where the signal carries two; PySide drops what a slot does not accept.
- **An observation labelled "12 stale" could not be opened** -- the explorer looked it up by
  its label -- **and the label survived the recomputation that fixed it.**
- **A step stored its result under the handler's name** rather than the schema's store key, so
  `time_arrays` landed where nothing reads it.
- **Comparing two metadata mappings raised instead of answering** when one held numpy arrays,
  which turned a Mollweide recomputation into a failed calculation.
- **An installed application found no catalogues and lost its settings**: every path was
  relative to the directory it was started from.

### Upgrading from 0.9.0

| Symptom | Why | What to do |
| --- | --- | --- |
| Closing the window asks about saving | It always should have: those results were being discarded | Save, or discard deliberately |
| "Recompute everything" is off and no longer clears results | A run recomputes what is stale by itself | Nothing. Tick it after changing a calculation's own code |
| `manipulator.export(method="catalogue")` raises | Planning and running calculations moved to their own operation | `manipulator.compute(...)`. `plan`, `run`, `catalogue` and `order` moved together |
| `load` returns the object rather than `{"object": ...}` | MSB's own contract | Read the result directly |

## [0.9.0] - 2026-08-13

The release that makes pAstroCORE installable, and that moves the last of the running of
calculations out of the dialog that used to do it. Three of the four fixes below are the same
fault wearing different clothes: **the interface reported success because nothing carried the
failure to it.**

### Added

- **`pip install .` gives a `pastrocore` command.** `pyproject.toml` declares the build, the
  dependencies and the entry point, and the version is stated once -- in
  `pastrocore/__init__.py`. `requirements.txt` installs the project rather than listing what it
  needs a second time.
- **Space telescope results can be drawn.** Pointing draws azimuth and elevation per station
  with range on a right-hand axis, since a range moves over four orders of magnitude more than
  the angles do. Visibility draws filled bands per station, because the value is a boolean and
  what a reader wants is when it is true and for how long.
- **The calculation dialog asks what to point at**, once per run, before starting. One
  spacecraft in the selection is used without asking; several are offered; none is said so, and
  the calculation that could not produce anything is not run.

### Changed

- **Running several calculations is a plan the backend builds.** The dialog used to loop over
  what was ticked, in whatever order the list happened to be in, with prerequisites left to
  whoever remembered them. `export(method="plan")` now returns a pipeline -- everything asked
  for plus everything those need, with the edges taken from the handlers themselves -- and
  `run` executes it. Asking for `telescope_visibility` alone plans five steps in the order that
  satisfies them. Progress and cancellation ride on an interceptor, so nothing is counted twice
  and a cancelled step skips the branch below it exactly as a failed one does. **A command line
  or a server sending the same request gets the same behaviour**, which is the point of putting
  it there.
- **Start-up: 4.0 s to 1.4 s.** The calculator and the visualizer, which between them import
  matplotlib, `astropy.coordinates` and scipy, are registered deferred (`msb_arch` 1.4.0) and
  built when first needed -- warmed on a background thread once the window is up. Nine dialogs
  imported at module level are imported where they are opened. The settings file is read once
  instead of twice.
- **The exporter asks each plot what it takes.** Five lists decided which arguments each picture
  was given, and each was a copy of what the plot states by reading it. `accepts` on a catalogue
  entry (`msb_arch` 1.5.0) derives that. One plot was missing from two of the lists.
- **The catalogues ship inside the package** and the settings live in one per-user file. See
  Fixed: the paths were relative to wherever the application was started.
- Requires `msb_arch` 1.5.0 or later.

### Fixed

- **Exporting pictures failed for every calculation.** The exporter called `self.manipulator` on
  a `Super` whose attribute is `_manipulator`, so every export with pictures raised
  `AttributeError` -- which the dialog reported as "0 files written". Text export worked
  throughout, which is why it read as "pictures are not implemented for this".
- **A run with a failed step reported complete success.** `CalculationDialog` defined
  `calculation_finished` twice; the later definition won and took one argument where the signal
  carries `(results, errors)`. PySide drops arguments a slot does not accept rather than
  complaining, so the failures fell into the gap between the two definitions.
- **The space telescope calculations ran with nothing to point at**, finishing in a millisecond
  having computed nothing, so there was afterwards nothing to export or draw. Which calculations
  need a target is read from the result's columns; the first fix compared the labels the list
  shows against the keys the catalogue speaks and matched nothing, which shipped because the
  tests called the helper directly and never went through the dialog's run.
- **Ticking a calculation did not tick what it needs**, the same label-against-key comparison, so
  `telescope_visibility` could run before `telescope_az_el`.
- **An installed application found no catalogues and lost its settings.** Every path was relative
  to the directory it was started from. The catalogues are inside the package now; the settings
  are one per-user file, adopting a `settings.pastro` left in a working directory once. A
  catalogue chosen in Preferences is kept; one that has been deleted falls back to the shipped
  one and says so.
- **`scan_times` narrowed only by `source_name`**, so a result about a tracked spacecraft needed
  a case of its own. It narrows by whatever column the caller named that the result has.

### Upgrading from 0.8.0

| Symptom | Why | What to do |
| --- | --- | --- |
| The application starts with empty catalogues after this upgrade | Your `settings.pastro` records `catalogs/sources.dat`, relative to the old layout | Nothing. The relative path no longer resolves, so the catalogue that ships with the install is used and a line in the log says so. Point Preferences at your own catalogue if you had one |
| Settings appear to have been forgotten | They moved to a per-user directory | Nothing, once. A `settings.pastro` in the directory you start from is read and kept in the new place |
| `pip install -r requirements.txt` now installs pAstroCORE itself | It is `-e .`, so the dependencies come from `pyproject.toml` | Nothing. This is what makes one list rather than two |

## [0.8.0] - 2026-08-11

Adding a calculation now touches the calculator and its schema, and nothing in the interface.
A space telescope can be pointed at. A result says when the configuration moved underneath it.

### Added

- **Pointing a ground station at a space telescope.** `telescope_az_el` and
  `telescope_visibility`, chosen by name and never run as part of an ordinary observation. The
  direction is the **vector from station to spacecraft**: a source is far enough away that
  every station sees it alike, a spacecraft at twenty thousand kilometres is not, and reusing
  the source geometry would have been wrong by degrees while looking entirely plausible. The
  scans supply the time window, the stations supply the vantage point, and the spacecraft need
  not take part in the observation it is tracked during. Checked against the law of cosines
  rather than against a stored number.
- **A result knows when its inputs changed.** Moving a telescope 1 000 km and recalculating
  used to return the previous numbers in silence. Three answers now -- stale, current, or
  *unknown*, since a result computed before this existed is neither. Shown as a label in the
  project explorer, never as a dialog. Granular: editing a scan stales `uv_coverage` and
  leaves `beam_pattern` alone, because each result declares what it reads in its own schema.
- **`ScheduleData`.** Export, save and load are operations reached through the manipulator, so
  a script or a server can do what the interface does. The export dialog went from 312 lines to
  210, its non-Qt logic from 252 to 130. Proved by bytes: four exported files hashed before a
  line moved and identical after.
- **One catalogue.** The same knowledge was written down nine times across three dialogs,
  including a table of which calculation needs which. It is one request now, answered by the
  manipulator from its own handlers -- `msb_arch` 1.2.0. Adding a calculation makes it appear
  with its label, its prerequisites and its place in the order, without a line changing in
  `pastrocore/gui`, which a test asserts by adding one.

### Fixed

- **Time on source lost its whole plot** with `KeyError` when a source was visible for less
  than one time step: a zero-length block, whose end sorted before its start.
- **Mollweide lost the source coordinates it draws against.** They are numpy arrays and
  `json.dumps` refuses them, so the metadata write dropped the key behind a warning nobody
  reads. Broke in 0.5.0 and broke silently. A project written before this needs
  `mollweide_tracks` recalculated once.
- **Metadata could disagree with the data beside it** -- 288 rows over one scan, described as
  covering nothing. Three fields restated what the frame already said, so one fact had two
  sources. The frame is the authority now.
- **Startup scanned 199 scratch directories** and asked the operating system about each,
  1 246 ms of it, for an answer it then threw away. 31 ms.
- **Every visualization tab failed to open** after the catalogue landed, and no test could see
  it: the tests build tabs directly, and none opened one through the dialog.

### Changed

- The visualizer's handlers follow MSB's naming, so the catalogue can see what it draws.
- Requires `msb_arch` 1.2.0 or later.

351 tests.

## [0.7.0] - 2026-08-11

A day of calculation is no longer lost to a crash.

### Added

- **Results are written to disk the moment they are calculated**, rather than waiting for a
  save. They used to be held in memory and marked unwritten -- true whether or not the project
  had a directory -- so they were lost to a crash, a power cut or the memory running out. They
  also counted **zero bytes** against the residency ceiling, because the budget cannot evict
  what it has nowhere to read back from, which meant an unsaved session was ungoverned as well
  as unprotected. Both are fixed by the same change.
- **A scratch directory per running session.** Before a project has a directory of its own its
  results live there; saving migrates them across rather than recalculating. One per session,
  named for the process, so two open windows never adopt or evict each other's results -- the
  same rule a server needs to run sessions for several people.
- **Recovery.** A session that did not close normally leaves its scratch directory behind on
  purpose, and the next start offers it back, naming the project and how much it holds. Closing
  normally removes its own and only its own. Nothing is ever swept at startup: a directory left
  by a previous run is the day of calculation this exists to protect.
- **Interface changes are made in the `.ui` files and regenerated**, with
  `tools/regenerate_ui.py` and a test that fails if a generated module and its form have
  drifted. It found one that had. The memory-share control added in 0.5.0 now lives in the
  form.

### Fixed

- `ui_dialog_edit_if.py` and its form had each been edited without the other, both only in
  styling. The form was the newer, so regenerating restored the dialog's own styling.

### Notes

- Writing through is best effort. A store that fails leaves the result held and unwritten, so a
  full disk costs the protection rather than the calculation.
- The scratch lives in the per-user data directory, deliberately not the system temporary
  directory: results have to survive a crash and be findable afterwards, and temporary
  directories are exactly what gets swept.

## [0.6.0] - 2026-08-11

### Removed

- **The single-file project format.** It was tolerated for one release and is now gone: nobody
  outside this repository had saved a project in it, so the window to carry it forever was open
  for a day and was not worth a branch in every load path. `ScheduleProject.to_file` and
  `from_file` went with it -- 147 lines of two-format handling. The test fixture is unaffected:
  it is a JSON file read through `from_dict`, the model's own serialization, not through a file
  format.

### Changed

- **Open and Save ask for a folder.** Both dialogs used to ask for a file: Save warned about
  overwriting one, and Open could not select a directory at all, so a user had to navigate
  inside the project and pick `project.json` -- which worked only because `open` had been
  written to tolerate it. Opening now checks that the chosen directory really is a project and
  says so plainly when it is not, because a directory chooser will return any directory.
- **Saving into a folder that already holds something else asks first.** An empty folder --
  what the dialog's New Folder button produces -- and an existing project both go ahead without
  a question. Anything else would have dropped `project.json` and a `results/` directory among
  a user's files with nothing said.

## [0.5.1] - 2026-08-10

A bug-fix release. A space telescope could be built but not read back, so any
project containing one failed to open.

### Fixed

- **A project holding a space telescope could not be opened.** A space telescope has no station
  geometry, no mount and no elevation limits -- the constructor fixes them rather than
  accepting them. They are inherited fields all the same, so `to_dict` wrote them out and
  deserialization handed them back to a constructor that rejects them. `to_dict` now omits
  them, as it already omitted the position and velocity for the same reason, and `from_dict`
  drops them if a file written earlier still carries them.
- Space telescope ranges may be written as whole numbers -- `pitch_range=(0, 90)` -- which
  needed `msb_arch` 1.1.2.

### Changed

- Requires `msb_arch` 1.1.2 or later.

## [0.5.0] - 2026-08-10

Results moved out of memory. A project saves as a directory whose model is 5 KB, each result
is a parquet file beside it, and nothing is read until something asks for it. What is read is
subject to a ceiling.

Two calculation defects were found on the way, both of which had been producing wrong output
in silence.

### Added

- **The directory format, wired into the application.** `ScheduleProject.open` takes a project
  directory, the `project.json` inside one, or a single file written by an earlier version, and
  works out which. `save` writes a directory, converting a single file at the same path -- the
  old file is removed only after the new directory is complete. Every project saved before this
  keeps opening.
- **A residency budget.** One per project, defaulting to half of available memory and settable
  in Preferences as a percentage. When the ceiling is passed the least recently used results
  are dropped and read back from disk when next needed. An unwritten result is never dropped,
  and a result larger than the whole budget is still read -- the budget governs what may be
  kept, never what may be read.
- **Lazy, filtered reads.** All eight plots read through `scan_calculated_data` and collect
  once their filter chain is complete, so polars pushes the filter into the parquet read.
- **Characterization tests for the plots**, which had none. They read the drawn artists back
  out of the figure and compare coordinates, because every plot method swallows exceptions and
  returns a blank figure -- a test that only checked for a crash would pass through exactly the
  failure worth catching.

### Fixed

- **Baseline projections were NaN in every row, always.** UV coverage covers only the times the
  source is up; the code copied those rows into the first N positions of the time grid and then
  masked by visibility, which is true somewhere in the middle. The two never overlapped, so
  every value was discarded. They are matched on time now.
- **The characterization suite could not see a NaN appear or disappear.** The comparison
  computed `abs(a - b) / scale`, which is NaN when one side is NaN, and `NaN > worst` is false.
  That is why the defect above went unreported.
- **Plots drew telescopes and baselines in an unpredictable order**, so colours and legend
  order changed between runs on identical data. Eight loops iterated `unique()`, which polars
  does not order.
- **Renaming an observation lost its results**, which are filed under the owner's name.
- **Results of observations no longer in a project were left on disk**, where renaming an
  observation away and back would pick them up as current.
- **Saving could write a directory over the model file** when a project was opened by picking
  its `project.json`.

### Changed

- Metadata is read from its own file rather than through the result: 0.33 ms against 2.20 ms,
  because the old path pulled every row off disk to reach four entries.
- The exporter releases each observation's results before moving to the next.

### Measured

| | Before | After |
|---|---|---|
| Draw one source of 300, 1.3M rows | 55.2 ms | **6.0 ms** |
| Memory over 60 observations, 200k rows each | 407 MB, all 60 held | **71 MB, 32 held** |
| Loading a project | every result read | **none read** |
| Model file | 230.5 KB | **5.1 KB** |

213 tests.

## [0.4.0] - 2026-08-10

Four stages of the road out of the MVP: a safety net, hygiene, the calculations, and adopting
what MSB 1.1.1 now does for us. **Over 500 lines removed**, almost all of it code that
duplicated the framework.

The calculations are unchanged, and that is the point of the first stage rather than a
coincidence.

### Added

- **A test suite, where there was none.** 161 tests. The characterization suite clears the
  eleven results a saved project holds, recomputes them, and compares the numbers -- so a
  change to any formula fails the build. The reference needed no separate file: the project
  the author saved and trusts *is* the reference.
- **CI**, running on push and on every pull request, with Qt offscreen so the GUI smoke tests
  need no display.
- **A request journal.** Every request the orchestrator processes is recorded, bounded to the
  most recent 500. Read backwards it answers what produced a result; read forwards it replays
  the session, which is how a reported problem becomes a reproduction. `journal_limit=None`
  declines it.
- **A schema version on the project**, with a `migrate` hook, ahead of the storage change that
  needs it.
- **`ResultStore` and `CalculatedData`**: calculated results can live on disk as parquet and
  be read only when asked for. Not yet wired into the application -- the format change is the
  next stage -- but the machinery and its tests are in.
- **A startup warm-up**: one throwaway coordinate transform on a background thread while the
  window is appearing.

### Changed

- **Constraints live on annotations.** `IF.frequency`, `IF.bandwidth` and `Telescope.diameter`
  are `Annotated[float, Positive()]`. The hand-written checks they replace ran *after*
  `super().__init__()`, so the object was already built with the bad value, and none of them
  ran on assignment at all.
- **The entry point moved.** `pastrocore.py` shadowed the `pastrocore` package, so the main
  window could not be imported and could not be tested. It is now `pastrocore/app.py`, and the
  launcher is `run.py`.
- **Logging is lazy** throughout: 1 169 calls rewritten, every one of 682 rendered messages
  verified identical.
- Six handlers in the interface that call themselves "Validation error" now catch
  `(ValidationError, ValueError)`, so a wrong *type* reaches the branch written for it instead
  of the catch-all.

### Removed

- **`BaseEntityN`**, 98 lines overriding validation "for numpy arrays". Not one of the five
  classes using it declares a numpy annotation, MSB accepts them natively anyway, and the
  override was *weaker* than what it replaced -- its list branch could never match, so list
  elements went unchecked.
- **Six of nine `from_dict` overrides**, which reimplemented what MSB already does. The three
  that remain each earn it.
- **Twenty of twenty-one `Inspector` and `Configurator` handlers.** They are the built-ins now.
  `_configure_scheduleproject` stays, because generating observations is real domain logic.
- **21 918 lines**: `rc_icons.py` existed twice, byte for byte.

### Fixed

- **A calculation that fails now says why.** Seventeen handlers wrapped a whole calculation,
  logged one line and returned an empty frame, so a failure was indistinguishable from a source
  that was simply never above the horizon. They now log with the traceback.
- **The first calculation in a process took 1 077 ms against 290 for every one after it.** The
  difference was astropy loading its reference tables, once. Warming them at startup makes the
  first calculation 307 ms.
- **`polars`, `pyerfa` and `pyarrow` are declared.** They were imported and missing from
  `requirements.txt`, so a clean environment installed and then failed to start.
- A cache miss caused by a differing `time_step` is now logged with both steps. It was correct
  and silent, which left no way to learn why a call took 300 ms instead of one.

### Notes

Three releases of `msb_arch` came out of this work, each from a real need here:

| | |
| --- | --- |
| **1.0.1** | A `Dict[float, float]` -- an instrument table -- could not round-trip through JSON, because mapping keys were not restored from the annotation |
| **1.1.0** | The built-in operations could not reach one named member of a collection, which is what ten handlers here existed to do |
| **1.1.1** | `SCHEMA_VERSION` worked on entities and nowhere else, so the class an application actually saves to a file was the one that could not be versioned |

### Upgrading from 0.3.0

| Symptom | Cause | What to do |
| --- | --- | --- |
| `python pastrocore.py` no longer works | The entry point moved out of the package's way. | `python run.py` |
| A negative frequency, bandwidth or diameter is now refused | It always should have been; the check now runs before the value is stored, and on assignment too. | Nothing, unless the value was wrong. |
| Nothing else. | The saved project format has not changed yet. | Nothing. |
