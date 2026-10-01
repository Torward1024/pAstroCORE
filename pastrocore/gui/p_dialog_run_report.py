# p_dialog_run_report.py
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QApplication, QDialog, QHeaderView, QTableWidgetItem

from msb_arch.utils.logging_setup import logger

from pastrocore.gui.ui_dialog_run_report import Ui_RunReportDialog

#: What the outcome of a step is shown as. The two words come from the operation; this is only
#: how they are painted.
COLOURS = {"ok": "#2e7d32", "failed": "#c62828"}


class RunReportDialog(QDialog):
    """What a calculation run did, step by step.

    Args:
        outcome (dict): What `compute(method="run")` returned -- `report`, a row per step, and
            `summary`. Both are assembled by the operation; nothing here works anything out.
        parent (QWidget): The window this belongs to.

    Notes:
        - One report rather than a message box and a line in `output.log`, and it stays
          reachable from Tools -> Last Run Report after the dialog is closed.
        - A failed step is in the table rather than only in the log, which is the whole point.
    """

    COLUMNS = ["Observation", "Calculation", "Seconds", "Outcome", "Why"]

    def __init__(self, outcome: dict, parent=None):
        super().__init__(parent)
        self.ui = Ui_RunReportDialog()
        self.ui.setupUi(self)
        self._outcome = outcome or {}
        self._fill()
        self.ui.pushButtonClose.clicked.connect(self.accept)
        self.ui.pushButtonCopy.clicked.connect(self.copy_to_clipboard)

    def _fill(self):
        """Put the report in the table and the summary above it."""
        rows = self._outcome.get("report") or []
        summary = self._outcome.get("summary") or {}

        failed = summary.get("failed", 0)
        # The clock, then the work: independent steps run together, so adding their
        # durations counts the same seconds twice. Both are shown when they differ.
        elapsed = summary.get("seconds", 0.0)
        work = summary.get("work", elapsed)
        headline = f"{summary.get('steps', len(rows))} calculation(s) in {elapsed:.2f} s"
        if work > elapsed * 1.05:
            headline += f"  ·  {work:.2f} s of work, {work / elapsed:.1f}x in parallel"
        if summary.get("slowest"):
            headline += (f"  ·  slowest {summary['slowest']} at "
                         f"{summary.get('slowest_seconds', 0.0):.2f} s")
        if failed:
            headline += f"  ·  {failed} failed"
        if self._outcome.get("cancelled"):
            headline += "  ·  cancelled"
        self.ui.labelSummary.setText(headline)

        self.ui.tableSteps.setColumnCount(len(self.COLUMNS))
        self.ui.tableSteps.setHorizontalHeaderLabels(self.COLUMNS)
        self.ui.tableSteps.setRowCount(len(rows))
        for index, row in enumerate(rows):
            cells = [row.get("observation", ""), row.get("label", row.get("step", "")),
                     f"{row.get('seconds', 0.0):.2f}", row.get("outcome", ""),
                     row.get("error", "")]
            for column, value in enumerate(cells):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if column == 2:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if colour := COLOURS.get(row.get("outcome")):
                    if column == 3:
                        item.setForeground(QBrush(QColor(colour)))
                self.ui.tableSteps.setItem(index, column, item)

        header = self.ui.tableSteps.horizontalHeader()
        # The reason a step refused is what a reader has come for, so it takes the room.
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        for column in (0, 1, 2, 3):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        logger.debug("Run report shown with %s step(s)", len(rows))

    def as_text(self) -> str:
        """Return the report as plain text, for pasting into a bug report."""
        lines = [self.ui.labelSummary.text(), ""]
        lines += [f"{row.get('observation', ''):<16} {row.get('label', ''):<28} "
                  f"{row.get('seconds', 0.0):>8.2f}  {row.get('outcome', '')}"
                  f"{'  ' + row['error'] if row.get('error') else ''}"
                  for row in self._outcome.get("report") or []]
        return "\n".join(lines)

    def copy_to_clipboard(self):
        """Put the report on the clipboard."""
        QApplication.clipboard().setText(self.as_text())
        logger.debug("Run report copied to the clipboard")
