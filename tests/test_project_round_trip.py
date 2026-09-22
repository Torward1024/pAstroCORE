"""Saving a project and loading it back must change nothing.

Stage 4 of the roadmap replaces how projects are stored, and stage 3 deletes most of the
hand-written `from_dict` overrides. Both edit the code that reads and writes a user's work.
This is what stands between those changes and a corrupted project file.

The fixture is a project the author saved from the application, so what is tested is the real
format rather than one invented here.
"""
import copy
import json
import pathlib

import pytest

from pastrocore.super.schedule_project import ScheduleProject


def test_a_saved_project_loads(project, observation):
    """The starting point: the format the application writes can be read back."""
    assert project.name
    assert observation.get_observation_code()
    assert len(observation.get_telescopes().get_items()) == 2
    assert len(observation.get_sources().get_items()) == 1


def test_a_project_survives_a_round_trip(project_data):
    """Load, save, load: the second reading has to match the first."""
    once = ScheduleProject.from_dict(copy.deepcopy(project_data))
    written = once.to_dict()
    twice = ScheduleProject.from_dict(copy.deepcopy(written))

    assert twice.to_dict() == written


def test_the_model_survives_json(project_data):
    """A project is stored as JSON, so anything unserializable is a bug in the model."""
    once = ScheduleProject.from_dict(copy.deepcopy(project_data))
    text = json.dumps(once.to_dict())
    restored = ScheduleProject.from_dict(json.loads(text))

    assert restored.name == once.name


def test_the_calculated_results_survive_a_round_trip(project_data):
    """The expensive part of a project, and the part stored as opaque blobs."""
    once = ScheduleProject.from_dict(copy.deepcopy(project_data))
    observation = once.get_observation(next(iter(project_data["items"])))
    before = {key: value["data"].height for key, value in observation.calculated_data.items()}

    twice = ScheduleProject.from_dict(copy.deepcopy(once.to_dict()))
    restored = twice.get_observation(next(iter(project_data["items"])))
    after = {key: value["data"].height for key, value in restored.calculated_data.items()}

    assert after == before


@pytest.mark.parametrize("entity", ["telescopes", "sources", "frequencies", "scans"])
def test_each_collection_survives_a_round_trip(project_data, entity):
    """Named separately so a failure says which part of the model broke."""
    once = ScheduleProject.from_dict(copy.deepcopy(project_data))
    observation = once.get_observation(next(iter(project_data["items"])))
    getter = getattr(observation, f"get_{entity}")

    twice = ScheduleProject.from_dict(copy.deepcopy(once.to_dict()))
    restored_observation = twice.get_observation(next(iter(project_data["items"])))
    restored_getter = getattr(restored_observation, f"get_{entity}")

    assert len(restored_getter().get_items()) == len(getter().get_items())


# --- what the fixture does not cover ------------------------------------------------------

def test_a_float_keyed_instrument_table_round_trips():
    """The fixture project happens to hold empty tables, so this path is not otherwise tested.

    It is the reason `Source` and `Telescope` each carried a hand-written `from_dict`: JSON has
    only string keys, so a `Dict[float, float]` came back keyed by strings and was rejected.
    msb_arch 1.0.1 restores mapping keys from the annotation, and the overrides are gone.
    """
    from pastrocore.base.telescope import Telescope

    telescope = Telescope(code="EF", name="Effelsberg", x=1.0, y=2.0, z=3.0, diameter=100.0,
                          sefd_table=[(1400.0, 1720.0, 350.0), (8150.0, 8650.0, 500.0)])
    restored = Telescope.from_dict(json.loads(json.dumps(telescope.to_dict())))

    assert restored.sefd_table == [(1400.0, 1720.0, 350.0), (8150.0, 8650.0, 500.0)]
    assert all(isinstance(row, tuple) for row in restored.sefd_table)


def test_a_telescope_written_before_its_tables_had_ranges_still_opens():
    """Before E1 a table was `{frequency: value}`. Each value was measured at one frequency, so
    it comes back as a row covering that frequency and nothing else -- no range is made up."""
    from pastrocore.base.telescope import Telescope

    written = {"name": "Effelsberg", "type": "Telescope", "code": "EF", "diameter": 100.0,
               "sefd_table": {"1420.0": 350.0}, "system_temperature_table": {"4840.0": 25.0}}
    restored = Telescope.from_dict(written)

    assert restored.sefd_table == [(1420.0, 1420.0, 350.0)]
    assert restored.get_system_temperature(4840.0) == 25.0
    assert restored.get_system_temperature(4841.0) is None


def test_a_float_keyed_flux_table_round_trips():
    from pastrocore.base.sources import Source

    source = Source(name="3C273", ra_h=12.0, ra_m=0.0, ra_s=0.0,
                    de_d=2.0, de_m=0.0, de_s=0.0, flux_table={1420.0: 45.0, 5000.0: 30.0})
    restored = Source.from_dict(json.loads(json.dumps(source.to_dict())))

    assert restored.flux_table == {1420.0: 45.0, 5000.0: 30.0}


def test_a_mount_type_round_trips_as_its_enum():
    """`Telescope.__init__` converts it, which is why removing the `from_dict` override was safe."""
    from pastrocore.base.telescope import MountType, Telescope

    telescope = Telescope(code="EF", name="Effelsberg", x=1.0, y=2.0, z=3.0,
                          mount_type="EQUA")
    restored = Telescope.from_dict(json.loads(json.dumps(telescope.to_dict())))

    assert isinstance(restored.mount_type, MountType)
    assert restored.mount_type == telescope.mount_type


def test_an_elevation_range_comes_back_as_a_tuple():
    """Restored from the annotation by msb_arch 1.0, where the override used to do it."""
    from pastrocore.base.telescope import Telescope

    telescope = Telescope(code="EF", name="Effelsberg", x=1.0, y=2.0, z=3.0,
                          elevation_range=(15.0, 85.0))
    restored = Telescope.from_dict(json.loads(json.dumps(telescope.to_dict())))

    assert restored.elevation_range == (15.0, 85.0)
    assert isinstance(restored.elevation_range, tuple)


# --- schema versioning (M5) ---------------------------------------------------------------

def test_a_project_at_version_one_writes_no_version(project):
    """Versioning must cost nothing until it is used, or every existing file changes shape."""
    assert "schema_version" not in project.to_dict()


def test_a_project_that_raises_its_version_refuses_older_data_by_default(project_data):
    """Stage 4 changes how results are stored. This is what stops a project written before it
    from being read as though nothing had changed."""
    from msb_arch import errors

    class Moved(ScheduleProject):
        SCHEMA_VERSION = 2

    payload = dict(copy.deepcopy(project_data))
    payload["schema_version"] = 1
    with pytest.raises(errors.SerializationError, match="version 1"):
        Moved.from_dict(payload)


def test_a_migration_is_taken_when_one_is_written(project_data):
    class Renamed(ScheduleProject):
        SCHEMA_VERSION = 2
        migrated = False

        @classmethod
        def migrate(cls, data, from_version):
            Renamed.migrated = True
            return data

    payload = dict(copy.deepcopy(project_data))
    payload["schema_version"] = 1
    Renamed.from_dict(payload)
    assert Renamed.migrated


# --- space telescopes ----------------------------------------------------------------------

def test_a_space_telescope_survives_a_round_trip():
    """It could not be read back at all, so a project holding one would not open.

    A space telescope has no station geometry, no mount and no elevation limits: the
    constructor fixes them. They are inherited fields all the same, so `to_dict` wrote them and
    `from_dict` handed them straight back to a constructor that does not accept them.
    """
    from pastrocore.base.spacetelescope import SpaceTelescope
    from pastrocore.base.telescopes import Telescopes

    telescope = SpaceTelescope(code="RADIO", name="RadioAstron",
                               pitch_range=(-90.0, 90.0), yaw_range=(-180.0, 180.0))
    box = Telescopes(name="telescopes")
    box.add(telescope)

    restored = Telescopes.from_dict(box.to_dict()).get_all()["RadioAstron"]

    assert isinstance(restored, SpaceTelescope)
    assert restored.pitch_range == (-90.0, 90.0)
    assert restored.yaw_range == (-180.0, 180.0)


def test_a_spacecraft_placed_by_keplerian_elements_comes_back(tmp_path):
    """Found by the audit: it went out and did not come back.

    `to_dict` writes the epoch as an ISO string -- which is what a file holds -- and the
    constructor refuses anything that is not an astropy `Time`, so a project holding a
    spacecraft on Keplerian elements could not be opened: `Epoch must be an astropy Time
    object`. Every round-trip test used the other branch, a spacecraft following an orbit file.
    """
    from astropy.time import Time

    from pastrocore.base.observation import Observation
    from pastrocore.base.spacetelescope import SpaceTelescope

    epoch = Time("2026-08-10T05:00:00")
    telescope = SpaceTelescope(code="RADIO", name="RadioAstron", use_kep=True, kepler_elements={
        "a": 3.0e7, "e": 0.01, "i": 51.0, "raan": 10.0, "argp": 90.0, "nu": 0.0,
        "epoch": epoch, "mu": 3.986004418e14})

    restored = SpaceTelescope.from_dict(telescope.to_dict())

    assert restored.use_kep is True
    assert isinstance(restored.kepler_elements["epoch"], Time)
    assert restored.kepler_elements["epoch"].isot == epoch.isot
    assert restored.kepler_elements["a"] == 3.0e7

    # And through a whole project, which is the path a user takes.
    project = ScheduleProject(name="Space")
    observation = Observation(name="obs_space", code="SPACE")
    observation.get_telescopes().add(telescope)
    project.add_item(observation)
    project.to_directory(str(tmp_path / "space.pastro"))
    reopened = ScheduleProject.open(str(tmp_path / "space.pastro"))

    held = reopened.get_observations()[0].get_telescopes().get_items()[0]
    assert isinstance(held.kepler_elements["epoch"], Time)


def test_a_copied_observation_is_not_stale_on_the_spot():
    """Found by the audit: copying an observation marked every result stale.

    Two of the four collections invented a new name when copied, the name is part of what a
    collection serializes, and a result's fingerprint covered it -- so even a beam pattern, which
    depends on the telescopes and nothing else, came back stale. The copies keep their names, and
    a fingerprint covers what a calculation *reads* rather than what the collection is called.
    """
    from pastrocore.base import freshness

    project = ScheduleProject.from_dict(copy.deepcopy(json.loads(
        (pathlib.Path(__file__).parent / "fixtures" / "test_project.pastro").read_text(encoding="utf-8"))))
    observation = project.get_observations()[0]
    twin = observation.copy()

    # A copy is another object, so it is named as one -- a name is an identity here.
    assert twin.name != observation.name
    for part in ("get_telescopes", "get_sources", "get_scans", "get_frequencies"):
        assert getattr(twin, part)().name != getattr(observation, part)().name, (
            f"{part} came back under the original's name")

    for key in observation.calculated_data:
        was = freshness.digest(observation, key, observation.get_calculated_metadata(key))
        now = freshness.digest(twin, key, twin.get_calculated_metadata(key))
        assert was == now, f"copying the observation made '{key}' stale"


def test_what_a_collection_is_called_is_not_what_a_result_was_computed_from():
    """The other half of the same finding: renaming a collection is not a change to the numbers,
    and moving a station is."""
    from pastrocore.base import freshness

    project = ScheduleProject.from_dict(copy.deepcopy(json.loads(
        (pathlib.Path(__file__).parent / "fixtures" / "test_project.pastro").read_text(encoding="utf-8"))))
    observation = project.get_observations()[0]
    before = freshness.digest(observation, "beam_pattern",
                              observation.get_calculated_metadata("beam_pattern"))

    observation.get_telescopes().name = "telescopes_under_another_name"
    assert freshness.digest(observation, "beam_pattern",
                            observation.get_calculated_metadata("beam_pattern")) == before

    observation.get_telescopes().get_items()[0].set({"diameter": 12.5})
    assert freshness.digest(observation, "beam_pattern",
                            observation.get_calculated_metadata("beam_pattern")) != before


def test_a_space_telescope_saved_by_an_older_version_still_opens():
    """Files already written carry the fields `to_dict` no longer emits."""
    from pastrocore.base.spacetelescope import SpaceTelescope

    telescope = SpaceTelescope(code="RADIO", name="RadioAstron")
    older = telescope.to_dict()
    older.update({"elevation_range": [15.0, 90.0], "azimuth_range": [0.0, 360.0],
                  "mount_type": "AZIM", "x": 0.0, "y": 0.0, "z": 0.0})

    restored = SpaceTelescope.from_dict(older)
    assert restored.code == "RADIO"


def test_a_space_telescope_accepts_whole_number_ranges():
    """`(0, 90)` is how anyone writes a range of degrees."""
    from pastrocore.base.spacetelescope import SpaceTelescope

    telescope = SpaceTelescope(code="RADIO", name="RadioAstron",
                               pitch_range=(0, 90), yaw_range=(0, 180))
    assert telescope.pitch_range == (0, 90)


def test_a_project_holding_a_space_telescope_opens(tmp_path):
    """The whole point: the file has to come back."""
    from pastrocore.base.observation import Observation
    from pastrocore.base.spacetelescope import SpaceTelescope
    from pastrocore.super.schedule_project import ScheduleProject

    project = ScheduleProject(name="Space")
    observation = Observation(name="obs_space", code="SPACE")
    observation.get_telescopes().add(SpaceTelescope(code="RADIO", name="RadioAstron"))
    project.add_item(observation)

    root = tmp_path / "space.pastro"
    project.save(str(root))

    reopened = ScheduleProject.open(str(root))
    restored = reopened.get_observation("obs_space").get_telescopes().get_all()["RadioAstron"]
    assert isinstance(restored, SpaceTelescope)


def test_a_save_interrupted_part_way_leaves_the_last_save_openable(project, tmp_path, monkeypatch):
    """`project.json` was written in place, and it is the one file without which a project does
    not open at all. A save that failed while writing it -- a full disk, an application closed
    mid-save -- left a truncated model and nothing to open."""
    import pathlib

    root = tmp_path / "saved"
    project.save(str(root))
    before = (root / ScheduleProject.MODEL_FILE).read_text(encoding="utf-8")

    real_write = pathlib.Path.write_text

    def disk_fills_half_way(self, data, *args, **kwargs):
        if self.name.startswith(ScheduleProject.MODEL_FILE):
            real_write(self, data[: len(data) // 2], *args, **kwargs)
            raise OSError("No space left on device")
        return real_write(self, data, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "write_text", disk_fills_half_way)
    with pytest.raises(OSError):
        project.save(str(root))
    monkeypatch.undo()

    assert (root / ScheduleProject.MODEL_FILE).read_text(encoding="utf-8") == before
    assert ScheduleProject.open(str(root)).get_observations(), "the last save no longer opens"
    assert not list(root.glob("*.partial")), "a half-written model was left behind"


# --- G9: a save says how far it has got -------------------------------------------------------------

def test_a_save_reports_each_result_file_and_then_the_model(project, tmp_path):
    """What a progress bar for saving is counted in: every result written, by observation code and
    calculation, then the model, rising to 100. A save with nothing new writes the model alone,
    and says only that."""
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    core = ScheduleManipulator(project)
    project.hold_results_in_scratch()
    observation = project.get_observations()[0]
    core.compute(obj=observation, method="run", calculations=["uv_coverage"], time_step=600.0,
                 recalculate=True)

    seen = []
    target = tmp_path / "saved"
    core.save(obj=project, path=str(target), progress=lambda percent, message: seen.append((percent, message)))

    files = sorted(target.rglob("*.parquet"))
    writes = [message for _, message in seen if message.startswith("Writing ") and message != "Writing the model"]
    assert len(writes) == len(files) > 0, "one step per result file written"
    assert all(message.startswith(f"Writing {observation.get_observation_code()}: ") for message in writes)
    assert [message for _, message in seen[-2:]] == ["Writing the model", "Saved"]
    percents = [percent for percent, _ in seen]
    assert percents == sorted(percents) and percents[0] == 0 and percents[-1] == 100

    seen.clear()
    core.save(obj=project, path=str(target), progress=lambda percent, message: seen.append((percent, message)))
    assert seen == [(0, "Writing the model"), (100, "Saved")]
