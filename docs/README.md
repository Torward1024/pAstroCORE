# pAstroCORE documentation

Four pages, and every Python example on them runs as part of the test suite.

| | |
| --- | --- |
| [**A first project**](guide.md) | Start here. Build an observation, calculate something, read the numbers back, save it |
| [**The calculations**](calculations.md) | What each one produces, what it needs, and what makes a result go stale |
| [**Installing and running**](installing.md) | The command, where its files live, the settings worth knowing |
| [**The roadmap**](ROADMAP.md) | What is done, what is left before 1.0, and what was decided against |

## The shape of it in one paragraph

You describe a schedule as objects — a project of observations, each with telescopes, sources,
frequencies and scans. Everything you *do* to them is a request sent to one orchestrator, the
manipulator, which dispatches it to whichever operation handles it. There are five:

| Operation | What it is for |
| --- | --- |
| `inspect` | Reading the model |
| `configure` | Changing it |
| `calculate` | One calculation, on one observation |
| `compute` | Orchestrating many: what can be run, in what order, running it, and the session |
| `visualize` | Drawing a result |
| `export` / `save` / `load` | Getting data out, and files |

```python
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject

manipulator = ScheduleManipulator(ScheduleProject(name="Demo"))
assert {"inspect", "configure", "calculate", "compute", "visualize", "export", "save", "load"} \
    <= set(manipulator.get_supported_operations())
```

The window is one caller of that, and a thin one. A command line and a client-server version are
planned, and they will send the same requests — which is the reason nothing that decides
anything lives in a dialog.

## Built on MSB

[MSB](https://github.com/Torward1024/MSB) is the framework underneath: the request model, the
operations, the pipelines, the interceptors, the derivation of what an application offers from
the code that does it. Ten of its releases came out of this project.

What that buys, concretely: the list of calculations, which one needs which, the order they run
in, what arguments each plot takes and what a run reports about itself are all **derived from
the code that does the work** rather than written down a second time. Adding a calculation means
writing it and its schema; nothing in the interface is edited.
