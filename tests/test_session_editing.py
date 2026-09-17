"""Cutting a session down to what is worth repeating (S1).

A session is every request the window made, and most of them are questions: `stale` after every
edit, `catalogue` whenever a dialog opens, a getter for every cell of a table. What is worth
repeating is what changed something. So the rows say whether they only read, a person removes
the rest, and what is saved is what is left -- while the journal keeps all of it, because what the
window asked is what a bug report needs.

Whether a request reads is said by its operation's name. That took two changes to be true:
msb_arch 3.0 made `inspect` call nothing that is not named as a read, and the questions this
application asks of itself moved from `compute` and `export` to `inspect`.
"""
import json

import pytest

from pastrocore.super.schedule_manipulator import ScheduleManipulator

#: What an operation name promises, one row per kind, as the manipulator documents it.
CHANGES = ScheduleManipulator.CHANGING
FILES = {"save", "load", "export", "vex", "cfx"}


@pytest.fixture
def core(project):
    return ScheduleManipulator(project, journal_limit=1000)


@pytest.fixture
def asked(core, project):
    """A short session of questions and one change, in that order."""
    observation = project.get_observations()[0]
    sources = observation.get_sources()
    first = sources.get_items()[0].name
    core.inspect(obj=project, get_observations=None)
    core.inspect(obj=observation, method="stale")
    core.configure(sources, deactivate_item=first)
    core.inspect(obj=project, method="catalogue")
    return observation, first


def test_every_operation_is_one_kind_by_its_name(core):
    """Each registered operation reads, changes the project or writes a file -- and the reading
    ones are exactly what `reads` says. A new operation fails this until it is placed."""
    registered = set(core.describe_operations())

    assert ScheduleManipulator.READING | CHANGES | FILES >= registered, (
        f"not placed: {sorted(registered - ScheduleManipulator.READING - CHANGES - FILES)}")
    assert ScheduleManipulator.READING <= registered, "a reading operation nobody registers"
    assert all(core.reads(operation) for operation in ScheduleManipulator.READING)
    assert not any(core.reads(operation) for operation in CHANGES | FILES)


def test_a_question_is_asked_of_inspect_and_nothing_else_is(core):
    """`compute` held six questions beside the calculations, and `export` four beside what writes
    files, so a session could not tell a question from a change by its operation."""
    described = core.describe_operations()

    assert set(described["compute"]) == {"run", "clear", "release", "replay"}
    assert {"catalogue", "history", "check", "order", "plan", "stale", "targets", "affected",
            "available", "distinct", "scan_times", "unsaved"} <= set(described["inspect"])
    assert not {"available", "distinct", "scan_times", "unsaved"} & set(described["export"])


def test_every_row_says_whether_it_only_reads_and_what_it_called(core, project, asked):
    """`call` is the handler when one was named and the model's methods otherwise. The table's
    Method column showed the handler alone, which is empty for a `get` or a `deactivate_item`."""
    rows = core.inspect(obj=project, method="history")

    kinds = [(row["operation"], row["call"], row["reads"]) for row in rows]
    assert kinds[:4] == [("inspect", "get_observations", True), ("inspect", "stale", True),
                         ("configure", "deactivate_item", False),
                         ("inspect", "catalogue", True)], kinds


def test_adding_an_observation_shows_what_it_called_and_saves_as_recorded(core, project, tmp_path):
    """Reported from use: the row read `configure  Untitled Project  Untitled Project` with the
    Method column empty, while the saved file named `create_item`. Both were right -- `method` is
    the operation's handler, and none was named -- and the table was the one saying nothing."""
    core.configure(project, create_item={"item_code": "OBS_ADDED", "isactive": True,
                                         "observation_type": "VLBI"})
    row = next(row for row in reversed(core.inspect(obj=project, method="history"))
               if row["operation"] == "configure")
    path = tmp_path / "session.json"
    core.export(obj=project, method="journal", path=str(path), steps=[row])

    assert (row["operation"], row["call"]) == ("configure", "create_item")
    saved = json.loads(path.read_text(encoding="utf-8"))["steps"][0]
    assert saved["method"] is None, "the file is the request as it was recorded"
    assert "create_item" in saved["attributes"] and "call" not in saved


def test_a_saved_session_is_the_rows_it_was_given(core, project, asked, tmp_path):
    """And the journal still holds all of them."""
    rows = core.inspect(obj=project, method="history")
    changes = [row for row in rows if not row["reads"]]
    recorded = len(core.get_journal())
    path = tmp_path / "cut.json"

    written = core.export(obj=project, method="journal", path=str(path), steps=changes)

    saved = json.loads(path.read_text(encoding="utf-8"))["steps"]
    assert written["steps"] == len(changes) == 1
    assert [step["operation"] for step in saved] == ["configure"]
    assert not {"where", "reads", "call"} & set(saved[0]), "what the table added reached the file"
    assert len(core.get_journal()) > recorded, "the journal lost what was cut from the file"


def test_a_replay_does_not_ask_questions_again(core, project, asked, tmp_path):
    """A question changes nothing, so asking it again reproduces nothing."""
    observation, first = asked
    path = tmp_path / "session.json"
    core.export(obj=project, method="journal", path=str(path))
    core.configure(observation.get_sources(), activate_item=first)

    outcome = core.compute(obj=project, method="replay", path=str(path))

    assert outcome["problems"] == []
    assert outcome["reads"] >= 3
    assert len(outcome["ran"]) == 1
    assert observation.get_sources().get(first).isactive is False, "the change was not replayed"


def test_a_session_written_before_the_questions_moved_still_replays(core, project, asked, tmp_path):
    """A file from 1.12 asks `compute` for `catalogue` and `export` for `unsaved`. Refusing it
    whole over two questions would lose the change in it."""
    observation, first = asked
    change = next(row for row in core.inspect(obj=project, method="history") if not row["reads"])
    path = tmp_path / "old.json"
    path.write_text(json.dumps({"steps": [
        {"operation": "compute", "method": "catalogue", "attributes": {}, "status": True},
        # As the window recorded it: a facade call keeps the handler among the attributes.
        {"operation": "export", "method": None, "attributes": {"method": "unsaved"}, "status": True},
        {key: value for key, value in change.items() if key not in ("where", "reads", "call")},
    ]}), encoding="utf-8")
    core.configure(observation.get_sources(), activate_item=first)

    checked = core.inspect(obj=project, method="check", path=str(path))
    outcome = core.compute(obj=project, method="replay", path=str(path))

    assert checked["problems"] == [], checked
    assert outcome["reads"] == 2 and len(outcome["ran"]) == 1
    assert observation.get_sources().get(first).isactive is False


# --- the dialog -----------------------------------------------------------------------------------

@pytest.fixture
def dialog(qt_application, core, asked):
    from pastrocore.gui.p_dialog_session import SessionDialog

    shown = SessionDialog(core)
    yield shown
    shown.close()
    shown.deleteLater()


def operations(dialog):
    table = dialog.ui.tableRequests
    return [table.item(row, 0).text() for row in range(table.rowCount())]


def test_the_dialog_shows_only_what_changed_something_when_asked(dialog):
    assert "inspect" in operations(dialog), "everything is shown until asked otherwise"

    dialog.ui.checkBoxChangesOnly.setChecked(True)

    assert operations(dialog) == ["configure"]
    assert dialog.ui.tableRequests.item(0, 3).text() == "deactivate_item", "the Call column is empty"
    assert "1 shown and saved" in dialog.ui.labelSummary.text()


def test_removed_rows_are_left_out_of_the_file_and_come_back_when_restored(
        dialog, core, tmp_path, monkeypatch):
    from PySide6.QtCore import QItemSelectionModel
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    table = dialog.ui.tableRequests
    assert not dialog.ui.pushButtonRemove.isEnabled(), "Remove is offered with nothing selected"
    everything = table.rowCount()
    for row in (0, 1):
        table.selectionModel().select(table.model().index(row, 0),
                                      QItemSelectionModel.Select | QItemSelectionModel.Rows)
    assert dialog.ui.pushButtonRemove.isEnabled()

    dialog.ui.pushButtonRemove.click()
    assert table.rowCount() == everything - 2
    assert dialog.ui.pushButtonRestore.isEnabled()

    path = tmp_path / "cut.json"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(path), ""))
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
    dialog.ui.pushButtonSave.click()
    assert len(json.loads(path.read_text(encoding="utf-8"))["steps"]) == everything - 2

    dialog.ui.pushButtonRestore.click()
    assert table.rowCount() == everything
