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
        
        self.sources_table = QTableWidget(0, 3)
        self.sources_table.setHorizontalHeaderLabels(["Name", "RA (deg)", "Dec (deg)"])
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
        
        # Создаём QTabWidget перед настройкой вкладок
        self.tabs = QTabWidget()
        # Настраиваем вкладки, где создаётся obs_selector
        self.setup_tabs()
        # Настраиваем project explorer, который использует obs_selector
        self.setup_project_explorer()
        # Добавляем tabs в layout после настройки
        main_layout.addWidget(self.tabs)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready | March 19, 2025")

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
        self.project_name_input = QLineEdit(self.manipulator.get_project_name())
        self.project_name_input.textChanged.connect(self.update_project_name)
        project_layout.addWidget(QLabel("Project Name:"))
        project_layout.addWidget(self.project_name_input)
        project_layout.addWidget(self.obs_table)
        self.tabs.addTab(project_tab, "Project")

        # Configurator Tab
        config_tab = QWidget()
        config_layout = QVBoxLayout(config_tab)
        
        # ComboBox для выбора наблюдения
        self.obs_selector = QComboBox()
        self.update_obs_selector()
        self.obs_selector.currentTextChanged.connect(self.on_obs_selected_from_combo)
        config_layout.addWidget(QLabel("Select Observation:"))
        config_layout.addWidget(self.obs_selector)
        
        # Поле для редактирования Observation Code
        code_layout = QHBoxLayout()
        code_layout.addWidget(QLabel("Observation Code:"))
        self.obs_code_input = QLineEdit()
        self.obs_code_input.textChanged.connect(self.update_observation_code)
        code_layout.addWidget(self.obs_code_input)
        config_layout.addLayout(code_layout)

        # Вкладки Sources, Telescopes, Scans, Frequencies
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
        
        # Telescopes Tab
        telescopes_tab = QWidget()
        telescopes_layout = QVBoxLayout(telescopes_tab)
        telescopes_layout.addWidget(self.telescopes_table)
        telescopes_layout.addWidget(QPushButton("Add Telescope", clicked=self.add_telescope))
        config_subtabs.addTab(telescopes_tab, "Telescopes")
        
        # Scans Tab
        scans_tab = QWidget()
        scans_layout = QVBoxLayout(scans_tab)
        scans_layout.addWidget(self.scans_table)
        scans_layout.addWidget(QPushButton("Add Scan", clicked=self.add_scan))
        config_subtabs.addTab(scans_tab, "Scans")
        
        # Frequencies Tab
        frequencies_tab = QWidget()
        frequencies_layout = QVBoxLayout(frequencies_tab)
        frequencies_layout.addWidget(self.frequencies_table)
        frequencies_layout.addWidget(QPushButton("Add Frequency", clicked=self.add_frequency))
        config_subtabs.addTab(frequencies_tab, "Frequencies")
        
        config_layout.addWidget(config_subtabs)
        self.tabs.addTab(config_tab, "Configurator")

        # Vizualizator Tab
        viz_tab = QWidget()
        viz_layout = QVBoxLayout(viz_tab)
        self.canvas = FigureCanvas(plt.Figure())
        viz_layout.addWidget(self.canvas)
        viz_layout.addWidget(QPushButton("Refresh Plot", clicked=self.refresh_plot))
        self.tabs.addTab(viz_tab, "Vizualizator")

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
            sources_item = QTableWidgetItem(str(len(obs.get_sources().get_active_sources())))
            sources_item.setFlags(sources_item.flags() & ~Qt.ItemIsEditable)
            self.obs_table.setItem(i, 2, sources_item)
            telescopes_item = QTableWidgetItem(str(len(obs.get_telescopes().get_active_telescopes())))
            telescopes_item.setFlags(telescopes_item.flags() & ~Qt.ItemIsEditable)
            self.obs_table.setItem(i, 3, telescopes_item)
            scans_item = QTableWidgetItem(str(len(obs.get_scans().get_active_scans())))
            scans_item.setFlags(scans_item.flags() & ~Qt.ItemIsEditable)
            self.obs_table.setItem(i, 4, scans_item)
            freqs_item = QTableWidgetItem(str(len(obs.get_frequencies().get_active_frequencies())))
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
            self.sources_table.setRowCount(0)
            self.telescopes_table.setRowCount(0)
            self.scans_table.setRowCount(0)
            self.frequencies_table.setRowCount(0)
            return
        for obs in self.manipulator.get_observations():
            if obs.get_observation_code() == text:
                # Отключаем сигналы перед обновлением obs_code_input
                self.obs_code_input.blockSignals(True)
                self.obs_code_input.setText(obs.get_observation_code())
                self.obs_code_input.blockSignals(False)
                self.update_config_tables(obs)
                # Синхронизация с Project Explorer
                for i in range(self.project_tree.topLevelItem(0).childCount()):
                    child = self.project_tree.topLevelItem(0).child(i)
                    if child.text(0) == text:
                        self.project_tree.setCurrentItem(child)
                        break
                break

    def update_observation_code(self, text):
        selected = self.obs_selector.currentText()
        if selected == "Select Observation..." or not text:
            return
        for obs in self.manipulator.get_observations():
            if obs.get_observation_code() == selected:
                self.manipulator._configurator.set_observation_code(obs, text)
                # Отключаем сигналы перед обновлением, чтобы избежать цикла
                self.obs_selector.blockSignals(True)
                self.obs_code_input.blockSignals(True)
                self.update_project_tree()
                self.obs_selector.setCurrentText(text)
                self.obs_selector.blockSignals(False)
                self.obs_code_input.blockSignals(False)
                break

    def update_config_tables(self, obs):
        # Sources
        self.sources_table.setRowCount(0)
        self.sources_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.sources_table.setSelectionMode(QTableWidget.MultiSelection)
        for src in obs.get_sources().get_active_sources():
            row = self.sources_table.rowCount()
            self.sources_table.insertRow(row)
            self.sources_table.setItem(row, 0, QTableWidgetItem(src.get_name()))
            self.sources_table.setItem(row, 1, QTableWidgetItem(str(src.get_ra_degrees())))
            self.sources_table.setItem(row, 2, QTableWidgetItem(str(src.get_dec_degrees())))
                
        # Telescopes
        self.telescopes_table.setRowCount(0)
        for tel in obs.get_telescopes().get_active_telescopes():
            row = self.telescopes_table.rowCount()
            self.telescopes_table.insertRow(row)
            self.telescopes_table.setItem(row, 0, QTableWidgetItem(tel.get_telescope_code()))
            self.telescopes_table.setItem(row, 1, QTableWidgetItem(tel.get_telescope_name()))
            self.telescopes_table.setItem(row, 2, QTableWidgetItem(str(tel.get_telescope_x())))
        
        # Scans
        self.scans_table.setRowCount(0)
        for scan in obs.get_scans().get_active_scans():
            row = self.scans_table.rowCount()
            self.scans_table.insertRow(row)
            self.scans_table.setItem(row, 0, QTableWidgetItem(str(scan.get_start())))
            self.scans_table.setItem(row, 1, QTableWidgetItem(str(scan.get_duration())))
            self.scans_table.setItem(row, 2, QTableWidgetItem(scan.get_source().get_name() if scan.get_source() else "None"))
        
        # Frequencies
        self.frequencies_table.setRowCount(0)
        for freq in obs.get_frequencies().get_active_frequencies():
            row = self.frequencies_table.rowCount()
            self.frequencies_table.insertRow(row)
            self.frequencies_table.setItem(row, 0, QTableWidgetItem(str(freq.get_freq())))
            self.frequencies_table.setItem(row, 1, QTableWidgetItem(str(freq.get_bandwidth())))
            self.frequencies_table.setItem(row, 2, QTableWidgetItem(freq.get_polarization() or "None"))

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
        self.update_project_tree()
        self.obs_selector.setCurrentText(obs.get_observation_code())

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
        self.update_project_tree()

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
            self.update_project_tree()

    def remove_observation_from_table(self):
        row = self.obs_table.currentRow()
        if row != -1:
            self.manipulator.remove_observation(row)
            self.update_project_tree()

    def update_project_name(self, text):
        self.manipulator._project.set_name(text)
        self.update_project_tree()

    def add_source(self):
        if not self.manipulator.get_catalog_manager().source_catalog.get_all_sources():
            logger.warning("Cannot add source: sources catalog is not loaded")
            self.status_bar.showMessage("Cannot add source: load sources catalog first")
            return
        selected = self.obs_selector.currentText()
        if selected == "Select Observation...":
            self.status_bar.showMessage("Please select an observation first")
            return
        
        # Открываем диалог выбора источников
        dialog = SourceSelectorDialog(self.manipulator.get_catalog_manager().source_catalog.get_all_sources(), self)
        if dialog.exec():
            selected_sources = dialog.get_selected_sources()
            if not selected_sources:
                self.status_bar.showMessage("No sources selected")
                return
            for obs in self.manipulator.get_observations():
                if obs.get_observation_code() == selected:
                    initial_source_count = len(obs.get_sources().get_active_sources())
                    for source in selected_sources:
                        self.manipulator._configurator.add_source(obs, source)
                    final_source_count = len(obs.get_sources().get_active_sources())
                    added_count = final_source_count - initial_source_count
                    if added_count > 0:
                        self.update_config_tables(obs)
                        self.update_obs_table()
                        self.status_bar.showMessage(f"Added {added_count} new source(s) to '{selected}'")
                    else:
                        self.status_bar.showMessage(f"No new sources added to '{selected}' (duplicates skipped)")
                    break
        
        # Открываем диалог выбора источников
        dialog = SourceSelectorDialog(self.manipulator.get_catalog_manager().source_catalog.get_all_sources(), self)
        if dialog.exec():
            selected_sources = dialog.get_selected_sources()
            if not selected_sources:
                self.status_bar.showMessage("No sources selected")
                return
            for obs in self.manipulator.get_observations():
                if obs.get_observation_code() == selected:
                    for source in selected_sources:
                        self.manipulator._configurator.add_source(obs, source)
                    self.update_config_tables(obs)
                    self.update_obs_table()
                    self.status_bar.showMessage(f"Added {len(selected_sources)} source(s) to '{selected}'")
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
        
        for obs in self.manipulator.get_observations():
            if obs.get_observation_code() == selected:
                # Удаляем источники в обратном порядке, чтобы не сбить индексы
                for row in sorted(selected_rows, reverse=True):
                    self.manipulator._configurator.remove_source(obs, row)
                self.update_config_tables(obs)  # Обновляем таблицу после удаления
                self.update_obs_table()
                self.status_bar.showMessage(f"Removed {len(selected_rows)} source(s) from '{selected}'")
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
        row = self.telescopes_table.rowCount()
        self.telescopes_table.insertRow(row)
        telescope = Telescope(code=f"T{row+1}", name=f"Telescope{row+1}", x=0.0, y=0.0, z=0.0, vx=0.0, vy=0.0, vz=0.0, isactive=True)
        for obs in self.manipulator.get_observations():
            if obs.get_observation_code() == selected:
                self.manipulator._configurator.add_telescope(obs, telescope)
                self.update_config_tables(obs)
                self.update_obs_table()
                break

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
        self.update_project_tree()

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
            self.update_obs_table()
            self.obs_selector.setCurrentIndex(0)  # "Select Observation..."
            self.obs_code_input.clear()
            self.sources_table.setRowCount(0)
            self.telescopes_table.setRowCount(0)
            self.scans_table.setRowCount(0)
            self.frequencies_table.setRowCount(0)
            self.canvas.figure.clf()
            self.canvas.draw()
            self.status_bar.showMessage("Selected Project: " + selected_item)
        else:
            for obs in self.manipulator.get_observations():
                if obs.get_observation_code() == selected_item:
                    self.obs_selector.setCurrentText(selected_item)
                    self.obs_code_input.setText(obs.get_observation_code())
                    self.update_config_tables(obs)
                    self.refresh_plot()
                    self.status_bar.showMessage("Selected Observation: " + selected_item)
                    break

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