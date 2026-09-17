"""A generation plan: how long it takes, what it saves, and what it is asked (O1).

The generator worked out how long a pattern takes in order to place its scans, and the dialog worked
the same formula out again to show an end time -- with a third copy inverting it for "what scan
duration fits this end". A preset saved the timing and dropped what it was for, so loading one left
a pattern pointed at nothing.

The plan is one object now. What matters here is that its arithmetic is the generator's own -- so
the last scan of a generated observation ends exactly where the plan says it does -- and that a plan
written to a file comes back whole.
"""
import copy
import json
from datetime import datetime

import pytest

from pastrocore.base.generation_plan import GenerationPlan, presets
from pastrocore.super.schedule_manipulator import ScheduleManipulator


@pytest.fixture
def collections(project):
    """The fixture's sources, stations and bands, which a plan needs to be about something."""
    observation = project.get_observations()[0]
    return (observation.get_sources(), observation.get_telescopes(), observation.get_frequencies())


def a_plan(collections, **changes):
    sources, telescopes, frequencies = collections
    settings = dict(start=datetime(2026, 1, 1), scan_duration=300.0, num_scans=4, interval_sec=60.0,
                    add_off_source=False, parallel=True, sources=sources, telescopes=telescopes,
                    frequencies=frequencies)
    settings.update(changes)
    return GenerationPlan(**settings)


# --- how long a pattern takes ---------------------------------------------------------------------

def test_the_interval_falls_between_scans_and_not_after_the_last(collections):
    """Four scans carry three gaps. A gap after the last one is time the observation does not use."""
    plan = a_plan(collections)
    assert plan.span_per_observation() == 4 * 300.0 + 3 * 60.0


def test_an_off_source_scan_doubles_the_time_on_each(collections):
    plan = a_plan(collections, add_off_source=True)
    assert plan.span_per_observation() == 4 * 600.0 + 3 * 60.0


def test_observations_that_follow_one_another_take_as_long_as_all_of_them(collections):
    one = a_plan(collections, parallel=True).span()
    several = a_plan(collections, parallel=False).span()
    assert several == one * len(collections[0].get_items())


def test_the_scan_duration_that_fits_an_end_is_the_inverse_of_the_span(collections):
    for parallel in (True, False):
        for off_source in (True, False):
            plan = a_plan(collections, parallel=parallel, add_off_source=off_source)
            assert plan.scan_duration_for(plan.span()) == pytest.approx(plan.scan_duration)


def test_a_pattern_that_does_not_fit_is_no_duration_at_all(collections):
    """Asked to fit in less time than its gaps alone take, a plan says so rather than proposing a
    scan of nothing -- or, as the arithmetic in the dialog did, of a negative length."""
    plan = a_plan(collections, num_scans=10, interval_sec=600.0)
    assert plan.scan_duration_for(60.0) == 0.0


# --- the generator and the plan agree ---------------------------------------------------------------

def test_the_last_scan_ends_where_the_plan_says_the_observation_does(project, collections):
    """The check that matters: the generator places the scans, and the plan says when it all ends.
    Two formulas for one thing is what this replaces."""
    import astropy.units as u
    from astropy.time import Time

    plan = a_plan(collections, parallel=True, add_off_source=True, num_scans=3)
    core = ScheduleManipulator(project)
    before = {observation.get_observation_code() for observation in project.get_observations()}

    answer = core.configure(obj=project, generate_observations=dict(plan.attributes(), cancelled=False))
    assert answer["status"], answer.get("error")

    made = [observation for observation in project.get_observations()
            if observation.get_observation_code() not in before]
    assert made, "nothing was generated to check"
    for observation in made:
        scans = observation.get_scans().get_items()
        last = max(scans, key=lambda scan: scan.get_start())
        ends = Time(last.get_start(), format="mjd") + last.get_duration() * u.s
        expected = Time(plan.start.isoformat(sep=" "), format="iso") + plan.span_per_observation() * u.s
        assert abs((ends - expected).to_value("s")) < 1e-6, observation.get_observation_code()


# --- a plan is a file --------------------------------------------------------------------------------

def test_a_plan_carries_what_it_is_for(collections):
    """A preset used to save the timing alone: sources, stations and bands were dropped, and loading
    one left the dialog with a pattern and nothing to point it at."""
    plan = a_plan(collections)
    written = plan.to_dict()

    assert written["sources"]["items"], "a plan with no sources is a pattern, not a plan"
    read = GenerationPlan.from_dict(copy.deepcopy(written))
    assert read.to_dict() == written
    assert [source.name for source in read.sources.get_items()] == \
           [source.name for source in plan.sources.get_items()]


def test_a_plan_written_by_an_older_version_still_reads(collections):
    """Fewer keys than there are now: what is missing takes its default rather than refusing."""
    plan = GenerationPlan.from_dict({"scan_duration": 120.0, "num_scans": 7})
    assert plan.scan_duration == 120.0 and plan.num_scans == 7
    assert plan.observation_type == "VLBI" and plan.start is None
    assert plan.end() is None, "a plan that does not say when it starts cannot say when it ends"


def test_a_plan_goes_to_a_file_and_comes_back(project, collections, tmp_path):
    core = ScheduleManipulator(project)
    plan = a_plan(collections, num_scans=9, naming_mask="{i}_{s}")
    path = tmp_path / "plan.json"

    # Sent as a window sends it, with the collections themselves rather than their data.
    written = core.export(obj=project, method="generation_plan", path=str(path),
                          plan=plan.as_mapping())
    assert written["path"] == str(path)
    assert json.loads(path.read_text(encoding="utf-8"))["num_scans"] == 9

    # Read back as the window is given it: the fields, holding the collections themselves.
    read = core.load(obj=project, method="generation_plan", path=str(path))
    assert read["num_scans"] == 9 and read["naming_mask"] == "{i}_{s}"
    assert list(read["sources"].get_all()) == list(plan.sources.get_all())
    assert GenerationPlan.of(read).to_dict() == plan.to_dict()


def test_a_plan_is_read_from_whatever_shape_it_arrives_in(collections):
    """A window hands over the collections it is showing; a file holds their data. The backend takes
    both, which is what keeps the conversion out of the interface."""
    plan = a_plan(collections)

    from_window = GenerationPlan.of(plan.as_mapping())
    from_file = GenerationPlan.of(plan.to_dict())

    assert from_window.to_dict() == from_file.to_dict() == plan.to_dict()
    assert from_window.start == plan.start, "a datetime from a window did not survive"


def test_the_generator_takes_a_plan_as_a_request(project, collections):
    """`generate_observations={"plan": ...}` is the whole ask: the window sends what it is showing
    rather than assembling the generator's attributes itself."""
    core = ScheduleManipulator(project)
    plan = a_plan(collections, num_scans=2)
    before = len(project.get_observations())

    answer = core.configure(obj=project,
                            generate_observations={"plan": plan.as_mapping(), "cancelled": False})

    assert answer["status"], answer.get("error")
    assert len(project.get_observations()) == before + len(plan.sources.get_all())


def test_a_cancel_still_reaches_a_generation_asked_for_as_a_plan(project, collections):
    """The caller sets `cancelled` on the dictionary it handed over while the work runs, so
    expanding the plan must not replace that dictionary with a copy."""
    core = ScheduleManipulator(project)
    attributes = {"plan": a_plan(collections).as_mapping(), "cancelled": False}
    attributes["cancelled"] = True

    answer = core.configure(obj=project, generate_observations=attributes)

    assert answer.get("cancelled") is True, "the cancel was not seen"


# --- what the project is asked ------------------------------------------------------------------------

def test_the_presets_are_the_backend_s_to_offer(project):
    """The dialog listed two patterns of its own; they are the model's now, like every other list the
    interface shows."""
    core = ScheduleManipulator(project)
    offered = core.inspect(obj=project, get_generation_presets=None)

    assert offered == presets()
    assert [entry["name"] for entry in offered], "no presets offered at all"
    for entry in offered:
        plan = GenerationPlan.from_dict(entry["plan"])
        assert plan.num_scans > 0 and plan.scan_duration > 0, entry["name"]
        assert not plan.sources.get_all(), f"{entry['name']} says what to observe, and should not"


def test_the_project_says_how_long_a_plan_takes_and_when_it_ends(project, collections):
    core = ScheduleManipulator(project)
    plan = a_plan(collections, parallel=False)

    span = core.inspect(obj=project, get_generation_span={"plan": plan.to_dict()})
    assert span["per_observation"] == plan.span_per_observation()
    assert span["total"] == plan.span()
    assert span["end"] == plan.end().strftime("%Y-%m-%d %H:%M:%S")


def test_the_project_says_which_scan_duration_fits_a_given_end(project, collections):
    core = ScheduleManipulator(project)
    plan = a_plan(collections)

    fitted = core.inspect(obj=project, get_generation_scan_duration={"plan": plan.to_dict(),
                                                                     "seconds": plan.span()})
    assert fitted == pytest.approx(plan.scan_duration)
