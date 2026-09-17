"""Nothing but a save and a deliberate Clear Data changes what is in a project directory (R1).

Reported from use: result files going missing from a project directory, with nothing said. They
were: **File -> New Project deleted them**, and so did every File -> Open, out of the directory of
the project being replaced, after it had been saved.

The window lets go of a project through `compute(method="release")`, which reaches
`ScheduleProject.remove_all`, which asked each observation to `clear_calculated_data` -- and that
erases the results on disk as well as in memory. Letting go of a project in order to open another
one is not a decision to delete a day of calculation.

So this walks a session the way it is worked and checks, at every step, that every result the
project says it has is a file with bytes in it -- and that the two things that are *meant* to remove
a file still do.
"""
import json
import pathlib

import pytest

from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject


def claimed(project):
    """What the project says it holds: observation name -> result keys."""
    return {observation.name: sorted(observation.calculated_data.keys())
            for observation in project.get_observations()}


def on_disk(root):
    """What the directory actually holds: owner -> result keys whose files have bytes."""
    results = pathlib.Path(root) / ScheduleProject.RESULTS_DIRECTORY
    if not results.is_dir():
        return {}
    return {owner.name: sorted(entry.stem for entry in owner.glob("*.parquet")
                               if entry.stat().st_size > 0)
            for owner in sorted(path for path in results.iterdir() if path.is_dir())}


def nothing_missing(project, root, step):
    said, there = claimed(project), on_disk(root)
    missing = {owner: [key for key in keys if key not in there.get(owner, [])]
               for owner, keys in said.items()}
    missing = {owner: keys for owner, keys in missing.items() if keys}
    assert not missing, f"{step}: the project claims results that are not on disk: {missing}"
    assert sum(len(keys) for keys in said.values()), f"{step}: nothing to check"


@pytest.fixture
def calculated(project, tmp_path):
    """A project saved to a directory, with results in it, and the orchestrator that saved it."""
    core = ScheduleManipulator(project)
    project.hold_results_in_scratch()
    core.compute(obj=None, method="run", targets=project.get_observations(),
                 calculations=["uv_coverage", "az_el"], time_step=600.0, recalculate=True)
    directory = tmp_path / "saved"
    core.save(obj=project, path=str(directory))
    nothing_missing(project, directory, "saved")
    return core, project, directory


# --- letting go of a project is not deleting it -------------------------------------------------------

def test_releasing_a_project_leaves_its_directory_alone(calculated):
    """The bug itself, at the level it happened: `release` is what a window runs to let go of a
    project before opening another, and it erased the results out of the saved directory."""
    core, project, directory = calculated
    before = on_disk(directory)

    core.compute(obj=project, method="release")

    assert on_disk(directory) == before, "letting go of the project deleted its results"
    assert not project.get_observations(), "the project was not let go of at all"


def test_removing_every_observation_does_not_reach_the_disk_either(calculated):
    """Removing one observation leaves its files until the next save; removing all of them was the
    one case that deleted immediately, through the same path."""
    core, project, directory = calculated
    before = on_disk(directory)

    core.configure(project, remove_all=None)

    assert on_disk(directory) == before, "removing the observations deleted their results"


def test_the_window_keeps_the_results_of_the_project_it_replaces(qt_application, project, tmp_path,
                                                                 monkeypatch):
    """End to end, where it was found: save, then File -> New Project, then File -> Open."""
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    from pastrocore.app import PAstroCoreMainWindow

    window = PAstroCoreMainWindow()
    window.project = project
    window.manipulator = ScheduleManipulator(project)
    project.hold_results_in_scratch()
    window.manipulator.compute(obj=None, method="run", targets=project.get_observations(),
                               calculations=["uv_coverage"], time_step=600.0, recalculate=True)

    directory = tmp_path / "saved"
    directory.mkdir()
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(directory)))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    try:
        window.save_project_as()
        saved = on_disk(directory)
        assert saved, "the window saved no results to begin with"

        window.new_project()
        assert on_disk(directory) == saved, "File -> New Project deleted the saved results"

        window._open_project_at(str(directory))
        nothing_missing(window.project, directory, "reopened")
        assert on_disk(directory) == saved, "opening it again changed what was on disk"
    finally:
        window.status.close()
        window.close()
        window.deleteLater()
        qt_application.processEvents()


# --- what is still meant to remove a file ---------------------------------------------------------------

def test_clear_data_still_deletes_the_results_it_is_asked_to(calculated):
    """The deliberate one: Clear Data in the calculation dialog means delete them."""
    core, project, directory = calculated

    core.compute(obj=project, method="clear")

    assert not any(on_disk(directory).values()), "Clear Data left the results on disk"
    assert not any(claimed(project).values()), "the project still claims results it cleared"


def test_a_save_drops_the_results_of_an_observation_the_project_no_longer_has(calculated):
    """Otherwise renaming an observation away and back would find stale results and treat them as
    fresh. The save is where the disk catches up with the model."""
    core, project, directory = calculated
    removed = project.get_observations()[0]

    core.configure(obj=project, remove_item=removed.name)
    core.save(obj=project, path=str(directory))

    assert removed.name not in on_disk(directory)


# --- the walk the roadmap asked for ------------------------------------------------------------------------

def test_a_session_of_ordinary_work_loses_nothing(project, tmp_path):
    """Save, calculate, save, change a code, save elsewhere, reopen, remove one, save, let go."""
    core = ScheduleManipulator(project)
    project.hold_results_in_scratch()
    core.compute(obj=None, method="run", targets=project.get_observations(),
                 calculations=["uv_coverage", "az_el"], time_step=600.0, recalculate=True)

    first, second = tmp_path / "first", tmp_path / "second"
    core.save(obj=project, path=str(first))
    nothing_missing(project, first, "1. saved")

    core.compute(obj=None, method="run", targets=project.get_observations(),
                 calculations=["sun_angles"], time_step=600.0, recalculate=False)
    core.save(obj=project, path=str(first))
    nothing_missing(project, first, "2. calculated again and saved")

    # the code a user edits is not the name the results are filed under
    core.configure(obj=project.get_observations()[0], set={"params": {"code": "RENAMED"}})
    core.save(obj=project, path=str(first))
    nothing_missing(project, first, "3. code changed and saved")

    core.save(obj=project, path=str(second))
    nothing_missing(project, second, "4. saved elsewhere")
    nothing_missing(project, first, "5. and the first directory is untouched")

    reopened = ScheduleProject.open(str(second))
    nothing_missing(reopened, second, "6. reopened")
    assert json.loads((second / ScheduleProject.MODEL_FILE).read_text(encoding="utf-8"))["items"]

    core.compute(obj=project, method="release")
    nothing_missing(reopened, second, "7. after the first project was let go of")
    nothing_missing(ScheduleProject.open(str(first)), first, "8. and the first is still readable")


# --- and the scratch a save has copied out of ---------------------------------------------------------

def test_a_save_takes_the_scratch_copies_with_it(project, tmp_path):
    """`migrate_to` copies rather than moves -- a save that fails half way must leave the results
    where they were -- and nothing cleared the copies afterwards. `unsaved_results` counts what is in
    the scratch, so a saved project went on reporting every result as unsaved for the rest of the
    session: the recovery offer at the next start, and the question on closing, were about results
    that were safely in the project directory."""
    from pastrocore.base.scratch import ScratchSpace

    project._scratch = ScratchSpace(root=tmp_path / "scratch")
    project.hold_results_in_scratch()
    core = ScheduleManipulator(project)
    core.compute(obj=None, method="run", targets=project.get_observations(),
                 calculations=["uv_coverage"], time_step=600.0, recalculate=True)
    held = project.scratch.path
    assert project.unsaved_results() > 0, "nothing was calculated into the scratch"

    directory = tmp_path / "saved"
    core.save(obj=project, path=str(directory))

    assert project.unsaved_results() == 0, "a saved project still calls its results unsaved"
    assert not held.exists(), "the copies were left in the scratch"
    nothing_missing(project, directory, "saved")


def test_a_project_that_was_never_saved_keeps_what_it_calculated(project, tmp_path):
    """The other half of the rule: what has nowhere else to be is left where it is, so the next
    start can offer it back."""
    from pastrocore.base.scratch import ScratchSpace

    project._scratch = ScratchSpace(root=tmp_path / "scratch")
    project.hold_results_in_scratch()
    core = ScheduleManipulator(project)
    core.compute(obj=None, method="run", targets=project.get_observations(),
                 calculations=["uv_coverage"], time_step=600.0, recalculate=True)

    tidied = core.export(obj=project, method="tidy")

    assert tidied == {"discarded": False, "held": project.unsaved_results()}
    assert project.unsaved_results() > 0
    assert project.scratch.path.exists(), "results nobody has saved were thrown away"


def test_the_window_closes_after_a_save_without_asking_about_saved_results(qt_application, project,
                                                                          tmp_path, monkeypatch):
    """Reported shape: save, then close. The window asked about results that were already saved and,
    when told to save them again, refused to close -- the count it re-read never changed."""
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    from pastrocore.app import PAstroCoreMainWindow
    from pastrocore.base.scratch import ScratchSpace

    window = PAstroCoreMainWindow()
    window.project = project
    window.manipulator = ScheduleManipulator(project)
    project._scratch = ScratchSpace(root=tmp_path / "scratch")
    project.hold_results_in_scratch()
    window.manipulator.compute(obj=None, method="run", targets=project.get_observations(),
                               calculations=["uv_coverage"], time_step=600.0, recalculate=True)

    directory = tmp_path / "saved"
    directory.mkdir()
    asked = []
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(directory)))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: (asked.append(1), QMessageBox.StandardButton.Save)[1]))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    try:
        window.save_project_as()
        assert window._ask_what_is_unsaved() == 0

        closed = window.close()

        assert asked == [], "the window asked about results it had just saved"
        assert closed, "the window refused to close after saving"
        assert on_disk(directory), "closing took the saved results with it"
    finally:
        # Whatever the assertions said: a window left standing is closed again by the suite's
        # own teardown, and one that refuses to close is closed twice, which ends the process.
        window.project = None
        window.close()
        window.deleteLater()
        qt_application.processEvents()
