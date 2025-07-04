# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_calculationsKAgmFt.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QDialog,
    QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QSizePolicy,
    QSpacerItem, QWidget)

class Ui_CalculationDialog(object):
    def setupUi(self, CalculationDialog):
        if not CalculationDialog.objectName():
            CalculationDialog.setObjectName(u"CalculationDialog")
        CalculationDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        CalculationDialog.resize(616, 461)
        icon = QIcon()
        icon.addFile(u":/icons/calculate.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        CalculationDialog.setWindowIcon(icon)
        CalculationDialog.setStyleSheet(u"background-color: #ffffff; font-family: Arial;")
        CalculationDialog.setModal(True)
        self.gridLayout_3 = QGridLayout(CalculationDialog)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.labelTargets = QLabel(CalculationDialog)
        self.labelTargets.setObjectName(u"labelTargets")

        self.gridLayout.addWidget(self.labelTargets, 2, 4, 1, 1)

        self.targetList = QListWidget(CalculationDialog)
        self.targetList.setObjectName(u"targetList")
        self.targetList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.gridLayout.addWidget(self.targetList, 3, 4, 1, 1)

        self.labelCalc = QLabel(CalculationDialog)
        self.labelCalc.setObjectName(u"labelCalc")

        self.gridLayout.addWidget(self.labelCalc, 2, 2, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.selectAllObsButton = QPushButton(CalculationDialog)
        self.selectAllObsButton.setObjectName(u"selectAllObsButton")
        self.selectAllObsButton.setStyleSheet(u"QPushButton {\n"
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
        self.selectAllObsButton.setFlat(True)

        self.horizontalLayout.addWidget(self.selectAllObsButton)

        self.clearAllObsButton = QPushButton(CalculationDialog)
        self.clearAllObsButton.setObjectName(u"clearAllObsButton")
        self.clearAllObsButton.setStyleSheet(u"QPushButton {\n"
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

        self.horizontalLayout.addWidget(self.clearAllObsButton)


        self.gridLayout.addLayout(self.horizontalLayout, 6, 4, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_3)

        self.selectAllCalcButton = QPushButton(CalculationDialog)
        self.selectAllCalcButton.setObjectName(u"selectAllCalcButton")
        self.selectAllCalcButton.setStyleSheet(u"QPushButton {\n"
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

        self.horizontalLayout_2.addWidget(self.selectAllCalcButton)

        self.clearAllCalcButton = QPushButton(CalculationDialog)
        self.clearAllCalcButton.setObjectName(u"clearAllCalcButton")
        self.clearAllCalcButton.setStyleSheet(u"QPushButton {\n"
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

        self.horizontalLayout_2.addWidget(self.clearAllCalcButton)


        self.gridLayout.addLayout(self.horizontalLayout_2, 6, 2, 1, 1)

        self.calcList = QListWidget(CalculationDialog)
        self.calcList.setObjectName(u"calcList")

        self.gridLayout.addWidget(self.calcList, 3, 2, 1, 1)


        self.gridLayout_3.addLayout(self.gridLayout, 1, 0, 1, 1)

        self.labelCalculations = QLabel(CalculationDialog)
        self.labelCalculations.setObjectName(u"labelCalculations")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setBold(True)
        self.labelCalculations.setFont(font)

        self.gridLayout_3.addWidget(self.labelCalculations, 0, 0, 1, 1)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonLayout.addItem(self.horizontalSpacer)

        self.calcButton = QPushButton(CalculationDialog)
        self.calcButton.setObjectName(u"calcButton")
        self.calcButton.setStyleSheet(u"QPushButton {\n"
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
        self.calcButton.setAutoDefault(False)
        self.calcButton.setFlat(True)

        self.buttonLayout.addWidget(self.calcButton)

        self.cancelButton = QPushButton(CalculationDialog)
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
        self.cancelButton.setAutoDefault(True)
        self.cancelButton.setFlat(True)

        self.buttonLayout.addWidget(self.cancelButton)


        self.gridLayout_3.addLayout(self.buttonLayout, 4, 0, 1, 1)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.labelTimestep = QLabel(CalculationDialog)
        self.labelTimestep.setObjectName(u"labelTimestep")

        self.gridLayout_2.addWidget(self.labelTimestep, 0, 0, 1, 1)

        self.timeStepSpin = QDoubleSpinBox(CalculationDialog)
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
        self.timeStepSpin.setMaximum(3600.000000000000000)
        self.timeStepSpin.setValue(600.000000000000000)

        self.gridLayout_2.addWidget(self.timeStepSpin, 0, 1, 1, 1)

        self.recalculateCheck = QCheckBox(CalculationDialog)
        self.recalculateCheck.setObjectName(u"recalculateCheck")
        self.recalculateCheck.setChecked(True)
        self.recalculateCheck.setTristate(False)

        self.gridLayout_2.addWidget(self.recalculateCheck, 1, 0, 1, 2)


        self.gridLayout_3.addLayout(self.gridLayout_2, 3, 0, 1, 1)

        self.labelParameters = QLabel(CalculationDialog)
        self.labelParameters.setObjectName(u"labelParameters")
        self.labelParameters.setFont(font)

        self.gridLayout_3.addWidget(self.labelParameters, 2, 0, 1, 1)


        self.retranslateUi(CalculationDialog)

        QMetaObject.connectSlotsByName(CalculationDialog)
    # setupUi

    def retranslateUi(self, CalculationDialog):
        CalculationDialog.setWindowTitle(QCoreApplication.translate("CalculationDialog", u"Perform Calculations", None))
        self.labelTargets.setText(QCoreApplication.translate("CalculationDialog", u"Observations:", None))
        self.labelCalc.setText(QCoreApplication.translate("CalculationDialog", u"Calculations:", None))
        self.selectAllObsButton.setText(QCoreApplication.translate("CalculationDialog", u"Select All", None))
        self.clearAllObsButton.setText(QCoreApplication.translate("CalculationDialog", u"Clear", None))
        self.selectAllCalcButton.setText(QCoreApplication.translate("CalculationDialog", u"Select All", None))
        self.clearAllCalcButton.setText(QCoreApplication.translate("CalculationDialog", u"Clear", None))
        self.labelCalculations.setText(QCoreApplication.translate("CalculationDialog", u"Calculations:", None))
        self.calcButton.setText(QCoreApplication.translate("CalculationDialog", u"Calculate", None))
        self.cancelButton.setText(QCoreApplication.translate("CalculationDialog", u"Cancel", None))
        self.labelTimestep.setText(QCoreApplication.translate("CalculationDialog", u"Time step (s):", None))
        self.recalculateCheck.setText(QCoreApplication.translate("CalculationDialog", u"Recalculate", None))
        self.labelParameters.setText(QCoreApplication.translate("CalculationDialog", u"Parameters:", None))
    # retranslateUi