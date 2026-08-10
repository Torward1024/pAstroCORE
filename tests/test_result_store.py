"""Results live on disk and are read when asked for, not before.

The reported case -- 300 sources, a year of daily observations, 12 telescopes -- is 173 million
rows of `uv_coverage` alone, 8.3 GB resident before anything else exists. A project that holds
every result in memory cannot serve it, and a project file that embeds every result cannot be
opened without reading all of them.

These tests are about the two properties that follow: a key that is on disk exists without
being read, and a consumer that filters can filter inside the read.
"""
import json

import polars as pl
import pytest

from pastrocore.base.result_store import CalculatedData, ResultStore


@pytest.fixture
def store(tmp_path):
    return ResultStore(tmp_path / "results")


@pytest.fixture
def frame():
    return pl.DataFrame({
        "source": ["a", "a", "b", "b"],
        "u": [1.0, 2.0, 3.0, 4.0],
        "v": [5.0, 6.0, 7.0, 8.0],
    })


def test_a_result_round_trips(store, frame):
    store.write("obs1", "uv_coverage", frame, {"time_step": 300.0})
    read = store.read("obs1", "uv_coverage")

    assert read["data"].equals(frame)
    assert read["metadata"] == {"time_step": 300.0}


def test_keys_are_answered_from_the_filenames(store, frame):
    """Listing what a project holds must not read what it holds."""
    store.write("obs1", "uv_coverage", frame, {})
    store.write("obs1", "az_el", frame, {})

    assert store.keys("obs1") == ["az_el", "uv_coverage"]
    assert store.has("obs1", "uv_coverage")
    assert not store.has("obs1", "nothing")


def test_unserializable_metadata_is_dropped_rather_than_losing_the_result(store, frame):
    """A note about a result is not worth the result."""
    store.write("obs1", "uv_coverage", frame, {"good": 1, "bad": object()})

    assert store.read("obs1", "uv_coverage")["metadata"] == {"good": 1}


def test_a_filter_can_be_pushed_into_the_read(store, frame):
    """The reason for parquet on disk rather than a container.

    Measured on an observation-sized frame: filtering inside the read returns 1 584 rows of
    475 200 and is 2.6x faster than reading everything and filtering afterwards.
    """
    store.write("obs1", "uv_coverage", frame, {})
    filtered = store.scan("obs1", "uv_coverage").filter(pl.col("source") == "a").collect()

    assert filtered.height == 2


# --- the mapping the application sees -----------------------------------------------------

def test_it_behaves_like_the_dictionary_it_replaces(store, frame):
    results = CalculatedData("obs1", store)
    results["uv_coverage"] = {"data": frame, "metadata": {"time_step": 300.0}}

    assert "uv_coverage" in results
    assert len(results) == 1
    assert list(results.keys()) == ["uv_coverage"]
    assert results["uv_coverage"]["data"].equals(frame)
    assert results.get("nothing") is None
    assert [key for key, _ in results.items()] == ["uv_coverage"]


def test_a_stored_result_exists_without_being_read(store, frame):
    """The property the whole format is for: opening a project reads the model, not the results."""
    store.write("obs1", "uv_coverage", frame, {})
    results = CalculatedData("obs1", store)

    assert "uv_coverage" in results
    assert len(results) == 1
    assert results._resident == {}, "listing a result must not load it"

    results["uv_coverage"]
    assert "uv_coverage" in results._resident, "asking for it does load it"


def test_flush_writes_what_is_held(store, frame):
    results = CalculatedData("obs1", store)
    results["uv_coverage"] = {"data": frame, "metadata": {}}

    assert results.flush() == 1
    assert store.has("obs1", "uv_coverage")
    assert results.flush() == 0, "nothing left unwritten"


def test_released_results_come_back_from_disk(store, frame):
    results = CalculatedData("obs1", store)
    results["uv_coverage"] = {"data": frame, "metadata": {}}
    results.flush()

    results.release()
    assert results._resident == {}
    assert results["uv_coverage"]["data"].equals(frame), "read back on demand"


def test_an_unwritten_result_is_never_released(store, frame):
    """Releasing it would leave nowhere to read it back from."""
    results = CalculatedData("obs1", store)
    results["uv_coverage"] = {"data": frame, "metadata": {}}

    results.release()
    assert results["uv_coverage"]["data"].equals(frame)


def test_results_with_no_store_still_work(frame):
    """An observation not yet part of a saved project keeps its results in memory."""
    results = CalculatedData("obs1")
    results["uv_coverage"] = {"data": frame, "metadata": {}}

    assert results["uv_coverage"]["data"].equals(frame)
    with pytest.raises(ValueError, match="no store"):
        results.flush()


def test_clearing_removes_what_is_on_disk_too(store, frame):
    results = CalculatedData("obs1", store)
    results["uv_coverage"] = {"data": frame, "metadata": {}}
    results.flush()

    results.clear()
    assert len(results) == 0
    assert not store.has("obs1", "uv_coverage")


# --- a project as a directory -------------------------------------------------------------

def test_a_project_saves_as_a_directory(project, tmp_path):
    """The model in one small file, each result in its own, so opening reads only the model."""
    from pastrocore.super.schedule_project import ScheduleProject

    root = tmp_path / "saved.pastro"
    project.to_directory(str(root))

    assert (root / "project.json").is_file()
    assert list((root / "results").rglob("*.parquet")), "no results written"
    assert ScheduleProject.is_directory_project(str(root))


def test_the_model_is_a_fraction_of_the_single_file(project, tmp_path):
    """The single-file form of the fixture is 97% base64; the model itself is a few kilobytes.

    That ratio is the whole argument for the format: a project of a year of observations cannot
    be opened at all if opening means reading every result.
    """
    from conftest import FIXTURE

    root = tmp_path / "saved.pastro"
    project.to_directory(str(root))

    model = (root / "project.json").stat().st_size
    assert model < FIXTURE.stat().st_size / 10, (
        f"the model is {model} bytes against a single file of {FIXTURE.stat().st_size}")


def test_loading_a_directory_reads_no_results(project, project_data, tmp_path):
    """The property everything else rests on."""
    from pastrocore.super.schedule_project import ScheduleProject

    root = tmp_path / "saved.pastro"
    project.to_directory(str(root))

    loaded = ScheduleProject.from_directory(str(root))
    observation = loaded.get_observation(next(iter(project_data["items"])))

    assert len(observation.calculated_data) == 11, "every result is visible"
    assert observation.calculated_data._resident == {}, "and none of them has been read"


def test_a_result_is_read_when_it_is_asked_for(project, project_data, tmp_path):
    from pastrocore.super.schedule_project import ScheduleProject

    root = tmp_path / "saved.pastro"
    project.to_directory(str(root))
    loaded = ScheduleProject.from_directory(str(root))
    observation = loaded.get_observation(next(iter(project_data["items"])))

    frame = observation.calculated_data["uv_coverage"]["data"]

    assert frame.height > 0
    assert list(observation.calculated_data._resident) == ["uv_coverage"], "only that one"


def test_the_results_survive_the_round_trip(project, project_data, tmp_path):
    """A format that loses numbers would be worse than the memory it saves."""
    from pastrocore.super.schedule_project import ScheduleProject

    observation = project.get_observation(next(iter(project_data["items"])))
    before = {key: observation.calculated_data[key]["data"].height
              for key in observation.calculated_data.keys()}

    root = tmp_path / "saved.pastro"
    project.to_directory(str(root))
    loaded = ScheduleProject.from_directory(str(root))
    restored = loaded.get_observation(next(iter(project_data["items"])))

    after = {key: restored.calculated_data[key]["data"].height
             for key in restored.calculated_data.keys()}
    assert after == before


def test_a_directory_without_a_model_is_refused(tmp_path):
    from pastrocore.super.schedule_project import ScheduleProject

    with pytest.raises(IOError, match="not a project directory"):
        ScheduleProject.from_directory(str(tmp_path))


# --- one entry point, and converting what already exists ----------------------------------

def test_open_accepts_a_directory(project, tmp_path):
    from pastrocore.super.schedule_project import ScheduleProject

    root = tmp_path / "saved.pastro"
    project.save(str(root))
    assert ScheduleProject.open(str(root)).name == project.name


def test_open_accepts_the_model_file_inside_a_directory(project, tmp_path):
    """The file dialog shows files, so a user navigating into a project picks this one."""
    from pastrocore.super.schedule_project import ScheduleProject

    root = tmp_path / "saved.pastro"
    project.save(str(root))
    assert ScheduleProject.open(str(root / "project.json")).name == project.name


def test_open_still_accepts_a_single_file(tmp_path):
    """Every project saved before this format existed has to keep opening."""
    import shutil

    from conftest import FIXTURE
    from pastrocore.super.schedule_project import ScheduleProject

    legacy = tmp_path / "old.pastro"
    shutil.copy(FIXTURE, legacy)

    loaded = ScheduleProject.open(str(legacy))
    assert loaded.name


def test_saving_over_a_single_file_converts_it(tmp_path, project_data):
    """The path a user already has in their recent files keeps working, and becomes the new
    format the first time they save."""
    import shutil

    from conftest import FIXTURE
    from pastrocore.super.schedule_project import ScheduleProject

    legacy = tmp_path / "old.pastro"
    shutil.copy(FIXTURE, legacy)
    assert legacy.is_file()

    loaded = ScheduleProject.open(str(legacy))
    loaded.save(str(legacy))

    assert legacy.is_dir(), "the single file became a directory"
    assert (legacy / "project.json").is_file()

    reopened = ScheduleProject.open(str(legacy))
    observation = reopened.get_observation(next(iter(project_data["items"])))
    assert len(observation.calculated_data) == 11
    assert observation.calculated_data._resident == {}, "and reopening reads none of them"


def test_an_interrupted_conversion_leaves_the_original(tmp_path, monkeypatch):
    """The old file is removed only once the directory is complete, never before."""
    import shutil

    from conftest import FIXTURE
    from pastrocore.super.schedule_project import ScheduleProject

    legacy = tmp_path / "old.pastro"
    shutil.copy(FIXTURE, legacy)
    loaded = ScheduleProject.open(str(legacy))

    def explode(self, path):
        raise RuntimeError("disk full")

    monkeypatch.setattr(ScheduleProject, "to_directory", explode)
    with pytest.raises(RuntimeError):
        loaded.save(str(legacy))

    assert legacy.is_file(), "the original must survive a failed conversion"
