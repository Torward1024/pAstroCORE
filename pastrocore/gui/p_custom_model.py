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
        - Disconnecting an unconnected signal is not an error but a False and a warning.
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
        - Asked of the source in one place: the degrees field of a declination between -1 and
          0 holds `-0.0`, and seconds rounded apart from their minutes show `:60.0`.
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
        - The sort arrow takes room in the header and Qt draws it over a narrow heading, so
          the number column is given room for both.
        - Fixed: these two hold a row number and a dot, with nothing to widen for.
    """
    header = view.horizontalHeader()
    header.setMinimumSectionSize(24)
    for column in range(min(narrow, header.count())):
        header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(column, 46 if column == 0 else 28)


def fit_columns(view, narrow: int = 2) -> None:
    """Size a filled table: its data columns to what they hold, its narrow ones to what they are.

    Notes:
        - `resizeColumnsToContents` does not measure a heading, so the narrow ones follow.
    """
    view.resizeColumnsToContents()
    fit_narrow_columns(view, narrow)

class CustomSortFilterProxyModel(QSortFilterProxyModel):
    """Sorts the number column as a number: past nine, as text, 10 comes before 9.

    Notes:
        - The only place it is done: a table sorts through its proxy, and the plain
          `QStandardItemModel` it holds has no `lessThan` to override.
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