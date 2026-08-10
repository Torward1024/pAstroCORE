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
