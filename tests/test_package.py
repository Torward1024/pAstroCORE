"""A project as one file (R6): how it reaches a colleague or a bug report.

A project is a **directory**, which is right for working in and wrong for sending. Packing the
working project was measured and rejected -- parquet is already compressed, so zip saves 0.6%,
and opening becomes 46x slower. Neither cost applies to a file written once and unpacked once,
which is what this is: an exchange format, not storage.
"""
import json
import zipfile

import pytest

from pastrocore.super.schedule_data import ScheduleData
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject

import conftest


@pytest.fixture
def core(project):
    return ScheduleManipulator(project)


def packed(core, project, destination, **attributes):
    return core.export(obj=project, method="package", path=str(destination),
                       raise_on_error=False, **attributes)


def test_a_packed_project_reopens_as_the_project_it_was(core, project, tmp_path):
    """The whole claim. It holds because `Project.__eq__` compares contents -- which is what
    msb_arch 2.0.0 added and what `CalculatedData.__eq__` finished here."""
    answer = packed(core, project, tmp_path / "survey")
    assert answer.ok, answer.error

    opening = ScheduleProject(name="opening")
    reopened = ScheduleManipulator(opening).load(
        obj=opening, method="package", path=answer.value["path"], raise_on_error=False)

    assert reopened.ok, reopened.error
    assert reopened.value == project


def test_the_results_travel_with_it(core, project, tmp_path):
    """A colleague opening it should not have to recalculate a day of work."""
    observation = project.get_observations()[0]
    core.compute(obj=observation, method="run", calculations=["uv_coverage"], time_step=600.0,
                 raise_on_error=False)
    here = set(observation.calculated_data.keys())

    answer = packed(core, project, tmp_path / "survey")
    opening = ScheduleProject(name="opening")
    reopened = ScheduleManipulator(opening).load(
        obj=opening, method="package", path=answer.value["path"])

    assert set(reopened.get_observations()[0].calculated_data.keys()) == here


def test_packing_leaves_the_project_where_it_was(project, tmp_path):
    """Sending a colleague a copy must not take the results away from the sender.

    Packing saves the project into a temporary directory and deletes it afterwards, and a save
    re-points every observation at where it was written -- so the project in hand came back
    pointing at a directory that had just been removed. A project opened from disk with eleven
    results had none the moment it was packed; they were still on disk, and nothing in the
    session could reach them again until it was reopened.
    """
    root = tmp_path / "work.pastro"
    project.save(str(root))
    reopened = ScheduleProject.open(str(root))
    observation = reopened.get_observations()[0]
    before = set(observation.calculated_data.keys())
    assert len(before) > 1

    answer = packed(ScheduleManipulator(reopened), reopened, tmp_path / "sent")
    assert answer.ok, answer.error

    assert set(observation.calculated_data.keys()) == before, "packing took the results away"
    assert observation.get_calculated_data_by_key("uv_coverage")["data"].height > 0, (
        "the results are named but no longer readable")


def test_packing_an_unsaved_project_keeps_what_it_has_calculated(core, project, tmp_path):
    """The same fault, where it costs the most.

    A project that has never been saved keeps its results in this session's scratch, which is
    what protects them from a crash. Packing saved into a temporary directory, which moved them
    out of the scratch and then discarded it -- so both copies went, and the only thing left was
    whatever happened to still be in memory.
    """
    observation = project.get_observations()[0]
    core.compute(obj=observation, method="run", calculations=["uv_coverage"], time_step=600.0,
                 raise_on_error=False)
    project.hold_results_in_scratch()
    observation.calculated_data.flush()
    scratch = project.scratch.path
    assert scratch is not None and list(scratch.rglob("*.parquet"))

    assert packed(core, project, tmp_path / "unsaved").ok

    assert scratch.exists() and list(scratch.rglob("*.parquet")), (
        "packing threw away the results of a session that had never been saved")


def test_a_bug_report_can_leave_the_results_behind(core, project, tmp_path):
    """The model alone: a few kilobytes that reproduce the configuration, without a gigabyte of
    frames nobody reading the report needs."""
    core.compute(obj=project.get_observations()[0], method="run", calculations=["uv_coverage"],
                 time_step=600.0, raise_on_error=False)

    full = packed(core, project, tmp_path / "everything").value
    lean = packed(core, project, tmp_path / "report", results=False).value

    assert lean["files"] == 1, "the model is one file"
    assert lean["bytes"] < full["bytes"]
    with zipfile.ZipFile(lean["path"]) as package:
        assert package.namelist() == [ScheduleProject.MODEL_FILE]


def test_a_model_only_package_writes_no_results_anywhere(core, project, tmp_path, monkeypatch):
    """Not merely absent from the zip: never written.

    Packing saved the whole project into a temporary directory and then left the results out of
    the archive, so a package of a few kilobytes cost a copy of every parquet the project has.
    """
    from pastrocore.base.result_store import ResultStore

    copied = []
    monkeypatch.setattr(ResultStore, "write",
                        lambda self, owner, key, frame, metadata: copied.append(key))

    answer = packed(core, project, tmp_path / "report", results=False)

    assert answer.ok, answer.error
    assert not copied, f"{len(copied)} result(s) were written out only to be left out"


def test_a_model_only_package_still_opens(core, project, tmp_path):
    """It is a project, just one that has calculated nothing yet."""
    answer = packed(core, project, tmp_path / "report", results=False)

    opening = ScheduleProject(name="opening")
    reopened = ScheduleManipulator(opening).load(
        obj=opening, method="package", path=answer.value["path"])

    assert [o.code for o in reopened.get_observations()] == [o.code for o in project.get_observations()]


def test_the_suffix_is_added_when_it_is_missing(core, project, tmp_path):
    """A user typing a name in a save dialog should not have to remember the extension."""
    answer = packed(core, project, tmp_path / "survey")

    assert answer.value["path"].endswith(ScheduleData.ARCHIVE_SUFFIX)


def test_an_existing_file_is_not_replaced_silently(core, project, tmp_path):
    packed(core, project, tmp_path / "survey")

    again = packed(core, project, tmp_path / "survey")

    assert not again.ok
    assert "overwrite" in str(again.error)


def test_overwrite_replaces_it(core, project, tmp_path):
    packed(core, project, tmp_path / "survey")

    again = packed(core, project, tmp_path / "survey", overwrite=True)

    assert again.ok


def test_packing_without_a_path_is_refused(core, project):
    answer = core.export(obj=project, method="package", raise_on_error=False)

    assert not answer.ok
    assert "path" in str(answer.error)


def test_a_zip_that_is_not_a_project_is_refused(core, project, tmp_path):
    """Said plainly. The other way to find out is a project that opens with everything
    missing."""
    stranger = tmp_path / "holiday.pastroz"
    with zipfile.ZipFile(stranger, "w") as package:
        package.writestr("photo.jpg", "not a project")

    opening = ScheduleProject(name="opening")
    answer = ScheduleManipulator(opening).load(
        obj=opening, method="package", path=str(stranger), raise_on_error=False)

    assert not answer.ok
    assert ScheduleProject.MODEL_FILE in str(answer.error)


def test_a_file_that_is_not_a_zip_is_refused(core, project, tmp_path):
    plain = tmp_path / "notes.pastroz"
    plain.write_text("hello", encoding="utf-8")

    opening = ScheduleProject(name="opening")
    answer = ScheduleManipulator(opening).load(
        obj=opening, method="package", path=str(plain), raise_on_error=False)

    assert not answer.ok


def test_an_entry_that_would_escape_the_directory_is_refused(core, project, tmp_path):
    """A package is a file from somewhere else, and an entry named `../../...` is the oldest
    trick there is against a program that unpacks one."""
    hostile = tmp_path / "hostile.pastroz"
    with zipfile.ZipFile(hostile, "w") as package:
        package.writestr(ScheduleProject.MODEL_FILE, json.dumps({"name": "p", "items": {}}))
        package.writestr("../escaped.txt", "should never be written")

    opening = ScheduleProject(name="opening")
    answer = ScheduleManipulator(opening).load(
        obj=opening, method="package", path=str(hostile), into=str(tmp_path / "unpacked"),
        raise_on_error=False)

    assert not answer.ok
    assert not (tmp_path / "escaped.txt").exists(), "an entry escaped the directory"


def test_unpacking_into_a_chosen_directory(core, project, tmp_path):
    """So a colleague can keep what they were sent rather than working in a temporary copy."""
    answer = packed(core, project, tmp_path / "survey")
    into = tmp_path / "kept"

    opening = ScheduleProject(name="opening")
    reopened = ScheduleManipulator(opening).load(
        obj=opening, method="package", path=answer.value["path"], into=str(into))

    assert (into / ScheduleProject.MODEL_FILE).is_file()
    assert reopened == project


# --- the command line ---------------------------------------------------------------------

def test_the_command_line_packs_a_project(project, tmp_path, capsys):
    from pastrocore import cli

    root = tmp_path / "proj.pastro"
    project.save(str(root))

    assert cli.main(["package", str(root), str(tmp_path / "sent")]) == 0
    assert (tmp_path / "sent.pastroz").is_file()
    assert "KB" in capsys.readouterr().out


def test_the_command_line_refuses_to_replace_without_force(project, tmp_path, capsys):
    from pastrocore import cli

    root = tmp_path / "proj.pastro"
    project.save(str(root))
    cli.main(["package", str(root), str(tmp_path / "sent")])

    assert cli.main(["package", str(root), str(tmp_path / "sent")]) == 1
    assert cli.main(["package", str(root), str(tmp_path / "sent"), "--force"]) == 0


def test_every_command_works_on_a_package_without_unpacking_it(project, tmp_path, capsys):
    """What a colleague was sent is a project as far as reading it goes."""
    from pastrocore import cli

    root = tmp_path / "proj.pastro"
    project.save(str(root))
    cli.main(["package", str(root), str(tmp_path / "sent")])
    capsys.readouterr()

    assert cli.main(["info", str(tmp_path / "sent.pastroz")]) == 0
    assert project.get_observations()[0].code in capsys.readouterr().out
