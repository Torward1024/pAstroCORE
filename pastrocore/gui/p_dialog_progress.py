# pastrocore/gui/p_dialog_progress.py
"""The progress of work running in a thread, and the one way to stop it."""
from typing import Any, Callable

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QDialog
from msb_arch.utils.logging_setup import logger

from pastrocore.gui.ui_dialog_calc_progress import Ui_ProgressDialog


class ProgressDialog(QDialog):
    """A progress bar, a message, and Cancel.

    Notes:
        - Escape and the close button ask to cancel rather than close, the window closing when
          the work reports back through `finish`.
        - One class: calculation, export and generation each had their own copy of this form.
        - A long message is shortened in the middle, not wrapped and not given more room; the
          whole of it is the tooltip, and the log.
    """

    cancelRequested = Signal()

    def __init__(self, parent=None, title: str = "Progress", message: str = "",
                 cancellable: bool = True):
        super().__init__(parent)
        self.ui = Ui_ProgressDialog()
        self.ui.setupUi(self)
        self.setWindowTitle(title)
        # Work that must not be stopped half way -- a save -- has no Cancel, and Escape does not
        # stand in for one.
        self._cancellable = cancellable
        self.ui.pushButtonCancel.setVisible(cancellable)
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
        if self._cancelling or not self._cancellable:
            return
        self._cancelling = True
        self.ui.pushButtonCancel.setEnabled(False)
        self._say("Cancelling after the step in progress...")
        logger.debug("Cancellation requested")
        self.cancelRequested.emit()

    def reject(self) -> None:
        """Escape and the close button: cancel, and wait for the work to say it has stopped."""
        if self._cancellable:
            self.cancel()

    def finish(self) -> None:
        """Close the window, because the work has reported back."""
        super().done(QDialog.DialogCode.Accepted)


def stop_and_wait(thread) -> None:
    """Cancel work still running in `thread` and wait for it, before its owner goes away.

    Notes:
        - A `QThread` destroyed while running aborts the process, and a dialog's thread dies
          with the dialog. Cancellation lands between steps, so the wait is one step at most.
    """
    # Checked by type: anything that is not a thread has nothing to wait for.
    if not isinstance(thread, QThread) or not thread.isRunning():
        return
    logger.info("Waiting for the work in progress to stop before closing")
    thread.cancel()
    thread.wait()


class WorkThread(QThread):
    """One piece of work off the window's thread, telling the window how far it has got.

    Args:
        work (Callable): Called in the thread with one argument, a `progress(percent, message)`
            to report through; what it returns is kept in `answer`, what it raises in `error`.

    Notes:
        - Not a signal for the answer: the window waits for the thread and reads both, which
          keeps the caller's code in the order it happens rather than split across slots.
    """

    progress = Signal(int, str)

    def __init__(self, work: Callable[[Callable[[int, str], None]], Any]):
        super().__init__()
        self._work = work
        self.answer = None
        self.error = None

    def run(self):
        try:
            self.answer = self._work(self.progress.emit)
        except Exception as e:                          # noqa: BLE001 - handed to the window
            self.error = e


def run_with_progress(parent, title: str, message: str,
                      work: Callable[[Callable[[int, str], None]], Any],
                      quiet_ms: int = 400) -> Any:
    """Run work in a thread behind a progress window that cannot be cancelled, and wait for it.

    Args:
        parent (QWidget): The window the progress window belongs to.
        title (str): The progress window's title.
        message (str): What it says before the work reports anything.
        work (Callable): As for `WorkThread`.
        quiet_ms (int): How long work may take before the window appears at all.

    Returns:
        Any: What the work returned.

    Raises:
        Exception: Whatever the work raised, raised here, in the window's thread.

    Notes:
        - Returns when the work is done, so a caller reads like the synchronous code it
          replaces.
        - Nothing is shown for work that takes no time: the window appears only for work still
          running after `quiet_ms`.
        - The window is modal and its event loop keeps the application painting, which a
          progress bar made on the window's thread does not.
    """
    worker = WorkThread(work)
    dialog = ProgressDialog(parent, title, message, cancellable=False)
    worker.progress.connect(dialog.update_progress)
    worker.finished.connect(dialog.finish)
    worker.start()
    try:
        if not worker.wait(quiet_ms):
            dialog.exec()
        worker.wait()
    finally:
        dialog.deleteLater()
    if worker.error is not None:
        raise worker.error
    return worker.answer
