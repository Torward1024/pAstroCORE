"""Writing a schedule as CFX, for the ASC correlator (X1).

The same two claims as the VEX suite, and one more that is CFX's own.

**That the file is well formed**, read by CFX's punctuation -- `[$SECTION]` blocks of
`key = value` lines -- and the same reading run first against
`RADIOASTRON_RAES03FR_C_...cfx` and its K-band twin, which were written at the ASC by people
this project has never met.

**That the file says only what the model knows.** What is finished during correlation -- the
recorded data, the `TIMEOFS` figures that come out of the delay model, the clock offsets, the
correlator settings -- is present, commented out, and named in the report.

**That a space telescope is a station here.** That is the reason this format matters in this
lab: VEX 1.5 has nowhere to put an orbit, and CFX has `ORB_FILE`, which is a field this model
has carried since before either exporter existed.
"""
import pathlib
import re

import pytest

from pastrocore.formats import cfx
from pastrocore.super.schedule_manipulator import ScheduleManipulator

EXAMPLES = pathlib.Path("I:/format_examples")

#: What correlation fills in. Named here so the test says which keys it means; the writer's own
#: list is the one that decides what is written, and the report is made from it.
COMPLETED_LATER = ("FORMAT**", "FILE00", "TIMEOFS00", "POLY_FILE", "CLOCK DELAY", "CHANNELS")


# --- reading CFX by its punctuation ----------------------------------------------------------

SECTION = re.compile(r"^\[\$(\w+)\]$", re.I)
CLOSER = re.compile(r"^\[\$end\]$", re.I)


def parse(text):
    """Return `[(section, [(key, value), ...]), ...]`, comments dropped.

    Notes:
        - `#` starts a comment, and everything checked here is about lines that are *not*
          commented: a commented `IF` line is not a channel, which is precisely how the K-band
          example writes a receiver whose polarizations were swapped.
    """
    found, section, pairs = [], None, []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if CLOSER.match(stripped):
            if section is not None:
                found.append((section, pairs))
            section, pairs = None, []
            continue
        opening = SECTION.match(stripped)
        if opening:
            section, pairs = opening.group(1).upper(), []
            continue
        if section is not None and "=" in stripped:
            key, value = stripped.split("=", 1)
            pairs.append((key.strip(), value.strip()))
    return found


def sections_of(text, name):
    """Return every section of one kind."""
    return [pairs for section, pairs in parse(text) if section == name.upper()]


def values(pairs, key):
    """Return every value a section gives for one key."""
    return [value for name, value in pairs if name.lower() == key.lower()]


def example(name):
    """Return one of the real files, or skip: they calibrate the checker, they are not it."""
    path = EXAMPLES / name
    if not path.exists():
        pytest.skip(f"{path} is not here; the real files calibrate the checker")
    return path.read_text(encoding="utf-8", errors="replace")


# --- a schedule to write ---------------------------------------------------------------------

@pytest.fixture
def orbiting(project):
    """The fixture project with a spacecraft on its scan, and a band of four channels.

    Notes:
        - Built to resemble the example experiment: a space telescope with an orbit file, two
          ground stations, one band at 4828 MHz recording both sidebands in both circular
          polarizations.
    """
    core = ScheduleManipulator(project)
    observation = project.observations()[0]

    telescopes = observation.get_telescopes()
    core.configure(telescopes, create_space_telescope={"code": "RA", "use_kep": False,
                                                       "orbit_file": "RA121118_1100_v02.scf"})
    band = observation.get_frequencies().get_items()[0]
    core.configure(observation.get_frequencies(),
                   set_if={"name": band.name, "frequency": 4828.0, "bandwidth": 16.0,
                           "sidebands": ["U", "L"], "polarizations": ["RCP", "LCP"]})
    scan = observation.get_scans().get_items()[0]
    core.configure(scan, set_telescopes={"telescopes": list(telescopes.get_items()),
                                         "observation": observation})
    return core, observation


@pytest.fixture
def written(orbiting):
    """The one file the fixture observation produces, with its report."""
    _core, observation = orbiting
    files = cfx.write_cfx(observation)

    assert len(files) == 1, "the fixture observation uses one band and should write one file"
    _mode, text, report = files[0]
    return text, report


# --- the checker, calibrated ------------------------------------------------------------------

@pytest.mark.parametrize("name", ["RADIOASTRON_RAES03FR_C_20121118T135000_ASC_V2.cfx",
                                  "RADIOASTRON_RAES03FR_K_20121118T135000_ASC_V2.cfx"])
def test_the_checker_reads_a_file_written_at_the_asc(name):
    """Run first, and on purpose. A checker written beside the writer it checks proves nothing;
    one that also reads two files from the correlator is reading the format."""
    text = example(name)

    stations = sections_of(text, "TLSC")
    assert len(stations) == 4, f"expected four stations, read {len(stations)}"
    assert sections_of(text, "SOURCE"), "no source was read from a file that has one"
    assert len(sections_of(text, "skan")) == 4, "four scans were not read"

    spacecraft = [pairs for pairs in stations if values(pairs, "ORB_FILE")]
    assert len(spacecraft) == 1, "the one station with an orbit file was not found"
    assert not values(spacecraft[0], "TLSC_PAR"), "a spacecraft has no fixed position"


def test_the_file_carries_every_section_the_example_does(written):
    """Structure per the format, not per what we happen to be able to fill in."""
    text, _ = written
    ours = {section for section, _ in parse(text)}
    theirs = {section for section, _ in parse(
        example("RADIOASTRON_RAES03FR_C_20121118T135000_ASC_V2.cfx"))}

    assert not theirs - ours, f"sections the real file has and ours does not: {theirs - ours}"


# --- what it says -------------------------------------------------------------------------------

def test_a_space_telescope_is_a_station_with_an_orbit_file(written):
    """The reason this format is worth having here. VEX 1.5 excludes a spacecraft; CFX names it
    and points at its orbit, which is what this model has carried all along."""
    text, report = written
    spacecraft = [pairs for pairs in sections_of(text, "TLSC") if values(pairs, "ORB_FILE")]

    assert report["spacecraft"] == ["RA"]
    assert len(spacecraft) == 1
    assert values(spacecraft[0], "ORB_FILE") == ["RA121118_1100_v02.scf"]
    assert not values(spacecraft[0], "TLSC_PAR"), "a spacecraft was given a fixed position"


def test_a_band_with_both_sidebands_is_four_IF_lines(written):
    """One receiver setting, four channels -- the same claim the VEX writer makes with
    `chan_def`, in CFX's flattened spelling."""
    text, report = written

    for pairs in sections_of(text, "TLSC"):
        lines = values(pairs, "IF")
        assert len(lines) == 4, f"expected four channels, wrote {lines}"
        assert sum(line.endswith(", U") for line in lines) == 2
        assert sum(line.endswith(", L") for line in lines) == 2
    assert report["channels"] == 4


def test_the_output_section_names_the_recorded_sub_bands(written):
    """The example lists `IF = 4812.00` and `IF = 4828.00` for one band at 4828 MHz with both
    sidebands: the two 16 MHz halves it covers. Asked of the model one sideband at a time, so
    this is not a second place deciding which way a sideband runs."""
    text, _ = written
    output = sections_of(text, "OUTPAR")[0]

    assert values(output, "IF") == ["4812.00", "4828.00"]


def test_a_ground_station_states_its_position_and_leaves_the_rest_blank(written):
    """`TLSC_PAR` is positional, so a field this model does not carry is blank rather than
    zero: an axis offset of zero and an epoch of zero are claims, and wrong ones."""
    text, _ = written
    ground = [pairs for pairs in sections_of(text, "TLSC") if values(pairs, "TLSC_PAR")]

    assert ground, "no ground station wrote a position"
    for pairs in ground:
        fields = [field.strip() for field in values(pairs, "TLSC_PAR")[0].split(",")]
        assert len(fields) == 9, f"TLSC_PAR takes nine fields, wrote {len(fields)}"
        assert all(fields[:3]), "the position is the part we know and it must be written"
        assert fields[6] == "" and fields[7] == "", "an axis offset and an epoch were invented"
        assert fields[8] in ("AZEL", "EQUA")


def test_what_correlation_completes_is_shown_and_not_claimed(written):
    """Absent is not the same as missing. `TIMEOFS` comes out of the delay model and `FILE00`
    from the recording, so both are shown in place rather than left for somebody to remember --
    and neither is written as a value."""
    text, report = written
    stated = {key for _section, pairs in parse(text) for key, _value in pairs}

    for key in COMPLETED_LATER:
        assert key in text, f"{key} is not shown anywhere in the file"
        assert key not in stated, f"{key} was written as a value"

    needs = " ".join(entry["needs"] for entry in report["to_complete"])
    assert "delay model" in needs or "after observing" in needs
    assert "correlation" in needs


def test_a_commented_line_is_not_read_as_a_channel(written):
    """The K-band example comments out four `IF` lines for a receiver whose polarizations were
    swapped. A checker that counted them would be reading the file wrong, and so would
    anything else that read the file that way."""
    text, _ = written
    commented = text.replace("\tIF = 4828.00, R, U", "#\tIF = 4828.00, R, U")

    for pairs in sections_of(commented, "TLSC"):
        assert len(values(pairs, "IF")) == 3


def test_the_scan_line_carries_the_stations_by_code(written):
    """`telescopes = RA, Wb, Sv, Bd` in the example: the short names, which are what every
    other section keys on."""
    text, report = written
    scan = sections_of(text, "skan")[0]

    named = [code.strip() for code in values(scan, "telescopes")[0].split(",")]
    assert set(named) == set(report["stations"])
    assert "RA" in named, "the spacecraft is on the scan and belongs on its line"


def test_the_same_observation_writes_the_same_bytes(orbiting):
    """Everything else here rests on it: a dictionary iterated in whatever order it happens to
    have would pass every other test in this file."""
    _core, observation = orbiting

    first = cfx.write_cfx(observation)[0][1]
    second = cfx.write_cfx(observation)[0][1]

    assert first == second


def test_a_second_frequency_setup_is_a_second_file(orbiting):
    """A CFX file is a band: the two examples are one experiment in C and in K, as two files.
    Scans using two setups therefore write two."""
    core, observation = orbiting
    frequencies = observation.get_frequencies()
    core.configure(frequencies, create_if={"name": "K", "frequency": 22228.0, "bandwidth": 16.0,
                                           "polarizations": ["RCP"], "sidebands": ["U"]})

    scans = observation.get_scans()
    first = scans.get_items()[0]
    core.configure(scans, set_scan={"name": first.name,
                                    "frequencies": [frequencies.get("K")],
                                    "observation": observation})

    files = cfx.write_cfx(observation)

    assert len(files) == 1, "one scan uses one setup, so one file"
    assert files[0][2]["channels"] == 1, "the file describes the setup that scan uses"


@pytest.fixture(params=["RADIOASTRON_RAES03FR_C_20121118T135000_ASC_V2.cfx",
                        "RADIOASTRON_RAES03FR_K_20121118T135000_ASC_V2.cfx"])
def example_file(request):
    """Each real CFX file in turn, C band and K band of the same experiment."""
    return request.param


# --- reading one back (V5, V6) ------------------------------------------------------------

def imported(path, project=None):
    """Read one of the real files into a project, through the orchestrator."""
    from pastrocore.super.schedule_manipulator import ScheduleManipulator
    from pastrocore.super.schedule_project import ScheduleProject

    if not (EXAMPLES / path).exists():
        pytest.skip(f"{path} is not here")
    project = project or ScheduleProject(name="Imported")
    core = ScheduleManipulator(project)
    operation = "cfx" if path.lower().endswith(".cfx") else "vex"
    report = getattr(core, operation)(obj=project, method="import",
                                      path=str(EXAMPLES / path))
    return project, report


def test_a_real_file_this_lab_did_not_schedule_loads(example_file):
    """V5's exit criterion. The file was written by somebody else, for an experiment nobody
    here scheduled, and what comes back is an observation like any other."""
    project, report = imported(example_file)
    observation = project.observations()[0]

    assert report["scans"] > 0
    assert len(report["stations"]) > 1, "an interferometer needs more than one station"
    assert observation.get_sources().get_items(), "no source came back"
    assert observation.get_frequencies().get_items(), "no band came back"
    assert observation.get_scans().get_items(), "no scan came back"


def test_what_was_read_can_be_analysed(example_file):
    """The rest of V5's criterion: it is not enough for it to load. `analyze` reads results, so
    what is checked here is that a calculation runs over it and produces rows."""
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    project, _ = imported(example_file)
    core = ScheduleManipulator(project)
    observation = project.observations()[0]

    core.compute(obj=observation, method="run", calculations=["az_el"], time_step=600.0,
                 recalculate=True, raise_on_error=False)
    described = core.analyze(obj=observation, method="describe", key="az_el",
                             raise_on_error=False)

    assert described.ok, described.error
    assert described.value, "nothing to analyse came out of an imported schedule"


def test_what_the_model_cannot_hold_is_named_rather_than_carried(example_file):
    """V6, decided and then tested. The hardware and the session belong to the station and the
    correlator: an export leaves those blocks empty for them to fill, so importing them would
    be keeping something nothing here can use or check. What was passed over is *named*, so a
    round trip is never mistaken for a lossless one."""
    _project, report = imported(example_file)

    assert report["passed_over"], "a real file always says more than this model holds"
    for name in report["passed_over"]:
        assert isinstance(name, str) and name


def test_a_scan_the_model_refuses_is_named_rather_than_forced_in(example_file):
    """Whatever the model will not take is reported instead of being bent to fit. Nothing in
    these two files is refused any more -- the rule that used to throw half of `re03fr.vex`
    away was the one about overlapping scans, and it was wrong."""
    _project, report = imported(example_file)

    assert report["refused"] == [], f"scans were refused: {report['refused']}"
