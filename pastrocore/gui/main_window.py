# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_windowPwoPwe.ui'
##
## Created by: Qt User Interface Compiler version 6.8.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QDockWidget, QHBoxLayout, QHeaderView,
    QLabel, QMainWindow, QMenu, QMenuBar,
    QProgressBar, QSizePolicy, QStatusBar, QTabWidget,
    QTreeView, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1119, 720)
        icon = QIcon()
        icon.addFile(u"./pastrocore/gui/pAstroCORE_icon.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        MainWindow.setWindowIcon(icon)
        self.actionNewProject = QAction(MainWindow)
        self.actionNewProject.setObjectName(u"actionNewProject")
        icon1 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentNew))
        self.actionNewProject.setIcon(icon1)
        self.actionOpenProject = QAction(MainWindow)
        self.actionOpenProject.setObjectName(u"actionOpenProject")
        icon2 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentOpen))
        self.actionOpenProject.setIcon(icon2)
        self.actionSaveProject = QAction(MainWindow)
        self.actionSaveProject.setObjectName(u"actionSaveProject")
        icon3 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentSave))
        self.actionSaveProject.setIcon(icon3)
        self.actionExit = QAction(MainWindow)
        self.actionExit.setObjectName(u"actionExit")
        self.actionExit.setMenuRole(QAction.MenuRole.QuitRole)
        self.actionPreferences = QAction(MainWindow)
        self.actionPreferences.setObjectName(u"actionPreferences")
        icon4 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentProperties))
        self.actionPreferences.setIcon(icon4)
        self.actionAbout = QAction(MainWindow)
        self.actionAbout.setObjectName(u"actionAbout")
        icon5 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.HelpAbout))
        self.actionAbout.setIcon(icon5)
        self.actionProject_Explorer = QAction(MainWindow)
        self.actionProject_Explorer.setObjectName(u"actionProject_Explorer")
        self.actionProject_Explorer.setCheckable(True)
        self.actionProject_Explorer.setChecked(True)
        icon6 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.EditFind))
        self.actionProject_Explorer.setIcon(icon6)
        self.actionSource_Catalog_Manager = QAction(MainWindow)
        self.actionSource_Catalog_Manager.setObjectName(u"actionSource_Catalog_Manager")
        icon7 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentPageSetup))
        self.actionSource_Catalog_Manager.setIcon(icon7)
        self.actionTelescope_Catalog_Manager = QAction(MainWindow)
        self.actionTelescope_Catalog_Manager.setObjectName(u"actionTelescope_Catalog_Manager")
        self.actionTelescope_Catalog_Manager.setIcon(icon7)
        self.actionSave_Project_As = QAction(MainWindow)
        self.actionSave_Project_As.setObjectName(u"actionSave_Project_As")
        icon8 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentSaveAs))
        self.actionSave_Project_As.setIcon(icon8)
        self.actionImport_Observation = QAction(MainWindow)
        self.actionImport_Observation.setObjectName(u"actionImport_Observation")
        icon9 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentRevert))
        self.actionImport_Observation.setIcon(icon9)
        self.actionExport_Observation = QAction(MainWindow)
        self.actionExport_Observation.setObjectName(u"actionExport_Observation")
        icon10 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.EditRedo))
        self.actionExport_Observation.setIcon(icon10)
        self.mainCentralWidget = QWidget(MainWindow)
        self.mainCentralWidget.setObjectName(u"mainCentralWidget")
        self.mainLayout = QHBoxLayout(self.mainCentralWidget)
        self.mainLayout.setObjectName(u"mainLayout")
        self.tabContainer = QTabWidget(self.mainCentralWidget)
        self.tabContainer.setObjectName(u"tabContainer")
        self.tabWelcome = QWidget()
        self.tabWelcome.setObjectName(u"tabWelcome")
        self.welcomeLayout = QVBoxLayout(self.tabWelcome)
        self.welcomeLayout.setObjectName(u"welcomeLayout")
        self.welcomeLabel = QLabel(self.tabWelcome)
        self.welcomeLabel.setObjectName(u"welcomeLabel")
        self.welcomeLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.welcomeLayout.addWidget(self.welcomeLabel)

        self.tabContainer.addTab(self.tabWelcome, "")

        self.mainLayout.addWidget(self.tabContainer)

        MainWindow.setCentralWidget(self.mainCentralWidget)
        self.mainMenuBar = QMenuBar(MainWindow)
        self.mainMenuBar.setObjectName(u"mainMenuBar")
        self.mainMenuBar.setGeometry(QRect(0, 0, 1119, 20))
        self.mainMenuBar.setNativeMenuBar(False)
        self.menuFile = QMenu(self.mainMenuBar)
        self.menuFile.setObjectName(u"menuFile")
        self.menuFile.setTearOffEnabled(False)
        self.menuOptions = QMenu(self.mainMenuBar)
        self.menuOptions.setObjectName(u"menuOptions")
        self.menuHelp = QMenu(self.mainMenuBar)
        self.menuHelp.setObjectName(u"menuHelp")
        self.menuWindow = QMenu(self.mainMenuBar)
        self.menuWindow.setObjectName(u"menuWindow")
        MainWindow.setMenuBar(self.mainMenuBar)
        self.mainStatusBar = QStatusBar(MainWindow)
        self.mainStatusBar.setObjectName(u"mainStatusBar")
        self.mainStatusBar.setAutoFillBackground(False)
        self.progressBar = QProgressBar(self.mainStatusBar)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setGeometry(QRect(0, 0, 100, 16))
        self.progressBar.setMaximumSize(QSize(200, 16))
        self.progressBar.setVisible(False)
        self.progressBar.setValue(0)
        MainWindow.setStatusBar(self.mainStatusBar)
        self.dockWidget = QDockWidget(MainWindow)
        self.dockWidget.setObjectName(u"dockWidget")
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName(u"dockWidgetContents")
        self.horizontalLayout = QHBoxLayout(self.dockWidgetContents)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.projectExplorer = QTreeView(self.dockWidgetContents)
        self.projectExplorer.setObjectName(u"projectExplorer")
        self.projectExplorer.setMinimumSize(QSize(300, 0))
        self.projectExplorer.setHeaderHidden(False)

        self.horizontalLayout.addWidget(self.projectExplorer)

        self.dockWidget.setWidget(self.dockWidgetContents)
        MainWindow.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockWidget)
        QWidget.setTabOrder(self.tabContainer, self.projectExplorer)

        self.mainMenuBar.addAction(self.menuFile.menuAction())
        self.mainMenuBar.addAction(self.menuOptions.menuAction())
        self.mainMenuBar.addAction(self.menuWindow.menuAction())
        self.mainMenuBar.addAction(self.menuHelp.menuAction())
        self.menuFile.addAction(self.actionNewProject)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionOpenProject)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionSaveProject)
        self.menuFile.addAction(self.actionSave_Project_As)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionImport_Observation)
        self.menuFile.addAction(self.actionExport_Observation)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionExit)
        self.menuOptions.addAction(self.actionPreferences)
        self.menuOptions.addSeparator()
        self.menuOptions.addAction(self.actionSource_Catalog_Manager)
        self.menuOptions.addAction(self.actionTelescope_Catalog_Manager)
        self.menuHelp.addAction(self.actionAbout)
        self.menuWindow.addAction(self.actionProject_Explorer)

        self.retranslateUi(MainWindow)
        self.actionExit.triggered.connect(MainWindow.close)
        self.actionProject_Explorer.toggled.connect(self.dockWidget.setVisible)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"pAstroCORE", None))
        MainWindow.setStyleSheet(QCoreApplication.translate("MainWindow", u"background-color: #f5f5f5; font-family: Arial;", None))
        self.actionNewProject.setText(QCoreApplication.translate("MainWindow", u"New Project", None))
        self.actionOpenProject.setText(QCoreApplication.translate("MainWindow", u"Open Project", None))
        self.actionSaveProject.setText(QCoreApplication.translate("MainWindow", u"Save Project", None))
        self.actionExit.setText(QCoreApplication.translate("MainWindow", u"Exit", None))
        self.actionPreferences.setText(QCoreApplication.translate("MainWindow", u"Preferences...", None))
        self.actionAbout.setText(QCoreApplication.translate("MainWindow", u"About", None))
        self.actionProject_Explorer.setText(QCoreApplication.translate("MainWindow", u"Project Explorer", None))
        self.actionSource_Catalog_Manager.setText(QCoreApplication.translate("MainWindow", u"Source Catalog Manager", None))
        self.actionTelescope_Catalog_Manager.setText(QCoreApplication.translate("MainWindow", u"Telescope Catalog Manager", None))
        self.actionSave_Project_As.setText(QCoreApplication.translate("MainWindow", u"Save Project As...", None))
        self.actionImport_Observation.setText(QCoreApplication.translate("MainWindow", u"Import Observation", None))
        self.actionExport_Observation.setText(QCoreApplication.translate("MainWindow", u"Export Observation", None))
        self.tabContainer.setStyleSheet(QCoreApplication.translate("MainWindow", u"QTabWidget::pane { border: 1px solid #d3d3d3; background: #ffffff; }\n"
"               QTabBar::tab { background: #e0e0e0; padding: 8px; }\n"
"               QTabBar::tab:selected { background: #ffffff; border-bottom: 2px solid #0078d7; }", None))
        self.welcomeLabel.setText(QCoreApplication.translate("MainWindow", u"Select an item in Project Explorer to begin.", None))
        self.tabContainer.setTabText(self.tabContainer.indexOf(self.tabWelcome), QCoreApplication.translate("MainWindow", u"Welcome", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"File", None))
        self.menuOptions.setTitle(QCoreApplication.translate("MainWindow", u"Options", None))
        self.menuHelp.setTitle(QCoreApplication.translate("MainWindow", u"Help", None))
        self.menuWindow.setTitle(QCoreApplication.translate("MainWindow", u"Window", None))
        self.projectExplorer.setStyleSheet(QCoreApplication.translate("MainWindow", u"border: 1px solid #d3d3d3; background-color: #ffffff;", None))
    # retranslateUi

