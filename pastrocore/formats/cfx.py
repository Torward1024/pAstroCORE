# formats/cfx.py
"""Writing a schedule as CFX, which is what the ASC correlator reads.

CFX carries a subset of what VEX carries, in a syntax of its own: flat `[$SECTION]` blocks of
`key = value` lines rather than nested definitions. It is smaller, and it has one thing VEX
has not -- **a space telescope is an ordinary station with an orbit file**, which is the shape
this model already has and `sched` does not.

The same rule as the VEX writer, for the same reason: every section the format calls for is
written, what the model knows carries real values, and what it cannot know is a blank field or
a commented-out line annotated with what belongs there. A CFX file is finished during
correlation, and rather more of it than a VEX file is -- the recorded data, the clock offsets
measured after the fact, the `TIMEOFS` figures that come out of the delay model, the correlator
output settings. None of that is a scheduler's to write and all of it is named.

**One file per frequency setup.** The two examples this was written against are one experiment
in C band and in K band, as two files, with `[$OUTPAR]` naming the sub-bands of that file's
setup. A CFX file is a band, so an observation using two writes two.
"""
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple

from astropy.time import Time
from msb_arch.utils.logging_setup import logger

from pastrocore.base.frequencies import IF
from pastrocore.base.observation import Observation
from pastrocore.base.sources import Source
from pastrocore.base.spacetelescope import SpaceTelescope
from pastrocore.base.telescope import MountType, Telescope

#: CFX's comment character, and how a line says "not stated". `#` at the start of a line, as
#: the examples use it for the commented-out `IF` lines of a swapped-polarization receiver.
HASH = "#"

#: What the examples indent a key by: one tab.
INDENT = "\t"

#: Our polarizations in CFX's letters, which are VEX's.
POLARIZATION_LETTERS = {"RCP": "R", "LCP": "L", "H": "H", "V": "V"}

#: Sideband order within a band. Matching the VEX writer, so the two files of one experiment
#: list their channels the same way round.
SIDEBAND_ORDER = ("L", "U")

#: Our mounts in CFX's words, read off `TLSC_PAR`'s last field in the examples.
MOUNTS = {MountType.AZIMUTHAL: "AZEL", MountType.EQUATORIAL: "EQUA"}


class Skeleton(NamedTuple):
    """Lines written commented out, because what goes in them is not a scheduler's to say.

    Attributes:
        needs (str): What has to be supplied, in words, for the report and for the file.
        lines (Tuple[str, ...]): The keys, with their shape, written commented.
    """

    needs: str
    lines: Tuple[str, ...]


#: Per station: everything about the recording and the correlation model. **The list the report
#: is made of** -- there is no second copy, so a line cannot be written and go unreported.
STATION_SKELETON = Skeleton(
    "the recording format, the data files, and the clock -- all known after observing", (
        "FORMAT** = <Mark5B-256-4-2 | RDF_128-4-1-4 | ...>",
        "%P = <directory holding the recorded data>",
        "DATA_FILES = <count>",
        "FILE00 = %P:<file>",
        "TIMEOFS00 = <offset>, <MJD>       # comes out of the delay model, per file",
        "POLY_FILE = %W:<delay model>",
        "CLOCK DATE = <dd>d<mm>m<yyyy>y<hh>h<mm>m<ss>s",
        "CLOCK DELAY = <seconds>",
        "CLOCK RATE = <s/s>",
        "FREQ OFF = <Hz>",
    ))

#: The clock section: measured against a reference station during correlation.
CLOCK_SKELETON = Skeleton(
    "clock offsets, which are measured during correlation rather than scheduled", (
        "CLOCK = <station>, <dd>d<mm>m<yyyy>y<hh>h<mm>m<ss>s, <delay>, <rate>, <acceleration>",
    ))

#: The output section. `OBSERVER` and the sub-bands are ours; the rest is the correlator's.
OUTPUT_SKELETON = Skeleton(
    "where the correlator writes and how it is set up", (
        "%W = <working directory>",
        "ARIAD_PATH = <correlator>",
        "OUT FILE = %W:<name>.uvx",
        "CHANNELS = <spectral channels>",
        "SOL INT = <seconds>",
        "PULSAR BINNING = false",
        "AUTOSQ = 1",
    ))

#: Fields of `TLSC_PAR` this model does not carry. Positional, so they are written blank, and
#: named above the line so that a blank is read as a blank rather than as zero.
TLSC_PAR_BLANKS = Skeleton(
    "a station's axis offset and the epoch its coordinates were measured at", ())


class _Channel(NamedTuple):
    """One recorded channel: a band, one of its sidebands, one of its polarizations."""

    band: IF
    sideband: str
    polarization: str


class _Mode(NamedTuple):
    """A distinct frequency setup, which is what one CFX file describes."""

    name: str
    bands: Tuple[IF, ...]
    channels: Tuple[_Channel, ...]


# --- CFX's spelling --------------------------------------------------------------------------

def cfx_epoch(moment: Time) -> str:
    """Return a moment as CFX writes one: `18d11m2012y13h50m00s`."""
    when = moment.datetime
    return (f"{when.day:02d}d{when.month:02d}m{when.year}y"
            f"{when.hour:02d}h{when.minute:02d}m{when.second:02d}s")


def _comment(text: str) -> str:
    """Return a line CFX reads as a comment, indented as a key would be."""
    return f"{HASH}{INDENT}{text}"


def _note(text: str) -> str:
    """Return a line of prose about a section."""
    return f"{HASH} {text}"


def _channels_of(bands: Sequence[IF]) -> Tuple[_Channel, ...]:
    """Return every channel a set of bands records, in the order the file lists them.

    Notes:
        - Sideband outermost then polarization, as in the VEX writer, so that the two files of
          one experiment can be read side by side.
    """
    channels: List[_Channel] = []
    for band in bands:
        for sideband in SIDEBAND_ORDER:
            if sideband not in band.get_sidebands():
                continue
            for polarization in (band.polarizations or [""]):
                channels.append(_Channel(band, sideband, polarization))
    return tuple(channels)


def _sub_bands(bands: Sequence[IF]) -> List[float]:
    """Return the lower edge of every recorded piece of spectrum, for `[$OUTPAR]`.

    Notes:
        - The example lists `IF = 4812.00` and `IF = 4828.00` for one band at 4828 MHz with
          both sidebands: the two 16 MHz halves it covers. Asked of `IF.band_of` one sideband
          at a time, so this does not become a second place that decides which way a sideband
          runs.
    """
    edges = []
    for band in bands:
        for sideband in SIDEBAND_ORDER:
            if sideband not in band.get_sidebands():
                continue
            low, _high = IF.band_of(band.frequency, band.bandwidth, [sideband])
            if low not in edges:
                edges.append(low)
    return sorted(edges)


# --- the sections ----------------------------------------------------------------------------

def _station_section(telescope: Telescope, mode: _Mode) -> List[str]:
    """Return one `[$TLSC]`: where the station is, or where its orbit file is, and what it records.

    Notes:
        - **A space telescope has no `TLSC_PAR` and does have an `ORB_FILE`**, which is exactly
          how the example writes RadioAstron. It is the reason this format suits this model:
          nothing has to be pretended about a station that moves.
        - `TLSC_PAR` is positional, so a field this model does not carry is written blank and
          named in the comment above it. A velocity of zero would be a claim that a station is
          tectonically fixed, and the model defaults it to zero.
    """
    lines = ["[$TLSC]",
             f"{INDENT}name = {telescope.name}",
             f"{INDENT}iam_name = {telescope.get_code()}"]

    if isinstance(telescope, SpaceTelescope):
        orbit = telescope.get_orbit()
        if orbit:
            lines.append(f"{INDENT}ORB_FILE = {orbit}")
        else:
            lines.append(_comment("This spacecraft is modelled by Keplerian elements rather "
                                  "than an orbit file; the correlator wants a file."))
            lines.append(_comment("ORB_FILE = <orbit file>"))
    else:
        x, y, z = telescope.get_coordinates()
        velocities = telescope.get_velocities()
        speeds = (", ".join(f"{value:.6f}" for value in velocities) if any(velocities)
                  else ", , ")
        blank = "the velocity, " if not any(velocities) else ""
        lines.append(_comment(f"TLSC_PAR fields left blank: {blank}the axis offset and the "
                              f"epoch the coordinates were measured at."))
        lines.append(f"{INDENT}TLSC_PAR = {x:.5f}, {y:.5f}, {z:.5f}, {speeds}, , , "
                     f"{MOUNTS.get(telescope.mount_type, '')}")

    lines.append(_note(f"Not stated: {STATION_SKELETON.needs}."))
    for statement in STATION_SKELETON.lines:
        lines.append(_comment(statement))

    for channel in mode.channels:
        letter = POLARIZATION_LETTERS.get(channel.polarization)
        if letter is None:
            lines.append(_comment(f"IF = {channel.band.frequency:.2f}, <polarization>, "
                                  f"{channel.sideband}"))
        else:
            lines.append(f"{INDENT}IF = {channel.band.frequency:.2f}, {letter}, "
                         f"{channel.sideband}")
    lines.append("[$end]")
    lines.append("")
    return lines


def _source_section(source: Source) -> List[str]:
    """Return one `[$SOURCE]`, in degrees, which is how CFX states a position."""
    return ["[$SOURCE]",
            f"{INDENT}name = {source.name}",
            f"{INDENT}RA = {source.ra_degrees:.10f}",
            f"{INDENT}DEC = {source.dec_degrees:.10f}",
            f"{INDENT}EPOCH = 2000",
            "[$END]",
            ""]


def _scan_section(scan, codes: Sequence[str]) -> List[str]:
    """Return one `[$skan]`: when it starts, how long it runs, what it looks at, and who is on it."""
    return ["[$skan]",
            f"{INDENT}start = {cfx_epoch(scan.get_start())} , "
            f"{int(round(scan.get_duration()))}s",
            f"{INDENT}source = {scan.source.name}",
            f"{INDENT}telescopes = {', '.join(codes)}",
            "[$end]",
            ""]


def _skeleton_section(header: str, closer: str, skeleton: Skeleton) -> List[str]:
    """Return a section that is present and says only what belongs in it."""
    lines = [header, _note(f"Not stated: {skeleton.needs}.")]
    for statement in skeleton.lines:
        lines.append(_comment(statement))
    lines.append(closer)
    lines.append("")
    return lines


def _output_section(experiment: str, bands: Sequence[IF]) -> List[str]:
    """Return `[$OUTPAR]`: the experiment and its sub-bands, and nothing else stated."""
    lines = ["[$OUTPAR]", f"{INDENT}OBSERVER = {experiment}"]
    for edge in _sub_bands(bands):
        lines.append(f"{INDENT}IF = {edge:.2f}")
    lines.append(_note(f"Not stated: {OUTPUT_SKELETON.needs}."))
    for statement in OUTPUT_SKELETON.lines:
        lines.append(_comment(statement))
    lines.append("[$END]")
    lines.append("")
    return lines


# --- putting it together -----------------------------------------------------------------------

def collect_modes(scans: Sequence) -> List[_Mode]:
    """Return the distinct frequency setups the scans use, in a stable order.

    Notes:
        - A mode is identified by *which bands*, not by the order a scan lists them in. Within
          a mode the bands are ordered by frequency, which is deterministic and is the order a
          person reads them in.
    """
    modes: List[_Mode] = []
    seen = set()
    for scan in scans:
        bands = tuple(sorted((band for band in scan.frequencies if band.isactive),
                             key=lambda band: (band.frequency, band.name)))
        identity = tuple(band.name for band in bands)
        if not bands or identity in seen:
            continue
        seen.add(identity)
        modes.append(_Mode(name=f"MODE{len(modes) + 1:02d}", bands=bands,
                           channels=_channels_of(bands)))
    return modes


def write_cfx(observation: Observation,
              *, generator: str = "pAstroCORE") -> List[Tuple[_Mode, str, Dict[str, Any]]]:
    """Write an observation as CFX -- one file per frequency setup.

    Args:
        observation (Observation): What to write. Its active scans are the schedule.
        generator (str): What to name as the file's author, in the header comment.

    Returns:
        List[Tuple[_Mode, str, Dict[str, Any]]]: One `(mode, text, report)` per frequency
            setup. A report names the stations, sources and channels written, what was left out
            and why, and everything the file leaves to be completed.

    Raises:
        ValueError: If there is nothing to write: no active scan, or no station on any of them.

    Notes:
        - **A space telescope is written, not excluded.** That is the whole reason this format
          matters here, and the difference from the VEX writer.
    """
    scans = observation.get_scans().get_active_scans(observation)
    if not scans:
        raise ValueError("The observation has no active scans, so there is no schedule to write")

    experiment = observation.get_observation_code() or observation.name
    modes = collect_modes(scans)
    if not modes:
        raise ValueError("No active scan names an active frequency band, so no correlator "
                         "setup can be written")

    written: List[Tuple[_Mode, str, Dict[str, Any]]] = []
    for mode in modes:
        of_this_mode = [scan for scan in scans
                        if tuple(sorted((band.name for band in scan.frequencies
                                         if band.isactive))) ==
                        tuple(sorted(band.name for band in mode.bands))]
        text, report = _one_file(observation, experiment, mode, of_this_mode, generator)
        if report["scans"]:
            written.append((mode, text, report))

    if not written:
        raise ValueError("Every active scan was excluded; there is nothing to write")
    return written


def _one_file(observation: Observation, experiment: str, mode: _Mode, scans: Sequence,
              generator: str) -> Tuple[str, Dict[str, Any]]:
    """Write one frequency setup: its stations, its sources, its scans and its output section."""
    excluded: List[Dict[str, str]] = []
    on_scan: Dict[str, Telescope] = {}
    for scan in scans:
        for telescope in scan.telescopes:
            if telescope.isactive:
                on_scan.setdefault(telescope.name, telescope)

    telescopes = sorted(on_scan.values(), key=lambda t: (not isinstance(t, SpaceTelescope),
                                                        t.name))
    if not telescopes:
        raise ValueError("No active station appears on any scan of this frequency setup")

    entries, sources = [], {}
    for scan in scans:
        codes = [t.get_code() for t in telescopes
                 if any(t.name == on.name for on in scan.telescopes)]
        if scan.source is None or not codes:
            excluded.append({"scan": scan.name,
                             "reason": "no source, or no active station on it"})
            continue
        sources.setdefault(scan.source.name, scan.source)
        entries.append((scan, codes))

    lines = [_note(f"Written by {generator}"),
             _note(f"Experiment {experiment}, frequency setup {mode.name}"),
             _note("Everything known only after observing -- the recorded data, the clock, "
                   "the correlator settings -- is present and commented out."),
             ""]
    for telescope in telescopes:
        lines.extend(_station_section(telescope, mode))
    for source in sorted(sources.values(), key=lambda s: s.name):
        lines.extend(_source_section(source))
    for scan, codes in entries:
        lines.extend(_scan_section(scan, codes))
    lines.extend(_skeleton_section("[$CLOCK]", "[$END]", CLOCK_SKELETON))
    lines.extend(_output_section(experiment, mode.bands))

    spacecraft = [t.get_code() for t in telescopes if isinstance(t, SpaceTelescope)]
    report = {
        "experiment": experiment,
        "mode": mode.name,
        "scans": len(entries),
        "stations": [t.get_code() for t in telescopes],
        "spacecraft": spacecraft,
        "sources": sorted(sources),
        "channels": len(mode.channels),
        "excluded": excluded,
        "to_complete": [{"block": "[$TLSC]", "needs": STATION_SKELETON.needs},
                        {"block": "[$TLSC]", "needs": TLSC_PAR_BLANKS.needs},
                        {"block": "[$CLOCK]", "needs": CLOCK_SKELETON.needs},
                        {"block": "[$OUTPAR]", "needs": OUTPUT_SKELETON.needs}],
    }
    logger.info("Wrote CFX for '%s' %s: %s scans, %s stations, %s channels", experiment,
                mode.name, len(entries), len(telescopes), len(mode.channels))
    return "\n".join(lines) + "\n", report
