# p_dialog_schedule_export.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QHeaderView, QTableWidgetItem

from msb_arch.utils.logging_setup import logger

from pastrocore.gui.ui_dialog_schedule_export import Ui_ScheduleExportDialog


class ScheduleExportDialog(QDialog):
    """What was written, and what the file leaves for somebody else to fill in.

    Args:
        report (dict): What `vex(method="export")` or `cfx(method="export")` returned. Every
            field shown here is in it; nothing is worked out again.
        label (str): The format, for the title.
        parent (QWidget): The window this belongs to.

    Notes:
        - **This is not a courtesy dialog.** A file written here is complete in shape and
          partial in content on purpose, and someone has to finish it -- a station for VEX, the
          correlator for CFX. Saying so by name, at the moment it is written, is the difference
          between that being a workflow and being a surprise months later.
        - One dialog for both formats. They differ in which sections are outstanding and who
          completes them, and both answer that in the same `to_complete` field -- so a second
          dialog would be a second copy of this table.
        - The rows come from the report, which is made from the same declaration the file's
          empty sections are written from. A list here would be a second copy to keep in step.
    """

    COLUMNS = ["Block", "What it needs"]

    def __init__(self, report: dict, label: str = "Schedule", parent=None):
        super().__init__(parent)
        self.ui = Ui_ScheduleExportDialog()
        self.ui.setupUi(self)
        self._report = report or {}
        self.setWindowTitle(f"{label} Written")
        self._fill()
        self.ui.pushButtonClose.clicked.connect(self.accept)
        self.ui.pushButtonCopy.clicked.connect(self.copy_to_clipboard)

    def _fill(self):
        """Put the summary above the table and the outstanding sections in it."""
        report = self._report
        headline = (f"{report.get('scans', 0)} scan(s), "
                    f"{len(report.get('stations') or [])} station(s), "
                    f"{report.get('channels', 0)} channel(s)")
        if report.get("spacecraft"):
            headline += f"  ·  {', '.join(report['spacecraft'])} in orbit"
        if report.get("modes"):
            headline += f"  ·  {len(report['modes'])} mode(s)"
        if report.get("excluded"):
            headline += f"  ·  {len(report['excluded'])} left out"
        self.ui.labelSummary.setText(headline)

        files = report.get("files")
        self.ui.labelPath.setText("\n".join(one["path"] for one in files) if files
                                  else str(report.get("path", "")))

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
        logger.debug("Export report shown with %s outstanding item(s)", len(rows))

    def as_text(self) -> str:
        """Return the report as plain text, to send with the file."""
        report = self._report
        lines = [self.ui.labelSummary.text(), self.ui.labelPath.text(), ""]
        lines += [f"{row.get('block', ''):<20} {row.get('needs', '')}"
                  for row in report.get("to_complete") or []]
        for entry in report.get("excluded") or []:
            lines.append(f"{entry.get('telescope') or entry.get('scan') or '':<20} "
                         f"left out: {entry.get('reason', '')}")
        return "\n".join(lines)

    def copy_to_clipboard(self):
        """Put the report on the clipboard."""
        QApplication.clipboard().setText(self.as_text())
        logger.debug("Export report copied to the clipboard")
