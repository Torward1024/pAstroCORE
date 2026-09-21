# pAstroCORE roadmap

**1.15.0 shipped.** What is left, what was decided against, and why.

Every item has an **exit criterion**: a sentence that is true or false. An item is finished when
its criterion holds, not when it feels tidy.

## Next -- finishing it

Seventeen items from using it, ranked: what cost an hour every day first, what a new user sees
second, what it cannot do yet third, and last what lets any astronomer install it and start.
They land in this order, a stage or an item per release, unless a later one turns out to need an
earlier one. **Stages 1 and 2 shipped, in 1.10.0 and 1.11.0; O1 in 1.12.0; C1 and S1 in 1.13.0; L4 in 1.14.0; E1 in 1.15.0.**
With E1 the last of stage 3 is in: what is left is for somebody else to install it and start.

### Stage 4 -- for anyone to install and use

| # | Item | Exit criterion |
| --- | --- | --- |
| U1 | **A redesign** | The window looks like a current application rather than an early Windows 8 one. Designed as tokens -- palette, type scale, spacing, radii, one light and one dark theme -- from which the stylesheet and the plots' matplotlib style are both generated, so a colour is changed in one place. Mockups of the main window, a visualization tab and an editor are agreed before any form is touched; then every form, with its pixels regenerated deliberately and before/after shown for each. **A form's layout may change where that is what makes it usable** -- what is grouped with what, what is on screen at once, what a first click reaches -- rather than only its colours; a window that reads well and is awkward to work in has not been redesigned. The theme is a choice in Preferences. The icons from G10 take their stroke from the palette, so they follow rather than get redrawn |
| I1 | **Installing without Python** | A tag builds, in CI, a download per platform that installs and starts with no Python on the machine -- a Windows installer with a Start menu entry, a macOS application, a Linux AppImage -- and attaches them to the release. CI starts each build it made, opens the fixture project and closes, so a download that does not start is a failed build. *Which platforms, signing, and PyPI: decided when it starts* |
| A3 | **A full audit of the code** | Every module in `pastrocore/` read once against what it is *for* rather than against what it does now, and each pass ends in one of three things: a fix, a test that would have caught it, or a line here saying why it stands. Physics re-derived from its equations independently of the code; every handler checked against what its docstring claims; every rule checked against something real, because a rule the model cannot justify refuses something real. The three earlier audits each found a class of defect nobody was looking for -- a position in degrees that did not read back (1.7.0), a beam drawn pi times too wide and time on source a step short per block (1.8.0), stations 9 500 km off (1.9.0) -- so "it looks clean" is not the exit. Ends with the suite green on a machine that is not busy and a written list of what was found, which is what the release notes are made of |
| W1 | **The words, cut down** | Every commit message from 03.08.2026, every docstring and every comment in `pastrocore/`, and every `.md` in the repository rewritten to one house style: short, plain, to the point. What a thing does and why it is that way, in as few words as that takes -- not an essay with a narrative. The style itself is the user's to give, and is written down here before the pass starts, so "shorter" is a rule rather than a taste. **The history is rewritten**, which means a force-push to a branch others may have pulled: it happens in one pass, announced, with the tag objects rewritten with it. Exit: no docstring longer than what it documents, no comment that tells a story, `README`, `CHANGELOG`, `ROADMAP` and `docs/*.md` in the same voice, and the suite green afterwards -- the documentation tests run every code block in those files |
| D1 | **The documentation, whole** | An astronomer with no Python reaches a VEX file from the manual alone: installing, a first observation from the catalogues, every tab and dialog, calculations and what each plot shows, formats, sessions, the command line, troubleshooting. Screenshots are made by a script from the application, so they are regenerated rather than going stale; every code block runs in the suite, as now; the command-line reference comes from the command line itself. Built as a site in CI and published with each release |

## Seen in use, and answered

Two reports from using it, both answered in 1.12.0 -- one a fix, one a measurement. Kept here so
that neither is chased twice.

| # | Item | Exit criterion |
| --- | --- | --- |
| R1 | **Result files go missing from a project directory** | **Answered, 16.09.2026: they were deleted by File -> New Project and by File -> Open.** A window lets go of a project through `compute(method="release")`, which reached `ScheduleProject.remove_all`, which asked each observation to `clear_calculated_data` -- and that erases the results *on disk* as well as in memory. So opening a second project deleted the first one's results out of its saved directory, silently. `remove_all` lets go of what is in hand now; the disk is changed by a save (which drops the results of observations the project no longer has) and by the deliberate Clear Data, and by nothing else. `test_results_survive` walks a session and fails on the old code in four places |
| M1 | **Memory grows through a session and does not come back** | **Answered, 16.09.2026: caches filling, not a leak -- and it stops.** A harness opens the visualization dialog, draws every plot it offers and opens four editors, over and over. Objects grew by 1 300 a round for a dozen rounds and then by 5: matplotlib's text metrics are an `lru_cache(4096)`, and a new tab means a new renderer, so every round filled it with new keys (about 400 `FontProperties` each) until it was full. The resident set flattens with it -- 339 MB to 377 MB over twelve rounds, then 378 MB at twenty-four. The other two things that grow are bounded by settings: the request journal at `session_limit` (5 000 entries of plain data -- what a request named is recorded by name, so nothing in the model is pinned), and the results in hand at the residency budget, which is the design. Nothing else accumulates: widgets, tabs and figures all reach zero. Two things were fixed on the way -- the visualization dialog removed a tab without closing it, so the tab's own teardown never freed its figure, and the same on the dialog's own close; `test_memory_bounds` holds both, and the journal's limit |

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
| **1.8.0** | An audit against physics rather than against what the code used to say: the beam pattern was drawn pi times too wide, time on source was one step short per block. Atomic saves; a calculation about twice as fast |
| **1.9.0** | Moving stations (velocities in m/yr taken as m/s, 9 500 km off), sources at -0 degrees, editors that rounded on save, X/Y polarizations, and a calculation that scales linearly with scans. 1.9.1--1.9.3: no orbit step without a spacecraft, the Mollweide and spacecraft tabs draw, and plots redraw clean |
| **1.10.0** | **G7, G8, G9.** Select All and Clear under every list a plot is chosen from; nothing on a form overlaps or is cut off, and no window is pinned to a size; saving shows how far it has got and the window keeps answering |
| **1.11.0** | **G10--G13.** The icon set complete and in one style; a toolbar of the menu's own actions; the platform's keys and a few of our own; a status bar showing the last log line and what the process holds |
| **1.12.0** | **O1.** A generation is a plan: saved whole, timed by the backend, its presets the model's. **R1, M1** answered -- opening a second project deleted the first one's results, and the memory that climbs through a session is caches filling, with a bound |
| **1.13.0** | **C1, S1.** The catalogues are edited in their managers and kept as JSON -- the `Sources` and `Telescopes` a project holds, with a reader fixed on the way. A session is cut down to what changed something, by the operation's name: msb_arch 3.0.0 made `inspect` read and nothing else, and the questions moved to it from `compute` and `export` |
| **1.14.0** | **L4.** Every request the window can make, from a terminal: `pastrocore-cli ask <project> <operation> <address> key=value`, and a shell that completes what the orchestrator says there is. No command table and no new language -- an address is how a person names a part, resolved from MSB's model graph, and a script is a session file |
| **1.15.0** | **E1.** How well a schedule would be heard. Each station's SEFD per band, from its table or its dish and system temperature, with where it came from; the same SEFD followed along every scan by elevation; each baseline's noise summed over the time both stations see the source, against the source's power-law flux and a threshold, and the shortest scan that would detect it. The weather and the gain curves are the run's assumptions and go with the request -- a station carries only what was measured of it, and a computed SEFD written into its table when asked. Checked against the VLBA's published baseline sensitivities; drawn, exported, and asked for in the calculation dialog, which offers each parameter only beside a calculation that takes it |

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
