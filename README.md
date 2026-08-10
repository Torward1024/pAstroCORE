pAstroCORE -- a versatile tool for scheduling radio-astronomical observations

Version 0.2.0. Past the MVP: the calculations are now defended by a test suite that
recomputes a real project and compares against what it was saved holding.

Utilizes developed MSB (Mega-Super-Base) architecture (see /common/ for more details):

Requires msb_arch 1.0.0 or later:
```pip install msb_arch```

Documentation lives in [`docs/`](docs/). Start with [the roadmap](docs/ROADMAP.md),
which records what is being worked on, what was measured, and why.

## Running

```bash
python run.py
```

## Tests

```bash
pip install -r requirements.txt pytest
pytest tests/
```

130 tests. The characterization suite recomputes every calculation in
`tests/fixtures/test_project.pastro` and compares the numbers against the ones the
project was saved with, so a change to any formula fails the build. Qt runs
offscreen, so the GUI smoke tests need no display.