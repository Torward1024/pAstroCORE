# gui/EditSourceDialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                               QComboBox, QTableWidget, QTableWidgetItem, QPushButton)
from PySide6.QtCore import Qt
from base.sources import Source
from utils.validation import check_range, check_positive
from utils.logging_setup import logger

class EditSourceDialog(QDialog):
    def __init__(self, source: Source, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Source")
        self.source = source  # Исходный объект Source
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Поля для имен
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("B1950 Name:"))
        self.name_input = QLineEdit(self.source.get_name())
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        j2000_layout = QHBoxLayout()
        j2000_layout.addWidget(QLabel("J2000 Name:"))
        self.j2000_input = QLineEdit(self.source.get_name_J2000() or "")
        j2000_layout.addWidget(self.j2000_input)
        layout.addLayout(j2000_layout)

        alt_layout = QHBoxLayout()
        alt_layout.addWidget(QLabel("Alt Name:"))
        self.alt_input = QLineEdit(self.source.get_alt_name() or "")
        alt_layout.addWidget(self.alt_input)
        layout.addLayout(alt_layout)

        # Координаты RA
        ra_layout = QHBoxLayout()
        ra_layout.addWidget(QLabel("RA (hh:mm:ss):"))
        self.ra_h_input = QLineEdit(str(self.source.get_ra()[0]))
        self.ra_m_input = QLineEdit(str(self.source.get_ra()[1]))
        self.ra_s_input = QLineEdit(f"{self.source.get_ra()[2]:.3f}")
        ra_layout.addWidget(self.ra_h_input)
        ra_layout.addWidget(self.ra_m_input)
        ra_layout.addWidget(self.ra_s_input)
        layout.addLayout(ra_layout)

        # Координаты DEC
        dec_layout = QHBoxLayout()
        dec_layout.addWidget(QLabel("Dec (dd:mm:ss):"))
        self.dec_d_input = QLineEdit(str(self.source.get_dec()[0]))
        self.dec_m_input = QLineEdit(str(self.source.get_dec()[1]))
        self.dec_s_input = QLineEdit(f"{self.source.get_dec()[2]:.3f}")
        dec_layout.addWidget(self.dec_d_input)
        dec_layout.addWidget(self.dec_m_input)
        dec_layout.addWidget(self.dec_s_input)
        layout.addLayout(dec_layout)

        # Статус isactive
        active_layout = QHBoxLayout()
        active_layout.addWidget(QLabel("Is Active:"))
        self.active_combo = QComboBox()
        self.active_combo.addItems(["True", "False"])
        self.active_combo.setCurrentText(str(self.source.isactive))
        active_layout.addWidget(self.active_combo)
        layout.addLayout(active_layout)

        # Таблица потоков
        layout.addWidget(QLabel("Flux Table (MHz : Jy):"))
        self.flux_table = QTableWidget(len(self.source._flux_table), 2)
        self.flux_table.setHorizontalHeaderLabels(["Frequency (MHz)", "Flux (Jy)"])
        for row, (freq, flux) in enumerate(self.source._flux_table.items()):
            self.flux_table.setItem(row, 0, QTableWidgetItem(str(freq)))
            self.flux_table.setItem(row, 1, QTableWidgetItem(str(flux)))
        self.flux_table.resizeColumnsToContents()
        layout.addWidget(self.flux_table)

        flux_btn_layout = QHBoxLayout()
        flux_btn_layout.addWidget(QPushButton("Add Flux", clicked=self.add_flux_row))
        flux_btn_layout.addWidget(QPushButton("Remove Flux", clicked=self.remove_flux_row))
        layout.addLayout(flux_btn_layout)

        # Спектральный индекс
        spec_layout = QHBoxLayout()
        spec_layout.addWidget(QLabel("Spectral Index:"))
        self.spec_input = QLineEdit(str(self.source.get_spectral_index() or ""))
        spec_layout.addWidget(self.spec_input)
        layout.addLayout(spec_layout)

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

    def add_flux_row(self):
        row = self.flux_table.rowCount()
        self.flux_table.insertRow(row)
        self.flux_table.setItem(row, 0, QTableWidgetItem("0.0"))
        self.flux_table.setItem(row, 1, QTableWidgetItem("0.0"))

    def remove_flux_row(self):
        row = self.flux_table.currentRow()
        if row != -1:
            self.flux_table.removeRow(row)

    def on_ok(self):
        try:
            # Валидация имен
            name = self.name_input.text().strip()
            if not name:
                raise ValueError("B1950 Name cannot be empty")
            j2000_name = self.j2000_input.text().strip() or None
            alt_name = self.alt_input.text().strip() or None

            # Валидация координат
            ra_h = float(self.ra_h_input.text())
            ra_m = float(self.ra_m_input.text())
            ra_s = float(self.ra_s_input.text())
            check_range(ra_h, 0, 23, "RA hours")
            check_range(ra_m, 0, 59, "RA minutes")
            check_range(ra_s, 0, 59.999, "RA seconds")

            dec_d = float(self.dec_d_input.text())
            dec_m = float(self.dec_m_input.text())
            dec_s = float(self.dec_s_input.text())
            check_range(dec_d, -90, 90, "DEC degrees")
            check_range(dec_m, 0, 59, "DEC minutes")
            check_range(dec_s, 0, 59.999, "DEC seconds")

            # Статус
            isactive = self.active_combo.currentText() == "True"

            # Таблица потоков
            flux_table = {}
            for row in range(self.flux_table.rowCount()):
                freq = float(self.flux_table.item(row, 0).text())
                flux = float(self.flux_table.item(row, 1).text())
                check_positive(freq, "Frequency")
                check_positive(flux, "Flux")
                flux_table[freq] = flux

            # Спектральный индекс
            spec_text = self.spec_input.text().strip()
            spectral_index = float(spec_text) if spec_text else None

            # Обновляем источник
            self.source.set_source(
                name=name, ra_h=ra_h, ra_m=ra_m, ra_s=ra_s,
                de_d=dec_d, de_m=dec_m, de_s=dec_s,
                name_J2000=j2000_name, alt_name=alt_name,
                flux_table=flux_table, spectral_index=spectral_index,
                isactive=isactive
            )
            logger.info(f"Updated source '{name}' in EditSourceDialog")
            self.accept()

        except ValueError as e:
            logger.error(f"Validation error in EditSourceDialog: {e}")
            self.parent().status_bar.showMessage(f"Error: {e}")

    def get_updated_source(self):
        return self.source