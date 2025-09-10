# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_export_calculated_dataPkDjnJ.ui'
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
    QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPushButton,
    QSizePolicy, QSpacerItem, QWidget)

class Ui_ExportCalculatedDataDialog(object):
    def setupUi(self, ExportCalculatedDataDialog):
        if not ExportCalculatedDataDialog.objectName():
            ExportCalculatedDataDialog.setObjectName(u"ExportCalculatedDataDialog")
        ExportCalculatedDataDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        ExportCalculatedDataDialog.resize(600, 450)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(ExportCalculatedDataDialog.sizePolicy().hasHeightForWidth())
        ExportCalculatedDataDialog.setSizePolicy(sizePolicy)
        ExportCalculatedDataDialog.setMinimumSize(QSize(600, 450))
        ExportCalculatedDataDialog.setMaximumSize(QSize(600, 450))
        icon = QIcon()
        icon.addFile(u":/icons/export_icon.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        ExportCalculatedDataDialog.setWindowIcon(icon)
        ExportCalculatedDataDialog.setStyleSheet(u"background-color: #ffffff; font-family: Arial;")
        ExportCalculatedDataDialog.setModal(True)
        self.gridLayout_2 = QGridLayout(ExportCalculatedDataDialog)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.line_2 = QFrame(ExportCalculatedDataDialog)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.line_2, 7, 0, 1, 1)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonLayout.addItem(self.horizontalSpacer)

        self.exportButton = QPushButton(ExportCalculatedDataDialog)
        self.exportButton.setObjectName(u"exportButton")
        self.exportButton.setStyleSheet(u"QPushButton {\n"
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
        self.exportButton.setAutoDefault(False)
        self.exportButton.setFlat(True)

        self.buttonLayout.addWidget(self.exportButton)

        self.cancelButton = QPushButton(ExportCalculatedDataDialog)
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


        self.gridLayout_2.addLayout(self.buttonLayout, 8, 0, 1, 1)

        self.labelParameters = QLabel(ExportCalculatedDataDialog)
        self.labelParameters.setObjectName(u"labelParameters")
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setBold(False)
        self.labelParameters.setFont(font)

        self.gridLayout_2.addWidget(self.labelParameters, 2, 0, 1, 1)

        self.line = QFrame(ExportCalculatedDataDialog)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.line, 1, 0, 1, 1)

        self.chkExportVisualizations = QCheckBox(ExportCalculatedDataDialog)
        self.chkExportVisualizations.setObjectName(u"chkExportVisualizations")
        self.chkExportVisualizations.setChecked(True)

        self.gridLayout_2.addWidget(self.chkExportVisualizations, 3, 0, 1, 1)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_3)

        self.selectAllCalcButton = QPushButton(ExportCalculatedDataDialog)
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

        self.clearAllCalcButton = QPushButton(ExportCalculatedDataDialog)
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

        self.targetList = QListWidget(ExportCalculatedDataDialog)
        self.targetList.setObjectName(u"targetList")
        self.targetList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.gridLayout.addWidget(self.targetList, 3, 3, 1, 1)

        self.labelTargets = QLabel(ExportCalculatedDataDialog)
        self.labelTargets.setObjectName(u"labelTargets")

        self.gridLayout.addWidget(self.labelTargets, 2, 3, 1, 1)

        self.labelCalc = QLabel(ExportCalculatedDataDialog)
        self.labelCalc.setObjectName(u"labelCalc")

        self.gridLayout.addWidget(self.labelCalc, 2, 2, 1, 1)

        self.calcList = QListWidget(ExportCalculatedDataDialog)
        self.calcList.setObjectName(u"calcList")

        self.gridLayout.addWidget(self.calcList, 3, 2, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.selectAllObsButton = QPushButton(ExportCalculatedDataDialog)
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

        self.clearAllObsButton = QPushButton(ExportCalculatedDataDialog)
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


        self.gridLayout.addLayout(self.horizontalLayout, 6, 3, 1, 1)


        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.lblPath = QLabel(ExportCalculatedDataDialog)
        self.lblPath.setObjectName(u"lblPath")

        self.horizontalLayout_3.addWidget(self.lblPath)

        self.lineEdit = QLineEdit(ExportCalculatedDataDialog)
        self.lineEdit.setObjectName(u"lineEdit")
        self.lineEdit.setStyleSheet(u"QLineEdit {\n"
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

        self.horizontalLayout_3.addWidget(self.lineEdit)

        self.pushButton = QPushButton(ExportCalculatedDataDialog)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setStyleSheet(u"QPushButton {\n"
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

        self.horizontalLayout_3.addWidget(self.pushButton)


        self.gridLayout_2.addLayout(self.horizontalLayout_3, 6, 0, 1, 1)

        self.chkExportData = QCheckBox(ExportCalculatedDataDialog)
        self.chkExportData.setObjectName(u"chkExportData")
        self.chkExportData.setEnabled(False)
        self.chkExportData.setChecked(False)

        self.gridLayout_2.addWidget(self.chkExportData, 4, 0, 1, 1)


        self.retranslateUi(ExportCalculatedDataDialog)

        QMetaObject.connectSlotsByName(ExportCalculatedDataDialog)
    # setupUi

    def retranslateUi(self, ExportCalculatedDataDialog):
        ExportCalculatedDataDialog.setWindowTitle(QCoreApplication.translate("ExportCalculatedDataDialog", u"Export Calculated Data", None))
        self.exportButton.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Export", None))
        self.cancelButton.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Cancel", None))
        self.labelParameters.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Parameters:", None))
        self.chkExportVisualizations.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Export Visualizations", None))
        self.selectAllCalcButton.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Select All", None))
        self.clearAllCalcButton.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Clear", None))
        self.labelTargets.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Observations:", None))
        self.labelCalc.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Calculations:", None))
        self.selectAllObsButton.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Select All", None))
        self.clearAllObsButton.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Clear", None))
        self.lblPath.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Path:", None))
        self.pushButton.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Browse", None))
        self.chkExportData.setText(QCoreApplication.translate("ExportCalculatedDataDialog", u"Export Data", None))
    # retranslateUi