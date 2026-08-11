# Changelog

All notable changes to pAstroCORE are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Dates are ISO-8601.

What is planned, and what was measured on the way to deciding it, is in
[`docs/ROADMAP.md`](docs/ROADMAP.md).

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
