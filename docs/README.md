# pAstroCORE documentation

Thirteen pages, and every Python example on them runs as part of the test suite.

| | |
| --- | --- |
| [**Download it**](download.md) | One file per platform, with no Python on the machine |
| [**Your first schedule**](first-schedule.md) | Start here if you came to make a schedule. From an empty window to a VEX file, in the application |
| [**A first project**](guide.md) | The same ground through the Python API, for a script or a second caller |
| [**Every tab and dialog**](interface.md) | What each screen is for and what its controls do |
| [**The calculations**](calculations.md) | What each one produces, what it needs, and what makes a result go stale |
| [**What each plot shows**](plots.md) | The thirteen plots, what is on each, and what to read off it |
| [**When something goes wrong**](troubleshooting.md) | What a message means and what to do about it |
| [**Asking something of the numbers**](analysis.md) | Windows, gaps, coverage and statistics over results that already exist |
| [**From a terminal**](command-line.md) | `pastrocore-cli`: what a project holds, calculating, exporting, sessions, any request with `ask`, and a shell |
| [**Every command**](command-line-reference.md) | Each one with its usage and arguments, generated from the command line itself |
| [**Installing and running**](installing.md) | The command, where its files live, the settings worth knowing |
| [**Getting a schedule to a correlator**](formats.md) | The map of VEX and CFX: what the model answers, what a station must supply, what is none of our business |
| [**The roadmap**](ROADMAP.md) | What is done, what comes next, and what was decided against |

## The shape of it in one paragraph

You describe a schedule as objects — a project of observations, each with telescopes, sources,
frequencies and scans. Everything you *do* to them is a request sent to one orchestrator, the
manipulator, which dispatches it to whichever operation handles it. There are five:

| Operation | What it is for |
| --- | --- |
| `inspect` | Reading: the model, and every question about it -- what can be calculated and in what order, what is stale, what a session asked |
| `configure` | Changing the model |
| `calculate` | One calculation, on one observation |
| `compute` | Changing what a project holds, many at once: running calculations, clearing them, replaying a session |
| `visualize` / `analyze` | Drawing a result, and summarising one |
| `export` / `save` / `load` | Files: results, sessions and projects written out, and read back |

**The name says whether a request changes anything.** `inspect`, `visualize` and `analyze`
only read, and msb_arch holds `inspect` to it: since 3.0 it calls nothing through it that is not
named as a read (`get`, `get_*`, `has_*`, `is_*`). That is what lets a session be cut down to
what changed something, and a replay leave the questions out.

`catalogue` is msb_arch's own read-only operation, registered on every orchestrator and
describing what is registered. It is not `inspect(method="catalogue")`, which is this
application's answer to what can be calculated.

The window is one caller of that. **`pastrocore-cli` is a second one** -- the same requests,
about two hundred lines, and it imports neither the interface nor Qt. A client-server version is
planned and will send the same requests again, which is the reason nothing that decides anything
lives in a dialog.

```python
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject

manipulator = ScheduleManipulator(ScheduleProject(name="Demo"))
assert {"inspect", "configure", "calculate", "compute", "visualize", "export", "save", "load"} \
    <= set(manipulator.get_supported_operations())
```

## Built on MSB

[MSB](https://github.com/Torward1024/MSB) is the framework underneath: the request model, the
operations, the pipelines, the interceptors, the derivation of what an application offers from
the code that does it. Thirteen of its releases came out of this project -- the most recent because `address` and `locate` were documented as inverses and were not, which is a thing you only discover by trying to use them.

What that buys, concretely: the list of calculations, which one needs which, the order they run
in, what arguments each plot takes and what a run reports about itself are all **derived from
the code that does the work** rather than written down a second time. Adding a calculation means
writing it and its schema; nothing in the interface is edited.
