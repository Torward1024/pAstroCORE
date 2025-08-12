# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_generate_observationsQkxhEq.ui'
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
    QDateTimeEdit, QDialog, QDoubleSpinBox, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QSizePolicy, QSpacerItem, QSpinBox,
    QTabWidget, QVBoxLayout, QWidget)

class Ui_GenerateObservationsDialog(object):
    def setupUi(self, GenerateObservationsDialog):
        if not GenerateObservationsDialog.objectName():
            GenerateObservationsDialog.setObjectName(u"GenerateObservationsDialog")
        GenerateObservationsDialog.resize(750, 685)
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
        self.verticalLayoutBasic = QVBoxLayout(self.tabBasic)
        self.verticalLayoutBasic.setObjectName(u"verticalLayoutBasic")
        self.horizontalLayoutSources = QHBoxLayout()
        self.horizontalLayoutSources.setObjectName(u"horizontalLayoutSources")
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

        self.horizontalLayoutSources.addWidget(self.sourceSelectAllButton)

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

        self.horizontalLayoutSources.addWidget(self.sourceClearButton)

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

        self.horizontalLayoutSources.addWidget(self.sourceUpButton)

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

        self.horizontalLayoutSources.addWidget(self.sourceDownButton)


        self.verticalLayoutBasic.addLayout(self.horizontalLayoutSources)

        self.labelSources = QLabel(self.tabBasic)
        self.labelSources.setObjectName(u"labelSources")

        self.verticalLayoutBasic.addWidget(self.labelSources)

        self.sourceList = QListWidget(self.tabBasic)
        self.sourceList.setObjectName(u"sourceList")
        self.sourceList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sourceList.setStyleSheet(u"border: 1px solid #d3d3d3; background-color: #ffffff;")
        self.sourceList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.verticalLayoutBasic.addWidget(self.sourceList)

        self.horizontalLayoutTelescopes = QHBoxLayout()
        self.horizontalLayoutTelescopes.setObjectName(u"horizontalLayoutTelescopes")
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

        self.horizontalLayoutTelescopes.addWidget(self.telescopeSelectAllButton)

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

        self.horizontalLayoutTelescopes.addWidget(self.telescopeClearButton)


        self.verticalLayoutBasic.addLayout(self.horizontalLayoutTelescopes)

        self.labelTelescopes = QLabel(self.tabBasic)
        self.labelTelescopes.setObjectName(u"labelTelescopes")

        self.verticalLayoutBasic.addWidget(self.labelTelescopes)

        self.telescopeList = QListWidget(self.tabBasic)
        self.telescopeList.setObjectName(u"telescopeList")
        self.telescopeList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.telescopeList.setStyleSheet(u"border: 1px solid #d3d3d3; background-color: #ffffff;")
        self.telescopeList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.verticalLayoutBasic.addWidget(self.telescopeList)

        self.horizontalLayoutFrequencies = QHBoxLayout()
        self.horizontalLayoutFrequencies.setObjectName(u"horizontalLayoutFrequencies")
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

        self.horizontalLayoutFrequencies.addWidget(self.frequencySelectAllButton)

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

        self.horizontalLayoutFrequencies.addWidget(self.frequencyClearButton)


        self.verticalLayoutBasic.addLayout(self.horizontalLayoutFrequencies)

        self.labelFrequencies = QLabel(self.tabBasic)
        self.labelFrequencies.setObjectName(u"labelFrequencies")

        self.verticalLayoutBasic.addWidget(self.labelFrequencies)

        self.frequencyList = QListWidget(self.tabBasic)
        self.frequencyList.setObjectName(u"frequencyList")
        self.frequencyList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.frequencyList.setStyleSheet(u"border: 1px solid #d3d3d3; background-color: #ffffff;")
        self.frequencyList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.verticalLayoutBasic.addWidget(self.frequencyList)

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


        self.verticalLayoutBasic.addLayout(self.horizontalLayoutNaming)

        self.tabWidget.addTab(self.tabBasic, "")
        self.tabPattern = QWidget()
        self.tabPattern.setObjectName(u"tabPattern")
        self.verticalLayoutPattern = QVBoxLayout(self.tabPattern)
        self.verticalLayoutPattern.setObjectName(u"verticalLayoutPattern")
        self.addOffSourceCheck = QCheckBox(self.tabPattern)
        self.addOffSourceCheck.setObjectName(u"addOffSourceCheck")
        self.addOffSourceCheck.setStyleSheet(u"\n"
"           QCheckBox {\n"
"            color: #333333;\n"
"            padding: 4px;\n"
"           }\n"
"           QCheckBox::indicator {\n"
"            width: 16px;\n"
"            height: 16px;\n"
"           }\n"
"           QCheckBox::indicator:checked {\n"
"            background-color: #0078d7;\n"
"            border: 1px solid #0078d7;\n"
"           }\n"
"          ")
        self.addOffSourceCheck.setChecked(False)

        self.verticalLayoutPattern.addWidget(self.addOffSourceCheck)

        self.randomizeOrderCheck = QCheckBox(self.tabPattern)
        self.randomizeOrderCheck.setObjectName(u"randomizeOrderCheck")
        self.randomizeOrderCheck.setStyleSheet(u"\n"
"           QCheckBox {\n"
"            color: #333333;\n"
"            padding: 4px;\n"
"           }\n"
"           QCheckBox::indicator {\n"
"            width: 16px;\n"
"            height: 16px;\n"
"           }\n"
"           QCheckBox::indicator:checked {\n"
"            background-color: #0078d7;\n"
"            border: 1px solid #0078d7;\n"
"           }\n"
"          ")
        self.randomizeOrderCheck.setChecked(False)

        self.verticalLayoutPattern.addWidget(self.randomizeOrderCheck)

        self.horizontalLayoutInterval = QHBoxLayout()
        self.horizontalLayoutInterval.setObjectName(u"horizontalLayoutInterval")
        self.labelInterval = QLabel(self.tabPattern)
        self.labelInterval.setObjectName(u"labelInterval")

        self.horizontalLayoutInterval.addWidget(self.labelInterval)

        self.intervalSpinBox = QSpinBox(self.tabPattern)
        self.intervalSpinBox.setObjectName(u"intervalSpinBox")
        self.intervalSpinBox.setStyleSheet(u"\n"
"             QSpinBox {\n"
"              font-family: Arial;\n"
"              font-size: 9pt;\n"
"              color: #333333;\n"
"              padding: 1px;\n"
"              padding-right: 20px;\n"
"              border-radius: 3px;\n"
"              background-color: #f0f6ff;\n"
"              border: 1px solid #0078d7;\n"
"             }\n"
"             QSpinBox:hover {\n"
"              border: 1px solid #1a8cff;\n"
"             }\n"
"             QSpinBox:focus {\n"
"              border: 1px solid #005bb5;\n"
"              background-color: #ffffff;\n"
"             }\n"
"             QSpinBox::up-button, QSpinBox::down-button {\n"
"              width: 20px;\n"
"              border-left: 1px solid #d3d3d3;\n"
"              background-color: #f9f9f9;\n"
"             }\n"
"             QSpinBox::up-button:hover, QSpinBox::down-button:hover {\n"
"              background-color: #0078d7;\n"
"             }\n"
"             QSpinBox::up-arrow {\n"
"              width: 12px;\n"
"             "
                        " height: 12px;\n"
"              image: url(:/icons/up_arrow_icon.svg);\n"
"             }\n"
"             QSpinBox::down-arrow {\n"
"              width: 12px;\n"
"              height: 12px;\n"
"              image: url(:/icons/down_arrow_icon.svg);\n"
"             }\n"
"            ")
        self.intervalSpinBox.setMinimum(0)
        self.intervalSpinBox.setMaximum(60)
        self.intervalSpinBox.setValue(5)

        self.horizontalLayoutInterval.addWidget(self.intervalSpinBox)


        self.verticalLayoutPattern.addLayout(self.horizontalLayoutInterval)

        self.labelPreset = QLabel(self.tabPattern)
        self.labelPreset.setObjectName(u"labelPreset")

        self.verticalLayoutPattern.addWidget(self.labelPreset)

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

        self.verticalLayoutPattern.addWidget(self.presetCombo)

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


        self.verticalLayoutPattern.addLayout(self.horizontalLayoutPresetButtons)

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
        self.startTimeEdit.setStyleSheet(u"\n"
"           QDateTimeEdit {\n"
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
        self.endTimeEdit.setStyleSheet(u"\n"
"           QDateTimeEdit {\n"
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
        self.scanDurationSpinBox.setStyleSheet(u"\n"
"         QDoubleSpinBox {\n"
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
"          image: url(:/icons/up_arrow_icon.sv"
                        "g);\n"
"         }\n"
"         QDoubleSpinBox::down-arrow {\n"
"          width: 12px;\n"
"          height: 12px;\n"
"          image: url(:/icons/down_arrow_icon.svg);\n"
"         }\n"
"        ")
        self.scanDurationSpinBox.setMinimum(1.000000000000000)
        self.scanDurationSpinBox.setMaximum(3600.000000000000000)
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
        self.numScansSpinBox.setStyleSheet(u"\n"
"         QSpinBox {\n"
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
"         QSpinBox::down-a"
                        "rrow {\n"
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
        self.sourceSelectAllButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Select All", None))
        self.sourceClearButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Clear", None))
        self.sourceUpButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Up", None))
        self.sourceDownButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Down", None))
        self.labelSources.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Sources:", None))
        self.telescopeSelectAllButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Select All", None))
        self.telescopeClearButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Clear", None))
        self.labelTelescopes.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Telescopes:", None))
        self.frequencySelectAllButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Select All", None))
        self.frequencyClearButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Clear", None))
        self.labelFrequencies.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Frequencies:", None))
        self.labelNamingMask.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Naming Mask:", None))
        self.namingMaskEdit.setPlaceholderText(QCoreApplication.translate("GenerateObservationsDialog", u"Observation_{i}_{s}_{dt}_{t}_{d}", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabBasic), QCoreApplication.translate("GenerateObservationsDialog", u"Basic Settings", None))
        self.addOffSourceCheck.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Add Off-Source Scans", None))
        self.randomizeOrderCheck.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Randomize Scan Order", None))
        self.labelInterval.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Interval between Scans (min):", None))
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
        self.generateButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Generate", None))
        self.cancelButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Cancel", None))
    # retranslateUi