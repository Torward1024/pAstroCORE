import sys
import os
import json
from typing import Optional
from PySide6.QtWidgets import (QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, 
                               QTabWidget, QWidget, QVBoxLayout, QLineEdit, QPushButton, 
                               QTableWidget, QTableWidgetItem, QStatusBar, QDockWidget, QHBoxLayout, QMenu, 
                               QDialog, QFileDialog, QLabel, QGridLayout)
from PySide6.QtGui import QAction, QCloseEvent
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
from base.observation import Observation, CatalogManager
from base.sources import Source, Sources
from base.telescopes import Telescope, Telescopes, SpaceTelescope

# Классы CatalogSettingsDialog и CatalogBrowserDialog остаются без изменений
class CatalogSettingsDialog(QDialog):
    def __init__(self, current_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Catalogs")
        self.current_settings = current_settings
        self.init_ui()

    def init_ui(self):
        layout = QGridLayout()
        layout.addWidget(QLabel("Sources Catalog:"), 0, 0)
        self.sources_path = QLineEdit(self.current_settings["catalogs"]["sources"])
        layout.addWidget(self.sources_path, 0, 1)
        sources_browse_btn = QPushButton("Browse", clicked=self.browse_sources)
        layout.addWidget(sources_browse_btn, 0, 2)
        layout.addWidget(QLabel("Telescopes Catalog:"), 1, 0)
        self.telescopes_path = QLineEdit(self.current_settings["catalogs"]["telescopes"])
        layout.addWidget(self.telescopes_path, 1, 1)
        telescopes_browse_btn = QPushButton("Browse", clicked=self.browse_telescopes)
        layout.addWidget(telescopes_browse_btn, 1, 2)
        ok_btn = QPushButton("OK", clicked=self.accept)
        cancel_btn = QPushButton("Cancel", clicked=self.reject)
        layout.addWidget(ok_btn, 2, 1)
        layout.addWidget(cancel_btn, 2, 2)
        self.setLayout(layout)

    def browse_sources(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Sources Catalog", "", "Data Files (*.dat)")
        if path:
            self.sources_path.setText(path)

    def browse_telescopes(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Telescopes Catalog", "", "Data Files (*.dat)")
        if path:
            self.telescopes_path.setText(path)

    def get_paths(self):
        return {
            "sources": self.sources_path.text(),
            "telescopes": self.telescopes_path.text()
        }

class CatalogBrowserDialog(QDialog):
    def __init__(self, catalog_type, catalog_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{catalog_type} Catalog Browser")
        self.catalog_type = catalog_type
        self.catalog_data = catalog_data
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        if self.catalog_type == "Source":
            self.table = QTableWidget(len(self.catalog_data), 5)
            self.table.setHorizontalHeaderLabels(["B1950 Name", "J2000 Name", "Alt Name", "RA", "Dec"])
            for row, source in enumerate(self.catalog_data):
                # Заполняем ячейки
                self.table.setItem(row, 0, QTableWidgetItem(source.get_name()))
                self.table.setItem(row, 1, QTableWidgetItem(source.get_name_J2000() or ""))
                self.table.setItem(row, 2, QTableWidgetItem(source.get_alt_name() or ""))
                
                # Форматируем RA (DD°MM′SS.SS″)
                ra_deg = source.get_ra_degrees()
                ra_d = int(ra_deg)
                ra_m = int((ra_deg - ra_d) * 60)
                ra_s = ((ra_deg - ra_d) * 60 - ra_m) * 60
                ra_str = f"{ra_d}°{ra_m:02d}′{ra_s:05.2f}″"
                ra_item = QTableWidgetItem(ra_str)
                ra_item.setFlags(ra_item.flags() & ~Qt.ItemIsEditable)  # Не редактируемый
                self.table.setItem(row, 3, ra_item)

                # Форматируем DEC (HHʰMM′SS.SS″)
                dec_deg = source.get_dec_degrees()
                sign = "-" if dec_deg < 0 else ""
                dec_deg = abs(dec_deg)
                dec_h = int(dec_deg / 15)  # Переводим в часы (1h = 15°)
                dec_m = int((dec_deg / 15 - dec_h) * 60)
                dec_s = ((dec_deg / 15 - dec_h) * 60 - dec_m) * 60
                dec_str = f"{sign}{dec_h:02d}ʰ{dec_m:02d}′{dec_s:05.2f}″"
                dec_item = QTableWidgetItem(dec_str)
                dec_item.setFlags(dec_item.flags() & ~Qt.ItemIsEditable)  # Не редактируемый
                self.table.setItem(row, 4, dec_item)

        else:  # Telescope
            self.table = QTableWidget(len(self.catalog_data), 5)
            self.table.setHorizontalHeaderLabels(["Code", "Name", "X (m)", "Y (m)", "Z (m)"])
            for row, telescope in enumerate(self.catalog_data):
                self.table.setItem(row, 0, QTableWidgetItem(telescope.get_telescope_code()))
                self.table.setItem(row, 1, QTableWidgetItem(telescope.get_telescope_name()))
                self.table.setItem(row, 2, QTableWidgetItem(str(telescope.get_telescope_x())))
                self.table.setItem(row, 3, QTableWidgetItem(str(telescope.get_telescope_y())))
                self.table.setItem(row, 4, QTableWidgetItem(str(telescope.get_telescope_z())))
                # Делаем все ячейки не редактируемыми
                for col in range(5):
                    item = self.table.item(row, col)
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)

        # Настраиваем таблицу
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # Запрещаем редактирование
        self.table.resizeColumnsToContents()  # Подгоняем ширину столбцов под содержимое
        self.table.horizontalHeader().setStretchLastSection(True)  # Растягиваем последний столбец
        layout.addWidget(self.table)

        # Кнопка Close
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Сдвигаем кнопку вправо
        close_btn = QPushButton("Close")
        close_btn.setFixedSize(80, 30)  # Фиксированный размер кнопки
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        # Устанавливаем минимальный размер окна
        self.setMinimumSize(500, 400)  # Увеличенный размер для видимости всех столбцов


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
        self.load_settings()
        self.catalog_manager = CatalogManager()
        self.load_catalogs()

        self.obs_table = QTableWidget(0, 4)
        self.obs_table.setHorizontalHeaderLabels(["Code", "Type", "Sources", "Telescopes"])
        self.sources_table = QTableWidget(0, 3)
        self.sources_table.setHorizontalHeaderLabels(["Name", "RA (deg)", "Dec (deg)"])
        self.telescopes_table = QTableWidget(0, 3)
        self.telescopes_table.setHorizontalHeaderLabels(["Code", "Name", "X (m)"])

        self.setup_menu()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        self.setup_project_explorer()
        self.tabs = QTabWidget()
        self.setup_tabs()
        main_layout.addWidget(self.tabs)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready | March 19, 2025")

    def setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        file_menu.addAction("New Project", self.new_project)
        file_menu.addAction("Open", self.open_project)
        file_menu.addAction("Save", self.save_project)
        file_menu.addAction("Exit", self.close)

        settings_menu = menubar.addMenu("Settings")
        settings_menu.addAction("Set Catalogs...", self.show_catalog_settings)
        settings_menu.addAction("Source Catalog Browser", self.show_source_catalog_browser)
        settings_menu.addAction("Telescope Catalog Browser", self.show_telescope_catalog_browser)

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
        self.project_name_input = QLineEdit(self.manipulator.get_project_name())
        self.project_name_input.textChanged.connect(self.update_project_name)
        project_layout.addWidget(QLabel("Project Name:"))
        project_layout.addWidget(self.project_name_input)
        project_layout.addWidget(self.obs_table)
        project_layout.addWidget(QPushButton("Add Observation", clicked=self.add_observation))
        self.tabs.addTab(project_tab, "Project")

        config_tab = QTabWidget()
        sources_tab = QWidget()
        sources_layout = QVBoxLayout(sources_tab)
        sources_layout.addWidget(self.sources_table)
        sources_layout.addWidget(QPushButton("Add Source", clicked=self.add_source))
        config_tab.addTab(sources_tab, "Sources")
        telescopes_tab = QWidget()
        telescopes_layout = QVBoxLayout(telescopes_tab)
        telescopes_layout.addWidget(self.telescopes_table)
        telescopes_layout.addWidget(QPushButton("Add Telescope", clicked=self.add_telescope))
        config_tab.addTab(telescopes_tab, "Telescopes")
        self.tabs.addTab(config_tab, "Configurator")

        viz_tab = QWidget()
        viz_layout = QVBoxLayout(viz_tab)
        self.canvas = FigureCanvas(plt.Figure())
        viz_layout.addWidget(self.canvas)
        viz_layout.addWidget(QPushButton("Refresh Plot", clicked=self.refresh_plot))
        self.tabs.addTab(viz_tab, "Vizualizator")

    def update_project_tree(self):
        self.project_tree.clear()
        root = QTreeWidgetItem([self.manipulator.get_project_name()])
        for obs in self.manipulator._project.get_observations():
            QTreeWidgetItem(root, [obs.get_observation_code()])
        self.project_tree.addTopLevelItem(root)
        root.setExpanded(True)
        self.update_obs_table()

    def update_obs_table(self):
        self.obs_table.setRowCount(0)
        for obs in self.manipulator._project.get_observations():
            row = self.obs_table.rowCount()
            self.obs_table.insertRow(row)
            self.obs_table.setItem(row, 0, QTableWidgetItem(obs.get_observation_code()))
            self.obs_table.setItem(row, 1, QTableWidgetItem(obs.get_observation_type()))
            self.obs_table.setItem(row, 2, QTableWidgetItem(str(len(obs.get_sources().get_active_sources()))))
            self.obs_table.setItem(row, 3, QTableWidgetItem(str(len(obs.get_telescopes().get_active_telescopes()))))

    def show_context_menu(self, position):
        menu = QMenu()
        menu.addAction("Add Observation", self.add_observation)
        menu.addAction("Insert Observation", self.insert_observation)
        menu.addAction("Remove Observation", self.remove_observation)
        menu.exec(self.project_tree.viewport().mapToGlobal(position))

    def add_observation(self):
        obs = Observation(observation_code=f"Obs{len(self.manipulator._project.get_observations())+1}", observation_type="VLBI")
        self.manipulator.add_observation(obs)
        self.update_project_tree()

    def insert_observation(self):
        selected = self.project_tree.selectedItems()
        if not selected or selected[0].text(0) == self.manipulator.get_project_name():
            self.add_observation()
            return
        index = self.project_tree.indexOfTopLevelItem(self.project_tree.topLevelItem(0)) + 1
        for i, obs in enumerate(self.manipulator._project.get_observations()):
            if obs.get_observation_code() == selected[0].text(0):
                index = i
                break
        new_obs = Observation(observation_code=f"Obs{len(self.manipulator._project.get_observations())+1}", observation_type="VLBI")
        self.manipulator._project._observations.insert(index, new_obs)
        self.update_project_tree()

    def remove_observation(self):
        selected = self.project_tree.selectedItems()
        if not selected or selected[0].text(0) == self.manipulator.get_project_name():
            return
        index = self.project_tree.indexOfTopLevelItem(self.project_tree.topLevelItem(0)) + 1
        for i, obs in enumerate(self.manipulator._project.get_observations()):
            if obs.get_observation_code() == selected[0].text(0):
                self.manipulator.remove_observation(i)
                break
        self.update_project_tree()

    def update_project_name(self, text):
        self.manipulator._project.set_name(text)
        self.update_project_tree()

    def add_source(self):
        if not self.catalog_manager.source_catalog.get_all_sources():
            logger.warning("Cannot add source: sources catalog is not loaded")
            self.status_bar.showMessage("Cannot add source: load sources catalog first")
            return
        row = self.sources_table.rowCount()
        self.sources_table.insertRow(row)
        source = Source(name=f"Source{row+1}", ra_h=0, ra_m=0, ra_s=0, de_d=0, de_m=0, de_s=0)
        selected = self.project_tree.selectedItems()
        if selected and selected[0].text(0) != self.manipulator.get_project_name():
            for obs in self.manipulator._project.get_observations():
                if obs.get_observation_code() == selected[0].text(0):
                    self.configurator.add_source(obs, source)
                    break
        self.sources_table.setItem(row, 0, QTableWidgetItem(source.get_name()))
        self.sources_table.setItem(row, 1, QTableWidgetItem(str(source.get_ra_degrees())))
        self.sources_table.setItem(row, 2, QTableWidgetItem(str(source.get_dec_degrees())))

    def add_telescope(self):
        if not self.catalog_manager.telescope_catalog.get_all_telescopes():
            logger.warning("Cannot add telescope: telescopes catalog is not loaded")
            self.status_bar.showMessage("Cannot add telescope: load telescopes catalog first")
            return
        row = self.telescopes_table.rowCount()
        self.telescopes_table.insertRow(row)
        telescope = Telescope(code=f"T{row+1}", name=f"Telescope{row+1}", x=0.0, y=0.0, z=0.0, vx=0.0, vy=0.0, vz=0.0, isactive=True)
        selected = self.project_tree.selectedItems()
        if selected and selected[0].text(0) != self.manipulator.get_project_name():
            for obs in self.manipulator._project.get_observations():
                if obs.get_observation_code() == selected[0].text(0):
                    self.configurator.add_telescope(obs, telescope)
                    break
        self.telescopes_table.setItem(row, 0, QTableWidgetItem(telescope.code))
        self.telescopes_table.setItem(row, 1, QTableWidgetItem(telescope.name))
        self.telescopes_table.setItem(row, 2, QTableWidgetItem(str(telescope.x)))

    def refresh_plot(self):
        selected = self.project_tree.selectedItems()
        if not selected or selected[0].text(0) == self.manipulator.get_project_name():
            self.canvas.figure.clf()
            self.canvas.draw()
            return
        for obs in self.manipulator._project.get_observations():
            if obs.get_observation_code() == selected[0].text(0):
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
        self.update_project_tree()

    def save_project(self):
        self.manipulator.save_project("project.json")
        self.status_bar.showMessage("Project saved")

    def open_project(self):
        self.manipulator.load_project("project.json")
        self.update_project_tree()
        self.status_bar.showMessage("Project loaded")

    def on_project_item_selected(self):
        selected = self.project_tree.selectedItems()
        if not selected:
            return
        selected_item = selected[0].text(0)
        if selected_item == self.manipulator.get_project_name():
            self.update_obs_table()
            self.sources_table.setRowCount(0)
            self.telescopes_table.setRowCount(0)
            self.canvas.figure.clf()
            self.canvas.draw()
            self.status_bar.showMessage("Selected Project: " + selected_item)
        else:
            for obs in self.manipulator._project.get_observations():
                if obs.get_observation_code() == selected_item:
                    self.sources_table.setRowCount(0)
                    for src in obs.get_sources().get_active_sources():
                        row = self.sources_table.rowCount()
                        self.sources_table.insertRow(row)
                        self.sources_table.setItem(row, 0, QTableWidgetItem(src.get_name()))
                        self.sources_table.setItem(row, 1, QTableWidgetItem(str(src.get_ra_degrees())))
                        self.sources_table.setItem(row, 2, QTableWidgetItem(str(src.get_dec_degrees())))
                    self.telescopes_table.setRowCount(0)
                    for tel in obs.get_telescopes().get_active_telescopes():
                        row = self.telescopes_table.rowCount()
                        self.telescopes_table.insertRow(row)
                        self.telescopes_table.setItem(row, 0, QTableWidgetItem(tel.code))
                        self.telescopes_table.setItem(row, 1, QTableWidgetItem(tel.name))
                        self.telescopes_table.setItem(row, 2, QTableWidgetItem(str(tel.x)))
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
        if os.path.exists(sources_path):
            try:
                self.catalog_manager.load_source_catalog(sources_path)
                logger.info(f"Loaded sources catalog from '{sources_path}'")
            except (FileNotFoundError, ValueError) as e:
                logger.error(f"Failed to load sources catalog: {e}")
        else:
            logger.warning(f"Sources catalog file '{sources_path}' not found")
        if os.path.exists(telescopes_path):
            try:
                self.catalog_manager.load_telescope_catalog(telescopes_path)
                logger.info(f"Loaded telescopes catalog from '{telescopes_path}'")
            except (FileNotFoundError, ValueError) as e:
                logger.error(f"Failed to load telescopes catalog: {e}")
        else:
            logger.warning(f"Telescopes catalog file '{telescopes_path}' not found")

    def show_catalog_settings(self):
        dialog = CatalogSettingsDialog(self.settings, self)
        if dialog.exec():
            new_paths = dialog.get_paths()
            old_sources = self.catalog_manager.source_catalog.get_all_sources()
            old_telescopes = self.catalog_manager.telescope_catalog.get_all_telescopes()
            success = True
            if new_paths["sources"] != self.settings["catalogs"]["sources"]:
                try:
                    self.catalog_manager.load_source_catalog(new_paths["sources"])
                    logger.info(f"Updated sources catalog to '{new_paths['sources']}'")
                except (FileNotFoundError, ValueError) as e:
                    logger.error(f"Failed to load new sources catalog: {e}")
                    self.catalog_manager.source_catalog = Sources(old_sources)
                    success = False
            if new_paths["telescopes"] != self.settings["catalogs"]["telescopes"]:
                try:
                    self.catalog_manager.load_telescope_catalog(new_paths["telescopes"])
                    logger.info(f"Updated telescopes catalog to '{new_paths['telescopes']}'")
                except (FileNotFoundError, ValueError) as e:
                    logger.error(f"Failed to load new telescopes catalog: {e}")
                    self.catalog_manager.telescope_catalog = Telescopes(old_telescopes)
                    success = False
            if success:
                self.settings["catalogs"] = new_paths
                self.save_settings()
                self.status_bar.showMessage("Catalogs updated successfully")
            else:
                self.status_bar.showMessage("Failed to update some catalogs; keeping old settings")

    def show_source_catalog_browser(self):
        sources = self.catalog_manager.source_catalog.get_all_sources()
        dialog = CatalogBrowserDialog("Source", sources, self)
        dialog.exec()

    def show_telescope_catalog_browser(self):
        telescopes = self.catalog_manager.telescope_catalog.get_all_telescopes()
        dialog = CatalogBrowserDialog("Telescope", telescopes, self)
        dialog.exec()

    def closeEvent(self, event: QCloseEvent):
        """Переопределяем метод закрытия окна для сохранения настроек."""
        self.save_settings()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PvCoreWindow()
    window.show()
    sys.exit(app.exec())