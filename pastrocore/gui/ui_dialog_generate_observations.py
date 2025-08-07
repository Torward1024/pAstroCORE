# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_generate_observationsBzGjvc.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDateTimeEdit,
    QDialog, QDoubleSpinBox, QGridLayout, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QPushButton,
    QSizePolicy, QSpacerItem, QSpinBox, QVBoxLayout,
    QWidget)

class Ui_GenerateObservationsDialog(object):
    def setupUi(self, GenerateObservationsDialog):
        if not GenerateObservationsDialog.objectName():
            GenerateObservationsDialog.setObjectName(u"GenerateObservationsDialog")
        GenerateObservationsDialog.setWindowModality(Qt.WindowModality.WindowModal)
        GenerateObservationsDialog.resize(599, 553)
        icon = QIcon()
        icon.addFile(u":/icons/preferences.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        GenerateObservationsDialog.setWindowIcon(icon)
        GenerateObservationsDialog.setStyleSheet(u"background-color: #ffffff; font-family: Arial;")
        GenerateObservationsDialog.setModal(True)
        self.mainLayout = QVBoxLayout(GenerateObservationsDialog)
        self.mainLayout.setObjectName(u"mainLayout")
        self.labelObservations = QLabel(GenerateObservationsDialog)
        self.labelObservations.setObjectName(u"labelObservations")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setBold(True)
        self.labelObservations.setFont(font)

        self.mainLayout.addWidget(self.labelObservations)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer_2, 0, 0, 1, 1)

        self.sourceButtonLayout = QVBoxLayout()
        self.sourceButtonLayout.setObjectName(u"sourceButtonLayout")
        self.sourceSelectAllButton = QPushButton(GenerateObservationsDialog)
        self.sourceSelectAllButton.setObjectName(u"sourceSelectAllButton")
        self.sourceSelectAllButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5;\n"
"    padding-top: 7px;\n"
"    padding-bottom: 5px;\n"
"}")

        self.sourceButtonLayout.addWidget(self.sourceSelectAllButton)

        self.sourceClearButton = QPushButton(GenerateObservationsDialog)
        self.sourceClearButton.setObjectName(u"sourceClearButton")
        self.sourceClearButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5;\n"
"    padding-top: 7px;\n"
"    padding-bottom: 5px;\n"
"}")

        self.sourceButtonLayout.addWidget(self.sourceClearButton)


        self.gridLayout.addLayout(self.sourceButtonLayout, 0, 6, 1, 1)

        self.sourceList = QListWidget(GenerateObservationsDialog)
        self.sourceList.setObjectName(u"sourceList")
        self.sourceList.setStyleSheet(u"border: 1px solid #d3d3d3; background-color: #ffffff;")
        self.sourceList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.gridLayout.addWidget(self.sourceList, 0, 3, 1, 2)

        self.labelSources = QLabel(GenerateObservationsDialog)
        self.labelSources.setObjectName(u"labelSources")

        self.gridLayout.addWidget(self.labelSources, 0, 1, 1, 1)


        self.mainLayout.addLayout(self.gridLayout)

        self.telescopeLayout = QHBoxLayout()
        self.telescopeLayout.setObjectName(u"telescopeLayout")
        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.telescopeLayout.addItem(self.horizontalSpacer_3)

        self.labelTelescopes = QLabel(GenerateObservationsDialog)
        self.labelTelescopes.setObjectName(u"labelTelescopes")

        self.telescopeLayout.addWidget(self.labelTelescopes)

        self.telescopeList = QListWidget(GenerateObservationsDialog)
        self.telescopeList.setObjectName(u"telescopeList")
        self.telescopeList.setStyleSheet(u"border: 1px solid #d3d3d3; background-color: #ffffff;")
        self.telescopeList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.telescopeLayout.addWidget(self.telescopeList)

        self.telescopeButtonLayout = QVBoxLayout()
        self.telescopeButtonLayout.setObjectName(u"telescopeButtonLayout")
        self.telescopeSelectAllButton = QPushButton(GenerateObservationsDialog)
        self.telescopeSelectAllButton.setObjectName(u"telescopeSelectAllButton")
        self.telescopeSelectAllButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5;\n"
"    padding-top: 7px;\n"
"    padding-bottom: 5px;\n"
"}")

        self.telescopeButtonLayout.addWidget(self.telescopeSelectAllButton)

        self.telescopeClearButton = QPushButton(GenerateObservationsDialog)
        self.telescopeClearButton.setObjectName(u"telescopeClearButton")
        self.telescopeClearButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5;\n"
"    padding-top: 7px;\n"
"    padding-bottom: 5px;\n"
"}")

        self.telescopeButtonLayout.addWidget(self.telescopeClearButton)


        self.telescopeLayout.addLayout(self.telescopeButtonLayout)


        self.mainLayout.addLayout(self.telescopeLayout)

        self.frequencyLayout = QHBoxLayout()
        self.frequencyLayout.setObjectName(u"frequencyLayout")
        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.frequencyLayout.addItem(self.horizontalSpacer_4)

        self.labelFrequencies = QLabel(GenerateObservationsDialog)
        self.labelFrequencies.setObjectName(u"labelFrequencies")

        self.frequencyLayout.addWidget(self.labelFrequencies)

        self.frequencyList = QListWidget(GenerateObservationsDialog)
        self.frequencyList.setObjectName(u"frequencyList")
        self.frequencyList.setStyleSheet(u"border: 1px solid #d3d3d3; background-color: #ffffff;")
        self.frequencyList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.frequencyLayout.addWidget(self.frequencyList)

        self.frequencyButtonLayout = QVBoxLayout()
        self.frequencyButtonLayout.setObjectName(u"frequencyButtonLayout")
        self.frequencySelectAllButton = QPushButton(GenerateObservationsDialog)
        self.frequencySelectAllButton.setObjectName(u"frequencySelectAllButton")
        self.frequencySelectAllButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5;\n"
"    padding-top: 7px;\n"
"    padding-bottom: 5px;\n"
"}")

        self.frequencyButtonLayout.addWidget(self.frequencySelectAllButton)

        self.frequencyClearButton = QPushButton(GenerateObservationsDialog)
        self.frequencyClearButton.setObjectName(u"frequencyClearButton")
        self.frequencyClearButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5;\n"
"    padding-top: 7px;\n"
"    padding-bottom: 5px;\n"
"}")

        self.frequencyButtonLayout.addWidget(self.frequencyClearButton)


        self.frequencyLayout.addLayout(self.frequencyButtonLayout)


        self.mainLayout.addLayout(self.frequencyLayout)

        self.observationTypeLayout = QHBoxLayout()
        self.observationTypeLayout.setObjectName(u"observationTypeLayout")
        self.labelObservationType = QLabel(GenerateObservationsDialog)
        self.labelObservationType.setObjectName(u"labelObservationType")

        self.observationTypeLayout.addWidget(self.labelObservationType)

        self.observationTypeCombo = QComboBox(GenerateObservationsDialog)
        self.observationTypeCombo.addItem("")
        self.observationTypeCombo.addItem("")
        self.observationTypeCombo.setObjectName(u"observationTypeCombo")
        self.observationTypeCombo.setStyleSheet(u"QComboBox {\n"
"    background-color: #f0f6ff;\n"
"    border: 1px solid #0078d7;\n"
"    padding: 4px;\n"
"    border-radius: 3px;\n"
"}\n"
"QComboBox:hover {\n"
"    border: 1px solid #1a8cff;\n"
"}\n"
"QComboBox:focus {\n"
"    border: 1px solid #005bb5;\n"
"    background-color: #ffffff;\n"
"}\n"
"QComboBox::drop-down {\n"
"    width: 20px;\n"
"    border-left: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"}\n"
"QComboBox::down-arrow {\n"
"    image: url(:/icons/down_arrow_icon.svg);\n"
"    width: 12px;\n"
"    height: 12px;\n"
"}")

        self.observationTypeLayout.addWidget(self.observationTypeCombo)


        self.mainLayout.addLayout(self.observationTypeLayout)

        self.timeRangeLayout = QHBoxLayout()
        self.timeRangeLayout.setObjectName(u"timeRangeLayout")
        self.labelTimeRange = QLabel(GenerateObservationsDialog)
        self.labelTimeRange.setObjectName(u"labelTimeRange")

        self.timeRangeLayout.addWidget(self.labelTimeRange)

        self.timeRangeFieldsLayout = QVBoxLayout()
        self.timeRangeFieldsLayout.setObjectName(u"timeRangeFieldsLayout")
        self.startTimeLayout = QHBoxLayout()
        self.startTimeLayout.setObjectName(u"startTimeLayout")
        self.labelStartTime = QLabel(GenerateObservationsDialog)
        self.labelStartTime.setObjectName(u"labelStartTime")

        self.startTimeLayout.addWidget(self.labelStartTime)

        self.startTimeEdit = QDateTimeEdit(GenerateObservationsDialog)
        self.startTimeEdit.setObjectName(u"startTimeEdit")
        self.startTimeEdit.setStyleSheet(u"QDateTimeEdit {\n"
"    background-color: #f0f6ff;\n"
"    border: 1px solid #0078d7;\n"
"    padding: 4px;\n"
"    border-radius: 3px;\n"
"}\n"
"QDateTimeEdit:hover {\n"
"    border: 1px solid #1a8cff;\n"
"}\n"
"QDateTimeEdit:focus {\n"
"    border: 1px solid #005bb5;\n"
"    background-color: #ffffff;\n"
"}")
        self.startTimeEdit.setCalendarPopup(True)

        self.startTimeLayout.addWidget(self.startTimeEdit)


        self.timeRangeFieldsLayout.addLayout(self.startTimeLayout)

        self.endTimeLayout = QHBoxLayout()
        self.endTimeLayout.setObjectName(u"endTimeLayout")
        self.labelEndTime = QLabel(GenerateObservationsDialog)
        self.labelEndTime.setObjectName(u"labelEndTime")

        self.endTimeLayout.addWidget(self.labelEndTime)

        self.endTimeEdit = QDateTimeEdit(GenerateObservationsDialog)
        self.endTimeEdit.setObjectName(u"endTimeEdit")
        self.endTimeEdit.setStyleSheet(u"QDateTimeEdit {\n"
"    background-color: #f0f6ff;\n"
"    border: 1px solid #0078d7;\n"
"    padding: 4px;\n"
"    border-radius: 3px;\n"
"}\n"
"QDateTimeEdit:hover {\n"
"    border: 1px solid #1a8cff;\n"
"}\n"
"QDateTimeEdit:focus {\n"
"    border: 1px solid #005bb5;\n"
"    background-color: #ffffff;\n"
"}")
        self.endTimeEdit.setCalendarPopup(True)

        self.endTimeLayout.addWidget(self.endTimeEdit)


        self.timeRangeFieldsLayout.addLayout(self.endTimeLayout)


        self.timeRangeLayout.addLayout(self.timeRangeFieldsLayout)


        self.mainLayout.addLayout(self.timeRangeLayout)

        self.scanDurationLayout = QHBoxLayout()
        self.scanDurationLayout.setObjectName(u"scanDurationLayout")
        self.labelScanDuration = QLabel(GenerateObservationsDialog)
        self.labelScanDuration.setObjectName(u"labelScanDuration")

        self.scanDurationLayout.addWidget(self.labelScanDuration)

        self.scanDurationSpinBox = QDoubleSpinBox(GenerateObservationsDialog)
        self.scanDurationSpinBox.setObjectName(u"scanDurationSpinBox")
        self.scanDurationSpinBox.setStyleSheet(u"QDoubleSpinBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    padding-right: 20px;\n"
"    border-radius: 3px;\n"
"    background-color: #f0f6ff;\n"
"    border: 1px solid #0078d7;\n"
"}\n"
"QDoubleSpinBox:hover {\n"
"    border: 1px solid #1a8cff;\n"
"}\n"
"QDoubleSpinBox:focus {\n"
"    border: 1px solid #005bb5;\n"
"    background-color: #ffffff;\n"
"}\n"
"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {\n"
"    width: 20px;\n"
"    border-left: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"}\n"
"QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {\n"
"    background-color: #0078d7;\n"
"}\n"
"QDoubleSpinBox::up-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/up_arrow_icon.svg);\n"
"}\n"
"QDoubleSpinBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/down_arrow_icon.svg);\n"
"}")
        self.scanDurationSpinBox.setMinimum(1.000000000000000)
        self.scanDurationSpinBox.setMaximum(3600.000000000000000)
        self.scanDurationSpinBox.setValue(300.000000000000000)

        self.scanDurationLayout.addWidget(self.scanDurationSpinBox)


        self.mainLayout.addLayout(self.scanDurationLayout)

        self.numScansLayout = QHBoxLayout()
        self.numScansLayout.setObjectName(u"numScansLayout")
        self.labelNumScans = QLabel(GenerateObservationsDialog)
        self.labelNumScans.setObjectName(u"labelNumScans")

        self.numScansLayout.addWidget(self.labelNumScans)

        self.numScansSpinBox = QSpinBox(GenerateObservationsDialog)
        self.numScansSpinBox.setObjectName(u"numScansSpinBox")
        self.numScansSpinBox.setStyleSheet(u"QSpinBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    padding-right: 20px;\n"
"    border-radius: 3px;\n"
"    background-color: #f0f6ff;\n"
"    border: 1px solid #0078d7;\n"
"}\n"
"QSpinBox:hover {\n"
"    border: 1px solid #1a8cff;\n"
"}\n"
"QSpinBox:focus {\n"
"    border: 1px solid #005bb5;\n"
"    background-color: #ffffff;\n"
"}\n"
"QSpinBox::up-button, QSpinBox::down-button {\n"
"    width: 20px;\n"
"    border-left: 1px solid #d3d3d3;\n"
"    background-color: #f9f9f9;\n"
"}\n"
"QSpinBox::up-button:hover, QSpinBox::down-button:hover {\n"
"    background-color: #0078d7;\n"
"}\n"
"QSpinBox::up-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/up_arrow_icon.svg);\n"
"}\n"
"QSpinBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/icons/down_arrow_icon.svg);\n"
"}")
        self.numScansSpinBox.setMinimum(1)
        self.numScansSpinBox.setMaximum(100)
        self.numScansSpinBox.setValue(5)

        self.numScansLayout.addWidget(self.numScansSpinBox)


        self.mainLayout.addLayout(self.numScansLayout)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.mainLayout.addItem(self.verticalSpacer)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonLayout.addItem(self.horizontalSpacer)

        self.generateButton = QPushButton(GenerateObservationsDialog)
        self.generateButton.setObjectName(u"generateButton")
        self.generateButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5;\n"
"    padding-top: 7px;\n"
"    padding-bottom: 5px;\n"
"}")

        self.buttonLayout.addWidget(self.generateButton)

        self.cancelButton = QPushButton(GenerateObservationsDialog)
        self.cancelButton.setObjectName(u"cancelButton")
        self.cancelButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 6px;\n"
"    border-radius: 3px;\n"
"    border: none;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #1a8cff;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #005bb5;\n"
"    padding-top: 7px;\n"
"    padding-bottom: 5px;\n"
"}")

        self.buttonLayout.addWidget(self.cancelButton)


        self.mainLayout.addLayout(self.buttonLayout)


        self.retranslateUi(GenerateObservationsDialog)
        self.cancelButton.clicked.connect(GenerateObservationsDialog.reject)

        self.generateButton.setDefault(True)


        QMetaObject.connectSlotsByName(GenerateObservationsDialog)
    # setupUi

    def retranslateUi(self, GenerateObservationsDialog):
        GenerateObservationsDialog.setWindowTitle(QCoreApplication.translate("GenerateObservationsDialog", u"Generate Observations", None))
        self.labelObservations.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Observations Parameters:", None))
        self.sourceSelectAllButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Select All", None))
        self.sourceClearButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Clear", None))
        self.labelSources.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Sources:", None))
        self.labelTelescopes.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Telescopes:", None))
        self.telescopeSelectAllButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Select All", None))
        self.telescopeClearButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Clear", None))
        self.labelFrequencies.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Frequencies:", None))
        self.frequencySelectAllButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Select All", None))
        self.frequencyClearButton.setText(QCoreApplication.translate("GenerateObservationsDialog", u"Clear", None))
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