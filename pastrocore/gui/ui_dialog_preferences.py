# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_preferenceslHwpJt.ui'
##
## Created by: Qt User Interface Compiler version 6.8.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
    QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QTabWidget,
    QWidget)

class Ui_PreferencesDialog(object):
    def setupUi(self, PreferencesDialog):
        if not PreferencesDialog.objectName():
            PreferencesDialog.setObjectName(u"PreferencesDialog")
        PreferencesDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        PreferencesDialog.resize(450, 350)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(PreferencesDialog.sizePolicy().hasHeightForWidth())
        PreferencesDialog.setSizePolicy(sizePolicy)
        PreferencesDialog.setMinimumSize(QSize(450, 350))
        PreferencesDialog.setMaximumSize(QSize(450, 350))
        icon = QIcon()
        icon.addFile(u":/icons/preferences.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        PreferencesDialog.setWindowIcon(icon)
        PreferencesDialog.setStyleSheet(u"background-color: #ffffff; font-family: Arial;")
        PreferencesDialog.setModal(True)
        self.gridLayout = QGridLayout(PreferencesDialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.tabWidget = QTabWidget(PreferencesDialog)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.gridLayout_3 = QGridLayout(self.tab)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.lbl_telescopes_catalog_path = QLabel(self.tab)
        self.lbl_telescopes_catalog_path.setObjectName(u"lbl_telescopes_catalog_path")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(9)
        self.lbl_telescopes_catalog_path.setFont(font)

        self.gridLayout_2.addWidget(self.lbl_telescopes_catalog_path, 1, 0, 1, 1)

        self.openSourcesCatalogButton = QPushButton(self.tab)
        self.openSourcesCatalogButton.setObjectName(u"openSourcesCatalogButton")
        self.openSourcesCatalogButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff; /* \u0421\u0432\u0435\u0442\u043b\u0435\u0435 \u043f\u0440\u0438 \u043d\u0430\u0432\u0435\u0434\u0435\u043d\u0438\u0438 */\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5; /* \u0422\u0435\u043c\u043d\u0435\u0435 \u043f\u0440\u0438 \u043d\u0430\u0436\u0430\u0442\u0438\u0438 */\n"
"    padding-top: 7px; /* \u041b\u0435\u0433\u043a\u043e\u0435 \u0441\u043c\u0435\u0449\u0435\u043d\u0438\u0435 \u0432\u043d\u0438\u0437 \u0434\u043b\u044f \u044d\u0444\u0444\u0435\u043a\u0442\u0430 \"\u043f\u0440\u043e\u0434\u0430\u0432\u043b\u0438\u0432\u0430\u043d\u0438\u044f\" */\n"
"    padding-bottom: 5px;\n"
"}")
        self.openSourcesCatalogButton.setAutoDefault(False)
        self.openSourcesCatalogButton.setFlat(True)

        self.gridLayout_2.addWidget(self.openSourcesCatalogButton, 0, 2, 1, 1)

        self.sourcesCatalogPath = QLineEdit(self.tab)
        self.sourcesCatalogPath.setObjectName(u"sourcesCatalogPath")
        self.sourcesCatalogPath.setStyleSheet(u"QLineEdit {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    border-radius: 3px;\n"
"}\n"
"QLineEdit[readOnly=\"true\"] {\n"
"    border: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"}\n"
"QLineEdit[readOnly=\"false\"] {\n"
"    border: 1px solid #0078d7;\n"
"    background-color: #f0f6ff;\n"
"}\n"
"QLineEdit[readOnly=\"false\"]:hover {\n"
"    border: 1px solid #1a8cff;\n"
"}\n"
"QLineEdit[readOnly=\"false\"]:focus {\n"
"    border: 1px solid #005bb5;\n"
"    background-color: #ffffff;\n"
"}")

        self.gridLayout_2.addWidget(self.sourcesCatalogPath, 0, 1, 1, 1)

        self.lbl_sources_catalog_path = QLabel(self.tab)
        self.lbl_sources_catalog_path.setObjectName(u"lbl_sources_catalog_path")
        self.lbl_sources_catalog_path.setFont(font)

        self.gridLayout_2.addWidget(self.lbl_sources_catalog_path, 0, 0, 1, 1)

        self.openTelescopesCatalogButton = QPushButton(self.tab)
        self.openTelescopesCatalogButton.setObjectName(u"openTelescopesCatalogButton")
        self.openTelescopesCatalogButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff; /* \u0421\u0432\u0435\u0442\u043b\u0435\u0435 \u043f\u0440\u0438 \u043d\u0430\u0432\u0435\u0434\u0435\u043d\u0438\u0438 */\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5; /* \u0422\u0435\u043c\u043d\u0435\u0435 \u043f\u0440\u0438 \u043d\u0430\u0436\u0430\u0442\u0438\u0438 */\n"
"    padding-top: 7px; /* \u041b\u0435\u0433\u043a\u043e\u0435 \u0441\u043c\u0435\u0449\u0435\u043d\u0438\u0435 \u0432\u043d\u0438\u0437 \u0434\u043b\u044f \u044d\u0444\u0444\u0435\u043a\u0442\u0430 \"\u043f\u0440\u043e\u0434\u0430\u0432\u043b\u0438\u0432\u0430\u043d\u0438\u044f\" */\n"
"    padding-bottom: 5px;\n"
"}")
        self.openTelescopesCatalogButton.setAutoDefault(False)
        self.openTelescopesCatalogButton.setFlat(True)

        self.gridLayout_2.addWidget(self.openTelescopesCatalogButton, 1, 2, 1, 1)

        self.comboLogging = QComboBox(self.tab)
        self.comboLogging.setObjectName(u"comboLogging")
        self.comboLogging.setStyleSheet(u"QComboBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    border-radius: 3px;\n"
"    background-color: #f9f9f9; /* \u0411\u0430\u0437\u043e\u0432\u044b\u0439 \u0444\u043e\u043d, \u043a\u0430\u043a \u0443 readOnly QLineEdit */\n"
"    border: 1px solid #d3d3d3; /* \u0411\u0430\u0437\u043e\u0432\u0430\u044f \u0433\u0440\u0430\u043d\u0438\u0446\u0430, \u043a\u0430\u043a \u0443 readOnly QLineEdit */\n"
"}\n"
"\n"
"QComboBox:editable {\n"
"    background-color: #f0f6ff; /* \u0424\u043e\u043d \u0434\u043b\u044f \u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u0443\u0435\u043c\u043e\u0433\u043e \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044f, \u043a\u0430\u043a \u0443 readOnly=\"false\" */\n"
"    border: 1px solid #0078d7; /* \u0413\u0440\u0430\u043d\u0438\u0446\u0430 \u0434\u043b\u044f \u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u0443\u0435\u043c\u043e\u0433\u043e \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044f */\n"
"}\n"
"\n"
"QCombo"
                        "Box:editable:hover {\n"
"    border: 1px solid #1a8cff; /* \u0413\u0440\u0430\u043d\u0438\u0446\u0430 \u043f\u0440\u0438 \u043d\u0430\u0432\u0435\u0434\u0435\u043d\u0438\u0438, \u043a\u0430\u043a \u0443 readOnly=\"false\":hover */\n"
"}\n"
"\n"
"QComboBox:editable:focus {\n"
"    border: 1px solid #005bb5; /* \u0413\u0440\u0430\u043d\u0438\u0446\u0430 \u043f\u0440\u0438 \u0444\u043e\u043a\u0443\u0441\u0435, \u043a\u0430\u043a \u0443 readOnly=\"false\":focus */\n"
"    background-color: #ffffff; /* \u0424\u043e\u043d \u043f\u0440\u0438 \u0444\u043e\u043a\u0443\u0441\u0435, \u043a\u0430\u043a \u0443 readOnly=\"false\":focus */\n"
"}\n"
"\n"
"QComboBox:!editable {\n"
"    background-color: #f0f6ff; /* \u0424\u043e\u043d \u0434\u043b\u044f \u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u0443\u0435\u043c\u043e\u0433\u043e \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044f, \u043a\u0430\u043a \u0443 readOnly=\"false\" */\n"
"    border: 1px solid #0078d7; /* \u0413\u0440\u0430\u043d\u0438\u0446\u0430 \u0434\u043b"
                        "\u044f \u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u0443\u0435\u043c\u043e\u0433\u043e \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044f */\n"
"}\n"
"\n"
"QComboBox:!editable:hover {\n"
"    border: 1px solid #1a8cff; /* \u0413\u0440\u0430\u043d\u0438\u0446\u0430 \u043f\u0440\u0438 \u043d\u0430\u0432\u0435\u0434\u0435\u043d\u0438\u0438, \u043a\u0430\u043a \u0443 readOnly=\"false\":hover */\n"
"}\n"
"\n"
"QComboBox:!editable:focus {\n"
"    border: 1px solid #005bb5; /* \u0413\u0440\u0430\u043d\u0438\u0446\u0430 \u043f\u0440\u0438 \u0444\u043e\u043a\u0443\u0441\u0435, \u043a\u0430\u043a \u0443 readOnly=\"false\":focus */\n"
"    background-color: #ffffff; /* \u0424\u043e\u043d \u043f\u0440\u0438 \u0444\u043e\u043a\u0443\u0441\u0435, \u043a\u0430\u043a \u0443 readOnly=\"false\":focus */\n"
"}\n"
"\n"
"/* \u0421\u0442\u0438\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u043a\u043d\u043e\u043f\u043a\u0438 \u0441\u043e \u0441\u0442\u0440\u0435\u043b\u043a\u043e\u0439 */\n"
"QComboBox::drop-down {\n"
"    sub"
                        "control-origin: padding;\n"
"    subcontrol-position: right;\n"
"    width: 20px;\n"
"    border-left: 1px solid #d3d3d3; /* \u0414\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u0430 \u0433\u0440\u0430\u043d\u0438\u0446\u0430 \u0434\u043b\u044f \u0432\u0438\u0437\u0443\u0430\u043b\u044c\u043d\u043e\u0433\u043e \u0440\u0430\u0437\u0434\u0435\u043b\u0435\u043d\u0438\u044f */\n"
"    border-top-right-radius: 3px;\n"
"    border-bottom-right-radius: 3px;\n"
"    background-color: #f9f9f9; /* \u0424\u043e\u043d \u043a\u043d\u043e\u043f\u043a\u0438, \u0441\u043e\u0432\u043f\u0430\u0434\u0430\u044e\u0449\u0438\u0439 \u0441 \u043e\u0441\u043d\u043e\u0432\u043d\u044b\u043c */\n"
"}\n"
"\n"
"QComboBox::drop-down:hover {\n"
"    background-color: #0078d7; /* \u041b\u0451\u0433\u043a\u043e\u0435 \u0432\u044b\u0434\u0435\u043b\u0435\u043d\u0438\u0435 \u043f\u0440\u0438 \u043d\u0430\u0432\u0435\u0434\u0435\u043d\u0438\u0438 */\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    /* \u0421\u0442"
                        "\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0430\u044f \u0441\u0442\u0440\u0435\u043b\u043a\u0430 Qt, \u0435\u0441\u043b\u0438 \u043d\u0435\u0442 \u0438\u043a\u043e\u043d\u043a\u0438 */\n"
"    /* \u0415\u0441\u043b\u0438 \u0435\u0441\u0442\u044c \u0438\u043a\u043e\u043d\u043a\u0430, \u0440\u0430\u0441\u043a\u043e\u043c\u043c\u0435\u043d\u0442\u0438\u0440\u0443\u0439\u0442\u0435: */\n"
"    image: url(:/icons/down_arrow_icon.svg);\n"
"}\n"
"\n"
"/* \u0421\u0442\u0438\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u0432\u044b\u043f\u0430\u0434\u0430\u044e\u0449\u0435\u0433\u043e \u0441\u043f\u0438\u0441\u043a\u0430 */\n"
"QComboBox QAbstractItemView {\n"
"    font-family: Arial;\n"
"    font-size: 12pt;\n"
"    color: #333333;\n"
"    background-color: #ffffff;\n"
"    border: 1px solid #d3d3d3;\n"
"    selection-background-color: #0078d7;\n"
"    selection-color: #ffffff;\n"
"    padding: 1px;\n"
"}\n"
"\n"
"QComboBox QAbstractItemView::item {\n"
"    padding: 4px;\n"
"    min-height: 20px;\n"
"}\n"
"\n"
"QComboBo"
                        "x QAbstractItemView::item:hover {\n"
"    background-color: #0078d7;\n"
"}")

        self.gridLayout_2.addWidget(self.comboLogging, 2, 1, 1, 1)

        self.telescopesCatalogPath = QLineEdit(self.tab)
        self.telescopesCatalogPath.setObjectName(u"telescopesCatalogPath")
        self.telescopesCatalogPath.setStyleSheet(u"QLineEdit {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    border-radius: 3px;\n"
"}\n"
"QLineEdit[readOnly=\"true\"] {\n"
"    border: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"}\n"
"QLineEdit[readOnly=\"false\"] {\n"
"    border: 1px solid #0078d7;\n"
"    background-color: #f0f6ff;\n"
"}\n"
"QLineEdit[readOnly=\"false\"]:hover {\n"
"    border: 1px solid #1a8cff;\n"
"}\n"
"QLineEdit[readOnly=\"false\"]:focus {\n"
"    border: 1px solid #005bb5;\n"
"    background-color: #ffffff;\n"
"}")

        self.gridLayout_2.addWidget(self.telescopesCatalogPath, 1, 1, 1, 1)

        self.labelLogging = QLabel(self.tab)
        self.labelLogging.setObjectName(u"labelLogging")

        self.gridLayout_2.addWidget(self.labelLogging, 2, 0, 1, 1)

        self.chkClearLog = QCheckBox(self.tab)
        self.chkClearLog.setObjectName(u"chkClearLog")

        self.gridLayout_2.addWidget(self.chkClearLog, 3, 0, 1, 3)


        self.gridLayout_3.addLayout(self.gridLayout_2, 0, 0, 1, 2)

        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.gridLayout_4 = QGridLayout(self.tab_2)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.labelTimestep = QLabel(self.tab_2)
        self.labelTimestep.setObjectName(u"labelTimestep")

        self.horizontalLayout.addWidget(self.labelTimestep)

        self.timeStepSpin = QDoubleSpinBox(self.tab_2)
        self.timeStepSpin.setObjectName(u"timeStepSpin")
        self.timeStepSpin.setStyleSheet(u"/* Base style for QDoubleSpinBox */\n"
"QDoubleSpinBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    padding-right: 20px;\n"
"    border-radius: 3px;\n"
"    background-color: #f9f9f9; /* Matches readOnly QLineEdit background */\n"
"    border: 1px solid #d3d3d3; /* Matches readOnly QLineEdit border */\n"
"}\n"
"\n"
"/* Editable state */\n"
"QDoubleSpinBox:editable {\n"
"    background-color: #f0f6ff; /* Matches editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches editable QComboBox border */\n"
"}\n"
"\n"
"/* Editable hover state */\n"
"QDoubleSpinBox:editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Editable focus state */\n"
"QDoubleSpinBox:editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Non-editable state"
                        " */\n"
"QDoubleSpinBox:!editable {\n"
"    background-color: #f0f6ff; /* Matches non-editable QComboBox background */\n"
"    border: 1px solid #0078d7; /* Matches non-editable QComboBox border */\n"
"}\n"
"\n"
"/* Non-editable hover state */\n"
"QDoubleSpinBox:!editable:hover {\n"
"    border: 1px solid #1a8cff; /* Matches non-editable QComboBox:hover border */\n"
"}\n"
"\n"
"/* Non-editable focus state */\n"
"QDoubleSpinBox:!editable:focus {\n"
"    border: 1px solid #005bb5; /* Matches non-editable QComboBox:focus border */\n"
"    background-color: #ffffff; /* Matches non-editable QComboBox:focus background */\n"
"}\n"
"\n"
"/* Styling for up/down buttons */\n"
"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: padding;\n"
"    width: 20px;\n"
"    border-left: 1px solid #d3d3d3; /* Visual separation like QComboBox drop-down */\n"
"    background-color: #f9f9f9; /* Matches QComboBox drop-down background */\n"
"}\n"
"/* Hover state for up/down buttons */\n"
"QDoubleSpinBox:"
                        ":up-button:hover, QDoubleSpinBox::down-button:hover {\n"
"    background-color: #0078d7; /* Matches QComboBox drop-down:hover */\n"
"}\n"
"\n"
"/* Up arrow styling */\n"
"QDoubleSpinBox::up-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/up_arrow_icon.svg); /* Ensure this icon exists */\n"
"}\n"
"/* Down arrow styling */\n"
"QDoubleSpinBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/down_arrow_icon.svg); /* Matches QComboBox down-arrow */\n"
"}")
        self.timeStepSpin.setMinimum(1.000000000000000)
        self.timeStepSpin.setMaximum(99999999.000000000000000)
        self.timeStepSpin.setValue(600.000000000000000)

        self.horizontalLayout.addWidget(self.timeStepSpin)


        self.gridLayout_4.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.tabWidget.addTab(self.tab_2, "")
        self.tab_3 = QWidget()
        self.tab_3.setObjectName(u"tab_3")
        self.tabWidget.addTab(self.tab_3, "")

        self.gridLayout.addWidget(self.tabWidget, 3, 0, 1, 5)

        self.cancelButton = QPushButton(PreferencesDialog)
        self.cancelButton.setObjectName(u"cancelButton")
        self.cancelButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff; /* \u0421\u0432\u0435\u0442\u043b\u0435\u0435 \u043f\u0440\u0438 \u043d\u0430\u0432\u0435\u0434\u0435\u043d\u0438\u0438 */\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5; /* \u0422\u0435\u043c\u043d\u0435\u0435 \u043f\u0440\u0438 \u043d\u0430\u0436\u0430\u0442\u0438\u0438 */\n"
"    padding-top: 7px; /* \u041b\u0435\u0433\u043a\u043e\u0435 \u0441\u043c\u0435\u0449\u0435\u043d\u0438\u0435 \u0432\u043d\u0438\u0437 \u0434\u043b\u044f \u044d\u0444\u0444\u0435\u043a\u0442\u0430 \"\u043f\u0440\u043e\u0434\u0430\u0432\u043b\u0438\u0432\u0430\u043d\u0438\u044f\" */\n"
"    padding-bottom: 5px;\n"
"}")
        self.cancelButton.setAutoDefault(False)
        self.cancelButton.setFlat(True)

        self.gridLayout.addWidget(self.cancelButton, 5, 4, 1, 1)

        self.okButton = QPushButton(PreferencesDialog)
        self.okButton.setObjectName(u"okButton")
        self.okButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff; /* \u0421\u0432\u0435\u0442\u043b\u0435\u0435 \u043f\u0440\u0438 \u043d\u0430\u0432\u0435\u0434\u0435\u043d\u0438\u0438 */\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5; /* \u0422\u0435\u043c\u043d\u0435\u0435 \u043f\u0440\u0438 \u043d\u0430\u0436\u0430\u0442\u0438\u0438 */\n"
"    padding-top: 7px; /* \u041b\u0435\u0433\u043a\u043e\u0435 \u0441\u043c\u0435\u0449\u0435\u043d\u0438\u0435 \u0432\u043d\u0438\u0437 \u0434\u043b\u044f \u044d\u0444\u0444\u0435\u043a\u0442\u0430 \"\u043f\u0440\u043e\u0434\u0430\u0432\u043b\u0438\u0432\u0430\u043d\u0438\u044f\" */\n"
"    padding-bottom: 5px;\n"
"}")
        self.okButton.setAutoDefault(True)
        self.okButton.setFlat(True)

        self.gridLayout.addWidget(self.okButton, 5, 3, 1, 1)


        self.retranslateUi(PreferencesDialog)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(PreferencesDialog)
    # setupUi

    def retranslateUi(self, PreferencesDialog):
        PreferencesDialog.setWindowTitle(QCoreApplication.translate("PreferencesDialog", u"Dialog", None))
        self.lbl_telescopes_catalog_path.setText(QCoreApplication.translate("PreferencesDialog", u"Telescopes catalog path:", None))
        self.openSourcesCatalogButton.setText(QCoreApplication.translate("PreferencesDialog", u"Open...", None))
        self.lbl_sources_catalog_path.setText(QCoreApplication.translate("PreferencesDialog", u"Sources catalog path:", None))
        self.openTelescopesCatalogButton.setText(QCoreApplication.translate("PreferencesDialog", u"Open...", None))
        self.labelLogging.setText(QCoreApplication.translate("PreferencesDialog", u"Logging level:", None))
        self.chkClearLog.setText(QCoreApplication.translate("PreferencesDialog", u"Clear log-file on start", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("PreferencesDialog", u"Common", None))
        self.labelTimestep.setText(QCoreApplication.translate("PreferencesDialog", u"Time step (s):", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QCoreApplication.translate("PreferencesDialog", u"Calculations", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_3), QCoreApplication.translate("PreferencesDialog", u"Visualisations", None))
        self.cancelButton.setText(QCoreApplication.translate("PreferencesDialog", u"Cancel", None))
        self.okButton.setText(QCoreApplication.translate("PreferencesDialog", u"OK", None))
    # retranslateUi