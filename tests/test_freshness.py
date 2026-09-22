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
    observation = project.get_observations()[0]
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
    observation = project.get_observations()[0]

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


# --- a stored answer to another question -----------------------------------------------------

#: A value of each kind a parameter is declared as, and another one of the same kind. A
#: parameter is only ever one of these: the schema says so, and a test below checks that it does.
A_VALUE = {float: 1.0, int: 1, str: "one", list: [[1.0, 2.0, 0.1]], dict: {"AA": [[1.0, 2.0, [1.0]]]}}
ANOTHER = {float: 2.0, int: 2, str: "two", list: [[1.0, 2.0, 0.9]], dict: {"AA": [[1.0, 2.0, [0.5]]]}}


def _a_row(key: str) -> pl.DataFrame:
    """One row of a result, built from the columns its schema declares."""
    samples = {pl.String: "x", pl.Float64: 1.0, pl.Int64: 1, pl.Int32: 1, pl.Boolean: True}
    dtypes = CalculatedDataStructure.get_dtypes(key)
    return pl.DataFrame({name: [samples.get(dtype, None)] for name, dtype in dtypes.items()},
                        schema=dtypes)


def _metadata(key: str, parameter: str, value) -> dict:
    """Metadata a result of this kind carries, with one parameter set to a given value."""
    declared = CalculatedDataStructure.get_metadata_types(key) or {}
    recorded = {name: A_VALUE[kind] for name, kind in declared.items()}
    recorded[parameter] = value
    return recorded


PARAMETERISED = [(key, parameter)
                 for key in CalculatedDataStructure.SCHEMAS
                 for parameter in CalculatedDataStructure.recorded_parameters(key)]


@pytest.mark.parametrize("key,parameter", PARAMETERISED, ids=[f"{k}:{p}" for k, p in PARAMETERISED])
def test_a_result_worked_out_with_another_parameter_is_not_handed_back(key, parameter, observation,
                                                                       manipulator):
    """A parameter that changes the answer is part of the question, so a stored answer to another
    one is not this one's.

    This was true of `time_step` because the cache compared it by name, and of the weather and the
    detection threshold because two calculations compared those themselves. Three hand-written
    copies of one rule, and the fourth calculation to record a parameter would have had none:
    it would have handed back the previous numbers, which is what freshness exists to prevent.
    """
    from pastrocore.super.schedule_calculator import ScheduleCalculator

    kind = (CalculatedDataStructure.get_metadata_types(key) or {})[parameter]
    stored, asked = A_VALUE[kind], ANOTHER[kind]
    frame = _a_row(key)
    observation.set_calculated_data_by_key(key, frame, _metadata(key, parameter, stored))

    # Everything else the question is made of stays as it was, so the one difference is the one
    # under test -- otherwise `time_step` alone would account for every recalculation here.
    wanted = _metadata(key, parameter, asked)
    ran = []
    ScheduleCalculator(manipulator)._get_cached_or_calculate(
        observation, key, lambda obj, attrs: (ran.append(parameter), frame)[1],
        {"recalculate": False, "store_key": key,
         **{name: value for name, value in wanted.items() if name in freshness.PARAMETERS}},
        wanted)

    assert ran, (f"'{key}' was handed back although it was worked out with {parameter}={stored!r} "
                 f"and {asked!r} was asked for")


@pytest.mark.parametrize("key,parameter", PARAMETERISED, ids=[f"{k}:{p}" for k, p in PARAMETERISED])
def test_the_same_parameter_is_the_same_question(key, parameter, observation, manipulator):
    """The half that keeps the test above from being satisfied by recomputing everything."""
    from pastrocore.super.schedule_calculator import ScheduleCalculator

    kind = (CalculatedDataStructure.get_metadata_types(key) or {})[parameter]
    frame = _a_row(key)
    metadata = _metadata(key, parameter, A_VALUE[kind])
    observation.set_calculated_data_by_key(key, frame, metadata)

    ran = []
    ScheduleCalculator(manipulator)._get_cached_or_calculate(
        observation, key, lambda obj, attrs: (ran.append(parameter), frame)[1],
        {"recalculate": False, "store_key": key, **{name: value for name, value in metadata.items()
                                                    if name in freshness.PARAMETERS}},
        dict(metadata))

    assert not ran, f"'{key}' was worked out again although nothing about the question changed"


def test_every_parameter_is_declared_as_a_kind_a_result_can_record():
    """The two tests above are driven by the schema, so a parameter of an undeclared kind would
    quietly drop out of them rather than fail."""
    for key in CalculatedDataStructure.SCHEMAS:
        declared = CalculatedDataStructure.get_metadata_types(key) or {}
        for parameter in CalculatedDataStructure.recorded_parameters(key):
            assert declared[parameter] in A_VALUE, (
                f"'{key}' records {parameter} as {declared[parameter]}, which no test can vary")


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


def test_a_calculation_answers_to_its_handler_s_name_as_well_as_to_its_key():
    """One calculation files its result under another name than its handler's, and the schema is
    read by both spellings -- the catalogue speaks handlers, results are filed under store keys.

    Asked by the handler's name, the dependencies came back as "everything", which is the
    coarseness the declaration exists to avoid: every edit would stale it.
    """
    assert CalculatedDataStructure.SCHEMAS["times"]["handler"] == "time_arrays"

    for reader in (CalculatedDataStructure.get_dependencies, CalculatedDataStructure.get_columns,
                   CalculatedDataStructure.get_dtypes, CalculatedDataStructure.get_metadata_types):
        assert reader("time_arrays") == reader("times"), (
            f"{reader.__name__} answers differently to a handler's name than to its store key")

    assert CalculatedDataStructure.get_dependencies("time_arrays") != (
        "telescopes", "sources", "scans", "frequencies")


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
    observation = reopened.get_observations()[0]

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
    observation = reopened.get_observations()[0]

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
    observation = reopened.get_observations()[0]
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


def test_asking_serialises_each_part_once(project, tmp_path, monkeypatch):
    """Opening one project converted the same scan ten times over, which a user saw in the log
    as twenty identical lines.

    A dozen results depend on nearly the same handful of parts, so the naive version paid for
    every overlap. The explorer asks the same question on every refresh, so it was not only a
    load-time cost.
    """
    import collections

    from pastrocore.base.scans import Scans

    root = tmp_path / "counted.pastro"
    project.save(str(root))
    for sidecar in (root / "results").rglob("*.meta.json"):
        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        metadata.pop(freshness.DIGEST_FIELD, None)
        sidecar.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    calls = collections.Counter()
    original = Scans.to_dict
    monkeypatch.setattr(Scans, "to_dict",
                        lambda self, *a, **k: (calls.update(["scans"]), original(self, *a, **k))[1])

    reopened = ScheduleProject.open(str(root))
    assert calls["scans"] <= 1, (
        f"opening converted the scans {calls['scans']} times; once is enough for any number "
        f"of results that depend on them")

    observation = reopened.get_observations()[0]
    calls.clear()
    observation.stale_results()
    assert calls["scans"] <= 1, (
        f"one refresh converted the scans {calls['scans']} times")


# --- the declaration checked against what the handler reaches ---------------------------------

def test_deactivating_a_source_stales_the_time_arrays(observation, manipulator):
    """`times` is grouped by *active source* -- one block per source, and a `source_name`
    column to say which. It declared `("scans",)`, so a source going inactive left a result
    holding rows for it while the interface called that result current.

    Found by comparing the declaration against what MSB derives the handler to touch.
    """
    from pastrocore.base import freshness

    manipulator.calculate(obj=observation, method="time_arrays", time_step=600.0,
                          recalculate=True)
    assert freshness.is_stale(observation, "times") is False

    source = observation.get_sources().get_items()[0]
    source.isactive = not source.isactive

    assert freshness.is_stale(observation, "times") is True, (
        "a source went inactive and the result computed per source stayed 'current'")


#: Calculations whose declared `depends_on` is narrower than what MSB derives them to touch.
#: The derivation is an **upper bound** -- a shared helper is followed for every handler that
#: calls it -- so a difference is a candidate rather than a defect, and each entry here has
#: been looked at. The list may shrink and must never grow without a reason written beside it.
NARROWER_THAN_DERIVED = {
    # Reached through helpers shared with the calculations that do read them. Orbits are
    # interpolated over the scan's times and the spacecraft's ephemeris; no source is involved.
    "interpolated_orbits": {"sources"},
    "telescope_positions": {"sources"},
    "telescope_az_el": {"sources"},
    "telescope_visibility": {"sources"},
    # Station geometry and the scan window reach it through `_process_object`; the pattern
    # itself is a function of the dish and the frequency.
    "beam_pattern": {"scans", "sources"},
    "time_arrays": {"telescopes"},
}


def test_no_calculation_declares_less_than_it_reads():
    """MSB derives what a handler touches outside its own operation. It cannot replace the
    declaration -- it is an upper bound -- but it is exactly what checks one, and it found a
    real defect: `times` reads sources and said it did not.
    """
    from pastrocore.base.data_structure import CalculatedDataStructure
    from pastrocore.super.schedule_manipulator import ScheduleManipulator
    from pastrocore.super.schedule_project import ScheduleProject
    from pastrocore.super.schedule_runner import ScheduleRunner

    manipulator = ScheduleManipulator(ScheduleProject(name="probe"))
    described = manipulator.describe_operations(
        "calculate", interpret=ScheduleRunner.MODEL_PARTS.get)["calculate"]

    surprises = {}
    for key, entry in described.items():
        declared = set(CalculatedDataStructure.entry_for(key).get("depends_on") or ())
        missing = set(entry["touches"]) - declared - NARROWER_THAN_DERIVED.get(key, set())
        if missing:
            surprises[key] = sorted(missing)

    assert not surprises, (
        f"{surprises} reach model parts they do not declare, so a change to one leaves the "
        f"result looking current. Declare it, or record why the derivation over-reports it in "
        f"NARROWER_THAN_DERIVED.")


def test_metadata_holding_arrays_can_be_compared(observation, manipulator):
    """Reported from a live session:

        ERROR - Failed to calculate Mollweide tracks: The truth value of an array with more
        than one element is ambiguous. Use a.any() or a.all()

    `_store_result` decides whether to write by comparing the new metadata against the stored
    one. Mollweide records the source coordinates it draws against, and those are numpy arrays,
    so comparing two of those mappings with `==` produces an array rather than an answer.
    """
    import numpy as np
    import polars as pl

    from pastrocore.super.schedule_calculator import ScheduleCalculator

    calculator = ScheduleCalculator(manipulator)
    frame = pl.DataFrame({"time": [1.0], "scan_name": ["s"], "telescope_code": ["T"],
                          "lon": [0.1], "lat": [0.2]})
    metadata = {"time_step": 600.0, "scan_count": 1, "start_time": 0.0, "end_time": 1.0,
                "sources": {"1228+126": np.array([1.0, 2.0, 3.0])}}

    # As the calculator does it: the frame is stored while it is computed, with the metadata
    # it has at that moment -- arrays and all -- and `_store_result` then compares.
    observation.set_calculated_data_by_key("mollweide_tracks", frame, metadata)

    # Recomputed, so the arrays are equal and distinct. A shallow copy would compare identical
    # objects and never reach the comparison that raised.
    again = {"time_step": 600.0, "scan_count": 1, "start_time": 0.0, "end_time": 1.0,
             "sources": {"1228+126": np.array([1.0, 2.0, 3.0])}}
    calculator._store_result(observation, "mollweide_tracks", frame, again)

    stored = observation.get_calculated_metadata("mollweide_tracks")
    assert stored is not None and "sources" in stored


def test_two_metadata_mappings_holding_arrays_compare_without_raising():
    """The comparison itself, which is where the reported failure came from."""
    import numpy as np

    from pastrocore.base import freshness

    one = {"time_step": 600.0, "sources": {"1228+126": np.array([1.0, 2.0, 3.0])}}
    same = {"time_step": 600.0, "sources": {"1228+126": np.array([1.0, 2.0, 3.0])}}
    other = {"time_step": 600.0, "sources": {"1228+126": np.array([1.0, 2.0, 4.0])}}

    with pytest.raises(ValueError):
        bool(one == same)               # what the calculator used to do

    assert freshness.same_metadata(one, same) is True
    assert freshness.same_metadata(one, other) is False
    assert freshness.same_metadata(one, None) is False
    assert freshness.same_metadata({"a": [1, 2]}, {"a": [1, 2]}) is True
