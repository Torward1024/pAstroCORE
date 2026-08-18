# p_dialog_session.py
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QDialog, QFileDialog, QHeaderView, QMessageBox,
                               QTableWidgetItem)

from msb_arch.utils.logging_setup import logger

from pastrocore.gui.ui_dialog_session import Ui_SessionDialog

#: How an outcome is painted. The words come from the operation; this is only the colour.
COLOURS = {True: "#2e7d32", False: "#c62828"}


class SessionDialog(QDialog):
    """What has been asked of this project, and running a saved session again.

    Args:
        manipulator (ScheduleManipulator): The orchestrator every request goes through.
        parent (QWidget): The window this belongs to.

    Notes:
        - Everything shown here is what `compute(method="history")` returns, and everything the
          buttons do is one request each. The dialog holds the file chooser and the table, which
          is the whole of what an interface is for.
        - A session is portable because MSB records what was *asked* rather than the request as
          it ran: each row names its object instead of holding it. That is what makes a saved
          session replayable in a later run, and what stopped a journal from keeping alive
          every result it had recorded.
    """

    COLUMNS = ["Operation", "Object", "Where", "Method", "Seconds", "Outcome"]

    def __init__(self, manipulator, parent=None):
        super().__init__(parent)
        self.ui = Ui_SessionDialog()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self._fill()
        self.ui.pushButtonClose.clicked.connect(self.accept)
        self.ui.pushButtonSave.clicked.connect(self.save_session)
        self.ui.pushButtonReplay.clicked.connect(self.replay_session)

    def _ask(self, method, **attributes):
        """Send one request and hand back what it produced."""
        response = self.manipulator.compute(obj=self.manipulator.get_managing_object(),
                                            method=method, raise_on_error=False, **attributes)
        return response.value

    def _fill(self):
        """Put the session in the table."""
        rows = self._ask("history") or []
        failed = sum(1 for row in rows if not row.get("status"))
        spent = sum(row.get("seconds") or 0.0 for row in rows)
        headline = f"{len(rows)} request(s) in {spent:.2f} s"
        if failed:
            headline += f"  ·  {failed} failed"
        if not rows:
            headline = ("Nothing has been recorded. Recording is off in "
                        "Preferences, or nothing has been asked of this project yet.")
        self.ui.labelSummary.setText(headline)

        self.ui.tableRequests.setColumnCount(len(self.COLUMNS))
        self.ui.tableRequests.setHorizontalHeaderLabels(self.COLUMNS)
        self.ui.tableRequests.setRowCount(len(rows))
        for index, row in enumerate(rows):
            worked = bool(row.get("status"))
            cells = [row.get("operation") or "", row.get("object") or "",
                     row.get("where") or "", row.get("method") or "",
                     f"{row.get('seconds') or 0.0:.3f}",
                     "ok" if worked else (row.get("error") or "failed")]
            for column, value in enumerate(cells):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if column == 4:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if column == 5:
                    item.setForeground(QBrush(QColor(COLOURS[worked])))
                self.ui.tableRequests.setItem(index, column, item)

        header = self.ui.tableRequests.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        for column in (0, 1, 3, 4, 5):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        logger.debug("Session shown with %s request(s)", len(rows))

    def save_session(self):
        """Write the session to a file."""
        path, _ = QFileDialog.getSaveFileName(self, "Save session", "session.json",
                                              "Session (*.json)")
        if not path:
            return
        response = self.manipulator.export(obj=self.manipulator.get_managing_object(),
                                           method="journal", path=path, raise_on_error=False)
        result = response.value
        if not result:
            QMessageBox.critical(self, "Error", "The session could not be written.")
            return
        QMessageBox.information(self, "Saved",
                                f"{result['steps']} request(s) written to\n{result['path']}")

    def replay_session(self):
        """Read a saved session and run it against the project that is open now."""
        path, _ = QFileDialog.getOpenFileName(self, "Replay a session", "",
                                              "Session (*.json)")
        if not path:
            return

        outcome = self._ask("replay", path=path)
        if not outcome:
            QMessageBox.critical(self, "Error", "The session could not be replayed.")
            return

        # Unresolved steps are named rather than counted: a session that half ran is worse than
        # one that refused, and which step could not be placed is the whole diagnosis.
        summary = f"{len(outcome['ran'])} request(s) replayed"
        if outcome["failed"]:
            summary += f"\n{len(outcome['failed'])} failed"
        if outcome["unresolved"]:
            summary += ("\n\nNot in this project:\n  "
                        + "\n  ".join(outcome["unresolved"][:10]))
        (QMessageBox.warning if outcome["failed"] or outcome["unresolved"]
         else QMessageBox.information)(self, "Replayed", summary)
        self._fill()
