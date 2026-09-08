"""Writing a schedule as VEX (V2, V4).

Two things are checked here and they are not the same thing.

**That the file is well formed.** The checker below reads VEX's punctuation and nothing else --
blocks, `def`s, `ref`s, statements -- and it is run against `re03fr.vex` and `s16tj07a.vex`
*first*, in the same tests. Those files were written by `sched` and by people this project has
never met, so a checker that accepts them is a checker calibrated against something other than
its own author's expectations. It is not a substitute for V3: a real parser is still the exit
criterion, and none is available here. It is what can honestly be claimed in the meantime.

**That the file says only what the model knows.** Every station-hardware block is present, and
present *empty*: the report names them, and the report and the file are made from one
declaration, so they cannot drift apart.

The reference file is regenerated deliberately:

    python -m pytest tests/test_vex.py --regenerate-vex
"""
import pathlib
import re

import pytest

from pastrocore.formats import vex
from pastrocore.super.schedule_manipulator import ScheduleManipulator

EXAMPLES = pathlib.Path("I:/format_examples")
REFERENCE = pathlib.Path(__file__).parent / "fixtures" / "reference.vex"


# --- reading VEX by its punctuation ---------------------------------------------------------

def statements(text):
    """Yield a VEX file's statements, with comments and quoted awkwardness dealt with.

    Notes:
        - `*` starts a comment to the end of the line *outside a quoted string*, and `;` ends a
          statement. That is the whole grammar this needs: nothing here interprets a statement,
          it only says where one begins and ends.
        - A `"` only opens a string where a value may begin -- after `=`, `:` or `,`. VEX also
          writes it as the arcsecond mark, and `dec = 11d43'50.903940"` would otherwise open a
          string that swallows the rest of the file. That is not a quirk of ours: it is in the
          `sched` output this checker is calibrated against.
    """
    collected, quoted, commented, previous = [], False, False, ""
    for character in text:
        if commented:
            if character == "\n":
                commented = False
            continue
        if character == '"' and (quoted or previous in ("=", ":", ",")):
            quoted = not quoted
        elif not quoted and character == "*":
            commented = True
            continue
        elif not quoted and character == ";":
            statement = " ".join("".join(collected).split())
            if statement:
                yield statement
            collected = []
            previous = ""
            continue
        if not character.isspace():
            previous = character
        collected.append(character)


def parse(text):
    """Return `{block: {def name: [statements]}}` for a VEX file."""
    blocks, block, current = {}, None, None
    for statement in statements(text):
        if statement.startswith("$"):
            block = statement
            blocks.setdefault(block, {})
        elif statement.startswith("def ") or statement.startswith("scan "):
            current = statement.split(None, 1)[1]
            blocks.setdefault(block, {})[current] = []
        elif statement in ("enddef", "endscan"):
            current = None
        elif current is not None:
            blocks[block][current].append(statement)
    return blocks


#: `ref $FREQ = NAME:Wb:Sv;` -- the station qualifiers after the name are not part of it.
REFERENCE_LINE = re.compile(r"^ref (\$[A-Z_]+) = ([^:]+)")


def references(text):
    """Yield every `(block, def name)` a file refers to."""
    for statement in statements(text):
        found = REFERENCE_LINE.match(statement)
        if found:
            yield found.group(1), found.group(2).strip()


def example(name):
    """Return one of the real files, or skip: they are the calibration, not the subject."""
    path = EXAMPLES / name
    if not path.exists():
        pytest.skip(f"{path} is not here; the real files calibrate the checker")
    return path.read_text(encoding="utf-8", errors="replace")


# --- what is written ------------------------------------------------------------------------

@pytest.fixture
def written(project):
    """A VEX file for the fixture project's observation, and its report."""
    core = ScheduleManipulator(project)
    observation = project.observations()[0]
    return vex.write_vex(observation)


@pytest.fixture
def dual(project):
    """The same observation with a band recording both sidebands in both polarizations.

    Notes:
        - The RadioAstron case, which is what the sideband field exists for: one receiver
          setting, four channels.
    """
    core = ScheduleManipulator(project)
    observation = project.observations()[0]
    band = observation.get_frequencies().get_items()[0]
    core.configure(observation.get_frequencies(),
                   set_if={"name": band.name, "sidebands": ["U", "L"],
                           "polarizations": ["RCP", "LCP"]})
    return vex.write_vex(observation)


# --- the checker, calibrated -----------------------------------------------------------------

@pytest.mark.parametrize("name", ["re03fr.vex", "s16tj07a.vex"])
def test_the_checker_accepts_a_file_written_by_sched(name):
    """Run first, and on purpose. A structural checker written beside the writer it checks
    proves nothing; one that also accepts two files from other people is at least reading the
    format rather than reading its author's mind."""
    text = example(name)
    blocks = parse(text)

    assert "$SCHED" in blocks, "no schedule was found in a file that certainly has one"
    for block, name_of in references(text):
        assert name_of in blocks.get(block, {}), f"{block} = {name_of} does not resolve"


def test_every_reference_resolves_to_a_definition(written):
    """A `ref` naming a `def` that is not there is a file a parser rejects -- and it is the
    failure an exporter that writes empty blocks is most likely to make."""
    text, _ = written
    blocks = parse(text)

    for block, name in references(text):
        assert name in blocks.get(block, {}), f"{block} = {name} does not resolve"


def test_the_file_carries_every_block_the_examples_do(written):
    """Structure per the format, not per what we happen to be able to fill in. The list comes
    from a real file rather than from the writer's own idea of completeness."""
    text, _ = written
    ours = set(parse(text))
    theirs = set(parse(example("re03fr.vex")))

    # `sched` marks these obsolete in its own output, and writes them for tape.
    obsolete = {"$HEAD_POS", "$PASS_ORDER"}
    missing = theirs - ours - obsolete

    assert not missing, f"blocks the real file has and ours does not: {sorted(missing)}"


# --- what it says, and what it refuses to say ------------------------------------------------

def test_a_band_with_both_sidebands_becomes_four_channels(dual):
    """One receiver setting at one sky frequency, recording both sidebands in both circular
    polarizations, is four `chan_def` lines and one `IF` object. That is the whole reason
    `sidebands` is a list."""
    text, report = dual
    channels = [line for line in text.splitlines() if line.strip().startswith("chan_def")]

    assert report["channels"] == 4
    assert len(channels) == 4
    assert sum(": U :" in line for line in channels) == 2
    assert sum(": L :" in line for line in channels) == 2


def test_the_sky_frequency_is_written_once_for_both_sidebands(dual):
    """A sideband is a direction from the sky frequency, not a different frequency. Writing
    4828 U as 4828 and 4828 L as 4812 would be the confusion the field exists to prevent."""
    text, _ = dual
    frequencies = {line.split(":")[1].strip() for line in text.splitlines()
                   if line.strip().startswith("chan_def")}

    assert len(frequencies) == 1, f"one band was written at several frequencies: {frequencies}"


def test_every_empty_block_is_named_in_the_report(written):
    """The report is how anyone finds out what is outstanding without reading the file. If a
    block can be written and go unreported, the report is decoration."""
    text, report = written
    reported = {entry["block"] for entry in report["to_complete"]}
    blocks = parse(text)

    for block in ("$DAS", "$BBC", "$TRACKS", "$PHASE_CAL_DETECT", "$PROCEDURES"):
        assert block in blocks, f"{block} is not in the file at all"
        assert all(not statements for statements in blocks[block].values()), \
            f"{block} carries a statement, which would be a claim about a station"
        assert block in reported, f"{block} is empty in the file and absent from the report"


def test_a_station_hardware_block_is_present_rather_than_omitted(written):
    """The decision this exporter turns on. An omitted block leaves the next tool to invent the
    structure; an empty one is a form, and filling it in is what `drudg` and the stations do."""
    text, _ = written
    blocks = parse(text)

    assert "$DAS" in blocks
    assert blocks["$DAS"], "$DAS is there but defines nothing, so no station has a place to fill"
    assert "record_transport_type" in text, "the shape of what is missing is not shown anywhere"


def test_a_velocity_of_zero_is_not_written_as_a_velocity(written):
    """The model defaults plate motion to zero and most projects never set it. Writing
    `0.000000 m/yr` states that a station is tectonically fixed, which is false everywhere and
    false by millimetres a year that a correlator notices."""
    text, _ = written

    assert "site_position" in text, "the positions themselves should certainly be written"
    for line in text.splitlines():
        if line.strip().startswith("site_velocity"):
            pytest.fail(f"a velocity this project does not have was written: {line.strip()}")


def test_a_space_telescope_is_excluded_by_name_rather_than_dropped(project):
    """VEX 1.5 describes a station as a place on the Earth. A spacecraft cannot be written, and
    silently leaving it out would produce a file that looks like the whole array."""
    core = ScheduleManipulator(project)
    observation = project.observations()[0]
    telescopes = observation.get_telescopes()
    core.configure(telescopes, create_space_telescope={"code": "RA", "use_kep": False})
    spacecraft = core.inspect(telescopes, get="RA")
    scan = observation.get_scans().get_items()[0]
    core.configure(scan, set_telescopes={"telescopes": list(scan.telescopes) + [spacecraft],
                                         "observation": observation})

    text, report = vex.write_vex(observation)
    excluded = {entry.get("telescope") for entry in report["excluded"]}

    assert "RA" in excluded, f"a spacecraft vanished from the report: {report}"
    assert "RA" not in report["stations"], "a spacecraft was written as a fixed site"
    assert "station = RA " not in text, "a spacecraft was put on a scan line"


def test_the_same_observation_writes_the_same_bytes(project):
    """Everything else here rests on it, and so does the reference file below. A dictionary
    iterated in whatever order it happens to have would pass every other test in this file."""
    observation = project.observations()[0]

    first, _ = vex.write_vex(observation)
    second, _ = vex.write_vex(observation)

    assert first == second


# --- the reference (V4) ------------------------------------------------------------------------

def test_the_file_is_the_one_that_was_agreed(written):
    """A change that alters the file fails the build. The reference is the whole file rather
    than a digest of it, because "the bytes moved" is not a useful thing to be told -- what a
    person needs is the diff."""
    text, _ = written
    if not REFERENCE.exists():
        pytest.skip("no reference yet; write one with --regenerate-vex")

    expected = REFERENCE.read_text(encoding="utf-8")
    if text == expected:
        return

    import difflib
    diff = "\n".join(list(difflib.unified_diff(
        expected.splitlines(), text.splitlines(),
        fromfile="reference.vex", tofile="written now", lineterm=""))[:60])
    pytest.fail(f"the VEX written has changed:\n{diff}\n\n"
                f"If that was intended:\n"
                f"    python -m pytest tests/test_vex.py --regenerate-vex")
