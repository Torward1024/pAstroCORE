from PySide6.QtGui import QStandardItemModel
from PySide6.QtCore import Qt, QSortFilterProxyModel
from common.utils.logging_setup import logger

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
                logger.warning(f"Non-numeric data in first column: left={left_data}, right={right_data}")
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
                logger.warning(f"Non-numeric data in first column: left={left_data}, right={right_data}")
                return super().lessThan(left, right)
        return super().lessThan(left, right)