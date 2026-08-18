# Installing and running

## Installing

Python 3.12 or later.

```bash
pip install .
```

That gives two commands, from any directory:

| | |
| --- | --- |
| `pastrocore` | The window |
| `pastrocore-cli` | The same work from a terminal — see [from a terminal](command-line.md) |

From a checkout, without installing:

```bash
python run.py
```

`requirements.txt` installs this project rather than repeating its dependencies, so there is one
list and it is in `pyproject.toml`.

## Where its files are

Two kinds, and they live in different places on purpose.

**What comes with the install** — the source and telescope catalogues — is inside the package,
which is how a wheel carries it and how it is found from any working directory:

```python
from pastrocore.paths import shipped_catalog

assert shipped_catalog("sources.dat").is_file()
assert shipped_catalog("telescopes.dat").is_file()
```

**What is yours** — the settings — lives in one per-user file, the same one every time:

```python
from pastrocore.base.scratch import data_home
from pastrocore.paths import settings_file

assert settings_file() == data_home() / "settings.pastro"
```

A `settings.pastro` left in a working directory by an older version is read once and kept in the
new place, so nobody's settings are lost.

A catalogue you choose in **Preferences** is recorded and honoured. One that has been deleted
falls back to the shipped one, and says so in the log rather than leaving you with an empty
catalogue.

## Where results are

A project is a **directory**, not a file:

```text
my_survey.pastro/
    project.json           the observations, sources, telescopes, scans -- about 5 KB
    results/
        obs_001/
            uv_coverage.parquet
            az_el.parquet
            ...
```

Opening one reads the model and no results at all; each is read when something asks for it.

**Before a project is saved, results live in a per-session scratch directory** under
`data_home()`, written the moment they are calculated. That is what survives a crash: the next
start offers them back. Closing the window asks before discarding them.

## Settings worth knowing

| Setting | Default | What it does |
| --- | --- | --- |
| `results_memory_share` | 0.5 | The share of available memory the results in hand may occupy before the least recently used are dropped. They are read back from disk, so this costs a read rather than a recalculation |
| `record_session` | on | Record every request, which is what **Tools → Session** shows and what a saved session replays. 10.4 µs per request |
| `session_limit` | 5000 | How many requests to remember. The window slides, so an overflowed journal is no longer a whole session |
| `time_step` | 600 | Seconds between sampled moments, for the calculations that sample |
| `log_level` | INFO | What reaches `output.log` |

## Running the tests

```bash
python -m pytest -q
```

`python -m pytest` rather than `pytest`: the module form puts the working directory on
`sys.path`, which is how the suite is run in CI. Every example in this documentation is one of
those tests.
