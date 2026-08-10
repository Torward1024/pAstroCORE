"""Saving a project and loading it back must change nothing.

Stage 4 of the roadmap replaces how projects are stored, and stage 3 deletes most of the
hand-written `from_dict` overrides. Both edit the code that reads and writes a user's work.
This is what stands between those changes and a corrupted project file.

The fixture is a project the author saved from the application, so what is tested is the real
format rather than one invented here.
"""
import copy
import json

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
                          sefd_table={1420.0: 350.0, 8400.0: 500.0})
    restored = Telescope.from_dict(json.loads(json.dumps(telescope.to_dict())))

    assert restored.sefd_table == {1420.0: 350.0, 8400.0: 500.0}
    assert all(isinstance(key, float) for key in restored.sefd_table)


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
