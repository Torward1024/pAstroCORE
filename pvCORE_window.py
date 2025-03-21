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
from base.scans import Scan
from base.observation import Observation
from base.sources import Source, Sources
from base.telescopes import Telescope, SpaceTelescope, Telescopes
from base.frequencies import IF
from gui.CatalogBrowserDialog import CatalogBrowserDialog
from gui.CatalogSettingsDialog import CatalogSettingsDialog
from gui.AboutDialog import AboutDialog
from gui.SourceSelectorDialog import SourceSelectorDialog
from gui.EditSourceDialog import EditSourceDialog
from gui.TelescopeSelectorDialog import TelescopeSelectorDialog
from gui.EditTelescopeDialog import EditTelescopeDialog
from gui.PolarizationSelectorDialog import PolarizationSelectorDialog
from gui.EditScanDialog import EditScanDialog
from typing import Union
from datetime import datetime

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
        self.obs_table.setHorizontalHeaderLabels(["Code", "Type", "Sources", "Telescopes", "Frequencies", "Scans"])
        self.obs_table.horizontalHeader().setStretchLastSection(True)
        self.obs_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.obs_table.customContextMenuRequested.connect(self.show_obs_table_context_menu)
        self.obs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        self.sources_table = QTableWidget(0, 6)
        self.sources_table.setHorizontalHeaderLabels(["Name", "Name (J2000)", "Alt. Name", "RA", "Dec", "Is Active"])
        self.sources_table.horizontalHeader().setStretchLastSection(True)
        self.sources_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sources_table.customContextMenuRequested.connect(self.show_sources_table_context_menu)

        self.telescopes_table = QTableWidget(0, 8)
        self.telescopes_table.setHorizontalHeaderLabels(["Code", "Name", "X (m)", "Y (m)", "Z (m)", "Diameter (m)", "Mount Type", "Is Active"])
        self.telescopes_table.horizontalHeader().setStretchLastSection(True)
        self.telescopes_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.telescopes_table.customContextMenuRequested.connect(self.show_telescopes_context_menu)

        self.frequencies_table = QTableWidget(0, 4)  
        self.frequencies_table.setHorizontalHeaderLabels(["Frequency (MHz)", "Bandwidth (MHz)", "Polarizations", "Is Active"])
        self.telescopes_table.horizontalHeader().setStretchLastSection(True)
        self.frequencies_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.frequencies_table.customContextMenuRequested.connect(self.show_frequencies_context_menu)
        self.frequencies_table.itemChanged.connect(self.on_frequency_item_changed)

        self.scans_table = QTableWidget(0, 6)  
        self.scans_table.setHorizontalHeaderLabels(["Start", "Duration", "Source", "Telescopes", "Frequencies", "Is Active"])
        self.scans_table.horizontalHeader().setStretchLastSection(True)
        self.scans_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.scans_table.customContextMenuRequested.connect(self.show_scans_context_menu)

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
        self.status_bar.showMessage(f"Ready | {datetime.now().strftime('%B %d, %Y')}")

    def get_observation_by_code(self, code: str) -> Optional[Observation]:
        return next((obs for obs in self.manipulator.get_observations() if obs.get_observation_code() == code), None)

    def format_ra(self, ra_deg: float) -> str:
        ra_h = int(ra_deg / 15)
        ra_m = int((ra_deg / 15 - ra_h) * 60)
        ra_s = ((ra_deg / 15 - ra_h) * 60 - ra_m) * 60
        return f"{ra_h:02d}ʰ{ra_m:02d}′{ra_s:05.2f}″"

    def format_dec(self, dec_deg: float) -> str:
        sign = "-" if dec_deg < 0 else ""
        dec_deg = abs(dec_deg)
        dec_d = int(dec_deg)
        dec_m = int((dec_deg - dec_d) * 60)
        dec_s = ((dec_deg - dec_d) * 60 - dec_m) * 60
        return f"{sign}{dec_d}°{dec_m:02d}′{dec_s:05.2f}″"
    
    def show_frequencies_context_menu(self, position):
        menu = QMenu(self)
        add_action = QAction("Add Frequency", self)
        add_action.triggered.connect(self.add_frequency)
        menu.addAction(add_action)
        
        insert_action = QAction("Insert Frequency", self)
        insert_action.triggered.connect(self.insert_frequency)
        menu.addAction(insert_action)
        
        remove_action = QAction("Remove Frequency", self)
        remove_action.triggered.connect(self.remove_frequency)
        menu.addAction(remove_action)
        
        menu.addSeparator()
        
        activate_action = QAction("Activate All Frequencies", self)
        activate_action.triggered.connect(self.activate_all_frequencies)
        menu.addAction(activate_action)
        
        deactivate_action = QAction("Deactivate All Frequencies", self)
        deactivate_action.triggered.connect(self.deactivate_all_frequencies)
        menu.addAction(deactivate_action)
        
        menu.popup(self.frequencies_table.viewport().mapToGlobal(position))

    def on_scan_is_active_changed(self, scan: Scan, state: str):
        new_state = state == "True"
        if new_state != scan.isactive:
            if new_state:
                scan.activate()
                logger.info(f"Activated scan with start={scan.get_start()}")
            else:
                scan.deactivate()
                logger.info(f"Deactivated scan with start={scan.get_start()}")
            selected = self.obs_selector.currentText()
            if selected != "Select Observation...":
                obs = self.get_observation_by_code(selected)
                if obs:
                    self.update_config_tables(obs)
                    self.update_obs_table()
    
    def activate_all_frequencies(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        obs = self.get_observation_by_code(selected)
        if obs:
            obs.get_frequencies().activate_all()
            self.update_config_tables(obs)
            self.update_obs_table()
            self.status_bar.showMessage(f"All frequencies activated for '{selected}'")
    
    def deactivate_all_frequencies(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        obs = self.get_observation_by_code(selected)
        if obs:
            obs.get_frequencies().deactivate_all()
            self.update_config_tables(obs)
            self.update_obs_table()
            self.status_bar.showMessage(f"All frequencies deactivated for '{selected}'")

    def insert_frequency(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        row = self.frequencies_table.currentRow()
        obs = self.get_observation_by_code(selected)
        if obs:
            new_freq = 1000.0 + len(obs.get_frequencies().get_all_frequencies()) * 10
            default_pol = ["LL"] if obs.get_observation_type() == "VLBI" else ["RCP"]
            if_obj = IF(freq=new_freq, bandwidth=16.0, polarization=default_pol)
            if row == -1:
                self.manipulator.add_frequency_to_observation(obs, if_obj)
            else:
                self.manipulator.insert_frequency_to_observation(obs, if_obj, row)
            self.update_all_ui(selected)
            self.status_bar.showMessage(f"Inserted frequency {new_freq} MHz into '{selected}'")
    
    def remove_frequency(self):
        obs_code = self.obs_selector.currentText()
        if obs_code == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        row = self.frequencies_table.currentRow()
        if row == -1:
            self.status_bar.showMessage("Please select a frequency to remove")
            return
        obs = self.get_observation_by_code(obs_code)
        if obs:
            self.manipulator.remove_frequency_from_observation(obs, row)
            self.update_all_ui(obs_code)
            self.status_bar.showMessage("Telescope removed")        
    
    def on_frequency_item_changed(self, item):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            return
        obs = self.get_observation_by_code(selected)
        if not obs:
            return
        row = item.row()
        col = item.column()
        frequencies = obs.get_frequencies().get_all_frequencies()
        if row >= len(frequencies):
            return
        freq_obj = frequencies[row]
        old_freq = freq_obj.get_frequency()
        old_bw = freq_obj.get_bandwidth()
        old_pol = freq_obj.get_polarization()
        try:
            if col == 0:  # Frequency
                new_freq = float(item.text())
                if new_freq <= 0:
                    raise ValueError("Frequency must be positive")
                freq_obj.set_frequency(new_freq)
            elif col == 1:  # Bandwidth
                new_bw = float(item.text())
                if new_bw <= 0:
                    raise ValueError("Bandwidth must be positive")
                freq_obj.set_bandwidth(new_bw)
            elif col == 2:  # Polarization
                new_pol = item.text().strip() or None
                if new_pol:
                    freq_obj.set_polarization(new_pol)
                else:
                    freq_obj._polarization = None
            logger.info(f"Updated frequency at row {row} in observation '{selected}'")
            self.update_config_tables(obs)
            self.update_obs_table()
            self.status_bar.showMessage(f"Frequency updated in '{selected}'")
        except ValueError as e:
            logger.error(f"Invalid input for frequency at row {row}, col {col}: {e}")
            self.status_bar.showMessage(f"Error: {e}")
            if col == 0:
                freq_obj.set_frequency(old_freq)
            elif col == 1:
                freq_obj.set_bandwidth(old_bw)
            elif col == 2:
                freq_obj.set_polarization(old_pol)
            self.update_config_tables(obs)

    def update_all_ui(self, selected_obs_code=None):
        self.project_tree.clear()
        root = QTreeWidgetItem([self.manipulator.get_project_name()])
        for obs in self.manipulator.get_observations():
            QTreeWidgetItem(root, [obs.get_observation_code()])
        self.project_tree.addTopLevelItem(root)
        root.setExpanded(True)

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

        self.obs_selector.blockSignals(True)
        self.obs_selector.clear()
        self.obs_selector.addItem("Select Observation...")
        for obs in self.manipulator.get_observations():
            self.obs_selector.addItem(obs.get_observation_code())
        if selected_obs_code:
            self.obs_selector.setCurrentText(selected_obs_code)
        self.obs_selector.blockSignals(False)

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
        
        self.obs_type_combo = QComboBox()
        self.obs_type_combo.addItems(["VLBI", "SINGLE_DISH"])
        self.obs_type_combo.currentTextChanged.connect(self.update_observation_type)
        code_layout.addWidget(QLabel("Type:"))
        code_layout.addWidget(self.obs_type_combo)
        config_layout.addLayout(code_layout)

        config_subtabs = QTabWidget()
        
        sources_tab = QWidget()
        sources_layout = QVBoxLayout(sources_tab)
        sources_layout.addWidget(self.sources_table)
        sources_buttons_layout = QHBoxLayout()
        sources_buttons_layout.addWidget(QPushButton("Add Source", clicked=self.add_source))
        sources_buttons_layout.addWidget(QPushButton("Remove Source", clicked=self.remove_source))
        sources_layout.addLayout(sources_buttons_layout)
        config_subtabs.addTab(sources_tab, "Sources")
        
        telescopes_tab = QWidget()
        telescopes_layout = QVBoxLayout(telescopes_tab)
        telescopes_layout.addWidget(self.telescopes_table)
        telescopes_buttons_layout = QHBoxLayout()
        telescopes_buttons_layout.addWidget(QPushButton("Add Telescope", clicked=self.add_telescope))
        telescopes_buttons_layout.addWidget(QPushButton("Add Space Telescope", clicked=self.add_space_telescope))
        telescopes_buttons_layout.addWidget(QPushButton("Edit Telescope", clicked=self.edit_telescope))
        telescopes_buttons_layout.addWidget(QPushButton("Remove Telescope", clicked=self.remove_telescope))
        telescopes_layout.addLayout(telescopes_buttons_layout)
        self.telescopes_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.telescopes_table.customContextMenuRequested.connect(self.show_telescopes_context_menu)
        config_subtabs.addTab(telescopes_tab, "Telescopes")

        frequencies_tab = QWidget()
        frequencies_layout = QVBoxLayout(frequencies_tab)
        frequencies_layout.addWidget(self.frequencies_table)
        frequencies_buttons_layout = QHBoxLayout()
        frequencies_buttons_layout.addWidget(QPushButton("Add Frequency", clicked=self.add_frequency))
        frequencies_buttons_layout.addWidget(QPushButton("Remove Frequency", clicked=self.remove_frequency))
        frequencies_layout.addLayout(frequencies_buttons_layout)
        config_subtabs.addTab(frequencies_tab, "Frequencies")
        
        scans_tab = QWidget()
        scans_layout = QVBoxLayout(scans_tab)
        scans_layout.addWidget(self.scans_table)
        scans_buttons_layout = QHBoxLayout()
        scans_buttons_layout.addWidget(QPushButton("Add Scan", clicked=self.add_scan))
        scans_buttons_layout.addWidget(QPushButton("Remove Scan", clicked=self.remove_scan))
        scans_layout.addLayout(scans_buttons_layout)
        self.scans_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.scans_table.customContextMenuRequested.connect(self.show_scans_context_menu)
        config_subtabs.addTab(scans_tab, "Scans")
        
        config_layout.addWidget(config_subtabs)
        self.tabs.addTab(config_tab, "Configurator")

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
    
    def show_scans_context_menu(self, position):
        menu = QMenu(self)
        add_action = QAction("Add Scan", self)
        add_action.triggered.connect(self.add_scan)
        menu.addAction(add_action)
        
        insert_action = QAction("Insert Scan", self)
        insert_action.triggered.connect(self.insert_scan)
        menu.addAction(insert_action)
        
        edit_action = QAction("Edit Scan", self)
        edit_action.triggered.connect(self.edit_scan)
        menu.addAction(edit_action)
        
        remove_action = QAction("Remove Scan", self)
        remove_action.triggered.connect(self.remove_scan)
        menu.addAction(remove_action)
        
        menu.addSeparator()
        
        activate_action = QAction("Activate All", self)
        activate_action.triggered.connect(self.activate_all_scans)
        menu.addAction(activate_action)
        
        deactivate_action = QAction("Deactivate All", self)
        deactivate_action.triggered.connect(self.deactivate_all_scans)
        menu.addAction(deactivate_action)
        
        # Исполняем меню и сразу очищаем его после завершения
        menu.popup(self.scans_table.viewport().mapToGlobal(position))
        menu.aboutToHide.connect(menu.deleteLater)
    
    def insert_scan(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        obs = self.get_observation_by_code(selected)
        if not obs:
            return
        if not (obs.get_sources().get_active_sources() and obs.get_telescopes().get_active_telescopes() and obs.get_frequencies().get_active_frequencies()):
            logger.warning(f"Cannot insert scan to '{selected}': missing active sources, telescopes, or frequencies")
            self.status_bar.showMessage("Cannot insert scan: observation requires active sources, telescopes, and frequencies")
            return
        
        # Вставка ТОЛЬКО через EditScanDialog
        dialog = EditScanDialog(sources=obs.get_sources().get_active_sources(), 
                                telescopes=obs.get_telescopes(), 
                                frequencies=obs.get_frequencies(), 
                                parent=self)
        if dialog.exec():
            new_scan = dialog.get_updated_scan()
            scans = obs.get_scans()
            current_scans = scans.get_all_scans()
            row = self.scans_table.currentRow()
            if row == -1:  # Если позиция не выбрана, добавляем в конец
                try:
                    self.manipulator.add_scan_to_observation(obs, new_scan)
                except ValueError as e:
                    logger.error(f"Failed to insert scan: {e}")
                    self.status_bar.showMessage(f"Error: {e}")
                    return
            else:  # Вставка в указанную позицию
                current_scans.insert(row, new_scan)
                scans._data = current_scans
                overlap, reason = scans._check_overlap(new_scan)
                if overlap:
                    current_scans.pop(row)
                    scans._data = current_scans
                    logger.error(f"Failed to insert scan: {reason}")
                    self.status_bar.showMessage(f"Error: {reason}")
                    return
                logger.info(f"Inserted scan starting at {new_scan.get_start_datetime().strftime('%Y-%m-%d %H:%M:%S.%f')[:-4]} at index {row} in '{selected}'")
            self.update_config_tables(obs)
            self.update_obs_table()
            self.status_bar.showMessage(f"Inserted scan starting at {new_scan.get_start_datetime().strftime('%Y-%m-%d %H:%M:%S.%f')[:-4]} into '{selected}'")
    
    def remove_scan(self):
        obs_code = self.obs_selector.currentText()
        if obs_code == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        row = self.scans_table.currentRow()
        if row == -1:
            self.status_bar.showMessage("Please select a scan to remove")
            return
        obs = self.get_observation_by_code(obs_code)
        if obs:
            self.manipulator.remove_scan_from_observation(obs, row)
            self.update_all_ui(obs_code)
            self.status_bar.showMessage("Scan removed")
    
    def activate_all_scans(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        obs = self.get_observation_by_code(selected)
        if obs:
            obs.get_scans().activate_all()
            self.update_config_tables(obs)
            self.update_obs_table()
            self.status_bar.showMessage(f"All scans activated for '{selected}'")

    def deactivate_all_scans(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        obs = self.get_observation_by_code(selected)
        if obs:
            obs.get_scans().deactivate_all()
            self.update_config_tables(obs)
            self.update_obs_table()
            self.status_bar.showMessage(f"All scans deactivated for '{selected}'")
    
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
        obs = self.get_observation_by_code(selected)
        if obs:
            telescope = obs.get_telescopes().get_telescope(row)
            dialog = EditTelescopeDialog(telescope, self)
            if dialog.exec():
                updated_telescope = dialog.get_updated_telescope()
                obs.get_telescopes().set_telescope(row, updated_telescope)
                self.update_config_tables(obs)
                self.update_obs_table()
                self.status_bar.showMessage(f"Telescope '{updated_telescope.get_telescope_code()}' updated")

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
            self.manipulator.remove_telescope_from_observation(obs, row)
            self.update_all_ui(obs_code)
            self.status_bar.showMessage("Telescope removed")

    def show_telescopes_context_menu(self, position):
        menu = QMenu(self)
        add_action = QAction("Add Telescope", self)
        add_action.triggered.connect(self.add_telescope)
        menu.addAction(add_action)
        
        add_space_action = QAction("Add Space Telescope", self)
        add_space_action.triggered.connect(self.add_space_telescope)
        menu.addAction(add_space_action)
        
        insert_action = QAction("Insert Telescope", self)
        insert_action.triggered.connect(self.insert_telescope)
        menu.addAction(insert_action)
        
        edit_action = QAction("Edit Telescope", self)
        edit_action.triggered.connect(self.edit_telescope)
        menu.addAction(edit_action)
        
        remove_action = QAction("Remove Telescope", self)
        remove_action.triggered.connect(self.remove_telescope)
        menu.addAction(remove_action)
        
        menu.addSeparator()
        
        activate_action = QAction("Activate All", self)
        activate_action.triggered.connect(self.activate_all_telescopes)
        menu.addAction(activate_action)
        
        deactivate_action = QAction("Deactivate All", self)
        deactivate_action.triggered.connect(self.deactivate_all_telescopes)
        menu.addAction(deactivate_action)
        
        # Исполняем меню и сразу очищаем его после завершения
        menu.popup(self.telescopes_table.viewport().mapToGlobal(position))
        menu.aboutToHide.connect(menu.deleteLater)
    
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
            telescopes_item = QTableWidgetItem(str(len(obs.get_telescopes().get_active_telescopes())) + ' (' + str(len(obs.get_telescopes().get_all_telescopes())) + ')')
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
            self.canvas.figure.clf()
            self.canvas.draw()
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
            # Подгружаем только существующие данные
            if hasattr(obs, '_calculated_data') and obs._calculated_data:
                self._plot_existing_data(obs)
            else:
                self.canvas.figure.clf()
                self.canvas.draw()
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
            # Устанавливаем дефолтные поляризации, если текущие не подходят
            default_pols = ["LL", "RR", "LR", "RL"] if obs_type == "VLBI" else ["RCP", "LCP"]
            valid_pols = {"VLBI": ["LL", "RR", "LR", "RL"], "SINGLE_DISH": ["RCP", "LCP", "H", "V"]}
            for freq in obs.get_frequencies().get_all_frequencies():
                current_pols = freq.get_polarization()
                # Если текущие поляризации пустые или не подходят для нового типа, устанавливаем дефолтные
                if not current_pols or not all(p in valid_pols[obs_type] for p in current_pols):
                    freq.set_polarization(default_pols)
                    logger.info(f"Set default polarizations {default_pols} for frequency {freq.get_frequency()} MHz in '{selected}'")
                else:
                    logger.info(f"Kept existing polarizations {current_pols} for frequency {freq.get_frequency()} MHz in '{selected}'")
            self.update_all_ui(selected)
            self.status_bar.showMessage(f"Observation type set to '{obs_type}'")

    def update_config_tables(self, obs: Observation):
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
            combo.currentTextChanged.connect(lambda state, s=src: self.on_source_is_active_changed(s, state))
            self.sources_table.setCellWidget(row, 5, combo)
        self.sources_table.resizeColumnsToContents()
        self.sources_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.telescopes_table.setRowCount(0)
        self.telescopes_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.telescopes_table.setSelectionMode(QTableWidget.MultiSelection)
        for tel in obs.get_telescopes().get_all_telescopes():
            row = self.telescopes_table.rowCount()
            self.telescopes_table.insertRow(row)
            coords = tel.get_telescope_coordinates() if not isinstance(tel, SpaceTelescope) else [0, 0, 0]
            for col, value in enumerate([
                tel.get_telescope_code(), tel.get_telescope_name(),
                f"{coords[0]:.2f}", f"{coords[1]:.2f}", f"{coords[2]:.2f}",
                f"{tel.get_diameter():.2f}", tel.get_mount_type().value if isinstance(tel, Telescope) else "N/A"
            ]):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.telescopes_table.setItem(row, col, item)
            combo = QComboBox()
            combo.addItems(["True", "False"])
            combo.setCurrentText(str(tel.isactive))
            combo.currentTextChanged.connect(lambda state, t=tel: self.on_telescope_is_active_changed(t, state))
            self.telescopes_table.setCellWidget(row, 7, combo)
        self.telescopes_table.resizeColumnsToContents()
        self.telescopes_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.frequencies_table.blockSignals(True)
        self.frequencies_table.setRowCount(0)
        self.frequencies_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.frequencies_table.setSelectionMode(QTableWidget.MultiSelection)

        for freq in obs.get_frequencies().get_all_frequencies():
            row = self.frequencies_table.rowCount()
            self.frequencies_table.insertRow(row)
            freq_item = QTableWidgetItem(str(freq.get_frequency()))
            freq_item.setFlags(freq_item.flags() | Qt.ItemIsEditable)
            self.frequencies_table.setItem(row, 0, freq_item)
            bw_item = QTableWidgetItem(str(freq.get_bandwidth()))
            bw_item.setFlags(bw_item.flags() | Qt.ItemIsEditable)
            self.frequencies_table.setItem(row, 1, bw_item)
            pol_text = ", ".join(freq.get_polarization()) if freq.get_polarization() else "None"
            pol_button = QPushButton(pol_text)
            pol_button.clicked.connect(lambda _, f=freq: self.edit_polarizations(f))
            self.frequencies_table.setCellWidget(row, 2, pol_button)
            # Добавляем колонку Is Active
            active_combo = QComboBox()
            active_combo.addItems(["True", "False"])
            active_combo.setCurrentText(str(freq.isactive))
            active_combo.currentTextChanged.connect(lambda state, f=freq: self.on_frequency_is_active_changed(f, state))
            self.frequencies_table.setCellWidget(row, 3, active_combo)

        self.frequencies_table.resizeColumnsToContents()
        self.frequencies_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.frequencies_table.blockSignals(False)

        self.scans_table.setRowCount(0)
        all_sources = obs.get_sources().get_all_sources()
        all_tels = obs.get_telescopes().get_all_telescopes()
        all_freqs = obs.get_frequencies().get_all_frequencies()
        for scan in obs.get_scans().get_all_scans():
            row = self.scans_table.rowCount()
            self.scans_table.insertRow(row)
            start_dt = scan.get_start_datetime()
            source_name = "None (OFF SOURCE)" if scan.is_off_source else (all_sources[scan.get_source_index()].get_name() if scan.get_source_index() is not None else "None")
            telescopes_str = ", ".join(all_tels[idx].get_telescope_code() for idx in scan.get_telescope_indices())
            frequencies_str = ", ".join(str(all_freqs[idx].get_frequency()) for idx in scan.get_frequency_indices())
            for col, value in enumerate([
                start_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-4],
                str(scan.get_duration()), source_name, telescopes_str, frequencies_str
            ]):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.scans_table.setItem(row, col, item)
            active_combo = QComboBox()
            active_combo.addItems(["True", "False"])
            active_combo.setCurrentText(str(scan.isactive))
            active_combo.currentTextChanged.connect(lambda state, s=scan: self.on_scan_is_active_changed(s, state))
            self.scans_table.setCellWidget(row, 5, active_combo)
        self.scans_table.resizeColumnsToContents()
        self.scans_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    
    def edit_scan(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        row = self.scans_table.currentRow()
        if row == -1:
            self.status_bar.showMessage("Please select a scan to edit")
            return
        obs = self.get_observation_by_code(selected)
        if obs:
            scan = obs.get_scans().get_scan(row)
            dialog = EditScanDialog(scan=scan, 
                                    sources=obs.get_sources().get_active_sources(), 
                                    telescopes=obs.get_telescopes(), 
                                    frequencies=obs.get_frequencies(), 
                                    parent=self)
            if dialog.exec():
                updated_scan = dialog.get_updated_scan()
                try:
                    obs.get_scans().set_scan(updated_scan, row)
                    self.update_config_tables(obs)
                    self.update_obs_table()
                    self.status_bar.showMessage(f"Updated scan starting at {updated_scan.get_start_datetime().strftime('%Y-%m-%d %H:%M:%S.%f')[:-4]} in '{selected}'")
                except ValueError as e:
                    logger.error(f"Failed to update scan: {e}")
                    self.status_bar.showMessage(f"Error: {e}")

    def on_frequency_is_active_changed(self, freq: IF, state: str):
        new_state = state == "True"
        if new_state != freq.isactive:
            if new_state:
                freq.activate()
                logger.info(f"Activated frequency {freq.get_frequency()} MHz")
            else:
                freq.deactivate()
                logger.info(f"Deactivated frequency {freq.get_frequency()} MHz")
            selected = self.obs_selector.currentText()
            if selected != "Select Observation...":
                obs = self.get_observation_by_code(selected)
                if obs:
                    self.update_config_tables(obs)
                    self.update_obs_table()
    
    def edit_polarizations(self, freq_obj: IF):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        obs = self.get_observation_by_code(selected)
        if not obs or freq_obj not in obs.get_frequencies().get_all_frequencies():
            return
        dialog = PolarizationSelectorDialog(freq_obj.get_polarization(), obs.get_observation_type(), self)
        if dialog.exec():
            new_polarizations = dialog.get_selected_polarizations()
            freq_obj.set_polarization(new_polarizations)
            logger.info(f"Updated polarizations to {new_polarizations} for frequency {freq_obj.get_frequency()} MHz in '{selected}'")
            self.update_config_tables(obs)
            self.update_obs_table()
            self.status_bar.showMessage(f"Polarizations updated in '{selected}'")

    def show_context_menu(self, position):
        menu = QMenu(self)
        add_action = QAction("Add Observation", self)
        add_action.triggered.connect(self.add_observation)
        menu.addAction(add_action)
        
        insert_action = QAction("Insert Observation", self)
        insert_action.triggered.connect(self.insert_observation)
        menu.addAction(insert_action)
        
        remove_action = QAction("Remove Observation", self)
        remove_action.triggered.connect(self.remove_observation)
        menu.addAction(remove_action)
        
        menu.popup(self.project_tree.viewport().mapToGlobal(position))

    def show_obs_table_context_menu(self, position):
        menu = QMenu(self)
        add_action = QAction("Add Observation", self)
        add_action.triggered.connect(self.add_observation)
        menu.addAction(add_action)
        
        insert_action = QAction("Insert Observation", self)
        insert_action.triggered.connect(self.insert_observation_from_table)
        menu.addAction(insert_action)
        
        remove_action = QAction("Remove Observation", self)
        remove_action.triggered.connect(self.remove_observation_from_table)
        menu.addAction(remove_action)
        
        menu.popup(self.obs_table.viewport().mapToGlobal(position))

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
            obs = self.get_observation_by_code(selected)
            if obs:
                initial_count = len(obs.get_telescopes().get_all_telescopes())
                if row == -1:
                    for telescope in selected_telescopes:
                        self.manipulator.add_telescope_to_observation(obs, telescope)
                else:
                    for i, telescope in enumerate(selected_telescopes):
                        self.manipulator.insert_telescope_to_observation(obs, telescope, row + i)
                final_count = len(obs.get_telescopes().get_all_telescopes())
                added_count = final_count - initial_count
                if added_count > 0:
                    self.update_config_tables(obs)
                    self.update_obs_table()
                    self.status_bar.showMessage(f"Inserted {added_count} telescope(s) into '{selected}'")
                else:
                    self.status_bar.showMessage(f"No new telescopes inserted into '{selected}' (duplicates skipped)")

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
            obs = self.get_observation_by_code(selected)
            if obs:
                initial_count = len(obs.get_sources().get_active_sources())
                if row == -1:
                    for source in selected_sources:
                        self.manipulator.add_source_to_observation(obs, source)
                else:
                    for i, source in enumerate(selected_sources):
                        self.manipulator.insert_source_to_observation(obs, source, row + i)
                final_count = len(obs.get_sources().get_active_sources())
                added_count = final_count - initial_count
                if added_count > 0:
                    self.update_config_tables(obs)
                    self.update_obs_table()
                    self.status_bar.showMessage(f"Inserted {added_count} new source(s) into '{selected}'")
                else:
                    self.status_bar.showMessage(f"No new sources inserted into '{selected}' (duplicates skipped)")

    def on_source_is_active_changed(self, source: Source, state: str):
        new_state = state == "True"
        if new_state != source.isactive:
            if new_state:
                source.activate()
                logger.info(f"Activated source '{source.get_name()}'")
            else:
                source.deactivate()
                logger.info(f"Deactivated source '{source.get_name()}'")
            selected = self.obs_selector.currentText()
            if selected != "Select Observation...":
                for obs in self.manipulator.get_observations():
                    if obs.get_observation_code() == selected:
                        self.update_config_tables(obs)
                        self.update_obs_table()
                        break

    def on_telescope_is_active_changed(self, telescope: Union[Telescope, SpaceTelescope], state: str):
        new_state = state == "True"
        if new_state != telescope.isactive:
            if new_state:
                telescope.activate()
                logger.info(f"Activated telescope '{telescope.get_telescope_code()}'")
            else:
                telescope.deactivate()
                logger.info(f"Deactivated telescope '{telescope.get_telescope_code()}'")
            selected = self.obs_selector.currentText()
            if selected != "Select Observation...":
                for obs in self.manipulator.get_observations():
                    if obs.get_observation_code() == selected:
                        self.update_config_tables(obs)
                        self.update_obs_table()
                        break

    def show_sources_table_context_menu(self, position):
        menu = QMenu(self)
        add_action = QAction("Add Source", self)
        add_action.triggered.connect(self.add_source)
        menu.addAction(add_action)
        
        insert_action = QAction("Insert Source", self)
        insert_action.triggered.connect(self.insert_source)
        menu.addAction(insert_action)
        
        edit_action = QAction("Edit Source", self)
        edit_action.triggered.connect(self.edit_source)
        menu.addAction(edit_action)
        
        remove_action = QAction("Remove Source", self)
        remove_action.triggered.connect(self.remove_source)
        menu.addAction(remove_action)
        
        menu.addSeparator()
        
        activate_action = QAction("Activate All", self)
        activate_action.triggered.connect(self.activate_all_sources)
        menu.addAction(activate_action)
        
        deactivate_action = QAction("Deactivate All", self)
        deactivate_action.triggered.connect(self.deactivate_all_sources)
        menu.addAction(deactivate_action)
        
        menu.popup(self.sources_table.viewport().mapToGlobal(position))

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

    def add_space_telescope(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        # Создаём SpaceTelescope с пустым orbit_file
        default_space_telescope = SpaceTelescope(
            code=f"ST{len(self.manipulator.get_observations())}",
            name="New Space Telescope",
            orbit_file="",  # Пустой файл орбиты, пользователь задаст позже
            diameter=1.0
        )
        dialog = EditTelescopeDialog(default_space_telescope, self)
        if dialog.exec():
            new_space_telescope = dialog.get_updated_telescope()
            obs = self.get_observation_by_code(selected)
            if obs:
                try:
                    self.manipulator.add_telescope_to_observation(obs, new_space_telescope)
                    self.update_all_ui(selected)
                    self.status_bar.showMessage(f"Added space telescope '{new_space_telescope.get_telescope_code()}' to '{selected}'")
                except ValueError as e:
                    self.status_bar.showMessage(str(e))

    def add_scan(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        obs = self.get_observation_by_code(selected)
        if not obs:
            return
        if not (obs.get_sources().get_active_sources() and obs.get_telescopes().get_active_telescopes() and obs.get_frequencies().get_active_frequencies()):
            logger.warning(f"Cannot add scan to '{selected}': missing active sources, telescopes, or frequencies")
            self.status_bar.showMessage("Cannot add scan: observation requires active sources, telescopes, and frequencies")
            return
        
        dialog = EditScanDialog(sources=obs.get_sources().get_active_sources(), 
                                telescopes=obs.get_telescopes(), 
                                frequencies=obs.get_frequencies(), 
                                parent=self)
        if dialog.exec():
            new_scan = dialog.get_updated_scan()
            try:
                self.manipulator.add_scan_to_observation(obs, new_scan)
                self.update_config_tables(obs)
                self.update_obs_table()
                self.status_bar.showMessage(f"Added scan starting at {new_scan.get_start_datetime().strftime('%Y-%m-%d %H:%M:%S.%f')[:-4]} to '{selected}'")
            except ValueError as e:
                logger.error(f"Failed to add scan: {e}")
                self.status_bar.showMessage(f"Error: {e}")

    def add_frequency(self):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        obs = self.get_observation_by_code(selected)
        if not obs:
            self.status_bar.showMessage("Observation not found")
            return
        
        # Параметры новой частоты
        bandwidth = 16.0
        default_pol = ["LL"] if obs.get_observation_type() == "VLBI" else ["RCP"]
        
        # Получаем существующие частоты и сортируем их
        existing_freqs = obs.get_frequencies().get_all_frequencies()
        ranges = [(f.get_frequency() - f.get_bandwidth() / 2, f.get_frequency() + f.get_bandwidth() / 2) 
                for f in existing_freqs]
        ranges.sort()  # Сортируем по нижней границе диапазона
        
        # Ищем свободную частоту, начиная с 1000.0 МГц
        new_freq = 1000.0
        step = bandwidth  # Шаг равен ширине полосы для минимизации пересечений
        if ranges:
            for lower, upper in ranges:
                if new_freq + bandwidth / 2 <= lower:  # Если новый диапазон помещается перед текущим
                    break
                new_freq = upper + step  # Перескакиваем за верхнюю границу текущего диапазона
        
        # Создаём объект IF и добавляем его
        if_obj = IF(freq=new_freq, bandwidth=bandwidth, polarization=default_pol)
        try:
            self.manipulator.add_frequency_to_observation(obs, if_obj)
            self.update_all_ui(selected)
            self.status_bar.showMessage(f"Added frequency {new_freq} MHz to '{selected}'")
        except ValueError as e:
            logger.warning(f"Failed to add frequency {new_freq} MHz to '{selected}': {e}")
            self.status_bar.showMessage(f"Error: {e}")

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
        self.canvas.figure.clf()
        self.canvas.draw()
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
    
    def load_project(self, filepath: str) -> None:
        import json
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._project = Project.from_dict(data)
            # Проверка целостности
            for obs in self._project.get_observations():
                if not obs.validate():
                    logger.error(f"Observation '{obs.get_observation_code()}' failed validation after loading")
                    raise ValueError(f"Observation '{obs.get_observation_code()}' is invalid")
            logger.info(f"Project loaded from '{filepath}'")
        except FileNotFoundError:
            logger.error(f"Project file '{filepath}' not found")
            raise FileNotFoundError(f"Project file '{filepath}' not found!")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from '{filepath}': {e}")
            raise ValueError(f"Invalid JSON in '{filepath}': {e}")
        except ValueError as e:
            logger.error(f"Validation error during project load: {e}")
            raise

    def open_project(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "JSON Files (*.json)")
        if filepath:
            try:
                self.manipulator.load_project(filepath)
                self.current_project_file = filepath
                self.project_name_input.setText(self.manipulator.get_project_name())
                self.canvas.figure.clf()
                self.canvas.draw()
                self.update_all_ui()
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
                # Убираем автоматический refresh_plot, подгружаем только существующие данные
                if hasattr(obs, '_calculated_data') and obs._calculated_data:
                    self._plot_existing_data(obs)
                else:
                    self.canvas.figure.clf()
                    self.canvas.draw()
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