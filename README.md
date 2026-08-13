# pAstroCORE

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.9.0-brightgreen.svg)](https://github.com/Torward1024/pAstroCORE)
[![Built on MSB](https://img.shields.io/badge/built%20on-MSB%201.7.0-8a2be2.svg)](https://github.com/Torward1024/MSB)

A versatile tool for scheduling radio-astronomical observations.

Version 0.9.0. Past the MVP, and the parts written under time pressure are being put in order
one measured stage at a time. What has changed and why is in
[the changelog](CHANGELOG.md); what is next is in [the roadmap](docs/ROADMAP.md).

Built on the [MSB](https://github.com/Torward1024/MSB) architecture: you describe the data as
typed entities, and everything reaches it through one orchestrator by sending a request that
is data rather than a call.

```bash
pip install .
```

That gives a `pastrocore` command, which starts the window from any directory.

Requires `msb_arch` 1.7.0 or later. Ten releases of it came out of this project -- mapping
keys that could not survive JSON, built-in operations that could not reach a member of a
collection, a schema version that worked everywhere except the class saved to a file, an `int`
that was not accepted where a `float` was declared, a manipulator that could not say what it
offers, an operation whose cost was paid on every start whether or not it was used, a
handler that could not say what arguments it takes, a journal that kept alive everything it
recorded, and the six lines every application writes to plan an operation.

## What it does

Describes radio-astronomical observations -- sources, telescopes, frequencies, scans -- and
calculates what follows from them: when a source is visible from which station, the uv
coverage of a baseline, azimuth and elevation over a scan, sun angles, beam patterns,
parallactic angle. Eleven calculations in all, each drawn as well as computed.

Every one of them is defended by a test that recomputes it against a saved project and
compares the numbers, so a refactoring cannot change a result quietly. The plots are defended
the same way, by reading the drawn points back out of the figure.

## Running

```bash
pastrocore
```

From a checkout, without installing:

```bash
python run.py
```

## Projects on disk

A project saves as a **directory** named `something.pastro`, holding a small `project.json`
and a `results/` directory with one parquet file per calculated result.

```
my_survey.pastro/
    project.json           the observations, sources, telescopes, scans -- about 5 KB
    results/
        obs_001/
            uv_coverage.parquet
            az_el.parquet
            ...
```

This is not tidiness. A year of observing 300 sources through 12 telescopes produced results
that filled 16 GB of memory, because every one of them lived inside the project file and the
file was loaded whole. Now opening a project reads the model and **no results at all**; each
one is read when something asks for it, and a plot that draws one source reads that source
rather than all 300.

What is in memory is capped. **Preferences → Calculations → Results in memory** sets the share
of available memory the results in hand may occupy; past it, the least recently used are
dropped and read back from the directory when needed again. The default is half of what is
available. Dropping a result costs a read, never a recalculation.

**A calculation is written to disk as soon as it is made**, not when you press save. Before a
project has been saved anywhere, results go to a scratch directory belonging to that session --
so a crash, a power cut or a full memory costs you nothing, and two open windows never disturb
each other. Saving moves them into the project. Closing normally clears the scratch; a session
that ended any other way is offered back the next time the application starts.

**Open and Save ask for a folder**, not a file, because that is what a project is. Use the
dialog's New Folder button to make one.

Export is unchanged and unaffected: it writes text and pictures, not projects.

## Working on the interface

**Interface changes are made in the `.ui` files with Qt Designer, then regenerated.**

```bash
python tools/regenerate_ui.py
```

The forms live in `pastrocore/gui_pyside/`; the modules they generate live in
`pastrocore/gui/ui_*.py` and are not edited by hand. A form edited only in its generated `.py`
cannot be opened in Designer again without losing the edit -- the rule protects the tool, not
the file. Hand-written code that *uses* a form goes in `pastrocore/gui/p_*.py`, which is yours.

The test suite runs `tools/regenerate_ui.py --check` and fails if the two have drifted, so this
cannot be forgotten quietly. Do not run `pyside6-uic` directly: it emits `import icons_rc`, a
bare module name that only resolves if `pastrocore/gui` is on `sys.path`, and the icons then
fail at the first use. The script rewrites it.

## Tests

```bash
pip install -r requirements.txt pytest
python -m pytest tests/
```

351 tests. The characterization suites recompute every calculation in
`tests/fixtures/test_project.pastro` and redraw every plot, comparing against what the project
was saved with, so a change to any formula or any filter fails the build. Qt runs offscreen,
so the GUI smoke tests need no display.
