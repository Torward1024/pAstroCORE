from PySide6.QtGui import QStandardItemModel
from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtWidgets import QHeaderView
from msb_arch.utils.logging_setup import logger


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

class CustomStandardItemModel(QStandardItemModel):
    """Custom model that sorts the first column numerically using Qt.UserRole + 1 data."""
    
    def lessThan(self, left, right):
        """Override comparison for sorting, treating the first column as numeric."""
        if left.column() == 0 and right.column() == 0:
            left_data = left.data(Qt.UserRole + 1)
            right_data = right.data(Qt.UserRole + 1)
            try:
                left_num = int(left_data) if left_data is not None else 0
                right_num = int(right_data) if right_data is not None else 0
                return left_num < right_num
            except (ValueError, TypeError):
                logger.warning("Non-numeric data in first column: left=%s, right=%s", left_data, right_data)
                return super().lessThan(left, right)
        return super().lessThan(left, right)

class CustomSortFilterProxyModel(QSortFilterProxyModel):
    """Custom proxy model that sorts the first column numerically using Qt.UserRole + 1 data."""
    
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