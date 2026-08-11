"""Exporting is an operation, not a dialog.

Of the 312 lines in the export dialog, only 60 touched Qt: 252 were logic a command-line
version would have had to write again and a server could not reach at all. They live in
`ScheduleData` now.

These tests exercise it with no Qt imported, which is the whole point -- if any of them needed
a QApplication, the move would not have achieved anything.
"""
import hashlib
import json
import pathlib

import polars as pl
import pytest

import conftest
from pastrocore.super.schedule_data import ScheduleData
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject

TYPES = ["UV Coverage", "Time on Source", "Sun Angles", "Mollweide Tracks"]


def export(manipulator, target, path, **extra):
    """Run an export through the orchestrator and return what it reports."""
    response = manipulator.export(obj=target, calc_types=TYPES, export_data=True,
                                  export_vis=False, export_path=str(path),
                                  units="wavelengths", raise_on_error=False, **extra)
    if isinstance(response, dict) and "status" in response:
        return response["result"] if response["status"] else None
    return response


def test_exporting_needs_no_interface(project, tmp_path):
    """Reachable from a script, which a QDialog and a QThread were not."""
    observation = project.get_observation(next(iter(project.get_items())))
    result = export(ScheduleManipulator(project), observation, tmp_path)

    assert result is not None
    assert len(result["written"]) == 4
    assert not result["cancelled"]
    for path in result["written"]:
        assert pathlib.Path(path).is_file()


def test_it_says_what_it_wrote(project, tmp_path):
    """A caller should not have to go looking on disk to find out what it got."""
    observation = project.get_observation(next(iter(project.get_items())))
    result = export(ScheduleManipulator(project), observation, tmp_path)

    on_disk = sorted(p.name for p in tmp_path.iterdir())
    reported = sorted(pathlib.Path(p).name for p in result["written"])
    assert reported == on_disk


def test_progress_is_reported_through_a_plain_callable(project, tmp_path):
    """The seam: no signals, no threads, nothing this module knows about windows."""
    observation = project.get_observation(next(iter(project.get_items())))
    seen = []
    export(ScheduleManipulator(project), observation, tmp_path,
           progress=lambda percent, message: seen.append((percent, message)))

    assert seen, "an operation this long owes its caller some word of progress"
    assert seen[-1][0] <= 100
    assert all(isinstance(percent, int) for percent, _ in seen)


def test_cancelling_stops_it_and_says_so(project, tmp_path):
    """The other half a long operation owes a caller, expressed the same way."""
    observation = project.get_observation(next(iter(project.get_items())))
    result = export(ScheduleManipulator(project), observation, tmp_path,
                    cancelled=lambda: True)

    assert result["cancelled"] is True
    assert result["written"] == []
    assert list(tmp_path.iterdir()) == []


def test_a_project_exports_every_observation(project, tmp_path):
    """One observation or all of them, without the caller writing the loop."""
    result = export(ScheduleManipulator(project), project, tmp_path)
    assert len(result["written"]) == 4


def test_writing_nowhere_is_refused_rather_than_guessed(project, tmp_path):
    """There is no sensible default for where a user's files should land."""
    observation = project.get_observation(next(iter(project.get_items())))
    data = ScheduleData(ScheduleManipulator(project))

    with pytest.raises(ValueError):
        data._export(observation, {"calc_types": TYPES, "export_data": True})


def test_the_export_releases_results_as_it_goes(project, tmp_path):
    """An export walks every result of every observation; holding them all is the problem the
    directory format was built to solve."""
    root = tmp_path / "saved.pastro"
    project.save(str(root))
    reopened = ScheduleProject.open(str(root))
    observation = reopened.get_observation(next(iter(reopened.get_items())))

    export(ScheduleManipulator(reopened), reopened, tmp_path / "out")

    assert observation.calculated_data._resident == {}


def test_the_bytes_are_what_the_dialog_used_to_produce(project, tmp_path):
    """The move is only safe if the files are identical, not merely similar.

    These digests were taken from the previous implementation before a line was moved.
    """
    expected = {
        "OBS_DEFAULT_UV_Coverage.txt": "3d434be646a57a43",
        "OBS_DEFAULT_Time_on_Source.txt": "d8d4a3c61ea1d50c",
        "OBS_DEFAULT_Sun_Angles.txt": "2f7195b35eaa09d5",
        "OBS_DEFAULT_Mollweide.txt": "4c8e76c65530fc78",
    }
    observation = project.get_observation(next(iter(project.get_items())))
    export(ScheduleManipulator(project), observation, tmp_path)

    produced = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()[:16]
                for path in tmp_path.iterdir()}
    assert produced == expected, (
        "the exported files differ from what the dialog produced before the move")


def test_the_dialog_no_longer_holds_the_logic():
    """A move that leaves a copy behind is not a move."""
    source = (pathlib.Path(__file__).resolve().parent.parent / "pastrocore" / "gui"
              / "p_dialog_export_calculated_data.py").read_text(encoding="utf-8")

    assert "_export_data_to_csv" not in source, "the writer stayed behind"
    assert "write_csv" not in source, "the dialog is still writing files itself"
    assert "manipulator.export(" in source, "and it must reach the operation instead"


# --- save and load as operations --------------------------------------------------------

def test_saving_is_a_request_like_any_other(project, tmp_path):
    """A method among operations is the odd one out: a caller mapping commands to requests
    needs a special case for it, the journal records every calculation of a session but not
    the save that ended it, and a server needs an endpoint outside the request model."""
    root = tmp_path / "viaop.pastro"
    manipulator = ScheduleManipulator(project)

    response = manipulator.save(project, path=str(root), raise_on_error=False)
    result = response["result"] if isinstance(response, dict) and "status" in response else response

    assert result["path"] == str(root)
    assert (root / "project.json").is_file()
    assert (root / "results").is_dir()


def test_loading_is_too(project, tmp_path):
    root = tmp_path / "viaop.pastro"
    project.save(str(root))
    manipulator = ScheduleManipulator(project)

    response = manipulator.load(project, path=str(root), raise_on_error=False)
    result = response["result"] if isinstance(response, dict) and "status" in response else response

    loaded = result["project"]
    assert isinstance(loaded, ScheduleProject)
    assert loaded.name == project.name


def test_the_model_still_owns_its_serialization(project, tmp_path):
    """A facade, not a second implementation. If this ever stops holding, there are two ways
    to write a project and they will disagree."""
    import inspect

    from pastrocore.super.schedule_data import ScheduleData

    source = inspect.getsource(ScheduleData._save_scheduleproject)
    assert "obj.save(" in source, "the operation must delegate to the model"
    assert "to_directory" not in source and "json.dumps" not in source, (
        "the operation is writing a project itself instead of asking the model to")


def test_anything_serialisable_can_be_saved_and_read_back(project, tmp_path):
    """Save and load are not about projects. Any object the model can describe goes to a file,
    and a project takes a branch of its own because it is a directory rather than a file --
    which MSB reaches on its own, by the type of the object the request runs on.
    """
    manipulator = ScheduleManipulator(project)
    observation = project.get_observation(next(iter(project.get_items())))

    for name, obj in [("telescopes", observation.get_telescopes()),
                      ("source", observation.get_sources().get_items()[0]),
                      ("frequencies", observation.get_frequencies())]:
        path = tmp_path / f"{name}.pastrod"
        manipulator.save(obj, path=str(path), raise_on_error=False)
        assert path.is_file(), f"{name} was not written"

        response = manipulator.load(obj, path=str(path), raise_on_error=False)
        result = response["result"] if isinstance(response, dict) and "status" in response else response
        assert type(result["object"]) is type(obj), f"{name} came back as something else"


def test_a_telescope_is_read_back_as_the_kind_the_file_says(project, tmp_path):
    """A ground station and a spacecraft are written to the same kind of file and told apart
    by what is in it, which the general case cannot answer."""
    from pastrocore.base.spacetelescope import SpaceTelescope

    manipulator = ScheduleManipulator(project)
    observation = project.get_observation(next(iter(project.get_items())))
    telescopes = observation.get_telescopes()
    telescopes.add(SpaceTelescope(code="RADIO", name="RadioAstron"))

    for code, expected in [("ALMA", "Telescope"), ("RADIO", "SpaceTelescope")]:
        telescope = next(t for t in telescopes.get_items() if t.get_code() == code)
        path = tmp_path / f"{code}.pastrod"
        manipulator.save(telescope, path=str(path), raise_on_error=False)

        response = manipulator.load(telescopes, path=str(path), raise_on_error=False)
        result = response["result"] if isinstance(response, dict) and "status" in response else response
        assert type(result["object"]).__name__ == expected


def test_the_tabs_no_longer_read_and_write_files_themselves(project):
    """All the logic into the Supers, including the small pieces scattered through the tabs."""
    import pathlib as _pathlib

    gui = _pathlib.Path(__file__).resolve().parent.parent / "pastrocore" / "gui"
    offenders = []
    for module in gui.glob("p_tab_*.py"):
        source = module.read_text(encoding="utf-8")
        if "json.dump(" in source or "json.load(" in source:
            offenders.append(module.name)
    assert not offenders, f"{offenders} still serialise objects by hand"


def test_saving_nowhere_is_refused(project):
    manipulator = ScheduleManipulator(project)
    response = manipulator.save(project, raise_on_error=False)
    assert isinstance(response, dict) and response.get("status") is False


def test_a_session_can_be_expressed_entirely_as_requests(project, tmp_path):
    """What the whole stage is for: configure, calculate, save -- one surface, so the list of
    requests a session made *is* a script.

    A journal that replays every calculation and then saves nothing is a rehearsal.
    """
    manipulator = ScheduleManipulator(project)
    observation = project.get_observation(next(iter(project.get_items())))
    root = tmp_path / "pipeline.pastro"

    manipulator.calculate(observation, method="uv_coverage", time_step=300.0,
                          recalculate=True, raise_on_error=False)
    manipulator.save(project, path=str(root), raise_on_error=False)
    manipulator.export(observation, calc_types=["UV Coverage"], export_data=True,
                       export_vis=False, export_path=str(tmp_path / "out"),
                       raise_on_error=False)

    assert (root / "project.json").is_file()
    assert (tmp_path / "out" / "OBS_DEFAULT_UV_Coverage.txt").is_file()


def test_scan_times_answers_what_ten_tabs_used_to_ask_for_themselves(project):
    """The same filter, group-by and time conversion existed in every visualization tab, each
    copy needing polars and astropy to do it. A command-line version would have written an
    eleventh."""
    manipulator = ScheduleManipulator(project)
    observation = project.get_observation(next(iter(project.get_items())))

    response = manipulator.export(obj=observation, method="scan_times", key="uv_coverage",
                                  source_name="1228+126", raise_on_error=False)
    result = response["result"] if isinstance(response, dict) and "status" in response else response

    assert result, "the fixture observes one source over one scan"
    assert set(result[0]) == {"scan_name", "start"}
    assert result[0]["start"].startswith("20"), "the start is readable, not an MJD float"


def test_an_unobserved_source_is_an_answer_rather_than_an_error(project):
    """A source may simply not be observed, and a tab filling a list needs that back as an
    empty list rather than as an exception."""
    manipulator = ScheduleManipulator(project)
    observation = project.get_observation(next(iter(project.get_items())))

    response = manipulator.export(obj=observation, method="scan_times", key="uv_coverage",
                                  source_name="not_observed", raise_on_error=False)
    result = response["result"] if isinstance(response, dict) and "status" in response else response
    assert result == []


def test_scan_times_needs_to_be_told_what_to_look_at(project):
    from pastrocore.super.schedule_data import ScheduleData

    observation = project.get_observation(next(iter(project.get_items())))
    data = ScheduleData(ScheduleManipulator(project))

    with pytest.raises(ValueError):
        data._export_scan_times(observation, {"key": "uv_coverage"})
    with pytest.raises(ValueError):
        data._export_scan_times(observation, {"source_name": "1228+126"})


def test_distinct_lists_what_fills_a_combo_box(project):
    """The other question every visualization tab asked for itself: which sources are in this
    result, which baselines. Each copy read the frame, checked the schema and called unique()."""
    manipulator = ScheduleManipulator(project)
    observation = project.get_observation(next(iter(project.get_items())))

    response = manipulator.export(obj=observation, method="distinct", key="uv_coverage",
                                  columns=["source_name", "baseline"], raise_on_error=False)
    result = response["result"] if isinstance(response, dict) and "status" in response else response

    assert result["source_name"] == ["1228+126"]
    assert result["baseline"] == ["ALMA-APEX"]


def test_a_column_that_is_not_there_comes_back_empty(project):
    """Empty rather than missing, so a caller filling a list needs no second check."""
    manipulator = ScheduleManipulator(project)
    observation = project.get_observation(next(iter(project.get_items())))

    response = manipulator.export(obj=observation, method="distinct", key="uv_coverage",
                                  columns=["source_name", "telescope_code"], raise_on_error=False)
    result = response["result"] if isinstance(response, dict) and "status" in response else response

    assert result["source_name"], "the column that exists still answers"
    assert result["telescope_code"] == []
