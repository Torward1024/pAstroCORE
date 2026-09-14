# pastrocore/gui/p_dialog_progress.py
"""The progress of work running in a thread, and the one way to stop it."""
from PySide6.QtCore import Signal
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
    """

    cancelRequested = Signal()

    def __init__(self, parent=None, title: str = "Progress", message: str = ""):
        super().__init__(parent)
        self.ui = Ui_ProgressDialog()
        self.ui.setupUi(self)
        self.setWindowTitle(title)
        if message:
            self.ui.label.setText(message)
        self.ui.pushButtonCancel.clicked.connect(self.cancel)
        self._cancelling = False

    def update_progress(self, value: int, message: str) -> None:
        """Show how far the work has got."""
        self.ui.progressBar.setValue(value)
        if not self._cancelling:
            self.ui.label.setText(message)
        logger.debug("Progress: %s%% - %s", value, message)

    def cancel(self) -> None:
        """Ask the work to stop after the step in flight, once."""
        if self._cancelling:
            return
        self._cancelling = True
        self.ui.pushButtonCancel.setEnabled(False)
        self.ui.label.setText("Cancelling after the step in progress...")
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
    if thread is None or not thread.isRunning():
        return
    logger.info("Waiting for the work in progress to stop before closing")
    thread.cancel()
    thread.wait()
