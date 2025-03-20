# gui/EditTelescopeDialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                               QComboBox, QTableWidget, QTableWidgetItem, QPushButton)
from PySide6.QtCore import Qt
from base.telescopes import Telescope, SpaceTelescope, MountType
from utils.validation import check_type, check_non_empty_string, check_positive, check_range
from utils.logging_setup import logger

class EditTelescopeDialog(QDialog):
    def __init__(self, telescope: Telescope | SpaceTelescope, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Telescope")
        self.telescope = telescope
        self.is_space = isinstance(telescope, SpaceTelescope)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Основные поля
        code_layout = QHBoxLayout()
        code_layout.addWidget(QLabel("Code:"))
        self.code_input = QLineEdit(self.telescope.get_telescope_code())
        code_layout.addWidget(self.code_input)
        layout.addLayout(code_layout)

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit(self.telescope.get_telescope_name())
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        diam_layout = QHBoxLayout()
        diam_layout.addWidget(QLabel("Diameter (m):"))
        self.diam_input = QLineEdit(str(self.telescope.get_diameter()))
        diam_layout.addWidget(self.diam_input)
        layout.addLayout(diam_layout)

        mount_layout = QHBoxLayout()
        mount_layout.addWidget(QLabel("Mount Type:"))
        self.mount_combo = QComboBox()
        self.mount_combo.addItems([mt.value for mt in MountType])
        self.mount_combo.setCurrentText(self.telescope.get_mount_type().value)
        mount_layout.addWidget(self.mount_combo)
        layout.addLayout(mount_layout)

        active_layout = QHBoxLayout()
        active_layout.addWidget(QLabel("Is Active:"))
        self.active_combo = QComboBox()
        self.active_combo.addItems(["True", "False"])
        self.active_combo.setCurrentText(str(self.telescope.isactive))
        active_layout.addWidget(self.active_combo)
        layout.addLayout(active_layout)

        # Координаты (только для наземных телескопов)
        if not self.is_space:
            coord_layout = QVBoxLayout()
            coord_layout.addWidget(QLabel("Coordinates (ITRF, m):"))
            self.x_input = QLineEdit(str(self.telescope.get_telescope_coordinates()[0]))
            self.y_input = QLineEdit(str(self.telescope.get_telescope_coordinates()[1]))
            self.z_input = QLineEdit(str(self.telescope.get_telescope_coordinates()[2]))
            coord_layout.addWidget(QLabel("X:"))
            coord_layout.addWidget(self.x_input)
            coord_layout.addWidget(QLabel("Y:"))
            coord_layout.addWidget(self.y_input)
            coord_layout.addWidget(QLabel("Z:"))
            coord_layout.addWidget(self.z_input)
            layout.addLayout(coord_layout)

            vel_layout = QVBoxLayout()
            vel_layout.addWidget(QLabel("Velocities (ITRF, m/s):"))
            self.vx_input = QLineEdit(str(self.telescope.get_telescope_velocities()[0]))
            self.vy_input = QLineEdit(str(self.telescope.get_telescope_velocities()[1]))
            self.vz_input = QLineEdit(str(self.telescope.get_telescope_velocities()[2]))
            vel_layout.addWidget(QLabel("VX:"))
            vel_layout.addWidget(self.vx_input)
            vel_layout.addWidget(QLabel("VY:"))
            vel_layout.addWidget(self.vy_input)
            vel_layout.addWidget(QLabel("VZ:"))
            vel_layout.addWidget(self.vz_input)
            layout.addLayout(vel_layout)

        # Орбитальный файл (только для космических телескопов)
        if self.is_space:
            orbit_layout = QHBoxLayout()
            orbit_layout.addWidget(QLabel("Orbit File:"))
            self.orbit_input = QLineEdit(self.telescope._orbit_file or "")
            orbit_layout.addWidget(self.orbit_input)
            layout.addLayout(orbit_layout)

        # Таблица SEFD
        layout.addWidget(QLabel("SEFD Table (MHz : Jy):"))
        self.sefd_table = QTableWidget(len(self.telescope._sefd_table), 2)
        self.sefd_table.setHorizontalHeaderLabels(["Frequency (MHz)", "SEFD (Jy)"])
        for row, (freq, sefd) in enumerate(self.telescope._sefd_table.items()):
            self.sefd_table.setItem(row, 0, QTableWidgetItem(str(freq)))
            self.sefd_table.setItem(row, 1, QTableWidgetItem(str(sefd)))
        self.sefd_table.resizeColumnsToContents()
        layout.addWidget(self.sefd_table)

        sefd_btn_layout = QHBoxLayout()
        sefd_btn_layout.addWidget(QPushButton("Add SEFD", clicked=self.add_sefd_row))
        sefd_btn_layout.addWidget(QPushButton("Remove SEFD", clicked=self.remove_sefd_row))
        layout.addLayout(sefd_btn_layout)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.on_ok)
        btn_layout.addWidget(ok_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.setMinimumSize(400, 500)

    def add_sefd_row(self):
        row = self.sefd_table.rowCount()
        self.sefd_table.insertRow(row)
        self.sefd_table.setItem(row, 0, QTableWidgetItem("1.0"))
        self.sefd_table.setItem(row, 1, QTableWidgetItem("1.0"))

    def remove_sefd_row(self):
        row = self.sefd_table.currentRow()
        if row != -1:
            self.sefd_table.removeRow(row)

    def on_ok(self):
        try:
            # Валидация основных полей
            code = self.code_input.text().strip()
            check_non_empty_string(code, "Code")
            name = self.name_input.text().strip()
            check_non_empty_string(name, "Name")
            diameter = float(self.diam_input.text())
            check_positive(diameter, "Diameter")
            mount_type = self.mount_combo.currentText()
            isactive = self.active_combo.currentText() == "True"

            # SEFD таблица
            sefd_table = {}
            for row in range(self.sefd_table.rowCount()):
                freq = float(self.sefd_table.item(row, 0).text())
                sefd = float(self.sefd_table.item(row, 1).text())
                check_positive(freq, "Frequency")
                check_positive(sefd, "SEFD")
                sefd_table[freq] = sefd

            # Обновление телескопа
            if self.is_space:
                orbit_file = self.orbit_input.text().strip() or None
                if orbit_file:
                    check_non_empty_string(orbit_file, "Orbit file")
                self.telescope = SpaceTelescope(
                    code=code, name=name, orbit_file=orbit_file, diameter=diameter,
                    sefd_table=sefd_table, isactive=isactive
                )
            else:
                x = float(self.x_input.text())
                y = float(self.y_input.text())
                z = float(self.z_input.text())
                vx = float(self.vx_input.text())
                vy = float(self.vy_input.text())
                vz = float(self.vz_input.text())
                self.telescope.set_telescope(
                    code=code, name=name, x=x, y=y, z=z, vx=vx, vy=vy, vz=vz,
                    diameter=diameter, sefd_table=sefd_table, mount_type=mount_type,
                    isactive=isactive
                )

            logger.info(f"Updated telescope '{code}' in EditTelescopeDialog")
            self.accept()

        except ValueError as e:
            logger.error(f"Validation error in EditTelescopeDialog: {e}")
            self.parent().status_bar.showMessage(f"Error: {e}")

    def get_updated_telescope(self):
        return self.telescope