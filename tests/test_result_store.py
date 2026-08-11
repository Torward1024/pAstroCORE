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


def test_a_result_reaches_the_disk_the_moment_it_is_calculated(store, frame):
    """It used to wait for the next save, which is how a day of calculation was lost."""
    results = CalculatedData("obs1", store)
    results["uv_coverage"] = {"data": frame, "metadata": {}}

    assert store.has("obs1", "uv_coverage"), "written on arrival, not at save time"
    assert results.flush() == 0, "so there is nothing left for flush to do"


def test_flush_still_writes_what_could_not_be_written_earlier(store, frame):
    """Write-through is best effort: a store that fails leaves the result held, and flush is
    the second chance. Without this the fallback path would never be exercised."""
    results = CalculatedData("obs1", store=None)
    results["uv_coverage"] = {"data": frame, "metadata": {}}
    assert "uv_coverage" in results._unwritten

    assert results.flush(store) == 1
    assert store.has("obs1", "uv_coverage")
    assert results.flush() == 0


def test_a_failing_write_costs_the_protection_and_not_the_result(store, frame, monkeypatch):
    """A full disk must not lose the calculation that has just been done."""
    def refuse(*args, **kwargs):
        raise OSError("no space left on device")

    monkeypatch.setattr(type(store), "write", refuse)
    results = CalculatedData("obs1", store)
    results["uv_coverage"] = {"data": frame, "metadata": {}}

    assert results["uv_coverage"]["data"].equals(frame), "the result is still in hand"
    assert "uv_coverage" in results._unwritten, "and will be written at the next opportunity"


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

    # Genuinely unwritten: the store refused it, so there is nowhere to read it back from.
    # With write-through this is the only way a result is unwritten, and it is exactly the
    # case where evicting it would destroy it.
    results._resident["fresh"] = {"data": pl.DataFrame({"x": [1, 2, 3]}), "metadata": {}}
    results._unwritten.add("fresh")

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


# --- the scratch directory ------------------------------------------------------------------

@pytest.fixture
def scratch_root(tmp_path):
    """A scratch root of our own, so tests never write to the user's data directory."""
    return tmp_path / "scratch"


def test_a_result_survives_the_session_that_calculated_it(project, scratch_root):
    """The scenario this exists for: calculate for a day, never save, lose the process."""
    from pastrocore.base.scratch import ScratchSpace

    space = ScratchSpace(root=scratch_root, session="1234-aaaa")
    project.attach_results_store(space.store)

    observation = project.get_observation(next(iter(project.get_items())))
    observation.set_calculated_data_by_key("fresh", pl.DataFrame({"x": [1.0, 2.0]}), {"note": "kept"})

    owner = observation.name
    del project, observation                      # the session goes away without saving

    # A later session reads the scratch directory with nothing but the path.
    survivor = ResultStore(scratch_root / "1234-aaaa" / "results")
    assert "fresh" in survivor.keys(owner)
    assert survivor.read(owner, "fresh")["data"]["x"].to_list() == [1.0, 2.0]
    assert survivor.read(owner, "fresh")["metadata"]["note"] == "kept"


def test_what_is_calculated_is_on_disk_before_anything_is_saved(project, scratch_root):
    from pastrocore.base.scratch import ScratchSpace

    space = ScratchSpace(root=scratch_root, session="1234-bbbb")
    project.attach_results_store(space.store)
    observation = project.get_observation(next(iter(project.get_items())))
    observation.set_calculated_data_by_key("fresh", pl.DataFrame({"x": [1.0, 2.0]}), {})

    written = list((space.path / "results").rglob("*.parquet"))
    assert written, "the result must reach the disk without waiting for a save"


def test_saving_brings_the_scratch_results_into_the_project(project, scratch_root, tmp_path):
    """Saving moves results rather than asking for them to be calculated again."""
    from pastrocore.base.scratch import ScratchSpace
    from pastrocore.super.schedule_project import ScheduleProject

    space = ScratchSpace(root=scratch_root, session="1234-cccc")
    project.attach_results_store(space.store)
    observation = project.get_observation(next(iter(project.get_items())))
    observation.set_calculated_data_by_key("fresh", pl.DataFrame({"x": [7.0, 8.0]}), {"note": "carried"})

    root = tmp_path / "saved.pastro"
    project.save(str(root))

    reopened = ScheduleProject.open(str(root))
    carried = reopened.get_observation(observation.name).calculated_data
    assert "fresh" in carried
    assert carried["fresh"]["data"]["x"].to_list() == [7.0, 8.0]
    assert carried["fresh"]["metadata"]["note"] == "carried"


def test_two_sessions_do_not_share_a_scratch(scratch_root):
    """A window must not adopt or evict another window's results -- and the same rule is what
    lets a server run sessions for several people."""
    from pastrocore.base.scratch import ScratchSpace

    first, second = ScratchSpace(root=scratch_root), ScratchSpace(root=scratch_root)
    assert first.session != second.session

    first.store.write("obs", "a", pl.DataFrame({"x": [1.0]}), {})
    second.store.write("obs", "b", pl.DataFrame({"x": [2.0]}), {})

    assert first.store.keys("obs") == ["a"]
    assert second.store.keys("obs") == ["b"]


def test_a_clean_exit_removes_only_its_own(scratch_root):
    from pastrocore.base.scratch import ScratchSpace

    mine, theirs = ScratchSpace(root=scratch_root), ScratchSpace(root=scratch_root)
    mine.store.write("obs", "a", pl.DataFrame({"x": [1.0]}), {})
    theirs.store.write("obs", "b", pl.DataFrame({"x": [2.0]}), {})
    other_path = theirs.path

    mine.discard()

    assert not (scratch_root / mine.session).exists()
    assert other_path.exists(), "another session's results are not ours to delete"


def test_an_interrupted_session_is_offered_back(scratch_root, monkeypatch):
    """A scratch directory left by a previous run is not litter. It is the day of calculation
    this whole mechanism exists to protect."""
    from pastrocore.base import scratch as scratch_module
    from pastrocore.base.scratch import ScratchSpace

    dead = ScratchSpace(root=scratch_root, session="99999-dead")
    dead.note_project("Survey A")
    dead.store.write("obs", "uv_coverage", pl.DataFrame({"x": [1.0]}), {})

    monkeypatch.setattr(scratch_module, "live_pids", lambda: set())
    found = ScratchSpace.abandoned(root=scratch_root)

    assert len(found) == 1
    assert found[0].results == 1
    assert "Survey A" in found[0].describe()


def test_a_running_session_is_not_offered_back(scratch_root, monkeypatch):
    """Offering another window's live directory would invite the user to recover results that
    are still being written."""
    from pastrocore.base import scratch as scratch_module
    from pastrocore.base.scratch import ScratchSpace

    import os

    alive = ScratchSpace(root=scratch_root, session="12345-live")
    alive.store.write("obs", "uv_coverage", pl.DataFrame({"x": [1.0]}), {})

    # The marker records this process, so claiming it is running is claiming the truth.
    monkeypatch.setattr(scratch_module, "live_pids", lambda: {os.getpid()})
    assert ScratchSpace.abandoned(root=scratch_root) == []


def test_an_unanswerable_process_is_treated_as_alive(scratch_root, monkeypatch):
    """The bias is deliberate: wrongly claiming a session is dead offers up a directory that
    is being written to, while wrongly claiming it is alive costs one stale directory."""
    from pastrocore.base import scratch as scratch_module

    monkeypatch.setattr(scratch_module, "psutil", None, raising=False)
    monkeypatch.setitem(__import__("sys").modules, "psutil", None)
    assert scratch_module._process_is_alive(999999) is True


def test_a_session_that_calculated_nothing_leaves_nothing(scratch_root):
    """Starting the application and closing it must not litter."""
    from pastrocore.base.scratch import ScratchSpace

    space = ScratchSpace(root=scratch_root)
    assert space.path is None
    assert not scratch_root.exists()


def test_an_empty_abandoned_session_is_not_offered(scratch_root, monkeypatch):
    """There is nothing to recover, so asking would be noise."""
    from pastrocore.base import scratch as scratch_module
    from pastrocore.base.scratch import ScratchSpace

    empty = ScratchSpace(root=scratch_root, session="4242-empty")
    empty.store                                    # creates the directory, writes nothing

    monkeypatch.setattr(scratch_module, "live_pids", lambda: set())
    assert ScratchSpace.abandoned(root=scratch_root) == []


def test_nothing_but_a_scratch_directory_can_ever_be_deleted(tmp_path):
    """Deleting a project would be the worst failure this module could have, so it is made
    unreachable rather than merely avoided.

    Reported as happening after a save, and not reproducible on any path through the code --
    which is exactly when a guard earns its place, because "I could not make it happen" is not
    the same as "it cannot happen".
    """
    from pastrocore.base.scratch import ScratchSpace, _is_a_scratch_directory

    root = tmp_path / "scratch"
    space = ScratchSpace(root=root, session="mine")
    space.store.write("obs", "a", pl.DataFrame({"x": [1.0]}), {})
    assert _is_a_scratch_directory(space.path, root), "a real scratch directory must qualify"

    project = tmp_path / "real.pastro"
    (project / "results").mkdir(parents=True)
    (project / "project.json").write_text("{}", encoding="utf-8")

    assert not _is_a_scratch_directory(project, root), "outside the scratch root"
    assert not _is_a_scratch_directory(project, tmp_path), "and it holds a project"
    assert not _is_a_scratch_directory(root, root), "the root itself is not a session"


def test_a_project_inside_the_scratch_root_is_still_refused(tmp_path):
    """Nothing invites this and nothing forbids it, so the marker has to be what decides."""
    from pastrocore.base.scratch import MARKER, ScratchSpace, _is_a_scratch_directory

    root = tmp_path / "scratch"
    intruder = root / "a_project.pastro"
    (intruder / "results").mkdir(parents=True)
    (intruder / "project.json").write_text("{}", encoding="utf-8")
    (intruder / MARKER).write_text('{"pid": 1}', encoding="utf-8")

    assert not _is_a_scratch_directory(intruder, root)


def test_discard_refuses_rather_than_deletes(tmp_path):
    """The guard has to be wired in, not merely written."""
    from pastrocore.base.scratch import ScratchSpace

    root = tmp_path / "scratch"
    space = ScratchSpace(root=root, session="mine")
    space.store.write("obs", "a", pl.DataFrame({"x": [1.0]}), {})

    project = tmp_path / "real.pastro"
    (project / "results").mkdir(parents=True)
    (project / "project.json").write_text("{}", encoding="utf-8")

    space._path = project            # the failure that was reported, forced
    space.discard()

    assert project.is_dir(), "a project directory must survive being handed to discard"
    assert (project / "project.json").is_file()


# --- metadata that agrees with its data, and files anything can read ------------------------

def strict(text):
    """Parse JSON the way something that is not Python would.

    Notes:
        - `json.loads` accepts `NaN` and `Infinity` by default, so reading a file back with it
          proves nothing about whether the file is valid JSON. This refuses them, which is what
          a parser in another language does without being asked.
    """
    def refuse(constant):
        raise ValueError(f"{constant} is not valid JSON")

    return json.loads(text, parse_constant=refuse)


def test_the_metadata_describes_the_frame_beside_it(project, tmp_path):
    """The reported defect: 288 rows over one scan, beside metadata saying it covered nothing.

    `_process_object` stores the frame with placeholder metadata, and the correction afterwards
    was guarded by "or nothing is stored yet" -- which is false precisely because the frame has
    just been stored. The correction could never happen.
    """
    from pastrocore.super.schedule_manipulator import ScheduleManipulator
    from pastrocore.super.schedule_project import ScheduleProject

    observation = project.get_observation(next(iter(project.get_items())))
    observation.calculated_data.clear()
    manipulator = ScheduleManipulator(project)

    # recalculate=False is the path the defect lived on.
    manipulator.calculate(observation, method="time_arrays", time_step=300.0,
                          raise_on_error=False)

    frame = observation.calculated_data["times"]["data"]
    metadata = observation.get_calculated_metadata("times")

    assert metadata["scan_count"] == frame["scan_name"].unique().len()
    assert metadata["start_time"] == pytest.approx(frame["time"].min())
    assert metadata["end_time"] == pytest.approx(frame["time"].max())


def test_the_metadata_survives_being_saved(project, tmp_path):
    """It has to still agree after a round trip, since that is where it was found wrong."""
    from pastrocore.super.schedule_manipulator import ScheduleManipulator
    from pastrocore.super.schedule_project import ScheduleProject

    observation = project.get_observation(next(iter(project.get_items())))
    observation.calculated_data.clear()
    ScheduleManipulator(project).calculate(observation, method="time_arrays", time_step=300.0,
                                           raise_on_error=False)

    root = tmp_path / "metadata.pastro"
    project.save(str(root))
    reopened = ScheduleProject.open(str(root))
    restored = reopened.get_observation(observation.name)

    metadata = restored.get_calculated_metadata("times")
    frame = restored.calculated_data["times"]["data"]
    assert metadata["scan_count"] == frame["scan_name"].unique().len()
    assert metadata["start_time"] is not None


def test_no_file_the_application_writes_contains_nan(project, tmp_path):
    """`json.dumps` writes bare NaN, which is not valid JSON. A file in that state can be read
    by us and by nothing else -- which surfaces the first time an export, an import or a server
    response is parsed by something we did not write.
    """
    root = tmp_path / "strict.pastro"
    project.save(str(root))

    written = list(root.rglob("*.json"))
    assert written, "nothing was written to check"
    for path in written:
        try:
            strict(path.read_text(encoding="utf-8"))
        except ValueError as reason:
            pytest.fail(f"{path.relative_to(root)} is not valid JSON: {reason}")


def test_an_unrepresentable_number_becomes_null_rather_than_nan(tmp_path):
    """None is not a workaround: a span that could not be determined is absent, and null is how
    JSON says absent."""
    store = ResultStore(tmp_path / "results")
    store.write("obs", "times", pl.DataFrame({"x": [1.0]}),
                {"start_time": float("nan"), "end_time": float("inf"),
                 "nested": {"deep": float("nan")}, "listed": [1.0, float("nan")],
                 "kept": 300.0})

    text = (tmp_path / "results" / "obs" / "times.meta.json").read_text(encoding="utf-8")
    assert "NaN" not in text and "Infinity" not in text

    metadata = strict(text)
    assert metadata["start_time"] is None
    assert metadata["end_time"] is None
    assert metadata["nested"]["deep"] is None
    assert metadata["listed"] == [1.0, None]
    assert metadata["kept"] == 300.0


def test_recalculating_does_not_rewrite_an_unchanged_result(project, tmp_path):
    """Storing is a disk write now, so correcting metadata must not mean writing every time."""
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    root = tmp_path / "rewrite.pastro"
    project.save(str(root))
    observation = project.get_observation(next(iter(project.get_items())))
    manipulator = ScheduleManipulator(project)

    manipulator.calculate(observation, method="time_arrays", time_step=300.0, raise_on_error=False)
    written = root / "results" / observation.name / "times.parquet"
    before = written.stat().st_mtime_ns

    manipulator.calculate(observation, method="time_arrays", time_step=300.0, raise_on_error=False)
    assert written.stat().st_mtime_ns == before, "an unchanged result was written again"


def test_looking_for_abandoned_sessions_does_not_ask_about_every_directory(tmp_path, monkeypatch):
    """Startup got slow: 1 246 ms, of which 843 was psutil.pid_exists called once per scratch
    directory, against a hundred and ninety-nine of them -- every one empty, so the answer was
    never even used.

    Two mistakes, and this holds both fixed: ask the operating system once rather than per
    directory, and only for directories that hold something worth offering back.
    """
    from pastrocore.base import scratch as scratch_module
    from pastrocore.base.scratch import ScratchSpace

    root = tmp_path / "scratch"
    for index in range(30):
        ScratchSpace(root=root, session=f"{index}-empty").store       # a directory, no results
    ScratchSpace(root=root, session="99-real").store.write(
        "obs", "uv_coverage", pl.DataFrame({"x": [1.0]}), {})

    asked = []
    monkeypatch.setattr(scratch_module, "live_pids",
                        lambda: asked.append(1) or set())

    found = ScratchSpace.abandoned(root=root)

    assert len(asked) <= 1, f"the process list was asked for {len(asked)} times, not once"
    assert len(found) == 1 and found[0].results == 1


def test_scratch_directories_holding_nothing_are_swept(tmp_path):
    """One accumulates per run otherwise. "A scratch directory is not litter" protects
    calculations, and one holding none is exactly litter."""
    import os
    import time

    from pastrocore.base.scratch import ScratchSpace

    root = tmp_path / "scratch"
    empty = ScratchSpace(root=root, session="1-empty")
    empty.store
    kept = ScratchSpace(root=root, session="2-kept")
    kept.store.write("obs", "a", pl.DataFrame({"x": [1.0]}), {})

    old = time.time() - 7200
    os.utime(empty.path, (old, old))

    ScratchSpace.abandoned(root=root)

    assert not empty.path.exists(), "an empty, untouched directory should have been swept"
    assert kept.path.exists(), "one holding results must survive"


def test_a_session_running_right_now_is_not_swept(tmp_path):
    """Protected by how recently it was touched, which costs nothing to check -- asking the
    operating system per directory is the expense this whole path exists to avoid."""
    from pastrocore.base.scratch import ScratchSpace

    root = tmp_path / "scratch"
    fresh = ScratchSpace(root=root, session="3-live")
    fresh.store                                  # created just now, still empty

    ScratchSpace.abandoned(root=root)

    assert fresh.path.exists(), "a directory touched moments ago belongs to a live session"
