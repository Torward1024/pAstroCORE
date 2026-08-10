pAstroCORE -- a versatile tool for scheduling radio-astronomical observations

Version 0.4.0. Past the MVP, and the parts written under time pressure are being put in order
one measured stage at a time. What has changed and why is in
[the changelog](CHANGELOG.md); what is next is in [the roadmap](docs/ROADMAP.md).

Built on the [MSB](https://github.com/Torward1024/MSB) architecture: you describe the data as
typed entities, and everything reaches it through one orchestrator by sending a request that
is data rather than a call.

```bash
pip install -r requirements.txt
```

Requires `msb_arch` 1.1.1 or later. Three releases of it came out of this project -- mapping
keys that could not survive JSON, built-in operations that could not reach a member of a
collection, and a schema version that worked everywhere except the class saved to a file.

## What it does

Describes radio-astronomical observations -- sources, telescopes, frequencies, scans -- and
calculates what follows from them: when a source is visible from which station, the uv
coverage of a baseline, azimuth and elevation over a scan, sun angles, beam patterns,
parallactic angle. Eleven calculations in all, each drawn as well as computed.

Every one of them is defended by a test that recomputes it against a saved project and
compares the numbers, so a refactoring cannot change a result quietly.

## Running

```bash
python run.py
```

## Tests

```bash
pip install -r requirements.txt pytest
python -m pytest tests/
```

161 tests. The characterization suite recomputes every calculation in
`tests/fixtures/test_project.pastro` and compares the numbers against the ones the
project was saved with, so a change to any formula fails the build. Qt runs
offscreen, so the GUI smoke tests need no display.