# gui/p_status_bar.py
"""The window's status bar: the last thing the log said, and what the process is holding (G13).

Notes:
    - **The messages come from the log, not from call sites.** Every operation already says what it
      did through `logger`; a status bar fed by hand would be a second place to update, and would
      say nothing about the parts of the application nobody remembered to wire up.
    - A record can be logged from a worker thread -- a calculation, a save -- and a widget may only
      be touched from the window's. The handler emits a signal, which Qt delivers on the window's
      thread, and the label is written there.
"""
import logging

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtWidgets import QLabel, QStatusBar
from msb_arch.utils.logging_setup import logger

from pastrocore.utils.machine import as_size, process_memory


class _Records(QObject):
    """Carries a log record from whichever thread logged it to the window's."""

    arrived = Signal(int, str)


class _StatusHandler(logging.Handler):
    """A logging handler that hands each record to a signal and does nothing else."""

    def __init__(self, records: _Records):
        super().__init__(level=logging.INFO)
        self._records = records

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._records.arrived.emit(record.levelno, record.getMessage())
        except Exception:                               # noqa: BLE001 - logging never raises
            # What logging does with a handler that fails: report it once, through the
            # machinery meant for it, rather than logging from inside a log handler.
            self.handleError(record)


class WindowStatusBar(QObject):
    """What the status bar shows, and what keeps it up to date.

    Args:
        bar (QStatusBar): The window's status bar.
        parent (QObject): The window, so this goes when it does.

    Notes:
        - The memory is read on a timer rather than on every log line: it is the process's
          resident set, which moves whether or not anything is being logged.
    """

    #: What a message's level is called on the label, for the stylesheet to colour. Anything
    #: below a warning has no level and takes the ordinary text colour.
    LEVELS = {logging.WARNING: "warning", logging.ERROR: "error", logging.CRITICAL: "error"}

    #: How often the memory is re-read, in milliseconds.
    REFRESH_MS = 2000

    def __init__(self, bar: QStatusBar, parent: QObject = None):
        super().__init__(parent)
        self._bar = bar
        self.message = QLabel("")
        self.message.setObjectName("statusMessage")
        self.memory = QLabel("")
        self.memory.setObjectName("statusMemory")
        bar.addWidget(self.message, 1)
        # Permanent, so a message of any length cannot push it off the end of the bar.
        bar.addPermanentWidget(self.memory)

        self._records = _Records()
        self._records.arrived.connect(self.say)
        self._handler = _StatusHandler(self._records)
        self._logger = logging.getLogger(logger.name)
        self._logger.addHandler(self._handler)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_memory)
        self._timer.start(self.REFRESH_MS)
        self.refresh_memory()

    @Slot(int, str)
    def say(self, level: int, message: str) -> None:
        """Show one message, marked with its level so the stylesheet can colour it.

        Notes:
            - The property is what the stylesheet selects on, and Qt only re-reads it when the
              widget is re-polished, which is what the two calls below are for.
        """
        self.message.setProperty("level", self.LEVELS.get(level, ""))
        self.message.style().unpolish(self.message)
        self.message.style().polish(self.message)
        self.message.setText(message)
        self.message.setToolTip(message)

    @Slot()
    def refresh_memory(self) -> None:
        """Show what this process is holding."""
        held = as_size(process_memory())
        self.memory.setText(f"Memory: {held}" if held else "")

    def close(self) -> None:
        """Stop reading and stop listening, before the window goes.

        Notes:
            - A handler left on the logger outlives the window it writes to, and writing to a
              deleted label is an access violation rather than an exception.
        """
        self._timer.stop()
        self._logger.removeHandler(self._handler)
        try:
            self._records.arrived.disconnect(self.say)
        except (RuntimeError, TypeError):
            pass
