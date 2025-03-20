import sys
import os
import json
from typing import Optional, List
from PySide6.QtWidgets import (QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, 
                               QTabWidget, QWidget, QVBoxLayout, QLineEdit, QPushButton, 
                               QTableWidget, QTableWidgetItem, QStatusBar, QDockWidget, QHBoxLayout, QMenu, 
                               QDialog, QFileDialog, QLabel, QGridLayout, QComboBox, QHeaderView)
from PySide6.QtGui import QAction, QCloseEvent, QIcon
from PySide6.QtCore import Qt
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from super.manipulator import DefaultManipulator, Project
from super.configurator import DefaultConfigurator
from super.calculator import DefaultCalculator
from super.vizualizator import DefaultVizualizator
from utils.logging_setup import logger
from base.observation import Observation
from base.sources import Source, Sources
from base.telescopes import Telescope, Telescopes
from gui.CatalogBrowserDialog import CatalogBrowserDialog
from gui.CatalogSettingsDialog import CatalogSettingsDialog
from gui.AboutDialog import AboutDialog
from gui.SourceSelectorDialog import SourceSelectorDialog
from gui.EditSourceDialog import EditSourceDialog
from gui.TelescopeSelectorDialog import TelescopeSelectorDialog
from gui.EditTelescopeDialog import EditTelescopeDialog
from typing import Union

class PvCoreWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("pvCORE")
        self.setGeometry(100, 100, 1200, 800)
        
        self.manipulator = DefaultManipulator()
        self.configurator = DefaultConfigurator()
        self.calculator = DefaultCalculator()
        self.vizualizator = DefaultVizualizator()
        self.manipulator.set_configurator(self.configurator)
        self.manipulator.set_calculator(self.calculator)
        self.manipulator.set_vizualizator(self.vizualizator)

        self.settings_file = "settings.json"
        self.current_project_file = None
        self.load_settings()
        self.load_catalogs()

        self.obs_table = QTableWidget(0, 6)
        self.obs_table.setHorizontalHeaderLabels(["Code", "Type", "Sources", "Telescopes", "Scans", "Frequencies"])
        self.obs_table.horizontalHeader().setStretchLastSection(True)
        self.obs_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.obs_table.customContextMenuRequested.connect(self.show_obs_table_context_menu)
        self.obs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Обновляем sources_table: 6 столбцов вместо 3
        self.sources_table = QTableWidget(0, 6)
        self.sources_table.setHorizontalHeaderLabels(["Name", "Name (J2000)", "Alt. Name", "RA", "Dec", "Is Active"])
        self.sources_table.horizontalHeader().setStretchLastSection(True)  # Растягиваем последний столбец
        self.sources_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sources_table.customContextMenuRequested.connect(self.show_sources_table_context_menu)

        self.telescopes_table = QTableWidget(0, 3)
        self.telescopes_table.setHorizontalHeaderLabels(["Code", "Name", "X (m)"])
        self.scans_table = QTableWidget(0, 3)
        self.scans_table.setHorizontalHeaderLabels(["Start", "Duration", "Source"])
        self.frequencies_table = QTableWidget(0, 3)
        self.frequencies_table.setHorizontalHeaderLabels(["Frequency (MHz)", "Bandwidth (MHz)", "Polarization"])

        self.setup_menu()
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        self.tabs = QTabWidget()
        self.setup_tabs()
        self.setup_project_explorer()
        main_layout.addWidget(self.tabs)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready | March 19, 2025")


    def get_observation_by_code(self, code: str) -> Optional[Observation]:
        """Get observation by code efficiently."""
        return next((obs for obs in self.manipulator.get_observations() if obs.get_observation_code() == code), None)

    def format_ra(self, ra_deg: float) -> str:
        """Format RA from degrees to hms."""
        ra_h = int(ra_deg / 15)
        ra_m = int((ra_deg / 15 - ra_h) * 60)
        ra_s = ((ra_deg / 15 - ra_h) * 60 - ra_m) * 60
        return f"{ra_h:02d}ʰ{ra_m:02d}′{ra_s:05.2f}″"

    def format_dec(self, dec_deg: float) -> str:
        """Format Dec from degrees to dms."""
        sign = "-" if dec_deg < 0 else ""
        dec_deg = abs(dec_deg)
        dec_d = int(dec_deg)
        dec_m = int((dec_deg - dec_d) * 60)
        dec_s = ((dec_deg - dec_d) * 60 - dec_m) * 60
        return f"{sign}{dec_d}°{dec_m:02d}′{dec_s:05.2f}″"

    def update_all_ui(self, selected_obs_code=None):
        """Централизованное обновление всего интерфейса."""
        # Обновляем дерево проекта
        self.project_tree.clear()
        root = QTreeWidgetItem([self.manipulator.get_project_name()])
        for obs in self.manipulator.get_observations():
            QTreeWidgetItem(root, [obs.get_observation_code()])
        self.project_tree.addTopLevelItem(root)
        root.setExpanded(True)

        # Обновляем таблицу наблюдений
        self.obs_table.setRowCount(0)
        for i, obs in enumerate(self.manipulator.get_observations()):
            self.obs_table.insertRow(i)
            for col, value in enumerate([
                obs.get_observation_code(),
                obs.get_observation_type(),
                f"{len(obs.get_sources().get_active_sources())} ({len(obs.get_sources().get_all_sources())})",
                f"{len(obs.get_telescopes().get_active_telescopes())} ({len(obs.get_telescopes().get_all_telescopes())})",
                f"{len(obs.get_scans().get_active_scans())} ({len(obs.get_scans().get_all_scans())})",
                f"{len(obs.get_frequencies().get_active_frequencies())} ({len(obs.get_frequencies().get_all_frequencies())})"
            ]):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.obs_table.setItem(i, col, item)
        self.obs_table.resizeColumnsToContents()
        self.obs_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Обновляем селектор
        self.obs_selector.blockSignals(True)
        self.obs_selector.clear()
        self.obs_selector.addItem("Select Observation...")
        for obs in self.manipulator.get_observations():
            self.obs_selector.addItem(obs.get_observation_code())
        if selected_obs_code:
            self.obs_selector.setCurrentText(selected_obs_code)
        self.obs_selector.blockSignals(False)

        # Обновляем таблицы конфигурации, если выбрано наблюдение
        if selected_obs_code and selected_obs_code != "Select Observation...":
            obs = self.get_observation_by_code(selected_obs_code)
            if obs:
                self.update_config_tables(obs)

    def setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        file_menu.addAction("New", self.new_project)
        file_menu.addSeparator()
        file_menu.addAction("Open", self.open_project)
        file_menu.addAction("Save", self.save_project)
        file_menu.addAction("Save As...", self.save_project_as)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        settings_menu = menubar.addMenu("Settings")
        settings_menu.addAction("Set Catalogs...", self.show_catalog_settings)
        settings_menu.addAction("Source Catalog Browser", self.show_source_catalog_browser)
        settings_menu.addAction("Telescope Catalog Browser", self.show_telescope_catalog_browser)

        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About", self.show_about_dialog)

    def setup_project_explorer(self):
        self.project_dock = QDockWidget("Project Explorer", self)
        self.project_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.project_dock)

        dock_widget = QWidget()
        dock_layout = QVBoxLayout(dock_widget)
        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderLabels(["Project / Observations"])
        self.project_tree.setMaximumWidth(300)
        self.update_project_tree()
        self.project_tree.itemSelectionChanged.connect(self.on_project_item_selected)
        self.project_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.project_tree.customContextMenuRequested.connect(self.show_context_menu)
        dock_layout.addWidget(self.project_tree)
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(QPushButton("Add Observation", clicked=self.add_observation))
        buttons_layout.addWidget(QPushButton("Remove Observation", clicked=self.remove_observation))
        dock_layout.addLayout(buttons_layout)
        self.project_dock.setWidget(dock_widget)

    def setup_tabs(self):
# Project Tab
        project_tab = QWidget()
        project_layout = QVBoxLayout(project_tab)
        project_name_layout = QHBoxLayout()
        project_name_layout.addWidget(QLabel("Project Name:"))
        self.project_name_input = QLineEdit(self.manipulator.get_project_name())
        project_name_layout.addWidget(self.project_name_input)
        self.project_name_set_btn = QPushButton("Set")
        self.project_name_set_btn.clicked.connect(self.set_project_name)
        project_name_layout.addWidget(self.project_name_set_btn)
        self.project_name_input.returnPressed.connect(self.set_project_name)
        project_layout.addLayout(project_name_layout)
        project_layout.addWidget(self.obs_table)
        self.tabs.addTab(project_tab, "Project")

        # Configurator Tab
        config_tab = QWidget()
        config_layout = QVBoxLayout(config_tab)
        
        self.obs_selector = QComboBox()
        self.update_obs_selector()
        self.obs_selector.currentTextChanged.connect(self.on_obs_selected_from_combo)
        config_layout.addWidget(QLabel("Select Observation:"))
        config_layout.addWidget(self.obs_selector)
        
        code_layout = QHBoxLayout()
        code_layout.addWidget(QLabel("Observation Code:"))
        self.obs_code_input = QLineEdit()
        code_layout.addWidget(self.obs_code_input)
        self.obs_code_set_btn = QPushButton("Set")
        self.obs_code_set_btn.clicked.connect(self.set_observation_code)
        code_layout.addWidget(self.obs_code_set_btn)
        self.obs_code_input.returnPressed.connect(self.set_observation_code)
        
        # Добавляем Combobox для типа наблюдения
        self.obs_type_combo = QComboBox()
        self.obs_type_combo.addItems(["VLBI", "SINGLE_DISH"])
        self.obs_type_combo.currentTextChanged.connect(self.update_observation_type)
        code_layout.addWidget(QLabel("Type:"))
        code_layout.addWidget(self.obs_type_combo)
        config_layout.addLayout(code_layout)

        config_subtabs = QTabWidget()
        
        # Sources Tab
        sources_tab = QWidget()
        sources_layout = QVBoxLayout(sources_tab)
        sources_layout.addWidget(self.sources_table)
        sources_buttons_layout = QHBoxLayout()
        sources_buttons_layout.addWidget(QPushButton("Add Source", clicked=self.add_source))
        sources_buttons_layout.addWidget(QPushButton("Remove Source", clicked=self.remove_source))
        sources_layout.addLayout(sources_buttons_layout)
        config_subtabs.addTab(sources_tab, "Sources")
        
        # Telescopes, Scans, Frequencies (без изменений)
        telescopes_tab = QWidget()
        telescopes_layout = QVBoxLayout(telescopes_tab)
        telescopes_layout.addWidget(self.telescopes_table)
        telescopes_buttons_layout = QHBoxLayout()
        telescopes_buttons_layout.addWidget(QPushButton("Add Telescope", clicked=self.add_telescope))
        telescopes_buttons_layout.addWidget(QPushButton("Edit Telescope", clicked=self.edit_telescope))
        telescopes_buttons_layout.addWidget(QPushButton("Remove Telescope", clicked=self.remove_telescope))
        telescopes_layout.addLayout(telescopes_buttons_layout)
        config_subtabs.addTab(telescopes_tab, "Telescopes")
        
        scans_tab = QWidget()
        scans_layout = QVBoxLayout(scans_tab)
        scans_layout.addWidget(self.scans_table)
        scans_layout.addWidget(QPushButton("Add Scan", clicked=self.add_scan))
        config_subtabs.addTab(scans_tab, "Scans")
        
        frequencies_tab = QWidget()
        frequencies_layout = QVBoxLayout(frequencies_tab)
        frequencies_layout.addWidget(self.frequencies_table)
        frequencies_layout.addWidget(QPushButton("Add Frequency", clicked=self.add_frequency))
        config_subtabs.addTab(frequencies_tab, "Frequencies")
        
        config_layout.addWidget(config_subtabs)
        self.tabs.addTab(config_tab, "Configurator")

        # Vizualizator Tab (без изменений)
        viz_tab = QWidget()
        viz_layout = QVBoxLayout(viz_tab)
        self.canvas = FigureCanvas(plt.Figure())
        viz_layout.addWidget(self.canvas)
        viz_layout.addWidget(QPushButton("Refresh Plot", clicked=self.refresh_plot))
        self.tabs.addTab(viz_tab, "Vizualizator")
    
    def set_project_name(self):
     new_name = self.project_name_input.text().strip()
     if new_name:
         self.manipulator._project.set_name(new_name)
         self.update_all_ui()
         self.status_bar.showMessage(f"Project name set to '{new_name}'")
     else:
         self.status_bar.showMessage("Project name cannot be empty")
    
    def set_observation_code(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        new_code = self.obs_code_input.text().strip()
        if not new_code:
            self.status_bar.showMessage("Observation code cannot be empty")
            return
        obs = self.get_observation_by_code(selected)
        if obs:
            self.manipulator.configure_observation_code(obs, new_code)
            self.update_all_ui(new_code)
            self.status_bar.showMessage(f"Observation code set to '{new_code}'")

    def edit_telescope(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        row = self.telescopes_table.currentRow()
        if row == -1:
            self.status_bar.showMessage("Please select a telescope to edit")
            return
        for obs in self.manipulator.get_observations():
            if obs.get_observation_code() == selected:
                telescope = obs.get_telescopes().get_telescope(row)
                dialog = EditTelescopeDialog(telescope, self)
                if dialog.exec():
                    updated_telescope = dialog.get_updated_telescope()
                    obs.get_telescopes().set_telescope(row, updated_telescope)
                    self.update_config_tables(obs)
                    self.update_obs_table()
                    self.status_bar.showMessage(f"Telescope '{updated_telescope.get_telescope_code()}' updated")
                break

    def remove_source(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        selected_rows = [index.row() for index in self.sources_table.selectionModel().selectedRows()]
        if not selected_rows:
            self.status_bar.showMessage("No sources selected to remove")
            return
        obs = self.get_observation_by_code(selected)
        if obs:
            for row in sorted(selected_rows, reverse=True):
                self.manipulator.remove_source_from_observation(obs, row)
            self.update_all_ui(selected)
            self.status_bar.showMessage(f"Removed {len(selected_rows)} source(s) from '{selected}'")

    def remove_telescope(self):
        obs_code = self.obs_selector.currentText()
        if obs_code == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        row = self.telescopes_table.currentRow()
        if row == -1:
            self.status_bar.showMessage("Please select a telescope to remove")
            return
        obs = self.get_observation_by_code(obs_code)
        if obs:
            self.manipulator.remove_telescope_by_index(obs, row)
            self.update_all_ui(obs_code)
            self.status_bar.showMessage("Telescope removed")

    def show_telescopes_context_menu(self, position):
        menu = QMenu()
        menu.addAction("Add Telescope", self.add_telescope)
        menu.addAction("Insert Telescope", self.insert_telescope)
        menu.addAction("Edit Telescope", self.edit_telescope)
        menu.addAction("Remove Telescope", self.remove_telescope)
        menu.addSeparator()
        menu.addAction("Activate All", self.activate_all_telescopes)
        menu.addAction("Deactivate All", self.deactivate_all_telescopes)
        menu.exec(self.telescopes_table.viewport().mapToGlobal(position))
    
    def activate_all_telescopes(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        for obs in self.manipulator.get_observations():
            if obs.get_observation_code() == selected:
                obs.get_telescopes().activate_all()
                self.update_config_tables(obs)
                self.update_obs_table()
                self.status_bar.showMessage(f"All telescopes activated for '{selected}'")
                break
    
    def deactivate_all_telescopes(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        for obs in self.manipulator.get_observations():
            if obs.get_observation_code() == selected:
                obs.get_telescopes().deactivate_all()
                self.update_config_tables(obs)
                self.update_obs_table()
                self.status_bar.showMessage(f"All telescopes deactivated for '{selected}'")
                break

    def update_project_tree(self):
        self.project_tree.clear()
        root = QTreeWidgetItem([self.manipulator.get_project_name()])
        for obs in self.manipulator.get_observations():
            QTreeWidgetItem(root, [obs.get_observation_code()])
        self.project_tree.addTopLevelItem(root)
        root.setExpanded(True)
        # Отключаем сигналы перед обновлением селектора
        self.obs_selector.blockSignals(True)
        self.update_obs_table()
        self.update_obs_selector()
        self.obs_selector.blockSignals(False)

    def update_obs_table(self):
        self.obs_table.setRowCount(0)
        for i, obs in enumerate(self.manipulator.get_observations()):
            self.obs_table.insertRow(i)
            code_item = QTableWidgetItem(obs.get_observation_code())
            code_item.setFlags(code_item.flags() & ~Qt.ItemIsEditable)
            self.obs_table.setItem(i, 0, code_item)
            type_item = QTableWidgetItem(obs.get_observation_type())
            type_item.setFlags(type_item.flags() & ~Qt.ItemIsEditable)
            self.obs_table.setItem(i, 1, type_item)
            sources_item = QTableWidgetItem(str(len(obs.get_sources().get_active_sources())) + ' (' + str(len(obs.get_sources().get_all_sources())) + ')')
            sources_item.setFlags(sources_item.flags() & ~Qt.ItemIsEditable)
            self.obs_table.setItem(i, 2, sources_item)
            telescopes_item = QTableWidgetItem(str(len(obs.get_telescopes().get_active_telescopes())) + ' (' + str(len(obs.get_telescopes().get_active_telescopes())) + ')')
            telescopes_item.setFlags(telescopes_item.flags() & ~Qt.ItemIsEditable)
            self.obs_table.setItem(i, 3, telescopes_item)
            scans_item = QTableWidgetItem(str(len(obs.get_scans().get_all_scans())) + ' (' + str(len(obs.get_scans().get_active_scans())) + ')')
            scans_item.setFlags(scans_item.flags() & ~Qt.ItemIsEditable)
            self.obs_table.setItem(i, 4, scans_item)
            freqs_item = QTableWidgetItem(str(len(obs.get_frequencies().get_all_frequencies())) + ' (' + str(len(obs.get_frequencies().get_active_frequencies())) +')')
            freqs_item.setFlags(freqs_item.flags() & ~Qt.ItemIsEditable)
            self.obs_table.setItem(i, 5, freqs_item)
        
        self.obs_table.resizeColumnsToContents()
        self.obs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.obs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.obs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.obs_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.obs_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.obs_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)

    def update_obs_selector(self):
        self.obs_selector.clear()
        self.obs_selector.addItem("Select Observation...")
        for obs in self.manipulator.get_observations():
            self.obs_selector.addItem(obs.get_observation_code())

    def on_obs_selected_from_combo(self, text):
        if text == "Select Observation...":
            self.obs_code_input.clear()
            self.obs_type_combo.blockSignals(True)
            self.obs_type_combo.setCurrentText("VLBI")
            self.obs_type_combo.blockSignals(False)
            self.sources_table.setRowCount(0)
            self.telescopes_table.setRowCount(0)
            self.scans_table.setRowCount(0)
            self.frequencies_table.setRowCount(0)
            return
        obs = self.get_observation_by_code(text)
        if obs:
            self.obs_code_input.blockSignals(True)
            self.obs_type_combo.blockSignals(True)
            self.obs_code_input.setText(obs.get_observation_code())
            self.obs_type_combo.setCurrentText(obs.get_observation_type())
            self.obs_code_input.blockSignals(False)
            self.obs_type_combo.blockSignals(False)
            self.update_config_tables(obs)
            for i in range(self.project_tree.topLevelItem(0).childCount()):
                child = self.project_tree.topLevelItem(0).child(i)
                if child.text(0) == text:
                    self.project_tree.setCurrentItem(child)
                    break

    def edit_source(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        row = self.sources_table.currentRow()
        if row == -1:
            self.status_bar.showMessage("Please select a source to edit")
            return
        for obs in self.manipulator.get_observations():
            if obs.get_observation_code() == selected:
                source = obs.get_sources().get_all_sources()[row]
                dialog = EditSourceDialog(source, self)
                if dialog.exec():
                    updated_source = dialog.get_updated_source()
                    obs.get_sources().set_source(row, updated_source)
                    self.update_config_tables(obs)
                    self.update_obs_table()
                    self.status_bar.showMessage(f"Source '{updated_source.get_name()}' updated")
                break

    def update_observation_code(self):
        selected = self.obs_selector.currentText()
        text = self.obs_code_input.text()
        if selected == "Select Observation..." or not text:
            return
        for obs in self.manipulator.get_observations():
            if obs.get_observation_code() == selected:
                self.manipulator._configurator.set_observation_code(obs, text)
                self.update_project_tree()
                self.obs_selector.blockSignals(True)
                self.obs_selector.setCurrentText(text)
                self.obs_selector.blockSignals(False)
                self.status_bar.showMessage(f"Observation code updated to '{text}'")
                break
            
    def update_observation_type(self, obs_type):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            return
        obs = self.get_observation_by_code(selected)
        if obs:
            self.manipulator.configure_observation_type(obs, obs_type)
            self.update_all_ui(selected)
            self.status_bar.showMessage(f"Observation type set to '{obs_type}'")

    def update_config_tables(self, obs: Observation):
        """Update configuration tables for the given observation."""
        # Sources
        self.sources_table.setRowCount(0)
        self.sources_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.sources_table.setSelectionMode(QTableWidget.MultiSelection)
        for src in obs.get_sources().get_all_sources():
            row = self.sources_table.rowCount()
            self.sources_table.insertRow(row)
            for col, value in enumerate([
                src.get_name(), src.get_name_J2000() or "", src.get_alt_name() or "",
                self.format_ra(src.get_ra_degrees()), self.format_dec(src.get_dec_degrees())
            ]):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.sources_table.setItem(row, col, item)
            combo = QComboBox()
            combo.addItems(["True", "False"])
            combo.setCurrentText(str(src.isactive))
            combo.currentTextChanged.connect(lambda state, s=src: self.on_is_active_changed(s, state))
            self.sources_table.setCellWidget(row, 5, combo)
        self.sources_table.resizeColumnsToContents()
        self.sources_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Telescopes
        self.telescopes_table.setRowCount(0)
        for tel in obs.get_telescopes().get_all_telescopes():
            row = self.telescopes_table.rowCount()
            self.telescopes_table.insertRow(row)
            for col, value in enumerate([
                tel.get_telescope_code(), tel.get_telescope_name(), f"{tel.get_diameter():.2f}",
                tel.get_mount_type().value, str(tel.isactive)
            ]):
                self.telescopes_table.setItem(row, col, QTableWidgetItem(value))

        # Scans
        self.scans_table.setRowCount(0)
        for scan in obs.get_scans().get_active_scans():
            row = self.scans_table.rowCount()
            self.scans_table.insertRow(row)
            for col, value in enumerate([
                str(scan.get_start()), str(scan.get_duration()),
                scan.get_source().get_name() if scan.get_source() else "None"
            ]):
                self.scans_table.setItem(row, col, QTableWidgetItem(value))

        # Frequencies
        self.frequencies_table.setRowCount(0)
        for freq in obs.get_frequencies().get_active_frequencies():
            row = self.frequencies_table.rowCount()
            self.frequencies_table.insertRow(row)
            for col, value in enumerate([
                str(freq.get_freq()), str(freq.get_bandwidth()), freq.get_polarization() or "None"
            ]):
                self.frequencies_table.setItem(row, col, QTableWidgetItem(value))

    def show_context_menu(self, position):
        menu = QMenu()
        menu.addAction("Add Observation", self.add_observation)
        menu.addAction("Insert Observation", self.insert_observation)
        menu.addAction("Remove Observation", self.remove_observation)
        menu.exec(self.project_tree.viewport().mapToGlobal(position))

    def show_obs_table_context_menu(self, position):
        menu = QMenu()
        menu.addAction("Add Observation", self.add_observation)
        menu.addAction("Insert Observation", self.insert_observation_from_table)
        menu.addAction("Remove Observation", self.remove_observation_from_table)
        menu.exec(self.obs_table.viewport().mapToGlobal(position))

    def add_observation(self):
        obs = Observation(observation_code=f"Obs{len(self.manipulator.get_observations())+1}", observation_type="VLBI")
        self.manipulator.add_observation(obs)
        self.update_all_ui(obs.get_observation_code())

    def insert_observation(self):
        selected = self.project_tree.selectedItems()
        if not selected or selected[0].text(0) == self.manipulator.get_project_name():
            self.add_observation()
            return
        selected_code = selected[0].text(0)
        observations = self.manipulator.get_observations()
        index = next((i for i, obs in enumerate(observations) if obs.get_observation_code() == selected_code), -1)
        if index == -1:
            self.add_observation()
            return
        new_obs = Observation(observation_code=f"Obs{len(observations)+1}", observation_type="VLBI")
        self.manipulator.insert_observation(new_obs, index)
        self.update_all_ui(new_obs.get_observation_code())

    def insert_telescope(self):
        if not self.manipulator.get_catalog_manager().telescope_catalog.get_all_telescopes():
            logger.warning("Cannot insert telescope: telescopes catalog is not loaded")
            self.status_bar.showMessage("Cannot insert telescope: load telescopes catalog first")
            return
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        row = self.telescopes_table.currentRow()
        dialog = TelescopeSelectorDialog(self.manipulator.get_catalog_manager().telescope_catalog, self)
        if dialog.exec():
            selected_telescopes = dialog.get_selected_telescopes()
            if not selected_telescopes:
                self.status_bar.showMessage("No telescopes selected")
                return
            for obs in self.manipulator.get_observations():
                if obs.get_observation_code() == selected:
                    telescopes = obs.get_telescopes()
                    initial_count = len(telescopes.get_all_telescopes())
                    if row == -1:  # Если строка не выбрана, добавляем в конец
                        for telescope in selected_telescopes:
                            try:
                                self.manipulator._configurator.add_telescope(obs, telescope)
                            except ValueError as e:
                                self.status_bar.showMessage(str(e))
                                continue
                    else:
                        # Вставка перед выбранной строкой
                        current_telescopes = telescopes.get_all_telescopes()
                        for i, telescope in enumerate(selected_telescopes):
                            current_telescopes.insert(row + i, telescope)
                        telescopes._data = current_telescopes  # Обновляем список телескопов
                        logger.info(f"Inserted {len(selected_telescopes)} telescope(s) at index {row} in observation '{selected}'")
                    final_count = len(telescopes.get_all_telescopes())
                    added_count = final_count - initial_count
                    if added_count > 0:
                        self.update_config_tables(obs)
                        self.update_obs_table()
                        self.status_bar.showMessage(f"Inserted {added_count} telescope(s) into '{selected}'")
                    else:
                        self.status_bar.showMessage(f"No new telescopes inserted into '{selected}' (duplicates skipped)")
                    break

    def insert_observation_from_table(self):
        row = self.obs_table.currentRow()
        if row == -1:
            self.add_observation()
            return
        new_obs = Observation(observation_code=f"Obs{len(self.manipulator.get_observations())+1}", observation_type="VLBI")
        self.manipulator.insert_observation(new_obs, row)
        self.update_project_tree()

    def remove_observation(self):
        selected = self.project_tree.selectedItems()
        if not selected or selected[0].text(0) == self.manipulator.get_project_name():
            return
        selected_code = selected[0].text(0)
        observations = self.manipulator.get_observations()
        index = next((i for i, obs in enumerate(observations) if obs.get_observation_code() == selected_code), -1)
        if index != -1:
            self.manipulator.remove_observation(index)
            self.update_all_ui()

    def remove_observation_from_table(self):
        row = self.obs_table.currentRow()
        if row != -1:
            self.manipulator.remove_observation(row)
            self.update_project_tree()

    def update_project_name(self):
        text = self.project_name_input.text()
        if text:
            self.manipulator._project.set_name(text)
            self.update_project_tree()
            self.status_bar.showMessage(f"Project name updated to '{text}'")

    def add_source(self):
        if not self.manipulator.get_catalog_manager().source_catalog.get_all_sources():
            logger.warning("Cannot add source: sources catalog is not loaded")
            self.status_bar.showMessage("Cannot add source: load sources catalog first")
            return
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        dialog = SourceSelectorDialog(self.manipulator.get_catalog_manager().source_catalog.get_all_sources(), self)
        if dialog.exec():
            selected_sources = dialog.get_selected_sources()
            if not selected_sources:
                self.status_bar.showMessage("No sources selected")
                return
            obs = self.get_observation_by_code(selected)
            if obs:
                initial_source_count = len(obs.get_sources().get_active_sources())
                for source in selected_sources:
                    self.manipulator.add_source_to_observation(obs, source)
                final_source_count = len(obs.get_sources().get_active_sources())
                added_count = final_source_count - initial_source_count
                if added_count > 0:
                    self.update_all_ui(selected)
                    self.status_bar.showMessage(f"Added {added_count} new source(s) to '{selected}'")
                else:
                    self.status_bar.showMessage(f"No new sources added to '{selected}' (duplicates skipped)")

    def insert_source(self):
        """Вставка источника перед выбранной строкой."""
        if not self.manipulator.get_catalog_manager().source_catalog.get_all_sources():
            logger.warning("Cannot insert source: sources catalog is not loaded")
            self.status_bar.showMessage("Cannot insert source: load sources catalog first")
            return
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        
        row = self.sources_table.currentRow()
        dialog = SourceSelectorDialog(self.manipulator.get_catalog_manager().source_catalog.get_all_sources(), self)
        if dialog.exec():
            selected_sources = dialog.get_selected_sources()
            if not selected_sources:
                self.status_bar.showMessage("No sources selected")
                return
            for obs in self.manipulator.get_observations():
                if obs.get_observation_code() == selected:
                    sources = obs.get_sources()
                    initial_count = len(sources.get_active_sources())
                    if row == -1:  # Если строка не выбрана, добавляем в конец
                        for source in selected_sources:
                            self.manipulator._configurator.add_source(obs, source)
                    else:
                        # Вставка перед выбранной строкой
                        current_sources = sources.get_all_sources()  # Берем все источники, включая неактивные
                        for i, source in enumerate(selected_sources):
                            current_sources.insert(row + i, source)
                        sources._data = current_sources  # Обновляем список источников
                        logger.info(f"Inserted {len(selected_sources)} source(s) at index {row} in observation '{selected}'")
                    final_count = len(sources.get_active_sources())
                    added_count = final_count - initial_count
                    if added_count > 0:
                        self.update_config_tables(obs)
                        self.update_obs_table()
                        self.status_bar.showMessage(f"Inserted {added_count} new source(s) into '{selected}'")
                    else:
                        self.status_bar.showMessage(f"No new sources inserted into '{selected}' (duplicates skipped)")
                    break

    def on_is_active_changed(self, source: Source, state: str):
        """Обработчик изменения состояния Is Active."""
        new_state = state == "True"
        if new_state != source.isactive:
            if new_state:
                source.activate()
                logger.info(f"Activated source '{source.get_name()}'")
            else:
                source.deactivate()
                logger.info(f"Deactivated source '{source.get_name()}'")
            # Обновляем таблицы, чтобы отразить изменения в активных источниках
            selected = self.obs_selector.currentText()
            if selected != "Select Observation...":
                for obs in self.manipulator.get_observations():
                    if obs.get_observation_code() == selected:
                        self.update_config_tables(obs)
                        self.update_obs_table()
                        break

    def show_sources_table_context_menu(self, position):
        menu = QMenu()
        menu.addAction("Add Source", self.add_source)
        menu.addAction("Insert Source", self.insert_source)
        menu.addAction("Edit Source", self.edit_source)  # Добавляем пункт
        menu.addAction("Remove Source", self.remove_source)
        menu.addSeparator()
        menu.addAction("Activate All", self.activate_all_sources)
        menu.addAction("Deactivate All", self.deactivate_all_sources)
        menu.exec(self.sources_table.viewport().mapToGlobal(position))

    def remove_source(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
            
        selected_rows = [index.row() for index in self.sources_table.selectionModel().selectedRows()]
        if not selected_rows:
            self.status_bar.showMessage("No sources selected to remove")
            return
            
        for obs in self.manipulator.get_observations():
            if obs.get_observation_code() == selected:
                # Удаляем источники в обратном порядке, чтобы не сбить индексы
                for row in sorted(selected_rows, reverse=True):
                    self.manipulator._configurator.remove_source(obs, row)
                self.update_config_tables(obs)  # Обновляем таблицу после удаления
                self.update_obs_table()
                self.status_bar.showMessage(f"Removed {len(selected_rows)} source(s) from '{selected}'")
                break
    
    def activate_all_sources(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        for obs in self.manipulator.get_observations():
            if obs.get_observation_code() == selected:
                obs.get_sources().activate_all()
                self.update_config_tables(obs)
                self.update_obs_table()
                self.status_bar.showMessage(f"All sources activated for '{selected}'")
                break
    
    def deactivate_all_sources(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        for obs in self.manipulator.get_observations():
            if obs.get_observation_code() == selected:
                obs.get_sources().deactivate_all()
                self.update_config_tables(obs)
                self.update_obs_table()
                self.status_bar.showMessage(f"All sources deactivated for '{selected}'")
                break

    def add_telescope(self):
        if not self.manipulator.get_catalog_manager().telescope_catalog.get_all_telescopes():
            logger.warning("Cannot add telescope: telescopes catalog is not loaded")
            self.status_bar.showMessage("Cannot add telescope: load telescopes catalog first")
            return
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        dialog = TelescopeSelectorDialog(self.manipulator.get_catalog_manager().telescope_catalog, self)
        if dialog.exec():
            selected_telescopes = dialog.get_selected_telescopes()
            if not selected_telescopes:
                self.status_bar.showMessage("No telescopes selected")
                return
            obs = self.get_observation_by_code(selected)
            if obs:
                initial_telescope_count = len(obs.get_telescopes().get_all_telescopes())
                for telescope in selected_telescopes:
                    try:
                        self.manipulator.add_telescope_to_observation(obs, telescope)
                    except ValueError as e:
                        self.status_bar.showMessage(str(e))
                        continue
                final_telescope_count = len(obs.get_telescopes().get_all_telescopes())
                added_count = final_telescope_count - initial_telescope_count
                if added_count > 0:
                    self.update_all_ui(selected)
                    self.status_bar.showMessage(f"Added {added_count} telescope(s) to '{selected}'")
                else:
                    self.status_bar.showMessage(f"No new telescopes added to '{selected}' (duplicates skipped)")

    def add_scan(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        row = self.scans_table.rowCount()
        self.scans_table.insertRow(row)
        for obs in self.manipulator.get_observations():
            if obs.get_observation_code() == selected:
                self.manipulator._configurator.add_scan(obs, start=row+1.0, duration=1.0)
                self.update_config_tables(obs)
                self.update_obs_table()
                break

    def add_frequency(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        row = self.frequencies_table.rowCount()
        self.frequencies_table.insertRow(row)
        for obs in self.manipulator.get_observations():
            if obs.get_observation_code() == selected:
                self.manipulator._configurator.add_frequency(obs, freq=1000.0 + row * 10, bandwidth=16.0)
                self.update_config_tables(obs)
                self.update_obs_table()
                break

    def refresh_plot(self):
        selected = self.project_tree.selectedItems()
        if not selected or selected[0].text(0) == self.manipulator.get_project_name():
            self.canvas.figure.clf()
            self.canvas.draw()
            return
        selected_code = selected[0].text(0)
        for obs in self.manipulator.get_observations():
            if obs.get_observation_code() == selected_code:
                self.calculator.calculate_all(obs)
                if not hasattr(obs, '_calculated_data') or not obs._calculated_data:
                    logger.warning(f"Nothing to plot for observation '{obs.get_observation_code()}': no calculated data")
                    self.canvas.figure.clf()
                    self.canvas.draw()
                    return
                first_scan_key = list(obs._calculated_data.keys())[0]
                if "uv_coverage" not in obs._calculated_data[first_scan_key] or not obs._calculated_data[first_scan_key]["uv_coverage"]:
                    logger.warning(f"Nothing to plot for observation '{obs.get_observation_code()}': no u,v coverage data")
                    self.canvas.figure.clf()
                    self.canvas.draw()
                    return
                self.canvas.figure.clf()
                ax = self.canvas.figure.add_subplot(111)
                for (tel1, tel2), points in obs._calculated_data[first_scan_key]["uv_coverage"].items():
                    u_vals, v_vals = zip(*points)
                    ax.scatter(u_vals, v_vals, label=f"{tel1}-{tel2}", s=5)
                    ax.scatter([-u for u in u_vals], [-v for v in v_vals], s=5)
                ax.set_xlabel("u (m)")
                ax.set_ylabel("v (m)")
                ax.set_title("u,v Coverage")
                ax.legend()
                self.canvas.draw()
                break

    def new_project(self):
        self.manipulator.set_project(Project("NewProject"))
        self.current_project_file = None
        self.project_name_input.setText(self.manipulator.get_project_name())
        self.update_all_ui()

    def save_project(self):
        if self.current_project_file:
            try:
                self.manipulator.save_project(self.current_project_file)
                self.status_bar.showMessage(f"Project saved to '{self.current_project_file}'")
            except Exception as e:
                logger.error(f"Failed to save project: {e}")
                self.status_bar.showMessage("Failed to save project")
        else:
            self.save_project_as()

    def save_project_as(self):
        project_name = self.manipulator.get_project_name()
        if not project_name:
            logger.warning("Project name is empty, using default 'Untitled'")
            project_name = "Untitled"
        default_filepath = f"{project_name}.json"
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Project As", default_filepath, "JSON Files (*.json)")
        if filepath:
            try:
                self.manipulator.save_project(filepath)
                self.current_project_file = filepath
                self.status_bar.showMessage(f"Project saved as '{filepath}'")
            except Exception as e:
                logger.error(f"Failed to save project: {e}")
                self.status_bar.showMessage("Failed to save project")

    def open_project(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "JSON Files (*.json)")
        if filepath:
            try:
                self.manipulator.load_project(filepath)
                self.current_project_file = filepath
                self.project_name_input.setText(self.manipulator.get_project_name())
                self.update_project_tree()
                self.status_bar.showMessage(f"Project loaded from '{filepath}'")
            except (FileNotFoundError, ValueError) as e:
                logger.error(f"Failed to load project: {e}")
                self.status_bar.showMessage(f"Failed to load project: {str(e)}")

    def show_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def on_project_item_selected(self):
        selected = self.project_tree.selectedItems()
        if not selected:
            return
        selected_item = selected[0].text(0)
        if selected_item == self.manipulator.get_project_name():
            self.update_all_ui()
            self.obs_selector.setCurrentIndex(0)
            self.obs_code_input.clear()
            self.canvas.figure.clf()
            self.canvas.draw()
            self.status_bar.showMessage("Selected Project: " + selected_item)
        else:
            obs = self.get_observation_by_code(selected_item)
            if obs:
                self.obs_selector.setCurrentText(selected_item)
                self.obs_code_input.setText(obs.get_observation_code())
                self.update_config_tables(obs)
                self.refresh_plot()
                self.status_bar.showMessage("Selected Observation: " + selected_item)

    def load_settings(self):
        default_settings = {
            "catalogs": {
                "sources": "catalogs/sources.dat",
                "telescopes": "catalogs/telescopes.dat"
            }
        }
        if not os.path.exists(self.settings_file):
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(default_settings, f, indent=4)
            self.settings = default_settings
            logger.info("Created default settings file")
        else:
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
                logger.info("Loaded settings from file")
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.error(f"Error loading settings: {e}. Using defaults.")
                self.settings = default_settings
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(default_settings, f, indent=4)

    def save_settings(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
            logger.info("Settings saved")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def load_catalogs(self):
        sources_path = self.settings["catalogs"]["sources"]
        telescopes_path = self.settings["catalogs"]["telescopes"]
        self.manipulator.load_catalogs(sources_path, telescopes_path)

    def show_catalog_settings(self):
        dialog = CatalogSettingsDialog(self.settings, self)
        if dialog.exec():
            new_paths = dialog.get_paths()
            old_sources = self.manipulator.get_catalog_manager().source_catalog.get_all_sources()
            old_telescopes = self.manipulator.get_catalog_manager().telescope_catalog.get_all_telescopes()
            success = True
            if new_paths["sources"] != self.settings["catalogs"]["sources"]:
                try:
                    self.manipulator.get_catalog_manager().load_source_catalog(new_paths["sources"])
                    logger.info(f"Updated sources catalog to '{new_paths['sources']}'")
                except (FileNotFoundError, ValueError) as e:
                    logger.error(f"Failed to load new sources catalog: {e}")
                    self.manipulator.get_catalog_manager().source_catalog = Sources(old_sources)
                    success = False
            if new_paths["telescopes"] != self.settings["catalogs"]["telescopes"]:
                try:
                    self.manipulator.get_catalog_manager().load_telescope_catalog(new_paths["telescopes"])
                    logger.info(f"Updated telescopes catalog to '{new_paths['telescopes']}'")
                except (FileNotFoundError, ValueError) as e:
                    logger.error(f"Failed to load new telescopes catalog: {e}")
                    self.manipulator.get_catalog_manager().telescope_catalog = Telescopes(old_telescopes)
                    success = False
            if success:
                self.settings["catalogs"] = new_paths
                self.save_settings()
                self.status_bar.showMessage("Catalogs updated successfully")
            else:
                self.status_bar.showMessage("Failed to update some catalogs; keeping old settings")

    def show_source_catalog_browser(self):
        sources = self.manipulator.get_catalog_manager().source_catalog.get_all_sources()
        dialog = CatalogBrowserDialog("Source", sources, self)
        dialog.exec()

    def show_telescope_catalog_browser(self):
        telescopes = self.manipulator.get_catalog_manager().telescope_catalog.get_all_telescopes()
        dialog = CatalogBrowserDialog("Telescope", telescopes, self)
        dialog.exec()

    def closeEvent(self, event: QCloseEvent):
        self.save_settings()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PvCoreWindow()
    window.show()
    sys.exit(app.exec())