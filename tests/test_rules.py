"""Rules about a whole object, which no rule about one field can express.

Three of them were helpers called by hand -- `_check_overlap` on `Frequencies`, `_check_overlap`
on `Scans`, `_validate_item` on `ScheduleProject` -- so each held exactly where somebody had
remembered to call it, and each had paths where nobody had. msb_arch 1.10.0 gave them somewhere
to live: a rule declared with `@invariant` is checked when the object is built, when it is
restored, and after anything that changes what it holds, and a refused change is undone.

What is tested here is therefore the same rule on every path, and that a refusal leaves the
object as it was. The paths that were never checked before are marked.
"""
import json
import pathlib

import pytest
from astropy.time import Time
from msb_arch import InvariantError

from pastrocore.base.frequencies import Frequencies, IF
from pastrocore.base.observation import Observation
from pastrocore.base.scans import Scan, Scans
from pastrocore.base.sources import Source
from pastrocore.super.schedule_project import ScheduleProject

import conftest


def a_scan(name, start, duration=600.0, isactive=True):
    return Scan(name=name, start=Time(start, format="iso"), duration=duration, isactive=isactive)


#: A source to point somewhere else at, for the rule that says one antenna cannot do both.
SOMEWHERE_ELSE = Source(name="OTHER", ra_h=1.0, de_d=10.0)


def pointed(name, start, duration=600.0, isactive=True, stations=("Sv",), source="HERE"):
    """A scan with stations and a target, which is what the pointing rule is about."""
    from pastrocore.base.telescopes import Telescopes

    held = Telescopes()
    for code in stations:
        held.create_telescope(code=code)
    return Scan(name=name, start=Time(start, format="iso"), duration=duration,
                isactive=isactive, telescopes=list(held.get_items()),
                source=Source(name=source, ra_h=1.0, de_d=10.0))



# --- frequency bands ---------------------------------------------------------------------

def test_bands_that_touch_are_not_overlapping():
    """1000-1016 and 1016-1032 share an edge and no width. Refusing these would refuse the
    ordinary case of a contiguous set of bands."""
    frequencies = Frequencies(name="fq")
    frequencies.create_if(name="a", frequency=1000.0, bandwidth=16.0)
    frequencies.create_if(name="b", frequency=1016.0, bandwidth=16.0)

    assert [item.name for item in frequencies.get_items()] == ["a", "b"]


@pytest.mark.parametrize("path", ["add", "set_if", "set_item", "set_items", "build"])
def test_overlapping_bands_are_refused_on_every_path(path):
    """`set_item`, `set_items` and the constructor were the three nobody checked."""
    frequencies = Frequencies(name="fq")
    frequencies.create_if(name="a", frequency=1000.0, bandwidth=16.0)
    frequencies.create_if(name="b", frequency=1016.0, bandwidth=16.0)

    attempts = {
        "add": lambda: frequencies.create_if(name="c", frequency=1010.0, bandwidth=16.0),
        "set_if": lambda: frequencies.set_if("a", frequency=1010.0),
        "set_item": lambda: frequencies.set_item(
            "a", IF(name="a", frequency=1020.0, bandwidth=16.0)),
        "set_items": lambda: frequencies.set_items(
            {"x": IF(name="x", frequency=1.0, bandwidth=10.0),
             "y": IF(name="y", frequency=5.0, bandwidth=10.0)}),
        "build": lambda: Frequencies(name="bad", items={
            "p": IF(name="p", frequency=1.0, bandwidth=10.0),
            "q": IF(name="q", frequency=5.0, bandwidth=10.0)}),
    }

    with pytest.raises(InvariantError):
        attempts[path]()


def test_a_refused_band_leaves_the_bands_as_they_were():
    """A rule that refuses half a change is worse than one that does not refuse at all."""
    frequencies = Frequencies(name="fq")
    frequencies.create_if(name="a", frequency=1000.0, bandwidth=16.0)
    frequencies.create_if(name="b", frequency=1016.0, bandwidth=16.0)

    with pytest.raises(InvariantError):
        frequencies.set_if("a", frequency=1010.0)

    held = {item.name: (item.frequency, item.bandwidth) for item in frequencies.get_items()}
    assert held == {"a": (1000.0, 16.0), "b": (1016.0, 16.0)}


def test_the_refusal_names_both_bands():
    """"frequency ranges must not overlap" is true and leaves the user to find which two."""
    frequencies = Frequencies(name="fq")
    frequencies.create_if(name="a", frequency=1000.0, bandwidth=16.0)

    with pytest.raises(InvariantError) as refused:
        frequencies.create_if(name="c", frequency=1010.0, bandwidth=16.0)

    assert "'a'" in str(refused.value) and "'c'" in str(refused.value)


# --- polarizations -------------------------------------------------------------------------

@pytest.mark.parametrize("path", ["build", "set", "set_if", "from_dict"])
def test_mixed_polarizations_are_refused_on_every_path(path):
    """A band is recorded circular or linear, never in a mixture -- which is a fact about a
    receiver, not a preference.

    It was checked in `_validate_polarizations`, which runs from `__init__` and nowhere else,
    so `set` accepted `["RCP", "H"]` and so did a saved project carrying one back. The same
    shape as the coordinate range and the scan duration before it.
    """
    mixed = ["RCP", "H"]
    frequencies = Frequencies(name="fq")
    frequencies.create_if(name="a", frequency=1000.0, bandwidth=16.0, polarizations=["RCP"])

    attempts = {
        "build": lambda: IF(name="bad", frequency=1.0, bandwidth=1.0, polarizations=mixed),
        "set": lambda: frequencies.get("a").set({"polarizations": mixed}),
        "set_if": lambda: frequencies.set_if("a", polarizations=mixed),
        "from_dict": lambda: IF.from_dict({
            "name": "bad", "frequency": 1.0, "bandwidth": 1.0, "polarizations": mixed,
            "sidebands": ["U"], "isactive": True}),
    }

    with pytest.raises((InvariantError, ValueError)):
        attempts[path]()


def test_a_band_with_no_polarization_is_not_a_mixture():
    """Nothing entered means nothing was said, and the exporter writes it as "not stated".
    Refusing it would refuse every band in every project written before the field mattered."""
    band = IF(name="quiet", frequency=1000.0, bandwidth=16.0, polarizations=[])

    assert band.polarizations == []
    assert band.get_channel_count() == 1


def test_a_refused_polarization_leaves_the_band_as_it_was():
    """A rule that refuses half a change is worse than one that does not refuse at all."""
    frequencies = Frequencies(name="fq")
    frequencies.create_if(name="a", frequency=1000.0, bandwidth=16.0,
                          polarizations=["RCP", "LCP"])

    with pytest.raises((InvariantError, ValueError)):
        frequencies.set_if("a", polarizations=["RCP", "V"])

    assert frequencies.get("a").polarizations == ["RCP", "LCP"]


# --- what a band covers ---------------------------------------------------------------------

def test_the_span_is_asked_of_the_model_rather_than_worked_out():
    """`band_of` takes loose values so that an editor can show what the fields on screen would
    cover before anything is saved. It has to agree with the band's own answer, or there are
    two rules about which way a sideband runs."""
    band = IF(name="a", frequency=4828.0, bandwidth=16.0, sidebands=["U", "L"])

    assert IF.band_of(4828.0, 16.0, ["U", "L"]) == band.get_band() == (4812.0, 4844.0)
    assert IF.band_of(4828.0, 16.0, ["U"]) == (4828.0, 4844.0)
    assert IF.band_of(4844.0, 16.0, ["L"]) == (4828.0, 4844.0)


def test_the_same_spectrum_written_two_ways_is_still_refused():
    """4828 upper and 4844 lower are one 16 MHz band. This is the confusion the sideband field
    exists for, and the overlap rule is what catches it."""
    frequencies = Frequencies(name="fq")
    frequencies.create_if(name="a", frequency=4828.0, bandwidth=16.0, sidebands=["U"])

    with pytest.raises(InvariantError):
        frequencies.create_if(name="c", frequency=4844.0, bandwidth=16.0, sidebands=["L"])


# --- scan times --------------------------------------------------------------------------

def test_scans_that_abut_are_not_overlapping():
    """One scan ending as the next begins is a schedule, not a conflict."""
    scans = Scans(name="sc")
    scans.add(pointed("a", "2026-01-01 10:00:00"))
    scans.add(pointed("b", "2026-01-01 10:10:00"))

    assert [item.name for item in scans.get_items()] == ["a", "b"]


@pytest.mark.parametrize("path", ["add", "set_scan", "set_item", "build"])
def test_one_antenna_may_not_be_pointed_at_two_sources_at_once(path):
    """`set_item` and the constructor were unchecked, and a saved schedule arrives through the
    constructor -- which is exactly where a conflicting pair would come from."""
    scans = Scans(name="sc")
    scans.add(pointed("a", "2026-01-01 10:00:00"))
    scans.add(pointed("b", "2026-01-01 10:10:00"))

    attempts = {
        "add": lambda: scans.add(pointed("c", "2026-01-01 10:05:00", source="OTHER")),
        "set_scan": lambda: scans.set_scan(
            "a", start=Time("2026-01-01 10:15:00", format="iso"), source=SOMEWHERE_ELSE),
        "set_item": lambda: scans.set_item(
            "a", pointed("a", "2026-01-01 10:12:00", source="OTHER")),
        "build": lambda: Scans(name="bad", items={
            "p": pointed("p", "2026-01-01 09:00:00", 3600.0),
            "q": pointed("q", "2026-01-01 09:30:00", 3600.0, source="OTHER")}),
    }

    with pytest.raises(InvariantError):
        attempts[path]()


def test_two_sub_arrays_may_observe_one_source_at_once():
    """`re03fr.vex` does exactly this: 2230+114 from 13:50 with Wb, Sv and Bd at 4828 MHz and
    with Ev, Nt and Zc at 22228 MHz. It is an ordinary way to run an array and the basis of
    multi-frequency synthesis, and the rule that refused any overlap threw half of a real
    experiment away when it was imported."""
    scans = Scans(name="sc")
    scans.add(pointed("c_band", "2026-01-01 10:00:00", stations=("Wb", "Sv")))
    scans.add(pointed("k_band", "2026-01-01 10:00:00", stations=("Ev", "Nt")))

    assert len(scans.get_items()) == 2


def test_one_antenna_may_record_two_bands_at_once():
    """A dual-band receiver is two scans of one source sharing a station, at the same moment.
    Nothing about one mount forbids it: it is pointed one way and recording twice."""
    scans = Scans(name="sc")
    scans.add(pointed("lower", "2026-01-01 10:00:00", stations=("Sv",)))
    scans.add(pointed("upper", "2026-01-01 10:00:00", stations=("Sv",)))

    assert len(scans.get_items()) == 2


def test_inactive_scans_may_cover_the_same_hour():
    """An inactive scan is an alternative being kept, not a commitment. Refusing these would
    make it impossible to hold two candidates for one slot, which is how a schedule is planned."""
    scans = Scans(name="sc")
    scans.add(pointed("a", "2026-01-01 10:00:00"))
    scans.add(pointed("shadow", "2026-01-01 10:05:00", source="OTHER", isactive=False))

    assert len(scans.get_items()) == 2


def test_a_refused_scan_leaves_the_scan_as_it_was():
    scans = Scans(name="sc")
    scans.add(pointed("a", "2026-01-01 10:00:00"))
    scans.add(pointed("b", "2026-01-01 10:10:00"))

    with pytest.raises(InvariantError):
        scans.set_scan("a", start=Time("2026-01-01 10:15:00", format="iso"),
                       source=SOMEWHERE_ELSE)

    assert scans.get("a").get_start().isot.startswith("2026-01-01T10:00:00")


# --- observation codes -------------------------------------------------------------------

@pytest.mark.parametrize("path", ["add_item", "create_item", "set_item", "build"])
def test_two_observations_may_not_share_a_code(path):
    """`_validate_item` took a pair of exclusions at each call site to work out which item was
    being replaced. The rule reads the project as it would be, so there is nothing to exclude."""
    project = ScheduleProject(name="P")
    project.create_item(item_code="OBS1")
    project.create_item(item_code="OBS2")
    first = project.observations()[0]

    attempts = {
        "add_item": lambda: project.add_item(Observation(name="x", code="OBS1")),
        "create_item": lambda: project.create_item(item_code="OBS2"),
        "set_item": lambda: project.set_item(first.name,
                                             Observation(name=first.name, code="OBS2")),
        "build": lambda: ScheduleProject(name="D", items={
            "a": Observation(name="a", code="SAME"),
            "b": Observation(name="b", code="SAME")}),
    }

    with pytest.raises(InvariantError):
        attempts[path]()

    assert sorted(item.code for item in project.observations()) == ["OBS1", "OBS2"]


def test_a_code_may_still_be_changed_to_a_free_one():
    """The rule must refuse a collision, not a rename."""
    project = ScheduleProject(name="P")
    project.create_item(item_code="OBS1")
    project.create_item(item_code="OBS2")

    project.observations()[0].code = "OBS9"

    assert sorted(item.code for item in project.observations()) == ["OBS2", "OBS9"]


# --- what 2.0.0 promised about a project -------------------------------------------------

def test_a_project_equals_what_was_written_from_it():
    """msb_arch 2.0.0 made a `Project` compare by its contents so `load(...) == project` holds.
    It did not, here: `CalculatedData` had no `__eq__`, so every observation compared by
    identity and no restored project ever equalled the one it came from."""
    data = json.loads(conftest.FIXTURE.read_text(encoding="utf-8"))
    project = ScheduleProject.from_dict(data)

    assert ScheduleProject.from_dict(project.to_dict()) == project


def test_two_different_projects_are_not_equal():
    """The other half: an equality that is always True says nothing."""
    data = json.loads(conftest.FIXTURE.read_text(encoding="utf-8"))
    project = ScheduleProject.from_dict(data)

    assert project != ScheduleProject(name="Empty")


# --- importing a telescope that is already here ------------------------------------------

def test_importing_a_telescope_that_is_already_here_adds_a_second_one(tmp_path):
    """A telescope's name and its code are each unique within an observation, and a file
    written from one carries both -- so importing it back, or importing the same station from a
    colleague's project, was refused outright.

    The tab had two lines meant to handle this: `telescope.code = telescope.code` and
    `telescope.name = telescope.name`. Both do nothing, so nothing is what happened.
    """
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    data = json.loads(conftest.FIXTURE.read_text(encoding="utf-8"))
    project = ScheduleProject.from_dict(data)
    manipulator = ScheduleManipulator(project)
    telescopes = project.observations()[0].get_telescopes()

    written = tmp_path / "telescope.pastrod"
    manipulator.save(obj=telescopes.get_items()[0], path=str(written))
    before = [t.name for t in telescopes.get_items()]

    manipulator.configure(telescopes, add_as_new=manipulator.load(telescopes, path=str(written)))
    manipulator.configure(telescopes, add_as_new=manipulator.load(telescopes, path=str(written)))

    names = [t.name for t in telescopes.get_items()]
    codes = [t.get_code() for t in telescopes.get_items()]
    assert names[:len(before)] == before, "the telescopes already here were disturbed"
    assert len(names) == len(before) + 2
    assert len(set(names)) == len(names) and len(set(codes)) == len(codes)
    assert names[-2:] == ["EHT_ALMA_2", "EHT_ALMA_3"], (
        "a number says which station it is; a UUID would not")


def test_a_telescope_with_a_free_name_keeps_it(tmp_path):
    """The suffix is for a collision, not for every import."""
    from pastrocore.base.telescopes import Telescope, Telescopes

    telescopes = Telescopes(name="tels")
    telescopes.create_telescope(code="EF", name="Effelsberg", x=1.0, y=2.0, z=3.0, diameter=100.0)

    held = [t.name for t in telescopes.get_items()]
    telescopes.add_as_new(Telescope(code="ON", name="Onsala", x=4.0, y=5.0, z=6.0, diameter=25.0))

    assert [t.name for t in telescopes.get_items()] == held + ["Onsala"], (
        "a name nothing was using was changed anyway")
