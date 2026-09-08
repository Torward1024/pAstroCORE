# formats/vex.py
"""Writing a schedule as VEX 1.5.

VEX is what stations and most correlators read, and it asks for more than a scheduling model
can honestly answer: which recorder is in the rack, which baseband converter a channel goes
through, how many tracks the fan-out uses. Those are facts about a station *this week*, they are
not published anywhere central, and a scheduling tool that invented them would be writing a file
that looks right and is not -- the correlator would take it.

**So the shape stays and the claims do not.** Every block the format calls for is written. What
this model knows carries real values; what it cannot know is an empty field or a `def` whose
statements are commented out, annotated in place with what belongs there. The file is a form to
be finished at the station, by `drudg` or by a person, rather than a file with holes in it.

Both halves of that are VEX's own idiom rather than an invention of ours: the example the map
was written against has empty fields in every `chan_def` `sched` wrote, comments out a whole
`ref` line rather than dropping it, and contains `def`s holding nothing but comments.

Nothing here knows about a manipulator, a request or a window. It is a function of an
`Observation`: the same observation writes the same bytes, which is the only reason a
characterization test over this is worth anything.
"""
import re
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple

from astropy.time import Time
from msb_arch.utils.logging_setup import logger

from pastrocore.base.frequencies import IF
from pastrocore.base.observation import Observation
from pastrocore.base.sources import Source
from pastrocore.base.telescope import MountType, Telescope

#: The revision this writes. VEX 2 exists; the stations and correlators this file is for read 1.5.
VEX_REV = "1.5"

#: What VEX indents a statement by, what it indents a note by, and what it rules a block off
#: with. Cosmetic, and worth matching: the people who read these files have read thousands
#: written by `sched`, and a file that looks unfamiliar gets read less carefully.
INDENT = "     "
NOTE = "    "
RULE = "*" + "-" * 78

#: Written where a polarization, a local oscillator or anything else is not known. It is a
#: placeholder on purpose: an empty field reads as an answer, and this does not.
UNKNOWN = "<not stated>"

#: Our polarizations in VEX's letters. `if_def` names one of these per intermediate frequency,
#: and a `chan_def` carries it only as the trailing comment `sched` writes.
POLARIZATION_LETTERS = {"RCP": "R", "LCP": "L", "H": "H", "V": "V"}

#: Sideband order within a band. `L` first, as `sched` writes it, so a diff against a file
#: from anywhere else lines up.
SIDEBAND_ORDER = ("L", "U")


class Skeleton(NamedTuple):
    """A block written empty because its content is a fact about a station's hardware.

    Attributes:
        block (str): The VEX block, with its dollar.
        needs (str): What has to be put in it, in words, for the report and for the file.
        lines (Tuple[str, ...]): The statements, written commented out so that whoever
            completes the file has the shape in front of them.
    """

    block: str
    needs: str
    lines: Tuple[str, ...]


#: Blocks that describe one station's hardware. One `def` per station, referred to from
#: `$STATION`, and empty. **This is the list the report is made of** -- there is no second copy
#: of it anywhere, so a block cannot be written and go unreported, or reported and not written.
PER_STATION_BLOCKS = (
    Skeleton("$DAS", "the recorder and electronics rack in use at the station", (
        "record_transport_type = <Mark5B | Mark6 | Flexbuff | ...>;",
        "electronics_rack_type = <Mark4 | VLBA4 | DBBC | ...>;",
        "number_drives = <count>;",
    )),
)

#: Blocks that describe a station's electronics as set up for one frequency mode. One `def` per
#: mode, referred to from `$MODE`.
PER_MODE_BLOCKS = (
    Skeleton("$BBC", "which baseband converter each channel is taken through", (
        "BBC_assign = &BBC01 : <physical BBC number> : &IF_A;",
    )),
    Skeleton("$TRACKS", "the recording format and its fan-out", (
        "track_frame_format = <MARK5B | VDIF | Mark4>;",
        "fanout_def = : &CH01 : sign : 1 : <track>;",
        "fanout_def = : &CH01 :  mag : 1 : <track>;",
    )),
    Skeleton("$PHASE_CAL_DETECT", "the phase-cal tone spacing and which tones are detected", (
        "phase_cal_detect = &PCAL : <tone> : <tone> : <tone>;",
    )),
    Skeleton("$PROCEDURES", "the setup a station runs around a scan", (
        'procedure_name_prefix = "<nn>";',
        "setup_always = on : <seconds> sec;",
        "preob_cal  = on : <seconds> sec : preob;",
        "midob_cal  = on : <seconds> sec : midob;",
        "postob_cal = on : <seconds> sec : postob;",
    )),
    Skeleton("$ROLL", "whether the recording is barrel-rolled, which is a tape-era question", (
        "roll = off;",
    )),
)

#: Statements left commented *inside* a block that otherwise carries real values, keyed by the
#: block they belong to. Each is a field this model does not have rather than a whole subject it
#: knows nothing about, and each is reported for the same reason as a whole block is.
OPEN_LINES: Dict[str, Skeleton] = {
    "$SITE": Skeleton("$SITE", "the epoch the site coordinates were measured at", (
        "site_position_epoch = <MJD>;",
    )),
    "$ANTENNA": Skeleton("$ANTENNA", "the antenna's axis offset and how fast it slews", (
        "axis_offset = <metres> m;",
        "antenna_motion = <axis> : <deg/min> deg/min : <settling> sec;",
    )),
    "$IF": Skeleton("$IF", "which physical IF and local oscillator each polarization comes "
                           "through", (
        "if_def = &IF_{index} : <physical IF> : {letter} : <LO> MHz : <U|L> : "
        "<pcal spacing> MHz;",
    )),
    "$FREQ": Skeleton("$FREQ", "the BBC and phase-cal links each channel is assigned to, which "
                               "are the trailing fields of a chan_def", ()),
}


class _Channel(NamedTuple):
    """One recorded channel: a band, one of its sidebands, one of its polarizations."""

    link: str
    band: IF
    sideband: str
    polarization: str


class _Mode(NamedTuple):
    """A distinct frequency setup, and every channel it records."""

    name: str
    bands: Tuple[IF, ...]
    channels: Tuple[_Channel, ...]


# --- turning model values into VEX's spelling --------------------------------------------

_NOT_IN_A_NAME = re.compile(r"[^A-Za-z0-9_.+-]")


def vex_name(text: str) -> str:
    """Return a name VEX will accept, from whatever the model was given.

    Notes:
        - A VEX name is a bare word: no spaces, no colons, no semicolons, since all three end
          a statement or separate a field. A project may call an observation anything at all.
    """
    cleaned = _NOT_IN_A_NAME.sub("_", str(text).strip())
    return cleaned or "unnamed"


def vex_epoch(moment: Time) -> str:
    """Return a moment as VEX writes one: `2012y323d13h50m00s`.

    Notes:
        - Day of year, not month and day. Seconds are truncated rather than rounded, because a
          scan that starts a second late is a scan that starts late.
    """
    when = moment.datetime
    return (f"{when.year}y{when.timetuple().tm_yday:03d}d"
            f"{when.hour:02d}h{when.minute:02d}m{when.second:02d}s")


def _right_ascension(source: Source) -> str:
    """Return a source's right ascension as `22h32m36.4089050s`."""
    return f"{int(source.ra_h):02d}h{int(source.ra_m):02d}m{source.ra_s:010.7f}s"


def _declination(source: Source) -> str:
    """Return a source's declination as `+11d43'50.903940"`.

    Notes:
        - The sign is written explicitly. VEX accepts a bare number, and a reader skimming a
          list of sources should not have to work out whether one is north or south.
    """
    return f"{int(source.de_d):+03d}d{int(source.de_m):02d}'{source.de_s:09.6f}\""


def _letter(polarization: str) -> str:
    """Return a polarization in VEX's letter, or the placeholder if the model does not say.

    Notes:
        - A band with no polarization at all is legal in this model and means nothing was
          entered. Writing an empty field there would read as an answer.
    """
    if not polarization:
        return UNKNOWN
    return POLARIZATION_LETTERS.get(polarization, polarization)


def _axis_type(telescope: Telescope) -> Optional[str]:
    """Return the mount as VEX's pair of axes, or None if the model does not say.

    Notes:
        - `SPACE` is a mount this format has no word for, and a space telescope does not reach
          here anyway: it is excluded before the antennas are written.
    """
    return {MountType.AZIMUTHAL: "az : el",
            MountType.EQUATORIAL: "ha : dec"}.get(telescope.mount_type)


# --- writing ------------------------------------------------------------------------------

def _comment(text: str, indent: str = INDENT) -> str:
    """Return a line VEX reads as a comment, indented as a statement would be."""
    return f"*{indent}{text}"


def _note(text: str) -> str:
    """Return a line of prose about a block, indented the way `sched` indents its own."""
    return f"*{NOTE}{text}"


def _plural(count: int, word: str) -> str:
    """Return `1 channel` and `4 channels`, because a file people read says one or the other."""
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _block(name: str) -> List[str]:
    """Return the opening of a block: a rule, the block, and the blank comment `sched` writes."""
    return [RULE, f"{name};", "*"]


def _skeleton(skeleton: Skeleton, names: Sequence[str]) -> List[str]:
    """Return a block of empty `def`s, one per name, with its statements commented out.

    Args:
        skeleton (Skeleton): The block, what it needs, and the shape of what goes in it.
        names (Sequence[str]): One `def` per name -- a station code, or a mode.

    Notes:
        - A `def` holding only comments is legal VEX and `sched` writes them, which is what
          makes this an empty form rather than a broken file: the `ref` that points here
          resolves, and the reader finds the statements it has to fill in.
    """
    lines = _block(skeleton.block)
    lines.append(_note(f"Not stated: {skeleton.needs}."))
    lines.append(_note("It is a fact about the station rather than about this schedule."))
    lines.append("*")
    for name in names:
        lines.append(f"def {name};")
        for statement in skeleton.lines:
            lines.append(_comment(statement))
        lines.append("enddef;")
        lines.append("*")
    return lines[:-1]


# --- the parts of the file ----------------------------------------------------------------

def _header(experiment: str, generator: str) -> List[str]:
    """Return the revision line and the note saying where the file came from."""
    return [f"VEX_rev = {VEX_REV};",
            _note(f"Written by {generator}"),
            _note(f"Experiment {experiment}"),
            _note("Blocks describing station hardware are present and empty: what belongs in "
                  "each is written in it, commented out.")]


def _global_and_exper(experiment: str, description: str, scans: Sequence) -> List[str]:
    """Return `$GLOBAL` and `$EXPER`, whose nominal span is the first and last scan."""
    lines = _block("$GLOBAL")
    lines.append(f"{INDENT}ref $EXPER = {experiment};")
    lines.extend(_block("$EXPER"))
    lines.append(f"def {experiment};")
    lines.append(f'{INDENT}exper_name = {experiment};')
    lines.append(f'{INDENT}exper_description = "{description}";')
    lines.append(f"{INDENT}exper_nominal_start = {vex_epoch(scans[0].get_start())};")
    lines.append(f"{INDENT}exper_nominal_stop = {vex_epoch(max(s.get_end() for s in scans))};")
    lines.append(_comment("Not stated: who is to correlate this, and who to contact about it."))
    lines.append(_comment("target_correlator = <correlator>;"))
    lines.append(_comment('PI_name = "<name>";'))
    lines.append("enddef;")
    return lines


def _mode_block(modes: Sequence[_Mode]) -> List[str]:
    """Return `$MODE`, one `def` per frequency setup, referring to every block it needs."""
    lines = _block("$MODE")
    referred = ["$PROCEDURES", "$FREQ", "$IF", "$BBC", "$TRACKS", "$PHASE_CAL_DETECT", "$ROLL"]
    for mode in modes:
        lines.append(f"def {mode.name};")
        lines.append(_comment(_describe(mode)))
        for block in referred:
            lines.append(f"{INDENT}ref {block} = {mode.name};")
        lines.append("enddef;")
        lines.append("*")
    return lines[:-1]


def _describe(mode: _Mode) -> str:
    """Return a mode in one line of words, for the comment above its `def`.

    Notes:
        - The covered span is written out beside the sky frequency, because that is the thing
          a sideband decides and the thing two bands can silently agree on: 4828 U and 4844 L
          are the same 16 MHz, and a reader should be able to see it here.
    """
    bands = []
    for band in mode.bands:
        low, high = band.get_band()
        bands.append(f"{band.frequency:g} MHz {'+'.join(band.get_sidebands())} "
                     f"x {band.bandwidth:g} MHz, covering {low:g}-{high:g}")
    return f"{_plural(len(mode.channels), 'channel')}: " + "; ".join(bands)


def _station_block(stations: Sequence[Tuple[str, Telescope]]) -> List[str]:
    """Return `$STATION`, tying each station key to its site, antenna and (empty) rack."""
    lines = _block("$STATION")
    for key, telescope in stations:
        site = vex_name(telescope.name)
        lines.append(f"def {key};")
        lines.append(f"{INDENT}ref $SITE = {site};")
        lines.append(f"{INDENT}ref $ANTENNA = {site};")
        lines.append(f"{INDENT}ref $DAS = {key};")
        lines.append("enddef;")
        lines.append("*")
    return lines[:-1]


def _site_block(stations: Sequence[Tuple[str, Telescope]]) -> List[str]:
    """Return `$SITE`: where each station is, and the epoch of that, which the model has not.

    Notes:
        - **A velocity of zero is not written as a velocity.** The model's default is zero and
          most projects never set it, so writing `0.000000 m/yr` would state that a station is
          tectonically fixed -- which is false everywhere, and by millimetres a year that a
          correlator cares about. A station that does carry one has it written.
    """
    lines = _block("$SITE")
    for key, telescope in stations:
        x, y, z = telescope.get_coordinates()
        velocities = telescope.get_velocities()
        lines.append(f"def {vex_name(telescope.name)};")
        lines.append(f"{INDENT}site_type = fixed;")
        lines.append(f"{INDENT}site_name = {vex_name(telescope.name)};")
        lines.append(f"{INDENT}site_ID = {key};")
        lines.append(f"{INDENT}site_position = {x:15.5f} m: {y:15.5f} m: {z:15.5f} m;")
        if any(velocities):
            vx, vy, vz = velocities
            lines.append(f"{INDENT}site_velocity = {vx:9.6f} m/yr: {vy:9.6f} m/yr: "
                         f"{vz:9.6f} m/yr;")
        else:
            lines.append(_comment("This project carries no plate motion for this station; "
                                  "zero would be a claim, not a blank."))
            lines.append(_comment("site_velocity = <vx> m/yr: <vy> m/yr: <vz> m/yr;"))
        for statement in OPEN_LINES["$SITE"].lines:
            lines.append(_comment(statement))
        lines.append("enddef;")
        lines.append("*")
    return lines[:-1]


def _antenna_block(stations: Sequence[Tuple[str, Telescope]]) -> List[str]:
    """Return `$ANTENNA`: the mount, the horizon the schedule was made against, and no more.

    Notes:
        - The horizon is written from `elevation_range`, and labelled as what it is. It is not
          a survey of the local skyline -- it is the limit every visibility in this project was
          calculated against, which is worth stating precisely because a station's real horizon
          may be worse.
    """
    lines = _block("$ANTENNA")
    for _, telescope in stations:
        low, _high = telescope.get_elevation_range()
        first, last = telescope.get_azimuth_range()
        lines.append(f"def {vex_name(telescope.name)};")
        axis = _axis_type(telescope)
        if axis:
            lines.append(f"{INDENT}axis_type = {axis};")
        else:
            lines.append(_comment("The model gives no axis type for this antenna."))
            lines.append(_comment("axis_type = <az : el | ha : dec>;"))
        lines.append(_comment("The elevation limit this schedule was calculated against, not a "
                              "survey of the skyline."))
        lines.append(f"{INDENT}horizon_map_az = 0.0 deg: 360.0;")
        lines.append(f"{INDENT}horizon_map_el = {low:.1f} deg: {low:.1f};")
        if (first, last) != (0.0, 360.0):
            # VEX 1.5 has no statement for an azimuth limit, and a horizon map cannot express
            # one. Saying so is the only way it does not vanish between here and the station.
            lines.append(_comment(f"This antenna is limited to azimuth {first:g}-{last:g} deg, "
                                  "which VEX 1.5 has nowhere to state."))
        for statement in OPEN_LINES["$ANTENNA"].lines:
            lines.append(_comment(statement))
        lines.append("enddef;")
        lines.append("*")
    return lines[:-1]


def _source_block(sources: Sequence[Source]) -> List[str]:
    """Return `$SOURCE`, in J2000, with whatever other names the model carries."""
    lines = _block("$SOURCE")
    for source in sources:
        lines.append(f"def {vex_name(source.name)};")
        lines.append(f"{INDENT}source_name = {vex_name(source.name)};")
        written = {source.name}
        for alternate in (source.name_J2000, source.alt_name):
            if alternate and alternate not in written:
                written.add(alternate)
                lines.append(_comment(f"alternate source name: {alternate}"))
        lines.append(f"{INDENT}ra = {_right_ascension(source)}; "
                     f"dec = {_declination(source)}; ref_coord_frame = J2000;")
        lines.append("enddef;")
        lines.append("*")
    return lines[:-1]


def _freq_block(modes: Sequence[_Mode]) -> List[str]:
    """Return `$FREQ`: the sky frequency, sideband and bandwidth of every channel.

    Notes:
        - **This is the block the model actually owns**, and the only one whose values are all
          ours. A `chan_def`'s trailing fields -- the BBC link and the phase-cal link -- are
          left off entirely rather than pointed at links that do not exist; VEX allows trailing
          fields to be omitted, and a dangling `&BBC01` would fail a parser that checks them.
        - `sample_rate` is Nyquist for the bandwidth, which is a fact about sampling rather
          than about a rack. It is written only when every channel of the mode shares a
          bandwidth, because VEX states it once per `def` and there would otherwise be no
          single true answer.
    """
    lines = _block("$FREQ")
    lines.append(_note(f"Not stated: {OPEN_LINES['$FREQ'].needs}."))
    lines.append("*")
    for mode in modes:
        bandwidths = {band.bandwidth for band in mode.bands}
        lines.append(f"def {mode.name};")
        lines.append(_comment(_describe(mode)))
        if len(bandwidths) == 1:
            bandwidth = next(iter(bandwidths))
            lines.append(f"{INDENT}sample_rate = {2 * bandwidth:.3f} Ms/sec;"
                         f"  * Nyquist for {bandwidth:g} MHz")
        else:
            lines.append(_comment("The channels of this mode differ in bandwidth, so one "
                                  "sample rate cannot state them all."))
            lines.append(_comment("sample_rate = <rate> Ms/sec;"))
        for channel in mode.channels:
            statement = (f"{INDENT}chan_def = : {channel.band.frequency:9.2f} MHz : "
                         f"{channel.sideband} : {channel.band.bandwidth:6.2f} MHz : "
                         f"{channel.link};")
            if channel.polarization:
                statement += f"  *{_letter(channel.polarization)}"
            lines.append(statement)
        lines.append("enddef;")
        lines.append("*")
    return lines[:-1]


def _if_block(modes: Sequence[_Mode]) -> List[str]:
    """Return `$IF`: the polarizations, which are ours, written as the form a station fills in.

    Notes:
        - Every field of an `if_def` but the polarization belongs to the station -- which
          physical IF, which local oscillator, what the phase-cal spacing is -- so the
          statement is written commented with the polarization already in it. Half a statement
          live and half invented would be worse than a whole one shown as a template.
    """
    skeleton = OPEN_LINES["$IF"]
    lines = _block("$IF")
    lines.append(_note(f"Not stated: {skeleton.needs}."))
    lines.append(_note("The polarizations below are this schedule's; everything else in the "
                       "line is the station's."))
    lines.append("*")
    for mode in modes:
        polarizations: List[str] = []
        for channel in mode.channels:
            if channel.polarization not in polarizations:
                polarizations.append(channel.polarization)
        lines.append(f"def {mode.name};")
        for index, polarization in enumerate(polarizations):
            for statement in skeleton.lines:
                lines.append(_comment(statement.format(index=index + 1,
                                                       letter=_letter(polarization))))
        lines.append("enddef;")
        lines.append("*")
    return lines[:-1]


def _sched_block(experiment: str, entries: Sequence[Dict[str, Any]]) -> List[str]:
    """Return `$SCHED`: when each scan starts, what it looks at, and who is on it.

    Notes:
        - A station line states the two times it can: recording starts at the scan and stops
          after its duration. The fields after that -- start position on the medium, pass,
          sector, drive -- are about the recorder, and are left off.
        - Scans are numbered rather than named. A scan's name in this model may be a UUID,
          which is legal VEX and unreadable; the model's name goes in a comment so that a
          person can still match a line here to a row in the interface.
    """
    lines = _block("$SCHED")
    lines.append(_note(f"Schedule for experiment {experiment}"))
    lines.append(_note("Station lines give data_good and data_stop. The recorder's own fields "
                       "-- start position, pass, sector, drive -- are left off."))
    for number, entry in enumerate(entries, start=1):
        lines.append(f"scan No{number:04d};")
        lines.append(_comment(f"{entry['scan_name']}"))
        lines.append(f"{INDENT}start = {entry['start']}; mode = {entry['mode']}; "
                     f"source = {entry['source']};")
        for key in entry["stations"]:
            lines.append(f"{INDENT}station = {key} : 0 sec : {entry['duration']} sec;")
        lines.append("endscan;")
    return lines


# --- putting it together -------------------------------------------------------------------

def _station_keys(telescopes: Sequence[Telescope]) -> Dict[str, str]:
    """Return the VEX station key for each telescope, by the telescope's name.

    Notes:
        - The code, which is what a station is called everywhere else in VEX. Two telescopes
          may carry one code in this model, and VEX keys have to be distinct, so a collision
          falls back to the telescope's own name -- which is unique, because it is what the
          container keys on.
    """
    seen: Dict[str, int] = {}
    for telescope in telescopes:
        seen[telescope.get_code()] = seen.get(telescope.get_code(), 0) + 1
    return {telescope.name: vex_name(telescope.get_code() if seen[telescope.get_code()] == 1
                                     else telescope.name)
            for telescope in telescopes}


def _channels_of(bands: Sequence[IF]) -> Tuple[_Channel, ...]:
    """Return every channel a set of bands records, numbered in the order VEX lists them.

    Notes:
        - Sideband outermost then polarization, which is the order `sched` writes and therefore
          the order anyone comparing two files expects. The count is
          `sum(band.get_channel_count())` by construction, and that method is the model's own
          answer to the same question.
    """
    channels: List[_Channel] = []
    for band in bands:
        for sideband in SIDEBAND_ORDER:
            if sideband not in band.get_sidebands():
                continue
            for polarization in (band.polarizations or [""]):
                channels.append(_Channel(link=f"&CH{len(channels) + 1:02d}", band=band,
                                         sideband=sideband, polarization=polarization))
    return tuple(channels)


def _collect_modes(scans: Sequence) -> Tuple[List[_Mode], Dict[Tuple[str, ...], _Mode]]:
    """Return the distinct frequency setups the scans use, and the map from a setup to its mode.

    Notes:
        - A mode is identified by *which bands*, not by the order a scan happens to list them
          in, so two scans with the same setup written differently are one mode. Within a mode
          the bands are ordered by frequency, which is both deterministic and the order a
          person reads them in.
    """
    modes: List[_Mode] = []
    by_bands: Dict[Tuple[str, ...], _Mode] = {}
    for scan in scans:
        bands = tuple(sorted((band for band in scan.frequencies if band.isactive),
                             key=lambda band: (band.frequency, band.name)))
        if not bands:
            continue
        identity = tuple(band.name for band in bands)
        if identity in by_bands:
            continue
        mode = _Mode(name=f"MODE{len(modes) + 1:02d}", bands=bands,
                     channels=_channels_of(bands))
        modes.append(mode)
        by_bands[identity] = mode
    return modes, by_bands


def write_vex(observation: Observation, *, generator: str = "pAstroCORE") -> Tuple[str, Dict[str, Any]]:
    """Write an observation as a VEX file, and report what the file does not state.

    Args:
        observation (Observation): What to write. Its active scans are the schedule.
        generator (str): What to name as the file's author, in the header comment.

    Returns:
        Tuple[str, Dict[str, Any]]: The file, and a report -- the stations, modes and sources
            written, what was left out and why, and every block awaiting a station's answer.

    Raises:
        ValueError: If there is nothing to write: no active scan, or no ground station on any
            of them.

    Notes:
        - **Space telescopes are excluded, and named in the report.** VEX 1.5 describes a
          station as a fixed position on the Earth; there is no honest way to write an orbit
          in it. CFX is where a space telescope belongs, and it is an ordinary station there.
    """
    scans = observation.get_scans().get_active_scans(observation)
    if not scans:
        raise ValueError("The observation has no active scans, so there is no schedule to write")

    experiment = vex_name(observation.get_observation_code() or observation.name)
    excluded: List[Dict[str, str]] = []

    on_scan: Dict[str, Telescope] = {}
    for scan in scans:
        for telescope in scan.telescopes:
            if not telescope.isactive:
                continue
            if isinstance(telescope, Telescope) and type(telescope) is not Telescope:
                # A SpaceTelescope, or anything else deriving from Telescope: it has an orbit
                # rather than a position, and this format has nowhere to put one.
                if telescope.name not in {entry["telescope"] for entry in excluded}:
                    excluded.append({"telescope": telescope.name,
                                     "reason": "VEX 1.5 has no orbiting station; use CFX"})
                continue
            on_scan.setdefault(telescope.name, telescope)

    if not on_scan:
        raise ValueError("No ground station appears on any active scan, and VEX 1.5 cannot "
                         "describe an orbiting one")

    telescopes = sorted(on_scan.values(), key=lambda t: t.name)
    keys = _station_keys(telescopes)
    stations = [(keys[telescope.name], telescope) for telescope in telescopes]

    modes, by_bands = _collect_modes(scans)
    if not modes:
        raise ValueError("No active scan names an active frequency band, so no mode can be "
                         "written")

    entries: List[Dict[str, Any]] = []
    sources: Dict[str, Source] = {}
    for scan in scans:
        bands = tuple(sorted((band for band in scan.frequencies if band.isactive),
                             key=lambda band: (band.frequency, band.name)))
        mode = by_bands.get(tuple(band.name for band in bands))
        on_it = [keys[t.name] for t in scan.telescopes if t.name in keys and t.isactive]
        if mode is None or not on_it or scan.source is None:
            excluded.append({"scan": scan.name,
                             "reason": "no source, no active band, or no ground station on it"})
            continue
        sources.setdefault(scan.source.name, scan.source)
        entries.append({"scan_name": scan.name, "start": vex_epoch(scan.get_start()),
                        "mode": mode.name, "source": vex_name(scan.source.name),
                        "duration": int(round(scan.get_duration())),
                        "stations": on_it})

    if not entries:
        raise ValueError("Every active scan was excluded; there is nothing to write")

    written = [name for name in (mode.name for mode in modes)
               if name in {entry["mode"] for entry in entries}]
    modes = [mode for mode in modes if mode.name in written]

    lines: List[str] = []
    lines.extend(_header(experiment, generator))
    lines.extend(_global_and_exper(experiment, observation.name, scans))
    lines.extend(_mode_block(modes))
    lines.extend(_station_block(stations))
    lines.extend(_source_block(sorted(sources.values(), key=lambda s: s.name)))
    lines.extend(_site_block(stations))
    lines.extend(_antenna_block(stations))
    lines.extend(_freq_block(modes))
    lines.extend(_if_block(modes))
    for skeleton in PER_MODE_BLOCKS:
        lines.extend(_skeleton(skeleton, [mode.name for mode in modes]))
    for skeleton in PER_STATION_BLOCKS:
        lines.extend(_skeleton(skeleton, [key for key, _ in stations]))
    lines.extend(_sched_block(experiment, entries))
    lines.append(RULE)

    report = {
        "experiment": experiment,
        "scans": len(entries),
        "stations": [key for key, _ in stations],
        "modes": [mode.name for mode in modes],
        "sources": sorted(sources),
        "channels": sum(len(mode.channels) for mode in modes),
        "excluded": excluded,
        "to_complete": [{"block": skeleton.block, "needs": skeleton.needs}
                        for skeleton in (PER_MODE_BLOCKS + PER_STATION_BLOCKS
                                         + tuple(OPEN_LINES.values()))],
    }
    logger.info("Wrote VEX for '%s': %s scans, %s stations, %s modes", experiment,
                len(entries), len(stations), len(modes))
    return "\n".join(lines) + "\n", report
