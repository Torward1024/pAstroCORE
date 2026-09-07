# gui/p_tab_analysis.py
"""The analysis tab: ask something of results that have already been calculated.

**It holds no list of anything.** Which results exist, which of their columns are numbers,
which are categories worth slicing by, which values those categories actually take, and which
results have a true-or-false column with runs in them are all answered by
`analyze(method="describe")`. A calculation added tomorrow appears here with its own columns
and nobody edits a combo box.

The layout is `tab_analysis.ui`, like every other form. What the form cannot hold is the
*contents* of those boxes -- they exist only once a project has been calculated -- and the
filter row, which is one combo per categorical column of whichever result is chosen.
"""
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QDateTime, Qt, Slot
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (QComboBox, QDateTimeEdit, QFileDialog, QHBoxLayout, QHeaderView,
                               QLineEdit, QListWidgetItem, QMessageBox, QTableWidgetItem,
                               QWidget)
from msb_arch.utils.logging_setup import logger

from pastrocore.gui.ui_tab_analysis import Ui_AnalysisTab


class AnalysisTab(QWidget):
    """Summaries, windows and coverage over one project's results.

    Args:
        manipulator (ScheduleManipulator): The orchestrator every question goes through.
        parent (QWidget): The window.
    """

    #: What can be asked. The labels are this module's; every *choice* inside them comes from
    #: `describe`, which is the difference between a tab that lists things and one that asks.
    QUESTIONS = (("summary", "Statistics (min, max, mean, range)"),
                 ("windows", "Time windows (and gaps)"),
                 ("coverage", "Coverage across stations"))

    #: Columns of an answer that name what a row is about, for the interval summary line.
    SUBJECTS = ("source_name", "target_code", "telescope_code", "baseline")

    #: Columns that are a moment rather than a plain number, and get a calendar instead of
    #: a text box. The same three the analyzer reports in ISO.
    TIME_COLUMNS = ("time", "start", "end")

    def __init__(self, manipulator, parent=None):
        super().__init__(parent)
        self.ui = Ui_AnalysisTab()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self.described: Dict[str, Any] = {}
        self._filter_widgets: Dict[str, QComboBox] = {}
        self._range_widgets: Dict[str, Any] = {}
        self._time_widgets: Dict[str, Any] = {}

        for name, label in self.QUESTIONS:
            self.ui.questionCombo.addItem(label, name)

        self.ui.questionCombo.currentIndexChanged.connect(self._question_changed)
        self.ui.resultCombo.currentIndexChanged.connect(self._result_changed)
        self.ui.askButton.clicked.connect(self.ask)
        self.ui.refreshButton.clicked.connect(self.refresh)
        self.ui.exportButton.clicked.connect(self.export)

        #: The answer on screen. Exporting writes *this* rather than asking again, so the file
        #: and the table cannot disagree about what was filtered.
        self._answer: List[Dict[str, Any]] = []

        self.refresh()

    # --- filling it from what the backend says ---------------------------------------------

    @Slot()
    def refresh(self):
        """Ask what there is to analyse, and offer exactly that."""
        project = self.manipulator.get_managing_object()
        if project is None:
            return

        answer = self.manipulator.analyze(obj=project, method="describe", raise_on_error=False)
        if not answer.ok:
            logger.error("Could not describe the results: %s", answer.error)
            self.ui.statusLabel.setText(f"Could not read the results: {answer.error}")
            self.described = {}
        else:
            self.described = answer.value or {}

        chosen = self.ui.resultCombo.currentData()
        self.ui.resultCombo.blockSignals(True)
        self.ui.resultCombo.clear()
        for key in sorted(self.described):
            entry = self.described[key]
            # The words the calculation dialog uses, not the store key: "Telescope
            # Visibility" rather than telescope_visibility.
            self.ui.resultCombo.addItem(
                f"{entry.get('label') or key}  ({entry['rows']:,} rows)", key)
        self.ui.resultCombo.blockSignals(False)

        if chosen:
            index = self.ui.resultCombo.findData(chosen)
            if index >= 0:
                self.ui.resultCombo.setCurrentIndex(index)

        if not self.described:
            self.ui.statusLabel.setText("Nothing has been calculated yet.")
        self._result_changed()

    @Slot()
    def _question_changed(self):
        self._show_what_this_question_needs()

    @Slot()
    def _result_changed(self):
        """Offer the columns and the filter values of whichever result is chosen."""
        entry = self.described.get(self.ui.resultCombo.currentData()) or {}

        self.ui.columnsList.clear()
        for column in entry.get("numeric", []):
            item = QListWidgetItem(column)
            item.setSelected(True)
            self.ui.columnsList.addItem(item)

        self.ui.groupByList.clear()
        for column in entry.get("categorical", []):
            self.ui.groupByList.addItem(QListWidgetItem(column))

        while self.ui.filtersForm.rowCount():
            self.ui.filtersForm.removeRow(0)
        self._filter_widgets = {}
        self._range_widgets = {}
        self._time_widgets = {}

        for column, values in sorted((entry.get("values") or {}).items()):
            box = QComboBox()
            box.addItem("any", None)
            for value in values:
                box.addItem(str(value), value)
            self.ui.filtersForm.addRow(column, box)
            self._filter_widgets[column] = box

        # A range per number, filled with the range that is actually there. An empty pair of
        # boxes makes a user guess what the numbers even look like; showing the span they
        # already have turns the filter into narrowing rather than searching.
        spans = entry.get("ranges") or {}
        for column in entry.get("numeric", []):
            span = spans.get(column)
            if column in self.TIME_COLUMNS:
                self._add_time_range(column, span)
            else:
                self._add_number_range(column, span)

        self._show_what_this_question_needs()

    def _add_number_range(self, column: str, span: Optional[Dict[str, float]]):
        """Two boxes, filled with the column's own span."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        low, high = QLineEdit(), QLineEdit()
        low.setPlaceholderText("from")
        high.setPlaceholderText("to")
        if span:
            low.setText(f"{span['min']:.6g}")
            high.setText(f"{span['max']:.6g}")
        for edit in (low, high):
            edit.setValidator(QDoubleValidator())
            layout.addWidget(edit)
        self.ui.filtersForm.addRow(column, row)
        self._range_widgets[column] = (low, high)

    def _add_time_range(self, column: str, span: Optional[Dict[str, float]]):
        """A pair of date-and-time pickers, spelled as the rest of the application spells time.

        Notes:
            - A moment is stored as an MJD, which is the right thing to compute with and the
              wrong thing to type: nobody knows what 61262.2083 is. These read
              `yyyy-MM-dd HH:mm:ss` with a calendar, the same as the scan editor, and convert.
        """
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        first, last = QDateTimeEdit(), QDateTimeEdit()
        for picker in (first, last):
            picker.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            picker.setCalendarPopup(True)
            layout.addWidget(picker)
        # The dates come written out by `describe`, and go back the same way: converting a
        # moment is model work, and the analyzer accepts a written date as a filter bound
        # precisely so that this does not have to know what an MJD is.
        if span and span.get("min_iso") and span.get("max_iso"):
            first.setDateTime(self._parse(span["min_iso"]))
            last.setDateTime(self._parse(span["max_iso"]))
        self.ui.filtersForm.addRow(column, row)
        self._time_widgets[column] = (first, last)

    @staticmethod
    def _parse(written: str) -> QDateTime:
        """An ISO moment as a Qt date and time."""
        return QDateTime.fromString(written.split(".")[0], "yyyy-MM-ddTHH:mm:ss")

    def _show_what_this_question_needs(self):
        """Show only the controls the chosen question uses, and say when it cannot be asked."""
        question = self.ui.questionCombo.currentData()
        entry = self.described.get(self.ui.resultCombo.currentData()) or {}

        numbers = question == "summary"
        for widget in (self.ui.columnsList, self.ui.columnsLabel,
                       self.ui.groupByList, self.ui.groupByLabel):
            widget.setVisible(numbers)
        self.ui.gapsCheck.setVisible(question == "windows")
        self.ui.atLeastSpin.setVisible(question == "coverage")
        self.ui.atLeastLabel.setVisible(question == "coverage")

        # A question that needs a boolean column cannot be asked of a result without one, and
        # saying so beforehand is better than an error afterwards.
        needs_boolean = question in ("windows", "coverage")
        possible = bool(entry.get("boolean")) if needs_boolean else bool(entry)
        self.ui.askButton.setEnabled(possible)
        if needs_boolean and entry and not possible:
            self.ui.statusLabel.setText(
                f"'{self.ui.resultCombo.currentData()}' has no true-or-false column; "
                f"windows and coverage need one.")

    # --- asking ---------------------------------------------------------------------------

    def _where(self) -> Dict[str, Any]:
        """Return the filters as chosen, leaving out the ones left open.

        Notes:
            - A range with both ends blank is not a filter and is left out; one end blank is
              unbounded there, which is how "longer than 5000" is said.
        """
        where: Dict[str, Any] = {
            column: box.currentData() for column, box in self._filter_widgets.items()
            if box.currentData() is not None}

        for column, (low, high) in getattr(self, "_range_widgets", {}).items():
            bounds = {}
            for name, edit in (("from", low), ("to", high)):
                text = edit.text().strip().replace(",", ".")
                if text:
                    try:
                        bounds[name] = float(text)
                    except ValueError:
                        logger.debug("Ignoring '%s' as a bound for %s", text, column)
            if bounds:
                where[column] = bounds

        for column, (first, last) in getattr(self, "_time_widgets", {}).items():
            where[column] = {"from": first.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
                             "to": last.dateTime().toString("yyyy-MM-dd HH:mm:ss")}
        return where

    @Slot()
    def ask(self):
        """Send the question and put the answer in the table."""
        project = self.manipulator.get_managing_object()
        key = self.ui.resultCombo.currentData()
        if project is None or not key:
            return

        question = self.ui.questionCombo.currentData()
        asked: Dict[str, Any] = {"key": key, "where": self._where()}
        if question == "summary":
            chosen = [item.text() for item in self.ui.columnsList.selectedItems()]
            asked["columns"] = chosen or None
            asked["group_by"] = [item.text() for item in self.ui.groupByList.selectedItems()]
        elif question == "windows":
            asked["gaps"] = self.ui.gapsCheck.isChecked()
        elif question == "coverage":
            asked["at_least"] = self.ui.atLeastSpin.value()

        answer = self.manipulator.analyze(obj=project, method=question, raise_on_error=False,
                                          **asked)
        if not answer.ok:
            logger.error("Analysis refused: %s", answer.error)
            self.ui.statusLabel.setText(str(answer.error))
            self.ui.resultTable.setRowCount(0)
            self._answer = []
            self.ui.exportButton.setEnabled(False)
            return

        self._answer = answer.value or []
        self.ui.exportButton.setEnabled(bool(self._answer))
        self._show(self._answer, question)

    @Slot()
    def export(self):
        """Write what is on screen to a tab-separated file.

        Notes:
            - The rows already in hand are what is written, rather than the question being
              asked again: a file that does not match the table it was exported from is worse
              than no file.
        """
        if not self._answer:
            return

        question = self.ui.questionCombo.currentData()
        suggested = f"{self.ui.resultCombo.currentData()}_{question}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Analysis", suggested, "Tab-separated text (*.txt);;All files (*)")
        if not path:
            return

        written = self.manipulator.export(
            obj=self.manipulator.get_managing_object(), method="analysis",
            path=path, rows=self._answer, raise_on_error=False)
        if not written.ok:
            logger.error("Could not export the analysis: %s", written.error)
            QMessageBox.critical(self, "Error", f"Could not write the file: {written.error}")
            return

        self.ui.statusLabel.setText(
            f"Wrote {written.value['rows']} row(s) to {written.value['path']}")

    def _show(self, rows: List[Dict[str, Any]], question: str):
        """Put a list of mappings in the table, with the columns they actually carry."""
        table = self.ui.resultTable
        if not rows:
            table.setRowCount(0)
            table.setColumnCount(0)
            self.ui.statusLabel.setText("Nothing to report for that.")
            return

        # The columns are whatever the answer has, in the order the first row gives them -- so
        # a handler that grows a field shows it here without this module being told.
        headings = list(rows[0])
        table.setColumnCount(len(headings))
        table.setHorizontalHeaderLabels(headings)
        table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            for column_index, heading in enumerate(headings):
                value = row.get(heading)
                if isinstance(value, float):
                    text = f"{value:,.4f}".rstrip("0").rstrip(".")
                else:
                    text = "" if value is None else str(value)
                item = QTableWidgetItem(text)
                if isinstance(value, (int, float)):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table.setItem(row_index, column_index, item)

        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        if question in ("windows", "coverage") and "duration" in headings:
            total = sum(row.get("duration") or 0.0 for row in rows) / 60.0
            longest = max((row.get("duration") or 0.0) for row in rows) / 60.0
            self.ui.statusLabel.setText(f"{len(rows)} interval(s), {total:,.1f} min in total, "
                                        f"longest {longest:,.1f} min")
        else:
            self.ui.statusLabel.setText(f"{len(rows)} row(s)")
