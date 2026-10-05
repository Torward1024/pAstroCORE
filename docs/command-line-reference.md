# Every command, and what it takes

Generated from `pastrocore-cli` itself by `tools/make_cli_reference.py`, so a command that
gains an option gains a line here. What each one is *for*, with examples, is in
[from a terminal](command-line.md).


## `info`

```
usage: pastrocore-cli info [-h] project
```

| | |
| --- | --- |
| `project` | the project directory, or a package |

## `calculations`

```
usage: pastrocore-cli calculations [-h]
```

## `run`

```
usage: pastrocore-cli run [-h] [--only KEY [KEY ...]] [--time-step TIME_STEP]
                          [--force] [--session FILE]
                          project
```

| | |
| --- | --- |
| `project` | the project directory, or a package |
| `--only` | calculations to run; everything offered by default |
| `--time-step` | seconds between sampled moments (600) |
| `--force` | recompute what is current as well as what is stale |
| `--session` | write the session to a file, to replay later |

## `export`

```
usage: pastrocore-cli export [-h] [--only KEY [KEY ...]] [--pictures]
                             project destination
```

| | |
| --- | --- |
| `project` | the project directory, or a package |
| `destination` | the directory to write the files into |
| `--only` |  |
| `--pictures` | draw them as well |

## `analyze`

```
usage: pastrocore-cli analyze [-h] [--key CALCULATION]
                              [--columns COLUMN [COLUMN ...]]
                              [--group-by COLUMN [COLUMN ...]]
                              [--where COLUMN=VALUE [COLUMN=VALUE ...]]
                              [--gaps] [--at-least AT_LEAST] [--to FILE]
                              project {describe,summary,windows,coverage}
```

| | |
| --- | --- |
| `project` | the project directory, or a package |
| `what` | describe: what can be asked; summary: the numbers; windows: runs of a true/false column; coverage: across stations One of: describe, summary, windows, coverage. |
| `--key` | which result; every one for describe |
| `--columns` | summary: which numeric columns; all of them by default |
| `--group-by` | summary: break the answer down by these |
| `--where` | slice: a value, a,b,c for several, or x:y for a range |
| `--gaps` | windows: the runs of false rather than of true |
| `--at-least` | coverage: how many stations at once (1) |
| `--to` | write the answer to a tab-separated file instead of printing it |

## `package`

```
usage: pastrocore-cli package [-h] [--model-only] [--force]
                              project destination
```

| | |
| --- | --- |
| `project` | the project directory, or a package |
| `destination` | the package file to write |
| `--model-only` | leave the results out; a few KB that reproduce the configuration |
| `--force` | replace a file that is there |

## `vex`

```
usage: pastrocore-cli vex [-h] [--force] project destination
```

| | |
| --- | --- |
| `project` | the project directory, or a package |
| `destination` | the file to write, or a directory for a project with several observations -- a VEX file is one experiment |
| `--force` | replace a file that is there |

## `cfx`

```
usage: pastrocore-cli cfx [-h] [--force] project destination
```

| | |
| --- | --- |
| `project` | the project directory, or a package |
| `destination` | the file to write, or a directory -- a CFX file is one frequency setup, so several bands are several files |
| `--force` | replace a file that is there |

## `affected`

```
usage: pastrocore-cli affected [-h] project type
```

| | |
| --- | --- |
| `project` | the project directory, or a package |
| `type` | Telescope, SpaceTelescope, Source, Scan, IF, ... |

## `check`

```
usage: pastrocore-cli check [-h] project session
```

| | |
| --- | --- |
| `project` | the project directory, or a package |
| `session` | a session file, as `export ... --session` writes one |

## `replay`

```
usage: pastrocore-cli replay [-h] project session
```

| | |
| --- | --- |
| `project` | the project directory, or a package |
| `session` | a session file, as `export ... --session` writes one |

## `ask`

Send one request, as the window would. The address names what it is about: project, OBS001, OBS001/sources, OBS001/telescopes/ALMA, OBS001/scans/#3. A value is JSON when it reads as JSON and text otherwise; @address passes the object there. A request that changes the project saves it.

```
usage: pastrocore-cli ask [-h] [--json] [--dry-run]
                          project operation address [key=value ...]
```

| | |
| --- | --- |
| `project` | the project directory, or a package |
| `operation` | inspect, configure, compute, calculate, visualize, ... |
| `address` | what the request is about |
| `attributes` | a method or a handler's attribute; key alone passes nothing |
| `--json` | print the answer as JSON |
| `--dry-run` | send a change without saving the project |

## `shell`

```
usage: pastrocore-cli shell [-h] [project]
```

| | |
| --- | --- |
| `project` | the project to open; a new one if none |
