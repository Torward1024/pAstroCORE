from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                               QComboBox, QTableWidget, QTableWidgetItem, QPushButton, 
                               QSpacerItem, QSizePolicy, QRadioButton, QGroupBox, QGridLayout)
from PySide6.QtCore import Qt
from base.telescopes import Telescope, SpaceTelescope, MountType
from utils.validation import check_non_empty_string, check_positive, check_range
from utils.logging_setup import logger
from datetime import datetime

class EditTelescopeDialog(QDialog):
    def __init__(self, telescope: Telescope | SpaceTelescope = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Telescope" if telescope else "Add Space Telescope")
        self.telescope = telescope
        self.is_space = isinstance(telescope, SpaceTelescope) if telescope else True  # По умолчанию SpaceTelescope
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Основной контейнер для горизонтального разделения
        content_layout = QHBoxLayout()

        # Левая колонка: Основные параметры и координаты/орбита
        left_column = QVBoxLayout()

        # Группа основных параметров
        basic_group = QGroupBox("Basic Parameters")
        basic_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        code_layout = QHBoxLayout()
        code_layout.addWidget(QLabel("Code:"))
        self.code_input = QLineEdit(self.telescope.get_telescope_code() if self.telescope else "")
        code_layout.addWidget(self.code_input)
        top_layout.addLayout(code_layout)
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit(self.telescope.get_telescope_name() if self.telescope else "")
        name_layout.addWidget(self.name_input)
        top_layout.addLayout(name_layout)
        basic_layout.addLayout(top_layout)

        params_layout = QHBoxLayout()
        diam_layout = QHBoxLayout()
        diam_layout.addWidget(QLabel("Diameter (m):"))
        self.diam_input = QLineEdit(str(self.telescope.get_diameter()) if self.telescope else "1.0")
        diam_layout.addWidget(self.diam_input)
        params_layout.addLayout(diam_layout)
        mount_layout = QHBoxLayout()
        mount_layout.addWidget(QLabel("Mount Type:"))
        self.mount_combo = QComboBox()
        self.mount_combo.addItems([mt.value for mt in MountType])
        self.mount_combo.setCurrentText(self.telescope.get_mount_type().value if self.telescope else "AZIM")
        self.mount_combo.setEnabled(not self.is_space)
        mount_layout.addWidget(self.mount_combo)
        params_layout.addLayout(mount_layout)
        basic_layout.addLayout(params_layout)

        active_layout = QHBoxLayout()
        active_layout.addWidget(QLabel("Is Active:"))
        self.active_combo = QComboBox()
        self.active_combo.addItems(["True", "False"])
        self.active_combo.setCurrentText(str(self.telescope.isactive) if self.telescope else "True")
        active_layout.addWidget(self.active_combo)
        active_layout.addStretch()
        basic_layout.addLayout(active_layout)
        basic_group.setLayout(basic_layout)
        left_column.addWidget(basic_group)

        # Координаты или орбитальные параметры
        if not self.is_space:
            coord_group = QGroupBox("Coordinates (ITRF)")
            coord_layout = QGridLayout()
            self.x_input = QLineEdit(str(self.telescope.get_telescope_coordinates()[0]) if self.telescope else "0.0")
            self.y_input = QLineEdit(str(self.telescope.get_telescope_coordinates()[1]) if self.telescope else "0.0")
            self.z_input = QLineEdit(str(self.telescope.get_telescope_coordinates()[2]) if self.telescope else "0.0")
            self.vx_input = QLineEdit(str(self.telescope.get_telescope_velocities()[0]) if self.telescope else "0.0")
            self.vy_input = QLineEdit(str(self.telescope.get_telescope_velocities()[1]) if self.telescope else "0.0")
            self.vz_input = QLineEdit(str(self.telescope.get_telescope_velocities()[2]) if self.telescope else "0.0")
            coord_layout.addWidget(QLabel("X (m):"), 0, 0)
            coord_layout.addWidget(self.x_input, 0, 1)
            coord_layout.addWidget(QLabel("Y (m):"), 0, 2)
            coord_layout.addWidget(self.y_input, 0, 3)
            coord_layout.addWidget(QLabel("Z (m):"), 1, 0)
            coord_layout.addWidget(self.z_input, 1, 1)
            coord_layout.addWidget(QLabel("VX (m/s):"), 2, 0)
            coord_layout.addWidget(self.vx_input, 2, 1)
            coord_layout.addWidget(QLabel("VY (m/s):"), 2, 2)
            coord_layout.addWidget(self.vy_input, 2, 3)
            coord_layout.addWidget(QLabel("VZ (m/s):"), 3, 0)
            coord_layout.addWidget(self.vz_input, 3, 1)
            coord_group.setLayout(coord_layout)
            left_column.addWidget(coord_group)
        else:
            orbit_group = QGroupBox("Orbit Parameters")
            orbit_layout = QVBoxLayout()

            # Переключатель
            orbit_switch_layout = QHBoxLayout()
            self.orbit_file_radio = QRadioButton("Orbit File")
            self.kepler_radio = QRadioButton("Keplerian Elements")
            self.orbit_file_radio.setChecked(True)
            orbit_switch_layout.addWidget(self.orbit_file_radio)
            orbit_switch_layout.addWidget(self.kepler_radio)
            orbit_switch_layout.addStretch()
            orbit_layout.addLayout(orbit_switch_layout)

            # Поле для файла
            self.orbit_file_layout = QHBoxLayout()
            self.orbit_file_layout.addWidget(QLabel("Orbit File:"))
            self.orbit_input = QLineEdit(self.telescope._orbit_file if self.telescope and self.telescope._orbit_file else "")
            self.orbit_file_layout.addWidget(self.orbit_input)
            orbit_layout.addLayout(self.orbit_file_layout)

            # Кеплеровские элементы
            self.kepler_layout = QGridLayout()
            kepler_fields = [
                ("Semi-major Axis (m):", "a_input", "6371000.0"),
                ("Eccentricity (0-1):", "e_input", "0.0"),
                ("Inclination (deg):", "i_input", "0.0"),
                ("RAAN (deg):", "raan_input", "0.0"),
                ("Arg. of Periapsis (deg):", "argp_input", "0.0"),
                ("True Anomaly (deg):", "nu_input", "0.0"),
                ("Epoch (YYYY-MM-DD HH:MM:SS):", "epoch_input", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                ("Gravitational Parameter (m³/s²):", "mu_input", "398600441800000.0")
            ]
            for idx, (label, attr, default) in enumerate(kepler_fields):
                setattr(self, attr, QLineEdit(default))
                self.kepler_layout.addWidget(QLabel(label), idx // 2, (idx % 2) * 2)
                self.kepler_layout.addWidget(getattr(self, attr), idx // 2, (idx % 2) * 2 + 1)
            self.kepler_layout.setEnabled(False)
            orbit_layout.addLayout(self.kepler_layout)

            orbit_group.setLayout(orbit_layout)
            left_column.addWidget(orbit_group)
            self.orbit_file_radio.toggled.connect(self.toggle_orbit_input)
            self.kepler_radio.toggled.connect(self.toggle_orbit_input)

        left_column.addStretch()
        content_layout.addLayout(left_column)

        # Правая колонка: Таблицы производительности
        right_column = QVBoxLayout()
        tables_group = QGroupBox("Performance Tables")
        tables_layout = QVBoxLayout()

        # SEFD таблица
        tables_layout.addWidget(QLabel("SEFD Table (MHz : Jy):"))
        self.sefd_table = QTableWidget(len(self.telescope._sefd_table) if self.telescope else 0, 2)
        self.sefd_table.setHorizontalHeaderLabels(["Frequency (MHz)", "SEFD (Jy)"])
        if self.telescope:
            for row, (freq, sefd) in enumerate(self.telescope._sefd_table.items()):
                self.sefd_table.setItem(row, 0, QTableWidgetItem(str(freq)))
                self.sefd_table.setItem(row, 1, QTableWidgetItem(str(sefd)))
        self.sefd_table.resizeColumnsToContents()
        tables_layout.addWidget(self.sefd_table)
        sefd_btn_layout = QHBoxLayout()
        sefd_btn_layout.addWidget(QPushButton("Add SEFD", clicked=self.add_sefd_row))
        sefd_btn_layout.addWidget(QPushButton("Remove SEFD", clicked=self.remove_sefd_row))
        tables_layout.addLayout(sefd_btn_layout)

        # Efficiency таблица
        tables_layout.addWidget(QLabel("Efficiency Table (MHz : 0-1):"))
        self.efficiency_table = QTableWidget(len(self.telescope._efficiency_table) if self.telescope else 0, 2)
        self.efficiency_table.setHorizontalHeaderLabels(["Frequency (MHz)", "Efficiency (0-1)"])
        if self.telescope:
            for row, (freq, eff) in enumerate(self.telescope._efficiency_table.items()):
                self.efficiency_table.setItem(row, 0, QTableWidgetItem(str(freq)))
                self.efficiency_table.setItem(row, 1, QTableWidgetItem(str(eff)))
        self.efficiency_table.resizeColumnsToContents()
        tables_layout.addWidget(self.efficiency_table)
        eff_btn_layout = QHBoxLayout()
        eff_btn_layout.addWidget(QPushButton("Add Efficiency", clicked=self.add_efficiency_row))
        eff_btn_layout.addWidget(QPushButton("Remove Efficiency", clicked=self.remove_efficiency_row))
        tables_layout.addLayout(eff_btn_layout)

        tables_group.setLayout(tables_layout)
        right_column.addWidget(tables_group)
        right_column.addStretch()
        content_layout.addLayout(right_column)

        main_layout.addLayout(content_layout)

        # Кнопки внизу
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.on_ok)
        btn_layout.addWidget(ok_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)
        self.setMinimumSize(700, 500)  # Пропорциональное окно (шире и ниже)

    def toggle_orbit_input(self):
        self.orbit_file_layout.setEnabled(self.orbit_file_radio.isChecked())
        self.kepler_layout.setEnabled(self.kepler_radio.isChecked())

    def add_sefd_row(self):
        row = self.sefd_table.rowCount()
        self.sefd_table.insertRow(row)
        self.sefd_table.setItem(row, 0, QTableWidgetItem("1.0"))
        self.sefd_table.setItem(row, 1, QTableWidgetItem("1.0"))

    def remove_sefd_row(self):
        row = self.sefd_table.currentRow()
        if row != -1:
            self.sefd_table.removeRow(row)

    def add_efficiency_row(self):
        row = self.efficiency_table.rowCount()
        self.efficiency_table.insertRow(row)
        self.efficiency_table.setItem(row, 0, QTableWidgetItem("1.0"))
        self.efficiency_table.setItem(row, 1, QTableWidgetItem("0.5"))

    def remove_efficiency_row(self):
        row = self.efficiency_table.currentRow()
        if row != -1:
            self.efficiency_table.removeRow(row)

    def on_ok(self):
        try:
            code = self.code_input.text().strip()
            check_non_empty_string(code, "Code")
            name = self.name_input.text().strip()
            check_non_empty_string(name, "Name")
            diameter = float(self.diam_input.text())
            check_positive(diameter, "Diameter")
            mount_type = self.mount_combo.currentText()
            isactive = self.active_combo.currentText() == "True"

            sefd_table = {}
            for row in range(self.sefd_table.rowCount()):
                freq = float(self.sefd_table.item(row, 0).text())
                sefd = float(self.sefd_table.item(row, 1).text())
                check_positive(freq, "SEFD Frequency")
                check_positive(sefd, "SEFD Value")
                sefd_table[freq] = sefd

            efficiency_table = {}
            for row in range(self.efficiency_table.rowCount()):
                freq = float(self.efficiency_table.item(row, 0).text())
                eff = float(self.efficiency_table.item(row, 1).text())
                check_positive(freq, "Efficiency Frequency")
                check_range(eff, 0, 1, "Efficiency Value")
                efficiency_table[freq] = eff

            if self.is_space:
                if self.orbit_file_radio.isChecked():
                    orbit_file = self.orbit_input.text().strip() or None
                    if orbit_file:
                        check_non_empty_string(orbit_file, "Orbit File")
                    self.telescope = SpaceTelescope(
                        code=code, name=name, orbit_file=orbit_file, diameter=diameter,
                        sefd_table=sefd_table, efficiency_table=efficiency_table, isactive=isactive
                    )
                else:
                    a = float(self.a_input.text())
                    e = float(self.e_input.text())
                    i = float(self.i_input.text())
                    raan = float(self.raan_input.text())
                    argp = float(self.argp_input.text())
                    nu = float(self.nu_input.text())
                    epoch_str = self.epoch_input.text().strip()
                    mu = float(self.mu_input.text())
                    check_positive(a, "Semi-major Axis")
                    check_range(e, 0, 1, "Eccentricity")
                    check_positive(mu, "Gravitational Parameter")
                    epoch = datetime.strptime(epoch_str, "%Y-%m-%d %H:%M:%S")
                    self.telescope = SpaceTelescope(
                        code=code, name=name, orbit_file=None, diameter=diameter,
                        sefd_table=sefd_table, efficiency_table=efficiency_table, isactive=isactive
                    )
                    self.telescope.set_orbit_from_kepler_elements(a, e, np.radians(i), np.radians(raan), 
                                                                 np.radians(argp), np.radians(nu), epoch, mu)
            else:
                x = float(self.x_input.text())
                y = float(self.y_input.text())
                z = float(self.z_input.text())
                vx = float(self.vx_input.text())
                vy = float(self.vy_input.text())
                vz = float(self.vz_input.text())
                if self.telescope:
                    self.telescope.set_telescope(
                        code=code, name=name, x=x, y=y, z=z, vx=vx, vy=vy, vz=vz,
                        diameter=diameter, sefd_table=sefd_table, efficiency_table=efficiency_table,
                        mount_type=mount_type, isactive=isactive
                    )
                else:
                    self.telescope = Telescope(
                        code=code, name=name, x=x, y=y, z=z, vx=vx, vy=vy, vz=vz,
                        diameter=diameter, sefd_table=sefd_table, efficiency_table=efficiency_table,
                        mount_type=mount_type, isactive=isactive
                    )

            logger.info(f"Updated/Added telescope '{code}' in EditTelescopeDialog")
            self.accept()

        except ValueError as e:
            logger.error(f"Validation error in EditTelescopeDialog: {e}")
            self.parent().status_bar.showMessage(f"Error: {e}")

    def get_updated_telescope(self):
        return self.telescope