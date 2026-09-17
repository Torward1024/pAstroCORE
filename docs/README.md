# pAstroCORE documentation

Seven pages, and every Python example on them runs as part of the test suite.

| | |
| --- | --- |
| [**A first project**](guide.md) | Start here. Build an observation, calculate something, read the numbers back, save it |
| [**The calculations**](calculations.md) | What each one produces, what it needs, and what makes a result go stale |
| [**Asking something of the numbers**](analysis.md) | Windows, gaps, coverage and statistics over results that already exist |
| [**From a terminal**](command-line.md) | `pastrocore-cli`: what a project holds, calculating, exporting, sessions, any request with `ask`, and a shell |
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

**The name says whether a request changes anything.** `inspect`, `visualize` and `analyze` only
read -- `inspect` is held to it by msb_arch, which since 3.0 calls nothing through it that is not
named as a read (`get`, `get_*`, `has_*`, `is_*`). So does `catalogue`, which is msb_arch's own
operation, registered on every orchestrator, describing what is registered; it is not
`inspect(method="catalogue")`, this application's answer to what can be calculated. That is what
lets a session be cut down to what changed something, and a replay leave the questions out.

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
