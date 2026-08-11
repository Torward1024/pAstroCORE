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


def test_saving_drops_results_of_observations_that_left(project, tmp_path):
    """A rename must not leave the old results behind for a later rename to pick up."""
    from pastrocore.super.schedule_project import ScheduleProject

    root = tmp_path / "saved.pastro"
    project.save(str(root))

    original = next(iter(project.get_items()))
    assert (root / "results" / original).is_dir()

    reopened = ScheduleProject.open(str(root))
    moved = reopened.get_observation(original)
    reopened.remove_item(original)
    moved.name = "renamed"
    reopened.add_item(moved)
    reopened.save(str(root))

    assert not (root / "results" / original).exists(), "the old results must not survive"
    assert (root / "results" / "renamed").is_dir()

    # The results have to survive the move, not merely be filed somewhere.
    again = ScheduleProject.open(str(root))
    carried = again.get_observation("renamed").calculated_data
    assert len(carried) == 11
    assert carried["uv_coverage"]["data"].height > 0


def test_a_rename_onto_an_existing_name_keeps_the_current_results(project, tmp_path):
    """Two observations cannot share a results directory, and the newer one is the truth."""
    from pastrocore.base.result_store import CalculatedData, ResultStore

    store = ResultStore(tmp_path / "results")
    store.write("first", "times", pl.DataFrame({"t": [1.0]}), {})
    store.write("second", "times", pl.DataFrame({"t": [2.0]}), {})

    results = CalculatedData("first", store=store)
    results.attach(store, "second")

    assert not (tmp_path / "results" / "first").exists()
    assert store.read("second", "times")["data"]["t"].to_list() == [2.0]


# --- reading lazily -----------------------------------------------------------------------

def test_drawing_a_plot_leaves_nothing_in_memory(project, tmp_path):
    """The point of D3. A plot filters, so the filter belongs in the read.

    Before this, drawing read every row of a result and kept it: a session that plotted its
    way through a year of observations ended holding the whole project, which is the problem
    the directory format was supposed to solve.
    """
    from pastrocore.super.schedule_manipulator import ScheduleManipulator
    from pastrocore.super.schedule_project import ScheduleProject

    root = tmp_path / "plotted.pastro"
    project.save(str(root))

    reopened = ScheduleProject.open(str(root))
    observation = reopened.get_observation(next(iter(reopened.get_items())))
    manipulator = ScheduleManipulator(reopened)
    assert observation.calculated_data._resident == {}

    manipulator.visualize(obj=observation, plot_type="az_el", source_name="1228+126",
                          telescopes=["ALMA", "APEX"], return_figure=True, show=False,
                          raise_on_error=False)

    assert observation.calculated_data._resident == {}, (
        "a plot must not leave the result it read in memory")


def test_metadata_does_not_drag_the_result_in(project, tmp_path):
    """Metadata is a handful of entries beside the parquet; reaching it through the result
    read every row to get there."""
    from pastrocore.super.schedule_project import ScheduleProject

    root = tmp_path / "meta.pastro"
    project.save(str(root))

    reopened = ScheduleProject.open(str(root))
    observation = reopened.get_observation(next(iter(reopened.get_items())))

    metadata = observation.get_calculated_metadata("uv_coverage")
    assert metadata.get("time_step") is not None
    assert observation.calculated_data._resident == {}


def test_a_filter_reaches_the_read(project, tmp_path):
    """A pushed-down filter must not merely give the right answer -- it must avoid the rows."""
    from pastrocore.super.schedule_project import ScheduleProject

    root = tmp_path / "scanned.pastro"
    project.save(str(root))

    reopened = ScheduleProject.open(str(root))
    observation = reopened.get_observation(next(iter(reopened.get_items())))

    view = observation.scan_calculated_data("uv_coverage")
    assert isinstance(view, pl.LazyFrame), "reading for a filter must stay lazy"

    plan = view.filter(pl.col("baseline") == "ALMA-APEX").explain()
    assert "parquet" in plan.lower()

    filtered = view.filter(pl.col("baseline") == "ALMA-APEX").collect()
    whole = observation.calculated_data["uv_coverage"]["data"]
    assert filtered.height == whole.filter(pl.col("baseline") == "ALMA-APEX").height


def test_scanning_a_missing_result_says_so_rather_than_raising(project):
    """The plots ask for results that may not have been calculated yet."""
    observation = project.get_observation(next(iter(project.get_items())))
    assert observation.scan_calculated_data("never_calculated") is None
    assert observation.get_calculated_metadata("never_calculated") == {}


# --- the residency budget ------------------------------------------------------------------

def test_the_budget_evicts_the_least_recently_used(tmp_path):
    """Results are dropped in the order they stopped being useful, not the order they arrived."""
    from pastrocore.base.result_store import CalculatedData, ResidencyBudget, ResultStore

    store = ResultStore(tmp_path / "results")
    frames = {}
    for name in ("a", "b", "c"):
        frames[name] = pl.DataFrame({"x": list(range(2000))})
        store.write("obs", name, frames[name], {})

    one_result = frames["a"].estimated_size()
    budget = ResidencyBudget(limit_bytes=int(one_result * 2.5))
    results = CalculatedData("obs", store=store, budget=budget)

    results["a"], results["b"]
    assert set(results._resident) == {"a", "b"}

    results["a"]                       # 'b' is now the least recently used
    results["c"]                       # which makes room for this

    assert "b" not in results._resident, "the least recently used should have gone"
    assert set(results._resident) == {"a", "c"}


def test_an_evicted_result_reads_back_the_same(tmp_path):
    """Eviction must cost a read, never a number."""
    from pastrocore.base.result_store import CalculatedData, ResidencyBudget, ResultStore

    store = ResultStore(tmp_path / "results")
    original = pl.DataFrame({"x": [1.5, 2.5, 3.5], "name": ["a", "b", "c"]})
    store.write("obs", "kept", original, {"note": "unchanged"})
    store.write("obs", "other", pl.DataFrame({"x": list(range(5000))}), {})

    budget = ResidencyBudget(limit_bytes=1)
    results = CalculatedData("obs", store=store, budget=budget)

    results["kept"]
    results["other"]
    assert "kept" not in results._resident

    assert results["kept"]["data"].equals(original)
    assert results["kept"]["metadata"]["note"] == "unchanged"


def test_an_unwritten_result_is_never_evicted(tmp_path):
    """There would be nowhere to read it back from, so the budget must leave it alone."""
    from pastrocore.base.result_store import CalculatedData, ResidencyBudget, ResultStore

    store = ResultStore(tmp_path / "results")
    store.write("obs", "stored", pl.DataFrame({"x": list(range(5000))}), {})

    budget = ResidencyBudget(limit_bytes=1)
    results = CalculatedData("obs", store=store, budget=budget)
    results["fresh"] = {"data": pl.DataFrame({"x": [1, 2, 3]}), "metadata": {}}

    results["stored"]

    assert "fresh" in results._resident, "an unwritten result must survive any budget"
    assert results["fresh"]["data"].height == 3


def test_a_result_larger_than_the_budget_is_still_returned(tmp_path):
    """The budget governs what may be kept, never what may be read.

    Refusing to read a result too big for the budget would turn a memory setting into a
    correctness one: the plot would be blank and the number wrong.
    """
    from pastrocore.base.result_store import CalculatedData, ResidencyBudget, ResultStore

    store = ResultStore(tmp_path / "results")
    big = pl.DataFrame({"x": list(range(50000))})
    store.write("obs", "big", big, {})

    results = CalculatedData("obs", store=store, budget=ResidencyBudget(limit_bytes=1))
    assert results["big"]["data"].height == 50000


def test_the_budget_is_shared_across_observations(project, tmp_path):
    """The memory they compete for is one machine's, not one observation's."""
    from pastrocore.super.schedule_project import ScheduleProject

    root = tmp_path / "shared.pastro"
    project.save(str(root))

    reopened = ScheduleProject.open(str(root))
    budgets = {id(observation.calculated_data._budget)
               for observation in reopened._items.get_items()}
    assert len(budgets) == 1
    assert budgets == {id(reopened.residency_budget)}


def test_the_share_is_rejected_when_it_is_not_a_share(project):
    """A budget of nothing would evict a result the instant it was read."""
    with pytest.raises(ValueError):
        project.set_residency_share(0)
    with pytest.raises(ValueError):
        project.set_residency_share(1.5)

    project.set_residency_share(0.25)
    assert project.residency_budget.share == 0.25


def test_the_budget_follows_the_machine(project):
    """A share, not a number, because the same project is opened on a laptop and a workstation."""
    project.set_residency_share(0.5)
    half = project.residency_budget.limit
    project.set_residency_share(0.25)
    quarter = project.residency_budget.limit

    assert half > 0
    assert quarter == pytest.approx(half / 2, rel=0.15)


def test_copying_an_observation_does_not_fork_the_budget(project, tmp_path):
    """Two budgets would each believe they had the whole ceiling."""
    import copy

    from pastrocore.super.schedule_project import ScheduleProject

    root = tmp_path / "copied.pastro"
    project.save(str(root))
    reopened = ScheduleProject.open(str(root))
    observation = reopened.get_observation(next(iter(reopened.get_items())))

    duplicate = copy.deepcopy(observation)
    assert duplicate.calculated_data._budget is observation.calculated_data._budget


def test_walking_many_observations_stays_inside_the_budget(tmp_path):
    """The case that started all of this, at a size a build machine can afford.

    Measured at sixty observations of 200 000 rows: without a budget the walk grew memory by
    407 MB and ended holding all sixty results. With a 200 MB ceiling it grew by 71 MB and held
    thirty-two. This is the same shape, small enough to run on every push.

    It asserts residency rather than resident set size on purpose: RSS depends on the
    allocator and on what else the machine is doing, so a build machine would fail it for
    reasons that have nothing to do with this code.
    """
    from pastrocore.base.result_store import CalculatedData, ResidencyBudget, ResultStore

    store = ResultStore(tmp_path / "results")
    rows = 20000
    for index in range(20):
        store.write(f"obs{index:02d}", "uv_coverage",
                    pl.DataFrame({"u": [float(v) for v in range(rows)],
                                  "v": [float(v) for v in range(rows)]}), {})

    one_result = pl.DataFrame({"u": [float(v) for v in range(rows)],
                               "v": [float(v) for v in range(rows)]}).estimated_size()
    budget = ResidencyBudget(limit_bytes=one_result * 4)

    holders = [CalculatedData(f"obs{index:02d}", store=store, budget=budget)
               for index in range(20)]
    for results in holders:
        assert results["uv_coverage"]["data"].height == rows

    resident = sum(len(results._resident) for results in holders)
    assert resident <= 5, f"the budget allows about four results, {resident} are in hand"
    assert budget.held <= budget.limit

    # And the last one read is still there, because it is what the caller is using.
    assert "uv_coverage" in holders[-1]._resident


def test_without_a_budget_nothing_is_evicted(tmp_path):
    """The comparison that gives the test above its meaning."""
    from pastrocore.base.result_store import CalculatedData, ResultStore

    store = ResultStore(tmp_path / "results")
    for index in range(20):
        store.write(f"obs{index:02d}", "uv_coverage", pl.DataFrame({"u": [1.0] * 20000}), {})

    holders = [CalculatedData(f"obs{index:02d}", store=store) for index in range(20)]
    for results in holders:
        results["uv_coverage"]

    assert sum(len(results._resident) for results in holders) == 20
