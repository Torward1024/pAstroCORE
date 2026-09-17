# p_dialog_session.py
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QDialog, QFileDialog, QHeaderView, QMessageBox,
                               QTableWidgetItem)

from msb_arch.utils.logging_setup import logger

from pastrocore.gui.ui_dialog_session import Ui_SessionDialog

#: How an outcome is painted. The words come from the operation; this is only the colour.
COLOURS = {True: "#2e7d32", False: "#c62828"}

#: Where a row keeps its position in the session, so a removal survives a filter.
POSITION = Qt.UserRole


class SessionDialog(QDialog):
    """What has been asked of this project, cut down to what is worth repeating, and replayed.

    Args:
        manipulator (ScheduleManipulator): The orchestrator every request goes through.
        parent (QWidget): The window this belongs to.

    Notes:
        - Everything shown here is what `inspect(method="history")` returns, and everything the
          buttons do is one request each. The dialog holds the file chooser and the table, which
          is the whole of what an interface is for.
        - A session is portable because MSB records what was *asked* rather than the request as
          it ran: each row names its object instead of holding it. That is what makes a saved
          session replayable in a later run, and what stopped a journal from keeping alive
          every result it had recorded.
        - **Cutting a session down (S1) changes what is saved, never what is recorded.** Removed
          rows and hidden reads are left out of the file; the journal keeps all of it, because what
          the window asked is what a bug report needs. Whether a request only reads is said by
          its row, which the backend fills from the operation's name.
    """

    COLUMNS = ["Operation", "Object", "Where", "Method", "Seconds", "Outcome"]

    def __init__(self, manipulator, parent=None):
        super().__init__(parent)
        self.ui = Ui_SessionDialog()
        self.ui.setupUi(self)
        self.manipulator = manipulator
        self._rows = []
        self._removed = set()
        self._load()
        self.ui.pushButtonClose.clicked.connect(self.accept)
        self.ui.pushButtonSave.clicked.connect(self.save_session)
        self.ui.pushButtonReplay.clicked.connect(self.replay_session)
        self.ui.pushButtonRemove.clicked.connect(self.remove_selected)
        self.ui.pushButtonRestore.clicked.connect(self.restore_removed)
        self.ui.checkBoxChangesOnly.toggled.connect(self._fill)
        self.ui.tableRequests.itemSelectionChanged.connect(self._enable)

    def _load(self):
        """Read the session again, starting from all of it."""
        response = self.manipulator.inspect(obj=self.manipulator.get_managing_object(),
                                            method="history", raise_on_error=False)
        self._rows = response.value or []
        self._removed.clear()
        self._fill()

    def shown(self):
        """Return the rows the table shows and a save writes, in the order they were asked.

        Returns:
            list: `(position, row)` pairs -- every row not removed, and not a read when only the
                requests that change something are asked for.
        """
        changes_only = self.ui.checkBoxChangesOnly.isChecked()
        return [(position, row) for position, row in enumerate(self._rows)
                if position not in self._removed and not (changes_only and row.get("reads"))]

    @Slot()
    def _fill(self):
        """Put the session in the table."""
        rows = self._rows
        shown = self.shown()
        failed = sum(1 for row in rows if not row.get("status"))
        spent = sum(row.get("seconds") or 0.0 for row in rows)
        headline = f"{len(rows)} request(s) in {spent:.2f} s"
        if failed:
            headline += f"  ·  {failed} failed"
        if len(shown) != len(rows):
            headline += f"  ·  {len(shown)} shown and saved"
        if not rows:
            headline = ("Nothing has been recorded. Recording is off in "
                        "Preferences, or nothing has been asked of this project yet.")
        self.ui.labelSummary.setText(headline)

        table = self.ui.tableRequests
        table.setColumnCount(len(self.COLUMNS))
        table.setHorizontalHeaderLabels(self.COLUMNS)
        table.setRowCount(len(shown))
        for index, (position, row) in enumerate(shown):
            worked = bool(row.get("status"))
            cells = [row.get("operation") or "", row.get("object") or "",
                     row.get("where") or "", row.get("method") or "",
                     f"{row.get('seconds') or 0.0:.3f}",
                     "ok" if worked else (row.get("error") or "failed")]
            for column, value in enumerate(cells):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if column == 0:
                    item.setData(POSITION, position)
                if column == 4:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if column == 5:
                    item.setForeground(QBrush(QColor(COLOURS[worked])))
                table.setItem(index, column, item)

        header = table.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        for column in (0, 1, 3, 4, 5):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self._enable()
        logger.debug("Session shown: %s of %s request(s)", len(shown), len(rows))

    @Slot()
    def _enable(self):
        """Offer Remove for a selection and Restore when something was removed."""
        self.ui.pushButtonRemove.setEnabled(bool(self.ui.tableRequests.selectionModel().selectedRows()))
        self.ui.pushButtonRestore.setEnabled(bool(self._removed))

    @Slot()
    def remove_selected(self):
        """Leave the selected requests out of what is saved."""
        table = self.ui.tableRequests
        picked = {table.item(index.row(), 0).data(POSITION)
                  for index in table.selectionModel().selectedRows()}
        if not picked:
            return
        self._removed |= picked
        self._fill()
        logger.info("Left %s request(s) out of the session", len(picked))

    @Slot()
    def restore_removed(self):
        """Bring back every request removed from the list."""
        self._removed.clear()
        self._fill()

    @Slot()
    def save_session(self):
        """Write the requests shown to a file."""
        path, _ = QFileDialog.getSaveFileName(self, "Save session", "session.json",
                                              "Session (*.json)")
        if not path:
            return
        steps = [row for _, row in self.shown()]
        response = self.manipulator.export(obj=self.manipulator.get_managing_object(),
                                           method="journal", path=path, steps=steps,
                                           raise_on_error=False)
        result = response.value
        if not result:
            QMessageBox.critical(self, "Error", "The session could not be written.")
            return
        QMessageBox.information(self, "Saved",
                                f"{result['steps']} request(s) written to\n{result['path']}")

    @Slot()
    def replay_session(self):
        """Read a saved session and run it against the project that is open now."""
        path, _ = QFileDialog.getOpenFileName(self, "Replay a session", "",
                                              "Session (*.json)")
        if not path:
            return

        response = self.manipulator.compute(obj=self.manipulator.get_managing_object(),
                                            method="replay", path=path, raise_on_error=False)
        outcome = response.value
        if not outcome:
            QMessageBox.critical(self, "Error", "The session could not be replayed.")
            return

        # Checked whole before anything ran. A session is a file, and a file gets edited: one
        # bad step among good ones runs none of them, and the refusal is the whole list rather
        # than whatever broke first.
        if outcome.get("problems"):
            listed = "\n  ".join(outcome["problems"][:10])
            QMessageBox.critical(
                self, "Not replayed",
                f"This session does not check out, so nothing was run:\n\n  {listed}")
            return

        # Unresolved steps are named rather than counted: a session that half ran is worse than
        # one that refused, and which step could not be placed is the whole diagnosis.
        summary = f"{len(outcome['ran'])} request(s) replayed"
        if outcome.get("reads"):
            summary += f"; {outcome['reads']} that only read were not asked again"
        if outcome.get("warnings"):
            noted = "\n  ".join(outcome["warnings"][:5])
            summary += f"\n\nWorth a look:\n  {noted}"
        if outcome["failed"]:
            summary += f"\n{len(outcome['failed'])} failed"
        if outcome["unresolved"]:
            summary += ("\n\nNot in this project:\n  "
                        + "\n  ".join(outcome["unresolved"][:10]))
        (QMessageBox.warning if outcome["failed"] or outcome["unresolved"]
         else QMessageBox.information)(self, "Replayed", summary)
        self._load()
