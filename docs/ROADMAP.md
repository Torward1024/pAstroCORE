# pAstroCORE roadmap

**1.18.1 shipped.** Where it stands, what is still open, and what was decided against.

Every item has an **exit criterion**: a sentence that is true or false. An item is finished when
its criterion holds, not when it feels tidy.

## Where it stands

The ranked list this roadmap opened with is finished. Seventeen items, in the order they cost
something: stages 1 and 2 in 1.10.0 and 1.11.0, O1 in 1.12.0, C1 and S1 in 1.13.0, L4 in
1.14.0, E1 in 1.15.0, U1 in 1.16.0, A3 in 1.17.0, and W1, D1 and I1 in 1.18.0.

**Since 06.10.2026 it is being used by people who did not write it**, which is where the next
items come from. Two are open; nothing is scheduled against them, because a report from use
outranks anything either of us would think of.

## Open

| # | Item | Exit criterion |
| --- | --- | --- |
| P1 | **Used by people who did not write it** | Reports come from a laboratory and then from other departments, and each one ends in a fix, a test that would have caught it, or a line here saying why it stands. The downloads install and start on machines nobody here has touched. Exit: the reports stop being about whether it runs and start being about what it should do |
| V7 | **A correlator reads a file this wrote** | VEX and CFX are written by the model, read back by it, and checked against real files by the suite -- and no correlator has yet accepted one. Until it has, the formats are a well-tested guess. Exit: a file this wrote is taken by a correlator, and whatever it says is wrong is fixed or written down |

## Seen in use, and answered

Three reports from using it, kept so that none is chased twice.

| # | Item | Exit criterion |
| --- | --- | --- |
| R1 | **Result files go missing from a project directory** | **Answered, 16.09.2026: they were deleted by File -> New Project and by File -> Open.** Letting go of a project reached `clear_calculated_data`, which erases results *on disk* as well as in memory, so opening a second project silently deleted the first one's. The disk is now changed by a save and by the deliberate Clear Data, and by nothing else. `test_results_survive` walks a session and fails on the old code in four places |
| M1 | **Memory grows through a session and does not come back** | **Answered, 16.09.2026: caches filling, not a leak -- and it stops.** Drawing every plot and opening four editors, over and over, grew objects by 1 300 a round for a dozen rounds and then by 5: matplotlib's text metrics are an `lru_cache(4096)`, filled by a new renderer per tab. The resident set flattens with it, 339 MB to 378 MB over twenty-four rounds. What else grows is bounded by settings. Two real leaks were fixed on the way, and `test_memory_bounds` holds all of it |
| I2 | **A download started and could do nothing** | **Answered, 06.10.2026, within the hour of 1.18.0 reaching three machines: the Calculate dialog was empty and editing a scan refused.** MSB derives what an application offers by reading the source of its handlers, and a frozen build holds bytecode, so the catalogue came back empty and every request resolving a method by name failed. Running the same version from a checkout was fine, which is why 1 547 tests passed. Both packages' source ships in the build now, and `--selftest` runs the calculations and draws the plots rather than counting what is on offer -- so CI fails a build that cannot do its own work |

## Parked

| # | Item | Exit criterion |
| --- | --- | --- |
| L3 | Client-server | **Parked.** What it needs decided is storage, identity, and what a long calculation looks like to a caller who is not watching -- and those are answered by knowing who the callers are. Everything it would be built on is in place and does not go stale: a request is data, a session is a file, a project is a file |
| K1 | SKED | **Waiting for a real file.** No example here is certainly sked output, and an exporter written against a guess is a file that looks right and is not |
| G14 | What a plot shows when it has nothing to show | **Stated by the A3 audit, 28.09.2026, and standing.** Every plot handler builds a labelled empty plot when its filters select nothing -- axes, title, units, forty-eight call sites of it -- and every one of those is thrown away: the operation clears the figure for an empty answer, and the tab clears its canvas. What a user sees is a blank white panel. Either the empty labelled axes are shown, which means the operation returning them and the tab keeping them, or they are not built at all and forty-eight `labels={...}` blocks go. It is a decision about what the window should look like rather than a defect, and it is the user's. Exit: one of the two, with a form-pixel test of an empty tab |
| G15 | A rule about what a container holds, when a held item changes | **Stated by the A3 audit, 29.09.2026, and standing.** `@invariant` on a container is checked when its *composition* changes -- added, replaced, removed -- and msb_arch puts the items back when it refuses. Writing a field on an item it already holds changes no composition, so nothing re-checks: renaming one observation onto another's code was taken, saved, and then refused on the way back in by the rule that had not run, leaving a file that could not be opened. `ScheduleProject.set_observation_code` closes the one field in this application where it matters, by doing what msb_arch does for composition. The general case belongs in msb_arch and is a design question there: an item has no back-reference to what holds it, and giving every attribute write one is a cost paid on every write. Exit: either a container operation that writes through to a held item and re-checks -- `update_item(name, params)`, symmetric with `set_item` -- or a stated decision that the rule is the caller's to re-check, with the doctrine written down |
| E2 | What an equatorial mount is limited in, where the SEFD track cuts | **Stated by the A3 audit, 28.09.2026, and standing.** The track drops the samples outside `elevation_range`, because a flat atmosphere's airmass runs away at the horizon and a station whose limit is 15 degrees was drawing spikes of tens of millions of janskys at elevations it never uses. For an azimuthal mount that field *is* an elevation limit. For an equatorial one it holds declinations -- the same field, read as whichever the mount needs, which is how `source_visibility` and `az_el` already read it -- so the cut lands in the wrong place, and with limits of -90 to 90 it does not land at all and the spike comes back. What the right cut is, is a modelling decision rather than a defect to patch: either the track takes its answer from `source_visibility`, which already applies each mount's own limits in its own frame, or a station carries a horizon mask of its own, which is the thing an observatory actually publishes. Neither can be settled by the fixture. Exit: one of the two, with an equatorial station in the sensitivity tests. **The same field reaches a written schedule**: `$ANTENNA` states `horizon_map_el` from `elevation_range`, which for an equatorial mount is a declination limit written as a horizon -- a plausible wrong answer in a file a correlator reads, and the same decision resolves it |

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
| **1.16.0** | **U1.** One palette, as tokens, from which the window's stylesheet and the plots' colours are both generated -- light and dark, chosen in Preferences, following the desktop by default. Everything is styled, including what no form mentions: scrollbars, the buttons of a spin box, the calendar under a date, a tooltip. The icon set takes its ink from the palette rather than shipping twice. The toolbar says what its buttons do, the telescope editor is four groups instead of fourteen rows, every dialog names the button that does the thing, and the number column shows its own `#` |
| **1.17.0** | **A3.** The fifth audit: every module read once against what it is *for*. Twelve passes, sixty-eight findings, seventy-six tests added. A spacecraft placed by Keplerian elements stood 32 960 km from its own elements at the epoch, because a true anomaly was propagated as a mean one and the one test for it used a near-circular orbit; an equatorial mount was blind before transit, because its limits were read as a straight interval rather than an arc; renaming an observation onto a code another one carries was taken, saved, and refused on the way back in by the rule that had not run, leaving a file that could not be opened; and 801 of the 1 633 names in the shipped source catalogue could not be searched for, because a search box read what was typed as a regular expression and half of those names hold a `+`. Four findings are decisions rather than defects and stand as E2, G14, G15 and G16 |
| **1.18.0** | **W1, D1, I1.** The prose held to one style and counted, history included. The manual whole: thirteen pages, 39 screenshots made from the application against a schedule it generates. A download per platform that installs and starts with no Python, built by a tag and started by the machine that made it |
| **1.18.1** | **I2.** A build carries the source MSB derives it from, and `--selftest` does the work rather than counting it. The log moved beside the settings |

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
- **A test that runs from a checkout says nothing about a build.** 1 547 of them passed and
  1.18.0 shipped a window that could do nothing, because what breaks in a frozen build exists
  only there. A build is now asked to calculate and draw, by the machine that made it.
