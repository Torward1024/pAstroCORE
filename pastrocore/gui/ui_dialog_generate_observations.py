# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_generate_observationssmIiGF.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QDateTimeEdit, QDialog, QDoubleSpinBox, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QSizePolicy, QSpacerItem,
    QSpinBox, QTabWidget, QVBoxLayout, QWidget)

class Ui_GenerateObservationsDialog(object):
    def setupUi(self, GenerateObservationsDialog):
        if not GenerateObservationsDialog.objectName():
            GenerateObservationsDialog.setObjectName(u"GenerateObservationsDialog")
        GenerateObservationsDialog.resize(541, 654)
        icon = QIcon()
        icon.addFile(u":/icons/preferences.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        GenerateObservationsDialog.setWindowIcon(icon)
        GenerateObservationsDialog.setStyleSheet(u"background-color: #ffffff; font-family: Arial;")
        GenerateObservationsDialog.setModal(True)
        self.verticalLayout = QVBoxLayout(GenerateObservationsDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tabWidget = QTabWidget(GenerateObservationsDialog)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabBasic = QWidget()
        self.tabBasic.setObjectName(u"tabBasic")
        self.gridLayout = QGridLayout(self.tabBasic)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayoutNaming = QHBoxLayout()
        self.horizontalLayoutNaming.setObjectName(u"horizontalLayoutNaming")
        self.labelNamingMask = QLabel(self.tabBasic)
        self.labelNamingMask.setObjectName(u"labelNamingMask")

        self.horizontalLayoutNaming.addWidget(self.labelNamingMask)

        self.namingMaskEdit = QLineEdit(self.tabBasic)
        self.namingMaskEdit.setObjectName(u"namingMaskEdit")
        self.namingMaskEdit.setStyleSheet(u"\n"
"             QLineEdit {\n"
"              background-color: #f0f6ff;\n"
"              border: 1px solid #0078d7;\n"
"              padding: 4px;\n"
"              border-radius: 3px;\n"
"             }\n"
"             QLineEdit:hover {\n"
"              border: 1px solid #1a8cff;\n"
"             }\n"
"             QLineEdit:focus {\n"
"              border: 1px solid #005bb5;\n"
"              background-color: #ffffff;\n"
"             }\n"
"            ")

        self.horizontalLayoutNaming.addWidget(self.namingMaskEdit)


        self.gridLayout.addLayout(self.horizontalLayoutNaming, 9, 0, 1, 1)

        self.frequencyList = QListWidget(self.tabBasic)
        self.frequencyList.setObjectName(u"frequencyList")
        self.frequencyList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.frequencyList.setStyleSheet(u"border: 1px solid #d3d3d3; background-color: #ffffff;")
        self.frequencyList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.gridLayout.addWidget(self.frequencyList, 8, 0, 1, 1)

        self.sourceList = QListWidget(self.tabBasic)
        self.sourceList.setObjectName(u"sourceList")
        self.sourceList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sourceList.setStyleSheet(u"border: 1px solid #d3d3d3; background-color: #ffffff;")
        self.sourceList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.gridLayout.addWidget(self.sourceList, 2, 0, 1, 1)

        self.labelFrequencies = QLabel(self.tabBasic)
        self.labelFrequencies.setObjectName(u"labelFrequencies")

        self.gridLayout.addWidget(self.labelFrequencies, 7, 0, 1, 1)

        self.telescopeList = QListWidget(self.tabBasic)
        self.telescopeList.setObjectName(u"telescopeList")
        self.telescopeList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.telescopeList.setStyleSheet(u"border: 1px solid #d3d3d3; background-color: #ffffff;")
        self.telescopeList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.gridLayout.addWidget(self.telescopeList, 5, 0, 1, 1)

        self.labelTelescopes = QLabel(self.tabBasic)
        self.labelTelescopes.setObjectName(u"labelTelescopes")

        self.gridLayout.addWidget(self.labelTelescopes, 4, 0, 1, 1)

        self.labelSources = QLabel(self.tabBasic)
        self.labelSources.setObjectName(u"labelSources")

        self.gridLayout.addWidget(self.labelSources, 1, 0, 1, 1)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.sourceSelectAllButton = QPushButton(self.tabBasic)
        self.sourceSelectAllButton.setObjectName(u"sourceSelectAllButton")
        self.sourceSelectAllButton.setMinimumSize(QSize(40, 20))
        self.sourceSelectAllButton.setStyleSheet(u"\n"
"             QPushButton {\n"
"              background-color: #0078d7;\n"
"              color: #ffffff;\n"
"              padding: 6px;\n"
"              border-radius: 3px;\n"
"              border: none;\n"
"             }\n"
"             QPushButton:hover {\n"
"              background-color: #1a8cff;\n"
"             }\n"
"             QPushButton:pressed {\n"
"              background-color: #005bb5;\n"
"              padding-top: 7px;\n"
"              padding-bottom: 5px;\n"
"             }\n"
"            ")

        self.gridLayout_2.addWidget(self.sourceSelectAllButton, 2, 0, 1, 1)

        self.sourceUpButton = QPushButton(self.tabBasic)
        self.sourceUpButton.setObjectName(u"sourceUpButton")
        self.sourceUpButton.setMinimumSize(QSize(40, 20))
        self.sourceUpButton.setStyleSheet(u"\n"
"             QPushButton {\n"
"              background-color: #0078d7;\n"
"              color: #ffffff;\n"
"              padding: 6px;\n"
"              border-radius: 3px;\n"
"              border: none;\n"
"             }\n"
"             QPushButton:hover {\n"
"              background-color: #1a8cff;\n"
"             }\n"
"             QPushButton:pressed {\n"
"              background-color: #005bb5;\n"
"              padding-top: 7px;\n"
"              padding-bottom: 5px;\n"
"             }\n"
"            ")

        self.gridLayout_2.addWidget(self.sourceUpButton, 0, 0, 1, 1)

        self.sourceClearButton = QPushButton(self.tabBasic)
        self.sourceClearButton.setObjectName(u"sourceClearButton")
        self.sourceClearButton.setMinimumSize(QSize(40, 20))
        self.sourceClearButton.setStyleSheet(u"\n"
"             QPushButton {\n"
"              background-color: #0078d7;\n"
"              color: #ffffff;\n"
"              padding: 6px;\n"
"              border-radius: 3px;\n"
"              border: none;\n"
"             }\n"
"             QPushButton:hover {\n"
"              background-color: #1a8cff;\n"
"             }\n"
"             QPushButton:pressed {\n"
"              background-color: #005bb5;\n"
"              padding-top: 7px;\n"
"              padding-bottom: 5px;\n"
"             }\n"
"            ")

        self.gridLayout_2.addWidget(self.sourceClearButton, 3, 0, 1, 1)

        self.sourceDownButton = QPushButton(self.tabBasic)
        self.sourceDownButton.setObjectName(u"sourceDownButton")
        self.sourceDownButton.setMinimumSize(QSize(40, 20))
        self.sourceDownButton.setStyleSheet(u"\n"
"             QPushButton {\n"
"              background-color: #0078d7;\n"
"              color: #ffffff;\n"
"              padding: 6px;\n"
"              border-radius: 3px;\n"
"              border: none;\n"
"             }\n"
"             QPushButton:hover {\n"
"              background-color: #1a8cff;\n"
"             }\n"
"             QPushButton:pressed {\n"
"              background-color: #005bb5;\n"
"              padding-top: 7px;\n"
"              padding-bottom: 5px;\n"
"             }\n"
"            ")

        self.gridLayout_2.addWidget(self.sourceDownButton, 1, 0, 1, 1)


        self.gridLayout.addLayout(self.gridLayout_2, 2, 1, 1, 1)

        self.gridLayout_3 = QGridLayout()
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.telescopeClearButton = QPushButton(self.tabBasic)
        self.telescopeClearButton.setObjectName(u"telescopeClearButton")
        self.telescopeClearButton.setMinimumSize(QSize(40, 20))
        self.telescopeClearButton.setStyleSheet(u"\n"
"             QPushButton {\n"
"              background-color: #0078d7;\n"
"              color: #ffffff;\n"
"              padding: 6px;\n"
"              border-radius: 3px;\n"
"              border: none;\n"
"             }\n"
"             QPushButton:hover {\n"
"              background-color: #1a8cff;\n"
"             }\n"
"             QPushButton:pressed {\n"
"              background-color: #005bb5;\n"
"              padding-top: 7px;\n"
"              padding-bottom: 5px;\n"
"             }\n"
"            ")

        self.gridLayout_3.addWidget(self.telescopeClearButton, 1, 1, 1, 1)

        self.telescopeSelectAllButton = QPushButton(self.tabBasic)
        self.telescopeSelectAllButton.setObjectName(u"telescopeSelectAllButton")
        self.telescopeSelectAllButton.setMinimumSize(QSize(40, 20))
        self.telescopeSelectAllButton.setStyleSheet(u"\n"
"             QPushButton {\n"
"              background-color: #0078d7;\n"
"              color: #ffffff;\n"
"              padding: 6px;\n"
"              border-radius: 3px;\n"
"              border: none;\n"
"             }\n"
"             QPushButton:hover {\n"
"              background-color: #1a8cff;\n"
"             }\n"
"             QPushButton:pressed {\n"
"              background-color: #005bb5;\n"
"              padding-top: 7px;\n"
"              padding-bottom: 5px;\n"
"             }\n"
"            ")

        self.gridLayout_3.addWidget(self.telescopeSelectAllButton, 0, 1, 1, 1)


        self.gridLayout.addLayout(self.gridLayout_3, 5, 1, 1, 1)

        self.gridLayout_4 = QGridLayout()
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.frequencyClearButton = QPushButton(self.tabBasic)
        self.frequencyClearButton.setObjectName(u"frequencyClearButton")
        self.frequencyClearButton.setMinimumSize(QSize(40, 20))
        self.frequencyClearButton.setStyleSheet(u"\n"
"             QPushButton {\n"
"              background-color: #0078d7;\n"
"              color: #ffffff;\n"
"              padding: 6px;\n"
"              border-radius: 3px;\n"
"              border: none;\n"
"             }\n"
"             QPushButton:hover {\n"
"              background-color: #1a8cff;\n"
"             }\n"
"             QPushButton:pressed {\n"
"              background-color: #005bb5;\n"
"              padding-top: 7px;\n"
"              padding-bottom: 5px;\n"
"             }\n"
"            ")

        self.gridLayout_4.addWidget(self.frequencyClearButton, 1, 1, 1, 1)

        self.frequencySelectAllButton = QPushButton(self.tabBasic)
        self.frequencySelectAllButton.setObjectName(u"frequencySelectAllButton")
        self.frequencySelectAllButton.setMinimumSize(QSize(40, 20))
        self.frequencySelectAllButton.setStyleSheet(u"\n"
"             QPushButton {\n"
"              background-color: #0078d7;\n"
"              color: #ffffff;\n"
"              padding: 6px;\n"
"              border-radius: 3px;\n"
"              border: none;\n"
"             }\n"
"             QPushButton:hover {\n"
"              background-color: #1a8cff;\n"
"             }\n"
"             QPushButton:pressed {\n"
"              background-color: #005bb5;\n"
"              padding-top: 7px;\n"
"              padding-bottom: 5px;\n"
"             }\n"
"            ")

        self.gridLayout_4.addWidget(self.frequencySelectAllButton, 0, 1, 1, 1)


        self.gridLayout.addLayout(self.gridLayout_4, 8, 1, 1, 1)

        self.tabWidget.addTab(self.tabBasic, "")
        self.tabPattern = QWidget()
        self.tabPattern.setObjectName(u"tabPattern")
        self.gridLayout_5 = QGridLayout(self.tabPattern)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.addOffSourceCheck = QCheckBox(self.tabPattern)
        self.addOffSourceCheck.setObjectName(u"addOffSourceCheck")
        self.addOffSourceCheck.setStyleSheet(u"/* \u041e\u0441\u043d\u043e\u0432\u043d\u043e\u0439 \u0441\u0442\u0438\u043b\u044c QCheckBox */\n"
"QCheckBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    spacing: 6px;\n"
"    padding: 2px;\n"
"    outline: none;\n"
"}\n"
"\n"
"QCheckBox::item {\n"
"    padding: 2px;\n"
"}\n"
"\n"
"/* \u0418\u043d\u0434\u0438\u043a\u0430\u0442\u043e\u0440 \u0447\u0435\u043a\u0431\u043e\u043a\u0441\u0430 */\n"
"QCheckBox::indicator {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    border-radius: 3px;\n"
"    border: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"}\n"
"\n"
"/* Unchecked \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435 */\n"
"QCheckBox::indicator:unchecked {\n"
"    border: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"    image: none;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked:hover {\n"
"    border: 1px solid #1a8cff;\n"
"    background-color: #f0f6ff;\n"
"    image: none;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked:focus {\n"
"    b"
                        "order: 1px solid #005bb5;\n"
"    background-color: #f0f6ff;\n"
"    image: none;\n"
"}\n"
"\n"
"/* Checked \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435 - \u0411\u0415\u041b\u042b\u0419 \u0424\u041e\u041d, \u0441\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0430\u044f \u0433\u0440\u0430\u043d\u0438\u0446\u0430 */\n"
"QCheckBox::indicator:checked {\n"
"    border: 1px solid #0078d7;\n"
"    background-color: #ffffff; /* \u0411\u0435\u043b\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon.svg);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked:hover {\n"
"    border: 1px solid #1a8cff; /* \u0421\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0430\u044f \u0442\u043e\u043b\u0449\u0438\u043d\u0430 */\n"
"    background-color: #ffffff; /* \u0411\u0435\u043b\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon_hover.svg);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked:focus {\n"
"    border: 1px solid #005bb5; /* \u0421\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0430"
                        "\u044f \u0442\u043e\u043b\u0449\u0438\u043d\u0430 */\n"
"    background-color: #ffffff; /* \u0411\u0435\u043b\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon.svg);\n"
"}\n"
"\n"
"/* Disabled \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044f */\n"
"QCheckBox::indicator:unchecked:disabled {\n"
"    border: 1px solid #e0e0e0;\n"
"    background-color: #f5f5f5;\n"
"    image: none;\n"
"}\n"
"\n"
"QCheckBox::indicator:checked:disabled {\n"
"    border: 1px solid #cccccc;\n"
"    background-color: #f0f0f0; /* \u0421\u0432\u0435\u0442\u043b\u043e-\u0441\u0435\u0440\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon_disabled.svg);\n"
"}\n"
"\n"
"QCheckBox:disabled {\n"
"    color: #999999;\n"
"}")
        self.addOffSourceCheck.setChecked(False)

        self.gridLayout_5.addWidget(self.addOffSourceCheck, 0, 0, 1, 1)

        self.randomizeOrderCheck = QCheckBox(self.tabPattern)
        self.randomizeOrderCheck.setObjectName(u"randomizeOrderCheck")
        self.randomizeOrderCheck.setStyleSheet(u"/* \u041e\u0441\u043d\u043e\u0432\u043d\u043e\u0439 \u0441\u0442\u0438\u043b\u044c QCheckBox */\n"
"QCheckBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    spacing: 6px;\n"
"    padding: 2px;\n"
"    outline: none;\n"
"}\n"
"\n"
"QCheckBox::item {\n"
"    padding: 2px;\n"
"}\n"
"\n"
"/* \u0418\u043d\u0434\u0438\u043a\u0430\u0442\u043e\u0440 \u0447\u0435\u043a\u0431\u043e\u043a\u0441\u0430 */\n"
"QCheckBox::indicator {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    border-radius: 3px;\n"
"    border: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"}\n"
"\n"
"/* Unchecked \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435 */\n"
"QCheckBox::indicator:unchecked {\n"
"    border: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"    image: none;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked:hover {\n"
"    border: 1px solid #1a8cff;\n"
"    background-color: #f0f6ff;\n"
"    image: none;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked:focus {\n"
"    b"
                        "order: 1px solid #005bb5;\n"
"    background-color: #f0f6ff;\n"
"    image: none;\n"
"}\n"
"\n"
"/* Checked \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435 - \u0411\u0415\u041b\u042b\u0419 \u0424\u041e\u041d, \u0441\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0430\u044f \u0433\u0440\u0430\u043d\u0438\u0446\u0430 */\n"
"QCheckBox::indicator:checked {\n"
"    border: 1px solid #0078d7;\n"
"    background-color: #ffffff; /* \u0411\u0435\u043b\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon.svg);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked:hover {\n"
"    border: 1px solid #1a8cff; /* \u0421\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0430\u044f \u0442\u043e\u043b\u0449\u0438\u043d\u0430 */\n"
"    background-color: #ffffff; /* \u0411\u0435\u043b\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon_hover.svg);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked:focus {\n"
"    border: 1px solid #005bb5; /* \u0421\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0430"
                        "\u044f \u0442\u043e\u043b\u0449\u0438\u043d\u0430 */\n"
"    background-color: #ffffff; /* \u0411\u0435\u043b\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon.svg);\n"
"}\n"
"\n"
"/* Disabled \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044f */\n"
"QCheckBox::indicator:unchecked:disabled {\n"
"    border: 1px solid #e0e0e0;\n"
"    background-color: #f5f5f5;\n"
"    image: none;\n"
"}\n"
"\n"
"QCheckBox::indicator:checked:disabled {\n"
"    border: 1px solid #cccccc;\n"
"    background-color: #f0f0f0; /* \u0421\u0432\u0435\u0442\u043b\u043e-\u0441\u0435\u0440\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon_disabled.svg);\n"
"}\n"
"\n"
"QCheckBox:disabled {\n"
"    color: #999999;\n"
"}")
        self.randomizeOrderCheck.setChecked(False)

        self.gridLayout_5.addWidget(self.randomizeOrderCheck, 1, 0, 1, 1)

        self.horizontalLayoutInterval = QHBoxLayout()
        self.horizontalLayoutInterval.setObjectName(u"horizontalLayoutInterval")
        self.labelInterval = QLabel(self.tabPattern)
        self.labelInterval.setObjectName(u"labelInterval")

        self.horizontalLayoutInterval.addWidget(self.labelInterval)

        self.intervalSpinBox = QDoubleSpinBox(self.tabPattern)
        self.intervalSpinBox.setObjectName(u"intervalSpinBox")
        self.intervalSpinBox.setStyleSheet(u"         QDoubleSpinBox {\n"
"          font-family: Arial;\n"
"          font-size: 9pt;\n"
"          color: #333333;\n"
"          padding: 1px;\n"
"          padding-right: 20px;\n"
"          border-radius: 3px;\n"
"          background-color: #f0f6ff;\n"
"          border: 1px solid #0078d7;\n"
"         }\n"
"         QDoubleSpinBox:hover {\n"
"          border: 1px solid #1a8cff;\n"
"         }\n"
"         QDoubleSpinBox:focus {\n"
"          border: 1px solid #005bb5;\n"
"          background-color: #ffffff;\n"
"         }\n"
"         QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {\n"
"          width: 20px;\n"
"          border-left: 1px solid #d3d3d3;\n"
"          background-color: #f9f9f9;\n"
"         }\n"
"         QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {\n"
"          background-color: #0078d7;\n"
"         }\n"
"         QDoubleSpinBox::up-arrow {\n"
"          width: 12px;\n"
"          height: 12px;\n"
"          image: url(:/icons/up_arrow_icon.svg);\n"
""
                        "         }\n"
"         QDoubleSpinBox::down-arrow {\n"
"          width: 12px;\n"
"          height: 12px;\n"
"          image: url(:/icons/down_arrow_icon.svg);\n"
"         }\n"
"        ")
        self.intervalSpinBox.setMaximum(100000000000.000000000000000)
        self.intervalSpinBox.setValue(5.000000000000000)

        self.horizontalLayoutInterval.addWidget(self.intervalSpinBox)


        self.gridLayout_5.addLayout(self.horizontalLayoutInterval, 2, 0, 1, 1)

        self.labelPreset = QLabel(self.tabPattern)
        self.labelPreset.setObjectName(u"labelPreset")

        self.gridLayout_5.addWidget(self.labelPreset, 3, 0, 1, 1)

        self.presetCombo = QComboBox(self.tabPattern)
        self.presetCombo.addItem("")
        self.presetCombo.addItem("")
        self.presetCombo.setObjectName(u"presetCombo")
        self.presetCombo.setStyleSheet(u"\n"
"           QComboBox {\n"
"            font-family: Arial;\n"
"            font-size: 9pt;\n"
"            color: #333333;\n"
"            padding: 1px;\n"
"            border-radius: 3px;\n"
"            background-color: #f9f9f9;\n"
"            border: 1px solid #d3d3d3;\n"
"           }\n"
"           QComboBox:editable {\n"
"            background-color: #f0f6ff;\n"
"            border: 1px solid #0078d7;\n"
"           }\n"
"           QComboBox:editable:hover {\n"
"            border: 1px solid #1a8cff;\n"
"           }\n"
"           QComboBox:editable:focus {\n"
"            border: 1px solid #005bb5;\n"
"            background-color: #ffffff;\n"
"           }\n"
"           QComboBox:!editable {\n"
"            background-color: #f0f6ff;\n"
"            border: 1px solid #0078d7;\n"
"           }\n"
"           QComboBox:!editable:hover {\n"
"            border: 1px solid #1a8cff;\n"
"           }\n"
"           QComboBox:!editable:focus {\n"
"            border: 1px solid #005bb5;\n"
"         "
                        "   background-color: #ffffff;\n"
"           }\n"
"           QComboBox::drop-down {\n"
"            subcontrol-origin: padding;\n"
"            subcontrol-position: right;\n"
"            width: 20px;\n"
"            border-left: 1px solid #d3d3d3;\n"
"            border-top-right-radius: 3px;\n"
"            border-bottom-right-radius: 3px;\n"
"            background-color: #f9f9f9;\n"
"           }\n"
"           QComboBox::drop-down:hover {\n"
"            background-color: #0078d7;\n"
"           }\n"
"           QComboBox::down-arrow {\n"
"            width: 12px;\n"
"            height: 12px;\n"
"            image: url(:/icons/down_arrow_icon.svg);\n"
"           }\n"
"           QComboBox QAbstractItemView {\n"
"            font-family: Arial;\n"
"            font-size: 12pt;\n"
"            color: #333333;\n"
"            background-color: #ffffff;\n"
"            border: 1px solid #d3d3d3;\n"
"            selection-background-color: #0078d7;\n"
"            selection-color: #ffffff;\n"
"            p"
                        "adding: 1px;\n"
"           }\n"
"           QComboBox QAbstractItemView::item {\n"
"            padding: 4px;\n"
"            min-height: 20px;\n"
"           }\n"
"           QComboBox QAbstractItemView::item:hover {\n"
"            background-color: #0078d7;\n"
"           }\n"
"          ")

        self.gridLayout_5.addWidget(self.presetCombo, 4, 0, 1, 1)

        self.horizontalLayoutPresetButtons = QHBoxLayout()
        self.horizontalLayoutPresetButtons.setObjectName(u"horizontalLayoutPresetButtons")
        self.savePresetButton = QPushButton(self.tabPattern)
        self.savePresetButton.setObjectName(u"savePresetButton")
        self.savePresetButton.setStyleSheet(u"\n"
"             QPushButton {\n"
"              background-color: #0078d7;\n"
"              color: #ffffff;\n"
"              padding: 6px;\n"
"              border-radius: 3px;\n"
"              border: none;\n"
"             }\n"
"             QPushButton:hover {\n"
"              background-color: #1a8cff;\n"
"             }\n"
"             QPushButton:pressed {\n"
"              background-color: #005bb5;\n"
"              padding-top: 7px;\n"
"              padding-bottom: 5px;\n"
"             }\n"
"            ")

        self.horizontalLayoutPresetButtons.addWidget(self.savePresetButton)

        self.loadPresetButton = QPushButton(self.tabPattern)
        self.loadPresetButton.setObjectName(u"loadPresetButton")
        self.loadPresetButton.setStyleSheet(u"\n"
"             QPushButton {\n"
"              background-color: #0078d7;\n"
"              color: #ffffff;\n"
"              padding: 6px;\n"
"              border-radius: 3px;\n"
"              border: none;\n"
"             }\n"
"             QPushButton:hover {\n"
"              background-color: #1a8cff;\n"
"             }\n"
"             QPushButton:pressed {\n"
"              background-color: #005bb5;\n"
"              padding-top: 7px;\n"
"              padding-bottom: 5px;\n"
"             }\n"
"            ")

        self.horizontalLayoutPresetButtons.addWidget(self.loadPresetButton)


        self.gridLayout_5.addLayout(self.horizontalLayoutPresetButtons, 5, 0, 1, 1)

        self.tabWidget.addTab(self.tabPattern, "")

        self.verticalLayout.addWidget(self.tabWidget)

        self.labelObservationType = QLabel(GenerateObservationsDialog)
        self.labelObservationType.setObjectName(u"labelObservationType")

        self.verticalLayout.addWidget(self.labelObservationType)

        self.observationTypeCombo = QComboBox(GenerateObservationsDialog)
        self.observationTypeCombo.addItem("")
        self.observationTypeCombo.addItem("")
        self.observationTypeCombo.setObjectName(u"observationTypeCombo")
        self.observationTypeCombo.setStyleSheet(u"\n"
"       QComboBox {\n"
"        font-family: Arial;\n"
"        font-size: 9pt;\n"
"        color: #333333;\n"
"        padding: 1px;\n"
"        border-radius: 3px;\n"
"        background-color: #f9f9f9;\n"
"        border: 1px solid #d3d3d3;\n"
"       }\n"
"       QComboBox:editable {\n"
"        background-color: #f0f6ff;\n"
"        border: 1px solid #0078d7;\n"
"       }\n"
"       QComboBox:editable:hover {\n"
"        border: 1px solid #1a8cff;\n"
"       }\n"
"       QComboBox:editable:focus {\n"
"        border: 1px solid #005bb5;\n"
"        background-color: #ffffff;\n"
"       }\n"
"       QComboBox:!editable {\n"
"        background-color: #f0f6ff;\n"
"        border: 1px solid #0078d7;\n"
"       }\n"
"       QComboBox:!editable:hover {\n"
"        border: 1px solid #1a8cff;\n"
"       }\n"
"       QComboBox:!editable:focus {\n"
"        border: 1px solid #005bb5;\n"
"        background-color: #ffffff;\n"
"       }\n"
"       QComboBox::drop-down {\n"
"        subcontrol-origin: padding;\n"
""
                        "        subcontrol-position: right;\n"
"        width: 20px;\n"
"        border-left: 1px solid #d3d3d3;\n"
"        border-top-right-radius: 3px;\n"
"        border-bottom-right-radius: 3px;\n"
"        background-color: #f9f9f9;\n"
"       }\n"
"       QComboBox::drop-down:hover {\n"
"        background-color: #0078d7;\n"
"       }\n"
"       QComboBox::down-arrow {\n"
"        width: 12px;\n"
"        height: 12px;\n"
"        image: url(:/icons/down_arrow_icon.svg);\n"
"       }\n"
"       QComboBox QAbstractItemView {\n"
"        font-family: Arial;\n"
"        font-size: 12pt;\n"
"        color: #333333;\n"
"        background-color: #ffffff;\n"
"        border: 1px solid #d3d3d3;\n"
"        selection-background-color: #0078d7;\n"
"        selection-color: #ffffff;\n"
"        padding: 1px;\n"
"       }\n"
"       QComboBox QAbstractItemView::item {\n"
"        padding: 4px;\n"
"        min-height: 20px;\n"
"       }\n"
"       QComboBox QAbstractItemView::item:hover {\n"
"        background-color: #007"
                        "8d7;\n"
"       }\n"
"      ")

        self.verticalLayout.addWidget(self.observationTypeCombo)

        self.labelTimeRange = QLabel(GenerateObservationsDialog)
        self.labelTimeRange.setObjectName(u"labelTimeRange")

        self.verticalLayout.addWidget(self.labelTimeRange)

        self.horizontalLayoutTimeRange = QHBoxLayout()
        self.horizontalLayoutTimeRange.setObjectName(u"horizontalLayoutTimeRange")
        self.verticalLayoutStartTime = QVBoxLayout()
        self.verticalLayoutStartTime.setObjectName(u"verticalLayoutStartTime")
        self.labelStartTime = QLabel(GenerateObservationsDialog)
        self.labelStartTime.setObjectName(u"labelStartTime")

        self.verticalLayoutStartTime.addWidget(self.labelStartTime)

        self.startTimeEdit = QDateTimeEdit(GenerateObservationsDialog)
        self.startTimeEdit.setObjectName(u"startTimeEdit")
        self.startTimeEdit.setStyleSheet(u"           QDateTimeEdit {\n"
"            background-color: #f0f6ff;\n"
"            border: 1px solid #0078d7;\n"
"            padding: 4px;\n"
"            border-radius: 3px;\n"
"           }\n"
"           QDateTimeEdit:hover {\n"
"            border: 1px solid #1a8cff;\n"
"           }\n"
"           QDateTimeEdit:focus {\n"
"            border: 1px solid #005bb5;\n"
"            background-color: #ffffff;\n"
"           }\n"
"           QDateTimeEdit::drop-down {\n"
"            width: 20px;\n"
"            border-left: 1px solid #d3d3d3;\n"
"            background-color: #f9f9f9;\n"
"           }\n"
"           QDateTimeEdit::drop-down:hover {\n"
"            background-color: #0078d7;\n"
"           }\n"
"           QDateTimeEdit::down-arrow {\n"
"            image: url(:/icons/down_arrow_icon.svg);\n"
"            width: 12px;\n"
"            height: 12px;\n"
"           }\n"
"          ")
        self.startTimeEdit.setCalendarPopup(True)

        self.verticalLayoutStartTime.addWidget(self.startTimeEdit)


        self.horizontalLayoutTimeRange.addLayout(self.verticalLayoutStartTime)

        self.verticalLayoutEndTime = QVBoxLayout()
        self.verticalLayoutEndTime.setObjectName(u"verticalLayoutEndTime")
        self.labelEndTime = QLabel(GenerateObservationsDialog)
        self.labelEndTime.setObjectName(u"labelEndTime")

        self.verticalLayoutEndTime.addWidget(self.labelEndTime)

        self.endTimeEdit = QDateTimeEdit(GenerateObservationsDialog)
        self.endTimeEdit.setObjectName(u"endTimeEdit")
        self.endTimeEdit.setStyleSheet(u"           QDateTimeEdit {\n"
"            background-color: #f0f6ff;\n"
"            border: 1px solid #0078d7;\n"
"            padding: 4px;\n"
"            border-radius: 3px;\n"
"           }\n"
"           QDateTimeEdit:hover {\n"
"            border: 1px solid #1a8cff;\n"
"           }\n"
"           QDateTimeEdit:focus {\n"
"            border: 1px solid #005bb5;\n"
"            background-color: #ffffff;\n"
"           }\n"
"           QDateTimeEdit::drop-down {\n"
"            width: 20px;\n"
"            border-left: 1px solid #d3d3d3;\n"
"            background-color: #f9f9f9;\n"
"           }\n"
"           QDateTimeEdit::drop-down:hover {\n"
"            background-color: #0078d7;\n"
"           }\n"
"           QDateTimeEdit::down-arrow {\n"
"            image: url(:/icons/down_arrow_icon.svg);\n"
"            width: 12px;\n"
"            height: 12px;\n"
"           }\n"
"          ")
        self.endTimeEdit.setCalendarPopup(True)

        self.verticalLayoutEndTime.addWidget(self.endTimeEdit)


        self.horizontalLayoutTimeRange.addLayout(self.verticalLayoutEndTime)


        self.verticalLayout.addLayout(self.horizontalLayoutTimeRange)

        self.horizontalLayoutScanDuration = QHBoxLayout()
        self.horizontalLayoutScanDuration.setObjectName(u"horizontalLayoutScanDuration")
        self.labelScanDuration = QLabel(GenerateObservationsDialog)
        self.labelScanDuration.setObjectName(u"labelScanDuration")

        self.horizontalLayoutScanDuration.addWidget(self.labelScanDuration)

        self.scanDurationSpinBox = QDoubleSpinBox(GenerateObservationsDialog)
        self.scanDurationSpinBox.setObjectName(u"scanDurationSpinBox")
        self.scanDurationSpinBox.setStyleSheet(u"         QDoubleSpinBox {\n"
"          font-family: Arial;\n"
"          font-size: 9pt;\n"
"          color: #333333;\n"
"          padding: 1px;\n"
"          padding-right: 20px;\n"
"          border-radius: 3px;\n"
"          background-color: #f0f6ff;\n"
"          border: 1px solid #0078d7;\n"
"         }\n"
"         QDoubleSpinBox:hover {\n"
"          border: 1px solid #1a8cff;\n"
"         }\n"
"         QDoubleSpinBox:focus {\n"
"          border: 1px solid #005bb5;\n"
"          background-color: #ffffff;\n"
"         }\n"
"         QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {\n"
"          width: 20px;\n"
"          border-left: 1px solid #d3d3d3;\n"
"          background-color: #f9f9f9;\n"
"         }\n"
"         QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {\n"
"          background-color: #0078d7;\n"
"         }\n"
"         QDoubleSpinBox::up-arrow {\n"
"          width: 12px;\n"
"          height: 12px;\n"
"          image: url(:/icons/up_arrow_icon.svg);\n"
""
                        "         }\n"
"         QDoubleSpinBox::down-arrow {\n"
"          width: 12px;\n"
"          height: 12px;\n"
"          image: url(:/icons/down_arrow_icon.svg);\n"
"         }\n"
"        ")
        self.scanDurationSpinBox.setMinimum(1.000000000000000)
        self.scanDurationSpinBox.setMaximum(9999999999999.000000000000000)
        self.scanDurationSpinBox.setValue(300.000000000000000)

        self.horizontalLayoutScanDuration.addWidget(self.scanDurationSpinBox)


        self.verticalLayout.addLayout(self.horizontalLayoutScanDuration)

        self.horizontalLayoutNumScans = QHBoxLayout()
        self.horizontalLayoutNumScans.setObjectName(u"horizontalLayoutNumScans")
        self.labelNumScans = QLabel(GenerateObservationsDialog)
        self.labelNumScans.setObjectName(u"labelNumScans")

        self.horizontalLayoutNumScans.addWidget(self.labelNumScans)

        self.numScansSpinBox = QSpinBox(GenerateObservationsDialog)
        self.numScansSpinBox.setObjectName(u"numScansSpinBox")
        self.numScansSpinBox.setStyleSheet(u"         QSpinBox {\n"
"          font-family: Arial;\n"
"          font-size: 9pt;\n"
"          color: #333333;\n"
"          padding: 1px;\n"
"          padding-right: 20px;\n"
"          border-radius: 3px;\n"
"          background-color: #f0f6ff;\n"
"          border: 1px solid #0078d7;\n"
"         }\n"
"         QSpinBox:hover {\n"
"          border: 1px solid #1a8cff;\n"
"         }\n"
"         QSpinBox:focus {\n"
"          border: 1px solid #005bb5;\n"
"          background-color: #ffffff;\n"
"         }\n"
"         QSpinBox::up-button, QSpinBox::down-button {\n"
"          width: 20px;\n"
"          border-left: 1px solid #d3d3d3;\n"
"          background-color: #f9f9f9;\n"
"         }\n"
"         QSpinBox::up-button:hover, QSpinBox::down-button:hover {\n"
"          background-color: #0078d7;\n"
"         }\n"
"         QSpinBox::up-arrow {\n"
"          width: 12px;\n"
"          height: 12px;\n"
"          image: url(:/icons/up_arrow_icon.svg);\n"
"         }\n"
"         QSpinBox::down-arrow "
                        "{\n"
"          width: 12px;\n"
"          height: 12px;\n"
"          image: url(:/icons/down_arrow_icon.svg);\n"
"         }\n"
"        ")
        self.numScansSpinBox.setMinimum(1)
        self.numScansSpinBox.setMaximum(100)
        self.numScansSpinBox.setValue(5)

        self.horizontalLayoutNumScans.addWidget(self.numScansSpinBox)


        self.verticalLayout.addLayout(self.horizontalLayoutNumScans)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.chkParallel = QCheckBox(GenerateObservationsDialog)
        self.chkParallel.setObjectName(u"chkParallel")
        self.chkParallel.setStyleSheet(u"/* \u041e\u0441\u043d\u043e\u0432\u043d\u043e\u0439 \u0441\u0442\u0438\u043b\u044c QCheckBox */\n"
"QCheckBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    spacing: 6px;\n"
"    padding: 2px;\n"
"    outline: none;\n"
"}\n"
"\n"
"QCheckBox::item {\n"
"    padding: 2px;\n"
"}\n"
"\n"
"/* \u0418\u043d\u0434\u0438\u043a\u0430\u0442\u043e\u0440 \u0447\u0435\u043a\u0431\u043e\u043a\u0441\u0430 */\n"
"QCheckBox::indicator {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    border-radius: 3px;\n"
"    border: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"}\n"
"\n"
"/* Unchecked \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435 */\n"
"QCheckBox::indicator:unchecked {\n"
"    border: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"    image: none;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked:hover {\n"
"    border: 1px solid #1a8cff;\n"
"    background-color: #f0f6ff;\n"
"    image: none;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked:focus {\n"
"    b"
                        "order: 1px solid #005bb5;\n"
"    background-color: #f0f6ff;\n"
"    image: none;\n"
"}\n"
"\n"
"/* Checked \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435 - \u0411\u0415\u041b\u042b\u0419 \u0424\u041e\u041d, \u0441\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0430\u044f \u0433\u0440\u0430\u043d\u0438\u0446\u0430 */\n"
"QCheckBox::indicator:checked {\n"
"    border: 1px solid #0078d7;\n"
"    background-color: #ffffff; /* \u0411\u0435\u043b\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon.svg);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked:hover {\n"
"    border: 1px solid #1a8cff; /* \u0421\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0430\u044f \u0442\u043e\u043b\u0449\u0438\u043d\u0430 */\n"
"    background-color: #ffffff; /* \u0411\u0435\u043b\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon_hover.svg);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked:focus {\n"
"    border: 1px solid #005bb5; /* \u0421\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0430"
                        "\u044f \u0442\u043e\u043b\u0449\u0438\u043d\u0430 */\n"
"    background-color: #ffffff; /* \u0411\u0435\u043b\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon.svg);\n"
"}\n"
"\n"
"/* Disabled \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044f */\n"
"QCheckBox::indicator:unchecked:disabled {\n"
"    border: 1px solid #e0e0e0;\n"
"    background-color: #f5f5f5;\n"
"    image: none;\n"
"}\n"
"\n"
"QCheckBox::indicator:checked:disabled {\n"
"    border: 1px solid #cccccc;\n"
"    background-color: #f0f0f0; /* \u0421\u0432\u0435\u0442\u043b\u043e-\u0441\u0435\u0440\u044b\u0439 \u0444\u043e\u043d */\n"
"    image: url(:/icons/check_icon_disabled.svg);\n"
"}\n"
"\n"
"QCheckBox:disabled {\n"
"    color: #999999;\n"
"}")

        self.verticalLayout.addWidget(self.chkParallel)

        self.horizontalLayoutButtons = QHBoxLayout()
        self.horizontalLayoutButtons.setObjectName(u"horizontalLayoutButtons")
        self.generateButton = QPushButton(GenerateObservationsDialog)
        self.generateButton.setObjectName(u"generateButton")
        self.generateButton.setStyleSheet(u"\n"
"         QPushButton {\n"
"          background-color: #0078d7;\n"
"          color: #ffffff;\n"
"          padding: 6px;\n"
"          border-radius: 3px;\n"
"          border: none;\n"
"         }\n"
"         QPushButton:hover {\n"
"          background-color: #1a8cff;\n"
"         }\n"
"         QPushButton:pressed {\n"
"          background-color: #005bb5;\n"
"          padding-top: 7px;\n"
"          padding-bottom: 5px;\n"
"         }\n"
"        ")

        self.horizontalLayoutButtons.addWidget(self.generateButton)

        self.cancelButton = QPushButton(GenerateObservationsDialog)
        self.cancelButton.setObjectName(u"cancelButton")
        self.cancelButton.setStyleSheet(u"\n"
"         QPushButton {\n"
"          background-color: #0078d7;\n"
"          color: #ffffff;\n"
"          padding: 6px;\n"
"          border-radius: 3px;\n"
"          border: none;\n"
"         }\n"
"         QPushButton:hover {\n"
"          background-color: #1a8cff;\n"
"         }\n"
"         QPushButton:pressed {\n"
"          background-color: #005bb5;\n"
"          padding-top: 7px;\n"
"          padding-bottom: 5px;\n"
"         }\n"
"        ")

        self.horizontalLayoutButtons.addWidget(self.cancelButton)


        self.verticalLayout.addLayout(self.horizontalLayoutButtons)


        self.retranslateUi(GenerateObservationsDialog)
        self.cancelButton.clicked.connect(GenerateObservationsDialog.reject)

        self.tabWidget.setCurrentIndex(0)
        self.generateButton.setDefault(True)


        QMetaObject.connectSlotsByName(GenerateObservationsDialog)
    # setupUi

    def retranslateUi(self, GenerateObservationsDialog):
        GenerateObservationsDialog.setWindowTitle(QCoreApplication.translate("GenerateObservationsDialog", u"Generate Observations", None))
        self.labelNamingMask.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Naming Mask:", None))
        self.namingMaskEdit.setPlaceholderText(QCoreApplication.translate("GenerateObservationsDialog", u"Observation_{i}_{s}_{dt}_{t}_{d}", None))
        self.labelFrequencies.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Frequencies:", None))
        self.labelTelescopes.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Telescopes:", None))
        self.labelSources.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Sources:", None))
        self.sourceSelectAllButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Select All", None))
        self.sourceUpButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Up", None))
        self.sourceClearButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Clear", None))
        self.sourceDownButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Down", None))
        self.telescopeClearButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Clear", None))
        self.telescopeSelectAllButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Select All", None))
        self.frequencyClearButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Clear", None))
        self.frequencySelectAllButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Select All", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabBasic), QCoreApplication.translate("GenerateObservationsDialog", u"Basic Settings", None))
        self.addOffSourceCheck.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Add Off-Source Scans", None))
        self.randomizeOrderCheck.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Randomize Scan Order", None))
        self.labelInterval.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Interval between Scans (s):", None))
        self.labelPreset.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Preset:", None))
        self.presetCombo.setItemText(0, QCoreApplication.translate("GenerateObservationsDialog", u"Standard VLBI", None))
        self.presetCombo.setItemText(1, QCoreApplication.translate("GenerateObservationsDialog", u"Quick Single Dish", None))

        self.savePresetButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Save Preset", None))
        self.loadPresetButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Load Preset", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabPattern), QCoreApplication.translate("GenerateObservationsDialog", u"Pattern Settings", None))
        self.labelObservationType.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Observation Type:", None))
        self.observationTypeCombo.setItemText(0, QCoreApplication.translate("GenerateObservationsDialog", u"VLBI", None))
        self.observationTypeCombo.setItemText(1, QCoreApplication.translate("GenerateObservationsDialog", u"SINGLE_DISH", None))

        self.labelTimeRange.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Time Range:", None))
        self.labelStartTime.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Start:", None))
        self.startTimeEdit.setDisplayFormat(QCoreApplication.translate("GenerateObservationsDialog", u"yyyy-MM-dd HH:mm:ss", None))
        self.labelEndTime.setText(QCoreApplication.translate("GenerateObservationsDialog", u"End:", None))
        self.endTimeEdit.setDisplayFormat(QCoreApplication.translate("GenerateObservationsDialog", u"yyyy-MM-dd HH:mm:ss", None))
        self.labelScanDuration.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Scan Duration (s):", None))
        self.labelNumScans.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Number of Scans:", None))
        self.chkParallel.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Observations Parallel in Time", None))
        self.generateButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Generate", None))
        self.cancelButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Cancel", None))
    # retranslateUi