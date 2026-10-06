# When something goes wrong

What a message means and what to do about it. Most of these are the application refusing
something on purpose, and the refusal says which rule it was.

**Where to look first.** The status bar carries the last line the log wrote, coloured by level.
**Tools → Calculations Report** keeps the last run's outcome per step, with a **Why** beside
anything that did not work. Everything also reaches `output.log`, beside where the application
was started; **Preferences → Common** sets how much.

## A calculation

### It refused, and the report says why

A step that cannot run says so in the report rather than only in the log. The common ones:

| What it says | What it means |
| --- | --- |
| `No 'target_telescope' given; there is nothing to point at` | The two spacecraft calculations have to be told what to aim at |
| `an opacity needs t_atm` | Half a correction is refused rather than half applied: the air's temperature goes with its opacity |
| `t_atm ... is not a temperature` | It is in kelvin, above zero |

### Nothing happens when I tick one calculation

Ticking one runs everything underneath it. **Telescope Positions**, **Source Visibility**,
**Time Arrays** and **Interpolated Orbits** are steps rather than answers, which is why they are
not on the list — asking for a uv plot asks for all four.

The report names every step that ran, so a run of four rows for one tick is the plan, not a bug.

### Results go stale

The explorer says how many beside an observation. A result records which parts of the model it
read, so editing a scan makes uv coverage stale and leaves a beam pattern alone.

A run recomputes what is stale on its own. **Recompute everything** in the Calculate dialog
forces what is still current as well, which is for a change in a calculation rather than in the
schedule.

## A plot

### The panel is blank

Either a filter has nothing ticked, or the result is empty. Tick a scan and a station — a plot
refuses to draw every source over every baseline, and an empty selection is drawn as nothing.

A blank panel is the current answer to both, and giving it labelled empty axes instead is open
on the roadmap as G14.

### The plot I want is not offered

Only a plot the observation has results for appears in the chooser. Calculate it first; the
chooser is filled from what is on disk rather than from what exists.

### The SEFD plot says "no SEFD"

**The shipped catalogues carry geometry and positions, not measurements.** A station from the
catalogue has a dish, a mount and a place to stand, and no system temperature.

Give it one in the telescope editor's **Sensitivity** tab — SEFD directly, or system temperature
and aperture efficiency, from which it is computed. A row covers a range of frequencies, so a
measurement at C band is never read as the one at 22 GHz.

### Sensitivity is empty for a source

A source needs a flux at the band being observed. The shipped source catalogue carries positions
and no fluxes, so a source taken from it has none until one is entered.

Between two measured frequencies the flux is interpolated as a power law. Beyond them it needs a
spectral index, and without one the answer is left empty with the reason beside it.

### The SEFD track is flat

No atmosphere was given. Opacity, air temperature and a gain curve are properties of the day and
of the dish rather than of the station, so they go with the calculation and the result records
which it used.

Without them the track is the zenith SEFD held level, which is correct rather than broken.

### Both spacecraft plots are empty

They need a space telescope in the observation, and a target chosen when the calculation runs.
A ground array alone produces no rows for either.

## The model refuses an edit

### A scan cannot be ticked active

Three things have to hold: enough active stations for the kind of observation — two for VLBI,
one for SINGLE_DISH — at least one active band, and an active source the observation holds. An
off-source scan is excused the last of those.

### A band will not go in twice

A frequency is an *edge* rather than a middle, and **Covers** shows the span while it is typed.
4828 upper and 4844 lower are the same 16 MHz written two ways, and the model holds one of them.

### A name cannot be changed

**A name is given at creation and is an identity.** An observation's code can be changed and is
checked against the others; the internal name cannot, and a copy is given a fresh one.

### An observation code is already taken

Codes are unique in a project, because the code is what a correlator reads. Renaming one onto
another's is refused on the way in rather than on the way out of a saved file.

## Files

### Results are missing from a project directory

A save writes the schedule and every result beside it. Results calculated before a save live in
a per-session scratch directory, and the next start offers them back after a crash.

Removing an observation leaves its results on disk until the next save, which is the only other
thing that drops them.

### An exported VEX file has empty blocks

That is deliberate. The file is complete in shape and partial in content: what the model cannot
know — which recorder is in the rack, which converter a channel goes through — is written empty
and annotated with what belongs there.

The report shown after writing lists those blocks by name, and
[getting a schedule to a correlator](formats.md) says whose they are.

### An edited catalogue did not stick

The shipped catalogues are never written to. Saving one asks for a name in your own catalogue
folder, and the setting then follows your file, so an upgrade does not take the edit back.

### Memory grows through a session

Up to a point, and then it stops. What grows is caches: matplotlib's text metrics, the request
journal up to `session_limit`, and the results in hand up to `results_memory_share`.

A dropped result is read back from the project when it is next wanted, so the ceiling costs a
read rather than a run. [Installing and running](installing.md) has both settings.

## Still stuck

[The roadmap](ROADMAP.md) records what is known and not yet answered, including the four
parked items that read as oddities in use: an empty plot's axes (G14), what an equatorial mount
limits (E2), a multi-field write that one field refuses (G16), and a rule about a container when
a held item changes (G15).
