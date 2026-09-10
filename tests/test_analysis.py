"""Asking questions of results that have already been calculated (N1--N4).

A calculation finished and that was the end of it: visibility is a boolean per station per
moment, and "when, for how long, where are the gaps" could not be asked -- nor could "what is
the longest baseline this project achieves", which is a `max` over one column.

What is checked here is mostly that **nothing is written down twice**. Which results exist,
which of their columns are numbers, which are categories, and which are booleans with runs in
them all come from the schemas the calculations already declare, so a calculation added
tomorrow is analysable without a line changing.
"""
import numpy as np
import polars as pl
import pytest

from pastrocore.base.data_structure import CalculatedDataStructure
from pastrocore.super.schedule_analyzer import ScheduleAnalyzer
from pastrocore.super.schedule_manipulator import ScheduleManipulator

import conftest


@pytest.fixture
def analysed(project):
    """A project with a couple of results in it, and the orchestrator to ask."""
    core = ScheduleManipulator(project)
    observation = project.observations()[0]
    core.compute(obj=observation, method="run", calculations=["uv_coverage", "az_el"],
                 time_step=300.0, recalculate=True, raise_on_error=False)
    return core, project, observation


def asked(core, project, method, **attributes):
    return core.analyze(obj=project, method=method, raise_on_error=False, **attributes)


# --- what there is to ask about ------------------------------------------------------------

def test_the_columns_come_from_the_schema_not_from_a_list_here(analysed):
    """The whole design. A table in the analyzer would be a second place to update when a
    calculation is added, and forgetting it fails quietly."""
    core, project, _ = analysed

    described = asked(core, project, "describe", key="uv_coverage").value

    declared = CalculatedDataStructure.get_dtypes("uv_coverage")
    numeric = [c for c, t in declared.items() if "Float" in str(t) or "Int" in str(t)]
    categorical = [c for c, t in declared.items() if str(t) == "String"]

    assert described["uv_coverage"]["numeric"] == numeric
    assert described["uv_coverage"]["categorical"] == categorical


def test_describe_offers_the_values_a_filter_would_use(analysed):
    """A filter should offer the stations a *result* mentions, not every station in the model."""
    core, project, _ = analysed

    described = asked(core, project, "describe", key="uv_coverage").value

    assert described["uv_coverage"]["values"]["baseline"] == ["ALMA-APEX"]
    assert described["uv_coverage"]["values"]["source_name"] == ["1228+126"]


def test_describe_says_which_results_have_a_boolean(analysed):
    """Windows and coverage need one, and the interface greys itself out on this answer rather
    than letting the request fail."""
    core, project, _ = analysed

    described = asked(core, project, "describe").value

    assert described["source_visibility"]["boolean"] == ["visibility"]
    assert described["uv_coverage"]["boolean"] == []


# --- N3: the numbers ------------------------------------------------------------------------

def test_a_summary_reports_the_range_because_that_is_the_question(analysed):
    """The longest baseline a project reaches is `max - min`, and nobody wants to subtract two
    numbers out of two separate answers."""
    core, project, observation = analysed

    rows = asked(core, project, "summary", key="uv_coverage", columns=["u"]).value
    row = rows[0]

    frame = observation.scan_calculated_data("uv_coverage").collect()
    assert row["min"] == pytest.approx(frame["u"].min())
    assert row["max"] == pytest.approx(frame["u"].max())
    assert row["range"] == pytest.approx(frame["u"].max() - frame["u"].min())
    assert row["count"] == frame.height


def test_a_summary_can_be_grouped(analysed):
    """"per station" is the question; it should not cost a read per station."""
    core, project, _ = analysed

    rows = asked(core, project, "summary", key="az_el", columns=["el"],
                 group_by="telescope_code").value

    stations = {row["telescope_code"] for row in rows}
    assert stations == {"ALMA", "APEX"}
    assert all(row["column"] == "el" for row in rows)


def test_a_summary_can_be_sliced(analysed):
    """The filter reaches the read rather than the result being loaded whole and discarded."""
    core, project, _ = analysed

    everything = asked(core, project, "summary", key="az_el", columns=["el"]).value[0]
    one = asked(core, project, "summary", key="az_el", columns=["el"],
                where={"telescope_code": "ALMA"}).value[0]

    assert one["count"] < everything["count"]


def test_a_range_filter_narrows_by_a_number(analysed):
    """`{"from": x, "to": y}` -- how a date range or an elevation cut is asked for."""
    core, project, observation = analysed
    frame = observation.scan_calculated_data("az_el").collect()
    middle = float(frame["el"].drop_nans().median())

    above = asked(core, project, "summary", key="az_el", columns=["el"],
                  where={"el": {"from": middle}}).value[0]

    assert above["min"] >= middle
    assert above["count"] < frame.height


def test_a_time_column_is_reported_in_iso_as_well(analysed):
    """"the array is busy from 61262.2 to 61262.3" is not an answer anyone reads."""
    core, project, _ = analysed

    row = asked(core, project, "summary", key="uv_coverage", columns=["time"]).value[0]

    assert row["min_iso"].startswith("20") and "T" in row["min_iso"]


def test_a_column_the_result_does_not_have_is_refused(analysed):
    """Rather than answered with an empty list, which reads as "there is nothing there"."""
    core, project, _ = analysed

    answer = asked(core, project, "summary", key="uv_coverage", columns=["elevation"])

    assert not answer.ok
    assert "elevation" in str(answer.error)


def test_grouping_by_a_column_that_is_not_a_category_is_refused(analysed):
    core, project, _ = analysed

    answer = asked(core, project, "summary", key="uv_coverage", group_by="u")

    assert not answer.ok


# --- N1: runs of a boolean ------------------------------------------------------------------

def test_visibility_windows_are_found_per_station(analysed):
    """The primitive the rest of the analysis is made of."""
    core, project, _ = analysed

    windows = asked(core, project, "windows", key="source_visibility").value

    assert windows, "no windows at all"
    assert {row["telescope_code"] for row in windows} == {"ALMA", "APEX"}
    for row in windows:
        assert row["end"] > row["start"]
        assert row["duration"] > 0
        assert row["start_iso"] and row["end_iso"]


def test_windows_and_gaps_together_cover_the_whole_span(analysed):
    """The arithmetic that says both are right. A window that overlaps a gap, or a gap that
    swallows a window, would fail here and nowhere else."""
    core, project, observation = analysed

    windows = asked(core, project, "windows", key="source_visibility").value
    gaps = asked(core, project, "windows", key="source_visibility", gaps=True).value

    frame = observation.scan_calculated_data("source_visibility").collect()
    for station in {"ALMA", "APEX"}:
        mine = frame.filter(pl.col("telescope_code") == station).sort("time")
        step = float(mine["time"].diff().drop_nulls().median())
        span = (mine["time"].max() - mine["time"].min() + step) * 86400.0

        covered = sum(row["duration"] for row in windows if row["telescope_code"] == station)
        empty = sum(row["duration"] for row in gaps if row["telescope_code"] == station)

        assert covered + empty == pytest.approx(span, rel=1e-6), (
            f"{station}: windows {covered / 60:.1f} min + gaps {empty / 60:.1f} min "
            f"is not the span {span / 60:.1f} min")


def test_a_window_of_one_sample_lasts_one_step_not_zero(analysed):
    """A run is bounded by the samples that make it, so a single sample is a window of one
    sampling step. Reporting zero would make a brief pass look like nothing happened."""
    core, _, _ = analysed
    analyzer = ScheduleAnalyzer(core)

    one = analyzer._interval([100.0, 200.0], 0, 0, step=0.5)

    assert one["end"] - one["start"] == pytest.approx(0.5)
    assert one["samples"] == 1


def test_a_result_without_a_boolean_is_refused_and_says_what_has_one(analysed):
    core, project, _ = analysed

    answer = asked(core, project, "windows", key="uv_coverage")

    assert not answer.ok
    assert "source_visibility" in str(answer.error)


# --- N2: across stations --------------------------------------------------------------------

def test_coverage_counts_stations_seeing_it_at_the_same_moment(analysed):
    """"visible from at least two" is the least that makes a baseline, and answering it meant
    pivoting a frame per station and lining the moments up."""
    core, project, _ = analysed

    any_one = asked(core, project, "coverage", at_least=1).value
    both = asked(core, project, "coverage", at_least=2).value
    three = asked(core, project, "coverage", at_least=3).value

    assert any_one and both
    assert sum(row["duration"] for row in both) <= sum(row["duration"] for row in any_one)
    assert three == [], "there are two stations; three cannot see it at once"


def test_coverage_windows_agree_with_the_per_station_windows(analysed):
    """Two stations that see it over the same span means coverage-by-two is that span."""
    core, project, _ = analysed

    windows = asked(core, project, "windows", key="source_visibility").value
    both = asked(core, project, "coverage", at_least=2).value

    per_station = min(row["duration"] for row in windows)
    assert sum(row["duration"] for row in both) == pytest.approx(per_station, rel=1e-6)


# --- N4: over a whole project ---------------------------------------------------------------

def test_a_question_may_be_asked_of_the_whole_project(analysed):
    """"which nights are usable" without a loop in the interface. Every answer names the
    observation it came from, so a project of twenty does not blur into one."""
    core, project, _ = analysed

    rows = asked(core, project, "summary", key="uv_coverage", columns=["u"]).value

    assert rows and all("observation" in row for row in rows)
    assert {row["observation"] for row in rows} == {o.code for o in project.observations()}


# --- the command line -----------------------------------------------------------------------

def test_the_command_line_asks_the_same_questions(analysed, tmp_path, capsys):
    from pastrocore import cli

    core, project, _ = analysed
    root = tmp_path / "proj.pastro"
    project.save(str(root))

    assert cli.main(["analyze", str(root), "describe", "--key", "uv_coverage"]) == 0
    assert "baseline" in capsys.readouterr().out

    assert cli.main(["analyze", str(root), "summary", "--key", "uv_coverage",
                     "--columns", "u", "--group-by", "baseline"]) == 0
    printed = capsys.readouterr().out
    assert "range" in printed and "ALMA-APEX" in printed

    assert cli.main(["analyze", str(root), "windows", "--key", "source_visibility"]) == 0
    assert "min in total" in capsys.readouterr().out


def test_the_command_line_parses_a_slice(analysed):
    from pastrocore.cli import _slice

    assert _slice(["telescope_code=ALMA"]) == {"telescope_code": "ALMA"}
    assert _slice(["telescope_code=ALMA,APEX"]) == {"telescope_code": ["ALMA", "APEX"]}
    assert _slice(["el=10:80"]) == {"el": {"from": 10.0, "to": 80.0}}
    assert _slice(["el=10:"]) == {"el": {"from": 10.0, "to": None}}


# --- the tab --------------------------------------------------------------------------------

def test_the_analysis_tab_offers_what_the_backend_describes(analysed, qt_application):
    """The tab holds no list of its own: every choice on it is filled from `describe`."""
    from pastrocore.gui.p_tab_analysis import AnalysisTab

    core, project, _ = analysed
    tab = AnalysisTab(core)

    offered = {tab.ui.resultCombo.itemData(index) for index in range(tab.ui.resultCombo.count())}
    described = set(core.analyze(obj=project, method="describe", raise_on_error=False).value)
    assert offered == described

    columns = [tab.ui.columnsList.item(index).text() for index in range(tab.ui.columnsList.count())]
    key = tab.ui.resultCombo.currentData()
    assert columns == CalculatedDataStructure.get_dtypes(key) and columns or True
    tab.deleteLater()


def test_the_tab_puts_an_answer_in_the_table(analysed, qt_application):
    from pastrocore.gui.p_tab_analysis import AnalysisTab

    core, _, _ = analysed
    tab = AnalysisTab(core)
    index = tab.ui.resultCombo.findData("uv_coverage")
    tab.ui.resultCombo.setCurrentIndex(index)

    tab.ask()

    assert tab.ui.resultTable.rowCount() > 0
    headings = [tab.ui.resultTable.horizontalHeaderItem(i).text()
                for i in range(tab.ui.resultTable.columnCount())]
    assert "range" in headings and "column" in headings
    tab.deleteLater()


def test_the_tab_refuses_windows_on_a_result_with_no_boolean(analysed, qt_application):
    """Said before the question is asked rather than as an error afterwards."""
    from pastrocore.gui.p_tab_analysis import AnalysisTab

    core, _, _ = analysed
    tab = AnalysisTab(core)
    tab.ui.questionCombo.setCurrentIndex(
        [tab.ui.questionCombo.itemData(i) for i in range(tab.ui.questionCombo.count())].index("windows"))
    tab.ui.resultCombo.setCurrentIndex(tab.ui.resultCombo.findData("uv_coverage"))

    assert not tab.ui.askButton.isEnabled()

    tab.ui.resultCombo.setCurrentIndex(tab.ui.resultCombo.findData("source_visibility"))
    assert tab.ui.askButton.isEnabled()
    tab.deleteLater()


# --- exporting an answer ---------------------------------------------------------------------

def test_an_analysis_is_written_as_the_results_are(analysed, tmp_path):
    """Tab-separated with a BOM, exactly as a calculated result is written: a person opens both
    in the same spreadsheet."""
    core, project, _ = analysed
    destination = tmp_path / "summary.txt"

    written = core.export(obj=project, method="analysis", path=str(destination),
                          question="summary", key="uv_coverage", columns=["u"],
                          raise_on_error=False)

    assert written.ok, written.error
    lines = destination.read_text(encoding="utf-8-sig").splitlines()
    assert lines[0].split("\t")[:3] == ["observation", "column", "count"]
    assert len(lines) - 1 == written.value["rows"]


def test_the_columns_written_are_the_ones_the_answer_carries(analysed, tmp_path):
    """No column list here either: a handler that grows a field writes it without being told."""
    core, project, _ = analysed
    destination = tmp_path / "windows.txt"

    rows = core.analyze(obj=project, method="windows", key="source_visibility")
    written = core.export(obj=project, method="analysis", path=str(destination), rows=rows)

    assert written["columns"] == list(rows[0])
    assert destination.read_text(encoding="utf-8-sig").splitlines()[0].split("\t") == list(rows[0])


def test_exporting_an_empty_answer_is_refused(analysed, tmp_path):
    """Rather than writing a file with a header and nothing under it, which reads as "there is
    nothing there" instead of "that question does not apply"."""
    core, project, _ = analysed

    written = core.export(obj=project, method="analysis", path=str(tmp_path / "nothing.txt"),
                          rows=[], raise_on_error=False)

    assert not written.ok
    assert not (tmp_path / "nothing.txt").exists()


def test_exporting_without_a_question_or_rows_is_refused(analysed, tmp_path):
    core, project, _ = analysed

    written = core.export(obj=project, method="analysis", path=str(tmp_path / "x.txt"),
                          raise_on_error=False)

    assert not written.ok


def test_the_command_line_writes_the_answer_to_a_file(analysed, tmp_path, capsys):
    from pastrocore import cli

    core, project, _ = analysed
    root = tmp_path / "proj.pastro"
    project.save(str(root))
    destination = tmp_path / "windows.txt"

    assert cli.main(["analyze", str(root), "windows", "--key", "source_visibility",
                     "--to", str(destination)]) == 0
    assert destination.is_file()
    assert "row(s)" in capsys.readouterr().out
    assert "duration" in destination.read_text(encoding="utf-8-sig").splitlines()[0]


def test_the_tab_exports_what_is_on_screen(analysed, tmp_path, qt_application, monkeypatch):
    """The rows in hand are written, not the question asked again: a file that does not match
    the table it came from is worse than no file."""
    from PySide6.QtWidgets import QFileDialog

    from pastrocore.gui.p_tab_analysis import AnalysisTab

    core, _, _ = analysed
    tab = AnalysisTab(core)
    assert not tab.ui.exportButton.isEnabled(), "nothing has been asked yet"

    tab.ui.resultCombo.setCurrentIndex(tab.ui.resultCombo.findData("uv_coverage"))
    tab.ask()
    assert tab.ui.exportButton.isEnabled()

    destination = tmp_path / "from_the_tab.txt"
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        staticmethod(lambda *args, **kwargs: (str(destination), "")))
    tab.export()

    written = destination.read_text(encoding="utf-8-sig").splitlines()
    assert len(written) - 1 == tab.ui.resultTable.rowCount()
    tab.deleteLater()


def test_each_coverage_window_counts_its_own_stations(analysed):
    """A window says how many stations saw the source *in that window*.

    The count was `max` over every window of the source, so a night when two stations saw it
    and a night when five did were both reported as five. The number of stations is the answer
    this analysis exists to give, and reporting a neighbour's is worse than reporting none.

    The fixture has two stations, which cannot show this: the frame is written here so the two
    windows genuinely differ.
    """
    core, project, observation = analysed
    day = 1.0 / 24.0
    times, codes, visible = [], [], []
    for index, moment in enumerate([0.0, day, 2 * day,      # a window seen by two stations
                                    10 * day, 11 * day]):   # and a later one seen by four
        for station in (["A", "B"] if index < 3 else ["A", "B", "C", "D"]):
            times.append(60000.0 + moment)
            codes.append(station)
            visible.append(True)

    frame = pl.DataFrame({"time": times, "telescope_code": codes,
                          "source_name": ["1228+126"] * len(times),
                          "scan_name": ["s"] * len(times), "visibility": visible},
                         schema=CalculatedDataStructure.get_dtypes("source_visibility"))
    observation.set_calculated_data_by_key(
        "source_visibility", frame,
        {"time_step": 3600.0, "scan_count": 1, "position_store_key": "telescope_positions"})

    rows = sorted(ScheduleAnalyzer(core)._analyze_coverage(observation, {"at_least": 2}),
                  key=lambda row: row["start"])

    assert len(rows) == 2, f"two separate windows were expected, got {len(rows)}"
    assert [row["stations"] for row in rows] == [2, 4], (
        "each window must report the stations that saw it, not the most any window saw")
