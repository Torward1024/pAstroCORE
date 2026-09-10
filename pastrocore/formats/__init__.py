# formats/__init__.py
"""Contracts with software nobody here controls.

A module in here turns the model into a file some other program reads, and knows that program's
vocabulary and nothing else: no Qt, no manipulator, no request. What is here is a function of
an `Observation` -- given the same observation it writes the same bytes, which is what makes a
characterization test possible at all.

Each format is reached as its own operation on the manipulator, and the `Super` that does it is
the only thing that knows both this and the request. That is deliberate: `ScheduleData` writes
what a person wants to look at, and these write a contract with a correlator. Mixing them would
give one this module's vocabulary and give the other that module's tolerance for close enough.
"""
import re
from typing import Any, List, NamedTuple, Sequence, Tuple

#: Our polarizations in the letter both formats use. `if_def` names one per intermediate
#: frequency in VEX and an `IF =` line carries one in CFX, and they are the same letters.
POLARIZATION_LETTERS = {"RCP": "R", "LCP": "L", "H": "H", "V": "V"}

#: Sideband order within a band. `L` first, as `sched` writes it, so the two files of one
#: experiment list their channels the same way round and a diff against anyone else's lines up.
SIDEBAND_ORDER = ("L", "U")

#: Characters a name in either format may hold. Both want a bare word: a space, a colon or a
#: semicolon ends a statement or separates a field in one syntax or the other.
_NOT_IN_A_NAME = re.compile(r"[^A-Za-z0-9_.+-]")


def bare_name(text: str) -> str:
    """Return a name either format will accept, from whatever the model was given.

    Notes:
        - A project may call an observation anything at all, and a file may not.
    """
    cleaned = _NOT_IN_A_NAME.sub("_", str(text).strip())
    return cleaned or "unnamed"


class Skeleton(NamedTuple):
    """A block or a set of lines written empty, because what goes in it is not a scheduler's.

    Attributes:
        block (str): Where it belongs, spelled as its own format spells it -- `$DAS`, `[$TLSC]`.
        needs (str): What has to be supplied, in words, for the file and for the report.
        lines (Tuple[str, ...]): The statements, written commented out, so whoever completes
            the file has the shape in front of them.

    Notes:
        - **A report is made of these**, so a block cannot be written empty and go unreported,
          or reported and not written. Both formats had their own copy of this and CFX's report
          then named its blocks in string literals a second time.
    """

    block: str
    needs: str
    lines: Tuple[str, ...] = ()

    def as_reported(self) -> dict:
        """What this looks like in an operation's report."""
        return {"block": self.block, "needs": self.needs}


class Channel(NamedTuple):
    """One recorded channel: a band, one of its sidebands, one of its polarizations.

    Attributes:
        link (str): What VEX calls it in a `chan_def`. CFX has no link and ignores it.
        band (IF): The setting it came from.
        sideband (str): `U` or `L`.
        polarization (str): One of the model's, or empty where the model does not say.
    """

    link: str
    band: Any
    sideband: str
    polarization: str


class Mode(NamedTuple):
    """A distinct frequency setup, and every channel it records.

    Notes:
        - One VEX file holds several of these and one CFX file is one of them, which is the
          only place the two formats disagree about what a mode *is* -- not about what it holds.
    """

    name: str
    bands: Tuple[Any, ...]
    channels: Tuple[Channel, ...]

    def identity(self) -> Tuple[str, ...]:
        """What makes this setup the one it is: which bands, not the order a scan listed them."""
        return tuple(band.name for band in self.bands)


def bands_of(scan) -> Tuple[Any, ...]:
    """Return a scan's active bands, ordered by frequency.

    Notes:
        - Ordered rather than as the scan happens to hold them, so two scans with the same
          setup written differently are one mode, and so a file written twice is the same file.
    """
    return tuple(sorted((band for band in scan.frequencies if band.isactive),
                        key=lambda band: (band.frequency, band.name)))


def channels_of(bands: Sequence) -> Tuple[Channel, ...]:
    """Return every channel a set of bands records, in the order both formats list them.

    Notes:
        - Sideband outermost then polarization, which is the order `sched` writes and therefore
          the order anyone comparing two files expects.
        - The count is `sum(band.get_channel_count())` by construction, and that method is the
          model's own answer to the same question.
    """
    channels: List[Channel] = []
    for band in bands:
        for sideband in SIDEBAND_ORDER:
            if sideband not in band.get_sidebands():
                continue
            for polarization in (band.polarizations or [""]):
                channels.append(Channel(link=f"&CH{len(channels) + 1:02d}", band=band,
                                        sideband=sideband, polarization=polarization))
    return tuple(channels)


def collect_modes(scans: Sequence) -> List[Mode]:
    """Return the distinct frequency setups a set of scans uses, in a stable order.

    Notes:
        - Numbered `MODE01` upwards. A generated name rather than a derived one: a setup of
          four bands has no short name that is both readable and unique, and the comment above
          each `def` says what it holds.
    """
    modes: List[Mode] = []
    seen = set()
    for scan in scans:
        bands = bands_of(scan)
        identity = tuple(band.name for band in bands)
        if not bands or identity in seen:
            continue
        seen.add(identity)
        modes.append(Mode(name=f"MODE{len(modes) + 1:02d}", bands=bands,
                          channels=channels_of(bands)))
    return modes


def letter_for(polarization: str, unknown: str = "") -> str:
    """Return a polarization in the letter both formats use, or `unknown` if the model is silent.

    Notes:
        - A band with no polarization at all is legal in this model and means nothing was
          entered. Writing an empty field would read as an answer.
    """
    if not polarization:
        return unknown
    return POLARIZATION_LETTERS.get(polarization, polarization)



def build_observation(read: dict, *, code: str = None):
    """Turn what a format reader returned into an `Observation`.

    Args:
        read (dict): A reader's answer -- `code`, `telescopes`, `sources`, `bands`, `scans`.
        code (str): What to call the observation. The file's own experiment code by default.

    Returns:
        Tuple[Observation, List[str]]: What was built, and the scans this model would not hold.

    Raises:
        ValueError: If nothing usable was read.

    Notes:
        - **One builder for both formats**, because both readers answer in the same shape. A
          second one would be a second place for a scan to end up pointing at a source that is
          not in the observation.
        - What a reader passed over is passed over here too (V6): the hardware and the session
          are not this model's, an export leaves them for the station and the correlator to
          fill, and importing them would be carrying something nothing here can use or check.
        - **A scan this model refuses is named rather than forced in.** The ones that fit are
          imported and the rest are reported, so a partial reading is never mistaken for a
          whole one.
    """
    from pastrocore.base.observation import Observation

    observation = Observation(code=code or read.get("code") or "IMPORTED")

    telescopes = observation.get_telescopes()
    for entry in read.get("telescopes", {}).values():
        if entry.get("kind") == "space":
            telescopes.create_space_telescope(code=entry["code"], name=entry.get("name"),
                                              orbit_file=entry.get("orbit_file"),
                                              use_kep=False)
        else:
            telescopes.create_telescope(
                code=entry["code"], name=entry.get("name"),
                x=entry.get("x", 0.0), y=entry.get("y", 0.0), z=entry.get("z", 0.0),
                vx=entry.get("vx", 0.0), vy=entry.get("vy", 0.0), vz=entry.get("vz", 0.0),
                mount_type=entry.get("mount_type", "AZIM"))

    sources = observation.get_sources()
    for entry in read.get("sources", {}).values():
        if "ra_degrees" in entry:
            # CFX states a position in degrees; the model keeps hours and arcseconds, and
            # already knows how to convert. Built at zero and then set, so the one conversion
            # in the model is the one used.
            source = sources.create_source(name=entry["name"])
            source = sources.get(entry["name"])
            source.set_ra_degrees(float(entry["ra_degrees"]))
            source.set_dec_degrees(float(entry["dec_degrees"]))
        else:
            sources.create_source(
                name=entry["name"], ra_h=entry["ra_h"], ra_m=entry["ra_m"],
                ra_s=entry["ra_s"], de_d=entry["de_d"], de_m=entry["de_m"], de_s=entry["de_s"])

    frequencies = observation.get_frequencies()
    for entry in read.get("bands", {}).values():
        frequencies.create_if(name=entry["name"], frequency=entry["frequency"],
                              bandwidth=entry["bandwidth"],
                              polarizations=entry.get("polarizations") or None,
                              sidebands=entry.get("sidebands") or None)

    from msb_arch import InvariantError

    scans, refused = observation.get_scans(), []

    by_code = {telescope.get_code(): telescope for telescope in telescopes.get_items()}
    for entry in read.get("scans", []):
        source = sources.get(entry["source"]) if entry.get("source") else None
        on_it = [by_code[code] for code in entry.get("telescopes", []) if code in by_code]
        bands = [frequencies.get(name) for name in entry.get("bands", [])
                 if frequencies.get(name) is not None]
        if not on_it:
            refused.append(f"{entry['name']}: none of {entry.get('telescopes', [])} is a "
                           f"station this file defines")
            continue
        try:
            scans.create_scan(name=entry["name"], start=entry["start"],
                              duration=float(entry["duration"]), source=source,
                              telescopes=on_it, frequencies=bands, observation=observation)
        except InvariantError as e:
            refused.append(f"{entry['name']}: {e}")

    if not scans.get_items():
        raise ValueError("Nothing was read that this model can hold: no scan survived")
    return observation, refused
