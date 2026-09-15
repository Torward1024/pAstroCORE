# pastrocore/gui/p_dialog_progress.py
"""The progress of work running in a thread, and the one way to stop it."""
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QDialog
from msb_arch.utils.logging_setup import logger

from pastrocore.gui.ui_dialog_calc_progress import Ui_ProgressDialog


class ProgressDialog(QDialog):
    """A progress bar, a message, and Cancel.

    Notes:
        - **Escape and the close button ask to cancel; they do not close.** Closing the window
          is what Qt does with both by default, and the work went on without it: the dialog
          behind became usable again, could be closed, and closing the application then
          destroyed a thread that was still writing results -- `QThread: Destroyed while
          thread is still running`, and the process aborted. The window closes when the work
          reports back, through `finish`.
        - One class. Calculation, export and generation each had their own copy on the same form,
          and only one of the three turned the close button into a cancel.
        - **A long message is shortened in the middle, not wrapped and not given more room.** The
          window grew as wide as the longest step's name, and a wrapped message had its second
          line cut off, because a window does not grow taller for text that wraps. What a step
          is and how far along it is -- the start and the end of the message -- stay in view;
          the whole of it is the tooltip, and the log.
    """

    cancelRequested = Signal()

    def __init__(self, parent=None, title: str = "Progress", message: str = ""):
        super().__init__(parent)
        self.ui = Ui_ProgressDialog()
        self.ui.setupUi(self)
        self.setWindowTitle(title)
        self._message = ""
        if message:
            self._say(message)
        self.ui.pushButtonCancel.clicked.connect(self.cancel)
        self._cancelling = False

    def _say(self, message: str) -> None:
        """Show a message, shortened in the middle to the width there is."""
        self._message = message
        label = self.ui.label
        label.setToolTip(message)
        label.setText(label.fontMetrics().elidedText(message, Qt.TextElideMode.ElideMiddle,
                                                     label.contentsRect().width()))

    def resizeEvent(self, event) -> None:
        """Shorten the message again for the new width."""
        super().resizeEvent(event)
        if self._message:
            self._say(self._message)

    def update_progress(self, value: int, message: str) -> None:
        """Show how far the work has got."""
        self.ui.progressBar.setValue(value)
        if not self._cancelling:
            self._say(message)
        logger.debug("Progress: %s%% - %s", value, message)

    def cancel(self) -> None:
        """Ask the work to stop after the step in flight, once."""
        if self._cancelling:
            return
        self._cancelling = True
        self.ui.pushButtonCancel.setEnabled(False)
        self._say("Cancelling after the step in progress...")
        logger.debug("Cancellation requested")
        self.cancelRequested.emit()

    def reject(self) -> None:
        """Escape and the close button: cancel, and wait for the work to say it has stopped."""
        self.cancel()

    def finish(self) -> None:
        """Close the window, because the work has reported back."""
        super().done(QDialog.DialogCode.Accepted)


def stop_and_wait(thread) -> None:
    """Cancel work still running in `thread` and wait for it, before its owner goes away.

    Notes:
        - A `QThread` destroyed while running aborts the process, and a dialog's thread dies
          with the dialog. The progress window is modal and turns Escape into a cancel, so the
          interface offers no way to close a dialog mid-run; this is for every other way a
          dialog can be closed -- a script, a test, a parent closing. Cancellation lands between
          steps, so the wait is at most the step in flight.
    """
    # Checked by type: anything that is not a thread has nothing to wait for.
    if not isinstance(thread, QThread) or not thread.isRunning():
        return
    logger.info("Waiting for the work in progress to stop before closing")
    thread.cancel()
    thread.wait()
