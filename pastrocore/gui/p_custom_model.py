"""The pieces every table in the tabs is built from.

The proxy they sort through, how a table is sized, how a sky position is written into one, and
how a signal is let go of once.
"""
from PySide6.QtCore import Qt, QMetaMethod, QSortFilterProxyModel
from PySide6.QtWidgets import QHeaderView
from msb_arch.utils.logging_setup import logger


def listening(widget, signal) -> bool:
    """Report whether anything is connected to a signal, so it is disconnected exactly once.

    Notes:
        - **Disconnecting an unconnected signal is not an error.** It returns False and prints
          `RuntimeWarning: Failed to disconnect (None) from signal ...`, which a cleanup that
          may run twice did thirty times in one test run. The guards written for it disagreed
          with each other and with Qt: one caught `RuntimeError`, one caught `TypeError`, four
          caught nothing, and neither exception is ever raised.
        - `isSignalConnected` is the question itself, which the comment beside one of those
          guards said Qt does not offer.
    """
    return widget.isSignalConnected(QMetaMethod.fromSignal(signal))


def position_text(manipulator, source) -> tuple:
    """Return a source's right ascension and declination as a table writes them.

    Args:
        manipulator (ScheduleManipulator): The one entry point to the model.
        source (Source): The source to place.

    Returns:
        tuple: `(right ascension, declination)`, each `hh:mm:ss.s`, the declination signed.

    Notes:
        - **Asked of the source, in one place, because it was written twice and the two came
          apart.** The catalogue dialog asks; the sources tab formatted `de_d`, `de_m` and
          `de_s` itself and got three things wrong with them. The sign taken as `de_d >= 0` is
          `+` for every source between -1 and 0 degrees, whose degrees field holds `-0.0`: they
          were listed north of the equator. Seconds rounded apart from their minutes showed
          59.97 as `:60.0`. And `05.1f` is five characters wide including the point, so every
          second in the table carried a third digit -- `12:34:012.3`.
    """
    hours, minutes, seconds = manipulator.inspect(source, get_right_ascension_parts=1)
    sign, degrees, arcminutes, arcseconds = manipulator.inspect(source, get_declination_parts=1)
    return (f"{hours:02d}:{minutes:02d}:{seconds:04.1f}",
            f"{sign}{degrees:02d}:{arcminutes:02d}:{arcseconds:04.1f}")


def fit_narrow_columns(view, narrow: int = 2) -> None:
    """Give a table's leading narrow columns the room they need, and no more.

    Args:
        view (QTableView): The table.
        narrow (int): How many columns at the front are narrow ones -- the row number and the
            dot saying whether the row is active, and in the scan editor one more.

    Notes:
        - **The sort arrow takes room in the header too**, and Qt draws it over the heading
          rather than beside it when the column is narrow: `#` was pushed out of its own column
          and the heading read as a stray mark. Sizing to contents does not help -- the arrow is
          not part of what is measured -- so the number column is given room for both.
        - Fixed, because these two hold a row number and a dot: there is nothing in them to
          widen for, and dragging them wider only takes room from the columns that say things.
    """
    header = view.horizontalHeader()
    header.setMinimumSectionSize(24)
    for column in range(min(narrow, header.count())):
        header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(column, 46 if column == 0 else 28)


def fit_columns(view, narrow: int = 2) -> None:
    """Size a filled table: its data columns to what they hold, its narrow ones to what they are.

    Notes:
        - `resizeColumnsToContents` measures *contents*, and the heading is not contents: it
          sized the number column to the width of a digit and the sort arrow then sat on top of
          the `#`. Called together, in that order, so the narrow columns keep their width after
          every refill.
    """
    view.resizeColumnsToContents()
    fit_narrow_columns(view, narrow)

class CustomSortFilterProxyModel(QSortFilterProxyModel):
    """Sorts the number column as a number: past nine, as text, 10 comes before 9.

    Notes:
        - **The only place it is done.** A `CustomStandardItemModel` carried these same eleven
          lines and every table was built on it -- but `QStandardItemModel` has no `lessThan`
          to override, so Qt never called them once. A table sorts through its proxy, which is
          this; the tables now hold a plain `QStandardItemModel`.
    """

    def lessThan(self, left, right):
        """Override comparison for sorting, treating the first column as numeric."""
        if left.column() == 0 and right.column() == 0:
            left_data = self.sourceModel().data(left, Qt.UserRole + 1)
            right_data = self.sourceModel().data(right, Qt.UserRole + 1)
            try:
                left_num = int(left_data) if left_data is not None else 0
                right_num = int(right_data) if right_data is not None else 0
                return left_num < right_num
            except (ValueError, TypeError):
                logger.warning("Non-numeric data in first column: left=%s, right=%s", left_data, right_data)
                return super().lessThan(left, right)
        return super().lessThan(left, right)