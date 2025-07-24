# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_preferencesFxNsmK.ui'
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
    QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QTabWidget, QVBoxLayout, QWidget)

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
        self.verticalLayout_3 = QVBoxLayout(self.tab_3)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.groupBoxFigure = QGroupBox(self.tab_3)
        self.groupBoxFigure.setObjectName(u"groupBoxFigure")
        self.groupBoxFigure.setStyleSheet(u"QGroupBox { font-family: Arial; font-size: 9pt; font-weight: bold; }\n"
"QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 3px; }")
        self.gridLayoutFigure = QGridLayout(self.groupBoxFigure)
        self.gridLayoutFigure.setObjectName(u"gridLayoutFigure")
        self.labelPltStyle = QLabel(self.groupBoxFigure)
        self.labelPltStyle.setObjectName(u"labelPltStyle")
        self.labelPltStyle.setStyleSheet(u"font-family: Arial; font-size: 9pt;")

        self.gridLayoutFigure.addWidget(self.labelPltStyle, 0, 0, 1, 1)

        self.comboBoxPltStyle = QComboBox(self.groupBoxFigure)
        self.comboBoxPltStyle.addItem("")
        self.comboBoxPltStyle.addItem("")
        self.comboBoxPltStyle.addItem("")
        self.comboBoxPltStyle.addItem("")
        self.comboBoxPltStyle.setObjectName(u"comboBoxPltStyle")
        self.comboBoxPltStyle.setStyleSheet(u"QComboBox { font-family: Arial; font-size: 9pt; color: #333333; padding: 1px; border-radius: 3px; background-color: #f9f9f9; border: 1px solid #d3d3d3; }\n"
"QComboBox:editable { background-color: #f0f6ff; border: 1px solid #0078d7; }\n"
"QComboBox:editable:hover { border: 1px solid #1a8cff; }\n"
"QComboBox:editable:focus { border: 1px solid #005bb5; background-color: #ffffff; }\n"
"QComboBox::drop-down { width: 20px; border-left: 1px solid #d3d3d3; border-top-right-radius: 3px; border-bottom-right-radius: 3px; background-color: #f9f9f9; }\n"
"QComboBox::drop-down:hover { background-color: #0078d7; }\n"
"QComboBox::down-arrow { width: 12px; height: 12px; image: url(:/icons/down_arrow_icon.svg); }\n"
"QComboBox QAbstractItemView { font-family: Arial; font-size: 12pt; color: #333333; background-color: #ffffff; border: 1px solid #d3d3d3; selection-background-color: #0078d7; selection-color: #ffffff; padding: 1px; }\n"
"QComboBox QAbstractItemView::item { padding: 4px; min-height: 20px; }\n"
"QComboBox QAbstractIt"
                        "emView::item:hover { background-color: #0078d7; }")

        self.gridLayoutFigure.addWidget(self.comboBoxPltStyle, 0, 1, 1, 1)

        self.labelFigSize = QLabel(self.groupBoxFigure)
        self.labelFigSize.setObjectName(u"labelFigSize")
        self.labelFigSize.setStyleSheet(u"font-family: Arial; font-size: 9pt;")

        self.gridLayoutFigure.addWidget(self.labelFigSize, 1, 0, 1, 1)

        self.horizontalLayoutFigSize = QHBoxLayout()
        self.horizontalLayoutFigSize.setObjectName(u"horizontalLayoutFigSize")
        self.spinBoxFigWidth = QDoubleSpinBox(self.groupBoxFigure)
        self.spinBoxFigWidth.setObjectName(u"spinBoxFigWidth")
        self.spinBoxFigWidth.setStyleSheet(u"QDoubleSpinBox { font-family: Arial; font-size: 9pt; color: #333333; padding: 1px; padding-right: 20px; border-radius: 3px; background-color: #f9f9f9; border: 1px solid #d3d3d3; }\n"
"QDoubleSpinBox:editable { background-color: #f0f6ff; border: 1px solid #0078d7; }\n"
"QDoubleSpinBox:editable:hover { border: 1px solid #1a8cff; }\n"
"QDoubleSpinBox:editable:focus { border: 1px solid #005bb5; background-color: #ffffff; }\n"
"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 20px; border-left: 1px solid #d3d3d3; background-color: #f9f9f9; }\n"
"QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover { background-color: #0078d7; }\n"
"QDoubleSpinBox::up-arrow { width: 12px; height: 12px; image: url(:/icons/up_arrow_icon.svg); }\n"
"QDoubleSpinBox::down-arrow { width: 12px; height: 12px; image: url(:/icons/down_arrow_icon.svg); }")
        self.spinBoxFigWidth.setMinimum(1.000000000000000)
        self.spinBoxFigWidth.setMaximum(20.000000000000000)
        self.spinBoxFigWidth.setValue(10.000000000000000)

        self.horizontalLayoutFigSize.addWidget(self.spinBoxFigWidth)

        self.spinBoxFigHeight = QDoubleSpinBox(self.groupBoxFigure)
        self.spinBoxFigHeight.setObjectName(u"spinBoxFigHeight")
        self.spinBoxFigHeight.setStyleSheet(u"QDoubleSpinBox { font-family: Arial; font-size: 9pt; color: #333333; padding: 1px; padding-right: 20px; border-radius: 3px; background-color: #f9f9f9; border: 1px solid #d3d3d3; }\n"
"QDoubleSpinBox:editable { background-color: #f0f6ff; border: 1px solid #0078d7; }\n"
"QDoubleSpinBox:editable:hover { border: 1px solid #1a8cff; }\n"
"QDoubleSpinBox:editable:focus { border: 1px solid #005bb5; background-color: #ffffff; }\n"
"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 20px; border-left: 1px solid #d3d3d3; background-color: #f9f9f9; }\n"
"QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover { background-color: #0078d7; }\n"
"QDoubleSpinBox::up-arrow { width: 12px; height: 12px; image: url(:/icons/up_arrow_icon.svg); }\n"
"QDoubleSpinBox::down-arrow { width: 12px; height: 12px; image: url(:/icons/down_arrow_icon.svg); }")
        self.spinBoxFigHeight.setMinimum(1.000000000000000)
        self.spinBoxFigHeight.setMaximum(20.000000000000000)
        self.spinBoxFigHeight.setValue(6.000000000000000)

        self.horizontalLayoutFigSize.addWidget(self.spinBoxFigHeight)


        self.gridLayoutFigure.addLayout(self.horizontalLayoutFigSize, 1, 1, 1, 1)

        self.labelDpi = QLabel(self.groupBoxFigure)
        self.labelDpi.setObjectName(u"labelDpi")
        self.labelDpi.setStyleSheet(u"font-family: Arial; font-size: 9pt;")

        self.gridLayoutFigure.addWidget(self.labelDpi, 2, 0, 1, 1)

        self.spinBoxDpi = QDoubleSpinBox(self.groupBoxFigure)
        self.spinBoxDpi.setObjectName(u"spinBoxDpi")
        self.spinBoxDpi.setStyleSheet(u"QDoubleSpinBox { font-family: Arial; font-size: 9pt; color: #333333; padding: 1px; padding-right: 20px; border-radius: 3px; background-color: #f9f9f9; border: 1px solid #d3d3d3; }\n"
"QDoubleSpinBox:editable { background-color: #f0f6ff; border: 1px solid #0078d7; }\n"
"QDoubleSpinBox:editable:hover { border: 1px solid #1a8cff; }\n"
"QDoubleSpinBox:editable:focus { border: 1px solid #005bb5; background-color: #ffffff; }\n"
"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 20px; border-left: 1px solid #d3d3d3; background-color: #f9f9f9; }\n"
"QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover { background-color: #0078d7; }\n"
"QDoubleSpinBox::up-arrow { width: 12px; height: 12px; image: url(:/icons/up_arrow_icon.svg); }\n"
"QDoubleSpinBox::down-arrow { width: 12px; height: 12px; image: url(:/icons/down_arrow_icon.svg); }")
        self.spinBoxDpi.setMinimum(50.000000000000000)
        self.spinBoxDpi.setMaximum(300.000000000000000)
        self.spinBoxDpi.setValue(76.000000000000000)

        self.gridLayoutFigure.addWidget(self.spinBoxDpi, 2, 1, 1, 1)


        self.verticalLayout_3.addWidget(self.groupBoxFigure)

        self.groupBoxFont = QGroupBox(self.tab_3)
        self.groupBoxFont.setObjectName(u"groupBoxFont")
        self.groupBoxFont.setStyleSheet(u"QGroupBox { font-family: Arial; font-size: 9pt; font-weight: bold; }\n"
"QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 3px; }")
        self.gridLayoutFont = QGridLayout(self.groupBoxFont)
        self.gridLayoutFont.setObjectName(u"gridLayoutFont")
        self.labelFontFamily = QLabel(self.groupBoxFont)
        self.labelFontFamily.setObjectName(u"labelFontFamily")
        self.labelFontFamily.setStyleSheet(u"font-family: Arial; font-size: 9pt;")

        self.gridLayoutFont.addWidget(self.labelFontFamily, 0, 0, 1, 1)

        self.comboBoxFontFamily = QComboBox(self.groupBoxFont)
        self.comboBoxFontFamily.addItem("")
        self.comboBoxFontFamily.addItem("")
        self.comboBoxFontFamily.addItem("")
        self.comboBoxFontFamily.addItem("")
        self.comboBoxFontFamily.setObjectName(u"comboBoxFontFamily")
        self.comboBoxFontFamily.setStyleSheet(u"QComboBox { font-family: Arial; font-size: 9pt; color: #333333; padding: 1px; border-radius: 3px; background-color: #f9f9f9; border: 1px solid #d3d3d3; }\n"
"QComboBox:editable { background-color: #f0f6ff; border: 1px solid #0078d7; }\n"
"QComboBox:editable:hover { border: 1px solid #1a8cff; }\n"
"QComboBox:editable:focus { border: 1px solid #005bb5; background-color: #ffffff; }\n"
"QComboBox::drop-down { width: 20px; border-left: 1px solid #d3d3d3; border-top-right-radius: 3px; border-bottom-right-radius: 3px; background-color: #f9f9f9; }\n"
"QComboBox::drop-down:hover { background-color: #0078d7; }\n"
"QComboBox::down-arrow { width: 12px; height: 12px; image: url(:/icons/down_arrow_icon.svg); }\n"
"QComboBox QAbstractItemView { font-family: Arial; font-size: 12pt; color: #333333; background-color: #ffffff; border: 1px solid #d3d3d3; selection-background-color: #0078d7; selection-color: #ffffff; padding: 1px; }\n"
"QComboBox QAbstractItemView::item { padding: 4px; min-height: 20px; }\n"
"QComboBox QAbstractIt"
                        "emView::item:hover { background-color: #0078d7; }")

        self.gridLayoutFont.addWidget(self.comboBoxFontFamily, 0, 1, 1, 1)

        self.labelFontSize = QLabel(self.groupBoxFont)
        self.labelFontSize.setObjectName(u"labelFontSize")
        self.labelFontSize.setStyleSheet(u"font-family: Arial; font-size: 9pt;")

        self.gridLayoutFont.addWidget(self.labelFontSize, 1, 0, 1, 1)

        self.spinBoxFontSize = QDoubleSpinBox(self.groupBoxFont)
        self.spinBoxFontSize.setObjectName(u"spinBoxFontSize")
        self.spinBoxFontSize.setStyleSheet(u"QDoubleSpinBox { font-family: Arial; font-size: 9pt; color: #333333; padding: 1px; padding-right: 20px; border-radius: 3px; background-color: #f9f9f9; border: 1px solid #d3d3d3; }\n"
"QDoubleSpinBox:editable { background-color: #f0f6ff; border: 1px solid #0078d7; }\n"
"QDoubleSpinBox:editable:hover { border: 1px solid #1a8cff; }\n"
"QDoubleSpinBox:editable:focus { border: 1px solid #005bb5; background-color: #ffffff; }\n"
"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 20px; border-left: 1px solid #d3d3d3; background-color: #f9f9f9; }\n"
"QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover { background-color: #0078d7; }\n"
"QDoubleSpinBox::up-arrow { width: 12px; height: 12px; image: url(:/icons/up_arrow_icon.svg); }\n"
"QDoubleSpinBox::down-arrow { width: 12px; height: 12px; image: url(:/icons/down_arrow_icon.svg); }")
        self.spinBoxFontSize.setMinimum(6.000000000000000)
        self.spinBoxFontSize.setMaximum(20.000000000000000)
        self.spinBoxFontSize.setValue(12.000000000000000)

        self.gridLayoutFont.addWidget(self.spinBoxFontSize, 1, 1, 1, 1)


        self.verticalLayout_3.addWidget(self.groupBoxFont)

        self.groupBoxColors = QGroupBox(self.tab_3)
        self.groupBoxColors.setObjectName(u"groupBoxColors")
        self.groupBoxColors.setStyleSheet(u"QGroupBox { font-family: Arial; font-size: 9pt; font-weight: bold; }\n"
"QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 3px; }")
        self.gridLayoutColors = QGridLayout(self.groupBoxColors)
        self.gridLayoutColors.setObjectName(u"gridLayoutColors")
        self.labelIntersectionColor = QLabel(self.groupBoxColors)
        self.labelIntersectionColor.setObjectName(u"labelIntersectionColor")
        self.labelIntersectionColor.setStyleSheet(u"font-family: Arial; font-size: 9pt;")

        self.gridLayoutColors.addWidget(self.labelIntersectionColor, 0, 0, 1, 1)

        self.pushButtonIntersectionColor = QPushButton(self.groupBoxColors)
        self.pushButtonIntersectionColor.setObjectName(u"pushButtonIntersectionColor")
        self.pushButtonIntersectionColor.setStyleSheet(u"QPushButton { background-color: #0078d7; color: #ffffff; padding: 6px; border-radius: 3px; border: none; }\n"
"QPushButton:hover { background-color: #1a8cff; }\n"
"QPushButton:pressed { background-color: #005bb5; padding-top: 7px; padding-bottom: 5px; }")

        self.gridLayoutColors.addWidget(self.pushButtonIntersectionColor, 0, 1, 1, 1)

        self.labelColormap = QLabel(self.groupBoxColors)
        self.labelColormap.setObjectName(u"labelColormap")
        self.labelColormap.setStyleSheet(u"font-family: Arial; font-size: 9pt;")

        self.gridLayoutColors.addWidget(self.labelColormap, 1, 0, 1, 1)

        self.comboBoxColormap = QComboBox(self.groupBoxColors)
        self.comboBoxColormap.addItem("")
        self.comboBoxColormap.addItem("")
        self.comboBoxColormap.addItem("")
        self.comboBoxColormap.addItem("")
        self.comboBoxColormap.setObjectName(u"comboBoxColormap")
        self.comboBoxColormap.setStyleSheet(u"QComboBox { font-family: Arial; font-size: 9pt; color: #333333; padding: 1px; border-radius: 3px; background-color: #f9f9f9; border: 1px solid #d3d3d3; }\n"
"QComboBox:editable { background-color: #f0f6ff; border: 1px solid #0078d7; }\n"
"QComboBox:editable:hover { border: 1px solid #1a8cff; }\n"
"QComboBox:editable:focus { border: 1px solid #005bb5; background-color: #ffffff; }\n"
"QComboBox::drop-down { width: 20px; border-left: 1px solid #d3d3d3; border-top-right-radius: 3px; border-bottom-right-radius: 3px; background-color: #f9f9f9; }\n"
"QComboBox::drop-down:hover { background-color: #0078d7; }\n"
"QComboBox::down-arrow { width: 12px; height: 12px; image: url(:/icons/down_arrow_icon.svg); }\n"
"QComboBox QAbstractItemView { font-family: Arial; font-size: 12pt; color: #333333; background-color: #ffffff; border: 1px solid #d3d3d3; selection-background-color: #0078d7; selection-color: #ffffff; padding: 1px; }\n"
"QComboBox QAbstractItemView::item { padding: 4px; min-height: 20px; }\n"
"QComboBox QAbstractIt"
                        "emView::item:hover { background-color: #0078d7; }")

        self.gridLayoutColors.addWidget(self.comboBoxColormap, 1, 1, 1, 1)


        self.verticalLayout_3.addWidget(self.groupBoxColors)

        self.verticalSpacerVisualisations = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacerVisualisations)

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
        self.groupBoxFigure.setTitle(QCoreApplication.translate("PreferencesDialog", u"Figure Settings", None))
        self.labelPltStyle.setText(QCoreApplication.translate("PreferencesDialog", u"Matplotlib Style:", None))
        self.comboBoxPltStyle.setItemText(0, QCoreApplication.translate("PreferencesDialog", u"seaborn-v0_8-whitegrid", None))
        self.comboBoxPltStyle.setItemText(1, QCoreApplication.translate("PreferencesDialog", u"ggplot", None))
        self.comboBoxPltStyle.setItemText(2, QCoreApplication.translate("PreferencesDialog", u"classic", None))
        self.comboBoxPltStyle.setItemText(3, QCoreApplication.translate("PreferencesDialog", u"bmh", None))

        self.labelFigSize.setText(QCoreApplication.translate("PreferencesDialog", u"Figure Size (w, h):", None))
        self.labelDpi.setText(QCoreApplication.translate("PreferencesDialog", u"DPI:", None))
        self.groupBoxFont.setTitle(QCoreApplication.translate("PreferencesDialog", u"Font Settings", None))
        self.labelFontFamily.setText(QCoreApplication.translate("PreferencesDialog", u"Font Family:", None))
        self.comboBoxFontFamily.setItemText(0, QCoreApplication.translate("PreferencesDialog", u"Trebuchet MS", None))
        self.comboBoxFontFamily.setItemText(1, QCoreApplication.translate("PreferencesDialog", u"Arial", None))
        self.comboBoxFontFamily.setItemText(2, QCoreApplication.translate("PreferencesDialog", u"Helvetica", None))
        self.comboBoxFontFamily.setItemText(3, QCoreApplication.translate("PreferencesDialog", u"Times New Roman", None))

        self.labelFontSize.setText(QCoreApplication.translate("PreferencesDialog", u"Font Size:", None))
        self.groupBoxColors.setTitle(QCoreApplication.translate("PreferencesDialog", u"Color Settings", None))
        self.labelIntersectionColor.setText(QCoreApplication.translate("PreferencesDialog", u"Intersection Color:", None))
        self.pushButtonIntersectionColor.setText(QCoreApplication.translate("PreferencesDialog", u"Choose...", None))
        self.labelColormap.setText(QCoreApplication.translate("PreferencesDialog", u"Colormap:", None))
        self.comboBoxColormap.setItemText(0, QCoreApplication.translate("PreferencesDialog", u"redpurple", None))
        self.comboBoxColormap.setItemText(1, QCoreApplication.translate("PreferencesDialog", u"viridis", None))
        self.comboBoxColormap.setItemText(2, QCoreApplication.translate("PreferencesDialog", u"plasma", None))
        self.comboBoxColormap.setItemText(3, QCoreApplication.translate("PreferencesDialog", u"inferno", None))

        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_3), QCoreApplication.translate("PreferencesDialog", u"Visualisations", None))
        self.cancelButton.setText(QCoreApplication.translate("PreferencesDialog", u"Cancel", None))
        self.okButton.setText(QCoreApplication.translate("PreferencesDialog", u"OK", None))
    # retranslateUi