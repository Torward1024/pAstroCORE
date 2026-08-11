"""A result must not pass for current when the configuration has moved underneath it.

Measured before any of this existed: moving a telescope 1 000 km and recalculating returned the
previous numbers, unchanged and without a word.

The tests below check three things that are easy to get individually right and jointly wrong:
that a real change is noticed, that an *unrelated* change is not, and that a result which
predates the mechanism is reported as unknown rather than guessed at either way.
"""
import json

import polars as pl
import pytest

import conftest
from pastrocore.base import freshness
from pastrocore.base.data_structure import CalculatedDataStructure
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject


@pytest.fixture
def computed(project):
    """The fixture project with one calculation freshly made, so it carries a fingerprint."""
    observation = project.get_observation(next(iter(project.get_items())))
    observation.calculated_data.clear()
    ScheduleManipulator(project).calculate(observation, method="uv_coverage", time_step=300.0,
                                           raise_on_error=False)
    return project, observation


def test_moving_a_telescope_makes_the_result_stale(computed):
    """The measurement that started this: a thousand kilometres, silently ignored."""
    _, observation = computed
    assert observation.is_result_stale("uv_coverage") is False

    telescope = observation.get_telescopes().get_active_items()[0]
    x = telescope.get_coordinates()[0]
    telescope.set({"x": x + 1_000_000.0})

    assert observation.is_result_stale("uv_coverage") is True
    assert "uv_coverage" in observation.stale_results()


def test_an_unrelated_change_leaves_it_alone(computed):
    """The half that decides whether this is useful or unbearable.

    A beam pattern does not read the scans. If editing a scan staled it, every edit would stale
    everything, and "everything" would be all there was left to recompute -- which is the
    objection to staleness detection, and it is an objection to doing it coarsely.
    """
    project, observation = computed
    ScheduleManipulator(project).calculate(observation, method="beam_pattern", time_step=300.0,
                                           raise_on_error=False)
    if observation.is_result_stale("beam_pattern") is None:
        pytest.skip("the fixture computed no beam pattern to check")

    assert observation.is_result_stale("beam_pattern") is False

    scan = observation.get_scans().get_active_items()[0]
    scan.set({"duration": scan.get("duration") + 600.0})

    assert observation.is_result_stale("beam_pattern") is False, (
        "a beam pattern does not read the scans and must not be staled by one")
    assert observation.is_result_stale("uv_coverage") is True, (
        "uv coverage does read the scans, so it must be")


def test_a_result_from_before_this_existed_is_unknown_rather_than_guessed(project):
    """Reporting "current" would be a claim; reporting "stale" would send a user to recompute
    everything they own the first time they open an old project."""
    observation = project.get_observation(next(iter(project.get_items())))

    # The fixture's results were saved long before results carried fingerprints.
    assert freshness.DIGEST_FIELD not in observation.get_calculated_metadata("uv_coverage")
    assert observation.is_result_stale("uv_coverage") is None
    assert observation.stale_results() == (), "unknown is not stale"


def test_staleness_survives_being_saved_and_reopened(computed, tmp_path):
    """It is worth nothing if it only holds within one session."""
    project, observation = computed
    root = tmp_path / "fresh.pastro"
    project.save(str(root))

    reopened = ScheduleProject.open(str(root))
    restored = reopened.get_observation(observation.name)
    assert restored.is_result_stale("uv_coverage") is False

    telescope = restored.get_telescopes().get_active_items()[0]
    telescope.set({"x": telescope.get_coordinates()[0] + 1_000_000.0})
    assert restored.is_result_stale("uv_coverage") is True


def test_asking_reads_no_results(computed, tmp_path):
    """A project asked about staleness must not be loaded into memory to answer."""
    project, observation = computed
    root = tmp_path / "cheap.pastro"
    project.save(str(root))

    reopened = ScheduleProject.open(str(root))
    restored = reopened.get_observation(observation.name)
    assert restored.calculated_data._resident == {}

    restored.stale_results()

    assert restored.calculated_data._resident == {}, (
        "asking whether results are stale must not read them")


def test_a_stale_result_is_still_readable(computed):
    """A state, not an event. Nothing raises, nothing blocks, and the numbers stay available --
    a user may well want to compare them against what they become."""
    _, observation = computed
    before = observation.calculated_data["uv_coverage"]["data"]

    telescope = observation.get_telescopes().get_active_items()[0]
    telescope.set({"x": telescope.get_coordinates()[0] + 1_000_000.0})

    assert observation.is_result_stale("uv_coverage") is True
    after = observation.calculated_data["uv_coverage"]["data"]
    assert after.equals(before), "a stale result must still be readable, unchanged"


def test_recalculating_makes_it_current_again(computed):
    _, observation = computed
    project = None

    telescope = observation.get_telescopes().get_active_items()[0]
    telescope.set({"x": telescope.get_coordinates()[0] + 1_000_000.0})
    assert observation.is_result_stale("uv_coverage") is True

    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    manipulator = ScheduleManipulator(conftest_project(observation))
    manipulator.calculate(observation, method="uv_coverage", time_step=300.0,
                          recalculate=True, raise_on_error=False)

    assert observation.is_result_stale("uv_coverage") is False


def conftest_project(observation):
    """Return a project holding just this observation, for a manipulator to work through."""
    project = ScheduleProject(name="Recalculating")
    project.add_item(observation)
    return project


def test_a_different_time_step_is_a_different_result(computed):
    """Parameters that change the answer count as inputs, even though they are not the model."""
    project, observation = computed
    assert observation.is_result_stale("uv_coverage") is False

    stored = dict(observation.get_calculated_metadata("uv_coverage"))
    assert freshness.digest(observation, "uv_coverage", stored) == stored[freshness.DIGEST_FIELD]

    different = dict(stored, time_step=600.0)
    assert freshness.digest(observation, "uv_coverage", different) != stored[freshness.DIGEST_FIELD]


# --- the ratchet ---------------------------------------------------------------------------

def test_every_result_declares_what_it_depends_on():
    """The declaration lives in the schema so it cannot be forgotten in a second file -- and
    this is what makes "cannot" true.

    A new calculation that skips it does not fail: it silently depends on everything, so it
    looks stale whenever anything at all is edited, which is exactly the coarseness this
    mechanism exists to avoid.
    """
    everything = ("telescopes", "sources", "scans", "frequencies")
    missing = [key for key, schema in CalculatedDataStructure.SCHEMAS.items()
               if "depends_on" not in schema]
    assert not missing, (
        f"{missing} declare no 'depends_on' in their schema, so they would be treated as "
        f"depending on {everything} and go stale on every edit")


def test_declared_dependencies_are_parts_that_exist():
    """A typo would read as "depends on nothing", which never goes stale at all."""
    known = set(freshness._ACCESSORS)
    for key, schema in CalculatedDataStructure.SCHEMAS.items():
        declared = set(schema.get("depends_on", ()))
        assert declared <= known, f"'{key}' declares unknown parts: {sorted(declared - known)}"


def test_something_that_depends_on_nothing_would_be_caught():
    """The test above is only worth having if it can fail."""
    known = set(freshness._ACCESSORS)
    assert not {"telescopes", "typo_here"} <= known


# --- projects that already exist ------------------------------------------------------------

def test_opening_an_old_project_records_a_baseline(project, tmp_path):
    """Without this the mechanism is invisible to every project that already exists.

    Answering "unknown" forever is honest and useless: a user changes a scan, nothing is
    reported, and staleness never once fires. Reported exactly that way -- telescopes and scan
    times changed, no label.
    """
    root = tmp_path / "old.pastro"
    project.save(str(root))

    # Strip the fingerprints, so the directory looks like one written before they existed.
    for sidecar in (root / "results").rglob("*.meta.json"):
        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        metadata.pop(freshness.DIGEST_FIELD, None)
        sidecar.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    reopened = ScheduleProject.open(str(root))
    observation = reopened.get_observation(next(iter(reopened.get_items())))

    assert observation.stale_results() == (), "opening alone must not accuse anything"
    assert observation.is_result_stale("uv_coverage") is False

    scan = observation.get_scans().get_active_items()[0]
    scan.set({"duration": scan.get("duration") + 600.0})

    assert "uv_coverage" in observation.stale_results(), (
        "a change after opening must be reported, which is the whole point")


def test_an_adopted_baseline_says_it_was_adopted(project, tmp_path):
    """It is not a claim that the results were current -- only a record of what the
    configuration was when the project was opened."""
    root = tmp_path / "adopted.pastro"
    project.save(str(root))
    for sidecar in (root / "results").rglob("*.meta.json"):
        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        metadata.pop(freshness.DIGEST_FIELD, None)
        sidecar.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    reopened = ScheduleProject.open(str(root))
    observation = reopened.get_observation(next(iter(reopened.get_items())))

    metadata = observation.get_calculated_metadata("uv_coverage")
    assert metadata[freshness.ADOPTED_FIELD] is True
    assert metadata.get(freshness.DIGEST_FIELD)


def test_adopting_reads_no_results(project, tmp_path):
    """Metadata only. Opening a project must not become a reason to load it."""
    root = tmp_path / "cheap_adopt.pastro"
    project.save(str(root))
    for sidecar in (root / "results").rglob("*.meta.json"):
        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        metadata.pop(freshness.DIGEST_FIELD, None)
        sidecar.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    reopened = ScheduleProject.open(str(root))
    observation = reopened.get_observation(next(iter(reopened.get_items())))
    assert observation.calculated_data._resident == {}


def test_a_real_calculation_keeps_its_own_fingerprint(computed, tmp_path):
    """Adoption must not overwrite a fingerprint taken when the result was calculated."""
    project, observation = computed
    taken = observation.get_calculated_metadata("uv_coverage")[freshness.DIGEST_FIELD]

    root = tmp_path / "kept.pastro"
    project.save(str(root))
    reopened = ScheduleProject.open(str(root))
    restored = reopened.get_observation(observation.name)

    metadata = restored.get_calculated_metadata("uv_coverage")
    assert metadata[freshness.DIGEST_FIELD] == taken
    assert freshness.ADOPTED_FIELD not in metadata
