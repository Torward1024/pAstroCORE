"""Which results a change would make wrong -- asked *before* the change (T4).

`stale` compares a stored fingerprint against the configuration in hand, so it can only ever
speak about a change that has already happened. A user about to move a telescope wants to know
what it will cost first.

Both halves of the answer are derived. MSB's model graph says what reaching a type reaches --
a `Telescope` is held by `Telescopes` and *named by* `Scan`, so editing one reaches scans too,
which is the part nobody remembers. Each calculation's schema says which parts it reads. The
intersection is the answer, and nothing about it is written down twice.
"""
import json

import pytest

from pastrocore.base.data_structure import CalculatedDataStructure
from pastrocore.super.schedule_manipulator import ScheduleManipulator
from pastrocore.super.schedule_project import ScheduleProject
from pastrocore.super.schedule_runner import ScheduleRunner

import conftest


@pytest.fixture
def core(project):
    return ScheduleManipulator(project)


def asked(core, project, **attributes):
    return core.compute(obj=project, method="affected", raise_on_error=False, **attributes)


def test_the_parts_of_the_model_are_read_from_the_model(core):
    """A table here would be a second place to update when the model grows a part -- and
    `calculated_data` is annotated `Any`, which answers True to `isinstance(hint, type)` on this
    Python and would otherwise appear as a part a change could reach."""
    parts = ScheduleRunner(core)._parts_by_type()

    assert parts == {"Sources": "sources", "Telescopes": "telescopes",
                     "Frequencies": "frequencies", "Scans": "scans"}


def test_editing_a_telescope_reaches_the_scans_that_name_it(core, project):
    """The part nobody remembers. A `Telescope` is held by `Telescopes`, and a `Scan` names the
    telescopes it uses -- so a change to one reaches scans, and `times` goes with it."""
    report = asked(core, project, type="Telescope").value

    assert report["parts"] == ["scans", "telescopes"]
    assert "times" in report["calculations"]


def test_editing_a_scan_does_not_reach_the_frequencies(core, project):
    """The other direction: `beam_pattern` reads telescopes and frequencies, so a scan cannot
    spoil it. An answer that named every calculation would be no answer."""
    report = asked(core, project, type="Scan").value

    assert report["parts"] == ["scans"]
    assert "beam_pattern" not in report["calculations"]


@pytest.mark.parametrize("named,parts", [
    ("Telescope", ["scans", "telescopes"]),
    ("SpaceTelescope", ["scans", "telescopes"]),
    ("Source", ["scans", "sources"]),
    ("IF", ["frequencies", "scans"]),
    ("Scan", ["scans"]),
])
def test_what_each_type_reaches(core, project, named, parts):
    assert asked(core, project, type=named).value["parts"] == parts


def test_an_object_may_be_given_instead_of_a_type_name(core, project):
    """A caller holding the thing it is about to edit should not have to name its class."""
    telescope = project.observations()[0].get_telescopes().get_items()[0]

    report = asked(core, project, subject=telescope).value

    assert report["type"] == "Telescope"
    assert report["parts"] == ["scans", "telescopes"]


def test_every_affected_calculation_actually_declares_that_part(core, project):
    """The claim, checked against the schemas rather than against a list."""
    report = asked(core, project, type="Source").value

    for key in report["calculations"]:
        declared = set(CalculatedDataStructure.get_dependencies(key))
        assert declared & set(report["parts"]), f"{key} does not read any of {report['parts']}"


def test_a_calculation_that_reads_none_of_the_parts_is_left_out(core, project):
    """Nothing is affected by everything; if it were, the answer would be useless."""
    report = asked(core, project, type="Scan").value

    for key in CalculatedDataStructure.SCHEMAS:
        reads = set(CalculatedDataStructure.get_dependencies(key))
        if not reads & {"scans"}:
            assert key not in report["calculations"]


def test_what_has_been_calculated_is_named_separately(core, project):
    """Which calculations *could* go stale is a property of the model; which ones *would* is a
    property of this project, and a user wants the second."""
    observation = project.observations()[0]
    observation.clear_calculated_data()

    before = asked(core, project, type="Telescope").value
    assert before["stored"] == [], "nothing has been calculated yet"

    core.compute(obj=observation, method="run", calculations=["uv_coverage"], time_step=600.0,
                 raise_on_error=False)

    after = asked(core, project, type="Telescope").value
    assert any(key.endswith("/uv_coverage") for key in after["stored"])
    assert after["calculations"] == before["calculations"], "the model did not change"


def test_a_type_the_model_does_not_have_is_refused(core, project):
    """Rather than answered with an empty list, which reads as "nothing would break"."""
    answer = asked(core, project, type="Nonsense")

    assert not answer.ok
    assert "Nonsense" in str(answer.error)


def test_asking_about_nothing_is_refused(core, project):
    answer = asked(core, project)

    assert not answer.ok
    assert "type" in str(answer.error)


def test_the_command_line_reports_it(project, tmp_path, capsys):
    """The second caller gets the same answer from the same request."""
    from pastrocore import cli

    root = tmp_path / "proj.pastro"
    project.save(str(root))

    assert cli.main(["affected", str(root), "Telescope"]) == 0
    printed = capsys.readouterr().out
    assert "telescopes" in printed and "uv_coverage" in printed


def test_the_command_line_refuses_a_type_that_is_not_there(project, tmp_path, capsys):
    from pastrocore import cli

    root = tmp_path / "proj.pastro"
    project.save(str(root))

    assert cli.main(["affected", str(root), "Nonsense"]) == 1
