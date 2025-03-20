from PySide6.QtWidgets import QDialog, QHeaderView, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QPushButton
from PySide6.QtCore import Qt
from utils.logging_setup import logger

class TelescopeSelectorDialog(QDialog):
    def __init__(self, telescopes, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Telescopes")
        self.telescopes = telescopes.get_all_telescopes()  # Предполагается, что это Telescopes объект
        self.selected_telescopes = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Поиск
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.textChanged.connect(self.filter_table)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Таблица телескопов
        self.table = QTableWidget(len(self.telescopes), 5)
        self.table.setHorizontalHeaderLabels(["Code", "Name", "Diameter (m)", "Mount Type", "Type"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.MultiSelection)
        for row, telescope in enumerate(self.telescopes):
            self.table.setItem(row, 0, QTableWidgetItem(telescope.get_telescope_code()))
            self.table.setItem(row, 1, QTableWidgetItem(telescope.get_telescope_name()))
            self.table.setItem(row, 2, QTableWidgetItem(f"{telescope.get_diameter():.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(telescope.get_mount_type().value))
            self.table.setItem(row, 4, QTableWidgetItem("SpaceTelescope" if hasattr(telescope, "_orbit_file") else "Telescope"))
        layout.addWidget(self.table)

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.on_ok)
        button_layout.addWidget(ok_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setMinimumSize(600, 400)

    def filter_table(self, text):
        text = text.lower()
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)

    def on_ok(self):
        selected_rows = [index.row() for index in self.table.selectionModel().selectedRows()]
        if not selected_rows:
            self.parent().status_bar.showMessage("No telescopes selected")
            return
        self.selected_telescopes = [self.telescopes[row] for row in selected_rows]
        logger.info(f"Selected {len(self.selected_telescopes)} telescopes")
        self.accept()

    def get_selected_telescopes(self):
        return self.selected_telescopes