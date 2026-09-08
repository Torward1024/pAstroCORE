# pAstroCORE roadmap

**1.7 shipped.** What is left, what was decided against, and why.

Every item has an **exit criterion**: a sentence that is true or false. An item is finished when
its criterion holds, not when it feels tidy.

## Next

Nothing is scheduled, and nothing is blocking anyone.

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
