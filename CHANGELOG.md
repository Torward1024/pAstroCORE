# Changelog

All notable changes to pAstroCORE are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Dates are ISO-8601.

What is planned, and what was measured on the way to deciding it, is in
[`docs/ROADMAP.md`](docs/ROADMAP.md).

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
