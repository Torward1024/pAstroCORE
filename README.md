# pAstroCORE

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.3.0-brightgreen.svg)](https://github.com/Torward1024/pAstroCORE)
[![Built on MSB](https://img.shields.io/badge/built%20on-MSB%202.0.1-8a2be2.svg)](https://github.com/Torward1024/MSB)

A versatile tool for scheduling radio-astronomical observations.

Version 1.3.0. The parts written under time pressure have been put in order, one measured
stage at a time. What has changed and why is in
[the changelog](CHANGELOG.md); what is next is in [the roadmap](docs/ROADMAP.md).

Built on the [MSB](https://github.com/Torward1024/MSB) architecture: you describe the data as
typed entities, and everything reaches it through one orchestrator by sending a request that
is data rather than a call.

```bash
pip install .
```

That gives two commands from any directory: `pastrocore` opens the window, `pastrocore-cli`
does the same work in a terminal.

Requires `msb_arch` 2.0.1 or later. Thirteen of its releases came out of this project -- mapping
keys that could not survive JSON, built-in operations that could not reach a member of a
collection, a schema version that worked everywhere except the class saved to a file, an `int`
that was not accepted where a `float` was declared, a manipulator that could not say what it
offers, an operation whose cost was paid on every start whether or not it was used, a
handler that could not say what arguments it takes, a journal that kept alive everything it
recorded, the six lines every application writes to plan an operation, and a pair documented as
inverses that were not -- which is a thing you only find by trying to use them.

2.0 then gave back three things this project had written by hand: a project that answers with a
list exactly as a container does, a project that compares by its contents rather than by
identity, and `@invariant` -- a rule about a whole object, which is where the rules about
overlapping frequency bands, overlapping scans and duplicate observation codes now live.

**Documentation**: [a first project](docs/guide.md) · [the calculations](docs/calculations.md) ·
[from a terminal](docs/command-line.md) · [installing and running](docs/installing.md) ·
[the roadmap](docs/ROADMAP.md). Every example on those pages runs as part of the test suite.

## What it does

Describes radio-astronomical observations -- sources, telescopes, frequencies, scans -- and
calculates what follows from them: when a source is visible from which station, the uv
coverage of a baseline, azimuth and elevation over a scan, sun angles, beam patterns,
parallactic angle. Eleven calculations in all, each drawn as well as computed.

Every one of them is defended by a test that recomputes it against a saved project and
compares the numbers, so a refactoring cannot change a result quietly. The plots are defended
the same way, by reading the drawn points back out of the figure.

What that kind of test cannot do is tell you the numbers were wrong to begin with -- it compares
against what the code used to produce. The orbit interpolation was out by kilometres for as long
as it existed, and the suite was green throughout. Where an answer can be known independently it
is now checked against that instead: the orbit tests measure against a Kepler orbit solved to
machine precision.

## Running

```bash
pastrocore
```

From a checkout, without installing:

```bash
python run.py
```

## Or without a window

```bash
pastrocore-cli info survey.pastro
pastrocore-cli run survey.pastro --only uv_coverage
pastrocore-cli affected survey.pastro Telescope
pastrocore-cli package survey.pastro to_send
```

The same work from a terminal, and the same requests: `pastrocore-cli` is about two hundred
lines and imports neither the interface nor Qt, which two tests hold. What it can do is in
[from a terminal](docs/command-line.md).

## Sending a project

A project is a directory, which is right for working in and wrong for sending. **File → Package
Project** writes one file, and every command takes one anywhere it takes a project, so what a
colleague sends can be read without unpacking it.

```bash
pastrocore-cli package survey.pastro to_send              # 150 KB, results included
pastrocore-cli package survey.pastro bug --model-only     # 1 KB, the configuration alone
pastrocore-cli info to_send.pastroz                       # read it where it is
```

`--model-only` is what a bug report wants: the few kilobytes that reproduce the configuration,
without a gigabyte of frames nobody reading the report needs.

## What a change would cost

Before moving a telescope, ask what it will invalidate:

```bash
pastrocore-cli affected survey.pastro Telescope
```

Nothing about this is written down anywhere. MSB's model graph knows a `Telescope` is reached
through `Scan` as well as through `Telescopes`, and each calculation's schema declares which
parts of the model it reads; the answer is where the two meet. Staleness answers the same
question afterwards; this answers it first.

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

**Appearance is not in the forms.** It is in `pastrocore/gui/pastrocore.qss`, one file applied
to the `QApplication`, and a test refuses a `styleSheet` property in any form or a
`setStyleSheet` anywhere in the code. Rules are written against types -- `QPushButton { ... }`
-- so every button looks like every other button; that consistency is the whole point of having
one file rather than the 235 places this used to live in.

To change how the application looks, edit that file. To change it only for yourself, put your
own `pastrocore.qss` beside your settings: it replaces the shipped one rather than adding to it.

A styling change is judged by `tests/test_form_pixels.py`, which renders all 24 forms offscreen
and compares them against a stored reference. It is per platform, because pixels are not
portable. Regenerate it deliberately, after looking at what moved:

```bash
python -m pytest tests/test_form_pixels.py --regenerate-form-pixels
```

## Tests

```bash
pip install -r requirements.txt pytest
python -m pytest tests/
```

584 tests. The characterization suites recompute every calculation in
`tests/fixtures/test_project.pastro` and redraw every plot, comparing against what the project
was saved with, so a change to any formula or any filter fails the build. Qt runs offscreen,
so the GUI smoke tests need no display.
