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
from typing import Any, Dict, List

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QHeaderView, QLineEdit, QListWidgetItem,
                               QTableWidgetItem, QWidget)
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
    QUESTIONS = (("summary", "The numbers -- min, max, mean, range"),
                 ("windows", "Windows -- runs of a true/false column"),
                 ("coverage", "Coverage -- across stations, at once"))

    #: Columns of an answer that name what a row is about, for the interval summary line.
    SUBJECTS = ("source_name", "target_code", "telescope_code", "baseline")

    def __init__(self, manipulator, parent=None):
        super().__init__(parent)
        self.ui = Ui_AnalysisTab()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self.described: Dict[str, Any] = {}
        self._filter_widgets: Dict[str, QComboBox] = {}

        for name, label in self.QUESTIONS:
            self.ui.questionCombo.addItem(label, name)

        self.ui.questionCombo.currentIndexChanged.connect(self._question_changed)
        self.ui.resultCombo.currentIndexChanged.connect(self._result_changed)
        self.ui.askButton.clicked.connect(self.ask)
        self.ui.refreshButton.clicked.connect(self.refresh)

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
            self.ui.resultCombo.addItem(f"{key}  ({self.described[key]['rows']} rows)", key)
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

        for column, values in sorted((entry.get("values") or {}).items()):
            box = QComboBox()
            box.addItem("any", None)
            for value in values:
                box.addItem(str(value), value)
            self.ui.filtersForm.addRow(column, box)
            self._filter_widgets[column] = box

        # A range per numeric column: "baselines longer than 5000", "elevation above 20".
        # Left blank means unbounded at that end, which is why these are line edits rather
        # than spin boxes -- a spin box has no way to mean "no limit".
        for column in entry.get("numeric", []):
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            low, high = QLineEdit(), QLineEdit()
            low.setPlaceholderText("from")
            high.setPlaceholderText("to")
            for edit in (low, high):
                edit.setValidator(QDoubleValidator())
                layout.addWidget(edit)
            self.ui.filtersForm.addRow(column, row)
            self._range_widgets[column] = (low, high)

        self._show_what_this_question_needs()

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
            return

        self._show(answer.value or [], question)

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
