# p_dialog_vex_report.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QHeaderView, QTableWidgetItem

from msb_arch.utils.logging_setup import logger

from pastrocore.gui.ui_dialog_vex_report import Ui_VEXReportDialog


class VEXReportDialog(QDialog):
    """What was written, and what the file leaves for a station to fill in.

    Args:
        report (dict): What `vex(method="export")` returned. Every field shown here is in it;
            nothing is worked out again.
        parent (QWidget): The window this belongs to.

    Notes:
        - **This is not a courtesy dialog.** A VEX file written here is complete in shape and
          partial in content on purpose, and someone has to finish it. Telling them so at the
          moment they write it, by name, is the difference between that being a workflow and
          being a surprise at a correlator.
        - The rows come from the report, which is made from the same declaration the file's
          empty blocks are written from. A list here would be a second copy to keep in step.
    """

    COLUMNS = ["Block", "What it needs"]

    def __init__(self, report: dict, parent=None):
        super().__init__(parent)
        self.ui = Ui_VEXReportDialog()
        self.ui.setupUi(self)
        self._report = report or {}
        self._fill()
        self.ui.pushButtonClose.clicked.connect(self.accept)
        self.ui.pushButtonCopy.clicked.connect(self.copy_to_clipboard)

    def _fill(self):
        """Put the summary above the table and the outstanding blocks in it."""
        report = self._report
        headline = (f"{report.get('scans', 0)} scan(s), "
                    f"{len(report.get('stations') or [])} station(s), "
                    f"{len(report.get('modes') or [])} mode(s), "
                    f"{report.get('channels', 0)} channel(s)")
        if report.get("excluded"):
            headline += f"  ·  {len(report['excluded'])} left out"
        self.ui.labelSummary.setText(headline)
        self.ui.labelPath.setText(str(report.get("path", "")))

        rows = list(report.get("to_complete") or [])
        rows += [{"block": entry.get("telescope") or entry.get("scan") or "",
                  "needs": f"left out: {entry.get('reason', '')}"}
                 for entry in report.get("excluded") or []]

        self.ui.tableOutstanding.setColumnCount(len(self.COLUMNS))
        self.ui.tableOutstanding.setHorizontalHeaderLabels(self.COLUMNS)
        self.ui.tableOutstanding.setRowCount(len(rows))
        for index, row in enumerate(rows):
            for column, value in enumerate((row.get("block", ""), row.get("needs", ""))):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.ui.tableOutstanding.setItem(index, column, item)

        header = self.ui.tableOutstanding.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.ui.tableOutstanding.resizeRowsToContents()
        logger.debug("VEX report shown with %s outstanding item(s)", len(rows))

    def as_text(self) -> str:
        """Return the report as plain text, to send with the file."""
        report = self._report
        lines = [self.ui.labelSummary.text(), str(report.get("path", "")), ""]
        lines += [f"{row.get('block', ''):<20} {row.get('needs', '')}"
                  for row in report.get("to_complete") or []]
        for entry in report.get("excluded") or []:
            lines.append(f"{entry.get('telescope') or entry.get('scan') or '':<20} "
                         f"left out: {entry.get('reason', '')}")
        return "\n".join(lines)

    def copy_to_clipboard(self):
        """Put the report on the clipboard."""
        QApplication.clipboard().setText(self.as_text())
        logger.debug("VEX report copied to the clipboard")
