# Changelog

All notable changes to pAstroCORE are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Dates are ISO-8601.

What is planned, and what was measured on the way to deciding it, is in
[`docs/ROADMAP.md`](docs/ROADMAP.md).

## [Unreleased]

W1: the prose cut down to one style. A one-line summary and Google sections in a docstring,
`Notes` only for what a caller must know, a comment of two lines saying why, a paragraph of
four. Every docstring and comment in `pastrocore/`, every `.md` in the repository, and every
commit message from 03.08.2026.

The style is a measure rather than a taste: `tests/test_house_style.py` counts what each file
owes it, and the number may only go down. 889 places did not meet it when the pass started and
none do now, so both ledgers are empty and the style is a gate.

**The history was rewritten.** 266 commit messages, each one subject of 72 characters or fewer
with its own date, and a body of short paragraphs. The 34 tag objects were rewritten with it
and force-pushed. Every tree is byte for byte what it was, and the releases on GitHub still
point at their tags.

Found while reading: the README described the stylesheet as a file, which U1 replaced with
tokens in `pastrocore/theme.py`.

## [1.17.0] - 2026-09-30

A3, the fifth audit: every module in `pastrocore/` read once against what it is *for*.
Twelve passes over eight days and sixty-eight findings, each ending in a fix, a test that would
have caught it, or a line in the roadmap saying why it stands. Seventy-six tests were added,
three files of them new; the suite is 1 427 passing and 19 skipped.

Recalculate any project holding results for a spacecraft placed by Keplerian elements, or for
a station on an equatorial mount.

### Fixed

#### What was computed

- **A spacecraft placed by Keplerian elements stood in the wrong place.** The editor asks for
  a true anomaly and the propagation carried it forward as a mean one, which is the same number
  only on a circle: 32 960 km out at e = 0.6, at the epoch itself. Converted through the
  eccentric anomaly, and checked at four eccentricities against the equations in the test.
- **An equatorial mount could not see the sky before transit.** An hour angle runs -180 to 180
  and a telescope is created with limits of 0 to 360; read as a straight interval, every sample
  before transit fell outside them. A station observing entirely before transit saw nothing. The
  limits are an arc on a circle, and are read that way for the azimuth too.
- **A stored result was handed back for another question.** The rule that a parameter is part of
  the question was written three times, and the next calculation to take a parameter would have
  had none of it. One rule now, over the parameters each result declares it records.
- **A copy answered to another object's name**, so its results were looked up under a name
  something else already holds; and a fingerprint read `name` and `type`, so renaming or copying
  a collection made every result stale although nothing it was computed from had changed.
- **A valid ephemeris was refused.** A CCSDS OEM line may carry an acceleration after the
  velocity; every line was required to have exactly seven fields, so such a file came back as
  "must contain at least 2 data points" -- the complaint about its length rather than its columns.
- **A beam pattern was refused when no source was active**, and said "No active telescopes",
  which was neither the reason nor true. A dish's beam is the dish.
- **Clearing results said it had done so when it had not**, a result whose times were all missing
  was lost whole rather than losing the two entries describing it, and the residency budget held
  each owner strongly -- so an observation removed from a project kept its results in memory for
  the rest of the session.
- **A spacecraft placed by Keplerian elements could be saved and not loaded**: the epoch came
  back as a string and was handed on unparsed.

#### What was written out

- **Packing a project took its results away from the sender.** A package is written by saving
  the project into a temporary directory, and a save moves the project in. A project opened with
  eleven results had none the moment it was packed; an unsaved one lost them outright.
- **What a reader could not read, it dropped in silence.** A VEX station with no position, a
  source with no coordinates, a scan with no start, and the same in CFX: each was a bare
  `continue`, so a file came in with fewer than it holds and the report called it a clean read.
  Each is named now, as is a scan reduced by stations, bands or a source the file never defines.
- **A scan shorter than a second was written as no scan at all.** Both writers rounded to whole
  seconds, so four tenths went to a correlator as `0 sec`.
- **`Time Arrays` could not be exported**, because its handler's name and its store key differ;
  ticking everything in the export dialog wrote every file but that one, with the reason at debug
  level. The same mistake told a dialog an observation did not hold a result it was holding.
- **Three files were written in place** -- a session, a schedule and the settings -- each of them
  a file that a write interrupted part way leaves unreadable. Beside and moved over, like
  everything else this application writes.
- **A catalogue saved by an editor that writes a byte order mark came back empty.** Three bytes
  before the first brace, and the reader -- which decides JSON by that brace -- read the whole
  file as the old `.dat` format and answered with no sources at all. Every file a person may have
  written is read with `utf-8-sig` now.

#### What was drawn

- **The resolution a caller asked for was ignored.** The save that honoured `dpi` was behind a
  status a plot handler has never set, so asking for 300 gave the same 727x463 image. A plot for
  a paper can be got out of this application now.
- **A baseline in Earth diameters grew with the frequency.** Both baseline plots divided by the
  wavelength and then by the Earth's diameter *in wavelengths at the lowest frequency drawn*, so
  the same baseline came out twice as long at twice the frequency.
- **A position was written north of the equator by the table that shows it.** The sources tab
  took the sign from `de_d >= 0`, true of the `-0.0` a declination between -1 and 0 carries; it
  rounded seconds apart from their minutes; and it printed them three digits wide. The source
  answers all three, and the catalogue dialog was already asking it.
- **An export named pictures it did not draw**, and two forced collections in the drawing path
  cost 2.34 s against 0.90 s over eighteen plots to save nothing measurable.

#### What the window did

- **Replacing a project asked about unsaved results at one door of four.** New Project, Open and
  the recent list each replaced it without a word; an hour of calculation left the window in
  silence. All four ask now.
- **"Clr" discarded every result of every selected observation on one click**, said "Success"
  afterwards, and told the window nothing -- so the explorer went on listing results that were
  gone.
- **Renaming an observation onto a code another one carries was accepted, saved, and refused on
  the way back in** by the rule that had not run. The file could not be opened again. The rename
  belongs to the project now, because the rule does.
- **The search boxes took a pattern rather than a name.** 801 of the 1 633 names in the shipped
  source catalogue hold a `+`, which in a regular expression is not a plus: searching for a
  source by the name it was copied from found nothing, and an unclosed bracket emptied the table.
- **Moving a scan's start changed how long it is.** Correcting a start by an hour took an hour
  off the scan; correcting it by more than the scan lasts left a scan of one second.
- **"Active in this observation" was asked and ignored** -- the saved value was recomputed, so a
  scan unticked came back active.
- **The two station editors wrote before they checked**, so a code the form itself rejects was
  already on the station the observation holds, through the refusal, through Cancel, and into a
  written schedule. All four editors are handed a copy now, as the catalogue dialog's already was.
- **The source editor rewrote a spectrum on every save.** The flux table was shown to two decimal
  places and read back from what was shown, and anything under five millijanskys became `0.00`,
  which the dialog then refused as not positive. A spectral index of zero -- a flat spectrum,
  which is what most VLBI calibrators have -- was stored as "not measured".
- **Closing an observation tab put a `NoneType` error in front of the user** instead of closing,
  and the four tabs it holds were destroyed without being told to let go of the observation, the
  orchestrator and the project.
- **A project opened from a package was drawn in the light palette** whatever the theme.

### Added

- **`ScheduleProject.set_observation_code`**, which is how an observation is renamed: the rule
  that no two may share a code is the project's, and a rename is the one change to what it holds
  that msb_arch does not re-check.
- **`Observation.get_telescopes_a_scan_needs`**, **`OBSERVATION_TYPES`** in the interface, and
  **`UV_UNITS`** in the visualizer -- three answers that were written out in three, eight and two
  places respectively, one of them in a form.
- **Seventy-six tests**, including three new files: the editors, the operation dialogs and the
  project tab, none of which had any. Among them a Keplerian orbit checked against its own
  equations at four eccentricities, a baseline checked against the geometry at two frequencies,
  and eleven visualization tabs checked for something actually being on their axes.
- A convention test apiece for: a search box that filters on a pattern, an observation type
  written out rather than asked for, a private call to a method nothing defines, an example in a
  docstring that does not import, and a comment in a second language.

### Changed

- **`BaseEntity` and the containers came from msb_arch 3.1.0**, which is where the rule that a
  name is an identity now lives, so this project carries no code for it.
- **The interface asks where it used to list.** The observation types, how many telescopes a scan
  needs, the units a baseline is measured in, the analyses on offer and the logging levels were
  each written out in the interface; all five are the backend's answer now, and a sixth -- the
  calculations -- was already.
- **Nine visualization tabs share one `update_visualization` again.** Three carried a copy of it
  that differed in one line, because the declaration of what counts as drawn could name only one
  field. It names as many as the plot answers with.
- **A calculation removed from the selection stops being offered its parameters.** The refresh
  ran only when a calculation with prerequisites was ticked, so Clear All left a detection
  threshold offered to nothing.

### Standing

Four findings are decisions rather than defects, and are in
[`docs/ROADMAP.md`](docs/ROADMAP.md) with what each would take: **E2**, what an equatorial mount
is limited in; **G14**, what a plot shows when it has nothing to show; **G15**, a container's
rule when a held item changes; **G16**, a write of several fields that one of them refuses.

## [1.16.0] - 2026-09-21

U1: one palette, two themes, and no element left in the platform's default.

### Added

- **`pastrocore/theme.py`: the look, as tokens.** A palette per theme, one type scale, one set
  of spacings and radii. The window's stylesheet and the visualizer's colours are both generated
  from them, so a colour is changed in one place and everything follows.
- **A dark theme, and a light one**, chosen in Preferences -- `System`, `Light` or `Dark`.
  `System` follows the desktop. The plots follow the window: a dark window no longer holds a
  white rectangle where a figure is.
- **Everything is styled**, including what no form mentions and everybody sees: scrollbars, the
  buttons of a spin box, the calendar a date editor drops down, progress bars, tooltips, menus,
  a tree's branches, the corner of a table. The glyphs Qt draws itself -- a green arrow on the
  calendar, a grey square where a spin box's arrow belongs -- are generated from the same tokens.
- **The icon set takes its ink from the palette.** Each icon states its stroke once, so a theme
  repaints the whole set rather than shipping it twice; windows opened after a theme change are
  painted as they are shown.
- **A filter over the project explorer**, which survives a rebuild of the tree, and a count
  beside `Observations`.

### Changed

- **The toolbar says what its buttons do.** Thirteen unlabelled icons were thirteen guesses; the
  labels are short ones, so a menu still says "Export Calculated Data..." where a button says
  "Results".
- **The telescope editor is four groups** -- what it is, where it stands, the dish, where it can
  point -- with the coordinates and the velocities side by side. It was fourteen rows in one
  column, taller than a laptop screen.
- **Every dialog names the button that does the thing.** Styling whichever button Qt made the
  default had painted Cancel blue in the scan editor and Add in the source editor.
- `Active:` beside an empty tick became a tick that says what it is, here and in three editors.
- The project tab's search moved from under its table to beside it; the calculation dialog's
  parameters read as two groups, `Run` and `Sensitivity`.

### Fixed

- **The number column showed no `#`.** It was sized to its contents after every refill, so it
  came out one digit wide and Qt drew the sort arrow over the heading. All six tables size it in
  one place now.
- **Opening a project drew its plots in the light palette**, because a project comes with a new
  orchestrator and the theme had been applied to the old one.
- **The telescope editor labelled velocities m/s**; the model holds metres per year, which is
  what VEX writes -- reading them as m/s once put stations 9 500 km out.
- **The scan editor's OK button was spelled with a Cyrillic O and K.** It looks right, and
  nothing that searches or translates the interface can see it.
- **Three forms shipped showing their own scaffolding**: `lblSummary` and
  `[get_start_time_date]`. Something fills those at run time; until it does, that is what a user
  reads.

### Upgrading from 1.15.0

| What you see | Why | What to do |
| --- | --- | --- |
| The window looks different | U1: one generated palette, in place of a stylesheet assembled out of 224 inline properties | Nothing. **Preferences -> Theme** chooses `System`, `Light` or `Dark` |
| `pastrocore.qss` is no longer in the package | The sheet is generated from the tokens | A `pastrocore.qss` of your own, beside your settings, still replaces ours whole |
| A plot saved before this is lighter than one saved now | Figures follow the theme | Redraw, or set the theme to `Light` |

## [1.15.0] - 2026-09-18

E1: how well a schedule would be heard, and whether it would detect anything.

### Added

- **Three calculations, and none of them guesses.**
  - **`sefd`** -- each station's SEFD in each band, and where it came from: the station's
    SEFD table, or `2 k Tsys / A_eff` from its system temperature and effective area, or none,
    with the reason. Asked with `fill` it writes what it computed into the station's own table
    over the band -- the one thing E1 writes into the model -- and never over a measurement.
  - **`sefd_track`** -- that SEFD along every scan, on the time grid. A quoted SEFD is the
    one at zenith; away from it the source is dimmed, the system is warmed and the gain is the
    one where the dish points: `SEFD = SEFD_zenith e^(tau0 (A - 1)) Tsys(el) / Tsys_zenith
    g(90) / g(el)`, `A = 1/sin(el)`. Nothing is given where the station does not point.
  - **`baseline_sensitivity`** -- per scan, baseline and band, and for the bands together:
    the time both stations see the source, the noise summed over it at the SEFDs each piece had,
    the signal-to-noise, whether it detects, and the shortest scan that would. Checked against
    the VLBA's published baseline sensitivities.
- **The weather and the gain curves are parameters of a run, not properties of a station**:
  `opacity` rows `[f_min, f_max, tau0]` and `t_atm` in kelvin, and `gain_curve` by station code.
  They are recorded with the result, so changing them is another answer. A curve is taken as
  `g(90)/g(el)`; an opacity without an air temperature is refused rather than half applied.
- **Each draws itself**: SEFDs as bars on a log scale, measured plain and computed hatched;
  the track as a line per scan with the zenith behind it; detection as a grid of baselines by
  scans, with every cell under the threshold crossed out. Each has its tab, and exporting needed
  nothing: the catalogue says what there is.
- **The calculation dialog asks for what a calculation takes** -- a detection threshold, the
  bits per sample, the zenith opacity, the air's temperature, a gain curve per station -- and
  offers each only when a ticked calculation takes it. Which one takes what is read off what its
  result records, and the recordings on offer are `inspect(method="recording")`.
- **A refused step says why** in the run report, not only in the log.

### Changed

- **A telescope's measured tables are rows of `(f_min, f_max, value)`** -- SEFD, system
  temperature, aperture efficiency, effective area. A band takes a value only from a row covering
  its frequency, and rows in one table may not overlap. `get_sefd` interpolated across the table,
  which made a 22 GHz SEFD out of an L-band and a Q-band measurement.
- **A source's flux is a power law** between measured frequencies, and beyond them only with a
  spectral index, from the nearest point: `Source.get_flux_estimate` says how it was got.
- `Telescope.add_sefd(frequency_min, frequency_max, sefd)` takes the range it holds for.

### Removed

- `Telescope.calculate_sefd`, `calculate_effective_area` and `calculate_surface_efficiency`:
  unused, writing into the tables, and `calculate_sefd` had lost the conversion to janskys --
  1.8e-25 for an 18 Jy dish. `get_sefd_estimate` and `get_aperture_efficiency` replace them.

### Upgrading from 1.14.0

| What you see | Why | What to do |
| --- | --- | --- |
| A telescope's tables show a range per row | They are rows now; one written before reads as a row covering its one frequency, with no range made up | Widen the rows the receivers really cover, in the telescope editor |
| Results show as stale once | A telescope is written in its new form, so the fingerprint of what results were computed from moved | Run the calculations again, or leave them: nothing is recomputed unasked |
| `add_sefd(frequency, sefd)` raises `TypeError` | It takes the range: `add_sefd(frequency_min, frequency_max, sefd)` | Pass the range |
| `calculate_sefd` is gone | Replaced by `get_sefd_estimate`, which says where the number came from | Use `get_sefd_estimate(frequency)["sefd"]` |

## [1.14.0] - 2026-09-17

L4: everything the window can ask, from a terminal.

### Added

- **`pastrocore-cli ask <project> <operation> <address> key=value`** sends any request the window
  can make -- the request itself, on one line:

  ```bash
  pastrocore-cli ask survey.pastro inspect OBS001/telescopes get_items
  pastrocore-cli ask survey.pastro configure OBS001/sources deactivate_item=3C273
  pastrocore-cli ask survey.pastro compute project method=run calculations='["uv_coverage"]' targets='["@OBS001"]'
  ```

  A value is JSON when it reads as JSON and text otherwise; `@address` passes the object there. A
  request that changes the project -- `configure`, `calculate`, `compute` -- saves it, as `run` and
  `replay` do, and `--dry-run` does not. `--json` prints the answer whole; the readable form shows a
  table of results by its size and first rows.
- **`pastrocore-cli shell`** takes the same lines one after another. Tab completes the
  operation, the address a level at a time, the methods an object has, a handler after `method=`
  and an address after `=@`. Nothing is saved until `save project`, and what was typed is
  recorded, so `export project method=journal` writes a session that `replay` runs again.
- **Addresses as a person names things**: `project`, `OBS001`, `OBS001/sources/3C273`,
  `OBS001/telescopes/ALMA` by code or name, `OBS001/scans/#3` by position. Four `inspect`
  questions answer them -- `locate`, `address`, `contents` and `offers` -- read from MSB's model
  graph, so a part added to the model is addressable without a change here.
- **No command table.** The operations, their handlers and the methods an object has are asked of
  the orchestrator, so a mistake is answered with what was meant -- "Nothing called 'telescops' in
  OBS001 -- did you mean 'telescopes'?" -- and a change asked of `inspect` names the `configure` line
  that would do it.

### Fixed

- **A released project could be saved over its own directory.** `compute release` lets go of what a
  project holds, and a save drops the results of observations it no longer has -- so saving after it
  wrote an empty project and deleted its results. Nothing in the window did that; a command line
  that saves after a change would have. A released project refuses to be saved, for every caller.

### Upgrading from 1.13.0

| What you see | Why | What to do |
| --- | --- | --- |
| `pip` installs `prompt_toolkit` | The shell completes with it, the same on every platform | Nothing |
| `ValueError: Project ... was released` | A project was saved after `release` | Open the project again, then save |

## [1.13.0] - 2026-09-17

Two roadmap items, C1 and S1, and msb_arch 3.0.0 -- released for this, since the second needed the
framework to mean what its operations are called.

### Added

- **C1: the catalogues are edited.** Options -> Sources Catalog and Telescopes Catalog add,
  edit and remove entries -- a space telescope too -- and save, to the catalogue's own file or a
  new one. An edit is made at once, so the generator and every Add from Catalog see it; closing
  with unsaved edits asks, and Discard puts back what the file holds.
- **A catalogue is JSON**: the same `Sources` and `Telescopes` a project holds, written whole
  and atomically, so an SEFD table, a pointing limit or a spacecraft has somewhere to go. A
  `.dat` catalogue still opens and is saved as JSON, and each shipped catalogue is checked to
  read back equal to the `.dat` it was converted from.
- **The catalogues that came with the application are never written**: an upgrade replaces them
  and an install may not be writable, so saving one asks for a name in a `catalogs` folder beside
  the settings, and the application reads that file from then on.
- **S1: a session is cut down to what is worth repeating.** Tools -> Session shows only the
  requests that change something, leaves selected rows out and saves what is shown. Everything is
  still recorded. A replay does not ask the questions again and says how many it left out; a
  session saved by 1.12 still replays.
- The session table's **Call** column says what each request called: the operation's handler when
  one was named -- `run` -- and the model's methods otherwise -- `create_item`. It was Method, which
  is the handler alone, and empty for nearly everything the window asks.

### Changed

- **Requires msb_arch 3.0.0**, where `inspect` only reads: it calls `get` and methods named
  `get_*`, `has_*` or `is_*`, and refuses anything else. Four methods that read under other
  names are renamed: `get_observations`, `get_right_ascension_parts`, `get_declination_parts`
  and `is_activatable`.
- **The questions are `inspect`.** What can be calculated and in what order, what a session
  held, what is stale, which results exist and how many are unsaved were `compute` and `export`,
  so a session could not tell a question from a change. `compute` now runs, clears, releases and
  replays, `export` writes files, and `ScheduleManipulator.READING` says which only read.

### Fixed

- **Deactivating a source was recorded as a read**, and a failure of it showed no error box. It went
  through `inspect` since 24.09.2025, when two requests were folded into one line and kept the first
  one's operation. The other three tabs used `configure`; this one does now, and a test reads every
  `inspect` call in the code against msb_arch's own rule.
- **The shipped sources catalogue read `$` as a name**: 138 sources had an alternative name of `$`,
  the files' mark for none, and every gravitational lens did. **A name with a space was split in
  two** -- `Mrk 1419` was a source called `Mrk` with the J2000 name `1419`, and `IRAS 16293-2422` the
  same. The names are separated by tabs, and are read that way.
- **An edit refused by the catalogue's editor, then cancelled, stayed in the catalogue**: the editor
  writes into the object it is given before its checks run. It is given a copy.
- **A session file's handler was never checked.** A facade call records the handler among the
  attributes, and `check` read only the request's own key.
- A failed request no longer keeps what it named alive in any logging handler that keeps records --
  fixed in msb_arch 3.0.0, found here.

### Upgrading from 1.12.0

| What you see | Why | What to do |
| --- | --- | --- |
| `pip` refuses to install, or `RequestError: inspect only reads` from your own script | msb_arch 3.0.0 is required, and `inspect` now calls only reads | `pip install -U msb_arch`. In a script, ask `configure` for a change, and use the renamed methods above |
| Nothing | Your settings named the shipped `sources.dat` and `telescopes.dat`, which are JSON now | Nothing: the paths are corrected in the settings once, and nothing is said at every start |
| `compute(method="catalogue")`, `"stale"` or `export(method="unsaved")` fails in your own script | The questions moved to `inspect` | `inspect(method="catalogue")`, and so on. A saved session needs nothing: it is read the new way |
| A `.dat` catalogue you chose in Preferences | It still opens | Save it from its manager to have it as JSON |

## [1.12.0] - 2026-09-16

### Fixed

- **Opening a second project deleted the first one's results** (R1), out of the directory it
  had just been saved to, with nothing said. A `release` asked every observation to clear its
  results, which erases them on disk as well as in memory. What changes the disk now is a save
  and the deliberate Clear Data, and nothing else.
- **A saved project called its results unsaved for ever** (R1). A save copies them out of the
  session's scratch rather than moving them, and nobody cleared the copies -- so closing the
  window asked about results already saved and then refused to close. A save clears the scratch
  when it has finished writing.
- **Memory climbing through a session** (M1) was measured rather than argued about: it is
  caches filling, and it stops as matplotlib's text-metrics `lru_cache(4096)` fills. The journal
  and the results in hand are bounded by settings. Two real holds were fixed: the visualization
  dialog removed a tab without closing it, and did the same when it was closed itself.
- Editing a frequency in the generator had always ended in an error box: it called a method the band
  editor was renamed out of years ago, and nothing reached the call.
- The generator's Save and Load buttons were disabled in the form and enabled nowhere, so neither had
  ever been pressed.

### Added

- **O1: a generation is a plan.** Sources, stations, bands, times and pattern save to a file
  and load back into the dialog whole, where a preset used to keep the timing and drop what it
  was for. How long a pattern takes and what duration fits a given end are the backend's
  arithmetic, and the two built-in patterns come from the model.
- Tests that hold what was found: a session of ordinary work loses no result file; a window
  keeps the results of the project it replaces; a save takes its scratch copies with it; ten
  plots opened and closed leave no tab and no figure; the journal stops at the size it was
  given; and a control disabled in a form that no code enables fails the build.

## [1.11.0] - 2026-09-16

Stage 2 of the roadmap: the main window.

### Added

- **A toolbar** (G11) of twelve of the menu's own actions -- the same `QAction`s, so an action the
  window disables is disabled in both places.
- **Keyboard shortcuts** (G12), seventeen of them: the platform's own keys where there is one --
  New, Open, Save, Save As, Quit -- plus `Ctrl+R` to calculate, `Ctrl+Shift+V` to visualize,
  `Ctrl+G` to generate, `Ctrl+J` for the session, `F1` for about. No two actions answer to the same
  keys, which a test holds to.
- **A status bar** (G13): the last thing the log said, in the colour of its level, and what
  the process is holding, re-read every two seconds. It reads the log rather than being written
  to from call sites, so everything the application already reports arrives without being wired
  up, including from a calculation running in a thread.
- **Thirteen new icons and nine redrawn** (G10). Every action has its own now: a project packaged
  in and out, an observation in and out, the correlator's file in and out, results leaving,
  analysis, generation, the session, the explorer, the two catalogues, the run report. All of them
  24x24, strokes only, one colour stated once on the root, width 2, round caps and joins.
- `test_icons` and `test_main_window`: an action without an icon, two actions sharing one, an icon
  outside the style or missing from the resource, an icon that renders blank, a toolbar button that
  is a copy rather than the action itself, two actions on one key, and a status bar that does not
  follow the log all fail the build.

### Fixed

- A convention test turned logging off for the whole process with `logging.disable` and never put it
  back, so every test after it ran silenced.

## [1.10.0] - 2026-09-15

Stage 1 of the roadmap: what got in the way every day.

### Added

- **G7: Select All and Clear under every list a plot is chosen from** -- sources, scans,
  telescopes, baselines, frequencies. Two hundred baselines and one of them wanted is two clicks,
  and a whole list is ticked with the plot drawn once. The buttons are found by the name of their
  list, so a list added to a form gets them by being named like the others.
- **G9: saving shows how far it has got.** Each result file as it is written, then the model,
  with the window answering throughout. A save that takes no time shows nothing, and a save has
  no Cancel -- stopped half way it would leave the project directory half new. Opening a project
  has no progress window: it reads the model alone, a tenth of a second.
- `test_form_layout`: every form laid out as authored and at its smallest, each tab page in turn,
  fails on overlapping widgets, cut-off text, squashed fields and windows pinned to a size.

### Fixed

- **G8: nothing on a form overlaps or is cut off.** Twelve dialogs pinned their window to one
  size: five were smaller than their own layout, and the other seven fitted Arial on Windows and
  cut their labels with a wider font. A window is now as large as its layout says, and the
  catalogue browser can be made larger for a catalogue of hundreds.
- The progress window's bar spans it, Cancel sits a little lower, and a long message is shortened
  in the middle, with the whole of it as the tooltip.
- **Beam pattern with many stations.** Each code was its panel's title and sat on the angle labels of
  the panel above, and the legend lay over the top row. Codes are inside their panels and the figure
  is laid out by what is on it, again on every resize.
- Closing a visualization tab never cleared its figure: every close logged "Could not clear the
  figure on close" and kept the plot's arrays.
- Tests: every run is on the offscreen platform, which is what made regenerating the form pixels
  from one file rewrite 25 of 26 digests; and the pixel harness no longer reads an image freed under
  it, which crashed it now and then.

## [1.9.3] - 2026-09-15

### Fixed

- **A redraw emptied nothing, on every plot.** A visualization tab owns one figure and hands
  it to the visualizer with each request, and the visualizer drew into it without clearing it,
  so each redraw added its axes, titles and legend on top of the last. A borrowed figure is
  cleared before any plot draws, and its margins go back to the defaults.
- **Az/El with many stations.** Each station's name was its panel's title and sat on the plot
  above, and fixed margins left a third of the figure empty; the name is inside its panel now.
  Besides: only ten stations were drawn however many were ticked, every time tick read the same
  whole MJD, and lines ran through a wrap at 360 and across hours below the horizon.
- **`invalid value encountered in arcsin` from the Mollweide plot**, when the cursor left the
  sky. matplotlib asks where the cursor is as it leaves the axes, and its inverse Mollweide
  answers for points outside the ellipse. The tracks are drawn on `SkyMollweideAxes`, whose
  inverse answers NaN off the sky and matplotlib's own value on it.

### Added

- Every plot type is drawn twice into one figure and required to hold what it held after the
  first time; unticking Az/El stations leaves only their panels; the cursor leaving the Mollweide
  ellipse raises no warning. Each fails without its fix.

## [1.9.2] - 2026-09-15

### Fixed

- **The Mollweide tab opened and never drew, and neither did the two spacecraft tabs.** A
  visualization tab owns one figure and hands it to the visualizer with each request. These
  three wrote their request from scratch and left the figure out, so the visualizer drew into
  one of its own and the tab showed its empty one. They add to the base's request now.

### Added

- Every visualization tab, found rather than listed, is required to have something drawn on the
  figure it shows. The check it replaces, `tab.canvas is not None`, held for any tab, drawn or not.

## [1.9.1] - 2026-09-15

### Fixed

- **Orbits were interpolated for observations with no spacecraft to follow.** Positions call the
  interpolation step, and the framework derives requirements from what calls what, so an array of
  ground stations had it planned anyway. It ran, found nothing, and logged four warnings on every
  calculation -- cached data empty, an empty result, stored, no data computed.

  What it takes for a step to have something to do is declared beside its result (`only_if`,
  a question for the observation), and a plan asks the model before including the step.
  `Observation.has_orbit_file_telescopes` answers it, and `SpaceTelescope.follows_orbit_file`
  replaces four copies of the same check in the calculator.

## [1.9.0] - 2026-09-15

A fourth audit, run against real schedule files and at the size of a real schedule rather than
against the fixture -- one scan, two stations that do not move, no source near the equator. That is
where everything below was hiding.

### Fixed

- **A station with a velocity was placed thousands of kilometres from where it is.** A ground
  station's velocity is metres per year -- VEX `site_velocity`, CFX `TLSC_PAR` -- and the
  position multiplied it by seconds since J2000: Westerbork, Svetloe and Badary landed inside
  the Earth. **Recalculate any project whose stations came from a VEX or CFX file.**

- **A source between -1 and 0 degrees was written north of the equator.** Its sign lives in -0.0,
  and three places read that as positive: the VEX writer (`+00d30'` for -0°30', up to two degrees
  from where it is, in a file meant for a correlator), the catalogue's table, and the source editor,
  which moved such a source across the equator whenever it was saved. The editor has a sign field.

- **Editors rounded what they had not been asked to change.** Saving a source rounded its seconds to
  three places, 7.5 milliarcseconds; saving a telescope rounded its velocity to centimetres a year
  (-0.01353 to -0.01) and its position to centimetres; Keplerian elements to three and two places.
  Each field now holds the precision the formats write.

- **The edges of a position.** 360 degrees of right ascension carried to 24 hours, which the model
  refuses, so such a source could not be read. Seconds were bounded at 59.999 and refused 59.9995
  from a catalogue or a VEX file. Seconds rounded on their own wrote 59.99999999 as `60`. The model
  now splits a position with the carry, and the writer and the table ask it.

- **Linear feeds were dropped without a word.** VEX and CFX files with `X` and `Y` came in with no
  polarization at all.

### Added

- **X and Y polarizations**, a group of their own -- not H and V, since a feed's orientation is the
  station's. A letter neither reader knows is named in what was passed over.
- A physics test for a moving station, held to astropy within a centimetre.

### Changed

- **A calculation grows with the schedule instead of with its overheads.** Ten stations over
  fifty scans took 16.8 s, because every step worked one scan and one station at a time and each
  transform has a fixed cost. The topocentric transform and the rotation to GCRS are done once
  for the whole observation now. Fifty scans: 6.7 s; two hundred: 24.5 s -- linear.

## [1.8.1] - 2026-09-15

### Fixed

- **Cancel would not close the calculation, export or generation dialog if nothing had been
  started in it.** Introduced in 1.8.0. Each dialog kept its worker in `self.thread`, and on any
  Qt object that name is the method `thread()`, so a dialog closed before starting anything
  failed on `isRunning` and stayed open. The worker is `self.worker` now.

  A visualization tab had the same shape -- its plot's layout in `self.layout`, the name of
  `QWidget.layout()` -- and it is `plot_layout`.

### Added

- The three dialogs are tested built for real, with Cancel pressed before anything starts. The test
  that let this through built them without their constructors and always gave them a thread.
- A convention test refuses an attribute on a widget that hides a Qt method of the same name.

## [1.8.0] - 2026-09-14

A third audit, and the first to check the numbers against physics rather than against themselves.
Two results were wrong, two test harnesses could not have noticed, a failed save destroyed what it
replaced, and a full calculation takes less than half the time it did.

### Fixed

- **The beam pattern was drawn pi times too wide at every frequency.** A result holds one
  curve per dish and the plot gives it the frequency chosen in the tab. The curve keeps
  `x = D sin(t)` and the Airy pattern has `x = pi D sin(theta) / lambda`, so the angle is
  `sin(theta) = lambda sin(t) / pi`, where the plot drew `theta = t * lambda`.
- The axis is in degrees now and each station has its own scale, a large dish's beam having been
  a line on a shared one.

- **Time on source lost one sampling step from every block.** A block of k samples was
  measured from its first sample to its last, k - 1 steps: a source seen in one sample was on
  source for zero seconds, and a scan visible throughout came out shorter than the scan. The
  fixture's blocks now end at 00:20 with 32400 s, which is what the analysis tab already said.

- **"Total" on the time-on-source plot stopped at the first of two touching scans**, so two hours
  in common across two scans were reported as one. It counted open telescopes in a set, and at
  the seam the start of the second scan was a no-op and the end of the first removed the station.

- **A save that failed part way destroyed the saved result it was replacing.** Results and
  `project.json` were written in place, and a parquet write truncates before it encodes: a full
  disk left the result at zero bytes, and `project.json` a project with nothing to open. Every
  file is written beside the old one and moved over it now.

- **A window idle for an hour lost its scratch to the next window.** An empty scratch directory's
  time never moves, so it looked like litter and was swept without asking whether its process was
  alive. Its results then went into a directory without a session marker, and after a crash there
  was nothing to offer back.

- **Escape on a progress window left the work running, and closing the application then aborted
  it** (`QThread: Destroyed while thread is still running`, 0xC0000409). Escape and the close
  button now cancel, and a dialog does not close ahead of its thread. The three copies of the
  progress window are one.

- **A generation that made nothing closed its dialog as if it had worked**, because the thread
  wrapped the generator's answer in `{"status": True}`. A cancel now names the observations
  already added instead of `[]`.

- **`run` and `replay` on a package** calculated everything, then failed on saving a directory
  over a file and lost it all. They refuse a package before calculating.

- **The beam pattern declared a dependency on the frequencies it never reads**, so editing a band
  marked it stale. A beam saved before this is reported stale once.

### Changed

- **A full calculation takes less than half the time.** On the fixture at a 60 s step: 2.22 s on
  the clock and 3.75 s of work, now 0.97 s and 1.05 s.
  - The Sun angle is taken between two directions -- the Sun from the station, the source -- in
    numpy, once per scan, instead of three astropy transforms per station: 1.12 s to 0.16 s. It
    agrees with astropy's topocentric `get_body` to 0.21", and for a spacecraft it now uses the Sun
    as seen from the spacecraft, where it had used the geocentre.
  - Visibility, az/el and the parallactic angle share one topocentric transform, cached by what it
    is made of and bounded in bytes; the parallactic angle is taken from altitude and azimuth.
    Az/el went from 0.81 s to 0.02 s, the parallactic angle from 0.70 s to 0.02 s.

### Added

- **`tests/test_physics.py`** derives every result a second way -- from astropy, or from the
  geometry the result claims to be: az/el, parallactic angle, Sun angle, visibility, uvw,
  baseline projections, Mollweide tracks, time on source and the drawn beam. Characterization
  says the numbers did not change; this says they are right.

- **Characterization compares times in seconds.** A relative tolerance on an MJD near 61000 is
  thirty days wide, so a result shifted by an hour passed.

- **The plot harness sees what a plot draws.** It read the offsets of `fill_between` polygons,
  which are all (0, 0), and compared MJD coordinates relatively: a time-on-source bar five minutes
  longer compared equal, difference 0.00. It now records polygon vertices, the labels a reader
  reads, and coordinates from the axes' origin.

## [1.7.2] - 2026-09-10

### Removed

- **Randomize Scan Order.** Each scan's start is set from its index, so shuffling the list
  changed the order the scans were added to the container and nothing else: the sequence they
  are observed in stayed exactly as it was. The tick claimed a randomisation that never
  happened.

  There is nothing for it to mean here either -- the generator makes one observation per
  source, so every scan in an observation is on the same source and there is no order to
  randomise. Gone from the backend, the dialog, both presets and the form.

### Fixed

- **The connection register grew when connections were made twice.** Introduced in 1.7.1:
  `setup_connections` appended to it and never started it empty, so a caller that connects twice
  without clearing left the register holding each pair twice. Both registers start empty now.

### Known

- **The form-pixel reference does not see a tab that is not showing.** A form is grabbed as
  it appears, so a change on any other tab of a `QTabWidget` leaves its digest identical.
  Widening the harness to walk every tab would rewrite all 26 digests, so it is recorded here.

## [1.7.1] - 2026-09-10

A second audit pass, over the parts the first one did not reach: the visualizer, the
catalogues, the analyzer, the generator and the window. Seven defects, every one of them
found by asking the same question -- does this call reach something that is actually there.

### Fixed

- **Two projects opened, one tab closed, two tabs gone.** `setup_connections` runs again on
  New Project, Open Project and Open Package, and `clear_connections` was meant to take the
  previous set back first. It asked `receivers(QtCore.SIGNAL(...))` whether the signal had any
  connection at all, which counts everyone else's and misses the new spelling.
- The guard passed, the disconnect did nothing, and every reopen left another connection behind:
  `handle_tab_close` ran twice for one click, and after the first removed that tab the index
  belonged to its neighbour. What is disconnected is now what was connected, from a register.

- **Editing a source switched off every scan pointed at it.** The activity check asked
  `self.source in observation.get_sources().get_items()`, and `in` compares every field: a scan
  holds a copy, equal until one is edited. Correct one digit of the declination and the scan
  counted as pointed at nothing. It is found by name now.

- **A copied scan renamed itself.** `Scan.copy` did not carry the name over, so the
  constructor invented one while `Scans.copy` filed it under the old key. Results are keyed by
  scan name, so a copied observation had no scan under the name its own results referred to.

- **Five catalogue lookups called names the containers do not have.** `get_source`,
  `get_telescope`, both range searches and `get_telescopes_by_type` called `get_all_sources()`
  or `get_all_telescopes()`, and two asked a source for `get_ra_degrees()` rather than the
  `ra_degrees` property. Every one was an `AttributeError` waiting for its first caller.

- **Unticking a source left its Mollweide tracks on the plot.** The filter went through a
  `source_name` column no track has ever had, inside the branch that ran when a source was
  *not* found -- so the ordinary case filtered nothing and the unknown case raised. A track
  names a scan, and the scan carries the source.

- **A coverage window reported the stations of a different window.** The count was `max` over
  every window of the source, so a night when two stations saw it and a night when five did
  were both reported as five.

- **A tab was cleaned up twice and called the second pass an error.** `close_tab` cleans and
  then removes the tab, and Qt delivers `closeEvent` afterwards: the second pass reached through
  attributes the first had set to `None`, logged as "Error cleaning up" for work that had been
  done. The suite's Qt warnings went from 76 to 31.

- **A telescope catalogue line without a diameter** was reported as unparseable rather than
  as too short: the guard read `< 6` while the diameter is the seventh field.

### Added

- A convention test that checks the whole codebase for a method called on a model that does
  not have it -- a parameter annotated with a model class, or an attribute assigned one in a
  constructor. This family has now been found twice by hand: `clear` became `remove_all` in
  msb_arch 2.0.0 and five callers kept asking for `clear`, and the catalogue lookups above.

- Tests for the catalogues, which had none, driven against the files the application ships.

## [1.7.0] - 2026-09-08

An audit: four bugs, the duplication the format work left behind, and a rule that was
costing minutes.

### Fixed

- **A position set in degrees did not read back.** `set_ra_degrees(338.1517)` put the whole
  value in the hours field *and* the fraction in minutes and seconds, so the fraction counted
  three times: back came 346.455. `ra_degrees` is what every calculation asks of a source, and
  CFX states a position in degrees, so reading a CFX file went straight through it.

  A source between -1 and 0 degrees now stays south, too: the sign lives in a negative zero,
  and `-0.0 >= 0` is True, so it is read with `copysign`.

- **Five more rules that guarded the constructor and nothing else** -- the shape that has now
  been found six times. Each is an `@invariant`, so it holds on build, on `set` and on a saved
  project coming back:

  | What | What `set` used to take |
  | --- | --- |
  | a source's flux | `-5.0` Jy, handed to a sensitivity by `get_flux` |
  | four telescope tables | negative SEFDs, temperatures and areas; an aperture efficiency of 1.4 |
  | `sidebands` | `["X"]`, after which `get_band()` returned a band of zero width, quietly |
  | `surface_accuracy` | `-0.5` m, which reaches Ruze's formula squared, so the result looks reasonable |
  | `orbit_file` | a blank string, failing later inside a calculation as an empty path |

### Changed

- **Reading a schedule is 17x faster.** The pointing rule asked every scan for `get_end()`,
  which builds a `TimeDelta` and adds it to a `Time` -- 2415 of them for a 69-scan file. It
  compares Julian days now: 1.62 s to 0.09 s. An invariant decides on every write, so it does no
  expensive work to decide, which is a convention test now.

- **One `ScheduleFormat`.** The two format `Super`s shared a 57-line `_read_one` byte for
  byte, plus `_observations`, `_put` and `_combined`: 209 and 197 lines became 91 and 90 over a
  shared 161. The two writers each had `channels_of`, `collect_modes`, `Channel`, `Mode`, the
  polarization letters, the name sanitiser and `Skeleton`; one copy each in `pastrocore/formats/`.
- Both formats declare one `OUTSTANDING` tuple that the file and the report are made from, where
  CFX's report had named its blocks in string literals a third time.

- 26 unused imports, among them `matplotlib.pyplot` in a visualization tab -- which pulled in
  pyplot's backend machinery for a module that has not used it since the tab began owning its
  figure.

## [1.6.1] - 2026-09-08

### Fixed

- **Recent Projects never appeared.** The submenu was declared in the form, the setting was
  written, the entries were built -- and one `<addaction>` line was missing, so File held no
  Recent Projects at all. The test drove `rebuild_recent_menu` directly and passed against a
  menu nobody could open.

  Two tests now: the G4 one asks the File menu for it, and a convention test fails on **any**
  `QMenu` a form declares and never adds to anything. Qt does not complain about one, which is
  why it went out in a release.

## [1.6.0] - 2026-09-08

Schedules come back in, and a rule that had been refusing real experiments is gone.

### Added

- **Reading VEX and CFX** (V5). `vex(method="import")`, `cfx(method="import")` and
  **File → Import Schedule**. All four example files load, and what comes back is an observation
  like any other: calculable, analysable, exportable. `re03fr.vex` returns six stations, two
  bands, one source and its eight scans.

- **V6, decided: what this model cannot hold is read past, and named.** Neither of the two
  options that item offered: keeping unrecognised blocks verbatim means carrying something
  nothing here can use or check, and refusing to export an imported file makes the round trip
  useless. An import reports `passed_over` by name, so it is not mistaken for a lossless one.

- **A most-recently-used list** (G4). File → Recent Projects, ten deep, kept in the settings so
  it survives a restart by being a setting rather than something the window remembers. An entry
  whose folder is no longer a project is removed when it is clicked.

### Fixed

- **A rule was refusing half of a real experiment.** "Active scans must not overlap in time"
  -- but `re03fr.vex` observes 2230+114 from 13:50 with Wb, Sv and Bd at 4828 MHz *and* with Ev,
  Nt and Zc at 22228 MHz. Two sub-arrays on one source at two frequencies is an ordinary way to
  run an array, and one antenna recording two bands at once is ordinary too.
- The rule is about **pointing** now -- one mount cannot be aimed at two sources at the same
  moment -- which is the only thing the model can honestly say. Importing that file went from
  four scans to eight.

- **Both catalogue browsers raised on every path.** The lookup had been moved onto the
  orchestrator and the dialog was never given one, so the Options menu, the sources tab, the
  telescopes tab and Generate Observations all failed with `AttributeError`. Nothing ever
  constructed these dialogs; a test builds both now, in both selection modes.

- **One font, everywhere.** The forms carried 60 `font` properties, and a widget font beats the
  stylesheet: family-only meant Arial at whatever size the platform defaults to, next to a
  widget the stylesheet had given Arial 9pt. The stylesheet states it once on `QWidget`; a test
  tells a font that says something new from one that repeats what is already said.

- `create_telescope` and `create_space_telescope` took a `name` and passed `name=code`,
  discarding it -- so a telescope called Svetloe came back as `Sv`, and both exporters wrote a
  name where the model had only ever kept a code.

### Changed

- **A visualization tab owns its figure again.** Swapping a `Figure` into a live canvas is
  not something matplotlib supports. It was reverted in 1.5.0 on a measurement taken while three
  copies of the suite were running. Measured alone, back to back in one process: 5.04 s against
  5.31 s. **A number taken on a busy machine is not a number.**

- V3 dropped. No VEX parser is installable here, and an item standing against a tool nobody has
  can only ever be open. The real check is a correlator accepting a real file. G5 dropped: a
  visualizer configured from a file serves whoever edits the file.

## [1.5.0] - 2026-09-08

A schedule leaves pAstroCORE. Two formats, written whole and claiming only what is known.

### Added

- **VEX and CFX exporters (V1--V4, X1, A2).** `vex(method="export")` and
  `cfx(method="export")` -- one operation per format, named after the format, because writing a
  file, reading one back and checking one are three things done to one contract. The writing
  lives in `pastrocore/formats/`, which knows a format and nothing about requests.

  Reached from `pastrocore-cli vex`, `pastrocore-cli cfx`, and **File -> Export Schedule**.

- **The decision both exporters turn on: absent is not the same as missing.** Every block
  the format calls for is written. What the model knows carries real values; what it cannot
  know -- which recorder is in the rack this week, the clock offsets measured during
  correlation -- is an empty field or a commented-out `def`, as `sched` writes them.

  The report names every outstanding block, from the same declaration the file is written
  from, so the two cannot drift apart.

- Three things are refused rather than guessed at, each a plausible wrong answer a correlator
  would have taken: a `site_velocity` of zero, which the model defaults to; a BBC link pointing
  at a `&BBC01` nothing defines; a polarization written as an empty field.

- **A space telescope is a station in CFX**, with an `ORB_FILE` and no fixed position -- the
  shape this model has always had, and the reason the format is worth having here. VEX 1.5 has
  nowhere to put an orbit, so it excludes one **by name in the report**.

- **`IF.sidebands`** -- a list, like `polarizations`, because one receiver setting records both
  sidebands in both polarizations and is still one setting. `get_band()` is the one place a
  sideband becomes numbers, and the overlap rule asks it: 4828 upper and 4844 lower are the
  same 16 MHz written two ways, and the second is refused with both spans named.

  The frequency editor says which sidebands a band records and **shows what it covers while it
  is being edited**; the frequencies tab gains Sidebands and Covers. Both lists in the editor
  are filled from the model, so the form cannot offer what the model would refuse.

- [`docs/formats.md`](docs/formats.md) -- the map from the model onto both formats, written
  before either exporter, and the reasoning the exporters follow.

### Changed

- Drawing a whole project draws the observations **one at a time**. They went through a
  `ThreadPoolExecutor`, and matplotlib is not thread-safe -- invisible, because the call passed
  three arguments to a two-argument method, so every observation raised `TypeError` and a whole
  project drew nothing at all.

### Fixed

- **The polarization group rule holds everywhere.** It lived in `_validate_polarizations`,
  which runs from `__init__` and nowhere else, so `set({"polarizations": ["RCP", "H"]})` was
  accepted and so was a saved project carrying one back. It is an `@invariant` now.

- The suite's intermittent `access violation` inside `processEvents`. Deletions happen
  between tests, where nothing is inside Qt's event loop, rather than in the middle of a later
  test's redraw: seven clean runs against one crash in three before, and the suite goes from
  85 s to about 190 s. Two cheaper versions both ended in heap corruption.

### Known

- **A visualization tab still swaps figures into its canvas.** Having the tab own one figure
  and asking the visualizer to draw into it removes the swap, which matplotlib does not
  support -- and it was written, measured and **reverted the same day**: 60 redraws went from
  6 s to over 280 s and left 50 MB behind. Why is not yet known. The swap is what ships.

## [1.4.0] - 2026-09-07

The numbers stopped being something you could only look at a plot of, and nine tabs became one.

### Added

- **`analyze`: asking something of results that already exist (N1--N4).** A calculation
  finished and that was the end of it. Visibility is a boolean per station per moment, and
  "when is it up, for how long, where are the gaps" could not be asked at all -- nor could
  "what does this baseline reach", which is a `max` over one column.

  A fifth operation, because it *reads* results rather than producing them. Not `calculate`: a
  `_calculate_windows` would appear in the catalogue as a calculation called "Windows", offered
  in the dialog beside UV Coverage.

  | Method | Answers |
  | --- | --- |
  | `describe` | what can be asked of each result, and what values its categories take |
  | `summary` | count, missing, min, max, mean, median, std and **range**, grouped and sliced |
  | `windows` | runs of a boolean as intervals -- or the gaps between them |
  | `coverage` | how many stations see it at the same moment; two is the least that makes a baseline |

  Any of them over a whole project, each row naming its observation. **Nothing here names a
  column or a calculation** -- all of it is read from the schemas the calculations already
  declare, so one added tomorrow is analysable without a line changing.

  A new page describes it: [asking something of the numbers](docs/analysis.md).

- **Tools → Analysis**, a tab rather than a dialog: analysis is a filter changed and the
  question asked again, which a modal turns into reassembling the choice each time. It holds no
  list of its own -- every choice on it is filled from `describe`.

- **Exporting an answer.** `export(method="analysis")`, tab-separated with a BOM exactly as a
  calculated result is written, so both open in the same spreadsheet. The command line passes
  the question and gets it asked and written in one request; the tab passes the rows it already
  has, so the file cannot disagree with the table it came from.

- **`pastrocore-cli analyze`**, with `--where`, `--group-by`, `--gaps`, `--at-least` and `--to`.

### Changed

- **The nine visualization tabs share a base (G6).** 2562 lines became 832. They had the
  same nine methods each and **no two were byte-identical** -- parallel variations, with the
  differences that mattered buried among the ones that did not. What varies is four
  declarations: which form, which result, which filters, which field counts what was drawn.

  Two tests came with it, because building a tab proved nothing: one draws every tab against a
  calculated project and fails on a blank canvas, one refuses a tab that reimplements the shared
  machinery instead of declaring.

- **The analysis tab, tidied** after being used: results are listed as *Telescope
  Visibility* rather than `telescope_visibility`, from the same catalogue the calculation
  dialog uses; a moment is a calendar reading `yyyy-MM-dd HH:mm:ss`; every numeric filter opens
  filled with the span that is there; and the button says **Show** rather than "Ask".

- **Package Project, Open Package and Analysis are in `main_window.ui`**, where Designer can see
  them. They had been `QAction`s built in code.

### Fixed

- **`describe` read the whole project into memory.** It called `collect()` on every result of
  every observation just to describe them -- the one thing the parquet store exists to avoid. A
  row count now comes from the file's own metadata, and the distinct values of a column read
  that column and nothing else.

- **A window was short by a few sampling steps.** The step was measured across a frame holding
  one row per station per moment -- the same instant repeated -- so it came out wrong. Windows
  and gaps now add up to the span exactly, which is the arithmetic that says both are right.

- **NaN was being averaged.** A calculation writes NaN for a moment it has no answer for, and
  360 of 576 elevations in the fixture project are exactly that; including them made the median
  come out NaN. They are excluded and reported as `missing`, since how many moments have no
  answer is itself worth knowing.

### Upgrading from 1.3.0

Nothing to do.

## [1.3.0] - 2026-09-03

Three roadmap items, and the last place the interface reached past the orchestrator.

### Added

- **A project as one file (R6).** A project is a directory, which is right for working in and
  wrong for sending: a colleague gets a folder tree and a bug report gets nothing at all.
  `export(method="package")` writes one file and `load(method="package")` reads it.

  Zip as an **exchange** format, not as storage. Packing the working project was measured and
  rejected -- parquet is already compressed so it saves 0.6%, and opening becomes 46x slower --
  and neither cost applies to a file written once and unpacked once.

  `results=False` writes the model alone: about a kilobyte that reproduces the configuration,
  against 150 KB with the frames. Unpacking refuses any entry that would land outside the
  directory it unpacks into, because a package is a file from somewhere else.

  `pastrocore-cli package`, and every other command takes a package anywhere it takes a
  project -- so `info` and `affected` work on what a colleague sent without unpacking it.
  **File → Package Project** and **Open Package** in the window.

- **Which results a change would spoil (T4).** `compute(method="affected")`, asked *before* the
  change. `stale` compares a stored fingerprint against the configuration in hand, so it can
  only speak about a change that already happened; a user about to move a telescope wants to
  know what it will cost first.

  Both halves are derived and neither is written down. MSB's model graph says what reaching a
  type reaches -- a `Telescope` is held by `Telescopes` and *named by* `Scan`, so editing one
  reaches scans too, which is the part nobody remembers. Each calculation's schema says which
  parts it reads. Which parts exist comes from `Observation`'s own annotations.

  `pastrocore-cli affected <project> Telescope`.

- **One stylesheet (G1).** 224 `styleSheet` properties across 24 forms and 131 lines written
  inline in `app.main` became `pastrocore/gui/pastrocore.qss` -- 700 lines, applied to the
  `QApplication` so a dialog built later sees it, and replaceable by a user file kept beside
  their settings.

  **Rules are written against types on purpose.** A sheet set on one widget applied to that
  widget; the same rule at application level applies to every widget of that type -- a `QLabel`
  rule that reached 3 labels out of 121 now reaches all of them. That is why some forms changed
  appearance, and why every button looks like every other button now.

- **A pixel harness for the forms.** G1 was attempted and reverted once, and the reason is that
  it is a cascade and nothing tells you it has moved except the pixels. This renders all 24
  forms offscreen and compares digests, per platform -- pixels are not portable, and the build
  runs on Ubuntu while this is authored on Windows, so a platform with no reference skips.

  It earned its keep immediately: a `QWidget` rule emitted after `QPushButton` won over it,
  because Qt takes the later of two rules of equal specificity and `QWidget` matches every
  widget there is. Every button in the application went flat and nothing else would have said
  so.

### Fixed

- **The window came out grey and every button's label black.** Both from rules that arrived
  with the window chrome and landed after the surface rules: `QMainWindow { background-color:
  #f5f5f5 }` beat the white it was supposed to have, and `QWidget { color: #333333 }` painted
  the labels of the blue buttons. Surface rules go first now.

### Changed

- **The catalogue layer reaches the model through the orchestrator**, which was the one place
  left that did not. `CatalogManager` is backend -- the parsing lives there, not in a dialog --
  so this was never logic in the interface; it was the interface holding a model object and
  calling it, which a command line and a server cannot do.

### Upgrading from 1.2.2

Nothing to do. **The application looks different**, deliberately: controls that were styled
inconsistently now share one appearance. To change it, edit `pastrocore/gui/pastrocore.qss`, or
keep your own `pastrocore.qss` beside your settings -- a user file replaces the shipped one
rather than adding to it.

## [1.2.2] - 2026-09-03

A pass over the whole project after the move to 2.0.1, and the orbit path turned out to be
where everything was hiding. The fixture project holds two ground telescopes, no spacecraft and
no orbit file, so none of it had coverage -- and a characterization suite could not have helped
anyway, since it compares against what the code used to produce.

### Fixed

- **Chebyshev interpolation put a space telescope kilometres from where it was.** One
  polynomial of degree 30 was fitted over everything the orbit file covered. A Molniya-type
  orbit is fast through perigee and slow at apogee, and no single polynomial describes both:
  the method offered as the accurate one was two orders worse than linear interpolation.

  Measured against a Kepler orbit of eccentricity 0.94 sampled every 600 s, at times deliberately
  off the sample grid:

  | method | worst | mean |
  | --- | --- | --- |
  | chebyshev, before | 846.5 km | 44.75 km |
  | linear | 171.0 km | 1.03 km |
  | cubic_spline | 14.9 km | 0.016 km |
  | **chebyshev, after** | **19.5 km** | **0.063 km** |

  A telescope 40 km from where it is said to be puts that error into every baseline, which is
  why `linear` agreed with an independent tool and this did not.

  It is fitted per arc now, degree 12, with arcs cut along the **samples** rather than along
  the requested span -- so an arc is a fixed number of samples wherever it sits, and short in
  time through perigee where the orbit turns fastest. Cutting the span into equal pieces of
  time instead still left 43 km there.

  Each arc is fitted on its own samples plus half a degree either side, so joins are informed
  from both directions rather than extrapolated to. What remains is at perigee and belongs to
  the sampling: no method recovers a turn the file did not record.

- **An orbit was cut to the scan exactly.** Every method here interpolates *between* samples, so
  the first and last moments of a scan had nothing beyond them to lean on and were extrapolated
  to -- the worst place for it, and the hardest to notice because the numbers still come out.
  Eight samples are kept either side.

- **The orbit cache did nothing and its lock did too much.** `_orbit_cache` was created in
  the constructor and never written to or read from, while the lock named after it was held
  across the whole interpolation loop, serialising exactly the work the pipeline runs in
  parallel. Ten scans against one spacecraft re-read the same file ten times.
- The parse is cached now, keyed by path, mtime and size so an orbit edited on disk is read
  again, and the lock guards the dictionary access alone. Measured 23x on the second read.

- **Three of the four length-mismatch guards were wrong**, in two ways. Two read
  `positions[:k] = positions[:k]` *after* rebinding `positions` to all-NaN, so they copied NaN
  onto NaN and discarded every position computed. The third assigned a full-length slice from
  however many rows there really were.

- **Importing a telescope could not add one that was already here.** A name and a code are
  each unique within an observation and a file written from one carries both, so Import New
  Telescope refused every file written from this observation. `Telescopes.add_as_new` gives it
  the first free name and code, `EHT_ALMA_2` rather than a UUID.

- **One observation that could not be drawn took the whole project with it.** `future.result()`
  was called twice per future and re-raised into the caller, so a project of twenty plots
  produced none, with a message naming what went wrong but never where.

- **`CatalogManager.clear()` did nothing.** It set `_sources` and `_telescopes`, while the
  catalogues are held in `source_catalog` and `telescope_catalog`. Nothing called it, and `clear`
  is the name msb_arch 2.0.0 removed, so it is gone.

- **`get_telescopes_by_type` could not return a space telescope.** It read `telescope_type ==
  "Telescope" and isinstance(t, Telescope)`; a `SpaceTelescope` is a `Telescope`, so that gave
  every telescope for one spelling and an empty list for every other.

### Changed

- A figure "cleanup" that could only have tidied someone else's desk: `_finalize_plot`
  counted `plt.get_fignums()` and called `plt.close('all')` above ten, while building its
  figures with `Figure(...)`, which pyplot never registers. The only figures it could have
  closed belong to whoever did use pyplot -- a visualization tab's, exactly.
- The count of active scans was written out identically in the metadata of eleven calculations,
  which is how the twelfth count in the same file came to be spelled differently from all of
  them. Both are methods now; every number is unchanged.
- The window emptied one catalogue at a time by reaching into `source_catalog` itself.
  `clear_source_catalog` and `clear_telescope_catalog` are what it asks for now.

### Added

- **Tests for the orbit path**, measured against a Kepler orbit solved to machine precision
  rather than against what the code used to produce -- which is the only kind of test that could
  have caught the defect above. Plus tests for reading an orbit file: the margin either side of a
  scan, the parse being kept, and a file edited on disk being read again.

### Upgrading from 1.2.1

Nothing to do. **Recalculate anything computed with `interpolation_method="chebyshev"`**: those
results were wrong by kilometres, and staleness cannot know it, because the inputs did not change
-- the code did.

## [1.2.1] - 2026-09-03

### Fixed

- **An export that had written every file reported that it had failed.**
  `raise_on_error=False` is what turns a request's answer into a `Response`; the export thread
  did not pass it, so `.value` raised `AttributeError: 'dict' object has no attribute 'value'`
  after every file was on disk. The thread caught it and emitted `error`:

  ```
  INFO  - Exported 16 file(s) to 'E:/temp'
  ERROR - Export error in thread: 'dict' object has no attribute 'value'
  ```

  Nothing caught it because the thread logs and emits rather than raising, so a suite watching
  for exceptions sees a clean run -- and there were no tests for `ExportThread` at all. There is
  one now, and it watches the signals.

### Added

- **A ratchet on reading a response.** `.value`, `.ok` and `.error` may only be read off a
  request that asked for a `Response`. Twenty-six calls of exactly this shape were fixed when
  msb_arch 1.8.0 was adopted; this was the twenty-seventh. Scoped per function over the AST, so
  the same variable name elsewhere is not a false match.

  It found one thing while parsing: a packaging test's docstring held `catalogs\sources.dat` in
  a non-raw string, which Python warns about.

## [1.2.0] - 2026-09-03

The move to `msb_arch` 2.0.1. Three of its changes were breaking, and each broke something here
that had been wrong for longer than the framework had -- which is the usual way a breaking change
earns its keep.

### Fixed

- **The interface stopped guessing what shape a project answers with.** 2.0.0 made
  `Project.get_items()` return a list, exactly as a container does, with `get_all()` for the
  mapping. Six places called `.items()` on the answer:

  - The calculation dialog, the export dialog and the visualize dialog each raised, caught it,
    and opened a modal error. In the suite nothing mocked `QMessageBox.critical`, so the tests
    **stopped** instead of failing -- a hang is what a missing mock looks like.
  - The project table and its context menu asked `isinstance(observations, dict)` and quietly
    returned. A project full of observations looked empty, and said nothing about it.

  Each asks for `observations` now -- the method that exists precisely so no caller has to know
  which shape the framework returns.

- **Plotting a whole project raised on its first line.** It called `get_observations()`, which
  has never existed on a project.

- **The window released its observations after emptying the project**, so the loop that was
  meant to release them walked an empty list. It had never once had a body to run. Releasing a
  project is a request now -- `compute(method="release")` -- which is model work leaving the
  interface, and it is what a command line opening one project after another needs anyway.

- **A restored project never equalled the one it was written from.** 2.0.0 gave `Project` an
  `__eq__` so that `load(...) == project` holds; here it still did not, because
  `CalculatedData` had none and every observation compared by identity. It compares on the keys
  a result set answers to, since comparing frames would mean loading both projects.

- **`_compute_replay` overwrote its own `attributes` parameter inside its loop**, so from the
  second step onwards `skip_failures` was read out of that step's attributes rather than out of
  the request.

### Changed

- **Three rules moved from helpers called by hand to `@invariant`**, which 1.10.0 added: a rule
  about a whole object, checked when it is built, when it is restored, and after anything that
  changes what it holds, with the change undone when it refuses.

  | Rule | Was called from | Was not checked when |
  | --- | --- | --- |
  | Frequency bands must not overlap | six places | `set_item` wrote into `_items` directly |
  | Active scans must not overlap | `add`, `set_scan` | `set_item`, `set_items`, or the object was built from a file -- which is where a conflicting pair comes from |
  | Observation codes must be unique | four places | `remove_item` and `set_project` |

  Each rule names both offenders rather than stating the rule, which a method that only
  answers False cannot do. Both containers sort by start rather than comparing pairwise, so
  checking the whole costs one sort instead of a square. `set_if` and `set_scan` write, check,
  and put the old values back on a refusal, as msb_arch does for a field.

  A refusal is now an `InvariantError`. It is a `ValueError`, so anything catching that still
  catches this.

- `SCHEMA_VERSION`, `migrate`, `to_dict` and `clear` came off `ScheduleProject`. The first three
  were reimplementations of what `Project` provides once it is a `Serializable`; `clear` was the
  name 2.0.0 removed, and its work is in `remove_all`.

### Upgrading from 1.1.0

Install `msb_arch` 2.0.1. A project written by 1.1.0 opens unchanged.

Two things are refused that were previously accepted only because nothing checked: a saved
project whose active scans overlap, and one holding two observations with the same code. Both
are schedules that could not be run; if a file of yours does not open, that is what it is saying.

## [1.1.0] - 2026-08-18

The release where the backend gets a second caller, which is the claim 1.0 was built on and
could not yet prove.

### Added

- **`pastrocore-cli`** -- the same work without a window: `info`, `calculations`, `run`,
  `export`, `check` and `replay`. About two hundred lines, every command one request, and no
  knowledge about calculations at all: what can be run, what each needs, what order they go in
  and what a run did are all asked of the orchestrator.

  Two tests are the point rather than the commands. One refuses any mention of `pastrocore.gui`
  or Qt in its source; the other runs a command in a fresh process and looks at `sys.modules`
  afterwards, because an import that sneaks in through a chain would pass the first and fail the
  second. `pastrocore` still opens the window.

- **A session is checked before it is replayed.** The command line turned a session into a file,
  and a file gets edited. `compute(method="check")` reports every problem without running a
  step -- an operation nobody has, a method that operation lacks, an object this project does not
  hold and where it was looked for, an attribute the handler never reads.

  A **problem** stops the replay: one bad step among good ones runs none of them. An unread
  attribute is a **warning**, because `accepts` is a lower bound by construction and refusing on
  it would refuse valid sessions. `replay` checks first, the command line has `check`, and
  **Tools → Session** says the same, since all three ask the same operation.

- **A session row says which object, not just its name.** Two observations may hold a source
  called `1228+126`; the panel showed the bare name and the two rows were indistinguishable.
  `where` is the recorded path made readable, and it is a column now.

### Fixed

- **A replayed step reaches the object it ran on.** Replay resolved by name, and `find` does
  not descend into an observation at all, so a step that edited a source, a telescope or a scan
  came back unresolved and only calculations could be replayed. It resolves by **path** now,
  which works against the same project reopened and not against one built separately.

- **Replaying a session that contained a run called a string.** A run carries two callables --
  one to report progress, one to ask whether to stop -- a journal cannot record a callable so it
  records `<function>`, and replay handed that back for the handler to call. Only a command line
  writes a session containing its own run, so nothing had met it.

- **Importing a frequency from a file raised** `NotFoundError: Attribute 'object' not found in
  IF`. It asked `load` for a shape that stopped existing when that contract became MSB's own,
  and no test covered the path.

- **Three `to_dict` overrides wrote into the mapping they were handed.** On an object that
  caches, that mapping *is* the cache, and MSB 1.9.0 turned writing to it into a refusal.
  Nothing constructs with caching on today, so this was a rake with a label on it.

### Changed

- **Nothing unwraps a response by hand.** MSB 1.8.0 gave a request's answer one type, and 53
  places here carried the line it replaces. That line is *wrong* for a request naming one
  method, and 26 of the 53 were dead as well -- the call never asked for the whole response. A
  ratchet forbids its return, in the source, the tests and the documentation.

- Requires `msb_arch` 1.9.2, which came out of this: `address` and `locate` were documented as
  inverses and were not, for two independent reasons, both found by trying to use them here.

### Upgrading from 1.0.0

Nothing to do. `pastrocore` opens the window as before; `pastrocore-cli` is new. A session
recorded by 1.0.0 still replays -- it has no paths, so it falls back to names, which is what it
did before.

## [1.0.0] - 2026-08-13

The release that says the shape is settled: **a project saved by 1.0 opens in 1.0**, the
interface is one caller of a backend rather than the place the work happens, and every claim on
this page was measured or tested rather than felt.

### Added

- **Tools → Session.** What has been asked of this project -- operation, object, method, how
  long, whether it worked -- written to a file, and a saved session replayed against whatever
  project is open. Each step names its object and is resolved on replay, and a step naming
  something this project lacks is reported rather than skipped.
- **Tools → Last Run Report.** What a run did, a row per step with its own time and its
  outcome, kept after the dialog closes and copyable as text for a bug report.
- **Independent calculations run at once.** Measured 1.30x on a thirteen-step plan (1.885 s
  against 1.453 s, median of five alternating rounds). Cancellation and the skipping of a
  failed branch behave as they do in sequence.
- **Documentation** for somebody who has never seen the project: [a first
  project](docs/guide.md), [the calculations](docs/calculations.md), [installing and
  running](docs/installing.md). **Every Python block on those pages is executed by the test
  suite**, in order, in one namespace, so an example that has drifted fails the build.

### Changed

- **A run recomputes what has gone stale**, which freshness already knew and the run ignored
  -- and then re-stamped the reused result as current, so freshness stopped saying so. Forcing
  a recomputation of what is current is a separate thing to ask for: the box says "Recompute
  everything" now, off by default, and no longer clears every result the observation holds.
- **The interface reaches the model only through the orchestrator**, checked by a test rather
  than believed. Six places did not: the calculation dialog walked the telescopes and cleared
  results itself, two tabs read the frequencies, and the window asked an observation what was
  stale, saved the project by calling it, and wrote an observation to a file with `json.dump`.
- **`save` and `load` are MSB's**, inherited rather than written again: atomic writes, an
  overwrite guard, and the framework's own error types. 59 lines removed.
- **Every result is calculated and written once.** Measured on one `source_visibility` request:
  `times` 10 stores → 1, `telescope_positions` 4 → 1, `source_visibility` 2 → 1.
- Four rules moved from `__init__` onto the annotation, where they hold at every way in: the
  source coordinates, the observation type, a scan's duration, and a telescope's pointing
  ranges. Each of them accepted anything through `set` and through `from_dict`.
- Requires `msb_arch` 1.7.0.

### Fixed

- **Closing the window destroyed the day's calculations.** Results live in a scratch directory
  until the project is saved, and `closeEvent` discarded it on every clean close. It asks now.
- **Every File → New Project and Open orphaned a scratch**, which the next start offered to
  recover from a session that had ended normally with nothing in it.
- **Calculating for a whole project produced an empty frame and said nothing.** Iterating a
  project yields its *names*, so thirteen calculations called `get_scans()` on a string.
- **A source going inactive left the time arrays looking current.** Found by checking each
  result's declared `depends_on` against what MSB derives the handler to touch.
- **A run with a failed step reported complete success.** A slot defined twice, and the winner
  took one argument where the signal carries two; PySide drops what a slot does not accept.
- **An observation labelled "12 stale" could not be opened** -- the explorer looked it up by
  its label -- **and the label survived the recomputation that fixed it.**
- **A step stored its result under the handler's name** rather than the schema's store key, so
  `time_arrays` landed where nothing reads it.
- **Comparing two metadata mappings raised instead of answering** when one held numpy arrays,
  which turned a Mollweide recomputation into a failed calculation.
- **An installed application found no catalogues and lost its settings**: every path was
  relative to the directory it was started from.

### Upgrading from 0.9.0

| Symptom | Why | What to do |
| --- | --- | --- |
| Closing the window asks about saving | It always should have: those results were being discarded | Save, or discard deliberately |
| "Recompute everything" is off and no longer clears results | A run recomputes what is stale by itself | Nothing. Tick it after changing a calculation's own code |
| `manipulator.export(method="catalogue")` raises | Planning and running calculations moved to their own operation | `manipulator.compute(...)`. `plan`, `run`, `catalogue` and `order` moved together |
| `load` returns the object rather than `{"object": ...}` | MSB's own contract | Read the result directly |

## [0.9.0] - 2026-08-13

The release that makes pAstroCORE installable, and that moves the last of the running of
calculations out of the dialog that used to do it. Three of the four fixes below are the same
fault wearing different clothes: **the interface reported success because nothing carried the
failure to it.**

### Added

- **`pip install .` gives a `pastrocore` command.** `pyproject.toml` declares the build, the
  dependencies and the entry point, and the version is stated once -- in
  `pastrocore/__init__.py`. `requirements.txt` installs the project rather than listing what it
  needs a second time.
- **Space telescope results can be drawn.** Pointing draws azimuth and elevation per station
  with range on a right-hand axis, since a range moves over four orders of magnitude more than
  the angles do. Visibility draws filled bands per station, because the value is a boolean and
  what a reader wants is when it is true and for how long.
- **The calculation dialog asks what to point at**, once per run, before starting. One
  spacecraft in the selection is used without asking; several are offered; none is said so, and
  the calculation that could not produce anything is not run.

### Changed

- **Running several calculations is a plan the backend builds.** The dialog used to loop
  over what was ticked, in whatever order the list happened to be in, with prerequisites left
  to whoever remembered them. `export(method="plan")` returns a pipeline now -- everything
  asked for plus everything those need -- and `run` executes it.
- Asking for `telescope_visibility` alone plans five steps in the order that satisfies them.
  Progress and cancellation ride on an interceptor, so nothing is counted twice and a cancelled
  step skips the branch below it as a failed one does. **A command line or a server sending the
  same request gets the same behaviour**, which is the point of putting it there.
- **Start-up: 4.0 s to 1.4 s.** The calculator and the visualizer, which between them import
  matplotlib, `astropy.coordinates` and scipy, are registered deferred (`msb_arch` 1.4.0) and
  built when first needed, warmed on a background thread once the window is up. Nine dialogs
  imported at module level are imported where they are opened.
- **The exporter asks each plot what it takes.** Five lists decided which arguments each picture
  was given, and each was a copy of what the plot states by reading it. `accepts` on a catalogue
  entry (`msb_arch` 1.5.0) derives that. One plot was missing from two of the lists.
- **The catalogues ship inside the package** and the settings live in one per-user file. See
  Fixed: the paths were relative to wherever the application was started.
- Requires `msb_arch` 1.5.0 or later.

### Fixed

- **Exporting pictures failed for every calculation.** The exporter called `self.manipulator` on
  a `Super` whose attribute is `_manipulator`, so every export with pictures raised
  `AttributeError` -- which the dialog reported as "0 files written". Text export worked
  throughout, which is why it read as "pictures are not implemented for this".
- **A run with a failed step reported complete success.** `CalculationDialog` defined
  `calculation_finished` twice; the later definition won and took one argument where the signal
  carries `(results, errors)`. PySide drops arguments a slot does not accept rather than
  complaining, so the failures fell into the gap between the two definitions.
- **The space telescope calculations ran with nothing to point at**, finishing in a
  millisecond having computed nothing, so there was afterwards nothing to export or draw. Which
  calculations need a target is read from the result's columns; the first fix compared labels
  against keys and matched nothing, the tests never going through the dialog's run.
- **Ticking a calculation did not tick what it needs**, the same label-against-key comparison, so
  `telescope_visibility` could run before `telescope_az_el`.
- **An installed application found no catalogues and lost its settings.** Every path was
  relative to the directory it was started from. The catalogues are inside the package now; the
  settings are one per-user file, adopting a `settings.pastro` left in a working directory once.
  A catalogue that has been deleted falls back to the shipped one and says so.
- **`scan_times` narrowed only by `source_name`**, so a result about a tracked spacecraft needed
  a case of its own. It narrows by whatever column the caller named that the result has.

### Upgrading from 0.8.0

| Symptom | Why | What to do |
| --- | --- | --- |
| The application starts with empty catalogues after this upgrade | Your `settings.pastro` records `catalogs/sources.dat`, relative to the old layout | Nothing. The relative path no longer resolves, so the catalogue that ships with the install is used and a line in the log says so. Point Preferences at your own catalogue if you had one |
| Settings appear to have been forgotten | They moved to a per-user directory | Nothing, once. A `settings.pastro` in the directory you start from is read and kept in the new place |
| `pip install -r requirements.txt` now installs pAstroCORE itself | It is `-e .`, so the dependencies come from `pyproject.toml` | Nothing. This is what makes one list rather than two |

## [0.8.0] - 2026-08-11

Adding a calculation now touches the calculator and its schema, and nothing in the interface.
A space telescope can be pointed at. A result says when the configuration moved underneath it.

### Added

- **Pointing a ground station at a space telescope.** `telescope_az_el` and
  `telescope_visibility`, chosen by name and never run as part of an ordinary observation. The
  direction is the **vector from station to spacecraft**: a source is far enough away that every
  station sees it alike, and a spacecraft at twenty thousand kilometres is not.
- The scans supply the time window, the stations supply the vantage point, and the spacecraft
  need not take part in the observation it is tracked during. Checked against the law of
  cosines rather than against a stored number.
- **A result knows when its inputs changed.** Moving a telescope 1 000 km and recalculating
  used to return the previous numbers in silence. Three answers now -- stale, current, or
  *unknown*, a result computed before this existing being neither -- shown as a label in the
  project explorer. Granular: editing a scan stales `uv_coverage` and leaves `beam_pattern`.
- **`ScheduleData`.** Export, save and load are operations reached through the manipulator, so
  a script or a server can do what the interface does. The export dialog went from 312 lines to
  210, its non-Qt logic from 252 to 130. Proved by bytes: four exported files hashed before a
  line moved and identical after.
- **One catalogue.** The same knowledge was written down nine times across three dialogs,
  including a table of which calculation needs which. It is one request now, answered by the
  manipulator from its own handlers (`msb_arch` 1.2.0). Adding a calculation makes it appear
  with its label, its prerequisites and its place in the order, which a test asserts.

### Fixed

- **Time on source lost its whole plot** with `KeyError` when a source was visible for less
  than one time step: a zero-length block, whose end sorted before its start.
- **Mollweide lost the source coordinates it draws against.** They are numpy arrays and
  `json.dumps` refuses them, so the metadata write dropped the key behind a warning nobody
  reads. Broke in 0.5.0 and broke silently. A project written before this needs
  `mollweide_tracks` recalculated once.
- **Metadata could disagree with the data beside it** -- 288 rows over one scan, described as
  covering nothing. Three fields restated what the frame already said, so one fact had two
  sources. The frame is the authority now.
- **Startup scanned 199 scratch directories** and asked the operating system about each,
  1 246 ms of it, for an answer it then threw away. 31 ms.
- **Every visualization tab failed to open** after the catalogue landed, and no test could see
  it: the tests build tabs directly, and none opened one through the dialog.

### Changed

- The visualizer's handlers follow MSB's naming, so the catalogue can see what it draws.
- Requires `msb_arch` 1.2.0 or later.

351 tests.

## [0.7.0] - 2026-08-11

A day of calculation is no longer lost to a crash.

### Added

- **Results are written to disk the moment they are calculated**, rather than waiting for a
  save. They used to be held in memory and marked unwritten, so they were lost to a crash, a
  power cut or the memory running out. They also counted **zero bytes** against the residency
  ceiling, so an unsaved session was ungoverned as well as unprotected.
- **A scratch directory per running session.** Before a project has a directory of its own its
  results live there; saving migrates them across rather than recalculating. One per session,
  named for the process, so two open windows never adopt or evict each other's results -- the
  same rule a server needs to run sessions for several people.
- **Recovery.** A session that did not close normally leaves its scratch directory behind on
  purpose, and the next start offers it back, naming the project and how much it holds. Closing
  normally removes its own and only its own. Nothing is ever swept at startup: a directory left
  by a previous run is the day of calculation this exists to protect.
- **Interface changes are made in the `.ui` files and regenerated**, with
  `tools/regenerate_ui.py` and a test that fails if a generated module and its form have
  drifted. It found one that had. The memory-share control added in 0.5.0 now lives in the
  form.

### Fixed

- `ui_dialog_edit_if.py` and its form had each been edited without the other, both only in
  styling. The form was the newer, so regenerating restored the dialog's own styling.

### Notes

- Writing through is best effort. A store that fails leaves the result held and unwritten, so a
  full disk costs the protection rather than the calculation.
- The scratch lives in the per-user data directory, deliberately not the system temporary
  directory: results have to survive a crash and be findable afterwards, and temporary
  directories are exactly what gets swept.

## [0.6.0] - 2026-08-11

### Removed

- **The single-file project format.** It was tolerated for one release and is now gone:
  nobody outside this repository had saved a project in it, so it was not worth a branch in
  every load path. `ScheduleProject.to_file` and `from_file` went with it -- 147 lines of
  two-format handling. The test fixture is a JSON file read through `from_dict`.

### Changed

- **Open and Save ask for a folder.** Both dialogs used to ask for a file: Save warned about
  overwriting one, and Open could not select a directory at all, so a user had to navigate
  inside the project and pick `project.json`. Opening now checks that the chosen directory
  really is a project, because a directory chooser will return any directory.
- **Saving into a folder that already holds something else asks first.** An empty folder --
  what the dialog's New Folder button produces -- and an existing project both go ahead without
  a question. Anything else would have dropped `project.json` and a `results/` directory among
  a user's files with nothing said.

## [0.5.1] - 2026-08-10

A bug-fix release. A space telescope could be built but not read back, so any
project containing one failed to open.

### Fixed

- **A project holding a space telescope could not be opened.** A space telescope has no
  station geometry, no mount and no elevation limits -- the constructor fixes them rather than
  accepting them -- and they are inherited fields all the same, so `to_dict` wrote them out and
  deserialization handed them back to a constructor that rejects them.
- `to_dict` omits them now, as it already omitted the position and velocity for the same
  reason, and `from_dict` drops them if a file written earlier still carries them.
- Space telescope ranges may be written as whole numbers -- `pitch_range=(0, 90)` -- which
  needed `msb_arch` 1.1.2.

### Changed

- Requires `msb_arch` 1.1.2 or later.

## [0.5.0] - 2026-08-10

Results moved out of memory. A project saves as a directory whose model is 5 KB, each result
is a parquet file beside it, and nothing is read until something asks for it. What is read is
subject to a ceiling.

Two calculation defects were found on the way, both of which had been producing wrong output
in silence.

### Added

- **The directory format, wired into the application.** `ScheduleProject.open` takes a
  project directory, the `project.json` inside one, or a single file written by an earlier
  version, and works out which. `save` writes a directory, converting a single file at the same
  path and removing the old file only once the new directory is complete.
- **A residency budget.** One per project, defaulting to half of available memory and
  settable in Preferences as a percentage. When the ceiling is passed the least recently used
  results are dropped and read back from disk when next needed. An unwritten result is never
  dropped, and the budget governs what may be kept, never what may be read.
- **Lazy, filtered reads.** All eight plots read through `scan_calculated_data` and collect
  once their filter chain is complete, so polars pushes the filter into the parquet read.
- **Characterization tests for the plots**, which had none. They read the drawn artists back
  out of the figure and compare coordinates, because every plot method swallows exceptions and
  returns a blank figure -- a test that only checked for a crash would pass through exactly the
  failure worth catching.

### Fixed

- **Baseline projections were NaN in every row, always.** UV coverage covers only the times the
  source is up; the code copied those rows into the first N positions of the time grid and then
  masked by visibility, which is true somewhere in the middle. The two never overlapped, so
  every value was discarded. They are matched on time now.
- **The characterization suite could not see a NaN appear or disappear.** The comparison
  computed `abs(a - b) / scale`, which is NaN when one side is NaN, and `NaN > worst` is false.
  That is why the defect above went unreported.
- **Plots drew telescopes and baselines in an unpredictable order**, so colours and legend
  order changed between runs on identical data. Eight loops iterated `unique()`, which polars
  does not order.
- **Renaming an observation lost its results**, which are filed under the owner's name.
- **Results of observations no longer in a project were left on disk**, where renaming an
  observation away and back would pick them up as current.
- **Saving could write a directory over the model file** when a project was opened by picking
  its `project.json`.

### Changed

- Metadata is read from its own file rather than through the result: 0.33 ms against 2.20 ms,
  because the old path pulled every row off disk to reach four entries.
- The exporter releases each observation's results before moving to the next.

### Measured

| | Before | After |
|---|---|---|
| Draw one source of 300, 1.3M rows | 55.2 ms | **6.0 ms** |
| Memory over 60 observations, 200k rows each | 407 MB, all 60 held | **71 MB, 32 held** |
| Loading a project | every result read | **none read** |
| Model file | 230.5 KB | **5.1 KB** |

213 tests.

## [0.4.0] - 2026-08-10

Four stages of the road out of the MVP: a safety net, hygiene, the calculations, and adopting
what MSB 1.1.1 now does for us. **Over 500 lines removed**, almost all of it code that
duplicated the framework.

The calculations are unchanged, and that is the point of the first stage rather than a
coincidence.

### Added

- **A test suite, where there was none.** 161 tests. The characterization suite clears the
  eleven results a saved project holds, recomputes them, and compares the numbers -- so a
  change to any formula fails the build. The reference needed no separate file: the saved
  project *is* the reference.
- **CI**, running on push and on every pull request, with Qt offscreen so the GUI smoke tests
  need no display.
- **A request journal.** Every request the orchestrator processes is recorded, bounded to the
  most recent 500. Read backwards it answers what produced a result; read forwards it replays
  the session, which is how a reported problem becomes a reproduction. `journal_limit=None`
  declines it.
- **A schema version on the project**, with a `migrate` hook, ahead of the storage change that
  needs it.
- **`ResultStore` and `CalculatedData`**: calculated results can live on disk as parquet and
  be read only when asked for. Not yet wired into the application -- the format change is the
  next stage -- but the machinery and its tests are in.
- **A startup warm-up**: one throwaway coordinate transform on a background thread while the
  window is appearing.

### Changed

- **Constraints live on annotations.** `IF.frequency`, `IF.bandwidth` and `Telescope.diameter`
  are `Annotated[float, Positive()]`. The hand-written checks they replace ran *after*
  `super().__init__()`, so the object was already built with the bad value, and none of them
  ran on assignment at all.
- **The entry point moved.** `pastrocore.py` shadowed the `pastrocore` package, so the main
  window could not be imported and could not be tested. It is now `pastrocore/app.py`, and the
  launcher is `run.py`.
- **Logging is lazy** throughout: 1 169 calls rewritten, every one of 682 rendered messages
  verified identical.
- Six handlers in the interface that call themselves "Validation error" now catch
  `(ValidationError, ValueError)`, so a wrong *type* reaches the branch written for it instead
  of the catch-all.

### Removed

- **`BaseEntityN`**, 98 lines overriding validation "for numpy arrays". Not one of the five
  classes using it declares a numpy annotation, MSB accepts them natively anyway, and the
  override was *weaker* than what it replaced -- its list branch could never match, so list
  elements went unchecked.
- **Six of nine `from_dict` overrides**, which reimplemented what MSB already does. The three
  that remain each earn it.
- **Twenty of twenty-one `Inspector` and `Configurator` handlers.** They are the built-ins now.
  `_configure_scheduleproject` stays, because generating observations is real domain logic.
- **21 918 lines**: `rc_icons.py` existed twice, byte for byte.

### Fixed

- **A calculation that fails now says why.** Seventeen handlers wrapped a whole calculation,
  logged one line and returned an empty frame, so a failure was indistinguishable from a source
  that was simply never above the horizon. They now log with the traceback.
- **The first calculation in a process took 1 077 ms against 290 for every one after it.** The
  difference was astropy loading its reference tables, once. Warming them at startup makes the
  first calculation 307 ms.
- **`polars`, `pyerfa` and `pyarrow` are declared.** They were imported and missing from
  `requirements.txt`, so a clean environment installed and then failed to start.
- A cache miss caused by a differing `time_step` is now logged with both steps. It was correct
  and silent, which left no way to learn why a call took 300 ms instead of one.

### Notes

Three releases of `msb_arch` came out of this work, each from a real need here:

| | |
| --- | --- |
| **1.0.1** | A `Dict[float, float]` -- an instrument table -- could not round-trip through JSON, because mapping keys were not restored from the annotation |
| **1.1.0** | The built-in operations could not reach one named member of a collection, which is what ten handlers here existed to do |
| **1.1.1** | `SCHEMA_VERSION` worked on entities and nowhere else, so the class an application actually saves to a file was the one that could not be versioned |

### Upgrading from 0.3.0

| Symptom | Cause | What to do |
| --- | --- | --- |
| `python pastrocore.py` no longer works | The entry point moved out of the package's way. | `python run.py` |
| A negative frequency, bandwidth or diameter is now refused | It always should have been; the check now runs before the value is stored, and on assignment too. | Nothing, unless the value was wrong. |
| Nothing else. | The saved project format has not changed yet. | Nothing. |
