# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_calculationsexnJKs.ui'
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
    QDoubleSpinBox, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QListWidget, QListWidgetItem, QPushButton,
    QSizePolicy, QSpacerItem, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget)

class Ui_CalculationDialog(object):
    def setupUi(self, CalculationDialog):
        if not CalculationDialog.objectName():
            CalculationDialog.setObjectName(u"CalculationDialog")
        CalculationDialog.resize(611, 585)
        CalculationDialog.setStyleSheet(u"background-color: #ffffff; font-family: Arial;")
        CalculationDialog.setModal(True)
        self.gridLayout = QGridLayout(CalculationDialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.labelCalculations = QLabel(CalculationDialog)
        self.labelCalculations.setObjectName(u"labelCalculations")

        self.gridLayout.addWidget(self.labelCalculations, 0, 0, 1, 2)

        self.calcTable = QTableWidget(CalculationDialog)
        if (self.calcTable.columnCount() < 4):
            self.calcTable.setColumnCount(4)
        __qtablewidgetitem = QTableWidgetItem()
        self.calcTable.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.calcTable.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.calcTable.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.calcTable.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        self.calcTable.setObjectName(u"calcTable")
        self.calcTable.setStyleSheet(u"/* QTableWidget styles for pAstroCORE */\n"
"QTableWidget {\n"
"    background-color: #ffffff;\n"
"    gridline-color: #d3d3d3;\n"
"    color: #333333;\n"
"    font-family: Arial, sans-serif;\n"
"    font-size: 9pt;\n"
"    border: 1px solid #d3d3d3;\n"
"}\n"
"QTableWidget::item {\n"
"    padding: 4px;\n"
"}\n"
"QTableWidget::item:selected {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"    padding: 4px;\n"
"}\n"
"QTableWidget::item:hover {\n"
"    background-color: #1a8cff;\n"
"    color: #ffffff;\n"
"    padding: 4px;\n"
"}\n"
"QHeaderView {\n"
"    background-color: #f9f9f9;\n"
"    border: none;\n"
"    border-bottom: 1px solid #d3d3d3;\n"
"}\n"
"QHeaderView::section {\n"
"    background-color: #f9f9f9;\n"
"    color: #333333;\n"
"    border-bottom: none;\n"
"    border-right: none;\n"
"    border-left: none;\n"
"    border-top: none;\n"
"    padding: 4px;\n"
"    font-family: Arial, sans-serif;\n"
"    font-size: 9pt;\n"
"}\n"
"QHeaderView::section:horizontal {\n"
"    border-right: 1px s"
                        "olid #d3d3d3;\n"
"}\n"
"QHeaderView::section:vertical {\n"
"    border-bottom: 1px solid #d3d3d3;\n"
"}\n"
"QHeaderView::section:hover {\n"
"    background-color: #1a8cff;\n"
"    color: #ffffff;\n"
"    padding: 4px;\n"
"}")

        self.gridLayout.addWidget(self.calcTable, 1, 0, 1, 2)

        self.labelTargets = QLabel(CalculationDialog)
        self.labelTargets.setObjectName(u"labelTargets")

        self.gridLayout.addWidget(self.labelTargets, 2, 0, 1, 2)

        self.targetList = QListWidget(CalculationDialog)
        self.targetList.setObjectName(u"targetList")
        self.targetList.setStyleSheet(u"QListWidget {\n"
"    background-color: #ffffff;\n"
"    color: #333333;\n"
"    font-family: Arial, sans-serif;\n"
"    font-size: 9pt;\n"
"    border: 1px solid #d3d3d3;\n"
"}\n"
"QListWidget::item {\n"
"    padding: 4px;\n"
"}\n"
"QListWidget::item:selected {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"}\n"
"QListWidget::item:hover {\n"
"    background-color: #1a8cff;\n"
"    color: #ffffff;\n"
"}")
        self.targetList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.gridLayout.addWidget(self.targetList, 3, 0, 1, 2)

        self.selectAllButton = QPushButton(CalculationDialog)
        self.selectAllButton.setObjectName(u"selectAllButton")
        self.selectAllButton.setStyleSheet(u"QPushButton {\n"
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
        self.selectAllButton.setFlat(True)

        self.gridLayout.addWidget(self.selectAllButton, 4, 0, 1, 2)

        self.labelParameters = QLabel(CalculationDialog)
        self.labelParameters.setObjectName(u"labelParameters")

        self.gridLayout.addWidget(self.labelParameters, 5, 0, 1, 2)

        self.paramsLayout = QVBoxLayout()
        self.paramsLayout.setObjectName(u"paramsLayout")
        self.timeStepSpin = QDoubleSpinBox(CalculationDialog)
        self.timeStepSpin.setObjectName(u"timeStepSpin")
        self.timeStepSpin.setStyleSheet(u"QDoubleSpinBox {\n"
"    font-family: Arial;\n"
"    font-size: 9pt;\n"
"    color: #333333;\n"
"    padding: 1px;\n"
"    border-radius: 3px;\n"
"    background-color: #f9f9f9;\n"
"    border: 1px solid #d3d3d3;\n"
"}\n"
"QDoubleSpinBox:editable {\n"
"    background-color: #f0f6ff;\n"
"    border: 1px solid #0078d7;\n"
"}\n"
"QDoubleSpinBox:editable:hover {\n"
"    border: 1px solid #1a8cff;\n"
"}\n"
"QDoubleSpinBox:editable:focus {\n"
"    border: 1px solid #005bb5;\n"
"    background-color: #ffffff;\n"
"}\n"
"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: padding;\n"
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
"    height: 1"
                        "2px;\n"
"    image: url(:/icons/down_arrow_icon.svg);\n"
"}")
        self.timeStepSpin.setMinimum(1.000000000000000)
        self.timeStepSpin.setMaximum(3600.000000000000000)
        self.timeStepSpin.setValue(60.000000000000000)

        self.paramsLayout.addWidget(self.timeStepSpin)

        self.recalculateCheck = QCheckBox(CalculationDialog)
        self.recalculateCheck.setObjectName(u"recalculateCheck")

        self.paramsLayout.addWidget(self.recalculateCheck)

        self.limitFreqsCheck = QCheckBox(CalculationDialog)
        self.limitFreqsCheck.setObjectName(u"limitFreqsCheck")

        self.paramsLayout.addWidget(self.limitFreqsCheck)

        self.freqList = QListWidget(CalculationDialog)
        self.freqList.setObjectName(u"freqList")
        self.freqList.setEnabled(False)
        self.freqList.setStyleSheet(u"QListWidget {\n"
"    background-color: #ffffff;\n"
"    color: #333333;\n"
"    font-family: Arial, sans-serif;\n"
"    font-size: 9pt;\n"
"    border: 1px solid #d3d3d3;\n"
"}\n"
"QListWidget::item {\n"
"    padding: 4px;\n"
"}\n"
"QListWidget::item:selected {\n"
"    background-color: #0078d7;\n"
"    color: #ffffff;\n"
"}\n"
"QListWidget::item:hover {\n"
"    background-color: #1a8cff;\n"
"    color: #ffffff;\n"
"}")
        self.freqList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.paramsLayout.addWidget(self.freqList)


        self.gridLayout.addLayout(self.paramsLayout, 6, 0, 1, 2)

        self.ignoreDepsCheck = QCheckBox(CalculationDialog)
        self.ignoreDepsCheck.setObjectName(u"ignoreDepsCheck")

        self.gridLayout.addWidget(self.ignoreDepsCheck, 7, 0, 1, 2)

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

        self.calcVizButton = QPushButton(CalculationDialog)
        self.calcVizButton.setObjectName(u"calcVizButton")
        self.calcVizButton.setStyleSheet(u"QPushButton {\n"
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
        self.calcVizButton.setAutoDefault(False)
        self.calcVizButton.setFlat(True)

        self.buttonLayout.addWidget(self.calcVizButton)

        self.exportButton = QPushButton(CalculationDialog)
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


        self.gridLayout.addLayout(self.buttonLayout, 8, 0, 1, 2)


        self.retranslateUi(CalculationDialog)
        self.limitFreqsCheck.toggled.connect(self.freqList.setEnabled)

        QMetaObject.connectSlotsByName(CalculationDialog)
    # setupUi

    def retranslateUi(self, CalculationDialog):
        CalculationDialog.setWindowTitle(QCoreApplication.translate("CalculationDialog", u"Perform Calculations", None))
        self.labelCalculations.setText(QCoreApplication.translate("CalculationDialog", u"Calculations:", None))
        ___qtablewidgetitem = self.calcTable.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("CalculationDialog", u"Select", None));
        ___qtablewidgetitem1 = self.calcTable.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("CalculationDialog", u"Calculation Type", None));
        ___qtablewidgetitem2 = self.calcTable.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("CalculationDialog", u"Status", None));
        ___qtablewidgetitem3 = self.calcTable.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("CalculationDialog", u"Dependencies", None));
        self.labelTargets.setText(QCoreApplication.translate("CalculationDialog", u"Targets:", None))
        self.selectAllButton.setText(QCoreApplication.translate("CalculationDialog", u"Select All", None))
        self.labelParameters.setText(QCoreApplication.translate("CalculationDialog", u"Parameters:", None))
        self.recalculateCheck.setText(QCoreApplication.translate("CalculationDialog", u"Recalculate", None))
        self.limitFreqsCheck.setText(QCoreApplication.translate("CalculationDialog", u"Limit Frequencies", None))
        self.ignoreDepsCheck.setText(QCoreApplication.translate("CalculationDialog", u"Ignore Dependencies", None))
        self.calcButton.setText(QCoreApplication.translate("CalculationDialog", u"Calculate", None))
        self.calcVizButton.setText(QCoreApplication.translate("CalculationDialog", u"Calculate and Visualize", None))
        self.exportButton.setText(QCoreApplication.translate("CalculationDialog", u"Export Script", None))
        self.cancelButton.setText(QCoreApplication.translate("CalculationDialog", u"Cancel", None))
    # retranslateUi