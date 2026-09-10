# p_table_models.py
"""The frequency tables a telescope carries, edited in a grid.

Four of them -- SEFD, surface efficiency, effective area, system temperature -- and each was a
class of its own, in *both* telescope editors: 126 lines byte for byte identical between
`p_dialog_edit_telescope.py` and `p_dialog_edit_space_telescope.py`, and four near-copies
inside each. Eight classes for one table with two columns.

What actually varies is two things, and each is now a declaration: what the second column is
called, and what values it will take.

**The bounds are the model's, not this form's.** `Telescope` refuses a table holding anything
but a positive number, and a surface efficiency outside nought to one -- so a cell that took a
zero was a cell that produced a saved telescope the model would refuse. The two said different
things and the grid was the one that was wrong.
"""
from typing import NamedTuple, Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt


class Column(NamedTuple):
    """What the value column of one of these tables is, and what it will accept.

    Attributes:
        heading (str): What the column is called, with its unit.
        lowest (float): The value must be **above** this. Zero for a quantity that is positive.
        highest (Optional[float]): The value must not exceed this, where there is a ceiling.
        default (float): What a new row starts at.
    """

    heading: str
    lowest: float = 0.0
    highest: Optional[float] = None
    default: float = 1000.0


#: The four tables, by the attribute each is stored under. The bounds say the same thing as
#: `Telescope._tables_hold_positive_values`, which is what refuses them on the way in.
TABLES = {
    "sefd_table": Column("SEFD (Jy)"),
    "surface_efficiency_table": Column("Efficiency", highest=1.0, default=0.5),
    "effective_area_table": Column("Effective Area (m²)"),
    "system_temperature_table": Column("System Temperature (K)", default=50.0),
}


class FrequencyTableModel(QAbstractTableModel):
    """A grid of frequency against one number.

    Args:
        column (Column): What the second column holds.
        data (list): Rows of `[frequency, value]`. Held by reference, as a Qt model does.
    """

    def __init__(self, column: Column, data=None):
        super().__init__()
        self.column = column
        self._data = data if data else []

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return 2

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role in (Qt.DisplayRole, Qt.EditRole):
            return str(self._data[index.row()][index.column()])
        return None

    def setData(self, index, value, role=Qt.EditRole):
        """Take a typed value, or refuse it.

        Notes:
            - Returning False is how a Qt model rejects an edit, which is why the exception is
              swallowed: what the user typed is not a number and the cell keeps what it had.
            - The bounds are the model's own. A frequency is positive; the value is above
              `lowest` and, where there is one, no more than `highest`. Three of these tables
              used to accept a **zero**, which `Telescope` then refused on save.
        """
        if role != Qt.EditRole:
            return False
        try:
            typed = float(value)
        except (TypeError, ValueError):
            return False

        if index.column() == 0 and typed <= 0:
            return False
        if index.column() == 1:
            if typed <= self.column.lowest:
                return False
            if self.column.highest is not None and typed > self.column.highest:
                return False

        self._data[index.row()][index.column()] = typed
        self.dataChanged.emit(index, index)
        return True

    def flags(self, index):
        return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return ["Frequency (MHz)", self.column.heading][section]
        return None

    def add_row(self, frequency=1000.0, value=None):
        """Add a row at the end, starting at what this table's values usually look like."""
        self.beginInsertRows(QModelIndex(), len(self._data), len(self._data))
        self._data.append([frequency,
                           self.column.default if value is None else value])
        self.endInsertRows()

    def remove_row(self, row):
        self.beginRemoveRows(QModelIndex(), row, row)
        del self._data[row]
        self.endRemoveRows()

    def clear(self):
        self.beginResetModel()
        self._data = []
        self.endResetModel()

    def get_data(self):
        """The table as the model holds it: frequency to value."""
        return {row[0]: row[1] for row in self._data}


def model_for(attribute: str, data=None) -> FrequencyTableModel:
    """Return the grid for one of a telescope's tables, by the name it is stored under.

    Raises:
        KeyError: If nothing is declared for that attribute, which is a typo rather than a case
            to handle.
    """
    return FrequencyTableModel(TABLES[attribute], data)
