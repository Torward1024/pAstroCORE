# pAstroCORE roadmap

**1.9.3 shipped.** What is left, what was decided against, and why.

Every item has an **exit criterion**: a sentence that is true or false. An item is finished when
its criterion holds, not when it feels tidy.

## Next -- finishing it

Eleven items from using it, ranked: what costs an hour every day first, what a new user sees
second, what makes it complete last. Each lands as its own release, in this order, unless a
later one turns out to need an earlier one.

### Stage 1 -- what gets in the way every day

| # | Item | Exit criterion |
| --- | --- | --- |
| G7 | **Select All / Clear under every list a plot is chosen from** | Every `QListWidget` on a visualization tab has both buttons, found rather than listed: a test walks every tab and fails on a list without them. Two hundred baselines to one is two clicks |
| G8 | **Nothing overlaps** | A test lays out every form at its default size and at its minimum, and fails when two sibling widgets intersect or a label's text is wider than its label. Fixed in the `.ui` files, regenerated, pixels regenerated from a whole run |
| G9 | **Saving and opening show real progress** | Save and open run off the window's thread in the shared `ProgressDialog`, which moves by what has been written or read (the model, then each result file) and names it. Today save shows a bar that never moves and open shows nothing. Cancel on open leaves the project that was open |

### Stage 2 -- the main window

| # | Item | Exit criterion |
| --- | --- | --- |
| G10 | **The icon set, complete** | Every menu action has an icon in the existing style -- 24x24, stroke `#005BB5`, width 2, round caps and joins, no fill, no Illustrator preamble. A test fails on an action without one and on an SVG outside that style |
| G11 | **A toolbar** | New, Open, Save, Import, Export, Calculate, Visualize, Analysis, Generate, Session, Preferences -- the menu's own `QAction`s, so a disabled action is disabled in both places. Defined in `main_window.ui` |
| G12 | **Shortcuts** | The platform's standard keys where one exists (`QKeySequence.New`, `Open`, `Save`, `SaveAs`, `Preferences`, `Quit`), `Ctrl+R` calculate, `Ctrl+Shift+V` visualize, `F1` about. No two actions share one: a test fails on a collision |
| G13 | **A status bar** | The process's memory (resident set, from `psutil`, already a dependency), refreshed every two seconds, and the last log message at INFO or above -- warnings in amber, errors in red -- from a logging handler, not from call sites |

### Stage 3 -- what it cannot do yet

| # | Item | Exit criterion |
| --- | --- | --- |
| O1 | **The generator, finished** | A generation plan -- sources, stations, bands, times, pattern -- saves to a file and loads back into the dialog whole; today a preset keeps the timing and drops what it was for. The end time a pattern implies is computed by the backend, not by the dialog, and the two built-in presets come from the backend too |
| C1 | **Editing the catalogues** | Add, edit and remove sources and stations in the catalogue managers, and save to the same file or a new one. **A catalogue is JSON** -- the same `Sources` and `Telescopes` a project serializes, so a space telescope and any field added later have somewhere to go; `.dat` files still open, and are saved as JSON. The shipped catalogues are converted once, and read back equal to what the `.dat` gave |
| S1 | **Editing a session** | A session can be cut down to what is worth repeating: rows removed, the rest saved, and a filter showing only the requests that change the model. **Everything is still recorded** -- what the window asked is what a bug report needs. Whether an operation only reads is declared on the operation, in MSB, not listed here |
| L4 | **Everything from the command line** | Every operation the window can ask for can be asked from the command line: `pastrocore-cli ask <operation> <object> key=value`, and an interactive `pastrocore-cli shell` that completes operations, methods and objects. **No new language**: both are built from the catalogue of requests MSB already describes, so nothing is a command table to keep in step with the window, and a script is a session file, which already replays |

## Parked

| # | Item | Exit criterion |
| --- | --- | --- |
| L3 | Client-server | **Parked.** What it needs decided is storage, identity, and what a long calculation looks like to a caller who is not watching -- and those are answered by knowing who the callers are. Everything it would be built on is in place and does not go stale: a request is data, a session is a file, a project is a file |
| K1 | SKED | **Waiting for a real file.** No example here is certainly sked output, and an exporter written against a guess is a file that looks right and is not |

The formats are written and read. What would settle them is a correlator accepting a file, and
that happens when one is sent.

## Dropped

| # | Item | Why |
| --- | --- | --- |
| V3 | Validate against a parser we did not write | No VEX parser is installable here, and an item standing against a tool nobody has can only ever be open. Each suite reads its own output by the format's punctuation and runs the same reading against the real files first -- calibration on somebody else's output, which is worth having and is not the same thing |
| G1a | The stylesheet reloading without a restart | Serves whoever edits the stylesheet |
| G5 | The visualizer configured from a file | Serves whoever edits the file |

## Shipped

| Release | What it shipped |
| --- | --- |
| **0.4.0** | A test suite where there was none, CI, the calculations, MSB 1.1.1 |
| **0.5.0** | A project became a directory; results are parquet, read lazily and capped |
| **0.6.0** | The dialogs ask for a folder; the single-file format removed |
| **0.7.0** | A calculation reaches the disk when it is made, with recovery |
| **0.8.0** | One catalogue, derived. A space telescope can be pointed at. A result says when its inputs moved |
| **0.9.0** | `pip install .` gives a command. Running calculations is a plan the backend builds. Start-up 4.0 s to 1.4 s |
| **1.0.0** | The parts written under time pressure put in order |
| **1.1.0** | **L1, L2.** `pastrocore-cli`, the backend's second caller. A session is checked whole before any of it runs |
| **1.2.0** | `msb_arch` 2.0.1. Three rules became `@invariant` |
| **1.2.2** | An audit. The orbit path was where everything was hiding |
| **1.3.0** | **R6, T4, G1.** A project as one file; which results a change would spoil; one stylesheet |
| **1.4.0** | **N1--N4, G6.** Asking something of the numbers; nine tabs folded onto one base |
| **1.5.0** | **V1--V4, X1, A2.** A schedule leaves: VEX and CFX, written whole and claiming only what is known |
| **1.6.0** | **V5, V6, G4.** A schedule comes back in; a rule that refused real experiments is gone |
| **1.7.0** | An audit: a position in degrees did not read back, five rules guarded only the constructor, and reading a schedule is 17x faster |

What each release changed is in [`CHANGELOG.md`](../CHANGELOG.md). How the two formats map onto
the model, and what an exported file leaves for somebody else to fill in, is in
[`formats.md`](formats.md).

## Five rules that earned their place

- **Measure before deciding, on a machine that is not busy.** Twice a plausible optimisation
  measured slower and was dropped; once a correct change was reverted on a measurement taken
  while three copies of the suite were running on the same machine.
- **Build the check before the change.** G1 was only possible the second time because the pixel
  harness was written first.
- **A characterization test cannot tell you the answer was always wrong.** It compares against
  what the code used to produce. The orbit interpolation was out by up to 846 km with a green
  suite throughout.
- **A rule the model cannot justify will refuse something real.** "Active scans must not
  overlap" threw half of `re03fr.vex` away: two sub-arrays on one source at two frequencies is
  an ordinary way to run an array, and one antenna recording two bands at once is ordinary too.
- **A check in the constructor is a check nowhere.** Six of them were found: `set` and a saved
  project reach neither. An `@invariant` holds on every path -- and, being a check that runs on
  every write, it does no expensive work to decide.
