# From a terminal

`pastrocore` opens the window. `pastrocore-cli` does the same work without one.

It is not a second implementation of anything. Every command is one request to the same
orchestrator the window sends its requests to, which is why it is about two hundred lines and
why it holds no knowledge about calculations at all — what can be run, what each needs, what
order they go in and what a run did are all *asked*.

Two tests hold that: one refuses any mention of `pastrocore.gui` or Qt in its source, and one
runs a command in a fresh process and looks at `sys.modules` afterwards, because an import that
sneaks in through a chain would pass the first and fail the second.

## What a project holds

```bash
pastrocore-cli info survey.pastro
```

```text
Survey  (survey.pastro)

  OBS_DEFAULT  [VLBI]
    2 telescope(s), 1 source(s), 1 scan(s), 1 frequency band(s)
    - az_el
    - source_visibility  (stale)
    - uv_coverage
```

`(stale)` means the result was computed from a configuration that has since changed. It is the
same answer the project explorer labels an observation with.

## What can be calculated

```bash
pastrocore-cli calculations
```

Prints what you may ask for, what each needs, and — under its own heading — the steps that are
run for you and never asked for by name. Nothing in that output is written down anywhere: it is
derived from the calculations that exist.

## Calculating

```bash
pastrocore-cli run survey.pastro --only uv_coverage
```

| | |
| --- | --- |
| `--only KEY [KEY ...]` | What to calculate. Everything offered, by default |
| `--time-step SECONDS` | Between sampled moments. 600 |
| `--force` | Recompute what is *current* as well as what is stale |
| `--session FILE` | Write the session out, to replay later |

Without `--force` a run recomputes what has gone stale and leaves the rest alone. Forcing is for
the one case freshness cannot see: the calculation's own code changed and the model did not.

Each step reports its own time, measured where it ran rather than estimated from outside:

```text
  ok  OBS_DEFAULT      Time Arrays                  0.01 s
  ok  OBS_DEFAULT      Telescope Positions          0.04 s
  ok  OBS_DEFAULT      Source Visibility            0.02 s
  ok  OBS_DEFAULT      UV Coverage                  0.31 s

4 calculation(s) in 0.38 s
```

You asked for one and four ran: the other three are what `uv_coverage` needs, and you did not
have to know that.

## Exporting

```bash
pastrocore-cli export survey.pastro out/ --only uv_coverage --pictures
```

Text always; `--pictures` draws them as well. Each plot is given exactly the filters it reads,
which the visualizer itself says.

## Sending a project

A project is a directory, which is right for working in and wrong for sending. `package` writes
one file:

```bash
pastrocore-cli package survey.pastro to_send            # everything, results included
pastrocore-cli package survey.pastro bug --model-only   # the configuration alone
```

`--model-only` is what a bug report wants — about a kilobyte that reproduces the configuration,
against 150 KB with the frames. Neither replaces an existing file unless you pass `--force`.

**A package is a project as far as reading it goes.** Every command takes one, so what a
colleague sent can be read where it is:

```bash
pastrocore-cli info to_send.pastroz
```

```python
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject

project = ScheduleProject(name="Survey")
project.create_item(item_code="OBS1")
core = ScheduleManipulator(project)

packed = core.export(obj=project, method="package", path=str(TMP / "to_send"))
assert packed["path"].endswith(".pastroz")

opening = ScheduleProject(name="opening")
reopened = ScheduleManipulator(opening).load(
    obj=opening, method="package", path=packed["path"])

# It comes back as the project it was, which is the whole claim.
assert reopened == project
```

## What a change would cost

`stale` says which results *have* gone out of date. This says which ones *would*, before the
change is made:

```bash
pastrocore-cli affected survey.pastro Telescope
```

```
Editing a Telescope reaches: scans, telescopes

14 calculation(s) read those parts:
  az_el
  ...
```

Nothing about that answer is written down. MSB's model graph knows a `Telescope` is reached
through `Scan` as well as through `Telescopes` — which is the part nobody remembers — and each
calculation declares in its schema which parts of the model it reads.

```python
report = core.compute(obj=project, method="affected", type="Telescope")

assert report["parts"] == ["scans", "telescopes"]
assert "uv_coverage" in report["calculations"]

# A scan cannot spoil a beam pattern: that reads telescopes and frequencies.
scans = core.compute(obj=project, method="affected", type="Scan")
assert "beam_pattern" not in scans["calculations"]
```

## Sessions

Every request is recorded. `--session` writes that record out, and it is plain data — no live
objects — so it can be read, edited, and run again:

```bash
pastrocore-cli run survey.pastro --only uv_coverage --session monday.json
pastrocore-cli replay survey.pastro monday.json
```

A step names its object by **path**, so a replay reaches the same object it ran on rather than
the first thing with a matching name. That works against the same project, reopened. It cannot
work against a project built separately, because nothing there shares a name.

### Checking one before running it

A session is a file, and a file gets edited. So it is checked whole before any of it runs:

```bash
pastrocore-cli check survey.pastro monday.json
```

```text
  problem  step 2: 'calculate' has no 'time_arrys'
  warning  step 3: 'uv_coverage' does not read time_stp

1 problem(s) in 3 step(s); this session will not be replayed
```

A **problem** stops the replay — one bad step among good ones runs none of them, because a
session that half ran is worse than one that refused. A **warning** does not: an attribute no
handler reads is usually a typo, but `accepts` is a lower bound by construction, so refusing on
it would refuse valid sessions.

`replay` runs the same check first, and so does **Tools → Session** in the window.

## It works

```python
from pastrocore import cli

assert cli.main(["calculations"]) == 0
```

```python
import inspect

from pastrocore import cli

source = inspect.getsource(cli)
assert "PySide6" not in source and "pastrocore.gui" not in source
```
